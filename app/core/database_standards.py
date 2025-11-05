"""
Database Standardization Patterns for CNPERP
Comprehensive database consistency framework with naming conventions,
foreign key constraints, audit trails, and performance optimizations.
"""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Index, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from typing import Optional

# Base model with standardized patterns
class CNPERPBaseModel:
    """
    Base model implementing CNPERP database standards:
    - UUID primary keys
    - Standardized naming conventions
    - Audit trail fields
    - Soft delete capability
    - Validation patterns
    """
    
    # Standard primary key - UUID for all entities
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Audit trail fields (required for all entities)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)
    updated_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)
    
    # Soft delete pattern
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)
    deleted_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    
    # Branch isolation for multi-tenancy
    branch_id = Column(UUID(as_uuid=True), ForeignKey('branches.id'), nullable=False, index=True)
    
    # Version control for optimistic locking
    version = Column(String, default='1.0.0', nullable=False)
    
    # Relationships for audit trail
    created_by = relationship("User", foreign_keys=[created_by_user_id], lazy='select')
    updated_by = relationship("User", foreign_keys=[updated_by_user_id], lazy='select')
    deleted_by = relationship("User", foreign_keys=[deleted_by_user_id], lazy='select')
    branch = relationship("Branch", lazy='select')

class DatabaseNamingConventions:
    """
    Standardized naming conventions for CNPERP database objects.
    
    Ensures consistency across all modules and prevents naming conflicts.
    """
    
    # Table naming patterns
    TABLE_PATTERNS = {
        'entities': '{module}_{entity_plural}',  # e.g., 'accounting_journal_entries'
        'junction': '{entity1}_{entity2}_junction',  # e.g., 'users_roles_junction'
        'audit': '{entity}_audit_log',  # e.g., 'purchases_audit_log'
        'settings': '{module}_settings',  # e.g., 'inventory_settings'
    }
    
    # Column naming patterns
    COLUMN_PATTERNS = {
        'primary_key': 'id',
        'foreign_key': '{referenced_table}_id',  # e.g., 'supplier_id'
        'boolean': 'is_{description}',  # e.g., 'is_active'
        'datetime': '{action}_at',  # e.g., 'created_at'
        'user_reference': '{action}_by_user_id',  # e.g., 'approved_by_user_id'
        'amount': '{description}_amount',  # e.g., 'total_amount'
        'status': '{entity}_status',  # e.g., 'purchase_status'
    }
    
    # Index naming patterns
    INDEX_PATTERNS = {
        'single': 'idx_{table}_{column}',
        'composite': 'idx_{table}_{column1}_{column2}',
        'unique': 'uq_{table}_{column}',
        'foreign_key': 'fk_{table}_{referenced_table}',
    }
    
    # Constraint naming patterns
    CONSTRAINT_PATTERNS = {
        'primary_key': 'pk_{table}',
        'foreign_key': 'fk_{table}_{referenced_table}_{column}',
        'unique': 'uq_{table}_{column}',
        'check': 'ck_{table}_{column}_{description}',
    }

class AuditTrailMixin:
    """
    Mixin providing comprehensive audit trail functionality.
    
    Automatically tracks:
    - Who created/updated/deleted records
    - When operations occurred
    - What changes were made
    - From which system/session
    """
    
    @validates('updated_at')
    def validate_updated_at(self, key, value):
        """Ensure updated_at is always current for modifications."""
        return datetime.utcnow()
    
    def soft_delete(self, user_id: Optional[str] = None):
        """Perform soft delete operation."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.deleted_by_user_id = user_id
        self.updated_at = datetime.utcnow()
        self.updated_by_user_id = user_id
    
    def restore(self, user_id: Optional[str] = None):
        """Restore soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by_user_id = None
        self.updated_at = datetime.utcnow()
        self.updated_by_user_id = user_id
    
    def to_audit_dict(self):
        """Convert to dictionary for audit logging."""
        return {
            'id': str(self.id),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by_user_id': str(self.created_by_user_id) if self.created_by_user_id else None,
            'updated_by_user_id': str(self.updated_by_user_id) if self.updated_by_user_id else None,
            'branch_id': str(self.branch_id) if self.branch_id else None,
            'is_deleted': self.is_deleted,
            'version': self.version,
        }

