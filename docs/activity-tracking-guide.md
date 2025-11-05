# Activity Tracking & Permission Management System

## Complete Guide for Developers and Administrators

---

## Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Architecture](#architecture)
4. [Database Models](#database-models)
5. [Services](#services)
6. [API Endpoints](#api-endpoints)
7. [Frontend Components](#frontend-components)
8. [Usage Examples](#usage-examples)
9. [Security Considerations](#security-considerations)
10. [Best Practices](#best-practices)

---

## Overview

The Activity Tracking & Permission Management System provides comprehensive functionality for:
- **Activity Logging**: Track all user actions across the entire application
- **Approval Tracking**: Monitor and record approval workflows
- **Permission Management**: Fine-grained role and permission control
- **Audit Trail**: Complete history of permission changes
- **User Session Tracking**: Monitor active sessions and user activity

### Who Created What?

Every action in the system is tracked with:
- **Who**: User who performed the action
- **What**: Specific action taken
- **When**: Timestamp of the action
- **Where**: Branch/module context
- **Why**: Reason (for permission changes)
- **How**: Success/failure status

---

## Key Features

### 1. **Comprehensive Activity Logging**
- Track CRUD operations (Create, Read, Update, Delete)
- Monitor workflow actions (Submit, Approve, Reject, Reassign)
- Record authentication events (Login, Logout, Failed attempts)
- Log system operations (Export, Import, Print, Email)

### 2. **Approval Workflow Tracking**
- Complete approval history for all entities
- Track approval levels and delegation
- Record comments and attachments
- Monitor approval state transitions

### 3. **Permission Management**
- Create and manage roles
- Define granular permissions (module.action.resource)
- Assign permissions to roles
- Grant user-specific permissions (with expiration)
- Bulk operations for efficiency

### 4. **Audit Trail**
- Track all permission changes
- Record role assignments
- Monitor permission grants/revocations
- Include approval context for changes

### 5. **Session Management**
- Track active user sessions
- Monitor last activity time
- Record login methods and IP addresses
- Support session termination

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────┐
│                   Frontend Layer                     │
│  - Activity Timeline UI                              │
│  - Permission Matrix                                 │
│  - Role Management Interface                         │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│                   API Layer                          │
│  - Activity Endpoints                                │
│  - Permission Endpoints                              │
│  - Role Management Endpoints                         │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│                 Service Layer                        │
│  - ActivityService                                   │
│  - PermissionService                                 │
└────────────────┬────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────┐
│                Database Models                       │
│  - ActivityLog                                       │
│  - ApprovalLog                                       │
│  - PermissionChangeLog                               │
│  - UserSession                                       │
│  - EntityAccessLog                                   │
│  - Role, Permission, RolePermission, UserPermission  │
└─────────────────────────────────────────────────────┘
```

---

## Database Models

### 1. ActivityLog

Tracks all user activities in the application.

**Fields:**
```python
- user_id: Who performed the action
- username: Denormalized for performance
- role_name: User's role at time of action
- activity_type: Type of activity (enum)
- module: Application module (enum)
- action: Specific action taken
- description: Human-readable description
- entity_type: Type of affected entity
- entity_id: ID of affected entity
- entity_name: Display name of entity
- branch_id: Branch context
- old_values: State before change (JSON)
- new_values: State after change (JSON)
- metadata: Additional context (JSON)
- success: Whether action succeeded
- error_message: Error details if failed
- severity: Severity level (info/warning/error/critical)
- ip_address: User's IP address
- user_agent: User's browser/client
- session_id: Session identifier
- performed_at: Timestamp
```

**Indexes:**
- `idx_activity_user_module`: Fast queries by user and module
- `idx_activity_entity`: Fast entity lookups
- `idx_activity_branch_date`: Branch-filtered reports
- `idx_activity_type_date`: Type-filtered reports

### 2. ApprovalLog

Detailed tracking of approval workflows.

**Fields:**
```python
- approver_id: Who approved/rejected
- approver_name: Approver username
- approver_role: Approver's role
- entity_type: Type of entity approved
- entity_id: ID of approved entity
- entity_reference: Human-readable reference
- workflow_id: Associated workflow instance
- from_state: Previous state
- to_state: New state
- action: Action taken
- decision: Final decision
- comments: Approver's comments
- attachments: List of file references (JSON)
- on_behalf_of: If delegated
- delegation_reason: Why delegated
- approval_level: Approval level (L1/L2/L3)
- branch_id: Branch context
- approved_at: Timestamp
```

### 3. PermissionChangeLog

Tracks all permission and role changes.

**Fields:**
```python
- changed_by_id: Who made the change
- changed_by_name: Changer's username
- target_user_id: Affected user
- target_user_name: Target username
- target_role_id: Affected role
- target_role_name: Role name
- change_type: Type of change
- permission_id: Permission affected
- permission_name: Permission name
- old_value: Previous state (JSON)
- new_value: New state (JSON)
- reason: Reason for change
- approved_by_id: Who approved the change
- approval_date: When approved
- expires_at: For temporary permissions
- changed_at: Timestamp
```

### 4. UserSession

Track user sessions for security and correlation.

**Fields:**
```python
- user_id: Session owner
- username: User's username
- session_token: Session identifier
- session_start: Login timestamp
- session_end: Logout timestamp
- is_active: Session status
- ip_address: Login IP
- user_agent: Browser/client info
- login_method: How user logged in
- last_activity: Last action timestamp
- activity_count: Number of actions
- logout_reason: Why session ended
```

### 5. EntityAccessLog

Track access to sensitive entities.

**Fields:**
```python
- user_id: Who accessed
- username: User's username
- entity_type: Type of entity
- entity_id: Entity identifier
- entity_name: Display name
- access_method: How accessed (view/export/print)
- module: Application module
- accessed_at: Timestamp
```

---

## Services

### ActivityService

Handles activity logging and querying.

**Key Methods:**

```python
# Logging
log_activity(user_id, activity_type, module, action, ...)
log_activity_from_request(request, user_id, activity_type, ...)
log_approval(approver_id, entity_type, entity_id, action, ...)
log_permission_change(changed_by_id, change_type, ...)
log_entity_access(user_id, entity_type, entity_id, ...)

# Querying
get_user_activities(user_id, filters...)
get_entity_activities(entity_type, entity_id)
get_approval_history(filters...)
get_permission_changes(filters...)
get_module_activities(module, filters...)
get_activity_statistics(filters...)
```

**Usage Example:**

```python
from app.services.activity_service import ActivityService
from app.models.activity_log import ActivityType, ActivityModule

service = ActivityService(db)

# Log a purchase order creation
service.log_activity(
    user_id=current_user.id,
    activity_type=ActivityType.CREATE,
    module=ActivityModule.PURCHASES,
    action="Create Purchase Order",
    description=f"Created PO-{po_number} for ${total_amount}",
    entity_type="PurchaseOrder",
    entity_id=po.id,
    entity_name=f"PO-{po_number}",
    branch_id=current_user.branch_id,
    new_values={
        "supplier": supplier_name,
        "amount": total_amount,
        "items": item_count
    },
    success=True
)
```

### PermissionService

Manages roles, permissions, and access control.

**Key Methods:**

```python
# Role Management
create_role(name, description, is_system_role)
update_role(role_id, fields...)
delete_role(role_id)
get_all_roles(include_inactive)
get_role_by_id(role_id)

# Permission Management
create_permission(name, module, action, resource)
get_all_permissions()
get_permissions_by_module(module)

# Role-Permission Assignment
assign_permission_to_role(role_id, permission_id)
revoke_permission_from_role(role_id, permission_id)
get_role_permissions(role_id)

# User-Permission Assignment
assign_permission_to_user(user_id, permission_id, expires_at)
revoke_permission_from_user(user_id, permission_id)
get_user_permissions(user_id)

# User-Role Assignment
assign_role_to_user(user_id, role_id)
remove_role_from_user(user_id)

# Permission Checking
user_has_permission(user_id, module, action, resource)
check_permission(user_id, module, action, resource)  # Raises error
get_user_permissions_summary(user_id)
```

**Usage Example:**

```python
from app.services.permission_service import PermissionService

service = PermissionService(db)

# Create a new role
role = service.create_role(
    name="Branch Manager",
    description="Manages branch operations",
    is_system_role=False,
    created_by_id=admin_user.id,
    reason="New organizational structure"
)

# Assign permissions to role
service.assign_permission_to_role(
    role_id=role.id,
    permission_id=sales_create_permission.id,
    assigned_by_id=admin_user.id,
    reason="Branch managers can create sales"
)

# Assign role to user
service.assign_role_to_user(
    user_id=new_manager.id,
    role_id=role.id,
    assigned_by_id=admin_user.id,
    reason="Promoted to branch manager"
)

# Check if user has permission
has_perm = service.user_has_permission(
    user_id=user.id,
    module="sales",
    action="create",
    resource="all"
)
```

---

## API Endpoints

### Activity Logs

```http
GET /api/v1/activity/logs
    Query params: user_id, module, activity_type, entity_type,
                  entity_id, branch_id, start_date, end_date, limit, offset
    Returns: List of activity logs

GET /api/v1/activity/logs/entity/{entity_type}/{entity_id}
    Query params: include_access_logs
    Returns: Complete activity history for entity

GET /api/v1/activity/logs/module/{module}
    Query params: branch_id, start_date, end_date, limit
    Returns: Activities for specific module

GET /api/v1/activity/statistics
    Query params: start_date, end_date, user_id, module
    Returns: Activity statistics
```

### Approvals

```http
GET /api/v1/activity/approvals
    Query params: approver_id, entity_type, start_date, end_date, limit
    Returns: Approval history

GET /api/v1/activity/approvals/entity/{entity_type}/{entity_id}
    Returns: All approvals for specific entity
```

### Roles

```http
POST /api/v1/activity/roles
    Body: { name, description, is_system_role, reason }
    Returns: Created role

GET /api/v1/activity/roles
    Query params: include_inactive
    Returns: List of all roles

GET /api/v1/activity/roles/{role_id}
    Returns: Role with permissions

PATCH /api/v1/activity/roles/{role_id}
    Body: { name?, description?, is_active?, reason? }
    Returns: Updated role

DELETE /api/v1/activity/roles/{role_id}
    Query params: reason
    Returns: 204 No Content
```

### Permissions

```http
POST /api/v1/activity/permissions
    Body: { name, module, action, resource, description }
    Returns: Created permission

GET /api/v1/activity/permissions
    Returns: List of all permissions

GET /api/v1/activity/permissions/module/{module}
    Returns: Permissions for specific module
```

### Role-Permission Assignment

```http
POST /api/v1/activity/roles/{role_id}/permissions
    Body: { permission_id, reason }
    Returns: Success message

DELETE /api/v1/activity/roles/{role_id}/permissions/{permission_id}
    Query params: reason
    Returns: Success message
```

### User-Permission Assignment

```http
POST /api/v1/activity/users/{user_id}/permissions
    Body: { permission_id, reason, expires_at? }
    Returns: Success message

DELETE /api/v1/activity/users/{user_id}/permissions/{permission_id}
    Query params: reason
    Returns: Success message
```

### User-Role Assignment

```http
POST /api/v1/activity/users/{user_id}/role
    Body: { role_id, reason }
    Returns: Success message

DELETE /api/v1/activity/users/{user_id}/role
    Body: { reason }
    Returns: Success message
```

### Permission Checking

```http
POST /api/v1/activity/users/{user_id}/check-permission
    Body: { module, action, resource }
    Returns: { has_permission, module, action, resource, user_id, username }

GET /api/v1/activity/users/{user_id}/permissions/summary
    Returns: Complete permissions summary
```

### Bulk Operations

```http
POST /api/v1/activity/bulk/assign-permissions
    Body: { user_ids[], permission_id, reason, expires_at? }
    Returns: { success[], failed[] }

POST /api/v1/activity/bulk/assign-roles
    Body: { user_ids[], role_id, reason }
    Returns: { success[], failed[] }
```

---

## Frontend Components

### 1. Activity Timeline

Displays activity logs in a visual timeline.

**Features:**
- Chronological display
- Color-coded by activity type
- Shows who, what, when, where
- Expandable change details
- Success/failure indicators

**Usage:**
```javascript
const timeline = new ActivityTimeline('activityTimeline');
timeline.loadActivities({
    user_id: currentUserId,
    limit: 50
});
```

### 2. Permission Matrix

Interactive table for managing permissions.

**Features:**
- Grid view of module/action permissions
- Checkbox toggles for quick assignment
- Role-based or user-based views
- Real-time updates

### 3. Role Cards

Display role information with stats.

**Features:**
- Role name and description
- System role indicator
- Active/inactive status
- User count and permission count
- Quick actions

### 4. User Permission Summary

Comprehensive view of user permissions.

**Features:**
- User info with avatar
- Role permissions section
- User-specific permissions section
- Temporary permission indicators
- Edit capabilities

---

## Usage Examples

### Example 1: Log a Sales Invoice Creation

```python
from app.services.activity_service import ActivityService
from app.models.activity_log import ActivityType, ActivityModule

def create_invoice(db, current_user, invoice_data):
    # Create the invoice
    invoice = Invoice(**invoice_data)
    db.add(invoice)
    db.commit()

    # Log the activity
    activity_service = ActivityService(db)
    activity_service.log_activity(
        user_id=current_user.id,
        activity_type=ActivityType.CREATE,
        module=ActivityModule.SALES,
        action="Create Invoice",
        description=f"Created invoice {invoice.invoice_number} for customer {invoice.customer.name}",
        entity_type="Invoice",
        entity_id=invoice.id,
        entity_name=invoice.invoice_number,
        branch_id=current_user.branch_id,
        new_values={
            "invoice_number": invoice.invoice_number,
            "customer": invoice.customer.name,
            "total_amount": invoice.total_amount,
            "status": invoice.status
        },
        success=True
    )

    return invoice
```

### Example 2: Log an Approval

```python
def approve_purchase_order(db, current_user, po_id, comments):
    # Get PO
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()

    # Update status
    old_status = po.status
    po.status = "approved"
    po.approved_by = current_user.id
    po.approved_at = datetime.utcnow()
    db.commit()

    # Log the approval
    activity_service = ActivityService(db)
    activity_service.log_approval(
        approver_id=current_user.id,
        entity_type="PurchaseOrder",
        entity_id=po.id,
        action="approve",
        decision="approved",
        entity_reference=po.po_number,
        from_state=old_status,
        to_state="approved",
        comments=comments,
        approval_level="L2",
        branch_id=current_user.branch_id
    )

    return po
```

### Example 3: Assign Role to User

```python
def promote_user_to_manager(db, admin_user, user_id, manager_role_id):
    permission_service = PermissionService(db)

    # Assign role
    user = permission_service.assign_role_to_user(
        user_id=user_id,
        role_id=manager_role_id,
        assigned_by_id=admin_user.id,
        reason="Promoted to branch manager position"
    )

    # Grant temporary special permission
    permission_service.assign_permission_to_user(
        user_id=user_id,
        permission_id=system_config_permission.id,
        assigned_by_id=admin_user.id,
        reason="Temporary access for system configuration project",
        expires_at=datetime.utcnow() + timedelta(days=30)
    )

    return user
```

### Example 4: Check Permission Before Action

```python
def delete_invoice(db, current_user, invoice_id):
    permission_service = PermissionService(db)

    # Check if user has permission
    try:
        permission_service.check_permission(
            user_id=current_user.id,
            module="sales",
            action="delete",
            resource="all"
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    # Proceed with deletion
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    db.delete(invoice)
    db.commit()

    # Log the activity
    activity_service = ActivityService(db)
    activity_service.log_activity(
        user_id=current_user.id,
        activity_type=ActivityType.DELETE,
        module=ActivityModule.SALES,
        action="Delete Invoice",
        entity_type="Invoice",
        entity_id=invoice_id,
        old_values={"invoice_number": invoice.invoice_number},
        success=True
    )
```

---

## Security Considerations

### 1. Permission Checking

Always check permissions before sensitive operations:

```python
# Good
permission_service.check_permission(user_id, "sales", "delete", "all")
do_sensitive_operation()

# Bad
do_sensitive_operation()  # No permission check!
```

### 2. Activity Logging

Log all important activities, especially:
- Permission changes
- Role assignments
- Access to sensitive data
- Failed login attempts
- Deletion operations

### 3. Session Management

- Implement session timeout
- Track concurrent sessions
- Force logout on permission changes
- Monitor suspicious activity patterns

### 4. Audit Trail Integrity

- Never allow deletion of activity logs
- Store activity logs in separate schema/database for extra security
- Implement log archiving strategy
- Regular audit trail reviews

---

## Best Practices

### 1. Activity Logging

**DO:**
- Log immediately after action
- Include meaningful descriptions
- Track both old and new values
- Categorize by severity
- Include entity references

**DON'T:**
- Log sensitive data (passwords, tokens)
- Log excessively (every read operation)
- Skip error logging
- Use generic descriptions

### 2. Permission Management

**DO:**
- Use role-based permissions primarily
- Grant user-specific permissions sparingly
- Set expiration dates for temporary permissions
- Document permission changes with reasons
- Review permissions regularly

**DON'T:**
- Grant unnecessary permissions
- Skip permission checks
- Hardcode permission logic
- Allow users to modify their own permissions

### 3. Role Design

**DO:**
- Create roles based on job functions
- Keep permission sets focused
- Use descriptive role names
- Mark system roles appropriately
- Document role purposes

**DON'T:**
- Create too many roles
- Overlap role permissions unnecessarily
- Allow deletion of system roles
- Grant excessive permissions to roles

### 4. Approval Workflow

**DO:**
- Log approval level
- Track delegation chains
- Store approval comments
- Monitor approval times
- Support multi-level approvals

**DON'T:**
- Allow self-approval
- Skip approval logging
- Delete approval history
- Override approvals without logging

---

## Migration Script

To set up the activity tracking tables, create a migration:

```python
# migrations/create_activity_tracking_tables.py

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Activity Logs table
    op.create_table(
        'activity_logs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        # ... add all other columns
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )

    # Create indexes
    op.create_index('idx_activity_user_module', 'activity_logs', ['user_id', 'module'])
    op.create_index('idx_activity_entity', 'activity_logs', ['entity_type', 'entity_id'])
    # ... create other indexes

    # Repeat for other tables

def downgrade():
    op.drop_table('activity_logs')
    # ... drop other tables
```

---

## Conclusion

This comprehensive activity tracking and permission management system provides:

✅ **Complete Audit Trail** - Know who did what, when, and why
✅ **Fine-Grained Permissions** - Control access at module/action/resource level
✅ **Approval Tracking** - Full history of approval workflows
✅ **Session Management** - Monitor and control user sessions
✅ **Security & Compliance** - Meet audit and compliance requirements

For support or questions, refer to the API documentation or contact the development team.
