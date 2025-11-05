import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Text, Date, ForeignKey, Numeric, Integer, DateTime, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class BankAccount(BaseModel):
    """Bank account model"""
    __tablename__ = "bank_accounts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    name = Column(String)
    institution = Column(String)
    account_number = Column(String)
    currency = Column(String)
    account_type = Column(String)
    balance = Column(Numeric(15, 2), default=0.0)
    accounting_code_id = Column(ForeignKey("accounting_codes.id"), nullable=False)
    branch_id = Column(ForeignKey("branches.id"))

    # Relationships
    accounting_code = relationship("AccountingCode")
    branch = relationship("Branch", back_populates="bank_accounts")
    bank_transactions = relationship("BankTransaction", back_populates="bank_account", foreign_keys="BankTransaction.bank_account_id")
    bank_reconciliations = relationship("BankReconciliation", back_populates="bank_account")
    source_transfers = relationship("BankTransfer", foreign_keys="BankTransfer.source_account_id")
    destination_transfers = relationship("BankTransfer", foreign_keys="BankTransfer.destination_account_id")
    payments = relationship("Payment", back_populates="bank_account")


class BankTransaction(BaseModel):
    """Bank transaction model"""
    __tablename__ = "bank_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    bank_account_id = Column(ForeignKey("bank_accounts.id"), nullable=False)
    date = Column(Date)
    amount = Column(Numeric(15, 2))
    description = Column(String)
    transaction_type = Column(String)
    reference = Column(String)
    reconciled = Column(Boolean)
    accounting_entry_id = Column(ForeignKey("accounting_entries.id"))
    vat_amount = Column(Numeric(15, 2), default=0.0)
    destination_bank_account_id = Column(ForeignKey("bank_accounts.id"))

    # Phase 4: Dimensional Accounting Fields
    cost_center_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True, index=True)
    project_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True, index=True)
    department_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True, index=True)
    gl_bank_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)
    posting_status = Column(String, default="pending", nullable=False, index=True)  # pending|posted|error
    posted_by = Column(String, ForeignKey("users.id"), nullable=True)
    last_posted_date = Column(DateTime, nullable=True, index=True)
    reconciliation_status = Column(String, default="unreconciled", nullable=False)  # unreconciled|reconciled|variance
    reconciliation_note = Column(String, nullable=True)

    # Relationships
    bank_account = relationship("BankAccount", back_populates="bank_transactions", foreign_keys=[bank_account_id])
    destination_bank_account = relationship("BankAccount", foreign_keys=[destination_bank_account_id])
    accounting_entry = relationship("AccountingEntry")
    reconciliation_items = relationship("ReconciliationItem", back_populates="bank_transaction")
    cost_center = relationship("AccountingDimensionValue", foreign_keys=[cost_center_id])
    project = relationship("AccountingDimensionValue", foreign_keys=[project_id])
    department = relationship("AccountingDimensionValue", foreign_keys=[department_id])
    gl_account = relationship("AccountingCode", foreign_keys=[gl_bank_account_id])
    posted_by_user = relationship("User", foreign_keys=[posted_by])


class BankTransfer(BaseModel):
    """Bank transfer model"""
    __tablename__ = "bank_transfers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    amount = Column(Numeric(15, 2), nullable=False)
    transfer_type = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)
    reference = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=False)
    source_account_id = Column(ForeignKey("bank_accounts.id"))
    destination_account_id = Column(ForeignKey("bank_accounts.id"))
    accounting_entry_id = Column(ForeignKey("accounting_entries.id"))
    external_source_name = Column(String)
    external_source_currency = Column(String, default="USD")
    external_destination_name = Column(String)
    external_destination_currency = Column(String, default="USD")
    exchange_rate = Column(Numeric(10, 6))
    converted_amount = Column(Numeric(15, 2))
    vat_amount = Column(Numeric(15, 2), default=0.0)
    vat_rate = Column(Numeric(5, 2))
    transfer_fee = Column(Numeric(15, 2), default=0.0)
    meta_data = Column(JSON, default={})
    processed_at = Column(DateTime)
    completed_at = Column(DateTime)
    beneficiary_id = Column(ForeignKey("beneficiaries.id"))

    # Relationships
    source_account = relationship("BankAccount", foreign_keys=[source_account_id], overlaps="source_transfers")
    destination_account = relationship("BankAccount", foreign_keys=[destination_account_id], overlaps="destination_transfers")
    accounting_entry = relationship("AccountingEntry")
    beneficiary = relationship("Beneficiary")


