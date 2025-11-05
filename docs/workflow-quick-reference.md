# Workflow System - Quick Reference

## 🚀 Quick Start

### 1. Create a Standard Purchase Approval Workflow

```python
from app.services.workflow_service import WorkflowService

service = WorkflowService(db)
workflow = service.create_standard_purchase_workflow(
    branch_id="branch-001",
    created_by="user-admin"
)
```

### 2. Initiate Workflow for a Purchase

```python
workflow_instance = service.initiate_workflow(
    entity_type="purchase",
    entity_id=purchase.id,
    initiated_by=current_user.id,
    module="purchases",
    branch_id=purchase.branch_id
)
```

### 3. Submit for Approval

```python
instance = service.transition_workflow(
    workflow_instance_id=instance_id,
    user_id=current_user.id,
    action=WorkflowActionType.SUBMIT,
    comment="Ready for review"
)
```

### 4. Approve/Reject

```python
# Approve
instance = service.transition_workflow(
    workflow_instance_id=instance_id,
    user_id=manager_user_id,
    action=WorkflowActionType.APPROVE,
    comment="Approved for Q1 budget"
)

# Reject
instance = service.transition_workflow(
    workflow_instance_id=instance_id,
    user_id=manager_user_id,
    action=WorkflowActionType.REJECT,
    reason="Exceeds budget",
    comment="Please revise and resubmit"
)
```

---

## 📊 Common API Calls

### Get Pending Approvals for User

```bash
GET /api/v1/workflows/my-pending-approvals?limit=50
```

### Get Workflow Instance

```bash
GET /api/v1/workflows/instances/{instance_id}
```

### Get Available Actions

```bash
GET /api/v1/workflows/instances/{instance_id}/available-actions
```

### Submit

```bash
POST /api/v1/workflows/instances/{instance_id}/submit
Content-Type: application/json

{
  "comment": "Ready for manager review"
}
```

### Approve

```bash
POST /api/v1/workflows/instances/{instance_id}/approve
Content-Type: application/json

{
  "comment": "Approved for Q1 budget"
}
```

### Reject

```bash
POST /api/v1/workflows/instances/{instance_id}/reject
Content-Type: application/json

{
  "reason": "Exceeds budget",
  "comment": "Please revise and resubmit with lower amount"
}
```

---

## 🎨 Frontend Integration

### Load Workflow Widget

```html
<div id="workflowContainer"></div>

<script>
const widget = new WorkflowWidget('workflowContainer', {
    instanceId: 'workflow-instance-123',
    apiBaseUrl: '/api/v1/workflows',
    showTimeline: true,
    showProgress: true,
    showActions: true,
    onAction: (action, success) => {
        if (success) {
            alert(`${action} completed!`);
            location.reload();
        }
    }
});
</script>
```

### Display Status Badge

```javascript
function getWorkflowStatusBadge(status) {
    const statusConfig = {
        'draft': { icon: 'file-earmark', label: 'Draft' },
        'submitted': { icon: 'send', label: 'Submitted' },
        'pending_approval': { icon: 'clock', label: 'Pending Approval' },
        'approved': { icon: 'check-circle', label: 'Approved' },
        'rejected': { icon: 'x-circle', label: 'Rejected' },
        'completed': { icon: 'check-all', label: 'Completed' }
    };

    const config = statusConfig[status] || statusConfig['draft'];
    return `<span class="workflow-status workflow-status-${status}">
        <i class="bi bi-${config.icon}"></i> ${config.label}
    </span>`;
}
```

---

## 🔧 Workflow Configuration Examples

### 3-Level Purchase Approval

**States:**
1. Draft (initial)
2. Pending Manager Approval
3. Pending Finance Approval
4. Approved (final)
5. Rejected (final)

**Transitions:**
- Draft → Pending Manager (submit) - Any user
- Pending Manager → Pending Finance (approve) - Manager role
- Pending Manager → Rejected (reject) - Manager role
- Pending Finance → Approved (approve) - Finance Director role
- Pending Finance → Rejected (reject) - Finance Director role

### 2-Level Sales Invoice Approval

**States:**
1. Draft (initial)
2. Pending Sales Manager
3. Approved (final)
4. Rejected (final)

**Transitions:**
- Draft → Pending Sales Manager (submit) - Salesperson
- Pending Sales Manager → Approved (approve) - Sales Manager
- Pending Sales Manager → Rejected (reject) - Sales Manager

### 4-Level Manufacturing Order

**States:**
1. Draft (initial)
2. Pending Production Manager
3. Pending QA
4. Pending Warehouse
5. Approved (final)
6. Rejected (final)

**Transitions:**
- Draft → Pending Production Manager (submit)
- Pending Production Manager → Pending QA (approve)
- Pending QA → Pending Warehouse (approve)
- Pending Warehouse → Approved (approve)
- Any approval state → Rejected (reject)

