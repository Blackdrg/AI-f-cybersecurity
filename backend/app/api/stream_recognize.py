from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import cv2
import numpy as np
import asyncio
import base64
import json
import time
from ..models.face_detector import FaceDetector
from ..models.face_embedder import FaceEmbedder
from ..models.emotion_detector import EmotionDetector
from ..models.age_gender_estimator import AgeGenderEstimator
from ..models.behavioral_predictor import BehavioralPredictor
from ..models.spoof_detector import SpoofDetector
from ..models.face_reconstructor import FaceReconstructor
from ..db.db_client import get_db
from typing import Any, Dict, List
from ..schemas import RecognizeResponse, DetectedFace, FaceMatch, MultiCameraRequest
# from ..security import require_auth_ws  # Placeholder for auth
from ..metrics import recognition_count, recognition_latency

router = APIRouter()

detector = FaceDetector()
embedder = FaceEmbedder()
emotion_detector = EmotionDetector()
age_gender_estimator = AgeGenderEstimator()
behavioral_predictor = BehavioralPredictor()
spoof_detector = SpoofDetector()
face_reconstructor = FaceReconstructor()


@router.websocket("/recognize_stream")
async def recognize_stream(
    websocket: WebSocket,
    top_k: int = 1,
    threshold: float = 0.4,
    camera_id: str = None
):
    await websocket.accept()

    db = await get_db()

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message['type'] == 'frame':
                # Decode base64 image
                img_data = base64.b64decode(message['data'])
                nparr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                start_time = time.time()

                faces = detector.detect_faces(img)
                detected_faces = []

                for face in faces:
                    inference_start = time.time()
                    aligned = detector.align_face(img, face['landmarks'])
                    query_emb = embedder.get_embedding(aligned)
                    inference_ms = (time.time() - inference_start) * 1000

                    matches = await db.recognize_faces(query_emb, top_k=top_k, threshold=threshold, camera_id=camera_id)

                    face_matches = [
                        FaceMatch(
                            person_id=m['person_id'],
                            name=m['name'],
                            score=m['score'],
                            distance=m['distance']
                        ) for m in matches
                    ]

                    is_unknown = len(face_matches) == 0

                    # Additional features for stream
                    emotion = emotion_detector.detect_emotion(
                        img, face['bbox'])
                    age_gender = age_gender_estimator.estimate_age_gender(
                        img, face['bbox'])
                    behavior = behavioral_predictor.predict_behavior(
                        emotion) if emotion else None

                    # Spoof detection
                    spoof_score = spoof_detector.detect_spoof(
                        img, face['bbox'])

                    # Face reconstruction (only if not likely spoof)
                    reconstruction_confidence = None
                    if spoof_score < 0.5:
                        reconstructed, reconstruction_confidence = face_reconstructor.reconstruct_face(
                            img, face['bbox'])

                    detected_faces.append(DetectedFace(
                        face_box=face['bbox'],
                        matches=face_matches,
                        inference_ms=inference_ms,
                        is_unknown=is_unknown,
                        spoof_score=spoof_score,
                        reconstruction_confidence=reconstruction_confidence,
                        emotion=emotion,
                        age=age_gender['age'] if age_gender else None,
                        gender=age_gender['gender'] if age_gender else None,
                        behavior=behavior
                    ))

                response = RecognizeResponse(faces=detected_faces)

                recognition_count.inc()
                recognition_latency.observe(time.time() - start_time)

                await websocket.send_json(response.dict())

            elif message['type'] == 'multi_camera':
                # Handle multi-camera sync
                request = MultiCameraRequest(**message['data'])
                synced_faces = await process_multi_camera(request, db)
                await websocket.send_json({"type": "multi_camera_result", "faces": synced_faces})

    except WebSocketDisconnect:
        pass


async def process_multi_camera(request: MultiCameraRequest, db) -> List[Dict[str, Any]]:
    """Process synchronized multi-camera streams"""
    all_faces = []
    base_timestamp = min(request.sync_timestamps)

    for i, stream in enumerate(request.streams):
        # Decode and process each stream
        img_data = base64.b64decode(stream)
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        faces = detector.detect_faces(img)
        for face in faces:
            aligned = detector.align_face(img, face['landmarks'])
            query_emb = embedder.get_embedding(aligned)

            matches = await db.recognize_faces(query_emb, camera_id=request.camera_ids[i])
            all_faces.append({
                'camera_id': request.camera_ids[i],
                'face_box': face['bbox'],
                'matches': matches,
                'timestamp_offset': request.sync_timestamps[i] - base_timestamp
            })

    # Fuse detections from multiple cameras (simple: combine matches)
    fused = {}
    for face in all_faces:
        for match in face['matches']:
            pid = match['person_id']
            if pid not in fused:
                fused[pid] = {'person_id': pid, 'cameras': [], 'scores': []}
            fused[pid]['cameras'].append(face['camera_id'])
            fused[pid]['scores'].append(match['score'])

    # Average scores across cameras
    for pid in fused:
        fused[pid]['avg_score'] = sum(
            fused[pid]['scores']) / len(fused[pid]['scores'])

    return list(fused.values())
