"""
Dot Matrix Invoice Service

This service handles invoice generation for dot matrix printers using continuous paper.
Optimized for Epson LX-300+ and similar 9-pin dot matrix printers.
"""

from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
import io
from textwrap import fill

from app.models.sales import Invoice
from app.models.app_setting import AppSetting


class DotMatrixInvoiceService:
    """Service for generating dot matrix printer-ready invoice formats"""
    
    def __init__(self, db: Session):
        self.db = db
        self.app_settings = self._load_app_settings()
    
    def _load_app_settings(self) -> Dict:
        """Load application settings for invoice generation"""
        settings = {}
        app_settings = self.db.query(AppSetting).all()
        
        for setting in app_settings:
            settings[setting.key] = setting.value
        
        # Default values for dot matrix printing
        defaults = {
            'company_name': 'YOUR COMPANY NAME',
            'company_address': 'Company Address Line 1\nCompany Address Line 2',
            'company_phone': 'Phone: +267 1234 5678',
            'company_email': 'Email: info@company.com',
            'tax_number': 'TAX: 123456789',
            'vat_number': 'VAT: 987654321',
            'currency_symbol': 'P',
            'default_vat_rate': '12.0',
            # Dot matrix specific settings
            'dot_matrix_width': '80',  # characters per line (80 or 136)
            'dot_matrix_lines_per_inch': '6',  # 6 or 8 LPI
            'dot_matrix_form_length': '11',  # inches
            'dot_matrix_left_margin': '5',  # character positions
            'dot_matrix_compressed_print': 'false',  # 17 CPI vs 10 CPI
        }
        
        for key, default_value in defaults.items():
            if key not in settings:
                settings[key] = default_value
        
        return settings
    
    def generate_dot_matrix_invoice(
        self, 
        invoice_id: str,
        paper_width: int = 80,  # 80 or 136 characters
        form_length: int = 66,  # lines (11" at 6 LPI = 66 lines)
        compressed: bool = False,  # 17 CPI vs 10 CPI
        carbon_copies: int = 1,  # number of copies
        custom_template: Optional[str] = None
    ) -> str:
        """Generate dot matrix printer format invoice"""
        
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("Invoice not found")
        
        # Set printing parameters
        self.paper_width = paper_width
        self.form_length = form_length
        self.compressed = compressed
        self.left_margin = int(self.app_settings.get('dot_matrix_left_margin', '5'))
        
        # Calculate effective width
        self.effective_width = paper_width - (self.left_margin * 2)
        
        # Generate invoice content
        if custom_template:
            content = self._generate_custom_template(invoice, custom_template)
        else:
            content = self._generate_standard_template(invoice)
        
        # Add printer control codes
        formatted_content = self._add_printer_control_codes(content, carbon_copies)
        
        return formatted_content
    
    def _generate_standard_template(self, invoice: Invoice) -> str:
        """Generate standard dot matrix invoice template"""
        lines = []
        
        # Header section
        lines.extend(self._generate_header())
        lines.append("")  # Blank line
        
        # Invoice info section
        lines.extend(self._generate_invoice_info(invoice))
        lines.append("")
        
        # Customer section
        lines.extend(self._generate_customer_info(invoice))
        lines.append("")
        
        # Items header
        lines.extend(self._generate_items_header())
        
        # Invoice items
        lines.extend(self._generate_invoice_items(invoice))
        
        # Totals section
        lines.extend(self._generate_totals_section(invoice))
        
        # Footer section
        lines.extend(self._generate_footer(invoice))
        
        # Pad to form length
        while len(lines) < self.form_length:
            lines.append("")
        
        return '\n'.join(lines)
    
    def _generate_header(self) -> List[str]:
        """Generate company header section"""
        lines = []
        
        # Company name (centered, bold if supported)
        company_name = self.app_settings['company_name']
        lines.append(self._center_text(company_name.upper()))
        lines.append(self._center_text('=' * len(company_name)))
        lines.append("")
        
        # Company details
        address_lines = self.app_settings['company_address'].split('\n')
        for addr_line in address_lines:
            lines.append(self._center_text(addr_line))
        
        lines.append(self._center_text(self.app_settings['company_phone']))
        lines.append(self._center_text(self.app_settings['company_email']))
        lines.append("")
        
        # Tax numbers
        tax_line = f"{self.app_settings['tax_number']}  {self.app_settings['vat_number']}"
        lines.append(self._center_text(tax_line))
        lines.append("")
        
        # Invoice title
        lines.append(self._center_text("TAX INVOICE"))
        lines.append(self._center_text("=" * 15))
        
        return lines
    
    def _generate_invoice_info(self, invoice: Invoice) -> List[str]:
        """Generate invoice information section"""
        lines = []
        
        # Invoice details in two columns
        col1_width = self.effective_width // 2
        col2_width = self.effective_width - col1_width
        
        # First row
        inv_no = f"Invoice No: {invoice.invoice_number}"
        inv_date = f"Date: {invoice.date.strftime('%d/%m/%Y')}"
        lines.append(self._format_two_columns(inv_no, inv_date, col1_width, col2_width))
        
        # Second row
        due_date = f"Due Date: {invoice.due_date.strftime('%d/%m/%Y')}"
        terms = f"Terms: {invoice.payment_terms} days"
        lines.append(self._format_two_columns(due_date, terms, col1_width, col2_width))
        
        return lines
    
    def _generate_customer_info(self, invoice: Invoice) -> List[str]:
        """Generate customer information section"""
        lines = []
        
        lines.append("BILL TO:")
        lines.append("-" * 10)
        
        customer = invoice.customer
        lines.append(customer.name.upper())
        
        if customer.address:
            addr_lines = customer.address.split('\n')
            for addr_line in addr_lines:
                lines.append(addr_line)
        
        if customer.phone:
            lines.append(f"Phone: {customer.phone}")
        
        if customer.email:
            lines.append(f"Email: {customer.email}")
            
        if customer.vat_reg_number:
            lines.append(f"VAT No: {customer.vat_reg_number}")
        
        return lines
    
    def _generate_items_header(self) -> List[str]:
        """Generate items table header"""
        lines = []
        
        # Determine column widths based on paper width
        if self.effective_width >= 70:
            # Wide format
            desc_width = 25
            qty_width = 5
            price_width = 10
            disc_width = 6
            vat_width = 6
            total_width = 10
        else:
            # Narrow format
            desc_width = 20
            qty_width = 4
            price_width = 8
            disc_width = 5
            vat_width = 5
            total_width = 8
        
        # Store widths for use in items generation
        self.col_widths = {
            'desc': desc_width,
            'qty': qty_width,
            'price': price_width,
            'disc': disc_width,
            'vat': vat_width,
            'total': total_width
        }
        
        # Header line
        header = (
            f"{'DESCRIPTION':<{desc_width}} "
            f"{'QTY':>{qty_width}} "
            f"{'PRICE':>{price_width}} "
            f"{'DISC%':>{disc_width}} "
            f"{'VAT%':>{vat_width}} "
            f"{'TOTAL':>{total_width}}"
        )
        lines.append(header)
        lines.append("-" * len(header))
        
        return lines
    
    def _generate_invoice_items(self, invoice: Invoice) -> List[str]:
        """Generate invoice items section"""
        lines = []
        
        for item in invoice.invoice_items:
            # Format description (wrap if too long)
            desc = item.description or (item.product.name if item.product else "Item")
            if len(desc) > self.col_widths['desc']:
                desc = desc[:self.col_widths['desc'] - 3] + "..."
            
            # Format amounts
            currency = self.app_settings['currency_symbol']
            
            item_line = (
                f"{desc:<{self.col_widths['desc']}} "
                f"{item.quantity:>{self.col_widths['qty']}} "
                f"{currency}{item.unit_price:>{self.col_widths['price'] - 1}.2f} "
                f"{item.discount_percentage:>{self.col_widths['disc'] - 1}.1f}% "
                f"{item.vat_rate:>{self.col_widths['vat'] - 1}.1f}% "
                f"{currency}{item.total_amount:>{self.col_widths['total'] - 1}.2f}"
            )
            lines.append(item_line)
        
        # Add separator line
        lines.append("-" * (sum(self.col_widths.values()) + 5))
        
        return lines
    
    def _generate_totals_section(self, invoice: Invoice) -> List[str]:
        """Generate totals section"""
        lines = []
        currency = self.app_settings['currency_symbol']
        
        # Calculate alignment for totals
        total_section_width = 25
        label_width = 15
        amount_width = 10
        
        # Right-align totals section
        indent = max(0, self.effective_width - total_section_width)
        
        # Subtotal
        subtotal_line = f"{'Subtotal:':<{label_width}}{currency}{invoice.subtotal:>{amount_width - 1}.2f}"
        lines.append(" " * indent + subtotal_line)
        
        # Discount
        if invoice.discount_amount > 0:
            discount_line = f"{'Discount:':<{label_width}}{currency}{invoice.discount_amount:>{amount_width - 1}.2f}"
            lines.append(" " * indent + discount_line)
        
        # VAT
        vat_line = f"{'VAT Total:':<{label_width}}{currency}{invoice.total_vat_amount:>{amount_width - 1}.2f}"
        lines.append(" " * indent + vat_line)
        
        # Total
        lines.append(" " * indent + "-" * total_section_width)
        total_line = f"{'TOTAL:':<{label_width}}{currency}{invoice.total_amount:>{amount_width - 1}.2f}"
        lines.append(" " * indent + total_line)
        lines.append(" " * indent + "=" * total_section_width)
        
        return lines
    
    def _generate_footer(self, invoice: Invoice) -> List[str]:
        """Generate footer section"""
        lines = []
        lines.append("")
        
        # Payment terms
        lines.append(f"Payment is due within {invoice.payment_terms} days of invoice date.")
        
        # Notes
        if invoice.notes:
            lines.append("")
            lines.append("NOTES:")
            # Wrap notes to fit width
            wrapped_notes = fill(invoice.notes, width=self.effective_width)
            lines.extend(wrapped_notes.split('\n'))
        
        lines.append("")
        lines.append("Thank you for your business!")
        lines.append("")
        
        # Signature line
        lines.append("_" * 30)
        lines.append("Authorized Signature")
        
        return lines
    
    def _generate_custom_template(self, invoice: Invoice, template: str) -> str:
        """Generate invoice using custom template"""
        # Template variables that can be used
        template_vars = {
            'company_name': self.app_settings['company_name'],
            'company_address': self.app_settings['company_address'],
            'company_phone': self.app_settings['company_phone'],
            'company_email': self.app_settings['company_email'],
            'tax_number': self.app_settings['tax_number'],
            'vat_number': self.app_settings['vat_number'],
            'invoice_number': invoice.invoice_number,
            'invoice_date': invoice.date.strftime('%d/%m/%Y'),
            'due_date': invoice.due_date.strftime('%d/%m/%Y'),
            'payment_terms': str(invoice.payment_terms),
            'customer_name': invoice.customer.name,
            'customer_address': invoice.customer.address or '',
            'customer_phone': invoice.customer.phone or '',
            'customer_email': invoice.customer.email or '',
            'customer_vat': invoice.customer.vat_reg_number or '',
            'currency_symbol': self.app_settings['currency_symbol'],
            'subtotal': f"{invoice.subtotal:.2f}",
            'discount_amount': f"{invoice.discount_amount:.2f}",
            'vat_amount': f"{invoice.total_vat_amount:.2f}",
            'total_amount': f"{invoice.total_amount:.2f}",
            'notes': invoice.notes or '',
        }
        
        # Replace template variables
        content = template
        for var, value in template_vars.items():
            content = content.replace(f'{{{var}}}', str(value))
        
        # Process invoice items
        items_section = ""
        for item in invoice.invoice_items:
            item_vars = {
                'item_description': item.description or (item.product.name if item.product else 'Item'),
                'item_quantity': str(item.quantity),
                'item_price': f"{item.unit_price:.2f}",
                'item_discount': f"{item.discount_percentage:.1f}",
                'item_vat_rate': f"{item.vat_rate:.1f}",
                'item_total': f"{item.total_amount:.2f}",
            }
            
            # Replace item variables in items template
            item_template = "{item_description} | {item_quantity} | {currency_symbol}{item_price} | {item_discount}% | {item_vat_rate}% | {currency_symbol}{item_total}\n"
            item_line = item_template
            for var, value in item_vars.items():
                item_line = item_line.replace(f'{{{var}}}', str(value))
            item_line = item_line.replace('{currency_symbol}', self.app_settings['currency_symbol'])
            
            items_section += item_line
        
        content = content.replace('{invoice_items}', items_section.rstrip())
        
        return content
    
    def _add_printer_control_codes(self, content: str, copies: int = 1) -> str:
        """Add dot matrix printer control codes"""
        result = ""
        
        # ESC codes for Epson LX-300+ and compatible printers
        ESC = chr(27)  # Escape character
        
        # Initialize printer
        result += ESC + "@"  # Initialize printer
        
        # Set character pitch
        if self.compressed:
            result += ESC + chr(15)  # Compressed print (17 CPI)
        else:
            result += ESC + "P"  # 10 CPI
        
        # Set line spacing (6 LPI or 8 LPI)
        lpi = int(self.app_settings.get('dot_matrix_lines_per_inch', '6'))
        if lpi == 8:
            result += ESC + "0"  # 8 LPI
        else:
            result += ESC + "2"  # 6 LPI (default)
        
        # Set left margin
        result += ESC + "l" + chr(self.left_margin)
        
        # Set form length
        result += ESC + "C" + chr(self.form_length)
        
        # Add content for each copy
        for copy_num in range(copies):
            if copy_num > 0:
                result += chr(12)  # Form feed between copies
                if copy_num == 1:
                    result += "\n" + "CUSTOMER COPY".center(self.effective_width) + "\n"
                elif copy_num == 2:
                    result += "\n" + "OFFICE COPY".center(self.effective_width) + "\n"
                else:
                    result += "\n" + f"COPY {copy_num + 1}".center(self.effective_width) + "\n"
            
            result += content
        
        # Final form feed
        result += chr(12)
        
        return result
    
    def _center_text(self, text: str) -> str:
        """Center text within effective width"""
        if len(text) >= self.effective_width:
            return text[:self.effective_width]
        
        padding = (self.effective_width - len(text)) // 2
        return " " * padding + text
    
    def _format_two_columns(self, left_text: str, right_text: str, left_width: int, right_width: int) -> str:
        """Format text in two columns"""
        left_part = left_text[:left_width].ljust(left_width)
        right_part = right_text[:right_width].rjust(right_width)
        return left_part + right_part
    
    def get_available_templates(self) -> Dict[str, Dict]:
        """Get available dot matrix templates"""
        templates = {
            'standard_80': {
                'name': 'Standard 80 Column',
                'description': 'Standard format for 80-column dot matrix printers',
                'width': 80,
                'form_length': 66,
                'compressed': False
            },
            'standard_136': {
                'name': 'Standard 136 Column',
                'description': 'Wide format for 136-column dot matrix printers',
                'width': 136,
                'form_length': 66,
                'compressed': False
            },
            'compact_80': {
                'name': 'Compact 80 Column',
                'description': 'Compressed format for 80-column printers',
                'width': 80,
                'form_length': 66,
                'compressed': True
            },
            'short_form': {
                'name': 'Short Form',
                'description': 'Shorter invoice for small items',
                'width': 80,
                'form_length': 44,
                'compressed': False
            },
            'carbon_copy': {
                'name': 'Carbon Copy Format',
                'description': 'Optimized for carbon paper printing',
                'width': 80,
                'form_length': 66,
                'compressed': False,
                'copies': 3
            }
        }
        
        return templates
    
    def save_custom_template(self, name: str, template_content: str, settings: Dict) -> bool:
        """Save a custom dot matrix template"""
        try:
            # Save template to app settings
            template_key = f"dot_matrix_template_{name}"
            self.db.query(AppSetting).filter(AppSetting.key == template_key).delete()
            
            new_setting = AppSetting(
                key=template_key,
                value=template_content,
                description=f"Custom dot matrix template: {name}"
            )
            self.db.add(new_setting)
            
            # Save template settings
            settings_key = f"dot_matrix_settings_{name}"
            self.db.query(AppSetting).filter(AppSetting.key == settings_key).delete()
            
            settings_setting = AppSetting(
                key=settings_key,
                value=str(settings),
                description=f"Settings for template: {name}"
            )
            self.db.add(settings_setting)
            
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            return False


def get_dot_matrix_service(db: Session) -> DotMatrixInvoiceService:
    """Factory function to get DotMatrixInvoiceService instance"""
    return DotMatrixInvoiceService(db)
