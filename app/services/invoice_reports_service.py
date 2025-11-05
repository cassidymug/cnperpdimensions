"""Invoice Reports Service
Generates metrics, aging buckets, and performance insights for invoices."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.sales import Invoice


class InvoiceReportsService:
    """Service class that aggregates invoice analytics for reporting."""

    AGING_BUCKETS: List[tuple] = [
        ("Current", 0, 0),
        ("1-30", 1, 30),
        ("31-60", 31, 60),
        ("61-90", 61, 90),
        ("90+", 91, None),
    ]

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        if value is None:
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal("0")

    def get_invoice_metrics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_zero: bool = False,
        top_n: int = 10,
    ) -> Dict[str, Any]:
        today = date.today()
        if end_date is None:
            end_date = today
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        invoices = (
            self.db.query(Invoice)
            .filter(Invoice.date >= start_date, Invoice.date <= end_date)
            .all()
        )

        total_invoices = 0
        total_amount = Decimal("0")
        total_paid = Decimal("0")
        outstanding_total = Decimal("0")
        overdue_invoices = 0
        overdue_amount = Decimal("0")
        aging_totals: Dict[str, Decimal] = {bucket[0]: Decimal("0") for bucket in self.AGING_BUCKETS}

        customer_totals: Dict[str, Dict[str, Decimal]] = {}
        days_to_pay: List[int] = []
        on_time_payments = 0
        late_payments = 0

        for inv in invoices:
            invoice_total = self._to_decimal(inv.total_amount or inv.total)
            amount_paid = self._to_decimal(inv.amount_paid)
            outstanding = invoice_total - amount_paid
            if outstanding < 0:
                outstanding = Decimal("0")

            if not include_zero and invoice_total == 0 and outstanding == 0:
                continue

            total_invoices += 1
            total_amount += invoice_total
            total_paid += amount_paid
            outstanding_total += outstanding

            due_date = inv.due_date or inv.date or end_date
            days_overdue = 0
            if due_date:
                days_overdue = (today - due_date).days

            if outstanding > 0:
                bucket_label = self._determine_bucket(days_overdue)
                aging_totals[bucket_label] += outstanding
                if days_overdue > 0:
                    overdue_invoices += 1
                    overdue_amount += outstanding

            if inv.paid_at and inv.date:
                paid_at = inv.paid_at.date() if isinstance(inv.paid_at, datetime) else inv.paid_at
                days = (paid_at - inv.date).days
                if days >= 0:
                    days_to_pay.append(days)
                if due_date:
                    if paid_at <= due_date:
                        on_time_payments += 1
                    else:
                        late_payments += 1

            customer_name = self._resolve_customer_name(inv)
            bucket = customer_totals.setdefault(
                customer_name,
                {"invoiced": Decimal("0"), "paid": Decimal("0"), "outstanding": Decimal("0")},
            )
            bucket["invoiced"] += invoice_total
            bucket["paid"] += amount_paid
            bucket["outstanding"] += outstanding

        collection_rate = float(total_paid / total_amount) if total_amount > 0 else 0.0
        avg_days_to_pay = sum(days_to_pay) / len(days_to_pay) if days_to_pay else 0.0

        aging_buckets = self._build_aging_response(aging_totals, outstanding_total)
        top_customers = self._build_top_customers(customer_totals, total_amount, top_n)
        invoices_sample = self._build_sample(invoices, include_zero, start_date, end_date)

        metrics = {
            "total_invoices": total_invoices,
            "total_amount": float(total_amount),
            "total_paid": float(total_paid),
            "outstanding_total": float(outstanding_total),
            "collection_rate": collection_rate,
            "overdue_invoices": overdue_invoices,
            "overdue_amount": float(overdue_amount),
            "avg_days_to_pay": round(avg_days_to_pay, 2),
        }

        payment_performance = {
            "invoices_paid": len(days_to_pay),
            "avg_days_to_pay": round(avg_days_to_pay, 2),
            "on_time_payments": on_time_payments,
            "late_payments": late_payments,
            "collection_rate_pct": round(collection_rate * 100, 2),
        }

        return {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "metrics": metrics,
            "aging": {"buckets": aging_buckets},
            "payment_performance": payment_performance,
            "top_customers": top_customers,
            "invoices_sample": invoices_sample,
        }

    def export_pdf(self, data: Dict[str, Any]) -> BytesIO:
        from app.services.report_export_utils import export_key_value_pdf

        flattened = {
            "Metrics": data.get("metrics", {}),
            "Aging": {bucket["bucket"]: bucket["amount"] for bucket in data.get("aging", {}).get("buckets", [])},
            "Performance": data.get("payment_performance", {}),
        }
        period = data.get("period", {})
        return export_key_value_pdf(
            "Invoice Metrics Report",
            {"start": period.get("start", "N/A"), "end": period.get("end", "N/A")},
            flattened,
        )

    def export_xlsx(self, data: Dict[str, Any]) -> BytesIO:
        try:
            import pandas as pd
        except ModuleNotFoundError as exc:  # pragma: no cover - export path only
            raise RuntimeError("Pandas is required for XLSX export") from exc

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            metrics_df = pd.DataFrame([data.get("metrics", {})])
            metrics_df.to_excel(writer, sheet_name="Metrics", index=False)

            aging_df = pd.DataFrame(data.get("aging", {}).get("buckets", []))
            if not aging_df.empty:
                aging_df.to_excel(writer, sheet_name="Aging", index=False)

            top_customers_df = pd.DataFrame(data.get("top_customers", []))
            if not top_customers_df.empty:
                top_customers_df.to_excel(writer, sheet_name="Top Customers", index=False)

            sample_df = pd.DataFrame(data.get("invoices_sample", []))
            if not sample_df.empty:
                sample_df.to_excel(writer, sheet_name="Sample Invoices", index=False)

        buffer.seek(0)
        return buffer

    def _determine_bucket(self, days_overdue: int) -> str:
        for label, start, end in self.AGING_BUCKETS:
            if end is None:
                if days_overdue >= start:
                    return label
            elif days_overdue >= start and days_overdue <= end:
                return label
        return "Current"

    def _build_aging_response(
        self, aging_totals: Dict[str, Decimal], outstanding_total: Decimal
    ) -> List[Dict[str, Any]]:
        buckets: List[Dict[str, Any]] = []
        total_outstanding = outstanding_total if outstanding_total > 0 else Decimal("1")
        for label, _, _ in self.AGING_BUCKETS:
            amount = aging_totals.get(label, Decimal("0"))
            percent = float(amount / total_outstanding) if total_outstanding > 0 else 0.0
            buckets.append({
                "bucket": label,
                "amount": float(amount),
                "percent": percent,
            })
        return buckets

    def _build_top_customers(
        self,
        customer_totals: Dict[str, Dict[str, Decimal]],
        total_amount: Decimal,
        top_n: int,
    ) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        divisor = total_amount if total_amount > 0 else Decimal("1")

        for name, balances in customer_totals.items():
            invoiced = balances["invoiced"]
            paid = balances["paid"]
            outstanding = balances["outstanding"]
            entries.append({
                "name": name,
                "invoiced": float(invoiced),
                "paid": float(paid),
                "outstanding": float(outstanding),
                "percent_total": float(invoiced / divisor),
            })

        entries.sort(key=lambda x: x["invoiced"], reverse=True)
        return entries[: top_n if top_n > 0 else 10]

    def _build_sample(
        self,
        invoices: List[Invoice],
        include_zero: bool,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        filtered: List[Invoice] = []
        for inv in invoices:
            amount = self._to_decimal(inv.total_amount or inv.total)
            if not include_zero and amount == 0:
                continue
            filtered.append(inv)

        filtered.sort(key=lambda inv: inv.date or start_date, reverse=True)
        sample = filtered[:10]
        return [
            {
                "id": inv.id,
                "invoice_number": getattr(inv, "invoice_number", None),
                "date": inv.date.isoformat() if inv.date else None,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "customer": self._resolve_customer_name(inv),
                "total_amount": float(self._to_decimal(inv.total_amount or inv.total)),
                "amount_paid": float(self._to_decimal(inv.amount_paid)),
            }
            for inv in sample
        ]

    @staticmethod
    def _resolve_customer_name(inv: Invoice) -> str:
        if hasattr(inv, "customer") and inv.customer:
            name = getattr(inv.customer, "name", None) or getattr(inv.customer, "company_name", None)
            if name:
                return name
        if getattr(inv, "customer_id", None):
            return str(inv.customer_id)
        return "Unknown Customer"
