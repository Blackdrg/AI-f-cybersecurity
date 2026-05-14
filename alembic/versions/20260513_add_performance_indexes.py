"""Migration: Add performance indexes for production query patterns.
Revision: 20260513_add_performance_indexes
Revises: 002_add_stripe_columns
"""
from alembic import op
import sqlalchemy as sa

revision = '20260513_add_performance_indexes'
down_revision = '002_add_stripe_columns'
branch_labels = None
depends_on = None

def upgrade():
    # Vector HNSW indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw_face
        ON embeddings USING hnsw (embedding vector_cosine_ops)
        WITH (m=32, ef_construction=128)""")
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw_voice
        ON embeddings USING hnsw (voice_embedding vector_cosine_ops)
        WITH (m=16, ef_construction=64)""")
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_embeddings_hnsw_gait
        ON embeddings USING hnsw (gait_embedding vector_cosine_ops)
        WITH (m=16, ef_construction=64)""")

    # Composite B-tree indexes
    op.create_index('idx_recog_events_org_time', 'recognition_events',
        ['org_id', sa.text('created_at DESC')])
    op.create_index('idx_recog_events_camera_time', 'recognition_events',
        ['camera_id', sa.text('created_at DESC')])
    op.create_index('idx_recog_events_person', 'recognition_events',
        ['person_id', sa.text('created_at DESC')])
    op.create_index('idx_persons_org_name', 'persons', ['org_id', 'name'])
    op.create_index('idx_persons_risk_high', 'persons', ['risk_level'],
        postgresql_where=sa.text("risk_level IN ('high','critical')"))
    op.create_index('idx_persons_metadata_gin', 'persons', ['metadata'],
        postgresql_using='gin')
    op.create_index('idx_cameras_org_status', 'cameras', ['org_id', 'status'])
    op.create_index('idx_cameras_online', 'cameras', ['status'],
        postgresql_where=sa.text("status='online'"))
    op.create_index('idx_edge_devices_org_status', 'edge_devices', ['org_id', 'status'])
    op.create_index('idx_edge_devices_last_seen', 'edge_devices',
        [sa.text('last_seen_at DESC')])
    op.create_index('idx_alerts_org_severity', 'alerts', ['org_id', 'severity'])
    op.create_index('idx_alerts_org_status', 'alerts', ['org_id', 'status'])
    op.create_index('idx_alerts_unresolved', 'alerts', ['org_id'],
        postgresql_where=sa.text("status IN ('new','acknowledged','investigating','escalated')"))
    op.create_index('idx_alert_rules_active', 'alert_rules', ['org_id'],
        postgresql_where=sa.text("is_active=true"))
    op.create_index('idx_sessions_active', 'user_sessions', ['user_id', 'is_active'],
        postgresql_where=sa.text("is_active=true"))
    op.create_index('idx_sessions_expiry', 'user_sessions',
        [sa.text('expires_at ASC')])
    op.create_index('idx_sessions_user', 'user_sessions', ['user_id'])

    # Analyze
    for table in ['persons','embeddings','recognition_events','alerts',
                  'alert_rules','cameras','edge_devices','user_sessions']:
        op.execute("ANALYZE %s" % table)

def downgrade():
    for idx in ['idx_embeddings_hnsw_face','idx_embeddings_hnsw_voice',
        'idx_embeddings_hnsw_gait','idx_recog_events_org_time',
        'idx_recog_events_camera_time','idx_recog_events_person',
        'idx_persons_org_name','idx_persons_risk_high',
        'idx_persons_metadata_gin','idx_cameras_org_status',
        'idx_cameras_online','idx_edge_devices_org_status',
        'idx_edge_devices_last_seen','idx_alerts_org_severity',
        'idx_alerts_org_status','idx_alerts_unresolved',
        'idx_alert_rules_active','idx_sessions_active',
        'idx_sessions_expiry','idx_sessions_user']:
        op.drop_index(idx, if_exists=True)