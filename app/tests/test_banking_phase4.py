"""
Comprehensive Test Suite for Banking Dimensional Accounting GL Posting

Tests for Banking Module Phase 4 dimensional accounting implementation.
Validates GL posting, reconciliation, cash position, transfer tracking, and dimensional analysis.

Run with:
    pytest app/tests/test_banking_phase4.py -v
    pytest app/tests/test_banking_phase4.py::TestBankingGLPosting -v
"""
import pytest
import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from uuid import uuid4

from app.core.database import SessionLocal
from app.models.banking import (
    BankTransaction, BankReconciliation, BankTransferAllocation, BankAccount
)
from app.models.accounting import JournalEntry, AccountingCode
from app.models.accounting_dimensions import AccountingDimensionValue, AccountingDimensionAssignment
from app.models.branch import Branch
from app.models.user import User
from app.services.banking_service import BankingService

# Mark all tests in this module as async-capable
pytestmark = pytest.mark.asyncio


@pytest.fixture
def db():
    """Create a test database session"""
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def test_setup(db: Session):
    """Setup common test data for banking tests"""
    # Create test branch
    branch = Branch(
        id="test-branch-banking",
        name="Banking Test Branch",
        branch_number="001",
        country="US",
        state="CA",
        town="Test Town"
    )
    db.add(branch)
    db.flush()

    # Create test user
    user = User(
        id="test-user-banking",
        username="bankinguser",
        email="banking@example.com"
    )
    db.add(user)
    db.flush()

    # Create dimension values (cost centers)
    cc_hq = AccountingDimensionValue(
        id="cc-hq",
        dimension_id="dim-cc",
        code="CC-HQ",
        name="Headquarters",
        hierarchy_level=1,
        parent_value_id=None
    )
    cc_branch1 = AccountingDimensionValue(
        id="cc-br1",
        dimension_id="dim-cc",
        code="CC-BR1",
        name="Branch 1",
        hierarchy_level=2,
        parent_value_id="cc-hq"
    )
    cc_branch2 = AccountingDimensionValue(
        id="cc-br2",
        dimension_id="dim-cc",
        code="CC-BR2",
        name="Branch 2",
        hierarchy_level=2,
        parent_value_id="cc-hq"
    )
    db.add_all([cc_hq, cc_branch1, cc_branch2])
    db.flush()

    # Create projects
    proj_operating = AccountingDimensionValue(
        id="proj-ops",
        dimension_id="dim-proj",
        code="PROJ-OPS",
        name="Operating",
        hierarchy_level=1,
        parent_value_id=None
    )
    proj_capital = AccountingDimensionValue(
        id="proj-cap",
        dimension_id="dim-proj",
        code="PROJ-CAP",
        name="Capital",
        hierarchy_level=1,
        parent_value_id=None
    )
    db.add_all([proj_operating, proj_capital])
    db.flush()

    # Create departments
    dept_treasury = AccountingDimensionValue(
        id="dept-treas",
        dimension_id="dim-dept",
        code="DEPT-TREAS",
        name="Treasury",
        hierarchy_level=1,
        parent_value_id=None
    )
    dept_operations = AccountingDimensionValue(
        id="dept-ops",
        dimension_id="dim-dept",
        code="DEPT-OPS",
        name="Operations",
        hierarchy_level=1,
        parent_value_id=None
    )
    db.add_all([dept_treasury, dept_operations])
    db.flush()

    # Create GL accounts
    bank_account = AccountingCode(
        id="bank-1",
        code="1010",
        name="Cash - Operating Account",
        account_type="Asset",
        account_class="Current Assets"
    )
    bank_savings = AccountingCode(
        id="bank-2",
        code="1020",
        name="Cash - Savings Account",
        account_type="Asset",
        account_class="Current Assets"
    )
    revenue_account = AccountingCode(
        id="rev-bank",
        code="4500",
        name="Interest Income",
        account_type="Revenue",
        account_class="Other Income"
    )
    offset_account = AccountingCode(
        id="offset-bank",
        code="9999",
        name="Temporary Offset",
        account_type="Liability",
        account_class="Temporary"
    )
    db.add_all([bank_account, bank_savings, revenue_account, offset_account])
    db.flush()

    # Create bank accounts
    ba_operating = BankAccount(
        id="ba-op",
        account_number="1234567890",
        bank_name="Test Bank",
        account_name="Operating Account",
        account_type="checking",
        gl_account_id=bank_account.id,
        branch_id=branch.id,
        opening_balance=Decimal("100000.00"),
        current_balance=Decimal("100000.00")
    )
    ba_savings = BankAccount(
        id="ba-sav",
        account_number="9876543210",
        bank_name="Test Bank",
        account_name="Savings Account",
        account_type="savings",
        gl_account_id=bank_savings.id,
        branch_id=branch.id,
        opening_balance=Decimal("50000.00"),
        current_balance=Decimal("50000.00")
    )
    db.add_all([ba_operating, ba_savings])
    db.flush()

    db.commit()

    return {
        'branch': branch,
        'user': user,
        'cost_centers': {
            'hq': cc_hq,
            'branch1': cc_branch1,
            'branch2': cc_branch2
        },
        'projects': {
            'operating': proj_operating,
            'capital': proj_capital
        },
        'departments': {
            'treasury': dept_treasury,
            'operations': dept_operations
        },
        'gl_accounts': {
            'bank': bank_account,
            'bank_savings': bank_savings,
            'revenue': revenue_account,
            'offset': offset_account
        },
        'bank_accounts': {
            'operating': ba_operating,
            'savings': ba_savings
        }
    }


