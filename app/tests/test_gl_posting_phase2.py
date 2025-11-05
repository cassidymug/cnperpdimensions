"""
Comprehensive Test Suite for Dimensional Accounting GL Posting

Tests for Sales, Purchases, and dimensional reconciliation.
Validates that GL entries are created with correct dimensions and amounts.

Run with:
    pytest app/tests/test_gl_posting_phase2.py -v
"""
import pytest
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.core.database import engine, SessionLocal
from app.models.sales import Sale, Invoice, Customer
from app.models.purchases import Purchase, Supplier
from app.models.accounting import JournalEntry, AccountingCode, AccountingEntry
from app.models.accounting_dimensions import AccountingDimensionValue, AccountingDimensionAssignment
from app.models.branch import Branch
from app.models.user import User
from app.services.sales_service import SalesService
from app.services.purchase_service import PurchaseService


@pytest.fixture
def db():
    """Create a test database session"""
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def test_setup(db: Session):
    """Setup common test data"""
    # Create test branch
    branch = Branch(
        id="test-branch-1",
        name="Test Branch",
        branch_number="001",
        country="US",
        state="CA",
        town="Test Town"
    )
    db.add(branch)
    db.flush()

    # Create test user
    user = User(
        id="test-user-1",
        username="testuser",
        email="test@example.com"
    )
    db.add(user)
    db.flush()

    # Create dimension values (cost centers)
    cc1 = AccountingDimensionValue(
        id="cc-1",
        dimension_id="dim-cc",
        code="CC001",
        name="Sales - North",
        hierarchy_level=1,
        parent_value_id=None
    )
    cc2 = AccountingDimensionValue(
        id="cc-2",
        dimension_id="dim-cc",
        code="CC002",
        name="Sales - South",
        hierarchy_level=1,
        parent_value_id=None
    )
    db.add_all([cc1, cc2])
    db.flush()

    # Create projects
    proj1 = AccountingDimensionValue(
        id="proj-1",
        dimension_id="dim-proj",
        code="PROJ001",
        name="Project Alpha",
        hierarchy_level=1,
        parent_value_id=None
    )
    proj2 = AccountingDimensionValue(
        id="proj-2",
        dimension_id="dim-proj",
        code="PROJ002",
        name="Project Beta",
        hierarchy_level=1,
        parent_value_id=None
    )
    db.add_all([proj1, proj2])
    db.flush()

    # Create departments
    dept1 = AccountingDimensionValue(
        id="dept-1",
        dimension_id="dim-dept",
        code="DEPT001",
        name="Engineering",
        hierarchy_level=1,
        parent_value_id=None
    )
    db.add(dept1)
    db.flush()

    # Create GL accounts
    ar_account = AccountingCode(
        id="ar-1",
        code="1200",
        name="Accounts Receivable",
        account_type="Asset",
        account_class="Current Assets"
    )
    revenue_account = AccountingCode(
        id="rev-1",
        code="4000",
        name="Sales Revenue",
        account_type="Revenue",
        account_class="Operating Revenue"
    )
    exp_account = AccountingCode(
        id="exp-1",
        code="5000",
        name="Cost of Goods Sold",
        account_type="Expense",
        account_class="Cost of Goods Sold"
    )
    ap_account = AccountingCode(
        id="ap-1",
        code="2100",
        name="Accounts Payable",
        account_type="Liability",
        account_class="Current Liabilities"
    )
    offset_account = AccountingCode(
        id="offset-1",
        code="9999",
        name="Temporary Offset",
        account_type="Liability",
        account_class="Temporary"
    )
    db.add_all([ar_account, revenue_account, exp_account, ap_account, offset_account])
    db.flush()

    # Create test customer
    customer = Customer(
        id="cust-1",
        name="Test Customer",
        branch_id=branch.id,
        customer_type="retail"
    )
    db.add(customer)
    db.flush()

    # Create test supplier
    supplier = Supplier(
        id="supp-1",
        name="Test Supplier",
        branch_id=branch.id,
        is_active=True
    )
    db.add(supplier)
    db.flush()

    db.commit()

    return {
        'branch': branch,
        'user': user,
        'cost_centers': [cc1, cc2],
        'projects': [proj1, proj2],
        'departments': [dept1],
        'gl_accounts': {
            'ar': ar_account,
            'revenue': revenue_account,
            'expense': exp_account,
            'ap': ap_account,
            'offset': offset_account
        },
        'customer': customer,
        'supplier': supplier
    }


