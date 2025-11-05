"""
Workflow Schemas - Pydantic models for workflow API requests/responses
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from app.models.workflow import WorkflowStatus, WorkflowActionType


# ========== Workflow State Schemas ==========

class WorkflowStateBase(BaseModel):
    name: str = Field(..., description="State name")
    code: str = Field(..., description="State code (unique within workflow)")
    status: WorkflowStatus = Field(..., description="Mapped workflow status")
    description: Optional[str] = None
    is_initial: bool = False
    is_final: bool = False
    requires_approval: bool = False
    allowed_roles: Optional[List[str]] = Field(default_factory=list, description="Role IDs that can act on this state")
    notified_roles: Optional[List[str]] = Field(default_factory=list, description="Role IDs to notify")
    display_order: int = 0
    color: str = "#3b82f6"
    icon: str = "circle"


class WorkflowStateCreate(WorkflowStateBase):
    workflow_definition_id: str


class WorkflowStateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    allowed_roles: Optional[List[str]] = None
    notified_roles: Optional[List[str]] = None
    display_order: Optional[int] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class WorkflowStateResponse(WorkflowStateBase):
    id: str
    workflow_definition_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ========== Workflow Transition Schemas ==========

class WorkflowTransitionBase(BaseModel):
    name: str = Field(..., description="Transition name")
    action: WorkflowActionType = Field(..., description="Action type")
    description: Optional[str] = None
    allowed_roles: Optional[List[str]] = Field(default_factory=list, description="Role IDs that can perform this transition")
    required_permission: Optional[str] = None
    requires_comment: bool = False
    requires_attachment: bool = False
    condition_script: Optional[str] = None
    notify_on_transition: bool = True
    notification_template: Optional[str] = None
    button_label: Optional[str] = None
    button_color: str = "primary"
    display_order: int = 0


class WorkflowTransitionCreate(WorkflowTransitionBase):
    workflow_definition_id: str
    from_state_id: str
    to_state_id: str


class WorkflowTransitionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    allowed_roles: Optional[List[str]] = None
    requires_comment: Optional[bool] = None
    requires_attachment: Optional[bool] = None
    button_label: Optional[str] = None
    button_color: Optional[str] = None
    display_order: Optional[int] = None


class WorkflowTransitionResponse(WorkflowTransitionBase):
    id: str
    workflow_definition_id: str
    from_state_id: str
    to_state_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ========== Workflow Definition Schemas ==========

class WorkflowDefinitionBase(BaseModel):
    name: str = Field(..., description="Workflow name")
    code: str = Field(..., description="Unique workflow code")
    description: Optional[str] = None
    module: str = Field(..., description="Module this workflow applies to")
    is_active: bool = True
    is_default: bool = False
    requires_approval: bool = True
    auto_submit: bool = False
    approval_threshold_amount: int = 0
    max_approval_levels: int = 3


class WorkflowDefinitionCreate(WorkflowDefinitionBase):
    branch_id: Optional[str] = None


class WorkflowDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    requires_approval: Optional[bool] = None
    auto_submit: Optional[bool] = None
    approval_threshold_amount: Optional[int] = None
    max_approval_levels: Optional[int] = None


class WorkflowDefinitionResponse(WorkflowDefinitionBase):
    id: str
    created_by: Optional[str] = None
    branch_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    states: List[WorkflowStateResponse] = []
    transitions: List[WorkflowTransitionResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ========== Workflow Action Schemas ==========

class WorkflowActionBase(BaseModel):
    action: WorkflowActionType
    comment: Optional[str] = None
    reason: Optional[str] = None
    attachments: Optional[List[str]] = Field(default_factory=list)


class WorkflowActionCreate(WorkflowActionBase):
    workflow_instance_id: str
    to_state_id: str
    reassigned_to: Optional[str] = None


class WorkflowActionResponse(WorkflowActionBase):
    id: str
    workflow_instance_id: str
    from_state_id: Optional[str] = None
    to_state_id: str
    action_date: datetime
    performed_by: str
    reassigned_from: Optional[str] = None
    reassigned_to: Optional[str] = None
    ip_address: Optional[str] = None
    duration_seconds: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ========== Workflow Instance Schemas ==========

class WorkflowInstanceBase(BaseModel):
    entity_type: str = Field(..., description="Type of entity (e.g., 'purchase', 'invoice')")
    entity_id: str = Field(..., description="ID of the entity")
    priority: str = "normal"
    due_date: Optional[datetime] = None
    workflow_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class WorkflowInstanceCreate(WorkflowInstanceBase):
    workflow_definition_id: str
    branch_id: Optional[str] = None


class WorkflowInstanceUpdate(BaseModel):
    current_assignee: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    workflow_metadata: Optional[Dict[str, Any]] = None


class WorkflowInstanceResponse(WorkflowInstanceBase):
    id: str
    workflow_definition_id: str
    current_state_id: str
    status: WorkflowStatus
    initiated_by: str
    initiated_at: datetime
    current_assignee: Optional[str] = None
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    branch_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowInstanceDetailResponse(WorkflowInstanceResponse):
    """Detailed workflow instance with actions history"""
    actions: List[WorkflowActionResponse] = []
    current_state: Optional[WorkflowStateResponse] = None
    workflow_definition: Optional[WorkflowDefinitionResponse] = None

    model_config = ConfigDict(from_attributes=True)


# ========== Workflow Operation Schemas ==========

class WorkflowSubmitRequest(BaseModel):
    """Request to submit entity for workflow approval"""
    comment: Optional[str] = None
    attachments: Optional[List[str]] = Field(default_factory=list)


class WorkflowApproveRequest(BaseModel):
    """Request to approve workflow item"""
    comment: Optional[str] = None
    attachments: Optional[List[str]] = Field(default_factory=list)


class WorkflowRejectRequest(BaseModel):
    """Request to reject workflow item"""
    reason: str = Field(..., description="Reason for rejection")
    comment: Optional[str] = None
    attachments: Optional[List[str]] = Field(default_factory=list)


class WorkflowReassignRequest(BaseModel):
    """Request to reassign workflow to another user"""
    assignee_id: str = Field(..., description="User ID to assign to")
    comment: Optional[str] = None


class WorkflowTransitionRequest(BaseModel):
    """Generic workflow transition request"""
    transition_id: str = Field(..., description="Transition ID to execute")
    comment: Optional[str] = None
    attachments: Optional[List[str]] = Field(default_factory=list)


# ========== Workflow Dashboard Schemas ==========

class WorkflowPendingItem(BaseModel):
    """Item pending approval in user's workflow queue"""
    workflow_instance_id: str
    entity_type: str
    entity_id: str
    entity_reference: Optional[str] = None  # e.g., "PO-2025-001"
    current_state_name: str
    initiated_by_name: str
    initiated_at: datetime
    priority: str
    due_date: Optional[datetime] = None
    time_in_current_state_hours: int
    available_actions: List[Dict[str, Any]] = []  # List of {action, label, color}


class WorkflowDashboardResponse(BaseModel):
    """Workflow dashboard summary for current user"""
    pending_approval_count: int
    pending_my_action_count: int
    submitted_by_me_count: int
    completed_today_count: int
    overdue_count: int
    pending_items: List[WorkflowPendingItem] = []


# ========== Workflow Template Schemas (for quick setup) ==========

class WorkflowTemplateRequest(BaseModel):
    """Request to create workflow from template"""
    template_name: str = Field(..., description="Template name (e.g., 'purchase_approval_3level')")
    module: str = Field(..., description="Module to apply to")
    name: str = Field(..., description="Custom workflow name")
    branch_id: Optional[str] = None
    approval_threshold_amount: int = 0


class WorkflowAvailableAction(BaseModel):
    """Available action for current user on a workflow instance"""
    transition_id: str
    action: WorkflowActionType
    label: str
    color: str
    requires_comment: bool
    requires_attachment: bool
    to_state_name: str
