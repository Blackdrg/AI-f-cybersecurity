"""
Compliance Tasks - GDPR, Data Retention, DSAR Processing
"""
import logging
from celery import shared_task
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=600)
def enforce_data_retention(self):
    """Enforce data retention policies per compliance requirements."""
    try:
        import asyncio
        from app.db.db_client import get_db

        async def enforce():
            db = get_db()
            policies_result = await db.fetch("""
                SELECT * FROM compliance.data_retention_policies
                WHERE is_active = TRUE AND next_execution <= NOW()
            """)

            total_deleted = 0
            for policy in policies_result:
                table = policy['table_name']
                retention_days = policy['retention_days']
                action = policy['archival_action']
                cutoff = datetime.utcnow() - timedelta(days=retention_days)

                if action == 'delete':
                    result = await db.execute(f"""
                        DELETE FROM {table}
                        WHERE created_at < $1::timestamptz
                    """, cutoff)
                    total_deleted += int(result.split()[-1]) if result else 0
                elif action == 'anonymize':
                    await db.execute(f"""
                        UPDATE {table}
                        SET name = 'ANONYMIZED', email = CONCAT('anon_', uuid_generate_v4(), '@deleted.local')
                        WHERE created_at < $1::timestamptz
                    """, cutoff)

                await db.execute("""
                    UPDATE compliance.data_retention_policies
                    SET last_executed = NOW(),
                        next_execution = NOW() + make_interval(days => retention_days)
                    WHERE policy_id = $1
                """, policy['policy_id'])

            return {'policies_enforced': len(policies_result), 'records_affected': total_deleted}

        return asyncio.run(enforce())
    except Exception as exc:
        logger.error(f"Data retention enforcement failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=600)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def process_dsar_request(self, request_id: str):
    """Process a Data Subject Access Request."""
    try:
        import asyncio
        from app.db.db_client import get_db

        async def process():
            db = get_db()

            # Get request details
            request = await db.fetchrow(
                "SELECT * FROM compliance.dsar_requests WHERE request_id = $1", request_id
            )
            if not request:
                raise ValueError(f"DSAR request {request_id} not found")

            # Collect user data across all schemas
            user_id = request['user_id']
            data_package = {}

            # Users
            data_package['user_profile'] = await db.fetchrow(
                "SELECT * FROM users WHERE user_id = $1", user_id
            )

            # Sessions
            data_package['sessions'] = await db.fetch(
                "SELECT * FROM user_sessions WHERE user_id = $1", user_id
            )

            # Activity
            data_package['activity_log'] = await db.fetch(
                "SELECT * FROM user_activity_log WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1000", user_id
            )

            # Persons (if org context exists)
            if request.get('data_scope') and 'biometrics' in str(request.get('data_scope', '')):
                data_package['persons'] = await db.fetch(
                    "SELECT * FROM persons WHERE person_id IN "
                    "(SELECT person_id FROM enrollments WHERE org_id = $1)",
                    request.get('org_id')
                )

            # Consent records
            data_package['consent_records'] = await db.fetch(
                "SELECT * FROM compliance.consent_records WHERE user_id = $1", user_id
            )

            # Handle deletion request
            if request['request_type'] == 'deletion':
                # Anonymize user data
                await db.execute("""
                    UPDATE users SET display_name = 'DELETED', email = CONCAT('deleted_', uuid_generate_v4(), '@local')
                    WHERE user_id = $1
                """, user_id)
                data_package['deletion_status'] = 'anonymized'

            # Generate data package URL (in production, upload to S3)
            data_package['generated_at'] = datetime.utcnow().isoformat()
            data_package['request_reference'] = request_id

            # Update request status
            await db.execute("""
                UPDATE compliance.dsar_requests
                SET status = 'completed', completed_at = NOW(), data_package_url = $1
                WHERE request_id = $2
            """, f"s3://dsar-packages/{request_id}.json", request_id)

            return data_package

        return asyncio.run(process())
    except Exception as exc:
        logger.error(f"DSAR processing failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=300)


@shared_task(bind=True, max_retries=2, default_retry_delay=86400)
def generate_compliance_report(self, org_id: str = None, period_days: int = 30):
    """Generate periodic compliance report."""
    try:
        import asyncio
        from app.db.db_client import get_db

        async def generate():
            db = get_db()
            now = datetime.utcnow()
            cutoff = now - timedelta(days=period_days)

            report = {
                'period': f"{cutoff.date()} to {now.date()}",
                'dsar_requests': await db.fetchval(
                    "SELECT COUNT(*) FROM compliance.dsar_requests WHERE created_at > $1", cutoff
                ),
                'consent_changes': await db.fetchval(
                    "SELECT COUNT(*) FROM audit.log_entries WHERE action = 'consent_update' AND created_at > $1", cutoff
                ),
                'data_deletions': await db.fetchval(
                    "SELECT COUNT(*) FROM audit.log_entries WHERE action = 'gdpr_delete' AND created_at > $1", cutoff
                ),
                'retention_enforcements': await db.fetchval(
                    "SELECT COUNT(*) FROM system_celery_tasks WHERE task_name = 'enforce_data_retention' AND created_at > $1 AND status = 'success'", cutoff
                ),
                'audit_chain_verified': await db.fetchval(
                    "SELECT COUNT(*) FROM audit.integrity_checks WHERE is_valid = TRUE AND created_at > $1", cutoff
                ),
            }

            if org_id:
                report['org_id'] = org_id

            return report

        return asyncio.run(generate())
    except Exception as exc:
        logger.error(f"Compliance report generation failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)