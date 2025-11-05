import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Text, Integer, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Role(BaseModel):
    """Role model for role-based access control"""
    __tablename__ = "roles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    is_system_role = Column(Boolean, default=False)  # System roles cannot be deleted
    is_active = Column(Boolean, default=True)
    
    # Relationships
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    users = relationship("User", back_populates="role_obj")


class Permission(BaseModel):
    """Permission model for granular access control"""
    __tablename__ = "permissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    description = Column(Text)
    module = Column(String, nullable=False)  # e.g., 'users', 'inventory', 'sales'
    action = Column(String, nullable=False)  # e.g., 'create', 'read', 'update', 'delete'
    resource = Column(String, nullable=False)  # e.g., 'all', 'own_branch', 'specific_branch'
    
    # Relationships
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")


class RolePermission(BaseModel):
    """Many-to-many relationship between roles and permissions"""
    __tablename__ = "role_permissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    role_id = Column(ForeignKey("roles.id"), nullable=False)
    permission_id = Column(ForeignKey("permissions.id"), nullable=False)
    
    # Relationships
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="role_permissions")


class UserPermission(BaseModel):
    """Optional user-specific permission grants (overrides role permissions)."""
    __tablename__ = "user_permissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(ForeignKey("users.id"), nullable=False)
    permission_id = Column(ForeignKey("permissions.id"), nullable=False)

    # Relationships
    user = relationship("User", back_populates="user_permissions")
    permission = relationship("Permission")


class UserAuditLog(BaseModel):
    """Audit log for user actions to ensure accountability and traceability"""
    __tablename__ = "user_audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)  # e.g., 'create', 'update', 'delete', 'login'
    module = Column(String, nullable=False)  # e.g., 'users', 'inventory', 'sales'
    resource_type = Column(String, nullable=False)  # e.g., 'user', 'product', 'sale'
    resource_id = Column(String)  # ID of the affected resource
    details = Column(JSON)  # Additional details about the action
    ip_address = Column(String)
    user_agent = Column(String)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
