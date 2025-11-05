"""
Inventory Allocation Models for Branch-Specific Inventory Management

This module defines models for:
- Branch Inventory Allocation: Track allocated inventory per branch
- Inventory Allocation Requests: Requests for inventory from branches
- Inventory Transfers: Track transfers between branches
- Branch Stock Holdings: Current stock levels per branch per product
"""

import uuid
from sqlalchemy import Column, String, Integer, Numeric, Boolean, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel
from datetime import datetime


class BranchInventoryAllocation(BaseModel):
    """Track allocated inventory levels for each branch per product"""
    __tablename__ = "branch_inventory_allocations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Core fields
    product_id = Column(ForeignKey("products.id"), nullable=False, index=True)
    branch_id = Column(ForeignKey("branches.id"), nullable=False, index=True)
    
    # Allocation quantities
    allocated_quantity = Column(Integer, default=0, nullable=False)
    received_quantity = Column(Integer, default=0, nullable=False)
    available_quantity = Column(Integer, default=0, nullable=False)
    reserved_quantity = Column(Integer, default=0, nullable=False)
    
    # Cost and pricing
    allocated_cost_per_unit = Column(Numeric(15, 2), nullable=False)
    total_allocated_cost = Column(Numeric(15, 2), nullable=False)
    branch_selling_price = Column(Numeric(15, 2))
    
    # Status and tracking
    allocation_status = Column(String, default='pending')
    allocation_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    expected_delivery_date = Column(Date)
    actual_delivery_date = Column(Date)
    
    # References
    allocated_by = Column(ForeignKey("users.id"))
    received_by = Column(ForeignKey("users.id"))
    
    # Notes and tracking
    notes = Column(Text)
    
    # Relationships
    product = relationship("Product")
    branch = relationship("Branch")
    allocated_by_user = relationship("User", foreign_keys=[allocated_by])
    received_by_user = relationship("User", foreign_keys=[received_by])
    allocation_reference = Column(String, unique=True)  # Reference number for tracking
    notes = Column(Text)
    transport_method = Column(String)  # truck, courier, pickup, etc.
    tracking_number = Column(String)
    
    # Reorder information
    minimum_stock_level = Column(Integer, default=0)  # Branch-specific minimum stock
    reorder_point = Column(Integer, default=5)        # When to request more stock
    maximum_stock_level = Column(Integer, default=100) # Branch storage capacity
    
    # Relationships
    product = relationship("Product", lazy="select")
    branch = relationship("Branch", lazy="select")
    allocated_by_user = relationship("User", foreign_keys=[allocated_by], lazy="select")
    received_by_user = relationship("User", foreign_keys=[received_by], lazy="select")
    allocation_requests = relationship("InventoryAllocationRequest", back_populates="allocation", lazy="select")
    allocation_movements = relationship("InventoryAllocationMovement", back_populates="allocation", lazy="select")


class InventoryAllocationRequest(BaseModel):
    """Requests from branches for inventory allocation"""
    __tablename__ = "inventory_allocation_requests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Request details
    requesting_branch_id = Column(ForeignKey("branches.id"), nullable=False)
    product_id = Column(ForeignKey("products.id"), nullable=False)
    requested_quantity = Column(Integer, nullable=False)
    approved_quantity = Column(Integer, default=0)
    
    # Request status and priority
    request_status = Column(String, default='pending')  # pending, approved, rejected, fulfilled, cancelled
    priority_level = Column(String, default='normal')   # urgent, high, normal, low
    
    # Justification and details
    reason = Column(String, nullable=False)  # restock, new_branch, promotion, seasonal, etc.
    justification = Column(Text)
    expected_usage_period = Column(String)  # weekly, monthly, quarterly
    
    # Dates and timing
    request_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    required_by_date = Column(Date)
    approved_date = Column(DateTime)
    fulfilled_date = Column(DateTime)
    
    # User tracking
    requested_by = Column(ForeignKey("users.id"), nullable=False)
    approved_by = Column(ForeignKey("users.id"))
    fulfilled_by = Column(ForeignKey("users.id"))
    
    # Reference and notes
    request_reference = Column(String, unique=True)
    internal_notes = Column(Text)  # For headquarters use
    branch_notes = Column(Text)    # For requesting branch
    
    # Linked allocation
    allocation_id = Column(ForeignKey("branch_inventory_allocations.id"))
    
    # Relationships
    requesting_branch = relationship("Branch", lazy="select")
    product = relationship("Product", lazy="select")
    requested_by_user = relationship("User", foreign_keys=[requested_by], lazy="select")
    approved_by_user = relationship("User", foreign_keys=[approved_by], lazy="select")
    fulfilled_by_user = relationship("User", foreign_keys=[fulfilled_by], lazy="select")
    allocation = relationship("BranchInventoryAllocation", back_populates="allocation_requests", lazy="select")


