import uuid
from sqlalchemy import Column, String, Boolean, Text, Date, ForeignKey, Numeric, Integer, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class BillingCycle(BaseModel):
    """Billing cycle model for recurring billing"""
    __tablename__ = "billing_cycles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    name = Column(String, nullable=False)
    cycle_type = Column(String, nullable=False)
    interval = Column(String, nullable=False)
    interval_count = Column(Integer, default=1, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    status = Column(String, default="active", nullable=False)
    description = Column(Text)
    meta_data = Column(JSON, default={})
    customer_id = Column(ForeignKey("customers.id"), nullable=False)

    # Relationships
    customer = relationship("Customer", back_populates="billing_cycles")
    billable_items = relationship("BillableItem", back_populates="billing_cycle")
    recurring_invoices = relationship("RecurringInvoice", back_populates="billing_cycle")


class BillableItem(BaseModel):
    """Billable item model"""
    __tablename__ = "billable_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    billing_cycle_id = Column(ForeignKey("billing_cycles.id"), nullable=False)
    billable_type = Column(String, nullable=False)
    billable_id = Column(String, nullable=False)  # Can reference products, assets, or other entities
    amount = Column(Numeric(15, 2), nullable=False)
    description = Column(Text)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    status = Column(String, default="active", nullable=False)
    meta_data = Column(JSON, default={})
    license_number = Column(String)
    license_type = Column(String)
    license_version = Column(String)
    license_holder = Column(String)
    license_expiry_date = Column(Date)

    # Relationships
    billing_cycle = relationship("BillingCycle", back_populates="billable_items")
    # Note: billable_id can reference products, assets, or other entities - no direct relationship
    recurring_invoices = relationship("RecurringInvoice", back_populates="billable_item")


class RecurringInvoice(BaseModel):
    """Recurring invoice model"""
    __tablename__ = "recurring_invoices"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    billing_cycle_id = Column(ForeignKey("billing_cycles.id"), nullable=False)
    billable_item_id = Column(ForeignKey("billable_items.id"), nullable=False)
    invoice_number = Column(String, nullable=False, unique=True)
    due_date = Column(Date, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    status = Column(String, default="pending", nullable=False)
    description = Column(Text)
    meta_data = Column(JSON, default={})

    # Relationships
    billing_cycle = relationship("BillingCycle", back_populates="recurring_invoices")
    billable_item = relationship("BillableItem", back_populates="recurring_invoices")
    recurring_payments = relationship("RecurringPayment", back_populates="recurring_invoice")


class RecurringPayment(BaseModel):
    """Recurring payment model"""
    __tablename__ = "recurring_payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    recurring_invoice_id = Column(ForeignKey("recurring_invoices.id"), nullable=False)
    payment_date = Column(Date)
    amount = Column(Numeric(15, 2))
    payment_method = Column(String)
    reference = Column(String)
    status = Column(String)
    meta_data = Column(JSON)

    # Relationships
    recurring_invoice = relationship("RecurringInvoice", back_populates="recurring_payments")
