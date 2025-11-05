"""
merge heads after adding awards PO linkage

Revision ID: 20251005_03_merge_heads_fix_awards
Revises: 20251005_02_add_purchase_order_id_to_procurement_awards, 493cfcf8622f
Create Date: 2025-10-05
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '20251005_03_merge_heads_fix_awards'
# Merge the two active heads into a single lineage
down_revision = ('20251005_01_add_uom_to_product_assemblies', '20251005_02_add_purchase_order_id_to_procurement_awards')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # merge point; no-op
    pass


def downgrade() -> None:
    # no-op
    pass
