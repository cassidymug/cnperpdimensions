from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models.sales import Sale, SaleItem, Customer
from app.models.user import User
from app.models.branch import Branch
from app.models.receipt import Receipt
import uuid
import os
from reportlab.lib.pagesizes import letter, A4, inch, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.units import inch, mm


class ReceiptService:
    """Service for generating and managing receipts"""

    def __init__(self, db: Session):
        self.db = db
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.static_dir = os.path.join(base_dir, "static")
        self.receipts_dir = os.path.join(self.static_dir, "receipts")
        os.makedirs(self.static_dir, exist_ok=True)
        os.makedirs(self.receipts_dir, exist_ok=True)
        self.public_receipts_prefix = "/static/receipts"

    def generate_receipt(self, sale_id: str, user_id: str, format_type: str = None) -> Dict:
        """Generate a receipt for a completed sale with specified format"""
        try:
            # Get sale with related data
            sale = self.db.query(Sale).filter_by(id=sale_id).first()
            if not sale:
                return {'success': False, 'error': 'Sale not found'}

            # Get sale items with product details
            sale_items = self.db.query(SaleItem).filter_by(sale_id=sale_id).all()

            # Get user and branch info
            user = self.db.query(User).filter_by(id=user_id).first()
            branch = self.db.query(Branch).filter_by(id=sale.branch_id).first()

            # Get customer info if available
            customer = None
            if sale.customer_id:
                customer = self.db.query(Customer).filter_by(id=sale.customer_id).first()

            # Get app settings for company info and default format
            from app.models.app_setting import AppSetting
            app_settings = self.db.query(AppSetting).first()

            # Use provided format or default from settings
            if not format_type and app_settings:
                format_type = app_settings.default_receipt_format or "80mm"
            elif not format_type:
                format_type = "80mm"  # fallback default

            # Generate receipt number
            receipt_number = f"RCP-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

            # Create receipt record
            receipt = Receipt(
                sale_id=sale_id,
                receipt_number=receipt_number,
                created_by_user_id=user_id,
                branch_id=sale.branch_id,
                customer_id=sale.customer_id,
                amount=sale.total_amount or 0,
                currency=sale.currency or "BWP",
                payment_method=sale.payment_method,
                payment_date=sale.date or sale.sale_time or datetime.utcnow(),
                notes=f"Receipt for Sale {sale.reference}" if sale.reference else None
            )
            self.db.add(receipt)
            self.db.flush()

            # Generate receipt data
            receipt_data = self._prepare_receipt_data(sale, sale_items, user, branch, customer, app_settings, receipt_number)

            # Generate PDF based on format
            pdf_path = self._generate_pdf(receipt_data, receipt_number, format_type)

            # Generate HTML
            html_content = self._generate_html(receipt_data, format_type)

            # Update receipt record
            receipt.pdf_path = pdf_path
            receipt.html_content = html_content

            self.db.commit()

            return {
                'success': True,
                'receipt_id': receipt.id,
                'receipt_number': receipt_number,
                'pdf_path': pdf_path,
                'html_content': html_content,
                'receipt_data': receipt_data
            }

        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def _prepare_receipt_data(self, sale: Sale, sale_items: List[SaleItem],
                            user: User, branch: Branch, customer: Customer,
                            app_settings, receipt_number: str) -> Dict:
        """Prepare receipt data for generation"""
        items_data = []
        subtotal = 0

        for item in sale_items:
            item_total = item.total_amount
            subtotal += item_total

            items_data.append({
                'name': item.product.name if item.product else 'Unknown Product',
                'quantity': item.quantity,
                'unit_price': item.selling_price,
                'total': item_total
            })

        return {
            'receipt_number': receipt_number,
            'date': sale.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'time': sale.created_at.strftime('%H:%M:%S'),
            'date_only': sale.created_at.strftime('%Y-%m-%d'),
            # Company Information
            'company_name': app_settings.app_name if app_settings else 'Company Name',
            'company_address': app_settings.address if app_settings else '',
            'company_phone': app_settings.phone if app_settings else '',
            'company_email': app_settings.email if app_settings else '',
            'company_website': app_settings.website if app_settings else '',
            'company_vat_number': app_settings.vat_registration_number if app_settings else '',
            'company_logo_url': branch.company_logo_url if branch else '',
            # Branch Information
            'branch_name': branch.name if branch else 'Main Branch',
            'branch_address': branch.address if branch else '',
            'branch_phone': branch.phone if branch else '',
            'branch_email': branch.email if branch else '',
            'branch_vat_number': branch.vat_registration_number if branch else '',
            # Customer Information
            'customer_name': customer.name if customer else 'Walk-in Customer',
            'customer_address': customer.address if customer else '',
            'customer_phone': customer.phone if customer else '',
            'customer_email': customer.email if customer else '',
            'customer_vat_number': customer.vat_reg_number if customer else '',
            # Transaction Details
            'cashier': f"{user.first_name} {user.last_name}" if user else 'System',
            'items': items_data,
            'subtotal': subtotal,
            'vat_amount': sale.total_vat_amount,
            'total_amount': sale.total_amount,
            'amount_tendered': sale.amount_tendered,
            'change_given': sale.change_given,
            'payment_method': sale.payment_method,
            'sale_reference': sale.reference
        }

    def _generate_pdf(self, receipt_data: Dict, receipt_number: str, format_type: str = "a4") -> str:
        """Generate PDF receipt with specified format"""
        filename = f"{receipt_number}.pdf"
        filepath = os.path.join(self.receipts_dir, filename)

        # Define page sizes
        if format_type == "50mm":
            # 50mm thermal paper (approximately 1.97 inches wide)
            page_width = 50 * mm
            page_height = 200 * mm  # Shorter height for testing
        elif format_type == "80mm":
            # 80mm thermal paper (approximately 3.15 inches wide)
            page_width = 80 * mm
            page_height = 297 * mm  # A4 height for long receipts
        else:  # A4 or default
            page_width, page_height = A4

        # Create document with specific margins for thermal paper
        if format_type in ["50mm", "80mm"]:
            doc = SimpleDocTemplate(filepath, pagesize=(page_width, page_height),
                                  leftMargin=2*mm, rightMargin=2*mm,
                                  topMargin=2*mm, bottomMargin=2*mm)
        else:
            doc = SimpleDocTemplate(filepath, pagesize=(page_width, page_height))
        styles = getSampleStyleSheet()
        story = []

        # Define styles based on format
        if format_type == "50mm":
            # Thermal paper styles - very compact for 50mm
            title_style = ParagraphStyle(
                'ThermalTitle',
                parent=styles['Heading2'],
                fontSize=10,
                spaceAfter=3,
                alignment=1,  # Center
                fontName='Helvetica-Bold'
            )
            header_style = ParagraphStyle(
                'ThermalHeader',
                parent=styles['Normal'],
                fontSize=6,
                spaceAfter=2,
                alignment=1
            )
            normal_style = ParagraphStyle(
                'ThermalNormal',
                parent=styles['Normal'],
                fontSize=6,
                spaceAfter=2
            )
            table_font_size = 6
        elif format_type == "80mm":
            # Thermal paper styles - compact
            title_style = ParagraphStyle(
                'ThermalTitle',
                parent=styles['Heading2'],
                fontSize=12,
                spaceAfter=5,
                alignment=1,  # Center
                fontName='Helvetica-Bold'
            )
            header_style = ParagraphStyle(
                'ThermalHeader',
                parent=styles['Normal'],
                fontSize=8,
                spaceAfter=2,
                alignment=1
            )
            normal_style = ParagraphStyle(
                'ThermalNormal',
                parent=styles['Normal'],
                fontSize=7,
                spaceAfter=2
            )
            table_font_size = 7
        else:
            # A4 styles - normal
            title_style = ParagraphStyle(
                'A4Title',
                parent=styles['Heading1'],
                fontSize=20,
                spaceAfter=20,
                alignment=1
            )
            header_style = ParagraphStyle(
                'A4Header',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=5,
                alignment=1
            )
            normal_style = ParagraphStyle(
                'A4Normal',
                parent=styles['Normal'],
                fontSize=9,
                spaceAfter=5
            )
            table_font_size = 9

        # Company Header
        if format_type not in ["50mm", "80mm"]:
            # Add company logo for A4 (if available)
            if receipt_data.get('company_logo_url'):
                try:
                    logo_rel = receipt_data['company_logo_url'].lstrip('/\\')
                    logo_path = os.path.join(self.static_dir, logo_rel)
                    if os.path.exists(logo_path):
                        logo = Image(logo_path, width=2*inch, height=1*inch)
                        logo.hAlign = 'CENTER'
                        story.append(logo)
                        story.append(Spacer(1, 10))
                except:
                    pass  # Logo not found, continue without it

        # Company Name
        company_name = receipt_data['company_name']
        if format_type == "50mm":
            # For 50mm, use a very short name or abbreviation
            if len(company_name) > 10:
                company_name = "CNPERP"  # Use a short version
        story.append(Paragraph(company_name, title_style))
        story.append(Spacer(1, 3))

        # Company Details (simplified for 50mm)
        if format_type == "50mm":
            # Very minimal for 50mm
            if receipt_data.get('company_vat_number'):
                story.append(Paragraph(f"VAT: {receipt_data['company_vat_number'][:10]}", header_style))
        else:
            # Full details for 80mm and A4
            if receipt_data.get('company_address'):
                story.append(Paragraph(receipt_data['company_address'], header_style))
            if receipt_data.get('company_phone'):
                story.append(Paragraph(f"Tel: {receipt_data['company_phone']}", header_style))
            if receipt_data.get('company_vat_number'):
                story.append(Paragraph(f"VAT No: {receipt_data['company_vat_number']}", header_style))
        story.append(Spacer(1, 10))

        # Branch Details (if different from company)
        if receipt_data.get('branch_name') and receipt_data['branch_name'] != receipt_data['company_name']:
            story.append(Paragraph(f"Branch: {receipt_data['branch_name']}", normal_style))
            if receipt_data.get('branch_address'):
                story.append(Paragraph(receipt_data['branch_address'], normal_style))
            if receipt_data.get('branch_vat_number') and receipt_data['branch_vat_number'] != receipt_data.get('company_vat_number'):
                story.append(Paragraph(f"Branch VAT: {receipt_data['branch_vat_number']}", normal_style))

        # Receipt Info
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Receipt #: {receipt_data['receipt_number']}", normal_style))
        story.append(Paragraph(f"Date: {receipt_data['date_only']} {receipt_data['time']}", normal_style))
        story.append(Paragraph(f"Cashier: {receipt_data['cashier']}", normal_style))
        if receipt_data.get('sale_reference'):
            story.append(Paragraph(f"Reference: {receipt_data['sale_reference']}", normal_style))
        story.append(Spacer(1, 10))

        # Customer Information
        if receipt_data.get('customer_name') and receipt_data['customer_name'] != 'Walk-in Customer':
            story.append(Paragraph("CUSTOMER DETAILS", title_style))
            story.append(Paragraph(f"Name: {receipt_data['customer_name']}", normal_style))
            if receipt_data.get('customer_address'):
                story.append(Paragraph(f"Address: {receipt_data['customer_address']}", normal_style))
            if receipt_data.get('customer_vat_number'):
                story.append(Paragraph(f"VAT No: {receipt_data['customer_vat_number']}", normal_style))
            story.append(Spacer(1, 10))

        # Items Table
        if format_type == "50mm":
            # Compact table for 50mm thermal paper - single column for item name
            table_data = [['Item', 'Total']]
            for item in receipt_data['items']:
                item_name = item['name']
                if len(item_name) > 15:
                    item_name = item_name[:15] + "..."
                table_data.append([
                    item_name,
                    f"P {item['total']:.2f}"
                ])
        elif format_type == "80mm":
            # Compact table for 80mm thermal paper
            table_data = [['Item', 'Qty', 'Total']]
            for item in receipt_data['items']:
                table_data.append([
                    item['name'][:20] + '...' if len(item['name']) > 20 else item['name'],
                    str(item['quantity']),
                    f"P {item['total']:.2f}"
                ])
        else:
            # Full table for A4
            table_data = [['Item', 'Qty', 'Price', 'Total']]
            for item in receipt_data['items']:
                table_data.append([
                    item['name'],
                    str(item['quantity']),
                    f"P {item['unit_price']:.2f}",
                    f"P {item['total']:.2f}"
                ])

        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), table_font_size),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), table_font_size - 1),
        ]))
        story.append(table)
        story.append(Spacer(1, 10))

        # Totals
        if format_type in ["50mm", "80mm"]:
            # Compact totals for thermal paper
            story.append(Paragraph(f"Subtotal: P {receipt_data['subtotal']:.2f}", normal_style))
            if receipt_data.get('vat_amount'):
                story.append(Paragraph(f"VAT: P {receipt_data['vat_amount']:.2f}", normal_style))
            story.append(Paragraph(f"TOTAL: P {receipt_data['total_amount']:.2f}", title_style))
        else:
            # Full totals for A4
            totals_data = [
                ['Subtotal:', f"P {receipt_data['subtotal']:.2f}"],
                ['VAT:', f"P {receipt_data['vat_amount']:.2f}"],
                ['TOTAL:', f"P {receipt_data['total_amount']:.2f}"]
            ]
            totals_table = Table(totals_data, colWidths=[2*inch, 1.5*inch])
            totals_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, -1), (1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            story.append(totals_table)

        story.append(Spacer(1, 10))

        # Payment Information
        story.append(Paragraph(f"Payment: {receipt_data['payment_method'].title()}", normal_style))
        if receipt_data.get('amount_tendered'):
            story.append(Paragraph(f"Tendered: P {receipt_data['amount_tendered']:.2f}", normal_style))
        if receipt_data.get('change_given'):
            story.append(Paragraph(f"Change: P {receipt_data['change_given']:.2f}", normal_style))

        story.append(Spacer(1, 15))

        # Footer
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8 if format_type in ["50mm", "80mm"] else 10,
            alignment=1
        )
        story.append(Paragraph("Thank you for your business!", footer_style))
        story.append(Paragraph("Please keep this receipt for your records.", footer_style))

        # Add company website if available
        if receipt_data.get('company_website'):
            story.append(Paragraph(receipt_data['company_website'], footer_style))

        doc.build(story)
        return f"{self.public_receipts_prefix}/{filename}"

    def _generate_html(self, receipt_data: Dict, format_type: str = "a4") -> str:
        """Generate HTML receipt for web display with specified format"""
        # Define CSS based on format
        if format_type == "50mm":
            container_width = "50mm"
            font_size = "7px"
            padding = "2mm"
        elif format_type == "80mm":
            container_width = "80mm"
            font_size = "8px"
            padding = "3mm"
        else:  # A4
            container_width = "210mm"
            font_size = "12px"
            padding = "20px"

        # Build items table
        items_html = ""
        for item in receipt_data['items']:
            if format_type in ["50mm", "80mm"]:
                # Compact format for thermal paper
                items_html += f"""
                <tr>
                    <td style="font-size: {font_size};">{item['name'][:25]}{'...' if len(item['name']) > 25 else ''}</td>
                    <td style="text-align: center; font-size: {font_size};">{item['quantity']}</td>
                    <td style="text-align: right; font-size: {font_size};">P {item['total']:.2f}</td>
                </tr>
                """
            else:
                # Full format for A4
                items_html += f"""
                <tr>
                    <td>{item['name']}</td>
                    <td style="text-align: center;">{item['quantity']}</td>
                    <td style="text-align: right;">P {item['unit_price']:.2f}</td>
                    <td style="text-align: right;">P {item['total']:.2f}</td>
                </tr>
                """

        # Company logo HTML
        logo_html = ""
        if format_type not in ["50mm", "80mm"] and receipt_data.get('company_logo_url'):
            logo_url = receipt_data['company_logo_url']
            if not logo_url.lower().startswith(('http://', 'https://')):
                # Ensure logo paths resolve through the FastAPI static mount only once
                logo_rel = logo_url.lstrip('/\\')
                logo_url = f'/static/{logo_rel}' if not logo_rel.startswith('static/') else f'/{logo_rel}'
            logo_html = f'<img src="{logo_url}" alt="Company Logo" style="max-width: 200px; max-height: 100px; display: block; margin: 0 auto 10px;"><br>'

        # Customer details HTML
        customer_html = ""
        if receipt_data.get('customer_name') and receipt_data['customer_name'] != 'Walk-in Customer':
            customer_html = f"""
            <div style="border: 1px solid #ccc; padding: 10px; margin: 10px 0; background-color: #f9f9f9;">
                <strong>CUSTOMER DETAILS</strong><br>
                <strong>Name:</strong> {receipt_data['customer_name']}<br>
                {'<strong>Address:</strong> ' + receipt_data['customer_address'] + '<br>' if receipt_data.get('customer_address') else ''}
                {'<strong>VAT No:</strong> ' + receipt_data['customer_vat_number'] + '<br>' if receipt_data.get('customer_vat_number') else ''}
            </div>
            """

        html = f"""
        <div style="max-width: {container_width}; margin: 0 auto; font-family: 'Courier New', monospace; border: 1px solid #ccc; padding: {padding}; font-size: {font_size}; line-height: 1.2;">
            {logo_html}
            <div style="text-align: center; margin-bottom: 10px;">
                <h2 style="margin: 5px 0; font-size: {font_size};">{receipt_data['company_name']}</h2>
                {'<p style="margin: 2px 0;">' + receipt_data['company_address'] + '</p>' if receipt_data.get('company_address') else ''}
                {'<p style="margin: 2px 0;">Tel: ' + receipt_data['company_phone'] + '</p>' if receipt_data.get('company_phone') else ''}
                {'<p style="margin: 2px 0;">VAT No: ' + receipt_data['company_vat_number'] + '</p>' if receipt_data.get('company_vat_number') else ''}
            </div>

            {'<div style="text-align: center; margin-bottom: 10px; border-top: 1px solid #ccc; padding-top: 5px;">' + receipt_data['branch_name'] + '<br>' + (receipt_data['branch_address'] if receipt_data.get('branch_address') else '') + '</div>' if receipt_data.get('branch_name') and receipt_data['branch_name'] != receipt_data['company_name'] else ''}

            <div style="margin-bottom: 10px;">
                <strong>Receipt #:</strong> {receipt_data['receipt_number']}<br>
                <strong>Date:</strong> {receipt_data['date_only']} {receipt_data['time']}<br>
                <strong>Cashier:</strong> {receipt_data['cashier']}<br>
                {'<strong>Reference:</strong> ' + receipt_data['sale_reference'] + '<br>' if receipt_data.get('sale_reference') else ''}
            </div>

            {customer_html}

            <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
                <thead>
                    <tr style="background-color: #f0f0f0;">
                        {'<th style="border: 1px solid #ccc; padding: 3px;">Item</th><th style="border: 1px solid #ccc; padding: 3px; text-align: center;">Qty</th><th style="border: 1px solid #ccc; padding: 3px; text-align: right;">Total</th>' if format_type in ["50mm", "80mm"] else '<th style="border: 1px solid #ccc; padding: 5px;">Item</th><th style="border: 1px solid #ccc; padding: 5px; text-align: center;">Qty</th><th style="border: 1px solid #ccc; padding: 5px; text-align: right;">Price</th><th style="border: 1px solid #ccc; padding: 5px; text-align: right;">Total</th>'}
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>

            <div style="margin: 10px 0;">
                {'<div style="display: flex; justify-content: space-between;"><span>Subtotal:</span><span>P ' + str(receipt_data['subtotal']) + '</span></div>' if format_type in ["50mm", "80mm"] else '<div style="display: flex; justify-content: space-between; margin: 5px 0;"><span><strong>Subtotal:</strong></span><span>P ' + str(receipt_data['subtotal']) + '</span></div>'}
                {'<div style="display: flex; justify-content: space-between;"><span>VAT:</span><span>P ' + str(receipt_data['vat_amount']) + '</span></div>' if receipt_data.get('vat_amount') else ''}
                {'<div style="display: flex; justify-content: space-between; border-top: 1px solid #000; padding-top: 5px; margin-top: 5px;"><span><strong>TOTAL:</strong></span><span><strong>P ' + str(receipt_data['total_amount']) + '</strong></span></div>' if format_type in ["50mm", "80mm"] else '<div style="display: flex; justify-content: space-between; border-top: 2px solid #000; padding-top: 10px; margin-top: 10px;"><span><strong>TOTAL:</strong></span><span><strong>P ' + str(receipt_data['total_amount']) + '</strong></span></div>'}
            </div>

            <div style="margin: 10px 0;">
                <strong>Payment:</strong> {receipt_data['payment_method'].title()}<br>
                {'<strong>Tendered:</strong> P ' + str(receipt_data['amount_tendered']) + '<br>' if receipt_data.get('amount_tendered') else ''}
                {'<strong>Change:</strong> P ' + str(receipt_data['change_given']) + '<br>' if receipt_data.get('change_given') else ''}
            </div>

            <div style="text-align: center; margin-top: 15px; border-top: 1px solid #ccc; padding-top: 10px;">
                <p style="margin: 5px 0;"><strong>Thank you for your business!</strong></p>
                <p style="margin: 5px 0;">Please keep this receipt for your records.</p>
                {'<p style="margin: 5px 0;">' + receipt_data['company_website'] + '</p>' if receipt_data.get('company_website') else ''}
            </div>
        </div>
        """
        return html

    def get_receipt(self, receipt_id: str) -> Optional[Receipt]:
        """Get receipt by ID"""
        from sqlalchemy.orm import joinedload
        return self.db.query(Receipt).options(
            joinedload(Receipt.created_by_user),
            joinedload(Receipt.branch)
        ).filter_by(id=receipt_id).first()

    def get_receipts_by_sale(self, sale_id: str) -> List[Receipt]:
        """Get all receipts for a sale"""
        from sqlalchemy.orm import joinedload
        return self.db.query(Receipt).options(
            joinedload(Receipt.created_by_user),
            joinedload(Receipt.branch)
        ).filter_by(sale_id=sale_id).all()

    def get_recent_receipts(self, limit: int = 20, branch_id: Optional[str] = None) -> List[Receipt]:
        """Return the most recent receipts, optionally filtered by branch."""
        from sqlalchemy.orm import joinedload

        query = self.db.query(Receipt).options(
            joinedload(Receipt.created_by_user),
            joinedload(Receipt.branch)
        ).order_by(Receipt.created_at.desc())
        if branch_id:
            query = query.filter(Receipt.branch_id == branch_id)
        return query.limit(max(1, limit)).all()

    def search_receipts(self, query: str = "", status: str = "", start_date: str = "", end_date: str = "", skip: int = 0, limit: int = 100):
        """Search receipts with filters"""
        from sqlalchemy import or_, and_
        from sqlalchemy.orm import joinedload

        db_query = self.db.query(Receipt).options(
            joinedload(Receipt.created_by_user),
            joinedload(Receipt.branch)
        )

        # Text search
        if query:
            db_query = db_query.filter(
                or_(
                    Receipt.receipt_number.ilike(f"%{query}%"),
                    Receipt.sale_id.ilike(f"%{query}%")
                )
            )

        # Status filter
        if status == "printed":
            db_query = db_query.filter(Receipt.printed == True)
        elif status == "not_printed":
            db_query = db_query.filter(Receipt.printed == False)

        # Date range filter
        if start_date:
            from datetime import datetime
            start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            db_query = db_query.filter(Receipt.created_at >= start)

        if end_date:
            from datetime import datetime
            end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            db_query = db_query.filter(Receipt.created_at <= end)

        total = db_query.count()
        receipts = db_query.offset(skip).limit(limit).all()

        return {
            "total": total,
            "receipts": receipts
        }

    def get_receipt_stats(self):
        """Get receipt statistics"""
        from sqlalchemy import func

        # Total receipts
        total = self.db.query(func.count(Receipt.id)).scalar()

        # Printed receipts
        printed = self.db.query(func.count(Receipt.id)).filter(Receipt.printed == True).scalar()

        # This month's receipts
        from datetime import datetime
        start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly = self.db.query(func.count(Receipt.id)).filter(Receipt.created_at >= start_of_month).scalar()

        return {
            "total_receipts": total,
            "printed_receipts": printed,
            "pending_receipts": total - printed,
            "monthly_receipts": monthly
        }

    def bulk_print_receipts(self, receipt_ids: List[str]):
        """Bulk print multiple receipts"""
        results = []

        for receipt_id in receipt_ids:
            success = self.mark_receipt_printed(receipt_id)
            results.append({
                'receipt_id': receipt_id,
                'success': success
            })

        return results

    def mark_receipt_printed(self, receipt_id: str) -> bool:
        """Mark a receipt as printed and increment print count"""
        try:
            receipt = self.db.query(Receipt).filter(Receipt.id == receipt_id).first()
            if receipt:
                receipt.printed = True
                receipt.print_count = (receipt.print_count or 0) + 1
                self.db.commit()
                return True
            return False
        except Exception as e:
            self.db.rollback()
            print(f"Error marking receipt as printed: {e}")
            return False

    def record_invoice_payment(self, invoice_id: str, payment_data: Dict[str, object], user_id: str, format_type: Optional[str] = None) -> Dict[str, object]:
        """Record a manual payment for an invoice and generate a receipt."""
        try:
            from app.models.sales import Invoice, Payment

            invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
            if not invoice:
                invoice = self.db.query(Invoice).filter(Invoice.invoice_number == invoice_id).first()
            if not invoice:
                return {"success": False, "error": "Invoice not found"}

            if not invoice.customer_id:
                return {"success": False, "error": "Invoice is missing a customer"}

            amount = Decimal(str(payment_data.get("amount", "0")))
            if amount <= 0:
                return {"success": False, "error": "Payment amount must be greater than zero"}

            already_paid = Decimal(invoice.amount_paid or 0)
            total_amount = Decimal(invoice.total_amount or 0)
            remaining = total_amount - already_paid

            if remaining <= 0:
                return {"success": False, "error": "Invoice is already fully paid"}

            if amount > remaining:
                return {"success": False, "error": "Payment exceeds outstanding balance"}

            payment = Payment(
                invoice_id=invoice.id,
                customer_id=invoice.customer_id,
                amount=amount,
                payment_date=payment_data.get("payment_date") or datetime.utcnow().date(),
                payment_method=payment_data.get("payment_method") or "cash",
                reference=payment_data.get("reference"),
                note=payment_data.get("note"),
                payment_status="completed",
                created_by=user_id
            )

            self.db.add(payment)

            invoice.amount_paid = already_paid + amount
            remaining_after = total_amount - invoice.amount_paid
            if hasattr(invoice, 'amount_due'):
                invoice.amount_due = remaining_after

            if remaining_after <= 0:
                if hasattr(invoice, 'amount_due'):
                    invoice.amount_due = Decimal('0')
                invoice.status = "paid"
                invoice.paid_at = datetime.utcnow()
            else:
                invoice.status = "partial"

            # Update customer account balance (reduce receivables)
            from app.models.sales import Customer
            customer = self.db.query(Customer).filter(Customer.id == invoice.customer_id).first()
            if customer:
                current_balance = Decimal(customer.account_balance or 0)
                new_balance = current_balance - amount
                customer.account_balance = new_balance
                self.db.add(customer)
                print(f"[CUSTOMER_BALANCE] Customer {customer.id} ({customer.name}) balance updated: P{current_balance} -> P{new_balance} (payment: P{amount})")

            self.db.flush()

            try:
                from app.services.accounting_service import AccountingService
                accounting_service = AccountingService(self.db)
                accounting_service.record_payment(payment)
            except Exception as accounting_error:
                print(f"[ACCOUNTING_WARN] Failed to post payment entry: {accounting_error}")

            self.db.commit()

            receipt_result = self.generate_invoice_receipt(invoice.id, payment.id, user_id, format_type)
            if not receipt_result.get("success"):
                return {
                    "success": False,
                    "error": receipt_result.get("error", "Failed to generate receipt"),
                    "payment_id": payment.id
                }

            payment_payload = {
                "id": payment.id,
                "invoice_id": payment.invoice_id,
                "customer_id": payment.customer_id,
                "amount": float(payment.amount or 0),
                "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
                "payment_method": payment.payment_method,
                "reference": payment.reference,
                "note": payment.note
            }

            return {
                "success": True,
                "payment": payment_payload,
                "receipt": receipt_result
            }
        except Exception as exc:
            self.db.rollback()
            return {"success": False, "error": str(exc)}

    def generate_invoice_receipt(self, invoice_id: str, payment_id: str, user_id: str = None, format_type: str = None) -> Dict:
        """Generate a receipt for a cash invoice payment"""
        try:
            from app.models.sales import Invoice, InvoiceItem, Payment, Customer

            # Get invoice with related data
            invoice = self.db.query(Invoice).filter_by(id=invoice_id).first()
            if not invoice:
                return {'success': False, 'error': 'Invoice not found'}

            # Get payment details
            payment = self.db.query(Payment).filter_by(id=payment_id).first()
            if not payment:
                return {'success': False, 'error': 'Payment not found'}

            # Get invoice items
            invoice_items = self.db.query(InvoiceItem).filter_by(invoice_id=invoice_id).all()

            # Get user and branch info
            user = self.db.query(User).filter_by(id=user_id).first() if user_id else None
            branch = self.db.query(Branch).filter_by(id=invoice.branch_id).first()

            # Get customer info
            customer = self.db.query(Customer).filter_by(id=invoice.customer_id).first()

            # Get app settings for company info and default format
            from app.models.app_setting import AppSetting
            app_settings = self.db.query(AppSetting).first()

            # Use provided format or default from settings
            if not format_type and app_settings:
                format_type = app_settings.default_receipt_format or "80mm"
            elif not format_type:
                format_type = "80mm"  # fallback default

            # Generate receipt number
            receipt_number = f"RCP-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

            # Create receipt record
            receipt = Receipt(
                sale_id=None,
                invoice_id=invoice.id,
                payment_id=payment.id,
                customer_id=invoice.customer_id,
                receipt_number=receipt_number,
                created_by_user_id=user_id or 'system',
                branch_id=invoice.branch_id,
                amount=payment.amount or invoice.total_amount or 0,
                currency=getattr(invoice, 'currency', None) or 'BWP',
                payment_method=payment.payment_method,
                payment_date=datetime.combine(payment.payment_date, datetime.min.time()) if hasattr(payment, 'payment_date') and payment.payment_date else datetime.utcnow(),
                notes=f"Receipt for Invoice {invoice.invoice_number}"
            )
            self.db.add(receipt)
            self.db.flush()

            # Generate receipt data for invoice
            receipt_data = self._prepare_invoice_receipt_data(
                invoice, invoice_items, payment, user, branch, customer, app_settings, receipt_number
            )

            # Generate PDF based on format
            pdf_path = self._generate_pdf(receipt_data, receipt_number, format_type)

            # Generate HTML
            html_content = self._generate_html(receipt_data, format_type)

            # Update receipt record
            receipt.pdf_path = pdf_path
            receipt.html_content = html_content

            self.db.commit()

            return {
                'success': True,
                'receipt_id': receipt.id,
                'receipt_number': receipt_number,
                'pdf_path': pdf_path,
                'html_content': html_content,
                'receipt_data': receipt_data
            }

        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def _prepare_invoice_receipt_data(self, invoice, invoice_items: List, payment,
                                    user: User, branch: Branch, customer: Customer,
                                    app_settings, receipt_number: str) -> Dict:
        """Prepare receipt data for invoice payment"""
        items_data = []
        subtotal = 0

        for item in invoice_items:
            quantity = float(item.quantity or 0)
            unit_price = float(getattr(item, "price", None) or getattr(item, "unit_price", 0) or 0)
            item_total = float(getattr(item, "total", None) or (quantity * unit_price))
            subtotal += item_total

            items_data.append({
                'name': item.product.name if getattr(item, 'product', None) else 'Unknown Product',
                'quantity': quantity,
                'unit_price': unit_price,
                'total': item_total
            })

        # Extract amount tendered and change from payment note
        amount_tendered = float(invoice.total_amount or 0)
        change_given = 0.0

        if payment.note:
            # Parse payment note for amount tendered and change details
            if "Amount tendered:" in payment.note:
                try:
                    tendered_part = payment.note.split("Amount tendered:")[1].split("|")[0].strip()
                    amount_tendered = float(tendered_part)
                except:
                    pass

            if "Change due:" in payment.note:
                try:
                    change_part = payment.note.split("Change due:")[1].split("|")[0].strip()
                    change_given = float(change_part)
                except:
                    pass

        payment_dt = None
        if getattr(payment, "payment_date", None):
            try:
                payment_dt = datetime.combine(payment.payment_date, datetime.min.time())
            except TypeError:
                payment_dt = datetime.utcnow()
        else:
            payment_dt = datetime.utcnow()

        return {
            'receipt_number': receipt_number,
            'date': payment_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'time': payment_dt.strftime('%H:%M:%S'),
            'date_only': payment_dt.strftime('%Y-%m-%d'),
            # Company Information
            'company_name': app_settings.app_name if app_settings else 'Company Name',
            'company_address': app_settings.address if app_settings else '',
            'company_phone': app_settings.phone if app_settings else '',
            'company_email': app_settings.email if app_settings else '',
            'company_website': app_settings.website if app_settings else '',
            'company_vat_number': app_settings.vat_registration_number if app_settings else '',
            'company_logo_url': branch.company_logo_url if branch else '',
            # Branch Information
            'branch_name': branch.name if branch else 'Main Branch',
            'branch_address': branch.address if branch else '',
            'branch_phone': branch.phone if branch else '',
            'branch_email': branch.email if branch else '',
            'branch_vat_number': branch.vat_registration_number if branch else '',
            # Customer Information
            'customer_name': customer.name if customer else 'Walk-in Customer',
            'customer_address': customer.address if customer else '',
            'customer_phone': customer.phone if customer else '',
            'customer_email': customer.email if customer else '',
            'customer_vat_number': customer.vat_reg_number if customer else '',
            # Transaction Details
            'cashier': f"{user.first_name} {user.last_name}" if user else 'System',
            'items': items_data,
            'subtotal': subtotal,
            'vat_amount': float(getattr(invoice, 'total_vat_amount', 0) or 0),
            'total_amount': float(invoice.total_amount or 0),
            'amount_tendered': amount_tendered,
            'change_given': change_given,
            'payment_method': payment.payment_method,
            'sale_reference': invoice.invoice_number,
            'invoice_number': invoice.invoice_number,
            'payment_reference': payment.reference or '',
            # Receipt-specific fields
            'transaction_type': 'CASH SALE RECEIPT',
            'document_title': 'PAYMENT RECEIPT'
        }
