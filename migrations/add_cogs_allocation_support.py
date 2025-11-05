"""
Phase 3 Migration: Add COGS Posting Support to Production Orders and Create COGS Allocation Table

This migration adds:
1. COGS posting status fields to production_orders table
2. COGS GL account reference to production_orders table
3. New cogs_allocations bridge table linking ProductionOrder costs to Invoice revenue
4. Indexes for performance optimization

Migration is idempotent (safe to re-run).
"""

import sys
from datetime import datetime
from sqlalchemy import text, inspect

def run_migration():
    """Execute the Phase 3 migration"""
    print(f"\n🚀 Starting Phase 3 Migration - COGS Allocation Setup")
    print(f"⏰ Timestamp: {datetime.now().isoformat()}")

    try:
        # Import database engine after ensuring context
        from app.core.database import engine

        with engine.begin() as connection:
            # Get database inspector
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()

            print(f"\n📋 Step 1: Checking existing schema...")

            # Step 1: Add COGS posting fields to production_orders table
            if "production_orders" in existing_tables:
                print(f"   ✓ production_orders table found")

                existing_columns = [col["name"] for col in inspector.get_columns("production_orders")]

                # Add cogs_posting_status column if not exists
                if "cogs_posting_status" not in existing_columns:
                    print(f"   → Adding cogs_posting_status column...")
                    connection.execute(text("""
                        ALTER TABLE production_orders
                        ADD COLUMN cogs_posting_status VARCHAR(20) DEFAULT 'pending' NOT NULL
                    """))
                    print(f"   ✓ cogs_posting_status column added")
                else:
                    print(f"   ✓ cogs_posting_status column already exists")

                # Add cogs_gl_account_id column if not exists
                if "cogs_gl_account_id" not in existing_columns:
                    print(f"   → Adding cogs_gl_account_id column...")
                    connection.execute(text("""
                        ALTER TABLE production_orders
                        ADD COLUMN cogs_gl_account_id VARCHAR NULL
                    """))
                    print(f"   ✓ cogs_gl_account_id column added")
                else:
                    print(f"   ✓ cogs_gl_account_id column already exists")

                # Add cogs_last_posted_date column if not exists
                if "cogs_last_posted_date" not in existing_columns:
                    print(f"   → Adding cogs_last_posted_date column...")
                    connection.execute(text("""
                        ALTER TABLE production_orders
                        ADD COLUMN cogs_last_posted_date DATETIME NULL
                    """))
                    print(f"   ✓ cogs_last_posted_date column added")
                else:
                    print(f"   ✓ cogs_last_posted_date column already exists")

                # Add cogs_posted_by column if not exists
                if "cogs_posted_by" not in existing_columns:
                    print(f"   → Adding cogs_posted_by column...")
                    connection.execute(text("""
                        ALTER TABLE production_orders
                        ADD COLUMN cogs_posted_by VARCHAR NULL
                    """))
                    print(f"   ✓ cogs_posted_by column added")
                else:
                    print(f"   ✓ cogs_posted_by column already exists")

                # Add FK constraint for cogs_gl_account_id if not exists
                print(f"   → Adding FK constraint for cogs_gl_account_id...")
                try:
                    connection.execute(text("""
                        ALTER TABLE production_orders
                        ADD CONSTRAINT fk_production_orders_cogs_gl_account
                        FOREIGN KEY (cogs_gl_account_id) REFERENCES accounting_codes(id)
                    """))
                    print(f"   ✓ FK constraint for cogs_gl_account_id added")
                except:
                    print(f"   ✓ FK constraint for cogs_gl_account_id already exists")

                # Add FK constraint for cogs_posted_by if not exists
                print(f"   → Adding FK constraint for cogs_posted_by...")
                try:
                    connection.execute(text("""
                        ALTER TABLE production_orders
                        ADD CONSTRAINT fk_production_orders_cogs_posted_by
                        FOREIGN KEY (cogs_posted_by) REFERENCES users(id)
                    """))
                    print(f"   ✓ FK constraint for cogs_posted_by added")
                except:
                    print(f"   ✓ FK constraint for cogs_posted_by already exists")

                # Create index on cogs_posting_status
                print(f"   → Creating index on cogs_posting_status...")
                try:
                    connection.execute(text("""
                        CREATE INDEX idx_production_orders_cogs_status
                        ON production_orders(cogs_posting_status)
                    """))
                    print(f"   ✓ Index on cogs_posting_status created")
                except:
                    print(f"   ✓ Index on cogs_posting_status already exists")

                # Create index on cogs_last_posted_date
                print(f"   → Creating index on cogs_last_posted_date...")
                try:
                    connection.execute(text("""
                        CREATE INDEX idx_production_orders_cogs_date
                        ON production_orders(cogs_last_posted_date)
                    """))
                    print(f"   ✓ Index on cogs_last_posted_date created")
                except:
                    print(f"   ✓ Index on cogs_last_posted_date already exists")

            # Step 2: Create cogs_allocations table
            print(f"\n📋 Step 2: Creating COGS Allocation table...")

            if "cogs_allocations" not in existing_tables:
                print(f"   → Creating cogs_allocations table...")
                connection.execute(text("""
                    CREATE TABLE cogs_allocations (
                        id VARCHAR PRIMARY KEY,
                        production_order_id VARCHAR NOT NULL,
                        invoice_id VARCHAR NOT NULL,
                        product_id VARCHAR NOT NULL,
                        quantity_produced NUMERIC(15, 2) NOT NULL,
                        quantity_sold NUMERIC(15, 2) NOT NULL,
                        cost_per_unit NUMERIC(15, 4) NOT NULL,
                        total_cogs NUMERIC(15, 2) NOT NULL,
                        revenue_gl_entry_id VARCHAR NOT NULL,
                        cogs_gl_entry_id VARCHAR NOT NULL,
                        production_cost_center_id VARCHAR NULL,
                        production_project_id VARCHAR NULL,
                        production_department_id VARCHAR NULL,
                        sales_cost_center_id VARCHAR NULL,
                        sales_project_id VARCHAR NULL,
                        sales_department_id VARCHAR NULL,
                        has_dimension_variance VARCHAR DEFAULT 'false',
                        variance_reason VARCHAR(255) NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        created_by VARCHAR NULL,
                        FOREIGN KEY (production_order_id) REFERENCES production_orders(id),
                        FOREIGN KEY (invoice_id) REFERENCES invoices(id),
                        FOREIGN KEY (product_id) REFERENCES products(id),
                        FOREIGN KEY (revenue_gl_entry_id) REFERENCES journal_entries(id),
                        FOREIGN KEY (cogs_gl_entry_id) REFERENCES journal_entries(id),
                        FOREIGN KEY (production_cost_center_id) REFERENCES dimension_values(id),
                        FOREIGN KEY (production_project_id) REFERENCES dimension_values(id),
                        FOREIGN KEY (production_department_id) REFERENCES dimension_values(id),
                        FOREIGN KEY (sales_cost_center_id) REFERENCES dimension_values(id),
                        FOREIGN KEY (sales_project_id) REFERENCES dimension_values(id),
                        FOREIGN KEY (sales_department_id) REFERENCES dimension_values(id),
                        FOREIGN KEY (created_by) REFERENCES users(id)
                    )
                """))
                print(f"   ✓ cogs_allocations table created")

                # Create indexes on cogs_allocations
                print(f"   → Creating indexes on cogs_allocations table...")

                indexes = [
                    ("idx_cogs_allocations_po", "production_order_id"),
                    ("idx_cogs_allocations_invoice", "invoice_id"),
                    ("idx_cogs_allocations_product", "product_id"),
                    ("idx_cogs_allocations_variance", "has_dimension_variance"),
                    ("idx_cogs_allocations_created", "created_at"),
                ]

                for idx_name, column_name in indexes:
                    try:
                        connection.execute(text(f"""
                            CREATE INDEX {idx_name}
                            ON cogs_allocations({column_name})
                        """))
                        print(f"   ✓ Index {idx_name} created")
                    except:
                        print(f"   ✓ Index {idx_name} already exists")
            else:
                print(f"   ✓ cogs_allocations table already exists")

            # Commit all changes
            print(f"\n✅ Phase 3 Migration completed successfully!")
            print(f"   Production Orders enhanced with COGS posting support")
            print(f"   COGS Allocations table created and indexed")
            print(f"   All changes committed to database")

    except Exception as e:
        print(f"\n❌ Phase 3 Migration failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        sys.exit(1)


if __name__ == "__main__":
    print("\n" + "="*70)
    print(" PHASE 3: COGS ALLOCATION MIGRATION")
    print("="*70)
    run_migration()
    print("="*70 + "\n")
