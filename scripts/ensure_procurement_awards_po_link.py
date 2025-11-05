import sys
from sqlalchemy import inspect, text
from app.core.database import engine

"""
One-off script to ensure procurement_awards.purchase_order_id exists and is FK to purchase_orders(id).
Safe to run multiple times; it checks existence before applying.
"""

def column_exists(conn, table, column):
    insp = inspect(conn)
    try:
        cols = [c['name'] for c in insp.get_columns(table)]
        return column in cols
    except Exception:
        return False


def constraint_exists(conn, table, constraint_name):
    q = text(
        """
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = :table AND constraint_name = :cname
        LIMIT 1
        """
    )
    res = conn.execute(q, {"table": table, "cname": constraint_name}).fetchone()
    return bool(res)


def index_exists(conn, schema, table, index_name):
    q = text(
        """
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = :schema AND tablename = :table AND indexname = :iname
        LIMIT 1
        """
    )
    res = conn.execute(q, {"schema": schema, "table": table, "iname": index_name}).fetchone()
    return bool(res)


def main():
    with engine.begin() as conn:
        # Add column if missing
        if not column_exists(conn, 'procurement_awards', 'purchase_order_id'):
            conn.execute(text("ALTER TABLE procurement_awards ADD COLUMN IF NOT EXISTS purchase_order_id VARCHAR NULL"))
            print("Added column procurement_awards.purchase_order_id")
        else:
            print("Column procurement_awards.purchase_order_id already exists")

        # Add FK if missing
        fk_name = 'fk_procurement_awards_purchase_order_id'
        if not constraint_exists(conn, 'procurement_awards', fk_name):
            # Ensure referenced table exists
            if column_exists(conn, 'purchase_orders', 'id'):
                conn.execute(text(
                    f"ALTER TABLE procurement_awards ADD CONSTRAINT {fk_name} FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE SET NULL"
                ))
                print("Added foreign key on procurement_awards.purchase_order_id -> purchase_orders(id)")
            else:
                print("Warning: purchase_orders.id not found; skipping FK creation")
        else:
            print("Foreign key already exists")

        # Create index if missing
        if not index_exists(conn, 'public', 'procurement_awards', 'ix_procurement_awards_purchase_order_id'):
            conn.execute(text(
                "CREATE INDEX ix_procurement_awards_purchase_order_id ON procurement_awards(purchase_order_id)"
            ))
            print("Created index ix_procurement_awards_purchase_order_id")
        else:
            print("Index ix_procurement_awards_purchase_order_id already exists")


if __name__ == '__main__':
    main()
    print("Done")
