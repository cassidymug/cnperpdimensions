# Manufacturing Accounting Integration - Implementation Examples

## Backend Service Implementation

### Manufacturing Service Enhancement

```python
# app/services/manufacturing_service.py

from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.accounting import JournalEntry, AccountingEntry
from app.models.production_order import ProductionOrder
from app.models.cost_accounting import ManufacturingCost
from app.models.accounting_dimensions import AccountingDimensionAssignment

class ManufacturingService:
    def __init__(self, db: Session):
        self.db = db

    def post_to_accounting(self, production_order_id: str, user_id: str = None) -> dict:
        """
        Post manufacturing costs to General Ledger with dimensional assignments

        Flow:
        1. Get production order with all costs
        2. Retrieve mapped GL accounts (WIP, Labor, Overhead)
        3. Create accounting entry header
        4. Create journal entry lines for each cost element
        5. Apply dimension assignments
        6. Link back to production order
        7. Update posting status
        """

        # Fetch production order
        po = self.db.query(ProductionOrder).filter(
            ProductionOrder.id == production_order_id
        ).first()

        if not po:
            raise ValueError(f"Production order {production_order_id} not found")

        if po.posting_status == 'posted':
            raise ValueError(f"Production order already posted")

        # Get manufacturing costs
        mfg_costs = self.db.query(ManufacturingCost).filter(
            ManufacturingCost.production_order_id == production_order_id
        ).all()

        if not mfg_costs:
            raise ValueError("No manufacturing costs found for this order")

        # Validate GL accounts are set
        if not po.wip_account_id or not po.labor_account_id:
            raise ValueError("WIP and Labor GL accounts must be set")

        # Calculate totals
        total_material = sum(Decimal(str(c.material_cost or 0)) for c in mfg_costs)
        total_labor = sum(Decimal(str(c.labor_cost or 0)) for c in mfg_costs)
        total_overhead = sum(Decimal(str(c.overhead_cost or 0)) for c in mfg_costs)
        total = total_material + total_labor + total_overhead

        # Create accounting entry header
        acct_entry = AccountingEntry(
            entry_type='MANUFACTURING_POSTING',
            entry_date=datetime.now(),
            total_debit=total,
            total_credit=total,
            reference=f"MFG-{po.id}",
            created_by_user_id=user_id,
            branch_id=po.branch_id
        )
        self.db.add(acct_entry)
        self.db.flush()

        journal_entries = []

        # Create WIP debit entry (Material + Overhead)
        wip_amount = total_material + total_overhead
        wip_entry = JournalEntry(
            accounting_code_id=po.wip_account_id,
            accounting_entry_id=acct_entry.id,
            debit_amount=float(wip_amount),
            credit_amount=0,
            entry_type='DEBIT',
            description=f"Manufacturing WIP: {po.product.name} - {po.quantity} units",
            reference=f"MFG-{po.id}-WIP",
            date_posted=datetime.now().date(),
            branch_id=po.branch_id,
            created_by_user_id=user_id
        )
        self.db.add(wip_entry)
        journal_entries.append(wip_entry)

        # Create Labor debit entry
        labor_entry = JournalEntry(
            accounting_code_id=po.labor_account_id,
            accounting_entry_id=acct_entry.id,
            debit_amount=float(total_labor),
            credit_amount=0,
            entry_type='DEBIT',
            description=f"Manufacturing Labor: {po.product.name}",
            reference=f"MFG-{po.id}-LABOR",
            date_posted=datetime.now().date(),
            branch_id=po.branch_id,
            created_by_user_id=user_id
        )
        self.db.add(labor_entry)
        journal_entries.append(labor_entry)

        # Create offset credit entry (payable)
        # Get payable account (assumes account code exists)
        payable_account = self.db.query(AccountingCode).filter(
            AccountingCode.category == 'Current Liability'
        ).first()

        if payable_account:
            offset_entry = JournalEntry(
                accounting_code_id=payable_account.id,
                accounting_entry_id=acct_entry.id,
                debit_amount=0,
                credit_amount=float(total),
                entry_type='CREDIT',
                description=f"Mfg Costs Payable: {po.product.name}",
                reference=f"MFG-{po.id}-PAYABLE",
                date_posted=datetime.now().date(),
                branch_id=po.branch_id,
                created_by_user_id=user_id
            )
            self.db.add(offset_entry)
            journal_entries.append(offset_entry)

        self.db.flush()

        # Apply dimension assignments to all journal entries
        if po.cost_center_id:
            for je in journal_entries:
                dim_assign = AccountingDimensionAssignment(
                    journal_entry_id=je.id,
                    dimension_value_id=po.cost_center_id,
                    assignment_date=datetime.now(),
                    is_primary=True
                )
                self.db.add(dim_assign)

        if po.project_id:
            for je in journal_entries:
                dim_assign = AccountingDimensionAssignment(
                    journal_entry_id=je.id,
                    dimension_value_id=po.project_id,
                    assignment_date=datetime.now(),
                    is_primary=False
                )
                self.db.add(dim_assign)

        # Update production order status
        po.posting_status = 'posted'
        po.last_posted_date = datetime.now()

        self.db.commit()

        return {
            "entries_created": len(journal_entries),
            "journal_entry_ids": [je.id for je in journal_entries],
            "total_amount": float(total),
            "reference": f"MFG-{po.id}",
            "status": "success"
        }

    def reconcile_manufacturing_costs(self, period: str, cost_center_id: str = None) -> dict:
        """
        Reconcile manufacturing costs with GL balances by dimension

        Compares:
        - Total manufacturing costs recorded
        - Total GL account balances
        - Detects variances and reports them
        """

        from dateutil.parser import parse

        # Parse period (YYYY-MM format)
        period_date = parse(period)
        start_date = period_date.replace(day=1)

        # Calculate last day of month
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1, day=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1, day=1)
        end_date = end_date - timedelta(days=1)

        # Get manufacturing costs for period
        mfg_costs = self.db.query(
            ManufacturingCost,
            ProductionOrder.cost_center_id
        ).join(
            ProductionOrder,
            ManufacturingCost.production_order_id == ProductionOrder.id
        ).filter(
            ManufacturingCost.date >= start_date,
            ManufacturingCost.date <= end_date
        )

        if cost_center_id:
            mfg_costs = mfg_costs.filter(ProductionOrder.cost_center_id == cost_center_id)

        mfg_costs = mfg_costs.all()

        # Group by dimension
        by_dimension = {}
        for cost, cc_id in mfg_costs:
            if cc_id not in by_dimension:
                by_dimension[cc_id] = {
                    'mfg_cost': 0,
                    'dimension': cc_id
                }
            by_dimension[cc_id]['mfg_cost'] += float(cost.total_cost or 0)

        # Get GL balances for same period
        gl_balances = {}
        for dimension_id, data in by_dimension.items():
            # Query GL accounts with this dimension assignment
            gl_total = self.db.query(func.sum(JournalEntry.debit_amount) - func.sum(JournalEntry.credit_amount)).filter(
                JournalEntry.date_posted >= start_date,
                JournalEntry.date_posted <= end_date,
                JournalEntry.dimension_assignments.any(
                    AccountingDimensionAssignment.dimension_value_id == dimension_id
                )
            ).scalar() or 0

            gl_balances[dimension_id] = float(gl_total)

        # Build reconciliation report
        reconciliation = []
        for dim_id, mfg_data in by_dimension.items():
            mfg_cost = mfg_data['mfg_cost']
            gl_balance = gl_balances.get(dim_id, 0)
            variance = abs(mfg_cost - gl_balance)
            pct_diff = (variance / mfg_cost * 100) if mfg_cost > 0 else 0

            status = "Reconciled" if variance < 0.01 else "Variance"

            reconciliation.append({
                'dimension': dim_id,
                'mfg_cost': mfg_cost,
                'gl_balance': gl_balance,
                'variance': variance,
                'pct_diff': pct_diff,
                'status': status,
                'notes': f"Variance of ${variance:.2f}" if variance > 0.01 else ""
            })

        return {
            'period': period,
            'reconciliation': reconciliation,
            'total_variance': sum(r['variance'] for r in reconciliation),
            'fully_reconciled': all(r['status'] == 'Reconciled' for r in reconciliation)
        }
```

