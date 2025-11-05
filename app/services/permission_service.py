"""
Permission Management Service
Comprehensive service for managing roles, permissions, and user access
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.role import Role, Permission, RolePermission, UserPermission
from app.models.user import User
from app.services.activity_service import ActivityService
from app.models.activity_log import ActivityModule


class PermissionService:
    """Service for managing permissions and roles"""

    def __init__(self, db: Session):
        self.db = db
        self.activity_service = ActivityService(db)

    # ==================== Role Management ====================

    def create_role(
        self,
        name: str,
        description: Optional[str] = None,
        is_system_role: bool = False,
        created_by_id: str = None,
        reason: Optional[str] = None
    ) -> Role:
        """
        Create a new role

        Args:
            name: Role name
            description: Role description
            is_system_role: Whether this is a system role (cannot be deleted)
            created_by_id: User creating the role
            reason: Reason for creating the role
        """
        # Check if role already exists
        existing = self.db.query(Role).filter(Role.name == name).first()
        if existing:
            raise ValueError(f"Role '{name}' already exists")

        role = Role(
            name=name,
            description=description,
            is_system_role=is_system_role,
            is_active=True
        )

        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)

        # Log the activity
        if created_by_id:
            self.activity_service.log_permission_change(
                changed_by_id=created_by_id,
                change_type="role_create",
                target_role_id=role.id,
                new_value={"name": name, "description": description},
                reason=reason
            )

        return role

    def update_role(
        self,
        role_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        updated_by_id: str = None,
        reason: Optional[str] = None
    ) -> Role:
        """Update an existing role"""
        role = self.db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise ValueError(f"Role {role_id} not found")

        old_values = {
            "name": role.name,
            "description": role.description,
            "is_active": role.is_active
        }

        if name is not None:
            # Check if new name conflicts
            existing = self.db.query(Role).filter(
                and_(Role.name == name, Role.id != role_id)
            ).first()
            if existing:
                raise ValueError(f"Role name '{name}' already exists")
            role.name = name

        if description is not None:
            role.description = description

        if is_active is not None:
            if role.is_system_role and not is_active:
                raise ValueError("System roles cannot be deactivated")
            role.is_active = is_active

        self.db.commit()
        self.db.refresh(role)

        new_values = {
            "name": role.name,
            "description": role.description,
            "is_active": role.is_active
        }

        # Log the change
        if updated_by_id:
            self.activity_service.log_permission_change(
                changed_by_id=updated_by_id,
                change_type="role_update",
                target_role_id=role_id,
                old_value=old_values,
                new_value=new_values,
                reason=reason
            )

        return role

    def delete_role(
        self,
        role_id: str,
        deleted_by_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Delete a role (if not system role)"""
        role = self.db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise ValueError(f"Role {role_id} not found")

        if role.is_system_role:
            raise ValueError("System roles cannot be deleted")

        # Check if any users have this role
        user_count = self.db.query(User).filter(User.role_id == role_id).count()
        if user_count > 0:
            raise ValueError(f"Cannot delete role: {user_count} users still assigned to this role")

        old_values = {
            "name": role.name,
            "description": role.description
        }

        self.db.delete(role)
        self.db.commit()

        # Log the deletion
        self.activity_service.log_permission_change(
            changed_by_id=deleted_by_id,
            change_type="role_delete",
            target_role_id=role_id,
            old_value=old_values,
            reason=reason
        )

        return True

    def get_all_roles(
        self,
        include_inactive: bool = False
    ) -> List[Role]:
        """Get all roles"""
        query = self.db.query(Role)

        if not include_inactive:
            query = query.filter(Role.is_active == True)

        return query.all()

    def get_role_by_id(self, role_id: str) -> Optional[Role]:
        """Get role by ID"""
        return self.db.query(Role).filter(Role.id == role_id).first()

    def get_role_by_name(self, name: str) -> Optional[Role]:
        """Get role by name"""
        return self.db.query(Role).filter(Role.name == name).first()

    # ==================== Permission Management ====================

    def create_permission(
        self,
        name: str,
        module: str,
        action: str,
        resource: str = "all",
        description: Optional[str] = None,
        created_by_id: str = None
    ) -> Permission:
        """Create a new permission"""
        # Check if permission already exists
        existing = self.db.query(Permission).filter(
            and_(
                Permission.module == module,
                Permission.action == action,
                Permission.resource == resource
            )
        ).first()

        if existing:
            raise ValueError(f"Permission already exists: {module}.{action}.{resource}")

        permission = Permission(
            name=name,
            module=module,
            action=action,
            resource=resource,
            description=description
        )

        self.db.add(permission)
        self.db.commit()
        self.db.refresh(permission)

        return permission

    def get_all_permissions(self) -> List[Permission]:
        """Get all permissions"""
        return self.db.query(Permission).all()

    def get_permissions_by_module(self, module: str) -> List[Permission]:
        """Get permissions for a specific module"""
        return self.db.query(Permission).filter(Permission.module == module).all()

    # ==================== Role-Permission Assignment ====================

    def assign_permission_to_role(
        self,
        role_id: str,
        permission_id: str,
        assigned_by_id: str,
        reason: Optional[str] = None
    ) -> RolePermission:
        """Assign a permission to a role"""
        # Verify role exists
        role = self.db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise ValueError(f"Role {role_id} not found")

        # Verify permission exists
        permission = self.db.query(Permission).filter(Permission.id == permission_id).first()
        if not permission:
            raise ValueError(f"Permission {permission_id} not found")

        # Check if already assigned
        existing = self.db.query(RolePermission).filter(
            and_(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id
            )
        ).first()

        if existing:
            raise ValueError("Permission already assigned to this role")

        role_permission = RolePermission(
            role_id=role_id,
            permission_id=permission_id
        )

        self.db.add(role_permission)
        self.db.commit()
        self.db.refresh(role_permission)

        # Log the assignment
        self.activity_service.log_permission_change(
            changed_by_id=assigned_by_id,
            change_type="permission_assign_to_role",
            target_role_id=role_id,
            permission_id=permission_id,
            new_value={
                "role": role.name,
                "permission": permission.name
            },
            reason=reason
        )

        return role_permission

    def revoke_permission_from_role(
        self,
        role_id: str,
        permission_id: str,
        revoked_by_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Revoke a permission from a role"""
        role_permission = self.db.query(RolePermission).filter(
            and_(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id
            )
        ).first()

        if not role_permission:
            raise ValueError("Permission not assigned to this role")

        # Get details for logging
        role = self.db.query(Role).filter(Role.id == role_id).first()
        permission = self.db.query(Permission).filter(Permission.id == permission_id).first()

        self.db.delete(role_permission)
        self.db.commit()

        # Log the revocation
        self.activity_service.log_permission_change(
            changed_by_id=revoked_by_id,
            change_type="permission_revoke_from_role",
            target_role_id=role_id,
            permission_id=permission_id,
            old_value={
                "role": role.name if role else None,
                "permission": permission.name if permission else None
            },
            reason=reason
        )

        return True

    def get_role_permissions(self, role_id: str) -> List[Permission]:
        """Get all permissions for a role"""
        return self.db.query(Permission).join(RolePermission).filter(
            RolePermission.role_id == role_id
        ).all()

    # ==================== User-Permission Assignment ====================

    def assign_permission_to_user(
        self,
        user_id: str,
        permission_id: str,
        assigned_by_id: str,
        reason: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> UserPermission:
        """Assign a permission directly to a user (overrides role permissions)"""
        # Verify user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Verify permission exists
        permission = self.db.query(Permission).filter(Permission.id == permission_id).first()
        if not permission:
            raise ValueError(f"Permission {permission_id} not found")

        # Check if already assigned
        existing = self.db.query(UserPermission).filter(
            and_(
                UserPermission.user_id == user_id,
                UserPermission.permission_id == permission_id
            )
        ).first()

        if existing:
            raise ValueError("Permission already assigned to this user")

        user_permission = UserPermission(
            user_id=user_id,
            permission_id=permission_id,
            granted_by=assigned_by_id,
            granted_at=datetime.utcnow(),
            expires_at=expires_at
        )

        self.db.add(user_permission)
        self.db.commit()
        self.db.refresh(user_permission)

        # Log the assignment
        self.activity_service.log_permission_change(
            changed_by_id=assigned_by_id,
            change_type="permission_grant",
            target_user_id=user_id,
            permission_id=permission_id,
            new_value={
                "user": user.username,
                "permission": permission.name,
                "expires_at": expires_at.isoformat() if expires_at else None
            },
            reason=reason,
            expires_at=expires_at
        )

        return user_permission

    def revoke_permission_from_user(
        self,
        user_id: str,
        permission_id: str,
        revoked_by_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Revoke a permission from a user"""
        user_permission = self.db.query(UserPermission).filter(
            and_(
                UserPermission.user_id == user_id,
                UserPermission.permission_id == permission_id
            )
        ).first()

        if not user_permission:
            raise ValueError("Permission not assigned to this user")

        # Get details for logging
        user = self.db.query(User).filter(User.id == user_id).first()
        permission = self.db.query(Permission).filter(Permission.id == permission_id).first()

        self.db.delete(user_permission)
        self.db.commit()

        # Log the revocation
        self.activity_service.log_permission_change(
            changed_by_id=revoked_by_id,
            change_type="permission_revoke",
            target_user_id=user_id,
            permission_id=permission_id,
            old_value={
                "user": user.username if user else None,
                "permission": permission.name if permission else None
            },
            reason=reason
        )

        return True

    def get_user_permissions(self, user_id: str) -> List[Permission]:
        """Get all permissions for a user (role + user-specific)"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        permissions = []

        # Get role permissions
        if user.role_id:
            role_permissions = self.get_role_permissions(user.role_id)
            permissions.extend(role_permissions)

        # Get user-specific permissions
        user_specific = self.db.query(Permission).join(UserPermission).filter(
            and_(
                UserPermission.user_id == user_id,
                or_(
                    UserPermission.expires_at.is_(None),
                    UserPermission.expires_at > datetime.utcnow()
                )
            )
        ).all()

        permissions.extend(user_specific)

        # Remove duplicates
        return list({p.id: p for p in permissions}.values())

    # ==================== User-Role Assignment ====================

    def assign_role_to_user(
        self,
        user_id: str,
        role_id: str,
        assigned_by_id: str,
        reason: Optional[str] = None
    ) -> User:
        """Assign a role to a user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        role = self.db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise ValueError(f"Role {role_id} not found")

        if not role.is_active:
            raise ValueError(f"Cannot assign inactive role")

        old_role_id = user.role_id
        old_role_name = user.role.name if user.role else None

        user.role_id = role_id
        self.db.commit()
        self.db.refresh(user)

        # Log the assignment
        self.activity_service.log_permission_change(
            changed_by_id=assigned_by_id,
            change_type="role_assign",
            target_user_id=user_id,
            target_role_id=role_id,
            old_value={"role": old_role_name},
            new_value={"role": role.name},
            reason=reason
        )

        return user

    def remove_role_from_user(
        self,
        user_id: str,
        removed_by_id: str,
        reason: Optional[str] = None
    ) -> User:
        """Remove role from a user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        old_role_name = user.role.name if user.role else None

        user.role_id = None
        self.db.commit()
        self.db.refresh(user)

        # Log the removal
        self.activity_service.log_permission_change(
            changed_by_id=removed_by_id,
            change_type="role_remove",
            target_user_id=user_id,
            old_value={"role": old_role_name},
            new_value={"role": None},
            reason=reason
        )

        return user

    # ==================== Permission Checking ====================

    def user_has_permission(
        self,
        user_id: str,
        module: str,
        action: str,
        resource: str = "all"
    ) -> bool:
        """
        Check if a user has a specific permission

        Args:
            user_id: User ID to check
            module: Permission module (e.g., "sales", "purchases")
            action: Permission action (e.g., "create", "read", "update", "delete")
            resource: Permission resource (e.g., "all", "own_branch")

        Returns:
            True if user has permission, False otherwise
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # Check user-specific permissions first (overrides)
        user_permission = self.db.query(Permission).join(UserPermission).filter(
            and_(
                UserPermission.user_id == user_id,
                Permission.module == module,
                Permission.action == action,
                Permission.resource == resource,
                or_(
                    UserPermission.expires_at.is_(None),
                    UserPermission.expires_at > datetime.utcnow()
                )
            )
        ).first()

        if user_permission:
            return True

        # Check role permissions
        if user.role_id:
            role_permission = self.db.query(Permission).join(RolePermission).filter(
                and_(
                    RolePermission.role_id == user.role_id,
                    Permission.module == module,
                    Permission.action == action,
                    Permission.resource == resource
                )
            ).first()

            if role_permission:
                return True

        return False

    def check_permission(
        self,
        user_id: str,
        module: str,
        action: str,
        resource: str = "all"
    ) -> None:
        """
        Check permission and raise exception if not permitted

        Raises:
            PermissionError: If user doesn't have permission
        """
        if not self.user_has_permission(user_id, module, action, resource):
            raise PermissionError(
                f"User does not have permission: {module}.{action}.{resource}"
            )

    def get_user_permissions_summary(self, user_id: str) -> Dict[str, Any]:
        """Get a summary of all user permissions"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        result = {
            "user_id": user_id,
            "username": user.username,
            "role": user.role.name if user.role else None,
            "role_permissions": [],
            "user_specific_permissions": [],
            "all_permissions": []
        }

        # Get role permissions
        if user.role_id:
            role_perms = self.get_role_permissions(user.role_id)
            result["role_permissions"] = [
                {
                    "id": p.id,
                    "name": p.name,
                    "module": p.module,
                    "action": p.action,
                    "resource": p.resource
                }
                for p in role_perms
            ]

        # Get user-specific permissions
        user_perms = self.db.query(Permission, UserPermission).join(UserPermission).filter(
            and_(
                UserPermission.user_id == user_id,
                or_(
                    UserPermission.expires_at.is_(None),
                    UserPermission.expires_at > datetime.utcnow()
                )
            )
        ).all()

        result["user_specific_permissions"] = [
            {
                "id": p.id,
                "name": p.name,
                "module": p.module,
                "action": p.action,
                "resource": p.resource,
                "granted_at": up.granted_at.isoformat() if up.granted_at else None,
                "expires_at": up.expires_at.isoformat() if up.expires_at else None
            }
            for p, up in user_perms
        ]

        # Get all permissions (combined)
        all_perms = self.get_user_permissions(user_id)
        result["all_permissions"] = [
            {
                "id": p.id,
                "name": p.name,
                "module": p.module,
                "action": p.action,
                "resource": p.resource
            }
            for p in all_perms
        ]

        return result
