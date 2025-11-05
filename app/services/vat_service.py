from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.vat import VatReconciliation, VatReconciliationItem, VatPayment
from app.models.sales import Sale, SaleItem
from app.models.purchases import Purchase, PurchaseItem
from app.models.accounting import AccountingCode, AccountingEntry, JournalEntry
from app.core.config import settings


class VatService:
    """Comprehensive VAT business logic service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_vat_collected(self, sale: Sale) -> bool:
        """Record VAT collected from a sale"""
        try:
            if sale.total_vat_amount <= 0:
                return True
            
            # Get VAT reconciliation for the period
            reconciliation = self._get_or_create_vat_reconciliation(sale.date)
            
            # Create VAT reconciliation item
            vat_item = VatReconciliationItem(
                vat_reconciliation_id=reconciliation.id,
                transaction_type='sale',
                transaction_id=str(sale.id),
                transaction_date=sale.date,
                vat_amount=sale.total_vat_amount,
                vat_rate=settings.default_vat_rate,
                description=f"VAT collected from sale #{sale.id}",
                branch_id=sale.branch_id
            )
            
            self.db.add(vat_item)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            return False
    
    def record_vat_paid(self, purchase: Purchase) -> bool:
        """Record VAT paid on a purchase"""
        try:
            if purchase.total_vat_amount <= 0:
                return True
            
            # Get VAT reconciliation for the period
            reconciliation = self._get_or_create_vat_reconciliation(purchase.date)
            
            # Create VAT reconciliation item
            vat_item = VatReconciliationItem(
                vat_reconciliation_id=reconciliation.id,
                transaction_type='purchase',
                transaction_id=str(purchase.id),
                transaction_date=purchase.date,
                vat_amount=purchase.total_vat_amount,
                vat_rate=settings.default_vat_rate,
                description=f"VAT paid on purchase #{purchase.id}",
                branch_id=purchase.branch_id
            )
            
            self.db.add(vat_item)
            self.db.commit()
            
            return True
            
        except Exception as e:
            self.db.rollback()
            return False
    
    def _get_or_create_vat_reconciliation(self, transaction_date: date) -> VatReconciliation:
        """Get or create VAT reconciliation for a period"""
        # Determine period (monthly)
        period_start = date(transaction_date.year, transaction_date.month, 1)
        period_end = date(transaction_date.year, transaction_date.month + 1, 1) - date.resolution
        
        reconciliation = self.db.query(VatReconciliation).filter(
            and_(
                VatReconciliation.period_start == period_start,
                VatReconciliation.period_end == period_end
            )
        ).first()
        
        if not reconciliation:
            reconciliation = VatReconciliation(
                period_start=period_start,
                period_end=period_end,
                status='open',
                vat_rate=settings.default_vat_rate
            )
            self.db.add(reconciliation)
            self.db.commit()
            self.db.refresh(reconciliation)
        
        return reconciliation
    
    def get_vat_summary(self, start_date: date, end_date: date, branch_id: str) -> Dict:
        """Get VAT summary for a period"""
        # Get VAT reconciliation for the period
        reconciliation = self.db.query(VatReconciliation).filter(
            and_(
                VatReconciliation.period_start >= start_date,
                VatReconciliation.period_end <= end_date,
                VatReconciliation.branch_id == branch_id
            )
        ).first()
        
        if not reconciliation:
            return {
                'period': {'start': start_date, 'end': end_date},
                'vat_collected': 0,
                'vat_paid': 0,
                'vat_payable': 0,
                'status': 'no_data'
            }
        
        # Calculate VAT collected
        vat_collected_items = self.db.query(VatReconciliationItem).filter(
            and_(
                VatReconciliationItem.vat_reconciliation_id == reconciliation.id,
                VatReconciliationItem.transaction_type == 'sale'
            )
        ).all()
        
        vat_collected = sum(item.vat_amount for item in vat_collected_items)
        
        # Calculate VAT paid
        vat_paid_items = self.db.query(VatReconciliationItem).filter(
            and_(
                VatReconciliationItem.vat_reconciliation_id == reconciliation.id,
                VatReconciliationItem.transaction_type == 'purchase'
            )
        ).all()
        
        vat_paid = sum(item.vat_amount for item in vat_paid_items)
        
        # Calculate VAT payable
        vat_payable = vat_collected - vat_paid
        
        return {
            'period': {'start': start_date, 'end': end_date},
            'vat_collected': float(vat_collected),
            'vat_paid': float(vat_paid),
            'vat_payable': float(vat_payable),
            'status': reconciliation.status,
            'reconciliation_id': str(reconciliation.id)
        }
    
    def create_vat_payment(self, payment_data: Dict, branch_id: str) -> Tuple[VatPayment, Dict]:
        """Create VAT payment record"""
        try:
            # Get VAT reconciliation
            reconciliation = self.db.query(VatReconciliation).filter(
                VatReconciliation.id == payment_data['reconciliation_id']
            ).first()
            
            if not reconciliation:
                return None, {'success': False, 'error': 'VAT reconciliation not found'}
            
            # Create VAT payment
            vat_payment = VatPayment(
                vat_reconciliation_id=reconciliation.id,
                payment_date=payment_data['payment_date'],
                payment_amount=payment_data['payment_amount'],
                payment_method=payment_data['payment_method'],
                reference_number=payment_data.get('reference_number'),
                notes=payment_data.get('notes'),
                branch_id=branch_id
            )
            
            self.db.add(vat_payment)
            self.db.commit()
            self.db.refresh(vat_payment)
            
            # Update reconciliation status if payment covers full amount
            if payment_data['payment_amount'] >= reconciliation.vat_payable:
                reconciliation.status = 'paid'
                self.db.commit()
            
            return vat_payment, {'success': True, 'payment_id': str(vat_payment.id)}
            
        except Exception as e:
            self.db.rollback()
            return None, {'success': False, 'error': str(e)}
    
    def get_vat_reconciliation_details(self, reconciliation_id: str) -> Dict:
        """Get detailed VAT reconciliation information"""
        reconciliation = self.db.query(VatReconciliation).filter(
            VatReconciliation.id == reconciliation_id
        ).first()
        
        if not reconciliation:
            return {}
        
        # Get all VAT items
        vat_items = self.db.query(VatReconciliationItem).filter(
            VatReconciliationItem.vat_reconciliation_id == reconciliation_id
        ).order_by(VatReconciliationItem.transaction_date).all()
        
        # Get VAT payments
        vat_payments = self.db.query(VatPayment).filter(
            VatPayment.vat_reconciliation_id == reconciliation_id
        ).order_by(VatPayment.payment_date).all()
        
        # Calculate totals
        vat_collected = sum(item.vat_amount for item in vat_items if item.transaction_type == 'sale')
        vat_paid = sum(item.vat_amount for item in vat_items if item.transaction_type == 'purchase')
        vat_payable = vat_collected - vat_paid
        total_payments = sum(payment.payment_amount for payment in vat_payments)
        balance_due = vat_payable - total_payments
        
        return {
            'reconciliation': {
                'id': str(reconciliation.id),
                'period_start': reconciliation.period_start,
                'period_end': reconciliation.period_end,
                'status': reconciliation.status,
                'vat_rate': float(reconciliation.vat_rate)
            },
            'summary': {
                'vat_collected': float(vat_collected),
                'vat_paid': float(vat_paid),
                'vat_payable': float(vat_payable),
                'total_payments': float(total_payments),
                'balance_due': float(balance_due)
            },
            'transactions': [
                {
                    'id': str(item.id),
                    'transaction_type': item.transaction_type,
                    'transaction_id': item.transaction_id,
                    'transaction_date': item.transaction_date,
                    'vat_amount': float(item.vat_amount),
                    'vat_rate': float(item.vat_rate),
                    'description': item.description
                }
                for item in vat_items
            ],
            'payments': [
                {
                    'id': str(payment.id),
                    'payment_date': payment.payment_date,
                    'payment_amount': float(payment.payment_amount),
                    'payment_method': payment.payment_method,
                    'reference_number': payment.reference_number,
                    'notes': payment.notes
                }
                for payment in vat_payments
            ]
        }
    
    def generate_vat_report(self, start_date: date, end_date: date, branch_id: str) -> Dict:
        """Generate comprehensive VAT report"""
        # Get all VAT reconciliations in the period
        reconciliations = self.db.query(VatReconciliation).filter(
            and_(
                VatReconciliation.period_start >= start_date,
                VatReconciliation.period_end <= end_date,
                VatReconciliation.branch_id == branch_id
            )
        ).order_by(VatReconciliation.period_start).all()
        
        total_vat_collected = Decimal('0')
        total_vat_paid = Decimal('0')
        total_vat_payable = Decimal('0')
        total_payments = Decimal('0')
        
        monthly_breakdown = []
        
        for reconciliation in reconciliations:
            # Get VAT items for this reconciliation
            vat_items = self.db.query(VatReconciliationItem).filter(
                VatReconciliationItem.vat_reconciliation_id == reconciliation.id
            ).all()
            
            # Get payments for this reconciliation
            payments = self.db.query(VatPayment).filter(
                VatPayment.vat_reconciliation_id == reconciliation.id
            ).all()
            
            # Calculate totals for this period
            period_vat_collected = sum(item.vat_amount for item in vat_items if item.transaction_type == 'sale')
            period_vat_paid = sum(item.vat_amount for item in vat_items if item.transaction_type == 'purchase')
            period_vat_payable = period_vat_collected - period_vat_paid
            period_payments = sum(payment.payment_amount for payment in payments)
            
            total_vat_collected += period_vat_collected
            total_vat_paid += period_vat_paid
            total_vat_payable += period_vat_payable
            total_payments += period_payments
            
            monthly_breakdown.append({
                'period': {
                    'start': reconciliation.period_start,
                    'end': reconciliation.period_end
                },
                'vat_collected': float(period_vat_collected),
                'vat_paid': float(period_vat_paid),
                'vat_payable': float(period_vat_payable),
                'payments': float(period_payments),
                'balance': float(period_vat_payable - period_payments),
                'status': reconciliation.status
            })
        
        return {
            'report_period': {'start': start_date, 'end': end_date},
            'summary': {
                'total_vat_collected': float(total_vat_collected),
                'total_vat_paid': float(total_vat_paid),
                'total_vat_payable': float(total_vat_payable),
                'total_payments': float(total_payments),
                'net_balance': float(total_vat_payable - total_payments)
            },
            'monthly_breakdown': monthly_breakdown
        }
    
    def update_vat_collected(self, sale: Sale) -> bool:
        """Update VAT collected when sale is modified"""
        try:
            # Remove old VAT record
            self._remove_vat_record(sale)
            
            # Record new VAT amount
            return self.record_vat_collected(sale)
            
        except Exception as e:
            return False
    
    def remove_vat_collected(self, sale: Sale) -> bool:
        """Remove VAT collected when sale is cancelled"""
        try:
            return self._remove_vat_record(sale)
        except Exception as e:
            return False
    
    def _remove_vat_record(self, sale: Sale) -> bool:
        """Remove VAT record for a sale"""
        # Find and delete VAT reconciliation item for this sale
        vat_item = self.db.query(VatReconciliationItem).filter(
            and_(
                VatReconciliationItem.transaction_type == 'sale',
                VatReconciliationItem.transaction_id == str(sale.id)
            )
        ).first()
        
        if vat_item:
            self.db.delete(vat_item)
            self.db.commit()
            return True
        
        return False
    
    def get_vat_liability_report(self, as_of_date: date, branch_id: str) -> Dict:
        """Get VAT liability report as of a specific date"""
        # Get all VAT reconciliations up to the date
        reconciliations = self.db.query(VatReconciliation).filter(
            and_(
                VatReconciliation.period_end <= as_of_date,
                VatReconciliation.branch_id == branch_id
            )
        ).all()
        
        total_vat_payable = Decimal('0')
        total_payments = Decimal('0')
        
        for reconciliation in reconciliations:
            # Calculate VAT payable for this reconciliation
            vat_items = self.db.query(VatReconciliationItem).filter(
                VatReconciliationItem.vat_reconciliation_id == reconciliation.id
            ).all()
            
            vat_collected = sum(item.vat_amount for item in vat_items if item.transaction_type == 'sale')
            vat_paid = sum(item.vat_amount for item in vat_items if item.transaction_type == 'purchase')
            vat_payable = vat_collected - vat_paid
            
            # Get payments for this reconciliation
            payments = self.db.query(VatPayment).filter(
                VatPayment.vat_reconciliation_id == reconciliation.id
            ).all()
            
            total_payment = sum(payment.payment_amount for payment in payments)
            
            total_vat_payable += vat_payable
            total_payments += total_payment
        
        outstanding_liability = total_vat_payable - total_payments
        
        return {
            'as_of_date': as_of_date,
            'total_vat_payable': float(total_vat_payable),
            'total_payments': float(total_payments),
            'outstanding_liability': float(outstanding_liability),
            'status': 'overdue' if outstanding_liability > 0 else 'current'
        } 