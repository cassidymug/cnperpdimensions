import uuid
from sqlalchemy import Column, String, Text, Date, ForeignKey, Numeric, Integer, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Budget(BaseModel):
    """Budget model for fund allocation and management"""
    __tablename__ = "budgets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    name = Column(String, nullable=False)
    description = Column(Text)
    budget_type = Column(String, default="project")  # project, department, category, general
    total_amount = Column(Numeric(15, 2), nullable=False)
    allocated_amount = Column(Numeric(15, 2), default=0.0)
    spent_amount = Column(Numeric(15, 2), default=0.0)
    remaining_amount = Column(Numeric(15, 2), default=0.0)
    
    # Budget period
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Status and control
    status = Column(String, default="active")  # active, suspended, closed, archived
    is_approved = Column(Boolean, default=False)
    approved_by = Column(ForeignKey("users.id"))
    approved_at = Column(DateTime)
    
    # Bank account integration
    bank_account_id = Column(ForeignKey("bank_accounts.id"))
    
    # Budget hierarchy
    parent_budget_id = Column(ForeignKey("budgets.id"))
    
    # Branch and accounting
    branch_id = Column(ForeignKey("branches.id"))
    accounting_code_id = Column(ForeignKey("accounting_codes.id"))
    
    # Relationships
    bank_account = relationship("BankAccount")
    parent_budget = relationship("Budget", remote_side=[id])
    sub_budgets = relationship("Budget", back_populates="parent_budget")
    branch = relationship("Branch")
    accounting_code = relationship("AccountingCode")
    approved_by_user = relationship("User", foreign_keys=[approved_by])
    allocations = relationship("BudgetAllocation", back_populates="budget")
    transactions = relationship("BudgetTransaction", back_populates="budget")
    user_access = relationship("BudgetUserAccess", back_populates="budget")


class BudgetAllocation(BaseModel):
    """Budget allocation for specific purposes/projects"""
    __tablename__ = "budget_allocations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    budget_id = Column(ForeignKey("budgets.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    allocated_amount = Column(Numeric(15, 2), nullable=False)
    spent_amount = Column(Numeric(15, 2), default=0.0)
    remaining_amount = Column(Numeric(15, 2), default=0.0)
    
    # Allocation period
    start_date = Column(Date)
    end_date = Column(Date)
    
    # Status
    status = Column(String, default="active")  # active, suspended, closed
    
    # Category and tracking
    category = Column(String)  # procurement, travel, equipment, etc.
    project_code = Column(String)
    
    # Relationships
    budget = relationship("Budget", back_populates="allocations")
    transactions = relationship("BudgetTransaction", back_populates="allocation")


class BudgetTransaction(BaseModel):
    """Budget transaction tracking"""
    __tablename__ = "budget_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    budget_id = Column(ForeignKey("budgets.id"), nullable=False)
    allocation_id = Column(ForeignKey("budget_allocations.id"))
    
    # Transaction details
    transaction_type = Column(String, nullable=False)  # purchase, expense, transfer, adjustment
    amount = Column(Numeric(15, 2), nullable=False)
    description = Column(Text, nullable=False)
    reference = Column(String)  # PO number, invoice number, etc.
    
    # Related entities
    purchase_id = Column(ForeignKey("purchases.id"))
    purchase_order_id = Column(ForeignKey("purchase_orders.id"))
    bank_transaction_id = Column(ForeignKey("bank_transactions.id"))
    
    # User tracking
    created_by = Column(ForeignKey("users.id"), nullable=False)
    approved_by = Column(ForeignKey("users.id"))
    approved_at = Column(DateTime)
    
    # Status
    status = Column(String, default="pending")  # pending, approved, rejected, cancelled
    
    # Relationships
    budget = relationship("Budget", back_populates="transactions")
    allocation = relationship("BudgetAllocation", back_populates="transactions")
    purchase = relationship("Purchase")
    purchase_order = relationship("PurchaseOrder")
    bank_transaction = relationship("BankTransaction")
    created_by_user = relationship("User", foreign_keys=[created_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])


class BudgetUserAccess(BaseModel):
    """User access control for budgets"""
    __tablename__ = "budget_user_access"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    budget_id = Column(ForeignKey("budgets.id"), nullable=False)
    user_id = Column(ForeignKey("users.id"), nullable=False)
    
    # Access levels
    can_view = Column(Boolean, default=True)
    can_allocate = Column(Boolean, default=False)
    can_spend = Column(Boolean, default=False)
    can_approve = Column(Boolean, default=False)
    can_manage = Column(Boolean, default=False)  # Full admin access
    
    # Access period
    access_start_date = Column(Date)
    access_end_date = Column(Date)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Relationships
    budget = relationship("Budget", back_populates="user_access")
    user = relationship("User")


class BudgetRequest(BaseModel):
    """Budget request/approval workflow"""
    __tablename__ = "budget_requests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Request details
    title = Column(String, nullable=False)
    description = Column(Text)
    requested_amount = Column(Numeric(15, 2), nullable=False)
    requested_by = Column(ForeignKey("users.id"), nullable=False)
    requested_at = Column(DateTime, nullable=False)
    
    # Budget context
    budget_id = Column(ForeignKey("budgets.id"))
    allocation_id = Column(ForeignKey("budget_allocations.id"))
    
    # Approval workflow
    status = Column(String, default="pending")  # pending, approved, rejected, cancelled
    approved_by = Column(ForeignKey("users.id"))
    approved_at = Column(DateTime)
    approved_amount = Column(Numeric(15, 2))
    rejection_reason = Column(Text)
    
    # Priority and urgency
    priority = Column(String, default="normal")  # low, normal, high, urgent
    urgency_level = Column(Integer, default=1)  # 1-5 scale
    
    # Relationships
    budget = relationship("Budget")
    allocation = relationship("BudgetAllocation")
    requested_by_user = relationship("User", foreign_keys=[requested_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])
