#!/usr/bin/env python3
"""
Migration script to add Phase 4 dimensional fields to bank_reconciliations table
"""

import sys
from app.core.database import engine
from sqlalchemy import text, inspect

def run_migration():
    """Add missing dimensional fields to bank_reconciliations table"""

    inspector = inspect(engine)
    existing_columns = [col['name'] for col in inspector.get_columns('bank_reconciliations')]
    print(f"[INFO] Current bank_reconciliations columns: {existing_columns}")

    columns_to_add = {
        'dimensional_accuracy': 'BOOLEAN DEFAULT TRUE NOT NULL',
        'dimension_variance_detail': 'TEXT NULL',
        'has_dimensional_mismatch': 'BOOLEAN DEFAULT FALSE NOT NULL',
        'variance_cost_centers': 'TEXT NULL',
        'gl_balance_by_dimension': 'TEXT NULL',
        'bank_statement_by_dimension': 'TEXT NULL',
        'variance_amount': 'NUMERIC(15,2) NULL',
    }

    with engine.connect() as conn:
        for col_name, col_type in columns_to_add.items():
            if col_name in existing_columns:
                print(f"[SKIP] Column {col_name} already exists")
                continue

            try:
                sql = f"ALTER TABLE bank_reconciliations ADD COLUMN {col_name} {col_type}"
                print(f"[RUN] {sql}")
                conn.execute(text(sql))
                conn.commit()
                print(f"[OK] Added column {col_name}")
            except Exception as e:
                conn.rollback()
                print(f"[ERROR] Failed to add column {col_name}: {e}")
                return False

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
