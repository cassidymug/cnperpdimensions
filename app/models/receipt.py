from datetime import datetime
import uuid

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer, Numeric
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class Receipt(BaseModel):
    """Receipt model for storing generated receipts"""
    __tablename__ = "receipts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sale_id = Column(ForeignKey("sales.id"), nullable=True)
    invoice_id = Column(ForeignKey("invoices.id"), nullable=True)
    payment_id = Column(ForeignKey("payments.id"), nullable=True)
    customer_id = Column(ForeignKey("customers.id"), nullable=True)
    receipt_number = Column(String, unique=True, nullable=False)
    amount = Column(Numeric(15, 2), default=0.0)
    currency = Column(String, default="BWP")
    payment_method = Column(String, nullable=True)
    payment_date = Column(DateTime, nullable=True)
    pdf_path = Column(String, nullable=True)  # Path to stored PDF file
    html_content = Column(Text, nullable=True)  # HTML version for web display
    notes = Column(Text, nullable=True)
    printed = Column(Boolean, default=False)
    print_count = Column(Integer, default=0)
    created_by_user_id = Column(ForeignKey("users.id"), nullable=False)
    branch_id = Column(ForeignKey("branches.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sale = relationship("Sale")
    invoice = relationship("Invoice")
    payment = relationship("Payment")
    customer = relationship("Customer")
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    branch = relationship("Branch")
