from fastapi import APIRouter, Depends, HTTPException, Query, Response
from datetime import datetime, date
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal

from app.core.database import get_db
from app.core.security import require_any, require_roles, require_permission_or_roles
from app.services.pos_service import POSService
from app.services.pos_reconciliation_service import PosReconciliationService
from app.services.pos_receipt_service import PosReceiptService
from app.services.ifrs_accounting_service import IFRSAccountingService
from app.services.app_setting_service import AppSettingService
from app.models.pos import PosSession
from app.models.sales import Sale, SaleItem
from app.schemas.pos import ShiftReconciliationRequest

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

# POS module access: branch roles (cashier/pos_user, manager) + universal roles (admin, super_admin, accountant)
# Previously universal roles were blocked which caused 403s when admins tried to open sessions.
router = APIRouter()  # Dependencies removed for development


@router.get("/sessions")
async def get_pos_sessions(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by session status"),
    branch_id: Optional[str] = Query(None, description="Filter by branch ID")
):
    """Get POS sessions with optional filtering"""
    pos_service = POSService(db)
    
    if status == 'open':
        sessions = pos_service.get_open_sessions(branch_id)
    else:
        # Get all sessions for the branch
        query = db.query(PosSession)
        if branch_id:
            query = query.filter(PosSession.branch_id == branch_id)
        sessions = query.all()
    
    return {
        "success": True,
        "data": [
            {
                "id": str(session.id),
                "user_id": session.user_id,
                "branch_id": session.branch_id,
                "till_id": session.till_id,
                "opened_at": session.opened_at,
                "closed_at": session.closed_at,
                "float_amount": float(session.float_amount) if session.float_amount else 0.0,
                "cash_submitted": float(session.cash_submitted) if session.cash_submitted else 0.0,
                "status": session.status,
                "total_sales": float(session.total_sales) if session.total_sales else 0.0,
                "total_transactions": session.total_transactions or 0,
                "total_cash_sales": float(session.total_cash_sales) if session.total_cash_sales else 0.0,
                "total_card_sales": float(session.total_card_sales) if session.total_card_sales else 0.0,
                "total_other_sales": float(session.total_other_sales) if session.total_other_sales else 0.0,
                "total_refunds": float(session.total_refunds) if session.total_refunds else 0.0,
                "notes": session.notes
            }
            for session in sessions
        ]
    }


@router.get("/reconciliation/shifts")
async def get_pos_shift_reconciliations(
    date_str: Optional[str] = Query(None, alias="date", description="Shift date (YYYY-MM-DD); defaults to today"),
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    db: Session = Depends(get_db)
):
    """List POS shift reconciliations for a given business date."""
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    reconciliation_service = PosReconciliationService(db)
    data = reconciliation_service.get_shift_reconciliations(target_date, branch_id)

    return {
        "success": True,
        "data": data
    }


