"""
Accounting Code Dimension Requirements

This module defines the relationship between accounting codes and dimensions,
allowing specific accounts to require or suggest certain dimensions when used in transactions.
"""

import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, Text, UniqueConstraint, Index
from sqlalchemy.orm import relationship, validates
from typing import Optional, Dict, Any
from app.models.base import BaseModel


class AccountingCodeDimensionRequirement(BaseModel):
    """
    Defines dimension requirements for specific accounting codes.

    This allows the system to enforce or suggest specific dimensions
    when transactions are posted to certain accounts.
    """
    __tablename__ = "accounting_code_dimension_requirements"

    __table_args__ = (
        UniqueConstraint('accounting_code_id', 'dimension_id',
                        name='uq_account_dimension_requirement'),
        Index('idx_account_dimension_code', 'accounting_code_id'),
        Index('idx_account_dimension_dim', 'dimension_id'),
        {
            'comment': 'Defines which dimensions are required or suggested for specific accounting codes'
        }
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    accounting_code_id = Column(String(36), ForeignKey("accounting_codes.id", ondelete='CASCADE'),
                               nullable=False, index=True,
                               comment='Reference to the accounting code')

    dimension_id = Column(String(36), ForeignKey("accounting_dimensions.id", ondelete='CASCADE'),
                         nullable=False, index=True,
                         comment='Reference to the required dimension')

    # Requirement Level
    is_required = Column(Boolean, default=False, nullable=False,
                        comment='Whether this dimension is required (True) or suggested (False)')

    # Default Values
    default_dimension_value_id = Column(String(36),
                                       ForeignKey("accounting_dimension_values.id", ondelete='SET NULL'),
                                       nullable=True,
                                       comment='Default dimension value to suggest')

    # Configuration
    priority = Column(Integer, default=1, nullable=False,
                     comment='Priority order for dimension display (lower numbers first)')

    description = Column(Text, nullable=True,
                        comment='Description of why this dimension is required for this account')

    # Relationships
    accounting_code = relationship("AccountingCode", back_populates="dimension_requirements")
    dimension = relationship("AccountingDimension")
    default_dimension_value = relationship("AccountingDimensionValue")

    @validates('priority')
    def validate_priority(self, key, value):
        if value < 1 or value > 100:
            raise ValueError("Priority must be between 1 and 100")
        return value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'accounting_code_id': self.accounting_code_id,
            'dimension_id': self.dimension_id,
            'is_required': self.is_required,
            'default_dimension_value_id': self.default_dimension_value_id,
            'priority': self.priority,
            'description': self.description,
            'dimension': {
                'id': self.dimension.id,
                'code': self.dimension.code,
                'name': self.dimension.name,
                'dimension_type': self.dimension.dimension_type
            } if self.dimension else None,
            'default_dimension_value': {
                'id': self.default_dimension_value.id,
                'code': self.default_dimension_value.code,
                'name': self.default_dimension_value.name,
                'full_path': self.default_dimension_value.full_path
            } if self.default_dimension_value else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class AccountingCodeDimensionTemplate(BaseModel):
    """
    Templates for applying dimension requirements to multiple accounting codes.

    Useful for setting up common dimension requirements across account types
    or categories (e.g., all expense accounts require Department dimension).
    """
    __tablename__ = "accounting_code_dimension_templates"

    __table_args__ = (
        Index('idx_template_account_type', 'account_type'),
        Index('idx_template_category', 'category'),
        {
            'comment': 'Templates for applying dimension requirements to groups of accounting codes'
        }
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Template Information
    name = Column(String(100), nullable=False,
                 comment='Name of the template')

    description = Column(Text, nullable=True,
                        comment='Description of the template purpose')

    # Account Filters
    account_type = Column(String(20), nullable=True,
                         comment='Apply to accounts of this type (Asset, Liability, etc.)')

    category = Column(String(50), nullable=True,
                     comment='Apply to accounts of this category')

    account_code_pattern = Column(String(50), nullable=True,
                                 comment='Apply to accounts matching this code pattern (e.g., "1*" for all assets)')

    # Template Status
    is_active = Column(Boolean, default=True, nullable=False,
                      comment='Whether this template is active')

    # Relationships
    dimension_requirements = relationship("AccountingCodeDimensionTemplateItem",
                                        back_populates="template",
                                        cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'account_type': self.account_type,
            'category': self.category,
            'account_code_pattern': self.account_code_pattern,
            'is_active': self.is_active,
            'dimension_requirements': [req.to_dict() for req in self.dimension_requirements],
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class AccountingCodeDimensionTemplateItem(BaseModel):
    """
    Individual dimension requirements within a template.
    """
    __tablename__ = "accounting_code_dimension_template_items"

    __table_args__ = (
        UniqueConstraint('template_id', 'dimension_id',
                        name='uq_template_dimension'),
        Index('idx_template_item_template', 'template_id'),
        Index('idx_template_item_dimension', 'dimension_id'),
        {
            'comment': 'Individual dimension requirements within dimension templates'
        }
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Keys
    template_id = Column(String(36), ForeignKey("accounting_code_dimension_templates.id", ondelete='CASCADE'),
                        nullable=False, index=True,
                        comment='Reference to the template')

    dimension_id = Column(String(36), ForeignKey("accounting_dimensions.id", ondelete='CASCADE'),
                         nullable=False, index=True,
                         comment='Reference to the dimension')

    # Requirements
    is_required = Column(Boolean, default=False, nullable=False,
                        comment='Whether this dimension is required')

    default_dimension_value_id = Column(String(36),
                                       ForeignKey("accounting_dimension_values.id", ondelete='SET NULL'),
                                       nullable=True,
                                       comment='Default dimension value')

    priority = Column(Integer, default=1, nullable=False,
                     comment='Priority order for dimension display')

    # Relationships
    template = relationship("AccountingCodeDimensionTemplate", back_populates="dimension_requirements")
    dimension = relationship("AccountingDimension")
    default_dimension_value = relationship("AccountingDimensionValue")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'template_id': self.template_id,
            'dimension_id': self.dimension_id,
            'is_required': self.is_required,
            'default_dimension_value_id': self.default_dimension_value_id,
            'priority': self.priority,
            'dimension': {
                'id': self.dimension.id,
                'code': self.dimension.code,
                'name': self.dimension.name,
                'dimension_type': self.dimension.dimension_type
            } if self.dimension else None,
            'default_dimension_value': {
                'id': self.default_dimension_value.id,
                'code': self.default_dimension_value.code,
                'name': self.default_dimension_value.name,
                'full_path': self.default_dimension_value.full_path
            } if self.default_dimension_value else None,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
