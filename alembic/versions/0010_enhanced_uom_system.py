"""
Enhanced Unit of Measure System Migration

This migration:
1. Adds new columns to unit_of_measures table
2. Seeds comprehensive unit data for all categories
3. Sets up conversion factors for precise calculations

Revision ID: 0010_enhanced_uom_system
Revises: previous_revision
Create Date: 2025-10-14 22:50:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Boolean, Numeric, Integer, Text
import uuid
from datetime import datetime


# revision identifiers
revision = '0010_enhanced_uom_system'
down_revision = None  # Update this to your last migration
branch_labels = None
depends_on = None


def upgrade():
    """Add enhanced UOM columns and seed comprehensive unit data"""
    
    # Check if columns already exist before adding
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('unit_of_measures')]
    
    # Add new columns if they don't exist
    if 'symbol' not in existing_columns:
        op.add_column('unit_of_measures', sa.Column('symbol', sa.String(), nullable=True))
    
    if 'category' not in existing_columns:
        op.add_column('unit_of_measures', sa.Column('category', sa.String(), nullable=False, server_default='quantity'))
    
    if 'subcategory' not in existing_columns:
        op.add_column('unit_of_measures', sa.Column('subcategory', sa.String(), nullable=True))
    
    if 'conversion_offset' not in existing_columns:
        op.add_column('unit_of_measures', sa.Column('conversion_offset', sa.Numeric(20, 10), nullable=False, server_default='0.0'))
    
    if 'is_system_unit' not in existing_columns:
        op.add_column('unit_of_measures', sa.Column('is_system_unit', sa.Boolean(), nullable=False, server_default='true'))
    
    if 'is_active' not in existing_columns:
        op.add_column('unit_of_measures', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    
    if 'display_order' not in existing_columns:
        op.add_column('unit_of_measures', sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'))
    
    if 'decimal_places' not in existing_columns:
        op.add_column('unit_of_measures', sa.Column('decimal_places', sa.Integer(), nullable=False, server_default='2'))
    
    if 'usage_hint' not in existing_columns:
        op.add_column('unit_of_measures', sa.Column('usage_hint', sa.Text(), nullable=True))
    
    # Modify existing columns for better precision
    op.alter_column('unit_of_measures', 'conversion_factor',
                    type_=sa.Numeric(20, 10),
                    existing_type=sa.Numeric(10, 4),
                    nullable=False,
                    server_default='1.0')
    
    # Create the table reference for bulk insert
    uom_table = table('unit_of_measures',
        column('id', String),
        column('name', String),
        column('abbreviation', String),
        column('symbol', String),
        column('category', String),
        column('subcategory', String),
        column('description', Text),
        column('is_base_unit', Boolean),
        column('base_unit_id', String),
        column('conversion_factor', Numeric),
        column('conversion_offset', Numeric),
        column('is_system_unit', Boolean),
        column('is_active', Boolean),
        column('display_order', Integer),
        column('decimal_places', Integer),
        column('usage_hint', Text),
        column('branch_id', String),
        column('created_at', sa.DateTime),
        column('updated_at', sa.DateTime),
    )
    
    now = datetime.utcnow()
    
    # Comprehensive unit definitions
    # Each category has a base unit and derived units with conversion factors
    
    units_data = []
    
    # ============================================================================
    # QUANTITY (Basic counting units)
    # ============================================================================
    piece_id = str(uuid.uuid4())
    units_data.extend([
        {'id': piece_id, 'name': 'Piece', 'abbreviation': 'pc', 'symbol': 'pc', 'category': 'quantity', 'subcategory': 'metric', 'is_base_unit': True, 'conversion_factor': 1.0, 'display_order': 1, 'description': 'Single unit/item'},
        {'id': str(uuid.uuid4()), 'name': 'Dozen', 'abbreviation': 'doz', 'symbol': 'doz', 'category': 'quantity', 'subcategory': 'metric', 'base_unit_id': piece_id, 'conversion_factor': 12.0, 'display_order': 2, 'description': '12 pieces'},
        {'id': str(uuid.uuid4()), 'name': 'Gross', 'abbreviation': 'gr', 'symbol': 'gr', 'category': 'quantity', 'subcategory': 'metric', 'base_unit_id': piece_id, 'conversion_factor': 144.0, 'display_order': 3, 'description': '144 pieces (12 dozen)'},
        {'id': str(uuid.uuid4()), 'name': 'Pair', 'abbreviation': 'pr', 'symbol': 'pr', 'category': 'quantity', 'subcategory': 'metric', 'base_unit_id': piece_id, 'conversion_factor': 2.0, 'display_order': 4, 'description': '2 pieces'},
    ])
    
    # ============================================================================
    # LENGTH (Linear measurements)
    # ============================================================================
    meter_id = str(uuid.uuid4())
    units_data.extend([
        # Metric
        {'id': meter_id, 'name': 'Meter', 'abbreviation': 'm', 'symbol': 'm', 'category': 'length', 'subcategory': 'metric', 'is_base_unit': True, 'conversion_factor': 1.0, 'display_order': 10, 'description': 'SI base unit of length', 'decimal_places': 3},
        {'id': str(uuid.uuid4()), 'name': 'Millimeter', 'abbreviation': 'mm', 'symbol': 'mm', 'category': 'length', 'subcategory': 'metric', 'base_unit_id': meter_id, 'conversion_factor': 0.001, 'display_order': 7, 'description': 'Precision measurement', 'decimal_places': 4, 'usage_hint': 'Used for precision machining and manufacturing'},
        {'id': str(uuid.uuid4()), 'name': 'Centimeter', 'abbreviation': 'cm', 'symbol': 'cm', 'category': 'length', 'subcategory': 'metric', 'base_unit_id': meter_id, 'conversion_factor': 0.01, 'display_order': 8, 'description': 'Small measurements'},
        {'id': str(uuid.uuid4()), 'name': 'Decimeter', 'abbreviation': 'dm', 'symbol': 'dm', 'category': 'length', 'subcategory': 'metric', 'base_unit_id': meter_id, 'conversion_factor': 0.1, 'display_order': 9, 'description': '1/10 of a meter'},
        {'id': str(uuid.uuid4()), 'name': 'Kilometer', 'abbreviation': 'km', 'symbol': 'km', 'category': 'length', 'subcategory': 'metric', 'base_unit_id': meter_id, 'conversion_factor': 1000.0, 'display_order': 11, 'description': 'Long distances'},
        {'id': str(uuid.uuid4()), 'name': 'Micrometer', 'abbreviation': 'µm', 'symbol': 'μm', 'category': 'length', 'subcategory': 'metric', 'base_unit_id': meter_id, 'conversion_factor': 0.000001, 'display_order': 6, 'description': 'Microscopic measurements', 'decimal_places': 6},
        {'id': str(uuid.uuid4()), 'name': 'Nanometer', 'abbreviation': 'nm', 'symbol': 'nm', 'category': 'length', 'subcategory': 'scientific', 'base_unit_id': meter_id, 'conversion_factor': 0.000000001, 'display_order': 5, 'description': 'Molecular scale', 'decimal_places': 9},
        # Imperial
        {'id': str(uuid.uuid4()), 'name': 'Inch', 'abbreviation': 'in', 'symbol': '"', 'category': 'length', 'subcategory': 'imperial', 'base_unit_id': meter_id, 'conversion_factor': 0.0254, 'display_order': 20, 'description': '1/12 of a foot'},
        {'id': str(uuid.uuid4()), 'name': 'Foot', 'abbreviation': 'ft', 'symbol': "'", 'category': 'length', 'subcategory': 'imperial', 'base_unit_id': meter_id, 'conversion_factor': 0.3048, 'display_order': 21, 'description': '12 inches'},
        {'id': str(uuid.uuid4()), 'name': 'Yard', 'abbreviation': 'yd', 'symbol': 'yd', 'category': 'length', 'subcategory': 'imperial', 'base_unit_id': meter_id, 'conversion_factor': 0.9144, 'display_order': 22, 'description': '3 feet'},
        {'id': str(uuid.uuid4()), 'name': 'Mile', 'abbreviation': 'mi', 'symbol': 'mi', 'category': 'length', 'subcategory': 'imperial', 'base_unit_id': meter_id, 'conversion_factor': 1609.34, 'display_order': 23, 'description': '5280 feet'},
    ])
    
    # ============================================================================
    # AREA (Surface measurements)
    # ============================================================================
    sq_meter_id = str(uuid.uuid4())
    units_data.extend([
        {'id': sq_meter_id, 'name': 'Square Meter', 'abbreviation': 'm²', 'symbol': 'm²', 'category': 'area', 'subcategory': 'metric', 'is_base_unit': True, 'conversion_factor': 1.0, 'display_order': 30, 'description': 'SI unit of area'},
        {'id': str(uuid.uuid4()), 'name': 'Square Millimeter', 'abbreviation': 'mm²', 'symbol': 'mm²', 'category': 'area', 'subcategory': 'metric', 'base_unit_id': sq_meter_id, 'conversion_factor': 0.000001, 'display_order': 28, 'decimal_places': 6},
        {'id': str(uuid.uuid4()), 'name': 'Square Centimeter', 'abbreviation': 'cm²', 'symbol': 'cm²', 'category': 'area', 'subcategory': 'metric', 'base_unit_id': sq_meter_id, 'conversion_factor': 0.0001, 'display_order': 29},
        {'id': str(uuid.uuid4()), 'name': 'Hectare', 'abbreviation': 'ha', 'symbol': 'ha', 'category': 'area', 'subcategory': 'metric', 'base_unit_id': sq_meter_id, 'conversion_factor': 10000.0, 'display_order': 31, 'description': '10,000 m²'},
        {'id': str(uuid.uuid4()), 'name': 'Square Kilometer', 'abbreviation': 'km²', 'symbol': 'km²', 'category': 'area', 'subcategory': 'metric', 'base_unit_id': sq_meter_id, 'conversion_factor': 1000000.0, 'display_order': 32},
        {'id': str(uuid.uuid4()), 'name': 'Square Inch', 'abbreviation': 'in²', 'symbol': 'in²', 'category': 'area', 'subcategory': 'imperial', 'base_unit_id': sq_meter_id, 'conversion_factor': 0.00064516, 'display_order': 40},
        {'id': str(uuid.uuid4()), 'name': 'Square Foot', 'abbreviation': 'ft²', 'symbol': 'ft²', 'category': 'area', 'subcategory': 'imperial', 'base_unit_id': sq_meter_id, 'conversion_factor': 0.092903, 'display_order': 41},
        {'id': str(uuid.uuid4()), 'name': 'Acre', 'abbreviation': 'ac', 'symbol': 'ac', 'category': 'area', 'subcategory': 'imperial', 'base_unit_id': sq_meter_id, 'conversion_factor': 4046.86, 'display_order': 42, 'description': '43,560 ft²'},
    ])
    
    # ============================================================================
    # VOLUME (Capacity measurements)
    # ============================================================================
    liter_id = str(uuid.uuid4())
    units_data.extend([
        {'id': liter_id, 'name': 'Liter', 'abbreviation': 'L', 'symbol': 'L', 'category': 'volume', 'subcategory': 'metric', 'is_base_unit': True, 'conversion_factor': 1.0, 'display_order': 50, 'description': 'Metric volume unit'},
        {'id': str(uuid.uuid4()), 'name': 'Milliliter', 'abbreviation': 'mL', 'symbol': 'mL', 'category': 'volume', 'subcategory': 'metric', 'base_unit_id': liter_id, 'conversion_factor': 0.001, 'display_order': 48, 'description': 'Small volumes', 'decimal_places': 3},
        {'id': str(uuid.uuid4()), 'name': 'Centiliter', 'abbreviation': 'cL', 'symbol': 'cL', 'category': 'volume', 'subcategory': 'metric', 'base_unit_id': liter_id, 'conversion_factor': 0.01, 'display_order': 49},
        {'id': str(uuid.uuid4()), 'name': 'Cubic Meter', 'abbreviation': 'm³', 'symbol': 'm³', 'category': 'volume', 'subcategory': 'metric', 'base_unit_id': liter_id, 'conversion_factor': 1000.0, 'display_order': 51, 'description': '1000 liters'},
        {'id': str(uuid.uuid4()), 'name': 'Gallon (US)', 'abbreviation': 'gal', 'symbol': 'gal', 'category': 'volume', 'subcategory': 'us_customary', 'base_unit_id': liter_id, 'conversion_factor': 3.78541, 'display_order': 60},
        {'id': str(uuid.uuid4()), 'name': 'Gallon (UK)', 'abbreviation': 'gal UK', 'symbol': 'gal UK', 'category': 'volume', 'subcategory': 'imperial', 'base_unit_id': liter_id, 'conversion_factor': 4.54609, 'display_order': 61},
        {'id': str(uuid.uuid4()), 'name': 'Fluid Ounce (US)', 'abbreviation': 'fl oz', 'symbol': 'fl oz', 'category': 'volume', 'subcategory': 'us_customary', 'base_unit_id': liter_id, 'conversion_factor': 0.0295735, 'display_order': 62},
        {'id': str(uuid.uuid4()), 'name': 'Pint (US)', 'abbreviation': 'pt', 'symbol': 'pt', 'category': 'volume', 'subcategory': 'us_customary', 'base_unit_id': liter_id, 'conversion_factor': 0.473176, 'display_order': 63},
        {'id': str(uuid.uuid4()), 'name': 'Quart (US)', 'abbreviation': 'qt', 'symbol': 'qt', 'category': 'volume', 'subcategory': 'us_customary', 'base_unit_id': liter_id, 'conversion_factor': 0.946353, 'display_order': 64},
    ])
    
    # ============================================================================
    # WEIGHT/MASS
    # ============================================================================
    kilogram_id = str(uuid.uuid4())
    units_data.extend([
        {'id': kilogram_id, 'name': 'Kilogram', 'abbreviation': 'kg', 'symbol': 'kg', 'category': 'weight', 'subcategory': 'metric', 'is_base_unit': True, 'conversion_factor': 1.0, 'display_order': 70, 'description': 'SI base unit of mass'},
        {'id': str(uuid.uuid4()), 'name': 'Milligram', 'abbreviation': 'mg', 'symbol': 'mg', 'category': 'weight', 'subcategory': 'metric', 'base_unit_id': kilogram_id, 'conversion_factor': 0.000001, 'display_order': 67, 'decimal_places': 6, 'usage_hint': 'Used for pharmaceuticals and precision'},
        {'id': str(uuid.uuid4()), 'name': 'Gram', 'abbreviation': 'g', 'symbol': 'g', 'category': 'weight', 'subcategory': 'metric', 'base_unit_id': kilogram_id, 'conversion_factor': 0.001, 'display_order': 68, 'decimal_places': 3},
        {'id': str(uuid.uuid4()), 'name': 'Metric Ton', 'abbreviation': 't', 'symbol': 't', 'category': 'weight', 'subcategory': 'metric', 'base_unit_id': kilogram_id, 'conversion_factor': 1000.0, 'display_order': 71, 'description': '1000 kg'},
        {'id': str(uuid.uuid4()), 'name': 'Ounce', 'abbreviation': 'oz', 'symbol': 'oz', 'category': 'weight', 'subcategory': 'imperial', 'base_unit_id': kilogram_id, 'conversion_factor': 0.0283495, 'display_order': 80},
        {'id': str(uuid.uuid4()), 'name': 'Pound', 'abbreviation': 'lb', 'symbol': 'lb', 'category': 'weight', 'subcategory': 'imperial', 'base_unit_id': kilogram_id, 'conversion_factor': 0.453592, 'display_order': 81},
        {'id': str(uuid.uuid4()), 'name': 'Ton (US)', 'abbreviation': 'ton', 'symbol': 'ton', 'category': 'weight', 'subcategory': 'us_customary', 'base_unit_id': kilogram_id, 'conversion_factor': 907.185, 'display_order': 82, 'description': '2000 pounds'},
    ])
    
    # ============================================================================
    # TEMPERATURE (Special: uses offset conversions)
    # ============================================================================
    celsius_id = str(uuid.uuid4())
    units_data.extend([
        {'id': celsius_id, 'name': 'Celsius', 'abbreviation': '°C', 'symbol': '°C', 'category': 'temperature', 'subcategory': 'metric', 'is_base_unit': True, 'conversion_factor': 1.0, 'conversion_offset': 0.0, 'display_order': 90},
        {'id': str(uuid.uuid4()), 'name': 'Fahrenheit', 'abbreviation': '°F', 'symbol': '°F', 'category': 'temperature', 'subcategory': 'imperial', 'base_unit_id': celsius_id, 'conversion_factor': 1.8, 'conversion_offset': 32.0, 'display_order': 91, 'usage_hint': 'Use custom conversion: (°C × 9/5) + 32'},
        {'id': str(uuid.uuid4()), 'name': 'Kelvin', 'abbreviation': 'K', 'symbol': 'K', 'category': 'temperature', 'subcategory': 'scientific', 'base_unit_id': celsius_id, 'conversion_factor': 1.0, 'conversion_offset': 273.15, 'display_order': 92, 'usage_hint': 'K = °C + 273.15'},
    ])
    
    # ============================================================================
    # PRESSURE
    # ============================================================================
    pascal_id = str(uuid.uuid4())
    units_data.extend([
        {'id': pascal_id, 'name': 'Pascal', 'abbreviation': 'Pa', 'symbol': 'Pa', 'category': 'pressure', 'subcategory': 'metric', 'is_base_unit': True, 'conversion_factor': 1.0, 'display_order': 100, 'description': 'SI unit of pressure'},
        {'id': str(uuid.uuid4()), 'name': 'Kilopascal', 'abbreviation': 'kPa', 'symbol': 'kPa', 'category': 'pressure', 'subcategory': 'metric', 'base_unit_id': pascal_id, 'conversion_factor': 1000.0, 'display_order': 101},
        {'id': str(uuid.uuid4()), 'name': 'Bar', 'abbreviation': 'bar', 'symbol': 'bar', 'category': 'pressure', 'subcategory': 'metric', 'base_unit_id': pascal_id, 'conversion_factor': 100000.0, 'display_order': 102},
        {'id': str(uuid.uuid4()), 'name': 'Atmosphere', 'abbreviation': 'atm', 'symbol': 'atm', 'category': 'pressure', 'subcategory': 'scientific', 'base_unit_id': pascal_id, 'conversion_factor': 101325.0, 'display_order': 103, 'description': 'Standard atmospheric pressure'},
        {'id': str(uuid.uuid4()), 'name': 'PSI', 'abbreviation': 'psi', 'symbol': 'psi', 'category': 'pressure', 'subcategory': 'imperial', 'base_unit_id': pascal_id, 'conversion_factor': 6894.76, 'display_order': 110, 'description': 'Pounds per square inch'},
        {'id': str(uuid.uuid4()), 'name': 'Torr', 'abbreviation': 'Torr', 'symbol': 'Torr', 'category': 'pressure', 'subcategory': 'scientific', 'base_unit_id': pascal_id, 'conversion_factor': 133.322, 'display_order': 104},
    ])
    
    # ============================================================================
    # SPEED/VELOCITY
    # ============================================================================
    mps_id = str(uuid.uuid4())
    units_data.extend([
        {'id': mps_id, 'name': 'Meters per Second', 'abbreviation': 'm/s', 'symbol': 'm/s', 'category': 'speed', 'subcategory': 'metric', 'is_base_unit': True, 'conversion_factor': 1.0, 'display_order': 120},
        {'id': str(uuid.uuid4()), 'name': 'Kilometers per Hour', 'abbreviation': 'km/h', 'symbol': 'km/h', 'category': 'speed', 'subcategory': 'metric', 'base_unit_id': mps_id, 'conversion_factor': 0.277778, 'display_order': 121},
        {'id': str(uuid.uuid4()), 'name': 'Miles per Hour', 'abbreviation': 'mph', 'symbol': 'mph', 'category': 'speed', 'subcategory': 'imperial', 'base_unit_id': mps_id, 'conversion_factor': 0.44704, 'display_order': 130},
        {'id': str(uuid.uuid4()), 'name': 'Knot', 'abbreviation': 'kn', 'symbol': 'kn', 'category': 'speed', 'subcategory': 'nautical', 'base_unit_id': mps_id, 'conversion_factor': 0.514444, 'display_order': 140, 'description': 'Nautical miles per hour'},
    ])
    
    # ============================================================================
    # TIME
    # ============================================================================
    second_id = str(uuid.uuid4())
    units_data.extend([
        {'id': second_id, 'name': 'Second', 'abbreviation': 's', 'symbol': 's', 'category': 'time', 'subcategory': 'metric', 'is_base_unit': True, 'conversion_factor': 1.0, 'display_order': 150, 'description': 'SI base unit of time'},
        {'id': str(uuid.uuid4()), 'name': 'Millisecond', 'abbreviation': 'ms', 'symbol': 'ms', 'category': 'time', 'subcategory': 'metric', 'base_unit_id': second_id, 'conversion_factor': 0.001, 'display_order': 149, 'decimal_places': 3},
        {'id': str(uuid.uuid4()), 'name': 'Minute', 'abbreviation': 'min', 'symbol': 'min', 'category': 'time', 'subcategory': 'metric', 'base_unit_id': second_id, 'conversion_factor': 60.0, 'display_order': 151},
        {'id': str(uuid.uuid4()), 'name': 'Hour', 'abbreviation': 'hr', 'symbol': 'hr', 'category': 'time', 'subcategory': 'metric', 'base_unit_id': second_id, 'conversion_factor': 3600.0, 'display_order': 152},
        {'id': str(uuid.uuid4()), 'name': 'Day', 'abbreviation': 'day', 'symbol': 'day', 'category': 'time', 'subcategory': 'metric', 'base_unit_id': second_id, 'conversion_factor': 86400.0, 'display_order': 153},
    ])
    
    # ============================================================================
    # ANGLE
    # ============================================================================
    radian_id = str(uuid.uuid4())
    units_data.extend([
        {'id': radian_id, 'name': 'Radian', 'abbreviation': 'rad', 'symbol': 'rad', 'category': 'angle', 'subcategory': 'scientific', 'is_base_unit': True, 'conversion_factor': 1.0, 'display_order': 160},
        {'id': str(uuid.uuid4()), 'name': 'Degree', 'abbreviation': '°', 'symbol': '°', 'category': 'angle', 'subcategory': 'metric', 'base_unit_id': radian_id, 'conversion_factor': 0.0174533, 'display_order': 161, 'description': 'π/180 radians'},
    ])
    
    # ============================================================================
    # NAUTICAL (Maritime/Aviation)
    # ============================================================================
    nm_id = str(uuid.uuid4())
    units_data.extend([
        {'id': nm_id, 'name': 'Nautical Mile', 'abbreviation': 'NM', 'symbol': 'NM', 'category': 'nautical', 'subcategory': 'nautical', 'is_base_unit': True, 'conversion_factor': 1.0, 'display_order': 170, 'description': '1852 meters'},
        {'id': str(uuid.uuid4()), 'name': 'Fathom', 'abbreviation': 'ftm', 'symbol': 'ftm', 'category': 'nautical', 'subcategory': 'nautical', 'base_unit_id': nm_id, 'conversion_factor': 0.000987473, 'display_order': 171, 'description': '6 feet depth measurement'},
    ])
    
    # ============================================================================
    # ENERGY
    # ============================================================================
    joule_id = str(uuid.uuid4())
    units_data.extend([
        {'id': joule_id, 'name': 'Joule', 'abbreviation': 'J', 'symbol': 'J', 'category': 'energy', 'subcategory': 'metric', 'is_base_unit': True, 'conversion_factor': 1.0, 'display_order': 180},
        {'id': str(uuid.uuid4()), 'name': 'Kilojoule', 'abbreviation': 'kJ', 'symbol': 'kJ', 'category': 'energy', 'subcategory': 'metric', 'base_unit_id': joule_id, 'conversion_factor': 1000.0, 'display_order': 181},
        {'id': str(uuid.uuid4()), 'name': 'Calorie', 'abbreviation': 'cal', 'symbol': 'cal', 'category': 'energy', 'subcategory': 'scientific', 'base_unit_id': joule_id, 'conversion_factor': 4.184, 'display_order': 182},
        {'id': str(uuid.uuid4()), 'name': 'Kilowatt-hour', 'abbreviation': 'kWh', 'symbol': 'kWh', 'category': 'energy', 'subcategory': 'metric', 'base_unit_id': joule_id, 'conversion_factor': 3600000.0, 'display_order': 183},
    ])
    
    # ============================================================================
    # POWER
    # ============================================================================
    watt_id = str(uuid.uuid4())
    units_data.extend([
        {'id': watt_id, 'name': 'Watt', 'abbreviation': 'W', 'symbol': 'W', 'category': 'power', 'subcategory': 'metric', 'is_base_unit': True, 'conversion_factor': 1.0, 'display_order': 190},
        {'id': str(uuid.uuid4()), 'name': 'Kilowatt', 'abbreviation': 'kW', 'symbol': 'kW', 'category': 'power', 'subcategory': 'metric', 'base_unit_id': watt_id, 'conversion_factor': 1000.0, 'display_order': 191},
        {'id': str(uuid.uuid4()), 'name': 'Horsepower', 'abbreviation': 'hp', 'symbol': 'hp', 'category': 'power', 'subcategory': 'imperial', 'base_unit_id': watt_id, 'conversion_factor': 745.7, 'display_order': 200},
    ])
    
    # Add common defaults to all units
    for unit in units_data:
        unit.setdefault('conversion_offset', 0.0)
        unit.setdefault('is_system_unit', True)
        unit.setdefault('is_active', True)
        unit.setdefault('decimal_places', 2)
        unit.setdefault('branch_id', None)
        unit.setdefault('created_at', now)
        unit.setdefault('updated_at', now)
    
    # Bulk insert all units
    op.bulk_insert(uom_table, units_data)
    
    print(f"✅ Successfully seeded {len(units_data)} units of measure across {len(set(u['category'] for u in units_data))} categories")


def downgrade():
    """Remove enhanced UOM columns"""
    op.drop_column('unit_of_measures', 'usage_hint')
    op.drop_column('unit_of_measures', 'decimal_places')
    op.drop_column('unit_of_measures', 'display_order')
    op.drop_column('unit_of_measures', 'is_active')
    op.drop_column('unit_of_measures', 'is_system_unit')
    op.drop_column('unit_of_measures', 'conversion_offset')
    op.drop_column('unit_of_measures', 'subcategory')
    op.drop_column('unit_of_measures', 'category')
    op.drop_column('unit_of_measures', 'symbol')
    
    # Revert conversion_factor precision
    op.alter_column('unit_of_measures', 'conversion_factor',
                    type_=sa.Numeric(10, 4),
                    existing_type=sa.Numeric(20, 10))