class TestBankingGLPosting:
    """Test GL posting for bank transactions"""

    def test_post_bank_deposit_with_all_dimensions(self, db: Session, test_setup):
        """Test posting bank deposit with all dimensions assigned"""
        transaction = BankTransaction(
            id="txn-deposit-1",
            transaction_type="deposit",
            amount=Decimal("50000.00"),
            transaction_date=date.today(),
            description="Customer deposit",
            bank_account_id=test_setup['bank_accounts']['operating'].id,
            branch_id=test_setup['branch'].id,
            cost_center_id=test_setup['cost_centers']['hq'].id,
            project_id=test_setup['projects']['operating'].id,
            department_id=test_setup['departments']['treasury'].id,
            gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
            posting_status='draft'
        )
        db.add(transaction)
        db.commit()

        # Post to accounting
        service = BankingService(db)
        result = asyncio.run(service.post_bank_transaction_to_accounting(
            transaction.id,
            test_setup['user'].id
        ))

        # Verify posting was successful
        assert result['success'] is True
        assert result['transaction_id'] == transaction.id
        assert result['entries_created'] == 2  # Bank debit + Offset credit

        # Verify journal entries were created
        entries = db.query(JournalEntry).filter(
            JournalEntry.reference.like(f"%BANK-{transaction.id}%")
        ).all()
        assert len(entries) == 2

        # Verify GL is balanced
        total_debit = sum(e.debit for e in entries if e.debit)
        total_credit = sum(e.credit for e in entries if e.credit)
        assert abs(total_debit - total_credit) < Decimal("0.01")

        # Verify dimensions are preserved in GL entries
        for entry in entries:
            assert len(entry.dimension_assignments) > 0
            dim_ids = [da.dimension_value_id for da in entry.dimension_assignments]
            assert test_setup['cost_centers']['hq'].id in dim_ids

        # Verify transaction posting status updated
        updated_txn = db.query(BankTransaction).filter(
            BankTransaction.id == transaction.id
        ).first()
        assert updated_txn.posting_status == 'posted'
        assert updated_txn.posted_by == test_setup['user'].id

    def test_post_bank_withdrawal_with_partial_dimensions(self, db: Session, test_setup):
        """Test posting bank withdrawal with only some dimensions"""
        transaction = BankTransaction(
            id="txn-withdraw-1",
            transaction_type="withdrawal",
            amount=Decimal("25000.00"),
            transaction_date=date.today(),
            description="Payroll withdrawal",
            bank_account_id=test_setup['bank_accounts']['operating'].id,
            branch_id=test_setup['branch'].id,
            cost_center_id=test_setup['cost_centers']['branch1'].id,
            project_id=None,  # No project
            department_id=test_setup['departments']['operations'].id,
            gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
            posting_status='draft'
        )
        db.add(transaction)
        db.commit()

        service = BankingService(db)
        result = service.post_bank_transaction_to_accounting(transaction.id)

        assert result['success'] is True
        assert result['total_amount'] == 25000.0

        # Verify dimensions assigned are only cost_center and department
        entries = db.query(JournalEntry).filter(
            JournalEntry.reference.like(f"%BANK-{transaction.id}%")
        ).all()
        assert len(entries) == 2

        for entry in entries:
            dim_ids = [da.dimension_value_id for da in entry.dimension_assignments]
            # Should have cost_center and department, but not project
            assert test_setup['cost_centers']['branch1'].id in dim_ids
            assert len(dim_ids) == 2

    def test_post_inter_dimensional_transfer(self, db: Session, test_setup):
        """Test posting inter-branch/inter-dimensional transfer"""
        # Create a transfer allocation
        transfer = BankTransferAllocation(
            id="trans-1",
            transfer_type="inter_branch",
            from_bank_account_id=test_setup['bank_accounts']['operating'].id,
            to_bank_account_id=test_setup['bank_accounts']['savings'].id,
            amount=Decimal("10000.00"),
            transfer_date=date.today(),
            from_cost_center_id=test_setup['cost_centers']['branch1'].id,
            to_cost_center_id=test_setup['cost_centers']['branch2'].id,
            gl_debit_entry_id=None,
            gl_credit_entry_id=None,
            status='draft',
            description="Branch funding transfer"
        )
        db.add(transfer)
        db.commit()

        service = BankingService(db)

        # Create GL entries for transfer
        debit_entry = JournalEntry(
            id=f"je-debit-{transfer.id}",
            date=date.today(),
            reference=f"BANK-TRANSFER-{transfer.id}",
            account_id=test_setup['gl_accounts']['bank_savings'].id,
            debit=Decimal("10000.00"),
            credit=Decimal("0.00"),
            description=f"Transfer from {transfer.from_bank_account_id}",
            branch_id=test_setup['branch'].id,
            created_by=test_setup['user'].id
        )
        credit_entry = JournalEntry(
            id=f"je-credit-{transfer.id}",
            date=date.today(),
            reference=f"BANK-TRANSFER-{transfer.id}",
            account_id=test_setup['gl_accounts']['bank'].id,
            debit=Decimal("0.00"),
            credit=Decimal("10000.00"),
            description=f"Transfer to {transfer.to_bank_account_id}",
            branch_id=test_setup['branch'].id,
            created_by=test_setup['user'].id
        )
        db.add_all([debit_entry, credit_entry])
        db.flush()

        # Assign dimensions to from-side
        da_from = AccountingDimensionAssignment(
            id=f"da-from-{uuid4()}",
            journal_entry_id=credit_entry.id,
            dimension_value_id=test_setup['cost_centers']['branch1'].id
        )
        # Assign dimensions to to-side
        da_to = AccountingDimensionAssignment(
            id=f"da-to-{uuid4()}",
            journal_entry_id=debit_entry.id,
            dimension_value_id=test_setup['cost_centers']['branch2'].id
        )
        db.add_all([da_from, da_to])
        db.commit()

        # Verify transfer GL entries exist and are balanced
        entries = db.query(JournalEntry).filter(
            JournalEntry.reference.like(f"%BANK-TRANSFER-{transfer.id}%")
        ).all()
        assert len(entries) == 2
        assert entries[0].debit + entries[1].debit == Decimal("10000.00")
        assert entries[0].credit + entries[1].credit == Decimal("10000.00")

    def test_cannot_post_transaction_twice(self, db: Session, test_setup):
        """Test that double-posting is prevented"""
        transaction = BankTransaction(
            id="txn-dblpost-1",
            transaction_type="deposit",
            amount=Decimal("5000.00"),
            transaction_date=date.today(),
            description="Test deposit",
            bank_account_id=test_setup['bank_accounts']['operating'].id,
            branch_id=test_setup['branch'].id,
            cost_center_id=test_setup['cost_centers']['hq'].id,
            gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
            posting_status='draft'
        )
        db.add(transaction)
        db.commit()

        service = BankingService(db)
        result1 = service.post_bank_transaction_to_accounting(transaction.id)
        assert result1['success'] is True

        # Try to post again - should fail
        with pytest.raises(ValueError, match="already posted"):
            service.post_bank_transaction_to_accounting(transaction.id)

    def test_post_without_required_dimensions(self, db: Session, test_setup):
        """Test that posting requires cost_center dimension"""
        transaction = BankTransaction(
            id="txn-nodim-1",
            transaction_type="deposit",
            amount=Decimal("1000.00"),
            transaction_date=date.today(),
            description="Missing dimension",
            bank_account_id=test_setup['bank_accounts']['operating'].id,
            branch_id=test_setup['branch'].id,
            cost_center_id=None,  # Required dimension missing
            gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
            posting_status='draft'
        )
        db.add(transaction)
        db.commit()

        service = BankingService(db)
        with pytest.raises(ValueError, match="cost_center_id is required"):
            service.post_bank_transaction_to_accounting(transaction.id)


