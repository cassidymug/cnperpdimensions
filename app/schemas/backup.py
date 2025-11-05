from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class BackupType(str, Enum):
    ABSOLUTE = "absolute"
    INCREMENTAL = "incremental"
    RESTORE = "restore"
    FULL_SYSTEM = "full_system"  # Complete application backup including code, database, and settings

class BackupStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class BackupCreate(BaseModel):
    backup_type: BackupType = Field(..., description="Type of backup to create")
    description: Optional[str] = Field(None, description="Description of the backup")
    include_files: bool = Field(True, description="Include application files in backup")
    tables: Optional[List[str]] = Field(None, description="Specific tables to backup (optional)")
    backup_location: Optional[str] = Field(None, description="Custom backup location path (optional, uses default if not specified)")

class BackupResponse(BaseModel):
    id: str
    backup_type: BackupType
    description: Optional[str]
    status: BackupStatus
    created_at: datetime
    created_by: str
    file_size: Optional[int] = None
    file_hash: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class BackupRestore(BaseModel):
    restore_database: bool = Field(True, description="Restore database from backup")
    restore_files: bool = Field(False, description="Restore application files from backup")
    confirm_restore: bool = Field(..., description="Confirm that you want to restore (this will overwrite current data)")

class BackupSchedule(BaseModel):
    backup_type: BackupType = Field(..., description="Type of backup to schedule")
    frequency: str = Field(..., description="Frequency of backup (daily, weekly, monthly)")
    time: str = Field(..., description="Time to run backup (HH:MM format)")
    include_files: bool = Field(True, description="Include application files in backup")
    description: Optional[str] = Field(None, description="Description of the scheduled backup")

class BackupSummary(BaseModel):
    total_backups: int
    completed_backups: int
    failed_backups: int
    latest_backup: Optional[datetime]
    total_size_bytes: int
    total_size_mb: float

class BackupFilter(BaseModel):
    backup_type: Optional[BackupType] = None
    status: Optional[BackupStatus] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    created_by: Optional[str] = None

class BackupScheduleResponse(BaseModel):
    id: str
    backup_type: BackupType
    frequency: str
    time: str
    include_files: bool
    description: Optional[str]
    created_at: datetime
    created_by: str
    is_active: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
