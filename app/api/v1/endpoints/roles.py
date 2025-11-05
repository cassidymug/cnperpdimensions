from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
import json
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)
import datetime

from app.core.database import get_db
# from app.core.security import get_current_user  # Removed for development
from app.models.role import Role, Permission, RolePermission, UserAuditLog, UserPermission
from app.models.user import User
from app.schemas.role import (
    RoleCreate, RoleUpdate, RoleResponse,
    PermissionCreate, PermissionUpdate, PermissionResponse,
    RolePermissionCreate, RolePermissionResponse,
    UserAuditLogCreate, UserAuditLogResponse,
    PrivilegeChart, RolePrivilegeAssignment,
    PermissionMatrixResponse, PermissionMatrixCell, PermissionMatrixUpdate,
    UserPermissionResponse, ExtendedPermissionMatrixResponse, PermissionMatrixUser, RoleFromMatrixCreate
)

router = APIRouter()


def log_user_action(
    db: Session,
    user: User,
    action: str,
    module: str,
    resource_type: str,
    resource_id: str = None,
    details: dict = None,
    request: Request = None
):
    """Log user action for audit purposes"""
    if not user:  # Skip logging if no user (development mode)
        return

    audit_log = UserAuditLog(
        user_id=user.id,
        action=action,
        module=module,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=request.client.host if request else None,
        user_agent=request.headers.get("user-agent") if request else None
    )
    db.add(audit_log)
    db.commit()


# Permission endpoints
@router.get("/permissions/", response_model=List[PermissionResponse])
async def get_permissions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    # current_user parameter removed for development)
):
    """Get all permissions"""
    permissions = db.query(Permission).offset(skip).limit(limit).all()
    return permissions


@router.get("/permissions/matrix", response_model=PermissionMatrixResponse)
async def get_permission_matrix(
    db: Session = Depends(get_db),
    # current_user parameter removed for development)
):
    """Return a matrix of permissions grouped by module/action with role assignments."""
    roles = db.query(Role).filter(Role.is_active == True).all()
    permissions = db.query(Permission).all()
    # Build cell map
    cell_map: dict[tuple[str,str,str], PermissionMatrixCell] = {}
    for perm in permissions:
        key = (perm.module, perm.action, perm.resource)
        if key not in cell_map:
            cell_map[key] = PermissionMatrixCell(module=perm.module, action=perm.action, resource=perm.resource, permission_id=perm.id, role_ids=[])
    # Populate role_ids
    role_permissions = db.query(RolePermission).all()
    for rp in role_permissions:
        perm = rp.permission
        key = (perm.module, perm.action, perm.resource)
        if key in cell_map:
            if rp.role_id not in cell_map[key].role_ids:
                cell_map[key].role_ids.append(rp.role_id)
    cells = list(cell_map.values())
    # Build RoleResponse objects manually to satisfy schema (role.permissions expects Permission objects, not RolePermission rows)
    role_responses = []
    for r in roles:
        perm_objs = [rp.permission for rp in r.permissions if getattr(rp, 'permission', None)]
        role_responses.append(RoleResponse(
            id=r.id,
            name=r.name,
            description=r.description,
            is_system_role=r.is_system_role,
            is_active=r.is_active,
            permissions=perm_objs,
            created_at=r.created_at,
            updated_at=r.updated_at
        ))
    return PermissionMatrixResponse(roles=role_responses, cells=cells)


@router.get("/permissions/matrix/extended", response_model=ExtendedPermissionMatrixResponse)
async def get_permission_matrix_extended(
    db: Session = Depends(get_db),
    # current_user parameter removed for development)
):
    """Extended matrix including users and their effective permissions."""
    base = await get_permission_matrix(db)  # reuse logic (no current_user needed)
    users = db.query(User).all()
    # Preload direct grants
    from app.models.role import UserPermission, RolePermission
    # Map role -> permission ids
    role_perm_map: dict[str,set[str]] = {}
    for rp in db.query(RolePermission).all():
        role_perm_map.setdefault(rp.role_id,set()).add(rp.permission_id)
    user_entries: list[PermissionMatrixUser] = []
    user_direct_map: dict[str,set[str]] = {}
    for up in db.query(UserPermission).all():
        user_direct_map.setdefault(up.user_id,set()).add(up.permission_id)
    for u in users:
        role_ids = role_perm_map.get(u.role_id, set()) if u.role_id else set()
        direct_ids = user_direct_map.get(u.id, set())
        effective = sorted(role_ids | direct_ids)
        user_entries.append(PermissionMatrixUser(
            id=u.id,
            username=u.username,
            role_id=u.role_id,
            direct_permission_ids=sorted(direct_ids),
            effective_permission_ids=effective
        ))
    return ExtendedPermissionMatrixResponse(roles=base.roles, cells=base.cells, users=user_entries)


