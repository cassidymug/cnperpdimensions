from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ExcelTemplateMetadata(BaseModel):
    """Metadata derived from an uploaded Excel workbook."""

    sheet_names: List[str] = Field(default_factory=list, description="Ordered list of sheet names in the workbook")
    named_ranges: List[str] = Field(default_factory=list, description="Defined names/named ranges in the workbook")
    sample_headers: Dict[str, List[Optional[str]]] = Field(
        default_factory=dict,
        description="First-row values for each sheet to assist with field mapping",
    )
    document_properties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Subset of workbook properties (title, author, created, etc.)",
    )


class ExcelTemplateUploader(BaseModel):
    id: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    branch_id: Optional[str] = None
    branch_name: Optional[str] = None
    branch_code: Optional[str] = None
    display_name: Optional[str] = None
    initials: Optional[str] = None
    avatar_url: Optional[str] = None
    avatar_background: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ExcelTemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    original_filename: str
    stored_filename: str
    public_url: str
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    version: Optional[str] = None
    workbook_metadata: Optional[ExcelTemplateMetadata] = None
    download_url: Optional[str] = None
    uploaded_by: Optional[str] = None
    uploaded_by_user: Optional[ExcelTemplateUploader] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExcelTemplateListResponse(BaseModel):
    templates: List[ExcelTemplateResponse]
    total: int


class ExcelTemplateDeleteResponse(BaseModel):
    success: bool = True
    message: str = "Template removed"
