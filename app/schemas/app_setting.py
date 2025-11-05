from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class AppSettingBase(BaseModel):
    """Base app setting schema"""
    app_name: Optional[str] = None
    company_name: Optional[str] = None
    currency: Optional[str] = "BWP"
    vat_rate: Optional[float] = 14.0
    country: Optional[str] = "BW"
    timezone: Optional[str] = "Africa/Gaborone"
    theme_mode: Optional[str] = "light"
    primary_color: Optional[str] = "#0d6efd"
    secondary_color: Optional[str] = "#6c757d"
    accent_color: Optional[str] = "#198754"


class AppSettingUpdate(BaseModel):
    """App setting update schema"""
    app_name: Optional[str] = None
    company_name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    currency: Optional[str] = None
    vat_rate: Optional[float] = None
    default_vat_rate: Optional[float] = None
    country: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None
    measurement_system: Optional[str] = None
    default_unit_of_measure: Optional[str] = None
    theme_mode: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    dark_mode_enabled: Optional[bool] = None
    debug_mode: Optional[bool] = None
    maintenance_mode: Optional[bool] = None
    session_timeout: Optional[int] = None
    low_stock_threshold: Optional[int] = None
    auto_reorder: Optional[bool] = None
    track_serial_numbers: Optional[bool] = None
    track_batch_numbers: Optional[bool] = None
    allow_negative_stock: Optional[bool] = None
    allow_credit_sales: Optional[bool] = None
    require_customer_for_sales: Optional[bool] = None
    auto_generate_invoices: Optional[bool] = None
    invoice_prefix: Optional[str] = None
    invoice_start_number: Optional[int] = None
    allow_credit_purchases: Optional[bool] = None
    require_supplier_for_purchases: Optional[bool] = None
    auto_generate_purchase_orders: Optional[bool] = None
    po_prefix: Optional[str] = None
    po_start_number: Optional[int] = None
    vat_registration_number: Optional[str] = None
    vat_filing_frequency: Optional[str] = None
    vat_due_date_offset: Optional[int] = None
    password_min_length: Optional[int] = None
    require_special_chars: Optional[bool] = None
    require_numbers: Optional[bool] = None
    require_uppercase: Optional[bool] = None
    session_timeout_minutes: Optional[int] = None
    idle_warning_minutes: Optional[int] = None
    refresh_threshold_minutes: Optional[int] = None
    max_login_attempts: Optional[int] = None
    
    # Branch Default Settings
    default_bank_account: Optional[str] = None
    default_payment_method: Optional[str] = None
    default_currency: Optional[str] = None
    allow_branch_override: Optional[bool] = None

    # Quotation configuration (stored in meta_data)
    quotation_settings: Optional[Dict[str, Any]] = None


class AppSettingResponse(BaseModel):
    """App setting response schema"""
    success: bool
    message: str
    data: Dict[str, Any]


class CurrencySettingsResponse(BaseModel):
    """Currency settings response schema"""
    success: bool
    data: Dict[str, Any]


class ThemeSettingsResponse(BaseModel):
    """Theme settings response schema"""
    success: bool
    data: Dict[str, Any]


class BusinessSettingsResponse(BaseModel):
    """Business settings response schema"""
    success: bool
    data: Dict[str, Any]


class InventorySettingsResponse(BaseModel):
    """Inventory settings response schema"""
    success: bool
    data: Dict[str, Any]


class SalesSettingsResponse(BaseModel):
    """Sales settings response schema"""
    success: bool
    data: Dict[str, Any]


class PurchaseSettingsResponse(BaseModel):
    """Purchase settings response schema"""
    success: bool
    data: Dict[str, Any]


class VatSettingsResponse(BaseModel):
    """VAT settings response schema"""
    success: bool
    data: Dict[str, Any]


class SecuritySettingsResponse(BaseModel):
    """Security settings response schema"""
    success: bool
    data: Dict[str, Any]


class AllSettingsResponse(BaseModel):
    """All settings response schema"""
    success: bool
    data: Dict[str, Any] 