class TestBankingReconciliation:
    """Test GL reconciliation for banking"""

    def test_reconcile_balanced_bank_statement(self, db: Session, test_setup):
        """Test reconciliation when GL equals bank statement"""
        # Create multiple transactions
        period = date.today().strftime("%Y-%m")
        year, month = map(int, period.split('-'))
        start_date = date(year, month, 1)

        transactions = [
            BankTransaction(
                id="txn-rec-1",
                transaction_type="deposit",
                amount=Decimal("10000.00"),
                transaction_date=start_date,
                description="Customer deposit",
                bank_account_id=test_setup['bank_accounts']['operating'].id,
                branch_id=test_setup['branch'].id,
                cost_center_id=test_setup['cost_centers']['hq'].id,
                gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
                posting_status='draft'
            ),
            BankTransaction(
                id="txn-rec-2",
                transaction_type="withdrawal",
                amount=Decimal("3000.00"),
                transaction_date=start_date + timedelta(days=2),
                description="Expense payment",
                bank_account_id=test_setup['bank_accounts']['operating'].id,
                branch_id=test_setup['branch'].id,
                cost_center_id=test_setup['cost_centers']['branch1'].id,
                gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
                posting_status='draft'
            )
        ]
        db.add_all(transactions)
        db.commit()

        # Post all transactions
        service = BankingService(db)
        for txn in transactions:
            service.post_bank_transaction_to_accounting(txn.id)

        # Create reconciliation record
        reconciliation = BankReconciliation(
            id="recon-1",
            bank_account_id=test_setup['bank_accounts']['operating'].id,
            statement_date=start_date + timedelta(days=5),
            statement_balance=Decimal("107000.00"),  # 100000 + 10000 - 3000
            gl_balance=Decimal("107000.00"),
            reconciled_by=test_setup['user'].id,
            reconciliation_date=date.today(),
            status='reconciled'
        )
        db.add(reconciliation)
        db.commit()

        # Run reconciliation
        result = service.reconcile_banking_by_dimension(
            test_setup['bank_accounts']['operating'].id,
            period
        )

        assert result['gl_total'] == 107000.0
        assert result['statement_total'] == 107000.0
        assert result['variance'] == 0.0
        assert result['is_reconciled'] is True

    def test_reconcile_detects_amount_variance(self, db: Session, test_setup):
        """Test reconciliation detects variance in amounts"""
        period = date.today().strftime("%Y-%m")
        year, month = map(int, period.split('-'))
        start_date = date(year, month, 1)

        transaction = BankTransaction(
            id="txn-var-1",
            transaction_type="deposit",
            amount=Decimal("5000.00"),
            transaction_date=start_date,
            description="Deposit",
            bank_account_id=test_setup['bank_accounts']['operating'].id,
            branch_id=test_setup['branch'].id,
            cost_center_id=test_setup['cost_centers']['hq'].id,
            gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
            posting_status='draft'
        )
        db.add(transaction)
        db.commit()

        service = BankingService(db)
        service.post_bank_transaction_to_accounting(transaction.id)

        # Create reconciliation with variance
        reconciliation = BankReconciliation(
            id="recon-var",
            bank_account_id=test_setup['bank_accounts']['operating'].id,
            statement_date=start_date + timedelta(days=5),
            statement_balance=Decimal("105500.00"),  # Should be 105000
            gl_balance=Decimal("105000.00"),
            reconciled_by=test_setup['user'].id,
            reconciliation_date=date.today(),
            status='unreconciled',
            variance_notes="Statement shows higher balance"
        )
        db.add(reconciliation)
        db.commit()

        result = service.reconcile_banking_by_dimension(
            test_setup['bank_accounts']['operating'].id,
            period
        )

        assert result['variance'] == 500.0
        assert result['is_reconciled'] is False

    def test_reconciliation_by_dimension(self, db: Session, test_setup):
        """Test reconciliation includes breakdown by dimension"""
        period = date.today().strftime("%Y-%m")
        year, month = map(int, period.split('-'))
        start_date = date(year, month, 1)

        # Create transactions across multiple dimensions
        txns = [
            BankTransaction(
                id="txn-dim-1",
                transaction_type="deposit",
                amount=Decimal("6000.00"),
                transaction_date=start_date,
                description="HQ deposit",
                bank_account_id=test_setup['bank_accounts']['operating'].id,
                branch_id=test_setup['branch'].id,
                cost_center_id=test_setup['cost_centers']['hq'].id,
                gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
                posting_status='draft'
            ),
            BankTransaction(
                id="txn-dim-2",
                transaction_type="deposit",
                amount=Decimal("4000.00"),
                transaction_date=start_date + timedelta(days=1),
                description="Branch1 deposit",
                bank_account_id=test_setup['bank_accounts']['operating'].id,
                branch_id=test_setup['branch'].id,
                cost_center_id=test_setup['cost_centers']['branch1'].id,
                gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
                posting_status='draft'
            )
        ]
        db.add_all(txns)
        db.commit()

        service = BankingService(db)
        for txn in txns:
            service.post_bank_transaction_to_accounting(txn.id)

        result = service.reconcile_banking_by_dimension(
            test_setup['bank_accounts']['operating'].id,
            period
        )

        # Should have breakdown by dimension
        assert 'by_dimension' in result
        assert result['gl_total'] == 110000.0  # 100000 + 10000

    def test_reconciliation_report_by_department(self, db: Session, test_setup):
        """Test reconciliation report groups by department dimension"""
        period = date.today().strftime("%Y-%m")
        year, month = map(int, period.split('-'))
        start_date = date(year, month, 1)

        txns = [
            BankTransaction(
                id="txn-dept-1",
                transaction_type="withdrawal",
                amount=Decimal("2000.00"),
                transaction_date=start_date,
                description="Treasury expense",
                bank_account_id=test_setup['bank_accounts']['operating'].id,
                branch_id=test_setup['branch'].id,
                cost_center_id=test_setup['cost_centers']['hq'].id,
                department_id=test_setup['departments']['treasury'].id,
                gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
                posting_status='draft'
            ),
            BankTransaction(
                id="txn-dept-2",
                transaction_type="withdrawal",
                amount=Decimal("1000.00"),
                transaction_date=start_date + timedelta(days=2),
                description="Operations expense",
                bank_account_id=test_setup['bank_accounts']['operating'].id,
                branch_id=test_setup['branch'].id,
                cost_center_id=test_setup['cost_centers']['hq'].id,
                department_id=test_setup['departments']['operations'].id,
                gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
                posting_status='draft'
            )
        ]
        db.add_all(txns)
        db.commit()

        service = BankingService(db)
        for txn in txns:
            service.post_bank_transaction_to_accounting(txn.id)

        result = service.reconcile_banking_by_dimension(
            test_setup['bank_accounts']['operating'].id,
            period
        )

        assert 'by_dimension' in result


