"""
Payment tracking models for purchases
"""
import uuid
from sqlalchemy import Column, String, Text, Date, ForeignKey, Numeric, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import BaseModel


class PurchasePayment(BaseModel):
    """Individual payment record for purchases"""
    __tablename__ = "purchase_payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Payment details
    purchase_id = Column(ForeignKey("purchases.id"), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    payment_date = Column(Date, nullable=False)
    payment_method = Column(String, nullable=False, default="bank_transfer")  # bank_transfer, cash, check, mobile_money, eft, credit_card
    reference = Column(String)  # Check number, transfer ID, receipt number, etc.
    notes = Column(Text)
    
    # Audit fields
    recorded_by = Column(String)  # User who recorded the payment
    recorded_at = Column(DateTime, default=datetime.utcnow)
    branch_id = Column(ForeignKey("branches.id"))
    
    # Relationships
    purchase = relationship("Purchase", back_populates="payments")
    branch = relationship("Branch")
    
    def __repr__(self):
        return f"<PurchasePayment(id={self.id}, purchase_id={self.purchase_id}, amount={self.amount})>"


# Add this to the Purchase model relationship
# In app/models/purchases.py, add:
# payments = relationship("PurchasePayment", back_populates="purchase")