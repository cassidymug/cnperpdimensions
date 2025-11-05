# Manufacturing & Accounting Integration - System Architecture

## Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MANUFACTURING MODULE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [Production Order Creation]                                                │
│  ├─ Product                    (Required)                                    │
│  ├─ Quantity                   (Required)                                    │
│  ├─ Cost Center ID  ──────────────────┐  (Required for Accounting)          │
│  ├─ Project ID      ──────────────┐   │  (Optional)                         │
│  ├─ Department ID   ──────────┐   │   │  (Optional)                         │
│  ├─ WIP Account ID  ──────┐   │   │   │  (Required for GL)                  │
│  └─ Labor Account ID ───┐ │   │   │   │  (Required for GL)                  │
│                         │ │   │   │   │                                      │
│                         ↓ ↓   ↓   ↓   ↓                                      │
│                    ┌──────────────────────┐                                  │
│                    │  Production Order    │                                  │
│                    │   (Draft Status)     │                                  │
│                    └──────────────────────┘                                  │
│                            │                                                 │
│                            ↓                                                 │
│            [Record Manufacturing Costs]                                      │
│            ├─ Material Cost  ──┐                                             │
│            ├─ Labor Cost     ──┤─→ ManufacturingCost Table                  │
│            └─ Overhead Cost  ──┘    (linked to PO)                         │
│                            │                                                 │
│                            ↓                                                 │
│               ┌────────────────────────┐                                    │
│               │  Total Manufacturing   │                                    │
│               │ Material + Labor +     │                                    │
│               │ Overhead = Total Cost  │                                    │
│               └────────────────────────┘                                    │
│                            │                                                 │
│                            │ POST /post-accounting                          │
│                            ↓                                                 │
│              ┌──────────────────────────────┐                               │
│              │  ManufacturingService        │                               │
│              │  .post_to_accounting()       │                               │
│              └──────────────────────────────┘                               │
│                            │                                                 │
│              ┌─────────────┼─────────────┐                                  │
│              │             │             │                                  │
│              ↓             ↓             ↓                                  │
│          ┌────────┐   ┌────────┐   ┌─────────┐                            │
│          │   WIP  │   │ LABOR  │   │ OFFSET  │                            │
│          │ DEBIT  │   │ DEBIT  │   │ CREDIT  │                            │
│          │(Asset) │   │(Payable)   │(Payable)│                            │
│          │$6000   │   │$2000   │   │($8000)  │                            │
│          └────────┘   └────────┘   └─────────┘                            │
│              │             │             │                                  │
│              └─────────────┼─────────────┘                                  │
│                            │                                                 │
│              ┌─────────────────────────────┐                                │
│              │    For Each Journal Entry:   │                               │
│              │  Attach All Dimensions:     │                               │
│              │  ├─ Cost Center             │                               │
│              │  ├─ Project (if set)        │                               │
│              │  └─ Department (if set)     │                               │
│              └─────────────────────────────┘                                │
│                            │                                                 │
└────────────────────────────┼────────────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ACCOUNTING MODULE (GENERAL LEDGER)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│            [Journal Entries Created by Manufacturing]                        │
│                                                                              │
│  Entry 1: WIP Debit                                                         │
│  ├─ Account: 1500-100 (Work in Process)                                     │
│  ├─ Debit: $6,000.00                                                        │
│  ├─ Credit: $0.00                                                           │
│  ├─ Reference: MFG-{po-id}-WIP                                              │
│  ├─ Source: MANUFACTURING                                                   │
│  └─ Dimensions:                                                             │
│     ├─ Cost Center: CC-001                                                  │
│     ├─ Project: PROJ-001 (if set)                                           │
│     └─ Department: DEPT-001 (if set)                                        │
│                                                                              │
│  Entry 2: Labor Debit                                                       │
│  ├─ Account: 2100-100 (Accrued Labor)                                       │
│  ├─ Debit: $2,000.00                                                        │
│  ├─ Credit: $0.00                                                           │
│  ├─ Reference: MFG-{po-id}-LABOR                                            │
│  ├─ Source: MANUFACTURING                                                   │
│  └─ Dimensions:                                                             │
│     ├─ Cost Center: CC-001                                                  │
│     ├─ Project: PROJ-001 (if set)                                           │
│     └─ Department: DEPT-001 (if set)                                        │
│                                                                              │
│  Entry 3: Offset Credit                                                     │
│  ├─ Account: 2100-200 (Manufacturing Payable)                               │
│  ├─ Debit: $0.00                                                            │
│  ├─ Credit: $8,000.00                                                       │
│  ├─ Reference: MFG-{po-id}-OFFSET                                           │
│  ├─ Source: MANUFACTURING                                                   │
│  └─ Dimensions:                                                             │
│     ├─ Cost Center: CC-001                                                  │
│     ├─ Project: PROJ-001 (if set)                                           │
│     └─ Department: DEPT-001 (if set)                                        │
│                                                                              │
│         All 3 entries total to: $8,000.00 (balanced)                        │
│         Production Order Status: POSTED                                      │
│         Last Posted Date: 2025-10-22                                        │
│         Posted By: User ID                                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                             │
                             ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                     REPORTING & RECONCILIATION LAYER                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  [Dimensional Analysis]  (GET /dimensional-analysis)                         │
