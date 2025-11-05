import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Text, Integer
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class User(BaseModel):
    """User model for authentication and authorization"""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, nullable=False, unique=True)
    password_digest = Column(String, nullable=False, default="")
    role = Column(String, default="staff", nullable=False)  # Legacy role field for backward compatibility
    role_id = Column(ForeignKey("roles.id"))  # New role relationship
    branch_id = Column(ForeignKey("branches.id"))
    # Additional fields for better user management
    email = Column(String, unique=True)
    first_name = Column(String)
    last_name = Column(String)
    phone = Column(String)
    address = Column(Text)
    active = Column(Boolean, default=True)
    last_login = Column(DateTime)
    login_count = Column(Integer, default=0)
    password_changed_at = Column(DateTime)
    notes = Column(Text)

    # Relationships
    branch = relationship("Branch", back_populates="users")
    role_obj = relationship("Role", back_populates="users")
    audit_logs = relationship("UserAuditLog", back_populates="user", cascade="all, delete-orphan")
    user_permissions = relationship("UserPermission", back_populates="user", cascade="all, delete-orphan")
    beneficiaries = relationship("Beneficiary", back_populates="user")
    pos_sessions = relationship("PosSession", back_populates="user", foreign_keys="PosSession.user_id")
    import_jobs = relationship("ImportJob", back_populates="user")
    notification_users = relationship("NotificationUser", back_populates="user")
    # Sales relationships (no back_populates since Sale side doesn't define them)
    sales = relationship("Sale", foreign_keys="Sale.salesperson_id")
    posted_sales = relationship("Sale", foreign_keys="Sale.posted_by")
    # Purchase relationships (no back_populates since Purchase side doesn't define them)
    created_purchases = relationship("Purchase", foreign_keys="Purchase.created_by")
    approved_purchases = relationship("Purchase", foreign_keys="Purchase.approved_by")
    created_purchase_orders = relationship("PurchaseOrder", foreign_keys="PurchaseOrder.created_by")
    approved_purchase_orders = relationship("PurchaseOrder", foreign_keys="PurchaseOrder.approved_by")
    # Invoice relationships (no back_populates since Invoice side doesn't define them)
    created_invoices = relationship("Invoice", foreign_keys="Invoice.created_by")
    posted_invoices = relationship("Invoice", foreign_keys="Invoice.posted_by")
    # Payment relationships (no back_populates since Payment side doesn't define them)
    created_payments = relationship("Payment", foreign_keys="Payment.created_by")
    # Inventory relationships - check if back_populates is needed
    created_inventory_transactions = relationship("InventoryTransaction", back_populates="created_by_user")
    created_inventory_adjustments = relationship("InventoryAdjustment", foreign_keys="InventoryAdjustment.created_by")
    approved_inventory_adjustments = relationship("InventoryAdjustment", foreign_keys="InventoryAdjustment.approved_by")
    # Notification relationships
    created_notifications = relationship("Notification", back_populates="created_by_user")
    # Report relationships
    generated_reports = relationship("Report", back_populates="generated_by_user")

    def __init__(self, **kwargs):  # Allow legacy test fixtures to pass hashed_password
        hashed = kwargs.pop("hashed_password", None)
        super().__init__(**kwargs)
        if hashed and not getattr(self, "password_digest", None):
            # Map legacy hashed_password field to password_digest storage
            self.password_digest = hashed
