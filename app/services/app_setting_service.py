from sqlalchemy.orm import Session
from app.models.app_setting import AppSetting
from typing import Dict, Any, Optional
import json


class AppSettingService:
    """Service for managing application settings"""
    
    def __init__(self, db: Session):
        self.db = db
        self._settings = None
    
    def get_settings(self) -> AppSetting:
        """Get the application settings singleton"""
        if not self._settings:
            self._settings = AppSetting.get_instance(self.db)
        return self._settings
    
    def update_settings(self, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update application settings"""
        settings = self.get_settings()

        # Extract quotation settings, handled separately below
        quotation_payload = settings_data.pop("quotation_settings", None)

        # Update direct attributes on the settings model
        for key, value in settings_data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        # Persist quotation settings into meta_data if provided
        if isinstance(quotation_payload, dict):
            try:
                settings.quotation_settings = quotation_payload
            except AttributeError:
                # Fallback: manually inject into meta_data
                try:
                    meta_payload = json.loads(settings.meta_data) if settings.meta_data else {}
                except json.JSONDecodeError:
                    meta_payload = {}
                meta_payload["quotation_settings"] = quotation_payload
                settings.meta_data = json.dumps(meta_payload)

        self.db.commit()
        self.db.refresh(settings)

        return {"success": True, "message": "Settings updated successfully", "data": settings.to_dict()}
    
    def get_currency_settings(self) -> Dict[str, Any]:
        """Get currency-related settings"""
        settings = self.get_settings()
        return {
            "currency": settings.currency,
            "currency_symbol": self.get_currency_symbol(settings.currency),
            "vat_rate": settings.vat_rate,
            "default_vat_rate": settings.default_vat_rate,
            "country": settings.country,
            "locale": settings.locale,
            "timezone": settings.timezone
        }
    
    def get_currency_symbol(self, currency_code: str) -> str:
        """Get currency symbol for a given currency code"""
        currency_symbols = {
            'BWP': 'P',
            'USD': '$',
            'EUR': '€',
            'GBP': '£',
            'ZAR': 'R',
            'NAD': 'N$',
            'ZMW': 'K',
            'ZWL': 'Z$',
            'MWK': 'MK',
            'TZS': 'TSh',
            'KES': 'KSh'
        }
        return currency_symbols.get(currency_code, currency_code)
    
    def format_currency(self, amount: float, currency_code: Optional[str] = None) -> str:
        """Format amount with currency symbol"""
        if currency_code is None:
            currency_code = self.get_settings().currency
        
        symbol = self.get_currency_symbol(currency_code)
        return f"{symbol}{amount:,.2f}"
    
    def get_theme_settings(self) -> Dict[str, Any]:
        """Get theme-related settings"""
        settings = self.get_settings()
        return {
            "theme_mode": settings.theme_mode,
            "primary_color": settings.primary_color,
            "secondary_color": settings.secondary_color,
            "accent_color": settings.accent_color,
            "dark_mode_enabled": settings.dark_mode_enabled,
            "theme_css_variables": settings.theme_css_variables
        }
    
    def get_business_settings(self) -> Dict[str, Any]:
        """Get business-related settings"""
        settings = self.get_settings()
        return {
            "company_name": settings.company_name,
            "app_name": settings.app_name,
            "address": settings.address,
            "phone": settings.phone,
            "email": settings.email,
            "website": settings.website,
            "company_logo_url": settings.company_logo_url,
            "company_logo_base64": settings.company_logo_base64,
            "invoice_show_logo": settings.invoice_show_logo,
            "invoice_show_company_address": settings.invoice_show_company_address,
            "invoice_show_company_phone": settings.invoice_show_company_phone,
            "invoice_show_company_email": settings.invoice_show_company_email,
            "invoice_show_company_website": settings.invoice_show_company_website,
            "fiscal_year_start": settings.fiscal_year_start,
            "default_payment_terms": settings.default_payment_terms,
            "late_payment_penalty": settings.late_payment_penalty,
            "early_payment_discount": settings.early_payment_discount
        }

    def get_quotation_settings(self) -> Dict[str, Any]:
        """Get quotation-specific settings stored in meta_data"""
        settings = self.get_settings()
        quotation_cfg = getattr(settings, "quotation_settings", None)
        if not isinstance(quotation_cfg, dict):
            defaults = getattr(settings, "quotation_settings_defaults", None)
            if isinstance(defaults, dict):
                return dict(defaults)
            return {
                "title": "QUOTATION",
                "show_logo": True,
                "logo_url": None,
                "logo_width_mm": 60,
                "logo_height_mm": 25,
                "footer_text": "",
                "footer_images": [],
            }
        return dict(quotation_cfg)
    
    def get_inventory_settings(self) -> Dict[str, Any]:
        """Get inventory-related settings"""
        settings = self.get_settings()
        return {
            "low_stock_threshold": settings.low_stock_threshold,
            "auto_reorder": settings.auto_reorder,
            "track_serial_numbers": settings.track_serial_numbers,
            "track_batch_numbers": settings.track_batch_numbers,
            "allow_negative_stock": settings.allow_negative_stock,
            "measurement_system": settings.measurement_system,
            "default_unit_of_measure": settings.default_unit_of_measure
        }
    
    def get_sales_settings(self) -> Dict[str, Any]:
        """Get sales-related settings"""
        settings = self.get_settings()
        return {
            "allow_credit_sales": settings.allow_credit_sales,
            "require_customer_for_sales": settings.require_customer_for_sales,
            "auto_generate_invoices": settings.auto_generate_invoices,
            "invoice_prefix": settings.invoice_prefix,
            "invoice_start_number": settings.invoice_start_number
        }
    
    def get_purchase_settings(self) -> Dict[str, Any]:
        """Get purchase-related settings"""
        settings = self.get_settings()
        return {
            "allow_credit_purchases": settings.allow_credit_purchases,
            "require_supplier_for_purchases": settings.require_supplier_for_purchases,
            "auto_generate_purchase_orders": settings.auto_generate_purchase_orders,
            "po_prefix": settings.po_prefix,
            "po_start_number": settings.po_start_number
        }
    
    def get_vat_settings(self) -> Dict[str, Any]:
        """Get VAT-related settings"""
        settings = self.get_settings()
        return {
            "vat_rate": settings.vat_rate,
            "default_vat_rate": settings.default_vat_rate,
            "vat_registration_number": settings.vat_registration_number,
            "vat_filing_frequency": settings.vat_filing_frequency,
            "vat_due_date_offset": settings.vat_due_date_offset
        }
    
    def get_security_settings(self) -> Dict[str, Any]:
        """Get security-related settings"""
        settings = self.get_settings()
        return {
            "password_min_length": settings.password_min_length,
            "require_special_chars": settings.require_special_chars,
            "require_numbers": settings.require_numbers,
            "require_uppercase": settings.require_uppercase,
            "session_timeout_minutes": settings.session_timeout_minutes,
            "idle_warning_minutes": getattr(settings, 'idle_warning_minutes', 2),
            "refresh_threshold_minutes": getattr(settings, 'refresh_threshold_minutes', 10),
            "max_login_attempts": settings.max_login_attempts
        }
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all application settings with graceful error handling"""
        try:
            settings = self.get_settings()
            return {
                "general": {
                    "app_name": getattr(settings, 'app_name', 'CNPERP ERP System'),
                    "company_name": getattr(settings, 'company_name', 'Your Company Name'),
                    "debug_mode": getattr(settings, 'debug_mode', False),
                    "maintenance_mode": getattr(settings, 'maintenance_mode', False),
                    "session_timeout": getattr(settings, 'session_timeout', 30)
                },
                "currency": self.get_currency_settings(),
                "theme": self.get_theme_settings(),
                "business": self.get_business_settings(),
                "quotation": self.get_quotation_settings(),
                "inventory": self.get_inventory_settings(),
                "sales": self.get_sales_settings(),
                "purchase": self.get_purchase_settings(),
                "vat": self.get_vat_settings(),
                "security": self.get_security_settings(),
                "available_currencies": self._get_safe_currencies(),
                "available_countries": self._get_safe_countries(),
                "available_locales": self._get_safe_locales(),
                "available_measurement_systems": self._get_safe_measurement_systems(),
                "available_units_of_measure": self._get_safe_units_of_measure(),
                "available_theme_modes": self._get_safe_theme_modes(),
                "available_color_schemes": self._get_safe_color_schemes()
            }
        except Exception as e:
            print(f"Error in get_all_settings: {e}")
            # Return basic default settings
            return {
                "general": {
                    "app_name": "CNPERP ERP System",
                    "company_name": "Your Company Name",
                    "debug_mode": False,
                    "maintenance_mode": False,
                    "session_timeout": 30
                },
                "currency": {
                    "currency": "BWP",
                    "currency_symbol": "P",
                    "vat_rate": 14.0,
                    "default_vat_rate": 14.0,
                    "country": "BW",
                    "locale": "en",
                    "timezone": "Africa/Gaborone"
                },
                "theme": {
                    "theme_mode": "light",
                    "primary_color": "#0d6efd",
                    "secondary_color": "#6c757d",
                    "accent_color": "#198754",
                    "dark_mode_enabled": False
                },
                "business": {
                    "company_name": "Your Company Name",
                    "app_name": "CNPERP ERP System",
                    "address": "123 Business Street, City, Country",
                    "phone": "+123 456 7890",
                    "email": "info@company.com",
                    "website": "www.company.com",
                    "company_logo_url": "",
                    "company_logo_base64": ""
                },
                "security": {
                    "session_timeout_minutes": 30,
                    "idle_warning_minutes": 2,
                    "refresh_threshold_minutes": 10,
                    "password_min_length": 8,
                    "require_special_chars": True,
                    "require_numbers": True,
                    "require_uppercase": True,
                    "max_login_attempts": 5
                }
            }
    
    def _get_safe_currencies(self):
        """Get currencies with error handling"""
        try:
            return AppSetting.get_currencies()
        except:
            return [{"code": "BWP", "name": "Botswana Pula", "symbol": "P"}]
    
    def _get_safe_countries(self):
        """Get countries with error handling"""
        try:
            return AppSetting.get_countries()
        except:
            return [{"code": "BW", "name": "Botswana"}]
    
    def _get_safe_locales(self):
        """Get locales with error handling"""
        try:
            return AppSetting.get_locales()
        except:
            return [{"code": "en", "name": "English"}]
    
    def _get_safe_measurement_systems(self):
        """Get measurement systems with error handling"""
        try:
            return AppSetting.get_measurement_systems()
        except:
            return [{"code": "metric", "name": "Metric"}]
    
    def _get_safe_units_of_measure(self):
        """Get units of measure with error handling"""
        try:
            return AppSetting.get_units_of_measure()
        except:
            return [{"code": "piece", "name": "Piece"}]
    
    def _get_safe_theme_modes(self):
        """Get theme modes with error handling"""
        try:
            return AppSetting.get_theme_modes()
        except:
            return ["light", "dark", "auto"]
    
    def _get_safe_color_schemes(self):
        """Get color schemes with error handling"""
        try:
            return AppSetting.get_color_schemes()
        except:
            return {"default": {"primary": "#0d6efd", "secondary": "#6c757d"}}
    
    def validate_currency(self, currency_code: str) -> bool:
        """Validate if a currency code is supported"""
        supported_currencies = [curr['code'] for curr in AppSetting.get_currencies()]
        return currency_code in supported_currencies
    
    def validate_country(self, country_code: str) -> bool:
        """Validate if a country code is supported"""
        supported_countries = [country['code'] for country in AppSetting.get_countries()]
        return country_code in supported_countries
    
    def reset_to_defaults(self) -> Dict[str, Any]:
        """Reset settings to default values"""
        settings = self.get_settings()
        
        # Reset to default values
        settings.app_name = "CNPERP ERP System"
        settings.company_name = "Your Company Name"
        settings.currency = "BWP"
        settings.vat_rate = 14.0
        settings.default_vat_rate = 14.0
        settings.country = "BW"
        settings.locale = "en"
        settings.timezone = "Africa/Gaborone"
        settings.theme_mode = "light"
        settings.primary_color = "#0d6efd"
        settings.secondary_color = "#6c757d"
        settings.accent_color = "#198754"
        settings.dark_mode_enabled = False
        
        self.db.commit()
        self.db.refresh(settings)
        
        return {"success": True, "message": "Settings reset to defaults", "data": settings.to_dict()} 

    # POS-specific helpers
    def get_branch_default_card_bank_account(self, branch_id: str) -> Optional[str]:
        settings = self.get_settings()
        try:
            meta = json.loads(settings.meta_data) if settings.meta_data else {}
        except json.JSONDecodeError:
            meta = {}
        pos_cfg = meta.get('pos', {})
        defaults = pos_cfg.get('branch_defaults', {})
        br = defaults.get(branch_id, {})
        return br.get('default_card_bank_account_id')

    def set_branch_default_card_bank_account(self, branch_id: str, bank_account_id: str) -> Dict[str, Any]:
        settings = self.get_settings()
        try:
            meta = json.loads(settings.meta_data) if settings.meta_data else {}
        except json.JSONDecodeError:
            meta = {}
        pos_cfg = meta.get('pos', {})
        if 'branch_defaults' not in pos_cfg:
            pos_cfg['branch_defaults'] = {}
        if branch_id not in pos_cfg['branch_defaults']:
            pos_cfg['branch_defaults'][branch_id] = {}
        pos_cfg['branch_defaults'][branch_id]['default_card_bank_account_id'] = bank_account_id
        meta['pos'] = pos_cfg
        settings.meta_data = json.dumps(meta)
        self.db.commit()
        self.db.refresh(settings)
        return {"success": True, "data": {"branch_id": branch_id, "default_card_bank_account_id": bank_account_id}}

    def clear_branch_default_card_bank_account(self, branch_id: str) -> Dict[str, Any]:
        settings = self.get_settings()
        try:
            meta = json.loads(settings.meta_data) if settings.meta_data else {}
        except json.JSONDecodeError:
            meta = {}
        pos_cfg = meta.get('pos', {})
        branch_defaults = pos_cfg.get('branch_defaults', {})
        if branch_id in branch_defaults:
            # Remove the specific key or the whole branch entry if empty after removal
            branch_defaults[branch_id].pop('default_card_bank_account_id', None)
            if not branch_defaults[branch_id]:
                branch_defaults.pop(branch_id, None)
        pos_cfg['branch_defaults'] = branch_defaults
        meta['pos'] = pos_cfg
        settings.meta_data = json.dumps(meta)
        self.db.commit()
        self.db.refresh(settings)
        return {"success": True, "data": {"branch_id": branch_id, "default_card_bank_account_id": None}}

    # Global POS defaults
    def get_global_default_card_bank_account(self) -> Optional[str]:
        settings = self.get_settings()
        try:
            meta = json.loads(settings.meta_data) if settings.meta_data else {}
        except json.JSONDecodeError:
            meta = {}
        pos_cfg = meta.get('pos', {})
        global_defaults = pos_cfg.get('global_defaults', {})
        return global_defaults.get('default_card_bank_account_id')

    def set_global_default_card_bank_account(self, bank_account_id: str) -> Dict[str, Any]:
        settings = self.get_settings()
        try:
            meta = json.loads(settings.meta_data) if settings.meta_data else {}
        except json.JSONDecodeError:
            meta = {}
        pos_cfg = meta.get('pos', {})
        if 'global_defaults' not in pos_cfg:
            pos_cfg['global_defaults'] = {}
        pos_cfg['global_defaults']['default_card_bank_account_id'] = bank_account_id
        meta['pos'] = pos_cfg
        settings.meta_data = json.dumps(meta)
        self.db.commit()
        self.db.refresh(settings)
        return {"success": True, "data": {"default_card_bank_account_id": bank_account_id}}