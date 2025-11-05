"""add_quotations_tables

Revision ID: 232e93fbc1f1
Revises: 20251009_02_create_pos_shift_reconciliations
Create Date: 2025-10-14 16:30:04.770879

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '232e93fbc1f1'
down_revision = '20251009_02_create_pos_shift_reconciliations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create quotations table
    op.create_table(
        'quotations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('quote_number', sa.String(), nullable=False),
        sa.Column('customer_id', sa.String(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('reference', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('subtotal', sa.Numeric(15, 2), nullable=True),
        sa.Column('vat', sa.Numeric(15, 2), nullable=True),
        sa.Column('total', sa.Numeric(15, 2), nullable=True),
        sa.Column('branch_id', sa.String(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quote_number'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'])
    )
    
    # Create quotation_items table
    op.create_table(
        'quotation_items',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('quotation_id', sa.String(), nullable=False),
        sa.Column('product_id', sa.String(), nullable=False),
        sa.Column('quantity', sa.Numeric(10, 2), nullable=False),
        sa.Column('price', sa.Numeric(15, 2), nullable=False),
        sa.Column('discount', sa.Numeric(5, 2), nullable=True),
        sa.Column('line_total', sa.Numeric(15, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['quotation_id'], ['quotations.id']),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'])
    )


def downgrade() -> None:
    op.drop_table('quotation_items')
    op.drop_table('quotations') 