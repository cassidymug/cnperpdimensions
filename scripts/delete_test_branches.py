#!/usr/bin/env python
"""Delete test branches directly"""

import sys
sys.path.insert(0, '.')

from app.core.database import engine
from sqlalchemy import text

conn = engine.connect()
trans = conn.begin()

try:
    # Get test branch IDs
    result = conn.execute(text("SELECT id FROM branches WHERE name ILIKE '%Test Branch%'"))
    ids = tuple(row[0] for row in result)

    if not ids:
        print("No test branches found")
        trans.commit()
        conn.close()
        exit(0)

    print(f"Found {len(ids)} test branches")

    # Build the ID list for IN clause
    id_list = "', '".join(ids)
    id_list = f"'{id_list}'"

    # Delete in dependency order
    # 1. Delete bank transactions for those accounts first
    result = conn.execute(text(f"DELETE FROM bank_transactions WHERE bank_account_id IN (SELECT id FROM bank_accounts WHERE branch_id IN ({id_list}))"))
    print(f"Deleted {result.rowcount} bank_transactions")

    # 2. Delete bank accounts
    result = conn.execute(text(f"DELETE FROM bank_accounts WHERE branch_id IN ({id_list})"))
    print(f"Deleted {result.rowcount} bank_accounts")

    # 3. Delete branches
    result = conn.execute(text(f"DELETE FROM branches WHERE id IN ({id_list})"))
    print(f"Deleted {result.rowcount} branches")

    trans.commit()
    print("✓ Committed")

    # Verify
    result = conn.execute(text("SELECT COUNT(*) FROM branches"))
    count = result.scalar()
    print(f"Remaining: {count}")

finally:
    conn.close()
