"""add purchase_payments table

Revision ID: 20251003_01_add_purchase_payments
Revises: 20250926_02_merge_asset_and_serial_heads
Create Date: 2025-10-03
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251003_01_add_purchase_payments'
down_revision = '20250926_02'
branch_labels = None
depends_on = None

def upgrade():
    # Create purchase_payments table if it does not exist
    op.create_table(
        'purchase_payments',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('purchase_id', sa.String(), sa.ForeignKey('purchases.id'), nullable=False),
        sa.Column('amount', sa.Numeric(15, 2), nullable=False),
        sa.Column('payment_date', sa.Date(), nullable=False),
        sa.Column('payment_method', sa.String(), nullable=False),
        sa.Column('reference', sa.String()),
        sa.Column('notes', sa.Text()),
        sa.Column('recorded_by', sa.String()),
        sa.Column('recorded_at', sa.DateTime()),
        sa.Column('branch_id', sa.String(), sa.ForeignKey('branches.id')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()')),
    )
    op.create_index('ix_purchase_payments_purchase_id', 'purchase_payments', ['purchase_id'])
    op.create_index('ix_purchase_payments_branch_id', 'purchase_payments', ['branch_id'])


def downgrade():
    op.drop_index('ix_purchase_payments_purchase_id', table_name='purchase_payments')
    op.drop_index('ix_purchase_payments_branch_id', table_name='purchase_payments')
    op.drop_table('purchase_payments')
