from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List
import cv2
import numpy as np
import time
import base64
import tempfile
import os
import uuid
from ..models.face_detector import FaceDetector
from ..models.face_embedder import FaceEmbedder
from ..models.voice_embedder import VoiceEmbedder
from ..models.gait_analyzer import GaitAnalyzer
from ..models.emotion_detector import EmotionDetector
from ..models.age_gender_estimator import AgeGenderEstimator
from ..models.behavioral_predictor import BehavioralPredictor
from ..models.bias_detector import BiasDetector
from ..models.zkp_auth import ZKPAuthenticator
from ..db.db_client import get_db
from ..schemas import RecognizeRequest, RecognizeResponse, DetectedFace, FaceMatch, ZKPRequest
from ..security import require_auth, check_ethical
from ..metrics import recognition_count, recognition_latency, false_accepts, false_rejects

router = APIRouter()

detector = FaceDetector()
embedder = FaceEmbedder()
voice_embedder = VoiceEmbedder()
gait_analyzer = GaitAnalyzer()
emotion_detector = EmotionDetector()
age_gender_estimator = AgeGenderEstimator()
behavioral_predictor = BehavioralPredictor()
bias_detector = BiasDetector()
zkp_auth = ZKPAuthenticator()


@router.post("/recognize", response_model=RecognizeResponse)
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
    user: dict = Depends(require_auth)
):
    start_time = time.time()

    contents = await image.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    faces = detector.detect_faces(
        img, check_spoof=enable_spoof_check, reconstruct=True)
    detected_faces = []

    db = await get_db()

    # Process voice if provided
    voice_embedding = None
    if voice_file:
        voice_contents = await voice_file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            tmp.write(voice_contents)
            tmp_path = tmp.name
        try:
            voice_embedding = voice_embedder.get_embedding(tmp_path)
        finally:
            os.unlink(tmp_path)

    # Process gait if provided
    gait_embedding = None
    if gait_video:
        gait_contents = await gait_video.read()
        nparr_gait = np.frombuffer(gait_contents, np.uint8)
        cap = cv2.VideoCapture()
        cap.open(nparr_gait)
        frames = []
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
            if len(frames) >= 30:
                break
        cap.release()
        if frames:
            gait_embedding = gait_analyzer.extract_gait_features(frames)

    for face in faces:
        # Skip if spoof detected and check enabled
        if enable_spoof_check and face['spoof_score'] > 0.5:
            continue

        inference_start = time.time()
        aligned = detector.align_face(img, face['landmarks'])
        query_emb = embedder.get_embedding(aligned)
        inference_ms = (time.time() - inference_start) * 1000

        matches = await db.recognize_faces(query_emb, top_k=top_k, threshold=threshold, camera_id=camera_id, voice_embedding=voice_embedding, gait_embedding=gait_embedding)

        face_matches = [
            FaceMatch(
                person_id=m['person_id'],
                name=m['name'],
                score=m['score'],
                distance=m['distance']
            ) for m in matches
        ]

        is_unknown = len(face_matches) == 0

        # Additional features
        emotion = None
        if enable_emotion:
            emotion = emotion_detector.detect_emotion(img, face['bbox'])

        age_gender = None
        if enable_age_gender:
            age_gender = age_gender_estimator.estimate_age_gender(
                img, face['bbox'])

        behavior = None
        if enable_behavior and emotion:
            behavior = behavioral_predictor.predict_behavior(emotion)

        detected_faces.append(DetectedFace(
            face_box=face['bbox'],
            face_embedding_id=str(uuid.uuid4()),
            matches=face_matches,
            inference_ms=inference_ms,
            is_unknown=is_unknown,
            spoof_score=face['spoof_score'] if enable_spoof_check else None,
            reconstruction_confidence=face['reconstruction_confidence'],
            emotion=emotion,
            age=age_gender['age'] if age_gender else None,
            gender=age_gender['gender'] if age_gender else None,
            behavior=behavior
        ))

    recognition_count.inc()
    recognition_latency.observe(time.time() - start_time)

    # Apply bias mitigation
    bias_metrics = bias_detector.detect_bias(
        [face.dict() for face in detected_faces])
    if bias_metrics.get('demographic_parity_difference', 0) > 0.1:
        mitigated = bias_detector.mitigate_bias(
            [face.dict() for face in detected_faces], bias_metrics)
        detected_faces = [DetectedFace(**face) for face in mitigated]

    return RecognizeResponse(faces=detected_faces)


@router.post("/recognize_zkp", response_model=RecognizeResponse)
async def recognize_faces_zkp(
    request: ZKPRequest,
    user: dict = Depends(require_auth)
):
    # ZKP-based recognition without revealing raw embedding
    # Simplified: assume proof contains embedding hash
    # In production, verify ZKP properly
    db = await get_db()
    # Placeholder: fetch user embedding and verify
    # For POC, assume authenticated
    return RecognizeResponse(faces=[])
