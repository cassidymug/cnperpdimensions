# Accounting Dimensions System

## Overview

The Accounting Dimensions system enables **multi-dimensional business analysis** by allowing you to break down and analyze financial data across various aspects of your business. This provides deep insights into performance across different segments, departments, projects, regions, and other business perspectives.

## What are Accounting Dimensions?

Accounting dimensions are **business perspectives** that help you categorize and analyze your financial transactions. Instead of just looking at "total sales" or "total expenses," you can now see:

- **Sales by Department** (Sales Dept vs Marketing Dept)
- **Expenses by Project** (Project Alpha vs Project Beta)
- **Costs by Geography** (North Region vs South Region)
- **Revenue by Product Line** (Hardware vs Software vs Services)

## Key Concepts

### 1. Dimensions
A **dimension** is a business perspective or categorization method. Examples:
- **Department**: Organizational units (Sales, Marketing, Finance)
- **Project**: Specific initiatives or campaigns
- **Geography**: Regional breakdown (North, South, Central)
- **Product Line**: Different product categories
- **Cost Center**: Operational units for cost allocation

### 2. Dimension Values
**Dimension values** are the specific instances within a dimension:
- For Department dimension: "Sales Dept", "Marketing Dept", "Finance Dept"
- For Project dimension: "Digital Transformation", "Market Expansion"
- For Geography dimension: "Northern Region", "Southern Region"

### 3. Dimension Assignments
**Dimension assignments** link your financial transactions (journal entries) to specific dimension values, enabling analysis across these perspectives.

### 4. Hierarchical Dimensions
Some dimensions support **hierarchies** for more detailed breakdown:
```
Sales Department
├── Retail Sales
└── Wholesale Sales

Operations
├── Warehouse Operations
└── Logistics
```

## System Architecture

### Database Tables

1. **accounting_dimensions**: Defines available dimensions
2. **accounting_dimension_values**: Specific values within each dimension
3. **accounting_dimension_assignments**: Links journal entries to dimension values
4. **dimension_templates**: Pre-configured dimension setups

### Key Features

- **Multi-dimensional Analysis**: Analyze data across multiple dimensions simultaneously
- **Hierarchical Support**: Create parent-child relationships within dimensions
- **Flexible Allocation**: Split transactions across multiple dimension values
- **Validation Rules**: Ensure required dimensions are assigned
- **Automated Assignment**: Set up rules for automatic dimension assignment
- **Comprehensive Reporting**: Generate reports and insights across dimensions

## Getting Started

### 1. Setup the System

Run the setup script to create tables and sample data:

```bash
python scripts/create_dimensions_tables.py
```

This creates sample dimensions:
- **Department** (DEPT): Sales, Marketing, Finance, Operations, IT, HR
- **Project** (PROJ): Digital Transformation, Market Expansion, etc.
- **Geography** (GEO): Northern, Southern, Central regions
- **Product Line** (PROD): Hardware, Software, Services

### 2. API Endpoints

The system provides comprehensive REST API endpoints:

#### Dimensions Management
- `GET /api/v1/accounting/dimensions` - List all dimensions
- `POST /api/v1/accounting/dimensions` - Create new dimension
- `PUT /api/v1/accounting/dimensions/{id}` - Update dimension
- `DELETE /api/v1/accounting/dimensions/{id}` - Delete dimension

#### Dimension Values Management
- `GET /api/v1/accounting/dimensions/{dimension_id}/values` - List values
- `POST /api/v1/accounting/dimensions/{dimension_id}/values` - Create value
- `PUT /api/v1/accounting/dimensions/values/{value_id}` - Update value
- `DELETE /api/v1/accounting/dimensions/values/{value_id}` - Delete value

#### Assignments Management
- `POST /api/v1/accounting/dimensions/assignments` - Create assignment
- `GET /api/v1/accounting/dimensions/assignments` - List assignments
- `PUT /api/v1/accounting/dimensions/assignments/{id}` - Update assignment
- `DELETE /api/v1/accounting/dimensions/assignments/{id}` - Delete assignment

#### Analysis & Reporting
- `POST /api/v1/accounting/dimensions/analysis` - Multi-dimensional analysis
- `GET /api/v1/accounting/dimensions/journal-entries/{id}/validation` - Validate assignments
- `GET /api/v1/accounting/dimensions/stats` - Usage statistics

### 3. FastAPI Documentation

Visit `http://localhost:8010/docs` to explore the interactive API documentation with all dimension endpoints.

## Usage Examples

### Creating a Dimension

```python
# Create a new "Customer Segment" dimension
POST /api/v1/accounting/dimensions
{
    "code": "CUSTSEG",
    "name": "Customer Segment",
    "description": "Customer segmentation for revenue analysis",
    "dimension_type": "customer",
    "scope": "global",
    "is_required": false,
    "supports_hierarchy": false
}
```

### Creating Dimension Values

```python
# Add values to Customer Segment dimension
POST /api/v1/accounting/dimensions/{dimension_id}/values
{
    "code": "ENTERPRISE",
    "name": "Enterprise Customers",
    "description": "Large enterprise clients"
}

POST /api/v1/accounting/dimensions/{dimension_id}/values
{
    "code": "SMB",
    "name": "Small & Medium Business",
    "description": "SMB customer segment"
}
```

### Assigning Dimensions to Transactions

```python
# Assign department and project to a journal entry
POST /api/v1/accounting/dimensions/assignments
{
    "journal_entry_id": "entry-123",
    "dimension_id": "dept-dimension-id",
    "dimension_value_id": "sales-dept-value-id",
    "allocation_percentage": 100.0,
    "assignment_method": "manual"
}

POST /api/v1/accounting/dimensions/assignments
{
    "journal_entry_id": "entry-123",
    "dimension_id": "proj-dimension-id",
    "dimension_value_id": "digital-transformation-id",
    "allocation_percentage": 100.0,
    "assignment_method": "manual"
}
```

