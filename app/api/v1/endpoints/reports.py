"""
Reports API Endpoints - IFRS Compliant
Comprehensive reporting endpoints with IFRS compliance
"""

from typing import Optional
from datetime import date, datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.services.ifrs_reports_core import IFRSReportsCore
from app.services.aging_reports_service import AgingReportsService
from app.services.sales_reports_service import SalesReportsService
from app.services.cogs_reports_service import COGSReportsService
from app.services.financial_statements_service import FinancialStatementsService
from app.services.invoice_reports_service import InvoiceReportsService
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
from io import BytesIO
import uuid
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

from app.core.database import get_db
from app.models import User, Branch, Product, Sale, Purchase, BankTransaction
from app.models.sales import Invoice
from app.models.accounting import JournalEntry, AccountingCode
# Import schemas from the correct module
from app.schemas.report import (
    SalesReportResponse,
    InventoryReportResponse,
    OperationalReportResponse
)
from app.schemas.financial_statements import (
    BalanceSheet,
    IncomeStatement,
    CashFlowStatement,
    StatementOfChangesInEquity,
    TrialBalance,
    FinancialReportPackage,
    ReportExportRequest,
    FinancialReportResponse
)

from app.core.security import require_any
from app.core.security import require_any, require_permission_or_roles
from app.services.report_export_utils import export_key_value_pdf, flatten_dict
from app.core.config import settings
from app.core.cache import get_redis, redis_available
from app.core.metrics import (
    GENERIC_REPORT_REQUESTS,
    GENERIC_REPORT_FLAT_ROWS,
    GENERIC_REPORT_SIZE_BYTES,
    set_cache_size
)
from app.services.app_setting_service import AppSettingService

# Simple in-process cache for generic report payloads (keyed by hash)
_GENERIC_REPORT_CACHE: dict = {}
from fastapi import Depends
# Reports: accountants plus managers (managers may view/print sales & operational reports).
# Universal roles (super_admin, admin) already bypass via security.ALLOWED_EVERYTHING.
router = APIRouter()  # Dependencies removed for development

@router.get("/pos/reconciliation")
def get_pos_reconciliation(
    date_str: str = Query(None, description="Date (YYYY-MM-DD) to reconcile; defaults to today"),
    db: Session = Depends(get_db),
    # current_user parameter removed for development)
):
    """Nightly POS reconciliation summary of journal entries with origin='POS'.
    Aggregates totals by branch and payment method (if encoded in narration/description keywords).
    """
    from datetime import datetime, date
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    # Fetch entries tagged with origin POS for the target date
    entries = db.query(JournalEntry).filter(JournalEntry.origin=='POS', JournalEntry.date==target_date).all()
    total_debits = sum(e.debit_amount or 0 for e in entries)
    total_credits = sum(e.credit_amount or 0 for e in entries)
    by_branch = {}
    for e in entries:
        b = e.branch_id or 'unassigned'
        rec = by_branch.setdefault(b, { 'debits':0, 'credits':0, 'count':0 })
        rec['debits'] += float(e.debit_amount or 0)
        rec['credits'] += float(e.credit_amount or 0)
        rec['count'] += 1
    # Include global settings and wrap data
    settings_service = AppSettingService(db)
    report_settings = settings_service.get_currency_settings()
    return {
        'success': True,
        'settings': report_settings,
        'data': {
            'date': str(target_date),
            'entry_count': len(entries),
            'total_debits': float(total_debits),
            'total_credits': float(total_credits),
            'balanced': float(total_debits) == float(total_credits),
            'by_branch': by_branch
        },
        'generated_at': datetime.now().isoformat()
    }


