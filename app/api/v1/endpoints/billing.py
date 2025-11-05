"""
Billing API Endpoints

Comprehensive billing management for rentals, utilities, subscriptions, and usage-based billing.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from datetime import date
from decimal import Decimal

from app.core.database import get_db
from app.services.billing_service import BillingService

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class BillingCycleCreate(BaseModel):
    """Billing cycle creation schema"""
    name: str
    customer_id: str
    cycle_type: str = Field(..., description="monthly, quarterly, annual, custom")
    interval: str
    interval_count: int = 1
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None


class BillingCycleResponse(BaseModel):
    """Billing cycle response schema"""
    id: str
    name: str
    customer_id: str
    cycle_type: str
    interval: str
    interval_count: int
    start_date: date
    end_date: Optional[date]
    status: str
    description: Optional[str]

    class Config:
        from_attributes = True


class BillableItemCreate(BaseModel):
    """Billable item creation schema"""
    billing_cycle_id: str
    billable_type: str = Field(
        ...,
        description="rental_property, rental_vehicle, utility_water, utility_electricity, subscription_service, usage_minutes, license, tax, etc."
    )
    billable_id: str = Field(..., description="Product ID")
    amount: Decimal
    start_date: date
    end_date: Optional[date] = None
    description: Optional[str] = None
    meta_data: Optional[Dict] = None


class BillableItemResponse(BaseModel):
    """Billable item response schema"""
    id: str
    billing_cycle_id: str
    billable_type: str
    billable_id: str
    amount: Decimal
    description: Optional[str]
    start_date: date
    end_date: Optional[date]
    status: str
    meta_data: Optional[Dict]
    license_number: Optional[str]
    license_type: Optional[str]
    license_expiry_date: Optional[date]

    class Config:
        from_attributes = True


class MeterReadingCreate(BaseModel):
    """Meter reading creation schema"""
    reading_date: date
    reading_value: Decimal
    notes: Optional[str] = None


class MeterReadingResponse(BaseModel):
    """Meter reading response schema"""
    last_reading: float
    current_reading: float
    usage: float
    rate: float
    amount: float
    reading_date: str


class InvoiceGenerationResponse(BaseModel):
    """Invoice generation response schema"""
    count: int
    invoices: List[Dict]


class DashboardStatsResponse(BaseModel):
    """Dashboard statistics response schema"""
    active_rentals: int
    rentals_revenue: float
    utility_meters: int
    pending_readings: int
    subscriptions: int
    subscriptions_revenue: float
    usage_items: int
    usage_revenue: float
    total_active_items: int


# ============================================================================
# BILLING CYCLES
# ============================================================================

@router.post("/cycles", response_model=BillingCycleResponse)
async def create_billing_cycle(
    cycle_data: BillingCycleCreate,
    db: Session = Depends(get_db)
):
    """Create a new billing cycle"""
    try:
        billing_service = BillingService(db)
        cycle = billing_service.create_billing_cycle(
            name=cycle_data.name,
            customer_id=cycle_data.customer_id,
            cycle_type=cycle_data.cycle_type,
            interval=cycle_data.interval,
            interval_count=cycle_data.interval_count,
            start_date=cycle_data.start_date,
            end_date=cycle_data.end_date,
            description=cycle_data.description
        )
        return cycle
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating billing cycle: {str(e)}")


@router.get("/cycles", response_model=List[BillingCycleResponse])
async def get_billing_cycles(
    customer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get billing cycles with optional filters"""
    try:
        billing_service = BillingService(db)
        cycles = billing_service.get_billing_cycles(
            customer_id=customer_id,
            status=status
        )
        return cycles
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving billing cycles: {str(e)}")


