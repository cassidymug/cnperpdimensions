"""
Alembic Migration Script - Add Workflow Tables

Run with:
    alembic revision --autogenerate -m "Add workflow tables"
    alembic upgrade head

Or use this standalone script:
    python migrations/create_workflow_tables.py
"""
from sqlalchemy import text
from app.core.database import engine


def create_workflow_tables():
    """Create all workflow-related tables"""

    with engine.connect() as conn:
        # Enable UUID extension if not exists
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"))

        # Create workflow_definitions table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS workflow_definitions (
                id VARCHAR PRIMARY KEY DEFAULT uuid_generate_v4()::text,
                name VARCHAR NOT NULL,
                code VARCHAR UNIQUE NOT NULL,
                description TEXT,
                module VARCHAR NOT NULL,
                is_active BOOLEAN DEFAULT TRUE NOT NULL,
                is_default BOOLEAN DEFAULT FALSE,
                requires_approval BOOLEAN DEFAULT TRUE,
                auto_submit BOOLEAN DEFAULT FALSE,
                approval_threshold_amount INTEGER DEFAULT 0,
                max_approval_levels INTEGER DEFAULT 3,
                created_by VARCHAR REFERENCES users(id),
                branch_id VARCHAR REFERENCES branches(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_workflow_def_module ON workflow_definitions(module);
            CREATE INDEX IF NOT EXISTS idx_workflow_def_code ON workflow_definitions(code);
        """))

        # Create workflow_states table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS workflow_states (
                id VARCHAR PRIMARY KEY DEFAULT uuid_generate_v4()::text,
                workflow_definition_id VARCHAR NOT NULL REFERENCES workflow_definitions(id) ON DELETE CASCADE,
                name VARCHAR NOT NULL,
                code VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                description TEXT,
                is_initial BOOLEAN DEFAULT FALSE,
                is_final BOOLEAN DEFAULT FALSE,
                requires_approval BOOLEAN DEFAULT FALSE,
                allowed_roles JSON,
                notified_roles JSON,
                display_order INTEGER DEFAULT 0,
                color VARCHAR DEFAULT '#3b82f6',
                icon VARCHAR DEFAULT 'circle',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_workflow_state_def ON workflow_states(workflow_definition_id);
            CREATE INDEX IF NOT EXISTS idx_workflow_state_code ON workflow_states(code);
        """))

        # Create workflow_transitions table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS workflow_transitions (
                id VARCHAR PRIMARY KEY DEFAULT uuid_generate_v4()::text,
                workflow_definition_id VARCHAR NOT NULL REFERENCES workflow_definitions(id) ON DELETE CASCADE,
                from_state_id VARCHAR NOT NULL REFERENCES workflow_states(id) ON DELETE CASCADE,
                to_state_id VARCHAR NOT NULL REFERENCES workflow_states(id) ON DELETE CASCADE,
                name VARCHAR NOT NULL,
                action VARCHAR NOT NULL,
                description TEXT,
                allowed_roles JSON,
                required_permission VARCHAR,
                requires_comment BOOLEAN DEFAULT FALSE,
                requires_attachment BOOLEAN DEFAULT FALSE,
                condition_script TEXT,
                notify_on_transition BOOLEAN DEFAULT TRUE,
                notification_template VARCHAR,
                button_label VARCHAR,
                button_color VARCHAR DEFAULT 'primary',
                display_order INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_workflow_trans_def ON workflow_transitions(workflow_definition_id);
            CREATE INDEX IF NOT EXISTS idx_workflow_trans_from ON workflow_transitions(from_state_id);
            CREATE INDEX IF NOT EXISTS idx_workflow_trans_to ON workflow_transitions(to_state_id);
        """))

        # Create workflow_instances table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS workflow_instances (
                id VARCHAR PRIMARY KEY DEFAULT uuid_generate_v4()::text,
                workflow_definition_id VARCHAR NOT NULL REFERENCES workflow_definitions(id),
                current_state_id VARCHAR NOT NULL REFERENCES workflow_states(id),
                entity_type VARCHAR NOT NULL,
                entity_id VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                initiated_by VARCHAR NOT NULL REFERENCES users(id),
                initiated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                current_assignee VARCHAR REFERENCES users(id),
                completed_at TIMESTAMP,
                completed_by VARCHAR REFERENCES users(id),
                branch_id VARCHAR REFERENCES branches(id),
                priority VARCHAR DEFAULT 'normal',
                due_date TIMESTAMP,
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_workflow_inst_entity ON workflow_instances(entity_type, entity_id);
            CREATE INDEX IF NOT EXISTS idx_workflow_inst_status ON workflow_instances(status);
            CREATE INDEX IF NOT EXISTS idx_workflow_inst_assignee ON workflow_instances(current_assignee);
            CREATE INDEX IF NOT EXISTS idx_workflow_inst_state ON workflow_instances(current_state_id);
        """))

        # Create workflow_actions table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS workflow_actions (
                id VARCHAR PRIMARY KEY DEFAULT uuid_generate_v4()::text,
                workflow_instance_id VARCHAR NOT NULL REFERENCES workflow_instances(id) ON DELETE CASCADE,
                from_state_id VARCHAR REFERENCES workflow_states(id),
                to_state_id VARCHAR NOT NULL REFERENCES workflow_states(id),
                action VARCHAR NOT NULL,
                action_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                performed_by VARCHAR NOT NULL REFERENCES users(id),
                comment TEXT,
                reason VARCHAR,
                attachments JSON,
                reassigned_from VARCHAR REFERENCES users(id),
                reassigned_to VARCHAR REFERENCES users(id),
                ip_address VARCHAR,
                user_agent VARCHAR,
                duration_seconds INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_workflow_action_inst ON workflow_actions(workflow_instance_id);
            CREATE INDEX IF NOT EXISTS idx_workflow_action_date ON workflow_actions(action_date);
            CREATE INDEX IF NOT EXISTS idx_workflow_action_to_state ON workflow_actions(to_state_id);
        """))

        # Create workflow_notifications table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS workflow_notifications (
                id VARCHAR PRIMARY KEY DEFAULT uuid_generate_v4()::text,
                workflow_instance_id VARCHAR NOT NULL REFERENCES workflow_instances(id) ON DELETE CASCADE,
                workflow_action_id VARCHAR REFERENCES workflow_actions(id),
                recipient_user_id VARCHAR NOT NULL REFERENCES users(id),
                notification_type VARCHAR NOT NULL,
                subject VARCHAR,
                message TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                read_at TIMESTAMP,
                is_read BOOLEAN DEFAULT FALSE,
                delivery_status VARCHAR DEFAULT 'sent',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_workflow_notif_inst ON workflow_notifications(workflow_instance_id);
            CREATE INDEX IF NOT EXISTS idx_workflow_notif_recipient ON workflow_notifications(recipient_user_id);
            CREATE INDEX IF NOT EXISTS idx_workflow_notif_read ON workflow_notifications(is_read);
        """))

        conn.commit()
        print("✅ Workflow tables created successfully!")

        # Create sample workflows
        create_sample_workflows(conn)


