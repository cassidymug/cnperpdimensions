"""
Accounting Dimensions Module

This module provides multi-dimensional analysis capabilities for financial data.
Dimensions allow you to analyze transactions and balances across various business segments
such as departments, projects, cost centers, geographical regions, etc.

Key Concepts:
- Dimension: A business perspective (e.g., Department, Project, Product Line)
- Dimension Value: Specific instances within a dimension (e.g., Sales Dept, Marketing Dept)
- Dimension Assignment: Links transactions to dimension values for analysis
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Numeric, DateTime,
    ForeignKey, UniqueConstraint, Index, CheckConstraint
)
from sqlalchemy.orm import relationship, validates
from enum import Enum

from app.models.base import BaseModel


class DimensionType(str, Enum):
    """Types of dimensions for categorization and validation"""
    ORGANIZATIONAL = "organizational"  # Departments, divisions, subsidiaries
    GEOGRAPHICAL = "geographical"     # Regions, countries, branches, locations
    FUNCTIONAL = "functional"         # Cost centers, profit centers, business units
    PROJECT = "project"              # Projects, campaigns, initiatives
    PRODUCT = "product"              # Product lines, categories, brands
    CUSTOMER = "customer"            # Customer segments, channels, types
    TEMPORAL = "temporal"            # Fiscal periods, seasons, quarters
    CUSTOM = "custom"                # User-defined dimensions


class DimensionScope(str, Enum):
    """Scope of dimension application"""
    GLOBAL = "global"        # Available across all branches/entities
    BRANCH = "branch"        # Specific to a branch
    ENTITY = "entity"        # Specific to a legal entity
    DEPARTMENT = "department" # Specific to a department


class AccountingDimension(BaseModel):
    """
    Defines a dimension for multi-dimensional analysis.

    Examples:
    - Department: Sales, Marketing, Finance, Operations
    - Project: Project Alpha, Project Beta, Project Gamma
    - Geography: North Region, South Region, Central Region
    - Product Line: Hardware, Software, Services
    """
    __tablename__ = "accounting_dimensions"

    __table_args__ = (
        UniqueConstraint('code', 'branch_id', name='uq_dimension_code_branch'),
        Index('idx_dimension_type_active', 'dimension_type', 'is_active'),
        Index('idx_dimension_scope', 'scope'),
        {
            'comment': 'Defines business dimensions for multi-dimensional financial analysis'
        }
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Basic Information
    code = Column(String(20), nullable=False, index=True,
                 comment='Unique code for the dimension (e.g., DEPT, PROJ, GEO)')

    name = Column(String(100), nullable=False,
                 comment='Display name of the dimension')

    description = Column(Text,
                        comment='Detailed description of the dimension purpose')

    # Categorization
    dimension_type = Column(String(20), nullable=False, default=DimensionType.CUSTOM,
                           comment='Type/category of the dimension')

    scope = Column(String(20), nullable=False, default=DimensionScope.GLOBAL,
                  comment='Scope of dimension application')

    # Configuration
    is_active = Column(Boolean, default=True, nullable=False,
                      comment='Whether this dimension is active for use')

    is_required = Column(Boolean, default=False, nullable=False,
                        comment='Whether this dimension must be specified on transactions')

    allow_multiple_values = Column(Boolean, default=False, nullable=False,
                                  comment='Whether transactions can have multiple values for this dimension')

    # Hierarchy Support
    supports_hierarchy = Column(Boolean, default=False, nullable=False,
                               comment='Whether dimension values can be hierarchical')

    max_hierarchy_levels = Column(Integer, default=1, nullable=False,
                                 comment='Maximum levels in hierarchy (1 = flat)')

    # Display and Ordering
    display_order = Column(Integer, default=0, nullable=False,
                          comment='Order for displaying dimensions in UI')

    # Branch/Entity Association
    branch_id = Column(String(36), ForeignKey("branches.id"), nullable=True,
                      comment='Branch this dimension belongs to (null = global)')

    # Audit fields inherited from BaseModel

    # Relationships
    dimension_values = relationship("AccountingDimensionValue", back_populates="dimension",
                                   cascade="all, delete-orphan")
    branch = relationship("Branch")

    @validates('dimension_type')
    def validate_dimension_type(self, key, value):
        if value not in [e.value for e in DimensionType]:
            raise ValueError(f"Invalid dimension type: {value}")
        return value

    @validates('scope')
    def validate_scope(self, key, value):
        if value not in [e.value for e in DimensionScope]:
            raise ValueError(f"Invalid scope: {value}")
        return value

    @validates('max_hierarchy_levels')
    def validate_hierarchy_levels(self, key, value):
        if value < 1 or value > 10:
            raise ValueError("Hierarchy levels must be between 1 and 10")
        return value

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'dimension_type': self.dimension_type,
            'scope': self.scope,
            'is_active': self.is_active,
            'is_required': self.is_required,
            'allow_multiple_values': self.allow_multiple_values,
            'supports_hierarchy': self.supports_hierarchy,
            'max_hierarchy_levels': self.max_hierarchy_levels,
            'display_order': self.display_order,
            'branch_id': self.branch_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class AccountingDimensionValue(BaseModel):
    """
    Specific values within a dimension.

    Examples for Department dimension:
    - Sales Department
    - Marketing Department
    - Finance Department
    """
    __tablename__ = "accounting_dimension_values"

    __table_args__ = (
        UniqueConstraint('dimension_id', 'code', name='uq_dimension_value_code'),
        Index('idx_dimension_value_active', 'dimension_id', 'is_active'),
        Index('idx_dimension_value_hierarchy', 'parent_value_id'),
        {
            'comment': 'Specific values within accounting dimensions'
        }
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Dimension Association
    dimension_id = Column(String(36), ForeignKey("accounting_dimensions.id"),
                         nullable=False, index=True)

    # Basic Information
    code = Column(String(50), nullable=False,
                 comment='Unique code within the dimension')

    name = Column(String(100), nullable=False,
                 comment='Display name of the dimension value')

    description = Column(Text,
                        comment='Detailed description of this value')

    # Hierarchy Support
    parent_value_id = Column(String(36), ForeignKey("accounting_dimension_values.id"),
                            nullable=True, index=True,
                            comment='Parent value for hierarchical dimensions')

    hierarchy_level = Column(Integer, default=1, nullable=False,
                            comment='Level in hierarchy (1 = top level)')

    hierarchy_path = Column(String(500), nullable=True,
                           comment='Full path in hierarchy (e.g., /sales/retail/online)')

    # Configuration
    is_active = Column(Boolean, default=True, nullable=False,
                      comment='Whether this value is active for use')

    # Display and Ordering
    display_order = Column(Integer, default=0, nullable=False,
                          comment='Order for displaying values in UI')

    # Optional Integration References
    external_reference = Column(String(100), nullable=True,
                               comment='Reference to external system entity')

    # Relationships
    dimension = relationship("AccountingDimension", back_populates="dimension_values")
    parent_value = relationship("AccountingDimensionValue", remote_side=[id],
                               back_populates="child_values")
    child_values = relationship("AccountingDimensionValue", back_populates="parent_value",
                               cascade="all, delete-orphan")

    # Transaction assignments (defined in next model)
    transaction_assignments = relationship("AccountingDimensionAssignment",
                                         back_populates="dimension_value")

    @validates('hierarchy_level')
    def validate_hierarchy_level(self, key, value):
        if value < 1 or value > 10:
            raise ValueError("Hierarchy level must be between 1 and 10")
        return value

    @property
    def full_path(self) -> str:
        """Get the full hierarchical path of this value"""
        if not self.parent_value:
            return self.name

        path = [self.name]
        parent = self.parent_value
        while parent:
            path.append(parent.name)
            parent = parent.parent_value

        return ' > '.join(reversed(path))

    def get_full_path(self) -> str:
        """Get the full hierarchical path of this value (deprecated - use full_path property)"""
        return self.full_path

    def get_all_children(self, include_inactive: bool = False) -> List['AccountingDimensionValue']:
        """Get all child values recursively"""
        children = []
        for child in self.child_values:
            if child.is_active or include_inactive:
                children.append(child)
                children.extend(child.get_all_children(include_inactive))
        return children

    def to_dict(self, include_children: bool = False) -> Dict[str, Any]:
        result = {
            'id': self.id,
            'dimension_id': self.dimension_id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'parent_value_id': self.parent_value_id,
            'hierarchy_level': self.hierarchy_level,
            'hierarchy_path': self.hierarchy_path,
            'is_active': self.is_active,
            'display_order': self.display_order,
            'external_reference': self.external_reference,
            'full_path': self.get_full_path(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

        if include_children and self.child_values:
            result['children'] = [child.to_dict(include_children=True)
                                for child in self.child_values if child.is_active]

        return result


class AccountingDimensionAssignment(BaseModel):
    """
    Links transactions/entries to dimension values for multi-dimensional analysis.

    This table creates the many-to-many relationship between financial transactions
    and dimension values, enabling slicing and dicing of financial data.
    """
    __tablename__ = "accounting_dimension_assignments"

    __table_args__ = (
        UniqueConstraint('journal_entry_id', 'dimension_id', name='uq_assignment_entry_dimension'),
        Index('idx_assignment_dimension_value', 'dimension_value_id'),
        Index('idx_assignment_journal_entry', 'journal_entry_id'),
        Index('idx_assignment_dimension', 'dimension_id'),
        {
            'comment': 'Links journal entries to dimension values for multi-dimensional analysis'
        }
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Link to financial transaction
    journal_entry_id = Column(String(36), ForeignKey("journal_entries.id"),
                             nullable=False, index=True,
                             comment='Journal entry this assignment belongs to')

    # Dimension information
    dimension_id = Column(String(36), ForeignKey("accounting_dimensions.id"),
                         nullable=False, index=True,
                         comment='Dimension being assigned')

    dimension_value_id = Column(String(36), ForeignKey("accounting_dimension_values.id"),
                               nullable=False, index=True,
                               comment='Specific dimension value assigned')

    # Optional allocation percentage (for split transactions)
    allocation_percentage = Column(Numeric(5, 2), default=100.00, nullable=False,
                                  comment='Percentage of transaction allocated to this dimension value')

    allocation_amount = Column(Numeric(15, 2), nullable=True,
                              comment='Specific amount allocated (calculated or manually set)')

    # Assignment metadata
    assignment_method = Column(String(20), default='manual', nullable=False,
                              comment='How assignment was made: manual, automatic, inherited')

    notes = Column(Text,
                  comment='Additional notes about this dimension assignment')

    # Relationships
    journal_entry = relationship("JournalEntry")
    dimension = relationship("AccountingDimension")
    dimension_value = relationship("AccountingDimensionValue", back_populates="transaction_assignments")

    @validates('allocation_percentage')
    def validate_allocation_percentage(self, key, value):
        if value < 0 or value > 100:
            raise ValueError("Allocation percentage must be between 0 and 100")
        return value

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'journal_entry_id': self.journal_entry_id,
            'dimension_id': self.dimension_id,
            'dimension_value_id': self.dimension_value_id,
            'allocation_percentage': float(self.allocation_percentage) if self.allocation_percentage else 100.0,
            'allocation_amount': float(self.allocation_amount) if self.allocation_amount else None,
            'assignment_method': self.assignment_method,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DimensionTemplate(BaseModel):
    """
    Pre-defined templates for common dimension setups to speed up implementation.

    Templates provide standard dimension configurations for different business types
    or accounting requirements.
    """
    __tablename__ = "dimension_templates"

    __table_args__ = (
        UniqueConstraint('code', name='uq_template_code'),
        {
            'comment': 'Pre-defined templates for dimension setups'
        }
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    code = Column(String(50), nullable=False, unique=True,
                 comment='Unique template code')

    name = Column(String(100), nullable=False,
                 comment='Template name')

    description = Column(Text,
                        comment='Description of template and use cases')

    business_type = Column(String(50), nullable=True,
                          comment='Type of business this template suits')

    template_data = Column(Text, nullable=False,
                          comment='JSON configuration data for dimensions and values')

    is_active = Column(Boolean, default=True, nullable=False)

    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False,
                        comment='Number of times this template has been used')

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'description': self.description,
            'business_type': self.business_type,
            'template_data': self.template_data,
            'is_active': self.is_active,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