@router.post("/permissions/matrix/roles")
async def create_role_from_matrix(
    payload: RoleFromMatrixCreate,
    db: Session = Depends(get_db),
    # current_user parameter removed for development),
    request: Request = None
):
    """Create a new role and assign permissions based on provided permission cells (module/action/resource)."""
    # Ensure permissions exist (reuse update logic pattern)
    existing_perms = db.query(Permission).all()
    perm_index = {(p.module,p.action,p.resource): p for p in existing_perms}
    permission_ids: set[str] = set()
    for cell in payload.permission_cells:
        key = (cell.module, cell.action, cell.resource or 'all')
        if key not in perm_index:
            name = f"{cell.module}.{cell.action}.{cell.resource}" if cell.resource != 'all' else f"{cell.module}.{cell.action}"
            new_perm = Permission(
                name=name,
                description=f"Auto-created via matrix for {cell.module}:{cell.action}:{cell.resource}",
                module=cell.module,
                action=cell.action,
                resource=cell.resource or 'all'
            )
            db.add(new_perm)
            db.flush()
            perm_index[key] = new_perm
        permission_ids.add(perm_index[key].id)
    # Create role
    if db.query(Role).filter(Role.name==payload.name).first():
        raise HTTPException(status_code=400, detail="Role name already exists")
    role = Role(name=payload.name, description=payload.description, is_system_role=False, is_active=True)
    db.add(role)
    db.flush()
    for pid in permission_ids:
        db.add(RolePermission(role_id=role.id, permission_id=pid))
    db.commit()
    log_user_action(db, None, "create_role_from_matrix", "permissions", "role", resource_id=role.id, details={"permission_count": len(permission_ids)}, request=request)
    return {"message":"Role created","role_id": role.id, "permission_count": len(permission_ids)}


