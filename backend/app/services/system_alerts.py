"""System-level alert checker.

Runs periodic background checks for BIAS_THRESHOLD_EXCEEDED and CONFIDENCE_DROPOUT alerts.
"""

import asyncio
import logging
from datetime import datetime
from typing import List

from ..db.db_client import get_db
from ..models.bias_detector import BiasDetector
from ..api.alerts import check_bias_alert, check_confidence_dropout

logger = logging.getLogger(__name__)

# Global flag to control background task
_system_alerts_task = None
_check_interval_seconds = 300  # 5 minutes


async def _check_all_organizations():
    """Iterate over all organizations and evaluate system alerts."""
    db = get_db()
    if db.pool is None:
        logger.warning("DB not available for system alert checks")
        return
    
    try:
        org_rows = await db.pool.fetch("SELECT org_id FROM organizations")
    except Exception as e:
        logger.error(f"Failed to fetch organizations: {e}")
        return
    
    if not org_rows:
        return
    
    detector = BiasDetector()
    now = datetime.utcnow()
    
    for row in org_rows:
        org_id = row['org_id']
        try:
            # Check bias
            await check_bias_alert(db, org_id, detector, now)
            # Check confidence dropout
            await check_confidence_dropout(db, org_id, now)
        except Exception as e:
            logger.error(f"Alert check failed for org {org_id}: {e}", exc_info=True)


async def start_system_alerts(interval: int = None):
    """Start background periodic system alert checks."""
    global _system_alerts_task
    if interval is not None:
        global _check_interval_seconds
        _check_interval_seconds = interval
    
    logger.info(f"Starting system alerts background task (interval={_check_interval_seconds}s)")
    
    while True:
        try:
            await _check_all_organizations()
        except Exception as e:
            logger.error(f"System alert check iteration failed: {e}", exc_info=True)
        await asyncio.sleep(_check_interval_seconds)


async def stop_system_alerts():
    """Stop the background task (for graceful shutdown)."""
    global _system_alerts_task
    if _system_alerts_task:
        _system_alerts_task.cancel()
        _system_alerts_task = None
        logger.info("System alerts task stopped")
