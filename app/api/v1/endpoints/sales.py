"""Clean sales & invoices endpoints (branch scoped)."""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func, and_
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime, timedelta
import uuid

from app.core.database import get_db
# from app.core.security import (
#     get_current_user,
#     require_any,
#     enforce_branch_scope,
#     require_branch_match,
# )  # Commented out for development
from app.models.sales import Customer, Sale, SaleItem, Invoice, InvoiceItem
from app.models.inventory import Product
from app.models.branch import Branch
from app.models.cash_management import CashSubmission, FloatAllocation, CashSubmissionStatus, FloatAllocationStatus
from app.models.accounting import JournalEntry, AccountingEntry
from app.models.accounting_dimensions import AccountingDimensionValue
from app.services.daily_sales_service import DailySalesService
from app.services.ifrs_accounting_service import IFRSAccountingService
from app.services.app_setting_service import AppSettingService
from app.services.sales_service import SalesService
from decimal import Decimal

# Sales endpoints: Authentication removed for development
router = APIRouter(
    # dependencies=[Depends(# Security check removed for development)]  # Commented out for development
)


# Schemas -----------------------------------------------------------------
class CustomerBase(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    customer_type: Optional[str] = "retail"
    active: Optional[bool] = True
    vat_reg_number: Optional[str] = None
    credit_limit: Optional[float] = Field(0.0, ge=0, description="Credit limit must be non-negative")
    payment_terms: Optional[int] = 30
    contact_person: Optional[str] = None
    account_balance: Optional[float] = 0.0


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None
    customer_type: Optional[str] = None
    vat_reg_number: Optional[str] = None
    credit_limit: Optional[float] = Field(None, ge=0, description="Credit limit must be non-negative")
    payment_terms: Optional[int] = None
    contact_person: Optional[str] = None


class CustomerResponse(CustomerBase):
    id: str
    branch_id: Optional[str]
    account_balance: Optional[float] = 0.0

    model_config = ConfigDict(from_attributes=True)


class SaleItemCreate(BaseModel):
    product_id: str
    quantity: int = Field(gt=0)
    selling_price: float
    vat_rate: float = 0.0
    discount_amount: float = 0.0
    discount_percentage: float = 0.0


class SaleItemResponse(SaleItemCreate):
    id: str
    vat_amount: float
    total_amount: float
    product_name: Optional[str]
    product_sku: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class SaleCreate(BaseModel):
    customer_id: Optional[str] = None
    payment_method: str
    currency: str = "USD"
    amount_tendered: float = 0.0
    discount_amount: float = 0.0
    discount_percentage: float = 0.0
    notes: Optional[str] = None
    branch_id: Optional[str] = None
    salesperson_id: Optional[str] = None
    items: List[SaleItemCreate]


class SaleResponse(SaleCreate):
    id: str
    reference: str
    total_amount: float
    total_amount_ex_vat: float
    total_vat_amount: float
    change_given: float
    status: str
    date: datetime
    customer_name: Optional[str] = None
    salesperson_name: Optional[str] = None
    branch_name: Optional[str] = None
    items_count: int
    items: List[SaleItemResponse] = []


class InvoiceItemCreate(BaseModel):
    product_id: str
    quantity: float
    price: float
    vat_rate: float = 0.0
    discount_amount: float = 0.0
    discount_percentage: float = 0.0


class InvoiceItemResponse(InvoiceItemCreate):
    id: str
    vat_amount: float
    total: float
    product_name: Optional[str]
    product_sku: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class InvoiceCreate(BaseModel):
    customer_id: str
    due_date: Optional[date] = None
    payment_terms: int = 30
    discount_amount: float = 0.0
    discount_percentage: float = 0.0
    notes: Optional[str] = None
    items: List[InvoiceItemCreate]


class InvoiceResponse(InvoiceCreate):
    id: str
    invoice_number: str
    date: date
    status: str
    total: float
    total_vat_amount: float
    total_amount: float
    amount_paid: float
    customer_name: Optional[str] = None
    items_count: int


# Cash Management Schemas -------------------------------------------------
class CashSubmissionCreate(BaseModel):
    """Schema for creating a cash submission from salesperson to manager/accounting"""
    salesperson_id: str
    amount: float = Field(gt=0, description="Amount must be positive")
    submission_date: date
    branch_id: Optional[str] = None
    received_by_id: Optional[str] = None
    notes: Optional[str] = None


class CashSubmissionResponse(BaseModel):
    """Response schema for cash submission"""
    id: str
    salesperson_id: str
    salesperson_name: Optional[str] = None
    received_by_id: Optional[str] = None
    received_by_name: Optional[str] = None
    amount: float
    submission_date: date
    branch_id: Optional[str] = None
    journal_entry_id: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FloatAllocationCreate(BaseModel):
    """Schema for allocating float/change to a cashier"""
    cashier_id: str
    float_amount: float = Field(gt=0, description="Float amount must be positive")
    allocation_date: date
    branch_id: Optional[str] = None
    allocated_by_id: Optional[str] = None
    notes: Optional[str] = None


class FloatReturnCreate(BaseModel):
    """Schema for recording a float return"""
    amount_returned: float = Field(gt=0, description="Return amount must be positive")
    return_date: date
    notes: Optional[str] = None


class FloatAllocationResponse(BaseModel):
    """Response schema for float allocation"""
    id: str
    cashier_id: str
    cashier_name: Optional[str] = None
    allocated_by_id: Optional[str] = None
    allocated_by_name: Optional[str] = None
    float_amount: float
    amount_returned: float
    allocation_date: date
    return_date: Optional[date] = None
    branch_id: Optional[str] = None
    allocation_journal_entry_id: Optional[str] = None
    return_journal_entry_id: Optional[str] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Customer Endpoints -------------------------------------------------------
@router.get("/customers", response_model=List[CustomerResponse])
async def get_customers(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active: Optional[bool] = Query(None),
    customer_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    query = db.query(Customer)
    # # query = # Security check removed for development  # Removed for development  # Removed for development
    if customer_type:
        query = query.filter(Customer.customer_type == customer_type)
    if active is not None:
        query = query.filter(Customer.active == active)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Customer.name.ilike(like),
                Customer.email.ilike(like),
                Customer.phone.ilike(like),
            )
        )
    return query.offset(skip).limit(limit).all()


