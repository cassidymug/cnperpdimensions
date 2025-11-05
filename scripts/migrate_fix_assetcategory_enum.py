from sqlalchemy import create_engine, text
from app.core.config import settings

ENUM_NAME = 'assetcategory'
OLD_LABEL = 'inventory'
NEW_LABEL = 'INVENTORY'

SQL_UPDATE_ROWS = f"""
UPDATE assets SET category = '{NEW_LABEL}'::assetcategory WHERE category::text = '{OLD_LABEL}';
UPDATE asset_category_configs SET category = '{NEW_LABEL}'::assetcategory WHERE category::text = '{OLD_LABEL}';
"""

SQL_DROP_OLD_LABEL = f"""
DO $$ BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid
        WHERE t.typname = '{ENUM_NAME}' AND e.enumlabel = '{OLD_LABEL}'
    ) THEN
        ALTER TYPE {ENUM_NAME} DROP VALUE '{OLD_LABEL}';
    END IF;
END $$;
"""

SQL_CHECK_ENUM = f"""
SELECT t.typname, e.enumlabel 
FROM pg_type t
JOIN pg_enum e ON t.oid=e.enumtypid
WHERE t.typname = '{ENUM_NAME}'
ORDER BY e.enumsortorder;
"""

def main():
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        print('Updating rows to use INVENTORY...')
        conn.execute(text(SQL_UPDATE_ROWS))
        conn.commit()
        print('Dropping old enum label if present...')
        try:
            conn.execute(text(SQL_DROP_OLD_LABEL))
            conn.commit()
        except Exception as e:
            print('Drop label failed:', e)
            conn.rollback()
        print('Enum values after migration:')
        rows = conn.execute(text(SQL_CHECK_ENUM)).fetchall()
        for r in rows:
            print(' -', r)

if __name__ == '__main__':
    main()