class ForeignKeyStandards:
    """
    Standardized foreign key constraints and relationships.
    
    Ensures referential integrity and proper cascading behavior.
    """
    
    # Standard foreign key configurations
    FK_PATTERNS = {
        'restrict': {
            'ondelete': 'RESTRICT',
            'onupdate': 'CASCADE'
        },
        'cascade': {
            'ondelete': 'CASCADE', 
            'onupdate': 'CASCADE'
        },
        'set_null': {
            'ondelete': 'SET NULL',
            'onupdate': 'CASCADE'
        },
        'soft_delete': {
            'ondelete': 'RESTRICT',  # Prevent deletion of referenced records
            'onupdate': 'CASCADE'
        }
    }
    
    # Module-specific foreign key rules
    MODULE_FK_RULES = {
        'purchases': {
            'supplier_id': 'restrict',  # Don't allow deleting suppliers with purchases
            'branch_id': 'restrict',    # Don't allow deleting branches with purchases
            'created_by_user_id': 'set_null',  # Allow user deletion
        },
        'inventory': {
            'product_id': 'restrict',   # Don't allow deleting products with stock
            'branch_id': 'restrict',    # Don't allow deleting branches with inventory
            'supplier_id': 'set_null',  # Allow supplier deletion
        },
        'accounting': {
            'account_id': 'restrict',   # Don't allow deleting accounts with entries
            'branch_id': 'restrict',    # Don't allow deleting branches with entries
            'created_by_user_id': 'set_null',  # Allow user deletion
        }
    }

class PerformanceOptimizations:
    """
    Database performance optimization patterns.
    
    Includes indexing strategies, connection pooling, and query optimization.
    """
    
    # Standard indexes for all entities
    STANDARD_INDEXES = [
        # Primary operations
        {'columns': ['id'], 'unique': True},
        {'columns': ['created_at'], 'unique': False},
        {'columns': ['updated_at'], 'unique': False},
        {'columns': ['branch_id'], 'unique': False},
        
        # Soft delete queries
        {'columns': ['is_deleted'], 'unique': False},
        {'columns': ['is_deleted', 'branch_id'], 'unique': False},
        
        # Audit trail queries
        {'columns': ['created_by_user_id'], 'unique': False},
        {'columns': ['updated_by_user_id'], 'unique': False},
    ]
    
    # Module-specific indexes
    MODULE_INDEXES = {
        'purchases': [
            {'columns': ['supplier_id'], 'unique': False},
            {'columns': ['purchase_date'], 'unique': False},
            {'columns': ['status'], 'unique': False},
            {'columns': ['branch_id', 'purchase_date'], 'unique': False},
            {'columns': ['supplier_id', 'purchase_date'], 'unique': False},
        ],
        'inventory': [
            {'columns': ['product_id'], 'unique': False},
            {'columns': ['movement_type'], 'unique': False},
            {'columns': ['transaction_date'], 'unique': False},
            {'columns': ['product_id', 'branch_id'], 'unique': False},
        ],
        'accounting': [
            {'columns': ['account_id'], 'unique': False},
            {'columns': ['entry_date'], 'unique': False},
            {'columns': ['entry_type'], 'unique': False},
            {'columns': ['account_id', 'entry_date'], 'unique': False},
        ]
    }
    
    # Connection pool settings
    CONNECTION_POOL_CONFIG = {
        'pool_size': 20,           # Base number of connections
        'max_overflow': 30,        # Additional connections during peak
        'pool_timeout': 30,        # Seconds to wait for connection
        'pool_recycle': 3600,      # Recycle connections every hour
        'pool_pre_ping': True,     # Validate connections before use
    }

