"""
Sales Reports Service
Comprehensive sales analytics and reporting service
"""

from typing import Dict, List, Optional, Any
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, extract
from app.models.sales import Sale, Customer, Invoice
from app.models.inventory import Product

class SalesReportsService:
    """Service for generating comprehensive sales reports"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_sales_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        branch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive sales summary report"""
        
        # Set default date range (last 30 days)
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
            
        # Get sales data from Sales table (POS transactions)
        sales_query = self.db.query(Sale).filter(
            Sale.date >= start_date,
            Sale.date <= end_date + timedelta(days=1)  # Include end date
        )
        
        # Get invoice data from Invoices table
        invoices_query = self.db.query(Invoice).filter(
            Invoice.date >= start_date,
            Invoice.date <= end_date
        )
        
        if branch_id:
            # Add branch filter if needed (assuming sales have branch relationship)
            pass  # You may need to add branch filtering based on your schema
            
        sales = sales_query.all()
        invoices = invoices_query.all()
        
        # Calculate total sales metrics
        total_sales_amount = sum(sale.total_amount or 0 for sale in sales)
        total_sales_ex_vat = sum(sale.total_amount_ex_vat or 0 for sale in sales)
        total_sales_vat = sum(sale.total_vat_amount or 0 for sale in sales)
        total_sales_count = len(sales)
        
        # Calculate invoice metrics
        total_invoice_amount = sum(invoice.total_amount or 0 for invoice in invoices)
        total_invoice_count = len(invoices)
        
        # Combined totals
        combined_total_amount = total_sales_amount + total_invoice_amount
        combined_total_orders = total_sales_count + total_invoice_count
        
        # Calculate average order value
        average_order_value = (
            combined_total_amount / combined_total_orders 
            if combined_total_orders > 0 else 0
        )
        
        # Get top customers from sales
        top_customers = self._get_top_customers(sales, invoices, limit=5)
        
        # Get top products from sales
        top_products = self._get_top_products(sales, limit=5)
        
        # Get monthly trend
        monthly_trend = self._get_monthly_trend(start_date, end_date, branch_id)
        
        # Get daily breakdown
        daily_breakdown = self._get_daily_breakdown(sales, invoices)
        
        return {
            "total_sales": float(combined_total_amount),
            "total_orders": combined_total_orders,
            "average_order_value": float(average_order_value),
            "total_vat": float(total_sales_vat),
            "sales_breakdown": {
                "pos_sales": {
                    "amount": float(total_sales_amount),
                    "count": total_sales_count,
                    "vat": float(total_sales_vat)
                },
                "invoices": {
                    "amount": float(total_invoice_amount),
                    "count": total_invoice_count
                }
            },
            "top_customers": top_customers,
            "top_products": top_products,
            "monthly_trend": monthly_trend,
            "daily_breakdown": daily_breakdown,
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat()
        }
    
    def _get_top_customers(self, sales: List[Sale], invoices: List[Invoice], limit: int = 5) -> List[Dict]:
        """Get top customers by total spending"""
        customer_totals = {}
        
        # Process POS sales
        for sale in sales:
            # Use related Customer name since Sale has no customer_name attribute
            customer_name = sale.customer.name if sale.customer and sale.customer.name else "Walk-in Customer"
            if customer_name not in customer_totals:
                customer_totals[customer_name] = {"total_spent": 0, "orders": 0}
            customer_totals[customer_name]["total_spent"] += float(sale.total_amount or 0)
            customer_totals[customer_name]["orders"] += 1
        
        # Process invoices
        for invoice in invoices:
            # Use related Customer name since Invoice has no customer_name attribute
            customer_name = invoice.customer.name if invoice.customer and invoice.customer.name else "Unknown Customer"
            if customer_name not in customer_totals:
                customer_totals[customer_name] = {"total_spent": 0, "orders": 0}
            customer_totals[customer_name]["total_spent"] += float(invoice.total_amount or 0)
            customer_totals[customer_name]["orders"] += 1
        
        # Sort by total spent and return top customers
        top_customers = [
            {"name": name, **data}
            for name, data in sorted(
                customer_totals.items(), 
                key=lambda x: x[1]["total_spent"], 
                reverse=True
            )[:limit]
        ]
        
        return top_customers
    
    def _get_top_products(self, sales: List[Sale], limit: int = 5) -> List[Dict]:
        """Get top-selling products from sales data"""
        product_totals = {}
        
        for sale in sales:
            if hasattr(sale, 'items') and sale.items:
                for item in sale.items:
                    product_name = item.get('product_name', 'Unknown Product')
                    if product_name not in product_totals:
                        product_totals[product_name] = {"sales": 0, "quantity": 0}
                    
                    product_totals[product_name]["sales"] += float(item.get('total_amount', 0))
                    product_totals[product_name]["quantity"] += int(item.get('quantity', 0))
        
        # Sort by sales amount and return top products
        top_products = [
            {"name": name, **data}
            for name, data in sorted(
                product_totals.items(),
                key=lambda x: x[1]["sales"],
                reverse=True
            )[:limit]
        ]
        
        return top_products
    
    def _get_monthly_trend(self, start_date: date, end_date: date, branch_id: Optional[str] = None) -> List[Dict]:
        """Get monthly sales trend data"""
        # Get the last 6 months of data
        end_month = end_date.replace(day=1)
        start_month = end_month - timedelta(days=180)  # Approximately 6 months
        
        monthly_data = []
        current_month = start_month
        
        while current_month <= end_month:
            next_month = (current_month + timedelta(days=32)).replace(day=1)
            
            # Get sales for this month
            month_sales = self.db.query(Sale).filter(
                Sale.date >= current_month,
                Sale.date < next_month
            ).all()
            
            # Get invoices for this month
            month_invoices = self.db.query(Invoice).filter(
                Invoice.date >= current_month,
                Invoice.date < next_month
            ).all()
            
            total_amount = (
                sum(sale.total_amount or 0 for sale in month_sales) +
                sum(invoice.total_amount or 0 for invoice in month_invoices)
            )
            
            monthly_data.append({
                "month": current_month.strftime("%b %Y"),
                "sales": float(total_amount)
            })
            
            current_month = next_month
        
        return monthly_data
    
    def _get_daily_breakdown(self, sales: List[Sale], invoices: List[Invoice]) -> List[Dict]:
        """Get daily sales breakdown"""
        daily_totals = {}
        
        # Process sales
        for sale in sales:
            if sale.date:
                day_key = sale.date.date().isoformat()
                if day_key not in daily_totals:
                    daily_totals[day_key] = {"sales": 0, "orders": 0}
                daily_totals[day_key]["sales"] += float(sale.total_amount or 0)
                daily_totals[day_key]["orders"] += 1
        
        # Process invoices
        for invoice in invoices:
            if invoice.date:
                day_key = invoice.date.isoformat()
                if day_key not in daily_totals:
                    daily_totals[day_key] = {"sales": 0, "orders": 0}
                daily_totals[day_key]["sales"] += float(invoice.total_amount or 0)
                daily_totals[day_key]["orders"] += 1
        
        # Convert to list and sort by date
        daily_breakdown = [
            {"date": day, **data}
            for day, data in sorted(daily_totals.items())
        ]
        
        return daily_breakdown
    
    def get_customer_analysis(self, branch_id: Optional[str] = None) -> Dict[str, Any]:
        """Get customer analysis report"""
        
        # Get all customers with their transaction counts and amounts
        customers = self.db.query(Customer).all()
        
        customer_analysis = []
        for customer in customers:
            # Get customer's sales
            customer_sales = self.db.query(Sale).filter(
                Sale.customer_id == customer.id
            ).all()
            
            # Get customer's invoices  
            customer_invoices = self.db.query(Invoice).filter(
                Invoice.customer_id == customer.id
            ).all()
            
            total_spent = (
                sum(sale.total_amount or 0 for sale in customer_sales) +
                sum(invoice.total_amount or 0 for invoice in customer_invoices)
            )
            
            total_orders = len(customer_sales) + len(customer_invoices)
            
            if total_orders > 0:  # Only include customers with transactions
                # Get all dates and normalize them to datetime for comparison
                all_dates = []
                for sale in customer_sales:
                    if sale.date:
                        # Convert date to datetime if needed
                        if isinstance(sale.date, date) and not isinstance(sale.date, datetime):
                            all_dates.append(datetime.combine(sale.date, datetime.min.time()))
                        else:
                            all_dates.append(sale.date)
                
                for invoice in customer_invoices:
                    if invoice.date:
                        # Convert date to datetime if needed
                        if isinstance(invoice.date, date) and not isinstance(invoice.date, datetime):
                            all_dates.append(datetime.combine(invoice.date, datetime.min.time()))
                        else:
                            all_dates.append(invoice.date)
                
                last_purchase = max(all_dates) if all_dates else None
                # Convert back to date for JSON serialization
                if last_purchase:
                    last_purchase = last_purchase.date() if isinstance(last_purchase, datetime) else last_purchase
                
                customer_analysis.append({
                    "customer_id": customer.id,
                    "customer_name": customer.name,
                    "email": customer.email,
                    "phone": customer.phone,
                    "total_spent": float(total_spent),
                    "total_orders": total_orders,
                    "average_order_value": float(total_spent / total_orders),
                    "customer_type": customer.customer_type,
                    "account_balance": float(customer.account_balance or 0),
                    "last_purchase": last_purchase.isoformat() if last_purchase else None
                })
        
        # Sort by total spent
        customer_analysis.sort(key=lambda x: x["total_spent"], reverse=True)
        
        return {
            "customers": customer_analysis,
            "total_customers": len(customer_analysis),
            "total_customer_value": sum(c["total_spent"] for c in customer_analysis)
        }
    
    def get_performance_metrics(self, branch_id: Optional[str] = None) -> Dict[str, Any]:
        """Get performance dashboard metrics"""
        
        today = date.today()
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=7)
        last_month = today - timedelta(days=30)
        
        # Get today's sales
        today_sales = self.db.query(Sale).filter(
            func.date(Sale.date) == today
        ).all()
        
        today_invoices = self.db.query(Invoice).filter(
            Invoice.date == today
        ).all()
        
        # Get yesterday's sales for comparison
        yesterday_sales = self.db.query(Sale).filter(
            func.date(Sale.date) == yesterday
        ).all()
        
        yesterday_invoices = self.db.query(Invoice).filter(
            Invoice.date == yesterday
        ).all()
        
        # Calculate metrics
        today_total = (
            sum(sale.total_amount or 0 for sale in today_sales) +
            sum(invoice.total_amount or 0 for invoice in today_invoices)
        )
        
        yesterday_total = (
            sum(sale.total_amount or 0 for sale in yesterday_sales) +
            sum(invoice.total_amount or 0 for invoice in yesterday_invoices)
        )
        
        # Calculate growth percentage
        growth_percentage = (
            ((today_total - yesterday_total) / yesterday_total * 100)
            if yesterday_total > 0 else 0
        )
        
        return {
            "today_sales": float(today_total),
            "yesterday_sales": float(yesterday_total),
            "growth_percentage": float(growth_percentage),
            "today_orders": len(today_sales) + len(today_invoices),
            "yesterday_orders": len(yesterday_sales) + len(yesterday_invoices)
        }
