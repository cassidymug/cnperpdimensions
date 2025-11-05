import uuid
from sqlalchemy import Column, String, Boolean, Text, Date, ForeignKey, Numeric, Integer
from sqlalchemy import types as _types
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


# Supplier model is defined in purchases.py


class UnitOfMeasure(BaseModel):
    """
    Comprehensive Unit of Measure system supporting:
    - Basic units (pieces, boxes)
    - Length (mm, cm, m, km, inch, foot, mile)
    - Area (mm², cm², m², hectare, acre)
    - Volume (ml, l, m³, gallon, fl oz)
    - Weight (mg, g, kg, ton, oz, lb)
    - Temperature (°C, °F, K)
    - Pressure (Pa, bar, psi, atm)
    - Speed (m/s, km/h, mph, knot)
    - Time (sec, min, hr, day)
    - Angle (degree, radian)
    - Nautical (nautical mile, knot, fathom)
    - Scientific (mol, candela, lux, etc.)
    """
    __tablename__ = "unit_of_measures"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    name = Column(String, nullable=False)  # e.g., "Millimeter"
    abbreviation = Column(String, nullable=False)  # e.g., "mm"
    symbol = Column(String, nullable=True)  # e.g., "㎜" for display

    # Category classification for filtering and organization
    category = Column(String, nullable=False)  # e.g., "length", "volume", "weight"
    subcategory = Column(String, nullable=True)  # e.g., "metric", "imperial", "nautical"

    description = Column(Text, nullable=True)

    # Conversion system - all units in a category convert to a base unit
    is_base_unit = Column(Boolean, default=False)  # e.g., meter is base for length
    base_unit_id = Column(ForeignKey("unit_of_measures.id"), nullable=True)
    conversion_factor = Column(Numeric(20, 10), default=1.0)  # Multiply by this to get base unit
    conversion_offset = Column(Numeric(20, 10), default=0.0)  # For temperature conversions

    # System and metadata
    is_system_unit = Column(Boolean, default=True)  # System-defined vs custom
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)  # For UI sorting

    # Optional precision and usage hints for BI module
    decimal_places = Column(Integer, default=2)  # Suggested decimal precision
    usage_hint = Column(Text, nullable=True)  # e.g., "Used for precise machining"

    branch_id = Column(ForeignKey("branches.id"), nullable=True)  # NULL for global units

    # Relationships
    branch = relationship("Branch", lazy="select")
    products = relationship("Product", back_populates="unit_of_measure", lazy="select")
    base_unit = relationship("UnitOfMeasure", remote_side=[id], foreign_keys=[base_unit_id], lazy="select")
    derived_units = relationship("UnitOfMeasure", foreign_keys=[base_unit_id], overlaps="base_unit", lazy="select")


