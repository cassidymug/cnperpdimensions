from fastapi import APIRouter, HTTPException, status, Depends, Response
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date as Date, datetime
from uuid import uuid4
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.sales import Customer, Quotation, QuotationItem as DBQuotationItem
from app.models.inventory import Product
from app.services.document_printing_service import DocumentPrintingService
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()


class QuotationItemSchema(BaseModel):
    product_id: Optional[str] = None  # Made optional for custom items
    description: Optional[str] = None  # For custom text (labor, services, etc.)
    quantity: float
    price: float
    discount: float = 0.0


class QuotationCreate(BaseModel):
    customer_id: str
    date: Date
    valid_until: Optional[Date] = None
    reference: Optional[str] = None
    notes: Optional[str] = None
    items: List[QuotationItemSchema]
    subtotal: float
    vat: float
    total: float
    status: str = Field(..., pattern=r"^(created|draft)$")


class QuotationUpdate(BaseModel):
    customer_id: Optional[str] = None
    date: Optional[Date] = None
    valid_until: Optional[Date] = None
    reference: Optional[str] = None
    notes: Optional[str] = None
    items: Optional[List[QuotationItemSchema]] = None
    subtotal: Optional[float] = None
    vat: Optional[float] = None
    total: Optional[float] = None
    status: Optional[str] = None


class ConvertToInvoiceRequest(BaseModel):
    """Request schema for converting quotation to invoice"""
    branch_id: Optional[str] = None  # Override user's default branch if needed
    payment_terms: Optional[int] = 30  # Days until due


def _quotation_to_dict(quotation: Quotation, db: Session) -> dict:
    """Convert a Quotation ORM object to a dictionary with enriched data"""
    items_list = []
    for item in quotation.items:
        # Use description if available, otherwise use product name
        description = item.description if item.description else (item.product.name if item.product else None)
        items_list.append({
            "product_id": item.product_id,
            "product_name": item.product.name if item.product else None,
            "description": description,
            "quantity": float(item.quantity),
            "price": float(item.price),
            "discount": float(item.discount),
            "line_total": float(item.line_total) if item.line_total else 0.0,
        })
    
    return {
        "id": quotation.id,
        "quote_number": quotation.quote_number,
        "customer_id": quotation.customer_id,
        "customer_name": quotation.customer.name if quotation.customer else None,
        "date": quotation.date.isoformat() if quotation.date else None,
        "valid_until": quotation.valid_until.isoformat() if quotation.valid_until else None,
        "reference": quotation.reference,
        "notes": quotation.notes,
        "status": quotation.status,
        "subtotal": float(quotation.subtotal),
        "vat": float(quotation.vat),
        "total": float(quotation.total),
        "branch_id": quotation.branch_id,
        "created_by": quotation.created_by,
        "created_at": quotation.created_at.isoformat() if quotation.created_at else None,
        "updated_at": quotation.updated_at.isoformat() if quotation.updated_at else None,
        "items": items_list,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_quotation(
    quotation: QuotationCreate, 
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # Verify user has a branch assigned
        if not current_user.branch_id:
            raise HTTPException(
                status_code=400,
                detail="User must be assigned to a branch to create quotations"
            )
        
        # Generate unique quote number
        # Find the highest sequence number for this date
        date_prefix = f"Q-{quotation.date.strftime('%Y%m%d')}-"
        existing_quotes = db.query(Quotation).filter(
            Quotation.quote_number.like(f"{date_prefix}%")
        ).all()
        
        # Extract sequence numbers and find the max
        max_sequence = 0
        for q in existing_quotes:
            try:
                seq_str = q.quote_number.split('-')[-1]
                seq_num = int(seq_str)
                if seq_num > max_sequence:
                    max_sequence = seq_num
            except (ValueError, IndexError):
                continue
        
        sequence = max_sequence + 1
        quote_number = f"{date_prefix}{sequence:04d}"
        
        # Create quotation record with user and branch attribution
        db_quotation = Quotation(
            id=str(uuid4()),
            quote_number=quote_number,
            customer_id=quotation.customer_id,
            date=quotation.date,
            valid_until=quotation.valid_until,
            reference=quotation.reference,
            notes=quotation.notes,
            status=quotation.status,
            subtotal=quotation.subtotal,
            vat=quotation.vat,
            total=quotation.total,
            created_by=current_user.id,
            branch_id=current_user.branch_id,
        )
        db.add(db_quotation)
        db.flush()
        
        # Create quotation items
        for item in quotation.items:
            line_total = item.quantity * item.price * (1 - item.discount / 100)
            db_item = DBQuotationItem(
                id=str(uuid4()),
                quotation_id=db_quotation.id,
                product_id=item.product_id,
                description=item.description,
                quantity=item.quantity,
                price=item.price,
                discount=item.discount,
                line_total=line_total,
            )
            db.add(db_item)
        
        db.commit()
        db.refresh(db_quotation)
        
        return {"success": True, "quotation": _quotation_to_dict(db_quotation, db)}
    
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create quotation: {str(e)}"
        )


@router.get("")
def list_quotations(db: Session = Depends(get_db)):
    quotations = db.query(Quotation).order_by(Quotation.date.desc()).all()
    quotations_list = [_quotation_to_dict(q, db) for q in quotations]
    return {"success": True, "quotations": quotations_list}


@router.get("/{quotation_id}")
def get_quotation(quotation_id: str, db: Session = Depends(get_db)):
    quotation = db.query(Quotation).filter(
        (Quotation.id == quotation_id) | (Quotation.quote_number == quotation_id)
    ).first()
    
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    return {"success": True, "quotation": _quotation_to_dict(quotation, db)}


@router.get("/{quotation_id}/print")
def print_quotation_pdf(quotation_id: str, db: Session = Depends(get_db)):
    quotation = db.query(Quotation).filter(
        (Quotation.id == quotation_id) | (Quotation.quote_number == quotation_id)
    ).first()
    
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    enriched_rec = _quotation_to_dict(quotation, db)
    service = DocumentPrintingService(db)
    fmt, content, filename = service.generate_document_pdf(
        document_type="quote",
        document_id=enriched_rec.get("quote_number") or quotation_id,
        title=f"Quotation {enriched_rec.get('quote_number', '')}",
        content_data=enriched_rec,
    )
    return Response(content=content, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{filename}"'
    })


