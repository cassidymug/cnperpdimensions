"""
Database Migration: Add POS Receipt Support to Credit Notes

This migration adds the ability for credit notes to reference either invoices or POS receipts.

Changes:
1. Add source_type column (VARCHAR) - 'invoice' or 'pos_receipt'
2. Add source_id column (VARCHAR) - ID of source document
3. Add original_sale_id column (VARCHAR, FK to sales table)
4. Make original_invoice_id nullable (was required before)
5. Add original_sale_item_id to credit_note_items table

Usage:
    python migrations/add_credit_note_pos_support.py

This script can be run multiple times safely (idempotent).
"""

import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import engine
from sqlalchemy import text, inspect

def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def check_foreign_key_exists(table_name: str, fk_name: str) -> bool:
    """Check if a foreign key constraint exists"""
    inspector = inspect(engine)
    foreign_keys = inspector.get_foreign_keys(table_name)
    return any(fk['name'] == fk_name for fk in foreign_keys)

def run_migration():
    """Execute the migration"""
    
    print("=" * 80)
    print("Credit Notes POS Support Migration")
    print("=" * 80)
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            # 1. Add source_type column to credit_notes
            if not check_column_exists('credit_notes', 'source_type'):
                print("\n✓ Adding source_type column to credit_notes...")
                conn.execute(text("""
                    ALTER TABLE credit_notes 
                    ADD COLUMN source_type VARCHAR NOT NULL DEFAULT 'invoice'
                """))
                print("  ✓ source_type column added successfully")
            else:
                print("\n✓ source_type column already exists")
            
            # 2. Add source_id column to credit_notes
            if not check_column_exists('credit_notes', 'source_id'):
                print("\n✓ Adding source_id column to credit_notes...")
                # First add as nullable, populate it, then make it NOT NULL
                conn.execute(text("""
                    ALTER TABLE credit_notes 
                    ADD COLUMN source_id VARCHAR
                """))
                print("  ✓ source_id column added (nullable)")
                
                # Populate source_id from original_invoice_id for existing records
                print("  ✓ Populating source_id from existing invoice IDs...")
                conn.execute(text("""
                    UPDATE credit_notes 
                    SET source_id = original_invoice_id 
                    WHERE source_id IS NULL AND original_invoice_id IS NOT NULL
                """))
                print("  ✓ source_id populated for existing records")
                
                # Now make it NOT NULL
                conn.execute(text("""
                    ALTER TABLE credit_notes 
                    ALTER COLUMN source_id SET NOT NULL
                """))
                print("  ✓ source_id column made NOT NULL")
            else:
                print("\n✓ source_id column already exists")
            
            # 3. Add original_sale_id column to credit_notes
            if not check_column_exists('credit_notes', 'original_sale_id'):
                print("\n✓ Adding original_sale_id column to credit_notes...")
                conn.execute(text("""
                    ALTER TABLE credit_notes 
                    ADD COLUMN original_sale_id VARCHAR
                """))
                print("  ✓ original_sale_id column added")
                
                # Add foreign key constraint
                if not check_foreign_key_exists('credit_notes', 'fk_credit_notes_original_sale_id'):
                    print("  ✓ Adding foreign key constraint to sales table...")
                    conn.execute(text("""
                        ALTER TABLE credit_notes 
                        ADD CONSTRAINT fk_credit_notes_original_sale_id 
                        FOREIGN KEY (original_sale_id) REFERENCES sales(id)
                    """))
                    print("  ✓ Foreign key constraint added")
            else:
                print("\n✓ original_sale_id column already exists")
            
            # 4. Make original_invoice_id nullable
            print("\n✓ Making original_invoice_id nullable...")
            conn.execute(text("""
                ALTER TABLE credit_notes 
                ALTER COLUMN original_invoice_id DROP NOT NULL
            """))
            print("  ✓ original_invoice_id is now nullable")
            
            # 5. Add original_sale_item_id column to credit_note_items
            if not check_column_exists('credit_note_items', 'original_sale_item_id'):
                print("\n✓ Adding original_sale_item_id column to credit_note_items...")
                conn.execute(text("""
                    ALTER TABLE credit_note_items 
                    ADD COLUMN original_sale_item_id VARCHAR
                """))
                print("  ✓ original_sale_item_id column added")
                
                # Add foreign key constraint
                if not check_foreign_key_exists('credit_note_items', 'fk_credit_note_items_original_sale_item_id'):
                    print("  ✓ Adding foreign key constraint to sale_items table...")
                    conn.execute(text("""
                        ALTER TABLE credit_note_items 
                        ADD CONSTRAINT fk_credit_note_items_original_sale_item_id 
                        FOREIGN KEY (original_sale_item_id) REFERENCES sale_items(id)
                    """))
                    print("  ✓ Foreign key constraint added")
            else:
                print("\n✓ original_sale_item_id column already exists")
            
            # 6. Make original_invoice_item_id nullable in credit_note_items
            print("\n✓ Making original_invoice_item_id nullable in credit_note_items...")
            conn.execute(text("""
                ALTER TABLE credit_note_items 
                ALTER COLUMN original_invoice_item_id DROP NOT NULL
            """))
            print("  ✓ original_invoice_item_id is now nullable")
            
            # Commit transaction
            trans.commit()
            
            print("\n" + "=" * 80)
            print("✓✓✓ Migration completed successfully! ✓✓✓")
            print("=" * 80)
            print("\nChanges applied:")
            print("  1. Added source_type column to credit_notes (default: 'invoice')")
            print("  2. Added source_id column to credit_notes (populated from invoice IDs)")
            print("  3. Added original_sale_id column to credit_notes (FK to sales)")
            print("  4. Made original_invoice_id nullable in credit_notes")
            print("  5. Added original_sale_item_id column to credit_note_items (FK to sale_items)")
            print("  6. Made original_invoice_item_id nullable in credit_note_items")
            print("\nCredit notes can now be created from both invoices and POS receipts!")
            print("=" * 80)
            
        except Exception as e:
            print(f"\n✗ ERROR during migration: {str(e)}")
            trans.rollback()
            print("✗ Transaction rolled back")
            raise