class TestCashPositionReporting:
    """Test cash position reporting by dimension"""

    def test_cash_position_by_cost_center(self, db: Session, test_setup):
        """Test cash position calculation by cost center"""
        period = date.today().strftime("%Y-%m")
        year, month = map(int, period.split('-'))
        start_date = date(year, month, 1)

        txns = [
            BankTransaction(
                id="txn-pos-1",
                transaction_type="deposit",
                amount=Decimal("20000.00"),
                transaction_date=start_date,
                description="HQ deposit",
                bank_account_id=test_setup['bank_accounts']['operating'].id,
                branch_id=test_setup['branch'].id,
                cost_center_id=test_setup['cost_centers']['hq'].id,
                gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
                posting_status='draft'
            ),
            BankTransaction(
                id="txn-pos-2",
                transaction_type="deposit",
                amount=Decimal("15000.00"),
                transaction_date=start_date + timedelta(days=1),
                description="Branch1 deposit",
                bank_account_id=test_setup['bank_accounts']['operating'].id,
                branch_id=test_setup['branch'].id,
                cost_center_id=test_setup['cost_centers']['branch1'].id,
                gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
                posting_status='draft'
            ),
            BankTransaction(
                id="txn-pos-3",
                transaction_type="deposit",
                amount=Decimal("10000.00"),
                transaction_date=start_date + timedelta(days=2),
                description="Branch2 deposit",
                bank_account_id=test_setup['bank_accounts']['operating'].id,
                branch_id=test_setup['branch'].id,
                cost_center_id=test_setup['cost_centers']['branch2'].id,
                gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
                posting_status='draft'
            )
        ]
        db.add_all(txns)
        db.commit()

        service = BankingService(db)
        for txn in txns:
            service.post_bank_transaction_to_accounting(txn.id)

        result = service.get_cash_position_by_dimension(
            test_setup['bank_accounts']['operating'].id,
            period
        )

        assert result['total_cash'] == 145000.0  # 100000 + 45000
        assert 'by_cost_center' in result
        assert result['by_cost_center'][test_setup['cost_centers']['hq'].id] == 120000.0

    def test_cash_position_includes_pending_transactions(self, db: Session, test_setup):
        """Test cash position includes both posted and pending transactions"""
        transaction = BankTransaction(
            id="txn-pending-1",
            transaction_type="deposit",
            amount=Decimal("5000.00"),
            transaction_date=date.today(),
            description="Pending deposit",
            bank_account_id=test_setup['bank_accounts']['operating'].id,
            branch_id=test_setup['branch'].id,
            cost_center_id=test_setup['cost_centers']['hq'].id,
            gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
            posting_status='pending'
        )
        db.add(transaction)
        db.commit()

        service = BankingService(db)
        result = service.get_cash_position_by_dimension(
            test_setup['bank_accounts']['operating'].id,
            date.today().strftime("%Y-%m")
        )

        # Should include opening balance and pending
        assert result['total_cash'] >= 100000.0


