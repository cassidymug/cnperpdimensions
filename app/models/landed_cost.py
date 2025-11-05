import uuid
from sqlalchemy import Column, String, Boolean, Text, Date, ForeignKey, Numeric, Integer, DateTime, Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel

class LandedCost(BaseModel):
    """
    Represents a collection of additional costs associated with a purchase or shipment.
    Enhanced with IFRS tags and dimensional accounting for proper cost tracking.
    """
    __tablename__ = "landed_costs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    purchase_id = Column(ForeignKey("purchases.id"), nullable=True)
    reference = Column(String, unique=True, index=True)
    supplier_id = Column(ForeignKey("suppliers.id"), nullable=True)
    date = Column(Date, nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False, default=0.0)
    status = Column(String, default="draft") # draft, confirmed, allocated
    notes = Column(Text)

    # Dimensional Accounting
    branch_id = Column(String, ForeignKey("branches.id"), nullable=True, index=True)
    cost_center_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True, index=True)
    project_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)
    department_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)

    # Invoice/Receipt Tracking
    invoice_number = Column(String(100), nullable=True)
    supplier_invoice_date = Column(Date, nullable=True)
    payment_due_date = Column(Date, nullable=True)

    # Payment Tracking
    paid_status = Column(String(20), default="unpaid", nullable=False) # unpaid, partial, paid
    amount_paid = Column(Numeric(15, 2), default=0.0)
    payment_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)

    # Relationships
    purchase = relationship("Purchase", back_populates="landed_costs")
    supplier = relationship("Supplier")
    branch = relationship("Branch")
    cost_center = relationship("AccountingDimensionValue", foreign_keys=[cost_center_id])
    project = relationship("AccountingDimensionValue", foreign_keys=[project_id])
    department = relationship("AccountingDimensionValue", foreign_keys=[department_id])
    payment_account = relationship("AccountingCode", foreign_keys=[payment_account_id])
    items = relationship("LandedCostItem", back_populates="landed_cost", cascade="all, delete-orphan")

class LandedCostItem(BaseModel):
    """
    Represents a single line item within a LandedCost document.
    Each item can have its own IFRS tag, GL account, and dimensional accounting.
    Examples: freight, insurance, duty, customs fees, taxes, handling, storage.
    """
    __tablename__ = "landed_cost_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    landed_cost_id = Column(ForeignKey("landed_costs.id"), nullable=False)
    description = Column(String, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    allocation_method = Column(String, default="quantity") # quantity, cost, weight, volume

    # Cost Classification
    cost_type = Column(String(50), default="other", nullable=False)
    # Valid types: freight, insurance, duty, customs, tax, handling, storage, other

    # IFRS Reporting Tag
    ifrs_tag = Column(String(20), nullable=True, index=True)
    # Examples: E1 (operating costs), A2.1 (inventory costs), E3 (taxes)

    # GL Account Mapping
    gl_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True, index=True)

    # Dimensional Accounting (can override parent landed cost dimensions)
    cost_center_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)
    project_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)
    department_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)

    # Invoice/Document Tracking (separate invoice for each cost type)
    invoice_number = Column(String(100), nullable=True)
    invoice_date = Column(Date, nullable=True)
    reference_number = Column(String(100), nullable=True) # e.g., customs declaration number

    # Tax Information
    tax_rate = Column(Numeric(5, 2), default=0.0)
    is_taxable = Column(Boolean, default=False) # whether VAT applies
    vat_amount = Column(Numeric(15, 2), default=0.0)
    vat_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)

    # Allocation Status
    allocated_to_inventory = Column(Boolean, default=False)

    # Additional Notes
    notes = Column(Text, nullable=True)

    # Relationships
    landed_cost = relationship("LandedCost", back_populates="items")
    gl_account = relationship("AccountingCode", foreign_keys=[gl_account_id])
    vat_account = relationship("AccountingCode", foreign_keys=[vat_account_id])
    cost_center = relationship("AccountingDimensionValue", foreign_keys=[cost_center_id])
    project = relationship("AccountingDimensionValue", foreign_keys=[project_id])
    department = relationship("AccountingDimensionValue", foreign_keys=[department_id])
