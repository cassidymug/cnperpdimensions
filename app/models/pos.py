import uuid
from sqlalchemy import Column, String, Boolean, Text, Date, ForeignKey, Numeric, Integer, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class PosSession(BaseModel):
    """Point of Sale session model"""
    __tablename__ = "pos_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    user_id = Column(ForeignKey("users.id"), nullable=False)
    branch_id = Column(ForeignKey("branches.id"), nullable=False)
    till_id = Column(String)
    opened_at = Column(DateTime)
    closed_at = Column(DateTime)
    float_amount = Column(Numeric(12, 2), default=0.0)
    cash_submitted = Column(Numeric(12, 2), default=0.0)
    status = Column(String, default="pending")
    verified_by = Column(ForeignKey("users.id"))
    verified_at = Column(DateTime)
    verification_note = Column(Text)
    # Additional fields for better POS session tracking
    total_sales = Column(Numeric(15, 2), default=0.0)
    total_transactions = Column(Integer, default=0)
    total_cash_sales = Column(Numeric(15, 2), default=0.0)
    total_card_sales = Column(Numeric(15, 2), default=0.0)
    total_other_sales = Column(Numeric(15, 2), default=0.0)
    total_refunds = Column(Numeric(15, 2), default=0.0)
    notes = Column(Text)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="pos_sessions")
    branch = relationship("Branch")
    verified_by_user = relationship("User", foreign_keys=[verified_by])
    sales = relationship("Sale", back_populates="pos_session") 
    shift_reconciliation = relationship("PosShiftReconciliation", back_populates="session", uselist=False)


class PosShiftReconciliation(BaseModel):
    """End-of-shift reconciliation record for POS cashiers"""
    __tablename__ = "pos_shift_reconciliations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(ForeignKey("pos_sessions.id"), nullable=False, unique=True)
    cashier_id = Column(ForeignKey("users.id"), nullable=False)
    branch_id = Column(ForeignKey("branches.id"), nullable=False)
    shift_date = Column(Date, nullable=False)
    float_given = Column(Numeric(12, 2), default=0.0)
    cash_collected = Column(Numeric(12, 2), default=0.0)
    cash_sales = Column(Numeric(12, 2), default=0.0)
    expected_cash = Column(Numeric(12, 2), default=0.0)
    variance = Column(Numeric(12, 2), default=0.0)
    notes = Column(Text)
    verified_by = Column(ForeignKey("users.id"))
    verified_at = Column(DateTime)

    session = relationship("PosSession", back_populates="shift_reconciliation", foreign_keys=[session_id])
    cashier = relationship("User", foreign_keys=[cashier_id])
    branch = relationship("Branch", foreign_keys=[branch_id])
    verifier = relationship("User", foreign_keys=[verified_by])