"""
Credit Note API Endpoints

Provides REST API for credit note management including creation, approval,
refund processing, and printing functionality.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import date, datetime
from decimal import Decimal

from app.core.database import get_db
# from app.core.security import get_current_user  # Removed for development
from app.models.credit_notes import CreditNote, CreditNoteItem, RefundTransaction
from app.services.credit_note_service import CreditNoteService
from app.services.pdf_service import PDFService
from app.utils.logger import get_logger, log_exception, log_error_with_context
# from app.core.exceptions import ValidationError, BusinessLogicError  # Not available - using HTTPException
from app.schemas.credit_notes import (
    CreditNoteCreate, CreditNoteResponse, CreditNoteItemResponse,
    RefundTransactionCreate, RefundTransactionResponse,
    CreditNoteSummary, CreditNoteStatusUpdate
)

logger = get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=CreditNoteResponse)
def create_credit_note(
    credit_note_data: CreditNoteCreate,
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_user)  # Removed for development
):
    """Create a new credit note for customer returns (supports both invoices and POS receipts)"""
    try:
        service = CreditNoteService(db)

        # Determine source type and create appropriate credit note
        if credit_note_data.source_type == "invoice":
            credit_note = service.create_credit_note_from_invoice(
                invoice_id=credit_note_data.source_id,
                return_items=[ item.model_dump() for item in credit_note_data.return_items],
                return_reason=credit_note_data.return_reason,
                return_description=credit_note_data.return_description,
                refund_method=credit_note_data.refund_method,
                user_id=None,  # None for development - will be replaced with current_user.id in production
                cost_center_id=credit_note_data.cost_center_id,
                project_id=credit_note_data.project_id
            )
        elif credit_note_data.source_type == "pos_receipt":
            credit_note = service.create_credit_note_from_sale(
                sale_id=credit_note_data.source_id,
                return_items=[item.model_dump() for item in credit_note_data.return_items],
                return_reason=credit_note_data.return_reason,
                return_description=credit_note_data.return_description,
                refund_method=credit_note_data.refund_method,
                user_id=None,  # None for development - will be replaced with current_user.id in production
                cost_center_id=credit_note_data.cost_center_id,
                project_id=credit_note_data.project_id
            )
        else:
            raise HTTPException(status_code=400, detail=f"Invalid source_type: {credit_note_data.source_type}")

        return credit_note
    except Exception as e:
        if "validation" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=f"Error creating credit note: {str(e)}")


@router.get("/{credit_note_id}", response_model=CreditNoteResponse)
def get_credit_note(
    credit_note_id: str,
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_user)  # Removed for development
):
    """Get credit note by ID"""
    service = CreditNoteService(db)
    credit_note = service.get_credit_note_by_id(credit_note_id)

    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")

    # Populate receipt_number for POS sales if needed
    if credit_note.original_sale and not hasattr(credit_note.original_sale, 'receipt_number'):
        receipt_number = credit_note.original_sale.reference if credit_note.original_sale.reference else f"RCT-{credit_note.original_sale.id[:8].upper()}"
        # Add as a computed attribute for serialization
        credit_note.original_sale.receipt_number = receipt_number

    return credit_note


@router.post("/{credit_note_id}/approve")
def approve_credit_note(
    credit_note_id: str,
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_user)  # Removed for development
):
    """Approve a credit note and create accounting entries"""
    try:
        service = CreditNoteService(db)
        credit_note = service.approve_credit_note(credit_note_id, None)  # None for development
        return {"message": f"Credit note {credit_note.credit_note_number} approved successfully"}
    except Exception as e:
        if "validation" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=f"Error approving credit note: {str(e)}")


@router.post("/{credit_note_id}/process-refund", response_model=RefundTransactionResponse)
def process_refund(
    credit_note_id: str,
    refund_data: RefundTransactionCreate,
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_user)  # Removed for development
):
    """Process refund payment for an approved credit note"""
    try:
        service = CreditNoteService(db)
        refund_transaction = service.process_refund(
            credit_note_id=credit_note_id,
            refund_details=refund_data.dict(),
            user_id=None  # None for development
        )
        return refund_transaction
    except Exception as e:
        if "validation" in str(e).lower():
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=500, detail=f"Error processing refund: {str(e)}")


@router.get("/customer/{customer_id}", response_model=List[CreditNoteSummary])
def get_customer_credit_notes(
    customer_id: str,
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_user)  # Removed for development
):
    """Get all credit notes for a specific customer"""
    service = CreditNoteService(db)
    credit_notes = service.get_customer_credit_notes(customer_id)
    return credit_notes


@router.get("/invoices/available", response_model=List[Dict[str, Any]])
def get_available_invoices_for_credit_notes(
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    days: int = Query(90, description="Number of days to look back"),
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_user)  # Removed for development
):
    """
    Get invoices available for creating credit notes
    Returns invoices from the last N days that can be returned
    """
    from app.models.sales import Invoice
    from datetime import date, timedelta

    cutoff_date = date.today() - timedelta(days=days)

    query = db.query(Invoice).filter(
        Invoice.status.in_(['paid', 'partial', 'unpaid']),  # Exclude cancelled/draft
        Invoice.date >= cutoff_date
    )

    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id)

    invoices = query.order_by(Invoice.date.desc()).limit(100).all()

    result = []
    for invoice in invoices:
        result.append({
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,  # Human-readable invoice number
            "date": invoice.date.isoformat() if invoice.date else None,
            "customer_id": invoice.customer_id,
            "customer_name": invoice.customer.name if invoice.customer else "Unknown",
            "total_amount": float(invoice.total_amount) if invoice.total_amount else 0.0,
            "status": invoice.status,
            "payment_method": getattr(invoice, 'payment_method', 'credit')
        })

    return result


@router.get("/sales/available", response_model=List[Dict[str, Any]])
def get_available_sales_for_credit_notes(
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    days: int = Query(90, description="Number of days to look back"),
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_user)  # Removed for development
):
    """
    Get POS sales/receipts available for creating credit notes
    Returns sales from the last N days that can be returned
    """
    from app.models.sales import Sale
    from datetime import datetime, timedelta

    cutoff_date = datetime.now() - timedelta(days=days)

    query = db.query(Sale).filter(
        Sale.status == 'completed',
        Sale.date >= cutoff_date
    )

    if customer_id:
        query = query.filter(Sale.customer_id == customer_id)

    sales = query.order_by(Sale.date.desc()).limit(100).all()

    result = []
    for sale in sales:
        # Generate a human-readable receipt number
        receipt_number = sale.reference if sale.reference else f"RCT-{sale.id[:8].upper()}"

        result.append({
            "id": sale.id,
            "receipt_number": receipt_number,  # Human-readable receipt number
            "date": sale.date.isoformat() if sale.date else None,
            "customer_id": sale.customer_id,
            "customer_name": sale.customer.name if sale.customer else "Walk-in Customer",
            "total_amount": float(sale.total_amount) if sale.total_amount else 0.0,
            "payment_method": sale.payment_method,
            "reference": sale.reference,
            "status": sale.status
        })

    return result


@router.get("/", response_model=List[CreditNoteSummary])
def list_credit_notes(
    status: Optional[str] = Query(None, description="Filter by status"),
    refund_status: Optional[str] = Query(None, description="Filter by refund status"),
    date_from: Optional[date] = Query(None, description="Filter from date"),
    date_to: Optional[date] = Query(None, description="Filter to date"),
    customer_id: Optional[str] = Query(None, description="Filter by customer"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_user)  # Removed for development
):
    """List credit notes with filtering options"""
    from app.models.sales import Sale, Invoice

    query = db.query(CreditNote)

    # Apply filters
    if status:
        query = query.filter(CreditNote.status == status)

    if refund_status:
        query = query.filter(CreditNote.refund_status == refund_status)

    if date_from:
        query = query.filter(CreditNote.issue_date >= date_from)

    if date_to:
        query = query.filter(CreditNote.issue_date <= date_to)

    if customer_id:
        query = query.filter(CreditNote.customer_id == customer_id)

    # Apply pagination
    credit_notes = query.offset(offset).limit(limit).all()

    # Enrich with source document numbers
    result = []
    for cn in credit_notes:
        # Get source document number based on type
        source_doc_number = None
        if cn.source_type == 'invoice' and cn.original_invoice_id:
            invoice = db.query(Invoice).filter(Invoice.id == cn.original_invoice_id).first()
            if invoice:
                source_doc_number = invoice.invoice_number
        elif cn.source_type == 'pos_receipt' and cn.original_sale_id:
            sale = db.query(Sale).filter(Sale.id == cn.original_sale_id).first()
            if sale:
                source_doc_number = sale.reference if sale.reference else f"RCT-{sale.id[:8].upper()}"

        result.append({
            "id": cn.id,
            "credit_note_number": cn.credit_note_number,
            "issue_date": cn.issue_date,
            "source_type": cn.source_type,
            "source_document_number": source_doc_number,
            "customer_name": cn.customer.name if cn.customer else "Unknown",
            "total_amount": cn.total_amount,
            "refund_method": cn.refund_method,
            "refund_status": cn.refund_status,
            "status": cn.status,
            "return_reason": cn.return_reason
        })

    return result


@router.get("/pending-refunds", response_model=List[CreditNoteSummary])
def get_pending_refunds(
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_user)  # Removed for development
):
    """Get credit notes with pending refunds"""
    from app.models.sales import Sale, Invoice

    service = CreditNoteService(db)
    credit_notes = service.get_pending_refunds()

    # Enrich with source document numbers
    result = []
    for cn in credit_notes:
        # Get source document number based on type
        source_doc_number = None
        if cn.source_type == 'invoice' and cn.original_invoice_id:
            invoice = db.query(Invoice).filter(Invoice.id == cn.original_invoice_id).first()
            if invoice:
                source_doc_number = invoice.invoice_number
        elif cn.source_type == 'pos_receipt' and cn.original_sale_id:
            sale = db.query(Sale).filter(Sale.id == cn.original_sale_id).first()
            if sale:
                source_doc_number = sale.reference if sale.reference else f"RCT-{sale.id[:8].upper()}"

        result.append({
            "id": cn.id,
            "credit_note_number": cn.credit_note_number,
            "issue_date": cn.issue_date,
            "source_type": cn.source_type,
            "source_document_number": source_doc_number,
            "customer_name": cn.customer.name if cn.customer else "Unknown",
            "total_amount": cn.total_amount,
            "refund_method": cn.refund_method,
            "refund_status": cn.refund_status,
            "status": cn.status,
            "return_reason": cn.return_reason
        })

    return result


@router.get("/{credit_note_id}/print")
def print_credit_note(
    credit_note_id: str,
    format: str = Query("pdf", pattern="^(pdf|html)$"),
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_user)  # Removed for development
):
    """Generate printable credit note"""
    service = CreditNoteService(db)
    credit_note = service.get_credit_note_by_id(credit_note_id)

    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")

    try:
        pdf_service = PDFService()

        if format == "pdf":
            # Generate PDF
            pdf_content = pdf_service.generate_credit_note_pdf(credit_note)
            return Response(
                content=pdf_content,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=credit_note_{credit_note.credit_note_number}.pdf"
                }
            )
        else:
            # Generate HTML
            html_content = pdf_service.generate_credit_note_html(credit_note)
            return Response(
                content=html_content,
                media_type="text/html"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating credit note: {str(e)}")


@router.patch("/{credit_note_id}/status", response_model=CreditNoteResponse)
def update_credit_note_status(
    credit_note_id: str,
    status_update: CreditNoteStatusUpdate,
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_user)  # Removed for development
):
    """Update credit note status"""
    credit_note = db.query(CreditNote).filter(CreditNote.id == credit_note_id).first()

    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")

    # Validate status transition
    valid_transitions = {
        'draft': ['issued', 'cancelled'],
        'issued': ['processed', 'cancelled'],
        'processed': ['cancelled'],
        'cancelled': []
    }

    if status_update.status not in valid_transitions.get(credit_note.status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status transition from {credit_note.status} to {status_update.status}"
        )

    credit_note.status = status_update.status
    credit_note.updated_at = datetime.now()

    if status_update.notes:
        credit_note.notes = status_update.notes

    db.commit()

    return credit_note


@router.delete("/{credit_note_id}")
def cancel_credit_note(
    credit_note_id: str,
    reason: str = Query(..., description="Reason for cancellation"),
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_user)  # Removed for development
):
    """Cancel a credit note (only if in draft status)"""
    credit_note = db.query(CreditNote).filter(CreditNote.id == credit_note_id).first()

    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")

    if credit_note.status != 'draft':
        raise HTTPException(
            status_code=400,
            detail="Only draft credit notes can be cancelled"
        )

    credit_note.status = 'cancelled'
    credit_note.notes = f"Cancelled: {reason}"
    credit_note.updated_at = datetime.now()

    db.commit()

    return {"message": f"Credit note {credit_note.credit_note_number} cancelled successfully"}


@router.get("/{credit_note_id}/refund-transactions", response_model=List[RefundTransactionResponse])
def get_refund_transactions(
    credit_note_id: str,
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_user)  # Removed for development
):
    """Get all refund transactions for a credit note"""
    credit_note = db.query(CreditNote).filter(CreditNote.id == credit_note_id).first()

    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")

    refund_transactions = db.query(RefundTransaction).filter(
        RefundTransaction.credit_note_id == credit_note_id
    ).all()

    return refund_transactions


@router.post("/{credit_note_id}/email")
def email_credit_note(
    credit_note_id: str,
    email_address: str = Query(..., description="Email address to send to"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
    # current_user: User = Depends(get_current_user)  # Removed for development
):
    """Email credit note to customer"""
    service = CreditNoteService(db)
    credit_note = service.get_credit_note_by_id(credit_note_id)

    if not credit_note:
        raise HTTPException(status_code=404, detail="Credit note not found")

    # Add background task to send email
    background_tasks.add_task(
        send_credit_note_email,
        credit_note=credit_note,
        email_address=email_address,
        current_user="dev-user"  # Hardcoded for development
    )

    return {"message": f"Credit note {credit_note.credit_note_number} will be sent to {email_address}"}


def send_credit_note_email(credit_note: CreditNote, email_address: str, current_user):
    """Background task to send credit note email"""
    try:
        # from app.services.email_service import EmailService  # Not available yet
        from app.services.pdf_service import PDFService
        pdf_service = PDFService()
        # email_service = EmailService()  # Not available yet

        # Generate PDF
        pdf_content = pdf_service.generate_credit_note_pdf(credit_note)

        # TODO: Send email when EmailService is implemented
        # email_service.send_credit_note_email(
        #     credit_note=credit_note,
        #     pdf_attachment=pdf_content,
        #     recipient_email=email_address,
        #     sender_user=current_user
        # )

        print(f"Email would be sent to {email_address} with credit note {credit_note.credit_note_number}")

    except Exception as e:
        print(f"Error sending credit note email: {str(e)}")
        # In production, you'd want to log this properly and potentially notify the user
