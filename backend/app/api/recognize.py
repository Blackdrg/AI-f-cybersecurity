from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List, Optional
import cv2
import numpy as np
import time
import tempfile
import os
import uuid
import logging
import json
import socket
import struct
import asyncio
from ..models.face_detector import FaceDetector
from ..models.face_embedder import FaceEmbedder
from ..models.voice_embedder import VoiceEmbedder
from ..models.gait_analyzer import GaitAnalyzer
from ..models.emotion_detector import EmotionDetector
from ..models.age_gender_estimator import AgeGenderEstimator
from ..models.behavioral_predictor import BehavioralPredictor
from ..models.bias_detector import BiasDetector
from ..models.hallucination_detector import HallucinationRisk, hallucination_detector
from ..models.emotion_behavior import get_emotion_behavior_engine, BehaviorContext
from ..db.db_client import get_db
from ..schemas import StandardResponse
from ..security import require_auth
from ..metrics import recognition_count, recognition_latency
from ..middleware.policy_enforcement import require_recognize_policy
from ..decision_engine import decision_engine
from ..models.explainable_ai import decision_breakdown_engine
from ..services.logger import get_logger

logger = logging.getLogger(__name__)
router = APIRouter()

# Model singletons (embedding models stay outside enclave)
detector = FaceDetector()
embedder = FaceEmbedder()
voice_embedder = VoiceEmbedder()
gait_analyzer = GaitAnalyzer()
emotion_detector = EmotionDetector()
age_gender_estimator = AgeGenderEstimator()
behavioral_predictor = BehavioralPredictor()
bias_detector = BiasDetector()
# Use singleton from module
hallucination_detector = hallucination_detector

from ..services.reliability import ai_model_circuit_breaker, db_circuit_breaker, CircuitBreakerOpenException

# TEE configuration
_enclave_enabled = os.getenv("ENCLAVE_ENABLED", "false").lower() == "true"


def recvall(conn, n):
    """Helper to receive exactly n bytes."""
    data = b''
    while len(data) < n:
        packet = conn.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data


