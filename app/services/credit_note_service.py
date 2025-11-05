"""
Credit Note Service

Handles creation, processing, and management of credit notes for customer returns.
Integrates with invoice reversal system and provides proper accounting documentation.
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func
from decimal import Decimal
from datetime import date, datetime
import logging

from app.models.credit_notes import CreditNote, CreditNoteItem, RefundTransaction
from app.models.sales import Invoice, InvoiceItem, Customer, Sale, SaleItem
from app.models.accounting import AccountingEntry, JournalEntry, AccountingCode
from app.models.inventory import InventoryTransaction
from app.services.accounting_service import AccountingService
from app.services.inventory_service import InventoryService
from app.services.accounting_dimensions_service import AccountingDimensionService
# from app.core.exceptions import ValidationError, BusinessLogicError  # Not available - using Exception

logger = logging.getLogger(__name__)


class CreditNoteService:
    """Service for managing credit notes and refunds"""

    def __init__(self, db: Session):
        self.db = db
        self.accounting_service = AccountingService(db)
        self.inventory_service = InventoryService(db)
        self.dimension_service = AccountingDimensionService(db)

    def _get_account_by_name(self, name_pattern: str, account_type: Optional[str] = None) -> Optional[AccountingCode]:
        """Helper method to get accounting code by name pattern"""
        query = self.db.query(AccountingCode).filter(
            AccountingCode.name.ilike(f"%{name_pattern}%")
        )

        if account_type:
            query = query.filter(AccountingCode.account_type == account_type)

        # Get the first match (don't filter by reporting_tag since all codes have tags)
        return query.first()

    def _get_original_dimensional_assignments(self, credit_note: CreditNote) -> Dict[str, str]:
        """
        Retrieve dimensional assignments (cost center, project) from original transaction
        """
        try:
            # Find the original journal entries based on source type
            if credit_note.source_type == 'invoice':
                # For invoices, look for journal entries with the invoice reference
                source_doc = credit_note.original_invoice
                if source_doc:
                    # Search for journal entries related to this invoice
                    original_entries = self.db.query(JournalEntry).filter(
                        JournalEntry.reference.ilike(f"%{source_doc.invoice_number}%")
                    ).all()
            else:  # pos_receipt
                # For POS sales, look for journal entries with the sale reference
                source_doc = credit_note.original_sale
                if source_doc:
                    # Search for journal entries related to this sale
                    original_entries = self.db.query(JournalEntry).filter(
                        JournalEntry.reference.ilike(f"%{source_doc.id}%")
                    ).all()

            if not original_entries:
                logger.warning(f"No original journal entries found for credit note {credit_note.id}")
                return {}

            # Get dimensional assignments from the first entry (usually sales entry)
            sales_entry = None
            for entry in original_entries:
                # Look for the sales/revenue entry (credit entry to sales account)
                if entry.entry_type == 'credit' and entry.accounting_code:
                    if ('sales' in entry.accounting_code.name.lower() or
                        'revenue' in entry.accounting_code.name.lower()):
                        sales_entry = entry
                        break

            if not sales_entry:
                # Fallback to first entry
                sales_entry = original_entries[0]

            # Get dimensional assignments for this journal entry
            assignments = self.dimension_service.get_assignments(journal_entry_id=sales_entry.id)

            dimensional_data = {}
            for assignment in assignments:
                dimension = self.dimension_service.get_dimension(assignment.dimension_id)
                if dimension:
                    if dimension.code == 'DEPT' or dimension.dimension_type == 'functional':
                        dimensional_data['cost_center_id'] = assignment.dimension_value_id
                    elif dimension.code == 'PROJ' or dimension.dimension_type == 'project':
                        dimensional_data['project_id'] = assignment.dimension_value_id

            logger.info(f"Retrieved dimensional assignments for credit note {credit_note.id}: {dimensional_data}")
            return dimensional_data

        except Exception as e:
            logger.error(f"Error retrieving dimensional assignments for credit note {credit_note.id}: {str(e)}")
            return {}

    def _copy_dimensional_assignments_to_journal_entries(self, journal_entries: List[JournalEntry], dimensional_data: Dict[str, str]):
        """
        Copy dimensional assignments to credit note journal entries
        """
        try:
            if not dimensional_data:
                logger.info("No dimensional data to copy")
                return

            for journal_entry in journal_entries:
                # Flush to ensure journal entry ID is available
                self.db.flush()

                # Create dimensional assignments for each dimension
                for dimension_key, dimension_value_id in dimensional_data.items():
                    try:
                        # Determine dimension ID based on the key
                        if dimension_key == 'cost_center_id':
                            dimensions = self.dimension_service.get_dimensions()
                            dimension = next((d for d in dimensions if d.code == 'DEPT' or d.dimension_type == 'functional'), None)
                        elif dimension_key == 'project_id':
                            dimensions = self.dimension_service.get_dimensions()
                            dimension = next((d for d in dimensions if d.code == 'PROJ' or d.dimension_type == 'project'), None)
                        else:
                            continue

                        if dimension:
                            from app.schemas.accounting_dimensions import AccountingDimensionAssignmentCreate

                            assignment_data = AccountingDimensionAssignmentCreate(
                                journal_entry_id=journal_entry.id,
                                dimension_id=dimension.id,
                                dimension_value_id=dimension_value_id,
                                allocation_percentage=100.0,
                                allocation_amount=None  # Will be auto-calculated
                            )

                            self.dimension_service.create_assignment(assignment_data)
                            logger.info(f"Created dimensional assignment for journal entry {journal_entry.id}")

                    except Exception as assign_error:
                        logger.error(f"Error creating dimensional assignment for journal entry {journal_entry.id}: {str(assign_error)}")
                        # Continue with other assignments even if one fails

        except Exception as e:
            logger.error(f"Error copying dimensional assignments: {str(e)}")
            # Don't raise - dimensional assignments are supplementary

    def _validate_credit_note_dimensions(self, credit_note: CreditNote, source_doc, source_type: str):
        """
        Validate that credit note dimensions are compatible with source transaction dimensions
        """
        try:
            # Get original dimensional assignments
            original_dimensions = self._get_original_dimensional_assignments(credit_note)

            # If no override dimensions provided, we'll use original dimensions (validation passes)
            if not credit_note.cost_center_id and not credit_note.project_id:
                logger.info(f"No dimensional overrides for credit note {credit_note.id}, will use original dimensions")
                return

            # Validate cost center consistency
            if credit_note.cost_center_id:
                original_cost_center = original_dimensions.get('cost_center_id')
                if original_cost_center and original_cost_center != credit_note.cost_center_id:
                    # Get dimension value names for better error message
                    try:
                        original_cc_value = self.dimension_service.get_dimension_value(original_cost_center)
                        current_cc_value = self.dimension_service.get_dimension_value(credit_note.cost_center_id)

                        logger.warning(
                            f"Credit note {credit_note.id} cost center override: "
                            f"original={original_cc_value.name if original_cc_value else original_cost_center}, "
                            f"override={current_cc_value.name if current_cc_value else credit_note.cost_center_id}"
                        )
                    except Exception:
                        logger.warning(
                            f"Credit note {credit_note.id} cost center override: "
                            f"original={original_cost_center}, override={credit_note.cost_center_id}"
                        )

            # Validate project consistency
            if credit_note.project_id:
                original_project = original_dimensions.get('project_id')
                if original_project and original_project != credit_note.project_id:
                    # Get dimension value names for better error message
                    try:
                        original_proj_value = self.dimension_service.get_dimension_value(original_project)
                        current_proj_value = self.dimension_service.get_dimension_value(credit_note.project_id)

                        logger.warning(
                            f"Credit note {credit_note.id} project override: "
                            f"original={original_proj_value.name if original_proj_value else original_project}, "
                            f"override={current_proj_value.name if current_proj_value else credit_note.project_id}"
                        )
                    except Exception:
                        logger.warning(
                            f"Credit note {credit_note.id} project override: "
                            f"original={original_project}, override={credit_note.project_id}"
                        )

            # Additional validation: Ensure dimensional values exist and are active
            if credit_note.cost_center_id:
                cost_center_value = self.dimension_service.get_dimension_value(credit_note.cost_center_id)
                if not cost_center_value:
                    raise ValueError(f"Invalid cost center ID: {credit_note.cost_center_id}")
                if not cost_center_value.is_active:
                    raise ValueError(f"Cost center '{cost_center_value.name}' is not active")

            if credit_note.project_id:
                project_value = self.dimension_service.get_dimension_value(credit_note.project_id)
                if not project_value:
                    raise ValueError(f"Invalid project ID: {credit_note.project_id}")
                if not project_value.is_active:
                    raise ValueError(f"Project '{project_value.name}' is not active")

            logger.info(f"Dimensional validation passed for credit note {credit_note.id}")

        except Exception as e:
            logger.error(f"Dimensional validation error for credit note {credit_note.id}: {str(e)}")
            # Re-raise validation errors to prevent credit note creation
            if "Invalid" in str(e) or "not active" in str(e):
                raise
            # Log other errors but don't prevent credit note creation

    def create_credit_note_from_invoice(
        self,
        invoice_id: str,
        return_items: List[Dict[str, Any]],
        return_reason: str,
        return_description: Optional[str] = None,
        refund_method: str = 'cash',
        user_id: Optional[str] = None,
        cost_center_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> CreditNote:
        """
        Create a credit note for returned items from an invoice

        Args:
            invoice_id: Original invoice ID
            return_items: List of items being returned with quantities
            return_reason: Reason for return (faulty_product, wrong_item, etc.)
            return_description: Additional description
            refund_method: Method of refund (cash, bank_transfer, credit_adjustment, store_credit)
            user_id: User creating the credit note
            cost_center_id: Optional cost center override for dimensional accounting
            project_id: Optional project override for dimensional accounting

        Returns:
            Created credit note
        """
        return self._create_credit_note(
            source_type='invoice',
            source_id=invoice_id,
            return_items=return_items,
            return_reason=return_reason,
            return_description=return_description,
            refund_method=refund_method,
            user_id=user_id,
            cost_center_id=cost_center_id,
            project_id=project_id
        )

    def create_credit_note_from_sale(
        self,
        sale_id: str,
        return_items: List[Dict[str, Any]],
        return_reason: str,
        return_description: Optional[str] = None,
        refund_method: str = 'cash',
        user_id: Optional[str] = None,
        cost_center_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> CreditNote:
        """
        Create a credit note for returned items from a POS sale/receipt

        Args:
            sale_id: Original sale/POS receipt ID
            return_items: List of items being returned with quantities
            return_reason: Reason for return (faulty_product, wrong_item, etc.)
            return_description: Additional description
            refund_method: Method of refund (cash, bank_transfer, credit_adjustment, store_credit)
            user_id: User creating the credit note
            cost_center_id: Optional cost center override for dimensional accounting
            project_id: Optional project override for dimensional accounting

        Returns:
            Created credit note
        """
        return self._create_credit_note(
            source_type='pos_receipt',
            source_id=sale_id,
            return_items=return_items,
            return_reason=return_reason,
            return_description=return_description,
            refund_method=refund_method,
            user_id=user_id,
            cost_center_id=cost_center_id,
            project_id=project_id
        )

    def _create_credit_note(
        self,
        source_type: str,
        source_id: str,
        return_items: List[Dict[str, Any]],
        return_reason: str,
        return_description: Optional[str] = None,
        refund_method: str = 'cash',
        user_id: Optional[str] = None,
        cost_center_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> CreditNote:
        """
        Internal method to create a credit note from either invoice or POS receipt

        Args:
            source_type: 'invoice' or 'pos_receipt'
            source_id: ID of source document
            return_items: List of items being returned with quantities
            return_reason: Reason for return
            return_description: Additional description
            refund_method: Method of refund
            user_id: User creating the credit note

        Returns:
            Created credit note
        """
        try:
            # Get source document (invoice or sale)
            if source_type == 'invoice':
                source_doc = self.db.query(Invoice).filter(Invoice.id == source_id).first()
                if not source_doc:
                    raise Exception(f"Invoice {source_id} not found")
                if source_doc.status == 'cancelled':
                    raise Exception("Cannot create credit note for cancelled invoice")
                customer_id = source_doc.customer_id
                branch_id = source_doc.branch_id

                # If invoice has no branch, get default branch
                if not branch_id:
                    from app.models.branch import Branch
                    default_branch = self.db.query(Branch).first()
                    if not default_branch:
                        raise Exception("No branches found in system - cannot create credit note")
                    branch_id = default_branch.id
                    logger.info(f"Invoice has no branch - using default branch {default_branch.name}")

            elif source_type == 'pos_receipt':
                source_doc = self.db.query(Sale).filter(Sale.id == source_id).first()
                if not source_doc:
                    raise Exception(f"Sale/POS Receipt {source_id} not found")
                if source_doc.status == 'cancelled':
                    raise Exception("Cannot create credit note for cancelled sale")
                customer_id = source_doc.customer_id
                branch_id = source_doc.branch_id

                # If sale has no branch, get default branch
                if not branch_id:
                    from app.models.branch import Branch
                    default_branch = self.db.query(Branch).first()
                    if not default_branch:
                        raise Exception("No branches found in system - cannot create credit note")
                    branch_id = default_branch.id
                    logger.info(f"Sale has no branch - using default branch {default_branch.name}")
            else:
                raise Exception(f"Invalid source_type: {source_type}")

            # Generate credit note number
            credit_note_number = self._generate_credit_note_number()

            # Create credit note
            credit_note = CreditNote(
                credit_note_number=credit_note_number,
                source_type=source_type,
                source_id=source_id,
                original_invoice_id=source_id if source_type == 'invoice' else None,
                original_sale_id=source_id if source_type == 'pos_receipt' else None,
                customer_id=customer_id,
                branch_id=branch_id,
                return_reason=return_reason,
                return_description=return_description,
                refund_method=refund_method,
                created_by=user_id,
                status='draft',
                cost_center_id=cost_center_id,
                project_id=project_id
            )

            self.db.add(credit_note)
            self.db.flush()  # Get the ID

            # Process return items
            total_amount = Decimal('0.00')
            total_vat = Decimal('0.00')
            total_discount = Decimal('0.00')

            for item_data in return_items:
                credit_note_item, item_total, item_vat, item_discount = self._create_credit_note_item(
                    credit_note.id,
                    item_data,
                    source_doc,
                    source_type
                )
                total_amount += item_total
                total_vat += item_vat
                total_discount += item_discount

            # Update credit note totals
            credit_note.subtotal = total_amount - total_vat
            credit_note.vat_amount = total_vat
            credit_note.discount_amount = total_discount
            credit_note.total_amount = total_amount

            # DIMENSIONAL VALIDATION: Validate dimensional assignments if provided
            self._validate_credit_note_dimensions(credit_note, source_doc, source_type)

            # CRITICAL VALIDATION: Ensure credit note doesn't exceed original document total
            original_total = source_doc.total_amount if source_type == 'invoice' else source_doc.total

            # Get sum of all existing credit notes for this document
            existing_credit_notes_total = self.db.query(
                func.sum(CreditNote.total_amount)
            ).filter(
                and_(
                    CreditNote.source_id == source_id,
                    CreditNote.source_type == source_type,
                    CreditNote.status.in_(['draft', 'issued'])  # Include draft and issued
                )
            ).scalar() or Decimal('0.00')

            # Add current credit note total
            total_credit_notes = existing_credit_notes_total + total_amount

            if total_credit_notes > original_total:
                self.db.rollback()
                raise Exception(
                    f"Credit note total ({total_amount}) plus existing credit notes ({existing_credit_notes_total}) "
                    f"= {total_credit_notes} exceeds original document total of {original_total}. "
                    f"Maximum refundable amount is {original_total - existing_credit_notes_total}."
                )

            self.db.commit()

            source_ref = source_doc.invoice_number if source_type == 'invoice' else f"Sale-{source_doc.id[:8]}"
            logger.info(f"Created credit note {credit_note_number} for {source_type} {source_ref}")
            return credit_note

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating credit note: {str(e)}")
            raise

    def _create_credit_note_item(
        self,
        credit_note_id: str,
        item_data: Dict[str, Any],
        source_document,
        source_type: str
    ) -> Tuple[CreditNoteItem, Decimal, Decimal, Decimal]:
        """Create a credit note item and return totals"""

        product_id = item_data['product_id']
        quantity_returned = Decimal(str(item_data['quantity_returned']))
        item_condition = item_data.get('item_condition', 'unopened')
        item_return_reason = item_data.get('return_reason', 'customer_request')
        description = item_data.get('description', '')

        # Find original item based on source type
        if source_type == 'invoice':
            original_item = self.db.query(InvoiceItem).filter(
                and_(
                    InvoiceItem.invoice_id == source_document.id,
                    InvoiceItem.product_id == product_id
                )
            ).first()

            if not original_item:
                raise Exception(f"Product {product_id} not found in original invoice")

            if quantity_returned > original_item.quantity:
                raise Exception(f"Cannot return more than original quantity for product {product_id}")

            unit_price = original_item.price
            discount_percentage = Decimal('0.00')  # Invoice items don't have discount_percentage
            vat_rate = Decimal('0.00')  # Will calculate from vat_amount if needed
            original_item_id = original_item.id
            original_sale_item_id = None

        else:  # pos_receipt
            original_item = self.db.query(SaleItem).filter(
                and_(
                    SaleItem.sale_id == source_document.id,
                    SaleItem.product_id == product_id
                )
            ).first()

            if not original_item:
                raise Exception(f"Product {product_id} not found in original sale")

            if quantity_returned > original_item.quantity:
                raise Exception(f"Cannot return more than original quantity for product {product_id}")

            unit_price = original_item.selling_price
            discount_percentage = original_item.discount_percentage or Decimal('0.00')
            vat_rate = original_item.vat_rate or Decimal('0.00')
            original_item_id = None
            original_sale_item_id = original_item.id

        # Calculate amounts
        gross_amount = quantity_returned * unit_price
        discount_amount = gross_amount * (discount_percentage / 100)
        discounted_amount = gross_amount - discount_amount
        vat_amount = discounted_amount * (vat_rate / 100)
        line_total = discounted_amount + vat_amount

        # Create credit note item
        credit_note_item = CreditNoteItem(
            credit_note_id=credit_note_id,
            product_id=product_id,
            original_invoice_item_id=original_item_id,
            original_sale_item_id=original_sale_item_id,
            quantity_returned=quantity_returned,
            unit_price=unit_price,
            discount_percentage=discount_percentage,
            discount_amount=discount_amount,
            vat_rate=vat_rate,
            vat_amount=vat_amount,
            line_total=line_total,
            item_condition=item_condition,
            return_reason=item_return_reason,
            description=description
        )

        self.db.add(credit_note_item)

        return credit_note_item, line_total, vat_amount, discount_amount

    def approve_credit_note(self, credit_note_id: str, user_id: str) -> CreditNote:
        """Approve a credit note and create accounting entries"""

        credit_note = self.db.query(CreditNote).filter(CreditNote.id == credit_note_id).first()
        if not credit_note:
            raise Exception(f"Credit note {credit_note_id} not found")

        if credit_note.status != 'draft':
            raise Exception(f"Credit note {credit_note.credit_note_number} is not in draft status")

        try:
            # Create reversal accounting entries
            accounting_entry = self._create_credit_note_accounting_entries(credit_note, user_id)

            # Update inventory
            self._update_inventory_for_returns(credit_note)

            # Update credit note status
            credit_note.status = 'issued'
            credit_note.approved_by = user_id
            credit_note.reversal_accounting_entry_id = accounting_entry.id
            credit_note.updated_at = datetime.now()

            self.db.commit()

            logger.info(f"Approved credit note {credit_note.credit_note_number}")
            return credit_note

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error approving credit note: {str(e)}")
            raise

    def process_refund(
        self,
        credit_note_id: str,
        refund_details: Dict[str, Any],
        user_id: str
    ) -> RefundTransaction:
        """Process the actual refund payment"""

        credit_note = self.db.query(CreditNote).filter(CreditNote.id == credit_note_id).first()
        if not credit_note:
            raise Exception(f"Credit note {credit_note_id} not found")

        if credit_note.status != 'issued':
            raise Exception(f"Credit note {credit_note.credit_note_number} must be issued before processing refund")

        try:
            # Create refund transaction
            refund_transaction = RefundTransaction(
                credit_note_id=credit_note_id,
                refund_method=credit_note.refund_method,
                refund_amount=credit_note.total_amount,
                bank_account_id=refund_details.get('bank_account_id'),
                cash_account_id=refund_details.get('cash_account_id'),
                reference_number=refund_details.get('reference_number'),
                customer_bank_name=refund_details.get('customer_bank_name'),
                customer_account_number=refund_details.get('customer_account_number'),
                customer_account_name=refund_details.get('customer_account_name'),
                transfer_reference=refund_details.get('transfer_reference'),
                processed_by=user_id
            )

            self.db.add(refund_transaction)
            self.db.flush()

            # Create accounting entry for refund
            refund_accounting_entry = self._create_refund_accounting_entries(
                credit_note, refund_transaction, user_id
            )

            refund_transaction.accounting_entry_id = refund_accounting_entry.id
            refund_transaction.status = 'processed'
            refund_transaction.processed_date = datetime.now()

            # Update credit note
            credit_note.refund_status = 'processed'
            credit_note.refund_processed_date = date.today()
            credit_note.refund_reference = refund_details.get('reference_number')
            credit_note.status = 'processed'
            credit_note.processed_by = user_id

            self.db.commit()

            logger.info(f"Processed refund for credit note {credit_note.credit_note_number}")
            return refund_transaction

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error processing refund: {str(e)}")
            raise

    def _create_credit_note_accounting_entries(
        self, credit_note: CreditNote, user_id: str
    ) -> AccountingEntry:
        """Create accounting entries for credit note (sales reversal)"""

        # Get source document reference
        if credit_note.source_type == 'invoice':
            source_doc = credit_note.original_invoice
            source_ref = f"Invoice {source_doc.invoice_number}"
            payment_method = source_doc.payment_method if hasattr(source_doc, 'payment_method') else 'credit'
        else:  # pos_receipt
            source_doc = credit_note.original_sale
            source_ref = f"POS Sale {source_doc.id[:8]}"
            payment_method = source_doc.payment_method or 'cash'

        # Create accounting entry header first
        accounting_entry_header = AccountingEntry(
            date_prepared=date.today(),
            date_posted=date.today(),
            particulars=f"Credit note for return - {source_ref}",
            book="Sales Journal - Credit Notes",
            status="posted",
            branch_id=credit_note.branch_id
        )

        self.db.add(accounting_entry_header)
        self.db.flush()

        # Get accounting codes for credit note entries
        sales_returns_code = self._get_account_by_name("Sales Returns")
        if not sales_returns_code:
            # Fallback to Sales account (will credit it)
            sales_returns_code = self._get_account_by_name("Sales")

        vat_output_code = self._get_account_by_name("VAT") if credit_note.vat_amount > 0 else None

        if payment_method == 'cash':
            receivables_code = self._get_account_by_name("Accounts Payable")  # Customer refunds payable
        else:
            receivables_code = self._get_account_by_name("Accounts Receivable")

        if not sales_returns_code or not receivables_code:
            raise Exception("Required accounting codes not found. Please ensure Sales Returns and Accounts Receivable accounts exist.")

        # Debit: Sales Returns (or Sales Returns and Allowances)
        sales_returns_entry = JournalEntry(
            accounting_entry_id=accounting_entry_header.id,
            accounting_code_id=sales_returns_code.id,
            entry_type='debit',
            debit_amount=credit_note.subtotal,  # Sales amount without VAT
            credit_amount=Decimal('0.00'),
            description=f"Sales return - Credit Note {credit_note.credit_note_number} - {credit_note.return_reason}",
            narration=f"Sales return - Credit Note {credit_note.credit_note_number}",
            reference=f"CN-{credit_note.credit_note_number}",
            date=date.today(),
            date_posted=date.today(),
            branch_id=credit_note.branch_id,
            created_by_user_id=user_id,
            origin="credit_note"
        )

        self.db.add(sales_returns_entry)

        # Debit: VAT Output (reverse VAT charged on original sale)
        if credit_note.vat_amount > 0:
            vat_entry = JournalEntry(
                accounting_entry_id=accounting_entry_header.id,
                accounting_code_id=vat_output_code.id,
                entry_type='debit',
                debit_amount=credit_note.vat_amount,
                credit_amount=Decimal('0.00'),
                description=f"VAT reversal - Credit Note {credit_note.credit_note_number}",
                narration=f"VAT reversal - Credit Note {credit_note.credit_note_number}",
                reference=f"CN-{credit_note.credit_note_number}",
                date=date.today(),
                date_posted=date.today(),
                branch_id=credit_note.branch_id,
                created_by_user_id=user_id,
                origin="credit_note"
            )
            self.db.add(vat_entry)

        # Credit: Accounts Receivable or Customer Refunds Payable (depending on original payment method)
        if payment_method == 'cash':
            description = f"Refund liability - Credit Note {credit_note.credit_note_number}"
        else:
            description = f"Customer credit adjustment - Credit Note {credit_note.credit_note_number}"

        receivables_entry = JournalEntry(
            accounting_entry_id=accounting_entry_header.id,
            accounting_code_id=receivables_code.id,
            entry_type='credit',
            debit_amount=Decimal('0.00'),
            credit_amount=credit_note.total_amount,
            description=description,
            narration=description,
            reference=f"CN-{credit_note.credit_note_number}",
            date=date.today(),
            date_posted=date.today(),
            branch_id=credit_note.branch_id,
            created_by_user_id=user_id,
            origin="credit_note"
        )

        self.db.add(receivables_entry)

        # Copy dimensional assignments from original transaction
        dimensional_data = self._get_original_dimensional_assignments(credit_note)

        # Store dimensional data in credit note for reference
        if dimensional_data:
            if 'cost_center_id' in dimensional_data:
                credit_note.cost_center_id = dimensional_data['cost_center_id']
            if 'project_id' in dimensional_data:
                credit_note.project_id = dimensional_data['project_id']

        # Create dimensional assignments for all journal entries
        journal_entries = [sales_returns_entry, receivables_entry]
        if credit_note.vat_amount > 0:
            journal_entries.append(vat_entry)

        self._copy_dimensional_assignments_to_journal_entries(journal_entries, dimensional_data)

        return accounting_entry_header

    def _create_refund_accounting_entries(
        self, credit_note: CreditNote, refund_transaction: RefundTransaction, user_id: str
    ) -> AccountingEntry:
        """
        Create accounting entries for actual refund payment

        Proper double-entry bookkeeping for each refund method:

        1. Cash Refund:
           DR: Customer Refunds Payable (Liability)
           CR: Cash on Hand (Asset)

        2. Bank Transfer:
           DR: Customer Refunds Payable (Liability)
           CR: Bank Account (Asset)

        3. Credit Adjustment (no cash movement):
           DR: Customer Refunds Payable (Liability)
           CR: Accounts Receivable (Asset)

        4. Store Credit:
           DR: Customer Refunds Payable (Liability)
           CR: Store Credit Liability (Liability)
        """

        # Create accounting entry header
        accounting_entry_header = AccountingEntry(
            date_prepared=date.today(),
            date_posted=date.today(),
            particulars=f"Refund payment for credit note {credit_note.credit_note_number} via {refund_transaction.refund_method}",
            book="Cash Book - Refunds",
            status="posted",
            branch_id=credit_note.branch_id
        )

        self.db.add(accounting_entry_header)
        self.db.flush()

        # Get accounting codes
        liability_code = self._get_account_by_name("Accounts Payable")  # Customer refunds payable

        if not liability_code:
            raise Exception("Accounts Payable account not found. Cannot process refund.")

        # DR: Customer Refunds Payable (always debited to clear the liability)
        liability_entry = JournalEntry(
            accounting_entry_id=accounting_entry_header.id,
            accounting_code_id=liability_code.id,
            entry_type='debit',
            debit_amount=refund_transaction.refund_amount,
            credit_amount=Decimal('0.00'),
            description=f"Clear refund liability - Credit Note {credit_note.credit_note_number}",
            narration=f"Clear refund liability - Credit Note {credit_note.credit_note_number}",
            reference=f"REF-{credit_note.credit_note_number}",
            date=date.today(),
            date_posted=date.today(),
            branch_id=credit_note.branch_id,
            created_by_user_id=user_id,
            origin="refund"
        )

        self.db.add(liability_entry)

        # CR: Credit the appropriate account based on refund method
        if refund_transaction.refund_method == 'cash':
            # Cash refund - reduce cash on hand
            account_code = self._get_account_by_name("Cash")
            if not account_code:
                account_code = self._get_account_by_name("Petty Cash")
            particulars = f"Cash refund paid - Credit Note {credit_note.credit_note_number}"

        elif refund_transaction.refund_method == 'bank_transfer':
            # Bank transfer - reduce bank account balance
            if refund_transaction.bank_account_id:
                account_code = self.db.query(AccountingCode).filter(AccountingCode.id == refund_transaction.bank_account_id).first()
            else:
                account_code = self._get_account_by_name("Bank")
            particulars = f"Bank transfer refund - Credit Note {credit_note.credit_note_number}"
            if refund_transaction.transfer_reference:
                particulars += f" (Ref: {refund_transaction.transfer_reference})"

        elif refund_transaction.refund_method == 'credit_adjustment':
            # Credit adjustment - reduce accounts receivable (customer owes less)
            account_code = self._get_account_by_name("Accounts Receivable")
            particulars = f"Credit adjustment against customer account - Credit Note {credit_note.credit_note_number}"

        elif refund_transaction.refund_method == 'store_credit':
            # Store credit - create liability for future purchases
            account_code = self._get_account_by_name("Accounts Payable")  # Store credit liability
            particulars = f"Store credit issued - Credit Note {credit_note.credit_note_number}"

        else:
            # Fallback for unknown refund methods
            account_code = self._get_account_by_name("Cash")
            particulars = f"Refund processed ({refund_transaction.refund_method}) - Credit Note {credit_note.credit_note_number}"

        if not account_code:
            raise Exception(f"Could not find appropriate accounting code for refund method: {refund_transaction.refund_method}")

        # Create the credit entry
        refund_entry = JournalEntry(
            accounting_entry_id=accounting_entry_header.id,
            accounting_code_id=account_code.id,
            entry_type='credit',
            debit_amount=Decimal('0.00'),
            credit_amount=refund_transaction.refund_amount,
            description=particulars,
            narration=particulars,
            reference=f"REF-{credit_note.credit_note_number}",
            date=date.today(),
            date_posted=date.today(),
            branch_id=credit_note.branch_id,
            created_by_user_id=user_id,
            origin="refund"
        )

        self.db.add(refund_entry)

        # Copy dimensional assignments from credit note if available
        dimensional_data = {}
        if credit_note.cost_center_id:
            dimensional_data['cost_center_id'] = credit_note.cost_center_id
        if credit_note.project_id:
            dimensional_data['project_id'] = credit_note.project_id

        # If no dimensional data in credit note, try to get from original transaction
        if not dimensional_data:
            dimensional_data = self._get_original_dimensional_assignments(credit_note)

        # Create dimensional assignments for refund journal entries
        journal_entries = [liability_entry, refund_entry]
        self._copy_dimensional_assignments_to_journal_entries(journal_entries, dimensional_data)

        logger.info(
            f"Created refund accounting entries for credit note {credit_note.credit_note_number}: "
            f"{refund_transaction.refund_method} refund of {refund_transaction.refund_amount}"
        )

        return accounting_entry_header

    def _update_inventory_for_returns(self, credit_note: CreditNote):
        """Update inventory for returned items"""
        from app.models.inventory import Product

        for item in credit_note.credit_note_items:
            # Get the product to update stock
            product = self.db.query(Product).filter(Product.id == item.product_id).first()

            if not product:
                logger.warning(f"Product {item.product_id} not found for inventory update")
                continue

            # Only add back to inventory if item is in good condition
            if item.item_condition in ['unopened', 'good']:
                transaction_type = 'return'
                # Add quantity back to stock
                product.quantity = (product.quantity or 0) + int(item.quantity_returned)
            else:
                transaction_type = 'write_off'
                # Don't add damaged items back to stock

            # Create inventory transaction record
            inventory_transaction = InventoryTransaction(
                product_id=item.product_id,
                transaction_type=transaction_type,
                quantity=int(item.quantity_returned),
                unit_cost=float(item.unit_price),
                reference=f"Credit Note {credit_note.credit_note_number}",
                note=f"Return from customer - {item.return_reason} ({item.item_condition})",
                branch_id=credit_note.branch_id,
                date=date.today()
            )

            self.db.add(inventory_transaction)

            logger.info(
                f"Created inventory {transaction_type} transaction for product {item.product_id}: "
                f"{item.quantity_returned} units"
            )

    def _generate_credit_note_number(self) -> str:
        """Generate unique credit note number"""

        today = date.today()
        prefix = f"CN{today.strftime('%Y%m')}"

        # Get the next sequence number for this month
        last_credit_note = self.db.query(CreditNote).filter(
            CreditNote.credit_note_number.like(f"{prefix}%")
        ).order_by(desc(CreditNote.credit_note_number)).first()

        if last_credit_note:
            last_number = int(last_credit_note.credit_note_number[-4:])
            next_number = last_number + 1
        else:
            next_number = 1

        return f"{prefix}{next_number:04d}"

    def get_credit_note_by_id(self, credit_note_id: str) -> Optional[CreditNote]:
        """Get credit note by ID with all relationships"""
        return self.db.query(CreditNote).filter(CreditNote.id == credit_note_id).first()

    def get_customer_credit_notes(self, customer_id: str) -> List[CreditNote]:
        """Get all credit notes for a customer"""
        return self.db.query(CreditNote).filter(CreditNote.customer_id == customer_id).all()

    def get_pending_refunds(self) -> List[CreditNote]:
        """Get credit notes with pending refunds"""
        return self.db.query(CreditNote).filter(
            and_(
                CreditNote.status == 'issued',
                CreditNote.refund_status == 'pending'
            )
        ).all()
