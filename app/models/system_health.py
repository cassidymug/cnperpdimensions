"""
Database models for System Health & Error Management
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class SystemError(BaseModel):
    """Tracks system errors and exceptions"""
    __tablename__ = "system_errors"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    error_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)  # critical, error, warning, info
    message = Column(Text, nullable=False)
    stack_trace = Column(Text)
    module = Column(String(100), index=True)  # inventory, sales, accounting, etc.
    user_id = Column(String, ForeignKey("users.id"))
    status = Column(String(20), default="new", index=True)  # new, investigating, resolved
    resolved = Column(Boolean, default=False, index=True)
    resolution = Column(Text)
    error_metadata = Column(JSON, default=dict)  # Additional context
    
    resolved_at = Column(DateTime)
    resolved_by_id = Column(String, ForeignKey("users.id"))
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], lazy="joined")
    resolved_by = relationship("User", foreign_keys=[resolved_by_id], lazy="joined")


class SystemHealthCheck(BaseModel):
    """Records system health check results"""
    __tablename__ = "system_health_checks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    check_type = Column(String(50), nullable=False)  # full, database, data_integrity, performance
    status = Column(String(20), nullable=False)  # healthy, warning, error
    results = Column(JSON, default=dict)  # Detailed results
    duration_ms = Column(Integer)  # How long the check took
    
    performed_by_id = Column(String, ForeignKey("users.id"))
    performed_by = relationship("User", lazy="joined")


class SystemFix(BaseModel):
    """Tracks automated fixes applied to the system"""
    __tablename__ = "system_fixes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    fix_type = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)  # running, completed, failed
    dry_run = Column(Boolean, default=True)
    parameters = Column(JSON, default=dict)
    result = Column(JSON, default=dict)
    error_message = Column(Text)
    
    completed_at = Column(DateTime)
    applied_by_id = Column(String, ForeignKey("users.id"))
    applied_by = relationship("User", lazy="joined")


class DataIntegrityIssue(BaseModel):
    """Tracks data integrity issues found during checks"""
    __tablename__ = "data_integrity_issues"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    issue_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False)  # critical, high, medium, low
    description = Column(Text, nullable=False)
    affected_table = Column(String(100))
    affected_records = Column(JSON, default=list)  # List of IDs
    resolution_status = Column(String(20), default="open")  # open, in_progress, resolved
    resolution_notes = Column(Text)
    
    resolved_at = Column(DateTime)
    resolved_by_id = Column(String, ForeignKey("users.id"))
    resolved_by = relationship("User", lazy="joined")


class PerformanceMetric(BaseModel):
    """Stores performance metrics over time"""
    __tablename__ = "performance_metrics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Integer, nullable=False)  # milliseconds, count, etc.
    metric_type = Column(String(50), nullable=False)  # query_time, cpu_usage, memory_usage
    context = Column(JSON, default=dict)  # Additional context
