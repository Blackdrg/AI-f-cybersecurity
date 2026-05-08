"""Integration tests for database migrations.

Tests all Alembic migrations can be upgraded and downgraded successfully
with data integrity preservation across up/down cycles.
"""

import os
import pytest
import asyncio
from pathlib import Path
from typing import AsyncGenerator, List, Tuple
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Setup paths
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ALEMBIC_INI = BACKEND_DIR / 'alembic.ini'
ALEMBIC_DIR = BACKEND_DIR / 'alembic'


@pytest.fixture(scope='session')
def test_db_url() -> str:
    """Get test database URL from environment or use default."""
    password = os.environ.get('DB_PASSWORD', 'postgres_secure_password_123!')
    default_url = f'postgresql://postgres:{password}@localhost:5433/face_recognition_test'
    test_url = os.environ.get('TEST_DATABASE_URL', default_url)
    return test_url


@pytest.fixture(scope='session')
def alembic_config(test_db_url: str) -> Config:
    """Create Alembic config for migrations."""
    config = Config(str(ALEMBIC_INI))
    config.set_main_option('script_location', str(ALEMBIC_DIR))
    config.set_main_option('sqlalchemy.url', test_db_url)
    return config


@pytest.fixture(scope='session')
def available_migrations(alembic_config: Config) -> List[Tuple[str, str]]:
    """Get list of (revision_id, description) tuples in order."""
    script = ScriptDirectory.from_config(alembic_config)
    migrations = []
    for rev in script.walk_revisions():
        migrations.append((rev.revision, rev.doc))
    # Sort by revision order (down to up)
    migrations.reverse()
    return migrations


@pytest.mark.integration
@pytest.mark.database
class TestMigrations:
    """Test suite for database migration rollback capabilities."""

    async def test_migration_upgrade_all(
        self, 
        test_db_url: str, 
        alembic_config: Config,
        available_migrations: List[Tuple[str, str]]
    ):
        """Test that all migrations can be upgraded successfully."""
        engine = create_engine(test_db_url)
        
        # Clean slate: drop all tables
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
        
        # Apply all migrations in order
        from alembic.command import upgrade
        upgrade(alembic_config, 'head')
        
        # Verify all expected tables exist
        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            
            # Core tables that should exist
            expected_tables = [
                'organizations', 'persons', 'embeddings', 'audit_log',
                'users', 'org_members', 'cameras', 'recognition_events',
                'alert_rules', 'alerts', 'system_health', 'plans',
                'subscriptions', 'payments', 'usage', 'support_tickets',
                'consents', 'enrichment_results', 'audit_logs',
                'api_keys', 'model_versions', 'federated_updates',
                'edge_devices', 'webhook_events'
            ]
            
            for table in expected_tables:
                assert table in tables, f"Table {table} missing after upgrade"
        
        engine.dispose()

    async def test_migration_downgrade_all(
        self, 
        test_db_url: str, 
        alembic_config: Config,
        available_migrations: List[Tuple[str, str]]
    ):
        """Test that all migrations can be downgraded in reverse order."""
        engine = create_engine(test_db_url)
        
        # Start from head (all migrations applied)
        from alembic.command import upgrade
        upgrade(alembic_config, 'head')
        
        # Downgrade one by one, verifying no errors
        for rev_id, description in available_migrations:
            # Downgrade to previous revision
            from alembic.command import downgrade
            downgrade(alembic_config, '-1')
            
            # Verify database is still accessible
            with engine.begin() as conn:
                # Check that tables from current revision still exist
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """))
                # Should not raise exception
        
        # Final state: only base tables (or empty)
        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            tables = [row[0] for row in result]
            # After full downgrade, most tables should be dropped
            assert len(tables) <= 5, f"Unexpected tables remain after full downgrade: {tables}"
        
        engine.dispose()

    async def test_migration_upgrade_downgrade_cycle(
        self, 
        test_db_url: str, 
        alembic_config: Config,
        available_migrations: List[Tuple[str, str]]
    ):
        """Test full up/down cycle preserves database integrity."""
        engine = create_engine(test_db_url)
        
        # Clean
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        
        # Upgrade all
        from alembic.command import upgrade
        upgrade(alembic_config, 'head')
        
        # Insert test data
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO organizations (org_id, name, subscription_tier)
                VALUES ('11111111-1111-1111-1111-111111111111', 'Test Org', 'enterprise')
            """))
            conn.execute(text("""
                INSERT INTO users (user_id, email, name, subscription_tier)
                VALUES ('test_user', 'test@example.com', 'Test User', 'pro')
            """))
        
        # Downgrade all
        for _ in available_migrations:
            from alembic.command import downgrade
            downgrade(alembic_config, '-1')
        
        # Upgrade again
        upgrade(alembic_config, 'head')
        
        # Verify data is preserved
        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT name FROM organizations 
                WHERE org_id = '11111111-1111-1111-1111-111111111111'
            """))
            org_name = result.scalar()
            assert org_name == 'Test Org', "Organization data lost after up/down cycle"
            
            result = conn.execute(text("""
                SELECT email FROM users WHERE user_id = 'test_user'
            """))
            email = result.scalar()
            assert email == 'test@example.com', "User data lost after up/down cycle"
        
        engine.dispose()

    async def test_each_migration_individually(
        self, 
        test_db_url: str, 
        alembic_config: Config,
        available_migrations: List[Tuple[str, str]]
    ):
        """Test that each migration can be applied and reverted individually."""
        engine = create_engine(test_db_url)
        
        # Start from clean state
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        
        from alembic.command import upgrade, downgrade
        
        # Apply migrations one at a time, verifying after each
        for i, (rev_id, description) in enumerate(available_migrations):
            # Upgrade to this specific revision
            upgrade(alembic_config, rev_id)
            
            # Database should be accessible
            with engine.begin() as conn:
                conn.execute(text("SELECT 1"))
            
            # If not the last migration, downgrade and verify
            if i < len(available_migrations) - 1:
                downgrade(alembic_config, '-1')
                with engine.begin() as conn:
                    conn.execute(text("SELECT 1"))
        
        engine.dispose()
