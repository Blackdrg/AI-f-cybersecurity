import celery
from celery import Celery
from .camera.rtsp_manager import rtsp_manager
from ..db.db_client import get_db
from ..metrics import recognition_latency
import time
import asyncio
import logging
from typing import Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

async def get_db_async():
    db = await get_db()
    return db

app = Celery('face_recognition', broker='redis://localhost:6379/0')

@app.task(bind=True)
def process_frame(self, camera_id: str, top_k: int = 1, threshold: float = 0.6):
    """Celery task for frame processing (stable queue)."""
    start_time = time.time()
    
    # Get frame from RTSP buffer
    frame_bytes = rtsp_manager.get_frame(camera_id)
    if not frame_bytes:
        return {'status': 'no_frame', 'camera_id': camera_id}
    
    import cv2
    import numpy as np
    nparr = np.frombuffer(frame_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Load models (from globals or init)
    from ..models.face_detector import FaceDetector
    detector = FaceDetector()
    faces = detector.detect_faces(img)
    
    loop.run_until_complete(get_db_async())  # Temp sync call
    db = _db_client  # Global from db_client
    results = []

    for face in faces:
        # Process face (stub - full in stream_recognize)
        query_emb = np.random.randn(512).astype(np.float32)  # Placeholder
        matches = db.recognize_faces(query_emb, top_k, threshold, camera_id)
        results.append({'face': face['bbox'], 'matches': matches})
    
    latency = time.time() - start_time
    recognition_latency.observe(latency)
    
    if latency > 0.3:  # >300ms
        self.retry(countdown=1)
    
    return {'camera_id': camera_id, 'faces': results, 'latency': latency}

@app.task
def multi_camera_fuse(camera_ids: list):
    """Fuse multi-cam results."""
    results = []
    for cam_id in camera_ids:
        frame_result = process_frame.delay(cam_id)
        results.append(frame_result.get(timeout=0.5))
    return results

# Config
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_prefetch_multiplier=1,  # Low latency
    task_acks_late=True,
)