def send_request_to_enclave(request_dict):
    """Send encrypted request to TEE enclave via VSOCK.
    
    Encrypts embedding → VSOCK → Decrypt response.
    """
    from ..security.encryption_utils import encrypt_request, decrypt_response
    
    encrypted_req = encrypt_request(request_dict)
    
    try:
        sock = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((3, 5000))

        request_json = json.dumps(encrypted_req)
        request_bytes = request_json.encode('utf-8')
        sock.sendall(struct.pack('>I', len(request_bytes)))
        sock.sendall(request_bytes)

        raw_msglen = recvall(sock, 4)
        if not raw_msglen:
            return {"success": False, "error": "No response"}
        msglen = struct.unpack('>I', raw_msglen)[0]
        response_bytes = recvall(sock, msglen)
        sock.close()
        
        response = json.loads(response_bytes.decode('utf-8'))
        return decrypt_response(response)
    except Exception as e:
        logger.error(f"TEE enclave error: {e}")
        return {"success": False, "error": str(e)}


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
    Face matching is performed inside the secure enclave.
    """
    try:
        start_time = time.time()

        # Decode image
        contents = await image.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return StandardResponse(success=False, error="Invalid image")

        # Detect faces (offloaded to threadpool to avoid blocking event loop)
        async def do_detect():
            return detector.detect_faces(img, check_spoof=enable_spoof_check, reconstruct=True)
        try:
            faces = await ai_model_circuit_breaker(do_detect)()
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

            # Embed (offloaded to threadpool)
            aligned = detector.align_face(img, face['landmarks'])
            try:
                async def get_emb():
                    return embedder.get_embedding(aligned)
                query_emb = await ai_model_circuit_breaker(get_emb)()
            except Exception:
                continue

            enclave_request = {
                "id": str(uuid.uuid4()),
                "operation": "face_match",
                "embedding": query_emb.flatten().tolist()  # Send as flat list
            }
            
            # Enclave communication is blocking; offload to thread
            enclave_response = await asyncio.to_thread(send_request_to_enclave, enclave_request)
            
            if not enclave_response.get("success", False):
                error_msg = f"Enclave request failed: {enclave_response.get('error')}"
                logger.error(error_msg)
                if _enclave_enabled:
                    # Strict mode: fail closed when TEE is required
                    return StandardResponse(
                        success=False,
                        error="Secure enclave unavailable — recognition service temporarily unavailable"
                    )
                # Fallback to local matching if enclave is unavailable (dev/optional)
                logger.warning("Falling back to non-TEE matching (less secure)")
                db_matches = await db_circuit_breaker(lambda: db.recognize_faces(
                    query_emb, top_k=top_k, threshold=threshold,
                    camera_id=camera_id,
                    voice_embedding=voice_embedding,
                    gait_embedding=gait_embedding
                ))()
            else:
                # Process enclave response
                result = enclave_response.get("result", {})
                if result.get("matched", False):
                    # We have a match, get the details from the database
                    matched_index = result.get("index")
                    similarity = result.get("similarity", 0.0)
                    
                    # Get the person details from the database
                    # For simplicity, we'll get all matches and then filter by index
                    # In a production system, you might optimize this
                    db_matches = await db_circuit_breaker(lambda: db.recognize_faces(
                        query_emb, top_k=top_k*2, threshold=threshold*0.8,  # Lower threshold to get more candidates
                        camera_id=camera_id,
                        voice_embedding=voice_embedding,
                        gait_embedding=gait_embedding
                    ))()
                    
                    # Reorder matches so the enclave-matched one is first if possible
                    if matched_index is not None and matched_index < len(db_matches):
                        # Swap the matched index to the front
                        matched_person = db_matches.pop(matched_index)
                        db_matches.insert(0, matched_person)
                else:
                    # No match found in enclave
                    db_matches = []

            is_unknown = len(db_matches) == 0

            # Decision engine
            de_face = {
                "matches": [
                    {"person_id": m['person_id'], "name": m['name'], "score": m['score']}
                    for m in db_matches
                ],
                "spoof_score": face['spoof_score'],
                "embedding": query_emb  # Include embedding for hallucination detection
            }
            de_result = decision_engine.make_decision(
                face_result=de_face,
                liveness_result={"spoof_score": face['spoof_score']},
                metadata={
                    "camera_id": camera_id,
                    "user_id": user.get("user_id"),
                    "embedding": query_emb,
                    "age": age_gender.get('age') if age_gender else None,
                    "gender": age_gender.get('gender') if age_gender else None,
                    "enrolled_age": age_gender.get('age') if age_gender else None,
                    "enrolled_gender": age_gender.get('gender') if age_gender else None
                }
            )

            # === Hallucination Detection (post-recognition) ===
            hallucination_risk = None
            try:
                # Build context for hallucination detection
                h_context = {
                    "enrolled_age": age_gender.get('age') if age_gender else None,
                    "detected_age": age_gender.get('age') if age_gender else None,
                    "enrolled_gender": age_gender.get('gender') if age_gender else None,
                    "detected_gender": age_gender.get('gender') if age_gender else None,
                    "voice_result": {
                        "matches": [{"person_id": m['person_id']} for m in (voice_embedding or [])]
                    } if voice_embedding else None,
                    "gait_result": {
                        "matches": [{"person_id": m['person_id']} for m in (gait_embedding or [])]
                    } if gait_embedding else None
                }
                hallucination_risk: HallucinationRisk = hallucination_detector.detect_hallucination(
                    face_result=de_face,
                    context=h_context
                )
                
                # Log high-risk hallucination events
                if hallucination_risk and hallucination_risk.flagged:
                    logger.warning(
                        f"HALLUCINATION_DETECTED: risk={hallucination_risk.risk_score:.3f}, "
                        f"person_id={db_matches[0]['person_id'] if db_matches else 'unknown'}, "
                        f"factors={hallucination_risk.factors}",
                        extra={
                            "event": "hallucination",
                            "risk_score": hallucination_risk.risk_score,
                            "factors": hallucination_risk.factors,
                            "person_id": db_matches[0]['person_id'] if db_matches else None,
                            "camera_id": camera_id,
                            "user_id": user.get("user_id")
                        }
                    )
            except Exception as e:
                logger.error(f"Hallucination detection error: {e}", exc_info=True)

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
            # Compute confidence interval from calibrator
            try:
                from ..scoring_engine import confidence_calibrator
                ci_lower, ci_upper = confidence_calibrator.get_confidence_interval(
                    embedding=query_emb,
                    matches=db_matches
                )
                confidence_interval = (ci_lower, ci_upper)
            except Exception as e:
                logger.error(f"Confidence interval error: {e}")
                confidence_interval = None
            
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
                "decision_factors": de_result.factors,
                # New AI reliability fields
                "hallucination_risk": {
                    "score": hallucination_risk.risk_score if hallucination_risk else None,
                    "flagged": hallucination_risk.flagged if hallucination_risk else False,
                    "factors": hallucination_risk.factors if hallucination_risk else {},
                    "recommendation": hallucination_risk.recommendation if hallucination_risk else None
                },
                "confidence_interval": confidence_interval
            }

            # Log recognition event for audit & alerting
            try:
                event_id = await db.log_recognition_event(
                    org_id=user.get("org_id"),
                    person_id=db_matches[0]['person_id'] if db_matches else None,
                    camera_id=camera_id,
                    confidence=float(de_result.confidence),
                    metadata={
                        "user_id": user.get("user_id"),
                        "decision": de_result.decision,
                        "risk_level": str(de_result.risk_level),
                        "num_matches": len(db_matches),
                        "spoof_score": face.get('spoof_score', 0.0),
                        "emotion": emotion,
                        "age": age_gender.get('age') if age_gender else None,
                        "gender": age_gender.get('gender') if age_gender else None,
                    }
                )
                # Trigger rule-based alerts asynchronously
                from app.api.alerts import process_event_rules
                asyncio.create_task(process_event_rules(
                    event_id=event_id,
                    org_id=user.get("org_id"),
                    person_id=db_matches[0]['person_id'] if db_matches else None,
                    camera_id=camera_id or ''
                ))
            except Exception as e:
                logger.error(f"Failed to log recognition event: {e}", exc_info=True)

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