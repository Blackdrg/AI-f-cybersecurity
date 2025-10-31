"""add public enrichment tables

Revision ID: 30236ede6f7f
Revises: 
Create Date: 2025-10-27 22:35:03.078257

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30236ede6f7f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create consents table
    op.create_table('consents',
                    sa.Column('consent_id', sa.UUID(), nullable=False,
                              server_default=sa.text('gen_random_uuid()')),
                    sa.Column('subject_id', sa.Text(), nullable=True),
                    sa.Column('consent_text_version',
                              sa.Text(), nullable=True),
                    sa.Column('granted_at', sa.TIMESTAMP(
                        timezone=True), nullable=True),
                    sa.Column('granted_by', sa.Text(), nullable=True),
                    sa.Column('ip_addr', sa.Text(), nullable=True),
                    sa.Column('token', sa.Text(), nullable=True),
                    sa.Column('expires_at', sa.TIMESTAMP(
                        timezone=True), nullable=True),
                    sa.PrimaryKeyConstraint('consent_id')
                    )

    # Create enrichment_results table
    op.create_table('enrichment_results',
                    sa.Column('enrich_id', sa.UUID(), nullable=False,
                              server_default=sa.text('gen_random_uuid()')),
                    sa.Column('query', sa.Text(), nullable=True),
                    sa.Column('subject', sa.Text(), nullable=True),
                    sa.Column('summary', sa.JSON(), nullable=True),
                    sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                              nullable=True, server_default=sa.text('now()')),
                    sa.Column('expires_at', sa.TIMESTAMP(
                        timezone=True), nullable=True),
                    sa.Column('requested_by', sa.Text(), nullable=True),
                    sa.Column('purpose', sa.Text(), nullable=True),
                    sa.PrimaryKeyConstraint('enrich_id')
                    )

    # Create audit_logs table
    op.create_table('audit_logs',
                    sa.Column('audit_id', sa.UUID(), nullable=False,
                              server_default=sa.text('gen_random_uuid()')),
                    sa.Column('action', sa.Text(), nullable=True),
                    sa.Column('user_id', sa.Text(), nullable=True),
                    sa.Column('target_enrich_id', sa.UUID(), nullable=True),
                    sa.Column('provider_calls', sa.JSON(), nullable=True),
                    sa.Column('metadata', sa.JSON(), nullable=True),
                    sa.Column('created_at', sa.TIMESTAMP(timezone=True),
                              nullable=True, server_default=sa.text('now()')),
                    sa.PrimaryKeyConstraint('audit_id')
                    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('audit_logs')
    op.drop_table('enrichment_results')
    op.drop_table('consents')
