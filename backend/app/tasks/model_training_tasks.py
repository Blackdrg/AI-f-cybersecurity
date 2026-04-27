"""
Model Training Tasks
Async training, fine-tuning, and model management tasks
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


@shared_task(bind=True, base=MonitoredTask, max_retries=2, default_retry_delay=600)
def retrain_model_async(self, model_name: str, training_data_path: str, epochs: int = 10, learning_rate: float = 0.001):
    """Async model retraining with federated aggregation support"""
    logger.info(f"Starting retraining: {model_name} on {training_data_path}")
    try:
        import asyncio
        from app.models.model_calibrator import ModelCalibrator
        
        async def train():
            calibrator = ModelCalibrator()
            result = await calibrator.retrain_model(model_name, training_data_path, epochs, learning_rate)
            return result
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(train())
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"Training failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=600)


@shared_task(bind=True, base=MonitoredTask, max_retries=2, default_retry_delay=300)
def evaluate_model_pipeline(self, model_version: str, test_dataset_path: str):
    """Run full evaluation pipeline on test dataset"""
    try:
        import asyncio
        from app.models.model_calibrator import evaluation_pipeline
        
        async def evaluate():
            result = await evaluation_pipeline.evaluate(model_version, test_dataset_path)
            return result
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(evaluate())
        finally:
            loop.close()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, base=MonitoredTask, max_retries=1)
def export_model_to_onnx(self, model_name: str, model_path: str, output_path: str = None):
    """Export PyTorch model to ONNX format for edge deployment"""
    try:
        import torch
        from app.models.model_calibrator import get_model
        import os
        
        model = get_model(model_name)
        model.load_state_dict(torch.load(model_path))
        model.eval()
        
        dummy_input = torch.randn(1, 3, 112, 112)
        if output_path is None:
            output_path = f"/app/models/onnx/{model_name}.onnx"
        
        torch.onnx.export(
            model,
            dummy_input,
            output_path,
            export_params=True,
            opset_version=14,
            do_constant_folding=True,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes={'input': {0: 'batch_size'}, 'output': {0: 'batch_size'}}
        )
        
        return {"model": model_name, "onnx_path": output_path, "status": "exported"}
    except Exception as exc:
        logger.error(f"ONNX export failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, base=MonitoredTask, max_retries=3)
def publish_model_to_registry(self, model_name: str, version: str, model_path: str, metrics: dict, changelog: str = ""):
    """Publish trained model to model registry"""
    try:
        import asyncio
        from app.db.db_client import get_db
        from app.models.model_calibrator import version_manager
        
        async def publish():
            db = await get_db()
            version_manager.register_version(
                version=version,
                model_name=model_name,
                model_path=model_path,
                metrics=metrics,
                changelog=changelog,
                status="staging"
            )
            # Store in DB
            await db.store_model_version(model_name, version, model_path, metrics, changelog)
            return {"published": True, "model": model_name, "version": version}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(publish())
        finally:
            loop.close()
    except Exception as exc:
        raise self.retry(exc=exc)
