# Sales & Invoicing Guide

## Overview
This guide covers the complete sales process from quotations to invoices, receipts, credit notes, and invoice customization in the CNPERP ERP system.

## Table of Contents
1. [Quotations](#quotations)
2. [Sales Orders](#sales-orders)
3. [Invoicing](#invoicing)
4. [Cash Sales](#cash-sales)
5. [Customer Receipts](#customer-receipts)
6. [Credit Notes & Returns](#credit-notes--returns)
7. [Invoice Customization](#invoice-customization)
8. [Invoice Reversal](#invoice-reversal)

---

## Quotations

### Creating a Quotation

1. **Navigate to Sales → Quotations**
2. **Click "New Quotation"**
3. **Fill Details:**

```
Customer Information:
├── Select Customer: ABC Company Ltd
├── Contact Person: John Smith
├── Email: john@abc.com
├── Phone: +267 1234 5678
└── Valid Until: 2025-10-30

Quotation Details:
├── Quotation Number: QUO-2025-001 (auto)
├── Date: 2025-10-15
├── Reference: Customer Ref #123
├── Sales Person: Jane Doe
├── Payment Terms: 30 days
└── Delivery Terms: Ex Works

Items:
┌──────────────────┬──────┬─────┬─────────┬────────┐
│ Product          │ Qty  │ UOM │ Price   │ Total  │
├──────────────────┼──────┼─────┼─────────┼────────┤
│ Office Chair     │ 20   │ EA  │ 750.00  │15,000  │
│ Desk Lamp        │ 50   │ EA  │ 125.00  │ 6,250  │
│ Filing Cabinet   │ 10   │ EA  │ 450.00  │ 4,500  │
└──────────────────┴──────┴─────┴─────────┴────────┘

Pricing:
├── Subtotal:           P 25,750.00
├── VAT @ 14%:          P  3,605.00
└── Total:              P 29,355.00

Notes & Terms:
├── Special Instructions: Delivery to Head Office
├── Terms & Conditions: Standard T&Cs apply
└── Validity: Quote valid for 30 days
```

4. **Save as Draft** or **Send to Customer**

### Converting Quotation to Sales Order

1. **Open Quotation**
2. **Click "Convert to Sales Order"**
3. **Review & Confirm**
4. **Sales Order Created**

---

## Sales Orders

### Creating Sales Order

```
Order Information:
├── Customer: ABC Company Ltd
├── Order Number: SO-2025-100 (auto)
├── Order Date: 2025-10-15
├── Expected Delivery: 2025-10-22
├── Payment Terms: 30 days net
└── Branch: Head Office

Order Items:
- Same as quotation or manual entry
- Stock allocation happens automatically
- Checks available stock

Order Status:
├── Draft → Confirmed → Preparing → Dispatched → Delivered
└── Can be cancelled before dispatch
```

### Stock Allocation

**Automatic on Order Confirmation:**
```
Product: Office Chair
├── Available Stock: 100 EA
├── Order Quantity: 20 EA
├── After Allocation:
│   ├── Physical Stock: 100 EA (unchanged)
│   ├── Allocated: 20 EA
│   └── Available: 80 EA
```

### Partial Delivery

**If stock insufficient:**
```
Order: 50 units
Available: 30 units

Option 1: Partial Delivery
├── Deliver 30 units now
├── Remaining 20 on backorder
└── Second delivery when stock arrives

Option 2: Wait for full delivery
├── Don't dispatch until all 50 available
```

---

## Invoicing

### Standard Invoice Creation

1. **Navigate to Sales → Invoices**
2. **Click "Create Invoice"**
3. **Fill Invoice Details:**

```
Invoice Header:
├── Invoice Number: INV-2025-1001 (auto)
├── Invoice Date: 2025-10-15
├── Due Date: 2025-11-14 (30 days)
├── Customer: ABC Company Ltd
├── Customer PO: PO-12345
├── Sales Person: Jane Doe
└── Branch: Head Office

Billing & Shipping:
├── Bill To:
│   ABC Company Ltd
│   Plot 123, Main Road
│   Gaborone, Botswana
│
└── Ship To:
    Branch Office
    Plot 456, Industrial Road
    Francistown, Botswana

Invoice Items:
┌────────────────┬─────┬─────┬────────┬────────┬──────────┐
│ Description    │ Qty │ UOM │ Price  │ VAT %  │ Amount   │
├────────────────┼─────┼─────┼────────┼────────┼──────────┤
│ Office Chair   │ 20  │ EA  │ 750.00 │ 14%    │ 15,000.00│
│ Desk Lamp      │ 50  │ EA  │ 125.00 │ 14%    │  6,250.00│
│ Delivery Charge│  1  │ EA  │ 500.00 │ 14%    │    500.00│
└────────────────┴─────┴─────┴────────┴────────┴──────────┘

Financial Summary:
├── Subtotal (excl VAT):     P 21,750.00
├── VAT @ 14%:               P  3,045.00
├── Total Amount:            P 24,795.00
├── Amount Paid:             P  0.00
└── Balance Due:             P 24,795.00

Payment Information:
├── Payment Terms: Net 30 days
├── Payment Methods: Bank Transfer, Cheque
├── Bank Details: Standard Bank, Acc: 1234567890
└── Reference: Please quote invoice number

Notes:
├── Internal Notes: (not printed)
├── Customer Notes: Thank you for your business
└── Terms & Conditions: (from settings)
```

4. **Save** or **Save & Print**

### Invoice from Sales Order

1. **Open Sales Order**
2. **Click "Create Invoice"**
3. **System pre-fills from order**
4. **Review & Adjust if needed**
5. **Post Invoice**

**Accounting Impact:**
```
Debit:  Accounts Receivable - ABC  P 24,795.00
Credit: Sales Revenue              P 21,750.00
Credit: VAT Output                 P  3,045.00
```

**At same time (Perpetual Inventory):**
```
Debit:  Cost of Goods Sold        P 12,500.00
Credit: Inventory                 P 12,500.00
```

### Invoice Designer

**Access: Sales → Invoice Designer**

Full A4 page invoice creator with:
- Click-to-edit fields
- Customer dropdown or manual entry
- Dynamic items table (add/remove rows)
- Live calculations (subtotal, VAT, total)
- Print & save functionality
- Professional layout

**Features:**
- Real-time preview
- Customer selection from database
- Product dropdown with prices
- Automatic VAT calculation
- Save as draft or finalize
- Print to PDF

---

## Cash Sales

### Creating Cash Sale Invoice

1. **Navigate to Sales → Cash Sales**
2. **Click "New Cash Sale"**
3. **Quick Entry:**

```
Customer: Walk-in Customer (optional name/phone)
Payment Method: Cash/Card/Mobile Money

Items:
├── Scan barcode or select product
├── Enter quantity
├── Price auto-fills
└── Add to cart

Cart:
┌─────────────┬─────┬────────┬──────────┐
│ Product     │ Qty │ Price  │ Total    │
├─────────────┼─────┼────────┼──────────┤
│ Notebook A4 │  5  │  12.50 │   62.50  │
│ Pen Blue    │ 12  │   3.00 │   36.00  │
└─────────────┴─────┴────────┴──────────┘

Payment:
├── Subtotal:          P  98.50
├── VAT @ 14%:         P  13.79
├── Total:             P 112.29
├── Amount Tendered:   P 150.00
└── Change Due:        P  37.71
```

4. **Process Payment**

**System automatically:**
- Creates invoice
- Records payment
- Updates inventory
- Generates receipt
- Opens cash drawer
- Prints receipt

**Accounting Impact:**
```
Debit:  Cash on Hand              P 112.29
Credit: Sales Revenue             P  98.50
Credit: VAT Output                P  13.79

Debit:  Cost of Goods Sold        P  45.20
Credit: Inventory                 P  45.20
```

### Amount Tendered & Change

**Cash Payment Fields:**
```
Total Amount:        P 112.29
Amount Tendered:     P 150.00  (user enters)
Change Due:          P  37.71  (auto-calculated)

Validation:
- Amount tendered must be ≥ total amount
- Change calculated automatically
- Shows on receipt
```

### Cash Sale Receipt

**Automatically Generated Receipt:**
```
================================
       YOUR COMPANY NAME
       Plot 123, Main Road
         Gaborone, BW
      Tel: +267 1234 5678
================================

CASH SALE RECEIPT

Receipt No: RCP-2025-0001
Invoice No: INV-2025-1001
Date: 15 Oct 2025 14:35:22
Cashier: Jane Doe
================================

Notebook A4         5 x 12.50
                         62.50

Pen Blue           12 x 3.00
                         36.00
--------------------------------
Subtotal:                98.50
VAT @ 14%:               13.79
--------------------------------
TOTAL:                  112.29

Amount Tendered:        150.00
Change:                  37.71
================================
Payment Method: Cash

Thank you for your business!
================================
```

---

## Customer Receipts

### Recording Customer Payment

**For Credit Sales:**

1. **Navigate to Sales → Receipts**
2. **Click "New Receipt"**
3. **Enter Details:**

```
Receipt Information:
├── Customer: ABC Company Ltd
├── Receipt Number: RCP-2025-0100 (auto)
├── Receipt Date: 2025-10-20
├── Amount Received: P 24,795.00
├── Payment Method: Bank Transfer
└── Reference: Customer Ref TRF-12345

Payment Details:
├── Bank Account: Standard Bank Checking
├── Deposit Date: 2025-10-20
├── Cleared: Yes
└── Bank Statement Ref: 20251020-001

Allocate to Invoices:
┌──────────────┬────────────┬──────────┬─────────┐
│ Invoice No   │ Inv Date   │ Amount   │ Paying  │
├──────────────┼────────────┼──────────┼─────────┤
│ INV-2025-1001│ 2025-10-15 │ 24,795.00│ 24,795.00│
└──────────────┴────────────┴──────────┴─────────┘

Total Allocated: P 24,795.00
Unallocated:     P 0.00
```

4. **Post Receipt**

**Accounting Impact:**
```
Debit:  Bank - Standard Bank       P 24,795.00
Credit: Accounts Receivable - ABC  P 24,795.00
```

### Partial Payment

```
Invoice Amount: P 50,000.00
Payment: P 30,000.00

Allocation:
├── Applied to Invoice: P 30,000.00
├── Outstanding Balance: P 20,000.00
└── Invoice Status: Partially Paid
```

### Payment on Account (Advance)

```
Customer pays without invoice:
├── Amount: P 10,000.00
├── No invoice allocation
├── Creates customer credit balance
└── Applied to future invoices
```

**Accounting:**
```
Debit:  Bank                       P 10,000.00
Credit: Customer Deposits Liability P 10,000.00
```

---

## Credit Notes & Returns

### Creating Credit Note

1. **Navigate to Sales → Credit Notes**
2. **Click "New Credit Note"**
3. **Fill Details:**

```
Credit Note Information:
├── Credit Note Number: CN-2025-001 (auto)
├── Date: 2025-10-16
├── Original Invoice: INV-2025-1001
├── Customer: ABC Company Ltd
├── Return Reason: Damaged goods
└── Return Description: Items damaged in transit

Return Items:
┌─────────────┬──────┬────────┬────────────┬──────────┐
│ Product     │ Qty  │ Price  │ Condition  │ Amount   │
├─────────────┼──────┼────────┼────────────┼──────────┤
│ Office Chair│  2   │ 750.00 │ Damaged    │ 1,500.00 │
└─────────────┴──────┴────────┴────────────┴──────────┘

Credit Amount:
├── Subtotal:           P 1,315.79
├── VAT @ 14%:          P   184.21
└── Total Credit:       P 1,500.00

Refund Method:
○ Cash Refund
○ Bank Transfer
● Credit to Account
○ Store Credit

Processing:
├── Status: Draft
├── Requires Approval: Yes
└── Approved By: (Manager)
```

4. **Submit for Approval**
5. **After Approval → Process Refund**

### Refund Methods

**1. Cash Refund:**
```
For cash sales:
├── Immediate cash payment
├── Receipt issued
└── Cash drawer reduces

Accounting:
Debit:  Sales Returns        P 1,315.79
Debit:  VAT Output           P   184.21
Credit: Cash on Hand         P 1,500.00
```

**2. Bank Transfer:**
```
For credit card/bank payments:
├── Customer bank details captured
├── Transfer processed
└── Reference recorded

Accounting:
Debit:  Sales Returns        P 1,315.79
Debit:  VAT Output           P   184.21
Credit: Bank Account         P 1,500.00
```

**3. Credit to Account:**
```
For account customers:
├── Creates credit balance
├── Applied to future invoices
└── Shows on customer statement

Accounting:
Debit:  Sales Returns        P 1,315.79
Debit:  VAT Output           P   184.21
Credit: Accounts Receivable  P 1,500.00
```

**4. Store Credit:**
```
Non-refundable credit:
├── Valid for future purchases
├── Expiry date option
└── Tracked separately

Accounting:
Debit:  Sales Returns        P 1,315.79
Debit:  VAT Output           P   184.21
Credit: Store Credit Liability P 1,500.00
```

### Inventory Handling

**Good Condition:**
```
Items returned in good condition:
├── Add back to inventory
├── Increase stock quantity
└── Restores to available stock

Accounting:
Debit:  Inventory            P 900.00
Credit: Cost of Goods Sold   P 900.00
```

**Damaged Condition:**
```
Items damaged/faulty:
├── DO NOT add to inventory
├── Record as loss/write-off
└── May claim from supplier/insurance

Accounting:
Debit:  Stock Loss Expense   P 900.00
Credit: Cost of Goods Sold   P 900.00
```

---

## Invoice Customization

### Accessing Customization

**Navigate to: Settings → Invoice Customization**

### Customization Options

#### 1. General Settings
```
Company Logo:
├── Upload logo image
├── Logo position: Left/Center/Right
├── Logo size: Small/Medium/Large
└── Logo URL or base64

Paper & Layout:
├── Paper Size: A4/Letter/Custom
├── Orientation: Portrait/Landscape
├── Margins: Top/Bottom/Left/Right
└── Template Style: Modern/Classic/Minimal
```

#### 2. Header Customization
```
Colors & Styling:
├── Header Background: #2C3E50
├── Header Text Color: #FFFFFF
├── Border Style: Solid/Dashed/None
├── Border Width: 1-5px
└── Font Family: Arial/Times/Helvetica

Header Content:
├── Show/Hide Company Logo
├── Show/Hide Company Name
├── Invoice Title Text
└── Title Font Size
```

#### 3. Company Information
```
Details Displayed:
├── Company Name
├── Address (multiple lines)
├── Contact Numbers
├── Email Address
├── Tax ID/VAT Number
├── Company Registration
└── Website URL

Styling:
├── Font size
├── Alignment
└── Spacing
```

#### 4. Invoice Title
```
Customization:
├── Title Text: "INVOICE" / "TAX INVOICE" / Custom
├── Font Size: 18-36pt
├── Color: Custom color picker
├── Font Weight: Normal/Bold
└── Alignment: Left/Center/Right
```

#### 5. Customer Section
```
Layout:
├── Label Style: Bold/Normal
├── Border: Yes/No
├── Background Color
└── Padding

Fields Shown:
├── Customer Name
├── Address
├── Contact Details
├── Tax Number
└── Customer Code
```

#### 6. Items Table
```
Table Styling:
├── Header Background: #34495E
├── Header Text Color: #FFFFFF
├── Row Striping: Yes/No
├── Stripe Color: #ECF0F1
├── Border Style: Grid/Horizontal/None
└── Font Size: 8-12pt

Columns:
├── Item Description
├── Quantity
├── UOM
├── Unit Price
├── VAT %
├── Line Total
└── Column widths adjustable
```

#### 7. Totals Section
```
Layout:
├── Position: Right/Full Width
├── Background: Shaded/White
├── Border: Yes/No
└── Font Size: 10-14pt

Rows Displayed:
├── Subtotal
├── Discount (if applicable)
├── VAT breakdown by rate
├── Shipping/handling
├── Total Amount
├── Amount Paid
└── Balance Due
```

#### 8. Footer
```
Content:
├── Payment Terms
├── Banking Details
├── Terms & Conditions
├── Thank You Message
└── Custom Footer Text

Styling:
├── Font Size: 8-10pt
├── Border Top: Yes/No
├── Alignment: Left/Center/Right
└── Background Color
```

#### 9. Layout & Spacing
```
Control:
├── Line Spacing: 1.0-2.0
├── Section Margins
├── Padding between elements
└── Overall page margins
```

#### 10. Color Schemes
```
Pre-defined Themes:
├── Professional Blue
├── Corporate Gray
├── Modern Green
├── Classic Black & White
└── Custom (create your own)

Color Picker:
├── Primary Color
├── Secondary Color
├── Accent Color
└── Text Color
```

### Live Preview

- See changes instantly
- Print preview mode
- Export sample PDF
- Save templates

---

## Invoice Reversal

### When to Reverse

- Invoice created in error
- Wrong customer
- Incorrect amounts
- Need to cancel sale

**Do NOT use for returns** - Use Credit Notes instead

### Reversal Process

1. **Open Invoice**
2. **Click "Reverse Invoice"**
3. **Enter Reason:**
```
Reversal Reason: [Select from dropdown]
├── Created in error
├── Duplicate invoice
├── Wrong customer
└── Other (specify)

Description: [Detailed explanation]
Reversal Date: [Today or backdated]
```

4. **Confirm Reversal**

**What Happens:**
- Original invoice marked as "REVERSED"
- Reversal journal entry created
- Inventory adjustments (if dispatched)
- Stock allocation released
- Cannot be edited or paid

**Accounting Impact:**
```
Original Invoice:
Debit:  Accounts Receivable    P 24,795.00
Credit: Sales Revenue          P 21,750.00
Credit: VAT Output             P  3,045.00

Reversal Entry:
Debit:  Sales Revenue          P 21,750.00
Debit:  VAT Output             P  3,045.00
Credit: Accounts Receivable    P 24,795.00

Net Effect: All balances back to zero
```

---

## Best Practices

### Invoicing
- ✅ Set clear payment terms
- ✅ Always include tax information
- ✅ Reference customer PO numbers
- ✅ Verify customer details before issuing
- ✅ Send invoices promptly

### Cash Sales
- ✅ Always count change carefully
- ✅ Print receipts for all sales
- ✅ Reconcile cash drawer daily
- ✅ Bank cash frequently
- ✅ Keep small denominations for change

### Returns
- ✅ Inspect returned items
- ✅ Get manager approval for large returns
- ✅ Document item condition
- ✅ Process refunds promptly
- ✅ Track return patterns

### Security
- 🔒 Limit who can reverse invoices
- 🔒 Require approval for credit notes
- 🔒 Segregate sales and receipts duties
- 🔒 Regular AR aging reviews
- 🔒 Follow-up on overdue accounts

---

## Troubleshooting

**Issue: Invoice won't save**
- Check required fields filled
- Verify customer selected
- Ensure at least one line item
- Check VAT configuration

**Issue: Wrong VAT calculated**
- Verify product VAT category
- Check customer VAT status
- Review app settings VAT rate
- Recalculate invoice

**Issue: Cannot reverse invoice**
- Check if already paid
- Verify user permissions
- Use credit note if for returns
- Contact administrator

---

## Related Documentation
- [Customer Management](customer-guide.md)
- [Product Setup](inventory-guide.md)
- [Accounting Integration](accounting-codes-guide.md)
- [Receipt & Payment Processing](receipts-guide.md)
