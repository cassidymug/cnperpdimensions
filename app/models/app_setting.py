
from sqlalchemy import Column, String, Float, Boolean, Integer, Text, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from typing import Any, Dict, List, Optional
import json
import uuid

from app.models.base import BaseModel


class AppSetting(BaseModel):
    """Application settings singleton model"""
    
    @classmethod
    def get_receipt_formats(cls) -> List[Dict[str, str]]:
        """Get available receipt formats"""
        return [
            {'code': '50mm', 'name': '50mm Thermal Paper', 'description': 'Narrow thermal receipt (1.97 inches wide)'},
            {'code': '80mm', 'name': '80mm Thermal Paper', 'description': 'Standard thermal receipt (3.15 inches wide)'},
            {'code': 'a4', 'name': 'A4 Paper', 'description': 'Full page receipt (8.27 x 11.69 inches)'}
        ]
    __tablename__ = "app_settings"

    # ------------------------------------------------------------------
    # Internal helpers for JSON meta payload handling
    # ------------------------------------------------------------------

    def _load_meta_payload(self) -> Dict[str, Any]:
        try:
            return json.loads(self.meta_data) if self.meta_data else {}
        except json.JSONDecodeError:
            return {}

    def _store_meta_payload(self, payload: Dict[str, Any]) -> None:
        try:
            self.meta_data = json.dumps(payload)
        except (TypeError, ValueError):
            # Fallback to empty payload when serialization fails
            self.meta_data = json.dumps({})

    @staticmethod
    def _normalise_layout_items(items: Any) -> List[Dict[str, Any]]:
        if not isinstance(items, list):
            return []
        normalised: List[Dict[str, Any]] = []
        for entry in items:
            if isinstance(entry, dict):
                normalised.append(entry)
        return normalised

    @property
    def invoice_designer_config(self) -> Dict[str, Any]:
        payload = self._load_meta_payload()
        stored = payload.get("invoice_designer") or {}

        if isinstance(stored, str):
            try:
                stored = json.loads(stored)
            except json.JSONDecodeError:
                stored = {}

        if not isinstance(stored, dict):
            stored = {}

        layout = self._normalise_layout_items(stored.get("layout", []))
        form_data = stored.get("form_data") or {}
        metadata = stored.get("metadata") or {}

        if not isinstance(form_data, dict):
            form_data = {}
        if not isinstance(metadata, dict):
            metadata = {}

        return {
            "layout": layout,
            "form_data": form_data,
            "metadata": metadata,
            "updated_at": stored.get("updated_at"),
            "version": stored.get("version", 1)
        }

    @invoice_designer_config.setter
    def invoice_designer_config(self, value: Dict[str, Any]) -> None:
        if not isinstance(value, dict):
            value = {}

        payload = self._load_meta_payload()

        layout = self._normalise_layout_items(value.get("layout", []))
        form_data = value.get("form_data") or {}
        metadata = value.get("metadata") or {}
        updated_at = value.get("updated_at")
        version = value.get("version", 1)

        if not isinstance(form_data, dict):
            form_data = {}
        if not isinstance(metadata, dict):
            metadata = {}

        payload["invoice_designer"] = {
            "layout": layout,
            "form_data": form_data,
            "metadata": metadata,
            "updated_at": updated_at,
            "version": version,
        }

        self._store_meta_payload(payload)
    
    # Primary Key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Singleton guard
    singleton_guard = Column(Boolean, default=True, unique=True)
    
    # Company Information
    app_name = Column(String(255), default="CNPERP ERP System")
    company_name = Column(String(255), default="Your Company Name")
    address = Column(Text, default="123 Business St, City, Country")
    phone = Column(String(50), default="+123 456 7890")
    email = Column(String(255), default="info@example.com")
    website = Column(String(255), default="www.your-erp-app.com")
    
    # Logo and Branding
    company_logo_url = Column(String(500))  # Path to uploaded logo
    company_logo_base64 = Column(Text)  # Base64 encoded logo for invoices
    logo_width = Column(Integer, default=150)  # Logo width in pixels
    logo_height = Column(Integer, default=75)  # Logo height in pixels
    logo_position = Column(String(20), default='left')  # left, right, center
    logo_margin_top = Column(Integer, default=10)
    logo_margin_bottom = Column(Integer, default=10)
    
    # Invoice Formatting Settings
    invoice_show_logo = Column(Boolean, default=True)
    invoice_show_company_address = Column(Boolean, default=True)
    invoice_show_company_phone = Column(Boolean, default=True)
    invoice_show_company_email = Column(Boolean, default=True)
    invoice_show_company_website = Column(Boolean, default=True)
    invoice_show_vat_number = Column(Boolean, default=True)
    invoice_show_customer_address = Column(Boolean, default=True)
    invoice_show_customer_phone = Column(Boolean, default=True)
    invoice_show_customer_email = Column(Boolean, default=True)
    invoice_show_customer_vat_number = Column(Boolean, default=True)
    invoice_show_payment_terms = Column(Boolean, default=True)
    invoice_show_due_date = Column(Boolean, default=True)
    invoice_show_discount = Column(Boolean, default=True)
    invoice_show_vat_breakdown = Column(Boolean, default=True)
    invoice_footer_text = Column(Text, default="Thank you for your business!")
    invoice_terms_conditions = Column(Text, default="Payment due within 30 days.")
    invoice_paper_size = Column(String(10), default="A4")  # A4, Letter, Legal
    invoice_template_style = Column(String(20), default="modern")  # modern, classic, minimal
    
    # Header customization
    invoice_header_height = Column(Integer, default=120)
    invoice_header_background_color = Column(String(20), default='#ffffff')
    invoice_header_text_color = Column(String(20), default='#000000')
    invoice_header_border_style = Column(String(20), default='solid')
    invoice_header_border_width = Column(Integer, default=2)
    invoice_header_border_color = Column(String(20), default='#333333')
    
    # Company info customization
    company_info_font_size = Column(Integer, default=12)
    company_info_font_weight = Column(String(20), default='normal')
    company_info_color = Column(String(20), default='#000000')
    company_info_alignment = Column(String(20), default='left')
    
    # Invoice title customization
    invoice_title_text = Column(String(100), default='INVOICE')
    invoice_title_font_size = Column(Integer, default=36)
    invoice_title_font_weight = Column(String(20), default='bold')
    invoice_title_color = Column(String(20), default='#333333')
    invoice_title_alignment = Column(String(20), default='right')
    
    # Customer section customization
    customer_section_background = Column(String(20), default='#f8f9fa')
    customer_section_border = Column(Boolean, default=True)
    customer_section_border_color = Column(String(20), default='#dee2e6')
    customer_section_padding = Column(Integer, default=20)
    
    # Items table customization
    items_table_header_bg = Column(String(20), default='#343a40')
    items_table_header_text = Column(String(20), default='#ffffff')
    items_table_border_color = Column(String(20), default='#dee2e6')
    items_table_stripe_color = Column(String(20), default='#f8f9fa')
    items_table_font_size = Column(Integer, default=12)
    
    # Totals section customization
    totals_section_background = Column(String(20), default='#f8f9fa')
    totals_section_border = Column(Boolean, default=True)
    totals_font_size = Column(Integer, default=14)
    totals_font_weight = Column(String(20), default='normal')
    
    # Footer customization
    invoice_footer_height = Column(Integer, default=100)
    invoice_footer_background_color = Column(String(20), default='#ffffff')
    invoice_footer_text_color = Column(String(20), default='#000000')
    invoice_footer_border_style = Column(String(20), default='solid')
    invoice_footer_border_width = Column(Integer, default=1)
    invoice_footer_border_color = Column(String(20), default='#333333')
    invoice_footer_font_size = Column(Integer, default=11)
    invoice_footer_alignment = Column(String(20), default='left')
    
    # Paper and layout customization
    invoice_margin_top = Column(Integer, default=20)
    invoice_margin_bottom = Column(Integer, default=20)
    invoice_margin_left = Column(Integer, default=20)
    invoice_margin_right = Column(Integer, default=20)
    
    # Color scheme
    invoice_primary_color = Column(String(20), default='#007bff')
    invoice_secondary_color = Column(String(20), default='#6c757d')
    invoice_accent_color = Column(String(20), default='#28a745')
    invoice_background_color = Column(String(20), default='#ffffff')
    
    # Typography
    invoice_font_family = Column(String(100), default='Arial, sans-serif')
    invoice_base_font_size = Column(Integer, default=12)
    invoice_line_height = Column(Float, default=1.4)
    
    # Financial Settings
    currency = Column(String(10), default="BWP")
    vat_rate = Column(Float, default=14.0)
    default_vat_rate = Column(Float, default=14.0)
    
    # Regional Settings
    country = Column(String(10), default="BW")
    locale = Column(String(10), default="en")
    timezone = Column(String(50), default="Africa/Gaborone")
    
    # Measurement System
    measurement_system = Column(String(20), default="metric")  # metric or imperial
    default_unit_of_measure = Column(String(20), default="piece")
    
    # User Management
    user_limit = Column(Integer, default=10)
    roles_config = Column(Text, default="{}")
    
    # Theme Settings
    theme_mode = Column(String(20), default="light")  # light, dark, auto
    primary_color = Column(String(20), default="#0d6efd")
    secondary_color = Column(String(20), default="#6c757d")
    accent_color = Column(String(20), default="#198754")
    dark_mode_enabled = Column(Boolean, default=False)
    
    # System Settings
    debug_mode = Column(Boolean, default=False)
    maintenance_mode = Column(Boolean, default=False)
    session_timeout = Column(Integer, default=30)  # minutes
    idle_warning_minutes = Column(Integer, default=2)  # minutes before timeout to warn
    refresh_threshold_minutes = Column(Integer, default=10)  # minutes before expiry to refresh token
    
    # Email Settings
    smtp_host = Column(String(255))
    smtp_port = Column(Integer, default=587)
    smtp_user = Column(String(255))
    smtp_username = Column(String(255))
    smtp_password = Column(String(255))
    smtp_encryption = Column(String(20), default="tls")
    
    # File Upload Settings
    max_file_size = Column(Integer, default=10485760)  # 10MB
    allowed_file_types = Column(Text, default="jpg,jpeg,png,pdf,doc,docx,xls,xlsx")
    upload_directory = Column(String(255), default="uploads")
    
    # Notification Settings
    email_notifications = Column(Boolean, default=True)
    sms_notifications = Column(Boolean, default=False)
    push_notifications = Column(Boolean, default=True)
    
    # Backup Settings
    auto_backup = Column(Boolean, default=True)
    backup_frequency = Column(String(20), default="daily")  # daily, weekly, monthly
    backup_retention = Column(Integer, default=30)  # days
    
    # Security Settings
    password_min_length = Column(Integer, default=8)
    require_special_chars = Column(Boolean, default=True)
    require_numbers = Column(Boolean, default=True)
    require_uppercase = Column(Boolean, default=True)
    session_timeout_minutes = Column(Integer, default=30)
    max_login_attempts = Column(Integer, default=5)
    
    # Business Settings
    fiscal_year_start = Column(String(10), default="01-01")  # MM-DD format
    default_payment_terms = Column(Integer, default=30)  # days
    late_payment_penalty = Column(Float, default=0.0)
    early_payment_discount = Column(Float, default=0.0)
    
    # Inventory Settings
    low_stock_threshold = Column(Integer, default=10)
    auto_reorder = Column(Boolean, default=False)
    track_serial_numbers = Column(Boolean, default=True)
    track_batch_numbers = Column(Boolean, default=True)
    allow_negative_stock = Column(Boolean, default=False)
    
    # Sales Settings
    allow_credit_sales = Column(Boolean, default=True)
    require_customer_for_sales = Column(Boolean, default=False)
    auto_generate_invoices = Column(Boolean, default=True)
    invoice_prefix = Column(String(10), default="INV")
    invoice_start_number = Column(Integer, default=1000)
    default_receipt_format = Column(String(10), default="80mm")  # 50mm, 80mm, a4
    
    # Purchase Settings
    allow_credit_purchases = Column(Boolean, default=True)
    require_supplier_for_purchases = Column(Boolean, default=False)
    auto_generate_purchase_orders = Column(Boolean, default=True)
    po_prefix = Column(String(10), default="PO")
    po_start_number = Column(Integer, default=1000)
    
    # VAT Settings
    vat_registration_number = Column(String(50))
    vat_filing_frequency = Column(String(20), default="monthly")  # monthly, quarterly, yearly
    vat_due_date_offset = Column(Integer, default=21)  # days after period end
    
    # Banking Settings
    default_bank_account = Column(String(50))
    bank_reconciliation_frequency = Column(String(20), default="monthly")
    auto_bank_reconciliation = Column(Boolean, default=False)
    
    # Branch Default Settings
    default_payment_method = Column(String(50), default="cash")
    default_currency = Column(String(10), default="BWP")
    allow_branch_override = Column(Boolean, default=True)
    
    # Reporting Settings
    default_report_period = Column(String(20), default="monthly")
    auto_generate_reports = Column(Boolean, default=False)
    report_retention_days = Column(Integer, default=365)
    
    # Integration Settings
    api_enabled = Column(Boolean, default=True)
    webhook_url = Column(String(255))
    third_party_integrations = Column(Text, default="{}")
    
    # Audit Settings
    audit_log_enabled = Column(Boolean, default=True)
    audit_log_retention_days = Column(Integer, default=365)
    track_user_activity = Column(Boolean, default=True)
    
    # Custom Fields
    custom_fields = Column(Text, default="{}")
    meta_data = Column(Text, default="{}")

    # ------------------------------------------------------------------
    # Quotation Settings stored inside meta_data JSON payload
    # ------------------------------------------------------------------

    @property
    def quotation_settings_defaults(self) -> Dict[str, Any]:
        """Default quotation configuration"""
        return {
            "title": "QUOTATION",
            "show_logo": True,
            "logo_url": None,
            "logo_width_mm": 60,
            "logo_height_mm": 25,
            "footer_text": "",
            "footer_images": [],
            "show_banking_details": True,
            "bank_name": "",
            "bank_account_name": "",
            "bank_account_number": "",
            "bank_branch": "",
            "bank_swift_code": "",
        }

    @property
    def quotation_settings(self) -> Dict[str, Any]:
        """Retrieve quotation configuration from meta_data"""
        defaults = self.quotation_settings_defaults

        try:
            meta_payload = json.loads(self.meta_data) if self.meta_data else {}
        except json.JSONDecodeError:
            meta_payload = {}

        raw_settings = meta_payload.get("quotation_settings", {})
        config = defaults.copy()

        if isinstance(raw_settings, dict):
            config.update({k: raw_settings.get(k, config[k]) for k in config.keys()})
        elif isinstance(raw_settings, str):
            try:
                decoded = json.loads(raw_settings)
                if isinstance(decoded, dict):
                    config.update({k: decoded.get(k, config[k]) for k in config.keys()})
            except json.JSONDecodeError:
                pass

        # Normalise types
        config["show_logo"] = bool(config.get("show_logo", defaults["show_logo"]))
        config["title"] = (config.get("title") or defaults["title"]).strip() or defaults["title"]
        config["logo_url"] = config.get("logo_url") or None
        try:
            config["logo_width_mm"] = int(config.get("logo_width_mm", defaults["logo_width_mm"]))
        except (TypeError, ValueError):
            config["logo_width_mm"] = defaults["logo_width_mm"]
        try:
            config["logo_height_mm"] = int(config.get("logo_height_mm", defaults["logo_height_mm"]))
        except (TypeError, ValueError):
            config["logo_height_mm"] = defaults["logo_height_mm"]

        footer_images = config.get("footer_images", [])
        if isinstance(footer_images, str):
            try:
                decoded_images = json.loads(footer_images)
                footer_images = decoded_images if isinstance(decoded_images, list) else [footer_images]
            except json.JSONDecodeError:
                footer_images = [footer_images] if footer_images else []
        elif not isinstance(footer_images, list):
            footer_images = []
        config["footer_images"] = [str(path) for path in footer_images if path]

        config["footer_text"] = config.get("footer_text") or ""

        return config

    @quotation_settings.setter
    def quotation_settings(self, value: Dict[str, Any]) -> None:
        """Persist quotation configuration inside meta_data payload"""
        try:
            meta_payload = json.loads(self.meta_data) if self.meta_data else {}
        except json.JSONDecodeError:
            meta_payload = {}

        config = self.quotation_settings_defaults.copy()
        if isinstance(value, dict):
            config.update({k: value.get(k, config[k]) for k in config.keys()})

        # Ensure list serialisation for footer images
        footer_images = config.get("footer_images", [])
        if isinstance(footer_images, str):
            footer_images = [footer_images] if footer_images else []
        elif not isinstance(footer_images, list):
            footer_images = []
        config["footer_images"] = footer_images

        meta_payload["quotation_settings"] = config
        self.meta_data = json.dumps(meta_payload)

    def set_quotation_setting(self, key: str, value: Any) -> None:
        """Update a single quotation setting value and persist it"""
        config = self.quotation_settings
        if key in config:
            config[key] = value
        else:
            # Unknown keys are stored to allow forward compatibility
            config[key] = value
        self.quotation_settings = config
    
    @classmethod
    def get_instance(cls, db_session):
        """Get the singleton app setting instance"""
        try:
            instance = db_session.query(cls).first()
            if not instance:
                # Create a new instance with defaults
                instance = cls()
                db_session.add(instance)
                db_session.commit()
                db_session.refresh(instance)
            return instance
        except Exception as e:
            # Handle column mismatch errors - create new instance with minimal columns
            print(f"Warning: Error querying app_settings table: {e}")
            
            # Try to create a minimal working instance
            try:
                # Check if table exists
                from sqlalchemy import text
                result = db_session.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'app_settings'"))
                table_exists = result.fetchone()[0] > 0
                
                if not table_exists:
                    # Table doesn't exist, create one
                    from app.database import engine
                    cls.metadata.create_all(bind=engine)
                
                # Try basic insert
                instance = cls()
                db_session.add(instance)
                db_session.commit()
                db_session.refresh(instance)
                return instance
                
            except Exception as inner_e:
                print(f"Error creating app_settings instance: {inner_e}")
                # Return a basic instance with defaults for API responses
                instance = cls()
                instance.id = "default-temp-id"
                instance.currency = "BWP"
                instance.company_name = "Your Company Name"
                instance.vat_rate = 14.0
                instance.app_name = "CNPERP ERP System"
                instance.address = "123 Business Street, City, Country"
                instance.phone = "+123 456 7890"
                instance.email = "info@company.com"
                instance.website = "www.company.com"
                instance.theme_mode = "light"
                instance.primary_color = "#0d6efd"
                instance.secondary_color = "#6c757d"
                instance.accent_color = "#198754"
                instance.dark_mode_enabled = False
                instance.session_timeout = 30
                instance.idle_warning_minutes = 2
                instance.refresh_threshold_minutes = 10
                instance.debug_mode = False
                instance.maintenance_mode = False
                return instance
    
    @property
    def roles(self) -> Dict:
        """Get roles configuration as dictionary"""
        try:
            return json.loads(self.roles_config) if self.roles_config else self.default_roles_config
        except json.JSONDecodeError:
            return self.default_roles_config
    
    @roles.setter
    def roles(self, value: Dict):
        """Set roles configuration"""
        self.roles_config = json.dumps(value)
    
    @property
    def default_roles_config(self) -> Dict:
        """Default roles configuration"""
        return {
            'edit_product': ['admin', 'super_admin'],
            'manage_product': ['admin', 'super_admin'],
            'delete_product': ['admin', 'super_admin'],
            'view_reports': ['admin', 'super_admin', 'staff'],
            'manage_users': ['admin', 'super_admin'],
            'manage_settings': ['admin', 'super_admin', 'accountant'],
            'manage_accounting': ['admin', 'super_admin'],
            'manage_inventory': ['admin', 'super_admin', 'manager'],
            'manage_sales': ['admin', 'super_admin', 'manager', 'staff'],
            'manage_purchases': ['admin', 'super_admin', 'manager'],
            'manage_banking': ['admin', 'super_admin'],
            'manage_vat': ['admin', 'super_admin'],
            'view_audit_logs': ['admin', 'super_admin'],
            'all': ['admin', 'super_admin']
        }
    
    @classmethod
    def user_has_permission(cls, user, permission: str, db_session=None) -> bool:
        """Check if user has a given permission.
        Accepts optional db_session to avoid relying on a dynamic attribute on user.
        """
        if not user:
            return False
        role_val = (getattr(user, 'role', None) or '').lower()
        if role_val in ('super_admin', 'admin'):
            return True
        if db_session is None:
            # Attempt to fetch a session-less instance; caller should normally pass db
            return False
        roles_cfg = cls.get_instance(db_session).roles
        allowed_roles = roles_cfg.get(permission, roles_cfg.get('all', []))
        return role_val in [r.lower() for r in allowed_roles]
    
    @property
    def theme_css_variables(self) -> Dict[str, str]:
        """Get theme CSS variables"""
        return {
            '--primary-color': self.primary_color or '#0d6efd',
            '--secondary-color': self.secondary_color or '#6c757d',
            '--accent-color': self.accent_color or '#198754',
            '--theme-mode': self.theme_mode or 'light',
            '--dark-mode-enabled': 'true' if self.dark_mode_enabled else 'false'
        }
    
    @property
    def is_dark_mode(self) -> bool:
        """Check if dark mode is enabled"""
        return self.dark_mode_enabled or self.theme_mode == 'dark'
    
    @property
    def is_light_mode(self) -> bool:
        """Check if light mode is enabled"""
        return not self.is_dark_mode
    
    @property
    def roles(self) -> str:
        """Get roles configuration"""
        return self.roles_config
    
    @classmethod
    def get_theme_modes(cls) -> List[str]:
        """Get available theme modes"""
        return ['light', 'dark', 'auto']
    
    @classmethod
    def get_color_schemes(cls) -> Dict[str, Dict[str, str]]:
        """Get available color schemes"""
        return {
            'default': {
                'primary_color': '#0d6efd',
                'secondary_color': '#6c757d',
                'accent_color': '#198754'
            },
            'ocean': {
                'primary_color': '#0dcaf0',
                'secondary_color': '#6c757d',
                'accent_color': '#20c997'
            },
            'forest': {
                'primary_color': '#198754',
                'secondary_color': '#6c757d',
                'accent_color': '#ffc107'
            },
            'sunset': {
                'primary_color': '#fd7e14',
                'secondary_color': '#6c757d',
                'accent_color': '#dc3545'
            },
            'purple': {
                'primary_color': '#6f42c1',
                'secondary_color': '#6c757d',
                'accent_color': '#e83e8c'
            }
        }
    
    @classmethod
    def get_currencies(cls) -> List[Dict[str, str]]:
        """Get available currencies"""
        return [
            {'code': 'BWP', 'name': 'Botswana Pula', 'symbol': 'P'},
            {'code': 'USD', 'name': 'US Dollar', 'symbol': '$'},
            {'code': 'EUR', 'name': 'Euro', 'symbol': '€'},
            {'code': 'GBP', 'name': 'British Pound', 'symbol': '£'},
            {'code': 'ZAR', 'name': 'South African Rand', 'symbol': 'R'},
            {'code': 'NAD', 'name': 'Namibian Dollar', 'symbol': 'N$'},
            {'code': 'ZMW', 'name': 'Zambian Kwacha', 'symbol': 'K'},
            {'code': 'ZWL', 'name': 'Zimbabwean Dollar', 'symbol': 'Z$'},
            {'code': 'MWK', 'name': 'Malawian Kwacha', 'symbol': 'MK'},
            {'code': 'TZS', 'name': 'Tanzanian Shilling', 'symbol': 'TSh'},
            {'code': 'KES', 'name': 'Kenyan Shilling', 'symbol': 'KSh'}
        ]
    
    @classmethod
    def get_currency_symbol(cls, currency_code: str) -> str:
        """Get currency symbol for a given currency code"""
        currencies = cls.get_currencies()
        for currency in currencies:
            if currency['code'] == currency_code:
                return currency['symbol']
        return 'P'  # Default to Botswana Pula symbol
    
    @classmethod
    def get_countries(cls) -> List[Dict[str, str]]:
        """Get available countries"""
        return [
            {'code': 'BW', 'name': 'Botswana'},
            {'code': 'ZA', 'name': 'South Africa'},
            {'code': 'NA', 'name': 'Namibia'},
            {'code': 'ZM', 'name': 'Zambia'},
            {'code': 'ZW', 'name': 'Zimbabwe'},
            {'code': 'MW', 'name': 'Malawi'},
            {'code': 'TZ', 'name': 'Tanzania'},
            {'code': 'KE', 'name': 'Kenya'},
            {'code': 'UG', 'name': 'Uganda'},
            {'code': 'US', 'name': 'United States'},
            {'code': 'GB', 'name': 'United Kingdom'},
            {'code': 'DE', 'name': 'Germany'},
            {'code': 'FR', 'name': 'France'},
            {'code': 'CA', 'name': 'Canada'},
            {'code': 'AU', 'name': 'Australia'}
        ]
    
    @classmethod
    def get_locales(cls) -> List[Dict[str, str]]:
        """Get available locales"""
        return [
            {'code': 'en', 'name': 'English'},
            {'code': 'af', 'name': 'Afrikaans'},
            {'code': 'zu', 'name': 'Zulu'},
            {'code': 'xh', 'name': 'Xhosa'},
            {'code': 'st', 'name': 'Sotho'},
            {'code': 'tn', 'name': 'Tswana'},
            {'code': 'fr', 'name': 'French'},
            {'code': 'de', 'name': 'German'},
            {'code': 'es', 'name': 'Spanish'},
            {'code': 'pt', 'name': 'Portuguese'}
        ]
    
    @classmethod
    def get_measurement_systems(cls) -> List[Dict[str, str]]:
        """Get available measurement systems"""
        return [
            {'code': 'metric', 'name': 'Metric System'},
            {'code': 'imperial', 'name': 'Imperial System'}
        ]
    
    @classmethod
    def get_receipt_formats(cls) -> List[Dict[str, str]]:
        """Get available receipt formats"""
        return [
            {'code': '50mm', 'name': '50mm Thermal Paper', 'description': 'Narrow thermal receipt (1.97 inches wide)'},
            {'code': '80mm', 'name': '80mm Thermal Paper', 'description': 'Standard thermal receipt (3.15 inches wide)'},
            {'code': 'a4', 'name': 'A4 Paper', 'description': 'Full page receipt (8.27 x 11.69 inches)'}
        ]
    
    @classmethod
    def get_units_of_measure(cls) -> List[Dict[str, str]]:
        """Get available units of measure"""
        return [
            # Basic units
            {'code': 'piece', 'name': 'Piece', 'abbreviation': 'pc'},
            {'code': 'unit', 'name': 'Unit', 'abbreviation': 'un'},
            {'code': 'box', 'name': 'Box', 'abbreviation': 'bx'},
            {'code': 'pack', 'name': 'Pack', 'abbreviation': 'pk'},
            {'code': 'dozen', 'name': 'Dozen', 'abbreviation': 'dz'},
            
            # Weight units
            {'code': 'kilogram', 'name': 'Kilogram', 'abbreviation': 'kg'},
            {'code': 'gram', 'name': 'Gram', 'abbreviation': 'g'},
            {'code': 'tonne', 'name': 'Tonne', 'abbreviation': 't'},
            {'code': 'pound', 'name': 'Pound', 'abbreviation': 'lb'},
            {'code': 'ounce', 'name': 'Ounce', 'abbreviation': 'oz'},
            
            # Volume units
            {'code': 'liter', 'name': 'Liter', 'abbreviation': 'L'},
            {'code': 'milliliter', 'name': 'Milliliter', 'abbreviation': 'ml'},
            {'code': 'gallon', 'name': 'Gallon', 'abbreviation': 'gal'},
            {'code': 'quart', 'name': 'Quart', 'abbreviation': 'qt'},
            {'code': 'pint', 'name': 'Pint', 'abbreviation': 'pt'},
            
            # Length units
            {'code': 'meter', 'name': 'Meter', 'abbreviation': 'm'},
            {'code': 'centimeter', 'name': 'Centimeter', 'abbreviation': 'cm'},
            {'code': 'millimeter', 'name': 'Millimeter', 'abbreviation': 'mm'},
            {'code': 'foot', 'name': 'Foot', 'abbreviation': 'ft'},
            {'code': 'inch', 'name': 'Inch', 'abbreviation': 'in'},
            
            # Area units
            {'code': 'square_meter', 'name': 'Square Meter', 'abbreviation': 'm²'},
            {'code': 'square_foot', 'name': 'Square Foot', 'abbreviation': 'ft²'},
            
            # Volume units
            {'code': 'cubic_meter', 'name': 'Cubic Meter', 'abbreviation': 'm³'},
            {'code': 'cubic_foot', 'name': 'Cubic Foot', 'abbreviation': 'ft³'},
            
            # Time units
            {'code': 'hour', 'name': 'Hour', 'abbreviation': 'hr'},
            {'code': 'minute', 'name': 'Minute', 'abbreviation': 'min'},
            {'code': 'second', 'name': 'Second', 'abbreviation': 's'},
            
            # Service units
            {'code': 'service', 'name': 'Service', 'abbreviation': 'svc'},
            
            # Packaging units
            {'code': 'bundle', 'name': 'Bundle', 'abbreviation': 'bdl'},
            {'code': 'roll', 'name': 'Roll', 'abbreviation': 'rl'},
            {'code': 'sheet', 'name': 'Sheet', 'abbreviation': 'sht'},
            {'code': 'carton', 'name': 'Carton', 'abbreviation': 'ctn'},
            {'code': 'bottle', 'name': 'Bottle', 'abbreviation': 'btl'},
            
            # Medical units
            {'code': 'tablet', 'name': 'Tablet', 'abbreviation': 'tab'},
            {'code': 'capsule', 'name': 'Capsule', 'abbreviation': 'cap'},
            
            # Other units
            {'code': 'pair', 'name': 'Pair', 'abbreviation': 'pr'},
            {'code': 'set', 'name': 'Set', 'abbreviation': 'set'},
            {'code': 'lot', 'name': 'Lot', 'abbreviation': 'lot'}
        ]
    
    def get_custom_field(self, field_name: str) -> Optional[str]:
        """Get custom field value"""
        try:
            custom_fields = json.loads(self.custom_fields) if self.custom_fields else {}
            return custom_fields.get(field_name)
        except json.JSONDecodeError:
            return None
    
    def set_custom_field(self, field_name: str, value: str) -> None:
        """Set custom field value"""
        try:
            custom_fields = json.loads(self.custom_fields) if self.custom_fields else {}
            custom_fields[field_name] = value
            self.custom_fields = json.dumps(custom_fields)
        except json.JSONDecodeError:
            self.custom_fields = json.dumps({field_name: value})
    
    def get_metadata(self, key: str) -> Optional[str]:
        """Get metadata value"""
        try:
            metadata = json.loads(self.metadata) if self.metadata else {}
            return metadata.get(key)
        except json.JSONDecodeError:
            return None
    
    def set_metadata(self, key: str, value: str) -> None:
        """Set metadata value"""
        try:
            metadata = json.loads(self.metadata) if self.metadata else {}
            metadata[key] = value
            self.metadata = json.dumps(metadata)
        except json.JSONDecodeError:
            self.metadata = json.dumps({key: value})
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'id': str(self.id),
            'app_name': self.app_name,
            'company_name': self.company_name,
            'address': self.address,
            'phone': self.phone,
            'email': self.email,
            'website': self.website,
            'company_logo_url': self.company_logo_url,
            'company_logo_base64': self.company_logo_base64,
            'invoice_show_logo': self.invoice_show_logo,
            'invoice_show_company_address': self.invoice_show_company_address,
            'invoice_show_company_phone': self.invoice_show_company_phone,
            'invoice_show_company_email': self.invoice_show_company_email,
            'invoice_show_company_website': self.invoice_show_company_website,
            'invoice_show_vat_number': self.invoice_show_vat_number,
            'invoice_show_customer_address': self.invoice_show_customer_address,
            'invoice_show_customer_phone': self.invoice_show_customer_phone,
            'invoice_show_customer_email': self.invoice_show_customer_email,
            'invoice_show_customer_vat_number': self.invoice_show_customer_vat_number,
            'invoice_show_payment_terms': self.invoice_show_payment_terms,
            'invoice_show_due_date': self.invoice_show_due_date,
            'invoice_show_discount': self.invoice_show_discount,
            'invoice_show_vat_breakdown': self.invoice_show_vat_breakdown,
            'invoice_footer_text': self.invoice_footer_text,
            'invoice_terms_conditions': self.invoice_terms_conditions,
            # 'invoice_paper_size': self.invoice_paper_size,  # COMMENTED OUT DUE TO MISSING COLUMN
            # 'invoice_template_style': self.invoice_template_style,  # COMMENTED OUT DUE TO MISSING COLUMN
            'currency': self.currency,
            'vat_rate': self.vat_rate,
            'default_vat_rate': self.default_vat_rate,
            'country': self.country,
            'locale': self.locale,
            'timezone': self.timezone,
            'measurement_system': self.measurement_system,
            'default_unit_of_measure': self.default_unit_of_measure,
            'user_limit': self.user_limit,
            'roles': self.roles_config,
            'theme_mode': self.theme_mode,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'accent_color': self.accent_color,
            'dark_mode_enabled': self.dark_mode_enabled,
            'debug_mode': self.debug_mode,
            'maintenance_mode': self.maintenance_mode,
            'session_timeout': self.session_timeout,
            'session_timeout_minutes': self.session_timeout_minutes,
            'idle_warning_minutes': self.idle_warning_minutes,
            'refresh_threshold_minutes': self.refresh_threshold_minutes,
            'password_min_length': self.password_min_length,
            'require_special_chars': self.require_special_chars,
            'require_numbers': self.require_numbers,
            'require_uppercase': self.require_uppercase,
            'max_login_attempts': self.max_login_attempts,
            'low_stock_threshold': self.low_stock_threshold,
            'auto_reorder': self.auto_reorder,
            'track_serial_numbers': self.track_serial_numbers,
            'track_batch_numbers': self.track_batch_numbers,
            'allow_negative_stock': self.allow_negative_stock,
            'allow_credit_sales': self.allow_credit_sales,
            'require_customer_for_sales': self.require_customer_for_sales,
            'auto_generate_invoices': self.auto_generate_invoices,
            'invoice_prefix': self.invoice_prefix,
            'invoice_start_number': self.invoice_start_number,
            'default_receipt_format': self.default_receipt_format,
            'allow_credit_purchases': self.allow_credit_purchases,
            'require_supplier_for_purchases': self.require_supplier_for_purchases,
            'auto_generate_purchase_orders': self.auto_generate_purchase_orders,
            'po_prefix': self.po_prefix,
            'po_start_number': self.po_start_number,
            'vat_registration_number': self.vat_registration_number,
            'vat_filing_frequency': self.vat_filing_frequency,
            'vat_due_date_offset': self.vat_due_date_offset,
            'quotation_settings': self.quotation_settings,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        } 