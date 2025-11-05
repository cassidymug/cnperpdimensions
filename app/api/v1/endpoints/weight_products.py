"""
API endpoints for weight-based product scanning
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import datetime

from app.core.database import get_db
from app.models.inventory import Product
from app.utils.weight_barcode import parse_weight_barcode, calculate_price, format_barcode_display

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()


class WeightBarcodeRequest(BaseModel):
    barcode: str


class WeightBarcodeResponse(BaseModel):
    success: bool
    product_id: Optional[str]
    product_name: Optional[str]
    category: Optional[str]
    weight_grams: Optional[float]
    weight_kg: Optional[float]
    price_per_kg: Optional[float]
    tare_weight: Optional[float]
    unit_price: Optional[float]  # Calculated price for this weight
    barcode_valid: bool
    error: Optional[str] = None


@router.post("/parse-weight-barcode", response_model=WeightBarcodeResponse)
async def parse_weight_barcode_endpoint(
    request: WeightBarcodeRequest,
    db: Session = Depends(get_db)
):
    """
    Parse a weight-based barcode and return product details with calculated price
    
    Barcode format: [Type:2][Product:5][Weight:5][Check:1]
    Example: 20-12345-01500-7 = Meat, Product 12345, 1.5kg
    """
    try:
        # Parse the barcode
        parsed = parse_weight_barcode(request.barcode)
        
        if not parsed:
            return WeightBarcodeResponse(
                success=False,
                barcode_valid=False,
                error="Invalid barcode format"
            )
        
        if not parsed['is_valid']:
            return WeightBarcodeResponse(
                success=False,
                barcode_valid=False,
                error="Barcode checksum invalid"
            )
        
        # Look up the product
        product = db.query(Product).filter(
            and_(
                Product.is_weight_based == True,
                Product.weight_barcode_prefix == parsed['type_code'],
                Product.weight_barcode_sku == parsed['product_code']
            )
        ).first()
        
        if not product:
            return WeightBarcodeResponse(
                success=False,
                barcode_valid=True,
                error=f"Product not found for code {parsed['type_code']}-{parsed['product_code']}"
            )
        
        # Calculate price
        unit_price = calculate_price(
            parsed['weight_grams'],
            Decimal(str(product.price_per_kg)),
            float(product.tare_weight or 0)
        )
        
        return WeightBarcodeResponse(
            success=True,
            product_id=product.id,
            product_name=product.name,
            category=parsed['category'],
            weight_grams=parsed['weight_grams'],
            weight_kg=parsed['weight_kg'],
            price_per_kg=float(product.price_per_kg),
            tare_weight=float(product.tare_weight or 0),
            unit_price=float(unit_price),
            barcode_valid=True
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/weight-products")
async def get_weight_products(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all weight-based products, optionally filtered by category
    """
    try:
        query = db.query(Product).filter(Product.is_weight_based == True)
        
        if category:
            # Map category to barcode prefix
            category_map = {
                'meat': '20',
                'fruits': '21',
                'vegetables': '22',
                'dairy': '23',
                'bakery': '24'
            }
            prefix = category_map.get(category.lower())
            if prefix:
                query = query.filter(Product.weight_barcode_prefix == prefix)
        
        products = query.all()
        
        return {
            "success": True,
            "products": [
                {
                    "id": p.id,
                    "name": p.name,
                    "sku": p.sku,
                    "category": get_category_name(p.weight_barcode_prefix),
                    "barcode_prefix": p.weight_barcode_prefix,
                    "barcode_sku": p.weight_barcode_sku,
                    "price_per_kg": float(p.price_per_kg) if p.price_per_kg else 0,
                    "tare_weight": float(p.tare_weight) if p.tare_weight else 0,
                    "min_weight": float(p.min_weight) if p.min_weight else None,
                    "max_weight": float(p.max_weight) if p.max_weight else None,
                }
                for p in products
            ],
            "total": len(products)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_category_name(prefix: str) -> str:
    """Get category name from barcode prefix"""
    categories = {
        '20': 'Meat',
        '21': 'Fruits',
        '22': 'Vegetables',
        '23': 'Dairy',
        '24': 'Bakery'
    }
    return categories.get(prefix, 'Unknown')


@router.get("/export-for-scale")
async def export_for_scale(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Export weight-based products in scale-compatible CSV format
    
    This endpoint exports products in a format that can be imported into
    label-printing scales (Bizerba, CAS, Toledo, etc.)
    
    CSV Format:
    PLU,Name,PricePerKg,Tare,Prefix,Category,MinWeight,MaxWeight
    
    Example:
    12345,Beef Mince,125.00,50,20,Meat,100,5000
    """
    try:
        query = db.query(Product).filter(Product.is_weight_based == True)
        
        if category:
            # Map category to barcode prefix
            category_map = {
                'meat': '20',
                'fruits': '21',
                'vegetables': '22',
                'dairy': '23',
                'bakery': '24'
            }
            prefix = category_map.get(category.lower())
            if prefix:
                query = query.filter(Product.weight_barcode_prefix == prefix)
        
        products = query.order_by(Product.weight_barcode_sku).all()
        
        # Generate CSV header
        csv_lines = [
            "PLU,Name,PricePerKg,Tare,Prefix,Category,MinWeight,MaxWeight"
        ]
        
        # Add product rows
        for p in products:
            plu = p.weight_barcode_sku or ''
            name = p.name.replace(',', ' ')  # Remove commas to avoid CSV issues
            price_per_kg = float(p.price_per_kg) if p.price_per_kg else 0
            tare = float(p.tare_weight) if p.tare_weight else 0
            prefix = p.weight_barcode_prefix or ''
            cat_name = get_category_name(prefix)
            min_wt = float(p.min_weight) if p.min_weight else 0
            max_wt = float(p.max_weight) if p.max_weight else 99999
            
            csv_lines.append(
                f"{plu},{name},{price_per_kg:.2f},{tare:.0f},"
                f"{prefix},{cat_name},{min_wt:.0f},{max_wt:.0f}"
            )
        
        csv_content = "\n".join(csv_lines)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scale_products_{category or 'all'}_{timestamp}.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
