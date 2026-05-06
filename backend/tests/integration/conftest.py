"""Integration test configuration and fixtures.

This module provides fixtures for integration tests that require real
external services (PostgreSQL, Redis, ONNX models, etc.) rather than mocks.
"""

import os
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from datetime import datetime
from pathlib import Path

# Import real database client for integration tests
import sys
import os
# Add backend directory to path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

try:
    from app.db.db_client import DBClient
    from app.security.encryption import EncryptionService
except ImportError as e:
    # These are optional for integration tests - if unavailable, fixtures will skip
    DBClient = None
    EncryptionService = None


# =============================================================================
# Environment Setup for Integration Tests
# =============================================================================
os.environ.setdefault('ENVIRONMENT', 'integration')
os.environ.setdefault('JWT_SECRET', 'integration-test-jwt-secret-64byte-long-string')
os.environ.setdefault('ENCRYPTION_KEY', '0XKYdoZg1Q4f1mXPIWwEVRwQcGm0sKomFk4N5ksJ2nA=')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')
os.environ.setdefault('MODEL_CACHE_DIR', '/tmp/models')
os.environ.setdefault('CI', 'true')


# =============================================================================
# Database Fixtures (Real PostgreSQL + pgvector)
# =============================================================================

@pytest.fixture(scope="session")
async def real_db() -> AsyncGenerator[DBClient, None]:
    """Provide a real database connection for integration tests.
    
    Requires:
    - PostgreSQL with pgvector extension running (see docker-compose.yml)
    - DATABASE_URL environment variable set
    
    The database is cleaned between tests using transaction rollback.
    """
    if DBClient is None:
        pytest.skip("DBClient not available - app modules not importable")
        return
    
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        pytest.skip("DATABASE_URL not set - skipping integration test")
    
    db = DBClient(database_url=db_url)
    await db.init_db()
    
    # Store original isolation level and set to serializable for test isolation
    async with db.pool.acquire() as conn:
        await conn.execute("BEGIN")
    
    yield db
    
    # Rollback all changes
    async with db.pool.acquire() as conn:
        await conn.execute("ROLLBACK")
    
    await db.close()


@pytest.fixture
async def db_transaction(real_db: DBClient) -> AsyncGenerator[DBClient, None]:
    """Provide a database client in a transaction that will be rolled back."""
    async with real_db.pool.acquire() as conn:
        await conn.execute("BEGIN")
        yield real_db
        await conn.execute("ROLLBACK")


# =============================================================================
# Redis Fixtures (Real Redis Cluster)
# =============================================================================

@pytest.fixture(scope="session")
async def real_redis() -> AsyncGenerator:
    """Provide a real Redis connection for integration tests."""
    try:
        import redis.asyncio as redis
    except ImportError:
        pytest.skip("redis-py not installed")
        return
    
    client = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))
    try:
        await client.ping()
        yield client
    except Exception:
        pytest.skip("Redis not available - skipping integration test")
        return
    finally:
        await client.close()


# =============================================================================
# ONNX Model Fixtures (Real Model Loading)
# =============================================================================

@pytest.fixture(scope="session")
def face_detection_model():
    """Load the real face detection ONNX model (retinaface or fallback)."""
    import onnxruntime as ort
    from pathlib import Path
    
    # Try retinaface first, fall back to buffalo_l (which does both detection + embedding)
    bundle_path = Path(os.environ.get('MODEL_PATH', 'backend/models/onnx_bundle'))
    model_path = bundle_path / 'retinaface.onnx'
    if not model_path.exists():
        model_path = bundle_path / 'insightface_buffalo_l.onnx'
    
    if not model_path.exists():
        pytest.skip(f"Face detection model not found in {bundle_path}")
    
    session = ort.InferenceSession(str(model_path), providers=['CPUExecutionProvider'])
    yield session
    del session


@pytest.fixture(scope="session")
def face_embedding_model():
    """Load the real face embedding ONNX model."""
    import onnxruntime as ort
    from pathlib import Path
    
    # Use insightface_buffalo_l which includes face recognition
    model_path = Path(os.environ.get('MODEL_PATH', 'backend/models/onnx_bundle')) / 'insightface_buffalo_l.onnx'
    if not model_path.exists():
        pytest.skip(f"Face embedding model not found at {model_path}")
    
    session = ort.InferenceSession(str(model_path), providers=['CPUExecutionProvider'])
    yield session
    del session


