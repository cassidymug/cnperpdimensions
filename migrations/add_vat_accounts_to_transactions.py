"""
Migration: Add VAT account fields to Sales and Purchases
This migration adds input_vat_account_id and output_vat_account_id fields to
sales and purchases tables, and vat_account_id to sale_items and purchase_items
tables for proper VAT accounting.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import engine


def run_migration():
    """Execute the migration"""
    print("=" * 80)
    print("ADDING VAT ACCOUNT FIELDS TO SALES AND PURCHASES")
    print("=" * 80)
    print("\nThis migration will add:")
    print("  - output_vat_account_id to sales table (FK to accounting_codes)")
    print("  - vat_account_id to sale_items table (FK to accounting_codes)")
    print("  - input_vat_account_id to purchases table (FK to accounting_codes)")
    print("  - vat_account_id to purchase_items table (FK to accounting_codes)")
    print("\n" + "=" * 80)

    with engine.connect() as conn:
        # Add output_vat_account_id to sales
        print("\n[1/4] Adding output_vat_account_id to sales table...")
        conn.execute(text("""
            ALTER TABLE sales
            ADD COLUMN IF NOT EXISTS output_vat_account_id VARCHAR(36);
        """))

        print("[1/4] Adding foreign key constraint for sales.output_vat_account_id...")
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE constraint_name = 'fk_sales_output_vat_account_id'
                ) THEN
                    ALTER TABLE sales
                    ADD CONSTRAINT fk_sales_output_vat_account_id
                    FOREIGN KEY (output_vat_account_id)
                    REFERENCES accounting_codes(id)
                    ON DELETE SET NULL;
                END IF;
            END $$;
        """))

        # Add vat_account_id to sale_items
        print("\n[2/4] Adding vat_account_id to sale_items table...")
        conn.execute(text("""
            ALTER TABLE sale_items
            ADD COLUMN IF NOT EXISTS vat_account_id VARCHAR(36);
        """))

        print("[2/4] Adding foreign key constraint for sale_items.vat_account_id...")
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE constraint_name = 'fk_sale_items_vat_account_id'
                ) THEN
                    ALTER TABLE sale_items
                    ADD CONSTRAINT fk_sale_items_vat_account_id
                    FOREIGN KEY (vat_account_id)
                    REFERENCES accounting_codes(id)
                    ON DELETE SET NULL;
                END IF;
            END $$;
        """))

        # Add input_vat_account_id to purchases
        print("\n[3/4] Adding input_vat_account_id to purchases table...")
        conn.execute(text("""
            ALTER TABLE purchases
            ADD COLUMN IF NOT EXISTS input_vat_account_id VARCHAR(36);
        """))

        print("[3/4] Adding foreign key constraint for purchases.input_vat_account_id...")
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE constraint_name = 'fk_purchases_input_vat_account_id'
                ) THEN
                    ALTER TABLE purchases
                    ADD CONSTRAINT fk_purchases_input_vat_account_id
                    FOREIGN KEY (input_vat_account_id)
                    REFERENCES accounting_codes(id)
                    ON DELETE SET NULL;
                END IF;
            END $$;
        """))

        # Add vat_account_id to purchase_items
        print("\n[4/4] Adding vat_account_id to purchase_items table...")
        conn.execute(text("""
            ALTER TABLE purchase_items
            ADD COLUMN IF NOT EXISTS vat_account_id VARCHAR(36);
        """))

        print("[4/4] Adding foreign key constraint for purchase_items.vat_account_id...")
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints
                    WHERE constraint_name = 'fk_purchase_items_vat_account_id'
                ) THEN
                    ALTER TABLE purchase_items
                    ADD CONSTRAINT fk_purchase_items_vat_account_id
                    FOREIGN KEY (vat_account_id)
                    REFERENCES accounting_codes(id)
                    ON DELETE SET NULL;
                END IF;
            END $$;
        """))

        conn.commit()

    print("\n" + "=" * 80)
    print("[SUCCESS] VAT account fields added successfully!")
    print("\nNew fields created:")
    print("  ✓ sales.output_vat_account_id")
    print("  ✓ sale_items.vat_account_id")
    print("  ✓ purchases.input_vat_account_id")
    print("  ✓ purchase_items.vat_account_id")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    run_migration()
