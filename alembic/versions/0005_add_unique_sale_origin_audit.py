"""Add unique constraint to journal_sale_audit (sale_id, origin)

Revision ID: 0005
Revises: 0004
Create Date: 2025-08-28
"""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

def upgrade():
    # Add unique constraint to prevent duplicate auto postings per sale & origin
    op.create_unique_constraint('uq_journal_sale_audit_sale_origin', 'journal_sale_audit', ['sale_id','origin'])

def downgrade():
    op.drop_constraint('uq_journal_sale_audit_sale_origin', 'journal_sale_audit', type_='unique')
