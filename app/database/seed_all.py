#!/usr/bin/env python3
"""
CNPERP Database Seeding Script - Comprehensive
Single script to seed all essential data for the CNPERP system
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

def create_session():
    return SessionLocal()

def seed_database():
    print("🌱 Starting CNPERP Database Seeding...")
    db = create_session()

    try:
        seed_app_settings(db)
        main_branch = seed_branches(db)
        seed_default_users(db, main_branch)
        seed_accounting_codes(db, main_branch)
        seed_units_of_measure(db)
        # Sample data removed - suppliers and products should be added via the application
        db.commit()
        print("✅ Database seeding completed successfully!")
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {str(e)}")
        raise
    finally:
        db.close()

def seed_app_settings(db: Session) -> None:
    print("\n🌍 Seeding App Settings...")
    try:
        # Check if settings already exist
        settings = db.query(AppSetting).first()
        if not settings:
            settings = AppSetting(
                currency="BWP",
                vat_rate=14.0,
                country="BW",
                user_limit=25,
                app_name="CNP Solutions Botswana",
                address="Plot 123, Industrial Area, Kasane",
                phone="+267 7481 8826",
                email="sales@cnpsolutions.co.bw"
            )
            db.add(settings)
            print("✅ App Settings seeded.")
        else:
            print("ℹ️  App Settings already exist.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding app settings: {str(e)}")
        raise

def seed_branches(db: Session) -> Branch:
    print("\n🏢 Seeding branches...")
    try:
        branch = db.query(Branch).filter_by(code="MAIN").first()
        if not branch:
            branch = Branch(
                code="MAIN", name="Main Branch",
                location="Set by admin", phone="Set by admin",
                email="Set by admin", address="Set by admin",
                is_head_office=True
            )
            db.add(branch)
            db.commit()
            print("✅ Main branch seeded.")
        return branch
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {str(e)}")
        raise

def seed_default_users(db: Session, branch: Branch) -> None:
    print("\n👤 Seeding default users...")

    users = [
        {"username": "superadmin", "password_digest": get_password_hash("superadminpassword"), "role": "super_admin"},
        {"username": "admin", "password_digest": get_password_hash("adminpassword"), "role": "admin"},
        {"username": "manager", "password_digest": get_password_hash("managerpassword"), "role": "manager"},
        {"username": "accountant", "password_digest": get_password_hash("accountantpassword"), "role": "accountant"},
        {"username": "cashier", "password_digest": get_password_hash("cashierpassword"), "role": "cashier"},
        {"username": "pos_user", "password_digest": get_password_hash("pos123"), "role": "pos_user"},
        {"username": "staff", "password_digest": get_password_hash("staffpassword"), "role": "staff"}
    ]

    for user_data in users:
        try:
            if not db.query(User).filter_by(username=user_data["username"]).first():
                # Create user with hashed password
                user = User(
                    username=user_data['username'],
                    password_digest=user_data['password_digest'],  # Use password_digest instead of password
                    role=user_data['role'],
                    branch_id=branch.id,
                    email=f"{user_data['username']}@example.com",
                    first_name=user_data['role'].capitalize(),
                    last_name="User",
                    active=True
                )
                db.add(user)
                print(f"✅ Created user: {user_data['username']}")
        except Exception as e:
            print(f"❌ Error creating user {user_data['username']}: {str(e)}")

    # Print credentials for reference
    print("\n📋 Login Credentials:")
    credentials = [
        ("Super Admin", "superadmin", "superadminpassword"),
        ("Admin", "admin", "adminpassword"),
        ("Manager", "manager", "managerpassword"),
        ("Accountant", "accountant", "accountantpassword"),
        ("Cashier", "cashier", "cashierpassword"),
        ("POS User", "pos_user", "pos123"),
        ("Staff", "staff", "staffpassword")
    ]
    for role, username, password in credentials:
        print(f"   {role}: {username} / {password}")

def seed_accounting_codes(db: Session, branch: Branch) -> None:
    print("\n📊 Seeding Chart of Accounts...")

    def create_account(code: str, name: str, account_type: str, category: str,
                      parent_code: Optional[str] = None, is_parent: bool = False) -> None:
        try:
            parent_id = None
            if parent_code:
                parent = db.query(AccountingCode).filter_by(code=parent_code).first()
                if not parent:
                    print(f"❌ Parent {parent_code} not found for {code}")
                    return
                parent_id = parent.id
                if not parent.is_parent:
                    parent.is_parent = True
                    db.add(parent)
                    db.flush()

            existing_account = db.query(AccountingCode).filter_by(code=code).first()
            if not existing_account:
                account = AccountingCode(
                    code=code,
                    name=name,
                    account_type=account_type,
                    category=category,
                    parent_id=parent_id,
                    is_parent=is_parent,
                    branch_id=branch.id
                )
                db.add(account)
                db.flush()
                print(f"✅ Created account: {code} - {name}")
            else:
                print(f"ℹ️ Account {code} already exists")
        except Exception as e:
            print(f"❌ Error creating {code}: {str(e)}")

    # Top-level accounts
    accounts = [
        # Assets
        {'code': '1000', 'name': 'Assets', 'account_type': 'Asset', 'category': 'Current Asset', 'is_parent': True},
        {'code': '2000', 'name': 'Liabilities', 'account_type': 'Liability', 'category': 'Current Liability', 'is_parent': True},
        {'code': '3000', 'name': 'Equity', 'account_type': 'Equity', 'category': 'Retained Earnings', 'is_parent': True},
        {'code': '4000', 'name': 'Revenue', 'account_type': 'Revenue', 'category': 'Sales Revenue', 'is_parent': True},
        {'code': '5000', 'name': 'Expenses', 'account_type': 'Expense', 'category': 'Operating Expense', 'is_parent': True},

        # Assets - Current Assets
        {'code': '1100', 'name': 'Current Assets', 'account_type': 'Asset', 'category': 'Current Asset', 'parent': '1000', 'is_parent': True},

        # Cash and Cash Equivalents
        {'code': '1110', 'name': 'Cash and Cash Equivalents', 'account_type': 'Asset', 'category': 'Cash', 'parent': '1100', 'is_parent': True},
        {'code': '1111', 'name': 'Cash in Hand', 'account_type': 'Asset', 'category': 'Cash', 'parent': '1110'},
        {'code': '1112', 'name': 'Petty Cash', 'account_type': 'Asset', 'category': 'Cash', 'parent': '1110'},
        {'code': '1113', 'name': 'Credit Card Clearing', 'account_type': 'Asset', 'category': 'Cash', 'parent': '1110'},

        # Bank Accounts
        {'code': '1120', 'name': 'Bank Accounts', 'account_type': 'Asset', 'category': 'Bank', 'parent': '1100', 'is_parent': True},
        {'code': '1121', 'name': 'Main Bank Account', 'account_type': 'Asset', 'category': 'Bank', 'parent': '1120'},
        {'code': '1122', 'name': 'Savings Account', 'account_type': 'Asset', 'category': 'Bank', 'parent': '1120'},
        {'code': '1123', 'name': 'Business Account', 'account_type': 'Asset', 'category': 'Bank', 'parent': '1120'},
        {'code': '1124', 'name': 'Foreign Currency Account', 'account_type': 'Asset', 'category': 'Bank', 'parent': '1120'},

        # Accounts Receivable
        {'code': '1130', 'name': 'Accounts Receivable', 'account_type': 'Asset', 'category': 'Trade Receivables', 'parent': '1100', 'is_parent': True},
        {'code': '1131', 'name': 'Trade Debtors', 'account_type': 'Asset', 'category': 'Trade Receivables', 'parent': '1130'},
        {'code': '1132', 'name': 'Other Receivables', 'account_type': 'Asset', 'category': 'Trade Receivables', 'parent': '1130'},
        {'code': '1133', 'name': 'Staff Advances', 'account_type': 'Asset', 'category': 'Trade Receivables', 'parent': '1130'},
        {'code': '1134', 'name': 'Allowance for Doubtful Debts', 'account_type': 'Asset', 'category': 'Trade Receivables', 'parent': '1130'},

        # Inventory
        {'code': '1140', 'name': 'Inventory', 'account_type': 'Asset', 'category': 'Inventory', 'parent': '1100', 'is_parent': True},
        {'code': '1141', 'name': 'Raw Materials', 'account_type': 'Asset', 'category': 'Inventory', 'parent': '1140'},
        {'code': '1142', 'name': 'Work in Progress', 'account_type': 'Asset', 'category': 'Inventory', 'parent': '1140'},
        {'code': '1143', 'name': 'Finished Goods', 'account_type': 'Asset', 'category': 'Inventory', 'parent': '1140'},
        {'code': '1144', 'name': 'Merchandise Inventory', 'account_type': 'Asset', 'category': 'Inventory', 'parent': '1140'},

        # Prepaid Expenses
        {'code': '1150', 'name': 'Prepaid Expenses', 'account_type': 'Asset', 'category': 'Prepaid Assets', 'parent': '1100', 'is_parent': True},
        {'code': '1151', 'name': 'Prepaid Insurance', 'account_type': 'Asset', 'category': 'Prepaid Assets', 'parent': '1150'},
        {'code': '1152', 'name': 'Prepaid Rent', 'account_type': 'Asset', 'category': 'Prepaid Assets', 'parent': '1150'},
        {'code': '1153', 'name': 'Prepaid Licenses', 'account_type': 'Asset', 'category': 'Prepaid Assets', 'parent': '1150'},

        # Tax Assets
        {'code': '1160', 'name': 'Tax Assets', 'account_type': 'Asset', 'category': 'Tax Assets', 'parent': '1100', 'is_parent': True},
        {'code': '1161', 'name': 'VAT Receivable', 'account_type': 'Asset', 'category': 'Tax Assets', 'parent': '1160'},
        {'code': '1162', 'name': 'Input VAT', 'account_type': 'Asset', 'category': 'Tax Assets', 'parent': '1160'},
        {'code': '1163', 'name': 'Tax Credits', 'account_type': 'Asset', 'category': 'Tax Assets', 'parent': '1160'},

        # Fixed Assets
        {'code': '1200', 'name': 'Fixed Assets', 'account_type': 'Asset', 'category': 'Fixed Asset', 'parent': '1000', 'is_parent': True},

        # Property, Plant & Equipment
        {'code': '1210', 'name': 'Property, Plant & Equipment', 'account_type': 'Asset', 'category': 'Fixed Asset', 'parent': '1200', 'is_parent': True},
        {'code': '1211', 'name': 'Land & Buildings', 'account_type': 'Asset', 'category': 'Fixed Asset', 'parent': '1210'},
        {'code': '1212', 'name': 'Machinery & Equipment', 'account_type': 'Asset', 'category': 'Fixed Asset', 'parent': '1210'},
        {'code': '1213', 'name': 'Furniture & Fixtures', 'account_type': 'Asset', 'category': 'Fixed Asset', 'parent': '1210'},
        {'code': '1214', 'name': 'Motor Vehicles', 'account_type': 'Asset', 'category': 'Fixed Asset', 'parent': '1210'},
        {'code': '1215', 'name': 'Computer Equipment', 'account_type': 'Asset', 'category': 'Fixed Asset', 'parent': '1210'},

        # Accumulated Depreciation
        {'code': '1220', 'name': 'Accumulated Depreciation', 'account_type': 'Asset', 'category': 'Contra Asset', 'parent': '1200', 'is_parent': True},
        {'code': '1221', 'name': 'Accumulated Depreciation - Buildings', 'account_type': 'Asset', 'category': 'Contra Asset', 'parent': '1220'},
        {'code': '1222', 'name': 'Accumulated Depreciation - Machinery', 'account_type': 'Asset', 'category': 'Contra Asset', 'parent': '1220'},
        {'code': '1223', 'name': 'Accumulated Depreciation - Furniture', 'account_type': 'Asset', 'category': 'Contra Asset', 'parent': '1220'},
        {'code': '1224', 'name': 'Accumulated Depreciation - Vehicles', 'account_type': 'Asset', 'category': 'Contra Asset', 'parent': '1220'},
        {'code': '1225', 'name': 'Accumulated Depreciation - Computer Equipment', 'account_type': 'Asset', 'category': 'Contra Asset', 'parent': '1220'},

        # Intangible Assets
        {'code': '1230', 'name': 'Intangible Assets', 'account_type': 'Asset', 'category': 'Intangible Asset', 'parent': '1200', 'is_parent': True},
        {'code': '1231', 'name': 'Software Licenses', 'account_type': 'Asset', 'category': 'Intangible Asset', 'parent': '1230'},
        {'code': '1232', 'name': 'Patents & Trademarks', 'account_type': 'Asset', 'category': 'Intangible Asset', 'parent': '1230'},
        {'code': '1233', 'name': 'Goodwill', 'account_type': 'Asset', 'category': 'Intangible Asset', 'parent': '1230'},

        # Liabilities - Comprehensive structure
        {'code': '2100', 'name': 'Current Liabilities', 'account_type': 'Liability', 'category': 'Current Liability', 'parent': '2000', 'is_parent': True},

        # Accounts Payable - Suppliers
        {'code': '2110', 'name': 'Accounts Payable - Trade Suppliers', 'account_type': 'Liability', 'category': 'Trade Payables', 'parent': '2100'},
        {'code': '2111', 'name': 'Accounts Payable - Manufacturing Suppliers', 'account_type': 'Liability', 'category': 'Trade Payables', 'parent': '2110'},
        {'code': '2112', 'name': 'Accounts Payable - Distributors', 'account_type': 'Liability', 'category': 'Trade Payables', 'parent': '2110'},
        {'code': '2113', 'name': 'Accounts Payable - Service Providers', 'account_type': 'Liability', 'category': 'Trade Payables', 'parent': '2110'},

        # Other Current Liabilities
        {'code': '2120', 'name': 'Accrued Expenses', 'account_type': 'Liability', 'category': 'Accrued Liabilities', 'parent': '2100', 'is_parent': True},
        {'code': '2121', 'name': 'Accrued Salaries & Wages', 'account_type': 'Liability', 'category': 'Accrued Liabilities', 'parent': '2120'},
        {'code': '2122', 'name': 'Accrued Utilities', 'account_type': 'Liability', 'category': 'Accrued Liabilities', 'parent': '2120'},
        {'code': '2123', 'name': 'Accrued Interest', 'account_type': 'Liability', 'category': 'Accrued Liabilities', 'parent': '2120'},

        {'code': '2130', 'name': 'Tax Liabilities', 'account_type': 'Liability', 'category': 'Tax Payables', 'parent': '2100', 'is_parent': True},
        {'code': '2131', 'name': 'VAT Payable', 'account_type': 'Liability', 'category': 'Tax Payables', 'parent': '2130'},
        {'code': '2132', 'name': 'Output VAT', 'account_type': 'Liability', 'category': 'Tax Payables', 'parent': '2130'},
        {'code': '2133', 'name': 'PAYE Payable', 'account_type': 'Liability', 'category': 'Tax Payables', 'parent': '2130'},
        {'code': '2134', 'name': 'Corporate Tax Payable', 'account_type': 'Liability', 'category': 'Tax Payables', 'parent': '2130'},

        {'code': '2140', 'name': 'Short-term Loans', 'account_type': 'Liability', 'category': 'Short-term Debt', 'parent': '2100'},
        {'code': '2150', 'name': 'Customer Deposits', 'account_type': 'Liability', 'category': 'Customer Deposits', 'parent': '2100'},

        # Long-term Liabilities
        {'code': '2200', 'name': 'Long-term Liabilities', 'account_type': 'Liability', 'category': 'Long-term Debt', 'parent': '2000', 'is_parent': True},
        {'code': '2210', 'name': 'Long-term Loans', 'account_type': 'Liability', 'category': 'Long-term Debt', 'parent': '2200'},
        {'code': '2220', 'name': 'Equipment Finance', 'account_type': 'Liability', 'category': 'Long-term Debt', 'parent': '2200'},
        {'code': '2230', 'name': 'Mortgage Payable', 'account_type': 'Liability', 'category': 'Long-term Debt', 'parent': '2200'},

        # Equity
        # Equity - Comprehensive structure
        {'code': '3100', 'name': 'Share Capital', 'account_type': 'Equity', 'category': 'Equity Capital', 'parent': '3000', 'is_parent': True},
        {'code': '3101', 'name': 'Ordinary Share Capital', 'account_type': 'Equity', 'category': 'Equity Capital', 'parent': '3100'},
        {'code': '3102', 'name': 'Preference Share Capital', 'account_type': 'Equity', 'category': 'Equity Capital', 'parent': '3100'},

        {'code': '3200', 'name': 'Retained Earnings', 'account_type': 'Equity', 'category': 'Retained Earnings', 'parent': '3000', 'is_parent': True},
        {'code': '3201', 'name': 'Current Year Earnings', 'account_type': 'Equity', 'category': 'Retained Earnings', 'parent': '3200'},
        {'code': '3202', 'name': 'Prior Year Earnings', 'account_type': 'Equity', 'category': 'Retained Earnings', 'parent': '3200'},

        {'code': '3300', 'name': 'Capital Reserves', 'account_type': 'Equity', 'category': 'Capital Reserves', 'parent': '3000', 'is_parent': True},
        {'code': '3301', 'name': 'Revaluation Reserve', 'account_type': 'Equity', 'category': 'Capital Reserves', 'parent': '3300'},
        {'code': '3302', 'name': 'General Reserve', 'account_type': 'Equity', 'category': 'Capital Reserves', 'parent': '3300'},

        # Revenue - Comprehensive structure
        {'code': '4100', 'name': 'Operating Revenue', 'account_type': 'Revenue', 'category': 'Sales Revenue', 'parent': '4000', 'is_parent': True},
        {'code': '4101', 'name': 'Sales Revenue - Products', 'account_type': 'Revenue', 'category': 'Sales Revenue', 'parent': '4100'},
        {'code': '4102', 'name': 'Sales Revenue - Services', 'account_type': 'Revenue', 'category': 'Sales Revenue', 'parent': '4100'},
        {'code': '4103', 'name': 'Sales Returns & Allowances', 'account_type': 'Revenue', 'category': 'Sales Revenue', 'parent': '4100'},
        {'code': '4104', 'name': 'Sales Discounts', 'account_type': 'Revenue', 'category': 'Sales Revenue', 'parent': '4100'},

        {'code': '4200', 'name': 'Other Revenue', 'account_type': 'Revenue', 'category': 'Other Revenue', 'parent': '4000', 'is_parent': True},
        {'code': '4201', 'name': 'Interest Income', 'account_type': 'Revenue', 'category': 'Other Revenue', 'parent': '4200'},
        {'code': '4202', 'name': 'Rental Income', 'account_type': 'Revenue', 'category': 'Other Revenue', 'parent': '4200'},
        {'code': '4203', 'name': 'Commission Income', 'account_type': 'Revenue', 'category': 'Other Revenue', 'parent': '4200'},
        {'code': '4204', 'name': 'Foreign Exchange Gains', 'account_type': 'Revenue', 'category': 'Other Revenue', 'parent': '4200'},

        # Expenses - Comprehensive structure
        {'code': '5100', 'name': 'Cost of Goods Sold', 'account_type': 'Expense', 'category': 'Cost of Sales', 'parent': '5000', 'is_parent': True},
        {'code': '5101', 'name': 'Purchases', 'account_type': 'Expense', 'category': 'Cost of Sales', 'parent': '5100'},
        {'code': '5102', 'name': 'Purchase Returns', 'account_type': 'Expense', 'category': 'Cost of Sales', 'parent': '5100'},
        {'code': '5103', 'name': 'Direct Labor', 'account_type': 'Expense', 'category': 'Cost of Sales', 'parent': '5100'},
        {'code': '5104', 'name': 'Manufacturing Overhead', 'account_type': 'Expense', 'category': 'Cost of Sales', 'parent': '5100'},
        {'code': '5105', 'name': 'Freight In', 'account_type': 'Expense', 'category': 'Cost of Sales', 'parent': '5100'},

        {'code': '5200', 'name': 'Operating Expenses', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5000', 'is_parent': True},

        # Selling Expenses
        {'code': '5210', 'name': 'Selling Expenses', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5200', 'is_parent': True},
        {'code': '5211', 'name': 'Sales Salaries', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5210'},
        {'code': '5212', 'name': 'Sales Commissions', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5210'},
        {'code': '5213', 'name': 'Advertising & Marketing', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5210'},
        {'code': '5214', 'name': 'Travel & Entertainment', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5210'},
        {'code': '5215', 'name': 'Freight Out', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5210'},

        # Administrative Expenses
        {'code': '5220', 'name': 'Administrative Expenses', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5200', 'is_parent': True},
        {'code': '5221', 'name': 'Office Salaries', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5220'},
        {'code': '5222', 'name': 'Office Rent', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5220'},
        {'code': '5223', 'name': 'Office Supplies', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5220'},
        {'code': '5224', 'name': 'Telephone & Internet', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5220'},
        {'code': '5225', 'name': 'Insurance', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5220'},
        {'code': '5226', 'name': 'Professional Fees', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5220'},
        {'code': '5227', 'name': 'Bank Charges', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5220'},
        {'code': '5228', 'name': 'Depreciation Expense', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5220'},
        {'code': '5229', 'name': 'Bad Debt Expense', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5220'},

        # Utilities
        {'code': '5230', 'name': 'Utilities', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5200', 'is_parent': True},
        {'code': '5231', 'name': 'Electricity', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5230'},
        {'code': '5232', 'name': 'Water & Sewer', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5230'},
        {'code': '5233', 'name': 'Gas', 'account_type': 'Expense', 'category': 'Operating Expense', 'parent': '5230'},

        # Other Expenses
        {'code': '5300', 'name': 'Other Expenses', 'account_type': 'Expense', 'category': 'Other Expense', 'parent': '5000', 'is_parent': True},
        {'code': '5301', 'name': 'Interest Expense', 'account_type': 'Expense', 'category': 'Other Expense', 'parent': '5300'},
        {'code': '5302', 'name': 'Foreign Exchange Losses', 'account_type': 'Expense', 'category': 'Other Expense', 'parent': '5300'},
        {'code': '5303', 'name': 'Miscellaneous Expenses', 'account_type': 'Expense', 'category': 'Other Expense', 'parent': '5300'}
    ]

    for acc in accounts:
        if 'parent' in acc:
            acc['parent_code'] = acc.pop('parent')
        create_account(**acc)

    try:
        tag_targets = [
            ('A1.3', ['1140', '1300'], 'Inventory'),
            ('A1.1', ['1000', '1110'], 'Cash'),
            ('A1.1', ['1010', '1112'], 'Petty Cash'),
            ('L1.1', ['2100', '2110'], 'Accounts Payable'),
            ('A1.2', ['1200', '1161'], 'VAT Receivable'),
        ]
        for tag, code_candidates, name_fragment in tag_targets:
            code_obj = None
            for candidate in code_candidates:
                code_obj = db.query(AccountingCode).filter(AccountingCode.code == candidate).first()
                if code_obj:
                    break
            if not code_obj:
                code_obj = db.query(AccountingCode).filter(AccountingCode.name.ilike(f"%{name_fragment}%")).first()
            if code_obj and code_obj.reporting_tag != tag:
                code_obj.reporting_tag = tag
                db.add(code_obj)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"❌ Error finalizing accounting codes: {str(e)}")
        raise

    print("✅ Chart of Accounts seeded.")


def seed_units_of_measure(db: Session) -> None:
    """Seed basic units of measure"""
    print("\n📏 Seeding Units of Measure...")
    try:
        units = [
            {'name': 'Piece', 'abbreviation': 'pcs', 'is_base_unit': True, 'category': 'Count'},
            {'name': 'Kilogram', 'abbreviation': 'kg', 'is_base_unit': True, 'category': 'Weight'},
            {'name': 'Liter', 'abbreviation': 'L', 'is_base_unit': True, 'category': 'Volume'},
            {'name': 'Meter', 'abbreviation': 'm', 'is_base_unit': True, 'category': 'Length'},
            {'name': 'Box', 'abbreviation': 'box', 'is_base_unit': True, 'category': 'Container'},
            {'name': 'Case', 'abbreviation': 'case', 'is_base_unit': True, 'category': 'Container'},
            {'name': 'Pack', 'abbreviation': 'pack', 'is_base_unit': True, 'category': 'Container'}
        ]

        for unit_data in units:
            existing = db.query(UnitOfMeasure).filter_by(name=unit_data['name']).first()
            if not existing:
                unit = UnitOfMeasure(**unit_data)
                db.add(unit)
                db.flush()
                print(f"✅ Created unit: {unit_data['name']}")

        print("✅ Units of measure seeded.")
    except Exception as e:
        print(f"❌ Error seeding units of measure: {str(e)}")
        raise


def seed_suppliers(db: Session, branch: Branch) -> None:
    """Seed sample suppliers - DISABLED: Add suppliers via the application"""
    print("\n🏭 Skipping sample suppliers (add via application)...")
    # Sample data removed - suppliers should be added via the application interface


def seed_products(db: Session, branch: Branch) -> None:
    """Seed sample products - DISABLED: Add products via the application"""
    print("\n📦 Skipping sample products (add via application)...")
    # Sample data removed - products should be added via the application interface


if __name__ == "__main__":
    seed_database()