@router.post("/permissions/matrix")
async def update_permission_matrix(
    update: PermissionMatrixUpdate,
    db: Session = Depends(get_db),
    # current_user parameter removed for development),
    request: Request = None,
    batch_window_seconds: int = 120
):
    """Apply a submitted permission matrix: ensures permissions exist then syncs role assignments.
    Strategy:
      1. Ensure each (module,action,resource) cell has a permission (create if missing).
      2. For each role aggregate desired permission ids; diff with current; add/remove.
    """
    # Load active roles
    roles = {r.id: r for r in db.query(Role).filter(Role.is_active == True).all()}
    existing_perms = db.query(Permission).all()
    perm_index: dict[tuple[str,str,str], Permission] = {(p.module,p.action,p.resource): p for p in existing_perms}
    desired_cells: list[PermissionMatrixCell] = update.cells
    created = 0
    for cell in desired_cells:
        key = (cell.module, cell.action, cell.resource or 'all')
        if key not in perm_index:
            # Create new permission (name convention module.action.resource)
            name = f"{cell.module}.{cell.action}.{cell.resource}" if cell.resource != 'all' else f"{cell.module}.{cell.action}"
            new_perm = Permission(
                name=name,
                description=f"Auto-created for {cell.module}:{cell.action}:{cell.resource}",
                module=cell.module,
                action=cell.action,
                resource=cell.resource or 'all'
            )
            db.add(new_perm)
            db.flush()
            perm_index[key] = new_perm
            created += 1
        cell.permission_id = perm_index[key].id
    db.commit()
    # Build desired mapping role -> set(permission_ids)
    role_desired: dict[str,set[str]] = {rid:set() for rid in roles.keys()}
    for cell in desired_cells:
        for rid in cell.role_ids:
            if rid in role_desired:
                role_desired[rid].add(cell.permission_id)
    # Current assignments
    role_perm_records = db.query(RolePermission).all()
    current_map: dict[str,set[str]] = {}
    for rp in role_perm_records:
        current_map.setdefault(rp.role_id,set()).add(rp.permission_id)
    # Apply diffs
    added = 0
    removed = 0
    for rid, desired_set in role_desired.items():
        current_set = current_map.get(rid,set())
        to_add = desired_set - current_set
        to_remove = current_set - desired_set
        for pid in to_add:
            db.add(RolePermission(role_id=rid, permission_id=pid))
            added += 1
        if to_remove:
            db.query(RolePermission).filter(RolePermission.role_id==rid, RolePermission.permission_id.in_(list(to_remove))).delete(synchronize_session=False)
            removed += len(to_remove)
    db.commit()
    # Audit log batching: if a recent update_matrix log exists within batch window, aggregate instead of separate row
    try:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(seconds=batch_window_seconds)
        recent = db.query(UserAuditLog).filter(
            UserAuditLog.user_id=='default-user-id',
            UserAuditLog.action=="update_matrix",
            UserAuditLog.module=="permissions",
            UserAuditLog.resource_type=="matrix",
            UserAuditLog.created_at >= cutoff
        ).order_by(UserAuditLog.created_at.desc()).first()
        if recent and isinstance(recent.details, dict):
            # Increment cumulative counters
            recent.details["created_permissions"] = recent.details.get("created_permissions",0) + created
            recent.details["added"] = recent.details.get("added",0) + added
            recent.details["removed"] = recent.details.get("removed",0) + removed
            recent.details["batched"] = True
            db.add(recent)
            db.commit()
        else:
            log_user_action(db, None, "update_matrix", "permissions", "matrix", details={"created_permissions":created,"added":added,"removed":removed,"batched":False}, request=request)
    except Exception:
        # Fallback to single log if anything unexpected
        log_user_action(db, None, "update_matrix", "permissions", "matrix", details={"created_permissions":created,"added":added,"removed":removed,"batched":"error-fallback"}, request=request)
    return {"message":"Permission matrix updated","created_permissions":created,"grants_added":added,"grants_removed":removed,"batched": True if (locals().get('recent') and getattr(locals().get('recent'),'details',{}).get('batched')) else False}