class TestTransferTracking:
    """Test transfer tracking by dimension"""

    def test_track_authorized_transfers(self, db: Session, test_setup):
        """Test tracking of authorized transfers"""
        transfer = BankTransferAllocation(
            id="trans-track-1",
            transfer_type="inter_branch",
            from_bank_account_id=test_setup['bank_accounts']['operating'].id,
            to_bank_account_id=test_setup['bank_accounts']['savings'].id,
            amount=Decimal("25000.00"),
            transfer_date=date.today(),
            from_cost_center_id=test_setup['cost_centers']['hq'].id,
            to_cost_center_id=test_setup['cost_centers']['branch1'].id,
            status='authorized',
            description="Authorized transfer"
        )
        db.add(transfer)
        db.commit()

        service = BankingService(db)
        result = service.track_dimensional_transfers(
            test_setup['bank_accounts']['operating'].id,
            status_filter='authorized'
        )

        assert result['total_authorized'] == 25000.0
        assert len(result['transfers']) >= 1

    def test_transfer_tracking_by_dimension(self, db: Session, test_setup):
        """Test transfers are tracked with dimension information"""
        transfer = BankTransferAllocation(
            id="trans-dim-1",
            transfer_type="inter_branch",
            from_bank_account_id=test_setup['bank_accounts']['operating'].id,
            to_bank_account_id=test_setup['bank_accounts']['savings'].id,
            amount=Decimal("15000.00"),
            transfer_date=date.today(),
            from_cost_center_id=test_setup['cost_centers']['hq'].id,
            from_project_id=test_setup['projects']['operating'].id,
            to_cost_center_id=test_setup['cost_centers']['branch1'].id,
            to_project_id=test_setup['projects']['capital'].id,
            status='pending',
            description="Multi-dimensional transfer"
        )
        db.add(transfer)
        db.commit()

        service = BankingService(db)
        result = service.track_dimensional_transfers(
            test_setup['bank_accounts']['operating'].id
        )

        assert 'by_dimension' in result