## API Endpoint Implementation

```python
# app/api/v1/endpoints/manufacturing.py

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.manufacturing_service import ManufacturingService

router = APIRouter()

@router.post("/production-orders/{production_order_id}/post-accounting")
def post_production_to_accounting(
    production_order_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Post production order costs to General Ledger"""
    service = ManufacturingService(db)
    try:
        result = service.post_to_accounting(production_order_id, current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/production-orders/{production_order_id}/accounting-details")
def get_production_accounting_details(
    production_order_id: str,
    db: Session = Depends(get_db)
):
    """Get accounting details for production order"""
    po = db.query(ProductionOrder).filter(
        ProductionOrder.id == production_order_id
    ).first()

    if not po:
        raise HTTPException(status_code=404, detail="Production order not found")

    # Get GL accounts
    wip_account = db.query(AccountingCode).filter(
        AccountingCode.id == po.wip_account_id
    ).first()

    labor_account = db.query(AccountingCode).filter(
        AccountingCode.id == po.labor_account_id
    ).first()

    # Get dimensions
    cost_center = db.query(DimensionValue).filter(
        DimensionValue.id == po.cost_center_id
    ).first()

    return {
        'wip_account': f"{wip_account.code} - {wip_account.name}" if wip_account else None,
        'labor_account': f"{labor_account.code} - {labor_account.name}" if labor_account else None,
        'dimensions': {
            'cost_center': cost_center.value if cost_center else None,
            'project': None,  # Similar lookup
            'department': None
        },
        'total_cost': float(sum(c.total_cost for c in po.costs)),
        'posting_status': po.posting_status,
        'last_posted_date': po.last_posted_date
    }

@router.get("/dimensional-analysis")
def get_dimensional_analysis(
    type: str = Query("cost_center"),
    period: str = Query("current_month"),
    group_by: str = Query("product"),
    db: Session = Depends(get_db)
):
    """Get dimensional analysis of manufacturing costs"""

    # Query manufacturing costs with dimensions
    query = db.query(ManufacturingCost).join(ProductionOrder)

    # Apply period filter
    from datetime import datetime, timedelta
    now = datetime.now()

    if period == "current_month":
        start_date = now.replace(day=1)
    elif period == "last_month":
        start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
    else:
        start_date = now.replace(month=1, day=1)

    query = query.filter(ManufacturingCost.date >= start_date)

    costs = query.all()

    # Group by dimension
    grouped = {}
    for cost in costs:
        key = getattr(cost.production_order, type)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(cost)

    # Build response
    details = []
    for dim_value, cost_list in grouped.items():
        details.append({
            'dimension': str(dim_value),
            'product': cost_list[0].product.name,
            'order_number': cost_list[0].production_order.order_number,
            'quantity': sum(c.quantity for c in cost_list),
            'material_cost': sum(float(c.material_cost or 0) for c in cost_list),
            'labor_cost': sum(float(c.labor_cost or 0) for c in cost_list),
            'overhead_cost': sum(float(c.overhead_cost or 0) for c in cost_list),
            'total_cost': sum(float(c.total_cost or 0) for c in cost_list)
        })

    return {
        'summary': {
            'total_orders': len(costs),
            'total_quantity': sum(c.quantity for c in costs),
            'total_cost': sum(float(c.total_cost or 0) for c in costs),
            'unique_dims': len(grouped)
        },
        'details': details
    }

@router.get("/reconcile")
def reconcile_manufacturing(
    period: str = Query(...),
    cost_center: str = Query(None),
    db: Session = Depends(get_db)
):
    """Reconcile manufacturing costs with GL"""
    service = ManufacturingService(db)
    return service.reconcile_manufacturing_costs(period, cost_center)
```

