from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.inventory import COGSEntry
from app.models.inventory import Product
from app.schemas.cost_accounting import COGSEntryCreate, COGSEntryResponse, COGSEntryUpdate

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()


@router.post("/", response_model=COGSEntryResponse)
def create_cogs_entry(
    cogs_entry: COGSEntryCreate,
    db: Session = Depends(get_db)
):
    """Create a new COGS entry"""
    # Verify product exists
    product = db.query(Product).filter(Product.id == cogs_entry.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Calculate total cost if not provided
    total_cost = cogs_entry.total_cost
    if total_cost is None:
        total_cost = cogs_entry.quantity * cogs_entry.unit_cost
    
    # Create COGS entry
    db_cogs_entry = COGSEntry(
        product_id=cogs_entry.product_id,
        quantity=cogs_entry.quantity,
        unit_cost=cogs_entry.unit_cost,
        total_cost=total_cost,
        description=cogs_entry.description,
        reference=cogs_entry.reference,
        date=cogs_entry.date
    )
    
    db.add(db_cogs_entry)
    db.commit()
    db.refresh(db_cogs_entry)
    
    # Add product details for response
    setattr(db_cogs_entry, "product_name", product.name)
    setattr(db_cogs_entry, "product_sku", product.sku)
    
    return db_cogs_entry


@router.get("/", response_model=List[COGSEntryResponse])
def read_cogs_entries(
    skip: int = 0,
    limit: int = 100,
    product_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all COGS entries with optional filtering"""
    query = db.query(COGSEntry)
    
    if product_id:
        query = query.filter(COGSEntry.product_id == product_id)
    
    cogs_entries = query.offset(skip).limit(limit).all()
    
    # Add product details for each entry
    for entry in cogs_entries:
        product = db.query(Product).filter(Product.id == entry.product_id).first()
        if product:
            setattr(entry, "product_name", product.name)
            setattr(entry, "product_sku", product.sku)
    
    return cogs_entries


@router.get("/{cogs_id}", response_model=COGSEntryResponse)
def read_cogs_entry(
    cogs_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific COGS entry by ID"""
    cogs_entry = db.query(COGSEntry).filter(COGSEntry.id == cogs_id).first()
    if not cogs_entry:
        raise HTTPException(status_code=404, detail="COGS entry not found")
    
    # Add product details
    product = db.query(Product).filter(Product.id == cogs_entry.product_id).first()
    if product:
        setattr(cogs_entry, "product_name", product.name)
        setattr(cogs_entry, "product_sku", product.sku)
    
    return cogs_entry


@router.put("/{cogs_id}", response_model=COGSEntryResponse)
def update_cogs_entry(
    cogs_id: int,
    cogs_entry: COGSEntryUpdate,
    db: Session = Depends(get_db)
):
    """Update a COGS entry"""
    db_cogs_entry = db.query(COGSEntry).filter(COGSEntry.id == cogs_id).first()
    if not db_cogs_entry:
        raise HTTPException(status_code=404, detail="COGS entry not found")
    
    # Update fields if provided
    update_data = cogs_entry.dict(exclude_unset=True)
    
    # If quantity or unit_cost is updated, recalculate total_cost
    if "quantity" in update_data or "unit_cost" in update_data:
        quantity = update_data.get("quantity", db_cogs_entry.quantity)
        unit_cost = update_data.get("unit_cost", db_cogs_entry.unit_cost)
        update_data["total_cost"] = quantity * unit_cost
    
    for key, value in update_data.items():
        setattr(db_cogs_entry, key, value)
    
    # Mark as adjusted
    db_cogs_entry.is_adjusted = True
    
    db.commit()
    db.refresh(db_cogs_entry)
    
    # Add product details for response
    product = db.query(Product).filter(Product.id == db_cogs_entry.product_id).first()
    if product:
        setattr(db_cogs_entry, "product_name", product.name)
        setattr(db_cogs_entry, "product_sku", product.sku)
    
    return db_cogs_entry


@router.delete("/{cogs_id}", status_code=204)
def delete_cogs_entry(
    cogs_id: int,
    db: Session = Depends(get_db)
):
    """Delete a COGS entry"""
    db_cogs_entry = db.query(COGSEntry).filter(COGSEntry.id == cogs_id).first()
    if not db_cogs_entry:
        raise HTTPException(status_code=404, detail="COGS entry not found")
    
    db.delete(db_cogs_entry)
    db.commit()
    
    return None