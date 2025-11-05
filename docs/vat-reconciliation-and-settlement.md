# VAT Reconciliation and Settlement System

## Overview

This document describes the complete VAT (Value Added Tax) reconciliation and settlement system, including how VAT is collected, reconciled, and properly posted to the general ledger with IFRS-compliant journal entries.

## VAT Account Structure

The system uses three main VAT accounts:

### 1. **Account 1160 - VAT Receivable (Input VAT)** - Asset Account
- **Purpose**: Tracks VAT paid on purchases, expenses, and landed costs
- **Usage**: Automatically selected when recording purchases, landed costs, duties
- **Normal Balance**: Debit (Asset account)
- **Increases with**: Debit (when VAT is paid to suppliers)
- **Decreases with**: Credit (when cleared during VAT settlement)

### 2. **Account 2132 - VAT Payable (Output VAT)** - Liability Account
- **Purpose**: Tracks VAT collected from sales
- **Usage**: Automatically selected when recording sales, POS transactions
- **Normal Balance**: Credit (Liability account)
- **Increases with**: Credit (when VAT is collected from customers)
- **Decreases with**: Debit (when cleared during VAT settlement)

### 3. **Account 2131 - VAT Control** - Parent Liability Account
- **Purpose**: Consolidation and control account for VAT
- **Usage**: Optional - can be used for VAT consolidation entries
- **Note**: Currently available but not automatically used; can be added for advanced VAT control

---

## VAT Collection Process

### Sales Transactions (Output VAT)

When a sale is recorded via POS, Sales module, or Credit Notes:

**Automatic Behavior:**
1. System calculates VAT based on item prices and VAT rate (14%)
2. System automatically selects **Account 2132 (VAT Payable)** for output VAT
3. VAT is recorded in `sales.output_vat_account_id`
4. Journal entries are created:

```
DR  Cash/Bank Account          [Total including VAT]
    CR  Sales Revenue               [Sale amount excluding VAT]
    CR  VAT Payable (2132)          [VAT amount collected]
```

**Example:**
- Sale Amount: BWP 1,000.00
- VAT (14%): BWP 140.00
- Total: BWP 1,140.00

**Journal Entry:**
```
DR  Cash (1010)              1,140.00
    CR  Sales (4010)                 1,000.00
    CR  VAT Payable (2132)             140.00
```

### Purchase Transactions (Input VAT)

When a purchase is recorded in the Purchases module:

**Automatic Behavior:**
1. System calculates VAT on purchase items
2. System automatically selects **Account 1160 (VAT Receivable)** for input VAT
3. VAT is recorded in `purchases.input_vat_account_id`
4. Journal entries are created:

```
DR  Inventory/Expense           [Purchase amount excluding VAT]
DR  VAT Receivable (1160)       [VAT amount paid]
    CR  Accounts Payable            [Total including VAT]
```

**Example:**
- Purchase Amount: BWP 500.00
- VAT (14%): BWP 70.00
- Total: BWP 570.00

**Journal Entry:**
```
DR  Inventory (1200)          500.00
DR  VAT Receivable (1160)      70.00
    CR  Accounts Payable (2010)      570.00
```

### Landed Costs (Duties/Customs VAT)

When landed costs (freight, customs duties, insurance) are added to purchases:

**Automatic Behavior:**
1. System uses **Account 1160 (VAT Receivable)** for landed cost VAT
2. Each landed cost item can have its own VAT account selection
3. Default auto-selects account 1160

**Example - Import Duties with VAT:**
- Customs Duty: BWP 200.00
- VAT on Duty (14%): BWP 28.00

**Journal Entry:**
```
DR  Inventory (1200)          200.00
DR  VAT Receivable (1160)      28.00
    CR  Accounts Payable (2010)      228.00
```

---

## VAT Reconciliation Process

### Creating a VAT Reconciliation Period

**Location:** http://localhost:8010/static/vat-reports.html

**Steps:**
1. Select date range (start date, end date) for the VAT period
2. Click "Create New Reconciliation"
3. System automatically:
   - Fetches all sales transactions in the period (VAT collected)
   - Fetches all purchase transactions in the period (VAT paid)
   - Calculates:
     - **VAT Collected (Output VAT)**: Sum of all VAT from sales
     - **VAT Paid (Input VAT)**: Sum of all VAT from purchases and landed costs
     - **Net VAT Liability**: VAT Collected - VAT Paid

**API Endpoint:** `POST /api/v1/vat/reconciliations`

**Example Reconciliation:**
```
Period: 2024-01-01 to 2024-01-31

VAT Collected (Sales):        BWP 15,400.00  (from account 2132)
VAT Paid (Purchases):         BWP  8,200.00  (from account 1160)
                              ───────────────
Net VAT Liability (Payable):  BWP  7,200.00  (to be paid to BURS)
```

