"""
Federated Learning Tasks
Secure aggregation, client coordination, OTA model distribution
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


@shared_task(bind=True, base=MonitoredTask, max_retries=3, default_retry_delay=120)
def aggregate_federated_updates(self, round_id: str, client_updates: list):
    """
    Perform secure aggregation of federated learning updates using
    Secure Aggregation protocol (Bonawitz et al.)
    """
    try:
        import asyncio
        from app.federated_learning import secure_aggregator
        
        async def aggregate():
            # Verify client signatures
            valid_updates = []
            for update in client_updates:
                if secure_aggregator.verify_signature(update):
                    valid_updates.append(update)
            
            # Perform secure aggregation (add secret sharing)
            aggregated = secure_aggregator.secure_aggregate(valid_updates)
            
            # Update global model
            from app.models.model_calibrator import global_model
            global_model.apply_update(aggregated)
            
            # Evaluate
            metrics = global_model.evaluate()
            
            return {
                "round_id": round_id,
                "clients": len(valid_updates),
                "aggregated": True,
                "metrics": metrics
            }
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(aggregate())
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"Aggregation failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, base=MonitoredTask, max_retries=3)
def trigger_federated_round(self, round_config: dict = None):
    """Trigger a new federated learning round"""
    try:
        import asyncio
        from app.federated_learning import orchestrator
        
        async def trigger():
            round_id = await orchestrator.start_round(round_config or {})
            return {"round_id": round_id, "status": "started"}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(trigger())
        finally:
            loop.close()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=600)


@shared_task(bind=True, base=MonitoredTask, max_retries=2)
def distribute_model_update(self, model_version: str, target_clients: list = None):
    """Distribute new model to edge devices via OTA"""
    try:
        import asyncio
        from app.db.db_client import get_db
        from app.models.model_calibrator import version_manager
        
        async def distribute():
            db = await get_db()
            model_path = version_manager.get_model_path(model_version)
            if not model_path:
                raise FileNotFoundError(f"Model {model_version} not found")
            
            # Get all active edge devices
            devices = await db.get_active_edge_devices() if not target_clients else target_clients
            
            # Queue OTA jobs
            jobs = []
            for device_id in devices:
                job = await db.create_ota_job(device_id, model_version, model_path)
                jobs.append(job)
            
            return {"model": model_version, "devices": len(devices), "jobs_created": len(jobs)}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(distribute())
        finally:
            loop.close()
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, base=MonitoredTask, max_retries=2, default_retry_delay=600)
def verify_client_update(self, client_id: str, round_id: str, update_proof: dict):
    """Verify zero-knowledge proof of client update correctness"""
    try:
        import asyncio
        from app.federated_learning import zkp_verifier
        
        async def verify():
            valid = zkp_verifier.verify_update(update_proof)
            return {"client_id": client_id, "round_id": round_id, "valid": valid}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(verify())
        finally:
            loop.close()
    except Exception as exc:
        raise self.retry(exc=exc)
