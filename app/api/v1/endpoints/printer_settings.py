"""
Printer Settings API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import BaseModel

from app.core.database import get_db
from app.models.app_setting import AppSetting
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()


class PrinterSettings(BaseModel):
    default_printer: str = ""
    paper_size: str = "A4"
    orientation: str = "portrait"
    margins_top: int = 20
    margins_bottom: int = 20
    margins_left: int = 20
    margins_right: int = 20
    print_quality: str = "normal"
    color_mode: str = "color"


class POSReceiptSettings(BaseModel):
    receipt_format: str = "80mm"
    printer_name: str = ""
    paper_width: int = 80
    font_size: int = 12
    header_text: str = ""
    footer_text: str = ""


@router.get("/invoice-printer/types")
async def get_printer_types():
    """Get available printer types for invoices"""
    return {
        "printer_types": [
            {"id": "thermal", "name": "Thermal Printer", "description": "For receipts and small format printing"},
            {"id": "inkjet", "name": "Inkjet Printer", "description": "Standard color printer"},
            {"id": "laser", "name": "Laser Printer", "description": "High quality document printing"},
            {"id": "dot_matrix", "name": "Dot Matrix Printer", "description": "Impact printer for multi-part forms"}
        ],
        "paper_sizes": [
            {"id": "A4", "name": "A4 (210 × 297 mm)", "width": 210, "height": 297},
            {"id": "Letter", "name": "Letter (8.5 × 11 in)", "width": 216, "height": 279},
            {"id": "Legal", "name": "Legal (8.5 × 14 in)", "width": 216, "height": 356},
            {"id": "80mm", "name": "80mm Thermal", "width": 80, "height": 200},
            {"id": "58mm", "name": "58mm Thermal", "width": 58, "height": 200}
        ],
        "orientations": [
            {"id": "portrait", "name": "Portrait"},
            {"id": "landscape", "name": "Landscape"}
        ],
        "qualities": [
            {"id": "draft", "name": "Draft"},
            {"id": "normal", "name": "Normal"},
            {"id": "high", "name": "High Quality"}
        ]
    }


@router.get("/invoice-printer")
async def get_invoice_printer_settings(db: Session = Depends(get_db)):
    """Get invoice printer settings"""
    try:
        settings = AppSetting.get_instance(db)
        
        return {
            "success": True,
            "data": {
                "default_printer": getattr(settings, 'default_printer', ''),
                "paper_size": getattr(settings, 'invoice_paper_size', 'A4'),
                "orientation": getattr(settings, 'print_orientation', 'portrait'),
                "margins_top": getattr(settings, 'invoice_margin_top', 20),
                "margins_bottom": getattr(settings, 'invoice_margin_bottom', 20),
                "margins_left": getattr(settings, 'invoice_margin_left', 20),
                "margins_right": getattr(settings, 'invoice_margin_right', 20),
                "print_quality": getattr(settings, 'print_quality', 'normal'),
                "color_mode": getattr(settings, 'print_color_mode', 'color'),
                "auto_print": getattr(settings, 'auto_print_invoices', False),
                "copies": getattr(settings, 'invoice_print_copies', 1)
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {
                "default_printer": "",
                "paper_size": "A4",
                "orientation": "portrait",
                "margins_top": 20,
                "margins_bottom": 20,
                "margins_left": 20,
                "margins_right": 20,
                "print_quality": "normal",
                "color_mode": "color",
                "auto_print": False,
                "copies": 1
            }
        }


@router.put("/invoice-printer")
async def update_invoice_printer_settings(
    settings_data: PrinterSettings,
    db: Session = Depends(get_db)
):
    """Update invoice printer settings"""
    try:
        settings = AppSetting.get_instance(db)
        
        # Update settings
        if hasattr(settings, 'default_printer'):
            settings.default_printer = settings_data.default_printer
        if hasattr(settings, 'invoice_paper_size'):
            settings.invoice_paper_size = settings_data.paper_size
        if hasattr(settings, 'print_orientation'):
            settings.print_orientation = settings_data.orientation
        if hasattr(settings, 'invoice_margin_top'):
            settings.invoice_margin_top = settings_data.margins_top
        if hasattr(settings, 'invoice_margin_bottom'):
            settings.invoice_margin_bottom = settings_data.margins_bottom
        if hasattr(settings, 'invoice_margin_left'):
            settings.invoice_margin_left = settings_data.margins_left
        if hasattr(settings, 'invoice_margin_right'):
            settings.invoice_margin_right = settings_data.margins_right
        
        db.commit()
        
        return {
            "success": True,
            "message": "Printer settings updated successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/pos-receipt")
async def get_pos_receipt_settings(db: Session = Depends(get_db)):
    """Get POS receipt settings"""
    try:
        settings = AppSetting.get_instance(db)
        
        return {
            "success": True,
            "data": {
                "receipt_format": getattr(settings, 'default_receipt_format', '80mm'),
                "printer_name": getattr(settings, 'pos_printer_name', ''),
                "paper_width": 80 if getattr(settings, 'default_receipt_format', '80mm') == '80mm' else 58,
                "font_size": getattr(settings, 'receipt_font_size', 12),
                "header_text": getattr(settings, 'receipt_header_text', ''),
                "footer_text": getattr(settings, 'receipt_footer_text', 'Thank you for your business!'),
                "show_logo": getattr(settings, 'receipt_show_logo', True),
                "show_company_info": getattr(settings, 'receipt_show_company_info', True),
                "show_vat_number": getattr(settings, 'receipt_show_vat_number', True),
                "auto_print": getattr(settings, 'auto_print_receipts', False),
                "copies": getattr(settings, 'receipt_print_copies', 1)
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {
                "receipt_format": "80mm",
                "printer_name": "",
                "paper_width": 80,
                "font_size": 12,
                "header_text": "",
                "footer_text": "Thank you for your business!",
                "show_logo": True,
                "show_company_info": True,
                "show_vat_number": True,
                "auto_print": False,
                "copies": 1
            }
        }


@router.put("/pos-receipt")
async def update_pos_receipt_settings(
    settings_data: POSReceiptSettings,
    db: Session = Depends(get_db)
):
    """Update POS receipt settings"""
    try:
        settings = AppSetting.get_instance(db)
        
        # Update settings
        if hasattr(settings, 'default_receipt_format'):
            settings.default_receipt_format = settings_data.receipt_format
        if hasattr(settings, 'pos_printer_name'):
            settings.pos_printer_name = settings_data.printer_name
        if hasattr(settings, 'receipt_font_size'):
            settings.receipt_font_size = settings_data.font_size
        if hasattr(settings, 'receipt_header_text'):
            settings.receipt_header_text = settings_data.header_text
        if hasattr(settings, 'receipt_footer_text'):
            settings.receipt_footer_text = settings_data.footer_text
        
        db.commit()
        
        return {
            "success": True,
            "message": "POS receipt settings updated successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/available-printers")
async def get_available_printers():
    """Get list of available system printers"""
    try:
        import win32print
        printers = []
        
        # Get default printer
        default_printer = win32print.GetDefaultPrinter()
        
        # Get all printers
        printer_list = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        
        for printer in printer_list:
            printers.append({
                "name": printer[2],
                "is_default": printer[2] == default_printer,
                "status": "Ready"  # Could be enhanced to get actual status
            })
        
        return {
            "success": True,
            "printers": printers,
            "default_printer": default_printer
        }
    except ImportError:
        # Fallback for non-Windows systems or when win32print is not available
        return {
            "success": True,
            "printers": [
                {"name": "Microsoft Print to PDF", "is_default": True, "status": "Ready"},
                {"name": "Default Printer", "is_default": False, "status": "Ready"}
            ],
            "default_printer": "Microsoft Print to PDF"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "printers": [],
            "default_printer": ""
        }
