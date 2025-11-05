"""
Workflow API Endpoints - Role-based workflow management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.services.workflow_service import WorkflowService
from app.utils.logger import get_logger, log_exception, log_error_with_context
from app.schemas.workflow import (
    WorkflowDefinitionCreate, WorkflowDefinitionUpdate, WorkflowDefinitionResponse,
    WorkflowStateCreate, WorkflowStateUpdate, WorkflowStateResponse,
    WorkflowTransitionCreate, WorkflowTransitionUpdate, WorkflowTransitionResponse,
    WorkflowInstanceCreate, WorkflowInstanceResponse, WorkflowInstanceDetailResponse,
    WorkflowActionResponse, WorkflowSubmitRequest, WorkflowApproveRequest,
    WorkflowRejectRequest, WorkflowReassignRequest, WorkflowTransitionRequest,
    WorkflowDashboardResponse, WorkflowAvailableAction, WorkflowTemplateRequest
)
from app.models.workflow import (

    WorkflowDefinition, WorkflowState, WorkflowTransition,
    WorkflowInstance, WorkflowAction, WorkflowActionType
)

logger = get_logger(__name__)

router = APIRouter()


# ========== Workflow Definition Endpoints ==========

@router.post("/definitions", response_model=WorkflowDefinitionResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow_definition(
    workflow_data: WorkflowDefinitionCreate,
    db: Session = Depends(get_db),
    # current_user parameter removed for development
):
    """Create a new workflow definition"""
    service = WorkflowService(db)
    current_user = None  # Development mode

    workflow = service.create_workflow_definition(
        name=workflow_data.name,
        code=workflow_data.code,
        module=workflow_data.module,
        description=workflow_data.description,
        created_by=current_user.id if current_user else None,
        is_active=workflow_data.is_active,
        is_default=workflow_data.is_default,
        requires_approval=workflow_data.requires_approval,
        auto_submit=workflow_data.auto_submit,
        approval_threshold_amount=workflow_data.approval_threshold_amount,
        max_approval_levels=workflow_data.max_approval_levels,
        branch_id=workflow_data.branch_id
    )

    return workflow


@router.get("/definitions", response_model=List[WorkflowDefinitionResponse])
async def get_workflow_definitions(
    module: Optional[str] = Query(None, description="Filter by module"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db)
):
    """Get all workflow definitions"""
    query = db.query(WorkflowDefinition)

    if module:
        query = query.filter(WorkflowDefinition.module == module)
    if is_active is not None:
        query = query.filter(WorkflowDefinition.is_active == is_active)

    return query.all()


@router.get("/definitions/{workflow_id}", response_model=WorkflowDefinitionResponse)
async def get_workflow_definition(
    workflow_id: str,
    db: Session = Depends(get_db)
):
    """Get workflow definition by ID"""
    workflow = db.query(WorkflowDefinition).filter(
        WorkflowDefinition.id == workflow_id
    ).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow definition not found"
        )

    return workflow


@router.put("/definitions/{workflow_id}", response_model=WorkflowDefinitionResponse)
async def update_workflow_definition(
    workflow_id: str,
    workflow_data: WorkflowDefinitionUpdate,
    db: Session = Depends(get_db)
):
    """Update workflow definition"""
    workflow = db.query(WorkflowDefinition).filter(
        WorkflowDefinition.id == workflow_id
    ).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow definition not found"
        )

    # Update fields
    update_data = workflow_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(workflow, field, value)

    db.commit()
    db.refresh(workflow)

    return workflow


@router.delete("/definitions/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow_definition(
    workflow_id: str,
    db: Session = Depends(get_db)
):
    """Delete workflow definition"""
    workflow = db.query(WorkflowDefinition).filter(
        WorkflowDefinition.id == workflow_id
    ).first()

    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow definition not found"
        )

    # Check if any instances exist
    instance_count = db.query(WorkflowInstance).filter(
        WorkflowInstance.workflow_definition_id == workflow_id
    ).count()

    if instance_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete workflow: {instance_count} instances exist. Set inactive instead."
        )

    db.delete(workflow)
    db.commit()


# ========== Workflow State Endpoints ==========

@router.post("/states", response_model=WorkflowStateResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow_state(
    state_data: WorkflowStateCreate,
    db: Session = Depends(get_db)
):
    """Create a new workflow state"""
    state = WorkflowState(**state_data.dict())
    db.add(state)
    db.commit()
    db.refresh(state)

    return state


@router.get("/states", response_model=List[WorkflowStateResponse])
async def get_workflow_states(
    workflow_definition_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get workflow states"""
    query = db.query(WorkflowState)

    if workflow_definition_id:
        query = query.filter(WorkflowState.workflow_definition_id == workflow_definition_id)

    return query.order_by(WorkflowState.display_order).all()


