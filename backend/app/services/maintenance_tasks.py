"""
Celery tasks for enrollment and maintenance.
"""
from app.celery_app import app
from app.db.db_client import get_db
import logging
import asyncio

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=2, default_retry_delay=120)
def enroll_person_task(self, person_id: str, name: str, embeddings_bytes: list, 
                       consent_data: dict, metadata: dict = None):
    """
    Background task for person enrollment.
    
    Args:
        person_id: Unique identifier
        name: Person's name
        embeddings_bytes: List of serialized embedding arrays
        consent_data: Consent record information
        metadata: Additional enrollment data (age, gender, etc.)
    """
    logger.info(
        "Starting enrollment task",
        extra={"task_id": self.request.id, "person_id": person_id, "name": name}
    )
    
    try:
        # Deserialize embeddings
        import numpy as np
        embeddings = [np.frombuffer(eb, dtype=np.float32) for eb in embeddings_bytes]
        
        # Run async enrollment
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def enroll():
            db = await get_db()
            return await db.enroll_person(
                person_id=person_id,
                name=name,
                embeddings=embeddings,
                consent_record=consent_data,
                camera_id=metadata.get('camera_id') if metadata else None,
                age=metadata.get('age') if metadata else None,
                gender=metadata.get('gender') if metadata else None
            )
        
        result = loop.run_until_complete(enroll())
        
        logger.info(
            "Enrollment completed",
            extra={"task_id": self.request.id, "person_id": person_id, "success": result}
        )
        
        return {"person_id": person_id, "status": "enrolled", "success": result}
        
    except Exception as exc:
        logger.error(
            "Enrollment failed",
            extra={"task_id": self.request.id, "person_id": person_id, "error": str(exc)},
            exc_info=True
        )
        raise self.retry(exc=exc)


@app.task(bind=True)
def cleanup_old_data(self, days_to_keep: int = 30):
    """
    Periodic task to clean up old recognition events and logs.
    
    Args:
        days_to_keep: Number of days to retain data
    """
    logger.info(
        "Starting cleanup task",
        extra={"task_id": self.request.id, "days_to_keep": days_to_keep}
    )
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def cleanup():
            db = await get_db()
            async with db.pool.acquire() as conn:
                # Delete old recognition events
                deleted_events = await conn.execute("""
                    DELETE FROM recognition_events 
                    WHERE timestamp < NOW() - INTERVAL '%s days'
                """, days_to_keep)
                
                # Delete old audit logs
                deleted_logs = await conn.execute("""
                    DELETE FROM audit_logs 
                    WHERE created_at < NOW() - INTERVAL '%s days'
                """, days_to_keep)
                
                # Delete old enrichment results (TTL should handle this, but cleanup anyway)
                deleted_enrich = await conn.execute("""
                    DELETE FROM enrichment_results 
                    WHERE expires_at < NOW()
                """)
                
                return deleted_events, deleted_logs, deleted_enrich
        
        result = loop.run_until_complete(cleanup())
        
        logger.info(
            "Cleanup completed",
            extra={
                "task_id": self.request.id,
                "deleted_events": str(result[0]),
                "deleted_logs": str(result[1]),
                "deleted_enrich": str(result[2]),
            }
        )
        
        return {"status": "completed", "deleted": result}
        
    except Exception as exc:
        logger.error(
            "Cleanup failed",
            extra={"task_id": self.request.id, "error": str(exc)},
            exc_info=True
        )
        raise self.retry(exc=exc)


@app.task(bind=True)
def check_camera_health(self):
    """
    Periodic health check for all cameras.
    Marks offline cameras and sends alerts.
    """
    logger.debug("Checking camera health", extra={"task_id": self.request.id})
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def check():
            db = await get_db()
            cameras = await db.get_all_cameras()
            
            offline = []
            for camera in cameras:
                if camera['status'] != 'online':
                    offline.append(camera)
            
            return len(cameras), len(offline)
        
        total, offline_count = loop.run_until_complete(check())
        
        logger.info(
            "Camera health check completed",
            extra={
                "task_id": self.request.id,
                "total_cameras": total,
                "offline_count": offline_count,
            }
        )
        
        if offline_count > 0:
            # Trigger alert via alerts service
            logger.warning(
                "Cameras offline",
                extra={"offline_count": offline_count}
            )
        
        return {"total": total, "offline": offline_count}
        
    except Exception as exc:
        logger.error(
            "Camera health check failed",
            extra={"task_id": self.request.id, "error": str(exc)},
            exc_info=True
        )
        raise self.retry(exc=exc)
