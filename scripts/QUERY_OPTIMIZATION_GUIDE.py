#!/usr/bin/env python3
"""
Query Optimization Guidelines for Banking Module

This document provides best practices for writing optimized SQLAlchemy queries
that reduce response times from 2000+ ms to <500ms target.

Key Optimization Strategies:
"""

# 1. EAGER LOADING WITH JOINEDLOAD
# ==========================================

# BEFORE (N+1 problem - 50+ queries):
# transactions = db.query(BankTransaction).all()
# for tx in transactions:
#     print(tx.bank_account.name)  # Separate query per transaction

# AFTER (Single query with join):
from sqlalchemy.orm import joinedload, selectinload

transactions_optimized = db.query(BankTransaction).options(
    joinedload(BankTransaction.bank_account)
).all()

# For multiple relationships:
transactions_optimized = db.query(BankTransaction).options(
    joinedload(BankTransaction.bank_account),
    joinedload(BankTransaction.cost_center),
    joinedload(BankTransaction.project),
    joinedload(BankTransaction.department),
    selectinload(BankTransaction.reconciliation_items)  # Use selectinload for collections
).all()


# 2. QUERY RESULT CACHING
# ==========================================

import functools
from datetime import timedelta

class QueryCache:
    """Simple in-memory cache for frequently accessed data"""

    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl = timedelta(seconds=ttl_seconds)

    def cached(self, key: str, ttl_override: int = None):
        """Decorator for caching query results"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                from datetime import datetime
                cache_key = f"{key}:{str(args)}{str(kwargs)}"

                if cache_key in self.cache:
                    result, timestamp = self.cache[cache_key]
                    ttl = timedelta(seconds=ttl_override) if ttl_override else self.ttl
                    if datetime.now() - timestamp < ttl:
                        return result

                result = func(*args, **kwargs)
                self.cache[cache_key] = (result, datetime.now())
                return result
            return wrapper
        return decorator

query_cache = QueryCache(ttl_seconds=300)


# 3. FILTER AND PAGINATION
# ==========================================

# BEFORE (Load all, filter in memory):
all_transactions = db.query(BankTransaction).all()
high_amount = [tx for tx in all_transactions if tx.amount > 1000]

# AFTER (Filter at database level):
from sqlalchemy import func

high_amount_optimized = db.query(BankTransaction).filter(
    BankTransaction.amount > 1000
).all()

# With pagination:
page = 1
page_size = 50
offset = (page - 1) * page_size

transactions_page = db.query(BankTransaction).filter(
    BankTransaction.amount > 1000
).offset(offset).limit(page_size).all()


# 4. AGGREGATION QUERIES
# ==========================================

# BEFORE (Load all, aggregate in Python):
transactions = db.query(BankTransaction).all()
total = sum(tx.amount for tx in transactions)
count = len(transactions)

# AFTER (Aggregate at database level):
from sqlalchemy import func

result = db.query(
    func.sum(BankTransaction.amount).label("total"),
    func.count(BankTransaction.id).label("count")
).filter(
    BankTransaction.reconciliation_status == "unreconciled"
).first()

total = result.total
count = result.count


# 5. BATCH OPERATIONS
# ==========================================

# BEFORE (Individual inserts - slow):
for tx_data in transactions_list:
    tx = BankTransaction(**tx_data)
    db.add(tx)
    db.commit()

# AFTER (Bulk insert - fast):
transactions = [BankTransaction(**tx_data) for tx_data in transactions_list]
db.bulk_insert_mappings(BankTransaction, transactions)
db.commit()

# Bulk updates:
db.query(BankTransaction).filter(
    BankTransaction.posting_status == "pending"
).update({"posting_status": "posted"})
db.commit()


# 6. SELECTIVE COLUMN LOADING
# ==========================================

# BEFORE (Load all columns, many unneeded):
transactions = db.query(BankTransaction).all()

# AFTER (Load only needed columns):
from sqlalchemy import select

transactions = db.query(
    BankTransaction.id,
    BankTransaction.date,
    BankTransaction.amount,
    BankTransaction.description
).all()


# 7. DIMENSIONAL QUERY OPTIMIZATION
# ==========================================

# Get cash position by dimension - OPTIMIZED:

class OptimizedBankingQueries:
    """Optimized queries for common banking operations"""

    @staticmethod
    def get_cash_position_by_dimension(db: Session, dimension_field: str):
        """Get cash position grouped by dimension"""
        from sqlalchemy import func, case

        # Single optimized query with grouping at database level
        result = db.query(
            getattr(BankTransaction, dimension_field).label("dimension_value"),
            func.sum(
                case(
                    (BankTransaction.transaction_type == "DEBIT", BankTransaction.amount),
                    else_=-BankTransaction.amount
                )
            ).label("position")
        ).filter(
            BankTransaction.posting_status == "posted"
        ).group_by(
            dimension_field
        ).all()

        return result

    @staticmethod
    def get_unmatched_transactions_for_reconciliation(db: Session, account_id: str):
        """Get unmatched transactions efficiently"""

        # Load only what's needed with eager loading for relationships
        result = db.query(BankTransaction).filter(
            BankTransaction.bank_account_id == account_id,
            BankTransaction.reconciliation_status == "unreconciled"
        ).options(
            joinedload(BankTransaction.bank_account)
        ).all()

        return result

    @staticmethod
    def get_reconciliation_with_items(db: Session, reconciliation_id: str):
        """Get reconciliation and all its items efficiently"""

        # Single query with eager loading
        reconciliation = db.query(BankReconciliation).filter(
            BankReconciliation.id == reconciliation_id
        ).options(
            joinedload(BankReconciliation.reconciliation_items).joinedload(
                ReconciliationItem.bank_transaction
            ),
            joinedload(BankReconciliation.bank_account)
        ).first()

        return reconciliation


# 8. INDEX USAGE VERIFICATION
# ==========================================

"""
After creating indexes, verify they're being used:

SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename IN ('bank_transactions', 'bank_reconciliations', 'reconciliation_items')
ORDER BY idx_scan DESC;

Indexes with 0 idx_scan are candidates for removal.
"""


# 9. QUERY LOGGING FOR ANALYSIS
# ==========================================

import logging
from sqlalchemy import event
from sqlalchemy.pool import Pool

def setup_query_logging():
    """Enable query logging for performance analysis"""

    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    @event.listens_for(Pool, "connect")
    def receive_connect(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("SET log_min_duration_statement = 100")  # Log queries > 100ms
        cursor.close()


# 10. COMMON QUERY PATTERNS - OPTIMIZED
# ==========================================

class OptimizedBankingPatterns:
    """Optimized versions of common banking queries"""

    @staticmethod
    def list_recent_transactions(
        db: Session,
        account_id: str,
        days: int = 30,
        limit: int = 100
    ):
        """List recent transactions with optimal performance"""
        from datetime import datetime, timedelta
        from sqlalchemy import desc

        cutoff_date = datetime.now().date() - timedelta(days=days)

        return db.query(BankTransaction).filter(
            BankTransaction.bank_account_id == account_id,
            BankTransaction.date >= cutoff_date
        ).options(
            joinedload(BankTransaction.bank_account)
        ).order_by(
            desc(BankTransaction.date)
        ).limit(limit).all()

    @staticmethod
    def get_reconciliation_status_summary(db: Session, account_id: str):
        """Get reconciliation status summary"""
        from sqlalchemy import func

        result = db.query(
            BankTransaction.reconciliation_status.label("status"),
            func.count(BankTransaction.id).label("count"),
            func.sum(BankTransaction.amount).label("total_amount")
        ).filter(
            BankTransaction.bank_account_id == account_id
        ).group_by(
            BankTransaction.reconciliation_status
        ).all()

        return result

    @staticmethod
    def find_unmatched_statement_items(
        db: Session,
        reconciliation_id: str
    ):
        """Find statement items that don't have matched transactions"""

        matched_tx_ids = db.query(ReconciliationItem.bank_transaction_id).filter(
            ReconciliationItem.bank_reconciliation_id == reconciliation_id,
            ReconciliationItem.matched == True
        ).all()

        matched_ids = [id_tuple[0] for id_tuple in matched_tx_ids]

        reconciliation = db.query(BankReconciliation).filter(
            BankReconciliation.id == reconciliation_id
        ).first()

        if not reconciliation:
            return []

        # Get transactions for this account not in the matched list
        unmatched = db.query(BankTransaction).filter(
            BankTransaction.bank_account_id == reconciliation.bank_account_id,
            BankTransaction.id.notin_(matched_ids)
        ).all()

        return unmatched


# 11. PERFORMANCE TESTING HELPERS
# ==========================================

import time
from contextlib import contextmanager

@contextmanager
def measure_query_time(description: str):
    """Context manager to measure query execution time"""
    start = time.time()
    yield
    elapsed = (time.time() - start) * 1000
    print(f"{description}: {elapsed:.2f}ms")


# Usage:
# with measure_query_time("Fetch transactions with dimensional data"):
#     transactions = db.query(BankTransaction).options(...).all()


# OPTIMIZATION CHECKLIST
# ==========================================
"""
☐ Create strategic indexes on foreign keys and common filters
☐ Use joinedload for required relationships
☐ Use selectinload for collection relationships
☐ Implement pagination for large result sets
☐ Filter and aggregate at database level, not in Python
☐ Use bulk operations for batch inserts/updates
☐ Load only required columns with explicit select()
☐ Cache frequently accessed static data (dimensions, GL codes)
☐ Monitor query performance with pg_stat_statements
☐ Analyze query plans with EXPLAIN ANALYZE
☐ Use connection pooling in production
☐ Set appropriate connection pool size based on concurrent users
"""
