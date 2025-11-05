# Inventory Adjustment System - User Guide

## Overview
The inventory adjustment system allows you to manually adjust product quantities with proper inventory transaction tracking and automatic journal entry creation for accounting purposes.

## What Changed

### ✅ Fixed Issues
1. **Inventory editing now works properly** - Creates inventory transactions and journal entries
2. **Proper accounting integration** - All adjustments create appropriate Dr/Cr entries
3. **Audit trail** - Complete history of all quantity changes with reasons

### 🆕 New Features
1. **Inventory Adjustment API** - `/api/v1/inventory/adjustments`
2. **Proper schemas** - Type-safe request/response models
3. **Multiple adjustment types** - gain, loss, correction, damage, theft, opening_stock
4. **Automatic journal entries** - Based on adjustment type

## API Endpoints

### 1. Create Inventory Adjustment
**POST** `/api/v1/inventory/adjustments`

**Request Body:**
```json
{
  "product_id": "product-uuid-here",
  "quantity_change": 10,  // Positive for increase, negative for decrease
  "adjustment_type": "gain",  // gain, loss, correction, damage, theft, opening_stock
  "reason": "Found extra stock during inventory count",
  "notes": "Optional additional notes",
  "branch_id": "branch-uuid",  // Optional
  "adjustment_date": "2025-10-26"  // Optional, defaults to today
}
```

**Response:**
```json
{
  "id": "adjustment-uuid",
  "product_id": "product-uuid",
  "adjustment_date": "2025-10-26",
  "quantity": 10,
  "reason": "Found extra stock during inventory count",
  "adjustment_type": "gain",
  "previous_quantity": 100,
  "new_quantity": 110,
  "unit_cost": "50.00",
  "total_amount": "500.00",
  "accounting_entry_id": "entry-uuid",
  "created_at": "2025-10-26T10:30:00"
}
```

### 2. Get Adjustment History
**GET** `/api/v1/inventory/adjustments`

**Query Parameters:**
- `product_id` (optional) - Filter by product
- `branch_id` (optional) - Filter by branch
- `limit` (optional) - Max records to return (default 100)

**Example:**
```
GET /api/v1/inventory/adjustments?product_id=abc-123&limit=50
```

## Adjustment Types & Journal Entries

### 1. Gain/Opening Stock (Quantity Increase)
**When:** Found extra stock, opening stock entry

**Quantity Change:** `+10` (positive number)

**Journal Entry:**
```
Dr. Inventory (Asset)        $500
    Cr. Inventory Gain (Income)   $500
```

### 2. Damage (Quantity Decrease)
**When:** Items damaged, spoiled, expired

**Quantity Change:** `-5` (negative number)

**Journal Entry:**
```
Dr. Damage Expense (Expense)    $250
    Cr. Inventory (Asset)            $250
```

### 3. Theft (Quantity Decrease)
**When:** Items stolen or missing

**Quantity Change:** `-3` (negative number)

**Journal Entry:**
```
Dr. Theft Expense (Expense)     $150
    Cr. Inventory (Asset)            $150
```

### 4. Loss/Correction (Quantity Decrease)
**When:** Inventory count discrepancies, corrections

**Quantity Change:** `-2` (negative number)

**Journal Entry:**
```
Dr. Inventory Loss (Expense)    $100
    Cr. Inventory (Asset)            $100
```

## How to Use

### Method 1: Using cURL (Command Line)

**Example 1: Increase inventory**
```powershell
curl -X POST "http://localhost:8010/api/v1/inventory/adjustments" `
  -H "Content-Type: application/json" `
  -d '{
    "product_id": "24dc748d-8313-4a79-8a35-92773faf97ee",
    "quantity_change": 25,
    "adjustment_type": "gain",
    "reason": "Physical count revealed 25 extra units"
  }'
```

**Example 2: Record damaged goods**
```powershell
curl -X POST "http://localhost:8010/api/v1/inventory/adjustments" `
  -H "Content-Type: application/json" `
  -d '{
    "product_id": "24dc748d-8313-4a79-8a35-92773faf97ee",
    "quantity_change": -10,
    "adjustment_type": "damage",
    "reason": "Water damage to stock in warehouse",
    "notes": "Items non-reusable, disposed of"
  }'
```

### Method 2: Using Python Script

