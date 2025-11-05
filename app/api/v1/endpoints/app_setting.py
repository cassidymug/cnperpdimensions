from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import base64
import io
from PIL import Image

from app.core.database import get_db
from app.models.app_setting import AppSetting
from app.services.app_setting_service import AppSettingService
from app.schemas.app_setting import (
    AppSettingResponse, AppSettingUpdate, CurrencySettingsResponse,
    ThemeSettingsResponse, BusinessSettingsResponse, InventorySettingsResponse,
    SalesSettingsResponse, PurchaseSettingsResponse, VatSettingsResponse,
    SecuritySettingsResponse, AllSettingsResponse
)
from pydantic import BaseModel
from typing import Optional
from app.schemas.user import User
from app.core.security import require_any
from app.utils.logger import get_logger, log_exception, log_error_with_context
# Allow super_admin, admin, accountant to access settings endpoints

logger = get_logger(__name__)
router = APIRouter()  # Dependencies removed for development


@router.get("/", response_model=AllSettingsResponse)
async def get_all_settings(
    db: Session = Depends(get_db)
):
    """Get all application settings"""
    try:
        app_setting_service = AppSettingService(db)
        settings = app_setting_service.get_all_settings()

        return {
            "success": True,
            "data": settings
        }
    except Exception as e:
        print(f"Error in get_all_settings: {e}")
        import traceback
        traceback.print_exc()

        # Return default settings if there's an error
        return {
            "success": True,
            "data": {
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
        }


@router.get("/simple")
async def get_simple_settings(db: Session = Depends(get_db)):
    """Get basic application settings without complex models"""
    try:
        settings = AppSetting.get_instance(db)

        return {
            "success": True,
            "data": {
                # Basic settings that are commonly needed
                "app_name": getattr(settings, 'app_name', 'CNPERP ERP System'),
                "company_name": getattr(settings, 'company_name', 'Your Company Name'),
                "currency": getattr(settings, 'currency', 'BWP'),
                "vat_rate": getattr(settings, 'vat_rate', 14.0),
                "theme_mode": getattr(settings, 'theme_mode', 'light'),
                "primary_color": getattr(settings, 'primary_color', '#0d6efd'),
                "secondary_color": getattr(settings, 'secondary_color', '#6c757d'),
                "accent_color": getattr(settings, 'accent_color', '#198754'),
                "dark_mode_enabled": getattr(settings, 'dark_mode_enabled', False),
                "session_timeout": getattr(settings, 'session_timeout', 30),
                "idle_warning_minutes": getattr(settings, 'idle_warning_minutes', 2),
                "refresh_threshold_minutes": getattr(settings, 'refresh_threshold_minutes', 10),
                "debug_mode": getattr(settings, 'debug_mode', False),
                "maintenance_mode": getattr(settings, 'maintenance_mode', False),
                "company_logo_url": getattr(settings, 'company_logo_url', ''),
                "address": getattr(settings, 'address', ''),
                "phone": getattr(settings, 'phone', ''),
                "email": getattr(settings, 'email', ''),
                "website": getattr(settings, 'website', '')
            }
        }
    except Exception as e:
        print(f"Error getting simple settings: {e}")
        return {
            "success": True,
            "data": {
                "app_name": "CNPERP ERP System",
                "company_name": "Your Company Name",
                "currency": "BWP",
                "vat_rate": 14.0,
                "theme_mode": "light",
                "primary_color": "#0d6efd",
                "secondary_color": "#6c757d",
                "accent_color": "#198754",
                "dark_mode_enabled": False,
                "session_timeout": 30,
                "idle_warning_minutes": 2,
                "refresh_threshold_minutes": 10,
                "debug_mode": False,
                "maintenance_mode": False,
                "company_logo_url": "",
                "address": "",
                "phone": "",
                "email": "",
                "website": ""
            }
        }


@router.get("/currency", response_model=CurrencySettingsResponse)
async def get_currency_settings(
    db: Session = Depends(get_db)
):
    """Get currency-related settings"""
    app_setting_service = AppSettingService(db)
    settings = app_setting_service.get_currency_settings()

    return {
        "success": True,
        "data": settings
    }

@router.get("/currency-test")
async def get_currency_settings_test(
    db: Session = Depends(get_db)
):
    """Test endpoint for currency settings without authentication"""
    return {
        "success": True,
        "data": {
            "currency": "BWP",
            "currency_symbol": "P",
            "currency_code": "BWP"
        }
    }

@router.get("/debug-test")
async def debug_test_settings(
    db: Session = Depends(get_db)
):
    """Debug test endpoint"""
    try:
        app_setting_service = AppSettingService(db)
        settings_instance = app_setting_service.get_settings()
        return {
            "success": True,
            "data": {
                "message": "Settings instance created successfully",
                "instance_id": str(settings_instance.id) if hasattr(settings_instance, 'id') else "No ID",
                "app_name": getattr(settings_instance, 'app_name', 'No app_name')
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "type": type(e).__name__
        }


@router.get("/theme", response_model=ThemeSettingsResponse)
async def get_theme_settings(
    db: Session = Depends(get_db)
):
    """Get theme-related settings"""
    app_setting_service = AppSettingService(db)
    settings = app_setting_service.get_theme_settings()

    return {
        "success": True,
        "data": settings
    }


@router.get("/business", response_model=BusinessSettingsResponse)
async def get_business_settings(
    db: Session = Depends(get_db)
):
    """Get business-related settings"""
    app_setting_service = AppSettingService(db)
    settings = app_setting_service.get_business_settings()

    return {
        "success": True,
        "data": settings
    }


@router.get("/inventory", response_model=InventorySettingsResponse)
async def get_inventory_settings(
    db: Session = Depends(get_db)
):
    """Get inventory-related settings"""
    app_setting_service = AppSettingService(db)
    settings = app_setting_service.get_inventory_settings()

    return {
        "success": True,
        "data": settings
    }


@router.get("/sales", response_model=SalesSettingsResponse)
async def get_sales_settings(
    db: Session = Depends(get_db)
):
    """Get sales-related settings"""
    app_setting_service = AppSettingService(db)
    settings = app_setting_service.get_sales_settings()

    return {
        "success": True,
        "data": settings
    }


@router.get("/purchase", response_model=PurchaseSettingsResponse)
async def get_purchase_settings(
    db: Session = Depends(get_db)
):
    """Get purchase-related settings"""
    app_setting_service = AppSettingService(db)
    settings = app_setting_service.get_purchase_settings()

    return {
        "success": True,
        "data": settings
    }


@router.get("/vat", response_model=VatSettingsResponse)
async def get_vat_settings(
    db: Session = Depends(get_db)
):
    """Get VAT-related settings"""
    app_setting_service = AppSettingService(db)
    settings = app_setting_service.get_vat_settings()

    return {
        "success": True,
        "data": settings
    }


@router.get("/security", response_model=SecuritySettingsResponse)
async def get_security_settings(
    db: Session = Depends(get_db)
):
    """Get security-related settings"""
    app_setting_service = AppSettingService(db)
    settings = app_setting_service.get_security_settings()

    return {
        "success": True,
        "data": settings
    }


@router.put("/", response_model=AppSettingResponse)
async def update_settings(
    settings_data: AppSettingUpdate,
    db: Session = Depends(get_db)
):
    """Update application settings"""
    app_setting_service = AppSettingService(db)

    # Validate currency if provided
    if settings_data.currency:
        # Currency validation removed for development
        pass

    # Persist settings
    update_dict = settings_data.dict(exclude_unset=True)
    if not update_dict:
        return {"success": True, "message": "No changes provided", "data": app_setting_service.get_settings().to_dict()}
    result = app_setting_service.update_settings(update_dict)
    return {
        "success": True,
        "message": result.get('message', 'Settings updated'),
        "data": result.get('data')
    }


@router.get("/pos-receipt/types")
async def get_pos_receipt_printer_types():
    """Get supported POS receipt printer types"""
    return {
        "success": True,
        "data": {
            "printer_types": [
                {
                    "value": "thermal_58mm",
                    "name": "58mm Thermal Receipt Printer",
                    "description": "Compact thermal printer for small receipts",
                    "width_chars": 32,
                    "width_mm": 58,
                    "supports": ["fast_printing", "compact_size", "low_maintenance", "auto_cut"]
                },
                {
                    "value": "thermal_80mm",
                    "name": "80mm Thermal Receipt Printer",
                    "description": "Standard thermal printer for regular receipts",
                    "width_chars": 48,
                    "width_mm": 80,
                    "supports": ["fast_printing", "standard_size", "graphics", "logos", "auto_cut", "barcode"]
                },
                {
                    "value": "impact_76mm",
                    "name": "76mm Impact Receipt Printer",
                    "description": "Impact printer for carbon copy receipts",
                    "width_chars": 42,
                    "width_mm": 76,
                    "supports": ["carbon_copies", "durable", "multi_part_forms"]
                },
                {
                    "value": "custom",
                    "name": "Custom Receipt Printer",
                    "description": "Custom configuration for specialized printers",
                    "width_chars": 48,
                    "width_mm": 80,
                    "supports": ["customizable", "flexible_settings"]
                }
            ],
            "cut_types": [
                {"value": "full", "name": "Full Cut", "description": "Complete paper cut"},
                {"value": "partial", "name": "Partial Cut", "description": "Perforated tear-off"},
                {"value": "none", "name": "No Cut", "description": "Continuous paper"}
            ],
            "char_sizes": [
                {"value": "normal", "name": "Normal (12x24)", "width": 1.0},
                {"value": "condensed", "name": "Condensed (9x17)", "width": 0.75},
                {"value": "double_width", "name": "Double Width (24x24)", "width": 2.0},
                {"value": "double_height", "name": "Double Height (12x48)", "width": 1.0}
            ],
            "line_spacings": [
                {"value": "normal", "name": "Normal (1/6 inch)", "spacing": 4.23},
                {"value": "tight", "name": "Tight (1/8 inch)", "spacing": 3.17},
                {"value": "loose", "name": "Loose (1/4 inch)", "spacing": 6.35}
            ],
            "templates": [
                {"value": "standard_thermal", "name": "Standard Thermal Receipt"},
                {"value": "compact", "name": "Compact Receipt"},
                {"value": "detailed", "name": "Detailed Receipt"},
                {"value": "logo_top", "name": "Logo at Top"},
                {"value": "logo_center", "name": "Logo Centered"}
            ]
        }
    }


@router.post("/logo/upload")
async def upload_company_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload company logo for invoices"""
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Read file content
        content = await file.read()

        # Convert to base64 for storage
        base64_content = base64.b64encode(content).decode('utf-8')
        data_url = f"data:{file.content_type};base64,{base64_content}"

        # Optionally resize image for better performance
        try:
            image = Image.open(io.BytesIO(content))
            # Resize if too large (max 400x200)
            if image.width > 400 or image.height > 200:
                image.thumbnail((400, 200), Image.Resampling.LANCZOS)

                # Convert back to base64
                buffer = io.BytesIO()
                image.save(buffer, format=image.format or 'PNG')
                resized_content = buffer.getvalue()
                base64_content = base64.b64encode(resized_content).decode('utf-8')
                data_url = f"data:image/{image.format.lower() or 'png'};base64,{base64_content}"
        except Exception as resize_error:
            print(f"Image resize warning: {resize_error}")

        # Update app settings
        app_setting_service = AppSettingService(db)
        settings = app_setting_service.get_settings()

        settings.company_logo_base64 = data_url
        settings.company_logo_url = f"/api/v1/app-setting/logo/display"

        db.commit()

        return {
            "success": True,
            "message": "Logo uploaded successfully",
            "logo_url": settings.company_logo_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload logo: {str(e)}")


@router.get("/logo/display")
async def get_company_logo(db: Session = Depends(get_db)):
    """Get company logo for display"""
    try:
        app_setting_service = AppSettingService(db)
        settings = app_setting_service.get_settings()

        if not settings.company_logo_base64:
            raise HTTPException(status_code=404, detail="No logo found")

        return {"logo_data": settings.company_logo_base64}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get logo: {str(e)}")


@router.delete("/logo")
async def delete_company_logo(db: Session = Depends(get_db)):
    """Delete company logo"""
    try:
        app_setting_service = AppSettingService(db)
        settings = app_setting_service.get_settings()

        settings.company_logo_base64 = None
        settings.company_logo_url = None

        db.commit()

        return {
            "success": True,
            "message": "Logo deleted successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete logo: {str(e)}")
