# Activity Tracking & Permission Management - Quick Reference

## 🚀 Quick Start

### 1. Run Migration
```bash
python migrations/create_activity_tracking_tables.py
```

### 2. Register Router (in app/main.py)
```python
from app.api.v1.endpoints.activity import router as activity_router
app.include_router(activity_router)
```

### 3. Start Using!

---

## 📝 Common Tasks

### Log an Activity
```python
from app.services.activity_service import ActivityService
from app.models.activity_log import ActivityType, ActivityModule

service = ActivityService(db)
service.log_activity(
    user_id=current_user.id,
    activity_type=ActivityType.CREATE,
    module=ActivityModule.SALES,
    action="Create Invoice",
    description=f"Created invoice INV-{number}",
    entity_type="Invoice",
    entity_id=invoice.id,
    entity_name=f"INV-{number}",
    branch_id=current_user.branch_id,
    new_values={"amount": 1500.00, "customer": "ABC Corp"},
    success=True
)
```

### Log an Approval
```python
service.log_approval(
    approver_id=current_user.id,
    entity_type="PurchaseOrder",
    entity_id=po.id,
    action="approve",
    decision="approved",
    entity_reference=f"PO-{number}",
    from_state="pending",
    to_state="approved",
    comments="Approved for processing",
    approval_level="L2"
)
```

### Check Permission
```python
from app.services.permission_service import PermissionService

service = PermissionService(db)

# Returns True/False
has_perm = service.user_has_permission(
    user_id=user.id,
    module="sales",
    action="delete",
    resource="all"
)

# Raises PermissionError if not allowed
service.check_permission(
    user_id=user.id,
    module="sales",
    action="delete",
    resource="all"
)
```

### Create a Role
```python
role = service.create_role(
    name="Branch Manager",
    description="Manages branch operations",
    is_system_role=False,
    created_by_id=admin.id,
    reason="New organizational structure"
)
```

### Assign Permission to Role
```python
service.assign_permission_to_role(
    role_id=role.id,
    permission_id=permission.id,
    assigned_by_id=admin.id,
    reason="Branch managers need sales access"
)
```

### Assign Role to User
```python
service.assign_role_to_user(
    user_id=user.id,
    role_id=role.id,
    assigned_by_id=admin.id,
    reason="Promoted to branch manager"
)
```

### Grant Temporary Permission
```python
from datetime import datetime, timedelta

service.assign_permission_to_user(
    user_id=user.id,
    permission_id=permission.id,
    assigned_by_id=admin.id,
    reason="Temporary access for project",
    expires_at=datetime.utcnow() + timedelta(days=30)
)
```

---

## 🔍 Common Queries

### Get User's Recent Activities
```python
activities = service.get_user_activities(
    user_id=user.id,
    module=ActivityModule.SALES,
    limit=50
)
```

### Get Entity History
```python
history = service.get_entity_activities(
    entity_type="Invoice",
    entity_id=invoice.id,
    include_access_logs=True
)
# Returns: { "activities": [...], "approvals": [...], "access_logs": [...] }
```

### Get Approval History
```python
approvals = service.get_approval_history(
    approver_id=user.id,
    entity_type="PurchaseOrder",
    limit=50
)
```

### Get User's Complete Permissions
```python
summary = service.get_user_permissions_summary(user.id)
# Returns: {
#   "user_id": "...",
#   "username": "...",
#   "role": "...",
#   "role_permissions": [...],
#   "user_specific_permissions": [...],
#   "all_permissions": [...]
# }
```

### Get Activity Statistics
```python
from datetime import datetime, timedelta

stats = service.get_activity_statistics(
    start_date=datetime.utcnow() - timedelta(days=7),
    end_date=datetime.utcnow(),
    module=ActivityModule.SALES
)
# Returns: {
#   "total_activities": 1247,
#   "failed_activities": 12,
#   "success_rate": 0.99,
#   "by_type": {...},
#   "by_module": {...},
#   "top_users": [...]
# }
```

---

## 🌐 API Endpoints Quick Reference

### Activity Logs
```
GET  /api/v1/activity/logs
GET  /api/v1/activity/logs/entity/{type}/{id}
GET  /api/v1/activity/logs/module/{module}
GET  /api/v1/activity/statistics
```

### Approvals
```
GET  /api/v1/activity/approvals
GET  /api/v1/activity/approvals/entity/{type}/{id}
```

### Roles
```
POST   /api/v1/activity/roles
GET    /api/v1/activity/roles
GET    /api/v1/activity/roles/{id}
PATCH  /api/v1/activity/roles/{id}
DELETE /api/v1/activity/roles/{id}
```

### Permissions
```
POST /api/v1/activity/permissions
GET  /api/v1/activity/permissions
GET  /api/v1/activity/permissions/module/{module}
```

### Role-Permission Assignment
```
POST   /api/v1/activity/roles/{role_id}/permissions
DELETE /api/v1/activity/roles/{role_id}/permissions/{perm_id}
```

### User-Permission Assignment
```
POST   /api/v1/activity/users/{user_id}/permissions
DELETE /api/v1/activity/users/{user_id}/permissions/{perm_id}
```

