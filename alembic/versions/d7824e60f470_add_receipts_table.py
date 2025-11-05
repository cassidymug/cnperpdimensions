"""Add receipts table

Revision ID: d7824e60f470
Revises: 0005
Create Date: 2025-09-01 05:09:44.835701

"""
from alembic import op
import sqlalchemy as sa


def _table_exists(table_name: str) -> bool:
    """Return True if the given table already exists."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


# revision identifiers, used by Alembic.
revision = 'd7824e60f470'
down_revision = '20250903_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create receipts table only if it is missing (models may have created it already).
    if _table_exists("receipts"):
        return

    op.create_table(
        'receipts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('sale_id', sa.String(), nullable=False),
        sa.Column('receipt_number', sa.String(), nullable=False),
        sa.Column('pdf_path', sa.String(), nullable=True),
        sa.Column('html_content', sa.Text(), nullable=True),
        sa.Column('printed', sa.Boolean(), nullable=True),
        sa.Column('print_count', sa.Integer(), nullable=True),
        sa.Column('created_by_user_id', sa.String(), nullable=False),
        sa.Column('branch_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.id']),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['sale_id'], ['sales.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('receipt_number')
    )


def downgrade() -> None:
    # Drop receipts table if it still exists.
    if _table_exists("receipts"):
        op.drop_table('receipts')