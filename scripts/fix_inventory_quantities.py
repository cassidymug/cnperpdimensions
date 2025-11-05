"""
Script to analyze and fix inventory quantities that may have been doubled
due to the duplicate InventoryTransaction bug.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import SessionLocal
from app.models.inventory import Product, InventoryTransaction
from app.models.purchases import Purchase, PurchaseItem
from sqlalchemy import func, and_, desc
from datetime import datetime

def analyze_inventory_issues():
    """Analyze inventory for potential doubling issues"""
    db = SessionLocal()

    try:
        print("=" * 80)
        print("INVENTORY QUANTITY ANALYSIS")
        print("=" * 80)

        # Find products with duplicate goods_receipt transactions for same purchase
        print("\n1. Checking for duplicate transactions from same purchase...")
        duplicate_query = db.query(
            InventoryTransaction.product_id,
            InventoryTransaction.related_purchase_id,
            func.count(InventoryTransaction.id).label('count')
        ).filter(
            and_(
                InventoryTransaction.transaction_type == 'goods_receipt',
                InventoryTransaction.related_purchase_id.isnot(None)
            )
        ).group_by(
            InventoryTransaction.product_id,
            InventoryTransaction.related_purchase_id
        ).having(func.count(InventoryTransaction.id) > 1).all()

        print(f"   Found {len(duplicate_query)} product-purchase combinations with duplicate transactions")

        duplicates_to_fix = []
        for dup in duplicate_query:
            product = db.query(Product).filter(Product.id == dup.product_id).first()
            purchase = db.query(Purchase).filter(Purchase.id == dup.related_purchase_id).first()

            # Get all transactions for this product-purchase combo
            transactions = db.query(InventoryTransaction).filter(
                and_(
                    InventoryTransaction.product_id == dup.product_id,
                    InventoryTransaction.related_purchase_id == dup.related_purchase_id,
                    InventoryTransaction.transaction_type == 'goods_receipt'
                )
            ).order_by(InventoryTransaction.created_at).all()

            if product and purchase:
                print(f"\n   Product: {product.name}")
                print(f"   Current Qty: {product.quantity}")
                print(f"   Purchase: {purchase.reference or purchase.id[:8]}...")
                print(f"   Duplicate transactions: {len(transactions)}")

                # Get the purchase item quantity
                purchase_item = db.query(PurchaseItem).filter(
                    and_(
                        PurchaseItem.purchase_id == dup.related_purchase_id,
                        PurchaseItem.product_id == dup.product_id
                    )
                ).first()

                if purchase_item:
                    expected_qty_change = purchase_item.quantity
                    actual_qty_change = sum(t.quantity for t in transactions)
                    print(f"   Expected qty change: {expected_qty_change}")
                    print(f"   Actual qty change: {actual_qty_change}")

                    if actual_qty_change > expected_qty_change:
                        overcounted = actual_qty_change - expected_qty_change
                        print(f"   ⚠️  OVERCOUNTED by: {overcounted}")
                        duplicates_to_fix.append({
                            'product': product,
                            'transactions': transactions,
                            'overcounted': overcounted,
                            'purchase': purchase
                        })

        print("\n" + "=" * 80)
        print(f"SUMMARY: Found {len(duplicates_to_fix)} products with overcounted inventory")
        print("=" * 80)

        return duplicates_to_fix

    finally:
        db.close()


def fix_inventory_quantities(duplicates_to_fix, dry_run=True):
    """Fix overcounted inventory quantities"""
    db = SessionLocal()

    try:
        print("\n" + "=" * 80)
        if dry_run:
            print("DRY RUN - No changes will be made")
        else:
            print("FIXING INVENTORY QUANTITIES")
        print("=" * 80)

        for item in duplicates_to_fix:
            product = item['product']
            transactions = item['transactions']
            overcounted = item['overcounted']

            print(f"\nProduct: {product.name}")
            print(f"  Current qty: {product.quantity}")
            print(f"  Overcounted by: {overcounted}")
            print(f"  Should be: {product.quantity - overcounted}")

            if not dry_run:
                # Delete duplicate transactions (keep the first one)
                for trans in transactions[1:]:
                    print(f"  Deleting duplicate transaction {trans.id[:8]}...")
                    db.delete(trans)

                # Adjust product quantity
                old_qty = product.quantity
                product.quantity -= overcounted
                print(f"  Adjusted quantity: {old_qty} -> {product.quantity}")

        if not dry_run:
            db.commit()
            print("\n✅ Changes committed to database")
        else:
            print("\n⚠️  DRY RUN - Run with --fix to apply changes")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Analyze issues
    duplicates = analyze_inventory_issues()

    # Fix issues
    if duplicates:
        # Check if --fix flag is present
        apply_fix = "--fix" in sys.argv
        fix_inventory_quantities(duplicates, dry_run=not apply_fix)
    else:
        print("\n✅ No inventory quantity issues found!")
