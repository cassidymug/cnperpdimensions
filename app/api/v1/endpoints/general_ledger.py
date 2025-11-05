from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import date, datetime
from decimal import Decimal

from app.core.database import get_db
from app.services.general_ledger_service import GeneralLedgerService
from app.models.accounting import AccountType, NormalBalance
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)

router = APIRouter()



# Pydantic Schemas
class AccountSummary(BaseModel):
    """Account summary for chart of accounts"""
    id: str
    code: str
    name: str
    account_type: Optional[str]
    category: Optional[str]
    parent_id: Optional[str]
    is_parent: bool
    balance: float
    total_debits: float
    total_credits: float
    normal_balance: Optional[str]
    currency: Optional[str]
    full_path: str
    children: Optional[List['AccountSummary']] = []

    model_config = ConfigDict(from_attributes=True)

# Fix forward reference
AccountSummary.model_rebuild()

class LedgerEntry(BaseModel):
    """General ledger entry"""
    id: str
    date: str
    account_code: str
    account_name: str
    account_type: Optional[str]
    description: str
    reference: str
    debit_amount: float
    credit_amount: float
    running_balance: float
    entry_type: Optional[str]
    origin: Optional[str]
    accounting_entry_id: Optional[str]
    particulars: str

    model_config = ConfigDict(from_attributes=True)

class LedgerSummary(BaseModel):
    """Summary statistics for ledger"""
    total_debits: float
    total_credits: float
    net_difference: float
    entry_count: int
    account_types: Dict[str, Dict[str, Any]]

class GeneralLedgerResponse(BaseModel):
    """General ledger response"""
    entries: List[LedgerEntry]
    total_count: int
    summary: LedgerSummary
    filters: Dict[str, Any]

class TrialBalanceEntry(BaseModel):
    """Trial balance entry"""
    account_id: str
    account_code: str
    account_name: str
    account_type: Optional[str]
    category: Optional[str]
    debit_balance: float
    credit_balance: float
    net_balance: float
    normal_balance: Optional[str]
    is_parent: bool
    parent_code: Optional[str]

class TrialBalanceResponse(BaseModel):
    """Trial balance response"""
    trial_balance: List[TrialBalanceEntry]
    totals: Dict[str, Any]
    as_of_date: str
    branch_id: Optional[str]
    account_count: int

class AccountLedgerResponse(BaseModel):
    """Account-specific ledger response"""
    account: AccountSummary
    opening_balance: float
    closing_balance: float
    entries: List[Dict[str, Any]]
    entry_count: int
    period: Dict[str, Optional[str]]

class BalanceSheetResponse(BaseModel):
    """Balance sheet response"""
    assets: Dict[str, Any]
    liabilities: Dict[str, Any]
    equity: Dict[str, Any]
    totals: Dict[str, Any]
    as_of_date: str

# API Endpoints
@router.get("/chart-of-accounts", response_model=List[AccountSummary])
async def get_chart_of_accounts(
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    include_inactive: bool = Query(False, description="Include inactive accounts"),
    db: Session = Depends(get_db)
):
    """
    Get complete chart of accounts with hierarchical structure
    
    Returns the full chart of accounts organized hierarchically with parent-child relationships.
    Includes account balances, types, and categories for IFRS compliance.
    """
    try:
        ledger_service = GeneralLedgerService(db)
        accounts = ledger_service.get_chart_of_accounts(branch_id, include_inactive)
        
        return accounts
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving chart of accounts: {str(e)}"
        )

@router.get("/general-ledger", response_model=GeneralLedgerResponse)
async def get_general_ledger(
    account_id: Optional[str] = Query(None, description="Filter by specific account ID"),
    account_code: Optional[str] = Query(None, description="Filter by account code (e.g., 1110)"),
    account_type: Optional[str] = Query(None, description="Filter by account type (Asset, Liability, Equity, Revenue, Expense)"),
    from_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    search: Optional[str] = Query(None, description="Search in descriptions, references, and account names"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip for pagination"),
    db: Session = Depends(get_db)
):
    """
    Get general ledger entries with IFRS-compliant running balances

    Returns paginated general ledger entries with comprehensive filtering options.
    Includes running balance calculations and summary statistics.
    """
    try:
        ledger_service = GeneralLedgerService(db)
        result = ledger_service.get_general_ledger_entries(
            account_id=account_id,
            account_type=account_type,
            from_date=from_date,
            to_date=to_date,
            branch_id=branch_id,
            search=search,
            limit=limit,
            offset=offset,
            account_code=account_code
        )
        
        if 'error' in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['error']
            )
        
        return GeneralLedgerResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving general ledger: {str(e)}"
        )