Run the test script:
```powershell
.\.venv\Scripts\python.exe scripts\test_inventory_adjustment.py
```

### Method 3: Frontend Integration (Coming Soon)

Add to your inventory management UI:
```javascript
async function adjustInventory(productId, quantityChange, type, reason) {
    const response = await fetch('/api/v1/inventory/adjustments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            product_id: productId,
            quantity_change: quantityChange,
            adjustment_type: type,
            reason: reason
        })
    });

    if (response.ok) {
        const result = await response.json();
        console.log('Adjustment created:', result);
        // Refresh inventory display
    }
}

// Example usage:
// Increase by 10
adjustInventory('product-id', 10, 'gain', 'Found extra stock');

// Decrease by 5 (damage)
adjustInventory('product-id', -5, 'damage', 'Items damaged');
```

## Important Notes

### ⚠️ Direct Product Updates
The `/products/{id}` PUT endpoint still exists but should **NOT** be used for quantity changes:
- It doesn't create inventory transactions
- It doesn't create journal entries
- It has no audit trail

**Always use `/adjustments` for quantity changes!**

### ✅ Best Practices

1. **Always provide a clear reason** - Required for audit trail
2. **Use appropriate adjustment types** - Ensures correct journal entries
3. **Review adjustments regularly** - Use GET endpoint to check history
4. **Verify quantities** - Check product after adjustment

### 🔍 Troubleshooting

**Problem:** "Product not found"
- **Solution:** Verify the product_id is correct

**Problem:** "Insufficient stock"
- **Solution:** Check current quantity before decreasing

**Problem:** "No accounting code"
- **Solution:** Ensure product has an accounting_code_id set

**Problem:** Journal entries not created
- **Solution:** Check that appropriate expense/income accounts exist in chart of accounts

## Testing

Run the comprehensive test:
```powershell
$env:PYTHONPATH = "$PWD"
.\.venv\Scripts\python.exe scripts\test_inventory_adjustment.py
```

Expected output:
```
================================================================================
INVENTORY ADJUSTMENT API TEST
================================================================================
📦 Testing with product: RAPOO WIRELESS KEYBOARD
   Current quantity: 175

🔼 Test 1: Increasing inventory by 10 units...
✅ Adjustment created successfully!
   Previous qty: 175
   New qty: 185

🔽 Test 2: Decreasing inventory by 5 units (damage)...
✅ Adjustment created successfully!
   Previous qty: 185
   New qty: 180

📋 Test 3: Fetching adjustment history...
✅ Found 2 adjustments for this product

🔍 Verifying final product quantity...
   ✅ Quantity matches!
```

## Database Schema

### inventory_adjustments table
```sql
CREATE TABLE inventory_adjustments (
    id VARCHAR PRIMARY KEY,
    product_id VARCHAR NOT NULL,
    adjustment_date DATE,
    quantity INTEGER,
    reason VARCHAR,
    adjustment_type VARCHAR,  -- gain, loss, correction, damage, theft
    previous_quantity INTEGER,
    new_quantity INTEGER,
    unit_cost NUMERIC(15,2),
    total_amount NUMERIC(15,2),
    accounting_entry_id VARCHAR NOT NULL,
    branch_id VARCHAR,
    notes TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (accounting_entry_id) REFERENCES accounting_entries(id)
);
```

### inventory_transactions table
```sql
-- Automatically created by InventoryService.update_product_quantity()
CREATE TABLE inventory_transactions (
    id VARCHAR PRIMARY KEY,
    product_id VARCHAR NOT NULL,
    transaction_type VARCHAR,  -- goods_receipt, sale, adjustment, damage, theft
    quantity INTEGER,
    unit_cost NUMERIC(15,2),
    reference VARCHAR,
    note TEXT,
    date DATE,
    branch_id VARCHAR,
    related_purchase_id VARCHAR,
    created_at TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
```

## Summary

✅ **What Works Now:**
- Manual inventory adjustments with full accounting
- Automatic journal entry creation
- Complete audit trail
- Transaction history

✅ **What's Fixed:**
- Inventory editing creates proper records
- Journal entries automatically generated
- No more "silent" quantity changes

🎯 **Next Steps:**
1. Test the adjustment API
2. Integrate into your frontend
3. Train users on proper adjustment types
4. Review adjustment history regularly
