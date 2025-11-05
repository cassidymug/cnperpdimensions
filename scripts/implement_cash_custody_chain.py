"""
Cash Custody Chain Implementation Script

This script:
1. Creates account 1114 "Undeposited Funds (Salesperson Takings)"
2. Deletes all existing incorrect journal entries for the 8 sales
3. Recreates journal entries with correct:
   - VAT calculation (total_amount already includes VAT)
   - Cash custody (cash -> 1114 Takings, not directly to 1111)

Usage:
    python scripts/implement_cash_custody_chain.py --preview   # Dry run
    python scripts/implement_cash_custody_chain.py --execute   # Execute changes
"""

import sys
from decimal import Decimal
from app.core.database import SessionLocal, engine
from sqlalchemy import text
from app.models.sales import Sale
from app.models.accounting import AccountingCode, JournalEntry


def preview_changes(db):
    """Preview what will be changed"""
    print("\n" + "="*80)
    print("CASH CUSTODY CHAIN IMPLEMENTATION - PREVIEW")
    print("="*80)

    # 1. Check if account 1114 exists
    print("\n[STEP 1] Check Undeposited Funds Account")
    account_1114 = db.query(AccountingCode).filter(AccountingCode.code == '1114').first()
    if account_1114:
        print(f"  ✓ Account 1114 exists: {account_1114.name}")
    else:
        print("  ✗ Account 1114 does NOT exist")
        print("  → Will create: 1114 - Undeposited Funds (Salesperson Takings)")

    # 2. Find ALL sales (we will recreate journal entries for all of them)
    print("\n[STEP 2] Identify All Cash Sales")

    # Get all sales
    all_sales = db.query(Sale).filter(Sale.payment_method == 'cash').order_by(Sale.date).all()

    sales_data = []
    for sale in all_sales:
        # Calculate what SHOULD be
        total = Decimal(str(sale.total_amount))
        vat = Decimal(str(sale.total_vat_amount))
        revenue_ex_vat = total - vat

        print(f"\n  Sale: {str(sale.id)[:8]}...")
        print(f"    Date: {sale.date}")
        print(f"    Payment: {sale.payment_method}")
        print(f"    Total (inc VAT): P {total:,.2f}")
        print(f"    VAT: P {vat:,.2f}")
        print(f"    Revenue (ex-VAT): P {revenue_ex_vat:,.2f}")

        sales_data.append(sale)

    print(f"\n  Total cash sales found: {len(sales_data)}")

    # 3. Show what new entries will look like (sample)
    if sales_data:
        print("\n[STEP 3] Sample New Journal Entries (First Sale)")
        sample = sales_data[0]
        total = Decimal(str(sample.total_amount))
        vat = Decimal(str(sample.total_vat_amount))
        revenue = total - vat

        print(f"\n  For sale {str(sample.id)[:8]}... (P {total:,.2f}):")
        print(f"    Dr 1114 Undeposited Funds (Takings)  P {total:,.2f}")
        print(f"       Cr Revenue (ex-VAT)               P {revenue:,.2f}")
        print(f"       Cr VAT Payable                    P {vat:,.2f}")
        print(f"    Dr COGS                              P [varies]")
        print(f"       Cr Inventory                      P [varies]")

    print("\n[STEP 4] Summary")
    print(f"  • Create account: 1114 Undeposited Funds")
    print(f"  • Will delete ALL existing entries for {len(sales_data)} sales")
    print(f"  • Will recreate entries for: {len(sales_data)} sales")
    print(f"  • Fix VAT calculation: Use total_amount - total_vat_amount for revenue")
    print(f"  • Fix cash custody: Cash -> 1114 (not 1111 directly)")

    print("\n" + "="*80)
    print("To execute these changes, run:")
    print("  python scripts\\implement_cash_custody_chain.py --execute")
    print("="*80 + "\n")

    return len(sales_data)
