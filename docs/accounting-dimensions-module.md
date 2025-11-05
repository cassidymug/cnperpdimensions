# Accounting Dimensions Management Module

## Overview
Comprehensive global management interface for accounting dimensions and their values. This module provides full CRUD operations for multi-dimensional financial analysis across the entire ERP system.

**URL**: `http://localhost:8010/static/accounting-dimensions.html`

## Features

### 1. **Dimensions Management**
Complete lifecycle management for accounting dimensions:

#### Dimension Types
- **Organizational**: Departments, divisions, subsidiaries
- **Geographical**: Regions, countries, branches, locations
- **Functional**: Cost centers, profit centers, business units
- **Project**: Projects, campaigns, initiatives
- **Product**: Product lines, categories, brands
- **Customer**: Customer segments, channels, types
- **Temporal**: Fiscal periods, seasons, quarters
- **Custom**: User-defined dimensions

#### Dimension Scopes
- **Global**: Available across all branches/entities
- **Branch**: Specific to a branch
- **Entity**: Specific to a legal entity
- **Department**: Specific to a department

#### Key Features
- ✅ Create new dimensions with full configuration
- ✅ Edit existing dimensions
- ✅ View detailed dimension information
- ✅ Delete dimensions (with validation)
- ✅ Filter by type, status, and scope
- ✅ Track active/inactive dimensions
- ✅ Configure required dimensions
- ✅ Support for hierarchical dimensions
- ✅ Allow multiple values per dimension
- ✅ Display order management

### 2. **Dimension Values Management**
Manage values within each dimension:

#### Value Features
- ✅ Create new values for any dimension
- ✅ Edit value names and descriptions
- ✅ Set parent-child relationships (hierarchy)
- ✅ Activate/deactivate values
- ✅ Delete unused values
- ✅ View all values in table format
- ✅ Filter by status

#### Hierarchy Support
- Parent-child relationships
- Multi-level hierarchies
- Configurable max depth
- Visual hierarchy display

### 3. **Statistics Dashboard**
Real-time metrics:
- **Total Dimensions**: Count of all dimensions
- **Active Dimensions**: Currently enabled dimensions
- **Total Values**: Sum of all dimension values
- **Required Dimensions**: Dimensions mandatory on transactions

### 4. **Filtering & Search**
Advanced filtering options:

**Dimensions Tab**:
- Filter by dimension type (8 types)
- Filter by status (Active/Inactive)
- Filter by scope (Global/Branch/Entity/Department)

**Values Tab**:
- Select specific dimension
- Filter by value status
- Quick refresh

## User Interface

### Dimensions Tab
Displays all dimensions with:
- Color-coded cards by type
- Status badges (Active/Inactive/Required/Scope)
- Value count preview (first 10 values)
- Configuration summary
- Action buttons (View/Edit/Delete)

### Values Tab
Table view of dimension values:
- Code and name columns
- Description
- Parent value (for hierarchies)
- Status indicator
- Edit and delete actions

### Analytics Tab
Placeholder for future analytics:
- Dimension usage tracking
- Transaction analysis
- Reporting integration

## API Integration

### Dimensions Endpoints

#### **Create Dimension**
```
POST /api/v1/accounting/dimensions/
```
**Request Body**:
```json
{
  "code": "DEPT",
  "name": "Department",
  "description": "Organizational departments",
  "dimension_type": "organizational",
  "scope": "global",
  "is_active": true,
  "is_required": false,
  "allow_multiple_values": false,
  "supports_hierarchy": true,
  "display_order": 1,
  "max_hierarchy_levels": 3
}
```

#### **Get All Dimensions**
```
GET /api/v1/accounting/dimensions/?include_values=true
```
**Query Parameters**:
- `dimension_type`: Filter by type
- `is_active`: Filter by status (true/false)
- `branch_id`: Filter by branch
- `include_values`: Include dimension values