### Verification Checklist

Before submitting a VAT reconciliation, the system requires verification of:

1. ✓ All sales invoices recorded with correct VAT
2. ✓ All purchase invoices recorded with correct VAT
3. ✓ VAT rates applied correctly (14%)
4. ✓ Supporting documentation available (invoices, receipts)
5. ✓ Cross-checked with bank statements

**Status Changes:**
- `draft` → User is creating the reconciliation
- `calculated` → System has calculated VAT amounts
- `reconciled` → User has verified and approved the reconciliation
- `submitted` → VAT return submitted to tax authority (BURS)
- `approved` → Tax authority has approved the return
- `paid` → VAT payment/refund has been completed

---

## VAT Settlement & Payment

### Scenario 1: VAT Payment (Output > Input)

**When:** Output VAT (from sales) > Input VAT (from purchases)
**Result:** Business owes VAT to tax authority

**Recording Payment:**
1. Go to VAT Reconciliations table
2. Click "Record Payment" for the reconciliation period
3. Enter:
   - Payment amount (defaults to outstanding balance)
   - Payment date
   - Payment method (Bank Transfer, EFT, Cheque, Cash, Online)
   - Reference number
   - Bank account (for payment)
   - Notes

**API Endpoint:** `POST /api/v1/vat/payments`

**Automatic Journal Entries Created:**

The system creates a **VAT Settlement Entry** that:
1. Clears the Output VAT liability (account 2132)
2. Clears the Input VAT asset (account 1160)
3. Records the net payment to tax authority

**Example:**
```
Reconciliation Summary:
- VAT Collected (Output): BWP 15,400.00
- VAT Paid (Input):       BWP  8,200.00
- Net Payable:            BWP  7,200.00

Journal Entry (Book: VAT_SETTLEMENT):
────────────────────────────────────────────────────────────────────
Date: 2024-02-15
Particulars: VAT Settlement & Payment to Tax Authority
             (Output: 15,400.00, Input: 8,200.00, Net: 7,200.00)

DR  VAT Payable (2132)            15,400.00    [Clear Output VAT]
    CR  VAT Receivable (1160)              8,200.00   [Clear Input VAT]
    CR  Bank Account (1011)                7,200.00   [Net payment to BURS]
────────────────────────────────────────────────────────────────────
Total Debits:  15,400.00
Total Credits: 15,400.00  ✓ Balanced
```

**Effect on Accounts:**
- Account 2132 (VAT Payable): Reduced to zero (liability cleared)
- Account 1160 (VAT Receivable): Reduced to zero (asset cleared)
- Bank Account: Reduced by net payment (BWP 7,200.00)

### Scenario 2: VAT Refund (Input > Output)

**When:** Input VAT (from purchases) > Output VAT (from sales)
**Result:** Business is owed a refund from tax authority

This can occur when:
- Heavy purchasing period with low sales
- Export sales (zero-rated)
- Purchase of capital equipment with high VAT
- Start-up phase with initial inventory purchases

**Recording Refund:**
1. Go to VAT Reconciliations table
2. Click "Record Payment" (same process, but amount will be negative)
3. System automatically detects this is a refund scenario
4. Enter refund details (same fields as payment)

**Automatic Journal Entries Created:**

**Example:**
```
Reconciliation Summary:
- VAT Collected (Output): BWP  3,500.00
- VAT Paid (Input):       BWP 12,000.00
- Net Receivable:         BWP  8,500.00  (negative liability = asset)

Journal Entry (Book: VAT_REFUND):
────────────────────────────────────────────────────────────────────
Date: 2024-02-20
Particulars: VAT Refund from Tax Authority
             (Input: 12,000.00, Output: 3,500.00, Net Refund: 8,500.00)

DR  Bank Account (1011)            8,500.00   [Refund received]
DR  VAT Payable (2132)             3,500.00   [Clear Output VAT]
    CR  VAT Receivable (1160)             12,000.00  [Clear Input VAT]
────────────────────────────────────────────────────────────────────
Total Debits:  12,000.00
Total Credits: 12,000.00  ✓ Balanced
```

**Effect on Accounts:**
- Account 2132 (VAT Payable): Reduced to zero
- Account 1160 (VAT Receivable): Reduced to zero
- Bank Account: Increased by refund (BWP 8,500.00)

---

## VAT Reporting

### Available Reports

1. **VAT Summary Report**
   - Shows total VAT collected, VAT paid, and net liability
   - Filter by date range and branch
   - Displays pie chart and trend analysis

