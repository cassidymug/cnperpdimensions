#!/usr/bin/env python
"""
Add missing cost_center_id columns to sales table and related tables.
These columns are defined in models but missing from the database.
"""

from app.core.database import engine
from sqlalchemy import text
import warnings

warnings.filterwarnings('ignore', category=DeprecationWarning)

def add_column_if_missing(table_name, column_name, column_def):
    """Add a column to a table if it doesn't exist"""
    with engine.connect() as conn:
        try:
            # Check if column exists
            result = conn.execute(text(f"""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='{table_name}' AND column_name='{column_name}'
                )
            """))
            exists = result.scalar()

            if exists:
                print(f"✓ Column {table_name}.{column_name} already exists")
                return True

            # Add column
            print(f"Adding column {table_name}.{column_name}...")
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_def}"))
            conn.commit()
            print(f"✓ Successfully added {table_name}.{column_name}")
            return True

        except Exception as e:
            print(f"✗ Error with {table_name}.{column_name}: {e}")
            return False

if __name__ == "__main__":
    print("Adding missing cost_center_id columns...\n")

    # Define columns to add
    columns_to_add = [
        ("sales", "cost_center_id", 'cost_center_id VARCHAR NULL REFERENCES accounting_dimension_values(id)'),
        ("sales", "project_id", 'project_id VARCHAR NULL REFERENCES accounting_dimension_values(id)'),
        ("sales", "department_id", 'department_id VARCHAR NULL REFERENCES accounting_dimension_values(id)'),
    ]

    success_count = 0
    for table, col, col_def in columns_to_add:
        if add_column_if_missing(table, col, col_def):
            success_count += 1

    print(f"\n✓ Migration complete: {success_count}/{len(columns_to_add)} columns added/verified")
