from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict
from decimal import Decimal
from datetime import date, datetime


class RequisitionItemBase(BaseModel):
    product_id: Optional[str] = None
    description: str
    quantity: Decimal
    unit_of_measure: Optional[str] = None
    estimated_unit_cost: Optional[Decimal] = None
    total_estimated_cost: Optional[Decimal] = None


class RequisitionItemCreate(RequisitionItemBase):
    pass


class RequisitionItemResponse(RequisitionItemBase):
    id: str
    requisition_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RequisitionBase(BaseModel):
    title: str
    description: Optional[str] = None
    requested_by: Optional[str] = None
    branch_id: Optional[str] = None
    status: str = "draft"
    needed_by: Optional[date] = None
    budget_code_id: Optional[str] = None
    notes: Optional[str] = None
    supplier_id: Optional[str] = None


class RequisitionCreate(RequisitionBase):
    items: List[RequisitionItemCreate] = []


class RequisitionResponse(RequisitionBase):
    id: str
    created_at: datetime
    updated_at: datetime
    items: List[RequisitionItemResponse] = []
    # Optionally include supplier basic info
    # supplier: Optional[SupplierResponse] = None

    model_config = ConfigDict(from_attributes=True)


class RFQInviteBase(BaseModel):
    supplier_id: str
    invited: bool = True
    notes: Optional[str] = None


class RFQInviteCreate(RFQInviteBase):
    pass


class RFQInviteResponse(RFQInviteBase):
    id: str
    rfq_id: str
    responded: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RFQBase(BaseModel):
    requisition_id: Optional[str] = None
    rfq_number: Optional[str] = None
    title: str
    description: Optional[str] = None
    issue_date: Optional[date] = None
    closing_date: Optional[date] = None
    status: str = "draft"
    branch_id: Optional[str] = None


class RFQCreate(RFQBase):
    invites: List[RFQInviteCreate] = []


class RFQResponse(RFQBase):
    id: str
    created_at: datetime
    updated_at: datetime
    invites: List[RFQInviteResponse] = []

    model_config = ConfigDict(from_attributes=True)


class SupplierQuoteItemBase(BaseModel):
    product_id: Optional[str] = None
    description: str
    quantity: Decimal
    unit_cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = Decimal('0')
    vat_amount: Optional[Decimal] = Decimal('0')


class SupplierQuoteItemCreate(SupplierQuoteItemBase):
    pass


class SupplierQuoteItemResponse(SupplierQuoteItemBase):
    id: str
    quote_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierQuoteBase(BaseModel):
    rfq_id: str
    supplier_id: str
    quote_number: Optional[str] = None
    quote_date: Optional[date] = None
    total_amount: Optional[Decimal] = None
    total_vat_amount: Optional[Decimal] = Decimal('0')
    currency: str = "BWP"
    valid_until: Optional[date] = None
    status: str = "submitted"
    notes: Optional[str] = None


class SupplierQuoteCreate(SupplierQuoteBase):
    items: List[SupplierQuoteItemCreate] = []


class SupplierQuoteResponse(SupplierQuoteBase):
    id: str
    created_at: datetime
    updated_at: datetime
    items: List[SupplierQuoteItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ProcurementAwardBase(BaseModel):
    rfq_id: Optional[str] = None
    quote_id: str
    award_number: Optional[str] = None
    award_date: Optional[date] = None
    status: str = "awarded"
    notes: Optional[str] = None
    branch_id: Optional[str] = None
    purchase_order_id: Optional[str] = None
    po_number: Optional[str] = None


class ProcurementAwardCreate(ProcurementAwardBase):
    pass


class ProcurementAwardResponse(ProcurementAwardBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierPerformanceBase(BaseModel):
    supplier_id: str
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    on_time_delivery_score: int = 0
    quality_score: int = 0
    responsiveness_score: int = 0
    compliance_score: int = 0
    overall_score: int = 0
    notes: Optional[str] = None


class SupplierPerformanceCreate(SupplierPerformanceBase):
    pass


class SupplierPerformanceResponse(SupplierPerformanceBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Supplier Evaluation Ticketing
class SupplierEvaluationMilestoneBase(BaseModel):
    name: str
    description: Optional[str] = None
    sequence: Optional[int] = 0
    status: Optional[str] = "pending"
    due_date: Optional[date] = None
    completed_at: Optional[date] = None
    notes: Optional[str] = None


class SupplierEvaluationMilestoneCreate(SupplierEvaluationMilestoneBase):
    pass


class SupplierEvaluationMilestoneResponse(SupplierEvaluationMilestoneBase):
    id: str
    ticket_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierEvaluationTicketBase(BaseModel):
    supplier_id: str
    purchase_order_id: str
    status: str = "open"
    opened_at: Optional[date] = None
    closed_at: Optional[date] = None
    branch_id: Optional[str] = None
    notes: Optional[str] = None


class SupplierEvaluationTicketCreate(SupplierEvaluationTicketBase):
    milestones: List[SupplierEvaluationMilestoneCreate] = []


class SupplierEvaluationTicketResponse(SupplierEvaluationTicketBase):
    id: str
    created_at: datetime
    updated_at: datetime
    milestones: List[SupplierEvaluationMilestoneResponse] = []

    model_config = ConfigDict(from_attributes=True)

# Evaluation API
class SupplierPerformanceEvaluateRequest(BaseModel):
    supplier_id: Optional[str] = None
    period_start: date
    period_end: date
    persist: bool = True


class SupplierPerformanceEvaluateResult(BaseModel):
    supplier_id: str
    period_start: date
    period_end: date
    on_time_delivery_score: int
    quality_score: int
    responsiveness_score: int
    compliance_score: int
    overall_score: int
    details: Dict[str, Optional[Decimal]] = {}

