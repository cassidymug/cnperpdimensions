"""
add unit_of_measure_id to product_assemblies

Revision ID: 20251005_01_add_uom_to_product_assemblies
Revises: 20251003_01_add_purchase_payments_table
Create Date: 2025-10-05
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251005_01_add_uom_to_product_assemblies'
down_revision = '20251003_01_add_purchase_payments'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('product_assemblies', sa.Column('unit_of_measure_id', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_product_assemblies_unit_of_measure_id',
        'product_assemblies',
        'unit_of_measures',
        ['unit_of_measure_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_product_assemblies_unit_of_measure_id', 'product_assemblies', type_='foreignkey')
    op.drop_column('product_assemblies', 'unit_of_measure_id')
