"""
Unit of Measure Service
Handles UOM management, conversions, and business logic
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from decimal import Decimal
import uuid

from app.models.inventory import UnitOfMeasure
from app.schemas.unit_of_measure import (
    UnitOfMeasureCreate,
    UnitOfMeasureUpdate,
    UnitConversionRequest,
)


class UnitOfMeasureService:
    """Service for managing units of measure"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def list_units(
        self,
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all units with optional filtering"""
        query = self.db.query(UnitOfMeasure)
        
        if category:
            query = query.filter(UnitOfMeasure.category == category)
        
        if subcategory:
            query = query.filter(UnitOfMeasure.subcategory == subcategory)
        
        if is_active is not None:
            query = query.filter(UnitOfMeasure.is_active == is_active)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    UnitOfMeasure.name.ilike(search_pattern),
                    UnitOfMeasure.abbreviation.ilike(search_pattern),
                    UnitOfMeasure.description.ilike(search_pattern),
                )
            )
        
        query = query.order_by(
            UnitOfMeasure.category,
            UnitOfMeasure.display_order,
            UnitOfMeasure.name
        )
        
        units = query.all()
        return [self._serialize_unit(unit) for unit in units]
    
    def get_unit_by_id(self, unit_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific unit by ID"""
        unit = self.db.query(UnitOfMeasure).filter(
            UnitOfMeasure.id == unit_id
        ).first()
        
        if not unit:
            return None
        
        return self._serialize_unit(unit)
    
    def create_unit(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new unit of measure"""
        # Validate category compatibility if base_unit_id provided
        if data.get('base_unit_id'):
            base_unit = self.db.query(UnitOfMeasure).filter(
                UnitOfMeasure.id == data['base_unit_id']
            ).first()
            
            if not base_unit:
                raise ValueError("Base unit not found")
            
            if base_unit.category != data['category']:
                raise ValueError(
                    f"Cannot create unit in category '{data['category']}' "
                    f"with base unit from category '{base_unit.category}'"
                )
        
        # Check for duplicate abbreviation in same category
        existing = self.db.query(UnitOfMeasure).filter(
            and_(
                UnitOfMeasure.abbreviation == data['abbreviation'],
                UnitOfMeasure.category == data['category'],
                UnitOfMeasure.is_active == True,
            )
        ).first()
        
        if existing:
            raise ValueError(
                f"Unit with abbreviation '{data['abbreviation']}' "
                f"already exists in category '{data['category']}'"
            )
        
        unit = UnitOfMeasure(
            id=str(uuid.uuid4()),
            **data
        )
        
        self.db.add(unit)
        self.db.commit()
        self.db.refresh(unit)
        
        return self._serialize_unit(unit)
    
    def update_unit(self, unit_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing unit"""
        unit = self.db.query(UnitOfMeasure).filter(
            UnitOfMeasure.id == unit_id
        ).first()
        
        if not unit:
            raise ValueError("Unit not found")
        
        # Prevent updating system units' core properties
        if unit.is_system_unit:
            # Only allow updating display_order, is_active, usage_hint
            allowed_fields = ['display_order', 'is_active', 'usage_hint', 'description']
            data = {k: v for k, v in data.items() if k in allowed_fields}
        
        for key, value in data.items():
            if hasattr(unit, key):
                setattr(unit, key, value)
        
        self.db.commit()
        self.db.refresh(unit)
        
        return self._serialize_unit(unit)
    
    def delete_unit(self, unit_id: str) -> bool:
        """Delete a unit (soft delete for system units)"""
        unit = self.db.query(UnitOfMeasure).filter(
            UnitOfMeasure.id == unit_id
        ).first()
        
        if not unit:
            raise ValueError("Unit not found")
        
        # Check if unit is in use
        if unit.products:
            raise ValueError("Cannot delete unit that is in use by products")
        
        if unit.is_system_unit:
            # Soft delete
            unit.is_active = False
            self.db.commit()
        else:
            # Hard delete custom units
            self.db.delete(unit)
            self.db.commit()
        
        return True
    
    def convert_value(
        self,
        value: float,
        from_unit_id: str,
        to_unit_id: str
    ) -> Dict[str, Any]:
        """Convert a value from one unit to another"""
        from_unit = self.db.query(UnitOfMeasure).filter(
            UnitOfMeasure.id == from_unit_id
        ).first()
        
        to_unit = self.db.query(UnitOfMeasure).filter(
            UnitOfMeasure.id == to_unit_id
        ).first()
        
        if not from_unit or not to_unit:
            raise ValueError("Invalid unit ID")
        
        if from_unit.category != to_unit.category:
            raise ValueError(
                f"Cannot convert between different categories: "
                f"{from_unit.category} and {to_unit.category}"
            )
        
        # Convert to base unit first
        if from_unit.category == "temperature":
            # Special handling for temperature (Celsius, Fahrenheit, Kelvin)
            base_value = self._convert_temperature_to_base(
                value, from_unit.abbreviation
            )
            converted_value = self._convert_temperature_from_base(
                base_value, to_unit.abbreviation
            )
            formula = self._get_temperature_formula(
                from_unit.abbreviation, to_unit.abbreviation
            )
        else:
            # Standard linear conversion
            base_value = value * float(from_unit.conversion_factor)
            converted_value = base_value / float(to_unit.conversion_factor)
            formula = (
                f"({value} {from_unit.abbreviation} × {from_unit.conversion_factor}) "
                f"÷ {to_unit.conversion_factor} = {converted_value:.{to_unit.decimal_places}f} {to_unit.abbreviation}"
            )
        
        return {
            "original_value": value,
            "converted_value": round(converted_value, to_unit.decimal_places),
            "from_unit": f"{from_unit.name} ({from_unit.abbreviation})",
            "to_unit": f"{to_unit.name} ({to_unit.abbreviation})",
            "formula": formula
        }
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """Get all unit categories with metadata"""
        from sqlalchemy import func
        
        categories = self.db.query(
            UnitOfMeasure.category,
            func.count(UnitOfMeasure.id).label('count')
        ).filter(
            UnitOfMeasure.is_active == True
        ).group_by(
            UnitOfMeasure.category
        ).all()
        
        category_info = {
            "quantity": {"name": "Quantity", "desc": "Basic counting units (pieces, boxes, dozen)"},
            "length": {"name": "Length/Distance", "desc": "Linear measurements (mm, m, km, inch, mile)"},
            "area": {"name": "Area", "desc": "Surface area (m², hectare, acre)"},
            "volume": {"name": "Volume", "desc": "Capacity measurements (ml, liter, gallon, m³)"},
            "weight": {"name": "Weight/Mass", "desc": "Mass measurements (mg, g, kg, lb, ton)"},
            "temperature": {"name": "Temperature", "desc": "Temperature (°C, °F, K)"},
            "pressure": {"name": "Pressure", "desc": "Pressure (Pa, bar, psi, atm)"},
            "speed": {"name": "Speed/Velocity", "desc": "Speed (m/s, km/h, mph, knot)"},
            "time": {"name": "Time", "desc": "Time duration (second, minute, hour, day)"},
            "angle": {"name": "Angle", "desc": "Angular measurement (degree, radian)"},
            "energy": {"name": "Energy", "desc": "Energy (joule, calorie, kWh)"},
            "power": {"name": "Power", "desc": "Power (watt, horsepower)"},
            "force": {"name": "Force", "desc": "Force (newton, pound-force)"},
            "frequency": {"name": "Frequency", "desc": "Frequency (hertz, rpm)"},
            "electric_current": {"name": "Electric Current", "desc": "Current (ampere)"},
            "voltage": {"name": "Voltage", "desc": "Voltage (volt)"},
            "resistance": {"name": "Resistance", "desc": "Resistance (ohm)"},
            "luminosity": {"name": "Luminosity", "desc": "Light intensity (candela, lumen, lux)"},
            "substance": {"name": "Amount of Substance", "desc": "Moles"},
            "nautical": {"name": "Nautical", "desc": "Maritime units (nautical mile, knot, fathom)"},
            "data": {"name": "Data Size", "desc": "Digital storage (byte, kilobyte, megabyte)"},
        }
        
        result = []
        for cat, count in categories:
            info = category_info.get(cat, {"name": cat.title(), "desc": ""})
            result.append({
                "category": cat,
                "display_name": info["name"],
                "description": info["desc"],
                "unit_count": count
            })
        
        return result
    
    def _serialize_unit(self, unit: UnitOfMeasure) -> Dict[str, Any]:
        """Serialize a unit to dict"""
        return {
            "id": unit.id,
            "name": unit.name,
            "abbreviation": unit.abbreviation,
            "symbol": unit.symbol,
            "category": unit.category,
            "subcategory": unit.subcategory,
            "description": unit.description,
            "is_base_unit": unit.is_base_unit,
            "base_unit_id": unit.base_unit_id,
            "base_unit_name": unit.base_unit.name if unit.base_unit else None,
            "base_unit_abbreviation": unit.base_unit.abbreviation if unit.base_unit else None,
            "conversion_factor": float(unit.conversion_factor),
            "conversion_offset": float(unit.conversion_offset),
            "is_system_unit": unit.is_system_unit,
            "is_active": unit.is_active,
            "display_order": unit.display_order,
            "decimal_places": unit.decimal_places,
            "usage_hint": unit.usage_hint,
            "branch_id": unit.branch_id,
            "created_at": unit.created_at.isoformat() if unit.created_at else None,
            "updated_at": unit.updated_at.isoformat() if unit.updated_at else None,
        }
    
    def _convert_temperature_to_base(self, value: float, from_unit: str) -> float:
        """Convert temperature to Celsius (base)"""
        if from_unit in ['C', '°C', 'celsius']:
            return value
        elif from_unit in ['F', '°F', 'fahrenheit']:
            return (value - 32) * 5/9
        elif from_unit in ['K', 'kelvin']:
            return value - 273.15
        else:
            raise ValueError(f"Unknown temperature unit: {from_unit}")
    
    def _convert_temperature_from_base(self, value: float, to_unit: str) -> float:
        """Convert temperature from Celsius (base)"""
        if to_unit in ['C', '°C', 'celsius']:
            return value
        elif to_unit in ['F', '°F', 'fahrenheit']:
            return (value * 9/5) + 32
        elif to_unit in ['K', 'kelvin']:
            return value + 273.15
        else:
            raise ValueError(f"Unknown temperature unit: {to_unit}")
    
    def _get_temperature_formula(self, from_unit: str, to_unit: str) -> str:
        """Get formula for temperature conversion"""
        formulas = {
            ('C', 'F'): "°F = (°C × 9/5) + 32",
            ('F', 'C'): "°C = (°F - 32) × 5/9",
            ('C', 'K'): "K = °C + 273.15",
            ('K', 'C'): "°C = K - 273.15",
            ('F', 'K'): "K = ((°F - 32) × 5/9) + 273.15",
            ('K', 'F'): "°F = ((K - 273.15) × 9/5) + 32",
        }
        
        key = (from_unit[0], to_unit[0])
        return formulas.get(key, f"{from_unit} → {to_unit}")