@router.get("/invoice-metrics")
def get_invoice_metrics(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD); defaults to 30 days ago"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD); defaults to today"),
    top_n: int = Query(10, ge=1, le=100, description="Number of top customers to include"),
    include_zero: bool = Query(False, description="Include zero-amount invoices in aggregates"),
    export: Optional[str] = Query(None, description="Export format: pdf or xlsx"),
    db: Session = Depends(get_db),
):
    """Return invoice metrics, aging, and payment performance data."""

    try:
        service = InvoiceReportsService(db)
        report_data = service.get_invoice_metrics(
            start_date=start_date,
            end_date=end_date,
            include_zero=include_zero,
            top_n=top_n,
        )

        if export:
            fmt = (export or "").lower()
            period = report_data.get("period", {})
            filename_stub = f"invoice_metrics_{period.get('start', 'na')}_{period.get('end', 'na')}"

            if fmt == "pdf":
                buffer = service.export_pdf(report_data)
                return StreamingResponse(
                    buffer,
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename={filename_stub}.pdf"},
                )
            if fmt == "xlsx":
                buffer = service.export_xlsx(report_data)
                return StreamingResponse(
                    buffer,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename={filename_stub}.xlsx"},
                )
            raise HTTPException(status_code=400, detail="Unsupported export format; use pdf or xlsx")

        settings_service = AppSettingService(db)
        report_settings = settings_service.get_currency_settings()

        return {
            "success": True,
            "settings": report_settings,
            "data": report_data,
            "generated_at": datetime.utcnow().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive logging for runtime issues
        raise HTTPException(status_code=500, detail=f"Error generating invoice metrics: {exc}") from exc

@router.get("/trial-balance")
async def get_trial_balance(
    as_of_date: Optional[date] = Query(None, description="Trial balance as of date"),
    include_zero_balances: bool = Query(False, description="Include accounts with zero balances"),
    account_type_filter: Optional[str] = Query(None, description="Filter by account type"),
    export: Optional[str] = Query(None, description="Export format: pdf|xlsx"),
    include_logo: bool = Query(True, description="Include logo (PDF)"),
    include_watermark: bool = Query(True, description="Include watermark (PDF)"),
    watermark_text: Optional[str] = Query(None, description="Override watermark text (PDF)"),
    db: Session = Depends(get_db)
):
    """
    Get IFRS-compliant Trial Balance

    Standards: IAS 1 - Presentation of Financial Statements
    """
    try:
        ifrs_service = IFRSReportsCore(db)
        trial_balance = ifrs_service.get_trial_balance_data(
            as_of_date=as_of_date,
            include_zero_balances=include_zero_balances,
            account_type_filter=account_type_filter
        )

        # Export handling
        if export:
            fmt = (export or "").lower()
            period = {"start": (as_of_date or date.today()).isoformat(), "end": (as_of_date or date.today()).isoformat()}
            # Prepare rows robustly
            try:
                from app.services.report_export_utils import export_simple_table_pdf, export_trial_balance_rows
                rows = export_trial_balance_rows(trial_balance.get('entries', []) if isinstance(trial_balance, dict) else trial_balance)
            except Exception:
                # Fallback generic row builder
                rows = []
                entries = trial_balance.get('entries', []) if isinstance(trial_balance, dict) else (trial_balance or [])
                for r in entries:
                    rows.append([
                        r.get('code'), r.get('name'), r.get('type'), f"{r.get('debit',0):,.2f}", f"{r.get('credit',0):,.2f}"
                    ])
            if fmt == 'pdf':
                cols = ["Code","Name","Type","Debit","Credit"]
                buf = export_simple_table_pdf("Trial Balance", period, cols, rows, include_logo=include_logo, include_watermark=include_watermark, watermark_text=watermark_text)
                fname = f"trial_balance_{period['end']}.pdf"
                return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={fname}"})
            if fmt == 'xlsx':
                import pandas as pd
                from io import BytesIO
                wb = BytesIO()
                with pd.ExcelWriter(wb, engine='openpyxl') as writer:
                    import pandas as pd
                    df = pd.DataFrame(rows, columns=["Code","Name","Type","Debit","Credit"])
                    df.to_excel(writer, sheet_name='Trial Balance', index=False)
                    # Summary sheet if available
                    if isinstance(trial_balance, dict):
                        summary_items = []
                        for k in ("total_debits","total_credits","difference"):
                            if k in trial_balance:
                                summary_items.append([k.replace('_',' ').title(), trial_balance.get(k)])
                        if summary_items:
                            pd.DataFrame(summary_items, columns=['Metric','Value']).to_excel(writer, sheet_name='Summary', index=False)
                wb.seek(0)
                fname = f"trial_balance_{period['end']}.xlsx"
                return StreamingResponse(wb, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={fname}"})

        settings_service = AppSettingService(db)
        report_settings = settings_service.get_currency_settings()
        return {
            "success": True,
            "settings": report_settings,
            "data": trial_balance,
            "ifrs_standards": ["IAS 1 - Presentation of Financial Statements"],
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating trial balance: {str(e)}")

@router.get("/balance-sheet")
async def get_balance_sheet(
    as_of_date: Optional[date] = Query(None, description="Balance sheet as of date"),
    comparison_date: Optional[date] = Query(None, description="Comparison date for prior period"),
    detail_level: str = Query("summary", description="Level of detail: summary or detailed"),
    include_logo: bool = Query(True, description="Include logo in export (if generating PDF)"),
    include_watermark: bool = Query(True, description="Include watermark in export (if generating PDF)"),
    watermark_text: Optional[str] = Query(None, description="Override watermark text (PDF)"),
    export: Optional[str] = Query(None, description="Export format: pdf|xlsx"),
    db: Session = Depends(get_db)
):
    """
    Generate IFRS-compliant Balance Sheet (Statement of Financial Position)

    Standards: IAS 1 - Presentation of Financial Statements
    """
    try:
        financial_service = FinancialStatementsService(db)
        balance_sheet = financial_service.get_balance_sheet(
            as_of_date=as_of_date,
            comparison_date=comparison_date,
            include_notes=include_logo
        )

        # Export handling (optional)
        if export:
            fmt = (export or "").lower()
            from io import BytesIO
            period = {"start": (as_of_date or date.today()).isoformat(), "end": (as_of_date or date.today()).isoformat()}
            # Build table rows from sections
            def rows_from_section(name: str, items: list) -> list:
                r = []
                if not isinstance(items, list):
                    return r
                for it in items:
                    label = it.get('name') or it.get('label') or it.get('account_name')
                    amt = it.get('balance') or it.get('amount') or it.get('value') or 0
                    r.append([name, label, f"{float(amt):,.2f}"])
                return r
            rows = []
            bs_dict = balance_sheet if isinstance(balance_sheet, dict) else balance_sheet.model_dump()  # type: ignore
            for sec_key, title in [
                ('current_assets','Current Assets'),
                ('non_current_assets','Non-Current Assets'),
                ('current_liabilities','Current Liabilities'),
                ('non_current_liabilities','Non-Current Liabilities'),
                ('equity','Equity')
            ]:
                items = bs_dict.get('sections', {}).get(sec_key) if 'sections' in bs_dict else bs_dict.get(sec_key)
                rows.extend(rows_from_section(title, items or []))
            if fmt == 'pdf':
                from app.services.report_export_utils import export_simple_table_pdf
                cols = ["Section","Line Item","Amount"]
                buf = export_simple_table_pdf("Balance Sheet", period, cols, rows, include_logo=include_logo, include_watermark=include_watermark, watermark_text=watermark_text)
                fname = f"balance_sheet_{period['end']}.pdf"
                return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={fname}"})
            if fmt == 'xlsx':
                import pandas as pd
                wb = BytesIO()
                with pd.ExcelWriter(wb, engine='openpyxl') as writer:
                    pd.DataFrame(rows, columns=["Section","Line Item","Amount"]).to_excel(writer, sheet_name='Balance Sheet', index=False)
                    # Totals sheet
                    totals = []
                    for k in ("total_assets","total_liabilities","total_equity"):
                        v = bs_dict.get(k) or bs_dict.get('totals',{}).get(k)
                        if v is not None:
                            totals.append([k.replace('_',' ').title(), v])
                    if totals:
                        pd.DataFrame(totals, columns=['Metric','Value']).to_excel(writer, sheet_name='Summary', index=False)
                wb.seek(0)
                fname = f"balance_sheet_{period['end']}.xlsx"
                return StreamingResponse(wb, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={fname}"})

        return FinancialReportResponse(
            success=True,
            data=balance_sheet,
            metadata=getattr(balance_sheet, 'metadata', None),
            ifrs_standards=["IAS 1 - Presentation of Financial Statements"],
            generated_at=datetime.now(),
            export_available=True
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating balance sheet: {str(e)}")

@router.get("/debtors-aging")
async def get_debtors_aging(
    as_of_date: Optional[date] = Query(None, description="Aging as of date"),
    customer_id: Optional[str] = Query(None, description="Filter by specific customer"),
    min_amount: Optional[Decimal] = Query(None, description="Minimum amount to include"),
    currency: Optional[str] = Query(None, description="Filter by currency"),
    branch_id: Optional[str] = Query(None, description="Filter by branch"),
    export: Optional[str] = Query(None, description="Export format: pdf|xlsx"),
    include_logo: bool = Query(True, description="Include logo (PDF)"),
    include_watermark: bool = Query(True, description="Include watermark (PDF)"),
    watermark_text: Optional[str] = Query(None, description="Override watermark text (PDF)"),
    db: Session = Depends(get_db)
):
    """
    Get Debtors Aging Report with IFRS 9 Expected Credit Loss

    Standards: IFRS 9 - Financial Instruments (Expected Credit Losses)
    """
    try:
        aging_service = AgingReportsService(db)
        debtors_aging = aging_service.generate_debtors_aging(
            as_of_date=as_of_date,
            customer_id=customer_id,
            min_amount=min_amount,
            currency=currency,
            branch_id=branch_id
        )

        # Optional export
        if export:
            fmt = (export or "").lower()
            period = {"start": (as_of_date or date.today()).isoformat(), "end": (as_of_date or date.today()).isoformat()}
            # Build rows
            def to_rows(data: dict) -> list:
                rows = []
                debtors = (data or {}).get('debtors') or []
                for d in debtors:
                    rows.append([
                        d.get('customer_name'),
                        d.get('contact_person') or d.get('phone') or d.get('email') or '',
                        f"{float(d.get('current',0)):,.2f}",
                        f"{float(d.get('days_31_60',0)):,.2f}",
                        f"{float(d.get('days_61_90',0)):,.2f}",
                        f"{float(d.get('days_91_120',0)):,.2f}",
                        f"{float(d.get('days_120_plus',0)):,.2f}",
                        f"{float(d.get('total_outstanding',0)):,.2f}"
                    ])
                return rows
            rows = to_rows(debtors_aging if isinstance(debtors_aging, dict) else {})
            if fmt == 'pdf':
                from app.services.report_export_utils import export_simple_table_pdf
                cols = ["Customer","Contact","Current","31-60","61-90","91-120","120+","Total"]
                buf = export_simple_table_pdf("Debtors Aging", period, cols, rows, include_logo=include_logo, include_watermark=include_watermark, watermark_text=watermark_text)
                fname = f"debtors_aging_{period['end']}.pdf"
                return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={fname}"})
            if fmt == 'xlsx':
                import pandas as pd
                from io import BytesIO
                wb = BytesIO()
                with pd.ExcelWriter(wb, engine='openpyxl') as writer:
                    pd.DataFrame(rows, columns=["Customer","Contact","Current","31-60","61-90","91-120","120+","Total"]).to_excel(writer, sheet_name='Debtors Aging', index=False)
                    # Summary
                    summary = (debtors_aging or {}).get('summary') if isinstance(debtors_aging, dict) else None
                    if isinstance(summary, dict):
                        pd.DataFrame([[k.replace('_',' ').title(), v] for k,v in summary.items()], columns=['Bucket','Amount']).to_excel(writer, sheet_name='Summary', index=False)
                wb.seek(0)
                fname = f"debtors_aging_{period['end']}.xlsx"
                return StreamingResponse(wb, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={fname}"})

        settings_service = AppSettingService(db)
        report_settings = settings_service.get_currency_settings()
        return {
            "success": True,
            "settings": report_settings,
            "data": debtors_aging,
            "ifrs_standards": ["IFRS 9 - Financial Instruments"],
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating debtors aging: {str(e)}")

@router.get("/creditors-aging")
async def get_creditors_aging(
    as_of_date: Optional[date] = Query(None, description="Aging as of date"),
    supplier_id: Optional[str] = Query(None, description="Filter by specific supplier"),
    min_amount: Optional[Decimal] = Query(None, description="Minimum amount to include"),
    currency: Optional[str] = Query(None, description="Filter by currency"),
    branch_id: Optional[str] = Query(None, description="Filter by branch"),
    export: Optional[str] = Query(None, description="Export format: pdf|xlsx"),
    include_logo: bool = Query(True, description="Include logo (PDF)"),
    include_watermark: bool = Query(True, description="Include watermark (PDF)"),
    watermark_text: Optional[str] = Query(None, description="Override watermark text (PDF)"),
    db: Session = Depends(get_db)
):
    """
    Get Creditors Aging Report

    Standards: IAS 1 - Presentation of Financial Statements
    """
    try:
        aging_service = AgingReportsService(db)
        creditors_aging = aging_service.generate_creditors_aging(
            as_of_date=as_of_date,
            supplier_id=supplier_id,
            min_amount=min_amount,
            currency=currency,
            branch_id=branch_id
        )
        # Optional export
        if export:
            fmt = (export or "").lower()
            period = {"start": (as_of_date or date.today()).isoformat(), "end": (as_of_date or date.today()).isoformat()}
            def to_rows(data: dict) -> list:
                rows = []
                creditors = (data or {}).get('creditors') or []
                for d in creditors:
                    rows.append([
                        d.get('supplier_name'),
                        d.get('contact_person') or d.get('phone') or d.get('email') or '',
                        f"{float(d.get('current',0)):,.2f}",
                        f"{float(d.get('days_31_60',0)):,.2f}",
                        f"{float(d.get('days_61_90',0)):,.2f}",
                        f"{float(d.get('days_91_120',0)):,.2f}",
                        f"{float(d.get('days_120_plus',0)):,.2f}",
                        f"{float(d.get('total_payable',0)):,.2f}"
                    ])
                return rows
            rows = to_rows(creditors_aging if isinstance(creditors_aging, dict) else {})
            if fmt == 'pdf':
                from app.services.report_export_utils import export_simple_table_pdf
                cols = ["Supplier","Contact","Current","31-60","61-90","91-120","120+","Total"]
                buf = export_simple_table_pdf("Creditors Aging", period, cols, rows, include_logo=include_logo, include_watermark=include_watermark, watermark_text=watermark_text)
                fname = f"creditors_aging_{period['end']}.pdf"
                return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={fname}"})
            if fmt == 'xlsx':
                import pandas as pd
                from io import BytesIO
                wb = BytesIO()
                with pd.ExcelWriter(wb, engine='openpyxl') as writer:
                    pd.DataFrame(rows, columns=["Supplier","Contact","Current","31-60","61-90","91-120","120+","Total"]).to_excel(writer, sheet_name='Creditors Aging', index=False)
                    # Summary
                    summary = (creditors_aging or {}).get('summary') if isinstance(creditors_aging, dict) else None
                    if isinstance(summary, dict):
                        pd.DataFrame([[k.replace('_',' ').title(), v] for k,v in summary.items()], columns=['Bucket','Amount']).to_excel(writer, sheet_name='Summary', index=False)
                wb.seek(0)
                fname = f"creditors_aging_{period['end']}.xlsx"
                return StreamingResponse(wb, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={fname}"})

        settings_service = AppSettingService(db)
        report_settings = settings_service.get_currency_settings()
        return {
            "success": True,
            "settings": report_settings,
            "data": creditors_aging,
            "ifrs_standards": ["IAS 1 - Presentation of Financial Statements"],
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating creditors aging: {str(e)}")

@router.get("/customer-aging-summary")
async def get_customer_aging_summary(
    as_of_date: Optional[date] = Query(None, description="Summary as of date"),
    db: Session = Depends(get_db)
):
    """
    Get Customer Aging Summary with Risk Ratings

    Standards: IFRS 9 - Financial Instruments (Credit Risk Assessment)
    """
    try:
        aging_service = AgingReportsService(db)
        summary = aging_service.get_customer_aging_summary(as_of_date=as_of_date)

        return {
            "success": True,
            "data": summary,
            "ifrs_standards": ["IFRS 9 - Financial Instruments"],
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating customer aging summary: {str(e)}")

@router.get("/supplier-aging-summary")
async def get_supplier_aging_summary(
    as_of_date: Optional[date] = Query(None, description="Summary as of date"),
    db: Session = Depends(get_db)
):
    """
    Get Supplier Aging Summary with Payment Priorities

    Standards: IAS 1 - Presentation of Financial Statements
    """
    try:
        aging_service = AgingReportsService(db)
        summary = aging_service.get_supplier_aging_summary(as_of_date=as_of_date)

        return {
            "success": True,
            "data": summary,
            "ifrs_standards": ["IAS 1 - Presentation of Financial Statements"],
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating supplier aging summary: {str(e)}")

@router.get("/ifrs-compliance-check")
async def get_ifrs_compliance_check(
    as_of_date: Optional[date] = Query(None, description="Compliance check as of date"),
    db: Session = Depends(get_db)
):
    """
    Comprehensive IFRS Compliance Check

    Validates compliance across multiple IFRS standards
    """
    try:
        if as_of_date is None:
            as_of_date = date.today()

        ifrs_service = IFRSReportsCore(db)
        aging_service = AgingReportsService(db)

        # Get trial balance for basic compliance
        trial_balance = ifrs_service.get_trial_balance_data(as_of_date=as_of_date)

        # Get balance sheet for financial position compliance
        balance_sheet = ifrs_service.get_balance_sheet_data(as_of_date=as_of_date)

        # Get aging for credit risk compliance
        debtors_aging = aging_service.generate_debtors_aging(as_of_date=as_of_date)

        # Overall compliance score
        compliance_checks = {
            'trial_balance_balanced': trial_balance['is_balanced'],
            'balance_sheet_balanced': balance_sheet['balance_check']['is_balanced'],
            'ifrs_categories_assigned': all(
                item['ifrs_category'] for item in trial_balance['accounts']
            ),
            'expected_credit_loss_calculated': debtors_aging['expected_credit_loss']['total_provision'] >= 0
        }

        compliance_score = sum(compliance_checks.values()) / len(compliance_checks) * 100

        return {
            "success": True,
            "data": {
                "as_of_date": as_of_date,
                "overall_compliance_score": compliance_score,
                "compliance_checks": compliance_checks,
                "recommendations": _get_compliance_recommendations(compliance_checks),
                "ifrs_standards_covered": [
                    "IAS 1 - Presentation of Financial Statements",
                    "IFRS 9 - Financial Instruments",
                    "IAS 2 - Inventories",
                    "IAS 7 - Statement of Cash Flows",
                    "IAS 12 - Income Taxes"
                ]
            },
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing IFRS compliance check: {str(e)}")

def _get_compliance_recommendations(compliance_checks: dict) -> list:
    """Generate compliance recommendations based on check results"""

    recommendations = []

    if not compliance_checks['trial_balance_balanced']:
        recommendations.append({
            "priority": "HIGH",
            "standard": "IAS 1",
            "issue": "Trial balance is not balanced",
            "recommendation": "Review and correct journal entries to ensure debits equal credits"
        })

    if not compliance_checks['balance_sheet_balanced']:
        recommendations.append({
            "priority": "HIGH",
            "standard": "IAS 1",
            "issue": "Balance sheet equation is not balanced",
            "recommendation": "Verify that Assets = Liabilities + Equity"
        })

    if not compliance_checks['ifrs_categories_assigned']:
        recommendations.append({
            "priority": "MEDIUM",
            "standard": "IAS 1",
            "issue": "Some accounts lack IFRS category assignments",
            "recommendation": "Assign appropriate IFRS categories to all accounting codes"
        })

    if not compliance_checks['expected_credit_loss_calculated']:
        recommendations.append({
            "priority": "MEDIUM",
            "standard": "IFRS 9",
            "issue": "Expected credit loss not properly calculated",
            "recommendation": "Implement proper ECL calculation for trade receivables"
        })

    return recommendations

@router.get("/financial/dashboard")
async def get_financial_dashboard(
    start_date: Optional[date] = Query(None, description="Dashboard start date"),
    end_date: Optional[date] = Query(None, description="Dashboard end date"),
    db: Session = Depends(get_db)
):
    """
    Get Financial Dashboard Data
    """
    try:
        # Initialize services
        ifrs_core = IFRSReportsCore(db)

        # Set default dates if not provided
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = date(end_date.year, 1, 1)  # Start of year

        # Get balance sheet data for assets, liabilities, and equity
        balance_sheet_data = ifrs_core.get_balance_sheet_data(end_date)

        # Get income statement data for revenue and expenses
        from app.services.report_service import ReportService
        income_data = ReportService.get_income_statement_data(db, start_date, end_date)

        # Calculate totals
        total_assets = float(balance_sheet_data.get('totals', {}).get('total_assets', 0))
        total_liabilities = float(balance_sheet_data.get('totals', {}).get('total_liabilities', 0))
        total_equity = float(balance_sheet_data.get('totals', {}).get('total_equity', 0))

        total_revenue = float(income_data.get('total_revenue', 0))
        total_expenses = float(income_data.get('total_expenses', 0))
        net_profit = total_revenue - total_expenses

        # Get cash flow (simplified - using cash accounts balance)
        cash_flow = 0.0
        try:
            # Get cash accounts from balance sheet
            current_assets = balance_sheet_data.get('assets', {}).get('current_assets', [])
            for asset in current_assets:
                if 'cash' in asset.get('account_name', '').lower() or 'bank' in asset.get('account_name', '').lower():
                    cash_flow += float(asset.get('amount', 0))
        except:
            pass

        return {
            "success": True,
            "data": {
                "total_revenue": total_revenue,
                "total_expenses": total_expenses,
                "net_profit": net_profit,
                "cash_flow": cash_flow,
                "assets": total_assets,
                "liabilities": total_liabilities,
                "equity": total_equity
            },
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating financial dashboard: {str(e)}")


# ------------------------ IFRS Core Financial Statements ------------------------

def _parse_dates(start_date: Optional[date], end_date: Optional[date]):
    from datetime import date as dt_date
    today = dt_date.today()
    if not end_date:
        end_date = today
    if not start_date:
        # default to month start
        start_date = end_date.replace(day=1)
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    return start_date, end_date


def _sum(entries, attr):
    total = 0
    for e in entries:
        v = getattr(e, attr, 0) or 0
        try:
            total += float(v)
        except Exception:
            pass
    return total


def _account_side(entry):
    # Determine natural balance side (simplified)
    code = getattr(entry, 'accounting_code', None)
    t = (getattr(code, 'account_type', '') or '').lower()
    if t in ("asset", "expense", "cost_of_goods_sold"):  # debit-nature
        return 'debit'
    return 'credit'


def _net_balance(entry):
    debit = float(entry.debit_amount or 0)
    credit = float(entry.credit_amount or 0)
    side = _account_side(entry)
    if side == 'debit':
        return debit - credit
    return credit - debit


@router.get("/income-statement")
async def get_income_statement(
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    export: Optional[str] = Query(None, description="Export format: pdf|xlsx"),
    include_logo: bool = Query(True, description="Include logo"),
    include_watermark: bool = Query(True, description="Include watermark"),
    watermark_text: Optional[str] = Query(None, description="Override watermark text"),
    db: Session = Depends(get_db)
):
    """IFRS-style Income Statement (Statement of Profit or Loss)"""
    try:
        from app.models.accounting import JournalEntry, AccountingCode
        s, e = _parse_dates(start_date, end_date)

        entries = db.query(JournalEntry).filter(JournalEntry.date >= s, JournalEntry.date <= e).all()
        by_account = {}
        for je in entries:
            code = je.accounting_code
            if not code:
                continue
            acct = by_account.setdefault(code.id, {"code": code.code, "name": code.name, "type": getattr(code, 'account_type', None), "balance": 0})
            acct['balance'] += _net_balance(je)

        revenue_total = 0; cogs_total = 0; expense_total = 0; other_income = 0; other_expense = 0
        lines = []
        for acct in by_account.values():
            t = (acct.get('type') or '').lower()
            bal = acct['balance']
            if t in ('revenue','income'):
                revenue_total += bal
            elif t in ('cogs','cost_of_goods_sold'):
                cogs_total += bal
            elif t in ('expense','operating_expense'):
                expense_total += bal
            elif 'other' in t and 'expense' in t:
                other_expense += bal
            elif 'other' in t and ('income' in t or 'revenue' in t):
                other_income += bal
            lines.append(acct)

        gross_profit = revenue_total - cogs_total
        operating_profit = gross_profit - expense_total
        profit_before_tax = operating_profit + other_income - other_expense
        tax_expense = 0  # placeholder
        net_profit = profit_before_tax - tax_expense

        payload = {
            "period": {"start": s.isoformat(), "end": e.isoformat()},
            "revenue": revenue_total,
            "cogs": cogs_total,
            "gross_profit": gross_profit,
            "operating_expenses": expense_total,
            "operating_profit": operating_profit,
            "other_income": other_income,
            "other_expenses": other_expense,
            "profit_before_tax": profit_before_tax,
            "tax_expense": tax_expense,
            "net_profit": net_profit,
            "accounts": lines,
            "ifrs_standards": ["IAS 1", "IAS 12 (placeholder for tax)"]
        }
        if export:
            if export.lower() == 'pdf':
                from app.services.report_export_utils import export_simple_table_pdf
                cols = ["Code","Name","Type","Balance"]
                rows = [[a['code'], a['name'], a.get('type'), f"{a['balance']:,.2f}"] for a in lines]
                buf = export_simple_table_pdf("Income Statement", payload['period'], cols, rows, include_logo=include_logo, include_watermark=include_watermark, watermark_text=watermark_text)
                fname = f"income_statement_{s.isoformat()}_{e.isoformat()}.pdf"
                return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={fname}"})
            if export.lower() == 'xlsx':
                import pandas as pd
                from io import BytesIO
                from app.core.config import settings
                wb = BytesIO()
                with pd.ExcelWriter(wb, engine='openpyxl') as writer:
                    pd.DataFrame([[k,v] for k,v in payload.items() if k not in ('accounts','ifrs_standards','period')], columns=['Metric','Value']).to_excel(writer, sheet_name='Summary', index=False)
                    acc_df = pd.DataFrame([[a['code'], a['name'], a.get('type'), a['balance']] for a in lines], columns=['Code','Name','Type','Balance'])
                    acc_df.to_excel(writer, sheet_name='Accounts', index=False)
                    meta_df = pd.DataFrame([
                        ['Period Start', payload['period']['start']],
                        ['Period End', payload['period']['end']],
                        ['Standards', ', '.join(payload['ifrs_standards'])],
                        ['Copyright', 'COMPUTING NETWORKING PRINTING SOLUTIONS PTY LTD TEL 74818826 77122880 BOTSWANA']
                    ], columns=['Key','Value'])
                    meta_df.to_excel(writer, sheet_name='Branding', index=False)
                wb.seek(0)
                fname = f"income_statement_{s.isoformat()}_{e.isoformat()}.xlsx"
                return StreamingResponse(wb, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={fname}"})
        return {"success": True, "data": payload}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating income statement: {str(e)}")


@router.post("/generic-report/export")
async def export_generic_report(
    payload: Dict[str, Any],
    export: Optional[str] = Query(None, description="Export format: pdf|xlsx"),
    include_logo: bool = Query(True, description="Include logo"),
    include_watermark: bool = Query(True, description="Include watermark"),
    watermark_text: Optional[str] = Query(None, description="Override watermark text")
):
    """Generic key-value hierarchical report exporter.
    Accepts arbitrary JSON. Optional top-level 'title' and 'period' keys; if absent we'll synthesize.
    Remaining structure is flattened (2-3 levels) to a simple table for PDF/XLSX export.
    Useful to quickly extend branding-aware exports to new reports without bespoke code.
    """
    try:
        raw_bytes = json.dumps(payload).encode('utf-8')
        GENERIC_REPORT_SIZE_BYTES.observe(len(raw_bytes))
        if len(raw_bytes) > settings.generic_report_max_bytes:
            raise HTTPException(status_code=413, detail=f"Payload exceeds max size {settings.generic_report_max_bytes} bytes")

        # Meta key allowlist
        allowed_meta = {k.strip() for k in settings.generic_report_allowed_meta_keys.split(',') if k.strip()}
        title = str(payload.get('title') or 'Generic Report')
        period = payload.get('period') or { 'start': datetime.now().date().isoformat(), 'end': datetime.now().date().isoformat() }
        if 'data' in payload:
            data_section = payload['data']
        else:
            data_section = {k:v for k,v in payload.items() if k not in allowed_meta}

        # Compute cache key (structure + export + options)
        import hashlib
        cache_basis = json.dumps({"title": title, "period": period, "data": data_section}, sort_keys=True)
        cache_key = hashlib.sha256((cache_basis + (export or '') + str(include_logo) + str(include_watermark) + (watermark_text or '')).encode('utf-8')).hexdigest()

        # Purge expired entries opportunistically
        now_ts = datetime.now().timestamp()
        ttl = settings.generic_report_cache_ttl_seconds
        to_delete = [k for k,(ts,_) in _GENERIC_REPORT_CACHE.items() if now_ts - ts > ttl]
        for k in to_delete:
            _GENERIC_REPORT_CACHE.pop(k, None)

        cache_hit = False
        if export:
            # Redis first
            if redis_available():
                r = get_redis()
                if r:
                    cached = r.get(f"genrep:{cache_key}")
                    if cached:
                        # format|filename|binary
                        try:
                            # First 2 lines meta separated by \n then raw bytes after a sentinel
                            # Simpler: store meta dict + bytes in one pickle? Keep pure bytes to avoid pickle risk. Use a simple delimiter.
                            # Structure: b"FMT:" + fmt + b"\nNAME:" + fname + b"\n\n" + data
                            raw: bytes = cached  # type: ignore
                            if raw.startswith(b'FMT:'):
                                header, body = raw.split(b"\n\n",1)
                                parts = header.split(b"\n")
                                fmt_line = parts[0][4:].decode()
                                name_line = parts[1][5:].decode() if len(parts)>1 and parts[1].startswith(b'NAME:') else f"report.{fmt_line}"
                                media_type = 'application/pdf' if fmt_line=='pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                                cache_hit = True
                                resp = StreamingResponse(BytesIO(body), media_type=media_type, headers={"Content-Disposition": f"attachment; filename={name_line}"})
                                resp.headers['X-Cache'] = 'HIT'
                                resp.headers['X-Cache-Backend'] = 'redis'
                                return resp
                        except Exception:
                            pass
            else:
                if cache_key in _GENERIC_REPORT_CACHE:
                    cached_media_type, cached_bytes, cached_fname = _GENERIC_REPORT_CACHE[cache_key][1]
                    cache_hit = True
                    resp = StreamingResponse(BytesIO(cached_bytes), media_type=cached_media_type, headers={"Content-Disposition": f"attachment; filename={cached_fname}"})
                    resp.headers['X-Cache'] = 'HIT'
                    resp.headers['X-Cache-Backend'] = 'memory'
                    return resp

        # Flatten and validate row count
        flat_rows = flatten_dict(data_section, max_depth=3)
        if len(flat_rows) > settings.generic_report_max_flat_rows:
            raise HTTPException(status_code=422, detail=f"Flattened rows exceed limit {settings.generic_report_max_flat_rows}")
        GENERIC_REPORT_FLAT_ROWS.observe(len(flat_rows))

        if export:
            fmt = export.lower()
            if fmt == 'pdf':
                buf = export_key_value_pdf(title, period, data_section, include_logo=include_logo, include_watermark=include_watermark, watermark_text=watermark_text)
                content = buf.getvalue()
                fname = f"{title.lower().replace(' ','_')}.pdf"
                if redis_available():
                    r = get_redis()
                    if r:
                        r.setex(f"genrep:{cache_key}", ttl, b"FMT:pdf\nNAME:"+fname.encode()+b"\n\n"+content)
                else:
                    _GENERIC_REPORT_CACHE[cache_key] = (now_ts, ('application/pdf', content, fname))
                set_cache_size(len(_GENERIC_REPORT_CACHE))
                buf.seek(0)
                resp = StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={fname}"})
                resp.headers['X-Cache'] = 'MISS'
                resp.headers['X-Cache-Backend'] = 'redis' if redis_available() else 'memory'
                return resp
            if fmt == 'xlsx':
                import pandas as pd
                df = pd.DataFrame(flat_rows, columns=['Key','Value'])
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Data', index=False)
                    meta_df = pd.DataFrame([
                        ['Title', title],
                        ['Period Start', period.get('start')],
                        ['Period End', period.get('end')],
                        ['Flattened Rows', len(flat_rows)],
                        ['Generated At', datetime.now().isoformat()],
                        ['Cached', 'False'],
                        ['Copyright', 'COMPUTING NETWORKING PRINTING SOLUTIONS PTY LTD TEL 74818826 77122880 BOTSWANA']
                    ], columns=['Key','Value'])
                    meta_df.to_excel(writer, sheet_name='Meta', index=False)
                output.seek(0)
                content = output.getvalue()
                fname = f"{title.lower().replace(' ','_')}.xlsx"
                if redis_available():
                    r = get_redis()
                    if r:
                        r.setex(f"genrep:{cache_key}", ttl, b"FMT:xlsx\nNAME:"+fname.encode()+b"\n\n"+content)
                else:
                    _GENERIC_REPORT_CACHE[cache_key] = (now_ts, ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', content, fname))
                set_cache_size(len(_GENERIC_REPORT_CACHE))
                output.seek(0)
                resp = StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={fname}"})
                resp.headers['X-Cache'] = 'MISS'
                resp.headers['X-Cache-Backend'] = 'redis' if redis_available() else 'memory'
                return resp
        base_response = {"title": title, "period": period, "flat_rows": len(flat_rows), "data": data_section}
        base_response['cache_backend'] = 'redis' if redis_available() else 'memory'
        base_response['cache_hit'] = cache_hit
        GENERIC_REPORT_REQUESTS.labels(format=export or 'json', cache_hit=str(cache_hit).lower(), backend=base_response['cache_backend']).inc()
        return base_response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting generic report: {str(e)}")








@router.get("/cash-flow-statement")
async def get_cash_flow_statement(
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    export: Optional[str] = Query(None, description="Export format: pdf|xlsx"),
    include_logo: bool = Query(True, description="Include logo"),
    include_watermark: bool = Query(True, description="Include watermark"),
    watermark_text: Optional[str] = Query(None, description="Override watermark text"),
    db: Session = Depends(get_db)
):
    """Cash Flow Statement (enhanced)

    Operating cash flows derived from:
      - Customer cash collections (Sales amount_tendered where date in range)
      - Supplier cash payments (Purchase amount_paid in range)
      - Changes in Accounts Receivable (invoices outstanding) and Accounts Payable (purchases unpaid)
    Investing & Financing still placeholders until asset acquisitions / debt/equity modules integrated.
    """
    try:
        from app.models import sales as sales_models
        from app.models import purchases as purchase_models
        from sqlalchemy import func
        s, e = _parse_dates(start_date, end_date)

        Sale = getattr(sales_models, 'Sale')
        Invoice = getattr(sales_models, 'Invoice')
        Purchase = getattr(purchase_models, 'Purchase')

        # Customer cash collections (assume amount_tendered reflects cash inflow at sale time)
        sales_cash = db.query(func.coalesce(func.sum(Sale.amount_tendered), 0)).filter(Sale.date >= s, Sale.date <= e).scalar() or 0.0

        # Supplier cash payments (amount_paid on purchases within window)
        purchase_cash_out = db.query(func.coalesce(func.sum(Purchase.amount_paid), 0)).filter(Purchase.purchase_date >= s, Purchase.purchase_date <= e).scalar() or 0.0

        # AR opening & closing (based on outstanding invoices)
        def outstanding_ar(as_of):
            invs = db.query(Invoice.total_amount, Invoice.amount_paid).filter(Invoice.date <= as_of).all()
            total = 0.0
            for total_amt, paid in invs:
                total += max(float(total_amt or 0) - float(paid or 0), 0.0)
            return total
        ar_open = outstanding_ar(s)
        ar_close = outstanding_ar(e)
        delta_ar = ar_close - ar_open  # increase in AR consumes cash

        # AP opening & closing (based on purchases outstanding)
        def outstanding_ap(as_of):
            pur = db.query(Purchase.total_amount, Purchase.amount_paid).filter(Purchase.purchase_date <= as_of).all()
            total = 0.0
            for total_amt, paid in pur:
                total += max(float(total_amt or 0) - float(paid or 0), 0.0)
            return total
        ap_open = outstanding_ap(s)
        ap_close = outstanding_ap(e)
        delta_ap = ap_close - ap_open  # increase in AP provides cash

        # Operating cash flow: collections - payments - increase in AR + increase in AP
        operating_cash_flow = float(sales_cash) - float(purchase_cash_out) - delta_ar + delta_ap
        investing_cash_flow = 0.0
        financing_cash_flow = 0.0
        net_cash_flow = operating_cash_flow + investing_cash_flow + financing_cash_flow

        payload = {
            "period": {"start": s.isoformat(), "end": e.isoformat()},
            "components": {
                "sales_cash_collections": float(sales_cash),
                "purchase_cash_payments": float(purchase_cash_out),
                "ar_open": round(ar_open,2),
                "ar_close": round(ar_close,2),
                "delta_ar": round(delta_ar,2),
                "ap_open": round(ap_open,2),
                "ap_close": round(ap_close,2),
                "delta_ap": round(delta_ap,2),
            },
            "operating_cash_flow": round(operating_cash_flow,2),
            "investing_cash_flow": investing_cash_flow,
            "financing_cash_flow": financing_cash_flow,
            "net_cash_flow": round(net_cash_flow,2),
            "ifrs_standards": ["IAS 7"],
            "method": "direct+working_cap_adjustments"
        }
        if export:
            if export.lower()=="pdf":
                from app.services.report_export_utils import export_simple_table_pdf
                cols=["Metric","Amount"]
                comp = payload['components']
                rows=[
                    ["Sales Cash Collections", f"{comp['sales_cash_collections']:,.2f}"],
                    ["Purchase Cash Payments", f"{comp['purchase_cash_payments']:,.2f}"],
                    ["Δ Accounts Receivable", f"{comp['delta_ar']:,.2f}"],
                    ["Δ Accounts Payable", f"{comp['delta_ap']:,.2f}"],
                    ["Operating Cash Flow", f"{payload['operating_cash_flow']:,.2f}"],
                    ["Investing Cash Flow", f"{payload['investing_cash_flow']:,.2f}"],
                    ["Financing Cash Flow", f"{payload['financing_cash_flow']:,.2f}"],
                    ["Net Cash Flow", f"{payload['net_cash_flow']:,.2f}"],
                ]
                buf = export_simple_table_pdf("Cash Flow Statement", payload['period'], cols, rows, include_logo=include_logo, include_watermark=include_watermark, watermark_text=watermark_text)
                fname=f"cash_flow_statement_{s.isoformat()}_{e.isoformat()}.pdf"
                return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={fname}"})
            if export.lower()=="xlsx":
                import pandas as pd
                from io import BytesIO
                wb = BytesIO()
                with pd.ExcelWriter(wb, engine='openpyxl') as writer:
                    pd.DataFrame([
                        ['Period Start', payload['period']['start']],
                        ['Period End', payload['period']['end']],
                        ['Sales Cash Collections', payload['components']['sales_cash_collections']],
                        ['Purchase Cash Payments', payload['components']['purchase_cash_payments']],
                        ['Δ Accounts Receivable', payload['components']['delta_ar']],
                        ['Δ Accounts Payable', payload['components']['delta_ap']],
                        ['Operating Cash Flow', payload['operating_cash_flow']],
                        ['Investing Cash Flow', payload['investing_cash_flow']],
                        ['Financing Cash Flow', payload['financing_cash_flow']],
                        ['Net Cash Flow', payload['net_cash_flow']],
                        ['Standards', ', '.join(payload['ifrs_standards'])],
                        ['Method', payload['method']],
                        ['Copyright', 'COMPUTING NETWORKING PRINTING SOLUTIONS PTY LTD TEL 74818826 77122880 BOTSWANA']
                    ], columns=['Metric','Value']).to_excel(writer, sheet_name='Summary', index=False)
                wb.seek(0)
                fname=f"cash_flow_statement_{s.isoformat()}_{e.isoformat()}.xlsx"
                return StreamingResponse(wb, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename={fname}"})
        return {"success": True, "data": payload}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating cash flow statement: {str(e)}")


@router.get("/profit-loss")
async def get_profit_loss_alias(
    start_date: Optional[date] = Query(None, description="Start date"),
    end_date: Optional[date] = Query(None, description="End date"),
    db: Session = Depends(get_db)
):
    """Alias for income statement for UI convenience"""
    return await get_income_statement(start_date=start_date, end_date=end_date, db=db)

@router.get("/performance/dashboard")
async def get_performance_dashboard(
    start_date: Optional[date] = Query(None, description="Dashboard start date"),
    end_date: Optional[date] = Query(None, description="Dashboard end date"),
    db: Session = Depends(get_db)
):
    """
    Get Performance Dashboard Data
    """
    try:
        # Simple mock dashboard data for now
        return {
            "success": True,
            "data": {
                "sales_growth": 0.0,
                "profit_margin": 0.0,
                "inventory_turnover": 0.0,
                "debt_ratio": 0.0,
                "current_ratio": 0.0,
                "return_on_assets": 0.0
            },
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating performance dashboard: {str(e)}")

@router.get("/debug/database-stats")
async def get_database_stats(db: Session = Depends(get_db)):
    """Debug endpoint to check what data exists in the database"""
    from app.models.accounting import AccountingCode, JournalEntry

    try:
        accounting_codes_count = db.query(AccountingCode).count()
        journal_entries_count = db.query(JournalEntry).count()

        # Get some sample data
        sample_codes = db.query(AccountingCode).limit(5).all()
        sample_entries = db.query(JournalEntry).limit(5).all()

        return {
            "status": "success",
            "data": {
                "accounting_codes_count": accounting_codes_count,
                "journal_entries_count": journal_entries_count,
                "sample_codes": [
                    {
                        "id": getattr(code, 'id', 'N/A'),
                        "code": getattr(code, 'code', 'N/A'),
                        "name": getattr(code, 'name', 'N/A'),
                        "account_type": getattr(code, 'account_type', 'N/A')
                    } for code in sample_codes
                ],
                "sample_entries": [
                    {
                        "id": entry.id,
                        "accounting_code_id": entry.accounting_code_id,
                        "debit_amount": float(entry.debit_amount or 0),
                        "credit_amount": float(entry.credit_amount or 0),
                        "date": entry.date.isoformat() if entry.date else None
                    } for entry in sample_entries
                ]
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


@router.get("/debug/raw-accounting-data")
async def get_raw_accounting_data(db: Session = Depends(get_db)):
    """Get comprehensive accounting data to debug trial balance issues"""
    try:
        from app.models.accounting import AccountingCode, JournalEntry

        # Get ALL accounting codes
        all_codes = db.query(AccountingCode).all()
        codes_data = []

        for code in all_codes:
            # Get journal entries for this code
            entries = db.query(JournalEntry).filter(
                JournalEntry.accounting_code_id == code.id
            ).all()

            total_debits = sum(float(entry.debit_amount or 0) for entry in entries)
            total_credits = sum(float(entry.credit_amount or 0) for entry in entries)

            codes_data.append({
                "id": code.id,
                "code": code.code,
                "name": code.name,
                "account_type": str(code.account_type) if code.account_type else None,
                "category": code.category,
                "stored_balance": float(code.balance or 0),
                "stored_total_debits": float(code.total_debits or 0),
                "stored_total_credits": float(code.total_credits or 0),
                "calculated_debits": total_debits,
                "calculated_credits": total_credits,
                "calculated_balance": total_debits - total_credits if str(code.account_type) in ['Asset', 'Expense'] else total_credits - total_debits,
                "journal_entries_count": len(entries)
            })

        # Get all journal entries for overview
        all_entries = db.query(JournalEntry).limit(10).all()
        entries_sample = [
            {
                "id": entry.id,
                "date": str(entry.date),
                "accounting_code_id": entry.accounting_code_id,
                "debit_amount": float(entry.debit_amount or 0),
                "credit_amount": float(entry.credit_amount or 0),
                "description": entry.description,
                "narration": entry.narration
            } for entry in all_entries
        ]

        return {
            "success": True,
            "data": {
                "total_accounting_codes": len(codes_data),
                "total_journal_entries": db.query(JournalEntry).count(),
                "accounting_codes": codes_data,
                "sample_journal_entries": entries_sample
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/management/kpi-metrics")
async def get_kpi_metrics(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    branch_id: Optional[str] = Query(None, description="Branch ID filter"),
    db: Session = Depends(get_db)
):
    """
    Get Key Performance Indicators for management dashboard
    """
    try:
        # Set default date range if not provided
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # Convert dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        # Get real data from database
        from sqlalchemy import func, and_

        # Revenue from sales
        total_revenue = db.query(func.sum(Sale.total_amount)).filter(
            and_(Sale.date >= start_dt, Sale.date <= end_dt)
        ).scalar() or 0.0

        # Expenses from journal entries (expense accounts)
        expense_accounts = db.query(AccountingCode).filter(
            AccountingCode.account_type.in_(['expense', 'cost_of_goods_sold'])
        ).all()
        expense_account_ids = [acc.id for acc in expense_accounts]

        total_expenses = db.query(func.sum(JournalEntry.debit_amount - JournalEntry.credit_amount)).filter(
            and_(
                JournalEntry.accounting_code_id.in_(expense_account_ids),
                JournalEntry.date >= start_dt,
                JournalEntry.date <= end_dt
            )
        ).scalar() or 0.0

        # Calculate net profit
        net_profit = float(total_revenue) - float(total_expenses)

        # Calculate profit margin
        profit_margin = (net_profit / float(total_revenue) * 100) if total_revenue > 0 else 0.0

        # Calculate trends (compare with previous period)
        prev_start = start_dt - timedelta(days=(end_dt - start_dt).days + 1)
        prev_end = start_dt - timedelta(days=1)

        prev_revenue = db.query(func.sum(Sale.total_amount)).filter(
            and_(Sale.date >= prev_start, Sale.date <= prev_end)
        ).scalar() or 0.0

        prev_expenses = db.query(func.sum(JournalEntry.debit_amount - JournalEntry.credit_amount)).filter(
            and_(
                JournalEntry.accounting_code_id.in_(expense_account_ids),
                JournalEntry.date >= prev_start,
                JournalEntry.date <= prev_end
            )
        ).scalar() or 0.0

        prev_profit = float(prev_revenue) - float(prev_expenses)

        # Calculate trend percentages
        revenue_trend = ((float(total_revenue) - float(prev_revenue)) / float(prev_revenue) * 100) if prev_revenue > 0 else 0.0
        profit_trend = ((net_profit - prev_profit) / abs(prev_profit) * 100) if prev_profit != 0 else 0.0
        expense_trend = ((float(total_expenses) - float(prev_expenses)) / float(prev_expenses) * 100) if prev_expenses > 0 else 0.0
        margin_trend = (profit_margin - (prev_profit / float(prev_revenue) * 100 if prev_revenue > 0 else 0)) if prev_revenue > 0 else 0.0

        return {
            "total_revenue": float(total_revenue),
            "net_profit": float(net_profit),
            "total_expenses": float(total_expenses),
            "profit_margin": round(profit_margin, 1),
            "revenue_trend": round(revenue_trend, 1),
            "profit_trend": round(profit_trend, 1),
            "expense_trend": round(expense_trend, 1),
            "margin_trend": round(margin_trend, 1),
            "period_start": start_date,
            "period_end": end_date
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating KPI metrics: {str(e)}")

@router.get("/management/financial-summary")
async def get_financial_summary(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    branch_id: Optional[str] = Query(None, description="Branch ID filter"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive financial summary for management reports
    """
    try:
        # Set default date range if not provided (last 30 days)
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # Convert to datetime boundaries
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        # Ensure end date includes entire day
        end_dt_inclusive = end_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Determine comparison window length
        period_delta = end_dt_inclusive - start_dt
        prev_end = start_dt - timedelta(seconds=1)
        prev_start = prev_end - period_delta

        # Helper functions
        def sum_sales(start_bound, end_bound):
            sale_total = db.query(func.sum(Sale.total_amount)).filter(
                Sale.date >= start_bound, Sale.date <= end_bound
            )
            if branch_id:
                sale_total = sale_total.filter(Sale.branch_id == branch_id)
            sale_total = sale_total.scalar() or 0

            invoice_start = _ensure_date(start_bound)
            invoice_end = _ensure_date(end_bound)
            invoice_total = db.query(func.sum(Invoice.total_amount)).filter(
                Invoice.date >= invoice_start, Invoice.date <= invoice_end
            )
            if branch_id:
                invoice_total = invoice_total.filter(Invoice.branch_id == branch_id)
            invoice_total = invoice_total.scalar() or 0
            return float(sale_total) + float(invoice_total)

        def _ensure_date(value):
            if isinstance(value, datetime):
                return value.date()
            return value

        def sum_journal(account_types, start_bound, end_bound):
            codes = db.query(AccountingCode.id).filter(AccountingCode.account_type.in_(account_types))
            code_ids = [row.id for row in codes]
            if not code_ids:
                return 0.0
            total = db.query(func.sum(JournalEntry.debit_amount - JournalEntry.credit_amount)).filter(
                JournalEntry.accounting_code_id.in_(code_ids),
                JournalEntry.date >= _ensure_date(start_bound),
                JournalEntry.date <= _ensure_date(end_bound)
            )
            if branch_id:
                total = total.filter(JournalEntry.branch_id == branch_id)
            return float(total.scalar() or 0)

        def percent_change(current, previous):
            if previous == 0:
                return 0.0
            return ((current - previous) / abs(previous)) * 100

        def trend_direction(current, previous):
            if current > previous:
                return "up"
            if current < previous:
                return "down"
            return "flat"

        # Current period calculations
        current_revenue = sum_sales(start_dt, end_dt_inclusive)
        current_cogs = sum_journal(['cost_of_goods_sold'], start_dt, end_dt_inclusive)
        current_operating = sum_journal(['expense'], start_dt, end_dt_inclusive)
        current_gross_profit = current_revenue - current_cogs
        current_net_profit = current_gross_profit - current_operating
        current_margin = (current_net_profit / current_revenue * 100) if current_revenue else 0.0

        # Previous period calculations
        previous_revenue = sum_sales(prev_start, prev_end)
        previous_cogs = sum_journal(['cost_of_goods_sold'], prev_start, prev_end)
        previous_operating = sum_journal(['expense'], prev_start, prev_end)
        previous_gross_profit = previous_revenue - previous_cogs
        previous_net_profit = previous_gross_profit - previous_operating
        previous_margin = (previous_net_profit / previous_revenue * 100) if previous_revenue else 0.0

        financial_data = {
            "gross_revenue": {
                "current": current_revenue,
                "previous": previous_revenue,
                "change": percent_change(current_revenue, previous_revenue),
                "trend": trend_direction(current_revenue, previous_revenue)
            },
            "cost_of_goods": {
                "current": current_cogs,
                "previous": previous_cogs,
                "change": percent_change(current_cogs, previous_cogs),
                "trend": trend_direction(current_cogs, previous_cogs)
            },
            "gross_profit": {
                "current": current_gross_profit,
                "previous": previous_gross_profit,
                "change": percent_change(current_gross_profit, previous_gross_profit),
                "trend": trend_direction(current_gross_profit, previous_gross_profit)
            },
            "operating_expenses": {
                "current": current_operating,
                "previous": previous_operating,
                "change": percent_change(current_operating, previous_operating),
                "trend": trend_direction(current_operating, previous_operating)
            },
            "net_profit": {
                "current": current_net_profit,
                "previous": previous_net_profit,
                "change": percent_change(current_net_profit, previous_net_profit),
                "trend": trend_direction(current_net_profit, previous_net_profit)
            },
            "profit_margin": {
                "current": current_margin,
                "previous": previous_margin,
                "change": percent_change(current_margin, previous_margin),
                "trend": trend_direction(current_margin, previous_margin)
            }
        }

        return {
            "financial_data": financial_data,
            "period_start": start_date,
            "period_end": end_date
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating financial summary: {str(e)}")

@router.get("/management/sales-report")
async def get_sales_report(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    branch_id: Optional[str] = Query(None, description="Branch ID filter"),
    db: Session = Depends(get_db)
):
    """
    Get sales performance report for management
    """
    try:
        # Parse dates
        start_date_obj = None
        end_date_obj = None

        if start_date:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Initialize sales reports service
        sales_service = SalesReportsService(db)

        # Generate comprehensive sales report
        sales_data = sales_service.generate_sales_summary(
            start_date=start_date_obj,
            end_date=end_date_obj,
            branch_id=branch_id
        )

        return {
            "sales_data": sales_data,
            "period_start": sales_data["period_start"],
            "period_end": sales_data["period_end"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating sales report: {str(e)}")

@router.get("/management/customer-analysis")
async def get_customer_analysis(
    branch_id: Optional[str] = Query(None, description="Branch ID filter"),
    db: Session = Depends(get_db)
):
    """
    Get customer analysis report for management
    """
    try:
        sales_service = SalesReportsService(db)
        customer_data = sales_service.get_customer_analysis(branch_id=branch_id)

        return {
            "success": True,
            "data": customer_data,
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating customer analysis: {str(e)}")

@router.get("/management/performance-metrics")
async def get_performance_metrics(
    branch_id: Optional[str] = Query(None, description="Branch ID filter"),
    db: Session = Depends(get_db)
):
    """
    Get performance dashboard metrics
    """
    try:
        sales_service = SalesReportsService(db)
        performance_data = sales_service.get_performance_metrics(branch_id=branch_id)

        return {
            "success": True,
            "data": performance_data,
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating performance metrics: {str(e)}")

@router.get("/management/inventory-report", response_model=InventoryReportResponse)
async def get_inventory_report(
    branch_id: Optional[str] = Query(None, description="Branch ID filter"),
    db: Session = Depends(get_db)
):
    """
    Get inventory status report for management
    """
    try:
        from app.services.inventory_service import InventoryService
        from app.services.app_setting_service import AppSettingService

        # Use default branch if not specified
        if not branch_id:
            # Attempt to get default branch from settings, fallback to hardcoded ID
            try:
                settings_service = AppSettingService(db)
                branch_id = settings_service.get_setting_by_key("default_branch_id")
                if not branch_id:
                    branch_id = "8f4aaa72-103b-4f40-b586-096675cfb4bf"
            except Exception:
                branch_id = "8f4aaa72-103b-4f40-b586-096675cfb4bf"

        inventory_service = InventoryService(db)
        inventory_data = inventory_service.get_inventory_summary(branch_id)

        # Get low stock alerts
        low_stock_alerts = inventory_service.get_low_stock_products(branch_id)

        # Get category analysis
        category_analysis = inventory_service.get_category_analysis(branch_id)
        categories = category_analysis.get('data', {}).get('categories', [])

        # Get stock movement data
        movement_report = inventory_service.get_stock_movement_report(branch_id)
        stock_movement_data = movement_report.get('data', [])

        # Aggregate stock movement by month for chart
        from collections import defaultdict
        stock_movement_agg = defaultdict(lambda: {'stock_in': 0, 'stock_out': 0})
        for entry in stock_movement_data:
            try:
                # Assuming entry['date'] is a string like 'YYYY-MM-DD...'
                month = entry['date'][:7]
                if entry['transaction_type'] in ['goods_receipt', 'return', 'opening_stock', 'production_receipt']:
                    stock_movement_agg[month]['stock_in'] += entry['quantity']
                elif entry['transaction_type'] in ['sale', 'damage', 'theft', 'adjustment', 'issue_to_wip']:
                    stock_movement_agg[month]['stock_out'] += abs(entry['quantity'])
            except (KeyError, TypeError):
                # Skip malformed entries
                continue

        stock_movement_chart_data = [
            {'month': month, 'stock_in': data['stock_in'], 'stock_out': data['stock_out']}
            for month, data in sorted(stock_movement_agg.items())
        ]

        # Transform data to match expected response format
        formatted_data = {
            "total_products": inventory_data.get('total_products', 0),
            "total_value": inventory_data.get('total_value', 0),
            "low_stock_items": inventory_data.get('low_stock_count', 0),
            "out_of_stock_items": inventory_data.get('out_of_stock_count', 0),
            "top_products": [
                {
                    "name": product.get('name'),
                    "stock_level": product.get('quantity'),
                    "value": product.get('value')
                }
                for product in sorted(inventory_data.get('products', []), key=lambda x: x.get('value', 0), reverse=True)[:5]
            ],
            "stock_movement": stock_movement_chart_data,
            "low_stock_alerts": [
                {
                    "name": alert.get('name'),
                    "sku": alert.get('sku'),
                    "quantity": alert.get('current_quantity'),
                    "reorder_level": alert.get('reorder_level'),
                    "cost_price": alert.get('cost_price')
                }
                for alert in low_stock_alerts
            ],
            "categories": categories,
            "summary": {
                "total_inventory_value": inventory_data.get('total_value', 0),
                "total_products": inventory_data.get('total_products', 0)
            }
        }

        return InventoryReportResponse(
            report_type="stock_levels",
            reporting_date=datetime.now(),
            total_products=formatted_data['total_products'],
            total_value=formatted_data['total_value'],
            low_stock_items=formatted_data['low_stock_items'],
            out_of_stock_items=formatted_data['out_of_stock_items'],
            overstocked_items=0,
            items_received=sum(m['stock_in'] for m in stock_movement_chart_data),
            items_sold=sum(m['stock_out'] for m in stock_movement_chart_data),
            items_adjusted=0,
            fifo_value=formatted_data['total_value'],
            lifo_value=formatted_data['total_value'],
            average_cost_value=formatted_data['total_value'],
            aging_data=None,
            report_data=formatted_data,
            charts_data=None,
            id=str(uuid.uuid4()),
            status="completed",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating inventory report: {str(e)}")

@router.get("/cogs/monthly")
async def get_monthly_cogs_report(
    year: int = Query(..., description="Year for the report"),
    month: int = Query(..., description="Month (1-12) for the report"),
    product_id: Optional[str] = Query(None, description="Filter by specific product"),
    category_id: Optional[str] = Query(None, description="Filter by product category"),
    export: Optional[str] = Query(None, description="Export format: pdf|xlsx"),
    db: Session = Depends(get_db)
):
    """
    Get Monthly COGS Report

    Standards: IAS 2 - Inventories (Cost of Goods Sold)
    """
    try:
        if month < 1 or month > 12:
            raise HTTPException(status_code=400, detail="Month must be between 1 and 12")

        cogs_service = COGSReportsService(db)
        report_data = cogs_service.generate_monthly_cogs_report(
            year=year, month=month, product_id=product_id, category_id=category_id
        )

        return {
            "success": True,
            "data": report_data,
            "ifrs_standards": ["IAS 2 - Inventories"],
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating monthly COGS report: {str(e)}")

@router.get("/cogs/quarterly")
async def get_quarterly_cogs_report(
    year: int = Query(..., description="Year for the report"),
    quarter: int = Query(..., description="Quarter (1-4) for the report"),
    product_id: Optional[str] = Query(None, description="Filter by specific product"),
    category_id: Optional[str] = Query(None, description="Filter by product category"),
    export: Optional[str] = Query(None, description="Export format: pdf|xlsx"),
    db: Session = Depends(get_db)
):
    """
    Get Quarterly COGS Report

    Standards: IAS 2 - Inventories (Cost of Goods Sold)
    """
    try:
        if quarter < 1 or quarter > 4:
            raise HTTPException(status_code=400, detail="Quarter must be between 1 and 4")

        cogs_service = COGSReportsService(db)
        report_data = cogs_service.generate_quarterly_cogs_report(
            year=year, quarter=quarter, product_id=product_id, category_id=category_id
        )

        return {
            "success": True,
            "data": report_data,
            "ifrs_standards": ["IAS 2 - Inventories"],
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating quarterly COGS report: {str(e)}")

@router.get("/cogs/annual")
async def get_annual_cogs_report(
    year: int = Query(..., description="Year for the report"),
    product_id: Optional[str] = Query(None, description="Filter by specific product"),
    category_id: Optional[str] = Query(None, description="Filter by product category"),
    export: Optional[str] = Query(None, description="Export format: pdf|xlsx"),
    db: Session = Depends(get_db)
):
    """
    Get Annual COGS Report

    Standards: IAS 2 - Inventories (Cost of Goods Sold)
    """
    try:
        cogs_service = COGSReportsService(db)
        report_data = cogs_service.generate_annual_cogs_report(
            year=year, product_id=product_id, category_id=category_id
        )

        return {
            "success": True,
            "data": report_data,
            "ifrs_standards": ["IAS 2 - Inventories"],
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating annual COGS report: {str(e)}")

@router.get("/cogs/trend-analysis")
async def get_cogs_trend_analysis(
    start_date: date = Query(..., description="Start date for trend analysis"),
    end_date: date = Query(..., description="End date for trend analysis"),
    period_type: str = Query("monthly", description="Period type: monthly or quarterly"),
    product_id: Optional[str] = Query(None, description="Filter by specific product"),
    export: Optional[str] = Query(None, description="Export format: pdf|xlsx"),
    db: Session = Depends(get_db)
):
    """
    Get COGS Trend Analysis

    Standards: IAS 2 - Inventories (Cost Analysis)
    """
    try:
        cogs_service = COGSReportsService(db)
        trend_data = cogs_service.get_cogs_trend_analysis(
            start_date=start_date,
            end_date=end_date,
            period_type=period_type,
            product_id=product_id
        )

        return {
            "success": True,
            "data": trend_data,
            "ifrs_standards": ["IAS 2 - Inventories"],
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating COGS trend analysis: {str(e)}")


@router.get("/financial-statements/balance-sheet", response_model=FinancialReportResponse)
async def get_balance_sheet(
    as_of_date: Optional[date] = Query(None, description="Balance sheet as of date"),
    comparison_date: Optional[date] = Query(None, description="Comparison balance sheet date"),
    include_notes: bool = Query(False, description="Include financial notes"),
    export: Optional[str] = Query(None, description="Export format: pdf|xlsx"),
    db: Session = Depends(get_db)
):
    """
    Generate IFRS-compliant Balance Sheet (Statement of Financial Position)

    Standards: IAS 1 - Presentation of Financial Statements
    """
    try:
        financial_service = FinancialStatementsService(db)
        balance_sheet = financial_service.get_balance_sheet(
            as_of_date=as_of_date,
            comparison_date=comparison_date,
            include_notes=include_notes
        )

        return FinancialReportResponse(
            success=True,
            data=balance_sheet,
            metadata=balance_sheet.metadata,
            ifrs_standards=["IAS 1 - Presentation of Financial Statements"],
            generated_at=datetime.now(),
            export_available=True
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating balance sheet: {str(e)}")


@router.get("/financial-statements/income-statement", response_model=FinancialReportResponse)
async def get_income_statement(
    start_date: Optional[date] = Query(None, description="Period start date"),
    end_date: Optional[date] = Query(None, description="Period end date (defaults to today)"),
    comparison_start_date: Optional[date] = Query(None, description="Comparison period start"),
    comparison_end_date: Optional[date] = Query(None, description="Comparison period end"),
    export: Optional[str] = Query(None, description="Export format: pdf|xlsx"),
    db: Session = Depends(get_db)
):
    """
    Generate IFRS-compliant Income Statement (Profit & Loss)

    Standards: IAS 1 - Presentation of Financial Statements
    """
    try:
        financial_service = FinancialStatementsService(db)
        income_statement = financial_service.get_income_statement(
            start_date=start_date,
            end_date=end_date,
            comparison_start_date=comparison_start_date,
            comparison_end_date=comparison_end_date
        )

        return FinancialReportResponse(
            success=True,
            data=income_statement,
            metadata=income_statement.metadata,
            ifrs_standards=["IAS 1 - Presentation of Financial Statements"],
            generated_at=datetime.now(),
            export_available=True
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating income statement: {str(e)}")


@router.get("/financial-statements/cash-flow", response_model=FinancialReportResponse)
async def get_cash_flow_statement(
    start_date: Optional[date] = Query(None, description="Period start date"),
    end_date: Optional[date] = Query(None, description="Period end date (defaults to today)"),
    method: str = Query("indirect", description="Cash flow method: indirect|direct"),
    export: Optional[str] = Query(None, description="Export format: pdf|xlsx"),
    db: Session = Depends(get_db)
):
    """
    Generate IFRS-compliant Cash Flow Statement

    Standards: IAS 7 - Statement of Cash Flows
    """
    try:
        financial_service = FinancialStatementsService(db)
        cash_flow = financial_service.get_cash_flow_statement(
            start_date=start_date,
            end_date=end_date
        )

        return FinancialReportResponse(
            success=True,
            data=cash_flow,
            metadata=cash_flow.metadata,
            ifrs_standards=["IAS 7 - Statement of Cash Flows"],
            generated_at=datetime.now(),
            export_available=True
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating cash flow statement: {str(e)}")


@router.get("/financial-statements/changes-in-equity", response_model=FinancialReportResponse)
async def get_statement_of_changes_in_equity(
    start_date: Optional[date] = Query(None, description="Period start date"),
    end_date: Optional[date] = Query(None, description="Period end date (defaults to today)"),
    export: Optional[str] = Query(None, description="Export format: pdf|xlsx"),
    db: Session = Depends(get_db)
):
    """
    Generate Statement of Changes in Equity

    Standards: IAS 1 - Presentation of Financial Statements
    """
    try:
        from app.schemas.financial_statements import ReportMetadata, IFRSStandard, ReportPeriodType, CurrencyCode
        import uuid

        financial_service = FinancialStatementsService(db)
        equity_statement = financial_service.get_statement_of_changes_in_equity(
            start_date=start_date,
            end_date=end_date
        )

        # Set default dates if not provided
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = date(end_date.year, 1, 1)  # Start of year

        # Create metadata
        metadata = ReportMetadata(
            report_id=str(uuid.uuid4()),
            report_type="Statement of Changes in Equity",
            company_name="Company Name",  # TODO: Get from settings
            reporting_date=end_date,
            period_start=start_date,
            period_end=end_date,
            period_type=ReportPeriodType.CUSTOM,
            presentation_currency=CurrencyCode.BWP,
            functional_currency=CurrencyCode.BWP,
            ifrs_standards=[IFRSStandard.IAS_1],
            prepared_by="System",
            prepared_at=datetime.now()
        )

        return FinancialReportResponse(
            success=True,
            data=equity_statement,
            metadata=metadata,
            ifrs_standards=[IFRSStandard.IAS_1],
            generated_at=datetime.now()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating statement of changes in equity: {str(e)}")


@router.get("/financial-statements/trial-balance-enhanced", response_model=FinancialReportResponse)
async def get_enhanced_trial_balance(
    as_of_date: Optional[date] = Query(None, description="Trial balance date (defaults to today)"),
    include_zero_balances: bool = Query(False, description="Include accounts with zero balances"),
    account_type_filter: Optional[str] = Query(None, description="Filter by account type"),
    export: Optional[str] = Query(None, description="Export format: pdf|xlsx"),
    db: Session = Depends(get_db)
):
    """
    Generate Enhanced Trial Balance with IFRS compliance

    Standards: IAS 1 - Presentation of Financial Statements
    """
    try:
        financial_service = FinancialStatementsService(db)
        trial_balance = financial_service.get_trial_balance(
            as_of_date=as_of_date,
            include_zero_balances=include_zero_balances
        )

        return FinancialReportResponse(
            success=True,
            data=trial_balance,
            metadata=trial_balance.metadata,
            ifrs_standards=["IAS 1 - Presentation of Financial Statements"],
            generated_at=datetime.now()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating enhanced trial balance: {str(e)}")


@router.get("/financial-statements/complete-package", response_model=FinancialReportResponse)
async def get_complete_financial_package(
    as_of_date: Optional[date] = Query(None, description="Reporting date (defaults to today)"),
    include_comparatives: bool = Query(True, description="Include comparative figures"),
    export: Optional[str] = Query(None, description="Export format: pdf|xlsx"),
    db: Session = Depends(get_db)
):
    """
    Generate Complete Financial Statements Package

    Includes: Balance Sheet, Income Statement, Cash Flow, Changes in Equity, Trial Balance
    Standards: IAS 1, IAS 7 - Complete Set of Financial Statements
    """
    try:
        financial_service = FinancialStatementsService(db)
        financial_package = financial_service.get_financial_report_package(
            as_of_date=as_of_date,
            include_comparatives=include_comparatives
        )

        return FinancialReportResponse(
            success=True,
            data=financial_package.dict(),
            ifrs_standards=[
                "IAS 1 - Presentation of Financial Statements",
                "IAS 7 - Statement of Cash Flows"
            ],
            generated_at=datetime.now(),
            export_available=True
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating complete financial package: {str(e)}")


@router.post("/financial-statements/export")
async def export_financial_statement(
    export_request: ReportExportRequest,
    db: Session = Depends(get_db)
):
    """
    Export financial statements to PDF or Excel

    Supports all financial statement types with various formatting options
    """
    try:
        financial_service = FinancialStatementsService(db)

        # Get the appropriate financial statement based on report type
        if export_request.report_type == "balance_sheet":
            data = financial_service.get_balance_sheet(
                as_of_date=export_request.as_of_date,
                include_notes=export_request.include_notes
            )
        elif export_request.report_type == "income_statement":
            data = financial_service.get_income_statement(
                start_date=export_request.start_date,
                end_date=export_request.end_date
            )
        elif export_request.report_type == "cash_flow":
            data = financial_service.get_cash_flow_statement(
                start_date=export_request.start_date,
                end_date=export_request.end_date
            )
        elif export_request.report_type == "changes_in_equity":
            data = financial_service.get_statement_of_changes_in_equity(
                start_date=export_request.start_date,
                end_date=export_request.end_date
            )
        elif export_request.report_type == "trial_balance":
            data = financial_service.get_trial_balance(
                as_of_date=export_request.as_of_date,
                include_zero_balances=export_request.include_zero_balances
            )
        elif export_request.report_type == "complete_package":
            data = financial_service.get_financial_report_package(
                as_of_date=export_request.as_of_date,
                include_comparatives=export_request.include_comparatives
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid report type")

        # TODO: Implement actual PDF/Excel export logic
        # For now, return the data structure
        return {
            "success": True,
            "message": f"Export functionality for {export_request.format} format will be implemented",
            "data": data.dict(),
            "export_format": export_request.format
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting financial statement: {str(e)}")


@router.get("/financial-statements/summary")
async def get_financial_summary(
    as_of_date: Optional[date] = Query(None, description="Summary date (defaults to today)"),
    db: Session = Depends(get_db)
):
    """
    Get Financial Summary Dashboard

    Provides key financial metrics and ratios for quick overview
    """
    try:
        financial_service = FinancialStatementsService(db)

        # Get balance sheet for ratios
        balance_sheet = financial_service.get_balance_sheet(as_of_date=as_of_date)

        # Get income statement for current year
        year_start = date(as_of_date.year if as_of_date else date.today().year, 1, 1)
        income_statement = financial_service.get_income_statement(
            start_date=year_start,
            end_date=as_of_date
        )

        # Calculate key ratios
        total_assets = balance_sheet.assets.total_assets
        total_liabilities = balance_sheet.liabilities_and_equity.total_liabilities
        total_equity = balance_sheet.liabilities_and_equity.total_equity

        current_assets = balance_sheet.assets.current_assets.subtotal
        current_liabilities = balance_sheet.liabilities_and_equity.current_liabilities.subtotal

        # Financial ratios
        current_ratio = float(current_assets / current_liabilities) if current_liabilities > 0 else 0
        debt_to_equity = float(total_liabilities / total_equity) if total_equity > 0 else 0
        debt_to_assets = float(total_liabilities / total_assets) if total_assets > 0 else 0

        return {
            "success": True,
            "data": {
                "as_of_date": as_of_date or date.today(),
                "financial_position": {
                    "total_assets": float(total_assets),
                    "total_liabilities": float(total_liabilities),
                    "total_equity": float(total_equity),
                    "current_assets": float(current_assets),
                    "current_liabilities": float(current_liabilities)
                },
                "performance": {
                    "revenue": float(income_statement.revenue.total_revenue),
                    "gross_profit": float(income_statement.gross_profit),
                    "operating_profit": float(income_statement.operating_profit),
                    "net_profit": float(income_statement.profit_after_tax)
                },
                "ratios": {
                    "current_ratio": current_ratio,
                    "debt_to_equity_ratio": debt_to_equity,
                    "debt_to_assets_ratio": debt_to_assets,
                    "gross_profit_margin": float(income_statement.gross_profit / income_statement.revenue.total_revenue * 100) if income_statement.revenue.total_revenue > 0 else 0,
                    "net_profit_margin": float(income_statement.profit_after_tax / income_statement.revenue.total_revenue * 100) if income_statement.revenue.total_revenue > 0 else 0
                }
            },
            "ifrs_standards": ["IAS 1 - Presentation of Financial Statements"],
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating financial summary: {str(e)}")

@router.get("/inventory/summary")
async def get_inventory_summary(
    branch_id: Optional[str] = Query(None, description="Branch ID filter"),
    db: Session = Depends(get_db)
):
    """
    Get inventory summary data for dashboard and filtering
    """
    try:
        from app.services.inventory_service import InventoryService
        from app.services.app_setting_service import AppSettingService

        # Use default branch if not specified
        if not branch_id:
            branch_id = "8f4aaa72-103b-4f40-b586-096675cfb4bf"  # Default branch ID

        # Fetch inventory data
        inventory_service = InventoryService(db)

        # Get inventory summary with error handling
        try:
            inventory_data = inventory_service.get_inventory_summary(branch_id)
        except Exception as inv_err:
            print(f"Error in get_inventory_summary: {str(inv_err)}")
            raise HTTPException(status_code=500, detail=f"Error fetching inventory data: {str(inv_err)}")

        # Fetch global report settings (currency, locale, vat)
        try:
            settings_service = AppSettingService(db)
            report_settings = settings_service.get_currency_settings()
        except Exception as set_err:
            print(f"Error getting currency settings: {str(set_err)}")
            report_settings = {
                "currency_code": "BWP",
                "currency_symbol": "P",
                "vat_rate": 14
            }

        # Get category analysis for proper category data
        try:
            category_analysis = inventory_service.get_category_analysis(branch_id)
            # Extract categories from nested data
            categories = category_analysis.get('data', {}).get('categories', [])
        except Exception as cat_err:
            print(f"Error getting category analysis: {str(cat_err)}")
            categories = []

        # Get low stock alert items
        try:
            low_stock_raw = inventory_service.get_low_stock_products(branch_id)
            low_stock_alerts = [
                {
                    "id": alert['id'],
                    "name": alert['name'],
                    "sku": alert['sku'],
                    "quantity": alert['current_quantity'],
                    "reorder_level": alert['reorder_point'],
                    "cost_price": alert['cost_price'],
                    "selling_price": alert['selling_price']
                }
                for alert in low_stock_raw
            ]
        except Exception as low_err:
            print(f"Error getting low stock products: {str(low_err)}")
            low_stock_alerts = []

        return {
            "success": True,
            "settings": report_settings,
            "data": {
                "total_products": inventory_data.get('total_products', 0),
                "total_value": inventory_data.get('total_value', 0),
                "low_stock_count": inventory_data.get('low_stock_count', 0),
                "out_of_stock_count": inventory_data.get('out_of_stock_count', 0),
                "low_stock_alerts": low_stock_alerts,
                "categories": categories
            },
            "generated_at": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Error generating inventory summary: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail=error_detail)

@router.get("/inventory/stock-movement")
async def get_stock_movement_report(
    branch_id: Optional[str] = Query(None, description="Branch ID filter"),
    start_date: Optional[date] = Query(None, description="Start date for movement report"),
    end_date: Optional[date] = Query(None, description="End date for movement report"),
    db: Session = Depends(get_db)
):
    """
    Get inventory stock movement report
    """
    try:
        from app.services.inventory_service import InventoryService

        # Use default branch if not specified
        if not branch_id:
            branch_id = "8f4aaa72-103b-4f40-b586-096675cfb4bf"  # Default branch ID

        inventory_service = InventoryService(db)
        # Service now returns structured data directly
        # Fetch report and global settings
        movement_report = inventory_service.get_stock_movement_report(branch_id, start_date, end_date)
        settings_service = AppSettingService(db)
        report_settings = settings_service.get_currency_settings()
        return {
            "success": movement_report.get("success", True),
            "settings": report_settings,
            "data": movement_report.get("data", []),
            "period": movement_report.get("period", {}),
            "total_transactions": movement_report.get("total_transactions", 0),
            "generated_at": movement_report.get("generated_at", datetime.now().isoformat())
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating stock movement report: {str(e)}")

@router.get("/inventory/aging-analysis")
async def get_inventory_aging_analysis(
    branch_id: Optional[str] = Query(None, description="Branch ID filter"),
    db: Session = Depends(get_db)
):
    """
    Get inventory aging analysis report
    """
    try:
        from app.services.inventory_service import InventoryService

        # Use default branch if not specified
        if not branch_id:
            branch_id = "8f4aaa72-103b-4f40-b586-096675cfb4bf"  # Default branch ID

        inventory_service = InventoryService(db)
        # Service now returns structured data directly
        aging_report = inventory_service.get_inventory_aging_report(branch_id)
        settings_service = AppSettingService(db)
        report_settings = settings_service.get_currency_settings()
        return {
            "success": aging_report.get("success", True),
            "settings": report_settings,
            "data": aging_report.get("data", {}),
            "generated_at": aging_report.get("generated_at", datetime.now().isoformat())
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating inventory aging analysis: {str(e)}")

@router.get("/inventory/abc-analysis")
async def get_abc_analysis(
    branch_id: Optional[str] = Query(None, description="Branch ID filter"),
    db: Session = Depends(get_db)
):
    """
    Get ABC analysis for inventory management
    """
    try:
        from app.services.inventory_service import InventoryService

        # Use default branch if not specified
        if not branch_id:
            branch_id = "8f4aaa72-103b-4f40-b586-096675cfb4bf"  # Default branch ID

        inventory_service = InventoryService(db)
        # Service now returns structured data directly
        abc_report = inventory_service.get_abc_analysis(branch_id)
        settings_service = AppSettingService(db)
        report_settings = settings_service.get_currency_settings()
        return {
            "success": abc_report.get("success", True),
            "settings": report_settings,
            "data": abc_report.get("data", {}),
            "generated_at": abc_report.get("generated_at", datetime.now().isoformat())
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating ABC analysis: {str(e)}")

@router.get("/inventory/valuation-methods")
async def get_valuation_methods_comparison(
    branch_id: Optional[str] = Query(None, description="Branch ID filter"),
    db: Session = Depends(get_db)
):
    """
    Get comparison of FIFO, LIFO, and Average Cost valuation methods
    """
    try:
        from app.services.inventory_service import InventoryService
        from app.services.app_setting_service import AppSettingService

        # Use default branch if not specified
        if not branch_id:
            branch_id = "8f4aaa72-103b-4f40-b586-096675cfb4bf"  # Default branch ID

        inventory_service = InventoryService(db)
        # Service now returns structured data directly
        valuation_report = inventory_service.get_valuation_methods_comparison(branch_id)
        settings_service = AppSettingService(db)
        report_settings = settings_service.get_currency_settings()
        return {
            "success": valuation_report.get("success", True),
            "settings": report_settings,
            "data": valuation_report.get("data", {}),
            "generated_at": valuation_report.get("generated_at", datetime.now().isoformat())
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating valuation methods comparison: {str(e)}")


@router.get("/inventory/category-analysis")
async def get_inventory_category_analysis(
    branch_id: Optional[str] = Query(None, description="Branch ID filter"),
    db: Session = Depends(get_db)
):
    """
    Get inventory category analysis report
    """
    try:
        from app.services.inventory_service import InventoryService
        from app.services.app_setting_service import AppSettingService
        # Use default branch if not specified
        if not branch_id:
            branch_id = "8f4aaa72-103b-4f40-b586-096675cfb4bf"  # Default branch ID

        inventory_service = InventoryService(db)
        category_report = inventory_service.get_category_analysis(branch_id)
        settings_service = AppSettingService(db)
        report_settings = settings_service.get_currency_settings()

        return {
            "success": category_report.get("success", True),
            "settings": report_settings,
            "data": category_report.get("data", {}),
            "generated_at": category_report.get("generated_at", datetime.now().isoformat())
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating category analysis: {str(e)}")


@router.get("/integration/dashboard-statistics")
async def get_integration_dashboard_statistics(
    branch_id: Optional[str] = Query(None, description="Branch ID filter"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive integration dashboard statistics

    Returns statistics about:
    - Sales integration (auto journal entries, VAT, IFRS compliance)
    - Inventory integration (stock movements, COGS, valuation)
    - Banking integration (auto entries, reconciliation, cash flow)
    - VAT integration (auto calculation, reporting, reconciliation)
    """
    try:
        from app.models.sales import Sale, Invoice
        from app.models.purchases import Purchase
        from app.models.banking import BankTransaction
        from app.models.accounting import JournalEntry, AccountingEntry
        from sqlalchemy import and_, or_

        # Use default branch if not specified
        if not branch_id:
            branch_id = "8f4aaa72-103b-4f40-b586-096675cfb4bf"  # Default branch ID

        # Get today's date range
        today = date.today()

        # SALES INTEGRATION STATISTICS
        sales_today = db.query(Sale).filter(
            and_(
                Sale.branch_id == branch_id,
                func.date(Sale.date_sold) == today
            )
        ).count()

        invoices_today = db.query(Invoice).filter(
            and_(
                Invoice.branch_id == branch_id,
                func.date(Invoice.invoice_date) == today
            )
        ).count()

        # Count auto-generated journal entries from sales (by checking source/particulars)
        sales_journal_entries = db.query(JournalEntry).filter(
            and_(
                JournalEntry.branch_id == branch_id,
                func.date(JournalEntry.date) == today,
                or_(
                    JournalEntry.description.ilike('%sale%'),
                    JournalEntry.description.ilike('%invoice%')
                )
            )
        ).count()

        # INVENTORY INTEGRATION STATISTICS
        from app.models.inventory import StockMovement
        stock_movements_today = db.query(StockMovement).filter(
            and_(
                StockMovement.branch_id == branch_id,
                func.date(StockMovement.transaction_date) == today
            )
        ).count()

        # Count COGS journal entries
        cogs_entries = db.query(JournalEntry).join(AccountingCode).filter(
            and_(
                JournalEntry.branch_id == branch_id,
                func.date(JournalEntry.date) == today,
                AccountingCode.code.like('5%')  # COGS accounts typically start with 5
            )
        ).count()

        # BANKING INTEGRATION STATISTICS
        bank_transactions_today = db.query(BankTransaction).filter(
            and_(
                BankTransaction.branch_id == branch_id,
                func.date(BankTransaction.transaction_date) == today
            )
        ).count()

        banking_journal_entries = db.query(JournalEntry).filter(
            and_(
                JournalEntry.branch_id == branch_id,
                func.date(JournalEntry.date) == today,
                or_(
                    JournalEntry.description.ilike('%bank%'),
                    JournalEntry.description.ilike('%cash%')
                )
            )
        ).count()

        # VAT INTEGRATION STATISTICS
        vat_journal_entries = db.query(JournalEntry).join(AccountingCode).filter(
            and_(
                JournalEntry.branch_id == branch_id,
                func.date(JournalEntry.date) == today,
                or_(
                    AccountingCode.code.like('2110%'),  # VAT Output
                    AccountingCode.code.like('1410%')   # VAT Input
                )
            )
        ).count()

        # Get total auto-generated journal entries today
        total_journal_entries_today = db.query(JournalEntry).filter(
            and_(
                JournalEntry.branch_id == branch_id,
                func.date(JournalEntry.date) == today
            )
        ).count()

        # Get IFRS compliance check
        ifrs_service = IFRSReportsCore(db)
        trial_balance = ifrs_service.get_trial_balance_data(as_of_date=today)

        compliance_score = 100  # Start with perfect score
        if not trial_balance.get('is_balanced', False):
            compliance_score -= 20

        # Check if IFRS categories are assigned
        accounts_without_ifrs = sum(
            1 for acc in trial_balance.get('accounts', [])
            if not acc.get('ifrs_category')
        )
        if accounts_without_ifrs > 0:
            compliance_score -= 5

        # Last sync time (current time for real-time integration)
        last_sync = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "success": True,
            "data": {
                "sales_integration": {
                    "status": "active",
                    "auto_journal_entries": "active",
                    "ifrs_compliance": "compliant" if compliance_score >= 90 else "needs_review",
                    "vat_integration": "active",
                    "sales_today": sales_today,
                    "invoices_today": invoices_today,
                    "journal_entries_generated": sales_journal_entries
                },
                "inventory_integration": {
                    "status": "partial" if stock_movements_today > 0 else "inactive",
                    "stock_movements": stock_movements_today,
                    "cogs_calculation": "active" if cogs_entries > 0 else "inactive",
                    "valuation_method": "FIFO",
                    "journal_entries_generated": cogs_entries
                },
                "banking_integration": {
                    "status": "active",
                    "auto_entries": "active",
                    "reconciliation": "integrated",
                    "cash_flow": "tracked",
                    "transactions_today": bank_transactions_today,
                    "journal_entries_generated": banking_journal_entries
                },
                "vat_integration": {
                    "status": "active",
                    "auto_calculation": "active",
                    "reporting": "ifrs",
                    "reconciliation": "pending" if vat_journal_entries == 0 else "active",
                    "journal_entries_generated": vat_journal_entries
                },
                "summary": {
                    "total_transactions_today": sales_today + bank_transactions_today,
                    "auto_generated_entries": total_journal_entries_today,
                    "ifrs_compliance_score": f"{compliance_score}%",
                    "last_sync": last_sync
                }
            },
            "generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating integration dashboard statistics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating integration dashboard statistics: {str(e)}"
        )