class InventoryAllocationMovement(BaseModel):
    """Track all movements of allocated inventory (shipping, receiving, adjustments)"""
    __tablename__ = "inventory_allocation_movements"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Movement details
    allocation_id = Column(ForeignKey("branch_inventory_allocations.id"), nullable=False)
    movement_type = Column(String, nullable=False)  # shipped, received, adjusted, returned, damaged
    quantity = Column(Integer, nullable=False)
    
    # Movement metadata
    movement_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    reference_number = Column(String)
    
    # User and location tracking
    processed_by = Column(ForeignKey("users.id"))
    from_location = Column(String)  # headquarters, branch_warehouse, in_transit
    to_location = Column(String)
    
    # Cost tracking
    unit_cost = Column(Numeric(15, 2))
    total_cost = Column(Numeric(15, 2))
    
    # Additional details
    notes = Column(Text)
    related_transaction_id = Column(ForeignKey("inventory_transactions.id"))  # Link to inventory transaction
    
    # Relationships
    allocation = relationship("BranchInventoryAllocation", back_populates="allocation_movements", lazy="select")
    processed_by_user = relationship("User", lazy="select")
    related_transaction = relationship("InventoryTransaction", lazy="select")


class BranchStockSnapshot(BaseModel):
    """Daily snapshots of branch stock levels for reporting and analysis"""
    __tablename__ = "branch_stock_snapshots"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Snapshot details
    snapshot_date = Column(Date, nullable=False, index=True)
    branch_id = Column(ForeignKey("branches.id"), nullable=False, index=True)
    product_id = Column(ForeignKey("products.id"), nullable=False, index=True)
    
    # Stock quantities at snapshot time
    available_quantity = Column(Integer, default=0)
    reserved_quantity = Column(Integer, default=0)
    total_quantity = Column(Integer, default=0)
    
    # Values at snapshot time
    cost_per_unit = Column(Numeric(15, 2))
    selling_price_per_unit = Column(Numeric(15, 2))
    total_cost_value = Column(Numeric(15, 2))
    total_selling_value = Column(Numeric(15, 2))
    
    # Movement counters for the day
    units_sold = Column(Integer, default=0)
    units_received = Column(Integer, default=0)
    units_adjusted = Column(Integer, default=0)
    units_transferred_out = Column(Integer, default=0)
    units_transferred_in = Column(Integer, default=0)
    
    # Status flags
    is_low_stock = Column(Boolean, default=False)
    is_out_of_stock = Column(Boolean, default=False)
    requires_reorder = Column(Boolean, default=False)
    
    # Relationships
    branch = relationship("Branch", lazy="select")
    product = relationship("Product", lazy="select")


class HeadquartersInventory(BaseModel):
    """Track inventory levels at headquarters for allocation to branches"""
    __tablename__ = "headquarters_inventory"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Product and quantities
    product_id = Column(ForeignKey("products.id"), nullable=False, index=True)
    
    # Headquarters stock levels
    total_received_quantity = Column(Integer, default=0)      # Total received from suppliers
    total_allocated_quantity = Column(Integer, default=0)     # Total allocated to branches
    available_for_allocation = Column(Integer, default=0)     # Available to allocate
    reserved_for_allocation = Column(Integer, default=0)      # Reserved for pending allocations
    damaged_quantity = Column(Integer, default=0)             # Damaged/unsellable stock
    
    # Cost tracking
    average_cost_per_unit = Column(Numeric(15, 2), default=0)
    total_cost_value = Column(Numeric(15, 2), default=0)
    
    # Reorder management
    minimum_hq_stock = Column(Integer, default=0)    # Minimum stock to maintain at HQ
    reorder_point = Column(Integer, default=10)      # When to reorder from supplier
    maximum_hq_stock = Column(Integer, default=1000) # Maximum storage capacity
    
    # Status and metadata
    last_received_date = Column(Date)
    last_allocated_date = Column(Date)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", lazy="select")