@router.put("/states/{state_id}", response_model=WorkflowStateResponse)
async def update_workflow_state(
    state_id: str,
    state_data: WorkflowStateUpdate,
    db: Session = Depends(get_db)
):
    """Update workflow state"""
    state = db.query(WorkflowState).filter(WorkflowState.id == state_id).first()

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow state not found"
        )

    update_data = state_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(state, field, value)

    db.commit()
    db.refresh(state)

    return state


# ========== Workflow Transition Endpoints ==========

@router.post("/transitions", response_model=WorkflowTransitionResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow_transition(
    transition_data: WorkflowTransitionCreate,
    db: Session = Depends(get_db)
):
    """Create a new workflow transition"""
    transition = WorkflowTransition(**transition_data.dict())
    db.add(transition)
    db.commit()
    db.refresh(transition)

    return transition


@router.get("/transitions", response_model=List[WorkflowTransitionResponse])
async def get_workflow_transitions(
    workflow_definition_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get workflow transitions"""
    query = db.query(WorkflowTransition)

    if workflow_definition_id:
        query = query.filter(WorkflowTransition.workflow_definition_id == workflow_definition_id)

    return query.order_by(WorkflowTransition.display_order).all()


@router.put("/transitions/{transition_id}", response_model=WorkflowTransitionResponse)
async def update_workflow_transition(
    transition_id: str,
    transition_data: WorkflowTransitionUpdate,
    db: Session = Depends(get_db)
):
    """Update workflow transition"""
    transition = db.query(WorkflowTransition).filter(
        WorkflowTransition.id == transition_id
    ).first()

    if not transition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow transition not found"
        )

    update_data = transition_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transition, field, value)

    db.commit()
    db.refresh(transition)

    return transition


# ========== Workflow Instance Endpoints ==========

@router.post("/instances", response_model=WorkflowInstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow_instance(
    instance_data: WorkflowInstanceCreate,
    db: Session = Depends(get_db)
):
    """Create a new workflow instance (initiate workflow for an entity)"""
    service = WorkflowService(db)
    current_user = None  # Development mode - replace with actual user
    user_id = "system"  # Development mode

    instance = service.initiate_workflow(
        entity_type=instance_data.entity_type,
        entity_id=instance_data.entity_id,
        initiated_by=user_id,
        workflow_definition_id=instance_data.workflow_definition_id,
        branch_id=instance_data.branch_id,
        metadata=instance_data.metadata
    )

    return instance


@router.get("/instances", response_model=List[WorkflowInstanceResponse])
async def get_workflow_instances(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get workflow instances"""
    query = db.query(WorkflowInstance)

    if entity_type:
        query = query.filter(WorkflowInstance.entity_type == entity_type)
    if entity_id:
        query = query.filter(WorkflowInstance.entity_id == entity_id)
    if status:
        query = query.filter(WorkflowInstance.status == status)

    return query.offset(skip).limit(limit).all()


@router.get("/instances/{instance_id}", response_model=WorkflowInstanceDetailResponse)
async def get_workflow_instance(
    instance_id: str,
    db: Session = Depends(get_db)
):
    """Get workflow instance with full details"""
    instance = db.query(WorkflowInstance).filter(
        WorkflowInstance.id == instance_id
    ).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow instance not found"
        )

    return instance


# ========== Workflow Actions (Submit, Approve, Reject, etc) ==========

@router.post("/instances/{instance_id}/submit", response_model=WorkflowInstanceResponse)
async def submit_workflow(
    instance_id: str,
    request_data: WorkflowSubmitRequest,
    db: Session = Depends(get_db)
):
    """Submit workflow for approval"""
    service = WorkflowService(db)
    user_id = "system"  # Development mode

    instance = service.transition_workflow(
        workflow_instance_id=instance_id,
        user_id=user_id,
        action=WorkflowActionType.SUBMIT,
        comment=request_data.comment,
        attachments=request_data.attachments
    )

    return instance


@router.post("/instances/{instance_id}/approve", response_model=WorkflowInstanceResponse)
async def approve_workflow(
    instance_id: str,
    request_data: WorkflowApproveRequest,
    db: Session = Depends(get_db)
):
    """Approve workflow item"""
    service = WorkflowService(db)
    user_id = "system"  # Development mode

    instance = service.transition_workflow(
        workflow_instance_id=instance_id,
        user_id=user_id,
        action=WorkflowActionType.APPROVE,
        comment=request_data.comment,
        attachments=request_data.attachments
    )

    return instance


@router.post("/instances/{instance_id}/reject", response_model=WorkflowInstanceResponse)
async def reject_workflow(
    instance_id: str,
    request_data: WorkflowRejectRequest,
    db: Session = Depends(get_db)
):
    """Reject workflow item"""
    service = WorkflowService(db)
    user_id = "system"  # Development mode

    instance = service.transition_workflow(
        workflow_instance_id=instance_id,
        user_id=user_id,
        action=WorkflowActionType.REJECT,
        comment=request_data.comment,
        reason=request_data.reason,
        attachments=request_data.attachments
    )

    return instance


@router.post("/instances/{instance_id}/reassign", response_model=WorkflowInstanceResponse)
async def reassign_workflow(
    instance_id: str,
    request_data: WorkflowReassignRequest,
    db: Session = Depends(get_db)
):
    """Reassign workflow to another user"""
    service = WorkflowService(db)
    user_id = "system"  # Development mode

    instance = service.transition_workflow(
        workflow_instance_id=instance_id,
        user_id=user_id,
        action=WorkflowActionType.REASSIGN,
        comment=request_data.comment,
        reassigned_to=request_data.assignee_id
    )

    return instance


@router.post("/instances/{instance_id}/transition", response_model=WorkflowInstanceResponse)
async def execute_workflow_transition(
    instance_id: str,
    request_data: WorkflowTransitionRequest,
    db: Session = Depends(get_db)
):
    """Execute a specific workflow transition"""
    # Get the transition to determine action type
    transition = db.query(WorkflowTransition).filter(
        WorkflowTransition.id == request_data.transition_id
    ).first()

    if not transition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transition not found"
        )

    service = WorkflowService(db)
    user_id = "system"  # Development mode

    instance = service.transition_workflow(
        workflow_instance_id=instance_id,
        user_id=user_id,
        action=transition.action,
        comment=request_data.comment,
        attachments=request_data.attachments
    )

    return instance


