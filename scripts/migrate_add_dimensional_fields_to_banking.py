#!/usr/bin/env python3
"""
Migration script to add dimensional accounting fields to bank_transactions table
Phase 4: Dimensional Accounting support for banking
"""

import sys
from app.core.database import engine
from sqlalchemy import text, inspect

def run_migration():
    """Add missing dimensional fields to bank_transactions table"""

    inspector = inspect(engine)
    existing_columns = [col['name'] for col in inspector.get_columns('bank_transactions')]
    print(f"[INFO] Current bank_transactions columns: {existing_columns}")

    columns_to_add = {
        'cost_center_id': 'VARCHAR NULL',
        'project_id': 'VARCHAR NULL',
        'department_id': 'VARCHAR NULL',
        'gl_bank_account_id': 'VARCHAR NULL',
        'posting_status': "VARCHAR DEFAULT 'pending' NOT NULL",
        'posted_by': 'VARCHAR NULL',
        'last_posted_date': 'TIMESTAMP NULL',
        'reconciliation_status': "VARCHAR DEFAULT 'unreconciled' NOT NULL",
        'reconciliation_note': 'VARCHAR NULL'
    }

    with engine.connect() as conn:
        for col_name, col_type in columns_to_add.items():
            if col_name in existing_columns:
                print(f"[SKIP] Column {col_name} already exists")
                continue

            try:
                sql = f"ALTER TABLE bank_transactions ADD COLUMN {col_name} {col_type}"
                print(f"[RUN] {sql}")
                conn.execute(text(sql))
                conn.commit()
                print(f"[OK] Added column {col_name}")
            except Exception as e:
                conn.rollback()
                print(f"[ERROR] Failed to add column {col_name}: {e}")
                return False

        # Add foreign key constraints
        fk_constraints = {
            'cost_center_id': ('accounting_dimension_values', 'id'),
            'project_id': ('accounting_dimension_values', 'id'),
            'department_id': ('accounting_dimension_values', 'id'),
            'gl_bank_account_id': ('accounting_codes', 'id'),
            'posted_by': ('users', 'id'),
        }

        for col_name, (ref_table, ref_col) in fk_constraints.items():
            constraint_name = f"fk_bank_transactions_{col_name}"

            # Check if constraint exists
            check_sql = text("""
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_name='bank_transactions' AND constraint_name=:cname
            """)
            result = conn.execute(check_sql, {"cname": constraint_name})

            if result.scalar():
                print(f"[SKIP] Constraint {constraint_name} already exists")
                continue

            try:
                fk_sql = f"""
                    ALTER TABLE bank_transactions
                    ADD CONSTRAINT {constraint_name}
                    FOREIGN KEY ({col_name}) REFERENCES {ref_table}({ref_col}) ON DELETE SET NULL
                """
                print(f"[RUN] Adding FK constraint {constraint_name}")
                conn.execute(text(fk_sql))
                conn.commit()
                print(f"[OK] Added FK constraint {constraint_name}")
            except Exception as e:
                conn.rollback()
                print(f"[WARN] Could not add FK constraint {constraint_name}: {e}")

        # Add indexes for performance (skip for now to avoid info_schema issues)
        # PostgreSQL uses pg_indexes instead of information_schema.statistics
        print("[INFO] Skipping index creation - will be added in future migration if needed")

    print("[DONE] Migration completed successfully")
    return True

if __name__ == "__main__":
    try:
        success = run_migration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[FATAL] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
