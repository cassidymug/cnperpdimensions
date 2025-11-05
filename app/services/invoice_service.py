"""
Comprehensive Invoice Service

This service handles invoice creation, PDF generation, accounting integration,
and WhatsApp/email delivery for tax-compliant invoices.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
import uuid
from io import BytesIO
import os

# PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from app.models.sales import Invoice, InvoiceItem, Customer
from app.models.inventory import Product, InventoryTransaction
from app.models.branch import Branch
from app.models.user import User
from app.models.app_setting import AppSetting
from app.models.accounting import JournalEntry, AccountingEntry, AccountingCode
from app.core.database import get_db


class InvoiceService:
    """Comprehensive invoice management service"""
    
    def __init__(self, db: Session):
        self.db = db
        self._app_setting_instance: Optional[AppSetting] = None
        self.app_settings = self._load_app_settings()
        self.invoice_designer_config = self._load_invoice_designer_config()
    
    def _load_app_settings(self) -> Dict:
        """Load application settings for invoice generation"""
        settings: Dict[str, str] = {}
        app_settings = self.db.query(AppSetting).all()
        # Two possible schemas:
        # 1. Key/Value rows (legacy) where each row has 'key' and 'value' columns
        # 2. Singleton settings row with many explicit columns (current model)
        if app_settings:
            first = app_settings[0]
            if hasattr(first, 'invoice_designer_config'):
                self._app_setting_instance = first
            if hasattr(first, 'key') and hasattr(first, 'value'):
                # Legacy style: multiple key/value rows
                for setting in app_settings:
                    try:
                        settings[str(setting.key)] = str(setting.value)
                    except Exception:
                        continue
            else:
                # Singleton style: only use the first row; extract column values
                # Avoid SQLAlchemy internal attributes
                cols = [c.name for c in first.__table__.columns]
                for col in cols:
                    try:
                        val = getattr(first, col)
                        # Skip id/meta fields if desired
                        settings[col] = '' if val is None else str(val)
                    except Exception:
                        continue
        
        # Default values if not set
        defaults = {
            'company_name': 'Your Company Name',
            'address': 'Company Address',
            'phone': 'Phone Number',
            'email': 'email@company.com',
            'website': 'www.company.com',
            'vat_registration_number': 'VAT123456789',
            'currency': 'BWP',
            'default_vat_rate': '12.0',
            'whatsapp_number': '',
            'whatsapp_api_key': '',
            'whatsapp_enabled': 'false'
        }
        
        for key, default_value in defaults.items():
            if key not in settings:
                settings[key] = default_value
        
        return settings

    def _load_invoice_designer_config(self) -> Dict[str, Any]:
        """Load saved invoice designer layout configuration."""
        settings_row = self._app_setting_instance

        if not settings_row or not hasattr(settings_row, 'invoice_designer_config'):
            settings_row = self.db.query(AppSetting).first()
            if settings_row and hasattr(settings_row, 'invoice_designer_config'):
                self._app_setting_instance = settings_row

        if settings_row and hasattr(settings_row, 'invoice_designer_config'):
            try:
                config = settings_row.invoice_designer_config
                if isinstance(config, dict):
                    return config
            except Exception as exc:
                print(f"[INVOICE_DESIGNER_CONFIG_WARN] Failed to load designer config: {exc}")

        return {
            "layout": [],
            "form_data": {},
            "metadata": {},
            "version": 1,
            "updated_at": None,
        }
    
    def _map_css_font_to_reportlab(self, css_font_family: str) -> str:
        """Map CSS font family to valid ReportLab font names"""
        # Clean up the font family string
        font_family = css_font_family.lower().strip()
        
        # Handle comma-separated font families (take the first valid one)
        if ',' in font_family:
            fonts = [f.strip() for f in font_family.split(',')]
            font_family = fonts[0]
        
        # Font mapping from CSS names to ReportLab names
        font_mapping = {
            'arial': 'Helvetica',
            'helvetica': 'Helvetica',
            'times': 'Times-Roman',
            'times new roman': 'Times-Roman',
            'courier': 'Courier',
            'courier new': 'Courier',
            'georgia': 'Times-Roman',
            'verdana': 'Helvetica',
            'tahoma': 'Helvetica',
            'trebuchet ms': 'Helvetica',
            'sans-serif': 'Helvetica',
            'serif': 'Times-Roman',
            'monospace': 'Courier'
        }
        
        # Return mapped font or default to Helvetica
        return font_mapping.get(font_family, 'Helvetica')
    
    def generate_invoice_number(self, branch_id: str = None) -> str:
        """Generate next sequential invoice number"""
        prefix = self.app_settings.get('invoice_prefix', 'INV')
        start_number = int(self.app_settings.get('invoice_start_number', 1000) or 1000)
        auto_gen = str(self.app_settings.get('auto_generate_invoices', 'true')).lower() == 'true'

        if not auto_gen:
            # Fallback to UUID-based if auto generation disabled
            return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

        current_year = datetime.now().year
        # Find the highest invoice number for the current year
        year_prefix = f"{prefix}-{current_year}-"
        latest_invoice = self.db.query(Invoice).filter(
            Invoice.invoice_number.like(f"{year_prefix}%")
        ).order_by(desc(Invoice.invoice_number)).first()

        if latest_invoice and latest_invoice.invoice_number:
            try:
                # Extract the sequence number from the invoice number
                seq_part = latest_invoice.invoice_number.replace(year_prefix, "")
                number = int(seq_part) + 1
            except (ValueError, AttributeError):
                number = start_number
        else:
            number = start_number

        # Ensure uniqueness by checking if the generated number already exists
        invoice_number = f"{year_prefix}{number:05d}"
        while self.db.query(Invoice).filter(Invoice.invoice_number == invoice_number).first():
            number += 1
            invoice_number = f"{year_prefix}{number:05d}"

        return invoice_number
    
    def create_invoice(
        self,
        customer_id: str,
        branch_id: str,
        invoice_items: List[Dict],
        due_date: date = None,
        payment_terms: int = 30,
        discount_percentage: float = 0.0,
        notes: str = "",
        created_by: str = None,
        save_draft: bool = False,
        is_cash_sale: bool = False
    ) -> Invoice:
        """Create a new tax invoice with accounting entries"""
        
        # Generate invoice number
        invoice_number = self.generate_invoice_number(branch_id)
        
        # Calculate totals
        subtotal = Decimal('0.00')
        total_vat = Decimal('0.00')
        total_discount = Decimal('0.00')
        
        # Determine invoice status
        if save_draft:
            status = 'draft'
        else:
            status = 'paid' if is_cash_sale else 'unpaid'
        # Create invoice
        invoice = Invoice(
            customer_id=customer_id,
            branch_id=branch_id,
            invoice_number=invoice_number,
            date=date.today(),
            due_date=due_date or (date.today() + timedelta(days=payment_terms)),
            payment_terms=payment_terms,
            discount_percentage=Decimal(str(discount_percentage)),
            notes=notes,
            created_by=created_by,
            status=status
        )
        
        self.db.add(invoice)
        self.db.flush()  # Get invoice ID
        
        # Add invoice items
        for item_data in invoice_items:
            product = self.db.query(Product).filter(Product.id == item_data['product_id']).first()
            if not product:
                continue
            
            quantity = Decimal(str(item_data['quantity']))
            # Support both 'price' and 'unit_price' field names for backward compatibility
            unit_price = Decimal(str(item_data.get('price') or item_data.get('unit_price', product.selling_price)))
            discount_percent = Decimal(str(item_data.get('discount_percentage', 0)))
            vat_rate = Decimal(str(item_data.get('vat_rate', self.app_settings['default_vat_rate'])))
            
            # Calculate amounts
            line_total = quantity * unit_price
            line_discount = line_total * (discount_percent / 100)
            line_subtotal = line_total - line_discount
            line_vat = line_subtotal * (vat_rate / 100)
            line_total_with_vat = line_subtotal + line_vat
            
            invoice_item = InvoiceItem(
                invoice_id=invoice.id,
                product_id=item_data['product_id'],
                quantity=int(quantity),
                price=unit_price,  # Fixed: Changed from unit_price to price to match the database model
                total=line_total_with_vat,  # Fixed: Changed from total_amount to total
                vat_amount=line_vat,
                vat_rate=vat_rate,
                discount_amount=line_discount,
                discount_percentage=discount_percent,
                description=item_data.get('description', product.name)
            )
            
            self.db.add(invoice_item)
            
            subtotal += line_subtotal
            total_vat += line_vat
            total_discount += line_discount
        
        # Apply overall discount
        if discount_percentage > 0:
            overall_discount = subtotal * (Decimal(str(discount_percentage)) / 100)
            subtotal -= overall_discount
            total_discount += overall_discount
            # Recalculate VAT on discounted amount
            total_vat = subtotal * (Decimal(str(self.app_settings['default_vat_rate'])) / 100)
        
        # Update invoice totals
        invoice.subtotal = subtotal
        invoice.total_vat_amount = total_vat
        invoice.discount_amount = total_discount
        invoice.total_amount = subtotal + total_vat
        invoice.amount_due = invoice.total_amount
        
        # Only create accounting entries when not saving draft
        if not save_draft:
            self._create_invoice_accounting_entries(invoice)
        
        self.db.commit()
        return invoice
    
    def get_printer_settings(self) -> Dict:
        """Get current printer settings from app settings"""
        # Get the singleton app settings record
        app_settings = self.db.query(AppSetting).first()
        
        # Create printer settings dictionary with defaults
        printer_settings = {
            'invoice_printer_type': 'a4_pdf',  # Default to A4 PDF for invoices
            'default_printer_name': '',
            'auto_print': 'false',
            'dot_matrix_paper_width': '80',
            'dot_matrix_form_length': '66',
            'dot_matrix_compressed': 'false',
            'dot_matrix_carbon_copies': '1',
            'dot_matrix_template': 'standard_80',
            'a4_orientation': 'portrait',
            'a4_paper_size': 'A4'
        }
        
        # If app settings exist, use the receipt format as a basis for invoice printing
        # Since there are no specific invoice printer columns yet, we'll use receipt format
        if app_settings and hasattr(app_settings, 'default_receipt_format'):
            receipt_format = app_settings.default_receipt_format or '80mm'
            
            # Map receipt format to invoice printer type
            if receipt_format == 'a4':
                printer_settings['invoice_printer_type'] = 'a4_pdf'
            elif receipt_format in ['50mm', '80mm']:
                # For thermal receipt formats, still use A4 PDF for invoices
                # (invoices are typically full-page documents, not receipts)
                printer_settings['invoice_printer_type'] = 'a4_pdf'
            else:
                printer_settings['invoice_printer_type'] = 'a4_pdf'  # Default fallback
        
        return printer_settings
    
    def generate_invoice_by_printer_type(self, invoice_id: str) -> Tuple[str, bytes, str]:
        """
        Generate invoice in the format specified by INVOICE printer settings
        This method is ONLY for invoices and uses invoice-specific printer configuration
        Returns: (format_type, content, filename)
        """
        printer_settings = self.get_printer_settings()
        printer_type = printer_settings['invoice_printer_type']
        
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("Invoice not found")
        
        # INVOICE PRINTER SETTINGS - Only applies to invoices
        if printer_type == 'a4_pdf':
            # Generate A4 PDF for invoices
            pdf_buffer = self.generate_pdf_invoice(invoice_id)
            content = pdf_buffer.read()
            filename = f"Invoice_{invoice.invoice_number}.pdf"
            return ('pdf', content, filename)
            
        elif printer_type == 'dot_matrix':
            # Generate dot matrix format for invoices (continuous paper)
            from app.services.dot_matrix_invoice_service import DotMatrixInvoiceService
            
            dot_matrix_service = DotMatrixInvoiceService(self.db)
            
            # Load custom template if specified
            custom_template = None
            template_name = printer_settings.get('dot_matrix_template')
            if template_name and template_name != 'standard_80':
                template_setting = self.db.query(AppSetting).filter(
                    AppSetting.key == f"dot_matrix_template_{template_name}"
                ).first()
                if template_setting:
                    custom_template = template_setting.value
            
            # Generate with saved invoice printer settings
            dot_matrix_content = dot_matrix_service.generate_dot_matrix_invoice(
                invoice_id=invoice_id,
                paper_width=int(printer_settings['dot_matrix_paper_width']),
                form_length=int(printer_settings['dot_matrix_form_length']),
                compressed=printer_settings['dot_matrix_compressed'].lower() == 'true',
                carbon_copies=int(printer_settings['dot_matrix_carbon_copies']),
                custom_template=custom_template
            )
            
            content = dot_matrix_content.encode('ascii', errors='replace')
            filename = f"Invoice_{invoice.invoice_number}_DotMatrix.txt"
            return ('text', content, filename)
            
        else:
            # For invoices, fallback to A4 PDF (not thermal receipt)
            # Thermal receipts are only for POS, not invoices
            pdf_buffer = self.generate_pdf_invoice(invoice_id)
            content = pdf_buffer.read()
            filename = f"Invoice_{invoice.invoice_number}.pdf"
            return ('pdf', content, filename)
    
    def generate_document_a4_pdf(self, document_type: str, document_id: str) -> Tuple[str, bytes, str]:
        """
        Generate any other document (NOT invoice, NOT POS receipt) as A4 PDF
        This is for all other documents that should always print on plain A4 paper
        """
        if document_type == 'invoice':
            # Invoices should use invoice printer settings
            return self.generate_invoice_by_printer_type(document_id)
        
        # For all other documents, always use A4 PDF regardless of printer settings
        # Examples: Reports, statements, quotes, purchase orders, etc.
        
        if document_type == 'quote':
            # Generate quote as A4 PDF
            pdf_buffer = self._generate_quote_pdf(document_id)
        elif document_type == 'purchase_order':
            # Generate purchase order as A4 PDF  
            pdf_buffer = self._generate_purchase_order_pdf(document_id)
        elif document_type == 'statement':
            # Generate statement as A4 PDF
            pdf_buffer = self._generate_statement_pdf(document_id)
        elif document_type == 'report':
            # Generate report as A4 PDF
            pdf_buffer = self._generate_report_pdf(document_id)
        else:
            # Generic document as A4 PDF
            pdf_buffer = self._generate_generic_pdf(document_type, document_id)
        
        content = pdf_buffer.read()
        filename = f"{document_type.title()}_{document_id}.pdf"
        return ('pdf', content, filename)
    
    def _generate_quote_pdf(self, quote_id: str) -> BytesIO:
        """Generate quote as A4 PDF - always plain paper"""
        # TODO: Implement quote PDF generation
        return self._generate_placeholder_pdf("Quote", quote_id)
    
    def _generate_purchase_order_pdf(self, po_id: str) -> BytesIO:
        """Generate purchase order as A4 PDF - always plain paper"""
        # TODO: Implement PO PDF generation
        return self._generate_placeholder_pdf("Purchase Order", po_id)
    
    def _generate_statement_pdf(self, statement_id: str) -> BytesIO:
        """Generate statement as A4 PDF - always plain paper"""
        # TODO: Implement statement PDF generation
        return self._generate_placeholder_pdf("Statement", statement_id)
    
    def _generate_report_pdf(self, report_id: str) -> BytesIO:
        """Generate report as A4 PDF - always plain paper"""
        # TODO: Implement report PDF generation
        return self._generate_placeholder_pdf("Report", report_id)
    
    def _generate_generic_pdf(self, doc_type: str, doc_id: str) -> BytesIO:
        """Generate generic document as A4 PDF - always plain paper"""
        return self._generate_placeholder_pdf(doc_type.title(), doc_id)
    
    def _generate_placeholder_pdf(self, doc_type: str, doc_id: str) -> BytesIO:
        """Generate placeholder PDF for document types not yet implemented"""
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        
        buffer = BytesIO()
        doc = canvas.Canvas(buffer, pagesize=A4)
        
        # Simple placeholder content
        doc.setTitle(f"{doc_type} {doc_id}")
        doc.drawString(100, 750, f"{doc_type} Document")
        doc.drawString(100, 720, f"Document ID: {doc_id}")
        doc.drawString(100, 690, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        doc.drawString(100, 660, "This document is generated on A4 plain paper")
        doc.drawString(100, 630, "(Printer settings do not affect this document type)")
        
        doc.save()
        buffer.seek(0)
        return buffer
    

    
    def _create_invoice_accounting_entries(self, invoice: Invoice):
        """Create journal entries for invoice"""
        # Create accounting entry header first
        accounting_entry = AccountingEntry(
            date_prepared=date.today(),
            date_posted=date.today(),
            particulars=f"Tax Invoice {invoice.invoice_number}",
            book="Sales Journal",
            status="posted",
            branch_id=invoice.branch_id
        )
        self.db.add(accounting_entry)
        self.db.flush()  # Get accounting entry ID
        
        # Get accounting codes
        accounts_receivable = self.db.query(AccountingCode).filter(
            AccountingCode.code == "1200"  # Accounts Receivable
        ).first()
        
        sales_revenue = self.db.query(AccountingCode).filter(
            AccountingCode.code == "4000"  # Sales Revenue
        ).first()
        
        vat_payable = self.db.query(AccountingCode).filter(
            AccountingCode.code == "2300"  # VAT Payable
        ).first()
        
        # Track total cost of goods for COGS/Inventory entry after line loop
        total_cogs = Decimal('0.00')
        # Build cost & inventory transactions per item
        try:
            for item in invoice.invoice_items:
                # Ensure product loaded
                product = None
                try:
                    product = self.db.query(Product).filter(Product.id == item.product_id).first()
                except Exception:
                    product = None
                if not product:
                    continue
                # Compute cost (simple FIFO/standard: cost_price * qty)
                line_cost = (product.cost_price or 0) * item.quantity
                try:
                    total_cogs += Decimal(str(line_cost))
                except Exception:
                    pass
                # Reduce on-hand quantity (avoid negative if not allowed later)
                try:
                    if product.quantity is not None:
                        product.quantity = max(0, (product.quantity or 0) - item.quantity)
                except Exception:
                    pass
                # Inventory transaction record
                inv_tx = InventoryTransaction(
                    product_id=product.id,
                    transaction_type='sale',
                    quantity=item.quantity,
                    unit_cost=product.cost_price or 0,
                    total_cost=line_cost,
                    date=date.today(),
                    reference=f"Invoice {invoice.invoice_number}",
                    branch_id=invoice.branch_id,
                    serial_numbers=[],  # empty list for PostgreSQL TEXT[] column
                    previous_quantity=None,
                    new_quantity=product.quantity
                )
                self.db.add(inv_tx)
        except Exception as inv_err:
            print(f"[INVOICE_INV_TX_WARN] {inv_err}")

        # Debit: Accounts Receivable
        if accounts_receivable:
            debit_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=accounts_receivable.id,
                entry_type="debit",
                narration=f"Invoice {invoice.invoice_number} - {invoice.customer.name if hasattr(invoice, 'customer') else 'Customer'}",
                debit_amount=float(invoice.total_amount),
                credit_amount=0.0,
                description=f"Sales to customer",
                reference=invoice.invoice_number,
                date=date.today(),
                branch_id=invoice.branch_id
            )
            self.db.add(debit_entry)
        
        # Credit: Sales Revenue
        if sales_revenue:
            credit_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=sales_revenue.id,
                entry_type="credit",
                narration=f"Sales Revenue - Invoice {invoice.invoice_number}",
                debit_amount=0.0,
                credit_amount=float(invoice.subtotal),
                description="Sales revenue",
                reference=invoice.invoice_number,
                date=date.today(),
                branch_id=invoice.branch_id
            )
            self.db.add(credit_entry)
        
        # Credit: VAT Payable
        if vat_payable and invoice.total_vat_amount > 0:
            vat_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=vat_payable.id,
                entry_type="credit",
                narration=f"VAT on Invoice {invoice.invoice_number}",
                debit_amount=0.0,
                credit_amount=float(invoice.total_vat_amount),
                description="VAT payable",
                reference=invoice.invoice_number,
                date=date.today(),
                branch_id=invoice.branch_id
            )
            self.db.add(vat_entry)

        # Add COGS / Inventory entries if cost captured
        if total_cogs > 0:
            cogs_account = self.db.query(AccountingCode).filter(AccountingCode.code == "5100").first()
            inventory_account = self.db.query(AccountingCode).filter(AccountingCode.code == "1140").first()
            if cogs_account and inventory_account:
                # Debit COGS (Expense)
                cogs_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=cogs_account.id,
                    entry_type="debit",
                    narration=f"COGS for Invoice {invoice.invoice_number}",
                    debit_amount=float(total_cogs),
                    credit_amount=0.0,
                    description="Cost of goods sold",
                    reference=invoice.invoice_number,
                    date=date.today(),
                    branch_id=invoice.branch_id
                )
                self.db.add(cogs_entry)
                # Credit Inventory (Asset decrease)
                inv_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=inventory_account.id,
                    entry_type="credit",
                    narration=f"Inventory reduction for Invoice {invoice.invoice_number}",
                    debit_amount=0.0,
                    credit_amount=float(total_cogs),
                    description="Inventory outflow",
                    reference=invoice.invoice_number,
                    date=date.today(),
                    branch_id=invoice.branch_id
                )
                self.db.add(inv_entry)
    
    def generate_pdf_invoice(self, invoice_id: str) -> BytesIO:
        """Generate fully customizable A4 PDF invoice using app settings"""
        from sqlalchemy.orm import joinedload
        from app.models.sales import InvoiceItem
        
        # Load invoice with all necessary relationships
        invoice = self.db.query(Invoice).options(
            joinedload(Invoice.customer),
            joinedload(Invoice.branch),
            joinedload(Invoice.invoice_items).joinedload(InvoiceItem.product)
        ).filter(Invoice.id == invoice_id).first()
        
        if not invoice:
            raise ValueError("Invoice not found")
        
        # Get customization settings
        settings = self.app_settings
        
        # Create PDF buffer with customizable margins
        buffer = BytesIO()
        paper_size = A4  # Could be customizable based on settings.get('invoice_paper_size')
        margin_top = int(settings.get('invoice_margin_top', 20)) * mm
        margin_bottom = int(settings.get('invoice_margin_bottom', 20)) * mm
        margin_left = int(settings.get('invoice_margin_left', 20)) * mm
        margin_right = int(settings.get('invoice_margin_right', 20)) * mm
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=paper_size,
            rightMargin=margin_right,
            leftMargin=margin_left,
            topMargin=margin_top,
            bottomMargin=margin_bottom
        )
        
        # Build PDF content
        story = []
        styles = getSampleStyleSheet()
        
        # Get color settings
        primary_color = colors.HexColor(settings.get('invoice_primary_color', '#007bff'))
        secondary_color = colors.HexColor(settings.get('invoice_secondary_color', '#6c757d'))
        accent_color = colors.HexColor(settings.get('invoice_accent_color', '#28a745'))
        bg_color = colors.HexColor(settings.get('invoice_background_color', '#ffffff'))
        
        # Get typography settings with font family mapping
        css_font_family = settings.get('invoice_font_family', 'Helvetica')
        font_family = self._map_css_font_to_reportlab(css_font_family)
        base_font_size = int(settings.get('invoice_base_font_size', 12))
        line_height = float(settings.get('invoice_line_height', 1.4))
        
        # Custom styles with settings
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=int(settings.get('invoice_title_font_size', 36)),
            fontName=f"{font_family}-Bold" if settings.get('invoice_title_font_weight') == 'bold' else font_family,
            spaceAfter=30,
            alignment=getattr(TA_CENTER if settings.get('invoice_title_alignment') == 'center' 
                           else TA_RIGHT if settings.get('invoice_title_alignment') == 'right' 
                           else TA_LEFT, 'value', TA_RIGHT),
            textColor=colors.HexColor(settings.get('invoice_title_color', '#333333'))
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            fontName=f"{font_family}-Bold",
            textColor=colors.HexColor(settings.get('invoice_header_text_color', '#000000'))
        )
        
        company_style = ParagraphStyle(
            'CompanyStyle',
            parent=styles['Normal'],
            fontSize=int(settings.get('company_info_font_size', 12)),
            fontName=f"{font_family}-Bold" if settings.get('company_info_font_weight') == 'bold' else font_family,
            textColor=colors.HexColor(settings.get('company_info_color', '#000000')),
            alignment=getattr(TA_CENTER if settings.get('company_info_alignment') == 'center' 
                           else TA_RIGHT if settings.get('company_info_alignment') == 'right' 
                           else TA_LEFT, 'value', TA_LEFT)
        )
        
        # Logo handling
        if settings.get('invoice_show_logo', True) and settings.get('company_logo_url'):
            logo_path = settings.get('company_logo_url')
            if os.path.exists(logo_path):
                logo_width = int(settings.get('logo_width', 150)) * mm / 10  # Convert to mm
                logo_height = int(settings.get('logo_height', 75)) * mm / 10
                logo = Image(logo_path, width=logo_width, height=logo_height)
                
                # Add logo margins
                logo_margin_top = int(settings.get('logo_margin_top', 10))
                logo_margin_bottom = int(settings.get('logo_margin_bottom', 10))
                
                if logo_margin_top > 0:
                    story.append(Spacer(1, logo_margin_top))
                story.append(logo)
                if logo_margin_bottom > 0:
                    story.append(Spacer(1, logo_margin_bottom))
        
        # Company header with customizable background
        header_bg = colors.HexColor(settings.get('invoice_header_background_color', '#ffffff'))
        
        # Company info - use app settings with conditional display
        company_info_parts = []
        
        # Company name (always show)
        company_info_parts.append(f"<b>{settings.get('company_name', 'Your Company Name')}</b>")
        
        # Address (conditional)
        if settings.get('invoice_show_company_address', True):
            address = settings.get('address', 'Company Address')
            if address:
                company_info_parts.append(address)
        
        # Phone (conditional)
        if settings.get('invoice_show_company_phone', True):
            phone = settings.get('phone', '')
            if phone:
                company_info_parts.append(f"Phone: {phone}")
        
        # Email (conditional)
        if settings.get('invoice_show_company_email', True):
            email = settings.get('email', '')
            if email:
                company_info_parts.append(f"Email: {email}")
        
        # Website (conditional)
        if settings.get('invoice_show_company_website', True):
            website = settings.get('website', '')
            if website:
                company_info_parts.append(f"Website: {website}")
        
        # VAT Number (conditional)
        if settings.get('invoice_show_vat_number', True):
            vat_number = settings.get('vat_registration_number', '')
            if vat_number:
                company_info_parts.append(f"VAT Number: {vat_number}")
        
        company_info = "<br/>".join(company_info_parts)
        story.append(Paragraph(company_info, company_style))
        story.append(Spacer(1, 20))
        
        # Invoice title with customizable text
        invoice_title = settings.get('invoice_title_text', 'INVOICE')
        story.append(Paragraph(invoice_title, title_style))
        
        # Header border customization
        border_style = settings.get('invoice_header_border_style', 'solid')
        border_width = int(settings.get('invoice_header_border_width', 2))
        border_color = colors.HexColor(settings.get('invoice_header_border_color', '#333333'))
        
        if border_style != 'none':
            story.append(HRFlowable(width="100%", thickness=border_width, color=border_color))
        story.append(Spacer(1, 20))
        
        # Invoice details table
        invoice_details = [
            ['Invoice Number:', invoice.invoice_number, 'Date:', invoice.date.strftime('%d/%m/%Y') if invoice.date else 'N/A'],
        ]
        
        # Add due date if setting enabled
        if settings.get('invoice_show_due_date', True) and invoice.due_date:
            invoice_details.append(['Due Date:', invoice.due_date.strftime('%d/%m/%Y'), '', ''])
        
        # Add payment terms if setting enabled
        if settings.get('invoice_show_payment_terms', True):
            payment_terms = invoice.payment_terms or int(settings.get('default_payment_terms', 30))
            invoice_details.append(['Payment Terms:', f'{payment_terms} days', '', ''])
        
        details_table = Table(invoice_details, colWidths=[35*mm, 45*mm, 25*mm, 35*mm])
        details_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), f'{font_family}-Bold'),
            ('FONTNAME', (2, 0), (2, -1), f'{font_family}-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), base_font_size),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        story.append(details_table)
        story.append(Spacer(1, 20))
        
        # Customer section with customizable styling
        customer = invoice.customer
        story.append(Paragraph("Bill To:", header_style))
        
        # Customer section background
        customer_bg = colors.HexColor(settings.get('customer_section_background', '#f8f9fa'))
        customer_border = settings.get('customer_section_border', True)
        customer_border_color = colors.HexColor(settings.get('customer_section_border_color', '#dee2e6'))
        
        # Build customer info based on settings
        customer_info_parts = [f"<b>{customer.name}</b>"]
        
        # Customer address (conditional)
        if settings.get('invoice_show_customer_address', True):
            if customer.address:
                customer_info_parts.append(customer.address)
        
        # Customer phone (conditional)
        if settings.get('invoice_show_customer_phone', True):
            if customer.phone:
                customer_info_parts.append(f"Phone: {customer.phone}")
        
        # Customer email (conditional)
        if settings.get('invoice_show_customer_email', True):
            if customer.email:
                customer_info_parts.append(f"Email: {customer.email}")
        
        # Customer VAT number (conditional)
        if settings.get('invoice_show_customer_vat_number', True):
            if customer.vat_reg_number:
                customer_info_parts.append(f"VAT Number: {customer.vat_reg_number}")
        
        customer_info = "<br/>".join(customer_info_parts)
        story.append(Paragraph(customer_info, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Invoice items table with customizable styling
        story.append(Paragraph("Invoice Items:", header_style))
        
        # Build table headers based on settings
        headers = ['Product/Description', 'Qty', 'Unit Price']
        
        # Add discount column if setting enabled
        if settings.get('invoice_show_discount', True):
            headers.append('Discount')
        
        # Add VAT columns if setting enabled
        if settings.get('invoice_show_vat_breakdown', True):
            headers.extend(['VAT Rate', 'VAT Amount'])
        
        headers.append('Total')
        items_data = [headers]
        
        # Add items with product information
        for item in invoice.invoice_items:
            currency_symbol = settings.get('currency', 'BWP')
            
            # Build product/description column
            product_desc = ''
            if item.product:
                product_desc = f"<b>{item.product.name}</b>"
                if item.description:
                    product_desc += f"<br/><i>{item.description}</i>"
            else:
                product_desc = item.description or 'No description'
            
            # Build row data
            row_data = [
                product_desc,
                str(item.quantity or 0),
                f"{currency_symbol}{float(item.price or 0):.2f}"
            ]
            
            # Add discount if enabled
            if settings.get('invoice_show_discount', True):
                discount_pct = float(item.discount_percentage or 0)
                row_data.append(f"{discount_pct:.1f}%")
            
            # Add VAT columns if enabled
            if settings.get('invoice_show_vat_breakdown', True):
                vat_rate = float(item.vat_rate or 0)
                vat_amount = float(item.vat_amount or 0)
                row_data.extend([f"{vat_rate:.1f}%", f"{currency_symbol}{vat_amount:.2f}"])
            
            # Add total
            row_data.append(f"{currency_symbol}{float(item.total or 0):.2f}")
            
            items_data.append(row_data)
        
        # Create items table with dynamic column widths
        num_cols = len(headers)
        if num_cols == 4:  # Product, Qty, Price, Total (no discount, no VAT)
            col_widths = [80*mm, 20*mm, 30*mm, 30*mm]
        elif num_cols == 5:  # With discount OR VAT
            col_widths = [60*mm, 15*mm, 25*mm, 25*mm, 25*mm]
        elif num_cols == 6:  # With discount and one VAT column
            col_widths = [50*mm, 15*mm, 20*mm, 20*mm, 20*mm, 25*mm]
        elif num_cols == 7:  # With discount and both VAT columns (full)
            col_widths = [40*mm, 12*mm, 18*mm, 15*mm, 15*mm, 20*mm, 20*mm]
        else:  # Default fallback
            col_widths = [170*mm // num_cols] * num_cols
        
        # Get table styling from settings
        table_header_bg = colors.HexColor(settings.get('items_table_header_bg', '#343a40'))
        table_header_text = colors.HexColor(settings.get('items_table_header_text', '#ffffff'))
        table_border_color = colors.HexColor(settings.get('items_table_border_color', '#dee2e6'))
        table_stripe_color = colors.HexColor(settings.get('items_table_stripe_color', '#f8f9fa'))
        table_font_size = int(settings.get('items_table_font_size', 12))
            
        items_table = Table(items_data, colWidths=col_widths)
        items_table.setStyle(TableStyle([
            # Header styling with customizable colors
            ('BACKGROUND', (0, 0), (-1, 0), table_header_bg),
            ('TEXTCOLOR', (0, 0), (-1, 0), table_header_text),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), f'{font_family}-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), table_font_size),
            
            # Data styling
            ('FONTNAME', (0, 1), (-1, -1), font_family),
            ('FONTSIZE', (0, 1), (-1, -1), table_font_size - 1),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),  # Align numbers right
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),    # Align description left
            
            # Borders with customizable color
            ('GRID', (0, 0), (-1, -1), 1, table_border_color),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, table_stripe_color]),
        ]))
        
        story.append(items_table)
        story.append(Spacer(1, 20))
        
        # Totals section with customizable styling
        currency_symbol = settings.get('currency', 'BWP')
        
        # Calculate subtotal (total_amount - total_vat_amount)
        subtotal = float(invoice.total_amount or 0) - float(invoice.total_vat_amount or 0)
        
        totals_data = []
        
        # Always show subtotal
        totals_data.append(['Subtotal:', f"{currency_symbol}{subtotal:.2f}"])
        
        # Show discount if enabled and there is a discount
        if (settings.get('invoice_show_discount', True) and 
            float(invoice.discount_amount or 0) > 0):
            totals_data.append(['Discount:', f"{currency_symbol}{float(invoice.discount_amount or 0):.2f}"])
        
        # Show VAT if enabled
        if settings.get('invoice_show_vat_breakdown', True):
            totals_data.append(['VAT Total:', f"{currency_symbol}{float(invoice.total_vat_amount or 0):.2f}"])
        
        # Always show total
        totals_data.append(['Total Amount:', f"{currency_symbol}{float(invoice.total_amount or 0):.2f}"])
        
        # Get totals styling from settings
        totals_bg = colors.HexColor(settings.get('totals_section_background', '#f8f9fa'))
        totals_font_size = int(settings.get('totals_font_size', 14))
        totals_font_weight = settings.get('totals_font_weight', 'normal')
        totals_font = f"{font_family}-Bold" if totals_font_weight == 'bold' else font_family
        
        totals_table = Table(totals_data, colWidths=[40*mm, 30*mm], hAlign='RIGHT')
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -1), f'{font_family}-Bold'),
            ('FONTNAME', (1, 0), (1, -1), font_family),
            ('FONTNAME', (0, -1), (-1, -1), f'{font_family}-Bold'),  # Last row bold
            ('FONTSIZE', (0, 0), (-1, -1), totals_font_size),
            ('FONTSIZE', (0, -1), (-1, -1), totals_font_size + 2),  # Last row larger
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, -2), (-1, -2), 1, colors.black),  # Line above total
            ('BACKGROUND', (0, -1), (-1, -1), totals_bg),  # Total row background
        ]))
        
        story.append(totals_table)
        story.append(Spacer(1, 30))
        
        # Payment terms and notes
        if invoice.notes:
            story.append(Paragraph("Notes:", header_style))
            story.append(Paragraph(invoice.notes, styles['Normal']))
            story.append(Spacer(1, 12))
        
        # Footer with customizable styling and content
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontSize=int(settings.get('invoice_footer_font_size', 11)),
            fontName=font_family,
            textColor=colors.HexColor(settings.get('invoice_footer_text_color', '#000000')),
            alignment=getattr(TA_CENTER if settings.get('invoice_footer_alignment') == 'center' 
                           else TA_RIGHT if settings.get('invoice_footer_alignment') == 'right' 
                           else TA_LEFT, 'value', TA_LEFT)
        )
        
        footer_parts = []
        
        # Payment terms
        payment_terms = invoice.payment_terms or int(settings.get('default_payment_terms', 30))
        footer_parts.append(f"<b>Payment Terms:</b> Payment is due within {payment_terms} days of invoice date.")
        
        # Add invoice footer text from settings
        footer_text = settings.get('invoice_footer_text', '')
        if footer_text:
            footer_parts.append(footer_text)
        
        # Add terms and conditions from settings
        terms_conditions = settings.get('invoice_terms_conditions', '')
        if terms_conditions:
            footer_parts.append(f"<b>Terms & Conditions:</b> {terms_conditions}")
        
        # Default closing
        footer_parts.append("<b>Thank you for your business!</b>")
        footer_parts.append("This is a computer-generated invoice and does not require a signature.")
        
        footer_text_final = "<br/><br/>".join(footer_parts)
        
        story.append(Paragraph(footer_text_final, footer_style))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer
    
    def get_invoice_list(
        self, 
        branch_id: str = None,
        customer_id: str = None,
        status: str = None,
        date_from: date = None,
        date_to: date = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Invoice]:
        """Get filtered list of invoices"""
        from sqlalchemy.orm import joinedload
        
        query = self.db.query(Invoice).options(joinedload(Invoice.customer))
        
        if branch_id:
            query = query.filter(Invoice.branch_id == branch_id)
        if customer_id:
            query = query.filter(Invoice.customer_id == customer_id)
        if status:
            if status == 'outstanding':
                # Outstanding means invoices that are not fully paid and not draft or cancelled
                query = query.filter(
                    Invoice.status.notin_(['draft', 'cancelled']),
                    Invoice.amount_paid < Invoice.total_amount
                )
            else:
                query = query.filter(Invoice.status == status)
        if date_from:
            query = query.filter(Invoice.date >= date_from)
        if date_to:
            query = query.filter(Invoice.date <= date_to)
        
        return query.order_by(desc(Invoice.created_at)).offset(offset).limit(limit).all()
    
    def mark_invoice_sent(self, invoice_id: str, method: str = 'email'):
        """Mark invoice as sent via email/WhatsApp"""
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if invoice:
            invoice.status = 'sent'
            if method == 'whatsapp':
                invoice.sent_via_whatsapp = True
                invoice.whatsapp_sent_at = datetime.now()
            else:
                invoice.sent_via_email = True
                invoice.email_sent_at = datetime.now()
            self.db.commit()
    
    def mark_invoice_paid(self, invoice_id: str, payment_amount: float, payment_date: date = None):
        """Mark invoice as paid and create accounting entries"""
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("Invoice not found")
        
        payment_amount = Decimal(str(payment_amount))
        invoice.amount_paid += payment_amount
        invoice.amount_due = invoice.total_amount - invoice.amount_paid
        
        if invoice.amount_due <= 0:
            invoice.status = 'paid'
            invoice.paid_at = datetime.now()
        else:
            invoice.status = 'partial'
        
        # Create payment record for accounting service
        from app.models.sales import Payment
        import uuid
        
        payment_record = Payment(
            id=str(uuid.uuid4()),
            invoice_id=invoice.id,
            customer_id=invoice.customer_id,
            amount=payment_amount,
            payment_date=payment_date or date.today(),
            payment_method='cash',  # Default for manual payments
            payment_status="completed"
        )
        
        # Use the standardized AccountingService for payment recording
        try:
            from app.services.accounting_service import AccountingService
            accounting_service = AccountingService(self.db)
            success = accounting_service.record_payment(payment_record)
            if not success:
                print(f"[PAYMENT_WARN] Accounting service failed to record payment for invoice {invoice.invoice_number}")
        except Exception as e:
            print(f"[PAYMENT_ERROR] Error recording payment accounting: {str(e)}")
        
        self.db.commit()

def get_invoice_service(db: Session = None) -> InvoiceService:
    """Factory function to get InvoiceService instance"""
    if db is None:
        db = next(get_db())
    return InvoiceService(db)
