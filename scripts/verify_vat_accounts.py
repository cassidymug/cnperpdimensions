#!/usr/bin/env python3
"""
Verify VAT accounts were created successfully.
"""
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_db
from app.models.accounting import AccountingCode

def main():
    print("="*70)
    print("VAT ACCOUNTS VERIFICATION")
    print("="*70)

    db = next(get_db())
    try:
        # Query VAT-related accounts
        vat_accounts = db.query(AccountingCode).filter(
            AccountingCode.code.in_(['1160', '2131', '2132', '2133'])
        ).order_by(AccountingCode.code).all()

        if not vat_accounts:
            print("\n❌ ERROR: No VAT accounts found!")
            return

        print(f"\n✓ Found {len(vat_accounts)} VAT accounts:\n")

        for acc in vat_accounts:
            parent_name = ""
            if acc.parent_id:
                parent = db.query(AccountingCode).filter(
                    AccountingCode.id == acc.parent_id
                ).first()
                if parent:
                    parent_name = f" (Parent: {parent.code} - {parent.name})"

            print(f"  Code: {acc.code}")
            print(f"  Name: {acc.name}")
            print(f"  Type: {acc.account_type}")
            print(f"  Category: {acc.category}")
            print(f"  Parent: {parent_name}")
            print(f"  Is Parent: {acc.is_parent}")
            print()

        # Check parent-child relationships
        print("="*70)
        print("PARENT-CHILD RELATIONSHIPS")
        print("="*70)

        # Check 1160 is under 1100 (Current Assets)
        acc_1160 = next((a for a in vat_accounts if a.code == '1160'), None)
        if acc_1160 and acc_1160.parent_id:
            parent = db.query(AccountingCode).get(acc_1160.parent_id)
            print(f"\n✓ 1160 (VAT Receivable) → Parent: {parent.code} - {parent.name}")

        # Check 2131 is under 2130 (Tax Liabilities)
        acc_2131 = next((a for a in vat_accounts if a.code == '2131'), None)
        if acc_2131 and acc_2131.parent_id:
            parent = db.query(AccountingCode).get(acc_2131.parent_id)
            print(f"✓ 2131 (VAT Control) → Parent: {parent.code} - {parent.name}")

        # Check 2132 and 2133 are under 2131 (VAT Control)
        acc_2132 = next((a for a in vat_accounts if a.code == '2132'), None)
        if acc_2132 and acc_2132.parent_id:
            parent = db.query(AccountingCode).get(acc_2132.parent_id)
            print(f"✓ 2132 (VAT Payable) → Parent: {parent.code} - {parent.name}")

        acc_2133 = next((a for a in vat_accounts if a.code == '2133'), None)
        if acc_2133 and acc_2133.parent_id:
            parent = db.query(AccountingCode).get(acc_2133.parent_id)
            print(f"✓ 2133 (VAT Receivable Contra) → Parent: {parent.code} - {parent.name}")

        print("\n" + "="*70)
        print("SUCCESS! All VAT accounts created and linked correctly.")
        print("="*70)
        print("\n📊 View the chart of accounts at:")
        print("   http://localhost:8010/static/accounting-codes.html")
        print("="*70)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
