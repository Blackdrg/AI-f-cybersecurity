#!/usr/bin/env python3
import os
BASE = r"D:\AI-F\AI-f"

def wf(path, content):
    with open(path, 'w') as f:
        f.write(content)
    print(f"Written: {path}")

# =========== FILE 1: init.sql ===========
sql_parts = []
sql_parts.append("""-- AI-f Database Initialization
-- Production-ready PostgreSQL 15+ with pgvector, pgcrypto
-- 42+ tables with full Row Level Security

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS billing;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS ml;
CREATE SCHEMA IF NOT EXISTS notifications;
CREATE SCHEMA IF NOT EXISTS compliance;

CREATE OR REPLACE FUNCTION set_tenant_context(p_org_id UUID, p_user_id TEXT, p_role TEXT DEFAULT 'viewer')
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_org_id', p_org_id::text, true);
    PERFORM set_config('app.current_user_id', p_user_id, true);
    PERFORM set_config('app.current_role', p_role, true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
""")

# Table definitions - all 42+ tables
tables = [
    # Organizations (5)
    """CREATE TABLE IF NOT EXISTS organizations (
    org_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL, subscription_tier TEXT DEFAULT 'free',
    billing_email TEXT, metadata JSONB DEFAULT '{}', is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_orgs_slug ON organizations(slug);
CREATE INDEX idx_orgs_active ON organizations(is_active) WHERE is_active;

CREATE TABLE IF NOT EXISTS org_members (
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    user_id TEXT NOT NULL, role TEXT DEFAULT 'viewer', PRIMARY KEY (org_id, user_id));
CREATE INDEX idx_org_members_user ON org_members(user_id);

CREATE TABLE IF NOT EXISTS api_keys (
    key_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    api_key_hash TEXT NOT NULL UNIQUE, scopes JSONB DEFAULT '[\"read\"]',
    ip_allowlist JSONB DEFAULT '[\"0.0.0.0/0\"]', is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_api_keys_org ON api_keys(org_id);

CREATE TABLE IF NOT EXISTS org_audit_log (
    log_id BIGSERIAL PRIMARY KEY, org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    action TEXT, actor_id TEXT, resource_type TEXT, resource_id TEXT,
    old_values JSONB, new_values JSONB, ip_address INET,
    created_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_org_audit_org ON org_audit_log(org_id, created_at DESC);

CREATE TABLE IF NOT EXISTS org_usage_limits (
    limit_id SERIAL PRIMARY KEY, org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    resource_type TEXT NOT NULL, limit_value BIGINT NOT NULL,
    period TEXT DEFAULT 'monthly', resets_at TIMESTAMPTZ,
    UNIQUE(org_id, resource_type, period));""",

    # Users (5)
    """CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY, org_id UUID REFERENCES organizations(org_id),
    email TEXT NOT NULL UNIQUE, username TEXT UNIQUE, display_name TEXT,
    hashed_password TEXT, mfa_secret TEXT, mfa_enabled BOOLEAN DEFAULT FALSE,
    email_verified BOOLEAN DEFAULT FALSE, phone TEXT, timezone TEXT DEFAULT 'UTC',
    subscription_tier TEXT DEFAULT 'free', last_login_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE, is_superadmin BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}', created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_users_org ON users(org_id);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active;

CREATE TABLE IF NOT EXISTS user_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE, refresh_token_hash TEXT,
    device_info JSONB, ip_address INET, is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(), expires_at TIMESTAMPTZ NOT NULL);
CREATE INDEX idx_sessions_user ON user_sessions(user_id);
CREATE INDEX idx_sessions_expires ON user_sessions(expires_at);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    theme TEXT DEFAULT 'dark', notifications_enabled BOOLEAN DEFAULT TRUE,
    digest_frequency TEXT DEFAULT 'daily', timezone TEXT DEFAULT 'UTC',
    ui_settings JSONB DEFAULT '{}');

CREATE TABLE IF NOT EXISTS user_activity_log (
    activity_id BIGSERIAL PRIMARY KEY, user_id TEXT REFERENCES users(user_id),
    action TEXT, resource_type TEXT, resource_id TEXT, metadata JSONB,
    ip_address INET, created_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_user_activity_user ON user_activity_log(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE, expires_at TIMESTAMPTZ NOT NULL,
    is_used BOOLEAN DEFAULT FALSE, created_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_reset_tokens_user ON password_reset_tokens(user_id);""",

    # Biometric Identity (7)
    """CREATE TABLE IF NOT EXISTS persons (
    person_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    name TEXT NOT NULL, aliases TEXT[], age INTEGER CHECK (age>=0 AND age<=150),
    gender TEXT CHECK (gender IN ('male','female','non-binary','unknown')),
    metadata JSONB DEFAULT '{}', consent_record_id UUID,
    risk_level TEXT DEFAULT 'unknown', created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_persons_org ON persons(org_id);

CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID REFERENCES persons(person_id) ON DELETE CASCADE,
    org_id UUID REFERENCES organizations(org_id),
    enrollment_type TEXT CHECK (enrollment_type IN ('face','voice','gait','iris','multi')),
    quality_score FLOAT, device_id TEXT, status TEXT DEFAULT 'active',
    metadata JSONB DEFAULT '{}', created_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_enrollments_person ON enrollments(person_id);
CREATE INDEX idx_enrollments_org ON enrollments(org_id);

CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID REFERENCES persons(person_id) ON DELETE CASCADE,
    embedding_type TEXT NOT NULL CHECK (embedding_type IN ('face','voice','gait','iris','palm')),
    embedding VECTOR(512), voice_embedding VECTOR(192), gait_embedding VECTOR(1280),
    modality_quality FLOAT, camera_id TEXT, algorithm_version TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_embeddings_person ON embeddings(person_id);
CREATE INDEX idx_embeddings_type ON embeddings(embedding_type);
CREATE INDEX idx_embedding_hnsw ON embeddings USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64);

CREATE TABLE IF NOT EXISTS face_templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID REFERENCES persons(person_id) ON DELETE CASCADE,
    template_version TEXT NOT NULL, template_data BYTEA NOT NULL,
    algorithm TEXT, quality_metrics JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(), is_active BOOLEAN DEFAULT TRUE);
CREATE INDEX idx_face_templates_person ON face_templates(person_id);

CREATE TABLE IF NOT EXISTS voice_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID REFERENCES persons(person_id) ON DELETE CASCADE,
    profile_data BYTEA NOT NULL, voice_model_version TEXT,
    sample_rate INTEGER, language TEXT, quality_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(), is_active BOOLEAN DEFAULT TRUE);
CREATE INDEX idx_voice_profiles_person ON voice_profiles(person_id);

CREATE TABLE IF NOT EXISTS gait_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID REFERENCES persons(person_id) ON DELETE CASCADE,
    profile_data BYTEA NOT NULL, gait_model_version TEXT,
    walking_speed_range JSONB, quality_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(), is_active BOOLEAN DEFAULT TRUE);
CREATE INDEX idx_gait_profiles_person ON gait_profiles(person_id);

CREATE TABLE IF NOT EXISTS iris_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID REFERENCES persons(person_id) ON DELETE CASCADE,
    profile_data BYTEA NOT NULL, algorithm_version TEXT, quality_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(), is_active BOOLEAN DEFAULT TRUE);
CREATE INDEX idx_iris_profiles_person ON iris_profiles(person_id);""",

    # Camera & Devices (5)
    """CREATE TABLE IF NOT EXISTS cameras (
    camera_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    name TEXT NOT NULL, rtsp_url TEXT, location TEXT, floor TEXT, building TEXT,
    status TEXT DEFAULT 'offline' CHECK (status IN ('online','offline','maintenance','decommissioned')),
    camera_type TEXT DEFAULT 'fixed', resolution TEXT DEFAULT '1920x1080',
    fps INTEGER DEFAULT 30, firmware_version TEXT, last_heartbeat_at TIMESTAMPTZ,
    config JSONB DEFAULT '{}', metadata JSONB DEFAULT '{}', is_recording BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_cameras_org ON cameras(org_id);
CREATE INDEX idx_cameras_status ON cameras(status);

CREATE TABLE IF NOT EXISTS edge_devices (
    device_id TEXT PRIMARY KEY, org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    device_name TEXT NOT NULL, device_type TEXT, status TEXT DEFAULT 'offline',
    last_seen_at TIMESTAMPTZ, ip_address INET, mac_address TEXT, location TEXT,
    cpu_temp FLOAT, gpu_temp FLOAT, memory_usage_pct FLOAT, disk_usage_pct FLOAT,
    config JSONB DEFAULT '{}', metadata JSONB DEFAULT '{}', is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_edge_devices_org ON edge_devices(org_id);
CREATE INDEX idx_edge_devices_status ON edge_devices(status) WHERE status='online';

CREATE TABLE IF NOT EXISTS camera_groups (
    group_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    name TEXT NOT NULL, camera_ids UUID[], metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());

CREATE TABLE IF NOT EXISTS camera_streams (
    stream_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    camera_id UUID REFERENCES cameras(camera_id) ON DELETE CASCADE,
    stream_type TEXT NOT NULL CHECK (stream_type IN ('primary','secondary','low_res','thermal')),
    rtsp_url TEXT NOT NULL, codec TEXT DEFAULT 'h264', resolution TEXT,
    fps INTEGER, bitrate_kbps INTEGER, is_active BOOLEAN DEFAULT TRUE,
    health_check_failures INTEGER DEFAULT 0, last_successful_frame_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_camera_streams_camera ON camera_streams(camera_id);

CREATE TABLE IF NOT EXISTS device_health_checks (
    check_id BIGSERIAL PRIMARY KEY, device_id TEXT, camera_id UUID REFERENCES cameras(camera_id),
    check_type TEXT NOT NULL, status TEXT NOT NULL, latency_ms FLOAT,
    cpu_usage FLOAT, memory_usage FLOAT, disk_usage FLOAT, error_message TEXT,
    metadata JSONB DEFAULT '{}', created_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_device_health_device ON device_health_checks(device_id, created_at DESC);""",

    # Recognition & Alerts (6)
    """CREATE TABLE IF NOT EXISTS recognition_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    camera_id UUID REFERENCES cameras(camera_id), person_id UUID REFERENCES persons(person_id),
    confidence_score FLOAT, threshold_used FLOAT, face_distance FLOAT,
    voice_distance FLOAT, gait_distance FLOAT, final_score FLOAT,
    match_type TEXT CHECK (match_type IN ('face','voice','gait','multi','no_match')),
    is_spoof BOOLEAN DEFAULT FALSE, spoof_score FLOAT, image_path TEXT,
    video_frame_number INTEGER, processing_latency_ms FLOAT,
    recognition_mode TEXT CHECK (recognition_mode IN ('realtime','batch','api','offline')),
    metadata JSONB DEFAULT '{}', created_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_recog_org ON recognition_events(org_id, created_at DESC);
CREATE INDEX idx_recog_camera ON recognition_events(camera_id);
CREATE INDEX idx_recog_person ON recognition_events(person_id);
CREATE INDEX idx_recog_created ON recognition_events(created_at DESC);

CREATE TABLE IF NOT EXISTS recognition_batches (
    batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), org_id UUID REFERENCES organizations(org_id),
    source TEXT, status TEXT DEFAULT 'pending', total_items INTEGER,
    processed_items INTEGER DEFAULT 0, failed_items INTEGER DEFAULT 0, priority INTEGER DEFAULT 5,
    error_message TEXT, results_summary JSONB,
    started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ, created_at TIMESTAMPTZ DEFAULT NOW());

CREATE TABLE IF NOT EXISTS recognition_quality_metrics (
    metric_id BIGSERIAL PRIMARY KEY, org_id UUID REFERENCES organizations(org_id),
    camera_id UUID REFERENCES cameras(camera_id), avg_confidence FLOAT,
    false_accept_rate FLOAT, false_reject_rate FLOAT, total_matches INTEGER,
    true_positives INTEGER, false_positives INTEGER, true_negatives INTEGER, false_negatives INTEGER,
    measurement_window TEXT, created_at TIMESTAMPTZ DEFAULT NOW());

CREATE TABLE IF NOT EXISTS video_processing_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), org_id UUID REFERENCES organizations(org_id),
    camera_id UUID REFERENCES cameras(camera_id), video_url TEXT NOT NULL,
    video_metadata JSONB, fps_sample_rate INTEGER DEFAULT 1,
    total_frames INTEGER, frames_processed INTEGER DEFAULT 0, status TEXT DEFAULT 'queued',
    total_faces_detected INTEGER DEFAULT 0, total_matches INTEGER DEFAULT 0, error_message TEXT,
    result_summary JSONB, started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW());

CREATE TABLE IF NOT EXISTS alert_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    name TEXT NOT NULL, description TEXT,
    rule_type TEXT NOT NULL CHECK (rule_type IN ('threshold','anomaly','time_based','geofence','unknown_person','spoof_detected')),
    conditions JSONB NOT NULL, actions JSONB NOT NULL, priority INTEGER DEFAULT 5,
    is_active BOOLEAN DEFAULT TRUE, cooldown_seconds INTEGER DEFAULT 300,
    last_triggered_at TIMESTAMPTZ, trigger_count INTEGER DEFAULT 0,
    created_by TEXT, created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_alert_rules_org ON alert_rules(org_id);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    rule_id UUID REFERENCES alert_rules(rule_id), event_id UUID REFERENCES recognition_events(event_id),
    camera_id UUID REFERENCES cameras(camera_id), person_id UUID REFERENCES persons(person_id),
    alert_type TEXT, severity TEXT DEFAULT 'medium' CHECK (severity IN ('low','medium','high','critical')),
    status TEXT DEFAULT 'new' CHECK (status IN ('new','acknowledged','investigating','resolved','false_positive','escalated')),
    title TEXT NOT NULL, description TEXT, confidence_score FLOAT, image_path TEXT,
    metadata JSONB DEFAULT '{}', assigned_to TEXT,
    acknowledged_at TIMESTAMPTZ, resolved_at TIMESTAMPTZ, expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_alerts_org ON alerts(org_id, created_at DESC);
CREATE INDEX idx_alerts_status ON alerts(status);

CREATE TABLE IF NOT EXISTS alert_delivery (
    delivery_id BIGSERIAL PRIMARY KEY, alert_id UUID REFERENCES alerts(alert_id) ON DELETE CASCADE,
    channel TEXT NOT NULL CHECK (channel IN ('email','sms','push','webhook','slack')),
    recipient TEXT NOT NULL, status TEXT DEFAULT 'pending',
    attempts INTEGER DEFAULT 0, last_attempt_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ, error_message TEXT);""",

    # Billing (4)
    """CREATE TABLE IF NOT EXISTS billing.plans (
    plan_id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
    price_cents INTEGER NOT NULL DEFAULT 0, currency TEXT DEFAULT 'USD',
    billing_interval TEXT DEFAULT 'monthly' CHECK (billing_interval IN ('monthly','yearly')),
    features JSONB, limits JSONB, is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());

CREATE TABLE IF NOT EXISTS billing.subscriptions (
    subscription_id TEXT PRIMARY KEY, org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    plan_id TEXT REFERENCES billing.plans(plan_id),
    status TEXT DEFAULT 'active' CHECK (status IN ('active','trialing','past_due','canceled','unpaid','incomplete')),
    stripe_customer_id TEXT, stripe_subscription_id TEXT, stripe_price_id TEXT,
    current_period_start TIMESTAMPTZ, current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE, canceled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_subs_org ON billing.subscriptions(org_id);

CREATE TABLE IF NOT EXISTS billing.invoices (
    invoice_id TEXT PRIMARY KEY, org_id UUID REFERENCES organizations(org_id),
    subscription_id TEXT REFERENCES billing.subscriptions(subscription_id),
    stripe_invoice_id TEXT, amount_cents INTEGER NOT NULL DEFAULT 0, currency TEXT DEFAULT 'USD',
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft','open','paid','void','refunded')),
    due_date TIMESTAMPTZ, paid_at TIMESTAMPTZ,
    period_start TIMESTAMPTZ, period_end TIMESTAMPTZ, receipt_number TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_invoices_org ON billing.invoices(org_id, created_at DESC);

CREATE TABLE IF NOT EXISTS billing.usage_records (
    record_id BIGSERIAL PRIMARY KEY, org_id UUID REFERENCES organizations(org_id),
    subscription_id TEXT REFERENCES billing.subscriptions(subscription_id),
    metric_name TEXT NOT NULL, quantity NUMERIC(18,4) NOT NULL, unit TEXT DEFAULT 'unit',
    timestamp TIMESTAMPTZ DEFAULT NOW(), stripe_usage_record_id TEXT);
CREATE INDEX idx_usage_org ON billing.usage_records(org_id, metric_name, timestamp DESC);""",

    # Audit (3)
    """CREATE TABLE IF NOT EXISTS audit.log_entries (
    log_id BIGSERIAL PRIMARY KEY, org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    actor_id TEXT, actor_type TEXT DEFAULT 'user', action TEXT, resource_type TEXT, resource_id TEXT,
    previous_hash TEXT, current_hash TEXT, details JSONB, ip_address INET,
    trace_id TEXT, created_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_audit_org ON audit.log_entries(org_id, created_at DESC);

CREATE TABLE IF NOT EXISTS audit.hash_chain (
    chain_id BIGSERIAL PRIMARY KEY, org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
    block_number BIGINT NOT NULL, previous_hash TEXT NOT NULL, merkle_root TEXT NOT NULL,
    record_count INTEGER NOT NULL, batch_signature TEXT, created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, block_number));

CREATE TABLE IF NOT EXISTS audit.integrity_checks (
    check_id BIGSERIAL PRIMARY KEY, org_id UUID REFERENCES organizations(org_id),
    check_type TEXT NOT NULL, is_valid BOOLEAN NOT NULL, broken_links JSONB,
    details JSONB, performed_by TEXT, created_at TIMESTAMPTZ DEFAULT NOW());""",

    # ML Model Registry (4)
    """CREATE TABLE IF NOT EXISTS ml.model_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), org_id UUID REFERENCES organizations(org_id),
    name TEXT NOT NULL, version TEXT NOT NULL, framework TEXT CHECK (framework IN ('pytorch','onnx','tflite','openvino','tensorrt')),
    architecture TEXT, input_shape INTEGER[], output_dim INTEGER, description TEXT,
    training_dataset TEXT, training_params JSONB, metrics JSONB DEFAULT '{}',
    model_path TEXT NOT NULL, size_bytes BIGINT, checksum CHAR(64), signature TEXT,
    status TEXT DEFAULT 'staging' CHECK (status IN ('draft','staging','production','deprecated','archived')),
    tags JSONB DEFAULT '[]', min_requirements JSONB DEFAULT '{}', uploaded_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(), updated_at TIMESTAMPTZ DEFAULT NOW(), download_count INTEGER DEFAULT 0,
    promoted_at TIMESTAMPTZ, UNIQUE(name, version));
CREATE INDEX idx_models_org ON ml.model_versions(org_id);
CREATE INDEX idx_models_status ON ml.model_versions(status);

CREATE TABLE IF NOT EXISTS ml.model_performance (
    metric_id BIGSERIAL PRIMARY KEY, model_version_id UUID REFERENCES ml.model_versions(version_id),
    dataset_name TEXT NOT NULL, accuracy FLOAT, precision FLOAT, recall FLOAT, f1_score FLOAT,
    auc_roc FLOAT, inference_latency_p50 FLOAT, inference_latency_p95 FLOAT, inference_latency_p99 FLOAT,
    tested_at TIMESTAMPTZ DEFAULT NOW());

CREATE TABLE IF NOT EXISTS ml.training_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_version_id UUID REFERENCES ml.model_versions(version_id),
    status TEXT DEFAULT 'pending', hyperparameters JSONB, training_data_path TEXT,
    epochs INTEGER, learning_rate FLOAT, batch_size INTEGER, final_loss FLOAT,
    final_metrics JSONB, compute_cost_usd FLOAT,
    started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ, created_at TIMESTAMPTZ DEFAULT NOW());

CREATE TABLE IF NOT EXISTS ml.model_drift (
    drift_id BIGSERIAL PRIMARY KEY, model_version_id UUID REFERENCES ml.model_versions(version_id),
    metric_name TEXT NOT NULL, baseline_value FLOAT, current_value FLOAT,
    drift_percentage FLOAT, threshold FLOAT, is_drifted BOOLEAN DEFAULT FALSE,
    detected_at TIMESTAMPTZ DEFAULT NOW());""",

    # Notifications (3)
    """CREATE TABLE IF NOT EXISTS notifications.outbox (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), org_id UUID REFERENCES organizations(org_id),
    user_id TEXT REFERENCES users(user_id), channel TEXT NOT NULL CHECK (channel IN ('email','sms','push','webhook','in_app')),
    template_id TEXT, subject TEXT, body TEXT, payload JSONB, priority TEXT DEFAULT 'normal',
    status TEXT DEFAULT 'pending', attempts INTEGER DEFAULT 0, max_attempts INTEGER DEFAULT 3,
    next_retry_at TIMESTAMPTZ, last_error TEXT, sent_at TIMESTAMPTZ, delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW());

CREATE TABLE IF NOT EXISTS notifications.preferences (
    pref_id SERIAL PRIMARY KEY, user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE,
    notification_type TEXT NOT NULL, email_enabled BOOLEAN DEFAULT TRUE,
    push_enabled BOOLEAN DEFAULT TRUE, sms_enabled BOOLEAN DEFAULT FALSE,
    webhook_enabled BOOLEAN DEFAULT FALSE, quiet_hours_start TIME DEFAULT '22:00',
    quiet_hours_end TIME DEFAULT '07:00', UNIQUE(user_id, notification_type));

CREATE TABLE IF NOT EXISTS notification_templates (
    template_id TEXT PRIMARY KEY, name TEXT NOT NULL,
    subject_template TEXT NOT NULL, body_template TEXT NOT NULL,
    template_type TEXT NOT NULL CHECK (template_type IN ('email','sms','push','webhook')),
    variables JSONB, is_active BOOLEAN DEFAULT TRUE, created_at TIMESTAMPTZ DEFAULT NOW());""",

    # Compliance (3)
    """CREATE TABLE IF NOT EXISTS compliance.dsar_requests (
    request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), org_id UUID REFERENCES organizations(org_id),
    user_id TEXT REFERENCES users(user_id),
    request_type TEXT NOT NULL CHECK (request_type IN ('access','deletion','rectification','portability','objection')),
    status TEXT DEFAULT 'received' CHECK (status IN ('received','verified','processing','completed','denied')),
    reason TEXT, data_scope JSONB, reviewer_id TEXT, review_notes TEXT,
    due_date TIMESTAMPTZ, completed_at TIMESTAMPTZ, data_package_url TEXT, created_at TIMESTAMPTZ DEFAULT NOW());

CREATE TABLE IF NOT EXISTS compliance.consent_records (
    consent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id TEXT REFERENCES users(user_id),
    purpose TEXT NOT NULL, consent_text_version TEXT NOT NULL, granted BOOLEAN DEFAULT TRUE,
    granted_at TIMESTAMPTZ DEFAULT NOW(), revoked_at TIMESTAMPTZ, ip_address INET, metadata JSONB);
CREATE INDEX idx_consent_user ON compliance.consent_records(user_id);

CREATE TABLE IF NOT EXISTS compliance.data_retention_policies (
    policy_id SERIAL PRIMARY KEY, org_id UUID REFERENCES organizations(org_id),
    table_name TEXT NOT NULL, retention_days INTEGER NOT NULL, archival_action TEXT DEFAULT 'delete',
    last_executed TIMESTAMPTZ, next_execution TIMESTAMPTZ, is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW());""",

    # System Infrastructure (4)
    """CREATE TABLE IF NOT EXISTS system_config (
    config_key TEXT PRIMARY KEY, config_value JSONB NOT NULL, description TEXT,
    is_sensitive BOOLEAN DEFAULT FALSE, updated_at TIMESTAMPTZ DEFAULT NOW(), updated_by TEXT);

CREATE TABLE IF NOT EXISTS system_health (
    health_id BIGSERIAL PRIMARY KEY, service_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('healthy','degraded','unhealthy','maintenance')),
    latency_ms FLOAT, error_message TEXT, check_type TEXT DEFAULT 'heartbeat',
    metadata JSONB, created_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX idx_health_service ON system_health(service_name, created_at DESC);

CREATE TABLE IF NOT EXISTS system_celery_tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(), task_name TEXT NOT NULL, task_queue TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending','received','started','success','failure','revoked','retry')),
    args JSONB, kwargs JSONB, result JSONB, error_message TEXT, retries INTEGER DEFAULT 0, max_retries INTEGER DEFAULT 3,
    eta TIMESTAMPTZ, expires TIMESTAMPTZ, worker_hostname TEXT, execution_time_ms FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(), started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ);

CREATE TABLE IF NOT EXISTS system_backup_log (
    backup_id TEXT PRIMARY KEY, backup_type TEXT NOT NULL CHECK (backup_type IN ('full','incremental','wal','logical')),
    status TEXT NOT NULL CHECK (status IN ('started','completed','failed')),
    source_size_bytes BIGINT, compressed_size_bytes BIGINT, storage_location TEXT,
    encryption_enabled BOOLEAN DEFAULT TRUE, checksum TEXT, retention_until TIMESTAMPTZ,
    duration_seconds FLOAT, error_message TEXT, started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ);""",

    # Redis Cache Layer (2)
    """CREATE TABLE IF NOT EXISTS redis.cache_manifest (
    cache_key TEXT PRIMARY KEY, cache_type TEXT NOT NULL, entity_type TEXT, entity_id TEXT,
    ttl_seconds INTEGER, invalidation_channel TEXT, dependencies JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(), expires_at TIMESTAMPTZ);

CREATE TABLE IF NOT EXISTS redis.rate_limit_buckets (
    bucket_id TEXT PRIMARY KEY, identifier TEXT NOT NULL, endpoint TEXT NOT NULL,
    tokens_remaining INTEGER NOT NULL, capacity INTEGER NOT NULL, refill_rate REAL NOT NULL,
    last_refill TIMESTAMPTZ DEFAULT NOW(), expires_at TIMESTAMPTZ NOT NULL, metadata JSONB);
CREATE INDEX idx_rate_limit_ident ON redis.rate_limit_buckets(identifier, endpoint);""",
]

