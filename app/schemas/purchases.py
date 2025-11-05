from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import datetime, date
from app.schemas.landed_cost import LandedCostItemCreate


class SupplierBase(BaseModel):
    """Base supplier schema"""
    name: str
    email: Optional[str] = None
    telephone: Optional[str] = None
    address: Optional[str] = None
    accounting_code_id: str
    vat_reg_number: Optional[str] = None
    branch_id: Optional[str] = None
    supplier_type: str = "vendor"
    contact_person: Optional[str] = None
    payment_terms: int = 30
    credit_limit: Decimal = Decimal('0.00')
    current_balance: Decimal = Decimal('0.00')
    tax_exempt: bool = False
    active: bool = True
    notes: Optional[str] = None


class SupplierCreate(SupplierBase):
    """Supplier creation schema"""
    pass


class SupplierUpdate(BaseModel):
    """Supplier update schema"""
    name: Optional[str] = None
    email: Optional[str] = None
    telephone: Optional[str] = None
    address: Optional[str] = None
    accounting_code_id: Optional[str] = None
    vat_reg_number: Optional[str] = None
    branch_id: Optional[str] = None
    supplier_type: Optional[str] = None
    contact_person: Optional[str] = None
    payment_terms: Optional[int] = None
    credit_limit: Optional[Decimal] = None
    current_balance: Optional[Decimal] = None
    tax_exempt: Optional[bool] = None
    active: Optional[bool] = None
    notes: Optional[str] = None


class SupplierResponse(SupplierBase):
    """Supplier response schema"""
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseItemBase(BaseModel):
    """Base purchase item schema"""
    product_id: Optional[str] = None
    quantity: Decimal
    cost: Decimal
    total_cost: Optional[Decimal] = None
    vat_amount: Optional[Decimal] = Decimal('0.00')
    vat_rate: Optional[Decimal] = Decimal('0.00')
    description: Optional[str] = None
    notes: Optional[str] = None
    is_inventory: Optional[bool] = True
    # Asset purchase support (optional, ignored for normal inventory)
    is_asset: Optional[bool] = False
    asset_name: Optional[str] = None
    asset_category: Optional[str] = None
    asset_depreciation_method: Optional[str] = None
    asset_useful_life_years: Optional[int] = None
    asset_salvage_value: Optional[Decimal] = None
    asset_serial_number: Optional[str] = None
    asset_vehicle_registration: Optional[str] = None
    asset_engine_number: Optional[str] = None
    asset_chassis_number: Optional[str] = None
    asset_accounting_code_id: Optional[str] = None
    # Extended optional metadata
    asset_location: Optional[str] = None
    asset_custodian: Optional[str] = None
    asset_purchase_ref: Optional[str] = None
    asset_tag: Optional[str] = None
    asset_warranty_expiry: Optional[date] = None
    asset_notes: Optional[str] = None
    asset_accum_depr_account_code_id: Optional[str] = None


class PurchaseItemCreate(PurchaseItemBase):
    """Purchase item creation schema"""
    pass


class PurchaseItemResponse(PurchaseItemBase):
    """Purchase item response schema"""
    id: str
    purchase_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseItemUpdate(BaseModel):
    """Purchase item update schema (all fields optional)"""
    product_id: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[Decimal] = None
    cost: Optional[Decimal] = None
    total_cost: Optional[Decimal] = None
    vat_amount: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None
    notes: Optional[str] = None
    is_inventory: Optional[bool] = None
    is_asset: Optional[bool] = None
    asset_name: Optional[str] = None
    asset_category: Optional[str] = None
    asset_depreciation_method: Optional[str] = None
    asset_useful_life_years: Optional[int] = None
    asset_salvage_value: Optional[Decimal] = None
    asset_serial_number: Optional[str] = None
    asset_vehicle_registration: Optional[str] = None
    asset_engine_number: Optional[str] = None
    asset_chassis_number: Optional[str] = None
    asset_accounting_code_id: Optional[str] = None
    asset_location: Optional[str] = None
    asset_custodian: Optional[str] = None
    asset_purchase_ref: Optional[str] = None
    asset_tag: Optional[str] = None
    asset_warranty_expiry: Optional[date] = None
    asset_notes: Optional[str] = None
    asset_accum_depr_account_code_id: Optional[str] = None


