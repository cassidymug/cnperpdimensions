"""
Migration script to add dimensional accounting columns to purchases table
These columns are already in the SQLAlchemy model but missing from the database.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import engine

def add_dimensional_columns():
    """Add dimensional accounting columns to purchases table"""

    print("=" * 60)
    print("Adding accounting columns to purchases table")
    print("=" * 60)

    with engine.connect() as conn:
        # Check if columns already exist
        all_columns_to_check = [
            'cost_center_id', 'project_id', 'department_id',
            'expense_account_id', 'payable_account_id',
            'posting_status', 'last_posted_date', 'posted_by'
        ]

        check_sql = text(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'purchases'
            AND column_name IN ({','.join(f"'{col}'" for col in all_columns_to_check)})
        """)

        existing_cols = conn.execute(check_sql).fetchall()
        existing_col_names = [row[0] for row in existing_cols]

        print(f"\nExisting accounting columns: {existing_col_names}")

        # Define columns to add with their types and constraints
        columns_config = {
            'cost_center_id': {
                'type': 'VARCHAR NULL',
                'fk_table': 'accounting_dimension_values',
                'add_index': True
            },
            'project_id': {
                'type': 'VARCHAR NULL',
                'fk_table': 'accounting_dimension_values',
                'add_index': False
            },
            'department_id': {
                'type': 'VARCHAR NULL',
                'fk_table': 'accounting_dimension_values',
                'add_index': False
            },
            'expense_account_id': {
                'type': 'VARCHAR NULL',
                'fk_table': 'accounting_codes',
                'add_index': False
            },
            'payable_account_id': {
                'type': 'VARCHAR NULL',
                'fk_table': 'accounting_codes',
                'add_index': False
            },
            'posting_status': {
                'type': "VARCHAR(20) DEFAULT 'draft' NOT NULL",
                'fk_table': None,
                'add_index': True
            },
            'last_posted_date': {
                'type': 'TIMESTAMP NULL',
                'fk_table': None,
                'add_index': False
            },
            'posted_by': {
                'type': 'VARCHAR NULL',
                'fk_table': 'users',
                'add_index': False
            }
        }

        columns_to_add = {
            col: config for col, config in columns_config.items()
            if col not in existing_col_names
        }

        if not columns_to_add:
            print("\n✅ All accounting columns already exist!")
            return

        print(f"\nColumns to add: {list(columns_to_add.keys())}")

        # Add missing columns
        for col_name, config in columns_to_add.items():
            print(f"\nAdding column: {col_name} ({config['type']})")

            add_col_sql = text(f"""
                ALTER TABLE purchases
                ADD COLUMN IF NOT EXISTS {col_name} {config['type']}
            """)
            conn.execute(add_col_sql)

            # Add foreign key constraint if specified
            if config['fk_table']:
                fk_name = f"fk_purchases_{col_name}"
                add_fk_sql = text(f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.table_constraints
                            WHERE constraint_name = '{fk_name}'
                        ) THEN
                            ALTER TABLE purchases
                            ADD CONSTRAINT {fk_name}
                            FOREIGN KEY ({col_name})
                            REFERENCES {config['fk_table']}(id)
                            ON DELETE SET NULL;
                        END IF;
                    END $$;
                """)
                conn.execute(add_fk_sql)
                print(f"✅ Added {col_name} with FK to {config['fk_table']}")
            else:
                print(f"✅ Added {col_name} (no FK)")

            # Add index if specified
            if config['add_index']:
                index_name = f"ix_purchases_{col_name}"
                print(f"  Adding index {index_name}...")
                create_index_sql = text(f"""
                    CREATE INDEX IF NOT EXISTS {index_name}
                    ON purchases({col_name})
                """)
                conn.execute(create_index_sql)
                print(f"  ✅ Index created")

        conn.commit()

        # Verify columns were added
        verify_sql = text(f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'purchases'
            AND column_name IN ({','.join(f"'{col}'" for col in all_columns_to_check)})
            ORDER BY column_name
        """)

        result = conn.execute(verify_sql).fetchall()

        print("\n" + "=" * 60)
        print("Verification - Accounting columns in purchases table:")
        print("=" * 60)
        for row in result:
            default_val = f" (default: {row[3]})" if row[3] else ""
            print(f"  {row[0]}: {row[1]} (nullable: {row[2]}){default_val}")

        print("\n✅ Migration completed successfully!")
        print("=" * 60)

if __name__ == "__main__":
    try:
        add_dimensional_columns()
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
