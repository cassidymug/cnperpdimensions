"""
COGS Reports Service
Comprehensive Cost of Goods Sold analytics and reporting service
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.models.inventory import COGSEntry
from app.models.sales import Sale
from app.models.accounting import JournalEntry, AccountingCode
from app.models.inventory import Product
from app.models.accounting import JournalEntry
from calendar import monthrange
import calendar

class COGSReportsService:
    """Service for generating comprehensive COGS reports"""
    
    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        """Convert arbitrary numeric input to Decimal safely."""
        if value is None:
            return Decimal(0)
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal(0)

    @classmethod
    def _entry_total_cost_decimal(cls, entry: Any) -> Decimal:
        """Return the total cost represented by a COGS entry."""
        if entry is None:
            return Decimal(0)

        total = getattr(entry, "total_cost", None)
        if total is not None:
            return cls._to_decimal(total)

        unit_cost = getattr(entry, "unit_cost", None)
        quantity = getattr(entry, "quantity", None)
        if unit_cost is not None and quantity is not None:
            return cls._to_decimal(unit_cost) * cls._to_decimal(quantity)

        cost = getattr(entry, "cost", None)
        if cost is not None:
            qty = quantity if quantity is not None else 1
            return cls._to_decimal(cost) * cls._to_decimal(qty)

        return Decimal(0)
    
    def generate_monthly_cogs_report(
        self,
        year: int,
        month: int,
        product_id: Optional[str] = None,
        category_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate monthly COGS report"""
        
        # Get start and end dates for the month
        start_date = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)
        
        return self._generate_period_cogs_report(
            start_date=start_date,
            end_date=end_date,
            period_type="monthly",
            product_id=product_id,
            category_id=category_id
        )
    
    def generate_quarterly_cogs_report(
        self,
        year: int,
        quarter: int,
        product_id: Optional[str] = None,
        category_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate quarterly COGS report"""
        
        # Calculate quarter start and end dates
        quarter_start_month = (quarter - 1) * 3 + 1
        start_date = date(year, quarter_start_month, 1)
        
        quarter_end_month = quarter * 3
        _, last_day = monthrange(year, quarter_end_month)
        end_date = date(year, quarter_end_month, last_day)
        
        return self._generate_period_cogs_report(
            start_date=start_date,
            end_date=end_date,
            period_type="quarterly",
            product_id=product_id,
            category_id=category_id
        )
    
    def generate_annual_cogs_report(
        self,
        year: int,
        product_id: Optional[str] = None,
        category_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate annual COGS report"""
        
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        
        return self._generate_period_cogs_report(
            start_date=start_date,
            end_date=end_date,
            period_type="annual",
            product_id=product_id,
            category_id=category_id
        )
    
    def _generate_period_cogs_report(
        self,
        start_date: date,
        end_date: date,
        period_type: str,
        product_id: Optional[str] = None,
        category_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate COGS report for a specific period"""
        
        # Get COGS entries for the period
        cogs_query = self.db.query(COGSEntry).filter(
            COGSEntry.date >= start_date,
            COGSEntry.date <= end_date
        )
        
        if product_id:
            cogs_query = cogs_query.filter(COGSEntry.product_id == product_id)
        
        cogs_entries = cogs_query.all()
        
        # Get sales data for the period to calculate COGS from sales
        sales_cogs = self._calculate_sales_cogs(start_date, end_date, product_id, category_id)
        
        # Calculate total COGS
        direct_cogs_total = sum(
            (self._entry_total_cost_decimal(entry) for entry in cogs_entries),
            Decimal(0)
        )
        journal_cogs_total, journal_entry_count = self._calculate_journal_cogs(
            start_date,
            end_date,
            product_id=product_id,
            category_id=category_id
        )
        direct_cogs_total += journal_cogs_total
        sales_cogs_total = self._to_decimal(sales_cogs["total_cogs"])
        total_cogs = direct_cogs_total + sales_cogs_total
        
        # Get product breakdown
        product_breakdown = self._get_product_cogs_breakdown(cogs_entries, sales_cogs["by_product"])
        
        # Get category breakdown if applicable
        category_breakdown = self._get_category_cogs_breakdown(product_breakdown)
        
        # Calculate trends and comparisons
        previous_period_data = self._get_previous_period_comparison(
            start_date, end_date, period_type, product_id, category_id
        )
        
        # Get monthly breakdown for quarterly/annual reports
        monthly_breakdown = []
        if period_type in ["quarterly", "annual"]:
            monthly_breakdown = self._get_monthly_cogs_breakdown(start_date, end_date, product_id, category_id)
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "type": period_type,
                "description": self._get_period_description(start_date, end_date, period_type)
            },
            "summary": {
                "total_cogs": float(total_cogs),
                "direct_cogs": float(direct_cogs_total),
                "sales_cogs": float(sales_cogs_total),
                "journal_cogs": float(journal_cogs_total),
                "total_entries": len(cogs_entries) + sales_cogs["total_transactions"] + journal_entry_count,
                "average_cogs_per_entry": float(
                    total_cogs / Decimal(len(cogs_entries) + sales_cogs["total_transactions"] + journal_entry_count)
                    if (len(cogs_entries) + sales_cogs["total_transactions"] + journal_entry_count) > 0
                    else Decimal(0)
                )
            },
            "product_breakdown": product_breakdown,
            "category_breakdown": category_breakdown,
            "monthly_breakdown": monthly_breakdown,
            "comparison": previous_period_data,
            "generated_at": datetime.now().isoformat()
        }
    
    def _calculate_sales_cogs(
        self,
        start_date: date,
        end_date: date,
        product_id: Optional[str] = None,
        category_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate COGS from sales transactions"""
        
        # Get sales within the period
        sales_query = self.db.query(Sale).filter(
            Sale.date >= start_date,
            Sale.date <= end_date
        )
        
        sales = sales_query.all()
        
        total_cogs = Decimal(0)
        total_transactions = 0
        by_product = {}
        
        for sale in sales:
            items = []
            if hasattr(sale, 'items') and sale.items:
                items = sale.items
            elif hasattr(sale, 'sale_items') and sale.sale_items:
                items = sale.sale_items

            for item in items:
                if product_id and str(item.product_id) != product_id:
                    continue

                quantity = self._to_decimal(getattr(item, "quantity", 0))
                unit_cost = self._to_decimal(getattr(item, "cost_price", 0))
                item_cogs = quantity * unit_cost
                total_cogs += item_cogs
                total_transactions += 1

                product_key = str(item.product_id)
                if product_key not in by_product:
                    by_product[product_key] = {
                        "product_id": item.product_id,
                        "total_cogs": Decimal(0),
                        "quantity_sold": Decimal(0),
                        "transactions": 0
                    }

                by_product[product_key]["total_cogs"] += item_cogs
                by_product[product_key]["quantity_sold"] += quantity
                by_product[product_key]["transactions"] += 1
        
        return {
            "total_cogs": total_cogs,
            "total_transactions": total_transactions,
            "by_product": by_product
        }

    def _calculate_journal_cogs(
        self,
        start_date: date,
        end_date: date,
        product_id: Optional[str] = None,
        category_id: Optional[str] = None
    ) -> Tuple[Decimal, int]:
        """Derive COGS totals from general-ledger journal entries."""

        # Journal entries are not linked to specific products, so respect product filters.
        if product_id:
            return Decimal(0), 0

        query = (
            self.db.query(
                JournalEntry.debit_amount,
                JournalEntry.credit_amount,
                AccountingCode.category,
                AccountingCode.name
            )
            .join(AccountingCode, JournalEntry.accounting_code_id == AccountingCode.id)
            .filter(
                JournalEntry.date >= start_date,
                JournalEntry.date <= end_date,
                func.lower(AccountingCode.account_type) == 'expense'
            )
        )

        # Limit to codes that clearly map to cost-of-goods buckets.
        cogs_criteria = or_(
            func.lower(AccountingCode.category).like('%cost of sales%'),
            func.lower(AccountingCode.category).like('%cost of goods%'),
            func.lower(AccountingCode.name).like('%cost of sales%'),
            func.lower(AccountingCode.name).like('%cost of goods%'),
            func.lower(AccountingCode.name).like('%cogs%')
        )
        query = query.filter(cogs_criteria)

        if category_id:
            query = query.filter(AccountingCode.category == category_id)

        totals = Decimal(0)
        entry_count = 0

        for debit_amount, credit_amount, _, _ in query.all():
            amount = self._to_decimal(debit_amount) - self._to_decimal(credit_amount)
            if amount == 0:
                continue
            totals += amount
            entry_count += 1

        return totals, entry_count
    
    def _get_product_cogs_breakdown(
        self,
        cogs_entries: List[COGSEntry],
        sales_by_product: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get COGS breakdown by product"""

        product_totals = {}
        
        # Process direct COGS entries
        for entry in cogs_entries:
            product_key = str(entry.product_id)
            if product_key not in product_totals:
                product_totals[product_key] = {
                    "product_id": entry.product_id,
                    "direct_cogs": Decimal(0),
                    "sales_cogs": Decimal(0),
                    "total_cogs": Decimal(0),
                    "quantity": Decimal(0),
                    "entries_count": 0
                }

            product_totals[product_key]["direct_cogs"] += self._entry_total_cost_decimal(entry)
            product_totals[product_key]["quantity"] += self._to_decimal(getattr(entry, "quantity", 0))
            product_totals[product_key]["entries_count"] += 1
        
        # Process sales COGS
        for product_key, sales_data in sales_by_product.items():
            if product_key not in product_totals:
                product_totals[product_key] = {
                    "product_id": sales_data["product_id"],
                    "direct_cogs": Decimal(0),
                    "sales_cogs": Decimal(0),
                    "total_cogs": Decimal(0),
                    "quantity": Decimal(0),
                    "entries_count": 0
                }
            
            product_totals[product_key]["sales_cogs"] += self._to_decimal(sales_data.get("total_cogs"))
            product_totals[product_key]["quantity"] += self._to_decimal(sales_data.get("quantity_sold"))
            product_totals[product_key]["entries_count"] += sales_data["transactions"]
        
        # Calculate totals and add product details
        breakdown = []
        for product_key, data in product_totals.items():
            data["total_cogs"] = data["direct_cogs"] + data["sales_cogs"]
            
            # Get product details
            product = self.db.query(Product).filter(Product.id == data["product_id"]).first()
            if product:
                data["product_name"] = product.name
                data["product_sku"] = product.sku
                data["category_id"] = getattr(product, 'category_id', None)
            
            # Convert to float for JSON serialization
            data["direct_cogs"] = float(data["direct_cogs"])
            data["sales_cogs"] = float(data["sales_cogs"])
            data["total_cogs"] = float(data["total_cogs"])
            data["quantity"] = float(data["quantity"])
            
            breakdown.append(data)
        
        # Sort by total COGS descending
        breakdown.sort(key=lambda x: x["total_cogs"], reverse=True)
        
        return breakdown
    
    def _get_category_cogs_breakdown(self, product_breakdown: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get COGS breakdown by category"""
        
        category_totals = {}
        
        for product_data in product_breakdown:
            category_id = product_data.get("category_id")
            if not category_id:
                category_id = "uncategorized"
            
            if category_id not in category_totals:
                category_totals[category_id] = {
                    "category_id": category_id,
                    "total_cogs": Decimal(0),
                    "direct_cogs": Decimal(0),
                    "sales_cogs": Decimal(0),
                    "product_count": 0,
                    "total_quantity": Decimal(0)
                }
            
            category_totals[category_id]["total_cogs"] += self._to_decimal(product_data["total_cogs"])
            category_totals[category_id]["direct_cogs"] += self._to_decimal(product_data["direct_cogs"])
            category_totals[category_id]["sales_cogs"] += self._to_decimal(product_data["sales_cogs"])
            category_totals[category_id]["product_count"] += 1
            category_totals[category_id]["total_quantity"] += self._to_decimal(product_data.get("quantity", 0))
        
        # Convert to list and sort
        breakdown = list(category_totals.values())
        for row in breakdown:
            row["total_cogs"] = float(row["total_cogs"])
            row["direct_cogs"] = float(row["direct_cogs"])
            row["sales_cogs"] = float(row["sales_cogs"])
            row["total_quantity"] = float(row["total_quantity"])
        
        breakdown.sort(key=lambda x: x["total_cogs"], reverse=True)
        
        return breakdown
    
    def _get_monthly_cogs_breakdown(
        self,
        start_date: date,
        end_date: date,
        product_id: Optional[str] = None,
        category_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get monthly COGS breakdown for quarterly/annual reports"""
        
        monthly_data = []
        current_date = start_date.replace(day=1)
        
        while current_date <= end_date:
            # Get last day of current month
            _, last_day = monthrange(current_date.year, current_date.month)
            month_end = date(current_date.year, current_date.month, last_day)
            
            # Don't go beyond the end date
            if month_end > end_date:
                month_end = end_date
            
            # Generate monthly report
            month_report = self._generate_period_cogs_report(
                start_date=current_date,
                end_date=month_end,
                period_type="monthly",
                product_id=product_id,
                category_id=category_id
            )
            
            monthly_data.append({
                "month": current_date.strftime("%Y-%m"),
                "month_name": calendar.month_name[current_date.month],
                "year": current_date.year,
                "total_cogs": month_report["summary"]["total_cogs"],
                "direct_cogs": month_report["summary"]["direct_cogs"],
                "sales_cogs": month_report["summary"]["sales_cogs"]
            })
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        return monthly_data
    
    def _get_previous_period_comparison(
        self,
        start_date: date,
        end_date: date,
        period_type: str,
        product_id: Optional[str] = None,
        category_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get comparison with previous period"""
        
        # Calculate previous period dates
        period_length = (end_date - start_date).days + 1
        prev_end_date = start_date - timedelta(days=1)
        prev_start_date = prev_end_date - timedelta(days=period_length - 1)
        
        # Calculate changes using direct totals to avoid recursive report generation
        current_total = self._calculate_period_total(start_date, end_date, product_id, category_id)
        previous_total = self._calculate_period_total(prev_start_date, prev_end_date, product_id, category_id)

        change_amount = current_total - previous_total
        change_percentage = (
            (change_amount / previous_total) * Decimal(100)
            if previous_total > 0
            else Decimal(0)
        )
        
        return {
            "previous_period": {
                "start_date": prev_start_date.isoformat(),
                "end_date": prev_end_date.isoformat(),
                "total_cogs": float(previous_total)
            },
            "change": {
                "amount": float(change_amount),
                "percentage": float(change_percentage),
                "trend": "increase" if change_amount > 0 else "decrease" if change_amount < 0 else "stable"
            }
        }
    
    def _calculate_period_total(
        self,
        start_date: date,
        end_date: date,
        product_id: Optional[str] = None,
        category_id: Optional[str] = None
    ) -> Decimal:
        """Calculate total COGS for a period"""
        
        # Direct COGS entries
        cogs_query = self.db.query(COGSEntry).filter(
            COGSEntry.date >= start_date,
            COGSEntry.date <= end_date
        )

        if product_id:
            cogs_query = cogs_query.filter(COGSEntry.product_id == product_id)

        direct_entries = cogs_query.all()
        direct_total = sum((self._entry_total_cost_decimal(entry) for entry in direct_entries), Decimal(0))

        # Sales COGS
        sales_cogs = self._calculate_sales_cogs(start_date, end_date, product_id, category_id)

        journal_total, _ = self._calculate_journal_cogs(
            start_date,
            end_date,
            product_id=product_id,
            category_id=category_id
        )

        return direct_total + self._to_decimal(sales_cogs["total_cogs"]) + journal_total
    
    def _get_period_description(self, start_date: date, end_date: date, period_type: str) -> str:
        """Get human-readable period description"""
        
        if period_type == "monthly":
            return f"{calendar.month_name[start_date.month]} {start_date.year}"
        elif period_type == "quarterly":
            quarter = ((start_date.month - 1) // 3) + 1
            return f"Q{quarter} {start_date.year}"
        elif period_type == "annual":
            return f"Year {start_date.year}"
        else:
            return f"{start_date.isoformat()} to {end_date.isoformat()}"
    
    def get_cogs_trend_analysis(
        self,
        start_date: date,
        end_date: date,
        period_type: str = "monthly",
        product_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get COGS trend analysis over time"""
        
        trends = []
        current_date = start_date
        
        while current_date <= end_date:
            if period_type == "monthly":
                # Monthly periods
                _, last_day = monthrange(current_date.year, current_date.month)
                period_end = date(current_date.year, current_date.month, last_day)
                next_date = date(current_date.year + (1 if current_date.month == 12 else 0), 
                               (current_date.month % 12) + 1, 1)
            elif period_type == "quarterly":
                # Quarterly periods
                quarter = ((current_date.month - 1) // 3) + 1
                quarter_start_month = (quarter - 1) * 3 + 1
                quarter_end_month = quarter * 3
                _, last_day = monthrange(current_date.year, quarter_end_month)
                period_end = date(current_date.year, quarter_end_month, last_day)
                next_date = date(current_date.year + (1 if quarter == 4 else 0), 
                               ((quarter % 4) * 3) + 1, 1)
            else:
                # Default to monthly
                _, last_day = monthrange(current_date.year, current_date.month)
                period_end = date(current_date.year, current_date.month, last_day)
                next_date = date(current_date.year + (1 if current_date.month == 12 else 0), 
                               (current_date.month % 12) + 1, 1)
            
            if period_end > end_date:
                period_end = end_date
            
            # Calculate COGS for this period
            period_total = self._calculate_period_total(current_date, period_end, product_id)
            
            trends.append({
                "period_start": current_date.isoformat(),
                "period_end": period_end.isoformat(),
                "period_label": self._get_period_description(current_date, period_end, period_type),
                "total_cogs": float(period_total)
            })
            
            current_date = next_date
            if current_date > end_date:
                break
        
        return {
            "trends": trends,
            "analysis": {
                "total_periods": len(trends),
                "average_cogs": sum(t["total_cogs"] for t in trends) / len(trends) if trends else 0,
                "highest_period": max(trends, key=lambda x: x["total_cogs"]) if trends else None,
                "lowest_period": min(trends, key=lambda x: x["total_cogs"]) if trends else None
            }
        }