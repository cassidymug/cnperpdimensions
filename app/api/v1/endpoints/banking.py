from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import date
from decimal import Decimal
# from app.core.security import get_current_user  # Removed for development

from app.core.database import get_db
from app.services.banking_service import BankingService
from app.services.ifrs_accounting_service import IFRSAccountingService
from app.core.response_wrapper import UnifiedResponse
from app.models.banking import BankAccount, BankTransaction, BankTransfer, BankReconciliation, ReconciliationItem, Beneficiary
from app.schemas.user import User
from app.utils.logger import get_logger, log_exception, log_error_with_context
from app.schemas.banking import (
    BankAccountCreate, BankAccountResponse, BankAccountUpdate,
    BankTransactionCreate, BankTransactionResponse, BankTransactionUpdate,
    BankTransferCreate, BankTransferResponse, BankTransferUpdate,
    BankReconciliationCreate, BankReconciliationResponse, BankReconciliationUpdate,
    ReconciliationItemCreate, ReconciliationItemResponse, ReconciliationItemUpdate,
    BeneficiaryCreate, BeneficiaryResponse, BeneficiaryUpdate,
    BankingSummaryResponse, BankStatementResponse
)

logger = get_logger(__name__)
# All banking endpoints require an authenticated user with specified roles (include superadmin)
router = APIRouter()  # Dependencies removed for development


# Bank Accounts Endpoints

@router.get("/cash-flow")
async def get_cash_flow_report(
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    branch_id: Optional[str] = Query(None, description="Branch filter"),
    db: Session = Depends(get_db)
):
    """Simplified cash flow classification based on bank transactions & transfers.

    Classification heuristics (override later with config):
      - Operating: default, also transaction_type containing: 'sale','expense','supplier','customer','vat','tax'
      - Investing: descriptions containing 'asset','equipment','purchase asset','capital expenditure'
      - Financing: transfer_type including 'loan','capital','dividend','equity', or description containing those.
    """
    from sqlalchemy import and_
    from datetime import date as dt_date
    if not end_date:
        end_date = dt_date.today()
    if not start_date:
        # default to month start
        start_date = end_date.replace(day=1)
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    # Fetch bank transactions in range
    tx_query = db.query(BankTransaction).filter(
        BankTransaction.date >= start_date,
        BankTransaction.date <= end_date
    )
    if branch_id:
        tx_query = tx_query.join(BankAccount, BankTransaction.bank_account_id==BankAccount.id).filter(BankAccount.branch_id==branch_id)
    transactions = tx_query.all()

    # Fetch transfers in range
    tr_query = db.query(BankTransfer).filter(
        BankTransfer.created_at >= start_date,
        BankTransfer.created_at <= end_date
    )
    transfers = tr_query.all()

    def classify_tx(t: BankTransaction):
        desc = (t.description or '').lower()
        ttype = (t.transaction_type or '').lower()
        if any(k in desc for k in ['asset ', 'equipment', 'capital expenditure', 'fixed asset']):
            return 'investing'
        if any(k in ttype for k in ['asset_purchase']):
            return 'investing'
        if any(k in desc for k in ['loan', 'capital', 'equity', 'dividend']):
            return 'financing'
        if any(k in ttype for k in ['loan', 'capital', 'equity', 'dividend']):
            return 'financing'
        return 'operating'

    def classify_transfer(tr: BankTransfer):
        desc = (tr.description or '').lower()
        ttype = (tr.transfer_type or '').lower()
        if any(k in ttype for k in ['loan','equity','capital']) or any(k in desc for k in ['loan','equity','capital']):
            return 'financing'
        return 'operating'  # internal reallocations treated as operating unless flagged

    buckets = {
        'operating': {'inflows':0.0,'outflows':0.0,'details':[]},
        'investing': {'inflows':0.0,'outflows':0.0,'details':[]},
        'financing': {'inflows':0.0,'outflows':0.0,'details':[]}
    }

    for t in transactions:
        cat = classify_tx(t)
        amt = float(t.amount or 0)
        direction = 'inflows' if amt > 0 else 'outflows'
        buckets[cat][direction] += abs(amt)
        buckets[cat]['details'].append({
            'id': t.id,
            'date': t.date,
            'description': t.description,
            'transaction_type': t.transaction_type,
            'amount': amt,
            'category': cat
        })

    for tr in transfers:
        cat = classify_transfer(tr)
        amt = float(tr.amount or 0)
        # Treat outgoing transfer as outflow; we don't know source/dest sign so assume positive = outflow from source
        buckets[cat]['outflows'] += amt
        buckets[cat]['details'].append({
            'id': tr.id,
            'date': tr.created_at,
            'description': tr.description,
            'transfer_type': tr.transfer_type,
            'amount': -amt,
            'category': cat,
            'is_transfer': True
        })

    # Opening and closing cash (sum of bank account balances simplistic)
    acct_query = db.query(BankAccount)
    if branch_id:
        acct_query = acct_query.filter(BankAccount.branch_id==branch_id)
    accounts = acct_query.all()
    from app.services.banking_service import BankingService
    bs = BankingService(db)
    closing_cash = sum(float(bs.get_bank_account_balance(a.id)) for a in accounts)
    net_cash_movement = sum((buckets[k]['inflows'] - buckets[k]['outflows']) for k in buckets)
    opening_cash = closing_cash - net_cash_movement

    return {
        'success': True,
        'data': {
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'opening_cash': opening_cash,
            'closing_cash': closing_cash,
            'net_cash_movement': net_cash_movement,
            'sections': {
                k: {
                    'inflows': v['inflows'],
                    'outflows': v['outflows'],
                    'net': v['inflows'] - v['outflows'],
                    'details': v['details'][:1000]  # cap
                } for k, v in buckets.items()
            }
        }
    }


