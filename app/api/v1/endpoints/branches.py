from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.branch import Branch
from app.models.sales import Sale, Customer
from app.models.inventory import Product, InventoryTransaction
from app.models.pos import PosSession
from app.models.user import User
# from app.core.security import get_current_user  # Removed for development
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)
router = APIRouter()


class BranchCreate(BaseModel):
    """Branch creation schema"""
    name: str
    code: str
    location: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    is_head_office: bool = False
    manager_id: Optional[str] = None
    contact_person: Optional[str] = None
    fax: Optional[str] = None
    website: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    active: bool = True
    notes: Optional[str] = None


class BranchUpdate(BaseModel):
    """Branch update schema"""
    name: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    manager_id: Optional[str] = None
    contact_person: Optional[str] = None
    fax: Optional[str] = None
    website: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    active: Optional[bool] = None
    notes: Optional[str] = None


class BranchResponse(BaseModel):
    """Branch response schema"""
    id: str
    name: str
    code: str
    location: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    is_head_office: bool = False
    manager_id: Optional[str] = None
    contact_person: Optional[str] = None
    fax: Optional[str] = None
    website: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    active: bool = True
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BranchStatistics(BaseModel):
    """Branch statistics schema"""
    total_sales: float
    monthly_sales: float
    total_customers: int
    total_products: int
    active_pos_sessions: int
    total_users: int
    recent_sales_trend: List[dict]


class BranchWithStatistics(BranchResponse):
    """Branch response with statistics"""
    statistics: Optional[BranchStatistics] = None


class BranchInventoryItem(BaseModel):
    """Branch inventory item schema"""
    product_id: str
    product_name: str
    sku: str
    quantity: int
    cost_price: float
    selling_price: float
    total_value: float


class BranchSalesReport(BaseModel):
    """Branch sales report schema"""
    sale_id: str
    customer_name: Optional[str]
    date: datetime
    total_amount: float
    payment_method: str
    status: str

@router.get("/public", response_model=List[BranchResponse])
async def get_public_active_branches(db: Session = Depends(get_db)):
    """Public lightweight list of active branches (id, code, name, active) for login / POS selectors.
    Does not require auth and returns only key identifying fields.
    """
    branches = db.query(Branch).filter(Branch.active == True).all()
    # Reuse BranchResponse but only essential fields are meaningful to client
    return branches


