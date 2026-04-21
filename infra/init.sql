-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- B2B & Organization Tables
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
    role TEXT DEFAULT 'viewer', -- admin, operator, viewer
    joined_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (org_id, user_id)
);

CREATE TABLE IF NOT EXISTS api_keys (
    key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    api_key TEXT UNIQUE NOT NULL,
    name TEXT,
    scopes JSONB, -- list of permissions
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Camera & Stream Management
CREATE TABLE IF NOT EXISTS cameras (
    camera_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    rtsp_url TEXT,
    location TEXT,
    status TEXT DEFAULT 'offline', -- online, offline, error
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Recognition Events (Timeline & Analytics)
CREATE TABLE IF NOT EXISTS recognition_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    camera_id UUID REFERENCES cameras(camera_id),
    person_id UUID REFERENCES persons(person_id),
    confidence_score FLOAT,
    image_path TEXT,
    metadata JSONB, -- landmarks, spoof_score, etc.
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Rule Engine & Alerts
CREATE TABLE IF NOT EXISTS alert_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    condition JSONB, -- e.g., {"person_type": "unknown", "camera_id": "..."}
    actions JSONB, -- e.g., [{"type": "email", "to": "..."}, {"type": "webhook", "url": "..."}]
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID REFERENCES alert_rules(rule_id) ON DELETE CASCADE,
    event_id UUID REFERENCES recognition_events(event_id),
    status TEXT DEFAULT 'new', -- new, acknowledged, resolved
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create tables for face recognition system
CREATE TABLE IF NOT EXISTS persons (
    person_id UUID PRIMARY KEY,
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    age INTEGER,
    gender TEXT,
    metadata JSONB,
    consent_record_id UUID,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id UUID PRIMARY KEY,
    person_id UUID REFERENCES persons(person_id) ON DELETE CASCADE,
    embedding VECTOR(512),
    voice_embedding VECTOR(192),
    gait_embedding VECTOR(128),
    camera_id TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Consent logs table
CREATE TABLE IF NOT EXISTS consent_logs (
    consent_record_id UUID PRIMARY KEY,
    person_id UUID,
    timestamp TIMESTAMP DEFAULT NOW(),
    client_id TEXT,
    consent_text_version TEXT,
    captured_ip TEXT,
    signed_token TEXT
);

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    action TEXT NOT NULL,
    person_id UUID,
    details JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Create feedback table for adaptive learning
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id UUID PRIMARY KEY,
    person_id UUID,
    recognition_id UUID,
    correct_person_id UUID,
    confidence_score FLOAT,
    feedback_type TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- SaaS Tables
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    subscription_tier TEXT DEFAULT 'free',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS plans (
    plan_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    features JSONB,
    limits JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Seed Plans
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
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id),
    amount DECIMAL(10,2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    status TEXT DEFAULT 'pending',
    stripe_payment_id TEXT,
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

-- Model versions for OTA
CREATE TABLE IF NOT EXISTS model_versions (
    version_id UUID PRIMARY KEY,
    model_data BYTEA,
    created_at TIMESTAMP DEFAULT NOW(),
    description TEXT
);

-- Edge devices
CREATE TABLE IF NOT EXISTS edge_devices (
    device_id TEXT PRIMARY KEY,
    model_version UUID REFERENCES model_versions(version_id),
    last_seen TIMESTAMP DEFAULT NOW(),
    status TEXT
);

-- Federated learning updates
CREATE TABLE IF NOT EXISTS federated_updates (
    update_id UUID PRIMARY KEY,
    device_id TEXT,
    model_gradients JSONB,
    num_samples INTEGER,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Public enrichment tables
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
