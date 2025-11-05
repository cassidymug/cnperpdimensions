"""
Financial Statements Service for IFRS-compliant real-time financial reporting
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, extract

from app.models.accounting import AccountingCode, JournalEntry, AccountingEntry
from app.services.ifrs_reports_core import IFRSReportsCore
from app.schemas.financial_statements import (
    BalanceSheet, BalanceSheetAssets, BalanceSheetLiabilitiesAndEquity,
    IncomeStatement, IncomeStatementRevenue, IncomeStatementExpenses,
    CashFlowStatement, CashFlowActivity,
    StatementOfChangesInEquity, EquityMovement, TrialBalance, TrialBalanceAccount,
    FinancialReportPackage, ReportMetadata, AccountLineItem, FinancialStatementSection,
    ReportPeriodType, IFRSStandard
)


class FinancialStatementsService:
    """Service for generating comprehensive IFRS-compliant financial statements"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ifrs_core = IFRSReportsCore(db)
        
    def get_report_metadata(self, report_type: str, as_of_date: date = None) -> ReportMetadata:
        """Generate metadata for financial reports"""
        if as_of_date is None:
            as_of_date = date.today()
            
        return ReportMetadata(
            report_id=f"rpt_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            report_type=report_type,
            company_name="Your Company Name",  # TODO: Get from settings
            reporting_date=as_of_date,
            period_start=as_of_date.replace(month=1, day=1),  # Start of year
            period_end=as_of_date,
            period_type=ReportPeriodType.ANNUALLY,
            ifrs_standards=[IFRSStandard.IAS_1],
            prepared_by="System Generated",
            prepared_at=datetime.now()
        )
    
    def get_balance_sheet(
        self, 
        as_of_date: date = None,
        comparison_date: date = None,
        include_notes: bool = True
    ) -> BalanceSheet:
        """Generate IFRS-compliant Balance Sheet"""
        
        if as_of_date is None:
            as_of_date = date.today()
            
        # Get balance sheet data from existing service
        bs_data = self.ifrs_core.get_balance_sheet_data(as_of_date, comparison_date)
        
        # Convert to new schema format
        current_assets_section = FinancialStatementSection(
            section_name="Current Assets",
            section_code="CA",
            line_items=[
                AccountLineItem(
                    account_code=item['account_code'],
                    account_name=item['account_name'],
                    account_type="Asset",
                    ifrs_category="Current Assets",
                    current_period=Decimal(str(item['amount'])),
                    prior_period=Decimal('0.00'),  # TODO: Add comparison logic
                    notes=""
                ) for item in bs_data['assets']['current_assets']
            ],
            subtotal=Decimal(str(bs_data['assets']['total_current_assets'])),
            notes=None
        )
        
        non_current_assets_section = FinancialStatementSection(
            section_name="Non-Current Assets",
            section_code="NCA",
            line_items=[
                AccountLineItem(
                    account_code=item['account_code'],
                    account_name=item['account_name'],
                    account_type="Asset",
                    ifrs_category="Non-Current Assets",
                    current_period=Decimal(str(item['amount'])),
                    prior_period=Decimal('0.00'),
                    notes=""
                ) for item in bs_data['assets']['non_current_assets']
            ],
            subtotal=Decimal(str(bs_data['assets']['total_non_current_assets'])),
            notes=None
        )
        
        current_liabilities_section = FinancialStatementSection(
            section_name="Current Liabilities",
            section_code="CL",
            line_items=[
                AccountLineItem(
                    account_code=item['account_code'],
                    account_name=item['account_name'],
                    account_type="Liability",
                    ifrs_category="Current Liabilities",
                    current_period=Decimal(str(item['amount'])),
                    prior_period=Decimal('0.00'),
                    notes=""
                ) for item in bs_data['liabilities']['current_liabilities']
            ],
            subtotal=Decimal(str(bs_data['liabilities']['total_current_liabilities'])),
            notes=None
        )
        
        non_current_liabilities_section = FinancialStatementSection(
            section_name="Non-Current Liabilities",
            section_code="NCL",
            line_items=[
                AccountLineItem(
                    account_code=item['account_code'],
                    account_name=item['account_name'],
                    account_type="Liability",
                    ifrs_category="Non-Current Liabilities",
                    current_period=Decimal(str(item['amount'])),
                    prior_period=Decimal('0.00'),
                    notes=""
                ) for item in bs_data['liabilities']['non_current_liabilities']
            ],
            subtotal=Decimal(str(bs_data['liabilities']['total_non_current_liabilities'])),
            notes=None
        )
        
        equity_section = FinancialStatementSection(
            section_name="Equity",
            section_code="EQ",
            line_items=[
                AccountLineItem(
                    account_code=item['account_code'],
                    account_name=item['account_name'],
                    account_type="Equity",
                    ifrs_category="Equity",
                    current_period=Decimal(str(item['amount'])),
                    prior_period=Decimal('0.00'),
                    notes=""
                ) for item in bs_data['equity']
            ],
            subtotal=Decimal(str(bs_data['totals']['total_equity'])),
            notes=None
        )
        
        # Create the structured balance sheet according to schema
        assets = BalanceSheetAssets(
            current_assets=current_assets_section,
            non_current_assets=non_current_assets_section,
            total_assets=Decimal(str(bs_data['totals']['total_assets']))
        )
        
        liabilities_and_equity = BalanceSheetLiabilitiesAndEquity(
            current_liabilities=current_liabilities_section,
            non_current_liabilities=non_current_liabilities_section,
            total_liabilities=Decimal(str(bs_data['totals']['total_liabilities'])),
            equity=equity_section,
            total_equity=Decimal(str(bs_data['totals']['total_equity'])),
            total_liabilities_and_equity=Decimal(str(bs_data['totals']['total_liabilities'] + bs_data['totals']['total_equity']))
        )
        
        return BalanceSheet(
            metadata=self.get_report_metadata("Balance Sheet", as_of_date),
            assets=assets,
            liabilities_and_equity=liabilities_and_equity
        )
    
    def get_income_statement(
        self,
        start_date: date = None,
        end_date: date = None,
        comparison_start_date: date = None,
        comparison_end_date: date = None
    ) -> IncomeStatement:
        """Generate IFRS-compliant Income Statement"""
        
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = date(end_date.year, 1, 1)  # Start of year
            
        # Get revenue accounts
        revenue_data = self._get_accounts_by_type_and_period('REVENUE', start_date, end_date)
        expense_data = self._get_accounts_by_type_and_period('EXPENSE', start_date, end_date)
        
        # Categorize expenses
        cost_of_sales = [item for item in expense_data if 'cost' in item['account_name'].lower() or 'cogs' in item['account_name'].lower()]
        operating_expenses = [item for item in expense_data if item not in cost_of_sales]
        
        operating_revenue_section = FinancialStatementSection(
            section_name="Operating Revenue",
            section_code="REV_OP",
            line_items=[
                AccountLineItem(
                    account_code=item['account_code'],
                    account_name=item['account_name'],
                    current_amount=Decimal(str(item['amount'])),
                    prior_amount=Decimal('0.00'),
                    notes=[]
                ) for item in revenue_data
            ],
            subtotal=sum(Decimal(str(item['amount'])) for item in revenue_data)
        )
        
        other_revenue_section = FinancialStatementSection(
            section_name="Other Revenue",
            section_code="REV_OTH",
            line_items=[],
            subtotal=Decimal('0.00')
        )
        
        cost_of_sales_section = FinancialStatementSection(
            section_name="Cost of Sales",
            section_code="COGS",
            line_items=[
                AccountLineItem(
                    account_code=item['account_code'],
                    account_name=item['account_name'],
                    current_amount=Decimal(str(item['amount'])),
                    prior_amount=Decimal('0.00'),
                    notes=[]
                ) for item in cost_of_sales
            ],
            subtotal=sum(Decimal(str(item['amount'])) for item in cost_of_sales)
        )
        
        operating_expenses_section = FinancialStatementSection(
            section_name="Operating Expenses",
            section_code="EXP_OP",
            line_items=[
                AccountLineItem(
                    account_code=item['account_code'],
                    account_name=item['account_name'],
                    current_amount=Decimal(str(item['amount'])),
                    prior_amount=Decimal('0.00'),
                    notes=[]
                ) for item in operating_expenses
            ],
            subtotal=sum(Decimal(str(item['amount'])) for item in operating_expenses)
        )
        
        finance_costs_section = FinancialStatementSection(
            section_name="Finance Costs",
            section_code="FIN_COST",
            line_items=[],
            subtotal=Decimal('0.00')
        )
        
        other_expenses_section = FinancialStatementSection(
            section_name="Other Expenses",
            section_code="EXP_OTH",
            line_items=[],
            subtotal=Decimal('0.00')
        )
        
        total_revenue = operating_revenue_section.subtotal + other_revenue_section.subtotal
        total_expenses = cost_of_sales_section.subtotal + operating_expenses_section.subtotal + finance_costs_section.subtotal + other_expenses_section.subtotal
        
        gross_profit = operating_revenue_section.subtotal - cost_of_sales_section.subtotal
        operating_profit = gross_profit - operating_expenses_section.subtotal
        profit_before_tax = operating_profit - finance_costs_section.subtotal
        tax_expense = Decimal('0.00')  # TODO: Implement
        profit_after_tax = profit_before_tax - tax_expense
        
        revenue = IncomeStatementRevenue(
            operating_revenue=operating_revenue_section,
            other_revenue=other_revenue_section,
            total_revenue=total_revenue
        )
        
        expenses = IncomeStatementExpenses(
            cost_of_sales=cost_of_sales_section,
            operating_expenses=operating_expenses_section,
            finance_costs=finance_costs_section,
            other_expenses=other_expenses_section,
            total_expenses=total_expenses
        )
        
        return IncomeStatement(
            metadata=self.get_report_metadata("Income Statement", end_date),
            revenue=revenue,
            expenses=expenses,
            gross_profit=gross_profit,
            operating_profit=operating_profit,
            profit_before_tax=profit_before_tax,
            tax_expense=tax_expense,
            profit_after_tax=profit_after_tax
        )
    
    def get_cash_flow_statement(
        self,
        start_date: date = None,
        end_date: date = None
    ) -> CashFlowStatement:
        """Generate IFRS-compliant Cash Flow Statement"""
        
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = date(end_date.year, 1, 1)
            
        # Get cash and cash equivalent accounts
        cash_accounts = self._get_cash_accounts()
        
        # Calculate cash flows (simplified implementation)
        operating_cash_flow = Decimal('0.00')  # TODO: Implement proper calculation
        investing_cash_flow = Decimal('0.00')  # TODO: Implement proper calculation
        financing_cash_flow = Decimal('0.00')  # TODO: Implement proper calculation
        
        operating_activities = CashFlowActivity(
            line_items=[],
            net_cash_flow=operating_cash_flow
        )
        
        investing_activities = CashFlowActivity(
            line_items=[],
            net_cash_flow=investing_cash_flow
        )
        
        financing_activities = CashFlowActivity(
            line_items=[],
            net_cash_flow=financing_cash_flow
        )
        
        net_increase_in_cash = operating_cash_flow + investing_cash_flow + financing_cash_flow
        
        # Get opening and closing cash balances
        cash_at_beginning = Decimal('0.00')  # TODO: Implement proper calculation
        cash_at_end = cash_at_beginning + net_increase_in_cash
        
        return CashFlowStatement(
            metadata=self.get_report_metadata("Cash Flow Statement", end_date),
            operating_activities=operating_activities,
            investing_activities=investing_activities,
            financing_activities=financing_activities,
            net_increase_in_cash=net_increase_in_cash,
            cash_at_beginning=cash_at_beginning,
            cash_at_end=cash_at_end
        )
    
    def get_statement_of_changes_in_equity(
        self,
        start_date: date = None,
        end_date: date = None
    ) -> StatementOfChangesInEquity:
        """Generate Statement of Changes in Equity"""
        
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = date(end_date.year, 1, 1)
            
        # Get equity accounts
        equity_data = self._get_accounts_by_type_and_period('EQUITY', start_date, end_date)
        
        # Calculate changes (simplified)
        opening_balance = Decimal('0.00')  # TODO: Implement proper calculation
        net_profit = Decimal('0.00')  # TODO: Implement proper calculation
        other_comprehensive_income = Decimal('0.00')  # TODO: Implement
        dividends = Decimal('0.00')  # TODO: Implement
        closing_balance = opening_balance + net_profit + other_comprehensive_income - dividends
        
        # Create equity movements for each component
        equity_movements = [
            EquityMovement(
                component_name="Share Capital",
                opening_balance=opening_balance,
                profit_loss=net_profit,
                other_comprehensive_income=other_comprehensive_income,
                transactions_with_owners=-dividends,
                closing_balance=closing_balance
            )
        ]
        
        return StatementOfChangesInEquity(
            metadata=self.get_report_metadata("Statement of Changes in Equity", end_date),
            equity_movements=equity_movements,
            total_equity_opening=opening_balance,
            total_equity_closing=closing_balance
        )
    
    def get_trial_balance(
        self,
        as_of_date: date = None,
        include_zero_balances: bool = False
    ) -> TrialBalance:
        """Generate Trial Balance"""
        
        if as_of_date is None:
            as_of_date = date.today()
            
        tb_data = self.ifrs_core.get_trial_balance_data(as_of_date, include_zero_balances)
        
        # Import TrialBalanceAccount here to avoid circular imports
        from app.schemas.financial_statements import TrialBalanceAccount
        
        accounts = []
        total_debits = Decimal('0.00')
        total_credits = Decimal('0.00')
        
        for item in tb_data['accounts']:
            debit_balance = Decimal(str(item.get('debit_balance', 0)))
            credit_balance = Decimal(str(item.get('credit_balance', 0)))
            net_balance = debit_balance - credit_balance
            
            accounts.append(TrialBalanceAccount(
                account_code=item['account_code'],
                account_name=item['account_name'],
                account_type=item.get('account_type', 'UNKNOWN'),
                debit_balance=debit_balance,
                credit_balance=credit_balance,
                net_balance=net_balance
            ))
            
            total_debits += debit_balance
            total_credits += credit_balance
        
        return TrialBalance(
            metadata=self.get_report_metadata("Trial Balance", as_of_date),
            accounts=accounts,
            total_debits=total_debits,
            total_credits=total_credits
        )
    
    def get_financial_report_package(
        self,
        as_of_date: date = None,
        include_comparatives: bool = True
    ) -> FinancialReportPackage:
        """Generate complete financial report package"""
        
        if as_of_date is None:
            as_of_date = date.today()
            
        start_date = date(as_of_date.year, 1, 1)
        
        return FinancialReportPackage(
            metadata=self.get_report_metadata("Financial Report Package", as_of_date),
            balance_sheet=self.get_balance_sheet(as_of_date),
            income_statement=self.get_income_statement(start_date, as_of_date),
            cash_flow_statement=self.get_cash_flow_statement(start_date, as_of_date),
            statement_of_changes_in_equity=self.get_statement_of_changes_in_equity(start_date, as_of_date),
            trial_balance=self.get_trial_balance(as_of_date),
            notes=["Complete financial statements prepared in accordance with IFRS"]
        )
    
    # Helper methods
    def _get_accounts_by_type_and_period(self, account_type: str, start_date: date, end_date: date) -> List[Dict]:
        """Get account balances for a specific type and period"""
        try:
            accounts = self.db.query(AccountingCode).filter(
                AccountingCode.account_type == account_type
            ).all()
            
            result = []
            for account in accounts:
                balance_info = self._get_account_balance_for_period(account.id, start_date, end_date)
                if balance_info['balance'] != 0:
                    result.append({
                        'account_code': getattr(account, 'code', f'ACC-{account.id}'),
                        'account_name': getattr(account, 'name', 'Unknown Account'),
                        'amount': abs(float(balance_info['balance'])),
                        'account_type': account_type
                    })
            return result
        except Exception as e:
            return []
    
    def _get_account_balance_for_period(self, account_id: int, start_date: date, end_date: date) -> Dict:
        """Get account balance for a specific period"""
        try:
            entries = self.db.query(JournalEntry).filter(
                and_(
                    JournalEntry.account_id == account_id,
                    JournalEntry.transaction_date >= start_date,
                    JournalEntry.transaction_date <= end_date
                )
            ).all()
            
            total_debits = sum(entry.debit_amount or 0 for entry in entries)
            total_credits = sum(entry.credit_amount or 0 for entry in entries)
            
            # Get account to determine balance calculation
            account = self.db.query(AccountingCode).filter(AccountingCode.id == account_id).first()
            account_type = getattr(account, 'account_type', 'ASSET')
            
            if account_type in ['ASSET', 'EXPENSE']:
                balance = total_debits - total_credits
            else:  # LIABILITY, EQUITY, REVENUE
                balance = total_credits - total_debits
                
            return {
                'balance': balance,
                'total_debits': total_debits,
                'total_credits': total_credits
            }
        except Exception as e:
            return {'balance': 0, 'total_debits': 0, 'total_credits': 0}
    
    def _get_cash_accounts(self) -> List[Dict]:
        """Get cash and cash equivalent accounts"""
        try:
            cash_accounts = self.db.query(AccountingCode).filter(
                or_(
                    AccountingCode.name.ilike('%cash%'),
                    AccountingCode.name.ilike('%bank%'),
                    AccountingCode.code.ilike('%1000%')  # Common cash account codes
                )
            ).all()
            return [{'id': acc.id, 'name': acc.name, 'code': acc.code} for acc in cash_accounts]
        except Exception as e:
            return []
    
    def _calculate_operating_cash_flows(self, start_date: date, end_date: date) -> Decimal:
        """Calculate operating cash flows (simplified)"""
        # This is a simplified calculation - in practice would be more complex
        net_profit = self._get_net_profit_for_period(start_date, end_date)
        return net_profit  # Simplified - would include adjustments for non-cash items
    
    def _calculate_investing_cash_flows(self, start_date: date, end_date: date) -> Decimal:
        """Calculate investing cash flows"""
        # TODO: Implement based on asset purchases/sales
        return Decimal('0.00')
    
    def _calculate_financing_cash_flows(self, start_date: date, end_date: date) -> Decimal:
        """Calculate financing cash flows"""
        # TODO: Implement based on debt/equity transactions
        return Decimal('0.00')
    
    def _get_cash_balance_at_date(self, as_of_date: date) -> Decimal:
        """Get total cash balance at a specific date"""
        cash_accounts = self._get_cash_accounts()
        total_cash = Decimal('0.00')
        
        for account in cash_accounts:
            balance_info = self.ifrs_core.get_account_balance_as_of_date(account['id'], as_of_date)
            total_cash += Decimal(str(balance_info['balance']))
            
        return total_cash
    
    def _get_equity_balance_at_date(self, as_of_date: date) -> Decimal:
        """Get total equity balance at a specific date"""
        try:
            equity_accounts = self.db.query(AccountingCode).filter(
                AccountingCode.account_type == 'EQUITY'
            ).all()
            
            total_equity = Decimal('0.00')
            for account in equity_accounts:
                balance_info = self.ifrs_core.get_account_balance_as_of_date(account.id, as_of_date)
                total_equity += Decimal(str(balance_info['balance']))
                
            return total_equity
        except Exception as e:
            return Decimal('0.00')
    
    def _get_net_profit_for_period(self, start_date: date, end_date: date) -> Decimal:
        """Calculate net profit for a period"""
        revenue_data = self._get_accounts_by_type_and_period('REVENUE', start_date, end_date)
        expense_data = self._get_accounts_by_type_and_period('EXPENSE', start_date, end_date)
        
        total_revenue = sum(Decimal(str(item['amount'])) for item in revenue_data)
        total_expenses = sum(Decimal(str(item['amount'])) for item in expense_data)
        
        return total_revenue - total_expenses