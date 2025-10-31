-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create tables for face recognition system
CREATE TABLE IF NOT EXISTS persons (
    person_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id SERIAL PRIMARY KEY,
    person_id VARCHAR REFERENCES persons(person_id) ON DELETE CASCADE,
    embedding BYTEA NOT NULL,
    camera_id VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Multi-modal embeddings
CREATE TABLE IF NOT EXISTS voice_embeddings (
    embedding_id SERIAL PRIMARY KEY,
    person_id VARCHAR REFERENCES persons(person_id) ON DELETE CASCADE,
    embedding BYTEA NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gait_embeddings (
    embedding_id SERIAL PRIMARY KEY,
    person_id VARCHAR REFERENCES persons(person_id) ON DELETE CASCADE,
    embedding BYTEA NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- User consent vault
CREATE TABLE IF NOT EXISTS consent_vault (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    biometric_type VARCHAR NOT NULL,
    granted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, biometric_type)
);

-- Create vector index for embeddings
CREATE INDEX IF NOT EXISTS embeddings_vector_idx ON embeddings USING ivfflat ((embedding::vector(512)));

-- Create audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    action VARCHAR NOT NULL,
    user_id VARCHAR,
    details JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Create feedback table for adaptive learning
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    person_id VARCHAR,
    recognition_id VARCHAR,
    correct_person_id VARCHAR,
    confidence_score FLOAT,
    feedback_type VARCHAR,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- SaaS Tables
CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    subscription_tier VARCHAR DEFAULT 'free',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS plans (
    plan_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    features JSONB,
    limits JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS subscriptions (
    subscription_id VARCHAR PRIMARY KEY,
    user_id VARCHAR REFERENCES users(user_id),
    plan_id VARCHAR REFERENCES plans(plan_id),
    status VARCHAR DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id VARCHAR PRIMARY KEY,
    user_id VARCHAR REFERENCES users(user_id),
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR DEFAULT 'USD',
    status VARCHAR DEFAULT 'pending',
    stripe_payment_id VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS usage (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR REFERENCES users(user_id),
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    recognitions_used INTEGER DEFAULT 0,
    enrollments_used INTEGER DEFAULT 0,
    recognitions_limit INTEGER,
    enrollments_limit INTEGER,
    UNIQUE(user_id, period_start, period_end)
);

CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id VARCHAR PRIMARY KEY,
    user_id VARCHAR REFERENCES users(user_id),
    subject VARCHAR NOT NULL,
    description TEXT,
    priority VARCHAR DEFAULT 'medium',
    status VARCHAR DEFAULT 'open',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
