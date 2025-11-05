from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from datetime import datetime
import logging
from app.models.accounting import AccountingCode, JournalEntry
from app.core.database import get_db
# from app.services.ifrs_reporting_service import IFRSReportingService
# from app.services.accounting_service import AccountingService

# Setup logger
logger = logging.getLogger(__name__)
# from app.services.ifrs_reporting_service import IFRSReportingService
# from app.services.accounting_service import AccountingService

# Setup logger
logger = logging.getLogger(__name__)

# Pydantic models for parent and branch info
class ParentInfo(BaseModel):
    id: str
    code: str
    name: str

class BranchInfo(BaseModel):
    id: str
    name: str
    code: str

class TransactionInfo(BaseModel):
    id: str
    date: str
    description: Optional[str]
    narration: Optional[str]
    reference: Optional[str]
    debit_amount: float
    credit_amount: float
    entry_type: Optional[str]
    origin: Optional[str]
    balance_after: float

class AccountTransactionsOut(BaseModel):
    account_id: str
    account_code: str
    account_name: str
    current_balance: float
    total_debits: float
    total_credits: float
    transactions: List[TransactionInfo]

router = APIRouter()

# Pydantic Schemas
class AccountingCodeBase(BaseModel):
    code: str = Field(...)
    name: str = Field(...)
    account_type: str = Field(...)
    category: str = Field(...)
    is_parent: bool = False
    parent_id: Optional[str] = None
    branch_id: Optional[str] = None
    # currency is automatically set from app settings

class AccountingCodeCreate(AccountingCodeBase):
    reporting_tag: Optional[str] = None

class AccountingCodeUpdate(BaseModel):
    name: Optional[str]
    account_type: Optional[str]
    category: Optional[str]
    is_parent: Optional[bool]
    parent_id: Optional[str]
    # currency cannot be updated - it's always set from app settings

class AccountingCodeOut(AccountingCodeBase):
    id: str
    balance: float
    total_debits: float
    total_credits: float
    currency: str  # Include currency in output
    reporting_tag: Optional[str]
    parent: Optional[ParentInfo] = None
    branch: Optional[BranchInfo] = None
    sub_accounts: Optional[List['AccountingCodeOut']] = []

    model_config = ConfigDict(from_attributes=True)

AccountingCodeOut.model_rebuild()

