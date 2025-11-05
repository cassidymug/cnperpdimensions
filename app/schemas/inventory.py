from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from decimal import Decimal
from datetime import date, datetime


class ProductResponse(BaseModel):
    """Product response schema"""
    id: str
    name: str
    sku: Optional[str] = None
    description: Optional[str] = None
    quantity: int
    barcode: Optional[str] = None
    cost_price: Decimal
    selling_price: Decimal
    is_serialized: bool
    is_perishable: Optional[bool] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    weight: Optional[Decimal] = None
    dimensions: Optional[str] = None
    minimum_stock_level: int = 0
    maximum_stock_level: Optional[int] = None
    reorder_point: int = 0
    active: bool = True
    notes: Optional[str] = None
    expiry_date: Optional[date] = None
    batch_number: Optional[str] = None
    warranty_period_months: Optional[int] = None
    warranty_period_years: Optional[int] = None
    branch_id: Optional[str] = None
    supplier_id: Optional[str] = None
    accounting_code_id: Optional[str] = None
    unit_of_measure_id: Optional[str] = None
    image_url: Optional[str] = None
    is_taxable: bool = True
    # Additional fields from Product model
    product_type: Optional[str] = None
    is_recurring_income: bool = False
    recurring_income_type: Optional[str] = None
    recurring_amount: Optional[Decimal] = None
    recurring_interval: Optional[str] = None
    recurring_start_date: Optional[date] = None
    recurring_end_date: Optional[date] = None
    recurring_description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    """Product creation schema"""
    name: str
    sku: str
    description: Optional[str] = None
    quantity: int = 0
    barcode: Optional[str] = None
    cost_price: Decimal = Decimal('0.00')
    selling_price: Decimal = Decimal('0.00')
    is_serialized: bool = False
    is_perishable: Optional[bool] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    weight: Optional[Decimal] = None
    dimensions: Optional[str] = None
    minimum_stock_level: int = 0
    maximum_stock_level: Optional[int] = None
    reorder_point: int = 0
    active: bool = True
    notes: Optional[str] = None
    expiry_date: Optional[date] = None
    batch_number: Optional[str] = None
    warranty_period_months: Optional[int] = None
    warranty_period_years: Optional[int] = None
    branch_id: Optional[str] = None
    supplier_id: Optional[str] = None
    accounting_code_id: Optional[str] = None
    unit_of_measure_id: Optional[str] = None
    image_url: Optional[str] = None
    is_taxable: bool = True


class ProductUpdate(BaseModel):
    """Product update schema"""
    name: Optional[str] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[int] = None
    barcode: Optional[str] = None
    cost_price: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    is_serialized: Optional[bool] = None
    is_perishable: Optional[bool] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    weight: Optional[Decimal] = None
    dimensions: Optional[str] = None
    minimum_stock_level: Optional[int] = None
    maximum_stock_level: Optional[int] = None
    reorder_point: Optional[int] = None
    active: Optional[bool] = None
    notes: Optional[str] = None
    expiry_date: Optional[date] = None
    batch_number: Optional[str] = None
    warranty_period_months: Optional[int] = None
    warranty_period_years: Optional[int] = None
    branch_id: Optional[str] = None
    supplier_id: Optional[str] = None
    accounting_code_id: Optional[str] = None
    unit_of_measure_id: Optional[str] = None
    image_url: Optional[str] = None
    is_taxable: Optional[bool] = None


class InventoryAdjustmentCreate(BaseModel):
    """Schema for creating inventory adjustments"""
    product_id: str
    quantity_change: int = Field(..., description="Positive for increase, negative for decrease")
    adjustment_type: str = Field(..., description="gain, loss, correction, damage, theft, opening_stock")
    reason: str = Field(..., description="Reason for adjustment")
    notes: Optional[str] = None
    branch_id: Optional[str] = None
    adjustment_date: Optional[date] = None


class InventoryAdjustmentResponse(BaseModel):
    """Schema for inventory adjustment responses"""
    id: str
    product_id: str
    adjustment_date: date
    quantity: int
    reason: str
    adjustment_type: str
    previous_quantity: int
    new_quantity: int
    unit_cost: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    accounting_entry_id: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
