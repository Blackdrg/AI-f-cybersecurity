-- pgvector extension setup and vector index optimization
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
SET hnsw.ef_search = 64;
SET hnsw.ef_construction = 128;
ALTER SYSTEM SET maintenance_work_mem = '512MB';
SELECT pg_reload_conf();
GRANT USAGE ON SCHEMA public TO ai_f_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO ai_f_user;
ANALYZE embeddings;
ANALYZE persons;
ANALYZE recognition_events;
SELECT 'pgvector configuration complete' AS status;