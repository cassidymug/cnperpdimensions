import uuid
from decimal import Decimal
from datetime import date
from app.core.database import get_db
from app.services.ifrs_accounting_service import IFRSAccountingService
from app.models.purchases import Purchase, PurchaseItem, Supplier
from app.models.inventory import Product
from app.models.branch import Branch
from app.models.accounting import JournalEntry, AccountingCode


def _req(obj, name):
    assert obj is not None, f"Required {name} missing"
    return obj


def _ap_net_balance(db) -> Decimal:
    ap_code = db.query(AccountingCode).filter(AccountingCode.name.ilike('%Accounts Payable%')).first()
    if not ap_code:
        return Decimal('0')
    ap_journals = db.query(JournalEntry).filter(JournalEntry.accounting_code_id == ap_code.id).all()
    return sum((j.credit_amount - j.debit_amount) for j in ap_journals)


def _create_purchase(db, supplier, branch, product, total_ex_vat, vat_amount, amount_paid=Decimal('0'), status='pending'):
    total = total_ex_vat + vat_amount
    p = Purchase(
        id=str(uuid.uuid4()),
        purchase_date=date.today(),
        supplier_id=supplier.id,
        total_amount=total,
        total_vat_amount=vat_amount,
        total_amount_ex_vat=total_ex_vat,
        amount_paid=amount_paid,
        status=status,
        branch_id=branch.id
    )
    db.add(p)
    db.flush()
    item = PurchaseItem(
        id=str(uuid.uuid4()),
        product_id=product.id,
        quantity=Decimal('10'),
        cost=total_ex_vat / Decimal('10'),
        total_cost=total_ex_vat,
        vat_amount=vat_amount,
        vat_rate=(vat_amount / total_ex_vat * 100) if total_ex_vat > 0 else Decimal('0'),
        purchase_id=p.id,
        is_inventory=True
    )
    db.add(item)
    db.commit()
    db.refresh(p)
    return p


def test_multi_branch_isolation():
    db = next(get_db())
    branches = db.query(Branch).filter(Branch.active == True).all()
    if len(branches) < 2:
        # Skip if only one branch configured
        return
    supplier = _req(db.query(Supplier).first(), 'supplier')
    product = _req(db.query(Product).first(), 'product')
    svc = IFRSAccountingService(db)

    p1 = _create_purchase(db, supplier, branches[0], product, Decimal('500'), Decimal('75'))
    p2 = _create_purchase(db, supplier, branches[1], product, Decimal('800'), Decimal('120'))

    j1 = svc.create_purchase_journal_entries(p1)
    j2 = svc.create_purchase_journal_entries(p2)

    b1_codes = {je.accounting_entry.branch_id for je in j1}
    b2_codes = {je.accounting_entry.branch_id for je in j2}
    assert b1_codes == {branches[0].id}
    assert b2_codes == {branches[1].id}


def test_partial_payments():
    db = next(get_db())
    supplier = _req(db.query(Supplier).first(), 'supplier')
    product = _req(db.query(Product).first(), 'product')
    branch = _req(db.query(Branch).filter(Branch.active == True).first(), 'branch')
    svc = IFRSAccountingService(db)

    baseline_net = _ap_net_balance(db)
    purchase = _create_purchase(db, supplier, branch, product, Decimal('600'), Decimal('90'))
    # Initial journals (unpaid)
    svc.create_purchase_journal_entries(purchase)

    # First partial payment 300
    svc.create_purchase_payment_journal_entries(purchase, Decimal('300'), date.today())
    # Second partial payment 390 (remaining)
    svc.create_purchase_payment_journal_entries(purchase, Decimal('390'), date.today())

    # Sum AP movements: AP credited 690, debited 690 total
    net_ap = _ap_net_balance(db) - baseline_net
    assert round(net_ap,2) >= -0.01 and round(net_ap,2) <= 0.01, f"AP not cleared: {net_ap}"


def test_vat_zero_purchase():
    db = next(get_db())
    supplier = _req(db.query(Supplier).first(), 'supplier')
    product = _req(db.query(Product).first(), 'product')
    branch = _req(db.query(Branch).filter(Branch.active == True).first(), 'branch')
    svc = IFRSAccountingService(db)

    purchase = _create_purchase(db, supplier, branch, product, Decimal('400'), Decimal('0'))
    jes = svc.create_purchase_journal_entries(purchase)

    # Ensure exactly 2 lines (inventory debit + AP credit) when VAT zero
    assert len(jes) == 2, f"Expected 2 journal lines for zero VAT, got {len(jes)}"
    assert any(j.debit_amount == Decimal('400') for j in jes)
    assert any(j.credit_amount == Decimal('400') for j in jes)
    assert not any(j.debit_amount == Decimal('0') and j.credit_amount == Decimal('0') for j in jes)


def test_ifrs_tag_coverage():
    db = next(get_db())
    # Core accounts expected to have tags
    required = {
        'Inventory': 'A1.3',
        'Cash': 'A1.1',
        'Petty Cash': 'A1.1',
        'Accounts Payable': 'L1.1',
        'VAT Receivable': 'A1.2'
    }
    missing = []
    for name, tag in required.items():
        code = db.query(AccountingCode).filter(AccountingCode.name.ilike(f"%{name}%")).first()
        if not code or not code.reporting_tag:
            missing.append(name)
    assert not missing, f"Missing IFRS tags for: {', '.join(missing)}"
