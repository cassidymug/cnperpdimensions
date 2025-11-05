from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
import datetime as dt
from decimal import Decimal
from sqlalchemy import func

from app.models.accounting import AccountingEntry, JournalEntry, Ledger, AccountingCode
from app.core.database import get_db
from app.core.response_wrapper import UnifiedResponse
from app.services.accounting_service import AccountingService
from app.schemas.accounting import AccountingCodeResponse
from app.utils.logger import get_logger, log_exception, log_error_with_context
# from app.core.security import get_current_user  # Removed for development
# Accounting restricted to accountant (plus universal overrides)
# Allow both accountant and manager (and implicit super/admin/accountant override)

logger = get_logger(__name__)
router = APIRouter()  # Dependencies removed for development

# Pydantic Schemas
class JournalEntryBase(BaseModel):
    accounting_code_id: str
    entry_type: Optional[str] = None
    narration: str
    debit_amount: Decimal = Field(default=0)
    credit_amount: Decimal = Field(default=0)
    description: Optional[str] = None
    reference: Optional[str] = None

class JournalEntryCreate(JournalEntryBase):
    pass

class JournalEntryOut(JournalEntryBase):
    id: str
    # Align with ORM model field name 'date'
    date: dt.date
    date_posted: Optional[dt.date] = None
    branch_id: str
    accounting_code_name: Optional[str] = None
    accounting_code_code: Optional[str] = None
    origin: Optional[str] = None
    created_by_user_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class AccountingEntryBase(BaseModel):
    date_prepared: dt.date
    particulars: str
    book: str
    status: str = "draft"

class AccountingEntryCreate(AccountingEntryBase):
    journal_entries: List[JournalEntryCreate]

class AccountingEntryOut(AccountingEntryBase):
    id: str
    date_posted: Optional[dt.date]
    branch_id: str
    journal_entries: List[JournalEntryOut] = []

    model_config = ConfigDict(from_attributes=True)

class LedgerEntryOut(BaseModel):
    id: str
    date: date
    account_code: str
    account_name: str
    description: str
    reference: str
    debit: Decimal
    credit: Decimal
    balance: Decimal
    type: str

    model_config = ConfigDict(from_attributes=True)

class TrialBalanceEntryOut(BaseModel):
    account_code: str
    account_name: str
    type: str
    debit_balance: Decimal
    credit_balance: Decimal
    net_balance: Decimal

    model_config = ConfigDict(from_attributes=True)

# Routes
@router.get("/codes")
def get_accounting_codes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get accounting codes, branch-scoped for non-universal roles."""
    try:
        query = db.query(AccountingCode)
        # AccountingCode has branch_id field; apply scope if user limited
        if False:  # Role check removed for development
            query = query.filter(AccountingCode.branch_id == 'default-branch')

        total = query.count()
        codes = query.offset(skip).limit(limit).all()

        return UnifiedResponse.success(
            data=codes,
            message=f"Retrieved {len(codes)} accounting codes",
            meta={
                "total": total,
                "skip": skip,
                "limit": limit
            }
        )
    except Exception as e:
        return UnifiedResponse.error(f"Error fetching accounting codes: {str(e)}")

@router.get("/codes/count")
def get_accounting_codes_count(db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Get count of accounting codes"""
    try:
        count = db.query(AccountingCode).count()
        return UnifiedResponse.success(
            data={"count": count},
            message=f"Found {count} accounting codes"
        )
    except Exception as e:
        return UnifiedResponse.error(f"Error counting accounting codes: {str(e)}")

@router.post("/codes/initialize")
def initialize_basic_accounting_codes(db: Session = Depends(get_db)):  # current_user parameter removed for development
    """Initialize basic chart of accounts if none exist"""
    from app.models.branch import Branch

    # Check if any accounting codes exist
    existing_codes = db.query(AccountingCode).count()
    if existing_codes > 0:
        return {"message": f"Chart of accounts already exists with {existing_codes} codes"}

    # Get the head office branch
    head_office = db.query(Branch).filter(Branch.is_head_office == True).first()
    if not head_office:
        # If no head office, get any branch
        head_office = db.query(Branch).first()

    if not head_office:
        raise HTTPException(status_code=400, detail="No branches found. Please create a branch first.")

    # Create basic chart of accounts
    basic_codes = [
        {"code": "1000", "name": "Cash", "account_type": "Asset", "category": "Current Assets"},
        {"code": "1100", "name": "Accounts Receivable", "account_type": "Asset", "category": "Current Assets"},
        {"code": "1200", "name": "Inventory", "account_type": "Asset", "category": "Current Assets"},
        {"code": "1500", "name": "Equipment", "account_type": "Asset", "category": "Fixed Assets"},
        {"code": "2000", "name": "Accounts Payable", "account_type": "Liability", "category": "Current Liabilities"},
        {"code": "2100", "name": "VAT Payable", "account_type": "Liability", "category": "Current Liabilities"},
        {"code": "3000", "name": "Owner's Equity", "account_type": "Equity", "category": "Owner's Equity"},
        {"code": "3100", "name": "Retained Earnings", "account_type": "Equity", "category": "Retained Earnings"},
        {"code": "4000", "name": "Sales Revenue", "account_type": "Revenue", "category": "Operating Revenue"},
        {"code": "5000", "name": "Cost of Goods Sold", "account_type": "Expense", "category": "Cost of Sales"},
        {"code": "6000", "name": "Operating Expenses", "account_type": "Expense", "category": "Operating Expenses"},
    ]

    created_codes = []
    errors = []

    for code_data in basic_codes:
        try:
            new_code = AccountingCode(
                code=code_data["code"],
                name=code_data["name"],
                account_type=code_data["account_type"],
                category=code_data["category"],
                # is_active=True,  # Field doesn't exist in DB yet
                description=f"Basic {code_data['account_type']} account",
                currency="BWP",
                branch_id=head_office.id
            )
            db.add(new_code)
            db.flush()  # Flush to catch any immediate errors
            created_codes.append(code_data["code"])
            print(f"Created accounting code: {code_data['code']} - {code_data['name']}")
        except Exception as e:
            error_msg = f"Error creating code {code_data['code']}: {str(e)}"
            print(error_msg)
            errors.append(error_msg)
            continue

    try:
        db.commit()
        print(f"Successfully committed {len(created_codes)} accounting codes")
        result = {
            "message": f"Successfully created {len(created_codes)} basic accounting codes",
            "codes": created_codes,
            "branch_used": head_office.name
        }
        if errors:
            result["errors"] = errors
        return result
    except Exception as e:
        db.rollback()
        error_msg = f"Error committing codes to database: {str(e)}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/entries", response_model=List[AccountingEntryOut])
