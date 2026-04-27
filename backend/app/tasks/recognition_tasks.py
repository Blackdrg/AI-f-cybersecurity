"""
Celery Tasks for AI-f
"""
from celery import shared_task, Task
import logging

logger = logging.getLogger(__name__)

class MonitoredTask(Task):
    """Base class with monitoring hooks"""
    def on_success(self, retval, task_id, args, kwargs):
        try:
            from app.metrics import tasks_successful
            tasks_successful.inc()
        except Exception:
            pass
        super().on_success(retval, task_id, args, kwargs)
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        try:
            from app.metrics import tasks_failed
            tasks_failed.inc()
        except Exception:
            pass
        super().on_failure(exc, task_id, args, kwargs, einfo)


@shared_task(bind=True, base=MonitoredTask, max_retries=5, default_retry_delay=60, acks_late=True)
def process_recognition_batch(self, image_batch, camera_ids, threshold=0.7, top_k=5, enable_spoof_check=True, org_id=None):
    """Batch face recognition processing"""
    logger.info(f"Processing recognition batch: {len(image_batch)} images")
    try:
        import asyncio, numpy as np, cv2
        from app.db.db_client import get_db
        from app.models.face_detector import FaceDetector
        from app.models.face_embedder import FaceEmbedder
        from datetime import datetime
        
        detector = FaceDetector()
        embedder = FaceEmbedder()
        
        async def process():
            db = await get_db()
            results = []
            for img_bytes, camera_id in zip(image_batch, camera_ids):
                try:
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    faces = detector.detect_faces(img, check_spoof=enable_spoof_check)
                    face_data = []
                    for face in faces:
                        if enable_spoof_check and face.get('spoof_score', 0) > 0.5:
                            continue
                        aligned = detector.align_face(img, face['landmarks'])
                        emb = embedder.get_embedding(aligned)
                        matches = await db.recognize_faces(emb, top_k=top_k, threshold=threshold, camera_id=camera_id)
                        face_data.append({"bbox": face['bbox'], "matches": matches})
                    results.append({"camera_id": camera_id, "faces": face_data, "timestamp": datetime.utcnow().isoformat()})
                except Exception as e:
                    logger.error(f"Error processing {camera_id}: {e}")
                    results.append({"camera_id": camera_id, "error": str(e), "faces": []})
            return {"batch_size": len(image_batch), "results": results, "processed_at": datetime.utcnow().isoformat()}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(process())
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"Recognition batch failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, base=MonitoredTask, max_retries=3, default_retry_delay=120)
def enroll_person_async(self, person_data, images, voice_files=None, gait_video=None):
    """Async enrollment with multi-modal data"""
    logger.info(f"Enrolling person: {person_data.get('name')}")
    try:
        import asyncio, numpy as np, cv2
        from app.db.db_client import get_db
        from app.models.face_detector import FaceDetector
        from app.models.face_embedder import FaceEmbedder
        from app.models.voice_embedder import VoiceEmbedder
        from app.models.gait_analyzer import GaitAnalyzer
        from app.models.zkp_proper import ZKProofManager
        from datetime import datetime
        
        detector = FaceDetector()
        embedder = FaceEmbedder()
        voice_embedder = VoiceEmbedder() if voice_files else None
        gait_analyzer = GaitAnalyzer() if gait_video else None
        zkp_manager = ZKProofManager()
        
        async def process():
            db = await get_db()
            person_id = person_data.get('person_id')
            face_embeddings = []
            for img_bytes in images:
                nparr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                faces = detector.detect_faces(img, check_spoof=False)
                if faces:
                    aligned = detector.align_face(img, faces[0]['landmarks'])
                    face_embeddings.append(embedder.get_embedding(aligned))
            if not face_embeddings:
                raise ValueError("No valid faces in enrollment images")
            
            voice_emb = voice_embedder.extract_embedding(voice_files) if voice_embedder and voice_files else None
            gait_emb = gait_analyzer.analyze_gait(gait_video) if gait_analyzer and gait_video else None
            
            await db.enroll_person(person_id, person_data['name'], face_embeddings, voice_emb, gait_emb, person_data.get('metadata', {}), person_data['consent_record'])
            proof = zkp_manager.generate_audit_proof(action="enroll", person_id=person_id, metadata={"timestamp": datetime.utcnow().isoformat()})
            await db.log_audit_event(action="enroll", person_id=person_id, details={"proof": proof.to_dict()}, zkp_proof=proof.to_dict())
            return {"person_id": person_id, "embeddings": len(face_embeddings), "audit_proof": True}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(process())
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"Enrollment failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=120 * (2 ** self.request.retries))


