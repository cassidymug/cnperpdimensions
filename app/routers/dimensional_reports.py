"""
Dimensional Financial Reports API Endpoints

Comprehensive API for generating financial reports with dimensional analysis.
Replaces the old reporting system with advanced dimensional capabilities.

Features:
- Profit & Loss with Cost Center/Project filtering
- Balance Sheet with dimensional breakdowns
- General Ledger with dimensional analysis
- Comparative period reporting with dimensions
- Debtors/Creditors dimensional analysis
- Sales/Purchase reports with dimensional analysis
"""

from datetime import date, datetime, timedelta
from typing import Optional, Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.dimensional_reports_service import DimensionalReportsService

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["dimensional-reports"])


@router.get("/dimensions/available")
async def get_available_dimensions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all available dimensions and their values for filtering reports
    """
    try:
        service = DimensionalReportsService(db)
        dimensions = service.get_available_dimensions()
        return {
            "status": "success",
            "data": dimensions,
            "message": "Available dimensions retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve dimensions: {str(e)}")


@router.get("/profit-loss")
async def get_dimensional_profit_loss(
    start_date: date = Query(..., description="Report period start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="Report period end date (YYYY-MM-DD)"),
    cost_center: Optional[str] = Query(None, description="Cost Center dimension filter"),
    project: Optional[str] = Query(None, description="Project dimension filter"),
    comparison_period: bool = Query(False, description="Include comparative period"),
    comparison_start: Optional[date] = Query(None, description="Comparison period start date"),
    comparison_end: Optional[date] = Query(None, description="Comparison period end date"),
    group_by_dimensions: bool = Query(True, description="Group results by dimensions"),
    format: str = Query("json", description="Response format: json, csv, pdf"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate Profit & Loss statement with dimensional analysis

    **Dimensional Filtering:**
    - Filter by Cost Center to see P&L for specific departments
    - Filter by Project to see P&L for specific initiatives
    - Combine filters for detailed analysis

    **Comparative Analysis:**
    - Compare current period with previous period
    - Show variance analysis and trends
    """
    try:
        service = DimensionalReportsService(db)

        # Build dimension filters
        dimension_filters = {}
        if cost_center:
            dimension_filters['FUNCTIONAL'] = cost_center
        if project:
            dimension_filters['PROJECT'] = project

        # Generate report
        report_data = service.get_dimensional_profit_loss(
            start_date=start_date,
            end_date=end_date,
            dimension_filters=dimension_filters,
            comparison_period=comparison_period,
            comparison_start_date=comparison_start,
            comparison_end_date=comparison_end,
            group_by_dimensions=group_by_dimensions
        )

        if format.lower() == "json":
            return {
                "status": "success",
                "data": report_data,
                "message": "Profit & Loss report generated successfully"
            }
        elif format.lower() == "csv":
            # TODO: Implement CSV export
            raise HTTPException(status_code=501, detail="CSV format not yet implemented")
        elif format.lower() == "pdf":
            # TODO: Implement PDF export
            raise HTTPException(status_code=501, detail="PDF format not yet implemented")
        else:
            raise HTTPException(status_code=400, detail="Unsupported format. Use: json, csv, pdf")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate P&L report: {str(e)}")


