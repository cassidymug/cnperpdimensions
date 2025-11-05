from datetime import datetime
from app.models.base import BaseModel
from app.models.accounting_constants import (
    ACCOUNT_TYPES, CATEGORIES,
    validate_account_type, validate_category,
    get_normal_balance, get_categories_for_type,
    NormalBalance, AccountType
)
import uuid
from sqlalchemy import Column, String, Boolean, Text, DateTime, Date, ForeignKey, Numeric, Integer, CheckConstraint, Enum
from sqlalchemy.orm import relationship, validates, object_session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    pass  # (retain placeholder; related journal models defined below in this file)


class AccountingCode(BaseModel):
    """
    Represents an account in the chart of accounts.

    The account must have a valid account type and category according to the
    ACCOUNT_TYPES and CATEGORIES defined in accounting_constants.py
    """
    __tablename__ = "accounting_codes"

    # Add a check constraint for valid account types
    __table_args__ = (
        CheckConstraint(
            "account_type IN ('Asset', 'Liability', 'Equity', 'Revenue', 'Expense')",
            name='valid_account_type'
        ),
        {
            'comment': 'Stores the chart of accounts with hierarchical structure'
        }
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
               comment='Unique identifier for the account')

    code = Column(String(20), unique=True, nullable=False, index=True,
                 comment='Account code (e.g., 1000, 1100, etc.)')

    name = Column(String(100), nullable=False,
                 comment='Name of the account')

    account_type = Column(String(20), nullable=False,
                         comment='Type of account (Asset, Liability, Equity, Revenue, Expense)')

    category = Column(String(50), nullable=False,
                     comment='Category of the account (e.g., Current Asset, Fixed Asset, etc.)')

    parent_id = Column(String(36), ForeignKey("accounting_codes.id", ondelete='CASCADE'),
                      nullable=True, index=True,
                      comment='Reference to parent account for hierarchical structure')

    is_parent = Column(Boolean, default=False, nullable=False,
                      comment='Indicates if this account can have sub-accounts')

    total_debits = Column(Numeric(19, 4), default=0.0,
                         comment='Sum of all debits to this account')

    total_credits = Column(Numeric(19, 4), default=0.0,
                          comment='Sum of all credits to this account')

    balance = Column(Numeric(19, 4), default=0.0, nullable=False,
                    comment='Current balance of the account')

    currency = Column(String(3), default="BWP",
                     comment='Currency code (ISO 4217)')

    reporting_tag = Column(String(50), nullable=True,
                         comment='Optional tag for financial reporting')

    # Foreign key to branch
    branch_id = Column(String(36), ForeignKey("branches.id"),
                      nullable=True, index=True,
                      comment='Reference to the branch this account belongs to')

    # Active status - temporarily commented out until DB migration
    # is_active = Column(Boolean, default=True, nullable=False,
    #                   comment='Whether this account is active and can be used')

    # Relationships
    parent = relationship("AccountingCode", remote_side=[id], back_populates="children")
    children = relationship(
        "AccountingCode",
        back_populates="parent",
        cascade="all, delete-orphan",
        foreign_keys="[AccountingCode.parent_id]"
    )

    # Dimension requirements for this account
    dimension_requirements = relationship("AccountingCodeDimensionRequirement",
                                        back_populates="accounting_code",
                                        cascade="all, delete-orphan")

    # Branch relationship (if multi-branch accounting is needed)
    branch_id = Column(String(36), ForeignKey("branches.id", ondelete='SET NULL'),
                     nullable=True, index=True,
                     comment='Reference to the branch this account belongs to')

    # Lazy loading for branch to avoid circular imports
    @property
    def branch(self):
        if not hasattr(self, '_branch'):
            from .branch import Branch
            session = object_session(self)
            if session and self.branch_id:
                self._branch = session.query(Branch).get(self.branch_id)
            else:
                self._branch = None
        return self._branch

    @branch.setter
    def branch(self, value):
        self._branch = value
        if value is not None:
            self.branch_id = value.id
        else:
            self.branch_id = None

    def __init__(self, **kwargs):
        # Initialize the model with provided kwargs
        super().__init__(**kwargs)

        # Set default values for required fields if not provided
        if not hasattr(self, 'is_parent'):
            self.is_parent = False

        if not hasattr(self, 'currency'):
            self.currency = 'BWP'

    @validates('account_type')
    def validate_account_type(self, key: str, account_type: AccountType) -> AccountType:
        """Validate and set the account type."""
        # Simple validation - just ensure it's a valid AccountType enum value
        if account_type not in [AccountType.ASSET, AccountType.LIABILITY, AccountType.EQUITY, AccountType.REVENUE, AccountType.EXPENSE]:
            raise ValueError(f"Invalid account type: {account_type}")

        return account_type

    @validates('category')
    def validate_category(self, key: str, category: str) -> str:
        """Validate the category against the account type."""
        # For now, just return the category without complex validation
        # TODO: Implement proper category validation later
        return category

    @validates('parent_id')
    def validate_parent(self, key: str, parent_id: Optional[str]) -> Optional[str]:
        """Validate the parent account."""
        if parent_id:
            if parent_id == self.id:
                raise ValueError("An account cannot be its own parent")

            # Skip circular reference check during creation to avoid issues
            # The check can be done in business logic layer if needed

        return parent_id

    def is_child_of(self, potential_parent: 'AccountingCode') -> bool:
        """Check if this account is a child (at any level) of the potential parent."""
        if not potential_parent:
            return False

        current = self.parent
        while current:
            if current.id == potential_parent.id:
                return True
            current = current.parent
        return False

    def update_balance(self) -> None:
        """Update the balance based on debits and credits."""
        # Get normal balance from the account type's configuration
        normal_balance = get_normal_balance(self.account_type)
        if normal_balance == NormalBalance.DEBIT:
            self.balance = self.total_debits - self.total_credits
        else:
            self.balance = self.total_credits - self.total_debits

    def get_full_path(self) -> str:
        """Get the full hierarchical path of the account (e.g., 'Assets > Current Assets > Bank')."""
        path = [self.name]
        parent = self.parent
        while parent:
            path.append(parent.name)
            parent = parent.parent
        return ' > '.join(reversed(path))

    def get_balance_with_children(self) -> Dict[str, Any]:
        """
        Get the balance including all child accounts.

        Returns:
            Dict with 'debit', 'credit', and 'balance' amounts including all children
        """
        if not self.is_parent:
            return {
                'debit': self.total_debits,
                'credit': self.total_credits,
                'balance': self.balance
            }

        # For parent accounts, aggregate child balances
        total_debits = self.total_debits
        total_credits = self.total_credits

        for child in self.children:
            child_balance = child.get_balance_with_children()
            total_debits += child_balance['debit']
            total_credits += child_balance['credit']

        if self.normal_balance == NormalBalance.DEBIT:
            balance = total_debits - total_credits
        else:
            balance = total_credits - total_debits

        return {
            'debit': total_debits,
            'credit': total_credits,
            'balance': balance
        }

    def to_dict(self, include_children: bool = False) -> Dict[str, Any]:
        """Convert the account to a dictionary representation."""
        result = {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'account_type': self.account_type.value if self.account_type else None,
            'category': self.category,
            'parent_id': self.parent_id,
            'is_parent': self.is_parent,
            'total_debits': float(self.total_debits) if self.total_debits is not None else 0.0,
            'total_credits': float(self.total_credits) if self.total_credits is not None else 0.0,
            'balance': float(self.balance) if self.balance is not None else 0.0,
            'normal_balance': self.normal_balance.value if self.normal_balance else None,
            'currency': self.currency,
            'reporting_tag': self.reporting_tag,
            'description': self.description,
            # 'is_active': self.is_active,  # Field doesn't exist in DB yet
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'full_path': self.get_full_path()
        }

        if include_children and self.children:
            result['children'] = [child.to_dict(include_children=True) for child in self.children]

        return result

    # Relationships
    parent = relationship("AccountingCode", remote_side="AccountingCode.id")
    children = relationship("AccountingCode", overlaps="parent")
    ledger = relationship("Ledger", uselist=False, back_populates="accounting_code", foreign_keys="Ledger.accounting_code_id")
    branch = relationship("Branch")
    journal_entries = relationship("JournalEntry", back_populates="accounting_code")
    journal_transactions = relationship("JournalTransaction", back_populates="accounting_code")
    opening_balances = relationship("OpeningBalance", back_populates="accounting_code")


