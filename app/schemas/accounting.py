from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from decimal import Decimal
from datetime import date as Date


class AccountingCodeBase(BaseModel):
    code: str
    name: str
    account_type: str
    category: Optional[str] = None
    parent_id: Optional[str] = None
    is_parent: Optional[bool] = None
    total_debits: Optional[Decimal] = None
    total_credits: Optional[Decimal] = None
    balance: Optional[Decimal] = Field(default=0.0)
    branch_id: Optional[str] = None
    currency: Optional[str] = Field(default="BWP")
    reporting_tag: Optional[str] = None


class AccountingCodeCreate(AccountingCodeBase):
    pass


class AccountingCodeUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    account_type: Optional[str] = None
    category: Optional[str] = None
    parent_id: Optional[str] = None
    is_parent: Optional[bool] = None
    total_debits: Optional[Decimal] = None
    total_credits: Optional[Decimal] = None
    balance: Optional[Decimal] = None
    branch_id: Optional[str] = None
    currency: Optional[str] = None
    reporting_tag: Optional[str] = None


class AccountingCodeResponse(AccountingCodeBase):
    id: str

    model_config = ConfigDict(from_attributes=True)


class JournalEntryBase(BaseModel):
    accounting_code_id: str
    entry_type: str
    narration: str
    debit_amount: Decimal = Field(default=0)
    credit_amount: Decimal = Field(default=0)
    description: Optional[str] = None
    reference: Optional[str] = None


class JournalEntryCreate(JournalEntryBase):
    pass


class JournalEntryResponse(JournalEntryBase):
    id: str
    date: Date
    date_posted: Optional[Date]
    branch_id: str
    accounting_code_name: Optional[str] = None
    accounting_code_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AccountingEntryBase(BaseModel):
    date_prepared: Date
    particulars: str
    book: str
    status: str = "draft"


class AccountingEntryCreate(AccountingEntryBase):
    journal_entries: List[JournalEntryCreate]


class AccountingEntryResponse(AccountingEntryBase):
    id: str
    date_posted: Optional[Date]
    branch_id: str
    journal_entries: List[JournalEntryResponse] = []

    model_config = ConfigDict(from_attributes=True)


class LedgerEntryResponse(BaseModel):
    id: str
    date: Date
    account_code: str
    account_name: str
    description: str
    reference: str
    debit: Decimal
    credit: Decimal
    balance: Decimal
    type: str

    model_config = ConfigDict(from_attributes=True)


class TrialBalanceEntryResponse(BaseModel):
    account_code: str
    account_name: str
    type: str
    debit_balance: Decimal
    credit_balance: Decimal
    net_balance: Decimal

    model_config = ConfigDict(from_attributes=True)