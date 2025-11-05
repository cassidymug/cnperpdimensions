"""
Asset Management API Endpoints
Comprehensive asset management with depreciation, maintenance, and tracking
"""

from typing import Optional, List
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.core.response_wrapper import UnifiedResponse
from app.services.asset_management_service import AssetManagementService
from fastapi.encoders import jsonable_encoder
from app.models.asset_management import Asset, AssetMaintenance, AssetDepreciation, AssetImage, AssetCategory, AssetStatus, DepreciationMethod
from app.core.security import require_roles, require_any
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)
router = APIRouter()  # Dependencies removed for development


# Pydantic Models for API
class AssetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    status: str = "active"
    location: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_department: Optional[str] = None
    branch_id: Optional[str] = None
    purchase_date: date
    purchase_cost: Decimal
    current_value: Optional[Decimal] = None
    salvage_value: Optional[Decimal] = None
    depreciation_method: Optional[str] = None
    useful_life_years: Optional[int] = None
    depreciation_rate: Optional[Decimal] = None
    serial_number: Optional[str] = None
    model_number: Optional[str] = None
    manufacturer: Optional[str] = None
    warranty_expiry: Optional[date] = None
    vehicle_registration: Optional[str] = None
    engine_number: Optional[str] = None
    chassis_number: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = None
    vehicle_color: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission_type: Optional[str] = None
    mileage: Optional[int] = None
    last_service_date: Optional[date] = None
    next_service_date: Optional[date] = None
    insurance_expiry: Optional[date] = None
    license_expiry: Optional[date] = None
    inventory_item_id: Optional[str] = None
    inventory_quantity: Optional[int] = None
    accounting_code_id: Optional[str] = None

    # IFRS and accounting dimensions
    ifrs_category: Optional[str] = None
    cost_center_id: Optional[str] = None
    project_id: Optional[str] = None
    department_id: Optional[str] = None

    supplier_id: Optional[str] = None
    warranty_details: Optional[str] = None
    maintenance_schedule: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[dict] = None


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    location: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_department: Optional[str] = None
    branch_id: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_cost: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    salvage_value: Optional[Decimal] = None
    depreciation_method: Optional[str] = None
    useful_life_years: Optional[int] = None
    depreciation_rate: Optional[Decimal] = None
    serial_number: Optional[str] = None
    model_number: Optional[str] = None
    manufacturer: Optional[str] = None
    warranty_expiry: Optional[date] = None
    vehicle_registration: Optional[str] = None
    engine_number: Optional[str] = None
    chassis_number: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_year: Optional[int] = None
    vehicle_color: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission_type: Optional[str] = None
    mileage: Optional[int] = None
    last_service_date: Optional[date] = None
    next_service_date: Optional[date] = None
    insurance_expiry: Optional[date] = None
    license_expiry: Optional[date] = None
    inventory_item_id: Optional[str] = None
    inventory_quantity: Optional[int] = None
    accounting_code_id: Optional[str] = None

    # IFRS and accounting dimensions
    ifrs_category: Optional[str] = None
    cost_center_id: Optional[str] = None
    project_id: Optional[str] = None
    department_id: Optional[str] = None

    supplier_id: Optional[str] = None
    warranty_details: Optional[str] = None
    maintenance_schedule: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[dict] = None


class MaintenanceCreate(BaseModel):
    asset_id: str
    maintenance_type: str
    description: str
    maintenance_date: date
    next_maintenance_date: Optional[date] = None
    cost: Optional[Decimal] = None
    service_provider: Optional[str] = None
    service_provider_contact: Optional[str] = None
    parts_replaced: Optional[str] = None
    work_performed: Optional[str] = None
    technician_notes: Optional[str] = None
    status: str = "completed"


