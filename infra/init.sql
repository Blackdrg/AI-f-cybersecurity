-- AI-f Database Initialization Script
-- Production-ready schema for PostgreSQL 15 + pgvector

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 0. Row Level Security (RLS) Policies
-- ============================================
-- Multi-tenant isolation: Every table with org_id or user_id must enforce row-level access
-- RLS ensures that even if application logic fails, one org cannot see another's data

-- Enable RLS on all tables with org_id
ALTER TABLE persons ENABLE ROW LEVEL SECURITY;
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE cameras ENABLE ROW LEVEL SECURITY;
ALTER TABLE recognition_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE org_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE support_tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE model_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE edge_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE ota_updates ENABLE ROW LEVEL SECURITY;
ALTER TABLE federated_updates ENABLE ROW LEVEL SECURITY;
ALTER TABLE bias_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE enrichment_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policy for persons: Users can only see persons in their org
CREATE POLICY persons_org_isolation ON persons
    FOR ALL
    USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- RLS Policy for embeddings: Restrict by org via person relationship
CREATE POLICY embeddings_org_isolation ON embeddings
    FOR ALL
    USING (EXISTS (
        SELECT 1 FROM persons p 
        WHERE p.person_id = embeddings.person_id 
        AND p.org_id = current_setting('app.current_org_id', true)::uuid
    ));

-- RLS Policy for cameras: Org isolation
CREATE POLICY cameras_org_isolation ON cameras
    FOR ALL
    USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- RLS Policy for recognition_events: Org isolation
CREATE POLICY recognition_events_org_isolation ON recognition_events
    FOR ALL
    USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- RLS Policy for users: Self-isolation (users see own record; admins see org members via separate endpoint)
-- Note: users table is NOT org-scoped universally (global SaaS accounts)
-- Row access controlled via middleware, not RLS

-- RLS Policy for org_members: Member can see other members in same org
CREATE POLICY org_members_org_isolation ON org_members
    FOR ALL
    USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- RLS Policy for api_keys: Org isolation
CREATE POLICY api_keys_org_isolation ON api_keys
    FOR ALL
    USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- RLS Policy for subscriptions: User can only see own subscription (except admins)
-- This is partially enforced via middleware + RLS for extra safety
CREATE POLICY subscriptions_user_isolation ON subscriptions
    FOR ALL
    USING (user_id = current_setting('app.current_user_id', true));

-- RLS Policy for usage: User can only see own usage
CREATE POLICY usage_user_isolation ON usage
    FOR ALL
    USING (user_id = current_setting('app.current_user_id', true));

-- RLS Policy for model_versions: Global read (all orgs can see production models), write admin-only
CREATE POLICY model_versions_global_read ON model_versions
    FOR SELECT
    USING (status = 'production' OR current_setting('app.current_role', true) IN ('admin', 'super_admin'));

-- RLS Policy for bias_reports: Org isolation
CREATE POLICY bias_reports_org_isolation ON bias_reports
    FOR ALL
    USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- RLS Policy for audit_logs: Org isolation (audit logs tied to org via person or camera)
CREATE POLICY audit_logs_org_isolation ON audit_logs
    FOR ALL
    USING (
        person_id IS NULL OR 
        EXISTS (
            SELECT 1 FROM persons p 
            WHERE p.person_id = audit_logs.person_id 
            AND p.org_id = current_setting('app.current_org_id', true)::uuid
        )
    );

-- ============================================
-- 1. Core Identity Tables
-- ============================================

