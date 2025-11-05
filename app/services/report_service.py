from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, text, desc, asc
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from decimal import Decimal
import calendar

from app.models.accounting import AccountingCode, JournalEntry, AccountingEntry
from app.models.sales import Sale, Invoice, Customer, Payment
from app.models.purchases import Purchase, Supplier
from app.models.inventory import Product, InventoryAdjustment
from app.models.banking import BankAccount, BankTransaction
from app.models.user import User
from app.models.branch import Branch


class ReportService:
    """Comprehensive reporting service with IFRS compliance"""
    
    @staticmethod
    def get_trial_balance_data(db: Session, branch_id: Optional[str] = None, as_of_date: Optional[date] = None):
        """Get IFRS-compliant trial balance with reporting tags"""
        if not as_of_date:
            as_of_date = date.today()
            
        # Base query with proper joins and grouping
        query = db.query(
            AccountingCode.id,
            AccountingCode.code,
            AccountingCode.name,
            AccountingCode.account_type,
            AccountingCode.category,
            AccountingCode.reporting_tag,
            func.coalesce(func.sum(JournalEntry.debit_amount), 0).label('total_debits'),
            func.coalesce(func.sum(JournalEntry.credit_amount), 0).label('total_credits')
        ).outerjoin(JournalEntry).outerjoin(AccountingEntry)
        
        # Apply filters
        if branch_id:
            query = query.filter(
                or_(
                    AccountingCode.branch_id == branch_id,
                    JournalEntry.branch_id == branch_id,
                    AccountingEntry.branch_id == branch_id
                )
            )
        
        # Filter by date
        query = query.filter(
            or_(
                AccountingEntry.date_prepared <= as_of_date,
                AccountingEntry.date_prepared.is_(None)
            )
        )
        
        # Group and order
        query = query.group_by(
            AccountingCode.id,
            AccountingCode.code,
            AccountingCode.name,
            AccountingCode.account_type,
            AccountingCode.category,
            AccountingCode.reporting_tag
        ).order_by(AccountingCode.code.asc())
        
        results = query.all()
        
        # Group by IFRS categories for enhanced reporting
        ifrs_grouped_data = {}
        for row in results:
            tag = row.reporting_tag or 'Uncategorized'
            if tag not in ifrs_grouped_data:
                ifrs_grouped_data[tag] = []
            
            balance = float(row.total_debits or 0) - float(row.total_credits or 0)
            ifrs_grouped_data[tag].append({
                "id": row.id,
                "code": row.code,
                "name": row.name,
                "account_type": row.account_type,
                "category": row.category,
                "reporting_tag": row.reporting_tag,
                "total_debits": float(row.total_debits or 0),
                "total_credits": float(row.total_credits or 0),
                "balance": balance
            })
        
        return {
            "as_of_date": as_of_date.isoformat(),
            "trial_balance": [item for sublist in ifrs_grouped_data.values() for item in sublist],
            "ifrs_grouped_data": ifrs_grouped_data,
            "total_debits": sum(float(row.total_debits or 0) for row in results),
            "total_credits": sum(float(row.total_credits or 0) for row in results)
        }
    
    @staticmethod
    def get_balance_sheet_data(db: Session, branch_id: Optional[str] = None, as_of_date: Optional[date] = None):
        """Get IFRS-compliant balance sheet data"""
        if not as_of_date:
            as_of_date = date.today()
        
        # Current Assets
        current_assets_query = db.query(
            AccountingCode.name,
            func.sum(JournalEntry.debit_amount - JournalEntry.credit_amount).label('balance')
        ).join(AccountingEntry).join(AccountingCode).filter(
            AccountingCode.account_type == 'asset',
            AccountingCode.reporting_tag.in_(['Current Assets', 'Cash and Cash Equivalents', 'Trade Receivables']),
            AccountingEntry.date_prepared <= as_of_date
        )
        if branch_id:
            current_assets_query = current_assets_query.filter(AccountingEntry.branch_id == branch_id)
        
        current_assets = {row.name: float(row.balance or 0) for row in current_assets_query.group_by(AccountingCode.name).all()}
        
        # Non-Current Assets
        non_current_assets_query = db.query(
            AccountingCode.name,
            func.sum(JournalEntry.debit_amount - JournalEntry.credit_amount).label('balance')
        ).join(AccountingEntry).join(AccountingCode).filter(
            AccountingCode.account_type == 'asset',
            AccountingCode.reporting_tag.in_(['Non-Current Assets', 'Property, Plant and Equipment', 'Intangible Assets']),
            AccountingEntry.date_prepared <= as_of_date
        )
        if branch_id:
            non_current_assets_query = non_current_assets_query.filter(AccountingEntry.branch_id == branch_id)
        
        non_current_assets = {row.name: float(row.balance or 0) for row in non_current_assets_query.group_by(AccountingCode.name).all()}
        
        # Current Liabilities
        current_liabilities_query = db.query(
            AccountingCode.name,
            func.sum(JournalEntry.credit_amount - JournalEntry.debit_amount).label('balance')
        ).join(AccountingEntry).join(AccountingCode).filter(
            AccountingCode.account_type == 'liability',
            AccountingCode.reporting_tag.in_(['Current Liabilities', 'Trade Payables', 'Short-term Borrowings']),
            AccountingEntry.date_prepared <= as_of_date
        )
        if branch_id:
            current_liabilities_query = current_liabilities_query.filter(AccountingEntry.branch_id == branch_id)
        
        current_liabilities = {row.name: float(row.balance or 0) for row in current_liabilities_query.group_by(AccountingCode.name).all()}
        
        # Non-Current Liabilities
        non_current_liabilities_query = db.query(
            AccountingCode.name,
            func.sum(JournalEntry.credit_amount - JournalEntry.debit_amount).label('balance')
        ).join(AccountingEntry).join(AccountingCode).filter(
            AccountingCode.account_type == 'liability',
            AccountingCode.reporting_tag.in_(['Non-Current Liabilities', 'Long-term Borrowings']),
            AccountingEntry.date_prepared <= as_of_date
        )
        if branch_id:
            non_current_liabilities_query = non_current_liabilities_query.filter(AccountingEntry.branch_id == branch_id)
        
        non_current_liabilities = {row.name: float(row.balance or 0) for row in non_current_liabilities_query.group_by(AccountingCode.name).all()}
        
        # Equity
        equity_query = db.query(
            AccountingCode.name,
            func.sum(JournalEntry.credit_amount - JournalEntry.debit_amount).label('balance')
        ).join(AccountingEntry).join(AccountingCode).filter(
            AccountingCode.account_type == 'equity',
            AccountingEntry.date_prepared <= as_of_date
        )
        if branch_id:
            equity_query = equity_query.filter(AccountingEntry.branch_id == branch_id)
        
        equity = {row.name: float(row.balance or 0) for row in equity_query.group_by(AccountingCode.name).all()}
        
        # Calculate totals
        total_current_assets = sum(current_assets.values())
        total_non_current_assets = sum(non_current_assets.values())
        total_assets = total_current_assets + total_non_current_assets
        
        total_current_liabilities = sum(current_liabilities.values())
        total_non_current_liabilities = sum(non_current_liabilities.values())
        total_liabilities = total_current_liabilities + total_non_current_liabilities
        
        total_equity = sum(equity.values())
        
        return {
            "as_of_date": as_of_date.isoformat(),
            "current_assets": current_assets,
            "total_current_assets": total_current_assets,
            "non_current_assets": non_current_assets,
            "total_non_current_assets": total_non_current_assets,
            "total_assets": total_assets,
            "current_liabilities": current_liabilities,
            "total_current_liabilities": total_current_liabilities,
            "non_current_liabilities": non_current_liabilities,
            "total_non_current_liabilities": total_non_current_liabilities,
            "total_liabilities": total_liabilities,
            "equity": equity,
            "total_equity": total_equity,
            "total_liabilities_and_equity": total_liabilities + total_equity
        }
    
    @staticmethod
    def get_income_statement_data(db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None, branch_id: Optional[str] = None):
        """Get IFRS-compliant income statement"""
        if not start_date:
            start_date = date.today().replace(day=1)
        if not end_date:
            end_date = date.today()
        
        # Revenue
        revenue_query = db.query(
            AccountingCode.name,
            func.sum(JournalEntry.credit_amount).label('amount')
        ).join(AccountingEntry).join(AccountingCode).filter(
            AccountingCode.account_type == 'revenue',
            AccountingEntry.date_prepared.between(start_date, end_date)
        )
        if branch_id:
            revenue_query = revenue_query.filter(AccountingEntry.branch_id == branch_id)
        
        revenue = {row.name: float(row.amount or 0) for row in revenue_query.group_by(AccountingCode.name).all()}
        total_revenue = sum(revenue.values())
        
        # Cost of Sales
        cost_of_sales_query = db.query(
            AccountingCode.name,
            func.sum(JournalEntry.debit_amount).label('amount')
        ).join(AccountingEntry).join(AccountingCode).filter(
            AccountingCode.account_type == 'expense',
            AccountingCode.reporting_tag == 'Cost of Sales',
            AccountingEntry.date_prepared.between(start_date, end_date)
        )
        if branch_id:
            cost_of_sales_query = cost_of_sales_query.filter(AccountingEntry.branch_id == branch_id)
        
        cost_of_sales = {row.name: float(row.amount or 0) for row in cost_of_sales_query.group_by(AccountingCode.name).all()}
        total_cost_of_sales = sum(cost_of_sales.values())
        
        # Gross Profit
        gross_profit = total_revenue - total_cost_of_sales
        
        # Operating Expenses
        operating_expenses_query = db.query(
            AccountingCode.name,
            func.sum(JournalEntry.debit_amount).label('amount')
        ).join(AccountingEntry).join(AccountingCode).filter(
            AccountingCode.account_type == 'expense',
            AccountingCode.reporting_tag.in_(['Operating Expenses', 'Administrative Expenses', 'Selling Expenses']),
            AccountingEntry.date_prepared.between(start_date, end_date)
        )
        if branch_id:
            operating_expenses_query = operating_expenses_query.filter(AccountingEntry.branch_id == branch_id)
        
        operating_expenses = {row.name: float(row.amount or 0) for row in operating_expenses_query.group_by(AccountingCode.name).all()}
        total_operating_expenses = sum(operating_expenses.values())
        
        # Operating Profit
        operating_profit = gross_profit - total_operating_expenses
        
        # Other Income/Expenses
        other_items_query = db.query(
            AccountingCode.name,
            func.sum(case((JournalEntry.credit_amount > 0, JournalEntry.credit_amount), else_=0)).label('income'),
            func.sum(case((JournalEntry.debit_amount > 0, JournalEntry.debit_amount), else_=0)).label('expense')
        ).join(AccountingEntry).join(AccountingCode).filter(
            AccountingCode.reporting_tag == 'Other Income/Expenses',
            AccountingEntry.date_prepared.between(start_date, end_date)
        )
        if branch_id:
            other_items_query = other_items_query.filter(AccountingEntry.branch_id == branch_id)
        
        other_items = []
        for row in other_items_query.group_by(AccountingCode.name).all():
            other_items.append({
                "name": row.name,
                "income": float(row.income or 0),
                "expense": float(row.expense or 0)
            })
        
        total_other_income = sum(item['income'] for item in other_items)
        total_other_expenses = sum(item['expense'] for item in other_items)
        
        # Net Profit
        net_profit = operating_profit + total_other_income - total_other_expenses
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "revenue": revenue,
            "total_revenue": total_revenue,
            "cost_of_sales": cost_of_sales,
            "total_cost_of_sales": total_cost_of_sales,
            "gross_profit": gross_profit,
            "operating_expenses": operating_expenses,
            "total_operating_expenses": total_operating_expenses,
            "operating_profit": operating_profit,
            "other_items": other_items,
            "total_other_income": total_other_income,
            "total_other_expenses": total_other_expenses,
            "net_profit": net_profit
        }
    
    @staticmethod
    def get_cash_flow_statement(db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None, branch_id: Optional[str] = None):
        """Get IFRS-compliant cash flow statement"""
        if not start_date:
            start_date = date.today().replace(day=1)
        if not end_date:
            end_date = date.today()
        
        # Operating Activities
        operating_cash_query = db.query(
            func.sum(case((JournalEntry.debit_amount > 0, JournalEntry.debit_amount), else_=0)).label('cash_out'),
            func.sum(case((JournalEntry.credit_amount > 0, JournalEntry.credit_amount), else_=0)).label('cash_in')
        ).join(AccountingEntry).join(AccountingCode).filter(
            AccountingCode.reporting_tag == 'Operating Activities',
            AccountingEntry.date_prepared.between(start_date, end_date)
        )
        if branch_id:
            operating_cash_query = operating_cash_query.filter(AccountingEntry.branch_id == branch_id)
        
        operating_result = operating_cash_query.first()
        operating_cash_in = float(operating_result.cash_in or 0)
        operating_cash_out = float(operating_result.cash_out or 0)
        net_operating_cash = operating_cash_in - operating_cash_out
        
        # Investing Activities
        investing_cash_query = db.query(
            func.sum(case((JournalEntry.debit_amount > 0, JournalEntry.debit_amount), else_=0)).label('cash_out'),
            func.sum(case((JournalEntry.credit_amount > 0, JournalEntry.credit_amount), else_=0)).label('cash_in')
        ).join(AccountingEntry).join(AccountingCode).filter(
            AccountingCode.reporting_tag == 'Investing Activities',
            AccountingEntry.date_prepared.between(start_date, end_date)
        )
        if branch_id:
            investing_cash_query = investing_cash_query.filter(AccountingEntry.branch_id == branch_id)
        
        investing_result = investing_cash_query.first()
        investing_cash_in = float(investing_result.cash_in or 0)
        investing_cash_out = float(investing_result.cash_out or 0)
        net_investing_cash = investing_cash_in - investing_cash_out
        
        # Financing Activities
        financing_cash_query = db.query(
            func.sum(case((JournalEntry.debit_amount > 0, JournalEntry.debit_amount), else_=0)).label('cash_out'),
            func.sum(case((JournalEntry.credit_amount > 0, JournalEntry.credit_amount), else_=0)).label('cash_in')
        ).join(AccountingEntry).join(AccountingCode).filter(
            AccountingCode.reporting_tag == 'Financing Activities',
            AccountingEntry.date_prepared.between(start_date, end_date)
        )
        if branch_id:
            financing_cash_query = financing_cash_query.filter(AccountingEntry.branch_id == branch_id)
        
        financing_result = financing_cash_query.first()
        financing_cash_in = float(financing_result.cash_in or 0)
        financing_cash_out = float(financing_result.cash_out or 0)
        net_financing_cash = financing_cash_in - financing_cash_out
        
        # Net Cash Flow
        net_cash_flow = net_operating_cash + net_investing_cash + net_financing_cash
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "operating_activities": {
                "cash_in": operating_cash_in,
                "cash_out": operating_cash_out,
                "net_cash": net_operating_cash
            },
            "investing_activities": {
                "cash_in": investing_cash_in,
                "cash_out": investing_cash_out,
                "net_cash": net_investing_cash
            },
            "financing_activities": {
                "cash_in": financing_cash_in,
                "cash_out": financing_cash_out,
                "net_cash": net_financing_cash
            },
            "net_cash_flow": net_cash_flow
        }
    
    @staticmethod
    def get_receivables_aging(db: Session, branch_id: Optional[str] = None):
        """Get trade receivables aging report"""
        # Get all invoices with outstanding balances
        invoices_query = db.query(
            Invoice.id,
            Invoice.invoice_number,
            Invoice.date,
            Invoice.due_date,
            Invoice.total_amount,
            Invoice.paid_amount,
            Customer.name.label('customer_name'),
            Customer.email.label('customer_email')
        ).join(Customer).filter(
            Invoice.total_amount > Invoice.paid_amount
        )
        
        if branch_id:
            invoices_query = invoices_query.filter(Invoice.branch_id == branch_id)
        
        invoices = invoices_query.all()
        
        # Calculate aging buckets
        today = date.today()
        aging_buckets = {
            "current": [],
            "30_days": [],
            "60_days": [],
            "90_days": [],
            "over_90_days": []
        }
        
        for invoice in invoices:
            outstanding_amount = float(invoice.total_amount - invoice.paid_amount)
            days_overdue = (today - invoice.due_date).days if invoice.due_date else 0
            
            aging_data = {
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer_name,
                "customer_email": invoice.customer_email,
                "invoice_date": invoice.date.isoformat(),
                "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
                "total_amount": float(invoice.total_amount),
                "paid_amount": float(invoice.paid_amount),
                "outstanding_amount": outstanding_amount,
                "days_overdue": days_overdue
            }
            
            if days_overdue <= 0:
                aging_buckets["current"].append(aging_data)
            elif days_overdue <= 30:
                aging_buckets["30_days"].append(aging_data)
            elif days_overdue <= 60:
                aging_buckets["60_days"].append(aging_data)
            elif days_overdue <= 90:
                aging_buckets["90_days"].append(aging_data)
            else:
                aging_buckets["over_90_days"].append(aging_data)
        
        # Calculate totals
        totals = {}
        for bucket, invoices in aging_buckets.items():
            totals[bucket] = sum(inv['outstanding_amount'] for inv in invoices)
        
        total_receivables = sum(totals.values())
        
        return {
            "aging_buckets": aging_buckets,
            "totals": totals,
            "total_receivables": total_receivables,
            "as_of_date": today.isoformat()
        }
    
    @staticmethod
    def get_payables_aging(db: Session, branch_id: Optional[str] = None):
        """Get trade payables aging report"""
        # Get all purchases with outstanding balances
        purchases_query = db.query(
            Purchase.id,
            Purchase.purchase_number,
            Purchase.date,
            Purchase.due_date,
            Purchase.total_amount,
            Purchase.paid_amount,
            Supplier.name.label('supplier_name'),
            Supplier.email.label('supplier_email')
        ).join(Supplier).filter(
            Purchase.total_amount > Purchase.paid_amount
        )
        
        if branch_id:
            purchases_query = purchases_query.filter(Purchase.branch_id == branch_id)
        
        purchases = purchases_query.all()
        
        # Calculate aging buckets
        today = date.today()
        aging_buckets = {
            "current": [],
            "30_days": [],
            "60_days": [],
            "90_days": [],
            "over_90_days": []
        }
        
        for purchase in purchases:
            outstanding_amount = float(purchase.total_amount - purchase.paid_amount)
            days_overdue = (today - purchase.due_date).days if purchase.due_date else 0
            
            aging_data = {
                "purchase_id": str(purchase.id),
                "purchase_number": purchase.purchase_number,
                "supplier_name": purchase.supplier_name,
                "supplier_email": purchase.supplier_email,
                "purchase_date": purchase.date.isoformat(),
                "due_date": purchase.due_date.isoformat() if purchase.due_date else None,
                "total_amount": float(purchase.total_amount),
                "paid_amount": float(purchase.paid_amount),
                "outstanding_amount": outstanding_amount,
                "days_overdue": days_overdue
            }
            
            if days_overdue <= 0:
                aging_buckets["current"].append(aging_data)
            elif days_overdue <= 30:
                aging_buckets["30_days"].append(aging_data)
            elif days_overdue <= 60:
                aging_buckets["60_days"].append(aging_data)
            elif days_overdue <= 90:
                aging_buckets["90_days"].append(aging_data)
            else:
                aging_buckets["over_90_days"].append(aging_data)
        
        # Calculate totals
        totals = {}
        for bucket, purchases in aging_buckets.items():
            totals[bucket] = sum(pur['outstanding_amount'] for pur in purchases)
        
        total_payables = sum(totals.values())
        
        return {
            "aging_buckets": aging_buckets,
            "totals": totals,
            "total_payables": total_payables,
            "as_of_date": today.isoformat()
        }
    
    @staticmethod
    def get_vat_summary(db: Session, start_date: Optional[date] = None, end_date: Optional[date] = None, branch_id: Optional[str] = None):
        """Get comprehensive VAT summary"""
        if not start_date:
            start_date = date.today().replace(day=1)
        if not end_date:
            end_date = date.today()
        
        # VAT Output (from sales)
        vat_output_query = db.query(
            func.sum(JournalEntry.credit_amount)
        ).join(AccountingEntry).join(AccountingCode).filter(
            AccountingCode.name.like('%VAT%'),
            AccountingCode.account_type == 'liability',
            AccountingCode.reporting_tag == 'VAT Output',
            AccountingEntry.date_prepared.between(start_date, end_date)
        )
        if branch_id:
            vat_output_query = vat_output_query.filter(AccountingEntry.branch_id == branch_id)
        
        vat_output = vat_output_query.scalar() or 0
        
        # VAT Input (from purchases)
        vat_input_query = db.query(
            func.sum(JournalEntry.debit_amount)
        ).join(AccountingEntry).join(AccountingCode).filter(
            AccountingCode.name.like('%VAT%'),
            AccountingCode.account_type == 'asset',
            AccountingCode.reporting_tag == 'VAT Input',
            AccountingEntry.date_prepared.between(start_date, end_date)
        )
        if branch_id:
            vat_input_query = vat_input_query.filter(AccountingEntry.branch_id == branch_id)
        
        vat_input = vat_input_query.scalar() or 0
        
        # Net VAT
        net_vat = vat_output - vat_input
        
        # VAT by rate
        vat_by_rate_query = db.query(
            AccountingCode.name,
            func.sum(JournalEntry.credit_amount).label('vat_output'),
            func.sum(JournalEntry.debit_amount).label('vat_input')
        ).join(AccountingEntry).join(AccountingCode).filter(
            AccountingCode.name.like('%VAT%'),
            AccountingEntry.date_prepared.between(start_date, end_date)
        )
        if branch_id:
            vat_by_rate_query = vat_by_rate_query.filter(AccountingEntry.branch_id == branch_id)
        
        vat_by_rate = []
        for row in vat_by_rate_query.group_by(AccountingCode.name).all():
            vat_by_rate.append({
                "rate": row.name,
                "vat_output": float(row.vat_output or 0),
                "vat_input": float(row.vat_input or 0),
                "net_vat": float(row.vat_output or 0) - float(row.vat_input or 0)
            })
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "vat_output": float(vat_output),
            "vat_input": float(vat_input),
            "net_vat": float(net_vat),
            "vat_by_rate": vat_by_rate
        }
    
    @staticmethod
    def get_performance_dashboard(db: Session, branch_id: Optional[str] = None):
        """Get comprehensive performance dashboard"""
        today = date.today()
        start_of_month = today.replace(day=1)
        start_of_year = today.replace(month=1, day=1)
        
        # Sales Performance
        monthly_sales = db.query(func.sum(Sale.total_amount)).filter(
            Sale.date.between(start_of_month, today)
        )
        if branch_id:
            monthly_sales = monthly_sales.filter(Sale.branch_id == branch_id)
        monthly_sales = monthly_sales.scalar() or 0
        
        yearly_sales = db.query(func.sum(Sale.total_amount)).filter(
            Sale.date.between(start_of_year, today)
        )
        if branch_id:
            yearly_sales = yearly_sales.filter(Sale.branch_id == branch_id)
        yearly_sales = yearly_sales.scalar() or 0
        
        # Customer Metrics
        total_customers = db.query(Customer).count()
        active_customers = db.query(Customer).join(Sale).distinct().count()
        
        # Inventory Metrics
        total_products = db.query(Product).count()
        low_stock_products = db.query(Product).filter(
            Product.quantity <= Product.reorder_point
        ).count()
        
        # Financial Metrics
        current_assets = db.query(func.sum(JournalEntry.debit_amount - JournalEntry.credit_amount)).join(
            AccountingEntry
        ).join(AccountingCode).filter(
            AccountingCode.account_type == 'asset',
            AccountingCode.reporting_tag == 'Current Assets'
        )
        if branch_id:
            current_assets = current_assets.filter(AccountingEntry.branch_id == branch_id)
        current_assets = current_assets.scalar() or 0
        
        return {
            "as_of_date": today.isoformat(),
            "sales_performance": {
                "monthly_sales": float(monthly_sales),
                "yearly_sales": float(yearly_sales)
            },
            "customer_metrics": {
                "total_customers": total_customers,
                "active_customers": active_customers,
                "customer_activity_rate": (active_customers / total_customers * 100) if total_customers > 0 else 0
            },
            "inventory_metrics": {
                "total_products": total_products,
                "low_stock_products": low_stock_products,
                "stock_alert_rate": (low_stock_products / total_products * 100) if total_products > 0 else 0
            },
            "financial_metrics": {
                "current_assets": float(current_assets)
            }
        }