## Frontend Usage Example

```javascript
// Load dimensional analysis
async function loadDimensionalAnalysis() {
    const dimType = document.getElementById('dimType').value;
    const period = document.getElementById('dimPeriod').value;
    const groupBy = document.getElementById('dimGroupBy').value;

    const res = await fetch(
        `/api/v1/manufacturing/dimensional-analysis?type=${dimType}&period=${period}&group_by=${groupBy}`
    );
    const data = await res.json();

    // Display summary
    const summaryDiv = document.getElementById('dimSummaryCards');
    summaryDiv.innerHTML = `
        <div class="col-md-3">
            <div class="summary-card">
                <div class="summary-value">${data.summary.total_orders}</div>
                <div>Total Orders</div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="summary-card">
                <div class="summary-value">$${data.summary.total_cost.toFixed(2)}</div>
                <div>Total Cost</div>
            </div>
        </div>
    `;

    // Display details in table
    const tbody = document.querySelector('#dimTable tbody');
    tbody.innerHTML = data.details.map(item => `
        <tr>
            <td>${item.dimension}</td>
            <td>${item.product}</td>
            <td>${item.order_number}</td>
            <td>${item.quantity}</td>
            <td>$${item.material_cost.toFixed(2)}</td>
            <td>$${item.labor_cost.toFixed(2)}</td>
            <td>$${item.overhead_cost.toFixed(2)}</td>
            <td><strong>$${item.total_cost.toFixed(2)}</strong></td>
        </tr>
    `).join('');
}

// Post to accounting
async function postToAccounting() {
    const productionOrderId = getCurrentProductionOrderId();

    const res = await fetch(
        `/api/v1/manufacturing/production-orders/${productionOrderId}/post-accounting`,
        { method: 'POST' }
    );

    const data = await res.json();

    if (res.ok) {
        showAlert(`Posted ${data.entries_created} journal entries`, 'success');
        // Reload data
        await loadJournalEntries();
    } else {
        showAlert('Error: ' + data.detail, 'danger');
    }
}
```

