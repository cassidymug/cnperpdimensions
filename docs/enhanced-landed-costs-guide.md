# Enhanced Landed Costs with IFRS Tags & Dimensional Accounting

## Overview
Landed costs have been significantly enhanced to support proper accounting treatment with IFRS reporting tags, dimensional accounting, and detailed tracking of each cost component.

## What Was Added

### Landed Costs Header (`landed_costs` table)
**Dimensional Accounting:**
- `branch_id` - Branch where cost was incurred
- `cost_center_id` - Cost center allocation
- `project_id` - Project tracking
- `department_id` - Department responsibility

**Invoice/Receipt Tracking:**
- `invoice_number` - Main invoice/receipt number
- `supplier_invoice_date` - Date on supplier invoice
- `payment_due_date` - Payment due date

**Payment Management:**
- `paid_status` - Payment status (unpaid, partial, paid)
- `amount_paid` - Amount already paid
- `payment_account_id` - GL account used for payment

### Landed Cost Items (`landed_cost_items` table)
**Cost Classification:**
- `cost_type` - Type of cost: freight, insurance, duty, customs, tax, handling, storage, other
- `ifrs_tag` - IFRS reporting tag for financial statements

**GL Accounting:**
- `gl_account_id` - Specific GL account for this cost
- `vat_account_id` - VAT GL account if taxable

**Dimensional Accounting (Line Level):**
- `cost_center_id` - Cost center (can override header)
- `project_id` - Project (can override header)
- `department_id` - Department (can override header)

**Document Tracking (Per Cost):**
- `invoice_number` - Specific invoice for this cost (e.g., customs duty invoice)
- `invoice_date` - Date on this specific invoice
- `reference_number` - Reference (e.g., customs declaration number)

**Tax Treatment:**
- `tax_rate` - Tax rate if applicable
- `is_taxable` - Whether VAT applies
- `vat_amount` - VAT amount

**Allocation:**
- `allocated_to_inventory` - Whether allocated to inventory cost
- `notes` - Additional notes

## IFRS Tag Examples

### Common IFRS Tags for Landed Costs:

**Import Duties & Customs:**
- **A2.1** - Add to inventory cost (capitalized)
- Tag: `A2.1` (Inventory - Raw Materials)

**Freight/Shipping:**
- **A2.1** - If capitalized into inventory
- **E1** - If expensed as operating cost
- Tag depends on accounting policy

**Insurance:**
- **E1** - Operating expense
- **A2.1** - If part of inventory cost
- Tag: `E1` (Operating Expenses)

**Customs Taxes:**
- **E3** - Tax expense
- Tag: `E3` (Taxes)

**Handling & Storage:**
- **E1** - Operating expense
- Tag: `E1` (Operating Expenses)

## Example: Purchase with Detailed Landed Costs

```json
{
  "purchase_id": "abc-123",
  "supplier_id": "xyz-789",
  "date": "2025-10-25",
  "total_amount": 26750.00,
  "branch_id": "branch-hq",
  "cost_center_id": "cc-procurement",
  "invoice_number": "LC-2025-001",
  "supplier_invoice_date": "2025-10-25",
  "payment_due_date": "2025-11-10",
  "paid_status": "unpaid",
  "items": [
    {
      "description": "Import Duty - Computers",
      "amount": 20250.00,
      "cost_type": "duty",
      "ifrs_tag": "A2.1",
      "gl_account_id": "acc-1144",
      "cost_center_id": "cc-procurement",
      "invoice_number": "CUSTOMS-2025-4173907",
      "invoice_date": "2025-10-24",
      "reference_number": "DECL-2025-10-24-001",
      "tax_rate": 0.0,
      "is_taxable": false,
      "allocated_to_inventory": true,
      "notes": "20% import duty on computers"
    },
    {
      "description": "Courier Fees",
      "amount": 3500.00,
      "cost_type": "freight",
      "ifrs_tag": "A2.1",
      "gl_account_id": "acc-1144",
      "cost_center_id": "cc-procurement",
      "invoice_number": "DHL-INV-789456",
      "invoice_date": "2025-10-24",
      "tax_rate": 14.0,
      "is_taxable": true,
      "vat_amount": 490.00,
      "vat_account_id": "acc-1161",
      "allocated_to_inventory": true,
      "notes": "International courier"
    },
    {
      "description": "Customs Processing Fee",
      "amount": 2500.00,
      "cost_type": "customs",
      "ifrs_tag": "E3",
      "gl_account_id": "acc-5120",
      "cost_center_id": "cc-procurement",
      "invoice_number": "CUSTOMS-FEE-001",
      "invoice_date": "2025-10-24",
      "tax_rate": 0.0,
      "is_taxable": false,
      "allocated_to_inventory": false,
      "notes": "Government processing fee"
    },
    {
      "description": "Insurance",
      "amount": 500.00,
      "cost_type": "insurance",
      "ifrs_tag": "E1",
      "gl_account_id": "acc-5110",
      "cost_center_id": "cc-procurement",
      "invoice_number": "INSURE-2025-123",
      "invoice_date": "2025-10-23",
      "tax_rate": 14.0,
      "is_taxable": true,
      "vat_amount": 70.00,
      "vat_account_id": "acc-1161",
      "allocated_to_inventory": false,
      "notes": "Cargo insurance"
    }
  ]
}
```

