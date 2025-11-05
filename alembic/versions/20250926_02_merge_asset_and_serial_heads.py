"""
Merge heads for asset and serial_numbers migrations

Revision ID: 20250926_02
Revises: 20250903_01, 20250926_01
Create Date: 2025-09-26 10:45:00.000000
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '20250926_02'
down_revision = ('20250903_01', '20250926_01')
branch_labels = None
depends_on = None


def upgrade():
    # merge point: no operations
    pass


def downgrade():
    pass
