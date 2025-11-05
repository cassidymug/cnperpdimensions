"""
Business Intelligence endpoints for analytics and reporting
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case, and_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.inventory import Product, UnitOfMeasure, ProductAssembly
from app.models.sales import Sale, SaleItem
from app.models.purchases import PurchaseOrder, PurchaseOrderItem
from app.models.job_card import JobCard

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()

@router.get("/dashboard/overview")
async def get_dashboard_overview(db: Session = Depends(get_db)):
    """Get high-level KPIs for BI dashboard"""
    try:
        # Total products
        total_products = db.query(func.count(Product.id)).scalar() or 0
        
        # Products by UOM category
        products_by_category = db.query(
            UnitOfMeasure.category,
            func.count(Product.id).label('count')
        ).join(
            Product, Product.unit_of_measure_id == UnitOfMeasure.id
        ).group_by(
            UnitOfMeasure.category
        ).all()
        
        category_stats = {cat: count for cat, count in products_by_category}
        
        # Total active UOMs
        total_uoms = db.query(func.count(UnitOfMeasure.id)).filter(
            UnitOfMeasure.is_active == True
        ).scalar() or 0
        
        # UOM usage (products per unit)
        uom_usage = db.query(
            UnitOfMeasure.id,
            UnitOfMeasure.name,
            UnitOfMeasure.abbreviation,
            UnitOfMeasure.category,
            func.count(Product.id).label('product_count')
        ).outerjoin(
            Product, Product.unit_of_measure_id == UnitOfMeasure.id
        ).filter(
            UnitOfMeasure.is_active == True
        ).group_by(
            UnitOfMeasure.id,
            UnitOfMeasure.name,
            UnitOfMeasure.abbreviation,
            UnitOfMeasure.category
        ).order_by(
            desc('product_count')
        ).limit(10).all()
        
        top_uoms = [
            {
                "unit_name": f"{row.name} ({row.abbreviation})",
                "category": row.category,
                "product_count": row.product_count
            }
            for row in uom_usage
        ]
        
        return {
            "success": True,
            "data": {
                "total_products": total_products,
                "total_active_uoms": total_uoms,
                "products_by_category": category_stats,
                "top_used_uoms": top_uoms
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/uom/category-distribution")
async def get_uom_category_distribution(db: Session = Depends(get_db)):
    """Get distribution of UOMs across categories"""
    try:
        distribution = db.query(
            UnitOfMeasure.category,
            UnitOfMeasure.subcategory,
            func.count(UnitOfMeasure.id).label('unit_count'),
            func.count(Product.id).label('product_count')
        ).outerjoin(
            Product, Product.unit_of_measure_id == UnitOfMeasure.id
        ).filter(
            UnitOfMeasure.is_active == True
        ).group_by(
            UnitOfMeasure.category,
            UnitOfMeasure.subcategory
        ).order_by(
            UnitOfMeasure.category,
            UnitOfMeasure.subcategory
        ).all()
        
        result = [
            {
                "category": row.category,
                "subcategory": row.subcategory,
                "unit_count": row.unit_count,
                "product_count": row.product_count,
                "utilization_rate": round((row.product_count / row.unit_count * 100), 2) if row.unit_count > 0 else 0
            }
            for row in distribution
        ]
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/uom-analysis")
async def get_product_uom_analysis(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Detailed analysis of products by UOM"""
    try:
        query = db.query(
            Product.id,
            Product.name,
            Product.sku,
            Product.selling_price,
            UnitOfMeasure.name.label('unit_name'),
            UnitOfMeasure.abbreviation.label('unit_abbr'),
            UnitOfMeasure.category,
            UnitOfMeasure.subcategory,
            UnitOfMeasure.decimal_places
        ).join(
            UnitOfMeasure, Product.unit_of_measure_id == UnitOfMeasure.id
        )
        
        if category:
            query = query.filter(UnitOfMeasure.category == category)
        
        products = query.order_by(UnitOfMeasure.category, Product.name).all()
        
        result = [
            {
                "product_id": p.id,
                "product_name": p.name,
                "sku": p.sku,
                "selling_price": float(p.selling_price) if p.selling_price else 0,
                "unit": f"{p.unit_name} ({p.unit_abbr})",
                "category": p.category,
                "subcategory": p.subcategory,
                "decimal_places": p.decimal_places
            }
            for p in products
        ]
        
        return {"success": True, "data": result, "total": len(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/uom/precision-analysis")
async def get_precision_analysis(db: Session = Depends(get_db)):
    """Analyze precision requirements across products"""
    try:
        precision_stats = db.query(
            UnitOfMeasure.category,
            UnitOfMeasure.decimal_places,
            func.count(Product.id).label('product_count')
        ).join(
            Product, Product.unit_of_measure_id == UnitOfMeasure.id
        ).filter(
            UnitOfMeasure.is_active == True
        ).group_by(
            UnitOfMeasure.category,
            UnitOfMeasure.decimal_places
        ).order_by(
            UnitOfMeasure.category,
            UnitOfMeasure.decimal_places
        ).all()
        
        result = [
            {
                "category": row.category,
                "decimal_places": row.decimal_places,
                "product_count": row.product_count
            }
            for row in precision_stats
        ]
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/inventory/category-value")
async def get_inventory_value_by_category(db: Session = Depends(get_db)):
    """Get inventory value grouped by UOM category"""
    try:
        category_values = db.query(
            UnitOfMeasure.category,
            func.count(Product.id).label('product_count'),
            func.sum(Product.quantity_on_hand * Product.price).label('total_value'),
            func.avg(Product.price).label('avg_price')
        ).join(
            Product, Product.unit_of_measure_id == UnitOfMeasure.id
        ).filter(
            UnitOfMeasure.is_active == True,
            Product.quantity_on_hand.isnot(None)
        ).group_by(
            UnitOfMeasure.category
        ).order_by(
            desc('total_value')
        ).all()
        
        result = [
            {
                "category": row.category,
                "product_count": row.product_count,
                "total_value": float(row.total_value or 0),
                "average_price": float(row.avg_price or 0)
            }
            for row in category_values
        ]
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/uom/system-vs-custom")
async def get_system_vs_custom_analysis(db: Session = Depends(get_db)):
    """Compare system units vs custom units usage"""
    try:
        analysis = db.query(
            UnitOfMeasure.is_system_unit,
            UnitOfMeasure.category,
            func.count(func.distinct(UnitOfMeasure.id)).label('unit_count'),
            func.count(Product.id).label('product_count')
        ).outerjoin(
            Product, Product.unit_of_measure_id == UnitOfMeasure.id
        ).filter(
            UnitOfMeasure.is_active == True
        ).group_by(
            UnitOfMeasure.is_system_unit,
            UnitOfMeasure.category
        ).order_by(
            UnitOfMeasure.is_system_unit.desc(),
            UnitOfMeasure.category
        ).all()
        
        result = [
            {
                "unit_type": "System" if row.is_system_unit else "Custom",
                "category": row.category,
                "unit_count": row.unit_count,
                "product_count": row.product_count
            }
            for row in analysis
        ]
        
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/product-creation")
async def get_product_creation_trends(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Analyze product creation trends by UOM category"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        trends = db.query(
            func.date(Product.created_at).label('date'),
            UnitOfMeasure.category,
            func.count(Product.id).label('count')
        ).join(
            UnitOfMeasure, Product.unit_of_measure_id == UnitOfMeasure.id
        ).filter(
            Product.created_at >= start_date
        ).group_by(
            func.date(Product.created_at),
            UnitOfMeasure.category
        ).order_by(
            'date',
            UnitOfMeasure.category
        ).all()
        
        result = [
            {
                "date": row.date.isoformat() if row.date else None,
                "category": row.category,
                "product_count": row.count
            }
            for row in trends
        ]
        
        return {"success": True, "data": result, "period_days": days}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
