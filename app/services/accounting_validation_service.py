from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from dataclasses import dataclass
from enum import Enum

from app.models.accounting import AccountingCode, AccountingEntry, JournalEntry, OpeningBalance
from app.services.ifrs_accounting_service import IFRSComplianceError, IFRSAccountType


class ValidationLevel(Enum):
    """Validation levels for accounting entries"""
    BASIC = "basic"
    IFRS = "ifrs"
    COMPLETE = "complete"


@dataclass
class ValidationResult:
    """Result of accounting validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    details: Dict[str, Any]


class AccountingValidationService:
    """Comprehensive accounting validation service for IFRS compliance"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def validate_accounting_entry(self, accounting_entry: AccountingEntry, level: ValidationLevel = ValidationLevel.COMPLETE) -> ValidationResult:
        """
        Validate an accounting entry for compliance
        
        Args:
            accounting_entry: The accounting entry to validate
            level: Validation level (basic, ifrs, complete)
            
        Returns:
            ValidationResult with validation details
        """
        errors = []
        warnings = []
        details = {}
        
        try:
            # Basic validation
            basic_result = self._validate_basic_compliance(accounting_entry)
            errors.extend(basic_result['errors'])
            warnings.extend(basic_result['warnings'])
            details.update(basic_result['details'])
            
            if not basic_result['is_valid']:
                return ValidationResult(
                    is_valid=False,
                    errors=errors,
                    warnings=warnings,
                    details=details
                )
            
            # IFRS validation (if required)
            if level in [ValidationLevel.IFRS, ValidationLevel.COMPLETE]:
                ifrs_result = self._validate_ifrs_compliance(accounting_entry)
                errors.extend(ifrs_result['errors'])
                warnings.extend(ifrs_result['warnings'])
                details.update(ifrs_result['details'])
            
            # Complete validation (if required)
            if level == ValidationLevel.COMPLETE:
                complete_result = self._validate_complete_compliance(accounting_entry)
                errors.extend(complete_result['errors'])
                warnings.extend(complete_result['warnings'])
                details.update(complete_result['details'])
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                details=details
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                details={}
            )
    
    def _validate_basic_compliance(self, accounting_entry: AccountingEntry) -> Dict[str, Any]:
        """Validate basic double-entry compliance"""
        errors = []
        warnings = []
        details = {}
        
        journal_entries = accounting_entry.journal_entries
        
        if not journal_entries:
            errors.append("Accounting entry must have at least one journal entry")
            return {
                'is_valid': False,
                'errors': errors,
                'warnings': warnings,
                'details': details
            }
        
        # Check double-entry principle
        total_debits = sum(je.debit_amount for je in journal_entries)
        total_credits = sum(je.credit_amount for je in journal_entries)
        
        details['total_debits'] = float(total_debits)
        details['total_credits'] = float(total_credits)
        details['balance'] = float(total_debits - total_credits)
        
        if total_debits != total_credits:
            errors.append(f"Double-entry principle violated: Debits ({total_debits}) != Credits ({total_credits})")
        
        # Check for zero amounts
        zero_amount_entries = [je for je in journal_entries if je.amount == 0]
        if zero_amount_entries:
            warnings.append(f"Found {len(zero_amount_entries)} journal entries with zero amounts")
        
        # Check for negative amounts
        negative_amount_entries = [je for je in journal_entries if je.amount < 0]
        if negative_amount_entries:
            errors.append(f"Found {len(negative_amount_entries)} journal entries with negative amounts")
        
        # Check entry types
        for je in journal_entries:
            if je.entry_type not in ['debit', 'credit']:
                errors.append(f"Invalid entry type '{je.entry_type}' for journal entry {je.id}")
            
            # Check that debit entries have debit amounts and credit entries have credit amounts
            if je.entry_type == 'debit' and je.debit_amount == 0:
                errors.append(f"Debit entry {je.id} has no debit amount")
            elif je.entry_type == 'credit' and je.credit_amount == 0:
                errors.append(f"Credit entry {je.id} has no credit amount")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'details': details
        }
    
    def _validate_ifrs_compliance(self, accounting_entry: AccountingEntry) -> Dict[str, Any]:
        """Validate IFRS compliance"""
        errors = []
        warnings = []
        details = {}
        
        journal_entries = accounting_entry.journal_entries
        
        # Check IFRS reporting tags
        missing_ifrs_tags = []
        invalid_ifrs_tags = []
        
        for je in journal_entries:
            accounting_code = je.accounting_code
            
            if not accounting_code.reporting_tag:
                missing_ifrs_tags.append(accounting_code.code)
            else:
                # Check if reporting tag is valid
                valid_tags = [
                    'A1', 'A1.1', 'A1.2', 'A1.3', 'A2', 'A2.1', 'A2.2', 'A2.3',
                    'L1', 'L1.1', 'L1.2', 'L1.3', 'L2', 'L2.1', 'L2.2',
                    'E1', 'E2', 'E3', 'R1', 'R2', 'X1', 'X2', 'X3', 'X4'
                ]
                
                if accounting_code.reporting_tag not in valid_tags:
                    invalid_ifrs_tags.append(f"{accounting_code.code}: {accounting_code.reporting_tag}")
        
        if missing_ifrs_tags:
            errors.append(f"Missing IFRS reporting tags for accounts: {', '.join(missing_ifrs_tags)}")
        
        if invalid_ifrs_tags:
            errors.append(f"Invalid IFRS reporting tags: {', '.join(invalid_ifrs_tags)}")
        
        # Check account type compliance
        account_type_issues = []
        for je in journal_entries:
            accounting_code = je.accounting_code
            account_type = accounting_code.account_type
            
            if account_type not in [at.value for at in IFRSAccountType]:
                account_type_issues.append(f"Invalid account type '{account_type}' for account {accounting_code.code}")
        
        if account_type_issues:
            errors.extend(account_type_issues)
        
        details['missing_ifrs_tags'] = missing_ifrs_tags
        details['invalid_ifrs_tags'] = invalid_ifrs_tags
        details['account_type_issues'] = account_type_issues
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'details': details
        }
    
    def _validate_complete_compliance(self, accounting_entry: AccountingEntry) -> Dict[str, Any]:
        """Validate complete compliance including business rules"""
        errors = []
        warnings = []
        details = {}
        
        journal_entries = accounting_entry.journal_entries
        
        # Check for balanced entries (same account on both sides)
        account_entries = {}
        for je in journal_entries:
            account_id = je.accounting_code_id
            if account_id not in account_entries:
                account_entries[account_id] = []
            account_entries[account_id].append(je)
        
        self_balanced_accounts = []
        for account_id, entries in account_entries.items():
            if len(entries) > 1:
                total_debit = sum(je.debit_amount for je in entries)
                total_credit = sum(je.credit_amount for je in entries)
                if total_debit == total_credit and total_debit > 0:
                    self_balanced_accounts.append(account_id)
        
        if self_balanced_accounts:
            warnings.append(f"Self-balanced entries detected for accounts: {self_balanced_accounts}")
        
        # Check for unusual entry patterns
        unusual_patterns = self._check_unusual_patterns(journal_entries)
        if unusual_patterns:
            warnings.extend(unusual_patterns)
        
        # Check for proper date consistency
        date_issues = self._check_date_consistency(accounting_entry)
        if date_issues:
            errors.extend(date_issues)
        
        details['self_balanced_accounts'] = self_balanced_accounts
        details['unusual_patterns'] = unusual_patterns
        details['date_issues'] = date_issues
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'details': details
        }
    
    def _check_unusual_patterns(self, journal_entries: List[JournalEntry]) -> List[str]:
        """Check for unusual accounting patterns"""
        warnings = []
        
        # Check for round numbers (might indicate estimates)
        round_numbers = []
        for je in journal_entries:
            amount = je.amount
            if amount > 0 and amount % 1000 == 0:
                round_numbers.append(f"{je.accounting_code.code}: {amount}")
        
        if round_numbers:
            warnings.append(f"Round number amounts detected: {', '.join(round_numbers)}")
        
        # Check for very large amounts
        large_amounts = []
        for je in journal_entries:
            if je.amount > 1000000:  # 1 million
                large_amounts.append(f"{je.accounting_code.code}: {je.amount}")
        
        if large_amounts:
            warnings.append(f"Large amounts detected: {', '.join(large_amounts)}")
        
        return warnings
    
    def _check_date_consistency(self, accounting_entry: AccountingEntry) -> List[str]:
        """Check for date consistency issues"""
        errors = []
        
        # Check that posted date is not in the future
        if accounting_entry.date_posted > date.today():
            errors.append("Accounting entry posted date is in the future")
        
        # Check that prepared date is not after posted date
        if accounting_entry.date_prepared > accounting_entry.date_posted:
            errors.append("Accounting entry prepared date is after posted date")
        
        return errors
    
    def validate_account_balance(self, accounting_code: AccountingCode, as_of_date: date = None) -> ValidationResult:
        """Validate account balance for IFRS compliance"""
        if not as_of_date:
            as_of_date = date.today()
        
        errors = []
        warnings = []
        details = {}
        
        try:
            # Get opening balance
            opening_balance = self.db.query(func.sum(OpeningBalance.amount)).filter(
                and_(
                    OpeningBalance.accounting_code_id == accounting_code.id,
                    OpeningBalance.year == as_of_date.year
                )
            ).scalar() or Decimal('0')
            
            # Get journal entries
            journal_entries = self.db.query(JournalEntry).join(AccountingEntry).filter(
                and_(
                    JournalEntry.accounting_code_id == accounting_code.id,
                    AccountingEntry.date_posted <= as_of_date,
                    AccountingEntry.branch_id == accounting_code.branch_id
                )
            ).all()
            
            # Calculate balance
            movement = sum(je.debit_amount - je.credit_amount for je in journal_entries)
            
            # Determine normal balance
            account_rules = IFRSAccountingService.IFRS_ACCOUNT_RULES[IFRSAccountType(accounting_code.account_type)]
            normal_balance = account_rules['normal_balance']
            
            if normal_balance == 'debit':
                balance = opening_balance + movement
            else:
                balance = opening_balance - movement
            
            details['opening_balance'] = float(opening_balance)
            details['movement'] = float(movement)
            details['current_balance'] = float(balance)
            details['normal_balance'] = normal_balance
            
            # Check for unusual balance patterns
            if accounting_code.account_type == 'Asset' and balance < 0:
                warnings.append("Asset account has negative balance")
            
            if accounting_code.account_type == 'Liability' and balance < 0:
                warnings.append("Liability account has negative balance")
            
            if accounting_code.account_type == 'Equity' and balance < 0:
                warnings.append("Equity account has negative balance")
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                details=details
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Error validating account balance: {str(e)}"],
                warnings=[],
                details={}
            )
    
    def validate_trial_balance(self, branch_id: str, as_of_date: date = None) -> ValidationResult:
        """Validate trial balance for IFRS compliance"""
        if not as_of_date:
            as_of_date = date.today()
        
        errors = []
        warnings = []
        details = {}
        
        try:
            # Get all accounts for the branch
            accounts = self.db.query(AccountingCode).filter(
                AccountingCode.branch_id == branch_id
            ).all()
            
            total_debits = Decimal('0')
            total_credits = Decimal('0')
            account_balances = []
            
            for account in accounts:
                # Get account balance
                balance_result = self.validate_account_balance(account, as_of_date)
                
                if balance_result.is_valid:
                    balance = balance_result.details['current_balance']
                    account_balances.append({
                        'account_code': account.code,
                        'account_name': account.name,
                        'balance': balance,
                        'account_type': account.account_type
                    })
                    
                    if balance > 0:
                        total_debits += balance
                    else:
                        total_credits += abs(balance)
                else:
                    errors.extend(balance_result.errors)
            
            details['total_debits'] = float(total_debits)
            details['total_credits'] = float(total_credits)
            details['difference'] = float(total_debits - total_credits)
            details['account_balances'] = account_balances
            
            # Check if trial balance balances
            if total_debits != total_credits:
                errors.append(f"Trial balance does not balance: Debits ({total_debits}) != Credits ({total_credits})")
            
            # Check for unusual patterns
            if total_debits == 0 and total_credits == 0:
                warnings.append("Trial balance shows zero activity")
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                details=details
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Error validating trial balance: {str(e)}"],
                warnings=[],
                details={}
            )
    
    def validate_ifrs_reporting(self, branch_id: str, as_of_date: date = None) -> ValidationResult:
        """Validate IFRS reporting compliance"""
        if not as_of_date:
            as_of_date = date.today()
        
        errors = []
        warnings = []
        details = {}
        
        try:
            # Check required IFRS categories
            required_categories = [
                'A1.1',  # Cash and Cash Equivalents
                'A1.2',  # Trade and Other Receivables
                'A1.3',  # Inventories
                'L1.1',  # Trade and Other Payables
                'E2',    # Retained Earnings
                'R1',    # Revenue from Contracts with Customers
                'X1'     # Cost of Sales
            ]
            
            missing_categories = []
            for category in required_categories:
                account = self.db.query(AccountingCode).filter(
                    and_(
                        AccountingCode.reporting_tag == category,
                        AccountingCode.branch_id == branch_id
                    )
                ).first()
                
                if not account:
                    missing_categories.append(category)
            
            if missing_categories:
                errors.append(f"Missing required IFRS categories: {', '.join(missing_categories)}")
            
            # Check for accounts without IFRS tags
            untagged_accounts = self.db.query(AccountingCode).filter(
                and_(
                    AccountingCode.branch_id == branch_id,
                    AccountingCode.reporting_tag.is_(None)
                )
            ).all()
            
            if untagged_accounts:
                warnings.append(f"Found {len(untagged_accounts)} accounts without IFRS reporting tags")
            
            details['missing_categories'] = missing_categories
            details['untagged_accounts'] = [acc.code for acc in untagged_accounts]
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                details=details
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Error validating IFRS reporting: {str(e)}"],
                warnings=[],
                details={}
            )
    
    def get_validation_summary(self, branch_id: str, start_date: date = None, end_date: date = None) -> Dict[str, Any]:
        """Get comprehensive validation summary for a period"""
        if not start_date:
            start_date = date.today().replace(day=1)
        if not end_date:
            end_date = date.today()
        
        summary = {
            'period': {'start_date': start_date, 'end_date': end_date},
            'total_entries': 0,
            'valid_entries': 0,
            'invalid_entries': 0,
            'total_errors': 0,
            'total_warnings': 0,
            'common_errors': [],
            'validation_details': {}
        }
        
        # Get all accounting entries for the period
        accounting_entries = self.db.query(AccountingEntry).filter(
            and_(
                AccountingEntry.branch_id == branch_id,
                AccountingEntry.date_posted >= start_date,
                AccountingEntry.date_posted <= end_date
            )
        ).all()
        
        error_counts = {}
        
        for entry in accounting_entries:
            summary['total_entries'] += 1
            
            validation_result = self.validate_accounting_entry(entry, ValidationLevel.COMPLETE)
            
            if validation_result.is_valid:
                summary['valid_entries'] += 1
            else:
                summary['invalid_entries'] += 1
            
            summary['total_errors'] += len(validation_result.errors)
            summary['total_warnings'] += len(validation_result.warnings)
            
            # Count common errors
            for error in validation_result.errors:
                if error in error_counts:
                    error_counts[error] += 1
                else:
                    error_counts[error] = 1
        
        # Get top common errors
        summary['common_errors'] = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Add trial balance validation
        trial_balance_result = self.validate_trial_balance(branch_id, end_date)
        summary['validation_details']['trial_balance'] = {
            'is_valid': trial_balance_result.is_valid,
            'errors': trial_balance_result.errors,
            'warnings': trial_balance_result.warnings
        }
        
        # Add IFRS reporting validation
        ifrs_result = self.validate_ifrs_reporting(branch_id, end_date)
        summary['validation_details']['ifrs_reporting'] = {
            'is_valid': ifrs_result.is_valid,
            'errors': ifrs_result.errors,
            'warnings': ifrs_result.warnings
        }
        
        return summary 