2. **Detailed VAT Transactions Report**
   - Lists all individual transactions with VAT
   - Shows invoice numbers, dates, amounts, VAT amounts
   - Separates sales (output VAT) and purchases (input VAT)

3. **VAT Reconciliations Report**
   - Lists all reconciliation periods
   - Shows status, due dates, payment status
   - Outstanding amounts
   - Action buttons for workflow

4. **Compliance Report**
   - VAT return checklist
   - Filing deadlines (21 days after period end)
   - Overdue reconciliations highlighted

### VAT Return Data

**API Endpoint:** `GET /api/v1/vat/return-data?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`

Returns official VAT return data formatted for tax authority submission:
- Total sales (including VAT)
- VAT-exclusive sales
- Output VAT
- Total purchases (including VAT)
- VAT-exclusive purchases
- Input VAT
- Net VAT liability/receivable
- Period dates
- Filing deadline

---

## Payment Status Tracking

The system tracks payment status for each reconciliation:

| Status | Description | Outstanding Amount |
|--------|-------------|-------------------|
| `unpaid` | No payments recorded | Full net liability |
| `partial` | Some payments made | Reduced balance |
| `paid` | Fully paid/refunded | Zero or negligible (< BWP 0.01) |
| `overpaid` | Payment > liability | Negative outstanding |

**Auto-updates when:**
- Payment is recorded
- Refund is received
- Reconciliation is adjusted

---

## Due Date Calculation

**Botswana VAT Law:**
- VAT returns must be filed within **21 days** after the end of the tax period
- System automatically calculates: `Due Date = Period End Date + 21 days`
- Overdue reconciliations are highlighted in yellow on the reports page

---

## Integration Points

### Frontend Components

**File:** `app/static/vat-reports.html`

**Key Functions:**
- `createNewReconciliation()` - Create new VAT period
- `performReconciliation()` - Load reconciliation for verification
- `showReconciliationModal()` - Display verification checklist
- `confirmReconciliation()` - Mark as reconciled
- `submitVatReturn()` - Submit to tax authority
- `recordVatPayment()` - Show payment modal
- `saveVatPayment()` - Save payment and create journal entries
- `viewReconciliationDetails()` - View full reconciliation details

### Backend Services

**VAT Service:** `app/services/vat_service.py`
- Basic VAT calculations and queries

**Enhanced VAT Service:** `app/services/enhanced_vat_service.py`
- Advanced VAT calculations from actual sales/purchase data
- VAT breakdown by rate
- VAT transaction details
- Account validation

**IFRS Accounting Service:** `app/services/ifrs_accounting_service.py`
- `create_tax_payment_journal_entries()` - VAT payment settlement
- `create_vat_refund_journal_entries()` - VAT refund settlement
- IFRS compliance validation

### API Endpoints

