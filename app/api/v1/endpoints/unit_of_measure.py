"""
Unit of Measure API Endpoints
RESTful API for managing units of measure
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.unit_of_measure_service import UnitOfMeasureService
from app.utils.logger import get_logger, log_exception, log_error_with_context
from app.schemas.unit_of_measure import (
    UnitOfMeasureCreate,
    UnitOfMeasureUpdate,
    UnitOfMeasureResponse,
    UnitConversionRequest,
    UnitConversionResponse,
    UOMListResponse,
    UOMCategoryInfo,
)

logger = get_logger(__name__)
router = APIRouter()


def _get_service(db: Session) -> UnitOfMeasureService:
    """Get UOM service instance"""
    return UnitOfMeasureService(db)


@router.get("", response_model=UOMListResponse)
def list_units(
    category: Optional[str] = Query(None, description="Filter by category"),
    subcategory: Optional[str] = Query(None, description="Filter by subcategory"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search name, abbreviation, description"),
    include_categories: bool = Query(False, description="Include category metadata"),
    db: Session = Depends(get_db),
):
    """
    List all units of measure with optional filtering

    Categories include:
    - quantity: Basic units (pieces, boxes)
    - length: mm, cm, m, km, inch, foot, mile
    - area: mm², m², hectare, acre
    - volume: ml, liter, gallon, m³
    - weight: mg, g, kg, ton, lb
    - temperature: °C, °F, K
    - pressure: Pa, bar, psi, atm
    - speed: m/s, km/h, mph, knot
    - time: sec, min, hour, day
    - angle: degree, radian
    - nautical: nautical mile, fathom
    - And many more scientific units
    """
    try:
        service = _get_service(db)
        units = service.list_units(
            category=category,
            subcategory=subcategory,
            is_active=is_active,
            search=search
        )

        categories_data = None
        if include_categories:
            categories_data = service.get_categories()

        return {
            "success": True,
            "units": units,
            "total": len(units),
            "categories": categories_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """Get all UOM categories with unit counts"""
    try:
        service = _get_service(db)
        categories = service.get_categories()
        return {
            "success": True,
            "categories": categories
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{unit_id}", response_model=UnitOfMeasureResponse)
def get_unit(unit_id: str, db: Session = Depends(get_db)):
    """Get a specific unit of measure by ID"""
    try:
        service = _get_service(db)
        unit = service.get_unit_by_id(unit_id)

        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")

        return unit
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=UnitOfMeasureResponse, status_code=201)
def create_unit(
    data: UnitOfMeasureCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new unit of measure

    For custom units, specify:
    - category: Must match an existing category
    - base_unit_id: Reference unit for conversions
    - conversion_factor: Multiply source by this to get base unit

    Example: Creating "dozen" in quantity category
    - base_unit_id: <id of "piece">
    - conversion_factor: 12.0
    """
    try:
        service = _get_service(db)
        unit = service.create_unit(data.model_dump())
        return unit
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{unit_id}", response_model=UnitOfMeasureResponse)
def update_unit(
    unit_id: str,
    data: UnitOfMeasureUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing unit of measure

    Note: System units have limited update fields for data integrity
    """
    try:
        service = _get_service(db)
        unit = service.update_unit(unit_id, data.model_dump(exclude_unset=True))
        return unit
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{unit_id}")
def delete_unit(unit_id: str, db: Session = Depends(get_db)):
    """
    Delete a unit of measure

    System units will be soft-deleted (is_active=false)
    Custom units will be permanently deleted
    Units in use by products cannot be deleted
    """
    try:
        service = _get_service(db)
        service.delete_unit(unit_id)
        return {"success": True, "message": "Unit deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert", response_model=UnitConversionResponse)
def convert_units(
    conversion: UnitConversionRequest,
    db: Session = Depends(get_db)
):
    """
    Convert a value from one unit to another

    Units must be in the same category (e.g., both length units)

    Example:
    ```json
    {
      "value": 100,
      "from_unit_id": "<millimeter_id>",
      "to_unit_id": "<meter_id>"
    }
    ```

    Returns: 0.1 meters
    """
    try:
        service = _get_service(db)
        result = service.convert_value(
            conversion.value,
            conversion.from_unit_id,
            conversion.to_unit_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
