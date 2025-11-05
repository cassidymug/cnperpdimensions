"""
Invoice Designer API endpoints for customization and logo management
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import json
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)
import os
import uuid
from pathlib import Path

from app.core.database import get_db
from app.models.app_setting import AppSetting
from app.services.invoice_service import InvoiceService

router = APIRouter()

# Configure upload directory
UPLOAD_DIR = Path("app/static/uploads/logos")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class InvoiceLayoutPayload(BaseModel):
    layout: List[Dict[str, Any]] = Field(default_factory=list)
    form_data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InvoiceLayoutResponse(InvoiceLayoutPayload):
    updated_at: Optional[str] = None
    version: int = 1

@router.post("/upload-logo")
async def upload_logo(
    logo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload company logo for invoice customization"""
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/svg+xml']
    if logo.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Please upload JPG, PNG, or SVG files only."
        )
    
    # Validate file size (5MB max)
    max_size = 5 * 1024 * 1024  # 5MB
    contents = await logo.read()
    if len(contents) > max_size:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 5MB."
        )
    
    # Generate unique filename
    file_extension = os.path.splitext(logo.filename)[1]
    unique_filename = f"logo_{uuid.uuid4()}{file_extension}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        buffer.write(contents)
    
    # Update app settings with logo path
    settings = AppSetting.get_instance(db)
    settings.company_logo_url = str(file_path)
    db.commit()
    
    return JSONResponse({
        "message": "Logo uploaded successfully",
        "logo_url": f"/static/uploads/logos/{unique_filename}",
        "filename": unique_filename
    })