class BankReconciliation(BaseModel):
    """Bank reconciliation model"""
    __tablename__ = "bank_reconciliations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    bank_account_id = Column(ForeignKey("bank_accounts.id"), nullable=False)
    statement_date = Column(Date, nullable=False)
    statement_balance = Column(Numeric(15, 2), nullable=False)
    book_balance = Column(Numeric(15, 2), nullable=False)
    difference = Column(Numeric(15, 2), default=0.0)
    status = Column(String, default="draft", nullable=False)
    statement_reference = Column(String)
    notes = Column(Text)
    meta_data = Column(JSON, default={})
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    reconciled_at = Column(DateTime)

    # Phase 4: Dimensional Reconciliation Fields
    dimensional_accuracy = Column(Boolean, default=True, nullable=False)
    dimension_variance_detail = Column(Text, nullable=True)  # JSON of variances by dimension
    has_dimensional_mismatch = Column(Boolean, default=False, nullable=False)
    variance_cost_centers = Column(Text, nullable=True)  # JSON array of cost centers with variances
    gl_balance_by_dimension = Column(Text, nullable=True)  # JSON of GL balances by dimension
    bank_statement_by_dimension = Column(Text, nullable=True)  # JSON of statement balances by dimension
    variance_amount = Column(Numeric(15, 2), default=0.0)

    # Relationships
    bank_account = relationship("BankAccount", back_populates="bank_reconciliations")
    reconciliation_items = relationship("ReconciliationItem", back_populates="bank_reconciliation")


class ReconciliationItem(BaseModel):
    """Bank reconciliation item model"""
    __tablename__ = "reconciliation_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    bank_reconciliation_id = Column(ForeignKey("bank_reconciliations.id"), nullable=False)
    bank_transaction_id = Column(ForeignKey("bank_transactions.id"))
    statement_description = Column(String, nullable=False)
    statement_amount = Column(Numeric(15, 2), nullable=False)
    statement_date = Column(Date, nullable=False)
    statement_reference = Column(String)
    book_amount = Column(Numeric(15, 2))
    book_date = Column(Date)
    book_description = Column(String)
    book_reference = Column(String)
    matched = Column(Boolean, default=False, nullable=False)
    matched_at = Column(DateTime)
    difference = Column(Numeric(15, 2), default=0.0)
    vat_amount = Column(Numeric(15, 2), default=0.0)
    vat_rate = Column(Numeric(5, 2))
    fee_amount = Column(Numeric(15, 2), default=0.0)
    notes = Column(Text)
    meta_data = Column(JSON, default={})

    # Relationships
    bank_reconciliation = relationship("BankReconciliation", back_populates="reconciliation_items")
    bank_transaction = relationship("BankTransaction", back_populates="reconciliation_items")


class Beneficiary(BaseModel):
    """Beneficiary model for bank transfers"""
    __tablename__ = "beneficiaries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    name = Column(String, nullable=False)
    account_type = Column(String, nullable=False)
    account_number = Column(String)
    bank_name = Column(String)
    provider = Column(String, nullable=False)
    mobile_number = Column(String)
    wallet_address = Column(String)
    email = Column(String)
    notes = Column(Text)
    active = Column(Boolean, default=True, nullable=False)
    user_id = Column(ForeignKey("users.id"), nullable=False)

    # Relationships
    user = relationship("User", back_populates="beneficiaries")
    bank_transfers = relationship("BankTransfer", back_populates="beneficiary")


class BankTransferAllocation(BaseModel):
    """Phase 4: Bridge table for tracking dimensional allocation of bank transfers"""
    __tablename__ = "bank_transfer_allocations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Reference to bank transfer
    bank_transfer_id = Column(String, ForeignKey("bank_transfers.id"), nullable=False, index=True)

    # From dimensions (stored as AccountingDimensionValue IDs)
    from_cost_center_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True, index=True)
    from_project_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)
    from_department_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)

    # To dimensions (stored as AccountingDimensionValue IDs)
    to_cost_center_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True, index=True)
    to_project_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)
    to_department_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)

    # Amount allocation
    amount = Column(Numeric(15, 2), nullable=False, index=True)
    authorization_required = Column(Boolean, default=True, nullable=False)
    authorized_by = Column(String, ForeignKey("users.id"), nullable=True)
    authorization_date = Column(DateTime, nullable=True)

    # GL tracking
    posted_to_gl = Column(Boolean, default=False, nullable=False)
    gl_debit_entry_id = Column(String, ForeignKey("journal_entries.id"), nullable=True)
    gl_credit_entry_id = Column(String, ForeignKey("journal_entries.id"), nullable=True)

    # Audit
    created_at = Column(DateTime, default=lambda: datetime.now(), nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)

    # Relationships
    bank_transfer = relationship("BankTransfer", backref="transfer_allocations")
    from_cost_center = relationship("AccountingDimensionValue", foreign_keys=[from_cost_center_id], backref="from_bank_allocations")
    from_project = relationship("AccountingDimensionValue", foreign_keys=[from_project_id])
    from_department = relationship("AccountingDimensionValue", foreign_keys=[from_department_id])
    to_cost_center = relationship("AccountingDimensionValue", foreign_keys=[to_cost_center_id], backref="to_bank_allocations")
    to_project = relationship("AccountingDimensionValue", foreign_keys=[to_project_id])
    to_department = relationship("AccountingDimensionValue", foreign_keys=[to_department_id])
    authorized_by_user = relationship("User", foreign_keys=[authorized_by], backref="authorized_transfers")
    created_by_user = relationship("User", foreign_keys=[created_by], backref="created_transfer_allocations")
    gl_debit = relationship("JournalEntry", foreign_keys=[gl_debit_entry_id])
    gl_credit = relationship("JournalEntry", foreign_keys=[gl_credit_entry_id])