### User-Role Assignment
```
POST   /api/v1/activity/users/{user_id}/role
DELETE /api/v1/activity/users/{user_id}/role
```

### Permission Checking
```
POST /api/v1/activity/users/{user_id}/check-permission
GET  /api/v1/activity/users/{user_id}/permissions/summary
```

### Bulk Operations
```
POST /api/v1/activity/bulk/assign-permissions
POST /api/v1/activity/bulk/assign-roles
```

---

## 📊 Activity Types

```python
class ActivityType(str, enum.Enum):
    # CRUD
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

    # Workflow
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    REASSIGN = "reassign"
    CANCEL = "cancel"

    # Permission
    GRANT_PERMISSION = "grant_permission"
    REVOKE_PERMISSION = "revoke_permission"
    ASSIGN_ROLE = "assign_role"
    REMOVE_ROLE = "remove_role"

    # Auth
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"

    # Other
    EXPORT = "export"
    IMPORT = "import"
    PRINT = "print"
    EMAIL = "email"
```

## 📂 Modules

```python
class ActivityModule(str, enum.Enum):
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
```

---

## 🎯 Best Practices

### ✅ DO:
- Log immediately after action
- Include meaningful descriptions
- Track old and new values
- Set appropriate severity levels
- Check permissions before actions
- Use role-based permissions primarily
- Set expiration for temporary permissions
- Document reasons for permission changes

### ❌ DON'T:
- Log sensitive data (passwords, tokens)
- Skip permission checks
- Grant unnecessary permissions
- Allow users to modify own permissions
- Delete activity logs
- Allow deletion of system roles
- Use generic descriptions

---

## 🔒 Security Checklist

- [ ] Permission checks before sensitive operations
- [ ] Activity logging for all important actions
- [ ] Regular permission audits
- [ ] Session timeout configured
- [ ] Failed login attempt monitoring
- [ ] Permission change approval workflow
- [ ] Regular activity log reviews
- [ ] Secure storage of activity logs

---

## 🆘 Troubleshooting

### Permission Denied Error
```python
# Check what permissions user has
summary = service.get_user_permissions_summary(user.id)
print(summary)

# Check specific permission
has_perm = service.user_has_permission(
    user_id=user.id,
    module="sales",
    action="delete",
    resource="all"
)
print(f"Has permission: {has_perm}")
```

### Activities Not Logging
```python
# Ensure ActivityService is initialized
service = ActivityService(db)

# Check database connection
try:
    service.log_activity(...)
except Exception as e:
    print(f"Error: {e}")
```

### Role Assignment Failed
```python
# Check if role exists and is active
role = service.get_role_by_id(role_id)
if not role:
    print("Role not found")
elif not role.is_active:
    print("Role is inactive")
```

---

## 📚 Documentation Files

- **Complete Guide**: `docs/activity-tracking-guide.md`
- **Implementation Summary**: `docs/activity-module-summary.md`
- **Frontend Components**: `app/static/activity-components.html`
- **This Quick Reference**: `docs/activity-quick-reference.md`

---

## 💡 Examples in Context

### In a Sales Endpoint
```python
from fastapi import APIRouter, Depends
from app.services.activity_service import ActivityService
from app.services.permission_service import PermissionService

@router.post("/invoices")
def create_invoice(invoice_data, db, current_user):
    # Check permission
    perm_service = PermissionService(db)
    perm_service.check_permission(
        user_id=current_user.id,
        module="sales",
        action="create",
        resource="all"
    )

    # Create invoice
    invoice = Invoice(**invoice_data)
    db.add(invoice)
    db.commit()

    # Log activity
    activity_service = ActivityService(db)
    activity_service.log_activity(
        user_id=current_user.id,
        activity_type=ActivityType.CREATE,
        module=ActivityModule.SALES,
        action="Create Invoice",
        entity_type="Invoice",
        entity_id=invoice.id,
        new_values={"amount": invoice.total}
    )

    return invoice
```

### In an Approval Workflow
```python
@router.post("/purchase-orders/{po_id}/approve")
def approve_po(po_id, comments, db, current_user):
    # Check permission
    perm_service.check_permission(
        current_user.id, "purchases", "approve", "all"
    )

    # Update PO
    po = db.query(PurchaseOrder).get(po_id)
    po.status = "approved"
    db.commit()

    # Log approval
    activity_service.log_approval(
        approver_id=current_user.id,
        entity_type="PurchaseOrder",
        entity_id=po_id,
        action="approve",
        decision="approved",
        comments=comments
    )
```

---

## 🎓 Key Concepts

### Permission Format
```
module.action.resource

Examples:
- sales.create.all        (Can create any sales record)
- sales.read.own_branch   (Can read only own branch sales)
- purchases.approve.all   (Can approve any purchase)
```

### Permission Hierarchy
1. **User-specific permissions** (highest priority)
2. **Role permissions** (inherited from role)
3. **No permission** (denied by default)

### Activity Severity Levels
- **INFO**: Normal operations
- **WARNING**: Unusual but not critical
- **ERROR**: Failed operations
- **CRITICAL**: Security or data integrity issues

---

**Need more help?** Refer to the complete guide in `docs/activity-tracking-guide.md`
