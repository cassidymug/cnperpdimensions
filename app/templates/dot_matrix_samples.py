"""
Sample Dot Matrix Templates

This file contains sample templates for different business needs and printer configurations.
"""

# Standard 80-column template for Epson LX-300+
STANDARD_80_TEMPLATE = """
                    {company_name}
                    ================
{company_address}
Phone: {company_phone} | Email: {company_email}
Tax: {tax_number} | VAT: {vat_number}

                    TAX INVOICE
                    ===========

Invoice No: {invoice_number}         Date: {invoice_date}
Due Date: {due_date}                 Terms: {payment_terms} days

BILL TO:
--------
{customer_name}
{customer_address}
Phone: {customer_phone}
Email: {customer_email}
VAT No: {customer_vat}

ITEMS:
------
{invoice_items}

                              Subtotal: {currency_symbol}{subtotal}
                              VAT Total: {currency_symbol}{vat_amount}
                              ===========================
                              TOTAL: {currency_symbol}{total_amount}

Payment is due within {payment_terms} days of invoice date.

Notes: {notes}

Thank you for your business!

_______________________________
Authorized Signature
"""

# Compact template for small invoices
COMPACT_TEMPLATE = """
{company_name} | Tax: {tax_number}
{company_phone}

INVOICE: {invoice_number} | {invoice_date}
TO: {customer_name}

{invoice_items}

TOTAL: {currency_symbol}{total_amount}
Due: {due_date}

Thank you!
"""

# Wide 136-column template
WIDE_136_TEMPLATE = """
                                                    {company_name}
                                                    ==============
{company_address}
Phone: {company_phone} | Email: {company_email} | Tax: {tax_number} | VAT: {vat_number}

                                                    TAX INVOICE
                                                    ===========

Invoice Number: {invoice_number}                                                    Date: {invoice_date}
Due Date: {due_date}                                                               Terms: {payment_terms} days

BILL TO:                                           SHIP TO:
--------                                           --------
{customer_name}                                    {customer_name}
{customer_address}                                 {customer_address}
Phone: {customer_phone}                           Phone: {customer_phone}
Email: {customer_email}                           Email: {customer_email}
VAT Number: {customer_vat}                        VAT Number: {customer_vat}

ITEMS:
----------------------------------------------------------------------------------------------------------------------
{invoice_items}
----------------------------------------------------------------------------------------------------------------------

                                                                                   Subtotal: {currency_symbol}{subtotal}
                                                                                   Discount: {currency_symbol}{discount_amount}
                                                                                   VAT Total: {currency_symbol}{vat_amount}
                                                                                   ============================
                                                                                   TOTAL: {currency_symbol}{total_amount}

Payment Terms: Payment is due within {payment_terms} days of invoice date.
Notes: {notes}

Thank you for your business!

_______________________________                    _______________________________
Customer Signature                                 Authorized Signature
"""

# Carbon copy optimized template
CARBON_COPY_TEMPLATE = """
{company_name}
{company_address}
{company_phone} | {tax_number}

INVOICE: {invoice_number}
DATE: {invoice_date}
TO: {customer_name}

{invoice_items}

TOTAL: {currency_symbol}{total_amount}

COPY FOR: CUSTOMER / OFFICE / ACCOUNTS
"""

# Receipt-style template
RECEIPT_TEMPLATE = """
        {company_name}
        ==============
        {company_phone}
        
Invoice: {invoice_number}
Date: {invoice_date}
Customer: {customer_name}

{invoice_items}

Subtotal: {currency_symbol}{subtotal}
VAT: {currency_symbol}{vat_amount}
Total: {currency_symbol}{total_amount}

Thank you!
"""

# Service invoice template
SERVICE_TEMPLATE = """
{company_name}
{company_address}
Phone: {company_phone} | Email: {company_email}
Tax Number: {tax_number} | VAT Number: {vat_number}

                SERVICE INVOICE
                ===============

Invoice Number: {invoice_number}
Service Date: {invoice_date}
Due Date: {due_date}

SERVICE PROVIDED TO:
-------------------
{customer_name}
{customer_address}
Phone: {customer_phone}
Email: {customer_email}

SERVICES RENDERED:
------------------
{invoice_items}

                        Subtotal: {currency_symbol}{subtotal}
                        VAT ({vat_rate}%): {currency_symbol}{vat_amount}
                        =============================
                        TOTAL AMOUNT: {currency_symbol}{total_amount}

PAYMENT TERMS: {payment_terms} days net

Additional Notes:
{notes}

Thank you for choosing our services!

This invoice is computer generated and does not require signature.
"""

# All templates dictionary
SAMPLE_TEMPLATES = {
    'standard_80': {
        'name': 'Standard 80 Column',
        'template': STANDARD_80_TEMPLATE,
        'settings': {
            'width': 80,
            'form_length': 66,
            'compressed': False
        }
    },
    'compact': {
        'name': 'Compact Receipt',
        'template': COMPACT_TEMPLATE,
        'settings': {
            'width': 80,
            'form_length': 44,
            'compressed': False
        }
    },
    'wide_136': {
        'name': 'Wide 136 Column',
        'template': WIDE_136_TEMPLATE,
        'settings': {
            'width': 136,
            'form_length': 66,
            'compressed': False
        }
    },
    'carbon_copy': {
        'name': 'Carbon Copy Optimized',
        'template': CARBON_COPY_TEMPLATE,
        'settings': {
            'width': 80,
            'form_length': 44,
            'compressed': False,
            'copies': 3
        }
    },
    'receipt': {
        'name': 'Receipt Style',
        'template': RECEIPT_TEMPLATE,
        'settings': {
            'width': 80,
            'form_length': 44,
            'compressed': True
        }
    },
    'service': {
        'name': 'Service Invoice',
        'template': SERVICE_TEMPLATE,
        'settings': {
            'width': 80,
            'form_length': 66,
            'compressed': False
        }
    }
}