@router.put("/{quotation_id}")
def update_quotation(quotation_id: str, quotation: QuotationUpdate, db: Session = Depends(get_db)):
    db_quotation = db.query(Quotation).filter(
        (Quotation.id == quotation_id) | (Quotation.quote_number == quotation_id)
    ).first()
    
    if not db_quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    # Update quotation fields
    update_data = quotation.dict(exclude_unset=True, exclude={"items"})
    for field, value in update_data.items():
        setattr(db_quotation, field, value)
    
    # Update items if provided
    if quotation.items is not None:
        # Delete existing items
        db.query(DBQuotationItem).filter(DBQuotationItem.quotation_id == db_quotation.id).delete()
        
        # Create new items
        for item in quotation.items:
            line_total = item.quantity * item.price * (1 - item.discount / 100)
            db_item = DBQuotationItem(
                id=str(uuid4()),
                quotation_id=db_quotation.id,
                product_id=item.product_id,
                description=item.description,
                quantity=item.quantity,
                price=item.price,
                discount=item.discount,
                line_total=line_total,
            )
            db.add(db_item)
    
    db.commit()
    db.refresh(db_quotation)
    
    return {"success": True, "quotation": _quotation_to_dict(db_quotation, db)}


@router.delete("/{quotation_id}")
def delete_quotation(quotation_id: str, db: Session = Depends(get_db)):
    db_quotation = db.query(Quotation).filter(
        (Quotation.id == quotation_id) | (Quotation.quote_number == quotation_id)
    ).first()
    
    if not db_quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    deleted_data = _quotation_to_dict(db_quotation, db)
    db.delete(db_quotation)
    db.commit()
    
    return {"success": True, "message": "Quotation deleted", "quotation": deleted_data}


