import uuid
from sqlalchemy import Column, String, Boolean, Text, Date, ForeignKey, Numeric, Integer, DateTime
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Supplier(BaseModel):
    """Supplier model for purchasing"""
    __tablename__ = "suppliers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    name = Column(String, nullable=False)
    email = Column(String)
    telephone = Column(String)
    address = Column(Text)
    accounting_code_id = Column(ForeignKey("accounting_codes.id"), nullable=False)
    vat_reg_number = Column(String(50))
    branch_id = Column(ForeignKey("branches.id"))
    # Additional fields for better supplier management
    supplier_type = Column(String, default="vendor")  # vendor, manufacturer, distributor
    contact_person = Column(String)
    payment_terms = Column(Integer, default=30)  # days
    credit_limit = Column(Numeric(15, 2), default=0.0)
    current_balance = Column(Numeric(15, 2), default=0.0)
    tax_exempt = Column(Boolean, default=False)
    active = Column(Boolean, default=True)
    notes = Column(Text)

    # Relationships
    accounting_code = relationship("AccountingCode")
    branch = relationship("Branch")
    purchases = relationship("Purchase", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")
    products = relationship("Product", back_populates="supplier")
    serial_numbers = relationship("SerialNumber", back_populates="supplier")


class Purchase(BaseModel):
    """Purchase transaction model"""
    __tablename__ = "purchases"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    purchase_date = Column(Date)
    total_amount = Column(Numeric(15, 2))
    supplier_id = Column(ForeignKey("suppliers.id"), nullable=False)
    amount_paid = Column(Numeric(15, 2), default=0.0, nullable=False)
    total_vat_amount = Column(Numeric(15, 2), default=0.0)
    status = Column(String, default="pending", nullable=False)
    due_date = Column(Date)
    total_amount_ex_vat = Column(Numeric(15, 2))
    payment_account_id = Column(ForeignKey("accounting_codes.id"))
    branch_id = Column(ForeignKey("branches.id"))
    bank_account_id = Column(String, ForeignKey("bank_accounts.id"))
    supplier_invoice_number = Column(String(100))
    # Additional fields for better purchase tracking
    reference = Column(String)
    notes = Column(Text)
    created_by = Column(ForeignKey("users.id"))
    approved_by = Column(ForeignKey("users.id"))
    approved_at = Column(Date)
    received_at = Column(Date)
    discount_amount = Column(Numeric(15, 2), default=0.0)
    discount_percentage = Column(Numeric(5, 2), default=0.0)
    shipping_cost = Column(Numeric(15, 2), default=0.0)
    handling_cost = Column(Numeric(15, 2), default=0.0)

    # Accounting Dimensions - for GL posting and cost tracking
    cost_center_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True, index=True)
    project_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)
    department_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)

    # GL Account mapping - for automatic journal entry creation
    expense_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)
    payable_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)
    input_vat_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)  # VAT Receivable (Input VAT) account

    # Accounting posting status
    posting_status = Column(String(20), default="draft", nullable=False, index=True)
    last_posted_date = Column(DateTime, nullable=True)
    posted_by = Column(String, ForeignKey("users.id"), nullable=True)

    # Relationships
    supplier = relationship("Supplier", back_populates="purchases")
    payment_account = relationship("AccountingCode", foreign_keys=[payment_account_id])
    branch = relationship("Branch")
    purchase_items = relationship("PurchaseItem", back_populates="purchase")
    created_by_user = relationship("User", foreign_keys=[created_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])
    inventory_transactions = relationship("InventoryTransaction", back_populates="related_purchase")
    landed_costs = relationship("LandedCost", back_populates="purchase")
    journal_entries = relationship("JournalEntry", back_populates="purchase")
    serial_numbers = relationship("SerialNumber", back_populates="purchase")
    payments = relationship("PurchasePayment", back_populates="purchase")

    # Accounting dimension relationships
    cost_center = relationship("AccountingDimensionValue", foreign_keys=[cost_center_id])
    project = relationship("AccountingDimensionValue", foreign_keys=[project_id])
    department = relationship("AccountingDimensionValue", foreign_keys=[department_id])

    # GL account relationships
    expense_account = relationship("AccountingCode", foreign_keys=[expense_account_id])
    payable_account = relationship("AccountingCode", foreign_keys=[payable_account_id])
    input_vat_account = relationship("AccountingCode", foreign_keys=[input_vat_account_id])

    # Audit relationship
    posted_by_user = relationship("User", foreign_keys=[posted_by])


