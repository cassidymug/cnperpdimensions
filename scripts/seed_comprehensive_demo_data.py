#!/usr/bin/env python3
"""
CNPERP Comprehensive Demo Data Seeding Script
Creates complete sample business data including:
- Dimensions and Projects
- Multiple Branches across Botswana
- Suppliers and Customers
- Products with Stock
- Stock Allocations to Branches
- POS Transactions
- Fixed Assets (Land, Buildings, Vehicles)
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
import random

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.user import User
from app.models.branch import Branch
from app.models.accounting import AccountingCode
from app.models.purchases import Supplier
from app.models.inventory import Product, UnitOfMeasure, InventoryTransaction
from app.models.sales import Sale, SaleItem
from app.core.security import get_password_hash

# Import models - may need to create some if they don't exist
try:
    from app.models.accounting_dimensions import Dimension, Project
except ImportError:
    print("⚠️  Warning: Dimension and Project models not found - skipping dimensions")
    Dimension = None
    Project = None

try:
    from app.models.customer import Customer
except ImportError:
    print("⚠️  Warning: Customer model not found - will skip customers")
    Customer = None

try:
    from app.models.fixed_assets import FixedAsset
except ImportError:
    print("⚠️  Warning: FixedAsset model not found - will skip fixed assets")
    FixedAsset = None


def print_header(message):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"  {message}")
    print("="*70 + "\n")


def seed_dimensions(db: Session) -> dict:
    """Seed accounting dimensions"""
    if not Dimension:
        print("⏭️  Skipping dimensions (model not available)")
        return {}

    print_header("📊 Seeding Dimensions")

    dimensions_data = [
        {'code': 'DEPT', 'name': 'Department', 'description': 'Business departments', 'is_mandatory': False},
        {'code': 'PROJ', 'name': 'Project', 'description': 'Project tracking', 'is_mandatory': False},
        {'code': 'COST', 'name': 'Cost Center', 'description': 'Cost allocation centers', 'is_mandatory': False},
        {'code': 'LOC', 'name': 'Location', 'description': 'Geographic location', 'is_mandatory': False},
        {'code': 'PROD', 'name': 'Product Line', 'description': 'Product line categorization', 'is_mandatory': False},
    ]

    dimensions = {}
    for dim_data in dimensions_data:
        existing = db.query(Dimension).filter_by(code=dim_data['code']).first()
        if not existing:
            dim = Dimension(**dim_data, active=True)
            db.add(dim)
            db.flush()
            dimensions[dim_data['code']] = dim
            print(f"✅ Created dimension: {dim_data['code']} - {dim_data['name']}")
        else:
            dimensions[dim_data['code']] = existing
            print(f"ℹ️  Dimension {dim_data['code']} already exists")

    db.commit()
    return dimensions


def seed_projects(db: Session) -> list:
    """Seed projects"""
    if not Project:
        print("⏭️  Skipping projects (model not available)")
        return []

    print_header("🏗️ Seeding Projects")

    projects_data = [
        {'code': 'HOTEL-2025', 'name': 'Kasane Hotel Construction', 'description': 'New 50-room hotel in Kasane', 'status': 'active', 'budget': 15000000.00},
        {'code': 'RETAIL-GBN', 'name': 'Gaborone Retail Expansion', 'description': 'Expand retail presence in Gaborone', 'status': 'active', 'budget': 2500000.00},
        {'code': 'IT-UPGRADE', 'name': 'IT Infrastructure Upgrade', 'description': 'Company-wide IT system upgrade', 'status': 'active', 'budget': 800000.00},
        {'code': 'MINING-JWN', 'name': 'Jwaneng Mining Supply Contract', 'description': 'Supply equipment to mining operations', 'status': 'active', 'budget': 5000000.00},
        {'code': 'TOURISM-DELTA', 'name': 'Okavango Delta Tourism Initiative', 'description': 'Tourism development project', 'status': 'planning', 'budget': 3500000.00},
    ]

    projects = []
    for proj_data in projects_data:
        existing = db.query(Project).filter_by(code=proj_data['code']).first()
        if not existing:
            project = Project(
                **proj_data,
                start_date=datetime.now() - timedelta(days=random.randint(30, 180)),
                active=True
            )
            db.add(project)
            db.flush()
            projects.append(project)
            print(f"✅ Created project: {proj_data['code']} - {proj_data['name']}")
        else:
            projects.append(existing)
            print(f"ℹ️  Project {proj_data['code']} already exists")

    db.commit()
    return projects


def seed_branches(db: Session) -> dict:
    """Seed branches across Botswana"""
    print_header("🏢 Seeding Branches")

    branches_data = [
        {'code': 'GBN', 'name': 'Gaborone Branch', 'location': 'Gaborone', 'phone': '+267 391 2345', 'email': 'gaborone@cnpsolutions.co.bw', 'address': 'Plot 123, CBD, Gaborone', 'is_head_office': True},
        {'code': 'MAUN', 'name': 'Maun Branch', 'location': 'Maun', 'phone': '+267 686 1234', 'email': 'maun@cnpsolutions.co.bw', 'address': 'Matlapana Road, Maun', 'is_head_office': False},
        {'code': 'LOBA', 'name': 'Lobatse Branch', 'location': 'Lobatse', 'phone': '+267 533 0123', 'email': 'lobatse@cnpsolutions.co.bw', 'address': 'Main Mall, Lobatse', 'is_head_office': False},
        {'code': 'KANG', 'name': 'Kanye Branch', 'location': 'Kanye', 'phone': '+267 544 1234', 'email': 'kanye@cnpsolutions.co.bw', 'address': 'Station Road, Kanye', 'is_head_office': False},
        {'code': 'JWN', 'name': 'Jwaneng Branch', 'location': 'Jwaneng', 'phone': '+267 588 2345', 'email': 'jwaneng@cnpsolutions.co.bw', 'address': 'Main Street, Jwaneng', 'is_head_office': False},
        {'code': 'KSN', 'name': 'Kasane Branch', 'location': 'Kasane', 'phone': '+267 625 1234', 'email': 'kasane@cnpsolutions.co.bw', 'address': 'Chobe Avenue, Kasane', 'is_head_office': False},
        {'code': 'PLP', 'name': 'Palapye Branch', 'location': 'Palapye', 'phone': '+267 492 3456', 'email': 'palapye@cnpsolutions.co.bw', 'address': 'A1 Highway, Palapye', 'is_head_office': False},
        {'code': 'FRAN', 'name': 'Francistown Branch', 'location': 'Francistown', 'phone': '+267 241 5678', 'email': 'francistown@cnpsolutions.co.bw', 'address': 'Blue Jacket Street, Francistown', 'is_head_office': False},
    ]

    branches = {}
    for branch_data in branches_data:
        existing = db.query(Branch).filter_by(code=branch_data['code']).first()
        if not existing:
            branch = Branch(**branch_data, active=True)
            db.add(branch)
            db.flush()
            branches[branch_data['code']] = branch
            print(f"✅ Created branch: {branch_data['code']} - {branch_data['name']}")
        else:
            branches[branch_data['code']] = existing
            print(f"ℹ️  Branch {branch_data['code']} already exists")

    db.commit()
    return branches


def seed_suppliers(db: Session, main_branch: Branch) -> list:
    """Seed suppliers"""
    print_header("🏭 Seeding Suppliers")

    # Get accounting code for suppliers
    supplier_account = db.query(AccountingCode).filter_by(code='2110').first()
    if not supplier_account:
        supplier_account = db.query(AccountingCode).filter_by(name='Liabilities').first()

    suppliers_data = [
        {'name': 'Choppies Enterprises', 'email': 'procurement@choppies.co.bw', 'telephone': '+267 391 4444', 'contact_person': 'Thabo Moeti', 'address': 'Industrial Site, Gaborone', 'supplier_type': 'distributor', 'payment_terms': 30, 'credit_limit': 500000.00},
        {'name': 'Sefalana Wholesale', 'email': 'sales@sefalana.co.bw', 'telephone': '+267 390 2222', 'contact_person': 'Mpho Kgosi', 'address': 'Broadhurst Industrial, Gaborone', 'supplier_type': 'distributor', 'payment_terms': 45, 'credit_limit': 750000.00},
        {'name': 'Barloworld Equipment', 'email': 'orders@barloworld.co.bw', 'telephone': '+267 397 5555', 'contact_person': 'John Sithole', 'address': 'Gaborone West, Gaborone', 'supplier_type': 'manufacturer', 'payment_terms': 60, 'credit_limit': 2000000.00},
        {'name': 'Kgalagadi Breweries Limited', 'email': 'supply@kbl.co.bw', 'telephone': '+267 365 3333', 'contact_person': 'Sarah Molefe', 'address': 'Plot 22, Gaborone', 'supplier_type': 'manufacturer', 'payment_terms': 30, 'credit_limit': 300000.00},
        {'name': 'Botswana Meat Commission', 'email': 'sales@bmc.bw', 'telephone': '+267 533 7777', 'contact_person': 'Boitumelo Tau', 'address': 'Lobatse', 'supplier_type': 'manufacturer', 'payment_terms': 15, 'credit_limit': 400000.00},
        {'name': 'Solar Botswana', 'email': 'info@solarbw.co.bw', 'telephone': '+267 318 6666', 'contact_person': 'Lesego Mogale', 'address': 'Broadhurst, Gaborone', 'supplier_type': 'vendor', 'payment_terms': 30, 'credit_limit': 600000.00},
        {'name': 'Masiela Trust Holdings', 'email': 'procurement@masiela.co.bw', 'telephone': '+267 395 8888', 'contact_person': 'Kefilwe Masire', 'address': 'Main Mall, Gaborone', 'supplier_type': 'distributor', 'payment_terms': 45, 'credit_limit': 450000.00},
        {'name': 'African Echo', 'email': 'sales@africanecho.co.bw', 'telephone': '+267 241 9999', 'contact_person': 'Neo Moagi', 'address': 'Francistown', 'supplier_type': 'vendor', 'payment_terms': 30, 'credit_limit': 250000.00},
    ]

    suppliers = []
    for supplier_data in suppliers_data:
        existing = db.query(Supplier).filter_by(name=supplier_data['name']).first()
        if not existing:
            supplier = Supplier(
                **supplier_data,
                accounting_code_id=supplier_account.id if supplier_account else None,
                branch_id=main_branch.id,
                active=True
            )
            db.add(supplier)
            db.flush()
            suppliers.append(supplier)
            print(f"✅ Created supplier: {supplier_data['name']}")
        else:
            suppliers.append(existing)
            print(f"ℹ️  Supplier {supplier_data['name']} already exists")

    db.commit()
    return suppliers


def seed_customers(db: Session, main_branch: Branch) -> list:
    """Seed customers"""
    if not Customer:
        print("⏭️  Skipping customers (model not available)")
        return []

    print_header("👥 Seeding Customers")

    # Get accounting code for customers
    customer_account = db.query(AccountingCode).filter_by(code='1131').first()
    if not customer_account:
        customer_account = db.query(AccountingCode).filter_by(code='1130').first()

    customers_data = [
        {'name': 'Debswana Diamond Company', 'email': 'accounts@debswana.bw', 'telephone': '+267 361 2000', 'contact_person': 'Tshepiso Keabetswe', 'address': 'Plot 64516, Gaborone', 'customer_type': 'corporate', 'credit_limit': 5000000.00},
        {'name': 'Air Botswana', 'email': 'procurement@airbotswana.co.bw', 'telephone': '+267 395 2812', 'contact_person': 'Kagiso Dintwe', 'address': 'Sir Seretse Khama Airport, Gaborone', 'customer_type': 'corporate', 'credit_limit': 2000000.00},
        {'name': 'Botswana Power Corporation', 'email': 'supplies@bpc.bw', 'telephone': '+267 360 3333', 'contact_person': 'Tshepo Makwati', 'address': 'Macheng Way, Gaborone', 'customer_type': 'corporate', 'credit_limit': 3000000.00},
        {'name': 'Cresta Hotels', 'email': 'admin@cresta.co.bw', 'telephone': '+267 395 2580', 'contact_person': 'Mmoloki Seretse', 'address': 'The Mall, Gaborone', 'customer_type': 'corporate', 'credit_limit': 1500000.00},
        {'name': 'Wilderness Safaris Botswana', 'email': 'bookings@wilderness.co.bw', 'telephone': '+267 686 1449', 'contact_person': 'Khumo Mokwena', 'address': 'Maun', 'customer_type': 'corporate', 'credit_limit': 800000.00},
        {'name': 'Chobe Game Lodge', 'email': 'manager@chobegamelodge.com', 'telephone': '+267 625 0340', 'contact_person': 'Boago Masilo', 'address': 'Kasane', 'customer_type': 'corporate', 'credit_limit': 600000.00},
        {'name': 'Jwaneng Mine Hospital', 'email': 'procurement@jwanengmine.bw', 'telephone': '+267 588 5000', 'contact_person': 'Dr. Olebile Gaborone', 'address': 'Jwaneng', 'customer_type': 'corporate', 'credit_limit': 1000000.00},
        {'name': 'University of Botswana', 'email': 'procurement@ub.ac.bw', 'telephone': '+267 355 2874', 'contact_person': 'Prof. Olebogeng Senatla', 'address': 'UB Campus, Gaborone', 'customer_type': 'corporate', 'credit_limit': 2500000.00},
        {'name': 'Gaborone City Council', 'email': 'supplies@gcc.gov.bw', 'telephone': '+267 391 1200', 'contact_person': 'Tumelo Morapedi', 'address': 'City Hall, Gaborone', 'customer_type': 'government', 'credit_limit': 4000000.00},
        {'name': 'Francistown City Council', 'email': 'procurement@fcc.gov.bw', 'telephone': '+267 241 5666', 'contact_person': 'Kabo Phiri', 'address': 'Blue Jacket Street, Francistown', 'customer_type': 'government', 'credit_limit': 2000000.00},
        # Retail/Individual customers
        {'name': 'Thato Mokgosi', 'email': 'tmokgosi@gmail.com', 'telephone': '+267 7234 5678', 'contact_person': 'Self', 'address': 'Broadhurst, Gaborone', 'customer_type': 'individual', 'credit_limit': 50000.00},
        {'name': 'Keitumetse Moagi', 'email': 'kmoagi@yahoo.com', 'telephone': '+267 7556 7890', 'contact_person': 'Self', 'address': 'Extension 2, Maun', 'customer_type': 'individual', 'credit_limit': 30000.00},
    ]

    customers = []
    for cust_data in customers_data:
        existing = db.query(Customer).filter_by(name=cust_data['name']).first()
        if not existing:
            customer = Customer(
                **cust_data,
                accounting_code_id=customer_account.id if customer_account else None,
                branch_id=main_branch.id,
                payment_terms=30,
                active=True
            )
            db.add(customer)
            db.flush()
            customers.append(customer)
            print(f"✅ Created customer: {cust_data['name']}")
        else:
            customers.append(existing)
            print(f"ℹ️  Customer {cust_data['name']} already exists")

    db.commit()
    return customers


def seed_products(db: Session, branches: dict, suppliers: list) -> list:
    """Seed products with various categories"""
    print_header("📦 Seeding Products")

    # Get units of measure
    piece_unit = db.query(UnitOfMeasure).filter_by(name='Piece').first()
    kg_unit = db.query(UnitOfMeasure).filter_by(name='Kilogram').first()
    liter_unit = db.query(UnitOfMeasure).filter_by(name='Liter').first()
    meter_unit = db.query(UnitOfMeasure).filter_by(name='Meter').first()
    box_unit = db.query(UnitOfMeasure).filter_by(name='Box').first()

    main_branch = branches.get('GBN') or list(branches.values())[0]
    main_supplier = suppliers[0] if suppliers else None

    products_data = [
        # Electronics
        {'name': 'HP Laptop ProBook 450 G8', 'description': '15.6" Intel Core i5, 8GB RAM, 256GB SSD', 'barcode': 'LAP001', 'cost_price': 6500.00, 'selling_price': 8950.00, 'quantity': 50, 'minimum_stock_level': 10, 'unit': piece_unit, 'category': 'Electronics'},
        {'name': 'Dell Monitor 24" FHD', 'description': '24-inch Full HD LED Monitor', 'barcode': 'MON001', 'cost_price': 1200.00, 'selling_price': 1680.00, 'quantity': 80, 'minimum_stock_level': 15, 'unit': piece_unit, 'category': 'Electronics'},
        {'name': 'Logitech Wireless Mouse', 'description': 'Wireless optical mouse', 'barcode': 'MOUSE001', 'cost_price': 180.00, 'selling_price': 250.00, 'quantity': 200, 'minimum_stock_level': 30, 'unit': piece_unit, 'category': 'Electronics'},
        {'name': 'Canon Printer MF445dw', 'description': 'Multifunction laser printer', 'barcode': 'PRINT001', 'cost_price': 3200.00, 'selling_price': 4480.00, 'quantity': 30, 'minimum_stock_level': 5, 'unit': piece_unit, 'category': 'Electronics'},

        # Office Supplies
        {'name': 'Copy Paper A4 (Ream)', 'description': '80gsm white copier paper, 500 sheets', 'barcode': 'PAP001', 'cost_price': 45.00, 'selling_price': 65.00, 'quantity': 500, 'minimum_stock_level': 100, 'unit': piece_unit, 'category': 'Office Supplies'},
        {'name': 'Stapler Heavy Duty', 'description': 'Metal heavy duty stapler', 'barcode': 'STAP001', 'cost_price': 85.00, 'selling_price': 120.00, 'quantity': 150, 'minimum_stock_level': 20, 'unit': piece_unit, 'category': 'Office Supplies'},
        {'name': 'File Folder A4', 'description': 'Cardboard file folder', 'barcode': 'FILE001', 'cost_price': 12.00, 'selling_price': 18.00, 'quantity': 1000, 'minimum_stock_level': 200, 'unit': piece_unit, 'category': 'Office Supplies'},
        {'name': 'Ballpoint Pen Blue (Box of 50)', 'description': 'Blue ink ballpoint pens', 'barcode': 'PEN001', 'cost_price': 75.00, 'selling_price': 110.00, 'quantity': 200, 'minimum_stock_level': 40, 'unit': box_unit or piece_unit, 'category': 'Office Supplies'},

        # Beverages
        {'name': 'St Louis Lager (24-pack)', 'description': 'Local beer 340ml bottles', 'barcode': 'BEER001', 'cost_price': 180.00, 'selling_price': 250.00, 'quantity': 300, 'minimum_stock_level': 50, 'unit': box_unit or piece_unit, 'category': 'Beverages'},
        {'name': 'Coca-Cola 500ml (24-pack)', 'description': 'Soft drink 500ml bottles', 'barcode': 'COKE001', 'cost_price': 120.00, 'selling_price': 170.00, 'quantity': 400, 'minimum_stock_level': 80, 'unit': box_unit or piece_unit, 'category': 'Beverages'},
        {'name': 'Bottled Water 500ml (24-pack)', 'description': 'Purified drinking water', 'barcode': 'WATER001', 'cost_price': 55.00, 'selling_price': 80.00, 'quantity': 600, 'minimum_stock_level': 100, 'unit': box_unit or piece_unit, 'category': 'Beverages'},

        # Food Items
        {'name': 'Rice 10kg Bag', 'description': 'Long grain white rice', 'barcode': 'RICE001', 'cost_price': 120.00, 'selling_price': 170.00, 'quantity': 250, 'minimum_stock_level': 50, 'unit': piece_unit, 'category': 'Food'},
        {'name': 'Cooking Oil 5L', 'description': 'Vegetable cooking oil', 'barcode': 'OIL001', 'cost_price': 85.00, 'selling_price': 120.00, 'quantity': 180, 'minimum_stock_level': 30, 'unit': piece_unit, 'category': 'Food'},
        {'name': 'Beef Mince (per kg)', 'description': 'Fresh beef mince', 'barcode': 'BEEF001', 'cost_price': 68.00, 'selling_price': 95.00, 'quantity': 150, 'minimum_stock_level': 20, 'unit': kg_unit or piece_unit, 'category': 'Food'},

        # Building Materials
        {'name': 'Cement 50kg Bag', 'description': 'Portland cement', 'barcode': 'CEM001', 'cost_price': 65.00, 'selling_price': 90.00, 'quantity': 500, 'minimum_stock_level': 100, 'unit': piece_unit, 'category': 'Building Materials'},
        {'name': 'Paint Interior White 20L', 'description': 'White interior wall paint', 'barcode': 'PAINT001', 'cost_price': 450.00, 'selling_price': 630.00, 'quantity': 80, 'minimum_stock_level': 15, 'unit': piece_unit, 'category': 'Building Materials'},
        {'name': 'Steel Rods 12mm (6m)', 'description': 'Construction steel reinforcement', 'barcode': 'STEEL001', 'cost_price': 85.00, 'selling_price': 120.00, 'quantity': 400, 'minimum_stock_level': 50, 'unit': piece_unit, 'category': 'Building Materials'},

        # Cleaning Supplies
        {'name': 'Bleach 5L', 'description': 'Household bleach', 'barcode': 'BLEACH001', 'cost_price': 35.00, 'selling_price': 50.00, 'quantity': 200, 'minimum_stock_level': 40, 'unit': piece_unit, 'category': 'Cleaning'},
        {'name': 'Mop & Bucket Set', 'description': 'Complete mopping set', 'barcode': 'MOP001', 'cost_price': 120.00, 'selling_price': 170.00, 'quantity': 100, 'minimum_stock_level': 20, 'unit': piece_unit, 'category': 'Cleaning'},
        {'name': 'Hand Sanitizer 5L', 'description': 'Alcohol-based hand sanitizer', 'barcode': 'SANI001', 'cost_price': 250.00, 'selling_price': 350.00, 'quantity': 150, 'minimum_stock_level': 30, 'unit': piece_unit, 'category': 'Cleaning'},
    ]

    products = []
    for prod_data in products_data:
        existing = db.query(Product).filter_by(barcode=prod_data['barcode']).first()
        if not existing:
            product = Product(
                name=prod_data['name'],
                description=prod_data['description'],
                barcode=prod_data['barcode'],
                cost_price=prod_data['cost_price'],
                selling_price=prod_data['selling_price'],
                quantity=prod_data['quantity'],
                minimum_stock_level=prod_data['minimum_stock_level'],
                unit_of_measure_id=prod_data['unit'].id if prod_data['unit'] else None,
                supplier_id=main_supplier.id if main_supplier else None,
                branch_id=main_branch.id,
                category=prod_data.get('category'),
                active=True,
                is_taxable=True
            )
            db.add(product)
            db.flush()
            products.append(product)
            print(f"✅ Created product: {prod_data['name']}")
        else:
            products.append(existing)
            print(f"ℹ️  Product {prod_data['barcode']} already exists")

    db.commit()
    return products


def allocate_stock_to_branches(db: Session, products: list, branches: dict):
    """Allocate stock to different branches"""
    print_header("📊 Allocating Stock to Branches")

    # Skip the main branch (already has stock)
    other_branches = {k: v for k, v in branches.items() if k != 'GBN'}

    allocation_count = 0
    for product in products[:15]:  # Allocate first 15 products to branches
        for branch_code, branch in list(other_branches.items())[:5]:  # First 5 branches
            # Allocate 20-40% of main stock to each branch
            allocated_qty = int(product.quantity * random.uniform(0.20, 0.40))
            if allocated_qty > 0:
                # Create inventory transaction for transfer
                transaction = InventoryTransaction(
                    product_id=product.id,
                    transaction_type='transfer_in',
                    quantity=allocated_qty,
                    branch_id=branch.id,
                    reference_number=f"TRANSFER-{branch_code}-{product.barcode}",
                    notes=f"Initial stock allocation to {branch.name}"
                )
                db.add(transaction)
                allocation_count += 1

    db.commit()
    print(f"✅ Created {allocation_count} stock allocations")


def create_pos_transactions(db: Session, products: list, branches: dict, customers: list):
    """Create multiple POS transactions"""
    print_header("🛒 Creating POS Transactions")

    if not products or not branches:
        print("⚠️  Skipping POS transactions - no products or branches")
        return

    # Get cashier user
    cashier = db.query(User).filter_by(role='cashier').first()
    if not cashier:
        cashier = db.query(User).first()

    transaction_count = 0
    for _ in range(50):  # Create 50 transactions
        # Random branch
        branch = random.choice(list(branches.values()))

        # Random customer (or walk-in)
        customer = random.choice(customers) if customers and random.random() > 0.3 else None

        # Random date within last 30 days
        sale_date = datetime.now() - timedelta(days=random.randint(0, 30))

        # Create sale
        sale = Sale(
            branch_id=branch.id,
            user_id=cashier.id if cashier else None,
            customer_id=customer.id if customer and hasattr(customer, 'id') else None,
            sale_date=sale_date,
            payment_method=random.choice(['cash', 'card', 'mobile_money']),
            status='completed',
            notes=f"POS Sale at {branch.name}"
        )
        db.add(sale)
        db.flush()

        # Add 1-5 random items to sale
        num_items = random.randint(1, 5)
        selected_products = random.sample(products, min(num_items, len(products)))

        total_amount = 0
        for product in selected_products:
            quantity = random.randint(1, 5)
            unit_price = float(product.selling_price)
            line_total = quantity * unit_price

            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=unit_price,
                line_total=line_total
            )
            db.add(sale_item)
            total_amount += line_total

        sale.total_amount = total_amount
        db.add(sale)
        transaction_count += 1

    db.commit()
    print(f"✅ Created {transaction_count} POS transactions")


def create_fixed_assets(db: Session, branches: dict):
    """Create fixed assets (land, buildings, vehicles)"""
    if not FixedAsset:
        print("⏭️  Skipping fixed assets (model not available)")
        return

    print_header("🏢 Creating Fixed Assets")

    # Get accounting codes for fixed assets
    land_account = db.query(AccountingCode).filter_by(code='1211').first()
    vehicle_account = db.query(AccountingCode).filter_by(code='1214').first()
    building_account = db.query(AccountingCode).filter_by(code='1211').first()

    main_branch = branches.get('GBN') or list(branches.values())[0]

    assets_data = [
        # Land
        {'name': 'Plot 123 Gaborone CBD', 'asset_type': 'land', 'description': 'Commercial plot in Gaborone CBD, 2000 sqm', 'acquisition_date': datetime(2020, 3, 15), 'acquisition_cost': 2500000.00, 'account': land_account, 'depreciation_method': 'none'},
        {'name': 'Plot 456 Kasane Commercial', 'asset_type': 'land', 'description': 'Tourist area commercial plot, 5000 sqm', 'acquisition_date': datetime(2021, 6, 20), 'acquisition_cost': 1800000.00, 'account': land_account, 'depreciation_method': 'none'},

        # Buildings
        {'name': 'Gaborone Head Office Building', 'asset_type': 'building', 'description': '3-story office building, 1200 sqm', 'acquisition_date': datetime(2019, 9, 1), 'acquisition_cost': 8500000.00, 'account': building_account, 'depreciation_method': 'straight_line', 'useful_life_years': 40},
        {'name': 'Maun Warehouse', 'asset_type': 'building', 'description': 'Storage warehouse, 800 sqm', 'acquisition_date': datetime(2022, 2, 10), 'acquisition_cost': 3200000.00, 'account': building_account, 'depreciation_method': 'straight_line', 'useful_life_years': 30},
        {'name': 'Francistown Retail Shop', 'asset_type': 'building', 'description': 'Retail premises, 400 sqm', 'acquisition_date': datetime(2023, 5, 15), 'acquisition_cost': 2800000.00, 'account': building_account, 'depreciation_method': 'straight_line', 'useful_life_years': 30},

        # Vehicles
        {'name': 'Toyota Hilux GBN-001', 'asset_type': 'vehicle', 'description': 'Double cab 4x4 pickup, white', 'acquisition_date': datetime(2023, 1, 10), 'acquisition_cost': 450000.00, 'account': vehicle_account, 'depreciation_method': 'reducing_balance', 'useful_life_years': 5, 'registration': 'B123ABC'},
        {'name': 'Toyota Hilux MAUN-001', 'asset_type': 'vehicle', 'description': 'Double cab 4x4 pickup, silver', 'acquisition_date': datetime(2023, 3, 15), 'acquisition_cost': 450000.00, 'account': vehicle_account, 'depreciation_method': 'reducing_balance', 'useful_life_years': 5, 'registration': 'B456DEF'},
        {'name': 'Isuzu Truck GBN-T001', 'asset_type': 'vehicle', 'description': '5-ton delivery truck', 'acquisition_date': datetime(2022, 8, 20), 'acquisition_cost': 680000.00, 'account': vehicle_account, 'depreciation_method': 'reducing_balance', 'useful_life_years': 7, 'registration': 'B789GHI'},
        {'name': 'Toyota Quantum GBN-V001', 'asset_type': 'vehicle', 'description': '14-seater staff transport', 'acquisition_date': datetime(2023, 6, 5), 'acquisition_cost': 520000.00, 'account': vehicle_account, 'depreciation_method': 'reducing_balance', 'useful_life_years': 5, 'registration': 'B321JKL'},
        {'name': 'Mercedes Benz C-Class GBN-E001', 'asset_type': 'vehicle', 'description': 'Executive sedan', 'acquisition_date': datetime(2024, 1, 12), 'acquisition_cost': 750000.00, 'account': vehicle_account, 'depreciation_method': 'reducing_balance', 'useful_life_years': 5, 'registration': 'B654MNO'},
    ]

    asset_count = 0
    for asset_data in assets_data:
        existing = db.query(FixedAsset).filter_by(name=asset_data['name']).first()
        if not existing:
            asset = FixedAsset(
                name=asset_data['name'],
                asset_type=asset_data['asset_type'],
                description=asset_data['description'],
                acquisition_date=asset_data['acquisition_date'],
                acquisition_cost=asset_data['acquisition_cost'],
                accounting_code_id=asset_data['account'].id if asset_data['account'] else None,
                branch_id=main_branch.id,
                depreciation_method=asset_data['depreciation_method'],
                useful_life_years=asset_data.get('useful_life_years'),
                registration_number=asset_data.get('registration'),
                status='active'
            )
            db.add(asset)
            asset_count += 1
            print(f"✅ Created asset: {asset_data['name']}")
        else:
            print(f"ℹ️  Asset {asset_data['name']} already exists")

    db.commit()
    print(f"✅ Created {asset_count} fixed assets")


def main():
    """Main execution function"""
    print_header("🚀 CNPERP Comprehensive Demo Data Seeding")
    print("Creating complete business scenario with:")
    print("  • Dimensions and Projects")
    print("  • 8 Branches across Botswana")
    print("  • Suppliers and Customers")
    print("  • Products with Stock")
    print("  • Stock Allocations")
    print("  • POS Transactions")
    print("  • Fixed Assets (Land, Buildings, Vehicles)")
    print("\n⚠️  This will add substantial demo data to the database!")

    db = SessionLocal()

    try:
        # Seed data in order
        dimensions = seed_dimensions(db)
        projects = seed_projects(db)
        branches = seed_branches(db)
        suppliers = seed_suppliers(db, list(branches.values())[0])
        customers = seed_customers(db, list(branches.values())[0])
        products = seed_products(db, branches, suppliers)
        allocate_stock_to_branches(db, products, branches)
        create_pos_transactions(db, products, branches, customers)
        create_fixed_assets(db, branches)

        print_header("✅ Demo Data Seeding Complete!")
        print("🎉 Your database now contains comprehensive demo data!")
        print("\n📊 Summary:")
        print(f"   • Dimensions: {len(dimensions)}")
        print(f"   • Projects: {len(projects)}")
        print(f"   • Branches: {len(branches)}")
        print(f"   • Suppliers: {len(suppliers)}")
        print(f"   • Customers: {len(customers)}")
        print(f"   • Products: {len(products)}")
        print("\n🌐 Access the application at: http://localhost:8010")
        print("="*70 + "\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
