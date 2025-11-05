#!/usr/bin/env python
"""
Delete test bank transactions and accounts
"""

import sys
sys.path.insert(0, '.')

from app.core.database import engine
from sqlalchemy import text

conn = engine.raw_connection()
cursor = conn.cursor()

try:
    print("Cleaning up test bank data...\n")

    # Find test bank accounts (belonging to the test branch or with 'test' in name)
    cursor.execute("""
        SELECT id, name FROM bank_accounts
        WHERE name ILIKE '%test%' OR branch_id = '4c142b60-9b31-4681-8508-de78a6405c85'
        ORDER BY name
    """)
    accounts = cursor.fetchall()
    print(f"Found {len(accounts)} test bank accounts:\n")

    for account_id, account_name in accounts:
        print(f"  - {account_name} (ID: {account_id})")

        # Delete in reverse FK order (deepest first)
        # 1. Delete reconciliation items
        cursor.execute("""
            DELETE FROM reconciliation_items
            WHERE bank_reconciliation_id IN (
                SELECT id FROM bank_reconciliations WHERE bank_account_id = %s
            ) OR bank_transaction_id IN (
                SELECT id FROM bank_transactions WHERE bank_account_id = %s
            )
        """, (account_id, account_id))
        recon_items_count = cursor.rowcount
        conn.commit()

        # 2. Delete bank reconciliations for this account
        cursor.execute("DELETE FROM bank_reconciliations WHERE bank_account_id = %s", (account_id,))
        recon_count = cursor.rowcount
        conn.commit()

        # 3. Delete reconciliation items for transactions (if any remain)
        cursor.execute("""
            DELETE FROM reconciliation_items
            WHERE bank_transaction_id IN (
                SELECT id FROM bank_transactions WHERE bank_account_id = %s
            )
        """, (account_id,))
        del_count = cursor.rowcount
        conn.commit()

        # 4. Delete bank transactions
        cursor.execute("DELETE FROM bank_transactions WHERE bank_account_id = %s", (account_id,))
        trans_count = cursor.rowcount
        conn.commit()

        # 5. Delete the bank account
        cursor.execute("DELETE FROM bank_accounts WHERE id = %s", (account_id,))
        acc_count = cursor.rowcount
        conn.commit()

        print(f"    - Deleted {recon_items_count} recon items, {recon_count} reconciliations, {del_count} more items, {trans_count} transactions, {acc_count} account")

    print("\n--- Final Summary ---")
    cursor.execute("SELECT COUNT(*) FROM bank_accounts WHERE name ILIKE '%test%'")
    test_count = cursor.fetchone()[0]
    print(f"Test bank accounts remaining: {test_count}")

    cursor.execute("SELECT COUNT(*) FROM bank_accounts WHERE branch_id = '4c142b60-9b31-4681-8508-de78a6405c85'")
    test_branch_count = cursor.fetchone()[0]
    print(f"Bank accounts for test branch: {test_branch_count}")

    if test_count == 0 and test_branch_count == 0:
        print("\nSUCCESS! All test bank data cleaned up!")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
finally:
    conn.close()
