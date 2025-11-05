from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from datetime import date

from app.core.database import get_db
# from app.core.security import get_current_user  # Removed for development
from app.models.user import User
from app.models.budgeting import (
    Budget, BudgetAllocation, BudgetTransaction, BudgetUserAccess, BudgetRequest
)
from app.schemas.budgeting import (
    BudgetCreate, BudgetUpdate, BudgetResponse,
    BudgetAllocationCreate, BudgetAllocationUpdate, BudgetAllocationResponse,
    BudgetTransactionCreate, BudgetTransactionUpdate, BudgetTransactionResponse,
    BudgetUserAccessCreate, BudgetUserAccessUpdate, BudgetUserAccessResponse,
    BudgetRequestCreate, BudgetRequestUpdate, BudgetRequestResponse,
    BudgetAnalytics, BudgetApprovalRequest, BudgetApprovalResponse
)
from app.services.budgeting_service import BudgetingService

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()  # Dependencies removed for development


# Budget Management Endpoints
@router.post("/budgets", response_model=BudgetResponse)
async def create_budget(
    budget: BudgetCreate,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Create a new budget"""
    try:
        service = BudgetingService(db)
        budget_data = budget.dict()
        budget_data['branch_id'] = budget_data.get('branch_id') or 'default-branch'
        return service.create_budget(budget_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/budgets", response_model=List[BudgetResponse])
async def list_budgets(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = Query(None),
    budget_type: Optional[str] = Query(None),
    branch_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """List budgets with optional filtering"""
    try:
        query = db.query(Budget)
        
        if status:
            query = query.filter(Budget.status == status)
        if budget_type:
            query = query.filter(Budget.budget_type == budget_type)
        if branch_id:
            query = query.filter(Budget.branch_id == branch_id)
        elif 'default-branch':
            query = query.filter(Budget.branch_id == 'default-branch')
        
        return query.offset(skip).limit(limit).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing budgets: {str(e)}")


@router.get("/budgets/{budget_id}", response_model=BudgetResponse)
async def get_budget(
    budget_id: str,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Get budget by ID"""
    try:
        budget = db.query(Budget).filter(Budget.id == budget_id).first()
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        return budget
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting budget: {str(e)}")


@router.put("/budgets/{budget_id}", response_model=BudgetResponse)
async def update_budget(
    budget_id: str,
    budget_update: BudgetUpdate,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Update a budget"""
    try:
        budget = db.query(Budget).filter(Budget.id == budget_id).first()
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        update_data = budget_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(budget, field, value)
        
        db.commit()
        db.refresh(budget)
        return budget
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating budget: {str(e)}")


@router.post("/budgets/{budget_id}/approve", response_model=BudgetResponse)
async def approve_budget(
    budget_id: str,
    approval: BudgetApprovalRequest,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Approve a budget"""
    try:
        service = BudgetingService(db)
        return service.approve_budget(budget_id, 'default-user-id', approval.approved_amount)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Budget Allocation Endpoints
@router.post("/allocations", response_model=BudgetAllocationResponse)
async def create_allocation(
    allocation: BudgetAllocationCreate,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Create a budget allocation"""
    try:
        service = BudgetingService(db)
        return service.create_allocation(allocation.dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/allocations", response_model=List[BudgetAllocationResponse])
async def list_allocations(
    budget_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """List budget allocations"""
    try:
        query = db.query(BudgetAllocation)
        
        if budget_id:
            query = query.filter(BudgetAllocation.budget_id == budget_id)
        if category:
            query = query.filter(BudgetAllocation.category == category)
        if status:
            query = query.filter(BudgetAllocation.status == status)
        
        return query.all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing allocations: {str(e)}")


@router.put("/allocations/{allocation_id}", response_model=BudgetAllocationResponse)
async def update_allocation(
    allocation_id: str,
    allocation_update: BudgetAllocationUpdate,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Update a budget allocation"""
    try:
        allocation = db.query(BudgetAllocation).filter(BudgetAllocation.id == allocation_id).first()
        if not allocation:
            raise HTTPException(status_code=404, detail="Allocation not found")
        
        update_data = allocation_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(allocation, field, value)
        
        db.commit()
        db.refresh(allocation)
        return allocation
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating allocation: {str(e)}")


# Budget Transaction Endpoints
@router.post("/transactions", response_model=BudgetTransactionResponse)
async def create_transaction(
    transaction: BudgetTransactionCreate,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Create a budget transaction"""
    try:
        service = BudgetingService(db)
        return service.record_transaction(transaction.dict(), 'default-user-id')
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transactions", response_model=List[BudgetTransactionResponse])
async def list_transactions(
    budget_id: Optional[str] = Query(None),
    allocation_id: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """List budget transactions"""
    try:
        query = db.query(BudgetTransaction)
        
        if budget_id:
            query = query.filter(BudgetTransaction.budget_id == budget_id)
        if allocation_id:
            query = query.filter(BudgetTransaction.allocation_id == allocation_id)
        if transaction_type:
            query = query.filter(BudgetTransaction.transaction_type == transaction_type)
        if status:
            query = query.filter(BudgetTransaction.status == status)
        
        return query.order_by(BudgetTransaction.created_at.desc()).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing transactions: {str(e)}")


# Procurement Integration Endpoints
@router.post("/link-purchase/{purchase_id}")
async def link_purchase_to_budget(
    purchase_id: str,
    budget_id: str,
    allocation_id: Optional[str] = None,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Link a purchase to a budget"""
    try:
        service = BudgetingService(db)
        transaction = service.link_purchase_to_budget(purchase_id, budget_id, 'default-user-id', allocation_id)
        return {"success": True, "transaction_id": transaction.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/link-purchase-order/{po_id}")
async def link_purchase_order_to_budget(
    po_id: str,
    budget_id: str,
    allocation_id: Optional[str] = None,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Link a purchase order to a budget"""
    try:
        service = BudgetingService(db)
        transaction = service.link_purchase_order_to_budget(po_id, budget_id, 'default-user-id', allocation_id)
        return {"success": True, "transaction_id": transaction.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# User Access Control Endpoints
@router.post("/user-access", response_model=BudgetUserAccessResponse)
async def grant_user_access(
    access: BudgetUserAccessCreate,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Grant user access to a budget"""
    try:
        service = BudgetingService(db)
        return service.grant_user_access(access.dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user-access", response_model=List[BudgetUserAccessResponse])
async def list_user_access(
    budget_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """List user access permissions"""
    try:
        query = db.query(BudgetUserAccess)
        
        if budget_id:
            query = query.filter(BudgetUserAccess.budget_id == budget_id)
        if user_id:
            query = query.filter(BudgetUserAccess.user_id == user_id)
        
        return query.all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing user access: {str(e)}")


@router.put("/user-access/{access_id}", response_model=BudgetUserAccessResponse)
async def update_user_access(
    access_id: str,
    access_update: BudgetUserAccessUpdate,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Update user access permissions"""
    try:
        access = db.query(BudgetUserAccess).filter(BudgetUserAccess.id == access_id).first()
        if not access:
            raise HTTPException(status_code=404, detail="User access not found")
        
        update_data = access_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(access, field, value)
        
        db.commit()
        db.refresh(access)
        return access
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating user access: {str(e)}")


# Budget Request Endpoints
@router.post("/requests", response_model=BudgetRequestResponse)
async def create_budget_request(
    request: BudgetRequestCreate,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Create a budget request"""
    try:
        service = BudgetingService(db)
        return service.create_budget_request(request.dict(), 'default-user-id')
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/requests", response_model=List[BudgetRequestResponse])
async def list_budget_requests(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    requested_by: Optional[str] = Query(None),
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """List budget requests"""
    try:
        query = db.query(BudgetRequest)
        
        if status:
            query = query.filter(BudgetRequest.status == status)
        if priority:
            query = query.filter(BudgetRequest.priority == priority)
        if requested_by:
            query = query.filter(BudgetRequest.requested_by == requested_by)
        
        return query.order_by(BudgetRequest.requested_at.desc()).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing budget requests: {str(e)}")


@router.post("/requests/{request_id}/approve")
async def approve_budget_request(
    request_id: str,
    approved_amount: Optional[Decimal] = None,
    rejection_reason: Optional[str] = None,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Approve or reject a budget request"""
    try:
        service = BudgetingService(db)
        request = service.approve_budget_request(request_id, 'default-user-id', approved_amount, rejection_reason)
        return {"success": True, "request_id": request.id, "status": request.status}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Analytics Endpoints
@router.get("/analytics", response_model=BudgetAnalytics)
async def get_budget_analytics(
    branch_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Get budget analytics"""
    try:
        service = BudgetingService(db)
        return service.get_budget_analytics(branch_id or 'default-branch')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting analytics: {str(e)}")


# Dashboard Endpoints
@router.get("/dashboard")
async def get_budget_dashboard(
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Get budget dashboard data"""
    try:
        service = BudgetingService(db)
        analytics = service.get_budget_analytics('default-branch')
        
        # Get recent transactions
        recent_transactions = db.query(BudgetTransaction).filter(
            BudgetTransaction.created_at >= date.today()
        ).order_by(BudgetTransaction.created_at.desc()).limit(10).all()
        
        # Get pending requests
        pending_requests = db.query(BudgetRequest).filter(
            BudgetRequest.status == "pending"
        ).order_by(BudgetRequest.requested_at.desc()).limit(5).all()
        
        return {
            "analytics": analytics,
            "recent_transactions": recent_transactions,
            "pending_requests": pending_requests
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting dashboard: {str(e)}")