class TestSalesGLPosting:
    """Test GL posting for sales/invoices"""

    def test_post_invoice_with_all_dimensions(self, db: Session, test_setup):
        """Test posting invoice with all dimensions assigned"""
        # Create invoice with dimensions
        invoice = Invoice(
            id="inv-1",
            invoice_number="INV-001",
            date=date.today(),
            total_amount=Decimal("1000.00"),
            branch_id=test_setup['branch'].id,
            customer_id=test_setup['customer'].id,
            cost_center_id=test_setup['cost_centers'][0].id,
            project_id=test_setup['projects'][0].id,
            department_id=test_setup['departments'][0].id,
            revenue_account_id=test_setup['gl_accounts']['revenue'].id,
            ar_account_id=test_setup['gl_accounts']['ar'].id,
            posting_status='draft'
        )
        db.add(invoice)
        db.commit()

        # Post to accounting
        service = SalesService(db)
        result = service.post_sale_to_accounting(invoice.id, test_setup['user'].id)

        # Verify posting was successful
        assert result['success'] is True
        assert result['invoice_id'] == invoice.id
        assert result['entries_created'] == 2  # AR debit + Revenue credit

        # Verify journal entries were created
        entries = db.query(JournalEntry).filter(
            JournalEntry.reference.like(f"%SALES-{invoice.id}%")
        ).all()
        assert len(entries) == 2

        # Verify dimensions are preserved in GL entries
        for entry in entries:
            assert len(entry.dimension_assignments) > 0
            dim_ids = [da.dimension_value_id for da in entry.dimension_assignments]
            assert test_setup['cost_centers'][0].id in dim_ids
            assert test_setup['projects'][0].id in dim_ids
            assert test_setup['departments'][0].id in dim_ids

        # Verify invoice posting status updated
        updated_invoice = db.query(Invoice).filter(Invoice.id == invoice.id).first()
        assert updated_invoice.posting_status == 'posted'
        assert updated_invoice.posted_by == test_setup['user'].id
        assert updated_invoice.last_posted_date is not None

    def test_post_invoice_partial_dimensions(self, db: Session, test_setup):
        """Test posting invoice with only some dimensions"""
        invoice = Invoice(
            id="inv-2",
            invoice_number="INV-002",
            date=date.today(),
            total_amount=Decimal("500.00"),
            branch_id=test_setup['branch'].id,
            customer_id=test_setup['customer'].id,
            cost_center_id=test_setup['cost_centers'][0].id,
            project_id=None,  # No project
            department_id=None,  # No department
            revenue_account_id=test_setup['gl_accounts']['revenue'].id,
            ar_account_id=test_setup['gl_accounts']['ar'].id,
            posting_status='draft'
        )
        db.add(invoice)
        db.commit()

        service = SalesService(db)
        result = service.post_sale_to_accounting(invoice.id)

        assert result['success'] is True
        assert result['total_amount'] == 500.0

        # Verify dimensions assigned are only cost_center
        entries = db.query(JournalEntry).filter(
            JournalEntry.reference.like(f"%SALES-{invoice.id}%")
        ).all()
        for entry in entries:
            dim_ids = [da.dimension_value_id for da in entry.dimension_assignments]
            assert test_setup['cost_centers'][0].id in dim_ids
            # No project or department should be assigned
            assert len(dim_ids) == 1

    def test_cannot_post_invoice_twice(self, db: Session, test_setup):
        """Test that double-posting is prevented"""
        invoice = Invoice(
            id="inv-3",
            invoice_number="INV-003",
            date=date.today(),
            total_amount=Decimal("750.00"),
            branch_id=test_setup['branch'].id,
            customer_id=test_setup['customer'].id,
            cost_center_id=test_setup['cost_centers'][0].id,
            revenue_account_id=test_setup['gl_accounts']['revenue'].id,
            ar_account_id=test_setup['gl_accounts']['ar'].id,
            posting_status='draft'
        )
        db.add(invoice)
        db.commit()

        service = SalesService(db)
        result1 = service.post_sale_to_accounting(invoice.id)
        assert result1['success'] is True

        # Try to post again - should fail
        with pytest.raises(ValueError, match="already posted"):
            service.post_sale_to_accounting(invoice.id)

    def test_reconcile_sales_by_dimension(self, db: Session, test_setup):
        """Test sales reconciliation by dimension"""
        # Create multiple invoices with different dimensions
        period = date.today().strftime("%Y-%m")
        year, month = map(int, period.split('-'))
        start_date = date(year, month, 1)
        end_date = date(year, month, 28)

        invoices = [
            Invoice(
                id="inv-rec-1",
                invoice_number="INV-REC-001",
                date=start_date,
                total_amount=Decimal("1000.00"),
                branch_id=test_setup['branch'].id,
                customer_id=test_setup['customer'].id,
                cost_center_id=test_setup['cost_centers'][0].id,
                revenue_account_id=test_setup['gl_accounts']['revenue'].id,
                ar_account_id=test_setup['gl_accounts']['ar'].id,
                posting_status='draft'
            ),
            Invoice(
                id="inv-rec-2",
                invoice_number="INV-REC-002",
                date=start_date + timedelta(days=5),
                total_amount=Decimal("2000.00"),
                branch_id=test_setup['branch'].id,
                customer_id=test_setup['customer'].id,
                cost_center_id=test_setup['cost_centers'][1].id,
                revenue_account_id=test_setup['gl_accounts']['revenue'].id,
                ar_account_id=test_setup['gl_accounts']['ar'].id,
                posting_status='draft'
            )
        ]
        db.add_all(invoices)
        db.commit()

        # Post both invoices
        service = SalesService(db)
        for invoice in invoices:
            service.post_sale_to_accounting(invoice.id)

        # Run reconciliation
        result = service.reconcile_sales_by_dimension(period)

        assert result['invoice_total'] == 3000.0
        assert result['gl_total'] == 3000.0
        assert result['variance'] < 0.01
        assert result['is_reconciled'] is True
        assert len(result['by_dimension']) > 0


