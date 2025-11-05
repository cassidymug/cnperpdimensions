# 🏭 Phase 3: Manufacturing + Sales COGS Integration

**Objective**: Link manufacturing costs to sales revenue by dimension for accurate gross margin and profitability analysis

**Scope**: ProductionOrder → COGS GL Entry → Invoice Revenue GL Entry → Gross Margin Calculation

**Timeline**: 1-2 weeks

**Completion Date**: November 6, 2025 (estimated)

---

## Phase 3 Overview

### Problem Statement

**Current Gap**:
- ✅ Phase 2 posts Sales revenue to GL by dimension
- ✅ Phase 1 posts Manufacturing costs (labor, OH) to GL
- ❌ **MISSING**: Link between manufactured product cost and revenue GL

**Result**: No gross margin reporting by dimension

### Solution Architecture

```
ProductionOrder (with dimensions)
  ├─ cost_center_id, project_id, department_id
  ├─ product_id (what we're making)
  ├─ quantity (how much)
  └─ total_cost (labor + materials + OH)
       ↓
       (When Invoice is created from this product)
       ↓
Invoice (same dimensions as original production)
  ├─ same cost_center_id, project_id, department_id
  ├─ product_id (same as PO)
  └─ total_amount (revenue)
       ↓
GL Entries:
  ├─ Revenue Credit (to Revenue account)
  ├─ AR Debit (to AR account)
  ├─ COGS Debit (to COGS account) ← **NEW IN PHASE 3**
  └─ Inventory Credit (reversal) ← **NEW IN PHASE 3**
       ↓
Reconciliation:
  Revenue - COGS = Gross Margin
  (All by cost_center, project, department)
```

---

## Key Features

### 1. **Automatic COGS Posting**

When invoice is posted to accounting:
```python
# Current (Phase 2) - Revenue posting
GL Entry 1: AR Debit (Invoice Amount)
GL Entry 2: Revenue Credit (Invoice Amount)

# New (Phase 3) - COGS posting
GL Entry 3: COGS Debit (Product's Manufacturing Cost)
GL Entry 4: Inventory Credit (Product's Manufacturing Cost)
```

**Dimension Preservation**:
- COGS GL entries inherit dimensions from Invoice
- COGS GL entries also inherit dimensions from original ProductionOrder
- Both sets of dimensions recorded in `AccountingDimensionAssignment` table

---

### 2. **Automatic Dimension Inheritance**

```
Product (e.g., "Widget")
  created by ProductionOrder
    with cost_center_id = "CC-001"

When Widget is sold (Invoice created):
  ├─ Sales Revenue GL Entry
  │   ├─ cost_center_id = "CC-001" (from Invoice)
  │   └─ Dimension Assignment Links to Revenue GL
  │
  └─ COGS GL Entry
      ├─ cost_center_id = "CC-001" (from Product's original PO)
      └─ Dimension Assignment Links to COGS GL
```

**Algorithm**:
1. User creates Invoice for a product
2. Fetch product's ProductionOrder (where it was made)
3. Extract dimensions from ProductionOrder (cost_center_id, project_id, department_id)
4. Use Invoice's dimensions for Revenue GL
5. Use ProductionOrder's dimensions for COGS GL
6. If both exist but differ = Flag variance (different cost centers made vs sold)

---

### 3. **Gross Margin Reconciliation**

**By Cost Center**:
```
Period: 2025-10

Cost Center: CC-001
  Revenue: $50,000.00
  COGS:    $30,000.00
  Gross Margin: $20,000.00 (40%)

Cost Center: CC-002
  Revenue: $75,000.00
  COGS:    $45,000.00
  Gross Margin: $30,000.00 (40%)

TOTAL:
  Revenue: $125,000.00
  COGS:    $75,000.00
  Gross Margin: $50,000.00 (40%)
```

**By Project**:
```
Project: PROJ-001
  Revenue: $100,000.00
  COGS:    $60,000.00
  Gross Margin: $40,000.00 (40%)
```