### Multi-Dimensional Analysis

```python
# Analyze sales by department and region for Q1
POST /api/v1/accounting/dimensions/analysis
{
    "dimension_values": {
        "dept-dimension-id": ["sales-dept-id", "marketing-dept-id"],
        "geo-dimension-id": ["north-region-id", "south-region-id"]
    },
    "date_from": "2024-01-01T00:00:00",
    "date_to": "2024-03-31T23:59:59",
    "account_types": ["REVENUE"]
}
```

## Business Value

### Before Dimensions
- **Limited Insight**: "Total sales this month: $100,000"
- **No Segmentation**: Can't break down performance by business unit
- **Manual Analysis**: Requires complex spreadsheet work
- **Time-Consuming**: Hours to get departmental breakdown

### After Dimensions
- **Rich Insights**: "Sales Dept: $60k, Marketing: $40k"
- **Multi-Perspective**: See performance by dept + region + project simultaneously
- **Automated Analysis**: Instant multi-dimensional reports
- **Strategic Decision Making**: Data-driven insights for business optimization

### Use Cases

1. **Department Performance Analysis**
   - Which departments are most/least profitable?
   - How do costs vary across organizational units?

2. **Project ROI Tracking**
   - Track revenues and costs for specific projects
   - Compare project performance across time periods

3. **Regional Performance**
   - Identify top-performing geographical regions
   - Optimize resource allocation by location

4. **Product Line Profitability**
   - Understand which products drive the most profit
   - Make informed product portfolio decisions

5. **Customer Segment Analysis**
   - Analyze revenue and costs by customer type
   - Tailor strategies for different segments

## Advanced Features

### Hierarchical Analysis
```
Total Sales: $100,000
├── Sales Department: $80,000
│   ├── Retail Sales: $50,000
│   └── Wholesale Sales: $30,000
└── Marketing Department: $20,000
```

### Allocation Splitting
Split a single transaction across multiple dimension values:
- 60% allocated to Project Alpha
- 40% allocated to Project Beta

### Required Dimensions
Set certain dimensions as required to ensure consistent data entry:
- Department assignment required on all expense entries
- Project assignment required on all consulting revenue

### Automated Assignment Rules
Create rules for automatic dimension assignment:
- All entries from POS system → Retail Sales department
- All vendor payments → Operations department
- All salary entries → Human Resources department

## Configuration Options

### Dimension Types
- **Organizational**: Departments, divisions, subsidiaries
- **Geographical**: Regions, countries, branches
- **Functional**: Cost centers, profit centers
- **Project**: Projects, campaigns, initiatives
- **Product**: Product lines, categories, brands
- **Customer**: Customer segments, channels, types
- **Temporal**: Fiscal periods, seasons, quarters
- **Custom**: User-defined dimensions

### Dimension Scopes
- **Global**: Available across all branches
- **Branch**: Specific to a branch
- **Entity**: Specific to a legal entity
- **Department**: Specific to a department

## Integration Points

### Journal Entries
- Every journal entry can have multiple dimension assignments
- Validation ensures required dimensions are assigned
- Assignment percentages can split transactions

### Reporting
- All financial reports can be filtered by dimensions
- Multi-dimensional analysis capabilities
- Export functionality for external tools

### API Integration
- Complete REST API for external system integration
- Bulk assignment operations
- Real-time validation endpoints

## Performance Considerations

- **Indexing**: Optimized database indexes for fast queries
- **Caching**: Dimension metadata cached for performance
- **Pagination**: Large result sets properly paginated
- **Bulk Operations**: Efficient bulk assignment capabilities

## Security & Permissions

- **Role-Based Access**: Control who can manage dimensions
- **Branch Isolation**: Branch-specific dimensions when needed
- **Audit Trail**: Complete audit trail of all changes
- **Data Validation**: Comprehensive validation rules

## Migration & Maintenance

### Existing Data
- Existing journal entries remain unaffected
- Dimensions can be gradually assigned to historical data
- Migration scripts for bulk historical assignment

### Ongoing Maintenance
- Regular validation reports to ensure data quality
- Performance monitoring of dimension queries
- Cleanup utilities for inactive dimensions

## Future Enhancements

### Planned Features
- **Machine Learning**: Automatic dimension assignment suggestions
- **Advanced Analytics**: Predictive analytics across dimensions
- **Data Visualization**: Built-in charts and dashboards
- **External Integration**: Integration with BI tools
- **Mobile Support**: Mobile-optimized dimension assignment

### Extensibility
- **Custom Fields**: Add custom fields to dimensions
- **Workflow Integration**: Approval workflows for assignments
- **API Webhooks**: Real-time notifications of changes
- **Plugin Architecture**: Custom dimension logic plugins

## Support & Documentation

### Getting Help
- Check the FastAPI documentation at `/docs`
- Review the API examples in this document
- Examine the sample data created by the setup script

### Best Practices
1. **Start Simple**: Begin with 2-3 key dimensions
2. **Plan Hierarchy**: Design your hierarchical structure upfront
3. **Train Users**: Ensure users understand dimension assignment
4. **Regular Reviews**: Periodically review and clean up dimensions
5. **Performance Monitoring**: Monitor query performance as data grows

### Common Issues
- **Missing Assignments**: Use validation endpoints to find incomplete assignments
- **Performance**: Use appropriate filters in analysis queries
- **Hierarchy Errors**: Validate parent-child relationships carefully
- **Allocation Errors**: Ensure allocation percentages sum correctly

---

The Accounting Dimensions system transforms your financial analysis capabilities, providing the insights needed for data-driven business decisions across all aspects of your organization.