def verify_migration():
    """Verify the migration was successful"""
    print("\n" + "=" * 80)
    print("Verifying Migration...")
    print("=" * 80)
    
    inspector = inspect(engine)
    
    # Check credit_notes table
    cn_columns = [col['name'] for col in inspector.get_columns('credit_notes')]
    required_cn_columns = ['source_type', 'source_id', 'original_sale_id']
    
    print("\nCredit Notes Table Columns:")
    for col in required_cn_columns:
        if col in cn_columns:
            print(f"  ✓ {col} exists")
        else:
            print(f"  ✗ {col} MISSING!")
    
    # Check credit_note_items table
    cni_columns = [col['name'] for col in inspector.get_columns('credit_note_items')]
    required_cni_columns = ['original_sale_item_id']
    
    print("\nCredit Note Items Table Columns:")
    for col in required_cni_columns:
        if col in cni_columns:
            print(f"  ✓ {col} exists")
        else:
            print(f"  ✗ {col} MISSING!")
    
    # Check foreign keys
    cn_fks = inspector.get_foreign_keys('credit_notes')
    cni_fks = inspector.get_foreign_keys('credit_note_items')
    
    print("\nForeign Key Constraints:")
    has_sale_fk = any('sales' in str(fk.get('referred_table', '')) for fk in cn_fks)
    has_sale_item_fk = any('sale_items' in str(fk.get('referred_table', '')) for fk in cni_fks)
    
    if has_sale_fk:
        print("  ✓ credit_notes -> sales FK exists")
    else:
        print("  ✗ credit_notes -> sales FK MISSING!")
    
    if has_sale_item_fk:
        print("  ✓ credit_note_items -> sale_items FK exists")
    else:
        print("  ✗ credit_note_items -> sale_items FK MISSING!")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    try:
        print("\nStarting credit notes POS support migration...\n")
        run_migration()
        verify_migration()
        print("\n✓ All done! Credit notes now support POS receipts.\n")
    except Exception as e:
        print(f"\n✗ Migration failed: {str(e)}\n")
        sys.exit(1)