**By Department**:
```
Department: SALES
  Revenue: $200,000.00
  COGS:    $120,000.00
  Gross Margin: $80,000.00 (40%)
```

---

### 4. **Variance Analysis**

**Scenario A: Perfect Match**
```
Invoice (CC-001, PROJ-001, DEPT-SALES): $100 revenue
ProductionOrder (CC-001, PROJ-001, DEPT-SALES): $60 COGS
Result: ✅ Dimensions match → Use as-is
```

**Scenario B: Mismatched Cost Center**
```
Invoice (CC-001, PROJ-001): $100 revenue
ProductionOrder (CC-002, PROJ-001): $60 COGS
Result: ⚠️ Variance = different cost centers made vs sold
       → Flag in variance report
       → Use COGS dimensions (where product was made)
```

**Scenario C: No ProductionOrder Found**
```
Invoice (CC-001): $100 revenue
ProductionOrder: NOT FOUND (purchased from supplier or legacy)
Result: ❌ Unable to post COGS
       → Manual GL entry required
       → Flag in error report
```

---

## Data Model Enhancements

### ProductionOrder Model Changes

**New Fields**:
```python
class ProductionOrder(Base):
    # ... existing fields ...

    # COGS Posting Status & Audit Trail
    cogs_posting_status = Column(String(20), default='pending')  # pending, posted, error
    cogs_gl_account_id = Column(String, ForeignKey('accounting_codes.id'), nullable=True)
    cogs_last_posted_date = Column(DateTime, nullable=True)
    cogs_posted_by = Column(String, ForeignKey('users.id'), nullable=True)

    # Relationships
    cogs_gl_account = relationship("AccountingCode", foreign_keys=[cogs_gl_account_id])
    cogs_posted_by_user = relationship("User", foreign_keys=[cogs_posted_by])
```

**Why These Fields**:
- `cogs_posting_status`: Track if COGS has been posted to GL (prevent double-posting)
- `cogs_gl_account_id`: Specify which GL account receives COGS debit
- `cogs_last_posted_date`: Audit trail (when was COGS posted)
- `cogs_posted_by`: Audit trail (who posted COGS)

---

### New Bridge Table: COGS_ALLOCATION

```python
class COGSAllocation(Base):
    __tablename__ = 'cogs_allocations'

    id = Column(UUID, primary_key=True, default=uuid4)
    production_order_id = Column(UUID, ForeignKey('production_orders.id'), nullable=False)
    invoice_id = Column(UUID, ForeignKey('invoices.id'), nullable=False)
    product_id = Column(UUID, ForeignKey('products.id'), nullable=False)

    quantity_produced = Column(Numeric(10, 2), nullable=False)
    quantity_sold = Column(Numeric(10, 2), nullable=False)
    cost_per_unit = Column(Numeric(15, 4), nullable=False)
    total_cogs = Column(Numeric(15, 2), nullable=False)

    revenue_gl_entry_id = Column(UUID, ForeignKey('journal_entries.id'), nullable=False)
    cogs_gl_entry_id = Column(UUID, ForeignKey('journal_entries.id'), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
```

**Purpose**: Track which invoice was assigned which production order's COGS

---

## Service Layer Implementation

### ManufacturingService Enhancements

**New Methods**:

#### 1. `post_cogs_to_accounting(production_order_id, invoice_id, user_id)`

```python
def post_cogs_to_accounting(self, production_order_id: str, invoice_id: str, user_id: str):
    """
    Post COGS from ProductionOrder to GL when Invoice is created/posted.

    Flow:
    1. Fetch ProductionOrder (get cost_center_id, project_id, department_id, total_cost)
    2. Fetch Invoice (get same dimensions, revenue_amount)
    3. Create 2 GL entries:
       - COGS Debit: To COGS GL account (with PO dimensions)
       - Inventory Credit: To Inventory GL account (with PO dimensions)
    4. Create COGS_ALLOCATION record
    5. Update ProductionOrder.cogs_posting_status = 'posted'
    6. Return GLPostingResponse with both GL entry IDs

    Returns:
        {
            "success": true,
            "production_order_id": "...",
            "invoice_id": "...",
            "cogs_entries_created": 2,
            "revenue_entries_created": 2,
            "total_revenue": 1000.00,
            "total_cogs": 600.00,
            "gross_margin": 400.00,
            "gross_margin_percent": 40.0
        }
    """
```

