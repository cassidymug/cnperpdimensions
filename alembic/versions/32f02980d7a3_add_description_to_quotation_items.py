"""add_description_to_quotation_items

Revision ID: 32f02980d7a3
Revises: 232e93fbc1f1
Create Date: 2025-10-14 17:58:21.602034

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '32f02980d7a3'
down_revision = '232e93fbc1f1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add description column to quotation_items
    op.add_column('quotation_items', sa.Column('description', sa.Text(), nullable=True))
    
    # Make product_id nullable
    op.alter_column('quotation_items', 'product_id',
                    existing_type=sa.String(),
                    nullable=True)


def downgrade() -> None:
    # Revert product_id to non-nullable
    op.alter_column('quotation_items', 'product_id',
                    existing_type=sa.String(),
                    nullable=False)
    
    # Remove description column
    op.drop_column('quotation_items', 'description') 