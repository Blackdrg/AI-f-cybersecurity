-- Demo Data Seed Script for AI-f Face Recognition System
-- Run this script to populate demo credentials and test data
-- 
-- Usage:
--   psql -U postgres -d face_recognition -f seed_demo.sql
-- Or in Docker:
--   docker-compose exec -T postgres psql -U postgres -d face_recognition < seed_demo.sql

-- Begin transaction for atomic insert
BEGIN;

-- ============================================
-- CREATE DEMO ORGANIZATIONS
-- ============================================
INSERT INTO organizations (org_id, name, tier, created_at, status)
VALUES 
    ('org_demo', 'Demo Organization', 'free', NOW(), 'active'),
    ('org_pro', 'Pro Test Organization', 'pro', NOW(), 'active'),
    ('org_enterprise', 'Enterprise Test Organization', 'enterprise', NOW(), 'active')
ON CONFLICT (org_id) DO NOTHING;

-- ============================================
-- CREATE DEMO USERS  
-- ============================================
INSERT INTO users (user_id, email, password_hash, name, created_at, mfa_enabled)
VALUES 
    ('usr_demo', 'demo@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqF3Z8QTVeW', 'Demo User', NOW(), false),
    ('usr_admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqF3Z8QTVeW', 'Admin User', NOW(), true),
    ('usr_operator', 'operator@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqF3Z8QTVeW', 'Operator User', NOW(), false)
ON CONFLICT (user_id) DO NOTHING;

-- Password for all demo users: 'password' (bcrypt hash above)
-- Note: In production, use properly hashed passwords!

-- ============================================
-- CREATE ORGANIZATION MEMBERSHIPS
-- ============================================
INSERT INTO org_members (user_id, org_id, role, joined_at)
VALUES
    ('usr_demo', 'org_demo', 'viewer', NOW()),
    ('usr_admin', 'org_demo', 'admin', NOW()),
    ('usr_admin', 'org_pro', 'admin', NOW()),
    ('usr_admin', 'org_enterprise', 'admin', NOW()),
    ('usr_operator', 'org_demo', 'operator', NOW())
ON CONFLICT DO NOTHING;

-- ============================================
-- CREATE API KEYS
-- ============================================
INSERT INTO api_keys (key_id, user_id, org_id, name, prefix, created_at, last_used, is_active)
VALUES 
    ('key_demo_001', 'usr_demo', 'org_demo', 'Demo API Key', 'sk_demo_', NOW(), NULL, true),
    ('key_admin_001', 'usr_admin', 'org_demo', 'Admin API Key', 'sk_admin', NOW(), NULL, true),
    ('key_operator_001', 'usr_operator', 'org_demo', 'Operator API Key', 'sk_oper_', NOW(), NULL, true)
ON CONFLICT (key_id) DO NOTHING;

-- ============================================
-- CREATE DEMO PERSONS (for testing recognition)
-- ============================================
INSERT INTO persons (person_id, org_id, name, created_at, consent_given, consent_timestamp)
VALUES 
    ('pers_alice', 'org_demo', 'Alice Johnson', NOW(), true, NOW()),
    ('pers_bob', 'org_demo', 'Bob Smith', NOW(), true, NOW()),
    ('pers_carol', 'org_demo', 'Carol Williams', NOW(), true, NOW())
ON CONFLICT (person_id) DO NOTHING;

-- ============================================
-- CREATE DEMO CAMERAS
-- ============================================
INSERT INTO cameras (camera_id, org_id, name, rtsp_url, location, created_at, is_active)
VALUES 
    ('cam_lobby', 'org_demo', 'Lobby Camera', 'rtsp://demo.example.com/lobby', 'Building A - Lobby', NOW(), true),
    ('cam_entrance', 'org_demo', 'Main Entrance', 'rtsp://demo.example.com/entrance', 'Building A - Entrance', NOW(), true),
    ('cam_parking', 'org_demo', 'Parking Lot', 'rtsp://demo.example.com/parking', 'Parking Lot', NOW(), true)
ON CONFLICT (camera_id) DO NOTHING;

-- ============================================
-- CREATE DEMO SUBSCRIPTIONS
-- ============================================
INSERT INTO subscriptions (subscription_id, user_id, org_id, plan, status, created_at, current_period_end)
VALUES 
    ('sub_free_001', 'usr_demo', 'org_demo', 'free', 'active', NOW(), NOW() + interval '30 days'),
    ('sub_pro_001', 'usr_admin', 'org_pro', 'pro', 'active', NOW() + interval '30 days'),
    ('sub_enterprise_001', 'usr_admin', 'org_enterprise', 'enterprise', 'active', NOW() + interval '30 days')
ON CONFLICT (subscription_id) DO NOTHING;

-- Commit transaction
COMMIT;

-- ============================================
-- VERIFY SEED DATA
-- ============================================
SELECT 'Organizations:' AS info, COUNT(*) AS count FROM organizations
UNION ALL
SELECT 'Users:', COUNT(*) FROM users
UNION ALL
SELECT 'API Keys:', COUNT(*) FROM api_keys WHERE is_active = true
UNION ALL
SELECT 'Demo Persons:', COUNT(*) FROM persons WHERE org_id = 'org_demo';

-- ============================================
-- QUICK TEST QUERIES
-- ============================================

-- View demo users:
-- SELECT user_id, email, name FROM users WHERE email LIKE '%example.com%';

-- View API keys:
-- SELECT key_id, name, prefix || '****' || substring(key_id, -4) AS key_preview 
-- FROM api_keys WHERE is_active = true;

-- Demo credentials to use:
--   Demo User:    demo@example.com / password
--   Admin:      admin@example.com / password  
--   Operator:   operator@example.com / password
--
-- API Keys:
--   Demo:    sk_demo_xxxxxxxxxxxx (use full key from api_keys table)
--   Admin:   sk_adminxxxxxxxxxxxx
