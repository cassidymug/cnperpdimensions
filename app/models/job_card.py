import uuid
from datetime import date, datetime
from sqlalchemy import Column, String, Text, Date, DateTime, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class JobCard(BaseModel):
    __tablename__ = "job_cards"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_number = Column(String(40), unique=True, nullable=False, index=True)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    branch_id = Column(String, ForeignKey("branches.id"), nullable=False)
    status = Column(String(30), default="draft", nullable=False)
    job_type = Column(String(40), nullable=False)
    priority = Column(String(20), default="normal", nullable=False)
    description = Column(Text)
    notes = Column(Text)
    start_date = Column(Date, nullable=False)
    due_date = Column(Date)
    completed_date = Column(Date)
    technician_id = Column(String, ForeignKey("users.id"))
    created_by_id = Column(String, ForeignKey("users.id"))
    updated_by_id = Column(String, ForeignKey("users.id"))
    currency = Column(String(10), default="BWP", nullable=False)
    vat_rate = Column(Numeric(6, 3), default=0)
    total_material_cost = Column(Numeric(15, 2), default=0)
    total_material_price = Column(Numeric(15, 2), default=0)
    total_labor_cost = Column(Numeric(15, 2), default=0)
    total_labor_price = Column(Numeric(15, 2), default=0)
    subtotal = Column(Numeric(15, 2), default=0)
    vat_amount = Column(Numeric(15, 2), default=0)
    total_amount = Column(Numeric(15, 2), default=0)
    amount_paid = Column(Numeric(15, 2), default=0)
    amount_due = Column(Numeric(15, 2), default=0)
    invoice_generated = Column(Boolean, default=False)
    
    # Manufacturing/BOM fields
    bom_product_id = Column(String, ForeignKey("products.id"), nullable=True)
    production_quantity = Column(Numeric(12, 3), nullable=True)

    customer = relationship("Customer", back_populates="job_cards", lazy="joined")
    branch = relationship("Branch", back_populates="job_cards", lazy="joined")
    technician = relationship("User", foreign_keys=[technician_id], lazy="joined")
    created_by = relationship("User", foreign_keys=[created_by_id], lazy="joined")
    updated_by = relationship("User", foreign_keys=[updated_by_id], lazy="joined")
    materials = relationship(
        "JobCardMaterial",
        back_populates="job_card",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    labor_entries = relationship(
        "JobCardLabor",
        back_populates="job_card",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    notes_entries = relationship(
        "JobCardNote",
        back_populates="job_card",
        cascade="all, delete-orphan",
        lazy="select",
    )
    inventory_transactions = relationship(
        "InventoryTransaction",
        back_populates="job_card",
        lazy="select",
    )
    invoice = relationship("Invoice", back_populates="job_card", uselist=False, lazy="select")


class JobCardMaterial(BaseModel):
    __tablename__ = "job_card_materials"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_card_id = Column(String, ForeignKey("job_cards.id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(12, 3), nullable=False, default=0)
    unit_cost = Column(Numeric(15, 2), default=0)
    unit_price = Column(Numeric(15, 2), default=0)
    total_cost = Column(Numeric(15, 2), default=0)
    total_price = Column(Numeric(15, 2), default=0)
    is_issued = Column(Boolean, default=False)
    issued_at = Column(DateTime)
    inventory_transaction_id = Column(String, ForeignKey("inventory_transactions.id"))
    notes = Column(Text)

    job_card = relationship("JobCard", back_populates="materials")
    product = relationship("Product", lazy="joined")
    inventory_transaction = relationship("InventoryTransaction", lazy="select")


class JobCardLabor(BaseModel):
    __tablename__ = "job_card_labors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_card_id = Column(String, ForeignKey("job_cards.id"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    hours = Column(Numeric(10, 2), default=0)
    rate = Column(Numeric(15, 2), default=0)
    total_price = Column(Numeric(15, 2), default=0)
    total_cost = Column(Numeric(15, 2), default=0)
    technician_id = Column(String, ForeignKey("users.id"))
    product_id = Column(String, ForeignKey("products.id"))
    notes = Column(Text)

    job_card = relationship("JobCard", back_populates="labor_entries")
    technician = relationship("User", lazy="joined")
    product = relationship("Product", lazy="joined")


class JobCardNote(BaseModel):
    __tablename__ = "job_card_notes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_card_id = Column(String, ForeignKey("job_cards.id"), nullable=False, index=True)
    note = Column(Text, nullable=False)
    author_id = Column(String, ForeignKey("users.id"))
    logged_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    job_card = relationship("JobCard", back_populates="notes_entries")
    author = relationship("User", lazy="joined")
