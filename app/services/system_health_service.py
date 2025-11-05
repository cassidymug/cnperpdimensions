"""
System Health & Error Management Service
Monitors system health, tracks errors, and provides diagnostic capabilities
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import traceback
import psutil
import logging
from decimal import Decimal

from app.models.system_health import (
    SystemError, SystemHealthCheck, SystemFix, 
    DataIntegrityIssue, PerformanceMetric
)
from app.models.inventory import Product, InventoryTransaction
from app.models.sales import Invoice, InvoiceItem
from app.models.accounting import JournalEntry
from app.core.database import engine

logger = logging.getLogger(__name__)


class SystemHealthService:
    """Service for monitoring system health and managing errors"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # =================================================================
    # ERROR TRACKING
    # =================================================================
    
    def log_error(
        self,
        error_type: str,
        severity: str,
        message: str,
        stack_trace: Optional[str] = None,
        module: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> SystemError:
        """Log an error to the system"""
        error = SystemError(
            error_type=error_type,
            severity=severity,
            message=message,
            stack_trace=stack_trace,
            module=module,
            user_id=user_id,
            error_metadata=metadata or {},
            status="new",
            resolved=False
        )
        self.db.add(error)
        self.db.commit()
        
        # Log to application logger as well
        logger.error(f"[{severity}] {error_type}: {message}")
        
        return error
    
    def get_errors(
        self,
        severity: Optional[str] = None,
        resolved: Optional[bool] = None,
        module: Optional[str] = None,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get errors with filtering"""
        query = self.db.query(SystemError)
        
        # Filter by date
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.filter(SystemError.created_at >= cutoff)
        
        if severity:
            query = query.filter(SystemError.severity == severity)
        if resolved is not None:
            query = query.filter(SystemError.resolved == resolved)
        if module:
            query = query.filter(SystemError.module == module)
        
        errors = query.order_by(desc(SystemError.created_at)).all()
        
        return [self._serialize_error(e) for e in errors]
    
    def resolve_error(
        self,
        error_id: str,
        resolution: str,
        fixed_by: Optional[str] = None
    ) -> SystemError:
        """Mark an error as resolved"""
        error = self.db.query(SystemError).filter(SystemError.id == error_id).first()
        if not error:
            raise ValueError(f"Error {error_id} not found")
        
        error.resolved = True
        error.status = "resolved"
        error.resolution = resolution
        error.resolved_at = datetime.utcnow()
        error.resolved_by_id = fixed_by
        
        self.db.commit()
        return error
    
    # =================================================================
    # HEALTH CHECKS
    # =================================================================
    
    def run_health_check(self, check_type: str = "full") -> Dict[str, Any]:
        """Run comprehensive system health check"""
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "checks": {}
        }
        
        checks = []
        
        if check_type in ["full", "database"]:
            checks.append(self._check_database_health())
        
        if check_type in ["full", "data_integrity"]:
            checks.append(self._check_data_integrity())
        
        if check_type in ["full", "performance"]:
            checks.append(self._check_performance())
        
        if check_type in ["full", "system"]:
            checks.append(self._check_system_resources())
        
        # Aggregate results
        for check in checks:
            results["checks"][check["name"]] = check
            if check["status"] == "error":
                results["overall_status"] = "error"
            elif check["status"] == "warning" and results["overall_status"] == "healthy":
                results["overall_status"] = "warning"
        
        # Save health check record
        health_check = SystemHealthCheck(
            check_type=check_type,
            status=results["overall_status"],
            results=results,
            duration_ms=0  # Calculate if needed
        )
        self.db.add(health_check)
        self.db.commit()
        
        return results
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and health"""
        try:
            # Test connection
            self.db.execute("SELECT 1")
            
            # Check table counts
            table_counts = {
                "products": self.db.query(func.count(Product.id)).scalar(),
                "invoices": self.db.query(func.count(Invoice.id)).scalar(),
                "transactions": self.db.query(func.count(InventoryTransaction.id)).scalar(),
            }
            
            return {
                "name": "database",
                "status": "healthy",
                "message": "Database connection OK",
                "details": table_counts
            }
        except Exception as e:
            return {
                "name": "database",
                "status": "error",
                "message": f"Database error: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _check_data_integrity(self) -> Dict[str, Any]:
        """Check for data integrity issues"""
        issues = []
        
        # Check for orphaned invoice items
        orphaned_items = self.db.execute("""
            SELECT COUNT(*) FROM invoice_items 
            WHERE invoice_id NOT IN (SELECT id FROM invoices)
        """).scalar()
        
        if orphaned_items > 0:
            issues.append(f"{orphaned_items} orphaned invoice items")
        
        # Check for negative inventory
        negative_inventory = self.db.query(Product).filter(Product.quantity < 0).count()
        if negative_inventory > 0:
            issues.append(f"{negative_inventory} products with negative inventory")
        
        # Check for unbalanced journal entries
        unbalanced_entries = self.db.execute("""
            SELECT journal_entry_id, SUM(debit_amount - credit_amount) as diff
            FROM journal_entry_lines
            GROUP BY journal_entry_id
            HAVING ABS(SUM(debit_amount - credit_amount)) > 0.01
        """).fetchall()
        
        if len(unbalanced_entries) > 0:
            issues.append(f"{len(unbalanced_entries)} unbalanced journal entries")
        
        status = "error" if issues else "healthy"
        
        return {
            "name": "data_integrity",
            "status": status,
            "message": "Integrity checks completed" if not issues else "Issues found",
            "details": {"issues": issues}
        }
    
    def _check_performance(self) -> Dict[str, Any]:
        """Check system performance metrics"""
        try:
            # Query performance - measure time for common queries
            import time
            
            start = time.time()
            self.db.query(Product).limit(100).all()
            product_query_time = (time.time() - start) * 1000
            
            start = time.time()
            self.db.query(Invoice).limit(100).all()
            invoice_query_time = (time.time() - start) * 1000
            
            # Determine status based on query times
            status = "healthy"
            if product_query_time > 1000 or invoice_query_time > 1000:
                status = "warning"
            if product_query_time > 5000 or invoice_query_time > 5000:
                status = "error"
            
            return {
                "name": "performance",
                "status": status,
                "message": "Performance metrics collected",
                "details": {
                    "product_query_ms": round(product_query_time, 2),
                    "invoice_query_ms": round(invoice_query_time, 2)
                }
            }
        except Exception as e:
            return {
                "name": "performance",
                "status": "error",
                "message": f"Performance check failed: {str(e)}",
                "details": {}
            }
    
    def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resources (CPU, memory, disk)"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Determine status
            status = "healthy"
            warnings = []
            
            if cpu_percent > 80:
                status = "warning"
                warnings.append(f"High CPU usage: {cpu_percent}%")
            
            if memory.percent > 85:
                status = "warning"
                warnings.append(f"High memory usage: {memory.percent}%")
            
            if disk.percent > 90:
                status = "error"
                warnings.append(f"Critical disk usage: {disk.percent}%")
            
            return {
                "name": "system_resources",
                "status": status,
                "message": "System resources OK" if not warnings else "; ".join(warnings),
                "details": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": round(memory.available / (1024**3), 2),
                    "disk_percent": disk.percent,
                    "disk_free_gb": round(disk.free / (1024**3), 2)
                }
            }
        except Exception as e:
            return {
                "name": "system_resources",
                "status": "error",
                "message": f"Resource check failed: {str(e)}",
                "details": {}
            }
    
    # =================================================================
    # AUTOMATED FIXES
    # =================================================================
    
    def apply_fix(
        self,
        fix_type: str,
        parameters: Optional[Dict] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Apply an automated fix to the system"""
        fix_functions = {
            "fix_negative_inventory": self._fix_negative_inventory,
            "fix_orphaned_invoice_items": self._fix_orphaned_invoice_items,
            "fix_unbalanced_journal_entries": self._fix_unbalanced_journal_entries,
            "recalculate_invoice_totals": self._recalculate_invoice_totals,
            "cleanup_old_errors": self._cleanup_old_errors,
        }
        
        if fix_type not in fix_functions:
            raise ValueError(f"Unknown fix type: {fix_type}")
        
        # Record fix attempt
        fix = SystemFix(
            fix_type=fix_type,
            parameters=parameters or {},
            status="running",
            dry_run=dry_run
        )
        self.db.add(fix)
        self.db.flush()
        
        try:
            # Apply the fix
            result = fix_functions[fix_type](parameters or {}, dry_run)
            
            # Update fix record
            fix.status = "completed" if result["success"] else "failed"
            fix.result = result
            fix.completed_at = datetime.utcnow()
            
            self.db.commit()
            
            return result
            
        except Exception as e:
            fix.status = "failed"
            fix.result = {"success": False, "error": str(e)}
            fix.error_message = str(e)
            self.db.commit()
            
            raise
    
    def _fix_negative_inventory(self, params: Dict, dry_run: bool) -> Dict[str, Any]:
        """Fix products with negative inventory"""
        negative_products = self.db.query(Product).filter(Product.quantity < 0).all()
        
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "affected_count": len(negative_products),
                "products": [{"id": p.id, "name": p.name, "quantity": float(p.quantity)} 
                            for p in negative_products]
            }
        
        # Fix by setting to 0 and logging
        for product in negative_products:
            old_qty = product.quantity
            product.quantity = Decimal("0")
            
            self.log_error(
                error_type="negative_inventory_fixed",
                severity="warning",
                message=f"Fixed negative inventory for {product.name}",
                metadata={"product_id": product.id, "old_quantity": float(old_qty)}
            )
        
        self.db.commit()
        
        return {
            "success": True,
            "dry_run": False,
            "affected_count": len(negative_products),
            "message": f"Fixed {len(negative_products)} products with negative inventory"
        }
    
    def _fix_orphaned_invoice_items(self, params: Dict, dry_run: bool) -> Dict[str, Any]:
        """Remove orphaned invoice items"""
        result = self.db.execute("""
            SELECT COUNT(*) FROM invoice_items 
            WHERE invoice_id NOT IN (SELECT id FROM invoices)
        """)
        count = result.scalar()
        
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "affected_count": count
            }
        
        self.db.execute("""
            DELETE FROM invoice_items 
            WHERE invoice_id NOT IN (SELECT id FROM invoices)
        """)
        self.db.commit()
        
        return {
            "success": True,
            "dry_run": False,
            "affected_count": count,
            "message": f"Removed {count} orphaned invoice items"
        }
    
    def _fix_unbalanced_journal_entries(self, params: Dict, dry_run: bool) -> Dict[str, Any]:
        """Fix unbalanced journal entries"""
        unbalanced = self.db.execute("""
            SELECT journal_entry_id, SUM(debit_amount - credit_amount) as diff
            FROM journal_entry_lines
            GROUP BY journal_entry_id
            HAVING ABS(SUM(debit_amount - credit_amount)) > 0.01
        """).fetchall()
        
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "affected_count": len(unbalanced),
                "entries": [{"id": row[0], "difference": float(row[1])} for row in unbalanced]
            }
        
        # This is complex - might need manual review
        # For now, just log them
        for entry_id, diff in unbalanced:
            self.log_error(
                error_type="unbalanced_journal_entry",
                severity="error",
                message=f"Journal entry {entry_id} is unbalanced by {diff}",
                metadata={"journal_entry_id": entry_id, "difference": float(diff)}
            )
        
        return {
            "success": True,
            "dry_run": False,
            "affected_count": len(unbalanced),
            "message": f"Logged {len(unbalanced)} unbalanced entries for manual review"
        }
    
    def _recalculate_invoice_totals(self, params: Dict, dry_run: bool) -> Dict[str, Any]:
        """Recalculate invoice totals"""
        invoice_id = params.get("invoice_id")
        
        if invoice_id:
            invoices = [self.db.query(Invoice).filter(Invoice.id == invoice_id).first()]
        else:
            # Recalculate all invoices from last 30 days
            cutoff = datetime.utcnow() - timedelta(days=30)
            invoices = self.db.query(Invoice).filter(Invoice.created_at >= cutoff).all()
        
        recalculated = 0
        
        for invoice in invoices:
            if not invoice:
                continue
            
            # Calculate from items
            items_total = sum(
                (item.quantity * item.price * (1 + item.vat_rate / 100))
                for item in invoice.items
            )
            
            if abs(float(invoice.total_amount or 0) - items_total) > 0.01:
                if not dry_run:
                    invoice.total_amount = Decimal(str(items_total))
                recalculated += 1
        
        if not dry_run:
            self.db.commit()
        
        return {
            "success": True,
            "dry_run": dry_run,
            "affected_count": recalculated,
            "message": f"Recalculated {recalculated} invoices"
        }
    
    def _cleanup_old_errors(self, params: Dict, dry_run: bool) -> Dict[str, Any]:
        """Clean up old resolved errors"""
        days = params.get("days", 90)
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        old_errors = self.db.query(SystemError).filter(
            and_(
                SystemError.resolved == True,
                SystemError.resolved_at < cutoff
            )
        ).all()
        
        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "affected_count": len(old_errors)
            }
        
        for error in old_errors:
            self.db.delete(error)
        
        self.db.commit()
        
        return {
            "success": True,
            "dry_run": False,
            "affected_count": len(old_errors),
            "message": f"Cleaned up {len(old_errors)} old errors"
        }
    
    # =================================================================
    # DIAGNOSTICS
    # =================================================================
    
    def run_diagnostics(self, module: Optional[str] = None) -> Dict[str, Any]:
        """Run comprehensive diagnostics"""
        diagnostics = {
            "timestamp": datetime.utcnow().isoformat(),
            "modules": {}
        }
        
        if not module or module == "inventory":
            diagnostics["modules"]["inventory"] = self._diagnose_inventory()
        
        if not module or module == "sales":
            diagnostics["modules"]["sales"] = self._diagnose_sales()
        
        if not module or module == "accounting":
            diagnostics["modules"]["accounting"] = self._diagnose_accounting()
        
        return diagnostics
    
    def _diagnose_inventory(self) -> Dict[str, Any]:
        """Diagnose inventory module"""
        return {
            "total_products": self.db.query(func.count(Product.id)).scalar(),
            "negative_inventory": self.db.query(Product).filter(Product.quantity < 0).count(),
            "zero_inventory": self.db.query(Product).filter(Product.quantity == 0).count(),
            "total_transactions": self.db.query(func.count(InventoryTransaction.id)).scalar(),
        }
    
    def _diagnose_sales(self) -> Dict[str, Any]:
        """Diagnose sales module"""
        return {
            "total_invoices": self.db.query(func.count(Invoice.id)).scalar(),
            "pending_invoices": self.db.query(Invoice).filter(Invoice.status == "pending").count(),
            "paid_invoices": self.db.query(Invoice).filter(Invoice.status == "paid").count(),
        }
    
    def _diagnose_accounting(self) -> Dict[str, Any]:
        """Diagnose accounting module"""
        try:
            unbalanced = self.db.execute("""
                SELECT COUNT(DISTINCT journal_entry_id)
                FROM journal_entry_lines
                GROUP BY journal_entry_id
                HAVING ABS(SUM(debit_amount - credit_amount)) > 0.01
            """).scalar() or 0
            
            return {
                "total_journal_entries": self.db.query(func.count(JournalEntry.id)).scalar(),
                "unbalanced_entries": unbalanced,
            }
        except:
            return {
                "error": "Could not diagnose accounting module"
            }
    
    # =================================================================
    # UTILITY METHODS
    # =================================================================
    
    def _serialize_error(self, error: SystemError) -> Dict[str, Any]:
        """Serialize error object"""
        return {
            "id": error.id,
            "error_type": error.error_type,
            "severity": error.severity,
            "message": error.message,
            "module": error.module,
            "status": error.status,
            "resolved": error.resolved,
            "created_at": error.created_at.isoformat() if error.created_at else None,
            "resolved_at": error.resolved_at.isoformat() if error.resolved_at else None,
            "metadata": error.error_metadata
        }
