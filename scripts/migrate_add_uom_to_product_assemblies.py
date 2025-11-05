import sys
from app.core.database import engine
from sqlalchemy import text

SQL_ADD_COLUMN = """
ALTER TABLE product_assemblies
ADD COLUMN IF NOT EXISTS unit_of_measure_id VARCHAR NULL;
"""

SQL_ADD_FK_IF_MISSING = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_product_assemblies_unit_of_measure_id'
          AND table_name = 'product_assemblies'
    ) THEN
        ALTER TABLE product_assemblies
        ADD CONSTRAINT fk_product_assemblies_unit_of_measure_id
        FOREIGN KEY (unit_of_measure_id)
        REFERENCES unit_of_measures(id)
        ON DELETE SET NULL;
    END IF;
END $$;
"""

SQL_LIST_COLUMNS = """
SELECT column_name 
FROM information_schema.columns 
WHERE table_name='product_assemblies' 
ORDER BY column_name;
"""

def main():
    try:
        list_only = '--list-only' in sys.argv
        with engine.connect() as conn:
            if not list_only:
                conn.execute(text(SQL_ADD_COLUMN))
                conn.execute(text(SQL_ADD_FK_IF_MISSING))
            cols = list(conn.execute(text(SQL_LIST_COLUMNS)).scalars())
            conn.commit()
        print(("OK: migration applied. Columns:" if not list_only else "Columns:"), cols)
        if 'unit_of_measure_id' not in cols:
            print("WARN: unit_of_measure_id not present after migration.")
            sys.exit(2)
        sys.exit(0)
    except Exception as e:
        print("ERROR:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
