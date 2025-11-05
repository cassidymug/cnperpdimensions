"""
Workflow Models - Role-based approval workflows for ERP modules

This module provides a flexible state machine-based workflow system that supports:
- Multi-level approvals based on user roles
- Configurable state transitions per module
- Audit trail of all workflow actions
- Role-based routing and notifications
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, DateTime, ForeignKey, Integer, JSON, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum


class WorkflowStatus(str, enum.Enum):
    """Standard workflow statuses across all modules"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    REVISION_REQUIRED = "revision_required"


class WorkflowActionType(str, enum.Enum):
    """Types of workflow actions"""
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    CANCEL = "cancel"
    REASSIGN = "reassign"
    REVISE = "revise"
    COMPLETE = "complete"
    HOLD = "hold"
    RESUME = "resume"


class WorkflowDefinition(BaseModel):
    """
    Workflow definition - defines a workflow template for a specific module

    Examples:
    - Purchase Order Approval (3-level: Submitter -> Manager -> Finance Director -> CEO)
    - Sales Invoice Approval (2-level: Salesperson -> Sales Manager -> Accountant)
    - Manufacturing Order (4-level: Requester -> Production Manager -> QA -> Warehouse)
    """
    __tablename__ = "workflow_definitions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Workflow identification
    name = Column(String, nullable=False)  # e.g., "Purchase Order Approval"
    code = Column(String, unique=True, nullable=False, index=True)  # e.g., "PO_APPROVAL"
    description = Column(Text)
    module = Column(String, nullable=False, index=True)  # e.g., "purchases", "sales", "manufacturing"

    # Configuration
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False)  # Default workflow for this module
    requires_approval = Column(Boolean, default=True)
    auto_submit = Column(Boolean, default=False)  # Auto-submit on creation

    # Approval thresholds
    approval_threshold_amount = Column(Integer, default=0)  # Min amount to trigger approval
    max_approval_levels = Column(Integer, default=3)

    # Metadata
    created_by = Column(String, ForeignKey("users.id"))
    branch_id = Column(String, ForeignKey("branches.id"))  # Branch-specific workflows

    # Relationships
    states = relationship("WorkflowState", back_populates="workflow_definition", cascade="all, delete-orphan")
    transitions = relationship("WorkflowTransition", back_populates="workflow_definition", cascade="all, delete-orphan")
    instances = relationship("WorkflowInstance", back_populates="workflow_definition")
    created_by_user = relationship("User", foreign_keys=[created_by])
    branch = relationship("Branch")


class WorkflowState(BaseModel):
    """
    Workflow state - individual state in a workflow

    Examples:
    - Draft, Submitted, Pending Manager Approval, Pending Finance Approval, Approved, Rejected
    """
    __tablename__ = "workflow_states"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    workflow_definition_id = Column(String, ForeignKey("workflow_definitions.id"), nullable=False, index=True)

    # State properties
    name = Column(String, nullable=False)  # e.g., "Pending Manager Approval"
    code = Column(String, nullable=False, index=True)  # e.g., "PENDING_MGR"
    status = Column(SQLEnum(WorkflowStatus), nullable=False)  # Maps to standard status
    description = Column(Text)

    # State behavior
    is_initial = Column(Boolean, default=False)  # Is this the starting state?
    is_final = Column(Boolean, default=False)  # Is this a terminal state?
    requires_approval = Column(Boolean, default=False)  # Does this state require approval action?

    # Role-based access (who can see/act on this state)
    allowed_roles = Column(JSON)  # List of role IDs that can act on items in this state
    notified_roles = Column(JSON)  # List of role IDs to notify when entering this state

    # Display
    display_order = Column(Integer, default=0)
    color = Column(String, default="#3b82f6")  # For UI display
    icon = Column(String, default="circle")  # Bootstrap icon name

    # Relationships
    workflow_definition = relationship("WorkflowDefinition", back_populates="states")
    transitions_from = relationship("WorkflowTransition", foreign_keys="WorkflowTransition.from_state_id", back_populates="from_state")
    transitions_to = relationship("WorkflowTransition", foreign_keys="WorkflowTransition.to_state_id", back_populates="to_state")


class WorkflowTransition(BaseModel):
    """
    Workflow transition - defines allowed state transitions

    Examples:
    - Draft -> Submitted (action: submit, roles: [submitter])
    - Submitted -> Pending Manager Approval (action: approve, roles: [manager])
    - Pending Manager Approval -> Rejected (action: reject, roles: [manager])
    """
    __tablename__ = "workflow_transitions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    workflow_definition_id = Column(String, ForeignKey("workflow_definitions.id"), nullable=False, index=True)
    from_state_id = Column(String, ForeignKey("workflow_states.id"), nullable=False, index=True)
    to_state_id = Column(String, ForeignKey("workflow_states.id"), nullable=False, index=True)

    # Transition properties
    name = Column(String, nullable=False)  # e.g., "Submit for Approval"
    action = Column(SQLEnum(WorkflowActionType), nullable=False)
    description = Column(Text)

    # Role-based authorization
    allowed_roles = Column(JSON)  # List of role IDs that can perform this transition
    required_permission = Column(String)  # Optional permission code required

    # Conditions
    requires_comment = Column(Boolean, default=False)  # Force user to add comment
    requires_attachment = Column(Boolean, default=False)
    condition_script = Column(Text)  # Python expression for conditional transitions

    # Notifications
    notify_on_transition = Column(Boolean, default=True)
    notification_template = Column(String)  # Email/SMS template ID

    # Display
    button_label = Column(String)  # e.g., "Approve", "Reject", "Submit"
    button_color = Column(String, default="primary")  # Bootstrap color class
    display_order = Column(Integer, default=0)

    # Relationships
    workflow_definition = relationship("WorkflowDefinition", back_populates="transitions")
    from_state = relationship("WorkflowState", foreign_keys=[from_state_id], back_populates="transitions_from")
    to_state = relationship("WorkflowState", foreign_keys=[to_state_id], back_populates="transitions_to")


