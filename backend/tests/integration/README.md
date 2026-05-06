# Integration Test Suite

This directory contains integration tests for the AI-f backend that test real interactions between components and external services.

## Test Categories

### Database Integration (`test_database.py`)
- Real PostgreSQL + pgvector operations
- Vector storage and retrieval
- HNSW index performance
- Transaction isolation
- Concurrent access patterns
- JSONB operations

### ONNX Model Integration (`test_onnx_models.py`)
- Real model loading from `models/onnx_bundle/`
- Inference latency and throughput
- Input/output schema validation
- Model consistency across runs
- Performance benchmarks (< 100ms avg latency)

### Vector Search (`test_vector_search.py`)
- FAISS HNSW index creation and search
- pgvector cosine and L2 similarity
- Index performance at scale (10K vectors)
- Distance metric accuracy
- Batch insert throughput

### Redis Integration (`test_redis.py`)
- Connection and cluster mode
- Sliding window rate limiting
- JWT revocation store
- Pub/Sub messaging
- Lua script atomic operations
- LRU cache patterns

### End-to-End Pipeline (`test_recognition_e2e.py`)
- Full enrollment → recognition flow
- Multi-modal fusion (face+voice+gait)
- Audit log integrity
- Encryption at rest
- Concurrent request handling
- Cache invalidation

### Stripe Webhooks (`test_webhooks_integration.py`)
- Webhook signature verification
- Checkout session completion
- Subscription lifecycle
- Payment intent processing
- Event idempotency
- Persistent event logging

### Celery Tasks (`test_celery.py`)
- Task enqueue and execution
- Result backend persistence
- Retry logic and error handling
- Priority queues
- Chord execution
- Task revocation

### API Contract (`test_api_contract.py`)
- OpenAPI schema validation
- Request/response schema conformance
- Error response validation
- All 137+ endpoints covered

## Prerequisites

### Services Required
1. **PostgreSQL 15** with pgvector extension
   ```bash
   docker run -d \
     -e POSTGRES_DB=face_recognition \
     -e POSTGRES_PASSWORD=password \
     -p 5432:5432 \
     pgvector/pgvector:pg15
   ```

2. **Redis** (single or cluster)
   ```bash
   docker run -d -p 6379:6379 redis:7.2.3-alpine
   ```

3. **ONNX Models** in `backend/models/onnx_bundle/`
   - `face_detection.onnx`
   - `face_embedding.onnx`
   - `anti_spoof.onnx` (optional)

### Environment Variables
```bash
export DATABASE_URL=postgresql://postgres:password@localhost:5432/face_recognition
export REDIS_URL=redis://localhost:6379
export MODEL_PATH=backend/models/onnx_bundle
export JWT_SECRET=integration-test-secret
export ENCRYPTION_KEY=base64_key_here
export CI=true
```

## Running Integration Tests

### All Integration Tests
```bash
cd backend
python run_integration_tests.py
```

### Skip Slow Tests
```bash
python run_integration_tests.py --skip-slow
```

### With Coverage
```bash
python run_integration_tests.py --coverage
```

### Specific Test File
```bash
pytest tests/integration/test_database.py -v
```

### Specific Test
```bash
pytest tests/integration/test_database.py::TestDatabaseIntegration::test_pgvector_extension_loaded -v
```

### With Docker Compose
```bash
docker-compose -f infra/docker-compose.yml up -d postgres redis
python run_integration_tests.py
```

## Test Markers

| Marker | Description |
|--------|-------------|
| `integration` | All integration tests |
| `database` | Requires real PostgreSQL |
| `redis` | Requires real Redis |
| `models` | Loads real ONNX models |
| `vector_search` | Uses FAISS or pgvector |
| `slow_integration` | Takes >30 seconds |
| `billing` | Stripe integration |
| `webhooks` | Webhook processing |
| `celery` | Task queue tests |

Run with marker selection:
```bash
pytest -m "database and not slow_integration"
pytest -m "models"
pytest -m "integration and not slow_integration"  # Fast integration suite
```

## Expected Performance

### Database
- Vector insert (bulk 1000): < 2s
- HNSW query (10 results): < 500ms
- Connection pool (50 concurrent): < 100ms avg

### ONNX Models (CPU)
- Face detection: 45-60ms
- Face embedding: 20-30ms
- Spoof detection: 30-50ms

### Vector Search
- FAISS 10K vectors: < 2ms query
- pgvector 10K vectors: < 500ms query (with HNSW)

### Redis
- Simple GET/SET: < 1ms
- Sliding window rate limit: < 3ms
- Pub/Sub latency: < 5ms

## CI/CD Integration

Integration tests run in the `ci.yml` workflow:
- Lint → Unit Tests → Integration Tests → Security Scan → Build
- Requires services: PostgreSQL (pgvector), Redis cluster
- Coverage threshold: 85% for integration code

To run in CI:
```yaml
- name: Run Integration Tests
  run: |
    docker-compose -f infra/docker-compose.yml up -d
    sleep 10  # Wait for services
    cd backend && python run_integration_tests.py --coverage
```

## Troubleshooting

### Tests Skipped
- Check that services are running: `docker ps`
- Verify environment variables set: `env | grep -E 'DATABASE_URL|REDIS_URL|MODEL_PATH'`
- Ensure ONNX models exist in specified path

### Database Connection Errors
```bash
# Check Postgres is up
pg_isready -h localhost -p 5432

# Verify pgvector extension
psql -d face_recognition -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

### Redis Connection Errors
```bash
redis-cli ping
# Should return PONG
```

### Model Loading Errors
```bash
ls backend/models/onnx_bundle/
# Should contain .onnx files
```

## Adding New Integration Tests

1. Create file in `tests/integration/` with `test_*.py` prefix
2. Use fixtures from `conftest.py`:
   - `real_db` - real database connection
   - `real_redis` - real redis client
   - `face_detection_model` - loaded ONNX model
   - `faiss_index` - FAISS index instance
   - `encryption_service` - encryption utility
3. Mark with `@pytest.mark.integration` and other relevant markers
4. Ensure cleanup in fixtures (use temp tables, rollback transactions)
5. Document test purpose and expectations

## Notes

- Integration tests are **SLOW** (30s-2min each) - use selectively
- They require **REAL SERVICES** - cannot run in isolation
- Use `--skip-slow` flag for fast feedback during development
- Database tests use transactions and rollback for isolation
- Redis tests clean up after themselves (KEY deletion)
- Model tests load once per session (scope="session")
