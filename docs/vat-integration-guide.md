# VAT Integration Guide

## Overview

This guide documents the complete VAT (Value Added Tax) integration across the ERP system, covering POS (Point of Sale), Sales, and Purchases modules. The system now automatically selects the correct VAT accounts and processes VAT correctly for all transactions.

## VAT Account Structure

### Chart of Accounts - VAT Hierarchy

```
1000 Assets
└── 1100 Current Assets
    └── 1160 VAT Receivable (Input VAT) ← Used for purchases

2000 Liabilities
└── 2100 Current Liabilities
    └── 2130 Tax Liabilities
        └── 2131 VAT Control
            ├── 2132 VAT Payable (Output VAT) ← Used for sales
            └── 2133 VAT Receivable (Input VAT - Contra)
```

### Account Purposes

| Account Code | Account Name | Type | Purpose |
|-------------|-------------|------|---------|
| **1160** | VAT Receivable (Input VAT) | Asset | Records VAT paid on purchases and expenses (reclaimable from tax authorities) |
| **2132** | VAT Payable (Output VAT) | Liability | Records VAT collected on sales (payable to tax authorities) |
| **2131** | VAT Control | Liability (Group) | Parent account consolidating VAT sub-accounts for reporting |
| **2133** | VAT Receivable (Contra) | Liability | Alternative tracking for input VAT within liability section |

## Database Schema Changes

### New Fields Added

#### Sales Table
```sql
ALTER TABLE sales
ADD COLUMN output_vat_account_id VARCHAR(36)
REFERENCES accounting_codes(id);
```

#### Sale Items Table
```sql
ALTER TABLE sale_items
ADD COLUMN vat_account_id VARCHAR(36)
REFERENCES accounting_codes(id);
```

#### Purchases Table
```sql
ALTER TABLE purchases
ADD COLUMN input_vat_account_id VARCHAR(36)
REFERENCES accounting_codes(id);
```

#### Purchase Items Table
```sql
ALTER TABLE purchase_items
ADD COLUMN vat_account_id VARCHAR(36)
REFERENCES accounting_codes(id);
```

## Backend Integration

### 1. POS Service (`app/services/pos_service.py`)

**Automatic VAT Account Selection**:
When a sale is created through the POS system, the service automatically:
- Queries for account code `2132` (VAT Payable - Output VAT)
- Sets `sale.output_vat_account_id` if VAT amount > 0
- This account is used for all VAT journal entries

```python
# Get default Output VAT account (2132 - VAT Payable)
output_vat_account = None
if total_vat > 0:
    output_vat_account = self.db.query(AccountingCode).filter(
        AccountingCode.code == '2132'
    ).first()

sale = Sale(
    # ... other fields ...
    output_vat_account_id=output_vat_account.id if output_vat_account else None
)
```

### 2. Sales Service (`app/services/sales_service.py`)

**Automatic VAT Account Selection**:
Similar to POS, the sales service automatically selects account `2132` for VAT:

```python
# Get default Output VAT account (2132 - VAT Payable)
output_vat_account = None
if total_vat_amount > 0:
    output_vat_account = self.db.query(AccountingCode).filter(
        AccountingCode.code == '2132'
    ).first()

sale.output_vat_account_id = output_vat_account.id if output_vat_account else None
```

### 3. Purchase Service (`app/services/purchase_service.py`)

**Automatic VAT Account Selection**:
The purchase service automatically selects account `1160` for Input VAT:

```python
# Get default Input VAT account (1160 - VAT Receivable)
input_vat_account = None
if total_vat_amount > 0:
    input_vat_account = self.db.query(AccountingCode).filter(
        AccountingCode.code == '1160'
    ).first()

purchase.input_vat_account_id = input_vat_account.id if input_vat_account else None
```

### 4. IFRS Accounting Service (`app/services/ifrs_accounting_service.py`)

**Sales Journal Entries**:
The accounting service now uses the selected VAT account for journal entries with fallback logic:

```python
# Use the output VAT account from the sale if set
vat_account_code = None
if sale.output_vat_account_id:
    vat_account_code = self.db.query(AccountingCode).filter(
        AccountingCode.id == sale.output_vat_account_id
    ).first()

# Fallback to account 2132 (VAT Payable - Output VAT)
if not vat_account_code:
    vat_account_code = self.db.query(AccountingCode).filter(
        AccountingCode.code == '2132'
    ).first()

# Create VAT journal entry (Credit)
vat_entry = JournalEntry(
    accounting_code_id=vat_account_code.id,
    entry_type='credit',
    credit_amount=sale.total_vat_amount,
    description=f"VAT collected for sale..."
)
```

**Purchase Journal Entries**:
Similarly for purchases, the service uses account `1160` for Input VAT:

