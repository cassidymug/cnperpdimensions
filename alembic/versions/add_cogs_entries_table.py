"""
Alembic migration to add cogs_entries table for COGSEntry model
"""
from alembic import op
import sqlalchemy as sa


def _table_exists(table_name: str) -> bool:
    """Return True if the given table already exists."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()

# revision identifiers, used by Alembic.
revision = 'add_cogs_entries_table'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    if _table_exists("cogs_entries"):
        return

    op.create_table(
        'cogs_entries',
        sa.Column('id', sa.String, primary_key=True),
        sa.Column('product_id', sa.String, sa.ForeignKey('products.id'), nullable=False),
        sa.Column('purchase_item_id', sa.String, sa.ForeignKey('purchase_items.id'), nullable=True),
        sa.Column('cost', sa.Numeric(15, 2), nullable=False),
        sa.Column('quantity', sa.Integer, nullable=False, default=1),
        sa.Column('date', sa.Date),
        sa.Column('notes', sa.Text),
        sa.Column('created_by', sa.String, sa.ForeignKey('users.id')),
        sa.Column('branch_id', sa.String, sa.ForeignKey('branches.id')),
    )

def downgrade():
    if _table_exists("cogs_entries"):
        op.drop_table('cogs_entries')
