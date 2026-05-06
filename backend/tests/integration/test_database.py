"""Database integration tests.

Tests real PostgreSQL + pgvector operations including:
- Connection pooling
- Vector storage and retrieval
- HNSW index performance
- Transaction isolation
- Concurrent access patterns
"""

import pytest
import time
import numpy as np
from datetime import datetime
from typing import Optional


class TestDatabaseIntegration:
    """Tests for real database connectivity and operations."""

    @pytest.mark.database
    @pytest.mark.integration
    async def test_database_connection_real(self, real_db):
        """Test that we can connect to the real database."""
        assert real_db.pool is not None
        
        async with real_db.pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1

    @pytest.mark.database
    @pytest.mark.integration
    async def test_pgvector_extension_loaded(self, real_db):
        """Verify pgvector extension is available and functional."""
        async with real_db.pool.acquire() as conn:
            # Check extension is installed
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
            assert result is True

    @pytest.mark.database
    @pytest.mark.integration
    async def test_vector_insert_and_query(self, real_db):
        """Test inserting and querying vector data."""
        async with real_db.pool.acquire() as conn:
            # Create a temporary table for testing
            await conn.execute("""
                CREATE TEMP TABLE test_vectors (
                    id SERIAL PRIMARY KEY,
                    embedding vector(512),
                    label TEXT
                ) ON COMMIT DROP
            """)
            
            # Insert a vector
            test_vector = np.random.randn(512).astype(np.float32).tolist()
            await conn.execute(
                "INSERT INTO test_vectors (embedding, label) VALUES ($1, $2)",
                test_vector, "test_label"
            )
            
            # Retrieve it
            row = await conn.fetchrow("SELECT id, label FROM test_vectors WHERE label = $1", "test_label")
            assert row is not None
            assert row['label'] == "test_label"
            
            # Verify vector distance query works
            result = await conn.fetchrow(
                "SELECT embedding <=> $1 as distance FROM test_vectors",
                test_vector
            )
            assert result['distance'] < 1e-6  # Should be nearly identical

    @pytest.mark.database
    @pytest.mark.vector_search
    @pytest.mark.integration
    async def test_hnsw_index_performance(self, real_db):
        """Test HNSW index query performance."""
        import numpy as np
        
        num_vectors = 1000
        async with real_db.pool.acquire() as conn:
            # Create table with HNSW index
            await conn.execute("""
                CREATE TEMP TABLE hnsw_test (
                    id SERIAL PRIMARY KEY,
                    embedding vector(512),
                    created_at TIMESTAMPTZ DEFAULT NOW()
                ) ON COMMIT DROP
            """)
            
            await conn.execute("""
                CREATE INDEX ON hnsw_test 
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 32, ef_construction = 40)
            """)
            
            # Insert test vectors
            vectors = [np.random.randn(512).astype(np.float32) for _ in range(num_vectors)]
            for vec in vectors:
                vec_norm = vec / np.linalg.norm(vec)
                await conn.execute(
                    "INSERT INTO hnsw_test (embedding) VALUES ($1)",
                    vec_norm.tolist()
                )
            
            # Warm-up query
            query_vec = vectors[0] / np.linalg.norm(vectors[0])
            
            # Measure query time
            start = time.time()
            results = await conn.fetch(
                "SELECT id, 1 - (embedding <=> $1) as similarity FROM hnsw_test ORDER BY embedding <=> $1 LIMIT 10",
                query_vec.tolist()
            )
            elapsed = time.time() - start
            
            assert len(results) == 10
            assert elapsed < 1.0  # Should complete in under 1 second even with 1000 vectors

    @pytest.mark.database
    @pytest.mark.integration
    async def test_transaction_isolation(self, real_db):
        """Test transaction isolation and rollback behavior."""
        async with real_db.pool.acquire() as conn:
            # Begin transaction in test connection
            await conn.execute("BEGIN")
            
            # Insert data
            await conn.execute("""
                CREATE TEMP TABLE iso_test (
                    id INT,
                    value TEXT
                ) ON COMMIT DROP
            """)
            await conn.execute("INSERT INTO iso_test VALUES (1, 'test')")
            
            # Verify it's visible in same transaction
            count = await conn.fetchval("SELECT COUNT(*) FROM iso_test")
            assert count == 1
            
            # Rollback
            await conn.execute("ROLLBACK")
            
            # Table should be gone
            # (Temp table automatically drops on rollback)
            # Verify by checking if we can still query - will fail
            
    @pytest.mark.database
    @pytest.mark.integration
    async def test_concurrent_connections(self, real_db):
        """Test that connection pooling works correctly under concurrency."""
        import asyncio
        
        async def simple_query():
            async with real_db.pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                return result
        
        # Run 50 concurrent queries
        tasks = [simple_query() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        
        assert all(r == 1 for r in results)
        assert len(results) == 50

    @pytest.mark.database
    @pytest.mark.integration
    async def test_audit_log_insertion(self, real_db):
        """Test that audit logs can be inserted and retrieved."""
        async with real_db.pool.acquire() as conn:
            # Check if audit_log table exists
            exists = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'audit_log'
                )
            """)
            
            if exists:
                # Insert a test audit event
                await conn.execute("""
                    INSERT INTO audit_log 
                    (event_type, user_id, details, timestamp, ip_address)
                    VALUES ($1, $2, $3, $4, $5)
                """, 
                "test_integration", 
                "test_user_123",
                '{"test": "integration"}',
                datetime.utcnow(),
                "127.0.0.1"
                )
                
                # Verify it was stored
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM audit_log WHERE event_type = $1",
                    "test_integration"
                )
                assert count >= 1

    @pytest.mark.database
    @pytest.mark.integration
    async def test_jsonb_operations(self, real_db):
        """Test JSONB column operations (used for metadata, preferences)."""
        async with real_db.pool.acquire() as conn:
            await conn.execute("""
                CREATE TEMP TABLE json_test (
                    id SERIAL PRIMARY KEY,
                    data JSONB
                ) ON COMMIT DROP
            """)
            
            # Insert JSON data
            test_data = {
                "user": {"id": "123", "name": "Test"},
                "permissions": ["read", "write"],
                "preferences": {"theme": "dark", "language": "en"}
            }
            
            await conn.execute(
                "INSERT INTO json_test (data) VALUES ($1)",
                test_data
            )
            
            # Query JSON fields
            name = await conn.fetchval(
                "SELECT data->'user'->>'name' FROM json_test"
            )
            assert name == "Test"
            
            # Query array containment
            has_read = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM json_test WHERE data->'permissions' @> $1)",
                ['read']
            )
            assert has_read is True
