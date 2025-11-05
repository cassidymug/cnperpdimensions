"""add_app_settings_timeout_columns

Revision ID: 60f29365095f
Revises: 20250903_02
Create Date: 2025-09-06 13:50:57.876966

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
revision = '60f29365095f'
down_revision = '20250903_02'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add timeout-related columns to app_settings table if they are missing.
    if not _column_exists('app_settings', 'idle_warning_minutes'):
        op.add_column('app_settings', sa.Column('idle_warning_minutes', sa.Integer(), nullable=True, default=2))

    if not _column_exists('app_settings', 'refresh_threshold_minutes'):
        op.add_column('app_settings', sa.Column('refresh_threshold_minutes', sa.Integer(), nullable=True, default=10))


def downgrade() -> None:
    # Remove timeout-related columns from app_settings table when present.
    if _column_exists('app_settings', 'refresh_threshold_minutes'):
        op.drop_column('app_settings', 'refresh_threshold_minutes')

    if _column_exists('app_settings', 'idle_warning_minutes'):
        op.drop_column('app_settings', 'idle_warning_minutes')