# ------------------ User-specific Permission Overrides ------------------
@router.get("/users/{user_id}/permissions", response_model=list[PermissionResponse])
async def get_user_effective_permissions(
    user_id: str,
    db: Session = Depends(get_db),
    # current_user parameter removed for development)
):
    """Return effective permissions for a user (role-based + direct grants)."""
    user = db.query(User).filter(User.id==user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Role permissions
    role_perm_ids = set()
    if user.role_id:
        role_perm_ids = {rp.permission_id for rp in db.query(RolePermission).filter(RolePermission.role_id==user.role_id).all()}
    # Direct grants
    direct_perm_ids = {up.permission_id for up in db.query(UserPermission).filter(UserPermission.user_id==user.id)}
    all_ids = role_perm_ids | direct_perm_ids
    if not all_ids:
        return []
    perms = db.query(Permission).filter(Permission.id.in_(list(all_ids))).all()
    return perms


@router.get("/users/{user_id}/permissions/raw", response_model=dict)
async def get_user_permission_details(
    user_id: str,
    db: Session = Depends(get_db),
    # current_user parameter removed for development)
):
    """Return separated role vs direct permissions for UI diff presentation."""
    user = db.query(User).filter(User.id==user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    role_perm_ids = set()
    if user.role_id:
        role_perm_ids = {rp.permission_id for rp in db.query(RolePermission).filter(RolePermission.role_id==user.role_id).all()}
    direct = list(db.query(UserPermission).filter(UserPermission.user_id==user.id).all())
    return {
        "role_permission_ids": list(role_perm_ids),
        "direct_permissions": [d.permission_id for d in direct]
    }


@router.post("/users/{user_id}/permissions")
async def set_user_direct_permissions(
    user_id: str,
    permission_ids: list[str],
    db: Session = Depends(get_db),
    # current_user parameter removed for development),
    request: Request = None
):
    """Replace the set of direct (override) permissions for a user.
    Does not alter role membership. Only manages rows in user_permissions.
    """
    user = db.query(User).filter(User.id==user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Validate permission ids
    if permission_ids:
        count = db.query(Permission).filter(Permission.id.in_(permission_ids)).count()
        if count != len(set(permission_ids)):
            raise HTTPException(status_code=400, detail="One or more permission IDs invalid")
    # Current direct
    db.query(UserPermission).filter(UserPermission.user_id==user.id).delete(synchronize_session=False)
    for pid in set(permission_ids):
        db.add(UserPermission(user_id=user.id, permission_id=pid))
    db.commit()
    log_user_action(db, None, "update_user_direct_perms", "permissions", "user", resource_id=user.id, details={"direct_permission_count": len(permission_ids)}, request=request)
    return {"message":"User direct permissions updated","direct_permission_count": len(permission_ids)}


@router.post("/permissions/", response_model=PermissionResponse)
async def create_permission(
    permission: PermissionCreate,
    db: Session = Depends(get_db),
    # current_user parameter removed for development),
    request: Request = None
):
    """Create a new permission"""
    # Check if permission already exists
    existing = db.query(Permission).filter(Permission.name == permission.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Permission already exists")

    new_permission = Permission(**permission.dict())
    db.add(new_permission)
    db.commit()
    db.refresh(new_permission)

    # Log the action (skipped in development mode)
    log_user_action(
        db, None, "create", "permissions", "permission",
        new_permission.id, {"permission_name": permission.name}, request
    )

    return new_permission
# Role endpoints
@router.get("/", response_model=List[RoleResponse])
async def get_roles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    # current_user parameter removed for development)
):
    """Get all roles"""
    roles = db.query(Role).offset(skip).limit(limit).all()

    # Transform to response format with proper permission objects
    role_responses = []
    for role in roles:
        perm_objs = [rp.permission for rp in role.permissions if rp.permission]
        role_responses.append(RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            is_system_role=role.is_system_role,
            is_active=role.is_active,
            permissions=perm_objs,
            created_at=role.created_at,
            updated_at=role.updated_at
        ))

    return role_responses


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    db: Session = Depends(get_db),
    # current_user parameter removed for development)
):
    """Get a specific role"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Transform to response format with proper permission objects
    perm_objs = [rp.permission for rp in role.permissions if rp.permission]
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_system_role=role.is_system_role,
        is_active=role.is_active,
        permissions=perm_objs,
        created_at=role.created_at,
        updated_at=role.updated_at
    )


@router.post("/", response_model=RoleResponse)
async def create_role(
    role: RoleCreate,
    db: Session = Depends(get_db),
    # current_user parameter removed for development),
    request: Request = None
):
    """Create a new role"""
    # Check if role already exists
    existing = db.query(Role).filter(Role.name == role.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Role already exists")

    # Create role
    role_data = role.dict(exclude={'permissions'})
    new_role = Role(**role_data)
    db.add(new_role)
    db.commit()
    db.refresh(new_role)

    # Assign permissions if provided
    if role.permissions:
        for permission_id in role.permissions:
            role_permission = RolePermission(
                role_id=new_role.id,
                permission_id=permission_id
            )
            db.add(role_permission)
        db.commit()

    # Log the action (skipped in development mode)
    log_user_action(
        db, None, "create", "roles", "role",
        new_role.id, {"role_name": role.name, "permissions_count": len(role.permissions)}, request
    )

    return new_role
@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    role_update: RoleUpdate,
    db: Session = Depends(get_db),
    # current_user parameter removed for development),
    request: Request = None
):
    """Update a role"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.is_system_role:
        raise HTTPException(status_code=400, detail="Cannot modify system roles")

    # Update role fields
    update_data = role_update.dict(exclude_unset=True, exclude={'permissions'})
    for field, value in update_data.items():
        setattr(role, field, value)

    # Update permissions if provided
    if role_update.permissions is not None:
        # Remove existing permissions
        db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()

        # Add new permissions
        for permission_id in role_update.permissions:
            role_permission = RolePermission(
                role_id=role_id,
                permission_id=permission_id
            )
            db.add(role_permission)

    db.commit()
    db.refresh(role)

    # Log the action
    log_user_action(
        db, None, "update", "roles", "role",
        role_id, {"role_name": role.name}, request
    )

    return role
@router.delete("/{role_id}")
async def delete_role(
    role_id: str,
    db: Session = Depends(get_db),
    # current_user parameter removed for development),
    request: Request = None
):
    """Delete a role"""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.is_system_role:
        raise HTTPException(status_code=400, detail="Cannot delete system roles")

    # Check if any users are using this role
    users_with_role = db.query(User).filter(User.role_id == role_id).count()
    if users_with_role > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete role: {users_with_role} users are assigned to this role")

    # Delete role permissions
    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()

    # Delete role
    db.delete(role)
    db.commit()

    # Log the action
    log_user_action(
        db, None, "delete", "roles", "role",
        role_id, {"role_name": role.name}, request
    )

    return {"message": "Role deleted successfully"}
# Privilege chart endpoints
@router.get("/privilege-chart/", response_model=List[PrivilegeChart])
async def get_privilege_chart(
    db: Session = Depends(get_db),
    # current_user parameter removed for development)
):
    """Get privilege chart for all roles"""
    roles = db.query(Role).filter(Role.is_active == True).all()
    privilege_charts = []

    for role in roles:
        permissions = []
        for role_perm in role.permissions:
            permissions.append({
                "id": role_perm.permission.id,
                "name": role_perm.permission.name,
                "module": role_perm.permission.module,
                "action": role_perm.permission.action,
                "resource": role_perm.permission.resource
            })

        # Determine module access and branch access based on permissions
        modules = list(set([p["module"] for p in permissions]))
        branch_access = "all" if any(p["resource"] == "all" for p in permissions) else "own"

        privilege_chart = PrivilegeChart(
            role_name=role.name,
            description=role.description or "",
            permissions=permissions,
            module_access=modules,
            branch_access=branch_access,
            audit_level="full" if role.name.lower() in ["accountant", "super_admin", "admin"] else "basic"
        )
        privilege_charts.append(privilege_chart)

    return privilege_charts


@router.post("/assign-privileges/")
async def assign_privileges(
    assignment: RolePrivilegeAssignment,
    db: Session = Depends(get_db),
    # current_user parameter removed for development),
    request: Request = None
):
    """Assign privileges to a role"""
    # If there was an intended bootstrap bypass for a special setup role, handle it here.
    # For now we always require an authenticated admin/super_admin user.
    role = db.query(Role).filter(Role.id == assignment.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.is_system_role:
        raise HTTPException(status_code=400, detail="Cannot modify system roles")

    # Remove existing permissions
    db.query(RolePermission).filter(RolePermission.role_id == assignment.role_id).delete()

    # Add new permissions
    for permission_id in assignment.permission_ids:
        role_permission = RolePermission(
            role_id=assignment.role_id,
            permission_id=permission_id
        )
        db.add(role_permission)

    db.commit()

    # Log the action (skipped in development mode)
    log_user_action(
        db, None, "assign_privileges", "roles", "role",
        assignment.role_id, {
            "permissions_count": len(assignment.permission_ids),
            "module_access": assignment.module_access,
            "branch_access": assignment.branch_access,
            "audit_level": assignment.audit_level
        }, request
    )

    return {"message": "Privileges assigned successfully"}
# Audit log endpoints
@router.get("/audit-logs/", response_model=List[UserAuditLogResponse])
async def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: str = None,
    module: str = None,
    action: str = None,
    db: Session = Depends(get_db),
    # current_user parameter removed for development)
):
    """Get audit logs with optional filtering"""
    query = db.query(UserAuditLog)

    if user_id:
        query = query.filter(UserAuditLog.user_id == user_id)
    if module:
        query = query.filter(UserAuditLog.module == module)
    if action:
        query = query.filter(UserAuditLog.action == action)

    audit_logs = query.order_by(UserAuditLog.created_at.desc()).offset(skip).limit(limit).all()
    return audit_logs


@router.get("/audit-logs/{log_id}", response_model=UserAuditLogResponse)
async def get_audit_log(
    log_id: str,
    db: Session = Depends(get_db),
    # current_user parameter removed for development)
):
    """Get a specific audit log"""
    audit_log = db.query(UserAuditLog).filter(UserAuditLog.id == log_id).first()
    if not audit_log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return audit_log
