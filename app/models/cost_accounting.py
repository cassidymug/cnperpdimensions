from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base



    # ...existing code...


class ManufacturingCost(Base):
    """Manufacturing Cost model"""
    __tablename__ = "manufacturing_costs"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    product_id = Column(String, ForeignKey("products.id"))
    batch_number = Column(String(50))
    batch_size = Column(Float)
    
    # Cost components
    material_cost = Column(Float, default=0.0)
    labor_cost = Column(Float, default=0.0)
    overhead_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    unit_cost = Column(Float, default=0.0)
    
    notes = Column(Text, nullable=True)
    status = Column(String(20), default="draft")  # draft, in_progress, completed
    
    # Relationships
    product = relationship("Product", back_populates="manufacturing_costs")
    material_entries = relationship("MaterialCostEntry", back_populates="manufacturing_cost", cascade="all, delete-orphan")
    labor_entries = relationship("LaborCostEntry", back_populates="manufacturing_cost", cascade="all, delete-orphan")
    overhead_entries = relationship("OverheadCostEntry", back_populates="manufacturing_cost", cascade="all, delete-orphan")


class MaterialCostEntry(Base):
    """Material cost entry for manufacturing"""
    __tablename__ = "material_cost_entries"

    id = Column(Integer, primary_key=True, index=True)
    manufacturing_cost_id = Column(Integer, ForeignKey("manufacturing_costs.id"))
    material_id = Column(String, ForeignKey("products.id"))
    quantity = Column(Float)
    unit_cost = Column(Float)
    total_cost = Column(Float)
    description = Column(Text, nullable=True)
    
    # Relationships
    manufacturing_cost = relationship("ManufacturingCost", back_populates="material_entries")
    material = relationship("Product")


class LaborCostEntry(Base):
    """Labor cost entry for manufacturing"""
    __tablename__ = "labor_cost_entries"

    id = Column(Integer, primary_key=True, index=True)
    manufacturing_cost_id = Column(Integer, ForeignKey("manufacturing_costs.id"))
    hours = Column(Float)
    rate = Column(Float)
    total_cost = Column(Float)
    description = Column(Text, nullable=True)
    
    # Relationships
    manufacturing_cost = relationship("ManufacturingCost", back_populates="labor_entries")


class OverheadCostEntry(Base):
    """Overhead cost entry for manufacturing"""
    __tablename__ = "overhead_cost_entries"

    id = Column(Integer, primary_key=True, index=True)
    manufacturing_cost_id = Column(Integer, ForeignKey("manufacturing_costs.id"))
    name = Column(String(100))
    amount = Column(Float)
    description = Column(Text, nullable=True)
    
    # Relationships
    manufacturing_cost = relationship("ManufacturingCost", back_populates="overhead_entries")