# Asset CRUD Endpoints
@router.post("/assets/")
async def create_asset(
    asset_data: AssetCreate,
    db: Session = Depends(get_db)
):
    """Create a new asset"""
    try:
        service = AssetManagementService(db)
        asset = service.create_asset(asset_data.dict())
        # JSON-safe encoding (enums, decimals, dates)
        asset_json = jsonable_encoder(asset.to_dict())
        return UnifiedResponse.success(
            data=asset_json,
            message="Asset created successfully"
        )
    except Exception as e:
        return UnifiedResponse.error(f"Error creating asset: {str(e)}")


@router.get("/assets/")
async def get_assets(
    category: Optional[str] = Query(None, description="Filter by asset category"),
    status: Optional[str] = Query(None, description="Filter by asset status"),
    branch_id: Optional[str] = Query(None, description="Filter by branch"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned user"),
    search: Optional[str] = Query(None, description="Search in name, code, serial number"),
    ifrs_category: Optional[str] = Query(None, description="Filter by IFRS category"),
    limit: int = Query(100, description="Number of assets to return"),
    offset: int = Query(0, description="Number of assets to skip"),
    db: Session = Depends(get_db)
):
    """Get assets with filters"""
    try:
        service = AssetManagementService(db)
        assets = service.get_assets(
            category=category,
            status=status,
            branch_id=branch_id,
            assigned_to=assigned_to,
            search=search,
            ifrs_category=ifrs_category,
            limit=limit,
            offset=offset
        )
        # Serialize SQLAlchemy models to plain dicts to avoid JSON encoding errors
        assets_data = [a.to_dict() for a in assets]
        # Ensure JSON-safe payload (convert enums/decimals/dates)
        assets_json = jsonable_encoder(assets_data)

        return UnifiedResponse.success(
            data=assets_json,
            message=f"Retrieved {len(assets)} assets",
            meta={
                "limit": limit,
                "offset": offset,
                "filters": {
                    "category": category,
                    "status": status,
                    "branch_id": branch_id,
                    "assigned_to": assigned_to,
                    "search": search,
                    "ifrs_category": ifrs_category
                }
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving assets: {str(e)}")


@router.get("/assets/{asset_id}")
async def get_asset(
    asset_id: str,
    db: Session = Depends(get_db)
):
    """Get asset by ID"""
    try:
        service = AssetManagementService(db)
        asset = service.get_asset(asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        # JSON-safe encoding for single asset
        return {
            "success": True,
            "data": jsonable_encoder(asset.to_dict())
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving asset: {str(e)}")


@router.put("/assets/{asset_id}")
async def update_asset(
    asset_id: str,
    asset_data: AssetUpdate,
    db: Session = Depends(get_db)
):
    """Update an asset"""
    try:
        service = AssetManagementService(db)
        asset = service.update_asset(asset_id, asset_data.dict(exclude_unset=True))
        return {
            "success": True,
            "data": asset.to_dict(),
            "message": "Asset updated successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating asset: {str(e)}")


@router.delete("/assets/{asset_id}")
async def delete_asset(
    asset_id: str,
    db: Session = Depends(get_db)
):
    """Delete an asset"""
    try:
        service = AssetManagementService(db)
        service.delete_asset(asset_id)
        return {
            "success": True,
            "message": "Asset deleted successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting asset: {str(e)}")


# Asset Search Endpoints
@router.get("/assets/search/serial/{serial_number}")
async def get_asset_by_serial(
    serial_number: str,
    db: Session = Depends(get_db)
):
    """Get asset by serial number"""
    try:
        service = AssetManagementService(db)
        asset = service.get_asset_by_serial_number(serial_number)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        return {
            "success": True,
            "data": asset.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving asset: {str(e)}")


@router.get("/assets/search/vehicle/{registration}")
async def get_vehicle_by_registration(
    registration: str,
    db: Session = Depends(get_db)
):
    """Get vehicle by registration number"""
    try:
        service = AssetManagementService(db)
        asset = service.get_vehicle_by_registration(registration)
        if not asset:
            raise HTTPException(status_code=404, detail="Vehicle not found")

        return {
            "success": True,
            "data": asset.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving vehicle: {str(e)}")


# Depreciation Endpoints
@router.get("/assets/{asset_id}/depreciation")
async def calculate_depreciation(
    asset_id: str,
    as_of_date: Optional[date] = Query(None, description="Calculate depreciation as of date"),
    db: Session = Depends(get_db)
):
    """Calculate depreciation for an asset"""
    try:
        service = AssetManagementService(db)
        depreciation_data = service.calculate_depreciation(asset_id, as_of_date)
        return {
            "success": True,
            "data": depreciation_data
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating depreciation: {str(e)}")


@router.post("/assets/{asset_id}/depreciation")
async def record_depreciation(
    asset_id: str,
    depreciation_date: Optional[date] = Query(None, description="Depreciation date"),
    db: Session = Depends(get_db)
):
    """Record depreciation for an asset"""
    try:
        service = AssetManagementService(db)
        depreciation_record = service.record_depreciation(asset_id, depreciation_date)
        return {
            "success": True,
            "data": depreciation_record.to_dict(),
            "message": "Depreciation recorded successfully"
        }
    except ValueError as e:
        error_msg = str(e)
        # Different status codes based on the type of error
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            # For validation errors like "No depreciation to record"
            raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording depreciation: {str(e)}")


# Maintenance Endpoints
@router.post("/maintenance/")
async def create_maintenance_record(
    maintenance_data: MaintenanceCreate,
    db: Session = Depends(get_db)
):
    """Create a maintenance record"""
    try:
        service = AssetManagementService(db)
        maintenance = service.create_maintenance_record(maintenance_data.dict())
        return {
            "success": True,
            "data": maintenance.to_dict(),
            "message": "Maintenance record created successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating maintenance record: {str(e)}")


@router.get("/assets/{asset_id}/maintenance")
async def get_maintenance_records(
    asset_id: str,
    db: Session = Depends(get_db)
):
    """Get maintenance records for an asset"""
    try:
        service = AssetManagementService(db)
        maintenance_records = service.get_maintenance_records(asset_id)
        return {
            "success": True,
            "data": [record.to_dict() for record in maintenance_records]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving maintenance records: {str(e)}")


@router.get("/maintenance/upcoming")
async def get_upcoming_maintenance(
    days_ahead: int = Query(30, description="Days ahead to check for maintenance"),
    db: Session = Depends(get_db)
):
    """Get assets with upcoming maintenance"""
    try:
        service = AssetManagementService(db)
        assets = service.get_upcoming_maintenance(days_ahead)
        return {
            "success": True,
            "data": [asset.to_dict() for asset in assets],
            "days_ahead": days_ahead
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving upcoming maintenance: {str(e)}")


# Reporting Endpoints
@router.get("/assets/summary")
async def get_asset_summary(
    db: Session = Depends(get_db)
):
    """Get asset summary statistics"""
    try:
        service = AssetManagementService(db)
        summary = service.get_asset_summary()
        return {
            "success": True,
            "data": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving asset summary: {str(e)}")


@router.get("/assets/reports/depreciation")
async def get_depreciation_report(
    as_of_date: Optional[date] = Query(None, description="Report as of date"),
    db: Session = Depends(get_db)
):
    """Generate depreciation report"""
    try:
        service = AssetManagementService(db)
        report = service.get_depreciation_report(as_of_date)
        return {
            "success": True,
            "data": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating depreciation report: {str(e)}")


# Category Configuration Endpoints
@router.get("/categories/config")
async def get_category_configs(
    db: Session = Depends(get_db)
):
    """Get all category configurations"""
    try:
        service = AssetManagementService(db)
        configs = service.get_all_category_configs()
        return {
            "success": True,
            "data": [config.to_dict() for config in configs]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving category configs: {str(e)}")


@router.get("/categories/config/{category}")
async def get_category_config(
    category: str,
    db: Session = Depends(get_db)
):
    """Get category configuration"""
    try:
        service = AssetManagementService(db)
        config = service.get_category_config(category)
        if not config:
            raise HTTPException(status_code=404, detail="Category configuration not found")

        return {
            "success": True,
            "data": config.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving category config: {str(e)}")


# Utility Endpoints
@router.get("/categories")
async def get_asset_categories():
    """Get all asset categories"""
    # Return the actual enum values that match the database
    categories = [
        "VEHICLE", "EQUIPMENT", "FURNITURE", "BUILDING", "LAND",
        "SOFTWARE", "INTANGIBLE", "MACHINERY", "COMPUTER",
        "OFFICE_EQUIPMENT", "INVENTORY", "OTHER"
    ]
    return {
        "success": True,
        "data": categories
    }


@router.get("/statuses")
async def get_asset_statuses():
    """Get all asset statuses"""
    return {
        "success": True,
        "data": [status.value for status in AssetStatus]
    }


@router.get("/depreciation-methods")
async def get_depreciation_methods():
    """Get all depreciation methods"""
    return {
        "success": True,
        "data": [method.value for method in DepreciationMethod]
    }


# Bulk Operations
@router.post("/assets/bulk-depreciation")
async def record_bulk_depreciation(
    as_of_date: Optional[date] = Query(None, description="Depreciation date"),
    db: Session = Depends(get_db)
):
    """Record depreciation for all active assets"""
    try:
        service = AssetManagementService(db)
        assets = service.get_assets(status="active")

        results = []
        for asset in assets:
            try:
                depreciation_record = service.record_depreciation(asset.id, as_of_date)
                results.append({
                    "asset_id": asset.id,
                    "asset_code": asset.asset_code,
                    "success": True,
                    "depreciation_amount": float(depreciation_record.depreciation_amount)
                })
            except Exception as e:
                results.append({
                    "asset_id": asset.id,
                    "asset_code": asset.asset_code,
                    "success": False,
                    "error": str(e)
                })

        return {
            "success": True,
            "data": {
                "total_assets": len(assets),
                "successful": len([r for r in results if r["success"]]),
                "failed": len([r for r in results if not r["success"]]),
                "results": results
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error recording bulk depreciation: {str(e)}")


@router.post("/assets/cleanup-test")
async def cleanup_test_assets(
    confirm: bool = Query(False, description="Require true to actually delete"),
    include_inventory: bool = Query(False, description="Also delete assets linked to inventory items"),
    db: Session = Depends(get_db)
):
    """Delete demo/test assets using the same heuristics as the CLI script."""
    try:
        from sqlalchemy import or_
        q = db.query(Asset)
        patterns = [
            Asset.asset_code.ilike('TEST%'),
            Asset.asset_code.ilike('DEMO%'),
            Asset.asset_code.ilike('SAMPLE%'),
            Asset.name.ilike('test%'),
            Asset.name.ilike('demo%'),
            Asset.name.ilike('sample%'),
            Asset.notes.ilike('%test%'),
            Asset.notes.ilike('%demo%'),
            Asset.notes.ilike('%sample%'),
        ]
        q = q.filter(or_(*patterns))
        if not include_inventory:
            q = q.filter(or_(Asset.inventory_item_id.is_(None), Asset.inventory_item_id == ''))
        matches: List[Asset] = q.all()
        count = len(matches)

        if not confirm:
            return UnifiedResponse.success(
                data={"matched": count},
                message="Dry run - set confirm=true to delete"
            )

        ids = [a.id for a in matches]
        if not ids:
            return UnifiedResponse.success(
                data={"deleted": 0},
                message="No test assets found"
            )

        # Delete children then assets
        db.query(AssetMaintenance).filter(AssetMaintenance.asset_id.in_(ids)).delete(synchronize_session=False)
        db.query(AssetDepreciation).filter(AssetDepreciation.asset_id.in_(ids)).delete(synchronize_session=False)
        db.query(AssetImage).filter(AssetImage.asset_id.in_(ids)).delete(synchronize_session=False)
        deleted = db.query(Asset).filter(Asset.id.in_(ids)).delete(synchronize_session=False)
        db.commit()

        return UnifiedResponse.success(
            data={"deleted": deleted},
            message=f"Deleted {deleted} test assets"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error cleaning test assets: {str(e)}")
