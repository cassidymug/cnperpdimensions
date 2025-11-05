# Accounting Codes & Chart of Accounts Guide

## Overview
This comprehensive guide covers setting up and managing your Chart of Accounts, accounting codes, sub-accounts, and IFRS compliance in the CNPERP ERP system.

## Table of Contents
1. [Understanding Chart of Accounts](#understanding-chart-of-accounts)
2. [Account Types & Classification](#account-types--classification)
3. [Setting Up Accounting Codes](#setting-up-accounting-codes)
4. [Managing Sub-Accounts](#managing-sub-accounts)
5. [IFRS Compliance](#ifrs-compliance)
6. [VAT Account Configuration](#vat-account-configuration)
7. [Journal Entries](#journal-entries)
8. [Best Practices](#best-practices)

---

## Understanding Chart of Accounts

### What is a Chart of Accounts?

The Chart of Accounts (COA) is the foundation of your accounting system. It's a complete listing of all accounts used to record financial transactions.

### Account Structure

```
Account Code Format: XXX-XXX-XX
                     │   │   │
                     │   │   └── Sub-account number
                     │   └────── Account number
                     └────────── Account type code
```

### Account Hierarchy

```
Assets (100-199)
├── Current Assets (100-149)
│   ├── Cash & Bank (100-109)
│   ├── Accounts Receivable (110-119)
│   └── Inventory (120-129)
└── Fixed Assets (150-199)
    ├── Property (150-159)
    └── Equipment (160-169)

Liabilities (200-299)
├── Current Liabilities (200-249)
└── Long-term Liabilities (250-299)

Equity (300-399)
Revenue (400-499)
Expenses (500-699)
```

---

## Account Types & Classification

### Main Account Types

#### 1. Assets
**Debit increases, Credit decreases**

- **Current Assets**: Converted to cash within 1 year
  - Cash and Cash Equivalents
  - Accounts Receivable
  - Inventory
  - Prepaid Expenses

- **Fixed Assets**: Long-term assets
  - Land
  - Buildings
  - Equipment
  - Vehicles
  - Accumulated Depreciation (contra-asset)

#### 2. Liabilities
**Credit increases, Debit decreases**

- **Current Liabilities**: Due within 1 year
  - Accounts Payable
  - Short-term Loans
  - Accrued Expenses
  - VAT Payable

- **Long-term Liabilities**: Due after 1 year
  - Long-term Loans
  - Bonds Payable
  - Mortgage Payable

#### 3. Equity
**Credit increases, Debit decreases**

- Owner's Equity
- Retained Earnings
- Common Stock
- Additional Paid-in Capital

#### 4. Revenue
**Credit increases, Debit decreases**

- Sales Revenue
- Service Revenue
- Interest Income
- Other Income

#### 5. Expenses
**Debit increases, Credit decreases**

- Cost of Goods Sold
- Operating Expenses
- Administrative Expenses
- Marketing Expenses

---

## Setting Up Accounting Codes

### Step 1: Access Chart of Accounts

1. Navigate to **Accounting → Chart of Accounts**
2. Review existing accounts (if system was seeded)
3. Click **"Add Account"** to create new accounts

### Step 2: Create Parent Account

```
Account Details:
├── Account Code: 100
├── Account Name: Current Assets
├── Account Type: Asset
├── Sub-type: Current Asset
├── Is Header: Yes (this is a parent account)
├── Parent Account: None
└── Description: Assets expected to be converted to cash within one year
```

### Step 3: Create Child Accounts

```
Account Details:
├── Account Code: 100-001
├── Account Name: Cash on Hand
├── Account Type: Asset
├── Sub-type: Cash
├── Is Header: No
├── Parent Account: 100 - Current Assets
├── Currency: BWP
├── Allow Direct Posting: Yes
└── Description: Physical cash in tills and safe
```

### Account Configuration Options

- **Allow Direct Posting**: Can transactions be posted directly?
- **Require Sub-accounts**: Must use sub-accounts?
- **Is Control Account**: Controls sub-ledger?
- **Is Bank Account**: Links to banking module?
- **Is VAT Account**: Used for VAT calculations?

### Standard Account Setup

#### Cash Accounts
```
100-001 | Cash on Hand - HQ
100-002 | Cash on Hand - Branch 1
100-003 | Petty Cash
100-010 | Bank - Standard Bank Checking
100-011 | Bank - Standard Bank Savings
```

#### Receivables
```
110-001 | Accounts Receivable - Trade
110-002 | Accounts Receivable - Other
110-010 | Allowance for Doubtful Debts (contra)
```

#### Inventory
```
120-001 | Inventory - Raw Materials
120-002 | Inventory - Work in Progress
120-003 | Inventory - Finished Goods
120-004 | Inventory - Consignment
```

#### Payables
```
200-001 | Accounts Payable - Trade
200-002 | Accounts Payable - Other
200-010 | Accrued Expenses
200-020 | VAT Payable
```

---

## Managing Sub-Accounts

### What are Sub-Accounts?

Sub-accounts provide detailed tracking under a parent account. For example:

```
110 - Accounts Receivable (Parent/Control Account)
├── 110-C001 - Customer A
├── 110-C002 - Customer B
└── 110-C003 - Customer C
```

### Creating Sub-Accounts

1. **Navigate to Chart of Accounts**
2. **Find Parent Account**
3. **Click "Add Sub-Account"**
4. **Fill Details:**
   ```
   Sub-Account Code: C001
   Full Code: 110-C001
   Name: Customer A - Receivables
   Parent: 110 - Accounts Receivable
   ```

### Sub-Account Types

#### Customer Sub-Accounts
Track individual customer balances:
```
110-C001 | ABC Company
110-C002 | XYZ Corporation
110-C003 | John's Store
```

#### Supplier Sub-Accounts
Track individual supplier balances:
```
200-S001 | Supplier Alpha
200-S002 | Supplier Beta
200-S003 | Supplier Gamma
```

#### Expense Sub-Accounts
Detailed expense tracking:
```
500-001 | Salaries & Wages
├── 500-001-01 | Management Salaries
├── 500-001-02 | Staff Salaries
├── 500-001-03 | Overtime
└── 500-001-04 | Bonuses
```

### Sub-Account Reconciliation

**Monthly Reconciliation Process:**
1. Generate sub-ledger report
2. Compare to control account balance
3. Investigate discrepancies
4. Post adjusting entries if needed
5. Document reconciliation

---

## IFRS Compliance

### IFRS Account Tagging

Tag accounts according to IFRS standards:

1. **Navigate to Account**
2. **Click "IFRS Settings"**
3. **Select IFRS Category:**
   - Financial Assets
   - Non-financial Assets
   - Financial Liabilities
   - Non-financial Liabilities
   - Equity
   - Revenue
   - Expenses

4. **Select IFRS Sub-category:**
   - For Assets: Current/Non-current
   - For Liabilities: Current/Non-current
   - For Revenue: Operating/Non-operating

### IFRS Financial Statements

The system generates IFRS-compliant reports:

- **Statement of Financial Position** (Balance Sheet)
- **Statement of Profit or Loss**
- **Statement of Changes in Equity**
- **Statement of Cash Flows**
- **Notes to Financial Statements**

### IFRS Account Examples

```python
# Asset Accounts
100-001 | Cash | IFRS: Financial Asset - Current
100-010 | Bank | IFRS: Financial Asset - Current
120-001 | Inventory | IFRS: Non-financial Asset - Current
150-001 | Buildings | IFRS: Non-financial Asset - Non-current

# Liability Accounts
200-001 | Payables | IFRS: Financial Liability - Current
250-001 | Long-term Loan | IFRS: Financial Liability - Non-current

# Revenue Accounts
400-001 | Sales Revenue | IFRS: Revenue - Operating
400-100 | Interest Income | IFRS: Revenue - Non-operating
```

---

## VAT Account Configuration

### Setting Up VAT Accounts

#### 1. VAT Output (Sales Tax Collected)
```
Account Code: 200-020
Account Name: VAT Output Payable
Account Type: Liability
Is VAT Account: Yes
VAT Type: Output
Default VAT Rate: 14%
```

#### 2. VAT Input (Purchase Tax Paid)
```
Account Code: 110-020
Account Name: VAT Input Recoverable
Account Type: Asset
Is VAT Account: Yes
VAT Type: Input
```

#### 3. VAT Liability
```
Account Code: 200-021
Account Name: VAT Liability
Account Type: Liability
Is VAT Account: Yes
VAT Type: Liability
```

### Automatic VAT Account Selection

The system automatically selects VAT accounts based on:
1. Transaction type (Sale/Purchase)
2. Product VAT settings
3. Customer/Supplier VAT status
4. Branch location

### VAT Reconciliation

**Monthly VAT Return Process:**

1. **Generate VAT Report**
   - Go to Reports → VAT Reports
   - Select period
   - Review transactions

2. **Calculate VAT Due**
   ```
   VAT Output (collected): R 14,000
   VAT Input (paid):      R  8,000
   ────────────────────────────────
   VAT Payable:           R  6,000
   ```

3. **Post VAT Payment**
   ```
   Debit:  VAT Liability     R 6,000
   Credit: Bank              R 6,000
   ```

---

## Journal Entries

### Understanding Journal Entries

Every financial transaction is recorded through journal entries following double-entry bookkeeping:
- **Debit = Credit** (always balanced)
- Each entry has at least two lines
- Posted to General Ledger

### Creating Journal Entries

1. **Navigate to Accounting → Journal Entries**
2. **Click "New Journal Entry"**
3. **Fill Header:**
   ```
   Date: 2025-10-15
   Reference: JE-2025-001
   Description: Record office supplies purchase
   ```

4. **Add Lines:**
   ```
   Line 1:
   Account: 500-010 | Office Supplies
   Debit: 1,500.00
   Credit: 0.00
   
   Line 2:
   Account: 100-010 | Bank - Checking
   Debit: 0.00
   Credit: 1,500.00
   ```

5. **Verify Balance**
6. **Post Entry**

### Common Journal Entry Types

#### 1. Cash Sale
```
Debit:  Cash               R 1,000
Credit: Sales Revenue      R   877
Credit: VAT Output         R   123
```

#### 2. Credit Purchase
```
Debit:  Inventory         R 5,000
Debit:  VAT Input         R   700
Credit: Accounts Payable  R 5,700
```

#### 3. Depreciation
```
Debit:  Depreciation Expense    R 1,200
Credit: Accumulated Depreciation R 1,200
```

#### 4. Month-end Accruals
```
Debit:  Expense Account   R 3,000
Credit: Accrued Expenses  R 3,000
```

### Reversing Entries

For accruals that need to be reversed:
1. Find original entry
2. Click "Create Reversing Entry"
3. System creates opposite entry
4. Post reversal

---

## Best Practices

### Account Naming Conventions

✅ **DO:**
- Use clear, descriptive names
- Be consistent with terminology
- Include location/branch if needed
- Use standard abbreviations

❌ **DON'T:**
- Use ambiguous names
- Create duplicate accounts
- Use special characters
- Make names too long

### Account Organization

1. **Group Related Accounts**
   - Keep similar accounts together
   - Use sequential numbering

2. **Maintain Hierarchy**
   - Clear parent-child relationships
   - Logical grouping

3. **Document Everything**
   - Add descriptions to accounts
   - Document special rules
   - Keep update log

### Regular Maintenance

**Monthly Tasks:**
- ✅ Reconcile all bank accounts
- ✅ Review aged receivables
- ✅ Review aged payables
- ✅ Post depreciation
- ✅ Reconcile inventory

**Quarterly Tasks:**
- ✅ Full general ledger review
- ✅ Clean up old transactions
- ✅ Archive old data
- ✅ Update account descriptions

**Annual Tasks:**
- ✅ Year-end closing
- ✅ Review COA structure
- ✅ Archive prior year
- ✅ Tax filing

### Security & Controls

1. **Segregation of Duties**
   - Different users for data entry vs approval
   - Separate cash handling from recording

2. **Approval Workflows**
   - Journal entries need approval
   - Large transactions require manager sign-off

3. **Audit Trail**
   - All changes logged
   - Who, what, when recorded
   - Cannot delete posted entries

---

## Troubleshooting

### Common Issues

**Issue: Account balance doesn't match**
- Run trial balance
- Check for unposted entries
- Verify all entries are balanced
- Review audit log for changes

**Issue: Cannot delete account**
- Account has transactions
- Account has sub-accounts
- Account is used as default
- Archive instead of delete

**Issue: VAT not calculating**
- Check VAT account setup
- Verify product VAT settings
- Confirm customer VAT status
- Review VAT configuration

---

## Related Documentation
- [Banking Configuration Guide](banking-guide.md)
- [Journal Entry Procedures](journal-entry-guide.md)
- [VAT Setup Guide](vat-guide.md)
- [Financial Reporting](reporting-guide.md)