@router.get("/trial-balance", response_model=TrialBalanceResponse)
async def get_trial_balance(
    as_of_date: Optional[date] = Query(None, description="Date for trial balance (defaults to today)"),
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    include_zero_balances: bool = Query(False, description="Include accounts with zero balances"),
    db: Session = Depends(get_db)
):
    """
    Generate IFRS-compliant trial balance
    
    Returns a trial balance showing all accounts with their debit and credit balances.
    Validates that total debits equal total credits for accounting integrity.
    """
    try:
        ledger_service = GeneralLedgerService(db)
        result = ledger_service.get_trial_balance(
            as_of_date=as_of_date,
            branch_id=branch_id,
            include_zero_balances=include_zero_balances
        )
        
        if 'error' in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['error']
            )
        
        return TrialBalanceResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating trial balance: {str(e)}"
        )

@router.get("/account-ledger/{account_id}", response_model=AccountLedgerResponse)
async def get_account_ledger(
    account_id: str,
    from_date: Optional[date] = Query(None, description="Start date for ledger entries"),
    to_date: Optional[date] = Query(None, description="End date for ledger entries"),
    db: Session = Depends(get_db)
):
    """
    Get detailed ledger for a specific account
    
    Returns all transactions for a specific account with running balance calculations.
    Shows opening balance, all entries, and closing balance for the period.
    """
    try:
        ledger_service = GeneralLedgerService(db)
        result = ledger_service.get_account_ledger(
            account_id=account_id,
            from_date=from_date,
            to_date=to_date
        )
        
        if 'error' in result:
            if result['error'] == 'Account not found':
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Account not found"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=result['error']
                )
        
        return AccountLedgerResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving account ledger: {str(e)}"
        )

@router.get("/balance-sheet", response_model=BalanceSheetResponse)
async def get_balance_sheet(
    as_of_date: Optional[date] = Query(None, description="Date for balance sheet (defaults to today)"),
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    db: Session = Depends(get_db)
):
    """
    Generate balance sheet data organized by IFRS categories
    
    Returns balance sheet with assets, liabilities, and equity properly categorized.
    Validates that Assets = Liabilities + Equity for balance sheet integrity.
    """
    try:
        ledger_service = GeneralLedgerService(db)
        result = ledger_service.get_balance_sheet_data(
            as_of_date=as_of_date,
            branch_id=branch_id
        )
        
        if 'error' in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['error']
            )
        
        return BalanceSheetResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating balance sheet: {str(e)}"
        )

@router.get("/account-types")
async def get_account_types():
    """
    Get available account types for filtering
    
    Returns the standard IFRS account types with their normal balance indicators.
    """
    return {
        "account_types": [
            {
                "value": "Asset",
                "label": "Assets",
                "normal_balance": "debit",
                "description": "Resources owned by the business"
            },
            {
                "value": "Liability", 
                "label": "Liabilities",
                "normal_balance": "credit",
                "description": "Obligations owed to external parties"
            },
            {
                "value": "Equity",
                "label": "Equity", 
                "normal_balance": "credit",
                "description": "Owner's claims on the assets"
            },
            {
                "value": "Revenue",
                "label": "Revenue",
                "normal_balance": "credit", 
                "description": "Income from sales and services"
            },
            {
                "value": "Expense",
                "label": "Expenses",
                "normal_balance": "debit",
                "description": "Costs incurred to generate revenue"
            }
        ]
    }

