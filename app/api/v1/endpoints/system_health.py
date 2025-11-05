"""
API endpoints for System Health & Error Management
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.services.system_health_service import SystemHealthService
from pydantic import BaseModel, Field
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)


router = APIRouter()


# =================================================================
# SCHEMAS
# =================================================================

class ErrorLogCreate(BaseModel):
    error_type: str
    severity: str = Field(..., pattern="^(critical|error|warning|info)$")
    message: str
    stack_trace: Optional[str] = None
    module: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[dict] = None


class ErrorResolve(BaseModel):
    resolution: str
    fixed_by: Optional[str] = None


class FixRequest(BaseModel):
    fix_type: str
    parameters: Optional[dict] = None
    dry_run: bool = True


# =================================================================
# ERROR MANAGEMENT
# =================================================================

@router.post("/errors")
def log_error(
    payload: ErrorLogCreate,
    db: Session = Depends(get_db)
):
    """Log a system error"""
    service = SystemHealthService(db)
    error = service.log_error(
        error_type=payload.error_type,
        severity=payload.severity,
        message=payload.message,
        stack_trace=payload.stack_trace,
        module=payload.module,
        user_id=payload.user_id,
        metadata=payload.metadata
    )
    return {
        "success": True,
        "error_id": error.id,
        "message": "Error logged successfully"
    }


@router.get("/errors")
def get_errors(
    severity: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None),
    module: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get system errors with filtering"""
    service = SystemHealthService(db)
    errors = service.get_errors(
        severity=severity,
        resolved=resolved,
        module=module,
        days=days
    )
    return {
        "success": True,
        "count": len(errors),
        "errors": errors
    }


@router.post("/errors/{error_id}/resolve")
def resolve_error(
    error_id: str,
    payload: ErrorResolve,
    db: Session = Depends(get_db)
):
    """Mark an error as resolved"""
    service = SystemHealthService(db)
    try:
        error = service.resolve_error(
            error_id=error_id,
            resolution=payload.resolution,
            fixed_by=payload.fixed_by
        )
        return {
            "success": True,
            "message": "Error resolved successfully",
            "error": {
                "id": error.id,
                "resolved_at": error.resolved_at.isoformat() if error.resolved_at else None
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =================================================================
# HEALTH CHECKS
# =================================================================

@router.get("/health")
def health_check(
    check_type: str = Query("full", regex="^(full|database|data_integrity|performance|system)$"),
    db: Session = Depends(get_db)
):
    """Run system health check"""
    service = SystemHealthService(db)
    results = service.run_health_check(check_type=check_type)
    return {
        "success": True,
        "health": results
    }


@router.get("/health/history")
def health_check_history(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db)
):
    """Get health check history"""
    from app.models.system_health import SystemHealthCheck
    from datetime import timedelta
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    checks = db.query(SystemHealthCheck).filter(
        SystemHealthCheck.created_at >= cutoff
    ).order_by(SystemHealthCheck.created_at.desc()).all()
    
    return {
        "success": True,
        "count": len(checks),
        "checks": [
            {
                "id": check.id,
                "check_type": check.check_type,
                "status": check.status,
                "created_at": check.created_at.isoformat() if check.created_at else None,
                "duration_ms": check.duration_ms,
                "results": check.results
            }
            for check in checks
        ]
    }


# =================================================================
# AUTOMATED FIXES
# =================================================================

@router.post("/fixes")
def apply_fix(
    payload: FixRequest,
    db: Session = Depends(get_db)
):
    """Apply an automated fix"""
    service = SystemHealthService(db)
    try:
        result = service.apply_fix(
            fix_type=payload.fix_type,
            parameters=payload.parameters,
            dry_run=payload.dry_run
        )
        return {
            "success": True,
            "result": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fix failed: {str(e)}")


@router.get("/fixes")
def get_fixes(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get applied fixes history"""
    from app.models.system_health import SystemFix
    from datetime import timedelta
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    fixes = db.query(SystemFix).filter(
        SystemFix.created_at >= cutoff
    ).order_by(SystemFix.created_at.desc()).all()
    
    return {
        "success": True,
        "count": len(fixes),
        "fixes": [
            {
                "id": fix.id,
                "fix_type": fix.fix_type,
                "status": fix.status,
                "dry_run": fix.dry_run,
                "created_at": fix.created_at.isoformat() if fix.created_at else None,
                "completed_at": fix.completed_at.isoformat() if fix.completed_at else None,
                "result": fix.result
            }
            for fix in fixes
        ]
    }


@router.get("/fixes/available")
def get_available_fixes(db: Session = Depends(get_db)):
    """Get list of available automated fixes"""
    return {
        "success": True,
        "fixes": [
            {
                "type": "fix_negative_inventory",
                "name": "Fix Negative Inventory",
                "description": "Set negative inventory quantities to 0",
                "severity": "high",
                "parameters": {}
            },
            {
                "type": "fix_orphaned_invoice_items",
                "name": "Remove Orphaned Invoice Items",
                "description": "Delete invoice items without parent invoices",
                "severity": "medium",
                "parameters": {}
            },
            {
                "type": "fix_unbalanced_journal_entries",
                "name": "Fix Unbalanced Journal Entries",
                "description": "Log unbalanced journal entries for review",
                "severity": "high",
                "parameters": {}
            },
            {
                "type": "recalculate_invoice_totals",
                "name": "Recalculate Invoice Totals",
                "description": "Recalculate invoice totals from line items",
                "severity": "medium",
                "parameters": {
                    "invoice_id": "Optional: specific invoice ID"
                }
            },
            {
                "type": "cleanup_old_errors",
                "name": "Clean Up Old Errors",
                "description": "Remove resolved errors older than specified days",
                "severity": "low",
                "parameters": {
                    "days": "Number of days (default: 90)"
                }
            }
        ]
    }


# =================================================================
# DIAGNOSTICS
# =================================================================

@router.get("/diagnostics")
def run_diagnostics(
    module: Optional[str] = Query(None, regex="^(inventory|sales|accounting)$"),
    db: Session = Depends(get_db)
):
    """Run system diagnostics"""
    service = SystemHealthService(db)
    diagnostics = service.run_diagnostics(module=module)
    return {
        "success": True,
        "diagnostics": diagnostics
    }


@router.get("/stats")
def get_system_stats(db: Session = Depends(get_db)):
    """Get overall system statistics"""
    from app.models.system_health import SystemError, SystemHealthCheck
    from datetime import timedelta
    # Error stats
    total_errors = db.query(SystemError).count()
    unresolved_errors = db.query(SystemError).filter(SystemError.resolved == False).count()
    
    # Recent errors by severity
    cutoff = datetime.utcnow() - timedelta(days=7)
    recent_errors = db.query(
        SystemError.severity,
        db.func.count(SystemError.id)
    ).filter(
        SystemError.created_at >= cutoff
    ).group_by(SystemError.severity).all()
    
    # Latest health check
    latest_check = db.query(SystemHealthCheck).order_by(
        SystemHealthCheck.created_at.desc()
    ).first()
    
    return {
        "success": True,
        "stats": {
            "total_errors": total_errors,
            "unresolved_errors": unresolved_errors,
            "recent_errors_by_severity": {
                severity: count for severity, count in recent_errors
            },
            "latest_health_check": {
                "status": latest_check.status if latest_check else None,
                "checked_at": latest_check.created_at.isoformat() if latest_check and latest_check.created_at else None
            } if latest_check else None
        }
    }