class TestPurchaseGLPosting:
    """Test GL posting for purchases"""

    def test_post_purchase_with_all_dimensions(self, db: Session, test_setup):
        """Test posting purchase with all dimensions assigned"""
        purchase = Purchase(
            id="purch-1",
            purchase_date=date.today(),
            total_amount=Decimal("5000.00"),
            branch_id=test_setup['branch'].id,
            supplier_id=test_setup['supplier'].id,
            cost_center_id=test_setup['cost_centers'][0].id,
            project_id=test_setup['projects'][0].id,
            department_id=test_setup['departments'][0].id,
            expense_account_id=test_setup['gl_accounts']['expense'].id,
            payable_account_id=test_setup['gl_accounts']['ap'].id,
            posting_status='draft'
        )
        db.add(purchase)
        db.commit()

        service = PurchaseService(db)
        result = service.post_purchase_to_accounting(purchase.id, test_setup['user'].id)

        assert result['success'] is True
        assert result['purchase_id'] == purchase.id
        assert result['entries_created'] == 2  # Expense debit + AP credit

        # Verify dimensions in GL entries
        entries = db.query(JournalEntry).filter(
            JournalEntry.reference.like(f"%PURCHASE-{purchase.id}%")
        ).all()
        assert len(entries) == 2

        for entry in entries:
            dim_ids = [da.dimension_value_id for da in entry.dimension_assignments]
            assert test_setup['cost_centers'][0].id in dim_ids

    def test_reconcile_purchases_by_dimension(self, db: Session, test_setup):
        """Test purchase reconciliation by dimension"""
        period = date.today().strftime("%Y-%m")
        year, month = map(int, period.split('-'))
        start_date = date(year, month, 1)

        purchases = [
            Purchase(
                id="purch-rec-1",
                purchase_date=start_date,
                total_amount=Decimal("3000.00"),
                branch_id=test_setup['branch'].id,
                supplier_id=test_setup['supplier'].id,
                cost_center_id=test_setup['cost_centers'][0].id,
                expense_account_id=test_setup['gl_accounts']['expense'].id,
                payable_account_id=test_setup['gl_accounts']['ap'].id,
                posting_status='draft'
            ),
            Purchase(
                id="purch-rec-2",
                purchase_date=start_date + timedelta(days=3),
                total_amount=Decimal("2000.00"),
                branch_id=test_setup['branch'].id,
                supplier_id=test_setup['supplier'].id,
                cost_center_id=test_setup['cost_centers'][1].id,
                expense_account_id=test_setup['gl_accounts']['expense'].id,
                payable_account_id=test_setup['gl_accounts']['ap'].id,
                posting_status='draft'
            )
        ]
        db.add_all(purchases)
        db.commit()

        service = PurchaseService(db)
        for purchase in purchases:
            service.post_purchase_to_accounting(purchase.id)

        result = service.reconcile_purchases_by_dimension(period)

        assert result['purchase_total'] == 5000.0
        assert result['gl_total'] == 5000.0
        assert result['variance'] < 0.01
        assert result['is_reconciled'] is True


