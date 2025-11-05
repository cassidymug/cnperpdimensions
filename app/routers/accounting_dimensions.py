"""
API routes for Accounting Dimensions

This module provides REST API endpoints for managing accounting dimensions,
dimension values, and their assignments to financial transactions.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.accounting_dimensions_service import AccountingDimensionService
from app.schemas.accounting_dimensions import (
    AccountingDimensionCreate, AccountingDimensionUpdate, AccountingDimensionResponse,
    AccountingDimensionValueCreate, AccountingDimensionValueUpdate, AccountingDimensionValueResponse,
    AccountingDimensionAssignmentCreate, AccountingDimensionAssignmentUpdate, AccountingDimensionAssignmentResponse,
    DimensionAnalysisFilter, DimensionAnalysisResult, DimensionValidationResult,
    JournalEntryWithDimensions, BulkDimensionAssignment
)
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/accounting/dimensions", tags=["accounting-dimensions"])


# Dimension endpoints
@router.post("/", response_model=AccountingDimensionResponse, status_code=status.HTTP_201_CREATED)
def create_dimension(
    dimension_data: AccountingDimensionCreate,
    db: Session = Depends(get_db)
):
    """Create a new accounting dimension"""
    try:
        logger.info(f"Creating accounting dimension: {dimension_data.name}")
        service = AccountingDimensionService(db)
        dimension = service.create_dimension(dimension_data)
        logger.info(f"Successfully created dimension: {dimension.id} - {dimension.name}")
        return AccountingDimensionResponse.from_orm(dimension)
    except ValueError as e:
        log_error_with_context(logger, "Validation error creating dimension",
                              dimension_name=dimension_data.name, error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_exception(logger, e, context=f"Error creating dimension: {dimension_data.name}")
        raise HTTPException(status_code=500, detail="Internal server error creating dimension")


@router.get("/", response_model=List[AccountingDimensionResponse])
def get_dimensions(
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    dimension_type: Optional[str] = Query(None, description="Filter by dimension type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    include_values: bool = Query(False, description="Include dimension values"),
    db: Session = Depends(get_db)
):
    """Get all accounting dimensions with optional filtering"""
    try:
        logger.debug(f"Fetching dimensions: branch={branch_id}, type={dimension_type}, active={is_active}")
        service = AccountingDimensionService(db)
        dimensions = service.get_dimensions(
            branch_id=branch_id,
            dimension_type=dimension_type,
            is_active=is_active,
            include_values=include_values
        )
        logger.info(f"Retrieved {len(dimensions)} accounting dimensions")
        return [AccountingDimensionResponse.from_orm(d) for d in dimensions]
    except Exception as e:
        log_exception(logger, e, context="Error fetching accounting dimensions")
        raise HTTPException(status_code=500, detail="Internal server error fetching dimensions")


@router.get("/{dimension_id}", response_model=AccountingDimensionResponse)
def get_dimension(
    dimension_id: str = Path(..., description="Dimension ID"),
    db: Session = Depends(get_db)
):
    """Get a specific dimension by ID"""
    service = AccountingDimensionService(db)
    dimension = service.get_dimension(dimension_id)
    if not dimension:
        raise HTTPException(status_code=404, detail="Dimension not found")
    return AccountingDimensionResponse.from_orm(dimension)


@router.put("/{dimension_id}", response_model=AccountingDimensionResponse)
def update_dimension(
    dimension_id: str = Path(..., description="Dimension ID"),
    update_data: AccountingDimensionUpdate = ...,
    db: Session = Depends(get_db)
):
    """Update a dimension"""
    service = AccountingDimensionService(db)
    try:
        dimension = service.update_dimension(dimension_id, update_data)
        if not dimension:
            raise HTTPException(status_code=404, detail="Dimension not found")
        return AccountingDimensionResponse.from_orm(dimension)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{dimension_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dimension(
    dimension_id: str = Path(..., description="Dimension ID"),
    force: bool = Query(False, description="Force delete even if assignments exist"),
    db: Session = Depends(get_db)
):
    """Delete a dimension"""
    service = AccountingDimensionService(db)
    try:
        success = service.delete_dimension(dimension_id, force=force)
        if not success:
            raise HTTPException(status_code=404, detail="Dimension not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Dimension value endpoints
@router.post("/{dimension_id}/values", response_model=AccountingDimensionValueResponse, status_code=status.HTTP_201_CREATED)
def create_dimension_value(
    dimension_id: str = Path(..., description="Dimension ID"),
    value_data: AccountingDimensionValueCreate = ...,
    db: Session = Depends(get_db)
):
    """Create a new dimension value"""
    service = AccountingDimensionService(db)
    try:
        # Ensure dimension_id matches the path parameter
        value_data.dimension_id = dimension_id
        value = service.create_dimension_value(value_data)
        return AccountingDimensionValueResponse.from_orm(value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{dimension_id}/values", response_model=List[AccountingDimensionValueResponse])
def get_dimension_values(
    dimension_id: str = Path(..., description="Dimension ID"),
    parent_value_id: Optional[str] = Query(None, description="Filter by parent value ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    include_children: bool = Query(False, description="Include child values"),
    db: Session = Depends(get_db)
):
    """Get dimension values"""
    service = AccountingDimensionService(db)
    values = service.get_dimension_values(
        dimension_id=dimension_id,
        parent_value_id=parent_value_id,
        is_active=is_active,
        include_children=include_children
    )
    return [AccountingDimensionValueResponse.from_orm(v) for v in values]


@router.get("/{dimension_id}/hierarchy", response_model=List[Dict[str, Any]])
def get_dimension_hierarchy(
    dimension_id: str = Path(..., description="Dimension ID"),
    db: Session = Depends(get_db)
):
    """Get hierarchical tree structure for a dimension"""
    service = AccountingDimensionService(db)
    tree = service.get_dimension_hierarchy_tree(dimension_id)
    return tree


@router.get("/values/{value_id}", response_model=AccountingDimensionValueResponse)
def get_dimension_value(
    value_id: str = Path(..., description="Dimension value ID"),
    db: Session = Depends(get_db)
):
    """Get a specific dimension value by ID"""
    service = AccountingDimensionService(db)
    value = service.get_dimension_value(value_id)
    if not value:
        raise HTTPException(status_code=404, detail="Dimension value not found")
    return AccountingDimensionValueResponse.from_orm(value)


@router.put("/values/{value_id}", response_model=AccountingDimensionValueResponse)
def update_dimension_value(
    value_id: str = Path(..., description="Dimension value ID"),
    update_data: AccountingDimensionValueUpdate = ...,
    db: Session = Depends(get_db)
):
    """Update a dimension value"""
    service = AccountingDimensionService(db)
    try:
        value = service.update_dimension_value(value_id, update_data)
        if not value:
            raise HTTPException(status_code=404, detail="Dimension value not found")
        return AccountingDimensionValueResponse.from_orm(value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/values/{value_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dimension_value(
    value_id: str = Path(..., description="Dimension value ID"),
    force: bool = Query(False, description="Force delete even if assignments exist"),
    db: Session = Depends(get_db)
):
    """Delete a dimension value"""
    service = AccountingDimensionService(db)
    try:
        success = service.delete_dimension_value(value_id, force=force)
        if not success:
            raise HTTPException(status_code=404, detail="Dimension value not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Assignment endpoints
@router.post("/assignments", response_model=AccountingDimensionAssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    assignment_data: AccountingDimensionAssignmentCreate,
    db: Session = Depends(get_db)
):
    """Create a dimension assignment to a journal entry"""
    service = AccountingDimensionService(db)
    try:
        assignment = service.create_assignment(assignment_data)
        return AccountingDimensionAssignmentResponse.from_orm(assignment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assignments", response_model=List[AccountingDimensionAssignmentResponse])
def get_assignments(
    journal_entry_id: Optional[str] = Query(None, description="Filter by journal entry ID"),
    dimension_id: Optional[str] = Query(None, description="Filter by dimension ID"),
    dimension_value_id: Optional[str] = Query(None, description="Filter by dimension value ID"),
    db: Session = Depends(get_db)
):
    """Get dimension assignments with optional filtering"""
    service = AccountingDimensionService(db)
    assignments = service.get_assignments(
        journal_entry_id=journal_entry_id,
        dimension_id=dimension_id,
        dimension_value_id=dimension_value_id
    )
    return [AccountingDimensionAssignmentResponse.from_orm(a) for a in assignments]


@router.put("/assignments/{assignment_id}", response_model=AccountingDimensionAssignmentResponse)
def update_assignment(
    assignment_id: str = Path(..., description="Assignment ID"),
    update_data: AccountingDimensionAssignmentUpdate = ...,
    db: Session = Depends(get_db)
):
    """Update a dimension assignment"""
    service = AccountingDimensionService(db)
    try:
        assignment = service.update_assignment(assignment_id, update_data)
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        return AccountingDimensionAssignmentResponse.from_orm(assignment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: str = Path(..., description="Assignment ID"),
    db: Session = Depends(get_db)
):
    """Delete a dimension assignment"""
    service = AccountingDimensionService(db)
    success = service.delete_assignment(assignment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Assignment not found")


@router.post("/assignments/bulk", response_model=List[AccountingDimensionAssignmentResponse])
def create_bulk_assignments(
    bulk_data: BulkDimensionAssignment,
    db: Session = Depends(get_db)
):
    """Create dimension assignments for multiple journal entries"""
    service = AccountingDimensionService(db)
    created_assignments = []
    errors = []

    for journal_entry_id in bulk_data.journal_entry_ids:
        for assignment_base in bulk_data.assignments:
            try:
                assignment_data = AccountingDimensionAssignmentCreate(
                    journal_entry_id=journal_entry_id,
                    **assignment_base.dict()
                )
                assignment = service.create_assignment(assignment_data)
                created_assignments.append(AccountingDimensionAssignmentResponse.from_orm(assignment))
            except ValueError as e:
                errors.append(f"Entry {journal_entry_id}: {str(e)}")

    if errors and not created_assignments:
        raise HTTPException(status_code=400, detail={"errors": errors})

    return created_assignments


# Analysis and reporting endpoints
@router.post("/analysis", response_model=DimensionAnalysisResult)
def analyze_by_dimensions(
    filters: DimensionAnalysisFilter,
    db: Session = Depends(get_db)
):
    """Perform multi-dimensional analysis of financial data"""
    service = AccountingDimensionService(db)
    try:
        result = service.analyze_by_dimensions(filters)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/journal-entries/{journal_entry_id}/validation", response_model=DimensionValidationResult)
def validate_journal_entry_dimensions(
    journal_entry_id: str = Path(..., description="Journal entry ID"),
    db: Session = Depends(get_db)
):
    """Validate dimension assignments for a journal entry"""
    service = AccountingDimensionService(db)
    result = service.validate_journal_entry_dimensions(journal_entry_id)
    return result


@router.get("/journal-entries/{journal_entry_id}/dimensions", response_model=JournalEntryWithDimensions)
def get_journal_entry_with_dimensions(
    journal_entry_id: str = Path(..., description="Journal entry ID"),
    db: Session = Depends(get_db)
):
    """Get journal entry with all dimension assignments"""
    service = AccountingDimensionService(db)

    # Get journal entry
    from app.models.accounting import JournalEntry
    journal_entry = db.query(JournalEntry).filter(JournalEntry.id == journal_entry_id).first()
    if not journal_entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    # Get assignments
    assignments = service.get_assignments(journal_entry_id=journal_entry_id)

    return JournalEntryWithDimensions(
        id=journal_entry.id,
        accounting_code_id=journal_entry.accounting_code_id,
        accounting_entry_id=journal_entry.accounting_entry_id,
        entry_type=journal_entry.entry_type,
        narration=journal_entry.narration,
        date=journal_entry.date,
        reference=journal_entry.reference,
        description=journal_entry.description,
        debit_amount=float(journal_entry.debit_amount or 0),
        credit_amount=float(journal_entry.credit_amount or 0),
        branch_id=journal_entry.branch_id,
        origin=journal_entry.origin or "manual",
        dimension_assignments=[AccountingDimensionAssignmentResponse.from_orm(a) for a in assignments]
    )


# Utility endpoints
@router.get("/types", response_model=List[str])
def get_dimension_types():
    """Get available dimension types"""
    from app.models.accounting_dimensions import DimensionType
    return [t.value for t in DimensionType]


@router.get("/scopes", response_model=List[str])
def get_dimension_scopes():
    """Get available dimension scopes"""
    from app.models.accounting_dimensions import DimensionScope
    return [s.value for s in DimensionScope]


@router.get("/stats", response_model=Dict[str, Any])
def get_dimension_statistics(
    db: Session = Depends(get_db)
):
    """Get statistics about dimensions usage"""
    service = AccountingDimensionService(db)

    from app.models.accounting_dimensions import AccountingDimension, AccountingDimensionValue, AccountingDimensionAssignment

    stats = {
        "total_dimensions": db.query(AccountingDimension).count(),
        "active_dimensions": db.query(AccountingDimension).filter(AccountingDimension.is_active == True).count(),
        "total_values": db.query(AccountingDimensionValue).count(),
        "active_values": db.query(AccountingDimensionValue).filter(AccountingDimensionValue.is_active == True).count(),
        "total_assignments": db.query(AccountingDimensionAssignment).count(),
        "dimensions_by_type": {},
        "assignments_by_dimension": {}
    }

    # Get dimensions by type
    from sqlalchemy import func
    type_counts = db.query(
        AccountingDimension.dimension_type,
        func.count(AccountingDimension.id)
    ).group_by(AccountingDimension.dimension_type).all()

    for dim_type, count in type_counts:
        stats["dimensions_by_type"][dim_type] = count

    # Get assignments by dimension
    assignment_counts = db.query(
        AccountingDimension.name,
        func.count(AccountingDimensionAssignment.id)
    ).join(
        AccountingDimensionAssignment,
        AccountingDimension.id == AccountingDimensionAssignment.dimension_id
    ).group_by(AccountingDimension.id, AccountingDimension.name).all()

    for dim_name, count in assignment_counts:
        stats["assignments_by_dimension"][dim_name] = count

    return stats
