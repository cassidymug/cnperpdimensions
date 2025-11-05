"""
IFRS Compliant Reporting Service - Core Module
Comprehensive service for generating IFRS-compliant financial reports
"""

from typing import Dict, List, Optional, Any, Tuple
import os, json
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, text, and_, or_
from app.models.accounting import AccountingCode, JournalEntry, AccountingEntry
from app.models.sales import Sale, Customer
from app.models.purchases import Purchase, Supplier
from app.models.inventory import Product, InventoryTransaction

class IFRSReportsCore:
    """Core IFRS reporting functionality"""

    def __init__(self, db: Session):
        self.db = db
        self._load_ifrs_mapping()

    def _load_ifrs_mapping(self):
        """Load IFRS mapping configuration for strict categorization"""
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'ifrs_mapping.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.ifrs_config = json.load(f)
            else:
                self.ifrs_config = {}
        except Exception as e:
            print(f"Warning: Could not load IFRS mapping config: {e}")
            self.ifrs_config = {}

    def get_account_balance_as_of_date(self, account_id: str, as_of_date: date) -> Dict:
        """Get account balance as of specific date with IFRS compliance"""

        total_debits = Decimal('0.00')
        total_credits = Decimal('0.00')

        try:
            # Query journal entries directly - they contain the debit/credit amounts
            journal_entries = self.db.query(JournalEntry).filter(
                JournalEntry.accounting_code_id == account_id,
                JournalEntry.date <= as_of_date
            ).all()

            print(f"Found {len(journal_entries)} journal entries for account {account_id}")

            total_debits = sum(Decimal(str(entry.debit_amount or 0)) for entry in journal_entries)
            total_credits = sum(Decimal(str(entry.credit_amount or 0)) for entry in journal_entries)

            print(f"Account {account_id}: Debits={total_debits}, Credits={total_credits}")

        except Exception as e:
            # If there are issues with entries, use zero balances
            # This could be due to missing tables, no data, or schema issues
            print(f"Warning: Could not retrieve journal entries for account {account_id}: {str(e)}")
            pass

        account = self.db.query(AccountingCode).filter(AccountingCode.id == account_id).first()
        # Normalize account type to handle case differences (e.g., 'Asset' vs 'ASSET')
        account_type = getattr(account, 'account_type', 'Asset') or 'Asset'
        atype = str(account_type).strip().lower()
        if atype in ['asset', 'expense']:
            balance = total_debits - total_credits
        else:  # liability, equity, revenue
            balance = total_credits - total_debits

        return {
            'balance': balance,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'account_type': account_type,
            'category': getattr(account, 'category', 'Other')
        }

    def get_trial_balance_data(
        self,
        as_of_date: date = None,
        include_zero_balances: bool = False,
        account_type_filter: str = None
    ) -> Dict:
        """Generate IFRS-compliant trial balance data"""
        if as_of_date is None:
            as_of_date = date.today()

        trial_balance_items: List[Dict] = []
        total_debits = Decimal('0.00')
        total_credits = Decimal('0.00')

        try:
            total_journal_entries = self.db.query(JournalEntry).count()
            print(f"Found {total_journal_entries} total journal entries in database")

            query = self.db.query(AccountingCode)
            if account_type_filter:
                try:
                    query = query.filter(AccountingCode.account_type == account_type_filter)
                except Exception:
                    pass

            # DO NOT limit accounts - trial balance must include ALL accounts
            accounts = query.all()
            print(f"Found {len(accounts)} accounting codes in database")

            if not accounts:
                print("No accounting codes found in database. Returning empty trial balance.")
                return {
                    'success': True,
                    'data': {
                        'as_of_date': as_of_date.isoformat(),
                        'items': [],
                        'totals': {
                            'total_debits': 0.0,
                            'total_credits': 0.0,
                            'difference': 0.0
                        },
                        'is_balanced': True,
                        'compliant': True,
                        'message': 'No accounting codes found. Please initialize the chart of accounts.'
                    }
                }

            for account in accounts:
                try:
                    balance_info = self.get_account_balance_as_of_date(account.id, as_of_date)

                    if not include_zero_balances and balance_info['balance'] == 0:
                        continue

                    # For trial balance, we use total debits and credits from all transactions
                    # not the net balance (which would be debit - credit)
                    account_total_debits = balance_info['total_debits']
                    account_total_credits = balance_info['total_credits']

                    trial_balance_items.append({
                        'account_code': getattr(account, 'code', f'ACC-{account.id}'),
                        'account_name': getattr(account, 'name', 'Unknown Account'),
                        'account_type': getattr(account, 'account_type', 'UNKNOWN'),
                        'category': getattr(account, 'category', 'Other'),
                        'reporting_tag': getattr(account, 'reporting_tag', ''),
                        'debit_balance': float(account_total_debits),
                        'credit_balance': float(account_total_credits),
                        'balance': float(balance_info['balance']),
                        'total_debits': float(balance_info['total_debits']),
                        'total_credits': float(balance_info['total_credits'])
                    })

                    total_debits += account_total_debits
                    total_credits += account_total_credits
                except Exception:
                    continue
        except Exception:
            pass

        is_balanced = total_debits == total_credits
        variance = total_debits - total_credits

        return {
            'as_of_date': as_of_date,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'is_balanced': is_balanced,
            'variance': variance,
            'accounts': trial_balance_items,
            'ifrs_compliance': {
                'standard': 'IAS 1 - Presentation of Financial Statements',
                'compliant': is_balanced and all(item['category'] for item in trial_balance_items),
                'notes': 'Trial balance includes account category classifications'
            }
        }

    def _classify_ifrs_section(self, account: AccountingCode) -> str:
        """Classify an account into an IFRS balance sheet section.
        Returns one of: CURRENT_ASSET, NON_CURRENT_ASSET, CURRENT_LIABILITY, NON_CURRENT_LIABILITY, EQUITY

        Classification priority:
        1. reporting_tag (A1.x = Current Asset, A2.x = Non-Current Asset, L1.x = Current Liability, L2.x = Non-Current Liability, E1 = Equity)
        2. account_overrides in config (by code)
        3. Keyword matching (fallback)
        """
        acct_type = (getattr(account, 'account_type', '') or '').strip()
        acct_type_l = acct_type.lower()
        cat = (getattr(account, 'category', '') or '').strip()
        name = (getattr(account, 'name', '') or '').strip()
        s = f"{cat} {name}".lower()

        # PRIORITY 1: Use reporting_tag to determine IFRS section (most reliable)
        tag = (getattr(account, 'reporting_tag', '') or '').strip()
        if tag:
            # A1.x = Current Assets, A2.x = Non-Current Assets
            # L1.x = Current Liabilities, L2.x = Non-Current Liabilities
            # E1 = Equity
            if tag.startswith('A1.') or tag == 'A1':
                return 'CURRENT_ASSET'
            elif tag.startswith('A2.') or tag == 'A2':
                return 'NON_CURRENT_ASSET'
            elif tag.startswith('L1.') or tag == 'L1':
                return 'CURRENT_LIABILITY'
            elif tag.startswith('L2.') or tag == 'L2':
                return 'NON_CURRENT_LIABILITY'
            elif tag.startswith('E') or tag == 'E1':
                return 'EQUITY'

        # PRIORITY 2: Mapping overrides by account code (from IFRS config)
        try:
            code = getattr(account, 'code', None)
            if code and isinstance(self.ifrs_config.get('account_overrides', {}), dict):
                override = self.ifrs_config['account_overrides'].get(code)
                if isinstance(override, dict) and 'section' in override:
                    sec = override['section']
                    if sec in ('CURRENT_ASSET','NON_CURRENT_ASSET','CURRENT_LIABILITY','NON_CURRENT_LIABILITY','EQUITY'):
                        return sec
        except Exception:
            pass

        # PRIORITY 3: Fallback to keyword matching (least reliable)
        if acct_type_l == 'equity':
            return 'EQUITY'

        if acct_type_l == 'asset':
            current_kw = ['current', 'cash', 'bank', 'receivable', 'trade receivable', 'inventory', 'prepaid', 'pre-payment', 'investment', 'deposits', 'advance']
            non_current_kw = ['non-current', 'non current', 'long-term', 'long term', 'fixed asset', 'property', 'plant', 'equipment', 'ppe', 'intangible', 'accumulated depreciation', 'depreciation']
            if any(k in s for k in current_kw):
                return 'CURRENT_ASSET'
            if any(k in s for k in non_current_kw):
                return 'NON_CURRENT_ASSET'
            if cat in ['Current Asset', 'Cash', 'Bank', 'Trade Receivables', 'Prepaid Expenses', 'Inventory', 'Investments']:
                return 'CURRENT_ASSET'
            if cat in ['Fixed Asset', 'Intangible Assets', 'Accumulated Depreciation']:
                return 'NON_CURRENT_ASSET'
            return 'CURRENT_ASSET'

        if acct_type_l == 'liability':
            current_kw = ['current', 'trade payable', 'payable', 'accrued', 'vat', 'tax', 'deferred revenue', 'notes payable', 'current portion', 'short-term']
            non_current_kw = ['non-current', 'non current', 'long-term', 'long term', 'loan', 'bond', 'debenture']
            if any(k in s for k in current_kw):
                return 'CURRENT_LIABILITY'
            if any(k in s for k in non_current_kw):
                return 'NON_CURRENT_LIABILITY'
            if cat in ['Current Liability', 'Trade Payables', 'Accrued Liabilities', 'VAT Payable', 'Tax Payable', 'Deferred Revenue', 'Notes Payable']:
                return 'CURRENT_LIABILITY'
            if cat in ['Long-Term Liability', 'Loans Payable']:
                return 'NON_CURRENT_LIABILITY'
            return 'CURRENT_LIABILITY'

        return ''



    def get_balance_sheet_section(self, ifrs_category: str, as_of_date: date, detail_level: str = 'summary') -> List[Dict]:
        """Get balance sheet section items by IFRS category using robust classification.
        Adds strict rules:
        - Retained earnings remains a distinct line in Equity.
        - Loans are split to current vs non-current based on maturity if available (fallback by name keywords).
        """
        try:
            if ifrs_category in ('CURRENT_ASSET', 'NON_CURRENT_ASSET'):
                account_type = 'Asset'
            elif ifrs_category in ('CURRENT_LIABILITY', 'NON_CURRENT_LIABILITY'):
                account_type = 'Liability'
            elif ifrs_category == 'EQUITY':
                account_type = 'Equity'
            else:
                return []

            # Case-insensitive filter for account type to be robust
            from sqlalchemy import func
            accounts = self.db.query(AccountingCode).filter(
                func.lower(AccountingCode.account_type) == account_type.lower()
            ).all()
        except Exception:
            return []

        section_items: List[Dict] = []
        for account in accounts:
            try:
                bucket = self._classify_ifrs_section(account)
                if bucket != ifrs_category:
                    continue
                balance_info = self.get_account_balance_as_of_date(account.id, as_of_date)
                if balance_info['balance'] == 0 and detail_level == 'summary':
                    continue

                line_item = getattr(account, 'name', 'Unknown Account')

                # Apply IFRS mapping for line item names
                code = getattr(account, 'code', '')
                cat = getattr(account, 'category', '')

                if code and 'account_overrides' in self.ifrs_config:
                    override = self.ifrs_config['account_overrides'].get(code, {})
                    line_item = override.get('line_item', line_item)
                elif cat and 'category_mapping' in self.ifrs_config:
                    mapping = self.ifrs_config['category_mapping'].get(cat, {})
                    line_item = mapping.get('line_item', line_item)

                # Special handling for retained earnings
                if ifrs_category == 'EQUITY':
                    name_lower = getattr(account, 'name', '').lower()
                    cat_lower = cat.lower()
                    if 'retained' in name_lower or 'retained' in cat_lower:
                        line_item = 'Retained Earnings'
                    elif 'share' in name_lower or 'capital' in name_lower or 'stock' in name_lower:
                        line_item = 'Share Capital'

                # Use signed balance: assets should show positive for debit balances
                # and negative for credit balances. Converting to absolute values
                # inflates totals when negative balances exist (turns negatives
                # into positives). Use the raw signed balance returned by
                # get_account_balance_as_of_date().
                section_items.append({
                    'account_code': getattr(account, 'code', f'ACC-{account.id}'),
                    'account_name': line_item,
                    'amount': float(balance_info['balance']),
                    'reporting_tag': getattr(account, 'reporting_tag', ''),
                    'account_type': getattr(account, 'account_type', ''),
                    'category': getattr(account, 'category', '')
                })
            except Exception:
                continue

        # Debug: Log section population for troubleshooting
        if not section_items:
            print(f"Info: No items found for IFRS section {ifrs_category} with {len(accounts)} accounts of type {account_type}")
        else:
            print(f"Success: Found {len(section_items)} items for IFRS section {ifrs_category}")

        # DO NOT use fallback logic - rely on reporting_tag classification
        # Previously, fallback logic added ALL accounts to empty sections, causing double-counting
        # Now that all active accounts have proper reporting_tags, we can trust the classification

        return section_items

    def get_balance_sheet_data(
        self,
        as_of_date: date = None,
        comparison_date: date = None,
        detail_level: str = 'summary'
    ) -> Dict:
        """Generate IFRS-compliant balance sheet data"""

        if as_of_date is None:
            as_of_date = date.today()

        # Assets
        current_assets = self.get_balance_sheet_section('CURRENT_ASSET', as_of_date, detail_level)
        non_current_assets = self.get_balance_sheet_section('NON_CURRENT_ASSET', as_of_date, detail_level)

        # Liabilities
        current_liabilities = self.get_balance_sheet_section('CURRENT_LIABILITY', as_of_date, detail_level)
        non_current_liabilities = self.get_balance_sheet_section('NON_CURRENT_LIABILITY', as_of_date, detail_level)

        # Equity
        equity = self.get_balance_sheet_section('EQUITY', as_of_date, detail_level)

        # Calculate Net Income (Revenue - Expense) and add to Equity as Retained Earnings
        # This is essential for the Balance Sheet to balance: Assets = Liabilities + Equity + Net Income
        from sqlalchemy import text, func
        revenue_balance = self.db.execute(
            text("""
                SELECT COALESCE(SUM(je.credit_amount - je.debit_amount), 0) as net_revenue
                FROM journal_entries je
                JOIN accounting_codes ac ON je.accounting_code_id = ac.id
                WHERE LOWER(ac.account_type) = 'revenue'
                AND je.date <= :as_of_date
            """),
            {"as_of_date": as_of_date}
        ).scalar() or 0

        expense_balance = self.db.execute(
            text("""
                SELECT COALESCE(SUM(je.debit_amount - je.credit_amount), 0) as net_expense
                FROM journal_entries je
                JOIN accounting_codes ac ON je.accounting_code_id = ac.id
                WHERE LOWER(ac.account_type) = 'expense'
                AND je.date <= :as_of_date
            """),
            {"as_of_date": as_of_date}
        ).scalar() or 0

        net_income = float(revenue_balance) - float(expense_balance)

        # Add Net Income to equity section
        if net_income != 0:
            equity.append({
                'account_code': 'RETAINED',
                'account_name': 'Retained Earnings (Current Period Net Income)',
                'amount': float(net_income),
                'reporting_tag': '',
                'account_type': 'Equity',
                'category': 'Retained Earnings'
            })

        # Calculate totals
        total_current_assets = sum(item['amount'] for item in current_assets)
        total_non_current_assets = sum(item['amount'] for item in non_current_assets)
        total_assets = total_current_assets + total_non_current_assets

        total_current_liabilities = sum(item['amount'] for item in current_liabilities)
        total_non_current_liabilities = sum(item['amount'] for item in non_current_liabilities)
        total_liabilities = total_current_liabilities + total_non_current_liabilities

        total_equity = sum(item['amount'] for item in equity)

        print(f"Balance Sheet Totals - Assets: {total_assets}, Liabilities: {total_liabilities}, Equity: {total_equity}")

        # IFRS Balance Check
        balance_check = total_assets == (total_liabilities + total_equity)
        variance = total_assets - (total_liabilities + total_equity)

        if not balance_check:
            print(f"WARNING: Balance sheet does not balance: Assets {total_assets} != Liabilities + Equity {total_liabilities + total_equity} (variance: {variance})")
        else:
            print(f"SUCCESS: Balance sheet is balanced: Assets {total_assets} = Liabilities + Equity {total_liabilities + total_equity}")

        return {
            'as_of_date': as_of_date,
            'comparison_date': comparison_date,
            'assets': {
                'current_assets': current_assets,
                'non_current_assets': non_current_assets,
                'total_current_assets': total_current_assets,
                'total_non_current_assets': total_non_current_assets,
                'total_assets': total_assets
            },
            'liabilities': {
                'current_liabilities': current_liabilities,
                'non_current_liabilities': non_current_liabilities,
                'total_current_liabilities': total_current_liabilities,
                'total_non_current_liabilities': total_non_current_liabilities,
                'total_liabilities': total_liabilities
            },
            'equity': equity,  # Frontend expects this to be an array directly
            'totals': {
                'total_assets': total_assets,
                'total_liabilities': total_liabilities,
                'total_equity': total_equity
            },
            'balance_check': {
                'is_balanced': balance_check,
                'variance': variance,
                'formula': 'Assets = Liabilities + Equity'
            },
            'ifrs_compliance': {
                'standard': 'IAS 1 - Presentation of Financial Statements',
                'compliant': balance_check,
                'current_ratio': total_current_assets / total_current_liabilities if total_current_liabilities > 0 else None,
                'debt_to_equity': total_liabilities / total_equity if total_equity > 0 else None
            }
        }

    def calculate_expected_credit_loss(self, aging_buckets: Dict) -> Dict:
        """Calculate Expected Credit Loss per IFRS 9"""

        # Simplified ECL calculation based on aging
        ecl_rates = {
            '0-30': 0.01,    # 1%
            '31-60': 0.03,   # 3%
            '61-90': 0.05,   # 5%
            '91-120': 0.10,  # 10%
            '120+': 0.25     # 25%
        }

        total_provision = Decimal('0.00')
        bucket_provisions = {}

        for bucket, items in aging_buckets.items():
            bucket_total = sum(item['outstanding_amount'] for item in items)
            provision = bucket_total * Decimal(str(ecl_rates[bucket]))
            bucket_provisions[bucket] = provision
            total_provision += provision

        total_outstanding = sum(sum(item['outstanding_amount'] for item in items)
                              for items in aging_buckets.values())

        provision_rate = (total_provision / total_outstanding) if total_outstanding > 0 else Decimal('0.00')

        return {
            'total_provision': total_provision,
            'provision_rate': provision_rate,
            'bucket_provisions': bucket_provisions,
            'method': 'Simplified approach for trade receivables',
            'ifrs_standard': 'IFRS 9 - Financial Instruments'
        }
