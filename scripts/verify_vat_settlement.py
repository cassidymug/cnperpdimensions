#!/usr/bin/env python3
"""
VAT Payment & Settlement Verification Script

This script verifies that the VAT payment/refund system is working correctly
by checking the database structure, testing the IFRS accounting service methods,
and validating journal entry creation.

Usage:
    python scripts/verify_vat_settlement.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from decimal import Decimal
from datetime import date, datetime
from app.core.database import SessionLocal, engine
from app.services.ifrs_accounting_service import IFRSAccountingService
from app.models.accounting import AccountingCode, AccountingEntry, JournalEntry
from app.models.vat import VatReconciliation, VatPayment
from sqlalchemy import text


def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}\n")


def verify_vat_accounts(db):
    """Verify that required VAT accounts exist"""
    print_section("1. Verifying VAT Account Structure")

    required_accounts = {
        '1160': 'VAT Receivable (Input VAT)',
        '2132': 'VAT Payable (Output VAT)',
        '2131': 'VAT Control'
    }

    all_exist = True
    for code, name in required_accounts.items():
        account = db.query(AccountingCode).filter(AccountingCode.code == code).first()
        if account:
            print(f"✅ Account {code} - {account.name}")
            print(f"   Type: {account.account_type}, Balance: {account.normal_balance}")
        else:
            print(f"❌ Account {code} - {name} NOT FOUND")
            all_exist = False

    return all_exist


def test_vat_payment_journals(db):
    """Test VAT payment journal entry creation"""
    print_section("2. Testing VAT Payment Journal Creation")

    try:
        ifrs_service = IFRSAccountingService(db)

        # Test data
        vat_output = Decimal('15400.00')  # From sales
        vat_input = Decimal('8200.00')     # From purchases
        net_payment = vat_output - vat_input  # 7200.00

        print(f"Test Scenario:")
        print(f"  VAT Collected (Output): BWP {vat_output:,.2f}")
        print(f"  VAT Paid (Input):       BWP {vat_input:,.2f}")
        print(f"  Net Payment:            BWP {net_payment:,.2f}")
        print()

        # Create test journal entries (will rollback after)
        journal_entries = ifrs_service.create_tax_payment_journal_entries(
            payment_amount=net_payment,
            payment_date=date.today(),
            branch_id='TEST_BRANCH',
            bank_account_id=None,  # Will use cash account
            vat_output_amount=vat_output,
            vat_input_amount=vat_input
        )

        print(f"✅ Successfully created {len(journal_entries)} journal entries:")
        total_debit = Decimal('0')
        total_credit = Decimal('0')

        for i, entry in enumerate(journal_entries, 1):
            account_code = db.query(AccountingCode).filter(
                AccountingCode.id == entry.accounting_code_id
            ).first()

            print(f"\n  Entry {i}:")
            print(f"    Account: {account_code.code} - {account_code.name}")
            print(f"    Type: {entry.entry_type.upper()}")
            print(f"    Debit:  BWP {entry.debit_amount:,.2f}")
            print(f"    Credit: BWP {entry.credit_amount:,.2f}")
            print(f"    Description: {entry.description}")

            total_debit += entry.debit_amount
            total_credit += entry.credit_amount

        print(f"\n  Totals:")
        print(f"    Debit:  BWP {total_debit:,.2f}")
        print(f"    Credit: BWP {total_credit:,.2f}")

        if total_debit == total_credit:
            print(f"  ✅ Journal entries are BALANCED")
        else:
            print(f"  ❌ Journal entries are NOT BALANCED")
            return False

        # Rollback to not persist test data
        db.rollback()
        print(f"\n  ℹ️  Test transaction rolled back (no data persisted)")

        return True

    except Exception as e:
        print(f"❌ Error creating VAT payment journals: {str(e)}")
        db.rollback()
        return False


def test_vat_refund_journals(db):
    """Test VAT refund journal entry creation"""
    print_section("3. Testing VAT Refund Journal Creation")

    try:
        ifrs_service = IFRSAccountingService(db)

        # Test data - refund scenario
        vat_output = Decimal('3500.00')   # From sales
        vat_input = Decimal('12000.00')    # From purchases
        net_refund = vat_input - vat_output  # 8500.00

        print(f"Test Scenario:")
        print(f"  VAT Collected (Output): BWP {vat_output:,.2f}")
        print(f"  VAT Paid (Input):       BWP {vat_input:,.2f}")
        print(f"  Net Refund:             BWP {net_refund:,.2f}")
        print()

        # Create test journal entries (will rollback after)
        journal_entries = ifrs_service.create_vat_refund_journal_entries(
            refund_amount=net_refund,
            refund_date=date.today(),
            branch_id='TEST_BRANCH',
            bank_account_id=None,  # Will use cash account
            vat_output_amount=vat_output,
            vat_input_amount=vat_input
        )

        print(f"✅ Successfully created {len(journal_entries)} journal entries:")
        total_debit = Decimal('0')
        total_credit = Decimal('0')

        for i, entry in enumerate(journal_entries, 1):
            account_code = db.query(AccountingCode).filter(
                AccountingCode.id == entry.accounting_code_id
            ).first()

            print(f"\n  Entry {i}:")
            print(f"    Account: {account_code.code} - {account_code.name}")
            print(f"    Type: {entry.entry_type.upper()}")
            print(f"    Debit:  BWP {entry.debit_amount:,.2f}")
            print(f"    Credit: BWP {entry.credit_amount:,.2f}")
            print(f"    Description: {entry.description}")

            total_debit += entry.debit_amount
            total_credit += entry.credit_amount

        print(f"\n  Totals:")
        print(f"    Debit:  BWP {total_debit:,.2f}")
        print(f"    Credit: BWP {total_credit:,.2f}")

        if total_debit == total_credit:
            print(f"  ✅ Journal entries are BALANCED")
        else:
            print(f"  ❌ Journal entries are NOT BALANCED")
            return False

        # Rollback to not persist test data
        db.rollback()
        print(f"\n  ℹ️  Test transaction rolled back (no data persisted)")

        return True

    except Exception as e:
        print(f"❌ Error creating VAT refund journals: {str(e)}")
        db.rollback()
        return False


def check_vat_reconciliations(db):
    """Check existing VAT reconciliations"""
    print_section("4. Checking VAT Reconciliations")

    reconciliations = db.query(VatReconciliation).order_by(
        VatReconciliation.period_start.desc()
    ).limit(5).all()

    if not reconciliations:
        print("  ℹ️  No VAT reconciliations found in database")
        return True

    print(f"  Found {len(reconciliations)} recent reconciliation(s):\n")

    for rec in reconciliations:
        print(f"  Period: {rec.period_start} to {rec.period_end}")
        print(f"    VAT Collected: BWP {rec.vat_collected:,.2f}")
        print(f"    VAT Paid:      BWP {rec.vat_paid:,.2f}")
        print(f"    Net Liability: BWP {rec.net_vat_liability:,.2f}")
        print(f"    Status:        {rec.status}")
        print(f"    Payment:       {rec.payment_status} (Outstanding: BWP {rec.outstanding_amount:,.2f})")

        # Check for payments
        payments = db.query(VatPayment).filter(
            VatPayment.vat_reconciliation_id == rec.id
        ).all()

        if payments:
            print(f"    Payments:      {len(payments)} payment(s)")
            for payment in payments:
                print(f"      - BWP {payment.amount_paid:,.2f} on {payment.payment_date} via {payment.payment_method}")
        print()

    return True


def check_vat_journal_entries(db):
    """Check existing VAT-related journal entries"""
    print_section("5. Checking VAT Journal Entries")

    # Check for VAT_SETTLEMENT entries
    settlement_entries = db.query(AccountingEntry).filter(
        AccountingEntry.book == 'VAT_SETTLEMENT'
    ).order_by(AccountingEntry.date_posted.desc()).limit(5).all()

    # Check for VAT_REFUND entries
    refund_entries = db.query(AccountingEntry).filter(
        AccountingEntry.book == 'VAT_REFUND'
    ).order_by(AccountingEntry.date_posted.desc()).limit(5).all()

    if not settlement_entries and not refund_entries:
        print("  ℹ️  No VAT settlement/refund journal entries found")
        print("  ℹ️  This is normal if no VAT payments have been recorded yet")
        return True

    if settlement_entries:
        print(f"  Found {len(settlement_entries)} VAT Settlement entries:\n")
        for entry in settlement_entries:
            print(f"    Date: {entry.date_posted}")
            print(f"    Particulars: {entry.particulars}")
            print(f"    Status: {entry.status}")

            # Get journal entry details
            journals = db.query(JournalEntry).filter(
                JournalEntry.accounting_entry_id == entry.id
            ).all()

            total_dr = sum(j.debit_amount for j in journals)
            total_cr = sum(j.credit_amount for j in journals)
            balanced = "✅" if total_dr == total_cr else "❌"

            print(f"    Entries: {len(journals)}, Balanced: {balanced} (DR: {total_dr}, CR: {total_cr})")
            print()

    if refund_entries:
        print(f"  Found {len(refund_entries)} VAT Refund entries:\n")
        for entry in refund_entries:
            print(f"    Date: {entry.date_posted}")
            print(f"    Particulars: {entry.particulars}")
            print(f"    Status: {entry.status}")

            journals = db.query(JournalEntry).filter(
                JournalEntry.accounting_entry_id == entry.id
            ).all()

            total_dr = sum(j.debit_amount for j in journals)
            total_cr = sum(j.credit_amount for j in journals)
            balanced = "✅" if total_dr == total_cr else "❌"

            print(f"    Entries: {len(journals)}, Balanced: {balanced} (DR: {total_dr}, CR: {total_cr})")
            print()

    return True


def main():
    """Main verification function"""
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "VAT SETTLEMENT VERIFICATION SCRIPT" + " " * 24 + "║")
    print("╚" + "═" * 78 + "╝")

    db = SessionLocal()

    try:
        results = []

        # Run all verification checks
        results.append(("VAT Account Structure", verify_vat_accounts(db)))
        results.append(("VAT Payment Journals", test_vat_payment_journals(db)))
        results.append(("VAT Refund Journals", test_vat_refund_journals(db)))
        results.append(("VAT Reconciliations", check_vat_reconciliations(db)))
        results.append(("VAT Journal Entries", check_vat_journal_entries(db)))

        # Summary
        print_section("Verification Summary")

        all_passed = True
        for check_name, passed in results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {status}: {check_name}")
            if not passed:
                all_passed = False

        print()

        if all_passed:
            print("  " + "─" * 76)
            print("  ✅ ALL CHECKS PASSED - VAT Settlement System is Ready!")
            print("  " + "─" * 76)
            print()
            print("  Next Steps:")
            print("  1. Go to http://localhost:8010/static/vat-reports.html")
            print("  2. Create a VAT reconciliation for a test period")
            print("  3. Record a payment to see the journal entries in action")
            print("  4. Check Journal Entries page to verify VAT_SETTLEMENT entries")
            print()
        else:
            print("  " + "─" * 76)
            print("  ❌ SOME CHECKS FAILED - Please review errors above")
            print("  " + "─" * 76)
            print()

    except Exception as e:
        print(f"\n❌ Error during verification: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == '__main__':
    main()
