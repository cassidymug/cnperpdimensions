"""Merge COGS and product ID heads

Revision ID: cdff0ebc054e
Revises: b37a980e5289, add_cogs_entries_table
Create Date: 2025-09-30 15:01:27.570471

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cdff0ebc054e'
down_revision = ('b37a980e5289', 'add_cogs_entries_table')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass 