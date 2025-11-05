#!/usr/bin/env python
import sys
sys.path.insert(0, '.')
from app.core.database import engine

conn = engine.raw_connection()
cursor = conn.cursor()

try:
    # Get test branch IDs
    cursor.execute("SELECT id FROM branches WHERE name ILIKE '%Test Branch%'")
    ids = [row[0] for row in cursor.fetchall()]
    print(f'Found {len(ids)} test branches')

    if not ids:
        conn.close()
        exit(0)

    # Delete each test branch's related data
    for bid in ids:
        print(f"Deleting data for branch: {bid}")
        cursor.execute("DELETE FROM reconciliation_items WHERE bank_transaction_id IN (SELECT id FROM bank_transactions WHERE branch_id = %s)", (bid,))
        cursor.execute("DELETE FROM bank_transactions WHERE branch_id = %s", (bid,))
        cursor.execute("DELETE FROM bank_reconciliations WHERE branch_id = %s", (bid,))
        cursor.execute("DELETE FROM bank_transfers WHERE branch_id = %s", (bid,))
        cursor.execute("DELETE FROM bank_accounts WHERE branch_id = %s", (bid,))
        cursor.execute("DELETE FROM sales WHERE branch_id = %s", (bid,))
        cursor.execute("DELETE FROM purchases WHERE branch_id = %s", (bid,))
        cursor.execute("DELETE FROM purchase_orders WHERE branch_id = %s", (bid,))
        cursor.execute("DELETE FROM invoices WHERE branch_id = %s", (bid,))
        cursor.execute("DELETE FROM products WHERE branch_id = %s", (bid,))
        cursor.execute("DELETE FROM customers WHERE branch_id = %s", (bid,))
        cursor.execute("DELETE FROM suppliers WHERE branch_id = %s", (bid,))
        cursor.execute("DELETE FROM users WHERE branch_id = %s", (bid,))
        cursor.execute("DELETE FROM branches WHERE id = %s", (bid,))

    conn.commit()

    cursor.execute('SELECT COUNT(*) FROM branches')
    remaining = cursor.fetchone()[0]
    print(f'\nSuccess! Remaining branches: {remaining}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    conn.rollback()
finally:
    conn.close()
