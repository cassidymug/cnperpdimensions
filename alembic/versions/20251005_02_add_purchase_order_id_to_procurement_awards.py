"""
add purchase_order_id to procurement_awards

Revision ID: 20251005_02_add_purchase_order_id_to_procurement_awards
Revises: 20251005_01_add_uom_to_product_assemblies
Create Date: 2025-10-05
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251005_02_add_purchase_order_id_to_procurement_awards'
# Linearize to the latest existing head to avoid multiple heads
down_revision = '493cfcf8622f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nullable purchase_order_id with FK to purchase_orders(id)
    op.add_column('procurement_awards', sa.Column('purchase_order_id', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_procurement_awards_purchase_order_id',
        'procurement_awards',
        'purchase_orders',
        ['purchase_order_id'],
        ['id'],
        ondelete='SET NULL'
    )
    op.create_index('ix_procurement_awards_purchase_order_id', 'procurement_awards', ['purchase_order_id'])


def downgrade() -> None:
    op.drop_index('ix_procurement_awards_purchase_order_id', table_name='procurement_awards')
    op.drop_constraint('fk_procurement_awards_purchase_order_id', 'procurement_awards', type_='foreignkey')
    op.drop_column('procurement_awards', 'purchase_order_id')
