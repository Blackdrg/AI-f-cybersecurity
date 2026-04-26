from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List, Optional
import cv2
import numpy as np
import time
import tempfile
import os
import uuid
import logging
from ..models.face_detector import FaceDetector
from .models.face_embedder import FaceEmbedder
from ..models.voice_embedder import VoiceEmbedder
from ..models.gait_analyzer import GaitAnalyzer
from ..models.emotion_detector import EmotionDetector
from ..models.age_gender_estimator import AgeGenderEstimator
from ..models.behavioral_predictor import BehavioralPredictor
from ..models.bias_detector import BiasDetector
from ..models.emotion_behavior import get_emotion_behavior_engine, BehaviorContext
from ..models.emotion_behavior import get_emotion_behavior_engine, BehaviorContext
from ..db.db_client import get_db
from ..schemas import StandardResponse
from ..security import require_auth
from ..metrics import recognition_count, recognition_latency
from ..middleware.policy_enforcement import require_recognize_policy
from ..decision_engine import decision_engine
from ..models.explainable_ai import decision_breakdown_engine

logger = logging.getLogger(__name__)
router = APIRouter()

# Model singletons
detector = FaceDetector()
embedder = FaceEmbedder()
voice_embedder = VoiceEmbedder()
gait_analyzer = GaitAnalyzer()
emotion_detector = EmotionDetector()
age_gender_estimator = AgeGenderEstimator()
behavioral_predictor = BehavioralPredictor()
bias_detector = BiasDetector()

from ..services.reliability import ai_model_circuit_breaker, db_circuit_breaker, CircuitBreakerOpenException


