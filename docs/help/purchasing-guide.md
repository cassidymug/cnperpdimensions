# Purchasing & Procurement Guide

## Overview
This guide covers the complete purchasing cycle from supplier management to purchase orders, goods receiving, supplier payments, and procurement analytics.

## Table of Contents
1. [Supplier Management](#supplier-management)
2. [Purchase Requisitions](#purchase-requisitions)
3. [Purchase Orders](#purchase-orders)
4. [Goods Receiving](#goods-receiving)
5. [Supplier Invoices](#supplier-invoices)
6. [Supplier Payments](#supplier-payments)
7. [Purchase Returns](#purchase-returns)
8. [Procurement Analytics](#procurement-analytics)

---

## Supplier Management

### Adding a Supplier

1. **Navigate to Purchases → Suppliers**
2. **Click "Add Supplier"**
3. **Fill Supplier Details:**

```
Basic Information:
├── Supplier Code: SUP-001 (auto-generated)
├── Supplier Name: ABC Furniture Ltd
├── Trading Name: ABC Furnitures
├── Supplier Type: Manufacturer/Wholesaler/Distributor
├── Status: Active/Inactive/Blocked
└── Category: Furniture & Fixtures

Contact Information:
├── Primary Contact: John Supplier
├── Phone: +267 1234 5678
├── Mobile: +267 7123 4567
├── Email: orders@abcfurniture.com
├── Website: www.abcfurniture.com
└── Fax: +267 1234 5679

Address Details:
├── Physical Address:
│   Plot 123, Industrial Area
│   Gaborone, Botswana
│
├── Postal Address:
│   P.O. Box 12345
│   Gaborone, Botswana
│
└── Delivery Address:
    (Same as physical / Different)

Financial Information:
├── Tax Number: C12345678
├── VAT Number: VAT-12345
├── Payment Terms: Net 30 days
├── Credit Limit: P 100,000.00
├── Discount %: 2.5% (for early payment)
└── Currency: BWP/USD/EUR

Banking Details:
├── Bank Name: Standard Bank
├── Branch: Main Branch
├── Branch Code: 285267
├── Account Number: 9876543210
├── Account Name: ABC Furniture Ltd
├── SWIFT Code: SBICBWGX
└── Bank Currency: BWP

Accounting Integration:
├── GL Account: 200-001 (Accounts Payable)
├── Sub-account Code: 200-S001
├── Expense Account: 500-010 (Purchases)
└── VAT Account: 210-002 (VAT Input)

Additional Settings:
├── Lead Time: 14 days
├── Minimum Order: P 5,000
├── Preferred: ✓ Yes
├── Approved: ✓ Yes
└── Rating: ⭐⭐⭐⭐⭐
```

4. **Save Supplier**

### Supplier Documents

**Attach Documents:**
- Tax certificates
- Company registration
- Bank confirmation letters
- Price lists
- Contracts/agreements
- Quality certificates
- Insurance documents

### Supplier Performance Tracking

```
Performance Metrics:
├── On-Time Delivery: 95%
├── Quality Rating: 4.5/5.0
├── Response Time: 2 hours avg
├── Returns Rate: 1.2%
├── Average Order Value: P 25,000
├── Total Purchases YTD: P 450,000
└── Payment History: Excellent

Historical Analysis:
├── Total Orders: 156
├── Completed: 148
├── Pending: 5
├── Cancelled: 3
└── Returns: 8
```

---

## Purchase Requisitions

### Creating Purchase Requisition

1. **Navigate to Purchases → Requisitions**
2. **Click "New Requisition"**
3. **Fill Details:**

```
Requisition Information:
├── Requisition No: PR-2025-001 (auto)
├── Date: 2025-10-15
├── Requested By: John Doe (Sales Manager)
├── Department: Sales
├── Branch: Head Office
├── Required Date: 2025-10-25
├── Priority: Normal/Urgent/Critical
└── Purpose: Restock office furniture

Items Requested:
┌──────────────────┬──────┬─────┬─────────────┬──────────┐
│ Product          │ Qty  │ UOM │ Est. Price  │ Total    │
├──────────────────┼──────┼─────┼─────────────┼──────────┤
│ Office Chair     │ 50   │ EA  │ 450.00      │ 22,500   │
│ Desk Lamp        │ 100  │ EA  │ 75.00       │  7,500   │
│ Filing Cabinet   │ 20   │ EA  │ 350.00      │  7,000   │
└──────────────────┴──────┴─────┴─────────────┴──────────┘

Estimated Total: P 37,000.00

Justification:
├── Reason: Stock levels below reorder point
├── Impact if not approved: Cannot fulfill customer orders
├── Alternative options: Purchase from local supplier at higher cost
└── Budget Code: SALES-2025-Q4

Approvals Required:
├── Department Manager: Pending
├── Finance Manager: Not yet
├── Managing Director: Not yet (if > P 50,000)
└── Procurement: Will process after approval
```

4. **Submit for Approval**

### Approval Workflow

```
Approval Chain:
├── < P 10,000: Department Manager only
├── P 10,000 - P 50,000: Dept Manager + Finance
├── > P 50,000: All + Managing Director
└── Capital Items: Board approval required

Status Flow:
Draft → Submitted → Approved → PO Created → Completed
         ↓
      Rejected → Revised → Resubmitted
```

---

## Purchase Orders

### Creating Purchase Order

1. **Navigate to Purchases → Purchase Orders**
2. **Click "New Purchase Order"**
3. **Select Source:**
   - From Approved Requisition
   - From Quotation
   - Direct Entry

**Purchase Order Details:**

```
Header Information:
├── PO Number: PO-2025-001 (auto)
├── PO Date: 2025-10-15
├── Supplier: ABC Furniture Ltd
├── Supplier Contact: John Supplier
├── Buyer: Jane Buyer
├── Branch: Head Office
├── Delivery Location: Main Warehouse
└── Expected Delivery: 2025-10-29

Reference Information:
├── Requisition: PR-2025-001
├── Supplier Quote: QUO-SUP-123
├── Your Reference: Customer order #456
├── Project Code: PROJ-2025-10
└── Budget Code: SALES-2025-Q4

Items:
┌──────────────┬────┬────┬─────────┬─────────┬──────────┐
│ Product      │Qty │UOM │ Price   │ VAT %   │ Total    │
├──────────────┼────┼────┼─────────┼─────────┼──────────┤
│ Office Chair │ 50 │ EA │ 450.00  │ 14%     │ 22,500   │
│ Desk Lamp    │100 │ EA │  75.00  │ 14%     │  7,500   │
│ Freight      │  1 │ EA │ 500.00  │ 14%     │    500   │
└──────────────┴────┴────┴─────────┴─────────┴──────────┘

Financial Summary:
├── Subtotal (excl VAT):     P 30,500.00
├── VAT @ 14%:               P  4,270.00
├── Total PO Value:          P 34,770.00
├── Amount Received:         P  0.00
└── Outstanding:             P 34,770.00

Terms & Conditions:
├── Payment Terms: Net 30 days
├── Delivery Terms: Free delivery to our warehouse
├── Incoterms: DAP (Delivered at Place)
├── Warranty: 12 months manufacturer warranty
├── Penalties: 1% per day for late delivery
└── Validity: 30 days from date

Special Instructions:
├── Delivery between 8 AM - 4 PM weekdays only
├── Call 1 day before delivery
├── Require delivery note with all items
└── Inspect all items before unloading
```

4. **Review & Approve**
5. **Send to Supplier**

### PO Status Workflow

```
Status Progression:
Draft
  ↓
Pending Approval
  ↓
Approved → Sent to Supplier
  ↓
Acknowledged by Supplier
  ↓
Partially Received → Fully Received
  ↓
Invoiced → Paid → Closed
  ↓
(Alternative) Cancelled
```

---

## Goods Receiving

### Receiving Stock from PO

1. **Navigate to Purchases → Goods Receiving**
2. **Click "New Receipt"** or **Select PO**
3. **Fill GRN (Goods Received Note):**

```
Receipt Information:
├── GRN Number: GRN-2025-001 (auto)
├── Receipt Date: 2025-10-29
├── Purchase Order: PO-2025-001
├── Supplier: ABC Furniture Ltd
├── Delivery Note: DN-SUP-789
├── Received By: Warehouse Manager
├── Received At: Main Warehouse
└── Vehicle/Courier: Truck ABC 123 BW

Items Received:
┌────────────┬────────┬──────────┬──────────┬─────────┐
│ Product    │Ordered │ Received │ Rejected │ Shortage│
├────────────┼────────┼──────────┼──────────┼─────────┤
│Office Chair│  50    │   48     │    2     │    0    │
│Desk Lamp   │ 100    │  100     │    0     │    0    │
└────────────┴────────┴──────────┴──────────┴─────────┘

Quality Inspection:
├── Inspector: QC Manager
├── Inspection Date: 2025-10-29
├── Overall Quality: Good
├── Issues Found: 2 chairs damaged
├── Action Taken: Rejected, supplier to replace
└── Photos Attached: Yes

Rejected Items:
┌────────────┬─────┬──────────────────────────┐
│ Product    │ Qty │ Reason                   │
├────────────┼─────┼──────────────────────────┤
│Office Chair│  2  │ Damaged - broken armrest │
└────────────┴─────┴──────────────────────────┘

Receipt Notes:
├── Condition: Items well packed
├── Delivery Time: 10:30 AM (on time)
├── Documentation: Complete
└── Follow-up: Replacement for 2 chairs needed
```

4. **Post GRN**

**Accounting Impact:**
```
Debit:  Inventory - Office Chairs   P 21,600 (48 × 450)
Debit:  Inventory - Desk Lamps      P  7,500 (100 × 75)
Credit: GRN Clearing Account        P 29,100

(To be matched against supplier invoice)
```

### Partial Receipts

```
Scenario: Order 100 units, receive in batches

Receipt 1 (Oct 29):
├── Received: 60 units
├── GRN: GRN-2025-001
└── Status: PO Partially Received

Receipt 2 (Nov 5):
├── Received: 40 units
├── GRN: GRN-2025-002
└── Status: PO Fully Received

System tracks:
├── Total Ordered: 100
├── Total Received: 100
├── Outstanding: 0
└── PO can be closed
```

---

## Supplier Invoices

### Recording Supplier Invoice

1. **Navigate to Purchases → Supplier Invoices**
2. **Click "New Invoice"** or **Match to GRN**
3. **Enter Invoice Details:**

```
Invoice Information:
├── Supplier: ABC Furniture Ltd
├── Supplier Invoice No: INV-SUP-456
├── Invoice Date: 2025-10-30
├── Due Date: 2025-11-29 (30 days)
├── Currency: BWP
├── Exchange Rate: 1.0000
└── Related PO: PO-2025-001

Match to GRN:
├── Select GRN: GRN-2025-001
├── Auto-populate items
├── Verify quantities
└── Check prices

Invoice Items:
┌────────────┬─────┬────┬────────┬─────────┬──────────┐
│ Product    │ Qty │UOM │ Price  │ VAT %   │ Amount   │
├────────────┼─────┼────┼────────┼─────────┼──────────┤
│Office Chair│  48 │ EA │ 450.00 │ 14%     │ 21,600   │
│Desk Lamp   │ 100 │ EA │  75.00 │ 14%     │  7,500   │
│Freight     │   1 │ EA │ 500.00 │ 14%     │    500   │
└────────────┴─────┴────┴────────┴─────────┴──────────┘

Invoice Summary:
├── Subtotal:               P 29,600.00
├── VAT @ 14%:              P  4,144.00
├── Total Invoice:          P 33,744.00
├── Early Payment Discount: P    843.60 (2.5% if paid early)
└── Net Payable:            P 32,900.40 (if discount taken)

Variances (if any):
├── Price Variance: P 0.00
├── Quantity Variance: -2 chairs (rejected)
├── Other Charges: P 500 freight
└── Total Variance: P 0.00 (within tolerance)

Approval Required:
├── Invoice matches PO: ✓ Yes
├── Invoice matches GRN: ✓ Yes
├── Prices correct: ✓ Yes
├── Approved By: Finance Manager
└── Approval Date: 2025-10-30
```

4. **Post Invoice**

**Accounting Impact:**
```
Debit:  GRN Clearing Account        P 29,100
Debit:  Freight In                  P    500
Debit:  VAT Input                   P  4,144
Credit: Accounts Payable - ABC      P 33,744
```

### Three-Way Matching

**System validates:**
```
Purchase Order ←→ GRN ←→ Supplier Invoice

Checks:
├── Quantities match (with tolerance)
├── Prices match PO
├── Items match
├── Calculations correct
└── Total within approval limit

Variances flagged:
├── Price variance > 5%
├── Quantity variance > 2%
├── Unexpected charges
└── Missing items
```

---

## Supplier Payments

### Creating Payment

1. **Navigate to Purchases → Payments**
2. **Click "New Payment"**
3. **Select Payment Method:**

**Payment Details:**

```
Payment Information:
├── Payment No: PAY-2025-100 (auto)
├── Payment Date: 2025-11-10
├── Supplier: ABC Furniture Ltd
├── Payment Method: EFT/Cheque/Cash
├── Bank Account: Standard Bank Checking
└── Payment Reference: PAY-ABC-NOV2025

Outstanding Invoices:
┌────────────────┬────────────┬──────────┬─────────┬────────┐
│ Invoice No     │ Due Date   │ Amount   │ Discount│ Paying │
├────────────────┼────────────┼──────────┼─────────┼────────┤
│ INV-SUP-456    │ 2025-11-29 │ 33,744.00│  843.60 │✓Select │
│ INV-SUP-412    │ 2025-11-15 │ 15,230.00│    0.00 │        │
│ INV-SUP-389    │ 2025-11-05 │  8,450.00│    0.00 │✓Select │
└────────────────┴────────────┴──────────┴─────────┴────────┘

Payment Allocation:
├── INV-SUP-456: P 32,900.40 (with 2.5% discount)
├── INV-SUP-389: P  8,450.00
├── Total Payment: P 41,350.40
└── Bank Charges: P 25.00

Payment Processing:
├── Generate EFT file for bank
├── OR Print cheque
├── OR Record cash payment
└── Send remittance advice to supplier

Bank Transfer Details:
├── Bank: Standard Bank
├── Account: 9876543210
├── Reference: INV-SUP-456, INV-SUP-389
├── Amount: P 41,350.40
└── Value Date: 2025-11-10
```

4. **Process Payment**

**Accounting Impact:**
```
Debit:  Accounts Payable - ABC      P 42,194.00
Credit: Bank Account                P 41,350.40
Credit: Discount Received           P    843.60
```

### Payment Run (Batch Processing)

**For multiple suppliers:**

1. **Select criteria:**
   ```
   Filter:
   ├── Due on or before: 2025-11-15
   ├── Suppliers: All/Selected
   ├── Minimum amount: P 1,000
   ├── Take discounts: Yes
   └── Payment method: EFT
   ```

2. **Review invoices:**
   - System shows all matching invoices
   - Select which to pay
   - Review discounts available

3. **Generate batch:**
   - Creates payment file
   - Exports for bank upload
   - Prints remittances
   - Posts accounting entries

---

## Purchase Returns

### Creating Purchase Return

```
Return Information:
├── Return No: PR-2025-001 (auto)
├── Date: 2025-11-01
├── Supplier: ABC Furniture Ltd
├── Return Reason: Damaged goods
├── Related PO: PO-2025-001
├── Related GRN: GRN-2025-001
└── Authorization: Supplier RMA-789

Items Returning:
┌────────────┬─────┬────────────────────────┬──────────┐
│ Product    │ Qty │ Reason                 │ Value    │
├────────────┼─────┼────────────────────────┼──────────┤
│Office Chair│  2  │ Damaged in transit     │  900.00  │
└────────────┴─────┴────────────────────────┴──────────┘

Return Method:
○ Supplier collects
● We deliver to supplier
○ Disposal (with supplier credit)

Credit Expected:
├── Return Value: P 900.00
├── VAT: P 126.00
├── Total Credit: P 1,026.00
├── Restocking Fee: P 0.00
└── Net Credit: P 1,026.00

Follow-up:
├── Replacement requested: Yes
├── Expected date: 2025-11-10
├── Credit note from supplier: Pending
└── Status: Awaiting collection
```

**Accounting Impact:**
```
Debit:  Accounts Payable - ABC      P 1,026.00
Credit: Inventory                   P   900.00
Credit: VAT Input                   P   126.00
```

---

## Procurement Analytics

### Key Reports

**1. Purchase Analysis Report**
```
Period: Oct 2025
├── Total Purchases: P 450,000
├── Number of POs: 45
├── Average PO Value: P 10,000
├── Top Supplier: ABC Furniture (P 125,000)
└── Top Category: Office Furniture (P 180,000)
```

**2. Supplier Performance**
```
Metrics by Supplier:
├── On-time delivery %
├── Quality rating
├── Average lead time
├── Price competitiveness
└── Payment terms compliance
```

**3. Purchase Price Variance**
```
Product: Office Chair
├── Standard Cost: P 450.00
├── Last Purchase: P 455.00
├── Variance: P 5.00 unfavorable
├── % Variance: 1.11%
└── Action: Review pricing with supplier
```

**4. Outstanding POs Report**
```
Lists all POs:
├── Not fully received
├── Overdue deliveries
├── Awaiting invoices
└── Pending payments
```

**5. Spend Analysis**
```
By Category:
├── Office Furniture: 40%
├── IT Equipment: 25%
├── Stationery: 15%
├── Utilities: 12%
└── Other: 8%

By Supplier:
├── Top 10 suppliers = 70% spend
├── Opportunity for negotiation
└── Consolidation potential
```

---

## Best Practices

### Purchase Orders
- ✅ Always use POs for purchases
- ✅ Get competitive quotes
- ✅ Maintain approved supplier list
- ✅ Review and approve before sending
- ✅ Communicate clearly with suppliers

### Goods Receiving
- ✅ Inspect all deliveries
- ✅ Match to PO immediately
- ✅ Document damages/shortages
- ✅ Process GRN same day
- ✅ Segregate rejected items

### Supplier Management
- ✅ Regular performance reviews
- ✅ Maintain good relationships
- ✅ Negotiate better terms
- ✅ Pay on time
- ✅ Keep accurate records

### Cost Control
- ✅ Monitor price variances
- ✅ Take early payment discounts
- ✅ Consolidate purchases
- ✅ Review spend regularly
- ✅ Benchmark prices

---

## Troubleshooting

**Issue: Cannot receive against PO**
- Verify PO is approved
- Check PO not already fully received
- Ensure correct branch/location
- Check user permissions

**Issue: Invoice won't match GRN**
- Verify quantities match
- Check prices within tolerance
- Ensure same currency
- Review variance settings

**Issue: Payment failing**
- Check bank account balance
- Verify invoice is approved
- Check payment not duplicate
- Review approval limits

---

## Related Documentation
- [Supplier Management](supplier-guide.md)
- [Inventory Management](inventory-guide.md)
- [Accounts Payable](accounting-codes-guide.md)
- [Banking & Payments](banking-guide.md)