**File:** `app/api/v1/endpoints/vat.py`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/vat/summary` | GET | VAT summary with output/input/net |
| `/api/v1/vat/breakdown` | GET | VAT breakdown by rate |
| `/api/v1/vat/transactions` | GET | Detailed transaction list |
| `/api/v1/vat/return-data` | GET | Official VAT return data |
| `/api/v1/vat/reconciliations` | GET | List all reconciliations |
| `/api/v1/vat/reconciliations` | POST | Create new reconciliation |
| `/api/v1/vat/reconciliations/{id}` | PUT | Update reconciliation status |
| `/api/v1/vat/payments` | GET | List VAT payments |
| `/api/v1/vat/payments` | POST | Record payment/refund |
| `/api/v1/vat/items` | GET | Reconciliation items |

---

## Database Schema

### `vat_reconciliations` Table
```sql
id                  STRING (UUID)
period_start        DATE
period_end          DATE
description         TEXT
vat_collected       NUMERIC(10,2)    -- Output VAT from sales
vat_paid            NUMERIC(10,2)    -- Input VAT from purchases
net_vat_liability   NUMERIC(10,2)    -- vat_collected - vat_paid
status              STRING           -- draft, calculated, reconciled, submitted, paid
vat_rate            NUMERIC(5,2)     -- Default 14.0
branch_id           STRING
calculated_at       DATETIME
submitted_at        DATETIME
paid_at             DATETIME
total_payments      NUMERIC(12,2)
outstanding_amount  NUMERIC(12,2)
payment_status      STRING           -- unpaid, partial, paid, overpaid
last_payment_date   DATE
```

### `vat_payments` Table
```sql
id                      STRING (UUID)
vat_reconciliation_id   STRING (FK)
amount_paid             NUMERIC(12,2)
payment_date            DATE
payment_time            DATETIME
payment_method          STRING          -- bank_transfer, EFT, cheque, cash, online
reference_number        STRING
bank_account_id         STRING (FK)
bank_details            TEXT
notes                   TEXT
payment_status          STRING          -- completed, pending, cancelled
penalty_amount          NUMERIC(10,2)
interest_amount         NUMERIC(10,2)
total_amount            NUMERIC(12,2)
tax_authority           STRING          -- Default: BURS
created_by              STRING
approved_by             STRING
approved_at             DATETIME
```

### `vat_reconciliation_items` Table
```sql
id                      STRING (UUID)
vat_reconciliation_id   STRING (FK)
item_type               STRING          -- sale, purchase, landed_cost
reference_type          STRING          -- sale_id, purchase_id, etc.
reference_id            STRING
description             TEXT
vat_amount              NUMERIC(10,2)
vat_rate                NUMERIC(5,2)
transaction_date        DATE
branch_id               STRING
```

---

## Best Practices

### 1. Monthly Reconciliation
- Create a new VAT reconciliation at the end of each month
- Verify all transactions before submission
- Submit VAT return to BURS within 21 days

### 2. Record Keeping
- Keep all sales invoices, receipts, and till tapes
- Keep all purchase invoices and proof of payment
- Maintain bank statements showing VAT payments
- Store documentation for at least 5 years (Botswana requirement)

### 3. Verification Process
Always complete the verification checklist:
- ✓ All sales invoices recorded with correct VAT
- ✓ All purchase invoices recorded with correct VAT
- ✓ VAT rates applied correctly (14%)
- ✓ Supporting documentation available
- ✓ Cross-checked with bank statements

### 4. Prompt Payment
- Pay VAT within the 21-day deadline to avoid penalties
- Interest and penalties are automatically calculated for late payments
- Record payment immediately after making it

### 5. Journal Entry Review
After recording VAT payment/refund:
1. Go to Journal Entries (Accounting → Journal Entries)
2. Filter by Book: "VAT_SETTLEMENT" or "VAT_REFUND"
3. Verify journal entries are balanced
4. Check that VAT accounts (1160, 2132) are properly cleared

### 6. Account Balance Verification
After VAT settlement, verify:
- Account 2132 (VAT Payable) balance should be zero or minimal
- Account 1160 (VAT Receivable) balance should be zero or minimal
- Any remaining balance indicates incomplete reconciliation

---

## Troubleshooting

### Issue: VAT accounts not auto-selected

**Cause:** Account codes 1160 or 2132 don't exist in chart of accounts

**Solution:**
1. Go to Chart of Accounts
2. Verify accounts exist:
   - 1160: VAT Receivable (Input VAT)
   - 2132: VAT Payable (Output VAT)
3. If missing, run seed script: `scripts/seeds/seed_accounts.py`

### Issue: Journal entries not balanced

**Cause:** Rounding errors or incorrect VAT amounts

**Solution:**
1. System allows 1 cent rounding difference (BWP 0.01)
2. Check `net_vat_liability = vat_collected - vat_paid`
3. Ensure payment amount matches net liability
4. Review transaction VAT calculations

### Issue: Wrong VAT amount in reconciliation

**Cause:** Missing transactions or incorrect date filters

**Solution:**
1. Verify date range includes all transactions
2. Check that all sales/purchases are posted (not draft)
3. Ensure branch filter is correct (or set to "All Branches")
4. Review detailed transactions report

### Issue: Cannot create journal entries

**Cause:** Missing accounting codes or bank account setup

**Solution:**
1. Verify accounts 1160, 2132 exist
2. Ensure bank account has `accounting_code_id` set
3. Check that user has permissions
4. Review error logs for specific missing codes

---

## Summary

The VAT reconciliation and settlement system provides:

✅ **Automatic VAT Collection:** Sales/purchases auto-select correct VAT accounts
✅ **Comprehensive Reconciliation:** Period-based VAT calculation and verification
✅ **IFRS-Compliant Journal Entries:** Proper double-entry accounting for VAT settlement
✅ **Both Payment and Refund Scenarios:** Handles all VAT situations
✅ **Payment Tracking:** Real-time status updates and outstanding amounts
✅ **Compliance Support:** Due date calculations, verification checklists, audit trail
✅ **Complete Integration:** Seamless flow from transaction → reconciliation → payment → general ledger

The system ensures that:
- All VAT is properly recorded at the transaction level
- VAT reconciliations are accurate and verifiable
- Journal entries follow IFRS double-entry accounting principles
- Both VAT Payable and VAT Receivable are properly cleared during settlement
- Tax authority payments/refunds are correctly recorded
- Full audit trail is maintained for compliance

For support or questions, refer to:
- VAT Integration Guide: `docs/vat-integration-guide.md`
- VAT Account Setup: `docs/vat-accounts-setup.md`
- Landed Cost VAT: `docs/landed-cost-vat-verification.md`
