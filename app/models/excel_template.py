from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import Column, String, Text, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class ExcelTemplate(BaseModel):
    """Metadata for uploaded Excel templates."""

    __tablename__ = "excel_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))

    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    public_url = Column(String(500), nullable=False)
    file_size = Column(Integer)
    content_type = Column(String(120), default="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    version = Column(String(20), default="1.0")

    workbook_metadata = Column(JSON)
    tags = Column(JSON)

    uploaded_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    uploaded_by_user = relationship("User")

    def absolute_path(self) -> Path:
        """Return the absolute path to the stored template file."""
        return Path(self.file_path).resolve()

    @property
    def filename(self) -> str:
        """Return the stored filename."""
        return self.stored_filename

    @property
    def extension(self) -> Optional[str]:
        """Return the file extension for the template."""
        if self.stored_filename:
            return Path(self.stored_filename).suffix
        return None