class PurchaseBase(BaseModel):
    """Base purchase schema"""
    supplier_id: str
    purchase_date: datetime
    total_amount: Decimal
    total_vat_amount: Optional[Decimal] = Decimal('0.00')
    total_amount_ex_vat: Optional[Decimal] = None
    status: str = "pending"
    reference: Optional[str] = None
    supplier_invoice_number: Optional[str] = None
    notes: Optional[str] = None
    discount_amount: Optional[Decimal] = Decimal('0.00')
    discount_percentage: Optional[Decimal] = Decimal('0.00')
    shipping_cost: Optional[Decimal] = Decimal('0.00')
    handling_cost: Optional[Decimal] = Decimal('0.00')
    due_date: Optional[datetime] = None
    branch_id: Optional[str] = None
    bank_account_id: Optional[str] = None


class PurchaseCreate(BaseModel):
    """Purchase creation schema"""
    supplier_id: str
    purchase_date: datetime
    due_date: Optional[datetime] = None
    reference: Optional[str] = None
    supplier_invoice_number: Optional[str] = None
    notes: Optional[str] = None
    items: List[PurchaseItemCreate] = []
    landed_costs: Optional[List[LandedCostItemCreate]] = []
    payment_method: Optional[str] = 'credit'
    payment_source_id: Optional[str] = None
    payment_source_type: Optional[str] = None  # 'bank', 'cash', or None for credit
    amount_paid: Optional[Decimal] = Decimal('0.00')
    payment_reference: Optional[str] = None
    expense_account_id: Optional[str] = None
    vat_account_id: Optional[str] = None
    # Legacy field for backward compatibility
    bank_account_id: Optional[str] = None


class PurchaseUpdate(BaseModel):
    """Purchase update schema"""
    supplier_id: Optional[str] = None
    purchase_date: Optional[datetime] = None
    total_amount: Optional[Decimal] = None
    total_vat_amount: Optional[Decimal] = None
    total_amount_ex_vat: Optional[Decimal] = None
    status: Optional[str] = None
    reference: Optional[str] = None
    supplier_invoice_number: Optional[str] = None
    notes: Optional[str] = None
    discount_amount: Optional[Decimal] = None
    discount_percentage: Optional[Decimal] = None
    shipping_cost: Optional[Decimal] = None
    handling_cost: Optional[Decimal] = None
    due_date: Optional[datetime] = None
    amount_paid: Optional[Decimal] = None


class PurchaseResponse(PurchaseBase):
    """Purchase response schema"""
    id: str
    amount_paid: Decimal
    created_at: datetime
    updated_at: datetime
    supplier: Optional[SupplierResponse] = None
    purchase_items: List[PurchaseItemResponse] = []
    branch_name: Optional[str] = None
    created_by_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderItemBase(BaseModel):
    """Base purchase order item schema"""
    product_id: str
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = Decimal('0.00')
    vat_amount: Optional[Decimal] = Decimal('0.00')
    description: Optional[str] = None
    notes: Optional[str] = None


class PurchaseOrderItemCreate(PurchaseOrderItemBase):
    """Purchase order item creation schema"""
    pass


class PurchaseOrderBase(BaseModel):
    """Base purchase order schema"""
    supplier_id: str
    po_number: Optional[str] = None
    date: datetime
    expected_delivery_date: Optional[datetime] = None
    status: str = "pending"
    total_amount: Optional[Decimal] = Decimal('0.00')
    total_vat_amount: Optional[Decimal] = Decimal('0.00')
    notes: Optional[str] = None
    branch_id: Optional[str] = None


class PurchaseOrderCreate(PurchaseOrderBase):
    """Purchase order creation schema"""
    items: List[PurchaseOrderItemCreate] = []


class PurchaseOrderResponse(PurchaseOrderBase):
    """Purchase order response schema"""
    id: str
    created_at: datetime
    updated_at: datetime
    supplier: Optional[SupplierResponse] = None
    purchase_order_items: List[PurchaseOrderItemBase] = []

    model_config = ConfigDict(from_attributes=True)
