"""
POS Receipt Printing Service

This service handles the generation of POS receipts with configurable
formats based on till slip printer types and settings.
"""

from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import datetime
import uuid
from decimal import Decimal

from app.models.app_setting import AppSetting
from app.models.sales import Sale
from app.models.pos import PosSession
from app.models.inventory import Product
from app.models.user import User
from app.models.branch import Branch


class PosReceiptService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = self._load_pos_receipt_settings()

    def _load_pos_receipt_settings(self) -> Dict:
        """Load POS receipt settings from database"""
        pos_keys = [
            'pos_receipt_printer_type', 'pos_default_printer_name', 'pos_auto_print',
            'pos_receipt_width', 'pos_receipt_cut_type', 'pos_header_lines', 'pos_footer_lines',
            'pos_logo_enabled', 'pos_logo_height', 'pos_barcode_enabled', 'pos_qr_code_enabled',
            'pos_print_customer_copy', 'pos_print_merchant_copy', 'pos_template',
            'pos_paper_width_mm', 'pos_char_size', 'pos_line_spacing'
        ]
        
        settings = {}
        for key in pos_keys:
            setting = self.db.query(AppSetting).filter(AppSetting.key == key).first()
            settings[key] = setting.value if setting else None
        
        # Apply defaults
        defaults = {
            'pos_receipt_printer_type': 'thermal_80mm',
            'pos_default_printer_name': '',
            'pos_auto_print': 'true',
            'pos_receipt_width': '48',
            'pos_receipt_cut_type': 'full',
            'pos_header_lines': '3',
            'pos_footer_lines': '2',
            'pos_logo_enabled': 'false',
            'pos_logo_height': '5',
            'pos_barcode_enabled': 'true',
            'pos_qr_code_enabled': 'false',
            'pos_print_customer_copy': 'true',
            'pos_print_merchant_copy': 'false',
            'pos_template': 'standard_thermal',
            'pos_paper_width_mm': '80',
            'pos_char_size': 'normal',
            'pos_line_spacing': 'normal'
        }
        
        for key, default_value in defaults.items():
            if settings[key] is None:
                settings[key] = default_value
        
        # Convert types
        settings['pos_auto_print'] = settings['pos_auto_print'].lower() == 'true'
        settings['pos_receipt_width'] = int(settings['pos_receipt_width'])
        settings['pos_header_lines'] = int(settings['pos_header_lines'])
        settings['pos_footer_lines'] = int(settings['pos_footer_lines'])
        settings['pos_logo_enabled'] = settings['pos_logo_enabled'].lower() == 'true'
        settings['pos_logo_height'] = int(settings['pos_logo_height'])
        settings['pos_barcode_enabled'] = settings['pos_barcode_enabled'].lower() == 'true'
        settings['pos_qr_code_enabled'] = settings['pos_qr_code_enabled'].lower() == 'true'
        settings['pos_print_customer_copy'] = settings['pos_print_customer_copy'].lower() == 'true'
        settings['pos_print_merchant_copy'] = settings['pos_print_merchant_copy'].lower() == 'true'
        settings['pos_paper_width_mm'] = int(settings['pos_paper_width_mm'])
        
        return settings

    def generate_receipt(self, sale_id: str, copy_type: str = 'customer') -> str:
        """
        Generate a receipt for a sale based on configured settings
        
        Args:
            sale_id: ID of the sale
            copy_type: 'customer', 'merchant', or 'both'
        
        Returns:
            Receipt content as string with ESC/POS commands
        """
        sale = self.db.query(Sale).filter(Sale.id == sale_id).first()
        if not sale:
            raise ValueError("Sale not found")
        
        receipt_content = []
        width = self.settings['pos_receipt_width']
        
        # ESC/POS initialization commands
        receipt_content.append(self._get_init_commands())
        
        # Generate receipt based on template
        template = self.settings['pos_template']
        
        if template == 'compact':
            receipt_content.append(self._generate_compact_receipt(sale, width, copy_type))
        elif template == 'detailed':
            receipt_content.append(self._generate_detailed_receipt(sale, width, copy_type))
        elif template == 'logo_top':
            receipt_content.append(self._generate_logo_top_receipt(sale, width, copy_type))
        elif template == 'logo_center':
            receipt_content.append(self._generate_logo_center_receipt(sale, width, copy_type))
        else:
            receipt_content.append(self._generate_standard_receipt(sale, width, copy_type))
        
        # Add cut command
        receipt_content.append(self._get_cut_commands())
        
        return ''.join(receipt_content)

    def _get_init_commands(self) -> str:
        """Get ESC/POS initialization commands"""
        commands = []
        
        # Initialize printer
        commands.append('\x1B@')  # ESC @ - Initialize printer
        
        # Set character size
        char_size = self.settings['pos_char_size']
        if char_size == 'condensed':
            commands.append('\x1B\x0F')  # ESC SI - Select condensed printing
        elif char_size == 'double_width':
            commands.append('\x1B\x20\x01')  # ESC SP - Double width
        elif char_size == 'double_height':
            commands.append('\x1B\x21\x10')  # ESC ! - Double height
        
        # Set line spacing
        line_spacing = self.settings['pos_line_spacing']
        if line_spacing == 'tight':
            commands.append('\x1B3\x18')  # ESC 3 - Set line spacing to 24/180 inch
        elif line_spacing == 'loose':
            commands.append('\x1B3\x30')  # ESC 3 - Set line spacing to 48/180 inch
        else:
            commands.append('\x1B2')  # ESC 2 - Default line spacing
        
        return ''.join(commands)

    def _get_cut_commands(self) -> str:
        """Get paper cut commands based on settings"""
        cut_type = self.settings['pos_receipt_cut_type']
        
        if cut_type == 'full':
            return '\x1D\x56\x00'  # GS V - Full cut
        elif cut_type == 'partial':
            return '\x1D\x56\x01'  # GS V - Partial cut
        else:
            return '\n\n\n\n'  # No cut, just feed paper

    def _generate_standard_receipt(self, sale: Sale, width: int, copy_type: str) -> str:
        """Generate standard thermal receipt"""
        lines = []
        
        # Get company info
        company_name = self._get_setting_value('company_name', 'CNPERP')
        company_phone = self._get_setting_value('company_phone', '')
        company_address = self._get_setting_value('company_address', '')
        tax_number = self._get_setting_value('tax_number', '')
        currency_symbol = self._get_setting_value('currency_symbol', 'R')
        
        # Header
        if self.settings['pos_logo_enabled']:
            lines.extend(self._generate_logo_section(width))
        
        lines.append(self._center_text(company_name, width))
        if company_address:
            lines.append(self._center_text(company_address, width))
        if company_phone:
            lines.append(self._center_text(f"Tel: {company_phone}", width))
        if tax_number:
            lines.append(self._center_text(f"VAT: {tax_number}", width))
        
        lines.append('=' * width)
        
        # Copy type indicator
        if copy_type == 'merchant':
            lines.append(self._center_text('MERCHANT COPY', width))
            lines.append('-' * width)
        
        # Sale information
        lines.append(f"Receipt #: {sale.receipt_number or sale.id[:8]}")
        lines.append(f"Date: {sale.date.strftime('%d/%m/%Y %H:%M')}")
        
        if sale.pos_session:
            lines.append(f"Till: {sale.pos_session.id[:8]}")
            if sale.pos_session.user:
                lines.append(f"Cashier: {sale.pos_session.user.username}")
        
        if sale.customer:
            lines.append(f"Customer: {sale.customer.name}")
        
        lines.append('-' * width)
        
        # Items header
        lines.append('ITEMS')
        lines.append('-' * width)
        
        # Sale items
        for item in sale.sale_items:
            product_name = item.product.name if item.product else 'Unknown Item'
            if len(product_name) > width - 15:
                product_name = product_name[:width - 18] + '...'
            
            # Item line: Name
            lines.append(product_name)
            
            # Price line: Qty x Price = Total
            qty_str = f"{item.quantity}"
            price_str = f"{currency_symbol}{item.unit_price:.2f}"
            total_str = f"{currency_symbol}{item.total_amount:.2f}"
            
            price_line = f"{qty_str} x {price_str}"
            spaces_needed = width - len(price_line) - len(total_str)
            price_line += ' ' * max(1, spaces_needed) + total_str
            lines.append(price_line)
            
            # Discount if applicable
            if item.discount_amount and item.discount_amount > 0:
                discount_line = f"  Discount: -{currency_symbol}{item.discount_amount:.2f}"
                lines.append(discount_line)
        
        lines.append('-' * width)
        
        # Totals
        subtotal = sum(item.subtotal for item in sale.sale_items)
        total_discount = sum(item.discount_amount or 0 for item in sale.sale_items)
        total_vat = sum(item.vat_amount or 0 for item in sale.sale_items)
        
        if total_discount > 0:
            lines.append(self._format_total_line(f"Subtotal:", f"{currency_symbol}{subtotal:.2f}", width))
            lines.append(self._format_total_line(f"Discount:", f"-{currency_symbol}{total_discount:.2f}", width))
        
        lines.append(self._format_total_line(f"VAT:", f"{currency_symbol}{total_vat:.2f}", width))
        lines.append('=' * width)
        lines.append(self._format_total_line(f"TOTAL:", f"{currency_symbol}{sale.total_amount:.2f}", width, bold=True))
        lines.append('=' * width)
        
        # Payment info
        if sale.payment_method:
            payment_method = sale.payment_method.replace('_', ' ').title()
            lines.append(self._format_total_line(f"Payment:", payment_method, width))
        
        if sale.amount_paid:
            lines.append(self._format_total_line(f"Paid:", f"{currency_symbol}{sale.amount_paid:.2f}", width))
            
            if sale.amount_paid > sale.total_amount:
                change = sale.amount_paid - sale.total_amount
                lines.append(self._format_total_line(f"Change:", f"{currency_symbol}{change:.2f}", width))
        
        # Footer
        lines.append('')
        
        # Barcode if enabled
        if self.settings['pos_barcode_enabled']:
            lines.append(self._generate_barcode(sale.receipt_number or sale.id))
        
        # QR code if enabled
        if self.settings['pos_qr_code_enabled']:
            lines.append(self._generate_qr_code(sale))
        
        # Thank you message
        lines.append('')
        lines.append(self._center_text('Thank you for your business!', width))
        lines.append(self._center_text('Please come again', width))
        
        # Add footer spacing
        for _ in range(self.settings['pos_footer_lines']):
            lines.append('')
        
        return '\n'.join(lines)

    def _generate_compact_receipt(self, sale: Sale, width: int, copy_type: str) -> str:
        """Generate compact receipt format"""
        lines = []
        currency_symbol = self._get_setting_value('currency_symbol', 'R')
        company_name = self._get_setting_value('company_name', 'CNPERP')
        
        # Minimal header
        lines.append(self._center_text(company_name, width))
        lines.append('=' * width)
        
        # Copy type
        if copy_type == 'merchant':
            lines.append(self._center_text('MERCHANT', width))
        
        # Essential info
        lines.append(f"#{sale.receipt_number or sale.id[:8]} {sale.date.strftime('%d/%m %H:%M')}")
        
        # Items (compact format)
        for item in sale.sale_items:
            name = item.product.name[:width-10] if item.product else 'Item'
            total = f"{currency_symbol}{item.total_amount:.2f}"
            spaces = width - len(name) - len(total)
            lines.append(f"{name}{' ' * max(1, spaces)}{total}")
        
        lines.append('-' * width)
        
        # Total only
        total_line = f"TOTAL: {currency_symbol}{sale.total_amount:.2f}"
        lines.append(self._center_text(total_line, width))
        
        # Minimal footer
        lines.append('')
        lines.append(self._center_text('Thank you!', width))
        lines.append('')
        
        return '\n'.join(lines)

    def _generate_detailed_receipt(self, sale: Sale, width: int, copy_type: str) -> str:
        """Generate detailed receipt with extra information"""
        # Start with standard receipt
        receipt = self._generate_standard_receipt(sale, width, copy_type)
        
        # Add extra details
        extra_lines = []
        
        # Branch info
        if sale.branch:
            extra_lines.append('')
            extra_lines.append(f"Branch: {sale.branch.name}")
            if sale.branch.location:
                extra_lines.append(f"Location: {sale.branch.location}")
        
        # Sale statistics
        total_items = sum(item.quantity for item in sale.sale_items)
        extra_lines.append('')
        extra_lines.append(f"Total Items: {total_items}")
        extra_lines.append(f"Transaction ID: {sale.id}")
        
        # Insert extra details before footer
        receipt_lines = receipt.split('\n')
        thank_you_index = next((i for i, line in enumerate(receipt_lines) if 'Thank you' in line), -3)
        receipt_lines[thank_you_index:thank_you_index] = extra_lines
        
        return '\n'.join(receipt_lines)

    def _generate_logo_section(self, width: int) -> List[str]:
        """Generate logo section (placeholder for actual logo)"""
        lines = []
        
        # Add space for logo
        for _ in range(self.settings['pos_logo_height']):
            lines.append(' ' * width)
        
        lines.append('')
        return lines

    def _generate_logo_top_receipt(self, sale: Sale, width: int, copy_type: str) -> str:
        """Generate receipt with logo at top"""
        lines = []
        
        # Logo at top
        if self.settings['pos_logo_enabled']:
            lines.extend(self._generate_logo_section(width))
        
        # Continue with standard receipt content
        standard_receipt = self._generate_standard_receipt(sale, width, copy_type)
        
        # Skip the company name section since logo replaces it
        standard_lines = standard_receipt.split('\n')
        company_end = next((i for i, line in enumerate(standard_lines) if line.startswith('=')), 0)
        
        lines.extend(standard_lines[company_end:])
        
        return '\n'.join(lines)

    def _generate_logo_center_receipt(self, sale: Sale, width: int, copy_type: str) -> str:
        """Generate receipt with centered logo"""
        standard_receipt = self._generate_standard_receipt(sale, width, copy_type)
        
        if not self.settings['pos_logo_enabled']:
            return standard_receipt
        
        lines = standard_receipt.split('\n')
        
        # Find center point (after company info, before items)
        items_start = next((i for i, line in enumerate(lines) if line == 'ITEMS'), len(lines))
        
        # Insert logo before items
        logo_lines = self._generate_logo_section(width)
        lines[items_start:items_start] = [''] + logo_lines
        
        return '\n'.join(lines)

    def _generate_barcode(self, barcode_data: str) -> str:
        """Generate barcode ESC/POS commands"""
        if not barcode_data:
            return ''
        
        # ESC/POS barcode commands (Code 128)
        commands = []
        commands.append('\x1D\x48\x02')  # GS H - Print barcode readable characters below
        commands.append('\x1D\x77\x02')  # GS w - Set barcode width
        commands.append('\x1D\x68\x60')  # GS h - Set barcode height
        commands.append(f'\x1D\x6B\x49{len(barcode_data):02d}{barcode_data}')  # GS k - Print barcode
        
        return ''.join(commands)

    def _generate_qr_code(self, sale: Sale) -> str:
        """Generate QR code ESC/POS commands"""
        # QR code with sale information
        qr_data = f"Sale:{sale.id},Amount:{sale.total_amount},Date:{sale.date.isoformat()}"
        
        commands = []
        commands.append('\x1D\x28\x6B\x04\x00\x31\x41\x32\x00')  # Set QR code model
        commands.append('\x1D\x28\x6B\x03\x00\x31\x43\x08')  # Set QR code size
        commands.append('\x1D\x28\x6B\x03\x00\x31\x45\x30')  # Set error correction
        
        # Store QR code data
        data_length = len(qr_data) + 3
        commands.append(f'\x1D\x28\x6B{data_length:04x}\x31\x50\x30{qr_data}')
        
        # Print QR code
        commands.append('\x1D\x28\x6B\x03\x00\x31\x51\x30')
        
        return ''.join(commands)

    def _center_text(self, text: str, width: int) -> str:
        """Center text within specified width"""
        if len(text) >= width:
            return text[:width]
        
        padding = (width - len(text)) // 2
        return ' ' * padding + text

    def _format_total_line(self, label: str, value: str, width: int, bold: bool = False) -> str:
        """Format a total line with label and value"""
        spaces_needed = width - len(label) - len(value)
        line = label + ' ' * max(1, spaces_needed) + value
        
        if bold:
            # ESC/POS bold commands
            line = '\x1B\x45\x01' + line + '\x1B\x45\x00'
        
        return line

    def _get_setting_value(self, key: str, default: str = '') -> str:
        """Get app setting value"""
        setting = self.db.query(AppSetting).filter(AppSetting.key == key).first()
        return setting.value if setting else default

    def should_auto_print(self) -> bool:
        """Check if auto-printing is enabled"""
        return self.settings['pos_auto_print']

    def get_copies_to_print(self) -> List[str]:
        """Get list of copy types to print based on settings"""
        copies = []
        
        if self.settings['pos_print_customer_copy']:
            copies.append('customer')
        
        if self.settings['pos_print_merchant_copy']:
            copies.append('merchant')
        
        return copies or ['customer']  # Default to customer copy

    def get_printer_config(self) -> Dict:
        """Get current printer configuration"""
        return {
            'printer_type': self.settings['pos_receipt_printer_type'],
            'printer_name': self.settings['pos_default_printer_name'],
            'paper_width': self.settings['pos_receipt_width'],
            'paper_width_mm': self.settings['pos_paper_width_mm'],
            'auto_print': self.settings['pos_auto_print'],
            'cut_type': self.settings['pos_receipt_cut_type'],
            'template': self.settings['pos_template']
        }
