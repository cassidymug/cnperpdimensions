"""
Pydantic schemas for Accounting Code Dimension Requirements API
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AccountingCodeDimensionRequirementBase(BaseModel):
    """Base schema for dimension requirements"""
    dimension_id: str = Field(..., description="ID of the required dimension")
    is_required: bool = Field(default=False, description="Whether this dimension is required")
    default_dimension_value_id: Optional[str] = Field(None, description="Default dimension value ID")
    priority: int = Field(default=1, ge=1, le=100, description="Priority order (1-100)")
    description: Optional[str] = Field(None, description="Description of the requirement")


class AccountingCodeDimensionRequirementCreate(AccountingCodeDimensionRequirementBase):
    """Schema for creating dimension requirements"""
    pass


class AccountingCodeDimensionRequirementUpdate(BaseModel):
    """Schema for updating dimension requirements"""
    is_required: Optional[bool] = None
    default_dimension_value_id: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=100)
    description: Optional[str] = None


class DimensionInfo(BaseModel):
    """Dimension information for responses"""
    id: str
    code: str
    name: str
    dimension_type: str


class DimensionValueInfo(BaseModel):
    """Dimension value information for responses"""
    id: str
    code: str
    name: str
    full_path: str


class AccountingCodeDimensionRequirementResponse(AccountingCodeDimensionRequirementBase):
    """Schema for dimension requirement responses"""
    id: str
    accounting_code_id: str
    dimension: Optional[DimensionInfo] = None
    default_dimension_value: Optional[DimensionValueInfo] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DimensionBalanceItem(BaseModel):
    """Individual dimension balance item"""
    dimension_code: str
    dimension_name: str
    dimension_value_code: str
    dimension_value_name: str
    dimension_value_path: str
    balance: float
    debit_total: float
    credit_total: float
    transaction_count: int


class AccountDimensionBalancesResponse(BaseModel):
    """Response schema for account dimension balances"""
    account_id: str
    account_code: str
    account_name: str
    total_balance: float
    dimension_requirements: List[AccountingCodeDimensionRequirementResponse]
    dimension_balances: List[DimensionBalanceItem]
    message: Optional[str] = None


class AccountingCodeDimensionTemplateBase(BaseModel):
    """Base schema for dimension templates"""
    name: str = Field(..., max_length=100, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    account_type: Optional[str] = Field(None, description="Apply to accounts of this type")
    category: Optional[str] = Field(None, description="Apply to accounts of this category")
    account_code_pattern: Optional[str] = Field(None, description="Apply to accounts matching this pattern")
    is_active: bool = Field(default=True, description="Whether template is active")


class AccountingCodeDimensionTemplateCreate(AccountingCodeDimensionTemplateBase):
    """Schema for creating dimension templates"""
    dimension_requirements: List[AccountingCodeDimensionRequirementBase] = []


class AccountingCodeDimensionTemplateItemResponse(BaseModel):
    """Schema for template item responses"""
    id: str
    template_id: str
    dimension_id: str
    is_required: bool
    default_dimension_value_id: Optional[str]
    priority: int
    dimension: Optional[DimensionInfo] = None
    default_dimension_value: Optional[DimensionValueInfo] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AccountingCodeDimensionTemplateResponse(AccountingCodeDimensionTemplateBase):
    """Schema for dimension template responses"""
    id: str
    dimension_requirements: List[AccountingCodeDimensionTemplateItemResponse] = []
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApplyTemplateRequest(BaseModel):
    """Schema for applying templates to accounts"""
    template_id: str
    account_ids: Optional[List[str]] = Field(None, description="Specific account IDs, or None for all matching accounts")


class ApplyTemplateResponse(BaseModel):
    """Schema for template application results"""
    template_id: str
    template_name: str
    accounts_processed: int
    requirements_created: int
    errors: List[str]


class BulkDimensionRequirementCreate(BaseModel):
    """Schema for creating dimension requirements for multiple accounts"""
    account_ids: List[str]
    dimension_requirements: List[AccountingCodeDimensionRequirementBase]


class BulkDimensionRequirementResponse(BaseModel):
    """Schema for bulk dimension requirement creation results"""
    accounts_processed: int
    requirements_created: int
    errors: List[str]
    created_requirements: List[AccountingCodeDimensionRequirementResponse]
