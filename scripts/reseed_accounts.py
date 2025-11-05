#!/usr/bin/env python3
"""
Reseed accounting codes to add VAT parent and sub-accounts.
This script updates existing accounts and adds new VAT-related accounts.
"""
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_db
import scripts.seeds.seed_accounts  # Import to register the seeder

def main():
    print("="*60)
    print("RESEEDING ACCOUNTING CODES")
    print("="*60)
    print("\nThis will add:")
    print("  - 1160: VAT Receivable (Input VAT) under Current Assets")
    print("  - 2131: VAT Control under Tax Liabilities")
    print("  - 2132: VAT Payable (Output VAT) under VAT Control")
    print("  - 2133: VAT Receivable (Input VAT - Contra) under VAT Control")
    print("\nExisting accounts will be preserved.")
    print("="*60)

    db = next(get_db())
    try:
        # Import and run the accounts seeder
        from scripts.seeds.registry import REGISTRY

        seeder_fn = REGISTRY.get("accounts")
        if not seeder_fn:
            print("[ERROR] Accounts seeder not found in registry!")
            return

        print("\n[SEEDING] Running accounts seeder...")
        seeder_fn(db)

        print("\n[SUCCESS] Accounting codes reseeded successfully!")
        print("\nNew VAT accounts added:")
        print("  ✓ 1160 - VAT Receivable (Input VAT)")
        print("  ✓ 2131 - VAT Control")
        print("  ✓ 2132 - VAT Payable (Output VAT)")
        print("  ✓ 2133 - VAT Receivable (Input VAT - Contra)")

        print("\n" + "="*60)
        print("Visit http://localhost:8010/static/accounting-codes.html")
        print("to see the updated chart of accounts")
        print("="*60)

    except Exception as e:
        print(f"\n[ERROR] Failed to reseed accounts: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