class TestDimensionalAnalysis:
    """Test dimensional cash flow analysis and reporting"""

    def test_cash_flow_analysis_calculations(self, db: Session, test_setup):
        """Test cash flow analysis with dimensional calculations"""
        period = date.today().strftime("%Y-%m")
        year, month = map(int, period.split('-'))
        start_date = date(year, month, 1)
        mid_date = start_date + timedelta(days=15)
        end_date = start_date + timedelta(days=28)

        txns = [
            BankTransaction(
                id="txn-cf-1",
                transaction_type="deposit",
                amount=Decimal("30000.00"),
                transaction_date=start_date,
                description="Opening deposit",
                bank_account_id=test_setup['bank_accounts']['operating'].id,
                branch_id=test_setup['branch'].id,
                cost_center_id=test_setup['cost_centers']['hq'].id,
                gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
                posting_status='draft'
            ),
            BankTransaction(
                id="txn-cf-2",
                transaction_type="withdrawal",
                amount=Decimal("10000.00"),
                transaction_date=mid_date,
                description="Mid-period expense",
                bank_account_id=test_setup['bank_accounts']['operating'].id,
                branch_id=test_setup['branch'].id,
                cost_center_id=test_setup['cost_centers']['branch1'].id,
                gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
                posting_status='draft'
            ),
            BankTransaction(
                id="txn-cf-3",
                transaction_type="deposit",
                amount=Decimal("15000.00"),
                transaction_date=end_date,
                description="Month-end deposit",
                bank_account_id=test_setup['bank_accounts']['operating'].id,
                branch_id=test_setup['branch'].id,
                cost_center_id=test_setup['cost_centers']['branch2'].id,
                gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
                posting_status='draft'
            )
        ]
        db.add_all(txns)
        db.commit()

        service = BankingService(db)
        for txn in txns:
            service.post_bank_transaction_to_accounting(txn.id)

        result = service.analyze_cash_flow_by_dimension(
            test_setup['bank_accounts']['operating'].id,
            period
        )

        assert result['total_inflows'] == 145000.0  # 100000 + 45000
        assert result['total_outflows'] == 10000.0
        assert result['net_change'] == 35000.0
        assert 'by_dimension' in result

    def test_dimensional_analysis_by_project(self, db: Session, test_setup):
        """Test dimensional analysis by project dimension"""
        period = date.today().strftime("%Y-%m")
        year, month = map(int, period.split('-'))
        start_date = date(year, month, 1)

        txns = [
            BankTransaction(
                id="txn-proj-1",
                transaction_type="deposit",
                amount=Decimal("20000.00"),
                transaction_date=start_date,
                description="Operating project",
                bank_account_id=test_setup['bank_accounts']['operating'].id,
                branch_id=test_setup['branch'].id,
                cost_center_id=test_setup['cost_centers']['hq'].id,
                project_id=test_setup['projects']['operating'].id,
                gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
                posting_status='draft'
            ),
            BankTransaction(
                id="txn-proj-2",
                transaction_type="deposit",
                amount=Decimal("10000.00"),
                transaction_date=start_date + timedelta(days=5),
                description="Capital project",
                bank_account_id=test_setup['bank_accounts']['operating'].id,
                branch_id=test_setup['branch'].id,
                cost_center_id=test_setup['cost_centers']['hq'].id,
                project_id=test_setup['projects']['capital'].id,
                gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
                posting_status='draft'
            )
        ]
        db.add_all(txns)
        db.commit()

        service = BankingService(db)
        for txn in txns:
            service.post_bank_transaction_to_accounting(txn.id)

        result = service.analyze_cash_flow_by_dimension(
            test_setup['bank_accounts']['operating'].id,
            period,
            dimension_type='project'
        )

        assert result['by_dimension'][test_setup['projects']['operating'].id] >= 20000.0


