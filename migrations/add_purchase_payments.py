"""Add purchase payments table

Revision ID: add_purchase_payments
Revises: previous_revision
Create Date: 2025-09-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_purchase_payments'
down_revision = None  # Update this to the actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    # Create purchase_payments table
    op.create_table('purchase_payments',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('purchase_id', sa.String(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=False),
        sa.Column('payment_method', sa.String(), nullable=False),
        sa.Column('reference', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_by', sa.String(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=True),
        sa.Column('branch_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], ),
        sa.ForeignKeyConstraint(['purchase_id'], ['purchases.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better performance
    op.create_index('ix_purchase_payments_purchase_id', 'purchase_payments', ['purchase_id'])
    op.create_index('ix_purchase_payments_payment_date', 'purchase_payments', ['payment_date'])
    op.create_index('ix_purchase_payments_branch_id', 'purchase_payments', ['branch_id'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_purchase_payments_branch_id', table_name='purchase_payments')
    op.drop_index('ix_purchase_payments_payment_date', table_name='purchase_payments')
    op.drop_index('ix_purchase_payments_purchase_id', table_name='purchase_payments')
    
    # Drop table
    op.drop_table('purchase_payments')