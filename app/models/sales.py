import uuid
from sqlalchemy import Column, String, Boolean, Text, Date, ForeignKey, Numeric, Integer, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Customer(BaseModel):
    """Customer model for sales and CRM"""
    __tablename__ = "customers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    name = Column(String)
    email = Column(String)
    phone = Column(String)
    address = Column(Text)
    account_balance = Column(Numeric(15, 2), default=0.0)
    vat_reg_number = Column(String(50))
    accounting_code_id = Column(ForeignKey("accounting_codes.id"))
    credit_limit = Column(Numeric(12, 2), default=0.0)
    branch_id = Column(ForeignKey("branches.id"))
    # Additional fields for better customer management
    customer_type = Column(String, default="retail")  # retail, wholesale, corporate
    tax_exempt = Column(Boolean, default=False)
    payment_terms = Column(Integer, default=30)  # days
    contact_person = Column(String)
    notes = Column(Text)
    active = Column(Boolean, default=True)

    # Relationships
    accounting_code = relationship("AccountingCode")
    branch = relationship("Branch")
    sales = relationship("Sale", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")
    payments = relationship("Payment", back_populates="customer")
    billing_cycles = relationship("BillingCycle", back_populates="customer")
    credit_notes = relationship("CreditNote", back_populates="customer")
    serial_numbers = relationship("SerialNumber", back_populates="customer")
    job_cards = relationship("JobCard", back_populates="customer")


class Sale(BaseModel):
    """Sales transaction model"""
    __tablename__ = "sales"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    customer_id = Column(ForeignKey("customers.id"))
    payment_method = Column(String)
    date = Column(DateTime)
    currency = Column(String)
    total_amount = Column(Numeric(15, 2))
    amount_tendered = Column(Numeric(15, 2))
    change_given = Column(Numeric(15, 2), default=0.0)
    total_vat_amount = Column(Numeric(15, 2), default=0.0)
    status = Column(String, default="completed", nullable=False)
    total_amount_ex_vat = Column(Numeric(15, 2))
    sale_time = Column(DateTime)
    branch_id = Column(ForeignKey("branches.id"))
    # Additional fields for better sales tracking
    pos_session_id = Column(ForeignKey("pos_sessions.id"))
    salesperson_id = Column(ForeignKey("users.id"))
    reference = Column(String)
    notes = Column(Text)
    discount_amount = Column(Numeric(15, 2), default=0.0)
    discount_percentage = Column(Numeric(5, 2), default=0.0)

    # Accounting Dimensions - for GL posting and dimensional revenue tracking
    cost_center_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True, index=True)
    project_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)
    department_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)

    # GL Account mapping - for automatic journal entry creation
    revenue_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)
    output_vat_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)  # VAT Payable (Output VAT) account

    # Accounting posting status
    posting_status = Column(String(20), default="draft", nullable=False, index=True)
    last_posted_date = Column(DateTime, nullable=True)
    posted_by = Column(String, ForeignKey("users.id"), nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="sales")
    branch = relationship("Branch")
    sale_items = relationship("SaleItem", back_populates="sale")
    pos_session = relationship("PosSession")
    salesperson = relationship("User", foreign_keys=[salesperson_id], overlaps="sales")

    # Accounting dimension relationships
    cost_center = relationship("AccountingDimensionValue", foreign_keys=[cost_center_id])
    project = relationship("AccountingDimensionValue", foreign_keys=[project_id])
    department = relationship("AccountingDimensionValue", foreign_keys=[department_id])

    # GL account relationships
    revenue_account = relationship("AccountingCode", foreign_keys=[revenue_account_id])
    output_vat_account = relationship("AccountingCode", foreign_keys=[output_vat_account_id])

    # Audit relationship
    posted_by_user = relationship("User", foreign_keys=[posted_by], overlaps="posted_sales")


class SaleItem(BaseModel):
    """Individual items in a sale"""
    __tablename__ = "sale_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    sale_id = Column(ForeignKey("sales.id"), nullable=False)
    product_id = Column(ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer)
    selling_price = Column(Numeric(10, 2))
    vat_amount = Column(Numeric(15, 2), default=0.0)
    serial_numbers = Column(Text, default='[]')
    vat_rate = Column(Numeric(8, 4), default=0.0, nullable=False)
    # Additional fields for better item tracking
    cost_price = Column(Numeric(10, 2))
    discount_amount = Column(Numeric(10, 2), default=0.0)
    discount_percentage = Column(Numeric(5, 2), default=0.0)
    total_amount = Column(Numeric(15, 2))
    notes = Column(Text)
    vat_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)  # Line-level VAT account override

    # Relationships
    sale = relationship("Sale", back_populates="sale_items")
    product = relationship("Product")
    vat_account = relationship("AccountingCode", foreign_keys=[vat_account_id])