@router.get("/cycles/{cycle_id}", response_model=BillingCycleResponse)
async def get_billing_cycle(
    cycle_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific billing cycle"""
    try:
        billing_service = BillingService(db)
        cycle = billing_service.get_billing_cycle(cycle_id)
        if not cycle:
            raise HTTPException(status_code=404, detail=f"Billing cycle {cycle_id} not found")
        return cycle
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving billing cycle: {str(e)}")


# ============================================================================
# BILLABLE ITEMS
# ============================================================================

@router.post("/items", response_model=BillableItemResponse)
async def create_billable_item(
    item_data: BillableItemCreate,
    db: Session = Depends(get_db)
):
    """Create a new billable item (rental, utility, subscription, etc.)"""
    try:
        billing_service = BillingService(db)
        item = billing_service.create_billable_item(
            billing_cycle_id=item_data.billing_cycle_id,
            billable_type=item_data.billable_type,
            billable_id=item_data.billable_id,
            amount=item_data.amount,
            start_date=item_data.start_date,
            end_date=item_data.end_date,
            description=item_data.description,
            meta_data=item_data.meta_data
        )
        return item
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating billable item: {str(e)}")


@router.get("/items", response_model=List[BillableItemResponse])
async def get_billable_items(
    billing_cycle_id: Optional[str] = Query(None),
    billable_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get billable items with optional filters"""
    try:
        billing_service = BillingService(db)
        items = billing_service.get_billable_items(
            billing_cycle_id=billing_cycle_id,
            billable_type=billable_type,
            status=status
        )
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving billable items: {str(e)}")


@router.get("/items/{item_id}", response_model=BillableItemResponse)
async def get_billable_item(
    item_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific billable item"""
    try:
        billing_service = BillingService(db)
        item = billing_service.get_billable_item(item_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Billable item {item_id} not found")
        return item
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving billable item: {str(e)}")


@router.put("/items/{item_id}", response_model=BillableItemResponse)
async def update_billable_item(
    item_id: str,
    update_data: Dict,
    db: Session = Depends(get_db)
):
    """Update a billable item"""
    try:
        billing_service = BillingService(db)
        item = billing_service.update_billable_item(item_id, **update_data)
        return item
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating billable item: {str(e)}")


# ============================================================================
# METER READINGS
# ============================================================================

@router.post("/items/{item_id}/readings", response_model=MeterReadingResponse)
async def record_meter_reading(
    item_id: str,
    reading_data: MeterReadingCreate,
    db: Session = Depends(get_db)
):
    """Record a meter reading for a utility item"""
    try:
        billing_service = BillingService(db)
        result = billing_service.record_meter_reading(
            item_id=item_id,
            reading_date=reading_data.reading_date,
            reading_value=reading_data.reading_value,
            notes=reading_data.notes
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording meter reading: {str(e)}")


# ============================================================================
# INVOICE GENERATION
# ============================================================================

@router.post("/cycles/{cycle_id}/generate-invoices")
async def generate_invoices_for_cycle(
    cycle_id: str,
    invoice_date: Optional[date] = None,
    created_by: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Generate invoices for a specific billing cycle"""
    try:
        billing_service = BillingService(db)
        invoices = billing_service.generate_invoices_for_cycle(
            billing_cycle_id=cycle_id,
            invoice_date=invoice_date,
            created_by=created_by
        )
        return {
            'count': len(invoices),
            'invoices': [
                {
                    'id': inv.id,
                    'invoice_number': inv.invoice_number,
                    'customer_id': inv.customer_id,
                    'total_amount': float(inv.total_amount)
                }
                for inv in invoices
            ]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating invoices: {str(e)}")


@router.post("/generate-invoices", response_model=InvoiceGenerationResponse)
async def generate_all_due_invoices(
    reference_date: Optional[date] = Query(None),
    created_by: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Generate invoices for all billing cycles that are due"""
    try:
        billing_service = BillingService(db)
        result = billing_service.generate_all_due_invoices(
            reference_date=reference_date,
            created_by=created_by
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating invoices: {str(e)}")


# ============================================================================
# DASHBOARD & REPORTING
# ============================================================================

@router.get("/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: Session = Depends(get_db)
):
    """Get billing dashboard statistics"""
    try:
        billing_service = BillingService(db)
        stats = billing_service.get_dashboard_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving dashboard stats: {str(e)}")


@router.get("/customers/{customer_id}/summary")
async def get_customer_billing_summary(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """Get billing summary for a specific customer"""
    try:
        billing_service = BillingService(db)
        summary = billing_service.get_customer_billing_summary(customer_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving customer billing summary: {str(e)}")
