-- Migration: Create knowledge_chunks table with pgvector support
-- Description: Table for storing knowledge chunks with embeddings for hybrid retrieval

-- Enable pgvector extension if not exists
CREATE EXTENSION IF NOT EXISTS vector;

-- Create knowledge_chunks table
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID NOT NULL,
    doc_type VARCHAR(20) NOT NULL CHECK (doc_type IN ('FAQ', 'POLICY', 'CASE')),
    parent_chunk_id UUID REFERENCES knowledge_chunks(id),
    chunk_level INTEGER NOT NULL CHECK (chunk_level IN (1, 2)),  -- 1=PARENT, 2=CHILD
    business_domain VARCHAR(50) NOT NULL,
    risk_level VARCHAR(20) CHECK (risk_level IN ('low', 'medium', 'high')),
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,  -- SHA-256 hex
    embedding VECTOR(384),  -- pgvector for embeddings
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT content_not_empty CHECK (length(content) > 0),
    CONSTRAINT hash_length CHECK (length(content_hash) = 64)
);

-- Create indexes for efficient retrieval

-- GIN index for full-text search with simple config
CREATE INDEX IF NOT EXISTS idx_chunks_fts
    ON knowledge_chunks
    USING GIN (to_tsvector('simple', content));

-- Index for doc_id lookups
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id
    ON knowledge_chunks(doc_id);

-- Index for doc_type filtering
CREATE INDEX IF NOT EXISTS idx_chunks_doc_type
    ON knowledge_chunks(doc_type);

-- Index for parent chunk lookups (for parent-child relationships)
CREATE INDEX IF NOT EXISTS idx_chunks_parent
    ON knowledge_chunks(parent_chunk_id)
    WHERE parent_chunk_id IS NOT NULL;

-- HNSW index for vector search
-- Parameters: m=16, ef_construction=200
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw
    ON knowledge_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);

-- Composite index for common filter combinations
CREATE INDEX IF NOT EXISTS idx_chunks_doc_type_business
    ON knowledge_chunks(doc_type, business_domain);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    -- Note: knowledge_chunks doesn't have updated_at, this is for future use
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Comments for documentation
COMMENT ON TABLE knowledge_chunks IS 'Knowledge chunks with embeddings for hybrid retrieval';
COMMENT ON COLUMN knowledge_chunks.embedding IS '384-dimensional embedding vector for semantic search';
COMMENT ON INDEX idx_chunks_fts IS 'GIN index for full-text search with simple config';
COMMENT ON INDEX idx_chunks_embedding_hnsw IS 'HNSW index for vector similarity search';