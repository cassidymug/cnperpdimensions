#!/usr/bin/env python
import sys
sys.path.insert(0, '.')
from app.core.database import engine

conn = engine.raw_connection()
cursor = conn.cursor()

try:
    # Find the remaining test branch
    cursor.execute("SELECT id, name FROM branches WHERE name ILIKE '%Test%'")
    result = cursor.fetchone()

    if not result:
        print("No test branches found!")
        conn.close()
        exit(0)

    bid, name = result
    print(f"Found test branch: {name} (ID: {bid})\n")

    # Delete bank transactions first
    cursor.execute("DELETE FROM bank_transactions WHERE bank_account_id IN (SELECT id FROM bank_accounts WHERE branch_id = %s)", (bid,))
    rows = cursor.rowcount
    print(f"Deleted {rows} bank transactions")
    conn.commit()

    # Delete bank accounts
    cursor.execute("DELETE FROM bank_accounts WHERE branch_id = %s", (bid,))
    rows = cursor.rowcount
    print(f"Deleted {rows} bank accounts")
    conn.commit()

    # Delete the branch
    cursor.execute("DELETE FROM branches WHERE id = %s", (bid,))
    rows = cursor.rowcount
    print(f"Deleted {rows} branches")
    conn.commit()

    # Verify
    cursor.execute("SELECT COUNT(*) FROM branches")
    total = cursor.fetchone()[0]
    print(f"\nTotal branches remaining: {total}")

    cursor.execute("SELECT COUNT(*) FROM branches WHERE name ILIKE '%Test%'")
    test_count = cursor.fetchone()[0]
    print(f"Test branches remaining: {test_count}")

    if test_count == 0:
        print("\nSUCCESS! All test branches deleted!")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
finally:
    conn.close()
