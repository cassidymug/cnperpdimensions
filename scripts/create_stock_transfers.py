"""
Stock Transfer Creator for CNPERP
Creates stock transfers from MAIN branch to other branches across Botswana
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.inventory import Product, InventoryTransaction
from app.models.branch import Branch
from app.models.user import User


def create_stock_transfers(db: Session):
    """Create stock transfers from MAIN to other branches"""

    print("\n" + "="*70)
    print("  📦 Creating Stock Transfers to Branch Locations")
    print("="*70)

    # Get GBN branch (source - this is where the purchase inventory went)
    main_branch = db.query(Branch).filter_by(code="GBN").first()
    if not main_branch:
        print("❌ Error: GBN branch not found")
        return

    # Get other branches (destinations - exclude both MAIN and GBN)
    other_branches = db.query(Branch).filter(
        Branch.code.notin_(["MAIN", "GBN"])
    ).all()
    if not other_branches:
        print("❌ Error: No other branches found")
        return

    print(f"\n📍 Source: {main_branch.name} ({main_branch.code})")
    print(f"📍 Destinations: {len(other_branches)} branches")

    # Get active user
    user = db.query(User).filter_by(active=True).first()
    if not user:
        print("❌ Error: No active user found")
        return

    # Get products with stock at MAIN
    products = db.query(Product).filter(
        Product.branch_id == main_branch.id,
        Product.quantity > 0
    ).all()

    if not products:
        print("❌ Error: No products with stock found at MAIN")
        return

    print(f"📦 Products to transfer: {len(products)}")

    # Define transfer strategy: distribute stock across branches
    # We'll transfer about 10-15% of stock to each branch
    transfer_percentage = Decimal('0.12')  # 12% to each branch

    total_transfers = 0
    total_quantity = 0

    for branch in other_branches:
        print(f"\n🚚 Transferring to {branch.name} ({branch.code})...")
        branch_transfers = 0

        for product in products:
            # Calculate transfer quantity (12% of current stock)
            transfer_qty = int(product.quantity * transfer_percentage)

            # Minimum transfer of 5 units if product has at least 50 units
            if product.quantity >= 50 and transfer_qty < 5:
                transfer_qty = 5

            # Skip if transfer quantity is too small
            if transfer_qty < 2:
                continue

            # Check if we have enough stock
            if transfer_qty > product.quantity:
                transfer_qty = product.quantity // 2  # Transfer half

            if transfer_qty < 1:
                continue

            # Create inventory transaction for stock OUT from MAIN
            inventory_out = InventoryTransaction(
                product_id=product.id,
                branch_id=main_branch.id,
                transaction_type="transfer_out",
                quantity=-transfer_qty,  # Negative for stock out
                unit_cost=float(product.cost_price) if product.cost_price else 0.0,
                total_cost=float(product.cost_price * transfer_qty) if product.cost_price else 0.0,
                date=datetime.now().date(),
                reference=f"XFER-{branch.code}-{datetime.now().strftime('%Y%m%d')}",
                note=f"Stock transfer to {branch.name}",
                created_by=user.id
            )
            db.add(inventory_out)

            # Create inventory transaction for stock IN at destination branch
            inventory_in = InventoryTransaction(
                product_id=product.id,
                branch_id=branch.id,
                transaction_type="transfer_in",
                quantity=transfer_qty,  # Positive for stock in
                unit_cost=float(product.cost_price) if product.cost_price else 0.0,
                total_cost=float(product.cost_price * transfer_qty) if product.cost_price else 0.0,
                date=datetime.now().date(),
                reference=f"XFER-{branch.code}-{datetime.now().strftime('%Y%m%d')}",
                note=f"Stock transfer from {main_branch.name}",
                created_by=user.id
            )
            db.add(inventory_in)

            # Update product quantity at MAIN
            product.quantity -= transfer_qty

            # Create or update product at destination branch
            dest_product = db.query(Product).filter_by(
                sku=product.sku,
                branch_id=branch.id
            ).first()

            if dest_product:
                # Update existing product
                dest_product.quantity += transfer_qty
            else:
                # Create new product at destination branch
                dest_product = Product(
                    name=product.name,
                    sku=product.sku,
                    description=product.description,
                    barcode=product.barcode,
                    quantity=transfer_qty,
                    cost_price=product.cost_price,
                    selling_price=product.selling_price,
                    unit_of_measure_id=product.unit_of_measure_id,
                    accounting_code_id=product.accounting_code_id,
                    branch_id=branch.id,
                    category=product.category,
                    product_type=product.product_type,
                    active=True
                )
                db.add(dest_product)

            branch_transfers += 1
            total_quantity += transfer_qty

        print(f"  ✅ Transferred {branch_transfers} product types to {branch.name}")
        total_transfers += branch_transfers

    # Commit all changes
    db.commit()

    print("\n" + "="*70)
    print("  ✅ Stock Transfers Complete!")
    print("="*70)
    print(f"\n📊 Summary:")
    print(f"   • Total Transfers: {total_transfers} product types")
    print(f"   • Total Units Transferred: {total_quantity}")
    print(f"   • Branches Stocked: {len(other_branches)}")

    # Display updated stock levels
    print(f"\n📦 Updated Stock at MAIN:")
    main_products = db.query(Product).filter(
        Product.branch_id == main_branch.id,
        Product.quantity > 0
    ).order_by(Product.quantity.desc()).limit(10).all()

    for p in main_products:
        print(f"   • {p.name}: {p.quantity} units")

    print("\n" + "="*70 + "\n")


def main():
    """Main function"""
    print("\n" + "="*70)
    print("  🚀 CNPERP Stock Transfer Creator")
    print("="*70)
    print("Creating stock transfers from MAIN to other branches...")

    db = SessionLocal()
    try:
        create_stock_transfers(db)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
