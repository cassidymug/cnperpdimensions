"""
Credit Note Pydantic Schemas

Data validation and serialization schemas for credit note operations.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class ReturnReasonEnum(str, Enum):
    """Valid return reasons"""
    FAULTY_PRODUCT = "faulty_product"
    WRONG_ITEM = "wrong_item"
    DAMAGED = "damaged"
    CUSTOMER_REQUEST = "customer_request"
    DUPLICATE_ORDER = "duplicate_order"
    QUALITY_ISSUE = "quality_issue"
    SIZE_ISSUE = "size_issue"
    COLOR_ISSUE = "color_issue"
    OTHER = "other"


class RefundMethodEnum(str, Enum):
    """Valid refund methods"""
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    CREDIT_ADJUSTMENT = "credit_adjustment"
    STORE_CREDIT = "store_credit"


class ItemConditionEnum(str, Enum):
    """Condition of returned items"""
    UNOPENED = "unopened"
    GOOD = "good"
    USED = "used"
    DAMAGED = "damaged"
    FAULTY = "faulty"


class CreditNoteStatusEnum(str, Enum):
    """Credit note status values"""
    DRAFT = "draft"
    ISSUED = "issued"
    PROCESSED = "processed"
    CANCELLED = "cancelled"


class RefundStatusEnum(str, Enum):
    """Refund processing status"""
    PENDING = "pending"
    PROCESSED = "processed"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceTypeEnum(str, Enum):
    """Source document type for credit notes"""
    INVOICE = "invoice"
    POS_RECEIPT = "pos_receipt"


# Request Schemas

class CreditNoteItemCreate(BaseModel):
    """Schema for creating a credit note item"""
    product_id: str = Field(..., description="Product ID being returned")
    quantity_returned: Decimal = Field(..., gt=0, description="Quantity being returned")
    item_condition: ItemConditionEnum = Field(default=ItemConditionEnum.UNOPENED)
    return_reason: ReturnReasonEnum = Field(..., description="Reason for returning this item")
    description: Optional[str] = Field(None, max_length=500, description="Additional description")
    serial_numbers: Optional[List[str]] = Field(None, description="Serial numbers of returned items")


class CreditNoteCreate(BaseModel):
    """Schema for creating a credit note"""
    source_type: SourceTypeEnum = Field(..., description="Source document type (invoice or pos_receipt)")
    source_id: str = Field(..., description="ID of source document (invoice or sale)")
    # Legacy support - auto-populated based on source_type
    invoice_id: Optional[str] = Field(None, description="Invoice ID (for backward compatibility)")
    sale_id: Optional[str] = Field(None, description="Sale/POS Receipt ID (for POS credit notes)")

    return_items: List[CreditNoteItemCreate] = Field(..., min_length=1, description="Items being returned")
    return_reason: ReturnReasonEnum = Field(..., description="Main reason for return")
    return_description: Optional[str] = Field(None, max_length=1000, description="Additional details")
    refund_method: RefundMethodEnum = Field(default=RefundMethodEnum.CASH, description="How refund will be processed")

    # Dimensional accounting fields
    cost_center_id: Optional[str] = Field(None, description="Cost center for dimensional accounting")
    project_id: Optional[str] = Field(None, description="Project for dimensional accounting")

    @field_validator('return_items')
    @classmethod
    def validate_return_items(cls, v):
        if not v:
            raise ValueError("At least one item must be returned")
        return v

    @field_validator('source_id')
    @classmethod
    def validate_source_id(cls, v, info):
        """Auto-populate invoice_id or sale_id based on source_type"""
        # This will be handled in the service layer
        return v


class RefundTransactionCreate(BaseModel):
    """Schema for processing a refund"""
    bank_account_id: Optional[str] = Field(None, description="Bank account ID for transfers")
    cash_account_id: Optional[str] = Field(None, description="Cash account ID for cash refunds")
    reference_number: Optional[str] = Field(None, description="Transaction reference number")
    customer_bank_name: Optional[str] = Field(None, description="Customer's bank name")
    customer_account_number: Optional[str] = Field(None, description="Customer's account number")
    customer_account_name: Optional[str] = Field(None, description="Customer's account name")
    transfer_reference: Optional[str] = Field(None, description="Bank transfer reference")
    notes: Optional[str] = Field(None, max_length=500, description="Processing notes")


class CreditNoteStatusUpdate(BaseModel):
    """Schema for updating credit note status"""
    status: CreditNoteStatusEnum = Field(..., description="New status")
    notes: Optional[str] = Field(None, max_length=500, description="Status change notes")


# Response Schemas

class CreditNoteItemResponse(BaseModel):
    """Schema for credit note item response"""
    id: str
    product_id: str
    original_invoice_item_id: Optional[str]
    quantity_returned: Decimal
    unit_price: Decimal
    discount_percentage: Decimal
    discount_amount: Decimal
    vat_rate: Decimal
    vat_amount: Decimal
    line_total: Decimal
    item_condition: str
    return_reason: str
    description: Optional[str]
    serial_numbers: Optional[str]

    # Product details (if loaded)
    product_name: Optional[str] = None
    product_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerResponse(BaseModel):
    """Basic customer information"""
    id: str
    name: str
    email: Optional[str]
    phone: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class InvoiceResponse(BaseModel):
    """Basic invoice information"""
    id: str
    invoice_number: str
    invoice_date: date
    total_amount: Decimal
    payment_method: str

    model_config = ConfigDict(from_attributes=True)


class SaleResponse(BaseModel):
    """Basic POS sale/receipt information"""
    id: str
    receipt_number: Optional[str] = None  # Human-readable receipt number
    date: datetime
    total_amount: Decimal
    payment_method: str
    reference: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class RefundTransactionResponse(BaseModel):
    """Schema for refund transaction response"""
    id: str
    credit_note_id: str
    transaction_date: date
    refund_method: str
    refund_amount: Decimal
    currency: str
    reference_number: Optional[str]
    customer_bank_name: Optional[str]
    customer_account_number: Optional[str]
    customer_account_name: Optional[str]
    transfer_reference: Optional[str]
    status: str
    processed_date: Optional[datetime]
    failure_reason: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreditNoteResponse(BaseModel):
    """Schema for full credit note response"""
    id: str
    credit_note_number: str
    issue_date: date
    source_type: str
    source_id: str
    original_invoice_id: Optional[str]
    original_sale_id: Optional[str]
    customer_id: str
    branch_id: str
    return_reason: str
    return_description: Optional[str]
    return_date: date
    subtotal: Decimal
    discount_amount: Decimal
    vat_amount: Decimal
    total_amount: Decimal
    refund_method: str
    refund_status: str
    refund_processed_date: Optional[date]
    refund_reference: Optional[str]
    status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Dimensional accounting fields
    cost_center_id: Optional[str] = None
    project_id: Optional[str] = None

    # Relationships
    credit_note_items: List[CreditNoteItemResponse] = []
    customer: Optional[CustomerResponse] = None
    original_invoice: Optional[InvoiceResponse] = None
    original_sale: Optional['SaleResponse'] = None

    # User information
    created_by_name: Optional[str] = None
    approved_by_name: Optional[str] = None
    processed_by_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CreditNoteSummary(BaseModel):
    """Schema for credit note summary (list view)"""
    id: str
    credit_note_number: str
    issue_date: date
    source_type: str
    source_document_number: Optional[str] = None  # Invoice number or receipt number
    customer_name: str
    total_amount: Decimal
    refund_method: str
    refund_status: str
    status: str
    return_reason: str

    model_config = ConfigDict(from_attributes=True)


class CreditNoteStats(BaseModel):
    """Credit note statistics"""
    total_credit_notes: int
    total_amount: Decimal
    pending_refunds_count: int
    pending_refunds_amount: Decimal
    processed_refunds_count: int
    processed_refunds_amount: Decimal

    by_reason: Dict[str, int] = {}
    by_refund_method: Dict[str, int] = {}
    by_status: Dict[str, int] = {}


# PDF Generation Schemas

class CreditNotePrintOptions(BaseModel):
    """Options for printing credit notes"""
    include_customer_details: bool = True
    include_original_invoice_details: bool = True
    include_return_reasons: bool = True
    include_refund_details: bool = True
    company_logo: bool = True
    show_serial_numbers: bool = False
    template: str = Field(default="standard", pattern="^(standard|detailed|summary)$")


class EmailCreditNoteRequest(BaseModel):
    """Request schema for emailing credit notes"""
    email_addresses: List[str] = Field(..., min_length=1)
    subject: Optional[str] = None
    message: Optional[str] = None
    include_pdf: bool = True
    copy_to_sender: bool = False

    @field_validator('email_addresses')
    @classmethod
    def validate_emails(cls, v):
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        for email in v:
            if not re.match(email_pattern, email):
                raise ValueError(f"Invalid email address: {email}")
        return v
