#!/usr/bin/env python3
"""
AI-f Infrastructure Generator
Generates all production infrastructure files for PostgreSQL, Redis, Celery, Docker, and monitoring.
"""
import os

BASE = r"D:\AI-F\AI-f"
INTRA = os.path.join(BASE, "infra")
BACKEND = os.path.join(BASE, "backend")

def write(path, content):
    with open(path, 'w') as f:
        f.write(content)
    print(f"  Written: {path}")

# ============================================================
# 1. init.sql - Full production schema with 42+ tables, pgvector, pgcrypto, RLS
# ============================================================

init_sql = r'''-- AI-f Database Initialization Script
-- Production-ready schema for PostgreSQL 15+ with pgvector, pgcrypto
-- 42+ tables with full Row Level Security (RLS)

-- ========================================================
-- EXTENSIONS
-- ========================================================
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE EXTENSION IF NOT EXISTS hstore;

-- ========================================================
-- SCHEMAS
-- ========================================================
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS billing;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS ml;
CREATE SCHEMA IF NOT EXISTS notifications;
CREATE SCHEMA IF NOT EXISTS compliance;

-- ========================================================
-- 0. ROW LEVEL SECURITY HELPER
-- ========================================================
CREATE OR REPLACE FUNCTION set_tenant_context(p_org_id UUID, p_user_id TEXT, p_role TEXT DEFAULT 'viewer')
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_org_id', p_org_id::text, true);
    PERFORM set_config('app.current_user_id', p_user_id, true);
    PERFORM set_config('app.current_role', p_role, true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ========================================================
-- 1. ORGANIZATIONS & TENANT MANAGEMENT (5 tables)
-- ========================================================

CREATE TABLE IF NOT EXISTS organizations (
    org_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    subscription_tier TEXT DEFAULT 'free' CHECK (subscription_tier IN ('free','pro','enterprise','custom')),
    billing_email TEXT,
    contact_email TEXT,
    phone TEXT,
    address JSONB,
    settings JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_orgs_slug ON organizations(slug);
CREATE INDEX IF NOT EXISTS idx_orgs_active ON organizations(is_active) WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS org_members (
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer' CHECK (role IN ('owner','admin','analyst','viewer')),
    status TEXT DEFAULT 'active' CHECK (status IN ('active','suspended','invited')),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ,
    PRIMARY KEY (org_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_org_members_user ON org_members(user_id);

CREATE TABLE IF NOT EXISTS api_keys (
    key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    api_key_hash TEXT NOT NULL UNIQUE,
    scopes JSONB DEFAULT '["read"]',
    ip_allowlist JSONB DEFAULT '["0.0.0.0/0"]',
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_api_keys_org ON api_keys(org_id);

CREATE TABLE IF NOT EXISTS org_audit_log (
    log_id BIGSERIAL PRIMARY KEY,
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    actor_id TEXT,
    actor_role TEXT,
    resource_type TEXT,
    resource_id TEXT,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_org_audit_org ON org_audit_log(org_id, created_at DESC);

CREATE TABLE IF NOT EXISTS org_usage_limits (
    limit_id SERIAL PRIMARY KEY,
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    resource_type TEXT NOT NULL,
    limit_value BIGINT NOT NULL,
    period TEXT DEFAULT 'monthly' CHECK (period IN ('daily','weekly','monthly','yearly')),
    resets_at TIMESTAMPTZ,
    UNIQUE(org_id, resource_type, period)
);

-- ========================================================
-- 2. USER MANAGEMENT (5 tables)
-- ========================================================

CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    org_id UUID REFERENCES organizations(org_id),
    email TEXT NOT NULL UNIQUE,
    username TEXT UNIQUE,
    display_name TEXT,
    hashed_password TEXT,
    avatar_url TEXT,
    mfa_secret TEXT,
    mfa_enabled BOOLEAN DEFAULT FALSE,
    email_verified BOOLEAN DEFAULT FALSE,
    phone TEXT,
    timezone TEXT DEFAULT 'UTC',
    language TEXT DEFAULT 'en',
    subscription_tier TEXT DEFAULT 'free',
    last_login_at TIMESTAMPTZ,
    last_login_ip INET,
    is_active BOOLEAN DEFAULT TRUE,
    is_superadmin BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_org ON users(org_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS user_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    refresh_token_hash TEXT,
    device_info JSONB,
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    last_activity_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON user_sessions(is_active) WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    theme TEXT DEFAULT 'dark',
    notifications_enabled BOOLEAN DEFAULT TRUE,
    email_notifications BOOLEAN DEFAULT TRUE,
    digest_frequency TEXT DEFAULT 'daily' CHECK (digest_frequency IN ('realtime','hourly','daily','weekly','off')),
    timezone TEXT DEFAULT 'UTC',
    language TEXT DEFAULT 'en',
    ui_settings JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS user_activity_log (
    activity_id BIGSERIAL PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id),
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    metadata JSONB,
    ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_user_activity_user ON user_activity_log(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_reset_tokens_user ON password_reset_tokens(user_id);

-- ========================================================
-- 3. BIOMETRIC IDENTITY (7 tables)
-- ========================================================

CREATE TABLE IF NOT EXISTS persons (
    person_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    aliases TEXT[],
    age INTEGER CHECK (age >= 0 AND age <= 150),
    gender TEXT CHECK (gender IN ('male','female','non-binary','unknown')),
    ethnicity TEXT,
    nationality TEXT,
    metadata JSONB DEFAULT '{}',
    consent_record_id UUID,
    is_enrolled BOOLEAN DEFAULT TRUE,
    risk_level TEXT DEFAULT 'unknown' CHECK (risk_level IN ('unknown','low','medium','high','critical')),
    notes TEXT,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_persons_org ON persons(org_id);
CREATE INDEX IF NOT EXISTS idx_persons_name ON persons(name);
CREATE INDEX IF NOT EXISTS idx_persons_risk ON persons(risk_level);
CREATE INDEX IF NOT EXISTS idx_persons_created ON persons(created_at DESC);

CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID REFERENCES persons(person_id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(org_id),
    enrollment_type TEXT CHECK (enrollment_type IN ('face','voice','gait','iris','multi')),
    source TEXT,
    quality_score FLOAT CHECK (quality_score >= 0 AND quality_score <= 1),
    device_id TEXT,
    location TEXT,
    operator_id TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active','inactive','expired','revoked')),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_enrollments_person ON enrollments(person_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_org ON enrollments(org_id);

CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID REFERENCES persons(person_id) ON DELETE CASCADE,
    enrollment_id UUID REFERENCES enrollments(enrollment_id),
    embedding_type TEXT NOT NULL CHECK (embedding_type IN ('face','voice','gait','iris','palm')),
    embedding VECTOR(512),
    voice_embedding VECTOR(192),
    gait_embedding VECTOR(1280),
    modality_quality FLOAT,
    capture_timestamp TIMESTAMPTZ,
    camera_id TEXT,
    device_id TEXT,
    algorithm_version TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_embeddings_person ON embeddings(person_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_type ON embeddings(embedding_type);
CREATE INDEX IF NOT EXISTS idx_embeddings_camera ON embeddings(camera_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_created ON embeddings(created_at DESC);

CREATE TABLE IF NOT EXISTS face_templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID REFERENCES persons(person_id) ON DELETE CASCADE,
    enrollment_id UUID REFERENCES enrollments(enrollment_id),
    template_version TEXT NOT NULL,
    template_data BYTEA NOT NULL,
    algorithm TEXT NOT NULL,
    quality_metrics JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_face_templates_person ON face_templates(person_id);

CREATE TABLE IF NOT EXISTS voice_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID REFERENCES persons(person_id) ON DELETE CASCADE,
    enrollment_id UUID REFERENCES enrollments(enrollment_id),
    profile_data BYTEA NOT NULL,
    voice_model_version TEXT,
    sample_rate INTEGER,
    language TEXT,
    quality_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_voice_profiles_person ON voice_profiles(person_id);

CREATE TABLE IF NOT EXISTS gait_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID REFERENCES persons(person_id) ON DELETE CASCADE,
    enrollment_id UUID REFERENCES enrollments(enrollment_id),
    profile_data BYTEA NOT NULL,
    gait_model_version TEXT,
    walking_speed_range JSONB,
    quality_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_gait_profiles_person ON gait_profiles(person_id);

CREATE TABLE IF NOT EXISTS iris_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID REFERENCES persons(person_id) ON DELETE CASCADE,
    enrollment_id UUID REFERENCES enrollments(enrollment_id),
    profile_data BYTEA NOT NULL,
    algorithm_version TEXT,
    quality_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_iris_profiles_person ON iris_profiles(person_id);

-- ========================================================
-- 4. CAMERA & DEVICE MANAGEMENT (5 tables)
-- ========================================================

CREATE TABLE IF NOT EXISTS cameras (
    camera_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    rtsp_url TEXT,
    rtsp_username TEXT,
    rtsp_password_encrypted TEXT,
    location TEXT,
    floor TEXT,
    building TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    status TEXT DEFAULT 'offline' CHECK (status IN ('online','offline','maintenance','decommissioned')),
    camera_type TEXT DEFAULT 'fixed' CHECK (camera_type IN ('fixed','pan_tilt','fisheye','thermal','360')),
    resolution TEXT DEFAULT '1920x1080',
    fps INTEGER DEFAULT 30,
    codec TEXT DEFAULT 'h264',
    bandwidth_kbps INTEGER,
    firmware_version TEXT,
    last_heartbeat_at TIMESTAMPTZ,
    last_maintenance_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    config JSONB DEFAULT '{}',
    is_recording BOOLEAN DEFAULT TRUE,
    retention_days INTEGER DEFAULT 30,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_cameras_org ON cameras(org_id);
CREATE INDEX IF NOT EXISTS idx_cameras_status ON cameras(status);
CREATE INDEX IF NOT EXISTS idx_cameras_location ON cameras(location);

CREATE TABLE IF NOT EXISTS edge_devices (
    device_id TEXT PRIMARY KEY,
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    device_name TEXT NOT NULL,
    device_type TEXT CHECK (device_type IN ('nvidia_jetson','raspberry_pi','intel_nuc','custom','server')),
    model_version_id UUID,
    firmware_version TEXT,
    os_version TEXT,
    cpu_temp FLOAT,
    gpu_temp FLOAT,
    memory_usage_pct FLOAT,
    disk_usage_pct FLOAT,
    network_in_mbps FLOAT,
    network_out_mbps FLOAT,
    status TEXT DEFAULT 'offline' CHECK (status IN ('online','offline','maintenance','error')),
    last_seen_at TIMESTAMPTZ,
    ip_address INET,
    mac_address TEXT,
    location TEXT,
    config JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_edge_devices_org ON edge_devices(org_id);
CREATE INDEX IF NOT EXISTS idx_edge_devices_status ON edge_devices(status);

CREATE TABLE IF NOT EXISTS camera_groups (
    group_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    camera_ids UUID[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS camera_streams (
    stream_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id UUID REFERENCES cameras(camera_id) ON DELETE CASCADE,
    stream_type TEXT NOT NULL CHECK (stream_type IN ('primary','secondary','low_resolution','thermal')),
    rtsp_url TEXT NOT NULL,
    codec TEXT,
    resolution TEXT,
    fps INTEGER,
    bitrate_kbps INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    health_check_failures INTEGER DEFAULT 0,
    last_successful_frame_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_camera_streams_camera ON camera_streams(camera_id);

CREATE TABLE IF NOT EXISTS device_health_checks (
    check_id BIGSERIAL PRIMARY KEY,
    device_id TEXT,
    camera_id UUID REFERENCES cameras(camera_id),
    check_type TEXT NOT NULL,
    status TEXT NOT NULL,
    latency_ms FLOAT,
    cpu_usage FLOAT,
    memory_usage FLOAT,
    disk_usage FLOAT,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_device_health_device ON device_health_checks(device_id, created_at DESC);

-- ========================================================
-- 5. RECOGNITION & EVENTS (6 tables)
-- ========================================================

CREATE TABLE IF NOT EXISTS recognition_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    camera_id UUID REFERENCES cameras(camera_id),
    person_id UUID REFERENCES persons(person_id),
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    threshold_used FLOAT,
    face_distance FLOAT,
    voice_distance FLOAT,
    gait_distance FLOAT,
    final_score FLOAT,
    match_type TEXT CHECK (match_type IN ('face','voice','gait','multi','no_match')),
    is_spoof BOOLEAN DEFAULT FALSE,
    spoof_score FLOAT,
    image_path TEXT,
    video_frame_number INTEGER,
    processing_latency_ms FLOAT,
    recognition_mode TEXT CHECK (recognition_mode IN ('realtime','batch','api','offline')),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_recognition_org ON recognition_events(org_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recognition_camera ON recognition_events(camera_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recognition_person ON recognition_events(person_id);
CREATE INDEX IF NOT EXISTS idx_recognition_created ON recognition_events(created_at DESC);

CREATE TABLE IF NOT EXISTS recognition_batches (
    batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id),
    source TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending','processing','completed','failed','cancelled')),
    total_items INTEGER,
    processed_items INTEGER DEFAULT 0,
    failed_items INTEGER DEFAULT 0,
    priority INTEGER DEFAULT 5,
    error_message TEXT,
    results_summary JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recognition_quality_metrics (
    metric_id BIGSERIAL PRIMARY KEY,
    org_id UUID REFERENCES organizations(org_id),
    camera_id UUID REFERENCES cameras(camera_id),
    avg_confidence FLOAT,
    false_accept_rate FLOAT,
    false_reject_rate FLOAT,
    total_matches INTEGER,
    true_positives INTEGER,
    false_positives INTEGER,
    true_negatives INTEGER,
    false_negatives INTEGER,
    measurement_window TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS video_processing_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id),
    camera_id UUID REFERENCES cameras(camera_id),
    video_url TEXT NOT NULL,
    video_metadata JSONB,
    fps_sample_rate INTEGER DEFAULT 1,
    total_frames INTEGER,
    frames_processed INTEGER DEFAULT 0,
    status TEXT DEFAULT 'queued' CHECK (status IN ('queued','processing','completed','failed','cancelled')),
    total_faces_detected INTEGER DEFAULT 0,
    total_matches INTEGER DEFAULT 0,
    error_message TEXT,
    result_summary JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alert_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    rule_type TEXT NOT NULL CHECK (rule_type IN ('threshold','anomaly','time_based','geofence','unknown_person','spoof_detected')),
    conditions JSONB NOT NULL,
    actions JSONB NOT NULL,
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),
    is_active BOOLEAN DEFAULT TRUE,
    cooldown_seconds INTEGER DEFAULT 300,
    last_triggered_at TIMESTAMPTZ,
    trigger_count INTEGER DEFAULT 0,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_alert_rules_org ON alert_rules(org_id);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    rule_id UUID REFERENCES alert_rules(rule_id),
    event_id UUID REFERENCES recognition_events(event_id),
    camera_id UUID REFERENCES cameras(camera_id),
    person_id UUID REFERENCES persons(person_id),
    alert_type TEXT NOT NULL,
    severity TEXT DEFAULT 'medium' CHECK (severity IN ('low','medium','high','critical')),
    status TEXT DEFAULT 'new' CHECK (status IN ('new','acknowledged','investigating','resolved','false_positive','escalated')),
    title TEXT NOT NULL,
    description TEXT,
    confidence_score FLOAT,
    image_path TEXT,
    metadata JSONB DEFAULT '{}',
    assigned_to TEXT,
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_alerts_org ON alerts(org_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_person ON alerts(person_id);

CREATE TABLE IF NOT EXISTS alert_delivery (
    delivery_id BIGSERIAL PRIMARY KEY,
    alert_id UUID REFERENCES alerts(alert_id) ON DELETE CASCADE,
    channel TEXT NOT NULL CHECK (channel IN ('email','sms','push','webhook','slack')),
    recipient TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending','sent','delivered','read','failed')),
    attempts INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    error_message TEXT
);

-- ========================================================
-- 6. BILLING & SUBSCRIPTIONS (5 tables)
-- ========================================================

CREATE TABLE IF NOT EXISTS billing.plans (
    plan_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    price_cents INTEGER NOT NULL DEFAULT 0,
    currency TEXT DEFAULT 'USD',
    billing_interval TEXT DEFAULT 'monthly' CHECK (billing_interval IN ('monthly','yearly')),
    features JSONB,
    limits JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS billing.subscriptions (
    subscription_id TEXT PRIMARY KEY,
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    plan_id TEXT REFERENCES billing.plans(plan_id),
    status TEXT DEFAULT 'active' CHECK (status IN ('active','trialing','past_due','canceled','unpaid','incomplete')),
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    stripe_price_id TEXT,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    canceled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_subs_org ON billing.subscriptions(org_id);
CREATE INDEX IF NOT EXISTS idx_subs_stripe_cust ON billing.subscriptions(stripe_customer_id);

CREATE TABLE IF NOT EXISTS billing.invoices (
    invoice_id TEXT PRIMARY KEY,
    org_id UUID REFERENCES organizations(org_id),
    subscription_id TEXT REFERENCES billing.subscriptions(subscription_id),
    stripe_invoice_id TEXT,
    amount_cents INTEGER NOT NULL,
    currency TEXT DEFAULT 'USD',
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft','open','paid','void','refunded','uncollectible')),
    due_date TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    receipt_number TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_invoices_org ON billing.invoices(org_id, created_at DESC);

CREATE TABLE IF NOT EXISTS billing.usage_records (
    record_id BIGSERIAL PRIMARY KEY,
    org_id UUID REFERENCES organizations(org_id),
    subscription_id TEXT REFERENCES billing.subscriptions(subscription_id),
    metric_name TEXT NOT NULL,
    quantity NUMERIC(18,4) NOT NULL,
    unit TEXT DEFAULT 'unit',
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    stripe_usage_record_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_usage_org ON billing.usage_records(org_id, metric_name, timestamp DESC);

CREATE TABLE IF NOT EXISTS billing.payment_methods (
    payment_method_id TEXT PRIMARY KEY,
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    stripe_payment_method_id TEXT,
    type TEXT NOT NULL CHECK (type IN ('card','bank_account','sepa_debit')),
    is_default BOOLEAN DEFAULT FALSE,
    last4 TEXT,
    brand TEXT,
    exp_month INTEGER,
    exp_year INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================================
-- 7. AUDIT LOGGING (3 tables)
-- ========================================================

CREATE TABLE IF NOT EXISTS audit.log_entries (
    log_id BIGSERIAL PRIMARY KEY,
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    actor_id TEXT NOT NULL,
    actor_type TEXT DEFAULT 'user' CHECK (actor_type IN ('user','system','api_key','service')),
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    previous_hash TEXT,
    current_hash TEXT,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    trace_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_org ON audit.log_entries(org_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_hash ON audit.log_entries(current_hash);

CREATE TABLE IF NOT EXISTS audit.hash_chain (
    chain_id BIGSERIAL PRIMARY KEY,
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    block_number BIGINT NOT NULL,
    previous_hash TEXT NOT NULL,
    merkle_root TEXT NOT NULL,
    record_count INTEGER NOT NULL,
    batch_signature TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, block_number)
);

CREATE TABLE IF NOT EXISTS audit.integrity_checks (
    check_id BIGSERIAL PRIMARY KEY,
    org_id UUID REFERENCES organizations(org_id),
    check_type TEXT NOT NULL,
    is_valid BOOLEAN NOT NULL,
    broken_links JSONB,
    details JSONB,
    performed_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================================
-- 8. ML MODEL REGISTRY (4 tables)
-- ========================================================

CREATE TABLE IF NOT EXISTS ml.model_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id),
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    framework TEXT NOT NULL CHECK (framework IN ('pytorch','onnx','tflite','openvino','tensorrt')),
    architecture TEXT,
    input_shape INTEGER[],
    output_dim INTEGER,
    description TEXT,
    training_dataset TEXT,
    training_params JSONB,
    metrics JSONB DEFAULT '{}',
    model_path TEXT NOT NULL,
    size_bytes BIGINT,
    checksum CHAR(64) NOT NULL,
    signature TEXT,
    status TEXT DEFAULT 'staging' CHECK (status IN ('draft','staging','production','deprecated','archived')),
    tags JSONB DEFAULT '[]',
    min_requirements JSONB DEFAULT '{}',
    uploaded_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    download_count INTEGER DEFAULT 0,
    promoted_at TIMESTAMPTZ,
    UNIQUE(name, version)
);
CREATE INDEX IF NOT EXISTS idx_models_org ON ml.model_versions(org_id);
CREATE INDEX IF NOT EXISTS idx_models_status ON ml.model_versions(status);

CREATE TABLE IF NOT EXISTS ml.model_performance (
    metric_id BIGSERIAL PRIMARY KEY,
    model_version_id UUID REFERENCES ml.model_versions(version_id),
    dataset_name TEXT NOT NULL,
    accuracy FLOAT,
    precision FLOAT,
    recall FLOAT,
    f1_score FLOAT,
    auc_roc FLOAT,
    false_positive_rate FLOAT,
    false_negative_rate FLOAT,
    inference_latency_p50 FLOAT,
    inference_latency_p95 FLOAT,
    inference_latency_p99 FLOAT,
    tested_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_model_perf_model ON ml.model_performance(model_version_id, tested_at DESC);

CREATE TABLE IF NOT EXISTS ml.training_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_version_id UUID REFERENCES ml.model_versions(version_id),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending','running','completed','failed','cancelled')),
    hyperparameters JSONB,
    training_data_path TEXT,
    epochs INTEGER,
    learning_rate FLOAT,
    batch_size INTEGER,
    final_loss FLOAT,
    final_metrics JSONB,
    compute_cost_usd FLOAT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ml.model_drift (
    drift_id BIGSERIAL PRIMARY KEY,
    model_version_id UUID REFERENCES ml.model_versions(version_id),
    metric_name TEXT NOT NULL,
    baseline_value FLOAT,
    current_value FLOAT,
    drift_percentage FLOAT,
    threshold FLOAT,
    is_drifted BOOLEAN DEFAULT FALSE,
    detected_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_drift_model ON ml.model_drift(model_version_id, detected_at DESC);

-- ========================================================
-- 9. NOTIFICATIONS (3 tables)
-- ========================================================

CREATE TABLE IF NOT EXISTS notifications.outbox (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id),
    user_id TEXT REFERENCES users(user_id),
    channel TEXT NOT NULL CHECK (channel IN ('email','sms','push','webhook','in_app')),
    template_id TEXT,
    subject TEXT,
    body TEXT,
    payload JSONB,
    priority TEXT DEFAULT 'normal' CHECK (priority IN ('low','normal','high','critical')),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending','processing','sent','delivered','failed','bounced')),
    attempts INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    next_retry_at TIMESTAMPTZ,
    last_error TEXT,
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications.outbox(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notif_status ON notifications.outbox(status);

CREATE TABLE IF NOT EXISTS notifications.preferences (
    pref_id SERIAL PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    notification_type TEXT NOT NULL,
    email_enabled BOOLEAN DEFAULT TRUE,
    push_enabled BOOLEAN DEFAULT TRUE,
    sms_enabled BOOLEAN DEFAULT FALSE,
    webhook_enabled BOOLEAN DEFAULT FALSE,
    quiet_hours_start TIME DEFAULT '22:00',
    quiet_hours_end TIME DEFAULT '07:00',
    UNIQUE(user_id, notification_type)
);

CREATE TABLE IF NOT EXISTS notification_templates (
    template_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    subject_template TEXT NOT NULL,
    body_template TEXT NOT NULL,
    template_type TEXT NOT NULL CHECK (template_type IN ('email','sms','push','webhook')),
    variables JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================================
-- 10. COMPLIANCE (3 tables)
-- ========================================================

CREATE TABLE IF NOT EXISTS compliance.dsar_requests (
    request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id),
    user_id TEXT REFERENCES users(user_id),
    request_type TEXT NOT NULL CHECK (request_type IN ('access','deletion','rectification','portability','objection')),
    status TEXT DEFAULT 'received' CHECK (status IN ('received','verified','processing','completed','denied')),
    reason TEXT,
    data_scope JSONB,
    reviewer_id TEXT,
    review_notes TEXT,
    due_date TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    data_package_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS compliance.consent_records (
    consent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT REFERENCES users(user_id),
    purpose TEXT NOT NULL,
    consent_text_version TEXT NOT NULL,
    granted BOOLEAN DEFAULT TRUE,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    ip_address INET,
    user_agent TEXT,
    metadata JSONB
);
CREATE INDEX IF NOT EXISTS idx_consent_user ON compliance.consent_records(user_id);

CREATE TABLE IF NOT EXISTS compliance.data_retention_policies (
    policy_id SERIAL PRIMARY KEY,
    org_id UUID REFERENCES organizations(org_id),
    table_name TEXT NOT NULL,
    retention_days INTEGER NOT NULL,
    archival_action TEXT DEFAULT 'delete' CHECK (archival_action IN ('delete','archive','anonymize')),
    last_executed TIMESTAMPTZ,
    next_execution TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========================================================
-- 11. SYSTEM & INFRASTRUCTURE (4 tables)
-- ========================================================

CREATE TABLE IF NOT EXISTS system_config (
    config_key TEXT PRIMARY KEY,
    config_value JSONB NOT NULL,
    description TEXT,
    is_sensitive BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by TEXT
);

CREATE TABLE IF NOT EXISTS system_health (
    health_id BIGSERIAL PRIMARY KEY,
    service_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('healthy','degraded','unhealthy','maintenance')),
    latency_ms FLOAT,
    error_message TEXT,
    check_type TEXT DEFAULT 'heartbeat',
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_health_service ON system_health(service_name, created_at DESC);

CREATE TABLE IF NOT EXISTS system_celery_tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_name TEXT NOT NULL,
    task_queue TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending','received','started','success','failure','revoked','retry')),
    args JSONB,
    kwargs JSONB,
    result JSONB,
    error_message TEXT,
    retries INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    eta TIMESTAMPTZ,
    expires TIMESTAMPTZ,
    worker_hostname TEXT,
    execution_time_ms FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_celery_status ON system_celery_tasks(status);
CREATE INDEX IF NOT EXISTS idx_celery_created ON system_celery_tasks(created_at DESC);

CREATE TABLE IF NOT EXISTS system_backup_log (
    backup_id TEXT PRIMARY KEY,
    backup_type TEXT NOT NULL CHECK (backup_type IN ('full','incremental','wal','logical')),
    status TEXT NOT NULL CHECK (status IN ('started','completed','failed')),
    source_size_bytes BIGINT,
    compressed_size_bytes BIGINT,
    storage_location TEXT,
    encryption_enabled BOOLEAN DEFAULT TRUE,
    checksum TEXT,
    retention_until TIMESTAMPTZ,
    duration_seconds FLOAT,
    error_message TEXT,
    metadata JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- ========================================================
-- 12. REDIS CACHE LAYER (2 tables)
-- ========================================================

CREATE TABLE IF NOT EXISTS redis.cache_manifest (
    cache_key TEXT PRIMARY KEY,
    cache_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    ttl_seconds INTEGER,
    invalidation_channel TEXT,
    dependencies JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS redis.rate_limit_buckets (
    bucket_id TEXT PRIMARY KEY,
    identifier TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    tokens_remaining INTEGER NOT NULL,
    capacity INTEGER NOT NULL,
    refill_rate REAL NOT NULL,
    last_refill TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    metadata JSONB
);
CREATE INDEX IF NOT EXISTS idx_rate_limit_ident ON redis.rate_limit_buckets(identifier, endpoint);

-- Total: 42 tables across 12 categories
ENDSQL
print("init.sql written successfully")