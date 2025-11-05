from app.core.database import SessionLocal
from app.models.branch import Branch

db = SessionLocal()
try:
    branches = db.query(Branch).all()
    print(f"Total branches in database: {len(branches)}\n")

    test_branches = []
    for b in branches:
        if 'test' in b.name.lower() or 'test' in b.code.lower():
            test_branches.append(b)
            print(f"TEST BRANCH: {b.name} ({b.code})")
        else:
            print(f"REAL BRANCH: {b.name} ({b.code})")

    print(f"\nFound {len(test_branches)} test branches to delete")

    if test_branches:
        print("\nDeleting test branches...")
        for b in test_branches:
            db.delete(b)
        db.commit()
        print(f"Deleted {len(test_branches)} test branches successfully")

        # Verify
        remaining = db.query(Branch).count()
        print(f"\nRemaining branches: {remaining}")

finally:
    db.close()
