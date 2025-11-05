"""
Database Migration: Add Production Order System Tables

Creates comprehensive production order tracking system for manufacturing.

Tables created:
- production_orders
- production_material_consumptions
- production_labor_entries
- production_overhead_entries
- production_order_status_history
- production_quality_checks

Run with:
    python migrations/add_production_orders.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine, text
from app.core.database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_production_order_tables():
    """Create all production order system tables"""

    tables_sql = [
        # 1. Production Orders table
        """
        CREATE TABLE IF NOT EXISTS production_orders (
            id VARCHAR PRIMARY KEY,
            order_number VARCHAR(50) UNIQUE NOT NULL,

            -- Product details
            product_id VARCHAR NOT NULL REFERENCES products(id),
            recipe_id VARCHAR REFERENCES products(id),

            -- Quantities
            quantity_planned NUMERIC(15, 2) NOT NULL,
            quantity_produced NUMERIC(15, 2) DEFAULT 0,
            quantity_scrapped NUMERIC(15, 2) DEFAULT 0,

            -- Unit of measure
            unit_of_measure_id VARCHAR REFERENCES unit_of_measures(id),

            -- Dates
            scheduled_start_date DATE,
            scheduled_end_date DATE,
            actual_start_date DATE,
            actual_end_date DATE,

            -- Status
            status VARCHAR(50) NOT NULL DEFAULT 'draft',
            priority INTEGER DEFAULT 5,

            -- Costs
            total_material_cost NUMERIC(15, 2) DEFAULT 0,
            total_labor_cost NUMERIC(15, 2) DEFAULT 0,
            total_overhead_cost NUMERIC(15, 2) DEFAULT 0,
            total_cost NUMERIC(15, 2) DEFAULT 0,
            unit_cost NUMERIC(15, 2) DEFAULT 0,

            -- Location
            manufacturing_branch_id VARCHAR REFERENCES branches(id),

            -- References
            notes TEXT,
            customer_reference VARCHAR(100),
            batch_number VARCHAR(50),

            -- Audit
            created_by VARCHAR REFERENCES users(id),
            updated_by VARCHAR REFERENCES users(id),
            approved_by VARCHAR REFERENCES users(id),
            completed_by VARCHAR REFERENCES users(id),

            -- Timestamps
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,

        # 2. Production Material Consumptions table
        """
        CREATE TABLE IF NOT EXISTS production_material_consumptions (
            id VARCHAR PRIMARY KEY,
            production_order_id VARCHAR NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,

            -- Material
            material_id VARCHAR NOT NULL REFERENCES products(id),
            quantity_planned NUMERIC(15, 2) NOT NULL,
            quantity_consumed NUMERIC(15, 2) DEFAULT 0,
            quantity_returned NUMERIC(15, 2) DEFAULT 0,
            quantity_scrapped NUMERIC(15, 2) DEFAULT 0,

            -- Costing
            unit_cost NUMERIC(15, 2) DEFAULT 0,
            total_cost NUMERIC(15, 2) DEFAULT 0,

            -- UOM
            unit_of_measure_id VARCHAR REFERENCES unit_of_measures(id),

            -- Inventory link
            inventory_transaction_id VARCHAR REFERENCES inventory_transactions(id),

            -- Issue tracking
            issued_date DATE,
            issued_by VARCHAR REFERENCES users(id),

            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,

        # 3. Production Labor Entries table
        """
        CREATE TABLE IF NOT EXISTS production_labor_entries (
            id VARCHAR PRIMARY KEY,
            production_order_id VARCHAR NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,

            -- Labor details
            employee_id VARCHAR REFERENCES users(id),
            hours_worked NUMERIC(10, 2) NOT NULL,
            hourly_rate NUMERIC(15, 2) NOT NULL,
            total_cost NUMERIC(15, 2) NOT NULL,

            -- Work details
            work_date DATE NOT NULL,
            work_description TEXT,
            operation_type VARCHAR(100),

            -- Overtime
            regular_hours NUMERIC(10, 2) DEFAULT 0,
            overtime_hours NUMERIC(10, 2) DEFAULT 0,

            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR REFERENCES users(id)
        )
        """,

        # 4. Production Overhead Entries table
        """
        CREATE TABLE IF NOT EXISTS production_overhead_entries (
            id VARCHAR PRIMARY KEY,
            production_order_id VARCHAR NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,

            -- Overhead details
            overhead_type VARCHAR(100) NOT NULL,
            description TEXT,
            amount NUMERIC(15, 2) NOT NULL,

            -- Allocation
            allocation_basis VARCHAR(50),
            allocation_rate NUMERIC(15, 4),
            allocation_quantity NUMERIC(15, 2),

            -- Date
            incurred_date DATE NOT NULL,

            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR REFERENCES users(id)
        )
        """,

        # 5. Production Order Status History table
        """
        CREATE TABLE IF NOT EXISTS production_order_status_history (
            id VARCHAR PRIMARY KEY,
            production_order_id VARCHAR NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,

            -- Status change
            from_status VARCHAR(50),
            to_status VARCHAR(50) NOT NULL,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            changed_by VARCHAR REFERENCES users(id),

            -- Reason
            reason TEXT,
            notes TEXT
        )
        """,

        # 6. Production Quality Checks table
        """
        CREATE TABLE IF NOT EXISTS production_quality_checks (
            id VARCHAR PRIMARY KEY,
            production_order_id VARCHAR NOT NULL REFERENCES production_orders(id) ON DELETE CASCADE,

            -- QC details
            check_date DATE NOT NULL,
            inspector_id VARCHAR REFERENCES users(id),

            -- Results
            quantity_inspected NUMERIC(15, 2) NOT NULL,
            quantity_passed NUMERIC(15, 2) NOT NULL,
            quantity_failed NUMERIC(15, 2) NOT NULL,

            -- Defects
            defect_description TEXT,
            corrective_action TEXT,

            -- Pass/Fail
            passed VARCHAR(20) NOT NULL,

            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    ]

    # Create indexes
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_production_orders_order_number ON production_orders(order_number)",
        "CREATE INDEX IF NOT EXISTS idx_production_orders_status ON production_orders(status)",
        "CREATE INDEX IF NOT EXISTS idx_production_orders_product_id ON production_orders(product_id)",
        "CREATE INDEX IF NOT EXISTS idx_production_orders_branch ON production_orders(manufacturing_branch_id)",
        "CREATE INDEX IF NOT EXISTS idx_production_material_consumptions_order ON production_material_consumptions(production_order_id)",
        "CREATE INDEX IF NOT EXISTS idx_production_labor_entries_order ON production_labor_entries(production_order_id)",
        "CREATE INDEX IF NOT EXISTS idx_production_overhead_entries_order ON production_overhead_entries(production_order_id)",
        "CREATE INDEX IF NOT EXISTS idx_production_status_history_order ON production_order_status_history(production_order_id)",
        "CREATE INDEX IF NOT EXISTS idx_production_quality_checks_order ON production_quality_checks(production_order_id)",
    ]

    try:
        with engine.connect() as conn:
            logger.info("Starting production order tables creation...")

            # Create tables
            for sql in tables_sql:
                logger.info(f"Executing: {sql[:100]}...")
                conn.execute(text(sql))
                conn.commit()

            logger.info("✅ All tables created successfully")

            # Create indexes
            for sql in indexes_sql:
                logger.info(f"Creating index: {sql[:80]}...")
                conn.execute(text(sql))
                conn.commit()

            logger.info("✅ All indexes created successfully")

            logger.info("🎉 Production order system migration completed!")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise


if __name__ == "__main__":
    create_production_order_tables()
