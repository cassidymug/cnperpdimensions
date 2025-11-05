import uuid
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Column, String, Boolean, Text, Date, ForeignKey, Numeric, Integer, DateTime, JSON, Enum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from enum import Enum as PyEnum


class AssetCategory(PyEnum):
    VEHICLE = "VEHICLE"
    EQUIPMENT = "EQUIPMENT"
    FURNITURE = "FURNITURE"
    BUILDING = "BUILDING"
    LAND = "LAND"
    SOFTWARE = "SOFTWARE"
    INTANGIBLE = "INTANGIBLE"
    MACHINERY = "MACHINERY"
    COMPUTER = "COMPUTER"
    OFFICE_EQUIPMENT = "OFFICE_EQUIPMENT"
    INVENTORY = "INVENTORY"
    OTHER = "OTHER"


class AssetStatus(PyEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SOLD = "SOLD"
    DISPOSED = "DISPOSED"
    UNDER_MAINTENANCE = "UNDER_MAINTENANCE"
    LOST = "LOST"
    STOLEN = "STOLEN"


class DepreciationMethod(PyEnum):
    STRAIGHT_LINE = "straight_line"
    DECLINING_BALANCE = "declining_balance"
    SUM_OF_YEARS = "sum_of_years"
    UNITS_OF_PRODUCTION = "units_of_production"
    NONE = "none"


class IFRSCategory(PyEnum):
    PPE_IAS_16 = "PPE_IAS_16"  # Property, Plant and Equipment
    INVESTMENT_PROPERTY_IAS_40 = "INVESTMENT_PROPERTY_IAS_40"
    INVENTORY_IAS_2 = "INVENTORY_IAS_2"
    INTANGIBLE_ASSET_IAS_38 = "INTANGIBLE_ASSET_IAS_38"
    FINANCIAL_INSTRUMENT_IFRS_9 = "FINANCIAL_INSTRUMENT_IFRS_9"
    ASSET_HELD_FOR_SALE_IFRS_5 = "ASSET_HELD_FOR_SALE_IFRS_5"
    LEASE_ASSET_IFRS_16 = "LEASE_ASSET_IFRS_16"


class Asset(BaseModel):
    """Asset management model"""
    __tablename__ = "assets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Basic Information
    asset_code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(Enum(AssetCategory), nullable=False)
    status = Column(Enum(AssetStatus), default=AssetStatus.ACTIVE, nullable=False)
    ifrs_category = Column(Enum(IFRSCategory), nullable=True)

    # Location and Assignment
    location = Column(String(200))
    assigned_to = Column(String(36), ForeignKey("users.id"))
    assigned_department = Column(String(100))
    branch_id = Column(String(36), ForeignKey("branches.id"))

    # Financial Information
    purchase_date = Column(Date, nullable=False)
    purchase_cost = Column(Numeric(15, 2), nullable=False)
    current_value = Column(Numeric(15, 2), nullable=False)
    salvage_value = Column(Numeric(15, 2), default=0.0)
    accumulated_depreciation = Column(Numeric(15, 2), default=0.0)

    # Depreciation Settings
    # Use enum values (lowercase) to match existing PostgreSQL enum labels
    depreciation_method = Column(
        Enum(
            DepreciationMethod,
            values_callable=lambda e: [m.value for m in e],
            name="depreciationmethod",
        ),
        default=DepreciationMethod.STRAIGHT_LINE,
    )
    useful_life_years = Column(Integer, default=5)
    depreciation_rate = Column(Numeric(5, 2))  # Annual depreciation rate as percentage

    # Serial Numbers and Identifiers
    serial_number = Column(String(100), index=True)
    model_number = Column(String(100))
    manufacturer = Column(String(100))
    warranty_expiry = Column(Date)

    # Vehicle Specific Fields
    vehicle_registration = Column(String(50))
    engine_number = Column(String(50))
    chassis_number = Column(String(50))
    vehicle_make = Column(String(100))
    vehicle_model = Column(String(100))
    vehicle_year = Column(Integer)
    vehicle_color = Column(String(50))
    fuel_type = Column(String(50))
    transmission_type = Column(String(50))
    mileage = Column(Integer)
    last_service_date = Column(Date)
    next_service_date = Column(Date)
    insurance_expiry = Column(Date)
    license_expiry = Column(Date)

    # Inventory Specific Fields
    inventory_item_id = Column(String(36), ForeignKey("products.id"))
    inventory_quantity = Column(Integer, default=1)

    # Accounting Integration
    accounting_code_id = Column(String(36), ForeignKey("accounting_codes.id"))

    # Accounting Dimensions - for GL posting and dimensional asset tracking
    cost_center_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True, index=True)
    project_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)
    department_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)

    # Additional Details
    supplier_id = Column(String(36), ForeignKey("suppliers.id"))
    warranty_details = Column(Text)
    maintenance_schedule = Column(Text)
    notes = Column(Text)

    # Metadata
    tags = Column(JSON, default=list)
    custom_fields = Column(JSON, default=dict)

    # Relationships
    assigned_user = relationship("User", foreign_keys=[assigned_to])
    branch = relationship("Branch")
    accounting_code = relationship("AccountingCode")
    supplier = relationship("Supplier")
    inventory_item = relationship("Product", foreign_keys=[inventory_item_id])

    # Accounting dimension relationships
    cost_center = relationship("AccountingDimensionValue", foreign_keys=[cost_center_id])
    project = relationship("AccountingDimensionValue", foreign_keys=[project_id])
    department = relationship("AccountingDimensionValue", foreign_keys=[department_id])

    maintenance_records = relationship("AssetMaintenance", back_populates="asset")
    depreciation_records = relationship("AssetDepreciation", back_populates="asset")
    images = relationship("AssetImage", back_populates="asset")

    def calculate_depreciation(self, as_of_date: date = None) -> dict:
        """Calculate depreciation for the asset"""
        if as_of_date is None:
            as_of_date = date.today()

        if self.depreciation_method == DepreciationMethod.NONE:
            return {
                'depreciation_amount': 0.0,
                'accumulated_depreciation': float(self.accumulated_depreciation) if self.accumulated_depreciation else 0.0,
                'book_value': float(self.current_value) if self.current_value else 0.0
            }

        # Calculate years since purchase
        years_held = Decimal(str((as_of_date - self.purchase_date).days / 365.25))

        if years_held <= 0:
            return {
                'depreciation_amount': 0.0,
                'accumulated_depreciation': float(self.accumulated_depreciation) if self.accumulated_depreciation else 0.0,
                'book_value': float(self.current_value) if self.current_value else 0.0
            }

        # Ensure all values are Decimal for calculations
        purchase_cost = Decimal(str(self.purchase_cost)) if self.purchase_cost else Decimal('0')
        salvage_value = Decimal(str(self.salvage_value)) if self.salvage_value else Decimal('0')
        accumulated_depreciation = Decimal(str(self.accumulated_depreciation)) if self.accumulated_depreciation else Decimal('0')

        if self.depreciation_method == DepreciationMethod.STRAIGHT_LINE:
            annual_depreciation = (purchase_cost - salvage_value) / Decimal(str(self.useful_life_years))
            total_depreciation = min(annual_depreciation * years_held, purchase_cost - salvage_value)

        elif self.depreciation_method == DepreciationMethod.DECLINING_BALANCE:
            if not self.depreciation_rate:
                self.depreciation_rate = Decimal('200') / Decimal(str(self.useful_life_years))  # Double declining balance

            depreciation_rate = Decimal(str(self.depreciation_rate))
            book_value = purchase_cost
            total_depreciation = Decimal('0')

            for year in range(int(years_held) + 1):
                if year == 0:
                    continue

                depreciation_amount = book_value * (depreciation_rate / Decimal('100'))
                book_value = max(book_value - depreciation_amount, salvage_value)
                total_depreciation += depreciation_amount

                if book_value <= salvage_value:
                    break

        else:
            # Default to straight line
            annual_depreciation = (purchase_cost - salvage_value) / Decimal(str(self.useful_life_years))
            total_depreciation = min(annual_depreciation * years_held, purchase_cost - salvage_value)

        book_value = max(purchase_cost - total_depreciation, salvage_value)

        return {
            'depreciation_amount': float(total_depreciation - accumulated_depreciation),
            'accumulated_depreciation': float(total_depreciation),
            'book_value': float(book_value)
        }

    def to_dict(self) -> dict:
        """Convert asset to dictionary"""
        return {
            'id': self.id,
            'asset_code': self.asset_code,
            'name': self.name,
            'description': self.description,
            'category': self.category.value if self.category else None,
            'status': self.status.value if self.status else None,
            'ifrs_category': self.ifrs_category.value if self.ifrs_category else None,
            'location': self.location,
            'assigned_to': self.assigned_to,
            'assigned_department': self.assigned_department,
            'branch_id': self.branch_id,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'purchase_cost': float(self.purchase_cost) if self.purchase_cost else 0.0,
            'current_value': float(self.current_value) if self.current_value else 0.0,
            'salvage_value': float(self.salvage_value) if self.salvage_value else 0.0,
            'accumulated_depreciation': float(self.accumulated_depreciation) if self.accumulated_depreciation else 0.0,
            'depreciation_method': self.depreciation_method.value if self.depreciation_method else None,
            'useful_life_years': self.useful_life_years,
            'depreciation_rate': float(self.depreciation_rate) if self.depreciation_rate else None,
            'serial_number': self.serial_number,
            'model_number': self.model_number,
            'manufacturer': self.manufacturer,
            'warranty_expiry': self.warranty_expiry.isoformat() if self.warranty_expiry else None,
            'vehicle_registration': self.vehicle_registration,
            'engine_number': self.engine_number,
            'chassis_number': self.chassis_number,
            'vehicle_make': self.vehicle_make,
            'vehicle_model': self.vehicle_model,
            'vehicle_year': self.vehicle_year,
            'vehicle_color': self.vehicle_color,
            'fuel_type': self.fuel_type,
            'transmission_type': self.transmission_type,
            'mileage': self.mileage,
            'last_service_date': self.last_service_date.isoformat() if self.last_service_date else None,
            'next_service_date': self.next_service_date.isoformat() if self.next_service_date else None,
            'insurance_expiry': self.insurance_expiry.isoformat() if self.insurance_expiry else None,
            'license_expiry': self.license_expiry.isoformat() if self.license_expiry else None,
            'inventory_item_id': self.inventory_item_id,
            'inventory_quantity': self.inventory_quantity,
            'accounting_code_id': self.accounting_code_id,

            # Accounting dimensions
            'cost_center_id': self.cost_center_id,
            'project_id': self.project_id,
            'department_id': self.department_id,

            'supplier_id': self.supplier_id,
            'warranty_details': self.warranty_details,
            'maintenance_schedule': self.maintenance_schedule,
            'notes': self.notes,
            'tags': self.tags or [],
            'custom_fields': self.custom_fields or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class AssetMaintenance(BaseModel):
    """Asset maintenance records"""
    __tablename__ = "asset_maintenance"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    asset_id = Column(String(36), ForeignKey("assets.id"), nullable=False)
    maintenance_type = Column(String(50), nullable=False)  # preventive, corrective, emergency
    description = Column(Text, nullable=False)
    maintenance_date = Column(Date, nullable=False)
    next_maintenance_date = Column(Date)

    # Cost and Service Details
    cost = Column(Numeric(15, 2), default=0.0)
    service_provider = Column(String(200))
    service_provider_contact = Column(String(100))

    # Technical Details
    parts_replaced = Column(Text)
    work_performed = Column(Text)
    technician_notes = Column(Text)

    # Status
    status = Column(String(50), default="completed")  # scheduled, in_progress, completed, cancelled

    # Relationships
    asset = relationship("Asset", back_populates="maintenance_records")

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'maintenance_type': self.maintenance_type,
            'description': self.description,
            'maintenance_date': self.maintenance_date.isoformat() if self.maintenance_date else None,
            'next_maintenance_date': self.next_maintenance_date.isoformat() if self.next_maintenance_date else None,
            'cost': float(self.cost) if self.cost else 0.0,
            'service_provider': self.service_provider,
            'service_provider_contact': self.service_provider_contact,
            'parts_replaced': self.parts_replaced,
            'work_performed': self.work_performed,
            'technician_notes': self.technician_notes,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class AssetDepreciation(BaseModel):
    """Asset depreciation records"""
    __tablename__ = "asset_depreciation"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    asset_id = Column(String(36), ForeignKey("assets.id"), nullable=False)
    depreciation_date = Column(Date, nullable=False)
    depreciation_amount = Column(Numeric(15, 2), nullable=False)
    accumulated_depreciation = Column(Numeric(15, 2), nullable=False)
    book_value = Column(Numeric(15, 2), nullable=False)

    # Accounting Integration
    journal_entry_id = Column(String(36), ForeignKey("accounting_entries.id"))

    # Relationships
    asset = relationship("Asset", back_populates="depreciation_records")
    journal_entry = relationship("AccountingEntry")

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'depreciation_date': self.depreciation_date.isoformat() if self.depreciation_date else None,
            'depreciation_amount': float(self.depreciation_amount) if self.depreciation_amount else 0.0,
            'accumulated_depreciation': float(self.accumulated_depreciation) if self.accumulated_depreciation else 0.0,
            'book_value': float(self.book_value) if self.book_value else 0.0,
            'journal_entry_id': self.journal_entry_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class AssetImage(BaseModel):
    """Asset images"""
    __tablename__ = "asset_images"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    asset_id = Column(String(36), ForeignKey("assets.id"), nullable=False)
    image_url = Column(String(500), nullable=False)
    image_type = Column(String(50), default="main")  # main, thumbnail, document
    description = Column(String(200))
    file_size = Column(Integer)
    mime_type = Column(String(100))

    # Relationships
    asset = relationship("Asset", back_populates="images")

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'asset_id': self.asset_id,
            'image_url': self.image_url,
            'image_type': self.image_type,
            'description': self.description,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class AssetCategoryConfig(BaseModel):
    """Asset category configuration"""
    __tablename__ = "asset_category_configs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    category = Column(Enum(AssetCategory), nullable=False, unique=True)
    # Use enum values (lowercase) to match existing PostgreSQL enum labels
    default_depreciation_method = Column(
        Enum(
            DepreciationMethod,
            values_callable=lambda e: [m.value for m in e],
            name="depreciationmethod",
        ),
        default=DepreciationMethod.STRAIGHT_LINE,
    )
    default_useful_life_years = Column(Integer, default=5)
    default_depreciation_rate = Column(Numeric(5, 2))
    default_salvage_value_percentage = Column(Numeric(5, 2), default=10.0)  # 10% of purchase cost

    # Custom fields for this category
    custom_fields_schema = Column(JSON, default=dict)

    # Maintenance settings
    maintenance_required = Column(Boolean, default=False)
    maintenance_interval_months = Column(Integer, default=12)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'category': self.category.value if self.category else None,
            'default_depreciation_method': self.default_depreciation_method.value if self.default_depreciation_method else None,
            'default_useful_life_years': self.default_useful_life_years,
            'default_depreciation_rate': float(self.default_depreciation_rate) if self.default_depreciation_rate else None,
            'default_salvage_value_percentage': float(self.default_salvage_value_percentage) if self.default_salvage_value_percentage else None,
            'custom_fields_schema': self.custom_fields_schema or {},
            'maintenance_required': self.maintenance_required,
            'maintenance_interval_months': self.maintenance_interval_months,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
