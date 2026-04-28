"""Add Stripe columns to subscriptions and payments

Revision ID: 002
Revises: 001
Create Date: 2026-04-28

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add Stripe-related columns to subscriptions and payments."""
    # subscriptions table enhancements
    op.add_column('subscriptions', sa.Column('stripe_customer_id', sa.String(), nullable=True))
    op.add_column('subscriptions', sa.Column('stripe_subscription_id', sa.String(), nullable=True))
    op.add_column('subscriptions', sa.Column('starts_at', sa.TIMESTAMP(), nullable=True))
    op.add_column('subscriptions', sa.Column('cancelled_at', sa.TIMESTAMP(), nullable=True))
    op.add_column('subscriptions', sa.Column('updated_at', sa.TIMESTAMP(), nullable=True))
    
    # payments table enhancements  
    op.add_column('payments', sa.Column('stripe_invoice_id', sa.String(), nullable=True))
    op.add_column('payments', sa.Column('metadata', postgresql.JSONB, nullable=True, default={}))
    
    # Create indexes for efficient Stripe lookups
    op.create_index('idx_subscriptions_stripe_customer', 'subscriptions', ['stripe_customer_id'])
    op.create_index('idx_subscriptions_stripe_subscription', 'subscriptions', ['stripe_subscription_id'])
    op.create_index('idx_payments_stripe_invoice', 'payments', ['stripe_invoice_id'])


def downgrade() -> None:
    """Remove Stripe-related columns."""
    op.drop_index('idx_payments_stripe_invoice')
    op.drop_index('idx_subscriptions_stripe_subscription')
    op.drop_index('idx_subscriptions_stripe_customer')
    
    op.drop_column('payments', 'metadata')
    op.drop_column('payments', 'stripe_invoice_id')
    
    op.drop_column('subscriptions', 'updated_at')
    op.drop_column('subscriptions', 'cancelled_at')
    op.drop_column('subscriptions', 'starts_at')
    op.drop_column('subscriptions', 'stripe_subscription_id')
    op.drop_column('subscriptions', 'stripe_customer_id')
