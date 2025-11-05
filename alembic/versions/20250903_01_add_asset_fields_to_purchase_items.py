"""Add asset fields to purchase_items

Revision ID: 20250903_01
Revises: 0005
Create Date: 2025-09-03
"""
from alembic import op
import sqlalchemy as sa


def _column_exists(table_name: str, column_name: str) -> bool:
    """Return True if the given column already exists on the table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
    return column_name in existing_columns

# revision identifiers, used by Alembic.
revision = '20250903_01'
down_revision = '0005'
branch_labels = None
depends_on = None

def upgrade():
    columns_to_add = [
        ("is_asset", sa.Boolean(), True),
        ("asset_name", sa.String(length=255), True),
        ("asset_category", sa.String(length=100), True),
        ("asset_depreciation_method", sa.String(length=100), True),
        ("asset_useful_life_years", sa.Integer(), True),
        ("asset_salvage_value", sa.Numeric(15, 2), True),
        ("asset_serial_number", sa.String(length=255), True),
        ("asset_vehicle_registration", sa.String(length=50), True),
        ("asset_engine_number", sa.String(length=100), True),
        ("asset_chassis_number", sa.String(length=100), True),
        ("asset_accounting_code_id", sa.String(length=36), True),
    ]

    missing_columns = [
        (name, coltype, nullable)
        for name, coltype, nullable in columns_to_add
        if not _column_exists("purchase_items", name)
    ]

    if missing_columns:
        with op.batch_alter_table("purchase_items") as batch_op:
            for name, coltype, nullable in missing_columns:
                batch_op.add_column(sa.Column(name, coltype, nullable=nullable))

    if _column_exists("purchase_items", "is_asset"):
        # Normalize NULL asset flags to avoid tri-state logic when column exists.
        op.execute("UPDATE purchase_items SET is_asset = FALSE WHERE is_asset IS NULL")


def downgrade():
    with op.batch_alter_table('purchase_items') as batch_op:
        batch_op.drop_column('asset_accounting_code_id')
        batch_op.drop_column('asset_chassis_number')
        batch_op.drop_column('asset_engine_number')
        batch_op.drop_column('asset_vehicle_registration')
        batch_op.drop_column('asset_serial_number')
        batch_op.drop_column('asset_salvage_value')
        batch_op.drop_column('asset_useful_life_years')
        batch_op.drop_column('asset_depreciation_method')
        batch_op.drop_column('asset_category')
        batch_op.drop_column('asset_name')
        batch_op.drop_column('is_asset')
