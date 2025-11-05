#!/usr/bin/env python3
"""
Set branch product quantities for POS smoke testing.
- Ensures products assigned to MAIN branch have a positive on-hand quantity.
- If quantity is NULL or <= 0, set to a default (20).
"""
import os
import sys
from sqlalchemy import create_engine, text

# Make sure we can import settings
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import settings

DEFAULT_QTY = int(os.environ.get("SEED_QTY", 20))
BRANCH_CODE = os.environ.get("SEED_BRANCH", "MAIN")

def main():
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        # Find branch id
        branch_id = conn.execute(text("SELECT id FROM branches WHERE code = :code LIMIT 1"), {"code": BRANCH_CODE}).scalar()
        if not branch_id:
            print(f"❌ Branch with code '{BRANCH_CODE}' not found.")
            sys.exit(1)
        # Update only products in this branch with non-positive quantity
        result = conn.execute(
            text(
                """
                UPDATE products
                SET quantity = :qty
                WHERE branch_id = :branch_id AND (quantity IS NULL OR quantity <= 0)
                """
            ),
            {"qty": DEFAULT_QTY, "branch_id": branch_id}
        )
        print(f"✅ Set quantity={DEFAULT_QTY} for {result.rowcount or 0} products in branch {BRANCH_CODE} ({branch_id}).")

if __name__ == "__main__":
    main()
