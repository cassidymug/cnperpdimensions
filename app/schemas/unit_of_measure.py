"""
Schemas for Unit of Measure Management
Comprehensive UOM system for products and business intelligence
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class UOMCategory:
    """Standard UOM Categories"""
    QUANTITY = "quantity"  # Basic counting units
    LENGTH = "length"
    AREA = "area"
    VOLUME = "volume"
    WEIGHT = "weight"
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    SPEED = "speed"
    TIME = "time"
    ANGLE = "angle"
    ENERGY = "energy"
    POWER = "power"
    FORCE = "force"
    FREQUENCY = "frequency"
    ELECTRIC_CURRENT = "electric_current"
    VOLTAGE = "voltage"
    RESISTANCE = "resistance"
    LUMINOSITY = "luminosity"
    SUBSTANCE = "substance"  # Moles
    NAUTICAL = "nautical"
    DATA = "data"  # Bytes, bits


class UOMSubcategory:
    """Unit system subcategories"""
    METRIC = "metric"
    IMPERIAL = "imperial"
    US_CUSTOMARY = "us_customary"
    NAUTICAL = "nautical"
    SCIENTIFIC = "scientific"
    CUSTOM = "custom"


class UnitOfMeasureBase(BaseModel):
    """Base schema for UOM"""
    name: str = Field(..., description="Full name of the unit")
    abbreviation: str = Field(..., description="Short abbreviation")
    symbol: Optional[str] = Field(None, description="Display symbol")
    category: str = Field(..., description="Unit category")
    subcategory: Optional[str] = Field(None, description="Unit subcategory")
    description: Optional[str] = None
    
    is_base_unit: bool = Field(default=False, description="Is this the base unit for conversions")
    base_unit_id: Optional[str] = Field(None, description="Reference to base unit if not base")
    conversion_factor: float = Field(default=1.0, description="Factor to convert to base unit")
    conversion_offset: float = Field(default=0.0, description="Offset for conversion (temperature)")
    
    is_system_unit: bool = Field(default=True, description="System vs custom unit")
    is_active: bool = Field(default=True, description="Active status")
    display_order: int = Field(default=0, description="Sort order for UI")
    decimal_places: int = Field(default=2, description="Suggested decimal precision")
    usage_hint: Optional[str] = Field(None, description="Usage guidance")
    branch_id: Optional[str] = None


class UnitOfMeasureCreate(UnitOfMeasureBase):
    """Schema for creating a unit of measure"""
    pass


class UnitOfMeasureUpdate(BaseModel):
    """Schema for updating a unit of measure"""
    name: Optional[str] = None
    abbreviation: Optional[str] = None
    symbol: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None
    decimal_places: Optional[int] = None
    usage_hint: Optional[str] = None


class UnitOfMeasureResponse(UnitOfMeasureBase):
    """Schema for UOM response"""
    id: str
    created_at: datetime
    updated_at: datetime
    base_unit_name: Optional[str] = None
    base_unit_abbreviation: Optional[str] = None

    class Config:
        from_attributes = True


class UnitConversionRequest(BaseModel):
    """Schema for unit conversion request"""
    value: float = Field(..., description="Value to convert")
    from_unit_id: str = Field(..., description="Source unit ID")
    to_unit_id: str = Field(..., description="Target unit ID")


class UnitConversionResponse(BaseModel):
    """Schema for unit conversion response"""
    original_value: float
    converted_value: float
    from_unit: str
    to_unit: str
    formula: str


class UOMCategoryInfo(BaseModel):
    """Information about a UOM category"""
    category: str
    display_name: str
    description: str
    base_unit: Optional[str] = None
    unit_count: int = 0


class UOMListResponse(BaseModel):
    """Response for listing units"""
    success: bool = True
    units: List[UnitOfMeasureResponse]
    total: int
    categories: Optional[List[UOMCategoryInfo]] = None
