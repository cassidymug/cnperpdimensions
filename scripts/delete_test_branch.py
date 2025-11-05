#!/usr/bin/env python
"""
Delete a specific test branch with proper cascade handling.
This script properly handles the FK dependency chain.
"""

import sys
sys.path.insert(0, '.')

from app.core.database import engine

# The test branch ID that keeps failing to delete
TEST_BRANCH_ID = '4c142b60-9b31-4681-8508-de78a6405c85'

def delete_branch_cascade():
    """Delete the test branch with proper cascade order"""
    conn = engine.raw_connection()
    cursor = conn.cursor()

    try:
        print(f"Starting cascade delete for branch: {TEST_BRANCH_ID}\n")

        # Step 1: Delete reconciliation items (deepest dependency)
        print("Step 1: Deleting reconciliation items...")
        cursor.execute("""
            DELETE FROM reconciliation_items
            WHERE bank_transaction_id IN (
                SELECT id FROM bank_transactions
                WHERE bank_account_id IN (
                    SELECT id FROM bank_accounts WHERE branch_id = %s
                )
            )
            OR bank_reconciliation_id IN (
                SELECT id FROM bank_reconciliations
                WHERE bank_account_id IN (
                    SELECT id FROM bank_accounts WHERE branch_id = %s
                )
            )
        """, (TEST_BRANCH_ID, TEST_BRANCH_ID))
        count = cursor.rowcount
        print(f"  -> Deleted {count} reconciliation items")
        conn.commit()

        # Step 2: Delete bank reconciliations
        print("Step 2: Deleting bank reconciliations...")
        cursor.execute("""
            DELETE FROM bank_reconciliations
            WHERE bank_account_id IN (
                SELECT id FROM bank_accounts WHERE branch_id = %s
            )
        """, (TEST_BRANCH_ID,))
        count = cursor.rowcount
        print(f"  -> Deleted {count} bank reconciliations")
        conn.commit()

        # Step 3: Delete bank transactions
        print("Step 3: Deleting bank transactions...")
        cursor.execute("""
            DELETE FROM bank_transactions
            WHERE bank_account_id IN (
                SELECT id FROM bank_accounts WHERE branch_id = %s
            )
        """, (TEST_BRANCH_ID,))
        count = cursor.rowcount
        print(f"  -> Deleted {count} bank transactions")
        conn.commit()

        # Step 4: Delete bank transfers
        print("Step 4: Deleting bank transfers...")
        cursor.execute("""
            DELETE FROM bank_transfers
            WHERE source_account_id IN (
                SELECT id FROM bank_accounts WHERE branch_id = %s
            )
            OR destination_account_id IN (
                SELECT id FROM bank_accounts WHERE branch_id = %s
            )
        """, (TEST_BRANCH_ID, TEST_BRANCH_ID))
        count = cursor.rowcount
        print(f"  -> Deleted {count} bank transfers")
        conn.commit()

        # Step 5: Delete bank accounts
        print("Step 5: Deleting bank accounts...")
        cursor.execute("""
            DELETE FROM bank_accounts
            WHERE branch_id = %s
        """, (TEST_BRANCH_ID,))
        count = cursor.rowcount
        print(f"  -> Deleted {count} bank accounts")
        conn.commit()

        # Step 6: Delete sales
        print("Step 6: Deleting sales...")
        try:
            cursor.execute("DELETE FROM sales WHERE branch_id = %s", (TEST_BRANCH_ID,))
            count = cursor.rowcount
            print(f"  -> Deleted {count} sales")
            conn.commit()
        except Exception as e:
            print(f"  -> Skipped (no branch_id column or not applicable)")
            conn.rollback()

        # Step 7: Delete purchases
        print("Step 7: Deleting purchases...")
        try:
            cursor.execute("DELETE FROM purchases WHERE branch_id = %s", (TEST_BRANCH_ID,))
            count = cursor.rowcount
            print(f"  -> Deleted {count} purchases")
            conn.commit()
        except Exception as e:
            print(f"  -> Skipped (no branch_id column or not applicable)")
            conn.rollback()

        # Step 8: Delete purchase orders
        print("Step 8: Deleting purchase orders...")
        try:
            cursor.execute("DELETE FROM purchase_orders WHERE branch_id = %s", (TEST_BRANCH_ID,))
            count = cursor.rowcount
            print(f"  -> Deleted {count} purchase orders")
            conn.commit()
        except Exception as e:
            print(f"  -> Skipped (no branch_id column or not applicable)")
            conn.rollback()

        # Step 9: Delete invoices
        print("Step 9: Deleting invoices...")
        try:
            cursor.execute("DELETE FROM invoices WHERE branch_id = %s", (TEST_BRANCH_ID,))
            count = cursor.rowcount
            print(f"  -> Deleted {count} invoices")
            conn.commit()
        except Exception as e:
            print(f"  -> Skipped (no branch_id column or not applicable)")
            conn.rollback()

        # Step 10: Delete products
        print("Step 10: Deleting products...")
        try:
            cursor.execute("DELETE FROM products WHERE branch_id = %s", (TEST_BRANCH_ID,))
            count = cursor.rowcount
            print(f"  -> Deleted {count} products")
            conn.commit()
        except Exception as e:
            print(f"  -> Skipped (no branch_id column or not applicable)")
            conn.rollback()

        # Step 11: Delete inventory transactions
        print("Step 11: Deleting inventory transactions...")
        try:
            cursor.execute("DELETE FROM inventory_transactions WHERE branch_id = %s", (TEST_BRANCH_ID,))
            count = cursor.rowcount
            print(f"  -> Deleted {count} inventory transactions")
            conn.commit()
        except Exception as e:
            print(f"  -> Skipped (no branch_id column or not applicable)")
            conn.rollback()

        # Step 12: Delete customers
        print("Step 12: Deleting customers...")
        try:
            cursor.execute("DELETE FROM customers WHERE branch_id = %s", (TEST_BRANCH_ID,))
            count = cursor.rowcount
            print(f"  -> Deleted {count} customers")
            conn.commit()
        except Exception as e:
            print(f"  -> Skipped (no branch_id column or not applicable)")
            conn.rollback()

        # Step 13: Delete suppliers
        print("Step 13: Deleting suppliers...")
        try:
            cursor.execute("DELETE FROM suppliers WHERE branch_id = %s", (TEST_BRANCH_ID,))
            count = cursor.rowcount
            print(f"  -> Deleted {count} suppliers")
            conn.commit()
        except Exception as e:
            print(f"  -> Skipped (no branch_id column or not applicable)")
            conn.rollback()

        # Step 14: Delete users
        print("Step 14: Deleting users...")
        try:
            cursor.execute("DELETE FROM users WHERE branch_id = %s", (TEST_BRANCH_ID,))
            count = cursor.rowcount
            print(f"  -> Deleted {count} users")
            conn.commit()
        except Exception as e:
            print(f"  -> Skipped (no branch_id column or not applicable)")
            conn.rollback()

        # Step 15: Finally delete the branch itself
        print("Step 15: Deleting the branch...")
        cursor.execute("DELETE FROM branches WHERE id = %s", (TEST_BRANCH_ID,))
        count = cursor.rowcount
        print(f"  -> Deleted {count} branches")
        conn.commit()

        print("\n" + "="*60)
        print("SUCCESS! Test branch and all related data deleted!")
        print("="*60)

        # Verify
        cursor.execute("SELECT COUNT(*) FROM branches")
        total = cursor.fetchone()[0]
        print(f"\nRemaining branches in database: {total}")

        cursor.execute("SELECT name FROM branches ORDER BY name")
        remaining = cursor.fetchall()
        print("\nRemaining branches:")
        for row in remaining:
            print(f"  - {row[0]}")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    delete_branch_cascade()
