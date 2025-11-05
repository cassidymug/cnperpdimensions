"""
Branch Stock Management API Endpoints

This module provides REST API endpoints for managing branch-specific stock operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.services.branch_stock_service import BranchStockService

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()


class StockTransferRequest(BaseModel):
    """Stock transfer request schema"""
    product_id: str
    from_branch_id: str
    to_branch_id: str
    quantity: int
    reason: Optional[str] = "Branch Transfer"
    user_id: Optional[str] = None


class StockLevel(BaseModel):
    """Stock level response schema"""
    product_id: str
    product_name: str
    sku: Optional[str]
    current_stock: int
    reorder_point: int
    cost_price: float
    selling_price: float
    is_low_stock: bool
    is_out_of_stock: bool
    stock_value: float
    branch_id: str


class StockMovement(BaseModel):
    """Stock movement response schema"""
    transaction_id: str
    product_id: str
    product_name: str
    sku: Optional[str]
    transaction_type: str
    quantity: int
    reference_number: Optional[str]
    notes: Optional[str]
    created_at: datetime
    created_by: Optional[str]


class BranchStockSummary(BaseModel):
    """Branch stock summary schema"""
    branch_id: str
    total_products: int
    total_stock_value: float
    low_stock_count: int
    out_of_stock_count: int
    recent_movements_count: int
    stock_turn_rate: float
    summary_date: datetime


class StockTransferResponse(BaseModel):
    """Stock transfer response schema"""
    success: bool
    outbound_transaction_id: str
    inbound_transaction_id: str
    transferred_quantity: int
    from_branch: str
    to_branch: str


@router.get("/{branch_id}/stock-levels", response_model=List[StockLevel])
async def get_branch_stock_levels(
    branch_id: str,
    db: Session = Depends(get_db)
):
    """Get current stock levels for all products in a branch"""
    stock_service = BranchStockService(db)
    
    try:
        stock_levels = stock_service.get_branch_stock_levels(branch_id)
        return [StockLevel(**level) for level in stock_levels]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{branch_id}/stock-movements", response_model=List[StockMovement])
async def get_branch_stock_movements(
    branch_id: str,
    days: int = Query(30, description="Number of days to look back"),
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    db: Session = Depends(get_db)
):
    """Get stock movements for a branch within specified days"""
    stock_service = BranchStockService(db)
    
    try:
        movements = stock_service.get_branch_stock_movements(
            branch_id=branch_id,
            days=days,
            product_id=product_id
        )
        return [StockMovement(**movement) for movement in movements]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{branch_id}/stock-summary", response_model=BranchStockSummary)
async def get_branch_stock_summary(
    branch_id: str,
    db: Session = Depends(get_db)
):
    """Get comprehensive stock summary for a branch"""
    stock_service = BranchStockService(db)
    
    try:
        summary = stock_service.get_branch_stock_summary(branch_id)
        return BranchStockSummary(**summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transfer", response_model=StockTransferResponse)
async def transfer_stock_between_branches(
    transfer_request: StockTransferRequest,
    db: Session = Depends(get_db)
):
    """Transfer stock from one branch to another"""
    stock_service = BranchStockService(db)
    
    try:
        result = stock_service.transfer_stock_between_branches(
            product_id=transfer_request.product_id,
            from_branch_id=transfer_request.from_branch_id,
            to_branch_id=transfer_request.to_branch_id,
            quantity=transfer_request.quantity,
            reason=transfer_request.reason,
            user_id=transfer_request.user_id
        )
        return StockTransferResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consolidation", response_model=Dict)
async def get_consolidated_branch_stocks(
    db: Session = Depends(get_db)
):
    """Get consolidated stock levels across all branches"""
    stock_service = BranchStockService(db)
    
    try:
        consolidation = stock_service.consolidate_branch_stocks()
        return consolidation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{branch_id}/low-stock", response_model=List[StockLevel])
async def get_branch_low_stock_items(
    branch_id: str,
    db: Session = Depends(get_db)
):
    """Get products with low stock levels in a branch"""
    stock_service = BranchStockService(db)
    
    try:
        all_stock_levels = stock_service.get_branch_stock_levels(branch_id)
        low_stock_items = [
            level for level in all_stock_levels 
            if level['is_low_stock'] or level['is_out_of_stock']
        ]
        return [StockLevel(**level) for level in low_stock_items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{branch_id}/stock-valuation")
async def get_branch_stock_valuation(
    branch_id: str,
    db: Session = Depends(get_db)
):
    """Get stock valuation report for a branch"""
    stock_service = BranchStockService(db)
    
    try:
        stock_levels = stock_service.get_branch_stock_levels(branch_id)
        
        total_cost_value = sum(level['stock_value'] for level in stock_levels)
        total_selling_value = sum(
            level['current_stock'] * level['selling_price'] 
            for level in stock_levels
        )
        potential_profit = total_selling_value - total_cost_value
        
        # Group by category if available
        valuation_by_category = {}
        for level in stock_levels:
            category = "Uncategorized"  # Default category
            if category not in valuation_by_category:
                valuation_by_category[category] = {
                    'cost_value': 0,
                    'selling_value': 0,
                    'item_count': 0
                }
            
            valuation_by_category[category]['cost_value'] += level['stock_value']
            valuation_by_category[category]['selling_value'] += (
                level['current_stock'] * level['selling_price']
            )
            valuation_by_category[category]['item_count'] += 1
        
        return {
            'branch_id': branch_id,
            'total_cost_value': total_cost_value,
            'total_selling_value': total_selling_value,
            'potential_profit': potential_profit,
            'margin_percentage': (
                (potential_profit / total_cost_value * 100) 
                if total_cost_value > 0 else 0
            ),
            'valuation_by_category': valuation_by_category,
            'total_items': len(stock_levels),
            'valuation_date': datetime.now()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
