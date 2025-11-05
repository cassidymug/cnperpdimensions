from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, case

from app.models.inventory import Product, InventoryTransaction, InventoryAdjustment, SerialNumber
from app.models.accounting import AccountingCode, AccountingEntry, JournalEntry
from app.services.accounting_service import AccountingService
from app.core.config import settings


class InventoryService:
    """Comprehensive inventory business logic service"""

    TRANSACTION_TYPES = [
        'goods_receipt', 'sale', 'return', 'adjustment', 'opening_stock',
        'sale_cancellation', 'damage', 'theft', 'expiry', 'job_issue', 'job_return'
    ]

    def __init__(self, db: Session):
        self.db = db
        self.accounting_service = AccountingService(db)

    def create_product(self, product_data: Dict, branch_id: str) -> Tuple[Product, Dict]:
        """Create a new product with comprehensive validation"""
        try:
            # Validate SKU uniqueness
            existing_product = self.db.query(Product).filter(
                and_(
                    Product.sku == product_data['sku'],
                    Product.branch_id == branch_id
                )
            ).first()

            if existing_product:
                return None, {'success': False, 'error': 'SKU already exists'}

            # Get accounting code for inventory
            inventory_account = self.db.query(AccountingCode).filter(
                and_(
                    AccountingCode.name == 'Inventory',
                    AccountingCode.account_type == 'Asset',
                    AccountingCode.branch_id == branch_id
                )
            ).first()

            if not inventory_account:
                return None, {'success': False, 'error': 'Inventory accounting code not found'}

            # Create product
            product = Product(
                name=product_data['name'],
                sku=product_data['sku'],
                barcode=product_data.get('barcode'),
                description=product_data.get('description'),
                cost_price=Decimal(product_data.get('cost_price', 0)),
                selling_price=Decimal(product_data.get('selling_price', 0)),
                quantity=product_data.get('initial_quantity', 0),
                unit_of_measure=product_data['unit_of_measure'],
                reorder_point=product_data.get('reorder_point', 0),
                is_serialized=product_data.get('is_serialized', False),
                is_perishable=product_data.get('is_perishable', False),
                expiry_date=product_data.get('expiry_date'),
                batch_number=product_data.get('batch_number'),
                accounting_code_id=inventory_account.id,
                branch_id=branch_id
            )

            self.db.add(product)
            self.db.commit()
            self.db.refresh(product)

            # Create opening stock transaction if initial quantity provided
            if product_data.get('initial_quantity', 0) > 0:
                self._create_opening_stock_transaction(product, product_data['initial_quantity'])

            return product, {'success': True, 'product_id': str(product.id)}

        except Exception as e:
            self.db.rollback()
            return None, {'success': False, 'error': str(e)}

    def _create_opening_stock_transaction(self, product: Product, quantity: int) -> None:
        """Create opening stock transaction"""
        transaction = InventoryTransaction(
            product_id=product.id,
            transaction_type='opening_stock',
            quantity=quantity,
            unit_cost=product.cost_price,
            date=date.today(),
            reference=f"Opening stock for {product.name}"
        )

        self.db.add(transaction)
        self.db.commit()

    def update_product_quantity(
        self,
        product_id: str,
        quantity_change: int,
        transaction_type: str,
        reference: str = None,
        branch_id: Optional[str] = None,
        job_card_id: Optional[str] = None,
        note: Optional[str] = None,
        related_purchase_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Update product quantity with transaction tracking"""
        try:
            product = self.db.query(Product).filter(Product.id == product_id).first()

            if not product:
                return False, "Product not found"

            # Validate quantity change
            if transaction_type in ['sale', 'damage', 'theft', 'job_issue'] and quantity_change > 0:
                if product.quantity < quantity_change:
                    return False, f"Insufficient stock. Available: {product.quantity}, Required: {quantity_change}"

            # Update product quantity
            if transaction_type in ['goods_receipt', 'return', 'opening_stock', 'job_return']:
                product.quantity += quantity_change
            else:
                product.quantity -= quantity_change

            # Ensure quantity doesn't go negative
            if product.quantity < 0:
                product.quantity = 0

            # Create inventory transaction
            inventory_transaction = InventoryTransaction(
                product_id=product.id,
                transaction_type=transaction_type,
                quantity=abs(quantity_change),
                unit_cost=product.cost_price,
                date=date.today(),
                reference=reference or f"{transaction_type} transaction"
            )
            inventory_transaction.branch_id = branch_id or product.branch_id
            inventory_transaction.note = note
            inventory_transaction.total_cost = (product.cost_price or 0) * abs(quantity_change)
            inventory_transaction.related_job_card_id = job_card_id
            inventory_transaction.related_purchase_id = related_purchase_id

            self.db.add(inventory_transaction)
            self.db.commit()

            # Create accounting entries for transactions that affect inventory value
            if product.cost_price and product.cost_price > 0:
                self._create_inventory_accounting_entries(
                    product, quantity_change, transaction_type,
                    reference or f"{transaction_type} transaction"
                )

            return True, "Quantity updated successfully"

        except Exception as e:
            self.db.rollback()
            return False, f"Error updating quantity: {str(e)}"

    def create_inventory_adjustment(self, adjustment_data: Dict, branch_id: str) -> Tuple[InventoryAdjustment, Dict]:
        """Create inventory adjustment with accounting entries"""
        try:
            product = self.db.query(Product).filter(
                and_(
                    Product.id == adjustment_data['product_id'],
                    Product.branch_id == branch_id
                )
            ).first()

            if not product:
                return None, {'success': False, 'error': 'Product not found'}

            # Create adjustment record
            adjustment = InventoryAdjustment(
                product_id=product.id,
                quantity_before=product.quantity,
                quantity_after=product.quantity + adjustment_data['quantity_change'],
                quantity_change=adjustment_data['quantity_change'],
                reason=adjustment_data['reason'],
                notes=adjustment_data.get('notes'),
                date=date.today(),
                branch_id=branch_id
            )

            self.db.add(adjustment)
            self.db.flush()

            # Update product quantity
            product.quantity += adjustment_data['quantity_change']
            if product.quantity < 0:
                product.quantity = 0

            # Create inventory transaction
            transaction = InventoryTransaction(
                product_id=product.id,
                transaction_type='adjustment',
                quantity=abs(adjustment_data['quantity_change']),
                unit_cost=product.cost_price,
                date=date.today(),
                reference=f"Adjustment: {adjustment_data['reason']}"
            )

            self.db.add(transaction)

            # Create accounting entries if cost is involved
            if product.cost_price and abs(adjustment_data['quantity_change']) > 0:
                self._create_adjustment_accounting_entries(adjustment, product)

            self.db.commit()
            self.db.refresh(adjustment)

            return adjustment, {'success': True, 'adjustment_id': str(adjustment.id)}

        except Exception as e:
            self.db.rollback()
            return None, {'success': False, 'error': str(e)}

    def _create_adjustment_accounting_entries(self, adjustment: InventoryAdjustment, product: Product) -> None:
        """Create accounting entries for inventory adjustment"""
        # Get required accounting codes
        inventory_account = product.accounting_code
        cogs_account = self.db.query(AccountingCode).filter(
            and_(
                AccountingCode.name == 'Cost of Goods Sold',
                AccountingCode.account_type == 'Expense',
                AccountingCode.branch_id == product.branch_id
            )
        ).first()

        if not cogs_account:
            return  # Skip accounting entries if COGS account not found

        # Calculate adjustment value
        adjustment_value = abs(adjustment.quantity_change) * product.cost_price

        # Create accounting entry
        accounting_entry = AccountingEntry(
            date_prepared=date.today(),
            date_posted=date.today(),
            particulars=f"Inventory adjustment for {product.name}",
            book=f"ADJUSTMENT-{adjustment.id}",
            status='posted',
            branch_id=product.branch_id
        )

        self.db.add(accounting_entry)
        self.db.flush()

        # Create journal entries
        if adjustment.quantity_change > 0:  # Stock increase
            # Debit inventory
            journal_entry1 = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=inventory_account.id,
                entry_type='debit',
                debit_amount=adjustment_value,
                description=f"Inventory increase for {product.name}",
                date=date.today(),
                date_posted=date.today(),
                branch_id=product.branch_id
            )

            # Credit COGS (reversal)
            journal_entry2 = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=cogs_account.id,
                entry_type='credit',
                credit_amount=adjustment_value,
                description=f"COGS reversal for {product.name}",
                date=date.today(),
                date_posted=date.today(),
                branch_id=product.branch_id
            )

            self.db.add(journal_entry1)
            self.db.add(journal_entry2)

        else:  # Stock decrease
            # Debit COGS
            journal_entry1 = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=cogs_account.id,
                entry_type='debit',
                debit_amount=adjustment_value,
                description=f"COGS for {product.name} adjustment",
                date=date.today(),
                date_posted=date.today(),
                branch_id=product.branch_id
            )

            # Credit inventory
            journal_entry2 = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=inventory_account.id,
                entry_type='credit',
                credit_amount=adjustment_value,
                description=f"Inventory decrease for {product.name}",
                date=date.today(),
                date_posted=date.today(),
                branch_id=product.branch_id
            )

            self.db.add(journal_entry1)
            self.db.add(journal_entry2)

    def _create_inventory_accounting_entries(self, product: Product, quantity_change: int,
                                           transaction_type: str, reference: str) -> None:
        """Create accounting entries for inventory transactions"""
        try:
            # Only create entries for transactions that affect inventory value
            if transaction_type not in ['goods_receipt', 'sale', 'return', 'adjustment', 'damage', 'theft']:
                return

            # Get inventory account
            inventory_account = product.accounting_code
            if not inventory_account:
                print(f"Warning: No accounting code found for product {product.name}")
                return

            # Calculate transaction value
            transaction_value = abs(quantity_change) * product.cost_price

            if transaction_value == 0:
                return

            # Create accounting entry
            accounting_entry = AccountingEntry(
                date_prepared=date.today(),
                date_posted=date.today(),
                particulars=f"{transaction_type} for {product.name}",
                book=f"INV-{transaction_type.upper()}-{product.id}",
                status='posted',
                branch_id=product.branch_id or '8f4aaa72-103b-4f40-b586-096675cfb4bf'  # Default to Main Branch
            )

            self.db.add(accounting_entry)
            self.db.flush()

            # Create journal entries based on transaction type
            if transaction_type == 'goods_receipt':
                # Debit inventory (increase assets)
                journal_entry1 = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=inventory_account.id,
                    entry_type='debit',
                    debit_amount=transaction_value,
                    description=f"Inventory receipt for {product.name}",
                    date=date.today(),
                    date_posted=date.today(),
                    branch_id=accounting_entry.branch_id
                )
                self.db.add(journal_entry1)

                # Credit cash (decrease assets)
                cash_account = self.db.query(AccountingCode).filter(
                    and_(
                        AccountingCode.name == 'Cash in Hand',
                        AccountingCode.account_type == 'Asset',
                        AccountingCode.branch_id == product.branch_id
                    )
                ).first()

                if cash_account:
                    journal_entry2 = JournalEntry(
                        accounting_entry_id=accounting_entry.id,
                        accounting_code_id=cash_account.id,
                        entry_type='credit',
                        credit_amount=transaction_value,
                        description=f"Payment for inventory receipt for {product.name}",
                        date=date.today(),
                        date_posted=date.today(),
                        branch_id=accounting_entry.branch_id
                    )
                    self.db.add(journal_entry2)

            elif transaction_type in ['sale', 'damage', 'theft']:
                # For sales/damage/theft: Debit COGS, Credit inventory
                cogs_account = self.db.query(AccountingCode).filter(
                    and_(
                        AccountingCode.name == 'Cost of Goods Sold',
                        AccountingCode.account_type == 'Expense',
                        AccountingCode.branch_id == product.branch_id
                    )
                ).first()

                if cogs_account:
                    # Debit COGS (increase expense)
                    journal_entry1 = JournalEntry(
                        accounting_entry_id=accounting_entry.id,
                        accounting_code_id=cogs_account.id,
                        entry_type='debit',
                        debit_amount=transaction_value,
                        description=f"COGS for {product.name}",
                        date=date.today(),
                        date_posted=date.today(),
                        branch_id=accounting_entry.branch_id
                    )

                    # Credit inventory (decrease assets)
                    journal_entry2 = JournalEntry(
                        accounting_entry_id=accounting_entry.id,
                        accounting_code_id=inventory_account.id,
                        entry_type='credit',
                        credit_amount=transaction_value,
                        description=f"Inventory reduction for {product.name}",
                        date=date.today(),
                        date_posted=date.today(),
                        branch_id=accounting_entry.branch_id
                    )

                    self.db.add(journal_entry1)
                    self.db.add(journal_entry2)
                else:
                    print(f"Warning: COGS account not found for branch {product.branch_id}")

            elif transaction_type == 'return':
                # For returns: Debit inventory, Credit COGS (reverse the sale)
                cogs_account = self.db.query(AccountingCode).filter(
                    and_(
                        AccountingCode.name == 'Cost of Goods Sold',
                        AccountingCode.account_type == 'Expense',
                        AccountingCode.branch_id == product.branch_id
                    )
                ).first()

                if cogs_account:
                    # Debit inventory (increase assets)
                    journal_entry1 = JournalEntry(
                        accounting_entry_id=accounting_entry.id,
                        accounting_code_id=inventory_account.id,
                        entry_type='debit',
                        debit_amount=transaction_value,
                        description=f"Inventory return for {product.name}",
                        date=date.today(),
                        date_posted=date.today(),
                        branch_id=accounting_entry.branch_id
                    )

                    # Credit COGS (decrease expense)
                    journal_entry2 = JournalEntry(
                        accounting_entry_id=accounting_entry.id,
                        accounting_code_id=cogs_account.id,
                        entry_type='credit',
                        credit_amount=transaction_value,
                        description=f"COGS reversal for {product.name}",
                        date=date.today(),
                        date_posted=date.today(),
                        branch_id=accounting_entry.branch_id
                    )

                    self.db.add(journal_entry1)
                    self.db.add(journal_entry2)

            # Update accounting code balances
            if inventory_account:
                self.db.commit()  # Commit first so journal entries are visible
                self.accounting_service.update_accounting_code_balance(inventory_account.id)

        except Exception as e:
            print(f"Error creating inventory accounting entries: {e}")
            self.db.rollback()
            # Don't raise exception - inventory transaction should still succeed even if accounting fails

    def get_inventory_summary(self, branch_id: str) -> Dict:
        """Get comprehensive inventory summary"""
        products = self.db.query(Product).filter(Product.branch_id == branch_id).all()

        total_products = len(products)
        total_value = sum(product.quantity * product.cost_price for product in products if product.cost_price and product.quantity)
        # Handle None values for reorder_point - default to 0 if None
        low_stock_count = sum(1 for product in products if product.quantity is not None and product.reorder_point is not None and product.quantity <= product.reorder_point)
        out_of_stock_count = sum(1 for product in products if product.quantity == 0 or product.quantity is None)

        # Calculate average cost - only for products with cost_price
        products_with_cost = [p for p in products if p.cost_price is not None]
        total_cost = sum(product.cost_price for product in products_with_cost)
        average_cost = total_cost / len(products_with_cost) if products_with_cost else 0

        return {
            'total_products': total_products,
            'total_value': float(total_value),
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
            'average_cost': float(average_cost),
            'products': [
                {
                    'id': str(product.id),
                    'name': product.name,
                    'sku': product.sku,
                    'quantity': product.quantity if product.quantity is not None else 0,
                    'cost_price': float(product.cost_price) if product.cost_price is not None else 0.0,
                    'selling_price': float(product.selling_price) if product.selling_price is not None else 0.0,
                    'value': float((product.quantity or 0) * (product.cost_price or 0)),
                    'status': self._get_stock_status(product)
                }
                for product in products
            ]
        }

    def _get_stock_status(self, product: Product) -> str:
        """Get stock status for a product"""
        quantity = product.quantity if product.quantity is not None else 0
        reorder_point = product.reorder_point if product.reorder_point is not None else 0

        if quantity == 0:
            return 'out_of_stock'
        elif quantity <= reorder_point:
            return 'low_stock'
        else:
            return 'in_stock'

    def get_low_stock_products(self, branch_id: str) -> List[Dict]:
        """Get products with low stock"""
        products = self.db.query(Product).filter(
            and_(
                Product.branch_id == branch_id,
                Product.quantity <= Product.reorder_point
            )
        ).all()

        return [
            {
                'id': str(product.id),
                'name': product.name,
                'sku': product.sku,
                'current_quantity': product.quantity,
                'reorder_point': product.reorder_point,
                'cost_price': float(product.cost_price),
                'selling_price': float(product.selling_price)
            }
            for product in products
        ]

    def get_inventory_transactions(self, product_id: str = None,
                                 start_date: date = None, end_date: date = None) -> List[Dict]:
        """Get inventory transactions with optional filtering"""
        query = self.db.query(InventoryTransaction).join(Product)

        if product_id:
            query = query.filter(InventoryTransaction.product_id == product_id)

        if start_date:
            query = query.filter(InventoryTransaction.date >= start_date)

        if end_date:
            query = query.filter(InventoryTransaction.date <= end_date)

        transactions = query.order_by(InventoryTransaction.date.desc()).all()

        return [
            {
                'id': str(transaction.id),
                'product_name': transaction.product.name,
                'product_sku': transaction.product.sku,
                'transaction_type': transaction.transaction_type,
                'quantity': transaction.quantity,
                'unit_cost': float(transaction.unit_cost),
                'total_value': float(transaction.quantity * transaction.unit_cost),
                'date': transaction.date,
                'reference': transaction.reference
            }
            for transaction in transactions
        ]

    def create_serial_number(self, product_id: str, serial_number: str,
                           status: str = 'available') -> Tuple[SerialNumber, Dict]:
        """Create serial number for serialized product"""
        try:
            product = self.db.query(Product).filter(Product.id == product_id).first()

            if not product:
                return None, {'success': False, 'error': 'Product not found'}

            if not product.is_serialized:
                return None, {'success': False, 'error': 'Product is not serialized'}

            # Check if serial number already exists
            existing_serial = self.db.query(SerialNumber).filter(
                SerialNumber.serial_number == serial_number
            ).first()

            if existing_serial:
                return None, {'success': False, 'error': 'Serial number already exists'}

            # Create serial number
            serial = SerialNumber(
                product_id=product_id,
                serial_number=serial_number,
                status=status,
                date_added=date.today()
            )

            self.db.add(serial)
            self.db.commit()
            self.db.refresh(serial)

            return serial, {'success': True, 'serial_id': str(serial.id)}

        except Exception as e:
            self.db.rollback()
            return None, {'success': False, 'error': str(e)}

    def get_serial_numbers(self, product_id: str = None, status: str = None) -> List[Dict]:
        """Get serial numbers with optional filtering"""
        query = self.db.query(SerialNumber).join(Product)

        if product_id:
            query = query.filter(SerialNumber.product_id == product_id)

        if status:
            query = query.filter(SerialNumber.status == status)

        serials = query.all()

        return [
            {
                'id': str(serial.id),
                'product_name': serial.product.name,
                'product_sku': serial.product.sku,
                'serial_number': serial.serial_number,
                'status': serial.status,
                'date_added': serial.date_added,
                'date_sold': serial.date_sold
            }
            for serial in serials
        ]

    def calculate_fifo_cost(self, product_id: str, quantity: int) -> Decimal:
        """Calculate FIFO cost for a given quantity"""
        # Get inventory transactions in FIFO order
        transactions = self.db.query(InventoryTransaction).filter(
            and_(
                InventoryTransaction.product_id == product_id,
                InventoryTransaction.transaction_type.in_(['goods_receipt', 'opening_stock']),
                InventoryTransaction.quantity > 0
            )
        ).order_by(InventoryTransaction.date, InventoryTransaction.created_at).all()

        remaining_quantity = quantity
        total_cost = Decimal('0')

        for transaction in transactions:
            if remaining_quantity <= 0:
                break

            available_quantity = min(remaining_quantity, transaction.quantity)
            total_cost += available_quantity * transaction.unit_cost
            remaining_quantity -= available_quantity

        return total_cost

    def calculate_average_cost(self, product_id: str) -> Decimal:
        """Calculate average cost for a product"""
        # Get total quantity and total cost from receipts
        result = self.db.query(
            func.sum(InventoryTransaction.quantity).label('total_quantity'),
            func.sum(InventoryTransaction.quantity * InventoryTransaction.unit_cost).label('total_cost')
        ).filter(
            and_(
                InventoryTransaction.product_id == product_id,
                InventoryTransaction.transaction_type.in_(['goods_receipt', 'opening_stock']),
                InventoryTransaction.quantity > 0
            )
        ).first()

        if result.total_quantity and result.total_quantity > 0:
            return result.total_cost / result.total_quantity
        else:
            return Decimal('0')

    def get_inventory_valuation(self, branch_id: str, valuation_method: str = 'average') -> Dict:
        """Get inventory valuation report"""
        products = self.db.query(Product).filter(Product.branch_id == branch_id).all()

        total_value = Decimal('0')
        valuation_details = []

        for product in products:
            if valuation_method == 'fifo':
                value = self.calculate_fifo_cost(product.id, product.quantity)
            else:  # average
                value = self.calculate_average_cost(product.id) * product.quantity

            total_value += value

            valuation_details.append({
                'product_name': product.name,
                'sku': product.sku,
                'quantity': product.quantity,
                'unit_cost': float(self.calculate_average_cost(product.id)),
                'total_value': float(value),
                'valuation_method': valuation_method
            })

        return {
            'valuation_method': valuation_method,
            'total_value': float(total_value),
            'product_count': len(products),
            'details': valuation_details
        }

    def issue_to_production(self, assembled_product_id: str, quantity: int, branch_id: str) -> Tuple[bool, str]:
        """Issue BOM components to WIP for production (Dr WIP, Cr Inventory)"""
        try:
            from app.models.inventory import ProductAssembly
            assembled_product = self.db.query(Product).filter(
                and_(Product.id == assembled_product_id, Product.branch_id == branch_id)
            ).first()
            if not assembled_product:
                return False, "Assembled product not found"

            bom_items = self.db.query(ProductAssembly).filter(
                ProductAssembly.assembled_product_id == assembled_product_id
            ).all()
            if not bom_items:
                return False, "No BOM defined for assembled product"

            # Find WIP accounting code (fallback by name)
            wip_code = self.db.query(AccountingCode).filter(
                and_(AccountingCode.name.ilike('%work in progress%'), AccountingCode.account_type == 'Asset', AccountingCode.branch_id == branch_id)
            ).first()
            if not wip_code:
                # Fallback: try a generic 'WIP' name
                wip_code = self.db.query(AccountingCode).filter(
                    and_(AccountingCode.name.ilike('%wip%'), AccountingCode.account_type == 'Asset', AccountingCode.branch_id == branch_id)
                ).first()

            accounting_entry = AccountingEntry(
                date_prepared=date.today(),
                date_posted=date.today(),
                particulars=f"Issue to WIP for {assembled_product.name} x{quantity}",
                book=f"WIP-ISSUE-{assembled_product_id}",
                status='posted',
                branch_id=branch_id
            )
            self.db.add(accounting_entry)
            self.db.flush()

            total_issue_value = Decimal('0')

            for bom in bom_items:
                component = self.db.query(Product).filter(Product.id == bom.component_id).first()
                if not component:
                    continue
                required_qty = int(Decimal(str(bom.quantity)) * Decimal(str(quantity)))
                if component.quantity < required_qty:
                    return False, f"Insufficient stock for component {component.name}"

                # Cost basis: use component.cost_price or BOM unit_cost
                unit_cost = Decimal(component.cost_price or 0)
                if bom.unit_cost:
                    unit_cost = Decimal(bom.unit_cost)
                line_value = unit_cost * Decimal(required_qty)
                total_issue_value += line_value

                # Reduce inventory
                component.quantity -= required_qty

                # Inventory transaction
                inv_tx = InventoryTransaction(
                    product_id=component.id,
                    transaction_type='issue_to_wip',
                    quantity=required_qty,
                    unit_cost=unit_cost,
                    date=date.today(),
                    reference=f"Issue to WIP for {assembled_product.name}",
                    branch_id=branch_id
                )
                self.db.add(inv_tx)

                # Accounting: Dr WIP, Cr Inventory
                if wip_code:
                    dr = JournalEntry(
                        accounting_entry_id=accounting_entry.id,
                        accounting_code_id=wip_code.id,
                        entry_type='debit',
                        debit_amount=line_value,
                        description=f"WIP issue: {component.name}",
                        date=date.today(),
                        date_posted=date.today(),
                        branch_id=branch_id
                    )
                    self.db.add(dr)

                if component.accounting_code_id:
                    cr = JournalEntry(
                        accounting_entry_id=accounting_entry.id,
                        accounting_code_id=component.accounting_code_id,
                        entry_type='credit',
                        credit_amount=line_value,
                        description=f"Inventory credit: {component.name}",
                        date=date.today(),
                        date_posted=date.today(),
                        branch_id=branch_id
                    )
                    self.db.add(cr)

            self.db.commit()
            return True, "Issued components to WIP"
        except Exception as e:
            self.db.rollback()
            return False, f"Error issuing to WIP: {str(e)}"

    def complete_production(self, assembled_product_id: str, quantity: int, branch_id: str) -> Tuple[bool, str]:
        """Receive finished goods from WIP (Dr Finished Goods, Cr WIP)"""
        try:
            assembled_product = self.db.query(Product).filter(
                and_(Product.id == assembled_product_id, Product.branch_id == branch_id)
            ).first()
            if not assembled_product:
                return False, "Assembled product not found"

            # Compute WIP value to clear: use BOM * cost as approximation
            from app.models.inventory import ProductAssembly
            bom_items = self.db.query(ProductAssembly).filter(
                ProductAssembly.assembled_product_id == assembled_product_id
            ).all()

            total_wip_value = Decimal('0')
            for bom in bom_items:
                component = self.db.query(Product).filter(Product.id == bom.component_id).first()
                unit_cost = Decimal(bom.unit_cost) if bom.unit_cost else Decimal(component.cost_price or 0)
                total_wip_value += unit_cost * Decimal(bom.quantity) * Decimal(str(quantity))

            # Update finished goods inventory
            assembled_product.quantity += quantity

            inv_tx = InventoryTransaction(
                product_id=assembled_product.id,
                transaction_type='production_receipt',
                quantity=quantity,
                unit_cost=assembled_product.cost_price or (total_wip_value / Decimal(max(quantity,1)) if total_wip_value else 0),
                date=date.today(),
                reference=f"Production receipt for {assembled_product.name}",
                branch_id=branch_id
            )
            self.db.add(inv_tx)

            # Accounting: Dr Inventory (finished goods), Cr WIP
            fg_code_id = assembled_product.accounting_code_id
            wip_code = self.db.query(AccountingCode).filter(
                and_(AccountingCode.name.ilike('%work in progress%'), AccountingCode.account_type == 'Asset', AccountingCode.branch_id == branch_id)
            ).first()
            if not wip_code:
                wip_code = self.db.query(AccountingCode).filter(
                    and_(AccountingCode.name.ilike('%wip%'), AccountingCode.account_type == 'Asset', AccountingCode.branch_id == branch_id)
                ).first()

            accounting_entry = AccountingEntry(
                date_prepared=date.today(),
                date_posted=date.today(),
                particulars=f"Complete production for {assembled_product.name} x{quantity}",
                book=f"WIP-COMP-{assembled_product_id}",
                status='posted',
                branch_id=branch_id
            )
            self.db.add(accounting_entry)
            self.db.flush()

            if fg_code_id and wip_code and total_wip_value > 0:
                dr = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=fg_code_id,
                    entry_type='debit',
                    debit_amount=total_wip_value,
                    description=f"Finished goods receipt: {assembled_product.name}",
                    date=date.today(),
                    date_posted=date.today(),
                    branch_id=branch_id
                )
                self.db.add(dr)

                cr = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=wip_code.id,
                    entry_type='credit',
                    credit_amount=total_wip_value,
                    description=f"Clear WIP to FG: {assembled_product.name}",
                    date=date.today(),
                    date_posted=date.today(),
                    branch_id=branch_id
                )
                self.db.add(cr)

            self.db.commit()
            return True, "Completed production and posted FG receipt"
        except Exception as e:
            self.db.rollback()
            return False, f"Error completing production: {str(e)}"

    def get_stock_movement_report(self, branch_id: str, start_date: date = None, end_date: date = None) -> Dict:
        """Get inventory stock movement report"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import desc

            if not end_date:
                end_date = date.today()
            if not start_date:
                start_date = end_date - timedelta(days=30)

            # Get inventory transactions for the period - fix query
            transactions = self.db.query(InventoryTransaction).join(Product).filter(
                and_(
                    Product.branch_id == branch_id,
                    InventoryTransaction.date >= start_date,
                    InventoryTransaction.date <= end_date
                )
            ).order_by(desc(InventoryTransaction.date)).all()

            movement_data = []
            for txn in transactions:
                product = txn.product
                movement_data.append({
                    'date': txn.date.isoformat(),
                    'product_id': str(product.id),
                    'product_name': product.name,
                    'product_sku': product.sku,
                    'transaction_type': txn.transaction_type,
                    'quantity': txn.quantity,
                    'unit_cost': float(txn.unit_cost or 0),
                    'total_value': float(txn.quantity * (txn.unit_cost or 0)),
                    'reference': txn.reference,
                    'running_balance': product.quantity  # Current balance
                })

            return {
                'success': True,
                'data': movement_data,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'total_transactions': len(movement_data),
                'generated_at': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'data': [],
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }

    def get_inventory_aging_report(self, branch_id: str) -> Dict:
        """Get inventory aging analysis based on last movement date"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import func, desc

            products = self.db.query(Product).filter(Product.branch_id == branch_id).all()

            aging_buckets = {
                '0-30_days': {'count': 0, 'value': 0.0, 'products': []},
                '31-60_days': {'count': 0, 'value': 0.0, 'products': []},
                '61-90_days': {'count': 0, 'value': 0.0, 'products': []},
                '90+_days': {'count': 0, 'value': 0.0, 'products': []}
            }

            today = date.today()

            for product in products:
                if product.quantity <= 0:
                    continue

                # Get last transaction date - fix field name
                last_transaction = self.db.query(InventoryTransaction).filter(
                    InventoryTransaction.product_id == product.id
                ).order_by(desc(InventoryTransaction.date)).first()

                last_movement_date = last_transaction.date if last_transaction else today
                days_since_movement = (today - last_movement_date).days

                product_value = float(product.quantity * (product.cost_price or 0))
                product_data = {
                    'id': str(product.id),
                    'name': product.name,
                    'sku': product.sku,
                    'quantity': product.quantity,
                    'value': product_value,
                    'days_since_movement': days_since_movement,
                    'last_movement_date': last_movement_date.isoformat()
                }

                if days_since_movement <= 30:
                    aging_buckets['0-30_days']['count'] += 1
                    aging_buckets['0-30_days']['value'] += product_value
                    aging_buckets['0-30_days']['products'].append(product_data)
                elif days_since_movement <= 60:
                    aging_buckets['31-60_days']['count'] += 1
                    aging_buckets['31-60_days']['value'] += product_value
                    aging_buckets['31-60_days']['products'].append(product_data)
                elif days_since_movement <= 90:
                    aging_buckets['61-90_days']['count'] += 1
                    aging_buckets['61-90_days']['value'] += product_value
                    aging_buckets['61-90_days']['products'].append(product_data)
                else:
                    aging_buckets['90+_days']['count'] += 1
                    aging_buckets['90+_days']['value'] += product_value
                    aging_buckets['90+_days']['products'].append(product_data)

            return {
                'success': True,
                'data': {
                    'aging_buckets': aging_buckets,
                    'total_value': sum(bucket['value'] for bucket in aging_buckets.values()),
                    'total_products': sum(bucket['count'] for bucket in aging_buckets.values())
                },
                'generated_at': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'data': {'aging_buckets': {}, 'total_value': 0, 'total_products': 0},
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }

    def get_abc_analysis(self, branch_id: str) -> Dict:
        """Get ABC analysis based on inventory value and turnover"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import func, desc

            products = self.db.query(Product).filter(
                and_(Product.branch_id == branch_id, Product.quantity > 0)
            ).all()

            # Calculate product values and turnover for last 90 days
            end_date = date.today()
            start_date = end_date - timedelta(days=90)

            product_analysis = []
            total_value = 0

            for product in products:
                # Calculate inventory value
                inventory_value = float(product.quantity * (product.cost_price or 0))

                # Calculate turnover (sales in last 90 days) - fix field name
                turnover = self.db.query(func.sum(InventoryTransaction.quantity)).filter(
                    and_(
                        InventoryTransaction.product_id == product.id,
                        InventoryTransaction.transaction_type == 'sale',
                        InventoryTransaction.date >= start_date,
                        InventoryTransaction.date <= end_date
                    )
                ).scalar() or 0

                product_analysis.append({
                    'id': str(product.id),
                    'name': product.name,
                    'sku': product.sku,
                    'inventory_value': inventory_value,
                    'turnover': abs(int(turnover)),
                    'turnover_value': float(abs(turnover) * (product.selling_price or 0))
                })

                total_value += inventory_value

            # Sort by inventory value (descending)
            product_analysis.sort(key=lambda x: x['inventory_value'], reverse=True)

            # Calculate ABC categories
            cumulative_value = 0
            abc_categories = {'A': [], 'B': [], 'C': []}

            for product in product_analysis:
                cumulative_value += product['inventory_value']
                cumulative_percentage = (cumulative_value / total_value * 100) if total_value > 0 else 0

                if cumulative_percentage <= 70:  # A items: top 70% of value
                    product['category'] = 'A'
                    abc_categories['A'].append(product)
                elif cumulative_percentage <= 90:  # B items: next 20% of value
                    product['category'] = 'B'
                    abc_categories['B'].append(product)
                else:  # C items: remaining 10% of value
                    product['category'] = 'C'
                    abc_categories['C'].append(product)

            return {
                'success': True,
                'data': {
                    'abc_categories': abc_categories,
                    'summary': {
                        'total_products': len(product_analysis),
                        'total_value': total_value,
                        'category_A_count': len(abc_categories['A']),
                        'category_B_count': len(abc_categories['B']),
                        'category_C_count': len(abc_categories['C']),
                        'category_A_value': sum(p['inventory_value'] for p in abc_categories['A']),
                        'category_B_value': sum(p['inventory_value'] for p in abc_categories['B']),
                        'category_C_value': sum(p['inventory_value'] for p in abc_categories['C'])
                    }
                },
                'generated_at': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'data': {'abc_categories': {}, 'summary': {}},
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }

    def get_category_analysis(self, branch_id: str) -> Dict:
        """Get detailed category analysis with stock levels and values"""
        try:
            from sqlalchemy import func

            # Get products grouped by category
            category_data = self.db.query(
                Product.category,
                func.count(Product.id).label('product_count'),
                func.sum(Product.quantity).label('total_quantity'),
                func.sum(Product.quantity * Product.cost_price).label('total_value'),
                func.avg(Product.cost_price).label('avg_cost_price'),
                func.sum(case((Product.quantity <= Product.reorder_point, 1), else_=0)).label('low_stock_count')
            ).filter(Product.branch_id == branch_id).group_by(Product.category).all()

            categories = []
            total_products = 0
            total_value = 0

            for row in category_data:
                category_name = row.category or 'Uncategorized'
                category_total_value = float(row.total_value or 0)
                total_products += row.product_count or 0
                total_value += category_total_value

                categories.append({
                    'category': category_name,
                    'product_count': row.product_count or 0,
                    'total_quantity': row.total_quantity or 0,
                    'total_value': category_total_value,
                    'value': category_total_value,  # Add alias for frontend compatibility
                    'avg_cost_price': float(row.avg_cost_price or 0),
                    'low_stock_count': row.low_stock_count or 0,
                    'percentage_of_total': 0  # Will calculate after we have total
                })

            # Calculate percentages
            for category in categories:
                category['percentage_of_total'] = (category['total_value'] / total_value * 100) if total_value > 0 else 0

            # Sort by total value descending
            categories.sort(key=lambda x: x['total_value'], reverse=True)

            return {
                'success': True,
                'data': {
                    'categories': categories,
                    'summary': {
                        'total_categories': len(categories),
                        'total_products': total_products,
                        'total_value': total_value
                    }
                },
                'generated_at': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'data': {'categories': [], 'summary': {}},
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }

    def get_valuation_methods_comparison(self, branch_id: str) -> Dict:
        """Compare FIFO, LIFO, and Average Cost valuation methods"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import func, desc

            products = self.db.query(Product).filter(
                and_(Product.branch_id == branch_id, Product.quantity > 0)
            ).all()

            total_fifo = 0
            total_lifo = 0
            total_avg_cost = 0

            product_valuations = []

            for product in products:
                quantity = product.quantity

                # Get recent transactions for FIFO/LIFO calculation - fix field name
                recent_receipts = self.db.query(InventoryTransaction).filter(
                    and_(
                        InventoryTransaction.product_id == product.id,
                        InventoryTransaction.transaction_type.in_(['goods_receipt', 'opening_stock']),
                        InventoryTransaction.quantity > 0
                    )
                ).order_by(InventoryTransaction.date).all()

                # FIFO calculation (First In, First Out)
                fifo_value = 0
                remaining_qty = quantity
                for txn in recent_receipts:
                    if remaining_qty <= 0:
                        break
                    qty_to_value = min(remaining_qty, txn.quantity)
                    fifo_value += qty_to_value * float(txn.unit_cost or product.cost_price or 0)
                    remaining_qty -= qty_to_value

                # LIFO calculation (Last In, First Out)
                lifo_value = 0
                remaining_qty = quantity
                for txn in reversed(recent_receipts):
                    if remaining_qty <= 0:
                        break
                    qty_to_value = min(remaining_qty, txn.quantity)
                    lifo_value += qty_to_value * float(txn.unit_cost or product.cost_price or 0)
                    remaining_qty -= qty_to_value

                # Average Cost calculation
                avg_cost_value = quantity * float(product.cost_price or 0)

                product_valuations.append({
                    'id': str(product.id),
                    'name': product.name,
                    'sku': product.sku,
                    'quantity': quantity,
                    'fifo_value': fifo_value,
                    'lifo_value': lifo_value,
                    'avg_cost_value': avg_cost_value,
                    'fifo_unit_cost': fifo_value / quantity if quantity > 0 else 0,
                    'lifo_unit_cost': lifo_value / quantity if quantity > 0 else 0,
                    'avg_unit_cost': float(product.cost_price or 0)
                })

                total_fifo += fifo_value
                total_lifo += lifo_value
                total_avg_cost += avg_cost_value

            return {
                'success': True,
                'data': {
                    'product_valuations': product_valuations,
                    'summary': {
                        'total_products': len(product_valuations),
                        'fifo_total': total_fifo,
                        'lifo_total': total_lifo,
                        'avg_cost_total': total_avg_cost,
                        'fifo_vs_avg_diff': total_fifo - total_avg_cost,
                        'lifo_vs_avg_diff': total_lifo - total_avg_cost,
                        'fifo_vs_lifo_diff': total_fifo - total_lifo
                    }
                },
                'generated_at': datetime.now().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'data': {'product_valuations': [], 'summary': {}},
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }
