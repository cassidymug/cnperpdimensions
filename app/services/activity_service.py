"""
Activity Tracking Service
Comprehensive service for logging and querying user activities
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import Request

from app.models.activity_log import (
    ActivityLog, ApprovalLog, PermissionChangeLog,
    UserSession, EntityAccessLog,
    ActivityType, ActivityModule, ActivitySeverity
)
from app.models.user import User
from app.models.role import Role


class ActivityService:
    """Service for tracking and querying user activities"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== Activity Logging ====================

    def log_activity(
        self,
        user_id: str,
        activity_type: ActivityType,
        module: ActivityModule,
        action: str,
        description: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        branch_id: Optional[str] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        severity: ActivitySeverity = ActivitySeverity.INFO,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> ActivityLog:
        """
        Log a user activity

        Args:
            user_id: ID of user performing the action
            activity_type: Type of activity (create, update, approve, etc.)
            module: Module where activity occurred
            action: Specific action taken
            description: Human-readable description
            entity_type: Type of entity affected (e.g., "Invoice")
            entity_id: ID of affected entity
            entity_name: Display name of entity
            branch_id: Branch context
            old_values: State before change
            new_values: State after change
            metadata: Additional context
            success: Whether action succeeded
            error_message: Error details if failed
            severity: Severity level
            ip_address: User's IP address
            user_agent: User's browser/client
            session_id: Session identifier
        """
        # Get user details
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Get branch name if provided
        branch_name = None
        if branch_id:
            from app.models.branch import Branch
            branch = self.db.query(Branch).filter(Branch.id == branch_id).first()
            if branch:
                branch_name = branch.name

        # Create activity log
        activity = ActivityLog(
            user_id=user_id,
            username=user.username,
            role_name=user.role.name if user.role else None,
            activity_type=activity_type,
            module=module,
            action=action,
            description=description,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            branch_id=branch_id,
            branch_name=branch_name,
            old_values=old_values,
            new_values=new_values,
            metadata=metadata,
            success=success,
            error_message=error_message,
            severity=severity,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            performed_at=datetime.utcnow()
        )

        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)

        return activity

    def log_activity_from_request(
        self,
        request: Request,
        user_id: str,
        activity_type: ActivityType,
        module: ActivityModule,
        action: str,
        **kwargs
    ) -> ActivityLog:
        """
        Log activity with automatic extraction of request context

        Args:
            request: FastAPI request object
            user_id: User ID
            activity_type: Type of activity
            module: Module name
            action: Action name
            **kwargs: Additional arguments for log_activity
        """
        # Extract IP address
        ip_address = request.client.host if request.client else None

        # Extract user agent
        user_agent = request.headers.get("user-agent")

        # Extract session ID from authorization header or cookie
        session_id = None
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_id = auth_header[7:]  # Remove "Bearer " prefix

        return self.log_activity(
            user_id=user_id,
            activity_type=activity_type,
            module=module,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            **kwargs
        )

    # ==================== Approval Logging ====================

    def log_approval(
        self,
        approver_id: str,
        entity_type: str,
        entity_id: str,
        action: str,
        decision: str,
        entity_reference: Optional[str] = None,
        workflow_id: Optional[str] = None,
        from_state: Optional[str] = None,
        to_state: Optional[str] = None,
        comments: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        on_behalf_of: Optional[str] = None,
        delegation_reason: Optional[str] = None,
        approval_level: Optional[str] = None,
        branch_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> ApprovalLog:
        """
        Log an approval/rejection action

        Args:
            approver_id: ID of user making approval decision
            entity_type: Type of entity (e.g., "PurchaseOrder")
            entity_id: ID of entity being approved
            action: Action taken ("approve", "reject", etc.)
            decision: Final decision ("approved", "rejected", etc.)
            entity_reference: Human-readable reference (e.g., "PO-2024-001")
            workflow_id: Associated workflow instance
            from_state: Previous workflow state
            to_state: New workflow state
            comments: Approver's comments
            attachments: List of attachment file references
            on_behalf_of: User ID if delegated
            delegation_reason: Why approval was delegated
            approval_level: Approval level (L1, L2, L3)
            branch_id: Branch context
            metadata: Additional data
            ip_address: IP address
        """
        # Get approver details
        approver = self.db.query(User).filter(User.id == approver_id).first()
        if not approver:
            raise ValueError(f"Approver {approver_id} not found")

        approval = ApprovalLog(
            approver_id=approver_id,
            approver_name=approver.username,
            approver_role=approver.role.name if approver.role else None,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_reference=entity_reference,
            workflow_id=workflow_id,
            from_state=from_state,
            to_state=to_state,
            action=action,
            decision=decision,
            comments=comments,
            attachments=attachments,
            on_behalf_of=on_behalf_of,
            delegation_reason=delegation_reason,
            approval_level=approval_level,
            branch_id=branch_id,
            metadata=metadata,
            ip_address=ip_address,
            approved_at=datetime.utcnow()
        )

        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)

        return approval

    # ==================== Permission Change Logging ====================

    def log_permission_change(
        self,
        changed_by_id: str,
        change_type: str,
        target_user_id: Optional[str] = None,
        target_role_id: Optional[str] = None,
        permission_id: Optional[str] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        reason: Optional[str] = None,
        approved_by_id: Optional[str] = None,
        approval_date: Optional[datetime] = None,
        branch_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None,
        ip_address: Optional[str] = None
    ) -> PermissionChangeLog:
        """
        Log a permission or role change

        Args:
            changed_by_id: User making the change
            change_type: Type of change (role_assign, permission_grant, etc.)
            target_user_id: User receiving the change
            target_role_id: Role being modified
            permission_id: Permission being granted/revoked
            old_value: Previous state
            new_value: New state
            reason: Reason for change
            approved_by_id: User who approved the change
            approval_date: When change was approved
            branch_id: Branch context
            metadata: Additional data
            expires_at: Expiration date for temporary permissions
            ip_address: IP address
        """
        # Get user details
        changed_by = self.db.query(User).filter(User.id == changed_by_id).first()
        if not changed_by:
            raise ValueError(f"User {changed_by_id} not found")

        # Get target user details
        target_user_name = None
        if target_user_id:
            target_user = self.db.query(User).filter(User.id == target_user_id).first()
            if target_user:
                target_user_name = target_user.username

        # Get target role details
        target_role_name = None
        if target_role_id:
            target_role = self.db.query(Role).filter(Role.id == target_role_id).first()
            if target_role:
                target_role_name = target_role.name

        # Get permission details
        permission_name = None
        if permission_id:
            from app.models.role import Permission
            permission = self.db.query(Permission).filter(Permission.id == permission_id).first()
            if permission:
                permission_name = permission.name

        # Get approver details
        approved_by_name = None
        if approved_by_id:
            approved_by = self.db.query(User).filter(User.id == approved_by_id).first()
            if approved_by:
                approved_by_name = approved_by.username

        change_log = PermissionChangeLog(
            changed_by_id=changed_by_id,
            changed_by_name=changed_by.username,
            target_user_id=target_user_id,
            target_user_name=target_user_name,
            target_role_id=target_role_id,
            target_role_name=target_role_name,
            change_type=change_type,
            permission_id=permission_id,
            permission_name=permission_name,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            approved_by_id=approved_by_id,
            approved_by_name=approved_by_name,
            approval_date=approval_date,
            branch_id=branch_id,
            metadata=metadata,
            expires_at=expires_at,
            ip_address=ip_address,
            changed_at=datetime.utcnow()
        )

        self.db.add(change_log)
        self.db.commit()
        self.db.refresh(change_log)

        return change_log

    # ==================== Access Logging ====================

    def log_entity_access(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        module: ActivityModule,
        entity_name: Optional[str] = None,
        access_method: Optional[str] = None,
        branch_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EntityAccessLog:
        """Log access to a sensitive entity"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        access_log = EntityAccessLog(
            user_id=user_id,
            username=user.username,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            access_method=access_method,
            module=module,
            branch_id=branch_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
            accessed_at=datetime.utcnow()
        )

        self.db.add(access_log)
        self.db.commit()
        self.db.refresh(access_log)

        return access_log

    # ==================== Query Methods ====================

    def get_user_activities(
        self,
        user_id: str,
        module: Optional[ActivityModule] = None,
        activity_type: Optional[ActivityType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ActivityLog]:
        """Get activities for a specific user"""
        query = self.db.query(ActivityLog).filter(ActivityLog.user_id == user_id)

        if module:
            query = query.filter(ActivityLog.module == module)

        if activity_type:
            query = query.filter(ActivityLog.activity_type == activity_type)

        if start_date:
            query = query.filter(ActivityLog.performed_at >= start_date)

        if end_date:
            query = query.filter(ActivityLog.performed_at <= end_date)

        return query.order_by(desc(ActivityLog.performed_at)).limit(limit).offset(offset).all()

    def get_entity_activities(
        self,
        entity_type: str,
        entity_id: str,
        include_access_logs: bool = False
    ) -> Dict[str, List]:
        """Get all activities related to a specific entity"""
        activities = self.db.query(ActivityLog).filter(
            and_(
                ActivityLog.entity_type == entity_type,
                ActivityLog.entity_id == entity_id
            )
        ).order_by(desc(ActivityLog.performed_at)).all()

        approvals = self.db.query(ApprovalLog).filter(
            and_(
                ApprovalLog.entity_type == entity_type,
                ApprovalLog.entity_id == entity_id
            )
        ).order_by(desc(ApprovalLog.approved_at)).all()

        result = {
            "activities": activities,
            "approvals": approvals
        }

        if include_access_logs:
            access_logs = self.db.query(EntityAccessLog).filter(
                and_(
                    EntityAccessLog.entity_type == entity_type,
                    EntityAccessLog.entity_id == entity_id
                )
            ).order_by(desc(EntityAccessLog.accessed_at)).all()
            result["access_logs"] = access_logs

        return result

    def get_approval_history(
        self,
        approver_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[ApprovalLog]:
        """Get approval history with optional filters"""
        query = self.db.query(ApprovalLog)

        if approver_id:
            query = query.filter(ApprovalLog.approver_id == approver_id)

        if entity_type:
            query = query.filter(ApprovalLog.entity_type == entity_type)

        if start_date:
            query = query.filter(ApprovalLog.approved_at >= start_date)

        if end_date:
            query = query.filter(ApprovalLog.approved_at <= end_date)

        return query.order_by(desc(ApprovalLog.approved_at)).limit(limit).all()

    def get_permission_changes(
        self,
        target_user_id: Optional[str] = None,
        changed_by_id: Optional[str] = None,
        change_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[PermissionChangeLog]:
        """Get permission change history"""
        query = self.db.query(PermissionChangeLog)

        if target_user_id:
            query = query.filter(PermissionChangeLog.target_user_id == target_user_id)

        if changed_by_id:
            query = query.filter(PermissionChangeLog.changed_by_id == changed_by_id)

        if change_type:
            query = query.filter(PermissionChangeLog.change_type == change_type)

        if start_date:
            query = query.filter(PermissionChangeLog.changed_at >= start_date)

        return query.order_by(desc(PermissionChangeLog.changed_at)).limit(limit).all()

    def get_module_activities(
        self,
        module: ActivityModule,
        branch_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[ActivityLog]:
        """Get activities for a specific module"""
        query = self.db.query(ActivityLog).filter(ActivityLog.module == module)

        if branch_id:
            query = query.filter(ActivityLog.branch_id == branch_id)

        if start_date:
            query = query.filter(ActivityLog.performed_at >= start_date)

        if end_date:
            query = query.filter(ActivityLog.performed_at <= end_date)

        return query.order_by(desc(ActivityLog.performed_at)).limit(limit).all()

    def get_activity_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
        module: Optional[ActivityModule] = None
    ) -> Dict[str, Any]:
        """Get activity statistics"""
        query = self.db.query(ActivityLog)

        if start_date:
            query = query.filter(ActivityLog.performed_at >= start_date)

        if end_date:
            query = query.filter(ActivityLog.performed_at <= end_date)

        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)

        if module:
            query = query.filter(ActivityLog.module == module)

        total_activities = query.count()

        # Activities by type
        by_type = self.db.query(
            ActivityLog.activity_type,
            func.count(ActivityLog.id).label('count')
        ).filter(query.whereclause).group_by(ActivityLog.activity_type).all()

        # Activities by module
        by_module = self.db.query(
            ActivityLog.module,
            func.count(ActivityLog.id).label('count')
        ).filter(query.whereclause).group_by(ActivityLog.module).all()

        # Failed activities
        failed_count = query.filter(ActivityLog.success == False).count()

        # Most active users
        top_users = self.db.query(
            ActivityLog.username,
            func.count(ActivityLog.id).label('count')
        ).filter(query.whereclause).group_by(ActivityLog.username).order_by(desc('count')).limit(10).all()

        return {
            "total_activities": total_activities,
            "failed_activities": failed_count,
            "success_rate": (total_activities - failed_count) / total_activities if total_activities > 0 else 0,
            "by_type": {str(t[0]): t[1] for t in by_type},
            "by_module": {str(m[0]): m[1] for m in by_module},
            "top_users": [{"username": u[0], "count": u[1]} for u in top_users]
        }
