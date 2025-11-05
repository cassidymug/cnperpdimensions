# Workflow Management Integration - Role Management Page

## Overview
Added comprehensive workflow creation, editing, viewing, and management functionality to the Role Management page at `http://localhost:8010/static/role-management.html`.

## Features Added

### 1. **Workflows Tab**
- New tab in the main navigation alongside Roles, Permissions, Privilege Chart, and Audit Log
- Dedicated interface for managing all workflow definitions in the system

### 2. **Workflow Listing**
- Display all workflow definitions with key information:
  - Workflow name and code
  - Module (Accounting, Sales, Purchases, etc.)
  - Status badges (Active/Inactive, Default, Requires Approval)
  - Configuration details (Max levels, Threshold, Auto submit)
  - State and transition counts
  - Creation and update timestamps

### 3. **Filtering & Search**
- **Module Filter**: Filter workflows by module (Accounting, Sales, Purchases, Inventory, Manufacturing, POS, HR)
- **Status Filter**: Show only Active or Inactive workflows
- **Refresh Button**: Reload workflow data

### 4. **Create Workflow Modal**
Comprehensive form for creating new workflows with:

**Basic Information:**
- Workflow Name (required)
- Code - unique identifier (required)
- Module selection (required)
- Description

**Configuration:**
- Max Approval Levels (1-10)
- Approval Threshold Amount
- Requires Approval (checkbox)
- Auto Submit - skip draft state (checkbox)
- Default Workflow for Module (checkbox)
- Active status (checkbox)

**API Endpoint:** `POST /api/v1/workflows/definitions`

### 5. **Edit Workflow Modal**
Update existing workflow configurations:
- Modify name, module, description
- Adjust approval threshold and max levels
- Toggle approval requirement and active status

**API Endpoint:** `PUT /api/v1/workflows/definitions/{workflow_id}`

### 6. **View Workflow Details Modal**
Detailed view showing:

**Basic Information:**
- Name, Code, Module, Description
- Status, Default flag, Approval settings
- Threshold amount and max levels

**Workflow States Table:**
- State name and code
- Status type
- Initial/Final flags
- Approval requirements
- Color coding

**Workflow Transitions Table:**
- Transition name and action type
- From State → To State mapping
- Comment requirements
- Notification settings

**API Endpoint:** `GET /api/v1/workflows/definitions/{workflow_id}`

### 7. **Delete Workflow**
- Confirmation dialog before deletion
- Immediate UI update after successful deletion

**API Endpoint:** `DELETE /api/v1/workflows/definitions/{workflow_id}`

## JavaScript Functions Added

### Core Functions:
```javascript
loadWorkflows()           // Load all workflows with filters
displayWorkflows()        // Render workflow cards
showCreateWorkflowModal() // Open creation modal
createWorkflow()          // Submit new workflow
editWorkflow(id)          // Open edit modal with data
updateWorkflow()          // Submit workflow updates
deleteWorkflow(id)        // Delete workflow with confirmation
viewWorkflowDetails(id)   // Show detailed workflow view
```

### Integration:
- Added to page initialization: `loadWorkflows()` on DOMContentLoaded
- Added global variable: `let workflows = []`
- Integrated with existing notification system
- Uses existing auth.authHeader() for authentication

## CSS Styling Added

### Workflow-Specific Styles:
```css
.workflow-card          // Card hover effects
.workflow-diagram       // Diagram container
.workflow-state         // State display boxes
.workflow-state.initial // Initial state styling (green)
.workflow-state.final   // Final state styling (red)
.workflow-arrow         // Transition arrows
```

## API Integration

### Endpoints Used:
1. **GET /api/v1/workflows/definitions**
   - Query params: `module`, `is_active`
   - Returns: List of workflow definitions

2. **POST /api/v1/workflows/definitions**
   - Body: WorkflowDefinitionCreate schema
   - Returns: Created workflow

3. **GET /api/v1/workflows/definitions/{id}**
   - Returns: Detailed workflow with states and transitions

4. **PUT /api/v1/workflows/definitions/{id}**
   - Body: WorkflowDefinitionUpdate schema
   - Returns: Updated workflow

5. **DELETE /api/v1/workflows/definitions/{id}**
   - Returns: Success status

## Module Support

