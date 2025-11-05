from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from enum import Enum
import json

from app.models.accounting import (
    AccountingCode, AccountingEntry, JournalEntry, 
    Ledger, OpeningBalance, AccountType, NormalBalance
)
from app.models.accounting_constants import get_normal_balance
from app.models.branch import Branch
from app.services.ifrs_accounting_service import IFRSAccountingService
from app.core.config import settings


class LedgerPeriod(Enum):
    """Period options for ledger reports"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class GeneralLedgerService:
    """
    IFRS-compliant General Ledger Service
    
    Provides comprehensive general ledger functionality including:
    - Account hierarchies and balances
    - Trial balance calculations
    - Period-specific reporting
    - Running balance calculations
    - IFRS compliance validation
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.ifrs_service = IFRSAccountingService(db)
    
    def get_chart_of_accounts(self, branch_id: Optional[str] = None, 
                             include_inactive: bool = False) -> List[Dict[str, Any]]:
        """
        Get complete chart of accounts with hierarchical structure
        
        Args:
            branch_id: Optional branch filter
            include_inactive: Include inactive accounts
            
        Returns:
            List of account dictionaries with hierarchy
        """
        try:
            # Test basic database connectivity first
            total_accounts = self.db.query(AccountingCode).count()
            print(f"Total accounts in database: {total_accounts}")

            query = self.db.query(AccountingCode).options(
                joinedload(AccountingCode.children),
                joinedload(AccountingCode.parent)
            )

            if branch_id:
                query = query.filter(AccountingCode.branch_id == branch_id)

            # if not include_inactive:
            #     query = query.filter(AccountingCode.is_active == True)

            accounts = query.order_by(AccountingCode.code).all()
            print(f"Filtered accounts found: {len(accounts)}")

            if not accounts:
                print("No accounts found with current filters")
                return []

            # Build hierarchical structure
            account_dict = {account.id: self._format_account_data(account) for account in accounts}
            root_accounts = []

            for account_id, account_data in account_dict.items():
                parent_id = account_data.get('parent_id')
                if parent_id and parent_id in account_dict:
                    if 'children' not in account_dict[parent_id]:
                        account_dict[parent_id]['children'] = []
                    account_dict[parent_id]['children'].append(account_data)
                elif not parent_id:
                    root_accounts.append(account_data)

            print(f"Returning {len(root_accounts)} root accounts")
            return root_accounts

        except Exception as e:
            print(f"Error getting chart of accounts: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            return []
    
    def get_general_ledger_entries(self, 
                                  account_id: Optional[str] = None,
                                  account_type: Optional[str] = None,
                                  from_date: Optional[date] = None,
                                  to_date: Optional[date] = None,
                                  branch_id: Optional[str] = None,
                                  search: Optional[str] = None,
                                  limit: int = 1000,
                                  offset: int = 0,
                                  account_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Get general ledger entries with IFRS-compliant running balances

        Args:
            account_id: Specific account filter (by ID)
            account_code: Specific account filter (by account code)
            account_type: Account type filter (Asset, Liability, etc.)
            from_date: Start date filter
            to_date: End date filter
            branch_id: Branch filter
            search: Text search filter
            limit: Maximum entries to return
            offset: Pagination offset

        Returns:
            Dictionary with entries and summary information
        """
        try:
            # Build base query
            query = self.db.query(JournalEntry).join(
                AccountingCode, JournalEntry.accounting_code_id == AccountingCode.id
            ).options(
                joinedload(JournalEntry.accounting_code),
                joinedload(JournalEntry.accounting_entry)
            )

            # Apply filters
            if account_id:
                query = query.filter(JournalEntry.accounting_code_id == account_id)

            # Allow filtering by account code for convenience (used by frontend)
            if account_code:
                query = query.filter(AccountingCode.code == account_code)

            # Account type filter (case-insensitive to accept values like 'asset')
            if account_type:
                try:
                    # Normalize to string and compare lower-cased
                    atype = str(account_type)
                    query = query.filter(func.lower(AccountingCode.account_type) == atype.lower())
                except Exception:
                    query = query.filter(AccountingCode.account_type == account_type)

            if from_date:
                query = query.filter(JournalEntry.date >= from_date)

            if to_date:
                query = query.filter(JournalEntry.date <= to_date)

            if branch_id:
                query = query.filter(JournalEntry.branch_id == branch_id)

            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        JournalEntry.description.ilike(search_term),
                        JournalEntry.narration.ilike(search_term),
                        JournalEntry.reference.ilike(search_term),
                        AccountingCode.name.ilike(search_term),
                        AccountingCode.code.ilike(search_term)
                    )
                )

            # Get total count
            total_count = query.count()

            # Order by date and get entries
            entries = query.order_by(
                JournalEntry.date.asc(),
                JournalEntry.id.asc()
            ).offset(offset).limit(limit).all()

            # Calculate running balances and format entries
            ledger_entries = self._calculate_running_balances(entries)

            # Calculate summary statistics
            summary = self._calculate_ledger_summary(entries)

            return {
                'entries': ledger_entries,
                'total_count': total_count,
                'summary': summary,
                'filters': {
                    'account_id': account_id,
                    'account_code': account_code,
                    'account_type': account_type,
                    'from_date': from_date.isoformat() if from_date else None,
                    'to_date': to_date.isoformat() if to_date else None,
                    'branch_id': branch_id,
                    'search': search
                }
            }
            
        except Exception as e:
            print(f"Error getting general ledger entries: {e}")
            return {
                'entries': [],
                'total_count': 0,
                'summary': {},
                'error': str(e)
            }
    
    def get_trial_balance(self, 
                         as_of_date: Optional[date] = None,
                         branch_id: Optional[str] = None,
                         include_zero_balances: bool = False) -> Dict[str, Any]:
        """
        Generate IFRS-compliant trial balance
        
        Args:
            as_of_date: Date for trial balance (defaults to today)
            branch_id: Branch filter
            include_zero_balances: Include accounts with zero balances
            
        Returns:
            Dictionary with trial balance data
        """
        try:
            if not as_of_date:
                as_of_date = date.today()
            
            # Get all accounts
            query = self.db.query(AccountingCode)
            if branch_id:
                query = query.filter(AccountingCode.branch_id == branch_id)
            
            accounts = query.all()
            
            trial_balance_entries = []
            total_debits = Decimal('0')
            total_credits = Decimal('0')
            
            for account in accounts:
                balance_info = self._get_account_balance_as_of_date(account.id, as_of_date)
                
                if not include_zero_balances and balance_info['balance'] == 0:
                    continue
                
                # Determine debit/credit presentation based on normal balance
                debit_balance = Decimal('0')
                credit_balance = Decimal('0')
                
                normal_balance = get_normal_balance(account.account_type)
                if normal_balance == NormalBalance.DEBIT.value:
                    if balance_info['balance'] >= 0:
                        debit_balance = balance_info['balance']
                    else:
                        credit_balance = abs(balance_info['balance'])
                else:
                    if balance_info['balance'] >= 0:
                        credit_balance = balance_info['balance']
                    else:
                        debit_balance = abs(balance_info['balance'])
                
                total_debits += debit_balance
                total_credits += credit_balance
                
                trial_balance_entries.append({
                    'account_id': account.id,
                    'account_code': account.code,
                    'account_name': account.name,
                    'account_type': account.account_type if account.account_type else None,
                    'category': account.category,
                    'debit_balance': float(debit_balance),
                    'credit_balance': float(credit_balance),
                    'net_balance': float(balance_info['balance']),
                    'normal_balance': normal_balance,
                    'is_parent': account.is_parent,
                    'parent_code': account.parent.code if account.parent else None
                })
            
            # Sort by account code
            trial_balance_entries.sort(key=lambda x: x['account_code'])
            
            return {
                'trial_balance': trial_balance_entries,
                'totals': {
                    'total_debits': float(total_debits),
                    'total_credits': float(total_credits),
                    'difference': float(total_debits - total_credits),
                    'is_balanced': total_debits == total_credits
                },
                'as_of_date': as_of_date.isoformat(),
                'branch_id': branch_id,
                'account_count': len(trial_balance_entries)
            }
            
        except Exception as e:
            print(f"Error generating trial balance: {e}")
            return {
                'trial_balance': [],
                'totals': {
                    'total_debits': 0,
                    'total_credits': 0,
                    'difference': 0,
                    'is_balanced': False
                },
                'error': str(e)
            }
    
    def get_account_ledger(self, account_id: str,
                          from_date: Optional[date] = None,
                          to_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Get detailed ledger for a specific account
        
        Args:
            account_id: Account ID
            from_date: Start date
            to_date: End date
            
        Returns:
            Dictionary with account ledger details
        """
        try:
            # Get account information
            account = self.db.query(AccountingCode).filter(
                AccountingCode.id == account_id
            ).first()
            
            if not account:
                return {'error': 'Account not found'}
            
            # Get opening balance as of the start of the requested period
            opening_balance = self._get_opening_balance_for_period(account_id, from_date)
            
            # Get journal entries
            query = self.db.query(JournalEntry).filter(
                JournalEntry.accounting_code_id == account_id
            ).options(
                joinedload(JournalEntry.accounting_entry)
            )
            
            if from_date:
                query = query.filter(JournalEntry.date >= from_date)
            
            if to_date:
                query = query.filter(JournalEntry.date <= to_date)
            
            entries = query.order_by(
                JournalEntry.date.asc(),
                JournalEntry.id.asc()
            ).all()
            
            # Calculate running balance
            running_balance = opening_balance
            ledger_entries = []
            
            for entry in entries:
                # Apply entry based on normal balance
                normal_balance = get_normal_balance(account.account_type)
                if normal_balance == NormalBalance.DEBIT.value:
                    running_balance += (entry.debit_amount or Decimal('0'))
                    running_balance -= (entry.credit_amount or Decimal('0'))
                else:
                    running_balance += (entry.credit_amount or Decimal('0'))
                    running_balance -= (entry.debit_amount or Decimal('0'))
                
                ledger_entries.append({
                    'id': entry.id,
                    'date': entry.date.isoformat(),
                    'description': entry.description or entry.narration or '',
                    'reference': entry.reference or '',
                    'debit_amount': float(entry.debit_amount or 0),
                    'credit_amount': float(entry.credit_amount or 0),
                    'running_balance': float(running_balance),
                    'entry_type': entry.entry_type,
                    'accounting_entry_id': entry.accounting_entry_id,
                    'particulars': entry.accounting_entry.particulars if entry.accounting_entry else ''
                })
            
            return {
                'account': self._format_account_data(account),
                'opening_balance': float(opening_balance),
                'closing_balance': float(running_balance),
                'entries': ledger_entries,
                'entry_count': len(ledger_entries),
                'period': {
                    'from_date': from_date.isoformat() if from_date else None,
                    'to_date': to_date.isoformat() if to_date else None
                }
            }
            
        except Exception as e:
            print(f"Error getting account ledger: {e}")
            return {'error': str(e)}
    
    def get_balance_sheet_data(self, as_of_date: Optional[date] = None,
                              branch_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate balance sheet data organized by IFRS categories
        
        Args:
            as_of_date: Date for balance sheet
            branch_id: Branch filter
            
        Returns:
            Dictionary with balance sheet structure
        """
        try:
            if not as_of_date:
                as_of_date = date.today()
            
            # Get accounts by type
            assets = self._get_accounts_by_type(AccountType.ASSET, as_of_date, branch_id)
            liabilities = self._get_accounts_by_type(AccountType.LIABILITY, as_of_date, branch_id)
            equity = self._get_accounts_by_type(AccountType.EQUITY, as_of_date, branch_id)
            
            # Calculate totals
            total_assets = sum(acc['balance'] for acc in assets)
            total_liabilities = sum(acc['balance'] for acc in liabilities)
            total_equity = sum(acc['balance'] for acc in equity)
            
            return {
                'assets': {
                    'accounts': assets,
                    'total': total_assets
                },
                'liabilities': {
                    'accounts': liabilities,
                    'total': total_liabilities
                },
                'equity': {
                    'accounts': equity,
                    'total': total_equity
                },
                'totals': {
                    'total_assets': total_assets,
                    'total_liabilities_equity': total_liabilities + total_equity,
                    'is_balanced': abs(total_assets - (total_liabilities + total_equity)) < 0.01
                },
                'as_of_date': as_of_date.isoformat()
            }
            
        except Exception as e:
            print(f"Error generating balance sheet: {e}")
            return {'error': str(e)}
    
    def _format_account_data(self, account: AccountingCode) -> Dict[str, Any]:
        """Format account data for API response"""
        return {
            'id': account.id,
            'code': account.code,
            'name': account.name,
            'account_type': account.account_type if account.account_type else None,
            'category': account.category,
            'parent_id': account.parent_id,
            'is_parent': account.is_parent,
            'normal_balance': get_normal_balance(account.account_type),
            'balance': float(account.balance or 0),
            'total_debits': float(account.total_debits or 0),
            'total_credits': float(account.total_credits or 0),
            'currency': account.currency,
            'reporting_tag': account.reporting_tag,
            'description': getattr(account, 'description', None),
            'full_path': account.get_full_path() if hasattr(account, 'get_full_path') else f"{account.code} - {account.name}",
            'created_at': account.created_at.isoformat() if account.created_at else None,
            'updated_at': account.updated_at.isoformat() if account.updated_at else None
        }
    
    def _calculate_running_balances(self, entries: List[JournalEntry], from_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """Calculate running balances for journal entries (includes opening balances as of from_date if provided)"""
        ledger_entries = []
        account_balances: Dict[str, Dict[str, Any]] = {}

        for entry in entries:
            account_id = entry.accounting_code_id

            # Initialize account balance for this account (include opening balance for the period if provided)
            if account_id not in account_balances:
                opening = self._get_opening_balance_for_period(account_id, from_date) if from_date else Decimal('0')
                account_balances[account_id] = {
                    'balance': opening,
                    'account': entry.accounting_code
                }
            
            # Update balance based on normal balance type
            account = account_balances[account_id]['account']
            normal_balance = get_normal_balance(account.account_type)
            if normal_balance == NormalBalance.DEBIT.value:
                account_balances[account_id]['balance'] += (entry.debit_amount or Decimal('0'))
                account_balances[account_id]['balance'] -= (entry.credit_amount or Decimal('0'))
            else:
                account_balances[account_id]['balance'] += (entry.credit_amount or Decimal('0'))
                account_balances[account_id]['balance'] -= (entry.debit_amount or Decimal('0'))
            
            ledger_entries.append({
                'id': entry.id,
                'date': entry.date.isoformat(),
                'account_code': account.code,
                'account_name': account.name,
                'account_type': account.account_type if account.account_type else None,
                'description': entry.description or entry.narration or '',
                'reference': entry.reference or '',
                'debit_amount': float(entry.debit_amount or 0),
                'credit_amount': float(entry.credit_amount or 0),
                'running_balance': float(account_balances[account_id]['balance']),
                'entry_type': entry.entry_type,
                'origin': entry.origin,
                'accounting_entry_id': entry.accounting_entry_id,
                'particulars': entry.accounting_entry.particulars if entry.accounting_entry else ''
            })
        
        return ledger_entries
    
    def _calculate_ledger_summary(self, entries: List[JournalEntry]) -> Dict[str, Any]:
        """Calculate summary statistics for ledger entries"""
        total_debits = sum(entry.debit_amount or Decimal('0') for entry in entries)
        total_credits = sum(entry.credit_amount or Decimal('0') for entry in entries)
        
        account_types = {}
        for entry in entries:
            if entry.accounting_code and entry.accounting_code.account_type:
                acc_type = entry.accounting_code.account_type
                if acc_type not in account_types:
                    account_types[acc_type] = {
                        'debits': Decimal('0'),
                        'credits': Decimal('0'),
                        'count': 0
                    }
                account_types[acc_type]['debits'] += (entry.debit_amount or Decimal('0'))
                account_types[acc_type]['credits'] += (entry.credit_amount or Decimal('0'))
                account_types[acc_type]['count'] += 1
        
        return {
            'total_debits': float(total_debits),
            'total_credits': float(total_credits),
            'net_difference': float(total_debits - total_credits),
            'entry_count': len(entries),
            'account_types': {
                acc_type: {
                    'debits': float(data['debits']),
                    'credits': float(data['credits']),
                    'count': data['count']
                }
                for acc_type, data in account_types.items()
            }
        }
    
    def _get_account_balance_as_of_date(self, account_id: str, as_of_date: date) -> Dict[str, Any]:
        """Get account balance as of specific date"""
        # Get opening balance
        opening_balance = self._get_opening_balance(account_id, as_of_date)
        
        # Get transactions up to date
        entries = self.db.query(JournalEntry).filter(
            and_(
                JournalEntry.accounting_code_id == account_id,
                JournalEntry.date <= as_of_date
            )
        ).all()
        
        total_debits = sum(entry.debit_amount or Decimal('0') for entry in entries)
        total_credits = sum(entry.credit_amount or Decimal('0') for entry in entries)
        
        # Get account for normal balance
        account = self.db.query(AccountingCode).filter(
            AccountingCode.id == account_id
        ).first()
        
        if account:
            normal_balance = get_normal_balance(account.account_type)
            if normal_balance == NormalBalance.DEBIT.value:
                balance = opening_balance + total_debits - total_credits
            else:
                balance = opening_balance + total_credits - total_debits
        else:
            balance = opening_balance + total_debits - total_credits
        
        return {
            'opening_balance': opening_balance,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'balance': balance
        }

    def _get_opening_balance_for_period(self, account_id: str, period_start: Optional[date]) -> Decimal:
        """
        Compute opening balance as of the start of the requested period.
        This equals:
          OpeningBalance for that account/year
          + net movements from the start of that year up to (but not including) period_start,
            taking into account the account's normal balance.
        """
        if not period_start:
            return Decimal('0')

        # Opening balance for the year containing period_start
        opening_year_balance = self._get_opening_balance(account_id, period_start)

        # Sum movements from beginning of the year to day before period_start
        year_start = date(period_start.year, 1, 1)
        if period_start <= year_start:
            return opening_year_balance

        pre_entries = self.db.query(JournalEntry).filter(
            and_(
                JournalEntry.accounting_code_id == account_id,
                JournalEntry.date >= year_start,
                JournalEntry.date < period_start
            )
        ).all()

        total_debits = sum(entry.debit_amount or Decimal('0') for entry in pre_entries)
        total_credits = sum(entry.credit_amount or Decimal('0') for entry in pre_entries)

        account = self.db.query(AccountingCode).filter(AccountingCode.id == account_id).first()
        if account:
            normal_balance = get_normal_balance(account.account_type)
            if normal_balance == NormalBalance.DEBIT.value:
                return opening_year_balance + total_debits - total_credits
            else:
                return opening_year_balance + total_credits - total_debits

        # Fallback if account not found (treat as debit-normal)
        return opening_year_balance + total_debits - total_credits
    
    def _get_opening_balance(self, account_id: str, as_of_date: Optional[date] = None) -> Decimal:
        """Get opening balance for account"""
        if not as_of_date:
            as_of_date = date.today()
        
        opening_balance = self.db.query(OpeningBalance).filter(
            and_(
                OpeningBalance.accounting_code_id == account_id,
                OpeningBalance.year == as_of_date.year
            )
        ).first()
        
        return opening_balance.amount if opening_balance else Decimal('0')
    
    def _get_accounts_by_type(self, account_type: AccountType, 
                             as_of_date: date, branch_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get accounts of specific type with balances"""
        query = self.db.query(AccountingCode).filter(
            AccountingCode.account_type == account_type
        )
        
        if branch_id:
            query = query.filter(AccountingCode.branch_id == branch_id)
        
        accounts = query.all()
        
        result = []
        for account in accounts:
            balance_info = self._get_account_balance_as_of_date(account.id, as_of_date)
            
            result.append({
                'id': account.id,
                'code': account.code,
                'name': account.name,
                'category': account.category,
                'balance': float(balance_info['balance']),
                'is_parent': account.is_parent,
                'parent_id': account.parent_id
            })
        
        return result
