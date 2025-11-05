import uuid
from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Branch(BaseModel):
    """Branch model for multi-branch operations"""
    __tablename__ = "branches"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    code = Column(String, nullable=False, unique=True)
    location = Column(String)
    phone = Column(String)
    email = Column(String)
    address = Column(Text)
    is_head_office = Column(Boolean, default=False)
    # Additional fields for better branch management
    manager_id = Column(String)  # Could be linked to User model
    contact_person = Column(String)
    fax = Column(String)
    website = Column(String)
    timezone = Column(String, default="UTC")
    currency = Column(String, default="USD")
    active = Column(Boolean, default=True)
    notes = Column(Text)
    vat_registration_number = Column(String(50))  # VAT registration number for the branch
    company_logo_url = Column(String(255))  # URL/path to company logo
    
    # Relationships
    users = relationship("User", back_populates="branch")
    customers = relationship("Customer", back_populates="branch")
    suppliers = relationship("Supplier", back_populates="branch")
    products = relationship("Product", back_populates="branch")
    sales = relationship("Sale", back_populates="branch")
    purchases = relationship("Purchase", back_populates="branch")
    invoices = relationship("Invoice", back_populates="branch")
    purchase_orders = relationship("PurchaseOrder", back_populates="branch")
    pos_sessions = relationship("PosSession", back_populates="branch")
    bank_accounts = relationship("BankAccount", back_populates="branch")
    inventory_transactions = relationship("InventoryTransaction", back_populates="branch")
    inventory_adjustments = relationship("InventoryAdjustment", back_populates="branch")
    unit_of_measures = relationship("UnitOfMeasure", back_populates="branch")
    import_jobs = relationship("ImportJob", back_populates="branch")
    notifications = relationship("Notification", back_populates="branch") 
    job_cards = relationship("JobCard", back_populates="branch")