class Product(BaseModel):
    """Product model for inventory management"""
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    name = Column(String)
    sku = Column(String, unique=True)
    description = Column(Text)
    quantity = Column(Integer)
    barcode = Column(String)
    accounting_code_id = Column(ForeignKey("accounting_codes.id"))
    cost_price = Column(Numeric(15, 2), default=0.0)
    unit_of_measure_id = Column(ForeignKey("unit_of_measures.id"), nullable=True)
    selling_price = Column(Numeric(15, 2), default=0.0)
    is_serialized = Column(Boolean, default=False, nullable=False)
    branch_id = Column(ForeignKey("branches.id"))
    is_perishable = Column(Boolean)
    expiry_date = Column(Date)
    batch_number = Column(String)
    warranty_period_months = Column(Integer)
    warranty_period_years = Column(Integer)
    is_recurring_income = Column(Boolean, default=False, nullable=False)
    recurring_income_type = Column(String)
    recurring_amount = Column(Numeric(15, 2))
    recurring_interval = Column(String)
    recurring_start_date = Column(Date)
    recurring_end_date = Column(Date)
    recurring_description = Column(Text)
    product_type = Column(String, default="inventory_item")
    # Additional fields for better product management
    category = Column(String)
    brand = Column(String)
    model = Column(String)
    weight = Column(Numeric(10, 2))
    dimensions = Column(String)
    supplier_id = Column(ForeignKey("suppliers.id"))
    minimum_stock_level = Column(Integer, default=0)
    maximum_stock_level = Column(Integer)
    reorder_point = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    notes = Column(Text)
    image_url = Column(String)  # URL/path to product image
    is_taxable = Column(Boolean, default=True)  # Whether the product is subject to VAT/tax

    # Weight-based product fields (for meat, fruits, vegetables sold by weight)
    is_weight_based = Column(Boolean, default=False, nullable=False)  # Product sold by weight
    weight_barcode_prefix = Column(String(2))  # Barcode type: 20=meat, 21=fruits, 22=vegetables
    price_per_kg = Column(Numeric(15, 2))  # Price per kilogram
    price_per_gram = Column(Numeric(15, 4))  # Price per gram (auto-calculated)
    tare_weight = Column(Numeric(10, 3), default=0)  # Container weight in grams
    min_weight = Column(Numeric(10, 3))  # Minimum sellable weight in grams
    max_weight = Column(Numeric(10, 3))  # Maximum sellable weight in grams
    weight_barcode_sku = Column(String(5))  # 5-digit product code for weight barcodes

    # Relationships
    accounting_code = relationship("AccountingCode", lazy="select")
    unit_of_measure = relationship("UnitOfMeasure", back_populates="products", lazy="select")
    branch = relationship("Branch", lazy="select")
    supplier = relationship("Supplier", lazy="select")
    inventory_transactions = relationship("InventoryTransaction", back_populates="product", lazy="select")
    inventory_adjustments = relationship("InventoryAdjustment", back_populates="product", lazy="select")
    serial_numbers = relationship("SerialNumber", back_populates="product", lazy="select")
    assembled_products = relationship("ProductAssembly", foreign_keys="ProductAssembly.assembled_product_id", lazy="select")
    components = relationship("ProductAssembly", foreign_keys="ProductAssembly.component_id", lazy="select")
    sale_items = relationship("SaleItem", back_populates="product", lazy="select")
    invoice_items = relationship("InvoiceItem", back_populates="product", lazy="select")
    purchase_items = relationship("PurchaseItem", back_populates="product", lazy="select")
    cogs_entries = relationship("COGSEntry", back_populates="product", lazy="select")
    manufacturing_costs = relationship("ManufacturingCost", back_populates="product", lazy="select")


