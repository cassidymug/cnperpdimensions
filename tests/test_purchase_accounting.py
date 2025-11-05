import uuid
from decimal import Decimal
from datetime import date

from app.core.database import get_db
from app.services.ifrs_accounting_service import IFRSAccountingService
from app.models.purchases import Purchase, PurchaseItem, Supplier
from app.models.inventory import Product
from app.models.branch import Branch
from app.models.accounting import JournalEntry, AccountingCode


def get_or_fail(query, name):
    obj = query.first()
    assert obj, f"Missing required object: {name}"
    return obj


def test_purchase_and_payment_flow():
    db = next(get_db())

    supplier = get_or_fail(db.query(Supplier), 'supplier')
    product = get_or_fail(db.query(Product), 'product')
    branch = get_or_fail(db.query(Branch).filter(Branch.active == True), 'active branch')

    purchase = Purchase(
        id=str(uuid.uuid4()),
        purchase_date=date.today(),
        supplier_id=supplier.id,
        total_amount=Decimal('1000.00'),
        total_vat_amount=Decimal('150.00'),
        total_amount_ex_vat=Decimal('850.00'),
        amount_paid=Decimal('0.00'),  # start unpaid
        status='pending',
        branch_id=branch.id
    )
    db.add(purchase)
    db.flush()

    item = PurchaseItem(
        id=str(uuid.uuid4()),
        product_id=product.id,
        quantity=Decimal('10'),
        cost=Decimal('85'),
        total_cost=Decimal('850.00'),
        vat_amount=Decimal('150.00'),
        vat_rate=Decimal('15'),
        purchase_id=purchase.id,
        is_inventory=True
    )
    db.add(item)
    db.commit()
    db.refresh(purchase)

    svc = IFRSAccountingService(db)

    # Main purchase journals
    jes_main = svc.create_purchase_journal_entries(purchase)
    assert sum(j.debit_amount for j in jes_main) == sum(j.credit_amount for j in jes_main)

    # Verify AP credit present
    ap_line = next((j for j in jes_main if j.credit_amount == Decimal('1000.00')), None)
    assert ap_line, 'AP credit line missing'

    # Record full payment now
    jes_pay = svc.create_purchase_payment_journal_entries(purchase, Decimal('1000.00'), date.today())
    assert sum(j.debit_amount for j in jes_pay) == sum(j.credit_amount for j in jes_pay)
    ap_debit = next((j for j in jes_pay if j.debit_amount == Decimal('1000.00')), None)
    assert ap_debit, 'AP debit (payment) missing'

    # Sanity: inventory + VAT debits
    inv_debit = next((j for j in jes_main if j.debit_amount == Decimal('850.00')), None)
    vat_debit = next((j for j in jes_main if j.debit_amount == Decimal('150.00')), None)
    assert inv_debit and vat_debit, 'Expected inventory and VAT debits missing'

    # Optional: ensure no dangling imbalance
    total_debits = sum(j.debit_amount for j in db.query(JournalEntry).all())
    total_credits = sum(j.credit_amount for j in db.query(JournalEntry).all())
    assert round(total_debits,2) == round(total_credits,2), 'Global journals imbalance'
