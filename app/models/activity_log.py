"""
Activity Log and Permission Management Models
Comprehensive tracking of user activities, approvals, and permission changes
"""
from sqlalchemy import Column, String, Text, DateTime, JSON, Boolean, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.models.base import BaseModel


class ActivityType(str, enum.Enum):
    """Types of activities that can be logged"""
    # CRUD Operations
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

    # Workflow Operations
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    REASSIGN = "reassign"
    CANCEL = "cancel"

    # Permission Operations
    GRANT_PERMISSION = "grant_permission"
    REVOKE_PERMISSION = "revoke_permission"
    ASSIGN_ROLE = "assign_role"
    REMOVE_ROLE = "remove_role"

    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"

    # Other
    EXPORT = "export"
    IMPORT = "import"
    PRINT = "print"
    EMAIL = "email"


class ActivityModule(str, enum.Enum):
    """Modules within the application"""
    USERS = "users"
    ROLES = "roles"
    PERMISSIONS = "permissions"
    BRANCHES = "branches"
    SALES = "sales"
    PURCHASES = "purchases"
    INVENTORY = "inventory"
    MANUFACTURING = "manufacturing"
    ACCOUNTING = "accounting"
    POS = "pos"
    REPORTING = "reporting"
    SETTINGS = "settings"
    WORKFLOWS = "workflows"
    AUDIT = "audit"


