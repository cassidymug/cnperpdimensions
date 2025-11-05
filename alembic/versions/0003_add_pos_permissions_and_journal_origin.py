"""Add journal entry origin fields and seed POS permissions

Revision ID: 0003
Revises: add_user_pin_hash  (Adjusted from missing '0002')
Create Date: 2025-08-27
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String


def _get_existing_columns(table_name: str):
    inspector = sa.inspect(op.get_bind())
    return {col['name'] for col in inspector.get_columns(table_name)}


def _has_index(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(idx['name'] == index_name for idx in inspector.get_indexes(table_name))

# revision identifiers, used by Alembic.
revision = '0003'
down_revision = 'add_user_pin_hash'
branch_labels = None
depends_on = None

def upgrade():
    existing_columns = _get_existing_columns('journal_entries')
    has_origin = 'origin' in existing_columns
    has_created_by = 'created_by_user_id' in existing_columns

    # Add columns to journal_entries only if missing to support reruns
    with op.batch_alter_table('journal_entries') as batch:
        if not has_origin:
            batch.add_column(sa.Column('origin', sa.String(), nullable=True))
        if not has_created_by:
            batch.add_column(sa.Column('created_by_user_id', sa.String(), nullable=True))
        if not _has_index('journal_entries', 'ix_journal_entries_origin'):
            batch.create_index('ix_journal_entries_origin', ['origin'], unique=False)

    # Seed POS permissions if not already there
    permissions = table('permissions',
        column('id', sa.String()),
        column('name', sa.String()),
        column('description', sa.String()),
        column('module', sa.String()),
        column('action', sa.String()),
        column('resource', sa.String())
    )

    import uuid
    conn = op.get_bind()
    existing = {r[0] for r in conn.execute(sa.text("SELECT name FROM permissions WHERE name IN ('pos.record_sale','pos.reconcile')"))}
    rows = []
    if 'pos.record_sale' not in existing:
        rows.append({
            'id': str(uuid.uuid4()),
            'name': 'pos.record_sale',
            'description': 'POS record sale',
            'module': 'pos',
            'action': 'record_sale',
            'resource': 'all'
        })
    if 'pos.reconcile' not in existing:
        rows.append({
            'id': str(uuid.uuid4()),
            'name': 'pos.reconcile',
            'description': 'POS reconciliation',
            'module': 'pos',
            'action': 'reconcile',
            'resource': 'all'
        })
    if rows:
        op.bulk_insert(permissions, rows)


def downgrade():
    # Drop columns / index (data loss acceptable for downgrade)
    with op.batch_alter_table('journal_entries') as batch:
        batch.drop_index('ix_journal_entries_origin')
        batch.drop_column('created_by_user_id')
        batch.drop_column('origin')
    # Optionally delete seeded permissions (kept to avoid accidental privilege loss)
    # Uncomment if you want to remove them on downgrade:
    # conn = op.get_bind()
    # conn.execute(sa.text("DELETE FROM permissions WHERE name IN ('pos.record_sale','pos.reconcile')"))
