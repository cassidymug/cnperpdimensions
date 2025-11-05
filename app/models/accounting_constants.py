"""
Constants and utilities for accounting types and categories.

This module defines the valid account types, their categories, and provides
utility functions for working with accounting codes.
"""
from typing import List, Dict, Optional, Set
from enum import Enum

class NormalBalance(str, Enum):
    """Represents the normal balance of an account (debit or credit)."""
    DEBIT = 'debit'
    CREDIT = 'credit'

class AccountType(str, Enum):
    """Valid account types in the accounting system."""
    ASSET = 'Asset'
    LIABILITY = 'Liability'
    EQUITY = 'Equity'
    REVENUE = 'Revenue'
    EXPENSE = 'Expense'

# Account types with their normal balance and description
ACCOUNT_TYPES: Dict[str, Dict[str, str]] = {
    AccountType.ASSET: {
        'normal_balance': NormalBalance.DEBIT,
        'description': "Resources owned by the business that provide future economic benefits."
    },
    AccountType.LIABILITY: {
        'normal_balance': NormalBalance.CREDIT,
        'description': "Present obligations arising from past events, expected to result in an outflow of resources."
    },
    AccountType.EQUITY: {
        'normal_balance': NormalBalance.CREDIT,
        'description': "The residual interest in the assets of the entity after deducting all its liabilities."
    },
    AccountType.REVENUE: {
        'normal_balance': NormalBalance.CREDIT,
        'description': "Increases in economic benefits during the accounting period in the form of inflows or enhancements of assets or decreases of liabilities."
    },
    AccountType.EXPENSE: {
        'normal_balance': NormalBalance.DEBIT,
        'description': "Decreases in economic benefits during the accounting period in the form of outflows or depletions of assets or incurrences of liabilities."
    }
}

# Categories for each account type
CATEGORIES: Dict[AccountType, List[str]] = {
    AccountType.ASSET: [
        'Current Asset', 'Fixed Asset', 'Inventory', 'Trade Receivables', 'Cash', 'Bank',
        'Prepaid Expenses', 'Investments', 'Intangible Assets', 'Accumulated Depreciation'
    ],
    AccountType.LIABILITY: [
        'Current Liability', 'Long-Term Liability', 'Trade Payables', 
        'Accrued Liabilities', 'VAT Payable', 'Tax Payable', 'Loans Payable',
        'Deferred Revenue', 'Notes Payable'
    ],
    AccountType.EQUITY: [
        'Equity Capital', 'Retained Earnings', 'Opening Balance Equity', 
        'Owner Equity', 'Common Stock', 'Preferred Stock', 'Treasury Stock',
        'Dividends', 'Drawings'
    ],
    AccountType.REVENUE: [
        'Sales Revenue', 'Service Revenue', 'Other Revenue', 'Operating Revenue',
        'Interest Income', 'Rental Income', 'Dividend Income', 'Gain on Sale of Assets'
    ],
    AccountType.EXPENSE: [
        'Operating Expense', 'Depreciation', 'Cost of Sales', 'Tax Expense',
        'Salaries and Wages', 'Rent Expense', 'Utilities', 'Insurance',
        'Office Supplies', 'Marketing', 'Professional Fees', 'Interest Expense',
        'Repairs and Maintenance', 'Travel Expense', 'Bad Debts'
    ]
}

def get_all_categories() -> Set[str]:
    """Get all unique category names across all account types."""
    return {cat for sublist in CATEGORIES.values() for cat in sublist}

def get_categories_for_type(account_type: AccountType) -> List[str]:
    """Get all valid categories for a specific account type."""
    return CATEGORIES.get(account_type, [])

def validate_account_type(account_type: str) -> bool:
    """
    Validate if the account type is valid.
    
    Args:
        account_type: The account type to validate
        
    Returns:
        bool: True if the account type is valid, False otherwise
    """
    return account_type in ACCOUNT_TYPES

def validate_category(account_type: str, category: str) -> bool:
    """
    Validate if the category is valid for the given account type.
    
    Args:
        account_type: The account type to validate against
        category: The category to validate
        
    Returns:
        bool: True if the category is valid for the account type, False otherwise
    """
    return category in CATEGORIES.get(account_type, [])

def get_normal_balance(account_type: str) -> Optional[str]:
    """
    Get the normal balance (debit/credit) for an account type.
    
    Args:
        account_type: The account type
        
    Returns:
        str: 'debit' or 'credit' if valid, None otherwise
    """
    return ACCOUNT_TYPES.get(account_type, {}).get('normal_balance')

def get_account_type_description(account_type: str) -> str:
    """
    Get the description for an account type.
    
    Args:
        account_type: The account type
        
    Returns:
        str: The description of the account type, or empty string if not found
    """
    return ACCOUNT_TYPES.get(account_type, {}).get('description', '')

def is_debit_account(account_type: str) -> bool:
    """Check if the account type is a debit account (increases with debits)."""
    return get_normal_balance(account_type) == NormalBalance.DEBIT

def is_credit_account(account_type: str) -> bool:
    """Check if the account type is a credit account (increases with credits)."""
    return get_normal_balance(account_type) == NormalBalance.CREDIT

def get_all_account_types() -> List[str]:
    """Get a list of all valid account types."""
    return list(ACCOUNT_TYPES.keys())

def get_category_account_type(category: str) -> Optional[str]:
    """
    Get the account type for a given category.
    
    Args:
        category: The category to look up
        
    Returns:
        str: The account type that contains this category, or None if not found
    """
    for acc_type, categories in CATEGORIES.items():
        if category in categories:
            return acc_type
    return None