Workflows can be created for the following modules:
- **Accounting** - Journal entries, invoices, payments
- **Sales** - Sales orders, invoices, quotes
- **Purchases** - Purchase orders, receipts, vendor payments
- **Inventory** - Stock transfers, adjustments, counts
- **Manufacturing** - Production orders, BOMs
- **Point of Sale** - POS transactions, cash management
- **Human Resources** - Leave requests, expense claims

## Workflow Configuration Options

### Approval Settings:
- **Requires Approval**: Enable multi-level approval process
- **Max Approval Levels**: 1-10 levels of approval
- **Approval Threshold**: Minimum amount requiring approval
- **Auto Submit**: Skip draft state and auto-submit

### Status Settings:
- **Active**: Workflow is available for use
- **Default**: Automatically used for the module
- **Is System Role**: Cannot be deleted

## Use Cases for Accounting

### 1. **Invoice Approval Workflow**
```
Draft → Submitted → Approved by Accountant → Approved by Manager → Posted
```
- Set threshold: $10,000
- Max levels: 3
- Requires approval: Yes

### 2. **Journal Entry Workflow**
```
Draft → Submitted → Reviewed → Approved → Posted
```
- All amounts require approval
- Max levels: 2

### 3. **Payment Approval Workflow**
```
Draft → Pending Approval → Approved → Payment Processed → Completed
```
- Threshold: $5,000
- Max levels: 2
- Auto-submit for amounts under threshold

### 4. **Expense Claim Workflow**
```
Submitted → Department Approval → Finance Approval → Paid
```
- Max levels: 2
- Requires comments for rejection

## Best Practices

### Creating Workflows:
1. Use descriptive names (e.g., "Accounting Invoice Approval")
2. Use consistent code format (e.g., ACC_INVOICE_APPROVAL)
3. Set appropriate thresholds based on business rules
4. Define max levels based on organizational hierarchy
5. Enable "Default" for primary workflow per module

### Managing Workflows:
1. Keep only one default workflow per module active
2. Test workflows before setting as default
3. Document state transitions clearly
4. Configure appropriate role permissions for each state
5. Use descriptive state colors for visual clarity

### Accounting-Specific:
1. Higher thresholds for senior approvers
2. Require comments for rejections
3. Enable audit trail for all transitions
4. Set up notifications for pending approvals
5. Define escalation paths for delayed approvals

## Integration with Roles & Permissions

Workflows integrate with the role management system:
- **State permissions**: Control which roles can access each state
- **Transition permissions**: Define who can perform actions
- **Approval roles**: Specify approver roles per level
- **Notification roles**: Configure who receives alerts

## Next Steps

To fully utilize workflow management:

1. **Create Default Workflows**
   - Define workflows for each accounting module
   - Set approval hierarchies

2. **Configure States**
   - Use the workflow API to add states
   - Define initial, intermediate, and final states

3. **Define Transitions**
   - Create transitions between states
   - Set required permissions and roles

4. **Assign to Entities**
   - Link workflows to invoices, journal entries, etc.
   - Enable approval process

5. **Monitor & Optimize**
   - Review workflow performance
   - Adjust thresholds and levels as needed

## API Documentation

For complete API reference, see:
- `/docs/workflow-api-guide.md`
- Swagger UI: `http://localhost:8010/docs`
- Endpoints under `/api/v1/workflows/`

## Testing

To test workflow management:

1. **Access the page**: `http://localhost:8010/static/role-management.html`
2. **Click "Workflows" tab**
3. **Create a test workflow**:
   - Name: "Test Accounting Workflow"
   - Code: "TEST_ACC_WF"
   - Module: "accounting"
   - Max Levels: 2
   - Click "Create Workflow"

4. **View details**: Click eye icon to see full workflow
5. **Edit**: Click edit icon to modify settings
6. **Filter**: Use module/status filters to find workflows

## Troubleshooting

### Workflows not loading:
- Check browser console for errors
- Verify API endpoint is accessible
- Check authentication token in auth.js

### Cannot create workflow:
- Ensure all required fields are filled
- Check code is unique
- Verify user has appropriate permissions

### Edit/Delete not working:
- Check workflow ID is valid
- Verify user permissions
- Check backend API logs

## Files Modified

- `app/static/role-management.html` - Added workflows tab, modals, and JavaScript functions

## Dependencies

- Bootstrap 5.3.0 (modals, forms, cards)
- Font Awesome 6.4.0 (icons)
- auth.js (authentication)
- navbar.js (navigation)
- Workflow API endpoints (backend)

---

**Status**: ✅ Complete and functional
**Version**: 1.0
**Date**: October 26, 2025
