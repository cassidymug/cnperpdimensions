from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal


# Bank Account Schemas
class BankAccountBase(BaseModel):
    name: str
    institution: str
    account_number: str
    currency: str = "USD"
    account_type: str
    accounting_code_id: str


class BankAccountCreate(BankAccountBase):
    pass


class BankAccountUpdate(BaseModel):
    name: Optional[str] = None
    institution: Optional[str] = None
    account_number: Optional[str] = None
    currency: Optional[str] = None
    account_type: Optional[str] = None
    accounting_code_id: Optional[str] = None


class BankAccountResponse(BankAccountBase):
    id: str
    accounting_code_name: Optional[str] = None
    accounting_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Bank Transaction Schemas
class BankTransactionBase(BaseModel):
    bank_account_id: str
    date: date
    amount: Decimal
    description: str
    transaction_type: str
    reference: Optional[str] = None
    vat_amount: Optional[Decimal] = 0
    destination_bank_account_id: Optional[str] = None


class BankTransactionCreate(BankTransactionBase):
    @field_validator('transaction_type')
    @classmethod
    def validate_transaction_type(cls, v):
        valid_types = ['deposit', 'withdrawal', 'transfer', 'payment', 'receipt', 'bank_charge', 'interest', 'reversal']
        if v not in valid_types:
            raise ValueError(f'Transaction type must be one of: {valid_types}')
        return v


class BankTransactionUpdate(BaseModel):
    date: Optional[date] = None
    amount: Optional[Decimal] = None
    description: Optional[str] = None
    transaction_type: Optional[str] = None
    reference: Optional[str] = None
    reconciled: Optional[bool] = None
    vat_amount: Optional[Decimal] = None
    destination_bank_account_id: Optional[str] = None


class BankTransactionResponse(BankTransactionBase):
    id: str
    reconciled: Optional[bool] = None
    accounting_entry_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# Bank Transfer Schemas
class BankTransferBase(BaseModel):
    amount: Decimal
    transfer_type: str
    reference: str
    description: str
    source_account_id: Optional[str] = None
    destination_account_id: Optional[str] = None
    external_source_name: Optional[str] = None
    external_source_currency: Optional[str] = "USD"
    external_destination_name: Optional[str] = None
    external_destination_currency: Optional[str] = "USD"
    exchange_rate: Optional[Decimal] = None
    converted_amount: Optional[Decimal] = None
    vat_amount: Optional[Decimal] = 0
    vat_rate: Optional[Decimal] = None
    transfer_fee: Optional[Decimal] = 0
    beneficiary_id: Optional[str] = None


class BankTransferCreate(BankTransferBase):
    @field_validator('transfer_type')
    @classmethod
    def validate_transfer_type(cls, v):
        valid_types = ['internal', 'external', 'wire', 'ach', 'swift', 'local']
        if v not in valid_types:
            raise ValueError(f'Transfer type must be one of: {valid_types}')
        return v


class BankTransferUpdate(BaseModel):
    status: Optional[str] = None
    description: Optional[str] = None
    exchange_rate: Optional[Decimal] = None
    converted_amount: Optional[Decimal] = None
    vat_amount: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None
    transfer_fee: Optional[Decimal] = None
    meta_data: Optional[Dict[str, Any]] = None


class BankTransferResponse(BankTransferBase):
    id: str
    status: str
    meta_data: Optional[Dict[str, Any]] = None
    processed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# Bank Reconciliation Schemas
class BankReconciliationBase(BaseModel):
    bank_account_id: str
    statement_date: date
    statement_balance: Decimal
    book_balance: Decimal
    statement_reference: Optional[str] = None
    notes: Optional[str] = None


class BankReconciliationCreate(BankReconciliationBase):
    pass


class BankReconciliationUpdate(BaseModel):
    statement_balance: Optional[Decimal] = None
    book_balance: Optional[Decimal] = None
    status: Optional[str] = None
    statement_reference: Optional[str] = None
    notes: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None


class BankReconciliationResponse(BankReconciliationBase):
    id: str
    difference: Optional[Decimal] = None
    status: str
    meta_data: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    reconciled_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# Reconciliation Item Schemas
class ReconciliationItemBase(BaseModel):
    bank_reconciliation_id: str
    statement_description: str
    statement_amount: Decimal
    statement_date: date
    statement_reference: Optional[str] = None
    book_amount: Optional[Decimal] = None
    book_date: Optional[date] = None
    book_description: Optional[str] = None
    book_reference: Optional[str] = None
    vat_amount: Optional[Decimal] = 0
    vat_rate: Optional[Decimal] = None
    fee_amount: Optional[Decimal] = 0
    notes: Optional[str] = None


class ReconciliationItemCreate(ReconciliationItemBase):
    pass


class ReconciliationItemUpdate(BaseModel):
    book_amount: Optional[Decimal] = None
    book_date: Optional[date] = None
    book_description: Optional[str] = None
    book_reference: Optional[str] = None
    matched: Optional[bool] = None
    vat_amount: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None
    fee_amount: Optional[Decimal] = None
    notes: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None


class ReconciliationItemResponse(ReconciliationItemBase):
    id: str
    bank_transaction_id: Optional[str] = None
    matched: bool
    matched_at: Optional[datetime] = None
    difference: Optional[Decimal] = None
    meta_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# Beneficiary Schemas
class BeneficiaryBase(BaseModel):
    name: str
    account_type: str
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    provider: str
    mobile_number: Optional[str] = None
    wallet_address: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None


class BeneficiaryCreate(BeneficiaryBase):
    @field_validator('account_type')
    @classmethod
    def validate_account_type(cls, v):
        valid_types = ['bank', 'mobile_money', 'digital_wallet', 'card']
        if v not in valid_types:
            raise ValueError(f'Account type must be one of: {valid_types}')
        return v


class BeneficiaryUpdate(BaseModel):
    name: Optional[str] = None
    account_type: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    provider: Optional[str] = None
    mobile_number: Optional[str] = None
    wallet_address: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    active: Optional[bool] = None


class BeneficiaryResponse(BeneficiaryBase):
    id: str
    user_id: str
    active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# Banking Summary Schema
class BankingSummaryResponse(BaseModel):
    total_accounts: int
    total_balance: Decimal
    total_transactions: int
    pending_transfers: int
    pending_reconciliations: int
    accounts_by_currency: Dict[str, Decimal]
    recent_transactions: List[Dict[str, Any]]
    account_balances: List[Dict[str, Any]]

    model_config = {"from_attributes": True}


# Bank Statement Schema
class BankStatementResponse(BaseModel):
    account_id: str
    start_date: date
    end_date: date
    opening_balance: Decimal
    closing_balance: Decimal
    transactions: List[Dict[str, Any]]
    summary: Dict[str, Any]

    model_config = {"from_attributes": True} 