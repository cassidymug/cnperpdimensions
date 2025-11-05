from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.vat import VatReconciliation
from app.schemas.vat import VATReconciliationCreate, VATReconciliation as VATReconciliationSchema
from typing import List

router = APIRouter()

@router.get("/summary", summary="Get VAT Summary")
async def get_vat_summary(db: Session = Depends(get_db)):
    # This is a placeholder. In a real application, you would calculate this from transactions.
    vat_collected = 12500.75
    vat_paid = 8750.25
    net_vat_liability = vat_collected - vat_paid
    return {
        "data": {
            "vat_collected": vat_collected,
            "vat_paid": vat_paid,
            "net_vat_liability": net_vat_liability,
            "vat_rate": 14.0
        }
    }

@router.get("/reconciliations", response_model=List[VATReconciliationSchema], summary="Get all VAT Reconciliations")
async def get_reconciliations(db: Session = Depends(get_db)):
    reconciliations = db.query(VATReconciliation).all()
    return reconciliations

@router.post("/reconciliations", response_model=VATReconciliationSchema, summary="Create a new VAT Reconciliation")
async def create_reconciliation(reconciliation: VATReconciliationCreate, db: Session = Depends(get_db)):
    db_reconciliation = VATReconciliation(**reconciliation.model_dump())
    db.add(db_reconciliation)
    db.commit()
    db.refresh(db_reconciliation)
    return db_reconciliation

@router.get("/reconciliations/{reconciliation_id}", response_model=VATReconciliationSchema, summary="Get a specific VAT Reconciliation")
async def get_reconciliation(reconciliation_id: int, db: Session = Depends(get_db)):
    db_reconciliation = db.query(VATReconciliation).filter(VATReconciliation.id == reconciliation_id).first()
    if db_reconciliation is None:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    return db_reconciliation

@router.put("/reconciliations/{reconciliation_id}", response_model=VATReconciliationSchema, summary="Update a VAT Reconciliation")
async def update_reconciliation(reconciliation_id: int, reconciliation: VATReconciliationCreate, db: Session = Depends(get_db)):
    db_reconciliation = db.query(VATReconciliation).filter(VATReconciliation.id == reconciliation_id).first()
    if db_reconciliation is None:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    
    for key, value in reconciliation.model_dump().items():
        setattr(db_reconciliation, key, value)
        
    db.commit()
    db.refresh(db_reconciliation)
    return db_reconciliation

@router.delete("/reconciliations/{reconciliation_id}", summary="Delete a VAT Reconciliation")
async def delete_reconciliation(reconciliation_id: int, db: Session = Depends(get_db)):
    db_reconciliation = db.query(VATReconciliation).filter(VATReconciliation.id == reconciliation_id).first()
    if db_reconciliation is None:
        raise HTTPException(status_code=404, detail="Reconciliation not found")
    
    db.delete(db_reconciliation)
    db.commit()
    return {"message": "Reconciliation deleted successfully"}
