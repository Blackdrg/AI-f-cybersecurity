from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List
import cv2
import numpy as np
import time
from ..models.face_detector import FaceDetector
from ..models.face_embedder import FaceEmbedder
from ..db.db_client import get_db
from ..schemas import RecognizeResponse, DetectedFace, FaceMatch
from ..security import require_auth
from ..metrics import recognition_count, recognition_latency

router = APIRouter()

detector = FaceDetector()
embedder = FaceEmbedder()


@router.post("/recognize_video", response_model=List[RecognizeResponse])
async def recognize_video(
    video: UploadFile = File(...),
    top_k: int = Form(1),
    threshold: float = Form(0.4),
    camera_id: str = Form(None),
    frame_interval: int = Form(30),  # Process every 30th frame
    user: dict = Depends(require_auth)
):
    start_time = time.time()

    contents = await video.read()
    nparr = np.frombuffer(contents, np.uint8)
    cap = cv2.VideoCapture()
    cap.open(nparr)

    if not cap.isOpened():
        raise HTTPException(status_code=400, detail="Invalid video file")

    frame_count = 0
    results = []

    db = await get_db()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % frame_interval != 0:
            continue

        # Process frame
        faces = detector.detect_faces(frame)
        detected_faces = []

        for face in faces:
            inference_start = time.time()
            aligned = detector.align_face(frame, face['landmarks'])
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
            detected_faces.append(DetectedFace(
                face_box=face['bbox'],
                matches=face_matches,
                inference_ms=inference_ms,
                is_unknown=is_unknown
            ))

        results.append(RecognizeResponse(faces=detected_faces))

    cap.release()

    recognition_count.inc()
    recognition_latency.observe(time.time() - start_time)

    return results
