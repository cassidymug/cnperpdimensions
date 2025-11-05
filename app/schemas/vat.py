from pydantic import BaseModel, ConfigDict
from datetime import date
from typing import Optional, List

class VATReconciliationBase(BaseModel):
    period_start: date
    period_end: date
    description: Optional[str] = None
    vat_collected: float
    vat_paid: float
    net_vat_liability: float
    status: str
    vat_rate: float

class VATReconciliationCreate(VATReconciliationBase):
    pass

class VATReconciliation(VATReconciliationBase):
    id: str

    model_config = ConfigDict(from_attributes=True)  # Updated for Pydantic v2

# For list responses, we'll just return List[VATReconciliation] directly
# instead of using a wrapper model
