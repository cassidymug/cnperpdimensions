"""
Workflow Service - Business logic for role-based workflow management

This service handles:
- Workflow state transitions
- Role-based authorization
- Approval routing
- Notification triggering
- Workflow templates
"""
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from datetime import datetime, timedelta
from fastapi import HTTPException, status

from app.models.workflow import (
    WorkflowDefinition, WorkflowState, WorkflowTransition,
    WorkflowInstance, WorkflowAction, WorkflowNotification,
    WorkflowStatus, WorkflowActionType
)
from app.models.user import User
from app.models.role import Role


class WorkflowService:
    """Service for managing workflow operations"""

    def __init__(self, db: Session):
        self.db = db

    # ========== Workflow Definition Management ==========

    def create_workflow_definition(
        self,
        name: str,
        code: str,
        module: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
        **kwargs
    ) -> WorkflowDefinition:
        """Create a new workflow definition"""
        # Check if code already exists
        existing = self.db.query(WorkflowDefinition).filter(
            WorkflowDefinition.code == code
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow with code '{code}' already exists"
            )

        workflow = WorkflowDefinition(
            name=name,
            code=code,
            module=module,
            description=description,
            created_by=created_by,
            **kwargs
        )

        self.db.add(workflow)
        self.db.commit()
        self.db.refresh(workflow)

        return workflow

    def get_workflow_for_module(
        self,
        module: str,
        branch_id: Optional[str] = None
    ) -> Optional[WorkflowDefinition]:
        """Get default workflow for a module"""
        query = self.db.query(WorkflowDefinition).filter(
            and_(
                WorkflowDefinition.module == module,
                WorkflowDefinition.is_active == True,
                WorkflowDefinition.is_default == True
            )
        )

        # Try branch-specific workflow first
        if branch_id:
            branch_workflow = query.filter(
                WorkflowDefinition.branch_id == branch_id
            ).first()
            if branch_workflow:
                return branch_workflow

        # Fall back to global workflow
        return query.filter(WorkflowDefinition.branch_id.is_(None)).first()

    # ========== Workflow Instance Management ==========

    def initiate_workflow(
        self,
        entity_type: str,
        entity_id: str,
        initiated_by: str,
        workflow_definition_id: Optional[str] = None,
        module: Optional[str] = None,
        branch_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WorkflowInstance:
        """
        Initiate a new workflow instance for an entity

        Args:
            entity_type: Type of entity (e.g., 'purchase', 'invoice')
            entity_id: ID of the entity
            initiated_by: User ID who initiated
            workflow_definition_id: Specific workflow to use (optional)
            module: Module name (required if workflow_definition_id not provided)
            branch_id: Branch ID for branch-specific workflows
            metadata: Additional metadata
        """
        # Get workflow definition
        if workflow_definition_id:
            workflow_def = self.db.query(WorkflowDefinition).filter(
                WorkflowDefinition.id == workflow_definition_id
            ).first()
        elif module:
            workflow_def = self.get_workflow_for_module(module, branch_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide either workflow_definition_id or module"
            )

        if not workflow_def:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active workflow found for module '{module}'"
            )

        # Get initial state
        initial_state = self.db.query(WorkflowState).filter(
            and_(
                WorkflowState.workflow_definition_id == workflow_def.id,
                WorkflowState.is_initial == True
            )
        ).first()

        if not initial_state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow '{workflow_def.name}' has no initial state defined"
            )

        # Create workflow instance
        instance = WorkflowInstance(
            workflow_definition_id=workflow_def.id,
            current_state_id=initial_state.id,
            entity_type=entity_type,
            entity_id=entity_id,
            status=initial_state.status,
            initiated_by=initiated_by,
            initiated_at=datetime.utcnow(),
            current_assignee=initiated_by,
            branch_id=branch_id,
            workflow_metadata=metadata or {}
        )

        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)

        # Record initial action
        self._record_action(
            workflow_instance_id=instance.id,
            action=WorkflowActionType.SUBMIT,
            from_state_id=None,
            to_state_id=initial_state.id,
            performed_by=initiated_by,
            comment="Workflow initiated"
        )

        # Auto-submit if configured
        if workflow_def.auto_submit:
            self.transition_workflow(instance.id, initiated_by, WorkflowActionType.SUBMIT)

        return instance

    def transition_workflow(
        self,
        workflow_instance_id: str,
        user_id: str,
        action: WorkflowActionType,
        comment: Optional[str] = None,
        reason: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        reassigned_to: Optional[str] = None
    ) -> WorkflowInstance:
        """
        Execute a workflow transition

        Validates user permissions and executes state transition
        """
        # Get workflow instance
        instance = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.id == workflow_instance_id
        ).first()

        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow instance not found"
            )

        # Get user and role
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Find valid transition
        transition = self._find_valid_transition(
            workflow_instance=instance,
            action=action,
            user=user
        )

        if not transition:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have permission to perform action '{action}' in current state"
            )

        # Validate requirements
        if transition.requires_comment and not comment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Comment is required for this action"
            )

        if transition.requires_attachment and not attachments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Attachment is required for this action"
            )

        # Calculate duration in previous state
        last_action = self.db.query(WorkflowAction).filter(
            WorkflowAction.workflow_instance_id == workflow_instance_id
        ).order_by(desc(WorkflowAction.action_date)).first()

        duration_seconds = None
        if last_action:
            duration = datetime.utcnow() - last_action.action_date
            duration_seconds = int(duration.total_seconds())

        # Execute transition
        old_state_id = instance.current_state_id
        new_state = self.db.query(WorkflowState).filter(
            WorkflowState.id == transition.to_state_id
        ).first()

        instance.current_state_id = new_state.id
        instance.status = new_state.status

        # Handle reassignment
        if action == WorkflowActionType.REASSIGN and reassigned_to:
            instance.current_assignee = reassigned_to
        elif new_state.is_final:
            instance.completed_at = datetime.utcnow()
            instance.completed_by = user_id

        # Record action
        self._record_action(
            workflow_instance_id=workflow_instance_id,
            action=action,
            from_state_id=old_state_id,
            to_state_id=new_state.id,
            performed_by=user_id,
            comment=comment,
            reason=reason,
            attachments=attachments,
            reassigned_to=reassigned_to,
            duration_seconds=duration_seconds
        )

        self.db.commit()
        self.db.refresh(instance)

        # Send notifications
        if transition.notify_on_transition:
            self._send_notifications(instance, new_state, action, user_id)

        return instance

    def _find_valid_transition(
        self,
        workflow_instance: WorkflowInstance,
        action: WorkflowActionType,
        user: User
    ) -> Optional[WorkflowTransition]:
        """Find a valid transition for the current state and user role"""
        # Get all transitions from current state with matching action
        transitions = self.db.query(WorkflowTransition).filter(
            and_(
                WorkflowTransition.workflow_definition_id == workflow_instance.workflow_definition_id,
                WorkflowTransition.from_state_id == workflow_instance.current_state_id,
                WorkflowTransition.action == action
            )
        ).all()

        # Check if user has permission for any transition
        for transition in transitions:
            if self._user_can_execute_transition(user, transition):
                return transition

        return None

    def _user_can_execute_transition(
        self,
        user: User,
        transition: WorkflowTransition
    ) -> bool:
        """Check if user can execute a specific transition"""
        # If no role restrictions, anyone can execute
        if not transition.allowed_roles:
            return True

        # Check if user's role is in allowed roles
        if user.role_id and user.role_id in transition.allowed_roles:
            return True

        return False

    def _record_action(
        self,
        workflow_instance_id: str,
        action: WorkflowActionType,
        to_state_id: str,
        performed_by: str,
        from_state_id: Optional[str] = None,
        comment: Optional[str] = None,
        reason: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        reassigned_to: Optional[str] = None,
        duration_seconds: Optional[int] = None
    ) -> WorkflowAction:
        """Record a workflow action in audit trail"""
        workflow_action = WorkflowAction(
            workflow_instance_id=workflow_instance_id,
            from_state_id=from_state_id,
            to_state_id=to_state_id,
            action=action,
            action_date=datetime.utcnow(),
            performed_by=performed_by,
            comment=comment,
            reason=reason,
            attachments=attachments or [],
            reassigned_to=reassigned_to,
            duration_seconds=duration_seconds
        )

        self.db.add(workflow_action)
        return workflow_action

    def _send_notifications(
        self,
        workflow_instance: WorkflowInstance,
        new_state: WorkflowState,
        action: WorkflowActionType,
        performed_by: str
    ):
        """Send notifications for workflow state change"""
        # Get users to notify from state configuration
        if not new_state.notified_roles:
            return

        # Get all users with notified roles
        users_to_notify = self.db.query(User).filter(
            and_(
                User.role_id.in_(new_state.notified_roles),
                User.active == True
            )
        ).all()

        # Create notifications
        for user in users_to_notify:
            notification = WorkflowNotification(
                workflow_instance_id=workflow_instance.id,
                recipient_user_id=user.id,
                notification_type="in_app",
                subject=f"Workflow Action Required: {workflow_instance.entity_type}",
                message=f"A {workflow_instance.entity_type} requires your attention in state: {new_state.name}",
                sent_at=datetime.utcnow()
            )
            self.db.add(notification)

    # ========== Query Methods ==========

    def get_pending_approvals_for_user(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[WorkflowInstance]:
        """Get all workflow instances pending approval by user"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not user.role_id:
            return []

        # Get all states where user's role can approve
        states_user_can_approve = self.db.query(WorkflowState).filter(
            WorkflowState.allowed_roles.contains([user.role_id])
        ).all()

        state_ids = [s.id for s in states_user_can_approve]

        # Get instances in these states
        instances = self.db.query(WorkflowInstance).filter(
            and_(
                WorkflowInstance.current_state_id.in_(state_ids),
                WorkflowInstance.status.in_([
                    WorkflowStatus.PENDING_APPROVAL,
                    WorkflowStatus.SUBMITTED
                ])
            )
        ).order_by(desc(WorkflowInstance.initiated_at)).limit(limit).all()

        return instances

    def get_workflow_history(
        self,
        workflow_instance_id: str
    ) -> List[WorkflowAction]:
        """Get full history of actions for a workflow instance"""
        return self.db.query(WorkflowAction).filter(
            WorkflowAction.workflow_instance_id == workflow_instance_id
        ).order_by(WorkflowAction.action_date).all()

    def get_available_actions(
        self,
        workflow_instance_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Get all available actions user can take on a workflow instance"""
        instance = self.db.query(WorkflowInstance).filter(
            WorkflowInstance.id == workflow_instance_id
        ).first()

        if not instance:
            return []

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return []

        # Get all transitions from current state
        transitions = self.db.query(WorkflowTransition).filter(
            and_(
                WorkflowTransition.workflow_definition_id == instance.workflow_definition_id,
                WorkflowTransition.from_state_id == instance.current_state_id
            )
        ).order_by(WorkflowTransition.display_order).all()

        # Filter transitions user can execute
        available = []
        for transition in transitions:
            if self._user_can_execute_transition(user, transition):
                to_state = self.db.query(WorkflowState).filter(
                    WorkflowState.id == transition.to_state_id
                ).first()

                available.append({
                    "transition_id": transition.id,
                    "action": transition.action,
                    "label": transition.button_label or transition.name,
                    "color": transition.button_color,
                    "requires_comment": transition.requires_comment,
                    "requires_attachment": transition.requires_attachment,
                    "to_state_name": to_state.name if to_state else ""
                })

        return available

    # ========== Template Methods ==========

    def create_standard_purchase_workflow(
        self,
        branch_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> WorkflowDefinition:
        """Create a standard 3-level purchase approval workflow"""
        # Create workflow definition
        workflow = self.create_workflow_definition(
            name="Purchase Order Approval (3-Level)",
            code="PO_APPROVAL_3LEVEL",
            module="purchases",
            description="Standard 3-level approval: Submitter -> Manager -> Finance Director",
            branch_id=branch_id,
            created_by=created_by,
            max_approval_levels=3
        )

        # Create states
        draft_state = WorkflowState(
            workflow_definition_id=workflow.id,
            name="Draft",
            code="DRAFT",
            status=WorkflowStatus.DRAFT,
            is_initial=True,
            display_order=1,
            color="#6b7280",
            icon="file-earmark"
        )

        submitted_state = WorkflowState(
            workflow_definition_id=workflow.id,
            name="Pending Manager Approval",
            code="PENDING_MGR",
            status=WorkflowStatus.PENDING_APPROVAL,
            requires_approval=True,
            display_order=2,
            color="#f59e0b",
            icon="clock"
        )

        finance_state = WorkflowState(
            workflow_definition_id=workflow.id,
            name="Pending Finance Approval",
            code="PENDING_FIN",
            status=WorkflowStatus.PENDING_APPROVAL,
            requires_approval=True,
            display_order=3,
            color="#f59e0b",
            icon="cash-stack"
        )

        approved_state = WorkflowState(
            workflow_definition_id=workflow.id,
            name="Approved",
            code="APPROVED",
            status=WorkflowStatus.APPROVED,
            is_final=True,
            display_order=4,
            color="#10b981",
            icon="check-circle"
        )

        rejected_state = WorkflowState(
            workflow_definition_id=workflow.id,
            name="Rejected",
            code="REJECTED",
            status=WorkflowStatus.REJECTED,
            is_final=True,
            display_order=5,
            color="#ef4444",
            icon="x-circle"
        )

        self.db.add_all([draft_state, submitted_state, finance_state, approved_state, rejected_state])
        self.db.flush()

        # Create transitions (simplified - in production you'd set role IDs)
        transitions = [
            # Submit
            WorkflowTransition(
                workflow_definition_id=workflow.id,
                from_state_id=draft_state.id,
                to_state_id=submitted_state.id,
                name="Submit for Approval",
                action=WorkflowActionType.SUBMIT,
                button_label="Submit",
                button_color="primary",
                display_order=1
            ),
            # Manager approve -> Finance
            WorkflowTransition(
                workflow_definition_id=workflow.id,
                from_state_id=submitted_state.id,
                to_state_id=finance_state.id,
                name="Manager Approval",
                action=WorkflowActionType.APPROVE,
                button_label="Approve",
                button_color="success",
                display_order=1
            ),
            # Manager reject
            WorkflowTransition(
                workflow_definition_id=workflow.id,
                from_state_id=submitted_state.id,
                to_state_id=rejected_state.id,
                name="Manager Rejection",
                action=WorkflowActionType.REJECT,
                button_label="Reject",
                button_color="danger",
                requires_comment=True,
                display_order=2
            ),
            # Finance approve -> Approved
            WorkflowTransition(
                workflow_definition_id=workflow.id,
                from_state_id=finance_state.id,
                to_state_id=approved_state.id,
                name="Finance Approval",
                action=WorkflowActionType.APPROVE,
                button_label="Approve",
                button_color="success",
                display_order=1
            ),
            # Finance reject
            WorkflowTransition(
                workflow_definition_id=workflow.id,
                from_state_id=finance_state.id,
                to_state_id=rejected_state.id,
                name="Finance Rejection",
                action=WorkflowActionType.REJECT,
                button_label="Reject",
                button_color="danger",
                requires_comment=True,
                display_order=2
            ),
        ]

        self.db.add_all(transitions)
        self.db.commit()
        self.db.refresh(workflow)

        return workflow