class ProductAssembly(BaseModel):
    """Bill of materials for assembled products"""
    __tablename__ = "product_assemblies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    assembled_product_id = Column(ForeignKey("products.id"), nullable=False)
    component_id = Column(ForeignKey("products.id"), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    # Additional fields for better BOM management
    unit_of_measure_id = Column(ForeignKey("unit_of_measures.id"), nullable=True)
    unit_cost = Column(Numeric(15, 2))
    total_cost = Column(Numeric(15, 2))
    notes = Column(Text)

    # Relationships
    assembled_product = relationship("Product", foreign_keys=[assembled_product_id], overlaps="assembled_products")
    component = relationship("Product", foreign_keys=[component_id], overlaps="components")
    unit_of_measure = relationship("UnitOfMeasure", foreign_keys=[unit_of_measure_id], lazy="select")


class InventoryTransaction(BaseModel):
    """Inventory movement transactions"""
    __tablename__ = "inventory_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    product_id = Column(ForeignKey("products.id"), nullable=False)
    transaction_type = Column(String)
    quantity = Column(Integer)
    note = Column(Text)
    unit_cost = Column(Numeric(15, 2), default=0.0)
    reference = Column(String)
    # Use hybrid type that supports PostgreSQL ARRAY and JSON fallback
    from app.models.types import StringArray
    serial_numbers = Column(StringArray, default=list)
    purchase_item_id = Column(Integer)
    date = Column(Date)
    branch_id = Column(ForeignKey("branches.id"))
    # Additional fields for better transaction tracking
    total_cost = Column(Numeric(15, 2))
    previous_quantity = Column(Integer)
    new_quantity = Column(Integer)
    created_by = Column(ForeignKey("users.id"))
    related_sale_id = Column(ForeignKey("sales.id"))
    related_purchase_id = Column(ForeignKey("purchases.id"))
    related_adjustment_id = Column(ForeignKey("inventory_adjustments.id"))
    related_job_card_id = Column(String, ForeignKey("job_cards.id"))

    # Relationships
    product = relationship("Product", back_populates="inventory_transactions")
    branch = relationship("Branch")
    created_by_user = relationship("User")
    related_sale = relationship("Sale")
    related_purchase = relationship("Purchase")
    related_adjustment = relationship("InventoryAdjustment")
    serial_numbers_rel = relationship("SerialNumber", back_populates="inventory_transaction")
    job_card = relationship("JobCard", back_populates="inventory_transactions")


class InventoryAdjustment(BaseModel):
    """Inventory adjustments for stock corrections"""
    __tablename__ = "inventory_adjustments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    product_id = Column(ForeignKey("products.id"), nullable=False)
    adjustment_date = Column(Date)
    quantity = Column(Integer)
    reason = Column(String)
    total_amount = Column(Numeric(15, 2))
    accounting_entry_type = Column(String, nullable=False)
    accounting_entry_id = Column(ForeignKey("accounting_entries.id"), nullable=False)
    branch_id = Column(ForeignKey("branches.id"))
    # Additional fields for better adjustment tracking
    adjustment_type = Column(String)  # gain, loss, correction
    previous_quantity = Column(Integer)
    new_quantity = Column(Integer)
    unit_cost = Column(Numeric(15, 2))
    created_by = Column(ForeignKey("users.id"))
    approved_by = Column(ForeignKey("users.id"))
    approved_at = Column(Date)
    notes = Column(Text)

    # Relationships
    product = relationship("Product", back_populates="inventory_adjustments")
    accounting_entry = relationship("AccountingEntry")
    branch = relationship("Branch")
    created_by_user = relationship("User", foreign_keys=[created_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])


class SerialNumber(BaseModel):
    """Serial number tracking for products"""
    __tablename__ = "serial_numbers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    serial = Column(String, unique=True)
    product_id = Column(ForeignKey("products.id"), nullable=False)
    inventory_transaction_id = Column(ForeignKey("inventory_transactions.id"), nullable=False)
    purchase_id = Column(String, ForeignKey("purchases.id"), nullable=True, index=True)
    status = Column(String)
    warranty_expires_at = Column(Date)
    # Additional fields for better serial number tracking
    purchase_date = Column(Date)
    supplier_id = Column(ForeignKey("suppliers.id"))
    customer_id = Column(ForeignKey("customers.id"))
    location = Column(String)
    notes = Column(Text)
    active = Column(Boolean, default=True)

    # Relationships
    product = relationship("Product", back_populates="serial_numbers", lazy="select")
    inventory_transaction = relationship("InventoryTransaction", back_populates="serial_numbers_rel", lazy="select")
    supplier = relationship("Supplier", back_populates="serial_numbers", lazy="select")
    customer = relationship("Customer", back_populates="serial_numbers", lazy="select")
    purchase = relationship("Purchase", back_populates="serial_numbers", lazy="select")


# --- COGSEntry model for COGS tracking ---
class COGSEntry(BaseModel):
    """Cost of Goods Sold entry for products and purchases"""
    __tablename__ = "cogs_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(ForeignKey("products.id"), nullable=False)
    purchase_item_id = Column(ForeignKey("purchase_items.id"), nullable=True)  # Optional for legacy products
    cost = Column(Numeric(15, 2), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    date = Column(Date)
    notes = Column(Text)
    created_by = Column(ForeignKey("users.id"))
    branch_id = Column(ForeignKey("branches.id"))

    # Relationships (cleaned)
    product = relationship("Product", back_populates="cogs_entries", lazy="select")
    purchase_item = relationship("PurchaseItem", lazy="select")
    branch = relationship("Branch", lazy="select")
    created_by_user = relationship("User", lazy="select")
