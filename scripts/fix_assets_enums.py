from sqlalchemy import create_engine, text
from app.core.config import settings

SQL_DISTINCTS = {
    'category': "SELECT DISTINCT category::text FROM assets ORDER BY 1",
    'status': "SELECT DISTINCT status::text FROM assets ORDER BY 1",
    'depreciation_method': "SELECT DISTINCT depreciation_method::text FROM assets ORDER BY 1",
}

SQL_RENAMES = [
    "ALTER TYPE depreciationmethod RENAME VALUE 'STRAIGHT_LINE' TO 'straight_line'",
    "ALTER TYPE depreciationmethod RENAME VALUE 'DECLINING_BALANCE' TO 'declining_balance'",
    "ALTER TYPE depreciationmethod RENAME VALUE 'SUM_OF_YEARS' TO 'sum_of_years'",
    "ALTER TYPE depreciationmethod RENAME VALUE 'UNITS_OF_PRODUCTION' TO 'units_of_production'",
    "ALTER TYPE depreciationmethod RENAME VALUE 'NONE' TO 'none'",
]

SQL_CATEGORY_NORMALIZE = "UPDATE assets SET category = 'INVENTORY'::assetcategory WHERE category::text = 'inventory'"

SQL_STATUS_NORMALIZE = """
UPDATE assets SET status = 'ACTIVE'::assetstatus WHERE status::text = 'active';
UPDATE assets SET status = 'INACTIVE'::assetstatus WHERE status::text = 'inactive';
UPDATE assets SET status = 'DISPOSED'::assetstatus WHERE status::text = 'disposed';
UPDATE assets SET status = 'SOLD'::assetstatus WHERE status::text = 'sold';
"""

def run():
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        print('Connected to DB')
        # Show distincts before
        print('\nBefore fix:')
        for k, q in SQL_DISTINCTS.items():
            rows = conn.execute(text(q)).fetchall()
            print(f" - {k}: {[r[0] for r in rows]}")
        # Normalize categories/status textual anomalies first
        conn.execute(text(SQL_CATEGORY_NORMALIZE))
        for stmt in SQL_STATUS_NORMALIZE.strip().split(';'):
            s = stmt.strip()
            if s:
                conn.execute(text(s))
        # Attempt enum renames for depreciationmethod
        for stmt in SQL_RENAMES:
            try:
                conn.execute(text(stmt))
                print('Executed:', stmt)
            except Exception as e:
                print('Skip/Already renamed or error:', stmt, '-', e)
        # Show distincts after
        print('\nAfter fix:')
        for k, q in SQL_DISTINCTS.items():
            rows = conn.execute(text(q)).fetchall()
            print(f" - {k}: {[r[0] for r in rows]}")

if __name__ == '__main__':
    run()