class TestVarianceReporting:
    """Test variance detection and reporting"""

    def test_variance_report_above_threshold(self, db: Session, test_setup):
        """Test variance report detects variances above threshold"""
        period = date.today().strftime("%Y-%m")
        year, month = map(int, period.split('-'))
        start_date = date(year, month, 1)

        transaction = BankTransaction(
            id="txn-var-threshold",
            transaction_type="deposit",
            amount=Decimal("50000.00"),
            transaction_date=start_date,
            description="Large deposit",
            bank_account_id=test_setup['bank_accounts']['operating'].id,
            branch_id=test_setup['branch'].id,
            cost_center_id=test_setup['cost_centers']['hq'].id,
            gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
            posting_status='draft'
        )
        db.add(transaction)
        db.commit()

        service = BankingService(db)
        service.post_bank_transaction_to_accounting(transaction.id)

        # Create reconciliation with variance above 1% threshold
        reconciliation = BankReconciliation(
            id="recon-var-threshold",
            bank_account_id=test_setup['bank_accounts']['operating'].id,
            statement_date=start_date + timedelta(days=5),
            statement_balance=Decimal("152500.00"),  # Should be 150000, variance = 2500
            gl_balance=Decimal("150000.00"),
            reconciled_by=test_setup['user'].id,
            reconciliation_date=date.today(),
            status='unreconciled'
        )
        db.add(reconciliation)
        db.commit()

        result = service.get_cash_variance_report(
            test_setup['bank_accounts']['operating'].id,
            period,
            variance_threshold=Decimal("1000.00")
        )

        assert result['has_variances'] is True
        assert len(result['variances']) > 0

    def test_variance_report_recommendations(self, db: Session, test_setup):
        """Test variance report includes investigation recommendations"""
        period = date.today().strftime("%Y-%m")
        year, month = map(int, period.split('-'))
        start_date = date(year, month, 1)

        transaction = BankTransaction(
            id="txn-var-rec",
            transaction_type="withdrawal",
            amount=Decimal("75000.00"),
            transaction_date=start_date,
            description="Large expense",
            bank_account_id=test_setup['bank_accounts']['operating'].id,
            branch_id=test_setup['branch'].id,
            cost_center_id=test_setup['cost_centers']['hq'].id,
            gl_bank_account_id=test_setup['gl_accounts']['bank'].id,
            posting_status='draft'
        )
        db.add(transaction)
        db.commit()

        service = BankingService(db)
        service.post_bank_transaction_to_accounting(transaction.id)

        result = service.get_cash_variance_report(
            test_setup['bank_accounts']['operating'].id,
            period
        )

        # Report should have recommendations for high-impact variances
        assert 'recommendations' in result


