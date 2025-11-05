# Banking & Reconciliation Guide

## Overview
This guide covers setting up and managing bank accounts, transactions, transfers, and reconciliations in the CNPERP ERP system.

## Table of Contents
1. [Bank Account Setup](#bank-account-setup)
2. [Bank Transactions](#bank-transactions)
3. [Bank Transfers](#bank-transfers)
4. [Bank Reconciliation](#bank-reconciliation)
5. [Payment Processing](#payment-processing)
6. [Multi-Currency Banking](#multi-currency-banking)
7. [Reporting](#reporting)

---

## Bank Account Setup

### Creating a Bank Account

1. **Navigate to Banking → Bank Accounts**
2. **Click "Add Bank Account"**
3. **Fill in Details:**

```
Bank Information:
├── Bank Name: Standard Bank
├── Branch Name: Main Branch
├── Branch Code: 285267
├── Account Number: 1234567890
├── Account Type: Checking/Savings/Credit
├── Currency: BWP/USD/EUR
└── SWIFT Code: SBICBWGX (for international)

Accounting Integration:
├── GL Account: 100-010 (must be configured as bank account)
├── Default Branch: Head Office
└── Is Active: Yes

Opening Balance:
├── Opening Balance: P 50,000.00
├── Opening Date: 2025-01-01
└── Reference: Initial Setup
```

4. **Click "Save"**

### Bank Account Types

#### 1. Checking Account
- Daily operations
- High transaction volume
- Usually no interest
- Immediate access

#### 2. Savings Account
- Interest-bearing
- Lower transaction volume
- Minimum balance requirements
- Regular deposits

#### 3. Credit Card
- Credit facility
- Monthly statements
- Interest on outstanding balance
- Credit limit tracking

#### 4. Loan Account
- Borrowed funds
- Repayment schedule
- Interest charges
- Principal tracking

### Linking to Chart of Accounts

Each bank account must link to a GL account:

1. **Create GL Account:**
   ```
   Account Code: 100-010
   Account Name: Bank - Standard Bank Checking
   Account Type: Asset
   Is Bank Account: ✓ Yes
   Allow Direct Posting: ✓ Yes
   Currency: BWP
   ```

2. **Link in Bank Account Setup:**
   - Select the GL account during bank account creation
   - System will use this for automatic postings

---

## Bank Transactions

### Recording Bank Deposits

1. **Navigate to Banking → Bank Transactions**
2. **Click "New Deposit"**
3. **Fill Details:**

```
Transaction Details:
├── Bank Account: Standard Bank Checking
├── Date: 2025-10-15
├── Amount: P 15,000.00
├── Reference: DEP-001
├── Description: Cash deposit from retail sales
└── Payment Method: Cash/Cheque/Transfer

Source Information:
├── From Account: Cash on Hand (100-001)
├── Customer: (optional)
└── Invoice: (if related to invoice payment)
```

4. **Post Transaction**

**Accounting Impact:**
```
Debit:  Bank - Standard Bank     P 15,000
Credit: Cash on Hand             P 15,000
```

### Recording Bank Withdrawals

```
Transaction Details:
├── Type: Withdrawal
├── Bank Account: Standard Bank Checking
├── Date: 2025-10-15
├── Amount: P 5,000.00
├── Reference: WD-001
├── Description: ATM withdrawal for petty cash
└── To Account: Petty Cash (100-003)
```

**Accounting Impact:**
```
Debit:  Petty Cash              P 5,000
Credit: Bank - Standard Bank    P 5,000
```

### Recording Bank Charges

```
Transaction Details:
├── Type: Bank Charge
├── Amount: P 45.00
├── Reference: Bank statement
├── Description: Monthly account fees
└── Expense Account: 500-025 (Bank Charges)
```

**Accounting Impact:**
```
Debit:  Bank Charges (Expense)  P 45
Credit: Bank Account            P 45
```

### Interest Income

```
Transaction Details:
├── Type: Interest Income
├── Amount: P 125.00
├── Reference: Bank statement
├── Description: Interest earned - October
└── Income Account: 400-050 (Interest Income)
```

**Accounting Impact:**
```
Debit:  Bank Account           P 125
Credit: Interest Income        P 125
```

---

## Bank Transfers

### Internal Transfer (Between Own Accounts)

1. **Navigate to Banking → Bank Transfers**
2. **Click "New Transfer"**
3. **Fill Details:**

```
Transfer Information:
├── From Account: Standard Bank Checking
├── To Account: Standard Bank Savings
├── Amount: P 20,000.00
├── Date: 2025-10-15
├── Reference: TRF-001
└── Description: Transfer to savings account
```

**Accounting Impact:**
```
Debit:  Bank - Savings Account   P 20,000
Credit: Bank - Checking Account  P 20,000
```

### Supplier Payment Transfer

```
Payment Details:
├── From Account: Standard Bank Checking
├── Amount: P 8,500.00
├── Supplier: ABC Suppliers
├── Reference: Payment for Inv-123
└── Payment Method: EFT/Cheque/Online

Accounting Details:
├── Clear Payable: Yes
├── Invoice: INV-123
├── Discount Taken: P 0.00
└── Withholding Tax: P 0.00
```

**Accounting Impact:**
```
Debit:  Accounts Payable - ABC  P 8,500
Credit: Bank Account            P 8,500
```

### Customer Receipt Transfer

```
Receipt Details:
├── From Customer: XYZ Company
├── Amount: P 12,000.00
├── To Account: Standard Bank Checking
├── Reference: Receipt-456
└── Payment Method: Bank Transfer

Allocation:
├── Invoice-789: P 10,000
├── Invoice-790: P  2,000
└── Total Applied: P 12,000
```

**Accounting Impact:**
```
Debit:  Bank Account              P 12,000
Credit: Accounts Receivable - XYZ P 12,000
```

---

## Bank Reconciliation

### Monthly Reconciliation Process

#### Step 1: Prepare

1. **Gather Documents:**
   - Bank statement for the month
   - List of outstanding checks
   - List of deposits in transit
   - Previous reconciliation

2. **Access Reconciliation:**
   - Navigate to Banking → Bank Reconciliations
   - Select bank account
   - Select statement period

#### Step 2: Enter Statement Details

```
Statement Information:
├── Statement Date: 2025-10-31
├── Opening Balance: P 45,230.50
├── Closing Balance: P 52,890.75
├── Statement Reference: OCT2025
└── Upload Statement PDF: (optional)
```

#### Step 3: Match Transactions

**The reconciliation screen shows:**
- **Left Side**: System transactions (from your records)
- **Right Side**: Bank statement items

**Matching Process:**
1. Check items that appear on both sides
2. System automatically marks matches
3. Manually match similar amounts
4. Note unmatched items

**Transaction Status:**
- ✅ **Matched**: Appears in both system and bank
- ⏳ **Outstanding**: In system but not on statement
- ❓ **Bank Only**: On statement but not in system

#### Step 4: Handle Discrepancies

**Outstanding Checks:**
```
Checks written but not yet cleared:
├── Check 1234 | P  2,500 | Dated Oct 28
├── Check 1235 | P  1,200 | Dated Oct 30
└── Check 1236 | P    450 | Dated Oct 31
```

**Deposits in Transit:**
```
Deposits made but not reflected:
├── Deposit Oct 31 | P 5,000 | After bank cutoff
```

**Bank Errors:**
```
Items on statement but not in our records:
├── Bank Charge | P 45.00 | Record as adjustment
├── Interest    | P 82.50 | Record as adjustment
└── NSF Fee     | P 25.00 | Record and contact customer
```

#### Step 5: Post Adjustments

**For items found on bank statement but not in system:**

1. Click "Create Adjustment"
2. Select transaction type
3. Fill details
4. Post to general ledger

**Example: Bank charges not recorded:**
```
Debit:  Bank Charges Expense  P 45.00
Credit: Bank Account          P 45.00
```

#### Step 6: Finalize Reconciliation

1. **Verify Balances Match:**
   ```
   System Balance:              P 50,340.25
   Add: Deposits in Transit     P  5,000.00
   Less: Outstanding Checks     P (4,150.00)
   ─────────────────────────────────────────
   Adjusted Balance:            P 51,190.25
   
   Bank Statement Balance:      P 51,190.25
   ─────────────────────────────────────────
   Difference:                  P      0.00 ✓
   ```

2. **Mark as Reconciled**
3. **Generate Reconciliation Report**
4. **Save for Audit Trail**

### Reconciliation Reports

**Standard Reconciliation Report:**
- Opening balances
- All transactions
- Outstanding items
- Adjustments
- Final reconciled balance

**Exception Report:**
- Old outstanding checks (90+ days)
- Large unmatched items
- Frequent adjustments

---

## Payment Processing

### Supplier Payments

**Batch Payment Process:**

1. **Navigate to Banking → Payment Run**
2. **Select Criteria:**
   ```
   Filter Options:
   ├── Supplier: All/Specific
   ├── Due Date: On or before [date]
   ├── Minimum Amount: P 0.00
   ├── Payment Method: EFT/Cheque
   └── Bank Account: Standard Bank Checking
   ```

3. **Review Invoices:**
   - System shows all due invoices
   - Select invoices to pay
   - Option to take discounts

4. **Generate Payments:**
   - Creates batch payment file
   - Posts accounting entries
   - Updates invoice statuses

5. **Export Payment File:**
   - For bank upload (CSV/XML)
   - Print cheques
   - Email remittances

### Customer Receipts

**Processing Customer Payment:**

1. **Navigate to Sales → Receipts**
2. **Click "New Receipt"**
3. **Enter Details:**
   ```
   Receipt Information:
   ├── Customer: ABC Company
   ├── Amount Received: P 15,000.00
   ├── Payment Date: 2025-10-15
   ├── Payment Method: Bank Transfer
   ├── Bank Account: Standard Bank Checking
   ├── Reference: Customer Ref-123
   └── Notes: Payment for multiple invoices
   ```

4. **Allocate to Invoices:**
   ```
   Invoice Selection:
   ├── INV-001 | P 8,000.00 | Full payment
   ├── INV-002 | P 5,000.00 | Full payment
   ├── INV-003 | P 2,000.00 | Partial payment
   └── Total:   P15,000.00
   ```

5. **Post Receipt**

---

## Multi-Currency Banking

### Setting Up Multi-Currency Accounts

```
Currency Account Setup:
├── Bank: Standard Bank
├── Account Number: 9876543210
├── Account Type: Forex Account
├── Base Currency: BWP
├── Foreign Currency: USD
└── GL Account: 100-015 (USD Bank Account)
```

### Exchange Rate Management

**Configure Exchange Rates:**
1. Go to Settings → Exchange Rates
2. Add rates for each currency
3. Update rates daily/weekly

```
Exchange Rate Example:
├── From Currency: USD
├── To Currency: BWP
├── Rate: 13.45
├── Effective Date: 2025-10-15
└── Source: Bank Rate
```

### Foreign Currency Transactions

**Recording USD Deposit:**
```
Transaction:
├── Amount in USD: $1,000.00
├── Exchange Rate: 13.45
├── Amount in BWP: P13,450.00
└── Post to both USD and BWP accounts
```

**Month-end Revaluation:**
- System revalues foreign currency accounts
- Posts unrealized gains/losses
- Adjusts to current exchange rate

---

## Reporting

### Standard Banking Reports

1. **Bank Balance Report**
   - Current balance by account
   - By branch/currency
   - Real-time or as-of date

2. **Transaction Listing**
   - All transactions by date range
   - Filter by account/type
   - Export to Excel/PDF

3. **Reconciliation History**
   - All past reconciliations
   - Status tracking
   - Outstanding items report

4. **Cash Flow Report**
   - Projected cash position
   - Receipts vs. payments
   - Daily/weekly/monthly view

5. **Payment Analysis**
   - Payments by supplier
   - Payment method analysis
   - Average payment period

### Custom Reports

Build custom reports using Report Builder:
- Select bank accounts
- Choose date ranges
- Add filters
- Group by various criteria
- Export in multiple formats

---

## Best Practices

### Daily Tasks
- ✅ Record all bank transactions
- ✅ Match online banking to system
- ✅ Verify payment processing
- ✅ Review pending items

### Weekly Tasks
- ✅ Download bank statements
- ✅ Review outstanding checks
- ✅ Follow up on old outstanding items
- ✅ Update exchange rates (if applicable)

### Monthly Tasks
- ✅ Complete bank reconciliation
- ✅ Review all bank accounts
- ✅ Archive bank statements
- ✅ Review bank charges
- ✅ Post any adjustments

### Security
- 🔒 Limit access to bank functions
- 🔒 Require approval for large transfers
- 🔒 Regular audit of bank transactions
- 🔒 Segregation of duties (entry vs. approval)
- 🔒 Secure storage of bank documents

---

## Troubleshooting

**Issue: Reconciliation won't balance**
- Check for duplicate entries
- Verify exchange rates (multi-currency)
- Look for reversed/deleted transactions
- Review all adjustments

**Issue: Transfer not showing**
- Verify both accounts updated
- Check posting date
- Review approval status
- Check for errors in log

**Issue: Cannot process payment**
- Verify sufficient balance
- Check account is active
- Verify GL account linked
- Check user permissions

---

## Related Documentation
- [Chart of Accounts Setup](accounting-codes-guide.md)
- [Supplier Payment Processing](supplier-guide.md)
- [Customer Receipt Management](customer-guide.md)
- [Financial Reporting](reporting-guide.md)