# Helper to serialize with sub-accounts
def serialize_code(code: AccountingCode, db: Session = None, include_subs=True):
    try:
        print(f"🔍 Serializing code: {code.id} ({code.code} - {code.name})")

        # Get parent and branch information
        parent_info = None
        if code.parent_id:
            print(f"  - Has parent_id: {code.parent_id}")
            try:
                parent = code.parent
                if parent:
                    print(f"  - Found parent: {parent.code} - {parent.name}")
                    parent_info = {
                        "id": parent.id,
                        "code": parent.code,
                        "name": parent.name
                    }
                else:
                    print(f"  - Warning: Parent with ID {code.parent_id} not found")
            except Exception as e:
                print(f"  - Error getting parent: {str(e)}")
                parent_info = None

        branch_info = None
        if code.branch_id and db:
            print(f"  - Has branch_id: {code.branch_id}")
            try:
                from app.models.branch import Branch
                branch = db.query(Branch).filter(Branch.id == code.branch_id).first()
                if branch:
                    print(f"  - Found branch: {branch.code} - {branch.name}")
                    branch_info = {
                        "id": branch.id,
                        "name": branch.name,
                        "code": branch.code
                    }
                else:
                    print(f"  - Warning: Branch with ID {code.branch_id} not found")
            except Exception as e:
                print(f"  - Error getting branch: {str(e)}")
                branch_info = None

        # Compute live totals from journal entries when a DB session is available
        live_total_debits = None
        live_total_credits = None
        live_balance = None
        if db is not None:
            try:
                debit_sum = db.query(func.coalesce(func.sum(JournalEntry.debit_amount), 0)).filter(
                    JournalEntry.accounting_code_id == code.id
                ).scalar() or 0
                credit_sum = db.query(func.coalesce(func.sum(JournalEntry.credit_amount), 0)).filter(
                    JournalEntry.accounting_code_id == code.id
                ).scalar() or 0

                # Determine balance direction by account type
                acct_type = (code.account_type or '').strip()
                if acct_type in ["Asset", "Expense"]:
                    bal = float(debit_sum) - float(credit_sum)
                else:
                    bal = float(credit_sum) - float(debit_sum)

                live_total_debits = float(debit_sum)
                live_total_credits = float(credit_sum)
                live_balance = float(bal)

                # If this is a parent account, aggregate sub-account balances
                if code.is_parent:
                    print(f"  - Parent account detected, aggregating sub-account balances...")
                    try:
                        sub_accounts = getattr(code, 'children', [])
                        if sub_accounts:
                            sub_debit_total = 0.0
                            sub_credit_total = 0.0

                            for sub in sub_accounts:
                                # Get direct journal entries for sub-account
                                sub_debits = db.query(func.coalesce(func.sum(JournalEntry.debit_amount), 0)).filter(
                                    JournalEntry.accounting_code_id == sub.id
                                ).scalar() or 0
                                sub_credits = db.query(func.coalesce(func.sum(JournalEntry.credit_amount), 0)).filter(
                                    JournalEntry.accounting_code_id == sub.id
                                ).scalar() or 0

                                sub_debit_total += float(sub_debits)
                                sub_credit_total += float(sub_credits)
                                print(f"    - Sub-account {sub.code}: Debits={sub_debits}, Credits={sub_credits}")

                            # Add sub-account totals to parent
                            live_total_debits += sub_debit_total
                            live_total_credits += sub_credit_total

                            # Recalculate balance with aggregated amounts
                            if acct_type in ["Asset", "Expense"]:
                                live_balance = live_total_debits - live_total_credits
                            else:
                                live_balance = live_total_credits - live_total_debits

                            print(f"  - Aggregated totals: Debits={live_total_debits}, Credits={live_total_credits}, Balance={live_balance}")
                    except Exception as sub_err:
                        print(f"  - Error aggregating sub-account balances: {str(sub_err)}")

            except Exception as e:
                print(f"  - Error computing live totals for {code.code}: {str(e)}")
                live_total_debits = None
                live_total_credits = None
                live_balance = None

        # Prepare the result
        result = {
            "id": code.id,
            "code": code.code,
            "name": code.name,
            "account_type": code.account_type,
            "category": code.category,
            "is_parent": code.is_parent,
            "parent_id": code.parent_id,
            "parent": parent_info,
            "branch_id": code.branch_id,
            "branch": branch_info,
            "currency": code.currency or "BWP",
            # Prefer live computed values when available; fall back to stored fields
            "balance": (live_balance if live_balance is not None else (float(code.balance or 0.0) if code.balance is not None else 0.0)),
            "total_debits": (live_total_debits if live_total_debits is not None else (float(code.total_debits or 0.0) if code.total_debits is not None else 0.0)),
            "total_credits": (live_total_credits if live_total_credits is not None else (float(code.total_credits or 0.0) if code.total_credits is not None else 0.0)),
            "reporting_tag": code.reporting_tag,
        }

        # Handle sub-accounts if needed
        if include_subs:
            try:
                sub_accounts = getattr(code, 'children', [])
                print(f"  - Found {len(sub_accounts)} sub-accounts")
                result["sub_accounts"] = [serialize_code(sub, db, False) for sub in sub_accounts]
            except Exception as e:
                print(f"  - Error getting sub-accounts: {str(e)}")
                result["sub_accounts"] = []
        else:
            result["sub_accounts"] = []

        return result

    except Exception as e:
        print(f"❌ Error in serialize_code for code {getattr(code, 'id', 'unknown')}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

# Routes
print("[DEBUG] Defining routes...")

@router.get("/", response_model=List[AccountingCodeOut])
def list_accounting_codes(db: Session = Depends(get_db)):
    print("\n" + "="*80)
    print("🔍 [API] GET /accounting-codes - Starting...")
    print("="*80)

    try:
        # Log database connection info
        print("\n🔧 Database connection details:")
        print(f"  - Connection URL: {db.bind.url if hasattr(db, 'bind') and db.bind else 'Unknown'}")

        # Check if AccountingCode table exists
        from sqlalchemy import inspect
        inspector = inspect(db.bind)
        table_exists = inspector.has_table('accounting_codes')
        print(f"  - Table 'accounting_codes' exists: {table_exists}")

        if not table_exists:
            raise HTTPException(
                status_code=500,
                detail="Database table 'accounting_codes' does not exist. Please run migrations."
            )

        # Query all accounting codes
        print("\n📊 Querying accounting codes...")
        from app.models.accounting import AccountingCode
        codes = db.query(AccountingCode).all()
        print(f"✅ Found {len(codes)} accounting codes in the database")

        if not codes:
            print("⚠️  No accounting codes found in the database")
            return []

        # Print sample of codes
        print("\n📋 Sample of accounting codes:")
        for i, code in enumerate(codes[:3]):
            print(f"  {i+1}. ID: {code.id}")
            print(f"     Code: {code.code}")
            print(f"     Name: {code.name}")
            print(f"     Type: {code.account_type}")
            print(f"     Category: {code.category}")
            print(f"     Parent ID: {code.parent_id}")
            print(f"     Is Parent: {code.is_parent}")
            print(f"     Normal Balance: {getattr(code, 'normal_balance', 'N/A')}")
            print()

        # Serialize the response
        print("\n🔄 Serializing accounting codes...")
        result = []
        for i, code in enumerate(codes, 1):
            try:
                print(f"  🔄 Processing code {i}/{len(codes)}: {code.code} - {code.name}")
                serialized = serialize_code(code, db)
                result.append(serialized)
                print(f"  ✅ Successfully serialized code {code.code}")
            except Exception as e:
                print(f"\n❌ [ERROR] Failed to serialize code {code.id} ({code.code}):")
                print(f"  - Error Type: {type(e).__name__}")
                print(f"  - Error Message: {str(e)}")
                import traceback
                traceback.print_exc()
                print("\n" + "-"*50 + "\n")
                raise

        print(f"\n✅ Successfully serialized {len(result)} accounting codes")
        return result

    except HTTPException as http_exc:
        print(f"\n❌ [HTTP {http_exc.status_code}] {http_exc.detail}")
        raise

    except Exception as e:
        print(f"\n❌ [UNHANDLED ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while retrieving accounting codes: {str(e)}"
        )
    finally:
        print("\n" + "="*80)
        print("🏁 [API] GET /accounting-codes - Completed")
        print("="*80 + "\n")

@router.get("/{code_id}", response_model=AccountingCodeOut)
def get_accounting_code(code_id: str, db: Session = Depends(get_db)):
    code = db.query(AccountingCode).filter_by(id=code_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="Accounting code not found")
    return serialize_code(code, db)

@router.post("/", response_model=AccountingCodeOut, status_code=status.HTTP_201_CREATED)
def create_accounting_code(data: AccountingCodeCreate, db: Session = Depends(get_db)):
    # Get app settings for default currency
    from app.core.config import settings

    # Create accounting code with currency from app settings
    code_data = data.model_dump()
    code_data['currency'] = settings.default_currency  # Always use app settings currency

    # Preserve provided reporting_tag; fallback to TEMP if missing (legacy behavior)
    reporting_tag = data.reporting_tag or "TEMP"
    code_data['reporting_tag'] = reporting_tag

    print(f"DEBUG: Setting currency to: {settings.default_currency}")
    print(f"DEBUG: Generated reporting tag: {reporting_tag}")
    print(f"DEBUG: Code data: {code_data}")

    code = AccountingCode(**code_data)
    db.add(code)
    db.commit()
    db.refresh(code)

    print(f"DEBUG: Saved code currency: {code.currency}")
    print(f"DEBUG: Saved code reporting tag: {code.reporting_tag}")
    return serialize_code(code, db)

@router.put("/{code_id}", response_model=AccountingCodeOut)
def update_accounting_code(code_id: str, data: AccountingCodeUpdate, db: Session = Depends(get_db)):
    """Update an existing accounting code with validation and error handling."""
    print(f"\n🔄 [PUT] Updating accounting code {code_id}")
    print(f"📝 Update data: {data.dict(exclude_unset=True)}")

    try:
        # Find the accounting code
        code = db.query(AccountingCode).filter_by(id=code_id).first()
        if not code:
            print(f"❌ Accounting code {code_id} not found")
            raise HTTPException(status_code=404, detail="Accounting code not found")

        print(f"✅ Found accounting code: {code.name} ({code.code})")

        # Get the update data, excluding unset values
        update_data = data.dict(exclude_unset=True)

        # Validate parent_id if being updated
        if 'parent_id' in update_data:
            parent_id = update_data['parent_id']
            if parent_id:
                # Check if parent exists
                parent = db.query(AccountingCode).filter_by(id=parent_id).first()
                if not parent:
                    print(f"❌ Parent code {parent_id} not found")
                    raise HTTPException(status_code=400, detail="Parent accounting code not found")

                # Prevent circular reference
                if parent_id == code_id:
                    print(f"❌ Cannot set account as its own parent")
                    raise HTTPException(status_code=400, detail="Account cannot be its own parent")

                # Check if the new parent would create a circular reference
                current = parent
                while current and current.parent_id:
                    if current.parent_id == code_id:
                        print(f"❌ Circular reference detected with parent {parent_id}")
                        raise HTTPException(status_code=400, detail="This change would create a circular reference")
                    current = db.query(AccountingCode).filter_by(id=current.parent_id).first()

                print(f"✅ Parent validation passed for {parent.name} ({parent.code})")

                # Set parent as a parent account if it isn't already
                if not parent.is_parent:
                    parent.is_parent = True
                    print(f"📝 Marked parent {parent.name} as parent account")

        # Validate account type and category consistency
        if 'account_type' in update_data or 'category' in update_data:
            new_account_type = update_data.get('account_type', code.account_type)
            new_category = update_data.get('category', code.category)

            # Add any validation logic for account type/category combinations here
            print(f"✅ Account type/category validation passed: {new_account_type}/{new_category}")

        # Apply updates
        for key, value in update_data.items():
            if hasattr(code, key):
                old_value = getattr(code, key)
                setattr(code, key, value)
                print(f"📝 Updated {key}: {old_value} -> {value}")
            else:
                print(f"⚠️ Skipping unknown field: {key}")

        # Regenerate reporting tag if account type or category changed
        if 'account_type' in update_data or 'category' in update_data:
            # new_reporting_tag = IFRSReportingService.generate_reporting_tag(
            #     code.account_type,
            #     code.category
            # )
            new_reporting_tag = "TEMP"  # Temporary while debugging imports
            code.reporting_tag = new_reporting_tag
            print(f"📝 Updated reporting tag: {new_reporting_tag}")

        # Commit the changes
        db.commit()
        db.refresh(code)
        print(f"✅ Successfully updated accounting code {code.name}")

        return serialize_code(code, db)

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error updating accounting code: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating accounting code: {str(e)}"
        )

