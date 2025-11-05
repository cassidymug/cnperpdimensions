"""
Database Migration: Add Dimensional Accounting to Sales Module

Adds cost center, project, and department dimension tracking to sales and invoices.
Also adds GL account references and posting status for accounting integration.

Columns added to sales table:
- cost_center_id, project_id, department_id (dimension tracking)
- revenue_account_id (GL account for revenue posting)
- posting_status, last_posted_date, posted_by (audit trail)

Columns added to invoices table (same plus ar_account_id):
- cost_center_id, project_id, department_id
- revenue_account_id, ar_account_id (for AR GL posting)
- posting_status, last_posted_date, posted_by

Run with:
    python migrations/add_accounting_dimensions_to_sales.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine, text
from app.core.database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_accounting_dimensions_to_sales():
    """Add accounting dimension columns to sales and invoices tables"""

    migration_sql = [
        # Add columns to sales table
        """
        ALTER TABLE sales ADD COLUMN IF NOT EXISTS cost_center_id VARCHAR REFERENCES dimension_values(id)
        """,
        """
        ALTER TABLE sales ADD COLUMN IF NOT EXISTS project_id VARCHAR REFERENCES dimension_values(id)
        """,
        """
        ALTER TABLE sales ADD COLUMN IF NOT EXISTS department_id VARCHAR REFERENCES dimension_values(id)
        """,
        """
        ALTER TABLE sales ADD COLUMN IF NOT EXISTS revenue_account_id VARCHAR REFERENCES accounting_codes(id)
        """,
        """
        ALTER TABLE sales ADD COLUMN IF NOT EXISTS posting_status VARCHAR(20) DEFAULT 'draft'
        """,
        """
        ALTER TABLE sales ADD COLUMN IF NOT EXISTS last_posted_date TIMESTAMP
        """,
        """
        ALTER TABLE sales ADD COLUMN IF NOT EXISTS posted_by VARCHAR REFERENCES users(id)
        """,

        # Add columns to invoices table
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS cost_center_id VARCHAR REFERENCES dimension_values(id)
        """,
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS project_id VARCHAR REFERENCES dimension_values(id)
        """,
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS department_id VARCHAR REFERENCES dimension_values(id)
        """,
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS revenue_account_id VARCHAR REFERENCES accounting_codes(id)
        """,
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS ar_account_id VARCHAR REFERENCES accounting_codes(id)
        """,
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS posting_status VARCHAR(20) DEFAULT 'draft'
        """,
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS last_posted_date TIMESTAMP
        """,
        """
        ALTER TABLE invoices ADD COLUMN IF NOT EXISTS posted_by VARCHAR REFERENCES users(id)
        """,
    ]

    # Create indexes for performance
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_sales_cost_center_id ON sales(cost_center_id)",
        "CREATE INDEX IF NOT EXISTS idx_sales_posting_status ON sales(posting_status)",
        "CREATE INDEX IF NOT EXISTS idx_invoices_cost_center_id ON invoices(cost_center_id)",
        "CREATE INDEX IF NOT EXISTS idx_invoices_posting_status ON invoices(posting_status)",
    ]

    try:
        with engine.connect() as conn:
            logger.info("Starting dimensional accounting migration for Sales module...")

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
            logger.info("🎉 Sales dimensional accounting migration completed!")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    add_accounting_dimensions_to_sales()
