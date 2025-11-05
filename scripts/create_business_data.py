#!/usr/bin/env python3
"""
CNPERP Business Data Creation Script
Creates actual business data through proper transactions:
- Accounting dimensions and projects
- Multiple branches across Botswana
- Suppliers and customers
- Products with proper inventory
- Stock allocations to branches
- Fixed asset purchases (land, buildings, vehicles)
- Point of sale transactions
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.branch import Branch
from app.models.accounting import AccountingCode, JournalEntry, AccountingEntry
from app.models.accounting_dimensions import AccountingDimension, AccountingDimensionValue
from app.models.inventory import Product, UnitOfMeasure, InventoryTransaction
from app.models.purchases import Supplier, Purchase, PurchaseItem
from app.models.sales import Customer, Sale, SaleItem
from app.models.user import User
from app.models.app_setting import AppSetting

def print_header(message):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"  {message}")
    print("="*70)

def create_branches(db: Session):
    """Create branches across Botswana"""
    print_header("🏢 Creating Branches Across Botswana")

    branches_data = [
        {"code": "GBR", "name": "Gaborone Branch", "location": "Gaborone", "phone": "+267 395 2222", "email": "gaborone@cnp.bw"},
        {"code": "MAU", "name": "Maun Branch", "location": "Maun", "phone": "+267 686 0123", "email": "maun@cnp.bw"},
        {"code": "LOB", "name": "Lobatse Branch", "location": "Lobatse", "phone": "+267 533 0456", "email": "lobatse@cnp.bw"},
        {"code": "KNG", "name": "Kanye Branch", "location": "Kanye", "phone": "+267 544 0789", "email": "kanye@cnp.bw"},
        {"code": "JWA", "name": "Jwaneng Branch", "location": "Jwaneng", "phone": "+267 588 0321", "email": "jwaneng@cnp.bw"},
        {"code": "KAS", "name": "Kasane Branch", "location": "Kasane", "phone": "+267 625 0654", "email": "kasane@cnp.bw"},
        {"code": "PAL", "name": "Palapye Branch", "location": "Palapye", "phone": "+267 492 0987", "email": "palapye@cnp.bw"},
        {"code": "FRN", "name": "Francistown Branch", "location": "Francistown", "phone": "+267 241 1234", "email": "francistown@cnp.bw"},
    ]

    branches = {}
    for branch_data in branches_data:
        existing = db.query(Branch).filter_by(code=branch_data["code"]).first()
        if existing:
            print(f"ℹ️  Branch {branch_data['code']} already exists")
            branches[branch_data["code"]] = existing
        else:
            branch = Branch(
                code=branch_data["code"],
                name=branch_data["name"],
                location=branch_data["location"],
                phone=branch_data["phone"],
                email=branch_data["email"],
                address=f"{branch_data['location']}, Botswana",
                is_head_office=(branch_data["code"] == "GBR"),
                active=True
            )
            db.add(branch)
            db.flush()
            branches[branch_data["code"]] = branch
            print(f"✅ Created branch: {branch_data['name']}")

    db.commit()
    return branches

def create_dimensions_and_projects(db: Session, branches: dict):
    """Create accounting dimensions and projects"""
    print_header("📊 Creating Accounting Dimensions and Projects")

    # Create Department Dimension
    dept_dimension = db.query(AccountingDimension).filter_by(code="DEPT").first()
    if not dept_dimension:
        dept_dimension = AccountingDimension(
            code="DEPT",
            name="Department",
            description="Organizational departments",
            is_required=False,
            is_active=True
        )
        db.add(dept_dimension)
        db.flush()
        print("✅ Created Department dimension")

    # Create department values
    departments = [
        {"code": "SALES", "name": "Sales Department"},
        {"code": "OPS", "name": "Operations"},
        {"code": "FIN", "name": "Finance"},
        {"code": "IT", "name": "Information Technology"},
        {"code": "HR", "name": "Human Resources"},
    ]

    for dept in departments:
        existing = db.query(AccountingDimensionValue).filter_by(
            dimension_id=dept_dimension.id,
            code=dept["code"]
        ).first()
        if not existing:
            dim_val = AccountingDimensionValue(
                dimension_id=dept_dimension.id,
                code=dept["code"],
                name=dept["name"],
                is_active=True
            )
            db.add(dim_val)
            print(f"✅ Created department: {dept['name']}")

    # Create Cost Center Dimension
    cc_dimension = db.query(AccountingDimension).filter_by(code="CC").first()
    if not cc_dimension:
        cc_dimension = AccountingDimension(
            code="CC",
            name="Cost Center",
            description="Cost centers for expense allocation",
            is_required=False,
            is_active=True
        )
        db.add(cc_dimension)
        db.flush()
        print("✅ Created Cost Center dimension")

    # Create cost center values for each branch
    for branch_code, branch in branches.items():
        existing = db.query(AccountingDimensionValue).filter_by(
            dimension_id=cc_dimension.id,
            code=f"CC-{branch_code}"
        ).first()
        if not existing:
            dim_val = AccountingDimensionValue(
                dimension_id=cc_dimension.id,
                code=f"CC-{branch_code}",
                name=f"{branch.name} Cost Center",
                is_active=True
            )
            db.add(dim_val)
            print(f"✅ Created cost center: CC-{branch_code}")

    # Create Projects Dimension
    proj_dimension = db.query(AccountingDimension).filter_by(code="PROJ").first()
    if not proj_dimension:
        proj_dimension = AccountingDimension(
            code="PROJ",
            name="Project",
            description="Projects and initiatives",
            is_required=False,
            is_active=True
        )
        db.add(proj_dimension)
        db.flush()
        print("✅ Created Project dimension")

    # Create project values
    projects_data = [
        {"code": "PRJ001", "name": "Branch Expansion 2025"},
        {"code": "PRJ002", "name": "IT Infrastructure Upgrade"},
        {"code": "PRJ003", "name": "Warehouse Modernization"},
        {"code": "PRJ004", "name": "Customer Experience Initiative"},
    ]

    projects = {}
    for proj_data in projects_data:
        existing = db.query(AccountingDimensionValue).filter_by(
            dimension_id=proj_dimension.id,
            code=proj_data["code"]
        ).first()
        if not existing:
            project = AccountingDimensionValue(
                dimension_id=proj_dimension.id,
                code=proj_data["code"],
                name=proj_data["name"],
                is_active=True
            )
            db.add(project)
            db.flush()
            projects[proj_data["code"]] = project
            print(f"✅ Created project: {proj_data['name']}")
        else:
            projects[proj_data["code"]] = existing

    db.commit()
    return projects

def create_suppliers(db: Session, main_branch: Branch):
    """Create actual suppliers"""
    print_header("🏭 Creating Suppliers")

    # Get Accounts Payable account
    ap_account = db.query(AccountingCode).filter_by(code="2110").first()
    if not ap_account:
        ap_account = db.query(AccountingCode).filter(
            AccountingCode.name.ilike("%payable%")
        ).first()

    suppliers_data = [
        {
            "name": "Botswana Wholesale Suppliers",
            "email": "orders@bwsuppliers.co.bw",
            "telephone": "+267 395 1111",
            "address": "Plot 50370, Gaborone Industrial",
            "contact_person": "Kabo Mogwe",
            "supplier_type": "distributor",
            "payment_terms": 30,
            "credit_limit": 150000.00
        },
        {
            "name": "Diamond Logistics Ltd",
            "email": "sales@diamondlogistics.bw",
            "telephone": "+267 241 2222",
            "address": "Francistown Commercial District",
            "contact_person": "Mpho Kgosi",
            "supplier_type": "manufacturer",
            "payment_terms": 45,
            "credit_limit": 250000.00
        },
        {
            "name": "Kalahari Traders",
            "email": "info@kalaharitraders.bw",
            "telephone": "+267 686 3333",
            "address": "Maun Business Park",
            "contact_person": "Thabo Moeti",
            "supplier_type": "vendor",
            "payment_terms": 15,
            "credit_limit": 100000.00
        },
        {
            "name": "Southern Imports (Pty) Ltd",
            "email": "procurement@southernimports.co.bw",
            "telephone": "+267 533 4444",
            "address": "Lobatse Industrial Zone",
            "contact_person": "Neo Modise",
            "supplier_type": "distributor",
            "payment_terms": 30,
            "credit_limit": 200000.00
        },
    ]

    suppliers = {}
    for supp_data in suppliers_data:
        existing = db.query(Supplier).filter_by(name=supp_data["name"]).first()
        if not existing:
            supplier = Supplier(
                name=supp_data["name"],
                email=supp_data["email"],
                telephone=supp_data["telephone"],
                address=supp_data["address"],
                contact_person=supp_data["contact_person"],
                supplier_type=supp_data["supplier_type"],
                payment_terms=supp_data["payment_terms"],
                credit_limit=supp_data["credit_limit"],
                accounting_code_id=ap_account.id if ap_account else None,
                branch_id=main_branch.id,
                active=True
            )
            db.add(supplier)
            db.flush()
            suppliers[supp_data["name"]] = supplier
            print(f"✅ Created supplier: {supp_data['name']}")
        else:
            suppliers[supp_data["name"]] = existing

    db.commit()
    return suppliers

def create_customers(db: Session, branches: dict):
    """Create actual customers"""
    print_header("👥 Creating Customers")

    # Get Accounts Receivable account
    ar_account = db.query(AccountingCode).filter_by(code="1131").first()
    if not ar_account:
        ar_account = db.query(AccountingCode).filter(
            AccountingCode.name.ilike("%receivable%")
        ).first()

    customers_data = [
        {
            "name": "Chobe Safari Lodge",
            "email": "accounts@chobesafari.bw",
            "telephone": "+267 625 1111",
            "address": "Kasane",
            "branch": "KAS",
            "credit_limit": 75000.00
        },
        {
            "name": "Gabs City Mall",
            "email": "procurement@gabscitymall.bw",
            "telephone": "+267 395 2222",
            "address": "Gaborone CBD",
            "branch": "GBR",
            "credit_limit": 100000.00
        },
        {
            "name": "Okavango Delta Resorts",
            "email": "finance@okavangoresorts.bw",
            "telephone": "+267 686 3333",
            "address": "Maun",
            "branch": "MAU",
            "credit_limit": 150000.00
        },
        {
            "name": "Jwaneng Mine Contractors",
            "email": "orders@jwanengcontractors.bw",
            "telephone": "+267 588 4444",
            "address": "Jwaneng Industrial",
            "branch": "JWA",
            "credit_limit": 200000.00
        },
    ]

    customers = {}
    for cust_data in customers_data:
        existing = db.query(Customer).filter_by(name=cust_data["name"]).first()
        if not existing:
            customer = Customer(
                name=cust_data["name"],
                email=cust_data["email"],
                phone=cust_data["telephone"],  # Changed from telephone to phone
                address=cust_data["address"],
                credit_limit=cust_data["credit_limit"],
                accounting_code_id=ar_account.id if ar_account else None,
                branch_id=branches[cust_data["branch"]].id,
                active=True
            )
            db.add(customer)
            db.flush()
            customers[cust_data["name"]] = customer
            print(f"✅ Created customer: {cust_data['name']}")
        else:
            customers[cust_data["name"]] = existing

    db.commit()
    return customers

def create_products(db: Session, suppliers: dict, main_branch: Branch):
    """Create actual products"""
    print_header("📦 Creating Products")

    # Get units of measure
    piece = db.query(UnitOfMeasure).filter_by(name="Piece").first()
    kg = db.query(UnitOfMeasure).filter_by(name="Kilogram").first()
    liter = db.query(UnitOfMeasure).filter_by(name="Liter").first()
    box = db.query(UnitOfMeasure).filter_by(name="Box").first()

    # Get first supplier
    supplier = list(suppliers.values())[0] if suppliers else None

    products_data = [
        {
            "name": "Premium Office Paper A4 (500 sheets)",
            "sku": "PAP-A4-500",
            "barcode": "6001234567890",
            "description": "High quality 80gsm white paper",
            "cost_price": 45.00,
            "selling_price": 75.00,
            "quantity": 0,  # Will be added through purchases
            "minimum_stock_level": 100,
            "unit": piece
        },
        {
            "name": "Wireless Mouse - Logitech",
            "sku": "MSE-WRL-001",
            "barcode": "6001234567891",
            "description": "Ergonomic wireless mouse",
            "cost_price": 180.00,
            "selling_price": 299.00,
            "quantity": 0,
            "minimum_stock_level": 50,
            "unit": piece
        },
        {
            "name": "LED Desk Lamp",
            "sku": "LMP-LED-001",
            "barcode": "6001234567892",
            "description": "Adjustable LED desk lamp",
            "cost_price": 250.00,
            "selling_price": 420.00,
            "quantity": 0,
            "minimum_stock_level": 30,
            "unit": piece
        },
        {
            "name": "Cleaning Detergent (5L)",
            "sku": "CLN-DET-5L",
            "barcode": "6001234567893",
            "description": "Industrial strength cleaner",
            "cost_price": 85.00,
            "selling_price": 145.00,
            "quantity": 0,
            "minimum_stock_level": 40,
            "unit": liter
        },
        {
            "name": "Coffee Beans - Premium Arabica (1kg)",
            "sku": "COF-ARA-1KG",
            "barcode": "6001234567894",
            "description": "Premium roasted coffee beans",
            "cost_price": 220.00,
            "selling_price": 380.00,
            "quantity": 0,
            "minimum_stock_level": 25,
            "unit": kg
        },
        {
            "name": "Hand Sanitizer (500ml)",
            "sku": "SAN-500ML",
            "barcode": "6001234567895",
            "description": "70% alcohol hand sanitizer",
            "cost_price": 35.00,
            "selling_price": 65.00,
            "quantity": 0,
            "minimum_stock_level": 100,
            "unit": piece
        },
        {
            "name": "USB Flash Drive 64GB",
            "sku": "USB-64GB",
            "barcode": "6001234567896",
            "description": "High-speed USB 3.0",
            "cost_price": 145.00,
            "selling_price": 249.00,
            "quantity": 0,
            "minimum_stock_level": 40,
            "unit": piece
        },
        {
            "name": "Notebook A5 (200 pages)",
            "sku": "NTB-A5-200",
            "barcode": "6001234567897",
            "description": "Spiral bound notebook",
            "cost_price": 25.00,
            "selling_price": 45.00,
            "quantity": 0,
            "minimum_stock_level": 80,
            "unit": piece
        },
    ]

    products = {}
    for prod_data in products_data:
        existing = db.query(Product).filter_by(sku=prod_data["sku"]).first()
        if not existing:
            product = Product(
                name=prod_data["name"],
                sku=prod_data["sku"],
                barcode=prod_data["barcode"],
                description=prod_data["description"],
                cost_price=prod_data["cost_price"],
                selling_price=prod_data["selling_price"],
                quantity=prod_data["quantity"],
                minimum_stock_level=prod_data["minimum_stock_level"],
                unit_of_measure_id=prod_data["unit"].id if prod_data["unit"] else None,
                supplier_id=supplier.id if supplier else None,
                branch_id=main_branch.id,
                product_type="inventory_item",
                active=True,
                is_taxable=True
            )
            db.add(product)
            db.flush()
            products[prod_data["sku"]] = product
            print(f"✅ Created product: {prod_data['name']}")
        else:
            products[prod_data["sku"]] = existing

    db.commit()
    return products

def main():
    """Main execution function"""
    print_header("🚀 CNPERP Business Data Creation")
    print("Creating actual business transactions and data...")

    db = SessionLocal()
    try:
        # Get main branch
        main_branch = db.query(Branch).filter_by(code="MAIN").first()
        if not main_branch:
            print("❌ MAIN branch not found. Please run seed_all.py first.")
            return

        # Step 1: Create branches
        branches = create_branches(db)

        # Step 2: Create dimensions and projects
        projects = create_dimensions_and_projects(db, branches)

        # Step 3: Create suppliers
        suppliers = create_suppliers(db, main_branch)

        # Step 4: Create customers
        customers = create_customers(db, branches)

        # Step 5: Create products
        products = create_products(db, suppliers, main_branch)

        print_header("✅ Business Data Creation Complete!")
        print(f"\n📊 Summary:")
        print(f"   • Branches: {len(branches)}")
        print(f"   • Projects: {len(projects)}")
        print(f"   • Suppliers: {len(suppliers)}")
        print(f"   • Customers: {len(customers)}")
        print(f"   • Products: {len(products)}")
        print("\n📝 Next Steps:")
        print("   1. Create purchases to add stock")
        print("   2. Transfer stock to branches")
        print("   3. Record fixed asset purchases (land, vehicles, buildings)")
        print("   4. Create point of sale transactions")
        print("\n" + "="*70 + "\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