@router.get("/cash-flow/pdf")
async def download_cash_flow_pdf(
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    branch_id: Optional[str] = Query(None, description="Branch filter"),
    include_logo: bool = Query(True, description="Include logo"),
    include_watermark: bool = Query(True, description="Include watermark"),
    watermark_text: Optional[str] = Query(None, description="Override watermark text"),
    db: Session = Depends(get_db)
):
    """Server-side PDF for cash flow with simple branding footer.

    Uses same logic as /cash-flow then renders PDF via ReportLab.
    """
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    import os, base64

    # Reuse existing function logic by calling it directly (avoid duplication)
    base = await get_cash_flow_report(start_date=start_date, end_date=end_date, branch_id=branch_id, db=db)
    if not base.get('success'):
        raise HTTPException(status_code=500, detail="Failed to build cash flow data")
    data = base['data']

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 25 * mm
    y = height - margin

    from app.core.config import settings
    logo_path = settings.brand_logo_path if include_logo else None
    wm_text = watermark_text or settings.brand_watermark_text
    header_text = settings.brand_header_text
    footer_brand_text = settings.brand_footer_text
    FALLBACK_LOGO_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAQAAAAAYLlVAAAAC0lEQVR42mP8/5+hHgAHggN4Vf6kZQAAAABJRU5ErkJggg=="  # simple placeholder block

    def footer(page_y):
        c.setStrokeColor(colors.lightgrey)
        c.setLineWidth(0.5)
        c.line(margin, 18*mm, width - margin, 18*mm)
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.grey)
        c.drawString(margin, 14*mm, f"{footer_brand_text} • Banking Cash Flow Report")
        c.drawRightString(width - margin, 14*mm, f"Page {c.getPageNumber()}")

    # Title / header
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor('#0d6efd'))
    c.drawString(margin, y, header_text)
    y -= 12
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.black)
    c.drawString(margin, y, "Banking Cash Flow Report")
    y -= 14
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.grey)
    c.drawString(margin, y, f"Period: {data['period']['start']} to {data['period']['end']}")
    y -= 12
    c.drawString(margin, y, f"Generated: {date.today().isoformat()}")
    c.setFillColor(colors.black)
    y -= 18

    # Summary box
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "Summary")
    y -= 12
    c.setFont("Helvetica", 9)
    summary_lines = [
        ("Opening Cash", data['opening_cash']),
        ("Net Cash Movement", data['net_cash_movement']),
        ("Closing Cash", data['closing_cash'])
    ]
    for label, val in summary_lines:
        c.drawString(margin+4, y, f"{label}:")
        c.drawRightString(width - margin, y, f"{val:,.2f}")
        y -= 12

    y -= 4
    # Watermark (diagonal)
    if include_watermark:
        try:
            c.saveState()
            c.setFillColor(colors.lightgrey)
            c.setFont("Helvetica-Bold", 60)
            c.translate(width/2, height/2)
            c.rotate(45)
            c.drawCentredString(0, 0, wm_text[:30])
            c.restoreState()
        except Exception:
            pass

    # Logo (top-right) with fallback base64
    if include_logo:
        try:
            logo_w = 35*mm
            if logo_path and os.path.exists(logo_path):
                c.drawImage(logo_path, width - margin - logo_w, height - margin - 20*mm, width=logo_w, preserveAspectRatio=True, mask='auto')
            else:
                # fallback
                logo_bytes = base64.b64decode(FALLBACK_LOGO_BASE64)
                c.drawImage(ImageReader(BytesIO(logo_bytes)), width - margin - logo_w, height - margin - 20*mm, width=logo_w, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # Activities
    for act in ["operating", "investing", "financing"]:
        section = data['sections'].get(act)
        if not section:
            continue
        if y < 60*mm:  # new page threshold
            footer(y)
            c.showPage()
            y = height - margin
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin, y, act.capitalize() + f" Activity  (Net: {section['net']:,.2f})")
        y -= 14
        c.setFont("Helvetica", 8)
        # Table header
        headers = ["Date", "Description", "Type", "Amount"]
        col_widths = [25*mm, 80*mm, 30*mm, 30*mm]
        x_positions = [margin, margin+col_widths[0], margin+col_widths[0]+col_widths[1], margin+col_widths[0]+col_widths[1]+col_widths[2]]
        c.setFillColor(colors.lightgrey)
        c.rect(margin-2, y-10, sum(col_widths)+4, 12, fill=1, stroke=0)
        c.setFillColor(colors.black)
        for i,h in enumerate(headers):
            c.drawString(x_positions[i], y, h)
        y -= 14
        max_rows = 200  # safety cap
        for row in section['details'][:max_rows]:
            if y < 30*mm:
                footer(y)
                c.showPage()
                y = height - margin
                c.setFont("Helvetica-Bold", 11)
                c.drawString(margin, y, act.capitalize() + " Activity (cont.)")
                y -= 14
                c.setFont("Helvetica", 8)
                c.setFillColor(colors.lightgrey)
                c.rect(margin-2, y-10, sum(col_widths)+4, 12, fill=1, stroke=0)
                c.setFillColor(colors.black)
                for i,h in enumerate(headers):
                    c.drawString(x_positions[i], y, h)
                y -= 14
            c.drawString(x_positions[0], y, str(row['date'])[:10] if row.get('date') else "")
            desc = (row.get('description') or '')[:45]
            c.drawString(x_positions[1], y, desc)
            c.drawString(x_positions[2], y, (row.get('transaction_type') or row.get('transfer_type') or '')[:10])
            c.drawRightString(x_positions[3]+col_widths[3]-4, y, f"{row.get('amount',0):,.2f}")
            y -= 12
        y -= 6

    footer(y)
    c.showPage()
    c.save()
    buffer.seek(0)
    filename = f"cash_flow_{data['period']['start']}_{data['period']['end']}.pdf"
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={filename}"})


