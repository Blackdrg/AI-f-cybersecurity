"""Federated learning tables."""
from alembic import op
import sqlalchemy as sa
import uuid

def upgrade():
    op.create_table('federated_clients',
    sa.Column('client_id', sa.String(length=128), nullable=False),
    sa.Column('org_id', sa.String(length=128), nullable=False),
    sa.Column('name', sa.String(length=256)),
    sa.Column('status', sa.String(length=32), server_default='idle'),
    sa.Column('capabilities', sa.JSON()),
    sa.Column('last_seen', sa.DateTime(), server_default=sa.text('now()')),
    sa.PrimaryKeyConstraint('client_id')
    )
    
    op.create_table('federated_rounds',
    sa.Column('round_id', sa.String(length=128), nullable=False),
    sa.Column('org_id', sa.String(length=128), nullable=False),
    sa.Column('status', sa.String(length=32), server_default='pending'),
    sa.Column('min_clients', sa.Integer(), nullable=False),
    sa.Column('num_clients', sa.Integer(), default=0),
    sa.Column('aggregation_method', sa.String(length=32), default='fedavg'),
    sa.Column('started_at', sa.DateTime(), nullable=True),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('round_id')
    )
    
    op.create_table('federated_updates',
    sa.Column('update_id', sa.String(length=128), primary_key=True),
    sa.Column('client_id', sa.String(length=128), nullable=False),
    sa.Column('round_id', sa.String(length=128), nullable=False),
    sa.Column('num_samples', sa.Integer(), nullable=False),
    sa.Column('model_version', sa.String(length=32), nullable=False),
    sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()')),
    sa.Column('gradients_hash', sa.String(length=64)),
    sa.Column('status', sa.String(length=32), server_default='pending'),
    sa.ForeignKeyConstraint(['client_id'], ['federated_clients.client_id']),
    sa.ForeignKeyConstraint(['round_id'], ['federated_rounds.round_id'])
    )

def downgrade():
    op.drop_table('federated_updates')
    op.drop_table('federated_rounds')
    op.drop_table('federated_clients')
