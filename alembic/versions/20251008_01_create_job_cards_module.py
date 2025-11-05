"""
create job card domain tables

Revision ID: 20251008_01_create_job_cards_module
Revises: 20251005_03_merge_heads_fix_awards
Create Date: 2025-10-08
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251008_01_create_job_cards_module'
down_revision = '20251005_03_merge_heads_fix_awards'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'job_cards',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('job_number', sa.String(length=40), nullable=False),
        sa.Column('customer_id', sa.String(), sa.ForeignKey('customers.id'), nullable=False),
        sa.Column('branch_id', sa.String(), sa.ForeignKey('branches.id'), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default=sa.text("'draft'")),
        sa.Column('job_type', sa.String(length=40), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default=sa.text("'normal'")),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('completed_date', sa.Date(), nullable=True),
        sa.Column('technician_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_by_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_by_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default=sa.text("'BWP'")),
        sa.Column('vat_rate', sa.Numeric(6, 3), nullable=False, server_default=sa.text('0')),
        sa.Column('total_material_cost', sa.Numeric(15, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('total_material_price', sa.Numeric(15, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('total_labor_cost', sa.Numeric(15, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('total_labor_price', sa.Numeric(15, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('subtotal', sa.Numeric(15, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('vat_amount', sa.Numeric(15, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('total_amount', sa.Numeric(15, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('amount_paid', sa.Numeric(15, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('amount_due', sa.Numeric(15, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('invoice_generated', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    op.create_index('ix_job_cards_job_number', 'job_cards', ['job_number'], unique=True)
    op.create_index('ix_job_cards_customer_id', 'job_cards', ['customer_id'])
    op.create_index('ix_job_cards_branch_id', 'job_cards', ['branch_id'])
    op.create_index('ix_job_cards_status', 'job_cards', ['status'])

    op.create_table(
        'job_card_materials',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('job_card_id', sa.String(), sa.ForeignKey('job_cards.id'), nullable=False),
        sa.Column('product_id', sa.String(), sa.ForeignKey('products.id'), nullable=False),
        sa.Column('quantity', sa.Numeric(12, 3), nullable=False, server_default=sa.text('0')),
        sa.Column('unit_cost', sa.Numeric(15, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('unit_price', sa.Numeric(15, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('total_cost', sa.Numeric(15, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('total_price', sa.Numeric(15, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('is_issued', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('issued_at', sa.DateTime(), nullable=True),
        sa.Column('inventory_transaction_id', sa.String(), sa.ForeignKey('inventory_transactions.id'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )
    op.create_index('ix_job_card_materials_job_card_id', 'job_card_materials', ['job_card_id'])
    op.create_index('ix_job_card_materials_product_id', 'job_card_materials', ['product_id'])

    op.create_table(
        'job_card_labors',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('job_card_id', sa.String(), sa.ForeignKey('job_cards.id'), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('hours', sa.Numeric(10, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('rate', sa.Numeric(15, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('total_price', sa.Numeric(15, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('total_cost', sa.Numeric(15, 2), nullable=False, server_default=sa.text('0')),
        sa.Column('technician_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('product_id', sa.String(), sa.ForeignKey('products.id'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
    )
    op.create_index('ix_job_card_labors_job_card_id', 'job_card_labors', ['job_card_id'])

    op.create_table(
        'job_card_notes',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('job_card_id', sa.String(), sa.ForeignKey('job_cards.id'), nullable=False),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('author_id', sa.String(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('logged_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_job_card_notes_job_card_id', 'job_card_notes', ['job_card_id'])

    op.add_column('invoices', sa.Column('job_card_id', sa.String(), nullable=True))
    op.create_foreign_key('fk_invoices_job_card_id', 'invoices', 'job_cards', ['job_card_id'], ['id'], ondelete='SET NULL')

    op.add_column('inventory_transactions', sa.Column('related_job_card_id', sa.String(), nullable=True))
    op.create_foreign_key('fk_inventory_transactions_job_card_id', 'inventory_transactions', 'job_cards', ['related_job_card_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_inventory_transactions_job_card_id', 'inventory_transactions', type_='foreignkey')
    op.drop_column('inventory_transactions', 'related_job_card_id')

    op.drop_constraint('fk_invoices_job_card_id', 'invoices', type_='foreignkey')
    op.drop_column('invoices', 'job_card_id')

    op.drop_index('ix_job_card_notes_job_card_id', table_name='job_card_notes')
    op.drop_table('job_card_notes')

    op.drop_index('ix_job_card_labors_job_card_id', table_name='job_card_labors')
    op.drop_table('job_card_labors')

    op.drop_index('ix_job_card_materials_product_id', table_name='job_card_materials')
    op.drop_index('ix_job_card_materials_job_card_id', table_name='job_card_materials')
    op.drop_table('job_card_materials')

    op.drop_index('ix_job_cards_status', table_name='job_cards')
    op.drop_index('ix_job_cards_branch_id', table_name='job_cards')
    op.drop_index('ix_job_cards_customer_id', table_name='job_cards')
    op.drop_index('ix_job_cards_job_number', table_name='job_cards')
    op.drop_table('job_cards')
