-- ============================================================
-- Context Trust Layer: PostgreSQL Database Schema (14 Tables)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. organizations
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    domain_whitelist JSONB DEFAULT '[]'::jsonb,
    allowed_auth_methods JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(205) NOT NULL UNIQUE,
    role VARCHAR(50) NOT NULL DEFAULT 'auditor',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    avatar_url VARCHAR(500),
    title VARCHAR(100),
    department VARCHAR(100),
    hashed_password VARCHAR(255),
    is_verified BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. data_sources
CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_family VARCHAR(50) NOT NULL DEFAULT 'document',
    source_intent VARCHAR(50) NOT NULL DEFAULT 'governance_policy',
    external_id VARCHAR(255) NOT NULL UNIQUE,
    authority_level INTEGER NOT NULL DEFAULT 50,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    domain VARCHAR(100) DEFAULT 'General',
    owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
    connection_config JSONB DEFAULT '{}'::jsonb,
    scope_config JSONB DEFAULT '{}'::jsonb,
    capabilities JSONB DEFAULT '{}'::jsonb,
    last_synced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. documents
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    external_id VARCHAR(255),
    content_uri TEXT,
    content_hash VARCHAR(64) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    domain VARCHAR(100) DEFAULT 'General',
    owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. document_versions
CREATE TABLE IF NOT EXISTS document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL DEFAULT 1,
    content_uri TEXT,
    content_hash VARCHAR(64) NOT NULL,
    modified_at TIMESTAMPTZ,
    is_current BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. claims
CREATE TABLE IF NOT EXISTS claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    document_version_id UUID NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL,
    subject VARCHAR(500),
    predicate VARCHAR(500),
    object TEXT,
    claim_type VARCHAR(50) NOT NULL DEFAULT 'policy',
    extraction_method VARCHAR(50),
    extraction_model VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'verified',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7. claim_evidence
CREATE TABLE IF NOT EXISTS claim_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    evidence_type VARCHAR(50) DEFAULT 'direct_quote',
    page_number INTEGER,
    section TEXT,
    text_span TEXT NOT NULL,
    start_offset INTEGER,
    end_offset INTEGER,
    evidence_hash VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 8. claim_validity
CREATE TABLE IF NOT EXISTS claim_validity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    version VARCHAR(20) DEFAULT 'v1',
    is_current BOOLEAN NOT NULL DEFAULT true,
    validity_status VARCHAR(50) NOT NULL DEFAULT 'valid',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 9. claim_trust_scores
CREATE TABLE IF NOT EXISTS claim_trust_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    source_score NUMERIC(3,2) DEFAULT 0.95,
    freshness_score NUMERIC(3,2) DEFAULT 0.90,
    evidence_score NUMERIC(3,2) DEFAULT 0.92,
    consistency_score NUMERIC(3,2) DEFAULT 0.88,
    authority_score NUMERIC(3,2) DEFAULT 0.95,
    human_score NUMERIC(3,2) DEFAULT 1.00,
    overall_score NUMERIC(3,2) NOT NULL DEFAULT 0.92,
    scoring_model VARCHAR(50) DEFAULT 'multi_factor_v1',
    scoring_version VARCHAR(20) DEFAULT '1.0.0',
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 10. claim_conflicts
CREATE TABLE IF NOT EXISTS claim_conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_a_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    claim_b_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    conflict_type VARCHAR(50) NOT NULL DEFAULT 'value_mismatch',
    severity VARCHAR(20) NOT NULL DEFAULT 'high',
    confidence NUMERIC(5,4) DEFAULT 0.9500,
    resolution_status VARCHAR(50) NOT NULL DEFAULT 'detected',
    resolved_claim_id UUID REFERENCES claims(id) ON DELETE SET NULL,
    resolved_by UUID REFERENCES users(id) ON DELETE SET NULL,
    resolved_at TIMESTAMPTZ,
    conflicting_fields JSONB DEFAULT '[]'::jsonb,
    supporting_evidence JSONB DEFAULT '{}'::jsonb,
    source_authority JSONB DEFAULT '{}'::jsonb,
    applicable_scope JSONB DEFAULT '{}'::jsonb,
    effective_dates JSONB DEFAULT '{}'::jsonb,
    reviewer_decision VARCHAR(50),
    resolution_rationale TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_conflicts_claim_a ON claim_conflicts(claim_a_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_claim_b ON claim_conflicts(claim_b_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_status ON claim_conflicts(resolution_status);

-- 11. agents
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    agent_type VARCHAR(50) NOT NULL DEFAULT 'support_agent',
    model_provider VARCHAR(50) DEFAULT 'openai',
    model_name VARCHAR(100) DEFAULT 'gpt-4o',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 12. agent_requests
CREATE TABLE IF NOT EXISTS agent_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    trust_threshold NUMERIC(3,2) NOT NULL DEFAULT 0.85,
    max_results INTEGER DEFAULT 10,
    status VARCHAR(50) NOT NULL DEFAULT 'completed',
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 13. agent_context_items
CREATE TABLE IF NOT EXISTS agent_context_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES agent_requests(id) ON DELETE CASCADE,
    claim_id UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    rank INTEGER NOT NULL DEFAULT 1,
    trust_score NUMERIC(3,2) NOT NULL,
    included BOOLEAN NOT NULL DEFAULT true,
    exclusion_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 14. human_reviews
CREATE TABLE IF NOT EXISTS human_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    reviewer_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_type VARCHAR(50) NOT NULL,
    target_id UUID NOT NULL,
    decision VARCHAR(50) NOT NULL DEFAULT 'approved',
    reason TEXT,
    previous_score NUMERIC(3,2),
    new_score NUMERIC(3,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- BASELINE DATA: Organization 'demo' and Default Agent
-- ============================================================

DO $$
DECLARE
    v_org_id UUID := '11111111-1111-1111-1111-111111111111';
    v_user_id UUID := '22222222-2222-2222-2222-222222222222';
    v_agent_id UUID := '88888888-8888-8888-8888-888888888888';
BEGIN
    -- 1. organizations
    INSERT INTO organizations (id, name, slug, status)
    VALUES (v_org_id, 'demo', 'demo', 'active')
    ON CONFLICT (id) DO UPDATE SET name = 'demo', slug = 'demo';

    -- 2. users
    INSERT INTO users (id, organization_id, name, email, role, status)
    VALUES (v_user_id, v_org_id, 'Sarah Chen', 'sarah.chen@demo.local', 'admin', 'active')
    ON CONFLICT (id) DO NOTHING;

    -- 3. agents
    INSERT INTO agents (id, organization_id, name, description, agent_type, model_provider, model_name, status)
    VALUES 
        (v_agent_id, v_org_id, 'Autonomous AI Copilot', 'Enterprise contextual copilot for policy verification.', 'claude_mcp_client', 'mock', 'gpt-4o', 'active')
    ON CONFLICT (id) DO NOTHING;
END $$;

-- 15. organization_invites
CREATE TABLE IF NOT EXISTS organization_invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'developer',
    token VARCHAR(255) NOT NULL UNIQUE,
    invited_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_org_invites_org ON organization_invites(organization_id);
CREATE INDEX IF NOT EXISTS idx_org_invites_token ON organization_invites(token);
CREATE INDEX IF NOT EXISTS idx_org_invites_email ON organization_invites(email);

-- Alembic version tracking
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO alembic_version (version_num) VALUES ('aafacd791d21') ON CONFLICT DO NOTHING;
