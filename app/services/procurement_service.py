from typing import List, Dict, Tuple
from decimal import Decimal
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text

from app.models.procurement import (
    ProcurementRequisition, ProcurementRequisitionItem,
    RFQ, RFQInvite, SupplierQuote, SupplierQuoteItem,
    ProcurementAward, SupplierEvaluationTicket, SupplierEvaluationMilestone, SupplierPerformance
)
from app.models.purchases import Supplier, PurchaseOrder, PurchaseOrderItem


class ProcurementService:
    """Business logic for procurement workflow: requisition -> RFQ -> quotes -> evaluation -> award -> PO"""

    def __init__(self, db: Session):
        self.db = db

    # Requisitions
    def create_requisition(self, req_data: Dict, items: List[Dict]) -> ProcurementRequisition:
        # Ensure DB column exists for optional fields added after initial table creation
        try:
            inspector = inspect(self.db.bind)
            columns = {col['name'] for col in inspector.get_columns('procurement_requisitions')}
            if 'supplier_id' not in columns:
                # Attempt to add column on the fly to avoid 500s until migrations are formalized
                self.db.execute(text("ALTER TABLE procurement_requisitions ADD COLUMN supplier_id VARCHAR"))
                # Optional: add FK constraint if suppliers table exists
                try:
                    self.db.execute(text("ALTER TABLE procurement_requisitions ADD CONSTRAINT fk_proc_req_supplier FOREIGN KEY (supplier_id) REFERENCES suppliers(id)"))
                except Exception:
                    # Constraint is optional; ignore if it fails due to perms or duplicate
                    pass
                self.db.commit()
        except Exception:
            # If inspection/DDL fails, proceed; we'll still attempt insert (or strip field below)
            pass

        # If column still doesn't exist, drop supplier_id from payload to prevent DB error
        try:
            inspector = inspect(self.db.bind)
            columns = {col['name'] for col in inspector.get_columns('procurement_requisitions')}
            if 'supplier_id' not in columns and 'supplier_id' in req_data:
                req_data = dict(req_data)
                req_data.pop('supplier_id', None)
        except Exception:
            # On inspection failure, leave data as-is
            pass

        requisition = ProcurementRequisition(**req_data)
        self.db.add(requisition)
        self.db.flush()

        for item in items:
            total_estimated = None
            if item.get('estimated_unit_cost') and item.get('quantity'):
                total_estimated = Decimal(str(item['estimated_unit_cost'])) * Decimal(str(item['quantity']))
            req_item = ProcurementRequisitionItem(
                requisition_id=requisition.id,
                product_id=item.get('product_id'),
                description=item['description'],
                quantity=item['quantity'],
                unit_of_measure=item.get('unit_of_measure'),
                estimated_unit_cost=item.get('estimated_unit_cost'),
                total_estimated_cost=total_estimated
            )
            self.db.add(req_item)

        self.db.commit()
        self.db.refresh(requisition)
        return requisition

    # RFQs
    def create_rfq(self, rfq_data: Dict, invites: List[Dict]) -> RFQ:
        rfq = RFQ(**rfq_data)
        self.db.add(rfq)
        self.db.flush()

        for inv in invites:
            invite = RFQInvite(
                rfq_id=rfq.id,
                supplier_id=inv['supplier_id'],
                invited=inv.get('invited', True),
                notes=inv.get('notes')
            )
            self.db.add(invite)

        self.db.commit()
        self.db.refresh(rfq)
        return rfq

    def submit_supplier_quote(self, quote_data: Dict, items: List[Dict]) -> SupplierQuote:
        quote = SupplierQuote(**quote_data)
        self.db.add(quote)
        self.db.flush()

        total_amount = Decimal('0')
        total_vat = Decimal('0')
        for it in items:
            qty = Decimal(str(it['quantity']))
            unit = Decimal(str(it.get('unit_cost', 0)))
            line_total = qty * unit
            vat_rate = Decimal(str(it.get('vat_rate', 0)))
            vat_amt = line_total * (vat_rate / 100)
            qi = SupplierQuoteItem(
                quote_id=quote.id,
                product_id=it.get('product_id'),
                description=it['description'],
                quantity=qty,
                unit_cost=unit,
                total_cost=line_total,
                vat_rate=vat_rate,
                vat_amount=vat_amt
            )
            self.db.add(qi)
            total_amount += line_total
            total_vat += vat_amt

        quote.total_amount = total_amount
        quote.total_vat_amount = total_vat

        self.db.commit()
        self.db.refresh(quote)
        return quote

    # Evaluation & Award
    def award_quote(self, award_data: Dict) -> Tuple[ProcurementAward, PurchaseOrder]:
        # Ensure DB column exists for new linkage field purchase_order_id
        try:
            inspector = inspect(self.db.bind)
            columns = {col['name'] for col in inspector.get_columns('procurement_awards')}
            if 'purchase_order_id' not in columns:
                self.db.execute(text("ALTER TABLE procurement_awards ADD COLUMN purchase_order_id VARCHAR"))
                try:
                    self.db.execute(text("ALTER TABLE procurement_awards ADD CONSTRAINT fk_proc_award_po FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id)"))
                except Exception:
                    pass
                self.db.commit()
        except Exception:
            pass

        award = ProcurementAward(**award_data)
        self.db.add(award)
        self.db.flush()

        # Create Purchase Order from awarded quote
        quote = self.db.query(SupplierQuote).filter(SupplierQuote.id == award.quote_id).first()
        if not quote:
            raise ValueError("Quote not found for award")

        po = PurchaseOrder(
            supplier_id=quote.supplier_id,
            date=award.award_date or date.today(),
            status='approved',
            notes=f"PO from award {award.award_number}",
            branch_id=award.branch_id
        )
        self.db.add(po)
        self.db.flush()

        total_amount = Decimal('0')
        total_vat = Decimal('0')
        for qi in quote.items:
            poi = PurchaseOrderItem(
                purchase_order_id=po.id,
                product_id=qi.product_id,
                quantity=qi.quantity,
                unit_cost=qi.unit_cost,
                total_cost=qi.total_cost,
                vat_rate=qi.vat_rate,
                vat_amount=qi.vat_amount,
                description=qi.description
            )
            self.db.add(poi)
            total_amount += qi.total_cost or Decimal('0')
            total_vat += qi.vat_amount or Decimal('0')

        po.total_amount = total_amount
        po.total_vat_amount = total_vat
        # Link award to created PO
        award.status = 'converted_to_po'
        award.purchase_order_id = po.id

        self.db.commit()
        self.db.refresh(award)
        self.db.refresh(po)

        # Auto-create evaluation ticket with default milestones for this PO
        try:
            self._create_supplier_evaluation_ticket_for_po(po)
        except Exception as e:
            # Don't fail award flow if evaluation ticket creation fails
            print(f"Warning: Failed to create evaluation ticket for PO {po.id}: {e}")

        return award, po

    # Supplier performance evaluation
    def evaluate_supplier_performance(self, supplier_id: str, period_start: date, period_end: date, persist: bool = True) -> Dict:
        """Compute supplier performance metrics from POs and Quotes within a period.

        Heuristics (initial version):
        - on_time_delivery_score: percent of POs with expected_delivery_date and delivered within period where Purchase.received_at <= expected_delivery_date.
        - quality_score: inverse of return/issue rate (placeholder 80 if no defect tracking).
        - responsiveness_score: percent of RFQ invites responded with quote within 7 days.
        - compliance_score: percent of RFQs responded that meet status 'submitted' and have non-null required fields; and POs approved.
        - overall_score: weighted average.
        """
        # Defaults to avoid division by zero
        def pct(n: int, d: int) -> int:
            if not d:
                return 100
            return int(round((n / d) * 100))

        # On-time delivery: map POs -> match Purchases by supplier_id and received_at
        total_pos = 0
        on_time_pos = 0
        pos = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.supplier_id == supplier_id,
            PurchaseOrder.date >= period_start,
            PurchaseOrder.date <= period_end
        ).all()
        total_pos = len(pos)

        # For each PO, consider received purchases within the period (if any)
        from app.models.purchases import Purchase
        for po in pos:
            # A purchase is considered linked if same supplier and received_at exists in period
            purchases = self.db.query(Purchase).filter(
                Purchase.supplier_id == supplier_id,
                Purchase.received_at != None,
                Purchase.received_at >= period_start,
                Purchase.received_at <= period_end
            ).all()
            # If expected_delivery_date exists, check if any received_on <= expected_delivery_date
            if po.expected_delivery_date and purchases:
                if any(p.received_at and p.received_at <= po.expected_delivery_date for p in purchases):
                    on_time_pos += 1

        on_time_delivery_score = pct(on_time_pos, total_pos)

        # Responsiveness: RFQ invites vs quotes within 7 days of invite
        invites = self.db.query(RFQInvite).join(RFQ, RFQInvite.rfq_id == RFQ.id).filter(
            RFQInvite.supplier_id == supplier_id,
            RFQ.issue_date != None,
            RFQ.issue_date >= period_start,
            RFQ.issue_date <= period_end
        ).all()
        total_invites = len(invites)
        quotes = self.db.query(SupplierQuote).join(RFQ, SupplierQuote.rfq_id == RFQ.id).filter(
            SupplierQuote.supplier_id == supplier_id,
            RFQ.issue_date != None,
            RFQ.issue_date >= period_start,
            RFQ.issue_date <= period_end
        ).all()

        responded_within_7 = 0
        # Build RFQ issue_date map
        rfq_issue_date = {inv.rfq_id: inv.rfq.issue_date for inv in invites if getattr(inv, 'rfq', None)}
        for q in quotes:
            issued = rfq_issue_date.get(q.rfq_id, getattr(q.rfq, 'issue_date', None))
            if issued and q.quote_date:
                days = (q.quote_date - issued).days
                if days <= 7:
                    responded_within_7 += 1
        responsiveness_score = pct(responded_within_7, total_invites)

        # Compliance: proportion of quotes that are complete (have at least 1 item and totals) and POs approved
        complete_quotes = 0
        for q in quotes:
            if q.items and q.total_amount is not None:
                complete_quotes += 1
        approved_pos = sum(1 for po in pos if po.status and po.status.lower() in {"approved", "closed", "completed"})
        # average of quote completeness and PO approvals
        compliance_score = int(round((pct(complete_quotes, len(quotes)) + pct(approved_pos, total_pos)) / 2))

        # Quality: placeholder until returns/defects tracking exists
        quality_score = 80 if (total_pos or quotes) else 100

        # Overall weighted average
        overall_score = int(round(
            0.4 * on_time_delivery_score +
            0.2 * quality_score +
            0.25 * responsiveness_score +
            0.15 * compliance_score
        ))

        result = {
            "supplier_id": supplier_id,
            "period_start": period_start,
            "period_end": period_end,
            "on_time_delivery_score": on_time_delivery_score,
            "quality_score": quality_score,
            "responsiveness_score": responsiveness_score,
            "compliance_score": compliance_score,
            "overall_score": overall_score,
            "details": {
                "total_purchase_orders": Decimal(total_pos),
                "on_time_pos": Decimal(on_time_pos),
                "total_invites": Decimal(total_invites),
                "responded_within_7": Decimal(responded_within_7),
            },
        }

        if persist:
            perf = SupplierPerformance(
                supplier_id=supplier_id,
                period_start=period_start,
                period_end=period_end,
                on_time_delivery_score=on_time_delivery_score,
                quality_score=quality_score,
                responsiveness_score=responsiveness_score,
                compliance_score=compliance_score,
                overall_score=overall_score,
            )
            self.db.add(perf)
            self.db.commit()

        return result

    # Internal helpers
    def _create_supplier_evaluation_ticket_for_po(self, po: PurchaseOrder) -> SupplierEvaluationTicket:
        from datetime import date as dt_date, timedelta
        ticket = SupplierEvaluationTicket(
            supplier_id=po.supplier_id,
            purchase_order_id=po.id,
            status='open',
            opened_at=po.date or dt_date.today(),
            branch_id=po.branch_id,
            notes=f"Auto-created evaluation for PO {po.po_number or po.id}"
        )
        self.db.add(ticket)
        self.db.flush()

        # Default milestones (customizable later via endpoints)
        default_milestones = [
            ("RFQ Response Quality Review", 1),
            ("PO Acknowledgement", 2),
            ("On-Time Delivery Check", 3),
            ("Goods Quality Inspection", 4),
            ("Documentation & Compliance", 5),
            ("Post-Delivery Support", 6)
        ]
        base_due = po.expected_delivery_date or (po.date or dt_date.today())
        for name, seq in default_milestones:
            ms = SupplierEvaluationMilestone(
                ticket_id=ticket.id,
                name=name,
                sequence=seq,
                status='pending',
                due_date=base_due,
            )
            self.db.add(ms)

        self.db.commit()
        self.db.refresh(ticket)
        return ticket


