from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal


class COGSEntryBase(BaseModel):
    """Base schema for COGS entries"""
    product_id: str
    quantity: float
    unit_cost: float
    total_cost: Optional[float] = None
    description: Optional[str] = None
    reference: Optional[str] = None


class COGSEntryCreate(COGSEntryBase):
    """Schema for creating COGS entries"""
    date: Optional[datetime] = None


class COGSEntryUpdate(BaseModel):
    """Schema for updating COGS entries"""
    product_id: Optional[str] = None
    quantity: Optional[float] = None
    unit_cost: Optional[float] = None
    total_cost: Optional[float] = None
    description: Optional[str] = None
    reference: Optional[str] = None
    is_adjusted: Optional[bool] = None


class COGSEntryResponse(COGSEntryBase):
    """Schema for COGS entry responses"""
    id: int
    date: datetime
    is_adjusted: bool
    product_name: Optional[str] = None
    product_sku: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Manufacturing Cost Schemas
class MaterialCostEntryBase(BaseModel):
    """Base schema for material cost entries"""
    material_id: str
    quantity: float
    unit_cost: float
    total_cost: Optional[float] = None
    description: Optional[str] = None


class MaterialCostEntryCreate(MaterialCostEntryBase):
    """Schema for creating material cost entries"""
    pass


class MaterialCostEntryResponse(MaterialCostEntryBase):
    """Schema for material cost entry responses"""
    id: int
    material_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LaborCostEntryBase(BaseModel):
    """Base schema for labor cost entries"""
    hours: float
    rate: float
    total_cost: Optional[float] = None
    description: Optional[str] = None


class LaborCostEntryCreate(LaborCostEntryBase):
    """Schema for creating labor cost entries"""
    pass


class LaborCostEntryResponse(LaborCostEntryBase):
    """Schema for labor cost entry responses"""
    id: int

    model_config = ConfigDict(from_attributes=True)


class OverheadCostEntryBase(BaseModel):
    """Base schema for overhead cost entries"""
    name: str
    amount: float
    description: Optional[str] = None


class OverheadCostEntryCreate(OverheadCostEntryBase):
    """Schema for creating overhead cost entries"""
    pass


class OverheadCostEntryResponse(OverheadCostEntryBase):
    """Schema for overhead cost entry responses"""
    id: int

    model_config = ConfigDict(from_attributes=True)


class ManufacturingCostBase(BaseModel):
    """Base schema for manufacturing costs"""
    product_id: str
    batch_number: str
    batch_size: float
    notes: Optional[str] = None


class ManufacturingCostCreate(ManufacturingCostBase):
    """Schema for creating manufacturing costs"""
    date: Optional[datetime] = None
    material_entries: Optional[List[MaterialCostEntryCreate]] = []
    labor_entries: Optional[List[LaborCostEntryCreate]] = []
    overhead_entries: Optional[List[OverheadCostEntryCreate]] = []


class ManufacturingCostUpdate(BaseModel):
    """Schema for updating manufacturing costs"""
    product_id: Optional[str] = None
    batch_number: Optional[str] = None
    batch_size: Optional[float] = None
    material_cost: Optional[float] = None
    labor_cost: Optional[float] = None
    overhead_cost: Optional[float] = None
    total_cost: Optional[float] = None
    unit_cost: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class ManufacturingCostResponse(ManufacturingCostBase):
    """Schema for manufacturing cost responses"""
    id: int
    date: datetime
    material_cost: float
    labor_cost: float
    overhead_cost: float
    total_cost: float
    unit_cost: float
    status: str
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    material_entries: List[MaterialCostEntryResponse] = []
    labor_entries: List[LaborCostEntryResponse] = []
    overhead_entries: List[OverheadCostEntryResponse] = []

    model_config = ConfigDict(from_attributes=True)