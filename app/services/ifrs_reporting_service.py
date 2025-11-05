#!/usr/bin/env python3
"""
IFRS Reporting Tags Service
Automatically generates IFRS reporting tags based on account type and category
"""

from typing import Optional, Dict, Any, Iterable, Tuple

class IFRSReportingService:
    """Service for automatically generating IFRS reporting tags"""
    
    # IFRS Reporting Tags for automatic assignment
    IFRS_REPORTING_TAGS = {
        'Asset': {
            'group': 'A1',              # Parent asset buckets default to current assets
            'detail': 'A1',             # Generic detail nodes default to current assets
            'Current Asset': 'A1',
            'Prepaid Assets': 'A1',
            'Inventory': 'A1.3',        # Inventories
            'Trade Receivables': 'A1.2', # Trade and Other Receivables
            'Tax Assets': 'A1.2',       # Treated as receivables/current assets
            'Cash': 'A1.1',             # Cash and Cash Equivalents
            'Bank': 'A1.1',             # Cash and Cash Equivalents
            'Fixed Asset': 'A2.1',      # Property, Plant and Equipment
            'Contra Asset': 'A2.1',     # Accumulated depreciation (contra PPE)
            'Intangible Asset': 'A2.2'  # Intangible Assets
        },
        'Liability': {
            'group': 'L1',
            'detail': 'L1',
            'Current Liability': 'L1',      # Current Liabilities
            'Trade Payables': 'L1.1',       # Trade and Other Payables
            'Accrued Liabilities': 'L1.2',  # Accrued Liabilities
            'Tax Payables': 'L1.3',         # Current Tax Liabilities
            'Short-term Debt': 'L1.2',      # Short-term borrowings
            'Customer Deposits': 'L1.1',    # Treated as other current liabilities
            'Long-term Debt': 'L2.1',       # Long-term borrowings
            'Long-Term Liability': 'L2',    # Generic non-current liabilities
        },
        'Equity': {
            'group': 'E1',
            'detail': 'E1',
            'Equity Capital': 'E1',         # Share Capital
            'Retained Earnings': 'E2',      # Retained Earnings
            'Capital Reserves': 'E3',       # Other Equity / Reserves
        },
        'Revenue': {
            'group': 'R1',
            'detail': 'R1',
            'Sales Revenue': 'R1',        # Revenue from Contracts with Customers
            'Service Revenue': 'R1',      # Revenue from Contracts with Customers
            'Operating Revenue': 'R1',    # Revenue from Contracts with Customers
            'Other Revenue': 'R2'         # Other Income
        },
        'Expense': {
            'group': 'X1',
            'detail': 'X1',
            'Cost of Sales': 'X1',        # Cost of Sales
            'Operating Expense': 'X2',    # Selling & distribution expenses
            'Administrative Expense': 'X3',
            'Other Expense': 'X4',        # Finance/other expenses
            'Depreciation': 'X3',         # Included under administrative expenses
            'Tax Expense': 'X4'           # Finance costs / tax expenses
        }
    }

    DEFAULT_TAGS = {
        'Asset': 'A1',
        'Liability': 'L1',
        'Equity': 'E1',
        'Revenue': 'R1',
        'Expense': 'X1'
    }

    VALID_IFRS_TAGS = {
        'A1', 'A1.1', 'A1.2', 'A1.3', 'A2', 'A2.1', 'A2.2', 'A2.3',
        'L1', 'L1.1', 'L1.2', 'L1.3', 'L2', 'L2.1', 'L2.2',
        'E1', 'E2', 'E3',
        'R1', 'R2',
        'X1', 'X2', 'X3', 'X4'
    }

    CODE_TAG_OVERRIDES = {
        # Asset hierarchy
        '1000': 'A1', '1100': 'A1', '1110': 'A1.1', '1111': 'A1.1', '1112': 'A1.1', '1113': 'A1.1',
        '1120': 'A1.1', '1121': 'A1.1', '1122': 'A1.1', '1123': 'A1.1', '1124': 'A1.1',
        '1130': 'A1.2', '1131': 'A1.2', '1132': 'A1.2', '1133': 'A1.2', '1134': 'A1.2',
        '1140': 'A1.3', '1141': 'A1.3', '1142': 'A1.3', '1143': 'A1.3', '1144': 'A1.3',
        '1150': 'A1', '1151': 'A1', '1152': 'A1', '1153': 'A1',
        '1160': 'A1', '1161': 'A1.2', '1162': 'A1.2', '1163': 'A1',
        '1200': 'A2', '1210': 'A2.1', '1211': 'A2.1', '1212': 'A2.1', '1213': 'A2.1',
        '1214': 'A2.1', '1215': 'A2.1', '1220': 'A2.1', '1221': 'A2.1', '1222': 'A2.1',
        '1223': 'A2.1', '1224': 'A2.1', '1225': 'A2.1', '1230': 'A2.2', '1231': 'A2.2',
        '1232': 'A2.2', '1233': 'A2.2',
        # Liability hierarchy
        '2000': 'L1', '2100': 'L1', '2110': 'L1.1', '2111': 'L1.1', '2112': 'L1.1', '2113': 'L1.1',
        '2120': 'L1.2', '2121': 'L1.2', '2122': 'L1.2', '2123': 'L1.2',
        '2130': 'L1.3', '2131': 'L1.3', '2132': 'L1.3', '2133': 'L1.3', '2134': 'L1.3',
        '2140': 'L1.2', '2150': 'L1.1', '2200': 'L2', '2210': 'L2.1', '2220': 'L2.1', '2230': 'L2.1',
        # Equity hierarchy
        '3000': 'E1', '3100': 'E1', '3101': 'E1', '3102': 'E1',
        '3200': 'E2', '3201': 'E2', '3202': 'E2',
        '3300': 'E3', '3301': 'E3', '3302': 'E3',
        # Revenue hierarchy
        '4000': 'R1', '4100': 'R1', '4101': 'R1', '4102': 'R1', '4103': 'R1', '4104': 'R1',
        '4200': 'R2', '4201': 'R2', '4202': 'R2', '4203': 'R2', '4204': 'R2',
        # Expense hierarchy
        '5000': 'X1', '5100': 'X1', '5101': 'X1', '5102': 'X1', '5103': 'X1', '5104': 'X1', '5105': 'X1',
        '5200': 'X2', '5210': 'X2', '5211': 'X2', '5212': 'X2', '5213': 'X2', '5214': 'X2', '5215': 'X2',
        '5220': 'X3', '5221': 'X3', '5222': 'X3', '5223': 'X3', '5224': 'X3', '5225': 'X3',
        '5226': 'X3', '5227': 'X3', '5228': 'X3', '5229': 'X3', '5230': 'X3',
        '5231': 'X3', '5232': 'X3', '5233': 'X3',
        '5300': 'X4', '5301': 'X4', '5302': 'X4', '5303': 'X4',
    }

    NAME_KEYWORD_TAGS: Iterable[Tuple[str, str]] = (
        ('cash', 'A1.1'),
        ('bank', 'A1.1'),
        ('receivable', 'A1.2'),
        ('advance', 'A1.2'),
        ('inventory', 'A1.3'),
        ('raw material', 'A1.3'),
        ('work in progress', 'A1.3'),
        ('finished goods', 'A1.3'),
        ('prepaid', 'A1'),
        ('tax', 'A1.2'),
        ('property', 'A2.1'),
        ('plant', 'A2.1'),
        ('equipment', 'A2.1'),
        ('depreciation', 'A2.1'),
        ('intangible', 'A2.2'),
        ('goodwill', 'A2.2'),
        ('accounts payable', 'L1.1'),
        ('payable', 'L1.1'),
        ('accrued', 'L1.2'),
        ('vat', 'L1.3'),
        ('tax payable', 'L1.3'),
        ('short-term loan', 'L1.2'),
        ('customer deposit', 'L1.1'),
        ('long-term loan', 'L2.1'),
        ('mortgage', 'L2.1'),
        ('loan', 'L2.1'),
        ('share capital', 'E1'),
        ('capital reserve', 'E3'),
        ('retained earnings', 'E2'),
        ('revenue', 'R1'),
        ('interest income', 'R2'),
        ('commission income', 'R2'),
        ('rental income', 'R2'),
        ('cost of goods', 'X1'),
        ('purchase', 'X1'),
        ('freight in', 'X1'),
        ('selling expense', 'X2'),
        ('sales commission', 'X2'),
        ('marketing', 'X2'),
        ('administrative', 'X3'),
        ('office', 'X3'),
        ('utilities', 'X3'),
        ('depreciation expense', 'X3'),
        ('bad debt', 'X3'),
        ('interest expense', 'X4'),
        ('foreign exchange', 'X4'),
        ('miscellaneous', 'X4')
    )
    
    @classmethod
    def generate_reporting_tag(
        cls,
        account_type: str,
        category: str,
        *,
        name: str = "",
        code: str = ""
    ) -> Optional[str]:
        """
        Automatically generate IFRS reporting tag based on account type and category
        
        Args:
            account_type: The account type (Asset, Liability, Equity, Revenue, Expense)
            category: The account category
            name: Optional account name used for keyword heuristics
            code: Optional account code for explicit overrides
            
        Returns:
            The IFRS reporting tag or None if no match found
        """
        return cls.determine_reporting_tag(account_type=account_type, category=category, name=name, code=code)

    @classmethod
    def determine_reporting_tag(
        cls,
        *,
        account_type: str,
        category: str = "",
        name: str = "",
        code: str = ""
    ) -> Optional[str]:
        """Determine the most appropriate IFRS tag using overrides, category rules, and heuristics."""

        account_type = (account_type or "").strip()
        category = (category or "").strip()
        name = (name or "").strip()
        code = (code or "").strip()

        if not account_type:
            return None

        # Code-specific override provides strongest signal
        if code and code in cls.CODE_TAG_OVERRIDES:
            return cls.CODE_TAG_OVERRIDES[code]

        # Direct category mapping
        type_mapping = cls.IFRS_REPORTING_TAGS.get(account_type, {})
        if category and category in type_mapping:
            return type_mapping[category]

        # Keyword heuristics across name and category
        combined = f"{category} {name}".lower()
        for keyword, tag in cls.NAME_KEYWORD_TAGS:
            if keyword in combined:
                return tag

        # Fallback to default tag by account type
        return cls.DEFAULT_TAGS.get(account_type)

    @classmethod
    def determine_tag_for_account(cls, account: Any) -> Optional[str]:
        """Helper that accepts an AccountingCode instance (or similar) and resolves a reporting tag."""

        if not account:
            return None

        return cls.determine_reporting_tag(
            account_type=getattr(account, 'account_type', None),
            category=getattr(account, 'category', None),
            name=getattr(account, 'name', None),
            code=getattr(account, 'code', None)
        )
    
    @classmethod
    def get_all_reporting_tags(cls) -> Dict[str, Dict[str, str]]:
        """Get all available IFRS reporting tags"""
        return cls.IFRS_REPORTING_TAGS.copy()
    
    @classmethod
    def validate_reporting_tag(cls, reporting_tag: str) -> bool:
        """Validate if a reporting tag is valid"""
        if not reporting_tag:
            return False
        return reporting_tag in cls.VALID_IFRS_TAGS

    @classmethod
    def list_valid_tags(cls) -> Tuple[str, ...]:
        """Return a sorted tuple of valid IFRS reporting tags."""
        return tuple(sorted(cls.VALID_IFRS_TAGS))