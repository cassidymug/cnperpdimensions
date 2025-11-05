import uuid
from sqlalchemy import Column, String, Boolean, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ImportJob(BaseModel):
    """Import job model for background import operations"""
    __tablename__ = "import_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    user_id = Column(ForeignKey("users.id"), nullable=False)
    file_name = Column(String)
    status = Column(Integer, default=0)
    result = Column(Text)
    # Additional fields for better import job tracking
    job_type = Column(String)  # products, customers, suppliers, sales, etc.
    file_size = Column(Integer)
    total_records = Column(Integer, default=0)
    processed_records = Column(Integer, default=0)
    successful_records = Column(Integer, default=0)
    failed_records = Column(Integer, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    progress_percentage = Column(Integer, default=0)
    branch_id = Column(ForeignKey("branches.id"))
    import_config = Column(Text)  # JSON configuration for the import
    validation_errors = Column(Text)  # JSON array of validation errors

    # Relationships
    user = relationship("User", back_populates="import_jobs")
    branch = relationship("Branch") 