def get_accounting_entries(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get accounting entries (branch scoped for non-universal roles)."""
    query = db.query(AccountingEntry)
    # query = # Security check removed for development  # Removed for development
    entries = query.order_by(AccountingEntry.date_prepared.desc()).offset(skip).limit(limit).all()
    return entries

@router.post("/entries", response_model=AccountingEntryOut, status_code=status.HTTP_201_CREATED)
def create_accounting_entry(
    entry_data: AccountingEntryCreate,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Create a new accounting entry with journal entries. Requires active branch context for all roles."""
    try:
        accounting_service = AccountingService(db)

        # Derive branch context: try user token branch, else first accounting code's branch, else first branch record
        from app.models.branch import Branch
        branch_ctx = None
        try:
            # Attempt to parse Authorization header via dependency in future; for now fallback
            first_code = db.query(AccountingCode).first()
            if first_code:
                branch_ctx = first_code.branch_id
            if not branch_ctx:
                first_branch = db.query(Branch).first()
                if first_branch:
                    branch_ctx = first_branch.id
        except Exception:
            pass
        if not branch_ctx:
            raise HTTPException(status_code=400, detail="No branch available to assign to accounting entry")

        accounting_entry = AccountingEntry(
            date_prepared=entry_data.date_prepared,
            particulars=entry_data.particulars,
            book=entry_data.book,
            status=entry_data.status,
            branch_id=branch_ctx
        )

        db.add(accounting_entry)
        db.flush()  # Get ID

        for journal_data in entry_data.journal_entries:
            if journal_data.debit_amount > 0 and journal_data.credit_amount == 0:
                entry_type = "debit"
            elif journal_data.credit_amount > 0 and journal_data.debit_amount == 0:
                entry_type = "credit"
            else:
                entry_type = journal_data.entry_type or "mixed"

            journal_entry = JournalEntry(
                accounting_code_id=journal_data.accounting_code_id,
                accounting_entry_id=accounting_entry.id,
                entry_type=entry_type,
                narration=journal_data.narration,
                date=entry_data.date_prepared,
                debit_amount=journal_data.debit_amount,
                credit_amount=journal_data.credit_amount,
                description=journal_data.description,
                reference=journal_data.reference,
                branch_id=branch_ctx
            )
            db.add(journal_entry)

        db.commit()

        for journal_data in entry_data.journal_entries:
            accounting_service.update_accounting_code_balance(journal_data.accounting_code_id)

        db.refresh(accounting_entry)
        return accounting_entry

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        db.rollback()
        print(f"Error creating accounting entry: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to create accounting entry: {str(e)}")

@router.get("/journal")
def get_journal_entries(
    skip: int = 0,
    limit: int = 100,
    accounting_code_id: Optional[str] = None,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get journal entries (branch scoped for non-universal roles)."""
    try:
        query = db.query(JournalEntry).options(
            joinedload(JournalEntry.accounting_code),
            joinedload(JournalEntry.accounting_entry),
            joinedload(JournalEntry.branch),
            joinedload(JournalEntry.ledger)
            # Skipping purchase joinedload due to schema mismatch (cost_center_id missing from DB)
        )
        # query = # Security check removed for development  # Removed for development
        if accounting_code_id:
            query = query.filter(JournalEntry.accounting_code_id == accounting_code_id)

        entries = query.order_by(JournalEntry.date.desc()).offset(skip).limit(limit).all()

        result = []
        running_balance = Decimal('0.0')
        for entry in entries:
            if entry.debit_amount > 0:
                running_balance += entry.debit_amount
            if entry.credit_amount > 0:
                running_balance -= entry.credit_amount

            # Build entry response with names instead of UUIDs
            # Safe access to purchase data - may not be loaded if schema mismatch
            entry_dict = {
                "id": entry.id,
                "accounting_code_id": entry.accounting_code_id,
                "accounting_code_name": entry.accounting_code.name if entry.accounting_code else None,
                "accounting_code_code": entry.accounting_code.code if entry.accounting_code else None,
                "accounting_entry_id": entry.accounting_entry_id,
                "accounting_entry_particulars": entry.accounting_entry.particulars if entry.accounting_entry else None,
                "entry_type": entry.entry_type,
                "narration": entry.narration,
                "date": entry.date,
                "date_posted": entry.date_posted,
                "description": entry.description,
                "reference": entry.reference,
                "debit_amount": float(entry.debit_amount) if entry.debit_amount else 0.0,
                "credit_amount": float(entry.credit_amount) if entry.credit_amount else 0.0,
                "running_balance": float(running_balance),
                "branch_id": entry.branch_id,
                "branch_name": entry.branch.name if entry.branch else None,
                "ledger_id": entry.ledger_id,
                "ledger_description": entry.ledger.description if entry.ledger else None,
                "purchase_id": entry.purchase_id,
                "purchase_reference": entry.purchase.reference if entry.purchase else None
            }
            result.append(entry_dict)
        return result
    except Exception as e:
        print(f"Error in get_journal_entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/journal/{entry_id}")
def get_journal_entry(entry_id: str, db: Session = Depends(get_db)):
    """Get a specific journal entry with all relationships eagerly loaded."""
    entry = db.query(JournalEntry).options(
        joinedload(JournalEntry.accounting_code),
        joinedload(JournalEntry.accounting_entry),
        joinedload(JournalEntry.branch),
        joinedload(JournalEntry.ledger),
        joinedload(JournalEntry.dimension_assignments)
        # Skipping purchase joinedload due to schema mismatch
    ).filter(JournalEntry.id == entry_id).first()

    if not entry:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    # Manually construct response with names instead of UUIDs
    return {
        "id": entry.id,
        "accounting_code_id": entry.accounting_code_id,
        "accounting_code_name": entry.accounting_code.name if entry.accounting_code else None,
        "accounting_code_code": entry.accounting_code.code if entry.accounting_code else None,
        "accounting_entry_id": entry.accounting_entry_id,
        "accounting_entry_particulars": entry.accounting_entry.particulars if entry.accounting_entry else None,
        "entry_type": entry.entry_type,
        "narration": entry.narration,
        "date": entry.date,
        "date_posted": entry.date_posted,
        "description": entry.description,
        "reference": entry.reference,
        "debit_amount": float(entry.debit_amount) if entry.debit_amount else 0.0,
        "credit_amount": float(entry.credit_amount) if entry.credit_amount else 0.0,
        "branch_id": entry.branch_id,
        "branch_name": entry.branch.name if entry.branch else None,
        "ledger_id": entry.ledger_id,
        "ledger_description": entry.ledger.description if entry.ledger else None,
        "purchase_id": entry.purchase_id,
        "purchase_reference": entry.purchase.reference if entry.purchase else None,
        "dimension_assignments": [
            {
                "dimension_type": da.dimension_value.dimension.code if da.dimension_value and da.dimension_value.dimension else None,
                "dimension_value": da.dimension_value.value if da.dimension_value else None
            }
            for da in entry.dimension_assignments
        ] if entry.dimension_assignments else []
    }

@router.delete("/journal/{entry_id}")
def delete_journal_entry(
    entry_id: str,
    force: bool = False,
    db: Session = Depends(get_db)
):
    """
    Delete a journal entry with proper rollback functionality.

    Args:
        entry_id: ID of the journal entry to delete
        force: If True, delete even if entry is posted or has dependencies
    """
    try:
        # Find the journal entry
        journal_entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
        if not journal_entry:
            raise HTTPException(status_code=404, detail="Journal entry not found")

        # Check if entry is posted (if you have posting functionality)
        if hasattr(journal_entry, 'date_posted') and journal_entry.date_posted and not force:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete posted journal entry. Use force=true to override."
            )

        # Store entry details for rollback logging
        entry_details = {
            "id": journal_entry.id,
            "accounting_code_id": journal_entry.accounting_code_id,
            "accounting_entry_id": journal_entry.accounting_entry_id,
            "description": journal_entry.description,
            "debit_amount": float(journal_entry.debit_amount) if journal_entry.debit_amount else 0.0,
            "credit_amount": float(journal_entry.credit_amount) if journal_entry.credit_amount else 0.0,
            "date": journal_entry.date.isoformat() if journal_entry.date else None,
            "reference": journal_entry.reference
        }

        # Check for dependencies (accounting entries that reference this journal entry)
        if journal_entry.accounting_entry_id:
            accounting_entry = db.query(AccountingEntry).filter(
                AccountingEntry.id == journal_entry.accounting_entry_id
            ).first()

            if accounting_entry and not force:
                # Count other journal entries that reference the same accounting entry
                related_entries_count = db.query(JournalEntry).filter(
                    JournalEntry.accounting_entry_id == journal_entry.accounting_entry_id,
                    JournalEntry.id != entry_id
                ).count()

                if related_entries_count > 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot delete journal entry with {related_entries_count} related entries. Use force=true to override."
                    )

        # Update accounting code balances by reversing the entry
        if journal_entry.accounting_code_id:
            accounting_code = db.query(AccountingCode).filter(
                AccountingCode.id == journal_entry.accounting_code_id
            ).first()

            if accounting_code:
                # Reverse the amounts to rollback the balance
                if journal_entry.debit_amount:
                    accounting_code.total_debits = (accounting_code.total_debits or 0) - journal_entry.debit_amount
                    accounting_code.balance = (accounting_code.balance or 0) - journal_entry.debit_amount

                if journal_entry.credit_amount:
                    accounting_code.total_credits = (accounting_code.total_credits or 0) - journal_entry.credit_amount
                    accounting_code.balance = (accounting_code.balance or 0) + journal_entry.credit_amount

        # Delete the journal entry
        db.delete(journal_entry)

        # If this was the only journal entry for an accounting entry, consider deleting the accounting entry too
        if journal_entry.accounting_entry_id and force:
            remaining_journal_entries = db.query(JournalEntry).filter(
                JournalEntry.accounting_entry_id == journal_entry.accounting_entry_id
            ).count()

            if remaining_journal_entries == 0:
                accounting_entry = db.query(AccountingEntry).filter(
                    AccountingEntry.id == journal_entry.accounting_entry_id
                ).first()
                if accounting_entry:
                    db.delete(accounting_entry)

        db.commit()

        return {
            "success": True,
            "message": "Journal entry deleted successfully",
            "deleted_entry": entry_details,
            "rollback_performed": True
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback
        print(f"Error deleting journal entry: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to delete journal entry: {str(e)}")

@router.post("/journal/{entry_id}/reverse")
def reverse_journal_entry(
    entry_id: str,
    description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Create a reversing journal entry instead of deleting.
    This is the preferred approach for maintaining audit trails.
    """
    try:
        # Find the original journal entry
        original_entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id).first()
        if not original_entry:
            raise HTTPException(status_code=404, detail="Journal entry not found")

        # Create reversing entry with swapped debit/credit amounts
        reversing_description = description or f"Reversal of entry: {original_entry.description}"

        # Create a new accounting entry for the reversal if needed
        accounting_entry_id = None
        if original_entry.accounting_entry_id:
            # Create a new accounting entry for the reversal
            from app.models.accounting import AccountingEntry
            reversing_accounting_entry = AccountingEntry(
                narration=f"Reversal of {original_entry.reference or original_entry.id}",
                entry_type="reversal",
                branch_id=original_entry.branch_id
            )
            db.add(reversing_accounting_entry)
            db.flush()  # Get the ID
            accounting_entry_id = reversing_accounting_entry.id

        reversing_entry = JournalEntry(
            accounting_code_id=original_entry.accounting_code_id,
            accounting_entry_id=accounting_entry_id,  # Use the new accounting entry ID
            description=reversing_description,
            reference=f"REV-{original_entry.reference}" if original_entry.reference else None,
            date=date.today(),
            # Swap debit and credit to reverse the effect
            debit_amount=original_entry.credit_amount,
            credit_amount=original_entry.debit_amount,
            entry_type="reversal",
            branch_id=original_entry.branch_id,
            origin=f"reversal_of_{original_entry.id}"
        )

        db.add(reversing_entry)

        # Update accounting code balances
        if original_entry.accounting_code_id:
            accounting_code = db.query(AccountingCode).filter(
                AccountingCode.id == original_entry.accounting_code_id
            ).first()

            if accounting_code:
                # Add the reversing amounts
                if reversing_entry.debit_amount:
                    accounting_code.total_debits = (accounting_code.total_debits or 0) + reversing_entry.debit_amount
                    accounting_code.balance = (accounting_code.balance or 0) + reversing_entry.debit_amount

                if reversing_entry.credit_amount:
                    accounting_code.total_credits = (accounting_code.total_credits or 0) + reversing_entry.credit_amount
                    accounting_code.balance = (accounting_code.balance or 0) - reversing_entry.credit_amount

        db.commit()
        db.refresh(reversing_entry)

        return {
            "success": True,
            "message": "Reversing journal entry created successfully",
            "original_entry_id": entry_id,
            "reversing_entry_id": reversing_entry.id,
            "reversing_entry": {
                "id": reversing_entry.id,
                "description": reversing_entry.description,
                "debit_amount": float(reversing_entry.debit_amount) if reversing_entry.debit_amount else 0.0,
                "credit_amount": float(reversing_entry.credit_amount) if reversing_entry.credit_amount else 0.0,
                "date": reversing_entry.date.isoformat() if reversing_entry.date else None
            }
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback
        print(f"Error creating reversing entry: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to create reversing entry: {str(e)}")

@router.get("/balances/{accounting_code_id}")
def get_account_balances(
    accounting_code_id: str,
    as_of_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Get detailed balance information for an accounting code"""
    accounting_service = AccountingService(db)

    total_debits = accounting_service.get_total_debits(accounting_code_id)
    total_credits = accounting_service.get_total_credits(accounting_code_id)
    current_balance = accounting_service.get_account_balance(accounting_code_id, as_of_date)

    return {
        "accounting_code_id": accounting_code_id,
        "total_debits": float(total_debits),
        "total_credits": float(total_credits),
        "current_balance": float(current_balance),
        "as_of_date": as_of_date or date.today()
    }

# New Ledger Endpoints
@router.get("/ledger", response_model=List[LedgerEntryOut])
def get_general_ledger(
    skip: int = 0,
    limit: int = 100,
    account_type: Optional[str] = None,
    account_code: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get general ledger entries with filtering (chronological for correct running balance)."""
    query = db.query(JournalEntry).join(AccountingCode)

    if account_type:
        query = query.filter(AccountingCode.account_type == account_type)
    if account_code:
        # Prefix match
        query = query.filter(AccountingCode.code.like(f"{account_code}%"))
    if from_date:
        query = query.filter(JournalEntry.date >= from_date)
    if to_date:
        query = query.filter(JournalEntry.date <= to_date)
    if search:
        like_term = f"%{search}%"
        query = query.filter(
            (JournalEntry.description.ilike(like_term)) |
            (JournalEntry.reference.ilike(like_term)) |
            (AccountingCode.name.ilike(like_term))
        )

    # Ascending order for running balance
    entries = query.order_by(JournalEntry.date.asc(), JournalEntry.id.asc()).offset(skip).limit(limit).all()

    ledger_entries: List[LedgerEntryOut] = []
    running_balance = Decimal('0.0')

    for entry in entries:
        if entry.debit_amount and entry.debit_amount > 0:
            running_balance += entry.debit_amount
        if entry.credit_amount and entry.credit_amount > 0:
            running_balance -= entry.credit_amount
        ledger_entries.append(
            LedgerEntryOut(
                id=entry.id,
                date=entry.date,
                account_code=entry.accounting_code.code if entry.accounting_code else '',
                account_name=entry.accounting_code.name if entry.accounting_code else '',
                description=entry.description or entry.narration or '',
                reference=entry.reference or '',
                debit=entry.debit_amount or Decimal('0'),
                credit=entry.credit_amount or Decimal('0'),
                balance=running_balance,
                type=entry.accounting_code.account_type if entry.accounting_code else ''
            )
        )
    return ledger_entries

@router.get("/ledger/customers", response_model=List[LedgerEntryOut])
def get_customer_ledger(
    skip: int = 0,
    limit: int = 200,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Customer (Accounts Receivable) ledger entries across all AR accounts.
    Uses journal entries whose accounting code category or name indicates receivables.
    """
    try:
        query = db.query(JournalEntry).join(AccountingCode)
        # Heuristic: category/name contains 'receivable'
        query = query.filter(
            (func.lower(AccountingCode.category).like('%receivable%')) |
            (func.lower(AccountingCode.name).like('%receivable%'))
        )
        if from_date:
            query = query.filter(JournalEntry.date >= from_date)
        if to_date:
            query = query.filter(JournalEntry.date <= to_date)
        if search:
            query = query.filter(
                (JournalEntry.description.ilike(f"%{search}%")) |
                (JournalEntry.reference.ilike(f"%{search}%")) |
                (AccountingCode.name.ilike(f"%{search}%"))
            )
        entries = query.order_by(JournalEntry.date.asc(), JournalEntry.id.asc())\
            .offset(skip).limit(limit).all()

        result: List[LedgerEntryOut] = []
        running_balance_map: Dict[str, Decimal] = {}
        for entry in entries:
            acc: AccountingCode = entry.accounting_code
            if not acc:
                continue
            # Normal balance for Assets (AR) is debit
            nb = 'debit'
            if acc.account_type in ('Liability','Equity','Revenue'):
                nb = 'credit'
            if acc.id not in running_balance_map:
                running_balance_map[acc.id] = Decimal('0')
            if entry.debit_amount:
                running_balance_map[acc.id] += entry.debit_amount if nb=='debit' else -entry.debit_amount
            if entry.credit_amount:
                running_balance_map[acc.id] += -entry.credit_amount if nb=='debit' else entry.credit_amount
            result.append(
                LedgerEntryOut(
                    id=entry.id,
                    date=entry.date,
                    account_code=acc.code,
                    account_name=acc.name,
                    description=entry.description or entry.narration,
                    reference=entry.reference or '',
                    debit=entry.debit_amount or Decimal('0'),
                    credit=entry.credit_amount or Decimal('0'),
                    balance=running_balance_map[acc.id],
                    type=acc.account_type
                )
            )
        return result
    except Exception as e:
        print(f"Error in get_customer_ledger: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ledger/suppliers", response_model=List[LedgerEntryOut])
def get_supplier_ledger(
    skip: int = 0,
    limit: int = 200,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Supplier (Accounts Payable) ledger entries across all AP accounts."""
    try:
        query = db.query(JournalEntry).join(AccountingCode)
        query = query.filter(
            (func.lower(AccountingCode.category).like('%payable%')) |
            (func.lower(AccountingCode.name).like('%payable%'))
        )
        if from_date:
            query = query.filter(JournalEntry.date >= from_date)
        if to_date:
            query = query.filter(JournalEntry.date <= to_date)
        if search:
            query = query.filter(
                (JournalEntry.description.ilike(f"%{search}%")) |
                (JournalEntry.reference.ilike(f"%{search}%")) |
                (AccountingCode.name.ilike(f"%{search}%"))
            )
        entries = query.order_by(JournalEntry.date.asc(), JournalEntry.id.asc())\
            .offset(skip).limit(limit).all()
        result: List[LedgerEntryOut] = []
        running_balance_map: Dict[str, Decimal] = {}
        for entry in entries:
            acc: AccountingCode = entry.accounting_code
            if not acc:
                continue
            nb = 'debit'
            if acc.account_type in ('Liability','Equity','Revenue'):
                nb = 'credit'
            if acc.id not in running_balance_map:
                running_balance_map[acc.id] = Decimal('0')
            if entry.debit_amount:
                running_balance_map[acc.id] += entry.debit_amount if nb=='debit' else -entry.debit_amount
            if entry.credit_amount:
                running_balance_map[acc.id] += -entry.credit_amount if nb=='debit' else entry.credit_amount
            result.append(
                LedgerEntryOut(
                    id=entry.id,
                    date=entry.date,
                    account_code=acc.code,
                    account_name=acc.name,
                    description=entry.description or entry.narration,
                    reference=entry.reference or '',
                    debit=entry.debit_amount or Decimal('0'),
                    credit=entry.credit_amount or Decimal('0'),
                    balance=running_balance_map[acc.id],
                    type=acc.account_type
                )
            )
        return result
    except Exception as e:
        print(f"Error in get_supplier_ledger: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ledger/inventory", response_model=List[LedgerEntryOut])
def get_inventory_ledger(
    skip: int = 0,
    limit: int = 200,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Inventory ledger entries across all inventory accounts (category/name contains 'inventory')."""
    try:
        query = db.query(JournalEntry).join(AccountingCode)
        query = query.filter(
            (func.lower(AccountingCode.category).like('%inventory%')) |
            (func.lower(AccountingCode.name).like('%inventory%'))
        )
        if from_date:
            query = query.filter(JournalEntry.date >= from_date)
        if to_date:
            query = query.filter(JournalEntry.date <= to_date)
        if search:
            query = query.filter(
                (JournalEntry.description.ilike(f"%{search}%")) |
                (JournalEntry.reference.ilike(f"%{search}%")) |
                (AccountingCode.name.ilike(f"%{search}%"))
            )
        entries = query.order_by(JournalEntry.date.asc(), JournalEntry.id.asc())\
            .offset(skip).limit(limit).all()
        result: List[LedgerEntryOut] = []
        running_balance_map: Dict[str, Decimal] = {}
        for entry in entries:
            acc: AccountingCode = entry.accounting_code
            if not acc:
                continue
            nb = 'debit'
            if acc.account_type in ('Liability','Equity','Revenue'):
                nb = 'credit'
            if acc.id not in running_balance_map:
                running_balance_map[acc.id] = Decimal('0')
            if entry.debit_amount:
                running_balance_map[acc.id] += entry.debit_amount if nb=='debit' else -entry.debit_amount
            if entry.credit_amount:
                running_balance_map[acc.id] += -entry.credit_amount if nb=='debit' else entry.credit_amount
            result.append(
                LedgerEntryOut(
                    id=entry.id,
                    date=entry.date,
                    account_code=acc.code,
                    account_name=acc.name,
                    description=entry.description or entry.narration,
                    reference=entry.reference or '',
                    debit=entry.debit_amount or Decimal('0'),
                    credit=entry.credit_amount or Decimal('0'),
                    balance=running_balance_map[acc.id],
                    type=acc.account_type
                )
            )
        return result
    except Exception as e:
        print(f"Error in get_inventory_ledger: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ledger/subsidiary/{ledger_type}")
def get_subsidiary_ledger(
    ledger_type: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get subsidiary ledger entries (Accounts Receivable, Accounts Payable, etc.)"""
    # Map ledger types to accounting codes
    ledger_mappings = {
        'accounts-receivable': '1300',  # Accounts Receivable
        'accounts-payable': '2100',     # Accounts Payable
        'inventory': '1400',            # Inventory
        'cash': '1110',                 # Cash in Hand
        'bank': '1210'                  # Main Bank Account
    }

    if ledger_type not in ledger_mappings:
        raise HTTPException(status_code=400, detail="Invalid ledger type")

    account_code = ledger_mappings[ledger_type]

    # Get accounting code
    accounting_code = db.query(AccountingCode).filter(AccountingCode.code == account_code).first()
    if not accounting_code:
        raise HTTPException(status_code=404, detail="Accounting code not found")

    # Get journal entries for this account
    query = db.query(JournalEntry).filter(JournalEntry.accounting_code_id == accounting_code.id)
    # query = # Security check removed for development  # Removed for development
    entries = query.order_by(JournalEntry.date.desc()).offset(skip).limit(limit).all()

    # Convert to subsidiary ledger format
    subsidiary_entries = []
    running_balance = Decimal('0.0')

    for entry in entries:
        # Calculate running balance
        if entry.debit_amount > 0:
            running_balance += entry.debit_amount
        if entry.credit_amount > 0:
            running_balance -= entry.credit_amount

        subsidiary_entry = {
            "id": entry.id,
            "date": entry.date,
            "customer": entry.description if ledger_type == 'accounts-receivable' else None,
            "supplier": entry.description if ledger_type == 'accounts-payable' else None,
            "description": entry.description or entry.narration,
            "reference": entry.reference or '',
            "debit": float(entry.debit_amount),
            "credit": float(entry.credit_amount),
            "balance": float(running_balance)
        }
        subsidiary_entries.append(subsidiary_entry)

    return subsidiary_entries

@router.get("/trial-balance", response_model=List[TrialBalanceEntryOut])
def get_trial_balance(
    as_of_date: Optional[date] = None,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get trial balance as of a specific date"""
    if not as_of_date:
        as_of_date = date.today()

    # Get all accounting codes
    accounting_codes_query = db.query(AccountingCode)
    # Apply branch scoping for non-universal roles/users with a fixed branch
    if False:  # Role check removed for development
        accounting_codes_query = accounting_codes_query.filter(AccountingCode.branch_id == 'default-branch')
    accounting_codes = accounting_codes_query.all()

    trial_balance = []

    for code in accounting_codes:
        # Get total debits and credits for this account
        total_debits = db.query(JournalEntry.debit_amount).filter(
            JournalEntry.accounting_code_id == code.id,
            JournalEntry.date <= as_of_date
        ).with_entities(func.sum(JournalEntry.debit_amount)).scalar() or Decimal('0.0')

        total_credits = db.query(JournalEntry.credit_amount).filter(
            JournalEntry.accounting_code_id == code.id,
            JournalEntry.date <= as_of_date
        ).with_entities(func.sum(JournalEntry.credit_amount)).scalar() or Decimal('0.0')

        # Calculate net balance
        net_balance = total_debits - total_credits

        # Only include accounts with activity
        if total_debits > 0 or total_credits > 0:
            trial_balance_entry = TrialBalanceEntryOut(
                account_code=code.code,
                account_name=code.name,
                type=code.account_type,
                debit_balance=total_debits,
                credit_balance=total_credits,
                net_balance=net_balance
            )
            trial_balance.append(trial_balance_entry)

    return trial_balance

# Grouped ledger response schemas (lightweight inline for now)
class GroupedLedgerItem(BaseModel):
    entity_name: str
    account_codes: List[str]
    total_debits: Decimal
    total_credits: Decimal
    net_balance: Decimal

class GroupedLedgerResponse(BaseModel):
    items: List[GroupedLedgerItem]
    page: int
    page_size: int
    total_items: int
    total_pages: int

def _aggregate_grouped(entries: List[JournalEntry]):
    from collections import defaultdict
    grouped = {}
    codes_map = defaultdict(set)
    for e in entries:
        # Determine grouping key: prefer reference, else description/narration
        key = (e.reference or '').strip() or (e.description or '').strip() or (e.narration or '').strip() or 'UNKNOWN'
        if key not in grouped:
            grouped[key] = {'debits': Decimal('0'), 'credits': Decimal('0')}
        if e.debit_amount:
            grouped[key]['debits'] += e.debit_amount
        if e.credit_amount:
            grouped[key]['credits'] += e.credit_amount
        if e.accounting_code and e.accounting_code.code:
            codes_map[key].add(e.accounting_code.code)
    # Build list
    items = []
    for key, vals in grouped.items():
        net = vals['debits'] - vals['credits']
        items.append(GroupedLedgerItem(
            entity_name=key,
            account_codes=sorted(list(codes_map[key])),
            total_debits=vals['debits'],
            total_credits=vals['credits'],
            net_balance=net
        ))
    # Sort by entity name
    items.sort(key=lambda x: x.entity_name.lower())
    return items

@router.get("/ledger/customers/grouped", response_model=GroupedLedgerResponse)
def get_customer_ledger_grouped(
    page: int = 1,
    page_size: int = 50,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Grouped customer ledger (Accounts Receivable) aggregated per customer (heuristic: reference/description)."""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 500:
        page_size = 50
    query = db.query(JournalEntry).join(AccountingCode)
    query = query.filter(
        (func.lower(AccountingCode.category).like('%receivable%')) |
        (func.lower(AccountingCode.name).like('%receivable%'))
    )
    if from_date:
        query = query.filter(JournalEntry.date >= from_date)
    if to_date:
        query = query.filter(JournalEntry.date <= to_date)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (JournalEntry.description.ilike(like)) |
            (JournalEntry.reference.ilike(like)) |
            (AccountingCode.name.ilike(like))
        )
    entries = query.all()
    items = _aggregate_grouped(entries)
    total_items = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    paged = items[start:end]
    total_pages = (total_items + page_size - 1) // page_size if page_size else 1
    return GroupedLedgerResponse(
        items=paged,
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages
    )

@router.get("/ledger/suppliers/grouped", response_model=GroupedLedgerResponse)
def get_supplier_ledger_grouped(
    page: int = 1,
    page_size: int = 50,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Grouped supplier ledger (Accounts Payable) aggregated per supplier (heuristic: reference/description)."""
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 500:
        page_size = 50
    query = db.query(JournalEntry).join(AccountingCode)
    query = query.filter(
        (func.lower(AccountingCode.category).like('%payable%')) |
        (func.lower(AccountingCode.name).like('%payable%'))
    )
    if from_date:
        query = query.filter(JournalEntry.date >= from_date)
    if to_date:
        query = query.filter(JournalEntry.date <= to_date)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (JournalEntry.description.ilike(like)) |
            (JournalEntry.reference.ilike(like)) |
            (AccountingCode.name.ilike(like))
        )
    entries = query.all()
    items = _aggregate_grouped(entries)
    total_items = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    paged = items[start:end]
    total_pages = (total_items + page_size - 1) // page_size if page_size else 1
    return GroupedLedgerResponse(
        items=paged,
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages
    )

@router.get("/financial-summary")
def get_financial_summary(db: Session = Depends(get_db)):
    """Get financial summary (Assets, Liabilities, Equity, Net Income)"""
    # This would typically calculate from trial balance
    # For now, return sample data structure
    return {
        "total_assets": 1250000.00,
        "total_liabilities": 450000.00,
        "total_equity": 800000.00,
        "net_income": 125000.00,
        "as_of_date": date.today()
    }


# ===== ACCOUNTING CODE DIMENSION REQUIREMENTS ENDPOINTS =====

@router.get("/codes/{accounting_code_id}/dimension-requirements")
def get_account_dimension_requirements(
    accounting_code_id: str,
    db: Session = Depends(get_db)
):
    """Get dimension requirements for an accounting code"""
    from app.services.accounting_code_dimension_service import AccountingCodeDimensionService

    service = AccountingCodeDimensionService(db)
    try:
        requirements = service.get_account_dimension_requirements(accounting_code_id)
        return {"requirements": requirements}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/codes/{accounting_code_id}/dimension-requirements")
def create_account_dimension_requirement(
    accounting_code_id: str,
    requirement_data: dict,
    db: Session = Depends(get_db)
):
    """Create a dimension requirement for an accounting code"""
    from app.services.accounting_code_dimension_service import AccountingCodeDimensionService

    service = AccountingCodeDimensionService(db)
    try:
        requirement = service.create_account_dimension_requirement(
            accounting_code_id=accounting_code_id,
            dimension_id=requirement_data.get("dimension_id"),
            is_required=requirement_data.get("is_required", False),
            default_dimension_value_id=requirement_data.get("default_dimension_value_id"),
            priority=requirement_data.get("priority", 1),
            description=requirement_data.get("description")
        )
        return {"requirement": requirement.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/codes/dimension-requirements/{requirement_id}")
def update_account_dimension_requirement(
    requirement_id: str,
    update_data: dict,
    db: Session = Depends(get_db)
):
    """Update a dimension requirement"""
    from app.services.accounting_code_dimension_service import AccountingCodeDimensionService

    service = AccountingCodeDimensionService(db)
    try:
        requirement = service.update_account_dimension_requirement(
            requirement_id=requirement_id,
            is_required=update_data.get("is_required"),
            default_dimension_value_id=update_data.get("default_dimension_value_id"),
            priority=update_data.get("priority"),
            description=update_data.get("description")
        )
        return {"requirement": requirement.to_dict()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/codes/dimension-requirements/{requirement_id}")
def delete_account_dimension_requirement(
    requirement_id: str,
    db: Session = Depends(get_db)
):
    """Delete a dimension requirement"""
    from app.services.accounting_code_dimension_service import AccountingCodeDimensionService

    service = AccountingCodeDimensionService(db)
    try:
        success = service.delete_account_dimension_requirement(requirement_id)
        if not success:
            raise HTTPException(status_code=404, detail="Dimension requirement not found")
        return {"message": "Dimension requirement deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/codes/{accounting_code_id}/dimension-balances")
def get_account_dimension_balances(
    accounting_code_id: str,
    db: Session = Depends(get_db)
):
    """Get account balance broken down by dimensions"""
    from app.services.accounting_code_dimension_service import AccountingCodeDimensionService

    service = AccountingCodeDimensionService(db)
    try:
        balances = service.get_dimension_balances_for_account(accounting_code_id)
        return balances
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DIMENSION MANAGEMENT ENDPOINTS ====================

@router.get("/dimensions/")
def get_dimensions(
    dimension_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    include_values: bool = False,
    db: Session = Depends(get_db)
):
    """Get all accounting dimensions with optional filters"""
    from app.services.accounting_dimensions_service import AccountingDimensionService

    service = AccountingDimensionService(db)
    try:
        dimensions = service.get_dimensions(
            dimension_type=dimension_type,
            is_active=is_active,
            include_values=include_values
        )
        return [dim.to_dict() for dim in dimensions]
    except Exception as e:
        logger.error(f"Error getting dimensions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dimensions/", status_code=status.HTTP_201_CREATED)
def create_dimension(
    dimension_data: Dict,
    db: Session = Depends(get_db)
):
    """Create a new accounting dimension"""
    from app.services.accounting_dimensions_service import AccountingDimensionService
    from app.schemas.accounting_dimensions import AccountingDimensionCreate

    service = AccountingDimensionService(db)
    try:
        # Convert dict to Pydantic schema
        schema_data = AccountingDimensionCreate(**dimension_data)
        dimension = service.create_dimension(schema_data)
        return dimension.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating dimension: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dimensions/{dimension_id}")
def get_dimension(
    dimension_id: str,
    include_values: bool = False,
    db: Session = Depends(get_db)
):
    """Get a specific accounting dimension"""
    from app.services.accounting_dimensions_service import AccountingDimensionService

    service = AccountingDimensionService(db)
    try:
        dimension = service.get_dimension(dimension_id, include_values=include_values)
        if not dimension:
            raise HTTPException(status_code=404, detail="Dimension not found")
        return dimension.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dimension: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/dimensions/{dimension_id}")
def update_dimension(
    dimension_id: str,
    dimension_data: Dict,
    db: Session = Depends(get_db)
):
    """Update an accounting dimension"""
    from app.services.accounting_dimensions_service import AccountingDimensionService
    from app.schemas.accounting_dimensions import AccountingDimensionUpdate

    service = AccountingDimensionService(db)
    try:
        # Convert dict to Pydantic schema
        schema_data = AccountingDimensionUpdate(**dimension_data)
        dimension = service.update_dimension(dimension_id, schema_data)
        if not dimension:
            raise HTTPException(status_code=404, detail="Dimension not found")
        return dimension.to_dict()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating dimension: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/dimensions/{dimension_id}")
def delete_dimension(
    dimension_id: str,
    db: Session = Depends(get_db)
):
    """Delete an accounting dimension"""
    from app.services.accounting_dimensions_service import AccountingDimensionService

    service = AccountingDimensionService(db)
    try:
        success = service.delete_dimension(dimension_id)
        if not success:
            raise HTTPException(status_code=404, detail="Dimension not found")
        return {"message": "Dimension deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting dimension: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DIMENSION VALUE ENDPOINTS ====================

@router.get("/dimensions/{dimension_id}/values")
def get_dimension_values(
    dimension_id: str,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get all values for a dimension"""
    from app.services.accounting_dimensions_service import AccountingDimensionService

    service = AccountingDimensionService(db)
    try:
        values = service.get_dimension_values(dimension_id, is_active=is_active)
        return [val.to_dict() for val in values]
    except Exception as e:
        logger.error(f"Error getting dimension values: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dimensions/{dimension_id}/values", status_code=status.HTTP_201_CREATED)
def create_dimension_value(
    dimension_id: str,
    value_data: Dict,
    db: Session = Depends(get_db)
):
    """Create a new dimension value"""
    from app.services.accounting_dimensions_service import AccountingDimensionService
    from app.schemas.accounting_dimensions import AccountingDimensionValueCreate

    service = AccountingDimensionService(db)
    try:
        # Ensure the dimension_id is set in the data
        value_data['dimension_id'] = dimension_id

        # Convert dict to Pydantic schema
        schema_data = AccountingDimensionValueCreate(**value_data)
        value = service.create_dimension_value(schema_data)
        return value.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating dimension value: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/dimensions/values/{value_id}")
def update_dimension_value(
    value_id: str,
    value_data: Dict,
    db: Session = Depends(get_db)
):
    """Update a dimension value"""
    from app.services.accounting_dimensions_service import AccountingDimensionService
    from app.schemas.accounting_dimensions import AccountingDimensionValueUpdate

    service = AccountingDimensionService(db)
    try:
        # Convert dict to Pydantic schema
        schema_data = AccountingDimensionValueUpdate(**value_data)
        value = service.update_dimension_value(value_id, schema_data)
        if not value:
            raise HTTPException(status_code=404, detail="Dimension value not found")
        return value.to_dict()
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating dimension value: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/dimensions/values/{value_id}")
def delete_dimension_value(
    value_id: str,
    db: Session = Depends(get_db)
):
    """Delete a dimension value"""
    from app.services.accounting_dimensions_service import AccountingDimensionService

    service = AccountingDimensionService(db)
    try:
        success = service.delete_dimension_value(value_id)
        if not success:
            raise HTTPException(status_code=404, detail="Dimension value not found")
        return {"message": "Dimension value deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting dimension value: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

