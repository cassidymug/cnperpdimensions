# Role-Based Workflow System - Complete Guide

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Database Models](#database-models)
4. [Workflow Configuration](#workflow-configuration)
5. [API Endpoints](#api-endpoints)
6. [Frontend Components](#frontend-components)
7. [Integration Guide](#integration-guide)
8. [Examples](#examples)
9. [Best Practices](#best-practices)

---

## Overview

The Role-Based Workflow System provides a flexible, configurable approval workflow engine for all ERP modules. It supports:

- ✅ **Multi-level approvals** with role-based routing
- ✅ **State machine transitions** with validation
- ✅ **Audit trail** of all workflow actions
- ✅ **Notifications** for pending approvals
- ✅ **Reassignment** capabilities
- ✅ **Configurable workflows** per module and branch
- ✅ **Template-based setup** for common workflows

### Key Features

| Feature | Description |
|---------|-------------|
| **Role-Based Authorization** | Control who can approve at each stage based on user roles |
| **Flexible States** | Define custom states for each workflow (Draft, Pending, Approved, etc) |
| **Conditional Transitions** | Set conditions for state transitions (amount thresholds, etc) |
| **Action Requirements** | Force comments, attachments, or specific permissions |
| **Dashboard & Reporting** | View pending approvals, workflow history, and analytics |
| **Branch-Specific** | Different workflows per branch if needed |

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Purchase     │  │ Sales        │  │ Manufacturing│     │
│  │ Module       │  │ Module       │  │ Module       │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │              │
│         └──────────────────┼──────────────────┘              │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────┐
│                    Workflow API Layer                        │
│                            │                                 │
│    /api/v1/workflows/*     │                                 │
│         │                  │                                 │
│         ▼                  │                                 │
│  ┌──────────────────────────────────────────┐               │
│  │      WorkflowService (Business Logic)    │               │
│  │  - State Transitions                     │               │
│  │  - Role Authorization                    │               │
│  │  - Approval Routing                      │               │
│  │  - Notification Triggering               │               │
│  └──────────────────────────────────────────┘               │
└────────────────────────────┼─────────────────────────────────┘
                             │
┌────────────────────────────┼─────────────────────────────────┐
│                    Data Layer                                │
│                            │                                 │
│  ┌──────────────┬─────────┴─────────┬──────────────┐       │
│  │ Workflow     │ Workflow          │ Workflow     │       │
│  │ Definitions  │ Instances         │ Actions      │       │
│  └──────────────┴───────────────────┴──────────────┘       │
│                                                              │
│  WorkflowDefinition → WorkflowState → WorkflowTransition    │
│  WorkflowInstance → WorkflowAction → WorkflowNotification   │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User Creates Entity** (e.g., Purchase Order)
2. **Workflow Initiated** → Creates WorkflowInstance
3. **State = Draft** → Initial state
4. **User Submits** → Transition to "Pending Manager Approval"
5. **Manager Approves** → Transition to "Pending Finance Approval"
6. **Finance Approves** → Transition to "Approved" (Final State)
7. **Audit Trail Recorded** → All actions logged in WorkflowAction

---

## Database Models

### Core Tables

#### `workflow_definitions`
Defines a workflow template for a module.

```sql
CREATE TABLE workflow_definitions (
    id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,           -- "Purchase Order Approval"
    code VARCHAR UNIQUE NOT NULL,    -- "PO_APPROVAL_3LEVEL"
    module VARCHAR NOT NULL,         -- "purchases", "sales", etc
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    requires_approval BOOLEAN DEFAULT TRUE,
    auto_submit BOOLEAN DEFAULT FALSE,
    approval_threshold_amount INTEGER DEFAULT 0,
    max_approval_levels INTEGER DEFAULT 3,
    created_by VARCHAR REFERENCES users(id),
    branch_id VARCHAR REFERENCES branches(id),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### `workflow_states`
Individual states in a workflow.

```sql
CREATE TABLE workflow_states (
    id VARCHAR PRIMARY KEY,
    workflow_definition_id VARCHAR REFERENCES workflow_definitions(id),
    name VARCHAR NOT NULL,               -- "Pending Manager Approval"
    code VARCHAR NOT NULL,               -- "PENDING_MGR"
    status VARCHAR NOT NULL,             -- Maps to WorkflowStatus enum
    description TEXT,
    is_initial BOOLEAN DEFAULT FALSE,    -- Starting state?
    is_final BOOLEAN DEFAULT FALSE,      -- Terminal state?
    requires_approval BOOLEAN DEFAULT FALSE,
    allowed_roles JSON,                  -- List of role IDs
    notified_roles JSON,                 -- List of role IDs to notify
    display_order INTEGER DEFAULT 0,
    color VARCHAR DEFAULT '#3b82f6',
    icon VARCHAR DEFAULT 'circle',
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### `workflow_transitions`
Allowed state transitions with role authorization.

```sql
CREATE TABLE workflow_transitions (
    id VARCHAR PRIMARY KEY,
    workflow_definition_id VARCHAR REFERENCES workflow_definitions(id),
    from_state_id VARCHAR REFERENCES workflow_states(id),
    to_state_id VARCHAR REFERENCES workflow_states(id),
    name VARCHAR NOT NULL,               -- "Submit for Approval"
    action VARCHAR NOT NULL,             -- submit, approve, reject, etc
    description TEXT,
    allowed_roles JSON,                  -- List of role IDs
    required_permission VARCHAR,
    requires_comment BOOLEAN DEFAULT FALSE,
    requires_attachment BOOLEAN DEFAULT FALSE,
    condition_script TEXT,               -- Python expression
    notify_on_transition BOOLEAN DEFAULT TRUE,
    notification_template VARCHAR,
    button_label VARCHAR,                -- "Approve", "Reject"
    button_color VARCHAR DEFAULT 'primary',
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### `workflow_instances`
Actual workflow instances for documents/transactions.

```sql
CREATE TABLE workflow_instances (
    id VARCHAR PRIMARY KEY,
    workflow_definition_id VARCHAR REFERENCES workflow_definitions(id),
    current_state_id VARCHAR REFERENCES workflow_states(id),
    entity_type VARCHAR NOT NULL,        -- "purchase", "invoice", etc
    entity_id VARCHAR NOT NULL,          -- ID of the entity
    status VARCHAR NOT NULL,             -- Current workflow status
    initiated_by VARCHAR REFERENCES users(id),
    initiated_at TIMESTAMP NOT NULL,
    current_assignee VARCHAR REFERENCES users(id),
    completed_at TIMESTAMP,
    completed_by VARCHAR REFERENCES users(id),
    branch_id VARCHAR REFERENCES branches(id),
    priority VARCHAR DEFAULT 'normal',   -- low, normal, high, urgent
    due_date TIMESTAMP,
    metadata JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,

    INDEX idx_entity (entity_type, entity_id),
    INDEX idx_status (status),
    INDEX idx_assignee (current_assignee)
);
```

#### `workflow_actions`
Audit trail of all workflow actions.

```sql
CREATE TABLE workflow_actions (
    id VARCHAR PRIMARY KEY,
    workflow_instance_id VARCHAR REFERENCES workflow_instances(id),
    from_state_id VARCHAR REFERENCES workflow_states(id),
    to_state_id VARCHAR REFERENCES workflow_states(id),
    action VARCHAR NOT NULL,             -- submit, approve, reject, etc
    action_date TIMESTAMP NOT NULL,
    performed_by VARCHAR REFERENCES users(id),
    comment TEXT,
    reason VARCHAR,                      -- Rejection reason
    attachments JSON,
    reassigned_from VARCHAR REFERENCES users(id),
    reassigned_to VARCHAR REFERENCES users(id),
    ip_address VARCHAR,
    user_agent VARCHAR,
    duration_seconds INTEGER,            -- Time in previous state
    created_at TIMESTAMP,

    INDEX idx_instance (workflow_instance_id),
    INDEX idx_date (action_date)
);
```

---

## Workflow Configuration

### Example 1: 3-Level Purchase Approval Workflow

```python
from app.services.workflow_service import WorkflowService

service = WorkflowService(db)

# Create workflow using template
workflow = service.create_standard_purchase_workflow(
    branch_id="branch-001",
    created_by="user-admin"
)

# Or create custom workflow
workflow = service.create_workflow_definition(
    name="Purchase Order Approval (3-Level)",
    code="PO_APPROVAL_3LEVEL",
    module="purchases",
    description="Standard 3-level approval workflow",
    max_approval_levels=3,
    approval_threshold_amount=10000  # Require approval for >$10k
)

# Create states
draft_state = WorkflowState(
    workflow_definition_id=workflow.id,
    name="Draft",
    code="DRAFT",
    status=WorkflowStatus.DRAFT,
    is_initial=True,
    color="#6b7280",
    icon="file-earmark"
)

pending_mgr_state = WorkflowState(
    workflow_definition_id=workflow.id,
    name="Pending Manager Approval",
    code="PENDING_MGR",
    status=WorkflowStatus.PENDING_APPROVAL,
    requires_approval=True,
    allowed_roles=["role-manager"],
    notified_roles=["role-manager"],
    color="#f59e0b",
    icon="clock"
)

# ... create other states

# Create transitions
submit_transition = WorkflowTransition(
    workflow_definition_id=workflow.id,
    from_state_id=draft_state.id,
    to_state_id=pending_mgr_state.id,
    name="Submit for Approval",
    action=WorkflowActionType.SUBMIT,
    button_label="Submit",
    button_color="primary"
)

# ... create other transitions
```

### Example 2: Configure Roles for Each State

```python
# Manager can approve purchases
manager_approve = WorkflowTransition(
    workflow_definition_id=workflow.id,
    from_state_id=pending_mgr_state.id,
    to_state_id=pending_finance_state.id,
    name="Manager Approval",
    action=WorkflowActionType.APPROVE,
    allowed_roles=["role-manager", "role-senior-manager"],
    requires_comment=False,
    button_label="Approve",
    button_color="success"
)

# Finance Director can final approve
finance_approve = WorkflowTransition(
    workflow_definition_id=workflow.id,
    from_state_id=pending_finance_state.id,
    to_state_id=approved_state.id,
    name="Finance Approval",
    action=WorkflowActionType.APPROVE,
    allowed_roles=["role-finance-director", "role-cfo"],
    requires_comment=True,  # Force comment
    button_label="Final Approve",
    button_color="success"
)
```

---

## API Endpoints

### Workflow Definition Management

```http
# Create workflow definition
POST /api/v1/workflows/definitions
Content-Type: application/json

{
  "name": "Purchase Order Approval (3-Level)",
  "code": "PO_APPROVAL_3LEVEL",
  "module": "purchases",
  "description": "Standard 3-level approval workflow",
  "is_active": true,
  "is_default": true,
  "requires_approval": true,
  "max_approval_levels": 3,
  "approval_threshold_amount": 10000
}

# Get all workflows for a module
GET /api/v1/workflows/definitions?module=purchases&is_active=true

# Get specific workflow
GET /api/v1/workflows/definitions/{workflow_id}

# Update workflow
PUT /api/v1/workflows/definitions/{workflow_id}

# Delete workflow
DELETE /api/v1/workflows/definitions/{workflow_id}
```

### Workflow Instance Operations

```http
# Initiate workflow for an entity
POST /api/v1/workflows/instances
{
  "workflow_definition_id": "wf-123",
  "entity_type": "purchase",
  "entity_id": "po-001",
  "branch_id": "branch-001"
}

# Get workflow instance
GET /api/v1/workflows/instances/{instance_id}

# Submit for approval
POST /api/v1/workflows/instances/{instance_id}/submit
{
  "comment": "Ready for manager review"
}

# Approve
POST /api/v1/workflows/instances/{instance_id}/approve
{
  "comment": "Approved for Q1 budget"
}

# Reject
POST /api/v1/workflows/instances/{instance_id}/reject
{
  "reason": "Exceeds budget",
  "comment": "Please revise and resubmit with lower amount"
}

# Reassign
POST /api/v1/workflows/instances/{instance_id}/reassign
{
  "assignee_id": "user-456",
  "comment": "Reassigning to senior manager"
}

# Get available actions for current user
GET /api/v1/workflows/instances/{instance_id}/available-actions

# Get workflow history
GET /api/v1/workflows/instances/{instance_id}/history
```

### User Dashboard

```http
# Get my pending approvals
GET /api/v1/workflows/my-pending-approvals?limit=50

# Get workflow dashboard
GET /api/v1/workflows/dashboard
```

### Quick Setup (Templates)

```http
# Create standard purchase approval workflow
POST /api/v1/workflows/templates/purchase-approval
{
  "template_name": "purchase_approval_3level",
  "module": "purchases",
  "name": "Purchase Order Approval",
  "branch_id": "branch-001",
  "approval_threshold_amount": 10000
}
```

---

## Frontend Components

### 1. Workflow Status Badge

```html
<span class="workflow-status workflow-status-pending_approval">
    <i class="bi bi-clock"></i> Pending Approval
</span>
```

### 2. Workflow Progress Tracker

```javascript
// Display workflow progress
const widget = new WorkflowWidget('workflowContainer', {
    instanceId: 'wf-instance-123',
    apiBaseUrl: '/api/v1/workflows',
    showProgress: true,
    showTimeline: true,
    showActions: true
});
```

### 3. Workflow Action Buttons

```html
<div class="workflow-actions">
    <button class="workflow-action-btn btn btn-success" onclick="approveWorkflow()">
        <i class="bi bi-check-circle"></i> Approve
    </button>
    <button class="workflow-action-btn btn btn-danger" onclick="rejectWorkflow()">
        <i class="bi bi-x-circle"></i> Reject
    </button>
</div>
```

See `workflow-components.html` for full component library and examples.

---

## Integration Guide

### Step 1: Add Workflow to Purchase Module

```python
# In app/api/v1/endpoints/purchases.py

from app.services.workflow_service import WorkflowService

@router.post("/purchases", response_model=PurchaseResponse)
async def create_purchase(
    purchase_data: PurchaseCreate,
    db: Session = Depends(get_db)
):
    # Create purchase
    purchase = Purchase(**purchase_data.dict())
    db.add(purchase)
    db.commit()

    # Initiate workflow
    workflow_service = WorkflowService(db)
    workflow_instance = workflow_service.initiate_workflow(
        entity_type="purchase",
        entity_id=purchase.id,
        initiated_by=current_user.id,
        module="purchases",
        branch_id=purchase.branch_id
    )

    return purchase
```

### Step 2: Add Workflow UI to Frontend

```html
<!-- In purchases.html -->
<div id="workflowSection" class="mt-4" style="display: none;">
    <div class="card">
        <div class="card-header">
            <h5><i class="bi bi-diagram-3 me-2"></i>Approval Workflow</h5>
        </div>
        <div class="card-body">
            <div id="workflowWidget"></div>
        </div>
    </div>
</div>

<script>
// Load workflow for purchase
async function loadPurchaseWorkflow(purchaseId) {
    try {
        // Get workflow instance for this purchase
        const response = await fetch(
            `/api/v1/workflows/instances?entity_type=purchase&entity_id=${purchaseId}`
        );
        const instances = await response.json();

        if (instances.length > 0) {
            const instance = instances[0];

            // Show workflow section
            document.getElementById('workflowSection').style.display = 'block';

            // Initialize workflow widget
            const widget = new WorkflowWidget('workflowWidget', {
                instanceId: instance.id,
                apiBaseUrl: '/api/v1/workflows',
                onAction: (action, success) => {
                    if (success) {
                        alert(`${action} completed successfully!`);
                        loadPurchases(); // Refresh purchase list
                    }
                }
            });
        }
    } catch (error) {
        console.error('Error loading workflow:', error);
    }
}
</script>
```

### Step 3: Update Entity Status on Workflow Completion

```python
# In app/services/workflow_service.py

def _on_workflow_completed(self, workflow_instance: WorkflowInstance):
    """Update entity status when workflow completes"""
    if workflow_instance.entity_type == "purchase":
        purchase = self.db.query(Purchase).filter(
            Purchase.id == workflow_instance.entity_id
        ).first()

        if workflow_instance.status == WorkflowStatus.APPROVED:
            purchase.status = "approved"
            purchase.approved_by = workflow_instance.completed_by
            purchase.approved_at = workflow_instance.completed_at
        elif workflow_instance.status == WorkflowStatus.REJECTED:
            purchase.status = "rejected"

        self.db.commit()
```

---

## Examples

### Example 1: Manufacturing Order Workflow

```
States:
1. Draft
2. Pending Production Manager Approval
3. Pending QA Approval
4. Pending Warehouse Approval
5. Approved
6. Rejected

Transitions:
Draft → Pending Production Manager (action: submit)
Pending Production Manager → Pending QA (action: approve)
Pending Production Manager → Rejected (action: reject)
Pending QA → Pending Warehouse (action: approve)
Pending QA → Rejected (action: reject)
Pending Warehouse → Approved (action: approve)
Pending Warehouse → Rejected (action: reject)
```

### Example 2: Sales Invoice Workflow

```
States:
1. Draft
2. Pending Sales Manager Approval
3. Pending Accountant Approval
4. Approved
5. Rejected

Transitions:
Draft → Pending Sales Manager (action: submit)
Pending Sales Manager → Pending Accountant (action: approve)
Pending Sales Manager → Rejected (action: reject)
Pending Accountant → Approved (action: approve)
Pending Accountant → Rejected (action: reject)
```

---

## Best Practices

### 1. Workflow Design

✅ **Keep workflows simple** - 3-5 states max for most cases
✅ **Define clear roles** - Map each approval level to specific roles
✅ **Use meaningful state names** - "Pending Manager Approval" not "State 2"
✅ **Set rejection paths** - Allow rejection from any approval state
✅ **Add revision capability** - Let users revise and resubmit rejected items

### 2. Role Configuration

✅ **Use role-based, not user-based** - Assign to roles, not individual users
✅ **Support role hierarchies** - Senior Manager can approve Manager-level items
✅ **Branch-specific roles** - Different approvers per branch if needed

### 3. Notifications

✅ **Notify on state change** - Alert assignee when item enters their queue
✅ **Escalation reminders** - Send reminders for overdue approvals
✅ **Status updates** - Notify submitter on approval/rejection

### 4. Audit & Compliance

✅ **Log everything** - Every action, every state change
✅ **Capture reasons** - Require comments on rejection
✅ **Immutable history** - Never delete workflow actions
✅ **Time tracking** - Record duration in each state

### 5. Performance

✅ **Index heavily** - Index entity_type, entity_id, status, assignee
✅ **Limit history queries** - Paginate workflow action history
✅ **Cache workflows** - Cache workflow definitions, reload only on change

---

## Migration Guide

### Creating the Tables

```bash
# Generate Alembic migration
alembic revision --autogenerate -m "Add workflow tables"

# Apply migration
alembic upgrade head
```

### Initial Setup

```python
from app.services.workflow_service import WorkflowService

# 1. Create roles (if not exists)
manager_role = Role(name="Manager", code="MANAGER")
finance_role = Role(name="Finance Director", code="FINANCE_DIR")

# 2. Create standard workflows
service = WorkflowService(db)
purchase_workflow = service.create_standard_purchase_workflow()

# 3. Configure roles on states/transitions
# ... (see Workflow Configuration section)
```

---

## Support & Maintenance

For questions or issues:

1. Check this documentation
2. Review `workflow-components.html` for UI examples
3. See `app/services/workflow_service.py` for business logic
4. Check `app/api/v1/endpoints/workflows.py` for API examples

---

**Version**: 1.0
**Last Updated**: October 26, 2025
**Author**: CN PERP Development Team
