from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class PermissionBase(BaseModel):
    name: str = Field(..., description="Permission name")
    description: Optional[str] = Field(None, description="Permission description")
    module: str = Field(..., description="Module name (e.g., 'users', 'inventory')")
    action: str = Field(..., description="Action (e.g., 'create', 'read', 'update', 'delete')")
    resource: str = Field(..., description="Resource scope (e.g., 'all', 'own_branch')")


class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    module: Optional[str] = None
    action: Optional[str] = None
    resource: Optional[str] = None


class PermissionResponse(PermissionBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoleBase(BaseModel):
    name: str = Field(..., description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    is_system_role: bool = Field(False, description="Whether this is a system role")
    is_active: bool = Field(True, description="Whether the role is active")


class RoleCreate(RoleBase):
    permissions: Optional[List[str]] = Field([], description="List of permission IDs")


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    permissions: Optional[List[str]] = None


class RoleResponse(RoleBase):
    id: str
    permissions: List[PermissionResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RolePermissionBase(BaseModel):
    role_id: str
    permission_id: str


class RolePermissionCreate(RolePermissionBase):
    pass


class RolePermissionResponse(RolePermissionBase):
    id: str
    role: RoleResponse
    permission: PermissionResponse
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PermissionMatrixCell(BaseModel):
    module: str
    action: str
    resource: str = 'all'
    permission_id: Optional[str] = None
    role_ids: List[str] = []


class PermissionMatrixResponse(BaseModel):
    roles: List[RoleResponse]
    cells: List[PermissionMatrixCell]


class PermissionMatrixUpdate(BaseModel):
    cells: List[PermissionMatrixCell]


class PermissionMatrixUser(BaseModel):
    id: str
    username: str
    role_id: Optional[str] = None
    direct_permission_ids: List[str] = []
    effective_permission_ids: List[str] = []


class ExtendedPermissionMatrixResponse(PermissionMatrixResponse):
    users: List[PermissionMatrixUser]


class RoleFromMatrixCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permission_cells: List[PermissionMatrixCell] = []


class UserPermissionGrant(BaseModel):
    user_id: str
    permission_id: str


class UserPermissionResponse(BaseModel):
    id: str
    user_id: str
    permission_id: str
    permission: PermissionResponse
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserAuditLogBase(BaseModel):
    action: str = Field(..., description="Action performed")
    module: str = Field(..., description="Module where action was performed")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: Optional[str] = Field(None, description="ID of affected resource")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    ip_address: Optional[str] = Field(None, description="IP address of user")
    user_agent: Optional[str] = Field(None, description="User agent string")


class UserAuditLogCreate(UserAuditLogBase):
    user_id: str


class UserAuditLogResponse(UserAuditLogBase):
    id: str
    user_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrivilegeChart(BaseModel):
    """Chart for assigning privileges to users"""
    role_name: str
    description: str
    permissions: List[Dict[str, Any]] = Field(..., description="List of permissions with details")
    module_access: List[str] = Field(..., description="List of accessible modules")
    branch_access: str = Field(..., description="Branch access level ('all', 'own', 'specific')")
    audit_level: str = Field(..., description="Audit level ('full', 'basic', 'none')")


class RolePrivilegeAssignment(BaseModel):
    """Model for assigning privileges to roles"""
    role_id: str
    permission_ids: List[str]
    module_access: List[str]
    branch_access: str
    audit_level: str
