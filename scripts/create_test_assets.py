"""
Create test assets for each category to verify View and Depreciate functionality
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date, timedelta
from decimal import Decimal
from app.core.database import SessionLocal
from app.models.asset_management import Asset, AssetCategory, AssetStatus, DepreciationMethod
import uuid

def create_test_assets():
    db = SessionLocal()
    try:
        # Test data for each category
        test_assets = [
            {
                'name': 'Executive Office Desk',
                'description': 'Mahogany executive desk with drawers',
                'category': AssetCategory.FURNITURE,
                'purchase_cost': Decimal('15000.00'),
                'location': 'HQ - CEO Office',
                'serial_number': 'DESK-001'
            },
            {
                'name': 'Conference Table',
                'description': 'Large conference table for boardroom',
                'category': AssetCategory.FURNITURE,
                'purchase_cost': Decimal('25000.00'),
                'location': 'HQ - Boardroom',
                'serial_number': 'TABLE-001'
            },
            {
                'name': 'Dell Latitude Laptop',
                'description': 'Dell Latitude 7420 laptop with i7 processor',
                'category': AssetCategory.COMPUTER,
                'purchase_cost': Decimal('18000.00'),
                'location': 'HQ - IT Department',
                'serial_number': 'LAP-2024-001',
                'manufacturer': 'Dell',
                'model_number': 'Latitude 7420'
            },
            {
                'name': 'HP LaserJet Printer',
                'description': 'HP LaserJet Pro M404dn printer',
                'category': AssetCategory.COMPUTER,
                'purchase_cost': Decimal('5500.00'),
                'location': 'HQ - Admin',
                'serial_number': 'PRT-2024-001',
                'manufacturer': 'HP',
                'model_number': 'LaserJet Pro M404dn'
            },
            {
                'name': 'Toyota Hilux',
                'description': 'Toyota Hilux 2.8 GD-6 Double Cab',
                'category': AssetCategory.VEHICLE,
                'purchase_cost': Decimal('450000.00'),
                'location': 'HQ - Fleet',
                'vehicle_registration': 'B123ABC',
                'vehicle_make': 'Toyota',
                'vehicle_model': 'Hilux 2.8 GD-6',
                'vehicle_year': 2023,
                'chassis_number': 'CHASSIS123456',
                'engine_number': 'ENGINE789012',
                'fuel_type': 'Diesel',
                'mileage': 15000
            },
            {
                'name': 'Ford Ranger',
                'description': 'Ford Ranger Wildtrak 2.0L Bi-Turbo',
                'category': AssetCategory.VEHICLE,
                'purchase_cost': Decimal('520000.00'),
                'location': 'Branch 1 - Fleet',
                'vehicle_registration': 'B456DEF',
                'vehicle_make': 'Ford',
                'vehicle_model': 'Ranger Wildtrak',
                'vehicle_year': 2024,
                'chassis_number': 'CHASSIS654321',
                'engine_number': 'ENGINE210987',
                'fuel_type': 'Diesel',
                'mileage': 8000
            },
            {
                'name': 'Bosch Drill Set',
                'description': 'Professional drill set with accessories',
                'category': AssetCategory.EQUIPMENT,
                'purchase_cost': Decimal('3500.00'),
                'location': 'Workshop',
                'serial_number': 'DRILL-001',
                'manufacturer': 'Bosch',
                'model_number': 'GSB 13 RE'
            },
            {
                'name': 'Makita Grinder',
                'description': 'Angle grinder 4.5 inch',
                'category': AssetCategory.EQUIPMENT,
                'purchase_cost': Decimal('2800.00'),
                'location': 'Workshop',
                'serial_number': 'GRIND-001',
                'manufacturer': 'Makita',
                'model_number': 'GA4530'
            }
        ]

        created_count = 0
        for asset_data in test_assets:
            # Common fields for all assets
            purchase_date = date.today() - timedelta(days=365)  # Purchased 1 year ago

            asset = Asset(
                id=str(uuid.uuid4()),
                asset_code=f"AST-{created_count + 1:04d}",
                status=AssetStatus.ACTIVE,
                purchase_date=purchase_date,
                depreciation_method=DepreciationMethod.STRAIGHT_LINE,
                useful_life_years=5,
                salvage_value=asset_data['purchase_cost'] * Decimal('0.1'),  # 10% salvage
                **asset_data
            )

            # Calculate initial depreciation (1 year)
            if asset.depreciation_method == DepreciationMethod.STRAIGHT_LINE:
                depreciable_amount = asset.purchase_cost - asset.salvage_value
                annual_depreciation = depreciable_amount / asset.useful_life_years
                asset.current_value = asset.purchase_cost - annual_depreciation

            db.add(asset)
            created_count += 1
            print(f"✓ Created: {asset.name} ({asset.category.value}) - {asset.asset_code}")

        db.commit()
        print(f"\n✅ Successfully created {created_count} test assets!")

        # Show summary
        print("\nSummary by category:")
        from sqlalchemy import func
        summary = db.query(
            Asset.category,
            func.count(Asset.id).label('count')
        ).group_by(Asset.category).all()

        for cat, count in summary:
            print(f"  {cat.value}: {count} assets")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    create_test_assets()
