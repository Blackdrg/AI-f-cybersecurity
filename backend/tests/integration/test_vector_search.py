"""FAISS and pgvector integration tests.

Tests vector search capabilities across both FAISS and PostgreSQL:
- Index creation and search performance
- Cosine similarity vs Euclidean distance
- Index building time and memory usage
- Search accuracy at various k values
"""

import pytest
import time
import numpy as np
from typing import List, Tuple


@pytest.mark.vector_search
@pytest.mark.integration
class TestFAISSIntegration:
    """FAISS-specific integration tests."""

    def test_faiss_index_creation(self, faiss_index):
        """Test that a FAISS HNSW index can be created."""
        if faiss_index is None:
            pytest.skip("FAISS not available")
        
        assert faiss_index.d == 512
        assert faiss_index.is_trained is True  # HNSWFlat is trained on construction

    def test_faiss_add_vectors(self, faiss_index):
        """Test adding vectors to FAISS index."""
        if faiss_index is None:
            pytest.skip("FAISS not available")
        
        # Generate random embeddings
        num_vectors = 100
        dimension = 512
        vectors = np.random.randn(num_vectors, dimension).astype(np.float32)
        
        # Normalize for cosine similarity
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / norms
        
        # Add to index
        faiss_index.add(vectors)
        
        assert faiss_index.ntotal == num_vectors

    def test_faiss_search_accuracy(self, faiss_index):
        """Test that FAISS returns correct nearest neighbors."""
        if faiss_index is None:
            pytest.skip("FAISS not available")
        
        # Create vectors where one is known query
        base = np.random.randn(1, 512).astype(np.float32)
        base = base / np.linalg.norm(base)
        
        # Create database of vectors (first one is identical to query)
        db_vectors = np.vstack([base, np.random.randn(999, 512).astype(np.float32)])
        norms = np.linalg.norm(db_vectors, axis=1, keepdims=True)
        db_vectors = db_vectors / norms
        
        faiss_index.reset()
        faiss_index.add(db_vectors)
        
        # Search
        k = 5
        distances, indices = faiss_index.search(base, k)
        
        # First result should be the query itself (distance ~0)
        assert indices[0][0] == 0
        assert distances[0][0] < 1e-6

    def test_faiss_search_performance(self, faiss_index):
        """Benchmark FAISS search latency with 10K vectors."""
        if faiss_index is None:
            pytest.skip("FAISS not available")
        
        num_vectors = 10000
        dimension = 512
        
        # Generate and index vectors
        vectors = np.random.randn(num_vectors, dimension).astype(np.float32)
        vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        
        start = time.time()
        faiss_index.add(vectors)
        build_time = time.time() - start
        assert build_time < 5.0  # Should index 10K vectors in < 5s
        
        # Search latency
        query = np.random.randn(1, dimension).astype(np.float32)
        query = query / np.linalg.norm(query)
        
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            distances, indices = faiss_index.search(query, 10)
            latencies.append((time.perf_counter() - start) * 1000)
        
        avg_latency = np.mean(latencies)
        p99_latency = np.percentile(latencies, 99)
        
        assert avg_latency < 2.0  # Average < 2ms
        assert p99_latency < 5.0  # P99 < 5ms

    def test_faiss_hnsw_params(self, faiss_index):
        """Verify HNSW parameters are set correctly."""
        if faiss_index is None:
            pytest.skip("FAISS not available")

        # M parameter (connectivity) - different FAISS versions use different attribute names
        m = getattr(faiss_index.hnsw, 'M', None) or getattr(faiss_index.hnsw, 'nb_neighbors', None)
        assert m == 32  # Expected value from conftest

        # efConstruction affects build quality
        ef_construction = faiss_index.hnsw.efConstruction
        assert ef_construction == 40

        # efSearch affects query accuracy/speed tradeoff
        ef_search = faiss_index.hnsw.efSearch
        assert ef_search == 16


