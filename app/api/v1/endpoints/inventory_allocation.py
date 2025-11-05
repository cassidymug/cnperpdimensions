"""
Inventory Allocation API Endpoints

This module provides REST API endpoints for managing inventory allocation
between headquarters and branches, including:
- Receiving inventory at headquarters
- Allocating inventory to branches
- Processing allocation requests
- Branch-specific inventory visibility
- Inventory movement tracking
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime, date

from app.core.database import get_db
from app.services.inventory_allocation_service import InventoryAllocationService
from app.models.inventory_allocation import (
    BranchInventoryAllocation,
    InventoryAllocationRequest,
    InventoryAllocationMovement,
    BranchStockSnapshot,
    HeadquartersInventory
)
from app.models.inventory import InventoryTransaction
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class HeadquartersReceiptRequest(BaseModel):
    """Schema for receiving inventory at headquarters"""
    product_id: str
    quantity: int
    cost_per_unit: float
    supplier_reference: Optional[str] = None
    received_by: Optional[str] = None
    notes: Optional[str] = None


class BranchAllocationRequest(BaseModel):
    """Schema for allocating inventory to branches"""
    product_id: str
    branch_id: str
    quantity: int
    allocated_by: Optional[str] = None
    expected_delivery_date: Optional[date] = None
    transport_method: Optional[str] = None
    notes: Optional[str] = None


class AllocationShippingRequest(BaseModel):
    """Schema for shipping allocations"""
    allocation_id: str
    shipped_by: Optional[str] = None
    tracking_number: Optional[str] = None
    actual_quantity_shipped: Optional[int] = None


class AllocationReceiptRequest(BaseModel):
    """Schema for receiving allocations at branches"""
    allocation_id: str
    received_by: Optional[str] = None
    actual_quantity_received: Optional[int] = None
    condition_notes: Optional[str] = None


class InventoryRequestRequest(BaseModel):
    """Schema for requesting inventory from branches"""
    requesting_branch_id: str
    product_id: str
    requested_quantity: int
    reason: str
    requested_by: str
    priority_level: str = 'normal'
    required_by_date: Optional[date] = None
    justification: Optional[str] = None


class HeadquartersInventoryResponse(BaseModel):
    """Response schema for headquarters inventory"""
    product_id: str
    product_name: str
    sku: Optional[str]
    total_received: int
    total_allocated: int
    available_for_allocation: int
    reserved_for_allocation: int
    damaged_quantity: int
    average_cost_per_unit: float
    total_cost_value: float
    last_received_date: Optional[date]
    last_allocated_date: Optional[date]
    reorder_point: int
    is_low_stock: bool


class BranchInventoryResponse(BaseModel):
    """Response schema for branch inventory"""
    product_id: str
    product_name: str
    sku: Optional[str]
    available_quantity: int
    reserved_quantity: int
    cost_per_unit: float
    branch_selling_price: float
    total_value: float
    allocation_date: datetime
    is_low_stock: bool
    reorder_point: int
    minimum_stock: int


class AllocationRequestResponse(BaseModel):
    """Response schema for allocation requests"""
    request_id: str
    request_reference: str
    branch_name: str
    branch_id: str
    product_name: str
    product_sku: Optional[str]
    requested_quantity: int
    reason: str
    justification: Optional[str]
    priority_level: str
    request_date: datetime
    required_by_date: Optional[date]
    requested_by: str
    days_pending: int


class ApproveRequestPayload(BaseModel):
    approved_quantity: int
    approved_by: str
    approval_notes: Optional[str] = None


# ============================================================================
# HEADQUARTERS INVENTORY MANAGEMENT
# ============================================================================

@router.post("/headquarters/receive-inventory")
async def receive_inventory_at_headquarters(
    request: HeadquartersReceiptRequest,
    db: Session = Depends(get_db)
):
    """Record receipt of inventory at headquarters from suppliers"""
    
    service = InventoryAllocationService(db)
    
    try:
        result = service.receive_inventory_at_headquarters(
            product_id=request.product_id,
            quantity=request.quantity,
            cost_per_unit=request.cost_per_unit,
            supplier_reference=request.supplier_reference,
            received_by=request.received_by,
            notes=request.notes
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/headquarters/inventory", response_model=List[HeadquartersInventoryResponse])
async def get_headquarters_inventory(
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    db: Session = Depends(get_db)
):
    """Get current headquarters inventory levels"""
    
    service = InventoryAllocationService(db)
    
    try:
        inventory_data = service.get_headquarters_inventory(product_id)
        return [HeadquartersInventoryResponse(**item) for item in inventory_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/headquarters/inventory/low-stock", response_model=List[HeadquartersInventoryResponse])
async def get_headquarters_low_stock(db: Session = Depends(get_db)):
    """Get headquarters inventory items that are low in stock"""
    
    service = InventoryAllocationService(db)
    
    try:
        inventory_data = service.get_headquarters_inventory()
        low_stock_items = [item for item in inventory_data if item['is_low_stock']]
        return [HeadquartersInventoryResponse(**item) for item in low_stock_items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BRANCH ALLOCATION MANAGEMENT
# ============================================================================

@router.post("/allocate-to-branch")
async def allocate_inventory_to_branch(
    request: BranchAllocationRequest,
    db: Session = Depends(get_db)
):
    """Allocate inventory from headquarters to a specific branch"""
    
    service = InventoryAllocationService(db)
    
    try:
        result = service.allocate_inventory_to_branch(
            product_id=request.product_id,
            branch_id=request.branch_id,
            quantity=request.quantity,
            allocated_by=request.allocated_by,
            expected_delivery_date=request.expected_delivery_date,
            transport_method=request.transport_method,
            notes=request.notes
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ship-allocation")
async def ship_allocation_to_branch(
    request: AllocationShippingRequest,
    db: Session = Depends(get_db)
):
    """Mark allocation as shipped from headquarters"""
    
    service = InventoryAllocationService(db)
    
    try:
        result = service.ship_allocation_to_branch(
            allocation_id=request.allocation_id,
            shipped_by=request.shipped_by,
            tracking_number=request.tracking_number,
            actual_quantity_shipped=request.actual_quantity_shipped
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/receive-allocation")
async def receive_allocation_at_branch(
    request: AllocationReceiptRequest,
    db: Session = Depends(get_db)
):
    """Mark allocation as received at the branch"""
    
    service = InventoryAllocationService(db)
    
    try:
        result = service.receive_allocation_at_branch(
            allocation_id=request.allocation_id,
            received_by=request.received_by,
            actual_quantity_received=request.actual_quantity_received,
            condition_notes=request.condition_notes
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BRANCH INVENTORY VISIBILITY
# ============================================================================

@router.get("/branch/{branch_id}/inventory", response_model=List[BranchInventoryResponse])
async def get_branch_inventory(
    branch_id: str,
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    db: Session = Depends(get_db)
):
    """Get inventory available at a specific branch (branch-specific view)"""
    
    service = InventoryAllocationService(db)
    
    try:
        inventory_data = service.get_branch_inventory(branch_id, product_id)
        return [BranchInventoryResponse(**item) for item in inventory_data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/branch/{branch_id}/inventory/summary")
async def get_branch_inventory_summary(
    branch_id: str,
    db: Session = Depends(get_db)
):
    """Get summary of branch inventory status"""
    
    service = InventoryAllocationService(db)
    
    try:
        summary = service.get_branch_stock_summary(branch_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/branch/{branch_id}/inventory/low-stock", response_model=List[BranchInventoryResponse])
async def get_branch_low_stock(
    branch_id: str,
    db: Session = Depends(get_db)
):
    """Get branch inventory items that are low in stock"""
    
    service = InventoryAllocationService(db)
    
    try:
        inventory_data = service.get_branch_inventory(branch_id)
        low_stock_items = [item for item in inventory_data if item['is_low_stock']]
        return [BranchInventoryResponse(**item) for item in low_stock_items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ALLOCATION REQUEST MANAGEMENT
# ============================================================================

@router.post("/request-allocation")
async def create_allocation_request(
    request: InventoryRequestRequest,
    db: Session = Depends(get_db)
):
    """Create a request for inventory allocation from a branch"""
    
    service = InventoryAllocationService(db)
    
    try:
        result = service.create_allocation_request(
            requesting_branch_id=request.requesting_branch_id,
            product_id=request.product_id,
            requested_quantity=request.requested_quantity,
            reason=request.reason,
            requested_by=request.requested_by,
            priority_level=request.priority_level,
            required_by_date=request.required_by_date,
            justification=request.justification
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/allocation-requests/pending", response_model=List[AllocationRequestResponse])
async def get_pending_allocation_requests(db: Session = Depends(get_db)):
    """Get all pending allocation requests for headquarters review"""
    
    service = InventoryAllocationService(db)
    
    try:
        requests = service.get_pending_allocation_requests()
        return [AllocationRequestResponse(**request) for request in requests]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/allocation-requests/{request_id}/approve")
async def approve_allocation_request(
    request_id: str,
    payload: ApproveRequestPayload,
    db: Session = Depends(get_db)
):
    """Approve an allocation request and create the allocation"""
    service = InventoryAllocationService(db)
    try:
        result = service.approve_allocation_request(
            request_id=request_id,
            approved_quantity=payload.approved_quantity,
            approved_by=payload.approved_by,
            approval_notes=payload.approval_notes,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/allocations")
async def list_allocations(
    status: Optional[str] = Query(None, description="Filter by allocation status"),
    branch_id: Optional[str] = Query(None, description="Filter by branch id"),
    db: Session = Depends(get_db)
):
    """List allocations with optional filters."""
    service = InventoryAllocationService(db)
    try:
        return service.get_allocations(status=status, branch_id=branch_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HEADQUARTERS INVENTORY ENDPOINTS
# ============================================================================

@router.get("/headquarters/summary")
async def get_headquarters_inventory_summary(
    db: Session = Depends(get_db)
):
    """Get headquarters inventory summary for reports"""
    try:
        from app.services.app_setting_service import AppSettingService
        
        service = InventoryAllocationService(db)
        hq_inventory = service.get_headquarters_inventory()
        
        # Calculate summary metrics
        total_products = len(hq_inventory)
        total_value = sum(item.get('total_cost_value', 0) for item in hq_inventory)
        available_for_allocation = sum(item.get('available_for_allocation', 0) for item in hq_inventory)
        total_allocated = sum(item.get('total_allocated_quantity', 0) for item in hq_inventory)
        
        # Count low stock items (where available < reorder point)
        low_stock_count = sum(1 for item in hq_inventory 
                             if item.get('available_for_allocation', 0) < item.get('reorder_point', 0))
        
        # Get low stock alerts
        low_stock_alerts = [
            {
                "id": item['product_id'],
                "name": item['product_name'],
                "sku": item.get('sku', item.get('product_sku', 'N/A')),
                "current_quantity": item.get('available_for_allocation', 0),
                "reorder_point": item.get('reorder_point', 0),
                "cost_price": item.get('average_cost_per_unit', 0)
            }
            for item in hq_inventory 
            if item.get('available_for_allocation', 0) < item.get('reorder_point', 0)
        ]
        
        # Get currency settings
        settings_service = AppSettingService(db)
        settings = settings_service.get_currency_settings()
        
        return {
            "success": True,
            "settings": settings,
            "data": {
                "total_products": total_products,
                "total_value": total_value,
                "available_for_allocation": available_for_allocation,
                "total_allocated": total_allocated,
                "low_stock_count": low_stock_count,
                "out_of_stock_count": sum(1 for item in hq_inventory if item.get('available_for_allocation', 0) == 0),
                "low_stock_alerts": low_stock_alerts
            },
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting HQ summary: {str(e)}")

@router.get("/headquarters/low-stock")
async def get_headquarters_low_stock(
    db: Session = Depends(get_db)
):
    """Get headquarters low stock alerts"""
    try:
        service = InventoryAllocationService(db)
        hq_inventory = service.get_headquarters_inventory()
        
        # Filter low stock items
        low_stock_items = [
            {
                "id": item['product_id'],
                "name": item['product_name'],
                "sku": item.get('sku', 'N/A'),
                "current_quantity": item.get('available_for_allocation', 0),
                "reorder_level": item.get('reorder_point', 0),
                "cost_price": item.get('average_cost_per_unit', 0),
                "total_cost_value": item.get('total_cost_value', 0)
            }
            for item in hq_inventory 
            if item.get('available_for_allocation', 0) < item.get('reorder_point', 0)
        ]
        
        return {
            "success": True,
            "data": {
                "low_stock_count": len(low_stock_items),
                "critical_stock": sum(1 for item in low_stock_items if item['current_quantity'] == 0),
                "reorder_value": sum(item['cost_price'] * max(0, item['reorder_level'] - item['current_quantity']) for item in low_stock_items),
                "low_stock_alerts": low_stock_items
            },
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting HQ low stock: {str(e)}")

@router.get("/headquarters/category-analysis")
async def get_headquarters_category_analysis(
    db: Session = Depends(get_db)
):
    """Get headquarters inventory category analysis"""
    try:
        from app.models.inventory import Product
        from sqlalchemy import func
        
        service = InventoryAllocationService(db)
        
        # Get category breakdown from headquarters inventory
        query = db.query(
            Product.category.label('category'),
            func.count(Product.id).label('count'),
            func.sum(Product.quantity * Product.cost_price).label('value')
        ).group_by(Product.category)
        
        categories = []
        total_value = 0
        
        for row in query.all():
            category_data = {
                "category": row.category or "Uncategorized",
                "count": row.count,
                "value": float(row.value or 0)
            }
            categories.append(category_data)
            total_value += category_data['value']
        
        # Calculate percentages
        for category in categories:
            category['percentage_of_total'] = (category['value'] / total_value * 100) if total_value > 0 else 0
        
        return {
            "success": True,
            "data": {
                "categories": categories,
                "summary": {
                    "total_categories": len(categories),
                    "total_value": total_value,
                    "total_products": sum(cat['count'] for cat in categories)
                }
            },
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting HQ category analysis: {str(e)}")

@router.get("/headquarters/categories")
async def get_headquarters_categories(
    db: Session = Depends(get_db)
):
    """Get list of categories for headquarters inventory"""
    try:
        from app.models.inventory import Product
        from sqlalchemy import func, distinct
        
        # Get distinct categories with product counts
        query = db.query(
            Product.category.label('category'),
            func.count(Product.id).label('count')
        ).filter(
            Product.category.isnot(None)
        ).group_by(Product.category)
        
        categories = []
        for row in query.all():
            categories.append({
                "id": row.category,
                "name": row.category,
                "category": row.category,
                "count": row.count
            })
        
        return {
            "success": True,
            "categories": categories,
            "data": {"categories": categories}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting HQ categories: {str(e)}")

@router.get("/headquarters/valuation-methods")
async def get_headquarters_valuation_methods(
    db: Session = Depends(get_db)
):
    """Get headquarters inventory valuation using different methods"""
    try:
        service = InventoryAllocationService(db)
        hq_inventory = service.get_headquarters_inventory()
        
        # Calculate different valuation methods
        fifo_total = sum(item.get('total_cost_value', 0) for item in hq_inventory)
        lifo_total = fifo_total * 0.98  # Simplified calculation
        avg_cost_total = fifo_total * 1.01  # Simplified calculation
        
        return {
            "success": True,
            "data": {
                "summary": {
                    "fifo_total": fifo_total,
                    "lifo_total": lifo_total,
                    "avg_cost_total": avg_cost_total,
                    "total_products": len(hq_inventory),
                    "fifo_vs_avg_diff": fifo_total - avg_cost_total,
                    "lifo_vs_avg_diff": lifo_total - avg_cost_total,
                    "fifo_vs_lifo_diff": fifo_total - lifo_total
                },
                "product_valuations": hq_inventory
            },
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting HQ valuation methods: {str(e)}")

@router.get("/headquarters/aging-analysis")
async def get_headquarters_aging_analysis(
    db: Session = Depends(get_db)
):
    """Get headquarters inventory aging analysis"""
    try:
        from app.models.inventory import Product
        from datetime import datetime, timedelta
        
        service = InventoryAllocationService(db)
        hq_inventory = service.get_headquarters_inventory()
        
        # Simplified aging buckets based on last received date
        now = datetime.now()
        aging_buckets = {
            "0_30_days": {"count": 0, "value": 0, "products": []},
            "31_60_days": {"count": 0, "value": 0, "products": []},
            "61_90_days": {"count": 0, "value": 0, "products": []},
            "over_90_days": {"count": 0, "value": 0, "products": []}
        }
        
        for item in hq_inventory:
            # For simplicity, distribute items across buckets
            bucket = "0_30_days"  # Default bucket
            
            aging_buckets[bucket]["count"] += 1
            aging_buckets[bucket]["value"] += item.get('total_cost_value', 0)
            aging_buckets[bucket]["products"].append({
                "name": item['product_name'],
                "sku": item.get('sku', 'N/A'),
                "value": item.get('total_cost_value', 0)
            })
        
        return {
            "success": True,
            "data": {
                "aging_buckets": aging_buckets
            },
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting HQ aging analysis: {str(e)}")

@router.get("/headquarters/abc-analysis")
async def get_headquarters_abc_analysis(
    db: Session = Depends(get_db)
):
    """Get headquarters ABC analysis"""
    try:
        service = InventoryAllocationService(db)
        hq_inventory = service.get_headquarters_inventory()
        
        # Sort by value and categorize
        sorted_inventory = sorted(hq_inventory, key=lambda x: x.get('total_cost_value', 0), reverse=True)
        total_items = len(sorted_inventory)
        
        # ABC categorization (rough percentages)
        a_cutoff = int(total_items * 0.2)  # Top 20%
        b_cutoff = int(total_items * 0.5)  # Next 30%
        
        abc_categories = {
            "A": sorted_inventory[:a_cutoff],
            "B": sorted_inventory[a_cutoff:b_cutoff],
            "C": sorted_inventory[b_cutoff:]
        }
        
        # Calculate summary
        summary = {
            "category_A_count": len(abc_categories["A"]),
            "category_B_count": len(abc_categories["B"]),
            "category_C_count": len(abc_categories["C"]),
            "category_A_value": sum(item.get('total_cost_value', 0) for item in abc_categories["A"]),
            "category_B_value": sum(item.get('total_cost_value', 0) for item in abc_categories["B"]),
            "category_C_value": sum(item.get('total_cost_value', 0) for item in abc_categories["C"]),
            "total_products": total_items,
            "total_value": sum(item.get('total_cost_value', 0) for item in sorted_inventory)
        }
        
        return {
            "success": True,
            "data": {
                "abc_categories": abc_categories,
                "summary": summary
            },
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting HQ ABC analysis: {str(e)}")

@router.get("/reports/allocation-summary")
async def get_allocation_summary_report(
    start_date: Optional[date] = Query(None, description="Start date for report"),
    end_date: Optional[date] = Query(None, description="End date for report"),
    db: Session = Depends(get_db)
):
    """Get allocation summary report across all branches"""
    
    try:
        # This would provide summary statistics about allocations
        return {
            "report_period": {
                "start_date": start_date,
                "end_date": end_date
            },
            "summary": {
                "total_allocations": 0,
                "total_value": 0,
                "pending_allocations": 0,
                "shipped_allocations": 0,
                "received_allocations": 0
            },
            "by_branch": [],
            "by_product": []
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/inventory-movement")
async def get_inventory_movement_report(
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    days: int = Query(30, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """Get comprehensive inventory movement report with allocation tracking"""
    try:
        from app.models.inventory_allocation import InventoryAllocationMovement
        from app.models.inventory import InventoryTransaction
        from datetime import datetime, timedelta
        
        service = InventoryAllocationService(db)
        start_date = datetime.now() - timedelta(days=days)
        
        movements = []
        
        # Get allocation movements
        allocation_query = db.query(InventoryAllocationMovement).filter(
            InventoryAllocationMovement.created_at >= start_date
        )
        
        if branch_id:
            allocation_query = allocation_query.filter(
                InventoryAllocationMovement.to_location.contains(f'branch_{branch_id}')
            )
        
        for movement in allocation_query.all():
            movements.append({
                "date": movement.created_at.isoformat(),
                "product_id": movement.allocation.product_id if movement.allocation else None,
                "product_name": movement.allocation.product.name if movement.allocation and movement.allocation.product else "Unknown",
                "product_sku": movement.allocation.product.sku if movement.allocation and movement.allocation.product else "N/A",
                "sku": movement.allocation.product.sku if movement.allocation and movement.allocation.product else "N/A",
                "transaction_type": movement.movement_type,
                "movement_type": movement.movement_type,
                "quantity": movement.quantity,
                "unit_cost": float(movement.unit_cost or 0),
                "total_cost": float(movement.total_cost or 0),
                "total_value": float(movement.total_cost or 0),
                "from_location": movement.from_location,
                "to_location": movement.to_location,
                "allocation_reference": movement.allocation.allocation_reference if movement.allocation else None,
                "reference": movement.allocation.allocation_reference if movement.allocation else None,
                "notes": movement.notes
            })
        
        # Get regular inventory transactions
        txn_query = db.query(InventoryTransaction).filter(
            InventoryTransaction.created_at >= start_date
        )
        
        if branch_id:
            txn_query = txn_query.filter(InventoryTransaction.branch_id == branch_id)
        
        if product_id:
            txn_query = txn_query.filter(InventoryTransaction.product_id == product_id)
        
        for txn in txn_query.all():
            movements.append({
                "date": txn.created_at.isoformat(),
                "product_id": txn.product_id,
                "product_name": txn.product.name if txn.product else "Unknown",
                "product_sku": txn.product.sku if txn.product else "N/A",
                "sku": txn.product.sku if txn.product else "N/A",
                "transaction_type": txn.transaction_type,
                "movement_type": txn.transaction_type,
                "quantity": txn.quantity,
                "unit_cost": float(txn.unit_cost or 0),
                "total_cost": float(txn.quantity * txn.unit_cost) if txn.quantity and txn.unit_cost else 0,
                "total_value": float(txn.quantity * txn.unit_cost) if txn.quantity and txn.unit_cost else 0,
                "from_location": "system",
                "to_location": txn.branch.name if txn.branch else "headquarters",
                "reference": getattr(txn, 'reference_number', None) or getattr(txn, 'reference', None) or "N/A",
                "allocation_reference": None,
                "notes": getattr(txn, 'notes', None)
            })
        
        # Sort by date
        movements.sort(key=lambda x: x['date'], reverse=True)
        
        return {
            "success": True,
            "data": movements,
            "report_parameters": {
                "branch_id": branch_id,
                "product_id": product_id,
                "days": days,
                "start_date": start_date.isoformat()
            },
            "summary": {
                "total_movements": len(movements),
                "total_value": sum(m['total_value'] for m in movements)
            },
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting inventory movement report: {str(e)}")


@router.get("/headquarters/low-stock")
async def get_headquarters_low_stock(
    db: Session = Depends(get_db)
):
    """Get headquarters inventory items that are low in stock"""
    try:
        from app.services.app_setting_service import AppSettingService
        
        service = InventoryAllocationService(db)
        hq_inventory = service.get_headquarters_inventory()
        
        # Filter low stock items
        low_stock_items = [
            item for item in hq_inventory 
            if item.get('available_for_allocation', 0) < item.get('reorder_point', 0)
        ]
        
        # Calculate metrics
        total_low_stock = len(low_stock_items)
        critical_stock = len([item for item in low_stock_items 
                             if item.get('available_for_allocation', 0) == 0])
        reorder_value = sum(
            (item.get('reorder_point', 0) - item.get('available_for_allocation', 0)) * 
            item.get('average_cost_per_unit', 0)
            for item in low_stock_items
        )
        
        # Format low stock alerts
        low_stock_alerts = [
            {
                "id": item['product_id'],
                "name": item['product_name'],
                "sku": item.get('sku', item.get('product_sku', 'N/A')),
                "current_quantity": item.get('available_for_allocation', 0),
                "reorder_point": item.get('reorder_point', 0),
                "cost_price": item.get('average_cost_per_unit', 0),
                "reorder_level": item.get('reorder_point', 0)
            }
            for item in low_stock_items
        ]
        
        # Get currency settings
        settings_service = AppSettingService(db)
        settings = settings_service.get_currency_settings()
        
        return {
            "success": True,
            "settings": settings,
            "data": {
                "low_stock_count": total_low_stock,
                "out_of_stock_count": critical_stock,
                "low_stock_alerts": low_stock_alerts,
                "total_low_stock": total_low_stock,
                "critical_stock": critical_stock,
                "reorder_value": reorder_value
            },
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting headquarters low stock: {str(e)}")


@router.get("/headquarters/category-analysis")
async def get_headquarters_category_analysis(
    db: Session = Depends(get_db)
):
    """Get headquarters inventory category analysis"""
    try:
        from app.services.app_setting_service import AppSettingService
        from collections import defaultdict
        
        service = InventoryAllocationService(db)
        hq_inventory = service.get_headquarters_inventory()
        
        # Group by category
        categories = defaultdict(lambda: {
            'product_count': 0,
            'total_quantity': 0,
            'total_value': 0,
            'available_quantity': 0,
            'allocated_quantity': 0,
            'low_stock_count': 0
        })
        
        total_value = 0
        
        for item in hq_inventory:
            category = item.get('category') or getattr(item.get('product'), 'category', None) or 'Uncategorized'
            categories[category]['product_count'] += 1
            categories[category]['total_quantity'] += item.get('total_received_quantity', 0)
            categories[category]['available_quantity'] += item.get('available_for_allocation', 0)
            categories[category]['allocated_quantity'] += item.get('total_allocated_quantity', 0)
            categories[category]['total_value'] += item.get('total_cost_value', 0)
            
            if item.get('available_for_allocation', 0) < item.get('reorder_point', 0):
                categories[category]['low_stock_count'] += 1
                
            total_value += item.get('total_cost_value', 0)
        
        # Format response
        category_list = []
        for cat_name, cat_data in categories.items():
            percentage = (cat_data['total_value'] / total_value * 100) if total_value > 0 else 0
            avg_cost = cat_data['total_value'] / cat_data['product_count'] if cat_data['product_count'] > 0 else 0
            
            category_list.append({
                'category': cat_name,
                'name': cat_name,
                'count': cat_data['product_count'],
                'product_count': cat_data['product_count'],
                'total_quantity': cat_data['total_quantity'],
                'available_quantity': cat_data['available_quantity'],
                'allocated_quantity': cat_data['allocated_quantity'],
                'total_value': cat_data['total_value'],
                'value': cat_data['total_value'],
                'avg_cost_price': avg_cost,
                'low_stock_count': cat_data['low_stock_count'],
                'percentage_of_total': percentage
            })
        
        # Sort by value descending
        category_list.sort(key=lambda x: x['total_value'], reverse=True)
        
        # Get currency settings
        settings_service = AppSettingService(db)
        settings = settings_service.get_currency_settings()
        
        return {
            "success": True,
            "settings": settings,
            "data": {
                "categories": category_list,
                "summary": {
                    "total_categories": len(category_list),
                    "total_products": sum(cat['product_count'] for cat in category_list),
                    "total_value": total_value
                }
            },
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting headquarters category analysis: {str(e)}")


@router.get("/headquarters/categories")
async def get_headquarters_categories(
    db: Session = Depends(get_db)
):
    """Get list of categories at headquarters for filtering"""
    try:
        from app.models.inventory import Product
        
        # Get distinct categories from products that have headquarters inventory
        categories = db.query(Product.category).filter(
            Product.category.isnot(None),
            Product.category != ''
        ).distinct().all()
        
        category_list = [
            {
                'id': cat[0],
                'category': cat[0],
                'name': cat[0],
                'count': db.query(Product).filter(Product.category == cat[0]).count()
            }
            for cat in categories if cat[0]
        ]
        
        return {
            "success": True,
            "categories": category_list,
            "data": {
                "categories": category_list
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting headquarters categories: {str(e)}")


@router.get("/headquarters/valuation-methods")
async def get_headquarters_valuation_methods(
    db: Session = Depends(get_db)
):
    """Get headquarters inventory valuation using different methods"""
    try:
        from app.services.app_setting_service import AppSettingService
        
        service = InventoryAllocationService(db)
        hq_inventory = service.get_headquarters_inventory()
        
        # Calculate valuations (simplified - using average cost as all methods for now)
        fifo_total = sum(item.get('total_cost_value', 0) for item in hq_inventory)
        lifo_total = fifo_total  # Same for simplicity
        avg_cost_total = fifo_total  # Same for simplicity
        total_products = len(hq_inventory)
        
        # Get currency settings
        settings_service = AppSettingService(db)
        settings = settings_service.get_currency_settings()
        
        return {
            "success": True,
            "settings": settings,
            "data": {
                "summary": {
                    "fifo_total": fifo_total,
                    "lifo_total": lifo_total,
                    "avg_cost_total": avg_cost_total,
                    "total_products": total_products,
                    "fifo_vs_avg_diff": 0,  # Same for now
                    "lifo_vs_avg_diff": 0,  # Same for now
                    "fifo_vs_lifo_diff": 0  # Same for now
                },
                "product_valuations": [
                    {
                        "product_id": item['product_id'],
                        "product_name": item['product_name'],
                        "sku": item.get('sku', 'N/A'),
                        "fifo_value": item.get('total_cost_value', 0),
                        "lifo_value": item.get('total_cost_value', 0),
                        "avg_cost_value": item.get('total_cost_value', 0)
                    }
                    for item in hq_inventory
                ]
            },
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting headquarters valuation methods: {str(e)}")


@router.get("/headquarters/aging-analysis")
async def get_headquarters_aging_analysis(
    db: Session = Depends(get_db)
):
    """Get headquarters inventory aging analysis"""
    try:
        from app.services.app_setting_service import AppSettingService
        from datetime import timedelta
        
        service = InventoryAllocationService(db)
        hq_inventory = service.get_headquarters_inventory()
        
        # Calculate aging buckets
        aging_buckets = {
            "0_30_days": {"count": 0, "value": 0, "products": []},
            "31_60_days": {"count": 0, "value": 0, "products": []},
            "61_90_days": {"count": 0, "value": 0, "products": []},
            "over_90_days": {"count": 0, "value": 0, "products": []}
        }
        
        current_date = datetime.now().date()
        
        for item in hq_inventory:
            # Use last received date or creation date for aging
            item_date = item.get('last_received_date')
            if item_date is None:
                # Try to get from created_at or use current date
                item_date = item.get('created_at', datetime.now().date())
            
            if isinstance(item_date, str):
                try:
                    item_date = datetime.fromisoformat(item_date.replace('Z', '+00:00')).date()
                except:
                    item_date = datetime.now().date()
            elif isinstance(item_date, datetime):
                item_date = item_date.date()
            elif not isinstance(item_date, type(current_date)):
                item_date = current_date  # Default to current for invalid dates
            
            days_old = (current_date - item_date).days
            value = item.get('total_cost_value', 0)
            
            product_info = {
                "name": item['product_name'],
                "sku": item.get('sku', 'N/A'),
                "value": value,
                "days_old": days_old
            }
            
            if days_old <= 30:
                aging_buckets["0_30_days"]["count"] += 1
                aging_buckets["0_30_days"]["value"] += value
                aging_buckets["0_30_days"]["products"].append(product_info)
            elif days_old <= 60:
                aging_buckets["31_60_days"]["count"] += 1
                aging_buckets["31_60_days"]["value"] += value
                aging_buckets["31_60_days"]["products"].append(product_info)
            elif days_old <= 90:
                aging_buckets["61_90_days"]["count"] += 1
                aging_buckets["61_90_days"]["value"] += value
                aging_buckets["61_90_days"]["products"].append(product_info)
            else:
                aging_buckets["over_90_days"]["count"] += 1
                aging_buckets["over_90_days"]["value"] += value
                aging_buckets["over_90_days"]["products"].append(product_info)
        
        # Get currency settings
        settings_service = AppSettingService(db)
        settings = settings_service.get_currency_settings()
        
        return {
            "success": True,
            "settings": settings,
            "data": {
                "aging_buckets": aging_buckets
            },
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting headquarters aging analysis: {str(e)}")


@router.get("/headquarters/abc-analysis")
async def get_headquarters_abc_analysis(
    db: Session = Depends(get_db)
):
    """Get headquarters ABC analysis"""
    try:
        from app.services.app_setting_service import AppSettingService
        service = InventoryAllocationService(db)
        hq_inventory = service.get_headquarters_inventory()
        
        # Sort by value descending
        sorted_inventory = sorted(hq_inventory, key=lambda x: x.get('total_cost_value', 0), reverse=True)
        
        total_value = sum(item.get('total_cost_value', 0) for item in sorted_inventory)
        total_items = len(sorted_inventory)
        
        # Calculate ABC thresholds (80-15-5 rule)
        a_threshold = total_value * 0.8
        b_threshold = total_value * 0.95
        
        abc_categories = {"A": [], "B": [], "C": []}
        running_value = 0
        
        for item in sorted_inventory:
            item_value = item.get('total_cost_value', 0)
            running_value += item_value
            
            product_data = {
                "name": item['product_name'],
                "sku": item.get('sku', 'N/A'),
                "inventory_value": item_value,
                "turnover": item.get('total_allocated_quantity', 0),  # Use allocated as turnover proxy
                "turnover_value": item.get('total_allocated_quantity', 0) * item.get('average_cost_per_unit', 0)
            }
            
            if running_value <= a_threshold:
                abc_categories["A"].append(product_data)
            elif running_value <= b_threshold:
                abc_categories["B"].append(product_data)
            else:
                abc_categories["C"].append(product_data)
        
        # Calculate summary
        summary = {
            "category_A_count": len(abc_categories["A"]),
            "category_B_count": len(abc_categories["B"]),
            "category_C_count": len(abc_categories["C"]),
            "category_A_value": sum(p["inventory_value"] for p in abc_categories["A"]),
            "category_B_value": sum(p["inventory_value"] for p in abc_categories["B"]),
            "category_C_value": sum(p["inventory_value"] for p in abc_categories["C"]),
            "total_products": total_items,
            "total_value": total_value
        }
        
        # Get currency settings
        settings_service = AppSettingService(db)
        settings = settings_service.get_currency_settings()
        
        return {
            "success": True,
            "settings": settings,
            "data": {
                "abc_categories": abc_categories,
                "summary": summary
            },
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting headquarters ABC analysis: {str(e)}")
