"""Extend receipts to support invoice payments

Revision ID: 20251009_01_extend_receipts_for_invoices
Revises: 20251008_01_create_job_cards_module
Create Date: 2025-10-09
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251009_01_extend_receipts_for_invoices'
down_revision = '20251008_01_create_job_cards_module'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Allow receipts to be linked to invoices/payments as well as sales
    op.alter_column('receipts', 'sale_id', existing_type=sa.String(), nullable=True)

    op.add_column('receipts', sa.Column('invoice_id', sa.String(), nullable=True))
    op.add_column('receipts', sa.Column('payment_id', sa.String(), nullable=True))
    op.add_column('receipts', sa.Column('customer_id', sa.String(), nullable=True))
    op.add_column('receipts', sa.Column('amount', sa.Numeric(15, 2), nullable=True, server_default='0'))
    op.add_column('receipts', sa.Column('currency', sa.String(length=10), nullable=True, server_default='BWP'))
    op.add_column('receipts', sa.Column('payment_method', sa.String(), nullable=True))
    op.add_column('receipts', sa.Column('payment_date', sa.DateTime(), nullable=True))
    op.add_column('receipts', sa.Column('notes', sa.Text(), nullable=True))

    # Create foreign-key relationships for the new references
    op.create_foreign_key('fk_receipts_invoice_id', 'receipts', 'invoices', ['invoice_id'], ['id'])
    op.create_foreign_key('fk_receipts_payment_id', 'receipts', 'payments', ['payment_id'], ['id'])
    op.create_foreign_key('fk_receipts_customer_id', 'receipts', 'customers', ['customer_id'], ['id'])

    # Backfill defaults for existing rows
    op.execute("UPDATE receipts SET amount = COALESCE(amount, 0)")
    op.execute("UPDATE receipts SET currency = 'BWP' WHERE currency IS NULL")


def downgrade() -> None:
    # Remove foreign-key relationships first
    op.drop_constraint('fk_receipts_customer_id', 'receipts', type_='foreignkey')
    op.drop_constraint('fk_receipts_payment_id', 'receipts', type_='foreignkey')
    op.drop_constraint('fk_receipts_invoice_id', 'receipts', type_='foreignkey')

    # Drop newly added columns
    op.drop_column('receipts', 'notes')
    op.drop_column('receipts', 'payment_date')
    op.drop_column('receipts', 'payment_method')
    op.drop_column('receipts', 'currency')
    op.drop_column('receipts', 'amount')
    op.drop_column('receipts', 'customer_id')
    op.drop_column('receipts', 'payment_id')
    op.drop_column('receipts', 'invoice_id')

    # Restore sale_id requirement
    op.alter_column('receipts', 'sale_id', existing_type=sa.String(), nullable=False)
