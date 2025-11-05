#!/usr/bin/env python
import sys
sys.path.insert(0, '.')
from app.core.database import engine

conn = engine.raw_connection()
cursor = conn.cursor()

bid = '4c142b60-9b31-4681-8508-de78a6405c85'

try:
    print('Deleting test branch and all nested data...\n')

    # Delete reconciliation_items first (deepest dependency)
    cursor.execute('DELETE FROM reconciliation_items WHERE bank_transaction_id IN (SELECT id FROM bank_transactions WHERE branch_id = %s)', (bid,))
    print(f'Deleted {cursor.rowcount} reconciliation_items')
    conn.commit()

    # Delete bank transactions
    cursor.execute('DELETE FROM bank_transactions WHERE branch_id = %s', (bid,))
    print(f'Deleted {cursor.rowcount} bank_transactions')
    conn.commit()

    # Delete bank accounts
    cursor.execute('DELETE FROM bank_accounts WHERE branch_id = %s', (bid,))
    print(f'Deleted {cursor.rowcount} bank_accounts')
    conn.commit()

    # Delete branch
    cursor.execute('DELETE FROM branches WHERE id = %s', (bid,))
    print(f'Deleted {cursor.rowcount} branches')
    conn.commit()

    # Verify
    cursor.execute('SELECT COUNT(*) FROM branches')
    total = cursor.fetchone()[0]
    print(f'\nTotal branches remaining: {total}')
    print('SUCCESS! All test branches deleted!')

except Exception as e:
    print(f'ERROR: {e}')
    conn.rollback()
finally:
    conn.close()