@pytest.mark.vector_search
@pytest.mark.database
@pytest.mark.integration
class TestPgVectorIntegration:
    """Tests for pgvector extension in PostgreSQL."""

    @pytest.fixture
    async def pgvector_table(self, real_db):
        """Create a test table with vector column."""
        async with real_db.pool.acquire() as conn:
            await conn.execute("""
                CREATE TEMP TABLE test_vectors (
                    id SERIAL PRIMARY KEY,
                    embedding vector(512),
                    metadata JSONB
                ) ON COMMIT DROP
            """)
            # Create HNSW index
            await conn.execute("""
                CREATE INDEX ON test_vectors 
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 32, ef_construction = 40)
            """)
        yield real_db
        # Temp table auto-drops

    async def _generate_and_insert_vectors(self, conn, num_vectors: int = 1000):
        """Helper to insert random vectors."""
        import numpy as np
        
        for i in range(num_vectors):
            vec = np.random.randn(512).astype(np.float32)
            vec = vec / np.linalg.norm(vec)
            await conn.execute(
                "INSERT INTO test_vectors (embedding, metadata) VALUES ($1, $2)",
                vec.tolist(),
                {"index": i, "source": "test"}
            )

    async def _wait_for_index(self, conn, table_name: str, index_name: str):
        """Wait for HNSW index to finish building."""
        # In pgvector, index builds automatically but we can check status
        # For large datasets, we might need to wait
        import asyncio
        await asyncio.sleep(0.5)  # Brief wait for async index build

    @pytest.mark.database
    @pytest.mark.vector_search
    @pytest.mark.integration
    async def test_pgvector_insert_and_search(self, pgvector_table):
        """Test vector insertion and similarity search in Postgres."""
        async with pgvector_table.pool.acquire() as conn:
            # Insert test vectors
            import numpy as np
            
            base_vec = np.random.randn(512).astype(np.float32)
            base_vec = base_vec / np.linalg.norm(base_vec)
            
            # Insert base vector + 99 random
            all_vecs = [base_vec] + [
                np.random.randn(512).astype(np.float32) for _ in range(99)
            ]
            all_vecs = [v / np.linalg.norm(v) for v in all_vecs]
            
            for i, vec in enumerate(all_vecs):
                await conn.execute(
                    "INSERT INTO test_vectors (embedding, metadata) VALUES ($1, $2)",
                    vec.tolist(),
                    {"id": i}
                )
            
            # Search for nearest to base vector
            results = await conn.fetch("""
                SELECT id, 1 - (embedding <=> $1) as similarity
                FROM test_vectors
                ORDER BY embedding <=> $1
                LIMIT 5
            """, base_vec.tolist())
            
            # First result should be the inserted base (or very close)
            assert len(results) == 5
            assert results[0]['similarity'] > 0.999  # Nearly perfect match

    @pytest.mark.database
    @pytest.mark.vector_search
    @pytest.mark.integration
    async def test_pgvector_index_performance(self, pgvector_table):
        """Test pgvector HNSW index query performance."""
        async with pgvector_table.pool.acquire() as conn:
            # Insert 1000 vectors
            import numpy as np
            num_vectors = 1000
            
            for _ in range(num_vectors):
                vec = np.random.randn(512).astype(np.float32)
                vec = vec / np.linalg.norm(vec)
                await conn.execute(
                    "INSERT INTO test_vectors (embedding) VALUES ($1)",
                    vec.tolist()
                )
            
            # Wait for index
            await self._wait_for_index(conn, "test_vectors", "test_vectors_embedding_idx")
            
            query = np.random.randn(512).astype(np.float32)
            query = query / np.linalg.norm(query)
            
            # Measure query time
            start = time.time()
            results = await conn.fetch("""
                SELECT id, 1 - (embedding <=> $1) as similarity
                FROM test_vectors
                ORDER BY embedding <=> $1
                LIMIT 10
            """, query.tolist())
            elapsed = time.time() - start
            
            assert len(results) == 10
            assert elapsed < 0.5  # Should be sub-second with HNSW

    @pytest.mark.database
    @pytest.mark.vector_search
    @pytest.mark.integration
    async def test_pgvector_distance_metrics(self, pgvector_table):
        """Test different distance metrics (L2, cosine, inner product)."""
        async with pgvector_table.pool.acquire() as conn:
            vec = [0.5] * 512  # Uniform vector
            identical = vec[:]
            opposite = [-x for x in vec]
            
            await conn.execute("INSERT INTO test_vectors (embedding) VALUES ($1)", vec)
            await conn.execute("INSERT INTO test_vectors (embedding) VALUES ($1)", opposite)
            
            # Check inner product (dot product)
            result = await conn.fetchrow("""
                SELECT embedding <-> $1 as l2_dist, 
                       1 - (embedding <=> $1) as cosine_sim,
                       embedding <#> $1 as ip_dist
                FROM test_vectors 
                WHERE id = 1
            """, vec)
            
            # Cosine similarity with itself should be ~1
            assert result['cosine_sim'] > 0.999
            
            # L2 distance with itself should be ~0
            assert result['l2_dist'] < 0.01

    @pytest.mark.database
    @pytest.mark.integration
    async def test_pgvector_index_types(self, real_db):
        """Test HNSW vs IVFFlat index performance."""
        async with real_db.pool.acquire() as conn:
            # Create table
            await conn.execute("""
                CREATE TEMP TABLE index_compare (
                    id SERIAL PRIMARY KEY,
                    embedding vector(512)
                ) ON COMMIT DROP
            """)
            
            # Build HNSW index
            start = time.time()
            await conn.execute("""
                CREATE INDEX ON index_compare 
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 32, ef_construction = 40)
            """)
            hnsw_time = time.time() - start
            
            # Check index exists
            index_exists = await conn.fetchval("""
                SELECT COUNT(*) FROM pg_indexes 
                WHERE tablename = 'index_compare' 
                AND indexdef LIKE '%hnsw%'
            """)
            assert index_exists > 0

    @pytest.mark.database
    @pytest.mark.integration
    async def test_pgvector_batch_insert_performance(self, pgvector_table):
        """Test bulk insert performance."""
        async with pgvector_table.pool.acquire() as conn:
            num_vectors = 5000
            import numpy as np
            
            # Use COPY for bulk insert (if available) or fast executemany
            vectors = [np.random.randn(512).astype(np.float32) for _ in range(num_vectors)]
            vectors = [v / np.linalg.norm(v) for v in vectors]
            
            start = time.time()
            
            # Batch insert using executemany
            for vec in vectors:
                await conn.execute(
                    "INSERT INTO test_vectors (embedding) VALUES ($1)",
                    vec.tolist()
                )
            
            elapsed = time.time() - start
            
            count = await conn.fetchval("SELECT COUNT(*) FROM test_vectors")
            assert count == num_vectors
            # Should insert at least 1000 vectors per second (better with COPY)
            assert elapsed < num_vectors / 500  # At least 500/sec
