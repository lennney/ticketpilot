-- Migration: Create embedding_index_metadata table
-- Description: Tracks which provider/model/dimension built the current embeddings.
--              Created on first rebuild via Python code if table does not exist.
--              This migration ensures the table exists for Docker-based deployments.

CREATE TABLE IF NOT EXISTS embedding_index_metadata (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_name VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    dimension INTEGER NOT NULL,
    batch_size INTEGER NOT NULL DEFAULT 32,
    built_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    source_record_count INTEGER NOT NULL DEFAULT 0,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    embedding_count INTEGER NOT NULL DEFAULT 0,
    config_fingerprint VARCHAR(64) NOT NULL,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE embedding_index_metadata IS 'Records each embedding index build: provider, model, dimension, and counts';
COMMENT ON COLUMN embedding_index_metadata.config_fingerprint IS 'SHA-256(provider|model|dimension) hex digest (first 16 chars) for quick config comparison';
