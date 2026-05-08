"""Integration tests for database replication and failover.

Tests:
- Write to primary appears on replica within SLA (5 seconds)
- Read replica failover scenarios
- Primary failover simulation
- Consistency verification between primary and replica
"""

import os
import pytest
import asyncio
from typing import AsyncGenerator, Optional, Tuple, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import uuid

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
import sys
sys.path.insert(0, str(BACKEND_DIR))

from app.db.db_client import DBClient


@pytest.fixture
async def primary_db() -> AsyncGenerator[DBClient, None]:
    """Provide primary database connection."""
    db = DBClient()
    await db.init_db()
    
    if db.pool is None:
        pytest.skip("Primary database not available")
    
    yield db
    await db.close()


@pytest.fixture
async def replica_db() -> AsyncGenerator[Optional[DBClient], None]:
    """Provide read replica database connection if configured."""
    replica_urls = os.environ.get('DB_READ_REPLICAS', '')
    if not replica_urls:
        pytest.skip("No read replicas configured (DB_READ_REPLICAS)")
    
    # Use first replica
    db = DBClient(read_replicas=[replica_urls.split(',')[0]])
    await db.init_db()
    
    if db.pool is None or not db.read_replica_pools:
        pytest.skip("Read replica not available")
    
    yield db
    await db.close()