class ActivitySeverity(str, enum.Enum):
    """Severity level of the activity"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ActivityLog(BaseModel):
    """
    Comprehensive activity logging for all user actions
    Tracks who did what, when, where, and why
    """
    __tablename__ = "activity_logs"

    # Who performed the action
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    username = Column(String, nullable=False)  # Denormalized for performance
    role_name = Column(String, nullable=True)  # User's role at time of action

    # What was done
    activity_type = Column(SQLEnum(ActivityType), nullable=False, index=True)
    module = Column(SQLEnum(ActivityModule), nullable=False, index=True)
    action = Column(String, nullable=False)  # Specific action taken
    description = Column(Text, nullable=True)  # Human-readable description

    # Target of the action
    entity_type = Column(String, nullable=True)  # e.g., "Invoice", "Purchase Order"
    entity_id = Column(String, nullable=True, index=True)  # ID of the affected entity
    entity_name = Column(String, nullable=True)  # Name/identifier for display

    # Context
    branch_id = Column(String, ForeignKey("branches.id"), nullable=True, index=True)
    branch_name = Column(String, nullable=True)  # Denormalized

    # Details
    old_values = Column(JSON, nullable=True)  # State before change
    new_values = Column(JSON, nullable=True)  # State after change
    metadata = Column(JSON, nullable=True)  # Additional context

    # Result
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    severity = Column(SQLEnum(ActivitySeverity), default=ActivitySeverity.INFO, nullable=False)

    # Technical details
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    session_id = Column(String, nullable=True, index=True)

    # Timestamp
    performed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="activity_logs")
    branch = relationship("Branch", foreign_keys=[branch_id])

    # Indexes for common queries
    __table_args__ = (
        Index('idx_activity_user_module', 'user_id', 'module'),
        Index('idx_activity_entity', 'entity_type', 'entity_id'),
        Index('idx_activity_branch_date', 'branch_id', 'performed_at'),
        Index('idx_activity_type_date', 'activity_type', 'performed_at'),
    )


class ApprovalLog(BaseModel):
    """
    Detailed tracking of approval workflows
    Complements ActivityLog with approval-specific fields
    """
    __tablename__ = "approval_logs"

    # Who approved/rejected
    approver_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    approver_name = Column(String, nullable=False)
    approver_role = Column(String, nullable=True)

    # What was approved/rejected
    entity_type = Column(String, nullable=False, index=True)  # e.g., "PurchaseOrder"
    entity_id = Column(String, nullable=False, index=True)
    entity_reference = Column(String, nullable=True)  # e.g., "PO-2024-001"

    # Workflow context
    workflow_id = Column(String, ForeignKey("workflow_instances.id"), nullable=True, index=True)
    from_state = Column(String, nullable=True)
    to_state = Column(String, nullable=True)

    # Action taken
    action = Column(String, nullable=False)  # "approve", "reject", "request_changes"
    decision = Column(String, nullable=False)  # "approved", "rejected", "changes_requested"

    # Supporting information
    comments = Column(Text, nullable=True)
    attachments = Column(JSON, nullable=True)  # List of file references

    # Delegation
    on_behalf_of = Column(String, ForeignKey("users.id"), nullable=True)
    delegation_reason = Column(Text, nullable=True)

    # Metadata
    approval_level = Column(String, nullable=True)  # e.g., "L1", "L2", "L3"
    branch_id = Column(String, ForeignKey("branches.id"), nullable=True, index=True)
    metadata = Column(JSON, nullable=True)

    # Timestamp
    approved_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Technical
    ip_address = Column(String, nullable=True)

    # Relationships
    approver = relationship("User", foreign_keys=[approver_id], backref="approvals_given")
    delegated_by = relationship("User", foreign_keys=[on_behalf_of])
    branch = relationship("Branch", foreign_keys=[branch_id])

    __table_args__ = (
        Index('idx_approval_entity', 'entity_type', 'entity_id'),
        Index('idx_approval_user_date', 'approver_id', 'approved_at'),
        Index('idx_approval_workflow', 'workflow_id', 'approved_at'),
    )


class PermissionChangeLog(BaseModel):
    """
    Track all permission and role assignment changes
    Critical for security auditing
    """
    __tablename__ = "permission_change_logs"

    # Who made the change
    changed_by_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    changed_by_name = Column(String, nullable=False)

    # Who was affected
    target_user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    target_user_name = Column(String, nullable=True)
    target_role_id = Column(String, ForeignKey("roles.id"), nullable=True, index=True)
    target_role_name = Column(String, nullable=True)

    # What changed
    change_type = Column(String, nullable=False)  # "role_assign", "role_remove", "permission_grant", "permission_revoke"
    permission_id = Column(String, ForeignKey("permissions.id"), nullable=True)
    permission_name = Column(String, nullable=True)

    # Context
    old_value = Column(JSON, nullable=True)  # Previous state
    new_value = Column(JSON, nullable=True)  # New state
    reason = Column(Text, nullable=True)

    # Approval context
    approved_by_id = Column(String, ForeignKey("users.id"), nullable=True)
    approved_by_name = Column(String, nullable=True)
    approval_date = Column(DateTime, nullable=True)

    # Metadata
    branch_id = Column(String, ForeignKey("branches.id"), nullable=True)
    metadata = Column(JSON, nullable=True)

    # Timestamp
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True)  # For temporary permission grants

    # Technical
    ip_address = Column(String, nullable=True)

    # Relationships
    changed_by = relationship("User", foreign_keys=[changed_by_id])
    target_user = relationship("User", foreign_keys=[target_user_id])
    target_role = relationship("Role", foreign_keys=[target_role_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    permission = relationship("Permission", foreign_keys=[permission_id])
    branch = relationship("Branch", foreign_keys=[branch_id])

    __table_args__ = (
        Index('idx_permission_change_target', 'target_user_id', 'changed_at'),
        Index('idx_permission_change_type', 'change_type', 'changed_at'),
    )


class UserSession(BaseModel):
    """
    Track user sessions for security and activity correlation
    """
    __tablename__ = "user_sessions"

    # User
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    username = Column(String, nullable=False)

    # Session details
    session_token = Column(String, unique=True, nullable=False, index=True)
    session_start = Column(DateTime, default=datetime.utcnow, nullable=False)
    session_end = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Login context
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    login_method = Column(String, nullable=True)  # "password", "sso", "api_key"

    # Activity tracking
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    activity_count = Column(String, default="0", nullable=False)

    # Logout context
    logout_reason = Column(String, nullable=True)  # "manual", "timeout", "forced", "token_expired"

    # Branch context
    branch_id = Column(String, ForeignKey("branches.id"), nullable=True)

    # Metadata
    metadata = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="sessions")
    branch = relationship("Branch", foreign_keys=[branch_id])

    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_token_active', 'session_token', 'is_active'),
    )


class EntityAccessLog(BaseModel):
    """
    Track access to sensitive entities (read operations)
    For compliance and security monitoring
    """
    __tablename__ = "entity_access_logs"

    # Who accessed
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    username = Column(String, nullable=False)

    # What was accessed
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(String, nullable=False, index=True)
    entity_name = Column(String, nullable=True)

    # How it was accessed
    access_method = Column(String, nullable=True)  # "view", "export", "print", "api"
    module = Column(SQLEnum(ActivityModule), nullable=False)

    # Context
    branch_id = Column(String, ForeignKey("branches.id"), nullable=True)
    session_id = Column(String, nullable=True, index=True)

    # Technical
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    # Metadata
    metadata = Column(JSON, nullable=True)

    # Timestamp
    accessed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    branch = relationship("Branch", foreign_keys=[branch_id])

    __table_args__ = (
        Index('idx_access_entity', 'entity_type', 'entity_id'),
        Index('idx_access_user_date', 'user_id', 'accessed_at'),
    )
