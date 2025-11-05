from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.core.database import get_db
from app.services.vat_service import VatService
from app.services.enhanced_vat_service import EnhancedVatService
from app.services.app_setting_service import AppSettingService
from app.services.ifrs_accounting_service import IFRSAccountingService
from app.core.security import require_roles, require_any
from app.models.vat import VatReconciliation, VatReconciliationItem, VatPayment
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()  # Dependencies removed for development


@router.get("/summary")
async def get_vat_summary(
    db: Session = Depends(get_db),
    start_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(None, description="End date (YYYY-MM-DD)"),
    branch_id: str = Query(None, description="Branch ID filter")
):
    """Get comprehensive VAT summary from actual sales and purchase data"""
    try:
        # Parse dates
        start = None
        end = None
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Default to current month if no dates provided
        if not start or not end:
            today = date.today()
            start = date(today.year, today.month, 1)
            # Get last day of current month
            if today.month == 12:
                end = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(today.year, today.month + 1, 1) - timedelta(days=1)

        # Use enhanced VAT service for real calculations
        enhanced_vat_service = EnhancedVatService(db)
        summary = enhanced_vat_service.calculate_vat_summary(start, end, branch_id)

        return {"data": summary}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating VAT summary: {str(e)}")


@router.get("/breakdown")
async def get_vat_breakdown(
    db: Session = Depends(get_db),
    start_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(None, description="End date (YYYY-MM-DD)"),
    branch_id: str = Query(None, description="Branch ID filter")
):
    """Get detailed VAT breakdown by rate"""
    try:
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else date.today().replace(day=1)
        end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else date.today()

        enhanced_vat_service = EnhancedVatService(db)
        breakdown = enhanced_vat_service.get_vat_by_rate_breakdown(start, end, branch_id)

        return {"data": breakdown}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting VAT breakdown: {str(e)}")


@router.get("/transactions")
async def get_vat_transactions(
    db: Session = Depends(get_db),
    start_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(None, description="End date (YYYY-MM-DD)"),
    branch_id: str = Query(None, description="Branch ID filter"),
    limit: int = Query(100, description="Maximum number of transactions to return")
):
    """Get detailed VAT transactions"""
    try:
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else date.today().replace(day=1)
        end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else date.today()

        enhanced_vat_service = EnhancedVatService(db)
        transactions = enhanced_vat_service.get_vat_transactions_detail(start, end, branch_id, limit)

        return {"data": transactions}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting VAT transactions: {str(e)}")


