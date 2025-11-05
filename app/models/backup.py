from sqlalchemy import Column, String, DateTime, Boolean, Integer, Text, JSON
from sqlalchemy.sql import func
from app.core.database import Base
import uuid

class Backup(Base):
    __tablename__ = "backups"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    backup_type = Column(String, nullable=False)  # absolute, incremental, restore
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="in_progress")  # in_progress, completed, failed, cancelled
    file_path = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    file_hash = Column(String, nullable=True)
    backup_metadata = Column('metadata', JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

class BackupSchedule(Base):
    __tablename__ = "backup_schedules"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    backup_type = Column(String, nullable=False)
    frequency = Column(String, nullable=False)  # daily, weekly, monthly
    time = Column(String, nullable=False)  # HH:MM format
    include_files = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    last_run = Column(DateTime(timezone=True), nullable=True)
    next_run = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String, nullable=False)
