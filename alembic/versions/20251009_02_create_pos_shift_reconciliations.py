"""Create POS shift reconciliation table

Revision ID: 20251009_02_create_pos_shift_reconciliations
Revises: 20251009_01_extend_receipts_for_invoices
Create Date: 2025-10-09
"""
from alembic import op
import sqlalchemy as sa


def _has_table(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(idx['name'] == index_name for idx in inspector.get_indexes(table_name))


def _has_constraint(table_name: str, constraint_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(constraint['name'] == constraint_name for constraint in inspector.get_unique_constraints(table_name))


# revision identifiers, used by Alembic.
revision = '20251009_02_create_pos_shift_reconciliations'
down_revision = '20251009_01_extend_receipts_for_invoices'
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not _has_table('pos_shift_reconciliations'):
        op.create_table(
            'pos_shift_reconciliations',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('session_id', sa.String(), nullable=False),
            sa.Column('cashier_id', sa.String(), nullable=False),
            sa.Column('branch_id', sa.String(), nullable=False),
            sa.Column('shift_date', sa.Date(), nullable=False),
            sa.Column('float_given', sa.Numeric(12, 2), nullable=False, server_default='0'),
            sa.Column('cash_collected', sa.Numeric(12, 2), nullable=False, server_default='0'),
            sa.Column('cash_sales', sa.Numeric(12, 2), nullable=False, server_default='0'),
            sa.Column('expected_cash', sa.Numeric(12, 2), nullable=False, server_default='0'),
            sa.Column('variance', sa.Numeric(12, 2), nullable=False, server_default='0'),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('verified_by', sa.String(), nullable=True),
            sa.Column('verified_at', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['session_id'], ['pos_sessions.id'], name='fk_pos_shift_reconciliations_session_id', ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['cashier_id'], ['users.id'], name='fk_pos_shift_reconciliations_cashier_id'),
            sa.ForeignKeyConstraint(['branch_id'], ['branches.id'], name='fk_pos_shift_reconciliations_branch_id'),
            sa.ForeignKeyConstraint(['verified_by'], ['users.id'], name='fk_pos_shift_reconciliations_verified_by'),
            sa.PrimaryKeyConstraint('id')
        )

    if not _has_constraint('pos_shift_reconciliations', 'uq_pos_shift_reconciliations_session_id'):
        op.create_unique_constraint('uq_pos_shift_reconciliations_session_id', 'pos_shift_reconciliations', ['session_id'])
    if not _has_index('pos_shift_reconciliations', 'ix_pos_shift_reconciliations_shift_date'):
        op.create_index('ix_pos_shift_reconciliations_shift_date', 'pos_shift_reconciliations', ['shift_date'])
    if not _has_index('pos_shift_reconciliations', 'ix_pos_shift_reconciliations_branch_id'):
        op.create_index('ix_pos_shift_reconciliations_branch_id', 'pos_shift_reconciliations', ['branch_id'])


def downgrade() -> None:
    op.drop_index('ix_pos_shift_reconciliations_branch_id', table_name='pos_shift_reconciliations')
    op.drop_index('ix_pos_shift_reconciliations_shift_date', table_name='pos_shift_reconciliations')
    op.drop_constraint('uq_pos_shift_reconciliations_session_id', 'pos_shift_reconciliations', type_='unique')
    op.drop_table('pos_shift_reconciliations')