class TestBankingErrorHandling:
    """Test error handling in banking operations"""

    def test_post_accounting_transaction_not_found(self, db: Session, test_setup):
        """Test posting non-existent transaction returns error"""
        service = BankingService(db)

        with pytest.raises(ValueError, match="not found|does not exist"):
            service.post_bank_transaction_to_accounting("nonexistent-txn-id")

    def test_reconciliation_invalid_period_format(self, db: Session, test_setup):
        """Test reconciliation with invalid period format"""
        service = BankingService(db)

        with pytest.raises(ValueError, match="Invalid period format"):
            service.reconcile_banking_by_dimension(
                test_setup['bank_accounts']['operating'].id,
                "invalid-period"
            )

    def test_analysis_invalid_dimension_type(self, db: Session, test_setup):
        """Test analysis with invalid dimension type"""
        service = BankingService(db)

        with pytest.raises(ValueError, match="Invalid dimension type"):
            service.analyze_cash_flow_by_dimension(
                test_setup['bank_accounts']['operating'].id,
                date.today().strftime("%Y-%m"),
                dimension_type="invalid_type"
            )

    def test_variance_negative_threshold(self, db: Session, test_setup):
        """Test variance report with invalid threshold"""
        service = BankingService(db)

        with pytest.raises(ValueError, match="threshold must be positive"):
            service.get_cash_variance_report(
                test_setup['bank_accounts']['operating'].id,
                date.today().strftime("%Y-%m"),
                variance_threshold=Decimal("-1000.00")
            )

    def test_transfer_invalid_status_filter(self, db: Session, test_setup):
        """Test transfer tracking with invalid status filter"""
        service = BankingService(db)

        with pytest.raises(ValueError, match="Invalid status"):
            service.track_dimensional_transfers(
                test_setup['bank_accounts']['operating'].id,
                status_filter='invalid_status'
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
