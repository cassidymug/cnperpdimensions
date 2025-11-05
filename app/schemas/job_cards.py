from datetime import date
from decimal import Decimal
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class JobCardMaterialInput(BaseModel):
    product_id: str
    quantity: Decimal = Field(..., gt=0)
    unit_cost: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    notes: Optional[str] = None


class JobCardLaborInput(BaseModel):
    description: str
    hours: Optional[Decimal] = Field(default=Decimal("0"), ge=0)
    rate: Optional[Decimal] = Field(default=Decimal("0"), ge=0)
    cost_rate: Optional[Decimal] = Field(default=None, ge=0)
    technician_id: Optional[str] = None
    product_id: Optional[str] = None
    notes: Optional[str] = None


class JobCardCreate(BaseModel):
    customer_id: str
    branch_id: str
    job_type: str
    start_date: date
    due_date: Optional[date] = None
    priority: Optional[str] = Field(default="normal")
    status: Optional[str] = Field(default="draft")
    description: Optional[str] = None
    notes: Optional[str] = None
    technician_id: Optional[str] = None
    vat_rate: Optional[Decimal] = None
    currency: Optional[str] = None
    materials: Optional[List[JobCardMaterialInput]] = None
    labor: Optional[List[JobCardLaborInput]] = None
    # Manufacturing/BOM fields
    bom_product_id: Optional[str] = None
    production_quantity: Optional[Decimal] = None


class JobCardUpdate(BaseModel):
    customer_id: Optional[str] = None
    branch_id: Optional[str] = None
    job_type: Optional[str] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    notes: Optional[str] = None
    technician_id: Optional[str] = None
    vat_rate: Optional[Decimal] = None
    currency: Optional[str] = None
    materials: Optional[List[JobCardMaterialInput]] = None
    labor: Optional[List[JobCardLaborInput]] = None


class MaterialsUpdateRequest(BaseModel):
    materials: List[JobCardMaterialInput]
    mode: Literal["append", "replace"] = "append"


class LaborUpdateRequest(BaseModel):
    labor: List[JobCardLaborInput]
    mode: Literal["append", "replace"] = "append"


class JobCardStatusChange(BaseModel):
    status: str


class JobCardNoteCreate(BaseModel):
    note: str


class JobCardInvoiceRequest(BaseModel):
    save_draft: bool = False
    is_cash_sale: bool = False