def create_sample_workflows(conn):
    """Create sample workflow definitions"""

    print("\n📋 Creating sample workflows...")

    # Check if sample workflows already exist
    result = conn.execute(text(
        "SELECT COUNT(*) FROM workflow_definitions WHERE code IN ('PO_APPROVAL_3LEVEL', 'SALES_APPROVAL_2LEVEL')"
    ))
    existing_count = result.scalar()

    if existing_count > 0:
        print(f"⚠️  Sample workflows already exist (found {existing_count}). Skipping creation.")
        return

    # Create Purchase Order Approval Workflow
    print("\n1️⃣  Creating Purchase Order Approval (3-Level) workflow...")

    # Insert workflow definition
    result = conn.execute(text("""
        INSERT INTO workflow_definitions (name, code, module, description, is_active, is_default, max_approval_levels)
        VALUES ('Purchase Order Approval (3-Level)', 'PO_APPROVAL_3LEVEL', 'purchases',
                'Standard 3-level approval: Submitter → Manager → Finance Director', TRUE, TRUE, 3)
        RETURNING id
    """))
    po_workflow_id = result.fetchone()[0]

    # Create states
    conn.execute(text(f"""
        INSERT INTO workflow_states (workflow_definition_id, name, code, status, is_initial, is_final, display_order, color, icon) VALUES
        ('{po_workflow_id}', 'Draft', 'DRAFT', 'draft', TRUE, FALSE, 1, '#6b7280', 'file-earmark'),
        ('{po_workflow_id}', 'Pending Manager Approval', 'PENDING_MGR', 'pending_approval', FALSE, FALSE, 2, '#f59e0b', 'clock'),
        ('{po_workflow_id}', 'Pending Finance Approval', 'PENDING_FIN', 'pending_approval', FALSE, FALSE, 3, '#f59e0b', 'cash-stack'),
        ('{po_workflow_id}', 'Approved', 'APPROVED', 'approved', FALSE, TRUE, 4, '#10b981', 'check-circle'),
        ('{po_workflow_id}', 'Rejected', 'REJECTED', 'rejected', FALSE, TRUE, 5, '#ef4444', 'x-circle')
    """))

    # Get state IDs
    states = conn.execute(text(f"""
        SELECT id, code FROM workflow_states WHERE workflow_definition_id = '{po_workflow_id}'
    """)).fetchall()
    state_map = {code: id for id, code in states}

    # Create transitions
    conn.execute(text(f"""
        INSERT INTO workflow_transitions (workflow_definition_id, from_state_id, to_state_id, name, action, button_label, button_color, display_order) VALUES
        ('{po_workflow_id}', '{state_map['DRAFT']}', '{state_map['PENDING_MGR']}', 'Submit for Approval', 'submit', 'Submit', 'primary', 1),
        ('{po_workflow_id}', '{state_map['PENDING_MGR']}', '{state_map['PENDING_FIN']}', 'Manager Approval', 'approve', 'Approve', 'success', 1),
        ('{po_workflow_id}', '{state_map['PENDING_MGR']}', '{state_map['REJECTED']}', 'Manager Rejection', 'reject', 'Reject', 'danger', 2),
        ('{po_workflow_id}', '{state_map['PENDING_FIN']}', '{state_map['APPROVED']}', 'Finance Approval', 'approve', 'Approve', 'success', 1),
        ('{po_workflow_id}', '{state_map['PENDING_FIN']}', '{state_map['REJECTED']}', 'Finance Rejection', 'reject', 'Reject', 'danger', 2)
    """))

    print(f"   ✅ Created Purchase Order workflow (ID: {po_workflow_id})")

    # Create Sales Invoice Approval Workflow
    print("\n2️⃣  Creating Sales Invoice Approval (2-Level) workflow...")

    result = conn.execute(text("""
        INSERT INTO workflow_definitions (name, code, module, description, is_active, is_default, max_approval_levels)
        VALUES ('Sales Invoice Approval (2-Level)', 'SALES_APPROVAL_2LEVEL', 'sales',
                'Standard 2-level approval: Salesperson → Sales Manager', TRUE, TRUE, 2)
        RETURNING id
    """))
    sales_workflow_id = result.fetchone()[0]

    # Create states
    conn.execute(text(f"""
        INSERT INTO workflow_states (workflow_definition_id, name, code, status, is_initial, is_final, display_order, color, icon) VALUES
        ('{sales_workflow_id}', 'Draft', 'DRAFT', 'draft', TRUE, FALSE, 1, '#6b7280', 'file-earmark'),
        ('{sales_workflow_id}', 'Pending Sales Manager', 'PENDING_MGR', 'pending_approval', FALSE, FALSE, 2, '#f59e0b', 'clock'),
        ('{sales_workflow_id}', 'Approved', 'APPROVED', 'approved', FALSE, TRUE, 3, '#10b981', 'check-circle'),
        ('{sales_workflow_id}', 'Rejected', 'REJECTED', 'rejected', FALSE, TRUE, 4, '#ef4444', 'x-circle')
    """))

    # Get state IDs
    sales_states = conn.execute(text(f"""
        SELECT id, code FROM workflow_states WHERE workflow_definition_id = '{sales_workflow_id}'
    """)).fetchall()
    sales_state_map = {code: id for id, code in sales_states}

    # Create transitions
    conn.execute(text(f"""
        INSERT INTO workflow_transitions (workflow_definition_id, from_state_id, to_state_id, name, action, button_label, button_color, display_order) VALUES
        ('{sales_workflow_id}', '{sales_state_map['DRAFT']}', '{sales_state_map['PENDING_MGR']}', 'Submit for Approval', 'submit', 'Submit', 'primary', 1),
        ('{sales_workflow_id}', '{sales_state_map['PENDING_MGR']}', '{sales_state_map['APPROVED']}', 'Manager Approval', 'approve', 'Approve', 'success', 1),
        ('{sales_workflow_id}', '{sales_state_map['PENDING_MGR']}', '{sales_state_map['REJECTED']}', 'Manager Rejection', 'reject', 'Reject', 'danger', 2)
    """))

    print(f"   ✅ Created Sales Invoice workflow (ID: {sales_workflow_id})")

    conn.commit()
    print("\n✅ Sample workflows created successfully!")
    print("\n📚 Next steps:")
    print("   1. Configure role assignments for workflow states/transitions")
    print("   2. Integrate workflows into your modules (purchases, sales, etc.)")
    print("   3. View workflows at: http://localhost:8010/static/workflow-components.html")


if __name__ == "__main__":
    print("🚀 Creating workflow tables...")
    print("=" * 60)

    try:
        create_workflow_tables()
        print("\n" + "=" * 60)
        print("✅ Workflow system setup complete!")
        print("\n📖 Documentation:")
        print("   - Full Guide: docs/workflow-system-guide.md")
        print("   - Quick Ref:  docs/workflow-quick-reference.md")
        print("   - UI Demo:    app/static/workflow-components.html")

    except Exception as e:
        print(f"\n❌ Error creating workflow tables: {e}")
        import traceback
        traceback.print_exc()
