"""
COGS Allocation Models for Manufacturing + Sales Integration

This module provides tracking of Cost of Goods Sold allocation from production
to sales invoices, enabling accurate gross margin and profitability analysis by dimension.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.base import BaseModel


class COGSAllocation(BaseModel):
    """
    COGS Allocation - Links ProductionOrder costs to Invoice revenue

    When an invoice is posted to GL, this record tracks which production order's
    cost was used as COGS for that sale. Enables reconciliation of:
    - Revenue (from Invoice GL entry)
    - COGS (from ProductionOrder GL entry)
    - Gross Margin = Revenue - COGS

    Tracks dimensions for variance analysis:
    - If Revenue cost_center != COGS cost_center = dimensional variance
    """
    __tablename__ = "cogs_allocations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Links to source data
    production_order_id = Column(String, ForeignKey("production_orders.id"), nullable=False, index=True)
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=False, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)

    # Quantity and Cost Tracking
    quantity_produced = Column(Numeric(15, 2), nullable=False)  # How much was made
    quantity_sold = Column(Numeric(15, 2), nullable=False)      # How much was sold
    cost_per_unit = Column(Numeric(15, 4), nullable=False)      # Manufacturing cost per unit
    total_cogs = Column(Numeric(15, 2), nullable=False)         # Total COGS = qty_sold * cost_per_unit

    # GL Entry Links for audit trail
    revenue_gl_entry_id = Column(String, ForeignKey("journal_entries.id"), nullable=False)
    cogs_gl_entry_id = Column(String, ForeignKey("journal_entries.id"), nullable=False)

    # Dimension tracking from both Production and Sales
    # Production Order dimensions (where product was made)
    production_cost_center_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)
    production_project_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)
    production_department_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)

    # Invoice dimensions (where product was sold)
    sales_cost_center_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)
    sales_project_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)
    sales_department_id = Column(String, ForeignKey("accounting_dimension_values.id"), nullable=True)

    # Variance Detection
    has_dimension_variance = Column(String, default="false")  # true if prod vs sales dimensions differ
    variance_reason = Column(String(255), nullable=True)  # e.g., "COST_CENTER_MISMATCH"

    # Audit Trail
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)

    # Relationships
    production_order = relationship("ProductionOrder", foreign_keys=[production_order_id])
    invoice = relationship("Invoice", foreign_keys=[invoice_id])
    product = relationship("Product", foreign_keys=[product_id])
    revenue_gl_entry = relationship("JournalEntry", foreign_keys=[revenue_gl_entry_id])
    cogs_gl_entry = relationship("JournalEntry", foreign_keys=[cogs_gl_entry_id])

    # Dimension relationships from Production
    production_cost_center = relationship("AccountingDimensionValue", foreign_keys=[production_cost_center_id])
    production_project = relationship("AccountingDimensionValue", foreign_keys=[production_project_id])
    production_department = relationship("AccountingDimensionValue", foreign_keys=[production_department_id])

    # Dimension relationships from Sales
    sales_cost_center = relationship("AccountingDimensionValue", foreign_keys=[sales_cost_center_id])
    sales_project = relationship("AccountingDimensionValue", foreign_keys=[sales_project_id])
    sales_department = relationship("AccountingDimensionValue", foreign_keys=[sales_department_id])

    created_by_user = relationship("User", foreign_keys=[created_by])

    # Indexes for common queries
    __table_args__ = (
        Index("idx_cogs_allocations_po", "production_order_id"),
        Index("idx_cogs_allocations_invoice", "invoice_id"),
        Index("idx_cogs_allocations_product", "product_id"),
        Index("idx_cogs_allocations_variance", "has_dimension_variance"),
        Index("idx_cogs_allocations_created", "created_at"),
    )

    def __repr__(self):
        return f"<COGSAllocation invoice={self.invoice_id} cogs={self.total_cogs:.2f} variance={self.has_dimension_variance}>"
