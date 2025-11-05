"""
Invoice Reversal Service

This service handles the complete reversal of invoices for customer returns,
including journal entry reversals and inventory adjustments.
"""

from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from datetime import datetime, date
from decimal import Decimal
import uuid

from app.models.sales import Invoice, InvoiceItem
from app.models.inventory import Product, InventoryTransaction
from app.models.accounting import JournalEntry, AccountingEntry, AccountingCode
from app.services.invoice_service import InvoiceService
from app.core.database import get_db


class InvoiceReversalService:
    """Service for reversing invoices and their associated transactions"""
    
    def __init__(self, db: Session):
        self.db = db
        self.invoice_service = InvoiceService(db)
    
    def reverse_invoice(
        self, 
        invoice_id: str, 
        reversal_reason: str = "Customer Return",
        created_by: str = None
    ) -> Dict:
        """
        Complete invoice reversal including:
        - Journal entry reversals
        - Inventory quantity restoration
        - Invoice status update
        """
        
        # Get the original invoice
        original_invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not original_invoice:
            raise ValueError("Invoice not found")
        
        if original_invoice.status == 'reversed':
            raise ValueError("Invoice is already reversed")
        
        # Create reversal accounting entry
        reversal_entry = self._create_reversal_accounting_entries(
            original_invoice, 
            reversal_reason,
            created_by
        )
        
        # Restore inventory quantities
        inventory_adjustments = self._restore_inventory_quantities(
            original_invoice,
            reversal_reason
        )
        
        # Update original invoice status
        original_invoice.status = 'reversed'
        original_invoice.updated_at = datetime.now()
        if created_by:
            original_invoice.updated_by = created_by
        
        self.db.commit()
        
        return {
            'original_invoice_id': invoice_id,
            'reversal_accounting_entry_id': reversal_entry.id,
            'inventory_adjustments': inventory_adjustments,
            'status': 'success',
            'message': f'Invoice {original_invoice.invoice_number} successfully reversed'
        }
    
    def _create_reversal_accounting_entries(
        self, 
        original_invoice: Invoice, 
        reversal_reason: str,
        created_by: str = None
    ) -> AccountingEntry:
        """Create journal entries that reverse the original invoice entries"""
        
        # Create reversal accounting entry header
        reversal_entry = AccountingEntry(
            date_prepared=date.today(),
            date_posted=date.today(),
            particulars=f"Reversal of Invoice {original_invoice.invoice_number} - {reversal_reason}",
            book="Sales Journal - Reversals",
            status="posted",
            branch_id=original_invoice.branch_id
        )
        self.db.add(reversal_entry)
        self.db.flush()  # Get accounting entry ID
        
        # Get accounting codes (same as original invoice creation)
        accounts_receivable = self.db.query(AccountingCode).filter(
            AccountingCode.code == "1200"  # Accounts Receivable
        ).first()
        
        sales_revenue = self.db.query(AccountingCode).filter(
            AccountingCode.code == "4000"  # Sales Revenue
        ).first()
        
        vat_payable = self.db.query(AccountingCode).filter(
            AccountingCode.code == "2300"  # VAT Payable
        ).first()
        
        cogs_account = self.db.query(AccountingCode).filter(
            AccountingCode.code == "5100"  # Cost of Goods Sold
        ).first()
        
        inventory_account = self.db.query(AccountingCode).filter(
            AccountingCode.code == "1140"  # Inventory
        ).first()
        
        # Calculate total COGS for reversal
        total_cogs = Decimal('0.00')
        for item in original_invoice.invoice_items:
            product = self.db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                line_cost = (product.cost_price or 0) * item.quantity
                total_cogs += Decimal(str(line_cost))
        
        # REVERSAL ENTRIES (opposite of original)
        
        # 1. Credit: Accounts Receivable (originally debited)
        if accounts_receivable:
            reversal_ar_entry = JournalEntry(
                accounting_entry_id=reversal_entry.id,
                accounting_code_id=accounts_receivable.id,
                entry_type="credit",
                narration=f"Reversal - Invoice {original_invoice.invoice_number} - {reversal_reason}",
                debit_amount=0.0,
                credit_amount=float(original_invoice.total_amount),
                description=f"Customer return - reverse accounts receivable",
                reference=f"REV-{original_invoice.invoice_number}",
                date=date.today(),
                branch_id=original_invoice.branch_id
            )
            self.db.add(reversal_ar_entry)
        
        # 2. Debit: Sales Revenue (originally credited)
        if sales_revenue:
            reversal_sales_entry = JournalEntry(
                accounting_entry_id=reversal_entry.id,
                accounting_code_id=sales_revenue.id,
                entry_type="debit",
                narration=f"Reversal - Sales Revenue - Invoice {original_invoice.invoice_number}",
                debit_amount=float(original_invoice.subtotal),
                credit_amount=0.0,
                description="Reverse sales revenue for return",
                reference=f"REV-{original_invoice.invoice_number}",
                date=date.today(),
                branch_id=original_invoice.branch_id
            )
            self.db.add(reversal_sales_entry)
        
        # 3. Debit: VAT Payable (originally credited)
        if vat_payable and original_invoice.total_vat_amount > 0:
            reversal_vat_entry = JournalEntry(
                accounting_entry_id=reversal_entry.id,
                accounting_code_id=vat_payable.id,
                entry_type="debit",
                narration=f"Reversal - VAT on Invoice {original_invoice.invoice_number}",
                debit_amount=float(original_invoice.total_vat_amount),
                credit_amount=0.0,
                description="Reverse VAT payable for return",
                reference=f"REV-{original_invoice.invoice_number}",
                date=date.today(),
                branch_id=original_invoice.branch_id
            )
            self.db.add(reversal_vat_entry)
        
        # 4. Reverse COGS and Inventory entries
        if total_cogs > 0 and cogs_account and inventory_account:
            # Credit COGS (originally debited)
            reversal_cogs_entry = JournalEntry(
                accounting_entry_id=reversal_entry.id,
                accounting_code_id=cogs_account.id,
                entry_type="credit",
                narration=f"Reversal - COGS for Invoice {original_invoice.invoice_number}",
                debit_amount=0.0,
                credit_amount=float(total_cogs),
                description="Reverse cost of goods sold for return",
                reference=f"REV-{original_invoice.invoice_number}",
                date=date.today(),
                branch_id=original_invoice.branch_id
            )
            self.db.add(reversal_cogs_entry)
            
            # Debit Inventory (originally credited)
            reversal_inv_entry = JournalEntry(
                accounting_entry_id=reversal_entry.id,
                accounting_code_id=inventory_account.id,
                entry_type="debit",
                narration=f"Reversal - Inventory restoration for Invoice {original_invoice.invoice_number}",
                debit_amount=float(total_cogs),
                credit_amount=0.0,
                description="Restore inventory for returned items",
                reference=f"REV-{original_invoice.invoice_number}",
                date=date.today(),
                branch_id=original_invoice.branch_id
            )
            self.db.add(reversal_inv_entry)
        
        return reversal_entry
    
    def _restore_inventory_quantities(
        self, 
        original_invoice: Invoice,
        reversal_reason: str
    ) -> List[Dict]:
        """Restore inventory quantities for returned items"""
        
        inventory_adjustments = []
        
        for item in original_invoice.invoice_items:
            product = self.db.query(Product).filter(Product.id == item.product_id).first()
            if not product:
                continue
            
            # Store previous quantity for tracking
            previous_quantity = product.quantity or 0
            
            # Restore the quantity that was reduced during the original sale
            product.quantity = (product.quantity or 0) + item.quantity
            
            # Create inventory transaction record for the return
            return_transaction = InventoryTransaction(
                product_id=product.id,
                transaction_type='return',
                quantity=item.quantity,  # Positive quantity for return
                unit_cost=product.cost_price or 0,
                total_cost=(product.cost_price or 0) * item.quantity,
                date=date.today(),
                reference=f"Return - Invoice {original_invoice.invoice_number}",
                branch_id=original_invoice.branch_id,
                previous_quantity=previous_quantity,
                new_quantity=product.quantity
            )
            self.db.add(return_transaction)
            
            inventory_adjustments.append({
                'product_id': product.id,
                'product_name': product.name,
                'quantity_returned': item.quantity,
                'previous_quantity': previous_quantity,
                'new_quantity': product.quantity,
                'unit_cost': product.cost_price or 0
            })
        
        return inventory_adjustments
    
    def reverse_and_recreate_invoice(
        self,
        original_invoice_id: str,
        new_invoice_data: Dict,
        reversal_reason: str = "Customer Return - Recreate with Updates",
        created_by: str = None
    ) -> Dict:
        """
        Reverse original invoice and create a new one with updated formatting/items
        """
        
        # First, reverse the original invoice
        reversal_result = self.reverse_invoice(
            original_invoice_id,
            reversal_reason,
            created_by
        )
        
        # Create new invoice with updated data
        new_invoice = self.invoice_service.create_invoice(
            customer_id=new_invoice_data['customer_id'],
            branch_id=new_invoice_data['branch_id'],
            invoice_items=new_invoice_data['invoice_items'],
            due_date=new_invoice_data.get('due_date'),
            payment_terms=new_invoice_data.get('payment_terms', 30),
            discount_percentage=new_invoice_data.get('discount_percentage', 0.0),
            notes=new_invoice_data.get('notes', ''),
            created_by=created_by
        )
        
        # Add reference to the reversed invoice in notes
        original_invoice = self.db.query(Invoice).filter(Invoice.id == original_invoice_id).first()
        if original_invoice:
            reference_note = f"Replaces reversed invoice {original_invoice.invoice_number}"
            new_invoice.notes = f"{new_invoice.notes}\n{reference_note}" if new_invoice.notes else reference_note
        
        self.db.commit()
        
        return {
            'reversal_result': reversal_result,
            'new_invoice': {
                'id': new_invoice.id,
                'invoice_number': new_invoice.invoice_number,
                'total_amount': float(new_invoice.total_amount),
                'status': new_invoice.status
            },
            'status': 'success',
            'message': f'Invoice reversed and recreated successfully'
        }
    
    def get_invoice_reversal_summary(self, invoice_id: str) -> Dict:
        """Get summary of what would be reversed for an invoice"""
        
        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError("Invoice not found")
        
        # Calculate totals that would be reversed
        total_cogs = Decimal('0.00')
        items_summary = []
        
        for item in invoice.invoice_items:
            product = self.db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                line_cost = (product.cost_price or 0) * item.quantity
                total_cogs += Decimal(str(line_cost))
                
                items_summary.append({
                    'product_name': product.name,
                    'quantity': item.quantity,
                    'unit_price': float(item.price),
                    'line_total': float(item.total),
                    'current_stock': product.quantity or 0,
                    'stock_after_return': (product.quantity or 0) + item.quantity,
                    'cost_impact': float(line_cost)
                })
        
        return {
            'invoice_number': invoice.invoice_number,
            'customer_id': invoice.customer_id,
            'total_amount': float(invoice.total_amount),
            'subtotal': float(invoice.subtotal),
            'vat_amount': float(invoice.total_vat_amount),
            'total_cogs': float(total_cogs),
            'items': items_summary,
            'accounting_entries_to_reverse': {
                'accounts_receivable': float(invoice.total_amount),
                'sales_revenue': float(invoice.subtotal),
                'vat_payable': float(invoice.total_vat_amount),
                'cost_of_goods_sold': float(total_cogs),
                'inventory': float(total_cogs)
            }
        }
