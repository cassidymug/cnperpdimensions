"""add_quotation_to_invoice_link

Revision ID: 1b440d1bc680
Revises: 32f02980d7a3
Create Date: 2025-10-14 19:00:02.629789

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1b440d1bc680'
down_revision = '32f02980d7a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add quotation_id to invoices table
    op.add_column('invoices', sa.Column('quotation_id', sa.String(), nullable=True))
    op.create_foreign_key('fk_invoices_quotation_id', 'invoices', 'quotations', ['quotation_id'], ['id'])
    
    # Make product_id nullable in invoice_items (for custom descriptions)
    op.alter_column('invoice_items', 'product_id',
                    existing_type=sa.String(),
                    nullable=True)


def downgrade() -> None:
    # Revert product_id to non-nullable in invoice_items
    op.alter_column('invoice_items', 'product_id',
                    existing_type=sa.String(),
                    nullable=False)
    
    # Remove foreign key and column from invoices
    op.drop_constraint('fk_invoices_quotation_id', 'invoices', type_='foreignkey')
    op.drop_column('invoices', 'quotation_id') 