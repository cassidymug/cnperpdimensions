# Accounting Dimensions - Quick Reference Guide

## 🚀 Quick Start

### Access the Module
```
http://localhost:8010/static/accounting-dimensions.html
```

## 📊 Dashboard Overview

### Statistics (Top Cards)
- **Total Dimensions**: All dimensions in system
- **Active Dimensions**: Currently enabled
- **Total Values**: All dimension values combined
- **Required Dimensions**: Must be specified on transactions

## 🎯 Common Tasks

### Create a New Dimension

1. Click **"Create Dimension"** button
2. Fill in required fields:
   - **Code**: DEPT, PROJ, CC (max 20 chars)
   - **Name**: Department, Project, Cost Center
   - **Type**: Select from dropdown
3. Configure options:
   - ✅ Active (recommended)
   - ✅ Required on Transactions (optional)
   - ✅ Supports Hierarchy (if needed)
4. Click **"Create Dimension"**

### Add Values to a Dimension

1. Go to **"Dimension Values"** tab
2. Select dimension from dropdown
3. Click **"Create Value"**
4. Enter:
   - **Code**: Unique identifier
   - **Name**: Display name
   - **Parent**: (optional, for hierarchies)
5. Click **"Create Value"**

### Edit a Dimension

1. Find dimension card
2. Click **Edit** icon (pencil)
3. Modify fields
4. Click **"Update Dimension"**

### View Full Details

1. Click **View** icon (eye) on dimension card
2. See complete information:
   - Configuration
   - All values
   - Hierarchy structure

### Delete a Dimension

1. Click **Delete** icon (trash)
2. Confirm deletion
3. ⚠️ Cannot delete if used in transactions

## 📋 Dimension Types Reference

| Type | Use Case | Examples |
|------|----------|----------|
| **Organizational** | Company structure | Departments, Divisions, Subsidiaries |
| **Geographical** | Location tracking | Regions, Countries, Branches |
| **Functional** | Cost/Profit centers | Cost Centers, Profit Centers |
| **Project** | Project tracking | Projects, Campaigns, Initiatives |
| **Product** | Product analysis | Product Lines, Categories, Brands |
| **Customer** | Customer segments | Enterprise, SMB, Retail |
| **Temporal** | Time periods | Fiscal Periods, Seasons, Quarters |
| **Custom** | User-defined | Any custom classification |

## 🏗️ Common Setups

### Setup 1: Basic Department Tracking
```
Dimension: Department
Code: DEPT
Type: Organizational
Scope: Global
Required: Yes

Values:
- SALES: Sales Department
- MKTG: Marketing Department
- FIN: Finance Department
- OPS: Operations Department
- IT: IT Department
```

### Setup 2: Project with Hierarchy
```
Dimension: Project
Code: PROJ
Type: Project
Scope: Global
Hierarchy: Yes (3 levels)

Values:
- CLIENT_PROJ: Client Projects
  - CLIENT_A_P1: Client A - Project 1
  - CLIENT_A_P2: Client A - Project 2
- INTERNAL: Internal Projects
  - INFRA: Infrastructure Upgrade
  - MIGRATION: System Migration
```

### Setup 3: Cost Center Tracking
```
Dimension: Cost Center
Code: CC
Type: Functional
Scope: Branch
Required: Yes

Values:
- CC100: Administration
- CC200: Sales & Marketing
- CC300: Production
- CC400: Research & Development
```

### Setup 4: Geographic Revenue
```
Dimension: Geography
Code: GEO
Type: Geographical
Scope: Global
Hierarchy: Yes (2 levels)

Values:
- NORTH_AM: North America
  - USA: United States
  - CAN: Canada
- EUROPE: Europe
  - UK: United Kingdom
  - DE: Germany
```

## 🔍 Filtering

### Dimensions Tab Filters
- **Type**: Filter by dimension type
- **Status**: Active/Inactive/All
- **Scope**: Global/Branch/Entity/Department

### Values Tab Filters
- **Dimension**: Select specific dimension
- **Status**: Active/Inactive/All

## ✅ Best Practices

### DO:
✅ Use clear, short codes (3-10 characters)
✅ Write descriptive names
✅ Add descriptions for complex dimensions
✅ Mark inactive instead of deleting
✅ Plan hierarchy before enabling
✅ Set appropriate display order
✅ Use required wisely (don't overwhelm users)

### DON'T:
❌ Use spaces in codes
❌ Delete dimensions with transactions
❌ Create too many required dimensions
❌ Use duplicate codes
❌ Enable hierarchy without planning
❌ Mix unrelated concepts in one dimension

## 🎨 Visual Guide

### Dimension Card Colors
- 🔵 **Blue**: Organizational
- 🟢 **Green**: Geographical
- 🟡 **Yellow**: Functional
- 🔵 **Cyan**: Project
- 🟣 **Purple**: Product
- 🟠 **Orange**: Customer
- 🔴 **Red**: Temporal
- ⚫ **Gray**: Custom

### Status Badges
- 🟢 **Green**: Active
- ⚫ **Gray**: Inactive
- 🟡 **Yellow**: Required
- 🔵 **Blue**: Scope indicator

## 🔧 Troubleshooting

### "Dimension code already exists"
**Solution**: Choose a unique code or check inactive dimensions

### "Cannot delete dimension"
**Solution**: Dimension is used in transactions. Mark as inactive instead.

### "No values showing"
**Solution**:
1. Ensure dimension is selected in Values tab
2. Check status filter (might be hiding active/inactive)
3. Verify values exist for selected dimension

### "Cannot create value"
**Solution**: Select a dimension first in the Values tab

## 📱 Mobile Usage

The interface is fully responsive:
- Cards stack vertically
- Filters collapse into dropdowns
- Tables scroll horizontally
- Modals adjust to screen size

## ⌨️ Keyboard Shortcuts

- **Tab**: Navigate between fields
- **Enter**: Submit form (in modals)
- **Esc**: Close modal
- **Ctrl+F**: Browser search (find dimensions)

## 🔐 Required Permissions

To use this module, you need:
- `accounting.dimensions.view` - View dimensions
- `accounting.dimensions.create` - Create new
- `accounting.dimensions.edit` - Modify existing
- `accounting.dimensions.delete` - Remove unused

## 📞 Need Help?

1. Check the full documentation: `docs/accounting-dimensions-module.md`
2. Contact your system administrator
3. Review API documentation at `/docs`

## 🎓 Learning Path

### Beginner
1. Create a simple dimension (Department)
2. Add 3-5 values
3. Practice editing and viewing

### Intermediate
1. Create hierarchical dimension (Projects)
2. Set up parent-child values
3. Configure required dimensions

### Advanced
1. Create full dimensional model
2. Configure account requirements
3. Set up multi-dimensional reporting

---

**Quick Tips**:
- 💡 Start with 2-3 essential dimensions
- 💡 Use codes consistently across dimensions
- 💡 Document dimension purposes
- 💡 Review and clean up quarterly
- 💡 Train users on dimension concepts

**Remember**: Dimensions are powerful tools for financial analysis. Start simple and expand as needed!