class WorkflowInstance(BaseModel):
    """
    Workflow instance - tracks an actual workflow for a specific document/transaction

    Examples:
    - Purchase Order PO-2025-001 workflow instance
    - Sales Invoice INV-2025-123 workflow instance
    """
    __tablename__ = "workflow_instances"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    workflow_definition_id = Column(String, ForeignKey("workflow_definitions.id"), nullable=False, index=True)
    current_state_id = Column(String, ForeignKey("workflow_states.id"), nullable=False, index=True)

    # Document reference
    entity_type = Column(String, nullable=False, index=True)  # e.g., "purchase", "invoice", "manufacturing_order"
    entity_id = Column(String, nullable=False, index=True)  # ID of the actual purchase/invoice/etc

    # Workflow status
    status = Column(SQLEnum(WorkflowStatus), nullable=False, default=WorkflowStatus.DRAFT, index=True)

    # Tracking
    initiated_by = Column(String, ForeignKey("users.id"), nullable=False)
    initiated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    current_assignee = Column(String, ForeignKey("users.id"))  # Currently assigned to

    # Completion tracking
    completed_at = Column(DateTime)
    completed_by = Column(String, ForeignKey("users.id"))

    # Metadata
    branch_id = Column(String, ForeignKey("branches.id"))
    priority = Column(String, default="normal")  # low, normal, high, urgent
    due_date = Column(DateTime)

    # Additional data
    workflow_metadata = Column(JSON)  # Custom metadata for this workflow instance

    # Relationships
    workflow_definition = relationship("WorkflowDefinition", back_populates="instances")
    current_state = relationship("WorkflowState")
    initiated_by_user = relationship("User", foreign_keys=[initiated_by])
    current_assignee_user = relationship("User", foreign_keys=[current_assignee])
    completed_by_user = relationship("User", foreign_keys=[completed_by])
    branch = relationship("Branch")
    actions = relationship("WorkflowAction", back_populates="workflow_instance", cascade="all, delete-orphan")


class WorkflowAction(BaseModel):
    """
    Workflow action - audit trail of all actions taken on a workflow

    Examples:
    - User "john@example.com" submitted purchase order at 2025-01-15 10:30
    - Manager "jane@example.com" approved with comment "Approved for Q1 budget"
    - Finance Director "bob@example.com" rejected with comment "Exceeds budget"
    """
    __tablename__ = "workflow_actions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    workflow_instance_id = Column(String, ForeignKey("workflow_instances.id"), nullable=False, index=True)
    from_state_id = Column(String, ForeignKey("workflow_states.id"))
    to_state_id = Column(String, ForeignKey("workflow_states.id"), nullable=False, index=True)

    # Action details
    action = Column(SQLEnum(WorkflowActionType), nullable=False)
    action_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    performed_by = Column(String, ForeignKey("users.id"), nullable=False)

    # Context
    comment = Column(Text)
    reason = Column(String)  # Rejection reason, etc
    attachments = Column(JSON)  # List of attachment file paths

    # Reassignment
    reassigned_from = Column(String, ForeignKey("users.id"))
    reassigned_to = Column(String, ForeignKey("users.id"))

    # Metadata
    ip_address = Column(String)
    user_agent = Column(String)
    duration_seconds = Column(Integer)  # Time spent in previous state

    # Relationships
    workflow_instance = relationship("WorkflowInstance", back_populates="actions")
    from_state = relationship("WorkflowState", foreign_keys=[from_state_id])
    to_state = relationship("WorkflowState", foreign_keys=[to_state_id])
    performed_by_user = relationship("User", foreign_keys=[performed_by])
    reassigned_from_user = relationship("User", foreign_keys=[reassigned_from])
    reassigned_to_user = relationship("User", foreign_keys=[reassigned_to])


class WorkflowNotification(BaseModel):
    """
    Workflow notification - tracks notifications sent for workflow events
    """
    __tablename__ = "workflow_notifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    workflow_instance_id = Column(String, ForeignKey("workflow_instances.id"), nullable=False, index=True)
    workflow_action_id = Column(String, ForeignKey("workflow_actions.id"), index=True)

    # Notification details
    recipient_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    notification_type = Column(String, nullable=False)  # email, sms, in_app
    subject = Column(String)
    message = Column(Text)

    # Status
    sent_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime)
    is_read = Column(Boolean, default=False, index=True)

    # Delivery tracking
    delivery_status = Column(String, default="sent")  # sent, delivered, failed, bounced
    error_message = Column(Text)

    # Relationships
    workflow_instance = relationship("WorkflowInstance")
    workflow_action = relationship("WorkflowAction")
    recipient_user = relationship("User")
