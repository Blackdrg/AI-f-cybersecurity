"""
Maintenance Tasks
System health, cleanup, and periodic maintenance tasks
"""
from celery import shared_task, Task
import logging
logger = logging.getLogger(__name__)

class MonitoredTask(Task):
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


@shared_task(bind=True, base=MonitoredTask, max_retries=2, default_retry_delay=300)
def check_model_health(self):
    """Monitor model performance and trigger retraining if degraded"""
    try:
        import asyncio
        from app.models.model_calibrator import evaluation_pipeline
        from datetime import datetime, timedelta
        
        async def check():
            # Check if any model accuracy has dropped below threshold
            degraded_models = evaluation_pipeline.check_drift()
            if degraded_models:
                for model_name, drift_info in degraded_models.items():
                    logger.warning(f"Model {model_name} degraded: {drift_info}")
                    # Trigger retraining
                    retrain_model_async.delay(model_name, f"/data/{model_name}_training", epochs=5)
            return {"degraded": len(degraded_models) > 0, "models": degraded_models}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(check())
        finally:
            loop.close()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, base=MonitoredTask, max_retries=2, default_retry_delay=300)
def verify_audit_chain_integrity(self):
    """Daily verification of hash chain integrity"""
    try:
        import asyncio
        from app.db.db_client import get_db
        
        async def verify():
            db = await get_db()
            broken = await db.verify_audit_chain()
            if broken:
                logger.error(f"Audit chain broken at {len(broken)} points")
                # Send alert
                from app.middleware.alerting import send_critical_alert
                send_critical_alert("AUDIT_CHAIN_BROKEN", {"broken_links": broken})
            return {"valid": len(broken) == 0, "broken_count": len(broken)}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(verify())
        finally:
            loop.close()
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, base=MonitoredTask, max_retries=3)
def cleanup_stale_sessions(self, max_age_hours: int = 24):
    """Remove expired sessions and old cache entries"""
    try:
        import asyncio
        from app.db.db_client import get_db
        from datetime import timedelta
        
        async def cleanup():
            db = await get_db()
            sessions = await db.cleanup_expired_sessions(timedelta(hours=max_age_hours))
            cache = await db.cleanup_redis_cache(pattern="session:*")
            return {"deleted_sessions": sessions, "deleted_cache_keys": cache}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(cleanup())
        finally:
            loop.close()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=180)


@shared_task(bind=True, base=MonitoredTask, max_retries=2)
def rotate_encryption_keys(self):
    """Rotate data encryption keys (scheduled quarterly)"""
    try:
        import asyncio
        from app.security.key_manager import key_manager
        
        async def rotate():
            new_key = await key_manager.rotate_keys()
            return {"rotated": True, "new_key_version": new_key.version}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(rotate())
        finally:
            loop.close()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=600)


@shared_task(bind=True, base=MonitoredTask, max_retries=2)
def backup_database(self):
    """Create encrypted backup of critical tables"""
    try:
        import asyncio, subprocess, os
        from datetime import datetime
        
        async def backup():
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_file = f"/backups/pg_backup_{timestamp}.sql.gz"
            
            # Use pg_dump
            cmd = f"pg_dump -h ${{DB_HOST}} -U ${{DB_USER}} -d ${{DB_NAME}} | gzip > {backup_file}"
            subprocess.run(cmd, shell=True, check=True)
            
            # Upload to S3 or object storage
            from app.providers.storage_provider import upload_backup
            url = await upload_backup(backup_file)
            return {"backup_url": url, "timestamp": timestamp}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(backup())
        finally:
            loop.close()
    except Exception as exc:
        raise self.retry(exc=exc)
