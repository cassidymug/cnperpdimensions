from __future__ import annotations

from datetime import datetime, date, time
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.branch import Branch
from app.models.pos import PosSession, PosShiftReconciliation
from app.models.sales import Sale
from app.services.app_setting_service import AppSettingService

TWOPLACES = Decimal('0.01')


class PosReconciliationService:
    """Business logic for reconciling POS cashier shifts."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings_service = AppSettingService(db)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_shift_reconciliations(self, shift_date: date, branch_id: Optional[str] = None) -> Dict[str, Any]:
        """Return reconciliation detail for all POS sessions on a specific day."""
        sessions = self._load_sessions_for_date(shift_date, branch_id)
        session_ids = [session.id for session in sessions]

        cash_sales_map = self._cash_sales_by_session(session_ids)
        reconciliation_map = self._reconciliations_by_session(session_ids)

        currency_settings = self.settings_service.get_currency_settings()

        summaries: Dict[str, Decimal] = {
            'total_float_given': Decimal('0'),
            'total_cash_sales': Decimal('0'),
            'total_expected_cash': Decimal('0'),
            'total_cash_collected': Decimal('0'),
            'total_variance': Decimal('0')
        }

        status_counters = {
            'balanced': 0,
            'variance': 0,
            'pending': 0,
            'open': 0
        }

        session_payloads: List[Dict[str, Any]] = []

        for session in sessions:
            record = reconciliation_map.get(session.id)
            payload = self._serialize_session(
                session=session,
                record=record,
                cash_sales=cash_sales_map.get(session.id, Decimal('0')),
            )

            session_payloads.append(payload)

            summaries['total_float_given'] += Decimal(str(payload['float_given']))
            summaries['total_cash_sales'] += Decimal(str(payload['cash_sales']))
            summaries['total_expected_cash'] += Decimal(str(payload['expected_cash']))
            summaries['total_cash_collected'] += Decimal(str(payload['cash_collected']))
            summaries['total_variance'] += Decimal(str(payload['variance']))

            status_counters[payload['status']] = status_counters.get(payload['status'], 0) + 1

        branch_name: Optional[str] = None
        if branch_id:
            branch = self.db.query(Branch).filter(Branch.id == branch_id).first()
            branch_name = branch.name if branch else None

        return {
            'shift_date': shift_date.isoformat(),
            'branch_id': branch_id,
            'branch_name': branch_name,
            'summary': {
                'session_count': len(sessions),
                'balanced_sessions': status_counters.get('balanced', 0),
                'variance_sessions': status_counters.get('variance', 0),
                'pending_sessions': status_counters.get('pending', 0),
                'open_sessions': status_counters.get('open', 0),
                'total_float_given': float(self._quantize(summaries['total_float_given'])),
                'total_cash_sales': float(self._quantize(summaries['total_cash_sales'])),
                'total_expected_cash': float(self._quantize(summaries['total_expected_cash'])),
                'total_cash_collected': float(self._quantize(summaries['total_cash_collected'])),
                'total_variance': float(self._quantize(summaries['total_variance']))
            },
            'sessions': session_payloads,
            'currency_code': currency_settings.get('currency'),
            'currency_symbol': currency_settings.get('currency_symbol'),
            'generated_at': datetime.utcnow().isoformat()
        }

    def record_shift_reconciliation(
        self,
        *,
        session_id: str,
        float_given: Decimal,
        cash_collected: Decimal,
        shift_date: Optional[date] = None,
        notes: Optional[str] = None,
        verifier_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create or update reconciliation data for a POS session."""
        session: Optional[PosSession] = (
            self.db.query(PosSession)
            .options(joinedload(PosSession.user), joinedload(PosSession.branch))
            .filter(PosSession.id == session_id)
            .first()
        )

        if not session:
            return {'success': False, 'error': 'POS session not found'}

        float_given = self._quantize(float_given)
        cash_collected = self._quantize(cash_collected)

        if shift_date is None:
            if session.closed_at:
                shift_date = session.closed_at.date()
            elif session.opened_at:
                shift_date = session.opened_at.date()
            else:
                shift_date = date.today()

        cash_sales = self._cash_sales_for_session(session.id)
        expected_cash = self._quantize(float_given + cash_sales)
        variance = self._quantize(cash_collected - expected_cash)

        existing_record = (
            self.db.query(PosShiftReconciliation)
            .filter(PosShiftReconciliation.session_id == session.id)
            .first()
        )

        now = datetime.utcnow()

        if existing_record:
            existing_record.float_given = float_given
            existing_record.cash_collected = cash_collected
            existing_record.cash_sales = cash_sales
            existing_record.expected_cash = expected_cash
            existing_record.variance = variance
            existing_record.shift_date = shift_date
            existing_record.notes = notes
            if verifier_id:
                existing_record.verified_by = verifier_id
                existing_record.verified_at = now
        else:
            existing_record = PosShiftReconciliation(
                session_id=session.id,
                cashier_id=session.user_id,
                branch_id=session.branch_id,
                shift_date=shift_date,
                float_given=float_given,
                cash_collected=cash_collected,
                cash_sales=cash_sales,
                expected_cash=expected_cash,
                variance=variance,
                notes=notes,
                verified_by=verifier_id,
                verified_at=now if verifier_id else None
            )
            self.db.add(existing_record)

        session.float_amount = float_given
        session.cash_submitted = cash_collected
        if session.closed_at is None:
            session.closed_at = now
        if session.status == 'open':
            session.status = 'closed'
        if verifier_id:
            session.verified_by = verifier_id
            session.verified_at = now
        if notes:
            session.verification_note = notes

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        self.db.refresh(session)
        self.db.refresh(existing_record)

        payload = self._serialize_session(
            session=session,
            record=existing_record,
            cash_sales=cash_sales,
        )

        return {
            'success': True,
            'data': payload,
            'message': 'Shift reconciliation recorded successfully'
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_sessions_for_date(self, shift_date: date, branch_id: Optional[str]) -> List[PosSession]:
        start_dt = datetime.combine(shift_date, time.min)
        end_dt = datetime.combine(shift_date, time.max)

        query = (
            self.db.query(PosSession)
            .options(joinedload(PosSession.user), joinedload(PosSession.branch))
            .filter(
                or_(
                    and_(PosSession.opened_at != None, PosSession.opened_at >= start_dt, PosSession.opened_at <= end_dt),
                    and_(PosSession.closed_at != None, PosSession.closed_at >= start_dt, PosSession.closed_at <= end_dt)
                )
            )
        )

        if branch_id:
            query = query.filter(PosSession.branch_id == branch_id)

        return query.order_by(PosSession.opened_at.asc()).all()

    def _cash_sales_by_session(self, session_ids: List[str]) -> Dict[str, Decimal]:
        if not session_ids:
            return {}

        rows = (
            self.db.query(
                Sale.pos_session_id,
                func.coalesce(func.sum(Sale.total_amount), 0).label('cash_total')
            )
            .filter(Sale.pos_session_id.in_(session_ids))
            .filter(func.lower(func.coalesce(Sale.payment_method, '')) == 'cash')
            .group_by(Sale.pos_session_id)
            .all()
        )

        totals: Dict[str, Decimal] = {sid: Decimal('0') for sid in session_ids}
        for session_id, total in rows:
            totals[session_id] = self._quantize(Decimal(total))
        return totals

    def _cash_sales_for_session(self, session_id: str) -> Decimal:
        result = (
            self.db.query(func.coalesce(func.sum(Sale.total_amount), 0))
            .filter(Sale.pos_session_id == session_id)
            .filter(func.lower(func.coalesce(Sale.payment_method, '')) == 'cash')
            .scalar()
        )
        return self._quantize(Decimal(result or 0))

    def _reconciliations_by_session(self, session_ids: List[str]) -> Dict[str, PosShiftReconciliation]:
        if not session_ids:
            return {}

        records = (
            self.db.query(PosShiftReconciliation)
            .filter(PosShiftReconciliation.session_id.in_(session_ids))
            .all()
        )
        return {record.session_id: record for record in records}

    def _serialize_session(
        self,
        *,
        session: PosSession,
        record: Optional[PosShiftReconciliation],
        cash_sales: Decimal
    ) -> Dict[str, Any]:
        float_given = self._quantize(record.float_given if record else self._ensure_decimal(session.float_amount))
        cash_collected = self._quantize(record.cash_collected if record else self._ensure_decimal(session.cash_submitted))
        expected_cash = self._quantize(record.expected_cash if record else float_given + cash_sales)
        variance = self._quantize(record.variance if record else cash_collected - expected_cash)

        status = 'balanced'
        if session.status == 'open':
            status = 'open'
        elif record is None and session.status != 'open':
            status = 'pending'
        elif variance != Decimal('0'):
            status = 'variance' if abs(variance) >= Decimal('0.01') else 'balanced'

        user = session.user
        branch = session.branch

        return {
            'session_id': session.id,
            'cashier_id': session.user_id,
            'cashier_name': getattr(user, 'full_name', None) or getattr(user, 'username', None) or getattr(user, 'email', ''),
            'branch_id': session.branch_id,
            'branch_name': getattr(branch, 'name', None),
            'till_id': session.till_id,
            'opened_at': session.opened_at.isoformat() if session.opened_at else None,
            'closed_at': session.closed_at.isoformat() if session.closed_at else None,
            'float_given': float(float_given),
            'cash_sales': float(self._quantize(record.cash_sales if record else cash_sales)),
            'expected_cash': float(expected_cash),
            'cash_collected': float(cash_collected),
            'variance': float(variance),
            'status': status,
            'notes': record.notes if record else session.notes,
            'reconciled_at': record.verified_at.isoformat() if record and record.verified_at else (record.updated_at.isoformat() if record and record.updated_at else None),
            'verified_by': record.verified_by if record else session.verified_by,
            'last_updated': record.updated_at.isoformat() if record else (session.updated_at.isoformat() if session.updated_at else None)
        }

    def _quantize(self, value: Decimal) -> Decimal:
        return self._ensure_decimal(value).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    def _ensure_decimal(self, value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        if value is None:
            return Decimal('0')
        return Decimal(str(value))
