from pydantic import BaseModel, Field, ConfigDict
from datetime import date as dt_date
from typing import Optional, List

# Schema for a single item within a landed cost document
class LandedCostItemBase(BaseModel):
    description: str
    amount: float = Field(..., gt=0)
    allocation_method: str = "quantity"

class LandedCostItemCreate(LandedCostItemBase):
    pass

class LandedCostItemResponse(LandedCostItemBase):
    id: str

    model_config = ConfigDict(from_attributes=True)

# Main schema for the landed cost document
class LandedCostBase(BaseModel):
    purchase_id: Optional[str] = None
    reference: str
    supplier_id: Optional[str] = None
    date: dt_date
    notes: Optional[str] = None

class LandedCostCreate(LandedCostBase):
    items: List[LandedCostItemCreate]

class LandedCostUpdate(BaseModel):
    reference: Optional[str] = None
    date: Optional[dt_date] = None
    notes: Optional[str] = None
    items: Optional[List[LandedCostItemCreate]] = None

class LandedCostResponse(LandedCostBase):
    id: str
    total_amount: float
    status: str
    items: List[LandedCostItemResponse]

    model_config = ConfigDict(from_attributes=True)