#### 2. `reconcile_cogs_by_dimension(period: str)`

```python
def reconcile_cogs_by_dimension(self, period: str):
    """
    Compare Revenue GL entries to COGS GL entries by dimension.
    Calculates gross margin and flags variances.

    Algorithm:
    For each dimension (cost_center, project, department):
        1. Sum Revenue GL entries for period
        2. Sum COGS GL entries for period
        3. Calculate Gross Margin = Revenue - COGS
        4. Calculate GM% = Gross Margin / Revenue
        5. Check variance (Revenue GL sum == Invoice sum)

    Returns:
        {
            "period": "2025-10",
            "by_dimension": [
                {
                    "cost_center_id": "CC-001",
                    "cost_center_name": "Manufacturing",
                    "revenue": 50000.00,
                    "cogs": 30000.00,
                    "gross_margin": 20000.00,
                    "gm_percent": 40.0,
                    "is_reconciled": true,
                    "variance": 0.00
                }
            ],
            "totals": {
                "revenue": 125000.00,
                "cogs": 75000.00,
                "gross_margin": 50000.00,
                "gm_percent": 40.0
            }
        }
    """
```

#### 3. `get_product_manufacturing_cost(product_id: str)`

```python
def get_product_manufacturing_cost(self, product_id: str):
    """
    Get the total cost of manufacturing a product (from most recent ProductionOrder).
    Used to populate COGS GL entry amount.

    Returns:
        {
            "product_id": "...",
            "product_name": "...",
            "production_order_id": "...",
            "total_cost": 600.00,
            "cost_per_unit": 150.00,
            "cost_center_id": "CC-001",
            "project_id": "PROJ-001",
            "department_id": "DEPT-001"
        }
    """
```

---

## API Endpoints

### Manufacturing Endpoints (Enhanced)

#### 1. POST `/manufacturing/production-orders/{id}/post-cogs`
```json
Request:
{
  "invoice_id": "inv-123",
  "user_id": "user-456"
}

Response:
{
  "success": true,
  "production_order_id": "po-789",
  "invoice_id": "inv-123",
  "cogs_entries_created": 2,
  "cogs_gl_entry_ids": ["je-cogs-debit", "je-cogs-credit"],
  "revenue_entries_created": 2,
  "revenue_gl_entry_ids": ["je-ar-debit", "je-rev-credit"],
  "total_revenue": 1000.00,
  "total_cogs": 600.00,
  "gross_margin": 400.00,
  "gross_margin_percent": 40.0,
  "posting_date": "2025-10-23T14:30:00Z"
}
```

#### 2. GET `/manufacturing/gross-margin-analysis?period=2025-10`
```json
Response:
{
  "period": "2025-10",
  "by_cost_center": [
    {
      "cost_center_id": "CC-001",
      "cost_center_name": "Production Floor 1",
      "revenue": 50000.00,
      "cogs": 30000.00,
      "gross_margin": 20000.00,
      "gm_percent": 40.0
    }
  ],
  "by_project": [...],
  "by_department": [...],
  "totals": {
    "revenue": 200000.00,
    "cogs": 120000.00,
    "gross_margin": 80000.00,
    "gm_percent": 40.0
  }
}
```

#### 3. GET `/manufacturing/cogs-variance-report?period=2025-10`
```json
Response:
{
  "variances": [
    {
      "invoice_id": "inv-123",
      "production_order_id": "po-789",
      "variance_type": "DIMENSION_MISMATCH",
      "revenue_cost_center": "CC-001",
      "cogs_cost_center": "CC-002",
      "difference": 0.00,
      "status": "flagged"
    }
  ],
  "unmatched_invoices": [
    {
      "invoice_id": "inv-456",
      "reason": "NO_PRODUCTION_ORDER_FOUND"
    }
  ]
}
```

