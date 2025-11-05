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
    print(f'Found {len(ids)} test branches\n')

    if not ids:
        conn.close()
        exit(0)

    id_list = "', '".join(ids)
    id_list = f"'{id_list}'"

    # Delete in proper order - handle those with branch_id first
    tables_with_branch_id = [
        'bank_reconciliations',
        'bank_transfers',
        'bank_accounts',
        'sales',
        'purchases',
        'purchase_orders',
        'invoices',
        'products',
        'customers',
        'suppliers',
        'users',
        'branches'
    ]

    for table in tables_with_branch_id:
        try:
            cursor.execute(f"DELETE FROM {table} WHERE branch_id IN ({id_list})")
            if cursor.rowcount > 0:
                print(f"Deleted {cursor.rowcount} from {table}")
        except Exception as e:
            print(f"Skipped {table}: {str(e)[:50]}")

    conn.commit()
    print('\n--- Verifying results ---')
    cursor.execute('SELECT COUNT(*) FROM branches')
    remaining = cursor.fetchone()[0]
    print(f'Remaining branches: {remaining}')

    cursor.execute("SELECT name, code FROM branches ORDER BY name")
    print('\nBranches still in database:')
    for name, code in cursor.fetchall():
        print(f'  - {name} ({code})')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
    conn.rollback()
finally:
    conn.close()