@router.get("/statistics")
async def get_ledger_statistics(
    branch_id: Optional[str] = Query(None, description="Filter by branch ID"),
    db: Session = Depends(get_db)
):
    """
    Get general ledger statistics and health metrics
    
    Returns key statistics about the ledger including account counts,
    transaction volumes, and balance verification.
    """
    try:
        ledger_service = GeneralLedgerService(db)
        
        # Get basic counts
        from app.models.accounting import AccountingCode, JournalEntry
        
        account_query = db.query(AccountingCode)
        if branch_id:
            account_query = account_query.filter(AccountingCode.branch_id == branch_id)
        
        account_counts = {
            'total_accounts': account_query.count(),
            'asset_accounts': account_query.filter(AccountingCode.account_type == AccountType.ASSET).count(),
            'liability_accounts': account_query.filter(AccountingCode.account_type == AccountType.LIABILITY).count(),
            'equity_accounts': account_query.filter(AccountingCode.account_type == AccountType.EQUITY).count(),
            'revenue_accounts': account_query.filter(AccountingCode.account_type == AccountType.REVENUE).count(),
            'expense_accounts': account_query.filter(AccountingCode.account_type == AccountType.EXPENSE).count(),
            'parent_accounts': account_query.filter(AccountingCode.is_parent == True).count()
        }
        
        # Get transaction counts
        from sqlalchemy import func
        today = date.today()
        
        transaction_stats = db.query(
            func.count(JournalEntry.id).label('total_entries'),
            func.sum(JournalEntry.debit_amount).label('total_debits'),
            func.sum(JournalEntry.credit_amount).label('total_credits')
        ).first()
        
        # Get trial balance to check if books are balanced
        trial_balance = ledger_service.get_trial_balance(branch_id=branch_id)
        
        return {
            'account_counts': account_counts,
            'transaction_stats': {
                'total_entries': transaction_stats.total_entries or 0,
                'total_debits': float(transaction_stats.total_debits or 0),
                'total_credits': float(transaction_stats.total_credits or 0),
                'is_balanced': abs(float(transaction_stats.total_debits or 0) - float(transaction_stats.total_credits or 0)) < 0.01
            },
            'trial_balance_status': {
                'is_balanced': trial_balance.get('totals', {}).get('is_balanced', False),
                'difference': trial_balance.get('totals', {}).get('difference', 0)
            },
            'last_updated': datetime.now().isoformat(),
            'branch_id': branch_id
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving ledger statistics: {str(e)}"
        )

@router.get("/debug")
async def debug_database_connection(db: Session = Depends(get_db)):
    """
    Debug endpoint to check database connectivity and data existence
    """
    try:
        from sqlalchemy import text, inspect
        import traceback

        # Test basic database connectivity
        result = db.execute(text("SELECT 1 as test")).fetchone()
        connection_test = result[0] if result else None

        # Get database engine info
        engine = db.bind
        inspector = inspect(engine)

        # List all tables
        tables = inspector.get_table_names()

        debug_info = {
            "database_connected": True,
            "connection_test": connection_test,
            "database_url": str(engine.url).replace(str(engine.url.password), "***") if engine.url.password else str(engine.url),
            "available_tables": tables,
            "accounting_tables_exist": {
                "accounting_codes": "accounting_codes" in tables,
                "journal_entries": "journal_entries" in tables,
                "accounting_entries": "accounting_entries" in tables,
                "opening_balances": "opening_balances" in tables
            }
        }

        # Only try to query if tables exist
        if "accounting_codes" in tables:
            try:
                from app.models.accounting import AccountingCode
                accounts_count = db.query(AccountingCode).count()
                debug_info["accounting_codes_count"] = accounts_count

                # Try to get one account
                sample_account = db.query(AccountingCode).first()
                if sample_account:
                    debug_info["sample_account"] = {
                        "id": sample_account.id,
                        "code": sample_account.code,
                        "name": sample_account.name,
                        "account_type": str(sample_account.account_type) if sample_account.account_type else None,
                    }
            except Exception as model_error:
                debug_info["accounting_model_error"] = str(model_error)

        if "journal_entries" in tables:
            try:
                from app.models.accounting import JournalEntry
                entries_count = db.query(JournalEntry).count()
                debug_info["journal_entries_count"] = entries_count
            except Exception as je_error:
                debug_info["journal_entries_error"] = str(je_error)

        return debug_info

    except Exception as e:
        import traceback
        return {
            "database_connected": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }

