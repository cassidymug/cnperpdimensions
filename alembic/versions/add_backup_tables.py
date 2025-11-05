"""Add backup tables

Revision ID: add_backup_tables
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def _has_table(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _has_index(inspector, table_name: str, index_name: str) -> bool:
    return any(idx['name'] == index_name for idx in inspector.get_indexes(table_name))

# revision identifiers, used by Alembic.
revision = 'add_backup_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, 'backups'):
        # Create backups table if it does not already exist
        op.create_table(
            'backups',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('backup_type', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('file_path', sa.String(), nullable=True),
            sa.Column('file_size', sa.Integer(), nullable=True),
            sa.Column('file_hash', sa.String(), nullable=True),
            sa.Column('backup_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('created_by', sa.String(), nullable=False),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )

    if not _has_table(inspector, 'backup_schedules'):
        # Create backup_schedules table if it does not already exist
        op.create_table(
            'backup_schedules',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('backup_type', sa.String(), nullable=False),
            sa.Column('frequency', sa.String(), nullable=False),
            sa.Column('time', sa.String(), nullable=False),
            sa.Column('include_files', sa.Boolean(), default=True, nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), default=True, nullable=True),
            sa.Column('last_run', sa.DateTime(timezone=True), nullable=True),
            sa.Column('next_run', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('created_by', sa.String(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )

    # Create indexes if they do not already exist
    if _has_table(inspector, 'backups'):
        if not _has_index(inspector, 'backups', op.f('ix_backups_backup_type')):
            op.create_index(op.f('ix_backups_backup_type'), 'backups', ['backup_type'], unique=False)
        if not _has_index(inspector, 'backups', op.f('ix_backups_status')):
            op.create_index(op.f('ix_backups_status'), 'backups', ['status'], unique=False)
        if not _has_index(inspector, 'backups', op.f('ix_backups_created_at')):
            op.create_index(op.f('ix_backups_created_at'), 'backups', ['created_at'], unique=False)
        if not _has_index(inspector, 'backups', op.f('ix_backups_created_by')):
            op.create_index(op.f('ix_backups_created_by'), 'backups', ['created_by'], unique=False)

    if _has_table(inspector, 'backup_schedules'):
        if not _has_index(inspector, 'backup_schedules', op.f('ix_backup_schedules_backup_type')):
            op.create_index(op.f('ix_backup_schedules_backup_type'), 'backup_schedules', ['backup_type'], unique=False)
        if not _has_index(inspector, 'backup_schedules', op.f('ix_backup_schedules_frequency')):
            op.create_index(op.f('ix_backup_schedules_frequency'), 'backup_schedules', ['frequency'], unique=False)
        if not _has_index(inspector, 'backup_schedules', op.f('ix_backup_schedules_is_active')):
            op.create_index(op.f('ix_backup_schedules_is_active'), 'backup_schedules', ['is_active'], unique=False)
        if not _has_index(inspector, 'backup_schedules', op.f('ix_backup_schedules_created_by')):
            op.create_index(op.f('ix_backup_schedules_created_by'), 'backup_schedules', ['created_by'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_backup_schedules_created_by'), table_name='backup_schedules')
    op.drop_index(op.f('ix_backup_schedules_is_active'), table_name='backup_schedules')
    op.drop_index(op.f('ix_backup_schedules_frequency'), table_name='backup_schedules')
    op.drop_index(op.f('ix_backup_schedules_backup_type'), table_name='backup_schedules')
    
    op.drop_index(op.f('ix_backups_created_by'), table_name='backups')
    op.drop_index(op.f('ix_backups_created_at'), table_name='backups')
    op.drop_index(op.f('ix_backups_status'), table_name='backups')
    op.drop_index(op.f('ix_backups_backup_type'), table_name='backups')

    # Drop tables
    op.drop_table('backup_schedules')
    op.drop_table('backups')
