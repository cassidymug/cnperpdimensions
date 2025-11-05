#!/usr/bin/env python3
"""
Check inventory status across branches
"""
from app.core.database import SessionLocal
from app.models import Product, Branch

def main():
    db = SessionLocal()
    try:
        # Get all branches
        branches = db.query(Branch).all()
        print(f"\n{'='*70}")
        print(f"  📦 Inventory Status Report")
        print(f"{'='*70}\n")

        for branch in branches:
            products = db.query(Product).filter(
                Product.branch_id == branch.id,
                Product.quantity > 0
            ).all()

            print(f"\n📍 {branch.name} ({branch.code})")
            print(f"   Branch ID: {branch.id}")
            print(f"   Products with stock: {len(products)}")

            if products:
                total_units = sum(p.quantity for p in products)
                print(f"   Total units: {total_units}")
                print(f"\n   Products:")
                for p in products:
                    print(f"     • {p.name}: {p.quantity} units")
            else:
                print(f"   No stock")

    finally:
        db.close()

if __name__ == "__main__":
    main()
