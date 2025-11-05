"""
Accounting Dimensions Service

This service provides business logic for managing accounting dimensions,
dimension values, and their assignments to financial transactions.
"""

import json
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.exc import IntegrityError

from app.models.accounting_dimensions import (
    AccountingDimension, AccountingDimensionValue,
    AccountingDimensionAssignment, DimensionTemplate,
    DimensionType, DimensionScope
)
from app.models.accounting import JournalEntry, AccountingCode
from app.schemas.accounting_dimensions import (
    AccountingDimensionCreate, AccountingDimensionUpdate,
    AccountingDimensionValueCreate, AccountingDimensionValueUpdate,
    AccountingDimensionAssignmentCreate, AccountingDimensionAssignmentUpdate,
    DimensionAnalysisFilter, DimensionAnalysisResult, DimensionValidationResult
)
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)


class AccountingDimensionService:
    """Service for managing accounting dimensions"""

    def __init__(self, db: Session):
        self.db = db

    # Dimension CRUD operations
    def create_dimension(self, dimension_data: AccountingDimensionCreate, branch_id: Optional[str] = None) -> AccountingDimension:
        """Create a new accounting dimension"""
        try:
            logger.debug(f"Creating dimension: {dimension_data.name} ({dimension_data.code})")

            # Convert to dict and handle branch_id separately to avoid duplicate keyword argument
            data_dict = dimension_data.dict(exclude={'branch_id'})
            dimension = AccountingDimension(
                **data_dict,
                branch_id=branch_id or dimension_data.branch_id
            )

            self.db.add(dimension)
            self.db.commit()
            self.db.refresh(dimension)

            logger.info(f"Successfully created dimension: {dimension.id} - {dimension.name}")
            return dimension
        except IntegrityError as e:
            self.db.rollback()
            error_msg = f"Dimension with code '{dimension_data.code}' already exists"
            log_error_with_context(logger, error_msg, code=dimension_data.code, name=dimension_data.name)
            raise ValueError(error_msg)
        except Exception as e:
            self.db.rollback()
            log_exception(logger, e, context=f"Error creating dimension: {dimension_data.name}")
            raise

    def get_dimension(self, dimension_id: str) -> Optional[AccountingDimension]:
        """Get dimension by ID"""
        return self.db.query(AccountingDimension).filter(
            AccountingDimension.id == dimension_id
        ).first()

    def get_dimensions(self,
                      branch_id: Optional[str] = None,
                      dimension_type: Optional[DimensionType] = None,
                      is_active: Optional[bool] = None,
                      include_values: bool = False) -> List[AccountingDimension]:
        """Get dimensions with optional filtering"""
        query = self.db.query(AccountingDimension)

        if include_values:
            query = query.options(joinedload(AccountingDimension.dimension_values))

        # Apply filters
        filters = []
        if branch_id:
            filters.append(or_(
                AccountingDimension.branch_id == branch_id,
                AccountingDimension.scope == DimensionScope.GLOBAL
            ))
        if dimension_type:
            filters.append(AccountingDimension.dimension_type == dimension_type)
        if is_active is not None:
            filters.append(AccountingDimension.is_active == is_active)

        if filters:
            query = query.filter(and_(*filters))

        return query.order_by(AccountingDimension.display_order, AccountingDimension.name).all()

    def update_dimension(self, dimension_id: str, update_data: AccountingDimensionUpdate) -> Optional[AccountingDimension]:
        """Update an existing dimension"""
        dimension = self.get_dimension(dimension_id)
        if not dimension:
            return None

        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(dimension, field, value)

        try:
            self.db.commit()
            self.db.refresh(dimension)
            return dimension
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Update failed due to constraint violation")

    def delete_dimension(self, dimension_id: str, force: bool = False) -> bool:
        """Delete a dimension"""
        dimension = self.get_dimension(dimension_id)
        if not dimension:
            return False

        # Check for existing assignments unless force delete
        if not force:
            assignment_count = self.db.query(AccountingDimensionAssignment).filter(
                AccountingDimensionAssignment.dimension_id == dimension_id
            ).count()

            if assignment_count > 0:
                raise ValueError(f"Cannot delete dimension: {assignment_count} assignments exist")

        self.db.delete(dimension)
        self.db.commit()
        return True

    # Dimension Value CRUD operations
    def create_dimension_value(self, value_data: AccountingDimensionValueCreate) -> AccountingDimensionValue:
        """Create a new dimension value"""
        # Validate dimension exists
        dimension = self.get_dimension(value_data.dimension_id)
        if not dimension:
            raise ValueError("Dimension not found")

        # Calculate hierarchy level and path
        hierarchy_level = 1
        hierarchy_path = None

        if value_data.parent_value_id:
            parent = self.get_dimension_value(value_data.parent_value_id)
            if not parent:
                raise ValueError("Parent value not found")

            if parent.dimension_id != value_data.dimension_id:
                raise ValueError("Parent value must belong to the same dimension")

            hierarchy_level = parent.hierarchy_level + 1
            if hierarchy_level > dimension.max_hierarchy_levels:
                raise ValueError(f"Maximum hierarchy level ({dimension.max_hierarchy_levels}) exceeded")

            hierarchy_path = f"{parent.hierarchy_path or ''}/{parent.code}".lstrip('/')

        value = AccountingDimensionValue(
            **value_data.dict(),
            hierarchy_level=hierarchy_level,
            hierarchy_path=hierarchy_path
        )

        try:
            self.db.add(value)
            self.db.commit()
            self.db.refresh(value)
            return value
        except IntegrityError:
            self.db.rollback()
            raise ValueError(f"Value with code '{value_data.code}' already exists in this dimension")

    def get_dimension_value(self, value_id: str) -> Optional[AccountingDimensionValue]:
        """Get dimension value by ID"""
        return self.db.query(AccountingDimensionValue).filter(
            AccountingDimensionValue.id == value_id
        ).first()

    def get_dimension_values(self,
                           dimension_id: str,
                           parent_value_id: Optional[str] = None,
                           is_active: Optional[bool] = None,
                           include_children: bool = False) -> List[AccountingDimensionValue]:
        """Get dimension values with optional filtering"""
        query = self.db.query(AccountingDimensionValue).filter(
            AccountingDimensionValue.dimension_id == dimension_id
        )

        if include_children:
            query = query.options(joinedload(AccountingDimensionValue.child_values))

        # Apply filters
        filters = []
        if parent_value_id is not None:
            filters.append(AccountingDimensionValue.parent_value_id == parent_value_id)
        if is_active is not None:
            filters.append(AccountingDimensionValue.is_active == is_active)

        if filters:
            query = query.filter(and_(*filters))

        return query.order_by(
            AccountingDimensionValue.hierarchy_level,
            AccountingDimensionValue.display_order,
            AccountingDimensionValue.name
        ).all()

    def update_dimension_value(self, value_id: str, update_data: AccountingDimensionValueUpdate) -> Optional[AccountingDimensionValue]:
        """Update an existing dimension value"""
        value = self.get_dimension_value(value_id)
        if not value:
            return None

        update_dict = update_data.dict(exclude_unset=True)

        # Handle parent change (requires hierarchy recalculation)
        if 'parent_value_id' in update_dict:
            parent_id = update_dict['parent_value_id']
            if parent_id:
                parent = self.get_dimension_value(parent_id)
                if not parent or parent.dimension_id != value.dimension_id:
                    raise ValueError("Invalid parent value")

                # Check for circular reference
                if self._would_create_circular_reference(value.id, parent_id):
                    raise ValueError("Parent change would create circular reference")

        for field, new_value in update_dict.items():
            setattr(value, field, new_value)

        try:
            self.db.commit()
            self.db.refresh(value)
            return value
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Update failed due to constraint violation")

    def delete_dimension_value(self, value_id: str, force: bool = False) -> bool:
        """Delete a dimension value"""
        value = self.get_dimension_value(value_id)
        if not value:
            return False

        # Check for child values
        child_count = self.db.query(AccountingDimensionValue).filter(
            AccountingDimensionValue.parent_value_id == value_id
        ).count()

        if child_count > 0 and not force:
            raise ValueError(f"Cannot delete value: {child_count} child values exist")

        # Check for assignments unless force delete
        if not force:
            assignment_count = self.db.query(AccountingDimensionAssignment).filter(
                AccountingDimensionAssignment.dimension_value_id == value_id
            ).count()

            if assignment_count > 0:
                raise ValueError(f"Cannot delete value: {assignment_count} assignments exist")

        self.db.delete(value)
        self.db.commit()
        return True

    # Assignment operations
    def create_assignment(self, assignment_data: AccountingDimensionAssignmentCreate) -> AccountingDimensionAssignment:
        """Create a dimension assignment to a journal entry"""
        # Validate journal entry exists
        journal_entry = self.db.query(JournalEntry).filter(
            JournalEntry.id == assignment_data.journal_entry_id
        ).first()
        if not journal_entry:
            raise ValueError("Journal entry not found")

        # Validate dimension and value
        dimension = self.get_dimension(assignment_data.dimension_id)
        if not dimension:
            raise ValueError("Dimension not found")

        dimension_value = self.get_dimension_value(assignment_data.dimension_value_id)
        if not dimension_value or dimension_value.dimension_id != assignment_data.dimension_id:
            raise ValueError("Invalid dimension value")

        # Check if assignment already exists (unless multiple values allowed)
        existing = self.db.query(AccountingDimensionAssignment).filter(
            and_(
                AccountingDimensionAssignment.journal_entry_id == assignment_data.journal_entry_id,
                AccountingDimensionAssignment.dimension_id == assignment_data.dimension_id
            )
        ).first()

        if existing and not dimension.allow_multiple_values:
            raise ValueError("Assignment already exists for this dimension")

        # Calculate allocation amount if not provided
        allocation_amount = assignment_data.allocation_amount
        if allocation_amount is None:
            entry_amount = abs(journal_entry.debit_amount or 0) + abs(journal_entry.credit_amount or 0)
            allocation_amount = entry_amount * (assignment_data.allocation_percentage / 100)

        assignment = AccountingDimensionAssignment(
            **assignment_data.dict(),
            allocation_amount=allocation_amount
        )

        try:
            self.db.add(assignment)
            self.db.commit()
            self.db.refresh(assignment)
            return assignment
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Assignment creation failed")

    def get_assignments(self,
                       journal_entry_id: Optional[str] = None,
                       dimension_id: Optional[str] = None,
                       dimension_value_id: Optional[str] = None) -> List[AccountingDimensionAssignment]:
        """Get dimension assignments with optional filtering"""
        query = self.db.query(AccountingDimensionAssignment)

        filters = []
        if journal_entry_id:
            filters.append(AccountingDimensionAssignment.journal_entry_id == journal_entry_id)
        if dimension_id:
            filters.append(AccountingDimensionAssignment.dimension_id == dimension_id)
        if dimension_value_id:
            filters.append(AccountingDimensionAssignment.dimension_value_id == dimension_value_id)

        if filters:
            query = query.filter(and_(*filters))

        return query.all()

    def update_assignment(self, assignment_id: str, update_data: AccountingDimensionAssignmentUpdate) -> Optional[AccountingDimensionAssignment]:
        """Update an existing assignment"""
        assignment = self.db.query(AccountingDimensionAssignment).filter(
            AccountingDimensionAssignment.id == assignment_id
        ).first()

        if not assignment:
            return None

        update_dict = update_data.dict(exclude_unset=True)

        # Validate new dimension value if provided
        if 'dimension_value_id' in update_dict:
            new_value = self.get_dimension_value(update_dict['dimension_value_id'])
            if not new_value or new_value.dimension_id != assignment.dimension_id:
                raise ValueError("Invalid dimension value")

        for field, value in update_dict.items():
            setattr(assignment, field, value)

        self.db.commit()
        self.db.refresh(assignment)
        return assignment

    def delete_assignment(self, assignment_id: str) -> bool:
        """Delete a dimension assignment"""
        assignment = self.db.query(AccountingDimensionAssignment).filter(
            AccountingDimensionAssignment.id == assignment_id
        ).first()

        if not assignment:
            return False

        self.db.delete(assignment)
        self.db.commit()
        return True

    # Analysis and reporting
    def analyze_by_dimensions(self, filters: DimensionAnalysisFilter) -> DimensionAnalysisResult:
        """Perform multi-dimensional analysis of financial data"""
        # Build base query for journal entries with dimension assignments
        query = self.db.query(
            JournalEntry,
            AccountingDimensionAssignment,
            AccountingDimension,
            AccountingDimensionValue
        ).join(
            AccountingDimensionAssignment,
            JournalEntry.id == AccountingDimensionAssignment.journal_entry_id
        ).join(
            AccountingDimension,
            AccountingDimensionAssignment.dimension_id == AccountingDimension.id
        ).join(
            AccountingDimensionValue,
            AccountingDimensionAssignment.dimension_value_id == AccountingDimensionValue.id
        )

        # Apply filters
        filter_conditions = []

        # Date filters
        if filters.date_from:
            filter_conditions.append(JournalEntry.date >= filters.date_from)
        if filters.date_to:
            filter_conditions.append(JournalEntry.date <= filters.date_to)

        # Branch filters
        if filters.branch_ids:
            filter_conditions.append(JournalEntry.branch_id.in_(filters.branch_ids))

        # Dimension value filters
        if filters.dimension_values:
            dimension_filters = []
            for dim_id, value_ids in filters.dimension_values.items():
                dimension_filters.append(
                    and_(
                        AccountingDimensionAssignment.dimension_id == dim_id,
                        AccountingDimensionAssignment.dimension_value_id.in_(value_ids)
                    )
                )
            if dimension_filters:
                filter_conditions.append(or_(*dimension_filters))

        # Active filters
        if not filters.include_inactive:
            filter_conditions.extend([
                AccountingDimension.is_active == True,
                AccountingDimensionValue.is_active == True
            ])

        if filter_conditions:
            query = query.filter(and_(*filter_conditions))

        # Execute query and process results
        results = query.all()

        # Aggregate data by dimensions
        dimension_breakdown = {}
        totals = {'debit': 0.0, 'credit': 0.0, 'net': 0.0}

        for entry, assignment, dimension, value in results:
            dim_name = dimension.name
            value_name = value.name

            if dim_name not in dimension_breakdown:
                dimension_breakdown[dim_name] = {}

            if value_name not in dimension_breakdown[dim_name]:
                dimension_breakdown[dim_name][value_name] = {
                    'debit': 0.0, 'credit': 0.0, 'net': 0.0, 'count': 0
                }

            # Calculate allocated amounts
            debit_amount = (entry.debit_amount or 0) * (assignment.allocation_percentage / 100)
            credit_amount = (entry.credit_amount or 0) * (assignment.allocation_percentage / 100)

            dimension_breakdown[dim_name][value_name]['debit'] += float(debit_amount)
            dimension_breakdown[dim_name][value_name]['credit'] += float(credit_amount)
            dimension_breakdown[dim_name][value_name]['net'] += float(debit_amount - credit_amount)
            dimension_breakdown[dim_name][value_name]['count'] += 1

            totals['debit'] += float(debit_amount)
            totals['credit'] += float(credit_amount)
            totals['net'] += float(debit_amount - credit_amount)

        return DimensionAnalysisResult(
            dimension_breakdown=dimension_breakdown,
            totals=totals,
            metadata={
                'filter_applied': filters.dict(),
                'total_entries': len(results),
                'analysis_date': datetime.now().isoformat()
            }
        )

    def validate_journal_entry_dimensions(self, journal_entry_id: str) -> DimensionValidationResult:
        """Validate that journal entry has all required dimension assignments"""
        # Get all required dimensions for the branch
        journal_entry = self.db.query(JournalEntry).filter(JournalEntry.id == journal_entry_id).first()
        if not journal_entry:
            return DimensionValidationResult(
                is_valid=False,
                errors=["Journal entry not found"]
            )

        required_dimensions = self.get_dimensions(
            branch_id=journal_entry.branch_id,
            is_active=True
        )
        required_dimensions = [d for d in required_dimensions if d.is_required]

        # Get existing assignments
        existing_assignments = self.get_assignments(journal_entry_id=journal_entry_id)
        assigned_dimension_ids = {a.dimension_id for a in existing_assignments}

        # Check for missing required dimensions
        missing_required = []
        for dimension in required_dimensions:
            if dimension.id not in assigned_dimension_ids:
                missing_required.append(dimension.name)

        # Validate allocation percentages
        warnings = []
        errors = []

        dimension_totals = {}
        for assignment in existing_assignments:
            dim_id = assignment.dimension_id
            if dim_id not in dimension_totals:
                dimension_totals[dim_id] = 0.0
            dimension_totals[dim_id] += assignment.allocation_percentage

        for dim_id, total_percentage in dimension_totals.items():
            dimension = self.get_dimension(dim_id)
            if dimension and not dimension.allow_multiple_values and total_percentage != 100.0:
                warnings.append(f"Dimension '{dimension.name}' allocation is {total_percentage}%, expected 100%")

        is_valid = len(missing_required) == 0 and len(errors) == 0

        return DimensionValidationResult(
            is_valid=is_valid,
            missing_required_dimensions=missing_required,
            warnings=warnings,
            errors=errors
        )

    # Helper methods
    def _would_create_circular_reference(self, value_id: str, new_parent_id: str) -> bool:
        """Check if setting a new parent would create a circular reference"""
        current_id = new_parent_id
        visited = set()

        while current_id and current_id not in visited:
            if current_id == value_id:
                return True

            visited.add(current_id)
            parent = self.get_dimension_value(current_id)
            current_id = parent.parent_value_id if parent else None

        return False

    def get_dimension_hierarchy_tree(self, dimension_id: str) -> List[Dict[str, Any]]:
        """Get hierarchical tree structure for a dimension"""
        all_values = self.get_dimension_values(dimension_id, is_active=True)

        # Build hierarchy tree
        value_map = {v.id: v for v in all_values}
        tree = []

        def build_tree(parent_id: Optional[str] = None) -> List[Dict[str, Any]]:
            children = [v for v in all_values if v.parent_value_id == parent_id]
            result = []

            for child in sorted(children, key=lambda x: (x.display_order, x.name)):
                node = {
                    'id': child.id,
                    'code': child.code,
                    'name': child.name,
                    'full_path': child.get_full_path(),
                    'level': child.hierarchy_level,
                    'children': build_tree(child.id)
                }
                result.append(node)

            return result

        return build_tree()
