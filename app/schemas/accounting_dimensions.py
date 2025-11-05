"""
Pydantic schemas for Accounting Dimensions

These schemas define the data structures for API requests and responses
for the accounting dimensions functionality.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class DimensionTypeEnum(str, Enum):
    """Types of dimensions for categorization and validation"""
    ORGANIZATIONAL = "organizational"
    GEOGRAPHICAL = "geographical"
    FUNCTIONAL = "functional"
    PROJECT = "project"
    PRODUCT = "product"
    CUSTOMER = "customer"
    TEMPORAL = "temporal"
    CUSTOM = "custom"


class DimensionScopeEnum(str, Enum):
    """Scope of dimension application"""
    GLOBAL = "global"
    BRANCH = "branch"
    ENTITY = "entity"
    DEPARTMENT = "department"


# Base schemas
class AccountingDimensionBase(BaseModel):
    """Base schema for accounting dimensions"""
    code: str = Field(..., max_length=20, description="Unique code for the dimension")
    name: str = Field(..., max_length=100, description="Display name of the dimension")
    description: Optional[str] = Field(None, description="Detailed description")
    dimension_type: DimensionTypeEnum = Field(default=DimensionTypeEnum.CUSTOM)
    scope: DimensionScopeEnum = Field(default=DimensionScopeEnum.GLOBAL)
    is_active: bool = Field(default=True)
    is_required: bool = Field(default=False, description="Required on transactions")
    allow_multiple_values: bool = Field(default=False)
    supports_hierarchy: bool = Field(default=False)
    max_hierarchy_levels: int = Field(default=1, ge=1, le=10)
    display_order: int = Field(default=0)
    branch_id: Optional[str] = Field(None, description="Branch association")

    @validator('code')
    def validate_code(cls, v):
        if not v or not v.strip():
            raise ValueError('Code cannot be empty')
        return v.strip().upper()

    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()


class AccountingDimensionCreate(AccountingDimensionBase):
    """Schema for creating a new dimension"""
    pass


class AccountingDimensionUpdate(BaseModel):
    """Schema for updating a dimension"""
    code: Optional[str] = Field(None, max_length=20)
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    dimension_type: Optional[DimensionTypeEnum] = None
    scope: Optional[DimensionScopeEnum] = None
    is_active: Optional[bool] = None
    is_required: Optional[bool] = None
    allow_multiple_values: Optional[bool] = None
    supports_hierarchy: Optional[bool] = None
    max_hierarchy_levels: Optional[int] = Field(None, ge=1, le=10)
    display_order: Optional[int] = None


class AccountingDimensionResponse(AccountingDimensionBase):
    """Schema for dimension responses"""
    id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    dimension_values: Optional[List['AccountingDimensionValueResponse']] = Field(
        default=None,
        description="List of dimension values (populated when include_values=true)"
    )

    class Config:
        from_attributes = True


# Dimension Value schemas
class AccountingDimensionValueBase(BaseModel):
    """Base schema for dimension values"""
    code: str = Field(..., max_length=50, description="Unique code within dimension")
    name: str = Field(..., max_length=100, description="Display name")
    description: Optional[str] = Field(None, description="Detailed description")
    parent_value_id: Optional[str] = Field(None, description="Parent for hierarchy")
    is_active: bool = Field(default=True)
    display_order: int = Field(default=0)
    external_reference: Optional[str] = Field(None, max_length=100)

    @validator('code')
    def validate_code(cls, v):
        if not v or not v.strip():
            raise ValueError('Code cannot be empty')
        return v.strip().upper()

    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()


class AccountingDimensionValueCreate(AccountingDimensionValueBase):
    """Schema for creating dimension values"""
    dimension_id: str = Field(..., description="Dimension this value belongs to")


class AccountingDimensionValueUpdate(BaseModel):
    """Schema for updating dimension values"""
    code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    parent_value_id: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None
    external_reference: Optional[str] = Field(None, max_length=100)


class AccountingDimensionValueResponse(AccountingDimensionValueBase):
    """Schema for dimension value responses"""
    id: str
    dimension_id: str
    hierarchy_level: int
    hierarchy_path: Optional[str] = None
    full_path: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    children: Optional[List['AccountingDimensionValueResponse']] = []

    class Config:
        from_attributes = True


# Assignment schemas
class AccountingDimensionAssignmentBase(BaseModel):
    """Base schema for dimension assignments"""
    dimension_id: str = Field(..., description="Dimension being assigned")
    dimension_value_id: str = Field(..., description="Specific value assigned")
    allocation_percentage: float = Field(default=100.0, ge=0, le=100)
    allocation_amount: Optional[float] = Field(None, ge=0)
    assignment_method: str = Field(default="manual")
    notes: Optional[str] = None


class AccountingDimensionAssignmentCreate(AccountingDimensionAssignmentBase):
    """Schema for creating dimension assignments"""
    journal_entry_id: str = Field(..., description="Journal entry to assign to")


class AccountingDimensionAssignmentUpdate(BaseModel):
    """Schema for updating dimension assignments"""
    dimension_value_id: Optional[str] = None
    allocation_percentage: Optional[float] = Field(None, ge=0, le=100)
    allocation_amount: Optional[float] = Field(None, ge=0)
    assignment_method: Optional[str] = None
    notes: Optional[str] = None


class AccountingDimensionAssignmentResponse(AccountingDimensionAssignmentBase):
    """Schema for dimension assignment responses"""
    id: str
    journal_entry_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Enhanced Journal Entry schema with dimensions
class JournalEntryWithDimensions(BaseModel):
    """Journal entry with dimensional assignments"""
    id: str
    accounting_code_id: str
    accounting_entry_id: str
    entry_type: Optional[str] = None
    narration: Optional[str] = None
    date: Optional[datetime] = None
    reference: Optional[str] = None
    description: Optional[str] = None
    debit_amount: float = 0.0
    credit_amount: float = 0.0
    branch_id: Optional[str] = None
    origin: str = "manual"

    # Dimensional assignments
    dimension_assignments: List[AccountingDimensionAssignmentResponse] = []

    class Config:
        from_attributes = True


# Bulk operations
class BulkDimensionAssignment(BaseModel):
    """Schema for bulk dimension assignments"""
    journal_entry_ids: List[str] = Field(..., description="Journal entries to assign")
    assignments: List[AccountingDimensionAssignmentBase] = Field(..., description="Assignments to apply")


class DimensionAssignmentRule(BaseModel):
    """Schema for automated dimension assignment rules"""
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    conditions: Dict[str, Any] = Field(..., description="Conditions for automatic assignment")
    assignments: List[AccountingDimensionAssignmentBase] = Field(..., description="Assignments to apply")
    is_active: bool = Field(default=True)
    priority: int = Field(default=0, description="Rule priority (higher = first)")


# Templates
class DimensionTemplateBase(BaseModel):
    """Base schema for dimension templates"""
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    business_type: Optional[str] = Field(None, max_length=50)
    template_data: str = Field(..., description="JSON configuration data")
    is_active: bool = Field(default=True)


class DimensionTemplateCreate(DimensionTemplateBase):
    """Schema for creating dimension templates"""
    pass


class DimensionTemplateResponse(DimensionTemplateBase):
    """Schema for dimension template responses"""
    id: str
    usage_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Analysis and Reporting schemas
class DimensionAnalysisFilter(BaseModel):
    """Schema for dimension-based analysis filters"""
    dimension_values: Dict[str, List[str]] = Field(default_factory=dict,
                                                  description="Dimension ID -> List of value IDs")
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    account_types: Optional[List[str]] = None
    branch_ids: Optional[List[str]] = None
    include_inactive: bool = Field(default=False)


class DimensionAnalysisResult(BaseModel):
    """Schema for dimension analysis results"""
    dimension_breakdown: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    totals: Dict[str, float] = Field(default_factory=dict)
    period_comparison: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DimensionValidationResult(BaseModel):
    """Schema for dimension validation results"""
    is_valid: bool
    missing_required_dimensions: List[str] = []
    invalid_assignments: List[str] = []
    warnings: List[str] = []
    errors: List[str] = []


# Update forward references
AccountingDimensionResponse.model_rebuild()


# Update forward reference for nested model
AccountingDimensionValueResponse.model_rebuild()
