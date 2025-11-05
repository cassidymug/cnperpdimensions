#!/usr/bin/env python
"""
Cleanup test branches and all their related records.
"""

from app.core.database import engine
from sqlalchemy import text
import warnings

warnings.filterwarnings('ignore')

def cleanup_test_branches():
    """Delete test branches and all their dependent records"""

    conn = engine.connect()
    trans = conn.begin()

    try:
        # Get test branch IDs
        result = conn.execute(text('''
            SELECT id FROM branches
            WHERE name ILIKE '%Test Branch%'
        '''))
        test_branch_ids = [row[0] for row in result]

        if not test_branch_ids:
            print("No test branches found to delete")
            trans.commit()
            conn.close()
            return

        print(f"Found {len(test_branch_ids)} test branches")

        # Delete in dependency order (reverse FK order)
        delete_queries = [
            # Level 1: Transaction-like records
            ('account_reconciliations', 'statement_account_id IS NULL AND branch_id IN'),
            ('bank_reconciliations', 'branch_id IN'),
            ('bank_transactions', 'branch_id IN'),
            ('cash_flows', 'branch_id IN'),
            ('cash_management_records', 'branch_id IN'),
            ('petty_cash_records', 'branch_id IN'),
            ('bank_transfers', 'branch_id IN'),

            # Level 2: Sales/Purchase related
            ('sales', 'branch_id IN'),
            ('purchases', 'branch_id IN'),
            ('purchase_orders', 'branch_id IN'),
            ('invoices', 'branch_id IN'),

            # Level 3: Inventory/Products
            ('products', 'branch_id IN'),
            ('inventory_movements', 'branch_id IN'),

            # Level 4: People/Entities
            ('customers', 'branch_id IN'),
            ('suppliers', 'branch_id IN'),
            ('users', 'branch_id IN'),

            # Level 5: Finance
            ('bank_accounts', 'branch_id IN'),

            # Finally: Branches
            ('branches', 'id IN'),
        ]

        id_list = ','.join(f"'{bid}'" for bid in test_branch_ids)

        for table, condition in delete_queries:
            try:
                query = f"DELETE FROM {table} WHERE {condition} ({id_list})"
                result = conn.execute(text(query))
                if result.rowcount > 0:
                    print(f"  Deleted {result.rowcount} from {table}")
            except Exception as e:
                # Table might not exist or have different structure
                pass

        trans.commit()
        print("\n✓ Cleanup complete!")

        # Verify remaining branches
        result = conn.execute(text('SELECT COUNT(*) FROM branches'))
        count = result.scalar()
        print(f"Remaining branches: {count}")

    except Exception as e:
        print(f"✗ Error during cleanup: {e}")
        trans.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    cleanup_test_branches()
