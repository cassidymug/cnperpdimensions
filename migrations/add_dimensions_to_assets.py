"""
Migration: Add accounting dimensions and IFRS support to Asset model
Run this script to add cost_center_id, project_id, and department_id to the assets table
"""

from sqlalchemy import text
from app.core.database import engine


def add_dimensions_to_assets():
    """Add accounting dimension foreign keys to assets table"""

    with engine.connect() as conn:
        try:
            # Add cost_center_id column
            conn.execute(text("""
                ALTER TABLE assets
                ADD COLUMN IF NOT EXISTS cost_center_id VARCHAR(36) REFERENCES accounting_dimension_values(id)
            """))
            print("✓ Added cost_center_id column to assets table")

            # Add project_id column
            conn.execute(text("""
                ALTER TABLE assets
                ADD COLUMN IF NOT EXISTS project_id VARCHAR(36) REFERENCES accounting_dimension_values(id)
            """))
            print("✓ Added project_id column to assets table")

            # Add department_id column (this is different from assigned_department which is just a string)
            conn.execute(text("""
                ALTER TABLE assets
                ADD COLUMN IF NOT EXISTS department_id VARCHAR(36) REFERENCES accounting_dimension_values(id)
            """))
            print("✓ Added department_id column to assets table")

            # Add indexes for performance
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_assets_cost_center
                ON assets(cost_center_id)
            """))
            print("✓ Created index on cost_center_id")

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_assets_project
                ON assets(project_id)
            """))
            print("✓ Created index on project_id")

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_assets_department
                ON assets(department_id)
            """))
            print("✓ Created index on department_id")

            conn.commit()
            print("\n✅ Migration completed successfully!")
            print("\nNote: Update the Asset model in app/models/asset_management.py to include:")
            print("  - cost_center_id = Column(String, ForeignKey('accounting_dimension_values.id'), nullable=True, index=True)")
            print("  - project_id = Column(String, ForeignKey('accounting_dimension_values.id'), nullable=True)")
            print("  - department_id = Column(String, ForeignKey('accounting_dimension_values.id'), nullable=True)")
            print("  - Add relationships for cost_center, project, and department")

        except Exception as e:
            conn.rollback()
            print(f"❌ Error during migration: {e}")
            raise


if __name__ == "__main__":
    print("Starting migration: Add accounting dimensions to assets table")
    print("=" * 70)
    add_dimensions_to_assets()
