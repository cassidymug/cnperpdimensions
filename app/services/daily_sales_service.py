"""
Daily Sales Report Service
Service for generating comprehensive daily sales reports with POS session tracking
"""

from typing import Dict, List, Optional
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from app.models.sales import Sale, Customer
from app.models.pos import PosSession
from app.models.user import User
from app.models.branch import Branch

class DailySalesService:
    """Service for generating daily sales reports with float calculations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_daily_sales_report(
        self,
        report_date: date,
        branch_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        payment_methods: Optional[List[str]] = None,
        include_float: bool = False
    ) -> Dict:
        """
        Generate comprehensive daily sales report with POS session tracking
        
        Args:
            report_date: Date to generate report for
            branch_id: Optional branch filter
            user_id: Optional user/cashier filter
            session_id: Optional specific POS session filter
            payment_methods: Optional payment method filters
            include_float: Whether to include opening float in cash calculations
        
        Returns:
            Dict containing complete daily sales report data
        """
        
        # Get POS sessions for the date
        sessions = self._get_pos_sessions(report_date, branch_id, user_id, session_id)
        
        # Get sales transactions for the date
        transactions = self._get_sales_transactions(
            report_date, branch_id, user_id, session_id, payment_methods
        )
        
        # Calculate summary data
        summary = self._calculate_summary(sessions, transactions, include_float)
        
        # Calculate payment method breakdown
        payment_method_breakdown = self._calculate_payment_methods(transactions)
        
        # Calculate cash reconciliation
        cash_reconciliation = self._calculate_cash_reconciliation(sessions, transactions, include_float)
        
        return {
            'report_date': report_date,
            'branch_id': branch_id,
            'user_id': user_id,
            'filters': {
                'include_float': include_float,
                'payment_methods': payment_methods
            },
            'summary': summary,
            'sessions': sessions,
            'transactions': transactions,
            'payment_methods': payment_method_breakdown,
            'cash_reconciliation': cash_reconciliation,
            'generated_at': datetime.now()
        }
    
    def _get_pos_sessions(
        self,
        report_date: date,
        branch_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> List[Dict]:
        """Get POS sessions for the specified date and filters"""
        
        query = self.db.query(PosSession).join(User).join(Branch)
        
        # Date filter - sessions opened on the report date
        start_datetime = datetime.combine(report_date, datetime.min.time())
        end_datetime = datetime.combine(report_date, datetime.max.time())
        
        query = query.filter(
            and_(
                PosSession.opened_at >= start_datetime,
                PosSession.opened_at <= end_datetime
            )
        )
        
        # Apply additional filters
        if branch_id:
            query = query.filter(PosSession.branch_id == branch_id)
        
        if user_id:
            query = query.filter(PosSession.user_id == user_id)
            
        if session_id:
            query = query.filter(PosSession.id == session_id)
        
        sessions = query.all()
        
        # Convert to dict format with user and branch info
        session_list = []
        for session in sessions:
            session_dict = {
                'id': session.id,
                'user_id': session.user_id,
                'user_name': f"{session.user.first_name} {session.user.last_name}" if session.user else 'Unknown',
                'user_username': session.user.username if session.user else '',
                'branch_id': session.branch_id,
                'branch_name': session.branch.name if session.branch else 'Unknown',
                'till_id': session.till_id,
                'opened_at': session.opened_at,
                'closed_at': session.closed_at,
                'float_amount': float(session.float_amount or 0),
                'cash_submitted': float(session.cash_submitted or 0),
                'status': session.status,
                'verified_by': session.verified_by,
                'verified_at': session.verified_at,
                'verification_note': session.verification_note,
                'total_sales': float(session.total_sales or 0),
                'total_transactions': session.total_transactions or 0,
                'total_cash_sales': float(session.total_cash_sales or 0),
                'total_card_sales': float(session.total_card_sales or 0),
                'total_other_sales': float(session.total_other_sales or 0)
            }
            session_list.append(session_dict)
        
        return session_list
    
    def _get_sales_transactions(
        self,
        report_date: date,
        branch_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        payment_methods: Optional[List[str]] = None
    ) -> List[Dict]:
        """Get sales transactions for the specified date and filters"""
        
        query = self.db.query(Sale).outerjoin(Customer).outerjoin(User)
        
        # Date filter - sales on the report date
        start_datetime = datetime.combine(report_date, datetime.min.time())
        end_datetime = datetime.combine(report_date, datetime.max.time())
        
        query = query.filter(
            and_(
                Sale.date >= start_datetime,
                Sale.date <= end_datetime
            )
        )
        
        # Apply additional filters
        if branch_id:
            query = query.filter(Sale.branch_id == branch_id)
            
        if user_id:
            query = query.filter(Sale.user_id == user_id)
            
        if payment_methods:
            query = query.filter(Sale.payment_method.in_(payment_methods))
        
        # Order by sale time
        query = query.order_by(Sale.date.desc())
        
        transactions = query.all()
        
        # Convert to dict format
        transaction_list = []
        for sale in transactions:
            transaction_dict = {
                'id': sale.id,
                'sale_time': sale.date,
                'sale_date': sale.date.date() if sale.date else None,
                'customer_id': sale.customer_id,
                'customer_name': sale.customer.name if sale.customer else 'Walk-in Customer',
                'customer_phone': sale.customer.phone if sale.customer else None,
                'customer_email': sale.customer.email if sale.customer else None,
                'payment_method': sale.payment_method or 'cash',
                'currency': sale.currency or 'BWP',
                'total_amount': float(sale.total_amount or 0),
                'total_amount_ex_vat': float(sale.total_amount_ex_vat or 0),
                'total_vat_amount': float(sale.total_vat_amount or 0),
                'amount_tendered': float(sale.amount_tendered or 0),
                'change_given': float(sale.change_given or 0),
                'status': sale.status,
                'user_id': sale.user_id,
                'user_name': f"{sale.user.first_name} {sale.user.last_name}" if sale.user else 'Unknown',
                'branch_id': sale.branch_id,
                'invoice_number': sale.invoice_number,
                'pos_session_id': getattr(sale, 'pos_session_id', None)  # If this field exists
            }
            transaction_list.append(transaction_dict)
        
        return transaction_list
    
    def _calculate_summary(
        self,
        sessions: List[Dict],
        transactions: List[Dict],
        include_float: bool
    ) -> Dict:
        """Calculate summary statistics for the daily report"""
        
        # Session totals
        total_sessions = len(sessions)
        total_float = sum(session['float_amount'] for session in sessions)
        
        # Transaction totals
        total_transactions = len(transactions)
        total_sales = sum(tx['total_amount'] for tx in transactions)
        total_cash_sales = sum(tx['total_amount'] for tx in transactions if tx['payment_method'].lower() == 'cash')
        total_card_sales = sum(tx['total_amount'] for tx in transactions if tx['payment_method'].lower() in ['card', 'credit', 'debit'])
        total_other_sales = sum(tx['total_amount'] for tx in transactions if tx['payment_method'].lower() not in ['cash', 'card', 'credit', 'debit'])
        
        # VAT calculations
        total_vat = sum(tx['total_vat_amount'] for tx in transactions)
        total_ex_vat = sum(tx['total_amount_ex_vat'] for tx in transactions)
        
        # Cash calculations (excluding float)
        net_cash_sales = total_cash_sales
        if not include_float:
            net_cash_sales = total_cash_sales  # Float is already excluded from sales
        
        # Cash submitted vs expected
        total_cash_submitted = sum(session['cash_submitted'] for session in sessions)
        expected_cash = total_float + total_cash_sales if include_float else total_cash_sales
        cash_variance = total_cash_submitted - expected_cash
        
        return {
            'report_date': datetime.now().date(),
            'total_sessions': total_sessions,
            'total_float': total_float,
            'total_transactions': total_transactions,
            'total_sales': total_sales,
            'cash_sales': total_cash_sales,
            'card_sales': total_card_sales,
            'other_sales': total_other_sales,
            'net_sales': total_sales,
            'net_cash_sales': net_cash_sales,
            'total_vat': total_vat,
            'total_ex_vat': total_ex_vat,
            'cash_submitted': total_cash_submitted,
            'expected_cash': expected_cash,
            'cash_variance': cash_variance,
            'transaction_count': total_transactions,
            'average_transaction': total_sales / total_transactions if total_transactions > 0 else 0
        }
    
    def _calculate_payment_methods(self, transactions: List[Dict]) -> Dict:
        """Calculate payment method breakdown"""
        
        payment_methods = {}
        
        for transaction in transactions:
            method = transaction['payment_method'].lower()
            
            # Normalize payment method names
            if method in ['cash']:
                method = 'Cash'
            elif method in ['card', 'credit', 'debit']:
                method = 'Card'
            elif method in ['mobile', 'mobile_money', 'orange_money']:
                method = 'Mobile Money'
            else:
                method = 'Other'
            
            if method not in payment_methods:
                payment_methods[method] = 0
            
            payment_methods[method] += transaction['total_amount']
        
        return payment_methods
    
    def _calculate_cash_reconciliation(
        self,
        sessions: List[Dict],
        transactions: List[Dict],
        include_float: bool
    ) -> Dict:
        """Calculate detailed cash reconciliation"""
        
        # Opening float
        opening_float = sum(session['float_amount'] for session in sessions)
        
        # Cash sales
        cash_sales = sum(tx['total_amount'] for tx in transactions if tx['payment_method'].lower() == 'cash')
        
        # Expected cash (float + cash sales)
        expected_cash = opening_float + cash_sales
        
        # Cash submitted by cashiers
        cash_submitted = sum(session['cash_submitted'] for session in sessions)
        
        # Variance
        variance = cash_submitted - expected_cash
        
        # Calculate per session
        session_reconciliation = []
        for session in sessions:
            session_cash_sales = sum(
                tx['total_amount'] for tx in transactions 
                if tx['payment_method'].lower() == 'cash' and tx.get('pos_session_id') == session['id']
            )
            
            session_expected = session['float_amount'] + session_cash_sales
            session_variance = session['cash_submitted'] - session_expected
            
            session_reconciliation.append({
                'session_id': session['id'],
                'user_name': session['user_name'],
                'opening_float': session['float_amount'],
                'cash_sales': session_cash_sales,
                'expected_cash': session_expected,
                'cash_submitted': session['cash_submitted'],
                'variance': session_variance,
                'status': 'balanced' if abs(session_variance) < 0.01 else 'variance'
            })
        
        return {
            'opening_float': opening_float,
            'cash_sales': cash_sales,
            'expected_cash': expected_cash,
            'cash_submitted': cash_submitted,
            'total_variance': variance,
            'is_balanced': abs(variance) < 0.01,
            'sessions': session_reconciliation,
            'include_float_in_calculations': include_float
        }
    
    def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """Get detailed summary for a specific POS session"""
        
        session = self.db.query(PosSession).filter(PosSession.id == session_id).first()
        if not session:
            return None
        
        # Get transactions for this session
        transactions = self.db.query(Sale).filter(
            # Assuming there's a relationship or we filter by user and time
            and_(
                Sale.user_id == session.user_id,
                Sale.date >= session.opened_at,
                Sale.date <= (session.closed_at or datetime.now())
            )
        ).all()
        
        transaction_list = []
        for sale in transactions:
            transaction_list.append({
                'id': sale.id,
                'time': sale.date,
                'amount': float(sale.total_amount or 0),
                'payment_method': sale.payment_method,
                'customer': sale.customer.name if sale.customer else 'Walk-in'
            })
        
        return {
            'session': {
                'id': session.id,
                'user_name': f"{session.user.first_name} {session.user.last_name}" if session.user else 'Unknown',
                'opened_at': session.opened_at,
                'closed_at': session.closed_at,
                'float_amount': float(session.float_amount or 0),
                'status': session.status
            },
            'transactions': transaction_list,
            'summary': {
                'transaction_count': len(transaction_list),
                'total_sales': sum(tx['amount'] for tx in transaction_list),
                'cash_sales': sum(tx['amount'] for tx in transaction_list if tx['payment_method'].lower() == 'cash'),
                'card_sales': sum(tx['amount'] for tx in transaction_list if tx['payment_method'].lower() in ['card', 'credit', 'debit'])
            }
        }
