from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.services.procurement_service import ProcurementService
from app.schemas.procurement import (
    RequisitionCreate, RequisitionResponse,
    RFQCreate, RFQResponse,
    SupplierQuoteCreate, SupplierQuoteResponse,
    ProcurementAwardCreate, ProcurementAwardResponse,
    SupplierPerformanceCreate, SupplierPerformanceResponse,
    SupplierPerformanceEvaluateRequest, SupplierPerformanceEvaluateResult,
    SupplierEvaluationTicketCreate, SupplierEvaluationTicketResponse,
    SupplierEvaluationMilestoneCreate, SupplierEvaluationMilestoneResponse
)
from app.models.procurement import (
    ProcurementRequisition, RFQ, SupplierQuote, ProcurementAward, SupplierPerformance,
    SupplierEvaluationTicket, SupplierEvaluationMilestone
)
from app.models.purchases import Supplier

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()  # Dependencies removed for development


@router.post("/requisitions", response_model=RequisitionResponse)
async def create_requisition(req: RequisitionCreate, db: Session = Depends(get_db)):
    try:
        service = ProcurementService(db)
        data = req.dict()
        items = data.pop('items', [])
        requisition = service.create_requisition(data, items)
        return requisition
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating requisition: {str(e)}")


@router.get("/requisitions", response_model=List[RequisitionResponse])
async def list_requisitions(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(ProcurementRequisition)
        if status:
            query = query.filter(ProcurementRequisition.status == status)
        return query.order_by(ProcurementRequisition.created_at.desc()).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing requisitions: {str(e)}")


@router.post("/rfqs", response_model=RFQResponse)
async def create_rfq(rfq: RFQCreate, db: Session = Depends(get_db)):
    try:
        service = ProcurementService(db)
        data = rfq.dict()
        invites = data.pop('invites', [])
        rfq_obj = service.create_rfq(data, invites)
        return rfq_obj
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating RFQ: {str(e)}")


@router.get("/rfqs", response_model=List[RFQResponse])
async def list_rfqs(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(RFQ)
        if status:
            query = query.filter(RFQ.status == status)
        return query.order_by(RFQ.issue_date.desc()).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing RFQs: {str(e)}")


@router.post("/quotes", response_model=SupplierQuoteResponse)
async def submit_quote(quote: SupplierQuoteCreate, db: Session = Depends(get_db)):
    try:
        service = ProcurementService(db)
        data = quote.dict()
        items = data.pop('items', [])
        quote_obj = service.submit_supplier_quote(data, items)
        return quote_obj
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting quote: {str(e)}")


@router.get("/quotes", response_model=List[SupplierQuoteResponse])
async def list_quotes(
    rfq_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    try:
        query = db.query(SupplierQuote)
        if rfq_id:
            query = query.filter(SupplierQuote.rfq_id == rfq_id)
        if status:
            query = query.filter(SupplierQuote.status == status)
        return query.order_by(SupplierQuote.quote_date.desc()).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing quotes: {str(e)}")


@router.post("/awards", response_model=ProcurementAwardResponse)
async def award_quote(award: ProcurementAwardCreate, db: Session = Depends(get_db)):
    try:
        service = ProcurementService(db)
        award_obj, _po = service.award_quote(award.dict())
        return award_obj
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error awarding quote: {str(e)}")


@router.get("/awards", response_model=List[ProcurementAwardResponse])
async def list_awards(db: Session = Depends(get_db)):
    try:
        awards = db.query(ProcurementAward).order_by(ProcurementAward.award_date.desc()).all()
        # Enrich with po_number if PO is linked
        for a in awards:
            try:
                if getattr(a, 'purchase_order', None):
                    # Attach transient attribute for schema "po_number"
                    setattr(a, 'po_number', getattr(a.purchase_order, 'po_number', None))
            except Exception:
                pass
        return awards
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing awards: {str(e)}")


@router.post("/performance", response_model=SupplierPerformanceResponse)
async def create_performance(item: SupplierPerformanceCreate, db: Session = Depends(get_db)):
    try:
        perf = SupplierPerformance(**item.dict())
        db.add(perf)
        db.commit()
        db.refresh(perf)
        return perf
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating supplier performance: {str(e)}")


@router.get("/performance", response_model=List[SupplierPerformanceResponse])
async def list_performance(supplier_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    try:
        query = db.query(SupplierPerformance)
        if supplier_id:
            query = query.filter(SupplierPerformance.supplier_id == supplier_id)
        return query.order_by(SupplierPerformance.created_at.desc()).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing supplier performance: {str(e)}")


@router.post("/evaluation-tickets", response_model=SupplierEvaluationTicketResponse)
async def create_evaluation_ticket(payload: SupplierEvaluationTicketCreate, db: Session = Depends(get_db)):
    try:
        ticket = SupplierEvaluationTicket(
            supplier_id=payload.supplier_id,
            purchase_order_id=payload.purchase_order_id,
            status=payload.status,
            opened_at=payload.opened_at,
            closed_at=payload.closed_at,
            branch_id=payload.branch_id,
            notes=payload.notes
        )
        db.add(ticket)
        db.flush()

        for idx, ms in enumerate(payload.milestones or []):
            db.add(SupplierEvaluationMilestone(
                ticket_id=ticket.id,
                name=ms.name,
                description=ms.description,
                sequence=ms.sequence or (idx + 1),
                status=ms.status or 'pending',
                due_date=ms.due_date,
                completed_at=ms.completed_at,
                notes=ms.notes
            ))

        db.commit()
        db.refresh(ticket)
        return ticket
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating evaluation ticket: {str(e)}")


@router.get("/evaluation-tickets", response_model=List[SupplierEvaluationTicketResponse])
async def list_evaluation_tickets(supplier_id: Optional[str] = Query(None), po_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    try:
        query = db.query(SupplierEvaluationTicket)
        if supplier_id:
            query = query.filter(SupplierEvaluationTicket.supplier_id == supplier_id)
        if po_id:
            query = query.filter(SupplierEvaluationTicket.purchase_order_id == po_id)
        return query.order_by(SupplierEvaluationTicket.created_at.desc()).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing evaluation tickets: {str(e)}")


@router.post("/evaluation-tickets/{ticket_id}/milestones", response_model=SupplierEvaluationMilestoneResponse)
async def add_milestone(ticket_id: str, payload: SupplierEvaluationMilestoneCreate, db: Session = Depends(get_db)):
    try:
        ticket = db.query(SupplierEvaluationTicket).filter(SupplierEvaluationTicket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Evaluation ticket not found")
        milestone = SupplierEvaluationMilestone(
            ticket_id=ticket_id,
            name=payload.name,
            description=payload.description,
            sequence=payload.sequence or 0,
            status=payload.status or 'pending',
            due_date=payload.due_date,
            completed_at=payload.completed_at,
            notes=payload.notes
        )
        db.add(milestone)
        db.commit()
        db.refresh(milestone)
        return milestone
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error adding milestone: {str(e)}")


@router.put("/evaluation-tickets/{ticket_id}/milestones/{milestone_id}", response_model=SupplierEvaluationMilestoneResponse)
async def update_milestone(ticket_id: str, milestone_id: str, payload: SupplierEvaluationMilestoneCreate, db: Session = Depends(get_db)):
    try:
        milestone = db.query(SupplierEvaluationMilestone).filter(
            SupplierEvaluationMilestone.id == milestone_id,
            SupplierEvaluationMilestone.ticket_id == ticket_id
        ).first()
        if not milestone:
            raise HTTPException(status_code=404, detail="Milestone not found")
        
        for field, value in payload.dict(exclude_unset=True).items():
            setattr(milestone, field, value)
        
        db.commit()
        db.refresh(milestone)
        return milestone
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating milestone: {str(e)}")


@router.post("/performance/evaluate", response_model=SupplierPerformanceEvaluateResult)
async def evaluate_performance(req: SupplierPerformanceEvaluateRequest, db: Session = Depends(get_db)):
    try:
        service = ProcurementService(db)
        if req.supplier_id:
            return service.evaluate_supplier_performance(req.supplier_id, req.period_start, req.period_end, req.persist)
        # If no supplier_id provided, compute for all active suppliers and return an aggregate (best effort: take average overall)
        suppliers = db.query(Supplier).filter(Supplier.active == True).all()
        if not suppliers:
            raise HTTPException(status_code=404, detail="No active suppliers found")
        results = [service.evaluate_supplier_performance(s.id, req.period_start, req.period_end, req.persist) for s in suppliers]
        # Return a pseudo-result summarizing averages (keeping schema fields)
        def avg(field):
            return int(round(sum(r[field] for r in results) / len(results)))
        return SupplierPerformanceEvaluateResult(
            supplier_id="ALL",
            period_start=req.period_start,
            period_end=req.period_end,
            on_time_delivery_score=avg("on_time_delivery_score"),
            quality_score=avg("quality_score"),
            responsiveness_score=avg("responsiveness_score"),
            compliance_score=avg("compliance_score"),
            overall_score=avg("overall_score"),
            details={}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating supplier performance: {str(e)}")

