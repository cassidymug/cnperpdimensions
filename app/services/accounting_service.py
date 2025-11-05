from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.accounting import AccountingCode, AccountingEntry, JournalEntry, Ledger, OpeningBalance
from app.models.inventory import Product
from app.core.config import settings


class AccountingService:
    """Comprehensive accounting business logic service"""

    # NOTE: Some parts of the codebase store AccountingCode.account_type as an Enum (AccountType.ASSET)
    # while this service historically assumed raw string values ('Asset'). Direct dictionary indexing
    # with an Enum key causes KeyError, which was propagating as a 500 when banking endpoints attempted
    # to compute balances. We normalize via helper _get_normal_balance now.
    ACCOUNT_TYPES = {
        'Asset': {'normal_balance': 'debit', 'description': 'Resources owned by the business'},
        'Liability': {'normal_balance': 'credit', 'description': 'Obligations owed to external parties'},
        'Equity': {'normal_balance': 'credit', 'description': "Owners' claims on the assets"},
        'Revenue': {'normal_balance': 'credit', 'description': 'Income from sales/services'},
        'Expense': {'normal_balance': 'debit', 'description': 'Costs incurred to generate revenue'}
    }

    CATEGORIES = {
        'Asset': [
            'Current Assets', 'Fixed Assets', 'Intangible Assets',
            'Investments', 'Prepaid Expenses', 'Inventory'
        ],
        'Liability': [
            'Current Liabilities', 'Long-term Liabilities',
            'Accounts Payable', 'Accrued Expenses'
        ],
        'Equity': [
            'Owner\'s Equity', 'Retained Earnings', 'Common Stock', 'Preferred Stock'
        ],
        'Revenue': [
            'Operating Revenue', 'Non-operating Revenue', 'Sales Revenue', 'Service Revenue'
        ],
        'Expense': [
            'Operating Expenses', 'Cost of Goods Sold', 'Administrative Expenses',
            'Selling Expenses', 'Financial Expenses'
        ]
    }

    def __init__(self, db: Session):
        self.db = db

    def create_accounting_code(self, code_data: Dict, branch_id: str) -> Tuple[AccountingCode, Dict]:
        """Create a new accounting code with validation"""
        try:
            # Validate code uniqueness
            existing_code = self.db.query(AccountingCode).filter(
                and_(
                    AccountingCode.code == code_data['code'],
                    AccountingCode.branch_id == branch_id
                )
            ).first()

            if existing_code:
                return None, {'success': False, 'error': 'Accounting code already exists'}

            # Create accounting code
            accounting_code = AccountingCode(
                code=code_data['code'],
                name=code_data['name'],
                account_type=code_data['account_type'],
                category=code_data.get('category'),
                parent_id=code_data.get('parent_id'),
                is_parent=code_data.get('is_parent', False),
                currency=code_data.get('currency', settings.default_currency),
                branch_id=branch_id
            )

            self.db.add(accounting_code)
            self.db.commit()
            self.db.refresh(accounting_code)

            return accounting_code, {'success': True, 'accounting_code_id': str(accounting_code.id)}

        except Exception as e:
            self.db.rollback()
            return None, {'success': False, 'error': str(e)}

    def get_total_debits(self, accounting_code_id: str) -> Decimal:
        """Calculate total debits for an accounting code"""
        total = self.db.query(func.sum(JournalEntry.debit_amount)).filter(
            JournalEntry.accounting_code_id == accounting_code_id
        ).scalar()
        return total or Decimal('0')

    def get_total_credits(self, accounting_code_id: str) -> Decimal:
        """Calculate total credits for an accounting code"""
        total = self.db.query(func.sum(JournalEntry.credit_amount)).filter(
            JournalEntry.accounting_code_id == accounting_code_id
        ).scalar()
        return total or Decimal('0')

    def update_accounting_code_balance(self, accounting_code_id: str) -> bool:
        """Update the balance field in accounting code based on journal entries"""
        try:
            accounting_code = self.db.query(AccountingCode).filter(
                AccountingCode.id == accounting_code_id
            ).first()

            if not accounting_code:
                return False

            # Calculate new balance
            total_debits = self.get_total_debits(accounting_code_id)
            total_credits = self.get_total_credits(accounting_code_id)

            # Get opening balance
            opening_balance = self.db.query(OpeningBalance).filter(
                and_(
                    OpeningBalance.accounting_code_id == accounting_code_id,
                    OpeningBalance.year == date.today().year
                )
            ).first()

            opening_amount = opening_balance.amount if opening_balance else Decimal('0')

            # Calculate balance based on normal balance type
            normal_balance = self._get_normal_balance(accounting_code.account_type) or 'debit'

            if normal_balance == 'debit':
                balance = opening_amount + total_debits - total_credits
            else:
                balance = opening_amount + total_credits - total_debits

            # Update the accounting code
            accounting_code.balance = balance
            accounting_code.total_debits = total_debits
            accounting_code.total_credits = total_credits

            self.db.commit()

            # Update parent account balance if this is a child account
            if accounting_code.parent_id:
                self.update_parent_balance(accounting_code.parent_id)

            return True

        except Exception as e:
            self.db.rollback()
            print(f"Error updating accounting code balance: {e}")
            return False

    def update_parent_balance(self, parent_id: str) -> bool:
        """Update parent account balance by summing all child balances"""
        try:
            parent = self.db.query(AccountingCode).filter(
                AccountingCode.id == parent_id
            ).first()

            if not parent:
                return False

            # Get all child accounts
            children = self.db.query(AccountingCode).filter(
                AccountingCode.parent_id == parent_id
            ).all()

            # Sum up all child balances
            total_debits = Decimal('0')
            total_credits = Decimal('0')
            total_balance = Decimal('0')

            for child in children:
                total_debits += child.total_debits or Decimal('0')
                total_credits += child.total_credits or Decimal('0')
                total_balance += child.balance or Decimal('0')

            # Update parent account
            parent.total_debits = total_debits
            parent.total_credits = total_credits
            parent.balance = total_balance

            self.db.commit()

            # Recursively update grandparent if exists
            if parent.parent_id:
                self.update_parent_balance(parent.parent_id)

            return True

        except Exception as e:
            self.db.rollback()
            print(f"Error updating parent balance: {e}")
            return False

    def get_account_balance(self, accounting_code_id: str, as_of_date: date = None) -> Decimal:
        """Calculate account balance as of a specific date"""
        accounting_code = self.db.query(AccountingCode).filter(
            AccountingCode.id == accounting_code_id
        ).first()

        if not accounting_code:
            return Decimal('0')

        # Get opening balance
        opening_balance = self.db.query(OpeningBalance).filter(
            and_(
                OpeningBalance.accounting_code_id == accounting_code_id,
                OpeningBalance.year == (as_of_date or date.today()).year
            )
        ).first()

        opening_amount = opening_balance.amount if opening_balance else Decimal('0')

        # Get movement from journal entries
        query = self.db.query(JournalEntry).join(AccountingEntry).filter(
            JournalEntry.accounting_code_id == accounting_code_id
        )

        if as_of_date:
            query = query.filter(AccountingEntry.date_posted <= as_of_date)

        journal_entries = query.all()

        # Calculate balance based on normal balance type
        normal_balance = self._get_normal_balance(accounting_code.account_type) or 'debit'

        debit_total = sum(entry.debit_amount for entry in journal_entries)
        credit_total = sum(entry.credit_amount for entry in journal_entries)

        if normal_balance == 'debit':
            balance = opening_amount + debit_total - credit_total
        else:
            balance = opening_amount + credit_total - debit_total

        return balance

    def get_total_asset_value(self, accounting_code_id: str) -> Decimal:
        """Calculate total asset value including inventory"""
        accounting_code = self.db.query(AccountingCode).filter(
            AccountingCode.id == accounting_code_id
        ).first()

        if not accounting_code:
            return Decimal('0')

        # Get all descendant IDs
        descendant_ids = self._get_descendant_ids(accounting_code_id)

        # Calculate inventory value for inventory accounts
        if accounting_code.category == 'Inventory':
            inventory_value = self.db.query(func.sum(Product.quantity * Product.cost_price)).filter(
                Product.accounting_code_id.in_(descendant_ids)
            ).scalar() or Decimal('0')
            return inventory_value

        # Calculate balance for other asset accounts
        balance = self.get_account_balance(accounting_code_id)
        return balance

    def _get_descendant_ids(self, accounting_code_id: str) -> List[str]:
        """Get all descendant accounting code IDs"""
        descendants = []
        accounting_code = self.db.query(AccountingCode).filter(
            AccountingCode.id == accounting_code_id
        ).first()

        if accounting_code:
            descendants.append(accounting_code.id)
            for sub_account in accounting_code.children:
                descendants.extend(self._get_descendant_ids(sub_account.id))

        return descendants

    def create_journal_entry(self, entry_data: Dict, branch_id: str) -> Tuple[AccountingEntry, Dict]:
        """Create a journal entry with proper validation"""
        try:
            # Validate that debits equal credits
            total_debits = sum(item['amount'] for item in entry_data['entries'] if item['entry_type'] == 'debit')
            total_credits = sum(item['amount'] for item in entry_data['entries'] if item['entry_type'] == 'credit')

            if total_debits != total_credits:
                return None, {'success': False, 'error': 'Debits must equal credits'}

            # Create accounting entry
            accounting_entry = AccountingEntry(
                date_prepared=entry_data.get('date_prepared', date.today()),
                date_posted=entry_data.get('date_posted', date.today()),
                particulars=entry_data['particulars'],
                book=entry_data.get('book', 'Manual Entry'),
                status='posted',
                branch_id=branch_id
            )

            self.db.add(accounting_entry)
            self.db.flush()

            # Create journal entries
            for entry_item in entry_data['entries']:
                # Determine debit vs credit amounts
                debit_amount = entry_item['amount'] if entry_item['entry_type'] == 'debit' else 0.0
                credit_amount = entry_item['amount'] if entry_item['entry_type'] == 'credit' else 0.0

                journal_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=entry_item['accounting_code_id'],
                    entry_type=entry_item['entry_type'],
                    debit_amount=debit_amount,
                    credit_amount=credit_amount,
                    description=entry_item.get('description', ''),
                    date=entry_data.get('date_prepared', date.today()),
                    date_posted=entry_data.get('date_posted', date.today()),
                    branch_id=branch_id
                )
                self.db.add(journal_entry)

            self.db.commit()
            self.db.refresh(accounting_entry)

            # Update account balances for all affected accounts
            affected_accounts = set(entry['accounting_code_id'] for entry in entry_data['entries'])
            for account_id in affected_accounts:
                try:
                    self.update_account_balance(account_id)
                except Exception as balance_error:
                    print(f"[BALANCE_WARN] Failed to update balance for account {account_id}: {balance_error}")

            return accounting_entry, {'success': True, 'entry_id': str(accounting_entry.id)}

        except Exception as e:
            self.db.rollback()
            return None, {'success': False, 'error': str(e)}

    def get_running_transactions(self, accounting_code_id: str, year: int) -> List[Dict]:
        """Get running transactions for an account for a specific year"""
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        # Get opening balance
        opening_balance = self.get_account_balance(accounting_code_id, start_date - date.resolution)

        # Get journal entries for the year
        journal_entries = self.db.query(JournalEntry).join(AccountingEntry).filter(
            and_(
                JournalEntry.accounting_code_id == accounting_code_id,
                AccountingEntry.date_posted >= start_date,
                AccountingEntry.date_posted <= end_date,
                AccountingEntry.status == 'posted'
            )
        ).order_by(AccountingEntry.date_posted, JournalEntry.created_at).all()

        running_balance = opening_balance
        result = []

        for entry in journal_entries:
            # Calculate change based on normal balance
            accounting_code = entry.accounting_code
            normal_balance = self._get_normal_balance(accounting_code.account_type) or 'debit'

            if normal_balance == 'debit':
                change = entry.debit_amount - entry.credit_amount
            else:
                change = entry.credit_amount - entry.debit_amount

            running_balance += change

            result.append({
                'id': str(entry.id),
                'date': entry.accounting_entry.date_posted,
                'description': entry.description or entry.accounting_entry.particulars,
                'entry_type': 'debit' if entry.debit_amount > 0 else 'credit',
                'debit': float(entry.debit_amount),
                'credit': float(entry.credit_amount),
                'amount': float(entry.amount),
                'running_balance': float(running_balance)
            })

        return result

    def get_trial_balance(self, branch_id: str, as_of_date: date = None) -> List[Dict]:
        """Generate trial balance report"""
        accounting_codes = self.db.query(AccountingCode).filter(
            AccountingCode.branch_id == branch_id
        ).all()

        trial_balance = []

        for code in accounting_codes:
            balance = self.get_account_balance(code.id, as_of_date)

            if balance != 0:  # Only include accounts with non-zero balances
                trial_balance.append({
                    'code': code.code,
                    'name': code.name,
                    'account_type': code.account_type,
                    'category': code.category,
                    'debit': float(balance) if balance > 0 else 0,
                    'credit': float(abs(balance)) if balance < 0 else 0,
                    'balance': float(balance)
                })

        return trial_balance

    def get_balance_sheet(self, branch_id: str, as_of_date: date = None) -> Dict:
        """Generate balance sheet report"""
        if not as_of_date:
            as_of_date = date.today()

        # Get all accounting codes
        accounting_codes = self.db.query(AccountingCode).filter(
            AccountingCode.branch_id == branch_id
        ).all()

        # Group by account type
        assets = []
        liabilities = []
        equity = []

        for code in accounting_codes:
            balance = self.get_account_balance(code.id, as_of_date)

            if code.account_type == 'Asset':
                assets.append({
                    'code': code.code,
                    'name': code.name,
                    'category': code.category,
                    'balance': float(balance)
                })
            elif code.account_type == 'Liability':
                liabilities.append({
                    'code': code.code,
                    'name': code.name,
                    'category': code.category,
                    'balance': float(balance)
                })
            elif code.account_type == 'Equity':
                equity.append({
                    'code': code.code,
                    'name': code.name,
                    'category': code.category,
                    'balance': float(balance)
                })

        # Calculate totals
        total_assets = sum(asset['balance'] for asset in assets)
        total_liabilities = sum(liability['balance'] for liability in liabilities)
        total_equity = sum(equity_item['balance'] for equity_item in equity)

        return {
            'as_of_date': as_of_date,
            'assets': assets,
            'liabilities': liabilities,
            'equity': equity,
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'total_equity': total_equity,
            'total_liabilities_and_equity': total_liabilities + total_equity
        }

    # ------------------------
    # Internal helpers
    # ------------------------
    def _normalize_account_type_key(self, account_type) -> str:
        """Return a string key for ACCOUNT_TYPES regardless of Enum or raw string input."""
        # Enum (e.g., AccountType.ASSET) -> its value ('Asset')
        if hasattr(account_type, 'value'):
            return account_type.value
        return str(account_type)

    def _get_normal_balance(self, account_type) -> Optional[str]:
        key = self._normalize_account_type_key(account_type)
        info = self.ACCOUNT_TYPES.get(key)
        return info.get('normal_balance') if info else None

    def get_income_statement(self, branch_id: str, start_date: date, end_date: date) -> Dict:
        """Generate income statement report"""
        # Get revenue accounts
        revenue_accounts = self.db.query(AccountingCode).filter(
            and_(
                AccountingCode.branch_id == branch_id,
                AccountingCode.account_type == 'Revenue'
            )
        ).all()

        # Get expense accounts
        expense_accounts = self.db.query(AccountingCode).filter(
            and_(
                AccountingCode.branch_id == branch_id,
                AccountingCode.account_type == 'Expense'
            )
        ).all()

        # Calculate revenue
        total_revenue = Decimal('0')
        revenue_details = []

        for account in revenue_accounts:
            revenue = self._get_account_movement(account.id, start_date, end_date)
            if revenue > 0:
                revenue_details.append({
                    'code': account.code,
                    'name': account.name,
                    'amount': float(revenue)
                })
                total_revenue += revenue

        # Calculate expenses
        total_expenses = Decimal('0')
        expense_details = []

        for account in expense_accounts:
            expense = self._get_account_movement(account.id, start_date, end_date)
            if expense > 0:
                expense_details.append({
                    'code': account.code,
                    'name': account.name,
                    'amount': float(expense)
                })
                total_expenses += expense

        # Calculate net income
        net_income = total_revenue - total_expenses

        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'revenue': {
                'details': revenue_details,
                'total': float(total_revenue)
            },
            'expenses': {
                'details': expense_details,
                'total': float(total_expenses)
            },
            'net_income': float(net_income)
        }

    def _get_account_movement(self, accounting_code_id: str, start_date: date, end_date: date) -> Decimal:
        """Get account movement for a specific period"""
        # Get balance at start of period
        start_balance = self.get_account_balance(accounting_code_id, start_date - date.resolution)

        # Get balance at end of period
        end_balance = self.get_account_balance(accounting_code_id, end_date)

        # Calculate movement
        return end_balance - start_balance

    def set_opening_balance(self, accounting_code_id: str, year: int, amount: Decimal) -> bool:
        """Set opening balance for an account for a specific year"""
        try:
            # Check if opening balance already exists
            existing_balance = self.db.query(OpeningBalance).filter(
                and_(
                    OpeningBalance.accounting_code_id == accounting_code_id,
                    OpeningBalance.year == year
                )
            ).first()

            if existing_balance:
                existing_balance.amount = amount
            else:
                opening_balance = OpeningBalance(
                    accounting_code_id=accounting_code_id,
                    year=year,
                    amount=amount
                )
                self.db.add(opening_balance)

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            return False

    def get_account_hierarchy(self, branch_id: str) -> List[Dict]:
        """Get accounting code hierarchy for the branch"""
        def build_hierarchy(parent_id=None):
            codes = self.db.query(AccountingCode).filter(
                and_(
                    AccountingCode.branch_id == branch_id,
                    AccountingCode.parent_id == parent_id
                )
            ).all()

            hierarchy = []
            for code in codes:
                node = {
                    'id': str(code.id),
                    'code': code.code,
                    'name': code.name,
                    'account_type': code.account_type,
                    'category': code.category,
                    'is_parent': code.is_parent,
                    'balance': float(self.get_account_balance(code.id)),
                    'children': build_hierarchy(code.id)
                }
                hierarchy.append(node)

            return hierarchy

        return build_hierarchy()

    def record_payment(self, payment) -> bool:
        """Record accounting entries for a payment"""
        try:
            from app.models.sales import Invoice
            import uuid

            # Get the invoice to understand the transaction
            invoice = self.db.query(Invoice).filter(Invoice.id == payment.invoice_id).first()
            if not invoice:
                raise ValueError("Invoice not found for payment")

            # Find or create appropriate accounting codes
            # Try to find existing cash accounts first
            cash_account = self.db.query(AccountingCode).filter(
                and_(
                    AccountingCode.branch_id == invoice.branch_id,
                    or_(
                        AccountingCode.code == '1111',  # Cash in Hand
                        AccountingCode.code == '1110',  # Cash and Cash Equivalents
                        AccountingCode.code == '1120',  # Bank Accounts
                        AccountingCode.name.ilike('%cash in hand%'),
                        AccountingCode.name.ilike('%cash%'),
                        AccountingCode.name.ilike('%bank%')
                    )
                )
            ).first()

            if not cash_account:
                # Create a basic cash account if none exists
                cash_account = AccountingCode(
                    id=str(uuid.uuid4()),
                    code="1111",
                    name="Cash in Hand",
                    account_type="Asset",
                    category="Cash",
                    branch_id=invoice.branch_id,
                    currency="BWP",
                    is_parent=False,
                    balance=Decimal('0.00'),
                    total_debits=Decimal('0.00'),
                    total_credits=Decimal('0.00')
                )
                self.db.add(cash_account)
                self.db.flush()
                print(f"[CASH_ACCOUNT_CREATED] Created cash account {cash_account.id} for branch {invoice.branch_id}")

            # Credit: Accounts Receivable (Asset - reducing)
            ar_account = self.db.query(AccountingCode).filter(
                and_(
                    AccountingCode.branch_id == invoice.branch_id,
                    AccountingCode.name.ilike('%receivable%')
                )
            ).first()

            if not ar_account:
                # Create accounts receivable if none exists
                ar_account = AccountingCode(
                    id=str(uuid.uuid4()),
                    code="1200",
                    name="Accounts Receivable",
                    account_type="Asset",
                    category="Current Assets",
                    branch_id=invoice.branch_id,
                    currency="BWP",
                    is_parent=False,
                    balance=Decimal('0.00'),
                    total_debits=Decimal('0.00'),
                    total_credits=Decimal('0.00')
                )
                self.db.add(ar_account)
                self.db.flush()
                print(f"[AR_ACCOUNT_CREATED] Created accounts receivable {ar_account.id} for branch {invoice.branch_id}")

            # Create journal entry using the standardized method
            entry_data = {
                'particulars': f"Payment received for Invoice {invoice.invoice_number}",
                'date_prepared': payment.payment_date,
                'date_posted': payment.payment_date,
                'book': 'Payments',
                'entries': [
                    {
                        'accounting_code_id': cash_account.id,
                        'entry_type': 'debit',
                        'amount': payment.amount,
                        'description': f"Cash received - Invoice {invoice.invoice_number}"
                    },
                    {
                        'accounting_code_id': ar_account.id,
                        'entry_type': 'credit',
                        'amount': payment.amount,
                        'description': f"Payment for Invoice {invoice.invoice_number}"
                    }
                ]
            }

            # Use the existing create_journal_entry method
            accounting_entry, result = self.create_journal_entry(entry_data, invoice.branch_id)

            if not result.get('success'):
                return False

            print(f"[PAYMENT_RECORDED] Payment {payment.id} recorded with accounting entry {accounting_entry.id}")
            return True

        except Exception as e:
            print(f"[PAYMENT_ERROR] Error recording payment: {str(e)}")
            self.db.rollback()
            return False
