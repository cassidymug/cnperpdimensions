#!/usr/bin/env python3
"""
Create Purchase Transactions Script

This script creates purchase orders from suppliers, receives stock,
and processes bank payments for the purchases.
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.purchases import Supplier, Purchase, PurchaseItem
from app.models.inventory import Product, InventoryTransaction
from app.models.branch import Branch
from app.models.banking import BankAccount, BankTransaction
from app.models.user import User
from app.models.accounting import AccountingCode


def get_bank_account(db: Session, branch_id: str) -> BankAccount:
    """Get or create a bank account for purchases"""
    # Try to find existing bank account
    bank_account = db.query(BankAccount).filter(
        BankAccount.branch_id == branch_id
    ).first()

    if not bank_account:
        # Get cash/bank accounting code
        cash_code = db.query(AccountingCode).filter_by(code="1010-01").first()
        if not cash_code:
            cash_code = db.query(AccountingCode).filter_by(code="1010").first()

        # Create a new bank account for the branch
        branch = db.query(Branch).filter_by(id=branch_id).first()
        bank_account = BankAccount(
            name=f"{branch.name} - Operating Account",
            institution="First National Bank Botswana",
            account_number=f"ACC{branch.code}001",
            account_type="checking",
            currency="BWP",
            balance=5000000.00,  # 5 Million Pula starting balance
            accounting_code_id=cash_code.id if cash_code else None,
            branch_id=branch_id
        )
        db.add(bank_account)
        db.flush()
        print(f"✅ Created bank account: {bank_account.name} (Balance: P{bank_account.balance:,.2f})")

    return bank_account


def create_purchase_transactions(db: Session):
    """Create purchase transactions with bank payments"""

    print("\n" + "="*70)
    print("  💰 Creating Purchase Transactions with Bank Payments")
    print("="*70)

    # Get the main branch
    main_branch = db.query(Branch).filter_by(code="MAIN").first()
    if not main_branch:
        print("❌ MAIN branch not found!")
        return

    # Get a user for creating transactions
    user = db.query(User).filter_by(active=True).first()
    if not user:
        print("❌ No active user found!")
        return

    # Get bank account
    bank_account = get_bank_account(db, main_branch.id)

    # Get all suppliers
    suppliers = db.query(Supplier).all()
    if not suppliers:
        print("❌ No suppliers found!")
        return

    # Get all products
    products = db.query(Product).all()
    if not products:
        print("❌ No products found!")
        return

    print(f"\n📋 Found {len(suppliers)} suppliers and {len(products)} products")
    print(f"💳 Using bank account: {bank_account.name} (Balance: P{bank_account.balance:,.2f})")

    # Get Accounts Payable account
    ap_account = db.query(AccountingCode).filter_by(code="2110").first()

    # Get Cash/Bank account for payments
    cash_account = db.query(AccountingCode).filter_by(code="1010-01").first()
    if not cash_account:
        # Try general cash account
        cash_account = db.query(AccountingCode).filter_by(code="1010").first()

    # Create large purchase orders from each supplier
    purchase_data = [
        {
            "supplier_index": 0,  # Botswana Wholesale Suppliers
            "items": [
                {"product_index": 0, "quantity": 500, "unit_price": 45.00},  # Paper A4
                {"product_index": 1, "quantity": 200, "unit_price": 180.00},  # Mouse
                {"product_index": 6, "quantity": 300, "unit_price": 145.00},  # USB Drive
                {"product_index": 7, "quantity": 400, "unit_price": 25.00},  # Notebook
            ]
        },
        {
            "supplier_index": 1,  # Diamond Logistics Ltd
            "items": [
                {"product_index": 2, "quantity": 150, "unit_price": 250.00},  # LED Lamp
                {"product_index": 3, "quantity": 250, "unit_price": 85.00},   # Detergent
                {"product_index": 6, "quantity": 200, "unit_price": 145.00},  # USB Drive
            ]
        },
        {
            "supplier_index": 2,  # Kalahari Traders
            "items": [
                {"product_index": 4, "quantity": 300, "unit_price": 220.00},  # Coffee
                {"product_index": 5, "quantity": 500, "unit_price": 35.00},   # Sanitizer
                {"product_index": 0, "quantity": 400, "unit_price": 45.00},   # Paper A4
            ]
        },
        {
            "supplier_index": 3,  # Southern Imports
            "items": [
                {"product_index": 1, "quantity": 250, "unit_price": 180.00},  # Mouse
                {"product_index": 2, "quantity": 180, "unit_price": 250.00},  # LED Lamp
                {"product_index": 4, "quantity": 200, "unit_price": 220.00},  # Coffee
                {"product_index": 5, "quantity": 350, "unit_price": 35.00},   # Sanitizer
            ]
        },
    ]

    total_purchases = 0
    total_amount = Decimal('0.00')

    for purchase_idx, po_data in enumerate(purchase_data, 1):
        supplier = suppliers[po_data["supplier_index"]]

        # Calculate total for this purchase
        subtotal = Decimal('0.00')
        for item_data in po_data["items"]:
            product = products[item_data["product_index"]]
            item_total = Decimal(str(item_data["quantity"])) * Decimal(str(item_data["unit_price"]))
            subtotal += item_total

        vat_amount = subtotal * Decimal('0.14')  # 14% VAT
        total = subtotal + vat_amount

        # Create Purchase Order
        purchase = Purchase(
            supplier_id=supplier.id,
            branch_id=main_branch.id,
            purchase_date=datetime.now().date(),
            total_amount=float(total),
            total_vat_amount=float(vat_amount),  # FIXED: was vat_amount
            total_amount_ex_vat=float(subtotal),  # Add the ex-vat amount
            status="received",  # Mark as received immediately
            amount_paid=float(total),  # Mark as fully paid
            created_by=user.id,
            approved_by=user.id,
            approved_at=datetime.now().date(),
            received_at=datetime.now().date(),
            bank_account_id=bank_account.id,
            notes=f"Large stock purchase order #{purchase_idx}"
        )
        db.add(purchase)
        db.flush()

        # Create purchase items and inventory transactions
        for item_data in po_data["items"]:
            product = products[item_data["product_index"]]
            quantity = item_data["quantity"]
            unit_price = Decimal(str(item_data["unit_price"]))
            item_total = quantity * unit_price

            # Create purchase item
            purchase_item = PurchaseItem(
                purchase_id=purchase.id,
                product_id=product.id,
                quantity=quantity,
                cost=float(unit_price),  # FIXED: was unit_price
                total_cost=float(item_total),  # FIXED: was total_price
                vat_amount=float(item_total * Decimal('0.14')),
                vat_rate=Decimal('0.14')
            )
            db.add(purchase_item)

            # Create inventory transaction (stock in)
            inventory_transaction = InventoryTransaction(
                product_id=product.id,
                branch_id=main_branch.id,
                transaction_type="purchase",
                quantity=quantity,
                unit_cost=float(unit_price),
                total_cost=float(item_total),
                date=datetime.now().date(),  # FIXED: was transaction_date
                reference=f"PO{purchase_idx:04d}",  # FIXED: was reference_type and reference_id
                related_purchase_id=purchase.id,
                note=f"Stock received from {supplier.name}",  # FIXED: was notes
                created_by=user.id
            )
            db.add(inventory_transaction)

            # Update product quantity
            product.quantity += quantity

            print(f"  ✅ Added {quantity} units of {product.name} @ P{unit_price}")

        # Create bank transaction for payment
        bank_transaction = BankTransaction(
            bank_account_id=bank_account.id,
            date=datetime.now().date(),  # FIXED: was transaction_date
            transaction_type="withdrawal",  # FIXED: standardize to withdrawal for debits
            amount=float(total),
            description=f"Payment to {supplier.name} - PO #{purchase.id[:8]}",
            reference=f"PAY{purchase_idx:04d}",  # FIXED: was reference_number
            reconciled=False,
            posting_status="posted"  # FIXED: was status and category
        )
        db.add(bank_transaction)

        # Update bank account balance
        bank_account.balance -= total  # FIXED: keep as Decimal, was float(total)

        print(f"\n✅ Purchase Order #{purchase_idx} created:")
        print(f"   Supplier: {supplier.name}")
        print(f"   Items: {len(po_data['items'])}")
        print(f"   Subtotal: P{subtotal:,.2f}")
        print(f"   VAT (14%): P{vat_amount:,.2f}")
        print(f"   Total: P{total:,.2f}")
        print(f"   Payment: Bank Transfer - {bank_transaction.reference}")  # FIXED: was reference_number
        print(f"   Bank Balance: P{bank_account.balance:,.2f}")

        total_purchases += 1
        total_amount += total

    db.commit()

    # Print summary
    print("\n" + "="*70)
    print("  ✅ Purchase Transactions Complete!")
    print("="*70)
    print(f"\n📊 Summary:")
    print(f"   • Total Purchase Orders: {total_purchases}")
    print(f"   • Total Amount Paid: P{total_amount:,.2f}")
    print(f"   • Remaining Bank Balance: P{bank_account.balance:,.2f}")

    # Print stock summary
    print(f"\n📦 Stock Summary:")
    for product in products:
        db.refresh(product)
        print(f"   • {product.name}: {product.quantity} units")

    print("\n" + "="*70)


def main():
    """Main execution"""
    print("\n" + "="*70)
    print("  🚀 CNPERP Purchase Transactions Creator")
    print("="*70)
    print("Creating large purchase orders with bank payments...")

    db = SessionLocal()
    try:
        create_purchase_transactions(db)
        print("\n✅ All purchase transactions created successfully!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
