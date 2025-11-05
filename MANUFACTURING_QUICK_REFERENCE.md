# Quick Reference - Manufacturing & Accounting Integration

## URLs
- **Manufacturing Module**: `http://localhost:8010/static/manufacturing.html`
- **Enhanced Dashboard**: `http://localhost:8010/static/manufacturing-enhanced.html`

## Production Order Creation Flow

### Step 1: Open Manufacturing Module
```
http://localhost:8010/static/manufacturing.html
→ Click "Production Orders" tab
→ Click "+ Create Production Order"
```

### Step 2: Fill Required Fields
```
Product:           [Select from list]
Quantity:          [Enter number]
Cost Center:       [SELECT - REQUIRED] (for accounting)
WIP GL Account:    [SELECT - REQUIRED] (e.g., 1500-100)
Labor GL Account:  [SELECT - REQUIRED] (e.g., 2100-100)
```

### Step 3: Optional Dimensional Fields
```
Project:           [Optional]
Department:        [Optional]
Start Date:        [Optional]
Due Date:          [Optional]
```

### Step 4: Submit
```
Click "Create Order"
Order appears in table with accounting metadata
```

## Posting to Accounting

### Method 1: From Production Orders Tab
```
1. Create/complete production order
2. Click action button on order row
3. Select "Post to Accounting"
4. Confirm dialog
5. Journal entries created automatically
```

### Method 2: From Enhanced Dashboard
```
1. Navigate to manufacturing-enhanced.html
2. Go to "Accounting Bridge" tab
3. Select Cost Center and period
4. Click "Load Bridge Data"
5. Review mapping
6. Click "Post All to GL"
```

## Dimensional Reporting

### Dimensional Analysis
```
1. Go to "Dimensional Analysis" tab in enhanced dashboard
2. Select dimension type (Cost Center, Project, Department, Location)
3. Select period (Current Month, Last Month, etc.)
4. Select grouping (Product, Order, BOM)
5. Click "Analyze"
6. View summary cards and detailed table
```

### Cost Allocation by Dimension
```
Manufacturing Cost = Material Cost + Labor Cost + Overhead Cost

Example:
Cost Center CC-001:
  ├─ Material Cost:  $5,000.00 → WIP Account (1500-100)
  ├─ Labor Cost:     $2,000.00 → Labor Account (2100-100)
  └─ Overhead Cost:  $1,000.00 → WIP Account (1500-100)
  Total:             $8,000.00
```

## Journal Entry Details

### Manual Posting Required for These GL Accounts
- WIP Account (Asset): Debit
- Labor Account (Payable): Debit
- Offset Account (Payable): Credit

### Dimensional Assignment
All journal entries automatically tagged with:
- Cost Center (primary)
- Project (if set)
- Department (if set)
- Location (if set)

### Example Journal Entry
```
Date:        2025-10-22
Reference:   MFG-PO-12345-WIP
GL Account:  1500-100 (WIP)
Debit:       $6,000.00
Credit:      $0.00
Dimensions:  CC-001 (Cost Center), PROJ-001 (Project)
Status:      Posted
Source:      Manufacturing
```

## Reconciliation

### Running Reconciliation
```
1. Go to "Reconciliation" tab in enhanced dashboard
2. Select month (YYYY-MM format)
3. Click "Reconcile"
4. Review results:
   ├─ Reconciled: Manufacturing = GL
   └─ Variance: Mismatch found
```

### Variance Analysis
```
Variance > $0.01 indicates:
1. Unposted production orders
2. GL adjustments made outside system
3. Cost recording errors
4. Missing dimension assignments
```

### Export Reconciliation Report
```
1. Complete reconciliation
2. Click "Export Report"
3. Download as Excel
4. Share with accounting team
```

## API Quick Reference

### Create Production Order (POST)
```bash
curl -X POST http://localhost:8010/api/v1/manufacturing/production-orders/ \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "123e4567-e89b-12d3-a456-426614174000",
    "quantity": 100,
    "cost_center_id": "cc-001",
    "wip_account_id": "1500-100",
    "labor_account_id": "2100-100"
  }'
```

### Post to Accounting (POST)
```bash
curl -X POST http://localhost:8010/api/v1/manufacturing/production-orders/{id}/post-accounting \
  -H "Content-Type: application/json"
```

### Get Dimensional Analysis (GET)
```bash
curl -X GET "http://localhost:8010/api/v1/manufacturing/dimensional-analysis?type=cost_center&period=current_month&group_by=product"
```

### Run Reconciliation (GET)
```bash
curl -X GET "http://localhost:8010/api/v1/manufacturing/reconcile?period=2025-10"
```

## Accounting Accounts Required

### Typically Needed
```
Asset Accounts:
  1500-100    Work in Process (WIP)
  1500-200    Finished Goods

Liability Accounts:
  2100-100    Accrued Labor
  2100-200    Manufacturing Payable

Expense Accounts:
  5000-100    Cost of Goods Sold (COGS)
  5000-200    Manufacturing Overhead
```

## Common Issues & Solutions

### Issue: GL Accounts Not Showing
**Solution**: GL accounts must exist in chart of accounts. Create them before production order.

### Issue: Dimension Not Tracking
**Solution**: Ensure dimension value exists in system and is assigned to production order.

### Issue: Reconciliation Shows Variance
**Solution**: Check for:
1. Unposted production orders in period
2. Manual GL entries not from manufacturing
3. Cost corrections after posting
4. Missing labor costs

### Issue: Can't Post Production Order
**Solution**: Verify:
1. WIP GL account is set
2. Labor GL account is set
3. Cost center is selected
4. Production order is in draft status

## Database Queries for Verification

### Check Production Order with Dimensions
```sql
SELECT id, product_id, quantity, status,
       cost_center_id, project_id, department_id,
       wip_account_id, labor_account_id
FROM production_orders
WHERE id = '123e4567-e89b-12d3-a456-426614174000';
```

### Check Journal Entries from Manufacturing
```sql
SELECT je.id, je.date_posted, ac.code, ac.name,
       je.debit_amount, je.credit_amount, je.reference
FROM journal_entries je
JOIN accounting_codes ac ON je.accounting_code_id = ac.id
WHERE je.reference LIKE 'MFG-%'
ORDER BY je.date_posted DESC;
```

### Check Dimension Assignments
```sql
SELECT jd.journal_entry_id, av.value, ad.code
FROM accounting_dimension_assignments jd
JOIN dimension_values av ON jd.dimension_value_id = av.id
JOIN accounting_dimensions ad ON av.dimension_id = ad.id
WHERE jd.journal_entry_id IN (
  SELECT id FROM journal_entries WHERE reference LIKE 'MFG-%'
);
```

## Support & Documentation

- **Implementation Guide**: `MANUFACTURING_ACCOUNTING_INTEGRATION.md`
- **Code Examples**: `MANUFACTURING_ACCOUNTING_EXAMPLES.md`
- **API Documentation**: Available at `/api/v1/docs` (Swagger)
- **Database Schema**: Check migration files in `migrations/` folder

## System Requirements

- FastAPI backend running on `localhost:8010`
- Manufacturing module database tables created
- GL accounts configured in chart of accounts
- Dimension values configured in system
- User with accounting module permissions

