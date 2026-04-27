"""Initial database schema
Revision ID: 001
Revises: 
Create Date: 2026-04-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from logging.config import fileConfig
import logging

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

logger = logging.getLogger('alembic')

def upgrade() -> None:
    """Create all tables."""
    # Read and execute init.sql
    import pathlib
    init_sql_path = pathlib.Path(__file__).parent.parent.parent / 'infra' / 'init.sql'
    if not init_sql_path.exists():
        raise FileNotFoundError(f"init.sql not found at {init_sql_path}")
    
    sql = init_sql_path.read_text()
    # Split by semicolon to execute multiple statements
    # Note: op.execute can run entire script
    op.execute(sql)

def downgrade() -> None:
    """Drop all tables (WARNING: destroys all data)"""
    # Drop in reverse order (due to FK constraints)
    tables = [
        "mfa_attempts",
        "mfa_secrets",
        "bias_reports",
        "system_health",
        "sessions",
        "system_config",
        "audit_logs",
        "enrichment_results",
        "consents",
        "ota_updates",
        "edge_devices",
        "model_versions",
        "federated_updates",
        "support_tickets",
        "usage",
        "subscriptions",
        "payments",
        "plans",
        "feedback",
        "alert_rules",
        "alerts",
        "recognition_events",
        "cameras",
        "api_keys",
        "org_members",
        "organizations",
        "users",
        "audit_log",
        "embeddings",
        "persons"
    ]
    for table in tables:
        try:
            op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        except Exception as e:
            logger.warning(f"Failed to drop {table}: {e}")
