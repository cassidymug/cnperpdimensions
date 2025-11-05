"""Add supplier_invoice_number to purchases

Revision ID: d46631b271ba
Revises: cdff0ebc054e
Create Date: 2025-09-30 20:47:49.032560

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
revision = 'd46631b271ba'
down_revision = 'cdff0ebc054e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not _column_exists('purchases', 'supplier_invoice_number'):
        op.add_column('purchases', sa.Column('supplier_invoice_number', sa.String(length=100), nullable=True))


def downgrade() -> None:
    if _column_exists('purchases', 'supplier_invoice_number'):
        op.drop_column('purchases', 'supplier_invoice_number')