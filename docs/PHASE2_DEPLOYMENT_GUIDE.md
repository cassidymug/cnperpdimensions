# Phase 2 Deployment Guide: Sales & Purchases Dimensional Accounting

## Overview

Phase 2 implementation adds dimensional accounting to the Sales and Purchases modules, enabling cost center, project, and department-based GL posting and reconciliation.

**Scope:**
- 4 model enhancements (Sale, Invoice, Purchase, PurchaseOrder)
- 2 service layer implementations (SalesService, PurchaseService)
- 12 new API endpoints (6 for Sales, 6 for Purchases)
- 2 idempotent database migrations
- Comprehensive test suite

**Status:** ✅ Ready for deployment

---

## Pre-Deployment Checklist

### Code Quality
- [ ] All 12 new API endpoints documented with request/response schemas
- [ ] Service layer methods follow manufacturing pattern (post_to_accounting + reconcile_by_dimension)
- [ ] GL posting creates balanced entries (Debit == Credit)
- [ ] Dimension assignments applied to all GL entries
- [ ] Reconciliation compares transaction totals to GL by dimension

### Database
- [ ] Migration scripts are idempotent (safe to re-run)
- [ ] Foreign key constraints reference correct tables
- [ ] Indexes created for performance (cost_center_id, posting_status)
- [ ] No breaking changes to existing schema

### Testing
- [ ] Unit tests for GL posting logic (test_gl_posting_phase2.py)
- [ ] Integration tests for dimension preservation
- [ ] Edge case tests (partial dimensions, double-posting prevention)
- [ ] Reconciliation variance testing

### Documentation
- [ ] API endpoint documentation complete
- [ ] Migration scripts documented with purpose
- [ ] Service method contracts documented
- [ ] Dimensional flow documented

---

## Deployment Steps

### Step 1: Backup Database

```bash
# Create full backup before deployment
python -c "from app.services.backup_service import BackupService; from app.core.database import SessionLocal; db = SessionLocal(); BackupService(db).create_backup('pre-phase2-deployment'); db.close()"
```

### Step 2: Run Database Migrations

**Sales Module Migration:**
```bash
# Add dimensional columns to sales and invoices tables
python migrations/add_accounting_dimensions_to_sales.py
```

Expected output:
```
✅ All columns added successfully
✅ All indexes created successfully
🎉 Sales dimensional accounting migration completed!
```

**Purchases Module Migration:**
```bash
# Add dimensional columns to purchases and purchase_orders tables
python migrations/add_accounting_dimensions_to_purchases.py
```

Expected output:
```
✅ All columns added successfully
✅ All indexes created successfully
🎉 Purchases dimensional accounting migration completed!
```

### Step 3: Verify Database Changes

```bash
# Verify sales columns added
python -c "
from app.core.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    cols = conn.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name='sales' ORDER BY column_name\")).fetchall()
    print('Sales columns:', [c[0] for c in cols])
"

# Verify purchases columns added
python -c "
from app.core.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    cols = conn.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name='purchases' ORDER BY column_name\")).fetchall()
    print('Purchases columns:', [c[0] for c in cols])
"
```

### Step 4: Run Unit Tests

```bash
# Run comprehensive test suite
pytest app/tests/test_gl_posting_phase2.py -v

# Expected: All tests pass (≥ 10 test cases)
# - Test GL posting with all dimensions
# - Test GL posting with partial dimensions
# - Test posting prevention (can't post twice)
# - Test reconciliation accuracy
# - Test edge cases
```

### Step 5: Smoke Tests on Staging

**Test 1: Create and Post Invoice**
```bash
# Create test invoice with dimensions
curl -X POST http://localhost:8010/api/v1/sales/invoices \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "test-customer-id",
    "date": "2025-01-15",
    "total_amount": 1000.00,
    "cost_center_id": "cc-001",
    "project_id": "proj-001",
    "revenue_account_id": "4000",
    "ar_account_id": "1200"
  }'

# Response should have invoice_id in body

# Post to accounting
curl -X POST http://localhost:8010/api/v1/sales/invoices/{invoice_id}/post-accounting \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user-001"}'

# Response should include:
# - success: true
# - entries_created: 2
# - journal_entry_ids: [...]
```