@router.get("/cash-flow/xlsx")
async def download_cash_flow_xlsx(
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    branch_id: Optional[str] = Query(None, description="Branch filter"),
    include_logo: bool = Query(True, description="Include logo branding sheet"),
    include_watermark: bool = Query(True, description="Include watermark text in Branding sheet"),
    watermark_text: Optional[str] = Query(None, description="Override watermark text"),
    db: Session = Depends(get_db)
):
    """Server-side Excel for cash flow using pandas/openpyxl with branding footer sheet."""
    import pandas as pd
    from io import BytesIO

    base = await get_cash_flow_report(start_date=start_date, end_date=end_date, branch_id=branch_id, db=db)
    if not base.get('success'):
        raise HTTPException(status_code=500, detail="Failed to build cash flow data")
    data = base['data']

    output = BytesIO()
    from app.core.config import settings
    wm_text = watermark_text or settings.brand_watermark_text
    header_text = settings.brand_header_text
    footer_brand_text = settings.brand_footer_text
    logo_path = settings.brand_logo_path if include_logo else None
    from openpyxl.drawing.image import Image as XLImage
    import os, base64
    FALLBACK_LOGO_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAQAAAAAYLlVAAAAC0lEQVR42mP8/5+hHgAHggN4Vf6kZQAAAABJRU5ErkJggg=="

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Summary
        summary_rows = [
            ['Period Start', data['period']['start']],
            ['Period End', data['period']['end']],
            ['Opening Cash', data['opening_cash']],
            ['Net Cash Movement', data['net_cash_movement']],
            ['Closing Cash', data['closing_cash']]
        ]
        pd.DataFrame(summary_rows, columns=['Metric','Value']).to_excel(writer, sheet_name='Summary', index=False)

        # Activities
        for act, sec in data['sections'].items():
            rows = []
            for d in sec['details']:
                rows.append({
                    'Date': str(d.get('date'))[:10] if d.get('date') else '',
                    'Description': d.get('description') or '',
                    'Type': d.get('transaction_type') or d.get('transfer_type') or '',
                    'Amount': d.get('amount')
                })
            df = pd.DataFrame(rows)
            if df.empty:
                df = pd.DataFrame(columns=['Date','Description','Type','Amount'])
            df.to_excel(writer, sheet_name=act[:31], index=False)

        # Branding sheet
        branding_rows = [
            ['Header', header_text],
            ['Report','Banking Cash Flow'],
            ['Generated By', footer_brand_text],
            ['Period', f"{data['period']['start']} to {data['period']['end']}"]
        ]
        if include_watermark:
            branding_rows.append(['Watermark', wm_text])
        brand_df = pd.DataFrame(branding_rows, columns=['Key','Value'])
        brand_df.to_excel(writer, sheet_name='Branding', index=False)

        # Insert logo into Branding sheet if requested
        if include_logo:
            wb = writer.book
            ws = wb['Branding']
            try:
                if logo_path and os.path.exists(logo_path):
                    img = XLImage(logo_path)
                else:
                    # fallback create temp image from base64
                    from io import BytesIO
                    from PIL import Image as PILImage
                    logo_bytes = base64.b64decode(FALLBACK_LOGO_BASE64)
                    pil_img = PILImage.open(BytesIO(logo_bytes))
                    tmp_buf = BytesIO()
                    pil_img.save(tmp_buf, format='PNG')
                    tmp_buf.seek(0)
                    img = XLImage(tmp_buf)
                img.width = 140
                img.height = 40
                ws.add_image(img, 'D1')
            except Exception:
                pass

    output.seek(0)
    filename = f"cash_flow_{data['period']['start']}_{data['period']['end']}.xlsx"
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={filename}"})
@router.get("/accounts")
async def get_bank_accounts(
    db: Session = Depends(get_db),
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    account_type: Optional[str] = Query(None, description="Filter by account type"),
    currency: Optional[str] = Query(None, description="Filter by currency"),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get bank accounts with optional filtering"""
    banking_service = BankingService(db)

    # Build filters
    filters = {}
    if branch_id:
        filters['branch_id'] = branch_id
    if account_type:
        filters['account_type'] = account_type
    if currency:
        filters['currency'] = currency

    # Eager load the accounting_code relationship to avoid N+1 queries
    query = db.query(BankAccount).options(joinedload(BankAccount.accounting_code)).filter_by(**filters)
    # query = # Security check removed for development  # Removed for development
    accounts = query.all()

    # Import accounting service for proper balance calculation
    from app.services.accounting_service import AccountingService
    accounting_service = AccountingService(db)

    account_data = []
    for account in accounts:
        account_info = {
            "id": account.id,
            "name": account.name,
            "institution": account.institution,
            "account_number": account.account_number,
            "currency": account.currency,
            "account_type": account.account_type,
            "accounting_code_id": account.accounting_code_id,
            "accounting_code_name": account.accounting_code.name if account.accounting_code else None,
            "accounting_code": account.accounting_code.code if account.accounting_code else None,
            "balance": float(banking_service.get_bank_account_balance(account.id)),
            "total_debits": float(accounting_service.get_total_debits(account.accounting_code_id)),
            "total_credits": float(accounting_service.get_total_credits(account.accounting_code_id)),
            "created_at": account.created_at,
            "updated_at": account.updated_at
        }
        account_data.append(account_info)

    return UnifiedResponse.success(
        data=account_data,
        message=f"Retrieved {len(account_data)} bank accounts",
        meta={
            "total": len(account_data),
            "filters_applied": len(filters) > 0,
            "filters": filters
        }
    )


@router.post("/accounts")
async def create_bank_account(
    account_data: BankAccountCreate,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Create a new bank account"""
    banking_service = BankingService(db)

    # Convert Pydantic model to dict
    account_dict = account_data.dict()

    # Get the first available branch as default
    from app.models.branch import Branch
    default_branch = db.query(Branch).filter(Branch.active == True).first()
    if not default_branch:
        raise HTTPException(status_code=400, detail="No active branch found. Please create a branch first.")

    branch_ctx = default_branch.id
    account_dict['branch_id'] = branch_ctx
    account, result = banking_service.create_bank_account(account_dict, branch_ctx)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    # Return proper unified response
    return UnifiedResponse.success(
        data={
            "id": account.id,
            "name": account.name,
            "institution": account.institution,
            "account_number": account.account_number,
            "currency": account.currency,
            "account_type": account.account_type,
            "accounting_code_id": account.accounting_code_id,
            "created_at": account.created_at,
            "updated_at": account.updated_at
        },
        message="Bank account created successfully"
    )


@router.get("/accounts/{account_id}")
async def get_bank_account(
    account_id: str,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get a specific bank account"""
    # Eager load the accounting_code relationship
    account = db.query(BankAccount).options(joinedload(BankAccount.accounting_code)).filter(BankAccount.id == account_id).first()

    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    # Import accounting service for proper balance calculation
    from app.services.accounting_service import AccountingService
    accounting_service = AccountingService(db)

    return {
        "success": True,
        "data": {
            "id": account.id,
            "name": account.name,
            "institution": account.institution,
            "account_number": account.account_number,
            "currency": account.currency,
            "account_type": account.account_type,
            "accounting_code_id": account.accounting_code_id,
            "accounting_code_name": account.accounting_code.name if account.accounting_code else None,
            "accounting_code": account.accounting_code.code if account.accounting_code else None,
            "balance": float(BankingService(db).get_bank_account_balance(account.id)),
            "total_debits": float(accounting_service.get_total_debits(account.accounting_code_id)),
            "total_credits": float(accounting_service.get_total_credits(account.accounting_code_id)),
            "created_at": account.created_at,
            "updated_at": account.updated_at
        }
    }


@router.put("/accounts/{account_id}")
async def update_bank_account(
    account_id: str,
    account_data: BankAccountUpdate,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Update a bank account"""
    banking_service = BankingService(db)

    # Check if account exists
    account = db.query(BankAccount).filter(BankAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    # Convert Pydantic model to dict, excluding None values
    update_data = account_data.dict(exclude_unset=True)

    # Update the account
    result = banking_service.update_bank_account(account_id, update_data)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    # Return proper unified response
    updated_account = result['account']
    return UnifiedResponse.success(
        data={
            "id": updated_account.id,
            "name": updated_account.name,
            "institution": updated_account.institution,
            "account_number": updated_account.account_number,
            "currency": updated_account.currency,
            "account_type": updated_account.account_type,
            "accounting_code_id": updated_account.accounting_code_id,
            "created_at": updated_account.created_at,
            "updated_at": updated_account.updated_at
        },
        message="Bank account updated successfully"
    )


@router.delete("/accounts/{account_id}")
async def delete_bank_account(
    account_id: str,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Delete a bank account"""
    banking_service = BankingService(db)

    result = banking_service.delete_bank_account(account_id)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    return {
        "success": True,
        "message": "Bank account deleted successfully"
    }


# Bank Transactions Endpoints
@router.get("/transactions")
async def get_bank_transactions(
    db: Session = Depends(get_db),
    account_id: Optional[str] = Query(None, description="Filter by bank account ID"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    start_date: Optional[date] = Query(None, description="Filter from date"),
    end_date: Optional[date] = Query(None, description="Filter to date"),
    reconciled: Optional[bool] = Query(None, description="Filter by reconciliation status"),
    search: Optional[str] = Query(None, description="Search term for description or reference"),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get bank transactions with optional filtering - OPTIMIZED"""
    from sqlalchemy import or_

    # OPTIMIZATION: Use eager loading to avoid N+1 queries
    query = db.query(BankTransaction).options(
        joinedload(BankTransaction.bank_account),
        joinedload(BankTransaction.cost_center),
        joinedload(BankTransaction.project),
        joinedload(BankTransaction.department)
    ).distinct()

    # Apply filters at database level for efficiency
    if account_id:
        query = query.filter(BankTransaction.bank_account_id == account_id)
    if transaction_type:
        query = query.filter(BankTransaction.transaction_type == transaction_type)
    if start_date:
        query = query.filter(BankTransaction.date >= start_date)
    if end_date:
        query = query.filter(BankTransaction.date <= end_date)
    if reconciled is not None:
        query = query.filter(BankTransaction.reconciled == reconciled)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                BankTransaction.description.ilike(search_term),
                BankTransaction.reference.ilike(search_term)
            )
        )

    # Sort by most recent first and limit to recent transactions
    from sqlalchemy import desc
    transactions = query.order_by(desc(BankTransaction.date)).limit(500).all()

    return {
        "success": True,
        "data": [
            {
                "id": transaction.id,
                "bank_account_id": transaction.bank_account_id,
                "date": transaction.date,
                "amount": float(transaction.amount) if transaction.amount else None,
                "description": transaction.description,
                "transaction_type": transaction.transaction_type,
                "reference": transaction.reference,
                "reconciled": transaction.reconciled,
                "vat_amount": float(transaction.vat_amount) if transaction.vat_amount else None,
                "accounting_entry_id": transaction.accounting_entry_id
            }
            for transaction in transactions
        ]
    }


@router.post("/transactions", response_model=BankTransactionResponse)
async def create_bank_transaction(
    transaction_data: BankTransactionCreate,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Create a new bank transaction"""
    banking_service = BankingService(db)

    transaction_dict = transaction_data.dict()
    # Use the same branch_id as bank accounts
    branch_ctx = 'default-branch'
    if not branch_ctx:
        raise HTTPException(status_code=400, detail="Branch context required to create transaction")
    transaction, result = banking_service.create_bank_transaction(transaction_dict, branch_ctx)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    # Automatically create IFRS-compliant journal entries
    try:
        ifrs_service = IFRSAccountingService(db)
        journal_entries = ifrs_service.create_bank_transaction_entries(transaction)
        print(f"Successfully created {len(journal_entries)} journal entries for bank transaction {transaction.id}")
    except Exception as e:
        # Log the error but do not fail the transaction creation
        print(f"Warning: Failed to create journal entries for bank transaction {transaction.id}: {str(e)}")

    return transaction


@router.get("/transactions/{transaction_id}")
async def get_bank_transaction_detail(
    transaction_id: str,
    db: Session = Depends(get_db),
):
    """Get a single bank transaction by ID (drill-down detail)."""
    transaction = db.query(BankTransaction).filter(BankTransaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail="Bank transaction not found")
    return {
        "success": True,
        "data": {
            "id": transaction.id,
            "bank_account_id": transaction.bank_account_id,
            "date": transaction.date,
            "amount": float(transaction.amount) if transaction.amount else None,
            "description": transaction.description,
            "transaction_type": transaction.transaction_type,
            "reference": transaction.reference,
            "reconciled": transaction.reconciled,
            "vat_amount": float(transaction.vat_amount) if transaction.vat_amount else None,
            "accounting_entry_id": transaction.accounting_entry_id,
            "created_at": transaction.created_at,
        }
    }


# Bank Transfers Endpoints
@router.get("/transfers")
async def get_bank_transfers(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by transfer status"),
    transfer_type: Optional[str] = Query(None, description="Filter by transfer type"),
    start_date: Optional[date] = Query(None, description="Filter from date"),
    end_date: Optional[date] = Query(None, description="Filter to date"),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get bank transfers with optional filtering"""
    query = db.query(BankTransfer)

    if status:
        query = query.filter(BankTransfer.status == status)
    if transfer_type:
        query = query.filter(BankTransfer.transfer_type == transfer_type)
    if start_date:
        query = query.filter(BankTransfer.created_at >= start_date)
    if end_date:
        query = query.filter(BankTransfer.created_at <= end_date)

    transfers = query.all()

    return {
        "success": True,
        "data": [
            {
                "id": transfer.id,
                "amount": float(transfer.amount) if transfer.amount else None,
                "transfer_type": transfer.transfer_type,
                "status": transfer.status,
                "reference": transfer.reference,
                "description": transfer.description,
                "source_account_id": transfer.source_account_id,
                "destination_account_id": transfer.destination_account_id,
                "exchange_rate": float(transfer.exchange_rate) if transfer.exchange_rate else None,
                "converted_amount": float(transfer.converted_amount) if transfer.converted_amount else None,
                "vat_amount": float(transfer.vat_amount) if transfer.vat_amount else None,
                "transfer_fee": float(transfer.transfer_fee) if transfer.transfer_fee else None,
                "processed_at": transfer.processed_at,
                "completed_at": transfer.completed_at,
                "created_at": transfer.created_at
            }
            for transfer in transfers
        ]
    }


@router.post("/transfers", response_model=BankTransferResponse)
async def create_bank_transfer(
    transfer_data: BankTransferCreate,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Create a new bank transfer"""
    banking_service = BankingService(db)

    transfer_dict = transfer_data.dict()
    branch_ctx = 'default-branch'
    if not branch_ctx:
        raise HTTPException(status_code=400, detail="Branch context required to create transfer")
    transfer, result = banking_service.create_bank_transfer(transfer_dict, branch_ctx)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    # Journal entries are now created within the banking_service for transfers

    return transfer


@router.get("/transfers/{transfer_id}")
async def get_bank_transfer_detail(
    transfer_id: str,
    db: Session = Depends(get_db),
):
    """Get a single bank transfer by ID (drill-down detail)."""
    transfer = db.query(BankTransfer).filter(BankTransfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Bank transfer not found")
    return {
        "success": True,
        "data": {
            "id": transfer.id,
            "amount": float(transfer.amount) if transfer.amount else None,
            "transfer_type": transfer.transfer_type,
            "status": transfer.status,
            "reference": transfer.reference,
            "description": transfer.description,
            "source_account_id": transfer.source_account_id,
            "destination_account_id": transfer.destination_account_id,
            "exchange_rate": float(transfer.exchange_rate) if transfer.exchange_rate else None,
            "converted_amount": float(transfer.converted_amount) if transfer.converted_amount else None,
            "vat_amount": float(transfer.vat_amount) if transfer.vat_amount else None,
            "transfer_fee": float(transfer.transfer_fee) if transfer.transfer_fee else None,
            "processed_at": transfer.processed_at,
            "completed_at": transfer.completed_at,
            "created_at": transfer.created_at,
        }
    }


@router.post("/transfers/{transfer_id}/approve")
async def approve_bank_transfer(
    transfer_id: str,
    db: Session = Depends(get_db),
):
    """Approve a pending bank transfer and process it."""
    from datetime import datetime

    transfer = db.query(BankTransfer).filter(BankTransfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Bank transfer not found")

    # Check if transfer is already approved or completed
    if transfer.status == 'completed':
        raise HTTPException(status_code=400, detail="Transfer is already completed")

    if transfer.status == 'approved':
        raise HTTPException(status_code=400, detail="Transfer is already approved")

    # Update transfer status
    transfer.status = 'approved'
    transfer.processed_at = datetime.utcnow()

    # If you want to automatically complete it as well
    transfer.status = 'completed'
    transfer.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(transfer)

    return {
        "success": True,
        "message": "Transfer approved and completed successfully",
        "data": {
            "id": transfer.id,
            "status": transfer.status,
            "processed_at": transfer.processed_at,
            "completed_at": transfer.completed_at
        }
    }


@router.post("/transfers/{transfer_id}/reject")
async def reject_bank_transfer(
    transfer_id: str,
    db: Session = Depends(get_db),
):
    """Reject/cancel a pending bank transfer."""
    from datetime import datetime

    transfer = db.query(BankTransfer).filter(BankTransfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Bank transfer not found")

    # Check if transfer is already completed
    if transfer.status == 'completed':
        raise HTTPException(status_code=400, detail="Cannot reject a completed transfer")

    # Update transfer status
    transfer.status = 'rejected'
    transfer.processed_at = datetime.utcnow()

    db.commit()
    db.refresh(transfer)

    return {
        "success": True,
        "message": "Transfer rejected successfully",
        "data": {
            "id": transfer.id,
            "status": transfer.status,
            "processed_at": transfer.processed_at
        }
    }


# Bank Reconciliations Endpoints
@router.get("/reconciliations")
async def get_bank_reconciliations(
    db: Session = Depends(get_db),
    account_id: Optional[str] = Query(None, description="Filter by bank account ID"),
    status: Optional[str] = Query(None, description="Filter by reconciliation status"),
    start_date: Optional[date] = Query(None, description="Filter from statement date"),
    end_date: Optional[date] = Query(None, description="Filter to statement date"),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get bank reconciliations with optional filtering - OPTIMIZED"""

    # OPTIMIZATION: Use eager loading to avoid N+1 queries
    query = db.query(BankReconciliation).options(
        joinedload(BankReconciliation.bank_account),
        joinedload(BankReconciliation.reconciliation_items).joinedload(
            ReconciliationItem.bank_transaction
        )
    ).distinct()

    if account_id:
        query = query.filter(BankReconciliation.bank_account_id == account_id)
    if status:
        query = query.filter(BankReconciliation.status == status)
    if start_date:
        query = query.filter(BankReconciliation.statement_date >= start_date)
    if end_date:
        query = query.filter(BankReconciliation.statement_date <= end_date)

    # Sort by most recent and limit to prevent memory issues
    from sqlalchemy import desc
    reconciliations = query.order_by(desc(BankReconciliation.statement_date)).limit(500).all()

    return {
        "success": True,
        "data": [
            {
                "id": reconciliation.id,
                "bank_account_id": reconciliation.bank_account_id,
                "statement_date": reconciliation.statement_date,
                "statement_balance": float(reconciliation.statement_balance) if reconciliation.statement_balance else None,
                "book_balance": float(reconciliation.book_balance) if reconciliation.book_balance else None,
                "difference": float(reconciliation.difference) if reconciliation.difference else None,
                "status": reconciliation.status,
                "statement_reference": reconciliation.statement_reference,
                "notes": reconciliation.notes,
                "started_at": reconciliation.started_at,
                "completed_at": reconciliation.completed_at,
                "reconciled_at": reconciliation.reconciled_at,
                "created_at": reconciliation.created_at
            }
            for reconciliation in reconciliations
        ]
    }


@router.post("/reconciliations", response_model=BankReconciliationResponse)
async def create_bank_reconciliation(
    reconciliation_data: BankReconciliationCreate,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Create a new bank reconciliation"""
    banking_service = BankingService(db)

    reconciliation_dict = reconciliation_data.dict()
    reconciliation, result = banking_service.create_bank_reconciliation(reconciliation_dict, 'default-branch')

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    return reconciliation


@router.post("/transactions/reconcile")
async def reconcile_transaction(
    reconciliation_data: dict,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Reconcile a specific bank transaction"""
    banking_service = BankingService(db)

    transaction_id = reconciliation_data.get('transaction_id')
    if not transaction_id:
        raise HTTPException(status_code=400, detail="Transaction ID is required")

    result = banking_service.reconcile_transaction(transaction_id, reconciliation_data)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    return result


@router.post("/transactions/bulk-reconcile")
async def bulk_reconcile_transactions(
    reconciliation_data: dict,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Bulk reconcile multiple transactions"""
    banking_service = BankingService(db)

    transaction_ids = reconciliation_data.get('transaction_ids', [])
    if not transaction_ids:
        raise HTTPException(status_code=400, detail="Transaction IDs are required")

    result = banking_service.bulk_reconcile_transactions(reconciliation_data)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    return result


@router.get("/transactions/unreconciled")
async def get_unreconciled_transactions(
    account_id: Optional[str] = Query(None, description="Filter by bank account ID"),
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get all unreconciled transactions"""
    banking_service = BankingService(db)

    transactions = banking_service.get_unreconciled_transactions(account_id)

    return {
        "success": True,
        "data": transactions
    }


@router.get("/reconciliation/summary")
async def get_reconciliation_summary(
    account_id: Optional[str] = Query(None, description="Filter by bank account ID"),
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get reconciliation summary"""
    banking_service = BankingService(db)

    summary = banking_service.get_reconciliation_summary(account_id)

    return {
        "success": True,
        "data": summary
    }


@router.get("/reconciliation/statistics")
async def get_reconciliation_statistics(
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get overall reconciliation statistics"""
    banking_service = BankingService(db)

    statistics = banking_service.get_reconciliation_statistics()

    return {
        "success": True,
        "data": statistics
    }


@router.get("/reconciliations/{reconciliation_id}")
async def get_reconciliation_details(
    reconciliation_id: str,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get detailed reconciliation information"""
    banking_service = BankingService(db)

    details = banking_service.get_reconciliation_details(reconciliation_id)

    if not details['success']:
        raise HTTPException(status_code=404, detail=details['error'])

    return details


@router.post("/reconciliations/{reconciliation_id}/complete")
async def complete_reconciliation(
    reconciliation_id: str,
    completion_data: dict,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Complete a bank reconciliation"""
    banking_service = BankingService(db)

    result = banking_service.complete_reconciliation(reconciliation_id, completion_data)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    return result


# Enhanced Reconciliation Endpoints
@router.post("/reconciliations/{reconciliation_id}/reconcile")
async def reconcile_reconciliation_items(
    reconciliation_id: str,
    reconciliation_data: dict,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Enhanced reconciliation with manual entries and bank-initiated transactions"""
    banking_service = BankingService(db)

    result = banking_service.reconcile_reconciliation_items(reconciliation_id, reconciliation_data)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    return result


@router.post("/reconciliations/{reconciliation_id}/draft")
async def save_reconciliation_draft(
    reconciliation_id: str,
    draft_data: dict,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Save reconciliation draft with selected transactions and manual entries"""
    banking_service = BankingService(db)

    result = banking_service.save_reconciliation_draft(reconciliation_id, draft_data)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    return result


# Beneficiaries Endpoints
@router.get("/beneficiaries")
async def get_beneficiaries(
    db: Session = Depends(get_db),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get beneficiaries with optional filtering"""
    query = db.query(Beneficiary)

    if active is not None:
        query = query.filter(Beneficiary.active == active)
    if provider:
        query = query.filter(Beneficiary.provider == provider)

    beneficiaries = query.all()

    return {
        "success": True,
        "data": [
            {
                "id": beneficiary.id,
                "name": beneficiary.name,
                "account_type": beneficiary.account_type,
                "account_number": beneficiary.account_number,
                "bank_name": beneficiary.bank_name,
                "provider": beneficiary.provider,
                "mobile_number": beneficiary.mobile_number,
                "wallet_address": beneficiary.wallet_address,
                "email": beneficiary.email,
                "notes": beneficiary.notes,
                "active": beneficiary.active,
                "created_at": beneficiary.created_at
            }
            for beneficiary in beneficiaries
        ]
    }


@router.post("/beneficiaries", response_model=BeneficiaryResponse)
async def create_beneficiary(
    beneficiary_data: BeneficiaryCreate,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Create a new beneficiary"""
    beneficiary_dict = beneficiary_data.dict()
    beneficiary_dict['user_id'] = 'default-user-id'

    beneficiary = Beneficiary(**beneficiary_dict)
    db.add(beneficiary)
    db.commit()
    db.refresh(beneficiary)

    return beneficiary


# Banking Summary Endpoint
@router.get("/summary")
async def get_banking_summary(
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get banking summary for the current branch"""
    banking_service = BankingService(db)

    summary = banking_service.get_banking_summary('default-branch')

    return {
        "success": True,
        "data": summary
    }


# Bank Statement Endpoint
@router.get("/accounts/{account_id}/statement")
async def get_bank_statement(
    account_id: str,
    start_date: date = Query(..., description="Start date for statement"),
    end_date: date = Query(..., description="End date for statement"),
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get bank statement for a specific account and date range"""
    banking_service = BankingService(db)

    statement = banking_service.get_bank_statement(account_id, start_date, end_date)

    return {
        "success": True,
        "data": statement
    }