@router.get("/invoice-settings")
async def get_invoice_settings(db: Session = Depends(get_db)):
    """Get all invoice customization settings"""
    
    settings = AppSetting.get_instance(db)
    
    # Return all invoice-related settings
    invoice_settings = {
        # General settings
        "invoice_paper_size": getattr(settings, 'invoice_paper_size', 'A4'),
        "invoice_template_style": getattr(settings, 'invoice_template_style', 'modern'),
        "invoice_margin_top": getattr(settings, 'invoice_margin_top', 20),
        "invoice_margin_bottom": getattr(settings, 'invoice_margin_bottom', 20),
        "invoice_margin_left": getattr(settings, 'invoice_margin_left', 20),
        "invoice_margin_right": getattr(settings, 'invoice_margin_right', 20),
        
        # Header settings
        "invoice_header_height": getattr(settings, 'invoice_header_height', 120),
        "invoice_header_background_color": getattr(settings, 'invoice_header_background_color', '#ffffff'),
        "invoice_header_text_color": getattr(settings, 'invoice_header_text_color', '#000000'),
        "invoice_header_border_style": getattr(settings, 'invoice_header_border_style', 'solid'),
        "invoice_header_border_width": getattr(settings, 'invoice_header_border_width', 2),
        "invoice_header_border_color": getattr(settings, 'invoice_header_border_color', '#333333'),
        
        # Logo settings
        "logo_width": getattr(settings, 'logo_width', 150),
        "logo_height": getattr(settings, 'logo_height', 75),
        "logo_position": getattr(settings, 'logo_position', 'left'),
        "logo_margin_top": getattr(settings, 'logo_margin_top', 10),
        "logo_margin_bottom": getattr(settings, 'logo_margin_bottom', 10),
        "company_logo_url": getattr(settings, 'company_logo_url', ''),
        
        # Company info settings
        "company_info_font_size": getattr(settings, 'company_info_font_size', 12),
        "company_info_font_weight": getattr(settings, 'company_info_font_weight', 'normal'),
        "company_info_color": getattr(settings, 'company_info_color', '#000000'),
        "company_info_alignment": getattr(settings, 'company_info_alignment', 'left'),
        
        # Invoice title settings
        "invoice_title_text": getattr(settings, 'invoice_title_text', 'INVOICE'),
        "invoice_title_font_size": getattr(settings, 'invoice_title_font_size', 36),
        "invoice_title_font_weight": getattr(settings, 'invoice_title_font_weight', 'bold'),
        "invoice_title_color": getattr(settings, 'invoice_title_color', '#333333'),
        "invoice_title_alignment": getattr(settings, 'invoice_title_alignment', 'right'),
        
        # Customer section settings
        "customer_section_background": getattr(settings, 'customer_section_background', '#f8f9fa'),
        "customer_section_border": getattr(settings, 'customer_section_border', True),
        "customer_section_border_color": getattr(settings, 'customer_section_border_color', '#dee2e6'),
        "customer_section_padding": getattr(settings, 'customer_section_padding', 20),
        
        # Items table settings
        "items_table_header_bg": getattr(settings, 'items_table_header_bg', '#343a40'),
        "items_table_header_text": getattr(settings, 'items_table_header_text', '#ffffff'),
        "items_table_border_color": getattr(settings, 'items_table_border_color', '#dee2e6'),
        "items_table_stripe_color": getattr(settings, 'items_table_stripe_color', '#f8f9fa'),
        "items_table_font_size": getattr(settings, 'items_table_font_size', 12),
        
        # Totals section settings
        "totals_section_background": getattr(settings, 'totals_section_background', '#f8f9fa'),
        "totals_section_border": getattr(settings, 'totals_section_border', True),
        "totals_font_size": getattr(settings, 'totals_font_size', 14),
        "totals_font_weight": getattr(settings, 'totals_font_weight', 'normal'),
        
        # Footer settings
        "invoice_footer_height": getattr(settings, 'invoice_footer_height', 100),
        "invoice_footer_background_color": getattr(settings, 'invoice_footer_background_color', '#ffffff'),
        "invoice_footer_text_color": getattr(settings, 'invoice_footer_text_color', '#000000'),
        "invoice_footer_border_style": getattr(settings, 'invoice_footer_border_style', 'solid'),
        "invoice_footer_border_width": getattr(settings, 'invoice_footer_border_width', 1),
        "invoice_footer_border_color": getattr(settings, 'invoice_footer_border_color', '#333333'),
        "invoice_footer_font_size": getattr(settings, 'invoice_footer_font_size', 11),
        "invoice_footer_alignment": getattr(settings, 'invoice_footer_alignment', 'left'),
        
        # Color scheme
        "invoice_primary_color": getattr(settings, 'invoice_primary_color', '#007bff'),
        "invoice_secondary_color": getattr(settings, 'invoice_secondary_color', '#6c757d'),
        "invoice_accent_color": getattr(settings, 'invoice_accent_color', '#28a745'),
        "invoice_background_color": getattr(settings, 'invoice_background_color', '#ffffff'),
        
        # Typography
        "invoice_font_family": getattr(settings, 'invoice_font_family', 'Arial, sans-serif'),
        "invoice_base_font_size": getattr(settings, 'invoice_base_font_size', 12),
        "invoice_line_height": getattr(settings, 'invoice_line_height', 1.4),
        
        # Content settings
        "invoice_show_logo": getattr(settings, 'invoice_show_logo', True),
        "invoice_show_company_address": getattr(settings, 'invoice_show_company_address', True),
        "invoice_show_company_phone": getattr(settings, 'invoice_show_company_phone', True),
        "invoice_show_company_email": getattr(settings, 'invoice_show_company_email', True),
        "invoice_show_company_website": getattr(settings, 'invoice_show_company_website', True),
        "invoice_show_vat_number": getattr(settings, 'invoice_show_vat_number', True),
        "invoice_show_customer_address": getattr(settings, 'invoice_show_customer_address', True),
        "invoice_show_customer_phone": getattr(settings, 'invoice_show_customer_phone', True),
        "invoice_show_customer_email": getattr(settings, 'invoice_show_customer_email', True),
        "invoice_show_customer_vat_number": getattr(settings, 'invoice_show_customer_vat_number', True),
        "invoice_show_payment_terms": getattr(settings, 'invoice_show_payment_terms', True),
        "invoice_show_due_date": getattr(settings, 'invoice_show_due_date', True),
        "invoice_show_discount": getattr(settings, 'invoice_show_discount', True),
        "invoice_show_vat_breakdown": getattr(settings, 'invoice_show_vat_breakdown', True),
        "invoice_footer_text": getattr(settings, 'invoice_footer_text', 'Thank you for your business!'),
        "invoice_terms_conditions": getattr(settings, 'invoice_terms_conditions', 'Payment due within 30 days.'),
        
        # Company info for preview
        "company_name": getattr(settings, 'company_name', 'Your Company Name'),
        "address": getattr(settings, 'address', '123 Business Street, City, Country'),
        "phone": getattr(settings, 'phone', '+123 456 7890'),
        "email": getattr(settings, 'email', 'info@company.com'),
        "website": getattr(settings, 'website', 'www.company.com'),
        "currency": getattr(settings, 'currency', 'BWP'),
    }
    
    return JSONResponse(invoice_settings)