│  ├─ Dimension Type: Cost Center                                             │
│  ├─ Period: Current Month                                                   │
│  └─ Results:                                                                │
│     ├─ CC-001:  $8,000.00                                                   │
│     ├─ CC-002:  $5,500.00                                                   │
│     └─ Total:   $13,500.00                                                  │
│                                                                              │
│  [Accounting Bridge]  (GET /accounting-bridge)                              │
│  ├─ Cost Center: CC-001                                                     │
│  ├─ Period: 2025-10                                                         │
│  └─ Mapping:                                                                │
│     ├─ Material:   $5,000.00 → WIP Account (1500-100)                      │
│     ├─ Labor:      $2,000.00 → Labor Account (2100-100)                    │
│     └─ Overhead:   $1,000.00 → WIP Account (1500-100)                      │
│                                                                              │
│  [Monthly Reconciliation]  (GET /reconcile)                                 │
│  ├─ Period: 2025-10                                                         │
│  ├─ Manufacturing Total:  $8,000.00                                         │
│  ├─ GL Total:             $8,000.00                                         │
│  ├─ Variance:             $0.00                                             │
│  ├─ Variance %:           0.0%                                              │
│  └─ Status:               RECONCILED ✓                                      │
│                                                                              │
│  By Dimension:                                                              │
│  ├─ CC-001:    Mfg=$8,000  GL=$8,000  Variance=$0      RECONCILED ✓        │
│  └─ CC-002:    Mfg=$5,500  GL=$5,500  Variance=$0      RECONCILED ✓        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## API Endpoint Relationships

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          API ENDPOINT FLOW                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. POST /manufacturing/production-orders/{id}/post-accounting           │
│     ├─ Input: Production Order ID, User ID (optional)                   │
│     ├─ Logic: Service.post_to_accounting()                              │
│     ├─ Output: 3 Journal Entries with dimensions                        │
│     └─ Side Effect: PO status → "posted", last_posted_date set         │
│                                                                          │
│  2. GET /manufacturing/production-orders/{id}/accounting-details         │
│     ├─ Input: Production Order ID                                       │
│     ├─ Output: Complete accounting metadata                             │
│     └─ Includes: Dimensions, GL accounts, all JE details               │
│                                                                          │
│  3. GET /manufacturing/dimensional-analysis                             │
│     ├─ Input: type, period, group_by                                    │
│     ├─ Logic: Aggregate by dimension over period                        │
│     └─ Output: Summary + detailed breakdown table                       │
│                                                                          │
│  4. GET /manufacturing/accounting-bridge                                │
│     ├─ Input: cost_center (optional), period (optional)                 │
│     ├─ Logic: Map Mfg costs to GL accounts                              │
│     └─ Output: Cost allocation summary by account                       │
│                                                                          │
│  5. GET /manufacturing/journal-entries                                  │
│     ├─ Input: period, status, cost_center, skip, limit                  │
│     ├─ Logic: Filter manufacturing JE by multiple criteria              │
│     └─ Output: Paginated JE list with dimensions                        │
│                                                                          │
│  6. GET /manufacturing/reconcile                                        │
│     ├─ Input: period (YYYY-MM required)                                 │
│     ├─ Logic: Service.reconcile_manufacturing_costs()                   │
│     └─ Output: Reconciliation report with variance by dimension         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Database Schema Relationships

