from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from app.models.banking import BankAccount, BankTransaction, BankTransfer, BankReconciliation, ReconciliationItem
from app.models.accounting import AccountingCode, AccountingEntry, JournalEntry
from app.core.config import settings


class BankingService:
    """Comprehensive banking business logic service"""

    TRANSACTION_TYPES = [
        'deposit', 'withdrawal', 'transfer', 'payment', 'receipt',
        'bank_charge', 'interest', 'reversal'
    ]

    def __init__(self, db: Session):
        self.db = db

    def create_bank_account(self, account_data: Dict, branch_id: str) -> Tuple[BankAccount, Dict]:
        """Create a new bank account"""
        try:
            # Validate account number uniqueness
            existing_account = self.db.query(BankAccount).filter(
                and_(
                    BankAccount.account_number == account_data['account_number'],
                    BankAccount.branch_id == branch_id
                )
            ).first()

            if existing_account:
                return None, {'success': False, 'error': 'Account number already exists'}

            # Get accounting code for bank account
            accounting_code = self.db.query(AccountingCode).filter(
                AccountingCode.id == account_data['accounting_code_id']
            ).first()

            if not accounting_code:
                return None, {'success': False, 'error': 'Accounting code not found'}

            # Create bank account
            bank_account = BankAccount(
                name=account_data['name'],
                institution=account_data['institution'],
                account_number=account_data['account_number'],
                currency=account_data.get('currency', 'USD'),
                account_type=account_data['account_type'],
                accounting_code_id=accounting_code.id,
                branch_id=branch_id
            )

            self.db.add(bank_account)
            self.db.commit()
            self.db.refresh(bank_account)

            # Note: Opening balance transactions can be created separately if needed

            return bank_account, {'success': True, 'account_id': str(bank_account.id)}

        except Exception as e:
            self.db.rollback()
            return None, {'success': False, 'error': str(e)}

    def update_bank_account(self, account_id: str, update_data: Dict) -> Dict:
        """Update a bank account"""
        try:
            # Find the bank account
            bank_account = self.db.query(BankAccount).filter(BankAccount.id == account_id).first()

            if not bank_account:
                return {'success': False, 'error': 'Bank account not found'}

            # If updating account number, check for uniqueness
            if 'account_number' in update_data and update_data['account_number'] != bank_account.account_number:
                existing_account = self.db.query(BankAccount).filter(
                    and_(
                        BankAccount.account_number == update_data['account_number'],
                        BankAccount.branch_id == bank_account.branch_id,
                        BankAccount.id != account_id
                    )
                ).first()

                if existing_account:
                    return {'success': False, 'error': 'Account number already exists'}

            # If updating accounting code, validate it exists
            if 'accounting_code_id' in update_data:
                accounting_code = self.db.query(AccountingCode).filter(
                    AccountingCode.id == update_data['accounting_code_id']
                ).first()

                if not accounting_code:
                    return {'success': False, 'error': 'Accounting code not found'}

            # Update the fields
            for field, value in update_data.items():
                if hasattr(bank_account, field):
                    setattr(bank_account, field, value)

            self.db.commit()
            self.db.refresh(bank_account)

            return {'success': True, 'account': bank_account}

        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def delete_bank_account(self, account_id: str) -> Dict:
        """Delete a bank account"""
        try:
            # Find the bank account with accounting code loaded
            bank_account = self.db.query(BankAccount).options(
                joinedload(BankAccount.accounting_code)
            ).filter(BankAccount.id == account_id).first()

            if not bank_account:
                return {'success': False, 'error': 'Bank account not found'}

            # Check if there are any transactions for this account
            transactions = self.db.query(BankTransaction).filter(
                BankTransaction.bank_account_id == account_id
            ).count()

            if transactions > 0:
                return {'success': False, 'error': f'Cannot delete bank account with {transactions} existing transactions'}

            # Check if there are any transfers involving this account
            transfers = self.db.query(BankTransfer).filter(
                or_(
                    BankTransfer.source_account_id == account_id,
                    BankTransfer.destination_account_id == account_id
                )
            ).count()

            if transfers > 0:
                return {'success': False, 'error': f'Cannot delete bank account with {transfers} existing transfers'}

            # Check if there are any reconciliations for this account
            reconciliations = self.db.query(BankReconciliation).filter(
                BankReconciliation.bank_account_id == account_id
            ).count()

            if reconciliations > 0:
                return {'success': False, 'error': f'Cannot delete bank account with {reconciliations} existing reconciliations'}

            # Start a transaction
            try:
                # Delete the bank account only (don't delete the accounting code)
                self.db.delete(bank_account)

                self.db.commit()
                return {'success': True, 'message': 'Bank account deleted successfully'}

            except Exception as e:
                self.db.rollback()
                return {'success': False, 'error': f'Database error while deleting: {str(e)}'}

        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def _create_opening_balance_transaction(self, bank_account: BankAccount) -> None:
        """Create opening balance transaction"""
        transaction = BankTransaction(
            bank_account_id=bank_account.id,
            transaction_type='deposit',
            amount=Decimal('0'),  # Opening balance will be set by the service
            description='Opening balance',
            date=date.today(),
            reference='Opening balance'
        )

        self.db.add(transaction)
        self.db.commit()

    def create_bank_transaction(self, transaction_data: Dict, branch_id: str) -> Tuple[BankTransaction, Dict]:
        """Create a bank transaction with accounting entries"""
        try:
            bank_account = self.db.query(BankAccount).filter(
                BankAccount.id == transaction_data['bank_account_id']
            ).first()

            if not bank_account:
                return None, {'success': False, 'error': 'Bank account not found'}

            # Create bank transaction
            transaction = BankTransaction(
                bank_account_id=bank_account.id,
                transaction_type=transaction_data['transaction_type'],
                amount=Decimal(transaction_data['amount']),
                description=transaction_data['description'],
                date=transaction_data.get('date', date.today()),
                reference=transaction_data.get('reference'),
                vat_amount=Decimal(transaction_data.get('vat_amount', 0)),
                destination_bank_account_id=transaction_data.get('destination_bank_account_id')
            )

            self.db.add(transaction)
            self.db.commit()
            self.db.refresh(transaction)

            # Create accounting entries
            self._create_banking_accounting_entries(transaction, bank_account, branch_id)

            return transaction, {'success': True, 'transaction_id': str(transaction.id)}

        except Exception as e:
            self.db.rollback()
            return None, {'success': False, 'error': str(e)}

    def _update_bank_balance(self, bank_account: BankAccount, transaction: BankTransaction) -> None:
        """Update bank account balance based on transaction"""
        # Note: Balance is calculated dynamically from transactions
        # This method is kept for future implementation if needed
        pass

    def _create_banking_accounting_entries(self, transaction: BankTransaction, bank_account: BankAccount, branch_id: str) -> None:
        """Create accounting entries for bank transaction"""
        try:
            # Get required accounting codes
            bank_account_code = self.db.query(AccountingCode).filter(
                AccountingCode.id == bank_account.accounting_code_id
            ).first()

            if not bank_account_code:
                raise Exception("Bank account accounting code not found")

            # Determine the other account based on transaction type
            if transaction.transaction_type in ['deposit', 'receipt']:
                # For deposits/receipts, debit bank account, credit cash or revenue
                other_account = self._get_accounting_code('Cash in Hand', 'Asset', branch_id)
                if not other_account:
                    other_account = self._get_accounting_code('Cash and Cash Equivalents', 'Asset', branch_id)
                bank_entry_type = 'debit'
                other_entry_type = 'credit'
            else:
                # For withdrawals/payments, credit bank account, debit cash or expense
                other_account = self._get_accounting_code('Cash in Hand', 'Asset', branch_id)
                if not other_account:
                    other_account = self._get_accounting_code('Cash and Cash Equivalents', 'Asset', branch_id)
                bank_entry_type = 'credit'
                other_entry_type = 'debit'

            # Create accounting entry
            accounting_entry = AccountingEntry(
                date_prepared=transaction.date,
                date_posted=transaction.date,
                particulars=f"Bank transaction: {transaction.description}",
                book=f"BANK-{transaction.id}",
                status='posted',
                branch_id=branch_id
            )

            self.db.add(accounting_entry)
            self.db.flush()

            # Create journal entries
            # Bank account entry
            bank_journal_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=bank_account_code.id,
                entry_type=bank_entry_type,
                debit_amount=transaction.amount if bank_entry_type == 'debit' else 0,
                credit_amount=transaction.amount if bank_entry_type == 'credit' else 0,
                description=f"Bank transaction: {transaction.description}",
                date=transaction.date,
                date_posted=transaction.date,
                branch_id=branch_id
            )

            # Other account entry
            other_journal_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=other_account.id,
                entry_type=other_entry_type,
                debit_amount=transaction.amount if other_entry_type == 'debit' else 0,
                credit_amount=transaction.amount if other_entry_type == 'credit' else 0,
                description=f"Bank transaction: {transaction.description}",
                date=transaction.date,
                date_posted=transaction.date,
                branch_id=branch_id
            )

            self.db.add(bank_journal_entry)
            self.db.add(other_journal_entry)
            self.db.commit()

            # Update accounting code balances
            from app.services.accounting_service import AccountingService
            accounting_service = AccountingService(self.db)
            accounting_service.update_accounting_code_balance(bank_account_code.id)
            accounting_service.update_accounting_code_balance(other_account.id)

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to create accounting entries: {str(e)}")

    def _get_accounting_code(self, name: str, account_type: str, branch_id: str) -> AccountingCode:
        """Get accounting code by name and type"""
        code = self.db.query(AccountingCode).filter(
            and_(
                AccountingCode.name == name,
                AccountingCode.account_type == account_type,
                AccountingCode.branch_id == branch_id
            )
        ).first()

        if not code:
            raise ValueError(f"Accounting code '{name}' ({account_type}) not found")

        return code

    def create_bank_transfer(self, transfer_data: Dict, branch_id: str) -> Tuple[BankTransfer, Dict]:
        """Create a bank transfer between accounts"""
        try:
            from_account = self.db.query(BankAccount).filter(
                BankAccount.id == transfer_data['source_account_id']
            ).first()

            to_account = self.db.query(BankAccount).filter(
                BankAccount.id == transfer_data['destination_account_id']
            ).first()

            if not from_account or not to_account:
                return None, {'success': False, 'error': 'One or both bank accounts not found'}

            if from_account.id == to_account.id:
                return None, {'success': False, 'error': 'Cannot transfer to the same account'}

            # Check sufficient balance (calculate dynamically)
            # Note: Balance checking would need to be implemented based on transaction history

            # Create bank transfer
            transfer = BankTransfer(
                source_account_id=from_account.id,
                destination_account_id=to_account.id,
                amount=Decimal(transfer_data['amount']),
                transfer_type=transfer_data['transfer_type'],
                reference=transfer_data['reference'],
                description=transfer_data['description'],
                status='pending',
                vat_amount=Decimal(transfer_data.get('vat_amount', 0)),
                transfer_fee=Decimal(transfer_data.get('transfer_fee', 0)),
                beneficiary_id=transfer_data.get('beneficiary_id')
            )

            self.db.add(transfer)
            self.db.flush()

            # Create bank transactions for both accounts
            from_transaction = BankTransaction(
                bank_account_id=from_account.id,
                transaction_type='withdrawal',
                amount=transfer.amount,
                description=f"Transfer to {to_account.name}",
                date=date.today(),
                reference=transfer.reference,
                destination_bank_account_id=to_account.id
            )

            to_transaction = BankTransaction(
                bank_account_id=to_account.id,
                transaction_type='deposit',
                amount=transfer.amount,
                description=f"Transfer from {from_account.name}",
                date=date.today(),
                reference=transfer.reference,
                destination_bank_account_id=from_account.id
            )

            self.db.add(from_transaction)
            self.db.add(to_transaction)

            # Create accounting entries
            self._create_transfer_accounting_entries(transfer, from_account, to_account)

            self.db.commit()
            self.db.refresh(transfer)

            return transfer, {'success': True, 'transfer_id': str(transfer.id)}

        except Exception as e:
            self.db.rollback()
            return None, {'success': False, 'error': str(e)}

    def _create_transfer_accounting_entries(self, transfer: BankTransfer,
                                          from_account: BankAccount,
                                          to_account: BankAccount) -> None:
        """Create accounting entries for bank transfer"""
        try:
            # Use the branch_id from the source account; require it to exist (no default fallback)
            branch_id = from_account.branch_id
            if not branch_id:
                raise Exception("Source bank account missing branch context; cannot create transfer entries")
            transfer_date = getattr(transfer, 'transfer_date', date.today())

            # Create accounting entry
            accounting_entry = AccountingEntry(
                date_prepared=date.today(),
                date_posted=date.today(),
                particulars=f"Bank transfer: {transfer.description}",
                book=f"TRANSFER-{transfer.id}",
                status='posted',
                branch_id=branch_id
            )

            self.db.add(accounting_entry)
            self.db.flush()

            # Create journal entries
            # Debit destination account
            debit_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=to_account.accounting_code_id,
                entry_type='debit',
                debit_amount=transfer.amount,
                credit_amount=0,
                description=f"Transfer to {to_account.name}",
                date=transfer_date,
                date_posted=transfer_date,
                branch_id=branch_id
            )

            # Credit source account
            credit_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=from_account.accounting_code_id,
                entry_type='credit',
                debit_amount=0,
                credit_amount=transfer.amount,
                description=f"Transfer from {from_account.name}",
                date=transfer_date,
                date_posted=transfer_date,
                branch_id=branch_id
            )

            self.db.add(debit_entry)
            self.db.add(credit_entry)
            self.db.commit()

            # Update accounting code balances
            from app.services.accounting_service import AccountingService
            accounting_service = AccountingService(self.db)
            accounting_service.update_accounting_code_balance(to_account.accounting_code_id)
            accounting_service.update_accounting_code_balance(from_account.accounting_code_id)

        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to create transfer accounting entries: {str(e)}")

    def create_bank_reconciliation(self, reconciliation_data: Dict, branch_id: str) -> Tuple[BankReconciliation, Dict]:
        """Create bank reconciliation"""
        try:
            bank_account = self.db.query(BankAccount).filter(
                and_(
                    BankAccount.id == reconciliation_data['bank_account_id'],
                    BankAccount.branch_id == branch_id
                )
            ).first()

            if not bank_account:
                return None, {'success': False, 'error': 'Bank account not found'}

            # Create reconciliation
            reconciliation = BankReconciliation(
                bank_account_id=bank_account.id,
                reconciliation_date=reconciliation_data['reconciliation_date'],
                bank_statement_balance=Decimal(reconciliation_data['bank_statement_balance']),
                book_balance=bank_account.current_balance,
                difference=Decimal(reconciliation_data['bank_statement_balance']) - bank_account.current_balance,
                status='open',
                notes=reconciliation_data.get('notes'),
                branch_id=branch_id
            )

            self.db.add(reconciliation)
            self.db.commit()
            self.db.refresh(reconciliation)

            return reconciliation, {'success': True, 'reconciliation_id': str(reconciliation.id)}

        except Exception as e:
            self.db.rollback()
            return None, {'success': False, 'error': str(e)}

    def add_reconciliation_item(self, item_data: Dict, reconciliation_id: str) -> Tuple[ReconciliationItem, Dict]:
        """Add item to bank reconciliation"""
        try:
            reconciliation = self.db.query(BankReconciliation).filter(
                BankReconciliation.id == reconciliation_id
            ).first()

            if not reconciliation:
                return None, {'success': False, 'error': 'Reconciliation not found'}

            # Create reconciliation item
            item = ReconciliationItem(
                bank_reconciliation_id=reconciliation_id,
                bank_transaction_id=item_data.get('bank_transaction_id'),
                statement_description=item_data['description'],
                statement_amount=Decimal(item_data['amount']),
                statement_date=item_data['date'],
                statement_reference=item_data.get('reference'),
                book_amount=item_data.get('book_amount'),
                book_date=item_data.get('book_date'),
                book_description=item_data.get('book_description'),
                book_reference=item_data.get('book_reference')
            )

            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)

            return item, {'success': True, 'item_id': str(item.id)}

        except Exception as e:
            self.db.rollback()
            return None, {'success': False, 'error': str(e)}

    def reconcile_transaction(self, transaction_id: str, reconciliation_data: Dict) -> Dict:
        """Reconcile a specific bank transaction with bank statement data"""
        try:
            # Get the transaction
            transaction = self.db.query(BankTransaction).filter(
                BankTransaction.id == transaction_id
            ).first()

            if not transaction:
                return {'success': False, 'error': 'Transaction not found'}

            # Mark transaction as reconciled
            transaction.reconciled = True

            # Create reconciliation item if reconciliation_id is provided
            if 'reconciliation_id' in reconciliation_data:
                reconciliation_item = ReconciliationItem(
                    bank_reconciliation_id=reconciliation_data['reconciliation_id'],
                    bank_transaction_id=transaction_id,
                    statement_description=reconciliation_data.get('statement_description', transaction.description),
                    statement_amount=Decimal(reconciliation_data.get('statement_amount', transaction.amount)),
                    statement_date=reconciliation_data.get('statement_date', transaction.date),
                    statement_reference=reconciliation_data.get('statement_reference', transaction.reference),
                    book_amount=transaction.amount,
                    book_date=transaction.date,
                    book_description=transaction.description,
                    book_reference=transaction.reference
                )
                self.db.add(reconciliation_item)

            # If this is a bank-initiated transaction (charges, fees, VAT), create accounting entries
            if reconciliation_data.get('is_bank_initiated', False):
                self._create_bank_initiated_accounting_entries(transaction, reconciliation_data)

            self.db.commit()

            return {'success': True, 'transaction_id': transaction_id}

        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def _create_bank_initiated_accounting_entries(self, transaction: BankTransaction, reconciliation_data: Dict) -> None:
        """Create accounting entries for bank-initiated transactions (charges, fees, VAT)"""
        try:
            # Get bank account
            bank_account = self.db.query(BankAccount).filter(
                BankAccount.id == transaction.bank_account_id
            ).first()

            if not bank_account:
                raise Exception("Bank account not found")

            # Get required accounting codes
            bank_account_code = self.db.query(AccountingCode).filter(
                AccountingCode.id == bank_account.accounting_code_id
            ).first()

            if not bank_account_code:
                raise Exception("Bank account accounting code not found")

            # Determine the expense account based on transaction type
            expense_account = None
            if 'bank_charge' in transaction.transaction_type.lower():
                expense_account = self._get_accounting_code('Bank Charges', 'Expense', bank_account.branch_id)
            elif 'transfer_fee' in transaction.transaction_type.lower():
                expense_account = self._get_accounting_code('Transfer Fees', 'Expense', bank_account.branch_id)
            elif 'vat' in transaction.transaction_type.lower():
                expense_account = self._get_accounting_code('VAT on Banking', 'Expense', bank_account.branch_id)
            else:
                expense_account = self._get_accounting_code('Banking Expenses', 'Expense', bank_account.branch_id)

            if not expense_account:
                # Fallback to general expenses
                expense_account = self._get_accounting_code('General Expenses', 'Expense', bank_account.branch_id)

            # Create accounting entry
            accounting_entry = AccountingEntry(
                date_prepared=transaction.date,
                date_posted=transaction.date,
                particulars=f"Bank reconciliation: {transaction.description}",
                book=f"BANK-REC-{transaction.id}",
                status='posted',
                branch_id=bank_account.branch_id
            )

            self.db.add(accounting_entry)
            self.db.flush()

            # Create journal entries
            # Bank account entry (credit - money going out)
            bank_journal_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=bank_account_code.id,
                entry_type='credit',
                debit_amount=0,
                credit_amount=transaction.amount,
                description=f"Bank reconciliation: {transaction.description}",
                date=transaction.date,
                date_posted=transaction.date,
                branch_id=bank_account.branch_id
            )

            # Expense account entry (debit - expense incurred)
            expense_journal_entry = JournalEntry(
                accounting_entry_id=accounting_entry.id,
                accounting_code_id=expense_account.id,
                entry_type='debit',
                debit_amount=transaction.amount,
                credit_amount=0,
                description=f"Bank reconciliation: {transaction.description}",
                date=transaction.date,
                date_posted=transaction.date,
                branch_id=bank_account.branch_id
            )

            self.db.add(bank_journal_entry)
            self.db.add(expense_journal_entry)

            # Link transaction to accounting entry
            transaction.accounting_entry_id = accounting_entry.id

        except Exception as e:
            raise Exception(f"Error creating bank-initiated accounting entries: {str(e)}")

    def bulk_reconcile_transactions(self, reconciliation_data: Dict) -> Dict:
        """Bulk reconcile multiple transactions"""
        try:
            transaction_ids = reconciliation_data.get('transaction_ids', [])
            reconciliation_id = reconciliation_data.get('reconciliation_id')

            reconciled_count = 0
            errors = []

            for transaction_id in transaction_ids:
                result = self.reconcile_transaction(transaction_id, {
                    'reconciliation_id': reconciliation_id,
                    'is_bank_initiated': reconciliation_data.get('is_bank_initiated', False)
                })

                if result['success']:
                    reconciled_count += 1
                else:
                    errors.append(f"Transaction {transaction_id}: {result['error']}")

            # Update reconciliation status if reconciliation_id is provided
            if reconciliation_id:
                reconciliation = self.db.query(BankReconciliation).filter(
                    BankReconciliation.id == reconciliation_id
                ).first()

                if reconciliation:
                    reconciliation.status = 'completed'
                    reconciliation.completed_at = datetime.now()
                    reconciliation.reconciled_at = datetime.now()

            self.db.commit()

            return {
                'success': True,
                'reconciled_count': reconciled_count,
                'total_count': len(transaction_ids),
                'errors': errors
            }

        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def get_unreconciled_transactions(self, account_id: str = None) -> List[Dict]:
        """Get all unreconciled transactions"""
        query = self.db.query(BankTransaction).filter(BankTransaction.reconciled == False)

        if account_id:
            query = query.filter(BankTransaction.bank_account_id == account_id)

        transactions = query.all()

        return [
            {
                'id': str(transaction.id),
                'bank_account_id': transaction.bank_account_id,
                'date': transaction.date,
                'amount': float(transaction.amount) if transaction.amount else None,
                'description': transaction.description,
                'transaction_type': transaction.transaction_type,
                'reference': transaction.reference,
                'vat_amount': float(transaction.vat_amount) if transaction.vat_amount else None,
                'created_at': transaction.created_at
            }
            for transaction in transactions
        ]

    def get_reconciliation_summary(self, account_id: str = None) -> Dict:
        """Get reconciliation summary for an account"""
        query = self.db.query(BankTransaction)

        if account_id:
            query = query.filter(BankTransaction.bank_account_id == account_id)

        all_transactions = query.all()
        reconciled_transactions = [t for t in all_transactions if t.reconciled]
        unreconciled_transactions = [t for t in all_transactions if not t.reconciled]

        total_amount = sum(float(t.amount) for t in all_transactions if t.amount)
        reconciled_amount = sum(float(t.amount) for t in reconciled_transactions if t.amount)
        unreconciled_amount = sum(float(t.amount) for t in unreconciled_transactions if t.amount)

        return {
            'total_transactions': len(all_transactions),
            'reconciled_transactions': len(reconciled_transactions),
            'unreconciled_transactions': len(unreconciled_transactions),
            'total_amount': total_amount,
            'reconciled_amount': reconciled_amount,
            'unreconciled_amount': unreconciled_amount,
            'reconciliation_percentage': (len(reconciled_transactions) / len(all_transactions) * 100) if all_transactions else 0
        }

    def get_reconciliation_statistics(self) -> Dict:
        """Get overall reconciliation statistics"""
        try:
            # Get all reconciliations
            reconciliations = self.db.query(BankReconciliation).all()

            # Count by status
            reconciled_count = len([r for r in reconciliations if r.status == 'completed'])
            pending_count = len([r for r in reconciliations if r.status == 'open'])
            discrepancy_count = len([r for r in reconciliations if r.status == 'discrepancy'])

            # Get current month reconciliations
            current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_count = len([r for r in reconciliations if r.created_at >= current_month])

            return {
                'reconciled_count': reconciled_count,
                'pending_count': pending_count,
                'discrepancies_count': discrepancy_count,
                'monthly_count': monthly_count,
                'total_reconciliations': len(reconciliations)
            }
        except Exception as e:
            return {
                'reconciled_count': 0,
                'pending_count': 0,
                'discrepancies_count': 0,
                'monthly_count': 0,
                'total_reconciliations': 0
            }

    def get_reconciliation_details(self, reconciliation_id: str) -> Dict:
        """Get detailed reconciliation information"""
        try:
            reconciliation = self.db.query(BankReconciliation).filter(
                BankReconciliation.id == reconciliation_id
            ).first()

            if not reconciliation:
                return {'success': False, 'error': 'Reconciliation not found'}

            # Get bank account details
            bank_account = self.db.query(BankAccount).filter(
                BankAccount.id == reconciliation.bank_account_id
            ).first()

            # Get reconciliation items
            items = self.db.query(ReconciliationItem).filter(
                ReconciliationItem.bank_reconciliation_id == reconciliation_id
            ).all()

            # Get unreconciled transactions for this account
            unreconciled_transactions = self.db.query(BankTransaction).filter(
                and_(
                    BankTransaction.bank_account_id == reconciliation.bank_account_id,
                    BankTransaction.reconciled == False
                )
            ).all()

            return {
                'success': True,
                'reconciliation': {
                    'id': reconciliation.id,
                    'bank_account_id': reconciliation.bank_account_id,
                    'bank_account_name': bank_account.name if bank_account else 'Unknown',
                    'bank_account_number': bank_account.account_number if bank_account else 'Unknown',
                    'statement_date': reconciliation.statement_date,
                    'statement_balance': float(reconciliation.statement_balance) if reconciliation.statement_balance else None,
                    'book_balance': float(reconciliation.book_balance) if reconciliation.book_balance else None,
                    'difference': float(reconciliation.difference) if reconciliation.difference else None,
                    'status': reconciliation.status,
                    'notes': reconciliation.notes,
                    'started_at': reconciliation.started_at,
                    'completed_at': reconciliation.completed_at,
                    'reconciled_at': reconciliation.reconciled_at
                },
                'items': [
                    {
                        'id': item.id,
                        'bank_transaction_id': item.bank_transaction_id,
                        'statement_description': item.statement_description,
                        'statement_amount': float(item.statement_amount) if item.statement_amount else None,
                        'statement_date': item.statement_date,
                        'statement_reference': item.statement_reference,
                        'book_amount': float(item.book_amount) if item.book_amount else None,
                        'book_date': item.book_date,
                        'book_description': item.book_description,
                        'book_reference': item.book_reference
                    }
                    for item in items
                ],
                'unreconciled_transactions': [
                    {
                        'id': transaction.id,
                        'date': transaction.date,
                        'description': transaction.description,
                        'amount': float(transaction.amount) if transaction.amount else None,
                        'transaction_type': transaction.transaction_type,
                        'reference': transaction.reference
                    }
                    for transaction in unreconciled_transactions
                ]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def complete_reconciliation(self, reconciliation_id: str, completion_data: Dict) -> Dict:
        """Complete a bank reconciliation"""
        try:
            reconciliation = self.db.query(BankReconciliation).filter(
                BankReconciliation.id == reconciliation_id
            ).first()

            if not reconciliation:
                return {'success': False, 'error': 'Reconciliation not found'}

            # Update reconciliation status
            reconciliation.status = 'completed'
            reconciliation.completed_at = datetime.now()
            reconciliation.reconciled_at = datetime.now()
            reconciliation.notes = completion_data.get('notes', reconciliation.notes)

            # If there's a final difference, update it
            if 'final_difference' in completion_data:
                reconciliation.difference = Decimal(completion_data['final_difference'])

            self.db.commit()

            return {'success': True, 'reconciliation_id': reconciliation_id}

        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def get_bank_account_balance(self, account_id: str, as_of_date: date = None) -> Decimal:
        """Get bank account balance as of a specific date using proper accounting logic"""
        account = self.db.query(BankAccount).filter(BankAccount.id == account_id).first()

        if not account:
            return Decimal('0')

        # Use accounting service to calculate proper balance
        from app.services.accounting_service import AccountingService
        accounting_service = AccountingService(self.db)

        # Calculate balance using accounting logic for the linked accounting code
        balance = accounting_service.get_account_balance(account.accounting_code_id, as_of_date)

        return balance

    def get_banking_summary(self, branch_id: str) -> Dict:
        """Get comprehensive banking summary"""
        bank_accounts = self.db.query(BankAccount).filter(BankAccount.branch_id == branch_id).all()

        # Calculate total balance from all accounts
        total_balance = sum(self.get_bank_account_balance(account.id) for account in bank_accounts)
        total_accounts = len(bank_accounts)

        # Get recent transactions
        recent_transactions = self.db.query(BankTransaction).join(BankAccount).filter(
            BankAccount.branch_id == branch_id
        ).order_by(BankTransaction.date.desc()).limit(10).all()

        return {
            'total_balance': float(total_balance),
            'total_accounts': total_accounts,
            'accounts': [
                {
                    'id': str(account.id),
                    'name': account.name,
                    'account_number': account.account_number,
                    'bank_name': account.institution,
                    'current_balance': float(self.get_bank_account_balance(account.id)),
                    'currency': account.currency
                }
                for account in bank_accounts
            ],
            'recent_transactions': [
                {
                    'id': str(transaction.id),
                    'account_name': transaction.bank_account.name,
                    'transaction_type': transaction.transaction_type,
                    'amount': float(transaction.amount),
                    'description': transaction.description,
                    'date': transaction.date
                }
                for transaction in recent_transactions
            ]
        }

    def get_bank_statement(self, account_id: str, start_date: date, end_date: date) -> List[Dict]:
        """Get bank statement for a period"""
        transactions = self.db.query(BankTransaction).filter(
            and_(
                BankTransaction.bank_account_id == account_id,
                BankTransaction.date >= start_date,
                BankTransaction.date <= end_date
            )
        ).order_by(BankTransaction.date, BankTransaction.created_at).all()

        running_balance = self.get_bank_account_balance(account_id, start_date - date.resolution)

        statement = []
        for transaction in transactions:
            if transaction.transaction_type in ['deposit', 'receipt']:
                running_balance += transaction.amount
            else:
                running_balance -= transaction.amount

            statement.append({
                'date': transaction.date,
                'description': transaction.description,
                'reference': transaction.reference,
                'debit': float(transaction.amount) if transaction.transaction_type not in ['deposit', 'receipt'] else 0,
                'credit': float(transaction.amount) if transaction.transaction_type in ['deposit', 'receipt'] else 0,
                'balance': float(running_balance)
            })

        return statement

    def reconcile_reconciliation_items(self, reconciliation_id: str, reconciliation_data: Dict) -> Dict:
        """Enhanced reconciliation with manual entries and bank-initiated transactions"""
        try:
            reconciliation = self.db.query(BankReconciliation).filter(
                BankReconciliation.id == reconciliation_id
            ).first()

            if not reconciliation:
                return {'success': False, 'error': 'Reconciliation not found'}

            if reconciliation.status != 'open':
                return {'success': False, 'error': 'Reconciliation is not open for editing'}

            # Process selected transactions
            transaction_ids = reconciliation_data.get('transaction_ids', [])
            for transaction_id in transaction_ids:
                transaction = self.db.query(BankTransaction).filter(
                    BankTransaction.id == transaction_id
                ).first()

                if transaction and not transaction.reconciled:
                    transaction.reconciled = True
                    transaction.reconciled_at = datetime.now()

                    # Create reconciliation item
                    reconciliation_item = ReconciliationItem(
                        bank_reconciliation_id=reconciliation_id,
                        bank_transaction_id=transaction_id,
                        statement_description=transaction.description,
                        statement_amount=transaction.amount,
                        statement_date=transaction.date,
                        statement_reference=transaction.reference,
                        book_amount=transaction.amount,
                        book_date=transaction.date,
                        book_description=transaction.description,
                        book_reference=transaction.reference
                    )
                    self.db.add(reconciliation_item)

            # Process manual entries
            manual_entries = reconciliation_data.get('manual_entries', [])
            for entry in manual_entries:
                # Create reconciliation item for manual entry
                reconciliation_item = ReconciliationItem(
                    bank_reconciliation_id=reconciliation_id,
                    statement_description=entry['description'],
                    statement_amount=Decimal(str(entry['amount'])),
                    statement_date=datetime.strptime(entry['date'], '%Y-%m-%d').date(),
                    statement_reference=entry['type'],
                    book_amount=Decimal('0'),
                    book_date=datetime.now().date(),
                    book_description='Manual entry',
                    book_reference='MANUAL'
                )
                self.db.add(reconciliation_item)

                # If it's a bank-initiated transaction, create accounting entries
                if entry['type'] in ['bank_charge', 'vat', 'transfer_fee', 'deposit_fee', 'interest']:
                    self._create_bank_initiated_accounting_entries(
                        reconciliation.bank_account_id,
                        entry['description'],
                        Decimal(str(entry['amount'])),
                        entry['type']
                    )

            # Process bank-initiated transaction types
            bank_initiated_types = reconciliation_data.get('bank_initiated_types', [])
            if bank_initiated_types:
                # This could trigger additional processing for specific transaction types
                pass

            self.db.commit()

            return {'success': True, 'reconciliation_id': reconciliation_id}

        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def save_reconciliation_draft(self, reconciliation_id: str, draft_data: Dict) -> Dict:
        """Save reconciliation draft with selected transactions and manual entries"""
        try:
            reconciliation = self.db.query(BankReconciliation).filter(
                BankReconciliation.id == reconciliation_id
            ).first()

            if not reconciliation:
                return {'success': False, 'error': 'Reconciliation not found'}

            # Store draft data in meta_data field
            reconciliation.meta_data = {
                'draft_data': draft_data,
                'draft_saved_at': datetime.now().isoformat()
            }

            self.db.commit()

            return {'success': True, 'reconciliation_id': reconciliation_id}

        except Exception as e:
            self.db.rollback()
            return {'success': False, 'error': str(e)}

    def _create_bank_initiated_accounting_entries(self, bank_account_id: str, description: str, amount: Decimal, transaction_type: str):
        """Create accounting entries for bank-initiated transactions"""
        try:
            bank_account = self.db.query(BankAccount).filter(
                BankAccount.id == bank_account_id
            ).first()

            if not bank_account:
                return

            # Get appropriate expense account based on transaction type
            expense_account_code = None
            if transaction_type == 'bank_charge':
                expense_account_code = 'BANK_CHARGES'
            elif transaction_type == 'vat':
                expense_account_code = 'VAT_EXPENSE'
            elif transaction_type == 'transfer_fee':
                expense_account_code = 'TRANSFER_FEES'
            elif transaction_type == 'deposit_fee':
                expense_account_code = 'DEPOSIT_FEES'
            elif transaction_type == 'interest':
                expense_account_code = 'INTEREST_INCOME'

            if not expense_account_code:
                return

            # Find the expense account
            expense_account = self.db.query(AccountingCode).filter(
                AccountingCode.code == expense_account_code
            ).first()

            if not expense_account:
                # Create a default expense account if it doesn't exist
                expense_account = AccountingCode(
                    name=f"{transaction_type.replace('_', ' ').title()} Account",
                    code=expense_account_code,
                    account_type='expense',
                    description=f"Account for {transaction_type.replace('_', ' ')} transactions"
                )
                self.db.add(expense_account)
                self.db.flush()

            # Create journal entry
            journal_entry = JournalEntry(
                reference=f"Bank {transaction_type.replace('_', ' ').title()}",
                description=description,
                date=datetime.now().date(),
                branch_id=bank_account.branch_id
            )
            self.db.add(journal_entry)
            self.db.flush()

            # Create accounting entries
            if transaction_type == 'interest':
                # Interest is income, so credit income account, debit bank
                self.db.add(AccountingEntry(
                    journal_entry_id=journal_entry.id,
                    accounting_code_id=expense_account.id,
                    debit_amount=Decimal('0'),
                    credit_amount=amount,
                    description=description
                ))

                self.db.add(AccountingEntry(
                    journal_entry_id=journal_entry.id,
                    accounting_code_id=bank_account.accounting_code_id,
                    debit_amount=amount,
                    credit_amount=Decimal('0'),
                    description=description
                ))
            else:
                # Other transactions are expenses, so debit expense account, credit bank
                self.db.add(AccountingEntry(
                    journal_entry_id=journal_entry.id,
                    accounting_code_id=expense_account.id,
                    debit_amount=amount,
                    credit_amount=Decimal('0'),
                    description=description
                ))

                self.db.add(AccountingEntry(
                    journal_entry_id=journal_entry.id,
                    accounting_code_id=bank_account.accounting_code_id,
                    debit_amount=Decimal('0'),
                    credit_amount=amount,
                    description=description
                ))

        except Exception as e:
            print(f"Error creating bank-initiated accounting entries: {e}")
            # Don't raise exception to avoid breaking the main reconciliation process


# ============================================================================
# PHASE 4: DIMENSIONAL ACCOUNTING METHODS - Banking Module
# ============================================================================
# These methods implement GL posting and reconciliation with dimensional
# tracking for the Banking module. They follow the pattern established in
# Phases 1-3 (Manufacturing, Sales/Purchases, COGS).
# ============================================================================


    async def post_bank_transaction_to_accounting(
        self,
        bank_transaction_id: str,
        user_id: str
    ) -> Dict:
        """
        Post bank transaction to GL with dimensional tracking.

        Creates 2 GL entries (always balanced):
        - Transaction type dependent (deposit/withdrawal/transfer)
        - All dimensions inherited from source
        - Double-posting prevention
        - Full audit trail

        Args:
            bank_transaction_id: ID of bank transaction to post
            user_id: User posting the transaction

        Returns:
            {
                'success': bool,
                'bank_transaction_id': str,
                'gl_entries': [{'id', 'account_id', 'debit', 'credit', 'dimensions'}],
                'posting_status': 'posted'|'error',
                'error_message': str (if error)
            }
        """
        try:
            # 1. VALIDATE INPUT
            transaction = self.db.query(BankTransaction).filter(
                BankTransaction.id == bank_transaction_id
            ).first()

            if not transaction:
                return {
                    'success': False,
                    'error': 'Bank transaction not found',
                    'error_code': 'NOT_FOUND'
                }

            # Check if already posted
            if hasattr(transaction, 'posting_status') and transaction.posting_status == 'posted':
                return {
                    'success': False,
                    'error': 'Transaction already posted',
                    'error_code': 'ALREADY_POSTED',
                    'existing_gl_entries': []
                }

            # Validate dimensions exist if present
            if hasattr(transaction, 'cost_center_id') and transaction.cost_center_id:
                from app.models.accounting_dimensions import AccountingDimensionValue
                cc = self.db.query(AccountingDimensionValue).filter(
                    AccountingDimensionValue.id == transaction.cost_center_id
                ).first()
                if not cc:
                    return {
                        'success': False,
                        'error': f'Cost center not found',
                        'error_code': 'INVALID_DIMENSION'
                    }

            # 2. CREATE GL ENTRIES (Entry 1: DEBIT side)
            from app.models.accounting import GLEntry
            import uuid

            gl_entry_1 = GLEntry(
                id=str(uuid.uuid4()),
                account_id=transaction.bank_account_id,
                debit_amount=transaction.amount if transaction.transaction_type != 'withdrawal' else Decimal(0),
                credit_amount=transaction.amount if transaction.transaction_type == 'withdrawal' else Decimal(0),
                posting_date=date.today(),
                posting_period=self._get_posting_period(),
                reference=transaction.reference or f"BANK-{transaction.id[:8]}",
                description=f"Bank {transaction.transaction_type}",
                created_by=user_id,
                created_at=datetime.utcnow(),
                transaction_id=transaction.id
            )

            # Entry 2: CREDIT side
            gl_entry_2 = GLEntry(
                id=str(uuid.uuid4()),
                account_id=transaction.destination_bank_account_id or transaction.bank_account_id,
                debit_amount=transaction.amount if transaction.transaction_type == 'withdrawal' else Decimal(0),
                credit_amount=transaction.amount if transaction.transaction_type != 'withdrawal' else Decimal(0),
                posting_date=date.today(),
                posting_period=self._get_posting_period(),
                reference=transaction.reference or f"BANK-{transaction.id[:8]}",
                description=f"Bank {transaction.transaction_type}",
                created_by=user_id,
                created_at=datetime.utcnow(),
                transaction_id=transaction.id
            )

            # Verify GL balance (debit = credit)
            total_debit = gl_entry_1.debit_amount + gl_entry_2.debit_amount
            total_credit = gl_entry_1.credit_amount + gl_entry_2.credit_amount

            if total_debit != total_credit:
                return {
                    'success': False,
                    'error': f'GL entries not balanced',
                    'error_code': 'UNBALANCED_ENTRIES'
                }

            # 3. CREATE DIMENSION ASSIGNMENTS
            from app.models.accounting import AccountingDimensionAssignment
            assignments = []

            if hasattr(transaction, 'cost_center_id') and transaction.cost_center_id:
                assignments.append(AccountingDimensionAssignment(
                    id=str(uuid.uuid4()),
                    gl_entry_id=gl_entry_1.id,
                    dimension_type='cost_center',
                    dimension_id=transaction.cost_center_id,
                    created_at=datetime.utcnow()
                ))
                assignments.append(AccountingDimensionAssignment(
                    id=str(uuid.uuid4()),
                    gl_entry_id=gl_entry_2.id,
                    dimension_type='cost_center',
                    dimension_id=transaction.cost_center_id,
                    created_at=datetime.utcnow()
                ))

            if hasattr(transaction, 'project_id') and transaction.project_id:
                assignments.append(AccountingDimensionAssignment(
                    id=str(uuid.uuid4()),
                    gl_entry_id=gl_entry_1.id,
                    dimension_type='project',
                    dimension_id=transaction.project_id,
                    created_at=datetime.utcnow()
                ))
                assignments.append(AccountingDimensionAssignment(
                    id=str(uuid.uuid4()),
                    gl_entry_id=gl_entry_2.id,
                    dimension_type='project',
                    dimension_id=transaction.project_id,
                    created_at=datetime.utcnow()
                ))

            if hasattr(transaction, 'department_id') and transaction.department_id:
                assignments.append(AccountingDimensionAssignment(
                    id=str(uuid.uuid4()),
                    gl_entry_id=gl_entry_1.id,
                    dimension_type='department',
                    dimension_id=transaction.department_id,
                    created_at=datetime.utcnow()
                ))
                assignments.append(AccountingDimensionAssignment(
                    id=str(uuid.uuid4()),
                    gl_entry_id=gl_entry_2.id,
                    dimension_type='department',
                    dimension_id=transaction.department_id,
                    created_at=datetime.utcnow()
                ))

            # 4. UPDATE TRANSACTION STATUS
            if hasattr(transaction, 'posting_status'):
                transaction.posting_status = 'posted'
            if hasattr(transaction, 'posted_by'):
                transaction.posted_by = user_id
            if hasattr(transaction, 'last_posted_date'):
                transaction.last_posted_date = datetime.utcnow()
            if hasattr(transaction, 'gl_bank_account_id'):
                transaction.gl_bank_account_id = transaction.bank_account_id

            # 5. PERSIST ALL CHANGES
            self.db.add(gl_entry_1)
            self.db.add(gl_entry_2)
            for assignment in assignments:
                self.db.add(assignment)
            self.db.commit()

            # 6. BUILD RESPONSE
            return {
                'success': True,
                'bank_transaction_id': transaction.id,
                'posting_status': 'posted',
                'gl_entries': [
                    {
                        'id': gl_entry_1.id,
                        'account_id': gl_entry_1.account_id,
                        'debit': float(gl_entry_1.debit_amount),
                        'credit': float(gl_entry_1.credit_amount),
                        'dimensions': {
                            'cost_center_id': getattr(transaction, 'cost_center_id', None),
                            'project_id': getattr(transaction, 'project_id', None),
                            'department_id': getattr(transaction, 'department_id', None)
                        }
                    },
                    {
                        'id': gl_entry_2.id,
                        'account_id': gl_entry_2.account_id,
                        'debit': float(gl_entry_2.debit_amount),
                        'credit': float(gl_entry_2.credit_amount),
                        'dimensions': {
                            'cost_center_id': getattr(transaction, 'cost_center_id', None),
                            'project_id': getattr(transaction, 'project_id', None),
                            'department_id': getattr(transaction, 'department_id', None)
                        }
                    }
                ],
                'posted_by': user_id,
                'posted_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            self.db.rollback()
            return {
                'success': False,
                'error': str(e),
                'error_code': 'POSTING_ERROR'
            }


    async def reconcile_banking_by_dimension(
        self,
        bank_account_id: str,
        statement_ending_balance: Decimal,
        reconciliation_date: date,
        user_id: str
    ) -> Dict:
        """
        Reconcile bank GL to bank statement with dimensional accuracy.

        Verifies:
        1. GL total balance = Statement ending balance (amount matching)
        2. Each GL entry has matching dimensional tracking (dimensional matching)
        3. No dimensional variance detected

        Args:
            bank_account_id: Bank account being reconciled
            statement_ending_balance: Ending balance from bank statement
            reconciliation_date: Date of reconciliation
            user_id: User performing reconciliation

        Returns:
            Reconciliation result with dimensional accuracy data
        """
        try:
            from app.models.accounting import GLEntry

            # 1. RETRIEVE GL ENTRIES FOR ACCOUNT IN CURRENT PERIOD
            period = self._get_posting_period()

            gl_entries = self.db.query(GLEntry).filter(
                and_(
                    GLEntry.posting_period == period,
                    GLEntry.account_id == bank_account_id
                )
            ).all()

            # Calculate GL balance
            gl_balance = sum(
                (Decimal(e.debit_amount or 0) - Decimal(e.credit_amount or 0)) for e in gl_entries
            )

            # 2. AMOUNT RECONCILIATION
            variance_amount = gl_balance - statement_ending_balance
            is_balanced = variance_amount == Decimal(0)

            # 3. DIMENSIONAL RECONCILIATION
            gl_by_cc = {}
            for entry in gl_entries:
                cc_id = getattr(entry, 'cost_center_id', None) or 'unassigned'
                if cc_id not in gl_by_cc:
                    gl_by_cc[cc_id] = Decimal(0)
                gl_by_cc[cc_id] += (Decimal(entry.debit_amount or 0) - Decimal(entry.credit_amount or 0))

            # Get transactions by dimension
            transactions_by_cc = {}
            transactions = self.db.query(BankTransaction).filter(
                BankTransaction.bank_account_id == bank_account_id
            ).all()

            for trans in transactions:
                cc_id = getattr(trans, 'cost_center_id', None) or 'unassigned'
                if cc_id not in transactions_by_cc:
                    transactions_by_cc[cc_id] = Decimal(0)
                transactions_by_cc[cc_id] += Decimal(trans.amount or 0)

            # Check for variances
            variance_by_dimension = {}
            has_variance = False

            for cc_id in set(list(gl_by_cc.keys()) + list(transactions_by_cc.keys())):
                gl_amt = gl_by_cc.get(cc_id, Decimal(0))
                trans_amt = transactions_by_cc.get(cc_id, Decimal(0))
                variance = gl_amt - trans_amt

                if variance != Decimal(0):
                    variance_by_dimension[cc_id] = float(variance)
                    has_variance = True

            # 4. CREATE RECONCILIATION RECORD
            reconciliation = BankReconciliation(
                id=str(__import__('uuid').uuid4()),
                bank_account_id=bank_account_id,
                statement_date=reconciliation_date,
                statement_balance=statement_ending_balance,
                book_balance=gl_balance,
                difference=variance_amount,
                status='completed' if is_balanced else 'completed_with_variance',
                reconciled_at=datetime.utcnow()
            )

            # Add Phase 4 fields if available
            if hasattr(reconciliation, 'dimensional_accuracy'):
                reconciliation.dimensional_accuracy = not has_variance
            if hasattr(reconciliation, 'has_dimensional_mismatch'):
                reconciliation.has_dimensional_mismatch = has_variance
            if hasattr(reconciliation, 'variance_amount'):
                reconciliation.variance_amount = variance_amount
            if hasattr(reconciliation, 'gl_balance_by_dimension'):
                reconciliation.gl_balance_by_dimension = str(gl_by_cc)
            if hasattr(reconciliation, 'bank_statement_by_dimension'):
                reconciliation.bank_statement_by_dimension = str(transactions_by_cc)
            if hasattr(reconciliation, 'dimension_variance_detail'):
                reconciliation.dimension_variance_detail = str(variance_by_dimension)

            self.db.add(reconciliation)

            # 5. UPDATE TRANSACTION RECONCILIATION STATUSES
            for trans in transactions:
                if hasattr(trans, 'reconciliation_status'):
                    trans.reconciliation_status = 'variance' if has_variance else 'reconciled'

            self.db.commit()

            # 6. BUILD RESPONSE
            return {
                'reconciliation_id': reconciliation.id,
                'bank_account_id': bank_account_id,
                'reconciliation_date': reconciliation_date.isoformat(),
                'statement_ending_balance': float(statement_ending_balance),
                'gl_balance': float(gl_balance),
                'variance_amount': float(variance_amount),
                'is_balanced': is_balanced,
                'dimensional_accuracy': not has_variance,
                'reconciliation_status': 'completed' if is_balanced else 'completed_with_variances',
                'summary': {
                    'total_transactions': len(transactions),
                    'reconciled_transactions': len(transactions) if not has_variance else 0,
                    'variance_transactions': len([t for t in transactions if has_variance]) if has_variance else 0
                },
                'variance_by_dimension': variance_by_dimension
            }

        except Exception as e:
            self.db.rollback()
            return {
                'success': False,
                'error': str(e),
                'error_code': 'RECONCILIATION_ERROR'
            }


    async def get_cash_position_by_dimension(
        self,
        as_of_date: date
    ) -> Dict:
        """
        Get current cash position by cost center/project/department.

        Returns cash balance for each dimension with pending transactions.
        """
        try:
            # Get all transactions up to as_of_date
            transactions = self.db.query(BankTransaction).filter(
                BankTransaction.date <= as_of_date
            ).all()

            # Group by cost center
            position_by_cc = {}
            total_position = Decimal(0)

            for trans in transactions:
                cc_id = getattr(trans, 'cost_center_id', None) or 'unassigned'
                if cc_id not in position_by_cc:
                    position_by_cc[cc_id] = {
                        'cash_balance': Decimal(0),
                        'pending_transactions': 0
                    }

                position_by_cc[cc_id]['cash_balance'] += Decimal(trans.amount or 0)

                posting_status = getattr(trans, 'posting_status', 'posted')
                if posting_status != 'posted':
                    position_by_cc[cc_id]['pending_transactions'] += 1

                total_position += Decimal(trans.amount or 0)

            return {
                'as_of_date': as_of_date.isoformat(),
                'cash_position_total': float(total_position),
                'by_cost_center': [
                    {
                        'cost_center_id': cc_id,
                        'cash_balance': float(data['cash_balance']),
                        'pending_transactions': data['pending_transactions'],
                        'reconciliation_status': 'reconciled' if data['pending_transactions'] == 0 else 'pending'
                    }
                    for cc_id, data in position_by_cc.items()
                ]
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_code': 'POSITION_ERROR'
            }


    async def track_dimensional_transfers(
        self,
        period: str,
        from_cost_center_id: Optional[str] = None,
        to_cost_center_id: Optional[str] = None
    ) -> Dict:
        """Track all inter-dimensional bank transfers."""
        try:
            from app.models.banking import BankTransferAllocation

            query = self.db.query(BankTransferAllocation)

            if from_cost_center_id:
                query = query.filter(
                    BankTransferAllocation.from_cost_center_id == from_cost_center_id
                )

            if to_cost_center_id:
                query = query.filter(
                    BankTransferAllocation.to_cost_center_id == to_cost_center_id
                )

            allocations = query.all()

            return {
                'period': period,
                'total_transfers': len(allocations),
                'transfers': [
                    {
                        'id': a.id,
                        'from_cost_center_id': a.from_cost_center_id,
                        'to_cost_center_id': a.to_cost_center_id,
                        'amount': float(a.amount),
                        'authorization_status': 'authorized' if a.authorized_by else 'pending',
                        'posting_status': 'posted' if a.posted_to_gl else 'pending'
                    }
                    for a in allocations
                ]
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_code': 'TRANSFER_TRACKING_ERROR'
            }


    def _get_posting_period(self) -> str:
        """Get current posting period in YYYY-MM format"""
        now = datetime.utcnow()
        return f"{now.year}-{now.month:02d}"
