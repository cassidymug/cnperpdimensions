from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.receipt import Receipt
from app.models.user import User
from app.services.receipt_service import ReceiptService

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)


router = APIRouter()


class ReceiptCreateRequest(BaseModel):
    sale_id: str
    format: Optional[str] = "a4"  # 50mm, 80mm, or a4


class InvoicePaymentRequest(BaseModel):
    amount: Decimal
    payment_method: str
    payment_date: Optional[date] = None
    reference: Optional[str] = None
    note: Optional[str] = None
    format: Optional[str] = None


class ReceiptResponse(BaseModel):
    id: str
    receipt_number: str
    sale_id: Optional[str]
    invoice_id: Optional[str]
    payment_id: Optional[str]
    customer_id: Optional[str]
    amount: Optional[float]
    currency: Optional[str]
    payment_method: Optional[str]
    payment_date: Optional[str]
    pdf_path: Optional[str]
    html_content: Optional[str]
    notes: Optional[str]
    printed: bool
    print_count: int
    created_by_user_id: str
    created_by_username: Optional[str]  # Add username field
    branch_id: str
    branch_name: Optional[str]  # Add branch name field
    created_at: Optional[str]


def _serialize_receipt(receipt: Receipt) -> dict:
    return {
        "id": receipt.id,
        "receipt_number": receipt.receipt_number,
        "sale_id": receipt.sale_id,
        "invoice_id": receipt.invoice_id,
        "payment_id": receipt.payment_id,
        "customer_id": receipt.customer_id,
        "amount": float(receipt.amount or 0) if receipt.amount is not None else None,
        "currency": receipt.currency,
        "payment_method": receipt.payment_method,
        "payment_date": receipt.payment_date.isoformat() if receipt.payment_date else None,
        "pdf_path": receipt.pdf_path,
        "html_content": receipt.html_content,
        "notes": receipt.notes,
        "printed": bool(receipt.printed),
        "print_count": receipt.print_count or 0,
        "created_by_user_id": receipt.created_by_user_id,
        "created_by_username": receipt.created_by_user.username if receipt.created_by_user else None,
        "branch_id": receipt.branch_id,
        "branch_name": receipt.branch.name if receipt.branch else None,
        "created_at": receipt.created_at.isoformat() if receipt.created_at else None
    }


@router.post("/generate", response_model=dict)
async def generate_receipt(
    request: ReceiptCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a receipt for a completed sale"""
    receipt_service = ReceiptService(db)
    result = receipt_service.generate_receipt(request.sale_id, current_user.id, request.format)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    return result


@router.post("/invoices/{invoice_id}/payments")
async def record_invoice_payment(
    invoice_id: str,
    request: InvoicePaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept a payment for an invoice (by ID or invoice number) and generate a receipt."""
    receipt_service = ReceiptService(db)
    result = receipt_service.record_invoice_payment(
        invoice_id,
        request.model_dump(),
        current_user.id,
        format_type=request.format
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to record payment"))

    return result


@router.get("/stats")
async def get_receipt_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receipt_service = ReceiptService(db)
    return receipt_service.get_receipt_stats()


@router.get("/recent")
async def get_recent_receipts(
    limit: int = Query(20, ge=1, le=200, description="Maximum number of receipts to return"),
    branch_id: Optional[str] = Query(None, description="Optional branch filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receipt_service = ReceiptService(db)
    receipts = receipt_service.get_recent_receipts(limit=limit, branch_id=branch_id)
    return [_serialize_receipt(receipt) for receipt in receipts]


@router.get("/search")
async def search_receipts(
    q: str = Query(""),
    status: str = Query(""),
    start_date: str = Query(""),
    end_date: str = Query(""),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receipt_service = ReceiptService(db)
    result = receipt_service.search_receipts(q, status, start_date, end_date, skip, limit)
    return {
        "total": result["total"],
        "receipts": [_serialize_receipt(r) for r in result["receipts"]]
    }


@router.get("/{receipt_id}", response_model=ReceiptResponse)
async def get_receipt(
    receipt_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receipt_service = ReceiptService(db)
    receipt = receipt_service.get_receipt(receipt_id)

    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    return _serialize_receipt(receipt)


@router.get("/sale/{sale_id}", response_model=List[ReceiptResponse])
async def get_receipts_by_sale(
    sale_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receipt_service = ReceiptService(db)
    receipts = receipt_service.get_receipts_by_sale(sale_id)
    return [_serialize_receipt(receipt) for receipt in receipts]


@router.post("/{receipt_id}/print")
async def mark_receipt_printed(
    receipt_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receipt_service = ReceiptService(db)
    success = receipt_service.mark_receipt_printed(receipt_id)

    if not success:
        raise HTTPException(status_code=404, detail="Receipt not found")

    return {"success": True, "message": "Receipt marked as printed"}


@router.post("/bulk-print")
async def bulk_print_receipts(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    receipt_ids = request.get('receipt_ids', [])

    if not receipt_ids:
        raise HTTPException(status_code=400, detail="No receipt IDs provided")

    receipt_service = ReceiptService(db)
    results = []

    for receipt_id in receipt_ids:
        success = receipt_service.mark_receipt_printed(receipt_id)
        results.append({
            'receipt_id': receipt_id,
            'success': success
        })

    return {"results": results, "total_processed": len(results)}
