"""
Models for cash management including salesperson takings submissions and cashier float allocations.
"""
from sqlalchemy import Column, String, Numeric, Date, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.models.base import Base


class CashSubmissionStatus(str, enum.Enum):
    """Status of a cash submission"""
    PENDING = "pending"
    VERIFIED = "verified"
    POSTED = "posted"


class FloatAllocationStatus(str, enum.Enum):
    """Status of a float allocation"""
    ALLOCATED = "allocated"
    RETURNED = "returned"
    PARTIALLY_RETURNED = "partially_returned"


class CashSubmission(Base):
    """
    Records cash submissions from salespersons to managers/accounting.
    Tracks the movement from Undeposited Funds (1114) to Cash in Hand (1111).
    """
    __tablename__ = "cash_submissions"

    id = Column(String, primary_key=True)

    # Who submitted the cash
    salesperson_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Who received the cash (manager/accounting)
    received_by_id = Column(String, ForeignKey("users.id"), nullable=True)

    # Amount submitted
    amount = Column(Numeric(15, 2), nullable=False)

    # When it was submitted
    submission_date = Column(Date, nullable=False)

    # Branch where submission occurred
    branch_id = Column(String, ForeignKey("branches.id"), nullable=True)

    # Reference to the journal entry created
    journal_entry_id = Column(String, ForeignKey("journal_entries.id"), nullable=True)

    # Status
    status = Column(SQLEnum(CashSubmissionStatus), default=CashSubmissionStatus.PENDING, nullable=False)

    # Notes
    notes = Column(Text, nullable=True)

    # Phase 4: Dimensional Accounting Fields
    cost_center_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True, index=True)
    department_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True, index=True)
    submission_reconciliation_status = Column(String, default="pending", nullable=False)  # pending|verified|variance

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    salesperson = relationship("User", foreign_keys=[salesperson_id], backref="cash_submissions_made")
    received_by = relationship("User", foreign_keys=[received_by_id], backref="cash_submissions_received")
    branch = relationship("Branch", backref="cash_submissions")
    journal_entry = relationship("JournalEntry", backref="cash_submission")
    cost_center = relationship("AccountingDimensionValue", foreign_keys=[cost_center_id])
    department = relationship("AccountingDimensionValue", foreign_keys=[department_id])


class FloatAllocation(Base):
    """
    Records float/change allocations to cashiers.
    Tracks the movement from Cash in Hand (1111) to Petty Cash (1112) or similar.
    """
    __tablename__ = "float_allocations"

    id = Column(String, primary_key=True)

    # Who received the float
    cashier_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Who allocated the float (manager)
    allocated_by_id = Column(String, ForeignKey("users.id"), nullable=True)

    # Float amount given
    float_amount = Column(Numeric(15, 2), nullable=False)

    # Amount returned (if any)
    amount_returned = Column(Numeric(15, 2), default=0, nullable=False)

    # Dates
    allocation_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)

    # Branch
    branch_id = Column(String, ForeignKey("branches.id"), nullable=True)

    # Reference to journal entries (allocation and return)
    allocation_journal_entry_id = Column(String, ForeignKey("journal_entries.id"), nullable=True)
    return_journal_entry_id = Column(String, ForeignKey("journal_entries.id"), nullable=True)

    # Status
    status = Column(SQLEnum(FloatAllocationStatus), default=FloatAllocationStatus.ALLOCATED, nullable=False)

    # Notes
    notes = Column(Text, nullable=True)

    # Phase 4: Dimensional Accounting Fields
    cost_center_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True, index=True)
    float_gl_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    cashier = relationship("User", foreign_keys=[cashier_id], backref="float_allocations_received")
    allocated_by = relationship("User", foreign_keys=[allocated_by_id], backref="float_allocations_made")
    branch = relationship("Branch", backref="float_allocations")
    allocation_journal_entry = relationship("JournalEntry", foreign_keys=[allocation_journal_entry_id])
    return_journal_entry = relationship("JournalEntry", foreign_keys=[return_journal_entry_id])
    cost_center = relationship("AccountingDimensionValue", foreign_keys=[cost_center_id])
    gl_account = relationship("AccountingCode", foreign_keys=[float_gl_account_id])
