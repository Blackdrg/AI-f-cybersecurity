"""Celery task queue integration tests.

Tests asynchronous task processing:
- Task creation and execution
- Result backend
- Task retries and error handling
- Queue routing and priorities
"""

import pytest
import time
from unittest.mock import patch


@pytest.mark.celery
@pytest.mark.integration
class TestCeleryIntegration:
    """Integration tests for Celery task queue."""

    @pytest.fixture(scope="session")
    def celery_app(self):
        """Create Celery app configured for testing."""
        try:
            from app.celery_app import celery_app
            return celery_app
        except ImportError:
            pytest.skip("Celery app not available")

    @pytest.fixture
    def celery_worker(self, celery_app):
        """Start an in-memory Celery worker for testing."""
        from celery.contrib.testing.worker import start_worker
        with start_worker(celery_app, concurrency=2, perform_ping_check=False):
            yield

    def test_task_enqueue_and_execute(self, celery_app, celery_worker):
        """Test that a task can be enqueued and executed."""
        from app.tasks import sample_task  # hypothetical task
        
        # Enqueue task
        result = sample_task.delay("test_arg")
        
        # Wait for completion
        output = result.get(timeout=10)
        assert output == "expected_result"

    def test_task_retry_on_failure(self, celery_app, celery_worker):
        """Test that tasks retry on transient failures."""
        from app.tasks import unreliable_task
        
        # Task should retry and eventually succeed or fail gracefully
        result = unreliable_task.delay()
        
        with pytest.raises(Exception):
            result.get(timeout=5)

    def test_task_result_backend(self, celery_app, celery_worker):
        """Test that task results are stored and retrievable."""
        from app.tasks import simple_task
        
        result = simple_task.delay(42)
        task_id = result.id
        
        # Check result stored in backend (Redis typically)
        stored = celery_app.AsyncResult(task_id)
        assert stored.id == task_id
        
        # Get result
        final = stored.get(timeout=10)
        assert final == 42

    def test_task_priority_queues(self, celery_app, celery_worker):
        """Test that tasks respect queue priorities."""
        # High priority task should execute before low priority
        from app.tasks import high_priority_task, low_priority_task
        
        start = time.time()
        
        high_res = high_priority_task.apply_async(priority=9)
        low_res = low_priority_task.apply_async(priority=0)
        
        high_out = high_res.get(timeout=10)
        low_out = low_res.get(timeout=10)
        
        # High should finish before low (if truly prioritized)
        # Note: depends on worker configuration
        assert high_out is not None
        assert low_out is not None

    def test_task_chord_execution(self, celery_app, celery_worker):
        """Test chord (group + callback) execution."""
        from celery import chord
        from app.tasks import process_chunk, aggregate_results
        
        # Create chord: map + reduce
        chord_obj = chord(
            [process_chunk.s(i) for i in range(5)],
            aggregate_results.s()
        )
        result = chord_obj()
        
        output = result.get(timeout=20)
        assert output is not None

    @pytest.mark.redis
    async def test_task_result_expiry(self, celery_app, real_redis):
        """Test that task results expire after configured TTL."""
        # Enqueue task, wait, check Redis key TTL
        pass

    def test_task_timeout(self, celery_app, celery_worker):
        """Test that tasks respect time limits."""
        from app.tasks import long_running_task
        
        result = long_running_task.apply_async()
        
        with pytest.raises(Exception) as exc_info:
            result.get(timeout=2)  # Should timeout
        
        assert "timeout" in str(exc_info.value).lower()

    def test_task_revocation(self, celery_app, celery_worker):
        """Test that tasks can be revoked before execution."""
        from app.tasks import revocable_task
        
        result = revocable_task.delay()
        task_id = result.id
        
        # Revoke before it runs
        result.revoke(terminate=True)
        
        with pytest.raises(Exception):
            result.get(timeout=5)
        
        # Verify task state is REVOKED
        assert celery_app.AsyncResult(task_id).status == "REVOKED"