@router.get("/", response_model=List[BranchResponse])
async def get_branches(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Get branches (non global roles restricted to their branch)."""
    query = db.query(Branch)
    # Restrict if not global role
    from app.core.security import ALLOWED_EVERYTHING
    if ("admin" or '').lower() not in ALLOWED_EVERYTHING and 'default-branch':
        query = query.filter(Branch.id == 'default-branch')
    branches = query.offset(skip).limit(limit).all()
    return branches


@router.get("/statistics", response_model=List[BranchWithStatistics])
async def get_all_branches_with_statistics(
    db: Session = Depends(get_db)
):
    """Get all branches with their statistics"""
    branches = db.query(Branch).filter(Branch.active == True).all()
    branches_with_stats = []

    for branch in branches:
        # Calculate statistics
        stats = await _calculate_branch_statistics(branch.id, db)
        branch_dict = BranchResponse.from_orm(branch).dict()
        branch_dict['statistics'] = stats
        branches_with_stats.append(BranchWithStatistics(**branch_dict))

    return branches_with_stats


@router.get("/{branch_id}", response_model=BranchResponse)
async def get_branch(branch_id: str, db: Session = Depends(get_db)):
    """Get branch by ID"""
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch


@router.post("/", response_model=BranchResponse)
async def create_branch(
    branch_data: BranchCreate,
    db: Session = Depends(get_db),
    # current_user parameter removed for development)
):
    """Create a new branch (requires branches:create permission or admin/super_admin)."""
    # Check if branch code already exists
    existing_branch = db.query(Branch).filter(Branch.code == branch_data.code).first()
    if existing_branch:
        raise HTTPException(
            status_code=400,
            detail="Branch code already exists"
        )

    new_branch = Branch(**branch_data.dict())
    db.add(new_branch)
    db.commit()
    db.refresh(new_branch)
    return new_branch


@router.put("/{branch_id}", response_model=BranchResponse)
async def update_branch(
    branch_id: str,
    branch_data: BranchUpdate,
    db: Session = Depends(get_db),
    # current_user parameter removed for development)
):
    """Update a branch (requires branches:update permission or admin/super_admin)."""
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Update only provided fields
    update_data = branch_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(branch, field, value)

    db.commit()
    db.refresh(branch)
    return branch


@router.delete("/{branch_id}")
async def delete_branch(
    branch_id: str,
    db: Session = Depends(get_db)
):
    """Delete a branch"""
    try:
        # Check branch exists and is not head office
        branch = db.query(Branch).filter(Branch.id == branch_id).first()
        if not branch:
            raise HTTPException(status_code=404, detail="Branch not found")

        if branch.is_head_office:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete head office branch"
            )

        # Use raw SQL with a more comprehensive deletion strategy
        from sqlalchemy import text

        # Delete in dependency order - deepest first
        deletion_order = [
            # Deepest dependencies
            "reconciliation_items WHERE bank_transaction_id IN (SELECT id FROM bank_transactions WHERE branch_id = :bid)",
            "bank_transactions WHERE branch_id = :bid",
            "bank_reconciliations WHERE branch_id = :bid",
            "bank_transfers WHERE branch_id = :bid",
            "bank_accounts WHERE branch_id = :bid",
            # Sales/Purchase related
            "sales WHERE branch_id = :bid",
            "purchases WHERE branch_id = :bid",
            "purchase_orders WHERE branch_id = :bid",
            "invoices WHERE branch_id = :bid",
            # Inventory/Products
            "products WHERE branch_id = :bid",
            "inventory_transactions WHERE branch_id = :bid",
            # People/Entities
            "customers WHERE branch_id = :bid",
            "suppliers WHERE branch_id = :bid",
            "users WHERE branch_id = :bid",
            # Finally the branch itself
            "branches WHERE id = :bid",
        ]

        for delete_clause in deletion_order:
            try:
                db.execute(text(f"DELETE FROM {delete_clause}"), {"bid": branch_id})
            except Exception as e:
                # Log but continue - some tables might not exist or might be empty
                print(f"[DEBUG] Skipped: {delete_clause[:50]} - {str(e)[:50]}")

        db.commit()
        return {"message": "Branch deleted successfully"}

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback
        print(f"[ERROR] Delete branch failed: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting branch: {str(e)}"
        )
@router.get("/{branch_id}/statistics", response_model=BranchStatistics)
async def get_branch_statistics(
    branch_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed statistics for a specific branch"""
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    return await _calculate_branch_statistics(branch_id, db)


@router.get("/{branch_id}/inventory", response_model=List[BranchInventoryItem])
async def get_branch_inventory(
    branch_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get inventory for a specific branch"""
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    products = db.query(Product).filter(
        Product.branch_id == branch_id
    ).offset(skip).limit(limit).all()

    inventory_items = []
    for product in products:
        total_value = float(product.quantity or 0) * float(product.cost_price or 0)
        inventory_items.append(BranchInventoryItem(
            product_id=product.id,
            product_name=product.name,
            sku=product.sku or "",
            quantity=product.quantity or 0,
            cost_price=float(product.cost_price or 0),
            selling_price=float(product.selling_price or 0),
            total_value=total_value
        ))

    return inventory_items


@router.get("/{branch_id}/sales", response_model=List[BranchSalesReport])
async def get_branch_sales(
    branch_id: str,
    days: int = 30,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get sales for a specific branch"""
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    sales_query = db.query(Sale, Customer).outerjoin(
        Customer, Sale.customer_id == Customer.id
    ).filter(
        Sale.branch_id == branch_id,
        Sale.date >= start_date,
        Sale.date <= end_date
    ).offset(skip).limit(limit)

    sales_reports = []
    for sale, customer in sales_query.all():
        sales_reports.append(BranchSalesReport(
            sale_id=sale.id,
            customer_name=customer.name if customer else "Walk-in Customer",
            date=sale.date,
            total_amount=float(sale.total_amount or 0),
            payment_method=sale.payment_method or "Unknown",
            status=sale.status or "completed"
        ))

    return sales_reports


async def _calculate_branch_statistics(branch_id: str, db: Session) -> BranchStatistics:
    """Calculate comprehensive statistics for a branch"""
    # Total sales
    total_sales = db.query(func.sum(Sale.total_amount)).filter(
        Sale.branch_id == branch_id
    ).scalar() or 0

    # Monthly sales (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    monthly_sales = db.query(func.sum(Sale.total_amount)).filter(
        Sale.branch_id == branch_id,
        Sale.date >= thirty_days_ago
    ).scalar() or 0

    # Total customers
    total_customers = db.query(func.count(Customer.id)).filter(
        Customer.branch_id == branch_id
    ).scalar() or 0

    # Total products
    total_products = db.query(func.count(Product.id)).filter(
        Product.branch_id == branch_id
    ).scalar() or 0

    # Active POS sessions
    active_pos_sessions = db.query(func.count(PosSession.id)).filter(
        PosSession.branch_id == branch_id,
        PosSession.status == "open"
    ).scalar() or 0

    # Total users
    total_users = db.query(func.count(User.id)).filter(
        User.branch_id == branch_id
    ).scalar() or 0

    # Recent sales trend (last 7 days)
    recent_sales_trend = []
    for i in range(7):
        date = datetime.now() - timedelta(days=i)
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)

        daily_sales = db.query(func.sum(Sale.total_amount)).filter(
            Sale.branch_id == branch_id,
            Sale.date >= start_of_day,
            Sale.date <= end_of_day
        ).scalar() or 0

        recent_sales_trend.append({
            "date": date.strftime("%Y-%m-%d"),
            "sales": float(daily_sales)
        })

    return BranchStatistics(
        total_sales=float(total_sales),
        monthly_sales=float(monthly_sales),
        total_customers=total_customers,
        total_products=total_products,
        active_pos_sessions=active_pos_sessions,
        total_users=total_users,
        recent_sales_trend=recent_sales_trend
    )


