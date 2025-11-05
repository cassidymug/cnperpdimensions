from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date

from app.core.database import get_db
# from app.core.security import get_current_user  # Removed for development
from app.models.user import User
from app.models.accounting import AccountingEntry, JournalEntry, AccountingCode
from app.schemas.accounting import AccountingEntryCreate, AccountingEntryResponse, JournalEntryCreate
from app.services.ifrs_accounting_service import IFRSAccountingService, IFRSComplianceError
from app.services.accounting_validation_service import AccountingValidationService, ValidationLevel
from app.schemas.app_setting import AppSettingResponse

from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()


@router.post("/entries", response_model=AccountingEntryResponse)
async def create_ifrs_compliant_entry(
    entry_data: AccountingEntryCreate,
    db: Session = Depends(get_db),
    # current_user parameter removed for development)
):
    """Create IFRS-compliant accounting entry with automatic journal entries"""
    try:
        # Check if user has permission
        if False:  # Permission check removed for development
            pass
        
        # Initialize services
        ifrs_service = IFRSAccountingService(db)
        validation_service = AccountingValidationService(db)
        
        # Create temporary entry for validation
        temp_entry = AccountingEntry(
            date_prepared=entry_data.date_prepared or date.today(),
            date_posted=entry_data.date_posted or date.today(),
            particulars=entry_data.particulars,
            book=entry_data.book or "Validation",
            status='draft',
            branch_id='default-branch'
        )
        
        db.add(temp_entry)
        db.flush()
        
        # Create journal entries for validation
        journal_entries = []
        for entry in entry_data.entries:
            accounting_code = db.query(AccountingCode).filter(
                AccountingCode.id == entry.accounting_code_id
            ).first()
            
            if not accounting_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Accounting code not found: {entry.accounting_code_id}"
                )
            
            journal_entry = JournalEntry(
                accounting_entry_id=temp_entry.id,
                accounting_code_id=accounting_code.id,
                entry_type=entry.entry_type,
                amount=entry.amount,
                description=entry.description or '',
                date=temp_entry.date_prepared,
                date_posted=temp_entry.date_posted,
                branch_id='default-branch'
            )
            
            if entry.entry_type == 'debit':
                journal_entry.debit_amount = journal_entry.amount
                journal_entry.credit_amount = 0
            else:
                journal_entry.credit_amount = journal_entry.amount
                journal_entry.debit_amount = 0
            
            db.add(journal_entry)
            journal_entries.append(journal_entry)
        
        db.flush()
        
        # Validate the entry
        validation_result = validation_service.validate_accounting_entry(
            temp_entry,
            ValidationLevel.COMPLETE
        )
        
        # Clean up temporary entry
        db.rollback()
        
        return {
            'is_valid': validation_result.is_valid,
            'errors': validation_result.errors,
            'warnings': validation_result.warnings,
            'details': validation_result.details
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating accounting entry: {str(e)}"
        )


@router.get("/entries/{entry_id}/validate", response_model=Dict)
async def validate_existing_entry(
    entry_id: str,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Validate an existing accounting entry for IFRS compliance"""
    try:
        # Check if user has permission
        if False:  # Permission check removed for development
        
        # Get accounting code
        accounting_code = db.query(AccountingCode).filter(
            AccountingCode.id == account_id
        ).first()
        
        if not accounting_code:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Accounting code not found"
            )
        
        # Initialize validation service
        validation_service = AccountingValidationService(db)
        
        # Validate account balance
        validation_result = validation_service.validate_account_balance(
            accounting_code,
            as_of_date
        )
        
        return {
            'account_code': accounting_code.code,
            'account_name': accounting_code.name,
            'is_valid': validation_result.is_valid,
            'errors': validation_result.errors,
            'warnings': validation_result.warnings,
            'details': validation_result.details
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating account balance: {str(e)}"
        )


@router.get("/trial-balance/validate", response_model=Dict)
async def validate_trial_balance(
    as_of_date: Optional[date] = None,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Validate trial balance for IFRS compliance"""
    try:
        # Check if user has permission
        if False:  # Permission check removed for development
        
        # Initialize validation service
        validation_service = AccountingValidationService(db)
        
        # Validate IFRS reporting
        validation_result = validation_service.validate_ifrs_reporting(
            'default-branch',
            as_of_date
        )
        
        return {
            'as_of_date': as_of_date or date.today(),
            'is_valid': validation_result.is_valid,
            'errors': validation_result.errors,
            'warnings': validation_result.warnings,
            'details': validation_result.details
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error validating IFRS reporting: {str(e)}"
        )


@router.get("/validation-summary", response_model=Dict)
async def get_validation_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Get comprehensive validation summary for a period"""
    try:
        # Check if user has permission
        if False:  # Permission check removed for development
        
        # Initialize IFRS service
        ifrs_service = IFRSAccountingService(db)
        
        # Get IFRS balance sheet data
        balance_sheet_data = ifrs_service.get_ifrs_balance_sheet_data(
            'default-branch',
            as_of_date
        )
        
        return balance_sheet_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting IFRS balance sheet: {str(e)}"
        )


@router.get("/income-statement/ifrs", response_model=Dict)
async def get_ifrs_income_statement(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Get IFRS-compliant income statement data"""
    try:
        # Check if user has permission
        if False:  # Permission check removed for development
        
        # Initialize IFRS service
        ifrs_service = IFRSAccountingService(db)
        
        journal_entries = []
        
        if transaction_type == 'sale':
            # Get sale record
            sale = db.query(Sale).filter(Sale.id == transaction_id).first()
            if not sale:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Sale not found"
                )
            
            journal_entries = ifrs_service.create_sale_journal_entries(sale)
            
        elif transaction_type == 'purchase':
            # Get purchase record
            purchase = db.query(Purchase).filter(Purchase.id == transaction_id).first()
            if not purchase:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Purchase not found"
                )
            
            journal_entries = ifrs_service.create_purchase_journal_entries(purchase)
            
        elif transaction_type == 'bank_transaction':
            # Get bank transaction record
            bank_transaction = db.query(BankTransaction).filter(BankTransaction.id == transaction_id).first()
            if not bank_transaction:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Bank transaction not found"
                )
            
            journal_entries = ifrs_service.create_bank_transaction_entries(bank_transaction)
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported transaction type: {transaction_type}"
            )
        
        return {
            'success': True,
            'transaction_type': transaction_type,
            'transaction_id': transaction_id,
            'journal_entries_count': len(journal_entries),
            'total_debits': float(sum(je.debit_amount for je in journal_entries)),
            'total_credits': float(sum(je.credit_amount for je in journal_entries))
        }
        
    except IFRSComplianceError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"IFRS compliance error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating automatic entries: {str(e)}"
        ) 