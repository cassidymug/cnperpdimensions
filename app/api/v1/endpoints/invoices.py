"""
Invoice Management API Endpoints

This module provides comprehensive invoice management including creation,
PDF generation, WhatsApp/email delivery, and accounting integration.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from decimal import Decimal
import io
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

from app.core.database import get_db
from app.services.invoice_service import InvoiceService
from app.services.invoice_reversal_service import InvoiceReversalService
from app.services.whatsapp_service import WhatsAppService
from app.services.dot_matrix_invoice_service import DotMatrixInvoiceService
from app.models.sales import Invoice, InvoiceItem, Payment as PaymentModel
from app.models.credit_notes import CreditNote
from app.models.app_setting import AppSetting  # needed for template lookup

router = APIRouter()


class InvoiceItemCreate(BaseModel):
    """Invoice item creation schema"""
    product_id: str
    quantity: int = Field(..., gt=0)
    unit_price: Optional[Decimal] = None
    price: Optional[Decimal] = None  # Added for backward compatibility
    discount_percentage: Optional[float] = Field(0.0, ge=0, le=100)
    vat_rate: Optional[float] = None
    description: Optional[str] = None

    @field_validator('price')
    @classmethod
    def validate_price_fields(cls, v, info):
        if hasattr(info, 'data'):
            unit_price = info.data.get('unit_price')
            if not v and not unit_price:
                raise ValueError('Either price or unit_price must be provided')
        return v


class CustomerCreate(BaseModel):
    """New customer creation schema"""
    name: str = Field(..., min_length=1, max_length=200)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=100)
    vat_reg_number: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None


class CashPayment(BaseModel):
    """Cash payment details for immediate payment"""
    payment_method: str = Field(..., description="Payment method: cash, card, mobile_money, bank_transfer, cheque")
    payment_reference: Optional[str] = Field(None, max_length=100, description="Transaction ID, receipt number, etc.")
    payment_date: date = Field(..., description="Date of payment")
    amount_tendered: Optional[Decimal] = Field(None, description="Amount given by customer")
    change_due: Optional[Decimal] = Field(None, description="Change to be given to customer")


class InvoiceCreate(BaseModel):
    """Invoice creation schema"""
    customer_id: Optional[str] = None
    new_customer_data: Optional[CustomerCreate] = None
    branch_id: str
    invoice_items: List[InvoiceItemCreate]
    due_date: Optional[date] = None
    payment_terms: int = Field(30, ge=0)
    discount_percentage: float = Field(0.0, ge=0, le=100)
    notes: Optional[str] = ""
    is_cash_sale: bool = Field(False, description="Whether this is a cash sale with immediate payment")
    cash_payment: Optional[CashPayment] = None

    @field_validator('customer_id')
    @classmethod
    def validate_customer_data(cls, v, info):
        # Temporarily disabled - moving validation to endpoint
        return v

    @field_validator('cash_payment')
    @classmethod
    def validate_cash_payment(cls, v, info):
        if hasattr(info, 'data'):
            is_cash_sale = info.data.get('is_cash_sale', False)
            if is_cash_sale and not v:
                raise ValueError('cash_payment is required for cash sales')
            if not is_cash_sale and v:
                raise ValueError('cash_payment should only be provided for cash sales')
        return v


class InvoiceItemResponse(BaseModel):
    """Invoice item response schema"""
    id: str
    product_id: str
    product_name: str
    quantity: int
    unit_price: Decimal
    discount_percentage: float
    vat_rate: float
    subtotal: Decimal
    discount_amount: Decimal
    vat_amount: Decimal
    total_amount: Decimal
    description: Optional[str] = ""


class InvoiceResponse(BaseModel):
    """Invoice response schema"""
    id: str
    invoice_number: str
    customer_id: str
    customer_name: str
    branch_id: Optional[str] = None  # Made optional
    invoice_date: date
    due_date: date
    status: str
    subtotal: Decimal
    discount_amount: Decimal
    total_vat_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    payment_terms: int
    notes: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_by_name: Optional[str] = None
    updated_by: Optional[str] = None
    updated_by_name: Optional[str] = None
    invoice_items: List[InvoiceItemResponse]
    # Optional auto-print metadata
    auto_print: Optional[bool] = False
    print_format: Optional[str] = None
    print_content_b64: Optional[str] = None
    print_filename: Optional[str] = None
    # Optional receipt information for cash sales
    receipt_generated: Optional[bool] = False
    receipt_number: Optional[str] = None
    # Optional designer layout metadata
    designer_layout: Optional[List[Dict[str, Any]]] = None
    designer_form_data: Optional[Dict[str, Any]] = None
    designer_metadata: Optional[Dict[str, Any]] = None
    designer_version: Optional[int] = None
    designer_updated_at: Optional[str] = None


class InvoiceListResponse(BaseModel):
    """Invoice list item response schema"""
    id: str
    invoice_number: str
    customer_name: str
    invoice_date: date
    due_date: date
    status: str
    total_amount: Decimal
    amount_due: Decimal
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class PaymentRequest(BaseModel):
    """Payment request schema"""
    amount: Decimal = Field(..., gt=0)
    payment_date: Optional[date] = None
    payment_method: Optional[str] = Field("cash")
    reference: Optional[str] = None
    note: Optional[str] = None


class WhatsAppSendRequest(BaseModel):
    """WhatsApp send request schema"""
    phone_number: str
    include_pdf: bool = True


class DotMatrixPrintRequest(BaseModel):
    """Dot matrix print request schema"""
    paper_width: int = Field(80, description="Paper width in characters (80 or 136)")
    form_length: int = Field(66, description="Form length in lines")
    compressed: bool = Field(False, description="Use compressed printing (17 CPI)")
    carbon_copies: int = Field(1, description="Number of copies to print")
    template: Optional[str] = Field(None, description="Custom template name")


class DotMatrixTemplate(BaseModel):
    """Dot matrix template schema"""
    name: str
    content: str
    settings: Dict[str, Any]


class InvoiceUpdate(BaseModel):
    """Invoice update schema"""
    due_date: Optional[date] = None
    payment_terms: Optional[int] = Field(None, ge=0)
    discount_percentage: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = None
    status: Optional[str] = None


class AuditEntry(BaseModel):
    """Simple audit log entry"""
    id: str
    invoice_id: str
    action: str
    field: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: Optional[str] = None
    changed_by_name: Optional[str] = None
    timestamp: datetime


@router.post("/", response_model=InvoiceResponse)
async def create_invoice(
    invoice_data: InvoiceCreate,
    created_by: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Create a new tax invoice with optional new customer creation and cash payment processing"""
    invoice_service = InvoiceService(db)
    
    # Validate customer data requirements
    print(f"[DEBUG] Endpoint - customer_id: {invoice_data.customer_id}")
    print(f"[DEBUG] Endpoint - new_customer_data: {invoice_data.new_customer_data}")
    
    if not invoice_data.customer_id and not invoice_data.new_customer_data:
        raise HTTPException(
            status_code=422,
            detail="Either customer_id or new_customer_data must be provided"
        )
    
    if invoice_data.customer_id and invoice_data.new_customer_data:
        raise HTTPException(
            status_code=422, 
            detail="Cannot provide both customer_id and new_customer_data"
        )
    
    try:
        # Handle customer creation or validation
        customer_id = invoice_data.customer_id
        
        if invoice_data.new_customer_data:
            # Create new customer
            from app.models.sales import Customer
            import uuid
            
            new_customer = Customer(
                id=str(uuid.uuid4()),
                name=invoice_data.new_customer_data.name,
                phone=invoice_data.new_customer_data.phone,
                email=invoice_data.new_customer_data.email,
                vat_reg_number=invoice_data.new_customer_data.vat_reg_number,
                address=invoice_data.new_customer_data.address,
                branch_id=invoice_data.branch_id,
                customer_type="retail" if invoice_data.is_cash_sale else "credit",
                payment_terms=0 if invoice_data.is_cash_sale else 30,
                active=True
            )
            
            db.add(new_customer)
            db.flush()  # Get the customer ID
            customer_id = new_customer.id
        
        # Validate existing customer if provided
        elif customer_id:
            from app.models.sales import Customer
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                raise HTTPException(status_code=400, detail="Customer not found")
        
        # Enforce credit limit for non-cash invoices
        # Fetch customer record to check credit_limit
        from app.models.sales import Customer as CustModel
        cust = db.query(CustModel).filter(CustModel.id == customer_id).first()
        if not invoice_data.is_cash_sale and (cust.credit_limit is None or cust.credit_limit <= 0):
            raise HTTPException(status_code=400, detail=f"Customer '{cust.name}' has insufficient credit limit")
        # Convert invoice items to dict format
        items_data = []
        for item in invoice_data.invoice_items:
            item_dict = {
                'product_id': item.product_id,
                'quantity': item.quantity,
                'discount_percentage': item.discount_percentage or 0.0,
                'description': item.description
            }
            if item.price is not None:
                item_dict['unit_price'] = float(item.price)
            if item.vat_rate is not None:
                item_dict['vat_rate'] = item.vat_rate
            
            items_data.append(item_dict)
        
        # Create invoice
        invoice = invoice_service.create_invoice(
            customer_id=customer_id,
            branch_id=invoice_data.branch_id,
            invoice_items=items_data,
            due_date=invoice_data.due_date,
            payment_terms=invoice_data.payment_terms,
            discount_percentage=invoice_data.discount_percentage,
            notes=invoice_data.notes,
            created_by=created_by
        )
        
        # Handle cash sale payment
        if invoice_data.is_cash_sale and invoice_data.cash_payment:
            from app.models.sales import Payment
            import uuid
            
            # Get amount tendered and change details
            amount_tendered = invoice_data.cash_payment.amount_tendered or invoice.total_amount
            change_due = invoice_data.cash_payment.change_due or Decimal('0.00')
            
            # Validate amount tendered for cash payments
            if invoice_data.cash_payment.payment_method == 'cash' and amount_tendered < invoice.total_amount:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Amount tendered ({amount_tendered}) cannot be less than total amount ({invoice.total_amount})"
                )
            
            # Create payment record with extended details
            payment_note = f"Cash sale payment - {invoice_data.cash_payment.payment_method}"
            if amount_tendered and amount_tendered != invoice.total_amount:
                payment_note += f" | Amount tendered: {amount_tendered}"
            if change_due and change_due > 0:
                payment_note += f" | Change due: {change_due}"
            
            payment = Payment(
                id=str(uuid.uuid4()),
                invoice_id=invoice.id,
                customer_id=customer_id,
                amount=invoice.total_amount,
                payment_date=invoice_data.cash_payment.payment_date,
                payment_method=invoice_data.cash_payment.payment_method,
                reference=invoice_data.cash_payment.payment_reference,
                note=payment_note,
                payment_status="completed",
                created_by=created_by
            )
            
            db.add(payment)
            
            # Update invoice status and amounts
            invoice.status = "paid"
            invoice.amount_paid = invoice.total_amount
            invoice.amount_due = 0
            invoice.paid_at = datetime.now()
            
            # Create accounting entries for the payment
            try:
                from app.services.accounting_service import AccountingService
                accounting_service = AccountingService(db)
                accounting_service.record_payment(payment)
            except Exception as acc_err:
                print(f"[ACCOUNTING_WARN] Payment accounting entry failed: {acc_err}")
            
            # Generate receipt for cash sale
            try:
                from app.services.receipt_service import ReceiptService
                receipt_service = ReceiptService(db)
                receipt_result = receipt_service.generate_invoice_receipt(
                    invoice_id=invoice.id,
                    payment_id=payment.id,
                    user_id=created_by
                )
                if receipt_result.get('success'):
                    # Store receipt info for response
                    invoice.receipt_generated = True
                    invoice.receipt_number = receipt_result.get('receipt_number')
                    print(f"[RECEIPT_SUCCESS] Generated receipt {receipt_result.get('receipt_number')} for invoice {invoice.invoice_number}")
                else:
                    print(f"[RECEIPT_WARN] Failed to generate receipt: {receipt_result.get('error')}")
            except Exception as receipt_err:
                print(f"[RECEIPT_WARN] Receipt generation failed: {receipt_err}")
        
        db.commit()

        resp = _format_invoice_response(invoice, invoice_service.invoice_designer_config)

        # Auto print logic (derive from settings)
        try:
            printer_settings = invoice_service.get_printer_settings()
            if str(printer_settings.get('auto_print', 'false')).lower() == 'true':
                fmt, content, filename = invoice_service.generate_invoice_by_printer_type(invoice.id)
                import base64
                resp.auto_print = True
                resp.print_format = fmt
                resp.print_content_b64 = base64.b64encode(content).decode('utf-8')
                resp.print_filename = filename
        except Exception as ap_err:
            print(f"[AUTO_PRINT_WARN] {ap_err}")

        return resp
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[InvoiceListResponse])
async def get_invoices(
    branch_id: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get filtered list of invoices"""
    invoice_service = InvoiceService(db)
    
    invoices = invoice_service.get_invoice_list(
        branch_id=branch_id,
        customer_id=customer_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset
    )
    
    return [_format_invoice_list_response(invoice) for invoice in invoices]


@router.get("/statistics/summary")
async def get_invoice_statistics(
    branch_id: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    # Reuse earlier statistics block (kept for compatibility); simple aggregation
    from sqlalchemy import func
    query = db.query(Invoice)
    if branch_id:
        query = query.filter(Invoice.branch_id == branch_id)
    if date_from:
        query = query.filter(Invoice.date >= date_from)
    if date_to:
        query = query.filter(Invoice.date <= date_to)
    total_invoices = query.count()
    total_amount = query.with_entities(func.sum(Invoice.total_amount)).scalar() or 0
    total_paid = query.with_entities(func.sum(Invoice.amount_paid)).scalar() or 0
    total_outstanding = total_amount - total_paid
    status_counts = db.query(
        Invoice.status,
        func.count(Invoice.id).label('count'),
        func.sum(Invoice.total_amount).label('total_amount')
    ).group_by(Invoice.status).all()
    return {
        'total_invoices': total_invoices,
        'total_amount': float(total_amount),
        'total_paid': float(total_paid),
        'total_outstanding': float(total_outstanding),
        'status_breakdown': [
            {'status': s, 'count': c, 'total_amount': float(a or 0)} for s, c, a in status_counts
        ]
    }

@router.get("/settings")
async def get_invoice_settings(db: Session = Depends(get_db)):
    """Return current effective invoice-related settings (prefix, numbering, auto flags, currency)."""
    service = InvoiceService(db)
    # Provide only relevant subset
    subset_keys = [
        'invoice_prefix','invoice_start_number','auto_generate_invoices','currency','currency_symbol','default_vat_rate','auto_print'
    ]
    settings_data = {k: service.app_settings.get(k) for k in subset_keys}
    return {'success': True, 'settings': settings_data}

@router.post("/settings/auto-print")
async def set_auto_print(
    enabled: bool = Query(..., description="Enable or disable automatic printing on invoice creation"),
    db: Session = Depends(get_db)
):
    """Toggle auto_print setting (persists in AppSetting)."""
    setting = db.query(AppSetting).filter(AppSetting.key == 'auto_print').first()
    if setting:
        setting.value = 'true' if enabled else 'false'
    else:
        new_setting = AppSetting(key='auto_print', value='true' if enabled else 'false', description='Auto print invoices when created')
        db.add(new_setting)
    db.commit()
    return {'success': True, 'auto_print': enabled}

@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    invoice_service = InvoiceService(db)
    return _format_invoice_response(invoice, invoice_service.invoice_designer_config)


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: str,
    download: bool = Query(False, description="Download as attachment"),
    db: Session = Depends(get_db)
):
    """Generate and return invoice PDF"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice_service = InvoiceService(db)
    
    try:
        pdf_buffer = invoice_service.generate_pdf_invoice(invoice_id)
        
        headers = {
            'Content-Type': 'application/pdf',
        }
        
        if download:
            headers['Content-Disposition'] = f'attachment; filename="Invoice_{invoice.invoice_number}.pdf"'
        else:
            headers['Content-Disposition'] = f'inline; filename="Invoice_{invoice.invoice_number}.pdf"'
        
        return StreamingResponse(
            io.BytesIO(pdf_buffer.read()),
            media_type='application/pdf',
            headers=headers
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


@router.post("/{invoice_id}/send-whatsapp")
async def send_invoice_whatsapp(
    invoice_id: str,
    request: WhatsAppSendRequest,
    db: Session = Depends(get_db)
):
    """Send invoice via WhatsApp"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice_service = InvoiceService(db)
    whatsapp_service = WhatsAppService(db)
    
    try:
        # Prepare invoice data for WhatsApp
        invoice_data = {
            'invoice_number': invoice.invoice_number,
            'date': invoice.date.strftime('%d/%m/%Y'),
            'due_date': invoice.due_date.strftime('%d/%m/%Y'),
            'customer_name': invoice.customer.name,
            'subtotal': float(invoice.subtotal),
            'vat_amount': float(invoice.total_vat_amount),
            'total_amount': float(invoice.total_amount),
            'payment_terms': invoice.payment_terms
        }
        
        # Generate PDF if requested
        pdf_buffer = None
        if request.include_pdf:
            pdf_buffer = invoice_service.generate_pdf_invoice(invoice_id)
        
        # Send via WhatsApp
        result = whatsapp_service.send_invoice(
            customer_phone=request.phone_number,
            invoice_data=invoice_data,
            pdf_buffer=pdf_buffer
        )
        
        if result['success']:
            # Mark invoice as sent
            invoice_service.mark_invoice_sent(invoice_id, 'whatsapp')
            
            return {
                'success': True,
                'message': 'Invoice sent via WhatsApp successfully',
                'whatsapp_response': result
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send WhatsApp: {str(e)}")


@router.post("/{invoice_id}/send-email")
async def send_invoice_email(
    invoice_id: str,
    email_to: str,
    include_pdf: bool = True,
    custom_message: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Send invoice via email"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # TODO: Implement email service
    # For now, return a placeholder response
    return {
        'success': True,
        'message': 'Email functionality to be implemented',
        'email_to': email_to,
        'include_pdf': include_pdf
    }


@router.post("/{invoice_id}/payment")
async def record_payment(
    invoice_id: str,
    payment: PaymentRequest,
    db: Session = Depends(get_db)
):
    """Record payment for invoice"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice_service = InvoiceService(db)
    
    try:
        invoice_service.mark_invoice_paid(
            invoice_id=invoice_id,
            payment_amount=float(payment.amount),
            payment_date=payment.payment_date
        )

        # Persist payment record (if not already done inside service)
        payment_record = PaymentModel(
            invoice_id=invoice.id,
            customer_id=invoice.customer_id,
            amount=payment.amount,
            payment_date=payment.payment_date or date.today(),
            payment_method=payment.payment_method or 'cash',
            reference=payment.reference,
            note=payment.note,
        )
        db.add(payment_record)
        db.commit()

        return {
            'success': True,
            'message': 'Payment recorded successfully',
            'payment_amount': float(payment.amount),
            'remaining_amount': float(invoice.amount_due),
            'invoice_id': invoice_id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{invoice_id}/payments")
async def list_payments(
    invoice_id: str,
    db: Session = Depends(get_db)
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return [
        {
            'id': p.id,
            'amount': float(p.amount),
            'payment_date': p.payment_date,
            'payment_method': p.payment_method,
            'reference': p.reference,
            'note': p.note,
            'created_by': p.created_by
        }
        for p in invoice.payments
    ]


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: str,
    invoice_update: InvoiceUpdate,
    updated_by: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Update invoice header fields and record audit entries"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    changes = []
    update_data = invoice_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        old = getattr(invoice, field, None)
        if old != value:
            setattr(invoice, field, value)
            changes.append((field, old, value))

    # Basic updated_by tracking (adds helper columns dynamically if exist)
    if hasattr(invoice, 'updated_by'):
        setattr(invoice, 'updated_by', updated_by)
    if hasattr(invoice, 'updated_at'):
        setattr(invoice, 'updated_at', datetime.utcnow())

    # Store audit in a lightweight table-less approach (could be replaced with real model)
    # If Audit model exists, integrate here. For now, print for diagnostics.
    for field, old, new in changes:
        print(f"[AUDIT] Invoice {invoice.invoice_number}: {field} {old} -> {new} (by {updated_by})")

    db.commit()
    db.refresh(invoice)
    invoice_service = InvoiceService(db)
    return _format_invoice_response(invoice, invoice_service.invoice_designer_config)


@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: str,
    deleted_by: Optional[str] = None,
    db: Session = Depends(get_db)
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice_number = invoice.invoice_number
    
    # Delete related invoice items first
    db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).delete()
    
    # Delete related payments
    db.query(PaymentModel).filter(PaymentModel.invoice_id == invoice_id).delete()
    
    # Delete related credit notes
    db.query(CreditNote).filter(CreditNote.original_invoice_id == invoice_id).delete()
    
    # Finally delete the invoice
    db.delete(invoice)
    db.commit()
    
    print(f"[AUDIT] Invoice {invoice_number} deleted by {deleted_by}")
    return { 'success': True, 'message': 'Invoice deleted', 'invoice_id': invoice_id }


@router.get("/{invoice_id}/audit")
async def invoice_audit_log(
    invoice_id: str,
    db: Session = Depends(get_db)
):
    # Placeholder: In real implementation, fetch from audit table.
    # For now return empty list to keep frontend logic simple.
    return []


@router.put("/{invoice_id}/status")
async def update_invoice_status(
    invoice_id: str,
    status: str,
    db: Session = Depends(get_db)
):
    """Update invoice status"""
    valid_statuses = ['draft', 'sent', 'paid', 'partial', 'overdue', 'cancelled']
    
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice.status = status
    db.commit()
    
    return {
        'success': True,
        'message': f'Invoice status updated to {status}',
        'invoice_id': invoice_id,
        'new_status': status
    }


@router.get("/statistics/summary")
async def get_invoice_statistics(
    branch_id: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """Get invoice statistics and summary"""
    from sqlalchemy import func
    
    query = db.query(Invoice)
    
    if branch_id:
        query = query.filter(Invoice.branch_id == branch_id)
    if date_from:
        query = query.filter(Invoice.date >= date_from)
    if date_to:
        query = query.filter(Invoice.date <= date_to)
    
    # Get counts by status
    status_counts = db.query(
        Invoice.status,
        func.count(Invoice.id).label('count'),
        func.sum(Invoice.total_amount).label('total_amount')
    ).group_by(Invoice.status).all()
    
    # Overall statistics
    total_invoices = query.count()
    total_amount = query.with_entities(func.sum(Invoice.total_amount)).scalar() or 0
    total_paid = query.with_entities(func.sum(Invoice.amount_paid)).scalar() or 0
    total_outstanding = total_amount - total_paid
    
    return {
        'total_invoices': total_invoices,
        'total_amount': float(total_amount),
        'total_paid': float(total_paid),
        'total_outstanding': float(total_outstanding),
        'status_breakdown': [
            {
                'status': status,
                'count': count,
                'total_amount': float(amount or 0)
            }
            for status, count, amount in status_counts
        ]
    }


@router.get("/{invoice_id}/dot-matrix")
async def get_dot_matrix_invoice(
    invoice_id: str,
    paper_width: int = Query(80, description="Paper width in characters"),
    form_length: int = Query(66, description="Form length in lines"),
    compressed: bool = Query(False, description="Use compressed printing"),
    carbon_copies: int = Query(1, description="Number of copies"),
    template: Optional[str] = Query(None, description="Template name"),
    db: Session = Depends(get_db)
):
    """Generate dot matrix printer format for invoice"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    dot_matrix_service = DotMatrixInvoiceService(db)
    
    try:
        # Load custom template if specified
        custom_template = None
        if template:
            template_setting = db.query(AppSetting).filter(
                AppSetting.key == f"dot_matrix_template_{template}"
            ).first()
            if template_setting:
                custom_template = template_setting.value
        
        # Generate dot matrix format
        dot_matrix_content = dot_matrix_service.generate_dot_matrix_invoice(
            invoice_id=invoice_id,
            paper_width=paper_width,
            form_length=form_length,
            compressed=compressed,
            carbon_copies=carbon_copies,
            custom_template=custom_template
        )
        
        # Return as plain text with appropriate headers
        headers = {
            'Content-Type': 'text/plain; charset=ascii',
            'Content-Disposition': f'attachment; filename="Invoice_{invoice.invoice_number}_DotMatrix.txt"'
        }
        
        return Response(
            content=dot_matrix_content,
            media_type='text/plain',
            headers=headers
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate dot matrix format: {str(e)}")


@router.post("/{invoice_id}/print-dot-matrix")
async def print_dot_matrix_invoice(
    invoice_id: str,
    print_request: DotMatrixPrintRequest,
    db: Session = Depends(get_db)
):
    """Generate dot matrix print format with custom settings"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    dot_matrix_service = DotMatrixInvoiceService(db)
    
    try:
        # Load custom template if specified
        custom_template = None
        if print_request.template:
            from app.models.app_setting import AppSetting
            template_setting = db.query(AppSetting).filter(
                AppSetting.key == f"dot_matrix_template_{print_request.template}"
            ).first()
            if template_setting:
                custom_template = template_setting.value
        
        # Generate dot matrix format
        dot_matrix_content = dot_matrix_service.generate_dot_matrix_invoice(
            invoice_id=invoice_id,
            paper_width=print_request.paper_width,
            form_length=print_request.form_length,
            compressed=print_request.compressed,
            carbon_copies=print_request.carbon_copies,
            custom_template=custom_template
        )
        
        return {
            'success': True,
            'message': 'Dot matrix format generated successfully',
            'content': dot_matrix_content,
            'settings': {
                'paper_width': print_request.paper_width,
                'form_length': print_request.form_length,
                'compressed': print_request.compressed,
                'carbon_copies': print_request.carbon_copies,
                'template': print_request.template
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate dot matrix format: {str(e)}")


@router.get("/dot-matrix/templates")
async def get_dot_matrix_templates(
    db: Session = Depends(get_db)
):
    """Get available dot matrix templates"""
    dot_matrix_service = DotMatrixInvoiceService(db)
    templates = dot_matrix_service.get_available_templates()
    
    # Add custom templates from database
    from app.models.app_setting import AppSetting
    custom_templates = db.query(AppSetting).filter(
        AppSetting.key.like('dot_matrix_template_%')
    ).all()
    
    for template_setting in custom_templates:
        template_name = template_setting.key.replace('dot_matrix_template_', '')
        templates[f'custom_{template_name}'] = {
            'name': f'Custom: {template_name}',
            'description': template_setting.description or 'Custom template',
            'custom': True
        }
    
    return {
        'success': True,
        'templates': templates
    }


@router.post("/dot-matrix/templates")
async def save_dot_matrix_template(
    template: DotMatrixTemplate,
    db: Session = Depends(get_db)
):
    """Save a custom dot matrix template"""
    dot_matrix_service = DotMatrixInvoiceService(db)
    
    success = dot_matrix_service.save_custom_template(
        template.name, 
        template.content, 
        template.settings
    )
    
    if success:
        return {
            'success': True,
            'message': f'Template "{template.name}" saved successfully'
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to save template")


@router.get("/{invoice_id}/print")
async def print_invoice_by_settings(
    invoice_id: str,
    db: Session = Depends(get_db)
):
    """Generate invoice using configured printer settings"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice_service = InvoiceService(db)
    
    try:
        # Get printer settings and generate appropriate format
        format_type, content, filename = invoice_service.generate_invoice_by_printer_type(invoice_id)
        
        # Set appropriate headers based on format
        if format_type == 'pdf':
            media_type = 'application/pdf'
        else:
            media_type = 'text/plain'
        
        headers = {
            'Content-Type': media_type,
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
        
        return Response(
            content=content,
            media_type=media_type,
            headers=headers
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate invoice: {str(e)}")


@router.get("/{invoice_id}/preview")
async def preview_invoice_by_settings(
    invoice_id: str,
    db: Session = Depends(get_db)
):
    """Preview invoice using configured printer settings"""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice_service = InvoiceService(db)
    
    try:
        # Get printer settings
        printer_settings = invoice_service.get_printer_settings()
        format_type, content, filename = invoice_service.generate_invoice_by_printer_type(invoice_id)
        
        # For text formats, return as preview content
        if format_type == 'text':
            preview_content = content.decode('utf-8', errors='replace')
        else:
            preview_content = "PDF content (use /print endpoint to download)"
        
        return {
            'success': True,
            'printer_type': printer_settings['invoice_printer_type'],
            'filename': filename,
            'format': format_type,
            'preview': preview_content if format_type == 'text' else None,
            'settings': printer_settings
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preview invoice: {str(e)}")


def _format_invoice_response(invoice: Invoice, designer_config: Optional[Dict[str, Any]] = None) -> InvoiceResponse:
    """Format invoice for API response"""
    # Calculate missing fields
    subtotal = invoice.total_amount - invoice.total_vat_amount if invoice.total_amount and invoice.total_vat_amount else 0
    amount_due = invoice.total_amount - invoice.amount_paid if invoice.total_amount and invoice.amount_paid else (invoice.total_amount or 0)

    config = designer_config or {}
    raw_layout = config.get('layout')
    layout = raw_layout if isinstance(raw_layout, list) else []
    form_data = config.get('form_data') if isinstance(config.get('form_data'), dict) else {}
    metadata = config.get('metadata') if isinstance(config.get('metadata'), dict) else {}
    version = config.get('version') if isinstance(config.get('version'), int) else None
    updated_at = config.get('updated_at') if isinstance(config.get('updated_at'), str) else None
    
    return InvoiceResponse(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        customer_id=invoice.customer_id,
        customer_name=invoice.customer.name if invoice.customer else "Unknown",
        branch_id=invoice.branch_id,
        invoice_date=invoice.date,
        due_date=invoice.due_date,
        status=invoice.status,
        subtotal=subtotal,
        discount_amount=invoice.discount_amount or 0,
        total_vat_amount=invoice.total_vat_amount or 0,
        total_amount=invoice.total_amount or 0,
        amount_paid=invoice.amount_paid or 0,
        amount_due=amount_due,
        payment_terms=invoice.payment_terms or 30,
        notes=invoice.notes,
        created_at=invoice.created_at,
        updated_at=getattr(invoice, 'updated_at', None),
        created_by=getattr(invoice, 'created_by', None),
        created_by_name=getattr(invoice.created_by_user, 'username', None) if getattr(invoice, 'created_by_user', None) else None,
        updated_by=getattr(invoice, 'updated_by', None),
        updated_by_name=None,  # Could join to user table if column exists
        invoice_items=[
            InvoiceItemResponse(
                id=item.id,
                product_id=item.product_id,
                product_name=item.product.name if item.product else "Unknown",
                quantity=item.quantity,
                unit_price=item.price,  # Fixed: Changed from unit_price to price
                discount_percentage=float(item.discount_percentage or 0),
                vat_rate=float(item.vat_rate or 0),
                subtotal=item.total or 0,  # Fixed: Use total as subtotal since model doesn't have subtotal
                discount_amount=item.discount_amount or 0,
                vat_amount=item.vat_amount or 0,
                total_amount=item.total or 0,  # Fixed: Use total instead of total_amount
                description=item.description or ""  # Ensure description is never None
            )
            for item in (invoice.invoice_items or [])
        ],
        auto_print=False,
        print_format=None,
        print_content_b64=None,
        print_filename=None,
        designer_layout=layout,
        designer_form_data=form_data,
        designer_metadata=metadata,
        designer_version=version,
        designer_updated_at=updated_at
    )


def _format_invoice_list_response(invoice: Invoice) -> InvoiceListResponse:
    """Format invoice for list API response"""
    # Calculate amount due safely
    amount_paid = invoice.amount_paid or Decimal('0.00')
    total_amount = invoice.total_amount or Decimal('0.00')
    amount_due = total_amount - amount_paid
    
    # Get customer name safely
    customer_name = invoice.customer.name if invoice.customer else "Unknown Customer"
    
    return InvoiceListResponse(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        customer_name=customer_name,
        invoice_date=invoice.date,
        due_date=invoice.due_date,
        status=invoice.status,
        total_amount=total_amount,
        amount_due=amount_due,
        updated_at=getattr(invoice, 'updated_at', None),
        updated_by=getattr(invoice, 'updated_by', None)
    )


# =============================
# INVOICE REVERSAL ENDPOINTS
# =============================

class InvoiceReversalRequest(BaseModel):
    """Invoice reversal request schema"""
    reversal_reason: str = Field(..., min_length=1, max_length=500)
    created_by: Optional[str] = None


class InvoiceReversalResponse(BaseModel):
    """Invoice reversal response schema"""
    original_invoice_id: str
    reversal_accounting_entry_id: str
    inventory_adjustments: List[Dict]
    status: str
    message: str


class InvoiceReversalSummaryResponse(BaseModel):
    """Invoice reversal summary response schema"""
    invoice_number: str
    customer_id: str
    total_amount: float
    subtotal: float
    vat_amount: float
    total_cogs: float
    items: List[Dict]
    accounting_entries_to_reverse: Dict


class InvoiceRecreateRequest(BaseModel):
    """Invoice recreation request schema"""
    reversal_reason: str = Field(..., min_length=1, max_length=500)
    new_invoice_data: Dict  # Contains the new invoice structure
    created_by: Optional[str] = None


class InvoiceRecreateResponse(BaseModel):
    """Invoice recreation response schema"""
    reversal_result: Dict
    new_invoice: Dict
    status: str
    message: str


@router.get("/{invoice_id}/reversal-summary", response_model=InvoiceReversalSummaryResponse)
async def get_invoice_reversal_summary(
    invoice_id: str,
    db: Session = Depends(get_db)
):
    """Get summary of what would be reversed for an invoice"""
    try:
        reversal_service = InvoiceReversalService(db)
        summary = reversal_service.get_invoice_reversal_summary(invoice_id)
        return InvoiceReversalSummaryResponse(**summary)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating reversal summary: {str(e)}")


@router.post("/{invoice_id}/reverse", response_model=InvoiceReversalResponse)
async def reverse_invoice(
    invoice_id: str,
    reversal_request: InvoiceReversalRequest,
    db: Session = Depends(get_db)
):
    """
    Reverse an invoice completely including:
    - Journal entry reversals
    - Inventory quantity restoration
    - Invoice status update
    """
    try:
        reversal_service = InvoiceReversalService(db)
        result = reversal_service.reverse_invoice(
            invoice_id=invoice_id,
            reversal_reason=reversal_request.reversal_reason,
            created_by=reversal_request.created_by
        )
        return InvoiceReversalResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reversing invoice: {str(e)}")


@router.post("/{invoice_id}/reverse-and-recreate", response_model=InvoiceRecreateResponse)
async def reverse_and_recreate_invoice(
    invoice_id: str,
    recreate_request: InvoiceRecreateRequest,
    db: Session = Depends(get_db)
):
    """
    Reverse original invoice and create a new one with updated formatting/items
    """
    try:
        reversal_service = InvoiceReversalService(db)
        result = reversal_service.reverse_and_recreate_invoice(
            original_invoice_id=invoice_id,
            new_invoice_data=recreate_request.new_invoice_data,
            reversal_reason=recreate_request.reversal_reason,
            created_by=recreate_request.created_by
        )
        return InvoiceRecreateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reversing and recreating invoice: {str(e)}")


@router.get("/{invoice_id}/can-reverse")
async def check_invoice_can_be_reversed(
    invoice_id: str,
    db: Session = Depends(get_db)
):
    """Check if an invoice can be reversed"""
    try:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        can_reverse = invoice.status not in ['reversed', 'cancelled']
        reasons = []
        
        if invoice.status == 'reversed':
            reasons.append("Invoice is already reversed")
        elif invoice.status == 'cancelled':
            reasons.append("Invoice is cancelled")
        
        # Check if there are any payments
        if invoice.amount_paid and invoice.amount_paid > 0:
            can_reverse = False
            reasons.append("Invoice has payments - payments must be reversed first")
        
        return {
            'can_reverse': can_reverse,
            'invoice_status': invoice.status,
            'reasons': reasons,
            'invoice_number': invoice.invoice_number,
            'total_amount': float(invoice.total_amount or 0),
            'amount_paid': float(invoice.amount_paid or 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking reversal eligibility: {str(e)}")
