from app.core.database import SessionLocal
from app.models.branch import Branch

db = SessionLocal()
try:
    branches = db.query(Branch).all()
    print(f"Total branches in database: {len(branches)}")
    for b in branches:
        print(f"\nBranch: {b.name}")
        print(f"  Code: {b.code}")
        print(f"  ID: {b.id}")
        print(f"  Active: {b.active}")
        print(f"  Created_at: {b.created_at}")
finally:
    db.close()
