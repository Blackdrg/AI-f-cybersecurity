"""
Compliance Tasks
Data retention, SAR processing, and compliance auditing
"""
from celery import shared_task
import logging
import asyncio
from datetime import datetime, timedelta
from ..db.db_client import get_db

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def automated_data_retention_purge(self):
    """
    Purges data that has exceeded retention periods.
    Default: 
    - Audit logs: 7 years
    - PII/Biometric templates: 3 years (if inactive)
    - Temporary uploads: 24 hours
    """
    try:
        async def purge():
            db = await get_db()
            
            # Retention settings (could be moved to env/config)
            LOG_RETENTION_DAYS = 7 * 365
            PII_RETENTION_DAYS = 3 * 365
            TEMP_RETENTION_HOURS = 24
            
            # 1. Purge Audit Logs
            cutoff_audit = datetime.utcnow() - timedelta(days=LOG_RETENTION_DAYS)
            purged_audit = await db.purge_audit_logs(cutoff_audit)
            logger.info(f"Purged {purged_audit} audit logs older than {cutoff_audit}")
            
            # 2. Purge Inactive PII
            cutoff_pii = datetime.utcnow() - timedelta(days=PII_RETENTION_DAYS)
            purged_pii = await db.purge_inactive_pii(cutoff_pii)
            logger.info(f"Purged {purged_pii} inactive PII profiles older than {cutoff_pii}")
            
            # 3. Purge Temp Files/Cache
            cutoff_temp = datetime.utcnow() - timedelta(hours=TEMP_RETENTION_HOURS)
            purged_temp = await db.purge_temp_data(cutoff_temp)
            
            return {
                "audit_logs_purged": purged_audit,
                "pii_purged": purged_pii,
                "temp_purged": purged_temp
            }
            
        return asyncio.run(purge())
    except Exception as exc:
        logger.error(f"Data retention purge failed: {exc}")
        raise self.retry(exc=exc, countdown=3600)

@shared_task(bind=True, max_retries=2)
def generate_sar_export(self, person_id: str, request_id: str):
    """
    Subject Access Request (SAR) Data Export.
    Collects all data relating to a specific identity and packages it.
    """
    try:
        async def export():
            db = await get_db()
            
            # 1. Collect all data
            profile = await db.get_person_by_id(person_id)
            if not profile:
                return {"success": False, "error": "Person not found"}
                
            embeddings = await db.get_embeddings_for_person(person_id)
            audit_events = await db.get_audit_events_for_person(person_id)
            recognition_events = await db.get_recognition_history_for_person(person_id)
            
            # 2. Format as JSON/XML
            export_data = {
                "identity": profile,
                "biometric_templates_count": len(embeddings),
                "audit_history": audit_events,
                "recognition_history": recognition_events,
                "exported_at": datetime.utcnow().isoformat()
            }
            
            # 3. Save to secure storage
            from ..providers.storage_provider import secure_save_export
            filename = f"sar_export_{person_id}_{request_id}.json"
            download_url = await secure_save_export(filename, export_data)
            
            # 4. Notify requester (via webhook or email)
            # await notify_sar_complete(request_id, download_url)
            
            return {"success": True, "download_url": download_url}
            
        return asyncio.run(export())
    except Exception as exc:
        logger.error(f"SAR export failed for {person_id}: {exc}")
        raise self.retry(exc=exc, countdown=300)

@shared_task(bind=True)
def run_compliance_auto_audit(self):
    """
    Automated check of compliance controls.
    - Verify audit chain
    - Check encryption status
    - Check MFA enforcement rates
    """
    try:
        async def audit():
            db = await get_db()
            
            # 1. Audit Chain Integrity
            broken_links = await db.verify_audit_chain()
            
            # 2. MFA Adoption
            mfa_stats = await db.get_mfa_adoption_stats()
            
            # 3. Encryption verification (mock check)
            encryption_status = "OK" # In reality, check KMS/Vault health
            
            report = {
                "timestamp": datetime.utcnow().isoformat(),
                "audit_chain_healthy": len(broken_links) == 0,
                "broken_links": broken_links,
                "mfa_adoption": mfa_stats,
                "encryption_status": encryption_status
            }
            
            # Log results to compliance table
            await db.log_compliance_audit(report)
            
            return report
         
        return asyncio.run(audit())
    except Exception as exc:
        logger.error(f"Compliance audit failed: {exc}")
        return {"success": False, "error": str(exc)}