for i, part in enumerate(tables):
    sql_parts.append(f"\n-- ============================================\n-- Table Set {i+1}\n-- ============================================\n")
    sql_parts.append(part)

# RLS Policies
rls = """
-- ============================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================

-- Organizations
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
CREATE POLICY org_read_policy ON organizations FOR SELECT USING (is_active);
CREATE POLICY org_write_policy ON organizations FOR ALL USING (current_setting('app.current_role', true) IN ('owner','admin'));

-- Org Members
ALTER TABLE org_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY org_members_policy ON org_members FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- API Keys
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
CREATE POLICY api_keys_policy ON api_keys FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Org Audit Log
ALTER TABLE org_audit_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY org_audit_rls ON org_audit_log FOR SELECT USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Users
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY users_self ON users FOR SELECT USING (user_id = current_setting('app.current_user_id', true) OR current_setting('app.current_role', true) IN ('owner','admin'));
CREATE POLICY users_write ON users FOR INSERT WITH CHECK (TRUE);

-- Sessions
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY sessions_rls ON user_sessions FOR ALL USING (user_id = current_setting('app.current_user_id', true));

-- Preferences
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;
CREATE POLICY prefs_rls ON user_preferences FOR ALL USING (user_id = current_setting('app.current_user_id', true));

-- Activity Log
ALTER TABLE user_activity_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY activity_rls ON user_activity_log FOR ALL USING (user_id = current_setting('app.current_user_id', true));

-- Password Reset
ALTER TABLE password_reset_tokens ENABLE ROW LEVEL SECURITY;
CREATE POLICY reset_rls ON password_reset_tokens FOR ALL USING (user_id = current_setting('app.current_user_id', true));

-- Persons
ALTER TABLE persons ENABLE ROW LEVEL SECURITY;
CREATE POLICY persons_rls ON persons FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Enrollments
ALTER TABLE enrollments ENABLE ROW LEVEL SECURITY;
CREATE POLICY enrollments_rls ON enrollments FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Embeddings (via person->org)
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;
CREATE POLICY embeddings_rls ON embeddings FOR ALL USING (EXISTS (SELECT 1 FROM persons WHERE persons.person_id = embeddings.person_id AND persons.org_id = current_setting('app.current_org_id', true)::uuid));

-- Face Templates
ALTER TABLE face_templates ENABLE ROW LEVEL SECURITY;
CREATE POLICY ftemplates_rls ON face_templates FOR ALL USING (EXISTS (SELECT 1 FROM persons WHERE persons.person_id = face_templates.person_id AND persons.org_id = current_setting('app.current_org_id', true)::uuid));

-- Voice Profiles
ALTER TABLE voice_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY vprofiles_rls ON voice_profiles FOR ALL USING (EXISTS (SELECT 1 FROM persons WHERE persons.person_id = voice_profiles.person_id AND persons.org_id = current_setting('app.current_org_id', true)::uuid));

-- Gait Profiles
ALTER TABLE gait_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY gprofiles_rls ON gait_profiles FOR ALL USING (EXISTS (SELECT 1 FROM persons WHERE persons.person_id = gait_profiles.person_id AND persons.org_id = current_setting('app.current_org_id', true)::uuid));

-- Iris Profiles
ALTER TABLE iris_profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY iris_rls ON iris_profiles FOR ALL USING (EXISTS (SELECT 1 FROM persons WHERE persons.person_id = iris_profiles.person_id AND persons.org_id = current_setting('app.current_org_id', true)::uuid));

-- Cameras
ALTER TABLE cameras ENABLE ROW LEVEL SECURITY;
CREATE POLICY cameras_rls ON cameras FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Edge Devices
ALTER TABLE edge_devices ENABLE ROW LEVEL SECURITY;
CREATE POLICY edevices_rls ON edge_devices FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Camera Groups
ALTER TABLE camera_groups ENABLE ROW LEVEL SECURITY;
CREATE POLICY cgroups_rls ON camera_groups FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Camera Streams
ALTER TABLE camera_streams ENABLE ROW LEVEL SECURITY;
CREATE POLICY cstreams_rls ON camera_streams FOR ALL USING (EXISTS (SELECT 1 FROM cameras WHERE cameras.camera_id = camera_streams.camera_id AND cameras.org_id = current_setting('app.current_org_id', true)::uuid));

-- Device Health
ALTER TABLE device_health_checks ENABLE ROW LEVEL SECURITY;
CREATE POLICY dhealth_rls ON device_health_checks FOR SELECT USING (EXISTS (SELECT 1 FROM cameras WHERE cameras.camera_id = device_health_checks.camera_id AND cameras.org_id = current_setting('app.current_org_id', true)::uuid));

-- Recognition Events
ALTER TABLE recognition_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY rec_rls ON recognition_events FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Recognition Batches
ALTER TABLE recognition_batches ENABLE ROW LEVEL SECURITY;
CREATE POLICY rbatches_rls ON recognition_batches FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Recognition Quality
ALTER TABLE recognition_quality_metrics ENABLE ROW LEVEL SECURITY;
CREATE POLICY rqm_rls ON recognition_quality_metrics FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Video Processing
ALTER TABLE video_processing_jobs ENABLE ROW LEVEL SECURITY;
CREATE POLICY vpj_rls ON video_processing_jobs FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Alert Rules
ALTER TABLE alert_rules ENABLE ROW LEVEL SECURITY;
CREATE POLICY arules_rls ON alert_rules FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Alerts
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
CREATE POLICY alerts_rls ON alerts FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Alert Delivery
ALTER TABLE alert_delivery ENABLE ROW LEVEL SECURITY;
CREATE POLICY adelivery_rls ON alert_delivery FOR ALL USING (EXISTS (SELECT 1 FROM alerts WHERE alerts.alert_id = alert_delivery.alert_id AND alerts.org_id = current_setting('app.current_org_id', true)::uuid));

-- Billing Plans: global read
ALTER TABLE billing.plans ENABLE ROW LEVEL SECURITY;
CREATE POLICY plans_read ON billing.plans FOR SELECT USING (TRUE);

-- Billing Subscriptions
ALTER TABLE billing.subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY subs_rls ON billing.subscriptions FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Billing Invoices
ALTER TABLE billing.invoices ENABLE ROW LEVEL SECURITY;
CREATE POLICY invoices_rls ON billing.invoices FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Billing Usage
ALTER TABLE billing.usage_records ENABLE ROW LEVEL SECURITY;
CREATE POLICY usage_rls ON billing.usage_records FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Audit Logs
ALTER TABLE audit.log_entries ENABLE ROW LEVEL SECURITY;
CREATE POLICY audit_rls ON audit.log_entries FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Hash Chain
ALTER TABLE audit.hash_chain ENABLE ROW LEVEL SECURITY;
CREATE POLICY hchain_rls ON audit.hash_chain FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Integrity Checks
ALTER TABLE audit.integrity_checks ENABLE ROW LEVEL SECURITY;
CREATE POLICY icheck_rls ON audit.integrity_checks FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- ML Models: global read of production, org-scoped write
ALTER TABLE ml.model_versions ENABLE ROW LEVEL SECURITY;
CREATE POLICY models_read ON ml.model_versions FOR SELECT USING (status = 'production' OR current_setting('app.current_role', true) IN ('owner','admin'));
CREATE POLICY models_write ON ml.model_versions FOR INSERT WITH CHECK (org_id = current_setting('app.current_org_id', true)::uuid);

-- ML Performance: global read
ALTER TABLE ml.model_performance ENABLE ROW LEVEL SECURITY;
CREATE POLICY mperf_read ON ml.model_performance FOR SELECT USING (TRUE);

-- ML Training Runs
ALTER TABLE ml.training_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY mruns_rls ON ml.training_runs FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- ML Drift
ALTER TABLE ml.model_drift ENABLE ROW LEVEL SECURITY;
CREATE POLICY mdrift_rls ON ml.model_drift FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Notifications
ALTER TABLE notifications.outbox ENABLE ROW LEVEL SECURITY;
CREATE POLICY notif_rls ON notifications.outbox FOR ALL USING (user_id = current_setting('app.current_user_id', true));

ALTER TABLE notifications.preferences ENABLE ROW LEVEL SECURITY;
CREATE POLICY nprefs_rls ON notifications.preferences FOR ALL USING (user_id = current_setting('app.current_user_id', true));

ALTER TABLE notification_templates ENABLE ROW LEVEL SECURITY;
CREATE POLICY ntemplates_read ON notification_templates FOR SELECT USING (TRUE);

-- DSAR
ALTER TABLE compliance.dsar_requests ENABLE ROW LEVEL SECURITY;
CREATE POLICY dsar_rls ON compliance.dsar_requests FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Consent
ALTER TABLE compliance.consent_records ENABLE ROW LEVEL SECURITY;
CREATE POLICY consent_rls ON compliance.consent_records FOR ALL USING (user_id = current_setting('app.current_user_id', true));

-- Data Retention
ALTER TABLE compliance.data_retention_policies ENABLE ROW LEVEL SECURITY;
CREATE POLICY retention_rls ON compliance.data_retention_policies FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- System Config: admin only
ALTER TABLE system_config ENABLE ROW LEVEL SECURITY;
CREATE POLICY sysconfig_rls ON system_config FOR ALL USING (current_setting('app.current_role', true) IN ('owner','admin'));

-- System Health: admin only
ALTER TABLE system_health ENABLE ROW LEVEL SECURITY;
CREATE POLICY shealth_rls ON system_health FOR ALL USING (current_setting('app.current_role', true) IN ('owner','admin'));

-- Celery Tasks
ALTER TABLE system_celery_tasks ENABLE ROW LEVEL SECURITY;
CREATE POLICY celery_rls ON system_celery_tasks FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

-- Backup Log: admin only
ALTER TABLE system_backup_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY backup_rls ON system_backup_log FOR ALL USING (current_setting('app.current_role', true) IN ('owner','admin'));

-- Redis Cache
ALTER TABLE redis.cache_manifest ENABLE ROW LEVEL SECURITY;
CREATE POLICY rcache_rls ON redis.cache_manifest FOR ALL USING (org_id = current_setting('app.current_org_id', true)::uuid);

ALTER TABLE redis.rate_limit_buckets ENABLE ROW LEVEL SECURITY;
CREATE POLICY rrate_rls ON redis.rate_limit_buckets FOR ALL USING (EXISTS (SELECT 1 FROM org_members WHERE org_members.user_id = redis.rate_limit_buckets.identifier AND org_members.org_id = current_setting('app.current_org_id', true)::uuid));
"""
sql_parts.append("\n-- ROW LEVEL SECURITY POLICIES\n" + rls)