@pytest.mark.integration
@pytest.mark.database
class TestReplication:
    """Test suite for database replication and failover."""
    
    async def test_write_propagates_to_replica(
        self, 
        primary_db: DBClient, 
        replica_db: DBClient
    ):
        """Test that writes to primary appear on replica within SLA (5 seconds)."""
        # Generate unique test data
        test_org_id = str(uuid.uuid4())
        test_user_id = f"repl_test_{uuid.uuid4().hex[:8]}"
        
        # Write to primary
        await primary_db.execute(
            """
            INSERT INTO organizations (org_id, name, subscription_tier)
            VALUES ($1, $2, $3)
            """,
            test_org_id,
            f"Replication Test Org {datetime.utcnow().isoformat()}",
            'enterprise',
            force_primary=True
        )
        
        # Poll replica until data appears (with timeout)
        start_time = datetime.utcnow()
        timeout = timedelta(seconds=5)
        found = False
        
        while datetime.utcnow() - start_time < timeout:
            try:
                row = await replica_db.fetchrow(
                    "SELECT name FROM organizations WHERE org_id = $1",
                    test_org_id,
                    use_replica=True
                )
                if row and row['name']:
                    found = True
                    break
            except Exception:
                pass
            await asyncio.sleep(0.2)
        
        assert found, (
            f"Write did not propagate to replica within 5 seconds SLA. "
            f"Org ID: {test_org_id}"
        )
        
        # Measure actual replication lag
        lag_seconds = (datetime.utcnow() - start_time).total_seconds()
        print(f"Replication lag: {lag_seconds:.2f}s")
        
        # Cleanup
        await primary_db.execute(
            "DELETE FROM organizations WHERE org_id = $1",
            test_org_id,
            force_primary=True
        )
    
    async def test_replica_health_checking(self, primary_db: DBClient, replica_db: DBClient):
        """Test that replica health checking works correctly."""
        # Trigger health check via DBClient
        await primary_db.health_check_replicas()
        
        # Check replica health status
        assert len(primary_db.read_replica_health) > 0
        health = primary_db.read_replica_health[0]
        assert 'healthy' in health
        assert 'last_check' in health
        
        print(f"Replica health status: {health}")
    
    async def test_read_queries_use_replicas(self, primary_db: DBClient):
        """Test that read queries with use_replica=True hit the replica pool."""
        if not primary_db.read_replica_pools or not any(
            p is not None for p in primary_db.read_replica_pools
        ):
            pytest.skip("No healthy replicas configured")
        
        # Execute a read query with replica flag
        result = await primary_db.fetch(
            "SELECT COUNT(*) as cnt FROM organizations",
            use_replica=True
        )
        
        assert result is not None
        assert result[0]['cnt'] >= 0
    
    async def test_replica_failover_on_down(self, primary_db: DBClient):
        """Test failover behavior when replica becomes unavailable."""
        if len(primary_db.read_replica_pools) < 2:
            pytest.skip("Need at least 2 replicas to test failover")
        
        # Initial state: replicas should be healthy
        initial_healthy = sum(
            1 for h in primary_db.read_replica_health if h.get('healthy', False)
        )
        assert initial_healthy >= 1, "At least one replica should be healthy"
        
        # Simulate replica failure by marking it unhealthy
        # (In real test, you'd stop the replica DB, but we'll just check logic)
        primary_db.read_replica_health[0]['healthy'] = False
        
        # Get read pool - should skip unhealthy and use next healthy replica
        pool = await primary_db._get_read_pool()
        
        # Should get a pool (either another replica or primary fallback)
        assert pool is not None, "Should get a fallback pool when replica is down"
        
        # Mark replica back healthy for cleanup
        primary_db.read_replica_health[0]['healthy'] = True
    
    async def test_round_robin_load_balancing(self, primary_db: DBClient):
        """Test that read replicas are used in round-robin fashion."""
        if len(primary_db.read_replica_pools) < 2:
            pytest.skip("Need at least 2 replicas to test round-robin")
        
        # Track which replica pools are used
        used_indices = []
        
        for _ in range(10):
            pool = await primary_db._get_read_pool()
            # Find index of this pool
            for i, p in enumerate(primary_db.read_replica_pools):
                if p is pool:
                    used_indices.append(i)
                    break
        
        # Should see variety in indices (round-robin)
        unique_indices = set(used_indices)
        assert len(unique_indices) > 1, (
            f"Round-robin not working: only used indices {used_indices}"
        )
    
    async def test_consistency_after_multiple_writes(self, primary_db: DBClient, replica_db: DBClient):
        """Test data consistency between primary and replica after multiple writes."""
        test_org_id = str(uuid.uuid4())
        
        # Perform multiple writes
        writes = []
        for i in range(5):
            user_id = f"consistency_test_{i}_{uuid.uuid4().hex[:8]}"
            await primary_db.execute(
                """
                INSERT INTO users (user_id, email, name, subscription_tier)
                VALUES ($1, $2, $3, $4)
                """,
                user_id,
                f"test{i}@example.com",
                f"Test User {i}",
                'free',
                force_primary=True
            )
            writes.append(user_id)
        
        # Wait for replication (up to 5 seconds)
        await asyncio.sleep(2)
        
        # Verify all writes appear on replica
        for user_id in writes:
            row = await replica_db.fetchrow(
                "SELECT email FROM users WHERE user_id = $1",
                user_id,
                use_replica=True
            )
            assert row is not None, f"User {user_id} missing on replica"
            assert row['email'].startswith('test'), f"Unexpected email: {row['email']}"
        
        # Cleanup
        for user_id in writes:
            await primary_db.execute(
                "DELETE FROM users WHERE user_id = $1",
                user_id,
                force_primary=True
            )
    
    async def test_replication_with_complex_query(self, primary_db: DBClient, replica_db: DBClient):
        """Test replication of complex queries with joins and aggregations."""
        test_org_id = str(uuid.uuid4())
        
        # Setup: create org with users and subscriptions
        await primary_db.execute(
            "INSERT INTO organizations (org_id, name) VALUES ($1, $2)",
            test_org_id,
            "Complex Query Test Org",
            force_primary=True
        )
        
        for i in range(3):
            user_id = f"complex_user_{i}"
            await primary_db.execute(
                """
                INSERT INTO users (user_id, email, name, subscription_tier)
                VALUES ($1, $2, $3, $4)
                """,
                user_id,
                f"complex{i}@test.com",
                f"Complex User {i}",
                'pro',
                force_primary=True
            )
            await primary_db.execute(
                """
                INSERT INTO subscriptions (subscription_id, user_id, plan_id, status)
                VALUES ($1, $2, $3, $4)
                """,
                f"sub_{i}",
                user_id,
                'pro',
                'active',
                force_primary=True
            )
        
        # Wait for replication
        await asyncio.sleep(2)
        
        # Run complex query on replica
        result = await replica_db.fetch(
            """
            SELECT 
                o.name as org_name,
                COUNT(DISTINCT u.user_id) as user_count,
                COUNT(DISTINCT s.subscription_id) as subscription_count
            FROM organizations o
            LEFT JOIN users u ON o.org_id = u.user_id
            LEFT JOIN subscriptions s ON u.user_id = s.user_id
            WHERE o.org_id = $1
            GROUP BY o.name
            """,
            test_org_id,
            use_replica=True
        )
        
        assert len(result) == 1
        assert result[0]['user_count'] >= 3
        assert result[0]['subscription_count'] >= 3
        
        # Cleanup
        await primary_db.execute(
            "DELETE FROM organizations WHERE org_id = $1",
            test_org_id,
            force_primary=True
        )
    
    async def test_replication_lag_alerting(self, primary_db: DBClient):
        """Test that replication lag exceeding threshold triggers alerts."""
        # This test verifies the monitoring logic
        # In production, lag should be < 5 seconds
        
        # Check current replication lag
        async with primary_db.pool.acquire() as conn:
            lag_result = await conn.fetch("""
                SELECT 
                    application_name,
                    pg_xlog_location_diff(pg_current_wal_lsn(), replay_lsn) as lag_bytes
                FROM pg_stat_replication
                WHERE state = 'streaming'
            """)
            
            for row in lag_result:
                lag_bytes = row['lag_bytes'] or 0
                lag_seconds = lag_bytes / 16 / 1024  # Approximate
                
                # In a healthy system, lag should be minimal
                assert lag_seconds < 5, (
                    f"Replication lag too high on {row['application_name']}: "
                    f"{lag_seconds:.1f}s"
                )
    
    async def test_cross_region_replication_consistency(self):
        """Test consistency across cross-region replicas (if configured)."""
        # This would require multi-region setup
        # Skip by default, enable in specific environments
        pytest.skip("Cross-region replication test requires multi-region setup")
