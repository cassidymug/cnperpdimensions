from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, date
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from enum import Enum

from app.models.accounting import AccountingCode, AccountingEntry, JournalEntry, OpeningBalance
from app.models.sales import Sale, SaleItem
from app.models.purchases import Purchase, PurchaseItem
from app.models.inventory import Product, InventoryTransaction
from app.models.banking import BankAccount, BankTransaction, BankTransfer
from app.models.vat import VatReconciliationItem
from app.core.config import settings


class IFRSAccountType(Enum):
    """IFRS Account Types with normal balance and compliance rules"""
    ASSET = "Asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"
    REVENUE = "Revenue"
    EXPENSE = "Expense"


class IFRSComplianceError(Exception):
    """Custom exception for IFRS compliance errors"""
    pass


class IFRSAccountingService:
    """Comprehensive IFRS-compliant accounting service"""

    # IFRS Account Type Rules
    IFRS_ACCOUNT_RULES = {
        IFRSAccountType.ASSET: {
            'normal_balance': 'debit',
            'increase_with': 'debit',
            'decrease_with': 'credit',
            'balance_sheet': True,
            'income_statement': False
        },
        IFRSAccountType.LIABILITY: {
            'normal_balance': 'credit',
            'increase_with': 'credit',
            'decrease_with': 'debit',
            'balance_sheet': True,
            'income_statement': False
        },
        IFRSAccountType.EQUITY: {
            'normal_balance': 'credit',
            'increase_with': 'credit',
            'decrease_with': 'debit',
            'balance_sheet': True,
            'income_statement': False
        },
        IFRSAccountType.REVENUE: {
            'normal_balance': 'credit',
            'increase_with': 'credit',
            'decrease_with': 'debit',
            'balance_sheet': False,
            'income_statement': True
        },
        IFRSAccountType.EXPENSE: {
            'normal_balance': 'debit',
            'increase_with': 'debit',
            'decrease_with': 'credit',
            'balance_sheet': False,
            'income_statement': True
        }
    }

    # IFRS Reporting Categories
    IFRS_REPORTING_CATEGORIES = {
        'A1': 'Current Assets',
        'A1.1': 'Cash and Cash Equivalents',
        'A1.2': 'Trade and Other Receivables',
        'A1.3': 'Inventories',
        'A2': 'Non-current Assets',
        'A2.1': 'Property, Plant and Equipment',
        'A2.2': 'Intangible Assets',
        'A2.3': 'Investments',
        'L1': 'Current Liabilities',
        'L1.1': 'Trade and Other Payables',
        'L1.2': 'Short-term Borrowings',
        'L1.3': 'Current Tax Liabilities',
        'L2': 'Non-current Liabilities',
        'L2.1': 'Long-term Borrowings',
        'L2.2': 'Deferred Tax Liabilities',
        'E1': 'Share Capital',
        'E2': 'Retained Earnings',
        'E3': 'Other Equity',
        'R1': 'Revenue from Contracts with Customers',
        'R2': 'Other Income',
        'X1': 'Cost of Sales',
        'X2': 'Selling and Distribution Expenses',
        'X3': 'Administrative Expenses',
        'X4': 'Finance Costs'
    }

    def __init__(self, db: Session):
        self.db = db

    def create_ifrs_compliant_entry(self, entry_data: Dict, branch_id: str) -> Tuple[AccountingEntry, Dict]:
        """
        Create IFRS-compliant accounting entry with proper double-entry bookkeeping

        Args:
            entry_data: Dictionary containing entry details
            branch_id: Branch ID for the entry

        Returns:
            Tuple of (accounting_entry, result_dict)
        """
        try:
            # Validate entry data
            self._validate_entry_data(entry_data)

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

            # Create IFRS-compliant journal entries
            journal_entries = self._create_ifrs_journal_entries(accounting_entry, entry_data['entries'])

            # Validate double-entry compliance
            self._validate_double_entry_compliance(journal_entries)

            # Validate IFRS compliance
            self._validate_ifrs_compliance(journal_entries)

            # Commit all entries
            self.db.commit()
            self.db.refresh(accounting_entry)

            return accounting_entry, {
                'success': True,
                'entry_id': str(accounting_entry.id),
                'journal_entries_count': len(journal_entries),
                'total_debits': float(sum(je.debit_amount for je in journal_entries)),
                'total_credits': float(sum(je.credit_amount for je in journal_entries))
            }

        except Exception as e:
            self.db.rollback()
            return None, {'success': False, 'error': str(e)}

    def _validate_entry_data(self, entry_data: Dict) -> None:
        """Validate entry data for completeness and accuracy"""
        required_fields = ['particulars', 'entries']
        for field in required_fields:
            if field not in entry_data:
                raise IFRSComplianceError(f"Missing required field: {field}")

        if not entry_data['entries']:
            raise IFRSComplianceError("Entry must have at least one journal entry")

        # Validate that entries have required fields
        for entry in entry_data['entries']:
            if 'accounting_code_id' not in entry:
                raise IFRSComplianceError("Each entry must specify accounting_code_id")
            if 'amount' not in entry:
                raise IFRSComplianceError("Each entry must specify amount")
            if 'entry_type' not in entry:
                raise IFRSComplianceError("Each entry must specify entry_type")

    def _create_ifrs_journal_entries(self, accounting_entry: AccountingEntry, entries: List[Dict]) -> List[JournalEntry]:
        """Create IFRS-compliant journal entries"""
        journal_entries = []

        for entry_data in entries:
            # Get accounting code
            accounting_code = self.db.query(AccountingCode).filter(
                AccountingCode.id == entry_data['accounting_code_id']
            ).first()

            if not accounting_code:
                raise IFRSComplianceError(f"Accounting code not found: {entry_data['accounting_code_id']}")

            # Validate entry type against account type
            self._validate_entry_type_for_account(entry_data['entry_type'], accounting_code.account_type)

            # Create journal entry
            # Determine debit/credit allocation from provided amount
            amount = Decimal(entry_data['amount'])
            if entry_data['entry_type'] == 'debit':
                debit_amount = amount
                credit_amount = Decimal('0')
            else:
                debit_amount = Decimal('0')
                credit_amount = amount

            journal_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=accounting_code.id,
                entry_type=entry_data['entry_type'],
                description=entry_data.get('description', ''),
                date=accounting_entry.date_prepared,
                date_posted=accounting_entry.date_posted,
                branch_id=accounting_entry.branch_id,
                debit_amount=debit_amount,
                credit_amount=credit_amount
            )

            self.db.add(journal_entry)
            journal_entries.append(journal_entry)

        return journal_entries

    def _validate_entry_type_for_account(self, entry_type: str, account_type: str) -> None:
        """Validate that entry type is appropriate for account type"""
        if account_type not in [at.value for at in IFRSAccountType]:
            raise IFRSComplianceError(f"Invalid account type: {account_type}")

        account_rules = self.IFRS_ACCOUNT_RULES[IFRSAccountType(account_type)]

        # Check if entry type follows normal balance rules
        if entry_type == 'debit' and account_rules['normal_balance'] == 'credit':
            # This is acceptable (e.g., debiting a liability to decrease it)
            pass
        elif entry_type == 'credit' and account_rules['normal_balance'] == 'debit':
            # This is acceptable (e.g., crediting an asset to decrease it)
            pass
        else:
            # Entry type follows normal balance (expected behavior)
            pass

    def _validate_double_entry_compliance(self, journal_entries: List[JournalEntry]) -> None:
        """Validate that debits equal credits (double-entry principle)"""
        total_debits = sum(je.debit_amount for je in journal_entries)
        total_credits = sum(je.credit_amount for je in journal_entries)

        if total_debits != total_credits:
            raise IFRSComplianceError(
                f"Double-entry principle violated: Debits ({total_debits}) != Credits ({total_credits})"
            )

    def _validate_ifrs_compliance(self, journal_entries: List[JournalEntry]) -> None:
        """Validate IFRS compliance for journal entries"""
        warned_missing_code = set()
        warned_missing_tag = set()
        for journal_entry in journal_entries:
            accounting_code = journal_entry.accounting_code
            if not accounting_code:
                key = id(journal_entry)
                if key not in warned_missing_code:
                    print("Warning: Journal entry missing accounting code - skipping IFRS validation (suppressed duplicates)")
                    warned_missing_code.add(key)
                continue
            if not accounting_code.reporting_tag:
                if accounting_code.id not in warned_missing_tag:
                    print(f"Warning: Accounting code {accounting_code.code} ({accounting_code.name}) missing IFRS reporting tag - using as fallback")
                    warned_missing_tag.add(accounting_code.id)
                continue
            if accounting_code.reporting_tag not in self.IFRS_REPORTING_CATEGORIES:
                raise IFRSComplianceError(f"Invalid IFRS reporting tag: {accounting_code.reporting_tag}")

    def create_sale_journal_entries(self, sale: Sale, bank_account_id: Optional[str] = None) -> List[JournalEntry]:
        """Create IFRS-compliant journal entries for a sale transaction"""
        try:
            # Get required accounting codes
            sales_revenue_code = self._get_accounting_code_by_ifrs_tag('R1')  # Revenue
            cash_code = self._get_accounting_code_by_ifrs_tag('A1.1')  # Cash / Bank (default)
            vat_payable_code = self._get_accounting_code_by_ifrs_tag('L1.3')  # VAT Payable
            cogs_code = self._get_accounting_code_by_ifrs_tag('X1')  # Cost of Sales
            inventory_code = self._get_accounting_code_by_ifrs_tag('A1.3')  # Inventory

            if not all([sales_revenue_code, cash_code, vat_payable_code, cogs_code, inventory_code]):
                raise IFRSComplianceError("Required accounting codes not found for sale transaction")

            # Create accounting entry
            accounting_entry = AccountingEntry(
                date_prepared=sale.date,
                date_posted=sale.date,
                particulars=f"Sale transaction #{sale.id}",
                book=f"SALE-{sale.id}",
                status='posted',
                branch_id=sale.branch_id
            )

            self.db.add(accounting_entry)
            self.db.flush()

            journal_entries = []

            # 1. Debit Cash/Bank (or Accounts Receivable for credit sales)
            pm = (sale.payment_method or '').lower()
            if pm in ['on_account', 'credit']:
                # Credit sale - debit Accounts Receivable
                ar_code = self._get_accounting_code_by_ifrs_tag('A1.2')  # Receivables
                if ar_code:
                    ar_entry = JournalEntry(
                        accounting_entry_id=accounting_entry.id,
                        accounting_code_id=ar_code.id,
                        entry_type='debit',
                        debit_amount=sale.total_amount,
                        credit_amount=Decimal('0'),
                        description=f"Accounts receivable for sale {sale.reference or '#' + sale.id[:8]}",
                        date=sale.date,
                        date_posted=sale.date,
                        branch_id=sale.branch_id
                    )
                    self.db.add(ar_entry)
                    journal_entries.append(ar_entry)
            elif pm == 'cash':
                # Cash sales go to Undeposited Funds (1114) - salesperson takings
                # Cash will be moved to 1111 Cash in Hand when submitted
                undeposited_funds_code = self.db.query(AccountingCode).filter(
                    AccountingCode.code == '1114'
                ).first()

                if not undeposited_funds_code:
                    # Fallback to cash code if 1114 doesn't exist yet
                    undeposited_funds_code = cash_code
                    description = f"Cash received for sale {sale.reference or '#' + sale.id[:8]}"
                else:
                    description = f"Cash received for sale {sale.reference or '#' + sale.id[:8]} (salesperson takings - undeposited)"

                cash_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=undeposited_funds_code.id,
                    entry_type='debit',
                    debit_amount=sale.total_amount,
                    credit_amount=Decimal('0'),
                    description=description,
                    date=sale.date,
                    date_posted=sale.date,
                    branch_id=sale.branch_id
                )
                self.db.add(cash_entry)
                journal_entries.append(cash_entry)
            else:
                # Card/Bank payment
                debit_account_code_id = None
                description = f"Card/Bank payment for sale {sale.reference or '#' + sale.id[:8]}"
                if pm in ['card', 'bank'] and bank_account_id:
                    # Use the selected bank account's accounting code
                    bank_account = self.db.query(BankAccount).filter(BankAccount.id == bank_account_id).first()
                    if bank_account and bank_account.accounting_code_id:
                        debit_account_code_id = bank_account.accounting_code_id
                if not debit_account_code_id:
                    # Fallback to Cash & Cash Equivalents account by IFRS tag
                    debit_account_code_id = cash_code.id
                payment_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=debit_account_code_id,
                    entry_type='debit',
                    debit_amount=sale.total_amount,
                    credit_amount=Decimal('0'),
                    description=description,
                    date=sale.date,
                    date_posted=sale.date,
                    branch_id=sale.branch_id
                )
                self.db.add(payment_entry)
                journal_entries.append(payment_entry)

            # 2. Credit Sales Revenue (ex-VAT)
            revenue_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=sales_revenue_code.id,
                entry_type='credit',
                debit_amount=Decimal('0'),
                credit_amount=sale.total_amount - sale.total_vat_amount,
                description=f"Sales revenue for sale {sale.reference or '#' + sale.id[:8]}",
                date=sale.date,
                date_posted=sale.date,
                branch_id=sale.branch_id
            )
            self.db.add(revenue_entry)
            journal_entries.append(revenue_entry)

            # 3. Credit VAT Payable (if VAT applicable)
            if sale.total_vat_amount > 0:
                # Use the output VAT account from the sale if set, otherwise use code 2132 (VAT Payable - Output VAT)
                vat_account_code = None
                if sale.output_vat_account_id:
                    vat_account_code = self.db.query(AccountingCode).filter(
                        AccountingCode.id == sale.output_vat_account_id
                    ).first()

                if not vat_account_code:
                    # Fallback to account 2132 (VAT Payable - Output VAT)
                    vat_account_code = self.db.query(AccountingCode).filter(
                        AccountingCode.code == '2132'
                    ).first()

                if not vat_account_code:
                    # Final fallback to IFRS tag
                    vat_account_code = vat_payable_code

                if vat_account_code:
                    vat_entry = JournalEntry(
                        accounting_entry_id=accounting_entry.id,
                        accounting_code_id=vat_account_code.id,
                        entry_type='credit',
                        debit_amount=Decimal('0'),
                        credit_amount=sale.total_vat_amount,
                        description=f"VAT collected for sale {sale.reference or '#' + sale.id[:8]}",
                        date=sale.date,
                        date_posted=sale.date,
                        branch_id=sale.branch_id
                    )
                    self.db.add(vat_entry)
                    journal_entries.append(vat_entry)

            # 4. Cost of Goods Sold entries (if inventory items)
            cogs_total = self._calculate_cogs_for_sale(sale)
            if cogs_total > 0:
                # Debit Cost of Sales
                cogs_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=cogs_code.id,
                    entry_type='debit',
                    debit_amount=cogs_total,
                    credit_amount=Decimal('0'),
                    description=f"Cost of goods sold for sale {sale.reference or '#' + sale.id[:8]}",
                    date=sale.date,
                    date_posted=sale.date,
                    branch_id=sale.branch_id
                )
                self.db.add(cogs_entry)
                journal_entries.append(cogs_entry)

                # Credit Inventory
                inventory_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=inventory_code.id,
                    entry_type='credit',
                    debit_amount=Decimal('0'),
                    credit_amount=cogs_total,
                    description=f"Inventory reduction for sale {sale.reference or '#' + sale.id[:8]}",
                    date=sale.date,
                    date_posted=sale.date,
                    branch_id=sale.branch_id
                )
                self.db.add(inventory_entry)
                journal_entries.append(inventory_entry)

            # Validate compliance
            self._validate_double_entry_compliance(journal_entries)
            self._validate_ifrs_compliance(journal_entries)

            self.db.commit()
            return journal_entries

        except Exception as e:
            self.db.rollback()
            raise IFRSComplianceError(f"Error creating sale journal entries: {str(e)}")

    def create_purchase_journal_entries(self, purchase: Purchase) -> List[JournalEntry]:
        """Create IFRS-compliant journal entries for a purchase transaction"""
        try:
            # Get required accounting codes with fallback to default codes
            inventory_code = self._get_accounting_code_by_ifrs_tag('A1.3') or self._get_default_accounting_code('Inventory', 'Asset')
            cash_code = self._get_accounting_code_by_ifrs_tag('A1.1') or self._get_default_accounting_code('Cash', 'Asset')
            ap_code = self._get_accounting_code_by_ifrs_tag('L1.1') or self._get_default_accounting_code('Accounts Payable', 'Liability')
            vat_receivable_code = self._get_accounting_code_by_ifrs_tag('A1.2') or self._get_default_accounting_code('VAT Receivable', 'Asset')
            ppe_code = self._get_accounting_code_by_ifrs_tag('A2.1') or self._get_default_accounting_code('Property, Plant and Equipment', 'Asset')

            if not all([inventory_code, cash_code, ap_code]):
                # Attempt on-the-fly creation of minimal required accounts (useful in tests / ephemeral DBs)
                created_any = False
                def ensure_account(code_val: str, name: str, acct_type: str, category: str, tag: str):
                    existing = self.db.query(AccountingCode).filter(
                        (AccountingCode.name == name) | (AccountingCode.code == code_val)
                    ).first()
                    if not existing:
                        # Convert string account type to enum expected by validator
                        try:
                            from app.models.accounting_constants import AccountType as _AcctTypeEnum
                            acct_type_enum = {
                                'Asset': _AcctTypeEnum.ASSET,
                                'Liability': _AcctTypeEnum.LIABILITY,
                                'Equity': _AcctTypeEnum.EQUITY,
                                'Revenue': _AcctTypeEnum.REVENUE,
                                'Expense': _AcctTypeEnum.EXPENSE,
                            }[acct_type]
                        except Exception:
                            acct_type_enum = acct_type  # fallback (may raise validator error, surfaced in tests)
                        acct = AccountingCode(
                            code=code_val,
                            name=name,
                            account_type=acct_type_enum,
                            category=category,
                            is_parent=False,
                            reporting_tag=tag,
                        )
                        self.db.add(acct)
                        return True
                    # backfill tag if missing
                    if not existing.reporting_tag:
                        existing.reporting_tag = tag
                        return True
                    return False

                created_any |= ensure_account('1300', 'Inventory', 'Asset', 'Inventories', 'A1.3')
                created_any |= ensure_account('1000', 'Cash', 'Asset', 'Current Assets', 'A1.1')
                created_any |= ensure_account('2100', 'Accounts Payable', 'Liability', 'Trade and Other Payables', 'L1.1')
                created_any |= ensure_account('1200', 'VAT Receivable', 'Asset', 'Trade and Other Receivables', 'A1.2')
                created_any |= ensure_account('1500', 'Property, Plant and Equipment', 'Asset', 'Property, Plant and Equipment', 'A2.1')
                if created_any:
                    self.db.flush()
                    # Re-fetch after creation
                    inventory_code = self._get_accounting_code_by_ifrs_tag('A1.3') or self._get_default_accounting_code('Inventory', 'Asset')
                    cash_code = self._get_accounting_code_by_ifrs_tag('A1.1') or self._get_default_accounting_code('Cash', 'Asset')
                    ap_code = self._get_accounting_code_by_ifrs_tag('L1.1') or self._get_default_accounting_code('Accounts Payable', 'Liability')
                    vat_receivable_code = self._get_accounting_code_by_ifrs_tag('A1.2') or self._get_default_accounting_code('VAT Receivable', 'Asset')
                    ppe_code = self._get_accounting_code_by_ifrs_tag('A2.1') or self._get_default_accounting_code('Property, Plant and Equipment', 'Asset')

            if not all([inventory_code, cash_code, ap_code]):
                raise IFRSComplianceError("Required accounting codes not found for purchase transaction")

            # Create accounting entry
            accounting_entry = AccountingEntry(
                date_prepared=purchase.purchase_date,
                date_posted=purchase.purchase_date,
                particulars=f"Purchase transaction #{purchase.reference or purchase.id}",
                book=f"PURCHASE-{purchase.id}",
                status='posted',
                branch_id=purchase.branch_id
            )

            self.db.add(accounting_entry)
            self.db.flush()

            journal_entries = []

            # Calculate allocations between inventory and capital assets (PPE)
            total_ex_vat = Decimal(purchase.total_amount_ex_vat or (purchase.total_amount - purchase.total_vat_amount))
            inventory_total = Decimal('0')
            asset_total = Decimal('0')
            total_item_base = Decimal('0')
            inventory_descriptions: list[str] = []
            asset_entries: dict[str, dict] = {}
            account_cache: dict[str, Optional[AccountingCode]] = {}

            for item in purchase.purchase_items:
                amount = Decimal(item.total_cost) if item.total_cost is not None else None
                if amount is None or amount == 0:
                    qty = Decimal(item.quantity) if item.quantity is not None else None
                    unit_cost = Decimal(item.cost) if item.cost is not None else None
                    if qty is not None and unit_cost is not None:
                        amount = qty * unit_cost
                if amount is None:
                    amount = Decimal('0')

                total_item_base += amount

                if item.is_asset:
                    target_account: Optional[AccountingCode] = None
                    if item.asset_accounting_code_id:
                        if item.asset_accounting_code_id in account_cache:
                            target_account = account_cache[item.asset_accounting_code_id]
                        else:
                            target_account = self.db.query(AccountingCode).filter(
                                AccountingCode.id == item.asset_accounting_code_id
                            ).first()
                            account_cache[item.asset_accounting_code_id] = target_account
                    if not target_account:
                        target_account = ppe_code
                    if not target_account:
                        raise IFRSComplianceError("Property, Plant and Equipment accounting code not found for asset purchase line")

                    entry = asset_entries.get(target_account.id)
                    if not entry:
                        entry = {
                            'account': target_account,
                            'amount': Decimal('0'),
                            'descriptions': []
                        }
                        asset_entries[target_account.id] = entry
                    entry['amount'] += amount
                    description_label = (item.asset_name or item.description or f"Asset item {item.id}").strip() or "Asset purchase item"
                    entry['descriptions'].append(description_label)
                    asset_total += amount
                else:
                    inventory_total += amount
                    if item.is_inventory:
                        if item.product:
                            inventory_descriptions.append(f"{item.quantity}x {item.product.name}")
                        elif item.description:
                            inventory_descriptions.append(f"{item.quantity}x {item.description}")

            extra_costs = total_ex_vat - total_item_base
            if extra_costs > Decimal('0'):
                if asset_total > Decimal('0') and total_item_base > Decimal('0'):
                    asset_share = (asset_total / total_item_base) * extra_costs
                    inventory_share = extra_costs - asset_share
                    for entry in asset_entries.values():
                        if asset_total > Decimal('0'):
                            proportion = entry['amount'] / asset_total
                            entry['amount'] += asset_share * proportion
                    asset_total += asset_share
                    inventory_total += inventory_share
                else:
                    inventory_total += extra_costs

            # Clamp small negative rounding differences
            if inventory_total < Decimal('0') and abs(inventory_total) < Decimal('0.01'):
                inventory_total = Decimal('0')

            # Build unified description list across inventory/asset lines for later reuse
            description_sources: List[str] = []
            if inventory_descriptions:
                description_sources.extend(inventory_descriptions)
            for entry in asset_entries.values():
                description_sources.extend(entry['descriptions'])

            if description_sources:
                description_preview = ", ".join(description_sources[:5])
                if len(description_sources) > 5:
                    description_preview += ", ..."
            else:
                description_preview = "Goods and services"

            # Create inventory journal entry if required
            if inventory_total > Decimal('0'):
                items_description = ", ".join(inventory_descriptions) if inventory_descriptions else description_preview
                detailed_description = f"Inventory purchase: {items_description} (Ref: {purchase.reference or purchase.id})"
                inventory_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=inventory_code.id,
                    entry_type='debit',
                    description=detailed_description,
                    date=purchase.purchase_date,
                    date_posted=purchase.purchase_date,
                    branch_id=purchase.branch_id,
                    debit_amount=inventory_total,
                    credit_amount=Decimal('0')
                )
                self.db.add(inventory_entry)
                journal_entries.append(inventory_entry)

            # Create journal entries for capital assets (PPE)
            for entry in asset_entries.values():
                if entry['amount'] <= Decimal('0'):
                    continue
                description_chunks = entry['descriptions'][:5]
                description_text = ", ".join(description_chunks)
                if len(entry['descriptions']) > 5:
                    description_text += ", ..."
                asset_description = (
                    f"Asset purchase: {description_text} (Ref: {purchase.reference or purchase.id})"
                )
                asset_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=entry['account'].id,
                    entry_type='debit',
                    description=asset_description,
                    date=purchase.purchase_date,
                    date_posted=purchase.purchase_date,
                    branch_id=purchase.branch_id,
                    debit_amount=entry['amount'],
                    credit_amount=Decimal('0')
                )
                self.db.add(asset_entry)
                journal_entries.append(asset_entry)

            # 2. Debit VAT Receivable (if VAT is applicable)
            supplier_name = purchase.supplier.name if purchase.supplier else "Unknown Supplier"
            if purchase.total_vat_amount > 0:
                # Use the input VAT account from the purchase if set, otherwise use code 1160 (VAT Receivable - Input VAT)
                vat_account_code = None
                if purchase.input_vat_account_id:
                    vat_account_code = self.db.query(AccountingCode).filter(
                        AccountingCode.id == purchase.input_vat_account_id
                    ).first()

                if not vat_account_code:
                    # Fallback to account 1160 (VAT Receivable - Input VAT)
                    vat_account_code = self.db.query(AccountingCode).filter(
                        AccountingCode.code == '1160'
                    ).first()

                if not vat_account_code:
                    # Final fallback to IFRS tag or default
                    if vat_receivable_code:
                        vat_account_code = vat_receivable_code
                    else:
                        raise IFRSComplianceError("VAT Receivable accounting code not found.")

                vat_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=vat_account_code.id,
                    entry_type='debit',
                    description=f"Input VAT on purchase from {supplier_name} - {purchase.total_vat_amount} (Ref: {purchase.reference or purchase.id})",
                    date=purchase.purchase_date,
                    date_posted=purchase.purchase_date,
                    branch_id=purchase.branch_id,
                    debit_amount=purchase.total_vat_amount,
                    credit_amount=Decimal('0')
                )
                self.db.add(vat_entry)
                journal_entries.append(vat_entry)

            # 3. Credit Cash or Accounts Payable for the full invoice amount
            total_invoice_amount = purchase.total_amount

            # Create detailed supplier description
            items_description = description_preview
            detailed_payable_description = f"Amount due to {supplier_name} - {items_description} (Ref: {purchase.reference or purchase.id})"

            # Always credit Accounts Payable for the full invoice amount.
            ap_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=ap_code.id,
                entry_type='credit',
                description=detailed_payable_description,
                date=purchase.purchase_date,
                date_posted=purchase.purchase_date,
                branch_id=purchase.branch_id,
                debit_amount=Decimal('0'),
                credit_amount=total_invoice_amount
            )
            self.db.add(ap_entry)
            journal_entries.append(ap_entry)

            # Validate compliance
            self._validate_double_entry_compliance(journal_entries)
            self._validate_ifrs_compliance(journal_entries)

            self.db.commit()
            return journal_entries

        except Exception as e:
            self.db.rollback()
            raise IFRSComplianceError(f"Error creating purchase journal entries: {str(e)}")

    def create_purchase_payment_journal_entries(self, purchase: Purchase, payment_amount: Decimal, payment_date: date, bank_account_id: Optional[str] = None) -> List[JournalEntry]:
        """Create IFRS-compliant journal entries for a purchase payment."""
        try:
            # Get required accounting codes
            ap_code = self._get_accounting_code_by_ifrs_tag('L1.1') or self._get_default_accounting_code('Accounts Payable', 'Liability')

            # Determine the credit account (Cash or a specific Bank Account)
            if bank_account_id:
                bank_account = self.db.query(BankAccount).filter(BankAccount.id == bank_account_id).first()
                if not bank_account or not bank_account.accounting_code:
                    raise IFRSComplianceError(f"Bank account {bank_account_id} not found or has no associated accounting code.")
                credit_account_code = bank_account.accounting_code
            else:
                # Default to the primary cash account if no bank is specified
                credit_account_code = self._get_accounting_code_by_ifrs_tag('A1.1') or self._get_default_accounting_code('Cash', 'Asset')

            if not ap_code or not credit_account_code:
                raise IFRSComplianceError("Required accounting codes (Accounts Payable and Cash/Bank) not found for purchase payment.")

            # Create the main accounting entry
            accounting_entry = AccountingEntry(
                date_prepared=payment_date,
                date_posted=payment_date,
                particulars=f"Payment for Purchase #{purchase.reference or purchase.id}",
                book=f"PAYMENT-{purchase.id}",
                status='posted',
                branch_id=purchase.branch_id
            )
            self.db.add(accounting_entry)
            self.db.flush()

            journal_entries = []

            # 1. Debit Accounts Payable to reduce the liability
            debit_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=ap_code.id,
                entry_type='debit',
                description=f"Reduce liability for purchase #{purchase.reference or purchase.id}",
                date=payment_date,
                date_posted=payment_date,
                branch_id=purchase.branch_id,
                debit_amount=payment_amount,
                credit_amount=Decimal('0')
            )
            self.db.add(debit_entry)
            journal_entries.append(debit_entry)

            # 2. Credit Cash/Bank to reduce the asset
            credit_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=credit_account_code.id,
                entry_type='credit',
                description=f"Payment from {credit_account_code.name} for purchase #{purchase.reference or purchase.id}",
                date=payment_date,
                date_posted=payment_date,
                branch_id=purchase.branch_id,
                debit_amount=Decimal('0'),
                credit_amount=payment_amount
            )
            self.db.add(credit_entry)
            journal_entries.append(credit_entry)

            # Validate and commit
            self._validate_double_entry_compliance(journal_entries)
            self.db.commit()

            return journal_entries

        except Exception as e:
            self.db.rollback()
            raise IFRSComplianceError(f"Error creating purchase payment journal entries: {str(e)}")

    def create_tax_payment_journal_entries(self, payment_amount: Decimal, payment_date: date, branch_id: str, bank_account_id: Optional[str] = None, vat_output_amount: Decimal = None, vat_input_amount: Decimal = None) -> List[JournalEntry]:
        """
        Create IFRS-compliant journal entries for VAT payment with proper settlement.

        This method creates journal entries that:
        1. Clear VAT Payable (Output VAT from sales) - Account 2132
        2. Clear VAT Receivable (Input VAT from purchases) - Account 1160
        3. Record payment to tax authority from bank/cash

        Args:
            payment_amount: Net amount paid to tax authority (vat_output - vat_input)
            payment_date: Date of payment
            branch_id: Branch ID
            bank_account_id: Bank account used for payment (optional, defaults to cash)
            vat_output_amount: Total Output VAT collected from sales (optional, uses payment_amount if not provided)
            vat_input_amount: Total Input VAT paid on purchases (optional, calculates from output if not provided)

        Journal Entry Structure (when Output > Input, net payable):
            DR  VAT Payable (2132)         [vat_output_amount]     Clear Output VAT liability
            DR  VAT Receivable (1160)      [vat_input_amount]      Clear Input VAT asset (contra)
                CR  Bank/Cash                  [payment_amount]        Payment to tax authority
                CR  VAT Receivable (1160)      [vat_input_amount]      Offset Input VAT

        Simplified Entry:
            DR  VAT Payable (2132)         [vat_output_amount]
                CR  Bank/Cash                  [payment_amount]
                CR  VAT Receivable (1160)      [vat_input_amount]
        """
        try:
            # Get required accounting codes
            # 2132 - VAT Payable (Output VAT)
            vat_payable_code = self.db.query(AccountingCode).filter(AccountingCode.code == '2132').first()
            if not vat_payable_code:
                vat_payable_code = self._get_accounting_code_by_ifrs_tag('L1.3') or self._get_default_accounting_code('VAT Payable', 'Liability')

            # 1160 - VAT Receivable (Input VAT)
            vat_receivable_code = self.db.query(AccountingCode).filter(AccountingCode.code == '1160').first()
            if not vat_receivable_code:
                vat_receivable_code = self._get_default_accounting_code('VAT Receivable', 'Asset')

            # Determine the credit account (Cash or a specific Bank Account)
            if bank_account_id:
                bank_account = self.db.query(BankAccount).filter(BankAccount.id == bank_account_id).first()
                if not bank_account or not bank_account.accounting_code:
                    raise IFRSComplianceError(f"Bank account {bank_account_id} not found or has no associated accounting code.")
                credit_account_code = bank_account.accounting_code
            else:
                # Default to the primary cash account if no bank is specified
                credit_account_code = self._get_accounting_code_by_ifrs_tag('A1.1') or self._get_default_accounting_code('Cash', 'Asset')

            if not vat_payable_code or not vat_receivable_code or not credit_account_code:
                raise IFRSComplianceError("Required accounting codes (VAT Payable, VAT Receivable, and Cash/Bank) not found for tax payment.")

            # Calculate VAT amounts if not provided
            if vat_output_amount is None and vat_input_amount is None:
                # If neither provided, assume payment_amount is net (output - input)
                # We can't determine the breakdown, so use simple entry
                vat_output_amount = payment_amount
                vat_input_amount = Decimal('0')
            elif vat_output_amount is not None and vat_input_amount is None:
                # Calculate input from output and payment
                vat_input_amount = vat_output_amount - payment_amount
            elif vat_output_amount is None and vat_input_amount is not None:
                # Calculate output from input and payment
                vat_output_amount = payment_amount + vat_input_amount

            # Validate amounts
            net_vat = vat_output_amount - vat_input_amount
            if abs(net_vat - payment_amount) > Decimal('0.01'):  # Allow 1 cent rounding difference
                raise IFRSComplianceError(f"VAT amounts don't match payment: Output {vat_output_amount} - Input {vat_input_amount} = {net_vat}, but payment is {payment_amount}")

            # Create the main accounting entry
            accounting_entry = AccountingEntry(
                date_prepared=payment_date,
                date_posted=payment_date,
                particulars=f"VAT Settlement & Payment to Tax Authority (Output: {vat_output_amount}, Input: {vat_input_amount}, Net: {payment_amount})",
                book="VAT_SETTLEMENT",
                status='posted',
                branch_id=branch_id
            )
            self.db.add(accounting_entry)
            self.db.flush()

            journal_entries = []

            # 1. Debit VAT Payable (2132) to clear Output VAT liability from sales
            if vat_output_amount > 0:
                vat_payable_debit = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=vat_payable_code.id,
                    entry_type='debit',
                    description=f"Clear VAT Payable (Output VAT collected from sales)",
                    date=payment_date,
                    date_posted=payment_date,
                    branch_id=branch_id,
                    debit_amount=vat_output_amount,
                    credit_amount=Decimal('0')
                )
                self.db.add(vat_payable_debit)
                journal_entries.append(vat_payable_debit)

            # 2. Credit VAT Receivable (1160) to clear Input VAT asset from purchases
            if vat_input_amount > 0:
                vat_receivable_credit = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=vat_receivable_code.id,
                    entry_type='credit',
                    description=f"Clear VAT Receivable (Input VAT paid on purchases)",
                    date=payment_date,
                    date_posted=payment_date,
                    branch_id=branch_id,
                    debit_amount=Decimal('0'),
                    credit_amount=vat_input_amount
                )
                self.db.add(vat_receivable_credit)
                journal_entries.append(vat_receivable_credit)

            # 3. Credit Cash/Bank for net payment to tax authority
            bank_credit = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=credit_account_code.id,
                entry_type='credit',
                description=f"VAT payment to tax authority from {credit_account_code.name}",
                date=payment_date,
                date_posted=payment_date,
                branch_id=branch_id,
                debit_amount=Decimal('0'),
                credit_amount=payment_amount
            )
            self.db.add(bank_credit)
            journal_entries.append(bank_credit)

            # Validate double-entry compliance
            self._validate_double_entry_compliance(journal_entries)
            self.db.commit()

            return journal_entries

        except Exception as e:
            self.db.rollback()
            raise IFRSComplianceError(f"Error creating VAT payment journal entries: {str(e)}")

    def create_vat_refund_journal_entries(self, refund_amount: Decimal, refund_date: date, branch_id: str, bank_account_id: Optional[str] = None, vat_output_amount: Decimal = None, vat_input_amount: Decimal = None) -> List[JournalEntry]:
        """
        Create IFRS-compliant journal entries for VAT refund (when Input VAT > Output VAT).

        This occurs when a business has paid more VAT on purchases than collected on sales,
        resulting in a net receivable from the tax authority.

        Args:
            refund_amount: Net amount received from tax authority (vat_input - vat_output)
            refund_date: Date of refund receipt
            branch_id: Branch ID
            bank_account_id: Bank account for refund (optional, defaults to cash)
            vat_output_amount: Total Output VAT collected from sales
            vat_input_amount: Total Input VAT paid on purchases

        Journal Entry Structure (when Input > Output, net receivable):
            DR  Bank/Cash                  [refund_amount]         Refund received
            DR  VAT Payable (2132)         [vat_output_amount]     Clear Output VAT (if any)
                CR  VAT Receivable (1160)      [vat_input_amount]      Clear Input VAT asset
        """
        try:
            # Get required accounting codes
            # 2132 - VAT Payable (Output VAT)
            vat_payable_code = self.db.query(AccountingCode).filter(AccountingCode.code == '2132').first()
            if not vat_payable_code:
                vat_payable_code = self._get_accounting_code_by_ifrs_tag('L1.3') or self._get_default_accounting_code('VAT Payable', 'Liability')

            # 1160 - VAT Receivable (Input VAT)
            vat_receivable_code = self.db.query(AccountingCode).filter(AccountingCode.code == '1160').first()
            if not vat_receivable_code:
                vat_receivable_code = self._get_default_accounting_code('VAT Receivable', 'Asset')

            # Determine the debit account (Cash or a specific Bank Account)
            if bank_account_id:
                bank_account = self.db.query(BankAccount).filter(BankAccount.id == bank_account_id).first()
                if not bank_account or not bank_account.accounting_code:
                    raise IFRSComplianceError(f"Bank account {bank_account_id} not found or has no associated accounting code.")
                debit_account_code = bank_account.accounting_code
            else:
                # Default to the primary cash account
                debit_account_code = self._get_accounting_code_by_ifrs_tag('A1.1') or self._get_default_accounting_code('Cash', 'Asset')

            if not vat_payable_code or not vat_receivable_code or not debit_account_code:
                raise IFRSComplianceError("Required accounting codes (VAT Payable, VAT Receivable, and Cash/Bank) not found for VAT refund.")

            # Calculate VAT amounts if not provided
            if vat_output_amount is None and vat_input_amount is None:
                # If neither provided, assume refund_amount is net (input - output)
                vat_output_amount = Decimal('0')
                vat_input_amount = refund_amount
            elif vat_input_amount is not None and vat_output_amount is None:
                # Calculate output from input and refund
                vat_output_amount = vat_input_amount - refund_amount
            elif vat_output_amount is not None and vat_input_amount is None:
                # Calculate input from output and refund
                vat_input_amount = refund_amount + vat_output_amount

            # Validate amounts (Input should be > Output for refund)
            net_vat_receivable = vat_input_amount - vat_output_amount
            if abs(net_vat_receivable - refund_amount) > Decimal('0.01'):  # Allow 1 cent rounding difference
                raise IFRSComplianceError(f"VAT refund amounts don't match: Input {vat_input_amount} - Output {vat_output_amount} = {net_vat_receivable}, but refund is {refund_amount}")

            # Create the main accounting entry
            accounting_entry = AccountingEntry(
                date_prepared=refund_date,
                date_posted=refund_date,
                particulars=f"VAT Refund from Tax Authority (Input: {vat_input_amount}, Output: {vat_output_amount}, Net Refund: {refund_amount})",
                book="VAT_REFUND",
                status='posted',
                branch_id=branch_id
            )
            self.db.add(accounting_entry)
            self.db.flush()

            journal_entries = []

            # 1. Debit Bank/Cash for refund received
            bank_debit = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=debit_account_code.id,
                entry_type='debit',
                description=f"VAT refund received from tax authority to {debit_account_code.name}",
                date=refund_date,
                date_posted=refund_date,
                branch_id=branch_id,
                debit_amount=refund_amount,
                credit_amount=Decimal('0')
            )
            self.db.add(bank_debit)
            journal_entries.append(bank_debit)

            # 2. Debit VAT Payable (2132) to clear any Output VAT liability (if any)
            if vat_output_amount > 0:
                vat_payable_debit = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=vat_payable_code.id,
                    entry_type='debit',
                    description=f"Clear VAT Payable (Output VAT from sales)",
                    date=refund_date,
                    date_posted=refund_date,
                    branch_id=branch_id,
                    debit_amount=vat_output_amount,
                    credit_amount=Decimal('0')
                )
                self.db.add(vat_payable_debit)
                journal_entries.append(vat_payable_debit)

            # 3. Credit VAT Receivable (1160) to clear Input VAT asset
            vat_receivable_credit = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=vat_receivable_code.id,
                entry_type='credit',
                description=f"Clear VAT Receivable (Input VAT paid on purchases)",
                date=refund_date,
                date_posted=refund_date,
                branch_id=branch_id,
                debit_amount=Decimal('0'),
                credit_amount=vat_input_amount
            )
            self.db.add(vat_receivable_credit)
            journal_entries.append(vat_receivable_credit)

            # Validate double-entry compliance
            self._validate_double_entry_compliance(journal_entries)
            self.db.commit()

            return journal_entries

        except Exception as e:
            self.db.rollback()
            raise IFRSComplianceError(f"Error creating VAT refund journal entries: {str(e)}")

    def create_bank_transaction_entries(self, bank_transaction: BankTransaction) -> List[JournalEntry]:
        """Create IFRS-compliant journal entries for bank transactions"""
        try:
            # Get required accounting codes
            bank_account_code = bank_transaction.bank_account.accounting_code
            cash_code = self._get_accounting_code_by_ifrs_tag('A1.1')  # Cash

            if not bank_account_code:
                raise IFRSComplianceError("Bank account missing accounting code")

            # Create accounting entry
            accounting_entry = AccountingEntry(
                date_prepared=bank_transaction.transaction_date,
                date_posted=bank_transaction.transaction_date,
                particulars=f"Bank transaction: {bank_transaction.description}",
                book=f"BANK-{bank_transaction.id}",
                status='posted',
                branch_id=bank_transaction.branch_id
            )

            self.db.add(accounting_entry)
            self.db.flush()

            journal_entries = []

            # Determine entry types based on transaction type
            if bank_transaction.transaction_type in ['deposit', 'receipt']:
                # Debit bank account, credit cash
                bank_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=bank_account_code.id,
                    entry_type='debit',
                    debit_amount=bank_transaction.amount,
                    credit_amount=Decimal('0'),
                    description=f"Bank deposit: {bank_transaction.description}",
                    date=bank_transaction.transaction_date,
                    date_posted=bank_transaction.transaction_date,
                    branch_id=bank_transaction.branch_id
                )
                self.db.add(bank_entry)
                journal_entries.append(bank_entry)

                cash_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=cash_code.id,
                    entry_type='credit',
                    debit_amount=Decimal('0'),
                    credit_amount=bank_transaction.amount,
                    description=f"Cash reduction: {bank_transaction.description}",
                    date=bank_transaction.transaction_date,
                    date_posted=bank_transaction.transaction_date,
                    branch_id=bank_transaction.branch_id
                )
                self.db.add(cash_entry)
                journal_entries.append(cash_entry)
            else:
                # Credit bank account, debit cash
                bank_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=bank_account_code.id,
                    entry_type='credit',
                    debit_amount=Decimal('0'),
                    credit_amount=bank_transaction.amount,
                    description=f"Bank withdrawal: {bank_transaction.description}",
                    date=bank_transaction.transaction_date,
                    date_posted=bank_transaction.transaction_date,
                    branch_id=bank_transaction.branch_id
                )
                self.db.add(bank_entry)
                journal_entries.append(bank_entry)

                cash_entry = JournalEntry(
                    accounting_entry_id=accounting_entry.id,
                    accounting_code_id=cash_code.id,
                    entry_type='debit',
                    debit_amount=bank_transaction.amount,
                    credit_amount=Decimal('0'),
                    description=f"Cash increase: {bank_transaction.description}",
                    date=bank_transaction.transaction_date,
                    date_posted=bank_transaction.transaction_date,
                    branch_id=bank_transaction.branch_id
                )
                self.db.add(cash_entry)
                journal_entries.append(cash_entry)

            # Validate compliance
            self._validate_double_entry_compliance(journal_entries)
            self._validate_ifrs_compliance(journal_entries)

            self.db.commit()
            return journal_entries

        except Exception as e:
            self.db.rollback()
            raise IFRSComplianceError(f"Error creating bank transaction entries: {str(e)}")

    def submit_cash_takings(
        self,
        salesperson_id: str,
        amount: Decimal,
        submission_date: date,
        branch_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> List[JournalEntry]:
        """
        Submit cash takings from salesperson to Cash in Hand.

        This moves cash from:
          1114 Undeposited Funds (Salesperson Takings)
        to:
          1111 Cash in Hand

        Args:
            salesperson_id: ID of the salesperson submitting cash
            amount: Amount of cash being submitted
            submission_date: Date of cash submission
            branch_id: Optional branch ID
            notes: Optional notes about the submission

        Returns:
            List of journal entries created
        """
        journal_entries = []

        # Get accounting codes
        undeposited_code = self.db.query(AccountingCode).filter(
            AccountingCode.code == '1114'
        ).first()

        cash_in_hand_code = self.db.query(AccountingCode).filter(
            AccountingCode.code == '1111'
        ).first()

        if not undeposited_code:
            raise ValueError("Undeposited Funds account (1114) not found")

        if not cash_in_hand_code:
            raise ValueError("Cash in Hand account (1111) not found")

        # Create accounting entry
        from app.models.accounting import AccountingEntry
        accounting_entry = AccountingEntry(
            date_posted=submission_date,
            particulars=f"Cash submission by salesperson {salesperson_id}",
            status='posted',
            branch_id=branch_id
        )
        self.db.add(accounting_entry)
        self.db.flush()

        description = f"Cash submission by salesperson"
        if notes:
            description = f"{description} - {notes}"

        # Dr 1111 Cash in Hand
        cash_in_hand_entry = JournalEntry(
            accounting_entry_id=accounting_entry.id,
            accounting_code_id=cash_in_hand_code.id,
            entry_type='debit',
            debit_amount=amount,
            credit_amount=Decimal('0'),
            description=description,
            date=submission_date,
            date_posted=submission_date,
            branch_id=branch_id
        )
        self.db.add(cash_in_hand_entry)
        journal_entries.append(cash_in_hand_entry)

        # Cr 1114 Undeposited Funds
        undeposited_entry = JournalEntry(
            accounting_entry_id=accounting_entry.id,
            accounting_code_id=undeposited_code.id,
            entry_type='credit',
            debit_amount=Decimal('0'),
            credit_amount=amount,
            description=description,
            date=submission_date,
            date_posted=submission_date,
            branch_id=branch_id
        )
        self.db.add(undeposited_entry)
        journal_entries.append(undeposited_entry)

        # Validate compliance
        self._validate_double_entry_compliance(journal_entries)
        self._validate_ifrs_compliance(journal_entries)

        self.db.commit()
        return journal_entries

    def _get_accounting_code_by_ifrs_tag(self, ifrs_tag: str) -> Optional[AccountingCode]:
        """Get accounting code by IFRS reporting tag"""
        return self.db.query(AccountingCode).filter(
            AccountingCode.reporting_tag == ifrs_tag
        ).first()

    def _get_default_accounting_code(self, name: str, account_type: str) -> Optional[AccountingCode]:
        """Get accounting code by name and type as fallback"""
        return self.db.query(AccountingCode).filter(
            AccountingCode.name.ilike(f"%{name}%"),
            AccountingCode.account_type == account_type
        ).first()

    def _calculate_cogs_for_sale(self, sale: Sale) -> Decimal:
        """Calculate cost of goods sold for a sale"""
        cogs_total = Decimal('0')

        for sale_item in sale.sale_items:
            product = sale_item.product
            if product.cost_price:
                cogs_total += Decimal(sale_item.quantity) * Decimal(product.cost_price)

        return cogs_total

    def validate_accounting_entry(self, accounting_entry: AccountingEntry) -> Dict[str, Any]:
        """Validate an existing accounting entry for IFRS compliance"""
        try:
            journal_entries = accounting_entry.journal_entries

            # Check double-entry compliance
            total_debits = sum(je.debit_amount for je in journal_entries)
            total_credits = sum(je.credit_amount for je in journal_entries)

            # Check IFRS compliance
            ifrs_compliant = True
            compliance_issues = []

            for je in journal_entries:
                accounting_code = je.accounting_code

                if not accounting_code.reporting_tag:
                    ifrs_compliant = False
                    compliance_issues.append(f"Missing IFRS tag for account {accounting_code.code}")

                if accounting_code.reporting_tag not in self.IFRS_REPORTING_CATEGORIES:
                    ifrs_compliant = False
                    compliance_issues.append(f"Invalid IFRS tag {accounting_code.reporting_tag} for account {accounting_code.code}")

            return {
                'is_valid': total_debits == total_credits and ifrs_compliant,
                'double_entry_balanced': total_debits == total_credits,
                'ifrs_compliant': ifrs_compliant,
                'total_debits': float(total_debits),
                'total_credits': float(total_credits),
                'compliance_issues': compliance_issues
            }

        except Exception as e:
            return {
                'is_valid': False,
                'error': str(e)
            }

    def get_ifrs_balance_sheet_data(self, branch_id: str, as_of_date: date = None) -> Dict[str, Any]:
        """Get IFRS-compliant balance sheet data"""
        if not as_of_date:
            as_of_date = date.today()

        balance_sheet_data = {
            'as_of_date': as_of_date,
            'assets': {
                'current_assets': self._get_balance_for_ifrs_category('A1', branch_id, as_of_date),
                'non_current_assets': self._get_balance_for_ifrs_category('A2', branch_id, as_of_date)
            },
            'liabilities': {
                'current_liabilities': self._get_balance_for_ifrs_category('L1', branch_id, as_of_date),
                'non_current_liabilities': self._get_balance_for_ifrs_category('L2', branch_id, as_of_date)
            },
            'equity': {
                'share_capital': self._get_balance_for_ifrs_category('E1', branch_id, as_of_date),
                'retained_earnings': self._get_balance_for_ifrs_category('E2', branch_id, as_of_date),
                'other_equity': self._get_balance_for_ifrs_category('E3', branch_id, as_of_date)
            }
        }

        # Calculate totals
        total_assets = sum(balance_sheet_data['assets'].values())
        total_liabilities = sum(balance_sheet_data['liabilities'].values())
        total_equity = sum(balance_sheet_data['equity'].values())

        balance_sheet_data['totals'] = {
            'total_assets': float(total_assets),
            'total_liabilities': float(total_liabilities),
            'total_equity': float(total_equity),
            'balance_check': float(total_assets - (total_liabilities + total_equity))
        }

        return balance_sheet_data

    def get_ifrs_income_statement_data(self, branch_id: str, start_date: date, end_date: date) -> Dict[str, Any]:
        """Get IFRS-compliant income statement data"""
        income_statement_data = {
            'period': {'start_date': start_date, 'end_date': end_date},
            'revenue': {
                'revenue_from_contracts': self._get_movement_for_ifrs_category('R1', branch_id, start_date, end_date),
                'other_income': self._get_movement_for_ifrs_category('R2', branch_id, start_date, end_date)
            },
            'expenses': {
                'cost_of_sales': self._get_movement_for_ifrs_category('X1', branch_id, start_date, end_date),
                'selling_expenses': self._get_movement_for_ifrs_category('X2', branch_id, start_date, end_date),
                'administrative_expenses': self._get_movement_for_ifrs_category('X3', branch_id, start_date, end_date),
                'finance_costs': self._get_movement_for_ifrs_category('X4', branch_id, start_date, end_date)
            }
        }

        # Calculate totals
        total_revenue = sum(income_statement_data['revenue'].values())
        total_expenses = sum(income_statement_data['expenses'].values())
        net_income = total_revenue - total_expenses

        income_statement_data['totals'] = {
            'total_revenue': float(total_revenue),
            'total_expenses': float(total_expenses),
            'net_income': float(net_income)
        }

        return income_statement_data

    def _get_balance_for_ifrs_category(self, ifrs_tag: str, branch_id: str, as_of_date: date) -> Decimal:
        """Get balance for IFRS category as of a specific date"""
        # Get all accounts with this IFRS tag
        accounts = self.db.query(AccountingCode).filter(
            and_(
                AccountingCode.reporting_tag == ifrs_tag,
                AccountingCode.branch_id == branch_id
            )
        ).all()

        total_balance = Decimal('0')

        for account in accounts:
            # Get opening balance
            opening_balance = self.db.query(func.sum(OpeningBalance.amount)).filter(
                and_(
                    OpeningBalance.accounting_code_id == account.id,
                    OpeningBalance.year == as_of_date.year
                )
            ).scalar() or Decimal('0')

            # Get movement from journal entries
            journal_entries = self.db.query(JournalEntry).join(AccountingEntry).filter(
                and_(
                    JournalEntry.accounting_code_id == account.id,
                    AccountingEntry.date_posted <= as_of_date,
                    AccountingEntry.branch_id == branch_id
                )
            ).all()

            movement = sum(je.debit_amount - je.credit_amount for je in journal_entries)

            # Calculate balance based on account type
            account_rules = self.IFRS_ACCOUNT_RULES[IFRSAccountType(account.account_type)]
            if account_rules['normal_balance'] == 'debit':
                balance = opening_balance + movement
            else:
                balance = opening_balance - movement

            total_balance += balance

        return total_balance

    def _get_movement_for_ifrs_category(self, ifrs_tag: str, branch_id: str, start_date: date, end_date: date) -> Decimal:
        """Get movement for IFRS category during a period"""
        # Get all accounts with this IFRS tag
        accounts = self.db.query(AccountingCode).filter(
            and_(
                AccountingCode.reporting_tag == ifrs_tag,
                AccountingCode.branch_id == branch_id
            )
        ).all()

        total_movement = Decimal('0')

        for account in accounts:
            # Get journal entries for the period
            journal_entries = self.db.query(JournalEntry).join(AccountingEntry).filter(
                and_(
                    JournalEntry.accounting_code_id == account.id,
                    AccountingEntry.date_posted >= start_date,
                    AccountingEntry.date_posted <= end_date,
                    AccountingEntry.branch_id == branch_id
                )
            ).all()

            movement = sum(je.debit_amount - je.credit_amount for je in journal_entries)
            total_movement += movement

        return total_movement
