"""add performance indexes for production scaling

Revision ID: idx_001
Revises: 30236ede6f7f
Create Date: 2025-04-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'idx_001'
down_revision: Union[str, Sequence[str], None] = '30236ede6f7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexes for performance optimization."""
    conn = op.get_bind()
    
    # --- persons table indexes ---
    op.create_index('ix_persons_org_id', 'persons', ['org_id'])
    op.create_index('ix_persons_name', 'persons', ['name'])
    
    # --- embeddings table indexes ---
    # Vector index for similarity search (HNSW preferred, fallback to IVFFlat)
    try:
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_embeddings_embedding 
            ON embeddings 
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)
    except Exception:
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_embeddings_embedding 
            ON embeddings 
            USING ivfflat (embedding vector_l2_ops)
            WITH (lists = 100)
        """)
    
    op.create_index('ix_embeddings_person_id', 'embeddings', ['person_id'])
    op.create_index('ix_embeddings_camera_id', 'embeddings', ['camera_id'])
    op.create_index('ix_embeddings_voice', 'embeddings', 
                    sa.text('(voice_embedding IS NOT NULL)'),
                    postgresql_where='voice_embedding IS NOT NULL')
    op.create_index('ix_embeddings_gait', 'embeddings', 
                    sa.text('(gait_embedding IS NOT NULL)'),
                    postgresql_where='gait_embedding IS NOT NULL')
    
    # --- consent_logs indexes ---
    op.create_index('ix_consent_logs_person_id', 'consent_logs', ['person_id'])
    op.create_index('ix_consent_logs_token', 'consent_logs', ['signed_token'], unique=True)
    
    # --- feedback indexes ---
    op.create_index('ix_feedback_person_id', 'feedback', ['person_id'])
    op.create_index('ix_feedback_recognition_id', 'feedback', ['recognition_id'])
    
    # --- organizations indexes ---
    op.create_index('ix_organizations_tier', 'organizations', ['subscription_tier'])
    
    # --- org_members indexes ---
    op.create_index('ix_org_members_user_id', 'org_members', ['user_id'])
    op.create_index('ix_org_members_role', 'org_members', ['role'])
    
    # --- users indexes ---
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_subscription_tier', 'users', ['subscription_tier'])
    
    # --- subscriptions indexes ---
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'])
    op.create_index('ix_subscriptions_status', 'subscriptions', ['status'])
    op.create_index('ix_subscriptions_plan_id', 'subscriptions', ['plan_id'])
    
    # --- payments indexes ---
    op.create_index('ix_payments_user_id', 'payments', ['user_id'])
    op.create_index('ix_payments_status', 'payments', ['status'])
    op.create_index('ix_payments_created_at', 'payments', ['created_at'], 
                    sa.text('DESC'))
    
    # --- support_tickets indexes ---
    op.create_index('ix_support_tickets_user_id', 'support_tickets', ['user_id'])
    op.create_index('ix_support_tickets_status', 'support_tickets', ['status'])
    op.create_index('ix_support_tickets_priority', 'support_tickets', ['priority'])
    
    # --- cameras indexes ---
    op.create_index('ix_cameras_org_id', 'cameras', ['org_id'])
    op.create_index('ix_cameras_status', 'cameras', ['status'])
    
    # --- recognition_events indexes (critical for analytics) ---
    op.create_index('ix_recognition_events_org_id', 'recognition_events', ['org_id'])
    op.create_index('ix_recognition_events_timestamp', 'recognition_events', 
                    ['timestamp'], sa.text('DESC'))
    op.create_index('ix_recognition_events_camera_id', 'recognition_events', ['camera_id'])
    op.create_index('ix_recognition_events_person_id', 'recognition_events', ['person_id'])
    op.create_index('ix_recognition_events_org_timestamp', 
                    'recognition_events', ['org_id', sa.text('timestamp DESC')])
    op.create_index('ix_recognition_events_camera_timestamp', 
                    'recognition_events', ['camera_id', sa.text('timestamp DESC')])
    
    # --- alerts indexes ---
    op.create_index('ix_alerts_rule_id', 'alerts', ['rule_id'])
    op.create_index('ix_alerts_status', 'alerts', ['status'])
    
    # --- audit_logs indexes ---
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'], 
                    sa.text('DESC'))
    
    # --- edge_devices indexes ---
    op.create_index('ix_edge_devices_model_version', 'edge_devices', ['model_version'])
    
    # --- enrichment_results indexes ---
    op.create_index('ix_enrichment_results_expires', 'enrichment_results', 
                    ['expires_at'])
    op.create_index('ix_enrichment_results_requested_by', 'enrichment_results', 
                    ['requested_by'])
    
    # Create GIN indexes for JSONB columns commonly queried
    op.create_index('ix_org_members_scopes', 'api_keys', 
                    sa.text("(scopes)"), 
                    postgresql_using='gin')
    
    op.execute("COMMIT")


def downgrade() -> None:
    """Remove performance indexes."""
    conn = op.get_bind()
    
    # Drop in reverse order
    indexes = [
        'ix_org_members_scopes',
        'ix_enrichment_results_requested_by',
        'ix_enrichment_results_expires',
        'ix_edge_devices_model_version',
        'ix_audit_logs_created_at',
        'ix_audit_logs_user_id',
        'ix_alerts_status',
        'ix_alerts_rule_id',
        'ix_recognition_events_camera_timestamp',
        'ix_recognition_events_org_timestamp',
        'ix_recognition_events_timestamp',
        'ix_recognition_events_person_id',
        'ix_recognition_events_camera_id',
        'ix_recognition_events_org_id',
        'ix_cameras_status',
        'ix_cameras_org_id',
        'ix_support_tickets_priority',
        'ix_support_tickets_status',
        'ix_support_tickets_user_id',
        'ix_payments_created_at',
        'ix_payments_status',
        'ix_payments_user_id',
        'ix_subscriptions_plan_id',
        'ix_subscriptions_status',
        'ix_subscriptions_user_id',
        'ix_users_subscription_tier',
        'ix_users_email',
        'ix_org_members_role',
        'ix_org_members_user_id',
        'ix_organizations_tier',
        'ix_feedback_recognition_id',
        'ix_feedback_person_id',
        'ix_consent_logs_token',
        'ix_consent_logs_person_id',
        'ix_embeddings_gait',
        'ix_embeddings_voice',
        'ix_embeddings_camera_id',
        'ix_embeddings_person_id',
        'ix_embeddings_embedding',
        'ix_persons_name',
        'ix_persons_org_id',
    ]
    
    for idx in indexes:
        try:
            op.drop_index(idx)
        except Exception:
            pass
    
    op.execute("COMMIT")
