"""
PDF Report Generation Service for Accounting and Credit Notes
Handles generation of hierarchical accounting reports with parent/sub account relationships
and professional credit note documents for customer returns.
"""
import os
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.platypus.flowables import KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from sqlalchemy.orm import Session
from sqlalchemy import or_
from io import BytesIO

from app.models.accounting import AccountingCode, JournalEntry, AccountingEntry
from app.core.database import SessionLocal
from app.core.config import settings


class AccountingPDFService:
    """Service for generating PDF reports of accounting codes and transactions"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom styles for the PDF"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
            alignment=1  # Center alignment
        ))

        self.styles.add(ParagraphStyle(
            name='ParentAccount',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=15,
            textColor=colors.darkblue
        ))

        self.styles.add(ParagraphStyle(
            name='SubAccount',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceAfter=10,
            leftIndent=20,
            textColor=colors.darkgreen
        ))

        self.styles.add(ParagraphStyle(
            name='NormalIndented',
            parent=self.styles['Normal'],
            leftIndent=40
        ))

    def generate_accounting_report(self, branch_id: Optional[str] = None, start_date: Optional[date] = None,
                                  end_date: Optional[date] = None) -> str:
        """
        Generate a comprehensive PDF report of accounting codes and their transactions

        Args:
            branch_id: Optional branch filter
            start_date: Optional start date for transactions
            end_date: Optional end date for transactions

        Returns:
            Path to the generated PDF file
        """
        db = SessionLocal()

        try:
            # Get all parent accounts
            parent_accounts = db.query(AccountingCode).filter(
                AccountingCode.is_parent == True,
                AccountingCode.branch_id == branch_id if branch_id else True
            ).order_by(AccountingCode.code).all()

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"accounting_report_{timestamp}.pdf"
            filepath = os.path.join("reports", filename)

            # Ensure reports directory exists
            os.makedirs("reports", exist_ok=True)

            # Create PDF document
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            story = []

            # Add title
            title = Paragraph("Accounting Codes and Transactions Report", self.styles['CustomTitle'])
            story.append(title)
            story.append(Spacer(1, 20))

            # Add report metadata
            metadata = [
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Branch: {branch_id or 'All Branches'}",
                f"Date Range: {start_date or 'All'} to {end_date or 'All'}"
            ]

            for meta in metadata:
                story.append(Paragraph(meta, self.styles['Normal']))
            story.append(Spacer(1, 30))

            # Process each parent account
            for parent_account in parent_accounts:
                # Keep parent account and its children together
                account_section = []

                # Parent account header
                parent_title = Paragraph(
                    f"{parent_account.code} - {parent_account.name}",
                    self.styles['ParentAccount']
                )
                account_section.append(parent_title)

                # Parent account summary
                parent_summary = self._create_account_summary(parent_account)
                account_section.append(parent_summary)
                account_section.append(Spacer(1, 15))

                # Get child accounts
                child_accounts = db.query(AccountingCode).filter(
                    AccountingCode.parent_id == parent_account.id
                ).order_by(AccountingCode.code).all()

                # Process each child account
                for child_account in child_accounts:
                    # Child account header
                    child_title = Paragraph(
                        f"{child_account.code} - {child_account.name}",
                        self.styles['SubAccount']
                    )
                    account_section.append(child_title)

                    # Child account summary
                    child_summary = self._create_account_summary(child_account)
                    account_section.append(child_summary)
                    account_section.append(Spacer(1, 10))

                    # Child account transactions
                    transactions = self._get_account_transactions(
                        db, child_account.id, start_date, end_date
                    )
                    if transactions:
                        transaction_table = self._create_transaction_table(transactions)
                        account_section.append(transaction_table)
                        account_section.append(Spacer(1, 15))

                # Add the entire account section to the story
                story.append(KeepTogether(account_section))
                story.append(PageBreak())

            # Build the PDF
            doc.build(story)

            return filepath

        finally:
            db.close()

    def _create_account_summary(self, account: AccountingCode) -> Table:
        """Create a summary table for an account"""
        data = [
            ['Account Summary', ''],
            ['Code', account.code],
            ['Name', account.name],
            ['Type', account.account_type],
            ['Category', account.category],
            ['Total Debits', f"{account.total_debits or 0:.2f}"],
            ['Total Credits', f"{account.total_credits or 0:.2f}"],
            ['Balance', f"{account.balance or 0:.2f}"]
        ]

        table = Table(data, colWidths=[2*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))

        return table

    def _get_account_transactions(self, db: Session, account_id: str,
                                start_date: Optional[date] = None,
                                end_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Get transactions for a specific account within date range"""
        query = db.query(JournalEntry).filter(
            JournalEntry.accounting_code_id == account_id
        )

        if start_date:
            query = query.filter(JournalEntry.date >= start_date)
        if end_date:
            query = query.filter(JournalEntry.date <= end_date)

        transactions = query.order_by(JournalEntry.date, JournalEntry.date_posted).all()

        result = []
        for transaction in transactions:
            result.append({
                'date': transaction.date,
                'description': transaction.description or '',
                'reference': transaction.reference or '',
                'debit': transaction.debit_amount or 0,
                'credit': transaction.credit_amount or 0,
                'balance': 0  # Will be calculated
            })

        return result

    def _create_transaction_table(self, transactions: List[Dict[str, Any]]) -> Table:
        """Create a table of transactions"""
        if not transactions:
            return Paragraph("No transactions found for this account.", self.styles['NormalIndented'])

        # Calculate running balance
        running_balance = 0
        for transaction in transactions:
            if transaction['debit'] > 0:
                running_balance += transaction['debit']
            if transaction['credit'] > 0:
                running_balance -= transaction['credit']
            transaction['balance'] = running_balance

        # Create table data
        data = [['Date', 'Description', 'Reference', 'Debit', 'Credit', 'Balance']]
        for transaction in transactions:
            data.append([
                transaction['date'].strftime('%Y-%m-%d') if transaction['date'] else '',
                transaction['description'][:50] + '...' if len(transaction['description']) > 50 else transaction['description'],
                transaction['reference'][:20] + '...' if len(transaction['reference']) > 20 else transaction['reference'],
                f"{transaction['debit']:.2f}" if transaction['debit'] > 0 else '',
                f"{transaction['credit']:.2f}" if transaction['credit'] > 0 else '',
                f"{transaction['balance']:.2f}"
            ])

        # Create table
        col_widths = [1*inch, 2.5*inch, 1.5*inch, 1*inch, 1*inch, 1*inch]
        table = Table(data, colWidths=col_widths)

        # Style the table
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (5, -1), 'RIGHT'),  # Right align numeric columns
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
        ]))

        return table

    def generate_single_account_report(self, account_id: str, start_date: Optional[date] = None,
                                     end_date: Optional[date] = None) -> str:
        """
        Generate a detailed PDF report for a single accounting code

        Args:
            account_id: The accounting code ID
            start_date: Optional start date for transactions
            end_date: Optional end date for transactions

        Returns:
            Path to the generated PDF file
        """
        db = SessionLocal()

        try:
            # Get the account
            account = db.query(AccountingCode).filter(AccountingCode.id == account_id).first()
            if not account:
                raise ValueError(f"Account with ID {account_id} not found")

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"account_{account.code}_{timestamp}.pdf"
            filepath = os.path.join("reports", filename)

            # Ensure reports directory exists
            os.makedirs("reports", exist_ok=True)

            # Create PDF document
            doc = SimpleDocTemplate(filepath, pagesize=A4)
            story = []

            # Add title
            title = Paragraph(f"Account Report: {account.code} - {account.name}", self.styles['CustomTitle'])
            story.append(title)
            story.append(Spacer(1, 20))

            # Add report metadata
            metadata = [
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Account Code: {account.code}",
                f"Account Name: {account.name}",
                f"Account Type: {account.account_type}",
                f"Date Range: {start_date or 'All'} to {end_date or 'All'}"
            ]

            for meta in metadata:
                story.append(Paragraph(meta, self.styles['Normal']))
            story.append(Spacer(1, 30))

            # Account summary
            summary = self._create_account_summary(account)
            story.append(summary)
            story.append(Spacer(1, 30))

            # Get transactions
            transactions = self._get_account_transactions(db, account_id, start_date, end_date)

            if transactions:
                # Add transactions header
                story.append(Paragraph("Transaction History", self.styles['Heading2']))
                story.append(Spacer(1, 15))

                # Create transaction table
                transaction_table = self._create_transaction_table(transactions)
                story.append(transaction_table)
            else:
                story.append(Paragraph("No transactions found for the specified period.", self.styles['Normal']))

            # Build the PDF
            doc.build(story)
            return filepath

        except Exception as e:
            raise Exception(f"Error generating account report: {str(e)}")
        finally:
            db.close()
    
    def generate_credit_note_pdf(self, credit_note) -> bytes:
        """Generate PDF for credit note"""
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
            title=f"Credit Note {credit_note.credit_note_number}"
        )
        
        # Build the PDF content
        story = []
        
        # Company header
        story.extend(self._build_company_header())
        
        # Credit note title and details
        story.extend(self._build_credit_note_header(credit_note))
        
        # Customer and invoice details
        story.extend(self._build_customer_invoice_section(credit_note))
        
        # Return details
        story.extend(self._build_return_details_section(credit_note))
        
        # Credit note items table
        story.extend(self._build_items_table(credit_note))
        
        # Totals section
        story.extend(self._build_totals_section(credit_note))
        
        # Refund information
        story.extend(self._build_refund_section(credit_note))
        
        # Terms and conditions
        story.extend(self._build_terms_section())
        
        # Footer
        story.extend(self._build_footer())
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer.getvalue()
        """Generate PDF for credit note"""
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
            title=f"Credit Note {credit_note.credit_note_number}"
        )
        
        # Build the PDF content
        story = []
        
        # Company header
        story.extend(self._build_company_header())
        
        # Credit note title and details
        story.extend(self._build_credit_note_header(credit_note))
        
        # Customer and invoice details
        story.extend(self._build_customer_invoice_section(credit_note))
        
        # Return details
        story.extend(self._build_return_details_section(credit_note))
        
        # Credit note items table
        story.extend(self._build_items_table(credit_note))
        
        # Totals section
        story.extend(self._build_totals_section(credit_note))
        
        # Refund information
        story.extend(self._build_refund_section(credit_note))
        
        # Terms and conditions
        story.extend(self._build_terms_section())
        
        # Footer
        story.extend(self._build_footer())
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer.getvalue()
    
    def _build_company_header(self) -> list:
        """Build company header section"""
        elements = []
        
        # Company logo (if available)
        logo_path = getattr(settings, 'COMPANY_LOGO_PATH', None)
        if logo_path and os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=2*inch, height=1*inch)
                logo.hAlign = 'CENTER'
                elements.append(logo)
            except:
                pass  # Logo loading failed, continue without it
        
        # Company name and details
        company_name = getattr(settings, 'COMPANY_NAME', 'CN Perpetual Trading (Pty) Ltd')
        company_address = getattr(settings, 'COMPANY_ADDRESS', 
            'Plot 123, Gaborone Industrial Site<br/>P.O. Box 1234, Gaborone<br/>Botswana')
        company_details = getattr(settings, 'COMPANY_DETAILS',
            'Tel: +267 1234 567 | Email: info@cnperp.co.bw<br/>VAT: P12345678 | Company Reg: BW00123456')
        
        elements.append(Paragraph(company_name, self.styles['CustomTitle']))
        elements.append(Paragraph(company_address, self.styles['Normal']))
        elements.append(Paragraph(company_details, self.styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_credit_note_header(self, credit_note) -> list:
        """Build credit note header with number and date"""
        elements = []
        
        # Credit Note title
        title_style = ParagraphStyle(
            name='CreditNoteTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#e74c3c'),
            fontName='Helvetica-Bold'
        )
        elements.append(Paragraph("CREDIT NOTE", title_style))
        
        # Credit note details table
        data = [
            ['Credit Note Number:', credit_note.credit_note_number],
            ['Issue Date:', credit_note.issue_date.strftime('%d %B %Y')],
            ['Return Date:', credit_note.return_date.strftime('%d %B %Y')],
            ['Status:', credit_note.status.upper()]
        ]
        
        table = Table(data, colWidths=[2.5*inch, 2.5*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _build_customer_invoice_section(self, credit_note) -> list:
        """Build customer and original invoice details"""
        elements = []
        
        # Section header
        elements.append(Paragraph("Customer & Invoice Details", self.styles['ParentAccount']))
        
        # Customer details
        customer = credit_note.customer
        invoice = credit_note.original_invoice
        
        customer_data = [
            ['Customer Name:', customer.name if customer else 'N/A'],
            ['Customer ID:', customer.customer_code if customer else 'N/A'],
            ['Email:', customer.email or 'N/A'],
            ['Phone:', customer.phone or 'N/A'],
        ]
        
        # Invoice details
        invoice_data = [
            ['Original Invoice:', invoice.invoice_number if invoice else 'N/A'],
            ['Invoice Date:', invoice.invoice_date.strftime('%d %B %Y') if invoice else 'N/A'],
            ['Payment Method:', invoice.payment_method.upper() if invoice else 'N/A'],
            ['Invoice Total:', f"BWP {invoice.total_amount:,.2f}" if invoice else 'N/A'],
        ]
        
        # Create side-by-side tables
        main_data = []
        for i in range(max(len(customer_data), len(invoice_data))):
            row = []
            if i < len(customer_data):
                row.extend(customer_data[i])
            else:
                row.extend(['', ''])
            
            row.append('')  # Spacer column
            
            if i < len(invoice_data):
                row.extend(invoice_data[i])
            else:
                row.extend(['', ''])
            
            main_data.append(row)
        
        table = Table(main_data, colWidths=[1.5*inch, 2*inch, 0.3*inch, 1.5*inch, 2*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _build_return_details_section(self, credit_note) -> list:
        """Build return reason and description"""
        elements = []
        
        elements.append(Paragraph("Return Details", self.styles['ParentAccount']))
        
        # Return reason
        reason_map = {
            'faulty_product': 'Faulty Product',
            'wrong_item': 'Wrong Item Ordered',
            'damaged': 'Damaged Item',
            'customer_request': 'Customer Request',
            'duplicate_order': 'Duplicate Order',
            'quality_issue': 'Quality Issue',
            'size_issue': 'Wrong Size',
            'color_issue': 'Wrong Color',
            'other': 'Other'
        }
        
        reason_text = reason_map.get(credit_note.return_reason, credit_note.return_reason)
        
        elements.append(Paragraph(f"<b>Return Reason:</b> {reason_text}", self.styles['Normal']))
        
        if credit_note.return_description:
            elements.append(Paragraph(f"<b>Description:</b> {credit_note.return_description}", self.styles['Normal']))
        
        elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
    def _build_items_table(self, credit_note) -> list:
        """Build returned items table"""
        elements = []
        
        elements.append(Paragraph("Returned Items", self.styles['ParentAccount']))
        
        # Table headers
        headers = [
            'Item Code',
            'Description',
            'Qty Returned',
            'Unit Price',
            'Discount',
            'VAT',
            'Line Total'
        ]
        
        data = [headers]
        
        # Add items
        for item in credit_note.credit_note_items:
            product = item.product
            row = [
                product.product_code if product else 'N/A',
                product.name if product else 'Unknown Product',
                f"{item.quantity_returned:.2f}",
                f"BWP {item.unit_price:,.2f}",
                f"BWP {item.discount_amount:,.2f}",
                f"BWP {item.vat_amount:,.2f}",
                f"BWP {item.line_total:,.2f}"
            ]
            data.append(row)
            
            # Add condition and reason as sub-row
            condition_reason = f"Condition: {item.item_condition.title()}, Reason: {item.return_reason.replace('_', ' ').title()}"
            if item.description:
                condition_reason += f", Note: {item.description}"
            
            data.append(['', Paragraph(condition_reason, self.styles['Normal']), '', '', '', '', ''])
        
        # Create table
        table = Table(data, colWidths=[1*inch, 2.2*inch, 0.8*inch, 1*inch, 0.8*inch, 0.8*inch, 1*inch])
        
        # Table styling
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            
            # Data rows
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),  # Right align numbers
            ('ALIGN', (0, 1), (1, -1), 'LEFT'),    # Left align text
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#2c3e50')),
            
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _build_totals_section(self, credit_note) -> list:
        """Build totals section"""
        elements = []
        
        # Totals table (right-aligned)
        totals_data = [
            ['Subtotal:', f"BWP {credit_note.subtotal:,.2f}"],
            ['Discount:', f"BWP {credit_note.discount_amount:,.2f}"],
            ['VAT:', f"BWP {credit_note.vat_amount:,.2f}"],
            ['', ''],  # Spacer
            ['TOTAL CREDIT:', f"BWP {credit_note.total_amount:,.2f}"]
        ]
        
        totals_table = Table(totals_data, colWidths=[1.5*inch, 1.5*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (0, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -2), 10),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#2c3e50')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        # Create container table to right-align the totals
        container_data = [['', totals_table]]
        container_table = Table(container_data, colWidths=[4.5*inch, 3*inch])
        container_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(container_table)
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _build_refund_section(self, credit_note) -> list:
        """Build refund method and status section"""
        elements = []
        
        elements.append(Paragraph("Refund Information", self.styles['ParentAccount']))
        
        # Refund method mapping
        method_map = {
            'cash': 'Cash Refund',
            'bank_transfer': 'Bank Transfer',
            'credit_adjustment': 'Account Credit Adjustment',
            'store_credit': 'Store Credit'
        }
        
        status_map = {
            'pending': 'Pending Processing',
            'processed': 'Processed',
            'completed': 'Completed',
            'failed': 'Failed'
        }
        
        refund_method = method_map.get(credit_note.refund_method, credit_note.refund_method)
        refund_status = status_map.get(credit_note.refund_status, credit_note.refund_status)
        
        refund_data = [
            ['Refund Method:', refund_method],
            ['Refund Status:', refund_status],
        ]
        
        if credit_note.refund_processed_date:
            refund_data.append(['Processed Date:', credit_note.refund_processed_date.strftime('%d %B %Y')])
        
        if credit_note.refund_reference:
            refund_data.append(['Reference:', credit_note.refund_reference])
        
        refund_table = Table(refund_data, colWidths=[2*inch, 3*inch])
        refund_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(refund_table)
        elements.append(Spacer(1, 0.2*inch))
        
        return elements
    
    def _build_terms_section(self) -> list:
        """Build terms and conditions"""
        elements = []
        
        elements.append(Paragraph("Terms & Conditions", self.styles['ParentAccount']))
        
        terms = [
            "• This credit note serves as proof of return and credit issued to the customer.",
            "• Refunds will be processed using the original payment method where possible.",
            "• For cash purchases, refunds will be issued in cash or store credit at customer's choice.",
            "• Bank transfer refunds may take 3-5 business days to reflect in customer account.",
            "• This document should be retained for your records and accounting purposes.",
            "• All returns are subject to our standard return policy terms and conditions."
        ]
        
        for term in terms:
            elements.append(Paragraph(term, self.styles['Normal']))
        
        elements.append(Spacer(1, 0.3*inch))
        
        return elements
    
    def _build_footer(self) -> list:
        """Build document footer"""
        elements = []
        
        # Signature section
        sig_data = [
            ['Customer Signature:', '_' * 30, 'Date:', '_' * 15],
            ['', '', '', ''],
            ['Authorized By:', '_' * 30, 'Date:', '_' * 15]
        ]
        
        sig_table = Table(sig_data, colWidths=[1.5*inch, 2.5*inch, 0.8*inch, 1.5*inch])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        
        elements.append(sig_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Generation timestamp
        generation_time = datetime.now().strftime("%d %B %Y at %H:%M")
        elements.append(Paragraph(
            f"Generated on {generation_time} | CN Perpetual Trading ERP System",
            self.styles['Normal']
        ))
        
        return elements
    
    def generate_credit_note_html(self, credit_note) -> str:
        """Generate HTML version of credit note for web display"""
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Credit Note {credit_note_number}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .company-name {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
                .document-title {{ font-size: 28px; font-weight: bold; color: #e74c3c; margin: 20px 0; }}
                .section {{ margin: 20px 0; }}
                .section-title {{ font-size: 16px; font-weight: bold; color: #34495e; border-bottom: 2px solid #bdc3c7; padding-bottom: 5px; }}
                .details-table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                .details-table td {{ padding: 5px; border: 1px solid #bdc3c7; }}
                .details-table .label {{ font-weight: bold; background-color: #ecf0f1; width: 150px; }}
                .items-table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                .items-table th {{ background-color: #34495e; color: white; padding: 10px; text-align: center; }}
                .items-table td {{ padding: 8px; border: 1px solid #bdc3c7; text-align: right; }}
                .items-table td:first-child, .items-table td:nth-child(2) {{ text-align: left; }}
                .totals {{ float: right; margin: 20px 0; }}
                .totals table {{ border-collapse: collapse; }}
                .totals td {{ padding: 5px 15px; }}
                .total-row {{ font-weight: bold; font-size: 14px; background-color: #ecf0f1; }}
                .signature-section {{ margin-top: 50px; }}
                .footer {{ text-align: center; font-size: 12px; color: #7f8c8d; margin-top: 30px; }}
                @media print {{ body {{ margin: 0; }} }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="company-name">CN Perpetual Trading (Pty) Ltd</div>
                <div>Plot 123, Gaborone Industrial Site<br>P.O. Box 1234, Gaborone, Botswana</div>
                <div>Tel: +267 1234 567 | Email: info@cnperp.co.bw</div>
                <div class="document-title">CREDIT NOTE</div>
            </div>
            
            <div class="section">
                <table class="details-table">
                    <tr><td class="label">Credit Note Number:</td><td>{credit_note_number}</td></tr>
                    <tr><td class="label">Issue Date:</td><td>{issue_date}</td></tr>
                    <tr><td class="label">Return Date:</td><td>{return_date}</td></tr>
                    <tr><td class="label">Status:</td><td>{status}</td></tr>
                </table>
            </div>
            
            <div class="section">
                <div class="section-title">Customer & Invoice Details</div>
                <table class="details-table">
                    <tr><td class="label">Customer:</td><td>{customer_name}</td></tr>
                    <tr><td class="label">Original Invoice:</td><td>{invoice_number}</td></tr>
                    <tr><td class="label">Return Reason:</td><td>{return_reason}</td></tr>
                </table>
            </div>
            
            <div class="section">
                <div class="section-title">Returned Items</div>
                <table class="items-table">
                    <thead>
                        <tr>
                            <th>Item Code</th>
                            <th>Description</th>
                            <th>Qty</th>
                            <th>Unit Price</th>
                            <th>Discount</th>
                            <th>VAT</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_rows}
                    </tbody>
                </table>
            </div>
            
            <div class="totals">
                <table>
                    <tr><td>Subtotal:</td><td>BWP {subtotal}</td></tr>
                    <tr><td>Discount:</td><td>BWP {discount}</td></tr>
                    <tr><td>VAT:</td><td>BWP {vat}</td></tr>
                    <tr class="total-row"><td>TOTAL CREDIT:</td><td>BWP {total}</td></tr>
                </table>
            </div>
            
            <div style="clear: both;"></div>
            
            <div class="section">
                <div class="section-title">Refund Information</div>
                <table class="details-table">
                    <tr><td class="label">Refund Method:</td><td>{refund_method}</td></tr>
                    <tr><td class="label">Refund Status:</td><td>{refund_status}</td></tr>
                </table>
            </div>
            
            <div class="signature-section">
                <table style="width: 100%;">
                    <tr>
                        <td>Customer Signature: ____________________</td>
                        <td>Date: ____________________</td>
                    </tr>
                    <tr><td colspan="2" style="height: 30px;"></td></tr>
                    <tr>
                        <td>Authorized By: ____________________</td>
                        <td>Date: ____________________</td>
                    </tr>
                </table>
            </div>
            
            <div class="footer">
                Generated on {generation_time} | CN Perpetual Trading ERP System
            </div>
        </body>
        </html>
        """
        
        # Prepare items rows
        items_rows = ""
        for item in credit_note.credit_note_items:
            product = item.product
            items_rows += f"""
                <tr>
                    <td>{product.product_code if product else 'N/A'}</td>
                    <td>{product.name if product else 'Unknown Product'}</td>
                    <td>{item.quantity_returned:.2f}</td>
                    <td>BWP {item.unit_price:,.2f}</td>
                    <td>BWP {item.discount_amount:,.2f}</td>
                    <td>BWP {item.vat_amount:,.2f}</td>
                    <td>BWP {item.line_total:,.2f}</td>
                </tr>
            """
        
        # Format data
        customer = credit_note.customer
        invoice = credit_note.original_invoice
        
        return html_template.format(
            credit_note_number=credit_note.credit_note_number,
            issue_date=credit_note.issue_date.strftime('%d %B %Y'),
            return_date=credit_note.return_date.strftime('%d %B %Y'),
            status=credit_note.status.upper(),
            customer_name=customer.name if customer else 'N/A',
            invoice_number=invoice.invoice_number if invoice else 'N/A',
            return_reason=credit_note.return_reason.replace('_', ' ').title(),
            items_rows=items_rows,
            subtotal=f"{credit_note.subtotal:,.2f}",
            discount=f"{credit_note.discount_amount:,.2f}",
            vat=f"{credit_note.vat_amount:,.2f}",
            total=f"{credit_note.total_amount:,.2f}",
            refund_method=credit_note.refund_method.replace('_', ' ').title(),
            refund_status=credit_note.refund_status.title(),
            generation_time=datetime.now().strftime("%d %B %Y at %H:%M")
        )

    def generate_cash_equivalents_report(self, db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None) -> bytes:
        """
        Generate a comprehensive PDF report for Cash and Cash Equivalents (code 1110) 
        including all parent and sub-accounts.
        """
        # Get the Cash and Cash Equivalents parent account (1110)
        cash_parent = db.query(AccountingCode).filter(
            AccountingCode.code == "1110"
        ).first()
        
        if not cash_parent:
            raise ValueError("Cash and Cash Equivalents account (1110) not found")
        
        # Get all sub-accounts under 1110
        cash_accounts = db.query(AccountingCode).filter(
            or_(
                AccountingCode.code == "1110",
                AccountingCode.parent_code == "1110"
            )
        ).order_by(AccountingCode.code).all()
        
        # Create PDF document
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.darkblue,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.darkgreen,
            spaceAfter=20
        )
        
        # Title
        title = Paragraph("Cash and Cash Equivalents Transaction History", title_style)
        story.append(title)
        
        # Date range info
        if start_date and end_date:
            date_range = f"Period: {start_date.strftime('%d %B %Y')} to {end_date.strftime('%d %B %Y')}"
        elif start_date:
            date_range = f"From: {start_date.strftime('%d %B %Y')}"
        elif end_date:
            date_range = f"Until: {end_date.strftime('%d %B %Y')}"
        else:
            date_range = "All Transactions"
        
        date_para = Paragraph(date_range, styles['Normal'])
        story.append(date_para)
        story.append(Spacer(1, 20))
        
        # Summary section
        summary_heading = Paragraph("Account Summary", heading_style)
        story.append(summary_heading)
        
        # Create summary table
        summary_data = [['Account Code', 'Account Name', 'Current Balance']]
        total_balance = Decimal('0')
        
        for account in cash_accounts:
            # Calculate balance for this account
            entries_query = db.query(JournalEntry).filter(
                JournalEntry.account_code == account.code
            )
            
            if start_date:
                entries_query = entries_query.filter(JournalEntry.transaction_date >= start_date)
            if end_date:
                entries_query = entries_query.filter(JournalEntry.transaction_date <= end_date)
            
            entries = entries_query.all()
            balance = sum(entry.debit_amount - entry.credit_amount for entry in entries)
            total_balance += balance
            
            summary_data.append([
                account.code,
                account.name,
                f"BWP {balance:,.2f}"
            ])
        
        # Add total row
        summary_data.append(['', 'TOTAL CASH & EQUIVALENTS', f"BWP {total_balance:,.2f}"])
        
        summary_table = Table(summary_data, colWidths=[2*inch, 3*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (-1, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (-1, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 30))
        
        # Detailed transactions for each account
        for account in cash_accounts:
            account_heading = Paragraph(f"Account: {account.code} - {account.name}", heading_style)
            story.append(account_heading)
            
            # Get transactions for this account
            entries_query = db.query(JournalEntry).filter(
                JournalEntry.account_code == account.code
            )
            
            if start_date:
                entries_query = entries_query.filter(JournalEntry.transaction_date >= start_date)
            if end_date:
                entries_query = entries_query.filter(JournalEntry.transaction_date <= end_date)
            
            entries = entries_query.order_by(JournalEntry.transaction_date.desc()).all()
            
            if not entries:
                no_trans = Paragraph("No transactions found for this period.", styles['Normal'])
                story.append(no_trans)
                story.append(Spacer(1, 20))
                continue
            
            # Create transaction table
            transaction_data = [['Date', 'Reference', 'Description', 'Debit', 'Credit', 'Balance']]
            running_balance = Decimal('0')
            
            # Calculate starting balance if start_date is specified
            if start_date:
                prev_entries = db.query(JournalEntry).filter(
                    JournalEntry.account_code == account.code,
                    JournalEntry.transaction_date < start_date
                ).all()
                running_balance = sum(entry.debit_amount - entry.credit_amount for entry in prev_entries)
            
            for entry in reversed(entries):  # Process in chronological order for balance calculation
                running_balance += entry.debit_amount - entry.credit_amount
                
                transaction_data.append([
                    entry.transaction_date.strftime('%d/%m/%Y'),
                    entry.reference or '',
                    entry.description or '',
                    f"BWP {entry.debit_amount:,.2f}" if entry.debit_amount > 0 else '',
                    f"BWP {entry.credit_amount:,.2f}" if entry.credit_amount > 0 else '',
                    f"BWP {running_balance:,.2f}"
                ])
            
            # Reverse back to show most recent first
            transaction_data[1:] = list(reversed(transaction_data[1:]))
            
            transaction_table = Table(transaction_data, colWidths=[1*inch, 1.2*inch, 2*inch, 1*inch, 1*inch, 1*inch])
            transaction_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            story.append(transaction_table)
            story.append(Spacer(1, 20))
        
        # Footer with generation time
        footer = Paragraph(
            f"Report generated on {datetime.now().strftime('%d %B %Y at %H:%M')}",
            styles['Normal']
        )
        story.append(Spacer(1, 20))
        story.append(footer)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def generate_financial_statement_pdf(self, statement_type: str, data: Dict[str, Any], 
                                       company_info: Optional[Dict[str, str]] = None) -> bytes:
        """
        Generate PDF for various financial statements
        
        Args:
            statement_type: Type of statement (balance_sheet, income_statement, cash_flow, etc.)
            data: Financial statement data
            company_info: Optional company information
            
        Returns:
            PDF content as bytes
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm,
            title=f"{statement_type.replace('_', ' ').title()}"
        )
        
        story = []
        
        # Add company header if provided
        if company_info:
            story.extend(self._build_company_header_financial(company_info))
        
        # Generate content based on statement type
        if statement_type == 'balance_sheet':
            story.extend(self._build_balance_sheet_content(data))
        elif statement_type == 'income_statement':
            story.extend(self._build_income_statement_content(data))
        elif statement_type == 'cash_flow':
            story.extend(self._build_cash_flow_content(data))
        elif statement_type == 'changes_in_equity':
            story.extend(self._build_changes_in_equity_content(data))
        elif statement_type == 'trial_balance':
            story.extend(self._build_trial_balance_content(data))
        elif statement_type == 'financial_summary':
            story.extend(self._build_financial_summary_content(data))
        elif statement_type == 'complete_package':
            story.extend(self._build_complete_package_content(data))
        else:
            raise ValueError(f"Unsupported statement type: {statement_type}")
        
        # Add footer
        story.extend(self._build_financial_footer(data))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def _build_company_header_financial(self, company_info: Dict[str, str]) -> List:
        """Build company header for financial statements"""
        story = []
        
        # Company name
        company_name = company_info.get('name', 'Company Name')
        story.append(Paragraph(company_name, self.styles['CustomTitle']))
        
        # Company address
        address = company_info.get('address', '')
        if address:
            story.append(Paragraph(address, self.styles['Normal']))
        
        story.append(Spacer(1, 20))
        return story

    def _build_balance_sheet_content(self, data: Dict[str, Any]) -> List:
        """Build balance sheet PDF content"""
        story = []
        report_data = data.get('report', data)
        
        # Title
        title = "BALANCE SHEET"
        as_of_date = data.get('as_of_date', datetime.now().strftime('%B %d, %Y'))
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Paragraph(f"As of {as_of_date}", self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Assets section
        if 'assets' in report_data:
            story.append(Paragraph("ASSETS", self.styles['ParentAccount']))
            story.extend(self._build_financial_section(report_data['assets']))
            story.append(Spacer(1, 15))
        
        # Liabilities section
        if 'liabilities' in report_data:
            story.append(Paragraph("LIABILITIES", self.styles['ParentAccount']))
            story.extend(self._build_financial_section(report_data['liabilities']))
            story.append(Spacer(1, 15))
        
        # Equity section
        if 'equity' in report_data:
            story.append(Paragraph("EQUITY", self.styles['ParentAccount']))
            story.extend(self._build_financial_section(report_data['equity']))
        
        return story

    def _build_income_statement_content(self, data: Dict[str, Any]) -> List:
        """Build income statement PDF content"""
        story = []
        report_data = data.get('report', data)
        
        # Title
        title = "INCOME STATEMENT"
        period = data.get('period', 'Current Period')
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Paragraph(f"For the period: {period}", self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Build sections
        if 'sections' in report_data:
            for section in report_data['sections']:
                story.append(Paragraph(section['name'].upper(), self.styles['ParentAccount']))
                story.extend(self._build_financial_section(section))
                story.append(Spacer(1, 10))
        
        # Net income
        net_income = report_data.get('net_income', 0)
        story.append(Spacer(1, 10))
        story.append(Paragraph("NET INCOME", self.styles['ParentAccount']))
        story.append(Paragraph(f"${net_income:,.2f}", self.styles['Normal']))
        
        return story

    def _build_cash_flow_content(self, data: Dict[str, Any]) -> List:
        """Build cash flow statement PDF content"""
        story = []
        report_data = data.get('report', data)
        
        # Title
        title = "CASH FLOW STATEMENT"
        period = data.get('period', 'Current Period')
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Paragraph(f"For the period: {period}", self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Build sections
        if 'sections' in report_data:
            for section in report_data['sections']:
                story.append(Paragraph(section['name'].upper(), self.styles['ParentAccount']))
                story.extend(self._build_financial_section(section))
                story.append(Spacer(1, 15))
        
        # Net cash flow
        net_cash_flow = report_data.get('net_cash_flow', 0)
        story.append(Spacer(1, 10))
        story.append(Paragraph("NET CASH FLOW", self.styles['ParentAccount']))
        story.append(Paragraph(f"${net_cash_flow:,.2f}", self.styles['Normal']))
        
        return story

    def _build_changes_in_equity_content(self, data: Dict[str, Any]) -> List:
        """Build statement of changes in equity PDF content"""
        story = []
        report_data = data.get('report', data)
        
        # Title
        title = "STATEMENT OF CHANGES IN EQUITY"
        period = data.get('period', 'Current Period')
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Paragraph(f"For the period: {period}", self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Build equity components table
        if 'equity_components' in report_data:
            table_data = [
                ['Component', 'Beginning Balance', 'Net Income', 'Other Comprehensive Income', 
                 'Dividends', 'Share Transactions', 'Ending Balance']
            ]
            
            for component in report_data['equity_components']:
                table_data.append([
                    component.get('component', ''),
                    f"${component.get('beginning_balance', 0):,.2f}",
                    f"${component.get('net_income', 0):,.2f}",
                    f"${component.get('other_comprehensive_income', 0):,.2f}",
                    f"${component.get('dividends', 0):,.2f}",
                    f"${component.get('share_transactions', 0):,.2f}",
                    f"${component.get('ending_balance', 0):,.2f}"
                ])
            
            table = Table(table_data, colWidths=[2.5*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
        
        return story

    def _build_trial_balance_content(self, data: Dict[str, Any]) -> List:
        """Build trial balance PDF content"""
        story = []
        report_data = data.get('report', data)
        
        # Title
        title = "TRIAL BALANCE"
        as_of_date = data.get('as_of_date', datetime.now().strftime('%B %d, %Y'))
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Paragraph(f"As of {as_of_date}", self.styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Build trial balance table
        if 'trial_balance' in report_data:
            table_data = [['Account Code', 'Account Name', 'Debit Balance', 'Credit Balance', 'Account Type']]
            
            total_debits = 0
            total_credits = 0
            
            for account in report_data['trial_balance']:
                debit_balance = account.get('debit_balance', 0)
                credit_balance = account.get('credit_balance', 0)
                total_debits += debit_balance
                total_credits += credit_balance
                
                table_data.append([
                    account.get('code', ''),
                    account.get('name', ''),
                    f"${debit_balance:,.2f}" if debit_balance else '',
                    f"${credit_balance:,.2f}" if credit_balance else '',
                    account.get('account_type', '')
                ])
            
            # Add totals row
            table_data.append([
                '', 'TOTALS', f"${total_debits:,.2f}", f"${total_credits:,.2f}", ''
            ])
            
            table = Table(table_data, colWidths=[2*cm, 4*cm, 2.5*cm, 2.5*cm, 2*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(table)
        
        return story

    def _build_financial_summary_content(self, data: Dict[str, Any]) -> List:
        """Build financial summary PDF content"""
        story = []
        report_data = data.get('report', data)
        
        # Title
        title = "FINANCIAL SUMMARY"
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Key metrics
        metrics = [
            ('Total Assets', report_data.get('total_assets', 0)),
            ('Total Liabilities', report_data.get('total_liabilities', 0)),
            ('Total Equity', report_data.get('total_equity', 0)),
            ('Net Income', report_data.get('net_income', 0))
        ]
        
        for metric_name, value in metrics:
            story.append(Paragraph(f"{metric_name}: ${value:,.2f}", self.styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        # Financial ratios
        if 'financial_ratios' in report_data:
            story.append(Paragraph("FINANCIAL RATIOS", self.styles['ParentAccount']))
            for ratio_name, ratio_value in report_data['financial_ratios'].items():
                display_name = ratio_name.replace('_', ' ').title()
                if isinstance(ratio_value, (int, float)):
                    story.append(Paragraph(f"{display_name}: {ratio_value:.2f}", self.styles['Normal']))
                else:
                    story.append(Paragraph(f"{display_name}: {ratio_value}", self.styles['Normal']))
        
        return story

    def _build_complete_package_content(self, data: Dict[str, Any]) -> List:
        """Build complete financial package PDF content"""
        story = []
        report_data = data.get('report', data)
        
        # Title
        title = "COMPLETE FINANCIAL STATEMENTS PACKAGE"
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Balance Sheet Summary
        if 'balance_sheet' in report_data:
            story.append(Paragraph("BALANCE SHEET SUMMARY", self.styles['ParentAccount']))
            story.extend(self._build_balance_sheet_content({'report': report_data['balance_sheet']}))
            story.append(PageBreak())
        
        # Income Statement Summary
        if 'income_statement' in report_data:
            story.append(Paragraph("INCOME STATEMENT SUMMARY", self.styles['ParentAccount']))
            story.extend(self._build_income_statement_content({'report': report_data['income_statement']}))
            story.append(PageBreak())
        
        # Cash Flow Summary
        if 'cash_flow_statement' in report_data:
            story.append(Paragraph("CASH FLOW STATEMENT SUMMARY", self.styles['ParentAccount']))
            story.extend(self._build_cash_flow_content({'report': report_data['cash_flow_statement']}))
            story.append(PageBreak())
        
        # Changes in Equity Summary
        if 'changes_in_equity' in report_data:
            story.append(Paragraph("STATEMENT OF CHANGES IN EQUITY", self.styles['ParentAccount']))
            story.extend(self._build_changes_in_equity_content({'report': report_data['changes_in_equity']}))
        
        return story

    def _build_financial_section(self, section_data: Dict[str, Any]) -> List:
        """Build a financial statement section"""
        story = []
        
        if 'sections' in section_data:
            # Handle nested sections
            for subsection in section_data['sections']:
                story.append(Paragraph(subsection['name'], self.styles['SubAccount']))
                if 'line_items' in subsection:
                    for item in subsection['line_items']:
                        story.append(Paragraph(
                            f"{item['name']}: ${item['amount']:,.2f}", 
                            self.styles['NormalIndented']
                        ))
                story.append(Paragraph(
                    f"Total {subsection['name']}: ${subsection.get('total', 0):,.2f}", 
                    self.styles['SubAccount']
                ))
                story.append(Spacer(1, 5))
        elif 'line_items' in section_data:
            # Handle direct line items
            for item in section_data['line_items']:
                story.append(Paragraph(
                    f"{item['name']}: ${item['amount']:,.2f}", 
                    self.styles['NormalIndented']
                ))
        
        # Add section total
        if 'total' in section_data:
            story.append(Paragraph(
                f"Total: ${section_data['total']:,.2f}", 
                self.styles['ParentAccount']
            ))
        
        return story

    def _build_financial_footer(self, data: Dict[str, Any]) -> List:
        """Build footer for financial statements"""
        story = []
        
        story.append(Spacer(1, 30))
        
        # IFRS compliance note
        ifrs_standards = data.get('ifrs_standards_applied', [])
        if ifrs_standards:
            story.append(Paragraph("IFRS Standards Applied:", self.styles['Normal']))
            for standard in ifrs_standards:
                story.append(Paragraph(f"• {standard}", self.styles['NormalIndented']))
            story.append(Spacer(1, 10))
        
        # Generation timestamp
        timestamp = data.get('generated_at', datetime.now().isoformat())
        story.append(Paragraph(
            f"Report generated on {timestamp}", 
            self.styles['Normal']
        ))
        
        return story


# Create an alias for backward compatibility and credit notes functionality
PDFService = AccountingPDFService