#### 4. GET `/manufacturing/production-sales-reconciliation?period=2025-10`
```json
Response:
{
  "period": "2025-10",
  "invoices_posted": 45,
  "production_orders_linked": 45,
  "cogs_posted": 45,
  "unmatched": 0,
  "reconciliation_status": "COMPLETE",
  "reconciliation_percentage": 100.0,
  "total_revenue": 200000.00,
  "total_cogs": 120000.00,
  "total_gross_margin": 80000.00
}
```

---

### Sales Endpoints (Enhanced)

#### 5. GET `/sales/invoices/{id}/cogs-details`
```json
Response:
{
  "invoice_id": "inv-123",
  "revenue_amount": 1000.00,
  "cogs_amount": 600.00,
  "gross_margin": 400.00,
  "gm_percent": 40.0,
  "linked_production_order_id": "po-789",
  "cogs_posting_status": "posted",
  "cogs_posted_by": "John Doe",
  "cogs_posted_date": "2025-10-23T14:30:00Z"
}
```

#### 6. GET `/sales/cogs-reconciliation?period=2025-10`
```json
Response:
{
  "period": "2025-10",
  "summary": {
    "total_revenue": 200000.00,
    "total_cogs": 120000.00,
    "total_gm": 80000.00,
    "avg_gm_percent": 40.0
  },
  "by_dimension": [...]
}
```

---

## Database Changes

### Migration Script: `add_cogs_posting_to_production_orders.py`

**New Columns to production_orders Table**:
- `cogs_posting_status` VARCHAR(20) DEFAULT 'pending'
- `cogs_gl_account_id` VARCHAR - FK to accounting_codes
- `cogs_last_posted_date` DATETIME NULL
- `cogs_posted_by` VARCHAR - FK to users

**New Indexes**:
- `idx_production_orders_cogs_status` on cogs_posting_status
- `idx_production_orders_cogs_date` on cogs_last_posted_date

**New Table: cogs_allocations**:
```sql
CREATE TABLE cogs_allocations (
    id UUID PRIMARY KEY,
    production_order_id UUID NOT NULL REFERENCES production_orders(id),
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    product_id UUID NOT NULL REFERENCES products(id),
    quantity_produced NUMERIC(10,2),
    quantity_sold NUMERIC(10,2),
    cost_per_unit NUMERIC(15,4),
    total_cogs NUMERIC(15,2),
    revenue_gl_entry_id UUID NOT NULL REFERENCES journal_entries(id),
    cogs_gl_entry_id UUID NOT NULL REFERENCES journal_entries(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cogs_allocations_po ON cogs_allocations(production_order_id);
CREATE INDEX idx_cogs_allocations_invoice ON cogs_allocations(invoice_id);
CREATE INDEX idx_cogs_allocations_product ON cogs_allocations(product_id);
```

---

## Testing Strategy

### Test Cases (12+)

1. **COGS Posting with All Dimensions**
   - Create Production Order (CC-001, PROJ-001, DEPT-001) with cost=$600
   - Create Invoice (CC-001, PROJ-001, DEPT-001) with revenue=$1000
   - Post to GL
   - Verify: 4 GL entries created (2 revenue + 2 COGS), dimensions match

2. **COGS Posting with Partial Dimensions**
   - Create Production Order (CC-001, no project, no department) with cost=$600
   - Create Invoice (CC-001, PROJ-001, DEPT-001) with revenue=$1000
   - Post to GL
   - Verify: COGS uses PO dimensions (CC-001), Revenue uses Invoice dimensions

3. **Dimension Mismatch Variance**
   - Create Production Order (CC-001) with cost=$600
   - Create Invoice (CC-002) with revenue=$1000
   - Post to GL
   - Verify: Variance report flags dimension mismatch

4. **Gross Margin Calculation**
   - Create 3 invoices (all in CC-001): $1000, $2000, $3000 revenue
   - Create matching POs: $600, $1200, $1800 COGS
   - Reconcile
   - Verify: GM = $2200, GM% = 44%