class PurchaseItem(BaseModel):
    """Individual items in a purchase (supports inventory or asset lines)"""
    __tablename__ = "purchase_items"
    # NOTE: New asset-related columns added; ensure Alembic migration is created to reflect schema changes.

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Allow free-text / asset lines without product linkage
    product_id = Column(ForeignKey("products.id"), nullable=True)
    quantity = Column(Numeric(10, 2))
    cost = Column(Numeric(15, 2))
    purchase_id = Column(ForeignKey("purchases.id"), nullable=False)
    total_cost = Column(Numeric(15, 2))
    vat_amount = Column(Numeric(15, 2), default=0.0)
    from app.models.types import StringArray
    serial_numbers = Column(StringArray, default=list)
    new_selling_price = Column(Numeric(15, 2))
    is_inventory = Column(Boolean, default=True)
    # Additional fields for better item tracking
    description = Column(Text)
    vat_rate = Column(Numeric(8, 4), default=0.0)
    discount_amount = Column(Numeric(10, 2), default=0.0)
    discount_percentage = Column(Numeric(5, 2), default=0.0)
    received_quantity = Column(Numeric(10, 2), default=0.0)
    notes = Column(Text)
    vat_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)  # Line-level VAT account override

    # Asset extension fields (mirror schema PurchaseItemBase)
    is_asset = Column(Boolean, default=False)
    asset_name = Column(String)
    asset_category = Column(String)
    asset_depreciation_method = Column(String)
    asset_useful_life_years = Column(Integer)
    asset_salvage_value = Column(Numeric(15, 2))
    asset_serial_number = Column(String)
    asset_vehicle_registration = Column(String(50))
    asset_engine_number = Column(String(100))
    asset_chassis_number = Column(String(100))
    asset_accounting_code_id = Column(String(36), ForeignKey("accounting_codes.id"))
    # Extended optional metadata (not yet migrated): location, custodian, purchase ref, tag, warranty expiry, notes, accumulated depreciation account
    asset_location = Column(String)
    asset_custodian = Column(String)
    asset_purchase_ref = Column(String)
    asset_tag = Column(String)
    asset_warranty_expiry = Column(Date)
    asset_notes = Column(Text)
    asset_accum_depr_account_code_id = Column(String(36), ForeignKey("accounting_codes.id"))
    vat_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)  # Line-level VAT account override

    # Relationships
    product = relationship("Product", back_populates="purchase_items")
    purchase = relationship("Purchase", back_populates="purchase_items")
    vat_account = relationship("AccountingCode", foreign_keys=[vat_account_id])


class PurchaseOrder(BaseModel):
    """Purchase order model"""
    __tablename__ = "purchase_orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    supplier_id = Column(ForeignKey("suppliers.id"), nullable=False)
    date = Column(Date)
    status = Column(String)
    # Additional fields for better PO tracking
    po_number = Column(String, unique=True)
    expected_delivery_date = Column(Date)
    total_amount = Column(Numeric(15, 2))
    total_vat_amount = Column(Numeric(15, 2), default=0.0)
    notes = Column(Text)
    created_by = Column(ForeignKey("users.id"))
    approved_by = Column(ForeignKey("users.id"))
    approved_at = Column(Date)
    branch_id = Column(ForeignKey("branches.id"))

    # Accounting Dimensions - for GL posting and cost tracking
    cost_center_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True, index=True)
    project_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)
    department_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)

    # GL Account mapping - for automatic journal entry creation
    expense_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)

    # Accounting posting status
    posting_status = Column(String(20), default="draft", nullable=False, index=True)

    # Relationships
    supplier = relationship("Supplier", back_populates="purchase_orders")
    created_by_user = relationship("User", foreign_keys=[created_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])
    branch = relationship("Branch")
    purchase_order_items = relationship("PurchaseOrderItem", back_populates="purchase_order")

    # Accounting dimension relationships
    cost_center = relationship("AccountingDimensionValue", foreign_keys=[cost_center_id])
    project = relationship("AccountingDimensionValue", foreign_keys=[project_id])
    department = relationship("AccountingDimensionValue", foreign_keys=[department_id])

    # GL account relationship
    expense_account = relationship("AccountingCode", foreign_keys=[expense_account_id])


class PurchaseOrderItem(BaseModel):
    """Individual items in a purchase order"""
    __tablename__ = "purchase_order_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    purchase_order_id = Column(ForeignKey("purchase_orders.id"), nullable=False)
    product_id = Column(ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_cost = Column(Numeric(15, 2))
    total_cost = Column(Numeric(15, 2))
    vat_rate = Column(Numeric(8, 4), default=0.0)
    vat_amount = Column(Numeric(15, 2), default=0.0)
    description = Column(Text)
    notes = Column(Text)

    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="purchase_order_items")
    product = relationship("Product")
