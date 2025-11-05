import uuid
from sqlalchemy import Column, String, Text, Date, ForeignKey, Numeric, Integer, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ProcurementRequisition(BaseModel):
    __tablename__ = "procurement_requisitions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    title = Column(String, nullable=False)
    description = Column(Text)
    requested_by = Column(ForeignKey("users.id"))
    branch_id = Column(ForeignKey("branches.id"))
    status = Column(String, default="draft")  # draft, submitted, approved, rejected, converted
    needed_by = Column(Date)
    budget_code_id = Column(ForeignKey("accounting_codes.id"))
    notes = Column(Text)
    supplier_id = Column(ForeignKey("suppliers.id"))

    requested_by_user = relationship("User")
    branch = relationship("Branch")
    budget_code = relationship("AccountingCode")
    items = relationship("ProcurementRequisitionItem", back_populates="requisition")
    supplier = relationship("Supplier")


class ProcurementRequisitionItem(BaseModel):
    __tablename__ = "procurement_requisition_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    requisition_id = Column(ForeignKey("procurement_requisitions.id"), nullable=False)
    product_id = Column(ForeignKey("products.id"), nullable=True)
    description = Column(Text, nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_of_measure = Column(String)
    estimated_unit_cost = Column(Numeric(15, 2))
    total_estimated_cost = Column(Numeric(15, 2))

    requisition = relationship("ProcurementRequisition", back_populates="items")
    product = relationship("Product")


class RFQ(BaseModel):
    __tablename__ = "rfqs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    requisition_id = Column(ForeignKey("procurement_requisitions.id"), nullable=True)
    rfq_number = Column(String, unique=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    issue_date = Column(Date)
    closing_date = Column(Date)
    status = Column(String, default="draft")  # draft, issued, closed, evaluated, awarded, cancelled
    branch_id = Column(ForeignKey("branches.id"))

    requisition = relationship("ProcurementRequisition")
    branch = relationship("Branch")
    invites = relationship("RFQInvite", back_populates="rfq")
    quotes = relationship("SupplierQuote", back_populates="rfq")


class RFQInvite(BaseModel):
    __tablename__ = "rfq_invites"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    rfq_id = Column(ForeignKey("rfqs.id"), nullable=False)
    supplier_id = Column(ForeignKey("suppliers.id"), nullable=False)
    invited = Column(Boolean, default=True)
    responded = Column(Boolean, default=False)
    notes = Column(Text)

    rfq = relationship("RFQ", back_populates="invites")
    supplier = relationship("Supplier")


class SupplierQuote(BaseModel):
    __tablename__ = "supplier_quotes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    rfq_id = Column(ForeignKey("rfqs.id"), nullable=False)
    supplier_id = Column(ForeignKey("suppliers.id"), nullable=False)
    quote_number = Column(String)
    quote_date = Column(Date)
    total_amount = Column(Numeric(15, 2))
    total_vat_amount = Column(Numeric(15, 2), default=0)
    currency = Column(String, default="BWP")
    valid_until = Column(Date)
    status = Column(String, default="submitted")  # submitted, shortlisted, rejected, awarded
    notes = Column(Text)

    rfq = relationship("RFQ", back_populates="quotes")
    supplier = relationship("Supplier")
    items = relationship("SupplierQuoteItem", back_populates="quote")


class SupplierQuoteItem(BaseModel):
    __tablename__ = "supplier_quote_items"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    quote_id = Column(ForeignKey("supplier_quotes.id"), nullable=False)
    product_id = Column(ForeignKey("products.id"), nullable=True)
    description = Column(Text, nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False)
    unit_cost = Column(Numeric(15, 2))
    total_cost = Column(Numeric(15, 2))
    vat_rate = Column(Numeric(8, 4), default=0)
    vat_amount = Column(Numeric(15, 2), default=0)

    quote = relationship("SupplierQuote", back_populates="items")
    product = relationship("Product")


class ProcurementAward(BaseModel):
    __tablename__ = "procurement_awards"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    rfq_id = Column(ForeignKey("rfqs.id"), nullable=True)
    quote_id = Column(ForeignKey("supplier_quotes.id"), nullable=False)
    award_number = Column(String, unique=True)
    award_date = Column(Date)
    status = Column(String, default="awarded")  # awarded, converted_to_po, cancelled
    notes = Column(Text)
    branch_id = Column(ForeignKey("branches.id"))
    purchase_order_id = Column(ForeignKey("purchase_orders.id"), nullable=True)

    rfq = relationship("RFQ")
    quote = relationship("SupplierQuote")
    branch = relationship("Branch")
    purchase_order = relationship("PurchaseOrder")


class SupplierPerformance(BaseModel):
    __tablename__ = "supplier_performance"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    supplier_id = Column(ForeignKey("suppliers.id"), nullable=False)
    period_start = Column(Date)
    period_end = Column(Date)
    on_time_delivery_score = Column(Integer, default=0)  # 0-100
    quality_score = Column(Integer, default=0)          # 0-100
    responsiveness_score = Column(Integer, default=0)   # 0-100
    compliance_score = Column(Integer, default=0)       # 0-100
    overall_score = Column(Integer, default=0)
    notes = Column(Text)

    supplier = relationship("Supplier")


class SupplierEvaluationTicket(BaseModel):
    __tablename__ = "supplier_evaluation_tickets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    supplier_id = Column(ForeignKey("suppliers.id"), nullable=False)
    purchase_order_id = Column(ForeignKey("purchase_orders.id"), nullable=False)
    status = Column(String, default="open")  # open, in_progress, closed
    opened_at = Column(Date)
    closed_at = Column(Date)
    branch_id = Column(ForeignKey("branches.id"))
    notes = Column(Text)

    supplier = relationship("Supplier")
    purchase_order = relationship("PurchaseOrder")
    milestones = relationship("SupplierEvaluationMilestone", back_populates="ticket")


class SupplierEvaluationMilestone(BaseModel):
    __tablename__ = "supplier_evaluation_milestones"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    ticket_id = Column(ForeignKey("supplier_evaluation_tickets.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    sequence = Column(Integer, default=0)
    status = Column(String, default="pending")  # pending, in_progress, completed, skipped
    due_date = Column(Date)
    completed_at = Column(Date)
    notes = Column(Text)

    ticket = relationship("SupplierEvaluationTicket", back_populates="milestones")

