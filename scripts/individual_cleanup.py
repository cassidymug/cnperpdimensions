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
    print(f'Found {len(ids)} test branches to delete\n')

    if not ids:
        conn.close()
        exit(0)

    # Delete one by one for better error handling
    for bid in ids:
        print(f"Processing branch {bid}...")

        tables_to_try = [
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
            'users'
        ]

        for table in tables_to_try:
            try:
                cursor.execute(f"DELETE FROM {table} WHERE branch_id = %s", (bid,))
                if cursor.rowcount > 0:
                    print(f"  - Deleted {cursor.rowcount} from {table}")
                conn.commit()  # Commit each delete separately
            except Exception as e:
                conn.rollback()
                # Continue with next table
                pass

        # Finally delete the branch itself
        try:
            cursor.execute("DELETE FROM branches WHERE id = %s", (bid,))
            conn.commit()
            print(f"  - Deleted branch")
        except Exception as e:
            conn.rollback()
            print(f"  - ERROR deleting branch: {e}")

    print('\n--- Verifying results ---')
    cursor.execute('SELECT COUNT(*) FROM branches')
    remaining = cursor.fetchone()[0]
    print(f'Remaining branches: {remaining}')

    if remaining > 0:
        cursor.execute("SELECT name, code FROM branches ORDER BY name")
        print('\nBranches in database:')
        for name, code in cursor.fetchall():
            marker = '(TEST)' if 'test' in name.lower() else '(REAL)'
            print(f'  - {name} ({code}) {marker}')

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
finally:
    conn.close()