@router.post("/recognize", response_model=StandardResponse)
async def recognize_faces(
    image: UploadFile = File(...),
    top_k: int = Form(1),
    threshold: float = Form(0.4),
    camera_id: str = Form(None),
    enable_spoof_check: bool = Form(True),
    enable_emotion: bool = Form(True),
    enable_age_gender: bool = Form(True),
    enable_behavior: bool = Form(True),
    voice_file: UploadFile = File(None),
    gait_video: UploadFile = File(None),
    physiological_data: str = Form("{}"),
    include_explanations: bool = Form(False),
    user: dict = Depends(require_auth),
    _policy_ok: bool = Depends(require_recognize_policy)
):
    """
    Multi-modal biometric recognition with full decision engine integration.
    """
    try:
        start_time = time.time()

        # Decode image
        contents = await image.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return StandardResponse(success=False, error="Invalid image")

        # Detect faces
        try:
            faces = await ai_model_circuit_breaker(lambda: detector.detect_faces(
                img, check_spoof=enable_spoof_check, reconstruct=True))()
        except CircuitBreakerOpenException:
            return StandardResponse(success=False, error="AI service unavailable")
        except Exception:
            faces = []

        if not faces:
            return StandardResponse(success=True, data={"faces": [], "time_taken": time.time() - start_time})

        # Process voice
        voice_embedding = None
        if voice_file:
            vc = await voice_file.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
                tmp.write(vc)
                vp = tmp.name
            try:
                voice_embedding = voice_embedder.get_embedding(vp)
            finally:
                os.unlink(vp)

        # Process gait
        gait_embedding = None
        if gait_video:
            gc = await gait_video.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                tmp.write(gc)
                vp = tmp.name
            try:
                cap = cv2.VideoCapture(vp)
                frames = []
                while cap.isOpened() and len(frames) < 30:
                    ret, f = cap.read()
                    if not ret:
                        break
                    frames.append(f)
                cap.release()
                if frames:
                    gait_embedding = gait_analyzer.extract_gait_features(frames)
            finally:
                os.unlink(vp)

        db = await get_db()
        response_faces = []

        for face in faces:
            if enable_spoof_check and face['spoof_score'] > 0.5:
                continue

            # Embed
            aligned = detector.align_face(img, face['landmarks'])
            try:
                query_emb = await ai_model_circuit_breaker(lambda: embedder.get_embedding(aligned))()
            except Exception:
                continue

            # Search
            try:
                db_matches = await db_circuit_breaker(lambda: db.recognize_faces(
                    query_emb, top_k=top_k, threshold=threshold,
                    camera_id=camera_id,
                    voice_embedding=voice_embedding,
                    gait_embedding=gait_embedding
                ))()
            except Exception:
                db_matches = []

            is_unknown = len(db_matches) == 0

            # Decision engine
            de_face = {
                "matches": [
                    {"person_id": m['person_id'], "name": m['name'], "score": m['score']}
                    for m in db_matches
                ],
                "spoof_score": face['spoof_score']
            }
            de_result = decision_engine.make_decision(
                face_result=de_face,
                liveness_result={"spoof_score": face['spoof_score']},
                metadata={"camera_id": camera_id, "user_id": user.get("user_id")}
            )

            # Bias mitigation (simple boost)
            emotion = emotion_detector.detect_emotion(img, face['bbox']) if enable_emotion else None
            age_gender = age_gender_estimator.estimate_age_gender(img, face['bbox']) if enable_age_gender else None
            
            # Use integrated Emotion + Behavior Engine if enabled
            behavior_analysis = None
            if enable_behavior:
                try:
                    behavior_engine = get_emotion_behavior_engine()
                    # Build context from request metadata
                    context = BehaviorContext(
                        person_id=db_matches[0]['person_id'] if db_matches else 'unknown',
                        session_id=str(uuid.uuid4()),
                        location=camera_id or 'unknown',
                        time_of_day=time.strftime('%H:%M'),
                        crowd_density=0.5,  # Would come from camera analytics
                        weather='unknown',  # Could fetch from weather API
                        previous_interactions=0,  # Would query DB
                        known_individual=not is_unknown
                    )
                    # Run behavior analysis
                    behavior_analysis = await behavior_engine.analyze_frame(
                        person_id=context.person_id,
                        face_data={'embedding': query_emb, 'landmarks': face.get('landmarks')},
                        voice_data=None,
                        gait_data=None,
                        context=context
                    )
                    behavior = {
                        'state': behavior_analysis.behavior_state.value if hasattr(behavior_analysis.behavior_state, 'value') else str(behavior_analysis.behavior_state),
                        'risk_level': behavior_analysis.risk_level,
                        'risk_score': behavior_analysis.risk_score,
                        'action': behavior_analysis.action,
                        'explanation': behavior_analysis.explanation
                    }
                except Exception as e:
                    logger.warning(f"Behavior analysis failed: {e}")
                    behavior = None
            else:
                behavior = behavioral_predictor.predict_behavior(emotion) if emotion else None

            if age_gender:
                bias_input = [{
                    "is_known": not is_unknown,
                    "matches": [{"score": de_result.confidence}],
                    "gender": age_gender.get('gender', 'unknown'),
                    "age": age_gender.get('age', 'unknown')
                }]
                bm = bias_detector.detect_bias(bias_input)
                if bm.get('demographic_parity_difference', 0) > 0.1:
                    if age_gender.get('gender') == 'F' or (age_gender.get('age') or 0) > 60:
                        de_result = de_result._replace(confidence=min(1.0, de_result.confidence * 1.1))

            # Build matches
            face_matches = [
                FaceMatch(
                    person_id=m['person_id'],
                    name=m['name'],
                    score=m['score'],
                    distance=m['distance']
                ) for m in db_matches
            ]

            # Build response face
            resp_face = {
                "face_box": face['bbox'],
                "face_embedding_id": str(uuid.uuid4()),
                "matches": face_matches,
                "inference_ms": 0.0,
                "is_unknown": is_unknown,
                "spoof_score": face['spoof_score'] if enable_spoof_check else None,
                "reconstruction_confidence": face['reconstruction_confidence'],
                "emotion": emotion,
                "age": age_gender['age'] if age_gender else None,
                "gender": age_gender['gender'] if age_gender else None,
                "behavior": behavior,
                "identity_score": float(de_result.confidence),
                "decision": de_result.decision,
                "risk_level": de_result.risk_level.value if hasattr(de_result.risk_level, 'value') else str(de_result.risk_level),
                "decision_factors": de_result.factors
            }

            if include_explanations:
                from ..models.explainable_ai import ExplainableDecision, DecisionFactor
                factors = [
                    DecisionFactor(
                        factor=f.get("factor", "unknown"),
                        contribution=float(f.get("impact", 0.0)),
                        description=f.get("description", "")
                    ) for f in de_result.factors
                ]
                expl = decision_breakdown_engine.explain_decision(
                    decision=de_result.decision,
                    confidence=float(de_result.confidence),
                    risk_score=0.5 if de_result.risk_level.value == "low" else 0.8,
                    face_result=de_face,
                    liveness_score=1.0 - face['spoof_score'],
                    factors=factors,
                    processing_time_ms=0.0
                )
                resp_face["explanation"] = expl.to_dict()

            response_faces.append(resp_face)

        recognition_count.inc()
        recognition_latency.observe(time.time() - start_time)

        return StandardResponse(
            success=True,
            data={"faces": response_faces, "time_taken": time.time() - start_time},
            error=None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recognition error: {e}", exc_info=True)
        return StandardResponse(success=False, error=str(e))


@router.post("/recognize_zkp", response_model=StandardResponse)
async def recognize_faces_zkp(request: dict, user: dict = Depends(require_auth)):
    try:
        return StandardResponse(success=True, data={"faces": []}, error=None)
    except Exception as e:
        logger.error(f"ZKP error: {e}", exc_info=True)
        return StandardResponse(success=False, error=str(e))
