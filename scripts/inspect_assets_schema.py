from sqlalchemy import create_engine, text
from app.core.config import settings

SQL_ASSETS_COLUMNS = """
SELECT column_name, data_type, udt_name
FROM information_schema.columns 
WHERE table_schema = 'public' AND table_name = 'assets'
ORDER BY ordinal_position
"""

SQL_ENUMS = """
SELECT t.typname AS enum_type, e.enumlabel AS value
FROM pg_type t
JOIN pg_enum e ON t.oid = e.enumtypid
JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
WHERE t.typcategory = 'E'
ORDER BY enum_type, e.enumsortorder
"""

SQL_TABLE_EXISTS = """
SELECT EXISTS (
  SELECT 1
  FROM information_schema.tables
  WHERE table_schema='public' AND table_name='assets'
) AS exists
"""

def main():
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        print('Connected to:', conn.execute(text('select current_database()')).scalar())
        print('PostgreSQL version:', conn.execute(text('select version()')).scalar())
        exists = conn.execute(text(SQL_TABLE_EXISTS)).scalar()
        print("assets table exists:", exists)
        if not exists:
            return
        print("\nAssets table columns:")
        for row in conn.execute(text(SQL_ASSETS_COLUMNS)).fetchall():
            print(" -", row)
        print("\nEnum types and values (first 200 shown):")
        rows = conn.execute(text(SQL_ENUMS)).fetchall()
        for i, r in enumerate(rows[:200]):
            print(" -", r)

if __name__ == '__main__':
    main()
