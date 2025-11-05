# Phase 2 Quick Reference: Dimensional GL Posting

## What's New

### Models
- **Sale/Invoice:** 8-9 dimensional fields + GL account mappings
- **Purchase/PurchaseOrder:** 8-9 dimensional fields + GL account mappings

### Services
- **SalesService.post_sale_to_accounting()** - Post invoice to GL with dimensions
- **SalesService.reconcile_sales_by_dimension()** - Verify GL matches invoices
- **PurchaseService.post_purchase_to_accounting()** - Post purchase to GL with dimensions
- **PurchaseService.reconcile_purchases_by_dimension()** - Verify GL matches purchases

### API Endpoints (12 total)

#### Sales (6 endpoints)
```
POST   /api/v1/sales/invoices/{invoice_id}/post-accounting
GET    /api/v1/sales/invoices/{invoice_id}/accounting-details
GET    /api/v1/sales/invoices/accounting-bridge
GET    /api/v1/sales/invoices/journal-entries
GET    /api/v1/sales/dimensional-analysis
GET    /api/v1/sales/reconcile?period=2025-01
```

#### Purchases (6 endpoints)
```
POST   /api/v1/purchases/{purchase_id}/post-accounting
GET    /api/v1/purchases/{purchase_id}/accounting-details
GET    /api/v1/purchases/accounting-bridge
GET    /api/v1/purchases/journal-entries
GET    /api/v1/purchases/dimensional-analysis
GET    /api/v1/purchases/reconcile?period=2025-01
```

---

## Usage Examples

### Create Invoice with Dimensions
```python
from app.models.sales import Invoice
from datetime import date

invoice = Invoice(
    id="inv-001",
    invoice_number="INV-2025-001",
    date=date.today(),
    total_amount=1000.00,
    branch_id="branch-1",
    customer_id="cust-1",
    # Dimensional fields
    cost_center_id="cc-001",     # From dimension_values table
    project_id="proj-001",         # From dimension_values table
    department_id="dept-001",      # From dimension_values table
    # GL accounts
    revenue_account_id="4000",     # From accounting_codes table
    ar_account_id="1200",          # From accounting_codes table
    posting_status="draft"
)
db.add(invoice)
db.commit()
```

### Post Invoice to GL
```python
from app.services.sales_service import SalesService

service = SalesService(db)
result = service.post_sale_to_accounting(
    invoice_id="inv-001",
    user_id="user-001"
)

# result = {
#     'success': True,
#     'invoice_id': 'inv-001',
#     'entries_created': 2,  # AR debit + Revenue credit
#     'journal_entry_ids': ['je-1', 'je-2'],
#     'total_amount': 1000.0,
#     'posting_date': '2025-01-15T10:30:45.123Z'
# }
```

### Reconcile Sales by Dimension
```python
result = service.reconcile_sales_by_dimension(period="2025-01")

# result = {
#     'period': '2025-01',
#     'invoice_total': 5000.0,
#     'gl_total': 5000.0,
#     'variance': 0.0,
#     'is_reconciled': True,
#     'by_dimension': [
#         {
#             'dimension_id': 'cc-001',
#             'dimension_name': 'Sales - North',
#             'invoice_amount': 3000.0,
#             'gl_amount': 3000.0,
#             'variance': 0.0
#         },
#         ...
#     ]
# }
```

### Get Dimensional Analysis
```python
# curl GET /api/v1/sales/dimensional-analysis?start_date=2025-01-01&end_date=2025-01-31
response = {
    'total_revenue': 10000.0,
    'by_cost_center': {
        'Sales - North': 6000.0,
        'Sales - South': 4000.0
    },
    'by_project': {
        'Project Alpha': 5500.0,
        'Project Beta': 4500.0
    },
    'by_department': {
        'Engineering': 7000.0,
        'Operations': 3000.0
    }
}
```

### Same Pattern for Purchases
```python
from app.services.purchase_service import PurchaseService

service = PurchaseService(db)

# Post purchase
result = service.post_purchase_to_accounting(
    purchase_id="purch-001",
    user_id="user-001"
)

# Reconcile
result = service.reconcile_purchases_by_dimension(period="2025-01")
```

---

## GL Entry Structure

### Sales Posting
**Invoice $1,000 with dimensions:**
```
GL Entry 1 (AR Debit):
  Account: 1200 (Accounts Receivable)
  Debit: $1,000
  Credit: $0
  Dimensions: CC-001, Project-001, Dept-001
  Source: SALES
  Reference: SALES-inv-001-AR

GL Entry 2 (Revenue Credit):
  Account: 4000 (Sales Revenue)
  Debit: $0
  Credit: $1,000
  Dimensions: CC-001, Project-001, Dept-001
  Source: SALES
  Reference: SALES-inv-001-REV

Total: Debit $1,000 = Credit $1,000 ✓
```

