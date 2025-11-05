"""
Credit Note Models

Credit notes are the proper accounting documents for customer returns and refunds.
They provide formal documentation of return reasons and refund methods.
"""

from sqlalchemy import Column, String, Numeric, Date, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from decimal import Decimal
import uuid
from datetime import datetime, date


class CreditNote(BaseModel):
    """Credit note for customer returns and refunds"""
    __tablename__ = "credit_notes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Credit note identification
    credit_note_number = Column(String, nullable=False, unique=True, index=True)
    issue_date = Column(Date, nullable=False, default=date.today)

    # Related documents - support both invoices and POS receipts
    source_type = Column(String, nullable=False, default='invoice')  # 'invoice' or 'pos_receipt'
    source_id = Column(String, nullable=False)  # ID of invoice or sale (POS receipt)
    original_invoice_id = Column(String, ForeignKey("invoices.id"), nullable=True)  # Legacy support - now optional
    original_sale_id = Column(String, ForeignKey("sales.id"), nullable=True)  # For POS receipts
    reversal_accounting_entry_id = Column(String, ForeignKey("accounting_entries.id"), nullable=True)

    # Customer and branch
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    branch_id = Column(String, ForeignKey("branches.id"), nullable=False)

    # Dimensional accounting fields
    cost_center_id = Column(String, nullable=True, comment="Cost center for dimensional accounting")
    project_id = Column(String, nullable=True, comment="Project for dimensional accounting")

    # Return details
    return_reason = Column(String, nullable=False)  # 'faulty_product', 'wrong_item', 'damaged', 'customer_request', etc.
    return_description = Column(Text, nullable=True)
    return_date = Column(Date, nullable=False, default=date.today)

    # Financial amounts
    subtotal = Column(Numeric(15, 2), nullable=False, default=0.0)
    discount_amount = Column(Numeric(15, 2), nullable=False, default=0.0)
    vat_amount = Column(Numeric(15, 2), nullable=False, default=0.0)
    total_amount = Column(Numeric(15, 2), nullable=False, default=0.0)

    # Refund method
    refund_method = Column(String, nullable=False)  # 'cash', 'bank_transfer', 'credit_adjustment', 'store_credit'
    refund_status = Column(String, nullable=False, default='pending')  # 'pending', 'processed', 'completed'
    refund_processed_date = Column(Date, nullable=True)
    refund_reference = Column(String, nullable=True)  # Bank transfer reference, etc.

    # Status and workflow
    status = Column(String, nullable=False, default='draft')  # 'draft', 'issued', 'processed', 'cancelled'
    notes = Column(Text, nullable=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    approved_by = Column(String, ForeignKey("users.id"), nullable=True)
    processed_by = Column(String, ForeignKey("users.id"), nullable=True)

    # Relationships
    original_invoice = relationship("Invoice", foreign_keys=[original_invoice_id], back_populates="credit_notes")
    original_sale = relationship("Sale", foreign_keys=[original_sale_id])
    customer = relationship("Customer", back_populates="credit_notes")
    branch = relationship("Branch")
    credit_note_items = relationship("CreditNoteItem", back_populates="credit_note", cascade="all, delete-orphan")
    reversal_accounting_entry = relationship("AccountingEntry")

    # User relationships
    created_by_user = relationship("User", foreign_keys=[created_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])
    processed_by_user = relationship("User", foreign_keys=[processed_by])


class CreditNoteItem(BaseModel):
    """Individual items in a credit note"""
    __tablename__ = "credit_note_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    credit_note_id = Column(String, ForeignKey("credit_notes.id"), nullable=False)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    original_invoice_item_id = Column(String, ForeignKey("invoice_items.id"), nullable=True)
    original_sale_item_id = Column(String, ForeignKey("sale_items.id"), nullable=True)

    # Item details
    quantity_returned = Column(Numeric(10, 2), nullable=False)
    unit_price = Column(Numeric(15, 2), nullable=False)
    discount_percentage = Column(Numeric(5, 2), default=0.0)
    discount_amount = Column(Numeric(10, 2), default=0.0)
    vat_rate = Column(Numeric(8, 4), default=0.0)
    vat_amount = Column(Numeric(15, 2), default=0.0)
    line_total = Column(Numeric(15, 2), nullable=False)

    # Return specifics
    item_condition = Column(String, nullable=False)  # 'faulty', 'damaged', 'unopened', 'used'
    return_reason = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    serial_numbers = Column(Text, nullable=True)  # JSON string for returned serial numbers

    # Relationships
    credit_note = relationship("CreditNote", back_populates="credit_note_items")
    product = relationship("Product")
    original_invoice_item = relationship("InvoiceItem")
    original_sale_item = relationship("SaleItem")


class RefundTransaction(BaseModel):
    """Tracks actual refund payments made to customers"""
    __tablename__ = "refund_transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    credit_note_id = Column(String, ForeignKey("credit_notes.id"), nullable=False)
    transaction_date = Column(Date, nullable=False, default=date.today)

    # Refund details
    refund_method = Column(String, nullable=False)
    refund_amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String, default='BWP')

    # Payment details
    bank_account_id = Column(String, ForeignKey("bank_accounts.id"), nullable=True)
    cash_account_id = Column(String, ForeignKey("accounting_codes.id"), nullable=True)
    reference_number = Column(String, nullable=True)

    # Banking details (for bank transfers)
    customer_bank_name = Column(String, nullable=True)
    customer_account_number = Column(String, nullable=True)
    customer_account_name = Column(String, nullable=True)
    transfer_reference = Column(String, nullable=True)

    # Status tracking
    status = Column(String, nullable=False, default='pending')  # 'pending', 'processed', 'failed', 'cancelled'
    processed_date = Column(DateTime, nullable=True)
    failure_reason = Column(Text, nullable=True)

    # Accounting integration
    accounting_entry_id = Column(String, ForeignKey("accounting_entries.id"), nullable=True)

    # Audit
    created_at = Column(DateTime, default=datetime.now)
    processed_by = Column(String, ForeignKey("users.id"), nullable=True)

    # Relationships
    credit_note = relationship("CreditNote")
    bank_account = relationship("BankAccount")
    cash_account = relationship("AccountingCode")
    accounting_entry = relationship("AccountingEntry")
    processed_by_user = relationship("User")


# Add relationships to existing models
# These would need to be added to the actual model files

# In app/models/sales.py - Invoice model:
# credit_notes = relationship("CreditNote", back_populates="original_invoice")

# In app/models/customer.py - Customer model:
# credit_notes = relationship("CreditNote", back_populates="customer")

# In app/models/sales.py - InvoiceItem model:
# credit_note_items = relationship("CreditNoteItem", back_populates="original_invoice_item")
