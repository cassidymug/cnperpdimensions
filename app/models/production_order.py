"""
Production Order Models for Manufacturing Work-in-Progress Tracking

This module provides comprehensive production tracking with:
- Production Orders (manufacturing jobs)
- Material consumption tracking
- Labor/overhead additions
- Status progression (draft → in-progress → completed)
- Inventory integration
"""
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, Numeric, Date, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.models.base import BaseModel


class ProductionOrderStatus(str, enum.Enum):
    """Production order status workflow"""
    DRAFT = "draft"                    # Created but not started
    PLANNED = "planned"                # Scheduled/planned
    RELEASED = "released"              # Released to production floor
    IN_PROGRESS = "in_progress"        # Active production
    ON_HOLD = "on_hold"                # Temporarily paused
    QUALITY_CHECK = "quality_check"    # QC inspection
    COMPLETED = "completed"            # Finished and closed
    CANCELLED = "cancelled"            # Cancelled


class ProductionOrder(BaseModel):
    """
    Production Order (Work Order / Manufacturing Order)

    Tracks a single manufacturing job from start to completion.
    Manages material consumption, labor, overhead, and finished goods production.
    """
    __tablename__ = "production_orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    order_number = Column(String(50), unique=True, nullable=False, index=True)

    # Product being manufactured
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    recipe_id = Column(String, ForeignKey("products.id"), nullable=True)  # BOM source (if using recipe)

    # Production details
    quantity_planned = Column(Numeric(15, 2), nullable=False)
    quantity_produced = Column(Numeric(15, 2), default=0)
    quantity_scrapped = Column(Numeric(15, 2), default=0)

    # Unit of measure
    unit_of_measure_id = Column(String, ForeignKey("unit_of_measures.id"), nullable=True)

    # Dates
    scheduled_start_date = Column(Date, nullable=True)
    scheduled_end_date = Column(Date, nullable=True)
    actual_start_date = Column(Date, nullable=True)
    actual_end_date = Column(Date, nullable=True)

    # Status tracking
    status = Column(SQLEnum(ProductionOrderStatus), default=ProductionOrderStatus.DRAFT, nullable=False, index=True)
    priority = Column(Integer, default=5)  # 1=highest, 10=lowest

    # Cost tracking (accumulated as production progresses)
    total_material_cost = Column(Numeric(15, 2), default=0)
    total_labor_cost = Column(Numeric(15, 2), default=0)
    total_overhead_cost = Column(Numeric(15, 2), default=0)
    total_cost = Column(Numeric(15, 2), default=0)
    unit_cost = Column(Numeric(15, 2), default=0)

    # Branch/location
    manufacturing_branch_id = Column(String, ForeignKey("branches.id"), nullable=True)

    # Accounting Dimensions - for GL posting and cost tracking
    cost_center_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True, index=True)
    project_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)
    department_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)

    # GL Account mappings - for automatic journal entry creation
    wip_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)
    labor_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)

    # Accounting posting status (Manufacturing GL posting)
    posting_status = Column(String(20), default="draft", nullable=False, index=True)  # draft, posted, reconciled
    last_posted_date = Column(DateTime, nullable=True)
    posted_by = Column(String, ForeignKey("users.id"), nullable=True)

    # COGS Posting Status & GL Account - for COGS posting when product is sold
    cogs_posting_status = Column(String(20), default="pending", nullable=False, index=True)  # pending, posted, error
    cogs_gl_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)
    cogs_last_posted_date = Column(DateTime, nullable=True)
    cogs_posted_by = Column(String, ForeignKey("users.id"), nullable=True)

    # Notes and references
    notes = Column(Text, nullable=True)
    customer_reference = Column(String(100), nullable=True)  # If make-to-order
    batch_number = Column(String(50), nullable=True)

    # Audit fields
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    updated_by = Column(String, ForeignKey("users.id"), nullable=True)
    approved_by = Column(String, ForeignKey("users.id"), nullable=True)
    completed_by = Column(String, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = relationship("Product", foreign_keys=[product_id])
    recipe = relationship("Product", foreign_keys=[recipe_id])
    unit_of_measure = relationship("UnitOfMeasure")
    manufacturing_branch = relationship("Branch", foreign_keys=[manufacturing_branch_id])

    # Accounting dimension relationships
    cost_center = relationship("AccountingDimensionValue", foreign_keys=[cost_center_id])
    project = relationship("AccountingDimensionValue", foreign_keys=[project_id])
    department = relationship("AccountingDimensionValue", foreign_keys=[department_id])

    # GL account relationships
    wip_account = relationship("AccountingCode", foreign_keys=[wip_account_id])
    labor_account = relationship("AccountingCode", foreign_keys=[labor_account_id])
    cogs_gl_account = relationship("AccountingCode", foreign_keys=[cogs_gl_account_id])

    # User relationships for audit
    posted_by_user = relationship("User", foreign_keys=[posted_by])
    cogs_posted_by_user = relationship("User", foreign_keys=[cogs_posted_by])

    # Production details
    material_consumptions = relationship("ProductionMaterialConsumption", back_populates="production_order", cascade="all, delete-orphan")
    labor_entries = relationship("ProductionLaborEntry", back_populates="production_order", cascade="all, delete-orphan")
    overhead_entries = relationship("ProductionOverheadEntry", back_populates="production_order", cascade="all, delete-orphan")
    status_history = relationship("ProductionOrderStatusHistory", back_populates="production_order", cascade="all, delete-orphan")
    quality_checks = relationship("ProductionQualityCheck", back_populates="production_order", cascade="all, delete-orphan")


class ProductionMaterialConsumption(BaseModel):
    """
    Material Consumption for Production Order

    Tracks raw materials consumed during production.
    Links to inventory transactions for stock deduction.
    """
    __tablename__ = "production_material_consumptions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    production_order_id = Column(String, ForeignKey("production_orders.id"), nullable=False)

    # Material details
    material_id = Column(String, ForeignKey("products.id"), nullable=False)
    quantity_planned = Column(Numeric(15, 2), nullable=False)  # From BOM
    quantity_consumed = Column(Numeric(15, 2), default=0)  # Actually used
    quantity_returned = Column(Numeric(15, 2), default=0)  # Returned to stock
    quantity_scrapped = Column(Numeric(15, 2), default=0)  # Wasted

    # Costing
    unit_cost = Column(Numeric(15, 2), default=0)
    total_cost = Column(Numeric(15, 2), default=0)

    # Unit of measure
    unit_of_measure_id = Column(String, ForeignKey("unit_of_measures.id"), nullable=True)

    # Inventory tracking
    inventory_transaction_id = Column(String, ForeignKey("inventory_transactions.id"), nullable=True)

    # Issue details
    issued_date = Column(Date, nullable=True)
    issued_by = Column(String, ForeignKey("users.id"), nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    production_order = relationship("ProductionOrder", back_populates="material_consumptions")
    material = relationship("Product")
    unit_of_measure = relationship("UnitOfMeasure")
    inventory_transaction = relationship("InventoryTransaction")


class ProductionLaborEntry(BaseModel):
    """
    Labor Entry for Production Order

    Tracks labor hours/costs applied to production.
    """
    __tablename__ = "production_labor_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    production_order_id = Column(String, ForeignKey("production_orders.id"), nullable=False)

    # Labor details
    employee_id = Column(String, ForeignKey("users.id"), nullable=True)
    hours_worked = Column(Numeric(10, 2), nullable=False)
    hourly_rate = Column(Numeric(15, 2), nullable=False)
    total_cost = Column(Numeric(15, 2), nullable=False)

    # Work details
    work_date = Column(Date, nullable=False)
    work_description = Column(Text, nullable=True)
    operation_type = Column(String(100), nullable=True)  # e.g., "Setup", "Production", "QC", "Packaging"

    # Overtime tracking
    regular_hours = Column(Numeric(10, 2), default=0)
    overtime_hours = Column(Numeric(10, 2), default=0)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)

    # Relationships
    production_order = relationship("ProductionOrder", back_populates="labor_entries")
    employee = relationship("User", foreign_keys=[employee_id])


class ProductionOverheadEntry(BaseModel):
    """
    Overhead Entry for Production Order

    Tracks overhead costs (utilities, machine time, facility costs, etc.)
    """
    __tablename__ = "production_overhead_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    production_order_id = Column(String, ForeignKey("production_orders.id"), nullable=False)

    # Overhead details
    overhead_type = Column(String(100), nullable=False)  # e.g., "Machine Time", "Utilities", "Facility", "Indirect Materials"
    description = Column(Text, nullable=True)
    amount = Column(Numeric(15, 2), nullable=False)

    # Allocation basis
    allocation_basis = Column(String(50), nullable=True)  # e.g., "Machine Hours", "Direct Labor", "Units Produced"
    allocation_rate = Column(Numeric(15, 4), nullable=True)
    allocation_quantity = Column(Numeric(15, 2), nullable=True)

    # Date tracking
    incurred_date = Column(Date, nullable=False)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)

    # Relationships
    production_order = relationship("ProductionOrder", back_populates="overhead_entries")