## Cost Type Options

| Cost Type | Description | Typical IFRS Tag | Capitalize to Inventory? |
|-----------|-------------|------------------|--------------------------|
| `duty` | Import duties | A2.1 | Usually YES |
| `customs` | Customs fees | E3 or A2.1 | Depends on policy |
| `freight` | Shipping/courier | A2.1 or E1 | Depends on policy |
| `insurance` | Cargo insurance | A2.1 or E1 | Depends on policy |
| `tax` | Other taxes | E3 | Usually NO |
| `handling` | Handling fees | E1 | Usually NO |
| `storage` | Storage fees | E1 | Usually NO |
| `other` | Miscellaneous | Varies | Depends on nature |

## Accounting Treatment

### Option 1: Capitalize to Inventory (A2.1)
Costs that increase the inventory value:
- Import duties (always)
- Freight to get goods to location
- Insurance during transit
- Necessary handling to make goods saleable

**Journal Entry:**
```
Dr. Inventory (1144)           26,750
    Cr. Accounts Payable (2110)        26,750
```

### Option 2: Expense Immediately (E1 or E3)
Costs that don't add value to inventory:
- Government fees not related to value (E3)
- Optional insurance (E1)
- Storage after receipt (E1)
- Penalties or fines (E3)

**Journal Entry:**
```
Dr. Operating Expense (5xxx)   2,500
    Cr. Accounts Payable (2110)       2,500
```

## Best Practices

1. **Always Tag Duties** - Use IFRS tag A2.1 for import duties
2. **Separate Invoices** - Track each cost type with its own invoice number
3. **VAT Handling** - Mark taxable costs and track VAT separately
4. **Cost Centers** - Assign to procurement or relevant cost center
5. **Reference Numbers** - Store customs declaration numbers for audit
6. **Allocation Flag** - Mark which costs were capitalized to inventory
7. **Payment Tracking** - Update payment status as costs are paid

## Database Schema

All new columns are added with proper:
- ✅ Foreign key constraints
- ✅ Indexes on frequently queried fields
- ✅ Default values where appropriate
- ✅ Nullable/Not Null constraints

## Migration Applied

Run: `python scripts/enhance_landed_costs_with_accounting.py`

This added:
- **10 columns** to `landed_costs` table
- **15 columns** to `landed_cost_items` table
- **6 indexes** for performance

## Next Steps

1. Update frontend UI to capture these fields
2. Create dropdown for cost_type selection
3. Add IFRS tag picker
4. Enable GL account selection per cost
5. Add invoice scanning/OCR for document numbers
6. Create reports by IFRS tag
7. Build cost allocation workflows

---

**Date Enhanced:** October 25, 2025
**Migration Script:** `enhance_landed_costs_with_accounting.py`
**Tables Modified:** `landed_costs`, `landed_cost_items`