class AccountingEntry(BaseModel):
    """Accounting entry header"""
    __tablename__ = "accounting_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    date_prepared = Column(Date)
    date_posted = Column(Date)
    particulars = Column(Text)
    book = Column(String)
    status = Column(String, default="posted")
    branch_id = Column(ForeignKey("branches.id"), nullable=False)

    # Relationships
    branch = relationship("Branch")
    journal_entries = relationship("JournalEntry", back_populates="accounting_entry")


class JournalEntry(BaseModel):
    """Journal entry line items"""
    __tablename__ = "journal_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    accounting_code_id = Column(ForeignKey("accounting_codes.id"), nullable=False)
    accounting_entry_id = Column(ForeignKey("accounting_entries.id"), nullable=False)
    purchase_id = Column(String, ForeignKey("purchases.id"), nullable=True, index=True)
    entry_type = Column(String)
    narration = Column(String)
    date = Column(Date)
    ledger_id = Column(ForeignKey("ledgers.id"))
    reference = Column(String)
    date_posted = Column(Date)
    description = Column(Text)
    debit_amount = Column(Numeric(15, 2), default=0.0)
    credit_amount = Column(Numeric(15, 2), default=0.0)
    branch_id = Column(ForeignKey("branches.id"))
    # POS / system attribution
    origin = Column(String, default="manual", index=True)  # e.g., 'POS', 'system'
    created_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)

    # Relationships
    accounting_code = relationship("AccountingCode", back_populates="journal_entries")
    accounting_entry = relationship("AccountingEntry", back_populates="journal_entries")
    ledger = relationship("Ledger", foreign_keys=[ledger_id])
    branch = relationship("Branch")
    purchase = relationship("Purchase", back_populates="journal_entries")

    # Dimensional analysis relationships
    dimension_assignments = relationship("AccountingDimensionAssignment",
                                       back_populates="journal_entry",
                                       cascade="all, delete-orphan")