@router.get("/balance-sheet")
async def get_dimensional_balance_sheet(
    as_of_date: Optional[date] = Query(None, description="As of date (defaults to today)"),
    cost_center: Optional[str] = Query(None, description="Cost Center dimension filter"),
    project: Optional[str] = Query(None, description="Project dimension filter"),
    comparison_date: Optional[date] = Query(None, description="Comparison date for variance analysis"),
    group_by_dimensions: bool = Query(True, description="Group results by dimensions"),
    format: str = Query("json", description="Response format: json, csv, pdf"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate Balance Sheet with dimensional analysis

    **Dimensional Filtering:**
    - Filter by Cost Center to see assets/liabilities by department
    - Filter by Project to see project-specific financial position
    - Analyze dimensional impact on financial position
    """
    try:
        service = DimensionalReportsService(db)

        if as_of_date is None:
            as_of_date = date.today()

        # Build dimension filters
        dimension_filters = {}
        if cost_center:
            dimension_filters['FUNCTIONAL'] = cost_center
        if project:
            dimension_filters['PROJECT'] = project

        # Generate report
        report_data = service.get_dimensional_balance_sheet(
            as_of_date=as_of_date,
            dimension_filters=dimension_filters,
            comparison_date=comparison_date,
            group_by_dimensions=group_by_dimensions
        )

        return {
            "status": "success",
            "data": report_data,
            "message": "Balance Sheet report generated successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Balance Sheet: {str(e)}")


@router.get("/general-ledger")
async def get_dimensional_general_ledger(
    start_date: date = Query(..., description="Report period start date"),
    end_date: date = Query(..., description="Report period end date"),
    account_codes: Optional[str] = Query(None, description="Comma-separated account codes to filter"),
    cost_center: Optional[str] = Query(None, description="Cost Center dimension filter"),
    project: Optional[str] = Query(None, description="Project dimension filter"),
    group_by_dimensions: bool = Query(True, description="Group results by dimensions"),
    format: str = Query("json", description="Response format: json, csv, pdf"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate General Ledger with dimensional analysis

    **Features:**
    - Detailed transaction-level view with dimensional tags
    - Filter by specific accounts or account ranges
    - Running balance calculations with dimensional context
    """
    try:
        service = DimensionalReportsService(db)

        # Parse account codes if provided
        account_codes_list = None
        if account_codes:
            account_codes_list = [code.strip() for code in account_codes.split(',')]

        # Build dimension filters
        dimension_filters = {}
        if cost_center:
            dimension_filters['FUNCTIONAL'] = cost_center
        if project:
            dimension_filters['PROJECT'] = project

        # Generate report
        report_data = service.get_dimensional_general_ledger(
            start_date=start_date,
            end_date=end_date,
            account_codes=account_codes_list,
            dimension_filters=dimension_filters,
            group_by_dimensions=group_by_dimensions
        )

        return {
            "status": "success",
            "data": report_data,
            "message": "General Ledger report generated successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate General Ledger: {str(e)}")


@router.get("/debtors-analysis")
async def get_debtors_dimensional_analysis(
    as_of_date: Optional[date] = Query(None, description="Analysis date (defaults to today)"),
    cost_center: Optional[str] = Query(None, description="Cost Center dimension filter"),
    project: Optional[str] = Query(None, description="Project dimension filter"),
    aging_buckets: Optional[str] = Query("30,60,90,120", description="Comma-separated aging buckets in days"),
    format: str = Query("json", description="Response format: json, csv, pdf"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate Debtors (Accounts Receivable) analysis with dimensional breakdown

    **Features:**
    - Aging analysis with dimensional context
    - Cost Center/Project breakdown of receivables
    - Collection priority analysis by dimension
    """
    try:
        service = DimensionalReportsService(db)

        if as_of_date is None:
            as_of_date = date.today()

        # Parse aging buckets
        aging_buckets_list = [int(bucket.strip()) for bucket in aging_buckets.split(',')]

        # Build dimension filters
        dimension_filters = {}
        if cost_center:
            dimension_filters['FUNCTIONAL'] = cost_center
        if project:
            dimension_filters['PROJECT'] = project

        # Generate report
        report_data = service.get_debtors_dimensional_analysis(
            as_of_date=as_of_date,
            dimension_filters=dimension_filters,
            aging_buckets=aging_buckets_list
        )

        return {
            "status": "success",
            "data": report_data,
            "message": "Debtors analysis generated successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Debtors analysis: {str(e)}")


@router.get("/creditors-analysis")
async def get_creditors_dimensional_analysis(
    as_of_date: Optional[date] = Query(None, description="Analysis date (defaults to today)"),
    cost_center: Optional[str] = Query(None, description="Cost Center dimension filter"),
    project: Optional[str] = Query(None, description="Project dimension filter"),
    aging_buckets: Optional[str] = Query("30,60,90,120", description="Comma-separated aging buckets in days"),
    format: str = Query("json", description="Response format: json, csv, pdf"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate Creditors (Accounts Payable) analysis with dimensional breakdown

    **Features:**
    - Aging analysis of payables by dimension
    - Cost Center/Project breakdown of liabilities
    - Payment priority analysis by dimension
    """
    try:
        service = DimensionalReportsService(db)

        if as_of_date is None:
            as_of_date = date.today()

        # Parse aging buckets
        aging_buckets_list = [int(bucket.strip()) for bucket in aging_buckets.split(',')]

        # Build dimension filters
        dimension_filters = {}
        if cost_center:
            dimension_filters['FUNCTIONAL'] = cost_center
        if project:
            dimension_filters['PROJECT'] = project

        # Generate report
        report_data = service.get_creditors_dimensional_analysis(
            as_of_date=as_of_date,
            dimension_filters=dimension_filters,
            aging_buckets=aging_buckets_list
        )

        return {
            "status": "success",
            "data": report_data,
            "message": "Creditors analysis generated successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Creditors analysis: {str(e)}")


@router.get("/sales-analysis")
async def get_sales_dimensional_analysis(
    start_date: date = Query(..., description="Analysis period start date"),
    end_date: date = Query(..., description="Analysis period end date"),
    cost_center: Optional[str] = Query(None, description="Cost Center dimension filter"),
    project: Optional[str] = Query(None, description="Project dimension filter"),
    group_by_period: str = Query("month", description="Grouping period: day, week, month, quarter"),
    format: str = Query("json", description="Response format: json, csv, pdf"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate Sales analysis with dimensional breakdown

    **Features:**
    - Sales trends by Cost Center and Project
    - Time-based analysis with dimensional context
    - Performance comparison across dimensions
    """
    try:
        service = DimensionalReportsService(db)

        # Build dimension filters
        dimension_filters = {}
        if cost_center:
            dimension_filters['FUNCTIONAL'] = cost_center
        if project:
            dimension_filters['PROJECT'] = project

        # Generate report
        report_data = service.get_sales_dimensional_analysis(
            start_date=start_date,
            end_date=end_date,
            dimension_filters=dimension_filters,
            group_by_period=group_by_period
        )

        return {
            "status": "success",
            "data": report_data,
            "message": "Sales analysis generated successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Sales analysis: {str(e)}")


@router.get("/purchases-analysis")
async def get_purchases_dimensional_analysis(
    start_date: date = Query(..., description="Analysis period start date"),
    end_date: date = Query(..., description="Analysis period end date"),
    cost_center: Optional[str] = Query(None, description="Cost Center dimension filter"),
    project: Optional[str] = Query(None, description="Project dimension filter"),
    group_by_period: str = Query("month", description="Grouping period: day, week, month, quarter"),
    format: str = Query("json", description="Response format: json, csv, pdf"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate Purchases analysis with dimensional breakdown

    **Features:**
    - Purchase trends by Cost Center and Project
    - Expense analysis with dimensional context
    - Cost control analysis across dimensions
    """
    try:
        service = DimensionalReportsService(db)

        # Build dimension filters
        dimension_filters = {}
        if cost_center:
            dimension_filters['FUNCTIONAL'] = cost_center
        if project:
            dimension_filters['PROJECT'] = project

        # Generate report
        report_data = service.get_purchases_dimensional_analysis(
            start_date=start_date,
            end_date=end_date,
            dimension_filters=dimension_filters,
            group_by_period=group_by_period
        )

        return {
            "status": "success",
            "data": report_data,
            "message": "Purchases analysis generated successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate Purchases analysis: {str(e)}")


@router.get("/comparative-analysis")
async def get_comparative_dimensional_analysis(
    report_type: str = Query(..., description="Report type: profit_loss, balance_sheet, sales, purchases"),
    period1_start: date = Query(..., description="Period 1 start date"),
    period1_end: date = Query(..., description="Period 1 end date"),
    period2_start: date = Query(..., description="Period 2 start date"),
    period2_end: date = Query(..., description="Period 2 end date"),
    cost_center: Optional[str] = Query(None, description="Cost Center dimension filter"),
    project: Optional[str] = Query(None, description="Project dimension filter"),
    format: str = Query("json", description="Response format: json, csv, pdf"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate comparative analysis between two periods with dimensional breakdown

    **Features:**
    - Period-over-period comparison with variance analysis
    - Dimensional context for trend analysis
    - Growth/decline analysis by dimension
    """
    try:
        service = DimensionalReportsService(db)

        # Build dimension filters
        dimension_filters = {}
        if cost_center:
            dimension_filters['FUNCTIONAL'] = cost_center
        if project:
            dimension_filters['PROJECT'] = project

        # Generate reports for both periods
        if report_type == "profit_loss":
            period1_data = service.get_dimensional_profit_loss(
                start_date=period1_start,
                end_date=period1_end,
                dimension_filters=dimension_filters
            )
            period2_data = service.get_dimensional_profit_loss(
                start_date=period2_start,
                end_date=period2_end,
                dimension_filters=dimension_filters
            )
        elif report_type == "sales":
            period1_data = service.get_sales_dimensional_analysis(
                start_date=period1_start,
                end_date=period1_end,
                dimension_filters=dimension_filters
            )
            period2_data = service.get_sales_dimensional_analysis(
                start_date=period2_start,
                end_date=period2_end,
                dimension_filters=dimension_filters
            )
        elif report_type == "purchases":
            period1_data = service.get_purchases_dimensional_analysis(
                start_date=period1_start,
                end_date=period1_end,
                dimension_filters=dimension_filters
            )
            period2_data = service.get_purchases_dimensional_analysis(
                start_date=period2_start,
                end_date=period2_end,
                dimension_filters=dimension_filters
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported report type for comparison")

        # Calculate variance
        if report_type == "profit_loss":
            variance_analysis = {
                'revenue_variance': period2_data['revenue']['total'] - period1_data['revenue']['total'],
                'expense_variance': period2_data['expenses']['total'] - period1_data['expenses']['total'],
                'net_income_variance': period2_data['net_income'] - period1_data['net_income']
            }
        elif report_type in ["sales", "purchases"]:
            total_key = 'total_sales' if report_type == 'sales' else 'total_purchases'
            variance_analysis = {
                f'{report_type}_variance': period2_data[total_key] - period1_data[total_key]
            }

        comparison_report = {
            'report_type': f'comparative_{report_type}',
            'dimension_filters': dimension_filters,
            'period1': {
                'period': f"{period1_start.isoformat()} to {period1_end.isoformat()}",
                'data': period1_data
            },
            'period2': {
                'period': f"{period2_start.isoformat()} to {period2_end.isoformat()}",
                'data': period2_data
            },
            'variance_analysis': variance_analysis,
            'generated_at': datetime.now().isoformat()
        }

        return {
            "status": "success",
            "data": comparison_report,
            "message": "Comparative analysis generated successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate comparative analysis: {str(e)}")


@router.get("/dashboard-summary")
async def get_dashboard_summary(
    as_of_date: Optional[date] = Query(None, description="Summary date (defaults to today)"),
    cost_center: Optional[str] = Query(None, description="Cost Center dimension filter"),
    project: Optional[str] = Query(None, description="Project dimension filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate executive dashboard summary with key dimensional metrics

    **Features:**
    - Key financial metrics with dimensional context
    - Trends and alerts by dimension
    - Quick overview for decision making
    """
    try:
        service = DimensionalReportsService(db)

        if as_of_date is None:
            as_of_date = date.today()

        # Build dimension filters
        dimension_filters = {}
        if cost_center:
            dimension_filters['FUNCTIONAL'] = cost_center
        if project:
            dimension_filters['PROJECT'] = project

        # Get current month P&L
        month_start = as_of_date.replace(day=1)
        current_pl = service.get_dimensional_profit_loss(
            start_date=month_start,
            end_date=as_of_date,
            dimension_filters=dimension_filters
        )

        # Get balance sheet
        balance_sheet = service.get_dimensional_balance_sheet(
            as_of_date=as_of_date,
            dimension_filters=dimension_filters
        )

        # Get receivables summary
        debtors = service.get_debtors_dimensional_analysis(
            as_of_date=as_of_date,
            dimension_filters=dimension_filters
        )

        # Get payables summary
        creditors = service.get_creditors_dimensional_analysis(
            as_of_date=as_of_date,
            dimension_filters=dimension_filters
        )

        summary = {
            'report_type': 'dashboard_summary',
            'as_of_date': as_of_date.isoformat(),
            'dimension_filters': dimension_filters,
            'key_metrics': {
                'monthly_revenue': current_pl['revenue']['total'],
                'monthly_expenses': current_pl['expenses']['total'],
                'monthly_net_income': current_pl['net_income'],
                'total_assets': balance_sheet['assets']['total'],
                'total_liabilities': balance_sheet['liabilities']['total'],
                'total_equity': balance_sheet['equity']['total'],
                'total_receivables': debtors['total_outstanding'],
                'total_payables': creditors['total_outstanding']
            },
            'alerts': {
                'high_receivables': debtors['aging_totals'].get('over_120_days', 0) > 10000,
                'high_payables': creditors['aging_totals'].get('over_120_days', 0) > 10000,
                'negative_net_income': current_pl['net_income'] < 0
            },
            'generated_at': datetime.now().isoformat()
        }

        return {
            "status": "success",
            "data": summary,
            "message": "Dashboard summary generated successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate dashboard summary: {str(e)}")


# Endpoint to test the new dimensional reports system
@router.get("/health")
async def health_check():
    """Health check for dimensional reports system"""
    return {
        "status": "success",
        "message": "Dimensional Reports API is operational",
        "version": "2.0.0",
        "features": [
            "Dimensional Profit & Loss",
            "Dimensional Balance Sheet",
            "Dimensional General Ledger",
            "Debtors/Creditors Analysis",
            "Sales/Purchases Analysis",
            "Comparative Period Analysis",
            "Dashboard Summary"
        ]
    }