@router.get("/instances/{instance_id}/available-actions", response_model=List[WorkflowAvailableAction])
async def get_available_actions(
    instance_id: str,
    db: Session = Depends(get_db)
):
    """Get available actions for current user on workflow instance"""
    service = WorkflowService(db)
    user_id = "system"  # Development mode

    actions = service.get_available_actions(instance_id, user_id)
    return actions


@router.get("/instances/{instance_id}/history", response_model=List[WorkflowActionResponse])
async def get_workflow_history(
    instance_id: str,
    db: Session = Depends(get_db)
):
    """Get full history of workflow actions"""
    service = WorkflowService(db)

    actions = service.get_workflow_history(instance_id)
    return actions


# ========== Workflow Dashboard & User-Specific ==========

@router.get("/my-pending-approvals", response_model=List[WorkflowInstanceResponse])
async def get_my_pending_approvals(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get workflow items pending approval by current user"""
    service = WorkflowService(db)
    user_id = "system"  # Development mode

    instances = service.get_pending_approvals_for_user(user_id, limit)
    return instances


@router.get("/dashboard", response_model=WorkflowDashboardResponse)
async def get_workflow_dashboard(
    db: Session = Depends(get_db)
):
    """Get workflow dashboard for current user"""
    service = WorkflowService(db)
    user_id = "system"  # Development mode

    # Get pending approvals
    pending_instances = service.get_pending_approvals_for_user(user_id, limit=100)

    # Build dashboard response
    dashboard = WorkflowDashboardResponse(
        pending_approval_count=len(pending_instances),
        pending_my_action_count=len([i for i in pending_instances if i.current_assignee == user_id]),
        submitted_by_me_count=db.query(WorkflowInstance).filter(
            WorkflowInstance.initiated_by == user_id
        ).count(),
        completed_today_count=db.query(WorkflowInstance).filter(
            WorkflowInstance.completed_at >= datetime.utcnow().date()
        ).count(),
        overdue_count=db.query(WorkflowInstance).filter(
            WorkflowInstance.due_date < datetime.utcnow(),
            WorkflowInstance.completed_at.is_(None)
        ).count(),
        pending_items=[]
    )

    return dashboard


# ========== Workflow Templates ==========

@router.post("/templates/purchase-approval", response_model=WorkflowDefinitionResponse)
async def create_purchase_approval_workflow(
    template_data: WorkflowTemplateRequest,
    db: Session = Depends(get_db)
):
    """Create a standard purchase approval workflow from template"""
    service = WorkflowService(db)
    current_user = None  # Development mode

    workflow = service.create_standard_purchase_workflow(
        branch_id=template_data.branch_id,
        created_by=current_user.id if current_user else None
    )

    return workflow
