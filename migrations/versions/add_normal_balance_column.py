"""add normal_balance column to accounting_codes

Revision ID: add_normal_balance
Revises: refactor_accounting_codes
Create Date: 2025-08-07 10:50:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from app.models.accounting_constants import NormalBalance

# revision identifiers, used by Alembic.
revision = 'add_normal_balance'
down_revision = 'refactor_accounting_codes'
branch_labels = None
depends_on = None

def upgrade():
    # Add normal_balance column with a default of 'debit' for existing records
    op.add_column('accounting_codes', 
                 sa.Column('normal_balance', 
                          sa.Enum('debit', 'credit', name='normalbalance'),
                          nullable=False,
                          server_default='debit'))
    
    # Update existing records based on account type
    op.execute("""
        UPDATE accounting_codes 
        SET normal_balance = 'credit'
        WHERE account_type IN ('Liability', 'Equity', 'Revenue')
    """)

def downgrade():
    # Drop the normal_balance column
    op.drop_column('accounting_codes', 'normal_balance')