```python
# Use the input VAT account from the purchase if set
vat_account_code = None
if purchase.input_vat_account_id:
    vat_account_code = self.db.query(AccountingCode).filter(
        AccountingCode.id == purchase.input_vat_account_id
    ).first()

# Fallback to account 1160 (VAT Receivable - Input VAT)
if not vat_account_code:
    vat_account_code = self.db.query(AccountingCode).filter(
        AccountingCode.code == '1160'
    ).first()

# Create VAT journal entry (Debit)
vat_entry = JournalEntry(
    accounting_code_id=vat_account_code.id,
    entry_type='debit',
    debit_amount=purchase.total_vat_amount,
    description=f"Input VAT on purchase..."
)
```

## VAT Processing Flow

### Sales Transaction Flow

1. **Sale Created** (POS or Sales Module)
   - System calculates VAT amount based on vat_rate
   - Automatically queries and sets `output_vat_account_id` to account `2132`

2. **Journal Entries Created**
   ```
   DR  Cash/Bank/AR          (Total incl. VAT)
   CR  Sales Revenue         (Subtotal ex. VAT)
   CR  VAT Payable (2132)    (VAT amount)
   ```

3. **VAT Recorded**
   - VAT amount accumulates in account `2132` (VAT Payable - Output VAT)
   - Ready for periodic VAT return filing

### Purchase Transaction Flow

1. **Purchase Created**
   - System calculates VAT amount based on vat_rate and is_taxable flag
   - Automatically queries and sets `input_vat_account_id` to account `1160`

2. **Journal Entries Created**
   ```
   DR  Inventory/Assets      (Subtotal ex. VAT)
   DR  VAT Receivable (1160) (VAT amount)
   CR  Accounts Payable      (Total incl. VAT)
   ```

3. **VAT Recorded**
   - VAT amount accumulates in account `1160` (VAT Receivable - Input VAT)
   - Available for offset against Output VAT in VAT returns

## VAT Settlement Process

### Monthly/Quarterly VAT Return

At the end of each VAT period:

1. **Calculate Net VAT Position**:
   ```
   Net VAT Payable = Balance(2132) - Balance(1160)
   ```

2. **If Net Payable (Output > Input)**:
   ```
   DR  VAT Payable (2132)         XXX
   DR  VAT Receivable (1160)      YYY
   CR  VAT Control (2131)                 ZZZ
   CR  Cash/Bank                          Net
   ```

3. **If Net Refundable (Input > Output)**:
   ```
   DR  VAT Payable (2132)         XXX
   DR  VAT Control (2131)         ZZZ
   CR  VAT Receivable (1160)              YYY
   CR  Cash/Bank                          Net
   ```

## Frontend Integration Notes

### Existing Frontends

The system currently has the following frontend pages that support VAT:

1. **POS System** (`/static/pos.html`, `/static/pos_new.html`)
   - VAT calculated automatically per item
   - Uses default account `2132` automatically
   - No UI change needed (works behind the scenes)

2. **Sales Module** (`/static/sales.html`, `/static/sales_updated.html`)
   - VAT calculated on sale items
   - Uses default account `2132` automatically
   - Future enhancement: Add VAT account dropdown for override

3. **Purchases Module** (`/static/purchases.html`)
   - VAT calculated per purchase item
   - Uses default account `1160` automatically
   - Already has landed cost modal with VAT account selection
   - Landed costs can use `lcVatAccount` dropdown to override

### Future Frontend Enhancements

To allow users to manually override VAT accounts:

1. **Add VAT Account Dropdowns**:
   ```html
   <!-- For Sales/POS -->
   <select id="outputVatAccount">
     <option value="2132" selected>2132 - VAT Payable (Output VAT)</option>
     <option value="2133">2133 - VAT Receivable (Contra)</option>
   </select>

   <!-- For Purchases -->
   <select id="inputVatAccount">
     <option value="1160" selected>1160 - VAT Receivable (Input VAT)</option>
     <option value="2133">2133 - VAT Receivable (Contra)</option>
   </select>
   ```

2. **Populate Dropdowns**:
   ```javascript
   // Filter for Output VAT accounts (for sales)
   const outputVatAccounts = accountingCodes.filter(code =>
       code.code === '2132' || code.code === '2133' ||
       code.name.toLowerCase().includes('vat payable') ||
       code.name.toLowerCase().includes('output vat')
   );

   // Filter for Input VAT accounts (for purchases)
   const inputVatAccounts = accountingCodes.filter(code =>
       code.code === '1160' || code.code === '2133' ||
       code.name.toLowerCase().includes('vat receivable') ||
       code.name.toLowerCase().includes('input vat')
   );
   ```

## Migration Script

Location: `migrations/add_vat_accounts_to_transactions.py`

Run with:
```bash
python migrations/add_vat_accounts_to_transactions.py
```

Adds:
- ✓ sales.output_vat_account_id
- ✓ sale_items.vat_account_id
- ✓ purchases.input_vat_account_id
- ✓ purchase_items.vat_account_id

## Files Modified

### Models
1. `app/models/sales.py`
   - Added `output_vat_account_id` to Sale model
   - Added `vat_account_id` to SaleItem model
   - Added relationships

