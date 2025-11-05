"""
Phase 4: Banking Module - Dimensional Accounting API Endpoints

This module provides REST API endpoints for dimensional accounting in banking:
1. POST /transactions/{id}/post-accounting - Post bank transaction to GL with dimensions
2. GET /reconciliation - Reconcile bank account by dimension
3. GET /cash-position - Cash position by dimension
4. GET /transfer-tracking - Track inter-dimensional transfers
5. GET /dimensional-analysis - Cash flow analysis by dimension
6. GET /variance-report - Cash variances by dimension

All endpoints integrate with BankingService methods for GL posting and reconciliation.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

from app.core.database import get_db
from app.services.banking_service import BankingService
from app.core.response_wrapper import UnifiedResponse

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/banking", tags=["banking-dimensions"])


# ============================================================================
# 1. POST /transactions/{id}/post-accounting
# ============================================================================

@router.post("/transactions/{transaction_id}/post-accounting", status_code=status.HTTP_200_OK)
async def post_transaction_to_accounting(
    transaction_id: str,
    db: Session = Depends(get_db)
):
    """Post bank transaction to GL with dimensional tracking."""
    try:
        banking_service = BankingService(db)
        result = await banking_service.post_bank_transaction_to_accounting(
            bank_transaction_id=transaction_id,
            user_id="system-user"
        )

        if not result.get('success'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('error', 'Failed to post transaction')
            )

        return UnifiedResponse.success(
            data={
                "bank_transaction_id": transaction_id,
                "posting_status": result.get('posting_status', 'posted'),
                "gl_entries": result.get('gl_entries', []),
                "posted_at": datetime.now().isoformat()
            },
            message="Bank transaction posted to GL successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 2. GET /reconciliation
# ============================================================================

@router.get("/reconciliation", status_code=status.HTTP_200_OK)
async def get_bank_reconciliation(
    bank_account_id: str = Query(...),
    period: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Retrieve bank reconciliation with dimensional accuracy."""
    try:
        banking_service = BankingService(db)
        result = await banking_service.reconcile_banking_by_dimension(
            bank_account_id=bank_account_id,
            period=period,
            reconciliation_date=date.today(),
            user_id="system-user"
        )

        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error'))

        recon = result.get('reconciliation', {})
        return UnifiedResponse.success(
            data={
                "reconciliation_id": recon.get('id', ''),
                "bank_account_id": bank_account_id,
                "statement_ending_balance": float(recon.get('statement_balance', 0)),
                "gl_balance": float(recon.get('gl_balance', 0)),
                "variance_amount": float(recon.get('variance_amount', 0)),
                "is_balanced": recon.get('is_balanced', False),
                "dimensional_accuracy": recon.get('dimensional_accuracy', True),
                "reconciliation_status": recon.get('status', 'pending')
            },
            message="Bank reconciliation retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 3. GET /cash-position
# ============================================================================

@router.get("/cash-position", status_code=status.HTTP_200_OK)
async def get_cash_position_by_dimension(
    as_of_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """Get current cash position by dimension."""
    try:
        banking_service = BankingService(db)
        result = await banking_service.get_cash_position_by_dimension(
            as_of_date=as_of_date or date.today()
        )

        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error'))

        cash = result.get('cash_position', {})
        return UnifiedResponse.success(
            data={
                "as_of_date": as_of_date or date.today(),
                "cash_position_total": float(cash.get('total', 0)),
                "by_cost_center": cash.get('by_cost_center', [])
            },
            message="Cash position retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 4. GET /transfer-tracking
# ============================================================================

@router.get("/transfer-tracking", status_code=status.HTTP_200_OK)
async def get_dimensional_transfers(
    period: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Track all inter-dimensional transfers."""
    try:
        banking_service = BankingService(db)
        result = await banking_service.track_dimensional_transfers(
            period=period
        )

        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error'))

        transfers = result.get('transfers', {})
        return UnifiedResponse.success(
            data={
                "period": period or "all",
                "total_transfers": transfers.get('count', 0),
                "transfers": transfers.get('items', [])
            },
            message="Dimensional transfers retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 5. GET /dimensional-analysis
# ============================================================================

@router.get("/dimensional-analysis", status_code=status.HTTP_200_OK)
def analyze_cash_flow_by_dimension(
    period: str = Query(..., description="YYYY-MM format"),
    dimension: str = Query("cost_center", description="cost_center | project | department"),
    db: Session = Depends(get_db)
):
    """Analyze cash flow by dimension."""
    try:
        if len(period) != 7 or period[4] != '-':
            raise HTTPException(status_code=400, detail="Period must be YYYY-MM")

        banking_service = BankingService(db)
        result = banking_service.analyze_cash_flow_by_dimension(
            period=period,
            dimension=dimension
        )

        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error'))

        analysis = result.get('analysis', {})
        return UnifiedResponse.success(
            data={
                "period": period,
                "dimension": dimension,
                "analysis": analysis.get('items', []),
                "summary": analysis.get('summary', {})
            },
            message="Cash flow analysis completed successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 6. GET /variance-report
# ============================================================================

@router.get("/variance-report", status_code=status.HTTP_200_OK)
def get_cash_variance_report(
    period: str = Query(..., description="YYYY-MM format"),
    variance_threshold: Decimal = Query(Decimal("100.00")),
    db: Session = Depends(get_db)
):
    """Identify cash variances by dimension."""
    try:
        if len(period) != 7 or period[4] != '-':
            raise HTTPException(status_code=400, detail="Period must be YYYY-MM")

        banking_service = BankingService(db)
        result = banking_service.get_cash_variance_report(
            period=period,
            variance_threshold=variance_threshold
        )

        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error'))

        variance = result.get('report', {})
        return UnifiedResponse.success(
            data={
                "period": period,
                "variance_threshold": float(variance_threshold),
                "variances_found": variance.get('count', 0),
                "variances": variance.get('items', []),
                "summary": variance.get('summary', {})
            },
            message="Variance report generated successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