**Test 2: Verify GL Entries**
```bash
# Get journal entries for the invoice
curl -X GET "http://localhost:8010/api/v1/sales/journal-entries?source=SALES&start_date=2025-01-15&end_date=2025-01-15" \
  -H "Content-Type: application/json"

# Response should show:
# - 2 GL entries (AR Debit + Revenue Credit)
# - Both entries have identical total amount
# - Both entries have dimension assignments
# - source = "SALES"
```

**Test 3: Verify Accounting Details**
```bash
# Get accounting details for invoice
curl -X GET http://localhost:8010/api/v1/sales/invoices/{invoice_id}/accounting-details

# Response should include:
# - cost_center: "CC-001"
# - project: "PROJECT-001"
# - posting_status: "posted"
# - revenue_account: "4000"
# - ar_account: "1200"
```

**Test 4: Test Reconciliation**
```bash
# Run reconciliation for current period
curl -X GET "http://localhost:8010/api/v1/sales/reconcile?period=2025-01" \
  -H "Content-Type: application/json"

# Response should show:
# - invoice_total: 1000.00
# - gl_total: 1000.00
# - variance: 0.00
# - is_reconciled: true
# - by_dimension: [...]
```

**Test 5: Dimensional Analysis**
```bash
# Get revenue by dimension
curl -X GET "http://localhost:8010/api/v1/sales/dimensional-analysis?start_date=2025-01-01&end_date=2025-01-31"

# Response should show:
# - total_revenue: 1000.00
# - by_cost_center: {"CC-001": 1000.00}
# - by_project: {"PROJECT-001": 1000.00}
```

**Test 6: Same tests for Purchases**
```bash
# Create purchase with dimensions
curl -X POST http://localhost:8010/api/v1/purchases \
  -H "Content-Type: application/json" \
  -d '{
    "supplier_id": "test-supplier-id",
    "purchase_date": "2025-01-15",
    "total_amount": 5000.00,
    "cost_center_id": "cc-001",
    "expense_account_id": "5000",
    "payable_account_id": "2100"
  }'

# Post to accounting
curl -X POST http://localhost:8010/api/v1/purchases/{purchase_id}/post-accounting

# Verify reconciliation
curl -X GET "http://localhost:8010/api/v1/purchases/reconcile?period=2025-01"
```

### Step 6: Verify No Data Loss

```bash
# Count records before and after
python -c "
from app.core.database import SessionLocal
from app.models.sales import Sale, Invoice
from app.models.purchases import Purchase

db = SessionLocal()
sales_count = db.query(Sale).count()
invoices_count = db.query(Invoice).count()
purchases_count = db.query(Purchase).count()

print(f'Sales: {sales_count}')
print(f'Invoices: {invoices_count}')
print(f'Purchases: {purchases_count}')
db.close()
"

# All counts should match pre-deployment values
```

### Step 7: Deploy to Production

Once staging tests pass:

1. **Backup production database**
2. **Stop application server**
3. **Run migrations on production**
4. **Verify all columns added**
5. **Start application server**
6. **Run production smoke tests**
7. **Monitor for errors** (1 hour minimum)

```bash
# Restart application
systemctl restart cnperp

# Check logs for errors
tail -f app.log

# Monitor health endpoint
curl http://localhost:8010/health
```

---

## Rollback Procedure (if needed)

If issues occur, rollback is safe because:
1. **New columns are optional** (all default to NULL or 'draft')
2. **No breaking changes** to existing APIs
3. **Old GL posting logic unchanged** (parallel to new dimensional posting)

**To rollback:**

```bash
# Restore from pre-deployment backup
python -c "from app.services.backup_service import BackupService; from app.core.database import SessionLocal; db = SessionLocal(); BackupService(db).restore_backup('pre-phase2-deployment'); db.close()"

# Or simply remove new code and restart
# - Models still have old fields
# - APIs not using dimensional posting still work
# - Old service methods unchanged
```

