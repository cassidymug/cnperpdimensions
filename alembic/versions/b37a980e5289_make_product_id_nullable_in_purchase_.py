"""make_product_id_nullable_in_purchase_items

Revision ID: b37a980e5289
Revises: 67c453e4eb82
Create Date: 2025-09-28 13:01:47.127531

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b37a980e5289'
down_revision = '67c453e4eb82'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make product_id nullable to support free-text and asset items
    with op.batch_alter_table('purchase_items') as batch_op:
        batch_op.alter_column('product_id', nullable=True)


def downgrade() -> None:
    # Make product_id not nullable again (this will fail if there are null values)
    with op.batch_alter_table('purchase_items') as batch_op:
        batch_op.alter_column('product_id', nullable=False) 