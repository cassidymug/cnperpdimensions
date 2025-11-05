"""
Convert serial_numbers column to PostgreSQL TEXT[] array

Revision ID: 20250926_01
Revises: 20250903_02_add_extended_asset_fields
Create Date: 2025-09-26 08:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250926_01'
down_revision = '20250903_02'
branch_labels = None
depends_on = None


def upgrade():
    # alter serial_numbers to TEXT[] array type, preserving data
    op.alter_column(
        'inventory_transactions',
        'serial_numbers',
        existing_type=sa.Text(),
        type_=postgresql.ARRAY(sa.Text()),
        postgresql_using="serial_numbers::text[]"
    )


def downgrade():
    # revert back to Text, serial_numbers will be array-to-string
    op.alter_column(
        'inventory_transactions',
        'serial_numbers',
        existing_type=postgresql.ARRAY(sa.Text()),
        type_=sa.Text(),
        postgresql_using="array_to_string(serial_numbers, ',')"
    )
