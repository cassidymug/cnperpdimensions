from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.landed_cost import LandedCostCreate, LandedCostResponse
from app.services.landed_cost_service import LandedCostService

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()

@router.post("/", response_model=LandedCostResponse)
def create_landed_cost(
    landed_cost: LandedCostCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new Landed Cost document.
    """
    service = LandedCostService(db)
    try:
        return service.create_landed_cost(landed_cost)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{landed_cost_id}/allocate", status_code=200)
def allocate_landed_cost(
    landed_cost_id: str,
    db: Session = Depends(get_db)
):
    """
    Allocate landed costs to the associated purchase items.
    """
    service = LandedCostService(db)
    try:
        service.allocate_landed_cost(landed_cost_id)
        return {"message": "Landed costs allocated successfully."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
