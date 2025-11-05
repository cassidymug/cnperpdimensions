"""
Real-time branch sales monitoring API endpoint.
Optimized for high-traffic scenarios with caching and efficient queries.
"""

from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy import func, text
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import json
from functools import lru_cache
import time

from app.core.database import get_db
from app.models.sales import Sale
from app.models import Customer
from app.models import Branch

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()

class BranchSalesMetric(BaseModel):
    branch_id: str
    branch_name: str
    total_sales_today: float
    total_sales_this_month: float
    transaction_count_today: int
    average_transaction: float
    active_now: int
    last_updated: str

class BranchSalesDetail(BaseModel):
    branch_id: str
    branch_name: str
    total_sales: float
    transaction_count: int
    avg_transaction: float
    hours_covered: int
    last_sale_time: Optional[str] = None
    last_sale_amount: Optional[float] = None
    payment_breakdown: Dict[str, float]
    hourly_data: List[Dict[str, Any]]
    recent_sales: List[Dict[str, Any]] = []

class RealtimeSalesData(BaseModel):
    timestamp: str
    branches: List[BranchSalesMetric]
    total_network_sales: float
    active_branches: int

# Cache configuration
CACHE_TTL = 5  # 5 seconds for real-time data
_cache = {}
_cache_timestamps = {}

def get_cached_data(key: str, ttl: int = CACHE_TTL) -> Optional[Any]:
    """Get cached data if still valid"""
    if key in _cache:
        cache_time = _cache_timestamps.get(key, 0)
        if time.time() - cache_time < ttl:
            return _cache[key]
        else:
            del _cache[key]
            del _cache_timestamps[key]
    return None

def set_cache(key: str, data: Any) -> None:
    """Cache data with timestamp"""
    _cache[key] = data
    _cache_timestamps[key] = time.time()

@router.get("/v1/branch-sales/realtime", response_model=RealtimeSalesData)
async def get_realtime_branch_sales(
    db: Session = Depends(get_db),
    exclude_empty: bool = Query(False, description="Exclude branches with no sales")
):
    """
    Get real-time sales data for all branches - optimized for high traffic.
    Includes caching and efficient database queries.

    Parameters:
    - exclude_empty: If true, only returns branches with sales
    """
    cache_key = f"realtime_sales_{exclude_empty}"
    cached = get_cached_data(cache_key, ttl=3)

    if cached:
        return cached

    try:
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Use raw SQL for better performance on large datasets
        query = text("""
            SELECT
                b.id,
                b.name,
                COUNT(CASE WHEN s.date >= :today_start THEN 1 END) as sales_today,
                COUNT(CASE WHEN s.date >= :month_start THEN 1 END) as sales_month,
                COALESCE(SUM(CASE WHEN s.date >= :today_start THEN s.total_amount ELSE 0 END), 0) as amount_today,
                COALESCE(SUM(CASE WHEN s.date >= :month_start THEN s.total_amount ELSE 0 END), 0) as amount_month
            FROM branches b
            LEFT JOIN sales s ON b.id = s.branch_id
            GROUP BY b.id, b.name
            ORDER BY amount_today DESC
        """)

        results = db.execute(query, {
            'today_start': today_start,
            'month_start': month_start
        }).fetchall()

        branches_data = []
        total_network_sales = 0
        active_branches_count = 0

        for row in results:
            branch_id, branch_name, sales_today, sales_month, amount_today, amount_month = row

            if exclude_empty and sales_today == 0:
                continue

            avg_transaction = float(amount_today / sales_today) if sales_today > 0 else 0

            metric = BranchSalesMetric(
                branch_id=branch_id,
                branch_name=branch_name,
                total_sales_today=float(amount_today),
                total_sales_this_month=float(amount_month),
                transaction_count_today=int(sales_today),
                average_transaction=avg_transaction,
                active_now=int(sales_today),  # Simplified: use daily count as proxy for active
                last_updated=now.isoformat()
            )

            branches_data.append(metric)
            total_network_sales += float(amount_today)
            if sales_today > 0:
                active_branches_count += 1

        response = RealtimeSalesData(
            timestamp=now.isoformat(),
            branches=branches_data,
            total_network_sales=total_network_sales,
            active_branches=active_branches_count
        )

        set_cache(cache_key, response)
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching realtime sales: {str(e)}")