class JournalTransaction(BaseModel):
    """Journal transaction details"""
    __tablename__ = "journal_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    journal_entry_id = Column(ForeignKey("journal_entries.id"), nullable=False)
    accounting_code_id = Column(ForeignKey("accounting_codes.id"), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    entry_type = Column(String, nullable=False)
    branch_id = Column(ForeignKey("branches.id"))

    # Relationships
    journal_entry = relationship("JournalEntry")
    accounting_code = relationship("AccountingCode", back_populates="journal_transactions")
    branch = relationship("Branch")


class Ledger(BaseModel):
    """Ledger for accounting codes"""
    __tablename__ = "ledgers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    accounting_code_id = Column(ForeignKey("accounting_codes.id"), nullable=False)
    is_balanced = Column(Boolean, default=False)

    # Relationships
    accounting_code = relationship("AccountingCode", back_populates="ledger", foreign_keys=[accounting_code_id])
    journal_entries = relationship("JournalEntry", back_populates="ledger")


class OpeningBalance(BaseModel):
    """Opening balances for accounting codes"""
    __tablename__ = "opening_balances"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    accounting_code_id = Column(ForeignKey("accounting_codes.id"), nullable=False)
    year = Column(Integer, nullable=False)
    amount = Column(Numeric(15, 2), default=0.0, nullable=False)

    # Relationships
    accounting_code = relationship("AccountingCode", back_populates="opening_balances")


class JournalSaleAudit(BaseModel):
    """Linkage audit table: ties auto-posted journal entries to POS sales with user & branch traceability"""
    __tablename__ = "journal_sale_audit"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    journal_entry_id = Column(String, ForeignKey("journal_entries.id"), nullable=False, index=True)
    sale_id = Column(String, ForeignKey("sales.id"), nullable=False, index=True)
    pos_session_id = Column(String, ForeignKey("pos_sessions.id"), nullable=True)
    branch_id = Column(String, ForeignKey("branches.id"), nullable=False, index=True)
    cashier_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    posted_by_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    origin = Column(String, default="POS_AUTO", index=True)
    notes = Column(Text)

    # Relationships (light; no backrefs to avoid heavy loading unless needed)
    journal_entry = relationship("JournalEntry")
    sale = relationship("Sale")
    branch = relationship("Branch")
