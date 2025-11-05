from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
# from app.core.security import get_current_user  # Removed for development
from app.models.app_setting import AppSetting
from app.models.user import User
from app.models.inventory import Product
from app.models.sales import Sale
from app.models.sales import Customer
from app.schemas.app_setting import (
    AppSettingResponse, AppSettingUpdate, RolesConfigUpdate, 
    ThemeUpdate, SystemInfo
)
from app.schemas.user import UserResponse, UserUpdate
from app.core.config import settings
import psutil
import os
from datetime import datetime, timedelta

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()


@router.get("/settings", response_model=AppSettingResponse)
async def get_app_settings(
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Get application settings"""
    # Check if user has permission to manage settings
    if False:  # Permission check removed for development
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update only provided fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Delete user"""
    # Check if user has permission to manage users
    if False:  # Permission check removed for development
    
    # Get app settings
    app_settings = AppSetting.get_instance(db)
    
    # Get system statistics
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_products = db.query(Product).count()
    total_sales = db.query(Sale).count()
    total_customers = db.query(Customer).count()
    
    # Get system metrics
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Calculate uptime (simplified)
    uptime = "24 hours"  # This would be calculated from system start time
    
    system_info = SystemInfo(
        app_name=app_settings.app_name,
        version="1.0.0",
        environment=settings.environment,
        database_url=settings.database_url,
        redis_url=settings.redis_url,
        debug_mode=app_settings.debug_mode,
        maintenance_mode=app_settings.maintenance_mode,
        uptime=uptime,
        memory_usage=f"{memory.percent}%",
        disk_usage=f"{disk.percent}%",
        active_users=active_users,
        total_users=total_users,
        total_products=total_products,
        total_sales=total_sales,
        total_customers=total_customers,
        system_health="healthy"
    )
    
    return system_info


@router.get("/system/currencies")
async def get_currencies():
    """Get available currencies"""
    return AppSetting.get_currencies()


@router.get("/system/currency-symbol/{currency_code}")
async def get_currency_symbol(currency_code: str):
    """Get currency symbol for a given currency code"""
    symbol = AppSetting.get_currency_symbol(currency_code)
    return {"currency_code": currency_code, "symbol": symbol}


@router.get("/system/countries")
async def get_countries():
    """Get available countries"""
    return AppSetting.get_countries()


@router.get("/system/locales")
async def get_locales():
    """Get available locales"""
    return AppSetting.get_locales()


@router.get("/system/measurement-systems")
async def get_measurement_systems():
    """Get available measurement systems"""
    return AppSetting.get_measurement_systems()


@router.get("/system/units-of-measure")
async def get_units_of_measure():
    """Get available units of measure"""
    return AppSetting.get_units_of_measure()


@router.get("/system/theme-modes")
async def get_theme_modes():
    """Get available theme modes"""
    return AppSetting.get_theme_modes()


@router.get("/system/color-schemes")
async def get_color_schemes():
    """Get available color schemes"""
    return AppSetting.get_color_schemes()


@router.get("/system/roles")
async def get_roles(
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Get current roles configuration"""
    # Check if user has permission to manage settings
    if False:  # Permission check removed for development
        # 403 error removed for development
    
    app_settings = AppSetting.get_instance(db)
    return {"roles": app_settings.roles}


@router.get("/system/permissions")
async def get_permissions():
    """Get available permissions"""
    return {
        "permissions": [
            "edit_product",
            "manage_product", 
            "delete_product",
            "view_reports",
            "manage_users",
            "manage_settings",
            "manage_accounting",
            "manage_inventory",
            "manage_sales",
            "manage_purchases",
            "manage_banking",
            "manage_vat",
            "view_audit_logs"
        ],
        "roles": [
            "super_admin",
            "admin",
            "manager",
            "staff",
            "viewer"
        ]
    }


@router.post("/system/maintenance-mode")
async def toggle_maintenance_mode(
    enabled: bool,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Toggle maintenance mode"""
    # Check if user has permission to manage settings
    if False:  # Permission check removed for development
        # 403 error removed for development
    
    app_settings = AppSetting.get_instance(db)
    app_settings.maintenance_mode = enabled
    
    db.commit()
    
    return {
        "message": f"Maintenance mode {'enabled' if enabled else 'disabled'}",
        "maintenance_mode": enabled
    }


@router.post("/system/backup")
async def create_backup(
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Create system backup"""
    # Check if user has permission to manage settings
    if False:  # Permission check removed for development
        # 403 error removed for development
    
    # This would implement actual backup logic
    # For now, return a placeholder response
    return {
        "message": "Backup created successfully",
        "backup_id": "backup_2024_01_01_120000",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/system/logs")
async def get_system_logs(
    limit: int = 100,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Get system logs"""
    # Check if user has permission to view audit logs
    if False:  # Permission check removed for development
        # 403 error removed for development
    
    # This would implement actual log retrieval
    # For now, return a placeholder response
    return {
        "logs": [
            {
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "message": "System logs endpoint accessed",
                "user": "development@example.com"
            }
        ],
        "total": 1
    }


@router.get("/dashboard/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Get dashboard statistics"""
    # Check if user has permission to view reports
    if False:  # Permission check removed for development
        # 403 error removed for development
    
    # Get basic statistics
    total_users = db.query(User).count()
    total_products = db.query(Product).count()
    total_sales = db.query(Sale).count()
    total_customers = db.query(Customer).count()
    
    # Get recent activity
    recent_sales = db.query(Sale).order_by(Sale.created_at.desc()).limit(5).all()
    recent_users = db.query(User).order_by(User.created_at.desc()).limit(5).all()
    
    # Get low stock products
    low_stock_products = db.query(Product).filter(
        Product.quantity <= Product.reorder_point
    ).limit(10).all()
    
    return {
        "statistics": {
            "total_users": total_users,
            "total_products": total_products,
            "total_sales": total_sales,
            "total_customers": total_customers
        },
        "recent_activity": {
            "recent_sales": [
                {
                    "id": str(sale.id),
                    "total_amount": float(sale.total_amount),
                    "date": sale.created_at.isoformat()
                }
                for sale in recent_sales
            ],
            "recent_users": [
                {
                    "id": str(user.id),
                    "email": user.email,
                    "date": user.created_at.isoformat()
                }
                for user in recent_users
            ]
        },
        "alerts": {
            "low_stock_products": [
                {
                    "id": str(product.id),
                    "name": product.name,
                    "quantity": product.quantity,
                    "reorder_point": product.reorder_point
                }
                for product in low_stock_products
            ]
        }
    } 