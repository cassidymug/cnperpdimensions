# Manufacturing & Accounting Integration Implementation Guide

## Overview
The manufacturing module has been enhanced with full accounting dimensions integration, allowing complete cost tracking from production orders through to journal entries in the general ledger.

## Key Components

### 1. Manufacturing Module (manufacturing.html)
**Location**: `http://localhost:8010/static/manufacturing.html`

#### Tabs:
- **Products**: Manage manufactured products with SKU, unit of measure
- **BOMs**: Bill of materials management with component tracking
- **Production Orders**: Create orders with full dimensional accounting
- **Dimensional Reports**: Analysis by cost center, project, department, location

#### Key Features:
- **Accounting Dimensions**: Each production order captures:
  - Cost Center (required)
  - Project
  - Department
  - GL Account for WIP (Work-In-Process)
  - GL Account for Labor costs

### 2. Enhanced Manufacturing Module (manufacturing-enhanced.html)
**Location**: `http://localhost:8010/static/manufacturing-enhanced.html`

#### Tabs:
- **Dimensional Analysis**: Manufacturing costs grouped by dimension
- **Accounting Bridge**: Map manufacturing costs to GL accounts
- **Journal Entries**: View all manufacturing-generated journal entries
- **Reconciliation**: Verify manufacturing costs match GL balances

## API Endpoints (Required Implementation)

### Manufacturing Endpoints

```
POST /api/v1/manufacturing/production-orders/
Parameters:
  - product_id (required)
  - quantity (required)
  - cost_center_id (required for accounting)
  - project_id
  - department_id
  - wip_account_id (GL account for WIP)
  - labor_account_id (GL account for labor)

Returns: Production order with accounting metadata
```

```
GET /api/v1/manufacturing/production-orders/{id}/accounting-details
Returns: Accounting details including GL mappings, dimensions, posting status
```

```
POST /api/v1/manufacturing/production-orders/{id}/post-accounting
Returns: { entries_created: int, journal_entry_ids: [...] }
Creates journal entries in the general ledger
```

### Dimensional Analysis Endpoints

```
GET /api/v1/manufacturing/dimensional-analysis
Parameters:
  - type: cost_center | project | department | location
  - period: current_month | last_month | current_quarter | current_year
  - group_by: product | order | bom

Returns:
{
  summary: {
    total_orders: int,
    total_quantity: int,
    total_cost: float,
    unique_dims: int
  },
  details: [{
    dimension: string,
    product: string,
    order_number: string,
    quantity: int,
    material_cost: float,
    labor_cost: float,
    overhead_cost: float,
    total_cost: float
  }]
}
```

### Accounting Bridge Endpoints

```
GET /api/v1/manufacturing/accounting-bridge
Parameters:
  - cost_center: string (cost center ID)
  - period: date

Returns:
{
  bridge_items: [{
    dimension: string,
    cost_element: string,
    material: float,
    labor: float,
    overhead: float,
    total: float,
    gl_account: string,
    status: draft | posted
  }]
}
```

```
POST /api/v1/manufacturing/post-to-accounting
Body: { cost_center_id: string }

Returns:
{
  entries_created: int,
  journal_entry_ids: [...],
  gl_accounts_updated: [...]
}

Creates journal entries for all manufacturing costs in cost center
```

### Journal Entry Endpoints

```
GET /api/v1/manufacturing/journal-entries
Parameters:
  - period: date (optional)
  - status: draft | posted (optional)
  - source: manufacturing | manual (optional)

Returns:
{
  entries: [{
    id: string,
    date: date,
    reference: string,
    gl_account: string,
    dimension: string,
    debit: float,
    credit: float,
    status: string
  }]
}
```

### Reconciliation Endpoints

```
GET /api/v1/manufacturing/reconcile
Parameters:
  - period: month (YYYY-MM format)

Returns:
{
  reconciliation: [{
    dimension: string,
    mfg_cost: float,
    gl_balance: float,
    variance: float,
    pct_diff: float,
    status: Reconciled | Variance,
    notes: string
  }]
}
```

## Database Schema Updates Required

### Production Orders Enhancement
```sql
ALTER TABLE production_orders ADD COLUMN IF NOT EXISTS (
  cost_center_id VARCHAR(36) REFERENCES accounting_dimensions(id),
  project_id VARCHAR(36) REFERENCES accounting_dimensions(id),
  department_id VARCHAR(36) REFERENCES accounting_dimensions(id),
  wip_account_id VARCHAR(36) REFERENCES accounting_codes(id),
  labor_account_id VARCHAR(36) REFERENCES accounting_codes(id),
  posting_status VARCHAR(20) DEFAULT 'draft',
  last_posted_date DATETIME
);

CREATE INDEX idx_po_cost_center ON production_orders(cost_center_id);
CREATE INDEX idx_po_posting_status ON production_orders(posting_status);
```

