"""
Create accounting dimensions tables

This script creates the necessary database tables for the accounting dimensions functionality.
Run this script after implementing the dimension models.

Usage:
python scripts/create_dimensions_tables.py
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.core.database import engine, SessionLocal
from app.models.accounting_dimensions import (
    AccountingDimension, AccountingDimensionValue,
    AccountingDimensionAssignment, DimensionTemplate
)


def create_dimension_tables():
    """Create the accounting dimension tables"""
    print("Creating accounting dimension tables...")

    try:
        # Import all models to ensure they're registered
        from app.models import Base

        # Create all tables (this will only create new ones)
        Base.metadata.create_all(bind=engine)

        print("✅ Dimension tables created successfully!")

        # Verify tables were created
        with engine.connect() as conn:
            # Check if our new tables exist
            table_check_queries = [
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'accounting_dimensions')",
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'accounting_dimension_values')",
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'accounting_dimension_assignments')",
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'dimension_templates')"
            ]

            table_names = [
                "accounting_dimensions",
                "accounting_dimension_values",
                "accounting_dimension_assignments",
                "dimension_templates"
            ]

            for query, table_name in zip(table_check_queries, table_names):
                result = conn.execute(text(query)).scalar()
                status = "✅ EXISTS" if result else "❌ MISSING"
                print(f"  {table_name}: {status}")

    except Exception as e:
        print(f"❌ Error creating dimension tables: {e}")
        return False

    return True


def seed_sample_dimensions():
    """Create sample dimensions for testing"""
    print("\nSeeding sample dimensions...")

    db = SessionLocal()
    try:
        # Check if dimensions already exist
        existing = db.query(AccountingDimension).first()
        if existing:
            print("  Sample dimensions already exist, skipping...")
            return True

        # Create sample dimensions
        dimensions_data = [
            {
                "code": "DEPT",
                "name": "Department",
                "description": "Organizational departments for cost allocation",
                "dimension_type": "organizational",
                "scope": "global",
                "is_required": True,
                "supports_hierarchy": True,
                "max_hierarchy_levels": 3,
                "display_order": 1
            },
            {
                "code": "PROJ",
                "name": "Project",
                "description": "Projects and initiatives for tracking costs and revenues",
                "dimension_type": "project",
                "scope": "global",
                "is_required": False,
                "supports_hierarchy": False,
                "max_hierarchy_levels": 1,
                "display_order": 2
            },
            {
                "code": "GEO",
                "name": "Geography",
                "description": "Geographical regions and locations",
                "dimension_type": "geographical",
                "scope": "global",
                "is_required": False,
                "supports_hierarchy": True,
                "max_hierarchy_levels": 2,
                "display_order": 3
            },
            {
                "code": "PROD",
                "name": "Product Line",
                "description": "Product lines and categories",
                "dimension_type": "product",
                "scope": "global",
                "is_required": False,
                "supports_hierarchy": True,
                "max_hierarchy_levels": 2,
                "display_order": 4
            }
        ]

        created_dimensions = []
        for dim_data in dimensions_data:
            dimension = AccountingDimension(**dim_data)
            db.add(dimension)
            db.flush()  # Get the ID
            created_dimensions.append(dimension)
            print(f"  ✅ Created dimension: {dimension.name} ({dimension.code})")

        # Create sample dimension values
        dept_dimension = next(d for d in created_dimensions if d.code == "DEPT")
        proj_dimension = next(d for d in created_dimensions if d.code == "PROJ")
        geo_dimension = next(d for d in created_dimensions if d.code == "GEO")
        prod_dimension = next(d for d in created_dimensions if d.code == "PROD")

        # Department values (with hierarchy)
        dept_values = [
            {"dimension_id": dept_dimension.id, "code": "SALES", "name": "Sales", "display_order": 1},
            {"dimension_id": dept_dimension.id, "code": "MKT", "name": "Marketing", "display_order": 2},
            {"dimension_id": dept_dimension.id, "code": "FIN", "name": "Finance", "display_order": 3},
            {"dimension_id": dept_dimension.id, "code": "OPS", "name": "Operations", "display_order": 4},
            {"dimension_id": dept_dimension.id, "code": "IT", "name": "Information Technology", "display_order": 5},
            {"dimension_id": dept_dimension.id, "code": "HR", "name": "Human Resources", "display_order": 6}
        ]

        dept_objects = []
        for val_data in dept_values:
            value = AccountingDimensionValue(**val_data, hierarchy_level=1)
            db.add(value)
            db.flush()
            dept_objects.append(value)

        # Add sub-departments
        sales_dept = next(v for v in dept_objects if v.code == "SALES")
        ops_dept = next(v for v in dept_objects if v.code == "OPS")

        sub_dept_values = [
            {"dimension_id": dept_dimension.id, "code": "RETAIL", "name": "Retail Sales",
             "parent_value_id": sales_dept.id, "hierarchy_level": 2, "display_order": 1},
            {"dimension_id": dept_dimension.id, "code": "WHOLESALE", "name": "Wholesale Sales",
             "parent_value_id": sales_dept.id, "hierarchy_level": 2, "display_order": 2},
            {"dimension_id": dept_dimension.id, "code": "WAREHOUSE", "name": "Warehouse Operations",
             "parent_value_id": ops_dept.id, "hierarchy_level": 2, "display_order": 1},
            {"dimension_id": dept_dimension.id, "code": "LOGISTICS", "name": "Logistics",
             "parent_value_id": ops_dept.id, "hierarchy_level": 2, "display_order": 2}
        ]

        for val_data in sub_dept_values:
            value = AccountingDimensionValue(**val_data)
            db.add(value)

        # Project values
        project_values = [
            {"dimension_id": proj_dimension.id, "code": "PROJ001", "name": "Digital Transformation", "display_order": 1},
            {"dimension_id": proj_dimension.id, "code": "PROJ002", "name": "Market Expansion", "display_order": 2},
            {"dimension_id": proj_dimension.id, "code": "PROJ003", "name": "Cost Optimization", "display_order": 3},
            {"dimension_id": proj_dimension.id, "code": "PROJ004", "name": "Product Development", "display_order": 4}
        ]

        for val_data in project_values:
            value = AccountingDimensionValue(**val_data, hierarchy_level=1)
            db.add(value)

        # Geography values
        geo_values = [
            {"dimension_id": geo_dimension.id, "code": "NORTH", "name": "Northern Region", "display_order": 1},
            {"dimension_id": geo_dimension.id, "code": "SOUTH", "name": "Southern Region", "display_order": 2},
            {"dimension_id": geo_dimension.id, "code": "CENTRAL", "name": "Central Region", "display_order": 3}
        ]

        for val_data in geo_values:
            value = AccountingDimensionValue(**val_data, hierarchy_level=1)
            db.add(value)

        # Product values
        product_values = [
            {"dimension_id": prod_dimension.id, "code": "HARDWARE", "name": "Hardware", "display_order": 1},
            {"dimension_id": prod_dimension.id, "code": "SOFTWARE", "name": "Software", "display_order": 2},
            {"dimension_id": prod_dimension.id, "code": "SERVICES", "name": "Services", "display_order": 3}
        ]

        for val_data in product_values:
            value = AccountingDimensionValue(**val_data, hierarchy_level=1)
            db.add(value)

        db.commit()
        print("  ✅ Sample dimension values created successfully!")

    except Exception as e:
        db.rollback()
        print(f"  ❌ Error seeding dimensions: {e}")
        return False

    finally:
        db.close()

    return True


def main():
    """Main function"""
    print("=== Accounting Dimensions Setup ===")

    # Create tables
    if not create_dimension_tables():
        sys.exit(1)

    # Seed sample data
    if not seed_sample_dimensions():
        sys.exit(1)

    print("\n🎉 Accounting dimensions setup completed successfully!")
    print("\nNext steps:")
    print("1. Restart your FastAPI application")
    print("2. Visit http://localhost:8010/docs to see the new dimension endpoints")
    print("3. Start assigning dimensions to your journal entries")
    print("4. Use the analysis endpoints to get multi-dimensional insights")


if __name__ == "__main__":
    main()
