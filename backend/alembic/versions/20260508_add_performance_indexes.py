"""Add performance-critical indexes for query optimization.

Revision ID: add_performance_indexes
Revises: e7c74bf31b19
Create Date: 2026-05-08

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_performance_indexes'
down_revision: Union[str, Sequence[str], None] = 'e7c74bf31b19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexes for frequently queried columns."""
    
    # =============================================================================
    # Persons and Embeddings (recognition pipeline)
    # =============================================================================
    
    # Index for person lookups
    op.create_index(
        'idx_persons_person_id',
        'persons',
        ['person_id'],
        unique=False
    )
    
    # Index for filtering persons by org
    op.create_index(
        'idx_persons_org_id',
        'persons',
        ['org_id'],
        unique=False
    )
    
    # Composite index for common query pattern: find person by org and name
    op.create_index(
        'idx_persons_org_created',
        'persons',
        ['org_id', sa.text('created_at DESC')],
        unique=False
    )
    
    # Embeddings: person_id is frequently queried
    op.create_index(
        'idx_embeddings_person_id',
        'embeddings',
        ['person_id'],
        unique=False
    )
    
    # Existing hnsw index on embedding vector (already exists from initial schema)
    # Ensure it's there with proper parameters
    # op.execute("""
    #     CREATE INDEX IF NOT EXISTS embedding_idx ON embeddings 
    #     USING hnsw (embedding vector_cosine_ops) 
    #     WITH (m=16, ef_construction=64)
    # """)
    
    # Index for camera-based queries
    op.create_index(
        'idx_embeddings_camera_id',
        'embeddings',
        ['camera_id'],
        unique=False
    )
    
    # Partial index for active (non-deleted) persons only
    op.create_index(
        'idx_persons_active',
        'persons',
        ['org_id'],
        postgresql_where=sa.text("deleted_at IS NULL")
    )
    
    # =============================================================================
    # Users and Subscriptions (SaaS queries)
    # =============================================================================
    
    # Already have primary key on user_id, add indexes for email lookup
    op.create_index(
        'idx_users_email',
        'users',
        ['email'],
        unique=False
    )
    
    # Index for subscription lookups by user
    op.create_index(
        'idx_subscriptions_user_id',
        'subscriptions',
        ['user_id'],
        unique=False
    )
    
    # Composite index for active subscription queries
    op.create_index(
        'idx_subscriptions_user_status',
        'subscriptions',
        ['user_id', 'status'],
        unique=False
    )
    
    # Index for subscription expiry checks
    op.create_index(
        'idx_subscriptions_expires',
        'subscriptions',
        ['expires_at'],
        unique=False,
        postgresql_where=sa.text("status = 'active'")
    )
    
    # Index on plans for tier lookups
    op.create_index(
        'idx_plans_tier',
        'plans',
        ['subscription_tier'],
        unique=False
    )
    
    # =============================================================================
    # Recognition Events (analytics and timeline)
    # =============================================================================
    
    # Index for camera-based event queries
    op.create_index(
        'idx_recognition_events_camera',
        'recognition_events',
        ['camera_id', 'timestamp DESC'],
        unique=False
    )
    
    # Index for person-based event queries
    op.create_index(
        'idx_recognition_events_person',
        'recognition_events',
        ['person_id', sa.text('timestamp DESC')],
        unique=False
    )
    
    # Index for organization-based queries
    op.create_index(
        'idx_recognition_events_org',
        'recognition_events',
        ['org_id', sa.text('timestamp DESC')],
        unique=False
    )
    
    # Index for time-based analytics queries
    op.create_index(
        'idx_recognition_events_timestamp',
        'recognition_events',
        [sa.text('timestamp DESC')],
        unique=False
    )
    
    # Composite index for common filter: org + camera + time
    op.create_index(
        'idx_recognition_events_org_camera_time',
        'recognition_events',
        ['org_id', 'camera_id', sa.text('timestamp DESC')],
        unique=False
    )
    
    # Index on confidence_score for filtering low-confidence matches
    op.create_index(
        'idx_recognition_events_confidence',
        'recognition_events',
        ['confidence_score'],
        unique=False
    )
    
    # =============================================================================
    # Auditing and Compliance
    # =============================================================================
    
    # Index for audit log queries by person_id (GDPR)
    op.create_index(
        'idx_audit_log_person_id',
        'audit_log',
        ['person_id'],
        unique=False
    )
    
    # Index for audit log by timestamp (chronological queries)
    op.create_index(
        'idx_audit_log_timestamp',
        'audit_log',
        [sa.text('timestamp DESC')],
        unique=False
    )
    
    # Composite index for action + time queries
    op.create_index(
        'idx_audit_log_action_time',
        'audit_log',
        ['action', sa.text('timestamp DESC')],
        unique=False
    )
    
    # Index for hash chain verification
    op.create_index(
        'idx_audit_log_hash',
        'audit_log',
        ['hash'],
        unique=False
    )
    
    # =============================================================================
    # Cameras and Edge Devices
    # =============================================================================
    
    # Index for camera status queries
    op.create_index(
        'idx_cameras_org_status',
        'cameras',
        ['org_id', 'status'],
        unique=False
    )
    
    # Index for edge device last_seen (stale device detection)
    op.create_index(
        'idx_edge_devices_last_seen',
        'edge_devices',
        [sa.text('last_seen DESC')],
        unique=False
    )
    
    # =============================================================================
    # Support Tickets
    # =============================================================================
    
    # Index for user's tickets
    op.create_index(
        'idx_support_tickets_user',
        'support_tickets',
        ['user_id', sa.text('created_at DESC')],
        unique=False
    )
    
    # Index for status filtering
    op.create_index(
        'idx_support_tickets_status',
        'support_tickets',
        ['status'],
        unique=False
    )
    
    # =============================================================================
    # Enrichment Results (TTL-based cleanup)
    # =============================================================================
    
    # Index for TTL cleanup of expired enrichment results
    op.create_index(
        'idx_enrichment_results_expires',
        'enrichment_results',
        ['expires_at'],
        unique=False,
        postgresql_where=sa.text("expires_at IS NOT NULL")
    )
    
    # Index for query caching lookups
    op.create_index(
        'idx_enrichment_results_query',
        'enrichment_results',
        ['query'],
        unique=False
    )
    
    # =============================================================================
    # Model Versions (model registry)
    # =============================================================================
    
    # Index for model version lookups
    op.create_index(
        'idx_model_versions_name_version',
        'model_versions',
        ['name', 'version'],
        unique=False
    )
    
    # Index for status-based filtering (staging, active, deprecated)
    op.create_index(
        'idx_model_versions_status',
        'model_versions',
        ['status'],
        unique=False
    )
    
    # =============================================================================
    # Federated Learning Updates
    # =============================================================================
    
    op.create_index(
        'idx_federated_updates_device',
        'federated_updates',
        ['device_id', sa.text('timestamp DESC')],
        unique=False
    )