#### **Get Dimension by ID**
```
GET /api/v1/accounting/dimensions/{dimension_id}
```

#### **Update Dimension**
```
PUT /api/v1/accounting/dimensions/{dimension_id}
```
**Request Body**:
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "is_active": true,
  "is_required": true
}
```

#### **Delete Dimension**
```
DELETE /api/v1/accounting/dimensions/{dimension_id}
```

### Dimension Values Endpoints

#### **Create Value**
```
POST /api/v1/accounting/dimensions/values
```
**Request Body**:
```json
{
  "dimension_id": "123-456-789",
  "code": "SALES",
  "name": "Sales Department",
  "description": "Sales and marketing team",
  "parent_value_id": null,
  "is_active": true
}
```

#### **Get Dimension Values**
```
GET /api/v1/accounting/dimensions/{dimension_id}/values
```
**Query Parameters**:
- `is_active`: Filter active/inactive

#### **Update Value**
```
PUT /api/v1/accounting/dimensions/values/{value_id}
```

#### **Delete Value**
```
DELETE /api/v1/accounting/dimensions/values/{value_id}
```

## Common Use Cases

### 1. **Department Dimension**
Track transactions by organizational department.

**Setup**:
1. Create dimension:
   - Code: `DEPT`
   - Name: `Department`
   - Type: `organizational`
   - Scope: `global`
   - Required: `Yes`

2. Add values:
   - Sales Department
   - Marketing Department
   - Finance Department
   - Operations Department
   - IT Department

**Usage**: Every transaction must specify a department for proper cost allocation.

### 2. **Project Tracking**
Analyze costs and revenue by project.

**Setup**:
1. Create dimension:
   - Code: `PROJ`
   - Name: `Project`
   - Type: `project`
   - Scope: `global`
   - Hierarchy: `Yes` (3 levels)

2. Add hierarchical values:
   - Client Projects
     - Client A - Project 1
     - Client A - Project 2
   - Internal Projects
     - Infrastructure Upgrade
     - System Migration

**Usage**: Track project profitability across sales and purchases.

### 3. **Cost Center Analysis**
Detailed cost center tracking for budgeting.

**Setup**:
1. Create dimension:
   - Code: `CC`
   - Name: `Cost Center`
   - Type: `functional`
   - Scope: `branch`
   - Required: `Yes` (for expense accounts)

2. Add values:
   - CC-100: Administration
   - CC-200: Sales & Marketing
   - CC-300: Production
   - CC-400: R&D

**Usage**: Budget allocation and variance analysis by cost center.

### 4. **Geographic Revenue Tracking**
Track sales by geographic region.

**Setup**:
1. Create dimension:
   - Code: `GEO`
   - Name: `Geography`
   - Type: `geographical`
   - Scope: `global`
   - Hierarchy: `Yes` (2 levels)

2. Add hierarchical values:
   - North America
     - USA
     - Canada
     - Mexico
   - Europe
     - UK
     - Germany
     - France

**Usage**: Regional sales analysis and territory management.

### 5. **Product Line Analysis**
Analyze profitability by product line.

**Setup**:
1. Create dimension:
   - Code: `PRODLINE`
   - Name: `Product Line`
   - Type: `product`
   - Scope: `global`
   - Multiple Values: `No`

2. Add values:
   - Hardware
   - Software
   - Services
   - Consulting

**Usage**: Product line contribution analysis.

## Best Practices

### Creating Dimensions
1. **Use clear, descriptive codes** (e.g., DEPT, PROJ, CC)
2. **Limit required dimensions** to avoid data entry burden
3. **Plan hierarchy levels** before enabling hierarchy
4. **Set appropriate scopes** (global vs. branch-specific)
5. **Use display order** for UI consistency
6. **Document purpose** in description field

### Managing Values
1. **Use consistent naming** conventions
2. **Leverage hierarchies** for complex structures
3. **Mark inactive** instead of deleting (preserve history)
4. **Avoid duplicate codes** within a dimension
5. **Keep descriptions** up to date
6. **Review regularly** for obsolete values

### Integration with Transactions
1. **Configure required dimensions** on account level
2. **Set default values** where possible
3. **Validate before posting** transactions
4. **Use bulk assignment** for mass updates
5. **Enable dimension analysis** in reports

## Accounting Integration

### Chart of Accounts
Dimensions can be:
- Required for specific accounts
- Suggested with defaults
- Validated on posting

### Journal Entries
Each journal entry line can have:
- Multiple dimension assignments
- Validation against requirements
- Default value population

### Financial Reports
Dimensions enable:
- Multi-dimensional P&L statements
- Balance sheet by dimension
- Cost center reports
- Project profitability
- Geographic analysis

## Configuration Examples

### Example 1: Small Business Setup
```javascript
// Minimal dimension setup
Dimensions:
1. Department (organizational, required)
   - Sales
   - Operations
   - Admin

