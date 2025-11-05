"""Add logo_width and logo_height columns to app_settings

Revision ID: add_logo_dimensions_001
Revises: 
Create Date: 2025-09-07 08:55:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_logo_dimensions_001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Add logo_width and logo_height columns to app_settings table"""
    
    # Check if columns already exist before adding them
    conn = op.get_bind()
    
    # Check if logo_width column exists
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'app_settings' AND column_name = 'logo_width'
    """))
    
    if not result.fetchone():
        op.add_column('app_settings', sa.Column('logo_width', sa.Integer(), default=150))
    
    # Check if logo_height column exists  
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'app_settings' AND column_name = 'logo_height'
    """))
    
    if not result.fetchone():
        op.add_column('app_settings', sa.Column('logo_height', sa.Integer(), default=75))

def downgrade():
    """Remove logo_width and logo_height columns from app_settings table"""
    
    # Check if columns exist before dropping them
    conn = op.get_bind()
    
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'app_settings' AND column_name IN ('logo_width', 'logo_height')
    """))
    
    existing_columns = [row.column_name for row in result]
    
    if 'logo_height' in existing_columns:
        op.drop_column('app_settings', 'logo_height')
        
    if 'logo_width' in existing_columns:
        op.drop_column('app_settings', 'logo_width')