@router.delete("/{code_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_accounting_code(code_id: str, db: Session = Depends(get_db)):
    """Delete an accounting code with proper validation and cascade handling."""
    print(f"\n🗑️ [DELETE] Deleting accounting code {code_id}")

    try:
        # Find the accounting code
        code = db.query(AccountingCode).filter_by(id=code_id).first()
        if not code:
            print(f"❌ Accounting code {code_id} not found")
            raise HTTPException(status_code=404, detail="Accounting code not found")

        print(f"✅ Found accounting code: {code.name} ({code.code})")

        # Check if this code has sub-accounts (children)
        children = db.query(AccountingCode).filter_by(parent_id=code_id).all()
        if children:
            child_names = [f"{child.name} ({child.code})" for child in children]
            print(f"❌ Cannot delete: Has {len(children)} sub-accounts: {', '.join(child_names[:3])}")
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete account with sub-accounts. This account has {len(children)} sub-accounts. Please delete or reassign sub-accounts first."
            )

        # Check if this code is referenced in any journal entries or transactions
        # This would require checking the journal_entries table if it exists
        try:
            from app.models.accounting import JournalEntry
            journal_entries = db.query(JournalEntry).filter_by(accounting_code_id=code_id).first()
            if journal_entries:
                print(f"❌ Cannot delete: Account has journal entries")
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete account that has journal entries. Please review and remove journal entries first."
                )
        except ImportError:
            # JournalEntry model might not exist yet, skip this check
            print("⚠️ JournalEntry model not found, skipping journal entry check")
        except Exception as e:
            # Other database errors, log but don't fail the deletion
            print(f"⚠️ Could not check journal entries: {str(e)}")

        # Check if this code is used in other transactions (purchases, sales, etc.)
        # You can add more checks here for other models that reference accounting codes

        # If this account is a child, check if parent should remain as parent
        if code.parent_id:
            parent = db.query(AccountingCode).filter_by(id=code.parent_id).first()
            if parent:
                # Check if parent has other children
                other_children = db.query(AccountingCode).filter(
                    AccountingCode.parent_id == code.parent_id,
                    AccountingCode.id != code_id
                ).count()

                # If this is the last child, mark parent as non-parent
                if other_children == 0:
                    parent.is_parent = False
                    print(f"📝 Marked parent {parent.name} as non-parent (no more children)")

        # Delete the accounting code
        db.delete(code)
        db.commit()
        print(f"✅ Successfully deleted accounting code {code.name} ({code.code})")

        return  # FastAPI automatically returns 204 No Content

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error deleting accounting code: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting accounting code: {str(e)}"
        )

