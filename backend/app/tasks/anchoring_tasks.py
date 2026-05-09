"""
Blockchain Anchoring Tasks
Periodically anchor audit chain root hash to external blockchain (Bitcoin, Ethereum, etc.)
"""
from celery import shared_task, Task
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)


class MonitoredAnchorTask(Task):
    """Base task with monitoring."""
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


@shared_task(bind=True, base=MonitoredAnchorTask, max_retries=3, default_retry_delay=300)
def anchor_audit_chain_to_blockchain(self):
    """
    Anchor the current audit chain root hash to an external blockchain (Bitcoin, Ethereum, etc.).
    This provides an immutable timestamped commitment to the state of the hash-chained audit log.

    Schedule: Controlled by ANCHOR_SCHEDULE environment variable (Celery beat crontab).
    Default: hourly (crontab minute=0, hour=*).
    """
    try:
        import asyncio
        from app.db.db_client import get_db
        from app.services.anchor_service import anchor_service

        async def anchor():
            # Get latest audit log hash (chain tip)
            db = await get_db()
            latest_hash = await db.get_latest_audit_hash()
            if not latest_hash:
                logger.warning("Blockchain anchoring skipped: no audit logs yet")
                return {"anchored": False, "reason": "no_audit_logs"}

            # Call external anchoring service
            result = await anchor_service.anchor_root_hash(latest_hash)
            if result.get("success"):
                tx_id = result.get("anchor_id")
                ledger = result.get("ledger", "unknown")
                logger.info(
                    f"Anchored audit chain root hash {latest_hash[:16]}... "
                    f"to {ledger} transaction {tx_id}"
                )
                # Record anchor in database for audit/verification
                await db.record_anchor(
                    root_hash=latest_hash,
                    tx_id=tx_id,
                    ledger=ledger,
                    anchored_at=datetime.utcnow()
                )
                return {
                    "anchored": True,
                    "root_hash": latest_hash,
                    "tx_id": tx_id,
                    "ledger": ledger,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                error = result.get("error", "Unknown anchoring error")
                logger.error(f"Blockchain anchoring failed: {error}")
                raise Exception(error)

        return asyncio.run(anchor())
    except Exception as exc:
        logger.error(f"Blockchain anchor task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=600)  # Retry after 10 minutes