---

## 📝 Database Queries

### Get All Workflows for a Module

```python
workflows = db.query(WorkflowDefinition).filter(
    WorkflowDefinition.module == "purchases",
    WorkflowDefinition.is_active == True
).all()
```

### Get Workflow Instance for Entity

```python
instance = db.query(WorkflowInstance).filter(
    WorkflowInstance.entity_type == "purchase",
    WorkflowInstance.entity_id == purchase_id
).first()
```

### Get Workflow History

```python
actions = db.query(WorkflowAction).filter(
    WorkflowAction.workflow_instance_id == instance_id
).order_by(WorkflowAction.action_date).all()
```

### Get Pending Approvals for Role

```python
# Get states where this role can approve
states = db.query(WorkflowState).filter(
    WorkflowState.allowed_roles.contains([role_id])
).all()

# Get instances in these states
instances = db.query(WorkflowInstance).filter(
    WorkflowInstance.current_state_id.in_([s.id for s in states]),
    WorkflowInstance.status.in_([
        WorkflowStatus.PENDING_APPROVAL,
        WorkflowStatus.SUBMITTED
    ])
).all()
```

---

## 🎯 Common Patterns

### Pattern 1: Auto-Submit on Creation

```python
# In create_purchase endpoint
workflow_instance = service.initiate_workflow(
    entity_type="purchase",
    entity_id=purchase.id,
    initiated_by=current_user.id,
    module="purchases"
)

# If workflow has auto_submit=True, it will auto-transition to first approval state
# Otherwise, manually submit:
service.transition_workflow(
    workflow_instance_id=workflow_instance.id,
    user_id=current_user.id,
    action=WorkflowActionType.SUBMIT
)
```

### Pattern 2: Update Entity on Approval

```python
# Hook in workflow service
if workflow_instance.status == WorkflowStatus.APPROVED:
    purchase = db.query(Purchase).filter(
        Purchase.id == workflow_instance.entity_id
    ).first()
    purchase.status = "approved"
    purchase.approved_by = workflow_instance.completed_by
    purchase.approved_at = workflow_instance.completed_at
    db.commit()
```

### Pattern 3: Conditional Workflow Based on Amount

```python
# Create workflow with threshold
workflow = service.create_workflow_definition(
    name="Purchase Order Approval",
    code="PO_APPROVAL",
    module="purchases",
    approval_threshold_amount=10000  # Only trigger for >$10k
)

# In purchase creation
if purchase.total_amount > 10000:
    # Initiate approval workflow
    workflow_instance = service.initiate_workflow(...)
else:
    # Auto-approve small purchases
    purchase.status = "approved"
```

---

## 🔍 Debugging & Troubleshooting

### Check Workflow State

```python
instance = db.query(WorkflowInstance).filter(
    WorkflowInstance.id == instance_id
).first()

print(f"Current State: {instance.current_state.name}")
print(f"Status: {instance.status}")
print(f"Assignee: {instance.current_assignee}")
```

### Check Available Actions

```python
actions = service.get_available_actions(instance_id, user_id)
print(f"Available actions: {[a['label'] for a in actions]}")
```

### View Workflow History

```python
history = service.get_workflow_history(instance_id)
for action in history:
    print(f"{action.action_date}: {action.action} by {action.performed_by_user.username}")
    if action.comment:
        print(f"  Comment: {action.comment}")
```

### Common Errors

**Error**: "User does not have permission to perform action"
- **Cause**: User's role not in transition's `allowed_roles`
- **Fix**: Add user's role to transition configuration

**Error**: "Comment is required for this action"
- **Cause**: Transition has `requires_comment=True`
- **Fix**: Include comment in request

**Error**: "No active workflow found for module"
- **Cause**: No workflow defined for this module
- **Fix**: Create workflow definition with `is_default=True`

---

## 📚 File Locations

| Component | Location |
|-----------|----------|
| Models | `app/models/workflow.py` |
| Service | `app/services/workflow_service.py` |
| API Endpoints | `app/api/v1/endpoints/workflows.py` |
| Schemas | `app/schemas/workflow.py` |
| UI Components | `app/static/workflow-components.html` |
| Documentation | `docs/workflow-system-guide.md` |
| This Quick Ref | `docs/workflow-quick-reference.md` |

---

## 🎓 Next Steps

1. **Read**: `docs/workflow-system-guide.md` for complete documentation
2. **Review**: `app/static/workflow-components.html` for UI examples
3. **Test**: Create a test workflow using the API
4. **Integrate**: Add workflow to your first module (purchases, sales, etc.)
5. **Customize**: Create custom workflows for your business needs

---

**Need Help?** Check the full documentation at `docs/workflow-system-guide.md`
