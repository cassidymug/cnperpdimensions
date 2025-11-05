"""
Pydantic Schemas for Activity Tracking and Permission Management
Request and response models for the activity and permission APIs
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== Enums ====================

class ActivityTypeEnum(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    REASSIGN = "reassign"
    CANCEL = "cancel"
    GRANT_PERMISSION = "grant_permission"
    REVOKE_PERMISSION = "revoke_permission"
    ASSIGN_ROLE = "assign_role"
    REMOVE_ROLE = "remove_role"
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    EXPORT = "export"
    IMPORT = "import"
    PRINT = "print"
    EMAIL = "email"


class ActivityModuleEnum(str, Enum):
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


class ActivitySeverityEnum(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ==================== Activity Log Schemas ====================

class ActivityLogCreate(BaseModel):
    """Schema for creating an activity log"""
    activity_type: ActivityTypeEnum
    module: ActivityModuleEnum
    action: str
    description: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    branch_id: Optional[str] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None
    severity: ActivitySeverityEnum = ActivitySeverityEnum.INFO


class ActivityLogResponse(BaseModel):
    """Schema for activity log response"""
    id: str
    user_id: str
    username: str
    role_name: Optional[str]
    activity_type: str
    module: str
    action: str
    description: Optional[str]
    entity_type: Optional[str]
    entity_id: Optional[str]
    entity_name: Optional[str]
    branch_id: Optional[str]
    branch_name: Optional[str]
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    success: bool
    error_message: Optional[str]
    severity: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    performed_at: datetime

    class Config:
        from_attributes = True


class ActivityLogFilter(BaseModel):
    """Schema for filtering activity logs"""
    user_id: Optional[str] = None
    module: Optional[ActivityModuleEnum] = None
    activity_type: Optional[ActivityTypeEnum] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    branch_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    severity: Optional[ActivitySeverityEnum] = None
    success: Optional[bool] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


# ==================== Approval Log Schemas ====================

class ApprovalLogCreate(BaseModel):
    """Schema for creating an approval log"""
    entity_type: str
    entity_id: str
    action: str
    decision: str
    entity_reference: Optional[str] = None
    workflow_id: Optional[str] = None
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    comments: Optional[str] = None
    attachments: Optional[List[str]] = None
    on_behalf_of: Optional[str] = None
    delegation_reason: Optional[str] = None
    approval_level: Optional[str] = None
    branch_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ApprovalLogResponse(BaseModel):
    """Schema for approval log response"""
    id: str
    approver_id: str
    approver_name: str
    approver_role: Optional[str]
    entity_type: str
    entity_id: str
    entity_reference: Optional[str]
    workflow_id: Optional[str]
    from_state: Optional[str]
    to_state: Optional[str]
    action: str
    decision: str
    comments: Optional[str]
    attachments: Optional[List[str]]
    on_behalf_of: Optional[str]
    delegation_reason: Optional[str]
    approval_level: Optional[str]
    branch_id: Optional[str]
    metadata: Optional[Dict[str, Any]]
    approved_at: datetime
    ip_address: Optional[str]

    class Config:
        from_attributes = True


class ApprovalLogFilter(BaseModel):
    """Schema for filtering approval logs"""
    approver_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    workflow_id: Optional[str] = None
    decision: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


# ==================== Permission Change Log Schemas ====================

class PermissionChangeLogResponse(BaseModel):
    """Schema for permission change log response"""
    id: str
    changed_by_id: str
    changed_by_name: str
    target_user_id: Optional[str]
    target_user_name: Optional[str]
    target_role_id: Optional[str]
    target_role_name: Optional[str]
    change_type: str
    permission_id: Optional[str]
    permission_name: Optional[str]
    old_value: Optional[Dict[str, Any]]
    new_value: Optional[Dict[str, Any]]
    reason: Optional[str]
    approved_by_id: Optional[str]
    approved_by_name: Optional[str]
    approval_date: Optional[datetime]
    branch_id: Optional[str]
    metadata: Optional[Dict[str, Any]]
    changed_at: datetime
    expires_at: Optional[datetime]
    ip_address: Optional[str]

    class Config:
        from_attributes = True


# ==================== Entity Access Log Schemas ====================

class EntityAccessLogResponse(BaseModel):
    """Schema for entity access log response"""
    id: str
    user_id: str
    username: str
    entity_type: str
    entity_id: str
    entity_name: Optional[str]
    access_method: Optional[str]
    module: str
    branch_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    metadata: Optional[Dict[str, Any]]
    accessed_at: datetime

    class Config:
        from_attributes = True


# ==================== Role Schemas ====================

class RoleCreate(BaseModel):
    """Schema for creating a role"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_system_role: bool = False
    reason: Optional[str] = None