2. Location (geographical, optional)
   - Main Office
   - Warehouse
```

### Example 2: Manufacturing Company
```javascript
Dimensions:
1. Cost Center (functional, required)
   - Production CC-100
   - Warehouse CC-200
   - Admin CC-300

2. Product Line (product, required)
   - Product A
   - Product B
   - Product C

3. Project (project, optional, hierarchy)
   - Customer Projects
     - Project 1
     - Project 2
   - Internal Projects
```

### Example 3: Multi-Branch Organization
```javascript
Dimensions:
1. Branch (geographical, required, global)
   - New York
   - Los Angeles
   - Chicago

2. Department (organizational, required, branch-specific)
   - Sales
   - Finance
   - Operations

3. Customer Segment (customer, optional, global)
   - Enterprise
   - SMB
   - Retail
```

## Security & Permissions

### Required Permissions
- `accounting.dimensions.view`: View dimensions
- `accounting.dimensions.create`: Create dimensions
- `accounting.dimensions.edit`: Modify dimensions
- `accounting.dimensions.delete`: Delete dimensions
- `accounting.dimensions.manage_values`: Manage dimension values

### Access Control
- Global dimensions: Requires global admin rights
- Branch dimensions: Branch manager access
- Entity dimensions: Entity admin access

## Troubleshooting

### Cannot Create Dimension
**Issue**: Code already exists
**Solution**: Use unique code or check for inactive dimensions with same code

### Cannot Delete Dimension
**Issue**: Dimension has transactions
**Solution**: Mark as inactive instead of deleting

### Values Not Showing
**Issue**: Dimension not selected or values inactive
**Solution**: Select dimension and check status filter

### Cannot Set Parent Value
**Issue**: Hierarchy not enabled
**Solution**: Enable "Supports Hierarchy" in dimension settings

## Next Steps

After creating dimensions:

1. **Configure Account Requirements**
   - Link dimensions to specific accounts
   - Set required vs. optional
   - Define default values

2. **Update Transaction Templates**
   - Add dimension fields to forms
   - Enable dimension dropdowns
   - Set validation rules

3. **Create Reports**
   - Multi-dimensional P&L
   - Cost center analysis
   - Project profitability
   - Geographic reports

4. **Train Users**
   - Dimension concepts
   - Value selection
   - Reporting capabilities

## Files Created

- `app/static/accounting-dimensions.html` - Main management interface

## Dependencies

- Bootstrap 5.3.0 (UI framework)
- Font Awesome 6.4.0 (icons)
- auth.js (authentication)
- navbar.js (navigation)
- Accounting Dimensions API (backend)

## Browser Compatibility

- Chrome/Edge: ✅ Fully supported
- Firefox: ✅ Fully supported
- Safari: ✅ Fully supported
- Mobile browsers: ✅ Responsive design

---

**Status**: ✅ Complete and functional
**Version**: 1.0
**Date**: October 26, 2025
**Author**: CNP ERP Development Team
