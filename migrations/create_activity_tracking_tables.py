"""
Database Migration: Create Activity Tracking and Permission Management Tables
Creates all necessary tables for comprehensive activity logging and permission management
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import engine


def create_activity_tracking_tables():
    """Create all activity tracking and permission management tables"""

    with engine.connect() as conn:
        print("Creating activity tracking tables...")

        # 1. Activity Logs Table
        print("  - Creating activity_logs table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS activity_logs (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR NOT NULL REFERENCES users(id),
                username VARCHAR NOT NULL,
                role_name VARCHAR,

                activity_type VARCHAR NOT NULL,
                module VARCHAR NOT NULL,
                action VARCHAR NOT NULL,
                description TEXT,

                entity_type VARCHAR,
                entity_id VARCHAR,
                entity_name VARCHAR,

                branch_id VARCHAR REFERENCES branches(id),
                branch_name VARCHAR,

                old_values JSONB,
                new_values JSONB,
                metadata JSONB,

                success BOOLEAN DEFAULT TRUE NOT NULL,
                error_message TEXT,
                severity VARCHAR DEFAULT 'info' NOT NULL,

                ip_address VARCHAR,
                user_agent VARCHAR,
                session_id VARCHAR,

                performed_at TIMESTAMP DEFAULT NOW() NOT NULL,
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW() NOT NULL
            )
        """))

        # Create indexes for activity_logs
        print("  - Creating indexes for activity_logs...")
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_activity_user_id ON activity_logs(user_id);
            CREATE INDEX IF NOT EXISTS idx_activity_module ON activity_logs(module);
            CREATE INDEX IF NOT EXISTS idx_activity_type ON activity_logs(activity_type);
            CREATE INDEX IF NOT EXISTS idx_activity_entity ON activity_logs(entity_type, entity_id);
            CREATE INDEX IF NOT EXISTS idx_activity_branch_date ON activity_logs(branch_id, performed_at);
            CREATE INDEX IF NOT EXISTS idx_activity_performed_at ON activity_logs(performed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_activity_user_module ON activity_logs(user_id, module);
            CREATE INDEX IF NOT EXISTS idx_activity_session ON activity_logs(session_id);
        """))

        # 2. Approval Logs Table
        print("  - Creating approval_logs table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS approval_logs (
                id VARCHAR PRIMARY KEY,

                approver_id VARCHAR NOT NULL REFERENCES users(id),
                approver_name VARCHAR NOT NULL,
                approver_role VARCHAR,

                entity_type VARCHAR NOT NULL,
                entity_id VARCHAR NOT NULL,
                entity_reference VARCHAR,

                workflow_id VARCHAR,
                from_state VARCHAR,
                to_state VARCHAR,

                action VARCHAR NOT NULL,
                decision VARCHAR NOT NULL,

                comments TEXT,
                attachments JSONB,

                on_behalf_of VARCHAR REFERENCES users(id),
                delegation_reason TEXT,

                approval_level VARCHAR,
                branch_id VARCHAR REFERENCES branches(id),
                metadata JSONB,

                approved_at TIMESTAMP DEFAULT NOW() NOT NULL,
                ip_address VARCHAR,

                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW() NOT NULL
            )
        """))

        # Create indexes for approval_logs
        print("  - Creating indexes for approval_logs...")
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_approval_approver ON approval_logs(approver_id);
            CREATE INDEX IF NOT EXISTS idx_approval_entity ON approval_logs(entity_type, entity_id);
            CREATE INDEX IF NOT EXISTS idx_approval_workflow ON approval_logs(workflow_id);
            CREATE INDEX IF NOT EXISTS idx_approval_approved_at ON approval_logs(approved_at DESC);
            CREATE INDEX IF NOT EXISTS idx_approval_user_date ON approval_logs(approver_id, approved_at);
        """))

        # 3. Permission Change Logs Table
        print("  - Creating permission_change_logs table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS permission_change_logs (
                id VARCHAR PRIMARY KEY,

                changed_by_id VARCHAR NOT NULL REFERENCES users(id),
                changed_by_name VARCHAR NOT NULL,

                target_user_id VARCHAR REFERENCES users(id),
                target_user_name VARCHAR,
                target_role_id VARCHAR REFERENCES roles(id),
                target_role_name VARCHAR,

                change_type VARCHAR NOT NULL,
                permission_id VARCHAR REFERENCES permissions(id),
                permission_name VARCHAR,

                old_value JSONB,
                new_value JSONB,
                reason TEXT,

                approved_by_id VARCHAR REFERENCES users(id),
                approved_by_name VARCHAR,
                approval_date TIMESTAMP,

                branch_id VARCHAR REFERENCES branches(id),
                metadata JSONB,

                changed_at TIMESTAMP DEFAULT NOW() NOT NULL,
                expires_at TIMESTAMP,
                ip_address VARCHAR,

                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW() NOT NULL
            )
        """))

        # Create indexes for permission_change_logs
        print("  - Creating indexes for permission_change_logs...")
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_permission_change_target_user ON permission_change_logs(target_user_id);
            CREATE INDEX IF NOT EXISTS idx_permission_change_target_role ON permission_change_logs(target_role_id);
            CREATE INDEX IF NOT EXISTS idx_permission_change_type ON permission_change_logs(change_type);
            CREATE INDEX IF NOT EXISTS idx_permission_change_date ON permission_change_logs(changed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_permission_change_target ON permission_change_logs(target_user_id, changed_at);
        """))

        # 4. User Sessions Table
        print("  - Creating user_sessions table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id VARCHAR PRIMARY KEY,

                user_id VARCHAR NOT NULL REFERENCES users(id),
                username VARCHAR NOT NULL,

                session_token VARCHAR UNIQUE NOT NULL,
                session_start TIMESTAMP DEFAULT NOW() NOT NULL,
                session_end TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE NOT NULL,

                ip_address VARCHAR,
                user_agent VARCHAR,
                login_method VARCHAR,

                last_activity TIMESTAMP DEFAULT NOW() NOT NULL,
                activity_count VARCHAR DEFAULT '0' NOT NULL,

                logout_reason VARCHAR,

                branch_id VARCHAR REFERENCES branches(id),
                metadata JSONB,

                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW() NOT NULL
            )
        """))

        # Create indexes for user_sessions
        print("  - Creating indexes for user_sessions...")
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_session_user ON user_sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_session_token ON user_sessions(session_token);
            CREATE INDEX IF NOT EXISTS idx_session_active ON user_sessions(is_active);
            CREATE INDEX IF NOT EXISTS idx_session_user_active ON user_sessions(user_id, is_active);
            CREATE INDEX IF NOT EXISTS idx_session_token_active ON user_sessions(session_token, is_active);
        """))

        # 5. Entity Access Logs Table
        print("  - Creating entity_access_logs table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS entity_access_logs (
                id VARCHAR PRIMARY KEY,

                user_id VARCHAR NOT NULL REFERENCES users(id),
                username VARCHAR NOT NULL,

                entity_type VARCHAR NOT NULL,
                entity_id VARCHAR NOT NULL,
                entity_name VARCHAR,

                access_method VARCHAR,
                module VARCHAR NOT NULL,

                branch_id VARCHAR REFERENCES branches(id),
                session_id VARCHAR,

                ip_address VARCHAR,
                user_agent VARCHAR,
                metadata JSONB,

                accessed_at TIMESTAMP DEFAULT NOW() NOT NULL,
                created_at TIMESTAMP DEFAULT NOW() NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW() NOT NULL
            )
        """))

        # Create indexes for entity_access_logs
        print("  - Creating indexes for entity_access_logs...")
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_access_user ON entity_access_logs(user_id);
            CREATE INDEX IF NOT EXISTS idx_access_entity ON entity_access_logs(entity_type, entity_id);
            CREATE INDEX IF NOT EXISTS idx_access_date ON entity_access_logs(accessed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_access_user_date ON entity_access_logs(user_id, accessed_at);
        """))

        conn.commit()
        print("✅ All activity tracking tables created successfully!")


def create_sample_data():
    """Create sample activity logs and permissions for testing"""

    with engine.connect() as conn:
        print("\nCreating sample data...")

        # Get a sample user
        result = conn.execute(text("SELECT id, username FROM users LIMIT 1"))
        user = result.fetchone()

        if not user:
            print("⚠️  No users found. Please create users first.")
            return

        user_id, username = user

        # Sample activity log
        print("  - Creating sample activity log...")
        conn.execute(text("""
            INSERT INTO activity_logs (
                id, user_id, username, activity_type, module, action,
                description, success, performed_at, created_at, updated_at
            ) VALUES (
                'sample-activity-001',
                :user_id,
                :username,
                'login',
                'users',
                'User Login',
                'User logged into the system',
                TRUE,
                NOW(),
                NOW(),
                NOW()
            )
            ON CONFLICT (id) DO NOTHING
        """), {"user_id": user_id, "username": username})

        # Sample permission definitions
        print("  - Creating sample permissions...")
        permissions_data = [
            ('perm-activity-read', 'View Activity Logs', 'audit', 'read', 'all'),
            ('perm-activity-export', 'Export Activity Logs', 'audit', 'export', 'all'),
            ('perm-roles-manage', 'Manage Roles', 'roles', 'manage', 'all'),
            ('perm-permissions-assign', 'Assign Permissions', 'permissions', 'assign', 'all'),
        ]

        for perm_id, name, module, action, resource in permissions_data:
            conn.execute(text("""
                INSERT INTO permissions (
                    id, name, module, action, resource,
                    created_at, updated_at
                ) VALUES (
                    :id, :name, :module, :action, :resource,
                    NOW(), NOW()
                )
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": perm_id,
                "name": name,
                "module": module,
                "action": action,
                "resource": resource
            })

        conn.commit()
        print("✅ Sample data created successfully!")


def main():
    """Main migration function"""
    print("=" * 60)
    print("Activity Tracking & Permission Management Migration")
    print("=" * 60)

    try:
        create_activity_tracking_tables()
        create_sample_data()

        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Review the created tables in your database")
        print("2. Update your models if needed")
        print("3. Test the activity logging functionality")
        print("4. Configure permissions for your roles")

    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