def downgrade() -> None:
    """Remove all indexes created in upgrade."""
    
    # Drop in reverse order
    op.drop_index('idx_federated_updates_device', table_name='federated_updates')
    op.drop_index('idx_model_versions_status', table_name='model_versions')
    op.drop_index('idx_model_versions_name_version', table_name='model_versions')
    op.drop_index('idx_enrichment_results_expires', table_name='enrichment_results')
    op.drop_index('idx_enrichment_results_query', table_name='enrichment_results')
    op.drop_index('idx_support_tickets_status', table_name='support_tickets')
    op.drop_index('idx_support_tickets_user', table_name='support_tickets')
    op.drop_index('idx_edge_devices_last_seen', table_name='edge_devices')
    op.drop_index('idx_cameras_org_status', table_name='cameras')
    op.drop_index('idx_audit_log_hash', table_name='audit_log')
    op.drop_index('idx_audit_log_action_time', table_name='audit_log')
    op.drop_index('idx_audit_log_timestamp', table_name='audit_log')
    op.drop_index('idx_audit_log_person_id', table_name='audit_log')
    op.drop_index('idx_recognition_events_confidence', table_name='recognition_events')
    op.drop_index('idx_recognition_events_org_camera_time', table_name='recognition_events')
    op.drop_index('idx_recognition_events_timestamp', table_name='recognition_events')
    op.drop_index('idx_recognition_events_org', table_name='recognition_events')
    op.drop_index('idx_recognition_events_person', table_name='recognition_events')
    op.drop_index('idx_recognition_events_camera', table_name='recognition_events')
    op.drop_index('idx_subscriptions_expires', table_name='subscriptions')
    op.drop_index('idx_subscriptions_user_status', table_name='subscriptions')
    op.drop_index('idx_subscriptions_user_id', table_name='subscriptions')
    op.drop_index('idx_users_email', table_name='users')
    op.drop_index('idx_embeddings_camera_id', table_name='embeddings')
    op.drop_index('idx_embeddings_person_id', table_name='embeddings')
    op.drop_index('idx_persons_active', table_name='persons')
    op.drop_index('idx_persons_org_created', table_name='persons')
    op.drop_index('idx_persons_org_id', table_name='persons')
    op.drop_index('idx_persons_person_id', table_name='persons')
