"""
Migration: Remove foreign key constraint from billable_items.billable_id
This allows billable_id to reference both products AND assets (or other entities)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine
from sqlalchemy import text

def migrate():
    """Remove FK constraint and convert to simple string column"""
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()

        try:
            print("Removing foreign key constraint from billable_items.billable_id...")

            # Drop the foreign key constraint
            # PostgreSQL syntax
            conn.execute(text("""
                ALTER TABLE billable_items
                DROP CONSTRAINT IF EXISTS billable_items_billable_id_fkey
            """))

            print("✅ Foreign key constraint removed successfully!")
            print("✅ billable_id can now reference products, assets, or any other entity")

            trans.commit()
            print("\n🎉 Migration completed successfully!")

        except Exception as e:
            trans.rollback()
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    migrate()
