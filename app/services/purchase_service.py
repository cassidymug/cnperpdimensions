from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.purchases import Purchase, PurchaseItem, PurchaseOrder, PurchaseOrderItem, Supplier
from app.models.inventory import Product, InventoryTransaction
from app.models.accounting import AccountingCode, AccountingEntry, JournalEntry
from app.models.accounting_dimensions import AccountingDimensionAssignment, AccountingDimensionValue
from app.models.user import User
from app.core.config import settings
from app.services.landed_cost_service import LandedCostService


class PurchaseService:
    """Comprehensive purchase business logic service with IFRS compliance"""

    PURCHASE_STATUSES = ['pending', 'approved', 'received', 'cancelled', 'paid']
    PAYMENT_METHODS = ['cash', 'bank_transfer', 'credit', 'check']

    def __init__(self, db: Session):
        self.db = db

    def create_purchase(self, purchase_data: Dict, items: List[Dict], branch_id: str) -> Tuple[Purchase, Dict]:
        """
        Create a new purchase with comprehensive business logic and accounting integration

        Args:
            purchase_data: Purchase header data
            items: List of purchase items
            branch_id: Branch ID

        Returns:
            Tuple of (purchase, result_dict)
        """
        try:
            # Validate purchase data
            self._validate_purchase_data(purchase_data, items)

            # Get supplier
            supplier = self.db.query(Supplier).filter(
                Supplier.id == purchase_data['supplier_id'],
                Supplier.branch_id == branch_id
            ).first()

            if not supplier:
                raise ValueError("Supplier not found")

            # Create purchase record
            purchase = Purchase(
                supplier_id=supplier.id,
                purchase_date=purchase_data.get('purchase_date', date.today()),
                total_amount=Decimal('0'),
                total_vat_amount=Decimal('0'),
                total_amount_ex_vat=Decimal('0'),
                status='pending',
                branch_id=branch_id,
                reference=purchase_data.get('reference'),
                notes=purchase_data.get('notes'),
                created_by=purchase_data.get('created_by'),
                payment_account_id=purchase_data.get('payment_account_id')
            )

            self.db.add(purchase)
            self.db.flush()

            # Calculate totals and create purchase items
            total_amount = Decimal('0')
            total_vat_amount = Decimal('0')

            for item_data in items:
                product = self.db.query(Product).filter(
                    Product.id == item_data['product_id'],
                    Product.branch_id == branch_id
                ).first()

                if not product:
                    raise ValueError(f"Product {item_data['product_id']} not found")

                quantity = Decimal(str(item_data['quantity']))
                cost = Decimal(str(item_data['cost']))
                vat_rate = Decimal(str(item_data.get('vat_rate', settings.default_vat_rate)))

                # Check if item is taxable (from frontend or product default)
                is_taxable = item_data.get('is_taxable', True)
                if hasattr(product, 'is_taxable'):
                    is_taxable = product.is_taxable and is_taxable  # Both product and item must be taxable

                # Calculate line totals
                line_total = quantity * cost

                # Only calculate VAT if item is taxable
                if is_taxable:
                    vat_amount = line_total * (vat_rate / 100)
                else:
                    vat_amount = Decimal('0')

                # Create purchase item
                purchase_item = PurchaseItem(
                    product_id=product.id,
                    quantity=quantity,
                    cost=cost,
                    total_cost=line_total,
                    vat_amount=vat_amount,
                    vat_rate=vat_rate,
                    description=item_data.get('description'),
                    notes=item_data.get('notes')
                )

                purchase.purchase_items.append(purchase_item)
                total_amount += line_total
                total_vat_amount += vat_amount

                # Update inventory if received
                if purchase_data.get('status') == 'received':
                    self._update_inventory(product, quantity, 'purchase')

            # Get default Input VAT account (1160 - VAT Receivable)
            input_vat_account = None
            if total_vat_amount > 0:
                input_vat_account = self.db.query(AccountingCode).filter(
                    AccountingCode.code == '1160'
                ).first()

            # Set final totals
            purchase.total_amount = total_amount
            purchase.total_vat_amount = total_vat_amount
            purchase.total_amount_ex_vat = total_amount
            purchase.input_vat_account_id = input_vat_account.id if input_vat_account else None

            # Create accounting entries
            self._create_purchase_accounting_entries(purchase, supplier)

            self.db.commit()
            return purchase, {'success': True, 'purchase_id': str(purchase.id)}

        except Exception as e:
            self.db.rollback()
            return None, {'success': False, 'error': str(e)}

    def _validate_purchase_data(self, purchase_data: Dict, items: List[Dict]) -> None:
        """Validate purchase data"""
        if not purchase_data.get('supplier_id'):
            raise ValueError("Supplier ID is required")

        if not items:
            raise ValueError("At least one item is required")

        for item in items:
            if not item.get('product_id'):
                raise ValueError("Product ID is required for all items")
            if not item.get('quantity') or Decimal(str(item['quantity'])) <= 0:
                raise ValueError("Valid quantity is required for all items")
            if not item.get('cost') or Decimal(str(item['cost'])) <= 0:
                raise ValueError("Valid cost is required for all items")

    def _update_inventory(self, product: Product, quantity: Decimal, transaction_type: str) -> None:
        """Update inventory for purchase"""
        # Create inventory transaction
        inventory_transaction = InventoryTransaction(
            product_id=product.id,
            quantity=quantity,
            transaction_type=transaction_type,
            reference=f"Purchase transaction",
            branch_id=product.branch_id
        )

        self.db.add(inventory_transaction)

        # Update product stock
        product.current_stock += quantity

    def _create_purchase_accounting_entries(self, purchase: Purchase, supplier: Supplier) -> None:
        """Create comprehensive accounting entries for the purchase with proper VAT handling"""
        # Get required accounting codes using exact names from seeded accounts
        inventory_account = self._get_accounting_code('Merchandise Inventory', 'Asset')
        accounts_payable = self._get_accounting_code('Accounts Payable', 'Liability')
        cash_account = self._get_accounting_code('Cash in Hand', 'Asset')
        vat_receivable = self._get_accounting_code('VAT Receivable', 'Asset')

        # Get supplier's specific accounting code for expense tracking
        supplier_expense_account = supplier.accounting_code

        if not supplier_expense_account:
            # Use a default expense account if supplier doesn't have one assigned
            supplier_expense_account = self._get_accounting_code('General Expenses', 'Expense')

        # Create accounting entry header
        accounting_entry = AccountingEntry(
            date_prepared=purchase.purchase_date,
            date_posted=purchase.purchase_date,
            particulars=f"Purchase from {supplier.name} - {purchase.reference}",
            book=f"PURCHASE-{purchase.id}",
            status='posted',
            branch_id=purchase.branch_id
        )

        self.db.add(accounting_entry)
        self.db.flush()

        # Create journal entries list
        entries = []

        # Separate inventory and non-inventory amounts
        inventory_amount = Decimal('0')
        expense_amount = Decimal('0')

        for item in purchase.purchase_items:
            if hasattr(item.product, 'product_type') and item.product.product_type == 'inventory':
                inventory_amount += item.total_cost
            else:
                expense_amount += item.total_cost

        # 1. Debit Inventory (for inventory items)
        if inventory_amount > 0:
            inventory_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=inventory_account.id,
                entry_type='debit',
                debit_amount=inventory_amount,
                credit_amount=Decimal('0'),
                description=f"Inventory purchase from {supplier.name}",
                date=purchase.purchase_date,
                branch_id=purchase.branch_id
            )
            entries.append(inventory_entry)

        # 2. Debit Expense account (for non-inventory items)
        if expense_amount > 0:
            expense_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=supplier_expense_account.id,
                entry_type='debit',
                debit_amount=expense_amount,
                credit_amount=Decimal('0'),
                description=f"Expense purchase from {supplier.name}",
                date=purchase.purchase_date,
                branch_id=purchase.branch_id
            )
            entries.append(expense_entry)

        # 3. Debit VAT Receivable (Input VAT - if applicable)
        if purchase.total_vat_amount > 0:
            vat_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=vat_receivable.id,
                entry_type='debit',
                debit_amount=purchase.total_vat_amount,
                credit_amount=Decimal('0'),
                description=f"VAT receivable (Input VAT) from {supplier.name}",
                date=purchase.purchase_date,
                branch_id=purchase.branch_id
            )
            entries.append(vat_entry)

        # 4. Credit Cash or Accounts Payable (total including VAT)
        total_payment = purchase.total_amount + purchase.total_vat_amount

        if purchase.payment_method == 'cash':
            payment_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=cash_account.id,
                entry_type='credit',
                debit_amount=Decimal('0'),
                credit_amount=total_payment,
                description=f"Cash payment to {supplier.name}",
                date=purchase.purchase_date,
                branch_id=purchase.branch_id
            )
        else:
            payment_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=accounts_payable.id,
                entry_type='credit',
                debit_amount=Decimal('0'),
                credit_amount=total_payment,
                description=f"Accounts payable to {supplier.name}",
                date=purchase.purchase_date,
                branch_id=purchase.branch_id
            )

        entries.append(payment_entry)

        # Add all entries to database
        for entry in entries:
            self.db.add(entry)

        # Validate journal entry balance
        total_debits = sum(entry.debit_amount for entry in entries)
        total_credits = sum(entry.credit_amount for entry in entries)

        if total_debits != total_credits:
            raise ValueError(f"Unbalanced journal for purchase {purchase.reference}: debits {total_debits} != credits {total_credits}")

        self.db.flush()

    def _get_accounting_code(self, name: str, account_type: str) -> AccountingCode:
        """Get accounting code by name and type with fallback options"""
        # Try exact match first
        code = self.db.query(AccountingCode).filter(
            and_(
                AccountingCode.name == name,
                AccountingCode.account_type == account_type
            )
        ).first()

        if code:
            return code

        # Fallback options for common accounts
        fallback_mapping = {
            ('Merchandise Inventory', 'Asset'): [('Inventory', 'Asset'), ('Finished Goods', 'Asset')],
            ('Accounts Payable', 'Liability'): [('Trade Creditors', 'Liability'), ('Creditors', 'Liability')],
            ('Cash in Hand', 'Asset'): [('Cash', 'Asset'), ('Petty Cash', 'Asset')],
            ('VAT Receivable', 'Asset'): [('Input VAT', 'Asset'), ('VAT Claimable', 'Asset')],
            ('General Expenses', 'Expense'): [('Operating Expenses', 'Expense'), ('Admin Expenses', 'Expense')]
        }

        # Try fallback names
        fallbacks = fallback_mapping.get((name, account_type), [])
        for fallback_name, fallback_type in fallbacks:
            code = self.db.query(AccountingCode).filter(
                and_(
                    AccountingCode.name == fallback_name,
                    AccountingCode.account_type == fallback_type
                )
            ).first()
            if code:
                return code

        # Last resort: find any account of the right type
        code = self.db.query(AccountingCode).filter(
            AccountingCode.account_type == account_type
        ).first()

        if not code:
            raise ValueError(f"No accounting code found for '{name}' ({account_type}) or any {account_type} account. Please run account seeding.")

        return code

    def approve_purchase(self, purchase_id: str, approved_by: str, branch_id: str) -> Tuple[bool, str]:
        """Approve a purchase order"""
        try:
            purchase = self.db.query(Purchase).filter(
                Purchase.id == purchase_id,
                Purchase.branch_id == branch_id
            ).first()

            if not purchase:
                return False, "Purchase not found"

            if purchase.status != 'pending':
                return False, "Purchase is not in pending status"

            purchase.status = 'approved'
            purchase.approved_by = approved_by
            purchase.approved_at = date.today()

            self.db.commit()
            return True, "Purchase approved successfully"

        except Exception as e:
            self.db.rollback()
            return False, str(e)

    def receive_purchase(self, purchase_id: str, branch_id: str) -> Tuple[bool, str]:
        """Mark purchase as received and update inventory"""
        try:
            purchase = self.db.query(Purchase).filter(
                Purchase.id == purchase_id,
                Purchase.branch_id == branch_id
            ).first()

            if not purchase:
                return False, "Purchase not found"

            if purchase.status not in ['approved', 'pending']:
                return False, "Purchase cannot be received in current status"

            purchase.status = 'received'
            purchase.received_at = date.today()

            # Update inventory for all items
            for item in purchase.purchase_items:
                self._update_inventory(item.product, item.quantity, 'purchase')

            # Check for and allocate landed costs
            landed_cost_service = LandedCostService(self.db)
            for lc in purchase.landed_costs:
                if lc.status == 'confirmed':
                    landed_cost_service.allocate_landed_cost(lc.id)

            self.db.commit()
            return True, "Purchase received successfully"

        except Exception as e:
            self.db.rollback()
            return False, str(e)

    def pay_purchase(self, purchase_id: str, payment_data: Dict, branch_id: str) -> Tuple[bool, str]:
        """Record payment for a purchase"""
        try:
            purchase = self.db.query(Purchase).filter(
                Purchase.id == purchase_id,
                Purchase.branch_id == branch_id
            ).first()

            if not purchase:
                return False, "Purchase not found"

            payment_amount = Decimal(str(payment_data['amount']))

            if payment_amount > (purchase.total_amount + purchase.total_vat_amount - purchase.amount_paid):
                return False, "Payment amount exceeds outstanding balance"

            purchase.amount_paid += payment_amount

            if purchase.amount_paid >= (purchase.total_amount + purchase.total_vat_amount):
                purchase.status = 'paid'

            # Create payment accounting entries
            self._create_payment_accounting_entries(purchase, payment_data)

            self.db.commit()
            return True, "Payment recorded successfully"

        except Exception as e:
            self.db.rollback()
            return False, str(e)

    def _create_payment_accounting_entries(self, purchase: Purchase, payment_data: Dict) -> None:
        """Create accounting entries for purchase payment"""
        # Get required accounting codes
        cash_account = self._get_accounting_code('Cash', 'Asset')
        bank_account = self._get_accounting_code('Bank Account', 'Asset')
        accounts_payable = self._get_accounting_code('Accounts Payable', 'Liability')

        payment_amount = Decimal(str(payment_data['amount']))
        payment_method = payment_data.get('payment_method', 'cash')

        # Create accounting entry
        accounting_entry = AccountingEntry(
            date_prepared=date.today(),
            date_posted=date.today(),
            particulars=f"Payment to {purchase.supplier.name}",
            book=f"PAYMENT-{purchase.id}",
            status='posted',
            branch_id=purchase.branch_id
        )

        self.db.add(accounting_entry)
        self.db.flush()

        # Debit Accounts Payable
        ap_entry = JournalEntry(
            accounting_entry_id=accounting_entry.id,
            accounting_code_id=accounts_payable.id,
            entry_type='debit',
            amount=payment_amount,
            description=f"Payment to {purchase.supplier.name}",
            date=date.today(),
            date_posted=date.today(),
            branch_id=purchase.branch_id
        )
        ap_entry.debit_amount = payment_amount
        ap_entry.credit_amount = Decimal('0')
        self.db.add(ap_entry)

        # Credit Cash or Bank
        if payment_method == 'cash':
            payment_account = cash_account
        else:
            payment_account = bank_account

        payment_entry = JournalEntry(
            accounting_entry_id=accounting_entry.id,
            accounting_code_id=payment_account.id,
            entry_type='credit',
            amount=payment_amount,
            description=f"Payment to {purchase.supplier.name}",
            date=date.today(),
            date_posted=date.today(),
            branch_id=purchase.branch_id
        )
        payment_entry.credit_amount = payment_amount
        payment_entry.debit_amount = Decimal('0')
        self.db.add(payment_entry)

    def get_supplier_expense_summary(self, supplier_id: str, start_date: date, end_date: date, branch_id: str) -> Dict:
        """Get expense summary for a specific supplier"""
        try:
            supplier = self.db.query(Supplier).filter(
                Supplier.id == supplier_id,
                Supplier.branch_id == branch_id
            ).first()

            if not supplier:
                return {'error': 'Supplier not found'}

            # Get all purchases for the supplier in date range
            purchases = self.db.query(Purchase).filter(
                Purchase.supplier_id == supplier_id,
                Purchase.purchase_date >= start_date,
                Purchase.purchase_date <= end_date,
                Purchase.branch_id == branch_id
            ).all()

            total_amount = sum(p.total_amount for p in purchases)
            total_vat = sum(p.total_vat_amount for p in purchases)
            total_paid = sum(p.amount_paid for p in purchases)

            # Get expense breakdown by accounting code
            expense_breakdown = {}
            for purchase in purchases:
                for item in purchase.purchase_items:
                    if item.product.product_type != 'inventory':
                        expense_type = supplier.accounting_code.name if supplier.accounting_code else 'Other Expenses'
                        if expense_type not in expense_breakdown:
                            expense_breakdown[expense_type] = Decimal('0')
                        expense_breakdown[expense_type] += item.total_cost

            return {
                'supplier_name': supplier.name,
                'period': f"{start_date} to {end_date}",
                'total_purchases': len(purchases),
                'total_amount': total_amount,
                'total_vat': total_vat,
                'total_paid': total_paid,
                'outstanding': total_amount + total_vat - total_paid,
                'expense_breakdown': expense_breakdown
            }

        except Exception as e:
            return {'error': str(e)}

    def get_purchases_summary(self, branch_id: str, start_date: date = None, end_date: date = None) -> Dict:
        """Get comprehensive purchase summary"""
        try:
            query = self.db.query(Purchase).filter(Purchase.branch_id == branch_id)

            if start_date:
                query = query.filter(Purchase.purchase_date >= start_date)
            if end_date:
                query = query.filter(Purchase.purchase_date <= end_date)

            purchases = query.all()

            total_amount = sum(p.total_amount for p in purchases)
            total_vat = sum(p.total_vat_amount for p in purchases)
            total_paid = sum(p.amount_paid for p in purchases)

            status_counts = {}
            for purchase in purchases:
                status = purchase.status
                if status not in status_counts:
                    status_counts[status] = 0
                status_counts[status] += 1

            return {
                'total_purchases': len(purchases),
                'total_amount': total_amount,
                'total_vat': total_vat,
                'total_paid': total_paid,
                'outstanding': total_amount + total_vat - total_paid,
                'status_breakdown': status_counts
            }

        except Exception as e:
            return {'error': str(e)}

    def post_purchase_to_accounting(self, purchase_id: str, user_id: str = None) -> dict:
        """
        Post purchase to General Ledger with dimensional assignments.

        Creates journal entries for:
        1. Expense Debit (by dimension)
        2. Accounts Payable Credit (by dimension)

        Follows manufacturing pattern with 2-entry posting (Expense Debit + AP Credit)
        """
        # Fetch purchase
        purchase = self.db.query(Purchase).filter(
            Purchase.id == purchase_id
        ).first()

        if not purchase:
            raise ValueError(f"Purchase {purchase_id} not found")

        if purchase.posting_status == 'posted':
            raise ValueError(f"Purchase already posted")

        # Validate GL accounts are set
        if not purchase.expense_account_id or not purchase.payable_account_id:
            raise ValueError("Expense and AP GL accounts must be set")

        # Calculate purchase total
        total_amount = Decimal(str(purchase.total_amount or 0))

        # Create accounting entry header
        acct_entry = AccountingEntry(
            entry_type='PURCHASE_POSTING',
            entry_date=datetime.now(),
            total_debit=total_amount,
            total_credit=total_amount,
            reference=f"PURCHASE-{purchase.id}",
            created_by_user_id=user_id,
            branch_id=purchase.branch_id
        )
        self.db.add(acct_entry)
        self.db.flush()

        journal_entries = []

        # Create Expense debit entry
        expense_entry = JournalEntry(
            accounting_code_id=purchase.expense_account_id,
            debit_amount=total_amount,
            credit_amount=Decimal('0'),
            description=f"Purchase Expense - {purchase.reference or purchase.id}",
            reference=f"PURCHASE-{purchase.id}-EXP",
            entry_date=datetime.now().date(),
            source='PURCHASES',
            accounting_entry_id=acct_entry.id
        )
        self.db.add(expense_entry)
        self.db.flush()
        journal_entries.append(expense_entry)

        # Create AP credit entry
        ap_entry = JournalEntry(
            accounting_code_id=purchase.payable_account_id,
            debit_amount=Decimal('0'),
            credit_amount=total_amount,
            description=f"Purchase AP - {purchase.reference or purchase.id}",
            reference=f"PURCHASE-{purchase.id}-AP",
            entry_date=datetime.now().date(),
            source='PURCHASES',
            accounting_entry_id=acct_entry.id
        )
        self.db.add(ap_entry)
        self.db.flush()
        journal_entries.append(ap_entry)

        # Apply dimension assignments to all journal entries
        dimension_mapping = {
            'cost_center': purchase.cost_center_id,
            'project': purchase.project_id,
            'department': purchase.department_id
        }

        for je in journal_entries:
            for dim_type, dim_value_id in dimension_mapping.items():
                if dim_value_id:
                    dim_assign = AccountingDimensionAssignment(
                        journal_entry_id=je.id,
                        dimension_value_id=dim_value_id
                    )
                    self.db.add(dim_assign)

        # Update purchase posting status
        purchase.posting_status = 'posted'
        purchase.last_posted_date = datetime.now()
        purchase.posted_by = user_id

        self.db.commit()

        return {
            'success': True,
            'purchase_id': purchase.id,
            'entries_created': len(journal_entries),
            'journal_entry_ids': [je.id for je in journal_entries],
            'total_amount': float(total_amount),
            'posting_date': datetime.now().isoformat()
        }

    def reconcile_purchases_by_dimension(self, period: str) -> dict:
        """
        Reconcile purchases against GL balances by dimension.

        Format: period = "2025-10" (YYYY-MM)
        Returns variance analysis by dimension
        """
        # Parse period
        try:
            year, month = map(int, period.split('-'))
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)
        except:
            raise ValueError(f"Invalid period format: {period}. Use YYYY-MM")

        # Get all purchases in period
        purch_query = self.db.query(Purchase).filter(
            Purchase.purchase_date >= start_date,
            Purchase.purchase_date <= end_date
        )

        purch_total = Decimal('0')
        purch_by_dimension = {}

        for purchase in purch_query.all():
            purch_total += Decimal(str(purchase.total_amount or 0))

            # Group by cost center
            if purchase.cost_center_id:
                if purchase.cost_center_id not in purch_by_dimension:
                    purch_by_dimension[purchase.cost_center_id] = Decimal('0')
                purch_by_dimension[purchase.cost_center_id] += Decimal(str(purchase.total_amount or 0))

        # Get GL balances for purchase accounts (expense)
        gl_total = Decimal('0')
        gl_by_dimension = {}

        je_query = self.db.query(JournalEntry).filter(
            JournalEntry.entry_date >= start_date,
            JournalEntry.entry_date <= end_date,
            JournalEntry.source == 'PURCHASES'
        )

        for je in je_query.all():
            # Expense entries are debits
            balance = Decimal(str(je.debit_amount or 0))
            gl_total += balance

            # Group by dimension if available
            if je.dimension_assignments:
                for dim_assign in je.dimension_assignments:
                    dim_id = dim_assign.dimension_value_id
                    if dim_id not in gl_by_dimension:
                        gl_by_dimension[dim_id] = Decimal('0')
                    gl_by_dimension[dim_id] += balance

        # Calculate variances
        reconciliation = {
            'period': period,
            'purchase_total': float(purch_total),
            'gl_total': float(gl_total),
            'variance': float(gl_total - purch_total),
            'is_reconciled': abs(gl_total - purch_total) < Decimal('0.01'),
            'by_dimension': []
        }

        # Add dimension-level variances
        all_dimensions = set(purch_by_dimension.keys()) | set(gl_by_dimension.keys())
        for dim_id in all_dimensions:
            purch_amt = purch_by_dimension.get(dim_id, Decimal('0'))
            gl_amt = gl_by_dimension.get(dim_id, Decimal('0'))

            dim_value = self.db.query(DimensionValue).filter(
                DimensionValue.id == dim_id
            ).first()

            reconciliation['by_dimension'].append({
                'dimension_id': dim_id,
                'dimension_name': dim_value.value if dim_value else 'Unknown',
                'purchase_amount': float(purch_amt),
                'gl_amount': float(gl_amt),
                'variance': float(gl_amt - purch_amt)
            })

        return reconciliation
