import uuid
from sqlalchemy import Column, String, Boolean, Text, Date, ForeignKey, Numeric, Integer, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class VatReconciliation(BaseModel):
    """VAT reconciliation model"""
    __tablename__ = "vat_reconciliations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    description = Column(Text)
    vat_collected = Column(Numeric(10, 2), default=0.0)
    vat_paid = Column(Numeric(10, 2), default=0.0)
    net_vat_liability = Column(Numeric(10, 2), default=0.0)
    status = Column(String, default="draft", nullable=False)
    vat_rate = Column(Numeric(5, 2), default=14.0)
    branch_id = Column(String)
    calculated_at = Column(DateTime)
    submitted_at = Column(DateTime)
    paid_at = Column(DateTime)
    total_payments = Column(Numeric(12, 2), default=0.0)
    outstanding_amount = Column(Numeric(12, 2), default=0.0)
    payment_status = Column(String, default="unpaid")
    last_payment_date = Column(Date)

    # Relationships
    vat_reconciliation_items = relationship("VatReconciliationItem", back_populates="vat_reconciliation")
    vat_payments = relationship("VatPayment", back_populates="vat_reconciliation")


class VatReconciliationItem(BaseModel):
    """VAT reconciliation item model"""
    __tablename__ = "vat_reconciliation_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    vat_reconciliation_id = Column(ForeignKey("vat_reconciliations.id"), nullable=False)
    item_type = Column(String, nullable=False)
    reference_type = Column(String)
    reference_id = Column(String)
    description = Column(Text, nullable=False)
    vat_amount = Column(Numeric(10, 2), nullable=False)
    vat_rate = Column(Numeric(5, 2), default=14.0)
    transaction_date = Column(Date, nullable=False)
    branch_id = Column(String)

    # Relationships
    vat_reconciliation = relationship("VatReconciliation", back_populates="vat_reconciliation_items")


class VatPayment(BaseModel):
    """VAT payment model"""
    __tablename__ = "vat_payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    vat_reconciliation_id = Column(ForeignKey("vat_reconciliations.id"), nullable=False)
    amount_paid = Column(Numeric(12, 2), nullable=False)
    payment_date = Column(Date, nullable=False)
    payment_time = Column(DateTime, nullable=False)
    payment_method = Column(String, nullable=False)
    reference_number = Column(String)
    bank_account_id = Column(String, ForeignKey("bank_accounts.id"))
    bank_details = Column(Text)
    notes = Column(Text)
    payment_status = Column(String, default="completed", nullable=False)
    penalty_amount = Column(Numeric(10, 2), default=0.0)
    interest_amount = Column(Numeric(10, 2), default=0.0)
    total_amount = Column(Numeric(12, 2), nullable=False)
    tax_authority = Column(String, default="FIRS", nullable=False)
    created_by = Column(String)
    approved_by = Column(String)
    approved_at = Column(DateTime)

    # Relationships
    vat_reconciliation = relationship("VatReconciliation", back_populates="vat_payments")