class RoleUpdate(BaseModel):
    """Schema for updating a role"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    reason: Optional[str] = None


class RoleResponse(BaseModel):
    """Schema for role response"""
    id: str
    name: str
    description: Optional[str]
    is_system_role: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleWithPermissions(RoleResponse):
    """Schema for role with its permissions"""
    permissions: List['PermissionResponse']


# ==================== Permission Schemas ====================

class PermissionCreate(BaseModel):
    """Schema for creating a permission"""
    name: str = Field(..., min_length=1, max_length=200)
    module: str = Field(..., min_length=1, max_length=100)
    action: str = Field(..., min_length=1, max_length=100)
    resource: str = Field(default="all", max_length=100)
    description: Optional[str] = None


class PermissionResponse(BaseModel):
    """Schema for permission response"""
    id: str
    name: str
    module: str
    action: str
    resource: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Role-Permission Assignment Schemas ====================

class AssignPermissionToRole(BaseModel):
    """Schema for assigning permission to role"""
    permission_id: str
    reason: Optional[str] = None


class RevokePermissionFromRole(BaseModel):
    """Schema for revoking permission from role"""
    permission_id: str
    reason: Optional[str] = None


# ==================== User-Permission Assignment Schemas ====================

class AssignPermissionToUser(BaseModel):
    """Schema for assigning permission to user"""
    permission_id: str
    reason: Optional[str] = None
    expires_at: Optional[datetime] = None


class RevokePermissionFromUser(BaseModel):
    """Schema for revoking permission from user"""
    permission_id: str
    reason: Optional[str] = None


# ==================== User-Role Assignment Schemas ====================

class AssignRoleToUser(BaseModel):
    """Schema for assigning role to user"""
    role_id: str
    reason: Optional[str] = None


class RemoveRoleFromUser(BaseModel):
    """Schema for removing role from user"""
    reason: Optional[str] = None


# ==================== Permission Check Schemas ====================

class PermissionCheck(BaseModel):
    """Schema for checking permission"""
    module: str
    action: str
    resource: str = "all"


class PermissionCheckResponse(BaseModel):
    """Schema for permission check response"""
    has_permission: bool
    module: str
    action: str
    resource: str
    user_id: str
    username: str


# ==================== User Permissions Summary ====================

class UserPermissionSummary(BaseModel):
    """Schema for user permissions summary"""
    user_id: str
    username: str
    role: Optional[str]
    role_permissions: List[PermissionResponse]
    user_specific_permissions: List[Dict[str, Any]]
    all_permissions: List[PermissionResponse]


# ==================== Activity Statistics ====================

class ActivityStatistics(BaseModel):
    """Schema for activity statistics"""
    total_activities: int
    failed_activities: int
    success_rate: float
    by_type: Dict[str, int]
    by_module: Dict[str, int]
    top_users: List[Dict[str, Any]]


# ==================== Entity Activity History ====================

class EntityActivityHistory(BaseModel):
    """Schema for entity activity history"""
    entity_type: str
    entity_id: str
    activities: List[ActivityLogResponse]
    approvals: List[ApprovalLogResponse]
    access_logs: Optional[List[EntityAccessLogResponse]] = None


# ==================== Bulk Operations ====================

class BulkPermissionAssignment(BaseModel):
    """Schema for bulk permission assignment"""
    user_ids: List[str]
    permission_id: str
    reason: Optional[str] = None
    expires_at: Optional[datetime] = None


class BulkRoleAssignment(BaseModel):
    """Schema for bulk role assignment"""
    user_ids: List[str]
    role_id: str
    reason: Optional[str] = None


# Update forward references
RoleWithPermissions.model_rebuild()
