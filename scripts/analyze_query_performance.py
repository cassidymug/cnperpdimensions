#!/usr/bin/env python3
"""
Query Performance Analysis - Check if indexes are being used and identify bottlenecks
"""
import sys
from datetime import date, timedelta
from sqlalchemy import text, desc
from app.core.database import SessionLocal
from app.models.banking import BankTransaction, BankReconciliation, ReconciliationItem
from sqlalchemy.orm import joinedload

def analyze_transactions():
    """Analyze GET /transactions query performance"""
    db = SessionLocal()

    print("\n" + "=" * 80)
    print("TRANSACTION QUERY ANALYSIS")
    print("=" * 80)

    # Build the query as the API does
    query = db.query(BankTransaction).options(
        joinedload(BankTransaction.bank_account),
        joinedload(BankTransaction.cost_center),
        joinedload(BankTransaction.project),
        joinedload(BankTransaction.department)
    ).distinct()

    # Apply filters
    start_date = date.today() - timedelta(days=30)
    query = query.filter(BankTransaction.date >= start_date)

    # Sort and limit
    query = query.order_by(desc(BankTransaction.date)).limit(500)

    # Get EXPLAIN PLAN
    compiled = query.statement.compile(compile_kwargs={"literal_binds": True})
    explain_query = f"EXPLAIN ANALYZE {str(compiled)}"

    print("\n[INFO] Query:")
    print(str(query.statement.compile(compile_kwargs={"literal_binds": False})))

    print("\n[INFO] Executing EXPLAIN ANALYZE...")
    results = db.execute(text(f"EXPLAIN ANALYZE {str(compiled)}"))
    plan = results.fetchall()

    print("\n[INFO] Query Plan:")
    for row in plan:
        print(f"  {row[0]}")

    # Check for index usage
    if "Seq Scan" in str(plan):
        print("\n[WARNING] Sequential scan detected - indexes may not be used!")
    if "Index" in str(plan):
        print("\n[SUCCESS] Index scan detected - indexes are being used")

    db.close()


def analyze_reconciliations():
    """Analyze GET /reconciliations query performance"""
    db = SessionLocal()

    print("\n" + "=" * 80)
    print("RECONCILIATION QUERY ANALYSIS")
    print("=" * 80)

    # Build the query as the API does
    query = db.query(BankReconciliation).options(
        joinedload(BankReconciliation.bank_account),
        joinedload(BankReconciliation.reconciliation_items).joinedload(
            ReconciliationItem.bank_transaction
        )
    ).distinct()

    # Apply filters
    start_date = date.today() - timedelta(days=30)
    query = query.filter(BankReconciliation.statement_date >= start_date)

    # Sort and limit
    query = query.order_by(desc(BankReconciliation.statement_date)).limit(500)

    # Get EXPLAIN PLAN
    compiled = query.statement.compile(compile_kwargs={"literal_binds": True})

    print("\n[INFO] Query:")
    print(str(query.statement.compile(compile_kwargs={"literal_binds": False})))

    print("\n[INFO] Executing EXPLAIN ANALYZE...")
    results = db.execute(text(f"EXPLAIN ANALYZE {str(compiled)}"))
    plan = results.fetchall()

    print("\n[INFO] Query Plan:")
    for row in plan:
        print(f"  {row[0]}")

    # Check for index usage
    if "Seq Scan" in str(plan):
        print("\n[WARNING] Sequential scan detected - indexes may not be used!")
    if "Index" in str(plan):
        print("\n[SUCCESS] Index scan detected - indexes are being used")

    db.close()


def check_index_statistics():
    """Check if indexes are being used according to PostgreSQL statistics"""
    db = SessionLocal()

    print("\n" + "=" * 80)
    print("INDEX USAGE STATISTICS")
    print("=" * 80)

    query = text("""
    SELECT
        schemaname,
        relname,
        indexrelname,
        idx_scan as index_scans,
        idx_tup_read as tuples_read,
        idx_tup_fetch as tuples_fetched
    FROM pg_stat_user_indexes
    WHERE relname IN ('bank_transactions', 'bank_reconciliations', 'reconciliation_items')
    ORDER BY idx_scan DESC;
    """)

    results = db.execute(query)

    print("\nIndex Usage:")
    print(f"{'Table':<25} {'Index':<50} {'Scans':<10} {'Tuples Read':<15}")
    print("-" * 100)

    for row in results:
        schema, table, idx, scans, tuples_read, tuples_fetched = row
        print(f"{table:<25} {idx:<50} {scans:<10} {tuples_read:<15}")

    db.close()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("QUERY PERFORMANCE ANALYSIS")
    print("=" * 80)

    try:
        check_index_statistics()
        analyze_transactions()
        analyze_reconciliations()

        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
