"""
Universal Document Printing API

This endpoint handles printing for ALL documents except:
1. Invoices (use /invoices/{id}/print)
2. POS receipts (use /pos/sales/{id}/receipt/print)

ALL documents handled here are printed on A4 plain paper.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from app.core.database import get_db
from app.services.document_printing_service import DocumentPrintingService

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()


@router.get("/print/{document_type}/{document_id}")
async def print_document(
    document_type: str,
    document_id: str,
    title: Optional[str] = Query(None, description="Custom document title"),
    db: Session = Depends(get_db)
):
    """
    Print any document (except invoices and POS receipts) as A4 PDF
    
    Documents are ALWAYS printed on A4 plain paper regardless of printer settings.
    
    Supported document types:
    - trial_balance, balance_sheet, income_statement
    - customer_statement, supplier_statement
    - purchase_order, quote
    - bank_reconciliation, vat_return
    - aging_report, cash_flow, budget_report
    - management_report, audit_trail
    """
    
    document_service = DocumentPrintingService(db)
    
    # Check if this is a valid document type for this service
    if document_type in ['invoice', 'pos_receipt']:
        raise HTTPException(
            status_code=400, 
            detail=f"Document type '{document_type}' should use specific endpoints: "
                   f"Invoices: /invoices/{{id}}/print, POS receipts: /pos/sales/{{id}}/receipt/print"
        )
    
    try:
        # Generate document (always A4 PDF)
        format_type, content, filename = document_service.generate_document_pdf(
            document_type=document_type,
            document_id=document_id,
            title=title
        )
        
        # Return PDF for download
        headers = {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
        
        return Response(
            content=content,
            media_type='application/pdf',
            headers=headers
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {str(e)}")


@router.get("/print-info")
async def get_document_printing_info(db: Session = Depends(get_db)):
    """Get information about document printing rules"""
    
    document_service = DocumentPrintingService(db)
    
    return {
        "success": True,
        "data": {
            "printing_rules": {
                "invoices": {
                    "endpoint": "/invoices/{id}/print",
                    "settings_applicable": True,
                    "description": "Uses invoice printer settings (A4 PDF or dot matrix)"
                },
                "pos_receipts": {
                    "endpoint": "/pos/sales/{id}/receipt/print", 
                    "settings_applicable": True,
                    "description": "Uses POS receipt printer settings (thermal, impact, etc.)"
                },
                "other_documents": {
                    "endpoint": "/documents/print/{type}/{id}",
                    "settings_applicable": False,
                    "description": "Always A4 plain paper PDF, printer settings ignored"
                }
            },
            "a4_plain_paper_documents": document_service.get_supported_document_types(),
            "printing_info": document_service.get_printing_info()
        }
    }


@router.get("/preview/{document_type}/{document_id}")
async def preview_document(
    document_type: str,
    document_id: str,
    title: Optional[str] = Query(None, description="Custom document title"),
    db: Session = Depends(get_db)
):
    """
    Preview document information (metadata only, no PDF generation)
    """
    
    document_service = DocumentPrintingService(db)
    
    if document_type in ['invoice', 'pos_receipt']:
        raise HTTPException(
            status_code=400,
            detail="Use specific preview endpoints for invoices and POS receipts"
        )
    
    return {
        "success": True,
        "data": {
            "document_type": document_type,
            "document_id": document_id,
            "title": title or document_type.replace('_', ' ').title(),
            "format": "PDF",
            "paper_size": "A4 (210 × 297 mm)",
            "paper_type": "Plain paper",
            "printer_settings_applicable": False,
            "note": "This document will always be printed on A4 plain paper regardless of any printer settings."
        }
    }


@router.get("/test-print")
async def test_document_printing(
    document_type: str = Query('trial_balance', description="Document type to test"),
    db: Session = Depends(get_db)
):
    """
    Test document printing with sample data
    """
    
    document_service = DocumentPrintingService(db)
    
    try:
        # Generate test document
        test_id = f"TEST_{document_type.upper()}"
        format_type, content, filename = document_service.generate_document_pdf(
            document_type=document_type,
            document_id=test_id,
            title=f"Test {document_type.replace('_', ' ').title()}",
            content_data={"test": True, "generated_for": "printer_testing"}
        )
        
        # Return test PDF
        headers = {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename="TEST_{filename}"'
        }
        
        return Response(
            content=content,
            media_type='application/pdf',
            headers=headers
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate test document: {str(e)}")


@router.get("/supported-types")
async def get_supported_document_types(db: Session = Depends(get_db)):
    """Get list of supported document types for A4 plain paper printing"""
    
    document_service = DocumentPrintingService(db)
    
    return {
        "success": True,
        "data": {
            "supported_types": document_service.get_supported_document_types(),
            "note": "All these document types are printed on A4 plain paper regardless of printer settings",
            "excluded_types": ["invoice", "pos_receipt"],
            "excluded_note": "Invoices and POS receipts have their own printer settings and endpoints"
        }
    }