---

## Post-Deployment Tasks

### 1. Enable Dimensional Accounting

For each sales/purchase transaction, populate new fields:
```python
# At time of invoice/purchase creation
invoice.cost_center_id = cost_center_id  # From UI
invoice.project_id = project_id          # From UI
invoice.revenue_account_id = "4000"      # From chart of accounts
invoice.ar_account_id = "1200"           # From chart of accounts
```

### 2. Manual GL Posting for Existing Transactions

For older transactions without dimensional data:
```bash
# Option 1: Retroactively assign dimensions and post
python -c "
from app.core.database import SessionLocal
from app.services.sales_service import SalesService
from app.models.sales import Invoice

db = SessionLocal()
service = SalesService(db)

# Get unposted invoices
unposted = db.query(Invoice).filter(Invoice.posting_status == 'draft').all()
for invoice in unposted:
    if invoice.revenue_account_id and invoice.ar_account_id:
        service.post_sale_to_accounting(invoice.id)

db.close()
"

# Option 2: Assign default dimensions to all existing transactions
python scripts/assign_default_dimensions_to_sales.py
python scripts/assign_default_dimensions_to_purchases.py
```

### 3. Monitor Reconciliation

```bash
# Daily reconciliation check
curl -X GET "http://localhost:8010/api/v1/sales/reconcile?period=2025-01"
curl -X GET "http://localhost:8010/api/v1/purchases/reconcile?period=2025-01"

# Investigate any variances > 0.01
# Most common cause: missing GL account mappings
```

### 4. Training

- Train finance team on new GL posting workflows
- Document dimensional accounting policies (which transactions get which dimensions)
- Set up default dimension mappings in system settings

---

## Success Metrics

Phase 2 deployment is successful when:

✅ **Data Integrity**
- 0 data loss or corruption
- All existing sales/purchases records intact
- GL accounts balanced (Debit == Credit for all posts)

✅ **Functional Requirements**
- Revenue tracked by cost center/project/department
- Expenses tracked by cost center/project/department
- GL posting creates balanced, dimensional entries
- Reconciliation variance < 0.01

✅ **Performance**
- Invoice posting completes in < 500ms
- Reconciliation query completes in < 2 seconds
- No database locking issues

✅ **Operational**
- Zero errors in production logs
- All API endpoints responding correctly
- Dimensional analysis reports accurate

---

## Phase 3 Roadmap (After Phase 2 Complete)

1. **Manufacturing + Sales Integration** - COGS matching to revenue dimensions
2. **Banking Module** - Payment GL posting with dimensions
3. **Asset Management** - Depreciation by cost center/project
4. **Advanced Reporting** - Multi-dimensional P&L statements
5. **Budget vs Actual** - Compare budgets to actual by dimension

---

## Support & Troubleshooting

**Issue:** GL entries not creating
- Check that revenue_account_id and ar_account_id are set
- Verify accounts exist in accounting_codes table
- Check GL posting logs for errors

**Issue:** Reconciliation variance exists
- Check for partial dimension assignments
- Verify all GL entries have dimension_assignments
- Check for double-posting or reversals

**Issue:** Performance degradation
- Check indexes are created (idx_sales_cost_center_id, etc.)
- Monitor query execution times
- May need index optimization if datasets > 1M records

**Issue:** Dimension assignments missing**
- Ensure DimensionValue records exist in dimension_values table
- Check that cost_center_id/project_id/department_id are valid UUIDs
- Verify FK constraint between sales/purchases and dimension_values

---

## Related Documentation

- ENTERPRISE_READINESS_ROADMAP.md - 12-week implementation plan for all 8 modules
- HOW_TO_IMPLEMENT.md - Step-by-step dimensional accounting implementation guide
- SYSTEM_ARCHITECTURE_MAP.md - Data flows and module dependencies
- manufacturing.md - Phase 1 implementation (already complete)