class Invoice(BaseModel):
    """Invoice model for billing customers"""
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    customer_id = Column(ForeignKey("customers.id"), nullable=False)
    quotation_id = Column(ForeignKey("quotations.id"), nullable=True)  # Link to quotation
    date = Column(Date)
    status = Column(String)
    total = Column(Numeric(15, 2))
    amount_paid = Column(Numeric(15, 2), default=0.0)
    total_vat_amount = Column(Numeric(15, 2), default=0.0)
    total_amount = Column(Numeric(12, 2), default=0.0)
    invoice_number = Column(String, nullable=False, unique=True)
    branch_id = Column(ForeignKey("branches.id"))
    # Additional fields for better invoice management
    due_date = Column(Date)
    payment_terms = Column(Integer, default=30)
    discount_amount = Column(Numeric(15, 2), default=0.0)
    discount_percentage = Column(Numeric(5, 2), default=0.0)
    notes = Column(Text)
    created_by = Column(ForeignKey("users.id"))
    sent_at = Column(DateTime)
    paid_at = Column(DateTime)
    job_card_id = Column(String, ForeignKey("job_cards.id"))

    # Accounting Dimensions - for GL posting and dimensional revenue tracking
    cost_center_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True, index=True)
    project_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)
    department_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)

    # GL Account mapping - for automatic journal entry creation
    revenue_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)
    ar_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)

    # Accounting posting status
    posting_status = Column(String(20), default="draft", nullable=False, index=True)
    last_posted_date = Column(DateTime, nullable=True)
    posted_by = Column(String, ForeignKey("users.id"), nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="invoices")
    quotation = relationship("Quotation", back_populates="invoices")
    branch = relationship("Branch")
    invoice_items = relationship("InvoiceItem", back_populates="invoice")
    payments = relationship("Payment", back_populates="invoice")
    created_by_user = relationship("User", foreign_keys=[created_by])
    credit_notes = relationship("CreditNote", back_populates="original_invoice")
    job_card = relationship("JobCard", back_populates="invoice")

    # Accounting dimension relationships
    cost_center = relationship("AccountingDimensionValue", foreign_keys=[cost_center_id])
    project = relationship("AccountingDimensionValue", foreign_keys=[project_id])
    department = relationship("AccountingDimensionValue", foreign_keys=[department_id])

    # GL account relationships
    revenue_account = relationship("AccountingCode", foreign_keys=[revenue_account_id])
    ar_account = relationship("AccountingCode", foreign_keys=[ar_account_id])

    # Audit relationship
    posted_by_user = relationship("User", foreign_keys=[posted_by])


class InvoiceItem(BaseModel):
    """Individual items in an invoice"""
    __tablename__ = "invoice_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    invoice_id = Column(ForeignKey("invoices.id"), nullable=False)
    product_id = Column(ForeignKey("products.id"), nullable=True)  # Made nullable for custom items
    quantity = Column(Numeric(10, 2))
    price = Column(Numeric(15, 2))
    total = Column(Numeric(15, 2))
    vat_amount = Column(Numeric(15, 2), default=0.0)
    serial_numbers = Column(Text)
    # Additional fields for better item tracking
    description = Column(Text)
    vat_rate = Column(Numeric(8, 4), default=0.0)
    discount_amount = Column(Numeric(10, 2), default=0.0)
    discount_percentage = Column(Numeric(5, 2), default=0.0)

    # Relationships
    invoice = relationship("Invoice", back_populates="invoice_items")
    product = relationship("Product")


class Payment(BaseModel):
    """Payment model for customer payments"""
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    invoice_id = Column(ForeignKey("invoices.id"), nullable=False)
    customer_id = Column(ForeignKey("customers.id"), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    payment_date = Column(Date, nullable=False)
    payment_method = Column(String, nullable=False)
    reference = Column(String)
    note = Column(Text)
    # Additional fields for better payment tracking
    payment_status = Column(String, default="completed")
    bank_account_id = Column(ForeignKey("bank_accounts.id"))
    transaction_id = Column(String)
    created_by = Column(ForeignKey("users.id"))

    # Relationships
    invoice = relationship("Invoice", back_populates="payments")
    customer = relationship("Customer", back_populates="payments")
    bank_account = relationship("BankAccount")
    created_by_user = relationship("User")

class Quotation(BaseModel):
    """Quotation/Quote model for sales"""
    __tablename__ = "quotations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    quote_number = Column(String, unique=True, nullable=False)
    customer_id = Column(ForeignKey("customers.id"), nullable=False)
    date = Column(Date, nullable=False)
    valid_until = Column(Date)
    reference = Column(String)
    notes = Column(Text)
    status = Column(String, default="draft")  # draft, created, sent, accepted, rejected, expired
    subtotal = Column(Numeric(15, 2), default=0.0)
    vat = Column(Numeric(15, 2), default=0.0)
    total = Column(Numeric(15, 2), default=0.0)
    branch_id = Column(ForeignKey("branches.id"))
    created_by = Column(ForeignKey("users.id"))

    # Relationships
    customer = relationship("Customer")
    branch = relationship("Branch")
    created_by_user = relationship("User")
    items = relationship("QuotationItem", back_populates="quotation", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="quotation")


class QuotationItem(BaseModel):
    """Individual items in a quotation"""
    __tablename__ = "quotation_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    quotation_id = Column(ForeignKey("quotations.id"), nullable=False)
    product_id = Column(ForeignKey("products.id"), nullable=True)  # Made nullable for custom items
    description = Column(Text, nullable=True)  # For custom text descriptions (labor, services, etc.)
    quantity = Column(Numeric(10, 2), nullable=False)
    price = Column(Numeric(15, 2), nullable=False)
    discount = Column(Numeric(5, 2), default=0.0)
    line_total = Column(Numeric(15, 2))

    # Relationships
    quotation = relationship("Quotation", back_populates="items")
    product = relationship("Product")