### Manufacturing Journal Entries Table
```sql
CREATE TABLE IF NOT EXISTS manufacturing_journal_entries (
  id VARCHAR(36) PRIMARY KEY,
  production_order_id VARCHAR(36) NOT NULL,
  journal_entry_id VARCHAR(36) NOT NULL,
  cost_center_id VARCHAR(36),
  project_id VARCHAR(36),
  department_id VARCHAR(36),
  cost_element VARCHAR(50), -- Material, Labor, Overhead
  amount DECIMAL(15,2),
  gl_account_id VARCHAR(36),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (production_order_id) REFERENCES production_orders(id),
  FOREIGN KEY (journal_entry_id) REFERENCES journal_entries(id),
  FOREIGN KEY (gl_account_id) REFERENCES accounting_codes(id)
);

CREATE INDEX idx_mje_production_order ON manufacturing_journal_entries(production_order_id);
CREATE INDEX idx_mje_cost_center ON manufacturing_journal_entries(cost_center_id);
```

## Integration with Journal Module

### Journal Entry Model Extension
```python
# In app/models/accounting.py - JournalEntry class

# Add to JournalEntry class:
manufacturing_cost_id = Column(String(36), ForeignKey("manufacturing_costs.id"), nullable=True)
production_order_id = Column(String(36), ForeignKey("production_orders.id"), nullable=True)
dimension_assignments = relationship(
    "AccountingDimensionAssignment",
    back_populates="journal_entry",
    cascade="all, delete-orphan"
)

# Add relationships
manufacturing_cost = relationship("ManufacturingCost", back_populates="journal_entries")
production_order = relationship("ProductionOrder", back_populates="journal_entries")
```

### Manufacturing Service Integration
```python
# In app/services/manufacturing_service.py

class ManufacturingService:
    def post_to_accounting(self, production_order_id: str, cost_center_id: str) -> dict:
        """
        Post manufacturing costs to General Ledger with dimensional assignments

        1. Retrieve production order with costs
        2. Get WIP and labor GL accounts
        3. Create journal entries for:
           - Material costs -> WIP Account (Debit)
           - Labor costs -> Labor Account (Debit)
           - Offset -> appropriate liability/payable (Credit)
        4. Apply dimension assignments to all entries
        5. Mark production order as posted
        6. Return created entries
        """
        pass
```

## Implementation Checklist

- [ ] Update ProductionOrder model with accounting fields
- [ ] Create manufacturing_journal_entries table
- [ ] Implement manufacturing service post_to_accounting() method
- [ ] Add API endpoints for dimensional analysis
- [ ] Add API endpoints for accounting bridge
- [ ] Add API endpoint for post-to-accounting
- [ ] Add API endpoints for journal entry filtering
- [ ] Add API endpoint for reconciliation
- [ ] Update production order modals to include GL account selection
- [ ] Add dimension assignment logic to journal entries
- [ ] Implement reconciliation service
- [ ] Create reconciliation report generation
- [ ] Add audit trail for manual vs auto-posted entries
- [ ] Test end-to-end flow from production order to GL

## Testing Scenarios

### Scenario 1: Production Order Creation with Accounting
1. Create product (SKU: PART-001)
2. Create production order with:
   - Cost Center: CC-001
   - Project: PROJ-001
   - WIP Account: 1500-100 (Asset - WIP)
   - Labor Account: 2100-100 (Liability - Payable)
3. Verify order displays with accounting dimensions

### Scenario 2: Cost Posting
1. Create and complete production order
2. Post costs to accounting
3. Verify journal entries created with correct:
   - GL accounts
   - Debit/Credit amounts
   - Dimensional assignments
   - Status = posted

### Scenario 3: Reconciliation
1. Create multiple production orders in period
2. Post all costs
3. Run reconciliation for period
4. Verify manufacturing total = GL total

## User Navigation Flow

```
Manufacturing Dashboard
  ├── Products Tab (Create/Manage)
  ├── BOMs Tab (Component tracking)
  ├── Production Orders Tab
  │   ├── Create with dimensions & GL accounts
  │   ├── View accounting details
  │   └── Post to accounting
  └── Dimensional Reports Tab
      ├── Analyze by dimension
      ├── View accounting bridge
      ├── See journal entries
      └── Run reconciliation
```

## Key Accounting Integrations

### Cost Flow
1. **Production Order Creation** → Captures dimensions & GL accounts
2. **Cost Recording** → Material, Labor, Overhead assigned to dimensions
3. **Journal Entry Generation** → Posts to specified GL accounts with dimension assignments
4. **Reconciliation** → Verifies manufacturing costs match GL balances by dimension

### Dimensional Accounting
- All manufacturing costs automatically tagged with:
  - Cost Center
  - Project
  - Department (optional)
  - Location (optional)
- Full drill-down capability to production order level
- Variance analysis between manufacturing and GL records

## Security & Audit

- All posts to GL recorded with:
  - User ID
  - Timestamp
  - Source (manufacturing vs manual)
  - Journal entry link
- Production orders locked after posting
- Reconciliation exceptions tracked
- Audit trail for all GL modifications

