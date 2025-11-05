"""Add extended asset metadata fields to purchase_items

Revision ID: 20250903_02
Revises: d7824e60f470
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

revision = '20250903_02'
down_revision = 'd7824e60f470'
branch_labels = None
depends_on = None

def upgrade():
    columns_to_add = [
        ("asset_location", sa.String(length=255), True),
        ("asset_custodian", sa.String(length=255), True),
        ("asset_purchase_ref", sa.String(length=255), True),
        ("asset_tag", sa.String(length=255), True),
        ("asset_warranty_expiry", sa.Date(), True),
        ("asset_notes", sa.Text(), True),
        ("asset_accum_depr_account_code_id", sa.String(length=36), True),
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


def downgrade():
    with op.batch_alter_table('purchase_items') as batch_op:
        batch_op.drop_column('asset_accum_depr_account_code_id')
        batch_op.drop_column('asset_notes')
        batch_op.drop_column('asset_warranty_expiry')
        batch_op.drop_column('asset_tag')
        batch_op.drop_column('asset_purchase_ref')
        batch_op.drop_column('asset_custodian')
        batch_op.drop_column('asset_location')