@router.get("/test-raw")
async def test_raw_database(db: Session = Depends(get_db)):
    """
    Test raw database queries without using models
    """
    try:
        from sqlalchemy import text

        # Test if accounting_codes table exists and has data
        result = db.execute(text("SELECT COUNT(*) FROM accounting_codes")).fetchone()
        accounts_count = result[0] if result else 0

        # Get a few sample accounts
        sample_accounts = db.execute(text("""
            SELECT id, code, name, account_type 
            FROM accounting_codes 
            LIMIT 5
        """)).fetchall()

        # Test journal_entries table
        entries_result = db.execute(text("SELECT COUNT(*) FROM journal_entries")).fetchone()
        entries_count = entries_result[0] if entries_result else 0

        # Get sample journal entries
        sample_entries = db.execute(text("""
            SELECT id, accounting_code_id, debit_amount, credit_amount, date
            FROM journal_entries 
            LIMIT 5
        """)).fetchall()

        return {
            "raw_query_success": True,
            "accounts_count": accounts_count,
            "journal_entries_count": entries_count,
            "sample_accounts": [
                {
                    "id": row[0],
                    "code": row[1], 
                    "name": row[2],
                    "account_type": row[3]
                } for row in sample_accounts
            ],
            "sample_entries": [
                {
                    "id": row[0],
                    "accounting_code_id": row[1],
                    "debit_amount": float(row[2]) if row[2] else 0,
                    "credit_amount": float(row[3]) if row[3] else 0,
                    "date": str(row[4]) if row[4] else None
                } for row in sample_entries
            ]
        }

    except Exception as e:
        import traceback
        return {
            "raw_query_success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.get("/seed-test-data")
async def seed_test_data(db: Session = Depends(get_db)):
    """
    Create some basic test data if the database is empty
    """
    try:
        from app.models.accounting import AccountingCode, JournalEntry, AccountingEntry
        from datetime import date
        import uuid

        # Check if we already have data
        existing_accounts = db.query(AccountingCode).count()
        if existing_accounts > 0:
            return {
                "message": "Data already exists",
                "existing_accounts": existing_accounts
            }

        # Create a few basic accounts
        accounts_data = [
            {"code": "1000", "name": "Assets", "account_type": "Asset", "category": "Assets", "is_parent": True},
            {"code": "1100", "name": "Current Assets", "account_type": "Asset", "category": "Current Assets", "is_parent": True},
            {"code": "1110", "name": "Cash", "account_type": "Asset", "category": "Current Assets", "is_parent": False},
            {"code": "2000", "name": "Liabilities", "account_type": "Liability", "category": "Liabilities", "is_parent": True},
            {"code": "3000", "name": "Equity", "account_type": "Equity", "category": "Equity", "is_parent": True},
            {"code": "4000", "name": "Revenue", "account_type": "Revenue", "category": "Revenue", "is_parent": True},
            {"code": "5000", "name": "Expenses", "account_type": "Expense", "category": "Expenses", "is_parent": True},
        ]

        created_accounts = []
        for acc_data in accounts_data:
            account = AccountingCode(
                id=str(uuid.uuid4()),
                code=acc_data["code"],
                name=acc_data["name"],
                account_type=acc_data["account_type"],
                category=acc_data["category"],
                is_parent=acc_data["is_parent"],
                balance=0.0,
                total_debits=0.0,
                total_credits=0.0
            )
            db.add(account)
            created_accounts.append(account)

        # Set up parent-child relationships
        for account in created_accounts:
            if account.code in ["1100"]:
                parent = next((a for a in created_accounts if a.code == "1000"), None)
                if parent:
                    account.parent_id = parent.id
            elif account.code in ["1110"]:
                parent = next((a for a in created_accounts if a.code == "1100"), None)
                if parent:
                    account.parent_id = parent.id

        db.commit()

        # Create a simple journal entry
        cash_account = next((a for a in created_accounts if a.code == "1110"), None)
        equity_account = next((a for a in created_accounts if a.code == "3000"), None)

        if cash_account and equity_account:
            # Create accounting entry header
            entry_header = AccountingEntry(
                id=str(uuid.uuid4()),
                date_prepared=date.today(),
                date_posted=date.today(),
                particulars="Initial capital investment",
                book="General Journal",
                status="posted"
            )
            db.add(entry_header)

            # Create journal entries
            cash_entry = JournalEntry(
                id=str(uuid.uuid4()),
                accounting_code_id=cash_account.id,
                accounting_entry_id=entry_header.id,
                date=date.today(),
                description="Initial capital - Cash",
                debit_amount=1000.00,
                credit_amount=0.00,
                entry_type="opening"
            )

            equity_entry = JournalEntry(
                id=str(uuid.uuid4()),
                accounting_code_id=equity_account.id,
                accounting_entry_id=entry_header.id,
                date=date.today(),
                description="Initial capital - Equity",
                debit_amount=0.00,
                credit_amount=1000.00,
                entry_type="opening"
            )

            db.add(cash_entry)
            db.add(equity_entry)

        db.commit()

        return {
            "message": "Test data created successfully",
            "accounts_created": len(created_accounts),
            "journal_entries_created": 2 if cash_account and equity_account else 0
        }

    except Exception as e:
        db.rollback()
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.post("/seed-one-entry")
async def seed_one_entry(db: Session = Depends(get_db)):
    """Create a single balanced journal entry (debit cash 100, credit equity 100).

    Useful when journals are empty so balances render in UI.
    """
    try:
        from sqlalchemy import text
        import uuid
        from datetime import date
        # Find cash-like and equity-like accounts
        cash_id = db.execute(text(
            "SELECT id FROM accounting_codes WHERE code IN ('1110','1120') OR LOWER(name) LIKE '%cash%' ORDER BY code LIMIT 1"
        )).scalar()
        equity_id = db.execute(text(
            "SELECT id FROM accounting_codes WHERE code IN ('3000','3100') OR LOWER(name) LIKE '%equity%' ORDER BY code LIMIT 1"
        )).scalar()

        if not cash_id or not equity_id:
            return {"success": False, "message": "Required accounts not found (cash/equity)"}

        # Determine a branch_id to satisfy NOT NULL constraint on accounting_entries.branch_id
        branch_id = db.execute(text(
            "SELECT id FROM branches WHERE active = 1 ORDER BY is_head_office DESC, code LIMIT 1"
        )).scalar() or db.execute(text("SELECT id FROM branches LIMIT 1")).scalar()
        if not branch_id:
            return {"success": False, "message": "No branch found to assign to entry"}

        entry_id = str(uuid.uuid4())
        today = date.today()

        # Insert header
        db.execute(text(
            "INSERT INTO accounting_entries (id, date_prepared, date_posted, particulars, book, status, branch_id, created_at, updated_at) "
            "VALUES (:id, :dp, :dp, :p, :b, :s, :branch_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ), {"id": entry_id, "dp": today, "p": "Seed entry", "b": "General Journal", "s": "posted", "branch_id": branch_id})

        # Debit cash
        db.execute(text(
            "INSERT INTO journal_entries (id, accounting_code_id, accounting_entry_id, date, description, debit_amount, credit_amount, entry_type, branch_id, created_at, updated_at) "
            "VALUES (:id, :aid, :eid, :d, :desc, :debit, 0.0, 'seed', :branch_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ), {"id": str(uuid.uuid4()), "aid": cash_id, "eid": entry_id, "d": today, "desc": "Seed debit cash", "debit": 100.0, "branch_id": branch_id})

        # Credit equity
        db.execute(text(
            "INSERT INTO journal_entries (id, accounting_code_id, accounting_entry_id, date, description, debit_amount, credit_amount, entry_type, branch_id, created_at, updated_at) "
            "VALUES (:id, :aid, :eid, :d, :desc, 0.0, :credit, 'seed', :branch_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ), {"id": str(uuid.uuid4()), "aid": equity_id, "eid": entry_id, "d": today, "desc": "Seed credit equity", "credit": 100.0, "branch_id": branch_id})

        db.commit()
        return {"success": True, "message": "Seeded one balanced journal entry", "debit_account_id": cash_id, "credit_account_id": equity_id, "branch_id": branch_id}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