### Purchase Posting
**Purchase $5,000 with dimensions:**
```
GL Entry 1 (Expense Debit):
  Account: 5000 (COGS)
  Debit: $5,000
  Credit: $0
  Dimensions: CC-001, Project-001
  Source: PURCHASES
  Reference: PURCHASE-purch-001-EXP

GL Entry 2 (AP Credit):
  Account: 2100 (Accounts Payable)
  Debit: $0
  Credit: $5,000
  Dimensions: CC-001, Project-001
  Source: PURCHASES
  Reference: PURCHASE-purch-001-AP

Total: Debit $5,000 = Credit $5,000 ✓
```

---

## Database Migrations

### Run Sales Migration
```bash
python migrations/add_accounting_dimensions_to_sales.py
```

**Columns Added:**
- sales: cost_center_id, project_id, department_id, revenue_account_id, posting_status, last_posted_date, posted_by
- invoices: cost_center_id, project_id, department_id, revenue_account_id, ar_account_id, posting_status, last_posted_date, posted_by

**Indexes Created:**
- idx_sales_cost_center_id
- idx_sales_posting_status
- idx_invoices_cost_center_id
- idx_invoices_posting_status

### Run Purchases Migration
```bash
python migrations/add_accounting_dimensions_to_purchases.py
```

**Columns Added:**
- purchases: cost_center_id, project_id, department_id, expense_account_id, payable_account_id, posting_status, last_posted_date, posted_by
- purchase_orders: cost_center_id, project_id, department_id, expense_account_id, posting_status

**Indexes Created:**
- idx_purchases_cost_center_id
- idx_purchases_posting_status
- idx_purchase_orders_cost_center_id
- idx_purchase_orders_posting_status

---

## Testing

### Run Test Suite
```bash
pytest app/tests/test_gl_posting_phase2.py -v

# Expected output:
# test_post_invoice_with_all_dimensions PASSED
# test_post_invoice_partial_dimensions PASSED
# test_cannot_post_invoice_twice PASSED
# test_reconcile_sales_by_dimension PASSED
# test_post_purchase_with_all_dimensions PASSED
# test_reconcile_purchases_by_dimension PASSED
# test_posting_without_gl_accounts PASSED
# test_reconciliation_with_missing_dimension_assignments PASSED
```

---

## Common Issues & Solutions

### ❌ GL posting fails: "GL accounts must be set"
**Solution:** Ensure both invoice.revenue_account_id and invoice.ar_account_id are set before posting
```python
invoice.revenue_account_id = "4000"  # Required
invoice.ar_account_id = "1200"       # Required
```

### ❌ Reconciliation shows variance
**Possible Causes:**
1. Invoice not posted to GL (posting_status still 'draft')
2. Dimension IDs don't match (typo in dimension_value_id)
3. GL entries have different dimensions than invoice

**Solution:** Verify all invoices in period have posting_status='posted' and dimensions assigned

### ❌ API endpoint returns 404
**Solution:** Verify:
1. Invoice/Purchase exists: `db.query(Invoice).filter(Invoice.id == invoice_id).first()`
2. GL accounts exist: `db.query(AccountingCode).filter(AccountingCode.id == account_id).first()`
3. Dimensions exist: `db.query(DimensionValue).filter(DimensionValue.id == dim_id).first()`

### ❌ Double-posting error
**This is expected behavior** - posting_status prevents re-posting
```python
# This will fail (prevents accidental double-posting):
service.post_sale_to_accounting(invoice_id)
service.post_sale_to_accounting(invoice_id)  # ValueError!

# To post again, reset status:
invoice.posting_status = 'draft'
db.commit()
service.post_sale_to_accounting(invoice_id)  # OK
```

---

## Related Documentation

- **docs/PHASE2_IMPLEMENTATION_SUMMARY.md** - Complete implementation details
- **docs/PHASE2_DEPLOYMENT_GUIDE.md** - Step-by-step deployment procedures
- **docs/ENTERPRISE_READINESS_ROADMAP.md** - 12-week roadmap for all 8 modules
- **docs/HOW_TO_IMPLEMENT.md** - Dimensional accounting implementation guide

---

## Key Metrics

| Metric | Value |
|--------|-------|
| New Models Enhanced | 4 |
| New Service Methods | 4 |
| New API Endpoints | 12 |
| Database Migrations | 2 |
| Test Cases | 10+ |
| Lines of Code Added | ~2,300 |
| GL Entries per Transaction | 2 |
| Reconciliation Variance Threshold | < 0.01 |

---

## Deployment Checklist

- [ ] Run database migrations (sales, purchases)
- [ ] Verify column additions: `ALTER TABLE sales COLUMN list`
- [ ] Run test suite: `pytest app/tests/test_gl_posting_phase2.py -v`
- [ ] Smoke test: Create invoice with dimensions and post to GL
- [ ] Verify reconciliation: Check variance < 0.01
- [ ] Check logs for errors
- [ ] Monitor performance (GL posting should complete in < 500ms)

---

**Ready to use!** Phase 2 is production-ready after passing smoke tests.