2. `app/models/purchases.py`
   - Added `input_vat_account_id` to Purchase model
   - Added `vat_account_id` to PurchaseItem model
   - Added relationships

### Services
3. `app/services/pos_service.py`
   - Auto-selects account `2132` for sales with VAT

4. `app/services/sales_service.py`
   - Auto-selects account `2132` for sales with VAT

5. `app/services/purchase_service.py`
   - Auto-selects account `1160` for purchases with VAT

6. `app/services/ifrs_accounting_service.py`
   - Updated `create_sale_journal_entries()` to use account `2132`
   - Updated `create_purchase_journal_entries()` to use account `1160`
   - Added fallback logic for account selection

### Migrations
7. `migrations/add_vat_accounts_to_transactions.py`
   - Database migration script

## Testing

### Test Sales Transaction

```python
# Create a sale via POS
sale_data = {
    'items': [
        {'product_id': 'xxx', 'quantity': 1, 'unit_price': '100', 'is_taxable': True}
    ],
    'payment_method': 'cash',
    'amount_tendered': '114',
    'vat_rate': '14'
}

# Expected Results:
# - sale.output_vat_account_id = ID of account 2132
# - sale.total_vat_amount = 14.00
# - Journal Entry: CR VAT Payable (2132) 14.00
```

### Test Purchase Transaction

```python
# Create a purchase
purchase_data = {
    'supplier_id': 'xxx',
    'purchase_date': '2025-10-25'
}

items = [
    {'product_id': 'yyy', 'quantity': 10, 'cost': '50', 'vat_rate': '14', 'is_taxable': True}
]

# Expected Results:
# - purchase.input_vat_account_id = ID of account 1160
# - purchase.total_vat_amount = 70.00
# - Journal Entry: DR VAT Receivable (1160) 70.00
```

### Verify Journal Entries

```sql
-- Check sales VAT entries
SELECT * FROM journal_entries
WHERE accounting_code_id = (SELECT id FROM accounting_codes WHERE code = '2132')
ORDER BY date DESC;

-- Check purchase VAT entries
SELECT * FROM journal_entries
WHERE accounting_code_id = (SELECT id FROM accounting_codes WHERE code = '1160')
ORDER BY date DESC;

-- Check VAT balances
SELECT
    code,
    name,
    (SELECT SUM(debit_amount - credit_amount)
     FROM journal_entries
     WHERE accounting_code_id = accounting_codes.id) as balance
FROM accounting_codes
WHERE code IN ('1160', '2132', '2131', '2133');
```

## Best Practices

1. **Always Use Correct VAT Rates**
   - Standard rate: 14% (Botswana)
   - Zero-rated: 0%
   - Exempt: Mark as `is_taxable = false`

2. **VAT Account Selection**
   - Sales/POS: Always use `2132` (Output VAT)
   - Purchases: Always use `1160` (Input VAT)
   - Landed Costs: Can use either depending on transaction type

3. **VAT Reconciliation**
   - Reconcile VAT accounts monthly
   - Ensure Output VAT (2132) balance matches sales records
   - Ensure Input VAT (1160) balance matches purchase records
   - Net position should equal tax authority filings

4. **Tax Exempt Transactions**
   - Set `is_taxable = false` for exempt items
   - VAT amount will be 0
   - No VAT journal entries created

## Troubleshooting

### Issue: VAT not being recorded

**Check**:
1. Is `total_vat_amount > 0`?
2. Does account `2132` or `1160` exist in accounting_codes?
3. Are journal entries being created?

**Solution**:
```bash
# Verify VAT accounts exist
python scripts/verify_vat_accounts.py

# Re-run seed if needed
python scripts/reseed_accounts.py
```

### Issue: Wrong VAT account used

**Check**:
1. What is `sale.output_vat_account_id` or `purchase.input_vat_account_id`?
2. Does the journal entry use the correct accounting_code_id?

**Solution**:
```sql
-- Update existing transactions
UPDATE sales
SET output_vat_account_id = (SELECT id FROM accounting_codes WHERE code = '2132')
WHERE total_vat_amount > 0 AND output_vat_account_id IS NULL;

UPDATE purchases
SET input_vat_account_id = (SELECT id FROM accounting_codes WHERE code = '1160')
WHERE total_vat_amount > 0 AND input_vat_account_id IS NULL;
```

## Summary

The VAT integration is now fully automated across all transaction types:

- ✅ **POS Sales**: Automatically use account `2132` (VAT Payable - Output VAT)
- ✅ **Sales**: Automatically use account `2132` (VAT Payable - Output VAT)
- ✅ **Purchases**: Automatically use account `1160` (VAT Receivable - Input VAT)
- ✅ **Journal Entries**: Automatically use correct VAT accounts with fallback logic
- ✅ **Database**: All necessary fields and relationships added
- ✅ **Migration**: Script available to update schema

The system now ensures proper VAT accounting for tax compliance and reporting.
