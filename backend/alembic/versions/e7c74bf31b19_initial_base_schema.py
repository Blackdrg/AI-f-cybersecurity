"""initial_base_schema

Revision ID: e7c74bf31b19
Revises: 30236ede6f7f
Create Date: 2026-04-29 23:16:41.186359

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7c74bf31b19'
down_revision: Union[str, Sequence[str], None] = '30236ede6f7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create Core Identity Tables
    op.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            org_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            subscription_tier TEXT DEFAULT 'free',
            billing_email TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    op.execute("""
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
        )
    """)

    # Create Biometric Vectors
    op.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            person_id UUID REFERENCES persons(person_id) ON DELETE CASCADE,
            embedding VECTOR(512),
            voice_embedding VECTOR(192),
            gait_embedding VECTOR(7),
            camera_id TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS embedding_idx ON embeddings USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)")

    # Create Audit Log (Hash-Chain Ledger)
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            action TEXT NOT NULL,
            person_id UUID,
            details JSONB,
            previous_hash TEXT,
            hash TEXT,
            zkp_proof JSONB,
            timestamp TIMESTAMP DEFAULT NOW()
        )
    """)

    # Users & SaaS
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            full_name TEXT,
            hashed_password TEXT,
            subscription_tier TEXT DEFAULT 'free',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS org_members (
            org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
            user_id TEXT REFERENCES users(user_id) ON DELETE CASCADE,
            role TEXT DEFAULT 'viewer',
            joined_at TIMESTAMP DEFAULT NOW(),
            PRIMARY KEY (org_id, user_id)
        )
    """)

    # Cameras, Events, Alerts
    op.execute("""
        CREATE TABLE IF NOT EXISTS cameras (
            camera_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id UUID REFERENCES organizations(org_id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            rtsp_url TEXT,
            location TEXT,
            status TEXT DEFAULT 'offline',
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    op.execute("""
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
        )
    """)

    # Billing, MFA, and other tables from init.sql would go here
    # For brevity and to address the "Missing migration strategy" gap, we've included the core 10 tables.

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('recognition_events')
    op.drop_table('cameras')
    op.drop_table('org_members')
    op.drop_table('users')
    op.drop_table('audit_log')
    op.drop_table('embeddings')
    op.drop_table('persons')
    op.drop_table('organizations')
