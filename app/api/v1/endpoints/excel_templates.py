from __future__ import annotations

from hashlib import md5
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.excel_template import (
    ExcelTemplateDeleteResponse,
    ExcelTemplateListResponse,
    ExcelTemplateResponse,
    ExcelTemplateUploader,
)
from app.services.excel_template_service import ExcelTemplateService
from app.core.security import get_current_user
from app.models.user import User
from app.services.branch_cache import branch_cache

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()


def _extract_url(value) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, dict):
        for key in ("url", "href", "image", "avatar"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate
    if hasattr(value, "url"):
        candidate = getattr(value, "url")
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    if hasattr(value, "get") and callable(getattr(value, "get")):
        candidate = value.get("url")
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None


def _resolve_avatar_url(user: User) -> Optional[str]:
    for attr in (
        "avatar_url",
        "profile_image_url",
        "image_url",
        "photo_url",
        "profile_photo_url",
        "avatar",
        "media",
        "profile",
    ):
        if not hasattr(user, attr):
            continue
        url = _extract_url(getattr(user, attr))
        if url:
            return url

    getter = getattr(user, "get_avatar_url", None)
    if callable(getter):
        url = _extract_url(getter())
        if url:
            return url

    storage = getattr(user, "media_assets", None)
    url = _extract_url(storage)
    if url:
        return url

    return None


def _derive_display_name(user: User) -> Optional[str]:
    names = [getattr(user, "first_name", None), getattr(user, "last_name", None)]
    names = [name.strip() for name in names if isinstance(name, str) and name.strip()]
    if names:
        return " ".join(names)
    username = getattr(user, "username", None)
    if isinstance(username, str) and username.strip():
        return username
    email = getattr(user, "email", None)
    if isinstance(email, str) and email.strip():
        return email
    return None


def _derive_initials(user: User, display_name: Optional[str]) -> Optional[str]:
    source = display_name or getattr(user, "username", "") or getattr(user, "email", "")
    if not isinstance(source, str) or not source.strip():
        return None
    segments = [segment for segment in source.replace("_", " ").split() if segment]
    chars = [segment[0] for segment in segments if segment]
    if not chars and source.strip():
        chars = [source.strip()[0]]
    if not chars:
        return None
    first = chars[0]
    second = chars[1] if len(chars) > 1 else ""
    return (first + second).upper()


def _derive_avatar_bg(user: User) -> str:
    seed_source = getattr(user, "id", None) or getattr(user, "username", "") or "default"
    digest = md5(str(seed_source).encode("utf-8")).hexdigest()
    hue = int(digest[:2], 16) % 360
    saturation = 65
    lightness = 55
    return f"hsl({hue} {saturation}% {lightness}%)"


def _build_uploader_payload(user: Optional[User]) -> Optional[ExcelTemplateUploader]:
    if user is None:
        return None

    base = ExcelTemplateUploader.model_validate(user, from_attributes=True)
    display_name = _derive_display_name(user)
    initials = _derive_initials(user, display_name)
    avatar_url = _resolve_avatar_url(user)
    avatar_background = _derive_avatar_bg(user)
    branch = getattr(user, "branch", None)
    branch_name = getattr(branch, "name", None) if branch else None
    branch_code = getattr(branch, "code", None) if branch else None

    if (branch_name is None or branch_code is None) and getattr(user, "branch_id", None):
        cached = branch_cache.get_branch(user.branch_id)
        if cached:
            branch_name = branch_name or cached.get("name")
            branch_code = branch_code or cached.get("code")

    return base.model_copy(
        update={
            "display_name": display_name,
            "initials": initials,
            "avatar_url": avatar_url or None,
            "avatar_background": avatar_background,
            "branch_name": branch_name,
            "branch_code": branch_code,
        }
    )


def _to_response(template, service: ExcelTemplateService) -> ExcelTemplateResponse:
    response = ExcelTemplateResponse.model_validate(template, from_attributes=True)
    response.download_url = service.build_download_url(template.id)
    if getattr(template, "uploaded_by_user", None):
        response.uploaded_by_user = _build_uploader_payload(template.uploaded_by_user)
        if response.uploaded_by_user and not response.uploaded_by:
            response.uploaded_by = response.uploaded_by_user.id
    return response


@router.post("/upload", response_model=ExcelTemplateResponse, status_code=201)
async def upload_excel_template(
    file: UploadFile = File(..., description="Excel template file (.xlsx or .xlsm)"),
    name: Optional[str] = Form(None, description="Friendly template name to display"),
    description: Optional[str] = Form(None, description="Optional description or usage notes"),
    category: Optional[str] = Form(None, description="Template category (e.g. invoices, reports)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        logger.info(f"Uploading Excel template: {file.filename}")
        service = ExcelTemplateService(db)
        template = await service.upload_template(
            file=file,
            name=name,
            description=description,
            category=category,
            uploaded_by=current_user.id if current_user else None,
        )
        logger.info(f"Successfully uploaded template: {template.id} - {template.name}")
        return _to_response(template, service)
    except ValueError as e:
        log_error_with_context(logger, "Validation error uploading template",
                              filename=file.filename, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_exception(logger, e, context=f"Error uploading template: {file.filename}")
        raise HTTPException(status_code=500, detail="Internal server error uploading template")


@router.get("/", response_model=ExcelTemplateListResponse)
def list_excel_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        logger.debug("Fetching Excel templates list")
        service = ExcelTemplateService(db)
        templates = service.list_templates()
        logger.info(f"Retrieved {len(templates)} Excel templates")
        return ExcelTemplateListResponse(
            templates=[_to_response(template, service) for template in templates],
            total=len(templates),
        )
    except Exception as e:
        log_exception(logger, e, context="Error fetching Excel templates")
        raise HTTPException(status_code=500, detail="Internal server error fetching templates")


@router.get("/{template_id}", response_model=ExcelTemplateResponse)
def get_excel_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ExcelTemplateService(db)
    template = service.get_template(template_id)
    return _to_response(template, service)


@router.get("/{template_id}/download")
def download_excel_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ExcelTemplateService(db)
    template = service.get_template(template_id)
    file_path = Path(template.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Stored template file is missing")

    return FileResponse(
        path=file_path,
        media_type=template.content_type or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=template.original_filename,
    )


@router.delete("/{template_id}", response_model=ExcelTemplateDeleteResponse)
def delete_excel_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ExcelTemplateService(db)
    service.delete_template(template_id)
    return ExcelTemplateDeleteResponse()
