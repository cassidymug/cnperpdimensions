"""
Migration script to enhance landed costs with proper accounting dimensions and IFRS tagging.

This adds:
1. Dimensional accounting fields (cost center, project, department)
2. IFRS tags for proper financial reporting
3. Invoice/receipt tracking for duties and taxes
4. GL account mapping for different cost types
5. Separate classification for cost types
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import engine

def enhance_landed_costs():
    """Add accounting dimensions and IFRS tags to landed costs"""

    print("=" * 70)
    print("Enhancing Landed Costs with Accounting Dimensions & IFRS Tags")
    print("=" * 70)

    with engine.connect() as conn:
        # Check existing columns in landed_costs table
        check_lc_sql = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'landed_costs'
            ORDER BY column_name
        """)

        existing_lc_cols = conn.execute(check_lc_sql).fetchall()
        existing_lc_names = [row[0] for row in existing_lc_cols]

        print(f"\n[LANDED_COSTS] Current columns: {len(existing_lc_names)}")

        # Define new columns for landed_costs table
        landed_cost_columns = {
            'branch_id': {
                'type': 'VARCHAR NULL',
                'fk_table': 'branches',
                'description': 'Branch where landed cost was incurred'
            },
            'cost_center_id': {
                'type': 'VARCHAR NULL',
                'fk_table': 'accounting_dimension_values',
                'description': 'Cost center for landed cost allocation'
            },
            'project_id': {
                'type': 'VARCHAR NULL',
                'fk_table': 'accounting_dimension_values',
                'description': 'Project for landed cost tracking'
            },
            'department_id': {
                'type': 'VARCHAR NULL',
                'fk_table': 'accounting_dimension_values',
                'description': 'Department responsible for landed cost'
            },
            'invoice_number': {
                'type': 'VARCHAR(100) NULL',
                'fk_table': None,
                'description': 'Invoice/receipt number for the landed cost'
            },
            'supplier_invoice_date': {
                'type': 'DATE NULL',
                'fk_table': None,
                'description': 'Date on the supplier invoice'
            },
            'payment_due_date': {
                'type': 'DATE NULL',
                'fk_table': None,
                'description': 'When payment is due for this landed cost'
            },
            'paid_status': {
                'type': "VARCHAR(20) DEFAULT 'unpaid' NOT NULL",
                'fk_table': None,
                'description': 'Payment status: unpaid, partial, paid'
            },
            'amount_paid': {
                'type': 'NUMERIC(15, 2) DEFAULT 0.0',
                'fk_table': None,
                'description': 'Amount already paid for this landed cost'
            },
            'payment_account_id': {
                'type': 'VARCHAR NULL',
                'fk_table': 'accounting_codes',
                'description': 'GL account used for payment'
            }
        }

        lc_cols_to_add = {
            col: config for col, config in landed_cost_columns.items()
            if col not in existing_lc_names
        }

        if lc_cols_to_add:
            print(f"\n[LANDED_COSTS] Adding {len(lc_cols_to_add)} columns:")
            for col_name, config in lc_cols_to_add.items():
                print(f"  - {col_name}: {config['description']}")

                add_col_sql = text(f"""
                    ALTER TABLE landed_costs
                    ADD COLUMN IF NOT EXISTS {col_name} {config['type']}
                """)
                conn.execute(add_col_sql)

                if config['fk_table']:
                    fk_name = f"fk_landed_costs_{col_name}"
                    add_fk_sql = text(f"""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.table_constraints
                                WHERE constraint_name = '{fk_name}'
                            ) THEN
                                ALTER TABLE landed_costs
                                ADD CONSTRAINT {fk_name}
                                FOREIGN KEY ({col_name})
                                REFERENCES {config['fk_table']}(id)
                                ON DELETE SET NULL;
                            END IF;
                        END $$;
                    """)
                    conn.execute(add_fk_sql)
                    print(f"    ✅ Added with FK to {config['fk_table']}")
                else:
                    print(f"    ✅ Added (no FK)")
        else:
            print("\n[LANDED_COSTS] ✅ All columns already exist")

        # Now enhance landed_cost_items table
        check_lci_sql = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'landed_cost_items'
            ORDER BY column_name
        """)

        existing_lci_cols = conn.execute(check_lci_sql).fetchall()
        existing_lci_names = [row[0] for row in existing_lci_cols]

        print(f"\n[LANDED_COST_ITEMS] Current columns: {len(existing_lci_names)}")

        # Define new columns for landed_cost_items table
        landed_cost_item_columns = {
            'cost_type': {
                'type': "VARCHAR(50) DEFAULT 'other' NOT NULL",
                'fk_table': None,
                'description': 'Type: freight, insurance, duty, customs, tax, handling, storage, other'
            },
            'ifrs_tag': {
                'type': 'VARCHAR(20) NULL',
                'fk_table': None,
                'description': 'IFRS reporting tag (e.g., E1 for operating costs, A2.1 for inventory)'
            },
            'gl_account_id': {
                'type': 'VARCHAR NULL',
                'fk_table': 'accounting_codes',
                'description': 'GL account for this specific cost'
            },
            'cost_center_id': {
                'type': 'VARCHAR NULL',
                'fk_table': 'accounting_dimension_values',
                'description': 'Cost center for this line item'
            },
            'project_id': {
                'type': 'VARCHAR NULL',
                'fk_table': 'accounting_dimension_values',
                'description': 'Project for this line item'
            },
            'department_id': {
                'type': 'VARCHAR NULL',
                'fk_table': 'accounting_dimension_values',
                'description': 'Department for this line item'
            },
            'invoice_number': {
                'type': 'VARCHAR(100) NULL',
                'fk_table': None,
                'description': 'Specific invoice number for this cost (e.g., customs duty invoice)'
            },
            'invoice_date': {
                'type': 'DATE NULL',
                'fk_table': None,
                'description': 'Date on the invoice for this specific cost'
            },
            'reference_number': {
                'type': 'VARCHAR(100) NULL',
                'fk_table': None,
                'description': 'Reference number (e.g., customs declaration number)'
            },
            'tax_rate': {
                'type': 'NUMERIC(5, 2) DEFAULT 0.0',
                'fk_table': None,
                'description': 'Tax rate applied if this is a tax cost'
            },
            'is_taxable': {
                'type': 'BOOLEAN DEFAULT FALSE',
                'fk_table': None,
                'description': 'Whether VAT applies to this landed cost'
            },
            'vat_amount': {
                'type': 'NUMERIC(15, 2) DEFAULT 0.0',
                'fk_table': None,
                'description': 'VAT amount on this cost'
            },
            'vat_account_id': {
                'type': 'VARCHAR NULL',
                'fk_table': 'accounting_codes',
                'description': 'VAT GL account if taxable'
            },
            'allocated_to_inventory': {
                'type': 'BOOLEAN DEFAULT FALSE',
                'fk_table': None,
                'description': 'Whether this cost has been allocated to inventory'
            },
            'notes': {
                'type': 'TEXT NULL',
                'fk_table': None,
                'description': 'Additional notes for this cost item'
            }
        }

        lci_cols_to_add = {
            col: config for col, config in landed_cost_item_columns.items()
            if col not in existing_lci_names
        }

        if lci_cols_to_add:
            print(f"\n[LANDED_COST_ITEMS] Adding {len(lci_cols_to_add)} columns:")
            for col_name, config in lci_cols_to_add.items():
                print(f"  - {col_name}: {config['description']}")

                add_col_sql = text(f"""
                    ALTER TABLE landed_cost_items
                    ADD COLUMN IF NOT EXISTS {col_name} {config['type']}
                """)
                conn.execute(add_col_sql)

                if config['fk_table']:
                    fk_name = f"fk_landed_cost_items_{col_name}"
                    add_fk_sql = text(f"""
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1 FROM information_schema.table_constraints
                                WHERE constraint_name = '{fk_name}'
                            ) THEN
                                ALTER TABLE landed_cost_items
                                ADD CONSTRAINT {fk_name}
                                FOREIGN KEY ({col_name})
                                REFERENCES {config['fk_table']}(id)
                                ON DELETE SET NULL;
                            END IF;
                        END $$;
                    """)
                    conn.execute(add_fk_sql)
                    print(f"    ✅ Added with FK to {config['fk_table']}")
                else:
                    print(f"    ✅ Added (no FK)")
        else:
            print("\n[LANDED_COST_ITEMS] ✅ All columns already exist")

        # Add indexes for frequently queried columns
        print("\n[INDEXES] Creating indexes for performance...")

        indexes = [
            ("ix_landed_costs_branch_id", "landed_costs", "branch_id"),
            ("ix_landed_costs_cost_center_id", "landed_costs", "cost_center_id"),
            ("ix_landed_costs_paid_status", "landed_costs", "paid_status"),
            ("ix_landed_cost_items_cost_type", "landed_cost_items", "cost_type"),
            ("ix_landed_cost_items_ifrs_tag", "landed_cost_items", "ifrs_tag"),
            ("ix_landed_cost_items_gl_account_id", "landed_cost_items", "gl_account_id"),
        ]

        for index_name, table_name, column_name in indexes:
            # Check if column exists first
            check_col = text(f"""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = '{table_name}' AND column_name = '{column_name}'
            """)
            col_exists = conn.execute(check_col).fetchone()

            if col_exists:
                create_idx_sql = text(f"""
                    CREATE INDEX IF NOT EXISTS {index_name}
                    ON {table_name}({column_name})
                """)
                conn.execute(create_idx_sql)
                print(f"  ✅ {index_name}")

        conn.commit()

        # Verification
        print("\n" + "=" * 70)
        print("VERIFICATION - New Columns Added")
        print("=" * 70)

        # Verify landed_costs
        verify_lc_sql = text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'landed_costs'
            AND column_name IN ('branch_id', 'cost_center_id', 'project_id', 'department_id',
                               'invoice_number', 'supplier_invoice_date', 'payment_due_date',
                               'paid_status', 'amount_paid', 'payment_account_id')
            ORDER BY column_name
        """)

        lc_result = conn.execute(verify_lc_sql).fetchall()

        print("\n[LANDED_COSTS] Accounting columns:")
        for row in lc_result:
            print(f"  ✓ {row[0]}: {row[1]} (nullable: {row[2]})")

        # Verify landed_cost_items
        verify_lci_sql = text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'landed_cost_items'
            AND column_name IN ('cost_type', 'ifrs_tag', 'gl_account_id', 'cost_center_id',
                               'project_id', 'department_id', 'invoice_number', 'invoice_date',
                               'reference_number', 'tax_rate', 'is_taxable', 'vat_amount',
                               'vat_account_id', 'allocated_to_inventory', 'notes')
            ORDER BY column_name
        """)

        lci_result = conn.execute(verify_lci_sql).fetchall()

        print("\n[LANDED_COST_ITEMS] Enhanced accounting columns:")
        for row in lci_result:
            print(f"  ✓ {row[0]}: {row[1]} (nullable: {row[2]})")

        print("\n" + "=" * 70)
        print("✅ Landed Costs Enhancement Completed Successfully!")
        print("=" * 70)
        print("\nYou can now:")
        print("  • Tag each landed cost item with IFRS reporting tags")
        print("  • Assign dimensional accounting (cost center, project, dept)")
        print("  • Track invoice numbers for duties, taxes, freight separately")
        print("  • Map each cost to specific GL accounts")
        print("  • Handle VAT on landed costs")
        print("  • Track payment status and amounts")
        print("  • Classify costs by type (duty, tax, freight, insurance, etc.)")
        print("=" * 70)

if __name__ == "__main__":
    try:
        enhance_landed_costs()
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
