"""Add alert and incident tables for monitoring and incident management.

Revision ID: 20260508_add_alert_tables
Revises: 20260508_add_performance_indexes
Create Date: 2026-05-08

"""
from alembic import op
import sqlalchemy as sa


revision = '20260508_add_alert_tables'
down_revision = 'add_performance_indexes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create alerts, alert_rules, and incidents tables."""
    # Alert rules table (user-defined)
    op.execute("""
        CREATE TABLE IF NOT EXISTS alert_rules (
            rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            condition JSONB NOT NULL,
            actions JSONB,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Alerts table (generated alerts)
    op.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
            rule_id UUID REFERENCES alert_rules(rule_id) ON DELETE SET NULL,
            event_id UUID REFERENCES recognition_events(event_id) ON DELETE SET NULL,
            type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            confidence FLOAT,
            source TEXT,
            status TEXT DEFAULT 'new',
            affected_entities INTEGER DEFAULT 0,
            details JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            acknowledged_at TIMESTAMP,
            resolved_at TIMESTAMP
        )
    """)

    # Incidents table (aggregated incidents)
    op.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            incident_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'open',
            severity TEXT,
            created_by TEXT REFERENCES users(user_id) ON DELETE SET NULL,
            priority TEXT,
            affected_systems TEXT,
            related_alerts JSONB,
            resolution_steps JSONB,
            root_cause TEXT,
            impact TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Indexes for performance
    op.create_index('idx_alert_rules_org', 'alert_rules', ['org_id'])
    op.create_index('idx_alerts_org_created', 'alerts', ['org_id', 'created_at DESC'])
    op.create_index('idx_alerts_status', 'alerts', ['status'])
    op.create_index('idx_alerts_type', 'alerts', ['type'])
    op.create_index('idx_incidents_org', 'incidents', ['org_id'])
    op.create_index('idx_incidents_status', 'incidents', ['status'])


def downgrade() -> None:
    """Drop tables and indexes."""
    op.drop_index('idx_incidents_status', table_name='incidents')
    op.drop_index('idx_incidents_org', table_name='incidents')
    op.drop_index('idx_alerts_type', table_name='alerts')
    op.drop_index('idx_alerts_status', table_name='alerts')
    op.drop_index('idx_alerts_org_created', table_name='alerts')
    op.drop_index('idx_alert_rules_org', table_name='alert_rules')
    op.drop_table('incidents')
    op.drop_table('alerts')
    op.drop_table('alert_rules')
