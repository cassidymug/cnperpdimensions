"""
Universal Document Printing Service

This service handles printing for ALL documents except:
1. Invoices (handled by InvoiceService with invoice printer settings)
2. POS receipts (handled by PosReceiptService with POS receipt settings)

ALL OTHER DOCUMENTS are printed on A4 plain paper regardless of any printer settings.
This includes: Reports, Statements, Quotes, Purchase Orders, Banking Documents, etc.
"""

import logging
import os
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from app.models.app_setting import AppSetting


class DocumentPrintingService:
    """
    Universal service for printing all documents except invoices and POS receipts
    
    SCOPE:
    - Reports (Trial Balance, Balance Sheet, P&L, etc.)
    - Statements (Customer statements, Bank statements)
    - Quotes (Sales quotes, Purchase quotes)
    - Purchase Orders
    - Banking Documents (Reconciliations, Transfers)
    - VAT Returns
    - Management Reports
    - All other business documents
    
    PRINTING RULE:
    - Always A4 size (210 × 297 mm)
    - Always plain paper
    - Always PDF format
    - Printer settings DO NOT affect these documents
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.app_settings = self._load_app_settings()

    def _load_app_settings(self) -> Dict:
        """Load essential app settings for document headers"""
        defaults = {
            "company_name": "Company Name",
            "company_address": "",
            "company_phone": "",
            "company_email": "",
            "tax_number": "",
            "currency_symbol": "P",
            "currency_code": "BWP",
            "company_logo_url": "",
            "quotation_title": "QUOTATION",
            "quotation_show_logo": True,
            "quotation_logo_url": "",
            "quotation_logo_width_mm": 60,
            "quotation_logo_height_mm": 25,
            "quotation_footer_text": "",
            "quotation_footer_images": [],
        }

        if not self.db:
            return defaults

        settings = defaults.copy()
        try:
            instance = AppSetting.get_instance(self.db)
            if instance:
                settings.update(
                    {
                        "company_name": getattr(instance, "company_name", settings["company_name"]) or settings["company_name"],
                        "company_address": getattr(instance, "address", settings["company_address"]) or settings["company_address"],
                        "company_phone": getattr(instance, "phone", settings["company_phone"]) or settings["company_phone"],
                        "company_email": getattr(instance, "email", settings["company_email"]) or settings["company_email"],
                        "tax_number": getattr(instance, "vat_registration_number", settings["tax_number"]) or settings["tax_number"],
                        "currency_symbol": getattr(instance, "currency", None) and AppSetting.get_currency_symbol(getattr(instance, "currency")) or settings["currency_symbol"],
                        "currency_code": getattr(instance, "currency", settings["currency_code"]) or settings["currency_code"],
                        "company_logo_url": getattr(instance, "company_logo_url", settings["company_logo_url"]) or settings["company_logo_url"],
                    }
                )

                try:
                    quotation_meta = instance.quotation_settings
                except AttributeError:
                    quotation_meta = getattr(instance, "quotation_settings_defaults", {}) or {}

                footer_images_setting = quotation_meta.get(
                    "footer_images", settings["quotation_footer_images"]
                )

                settings.update(
                    {
                        "quotation_title": quotation_meta.get("title", settings["quotation_title"]),
                        "quotation_show_logo": quotation_meta.get("show_logo", settings["quotation_show_logo"]),
                        "quotation_logo_url": quotation_meta.get("logo_url")
                        or settings["quotation_logo_url"]
                        or settings["company_logo_url"],
                        "quotation_logo_width_mm": quotation_meta.get("logo_width_mm", settings["quotation_logo_width_mm"]),
                        "quotation_logo_height_mm": quotation_meta.get("logo_height_mm", settings["quotation_logo_height_mm"]),
                        "quotation_footer_text": quotation_meta.get("footer_text", settings["quotation_footer_text"]),
                        "quotation_footer_images": footer_images_setting,
                        "quotation_show_banking_details": quotation_meta.get("show_banking_details", True),
                        "quotation_bank_name": quotation_meta.get("bank_name", ""),
                        "quotation_bank_account_name": quotation_meta.get("bank_account_name", ""),
                        "quotation_bank_account_number": quotation_meta.get("bank_account_number", ""),
                        "quotation_bank_branch": quotation_meta.get("bank_branch", ""),
                        "quotation_bank_swift_code": quotation_meta.get("bank_swift_code", ""),
                    }
                )
        except Exception as ex:
            logging.getLogger(__name__).warning(
                "DocumentPrintingService: failed to load structured app settings: %s", ex
            )

        return settings

    def generate_document_pdf(self, document_type: str, document_id: str, 
                            title: str = None, content_data: Dict = None) -> Tuple[str, bytes, str]:
        """
        Generate any document as A4 PDF (ALWAYS plain paper, NEVER affected by printer settings)
        
        Args:
            document_type: Type of document (report, statement, quote, purchase_order, etc.)
            document_id: ID of the document
            title: Optional custom title
            content_data: Optional data for document content
            
        Returns:
            Tuple of (format_type, content_bytes, filename)
        """
        
        # Generate PDF based on document type
        if document_type == 'trial_balance':
            pdf_buffer = self._generate_trial_balance_pdf(document_id, content_data)
        elif document_type == 'balance_sheet':
            pdf_buffer = self._generate_balance_sheet_pdf(document_id, content_data)
        elif document_type == 'income_statement':
            pdf_buffer = self._generate_income_statement_pdf(document_id, content_data)
        elif document_type == 'customer_statement':
            pdf_buffer = self._generate_customer_statement_pdf(document_id, content_data)
        elif document_type == 'purchase_order':
            pdf_buffer = self._generate_purchase_order_pdf(document_id, content_data)
        elif document_type == 'quote':
            pdf_buffer = self._generate_quote_pdf(document_id, content_data)
        elif document_type == 'bank_reconciliation':
            pdf_buffer = self._generate_bank_reconciliation_pdf(document_id, content_data)
        elif document_type == 'vat_return':
            pdf_buffer = self._generate_vat_return_pdf(document_id, content_data)
        else:
            # Generic document
            pdf_buffer = self._generate_generic_document_pdf(document_type, document_id, title, content_data)
        
        content = pdf_buffer.read()
        
        # Generate filename
        doc_title = title or document_type.replace('_', ' ').title()
        filename = f"{doc_title}_{document_id}.pdf"
        
        return ('pdf', content, filename)

    def _generate_standard_pdf_header(self, doc: canvas.Canvas, title: str, 
                                    document_id: str = None, date: datetime = None):
        """Generate standard header for all documents (A4 plain paper format)"""
        
        # Company info header
        company_name = self.app_settings.get('company_name', 'Company Name')
        company_address = self.app_settings.get('company_address', '')
        company_phone = self.app_settings.get('company_phone', '')
        company_email = self.app_settings.get('company_email', '')
        tax_number = self.app_settings.get('tax_number', '')
        
        # Header section
        y_pos = 800
        
        # Company name (large, bold)
        doc.setFont("Helvetica-Bold", 16)
        doc.drawString(50, y_pos, company_name)
        
        y_pos -= 20
        doc.setFont("Helvetica", 10)
        
        # Company details
        if company_address:
            doc.drawString(50, y_pos, company_address)
            y_pos -= 12
        
        contact_line = []
        if company_phone:
            contact_line.append(f"Tel: {company_phone}")
        if company_email:
            contact_line.append(f"Email: {company_email}")
        
        if contact_line:
            doc.drawString(50, y_pos, " | ".join(contact_line))
            y_pos -= 12
        
        if tax_number:
            doc.drawString(50, y_pos, f"Tax Number: {tax_number}")
            y_pos -= 12
        
        # Document title (centered, large)
        y_pos -= 20
        doc.setFont("Helvetica-Bold", 14)
        title_width = doc.stringWidth(title, "Helvetica-Bold", 14)
        doc.drawString((A4[0] - title_width) / 2, y_pos, title)
        
        # Document info (right side)
        y_pos -= 30
        doc.setFont("Helvetica", 10)
        
        if document_id:
            doc.drawRightString(A4[0] - 50, y_pos, f"Document ID: {document_id}")
            y_pos -= 12
        
        doc.drawRightString(A4[0] - 50, y_pos, f"Generated: {(date or datetime.now()).strftime('%d/%m/%Y %H:%M')}")
        y_pos -= 12
        
        # Note about printing
        doc.setFont("Helvetica", 8)
        doc.setFillColor(colors.grey)
        doc.drawRightString(A4[0] - 50, y_pos, "Printed on A4 plain paper")
        doc.setFillColor(colors.black)
        
        # Horizontal line
        y_pos -= 10
        doc.line(50, y_pos, A4[0] - 50, y_pos)
        
        return y_pos - 20  # Return next available y position

    def _generate_trial_balance_pdf(self, report_id: str, data: Dict) -> BytesIO:
        """Generate Trial Balance report as A4 PDF"""
        buffer = BytesIO()
        doc = canvas.Canvas(buffer, pagesize=A4)
        
        y_pos = self._generate_standard_pdf_header(doc, "Trial Balance", report_id)
        
        # TODO: Add actual trial balance content from data
        doc.setFont("Helvetica", 10)
        doc.drawString(50, y_pos, "Trial Balance content will be implemented here")
        doc.drawString(50, y_pos - 15, "This report is always printed on A4 plain paper")
        doc.drawString(50, y_pos - 30, "Printer settings do not affect this document")
        
        doc.save()
        buffer.seek(0)
        return buffer

    def _generate_balance_sheet_pdf(self, report_id: str, data: Dict) -> BytesIO:
        """Generate Balance Sheet as A4 PDF"""
        buffer = BytesIO()
        doc = canvas.Canvas(buffer, pagesize=A4)
        
        y_pos = self._generate_standard_pdf_header(doc, "Balance Sheet", report_id)
        
        # TODO: Add actual balance sheet content from data
        doc.setFont("Helvetica", 10)
        doc.drawString(50, y_pos, "Balance Sheet content will be implemented here")
        doc.drawString(50, y_pos - 15, "This report is always printed on A4 plain paper")
        
        doc.save()
        buffer.seek(0)
        return buffer

    def _generate_income_statement_pdf(self, report_id: str, data: Dict) -> BytesIO:
        """Generate Income Statement as A4 PDF"""
        buffer = BytesIO()
        doc = canvas.Canvas(buffer, pagesize=A4)
        
        y_pos = self._generate_standard_pdf_header(doc, "Income Statement", report_id)
        
        # TODO: Add actual income statement content from data
        doc.setFont("Helvetica", 10)
        doc.drawString(50, y_pos, "Income Statement content will be implemented here")
        doc.drawString(50, y_pos - 15, "This report is always printed on A4 plain paper")
        
        doc.save()
        buffer.seek(0)
        return buffer

    def _generate_customer_statement_pdf(self, statement_id: str, data: Dict) -> BytesIO:
        """Generate Customer Statement as A4 PDF"""
        buffer = BytesIO()
        doc = canvas.Canvas(buffer, pagesize=A4)
        
        y_pos = self._generate_standard_pdf_header(doc, "Customer Statement", statement_id)
        
        # TODO: Add actual customer statement content from data
        doc.setFont("Helvetica", 10)
        doc.drawString(50, y_pos, "Customer Statement content will be implemented here")
        doc.drawString(50, y_pos - 15, "This statement is always printed on A4 plain paper")
        
        doc.save()
        buffer.seek(0)
        return buffer

    def _generate_purchase_order_pdf(self, po_id: str, data: Dict) -> BytesIO:
        """Generate Purchase Order as A4 PDF"""
        buffer = BytesIO()
        doc = canvas.Canvas(buffer, pagesize=A4)
        
        y_pos = self._generate_standard_pdf_header(doc, "Purchase Order", po_id)
        
        # TODO: Add actual purchase order content from data
        doc.setFont("Helvetica", 10)
        doc.drawString(50, y_pos, "Purchase Order content will be implemented here")
        doc.drawString(50, y_pos - 15, "This document is always printed on A4 plain paper")
        
        doc.save()
        buffer.seek(0)
        return buffer

    def _format_currency(self, amount: float) -> str:
        try:
            value = float(amount or 0)
        except (TypeError, ValueError):
            value = 0.0
        symbol = self.app_settings.get("currency_symbol", "P")
        return f"{symbol}{value:,.2f}"

    def _resolve_image_path(self, path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        if path.startswith("http://") or path.startswith("https://"):
            # ReportLab can't fetch remote URLs directly; skip gracefully
            return None
        candidate = path
        if not os.path.isabs(candidate):
            candidate = os.path.join(os.getcwd(), path.lstrip("/"))
            if not os.path.exists(candidate):
                candidate = os.path.join(os.getcwd(), "app", path.lstrip("/"))
        return candidate if os.path.exists(candidate) else None

    def _generate_quote_pdf(self, quote_id: str, data: Dict) -> BytesIO:
        """Generate Quotation PDF using modern invoice-style layout"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        story: List = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "QuotationTitle",
            parent=styles["Heading1"],
            fontSize=24,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#2c3e50"),
            spaceAfter=18,
        )

        header_style = ParagraphStyle(
            "SectionHeader",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=colors.HexColor("#34495e"),
            spaceAfter=10,
        )

        # Logo
        if self.app_settings.get("quotation_show_logo"):
            logo_path = self._resolve_image_path(
                self.app_settings.get("quotation_logo_url")
            )
            if logo_path:
                logo = Image(
                    logo_path,
                    width=self.app_settings.get("quotation_logo_width_mm", 60) * mm,
                    height=self.app_settings.get("quotation_logo_height_mm", 25) * mm,
                    kind="proportional",
                )
                story.append(logo)
                story.append(Spacer(1, 12))

        # Company info
        company_lines = [f"<b>{self.app_settings['company_name']}</b>"]
        if self.app_settings.get("company_address"):
            company_lines.append(self.app_settings["company_address"])
        contact_bits = []
        if self.app_settings.get("company_phone"):
            contact_bits.append(f"Phone: {self.app_settings['company_phone']}")
        if self.app_settings.get("company_email"):
            contact_bits.append(f"Email: {self.app_settings['company_email']}")
        if contact_bits:
            company_lines.append(" | ".join(contact_bits))
        if self.app_settings.get("tax_number"):
            company_lines.append(f"Tax Number: {self.app_settings['tax_number']}")

        story.append(Paragraph("<br/>".join(company_lines), styles["Normal"]))
        story.append(Spacer(1, 16))

        # Title
        story.append(Paragraph(self.app_settings.get("quotation_title", "QUOTATION"), title_style))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#3498db")))
        story.append(Spacer(1, 18))

        # Quotation details
        date_value = (data or {}).get("date")
        if isinstance(date_value, datetime):
            date_str = date_value.strftime("%d/%m/%Y")
        else:
            date_str = str(date_value or "-")

        valid_until_value = (data or {}).get("valid_until")
        if isinstance(valid_until_value, datetime):
            valid_str = valid_until_value.strftime("%d/%m/%Y")
        else:
            valid_str = str(valid_until_value or "-")

        quote_details = [
            [
                "Quotation #:",
                (data or {}).get("quote_number") or quote_id,
                "Status:",
                (data or {}).get("status", "draft").title(),
            ],
            [
                "Date:",
                date_str,
                "Valid Until:",
                valid_str,
            ],
        ]

        details_table = Table(quote_details, colWidths=[30 * mm, 50 * mm, 30 * mm, 40 * mm])
        details_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("ALIGN", (3, 0), (3, -1), "LEFT"),
                ]
            )
        )
        story.append(details_table)
        story.append(Spacer(1, 16))

        # Customer details
        story.append(Paragraph("Customer", header_style))
        customer_lines = []
        customer_name = (data or {}).get("customer_name") or (data or {}).get("customer_id")
        if customer_name:
            customer_lines.append(f"<b>{customer_name}</b>")
        customer_contact = (data or {}).get("customer_contact")
        if isinstance(customer_contact, dict):
            if customer_contact.get("phone"):
                customer_lines.append(f"Phone: {customer_contact['phone']}")
            if customer_contact.get("email"):
                customer_lines.append(f"Email: {customer_contact['email']}")
            if customer_contact.get("address"):
                customer_lines.append(customer_contact["address"])

        story.append(
            Paragraph("<br/>".join(customer_lines) if customer_lines else "", styles["Normal"])
        )
        story.append(Spacer(1, 16))

        # Items table
        story.append(Paragraph("Quotation Items", header_style))

        table_headers = [
            "Description",
            "Quantity",
            "Unit Price",
            "Discount %",
            "Line Total",
        ]
        table_data: List = [table_headers]
        subtotal = 0.0
        
        # Create a style for table cell text with wrapping
        cell_style = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontSize=9,
            leading=11,
            wordWrap='CJK',
        )
        
        for item in (data or {}).get("items", []):
            qty = float(item.get("quantity") or 0)
            price = float(item.get("price") or 0)
            discount_pct = float(item.get("discount") or 0)
            line_total = qty * price * (1 - discount_pct / 100)
            subtotal += line_total

            # Wrap description in Paragraph for proper text wrapping
            description = str(item.get("product_name") or item.get("product_id") or "-")
            description_para = Paragraph(description, cell_style)
            
            table_data.append(
                [
                    description_para,
                    f"{qty:,.2f}",
                    self._format_currency(price),
                    f"{discount_pct:,.2f}",
                    self._format_currency(line_total),
                ]
            )

        items_table = Table(
            table_data,
            colWidths=[85 * mm, 15 * mm, 25 * mm, 20 * mm, 28 * mm],
            repeatRows=1,
        )
        items_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3498db")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                    ("ALIGN", (0, 1), (0, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d0d7de")),
                    ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#95a5a6")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f8f9fa")],
                    ),
                ]
            )
        )
        story.append(items_table)
        story.append(Spacer(1, 16))

        # Totals
        vat_amount = float((data or {}).get("vat") or (data or {}).get("vat_amount") or 0)
        total_amount = float((data or {}).get("total") or (subtotal + vat_amount))

        totals_data = [
            ["Subtotal", self._format_currency(subtotal)],
            ["VAT", self._format_currency(vat_amount)],
            ["Total", self._format_currency(total_amount)],
        ]
        totals_table = Table(totals_data, colWidths=[40 * mm, 35 * mm], hAlign="RIGHT")
        totals_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                    ("FONTSIZE", (0, 0), (-1, -2), 10),
                    ("FONTSIZE", (0, -1), (-1, -1), 12),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ecf0f1")),
                    ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(totals_table)
        story.append(Spacer(1, 20))

        # Notes
        notes = (data or {}).get("notes")
        if notes:
            story.append(Paragraph("Notes", header_style))
            story.append(Paragraph(str(notes), styles["Normal"]))
            story.append(Spacer(1, 16))

        # Banking Details
        if self.app_settings.get("quotation_show_banking_details"):
            bank_name = self.app_settings.get("quotation_bank_name", "")
            bank_account_name = self.app_settings.get("quotation_bank_account_name", "")
            bank_account_number = self.app_settings.get("quotation_bank_account_number", "")
            bank_branch = self.app_settings.get("quotation_bank_branch", "")
            bank_swift = self.app_settings.get("quotation_bank_swift_code", "")

            # Only show banking section if at least one field has data
            if any([bank_name, bank_account_name, bank_account_number, bank_branch, bank_swift]):
                story.append(Paragraph("Banking Details", header_style))
                
                banking_lines = []
                if bank_name:
                    banking_lines.append(f"<b>Bank:</b> {bank_name}")
                if bank_account_name:
                    banking_lines.append(f"<b>Account Name:</b> {bank_account_name}")
                if bank_account_number:
                    banking_lines.append(f"<b>Account Number:</b> {bank_account_number}")
                if bank_branch:
                    banking_lines.append(f"<b>Branch:</b> {bank_branch}")
                if bank_swift:
                    banking_lines.append(f"<b>SWIFT/BIC Code:</b> {bank_swift}")
                
                banking_para = Paragraph("<br/>".join(banking_lines), styles["Normal"])
                story.append(banking_para)
                story.append(Spacer(1, 16))

        # Footer text
        footer_text = self.app_settings.get("quotation_footer_text")
        if footer_text:
            footer_para = Paragraph(
                footer_text,
                ParagraphStyle("Footer", parent=styles["Normal"], alignment=TA_CENTER),
            )
            story.append(footer_para)
            story.append(Spacer(1, 12))

        # Footer images (e.g., signatures, seals, promotional banners)
        footer_images: List[str] = self.app_settings.get("quotation_footer_images", [])
        image_flowables: List[Image] = []
        for img_path in footer_images:
            resolved = self._resolve_image_path(img_path)
            if not resolved:
                continue
            image_flowables.append(Image(resolved, width=50 * mm, height=20 * mm, kind="proportional"))

        if image_flowables:
            footer_table = Table([image_flowables], hAlign="CENTER")
            footer_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
            story.append(footer_table)

        doc.build(story)
        buffer.seek(0)
        return buffer

    def _generate_bank_reconciliation_pdf(self, reconciliation_id: str, data: Dict) -> BytesIO:
        """Generate Bank Reconciliation as A4 PDF"""
        buffer = BytesIO()
        doc = canvas.Canvas(buffer, pagesize=A4)
        
        y_pos = self._generate_standard_pdf_header(doc, "Bank Reconciliation", reconciliation_id)
        
        # TODO: Add actual reconciliation content from data
        doc.setFont("Helvetica", 10)
        doc.drawString(50, y_pos, "Bank Reconciliation content will be implemented here")
        doc.drawString(50, y_pos - 15, "This report is always printed on A4 plain paper")
        
        doc.save()
        buffer.seek(0)
        return buffer

    def _generate_vat_return_pdf(self, return_id: str, data: Dict) -> BytesIO:
        """Generate VAT Return as A4 PDF"""
        buffer = BytesIO()
        doc = canvas.Canvas(buffer, pagesize=A4)
        
        y_pos = self._generate_standard_pdf_header(doc, "VAT Return", return_id)
        
        # TODO: Add actual VAT return content from data
        doc.setFont("Helvetica", 10)
        doc.drawString(50, y_pos, "VAT Return content will be implemented here")
        doc.drawString(50, y_pos - 15, "This return is always printed on A4 plain paper")
        
        doc.save()
        buffer.seek(0)
        return buffer

    def _generate_generic_document_pdf(self, doc_type: str, doc_id: str, 
                                     title: str = None, data: Dict = None) -> BytesIO:
        """Generate generic document as A4 PDF"""
        buffer = BytesIO()
        doc = canvas.Canvas(buffer, pagesize=A4)
        
        document_title = title or doc_type.replace('_', ' ').title()
        y_pos = self._generate_standard_pdf_header(doc, document_title, doc_id)
        
        # Generic content
        doc.setFont("Helvetica", 10)
        doc.drawString(50, y_pos, f"{document_title} content")
        doc.drawString(50, y_pos - 15, f"Document Type: {doc_type}")
        doc.drawString(50, y_pos - 30, f"Document ID: {doc_id}")
        doc.drawString(50, y_pos - 50, "This document is always printed on A4 plain paper")
        doc.drawString(50, y_pos - 65, "Printer settings do not affect this document type")
        
        # Add data if provided
        if data:
            y_pos -= 100
            doc.drawString(50, y_pos, "Document Data:")
            y_pos -= 15
            
            for key, value in data.items():
                if y_pos < 100:  # Start new page if needed
                    doc.showPage()
                    y_pos = 800
                
                doc.drawString(70, y_pos, f"{key}: {value}")
                y_pos -= 12
        
        doc.save()
        buffer.seek(0)
        return buffer

    def is_printer_settings_applicable(self, document_type: str) -> bool:
        """
        Check if printer settings apply to this document type
        
        Returns:
            False - Printer settings NEVER apply to documents handled by this service
                   These documents are ALWAYS printed on A4 plain paper
        """
        return False

    def get_supported_document_types(self) -> list:
        """Get list of document types supported by this service"""
        return [
            'trial_balance', 'balance_sheet', 'income_statement',
            'customer_statement', 'supplier_statement', 'purchase_order',
            'quote', 'bank_reconciliation', 'vat_return',
            'aging_report', 'cash_flow', 'budget_report',
            'management_report', 'audit_trail'
        ]

    def get_printing_info(self) -> Dict:
        """Get information about how documents are printed"""
        return {
            "paper_size": "A4 (210 × 297 mm)",
            "paper_type": "Plain paper",
            "format": "PDF",
            "printer_settings_applicable": False,
            "note": "These documents are always printed on A4 plain paper regardless of any printer settings configured in the system."
        }
