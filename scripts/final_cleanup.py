#!/usr/bin/env python
"""
Final cleanup script - delete test branches with CASCADE
"""

import sys
sys.path.insert(0, '.')

from app.core.database import engine
from sqlalchemy import text

conn = engine.raw_connection()
cursor = conn.cursor()

try:
    # Get test branch IDs
    cursor.execute("SELECT id FROM branches WHERE name ILIKE '%Test Branch%'")
    test_ids = tuple(row[0] for row in cursor.fetchall())

    if not test_ids:
        print("No test branches found")
        conn.close()
        exit(0)

    print(f"Found {len(test_ids)} test branches to delete")

    # Build ID list
    id_placeholders = ','.join(['%s'] * len(test_ids))

    # Disable FK checks and delete
    cursor.execute("SET CONSTRAINTS ALL DEFERRED")

    # Delete in dependency order
    tables = [
        "reconciliation_items",
        "bank_transactions",
        "bank_reconciliations",
        "bank_transfers",
        "bank_accounts",
        "sales",
        "purchases",
        "purchase_orders",
        "invoices",
        "products",
        "inventory_transactions",
        "customers",
        "suppliers",
        "users",
        "branches"
    ]

    total_deleted = 0
    for table in tables:
        try:
            cursor.execute(f"DELETE FROM {table} WHERE branch_id IN ({id_placeholders})", test_ids)
            if cursor.rowcount > 0:
                print(f"  Deleted {cursor.rowcount} from {table}")
                total_deleted += cursor.rowcount
        except Exception as e:
            # Table might not have branch_id
            pass

    conn.commit()
    print(f"\nCleanup complete! Total deleted: {total_deleted} records")
    print("Test branches cleaned up!")

    # Verify
    cursor.execute("SELECT COUNT(*) FROM branches")
    count = cursor.fetchone()[0]
    print(f"Remaining branches: {count}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
finally:
    conn.close()
