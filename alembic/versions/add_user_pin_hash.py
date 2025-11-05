"""add pin_hash column to users

Revision ID: add_user_pin_hash
Revises: add_backup_tables
Create Date: 2025-08-25
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_user_pin_hash'
down_revision = 'add_backup_tables'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('users', sa.Column('pin_hash', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'pin_hash')
