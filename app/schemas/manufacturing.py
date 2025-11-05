from pydantic import BaseModel, ConfigDict
from datetime import date
from typing import Optional, List, Dict, Any

class ManufacturingCostBase(BaseModel):
    product_id: int
    date: date
    quantity: float
    batch_number: Optional[str] = None
    material_cost: Optional[float] = 0.0
    labor_cost: Optional[float] = 0.0
    overhead_cost: Optional[float] = 0.0
    notes: Optional[str] = None

class ManufacturingCostCreate(ManufacturingCostBase):
    pass

class ManufacturingCostUpdate(ManufacturingCostBase):
    pass

class ManufacturingCost(ManufacturingCostBase):
    id: int
    total_cost: float
    unit_cost: float

    model_config = ConfigDict(from_attributes=True)

class ManufacturingTotals(BaseModel):
    total_materials: float
    total_labor: float
    total_overhead: float
    total_manufacturing: float
    total_batches: int
    total_intangible: float
    total_wip: float

class ProductTypeDistribution(BaseModel):
    type: str
    count: int
    total_cost: float

class MonthlyTrend(BaseModel):
    month: str
    materials: float
    labor: float
    overhead: float
    total: float

class ManufacturingStats(BaseModel):
    totals: ManufacturingTotals
    product_type_distribution: List[ProductTypeDistribution]
    monthly_trends: List[MonthlyTrend]
