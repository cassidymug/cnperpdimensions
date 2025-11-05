"""Add journal sale audit linkage table

Revision ID: 0004
Revises: 0003
Create Date: 2025-08-28
"""
from alembic import op
import sqlalchemy as sa


def _has_table(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(idx['name'] == index_name for idx in inspector.get_indexes(table_name))

# revision identifiers, used by Alembic.
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

def upgrade():
    if not _has_table('journal_sale_audit'):
        op.create_table(
            'journal_sale_audit',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('journal_entry_id', sa.String(), nullable=False),
            sa.Column('sale_id', sa.String(), nullable=False),
            sa.Column('pos_session_id', sa.String(), nullable=True),
            sa.Column('branch_id', sa.String(), nullable=False),
            sa.Column('cashier_user_id', sa.String(), nullable=True),
            sa.Column('posted_by_user_id', sa.String(), nullable=True),
            sa.Column('origin', sa.String(), nullable=False, server_default='POS_AUTO'),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['journal_entry_id'], ['journal_entries.id'], name='fk_jsa_journal_entry'),
            sa.ForeignKeyConstraint(['sale_id'], ['sales.id'], name='fk_jsa_sale'),
            sa.ForeignKeyConstraint(['pos_session_id'], ['pos_sessions.id'], name='fk_jsa_pos_session'),
            sa.ForeignKeyConstraint(['cashier_user_id'], ['users.id'], name='fk_jsa_cashier_user'),
            sa.ForeignKeyConstraint(['posted_by_user_id'], ['users.id'], name='fk_jsa_posted_user'),
            sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], name='fk_jsa_branch')
        )

    if _has_table('journal_sale_audit') and not _has_index('journal_sale_audit', 'ix_journal_sale_audit_journal_entry_id'):
        op.create_index('ix_journal_sale_audit_journal_entry_id', 'journal_sale_audit', ['journal_entry_id'])
    if _has_table('journal_sale_audit') and not _has_index('journal_sale_audit', 'ix_journal_sale_audit_sale_id'):
        op.create_index('ix_journal_sale_audit_sale_id', 'journal_sale_audit', ['sale_id'])
    if _has_table('journal_sale_audit') and not _has_index('journal_sale_audit', 'ix_journal_sale_audit_branch_id'):
        op.create_index('ix_journal_sale_audit_branch_id', 'journal_sale_audit', ['branch_id'])
    if _has_table('journal_sale_audit') and not _has_index('journal_sale_audit', 'ix_journal_sale_audit_origin'):
        op.create_index('ix_journal_sale_audit_origin', 'journal_sale_audit', ['origin'])


def downgrade():
    op.drop_index('ix_journal_sale_audit_origin', table_name='journal_sale_audit')
    op.drop_index('ix_journal_sale_audit_branch_id', table_name='journal_sale_audit')
    op.drop_index('ix_journal_sale_audit_sale_id', table_name='journal_sale_audit')
    op.drop_index('ix_journal_sale_audit_journal_entry_id', table_name='journal_sale_audit')
    op.drop_table('journal_sale_audit')
