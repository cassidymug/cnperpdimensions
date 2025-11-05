"""Refactor accounting codes with proper types and constraints

Revision ID: 1a2b3c4d5e6f
Revises: 
Create Date: 2025-03-07 08:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import sessionmaker
from app.models.accounting_constants import AccountType, NormalBalance

# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create a temporary table with the new schema
    op.create_table(
        'accounting_codes_new',
        sa.Column('id', sa.String(36), nullable=False, primary_key=True),
        sa.Column('code', sa.String(20), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('account_type', sa.Enum(AccountType, name='account_type_enum'), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('parent_id', sa.String(36), sa.ForeignKey('accounting_codes_new.id', ondelete='CASCADE'), nullable=True, index=True),
        sa.Column('is_parent', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('total_debits', sa.Numeric(19, 4), nullable=False, server_default='0'),
        sa.Column('total_credits', sa.Numeric(19, 4), nullable=False, server_default='0'),
        sa.Column('balance', sa.Numeric(19, 4), nullable=False, server_default='0'),
        sa.Column('normal_balance', sa.Enum(NormalBalance, name='normal_balance_enum'), nullable=False, server_default='debit'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='BWP'),
        sa.Column('reporting_tag', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),
        sa.Column('branch_id', sa.String(36), sa.ForeignKey('branches.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.CheckConstraint(
            "account_type IN ('Asset', 'Liability', 'Equity', 'Revenue', 'Expense')",
            name='valid_account_type'
        ),
        sa.CheckConstraint(
            "normal_balance IN ('debit', 'credit')",
            name='valid_normal_balance'
        ),
        comment='Stores the chart of accounts with hierarchical structure'
    )
    
    # Copy data from old table to new table
    op.execute("""
        INSERT INTO accounting_codes_new (
            id, code, name, account_type, category, parent_id, 
            is_parent, total_debits, total_credits, balance, 
            normal_balance, currency, reporting_tag, description, 
            is_active, created_at, updated_at, branch_id
        )
        SELECT 
            id, 
            code, 
            name, 
            account_type,
            category,
            parent_id,
            COALESCE(is_parent, 0) as is_parent,
            COALESCE(total_debits, 0) as total_debits,
            COALESCE(total_credits, 0) as total_credits,
            COALESCE(balance, 0) as balance,
            COALESCE(normal_balance, 
                CASE 
                    WHEN account_type IN ('Asset', 'Expense') THEN 'debit' 
                    ELSE 'credit' 
                END) as normal_balance,
            COALESCE(currency, 'BWP') as currency,
            reporting_tag,
            description,
            COALESCE(is_active, 1) as is_active,
            COALESCE(created_at, CURRENT_TIMESTAMP) as created_at,
            COALESCE(updated_at, CURRENT_TIMESTAMP) as updated_at,
            branch_id
        FROM accounting_codes
    """)
    
    # Drop constraints and indexes from old table
    op.drop_constraint('valid_account_type', 'accounting_codes', type_='check')
    
    # Drop the old table
    op.drop_table('accounting_codes')
    
    # Rename new table to original name
    op.rename_table('accounting_codes_new', 'accounting_codes')
    
    # Create indexes
    op.create_index(op.f('ix_accounting_codes_code'), 'accounting_codes', ['code'], unique=True)
    op.create_index(op.f('ix_accounting_codes_parent_id'), 'accounting_codes', ['parent_id'], unique=False)
    op.create_index(op.f('ix_accounting_codes_branch_id'), 'accounting_codes', ['branch_id'], unique=False)
    
    # Add foreign key constraints
    op.create_foreign_key(
        'fk_accounting_codes_parent_id',
        'accounting_codes', 'accounting_codes',
        ['parent_id'], ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_accounting_codes_branch_id',
        'accounting_codes', 'branches',
        ['branch_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    # This is a complex migration, so downgrade will need to be handled carefully
    # In a real scenario, you would need to implement a proper downgrade path
    # For now, we'll just drop the new constraints and enums
    
    # Drop foreign keys
    op.drop_constraint('fk_accounting_codes_parent_id', 'accounting_codes', type_='foreignkey')
    op.drop_constraint('fk_accounting_codes_branch_id', 'accounting_codes', type_='foreignkey')
    
    # Drop indexes
    op.drop_index(op.f('ix_accounting_codes_code'), table_name='accounting_codes')
    op.drop_index(op.f('ix_accounting_codes_parent_id'), table_name='accounting_codes')
    op.drop_index(op.f('ix_accounting_codes_branch_id'), table_name='accounting_codes')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS account_type_enum")
    op.execute("DROP TYPE IF EXISTS normal_balance_enum")