5. **Double-Posting Prevention**
   - Create Production Order → Post COGS
   - Try to post COGS again
   - Verify: Error (already posted)

6. **Missing Production Order**
   - Create Invoice for product with no production history
   - Try to post COGS
   - Verify: Error or manual GL entry flag

7. **Reconciliation Accuracy**
   - Create 5 invoices with different cost centers
   - Post all to GL
   - Reconcile by cost center
   - Verify: Each cost center total matches GL

8. **Period Filtering**
   - Create invoices in October and November
   - Reconcile October
   - Verify: Only October data included

9. **Variance Report Accuracy**
   - Create invoices with matching and mismatched dimensions
   - Generate variance report
   - Verify: Correct count of matched/unmatched

10. **GL Entry Balancing**
    - Post multiple invoices with COGS
    - Verify: Total debits = Total credits

11. **Dimension Preservation in GL**
    - Post invoice to GL
    - Fetch GL entry
    - Verify: All dimensions present in AccountingDimensionAssignment

12. **Gross Margin Percent Calculation**
    - Create scenarios with different GM%
    - Verify: Calculations accurate to 0.01%

---

## Implementation Order

**Week 1** (Oct 28 - Nov 1):
- Day 1: Finalize design, get approval
- Day 2-3: Implement ProductionOrder model enhancements + migration
- Day 4-5: Implement service layer methods

**Week 2** (Nov 2 - 6):
- Day 1-2: Implement API endpoints + Pydantic schemas
- Day 3: Write complete test suite
- Day 4-5: Testing, bug fixes, documentation

---

## Success Criteria

✅ All 12 test cases pass
✅ GL entries created with correct amounts and dimensions
✅ Reconciliation variance < 0.01
✅ Gross margin calculated accurately by dimension
✅ Variance report correctly identifies mismatches
✅ Double-posting prevention working
✅ No errors in production logs
✅ All 6 new endpoints functional
✅ Documentation complete and clear

---

## Risk Mitigation

**Risk**: Mismatch between product's manufacturing cost and selling price
**Mitigation**: Variance report + GL reconciliation catches it

**Risk**: Missing production order for some products
**Mitigation**: Error handling + manual GL entry option

**Risk**: Double-posting of COGS
**Mitigation**: `cogs_posting_status` field prevents re-posting

**Risk**: Dimension mismatch between manufacturing and sales
**Mitigation**: Separate dimension tracking + variance analysis

---

## Rollback Plan

If Phase 3 causes issues:

1. Revert migrations: Drop new columns/tables
2. Disable COGS posting endpoints
3. Keep Phase 2 (Sales revenue posting) active
4. Restore from backup if needed

**Rollback Time**: < 30 minutes

---

## Next Phases (After Phase 3)

**Phase 4: Banking Module** (Weeks 7-9)
- Add dimensions to bank transfers, deposits, reconciliations
- Cash flow reporting by dimension

**Phase 5: Asset Management** (Weeks 10-12)
- Depreciation posting by dimension
- Asset allocation by cost center/project

**Phase 6: Advanced Reporting** (Weeks 13+)
- Multi-dimensional P&L
- Budget vs Actual analysis
- Consolidated reporting across all modules

---

## Phase 3 Summary

| Aspect | Details |
|--------|---------|
| **Objective** | Link manufacturing costs to sales revenue by dimension |
| **Scope** | ProductionOrder → COGS GL → Invoice Revenue GL → Gross Margin |
| **Models** | ProductionOrder (enhance), COGSAllocation (new) |
| **Services** | ManufacturingService (expand) |
| **Endpoints** | 6 new endpoints (4 Manufacturing + 2 Sales) |
| **Tests** | 12+ comprehensive test cases |
| **Timeline** | 2 weeks |
| **Files** | 8 new/modified files (~1,500 lines code) |
| **Success Metric** | Gross margin reporting by dimension with <0.01 variance |