@router.get("/{code_id}/sub-accounts", response_model=List[AccountingCodeOut])
def get_sub_accounts(code_id: str, db: Session = Depends(get_db)):
    code = db.query(AccountingCode).filter_by(id=code_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="Accounting code not found")

    # Query for sub-accounts that have this code as their parent
    sub_accounts = db.query(AccountingCode).filter_by(parent_id=code_id).all()
    return [serialize_code(sub, db) for sub in sub_accounts]

@router.post("/{code_id}/sub-accounts", response_model=AccountingCodeOut, status_code=status.HTTP_201_CREATED)
def create_sub_account(code_id: str, data: AccountingCodeCreate, db: Session = Depends(get_db)):
    """Create a sub-account under the specified parent account."""
    print(f"\n➕ [POST] Creating sub-account under {code_id}")
    print(f"📝 Sub-account data: {data.model_dump()}")

    try:
        parent = db.query(AccountingCode).filter_by(id=code_id).first()
        if not parent:
            print(f"❌ Parent accounting code {code_id} not found")
            raise HTTPException(status_code=404, detail="Parent accounting code not found")

        print(f"✅ Found parent: {parent.name} ({parent.code})")

        # Get app settings for default currency
        from app.core.config import settings

        # Create sub-account with currency from app settings
        sub_data = data.model_dump()
        sub_data['currency'] = settings.default_currency  # Always use app settings currency

        # Automatically generate reporting tag based on account type and category
        # reporting_tag = IFRSReportingService.generate_reporting_tag(
        #     data.account_type,
        #     data.category
        # )
        reporting_tag = "TEMP"  # Temporary while debugging imports
        sub_data['reporting_tag'] = reporting_tag

        sub_data['parent_id'] = parent.id
        sub_data['is_parent'] = False

        print(f"📝 Generated sub-account reporting tag: {reporting_tag}")
        print(f"📝 Setting parent_id to: {parent.id}")

        # Validate that the code doesn't already exist
        existing_code = db.query(AccountingCode).filter_by(code=sub_data['code']).first()
        if existing_code:
            print(f"❌ Account code {sub_data['code']} already exists")
            raise HTTPException(status_code=400, detail=f"Account code '{sub_data['code']}' already exists")

        sub = AccountingCode(**sub_data)
        db.add(sub)

        # Mark parent as a parent account if it isn't already
        if not parent.is_parent:
            parent.is_parent = True
            print(f"📝 Marked parent {parent.name} as parent account")

        db.commit()
        db.refresh(sub)

        print(f"✅ Successfully created sub-account: {sub.name} ({sub.code})")
        return serialize_code(sub, db)

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating sub-account: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating sub-account: {str(e)}"
        )

