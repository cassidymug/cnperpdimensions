#!/usr/bin/env python3
"""
CNPERP Database Seeding Script - Comprehensive and Robust
Single script to seed all essential data for the CNPERP system.
This version includes improved error handling and dependency management.
"""

import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import SessionLocal
from app.models.user import User
from app.models.branch import Branch
from app.models.accounting import AccountingCode
from app.models.app_setting import AppSetting
from app.models.purchases import Supplier
from app.models.inventory import Product, UnitOfMeasure
from app.core.security import get_password_hash
from app.models.accounting_constants import AccountType
from app.models.role import Role, Permission, RolePermission

def create_session():
    """Creates and returns a new database session."""
    return SessionLocal()

def seed_database():
    """Main function to orchestrate the database seeding process."""
    print("🌱 Starting CNPERP Database Seeding...")
    db = create_session()
    
    try:
        seed_app_settings(db)
        main_branch = seed_branches(db)
        
        if main_branch:
            seed_default_users(db, main_branch)
            seed_branch_permissions(db)
            seed_accounting_codes(db, main_branch)
            seed_units_of_measure(db)
            seed_suppliers(db, main_branch)
            seed_products(db, main_branch)
            
            db.commit()
            print("\n✅ Database seeding completed successfully!")
        else:
            print("\n❌ Branch seeding failed. Aborting further seeding.")
            db.rollback()

    except Exception as e:
        db.rollback()
        print(f"\n❌ An unexpected error occurred during seeding: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

def seed_app_settings(db: Session) -> None:
    """Seeds the application settings."""
    print("\n🌍 Seeding App Settings...")
    try:
        if not db.query(AppSetting).first():
            settings = AppSetting(
                currency="BWP",
                vat_rate=14.0,
                country="BW",
                app_name="CNP Solutions Botswana",
                address="Plot 123, Industrial Area, Kasane",
                phone="+267 7481 8826",
                email="sales@cnpsolutions.co.bw"
            )
            db.add(settings)
            db.commit()
            print("✅ App Settings seeded.")
        else:
            print("ℹ️ App Settings already exist.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding app settings: {str(e)}")
        raise

def seed_branches(db: Session) -> Optional[Branch]:
    """Seeds the main branch and returns it."""
    print("\n🏢 Seeding branches...")
    try:
        branch = db.query(Branch).filter_by(code="MAIN").first()
        if not branch:
            branch = Branch(
                code="MAIN", name="Main Branch",
                location="Gaborone", phone="+267 333 3333",
                email="main@cnperp.com", address="Main Mall",
                is_head_office=True
            )
            db.add(branch)
            db.commit()
            db.refresh(branch)
            print("✅ Main branch seeded.")
        else:
            print("ℹ️ Main branch already exists.")
        return branch
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding branches: {str(e)}")
        return None

def seed_branch_permissions(db: Session) -> None:
    """Seeds branch-related permissions and assigns them to roles."""
    print("\n🔐 Seeding branch permissions...")
    definitions = [
        ("branches","create","all","Create branches"),
        ("branches","update","all","Update branches"),
        ("branches","view_all","all","View all branches globally")
    ]
    created = 0
    for module, action, resource, desc in definitions:
        existing = db.query(Permission).filter_by(module=module, action=action, resource=resource).first()
        if not existing:
            perm = Permission(module=module, action=action, resource=resource, name=f"{module}:{action}:{resource}", description=desc)
            db.add(perm)
            db.flush()
            created += 1
    if created:
        db.commit()
        print(f"✅ Created {created} branch permissions")
    else:
        print("ℹ️ Branch permissions already exist")
    # Assign to roles
    super_admin = db.query(Role).filter(Role.name.ilike('super_admin')).first()
    admin = db.query(Role).filter(Role.name.ilike('admin')).first()
    accountant = db.query(Role).filter(Role.name.ilike('accountant')).first()
    def attach(role, module, action):
        if not role: return
        perm = db.query(Permission).filter_by(module=module, action=action, resource='all').first()
        if not perm: return
        exists = db.query(RolePermission).filter_by(role_id=role.id, permission_id=perm.id).first()
        if not exists:
            db.add(RolePermission(role_id=role.id, permission_id=perm.id))
            db.commit()
    for act in ("create","update","view_all"):
        attach(super_admin,"branches",act)
        attach(admin,"branches",act)
    attach(accountant,"branches","view_all")
    print("✅ Assigned branch permissions to roles (accountant gets view_all)")

def seed_default_users(db: Session, branch: Branch) -> None:
    """Seeds default users with hashed passwords."""
    print("\n👤 Seeding default users...")
    
    users = [
        {"username": "superadmin", "password": "superadminpassword", "role": "super_admin"},
        {"username": "admin", "password": "adminpassword", "role": "admin"},
    ]
    
    for user_data in users:
        try:
            if not db.query(User).filter_by(username=user_data["username"]).first():
                hashed_password = get_password_hash(user_data['password'])
                user = User(
                    username=user_data['username'],
                    password_digest=hashed_password,
                    role=user_data['role'],
                    branch_id=branch.id,
                    email=f"{user_data['username']}@example.com",
                    first_name=user_data['role'].capitalize().replace('_', ' '),
                    last_name="User",
                    active=True
                )
                db.add(user)
                print(f"✅ Created user: {user_data['username']}")
        except Exception as e:
            print(f"❌ Error creating user {user_data['username']}: {str(e)}")
    
    print("\n📋 Login Credentials (for reference):")
    for user_data in users:
        print(f"   - {user_data['role'].replace('_', ' ').title()}: {user_data['username']} / {user_data['password']}")

def seed_accounting_codes(db: Session, branch: Branch) -> None:
    """Seeds the chart of accounts."""
    print("\n📊 Seeding Chart of Accounts...")
    
    accounts_data = [
        # Assets
        {'code': '1000', 'name': 'Assets', 'account_type': AccountType.ASSET, 'is_parent': True},
        {'code': '1100', 'name': 'Current Assets', 'account_type': AccountType.ASSET, 'parent_code': '1000', 'is_parent': True},
        {'code': '1110', 'name': 'Cash and Bank', 'account_type': AccountType.ASSET, 'parent_code': '1100', 'is_parent': True},
        {'code': '1111', 'name': 'Main Bank Account', 'account_type': AccountType.ASSET, 'parent_code': '1110', 'category': 'Bank'},
        {'code': '1112', 'name': 'Petty Cash', 'account_type': AccountType.ASSET, 'parent_code': '1110', 'category': 'Cash'},
        {'code': '1120', 'name': 'Accounts Receivable', 'account_type': AccountType.ASSET, 'parent_code': '1100'},
        {'code': '1130', 'name': 'Inventory', 'account_type': AccountType.ASSET, 'parent_code': '1100'},

        # Liabilities
        {'code': '2000', 'name': 'Liabilities', 'account_type': AccountType.LIABILITY, 'is_parent': True},
        {'code': '2100', 'name': 'Current Liabilities', 'account_type': AccountType.LIABILITY, 'parent_code': '2000', 'is_parent': True},
        {'code': '2110', 'name': 'Accounts Payable', 'account_type': AccountType.LIABILITY, 'parent_code': '2100'},

        # Equity
        {'code': '3000', 'name': 'Equity', 'account_type': AccountType.EQUITY, 'is_parent': True},
        {'code': '3100', 'name': 'Retained Earnings', 'account_type': AccountType.EQUITY, 'parent_code': '3000'},

        # Revenue
        {'code': '4000', 'name': 'Revenue', 'account_type': AccountType.REVENUE, 'is_parent': True},
        {'code': '4100', 'name': 'Sales Revenue', 'account_type': AccountType.REVENUE, 'parent_code': '4000'},

        # Expenses
        {'code': '5000', 'name': 'Expenses', 'account_type': AccountType.EXPENSE, 'is_parent': True},
        {'code': '5100', 'name': 'Cost of Goods Sold', 'account_type': AccountType.EXPENSE, 'parent_code': '5000'},
    ]

    for acc_data in accounts_data:
        try:
            code = acc_data['code']
            if db.query(AccountingCode).filter_by(code=code).first():
                continue

            parent_id = None
            if 'parent_code' in acc_data:
                parent = db.query(AccountingCode).filter_by(code=acc_data['parent_code']).first()
                if parent:
                    parent_id = parent.id
                else:
                    print(f"⚠️ Parent account {acc_data['parent_code']} not found for {code}.")

            account = AccountingCode(
                code=code,
                name=acc_data['name'],
                account_type=acc_data['account_type'],
                category=acc_data.get('category', 'Default'),
                parent_id=parent_id,
                is_parent=acc_data.get('is_parent', False),
                branch_id=branch.id
            )
            db.add(account)
            print(f"  - Creating account: {code} - {acc_data['name']}")

        except Exception as e:
            print(f"❌ Error creating account {acc_data.get('code')}: {str(e)}")
    
    print("✅ Chart of Accounts seeding process finished.")

def seed_units_of_measure(db: Session) -> None:
    """Seeds basic units of measure."""
    print("\n📏 Seeding Units of Measure...")
    units = [{'name': 'Piece', 'abbreviation': 'pcs'}, {'name': 'Kilogram', 'abbreviation': 'kg'}]
    for unit_data in units:
        if not db.query(UnitOfMeasure).filter_by(name=unit_data['name']).first():
            db.add(UnitOfMeasure(**unit_data, is_base_unit=True))
            print(f"  - Created unit: {unit_data['name']}")
    print("✅ Units of measure seeded.")

def seed_suppliers(db: Session, branch: Branch) -> None:
    """Seeds sample suppliers."""
    print("\n🏭 Seeding Suppliers...")
    ap_account = db.query(AccountingCode).filter_by(code='2110').first()
    if not ap_account:
        print("⚠️ Accounts Payable account not found. Skipping supplier seeding.")
        return
    
    suppliers = [{'name': 'Default Supplier', 'email': 'supplier@example.com'}]
    for sup_data in suppliers:
        if not db.query(Supplier).filter_by(name=sup_data['name']).first():
            db.add(Supplier(**sup_data, accounting_code_id=ap_account.id, branch_id=branch.id, active=True))
            print(f"  - Created supplier: {sup_data['name']}")
    print("✅ Suppliers seeded.")

def seed_products(db: Session, branch: Branch) -> None:
    """Seeds sample products."""
    print("\n📦 Seeding Products...")
    unit = db.query(UnitOfMeasure).first()
    supplier = db.query(Supplier).first()
    if not unit or not supplier:
        print("⚠️ Default unit or supplier not found. Skipping product seeding.")
        return

    products = [{'name': 'Sample Product', 'selling_price': 100, 'cost_price': 70, 'quantity': 50}]
    for prod_data in products:
        if not db.query(Product).filter_by(name=prod_data['name']).first():
            db.add(Product(**prod_data, unit_of_measure_id=unit.id, supplier_id=supplier.id, branch_id=branch.id, active=True))
            print(f"  - Created product: {prod_data['name']}")
    print("✅ Products seeded.")

if __name__ == "__main__":
    seed_database()