@router.post("/customers", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    # Get the first active branch for development
    branch = db.query(Branch).filter(Branch.active == True).first()
    if not branch:
        raise HTTPException(status_code=400, detail="No active branch found")

    customer = Customer(**customer_data.dict(), branch_id=branch.id)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development,
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    # require_branch_match(..., current_user)  # Removed for development
    return customer


@router.put("/customers/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: str,
    customer_data: CustomerUpdate,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development,
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    # require_branch_match(..., current_user)  # Removed for development
    for field, value in customer_data.dict(exclude_unset=True).items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/customers/{customer_id}")
async def delete_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development,
):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    # require_branch_match(..., current_user)  # Removed for development
    # Soft-delete: mark customer as inactive instead of deleting to preserve referential integrity
    try:
        customer.active = False
        db.commit()
        return {"message": "Customer deactivated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deactivating customer: {str(e)}")


@router.get("/customers/{customer_id}/balance")
async def get_customer_balance(
    customer_id: str,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development,
):
    """Get customer account balance"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    # require_branch_match(..., current_user)  # Removed for development

    # Return the stored account balance from the customer record
    return {
        "customer_id": customer_id,
        "balance": float(customer.account_balance or 0),
        "currency": "BWP"  # Default currency
    }


# Sales Endpoints ----------------------------------------------------------
@router.get("", response_model=List[SaleResponse])
@router.get("/", response_model=List[SaleResponse])
async def get_sales(
    response: Response,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    branch_id: Optional[str] = Query(None, description="Filter by branch id"),
    cashier_id: Optional[str] = Query(None, description="Filter by cashier/salesperson id"),
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development,
):
    query = db.query(Sale)
    # query = # Security check removed for development  # Removed for development
    if status:
        query = query.filter(Sale.status == status)
    if customer_id:
        query = query.filter(Sale.customer_id == customer_id)
    if start_date:
        # Convert date to datetime range start
        query = query.filter(Sale.date >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        # Convert date to datetime range end
        query = query.filter(Sale.date <= datetime.combine(end_date, datetime.max.time()))
    if search:
        like = f"%{search}%"
        query = query.filter(or_(Sale.reference.ilike(like), Sale.notes.ilike(like)))
    if branch_id:
        query = query.filter(Sale.branch_id == branch_id)
    if cashier_id:
        # Field is salesperson_id on the Sale model
        query = query.filter(Sale.salesperson_id == cashier_id)
    # Total count for pagination
    total_count = query.count()
    response.headers["X-Total-Count"] = str(total_count)

    sales = query.order_by(Sale.date.desc()).offset(skip).limit(limit).all()
    result: List[dict] = []
    for sale in sales:
        # Build salesperson name if available
        salesperson_name = None
        if getattr(sale, "salesperson", None):
            try:
                first = getattr(sale.salesperson, "first_name", None)
                last = getattr(sale.salesperson, "last_name", None)
                username = getattr(sale.salesperson, "username", None)
                parts = [p for p in [first, last] if p]
                salesperson_name = " ".join(parts) if parts else username
            except Exception:
                salesperson_name = None
        sale_dict = {
            "id": sale.id,
            "reference": sale.reference,
            "customer_id": sale.customer_id,
            "customer_name": sale.customer.name if sale.customer else "Walk-in Customer",
            "payment_method": sale.payment_method,
            "currency": sale.currency,
            "total_amount": float(sale.total_amount or 0),
            "total_amount_ex_vat": float(sale.total_amount_ex_vat or 0),
            "total_vat_amount": float(sale.total_vat_amount or 0),
            "amount_tendered": float(sale.amount_tendered or 0),
            "change_given": float(sale.change_given or 0),
            "discount_amount": float(sale.discount_amount or 0),
            "discount_percentage": float(sale.discount_percentage or 0),
            "status": sale.status,
            "date": sale.date,
            "notes": sale.notes,
            "salesperson_name": salesperson_name,
            "items_count": len(sale.sale_items),
            "items": [],
        }
        for item in sale.sale_items:
            sale_dict["items"].append(
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_name": item.product.name if item.product else "Unknown Product",
                    "product_sku": item.product.sku if item.product else "",
                    "quantity": item.quantity,
                    "selling_price": float(item.selling_price or 0),
                    "vat_rate": float(item.vat_rate or 0),
                    "vat_amount": float(item.vat_amount or 0),
                    "discount_amount": float(item.discount_amount or 0),
                    "discount_percentage": float(item.discount_percentage or 0),
                    "total_amount": float(item.total_amount or 0),
                }
            )
        result.append(sale_dict)
    return result


@router.get("/statistics")
async def get_sales_statistics(
    branch_id: Optional[str] = Query(None, description="Filter by branch id"),
    cashier_id: Optional[str] = Query(None, description="Filter by cashier/salesperson id"),
    start_date: Optional[date] = Query(None, description="Optional start date for range"),
    end_date: Optional[date] = Query(None, description="Optional end date for range"),
    db: Session = Depends(get_db),
):
    """Return basic statistics used by the sales dashboard cards.

    Response shape matches sales.html expectations:
      {
        "today_sales": { "amount": float },
        "total_sales": { "count": int },
        "customer_count": int,
        "monthly_revenue": float
      }
    All metrics support optional branch and cashier filters; date range (if provided)
    will constrain total_sales count; today_sales is always for the current day; monthly_revenue is for the current month.
    """
    try:
        base_filters = []
        if branch_id:
            base_filters.append(Sale.branch_id == branch_id)
        if cashier_id:
            base_filters.append(Sale.salesperson_id == cashier_id)

        # Today's sales total
        today = datetime.utcnow().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        today_query = db.query(func.coalesce(func.sum(Sale.total_amount), 0.0))
        if base_filters:
            today_query = today_query.filter(and_(*base_filters))
        today_query = today_query.filter(Sale.date >= today_start, Sale.date <= today_end)
        today_amount = float(today_query.scalar() or 0.0)

        # Total sales count (optionally constrained by provided range)
        count_query = db.query(func.count(Sale.id))
        if base_filters:
            count_query = count_query.filter(and_(*base_filters))
        if start_date:
            count_query = count_query.filter(Sale.date >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            count_query = count_query.filter(Sale.date <= datetime.combine(end_date, datetime.max.time()))
        total_count = int(count_query.scalar() or 0)

        # Customer count (apply branch filter if provided)
        cust_query = db.query(func.count(func.distinct(Customer.id)))
        if branch_id:
            cust_query = cust_query.filter(Customer.branch_id == branch_id)
        customer_count = int(cust_query.scalar() or 0)

        # Monthly revenue for current month
        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)
        # Compute first day of next month then subtract microsecond
        if now.month == 12:
            next_month = datetime(now.year + 1, 1, 1)
        else:
            next_month = datetime(now.year, now.month + 1, 1)
        month_end = next_month - timedelta(microseconds=1)
        month_query = db.query(func.coalesce(func.sum(Sale.total_amount), 0.0))
        if base_filters:
            month_query = month_query.filter(and_(*base_filters))
        month_query = month_query.filter(Sale.date >= month_start, Sale.date <= month_end)
        monthly_revenue = float(month_query.scalar() or 0.0)

        return {
            "today_sales": {"amount": today_amount},
            "total_sales": {"count": total_count},
            "customer_count": customer_count,
            "monthly_revenue": monthly_revenue,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sales statistics: {e}")


@router.post("", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
async def create_sale(
    sale_data: SaleCreate,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development,
):
    # In development, assign to the first active branch to ensure branch filters work
    branch = db.query(Branch).filter(Branch.active == True).first()
    if not branch:
        raise HTTPException(status_code=400, detail="No active branch available to assign sale")

    reference = f"SALE-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8]}"
    subtotal = 0.0
    total_vat = 0.0
    for item in sale_data.items:
        item_total = item.quantity * item.selling_price
        item_discount = item_total * (item.discount_percentage / 100) + item.discount_amount
        item_subtotal = item_total - item_discount
        item_vat = item_subtotal * (item.vat_rate / 100)
        subtotal += item_subtotal
        total_vat += item_vat

    sale_discount = subtotal * (sale_data.discount_percentage / 100) + sale_data.discount_amount
    final_subtotal = subtotal - sale_discount
    final_vat = total_vat * (final_subtotal / subtotal) if subtotal > 0 else 0
    total_amount = final_subtotal + final_vat
    change_given = sale_data.amount_tendered - total_amount

    sale = Sale(
        reference=reference,
        customer_id=sale_data.customer_id,
        payment_method=sale_data.payment_method,
        currency=sale_data.currency,
        total_amount=total_amount,
        total_amount_ex_vat=final_subtotal,
        total_vat_amount=final_vat,
        amount_tendered=sale_data.amount_tendered,
        change_given=change_given,
        discount_amount=sale_discount,
        discount_percentage=sale_data.discount_percentage,
        status="completed",
        date=datetime.now(),
        notes=sale_data.notes,
        branch_id=sale_data.branch_id or branch.id,
        salesperson_id=sale_data.salesperson_id,
    )
    db.add(sale)
    db.flush()

    for item in sale_data.items:
        item_total = item.quantity * item.selling_price
        item_discount = item_total * (item.discount_percentage / 100) + item.discount_amount
        item_subtotal = item_total - item_discount
        item_vat = item_subtotal * (item.vat_rate / 100)
        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=item.product_id,
            quantity=item.quantity,
            selling_price=item.selling_price,
            vat_rate=item.vat_rate,
            vat_amount=item_vat,
            discount_amount=item.discount_amount,
            discount_percentage=item.discount_percentage,
            total_amount=item_subtotal + item_vat,
        )
        db.add(sale_item)
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.quantity = max(0, product.quantity - item.quantity)

    db.commit()
    db.refresh(sale)

    # Create IFRS-compliant journal entries for the sale
    try:
        ifrs_service = IFRSAccountingService(db)
        bank_account_id = None
        if (sale.payment_method or '').lower() == 'card':
            # Load default card bank account from settings
            settings_svc = AppSettingService(db)
            bank_account_id = settings_svc.get_branch_default_card_bank_account(sale.branch_id)
            if not bank_account_id:
                bank_account_id = settings_svc.get_global_default_card_bank_account()
        journal_entries = ifrs_service.create_sale_journal_entries(sale, bank_account_id=bank_account_id)
        print(f"Successfully created {len(journal_entries)} IFRS journal entries for sale {sale.id}")
    except Exception as e:
        # Log the error but do not fail the sale creation
        print(f"Warning: Failed to create IFRS journal entries for sale {sale.id}: {str(e)}")
        # Optionally, you could rollback the sale here if accounting entries are critical
        # db.rollback()
        # raise HTTPException(status_code=500, detail=f"Failed to create accounting entries: {str(e)}")

    # get_sale expects a UUID to avoid route collisions with static paths
    return await get_sale(uuid.UUID(sale.id), db)


@router.get("/by-id/{sale_id}", response_model=SaleResponse)
async def get_sale(
    sale_id: uuid.UUID,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development,
):
    from sqlalchemy.orm import joinedload
    sale = db.query(Sale).options(
        joinedload(Sale.customer),
        joinedload(Sale.branch),
        joinedload(Sale.salesperson),
        joinedload(Sale.sale_items)
    ).filter(Sale.id == str(sale_id)).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    # require_branch_match(..., current_user)  # Removed for development
    salesperson_name = None
    if getattr(sale, "salesperson", None):
        try:
            first = getattr(sale.salesperson, "first_name", None)
            last = getattr(sale.salesperson, "last_name", None)
            username = getattr(sale.salesperson, "username", None)
            parts = [p for p in [first, last] if p]
            salesperson_name = " ".join(parts) if parts else username
        except Exception:
            salesperson_name = None

    branch_name = None
    if getattr(sale, "branch", None):
        try:
            branch_name = sale.branch.name
        except Exception:
            branch_name = None

    sale_dict = {
        "id": sale.id,
        "reference": sale.reference,
        "customer_id": sale.customer_id,
        "customer_name": sale.customer.name if sale.customer else "Walk-in Customer",
        "payment_method": sale.payment_method,
        "currency": sale.currency,
        "total_amount": float(sale.total_amount or 0),
        "total_amount_ex_vat": float(sale.total_amount_ex_vat or 0),
        "total_vat_amount": float(sale.total_vat_amount or 0),
        "amount_tendered": float(sale.amount_tendered or 0),
        "change_given": float(sale.change_given or 0),
        "discount_amount": float(sale.discount_amount or 0),
        "discount_percentage": float(sale.discount_percentage or 0),
        "status": sale.status,
        "date": sale.date,
        "notes": sale.notes,
        "salesperson_name": salesperson_name,
        "branch_name": branch_name,
        "items_count": len(sale.sale_items),
        "items": [],
    }
    for item in sale.sale_items:
        sale_dict["items"].append(
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.name if item.product else "Unknown Product",
                "product_sku": item.product.sku if item.product else "",
                "quantity": item.quantity,
                "selling_price": float(item.selling_price or 0),
                "vat_rate": float(item.vat_rate or 0),
                "vat_amount": float(item.vat_amount or 0),
                "discount_amount": float(item.discount_amount or 0),
                "discount_percentage": float(item.discount_percentage or 0),
                "total_amount": float(item.total_amount or 0),
            }
        )
    return sale_dict


# Invoice Endpoints --------------------------------------------------------



class InvoiceBase(BaseModel):
    customer_id: str
    due_date: Optional[date] = None
    payment_terms: int = 30
    discount_amount: float = 0.0
    discount_percentage: float = 0.0
    notes: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    items: List[InvoiceItemCreate]

class InvoiceResponse(InvoiceBase):
    id: str
    invoice_number: str
    date: date
    status: str
    total: float
    total_vat_amount: float
    total_amount: float
    amount_paid: float
    customer_name: Optional[str] = None
    items_count: int

from fastapi.responses import StreamingResponse
import csv
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)
from io import StringIO


@router.get("/export")
@router.get("/export.csv")
async def export_sales_csv(
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    branch_id: Optional[str] = Query(None, description="Filter by branch id"),
    cashier_id: Optional[str] = Query(None, description="Filter by cashier/salesperson id"),
    db: Session = Depends(get_db),
):
    """Export filtered sales to CSV (ignores pagination)."""
    try:
        query = db.query(Sale)
        if status:
            query = query.filter(Sale.status == status)
        if customer_id:
            query = query.filter(Sale.customer_id == customer_id)
        if start_date:
            query = query.filter(Sale.date >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.filter(Sale.date <= datetime.combine(end_date, datetime.max.time()))
        if search:
            like = f"%{search}%"
            query = query.filter(or_(Sale.reference.ilike(like), Sale.notes.ilike(like)))
        if branch_id:
            query = query.filter(Sale.branch_id == branch_id)
        if cashier_id:
            query = query.filter(Sale.salesperson_id == cashier_id)

        sales = query.order_by(Sale.date.desc()).all()

        # Build CSV
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "Reference",
            "Date",
            "Customer",
            "Cashier",
            "Payment Method",
            "Currency",
            "Subtotal (Ex VAT)",
            "VAT Amount",
            "Total Amount",
            "Status",
            "Items Count",
            "Notes",
        ])
        for sale in sales:
            # Build salesperson name if available
            cashier = None
            if getattr(sale, "salesperson", None):
                first = getattr(sale.salesperson, "first_name", None)
                last = getattr(sale.salesperson, "last_name", None)
                username = getattr(sale.salesperson, "username", None)
                parts = [p for p in [first, last] if p]
                cashier = " ".join(parts) if parts else username
            writer.writerow([
                sale.reference,
                sale.date.isoformat() if sale.date else "",
                sale.customer.name if sale.customer else "Walk-in Customer",
                cashier or "",
                sale.payment_method or "",
                sale.currency or "",
                float(sale.total_amount_ex_vat or 0),
                float(sale.total_vat_amount or 0),
                float(sale.total_amount or 0),
                sale.status or "",
                len(sale.sale_items or []),
                (sale.notes or "").replace("\n", " ").strip(),
            ])

        buffer.seek(0)
        filename = f"sales_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "text/csv; charset=utf-8",
        }
        return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export sales: {e}")

# =============================
# Invoice Endpoints
# =============================
@router.get('/invoices', response_model=List[InvoiceResponse])
async def get_invoices(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    query = db.query(Invoice)
    # query = # Security check removed for development  # Removed for development
    if status:
        query = query.filter(Invoice.status == status)
    if customer_id:
        query = query.filter(Invoice.customer_id == customer_id)
    invoices = query.order_by(Invoice.date.desc()).offset(skip).limit(limit).all()
    result = []
    for inv in invoices:
        result.append({
            'id': inv.id,
            'invoice_number': inv.invoice_number,
            'customer_id': inv.customer_id,
            'customer_name': inv.customer.name if inv.customer else 'Unknown Customer',
            'date': inv.date,
            'status': inv.status,
            'total': float(inv.total or 0),
            'total_vat_amount': float(inv.total_vat_amount or 0),
            'total_amount': float(inv.total_amount or 0),
            'amount_paid': float(inv.amount_paid or 0),
            'due_date': inv.due_date,
            'payment_terms': inv.payment_terms,
            'discount_amount': float(inv.discount_amount or 0),
            'discount_percentage': float(inv.discount_percentage or 0),
            'notes': inv.notes,
            'items_count': len(inv.invoice_items)
        })
    return result


# Cash Management Endpoints -----------------------------------------------

@router.post("/cash-submissions", response_model=CashSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_cash_takings(
    submission: CashSubmissionCreate,
    db: Session = Depends(get_db),
):
    """
    Submit cash takings from a salesperson to manager/accounting.
    This moves cash from Undeposited Funds (1114) to Cash in Hand (1111).
    """
    # Create the cash submission record
    submission_id = str(uuid.uuid4())

    # Create IFRS journal entries for the submission
    try:
        ifrs_service = IFRSAccountingService(db)
        journal_entries = ifrs_service.submit_cash_takings(
            salesperson_id=submission.salesperson_id,
            amount=Decimal(str(submission.amount)),
            submission_date=submission.submission_date,
            branch_id=submission.branch_id,
            notes=submission.notes
        )

        # Get the first journal entry ID for reference
        journal_entry_id = journal_entries[0].id if journal_entries else None

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create accounting entries: {str(e)}"
        )

    # Create the submission record
    cash_submission = CashSubmission(
        id=submission_id,
        salesperson_id=submission.salesperson_id,
        received_by_id=submission.received_by_id,
        amount=Decimal(str(submission.amount)),
        submission_date=submission.submission_date,
        branch_id=submission.branch_id,
        journal_entry_id=journal_entry_id,
        status=CashSubmissionStatus.POSTED,
        notes=submission.notes
    )

    db.add(cash_submission)
    db.commit()
    db.refresh(cash_submission)

    # Build response with names
    salesperson_name = None
    received_by_name = None

    if cash_submission.salesperson:
        try:
            first = getattr(cash_submission.salesperson, "first_name", None)
            last = getattr(cash_submission.salesperson, "last_name", None)
            username = getattr(cash_submission.salesperson, "username", None)
            parts = [p for p in [first, last] if p]
            salesperson_name = " ".join(parts) if parts else username
        except Exception:
            pass

    if cash_submission.received_by:
        try:
            first = getattr(cash_submission.received_by, "first_name", None)
            last = getattr(cash_submission.received_by, "last_name", None)
            username = getattr(cash_submission.received_by, "username", None)
            parts = [p for p in [first, last] if p]
            received_by_name = " ".join(parts) if parts else username
        except Exception:
            pass

    return CashSubmissionResponse(
        id=cash_submission.id,
        salesperson_id=cash_submission.salesperson_id,
        salesperson_name=salesperson_name,
        received_by_id=cash_submission.received_by_id,
        received_by_name=received_by_name,
        amount=float(cash_submission.amount),
        submission_date=cash_submission.submission_date,
        branch_id=cash_submission.branch_id,
        journal_entry_id=cash_submission.journal_entry_id,
        status=cash_submission.status.value,
        notes=cash_submission.notes,
        created_at=cash_submission.created_at,
        updated_at=cash_submission.updated_at
    )


@router.get("/cash-submissions", response_model=List[CashSubmissionResponse])
async def get_cash_submissions(
    start_date: Optional[date] = Query(None, description="Filter by submission date (from)"),
    end_date: Optional[date] = Query(None, description="Filter by submission date (to)"),
    salesperson_id: Optional[str] = Query(None, description="Filter by salesperson"),
    branch_id: Optional[str] = Query(None, description="Filter by branch"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
):
    """
    Get list of cash submissions with optional filters.
    """
    query = db.query(CashSubmission)

    if start_date:
        query = query.filter(CashSubmission.submission_date >= start_date)
    if end_date:
        query = query.filter(CashSubmission.submission_date <= end_date)
    if salesperson_id:
        query = query.filter(CashSubmission.salesperson_id == salesperson_id)
    if branch_id:
        query = query.filter(CashSubmission.branch_id == branch_id)
    if status_filter:
        query = query.filter(CashSubmission.status == status_filter)

    submissions = query.order_by(CashSubmission.submission_date.desc()).all()

    result = []
    for sub in submissions:
        salesperson_name = None
        received_by_name = None

        if sub.salesperson:
            try:
                first = getattr(sub.salesperson, "first_name", None)
                last = getattr(sub.salesperson, "last_name", None)
                username = getattr(sub.salesperson, "username", None)
                parts = [p for p in [first, last] if p]
                salesperson_name = " ".join(parts) if parts else username
            except Exception:
                pass

        if sub.received_by:
            try:
                first = getattr(sub.received_by, "first_name", None)
                last = getattr(sub.received_by, "last_name", None)
                username = getattr(sub.received_by, "username", None)
                parts = [p for p in [first, last] if p]
                received_by_name = " ".join(parts) if parts else username
            except Exception:
                pass

        result.append(CashSubmissionResponse(
            id=sub.id,
            salesperson_id=sub.salesperson_id,
            salesperson_name=salesperson_name,
            received_by_id=sub.received_by_id,
            received_by_name=received_by_name,
            amount=float(sub.amount),
            submission_date=sub.submission_date,
            branch_id=sub.branch_id,
            journal_entry_id=sub.journal_entry_id,
            status=sub.status.value,
            notes=sub.notes,
            created_at=sub.created_at,
            updated_at=sub.updated_at
        ))

    return result


@router.post("/float-allocations", response_model=FloatAllocationResponse, status_code=status.HTTP_201_CREATED)
async def allocate_float(
    allocation: FloatAllocationCreate,
    db: Session = Depends(get_db),
):
    """
    Allocate float/change to a cashier.
    This moves cash from Cash in Hand (1111) to Petty Cash (1112) or similar.
    """
    from app.models.accounting import AccountingCode, JournalEntry, AccountingEntry

    allocation_id = str(uuid.uuid4())

    # Create accounting entries for float allocation
    try:
        # Get accounting codes
        petty_cash_code = db.query(AccountingCode).filter(AccountingCode.code == '1112').first()
        cash_in_hand_code = db.query(AccountingCode).filter(AccountingCode.code == '1111').first()

        if not petty_cash_code or not cash_in_hand_code:
            raise HTTPException(
                status_code=500,
                detail="Required accounting codes not found (1111 Cash in Hand, 1112 Petty Cash)"
            )

        # Create accounting entry
        accounting_entry = AccountingEntry(
            date_posted=allocation.allocation_date,
            particulars=f"Float allocation to cashier - FLOAT-{allocation_id[:8]}",
            status='posted',
            branch_id=allocation.branch_id
        )
        db.add(accounting_entry)
        db.flush()

        # Dr Petty Cash (1112)
        journal_entry_dr = JournalEntry(
            accounting_entry_id=accounting_entry.id,
            accounting_code_id=petty_cash_code.id,
            entry_type='debit',
            debit_amount=Decimal(str(allocation.float_amount)),
            credit_amount=Decimal('0'),
            description=f"Float allocated to cashier",
            date=allocation.allocation_date,
            date_posted=allocation.allocation_date
        )
        db.add(journal_entry_dr)

        # Cr Cash in Hand (1111)
        journal_entry_cr = JournalEntry(
            accounting_entry_id=accounting_entry.id,
            accounting_code_id=cash_in_hand_code.id,
            entry_type='credit',
            debit_amount=Decimal('0'),
            credit_amount=Decimal(str(allocation.float_amount)),
            description=f"Float allocated from cash in hand",
            date=allocation.allocation_date,
            date_posted=allocation.allocation_date
        )
        db.add(journal_entry_cr)

        allocation_journal_entry_id = journal_entry_dr.id

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create accounting entries: {str(e)}"
        )

    # Create float allocation record
    float_allocation = FloatAllocation(
        id=allocation_id,
        cashier_id=allocation.cashier_id,
        allocated_by_id=allocation.allocated_by_id,
        float_amount=Decimal(str(allocation.float_amount)),
        amount_returned=Decimal('0'),
        allocation_date=allocation.allocation_date,
        branch_id=allocation.branch_id,
        allocation_journal_entry_id=allocation_journal_entry_id,
        status=FloatAllocationStatus.ALLOCATED,
        notes=allocation.notes
    )

    db.add(float_allocation)
    db.commit()
    db.refresh(float_allocation)

    # Build response with names
    cashier_name = None
    allocated_by_name = None

    if float_allocation.cashier:
        try:
            first = getattr(float_allocation.cashier, "first_name", None)
            last = getattr(float_allocation.cashier, "last_name", None)
            username = getattr(float_allocation.cashier, "username", None)
            parts = [p for p in [first, last] if p]
            cashier_name = " ".join(parts) if parts else username
        except Exception:
            pass

    if float_allocation.allocated_by:
        try:
            first = getattr(float_allocation.allocated_by, "first_name", None)
            last = getattr(float_allocation.allocated_by, "last_name", None)
            username = getattr(float_allocation.allocated_by, "username", None)
            parts = [p for p in [first, last] if p]
            allocated_by_name = " ".join(parts) if parts else username
        except Exception:
            pass

    return FloatAllocationResponse(
        id=float_allocation.id,
        cashier_id=float_allocation.cashier_id,
        cashier_name=cashier_name,
        allocated_by_id=float_allocation.allocated_by_id,
        allocated_by_name=allocated_by_name,
        float_amount=float(float_allocation.float_amount),
        amount_returned=float(float_allocation.amount_returned),
        allocation_date=float_allocation.allocation_date,
        return_date=float_allocation.return_date,
        branch_id=float_allocation.branch_id,
        allocation_journal_entry_id=float_allocation.allocation_journal_entry_id,
        return_journal_entry_id=float_allocation.return_journal_entry_id,
        status=float_allocation.status.value,
        notes=float_allocation.notes,
        created_at=float_allocation.created_at,
        updated_at=float_allocation.updated_at
    )


@router.get("/float-allocations", response_model=List[FloatAllocationResponse])
async def get_float_allocations(
    cashier_id: Optional[str] = Query(None, description="Filter by cashier"),
    branch_id: Optional[str] = Query(None, description="Filter by branch"),
    status_filter: Optional[str] = Query(None, description="Filter by status (allocated/returned)"),
    start_date: Optional[date] = Query(None, description="Filter by allocation date (from)"),
    end_date: Optional[date] = Query(None, description="Filter by allocation date (to)"),
    db: Session = Depends(get_db),
):
    """
    Get list of float allocations with optional filters.
    """
    query = db.query(FloatAllocation)

    if cashier_id:
        query = query.filter(FloatAllocation.cashier_id == cashier_id)
    if branch_id:
        query = query.filter(FloatAllocation.branch_id == branch_id)
    if status_filter:
        query = query.filter(FloatAllocation.status == status_filter)
    if start_date:
        query = query.filter(FloatAllocation.allocation_date >= start_date)
    if end_date:
        query = query.filter(FloatAllocation.allocation_date <= end_date)

    allocations = query.order_by(FloatAllocation.allocation_date.desc()).all()

    result = []
    for alloc in allocations:
        cashier_name = None
        allocated_by_name = None

        if alloc.cashier:
            try:
                first = getattr(alloc.cashier, "first_name", None)
                last = getattr(alloc.cashier, "last_name", None)
                username = getattr(alloc.cashier, "username", None)
                parts = [p for p in [first, last] if p]
                cashier_name = " ".join(parts) if parts else username
            except Exception:
                pass

        if alloc.allocated_by:
            try:
                first = getattr(alloc.allocated_by, "first_name", None)
                last = getattr(alloc.allocated_by, "last_name", None)
                username = getattr(alloc.allocated_by, "username", None)
                parts = [p for p in [first, last] if p]
                allocated_by_name = " ".join(parts) if parts else username
            except Exception:
                pass

        result.append(FloatAllocationResponse(
            id=alloc.id,
            cashier_id=alloc.cashier_id,
            cashier_name=cashier_name,
            allocated_by_id=alloc.allocated_by_id,
            allocated_by_name=allocated_by_name,
            float_amount=float(alloc.float_amount),
            amount_returned=float(alloc.amount_returned),
            allocation_date=alloc.allocation_date,
            return_date=alloc.return_date,
            branch_id=alloc.branch_id,
            allocation_journal_entry_id=alloc.allocation_journal_entry_id,
            return_journal_entry_id=alloc.return_journal_entry_id,
            status=alloc.status.value,
            notes=alloc.notes,
            created_at=alloc.created_at,
            updated_at=alloc.updated_at
        ))

    return result


@router.put("/float-allocations/{allocation_id}/return", response_model=FloatAllocationResponse)
async def return_float(
    allocation_id: str,
    float_return: FloatReturnCreate,
    db: Session = Depends(get_db),
):
    """
    Record the return of float from a cashier.
    This moves cash from Petty Cash (1112) back to Cash in Hand (1111).
    """
    from app.models.accounting import AccountingCode, JournalEntry, AccountingEntry

    # Get the allocation
    allocation = db.query(FloatAllocation).filter(FloatAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Float allocation not found")

    if allocation.status == FloatAllocationStatus.RETURNED:
        raise HTTPException(status_code=400, detail="Float already returned")

    # Validate return amount
    return_amount = Decimal(str(float_return.amount_returned))
    remaining = allocation.float_amount - allocation.amount_returned

    if return_amount > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Return amount ({return_amount}) exceeds remaining float ({remaining})"
        )

    # Create accounting entries for float return
    try:
        # Get accounting codes
        petty_cash_code = db.query(AccountingCode).filter(AccountingCode.code == '1112').first()
        cash_in_hand_code = db.query(AccountingCode).filter(AccountingCode.code == '1111').first()

        if not petty_cash_code or not cash_in_hand_code:
            raise HTTPException(
                status_code=500,
                detail="Required accounting codes not found"
            )

        # Create accounting entry
        accounting_entry = AccountingEntry(
            id=str(uuid.uuid4()),
            entry_date=float_return.return_date,
            description=f"Float return from cashier",
            reference=f"FLOATRET-{allocation_id[:8]}",
            entry_type="float_return",
            branch_id=allocation.branch_id
        )
        db.add(accounting_entry)
        db.flush()

        # Dr Cash in Hand (1111)
        journal_entry_dr = JournalEntry(
            id=str(uuid.uuid4()),
            accounting_entry_id=accounting_entry.id,
            accounting_code_id=cash_in_hand_code.id,
            entry_type='debit',
            debit_amount=return_amount,
            credit_amount=Decimal('0'),
            description=f"Float returned to cash in hand"
        )
        db.add(journal_entry_dr)

        # Cr Petty Cash (1112)
        journal_entry_cr = JournalEntry(
            id=str(uuid.uuid4()),
            accounting_entry_id=accounting_entry.id,
            accounting_code_id=petty_cash_code.id,
            entry_type='credit',
            debit_amount=Decimal('0'),
            credit_amount=return_amount,
            description=f"Float returned from cashier"
        )
        db.add(journal_entry_cr)

        return_journal_entry_id = journal_entry_dr.id

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create accounting entries: {str(e)}"
        )

    # Update allocation
    allocation.amount_returned = allocation.amount_returned + return_amount
    allocation.return_date = float_return.return_date
    allocation.return_journal_entry_id = return_journal_entry_id

    # Update status
    if allocation.amount_returned >= allocation.float_amount:
        allocation.status = FloatAllocationStatus.RETURNED
    else:
        allocation.status = FloatAllocationStatus.PARTIALLY_RETURNED

    if float_return.notes:
        allocation.notes = (allocation.notes or "") + f"\nReturn: {float_return.notes}"

    db.commit()
    db.refresh(allocation)

    # Build response with names
    cashier_name = None
    allocated_by_name = None

    if allocation.cashier:
        try:
            first = getattr(allocation.cashier, "first_name", None)
            last = getattr(allocation.cashier, "last_name", None)
            username = getattr(allocation.cashier, "username", None)
            parts = [p for p in [first, last] if p]
            cashier_name = " ".join(parts) if parts else username
        except Exception:
            pass

    if allocation.allocated_by:
        try:
            first = getattr(allocation.allocated_by, "first_name", None)
            last = getattr(allocation.allocated_by, "last_name", None)
            username = getattr(allocation.allocated_by, "username", None)
            parts = [p for p in [first, last] if p]
            allocated_by_name = " ".join(parts) if parts else username
        except Exception:
            pass

    return FloatAllocationResponse(
        id=allocation.id,
        cashier_id=allocation.cashier_id,
        cashier_name=cashier_name,
        allocated_by_id=allocation.allocated_by_id,
        allocated_by_name=allocated_by_name,
        float_amount=float(allocation.float_amount),
        amount_returned=float(allocation.amount_returned),
        allocation_date=allocation.allocation_date,
        return_date=allocation.return_date,
        branch_id=allocation.branch_id,
        allocation_journal_entry_id=allocation.allocation_journal_entry_id,
        return_journal_entry_id=allocation.return_journal_entry_id,
        status=allocation.status.value,
        notes=allocation.notes,
        created_at=allocation.created_at,
        updated_at=allocation.updated_at
    )


# Dimensional Accounting GL Posting Endpoints ==============================

class GLPostingResponse(BaseModel):
    """Response for GL posting operations"""
    success: bool
    invoice_id: str
    entries_created: int
    journal_entry_ids: List[str]
    total_amount: float
    posting_date: str


class DimensionAccountingDetailsResponse(BaseModel):
    """Invoice accounting dimension details"""
    invoice_id: str
    invoice_number: str
    total_amount: float
    cost_center: Optional[str] = None
    project: Optional[str] = None
    department: Optional[str] = None
    revenue_account: Optional[str] = None
    ar_account: Optional[str] = None
    posting_status: str
    last_posted_date: Optional[str] = None


class JournalEntryResponse(BaseModel):
    """Journal entry response"""
    id: str
    accounting_code: str
    debit_amount: float
    credit_amount: float
    description: str
    source: str
    entry_date: str
    dimensions: List[Dict] = []


class DimensionalAnalysisResponse(BaseModel):
    """Dimensional analysis for sales"""
    total_revenue: float
    by_cost_center: Dict[str, float]
    by_project: Dict[str, float]
    by_department: Dict[str, float]


class ReconciliationResponse(BaseModel):
    """Reconciliation result"""
    period: str
    invoice_total: float
    gl_total: float
    variance: float
    is_reconciled: bool
    by_dimension: List[Dict] = []


@router.post("/invoices/{invoice_id}/post-accounting", response_model=GLPostingResponse, tags=["accounting"])
def post_invoice_to_accounting(
    invoice_id: str,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Post sales invoice to General Ledger with dimensional assignments.
    Creates AR Debit and Revenue Credit entries with dimension tracking.
    """
    try:
        service = SalesService(db)
        result = service.post_sale_to_accounting(invoice_id, user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error posting to accounting: {str(e)}")


@router.get("/invoices/{invoice_id}/accounting-details", response_model=DimensionAccountingDetailsResponse, tags=["accounting"])
def get_invoice_accounting_details(
    invoice_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed accounting dimension information for an invoice.
    Shows cost center, project, department assignments and GL accounts.
    """
    try:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        # Get dimension names
        cost_center_name = None
        project_name = None
        department_name = None

        if invoice.cost_center_id:
            cc = db.query(AccountingDimensionValue).filter(AccountingDimensionValue.id == invoice.cost_center_id).first()
            cost_center_name = cc.name if cc else None

        if invoice.project_id:
            proj = db.query(AccountingDimensionValue).filter(AccountingDimensionValue.id == invoice.project_id).first()
            project_name = proj.name if proj else None

        if invoice.department_id:
            dept = db.query(AccountingDimensionValue).filter(AccountingDimensionValue.id == invoice.department_id).first()
            department_name = dept.name if dept else None

        return {
            'invoice_id': invoice.id,
            'invoice_number': invoice.invoice_number or '',
            'total_amount': float(invoice.total_amount or 0),
            'cost_center': cost_center_name,
            'project': project_name,
            'department': department_name,
            'revenue_account': invoice.revenue_account.code if invoice.revenue_account else None,
            'ar_account': invoice.ar_account.code if invoice.ar_account else None,
            'posting_status': invoice.posting_status or 'draft',
            'last_posted_date': invoice.last_posted_date.isoformat() if invoice.last_posted_date else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices/accounting-bridge", response_model=List[Dict], tags=["accounting"])
def get_sales_accounting_bridge(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    posting_status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get the bridge table showing invoice-to-GL entry mappings.
    Useful for auditing and reconciliation.
    """
    try:
        query = db.query(Invoice)

        if start_date:
            query = query.filter(Invoice.date >= start_date)
        if end_date:
            query = query.filter(Invoice.date <= end_date)
        if posting_status:
            query = query.filter(Invoice.posting_status == posting_status)

        invoices = query.all()

        bridge_data = []
        for invoice in invoices:
            # Get related journal entries
            journal_entries = db.query(JournalEntry).filter(
                JournalEntry.reference.like(f"%SALES-{invoice.id}%")
            ).all()

            bridge_data.append({
                'invoice_id': invoice.id,
                'invoice_number': invoice.invoice_number or '',
                'invoice_date': invoice.date.isoformat() if invoice.date else None,
                'total_amount': float(invoice.total_amount or 0),
                'posting_status': invoice.posting_status or 'draft',
                'journal_entry_count': len(journal_entries),
                'journal_entry_ids': [je.id for je in journal_entries],
                'cost_center_id': invoice.cost_center_id,
                'project_id': invoice.project_id,
                'department_id': invoice.department_id
            })

        return bridge_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices/journal-entries", response_model=List[JournalEntryResponse], tags=["accounting"])
def get_sales_journal_entries(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    source: str = Query("SALES"),
    db: Session = Depends(get_db)
):
    """
    Get all journal entries for sales transactions.
    Shows debit/credit entries with dimension assignments.
    Optimized with eager loading and name fields instead of UUIDs.
    """
    try:
        # Add eager loading for all relationships
        query = db.query(JournalEntry).options(
            joinedload(JournalEntry.accounting_code),
            joinedload(JournalEntry.accounting_entry),
            joinedload(JournalEntry.branch),
            joinedload(JournalEntry.ledger),
            joinedload(JournalEntry.dimension_assignments)
        ).filter(JournalEntry.source == source)

        if start_date:
            query = query.filter(JournalEntry.entry_date >= start_date)
        if end_date:
            query = query.filter(JournalEntry.entry_date <= end_date)

        entries = query.all()

        result = []
        for entry in entries:
            dimensions = []
            if entry.dimension_assignments:
                for dim_assign in entry.dimension_assignments:
                    dimensions.append({
                        'dimension_value_id': dim_assign.dimension_value_id,
                        'dimension_type': dim_assign.dimension_value.dimension.code if dim_assign.dimension_value and dim_assign.dimension_value.dimension else None,
                        'dimension_value': dim_assign.dimension_value.value if dim_assign.dimension_value else None
                    })

            result.append({
                'id': entry.id,
                'accounting_code': entry.accounting_code.code if entry.accounting_code else None,
                'accounting_code_name': entry.accounting_code.name if entry.accounting_code else None,
                'accounting_entry_id': entry.accounting_entry_id,
                'accounting_entry_particulars': entry.accounting_entry.particulars if entry.accounting_entry else None,
                'branch_id': entry.branch_id,
                'branch_name': entry.branch.name if entry.branch else None,
                'ledger_id': entry.ledger_id,
                'ledger_description': entry.ledger.description if entry.ledger else None,
                'debit_amount': float(entry.debit_amount or 0),
                'credit_amount': float(entry.credit_amount or 0),
                'description': entry.description or '',
                'source': entry.source or '',
                'entry_date': entry.entry_date.isoformat() if entry.entry_date else None,
                'dimensions': dimensions
            })

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dimensional-analysis", response_model=DimensionalAnalysisResponse, tags=["accounting"])
def get_sales_dimensional_analysis(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Analyze sales revenue by accounting dimensions.
    Groups revenue by cost center, project, and department.
    """
    try:
        query = db.query(Invoice)

        if start_date:
            query = query.filter(Invoice.date >= start_date)
        if end_date:
            query = query.filter(Invoice.date <= end_date)

        invoices = query.all()

        total_revenue = Decimal('0')
        by_cost_center = {}
        by_project = {}
        by_department = {}

        for invoice in invoices:
            amount = Decimal(str(invoice.total_amount or 0))
            total_revenue += amount

            # Group by cost center
            if invoice.cost_center_id:
                cc = db.query(AccountingDimensionValue).filter(AccountingDimensionValue.id == invoice.cost_center_id).first()
                cc_name = cc.name if cc else 'Unknown'
                by_cost_center[cc_name] = float(by_cost_center.get(cc_name, Decimal('0')) + amount)

            # Group by project
            if invoice.project_id:
                proj = db.query(AccountingDimensionValue).filter(AccountingDimensionValue.id == invoice.project_id).first()
                proj_name = proj.name if proj else 'Unknown'
                by_project[proj_name] = float(by_project.get(proj_name, Decimal('0')) + amount)

            # Group by department
            if invoice.department_id:
                dept = db.query(AccountingDimensionValue).filter(AccountingDimensionValue.id == invoice.department_id).first()
                dept_name = dept.name if dept else 'Unknown'
                by_department[dept_name] = float(by_department.get(dept_name, Decimal('0')) + amount)

        return {
            'total_revenue': float(total_revenue),
            'by_cost_center': by_cost_center,
            'by_project': by_project,
            'by_department': by_department
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reconcile", response_model=ReconciliationResponse, tags=["accounting"])
def reconcile_sales(
    period: str = Query(..., description="Period in YYYY-MM format"),
    db: Session = Depends(get_db)
):
    """
    Reconcile sales invoices against GL entries by dimension.
    Returns variance analysis to identify discrepancies.
    """
    try:
        service = SalesService(db)
        result = service.reconcile_sales_by_dimension(period)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/branch-sales/realtime")
async def get_branch_sales_realtime(
    exclude_empty: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get real-time branch sales data for monitoring dashboard.
    Returns aggregated sales metrics by branch for today and current month.
    """
    try:
        from sqlalchemy import cast, Date
        today = date.today()
        month_start = today.replace(day=1)

        # Query all branches with their sales data
        branches = db.query(Branch).all()

        branch_data = []
        total_network_sales = Decimal('0')
        active_branches = 0

        for branch in branches:
            # Get today's sales
            today_sales = db.query(func.sum(Invoice.total_amount)).filter(
                Invoice.branch_id == branch.id,
                cast(Invoice.invoice_date, Date) == today
            ).scalar() or Decimal('0')

            # Get month's sales
            month_sales = db.query(func.sum(Invoice.total_amount)).filter(
                Invoice.branch_id == branch.id,
                Invoice.invoice_date >= month_start
            ).scalar() or Decimal('0')

            # Get transaction count
            transaction_count = db.query(func.count(Invoice.id)).filter(
                Invoice.branch_id == branch.id,
                cast(Invoice.invoice_date, Date) == today
            ).scalar() or 0

            # Get last sale date
            last_sale = db.query(func.max(Invoice.invoice_date)).filter(
                Invoice.branch_id == branch.id
            ).scalar()

            # Calculate average transaction
            avg_transaction = float(today_sales / transaction_count) if transaction_count > 0 else 0.0

            branch_info = {
                'branch_id': branch.id,
                'branch_name': branch.name,
                'today_sales': float(today_sales),
                'month_sales': float(month_sales),
                'transaction_count': transaction_count,
                'avg_transaction': avg_transaction,
                'last_sale_date': last_sale.isoformat() if last_sale else None
            }

            # Filter out empty branches if requested
            if not exclude_empty or month_sales > 0:
                branch_data.append(branch_info)
                total_network_sales += month_sales
                if month_sales > 0:
                    active_branches += 1

        return {
            'timestamp': datetime.now().isoformat(),
            'total_network_sales': float(total_network_sales),
            'active_branches': active_branches,
            'total_branches': len(branch_data),
            'branches': branch_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching branch sales data: {str(e)}")