print("[DEBUG] Reached sub-account management endpoints...")

@router.delete("/{code_id}/sub-accounts/{sub_account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sub_account(code_id: str, sub_account_id: str, db: Session = Depends(get_db)):
    """Delete a specific sub-account."""
    print(f"\n🗑️ [DELETE] Deleting sub-account {sub_account_id} from parent {code_id}")

    try:
        # Find the parent account
        parent = db.query(AccountingCode).filter_by(id=code_id).first()
        if not parent:
            print(f"❌ Parent accounting code {code_id} not found")
            raise HTTPException(status_code=404, detail="Parent accounting code not found")

        # Find the sub-account
        sub_account = db.query(AccountingCode).filter_by(id=sub_account_id, parent_id=code_id).first()
        if not sub_account:
            print(f"❌ Sub-account {sub_account_id} not found under parent {code_id}")
            raise HTTPException(status_code=404, detail="Sub-account not found under this parent")

        print(f"✅ Found sub-account: {sub_account.name} ({sub_account.code})")

        # Check if sub-account has any journal entries or transactions
        try:
            from app.models.accounting import JournalEntry
            journal_entries = db.query(JournalEntry).filter_by(accounting_code_id=sub_account_id).first()
            if journal_entries:
                print(f"❌ Cannot delete: Sub-account has journal entries")
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete sub-account that has journal entries. Please review and remove journal entries first."
                )
        except ImportError:
            print("⚠️ JournalEntry model not found, skipping journal entry check")
        except Exception as e:
            print(f"⚠️ Could not check journal entries: {str(e)}")

        # Delete the sub-account
        db.delete(sub_account)

        # Check if parent has other children
        other_children = db.query(AccountingCode).filter(
            AccountingCode.parent_id == code_id,
            AccountingCode.id != sub_account_id
        ).count()

        # If this is the last child, mark parent as non-parent
        if other_children == 0:
            parent.is_parent = False
            print(f"📝 Marked parent {parent.name} as non-parent (no more children)")

        db.commit()
        print(f"✅ Successfully deleted sub-account {sub_account.name} ({sub_account.code})")

        return  # FastAPI automatically returns 204 No Content

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error deleting sub-account: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting sub-account: {str(e)}"
        )

