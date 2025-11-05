from sqlalchemy import create_engine, text
from app.core.config import settings

def main():
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        has_col = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema='public' AND table_name='assets' AND column_name='ifrs_category'
            )
        """)).scalar()
        print('has_ifrs_category:', has_col)
        if not has_col:
            # Ensure enum type exists
            enum_exists = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
                    WHERE t.typname='ifrscategory'
                )
            """)).scalar()
            print('has_ifrscategory_enum:', enum_exists)
            if not enum_exists:
                conn.execute(text("""
                    DO $$ BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
                        WHERE t.typname='ifrscategory'
                    ) THEN
                        CREATE TYPE ifrscategory AS ENUM (
                            'PPE_IAS_16','INVESTMENT_PROPERTY_IAS_40','INVENTORY_IAS_2','INTANGIBLE_ASSET_IAS_38','FINANCIAL_INSTRUMENT_IFRS_9','ASSET_HELD_FOR_SALE_IFRS_5','LEASE_ASSET_IFRS_16'
                        );
                    END IF; END $$;
                """))
                print('Created enum type ifrscategory')
            # Add column with NULL default
            conn.execute(text("""
                ALTER TABLE assets ADD COLUMN IF NOT EXISTS ifrs_category ifrscategory NULL
            """))
            print('Added column assets.ifrs_category')
        else:
            print('No changes required')

if __name__ == '__main__':
    main()
