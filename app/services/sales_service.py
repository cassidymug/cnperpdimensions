from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.sales import Sale, SaleItem, Invoice
from app.models.inventory import Product, InventoryTransaction
from app.models.accounting import AccountingCode, AccountingEntry, JournalEntry
from app.models.sales import Customer
from app.models.accounting_dimensions import AccountingDimensionAssignment, AccountingDimensionValue
from app.core.config import settings


class SalesService:
    """Comprehensive sales business logic service"""

    PAYMENT_METHODS = ['cash', 'card', 'bank_transfer', 'mobile_money', 'on_account']
    SALE_STATUSES = ['pending', 'completed', 'cancelled', 'invoiced']

    def __init__(self, db: Session):
        self.db = db

    def create_sale(self, sale_data: Dict, items: List[Dict], branch_id: str) -> Tuple[Sale, Dict]:
        """
        Create a new sale with comprehensive business logic

        Args:
            sale_data: Sale header data
            items: List of sale items
            branch_id: Branch ID

        Returns:
            Tuple of (sale, result_dict)
        """
        try:
            # Validate sale data
            self._validate_sale_data(sale_data, items)

            # Get customer if provided
            customer = None
            if sale_data.get('customer_id'):
                customer = self.db.query(Customer).filter(
                    Customer.id == sale_data['customer_id'],
                    Customer.branch_id == branch_id
                ).first()

            # Create sale record
            sale = Sale(
                customer_id=customer.id if customer else None,
                payment_method=sale_data['payment_method'],
                amount_tendered=Decimal(sale_data.get('amount_tendered', 0)),
                date=datetime.now(),
                sale_time=datetime.now(),
                currency=settings.default_currency,
                branch_id=branch_id,
                status='completed'
            )

            # Calculate totals and create sale items
            total_amount = Decimal('0')
            total_vat_amount = Decimal('0')

            for item_data in items:
                product = self.db.query(Product).filter(
                    Product.id == item_data['product_id'],
                    Product.branch_id == branch_id
                ).first()

                if not product:
                    raise ValueError(f"Product {item_data['product_id']} not found")

                quantity = int(item_data['quantity'])
                selling_price = Decimal(item_data['selling_price'])
                vat_rate = Decimal(item_data.get('vat_rate', settings.default_vat_rate))

                # Calculate line totals
                line_total = quantity * selling_price
                vat_amount = line_total * (vat_rate / 100)

                # Create sale item
                sale_item = SaleItem(
                    product_id=product.id,
                    quantity=quantity,
                    selling_price=selling_price,
                    vat_amount=vat_amount,
                    vat_rate=vat_rate
                )

                sale.sale_items.append(sale_item)
                total_amount += line_total
                total_vat_amount += vat_amount

                # Update inventory
                self._update_inventory(product, quantity, 'sale')

            # Get default Output VAT account (2132 - VAT Payable)
            output_vat_account = None
            if total_vat_amount > 0:
                output_vat_account = self.db.query(AccountingCode).filter(
                    AccountingCode.code == '2132'
                ).first()

            # Set final totals
            sale.total_amount = total_amount
            sale.total_vat_amount = total_vat_amount
            sale.total_amount_ex_vat = total_amount
            sale.change_given = sale.amount_tendered - (total_amount + total_vat_amount)
            sale.output_vat_account_id = output_vat_account.id if output_vat_account else None

            # Save sale
            self.db.add(sale)
            self.db.commit()
            self.db.refresh(sale)

            # Process accounting entries
            self._create_accounting_entries(sale)

            # Record VAT collected
            self._record_vat_collected(sale)

            return sale, {'success': True, 'sale_id': str(sale.id)}

        except Exception as e:
            self.db.rollback()
            return None, {'success': False, 'error': str(e)}

    def _validate_sale_data(self, sale_data: Dict, items: List[Dict]) -> None:
        """Validate sale data before processing"""
        if not items:
            raise ValueError("Sale must have at least one item")

        if sale_data['payment_method'] not in self.PAYMENT_METHODS:
            raise ValueError(f"Invalid payment method: {sale_data['payment_method']}")

        # Validate on-account sales
        if sale_data['payment_method'] == 'on_account' and not sale_data.get('customer_id'):
            raise ValueError("On-account sales require a customer")

        # Validate amount tendered for cash sales
        if sale_data['payment_method'] != 'on_account':
            amount_tendered = Decimal(sale_data.get('amount_tendered', 0))
            if amount_tendered <= 0:
                raise ValueError("Amount tendered must be greater than 0 for cash sales")

    def _update_inventory(self, product: Product, quantity: int, transaction_type: str) -> None:
        """Update product inventory"""
        if product.quantity < quantity:
            raise ValueError(f"Insufficient stock for product {product.name}")

        product.quantity -= quantity

        # Create inventory transaction
        inventory_transaction = InventoryTransaction(
            product_id=product.id,
            transaction_type=transaction_type,
            quantity=quantity,
            unit_cost=product.cost_price,
            date=date.today(),
            reference=f"Sale transaction"
        )

        self.db.add(inventory_transaction)

    def _create_accounting_entries(self, sale: Sale) -> None:
        """Create accounting entries for the sale"""
        # Get required accounting codes
        sales_account = self._get_accounting_code('Sales Revenue', 'Revenue')
        cash_account = self._get_accounting_code('Cash', 'Asset')
        vat_account = self._get_accounting_code('VAT Collected', 'Liability')
        cogs_account = self._get_accounting_code('Cost of Goods Sold', 'Expense')
        inventory_account = self._get_accounting_code('Inventory', 'Asset')

        # Create accounting entry
        accounting_entry = AccountingEntry(
            date_prepared=date.today(),
            date_posted=date.today(),
            particulars=f"Sale transaction #{sale.id}",
            book=f"SALE-{sale.id}",
            status='posted',
            branch_id=sale.branch_id
        )

        self.db.add(accounting_entry)
        self.db.flush()

        # Create journal entries
        entries_to_create = []

        # Sales revenue entry
        entries_to_create.append({
            'accounting_code_id': sales_account.id,
            'entry_type': 'credit',
            'amount': sale.total_amount_ex_vat,
            'description': f"Sales revenue for sale #{sale.id}"
        })

        # VAT collected entry
        if sale.total_vat_amount > 0:
            entries_to_create.append({
                'accounting_code_id': vat_account.id,
                'entry_type': 'credit',
                'amount': sale.total_vat_amount,
                'description': f"VAT collected for sale #{sale.id}"
            })

        # Cash received entry
        if sale.payment_method != 'on_account':
            entries_to_create.append({
                'accounting_code_id': cash_account.id,
                'entry_type': 'debit',
                'amount': sale.total_amount + sale.total_vat_amount,
                'description': f"Cash received for sale #{sale.id}"
            })

        # COGS and inventory entries
        cogs_total = self._calculate_cogs_total(sale)
        if cogs_total > 0:
            entries_to_create.append({
                'accounting_code_id': cogs_account.id,
                'entry_type': 'debit',
                'amount': cogs_total,
                'description': f"Cost of goods sold for sale #{sale.id}"
            })

            entries_to_create.append({
                'accounting_code_id': inventory_account.id,
                'entry_type': 'credit',
                'amount': cogs_total,
                'description': f"Inventory reduction for sale #{sale.id}"
            })

        # Create journal entries
        for entry_data in entries_to_create:
            journal_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=entry_data['accounting_code_id'],
                entry_type=entry_data['entry_type'],
                amount=entry_data['amount'],
                description=entry_data['description'],
                date=date.today(),
                date_posted=date.today(),
                branch_id=sale.branch_id
            )
            self.db.add(journal_entry)

    def _get_accounting_code(self, name: str, account_type: str) -> AccountingCode:
        """Get accounting code by name and type"""
        code = self.db.query(AccountingCode).filter(
            and_(
                AccountingCode.name == name,
                AccountingCode.account_type == account_type
            )
        ).first()

        if not code:
            raise ValueError(f"Accounting code '{name}' ({account_type}) not found")

        return code

    def _calculate_cogs_total(self, sale: Sale) -> Decimal:
        """Calculate total cost of goods sold for the sale"""
        cogs_total = Decimal('0')

        for sale_item in sale.sale_items:
            product = sale_item.product
            if product.cost_price:
                cogs_total += Decimal(sale_item.quantity) * Decimal(product.cost_price)

        return cogs_total

    def _record_vat_collected(self, sale: Sale) -> None:
        """Record VAT collected for reconciliation"""
        if sale.total_vat_amount <= 0:
            return

        # This would integrate with VAT reconciliation service
        # For now, we just log the VAT collection
        print(f"VAT collected: {sale.total_vat_amount} for sale {sale.id}")

    def get_sales_summary(self, branch_id: str, start_date: date = None, end_date: date = None) -> Dict:
        """Get sales summary statistics"""
        query = self.db.query(Sale).filter(Sale.branch_id == branch_id)

        if start_date:
            query = query.filter(Sale.date >= start_date)
        if end_date:
            query = query.filter(Sale.date <= end_date)

        sales = query.all()

        total_sales = len(sales)
        total_revenue = sum(sale.total_amount for sale in sales)
        total_vat = sum(sale.total_vat_amount for sale in sales)
        total_amount = sum(sale.total_amount + sale.total_vat_amount for sale in sales)

        return {
            'total_sales': total_sales,
            'total_revenue': float(total_revenue),
            'total_vat': float(total_vat),
            'total_amount': float(total_amount),
            'average_sale': float(total_amount / total_sales) if total_sales > 0 else 0
        }

    def get_sales_by_customer(self, customer_id: str, branch_id: str) -> List[Sale]:
        """Get all sales for a specific customer"""
        return self.db.query(Sale).filter(
            and_(
                Sale.customer_id == customer_id,
                Sale.branch_id == branch_id
            )
        ).order_by(Sale.date.desc()).all()

    def get_sales_by_date_range(self, branch_id: str, start_date: date, end_date: date) -> List[Sale]:
        """Get sales within a date range"""
        return self.db.query(Sale).filter(
            and_(
                Sale.branch_id == branch_id,
                Sale.date >= start_date,
                Sale.date <= end_date
            )
        ).order_by(Sale.date.desc()).all()

    def cancel_sale(self, sale_id: str, branch_id: str) -> Tuple[bool, str]:
        """Cancel a sale and reverse all transactions"""
        try:
            sale = self.db.query(Sale).filter(
                and_(
                    Sale.id == sale_id,
                    Sale.branch_id == branch_id
                )
            ).first()

            if not sale:
                return False, "Sale not found"

            if sale.status == 'cancelled':
                return False, "Sale is already cancelled"

            # Reverse inventory transactions
            for sale_item in sale.sale_items:
                product = sale_item.product
                product.quantity += sale_item.quantity

                # Create reversal inventory transaction
                inventory_transaction = InventoryTransaction(
                    product_id=product.id,
                    transaction_type='sale_cancellation',
                    quantity=sale_item.quantity,
                    unit_cost=product.cost_price,
                    date=date.today(),
                    reference=f"Sale cancellation - {sale.id}"
                )
                self.db.add(inventory_transaction)

            # Reverse accounting entries
            self._reverse_accounting_entries(sale)

            # Update sale status
            sale.status = 'cancelled'

            self.db.commit()
            return True, "Sale cancelled successfully"

        except Exception as e:
            self.db.rollback()
            return False, f"Error cancelling sale: {str(e)}"

    def _reverse_accounting_entries(self, sale: Sale) -> None:
        """Reverse accounting entries for cancelled sale"""
        # Find the accounting entry for this sale
        accounting_entry = self.db.query(AccountingEntry).filter(
            AccountingEntry.book == f"SALE-{sale.id}"
        ).first()

        if accounting_entry:
            # Create reversal entries with opposite amounts
            for journal_entry in accounting_entry.journal_entries:
                reversal_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=journal_entry.accounting_code_id,
                    entry_type='credit' if journal_entry.entry_type == 'debit' else 'debit',
                    amount=journal_entry.amount,
                    description=f"Reversal: {journal_entry.description}",
                    date=date.today(),
                    date_posted=date.today()
                )
                self.db.add(reversal_entry)

    def post_sale_to_accounting(self, invoice_id: str, user_id: str = None) -> dict:
        """
        Post sale/invoice to General Ledger with dimensional assignments.

        Creates journal entries for:
        1. Accounts Receivable Debit (by dimension)
        2. Revenue Credit (by dimension)

        Follows manufacturing pattern with 2-entry posting (AR Debit + Revenue Credit)
        """
        from app.models.production_order import User

        # Fetch invoice
        invoice = self.db.query(Invoice).filter(
            Invoice.id == invoice_id
        ).first()

        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        if invoice.posting_status == 'posted':
            raise ValueError(f"Invoice already posted")

        # Validate GL accounts are set
        if not invoice.revenue_account_id or not invoice.ar_account_id:
            raise ValueError("Revenue and AR GL accounts must be set")

        # Calculate invoice total
        total_amount = Decimal(str(invoice.total_amount or 0))

        # Create accounting entry header
        acct_entry = AccountingEntry(
            entry_type='SALES_POSTING',
            entry_date=datetime.now(),
            total_debit=total_amount,
            total_credit=total_amount,
            reference=f"SALES-{invoice.id}",
            created_by_user_id=user_id,
            branch_id=invoice.branch_id
        )
        self.db.add(acct_entry)
        self.db.flush()

        journal_entries = []

        # Create AR debit entry
        ar_entry = JournalEntry(
            accounting_code_id=invoice.ar_account_id,
            debit_amount=total_amount,
            credit_amount=Decimal('0'),
            description=f"Sales AR - Invoice {invoice.invoice_number}",
            reference=f"SALES-{invoice.id}-AR",
            entry_date=datetime.now().date(),
            source='SALES',
            accounting_entry_id=acct_entry.id,
            branch_id=invoice.branch_id
        )
        self.db.add(ar_entry)
        self.db.flush()
        journal_entries.append(ar_entry)

        # Create revenue credit entry
        revenue_entry = JournalEntry(
            accounting_code_id=invoice.revenue_account_id,
            debit_amount=Decimal('0'),
            credit_amount=total_amount,
            description=f"Sales Revenue - Invoice {invoice.invoice_number}",
            reference=f"SALES-{invoice.id}-REV",
            entry_date=datetime.now().date(),
            source='SALES',
            accounting_entry_id=acct_entry.id,
            branch_id=invoice.branch_id
        )
        self.db.add(revenue_entry)
        self.db.flush()
        journal_entries.append(revenue_entry)

        # Apply dimension assignments to all journal entries
        dimension_mapping = {
            'cost_center': invoice.cost_center_id,
            'project': invoice.project_id,
            'department': invoice.department_id
        }

        for je in journal_entries:
            for dim_type, dim_value_id in dimension_mapping.items():
                if dim_value_id:
                    dim_assign = AccountingDimensionAssignment(
                        journal_entry_id=je.id,
                        dimension_value_id=dim_value_id
                    )
                    self.db.add(dim_assign)

        # Update invoice posting status
        invoice.posting_status = 'posted'
        invoice.last_posted_date = datetime.now()
        invoice.posted_by = user_id

        self.db.commit()

        return {
            'success': True,
            'invoice_id': invoice.id,
            'entries_created': len(journal_entries),
            'journal_entry_ids': [je.id for je in journal_entries],
            'total_amount': float(total_amount),
            'posting_date': datetime.now().isoformat()
        }

    def reconcile_sales_by_dimension(self, period: str) -> dict:
        """
        Reconcile sales against GL balances by dimension.

        Format: period = "2025-10" (YYYY-MM)
        Returns variance analysis by dimension
        """
        from datetime import timedelta

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

        # Get all invoices in period
        inv_query = self.db.query(Invoice).filter(
            Invoice.date >= start_date,
            Invoice.date <= end_date
        )

        inv_total = Decimal('0')
        inv_by_dimension = {}

        for invoice in inv_query.all():
            inv_total += Decimal(str(invoice.total_amount or 0))

            # Group by cost center
            if invoice.cost_center_id:
                if invoice.cost_center_id not in inv_by_dimension:
                    inv_by_dimension[invoice.cost_center_id] = Decimal('0')
                inv_by_dimension[invoice.cost_center_id] += Decimal(str(invoice.total_amount or 0))

        # Get GL balances for sales accounts (revenue)
        gl_total = Decimal('0')
        gl_by_dimension = {}

        je_query = self.db.query(JournalEntry).filter(
            JournalEntry.entry_date >= start_date,
            JournalEntry.entry_date <= end_date,
            JournalEntry.source == 'SALES'
        )

        for je in je_query.all():
            # Revenue entries are credits
            balance = Decimal(str(je.credit_amount or 0))
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
            'invoice_total': float(inv_total),
            'gl_total': float(gl_total),
            'variance': float(gl_total - inv_total),
            'is_reconciled': abs(gl_total - inv_total) < Decimal('0.01'),
            'by_dimension': []
        }

        # Add dimension-level variances
        all_dimensions = set(inv_by_dimension.keys()) | set(gl_by_dimension.keys())
        for dim_id in all_dimensions:
            inv_amt = inv_by_dimension.get(dim_id, Decimal('0'))
            gl_amt = gl_by_dimension.get(dim_id, Decimal('0'))

            dim_value = self.db.query(AccountingDimensionValue).filter(
                AccountingDimensionValue.id == dim_id
            ).first()

            reconciliation['by_dimension'].append({
                'dimension_id': dim_id,
                'dimension_name': dim_value.name if dim_value else 'Unknown',
                'invoice_amount': float(inv_amt),
                'gl_amount': float(gl_amt),
                'variance': float(gl_amt - inv_amt)
            })

        return reconciliation
