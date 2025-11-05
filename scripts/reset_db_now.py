#!/usr/bin/env python3
"""
CNPERP Database Reset and Seed Script (No Delay)
Quick reset for testing - USE WITH CAUTION!
"""

import sys
import os
import subprocess
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import text
from app.core.database import engine

def print_header(message):
    """Print a formatted header"""
    print("\n" + "="*60)
    print(f"  {message}")
    print("="*60 + "\n")

def drop_all_tables():
    """Drop all tables in the database"""
    print_header("STEP 1: Dropping All Tables")
    try:
        with engine.begin() as conn:
            # Drop all tables
            conn.execute(text("""
                DO $$
                DECLARE
                    r RECORD;
                BEGIN
                    -- Drop all tables
                    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
                        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
                    END LOOP;

                    -- Drop all sequences
                    FOR r IN (SELECT sequence_name FROM information_schema.sequences WHERE sequence_schema = 'public') LOOP
                        EXECUTE 'DROP SEQUENCE IF EXISTS ' || quote_ident(r.sequence_name) || ' CASCADE';
                    END LOOP;

                    -- Drop all views
                    FOR r IN (SELECT table_name FROM information_schema.views WHERE table_schema = 'public') LOOP
                        EXECUTE 'DROP VIEW IF EXISTS ' || quote_ident(r.table_name) || ' CASCADE';
                    END LOOP;
                END;
                $$;
            """))
        print("✅ All tables, sequences, and views dropped successfully!")
        return True
    except Exception as e:
        print(f"❌ Error dropping tables: {str(e)}")
        return False

def run_alembic_migrations():
    """Run Alembic migrations to recreate schema"""
    print_header("STEP 2: Creating Database Schema")
    try:
        # Import all models to ensure they're registered
        from app.models import base
        from app.models.user import User
        from app.models.branch import Branch
        from app.models.accounting import AccountingCode, JournalEntry, AccountingEntry
        from app.models.inventory import Product, UnitOfMeasure, InventoryTransaction, InventoryAdjustment
        from app.models.purchases import Supplier, Purchase, PurchaseItem
        from app.models.sales import Sale, SaleItem
        from app.models.app_setting import AppSetting

        # Try importing cash management models if they exist
        try:
            from app.models.cash_management import CashSubmission, FloatAllocation
        except ImportError:
            print("ℹ️  Cash management models not found, skipping...")

        # Import Base from database
        from app.core.database import Base, engine

        # Create all tables
        print("Creating all tables...")
        Base.metadata.create_all(bind=engine)

        print("✅ Database schema created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating schema: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def seed_database():
    """Seed the database with initial data"""
    print_header("STEP 3: Seeding Database with Initial Data")
    try:
        # Import and run the seed_all script
        from app.database import seed_all
        seed_all.seed_database()
        return True
    except Exception as e:
        print(f"❌ Error seeding database: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def verify_vat_accounts():
    """Verify that VAT accounts were created"""
    print_header("STEP 4: Verifying VAT Accounts")
    try:
        from app.core.database import SessionLocal
        from app.models.accounting import AccountingCode

        db = SessionLocal()
        try:
            vat_accounts = db.query(AccountingCode).filter(
                AccountingCode.name.ilike('%vat%')
            ).all()

            print(f"\n✅ Found {len(vat_accounts)} VAT-related accounts:")
            for account in vat_accounts:
                print(f"   • {account.code} - {account.name} ({account.account_type})")

            # Check for specific required VAT accounts
            required_vat_accounts = {
                '1161': 'VAT Receivable',
                '1162': 'Input VAT',
                '2131': 'VAT Payable',
                '2132': 'Output VAT'
            }

            print("\n📋 Required VAT Accounts Status:")
            all_found = True
            for code, expected_name in required_vat_accounts.items():
                account = db.query(AccountingCode).filter_by(code=code).first()
                if account:
                    print(f"   ✅ {code} - {account.name}")
                else:
                    print(f"   ❌ {code} - {expected_name} (NOT FOUND)")
                    all_found = False

            return all_found
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Error verifying VAT accounts: {str(e)}")
        return False

def show_summary():
    """Show final summary with database statistics"""
    print_header("📊 Database Summary")
    try:
        from app.core.database import SessionLocal
        from app.models.user import User
        from app.models.branch import Branch
        from app.models.accounting import AccountingCode
        from app.models.inventory import Product, UnitOfMeasure
        from app.models.purchases import Supplier

        db = SessionLocal()
        try:
            user_count = db.query(User).count()
            branch_count = db.query(Branch).count()
            account_count = db.query(AccountingCode).count()
            product_count = db.query(Product).count()
            supplier_count = db.query(Supplier).count()
            uom_count = db.query(UnitOfMeasure).count()

            print(f"👤 Users: {user_count}")
            print(f"🏢 Branches: {branch_count}")
            print(f"📊 Chart of Accounts: {account_count}")
            print(f"📦 Products: {product_count}")
            print(f"🏭 Suppliers: {supplier_count}")
            print(f"📏 Units of Measure: {uom_count}")
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️  Could not generate summary: {str(e)}")

def main():
    """Main execution function"""
    print_header("🚀 CNPERP Database Reset and Seed (IMMEDIATE)")

    # Step 1: Drop all tables
    if not drop_all_tables():
        print("\n❌ Database reset failed at Step 1")
        sys.exit(1)

    # Step 2: Run migrations
    if not run_alembic_migrations():
        print("\n❌ Database reset failed at Step 2")
        sys.exit(1)

    # Step 3: Seed database
    if not seed_database():
        print("\n❌ Database reset failed at Step 3")
        sys.exit(1)

    # Step 4: Verify VAT accounts
    if not verify_vat_accounts():
        print("\n⚠️  Warning: Some VAT accounts may be missing")

    # Show summary
    show_summary()

    # Final summary
    print_header("✅ Database Reset and Seed Complete!")
    print("🎉 Your database is ready for use!")
    print("\n📋 Login Credentials:")
    print("   • Super Admin: superadmin / superadminpassword")
    print("   • Admin: admin / adminpassword")
    print("   • Manager: manager / managerpassword")
    print("   • Accountant: accountant / accountantpassword")
    print("   • Cashier: cashier / cashierpassword")
    print("   • POS User: pos_user / pos123")
    print("   • Staff: staff / staffpassword")
    print("\n📝 Note: Sample suppliers and products have been removed.")
    print("   Add your business data via the application interface.")
    print("\n🌐 Access the application at: http://localhost:8010")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
