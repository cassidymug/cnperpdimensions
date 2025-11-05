from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, date, timedelta
import logging
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

from app.core.database import get_db
from app.models.cost_accounting import (
    ManufacturingCost, MaterialCostEntry,
    LaborCostEntry, OverheadCostEntry
)
from app.models.inventory import Product, UnitOfMeasure
from app.models.branch import Branch
from app.schemas.manufacturing import (
    ManufacturingCostCreate, ManufacturingCost as ManufacturingCostResponse,
    ManufacturingCostUpdate, ManufacturingStats
)
from app.schemas.inventory import ProductResponse
from app.services.manufacturing_service import ManufacturingService

router = APIRouter()


@router.post("/costs", response_model=ManufacturingCostResponse)
def create_manufacturing_cost(
    manufacturing_cost: ManufacturingCostCreate,
    db: Session = Depends(get_db)
):
    """Create a new manufacturing cost record."""
    product = db.query(Product).filter(Product.id == manufacturing_cost.product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    total_cost = (manufacturing_cost.material_cost or 0) + \
                 (manufacturing_cost.labor_cost or 0) + \
                 (manufacturing_cost.overhead_cost or 0)

    unit_cost = total_cost / manufacturing_cost.quantity if manufacturing_cost.quantity > 0 else 0

    db_manufacturing_cost = ManufacturingCost(
        **manufacturing_cost.dict(),
        total_cost=total_cost,
        unit_cost=unit_cost
    )

    db.add(db_manufacturing_cost)
    db.commit()
    db.refresh(db_manufacturing_cost)

    return db_manufacturing_cost


@router.get("/costs", response_model=List[ManufacturingCostResponse])
def read_manufacturing_costs(
    skip: int = 0,
    limit: int = 100,
    product_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all manufacturing costs with optional filtering"""
    query = db.query(ManufacturingCost)

    if product_id:
        query = query.filter(ManufacturingCost.product_id == product_id)

    if status:
        query = query.filter(ManufacturingCost.status == status)

    manufacturing_costs = query.offset(skip).limit(limit).all()

    # Add product details for each record
    for cost in manufacturing_costs:
        product = db.query(Product).filter(Product.id == cost.product_id).first()
        if product:
            setattr(cost, "product_name", product.name)
            setattr(cost, "product_sku", product.sku)

    return manufacturing_costs


@router.get("/costs/{manufacturing_id}", response_model=ManufacturingCostResponse)
def read_manufacturing_cost(
    manufacturing_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific manufacturing cost record by ID"""
    manufacturing_cost = db.query(ManufacturingCost).filter(ManufacturingCost.id == manufacturing_id).first()
    if not manufacturing_cost:
        raise HTTPException(status_code=404, detail="Manufacturing cost record not found")

    # Add product details
    product = db.query(Product).filter(Product.id == manufacturing_cost.product_id).first()
    if product:
        setattr(manufacturing_cost, "product_name", product.name)
        setattr(manufacturing_cost, "product_sku", product.sku)

    return manufacturing_cost


@router.put("/costs/{manufacturing_id}", response_model=ManufacturingCostResponse)
def update_manufacturing_cost(
    manufacturing_id: int,
    manufacturing_cost: ManufacturingCostUpdate,
    db: Session = Depends(get_db)
):
    """Update a manufacturing cost record."""
    db_manufacturing_cost = db.query(ManufacturingCost).filter(ManufacturingCost.id == manufacturing_id).first()
    if not db_manufacturing_cost:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manufacturing cost record not found")

    update_data = manufacturing_cost.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_manufacturing_cost, key, value)

    total_cost = (db_manufacturing_cost.material_cost or 0) + \
                 (db_manufacturing_cost.labor_cost or 0) + \
                 (db_manufacturing_cost.overhead_cost or 0)

    unit_cost = total_cost / db_manufacturing_cost.quantity if db_manufacturing_cost.quantity > 0 else 0

    db_manufacturing_cost.total_cost = total_cost
    db_manufacturing_cost.unit_cost = unit_cost

    db.commit()
    db.refresh(db_manufacturing_cost)

    return db_manufacturing_cost


@router.delete("/costs/{manufacturing_id}", status_code=204)
def delete_manufacturing_cost(
    manufacturing_id: int,
    db: Session = Depends(get_db)
):
    """Delete a manufacturing cost record"""
    db_manufacturing_cost = db.query(ManufacturingCost).filter(ManufacturingCost.id == manufacturing_id).first()
    if not db_manufacturing_cost:
        raise HTTPException(status_code=404, detail="Manufacturing cost record not found")

    db.delete(db_manufacturing_cost)
    db.commit()

    return None


@router.get("/products")
def get_manufacturing_products(
    db: Session = Depends(get_db),
    product_type: Optional[str] = Query(None, description="Filter by product type: tangible, digital, service, license, intangible"),
    active_only: bool = Query(True, description="Show only active products")
):
    """Get products suitable for manufacturing with optional filtering"""
    query = db.query(Product)

    if active_only:
        query = query.filter(Product.active == True)

    # Filter by product type if specified
    if product_type:
        if product_type == "tangible":
            query = query.filter(or_(Product.category == "tangible", Product.category == "manufactured", Product.category.is_(None)))
        elif product_type == "digital":
            query = query.filter(Product.category.in_(["digital", "software", "airtime", "subscription"]))
        elif product_type == "service":
            query = query.filter(Product.category == "service")
        elif product_type == "license":
            query = query.filter(Product.category.in_(["license", "intellectual_property"]))
        elif product_type == "intangible":
            query = query.filter(Product.category.in_(["intangible", "patent", "trademark", "brand"]))

    products = query.order_by(Product.name).all()

    # Convert to dict format to avoid schema issues
    result = []
    for product in products:
        category = product.category or "tangible"
        if category in ["digital", "software", "airtime", "subscription"]:
            product_type_classified = "digital"
        elif category in ["license", "intellectual_property"]:
            product_type_classified = "license"
        elif category in ["intangible", "patent", "trademark", "brand"]:
            product_type_classified = "intangible"
        elif category == "service":
            product_type_classified = "service"
        else:
            product_type_classified = "tangible"

        result.append({
            "id": str(product.id),
            "name": product.name,
            "sku": product.sku,
            "description": product.description,
            "category": product.category,
            "product_type": product_type_classified,
            "unit_price": float(product.selling_price) if getattr(product, 'selling_price', None) else 0.0,
            "cost_price": float(product.cost_price) if product.cost_price else 0.0,
            "is_active": product.active,
            "stock_quantity": getattr(product, 'stock_quantity', 0)
        })

    return result


@router.get("/stats", response_model=ManufacturingStats)
def get_manufacturing_stats(
    db: Session = Depends(get_db),
    start_date: Optional[date] = Query(None, description="Filter from date"),
    end_date: Optional[date] = Query(None, description="Filter to date")
):
    """Get manufacturing cost statistics"""
    service = ManufacturingService(db)
    return service.get_stats(start_date=start_date, end_date=end_date)


@router.get("/cost-breakdown")
def get_cost_breakdown(
    db: Session = Depends(get_db),
    product_id: Optional[str] = Query(None, description="Filter by product ID")
) -> Dict[str, Any]:
    """Get detailed cost breakdown for analysis"""
    query = db.query(ManufacturingCost)

    if product_id:
        query = query.filter(ManufacturingCost.product_id == product_id)

    manufacturing_costs = query.all()

    # Calculate cost allocation percentages
    total_cost = sum(mc.total_cost for mc in manufacturing_costs)
    total_material = sum(mc.material_cost for mc in manufacturing_costs)
    total_labor = sum(mc.labor_cost for mc in manufacturing_costs)
    total_overhead = sum(mc.overhead_cost for mc in manufacturing_costs)

    if total_cost > 0:
        material_pct = (total_material / total_cost) * 100
        labor_pct = (total_labor / total_cost) * 100
        overhead_pct = (total_overhead / total_cost) * 100
    else:
        material_pct = labor_pct = overhead_pct = 0

    return {
        "cost_allocation": [
            {"category": "Direct Materials", "amount": total_material, "percentage": material_pct},
            {"category": "Direct Labor", "amount": total_labor, "percentage": labor_pct},
            {"category": "Manufacturing Overhead", "amount": total_overhead, "percentage": overhead_pct}
        ],
        "total_cost": total_cost,
        "average_unit_cost": sum(mc.unit_cost for mc in manufacturing_costs) / len(manufacturing_costs) if manufacturing_costs else 0
    }


@router.get("/products/{product_id}/details")
def get_product_manufacturing_details(
    product_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get detailed manufacturing information for a specific product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Get manufacturing costs for this product
    manufacturing_costs = db.query(ManufacturingCost).filter(
        ManufacturingCost.product_id == product_id
    ).all()

    # Calculate cost summaries
    total_costs = {
        "material_cost": sum(mc.material_cost for mc in manufacturing_costs),
        "labor_cost": sum(mc.labor_cost for mc in manufacturing_costs),
        "overhead_cost": sum(mc.overhead_cost for mc in manufacturing_costs),
        "total_cost": sum(mc.total_cost for mc in manufacturing_costs)
    }

    # Calculate average unit cost
    total_units = sum(mc.batch_size for mc in manufacturing_costs)
    avg_unit_cost = total_costs["total_cost"] / total_units if total_units > 0 else 0

    return {
        "product": {
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "category": product.category,
            "description": product.description,
            "is_active": product.active
        },
        "cost_summary": total_costs,
        "unit_cost": avg_unit_cost,
        "total_batches": len(manufacturing_costs),
        "total_units_produced": total_units,
        "recent_costs": [
            {
                "id": mc.id,
                "date": mc.date.isoformat() if mc.date else None,
                "batch_number": mc.batch_number,
                "batch_size": mc.batch_size,
                "unit_cost": mc.unit_cost,
                "total_cost": mc.total_cost,
                "status": mc.status
            }
            for mc in sorted(manufacturing_costs, key=lambda x: x.date or datetime.min, reverse=True)[:10]
        ]
    }


@router.get("/products/{product_id}/bom")
def get_product_bom(
    product_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get the bill of materials for an assembled product."""
    service = ManufacturingService(db)
    try:
        items = service.get_bom(product_id)
        return {"product_id": product_id, "bom": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/produce-to-hq")
def produce_to_headquarters(
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Produce finished goods to HQ by consuming BOM components from HQ inventory.

    Payload: { product_id: str, quantity: int, labor_cost?: float, overhead_cost?: float, created_by?: str, notes?: str }
    """
    service = ManufacturingService(db)
    try:
        product_id = payload.get("product_id")
        quantity = int(payload.get("quantity") or 0)
        labor_cost = float(payload.get("labor_cost") or 0)
        overhead_cost = float(payload.get("overhead_cost") or 0)
        created_by = payload.get("created_by")
        notes = payload.get("notes")
        if not product_id or quantity <= 0:
            raise HTTPException(status_code=400, detail="product_id and positive quantity are required")
        return service.produce_to_hq(
            product_id=product_id,
            quantity=quantity,
            labor_cost=labor_cost,
            overhead_cost=overhead_cost,
            created_by=created_by,
            notes=notes,
        )
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/products")
def create_manufacturing_product(
    product_data: dict,
    db: Session = Depends(get_db)
):
    """Create a new product for manufacturing (simplified endpoint)"""
    try:
        # Check if product code already exists
        existing = db.query(Product).filter(Product.sku == product_data.get("productCode")).first()
        if existing:
            raise HTTPException(status_code=400, detail="Product code already exists")

        # Validate required fields
        if not product_data.get("productName") or not product_data.get("productCode"):
            raise HTTPException(status_code=400, detail="Product name and code are required")

        # Optional fields
        category = product_data.get("category") or product_data.get("productType") or "manufactured"
        uom_id = product_data.get("unitOfMeasureId")
        unit_price = float(product_data.get("unitPrice") or 0)

        # Get a branch (required for product)
        branch = db.query(Branch).first()
        if not branch:
            raise HTTPException(status_code=400, detail="No branch available for product creation")

        # Create basic product record
        db_product = Product(
            name=product_data.get("productName"),
            sku=product_data.get("productCode"),
            description=product_data.get("productDescription", ""),
            category=category,
            selling_price=unit_price,  # Selling price can be provided; cost will be computed from production
            cost_price=0.0,  # Initial; updated as production occurs
            unit_of_measure_id=uom_id,
            branch_id=branch.id,
            active=True
        )

        db.add(db_product)
        db.commit()
        db.refresh(db_product)

        # Return dict format to avoid schema issues
        return {
            "id": str(db_product.id),
            "name": db_product.name,
            "sku": db_product.sku,
            "description": db_product.description,
            "category": db_product.category,
            "unit_price": float(db_product.selling_price or 0),
            "cost_price": float(db_product.cost_price),
            "is_active": db_product.active
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error creating manufacturing product: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error creating product")


@router.post("/products/{product_id}/bom")
def set_product_bom(
    product_id: str,
    payload: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Replace BOM for a product. Payload: { items: [{component_id, quantity, unit_cost?, notes?}, ...] }"""
    service = ManufacturingService(db)
    try:
        items = payload.get("items") or []
        return service.set_bom(product_id, items)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# ACCOUNTING INTEGRATION ENDPOINTS
# ============================================

@router.post("/production-orders/{order_id}/post-accounting")
def post_production_order_to_accounting(
    order_id: str,
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Post a production order's costs to the General Ledger.
    Creates journal entries for WIP, Labor, and offset with dimensional assignments.

    Returns:
    {
        "success": bool,
        "production_order_id": str,
        "entries_created": int,
        "journal_entry_ids": [str],
        "total_amount": float,
        "posting_date": str (ISO format)
    }
    """
    service = ManufacturingService(db)
    try:
        result = service.post_to_accounting(order_id, user_id)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Error posting production order to accounting: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/production-orders/{order_id}/accounting-details")
def get_production_order_accounting_details(
    order_id: str,
    db: Session = Depends(get_db)
):
    """
    Get accounting details for a production order.

    Returns:
    {
        "production_order_id": str,
        "order_number": str,
        "product_name": str,
        "quantity": float,
        "cost_center_id": str,
        "cost_center_name": str,
        "project_id": str,
        "project_name": str,
        "department_id": str,
        "department_name": str,
        "wip_account_id": str,
        "wip_account_code": str,
        "labor_account_id": str,
        "labor_account_code": str,
        "posting_status": str,
        "last_posted_date": str,
        "posted_by": str,
        "material_cost": float,
        "labor_cost": float,
        "overhead_cost": float,
        "total_cost": float,
        "journal_entries": [
            {
                "id": str,
                "account_code": str,
                "debit": float,
                "credit": float,
                "reference": str
            }
        ]
    }
    """
    from app.models.production_order import ProductionOrder
    from app.models.accounting import JournalEntry

    try:
        po = db.query(ProductionOrder).filter(ProductionOrder.id == order_id).first()
        if not po:
            raise HTTPException(status_code=404, detail="Production order not found")

        # Get costs
        mfg_costs = db.query(ManufacturingCost).filter(
            ManufacturingCost.production_order_id == order_id
        ).all()

        total_material = sum(float(c.material_cost or 0) for c in mfg_costs)
        total_labor = sum(float(c.labor_cost or 0) for c in mfg_costs)
        total_overhead = sum(float(c.overhead_cost or 0) for c in mfg_costs)
        total_cost = total_material + total_labor + total_overhead

        # Get journal entries
        journal_entries = db.query(JournalEntry).filter(
            JournalEntry.reference.like(f"MFG-{order_id}%")
        ).all()

        je_data = [
            {
                "id": str(je.id),
                "account_code": je.accounting_code.code if je.accounting_code else None,
                "debit": float(je.debit_amount or 0),
                "credit": float(je.credit_amount or 0),
                "reference": je.reference
            }
            for je in journal_entries
        ]

        return {
            "production_order_id": str(po.id),
            "order_number": po.order_number,
            "product_name": po.product.name if po.product else None,
            "quantity": float(po.quantity_planned or 0),
            "cost_center_id": str(po.cost_center_id) if po.cost_center_id else None,
            "cost_center_name": po.cost_center.value if po.cost_center else None,
            "project_id": str(po.project_id) if po.project_id else None,
            "project_name": po.project.value if po.project else None,
            "department_id": str(po.department_id) if po.department_id else None,
            "department_name": po.department.value if po.department else None,
            "wip_account_id": str(po.wip_account_id) if po.wip_account_id else None,
            "wip_account_code": po.wip_account.code if po.wip_account else None,
            "labor_account_id": str(po.labor_account_id) if po.labor_account_id else None,
            "labor_account_code": po.labor_account.code if po.labor_account else None,
            "posting_status": po.posting_status,
            "last_posted_date": po.last_posted_date.isoformat() if po.last_posted_date else None,
            "posted_by": po.posted_by,
            "material_cost": total_material,
            "labor_cost": total_labor,
            "overhead_cost": total_overhead,
            "total_cost": total_cost,
            "journal_entries": je_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error getting accounting details: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dimensional-analysis")
def get_dimensional_analysis(
    type: str = Query("cost_center", description="cost_center, project, department, location"),
    period: str = Query("current_month", description="current_month, last_month, current_quarter, current_year"),
    group_by: str = Query("product", description="product, order, bom"),
    db: Session = Depends(get_db)
):
    """
    Get dimensional analysis of manufacturing costs.

    Returns:
    {
        "dimension_type": str,
        "period": str,
        "group_by": str,
        "summary": {
            "total_orders": int,
            "total_quantity": float,
            "total_cost": float,
            "unique_dimensions": int
        },
        "details": [
            {
                "dimension": str,
                "dimension_name": str,
                "product": str,
                "order_number": str,
                "quantity": float,
                "material_cost": float,
                "labor_cost": float,
                "overhead_cost": float,
                "total_cost": float
            }
        ]
    }
    """
    from app.models.production_order import ProductionOrder
    from datetime import timedelta

    try:
        # Calculate date range
        today = date.today()
        if period == "current_month":
            start = date(today.year, today.month, 1)
            if today.month == 12:
                end = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(today.year, today.month + 1, 1) - timedelta(days=1)
        elif period == "last_month":
            first = date(today.year, today.month, 1)
            end = first - timedelta(days=1)
            start = date(end.year, end.month, 1)
        elif period == "current_quarter":
            quarter_start_month = ((today.month - 1) // 3) * 3 + 1
            start = date(today.year, quarter_start_month, 1)
            quarter_end_month = quarter_start_month + 2
            if quarter_end_month == 12:
                end = date(today.year, 12, 31)
            else:
                end = date(today.year, quarter_end_month + 1, 1) - timedelta(days=1)
        elif period == "current_year":
            start = date(today.year, 1, 1)
            end = date(today.year, 12, 31)
        else:
            start = date(today.year, today.month, 1)
            end = today

        # Get manufacturing costs in period
        query = db.query(ManufacturingCost).filter(
            ManufacturingCost.date >= start,
            ManufacturingCost.date <= end
        )

        costs = query.all()

        # Aggregate by dimension
        details = []
        dim_set = set()
        total_orders = 0
        total_quantity = 0
        total_cost = 0

        for cost in costs:
            po = db.query(ProductionOrder).filter(ProductionOrder.id == cost.production_order_id).first()
            if not po:
                continue

            # Determine dimension value
            dim_id = None
            dim_name = None
            if type == "cost_center" and po.cost_center:
                dim_id = str(po.cost_center_id)
                dim_name = po.cost_center.value
            elif type == "project" and po.project:
                dim_id = str(po.project_id)
                dim_name = po.project.value
            elif type == "department" and po.department:
                dim_id = str(po.department_id)
                dim_name = po.department.value

            if not dim_id:
                continue

            dim_set.add(dim_id)
            total_orders += 1
            total_quantity += float(po.quantity_planned or 0)
            total_cost += float(cost.total_cost or 0)

            details.append({
                "dimension": dim_id,
                "dimension_name": dim_name,
                "product": po.product.name if po.product else None,
                "order_number": po.order_number,
                "quantity": float(po.quantity_planned or 0),
                "material_cost": float(cost.material_cost or 0),
                "labor_cost": float(cost.labor_cost or 0),
                "overhead_cost": float(cost.overhead_cost or 0),
                "total_cost": float(cost.total_cost or 0)
            })

        return {
            "dimension_type": type,
            "period": period,
            "group_by": group_by,
            "summary": {
                "total_orders": total_orders,
                "total_quantity": total_quantity,
                "total_cost": total_cost,
                "unique_dimensions": len(dim_set)
            },
            "details": details
        }
    except Exception as e:
        logging.error(f"Error getting dimensional analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounting-bridge")
def get_accounting_bridge(
    cost_center: Optional[str] = Query(None),
    period: Optional[str] = Query(None, description="YYYY-MM format"),
    db: Session = Depends(get_db)
):
    """
    Get accounting bridge data mapping manufacturing costs to GL accounts.

    Returns:
    {
        "cost_center": str,
        "period": str,
        "bridge_data": [
            {
                "cost_element": str,
                "account_code": str,
                "account_name": str,
                "quantity": float,
                "material_cost": float,
                "labor_cost": float,
                "overhead_cost": float,
                "total_cost": float,
                "posting_status": str
            }
        ],
        "summary": {
            "total_material": float,
            "total_labor": float,
            "total_overhead": float,
            "total_amount": float
        }
    }
    """
    from app.models.production_order import ProductionOrder

    try:
        # Parse period
        if period:
            year, month = map(int, period.split('-'))
            start = date(year, month, 1)
            if month == 12:
                end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(year, month + 1, 1) - timedelta(days=1)
        else:
            today = date.today()
            start = date(today.year, today.month, 1)
            end = today

        # Get orders for cost center and period
        query = db.query(ProductionOrder, ManufacturingCost).join(
            ManufacturingCost,
            ManufacturingCost.production_order_id == ProductionOrder.id
        ).filter(
            ManufacturingCost.date >= start,
            ManufacturingCost.date <= end
        )

        if cost_center:
            query = query.filter(ProductionOrder.cost_center_id == cost_center)

        records = query.all()

        bridge_data = []
        total_material = 0
        total_labor = 0
        total_overhead = 0

        for po, cost in records:
            total_material += float(cost.material_cost or 0)
            total_labor += float(cost.labor_cost or 0)
            total_overhead += float(cost.overhead_cost or 0)

            # Material cost allocation
            bridge_data.append({
                "cost_element": "Material",
                "account_code": po.wip_account.code if po.wip_account else "N/A",
                "account_name": po.wip_account.name if po.wip_account else "N/A",
                "quantity": float(po.quantity_planned or 0),
                "material_cost": float(cost.material_cost or 0),
                "labor_cost": 0,
                "overhead_cost": 0,
                "total_cost": float(cost.material_cost or 0),
                "posting_status": po.posting_status
            })

            # Labor cost allocation
            bridge_data.append({
                "cost_element": "Labor",
                "account_code": po.labor_account.code if po.labor_account else "N/A",
                "account_name": po.labor_account.name if po.labor_account else "N/A",
                "quantity": float(po.quantity_planned or 0),
                "material_cost": 0,
                "labor_cost": float(cost.labor_cost or 0),
                "overhead_cost": 0,
                "total_cost": float(cost.labor_cost or 0),
                "posting_status": po.posting_status
            })

            # Overhead allocation
            bridge_data.append({
                "cost_element": "Overhead",
                "account_code": po.wip_account.code if po.wip_account else "N/A",
                "account_name": po.wip_account.name if po.wip_account else "N/A",
                "quantity": float(po.quantity_planned or 0),
                "material_cost": 0,
                "labor_cost": 0,
                "overhead_cost": float(cost.overhead_cost or 0),
                "total_cost": float(cost.overhead_cost or 0),
                "posting_status": po.posting_status
            })

        return {
            "cost_center": cost_center or "ALL",
            "period": period or f"{date.today().year}-{date.today().month:02d}",
            "bridge_data": bridge_data,
            "summary": {
                "total_material": total_material,
                "total_labor": total_labor,
                "total_overhead": total_overhead,
                "total_amount": total_material + total_labor + total_overhead
            }
        }
    except Exception as e:
        logging.error(f"Error getting accounting bridge: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/journal-entries")
def get_manufacturing_journal_entries(
    period: Optional[str] = Query(None, description="YYYY-MM format"),
    status: Optional[str] = Query(None, description="posted, reconciled, variance"),
    cost_center: Optional[str] = Query(None),
    skip: int = Query(0),
    limit: int = Query(100),
    db: Session = Depends(get_db)
):
    """
    Get all manufacturing-related journal entries with optional filtering.

    Returns:
    {
        "total_count": int,
        "entries": [
            {
                "id": str,
                "date": str,
                "reference": str,
                "account_code": str,
                "account_name": str,
                "debit": float,
                "credit": float,
                "source": str,
                "status": str,
                "dimensions": [
                    {"type": str, "value": str}
                ]
            }
        ]
    }
    """
    from app.models.accounting import JournalEntry
    from sqlalchemy.orm import joinedload

    try:
        query = db.query(JournalEntry).options(
            joinedload(JournalEntry.accounting_code),
            joinedload(JournalEntry.dimension_assignments)
        ).filter(JournalEntry.source == 'MANUFACTURING')

        # Filter by period
        if period:
            year, month = map(int, period.split('-'))
            start = date(year, month, 1)
            if month == 12:
                end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(year, month + 1, 1) - timedelta(days=1)
            query = query.filter(JournalEntry.entry_date >= start, JournalEntry.entry_date <= end)

        # Filter by status
        if status:
            query = query.filter(JournalEntry.status == status)

        # Filter by cost center (via dimension assignment)
        if cost_center:
            from app.models.accounting_dimensions import AccountingDimensionAssignment
            query = query.join(AccountingDimensionAssignment).filter(
                AccountingDimensionAssignment.dimension_value_id == cost_center
            )

        total = query.count()
        entries = query.offset(skip).limit(limit).all()

        entries_data = []
        for je in entries:
            dims = []
            if je.dimension_assignments:
                for da in je.dimension_assignments:
                    if da.dimension_value:
                        dims.append({
                            "type": da.dimension_value.dimension.code if da.dimension_value.dimension else "UNKNOWN",
                            "value": da.dimension_value.value
                        })

            entries_data.append({
                "id": str(je.id),
                "date": je.entry_date.isoformat() if je.entry_date else None,
                "reference": je.reference,
                "account_code": je.accounting_code.code if je.accounting_code else None,
                "account_name": je.accounting_code.name if je.accounting_code else None,
                "debit": float(je.debit_amount or 0),
                "credit": float(je.credit_amount or 0),
                "source": je.source,
                "status": je.status if hasattr(je, 'status') else "posted",
                "dimensions": dims
            })

        return {
            "total_count": total,
            "entries": entries_data
        }
    except Exception as e:
        logging.error(f"Error getting journal entries: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reconcile")
def run_reconciliation(
    period: str = Query(..., description="YYYY-MM format, e.g., 2025-10"),
    db: Session = Depends(get_db)
):
    """
    Run reconciliation of manufacturing costs vs GL balances by dimension.

    Returns:
    {
        "period": str,
        "reconciliation_date": str,
        "totals": {
            "mfg_total": float,
            "gl_total": float,
            "variance": float,
            "variance_percent": float
        },
        "reconciled_dimensions": [
            {
                "dimension_id": str,
                "mfg_amount": float,
                "gl_amount": float,
                "variance": float
            }
        ],
        "variance_dimensions": [
            {
                "dimension_id": str,
                "mfg_amount": float,
                "gl_amount": float,
                "variance": float,
                "variance_percent": float
            }
        ],
        "reconciliation_status": "RECONCILED" | "VARIANCE_DETECTED"
    }
    """
    service = ManufacturingService(db)
    try:
        result = service.reconcile_manufacturing_costs(period)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Error running reconciliation: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
