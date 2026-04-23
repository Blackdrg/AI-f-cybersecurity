"""
Celery tasks for frame processing and multi-camera fusion.
"""
from app.celery_app import app
from app.camera.rtsp_manager import rtsp_manager
from app.db.db_client import get_db
from app.metrics import recognition_latency
import time
import asyncio
import logging
import cv2
import numpy as np
from typing import Dict, Any

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_frame(self, camera_id: str, top_k: int = 1, threshold: float = 0.6) -> Dict[str, Any]:
    """
    Celery task for processing a single camera frame with face recognition.
    
    Features:
    - Automatic retry with exponential backoff
    - Dead-letter queue after max retries
    - Time-limited execution
    - Metrics collection
    """
    start_time = time.time()
    request_id = str(time.time_ns())  # Simple request ID for tracing
    
    logger.info(
        "Processing frame",
        extra={"camera_id": camera_id, "request_id": request_id, "top_k": top_k}
    )
    
    try:
        # Get frame from RTSP buffer
        frame_bytes = rtsp_manager.get_frame(camera_id)
        if not frame_bytes:
            logger.warning("No frame available", extra={"camera_id": camera_id})
            return {'status': 'no_frame', 'camera_id': camera_id, 'request_id': request_id}
        
        # Decode image
        nparr = np.frombuffer(frame_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Import here to avoid circular imports
        from app.models.face_detector import FaceDetector
        detector = FaceDetector()
        faces = detector.detect_faces(img)
        
        # Run async database operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        db = loop.run_until_complete(get_db())
        
        results = []
        for face in faces:
            # Extract face region and compute embedding
            x, y, w, h = face['bbox']
            face_img = img[y:y+h, x:x+w]
            
            from app.models.face_recognizer import FaceRecognizer
            recognizer = FaceRecognizer()
            query_emb = recognizer.get_embedding(face_img)
            
            if query_emb is None:
                continue
            
            # Recognize
            matches = db.recognize_faces(query_emb, top_k, threshold, camera_id)
            results.append({
                'face': face['bbox'],
                'matches': matches,
                'confidence': face.get('confidence', 0.0)
            })
        
        latency = time.time() - start_time
        recognition_latency.observe(latency)
        
        logger.info(
            "Frame processed successfully",
            extra={
                "camera_id": camera_id,
                "request_id": request_id,
                "faces_detected": len(results),
                "latency": latency,
            }
        )
        
        # Retry if latency is too high (>500ms)
        if latency > 0.5:
            logger.warning(
                "High latency detected",
                extra={"camera_id": camera_id, "latency": latency, "request_id": request_id}
            )
            # Exponential backoff
            countdown = min(60, 2 ** self.request.retries)
            raise self.retry(exc=Exception(f"High latency: {latency}s"), countdown=countdown)
        
        return {
            'camera_id': camera_id,
            'faces': results,
            'latency': latency,
            'request_id': request_id
        }
        
    except Exception as exc:
        logger.error(
            "Frame processing failed",
            extra={
                "camera_id": camera_id,
                "request_id": request_id,
                "error": str(exc),
                "retry_count": self.request.retries,
            },
            exc_info=True
        )
        raise self.retry(exc=exc, countdown=min(300, 2 ** self.request.retries))


@app.task(bind=True, max_retries=2, default_retry_delay=120)
def multi_camera_fuse(self, camera_ids: list, top_k: int = 1, threshold: float = 0.6):
    """
    Fuse recognition results from multiple cameras.
    
    Supports parallel processing via Celery chord/group pattern.
    """
    logger.info(
        "Starting multi-camera fusion",
        extra={"task_id": self.request.id, "num_cameras": len(camera_ids)}
    )
    
    try:
        # Use group for parallel execution
        from celery import group
        job = group(
            process_frame.s(cam_id, top_k, threshold) 
            for cam_id in camera_ids
        )
        results = job.apply_async().get(timeout=30)
        
        # Fusion logic (simple majority or weighted by confidence)
        fused = {}
        for result in results:
            if result.get('status') == 'no_frame':
                continue
            for face in result.get('faces', []):
                for match in face.get('matches', []):
                    person_id = match['person_id']
                    if person_id not in fused:
                        fused[person_id] = {
                            'person_id': person_id,
                            'name': match['name'],
                            'total_score': 0,
                            'count': 0,
                            'cameras': set()
                        }
                    fused[person_id]['total_score'] += match.get('score', 0)
                    fused[person_id]['count'] += 1
                    fused[person_id]['cameras'].add(result['camera_id'])
        
        # Calculate average scores
        final_results = []
        for person_data in fused.values():
            avg_score = person_data['total_score'] / person_data['count']
            final_results.append({
                'person_id': person_data['person_id'],
                'name': person_data['name'],
                'score': avg_score,
                'cameras': list(person_data['cameras']),
                'confidence': avg_score  # Alias for consistency
            })
        
        # Sort by score
        final_results.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(
            "Multi-camera fusion completed",
            extra={
                "task_id": self.request.id,
                "results_count": len(final_results),
                "cameras": camera_ids,
            }
        )
        
        return final_results[:top_k]
        
    except Exception as exc:
        logger.error(
            "Multi-camera fusion failed",
            extra={"task_id": self.request.id, "error": str(exc)},
            exc_info=True
        )
        raise self.retry(exc=exc)
