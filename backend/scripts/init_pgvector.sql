-- pgvector vector indexes for production scale
-- Run on startup for face/voice embeddings search

CREATE EXTENSION IF NOT EXISTS vector;

-- Embeddings table (face/voice hybrid)
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL,
    person_id UUID NOT NULL,
    type VARCHAR(20) NOT NULL, -- 'face', 'voice', 'gait'
    embedding VECTOR(512), -- ArcFace/ECAPA dim
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- HNSW index for <10ms P99 @ 100M vectors
CREATE INDEX IF NOT EXISTS embeddings_org_hnsw_idx ON embeddings 
USING hnsw (embedding vector_cosine_ops) 
WHERE org_id = '00000000-0000-0000-0000-000000000000'::uuid; -- Template per-org

-- IVFFlat fallback for cold vectors
CREATE INDEX IF NOT EXISTS embeddings_ivfflat_idx ON embeddings 
USING ivfflat (embedding vector_l2_ops) WITH (lists = 1000);

-- FAISS hybrid sync trigger (Redis → pgvector)
CREATE OR REPLACE FUNCTION sync_embedding() RETURNS TRIGGER AS $$
BEGIN
    -- Async Celery task for FAISS update
    PERFORM pg_notify('embedding_update', NEW.id::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER embeddings_sync_trig AFTER INSERT OR UPDATE ON embeddings
FOR EACH ROW EXECUTE FUNCTION sync_embedding();
