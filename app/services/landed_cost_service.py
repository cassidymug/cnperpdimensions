from sqlalchemy.orm import Session
from app.models.landed_cost import LandedCost, LandedCostItem
from app.models.purchases import Purchase, PurchaseItem
from app.models.inventory import Product, InventoryTransaction
from app.schemas.landed_cost import LandedCostCreate
from decimal import Decimal

class LandedCostService:
    def __init__(self, db: Session):
        self.db = db

    def create_landed_cost(self, landed_cost_data: LandedCostCreate) -> LandedCost:
        """
        Creates a new Landed Cost document and its associated items.
        """
        if not landed_cost_data.purchase_id:
            raise ValueError("A purchase ID is required to create a landed cost document.")

        purchase = self.db.query(Purchase).filter(Purchase.id == landed_cost_data.purchase_id).first()
        if not purchase:
            raise ValueError("Purchase not found.")

        total_amount = sum(item.amount for item in landed_cost_data.items)

        db_landed_cost = LandedCost(
            purchase_id=landed_cost_data.purchase_id,
            reference=landed_cost_data.reference,
            supplier_id=landed_cost_data.supplier_id,
            date=landed_cost_data.date,
            notes=landed_cost_data.notes,
            total_amount=total_amount,
            status="draft"
        )

        for item_data in landed_cost_data.items:
            db_item = LandedCostItem(**item_data.dict(), landed_cost=db_landed_cost)
            self.db.add(db_item)

        self.db.add(db_landed_cost)
        self.db.commit()
        self.db.refresh(db_landed_cost)
        return db_landed_cost

    def allocate_landed_cost(self, landed_cost_id: str):
        """
        Allocates the total landed cost to the items of the associated purchase,
        updating the cost price of the products.
        """
        landed_cost = self.db.query(LandedCost).filter(LandedCost.id == landed_cost_id).first()
        if not landed_cost:
            raise ValueError("Landed Cost document not found.")

        if landed_cost.status == 'allocated':
            raise ValueError("Landed costs have already been allocated.")

        purchase = landed_cost.purchase
        if not purchase:
            raise ValueError("Associated purchase not found.")

        purchase_items = purchase.purchase_items
        if not purchase_items:
            return # No items to allocate to

        # For now, we'll use a simple allocation by quantity.
        # This can be expanded to support other methods (cost, weight, volume).
        total_quantity = sum(item.quantity for item in purchase_items)

        if total_quantity == 0:
            return # Avoid division by zero

        cost_per_unit_quantity = Decimal(landed_cost.total_amount) / Decimal(total_quantity)

        for item in purchase_items:
            product = self.db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                continue

            allocated_cost = cost_per_unit_quantity * Decimal(item.quantity)
            
            # The new cost of the item is its original cost + allocated landed cost
            new_item_total_cost = (Decimal(item.cost) * Decimal(item.quantity)) + allocated_cost
            new_unit_cost = new_item_total_cost / Decimal(item.quantity)

            # Update product's cost price using a weighted average
            old_total_value = Decimal(product.cost_price) * Decimal(product.quantity_in_stock)
            new_total_value = old_total_value + allocated_cost
            new_total_quantity = Decimal(product.quantity_in_stock)
            
            if new_total_quantity > 0:
                product.cost_price = new_total_value / new_total_quantity

            # Create an inventory transaction to record the cost adjustment
            transaction = InventoryTransaction(
                product_id=product.id,
                transaction_type='cost_adjustment',
                quantity=0, # No change in quantity
                unit_cost=new_unit_cost, # The new effective unit cost
                reference=f"Landed cost allocation from {landed_cost.reference}",
                related_purchase_id=purchase.id
            )
            self.db.add(transaction)

        landed_cost.status = 'allocated'
        self.db.commit()

        return True