class ProductionOrderStatusHistory(BaseModel):
    """
    Status History for Production Order

    Audit trail of status changes throughout production lifecycle.
    """
    __tablename__ = "production_order_status_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    production_order_id = Column(String, ForeignKey("production_orders.id"), nullable=False)

    # Status change details
    from_status = Column(SQLEnum(ProductionOrderStatus), nullable=True)
    to_status = Column(SQLEnum(ProductionOrderStatus), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    changed_by = Column(String, ForeignKey("users.id"), nullable=True)

    # Reason/notes
    reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    production_order = relationship("ProductionOrder", back_populates="status_history")


class ProductionQualityCheck(BaseModel):
    """
    Quality Check for Production Order

    Records quality inspections and results.
    """
    __tablename__ = "production_quality_checks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    production_order_id = Column(String, ForeignKey("production_orders.id"), nullable=False)

    # QC details
    check_date = Column(Date, nullable=False)
    inspector_id = Column(String, ForeignKey("users.id"), nullable=True)

    # Results
    quantity_inspected = Column(Numeric(15, 2), nullable=False)
    quantity_passed = Column(Numeric(15, 2), nullable=False)
    quantity_failed = Column(Numeric(15, 2), nullable=False)

    # Defect tracking
    defect_description = Column(Text, nullable=True)
    corrective_action = Column(Text, nullable=True)

    # Pass/Fail
    passed = Column(SQLEnum(enum.Enum("QCResult", ["PASSED", "FAILED", "CONDITIONAL"])), nullable=False)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    production_order = relationship("ProductionOrder", back_populates="quality_checks")
    inspector = relationship("User", foreign_keys=[inspector_id])
