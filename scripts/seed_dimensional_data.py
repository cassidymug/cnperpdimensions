"""
Seed Dimensional Data Script

This script creates sample cost centers and projects for dimensional accounting.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.accounting_dimensions import AccountingDimension, AccountingDimensionValue
from sqlalchemy import text

def seed_dimensional_data():
    """Create sample cost centers and projects"""
    db = SessionLocal()

    try:
        print("=== Starting Dimensional Data Seeding ===\n")

        # Check if dimensions already exist
        existing_dims = db.query(AccountingDimension).all()
        print(f"Found {len(existing_dims)} existing dimensions")

        # Create Cost Center dimension (Functional)
        cost_center_dim = db.query(AccountingDimension).filter(
            AccountingDimension.code == 'DEPT'
        ).first()

        if not cost_center_dim:
            print("\nCreating Cost Center dimension...")
            cost_center_dim = AccountingDimension(
                code='DEPT',
                name='Cost Center',
                dimension_type='functional',
                description='Departmental cost centers for expense allocation',
                is_active=True
            )
            db.add(cost_center_dim)
            db.flush()
            print(f"✓ Created dimension: {cost_center_dim.code} - {cost_center_dim.name}")
        else:
            print(f"\n✓ Cost Center dimension already exists: {cost_center_dim.id}")

        # Create sample cost centers
        cost_centers = [
            {'code': 'ADMIN', 'name': 'Administration', 'description': 'Administrative department'},
            {'code': 'SALES', 'name': 'Sales & Marketing', 'description': 'Sales and marketing department'},
            {'code': 'PROD', 'name': 'Production', 'description': 'Production department'},
            {'code': 'IT', 'name': 'Information Technology', 'description': 'IT department'},
            {'code': 'HR', 'name': 'Human Resources', 'description': 'HR department'},
            {'code': 'FIN', 'name': 'Finance', 'description': 'Finance department'},
            {'code': 'OPS', 'name': 'Operations', 'description': 'Operations department'},
        ]

        print("\nCreating cost center values...")
        created_cc = 0
        for cc_data in cost_centers:
            existing = db.query(AccountingDimensionValue).filter(
                AccountingDimensionValue.dimension_id == cost_center_dim.id,
                AccountingDimensionValue.code == cc_data['code']
            ).first()

            if not existing:
                cc_value = AccountingDimensionValue(
                    dimension_id=cost_center_dim.id,
                    code=cc_data['code'],
                    name=cc_data['name'],
                    description=cc_data['description'],
                    is_active=True
                )
                db.add(cc_value)
                created_cc += 1
                print(f"  ✓ Created: {cc_data['code']} - {cc_data['name']}")

        if created_cc > 0:
            print(f"Created {created_cc} cost center values")
        else:
            print("All cost centers already exist")

        # Create Project dimension
        project_dim = db.query(AccountingDimension).filter(
            AccountingDimension.code == 'PROJ'
        ).first()

        if not project_dim:
            print("\nCreating Project dimension...")
            project_dim = AccountingDimension(
                code='PROJ',
                name='Project',
                dimension_type='project',
                description='Projects for tracking project-based expenses and revenues',
                is_active=True
            )
            db.add(project_dim)
            db.flush()
            print(f"✓ Created dimension: {project_dim.code} - {project_dim.name}")
        else:
            print(f"\n✓ Project dimension already exists: {project_dim.id}")

        # Create sample projects
        projects = [
            {'code': 'PROJ001', 'name': 'Website Redesign', 'description': 'Company website redesign project'},
            {'code': 'PROJ002', 'name': 'ERP Implementation', 'description': 'ERP system implementation'},
            {'code': 'PROJ003', 'name': 'Office Renovation', 'description': 'Head office renovation'},
            {'code': 'PROJ004', 'name': 'Product Launch 2025', 'description': 'New product launch campaign'},
            {'code': 'PROJ005', 'name': 'Training Program', 'description': 'Employee training and development'},
            {'code': 'GEN', 'name': 'General Operations', 'description': 'General operations (not project-specific)'},
        ]

        print("\nCreating project values...")
        created_proj = 0
        for proj_data in projects:
            existing = db.query(AccountingDimensionValue).filter(
                AccountingDimensionValue.dimension_id == project_dim.id,
                AccountingDimensionValue.code == proj_data['code']
            ).first()

            if not existing:
                proj_value = AccountingDimensionValue(
                    dimension_id=project_dim.id,
                    code=proj_data['code'],
                    name=proj_data['name'],
                    description=proj_data['description'],
                    is_active=True
                )
                db.add(proj_value)
                created_proj += 1
                print(f"  ✓ Created: {proj_data['code']} - {proj_data['name']}")

        if created_proj > 0:
            print(f"Created {created_proj} project values")
        else:
            print("All projects already exist")

        # Commit all changes
        db.commit()

        # Verify data
        print("\n=== Verification ===")
        total_cc = db.query(AccountingDimensionValue).filter(
            AccountingDimensionValue.dimension_id == cost_center_dim.id
        ).count()
        total_proj = db.query(AccountingDimensionValue).filter(
            AccountingDimensionValue.dimension_id == project_dim.id
        ).count()

        print(f"Total Cost Centers in database: {total_cc}")
        print(f"Total Projects in database: {total_proj}")

        # Test the API endpoint query
        print("\n=== Testing API Query ===")
        result = db.execute(text("""
            SELECT d.code, d.name, d.dimension_type, COUNT(dv.id) as value_count
            FROM accounting_dimensions d
            LEFT JOIN accounting_dimension_values dv ON d.id = dv.dimension_id AND dv.is_active = true
            WHERE d.is_active = true
            GROUP BY d.id, d.code, d.name, d.dimension_type
            ORDER BY d.code
        """))

        print("\nActive Dimensions with Value Counts:")
        for row in result:
            print(f"  {row.code:10} | {row.name:30} | Type: {row.dimension_type:15} | Values: {row.value_count}")

        print("\n✅ Dimensional data seeding completed successfully!")
        print("\nNext steps:")
        print("1. Refresh the purchases page in your browser")
        print("2. Open browser console and check for 'Cost Centers loaded: X' messages")
        print("3. Open the New Purchase modal and verify dropdowns are populated")

    except Exception as e:
        print(f"\n❌ Error seeding dimensional data: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

    return True


if __name__ == '__main__':
    success = seed_dimensional_data()
    sys.exit(0 if success else 1)