# Maintenance tasks
@shared_task(bind=True, base=MonitoredTask, max_retries=2, default_retry_delay=300)
def cleanup_stale_sessions(self, max_age_hours=24):
    """Remove expired sessions and cache entries"""
    try:
        import asyncio
        from app.db.db_client import get_db
        
        async def cleanup():
            db = await get_db()
            return {
                "deleted_sessions": await db.delete_expired_sessions(max_age_hours),
                "deleted_cache": await db.cleanup_redis_cache()
            }
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(cleanup())
        finally:
            loop.close()
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, base=MonitoredTask, max_retries=2, default_retry_delay=300)
def verify_audit_chain_integrity(self, start_id=None, end_id=None):
    """Daily chain integrity verification"""
    try:
        import asyncio
        from app.db.db_client import get_db
        from app.models.zkp_proper import ZKProofManager
        
        async def verify():
            db = await get_db()
            zkp = ZKProofManager()
            logs = await db.get_audit_logs_range(start_id, end_id)
            broken = []
            for i in range(1, len(logs)):
                if logs[i].get('previous_hash') != logs[i-1].get('hash'):
                    broken.append({"id": logs[i]['id']})
            invalid = [l['id'] for l in logs if l.get('zkp_proof') and not zkp.verify_audit_proof(l['zkp_proof'])]
            return {"total": len(logs), "chain_valid": len(broken)==0, "broken_links": broken, "invalid_proofs": len(invalid)}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(verify())
        finally:
            loop.close()
    except Exception as exc:
        raise self.retry(exc=exc)


# Model Training tasks
@shared_task(bind=True, base=MonitoredTask, max_retries=2, default_retry_delay=600)
def retrain_model_async(self, model_name: str, training_data_path: str, epochs: int = 10):
    """Async model retraining with gradient accumulation"""
    logger.info(f"Starting model retraining: {model_name}")
    try:
        import asyncio
        from app.models.model_calibrator import ModelCalibrator
        
        async def train():
            calibrator = ModelCalibrator()
            result = await calibrator.retrain_model(model_name, training_data_path, epochs)
            return result
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(train())
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"Model training failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=600)


@shared_task(bind=True, base=MonitoredTask, max_retries=3, default_retry_delay=120)
def process_video_recognition(self, video_path: str, camera_id: str, org_id: str, fps_sample: int = 1):
    """Batch video recognition with frame sampling"""
    try:
        import asyncio, cv2
        from app.db.db_client import get_db
        from app.models.face_detector import FaceDetector
        from app.models.face_embedder import FaceEmbedder
        
        detector = FaceDetector()
        embedder = FaceEmbedder()
        
        async def process():
            db = await get_db()
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Cannot open: {video_path}")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            sample_interval = int(fps / fps_sample) if fps > 0 else 1
            frame_idx = 0
            recognitions = []
            
            while True:
                ret, frame = cap.read()
                if not ret: break
                if frame_idx % sample_interval == 0:
                    faces = detector.detect_faces(frame, check_spoof=False)
                    for face in faces:
                        aligned = detector.align_face(frame, face['landmarks'])
                        emb = embedder.get_embedding(aligned)
                        matches = await db.recognize_faces(emb, top_k=3, threshold=0.7)
                        recognitions.append({"frame": frame_idx, "matches": matches})
                frame_idx += 1
            cap.release()
            
            await db.log_video_recognition(video_path, camera_id, org_id, frame_idx, len(recognitions))
            return {"video": video_path, "frames": frame_idx, "recognitions": len(recognitions)}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(process())
        finally:
            loop.close()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)
