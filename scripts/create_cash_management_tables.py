"""
Migration script to create cash management tables for tracking:
1. Cash submissions from salespersons to managers
2. Float allocations to cashiers

Run this script to add the necessary tables to the database.
"""

from sqlalchemy import text
from app.core.database import engine

def create_cash_management_tables():
    """Create cash_submissions and float_allocations tables"""

    with engine.connect() as conn:
        print("Creating cash management tables...")

        # Create cash_submissions table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cash_submissions (
                id VARCHAR PRIMARY KEY,
                salesperson_id VARCHAR NOT NULL REFERENCES users(id),
                received_by_id VARCHAR REFERENCES users(id),
                amount NUMERIC(15, 2) NOT NULL,
                submission_date DATE NOT NULL,
                branch_id VARCHAR REFERENCES branches(id),
                journal_entry_id VARCHAR REFERENCES journal_entries(id),
                status VARCHAR NOT NULL DEFAULT 'pending',
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        print("✓ Created cash_submissions table")

        # Create float_allocations table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS float_allocations (
                id VARCHAR PRIMARY KEY,
                cashier_id VARCHAR NOT NULL REFERENCES users(id),
                allocated_by_id VARCHAR REFERENCES users(id),
                float_amount NUMERIC(15, 2) NOT NULL,
                amount_returned NUMERIC(15, 2) NOT NULL DEFAULT 0,
                allocation_date DATE NOT NULL,
                return_date DATE,
                branch_id VARCHAR REFERENCES branches(id),
                allocation_journal_entry_id VARCHAR REFERENCES journal_entries(id),
                return_journal_entry_id VARCHAR REFERENCES journal_entries(id),
                status VARCHAR NOT NULL DEFAULT 'allocated',
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        print("✓ Created float_allocations table")

        # Create indexes for better query performance
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_cash_submissions_salesperson
            ON cash_submissions(salesperson_id)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_cash_submissions_date
            ON cash_submissions(submission_date)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_cash_submissions_branch
            ON cash_submissions(branch_id)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_float_allocations_cashier
            ON float_allocations(cashier_id)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_float_allocations_date
            ON float_allocations(allocation_date)
        """))

        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_float_allocations_status
            ON float_allocations(status)
        """))

        print("✓ Created indexes")

        conn.commit()
        print("\n✅ Cash management tables created successfully!")
        print("\nNew tables:")
        print("  - cash_submissions: Track cash submissions from salespersons")
        print("  - float_allocations: Track float/change allocations to cashiers")

if __name__ == "__main__":
    try:
        create_cash_management_tables()
    except Exception as e:
        print(f"\n❌ Error creating tables: {str(e)}")
        raise
