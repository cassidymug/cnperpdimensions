from sqlalchemy import create_engine, text
from app.core.config import settings

LOWER_ENUM_NAME = 'depreciationmethod_lower'
OLD_ENUM_NAME = 'depreciationmethod'

CREATE_LOWER_ENUM = f"""
DO $$ BEGIN
IF NOT EXISTS (
    SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
    WHERE t.typname='{LOWER_ENUM_NAME}'
) THEN
    CREATE TYPE {LOWER_ENUM_NAME} AS ENUM (
        'straight_line','declining_balance','sum_of_years','units_of_production','none'
    );
END IF; END $$;
"""

ALTER_ASSETS_TO_LOWER = f"""
ALTER TABLE assets 
    ALTER COLUMN depreciation_method TYPE {LOWER_ENUM_NAME} 
    USING lower(depreciation_method::text):: {LOWER_ENUM_NAME};
"""

ALTER_CATEGORY_CONFIGS_TO_LOWER = f"""
DO $$ BEGIN
IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_schema='public' AND table_name='asset_category_configs' AND column_name='default_depreciation_method'
) THEN
    ALTER TABLE asset_category_configs
        ALTER COLUMN default_depreciation_method TYPE {LOWER_ENUM_NAME}
        USING lower(default_depreciation_method::text):: {LOWER_ENUM_NAME};
END IF; END $$;
"""

DROP_OLD_ENUM = f"""
DO $$ BEGIN
IF EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace WHERE t.typname='{OLD_ENUM_NAME}') THEN
    DROP TYPE {OLD_ENUM_NAME};
END IF; END $$;
"""

RENAME_LOWER_TO_OLD = f"""
DO $$ BEGIN
IF NOT EXISTS (
    SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace WHERE t.typname='{OLD_ENUM_NAME}'
) THEN
    ALTER TYPE {LOWER_ENUM_NAME} RENAME TO {OLD_ENUM_NAME};
END IF; END $$;
"""

CHECK_TYPE_VALUES = """
SELECT t.typname, e.enumlabel 
FROM pg_type t
JOIN pg_enum e ON t.oid=e.enumtypid
JOIN pg_namespace n ON n.oid=t.typnamespace
WHERE t.typname in (:old, :lower)
ORDER BY t.typname, e.enumsortorder;
"""

def main():
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        # Step 1: ensure lower enum exists
        print('Creating lower-case enum type if needed...')
        conn.execute(text(CREATE_LOWER_ENUM))
        conn.commit()

        # Step 2: alter assets column to lower enum
        print('Altering assets.depreciation_method to lower-case enum...')
        conn.execute(text(ALTER_ASSETS_TO_LOWER))
        conn.commit()

        # Step 3: alter dependent tables (asset_category_configs) to lower enum
        print('Altering asset_category_configs.default_depreciation_method to lower-case enum (if exists)...')
        conn.execute(text(ALTER_CATEGORY_CONFIGS_TO_LOWER))
        conn.commit()

        # Step 4: try to drop old enum (no dependents should remain)
        print('Dropping old enum type if no dependents...')
        try:
            conn.execute(text(DROP_OLD_ENUM))
            conn.commit()
        except Exception as e:
            print('Skip drop old enum (still in use or not exist):', e)
            conn.rollback()

        # Step 5: if name free, rename lower enum back to original name
        print('Renaming lower-case enum to original name if available...')
        try:
            conn.execute(text(RENAME_LOWER_TO_OLD))
            conn.commit()
        except Exception as e:
            print('Skip rename (likely name already in use):', e)
            conn.rollback()

        print('Enum values after migration:')
        rows = conn.execute(text(CHECK_TYPE_VALUES), {'old': OLD_ENUM_NAME, 'lower': LOWER_ENUM_NAME}).fetchall()
        for r in rows:
            print(' -', r)

if __name__ == '__main__':
    main()