class DataValidationStandards:
    """
    Standardized data validation patterns across all modules.
    
    Ensures data quality and consistency.
    """
    
    # Standard validation patterns
    VALIDATION_PATTERNS = {
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'phone': r'^\+?[\d\s\-\(\)]{7,15}$',
        'currency': r'^\d+(\.\d{1,2})?$',
        'percentage': r'^(100(\.0{1,2})?|[0-9]?[0-9](\.[0-9]{1,2})?)$',
        'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    }
    
    # Business validation rules
    BUSINESS_RULES = {
        'amounts': {
            'min_value': 0,
            'max_value': 999999999.99,
            'decimal_places': 2,
        },
        'dates': {
            'min_date': '2020-01-01',  # System start date
            'max_future_years': 10,    # Maximum future date
        },
        'text_fields': {
            'max_length': {
                'short': 255,
                'medium': 1000,
                'long': 5000,
            }
        }
    }

# Example implementation of standardized model
class StandardizedPurchaseModel(CNPERPBaseModel, AuditTrailMixin):
    """
    Example of a fully standardized model following CNPERP patterns.
    """
    __tablename__ = 'purchases_purchase_orders'
    
    # Business fields following naming conventions
    purchase_number = Column(String(50), nullable=False, unique=True, index=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('suppliers.id', **ForeignKeyStandards.FK_PATTERNS['restrict']), nullable=False, index=True)
    purchase_date = Column(DateTime, nullable=False, index=True)
    due_date = Column(DateTime, nullable=True, index=True)
    
    # Amounts following currency patterns
    subtotal_amount = Column(String, nullable=False, default='0.00')  # Store as string for precision
    tax_amount = Column(String, nullable=False, default='0.00')
    total_amount = Column(String, nullable=False, default='0.00')
    
    # Status following enum patterns
    purchase_status = Column(String(20), nullable=False, default='draft', index=True)
    
    # Optional fields
    reference_number = Column(String(100), nullable=True)
    notes = Column(String(5000), nullable=True)
    
    # Relationships following standards
    supplier = relationship("Supplier", lazy='select')
    items = relationship("PurchaseItem", back_populates="purchase", cascade="all, delete-orphan")
    
    # Custom indexes for this model
    __table_args__ = (
        Index('idx_purchases_supplier_date', 'supplier_id', 'purchase_date'),
        Index('idx_purchases_status_branch', 'purchase_status', 'branch_id'),
        Index('idx_purchases_date_range', 'purchase_date', 'branch_id'),
    )
    
    @validates('purchase_status')
    def validate_status(self, key, value):
        """Validate purchase status values."""
        valid_statuses = ['draft', 'pending', 'approved', 'received', 'cancelled']
        if value not in valid_statuses:
            raise ValueError(f"Invalid purchase status: {value}")
        return value
    
    @validates('total_amount', 'subtotal_amount', 'tax_amount')
    def validate_amounts(self, key, value):
        """Validate monetary amounts."""
        try:
            amount = float(value)
            if amount < 0:
                raise ValueError(f"{key} cannot be negative")
            if amount > 999999999.99:
                raise ValueError(f"{key} exceeds maximum allowed value")
            return f"{amount:.2f}"
        except (ValueError, TypeError):
            raise ValueError(f"Invalid amount format for {key}: {value}")

# Database schema migration helper
class SchemaMigrationHelper:
    """
    Helper for applying standardization patterns to existing schemas.
    """
    
    @staticmethod
    def generate_standardization_migration(table_name: str, module: str):
        """Generate SQL migration script for standardizing a table."""
        return f"""
-- Standardization migration for {table_name}
-- Module: {module}
-- Generated: {datetime.utcnow().isoformat()}

-- Add standard audit fields if missing
ALTER TABLE {table_name} 
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS created_by_user_id UUID REFERENCES users(id),
ADD COLUMN IF NOT EXISTS updated_by_user_id UUID REFERENCES users(id),
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS deleted_by_user_id UUID REFERENCES users(id),
ADD COLUMN IF NOT EXISTS version VARCHAR(20) DEFAULT '1.0.0';

-- Add standard indexes
CREATE INDEX IF NOT EXISTS idx_{table_name}_created_at ON {table_name}(created_at);
CREATE INDEX IF NOT EXISTS idx_{table_name}_updated_at ON {table_name}(updated_at);
CREATE INDEX IF NOT EXISTS idx_{table_name}_branch_id ON {table_name}(branch_id);
CREATE INDEX IF NOT EXISTS idx_{table_name}_is_deleted ON {table_name}(is_deleted);

-- Add update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_{table_name}_updated_at 
    BEFORE UPDATE ON {table_name} 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Add module-specific indexes
{SchemaMigrationHelper._generate_module_indexes(table_name, module)}
"""
    
    @staticmethod
    def _generate_module_indexes(table_name: str, module: str) -> str:
        """Generate module-specific indexes."""
        indexes = PerformanceOptimizations.MODULE_INDEXES.get(module, [])
        sql_parts = []
        
        for idx in indexes:
            columns = '_'.join(idx['columns'])
            unique = 'UNIQUE ' if idx['unique'] else ''
            sql_parts.append(f"CREATE {unique}INDEX IF NOT EXISTS idx_{table_name}_{columns} ON {table_name}({', '.join(idx['columns'])});")
        
        return '\n'.join(sql_parts)