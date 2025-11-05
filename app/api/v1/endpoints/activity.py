"""
Activity Tracking and Permission Management API Endpoints
Comprehensive REST API for viewing activities and managing permissions
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.activity_service import ActivityService
from app.services.permission_service import PermissionService
from app.schemas.activity import (
    ActivityLogResponse, ActivityLogFilter, ActivityStatistics,
    ApprovalLogResponse, ApprovalLogFilter,
    PermissionChangeLogResponse, EntityAccessLogResponse,
    RoleCreate, RoleUpdate, RoleResponse, RoleWithPermissions,
    PermissionCreate, PermissionResponse,
    AssignPermissionToRole, RevokePermissionFromRole,
    AssignPermissionToUser, RevokePermissionFromUser,
    AssignRoleToUser, RemoveRoleFromUser,
    PermissionCheck, PermissionCheckResponse,
    UserPermissionSummary, EntityActivityHistory,
    BulkPermissionAssignment, BulkRoleAssignment
)
from app.models.activity_log import ActivityType, ActivityModule
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/activity", tags=["Activity Tracking & Permissions"])


# ==================== Activity Log Endpoints ====================

@router.get("/logs", response_model=List[ActivityLogResponse])
def get_activities(
    user_id: Optional[str] = None,
    module: Optional[str] = None,
    activity_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get activity logs with optional filters

    Requires: admin.activities.read permission
    """
    service = ActivityService(db)

    # Build filter criteria
    query = db.query(service.db.query(service.db.query.__class__))

    # For now, return user's own activities
    # TODO: Add permission check for viewing all activities
    if user_id:
        activities = service.get_user_activities(
            user_id=user_id,
            module=ActivityModule(module) if module else None,
            activity_type=ActivityType(activity_type) if activity_type else None,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
    else:
        activities = service.get_user_activities(
            user_id=current_user.id,
            module=ActivityModule(module) if module else None,
            activity_type=ActivityType(activity_type) if activity_type else None,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )

    return activities


@router.get("/logs/entity/{entity_type}/{entity_id}", response_model=EntityActivityHistory)
def get_entity_activity_history(
    entity_type: str,
    entity_id: str,
    include_access_logs: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get complete activity history for a specific entity

    Includes:
    - All activities (create, update, delete, etc.)
    - Approval history
    - Access logs (optional)
    """
    service = ActivityService(db)
    history = service.get_entity_activities(
        entity_type=entity_type,
        entity_id=entity_id,
        include_access_logs=include_access_logs
    )

    return EntityActivityHistory(
        entity_type=entity_type,
        entity_id=entity_id,
        activities=history["activities"],
        approvals=history["approvals"],
        access_logs=history.get("access_logs")
    )


@router.get("/logs/module/{module}", response_model=List[ActivityLogResponse])
def get_module_activities(
    module: str,
    branch_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get activities for a specific module"""
    service = ActivityService(db)
    activities = service.get_module_activities(
        module=ActivityModule(module),
        branch_id=branch_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )

    return activities


@router.get("/statistics", response_model=ActivityStatistics)
def get_activity_statistics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user_id: Optional[str] = None,
    module: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get activity statistics"""
    service = ActivityService(db)
    stats = service.get_activity_statistics(
        start_date=start_date,
        end_date=end_date,
        user_id=user_id,
        module=ActivityModule(module) if module else None
    )

    return ActivityStatistics(**stats)


# ==================== Approval Log Endpoints ====================

@router.get("/approvals", response_model=List[ApprovalLogResponse])
def get_approvals(
    approver_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get approval history with optional filters"""
    service = ActivityService(db)

    # If no approver specified, return current user's approvals
    if not approver_id:
        approver_id = current_user.id

    approvals = service.get_approval_history(
        approver_id=approver_id,
        entity_type=entity_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )

    return approvals


@router.get("/approvals/entity/{entity_type}/{entity_id}", response_model=List[ApprovalLogResponse])
def get_entity_approvals(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all approvals for a specific entity"""
    from app.models.activity_log import ApprovalLog
    from sqlalchemy import and_
    approvals = db.query(ApprovalLog).filter(
        and_(
            ApprovalLog.entity_type == entity_type,
            ApprovalLog.entity_id == entity_id
        )
    ).order_by(ApprovalLog.approved_at.desc()).all()

    return approvals


# ==================== Permission Change Log Endpoints ====================

@router.get("/permission-changes", response_model=List[PermissionChangeLogResponse])
def get_permission_changes(
    target_user_id: Optional[str] = None,
    changed_by_id: Optional[str] = None,
    change_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get permission change history"""
    service = ActivityService(db)
    changes = service.get_permission_changes(
        target_user_id=target_user_id,
        changed_by_id=changed_by_id,
        change_type=change_type,
        start_date=start_date,
        limit=limit
    )

    return changes


@router.get("/permission-changes/user/{user_id}", response_model=List[PermissionChangeLogResponse])
def get_user_permission_changes(
    user_id: str,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all permission changes for a specific user"""
    service = ActivityService(db)
    changes = service.get_permission_changes(
        target_user_id=user_id,
        limit=limit
    )

    return changes


# ==================== Role Management Endpoints ====================

@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    role: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new role

    Requires: admin.roles.create permission
    """
    permission_service = PermissionService(db)

    try:
        new_role = permission_service.create_role(
            name=role.name,
            description=role.description,
            is_system_role=role.is_system_role,
            created_by_id=current_user.id,
            reason=role.reason
        )
        return new_role
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/roles", response_model=List[RoleResponse])
def get_all_roles(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all roles"""
    permission_service = PermissionService(db)
    roles = permission_service.get_all_roles(include_inactive=include_inactive)
    return roles


@router.get("/roles/{role_id}", response_model=RoleWithPermissions)
def get_role(
    role_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get role by ID with its permissions"""
    permission_service = PermissionService(db)
    role = permission_service.get_role_by_id(role_id)

    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    permissions = permission_service.get_role_permissions(role_id)

    return RoleWithPermissions(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system_role=role.is_system_role,
        is_active=role.is_active,
        created_at=role.created_at,
        updated_at=role.updated_at,
        permissions=permissions
    )


@router.patch("/roles/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: str,
    role: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a role

    Requires: admin.roles.update permission
    """
    permission_service = PermissionService(db)

    try:
        updated_role = permission_service.update_role(
            role_id=role_id,
            name=role.name,
            description=role.description,
            is_active=role.is_active,
            updated_by_id=current_user.id,
            reason=role.reason
        )
        return updated_role
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(
    role_id: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a role

    Requires: admin.roles.delete permission
    System roles cannot be deleted
    """
    permission_service = PermissionService(db)

    try:
        permission_service.delete_role(
            role_id=role_id,
            deleted_by_id=current_user.id,
            reason=reason
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Permission Endpoints ====================

@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
def create_permission(
    permission: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new permission

    Requires: admin.permissions.create permission
    """
    permission_service = PermissionService(db)

    try:
        new_permission = permission_service.create_permission(
            name=permission.name,
            module=permission.module,
            action=permission.action,
            resource=permission.resource,
            description=permission.description,
            created_by_id=current_user.id
        )
        return new_permission
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/permissions", response_model=List[PermissionResponse])
def get_all_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all permissions"""
    permission_service = PermissionService(db)
    permissions = permission_service.get_all_permissions()
    return permissions


@router.get("/permissions/module/{module}", response_model=List[PermissionResponse])
def get_module_permissions(
    module: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get permissions for a specific module"""
    permission_service = PermissionService(db)
    permissions = permission_service.get_permissions_by_module(module)
    return permissions


# ==================== Role-Permission Assignment Endpoints ====================

@router.post("/roles/{role_id}/permissions", status_code=status.HTTP_201_CREATED)
def assign_permission_to_role(
    role_id: str,
    assignment: AssignPermissionToRole,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Assign a permission to a role

    Requires: admin.roles.manage_permissions permission
    """
    permission_service = PermissionService(db)

    try:
        permission_service.assign_permission_to_role(
            role_id=role_id,
            permission_id=assignment.permission_id,
            assigned_by_id=current_user.id,
            reason=assignment.reason
        )
        return {"message": "Permission assigned successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/roles/{role_id}/permissions/{permission_id}")
def revoke_permission_from_role(
    role_id: str,
    permission_id: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Revoke a permission from a role

    Requires: admin.roles.manage_permissions permission
    """
    permission_service = PermissionService(db)

    try:
        permission_service.revoke_permission_from_role(
            role_id=role_id,
            permission_id=permission_id,
            revoked_by_id=current_user.id,
            reason=reason
        )
        return {"message": "Permission revoked successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== User-Permission Assignment Endpoints ====================

@router.post("/users/{user_id}/permissions", status_code=status.HTTP_201_CREATED)
def assign_permission_to_user(
    user_id: str,
    assignment: AssignPermissionToUser,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Assign a permission directly to a user

    Requires: admin.users.manage_permissions permission
    """
    permission_service = PermissionService(db)

    try:
        permission_service.assign_permission_to_user(
            user_id=user_id,
            permission_id=assignment.permission_id,
            assigned_by_id=current_user.id,
            reason=assignment.reason,
            expires_at=assignment.expires_at
        )
        return {"message": "Permission assigned successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/users/{user_id}/permissions/{permission_id}")
def revoke_permission_from_user(
    user_id: str,
    permission_id: str,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Revoke a permission from a user

    Requires: admin.users.manage_permissions permission
    """
    permission_service = PermissionService(db)

    try:
        permission_service.revoke_permission_from_user(
            user_id=user_id,
            permission_id=permission_id,
            revoked_by_id=current_user.id,
            reason=reason
        )
        return {"message": "Permission revoked successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== User-Role Assignment Endpoints ====================

@router.post("/users/{user_id}/role")
def assign_role_to_user(
    user_id: str,
    assignment: AssignRoleToUser,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Assign a role to a user

    Requires: admin.users.manage_roles permission
    """
    permission_service = PermissionService(db)

    try:
        permission_service.assign_role_to_user(
            user_id=user_id,
            role_id=assignment.role_id,
            assigned_by_id=current_user.id,
            reason=assignment.reason
        )
        return {"message": "Role assigned successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/users/{user_id}/role")
def remove_role_from_user(
    user_id: str,
    removal: RemoveRoleFromUser,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove role from a user

    Requires: admin.users.manage_roles permission
    """
    permission_service = PermissionService(db)

    try:
        permission_service.remove_role_from_user(
            user_id=user_id,
            removed_by_id=current_user.id,
            reason=removal.reason
        )
        return {"message": "Role removed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Permission Check Endpoints ====================

@router.post("/users/{user_id}/check-permission", response_model=PermissionCheckResponse)
def check_user_permission(
    user_id: str,
    check: PermissionCheck,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if a user has a specific permission"""
    permission_service = PermissionService(db)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    has_permission = permission_service.user_has_permission(
        user_id=user_id,
        module=check.module,
        action=check.action,
        resource=check.resource
    )

    return PermissionCheckResponse(
        has_permission=has_permission,
        module=check.module,
        action=check.action,
        resource=check.resource,
        user_id=user_id,
        username=user.username
    )


@router.get("/users/{user_id}/permissions/summary", response_model=UserPermissionSummary)
def get_user_permissions_summary(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get complete permissions summary for a user"""
    permission_service = PermissionService(db)

    try:
        summary = permission_service.get_user_permissions_summary(user_id)
        return UserPermissionSummary(**summary)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== Bulk Operations ====================

@router.post("/bulk/assign-permissions")
def bulk_assign_permissions(
    assignment: BulkPermissionAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Assign a permission to multiple users at once

    Requires: admin.users.bulk_operations permission
    """
    permission_service = PermissionService(db)
    results = {"success": [], "failed": []}

    for user_id in assignment.user_ids:
        try:
            permission_service.assign_permission_to_user(
                user_id=user_id,
                permission_id=assignment.permission_id,
                assigned_by_id=current_user.id,
                reason=assignment.reason,
                expires_at=assignment.expires_at
            )
            results["success"].append(user_id)
        except Exception as e:
            results["failed"].append({"user_id": user_id, "error": str(e)})

    return results


@router.post("/bulk/assign-roles")
def bulk_assign_roles(
    assignment: BulkRoleAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Assign a role to multiple users at once

    Requires: admin.users.bulk_operations permission
    """
    permission_service = PermissionService(db)
    results = {"success": [], "failed": []}

    for user_id in assignment.user_ids:
        try:
            permission_service.assign_role_to_user(
                user_id=user_id,
                role_id=assignment.role_id,
                assigned_by_id=current_user.id,
                reason=assignment.reason
            )
            results["success"].append(user_id)
        except Exception as e:
            results["failed"].append({"user_id": user_id, "error": str(e)})

    return results
