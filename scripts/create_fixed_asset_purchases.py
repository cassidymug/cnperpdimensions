"""
Fixed Asset Purchase Creator for CNPERP
Creates purchases for land, motor vehicles, and buildings with proper accounting
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timedelta
from decimal import Decimal
import uuid
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.purchases import Supplier, Purchase, PurchaseItem
from app.models.assets import FixedAsset
from app.models.branch import Branch
from app.models.banking import BankAccount, BankTransaction
from app.models.user import User
from app.models.accounting import AccountingCode


def create_fixed_asset_purchases(db: Session):
    """Create fixed asset purchases"""

    print("\n" + "="*70)
    print("  🏢 Creating Fixed Asset Purchases")
    print("="*70)

    # Get MAIN branch
    main_branch = db.query(Branch).filter_by(code="MAIN").first()
    if not main_branch:
        print("❌ Error: MAIN branch not found")
        return

    # Get user
    user = db.query(User).filter_by(active=True).first()
    if not user:
        print("❌ Error: No active user found")
        return

    # Get or use bank account
    bank_account = db.query(BankAccount).filter_by(branch_id=main_branch.id).first()
    if not bank_account:
        print("❌ Error: No bank account found")
        return

    print(f"💳 Using bank account: {bank_account.name} (Balance: P{bank_account.balance:,.2f})")

    # Get accounting codes for fixed assets
    land_code = db.query(AccountingCode).filter_by(code="1510").first()  # Land
    vehicle_code = db.query(AccountingCode).filter_by(code="1520").first()  # Motor Vehicles
    building_code = db.query(AccountingCode).filter_by(code="1530").first()  # Buildings

    # Fixed Asset Purchases Data
    asset_purchases = [
        {
            "supplier_name": "Botswana Land Board",
            "asset_type": "land",
            "asset_name": "Commercial Land - Plot 5234, Gaborone",
            "description": "5,000 sqm commercial plot in Gaborone CBD",
            "cost": Decimal("2500000.00"),  # P2.5M
            "accounting_code": land_code,
            "location": "Plot 5234, CBD, Gaborone",
            "depreciation_method": None,  # Land doesn't depreciate
            "useful_life": None
        },
        {
            "supplier_name": "Botswana Land Board",
            "asset_type": "land",
            "asset_name": "Warehouse Land - Plot 892, Lobatse",
            "description": "10,000 sqm industrial land in Lobatse",
            "cost": Decimal("800000.00"),  # P800K
            "accounting_code": land_code,
            "location": "Plot 892, Industrial Area, Lobatse",
            "depreciation_method": None,
            "useful_life": None
        },
        {
            "supplier_name": "Toyota Botswana",
            "asset_type": "vehicle",
            "asset_name": "Toyota Hilux 2.8 GD-6 4x4",
            "description": "Double cab pickup - White - BAA 1234 GP",
            "cost": Decimal("485000.00"),  # P485K
            "accounting_code": vehicle_code,
            "location": "Gaborone Head Office",
            "depreciation_method": "straight_line",
            "useful_life": 5,
            "registration": "BAA 1234 GP",
            "engine_number": "2GD-FTV-8945612",
            "chassis_number": "MHFXW3CD0PK123456"
        },
        {
            "supplier_name": "Toyota Botswana",
            "asset_type": "vehicle",
            "asset_name": "Toyota Fortuner 2.8 GD-6",
            "description": "7-seater SUV - Silver - BAB 5678 GP",
            "cost": Decimal("625000.00"),  # P625K
            "accounting_code": vehicle_code,
            "location": "Gaborone Head Office",
            "depreciation_method": "straight_line",
            "useful_life": 5,
            "registration": "BAB 5678 GP",
            "engine_number": "2GD-FTV-7823451",
            "chassis_number": "MHFXW3CD0PK234567"
        },
        {
            "supplier_name": "Nissan Botswana",
            "asset_type": "vehicle",
            "asset_name": "Nissan NP300 Hardbody 2.5",
            "description": "Single cab pickup - White - BAC 9012 GP",
            "cost": Decimal("295000.00"),  # P295K
            "accounting_code": vehicle_code,
            "location": "Maun Branch",
            "depreciation_method": "straight_line",
            "useful_life": 5,
            "registration": "BAC 9012 GP",
            "engine_number": "YD25-DDTi-5612389",
            "chassis_number": "MNT7S4CD0PK345678"
        },
        {
            "supplier_name": "Khato Properties",
            "asset_type": "building",
            "asset_name": "Commercial Building - Main Street, Gaborone",
            "description": "3-storey office building, 1,200 sqm total",
            "cost": Decimal("4500000.00"),  # P4.5M
            "accounting_code": building_code,
            "location": "Plot 5234, Main Street, Gaborone",
            "depreciation_method": "straight_line",
            "useful_life": 40
        },
        {
            "supplier_name": "Mokolodi Builders",
            "asset_type": "building",
            "asset_name": "Warehouse - Lobatse Industrial",
            "description": "Warehouse facility, 2,500 sqm",
            "cost": Decimal("1800000.00"),  # P1.8M
            "accounting_code": building_code,
            "location": "Plot 892, Lobatse Industrial Area",
            "depreciation_method": "straight_line",
            "useful_life": 30
        }
    ]

    total_spent = Decimal("0")
    purchase_count = 0

    for idx, asset_data in enumerate(asset_purchases, 1):
        # Get or create supplier
        supplier = db.query(Supplier).filter_by(name=asset_data["supplier_name"]).first()
        if not supplier:
            # Get payables accounting code
            payables_code = db.query(AccountingCode).filter_by(code="2110").first()

            supplier = Supplier(
                name=asset_data["supplier_name"],
                email=f"{asset_data['supplier_name'].lower().replace(' ', '_')}@example.com",
                telephone="+267 1234567",
                accounting_code_id=payables_code.id if payables_code else None,
                branch_id=main_branch.id,
                supplier_type="vendor",
                payment_terms=30,
                credit_limit=Decimal("10000000.00"),
                active=True
            )
            db.add(supplier)
            db.flush()
            print(f"✅ Created supplier: {supplier.name}")

        # Calculate amounts (no VAT on land, but VAT on vehicles and buildings)
        cost = asset_data["cost"]
        if asset_data["asset_type"] == "land":
            vat = Decimal("0")
            total = cost
        else:
            vat = cost * Decimal("0.14")  # 14% VAT
            total = cost + vat

        # Create Purchase
        purchase = Purchase(
            supplier_id=supplier.id,
            branch_id=main_branch.id,
            purchase_date=datetime.now().date(),
            total_amount=float(total),
            total_vat_amount=float(vat),
            total_amount_ex_vat=float(cost),
            amount_paid=float(total),
            status="received",
            created_by=user.id,
            approved_by=user.id,
            approved_at=datetime.now().date(),
            received_at=datetime.now().date(),
            bank_account_id=bank_account.id,
            notes=f"Fixed asset purchase: {asset_data['asset_name']}"
        )
        db.add(purchase)
        db.flush()

        # Create Purchase Item (as asset)
        purchase_item = PurchaseItem(
            purchase_id=purchase.id,
            product_id=None,  # No product for fixed assets
            quantity=1,
            cost=float(cost),
            total_cost=float(cost),
            vat_amount=float(vat),
            vat_rate=Decimal("0.14") if asset_data["asset_type"] != "land" else Decimal("0"),
            is_inventory=False,
            is_asset=True,
            asset_name=asset_data["asset_name"],
            asset_category=asset_data["asset_type"],
            asset_depreciation_method=asset_data["depreciation_method"],
            asset_useful_life_years=asset_data["useful_life"],
            asset_salvage_value=Decimal("0"),
            asset_location=asset_data["location"],
            asset_accounting_code_id=asset_data["accounting_code"].id if asset_data["accounting_code"] else None,
            description=asset_data["description"]
        )

        # Add vehicle-specific fields
        if asset_data["asset_type"] == "vehicle":
            purchase_item.asset_vehicle_registration = asset_data.get("registration")
            purchase_item.asset_engine_number = asset_data.get("engine_number")
            purchase_item.asset_chassis_number = asset_data.get("chassis_number")

        db.add(purchase_item)

        # Create Fixed Asset record
        fixed_asset = FixedAsset(
            name=asset_data["asset_name"],
            category=asset_data["asset_type"],
            description=asset_data["description"],
            purchase_date=datetime.now().date(),
            purchase_cost=float(cost),
            depreciation_method=asset_data["depreciation_method"] or "none",
            useful_life_years=asset_data["useful_life"] or 0,
            salvage_value=0.0,
            accumulated_depreciation=0.0,
            book_value=float(cost),
            location=asset_data["location"],
            branch_id=main_branch.id,
            accounting_code_id=asset_data["accounting_code"].id if asset_data["accounting_code"] else None,
            status="active",
            purchase_id=purchase.id
        )

        # Add vehicle-specific fields to asset
        if asset_data["asset_type"] == "vehicle":
            fixed_asset.vehicle_registration = asset_data.get("registration")
            fixed_asset.engine_number = asset_data.get("engine_number")
            fixed_asset.chassis_number = asset_data.get("chassis_number")

        db.add(fixed_asset)

        # Create bank transaction
        bank_transaction = BankTransaction(
            bank_account_id=bank_account.id,
            date=datetime.now().date(),
            transaction_type="withdrawal",
            amount=float(total),
            description=f"Payment for {asset_data['asset_name']}",
            reference=f"ASSET{idx:04d}",
            reconciled=False,
            posting_status="posted"
        )
        db.add(bank_transaction)

        # Update bank balance
        bank_account.balance -= total

        print(f"\n✅ Fixed Asset Purchase #{idx} created:")
        print(f"   Type: {asset_data['asset_type'].upper()}")
        print(f"   Name: {asset_data['asset_name']}")
        print(f"   Supplier: {supplier.name}")
        print(f"   Cost: P{cost:,.2f}")
        if vat > 0:
            print(f"   VAT (14%): P{vat:,.2f}")
        print(f"   Total: P{total:,.2f}")
        print(f"   Location: {asset_data['location']}")
        if asset_data["depreciation_method"]:
            print(f"   Depreciation: {asset_data['useful_life']} years ({asset_data['depreciation_method']})")
        print(f"   Bank Balance: P{bank_account.balance:,.2f}")

        total_spent += total
        purchase_count += 1

    db.commit()

    print("\n" + "="*70)
    print("  ✅ Fixed Asset Purchases Complete!")
    print("="*70)
    print(f"\n📊 Summary:")
    print(f"   • Total Assets Purchased: {purchase_count}")
    print(f"   • Land Parcels: 2")
    print(f"   • Motor Vehicles: 3")
    print(f"   • Buildings: 2")
    print(f"   • Total Amount Spent: P{total_spent:,.2f}")
    print(f"   • Remaining Bank Balance: P{bank_account.balance:,.2f}")
    print("\n" + "="*70 + "\n")


def main():
    """Main function"""
    print("\n" + "="*70)
    print("  🚀 CNPERP Fixed Asset Purchase Creator")
    print("="*70)
    print("Creating purchases for land, vehicles, and buildings...")

    db = SessionLocal()
    try:
        create_fixed_asset_purchases(db)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