class TestGLPostingEdgeCases:
    """Test edge cases in GL posting"""

    def test_posting_without_gl_accounts(self, db: Session, test_setup):
        """Test that posting fails without required GL accounts"""
        invoice = Invoice(
            id="inv-edge-1",
            invoice_number="INV-EDGE-001",
            date=date.today(),
            total_amount=Decimal("100.00"),
            branch_id=test_setup['branch'].id,
            customer_id=test_setup['customer'].id,
            cost_center_id=test_setup['cost_centers'][0].id,
            revenue_account_id=None,  # Missing
            ar_account_id=test_setup['gl_accounts']['ar'].id,
            posting_status='draft'
        )
        db.add(invoice)
        db.commit()

        service = SalesService(db)
        with pytest.raises(ValueError, match="GL accounts must be set"):
            service.post_sale_to_accounting(invoice.id)

    def test_reconciliation_with_missing_dimension_assignments(self, db: Session, test_setup):
        """Test reconciliation handles invoices without all dimensions"""
        period = date.today().strftime("%Y-%m")
        year, month = map(int, period.split('-'))
        start_date = date(year, month, 1)

        # Invoice without dimensions
        invoice = Invoice(
            id="inv-nodim-1",
            invoice_number="INV-NODIM-001",
            date=start_date,
            total_amount=Decimal("500.00"),
            branch_id=test_setup['branch'].id,
            customer_id=test_setup['customer'].id,
            cost_center_id=None,
            project_id=None,
            department_id=None,
            revenue_account_id=test_setup['gl_accounts']['revenue'].id,
            ar_account_id=test_setup['gl_accounts']['ar'].id,
            posting_status='draft'
        )
        db.add(invoice)
        db.commit()

        service = SalesService(db)
        service.post_sale_to_accounting(invoice.id)

        # Reconciliation should still work
        result = service.reconcile_sales_by_dimension(period)
        assert result['invoice_total'] == 500.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
