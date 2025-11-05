# Inventory Management Guide

## Overview
This guide covers complete inventory management including product setup, stock tracking, allocation, transfers, and adjustments in the CNPERP ERP system.

## Table of Contents
1. [Product Setup](#product-setup)
2. [Stock Management](#stock-management)
3. [Units of Measure (UOM)](#units-of-measure-uom)
4. [Inventory Allocation](#inventory-allocation)
5. [Stock Transfers](#stock-transfers)
6. [Stock Adjustments](#stock-adjustments)
7. [Inventory Valuation](#inventory-valuation)
8. [Reporting](#reporting)

---

## Product Setup

### Creating a Product

1. **Navigate to Inventory → Products**
2. **Click "Add Product"**
3. **Fill in Details:**

```
Basic Information:
├── Product Code: PROD-001 (unique, auto-generated option)
├── Product Name: Office Chair - Executive
├── Description: Ergonomic executive office chair with lumbar support
├── Category: Furniture → Office Furniture
├── Brand: ErgoMax
└── Status: Active

Inventory Settings:
├── Track Inventory: ✓ Yes
├── Product Type: Finished Goods/Raw Material/Service
├── Unit of Measure: Each (EA)
├── Reorder Level: 10 units
├── Reorder Quantity: 50 units
└── Lead Time: 14 days

Pricing:
├── Cost Price: P 450.00 (average/standard/FIFO)
├── Selling Price: P 750.00
├── Tax Category: Standard VAT (14%)
├── Margin: 66.67%
└── Markup: 66.67%

Dimensions & Weight:
├── Length: 120 cm
├── Width: 70 cm
├── Height: 110 cm
├── Weight: 15.5 kg
└── Volume: 0.924 m³

Additional Info:
├── Supplier: ABC Furniture Ltd.
├── Supplier Code: SUP-CH-001
├── Barcode: 1234567890123
├── Image: Upload product photo
└── Custom Fields: (as configured)
```

4. **Click "Save"**

### Product Types

#### 1. Finished Goods
- Products ready for sale
- Manufactured or purchased
- Full inventory tracking
- COGS calculated on sale

#### 2. Raw Materials
- Used in manufacturing
- Consumed in production
- Allocated to BOM
- COGS to work-in-progress

#### 3. Work in Progress (WIP)
- Partially manufactured
- Between raw and finished
- Value accumulation
- Conversion tracking

#### 4. Services
- Non-physical items
- No inventory tracking
- Time/labor based
- Immediate COGS recognition

### Product Images

**Adding Product Images:**

1. **Single Image Upload:**
   - Click "Upload Image"
   - Select file (JPG, PNG up to 5MB)
   - Image automatically resized
   - Becomes primary product image

2. **Multiple Images:**
   - Upload gallery images
   - Set primary image
   - Reorder images
   - Delete unwanted images

3. **Image Best Practices:**
   - Use high-quality images (min 800x800px)
   - White background preferred
   - Show product clearly
   - Multiple angles helpful
   - Compress before upload

### Barcodes

**Barcode Types Supported:**

1. **Standard EAN-13:**
   ```
   Format: 1234567890123 (13 digits)
   Use: Regular products
   Printing: Any barcode printer
   ```

2. **Weight-Based (EAN-13):**
   ```
   Format: 20-24 XXXXX YYYYY C
   ├── 20-24: Weight prefix
   ├── XXXXX: Product code (5 digits)
   ├── YYYYY: Weight in grams (5 digits)
   └── C: Check digit
   
   Example: 20 12345 01250 3
   └── Product 12345, weight 1.250kg
   ```

3. **Custom Barcodes:**
   - Define your own format
   - Map to product codes
   - Use barcode generator

---

## Stock Management

### Viewing Stock Levels

1. **Navigate to Inventory → Stock Levels**
2. **View Options:**
   - All products
   - By branch/location
   - By category
   - Low stock items
   - Out of stock items

**Stock Level Display:**
```
Product Information:
├── Code: PROD-001
├── Name: Office Chair - Executive
├── UOM: Each

Stock Quantity:
├── Head Office: 45 EA
├── Branch A: 23 EA
├── Branch B: 12 EA
├── Total: 80 EA

Status Indicators:
├── Available: 55 EA (not allocated)
├── Allocated: 25 EA (to orders)
├── On Order: 50 EA (incoming)
├── Reorder Level: 10 EA
└── Status: ✓ Sufficient Stock
```

### Stock In (Receiving)

**From Purchase Order:**

1. **Navigate to Purchases → Receive Stock**
2. **Select PO:**
   ```
   PO Details:
   ├── PO Number: PO-2025-001
   ├── Supplier: ABC Furniture Ltd.
   ├── Order Date: 2025-10-01
   └── Status: Partially Received
   ```

3. **Receive Items:**
   ```
   Item: Office Chair - Executive
   ├── Ordered Quantity: 50 EA
   ├── Previously Received: 0 EA
   ├── Receiving Now: 50 EA
   ├── Outstanding: 0 EA
   ├── Unit Cost: P 450.00
   └── Total Value: P 22,500.00
   
   Receipt Details:
   ├── GRN Number: GRN-2025-001
   ├── Receipt Date: 2025-10-15
   ├── Delivery Note: DN-12345
   ├── Received By: John Doe
   └── Location: Main Warehouse
   ```

4. **Quality Check:**
   - Inspect items
   - Note any damage
   - Record actual qty received
   - Take photos if damaged

5. **Post Receipt**

**Accounting Impact:**
```
Debit:  Inventory - Office Chairs  P 22,500.00
Credit: Accounts Payable - ABC     P 22,500.00
```

**Direct Stock In (No PO):**

1. **Navigate to Inventory → Stock In**
2. **Click "New Stock In"**
3. **Fill Details:**
   ```
   Stock In Information:
   ├── Reference: SI-2025-001
   ├── Date: 2025-10-15
   ├── Supplier: (optional)
   ├── Location: Main Warehouse
   └── Reason: Initial stock/Found/Return
   
   Items:
   ├── Product: Office Chair - Executive
   ├── Quantity: 10 EA
   ├── Unit Cost: P 450.00
   └── Total: P 4,500.00
   ```

4. **Post Transaction**

### Stock Out (Issuing)

**From Sales Order:**

1. **Navigate to Sales → Dispatch Stock**
2. **Select Sales Order**
3. **Dispatch Items:**
   ```
   SO-2025-100:
   ├── Customer: XYZ Company
   ├── Order Date: 2025-10-10
   └── Status: Ready to Dispatch
   
   Dispatch Details:
   ├── Dispatch Note: DN-2025-001
   ├── Dispatch Date: 2025-10-15
   ├── Courier: DHL Express
   ├── Tracking: 1234567890
   └── Dispatched By: Jane Smith
   ```

4. **Print Dispatch Note**
5. **Update Order Status**

**Accounting Impact:**
```
At dispatch (perpetual inventory):
Debit:  Cost of Goods Sold        P 450.00
Credit: Inventory - Office Chairs P 450.00
```

**Manual Stock Out:**

```
Stock Out Information:
├── Reference: SO-2025-001
├── Date: 2025-10-15
├── Location: Main Warehouse
├── Reason: Production/Damaged/Sample
└── Approved By: Manager

Items:
├── Product: Office Chair - Executive
├── Quantity: 5 EA
├── Unit Cost: P 450.00
└── Total: P 2,250.00
```

---

## Units of Measure (UOM)

### Standard UOM Setup

**Common UOM Examples:**

```
Count Units:
├── Each (EA) - Individual items
├── Pair (PR) - Two items
├── Dozen (DZ) - 12 items
└── Gross (GR) - 144 items

Weight Units:
├── Kilogram (KG)
├── Gram (G)
├── Pound (LB)
└── Ton (TON)

Volume Units:
├── Liter (L)
├── Milliliter (ML)
├── Gallon (GAL)
└── Cubic Meter (M3)

Length Units:
├── Meter (M)
├── Centimeter (CM)
├── Foot (FT)
└── Roll (ROLL)
```

### UOM Conversions

**Setting Up Conversion:**

1. **Navigate to Inventory → UOM Conversions**
2. **Define Base Unit:**
   ```
   Product: Bottled Water
   Base UOM: Bottle (each)
   ```

3. **Add Conversion Units:**
   ```
   Conversion Rules:
   ├── 1 Case = 24 Bottles
   ├── 1 Pallet = 1,200 Bottles (50 cases)
   └── 1 Bottle = 500 ML
   ```

4. **Usage:**
   - Purchase in pallets
   - Store in cases
   - Sell in bottles
   - System auto-converts

**Multi-UOM Example:**

```
Purchasing:
└── Buy 10 pallets @ P 2,400/pallet = P 24,000

Stock Received:
└── 12,000 bottles @ P 2.00/bottle

Sales:
├── Sell 5 cases @ P 60/case = P 300
└── Stock reduced: 120 bottles

Reporting:
├── Stock on Hand: 11,880 bottles
├── = 495 cases
└── = 9.9 pallets
```

---

## Inventory Allocation

### Understanding Allocation

**Allocation Flow:**
```
Available Stock = Physical Stock - Allocated Stock

Example:
├── Physical Stock: 100 EA
├── Allocated to Orders: 35 EA
├── Available for Sale: 65 EA
└── On Order (incoming): 50 EA
```

### Automatic Allocation

**When Sales Order is Created:**

1. System checks available stock
2. If sufficient, allocates immediately
3. Reduces available quantity
4. Shows as "Allocated" in stock view
5. Prevents overselling

**Example:**
```
Before Order:
├── Physical: 100 EA
├── Allocated: 20 EA
└── Available: 80 EA

New Order for 30 EA:
├── System allocates: 30 EA
└── New Available: 50 EA

After Order:
├── Physical: 100 EA (unchanged)
├── Allocated: 50 EA (20 + 30)
└── Available: 50 EA
```

### Manual Allocation

**Reserve Stock for Special Order:**

1. **Navigate to Inventory → Allocations**
2. **Click "New Allocation"**
3. **Fill Details:**
   ```
   Allocation Details:
   ├── Product: Office Chair - Executive
   ├── Quantity: 15 EA
   ├── Customer: VIP Customer
   ├── Reference: Special Order
   ├── From Date: 2025-10-15
   ├── To Date: 2025-10-30
   └── Notes: Hold for confirmed delivery
   ```

4. **Save Allocation**

### De-allocation

**Releasing Allocated Stock:**

- Order cancelled → Auto de-allocates
- Order fulfilled → Removes allocation
- Manual release → Via allocation screen
- Expired allocation → Auto-release option

---

## Stock Transfers

### Branch-to-Branch Transfer

1. **Navigate to Inventory → Stock Transfers**
2. **Click "New Transfer"**
3. **Fill Details:**

```
Transfer Information:
├── Transfer No: TR-2025-001
├── Date: 2025-10-15
├── From Location: Head Office Warehouse
├── To Location: Branch A
├── Transfer Type: Branch Transfer
├── Initiated By: Warehouse Manager
└── Expected Date: 2025-10-16

Items to Transfer:
┌─────────────────┬──────────┬───────────┬────────┐
│ Product         │ Quantity │ UOM       │ Value  │
├─────────────────┼──────────┼───────────┼────────┤
│ Office Chair    │ 20       │ EA        │ 9,000  │
│ Desk Lamp       │ 50       │ EA        │ 2,500  │
│ Filing Cabinet  │ 10       │ EA        │ 4,500  │
└─────────────────┴──────────┴───────────┴────────┘
Total Value: P 16,000.00

Transport Details:
├── Vehicle: Truck Registration ABC123
├── Driver: Peter Molefe
├── Courier: Internal Transport
└── Expected Arrival: 2025-10-16 10:00
```

4. **Create Transfer** (Status: Draft)
5. **Approve Transfer** (Status: Approved)
6. **Dispatch Stock** (Status: In Transit)
   - Reduces source location stock
   - Stock in transit account

7. **Receive at Destination** (Status: Completed)
   - Increases destination stock
   - Clears in-transit

**Accounting Impact:**
```
At Dispatch:
Debit:  Inventory in Transit     P 16,000
Credit: Inventory - Head Office  P 16,000

At Receipt:
Debit:  Inventory - Branch A     P 16,000
Credit: Inventory in Transit     P 16,000
```

### Location-to-Location Transfer

**Within Same Branch:**

```
Transfer between:
├── From: Main Warehouse
├── To: Retail Floor
├── Reason: Replenish display stock
└── No accounting impact (same entity)
```

---

## Stock Adjustments

### When to Use Adjustments

- Physical count variance
- Damage/spoilage
- Theft/loss
- Found stock
- Reclassification
- Correction of errors

### Creating Stock Adjustment

1. **Navigate to Inventory → Stock Adjustments**
2. **Click "New Adjustment"**
3. **Fill Details:**

```
Adjustment Information:
├── Adjustment No: ADJ-2025-001
├── Date: 2025-10-15
├── Type: Physical Count Variance
├── Location: Head Office Warehouse
├── Reason: Annual stocktake
├── Approved By: CFO
└── Reference: Stocktake Report Oct 2025

Adjustments:
┌──────────────┬────────┬──────────┬──────────┬────────────┐
│ Product      │ UOM    │ System   │ Actual   │ Variance   │
├──────────────┼────────┼──────────┼──────────┼────────────┤
│ Office Chair │ EA     │ 100      │ 98       │ -2 (loss)  │
│ Desk Lamp    │ EA     │ 250      │ 255      │ +5 (gain)  │
│ Notebook     │ EA     │ 500      │ 495      │ -5 (loss)  │
└──────────────┴────────┴──────────┴──────────┴────────────┘

Value Impact:
├── Total Losses: P 1,150.00
├── Total Gains: P 125.00
└── Net Adjustment: P (1,025.00)
```

4. **Require Approval** (if variance > threshold)
5. **Post Adjustment**

**Accounting Impact:**
```
For Losses:
Debit:  Stock Loss Expense       P 1,150
Credit: Inventory                P 1,150

For Gains:
Debit:  Inventory                P 125
Credit: Stock Gain Income        P 125
```

### Damage/Spoilage

```
Damage Adjustment:
├── Product: Perishable Item
├── Quantity Lost: 10 EA
├── Reason: Expired/Damaged
├── Cost: P 500.00
└── Write-off Account: Stock Loss

Documentation:
├── Photo of damaged items
├── Manager approval
└── Disposal certificate
```

---

## Inventory Valuation

### Valuation Methods

#### 1. FIFO (First In, First Out)

```
Purchases:
├── Jan 1:  10 units @ P 100 = P 1,000
├── Feb 1:  10 units @ P 110 = P 1,100
└── Mar 1:  10 units @ P 120 = P 1,200

Sale: 15 units
COGS Calculation:
├── 10 units @ P 100 = P 1,000 (from Jan)
├── 5 units @ P 110 = P 550 (from Feb)
└── Total COGS: P 1,550

Remaining Stock:
├── 5 units @ P 110 = P 550 (from Feb)
├── 10 units @ P 120 = P 1,200 (from Mar)
└── Total Value: P 1,750
```

#### 2. Weighted Average

```
Purchases:
├── Jan 1:  10 units @ P 100 = P 1,000
├── Feb 1:  10 units @ P 110 = P 1,100
└── Mar 1:  10 units @ P 120 = P 1,200

Average Cost:
├── Total Cost: P 3,300
├── Total Units: 30
└── Avg Cost: P 110/unit

Sale: 15 units
├── COGS: 15 × P 110 = P 1,650

Remaining Stock:
├── 15 units × P 110 = P 1,650
```

#### 3. Standard Cost

```
Standard Cost Set: P 100/unit
(Regardless of actual purchase price)

All transactions use standard cost.
Variances tracked separately.

Purchase at P 110:
├── Inventory: 10 × P 100 = P 1,000
└── Purchase Price Variance: P 100

Sale at standard:
├── COGS: P 100/unit
└── No variance on sale
```

### Stock Valuation Report

**Navigate to Reports → Stock Valuation:**

```
Stock Valuation as at 2025-10-15
├── Method: FIFO
├── Location: All Branches
└── Currency: BWP

Summary by Category:
┌─────────────────┬────────┬────────────┬─────────────┐
│ Category        │ Qty    │ Avg Cost   │ Total Value │
├─────────────────┼────────┼────────────┼─────────────┤
│ Office Furniture│ 234    │ P 525.50   │ P 122,967   │
│ Electronics     │ 456    │ P 1,250.00 │ P 570,000   │
│ Stationery      │ 2,345  │ P 12.50    │ P 29,313    │
└─────────────────┴────────┴────────────┴─────────────┘
Total Inventory Value: P 722,280
```

---

## Reporting

### Stock Reports

1. **Stock on Hand Report**
   - Current stock levels
   - By location/category/product
   - Export to Excel

2. **Stock Movement Report**
   - All transactions by period
   - In/Out/Adjustments/Transfers
   - Running balance

3. **Stock Valuation Report**
   - Value by method (FIFO/AVG)
   - By location/category
   - For financial statements

4. **Reorder Report**
   - Items below reorder level
   - Suggested reorder quantity
   - Supplier information

5. **Stock Age Analysis**
   - How long stock on hand
   - Identify slow-moving items
   - Dead stock identification

6. **Stock Take Variance Report**
   - System vs. physical count
   - Variance analysis
   - Adjustment history

### Dashboards

**Inventory Dashboard Shows:**
- Total inventory value
- Low stock alerts
- Out of stock items
- Stock movement trends
- Top selling products
- Slow-moving items

---

## Best Practices

### Daily Tasks
- ✅ Process all stock receipts promptly
- ✅ Record all stock issues
- ✅ Update stock transfers
- ✅ Review low stock alerts

### Weekly Tasks
- ✅ Reconcile deliveries vs. POs
- ✅ Review stock allocations
- ✅ Check for dead stock
- ✅ Update reorder levels

### Monthly Tasks
- ✅ Spot check physical counts
- ✅ Review stock valuation
- ✅ Analyze slow-moving items
- ✅ Update standard costs
- ✅ Reconcile inventory GL accounts

### Annual Tasks
- ✅ Full physical stocktake
- ✅ Stock valuation for year-end
- ✅ Review all product master data
- ✅ Purge obsolete products

### Security & Control
- 🔒 Segregation of duties
- 🔒 Approval for adjustments
- 🔒 Regular stock counts
- 🔒 CCTV in warehouse
- 🔒 Access control to stock areas

---

## Troubleshooting

**Issue: Stock balance incorrect**
- Run stock movement report
- Check for unposted transactions
- Verify all transfers completed
- Look for duplicate entries

**Issue: Cannot sell item (out of stock)**
- Check allocated stock
- Review pending transfers
- Verify location settings
- Check negative stock allowed setting

**Issue: Wrong COGS calculated**
- Verify costing method
- Check if receipts posted correctly
- Review adjustment history
- Recalculate average cost

---

## Related Documentation
- [Product Costing & COGS](manufacturing-cogs-guide.md)
- [Purchase Orders](purchasing-guide.md)
- [Sales Orders](sales-guide.md)
- [Weight-Based Products](weight-products-guide.md)