def execute_changes(db):
    """Execute the cash custody chain implementation"""
    print("\n" + "="*80)
    print("EXECUTING CASH CUSTODY CHAIN IMPLEMENTATION")
    print("="*80)

    try:
        # STEP 1: Create account 1114
        print("\n[STEP 1] Creating Undeposited Funds Account...")
        account_1114 = db.query(AccountingCode).filter(AccountingCode.code == '1114').first()

        if not account_1114:
            account_1114 = AccountingCode(
                code='1114',
                name='Undeposited Funds (Salesperson Takings)',
                account_type='Asset',
                category='Cash and Cash Equivalents',
                reporting_tag='A1.1'
            )
            db.add(account_1114)
            db.flush()
            print(f"  ✓ Created account 1114: {account_1114.name}")
        else:
            print(f"  ✓ Account 1114 already exists: {account_1114.name}")

        # STEP 2: Get all cash sales
        print("\n[STEP 2] Finding Cash Sales...")
        cash_sales = db.query(Sale).filter(Sale.payment_method == 'cash').all()
        sale_ids = [sale.id for sale in cash_sales]
        print(f"  Found {len(sale_ids)} cash sales")

        # STEP 3: Delete ALL existing journal entries for these sales
        # We'll delete by accounting_entry_id to ensure we get all related entries
        print("\n[STEP 3] Deleting ALL Existing Journal Entries for Cash Sales...")

        # First, find all accounting entries for these sales
        from app.models.accounting import AccountingEntry

        total_deleted = 0
        for sale in cash_sales:
            # Find accounting entries that reference this sale
            # This is based on the pattern in create_sale_journal_entries() which creates an accounting_entry
            # We'll delete ALL entries for all sales and recreate them
            result = db.execute(text("""
                DELETE FROM journal_entries
                WHERE accounting_entry_id IN (
                    SELECT id FROM accounting_entries
                    WHERE description LIKE :pattern
                )
                RETURNING id
            """), {'pattern': f'%sale #{sale.id}%'})

            count = result.rowcount
            total_deleted += count
            if count > 0:
                print(f"  Deleted {count} entries for sale {str(sale.id)[:8]}...")

        db.commit()  # Commit deletions
        print(f"  ✓ Deleted {total_deleted} journal entries total")

        # STEP 4: Recreate journal entries with correct logic
        print("\n[STEP 4] Recreating Journal Entries with Correct Logic...")

        # Import the service
        from app.services.ifrs_accounting_service import IFRSAccountingService
        accounting_service = IFRSAccountingService(db)

        recreated_count = 0
        for sale in cash_sales:
            # Create new journal entries using the FIXED accounting service
            accounting_service.create_sale_journal_entries(sale)
            recreated_count += 1
            print(f"  Created entries for sale {str(sale.id)[:8]}... (P {sale.total_amount:,.2f})")

        print(f"  ✓ Recreated entries for {recreated_count} sales")

        # Commit all changes
        db.commit()

        print("\n[SUCCESS] Cash custody chain implementation completed!")
        print(f"  • Account 1114 created")
        print(f"  • {total_deleted} old entries deleted")
        print(f"  • {recreated_count} sales recreated with correct logic")
        print(f"  • VAT calculation fixed (ex-VAT revenue)")
        print(f"  • Cash custody chain in place (cash -> 1114 Takings)")

        print("\n" + "="*80)

    except Exception as e:
        db.rollback()
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/implement_cash_custody_chain.py --preview")
        print("  python scripts/implement_cash_custody_chain.py --execute")
        sys.exit(1)

    mode = sys.argv[1]

    db = SessionLocal()
    try:
        if mode == '--preview':
            count = preview_changes(db)
            sys.exit(0)
        elif mode == '--execute':
            execute_changes(db)
            sys.exit(0)
        else:
            print(f"Unknown mode: {mode}")
            print("Use --preview or --execute")
            sys.exit(1)
    finally:
        db.close()


if __name__ == '__main__':
    main()