@router.post("/reconciliation/shifts")
async def record_pos_shift_reconciliation(
    payload: ShiftReconciliationRequest,
    db: Session = Depends(get_db)
):
    """Record float and cash collected for a specific POS session shift."""
    reconciliation_service = PosReconciliationService(db)

    result = reconciliation_service.record_shift_reconciliation(
        session_id=payload.session_id,
        float_given=payload.float_given,
        cash_collected=payload.cash_collected,
        shift_date=payload.shift_date,
        notes=payload.notes,
        verifier_id=payload.verified_by
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to reconcile shift"))

    return result


@router.get("/branch-defaults/{branch_id}/card-bank")
async def get_branch_default_card_bank(
    branch_id: str,
    db: Session = Depends(get_db)
):
    """Get the branch default card bank account id for POS"""
    svc = AppSettingService(db)
    default_id = svc.get_branch_default_card_bank_account(branch_id)
    return {"success": True, "data": {"branch_id": branch_id, "default_card_bank_account_id": default_id}}


class SetDefaultCardBankPayload(dict):
    pass


@router.post("/branch-defaults/{branch_id}/card-bank")
async def set_branch_default_card_bank(
    branch_id: str,
    payload: dict,
    db: Session = Depends(get_db)
):
    """Set the branch default card bank account id for POS"""
    bank_id = payload.get('bank_account_id') or payload.get('default_card_bank_account_id')
    if not bank_id:
        raise HTTPException(status_code=400, detail="bank_account_id is required")
    svc = AppSettingService(db)
    res = svc.set_branch_default_card_bank_account(branch_id, bank_id)
    return res

@router.delete("/branch-defaults/{branch_id}/card-bank")
async def clear_branch_default_card_bank(
    branch_id: str,
    db: Session = Depends(get_db)
):
    """Clear the branch default card bank account id for POS"""
    svc = AppSettingService(db)
    return svc.clear_branch_default_card_bank_account(branch_id)


@router.get("/defaults/card-bank")
async def get_global_default_card_bank(
    db: Session = Depends(get_db)
):
    """Get the global default card bank account id for POS"""
    svc = AppSettingService(db)
    default_id = svc.get_global_default_card_bank_account()
    return {"success": True, "data": {"default_card_bank_account_id": default_id}}


@router.post("/defaults/card-bank")
async def set_global_default_card_bank(
    payload: dict,
    db: Session = Depends(get_db)
):
    """Set the global default card bank account id for POS"""
    bank_id = payload.get('bank_account_id') or payload.get('default_card_bank_account_id')
    if not bank_id:
        raise HTTPException(status_code=400, detail="bank_account_id is required")
    svc = AppSettingService(db)
    return svc.set_global_default_card_bank_account(bank_id)


@router.post("/sessions/open")
async def open_pos_session(
    session_data: dict,
    db: Session = Depends(get_db)
):
    """Open a new POS session"""
    pos_service = POSService(db)
    
    user_id = session_data.get('user_id')
    branch_id = session_data.get('branch_id')
    till_id = session_data.get('till_id')
    float_amount = Decimal(str(session_data.get('float_amount', '0')))
    
    if not user_id or not branch_id:
        raise HTTPException(status_code=400, detail="user_id and branch_id are required")
    
    session, result = pos_service.open_pos_session(user_id, branch_id, till_id, float_amount)
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return {
        "success": True,
        "data": {
            "session_id": str(session.id),
            "till_id": session.till_id,
            "opened_at": session.opened_at,
            "float_amount": float(session.float_amount),
            "status": session.status,
            "message": result.get('message', 'Session opened successfully')
        }
    }


@router.post("/sessions/close")
async def close_pos_session(
    session_data: dict,
    db: Session = Depends(get_db)
):
    """Close a POS session"""
    pos_service = POSService(db)
    
    session_id = session_data.get('session_id')
    cash_submitted = Decimal(str(session_data.get('cash_submitted', '0')))
    notes = session_data.get('notes')
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    
    result = pos_service.close_pos_session(session_id, cash_submitted, notes)
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return {
        "success": True,
        "data": result
    }


@router.get("/sessions/{session_id}")
async def get_pos_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific POS session"""
    pos_service = POSService(db)
    
    session = pos_service.get_pos_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "success": True,
        "data": {
            "id": str(session.id),
            "user_id": session.user_id,
            "branch_id": session.branch_id,
            "till_id": session.till_id,
            "opened_at": session.opened_at,
            "closed_at": session.closed_at,
            "float_amount": float(session.float_amount) if session.float_amount else 0.0,
            "cash_submitted": float(session.cash_submitted) if session.cash_submitted else 0.0,
            "status": session.status,
            "total_sales": float(session.total_sales) if session.total_sales else 0.0,
            "total_transactions": session.total_transactions or 0,
            "total_cash_sales": float(session.total_cash_sales) if session.total_cash_sales else 0.0,
            "total_card_sales": float(session.total_card_sales) if session.total_card_sales else 0.0,
            "total_other_sales": float(session.total_other_sales) if session.total_other_sales else 0.0,
            "total_refunds": float(session.total_refunds) if session.total_refunds else 0.0,
            "notes": session.notes
        }
    }


@router.post("/sales")
async def create_sale(
    sale_data: dict,
    db: Session = Depends(get_db),
    # Allow cashiers & pos_user role to trigger sale posting (system auto-poster pattern)
    # current_user parameter removed for development)
):
    """Create a new sale transaction"""
    pos_service = POSService(db)

    session_id = sale_data.get('session_id')
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    # Indicate we want IFRS service to handle journal posting
    sale_data = dict(sale_data)
    sale_data['use_ifrs_posting'] = True
    sale, result = pos_service.create_sale(sale_data, session_id)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    # Create IFRS-compliant journal entries here (single source of truth)
    try:
        ifrs_service = IFRSAccountingService(db)
        bank_account_id = sale_data.get('card_bank_account_id')
        if not bank_account_id and (sale.payment_method or '').lower() == 'card':
            # Load default from settings per branch, fallback to global
            settings_svc = AppSettingService(db)
            bank_account_id = settings_svc.get_branch_default_card_bank_account(sale.branch_id)
            if not bank_account_id:
                bank_account_id = settings_svc.get_global_default_card_bank_account()
        journal_entries = ifrs_service.create_sale_journal_entries(sale, bank_account_id=bank_account_id)
        print(f"Successfully created {len(journal_entries)} IFRS journal entries for sale {sale.id}")
    except Exception as e:
        # Log the error but do not fail the sale creation
        print(f"Warning: Failed to create IFRS journal entries for sale {sale.id}: {str(e)}")

    # Generate and return receipt information
    receipt_info = None
    if result.get('receipt_generated') and result.get('receipt'):
        receipt_data = result['receipt']
        receipt_info = {
            'receipt_number': receipt_data['receipt_number'],
            'receipt_id': receipt_data['receipt_id'],
            'html_content': receipt_data['html_content'],
            'pdf_path': receipt_data.get('pdf_path')
        }

    return {
        "success": True,
        "data": {
            "sale_id": str(sale.id),
            "reference": sale.reference,
            "total_amount": float(sale.total_amount),
            "payment_method": sale.payment_method,
            "status": sale.status,
            "date": sale.date,
            "receipt": receipt_info
        }
    }


@router.get("/products")
async def get_products_for_pos(
    branch_id: Optional[str] = Query(None, description="Branch ID filter"),
    search: Optional[str] = Query(None, description="Search term for products"),
    db: Session = Depends(get_db)
):
    """Get products available for POS"""
    pos_service = POSService(db)
    
    products = pos_service.get_products_for_pos(branch_id, search)
    
    return {
        "success": True,
        "data": products
    }


@router.get("/customers")
async def get_customers_for_pos(
    branch_id: Optional[str] = Query(None, description="Branch ID filter"),
    search: Optional[str] = Query(None, description="Search term for customers"),
    db: Session = Depends(get_db)
):
    """Get customers for POS"""
    pos_service = POSService(db)
    
    customers = pos_service.get_customers_for_pos(branch_id, search)
    
    return {
        "success": True,
        "data": customers
    }


@router.get("/sales/{sale_id}")
async def get_sale(
    sale_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific sale with all details"""
    pos_service = POSService(db)
    
    sale = pos_service.get_sale_by_id(sale_id)
    
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    return {
        "success": True,
        "data": {
            "id": str(sale.id),
            "reference": sale.reference,
            "customer": {
                "id": str(sale.customer.id),
                "name": sale.customer.name,
                "email": sale.customer.email,
                "phone": sale.customer.phone
            } if sale.customer else None,
            "payment_method": sale.payment_method,
            "total_amount": float(sale.total_amount),
            "amount_tendered": float(sale.amount_tendered) if sale.amount_tendered else 0.0,
            "change_given": float(sale.change_given) if sale.change_given else 0.0,
            "total_vat_amount": float(sale.total_vat_amount) if sale.total_vat_amount else 0.0,
            "discount_amount": float(sale.discount_amount) if sale.discount_amount else 0.0,
            "discount_percentage": float(sale.discount_percentage) if sale.discount_percentage else 0.0,
            "status": sale.status,
            "date": sale.date,
            "items": [
                {
                    "id": str(item.id),
                    "product": {
                        "id": str(item.product.id),
                        "name": item.product.name,
                        "code": item.product.code
                    },
                    "quantity": item.quantity,
                    "selling_price": float(item.selling_price),
                    "vat_amount": float(item.vat_amount) if item.vat_amount else 0.0,
                    "vat_rate": float(item.vat_rate) if item.vat_rate else 0.0,
                    "total_amount": float(item.total_amount) if item.total_amount else 0.0
                }
                for item in sale.sale_items
            ]
        }
    }


@router.post("/sales/{sale_id}/refund")
async def refund_sale(
    sale_id: str,
    refund_data: dict,
    db: Session = Depends(get_db)
):
    """Process a sale refund"""
    pos_service = POSService(db)
    
    result = pos_service.refund_sale(sale_id, refund_data)
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    
    return {
        "success": True,
        "data": result
    }


# POS Receipt Endpoints

@router.get("/sales/{sale_id}/receipt")
async def get_sale_receipt(
    sale_id: str,
    copy_type: str = Query('customer', description="Receipt copy type: customer, merchant, or both"),
    db: Session = Depends(get_db)
):
    """Generate receipt for a sale using configured POS printer settings"""
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    receipt_service = PosReceiptService(db)
    
    try:
        if copy_type == 'both':
            # Generate both customer and merchant copies
            customer_receipt = receipt_service.generate_receipt(sale_id, 'customer')
            merchant_receipt = receipt_service.generate_receipt(sale_id, 'merchant')
            
            return {
                "success": True,
                "data": {
                    "customer_copy": customer_receipt,
                    "merchant_copy": merchant_receipt,
                    "printer_config": receipt_service.get_printer_config()
                }
            }
        else:
            receipt_content = receipt_service.generate_receipt(sale_id, copy_type)
            
            return {
                "success": True,
                "data": {
                    "receipt_content": receipt_content,
                    "copy_type": copy_type,
                    "printer_config": receipt_service.get_printer_config()
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate receipt: {str(e)}")


@router.get("/sales/{sale_id}/receipt/print")
async def print_sale_receipt(
    sale_id: str,
    copy_type: str = Query('customer', description="Receipt copy type: customer, merchant, or both"),
    db: Session = Depends(get_db)
):
    """Print receipt for a sale (returns raw ESC/POS commands for direct printing)"""
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    receipt_service = PosReceiptService(db)
    
    try:
        receipt_content = receipt_service.generate_receipt(sale_id, copy_type)
        
        # Return as raw text file for direct printing
        headers = {
            'Content-Type': 'text/plain; charset=ascii',
            'Content-Disposition': f'attachment; filename="receipt_{sale_id}.txt"'
        }
        
        return Response(
            content=receipt_content.encode('ascii', errors='replace'),
            media_type='text/plain',
            headers=headers
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate receipt: {str(e)}")


@router.get("/receipt-settings")
async def get_receipt_printer_settings(db: Session = Depends(get_db)):
    """Get current POS receipt printer settings"""
    receipt_service = PosReceiptService(db)
    
    return {
        "success": True,
        "data": {
            "printer_config": receipt_service.get_printer_config(),
            "auto_print": receipt_service.should_auto_print(),
            "copies_to_print": receipt_service.get_copies_to_print()
        }
    }


@router.post("/sales/{sale_id}/receipt/auto-print")
async def auto_print_receipt(
    sale_id: str,
    db: Session = Depends(get_db)
):
    """Auto-print receipt if enabled in settings"""
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    receipt_service = PosReceiptService(db)
    
    if not receipt_service.should_auto_print():
        return {
            "success": True,
            "message": "Auto-print is disabled",
            "printed": False
        }
    
    try:
        copies_printed = []
        copies_to_print = receipt_service.get_copies_to_print()
        
        for copy_type in copies_to_print:
            receipt_content = receipt_service.generate_receipt(sale_id, copy_type)
            # In a real implementation, this would send to the actual printer
            # For now, we just indicate what would be printed
            copies_printed.append({
                "copy_type": copy_type,
                "content_length": len(receipt_content),
                "status": "queued_for_printing"
            })
        
        return {
            "success": True,
            "message": f"Receipt{'s' if len(copies_printed) > 1 else ''} queued for printing",
            "printed": True,
            "copies": copies_printed,
            "printer_config": receipt_service.get_printer_config()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to auto-print receipt: {str(e)}")


@router.get("/receipt/test-print")
async def test_receipt_printer(db: Session = Depends(get_db)):
    """Test the receipt printer with a sample receipt"""
    
    # Get the most recent sale for testing
    recent_sale = db.query(Sale).order_by(Sale.date.desc()).first()
    
    if not recent_sale:
        # Create a test receipt without a real sale
        test_content = """
====================================
           CNPERP TEST
====================================
Date: """ + str(datetime.now().strftime('%d/%m/%Y %H:%M')) + """

TEST RECEIPT - PRINTER CHECK

This is a test receipt to verify
your POS printer configuration.

If you can read this clearly,
your printer is working correctly.

====================================
           TEST COMPLETE
====================================


"""
        headers = {
            'Content-Type': 'text/plain; charset=ascii',
            'Content-Disposition': 'attachment; filename="test_receipt.txt"'
        }
        
        return Response(
            content=test_content.encode('ascii', errors='replace'),
            media_type='text/plain',
            headers=headers
        )
    
    # Use real sale for more accurate test
    receipt_service = PosReceiptService(db)
    
    try:
        test_receipt = receipt_service.generate_receipt(str(recent_sale.id), 'customer')
        
        # Add test header
        test_receipt = "*** TEST RECEIPT ***\n\n" + test_receipt + "\n\n*** END TEST ***"
        
        headers = {
            'Content-Type': 'text/plain; charset=ascii',
            'Content-Disposition': 'attachment; filename="test_receipt.txt"'
        }
        
        return Response(
            content=test_receipt.encode('ascii', errors='replace'),
            media_type='text/plain',
            headers=headers
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate test receipt: {str(e)}")