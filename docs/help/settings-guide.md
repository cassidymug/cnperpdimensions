# System Settings & Configuration Guide

## Overview
This comprehensive guide covers all system settings and configuration options in the CNPERP ERP system, from basic application settings to advanced customization.

## Table of Contents
1. [Application Settings](#application-settings)
2. [Company Information](#company-information)
3. [Currency & Localization](#currency--localization)
4. [VAT & Tax Settings](#vat--tax-settings)
5. [Invoice Customization](#invoice-customization)
6. [Email Configuration](#email-configuration)
7. [Printer Settings](#printer-settings)
8. [User Management](#user-management)
9. [Branch Settings](#branch-settings)
10. [Security Settings](#security-settings)

---

## Application Settings

### Accessing Settings

**Navigate to: Settings → Application Settings**

### General Settings

```
System Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Basic Information:
├── System Name: CNPERP ERP System
├── System Version: 2.0.1
├── Environment: Production/Development/Testing
├── Installation Date: 2025-01-15
└── License Key: XXXX-XXXX-XXXX-XXXX

Business Year:
├── Financial Year Start: 1 April
├── Financial Year End: 31 March
├── Current Period: October 2025
├── Locked Periods: Jan-Sep 2025
└── Auto Close Period: Yes (after 45 days)

Date & Time:
├── Date Format: DD/MM/YYYY
├── Time Format: 24 Hour
├── First Day of Week: Monday
├── Timezone: Africa/Gaborone (GMT+2)
└── Daylight Saving: No

Number Formatting:
├── Decimal Separator: . (period)
├── Thousand Separator: , (comma)
├── Decimal Places: 2
├── Negative Numbers: (1,234.56)
└── Currency Position: Before amount
```

### System Preferences

```
Feature Toggles:
├── Multi-Currency: ✓ Enabled
├── Multi-Branch: ✓ Enabled
├── Multi-Language: ⚬ Disabled
├── Inventory Management: ✓ Enabled
├── Manufacturing: ✓ Enabled
├── Project Management: ⚬ Disabled
├── Payroll: ⚬ Disabled
└── CRM: ⚬ Disabled

Inventory Settings:
├── Allow Negative Stock: ⚬ No
├── Default Costing Method: FIFO
├── Auto Allocate Stock: ✓ Yes
├── Serial Number Tracking: ✓ Enabled
├── Batch/Lot Tracking: ✓ Enabled
└── Default UOM: Each (EA)

Sales Settings:
├── Allow Credit Sales: ✓ Yes
├── Credit Limit Check: ✓ Enabled
├── Price Override: ⚬ Require Approval
├── Discount Limit: 10%
├── Auto Invoice Numbering: ✓ Enabled
└── Invoice Terms: Net 30 days

Purchase Settings:
├── Three-Way Matching: ✓ Enabled
├── PO Approval Required: ✓ Yes (>P 10,000)
├── GRN Required: ✓ Yes
├── Auto Create Bills: ⚬ No
└── Default Payment Terms: Net 30 days
```

---

## Company Information

### Company Profile

```
Company Details
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Legal Information:
├── Company Name: Your Company Name (Pty) Ltd
├── Trading Name: Your Company
├── Company Type: Private Limited Company
├── Registration Number: BW-12345678
├── Tax Number: T12345678
├── VAT Number: VAT-12345678
├── Incorporation Date: 2020-01-15
└── Business Activity: Retail & Wholesale Trade

Physical Address:
├── Address Line 1: Plot 123, Main Road
├── Address Line 2: Industrial Area
├── City: Gaborone
├── State/Region: South-East District
├── Postal Code: 0000
└── Country: Botswana

Postal Address:
├── PO Box: P.O. Box 12345
├── City: Gaborone
├── Postal Code: 0000
└── Country: Botswana

Contact Information:
├── Main Phone: +267 123 4567
├── Mobile: +267 712 3456
├── Fax: +267 123 4568
├── Email: info@yourcompany.co.bw
├── Website: www.yourcompany.co.bw
└── Support Email: support@yourcompany.co.bw

Banking Details:
├── Bank Name: Standard Bank Botswana
├── Branch: Main Branch - Gaborone
├── Branch Code: 285267
├── Account Number: 1234567890
├── Account Name: Your Company Name (Pty) Ltd
├── SWIFT Code: SBICBWGX
└── Currency: BWP

Social Media:
├── Facebook: @yourcompany
├── Twitter: @yourcompany
├── LinkedIn: company/yourcompany
└── Instagram: @yourcompany
```

### Logo Management

```
Company Branding
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Logo Settings:
├── Upload Method: File Upload/URL
├── Primary Logo: logo.png (200x80px)
├── Invoice Logo: logo_invoice.png (150x60px)
├── Email Logo: logo_email.png (180x70px)
└── Favicon: favicon.ico (32x32px)

Logo Display:
├── Show on Invoices: ✓ Yes
├── Show on Receipts: ✓ Yes
├── Show on Reports: ✓ Yes
├── Show in Email: ✓ Yes
└── Show in Login Page: ✓ Yes

Image Requirements:
├── Format: PNG, JPG, SVG
├── Max Size: 5 MB
├── Recommended: PNG with transparency
├── Min Resolution: 150x60 pixels
└── Max Resolution: 500x200 pixels
```

---

## Currency & Localization

### Currency Configuration

```
Currency Settings
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Base Currency:
├── Currency Code: BWP
├── Currency Name: Botswana Pula
├── Currency Symbol: P
├── Symbol Position: Before Amount
├── Decimal Places: 2
└── Subunit: Thebe (1/100)

Display Format:
├── Positive: P 1,234.56
├── Negative: (P 1,234.56)
├── Zero: P 0.00
├── Thousands: P 1,234,567.89
└── Small: P 0.01

Foreign Currencies:
┌──────┬──────────────┬────────┬──────────┬────────┐
│ Code │ Name         │ Symbol │ Rate     │ Active │
├──────┼──────────────┼────────┼──────────┼────────┤
│ USD  │ US Dollar    │ $      │  13.45   │   ✓    │
│ EUR  │ Euro         │ €      │  14.75   │   ✓    │
│ GBP  │ Pound        │ £      │  17.25   │   ✓    │
│ ZAR  │ Rand         │ R      │   0.72   │   ✓    │
└──────┴──────────────┴────────┴──────────┴────────┘

Exchange Rate Settings:
├── Update Frequency: Daily/Manual
├── Rate Source: Bank of Botswana/Manual
├── Default Rate Type: Buy/Sell/Mid
├── Rate Variance Alert: ± 5%
└── Auto Update: ✓ Enabled

Multi-Currency Features:
├── Foreign Currency Accounts: ✓ Enabled
├── Foreign Currency Invoicing: ✓ Enabled
├── Unrealized Gains/Losses: ✓ Track
├── Revaluation Period: Monthly
└── Conversion Rate Override: ⚬ Require Approval
```

### Regional Settings

```
Localization Settings
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Region & Language:
├── Country: Botswana
├── Language: English (British)
├── Locale Code: en_BW
├── Character Set: UTF-8
└── Text Direction: Left to Right

Date Format:
├── Short Date: DD/MM/YYYY (15/10/2025)
├── Long Date: DD MMMM YYYY (15 October 2025)
├── Time: HH:MM:SS (14:30:00)
└── DateTime: DD/MM/YYYY HH:MM (15/10/2025 14:30)

Number Format:
├── Integer: 1,234,567
├── Decimal: 1,234.56
├── Percentage: 12.5%
├── Currency: P 1,234.56
└── Phone: +267 123 4567

Paper Size:
├── Invoice: A4 (210 x 297 mm)
├── Receipt: 80mm thermal
├── Reports: A4 Portrait/Landscape
└── Labels: Various sizes
```

---

## VAT & Tax Settings

### VAT Configuration

```
VAT Settings
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VAT Registration:
├── VAT Registered: ✓ Yes
├── VAT Number: VAT-12345678
├── Registration Date: 2020-01-15
├── VAT Period: Monthly/Quarterly
├── Filing Method: Online
└── Next Filing: 15 November 2025

VAT Rates:
┌──────────────┬──────┬─────────┬────────┐
│ Category     │ Rate │ Account │ Active │
├──────────────┼──────┼─────────┼────────┤
│ Standard     │ 14%  │ 210-001 │   ✓    │
│ Zero-rated   │  0%  │ 210-002 │   ✓    │
│ Exempt       │  -   │    -    │   ✓    │
└──────────────┴──────┴─────────┴────────┘

VAT Calculation:
├── Method: Tax Exclusive/Tax Inclusive
├── Rounding: Standard (nearest cent)
├── Default Rate: 14% (Standard)
├── Apply to: Taxable items only
└── Show on Invoice: ✓ Yes (itemized)

VAT Accounts:
├── VAT Output (Sales): 210-001
├── VAT Input (Purchases): 210-002
├── VAT Payable: 210-003
├── VAT Refundable: 210-004
└── VAT on Imports: 210-005

Compliance:
├── Auto Calculate: ✓ Enabled
├── VAT Reports: Monthly
├── Audit Trail: ✓ Complete
├── IFRS Compliance: ✓ Enabled
└── E-Filing: ✓ Supported
```

### Tax Categories

```
Product Tax Categories
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Standard Rated (14%):
├── General goods & services
├── Electronics
├── Furniture
├── Stationery
└── Most retail items

Zero-Rated (0%):
├── Basic food items
├── Exported goods
├── International services
├── Educational materials
└── Medical supplies

Exempt:
├── Financial services
├── Residential rental
├── Some educational services
├── Healthcare services
└── Insurance products

Special Cases:
├── Imported goods: VAT + customs duty
├── Second-hand goods: Margin scheme
├── Tourism: Special VAT rules
└── Agriculture: Specific exemptions
```

---

## Invoice Customization

### Invoice Template Settings

```
Invoice Design
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

General Settings:
├── Template Style: Modern/Classic/Minimal
├── Paper Size: A4
├── Orientation: Portrait
├── Margins: Top 20mm, Bottom 20mm, Left/Right 15mm
└── Font Family: Arial/Helvetica/Times New Roman

Header Section:
├── Show Logo: ✓ Yes (Left/Center/Right)
├── Logo Size: Medium (150x60px)
├── Company Name: ✓ Show (24pt, Bold)
├── Company Details: ✓ Show (10pt)
├── Header Color: #2C3E50 (Dark Blue)
├── Header Text Color: #FFFFFF (White)
└── Border: 2px solid

Invoice Title:
├── Title Text: "TAX INVOICE"
├── Font Size: 28pt
├── Font Weight: Bold
├── Color: #E74C3C (Red)
├── Alignment: Right
└── Background: None/Shaded

Customer Section:
├── Show Label: ✓ "Bill To:"
├── Include: Name, Address, Tax Number
├── Font Size: 10pt
├── Border: 1px solid #BDC3C7
├── Background: #ECF0F1 (Light Gray)
└── Padding: 10px

Items Table:
├── Header Background: #34495E (Dark Gray)
├── Header Text: #FFFFFF (White)
├── Row Striping: ✓ Enabled
├── Stripe Color: #F8F9FA
├── Border Style: Grid (1px #BDC3C7)
├── Font Size: 9pt
└── Include Columns:
    ├── Item Description
    ├── Quantity
    ├── Unit Price
    ├── VAT %
    └── Line Total

Totals Section:
├── Position: Right aligned
├── Show:
    ├── Subtotal (excluding VAT)
    ├── VAT Amount (14%)
    ├── Discount (if applicable)
    ├── Shipping/Handling
    └── Total Amount
├── Total Font Size: 14pt (Bold)
├── Background: #ECF0F1
└── Border: 2px solid #2C3E50

Footer Section:
├── Payment Terms: ✓ Show
├── Bank Details: ✓ Show
├── Terms & Conditions: ✓ Show
├── Thank You Message: ✓ Show
├── Font Size: 8pt
├── Border Top: 1px solid
└── Custom Footer Text: Optional

Color Schemes (Pre-defined):
├── Professional Blue: #2C3E50, #3498DB
├── Corporate Gray: #7F8C8D, #BDC3C7
├── Modern Green: #27AE60, #2ECC71
├── Classic Black: #2C3E50, #ECF0F1
└── Custom: Define your own
```

### Invoice Numbering

```
Document Numbering
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Invoice Numbering:
├── Format: INV-{YYYY}-{NNNN}
├── Example: INV-2025-0001
├── Next Number: 1001
├── Prefix: INV-
├── Year Format: YYYY
├── Separator: - (hyphen)
├── Padding: 4 digits
└── Reset: Annually/Never

Other Documents:
├── Quotation: QUO-{YYYY}-{NNNN}
├── Sales Order: SO-{YYYY}-{NNNN}
├── Receipt: RCP-{YYYY}-{NNNN}
├── Credit Note: CN-{YYYY}-{NNNN}
├── Purchase Order: PO-{YYYY}-{NNNN}
├── GRN: GRN-{YYYY}-{NNNN}
└── Payment: PAY-{YYYY}-{NNNN}

Customization:
├── Include Branch Code: ⚬ Optional
├── Include User ID: ⚬ Optional
├── Custom Prefix: Configurable
├── Auto Increment: ✓ Yes
└── Manual Override: ⚬ Require Approval
```

---

## Email Configuration

### SMTP Settings

```
Email Server Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SMTP Server:
├── Host: smtp.gmail.com (or your mail server)
├── Port: 587 (TLS) / 465 (SSL) / 25 (Plain)
├── Encryption: TLS/SSL/None
├── Authentication: ✓ Required
├── Username: your-email@company.com
├── Password: ****************
└── Timeout: 30 seconds

Sender Information:
├── From Name: Your Company Name
├── From Email: noreply@company.com
├── Reply To: info@company.com
├── BCC All Emails: ⚬ No
└── Default Subject Prefix: [Your Company]

Email Templates:
├── Invoice Email
├── Receipt Email
├── Statement Email
├── Payment Reminder
├── Welcome Email
└── Password Reset

Test Connection:
├── Send Test Email To: admin@company.com
├── Status: ✓ Connection Successful
└── Last Test: 2025-10-15 14:30
```

### Email Templates

```
Invoice Email Template
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Subject:
Invoice {{invoice_number}} from {{company_name}}

Body:
Dear {{customer_name}},

Thank you for your business. Please find attached 
invoice {{invoice_number}} dated {{invoice_date}}.

Invoice Summary:
- Invoice Number: {{invoice_number}}
- Invoice Date: {{invoice_date}}
- Due Date: {{due_date}}
- Amount: {{currency}} {{total_amount}}

Payment Details:
Bank: {{bank_name}}
Account: {{account_number}}
Reference: {{invoice_number}}

Please remit payment by {{due_date}}.

If you have any questions, please contact us at
{{support_email}} or {{phone}}.

Best regards,
{{company_name}}

---
This is an automated email. Please do not reply.

Attachments:
├── Invoice PDF: ✓ Auto-attach
├── Terms & Conditions: ⚬ Optional
└── Payment Form: ⚬ Optional

Variables Available:
├── {{company_name}}
├── {{customer_name}}
├── {{invoice_number}}
├── {{invoice_date}}
├── {{due_date}}
├── {{total_amount}}
├── {{currency}}
├── {{support_email}}
└── {{phone}}
```

---

## Printer Settings

### Receipt Printer Configuration

```
POS Receipt Printer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Hardware Settings:
├── Printer Type: Thermal/Dot Matrix/Inkjet
├── Printer Name: EPSON TM-T88V
├── Connection: USB/Network/Bluetooth
├── Port: COM1 / IP Address
├── Paper Width: 80mm / 58mm
├── Auto Cut: ✓ Enabled
├── Drawer Kick: ✓ Enabled
└── Test Print: Available

Receipt Format:
├── Logo: ✓ Print at top
├── Header: Company name & address
├── Items: Product, Qty, Price
├── Separator: Dashed line
├── Totals: Subtotal, VAT, Total
├── Payment: Method, Tendered, Change
├── Footer: Thank you message
└── Barcode: ⚬ Optional

Layout:
├── Font Size: Small/Medium/Large
├── Text Alignment: Left/Center
├── Line Spacing: Normal/Condensed
├── Cut Paper After: ✓ Every receipt
└── Number of Copies: 1
```

### Document Printer Configuration

```
Invoice & Report Printer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Printer Settings:
├── Default Printer: HP LaserJet Pro
├── Paper Size: A4 (210 x 297 mm)
├── Orientation: Portrait/Landscape (auto)
├── Quality: Standard/High/Draft
├── Color: Color/Grayscale
├── Duplex: ✓ Two-sided printing
└── Collate: ✓ Enabled

Page Setup:
├── Top Margin: 20mm
├── Bottom Margin: 20mm
├── Left Margin: 15mm
├── Right Margin: 15mm
├── Header Space: 10mm
└── Footer Space: 10mm

Print Options:
├── Auto Print Invoices: ⚬ No
├── Auto Print Receipts: ⚬ No
├── Print Preview: ✓ Always show
├── Save as PDF Option: ✓ Enabled
└── Watermark: Draft/Confidential/None
```

---

## User Management

### User Roles & Permissions

```
Role Management
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Pre-defined Roles:
├── Super Administrator
│   └── Full system access
├── Administrator
│   └── All except system settings
├── Manager
│   └── Branch management & reporting
├── Accountant
│   └── Financial transactions & reports
├── Sales Person
│   └── Sales, customers, quotations
├── Cashier
│   └── POS & cash sales only
├── Warehouse
│   └── Inventory & stock management
└── Viewer
    └── Read-only access

Custom Roles:
├── Create custom roles
├── Assign specific permissions
├── Clone existing roles
├── Set role hierarchy
└── Define approval limits

Permission Categories:
├── Dashboard: View, Edit
├── Sales: Create, Edit, Delete, Approve
├── Purchases: Create, Edit, Delete, Approve
├── Inventory: Create, Edit, Delete, Adjust
├── Accounting: View, Post, Reverse
├── Reports: View, Export, Schedule
├── Settings: View, Edit, System Settings
└── Users: Create, Edit, Delete, Assign Roles
```

### User Account Settings

```
User Profile
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Account Information:
├── Username: john.doe
├── Full Name: John Doe
├── Email: john.doe@company.com
├── Phone: +267 712 3456
├── Employee ID: EMP-001
├── Department: Sales
├── Branch: Head Office
└── Status: Active

Role & Permissions:
├── Primary Role: Sales Person
├── Additional Roles: None
├── Custom Permissions: None
├── Approval Limit: P 10,000
└── Access Level: Standard

Security Settings:
├── Two-Factor Auth: ✓ Enabled
├── Login Notifications: ✓ Enabled
├── Session Timeout: 30 minutes
├── Allowed IP: Any/Specific
├── Password Last Changed: 2025-09-15
└── Failed Login Attempts: 0

Preferences:
├── Language: English
├── Date Format: DD/MM/YYYY
├── Time Zone: Africa/Gaborone
├── Theme: Light/Dark
├── Default Dashboard: Sales
└── Email Notifications: ✓ Enabled
```

---

## Branch Settings

### Branch Configuration

```
Branch Management
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Branch Information:
├── Branch Code: HO
├── Branch Name: Head Office
├── Branch Type: Main/Sub-branch
├── Status: Active
├── Opening Date: 2020-01-15
└── Manager: Jane Doe

Location:
├── Address: Plot 123, Main Road
├── City: Gaborone
├── Phone: +267 123 4567
├── Email: headoffice@company.com
└── Operating Hours: 08:00 - 17:00

Settings:
├── Default Currency: BWP
├── Allow Sales: ✓ Yes
├── Allow Purchases: ✓ Yes
├── Has Warehouse: ✓ Yes
├── Has POS: ✓ Yes
├── Stock Allocation: ✓ Automatic
└── Inter-branch Transfer: ✓ Enabled

Accounting:
├── Has Own GL: ⚬ No (consolidated)
├── Cost Center: CC-HO
├── Profit Center: PC-HO
└── Budget Code: BUD-HO-2025

Users Assigned:
├── Total Users: 15
├── Managers: 2
├── Sales Staff: 8
├── Warehouse: 3
└── Admin: 2
```

---

## Security Settings

### System Security

```
Security Configuration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Password Policy:
├── Minimum Length: 8 characters
├── Require Uppercase: ✓ Yes
├── Require Lowercase: ✓ Yes
├── Require Numbers: ✓ Yes
├── Require Special Chars: ✓ Yes
├── Password History: Remember last 5
├── Password Expiry: 90 days
└── Enforce on Next Login: ⚬ Optional

Login Security:
├── Max Failed Attempts: 5
├── Account Lockout: 30 minutes
├── Session Timeout: 30 minutes
├── Remember Me: ✓ 7 days
├── Force Logout: After business hours
└── IP Whitelist: ⚬ Optional

Two-Factor Authentication:
├── 2FA Required: ⚬ For Admins Only / All Users
├── 2FA Method: Email/SMS/Authenticator App
├── Backup Codes: ✓ Generate 10 codes
└── Recovery Options: Email/Phone

Audit & Logging:
├── Log All Logins: ✓ Enabled
├── Log Failed Attempts: ✓ Enabled
├── Log User Actions: ✓ Enabled
├── Log System Changes: ✓ Enabled
├── Retention Period: 2 years
└── Daily Backup: ✓ Enabled

Data Protection:
├── Database Encryption: ✓ Enabled
├── SSL/TLS: ✓ Required
├── API Rate Limiting: ✓ Enabled
├── CORS Policy: Configured
└── XSS Protection: ✓ Enabled
```

---

## Best Practices

### Settings Management
- ✅ Review settings quarterly
- ✅ Document all changes
- ✅ Test before applying to production
- ✅ Backup settings before changes
- ✅ Train users on new settings

### Security
- ✅ Enforce strong passwords
- ✅ Enable 2FA for all users
- ✅ Regular security audits
- ✅ Keep software updated
- ✅ Monitor login attempts

### Customization
- ✅ Maintain brand consistency
- ✅ Test on different devices
- ✅ Keep templates simple
- ✅ Use standard formats
- ✅ Document customizations

---

## Troubleshooting

**Issue: Can't save settings**
- Check user permissions
- Verify all required fields
- Check for validation errors
- Review system logs

**Issue: Email not sending**
- Test SMTP connection
- Verify credentials
- Check firewall settings
- Review email logs

**Issue: Printer not working**
- Check printer connection
- Verify printer name
- Test print from system
- Check paper/ink

---

## Related Documentation
- [Initial Setup](setup-configuration-guide.md)
- [User Management](user-guide.md)
- [Security Setup](security-guide.md)
- [Invoice Customization](invoice-customization-guide.md)
