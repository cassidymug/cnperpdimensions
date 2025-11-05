"""
Aging Reports Service - IFRS Compliant
Service for generating debtors and creditors aging reports
"""

from typing import Dict, List, Optional
from datetime import date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models.sales import Sale, Customer, Invoice
from app.models.purchases import Purchase, Supplier
from app.services.ifrs_reports_core import IFRSReportsCore

class AgingReportsService:
    """Service for generating aging reports with IFRS compliance"""
    
    def __init__(self, db: Session):
        self.db = db
        self.ifrs_core = IFRSReportsCore(db)
    
    def generate_debtors_aging(
        self,
        as_of_date: date = None,
        customer_id: Optional[str] = None,
        min_amount: Decimal = None,
        currency: str = None,
        branch_id: Optional[str] = None
    ) -> Dict:
        """
        Generate Debtors Aging Report
        IFRS 9: Financial Instruments - Expected Credit Losses
        """
        if as_of_date is None:
            as_of_date = date.today()
        
        # Initialize customer aging data
        customer_aging = {}
        total_outstanding = Decimal('0.00')
        
        # Try to get invoices, but handle gracefully if model issues exist
        try:
            # Include draft and other non-paid invoices as outstanding
            query = self.db.query(Invoice).filter(
                Invoice.status.in_(['draft', 'sent', 'partial', 'overdue'])  # Outstanding invoices including drafts
            )
            # Filter by branch if provided
            if branch_id:
                query = query.filter(Invoice.branch_id == branch_id)
            
            if customer_id:
                query = query.filter(Invoice.customer_id == customer_id)
                
            outstanding_invoices = query.all()
            
            for invoice in outstanding_invoices:
                try:
                    # Use total_amount if set, otherwise fall back to total
                    invoice_amount = invoice.total_amount or invoice.total
                    outstanding_amount = invoice_amount - (invoice.amount_paid or Decimal('0.00'))
                    
                    if outstanding_amount <= 0:  # Skip fully paid
                        continue
                        
                    if min_amount and outstanding_amount < min_amount:
                        continue
                        
                    days_outstanding = (as_of_date - invoice.date).days if invoice.date else 0
                    
                    # Initialize customer if not exists
                    customer_key = invoice.customer_id
                    if customer_key not in customer_aging:
                        customer_aging[customer_key] = {
                            'customer_id': invoice.customer_id,
                            'customer_name': invoice.customer.name if invoice.customer else 'Unknown Customer',
                            'customer_code': getattr(invoice.customer, 'code', '') if invoice.customer else '',
                            'contact_person': getattr(invoice.customer, 'contact_person', '') if invoice.customer else '',
                            'phone': getattr(invoice.customer, 'phone', '') if invoice.customer else '',
                            'email': getattr(invoice.customer, 'email', '') if invoice.customer else '',
                            'current': Decimal('0.00'),
                            'days_31_60': Decimal('0.00'),
                            'days_61_90': Decimal('0.00'),
                            'days_91_120': Decimal('0.00'),
                            'days_120_plus': Decimal('0.00'),
                            'total_outstanding': Decimal('0.00'),
                            'invoice_count': 0,
                            'oldest_invoice_date': invoice.date,
                            'invoices': []
                        }
                    
                    # Add to appropriate aging bucket
                    if days_outstanding <= 30:
                        customer_aging[customer_key]['current'] += outstanding_amount
                    elif days_outstanding <= 60:
                        customer_aging[customer_key]['days_31_60'] += outstanding_amount
                    elif days_outstanding <= 90:
                        customer_aging[customer_key]['days_61_90'] += outstanding_amount
                    elif days_outstanding <= 120:
                        customer_aging[customer_key]['days_91_120'] += outstanding_amount
                    else:
                        customer_aging[customer_key]['days_120_plus'] += outstanding_amount
                    
                    # Update customer totals
                    customer_aging[customer_key]['total_outstanding'] += outstanding_amount
                    customer_aging[customer_key]['invoice_count'] += 1
                    
                    # Track oldest invoice for credit assessment
                    if invoice.date and (not customer_aging[customer_key]['oldest_invoice_date'] or 
                                       invoice.date < customer_aging[customer_key]['oldest_invoice_date']):
                        customer_aging[customer_key]['oldest_invoice_date'] = invoice.date
                    
                    # Add invoice details for drill-down
                    customer_aging[customer_key]['invoices'].append({
                        'invoice_id': invoice.id,
                        'invoice_number': invoice.invoice_number or f"INV-{invoice.id[:8]}",
                        'invoice_date': invoice.date,
                        'due_date': invoice.due_date or invoice.date,
                        'total_amount': float(invoice.total_amount),
                        'amount_paid': float(invoice.amount_paid or 0),
                        'outstanding_amount': float(outstanding_amount),
                        'days_outstanding': days_outstanding,
                        'status': invoice.status
                    })
                    
                    total_outstanding += outstanding_amount
                    
                except Exception as e:
                    # Skip problematic records
                    continue
                    
        except Exception:
            # If there are no invoices or model issues, return empty structure
            pass
        
        # Convert to list and format for frontend
        debtors_list = []
        for customer_data in customer_aging.values():
            # Convert Decimal to float for JSON serialization
            debtor_record = {
                'customer_id': customer_data['customer_id'],
                'customer_name': customer_data['customer_name'],
                'customer_code': customer_data['customer_code'],
                'contact_person': customer_data['contact_person'],
                'phone': customer_data['phone'],
                'email': customer_data['email'],
                'current': float(customer_data['current']),
                'days_31_60': float(customer_data['days_31_60']),
                'days_61_90': float(customer_data['days_61_90']),
                'days_91_120': float(customer_data['days_91_120']),
                'days_120_plus': float(customer_data['days_120_plus']),
                'total_outstanding': float(customer_data['total_outstanding']),
                'invoice_count': customer_data['invoice_count'],
                'oldest_invoice_date': customer_data['oldest_invoice_date'],
                'invoices': customer_data['invoices']
            }
            debtors_list.append(debtor_record)
        
        # Sort by total outstanding (highest first)
        debtors_list.sort(key=lambda x: x['total_outstanding'], reverse=True)
        
        # Calculate bucket totals
        summary_totals = {
            'current': sum(d['current'] for d in debtors_list),
            'days_31_60': sum(d['days_31_60'] for d in debtors_list),
            'days_61_90': sum(d['days_61_90'] for d in debtors_list),
            'days_91_120': sum(d['days_91_120'] for d in debtors_list),
            'days_120_plus': sum(d['days_120_plus'] for d in debtors_list),
            'total': float(total_outstanding)
        }
        
        # IFRS 9 Expected Credit Loss calculation
        ecl_provision = self._calculate_expected_credit_loss(debtors_list)
        
        return {
            'as_of_date': as_of_date,
            'debtors': debtors_list,
            'summary': summary_totals,
            'total_outstanding': float(total_outstanding),
            'customer_count': len(debtors_list),
            'expected_credit_loss': ecl_provision,
            'ifrs_compliance': {
                'standard': 'IFRS 9 - Financial Instruments',
                'ecl_method': 'Simplified approach for trade receivables',
                'provision_rate': float(ecl_provision.get('provision_rate', 0)),
                'total_provision': float(ecl_provision.get('total_provision', 0))
            }
        }
    
    def generate_creditors_aging(
        self,
        as_of_date: date = None,
        supplier_id: Optional[str] = None,
        min_amount: Decimal = None,
        currency: str = None,
        branch_id: Optional[str] = None
    ) -> Dict:
        """
        Generate Creditors Aging Report
        IAS 1: Presentation of Financial Statements
        """
        if as_of_date is None:
            as_of_date = date.today()
            
        # Get outstanding purchases - those with unpaid balances
        try:
            query = self.db.query(Purchase).filter(
                and_(
                    Purchase.purchase_date <= as_of_date,
                    or_(
                        Purchase.amount_paid == None,
                        Purchase.amount_paid < Purchase.total_amount
                    )
                )
            ).limit(100)
            # Filter by branch if provided
            if branch_id:
                query = query.filter(Purchase.branch_id == branch_id)
        except Exception as e:
            # If there are issues, return empty structure
            return self._get_empty_creditors_aging_structure(as_of_date)
        
        if supplier_id:
            query = query.filter(Purchase.supplier_id == supplier_id)
            
        if currency:
            # Skip currency filter for now 
            pass
            
        outstanding_purchases = query.all()
        
        aging_buckets = {
            '0-30': [],
            '31-60': [],
            '61-90': [],
            '91-120': [],
            '120+': []
        }
        
        total_outstanding = Decimal('0.00')
        
        for purchase in outstanding_purchases:
            try:
                outstanding_amount = purchase.total_amount - (purchase.amount_paid or Decimal('0.00'))
                
                if min_amount and outstanding_amount < min_amount:
                    continue
                    
                days_outstanding = (as_of_date - purchase.purchase_date).days if purchase.purchase_date else 0
                
                aging_item = {
                    'supplier_id': purchase.supplier_id,
                    'supplier_name': purchase.supplier.name if purchase.supplier else 'Unknown',
                    'purchase_id': purchase.id,
                    'invoice_number': getattr(purchase, 'reference', f'PUR-{purchase.id[:8]}'),
                    'purchase_date': purchase.purchase_date,
                    'due_date': purchase.due_date,
                    'total_amount': float(purchase.total_amount),
                    'amount_paid': float(purchase.amount_paid or 0),
                    'outstanding_amount': float(outstanding_amount),
                    'days_outstanding': days_outstanding,
                    'currency': 'BWP',  # Default currency
                    'status': purchase.status
                }
            except Exception as e:
                # Skip problematic records
                continue
            
            total_outstanding += outstanding_amount
            
            # Categorize by aging bucket
            if days_outstanding <= 30:
                aging_buckets['0-30'].append(aging_item)
            elif days_outstanding <= 60:
                aging_buckets['31-60'].append(aging_item)
            elif days_outstanding <= 90:
                aging_buckets['61-90'].append(aging_item)
            elif days_outstanding <= 120:
                aging_buckets['91-120'].append(aging_item)
            else:
                aging_buckets['120+'].append(aging_item)
        
        # Calculate bucket totals
        bucket_totals = {}
        for bucket, items in aging_buckets.items():
            bucket_totals[bucket] = sum(item['outstanding_amount'] for item in items)
        
        # Group by supplier for frontend display
        supplier_aging = {}
        suppliers_cache = {}  # Cache supplier objects
        
        for bucket_name, items in aging_buckets.items():
            for item in items:
                supplier_id = item['supplier_id']
                if supplier_id not in supplier_aging:
                    # Get supplier details if not cached
                    if supplier_id not in suppliers_cache:
                        supplier = self.db.query(Supplier).filter(Supplier.id == supplier_id).first()
                        suppliers_cache[supplier_id] = supplier
                    else:
                        supplier = suppliers_cache[supplier_id]
                    
                    supplier_aging[supplier_id] = {
                        'supplier_id': supplier_id,
                        'supplier_name': item['supplier_name'],
                        'contact_person': supplier.contact_person if supplier else '',
                        'phone': supplier.telephone if supplier else '',
                        'email': supplier.email if supplier else '',
                        'current': 0.0,
                        'days_31_60': 0.0,
                        'days_61_90': 0.0,
                        'days_91_120': 0.0,
                        'days_120_plus': 0.0,
                        'total_payable': 0.0
                    }
                
                # Add to appropriate aging bucket
                amount = item['outstanding_amount']
                if bucket_name == '0-30':
                    supplier_aging[supplier_id]['current'] += amount
                elif bucket_name == '31-60':
                    supplier_aging[supplier_id]['days_31_60'] += amount
                elif bucket_name == '61-90':
                    supplier_aging[supplier_id]['days_61_90'] += amount
                elif bucket_name == '91-120':
                    supplier_aging[supplier_id]['days_91_120'] += amount
                else:  # 120+
                    supplier_aging[supplier_id]['days_120_plus'] += amount
                
                supplier_aging[supplier_id]['total_payable'] += amount
        
        # Convert to list for frontend
        creditors_list = list(supplier_aging.values())
            
        return {
            'as_of_date': as_of_date,
            'total_outstanding': float(total_outstanding),
            'aging_buckets': aging_buckets,
            'bucket_totals': bucket_totals,
            'creditors': creditors_list,  # Frontend expects supplier-aggregated data
            'summary': {
                'current': float(bucket_totals.get('0-30', Decimal('0.00'))),
                'days_31_60': float(bucket_totals.get('31-60', Decimal('0.00'))),
                'days_61_90': float(bucket_totals.get('61-90', Decimal('0.00'))),
                'days_91_120': float(bucket_totals.get('91-120', Decimal('0.00'))),
                'days_120_plus': float(bucket_totals.get('120+', Decimal('0.00'))),
                'total': float(total_outstanding)
            },
            'ifrs_compliance': {
                'standard': 'IAS 1 - Presentation of Financial Statements',
                'note': 'Creditors aging for liquidity management and cash flow planning'
            }
        }
    
    def get_customer_aging_summary(self, as_of_date: date = None) -> Dict:
        """Get summary of customer aging by customer"""
        
        if as_of_date is None:
            as_of_date = date.today()
            
        customers = self.db.query(Customer).all()
        customer_summaries = []
        
        for customer in customers:
            aging_data = self.generate_debtors_aging(
                as_of_date=as_of_date,
                customer_id=customer.id
            )
            
            if aging_data['total_outstanding'] > 0:
                customer_summaries.append({
                    'customer_id': customer.id,
                    'customer_name': customer.name,
                    'total_outstanding': aging_data['total_outstanding'],
                    'aging_summary': aging_data['summary'],
                    'credit_limit': customer.credit_limit,
                    'credit_available': customer.credit_limit - aging_data['total_outstanding'] if customer.credit_limit else None,
                    'risk_rating': self._calculate_risk_rating(aging_data)
                })
        
        return {
            'as_of_date': as_of_date,
            'customers': customer_summaries,
            'total_customers': len(customer_summaries),
            'total_outstanding': sum(c['total_outstanding'] for c in customer_summaries)
        }
    
    def get_supplier_aging_summary(self, as_of_date: date = None) -> Dict:
        """Get summary of supplier aging by supplier"""
        
        if as_of_date is None:
            as_of_date = date.today()
            
        suppliers = self.db.query(Supplier).all()
        supplier_summaries = []
        
        for supplier in suppliers:
            aging_data = self.generate_creditors_aging(
                as_of_date=as_of_date,
                supplier_id=supplier.id
            )
            
            if aging_data['total_outstanding'] > 0:
                supplier_summaries.append({
                    'supplier_id': supplier.id,
                    'supplier_name': supplier.name,
                    'total_outstanding': aging_data['total_outstanding'],
                    'aging_summary': aging_data['summary'],
                    'payment_terms': supplier.payment_terms,
                    'priority_rating': self._calculate_payment_priority(aging_data)
                })
        
        return {
            'as_of_date': as_of_date,
            'suppliers': supplier_summaries,
            'total_suppliers': len(supplier_summaries),
            'total_outstanding': sum(s['total_outstanding'] for s in supplier_summaries)
        }
    
    def _calculate_risk_rating(self, aging_data: Dict) -> str:
        """Calculate customer risk rating based on aging"""
        
        total = aging_data['total_outstanding']
        if total == 0:
            return 'NO_RISK'
        
        # Use correct field names from summary
        days_120_plus = aging_data['summary']['days_120_plus']
        days_91_120 = aging_data['summary']['days_91_120']
        
        overdue_ratio = (days_120_plus + days_91_120) / total
        
        if overdue_ratio > 0.5:
            return 'HIGH_RISK'
        elif overdue_ratio > 0.2:
            return 'MEDIUM_RISK'
        else:
            return 'LOW_RISK'
    
    def _calculate_payment_priority(self, aging_data: Dict) -> str:
        """Calculate payment priority based on aging"""
        
        total = aging_data['total_outstanding']
        if total == 0:
            return 'NONE'
        
        # Use correct field names from summary
        days_120_plus = aging_data['summary']['days_120_plus']
        days_91_120 = aging_data['summary']['days_91_120']
        days_61_90 = aging_data['summary']['days_61_90']
        
        if days_120_plus > 0:
            return 'URGENT'
        elif days_91_120 > 0:
            return 'HIGH'
        elif days_61_90 > 0:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _calculate_expected_credit_loss(self, debtors_list: List[Dict]) -> Dict:
        """
        Calculate Expected Credit Loss based on IFRS 9
        Uses simplified approach for trade receivables
        """
        if not debtors_list:
            return {
                'provision_rate': 0.0,
                'total_provision': 0.0,
                'bucket_provisions': {
                    'current': 0.0,
                    'days_31_60': 0.0,
                    'days_61_90': 0.0,
                    'days_91_120': 0.0,
                    'days_120_plus': 0.0
                }
            }
        
        # IFRS 9 Expected Credit Loss rates by aging bucket
        # These rates should be based on historical loss experience
        ecl_rates = {
            'current': 0.005,      # 0.5% loss rate for current
            'days_31_60': 0.02,    # 2% loss rate for 31-60 days
            'days_61_90': 0.05,    # 5% loss rate for 61-90 days
            'days_91_120': 0.15,   # 15% loss rate for 91-120 days
            'days_120_plus': 0.50  # 50% loss rate for 120+ days
        }
        
        total_provision = 0.0
        bucket_provisions = {}
        total_outstanding = 0.0
        
        # Calculate provisions by bucket
        for bucket in ['current', 'days_31_60', 'days_61_90', 'days_91_120', 'days_120_plus']:
            bucket_total = sum(debtor[bucket] for debtor in debtors_list)
            provision = bucket_total * ecl_rates[bucket]
            bucket_provisions[bucket] = provision
            total_provision += provision
            total_outstanding += bucket_total
        
        # Calculate overall provision rate
        provision_rate = (total_provision / total_outstanding) if total_outstanding > 0 else 0.0
        
        return {
            'provision_rate': provision_rate,
            'total_provision': total_provision,
            'bucket_provisions': bucket_provisions,
            'ecl_methodology': 'IFRS 9 Simplified Approach',
            'rates_applied': ecl_rates
        }
    
    def _get_empty_creditors_aging_structure(self, as_of_date: date) -> Dict:
        """Return empty creditors aging structure when there are no purchases"""
        return {
            'as_of_date': as_of_date,
            'total_outstanding': 0.0,
            'aging_buckets': {
                '0-30': [],
                '31-60': [],
                '61-90': [],
                '91-120': [],
                '120+': []
            },
            'bucket_totals': {
                '0-30': 0.0,
                '31-60': 0.0,
                '61-90': 0.0,
                '91-120': 0.0,
                '120+': 0.0
            },
            'creditors': [],
            'summary': {
                'current': 0.0,
                'days_31_60': 0.0,
                'days_61_90': 0.0,
                'days_91_120': 0.0,
                'days_120_plus': 0.0,
                'total': 0.0
            },
            'ifrs_compliance': {
                'standard': 'IAS 1 - Presentation of Financial Statements',
                'note': 'Creditors aging for liquidity management and cash flow planning'
            }
        }