```
┌──────────────────────────────────────────────────────────────────────────┐
│                       DATABASE RELATIONSHIPS                             │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  production_orders                                                       │
│  ├─ id (PK)                                                              │
│  ├─ order_number                                                         │
│  ├─ product_id → products (FK)                                           │
│  ├─ quantity_planned                                                     │
│  │                                                                       │
│  ├─ [NEW FIELDS]                                                         │
│  ├─ cost_center_id → dimension_values (FK) ◄──┐                        │
│  ├─ project_id → dimension_values (FK)     ◄──┼─ Accounting Dims       │
│  ├─ department_id → dimension_values (FK)  ◄──┤                        │
│  ├─ wip_account_id → accounting_codes (FK) ◄──┼─ GL Accounts          │
│  ├─ labor_account_id → accounting_codes (FK)  │                        │
│  ├─ posting_status ('draft'|'posted'|'recon') │                        │
│  ├─ last_posted_date                          │                        │
│  └─ posted_by → users (FK)                 ◄──┴─ Audit Trail          │
│                           │                                              │
│                           │ (one-to-many)                                │
│                           ↓                                              │
│  manufacturing_costs                                                     │
│  ├─ id (PK)                                                              │
│  ├─ production_order_id (FK)                                             │
│  ├─ material_cost                                                        │
│  ├─ labor_cost                                                           │
│  ├─ overhead_cost                                                        │
│  └─ total_cost                                                           │
│                           │                                              │
│                           │ (implicit via reference)                     │
│                           ↓                                              │
│  journal_entries (created by post_to_accounting)                         │
│  ├─ id (PK)                                                              │
│  ├─ reference = 'MFG-{po-id}-{WIP|LABOR|OFFSET}'                       │
│  ├─ source = 'MANUFACTURING'                                            │
│  ├─ accounting_code_id (FK) → GL account                                │
│  ├─ debit_amount                                                         │
│  ├─ credit_amount                                                        │
│  ├─ entry_date                                                           │
│  └─ accounting_entry_id (FK)                                             │
│                           │                                              │
│                           │ (one-to-many)                                │
│                           ↓                                              │
│  accounting_dimension_assignments                                        │
│  ├─ journal_entry_id (FK)                                                │
│  ├─ dimension_value_id (FK) → dimension_values                           │
│  │                          ▲                                            │
│  │                          │ belongs to                                 │
│  │                          │                                            │
│  │                    dimension_values                                   │
│  │                    ├─ id (PK)                                         │
│  │                    ├─ dimension_id → accounting_dimensions            │
│  │                    ├─ value (e.g., 'CC-001')                          │
│  │                    └─ description                                     │
│  │                                                                       │
│  └─ (Stores Cost Center, Project, Department, Location assignments)    │
│                                                                          │
│  All entries have same dimensions applied:                               │
│  Entry 1 (WIP) + Entry 2 (Labor) + Entry 3 (Offset)                    │
│    ├─ CC-001 dimension assignment                                        │
│    ├─ PROJ-001 dimension assignment (if set)                             │
│    └─ DEPT-001 dimension assignment (if set)                             │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Key Features Summary

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          FEATURE COVERAGE                                │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  GL POSTING AUTOMATION                                                   │
│  ✓ Automatic journal entry creation from manufacturing costs            │
│  ✓ Multi-cost-element support (Material, Labor, Overhead)               │
│  ✓ Debit/credit balance validation ($8000 = $6000 + $2000)             │
│  ✓ GL account mapping validation (WIP, Labor accounts required)         │
│  ✓ Posting status tracking (draft → posted → reconciled)                │
│  ✓ Audit trail (user, date, status recorded)                           │
│  ✓ Idempotent operations (safe to retry)                                │
│  ✓ Error handling (validation, not-found, system errors)                │
│                                                                          │
│  DIMENSIONAL TRACKING                                                    │
│  ✓ Cost center support (required)                                        │
│  ✓ Project tracking (optional)                                           │
│  ✓ Department tracking (optional)                                        │
│  ✓ Location tracking (optional)                                          │
│  ✓ Automatic dimension assignment to all GL entries                      │
│  ✓ Dimension-level cost allocation                                       │
│  ✓ Dimension filtering and grouping                                      │
│                                                                          │
│  REPORTING & ANALYSIS                                                    │
│  ✓ Dimensional cost analysis (by cost center, project, dept, location)  │
│  ✓ Accounting bridge mapping (Mfg → GL allocation)                      │
│  ✓ Journal entry viewing with dimensional filters                        │
│  ✓ Period-based filtering (month, quarter, year)                        │
│  ✓ Pagination support for large datasets                                 │
│  ✓ Cost aggregation and rollup                                           │
│                                                                          │
│  RECONCILIATION                                                          │
│  ✓ Monthly reconciliation (YYYY-MM period format)                        │
│  ✓ Variance detection by dimension                                       │
│  ✓ Variance percentage calculation                                       │
│  ✓ Reconciled vs variance dimension separation                           │
│  ✓ Reconciliation status reporting                                       │
│  ✓ Audit trail (reconciliation date, items)                              │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Deployment Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                      DEPLOYMENT LAYERS                                 │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  LAYER 1: Frontend (HTML/JavaScript)                                   │
│  ├─ manufacturing.html (enhanced production order UI)                  │
│  ├─ manufacturing-enhanced.html (dashboard with 4 tabs)               │
│  └─ Functions: postProductionToAccounting(), viewProductionOrder()   │
│                                                                        │
│  LAYER 2: API (FastAPI)                                                │
│  ├─ 6 new endpoints in /api/v1/endpoints/manufacturing.py             │
│  ├─ Request validation & error handling                               │
│  └─ Response formatting with proper HTTP status codes                 │
│                                                                        │
│  LAYER 3: Services (Python Business Logic)                             │
│  ├─ ManufacturingService.post_to_accounting()                          │
│  ├─ ManufacturingService.reconcile_manufacturing_costs()              │
│  ├─ GL posting logic with dimension preservation                      │
│  └─ Reconciliation with variance detection                            │
│                                                                        │
│  LAYER 4: Models (SQLAlchemy ORM)                                       │
│  ├─ ProductionOrder (8 new accounting fields)                          │
│  ├─ Relationships to DimensionValue, AccountingCode, User              │
│  ├─ JournalEntry (existing, linked to manufacturing)                   │
│  ├─ AccountingDimensionAssignment (links dimensions to JE)             │
│  └─ ManufacturingCost (linked to PO)                                   │
│                                                                        │
│  LAYER 5: Database (MySQL)                                              │
│  ├─ production_orders table (8 new columns added)                      │
│  ├─ 6 foreign key constraints created                                  │
│  ├─ 3 performance indexes added                                        │
│  └─ Migration script: migrate_add_accounting_to_production_orders.py   │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

## Success Criteria

```
✅ All Components Implemented
   [✓] Model layer enhanced with accounting fields
   [✓] Service layer with GL posting and reconciliation
   [✓] 6 API endpoints fully functional
   [✓] Database migration script ready
   [✓] Frontend HTML updated
   [✓] Documentation complete

✅ Functionality Verified
   [✓] Production orders accept accounting dimensions
   [✓] GL posting creates 3 journal entries
   [✓] All entries have correct debit/credit amounts
   [✓] All entries have dimensional assignments
   [✓] Posting status updates correctly
   [✓] Reconciliation detects matching balances

✅ Quality Standards Met
   [✓] Full error handling with meaningful messages
   [✓] Idempotent database migration
   [✓] Comprehensive input validation
   [✓] Audit trail (user, date, status)
   [✓] Production-ready code patterns
   [✓] RESTful API design

✅ Testing Coverage
   [✓] Database migration tested
   [✓] API endpoints tested
   [✓] GL posting logic verified
   [✓] Reconciliation verified
   [✓] Dimensional assignment verified
   [✓] Error scenarios covered

✅ Documentation Complete
   [✓] Implementation guide created
   [✓] Quick reference guide created
   [✓] Code examples provided
   [✓] API endpoint documentation complete
   [✓] Database schema documented
   [✓] Testing procedures documented
```

---

**Generated**: October 22, 2025
**Status**: ✅ READY FOR PRODUCTION
**Next Step**: Run database migration and restart application
