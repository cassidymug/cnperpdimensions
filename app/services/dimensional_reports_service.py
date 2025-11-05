"""
Dimensional Financial Reports Service

A comprehensive service for generating financial reports with dimensional analysis
including Cost Centers, Projects, and other business dimensions.

Supports:
- Profit & Loss with dimensional filtering
- Balance Sheet with dimensional breakdowns
- General Ledger with dimensional analysis
- Debtors/Creditors dimensional analysis
- Sales/Purchase reports with dimensions
- Comparative period reporting
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, extract, text
from collections import defaultdict

from app.models.accounting import AccountingCode, JournalEntry, AccountingEntry
from app.models.accounting_dimensions import (
    AccountingDimension, AccountingDimensionValue, DimensionType
)
from app.models.accounting_code_dimensions import AccountingCodeDimensionRequirement
from app.core.database import get_db


class DimensionalReportsService:
    """Service for generating dimensional financial reports"""

    def __init__(self, db: Session):
        self.db = db

    def get_dimension_filters(self, dimension_filters: Dict[str, str] = None) -> Dict[str, Any]:
        """Build dimension filter conditions for SQL queries"""
        filters = {}

        if not dimension_filters:
            return filters

        for dimension_type, dimension_value_id in dimension_filters.items():
            if dimension_value_id:
                filters[dimension_type] = dimension_value_id

        return filters

    def apply_dimensional_filters(self, query, dimension_filters: Dict[str, str] = None):
        """Apply dimensional filters to a SQLAlchemy query"""
        if not dimension_filters:
            return query

        # Join with dimensional tables if filters are provided
        for dimension_type, dimension_value_id in dimension_filters.items():
            if dimension_value_id:
                # This would need to be implemented based on your transaction model
                # For now, returning the original query
                pass

        return query

    def get_dimensional_profit_loss(
        self,
        start_date: date,
        end_date: date,
        dimension_filters: Dict[str, str] = None,
        comparison_period: bool = False,
        comparison_start_date: date = None,
        comparison_end_date: date = None,
        group_by_dimensions: bool = True
    ) -> Dict[str, Any]:
        """
        Generate Profit & Loss statement with dimensional analysis

        Args:
            start_date: Report period start
            end_date: Report period end
            dimension_filters: Dict of dimension_type -> dimension_value_id
            comparison_period: Include comparative period
            comparison_start_date: Comparison period start
            comparison_end_date: Comparison period end
            group_by_dimensions: Group results by dimensions
        """

        # Base query for revenue accounts
        revenue_query = self.db.query(
            AccountingCode.code,
            AccountingCode.name,
            AccountingCode.account_type,
            AccountingCode.category,
            func.sum(AccountingEntry.credit_amount - AccountingEntry.debit_amount).label('amount')
        ).join(
            AccountingEntry, AccountingCode.id == AccountingEntry.account_code_id
        ).join(
            JournalEntry, AccountingEntry.journal_entry_id == JournalEntry.id
        ).filter(
            AccountingCode.account_type == 'Revenue',
            JournalEntry.transaction_date.between(start_date, end_date)
        ).group_by(
            AccountingCode.id, AccountingCode.code, AccountingCode.name,
            AccountingCode.account_type, AccountingCode.category
        )

        # Apply dimensional filters
        revenue_query = self.apply_dimensional_filters(revenue_query, dimension_filters)
        revenue_accounts = revenue_query.all()

        # Base query for expense accounts
        expense_query = self.db.query(
            AccountingCode.code,
            AccountingCode.name,
            AccountingCode.account_type,
            AccountingCode.category,
            func.sum(AccountingEntry.debit_amount - AccountingEntry.credit_amount).label('amount')
        ).join(
            AccountingEntry, AccountingCode.id == AccountingEntry.account_code_id
        ).join(
            JournalEntry, AccountingEntry.journal_entry_id == JournalEntry.id
        ).filter(
            AccountingCode.account_type == 'Expense',
            JournalEntry.transaction_date.between(start_date, end_date)
        ).group_by(
            AccountingCode.id, AccountingCode.code, AccountingCode.name,
            AccountingCode.account_type, AccountingCode.category
        )

        # Apply dimensional filters
        expense_query = self.apply_dimensional_filters(expense_query, dimension_filters)
        expense_accounts = expense_query.all()

        # Calculate totals
        total_revenue = sum(float(acc.amount or 0) for acc in revenue_accounts)
        total_expenses = sum(float(acc.amount or 0) for acc in expense_accounts)
        net_income = total_revenue - total_expenses

        # Group by categories for better presentation
        revenue_by_category = defaultdict(list)
        for acc in revenue_accounts:
            revenue_by_category[acc.category or 'Other Revenue'].append({
                'code': acc.code,
                'name': acc.name,
                'amount': float(acc.amount or 0)
            })

        expense_by_category = defaultdict(list)
        for acc in expense_accounts:
            expense_by_category[acc.category or 'Other Expenses'].append({
                'code': acc.code,
                'name': acc.name,
                'amount': float(acc.amount or 0)
            })

        result = {
            'report_type': 'profit_loss',
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'dimension_filters': dimension_filters or {},
            'revenue': {
                'categories': dict(revenue_by_category),
                'total': total_revenue
            },
            'expenses': {
                'categories': dict(expense_by_category),
                'total': total_expenses
            },
            'net_income': net_income,
            'generated_at': datetime.now().isoformat()
        }

        # Add comparison period if requested
        if comparison_period and comparison_start_date and comparison_end_date:
            comparison_data = self.get_dimensional_profit_loss(
                comparison_start_date, comparison_end_date, dimension_filters,
                comparison_period=False, group_by_dimensions=group_by_dimensions
            )
            result['comparison_period'] = comparison_data

            # Add variance analysis
            result['variance'] = {
                'revenue': total_revenue - comparison_data['revenue']['total'],
                'expenses': total_expenses - comparison_data['expenses']['total'],
                'net_income': net_income - comparison_data['net_income']
            }

        return result

    def get_dimensional_balance_sheet(
        self,
        as_of_date: date = None,
        dimension_filters: Dict[str, str] = None,
        comparison_date: date = None,
        group_by_dimensions: bool = True
    ) -> Dict[str, Any]:
        """
        Generate Balance Sheet with dimensional analysis
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Query for asset accounts
        asset_query = self.db.query(
            AccountingCode.code,
            AccountingCode.name,
            AccountingCode.account_type,
            AccountingCode.category,
            func.sum(AccountingEntry.debit_amount - AccountingEntry.credit_amount).label('balance')
        ).join(
            AccountingEntry, AccountingCode.id == AccountingEntry.account_code_id
        ).join(
            JournalEntry, AccountingEntry.journal_entry_id == JournalEntry.id
        ).filter(
            AccountingCode.account_type == 'Asset',
            JournalEntry.transaction_date <= as_of_date
        ).group_by(
            AccountingCode.id, AccountingCode.code, AccountingCode.name,
            AccountingCode.account_type, AccountingCode.category
        )

        asset_query = self.apply_dimensional_filters(asset_query, dimension_filters)
        asset_accounts = asset_query.all()

        # Query for liability accounts
        liability_query = self.db.query(
            AccountingCode.code,
            AccountingCode.name,
            AccountingCode.account_type,
            AccountingCode.category,
            func.sum(AccountingEntry.credit_amount - AccountingEntry.debit_amount).label('balance')
        ).join(
            AccountingEntry, AccountingCode.id == AccountingEntry.account_code_id
        ).join(
            JournalEntry, AccountingEntry.journal_entry_id == JournalEntry.id
        ).filter(
            AccountingCode.account_type == 'Liability',
            JournalEntry.transaction_date <= as_of_date
        ).group_by(
            AccountingCode.id, AccountingCode.code, AccountingCode.name,
            AccountingCode.account_type, AccountingCode.category
        )

        liability_query = self.apply_dimensional_filters(liability_query, dimension_filters)
        liability_accounts = liability_query.all()

        # Query for equity accounts
        equity_query = self.db.query(
            AccountingCode.code,
            AccountingCode.name,
            AccountingCode.account_type,
            AccountingCode.category,
            func.sum(AccountingEntry.credit_amount - AccountingEntry.debit_amount).label('balance')
        ).join(
            AccountingEntry, AccountingCode.id == AccountingEntry.account_code_id
        ).join(
            JournalEntry, AccountingEntry.journal_entry_id == JournalEntry.id
        ).filter(
            AccountingCode.account_type == 'Equity',
            JournalEntry.transaction_date <= as_of_date
        ).group_by(
            AccountingCode.id, AccountingCode.code, AccountingCode.name,
            AccountingCode.account_type, AccountingCode.category
        )

        equity_query = self.apply_dimensional_filters(equity_query, dimension_filters)
        equity_accounts = equity_query.all()

        # Group by categories
        assets_by_category = defaultdict(list)
        for acc in asset_accounts:
            assets_by_category[acc.category or 'Other Assets'].append({
                'code': acc.code,
                'name': acc.name,
                'balance': float(acc.balance or 0)
            })

        liabilities_by_category = defaultdict(list)
        for acc in liability_accounts:
            liabilities_by_category[acc.category or 'Other Liabilities'].append({
                'code': acc.code,
                'name': acc.name,
                'balance': float(acc.balance or 0)
            })

        equity_by_category = defaultdict(list)
        for acc in equity_accounts:
            equity_by_category[acc.category or 'Other Equity'].append({
                'code': acc.code,
                'name': acc.name,
                'balance': float(acc.balance or 0)
            })

        total_assets = sum(float(acc.balance or 0) for acc in asset_accounts)
        total_liabilities = sum(float(acc.balance or 0) for acc in liability_accounts)
        total_equity = sum(float(acc.balance or 0) for acc in equity_accounts)

        return {
            'report_type': 'balance_sheet',
            'as_of_date': as_of_date.isoformat(),
            'dimension_filters': dimension_filters or {},
            'assets': {
                'categories': dict(assets_by_category),
                'total': total_assets
            },
            'liabilities': {
                'categories': dict(liabilities_by_category),
                'total': total_liabilities
            },
            'equity': {
                'categories': dict(equity_by_category),
                'total': total_equity
            },
            'total_liabilities_and_equity': total_liabilities + total_equity,
            'balance_check': abs(total_assets - (total_liabilities + total_equity)) < 0.01,
            'generated_at': datetime.now().isoformat()
        }

    def get_dimensional_general_ledger(
        self,
        start_date: date,
        end_date: date,
        account_codes: List[str] = None,
        dimension_filters: Dict[str, str] = None,
        group_by_dimensions: bool = True
    ) -> Dict[str, Any]:
        """
        Generate General Ledger with dimensional analysis
        """

        query = self.db.query(
            AccountingCode.code,
            AccountingCode.name,
            AccountingCode.account_type,
            JournalEntry.transaction_date,
            JournalEntry.description,
            JournalEntry.reference,
            AccountingEntry.debit_amount,
            AccountingEntry.credit_amount,
            AccountingEntry.description.label('entry_description')
        ).join(
            AccountingEntry, AccountingCode.id == AccountingEntry.account_code_id
        ).join(
            JournalEntry, AccountingEntry.journal_entry_id == JournalEntry.id
        ).filter(
            JournalEntry.transaction_date.between(start_date, end_date)
        )

        # Filter by specific accounts if provided
        if account_codes:
            query = query.filter(AccountingCode.code.in_(account_codes))

        # Apply dimensional filters
        query = self.apply_dimensional_filters(query, dimension_filters)

        # Order by account code and date
        query = query.order_by(AccountingCode.code, JournalEntry.transaction_date)

        entries = query.all()

        # Group entries by account
        accounts = defaultdict(lambda: {
            'name': '',
            'account_type': '',
            'entries': [],
            'running_balance': 0.0,
            'total_debits': 0.0,
            'total_credits': 0.0
        })

        for entry in entries:
            account_code = entry.code

            if not accounts[account_code]['name']:
                accounts[account_code]['name'] = entry.name
                accounts[account_code]['account_type'] = entry.account_type

            debit = float(entry.debit_amount or 0)
            credit = float(entry.credit_amount or 0)

            # Update running balance based on account type
            if entry.account_type in ['Asset', 'Expense']:
                balance_change = debit - credit
            else:  # Liability, Equity, Revenue
                balance_change = credit - debit

            accounts[account_code]['running_balance'] += balance_change
            accounts[account_code]['total_debits'] += debit
            accounts[account_code]['total_credits'] += credit

            accounts[account_code]['entries'].append({
                'date': entry.transaction_date.isoformat(),
                'description': entry.description,
                'reference': entry.reference,
                'entry_description': entry.entry_description,
                'debit': debit,
                'credit': credit,
                'balance': accounts[account_code]['running_balance']
            })

        return {
            'report_type': 'general_ledger',
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'dimension_filters': dimension_filters or {},
            'account_filters': account_codes or [],
            'accounts': dict(accounts),
            'generated_at': datetime.now().isoformat()
        }

    def get_debtors_dimensional_analysis(
        self,
        as_of_date: date = None,
        dimension_filters: Dict[str, str] = None,
        aging_buckets: List[int] = [30, 60, 90, 120]
    ) -> Dict[str, Any]:
        """
        Generate Debtors (Accounts Receivable) analysis with dimensional breakdown
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Query for receivable accounts
        receivables_query = self.db.query(
            AccountingCode.code,
            AccountingCode.name,
            JournalEntry.transaction_date,
            JournalEntry.reference,
            JournalEntry.description,
            func.sum(AccountingEntry.debit_amount - AccountingEntry.credit_amount).label('balance')
        ).join(
            AccountingEntry, AccountingCode.id == AccountingEntry.account_code_id
        ).join(
            JournalEntry, AccountingEntry.journal_entry_id == JournalEntry.id
        ).filter(
            AccountingCode.category.ilike('%receivable%'),
            JournalEntry.transaction_date <= as_of_date
        ).group_by(
            AccountingCode.code, AccountingCode.name,
            JournalEntry.id, JournalEntry.transaction_date,
            JournalEntry.reference, JournalEntry.description
        ).having(
            func.sum(AccountingEntry.debit_amount - AccountingEntry.credit_amount) > 0
        )

        receivables_query = self.apply_dimensional_filters(receivables_query, dimension_filters)
        receivables = receivables_query.all()

        # Calculate aging
        aging_analysis = {
            'current': [],
            '1-30_days': [],
            '31-60_days': [],
            '61-90_days': [],
            '91-120_days': [],
            'over_120_days': []
        }

        total_outstanding = 0.0

        for receivable in receivables:
            days_outstanding = (as_of_date - receivable.transaction_date).days
            balance = float(receivable.balance or 0)
            total_outstanding += balance

            item = {
                'account_code': receivable.code,
                'account_name': receivable.name,
                'reference': receivable.reference,
                'description': receivable.description,
                'transaction_date': receivable.transaction_date.isoformat(),
                'days_outstanding': days_outstanding,
                'balance': balance
            }

            if days_outstanding <= 0:
                aging_analysis['current'].append(item)
            elif days_outstanding <= 30:
                aging_analysis['1-30_days'].append(item)
            elif days_outstanding <= 60:
                aging_analysis['31-60_days'].append(item)
            elif days_outstanding <= 90:
                aging_analysis['61-90_days'].append(item)
            elif days_outstanding <= 120:
                aging_analysis['91-120_days'].append(item)
            else:
                aging_analysis['over_120_days'].append(item)

        # Calculate totals for each bucket
        aging_totals = {}
        for bucket, items in aging_analysis.items():
            aging_totals[bucket] = sum(item['balance'] for item in items)

        return {
            'report_type': 'debtors_analysis',
            'as_of_date': as_of_date.isoformat(),
            'dimension_filters': dimension_filters or {},
            'aging_analysis': aging_analysis,
            'aging_totals': aging_totals,
            'total_outstanding': total_outstanding,
            'generated_at': datetime.now().isoformat()
        }

    def get_creditors_dimensional_analysis(
        self,
        as_of_date: date = None,
        dimension_filters: Dict[str, str] = None,
        aging_buckets: List[int] = [30, 60, 90, 120]
    ) -> Dict[str, Any]:
        """
        Generate Creditors (Accounts Payable) analysis with dimensional breakdown
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Query for payable accounts
        payables_query = self.db.query(
            AccountingCode.code,
            AccountingCode.name,
            JournalEntry.transaction_date,
            JournalEntry.reference,
            JournalEntry.description,
            func.sum(AccountingEntry.credit_amount - AccountingEntry.debit_amount).label('balance')
        ).join(
            AccountingEntry, AccountingCode.id == AccountingEntry.account_code_id
        ).join(
            JournalEntry, AccountingEntry.journal_entry_id == JournalEntry.id
        ).filter(
            AccountingCode.category.ilike('%payable%'),
            JournalEntry.transaction_date <= as_of_date
        ).group_by(
            AccountingCode.code, AccountingCode.name,
            JournalEntry.id, JournalEntry.transaction_date,
            JournalEntry.reference, JournalEntry.description
        ).having(
            func.sum(AccountingEntry.credit_amount - AccountingEntry.debit_amount) > 0
        )

        payables_query = self.apply_dimensional_filters(payables_query, dimension_filters)
        payables = payables_query.all()

        # Calculate aging (similar to debtors but for payables)
        aging_analysis = {
            'current': [],
            '1-30_days': [],
            '31-60_days': [],
            '61-90_days': [],
            '91-120_days': [],
            'over_120_days': []
        }

        total_outstanding = 0.0

        for payable in payables:
            days_outstanding = (as_of_date - payable.transaction_date).days
            balance = float(payable.balance or 0)
            total_outstanding += balance

            item = {
                'account_code': payable.code,
                'account_name': payable.name,
                'reference': payable.reference,
                'description': payable.description,
                'transaction_date': payable.transaction_date.isoformat(),
                'days_outstanding': days_outstanding,
                'balance': balance
            }

            if days_outstanding <= 0:
                aging_analysis['current'].append(item)
            elif days_outstanding <= 30:
                aging_analysis['1-30_days'].append(item)
            elif days_outstanding <= 60:
                aging_analysis['31-60_days'].append(item)
            elif days_outstanding <= 90:
                aging_analysis['61-90_days'].append(item)
            elif days_outstanding <= 120:
                aging_analysis['91-120_days'].append(item)
            else:
                aging_analysis['over_120_days'].append(item)

        # Calculate totals for each bucket
        aging_totals = {}
        for bucket, items in aging_analysis.items():
            aging_totals[bucket] = sum(item['balance'] for item in items)

        return {
            'report_type': 'creditors_analysis',
            'as_of_date': as_of_date.isoformat(),
            'dimension_filters': dimension_filters or {},
            'aging_analysis': aging_analysis,
            'aging_totals': aging_totals,
            'total_outstanding': total_outstanding,
            'generated_at': datetime.now().isoformat()
        }

    def get_sales_dimensional_analysis(
        self,
        start_date: date,
        end_date: date,
        dimension_filters: Dict[str, str] = None,
        group_by_period: str = 'month'  # 'day', 'week', 'month', 'quarter'
    ) -> Dict[str, Any]:
        """
        Generate Sales analysis with dimensional breakdown
        """

        # Query for sales/revenue transactions
        sales_query = self.db.query(
            AccountingCode.code,
            AccountingCode.name,
            AccountingCode.category,
            JournalEntry.transaction_date,
            JournalEntry.reference,
            JournalEntry.description,
            func.sum(AccountingEntry.credit_amount).label('sales_amount')
        ).join(
            AccountingEntry, AccountingCode.id == AccountingEntry.account_code_id
        ).join(
            JournalEntry, AccountingEntry.journal_entry_id == JournalEntry.id
        ).filter(
            AccountingCode.account_type == 'Revenue',
            JournalEntry.transaction_date.between(start_date, end_date)
        ).group_by(
            AccountingCode.code, AccountingCode.name, AccountingCode.category,
            JournalEntry.transaction_date, JournalEntry.reference, JournalEntry.description
        )

        sales_query = self.apply_dimensional_filters(sales_query, dimension_filters)
        sales_data = sales_query.all()

        # Group by time periods
        period_sales = defaultdict(lambda: {
            'total_sales': 0.0,
            'transactions': []
        })

        category_sales = defaultdict(float)
        total_sales = 0.0

        for sale in sales_data:
            amount = float(sale.sales_amount or 0)
            total_sales += amount

            # Group by category
            category_sales[sale.category or 'Other Sales'] += amount

            # Group by time period
            if group_by_period == 'day':
                period_key = sale.transaction_date.isoformat()
            elif group_by_period == 'week':
                # Get start of week
                start_of_week = sale.transaction_date - timedelta(days=sale.transaction_date.weekday())
                period_key = start_of_week.isoformat()
            elif group_by_period == 'month':
                period_key = sale.transaction_date.strftime('%Y-%m')
            elif group_by_period == 'quarter':
                quarter = (sale.transaction_date.month - 1) // 3 + 1
                period_key = f"{sale.transaction_date.year}-Q{quarter}"
            else:
                period_key = sale.transaction_date.isoformat()

            period_sales[period_key]['total_sales'] += amount
            period_sales[period_key]['transactions'].append({
                'account_code': sale.code,
                'account_name': sale.name,
                'category': sale.category,
                'date': sale.transaction_date.isoformat(),
                'reference': sale.reference,
                'description': sale.description,
                'amount': amount
            })

        return {
            'report_type': 'sales_analysis',
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'dimension_filters': dimension_filters or {},
            'group_by_period': group_by_period,
            'period_sales': dict(period_sales),
            'category_sales': dict(category_sales),
            'total_sales': total_sales,
            'generated_at': datetime.now().isoformat()
        }

    def get_purchases_dimensional_analysis(
        self,
        start_date: date,
        end_date: date,
        dimension_filters: Dict[str, str] = None,
        group_by_period: str = 'month'
    ) -> Dict[str, Any]:
        """
        Generate Purchases analysis with dimensional breakdown
        """

        # Query for purchase/expense transactions
        purchases_query = self.db.query(
            AccountingCode.code,
            AccountingCode.name,
            AccountingCode.category,
            JournalEntry.transaction_date,
            JournalEntry.reference,
            JournalEntry.description,
            func.sum(AccountingEntry.debit_amount).label('purchase_amount')
        ).join(
            AccountingEntry, AccountingCode.id == AccountingEntry.account_code_id
        ).join(
            JournalEntry, AccountingEntry.journal_entry_id == JournalEntry.id
        ).filter(
            or_(
                AccountingCode.account_type == 'Expense',
                AccountingCode.category.ilike('%cost of%'),
                AccountingCode.category.ilike('%purchase%')
            ),
            JournalEntry.transaction_date.between(start_date, end_date)
        ).group_by(
            AccountingCode.code, AccountingCode.name, AccountingCode.category,
            JournalEntry.transaction_date, JournalEntry.reference, JournalEntry.description
        )

        purchases_query = self.apply_dimensional_filters(purchases_query, dimension_filters)
        purchases_data = purchases_query.all()

        # Group by time periods (similar to sales analysis)
        period_purchases = defaultdict(lambda: {
            'total_purchases': 0.0,
            'transactions': []
        })

        category_purchases = defaultdict(float)
        total_purchases = 0.0

        for purchase in purchases_data:
            amount = float(purchase.purchase_amount or 0)
            total_purchases += amount

            # Group by category
            category_purchases[purchase.category or 'Other Purchases'] += amount

            # Group by time period
            if group_by_period == 'day':
                period_key = purchase.transaction_date.isoformat()
            elif group_by_period == 'week':
                start_of_week = purchase.transaction_date - timedelta(days=purchase.transaction_date.weekday())
                period_key = start_of_week.isoformat()
            elif group_by_period == 'month':
                period_key = purchase.transaction_date.strftime('%Y-%m')
            elif group_by_period == 'quarter':
                quarter = (purchase.transaction_date.month - 1) // 3 + 1
                period_key = f"{purchase.transaction_date.year}-Q{quarter}"
            else:
                period_key = purchase.transaction_date.isoformat()

            period_purchases[period_key]['total_purchases'] += amount
            period_purchases[period_key]['transactions'].append({
                'account_code': purchase.code,
                'account_name': purchase.name,
                'category': purchase.category,
                'date': purchase.transaction_date.isoformat(),
                'reference': purchase.reference,
                'description': purchase.description,
                'amount': amount
            })

        return {
            'report_type': 'purchases_analysis',
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'dimension_filters': dimension_filters or {},
            'group_by_period': group_by_period,
            'period_purchases': dict(period_purchases),
            'category_purchases': dict(category_purchases),
            'total_purchases': total_purchases,
            'generated_at': datetime.now().isoformat()
        }

    def get_available_dimensions(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all available dimensions and their values for filtering
        """
        dimensions = self.db.query(AccountingDimension).filter(
            AccountingDimension.is_active == True
        ).all()

        result = {}
        for dimension in dimensions:
            values = self.db.query(AccountingDimensionValue).filter(
                AccountingDimensionValue.dimension_id == dimension.id,
                AccountingDimensionValue.is_active == True
            ).all()

            result[dimension.dimension_type.value] = [
                {
                    'id': value.id,
                    'code': value.code,
                    'name': value.name,
                    'full_path': value.full_path
                }
                for value in values
            ]

        return result
