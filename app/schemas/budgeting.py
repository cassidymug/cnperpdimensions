from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime


# Budget Schemas
class BudgetBase(BaseModel):
    name: str
    description: Optional[str] = None
    budget_type: str = "project"
    total_amount: Decimal
    start_date: date
    end_date: date
    status: str = "active"
    bank_account_id: Optional[str] = None
    parent_budget_id: Optional[str] = None
    branch_id: Optional[str] = None
    accounting_code_id: Optional[str] = None


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    budget_type: Optional[str] = None
    total_amount: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    bank_account_id: Optional[str] = None
    parent_budget_id: Optional[str] = None
    branch_id: Optional[str] = None
    accounting_code_id: Optional[str] = None


class BudgetResponse(BudgetBase):
    id: str
    allocated_amount: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    is_approved: bool
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Budget Allocation Schemas
class BudgetAllocationBase(BaseModel):
    budget_id: str
    name: str
    description: Optional[str] = None
    allocated_amount: Decimal
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str = "active"
    category: Optional[str] = None
    project_code: Optional[str] = None


class BudgetAllocationCreate(BudgetAllocationBase):
    pass


class BudgetAllocationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    allocated_amount: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    category: Optional[str] = None
    project_code: Optional[str] = None


class BudgetAllocationResponse(BudgetAllocationBase):
    id: str
    spent_amount: Decimal
    remaining_amount: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Budget Transaction Schemas
class BudgetTransactionBase(BaseModel):
    budget_id: str
    allocation_id: Optional[str] = None
    transaction_type: str
    amount: Decimal
    description: str
    reference: Optional[str] = None
    purchase_id: Optional[str] = None
    purchase_order_id: Optional[str] = None
    bank_transaction_id: Optional[str] = None
    status: str = "pending"


class BudgetTransactionCreate(BudgetTransactionBase):
    pass


class BudgetTransactionUpdate(BaseModel):
    allocation_id: Optional[str] = None
    transaction_type: Optional[str] = None
    amount: Optional[Decimal] = None
    description: Optional[str] = None
    reference: Optional[str] = None
    status: Optional[str] = None


class BudgetTransactionResponse(BudgetTransactionBase):
    id: str
    created_by: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Budget User Access Schemas
class BudgetUserAccessBase(BaseModel):
    budget_id: str
    user_id: str
    can_view: bool = True
    can_allocate: bool = False
    can_spend: bool = False
    can_approve: bool = False
    can_manage: bool = False
    access_start_date: Optional[date] = None
    access_end_date: Optional[date] = None
    is_active: bool = True


class BudgetUserAccessCreate(BudgetUserAccessBase):
    pass


class BudgetUserAccessUpdate(BaseModel):
    can_view: Optional[bool] = None
    can_allocate: Optional[bool] = None
    can_spend: Optional[bool] = None
    can_approve: Optional[bool] = None
    can_manage: Optional[bool] = None
    access_start_date: Optional[date] = None
    access_end_date: Optional[date] = None
    is_active: Optional[bool] = None


class BudgetUserAccessResponse(BudgetUserAccessBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Budget Request Schemas
class BudgetRequestBase(BaseModel):
    title: str
    description: Optional[str] = None
    requested_amount: Decimal
    budget_id: Optional[str] = None
    allocation_id: Optional[str] = None
    priority: str = "normal"
    urgency_level: int = Field(1, ge=1, le=5)


class BudgetRequestCreate(BudgetRequestBase):
    pass


class BudgetRequestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    requested_amount: Optional[Decimal] = None
    budget_id: Optional[str] = None
    allocation_id: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    urgency_level: Optional[int] = Field(None, ge=1, le=5)


class BudgetRequestResponse(BudgetRequestBase):
    id: str
    requested_by: str
    requested_at: datetime
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    approved_amount: Optional[Decimal] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Budget Summary and Analytics
class BudgetSummary(BaseModel):
    budget_id: str
    budget_name: str
    total_amount: Decimal
    allocated_amount: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    utilization_percentage: float
    status: str


class BudgetAnalytics(BaseModel):
    total_budgets: int
    active_budgets: int
    total_allocated: Decimal
    total_spent: Decimal
    total_remaining: Decimal
    average_utilization: float
    budget_summaries: List[BudgetSummary]


# Budget Approval Schemas
class BudgetApprovalRequest(BaseModel):
    budget_id: str
    approved_amount: Optional[Decimal] = None
    notes: Optional[str] = None


class BudgetApprovalResponse(BaseModel):
    success: bool
    message: str
    budget_id: str
    approved_amount: Decimal
    approved_by: str
    approved_at: datetime
