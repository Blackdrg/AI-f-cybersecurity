"""
Additional Celery task for IoC enrichment reporting - appended to threat_intel_tasks.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

try:
    from celery import shared_task, Task
    from app.services.ioc_repository import IOCRepository
    from app.services.threat_cache import ThreatIntelCache

    class MonitoredTask(Task):
        autoretry_for = (Exception,)
        retry_kwargs = {'max_retries': 2}
        retry_backoff = True

        def on_success(self, retval, task_id, args, kwargs):
            try:
                from app.metrics import tasks_successful
                tasks_successful.inc()
            except Exception:
                pass
            super().on_success(retval, task_id, args, kwargs)

        def on_failure(self, exc, task_id, args, kwargs, einfo):
            logger = logging.getLogger(__name__)
            logger.error(f"Task {self.name}[{task_id}] failed: {exc}", exc_info=True)
            try:
                from app.metrics import tasks_failed
                tasks_failed.inc()
            except Exception:
                pass
            super().on_failure(exc, task_id, args, kwargs, einfo)

    @shared_task(bind=True, base=MonitoredTask, max_retries=2)
    def ioc_enrichment_report(self, org_id: str = None, days: int = 7):
        """Generate IoC enrichment summary report for security team."""
        try:
            async def generate():
                ioc_repo = IOCRepository()
                await ioc_repo.initialize()

                cache = ThreatIntelCache()
                cache_stats = await cache.get_cache_stats()

                # Get recent high-severity IOCs
                high_iocs = await ioc_repo.query_by_type(
                    ioc_type=None, severity="high", active_only=True, limit=100
                )

                critical_iocs = await ioc_repo.query_by_type(
                    ioc_type=None, severity="critical", active_only=True, limit=100
                )

                # Get feed sync statistics
                feed_stats = {}
                try:
                    db = ioc_repo.db_client.pool if ioc_repo.db_client and ioc_repo.db_client.pool else None
                    if db:
                        rows = await db.fetch("""
                            SELECT name, feed_type, last_sync, total_indicators, new_indicators
                            FROM threat_feeds ORDER BY last_sync DESC NULLS LAST
                        """)
                        for row in rows:
                            feed_stats[row['name']] = {
                                "type": row['feed_type'],
                                "last_sync": row['last_sync'].isoformat() if row['last_sync'] else None,
                                "total_indicators": row['total_indicators'],
                                "new_indicators": row['new_indicators']
                            }
                except Exception:
                    pass

                # Calculate IoC type distribution
                type_distribution = {}
                for ioc in high_iocs + critical_iocs:
                    ioc_type = ioc.get('ioc_type', 'unknown')
                    type_distribution[ioc_type] = type_distribution.get(ioc_type, 0) + 1

                # Source distribution
                source_distribution = {}
                for ioc in high_iocs + critical_iocs:
                    source = ioc.get('source', 'unknown')
                    source_distribution[source] = source_distribution.get(source, 0) + 1

                report = {
                    "report_type": "ioc_enrichment_summary",
                    "generated_at": datetime.utcnow().isoformat(),
                    "period_days": days,
                    "org_id": org_id,
                    "summary": {
                        "total_high_severity": len(high_iocs),
                        "total_critical_severity": len(critical_iocs),
                        "total_active_threats": len(high_iocs) + len(critical_iocs),
                        "type_distribution": type_distribution,
                        "source_distribution": source_distribution,
                    },
                    "feed_status": feed_stats,
                    "cache_health": cache_stats,
                    "top_threats": critical_iocs[:10],
                }

                # Log report to database
                if ioc_repo.db_client:
                    try:
                        await ioc_repo.db_client.pool.execute("""
                            INSERT INTO ioc_sync_log (feed_id, sync_start, sync_end,
                                indicators_fetched, indicators_new, status)
                            VALUES (
                                (SELECT feed_id FROM threat_feeds ORDER BY feed_id DESC LIMIT 1),
                                $1, $2, $3, $4, 'report_generated'
                            )
                        """,
                            datetime.utcnow() - timedelta(days=days),
                            datetime.utcnow(),
                            len(high_iocs) + len(critical_iocs),
                            len(critical_iocs)
                        )
                    except Exception as e:
                        logging.getLogger(__name__).warning(f"Report DB log failed: {e}")

                return report

            return asyncio.run(generate())
        except Exception as exc:
            logging.getLogger(__name__).error(f"IOC enrichment report failed: {exc}", exc_info=True)
            raise self.retry(exc=exc, countdown=300)

except ImportError:
    # Module-level import failure - task won't be registered but won't crash
    pass