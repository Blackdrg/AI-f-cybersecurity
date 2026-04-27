"""
Enrichment Tasks
Bias analysis, data enrichment, external data integration
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
def generate_bias_report(self, org_id: str = None, days_back: int = 30):
    """Generate fairness/bias audit report"""
    try:
        import asyncio
        from app.models.bias_detector import BiasDetector
        from app.db.db_client import get_db
        from datetime import datetime, timedelta
        
        async def compute():
            db = await get_db()
            detector = BiasDetector()
            cutoff = datetime.utcnow() - timedelta(days=days_back)
            recognitions = await db.get_recognitions_since(org_id, cutoff)
            report = detector.detect_bias(recognitions)
            await db.store_bias_report(org_id, report)
            return report
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(compute())
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"Bias report failed: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=120)


@shared_task(bind=True, base=MonitoredTask, max_retries=2, default_retry_delay=60)
def enrich_identity_with_external_data(self, person_id: str, sources: list = None):
    """Enrich identity with external data sources (with consent)"""
    try:
        import asyncio
        from app.db.db_client import get_db
        from app.providers.bing_provider import BingProvider
        from app.providers.wikipedia_provider import WikipediaProvider
        
        async def enrich():
            db = await get_db()
            person = await db.get_person(person_id)
            if not person:
                return {"error": "Person not found"}
            
            enriched = {}
            bing = BingProvider()
            wiki = WikipediaProvider()
            
            if person.get('name'):
                if not sources or 'bing' in sources:
                    enriched['bing'] = await bing.search(person['name'])
                if not sources or 'wikipedia' in sources:
                    enriched['wikipedia'] = await wiki.search_person(person['name'])
            
            await db.update_person_metadata(person_id, enriched)
            return {"person_id": person_id, "enriched": True, "sources": list(enriched.keys())}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(enrich())
        finally:
            loop.close()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, base=MonitoredTask, max_retries=2, default_retry_delay=300)
def calculate_risk_scores_batch(self, org_id: str = None, batch_size: int = 1000):
    """Calculate risk scores for recent recognition events"""
    try:
        import asyncio, numpy as np
        from app.db.db_client import get_db
        from app.scoring_engine import risk_scorer
        
        async def score_batch():
            db = await get_db()
            events = await db.get_unscored_recognitions(org_id, limit=batch_size)
            scored = 0
            total_risk = 0
            for event in events:
                risk = risk_scorer.calculate(event)
                await db.update_risk_score(event['id'], risk)
                scored += 1
                total_risk += risk
            avg = total_risk / scored if scored else 0
            return {"scored": scored, "avg_risk": avg}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(score_batch())
        finally:
            loop.close()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=120)


@shared_task(bind=True, base=MonitoredTask, max_retries=2)
def generate_consent_report(self, user_id: str):
    """Generate GDPR consent audit report"""
    try:
        import asyncio
        from app.db.db_client import get_db
        from app.api.compliance import generate_dsar_report
        
        async def gen():
            report = await generate_dsar_report(user_id)
            return report
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(gen())
        finally:
            loop.close()
    except Exception as exc:
        raise self.retry(exc=exc)
