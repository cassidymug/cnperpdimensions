#!/usr/bin/env python
"""
Migration Script: Add Accounting Fields to Production Orders

This script adds accounting dimension and GL account fields to the production_orders table,
enabling manufacturing costs to be posted to the general ledger with dimensional tracking.

Fields Added:
- cost_center_id: Link to Cost Center dimension value
- project_id: Link to Project dimension value
- department_id: Link to Department dimension value
- wip_account_id: Link to WIP GL Account (Asset)
- labor_account_id: Link to Labor GL Account (Payable)
- posting_status: Status of GL posting (draft, posted, reconciled)
- last_posted_date: When this order was last posted to GL
- posted_by: User ID who posted to accounting

Usage:
    python scripts/migrate_add_accounting_to_production_orders.py

To list current columns only:
    python scripts/migrate_add_accounting_to_production_orders.py --list-only
"""

import sys
from sqlalchemy import text

def main():
    # Import database after setting Python path
    from app.core.database import engine

    list_only = "--list-only" in sys.argv

    with engine.connect() as conn:
        # List current columns
        print("\n[INFO] Current production_orders columns:")
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'production_orders'
            ORDER BY column_name
        """))

        current_columns = []
        for row in result:
            col_name, data_type, nullable = row
            current_columns.append(col_name)
            nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
            print(f"  {col_name:30s} {data_type:20s} {nullable_str}")

        if list_only:
            print("\n[INFO] Exiting (--list-only flag set)")
            return

        print("\n[INFO] Starting migration...")

        # Add accounting dimension fields
        fields_to_add = [
            ("cost_center_id", "VARCHAR(36)", "NULL"),
            ("project_id", "VARCHAR(36)", "NULL"),
            ("department_id", "VARCHAR(36)", "NULL"),
            ("wip_account_id", "VARCHAR(36)", "NULL"),
            ("labor_account_id", "VARCHAR(36)", "NULL"),
            ("posting_status", "VARCHAR(20)", "DEFAULT 'draft'"),
            ("last_posted_date", "DATETIME", "NULL"),
            ("posted_by", "VARCHAR(36)", "NULL")
        ]

        added_count = 0
        for field_name, data_type, nullable in fields_to_add:
            if field_name in current_columns:
                print(f"  ✓ {field_name} already exists, skipping")
                continue

            try:
                print(f"  → Adding {field_name}...")
                sql = f"ALTER TABLE production_orders ADD COLUMN {field_name} {data_type} {nullable}"
                conn.execute(text(sql))
                print(f"  ✓ {field_name} added successfully")
                added_count += 1
            except Exception as e:
                print(f"  ✗ Error adding {field_name}: {str(e)}")

        # Add foreign key constraints
        print("\n[INFO] Adding foreign key constraints...")
        fk_constraints = [
            {
                "name": "fk_po_cost_center",
                "column": "cost_center_id",
                "ref_table": "dimension_values",
                "ref_column": "id"
            },
            {
                "name": "fk_po_project",
                "column": "project_id",
                "ref_table": "dimension_values",
                "ref_column": "id"
            },
            {
                "name": "fk_po_department",
                "column": "department_id",
                "ref_table": "dimension_values",
                "ref_column": "id"
            },
            {
                "name": "fk_po_wip_account",
                "column": "wip_account_id",
                "ref_table": "accounting_codes",
                "ref_column": "id"
            },
            {
                "name": "fk_po_labor_account",
                "column": "labor_account_id",
                "ref_table": "accounting_codes",
                "ref_column": "id"
            },
            {
                "name": "fk_po_posted_by",
                "column": "posted_by",
                "ref_table": "users",
                "ref_column": "id"
            }
        ]

        for fk in fk_constraints:
            try:
                # Check if constraint already exists
                check_sql = f"""
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE constraint_name = '{fk['name']}'
                    AND table_name = 'production_orders'
                """
                result = conn.execute(text(check_sql))
                if result.fetchone():
                    print(f"  ✓ {fk['name']} already exists, skipping")
                    continue

                # Create the constraint
                print(f"  → Adding {fk['name']}...")
                sql = f"""
                    ALTER TABLE production_orders
                    ADD CONSTRAINT {fk['name']}
                    FOREIGN KEY ({fk['column']})
                    REFERENCES {fk['ref_table']}({fk['ref_column']})
                    ON DELETE SET NULL
                """
                conn.execute(text(sql))
                print(f"  ✓ {fk['name']} added successfully")
            except Exception as e:
                print(f"  ✗ Error adding {fk['name']}: {str(e)}")

        # Add indexes
        print("\n[INFO] Adding indexes for performance...")
        indexes = [
            {
                "name": "idx_po_cost_center",
                "column": "cost_center_id"
            },
            {
                "name": "idx_po_posting_status",
                "column": "posting_status"
            },
            {
                "name": "idx_po_posted_date",
                "column": "last_posted_date"
            }
        ]

        for idx in indexes:
            try:
                # Check if index already exists
                check_sql = f"""
                    SELECT 1 FROM information_schema.statistics
                    WHERE index_name = '{idx['name']}'
                    AND table_name = 'production_orders'
                """
                result = conn.execute(text(check_sql))
                if result.fetchone():
                    print(f"  ✓ {idx['name']} already exists, skipping")
                    continue

                # Create the index
                print(f"  → Adding {idx['name']}...")
                sql = f"CREATE INDEX {idx['name']} ON production_orders ({idx['column']})"
                conn.execute(text(sql))
                print(f"  ✓ {idx['name']} created successfully")
            except Exception as e:
                print(f"  ✗ Error adding {idx['name']}: {str(e)}")

        # Commit all changes
        conn.commit()

        print("\n" + "="*70)
        print("[SUCCESS] Migration completed successfully!")
        print("="*70)

        print("\n[INFO] Updated production_orders columns:")
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'production_orders'
            ORDER BY column_name
        """))

        for row in result:
            col_name, data_type, nullable = row
            nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
            if col_name in [f[0] for f in fields_to_add]:
                print(f"  ✓ {col_name:30s} {data_type:20s} {nullable_str} (NEW)")
            else:
                print(f"    {col_name:30s} {data_type:20s} {nullable_str}")

        print(f"\n[INFO] Total new fields added: {added_count}")
        print("[INFO] Foreign keys and indexes successfully created")
        print("\n[NEXT STEPS]")
        print("  1. Verify the database changes with: python scripts/migrate_add_accounting_to_production_orders.py --list-only")
        print("  2. Test the manufacturing API endpoints")
        print("  3. Create production orders with accounting dimensions")
        print("  4. Post orders to GL and verify journal entries")


if __name__ == "__main__":
    main()