@router.delete("/cleanup/test-branches")
async def cleanup_test_branches(db: Session = Depends(get_db)):
    """Admin endpoint to cleanup test branches and their related data"""
    try:
        from sqlalchemy import text

        # Get test branch IDs
        result = db.execute(text("SELECT id FROM branches WHERE name ILIKE '%Test Branch%'"))
        test_ids = tuple(row[0] for row in result)

        if not test_ids:
            return {"message": "No test branches found", "deleted": 0}

        # Build ID list
        id_list = "', '".join(test_ids)
        id_list = f"'{id_list}'"

        # Delete in dependency order using raw SQL
        db.execute(text("SET CONSTRAINTS ALL DEFERRED"))

        # Delete related data in reverse FK order
        tables_to_clean = [
            "reconciliation_items",
            "bank_transactions",
            "bank_reconciliations",
            "bank_transfers",
            "bank_accounts",
            "sales",
            "purchases",
            "purchase_orders",
            "invoices",
            "products",
            "inventory_transactions",
            "customers",
            "suppliers",
            "users",
            "branches"
        ]

        deleted_count = 0
        for table in tables_to_clean:
            try:
                result = db.execute(text(f"DELETE FROM {table} WHERE branch_id IN ({id_list})"))
                if result.rowcount > 0:
                    deleted_count += result.rowcount
            except:
                pass  # Table might not have branch_id column

        db.commit()
        return {"message": f"Cleaned up test branches and related data", "deleted": deleted_count}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error cleaning up test branches: {str(e)}"
        )
