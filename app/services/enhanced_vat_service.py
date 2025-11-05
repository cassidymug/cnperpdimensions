"""
Enhanced VAT Service for calculating VAT Input/Output from actual transactions
"""
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text

from app.models.sales import Sale, SaleItem
from app.models.purchases import Purchase, PurchaseItem  
from app.models.accounting import AccountingCode, JournalEntry
from app.models.branch import Branch


class EnhancedVatService:
    """Enhanced VAT service that calculates from actual sales and purchase data"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_vat_summary(self, start_date: date, end_date: date, branch_id: str = None) -> Dict:
        """Calculate VAT summary from actual sales and purchase transactions"""
        try:
            # Calculate VAT Output (from sales)
            vat_output = self._calculate_vat_output(start_date, end_date, branch_id)
            
            # Calculate VAT Input (from purchases)  
            vat_input = self._calculate_vat_input(start_date, end_date, branch_id)
            
            # Calculate net VAT (what's owed to tax authority)
            net_vat = vat_output - vat_input
            
            # Get transaction counts for context
            sales_count = self._get_sales_count(start_date, end_date, branch_id)
            purchases_count = self._get_purchases_count(start_date, end_date, branch_id)
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'vat_collected': float(vat_output),  # VAT collected from customers (Output VAT)
                'vat_paid': float(vat_input),        # VAT paid to suppliers (Input VAT)
                'net_vat_liability': float(net_vat), # Net amount owed to tax authority
                'vat_rate': 14.0,                    # Botswana VAT rate
                'transaction_counts': {
                    'sales': sales_count,
                    'purchases': purchases_count
                },
                'status': 'calculated',
                'compliance_due_date': self._calculate_due_date(end_date)
            }
            
        except Exception as e:
            print(f"Error calculating VAT summary: {str(e)}")
            return {
                'period': {
                    'start_date': start_date.isoformat() if start_date else None,
                    'end_date': end_date.isoformat() if end_date else None
                },
                'vat_collected': 0.0,
                'vat_paid': 0.0,
                'net_vat_liability': 0.0,
                'vat_rate': 14.0,
                'transaction_counts': {'sales': 0, 'purchases': 0},
                'status': 'error',
                'error': str(e)
            }
    
    def _calculate_vat_output(self, start_date: date, end_date: date, branch_id: str = None) -> Decimal:
        """Calculate VAT Output (collected from sales)"""
        query = self.db.query(func.sum(Sale.total_vat_amount)).filter(
            and_(
                Sale.date >= start_date,
                Sale.date <= end_date,
                Sale.total_vat_amount > 0  # Only include sales with VAT
            )
        )
        
        if branch_id:
            query = query.filter(Sale.branch_id == branch_id)
        
        result = query.scalar()
        return Decimal(str(result or 0))
    
    def _calculate_vat_input(self, start_date: date, end_date: date, branch_id: str = None) -> Decimal:
        """Calculate VAT Input (paid on purchases)"""
        query = self.db.query(func.sum(Purchase.total_vat_amount)).filter(
            and_(
                Purchase.purchase_date >= start_date,
                Purchase.purchase_date <= end_date,
                Purchase.total_vat_amount > 0  # Only include purchases with VAT
            )
        )
        
        if branch_id:
            query = query.filter(Purchase.branch_id == branch_id)
        
        result = query.scalar()
        return Decimal(str(result or 0))
    
    def _get_sales_count(self, start_date: date, end_date: date, branch_id: str = None) -> int:
        """Get count of sales transactions"""
        query = self.db.query(func.count(Sale.id)).filter(
            and_(
                Sale.date >= start_date,
                Sale.date <= end_date
            )
        )
        
        if branch_id:
            query = query.filter(Sale.branch_id == branch_id)
        
        return query.scalar() or 0
    
    def _get_purchases_count(self, start_date: date, end_date: date, branch_id: str = None) -> int:
        """Get count of purchase transactions"""
        query = self.db.query(func.count(Purchase.id)).filter(
            and_(
                Purchase.purchase_date >= start_date,
                Purchase.purchase_date <= end_date
            )
        )
        
        if branch_id:
            query = query.filter(Purchase.branch_id == branch_id)
        
        return query.scalar() or 0
    
    def _calculate_due_date(self, period_end: date) -> str:
        """Calculate VAT return due date (21 days after period end for Botswana)"""
        due_date = period_end + timedelta(days=21)
        return due_date.isoformat()
    
    def get_vat_by_rate_breakdown(self, start_date: date, end_date: date, branch_id: str = None) -> List[Dict]:
        """Get VAT breakdown by rate (currently only 14% in Botswana)"""
        vat_output = self._calculate_vat_output(start_date, end_date, branch_id)
        vat_input = self._calculate_vat_input(start_date, end_date, branch_id)
        
        return [{
            'rate': '14%',
            'vat_output': float(vat_output),
            'vat_input': float(vat_input),
            'net_vat': float(vat_output - vat_input)
        }]
    
    def get_vat_transactions_detail(self, start_date: date, end_date: date, branch_id: str = None, limit: int = 100) -> List[Dict]:
        """Get detailed VAT transactions for the period"""
        transactions = []
        
        # Get sales with VAT
        sales_query = self.db.query(Sale).filter(
            and_(
                Sale.date >= start_date,
                Sale.date <= end_date,
                Sale.total_vat_amount > 0
            )
        )
        
        if branch_id:
            sales_query = sales_query.filter(Sale.branch_id == branch_id)
        
        sales = sales_query.order_by(Sale.date.desc()).limit(limit // 2).all()
        
        for sale in sales:
            transactions.append({
                'transaction_date': sale.date.isoformat(),
                'item_type': 'output',
                'reference_type': 'sale',
                'reference_id': str(sale.id),
                'description': f'VAT collected from Sale #{sale.id}',
                'vat_amount': float(sale.total_vat_amount),
                'total_amount': float(sale.total_amount)
            })
        
        # Get purchases with VAT
        purchases_query = self.db.query(Purchase).filter(
            and_(
                Purchase.purchase_date >= start_date,
                Purchase.purchase_date <= end_date,
                Purchase.total_vat_amount > 0
            )
        )
        
        if branch_id:
            purchases_query = purchases_query.filter(Purchase.branch_id == branch_id)
        
        purchases = purchases_query.order_by(Purchase.purchase_date.desc()).limit(limit // 2).all()
        
        for purchase in purchases:
            transactions.append({
                'transaction_date': purchase.purchase_date.isoformat(),
                'item_type': 'input',
                'reference_type': 'purchase',
                'reference_id': str(purchase.id),
                'description': f'VAT paid on Purchase #{purchase.id}',
                'vat_amount': float(purchase.total_vat_amount),
                'total_amount': float(purchase.total_amount)
            })
        
        # Sort by date (newest first)
        transactions.sort(key=lambda x: x['transaction_date'], reverse=True)
        
        return transactions
    
    def generate_vat_return_data(self, start_date: date, end_date: date, branch_id: str = None) -> Dict:
        """Generate data for official VAT return submission to tax authority"""
        summary = self.calculate_vat_summary(start_date, end_date, branch_id)
        breakdown = self.get_vat_by_rate_breakdown(start_date, end_date, branch_id)
        
        # Get branch information
        branch = None
        if branch_id:
            branch = self.db.query(Branch).filter(Branch.id == branch_id).first()
        
        return {
            'return_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'due_date': summary['compliance_due_date']
            },
            'business_details': {
                'branch_id': branch_id,
                'branch_name': branch.name if branch else 'All Branches',
                'vat_registration_number': 'P000000000000',  # Should come from app settings
                'return_frequency': 'Monthly'
            },
            'vat_calculation': {
                'total_vat_output': summary['vat_collected'],
                'total_vat_input': summary['vat_paid'], 
                'net_vat_payable': summary['net_vat_liability'],
                'vat_rate_used': summary['vat_rate']
            },
            'breakdown_by_rate': breakdown,
            'transaction_summary': {
                'total_sales_transactions': summary['transaction_counts']['sales'],
                'total_purchase_transactions': summary['transaction_counts']['purchases'],
                'total_vat_transactions': summary['transaction_counts']['sales'] + summary['transaction_counts']['purchases']
            },
            'compliance_status': {
                'calculation_date': datetime.now().isoformat(),
                'status': 'ready_for_filing' if summary['net_vat_liability'] >= 0 else 'refund_due',
                'amount_due': max(0, summary['net_vat_liability']),
                'refund_due': abs(min(0, summary['net_vat_liability']))
            }
        }
    
    def validate_vat_accounts(self, branch_id: str = None) -> Dict:
        """Validate that proper VAT accounts exist for accurate reporting"""
        issues = []
        
        # Check for VAT Receivable account (Input VAT)
        vat_receivable = self.db.query(AccountingCode).filter(
            and_(
                AccountingCode.name == 'VAT Receivable',
                AccountingCode.account_type == 'Asset'
            )
        ).first()
        
        if not vat_receivable:
            issues.append("Missing 'VAT Receivable' asset account for Input VAT")
        
        # Check for VAT Payable account (Output VAT)
        vat_payable = self.db.query(AccountingCode).filter(
            and_(
                AccountingCode.name == 'VAT Payable', 
                AccountingCode.account_type == 'Liability'
            )
        ).first()
        
        if not vat_payable:
            issues.append("Missing 'VAT Payable' liability account for Output VAT")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'recommendations': [
                "Ensure VAT Receivable account exists for Input VAT tracking",
                "Ensure VAT Payable account exists for Output VAT tracking", 
                "Run VAT account migration if accounts are missing"
            ] if issues else []
        }