# =============================================================================
# Vector Search Fixtures (FAISS + pgvector)
# =============================================================================

@pytest.fixture(scope="session")
def faiss_index():
    """Create a real FAISS HNSW index for testing."""
    try:
        import faiss
    except ImportError:
        pytest.skip("faiss-cpu not installed")
        return None
    
    dimension = 512  # ArcFace embedding dimension
    index = faiss.IndexHNSWFlat(dimension, 32)  # M=32, typical value
    index.hnsw.efConstruction = 40
    index.hnsw.efSearch = 16
    yield index
    # FAISS index cleanup is implicit


@pytest.fixture
async def populated_vector_db(real_db, face_embedding_model) -> DBClient:
    """Populate the database with synthetic face embeddings for search testing."""
    import numpy as np
    from pathlib import Path
    
    # Generate synthetic embeddings and insert into DB
    num_vectors = 1000
    dimension = 512
    
    async with real_db.pool.acquire() as conn:
        # Create temporary embeddings table if not exists
        await conn.execute("""
            CREATE TEMP TABLE test_embeddings (
                person_id UUID,
                embedding vector(512),
                created_at TIMESTAMPTZ DEFAULT NOW()
            ) ON COMMIT DROP
        """)
        
        # Insert synthetic embeddings
        for i in range(num_vectors):
            person_id = f"test_person_{i}"
            embedding = np.random.randn(dimension).astype(np.float32)
            embedding = embedding / np.linalg.norm(embedding)  # L2 normalize
            
            await conn.execute(
                "INSERT INTO test_embeddings (person_id, embedding) VALUES ($1, $2)",
                person_id, embedding.tolist()
            )
        
        # Create HNSW index on the temp table
        await conn.execute("""
            CREATE INDEX ON test_embeddings 
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 32, ef_construction = 40)
        """)
    
    yield real_db
    # Temp table drops automatically on commit/rollback


# =============================================================================
# Encryption Service Fixture
# =============================================================================

@pytest.fixture(scope="session")
def encryption_service():
    """Provide a real encryption service for integration tests."""
    try:
        from app.security.encryption import EncryptionService
    except ImportError:
        pytest.skip("EncryptionService not available")
        return None
    
    key = os.environ.get('ENCRYPTION_KEY', '0XKYdoZg1Q4f1mXPIWwEVRwQcGm0sKomFk4N5ksJ2nA=')
    return EncryptionService(key.encode())


# =============================================================================
# Test Data Generators
# =============================================================================

def generate_test_face_image(size=(112, 112)):
    """Generate a synthetic face-like image for testing."""
    import cv2
    import numpy as np
    
    img = np.zeros((*size, 3), dtype=np.uint8)
    # Draw a simple face-like pattern
    cv2.ellipse(img, (size[0]//2, size[1]//2), (40, 50), 0, 0, 360, (200, 200, 200), -1)
    cv2.circle(img, (size[0]//2 - 20, size[1]//2 - 20), 8, (0, 0, 0), -1)  # Left eye
    cv2.circle(img, (size[0]//2 + 20, size[1]//2 - 20), 8, (0, 0, 0), -1)  # Right eye
    cv2.ellipse(img, (size[0]//2, size[1]//2 + 20), (15, 10), 0, 0, 360, (0, 0, 0), -1)  # Mouth
    return img


def generate_test_embedding(dimension=512) -> list:
    """Generate a normalized synthetic embedding vector."""
    import numpy as np
    vec = np.random.randn(dimension).astype(np.float32)
    vec = vec / np.linalg.norm(vec)
    return vec.tolist()


# =============================================================================
# Markers
# =============================================================================

def pytest_configure(config):
    """Register custom pytest markers for integration tests."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", "database: marks tests that require a real database"
    )
    config.addinivalue_line(
        "markers", "redis: marks tests that require a real Redis instance"
    )
    config.addinivalue_line(
        "markers", "models: marks tests that load real ONNX models"
    )
    config.addinivalue_line(
        "markers", "vector_search: marks tests that use FAISS or pgvector"
    )
    config.addinivalue_line(
        "markers", "slow_integration: marks slow integration tests"
    )
