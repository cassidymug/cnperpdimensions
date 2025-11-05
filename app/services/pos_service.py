from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
import uuid

from app.models.pos import PosSession
import logging

logger = logging.getLogger(__name__)
from app.models.sales import Sale, SaleItem, Customer
from app.models.inventory import Product
from app.models.accounting import AccountingEntry, JournalEntry, AccountingCode
from app.models.user import User
from app.models.branch import Branch
from app.models.app_setting import AppSetting
from app.core.config import settings


class POSService:
    """Comprehensive Point of Sale business logic service"""

    def __init__(self, db: Session):
        self.db = db

    def open_pos_session(self, user_id: str, branch_id: str, till_id: str = None, float_amount: Decimal = Decimal('0')) -> Tuple[PosSession, Dict]:
        """Open a new POS session"""
        try:
            # Check if user already has an open session
            existing_session = self.db.query(PosSession).filter(
                and_(
                    PosSession.user_id == user_id,
                    PosSession.status == 'open'
                )
            ).first()

            if existing_session:
                return existing_session, {'success': True, 'message': 'Existing session found', 'session_id': str(existing_session.id)}

            # Create new session
            session = PosSession(
                user_id=user_id,
                branch_id=branch_id,
                till_id=till_id or f"TILL_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                opened_at=datetime.now(),
                float_amount=float_amount,
                status='open'
            )

            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)

            return session, {'success': True, 'session_id': str(session.id)}

        except Exception as e:
            self.db.rollback()
            return None, {'success': False, 'error': str(e)}

    def close_pos_session(self, session_id: str, cash_submitted: Decimal, notes: str = None) -> Dict:
        """Close a POS session and generate session report"""
        try:
            session = self.db.query(PosSession).filter(PosSession.id == session_id).first()

            if not session:
                return {'success': False, 'error': 'Session not found'}

            if session.status != 'open':
                return {'success': False, 'error': 'Session is not open'}

            # Calculate session totals
            sales = self.db.query(Sale).filter(Sale.pos_session_id == session_id).all()

            total_sales = sum(sale.total_amount for sale in sales)
            total_transactions = len(sales)
            total_cash_sales = sum(sale.total_amount for sale in sales if sale.payment_method == 'cash')
            total_card_sales = sum(sale.total_amount for sale in sales if sale.payment_method == 'card')
            total_other_sales = sum(sale.total_amount for sale in sales if sale.payment_method not in ['cash', 'card'])
            total_refunds = sum(sale.total_amount for sale in sales if sale.status == 'refunded')

            # Update session
            session.closed_at = datetime.now()
            session.status = 'closed'
            session.cash_submitted = cash_submitted
            session.total_sales = total_sales
            session.total_transactions = total_transactions
            session.total_cash_sales = total_cash_sales
            session.total_card_sales = total_card_sales
            session.total_other_sales = total_other_sales
            session.total_refunds = total_refunds
            session.notes = notes

            # Generate session report
            session_report = self._generate_session_report(session, sales)

            self.db.commit()

            return {
                'success': True,
                'session_id': str(session.id),
                'summary': {
                    'total_sales': float(total_sales),
                    'total_transactions': total_transactions,
                    'total_cash_sales': float(total_cash_sales),
                    'total_card_sales': float(total_card_sales),
                    'total_other_sales': float(total_other_sales),
                    'total_refunds': float(total_refunds),
                    'cash_submitted': float(cash_submitted),
                    'float_amount': float(session.float_amount),
                    'cash_difference': float(cash_submitted - session.float_amount - total_cash_sales)
                },
                'session_report': session_report
            }

        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def create_sale(self, sale_data: Dict, session_id: str) -> Tuple[Sale, Dict]:
        """Create a complete sale transaction with journal entries and inventory updates"""
        try:
            # Validate session
            session = self.db.query(PosSession).filter(PosSession.id == session_id).first()
            if not session or session.status != 'open':
                return None, {'success': False, 'error': 'Invalid or closed POS session'}

            # Extract sale data
            items = sale_data.get('items', [])
            customer_id = sale_data.get('customer_id')
            payment_method = sale_data.get('payment_method', 'cash')
            amount_tendered = Decimal(str(sale_data.get('amount_tendered', '0')))
            currency = sale_data.get('currency', 'BWP')
            # Frontend currently sends a currency object; persist only the code
            if isinstance(currency, dict):
                currency = currency.get('currency') or currency.get('code') or 'BWP'
            vat_rate = Decimal(str(sale_data.get('vat_rate', '14.0')))

            # Calculate totals
            subtotal = Decimal('0')
            total_discount = Decimal('0')
            total_vat = Decimal('0')
            taxable_subtotal = Decimal('0')
            non_taxable_subtotal = Decimal('0')

            # Validate and process items
            sale_items = []
            for item_data in items:
                product_id = item_data.get('product_id')
                quantity = int(item_data.get('quantity', 1))
                unit_price = Decimal(str(item_data.get('unit_price', '0')))
                discount_amount = Decimal(str(item_data.get('discount_amount', '0')))
                is_taxable = item_data.get('is_taxable', True)

                # Get product
                product = self.db.query(Product).filter(Product.id == product_id).first()
                if not product:
                    return None, {'success': False, 'error': f'Product {product_id} not found'}

                # Check inventory
                if product.quantity < quantity:
                    return None, {'success': False, 'error': f'Insufficient stock for {product.name}'}

                # Calculate item totals
                item_total = unit_price * quantity
                item_total_after_discount = item_total - discount_amount

                if is_taxable:
                    item_vat = item_total_after_discount * (vat_rate / Decimal('100'))
                    taxable_subtotal += item_total_after_discount
                else:
                    item_vat = Decimal('0')
                    non_taxable_subtotal += item_total_after_discount

                subtotal += item_total
                total_discount += discount_amount
                total_vat += item_vat

                # Create sale item
                sale_item = SaleItem(
                    product_id=product_id,
                    quantity=quantity,
                    selling_price=unit_price,
                    cost_price=product.cost_price or Decimal('0'),
                    discount_amount=discount_amount,
                    discount_percentage=Decimal('0') if item_total == 0 else (discount_amount / item_total) * Decimal('100'),
                    vat_amount=item_vat,
                    vat_rate=vat_rate,
                    total_amount=item_total_after_discount + item_vat
                )
                sale_items.append(sale_item)

                # Update inventory
                product.quantity -= quantity

                # Record inventory transaction for traceability (POS sale)
                try:
                    from app.models.inventory import InventoryTransaction
                    inv_tx = InventoryTransaction(
                        product_id=product.id,
                        transaction_type='sale',
                        quantity=quantity,
                        unit_cost=product.cost_price or Decimal('0'),
                        total_cost=(product.cost_price or Decimal('0')) * quantity,
                        date=datetime.now().date(),
                        reference=f"POS {session.till_id} / {sale_data.get('reference') or 'N/A'}",
                        branch_id=session.branch_id,
                        previous_quantity=None,
                        new_quantity=product.quantity
                    )
                    self.db.add(inv_tx)
                except Exception as _inv_err:
                    logger.warning("POS inventory transaction logging failed: %s", _inv_err)

            # Calculate final totals
            total_amount = subtotal - total_discount + total_vat
            change_given = amount_tendered - total_amount

            if change_given < 0:
                return None, {'success': False, 'error': 'Insufficient payment'}

            # Get default Output VAT account (2132 - VAT Payable)
            output_vat_account = None
            if total_vat > 0:
                output_vat_account = self.db.query(AccountingCode).filter(
                    AccountingCode.code == '2132'
                ).first()

            # Create sale record
            sale = Sale(
                customer_id=customer_id,
                payment_method=payment_method,
                date=datetime.now(),
                currency=currency,
                total_amount=total_amount,
                amount_tendered=amount_tendered,
                change_given=change_given,
                total_vat_amount=total_vat,
                status='completed',
                total_amount_ex_vat=subtotal - total_discount,
                sale_time=datetime.now(),
                branch_id=session.branch_id,
                pos_session_id=session_id,
                salesperson_id=session.user_id,
                reference=f"POS{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:8]}",
                discount_amount=total_discount,
                discount_percentage=Decimal('0') if subtotal == 0 else (total_discount / subtotal) * Decimal('100'),
                output_vat_account_id=output_vat_account.id if output_vat_account else None
            )

            self.db.add(sale)
            self.db.flush()  # Get the sale ID

            # Add sale items and flush so relationship can be used reliably
            for item in sale_items:
                item.sale_id = sale.id
                self.db.add(item)
            self.db.flush()

            # Create journal entries unless caller indicates IFRS service will handle posting
            use_ifrs_posting = bool(sale_data.get('use_ifrs_posting'))
            journal_result = {'success': True, 'journal_entries': []}
            if not use_ifrs_posting:
                journal_result = self._create_sale_journal_entries(sale, session, sale_items)
                if not journal_result['success']:
                    return None, journal_result

            # Generate receipt automatically
            try:
                from app.services.receipt_service import ReceiptService
                receipt_service = ReceiptService(self.db)

                # Get default receipt format from app settings
                app_setting = self.db.query(AppSetting).first()
                default_format = app_setting.default_receipt_format if app_setting else '80mm'

                # Use configurable format for POS receipts, allow override from sale_data
                receipt_format = sale_data.get('receipt_format', default_format)
                receipt_result = receipt_service.generate_receipt(str(sale.id), str(session.user_id), receipt_format)
                if not receipt_result['success']:
                    logger.warning("Receipt generation failed: %s", receipt_result['error'])
                    receipt_result = None
                else:
                    # Mark as printed since we're auto-printing
                    receipt_service.mark_receipt_printed(receipt_result['receipt_id'])
            except Exception as receipt_error:
                logger.warning("Receipt generation error: %s", receipt_error)
                receipt_result = None

            self.db.commit()

            return sale, {
                'success': True,
                'sale_id': str(sale.id),
                'reference': sale.reference,
                'total_amount': float(total_amount),
                'journal_entries': journal_result['journal_entries'],
                'receipt_generated': receipt_result is not None,
                'receipt': receipt_result
            }

        except Exception as e:
            self.db.rollback()
            logger.exception("POS sale creation failed: %s", e)
            err_msg = str(e) or e.__class__.__name__ or 'Unknown sale error'
            return None, {'success': False, 'error': err_msg}

    def _create_sale_journal_entries(self, sale: Sale, session: PosSession, sale_items: List[SaleItem]) -> Dict:
        """Create balanced journal entries for a sale transaction.

        Uses provided sale_items list instead of relying on potentially not-yet-loaded relationship.
        """
        try:
            # Get accounting codes
            branch = self.db.query(Branch).filter(Branch.id == session.branch_id).first()

            # Get or create default accounts (align with seeded chart of accounts)
            cash_account = self._get_or_create_account(branch, '1111', 'Cash in Hand', 'Asset', 'Cash')
            bank_gl_account = self._get_or_create_account(branch, '1121', 'Main Bank Account', 'Asset', 'Bank')
            ar_account = self._get_or_create_account(branch, '1131', 'Trade Debtors', 'Asset', 'Trade Receivables')
            sales_account = self._get_or_create_account(branch, '4101', 'Sales Revenue - Products', 'Revenue', 'Sales Revenue')
            vat_payable_account = self._get_or_create_account(branch, '2131', 'VAT Payable', 'Liability', 'Tax Payables')
            cost_of_sales_account = self._get_or_create_account(branch, '5100', 'Cost of Goods Sold', 'Expense', 'Operating Expenses')
            inventory_account = self._get_or_create_account(branch, '1144', 'Merchandise Inventory', 'Asset', 'Inventory')

            # Calculate amounts
            net_sales = sale.total_amount - sale.total_vat_amount
            total_cost = sum((item.cost_price or Decimal('0')) * item.quantity for item in sale_items)

            # Create accounting entry header first
            accounting_entry = AccountingEntry(
                date_prepared=sale.date,
                date_posted=sale.date,
                particulars=f"POS Sale - {sale.reference}",
                book="POS",
                status="posted",
                branch_id=session.branch_id
            )
            self.db.add(accounting_entry)
            self.db.flush()

            # Create journal entry (System Auto-Poster with audit trail)
            journal_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=sales_account.id,  # Use sales account as primary
                reference=sale.reference,
                description=f"POS Sale - {sale.reference}",
                date=sale.date,
                branch_id=session.branch_id,
                entry_type='sale',
                # origin flags automated posting. created_by_user_id tracks cashier user.
                origin='POS_AUTO',
                created_by_user_id=session.user_id
            )

            self.db.add(journal_entry)
            self.db.flush()

            # Optional: lightweight audit linkage (could be expanded to a dedicated audit table)
            try:
                from app.core.security import log_user_action
                # We log using the session user as actor; module 'pos', action 'record_sale'
                # resource_type 'journal_entry' linking sale->journal
                # NOTE: get a pseudo user object if needed (fetch)
                acting_user = self.db.query(User).filter(User.id == session.user_id).first()
                if acting_user:
                    log_user_action(
                        db=self.db,
                        user=acting_user,
                        action='record_sale',
                        module='pos',
                        resource_type='journal_entry',
                        resource_id=journal_entry.id,
                        details={'sale_id': str(sale.id), 'reference': sale.reference, 'auto_poster': True, 'origin': 'POS_AUTO'}
                    )
            except Exception as audit_e:
                logger.warning("POS audit logging failed: %s", audit_e)

            # Create accounting entries (Journal Entries)
            entries = []

            # 1. Debit Cash/Bank (or Accounts Receivable for credit sales)
            if str(sale.payment_method).lower() == 'cash':
                cash_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=cash_account.id,
                    entry_type='debit',
                    debit_amount=sale.total_amount,
                    credit_amount=Decimal('0'),
                    description=f"Cash received for sale {sale.reference}",
                    date=sale.date,
                    branch_id=session.branch_id,
                    origin='POS_AUTO',
                    created_by_user_id=session.user_id
                )
                entries.append(cash_entry)
            elif str(sale.payment_method).lower() == 'card':
                # Card payments -> Bank
                bank_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=bank_gl_account.id,
                    entry_type='debit',
                    debit_amount=sale.total_amount,
                    credit_amount=Decimal('0'),
                    description=f"Bank payment for sale {sale.reference}",
                    date=sale.date,
                    branch_id=session.branch_id,
                    origin='POS_AUTO',
                    created_by_user_id=session.user_id
                )
                entries.append(bank_entry)
            else:
                # Credit sale -> Accounts Receivable
                ar_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=ar_account.id,
                    entry_type='debit',
                    debit_amount=sale.total_amount,
                    credit_amount=Decimal('0'),
                    description=f"Accounts receivable for sale {sale.reference}",
                    date=sale.date,
                    branch_id=session.branch_id,
                    origin='POS_AUTO',
                    created_by_user_id=session.user_id
                )
                entries.append(ar_entry)

            # 2. Credit Sales Revenue (net of VAT)
            sales_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=sales_account.id,
                entry_type='credit',
                debit_amount=Decimal('0'),
                credit_amount=net_sales,
                description=f"Sales revenue for {sale.reference}",
                date=sale.date,
                branch_id=session.branch_id,
                origin='POS_AUTO',
                created_by_user_id=session.user_id
            )
            entries.append(sales_entry)

            # 3. Credit VAT Payable
            if sale.total_vat_amount > 0:
                vat_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=vat_payable_account.id,
                    entry_type='credit',
                    debit_amount=Decimal('0'),
                    credit_amount=sale.total_vat_amount,
                    description=f"VAT collected for {sale.reference}",
                    date=sale.date,
                    branch_id=session.branch_id,
                    origin='POS_AUTO',
                    created_by_user_id=session.user_id
                )
                entries.append(vat_entry)

            # 4. Cost of Sales entries
            if total_cost > 0:
                # Debit Cost of Sales
                cost_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=cost_of_sales_account.id,
                    entry_type='debit',
                    debit_amount=total_cost,
                    credit_amount=Decimal('0'),
                    description=f"Cost of sales for {sale.reference}",
                    date=sale.date,
                    branch_id=session.branch_id,
                    origin='POS_AUTO',
                    created_by_user_id=session.user_id
                )
                entries.append(cost_entry)

                # Credit Inventory
                inventory_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=inventory_account.id,
                    entry_type='credit',
                    debit_amount=Decimal('0'),
                    credit_amount=total_cost,
                    description=f"Inventory reduction for {sale.reference}",
                    date=sale.date,
                    branch_id=session.branch_id,
                    origin='POS_AUTO',
                    created_by_user_id=session.user_id
                )
                entries.append(inventory_entry)

            # Add all entries
            for entry in entries:
                self.db.add(entry)

            # Update account balances
            self._update_account_balances(entries)

            # Balance validation: ensure debits == credits
            total_debits = sum(e.debit_amount for e in entries)
            total_credits = sum(e.credit_amount for e in entries)
            if total_debits != total_credits:
                raise ValueError(f"Unbalanced journal for sale {sale.reference}: debits {total_debits} != credits {total_credits}")

            return {
                'success': True,
                'journal_entries': [str(entry.id) for entry in entries]
            }

        except Exception as e:
            logger.exception("Journal entry creation failed for sale %s: %s", sale.id, e)
            return {'success': False, 'error': str(e)}

    def _get_or_create_account(self, branch: Branch, code: str, name: str, account_type: str, category: str) -> AccountingCode:
        """
        Get or create an accounting code.

        NOTE: AccountingCode.code is globally unique (not per-branch) in the current schema.
        The earlier implementation tried to create a duplicate of the same code for each branch,
        which triggers a UNIQUE constraint violation on subsequent sales in other branches and
        causes the POS sale to rollback with a 400 error.

        Until a migration adds a composite unique constraint (code, branch_id), we reuse the
        existing code across branches. This ensures POS sales succeed instead of failing when
        attempting to insert default accounts like 1000, 4000, 2131, 5000, 1200.
        """
        # First try by code ONLY (because of global uniqueness)
        account = self.db.query(AccountingCode).filter(AccountingCode.code == code).first()

        if not account:
            # Safe to create — will be globally unique.
            account = AccountingCode(
                code=code,
                name=name,
                account_type=account_type,
                category=category,
                branch_id=branch.id if branch else None,
                currency=(branch.currency if branch and getattr(branch, 'currency', None) else 'BWP')
            )
            self.db.add(account)
            self.db.flush()
        else:
            # If an existing global account lacks branch assignment and we have one, leave as-is to avoid conflicts.
            # (Optional future enhancement: introduce shared/universal account concept.)
            pass

        return account

    def _update_account_balances(self, entries: List[JournalEntry]):
        """Update account balances based on journal entries"""
        for entry in entries:
            account = self.db.query(AccountingCode).filter(AccountingCode.id == entry.accounting_code_id).first()
            if account:
                account.total_debits += entry.debit_amount
                account.total_credits += entry.credit_amount
                account.balance = account.total_debits - account.total_credits

    def _generate_session_report(self, session: PosSession, sales: List[Sale]) -> Dict:
        """Generate comprehensive session report"""
        try:
            # Sales summary
            sales_by_payment_method = {}
            sales_by_product = {}
            vat_summary = {
                'total_vat_collected': Decimal('0'),
                'vat_by_rate': {}
            }

            for sale in sales:
                # Payment method breakdown
                payment_method = sale.payment_method
                if payment_method not in sales_by_payment_method:
                    sales_by_payment_method[payment_method] = {
                        'count': 0,
                        'total': Decimal('0')
                    }
                sales_by_payment_method[payment_method]['count'] += 1
                sales_by_payment_method[payment_method]['total'] += sale.total_amount

                # Product breakdown
                for item in sale.sale_items:
                    product_name = item.product.name
                    if product_name not in sales_by_product:
                        sales_by_product[product_name] = {
                            'quantity': 0,
                            'revenue': Decimal('0'),
                            'cost': Decimal('0')
                        }
                    sales_by_product[product_name]['quantity'] += item.quantity
                    sales_by_product[product_name]['revenue'] += item.total_amount
                    sales_by_product[product_name]['cost'] += item.cost_price * item.quantity

                # VAT summary
                vat_summary['total_vat_collected'] += sale.total_vat_amount
                vat_rate = str(sale.sale_items[0].vat_rate if sale.sale_items else '14.0')
                if vat_rate not in vat_summary['vat_by_rate']:
                    vat_summary['vat_by_rate'][vat_rate] = Decimal('0')
                vat_summary['vat_by_rate'][vat_rate] += sale.total_vat_amount

            return {
                'session_id': str(session.id),
                'opened_at': session.opened_at,
                'closed_at': session.closed_at,
                'duration_hours': (session.closed_at - session.opened_at).total_seconds() / 3600,
                'total_transactions': len(sales),
                'total_sales': float(sum(sale.total_amount for sale in sales)),
                'total_vat': float(vat_summary['total_vat_collected']),
                'sales_by_payment_method': {
                    method: {
                        'count': data['count'],
                        'total': float(data['total'])
                    }
                    for method, data in sales_by_payment_method.items()
                },
                'top_products': sorted(
                    [
                        {
                            'name': name,
                            'quantity': data['quantity'],
                            'revenue': float(data['revenue']),
                            'cost': float(data['cost']),
                            'profit': float(data['revenue'] - data['cost'])
                        }
                        for name, data in sales_by_product.items()
                    ],
                    key=lambda x: x['revenue'],
                    reverse=True
                )[:10],
                'vat_summary': {
                    'total_vat_collected': float(vat_summary['total_vat_collected']),
                    'vat_by_rate': {
                        rate: float(amount)
                        for rate, amount in vat_summary['vat_by_rate'].items()
                    }
                }
            }

        except Exception as e:
            return {'error': str(e)}

    def get_open_sessions(self, branch_id: str = None) -> List[PosSession]:
        """Get open POS sessions"""
        query = self.db.query(PosSession).filter(PosSession.status == 'open')
        if branch_id:
            query = query.filter(PosSession.branch_id == branch_id)
        return query.all()

    def get_pos_session(self, session_id: str) -> Optional[PosSession]:
        """Get a specific POS session"""
        return self.db.query(PosSession).filter(PosSession.id == session_id).first()

    def get_products_for_pos(self, branch_id: Optional[str], search: str = None) -> List[Dict]:
        """Get products available for POS. Includes branch-specific and global (unassigned) items."""
        query = self.db.query(Product)

        if branch_id:
            query = query.filter(
                or_(
                    Product.branch_id == branch_id,
                    Product.branch_id.is_(None)
                )
            )

        if search:
            like = f"%{search}%"
            query = query.filter(
                or_(
                    Product.name.ilike(like),
                    Product.sku.ilike(like),
                    Product.barcode.ilike(like)
                )
            )

        products = query.all()

        return [
            {
                'id': str(product.id),
                'name': product.name,
                'sku': product.sku,
                'barcode': product.barcode,
                'selling_price': float(product.selling_price),
                'quantity': product.quantity,
                'image_url': product.image_url,
                'is_taxable': product.is_taxable
            }
            for product in products
        ]

    def get_customers_for_pos(self, branch_id: Optional[str], search: str = None) -> List[Dict]:
        """Get customers for POS. Branch filter is optional to allow shared customers."""
        query = self.db.query(Customer)

        if branch_id:
            query = query.filter(
                or_(
                    Customer.branch_id == branch_id,
                    Customer.branch_id.is_(None)
                )
            )

        if search:
            query = query.filter(
                or_(
                    Customer.name.ilike(f'%{search}%'),
                    Customer.email.ilike(f'%{search}%'),
                    Customer.phone.ilike(f'%{search}%')
                )
            )

        customers = query.all()

        return [
            {
                'id': str(customer.id),
                'name': customer.name,
                'email': customer.email,
                'phone': customer.phone,
                'customer_type': customer.customer_type
            }
            for customer in customers
        ]

    def get_sale_by_id(self, sale_id: str) -> Optional[Sale]:
        """Get a specific sale with all details"""
        return self.db.query(Sale).options(
            joinedload(Sale.customer),
            joinedload(Sale.sale_items).joinedload(SaleItem.product)
        ).filter(Sale.id == sale_id).first()

    def refund_sale(self, sale_id: str, refund_data: Dict) -> Dict:
        """Process a sale refund with proper accounting entries"""
        try:
            sale = self.db.query(Sale).filter(Sale.id == sale_id).first()
            if not sale:
                return {'success': False, 'error': 'Sale not found'}

            if sale.status == 'refunded':
                return {'success': False, 'error': 'Sale already refunded'}

            # Create refund journal entries
            refund_result = self._create_refund_journal_entries(sale, refund_data)
            if not refund_result['success']:
                return refund_result

            # Update sale status
            sale.status = 'refunded'

            # Restore inventory
            for item in sale.sale_items:
                product = self.db.query(Product).filter(Product.id == item.product_id).first()
                if product:
                    product.quantity += item.quantity

            # (Refund audit linkage omitted: journal entry creation for refund handled separately.)

            self.db.commit()

            return {
                'success': True,
                'refund_id': str(uuid.uuid4()),
                'sale_id': str(sale.id),
                'refund_amount': float(sale.total_amount)
            }

        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def _create_refund_journal_entries(self, sale: Sale, refund_data: Dict) -> Dict:
        """Create journal entries for a refund"""
        try:
            # Get accounting codes
            branch = self.db.query(Branch).filter(Branch.id == sale.branch_id).first()

            cash_account = self._get_or_create_account(branch, '1000', 'Cash', 'Asset', 'Current Asset')
            sales_account = self._get_or_create_account(branch, '4000', 'Sales Revenue', 'Revenue', 'Operating Revenue')
            vat_payable_account = self._get_or_create_account(branch, '2131', 'VAT Payable', 'Liability', 'Current Liability')
            cost_of_sales_account = self._get_or_create_account(branch, '5000', 'Cost of Sales', 'Expense', 'Operating Expense')
            inventory_account = self._get_or_create_account(branch, '1200', 'Inventory', 'Asset', 'Current Asset')

            # Create accounting entry header first
            accounting_entry = AccountingEntry(
                date_prepared=datetime.now(),
                date_posted=datetime.now(),
                particulars=f"Refund for sale {sale.reference}",
                book="POS",
                status="posted",
                branch_id=sale.branch_id
            )
            self.db.add(accounting_entry)
            self.db.flush()

            # Create journal entry
            journal_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=sales_account.id,  # Use sales account as primary
                reference=f"REFUND_{sale.reference}",
                description=f"Refund for sale {sale.reference}",
                date=datetime.now(),
                branch_id=sale.branch_id,
                entry_type='refund',
                origin='POS_AUTO_REFUND',
                created_by_user_id=refund_data.get('refunded_by')
            )

            self.db.add(journal_entry)
            self.db.flush()

            # Link audit (refund) - treat as POS_AUTO_REFUND for origin clarity
            try:
                from app.models.accounting import JournalSaleAudit
                self.db.add(JournalSaleAudit(
                    journal_entry_id=journal_entry.id,
                    sale_id=sale.id,
                    pos_session_id=None,
                    branch_id=sale.branch_id,
                    cashier_user_id=sale.salesperson_id,
                    posted_by_user_id=sale.salesperson_id,
                    origin='POS_AUTO_REFUND',
                    notes=f"Auto-posted POS refund for sale {sale.reference}"
                ))
            except Exception as link_e:
                logger.warning("Failed creating refund JournalSaleAudit record: %s", link_e)

            # Create accounting entries (reverse of sale entries)
            entries = []

            # 1. Credit Cash/Bank
            if sale.payment_method == 'cash':
                cash_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=cash_account.id,
                    entry_type='credit',
                    debit_amount=Decimal('0'),
                    credit_amount=sale.total_amount,
                    description=f"Cash refunded for {sale.reference}",
                    date=datetime.now(),
                    branch_id=sale.branch_id,
                    origin='POS_AUTO_REFUND',
                    created_by_user_id=refund_data.get('refunded_by')
                )
                entries.append(cash_entry)

            # 2. Debit Sales Revenue
            net_sales = sale.total_amount - sale.total_vat_amount
            sales_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=sales_account.id,
                entry_type='debit',
                debit_amount=net_sales,
                credit_amount=Decimal('0'),
                description=f"Sales revenue reversed for {sale.reference}",
                date=datetime.now(),
                branch_id=sale.branch_id,
                origin='POS_AUTO_REFUND',
                created_by_user_id=refund_data.get('refunded_by')
            )
            entries.append(sales_entry)

            # 3. Debit VAT Payable
            if sale.total_vat_amount > 0:
                vat_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=vat_payable_account.id,
                    entry_type='debit',
                    debit_amount=sale.total_vat_amount,
                    credit_amount=Decimal('0'),
                    description=f"VAT reversed for {sale.reference}",
                    date=datetime.now(),
                    branch_id=sale.branch_id,
                    origin='POS_AUTO_REFUND',
                    created_by_user_id=refund_data.get('refunded_by')
                )
                entries.append(vat_entry)

            # Add entries
            for entry in entries:
                self.db.add(entry)

            # Update account balances
            self._update_account_balances(entries)

            return {'success': True}

        except Exception as e:
            return {'success': False, 'error': str(e)}