@router.get("/v1/branch-sales/{branch_id}/detail", response_model=BranchSalesDetail)
async def get_branch_sales_detail(
    branch_id: str,
    hours: int = Query(24, ge=1, le=168, description="Hours to look back (1-168)"),
    db: Session = Depends(get_db)
):
    """
    Get detailed sales data for a specific branch with hourly breakdown.
    Optimized for high-frequency queries.
    """
    cache_key = f"branch_detail_{branch_id}_{hours}"
    cached = get_cached_data(cache_key, ttl=5)

    if cached:
        return cached

    try:
        # Verify branch exists
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        if not branch:
            raise HTTPException(status_code=404, detail="Branch not found")

        now = datetime.now()
        lookback_time = now - timedelta(hours=hours)

        # Get sales data efficiently - only select needed columns
        sales_query = db.query(
            Sale.id,
            Sale.date,
            Sale.total_amount,
            Sale.payment_method,
            Sale.customer_id,
            Sale.reference
        ).filter(
            Sale.branch_id == branch_id,
            Sale.date >= lookback_time
        ).all()

        # Calculate metrics
        total_sales = sum(float(s.total_amount or 0) for s in sales_query)
        transaction_count = len(sales_query)
        avg_transaction = total_sales / transaction_count if transaction_count > 0 else 0

        # Payment breakdown
        payment_breakdown = {}
        for sale in sales_query:
            method = sale.payment_method or "Unknown"
            payment_breakdown[method] = payment_breakdown.get(method, 0) + float(sale.total_amount or 0)

        # Hourly data
        hourly_data = []
        for i in range(hours, 0, -1):
            hour_start = now - timedelta(hours=i)
            hour_start = hour_start.replace(minute=0, second=0, microsecond=0)
            hour_end = hour_start + timedelta(hours=1)

            hour_sales = [s for s in sales_query
                         if hour_start <= s.date < hour_end]

            hourly_data.append({
                'hour': hour_start.isoformat(),
                'sales_count': len(hour_sales),
                'sales_amount': sum(float(s.total_amount or 0) for s in hour_sales)
            })

        # Get last sale info
        last_sale_query = db.query(
            Sale.date,
            Sale.total_amount
        ).filter(
            Sale.branch_id == branch_id,
            Sale.date >= lookback_time
        ).order_by(Sale.date.desc()).first()

        last_sale_time = last_sale_query.date.isoformat() if last_sale_query else None
        last_sale_amount = float(last_sale_query.total_amount or 0) if last_sale_query else None

        # Recent sales (last 20)
        recent_sales_query = db.query(
            Sale.id,
            Sale.reference,
            Sale.customer_id,
            Sale.total_amount,
            Sale.payment_method,
            Sale.date
        ).filter(
            Sale.branch_id == branch_id,
            Sale.date >= lookback_time
        ).order_by(Sale.date.desc()).limit(20).all()

        recent_sales = []
        for sale in recent_sales_query:
            customer = db.query(Customer).filter(Customer.id == sale.customer_id).first() if sale.customer_id else None
            recent_sales.append({
                'sale_id': sale.id,
                'receipt_number': sale.reference or sale.id[:8],  # Use reference or first 8 chars of ID
                'customer_name': customer.name if customer else 'Walk-in',
                'amount': float(sale.total_amount or 0),
                'payment_method': sale.payment_method or 'Unknown',
                'timestamp': sale.date.isoformat()
            })

        detail = BranchSalesDetail(
            branch_id=branch_id,
            branch_name=branch.name,
            total_sales=total_sales,
            transaction_count=transaction_count,
            avg_transaction=avg_transaction,
            hours_covered=hours,
            last_sale_time=last_sale_time,
            last_sale_amount=last_sale_amount,
            payment_breakdown=payment_breakdown,
            hourly_data=hourly_data,
            recent_sales=recent_sales
        )

        set_cache(cache_key, detail)
        return detail

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching branch sales detail: {str(e)}")

@router.get("/v1/branch-sales/comparison", response_model=Dict[str, Any])
async def get_branch_sales_comparison(
    branch_ids: str = Query(..., description="Comma-separated branch IDs"),
    metric: str = Query("daily", regex="^(hourly|daily|weekly)$"),
    db: Session = Depends(get_db)
):
    """
    Compare sales metrics across multiple branches.
    Useful for real-time monitoring of competitive performance.
    """
    cache_key = f"comparison_{branch_ids}_{metric}"
    cached = get_cached_data(cache_key, ttl=10)

    if cached:
        return cached

    try:
        branch_list = [b.strip() for b in branch_ids.split(',')]

        comparison_data = {}
        for branch_id in branch_list:
            branch = db.query(Branch).filter(Branch.id == branch_id).first()
            if not branch:
                continue

            now = datetime.now()
            if metric == "hourly":
                time_range = now - timedelta(hours=24)
            elif metric == "daily":
                time_range = now - timedelta(days=30)
            else:  # weekly
                time_range = now - timedelta(weeks=12)

            sales = db.query(func.sum(Sale.total_amount), func.count(Sale.id)).filter(
                Sale.branch_id == branch_id,
                Sale.date >= time_range
            ).first()

            total, count = sales if sales else (0, 0)

            comparison_data[branch.name] = {
                'total_sales': float(total or 0),
                'transaction_count': int(count or 0),
                'average': float((total or 0) / (count or 1)) if count > 0 else 0
            }

        result = {
            'metric': metric,
            'timestamp': now.isoformat(),
            'branches': comparison_data
        }

        set_cache(cache_key, result)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing branch sales: {str(e)}")
