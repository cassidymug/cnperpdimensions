from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
from app.core.db_utils import resolve_database_url
import logging, re

logger = logging.getLogger("db.init")

def _mask(url: str) -> str:
    if not url:
        return url
    return re.sub(r":([^:@/]+)@", r":****@", url)

original_url = settings.database_url
resolved_url = resolve_database_url(original_url)
if resolved_url != original_url:
    logger.info("Database URL adjusted for environment (WSL gateway logic applied)")

logger.info(f"Initializing DB engine: original={_mask(original_url)} resolved={_mask(resolved_url)}")

engine = create_engine(
    resolved_url,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        # Lightweight bootstrap for IFRS tags when startup events didn't run (e.g., direct dependency usage in tests)
        try:
            from app.models.accounting import AccountingCode
            needed = {
                'Inventory': 'A1.3',
                'Cash': 'A1.1',
                'Petty Cash': 'A1.1',
                'Accounts Payable': 'L1.1',
                'VAT Receivable': 'A1.2'
            }
            updated = 0
            created = 0
            # First, ensure core accounts exist (create if entirely missing)
            minimal_accounts_def = [
                # code, name, account_type, category, reporting_tag
                ('1000', 'Cash', 'Asset', 'Current Assets', 'A1.1'),
                ('1010', 'Petty Cash', 'Asset', 'Current Assets', 'A1.1'),
                ('1200', 'VAT Receivable', 'Asset', 'Trade and Other Receivables', 'A1.2'),
                ('1300', 'Inventory', 'Asset', 'Inventories', 'A1.3'),
                ('2100', 'Accounts Payable', 'Liability', 'Trade and Other Payables', 'L1.1'),
            ]
            for code_val, name, acct_type, category, tag in minimal_accounts_def:
                existing = db.query(AccountingCode).filter(
                    (AccountingCode.code == code_val) | (AccountingCode.name == name)
                ).first()
                if not existing:
                    acct = AccountingCode(
                        code=code_val,
                        name=name,
                        account_type=acct_type,
                        category=category,
                        is_parent=False,
                        reporting_tag=tag,
                    )
                    db.add(acct)
                    created += 1
            if created:
                db.flush()  # obtain IDs so tagging loop below can work uniformly
            for name, tag in needed.items():
                code = db.query(AccountingCode).filter(AccountingCode.name.ilike(f"%{name}%"), AccountingCode.reporting_tag.is_(None)).first()
                if code:
                    code.reporting_tag = tag
                    updated += 1
            if updated or created:
                db.commit()
        except Exception:
            # Suppress any bootstrap errors to avoid masking primary DB usage errors
            pass
        yield db
    finally:
        db.close()