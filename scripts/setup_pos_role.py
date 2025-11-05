"""
Setup POS User Role with Limited Permissions

This script creates a POS-only user role that:
1. Can only access the POS system
2. Cannot see the main navigation bar
3. Has restricted permissions to only POS-related operations
"""

from app.core.database import SessionLocal
from app.models.role import Role, Permission, RolePermission
from app.models.user import User
from sqlalchemy import text
import uuid

def setup_pos_role():
    db = SessionLocal()

    try:
        print("\n" + "="*80)
        print("POS USER ROLE SETUP")
        print("="*80 + "\n")

        # Check if pos_user role already exists
        existing_role = db.query(Role).filter(Role.name == 'pos_user').first()
        if existing_role:
            print(f"✓ POS User role already exists (ID: {existing_role.id})")
            pos_role = existing_role
        else:
            # Create POS User role
            pos_role = Role(
                id=str(uuid.uuid4()),
                name='pos_user',
                description='Point of Sale User - Can only access POS system with limited functionality',
                is_system_role=True,  # System role cannot be deleted
                is_active=True
            )
            db.add(pos_role)
            db.flush()
            print(f"✓ Created POS User role (ID: {pos_role.id})")

        # Define POS-only permissions
        pos_permissions = [
            {
                'name': 'pos.access',
                'description': 'Access the POS system',
                'module': 'pos',
                'action': 'access',
                'resource': 'pos_system'
            },
            {
                'name': 'pos.record_sale',
                'description': 'Record sales transactions',
                'module': 'pos',
                'action': 'record_sale',
                'resource': 'sales'
            },
            {
                'name': 'pos.view_products',
                'description': 'View products in POS',
                'module': 'pos',
                'action': 'view',
                'resource': 'products'
            },
            {
                'name': 'pos.search_customers',
                'description': 'Search and select customers',
                'module': 'pos',
                'action': 'search',
                'resource': 'customers'
            },
            {
                'name': 'pos.print_receipt',
                'description': 'Print sales receipts',
                'module': 'pos',
                'action': 'print',
                'resource': 'receipts'
            }
        ]

        created_permissions = []
        existing_permissions = []

        for perm_data in pos_permissions:
            # Check if permission already exists
            existing_perm = db.query(Permission).filter(
                Permission.name == perm_data['name']
            ).first()

            if existing_perm:
                existing_permissions.append(existing_perm)
                print(f"  • Found existing permission: {perm_data['name']}")
            else:
                # Create permission
                new_perm = Permission(
                    id=str(uuid.uuid4()),
                    **perm_data
                )
                db.add(new_perm)
                db.flush()
                created_permissions.append(new_perm)
                print(f"  + Created permission: {perm_data['name']}")

        db.commit()

        all_permissions = created_permissions + existing_permissions

        # Assign permissions to POS role (remove old ones first)
        db.query(RolePermission).filter(RolePermission.role_id == pos_role.id).delete()

        for perm in all_permissions:
            role_perm = RolePermission(
                id=str(uuid.uuid4()),
                role_id=pos_role.id,
                permission_id=perm.id
            )
            db.add(role_perm)

        db.commit()

        print(f"\n✓ Assigned {len(all_permissions)} permissions to POS User role")

        # Update existing users with 'pos_user' role to use the new role_id
        users = db.query(User).filter(User.role == 'pos_user').all()
        updated_count = 0
        for user in users:
            if user.role_id != pos_role.id:
                user.role_id = pos_role.id
                updated_count += 1

        if updated_count > 0:
            db.commit()
            print(f"✓ Updated {updated_count} existing POS users to use new role_id")

        # Summary
        print("\n" + "="*80)
        print("SETUP COMPLETE")
        print("="*80)
        print(f"\nRole Created/Updated: {pos_role.name}")
        print(f"Permissions Assigned: {len(all_permissions)}")
        print(f"Users Updated: {updated_count}")

        print("\n📋 Permissions Summary:")
        for perm in all_permissions:
            print(f"  • {perm.name} - {perm.description}")

        print("\n🔐 Access Control Rules:")
        print("  ✓ POS users can ONLY access /static/pos.html")
        print("  ✓ Navigation bar will be hidden for POS users")
        print("  ✓ Direct URL access to other pages will redirect to POS")
        print("  ✓ POS users cannot access admin, reports, or settings pages")

        print("\n💡 Usage:")
        print("  1. Create a user with role='pos_user' or role_id='{}'".format(pos_role.id))
        print("  2. User will be automatically redirected to POS on login")
        print("  3. User can only access POS-related functionality")

        print("\n" + "="*80 + "\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    setup_pos_role()