print("[DEBUG] Reached transaction endpoints section...")

@router.get("/test-transactions")
async def test_transactions_endpoint():
    """Simple test endpoint to verify route registration"""
    print("[DEBUG] test_transactions_endpoint called")
    return {"message": "Transactions endpoint is working"}

print("[DEBUG] test_transactions_endpoint defined")

@router.get("/{code_id}/transactions", response_model=AccountTransactionsOut)
async def get_account_transactions(
    code_id: str,
    db: Session = Depends(get_db),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="Number of transactions to return"),
    offset: int = Query(0, ge=0, description="Number of transactions to skip")
) -> AccountTransactionsOut:
    """
    Get all transactions for a specific accounting code with running balance calculation.

    Returns transactions in chronological order with running balance calculations.
    The running balance starts from the oldest transaction and accumulates through
    each subsequent transaction.
    """
    print(f"[DEBUG] get_account_transactions called for code_id: {code_id}")
    try:
        # Verify the accounting code exists
        accounting_code = db.query(AccountingCode).filter(
            AccountingCode.id == code_id
        ).first()

        if not accounting_code:
            raise HTTPException(
                status_code=404,
                detail=f"Accounting code with ID {code_id} not found"
            )

        # Build base query for journal entries related to this accounting code
        # If this is a parent account, include transactions from all child accounts
        if accounting_code.is_parent:
            # Get all child account IDs
            child_accounts = db.query(AccountingCode).filter(
                AccountingCode.parent_id == code_id
            ).all()

            if child_accounts:
                # Include the parent account itself AND all child accounts
                account_ids = [code_id] + [child.id for child in child_accounts]
                query = db.query(JournalEntry).filter(
                    JournalEntry.accounting_code_id.in_(account_ids)
                )
                print(f"[DEBUG] Parent account {accounting_code.code} - including {len(child_accounts)} child accounts")
            else:
                # Parent has no children, just use parent account
                query = db.query(JournalEntry).filter(
                    JournalEntry.accounting_code_id == code_id
                )
                print(f"[DEBUG] Parent account {accounting_code.code} - no child accounts found")
        else:
            # Child account - only show its own transactions
            query = db.query(JournalEntry).filter(
                JournalEntry.accounting_code_id == code_id
            )
            print(f"[DEBUG] Child account {accounting_code.code} - showing own transactions only")

        # Apply date filters if provided
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                query = query.filter(JournalEntry.date >= start_dt)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid start_date format. Use YYYY-MM-DD"
                )

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                query = query.filter(JournalEntry.date <= end_dt)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid end_date format. Use YYYY-MM-DD"
                )

        # Order by transaction date chronologically (oldest first)
        query = query.order_by(JournalEntry.date.asc(), JournalEntry.id.asc())

        # Get total count for pagination info
        total_count = query.count()

        # Apply pagination
        journal_entries = query.offset(offset).limit(limit).all()

        # Calculate running balance
        transactions = []
        running_balance = Decimal('0.00')

        for entry in journal_entries:
            # Calculate the transaction effect on balance
            debit_amount = Decimal(str(entry.debit_amount)) if entry.debit_amount else Decimal('0.00')
            credit_amount = Decimal(str(entry.credit_amount)) if entry.credit_amount else Decimal('0.00')

            # Update running balance (debits increase balance, credits decrease it for most accounts)
            running_balance += debit_amount - credit_amount

            # Create transaction info
            transaction_info = TransactionInfo(
                id=str(entry.id),
                date=entry.date.strftime("%Y-%m-%d") if entry.date else "",
                description=entry.description or "",
                narration=entry.narration or "",
                reference=entry.reference or "",
                debit_amount=float(debit_amount),
                credit_amount=float(credit_amount),
                entry_type=getattr(entry, 'entry_type', None),
                origin=getattr(entry, 'origin', None),
                balance_after=float(running_balance)
            )
            transactions.append(transaction_info)

        # Calculate summary information
        total_debits = sum(
            entry.debit_amount for entry in journal_entries
            if entry.debit_amount
        )
        total_credits = sum(
            entry.credit_amount for entry in journal_entries
            if entry.credit_amount
        )

        return AccountTransactionsOut(
            account_id=code_id,
            account_code=accounting_code.code,
            account_name=accounting_code.name,
            current_balance=float(running_balance if transactions else Decimal('0.00')),
            total_debits=float(total_debits),
            total_credits=float(total_credits),
            transactions=transactions
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching transactions for accounting code {code_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error while fetching transactions: {str(e)}"
        )

print("[DEBUG] get_account_transactions endpoint defined")

@router.get("/categories/{account_type}")
def get_categories_by_account_type(account_type: str):
    """Get valid categories for a specific account type"""
    categories_map = {
        "Asset": [
            "Cash",
            "Bank",
            "Trade Receivables",
            "Inventory",
            "Current Asset",
            "Fixed Asset",
            "Prepaid Expenses",
            "Other Assets"
        ],
        "Liability": [
            "Trade Payables",
            "Current Liability",
            "Long-Term Liability",
            "Accrued Liabilities",
            "Tax Payable",
            "Other Liabilities"
        ],
        "Equity": [
            "Equity Capital",
            "Retained Earnings",
            "Share Capital",
            "Owner's Equity",
            "Opening Balance Equity"
        ],
        "Revenue": [
            "Sales Revenue",
            "Service Revenue",
            "Other Revenue",
            "Operating Revenue",
            "Non-Operating Revenue"
        ],
        "Expense": [
            "Operating Expense",
            "Cost of Goods Sold",
            "Depreciation",
            "Tax Expense",
            "Interest Expense",
            "Other Expenses"
        ]
    }

    categories = categories_map.get(account_type, [])
    return {"account_type": account_type, "categories": categories}