@router.post("/{quotation_id}/convert-to-invoice")
def convert_quotation_to_invoice(
    quotation_id: str, 
    request: ConvertToInvoiceRequest = None,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Convert an accepted quotation into an invoice with inventory tracking.
    
    - Creates invoice from quotation
    - Deducts inventory from branch allocation
    - Creates audit trail via InventoryTransaction
    - Tracks user who created the invoice
    - Uses authenticated user's context for attribution
    """
    from app.models.sales import Invoice, InvoiceItem as DBInvoiceItem
    from app.models.inventory import InventoryTransaction, BranchInventoryAllocation
    from datetime import timedelta
    
    # Get the quotation
    quotation = db.query(Quotation).filter(
        (Quotation.id == quotation_id) | (Quotation.quote_number == quotation_id)
    ).first()
    
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    # Check if quotation is in a valid state
    if quotation.status not in ['created', 'sent', 'accepted']:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot convert quotation with status '{quotation.status}'. Only 'created', 'sent', or 'accepted' quotations can be converted."
        )
    
    # Check if already converted
    existing_invoice = db.query(Invoice).filter(Invoice.quotation_id == quotation.id).first()
    if existing_invoice:
        raise HTTPException(
            status_code=400,
            detail=f"Quotation already converted to invoice {existing_invoice.invoice_number}"
        )
    
    # Use authenticated user's context for attribution
    if request is None:
        request = ConvertToInvoiceRequest()
    
    # Get user ID from authenticated user
    user_id = current_user.id
    
    # Get branch ID: request override > user's branch > quotation's branch
    branch_id = request.branch_id or current_user.branch_id or quotation.branch_id
    
    if not branch_id:
        raise HTTPException(
            status_code=400,
            detail="Cannot determine branch for invoice. User must be assigned to a branch or branch_id must be provided."
        )
    
    payment_days = request.payment_terms or 30
    
    try:
        # Generate invoice number
        today = datetime.now().date()
        existing_count = db.query(Invoice).filter(
            Invoice.date == today
        ).count()
        sequence = existing_count + 1
        invoice_number = f"INV-{today.strftime('%Y%m%d')}-{sequence:04d}"
        
        # Create invoice
        invoice = Invoice(
            id=str(uuid4()),
            invoice_number=invoice_number,
            quotation_id=quotation.id,
            customer_id=quotation.customer_id,
            date=today,
            due_date=today + timedelta(days=payment_days),
            status='pending',
            total=float(quotation.total),
            total_vat_amount=float(quotation.vat),
            total_amount=float(quotation.total),
            amount_paid=0.0,
            branch_id=branch_id,
            created_by=user_id,
            notes=f"Converted from quotation {quotation.quote_number}\n{quotation.notes or ''}".strip()
        )
        db.add(invoice)
        db.flush()
        
        # Create invoice items and handle inventory deduction
        inventory_errors = []
        
        for q_item in quotation.items:
            # Create invoice item
            inv_item = DBInvoiceItem(
                id=str(uuid4()),
                invoice_id=invoice.id,
                product_id=q_item.product_id,
                description=q_item.description if q_item.description else (q_item.product.name if q_item.product else None),
                quantity=float(q_item.quantity),
                price=float(q_item.price),
                total=float(q_item.line_total),
                vat_amount=float(q_item.line_total) * 0.14,  # Assuming 14% VAT
                discount_percentage=float(q_item.discount),
            )
            db.add(inv_item)
            
            # Handle inventory deduction for product items (not custom text items)
            if q_item.product_id:
                # Check branch allocation
                allocation = db.query(BranchInventoryAllocation).filter(
                    BranchInventoryAllocation.product_id == q_item.product_id,
                    BranchInventoryAllocation.branch_id == branch_id
                ).first()
                
                if not allocation:
                    inventory_errors.append(
                        f"Product '{q_item.product.name if q_item.product else q_item.product_id}' not allocated to branch"
                    )
                    continue
                
                # Check sufficient stock
                if allocation.available_quantity < float(q_item.quantity):
                    inventory_errors.append(
                        f"Insufficient stock for '{q_item.product.name if q_item.product else q_item.product_id}' "
                        f"(available: {allocation.available_quantity}, required: {q_item.quantity})"
                    )
                    continue
                
                # Deduct from allocation
                allocation.available_quantity -= float(q_item.quantity)
                
                # Create inventory transaction for audit trail
                inv_transaction = InventoryTransaction(
                    id=str(uuid4()),
                    product_id=q_item.product_id,
                    branch_id=branch_id,
                    transaction_type='sale',
                    quantity=-int(q_item.quantity),  # Negative for outgoing
                    reference=f"Invoice {invoice_number}",
                    note=f"Sale via invoice {invoice_number} (converted from quotation {quotation.quote_number})",
                    created_by=user_id,
                    date=today,
                    previous_quantity=int(allocation.available_quantity + float(q_item.quantity)),
                    new_quantity=int(allocation.available_quantity)
                )
                db.add(inv_transaction)
        
        # If there were inventory errors, rollback and report
        if inventory_errors:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Inventory allocation errors",
                    "errors": inventory_errors
                }
            )
        
        # Update quotation status
        quotation.status = 'accepted'
        
        db.commit()
        db.refresh(invoice)
        
        return {
            "success": True,
            "message": f"Quotation {quotation.quote_number} converted to invoice {invoice.invoice_number}",
            "invoice": {
                "id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "total": float(invoice.total),
                "status": invoice.status,
                "branch_id": branch_id,
                "created_by": user_id
            }
        }
    
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to convert quotation to invoice: {str(e)}"
        )