CREATE TABLE IF NOT EXISTS persons (
    person_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    name TEXT,
    age INTEGER,
    gender TEXT,
    metadata JSONB,
    consent_record_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_persons_org ON persons(org_id);

-- ============================================
-- 2. Biometric Vectors
-- ============================================

CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID REFERENCES persons(person_id) ON DELETE CASCADE,
    embedding VECTOR(512),
    voice_embedding VECTOR(192),
    gait_embedding VECTOR(7),
    camera_id TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- HNSW index for fast vector search
CREATE INDEX IF NOT EXISTS embedding_idx ON embeddings 
USING hnsw (embedding vector_cosine_ops) 
WITH (m=16, ef_construction=64);

CREATE INDEX IF NOT EXISTS idx_embeddings_person ON embeddings(person_id);

-- ============================================
-- 3. Audit Log (Hash-Chain Ledger)
-- ============================================

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    action TEXT NOT NULL,
    person_id UUID,
    details JSONB,
    previous_hash TEXT,
    hash TEXT,
    zkp_proof JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_person ON audit_log(person_id);

-- ============================================
-- 4. Users & SaaS
-- ============================================

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    full_name TEXT,
    hashed_password TEXT,
    subscription_tier TEXT DEFAULT 'free',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS organizations (
    org_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    subscription_tier TEXT DEFAULT 'free',
    billing_email TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS org_members (
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    role TEXT DEFAULT 'viewer',
    joined_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (org_id, user_id)
);

CREATE TABLE IF NOT EXISTS api_keys (
    key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    api_key TEXT UNIQUE NOT NULL,
    name TEXT,
    scopes JSONB,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- 5. Cameras & Streams
-- ============================================

CREATE TABLE IF NOT EXISTS cameras (
    camera_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    rtsp_url TEXT,
    location TEXT,
    status TEXT DEFAULT 'offline',
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- 6. Recognition Timeline
-- ============================================

CREATE TABLE IF NOT EXISTS recognition_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    camera_id UUID REFERENCES cameras(camera_id),
    person_id UUID REFERENCES persons(person_id),
    confidence_score FLOAT,
    risk_score FLOAT,
    image_path TEXT,
    metadata JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recognition_org ON recognition_events(org_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_recognition_camera ON recognition_events(camera_id);
CREATE INDEX IF NOT EXISTS idx_recognition_person ON recognition_events(person_id);

-- ============================================
-- 7. Alerts & Incidents
-- ============================================

CREATE TABLE IF NOT EXISTS alert_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    condition JSONB,
    actions JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID REFERENCES alert_rules(rule_id) ON DELETE CASCADE,
    event_id UUID REFERENCES recognition_events(event_id),
    status TEXT DEFAULT 'new',
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- 8. Feedback & Learning
-- ============================================

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID,
    recognition_id UUID,
    correct_person_id UUID,
    confidence_score FLOAT,
    feedback_type TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- 9. SaaS Billing
-- ============================================

CREATE TABLE IF NOT EXISTS plans (
    plan_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    features JSONB,
    limits JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO plans (plan_id, name, price, features, limits)
VALUES 
('free', 'Free Starter', 0.00, '["Basic Recognition", "10 Enrollments", "Standard Support"]', '{"recognitions": 100, "enrollments": 10}'),
('pro', 'Pro Developer', 29.00, '["Advanced Recognition", "1000 Enrollments", "Priority Support", "Public Enrichment"]', '{"recognitions": 10000, "enrollments": 1000}'),
('enterprise', 'Enterprise Scale', 199.00, '["Unlimited Recognition", "Infinite Enrollments", "24/7 Dedicated Support", "Advanced Analytics", "ZKP Security"]', '{"recognitions": -1, "enrollments": -1}')
ON CONFLICT (plan_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id),
    plan_id TEXT REFERENCES plans(plan_id),
    status TEXT DEFAULT 'active',
    stripe_customer_id TEXT,              -- Stripe customer ID
    stripe_subscription_id TEXT,          -- Stripe subscription ID
    starts_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_customer ON subscriptions(stripe_customer_id);

CREATE TABLE IF NOT EXISTS payments (
    payment_id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id),
    amount DECIMAL(10,2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    status TEXT DEFAULT 'pending',
    stripe_payment_id TEXT,
    stripe_invoice_id TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS usage (
    user_id TEXT REFERENCES users(user_id),
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    recognitions_used INTEGER DEFAULT 0,
    enrollments_used INTEGER DEFAULT 0,
    recognitions_limit INTEGER,
    enrollments_limit INTEGER,
    PRIMARY KEY (user_id, period_start, period_end)
);

CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id),
    subject TEXT NOT NULL,
    description TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'open',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- 10. Model Registry (OTA)
-- ============================================

CREATE TABLE IF NOT EXISTS model_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(100) NOT NULL,
    framework VARCHAR(50) NOT NULL,
    architecture TEXT,
    input_shape INTEGER[],
    output_dim INTEGER,
    description TEXT,
    training_dataset TEXT,
    metrics JSONB,
    model_path TEXT NOT NULL,
    size_bytes BIGINT,
    checksum CHAR(64) NOT NULL,
    signature TEXT,
    status VARCHAR(50) DEFAULT 'staging',
    tags JSONB DEFAULT '[]',
    min_requirements JSONB DEFAULT '{}',
    uploaded_by TEXT REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    download_count INTEGER DEFAULT 0,
    promoted_at TIMESTAMP,
    CONSTRAINT unique_name_version UNIQUE(name, version)
);

CREATE INDEX IF NOT EXISTS idx_model_versions_name ON model_versions(name);
CREATE INDEX IF NOT EXISTS idx_model_versions_status ON model_versions(status);

-- ============================================
-- 11. Edge & OTA
-- ============================================

CREATE TABLE IF NOT EXISTS edge_devices (
    device_id TEXT PRIMARY KEY,
    model_version UUID REFERENCES model_versions(version_id),
    last_seen TIMESTAMP DEFAULT NOW(),
    status TEXT,
    pending_update UUID REFERENCES model_versions(version_id),
    capabilities JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS ota_updates (
    update_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id TEXT NOT NULL,
    model_version UUID REFERENCES model_versions(version_id) NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    dispatched_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_ota_device ON ota_updates(device_id, status);

CREATE TABLE IF NOT EXISTS federated_updates (
    update_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id TEXT,
    model_gradients JSONB,
    num_samples INTEGER,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- 12. Public Enrichment & Audits
-- ============================================

CREATE TABLE IF NOT EXISTS consents (
    consent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id TEXT,
    consent_text_version TEXT,
    granted_at TIMESTAMPTZ,
    granted_by TEXT,
    ip_addr TEXT,
    token TEXT,
    expires_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS enrichment_results (
    enrich_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query TEXT,
    subject TEXT,
    summary JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,
    requested_by TEXT,
    purpose TEXT
);

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action TEXT,
    user_id TEXT,
    target_enrich_id UUID,
    provider_calls JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- 13. System Config & Health
-- ============================================

CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value JSONB,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS system_health (
    id SERIAL PRIMARY KEY,
    service_name TEXT NOT NULL,
    status TEXT NOT NULL,
    latency_ms FLOAT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_system_health_service ON system_health(service_name, created_at);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash TEXT,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);

-- ============================================
-- 14. MFA (Multi-Factor Auth)
-- ============================================

CREATE TABLE IF NOT EXISTS mfa_secrets (
    id SERIAL PRIMARY KEY,
    user_id TEXT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    secret TEXT NOT NULL,
    backup_codes_hash JSONB NOT NULL,
    backup_codes_used JSONB DEFAULT '[]',
    enabled BOOLEAN DEFAULT FALSE,
    enabled_at TIMESTAMP,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mfa_attempts (
    id SERIAL PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    attempt_type TEXT,
    success BOOLEAN,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mfa_attempts_user ON mfa_attempts(user_id, created_at);

-- ============================================
-- 15. Bias & Fairness
-- ============================================

CREATE TABLE IF NOT EXISTS bias_reports (
    report_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id),
    report_date DATE NOT NULL,
    metrics JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bias_reports_org ON bias_reports(org_id, report_date);

-- ============================================
-- 16. Consent Logs (GDPR)
-- ============================================

CREATE TABLE IF NOT EXISTS consent_logs (
    consent_record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID,
    timestamp TIMESTAMP DEFAULT NOW(),
    client_id TEXT,
    consent_text_version TEXT,
    captured_ip TEXT,
    signed_token TEXT
);

-- END OF SCHEMA