@router.get("/return-data")
async def get_vat_return_data(
    db: Session = Depends(get_db),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    branch_id: str = Query(None, description="Branch ID filter")
):
    """Generate official VAT return data for tax authority submission"""
    try:
        # Parse dates
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        enhanced_vat_service = EnhancedVatService(db)
        return_data = enhanced_vat_service.generate_vat_return_data(start, end, branch_id)

        return {"data": return_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating VAT return data: {str(e)}")


@router.get("/validate-accounts")
async def validate_vat_accounts(
    db: Session = Depends(get_db),
    branch_id: str = Query(None, description="Branch ID filter")
):
    """Validate VAT account setup for accurate reporting"""
    try:
        enhanced_vat_service = EnhancedVatService(db)
        validation = enhanced_vat_service.validate_vat_accounts(branch_id)

        return {"data": validation}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating VAT accounts: {str(e)}")


@router.get("/reconciliations")
async def get_vat_reconciliations(
    db: Session = Depends(get_db),
    start_date: str = None,
    end_date: str = None,
    status: str = None,
    branch_id: str = None
):
    """Get VAT reconciliations"""
    try:
        vat_service = VatService(db)

        # Parse dates if provided
        start = None
        end = None
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Get reconciliations
        reconciliations = db.query(VatReconciliation)

        if start:
            reconciliations = reconciliations.filter(VatReconciliation.period_start >= start)
        if end:
            reconciliations = reconciliations.filter(VatReconciliation.period_end <= end)
        if status:
            reconciliations = reconciliations.filter(VatReconciliation.status == status)
        if branch_id:
            reconciliations = reconciliations.filter(VatReconciliation.branch_id == branch_id)

        reconciliations = reconciliations.order_by(VatReconciliation.period_start.desc()).all()

        # Format response
        result = []
        for rec in reconciliations:
            result.append({
                "id": rec.id,
                "period_start": rec.period_start.isoformat(),
                "period_end": rec.period_end.isoformat(),
                "description": rec.description,
                "vat_collected": float(rec.vat_collected),
                "vat_paid": float(rec.vat_paid),
                "net_vat_liability": float(rec.net_vat_liability),
                "status": rec.status,
                "calculated_at": rec.calculated_at.isoformat() if rec.calculated_at else None,
                "submitted_at": rec.submitted_at.isoformat() if rec.submitted_at else None,
                "paid_at": rec.paid_at.isoformat() if rec.paid_at else None,
                "total_payments": float(rec.total_payments),
                "outstanding_amount": float(rec.outstanding_amount),
                "payment_status": rec.payment_status,
                "last_payment_date": rec.last_payment_date.isoformat() if rec.last_payment_date else None
            })

        return {"data": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching VAT reconciliations: {str(e)}")


@router.post("/reconciliations")
async def create_vat_reconciliation(
    reconciliation_data: dict,
    db: Session = Depends(get_db)
):
    """Create a new VAT reconciliation"""
    try:
        from datetime import date
        # Create new reconciliation
        reconciliation = VatReconciliation(
            period_start=date.fromisoformat(reconciliation_data["period_start"]),
            period_end=date.fromisoformat(reconciliation_data["period_end"]),
            description=reconciliation_data.get("description", ""),
            vat_collected=Decimal(str(reconciliation_data.get("vat_collected", 0))),
            vat_paid=Decimal(str(reconciliation_data.get("vat_paid", 0))),
            net_vat_liability=Decimal(str(reconciliation_data.get("net_vat_liability", 0))),
            status=reconciliation_data.get("status", "draft"),
            vat_rate=Decimal(str(reconciliation_data.get("vat_rate", 14.0))),
            branch_id=reconciliation_data.get("branch_id")
        )

        db.add(reconciliation)
        db.commit()
        db.refresh(reconciliation)

        return {
            "id": reconciliation.id,
            "period_start": reconciliation.period_start.isoformat(),
            "period_end": reconciliation.period_end.isoformat(),
            "description": reconciliation.description,
            "vat_collected": float(reconciliation.vat_collected),
            "vat_paid": float(reconciliation.vat_paid),
            "net_vat_liability": float(reconciliation.net_vat_liability),
            "status": reconciliation.status
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating VAT reconciliation: {str(e)}")


@router.get("/summary")
async def get_vat_summary(
    db: Session = Depends(get_db),
    start_date: str = None,
    end_date: str = None,
    branch_id: str = None
):
    """Get VAT summary statistics"""
    try:
        vat_service = VatService(db)
        app_service = AppSettingService(db)

        # Parse dates if provided
        start = None
        end = None
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Get VAT summary
        summary = vat_service.get_vat_summary(start, end, branch_id)

        # Get app settings for VAT rate
        settings = app_service.get_settings()

        return {
            "data": {
                "vat_collected": float(summary.get("vat_collected", 0)),
                "vat_paid": float(summary.get("vat_paid", 0)),
                "net_vat_liability": float(summary.get("net_vat_liability", 0)),
                "vat_rate": float(settings.get("vat_rate", 14.0)),
                "period_start": start.isoformat() if start else None,
                "period_end": end.isoformat() if end else None
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching VAT summary: {str(e)}")


@router.get("/payments")
async def get_vat_payments(
    db: Session = Depends(get_db),
    reconciliation_id: str = None,
    start_date: str = None,
    end_date: str = None
):
    """Get VAT payments"""
    try:
        payments = db.query(VatPayment)

        if reconciliation_id:
            payments = payments.filter(VatPayment.vat_reconciliation_id == reconciliation_id)

        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            payments = payments.filter(VatPayment.payment_date >= start)

        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            payments = payments.filter(VatPayment.payment_date <= end)

        payments = payments.order_by(VatPayment.payment_date.desc()).all()

        result = []
        for payment in payments:
            result.append({
                "id": payment.id,
                "vat_reconciliation_id": payment.vat_reconciliation_id,
                "amount_paid": float(payment.amount_paid),
                "payment_date": payment.payment_date.isoformat(),
                "payment_time": payment.payment_time.isoformat(),
                "payment_method": payment.payment_method,
                "reference_number": payment.reference_number,
                "bank_details": payment.bank_details,
                "notes": payment.notes,
                "payment_status": payment.payment_status,
                "penalty_amount": float(payment.penalty_amount),
                "interest_amount": float(payment.interest_amount),
                "total_amount": float(payment.total_amount),
                "tax_authority": payment.tax_authority
            })

        return {"data": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching VAT payments: {str(e)}")


@router.post("/payments")
async def record_vat_payment(
    payment_data: dict,
    db: Session = Depends(get_db)
):
    """
    Record a VAT payment or refund with proper settlement journal entries.

    Handles both scenarios:
    - Payment (when Output VAT > Input VAT): Business pays net to tax authority
    - Refund (when Input VAT > Output VAT): Business receives net from tax authority
    """
    try:
        # Get the reconciliation to determine if this is a payment or refund
        reconciliation_id = payment_data.get("vat_reconciliation_id")
        reconciliation = db.query(VatReconciliation).filter(VatReconciliation.id == reconciliation_id).first()

        if not reconciliation:
            raise HTTPException(status_code=404, detail=f"VAT reconciliation {reconciliation_id} not found")

        # Determine transaction type based on net VAT liability
        is_refund = reconciliation.net_vat_liability < 0
        amount = abs(Decimal(str(payment_data["amount_paid"])))

        # Create the VAT payment/refund record
        payment = VatPayment(
            vat_reconciliation_id=reconciliation_id,
            amount_paid=amount,
            payment_date=date.fromisoformat(payment_data["payment_date"]),
            payment_method=payment_data["payment_method"],
            reference_number=payment_data.get("reference_number"),
            notes=payment_data.get("notes"),
            bank_account_id=payment_data.get("bank_account_id")
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        # Create IFRS-compliant journal entries
        try:
            ifrs_service = IFRSAccountingService(db)

            if is_refund:
                # VAT Refund scenario: Input VAT > Output VAT
                # Journal entries:
                #   DR  Bank/Cash
                #   DR  VAT Payable (2132) [if any output VAT]
                #       CR  VAT Receivable (1160)
                journal_entries = ifrs_service.create_vat_refund_journal_entries(
                    refund_amount=amount,
                    refund_date=payment.payment_date,
                    branch_id=reconciliation.branch_id,
                    bank_account_id=payment.bank_account_id,
                    vat_output_amount=reconciliation.vat_collected,  # Output VAT from sales
                    vat_input_amount=reconciliation.vat_paid         # Input VAT from purchases
                )
                transaction_type = "refund received"
            else:
                # VAT Payment scenario: Output VAT > Input VAT
                # Journal entries:
                #   DR  VAT Payable (2132)
                #       CR  VAT Receivable (1160)
                #       CR  Bank/Cash
                journal_entries = ifrs_service.create_tax_payment_journal_entries(
                    payment_amount=amount,
                    payment_date=payment.payment_date,
                    branch_id=reconciliation.branch_id,
                    bank_account_id=payment.bank_account_id,
                    vat_output_amount=reconciliation.vat_collected,  # Output VAT from sales
                    vat_input_amount=reconciliation.vat_paid         # Input VAT from purchases
                )
                transaction_type = "payment made"

            # Update reconciliation payment tracking
            if is_refund:
                # For refunds, reduce the outstanding amount (which is negative)
                reconciliation.total_payments = (reconciliation.total_payments or Decimal('0')) - amount
            else:
                # For payments, increase the total payments
                reconciliation.total_payments = (reconciliation.total_payments or Decimal('0')) + amount

            reconciliation.outstanding_amount = reconciliation.net_vat_liability - reconciliation.total_payments
            reconciliation.last_payment_date = payment.payment_date

            # Update payment status
            if abs(reconciliation.outstanding_amount) <= Decimal('0.01'):  # Allow 1 cent difference
                reconciliation.payment_status = 'paid'
                reconciliation.paid_at = datetime.now()
            elif reconciliation.total_payments > Decimal('0'):
                reconciliation.payment_status = 'partial'
            else:
                reconciliation.payment_status = 'unpaid'

            db.commit()

            print(f"Successfully created {len(journal_entries)} journal entries for VAT {transaction_type} {payment.id}")
            print(f"  - Cleared VAT Payable (Output): {reconciliation.vat_collected}")
            print(f"  - Cleared VAT Receivable (Input): {reconciliation.vat_paid}")
            print(f"  - Net {transaction_type}: {amount}")

        except Exception as e:
            print(f"Error: Failed to create journal entries for VAT {transaction_type} {payment.id}: {str(e)}")
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error creating VAT settlement journal entries: {str(e)}")

        return {
            "id": payment.id,
            "amount": float(amount),
            "transaction_type": transaction_type,
            "payment_date": payment.payment_date.isoformat(),
            "vat_output_cleared": float(reconciliation.vat_collected),
            "vat_input_cleared": float(reconciliation.vat_paid),
            "outstanding_amount": float(reconciliation.outstanding_amount),
            "payment_status": reconciliation.payment_status,
            "message": f"VAT {transaction_type} recorded successfully with settlement journal entries"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error recording VAT payment: {str(e)}")


@router.get("/items")
async def get_vat_items(
    db: Session = Depends(get_db),
    reconciliation_id: str = None,
    item_type: str = None,
    start_date: str = None,
    end_date: str = None
):
    """Get VAT reconciliation items"""
    try:
        items = db.query(VatReconciliationItem)

        if reconciliation_id:
            items = items.filter(VatReconciliationItem.vat_reconciliation_id == reconciliation_id)

        if item_type:
            items = items.filter(VatReconciliationItem.item_type == item_type)

        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            items = items.filter(VatReconciliationItem.transaction_date >= start)

        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            items = items.filter(VatReconciliationItem.transaction_date <= end)

        items = items.order_by(VatReconciliationItem.transaction_date.desc()).all()

        result = []
        for item in items:
            result.append({
                "id": item.id,
                "vat_reconciliation_id": item.vat_reconciliation_id,
                "item_type": item.item_type,
                "reference_type": item.reference_type,
                "reference_id": item.reference_id,
                "description": item.description,
                "vat_amount": float(item.vat_amount),
                "transaction_date": item.transaction_date.isoformat()
            })

        return {"data": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching VAT items: {str(e)}")
