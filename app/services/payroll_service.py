from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.user import User
from app.models.accounting import AccountingCode, AccountingEntry, JournalEntry
from app.core.config import settings


class PayrollService:
    """Comprehensive payroll business logic service with IFRS compliance"""
    
    PAYROLL_STATUSES = ['pending', 'processed', 'paid', 'cancelled']
    PAYMENT_METHODS = ['bank_transfer', 'cash', 'check']
    
    def __init__(self, db: Session):
        self.db = db
    
    def process_payroll(self, payroll_data: Dict, employees: List[Dict], branch_id: str) -> Tuple[Dict, Dict]:
        """
        Process payroll for multiple employees with comprehensive accounting integration
        
        Args:
            payroll_data: Payroll header data (period, payment date, etc.)
            employees: List of employee payroll data
            branch_id: Branch ID
            
        Returns:
            Tuple of (payroll_result, result_dict)
        """
        try:
            # Validate payroll data
            self._validate_payroll_data(payroll_data, employees)
            
            # Create payroll accounting entry
            accounting_entry = AccountingEntry(
                date_prepared=payroll_data.get('payment_date', date.today()),
                date_posted=payroll_data.get('payment_date', date.today()),
                particulars=f"Payroll for {payroll_data.get('period', 'Current Period')}",
                book=f"PAYROLL-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                status='posted',
                branch_id=branch_id
            )
            
            self.db.add(accounting_entry)
            self.db.flush()
            
            total_gross_pay = Decimal('0')
            total_net_pay = Decimal('0')
            total_tax = Decimal('0')
            total_pension = Decimal('0')
            total_other_deductions = Decimal('0')
            
            journal_entries = []
            
            for employee_data in employees:
                employee = self.db.query(User).filter(
                    User.id == employee_data['employee_id'],
                    User.branch_id == branch_id
                ).first()
                
                if not employee:
                    raise ValueError(f"Employee {employee_data['employee_id']} not found")
                
                # Calculate payroll components
                gross_pay = Decimal(str(employee_data['gross_pay']))
                tax_amount = Decimal(str(employee_data.get('tax_amount', 0)))
                pension_amount = Decimal(str(employee_data.get('pension_amount', 0)))
                other_deductions = Decimal(str(employee_data.get('other_deductions', 0)))
                net_pay = gross_pay - tax_amount - pension_amount - other_deductions
                
                # Create journal entries for this employee
                employee_entries = self._create_employee_payroll_entries(
                    accounting_entry, employee, gross_pay, net_pay, tax_amount, 
                    pension_amount, other_deductions, payroll_data.get('payment_method', 'bank_transfer')
                )
                
                journal_entries.extend(employee_entries)
                
                total_gross_pay += gross_pay
                total_net_pay += net_pay
                total_tax += tax_amount
                total_pension += pension_amount
                total_other_deductions += other_deductions
            
            # Validate double-entry compliance
            self._validate_payroll_entries(journal_entries)
            
            # Add all journal entries to database
            for entry in journal_entries:
                self.db.add(entry)
            
            self.db.commit()
            
            payroll_result = {
                'payroll_id': str(accounting_entry.id),
                'period': payroll_data.get('period'),
                'payment_date': payroll_data.get('payment_date'),
                'total_employees': len(employees),
                'total_gross_pay': total_gross_pay,
                'total_net_pay': total_net_pay,
                'total_tax': total_tax,
                'total_pension': total_pension,
                'total_other_deductions': total_other_deductions
            }
            
            return payroll_result, {'success': True, 'payroll_id': str(accounting_entry.id)}
            
        except Exception as e:
            self.db.rollback()
            return None, {'success': False, 'error': str(e)}
    
    def _validate_payroll_data(self, payroll_data: Dict, employees: List[Dict]) -> None:
        """Validate payroll data"""
        if not payroll_data.get('period'):
            raise ValueError("Payroll period is required")
        
        if not employees:
            raise ValueError("At least one employee is required")
        
        for employee in employees:
            if not employee.get('employee_id'):
                raise ValueError("Employee ID is required for all employees")
            if not employee.get('gross_pay') or Decimal(str(employee['gross_pay'])) <= 0:
                raise ValueError("Valid gross pay is required for all employees")
    
    def _create_employee_payroll_entries(self, accounting_entry: AccountingEntry, employee: User, 
                                       gross_pay: Decimal, net_pay: Decimal, tax_amount: Decimal,
                                       pension_amount: Decimal, other_deductions: Decimal, 
                                       payment_method: str) -> List[JournalEntry]:
        """Create journal entries for employee payroll"""
        entries = []
        
        # Get required accounting codes
        salary_expense = self._get_accounting_code('Salaries and Wages', 'Expense')
        cash_account = self._get_accounting_code('Cash', 'Asset')
        bank_account = self._get_accounting_code('Bank Account', 'Asset')
        tax_payable = self._get_accounting_code('Tax Payable', 'Liability')
        pension_payable = self._get_accounting_code('Pension Payable', 'Liability')
        other_payables = self._get_accounting_code('Other Payables', 'Liability')
        
        # 1. Debit Salary Expense
        salary_entry = JournalEntry(
            accounting_entry_id=accounting_entry.id,
            accounting_code_id=salary_expense.id,
            entry_type='debit',
            amount=gross_pay,
            description=f"Salary expense for {employee.first_name} {employee.last_name}",
            date=accounting_entry.date_prepared,
            date_posted=accounting_entry.date_posted,
            branch_id=accounting_entry.branch_id
        )
        salary_entry.debit_amount = gross_pay
        salary_entry.credit_amount = Decimal('0')
        entries.append(salary_entry)
        
        # 2. Credit Cash/Bank for net pay
        payment_account = bank_account if payment_method == 'bank_transfer' else cash_account
        payment_entry = JournalEntry(
            accounting_entry_id=accounting_entry.id,
            accounting_code_id=payment_account.id,
            entry_type='credit',
            amount=net_pay,
            description=f"Net pay to {employee.first_name} {employee.last_name}",
            date=accounting_entry.date_prepared,
            date_posted=accounting_entry.date_posted,
            branch_id=accounting_entry.branch_id
        )
        payment_entry.credit_amount = net_pay
        payment_entry.debit_amount = Decimal('0')
        entries.append(payment_entry)
        
        # 3. Credit Tax Payable (if applicable)
        if tax_amount > 0:
            tax_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=tax_payable.id,
                entry_type='credit',
                amount=tax_amount,
                description=f"Tax deduction for {employee.first_name} {employee.last_name}",
                date=accounting_entry.date_prepared,
                date_posted=accounting_entry.date_posted,
                branch_id=accounting_entry.branch_id
            )
            tax_entry.credit_amount = tax_amount
            tax_entry.debit_amount = Decimal('0')
            entries.append(tax_entry)
        
        # 4. Credit Pension Payable (if applicable)
        if pension_amount > 0:
            pension_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=pension_payable.id,
                entry_type='credit',
                amount=pension_amount,
                description=f"Pension deduction for {employee.first_name} {employee.last_name}",
                date=accounting_entry.date_prepared,
                date_posted=accounting_entry.date_posted,
                branch_id=accounting_entry.branch_id
            )
            pension_entry.credit_amount = pension_amount
            pension_entry.debit_amount = Decimal('0')
            entries.append(pension_entry)
        
        # 5. Credit Other Payables (if applicable)
        if other_deductions > 0:
            other_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=other_payables.id,
                entry_type='credit',
                amount=other_deductions,
                description=f"Other deductions for {employee.first_name} {employee.last_name}",
                date=accounting_entry.date_prepared,
                date_posted=accounting_entry.date_posted,
                branch_id=accounting_entry.branch_id
            )
            other_entry.credit_amount = other_deductions
            other_entry.debit_amount = Decimal('0')
            entries.append(other_entry)
        
        return entries
    
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
    
    def _validate_payroll_entries(self, journal_entries: List[JournalEntry]) -> None:
        """Validate that payroll entries balance (debits = credits)"""
        total_debits = sum(entry.debit_amount for entry in journal_entries)
        total_credits = sum(entry.credit_amount for entry in journal_entries)
        
        if total_debits != total_credits:
            raise ValueError(f"Payroll entries do not balance: Debits {total_debits} != Credits {total_credits}")
    
    def get_payroll_summary(self, branch_id: str, start_date: date = None, end_date: date = None) -> Dict:
        """Get comprehensive payroll summary"""
        try:
            query = self.db.query(AccountingEntry).filter(
                AccountingEntry.book.like('PAYROLL-%'),
                AccountingEntry.branch_id == branch_id
            )
            
            if start_date:
                query = query.filter(AccountingEntry.date_prepared >= start_date)
            if end_date:
                query = query.filter(AccountingEntry.date_prepared <= end_date)
            
            payroll_entries = query.all()
            
            total_gross_pay = Decimal('0')
            total_net_pay = Decimal('0')
            total_tax = Decimal('0')
            total_pension = Decimal('0')
            
            for entry in payroll_entries:
                # Get journal entries for this payroll
                journal_entries = self.db.query(JournalEntry).filter(
                    JournalEntry.accounting_entry_id == entry.id
                ).all()
                
                for je in journal_entries:
                    if je.accounting_code.name == 'Salaries and Wages':
                        total_gross_pay += je.debit_amount
                    elif je.accounting_code.name == 'Tax Payable':
                        total_tax += je.credit_amount
                    elif je.accounting_code.name == 'Pension Payable':
                        total_pension += je.credit_amount
                    elif je.accounting_code.name in ['Cash', 'Bank Account']:
                        total_net_pay += je.credit_amount
            
            return {
                'total_payroll_runs': len(payroll_entries),
                'total_gross_pay': total_gross_pay,
                'total_net_pay': total_net_pay,
                'total_tax': total_tax,
                'total_pension': total_pension,
                'period': f"{start_date} to {end_date}" if start_date and end_date else "All time"
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def get_employee_payroll_history(self, employee_id: str, branch_id: str, 
                                   start_date: date = None, end_date: date = None) -> List[Dict]:
        """Get payroll history for a specific employee"""
        try:
            employee = self.db.query(User).filter(
                User.id == employee_id,
                User.branch_id == branch_id
            ).first()
            
            if not employee:
                return []
            
            # Get payroll entries that include this employee
            query = self.db.query(AccountingEntry).filter(
                AccountingEntry.book.like('PAYROLL-%'),
                AccountingEntry.branch_id == branch_id
            )
            
            if start_date:
                query = query.filter(AccountingEntry.date_prepared >= start_date)
            if end_date:
                query = query.filter(AccountingEntry.date_prepared <= end_date)
            
            payroll_entries = query.all()
            
            payroll_history = []
            
            for entry in payroll_entries:
                # Check if this payroll includes the employee
                employee_entries = self.db.query(JournalEntry).filter(
                    JournalEntry.accounting_entry_id == entry.id,
                    JournalEntry.description.like(f"%{employee.first_name} {employee.last_name}%")
                ).all()
                
                if employee_entries:
                    gross_pay = Decimal('0')
                    net_pay = Decimal('0')
                    tax_amount = Decimal('0')
                    pension_amount = Decimal('0')
                    
                    for je in employee_entries:
                        if je.accounting_code.name == 'Salaries and Wages':
                            gross_pay = je.debit_amount
                        elif je.accounting_code.name == 'Tax Payable':
                            tax_amount = je.credit_amount
                        elif je.accounting_code.name == 'Pension Payable':
                            pension_amount = je.credit_amount
                        elif je.accounting_code.name in ['Cash', 'Bank Account']:
                            net_pay = je.credit_amount
                    
                    payroll_history.append({
                        'payroll_date': entry.date_prepared,
                        'period': entry.particulars,
                        'gross_pay': gross_pay,
                        'net_pay': net_pay,
                        'tax_amount': tax_amount,
                        'pension_amount': pension_amount
                    })
            
            return payroll_history
            
        except Exception as e:
            return []
    
    def create_salary_advance(self, advance_data: Dict, branch_id: str) -> Tuple[Dict, Dict]:
        """Create salary advance with accounting entries"""
        try:
            employee = self.db.query(User).filter(
                User.id == advance_data['employee_id'],
                User.branch_id == branch_id
            ).first()
            
            if not employee:
                return None, {'success': False, 'error': 'Employee not found'}
            
            advance_amount = Decimal(str(advance_data['amount']))
            
            # Create accounting entry
            accounting_entry = AccountingEntry(
                date_prepared=date.today(),
                date_posted=date.today(),
                particulars=f"Salary advance for {employee.first_name} {employee.last_name}",
                book=f"ADVANCE-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                status='posted',
                branch_id=branch_id
            )
            
            self.db.add(accounting_entry)
            self.db.flush()
            
            # Get accounting codes
            salary_advance = self._get_accounting_code('Salary Advances', 'Asset')
            cash_account = self._get_accounting_code('Cash', 'Asset')
            bank_account = self._get_accounting_code('Bank Account', 'Asset')
            
            payment_method = advance_data.get('payment_method', 'bank_transfer')
            payment_account = bank_account if payment_method == 'bank_transfer' else cash_account
            
            # Create journal entries
            # 1. Debit Salary Advances
            advance_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=salary_advance.id,
                entry_type='debit',
                amount=advance_amount,
                description=f"Salary advance to {employee.first_name} {employee.last_name}",
                date=date.today(),
                date_posted=date.today(),
                branch_id=branch_id
            )
            advance_entry.debit_amount = advance_amount
            advance_entry.credit_amount = Decimal('0')
            self.db.add(advance_entry)
            
            # 2. Credit Cash/Bank
            payment_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=payment_account.id,
                entry_type='credit',
                amount=advance_amount,
                description=f"Salary advance payment to {employee.first_name} {employee.last_name}",
                date=date.today(),
                date_posted=date.today(),
                branch_id=branch_id
            )
            payment_entry.credit_amount = advance_amount
            payment_entry.debit_amount = Decimal('0')
            self.db.add(payment_entry)
            
            self.db.commit()
            
            return {
                'advance_id': str(accounting_entry.id),
                'employee_name': f"{employee.first_name} {employee.last_name}",
                'amount': advance_amount,
                'payment_method': payment_method,
                'date': date.today()
            }, {'success': True, 'advance_id': str(accounting_entry.id)}
            
        except Exception as e:
            self.db.rollback()
            return None, {'success': False, 'error': str(e)} 