@router.get("/layout", response_model=InvoiceLayoutResponse)
async def get_invoice_layout(db: Session = Depends(get_db)):
    settings = AppSetting.get_instance(db)
    config = settings.invoice_designer_config
    return InvoiceLayoutResponse(**config)


@router.post("/layout", response_model=InvoiceLayoutResponse)
async def save_invoice_layout(
    payload: InvoiceLayoutPayload,
    db: Session = Depends(get_db)
):
    settings = AppSetting.get_instance(db)
    current = settings.invoice_designer_config
    normalised_layout = AppSetting._normalise_layout_items(payload.layout)
    normalised_form = payload.form_data if isinstance(payload.form_data, dict) else {}
    normalised_metadata = payload.metadata if isinstance(payload.metadata, dict) else {}

    def _normalise_for_compare(data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert structure into JSON comparable representation."""
        return json.loads(json.dumps(data, sort_keys=True, default=str))

    current_struct = {
        "layout": current.get("layout", []),
        "form_data": current.get("form_data", {}),
        "metadata": current.get("metadata", {}),
    }

    incoming_struct = {
        "layout": normalised_layout,
        "form_data": normalised_form,
        "metadata": normalised_metadata,
    }

    if _normalise_for_compare(incoming_struct) == _normalise_for_compare(current_struct):
        return InvoiceLayoutResponse(**current)

    has_existing_data = bool(current_struct["layout"] or current_struct["form_data"] or current_struct["metadata"])
    current_version = current.get("version")
    if not isinstance(current_version, int):
        current_version = 1 if has_existing_data else 0

    next_version = 1 if not has_existing_data else current_version + 1
    timestamp = datetime.now(timezone.utc).isoformat()

    settings.invoice_designer_config = {
        "layout": normalised_layout,
        "form_data": normalised_form,
        "metadata": normalised_metadata,
        "updated_at": timestamp,
        "version": next_version
    }

    db.commit()
    db.refresh(settings)

    saved = settings.invoice_designer_config
    return InvoiceLayoutResponse(**saved)

@router.put("/invoice-settings")
async def update_invoice_settings(
    settings_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update invoice customization settings"""
    
    settings = AppSetting.get_instance(db)
    
    # Update settings
    for key, value in settings_data.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    
    db.commit()
    
    return JSONResponse({
        "message": "Invoice settings updated successfully",
        "updated_settings": settings_data
    })

@router.post("/preview-invoice/{invoice_id}")
async def preview_customized_invoice(
    invoice_id: str,
    db: Session = Depends(get_db)
):
    """Generate preview of customized invoice PDF"""
    
    try:
        invoice_service = InvoiceService(db)
        pdf_buffer = invoice_service.generate_pdf_invoice(invoice_id)
        
        return StreamingResponse(
            pdf_buffer,
            media_type='application/pdf',
            headers={"Content-Disposition": f"inline; filename=invoice_preview_{invoice_id}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating preview: {str(e)}")

@router.get("/reset-to-defaults")
async def reset_invoice_settings_to_defaults(db: Session = Depends(get_db)):
    """Reset all invoice customization settings to defaults"""
    
    settings = AppSetting.get_instance(db)
    
    # Reset to default values
    default_settings = {
        # General settings
        "invoice_paper_size": "A4",
        "invoice_template_style": "modern",
        "invoice_margin_top": 20,
        "invoice_margin_bottom": 20,
        "invoice_margin_left": 20,
        "invoice_margin_right": 20,
        
        # Header settings
        "invoice_header_height": 120,
        "invoice_header_background_color": "#ffffff",
        "invoice_header_text_color": "#000000",
        "invoice_header_border_style": "solid",
        "invoice_header_border_width": 2,
        "invoice_header_border_color": "#333333",
        
        # Logo settings
        "logo_width": 150,
        "logo_height": 75,
        "logo_position": "left",
        "logo_margin_top": 10,
        "logo_margin_bottom": 10,
        
        # Company info settings
        "company_info_font_size": 12,
        "company_info_font_weight": "normal",
        "company_info_color": "#000000",
        "company_info_alignment": "left",
        
        # Invoice title settings
        "invoice_title_text": "INVOICE",
        "invoice_title_font_size": 36,
        "invoice_title_font_weight": "bold",
        "invoice_title_color": "#333333",
        "invoice_title_alignment": "right",
        
        # Customer section settings
        "customer_section_background": "#f8f9fa",
        "customer_section_border": True,
        "customer_section_border_color": "#dee2e6",
        "customer_section_padding": 20,
        
        # Items table settings
        "items_table_header_bg": "#343a40",
        "items_table_header_text": "#ffffff",
        "items_table_border_color": "#dee2e6",
        "items_table_stripe_color": "#f8f9fa",
        "items_table_font_size": 12,
        
        # Totals section settings
        "totals_section_background": "#f8f9fa",
        "totals_section_border": True,
        "totals_font_size": 14,
        "totals_font_weight": "normal",
        
        # Footer settings
        "invoice_footer_height": 100,
        "invoice_footer_background_color": "#ffffff",
        "invoice_footer_text_color": "#000000",
        "invoice_footer_border_style": "solid",
        "invoice_footer_border_width": 1,
        "invoice_footer_border_color": "#333333",
        "invoice_footer_font_size": 11,
        "invoice_footer_alignment": "left",
        
        # Color scheme
        "invoice_primary_color": "#007bff",
        "invoice_secondary_color": "#6c757d",
        "invoice_accent_color": "#28a745",
        "invoice_background_color": "#ffffff",
        
        # Typography
        "invoice_font_family": "Arial, sans-serif",
        "invoice_base_font_size": 12,
        "invoice_line_height": 1.4,
    }
    
    # Apply default settings
    for key, value in default_settings.items():
        if hasattr(settings, key):
            setattr(settings, key, value)
    
    db.commit()
    
    return JSONResponse({
        "message": "Invoice settings reset to defaults successfully",
        "default_settings": default_settings
    })


@router.post("/save-settings")
async def save_invoice_settings(
    request: Request,
    db: Session = Depends(get_db)
):
    """Save invoice customization settings"""
    try:
        # Get JSON data from request body
        settings_data = await request.json()
        
        print(f"Received settings data: {settings_data}")
        
        # Get or create app settings instance
        settings = AppSetting.get_instance(db)
        
        # Track what was updated
        updated_fields = []
        
        # Update each field that exists in the model
        for field_name, value in settings_data.items():
            if hasattr(settings, field_name):
                # Handle different data types
                if isinstance(value, str):
                    if value.lower() in ['true', 'false']:
                        value = value.lower() == 'true'
                    elif field_name.endswith(('_size', '_width', '_height', '_margin_top', '_margin_bottom', '_start_number')):
                        try:
                            value = int(value)
                        except (ValueError, TypeError):
                            continue
                    elif field_name.endswith(('_rate', '_threshold', '_line_height')):
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            continue
                
                # Set the value
                old_value = getattr(settings, field_name)
                setattr(settings, field_name, value)
                updated_fields.append(field_name)
                
                print(f"Updated {field_name}: {old_value} -> {value}")
        
        # Commit changes
        db.commit()
        
        return JSONResponse({
            "success": True,
            "message": f"Successfully updated {len(updated_fields)} settings",
            "updated_fields": updated_fields,
            "data": {field: getattr(settings, field) for field in updated_fields}
        })
        
    except Exception as e:
        import traceback
        print(f"Error saving settings: {e}")
        traceback.print_exc()
        
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error saving settings: {str(e)}"
        )
