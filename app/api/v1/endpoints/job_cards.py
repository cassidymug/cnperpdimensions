from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.job_cards import (
    JobCardCreate,
    JobCardUpdate,
    MaterialsUpdateRequest,
    LaborUpdateRequest,
    JobCardStatusChange,
    JobCardNoteCreate,
    JobCardInvoiceRequest,
)
from app.services.job_card_service import JobCardService
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()


def _service(db: Session) -> JobCardService:
    return JobCardService(db)


@router.get("")
def list_job_cards(
    status: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Search job number or description"),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        data = _service(db).list_job_cards(status, job_type, branch_id, customer_id, search, from_date, to_date)
        return {"success": True, "job_cards": data}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive guard for debugging
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("")
def create_job_card(payload: JobCardCreate, db: Session = Depends(get_db)):
    try:
        data = _service(db).create_job_card(payload.model_dump(), user_id=None)
        return {"success": True, "job_card": data}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/technicians")
def list_job_technicians(
    role: Optional[str] = Query(None, description="Filter technicians by role"),
    branch_id: Optional[str] = Query(None, description="Filter by branch assignment"),
    search: Optional[str] = Query(None, description="Search name, username, or email"),
    db: Session = Depends(get_db),
):
    data = _service(db).list_technicians(role=role, branch_id=branch_id, search=search)
    return {"success": True, "technicians": data}


@router.get("/{job_id}")
def get_job_card(job_id: str, db: Session = Depends(get_db)):
    try:
        data = _service(db).get_job_card(job_id)
        return {"success": True, "job_card": data}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{job_id}")
def update_job_card(job_id: str, payload: JobCardUpdate, db: Session = Depends(get_db)):
    try:
        data = _service(db).update_job_card(job_id, payload.model_dump(exclude_unset=True), user_id=None)
        return {"success": True, "job_card": data}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{job_id}/materials")
def update_job_materials(job_id: str, payload: MaterialsUpdateRequest, db: Session = Depends(get_db)):
    try:
        data = _service(db).update_materials(job_id, [item.model_dump() for item in payload.materials], payload.mode)
        return {"success": True, "job_card": data}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{job_id}/labor")
def update_job_labor(job_id: str, payload: LaborUpdateRequest, db: Session = Depends(get_db)):
    try:
        data = _service(db).update_labor(job_id, [item.model_dump() for item in payload.labor], payload.mode)
        return {"success": True, "job_card": data}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{job_id}/notes")
def add_job_note(job_id: str, payload: JobCardNoteCreate, db: Session = Depends(get_db)):
    if not payload.note.strip():
        raise HTTPException(status_code=400, detail="Note cannot be empty")
    data = _service(db).add_note(job_id, payload.note, author_id=None)
    return {"success": True, "note": data}


@router.post("/{job_id}/status")
def change_job_status(job_id: str, payload: JobCardStatusChange, db: Session = Depends(get_db)):
    try:
        data = _service(db).change_status(job_id, payload.status, user_id=None, auto_invoice=True)
        return {"success": True, "job_card": data}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{job_id}/invoice")
def generate_job_invoice(job_id: str, payload: JobCardInvoiceRequest, db: Session = Depends(get_db)):
    try:
        data = _service(db).generate_invoice(
            job_id,
            user_id=None,
            save_draft=payload.save_draft,
            is_cash_sale=payload.is_cash_sale,
        )
        return {"success": True, "invoice": data}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{job_id}")
def delete_job_card(
    job_id: str,
    force: bool = Query(False, description="Force delete even if invoiced"),
    db: Session = Depends(get_db)
):
    """
    Delete a job card and all related materials, labor, and notes.
    
    - **job_id**: The ID of the job card to delete
    - **force**: If true, delete even if job has been invoiced (default: false)
    """
    try:
        success = _service(db).delete_job_card(job_id, force=force)
        return {"success": success, "message": "Job card deleted successfully"}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        # Log the full error for debugging
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete job card: {str(exc)}"
        ) from exc
