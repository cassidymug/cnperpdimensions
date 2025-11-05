"""
Branch Stock Management Service

This service handles branch-specific stock operations including:
- Stock transfers between branches
- Branch stock levels
- Branch-specific inventory transactions
- Stock consolidation and reporting
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from app.models.branch import Branch
from app.models.inventory import Product, InventoryTransaction, InventoryAdjustment
from app.models.sales import Sale, SaleItem
from app.models.accounting import JournalEntry, AccountingEntry, AccountingCode
from app.core.database import get_db


class BranchStockService:
    """Service for managing branch-specific stock operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_branch_stock_levels(self, branch_id: str) -> List[Dict]:
        """Get current stock levels for all products in a branch"""
        products = self.db.query(Product).filter(
            Product.branch_id == branch_id
        ).all()
        
        stock_levels = []
        for product in products:
            # Calculate current stock from transactions
            current_stock = self._calculate_current_stock(product.id, branch_id)
            
            # Check for low stock
            is_low_stock = current_stock <= (product.reorder_point or 5)
            is_out_of_stock = current_stock <= 0
            
            stock_levels.append({
                'product_id': product.id,
                'product_name': product.name,
                'sku': product.sku,
                'current_stock': current_stock,
                'reorder_point': product.reorder_point or 5,
                'cost_price': float(product.cost_price or 0),
                'selling_price': float(product.selling_price or 0),
                'is_low_stock': is_low_stock,
                'is_out_of_stock': is_out_of_stock,
                'stock_value': current_stock * float(product.cost_price or 0),
                'branch_id': branch_id
            })
        
        return stock_levels
    
    def transfer_stock_between_branches(
        self, 
        product_id: str,
        from_branch_id: str,
        to_branch_id: str,
        quantity: int,
        reason: str = "Branch Transfer",
        user_id: str = None
    ) -> Dict:
        """Transfer stock from one branch to another"""
        
        # Verify branches exist
        from_branch = self.db.query(Branch).filter(Branch.id == from_branch_id).first()
        to_branch = self.db.query(Branch).filter(Branch.id == to_branch_id).first()
        
        if not from_branch or not to_branch:
            raise ValueError("Invalid branch ID(s)")
        
        # Verify product exists
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")
        
        # Check available stock in source branch
        available_stock = self._calculate_current_stock(product_id, from_branch_id)
        if available_stock < quantity:
            raise ValueError(f"Insufficient stock. Available: {available_stock}, Requested: {quantity}")
        
        # Create outbound transaction (from source branch)
        outbound_transaction = InventoryTransaction(
            product_id=product_id,
            branch_id=from_branch_id,
            transaction_type='stock_transfer_out',
            quantity=-quantity,  # Negative for outbound
            reference_number=f"XFER-OUT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            notes=f"Transfer to {to_branch.name}: {reason}",
            created_by=user_id
        )
        self.db.add(outbound_transaction)
        
        # Create inbound transaction (to destination branch)
        inbound_transaction = InventoryTransaction(
            product_id=product_id,
            branch_id=to_branch_id,
            transaction_type='stock_transfer_in',
            quantity=quantity,  # Positive for inbound
            reference_number=f"XFER-IN-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            notes=f"Transfer from {from_branch.name}: {reason}",
            created_by=user_id
        )
        self.db.add(inbound_transaction)
        
        # Create accounting entries for the transfer
        self._create_transfer_accounting_entries(
            product, quantity, from_branch, to_branch, user_id
        )
        
        self.db.commit()
        
        return {
            'success': True,
            'outbound_transaction_id': outbound_transaction.id,
            'inbound_transaction_id': inbound_transaction.id,
            'transferred_quantity': quantity,
            'from_branch': from_branch.name,
            'to_branch': to_branch.name
        }
    
    def get_branch_stock_movements(
        self, 
        branch_id: str, 
        days: int = 30,
        product_id: str = None
    ) -> List[Dict]:
        """Get stock movements for a branch within specified days"""
        
        start_date = datetime.now() - timedelta(days=days)
        
        query = self.db.query(InventoryTransaction).filter(
            InventoryTransaction.branch_id == branch_id,
            InventoryTransaction.created_at >= start_date
        )
        
        if product_id:
            query = query.filter(InventoryTransaction.product_id == product_id)
        
        transactions = query.order_by(InventoryTransaction.created_at.desc()).all()
        
        movements = []
        for transaction in transactions:
            product = self.db.query(Product).filter(Product.id == transaction.product_id).first()
            
            movements.append({
                'transaction_id': transaction.id,
                'product_id': transaction.product_id,
                'product_name': product.name if product else 'Unknown',
                'sku': product.sku if product else '',
                'transaction_type': transaction.transaction_type,
                'quantity': transaction.quantity,
                'reference_number': transaction.reference_number,
                'notes': transaction.notes,
                'created_at': transaction.created_at,
                'created_by': transaction.created_by
            })
        
        return movements
    
    def get_branch_stock_summary(self, branch_id: str) -> Dict:
        """Get comprehensive stock summary for a branch"""
        
        # Get all products for the branch
        products = self.db.query(Product).filter(Product.branch_id == branch_id).all()
        
        total_products = len(products)
        total_stock_value = 0
        low_stock_count = 0
        out_of_stock_count = 0
        
        for product in products:
            current_stock = self._calculate_current_stock(product.id, branch_id)
            stock_value = current_stock * float(product.cost_price or 0)
            total_stock_value += stock_value
            
            if current_stock <= 0:
                out_of_stock_count += 1
            elif current_stock <= (product.reorder_point or 5):
                low_stock_count += 1
        
        # Get recent movements (last 7 days)
        recent_movements = self.get_branch_stock_movements(branch_id, days=7)
        
        return {
            'branch_id': branch_id,
            'total_products': total_products,
            'total_stock_value': total_stock_value,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'recent_movements_count': len(recent_movements),
            'stock_turn_rate': self._calculate_stock_turnover(branch_id),
            'summary_date': datetime.now()
        }
    
    def consolidate_branch_stocks(self) -> Dict:
        """Get consolidated stock levels across all branches"""
        
        # Get all active branches
        branches = self.db.query(Branch).filter(Branch.active == True).all()
        
        consolidation = {}
        
        for branch in branches:
            branch_stock = self.get_branch_stock_levels(branch.id)
            consolidation[branch.id] = {
                'branch_name': branch.name,
                'branch_code': branch.code,
                'stock_levels': branch_stock,
                'summary': self.get_branch_stock_summary(branch.id)
            }
        
        return consolidation
    
    def _calculate_current_stock(self, product_id: str, branch_id: str) -> int:
        """Calculate current stock level from transactions"""
        
        # Sum all inventory transactions for this product in this branch
        total_quantity = self.db.query(
            func.sum(InventoryTransaction.quantity)
        ).filter(
            InventoryTransaction.product_id == product_id,
            InventoryTransaction.branch_id == branch_id
        ).scalar() or 0
        
        return int(total_quantity)
    
    def _calculate_stock_turnover(self, branch_id: str, days: int = 30) -> float:
        """Calculate stock turnover rate for a branch"""
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Get total sales for the period
        total_sales = self.db.query(
            func.sum(SaleItem.quantity)
        ).join(Sale).filter(
            Sale.branch_id == branch_id,
            Sale.date >= start_date
        ).scalar() or 0
        
        # Get average stock level
        products = self.db.query(Product).filter(Product.branch_id == branch_id).all()
        total_avg_stock = sum(
            self._calculate_current_stock(product.id, branch_id) 
            for product in products
        )
        
        if total_avg_stock > 0:
            return float(total_sales) / float(total_avg_stock) * (365 / days)
        
        return 0.0
    
    def _create_transfer_accounting_entries(
        self,
        product: Product,
        quantity: int,
        from_branch: Branch,
        to_branch: Branch,
        user_id: str = None
    ):
        """Create accounting entries for stock transfers between branches"""
        
        transfer_value = quantity * float(product.cost_price or 0)
        
        # Create accounting entry header
        entry_header = AccountingEntry(
            date_prepared=datetime.now().date(),
            date_posted=datetime.now().date(),
            particulars=f"Stock transfer: {product.name} from {from_branch.name} to {to_branch.name}",
            book="Inventory Journal",
            status="posted",
            branch_id=from_branch.id
        )
        self.db.add(entry_header)
        self.db.flush()

        # Ensure we have an inventory GL account (align to 1140)
        def get_or_create_account(code: str, name: str, account_type: str, category: str, branch_id: str) -> AccountingCode:
            acct = self.db.query(AccountingCode).filter(AccountingCode.code == code).first()
            if not acct:
                acct = AccountingCode(code=code, name=name, account_type=account_type, category=category, branch_id=branch_id)
                self.db.add(acct)
                self.db.flush()
            return acct

        inventory_gl = get_or_create_account('1140', 'Inventory', 'Asset', 'Current Assets', from_branch.id)

        # Debit destination branch inventory account
        debit_journal = JournalEntry(
            accounting_entry_id=entry_header.id,
            accounting_code_id=inventory_gl.id,
            entry_type='debit',
            narration=f"Stock transfer in - {product.name}",
            debit_amount=transfer_value,
            credit_amount=0.0,
            description=f"Transfer from {from_branch.name}",
            reference=f"XFER-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            date=datetime.now().date(),
            branch_id=to_branch.id
        )
        self.db.add(debit_journal)

        # Credit source branch inventory account
        credit_journal = JournalEntry(
            accounting_entry_id=entry_header.id,
            accounting_code_id=inventory_gl.id,
            entry_type='credit',
            narration=f"Stock transfer out - {product.name}",
            debit_amount=0.0,
            credit_amount=transfer_value,
            description=f"Transfer to {to_branch.name}",
            reference=f"XFER-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            date=datetime.now().date(),
            branch_id=from_branch.id
        )
        self.db.add(credit_journal)


def get_branch_stock_service(db: Session = None) -> BranchStockService:
    """Factory function to get BranchStockService instance"""
    if db is None:
        db = next(get_db())
    return BranchStockService(db)
