"""merge_heads_before_product_id_fix

Revision ID: 67c453e4eb82
Revises: 20250926_02, 60f29365095f
Create Date: 2025-09-28 13:00:22.176143

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '67c453e4eb82'
down_revision = ('20250926_02', '60f29365095f')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass 