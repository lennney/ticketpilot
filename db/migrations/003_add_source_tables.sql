-- Migration 003: Add source tables for FAQ, Policy, Case documents
-- Description: Creates physically separate source document tables and adds
--   referential columns (source_table, source_id) to knowledge_chunks.
--   This implements the two-layer architecture:
--     Source layer: knowledge_faq, knowledge_policy, knowledge_case
--     Chunk layer:  knowledge_chunks (unified)
--
-- Design: openspec/changes/close-project-audit-blockers/design.md

-- ============================================================
-- Source Tables
-- ============================================================

-- FAQ documents: intent_tags preserved for classification-to-source routing
CREATE TABLE IF NOT EXISTS knowledge_faq (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_domain VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL CONSTRAINT faq_content_not_empty CHECK (length(content) > 0),
    intent_tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Policy documents: policy_code preserved for exact-match lookup (e.g. "7.3.2")
CREATE TABLE IF NOT EXISTS knowledge_policy (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_domain VARCHAR(50) NOT NULL,
    policy_code VARCHAR(20) NOT NULL CONSTRAINT policy_code_format CHECK (policy_code ~ '^\d+\.\d+\.\d+$'),
    title TEXT NOT NULL,
    content TEXT NOT NULL CONSTRAINT policy_content_not_empty CHECK (length(content) > 0),
    effective_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Case documents: risk_level, compensation_amount preserved for prioritization
CREATE TABLE IF NOT EXISTS knowledge_case (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_domain VARCHAR(50) NOT NULL,
    case_id VARCHAR(100) NOT NULL,
    issue_summary TEXT NOT NULL,
    resolution TEXT NOT NULL,
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('low', 'medium', 'high')),
    compensation_amount DECIMAL(10, 2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for source tables
CREATE INDEX IF NOT EXISTS idx_faq_business_domain ON knowledge_faq(business_domain);
CREATE INDEX IF NOT EXISTS idx_faq_intent_tags ON knowledge_faq USING GIN(intent_tags);
CREATE INDEX IF NOT EXISTS idx_policy_business_domain ON knowledge_policy(business_domain);
CREATE INDEX IF NOT EXISTS idx_policy_code ON knowledge_policy(policy_code);
CREATE INDEX IF NOT EXISTS idx_case_business_domain ON knowledge_case(business_domain);
CREATE INDEX IF NOT EXISTS idx_case_risk_level ON knowledge_case(risk_level);

-- ============================================================
-- Add source references to knowledge_chunks
-- ============================================================

-- Add source_table column (which source table this chunk came from)
ALTER TABLE knowledge_chunks
    ADD COLUMN IF NOT EXISTS source_table VARCHAR(20);

-- Add source_id column (FK to the specific source row)
ALTER TABLE knowledge_chunks
    ADD COLUMN IF NOT EXISTS source_id UUID;

-- Index for source lookups
CREATE INDEX IF NOT EXISTS idx_chunks_source
    ON knowledge_chunks(source_table, source_id);

-- ============================================================
-- Comments
-- ============================================================

COMMENT ON TABLE knowledge_faq IS 'FAQ documents — source layer. Chunks derived from these go into knowledge_chunks.';
COMMENT ON TABLE knowledge_policy IS 'Policy documents — source layer. Chunks derived from these go into knowledge_chunks.';
COMMENT ON TABLE knowledge_case IS 'Case documents — source layer. Chunks derived from these go into knowledge_chunks.';
COMMENT ON COLUMN knowledge_chunks.source_table IS 'Source table name: knowledge_faq, knowledge_policy, or knowledge_case';
COMMENT ON COLUMN knowledge_chunks.source_id IS 'UUID reference to the source document row';
COMMENT ON COLUMN knowledge_faq.intent_tags IS 'Tags for intent-to-source routing (e.g., refund, account)';
COMMENT ON COLUMN knowledge_policy.policy_code IS 'Policy code in X.Y.Z format for exact-match lookup';
COMMENT ON COLUMN knowledge_case.compensation_amount IS 'Compensation amount if applicable, NULL if none';
