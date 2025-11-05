"""
Script to create IFRS database views
"""

import os
from sqlalchemy import text
from app.core.database import SessionLocal, engine

def create_ifrs_views():
    """Create all IFRS views in the database"""
    
    # Read the SQL file
    sql_file_path = os.path.join(os.path.dirname(__file__), 'ifrs_views.sql')
    
    try:
        with open(sql_file_path, 'r') as file:
            sql_content = file.read()
        
        # Split by statements (basic approach)
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        with SessionLocal() as db:
            for statement in statements:
                if statement and not statement.startswith('--'):
                    try:
                        db.execute(text(statement))
                        print(f"✅ Executed statement: {statement[:50]}...")
                    except Exception as e:
                        print(f"❌ Error executing statement: {e}")
                        print(f"Statement: {statement[:100]}...")
            
            db.commit()
            print("✅ All IFRS views created successfully!")
    
    except FileNotFoundError:
        print(f"❌ SQL file not found: {sql_file_path}")
    except Exception as e:
        print(f"❌ Error creating views: {e}")

if __name__ == "__main__":
    create_ifrs_views()
