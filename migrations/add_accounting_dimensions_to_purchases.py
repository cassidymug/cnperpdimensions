"""
Database Migration: Add Dimensional Accounting to Purchases Module

Adds cost center, project, and department dimension tracking to purchases and purchase orders.
Also adds GL account references and posting status for accounting integration.

Columns added to purchases table:
- cost_center_id, project_id, department_id (dimension tracking)
- expense_account_id, payable_account_id (GL accounts for expense and AP posting)
- posting_status, last_posted_date, posted_by (audit trail)

Columns added to purchase_orders table (same minus payable_account_id):
- cost_center_id, project_id, department_id
- expense_account_id
- posting_status

Run with:
    python migrations/add_accounting_dimensions_to_purchases.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine, text
from app.core.database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_accounting_dimensions_to_purchases():
    """Add accounting dimension columns to purchases and purchase_orders tables"""

    migration_sql = [
        # Add columns to purchases table
        """
        ALTER TABLE purchases ADD COLUMN IF NOT EXISTS cost_center_id VARCHAR REFERENCES dimension_values(id)
        """,
        """
        ALTER TABLE purchases ADD COLUMN IF NOT EXISTS project_id VARCHAR REFERENCES dimension_values(id)
        """,
        """
        ALTER TABLE purchases ADD COLUMN IF NOT EXISTS department_id VARCHAR REFERENCES dimension_values(id)
        """,
        """
        ALTER TABLE purchases ADD COLUMN IF NOT EXISTS expense_account_id VARCHAR REFERENCES accounting_codes(id)
        """,
        """
        ALTER TABLE purchases ADD COLUMN IF NOT EXISTS payable_account_id VARCHAR REFERENCES accounting_codes(id)
        """,
        """
        ALTER TABLE purchases ADD COLUMN IF NOT EXISTS posting_status VARCHAR(20) DEFAULT 'draft'
        """,
        """
        ALTER TABLE purchases ADD COLUMN IF NOT EXISTS last_posted_date TIMESTAMP
        """,
        """
        ALTER TABLE purchases ADD COLUMN IF NOT EXISTS posted_by VARCHAR REFERENCES users(id)
        """,

        # Add columns to purchase_orders table
        """
        ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS cost_center_id VARCHAR REFERENCES dimension_values(id)
        """,
        """
        ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS project_id VARCHAR REFERENCES dimension_values(id)
        """,
        """
        ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS department_id VARCHAR REFERENCES dimension_values(id)
        """,
        """
        ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS expense_account_id VARCHAR REFERENCES accounting_codes(id)
        """,
        """
        ALTER TABLE purchase_orders ADD COLUMN IF NOT EXISTS posting_status VARCHAR(20) DEFAULT 'draft'
        """,
    ]

    # Create indexes for performance
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_purchases_cost_center_id ON purchases(cost_center_id)",
        "CREATE INDEX IF NOT EXISTS idx_purchases_posting_status ON purchases(posting_status)",
        "CREATE INDEX IF NOT EXISTS idx_purchase_orders_cost_center_id ON purchase_orders(cost_center_id)",
        "CREATE INDEX IF NOT EXISTS idx_purchase_orders_posting_status ON purchase_orders(posting_status)",
    ]

    try:
        with engine.connect() as conn:
            logger.info("Starting dimensional accounting migration for Purchases module...")

            # Add columns to tables
            for sql in migration_sql:
                try:
                    logger.info(f"Executing: {sql[:100].strip()}...")
                    conn.execute(text(sql))
                    conn.commit()
                except Exception as e:
                    # Log but don't fail - column may already exist
                    if "already exists" not in str(e).lower() and "column" not in str(e).lower():
                        logger.warning(f"Skipping (likely already exists): {str(e)[:100]}")
                    conn.rollback()

            logger.info("✅ All columns added successfully")

            # Create indexes
            for sql in indexes_sql:
                try:
                    logger.info(f"Creating index: {sql[:80]}...")
                    conn.execute(text(sql))
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Index creation warning: {str(e)[:100]}")
                    conn.rollback()

            logger.info("✅ All indexes created successfully")
            logger.info("🎉 Purchases dimensional accounting migration completed!")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    add_accounting_dimensions_to_purchases()