# Seeds
seeds = """
-- ============================================
-- SEED DATA
-- ============================================
INSERT INTO billing.plans (plan_id, name, description, price_cents, billing_interval, features, limits) VALUES
  ('free', 'Free Starter', 'Basic recognition', 0, 'monthly', '["Basic Recognition", "10 Enrollments"]', '{"recognitions": 100, "enrollments": 10}'),
  ('pro', 'Pro Developer', 'Advanced features', 2900, 'monthly', '["Advanced Recognition", "1000 Enrollments", "Priority Support"]', '{"recognitions": 10000, "enrollments": 1000}'),
  ('enterprise', 'Enterprise Scale', 'Unlimited', 19900, 'monthly', '["Unlimited", "24/7 Support", "Analytics", "ZKP"]', '{"recognitions": -1, "enrollments": -1}')
ON CONFLICT (plan_id) DO NOTHING;
"""
sql_parts.append("\n" + seeds)

full_sql = "\n".join(sql_parts)
wf(os.path.join(BASE, "infra/init.sql"), full_sql)
print(f"=== init.sql written ({len(full_sql)} chars, ~{len(full_sql.split('CREATE TABLE'))-1} tables) ===")
"""
wf(os.path.join(BASE, "scratch/gen_infra.py"), main_py)
print("Generator written")
"""