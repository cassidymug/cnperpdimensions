from sqlalchemy.orm import Session

from app.models.accounting import AccountingCode
from app.services.ifrs_reporting_service import IFRSReportingService

from .registry import register

SEED_CODES = [
    ("1000","Assets","Asset","group"),
    ("1100","Current Assets","Asset","group"),
    ("1110","Cash and Cash Equivalents","Asset","detail"),
    ("1120","Bank Accounts","Asset","detail"),
    ("1130","Accounts Receivable","Asset","detail"),
    ("1140","Inventory","Asset","detail"),
    ("1160","VAT Receivable (Input VAT)","Asset","detail"),
    ("1200","Fixed Assets","Asset","group"),
    ("1210","Property, Plant & Equipment","Asset","detail"),
    ("1220","Accumulated Depreciation","Asset","detail"),
    ("2000","Liabilities","Liability","group"),
    ("2100","Current Liabilities","Liability","group"),
    ("2110","Accounts Payable - Trade Suppliers","Liability","detail"),
    ("2120","Accrued Expenses","Liability","detail"),
    ("2130","Tax Liabilities","Liability","group"),
    ("2131","VAT Control","Liability","group"),
    ("2132","VAT Payable (Output VAT)","Liability","detail"),
    ("2133","VAT Receivable (Input VAT - Contra)","Liability","detail"),
    ("3000","Equity","Equity","group"),
    ("3100","Share Capital","Equity","detail"),
    ("3200","Retained Earnings","Equity","detail"),
    ("3300","Capital Reserves","Equity","detail"),
    ("4000","Revenue","Revenue","group"),
    ("4100","Operating Revenue","Revenue","detail"),
    ("4200","Other Revenue","Revenue","detail"),
    ("5000","Expenses","Expense","group"),
    ("5100","Cost of Goods Sold","Expense","detail"),
    ("5200","Operating Expenses","Expense","detail"),
    ("5210","Selling Expenses","Expense","detail"),
    ("5220","Administrative Expenses","Expense","detail"),
    ("5230","Utilities","Expense","detail"),
]
PARENTS = {
    "1100":"1000","1110":"1100","1120":"1100","1130":"1100","1140":"1100","1160":"1100",
    "1200":"1000","1210":"1200","1220":"1200",
    "2100":"2000","2110":"2100","2120":"2100","2130":"2100",
    "2131":"2130","2132":"2131","2133":"2131",
    "3100":"3000","3200":"3000","3300":"3000",
    "4100":"4000","4200":"4000",
    "5100":"5000","5200":"5000","5210":"5200","5220":"5200","5230":"5200"
}

@register("accounts")
def seed_accounts(db: Session):
    existing = {c.code: c for c in db.query(AccountingCode).all()}
    missing_tags = []

    for code, name, a_type, cat in SEED_CODES:
        if code in existing:
            obj = existing[code]; ch=False
            if obj.name!=name: obj.name=name; ch=True
            if obj.account_type!=a_type: obj.account_type=a_type; ch=True
            if obj.category!=cat: obj.category=cat; ch=True
            recommended_tag = IFRSReportingService.determine_reporting_tag(
                account_type=a_type,
                category=cat,
                name=name,
                code=code
            )
            if recommended_tag and obj.reporting_tag != recommended_tag:
                obj.reporting_tag = recommended_tag
                ch = True
            elif not recommended_tag:
                missing_tags.append((code, name))
            if ch: db.add(obj)
        else:
            obj = AccountingCode(code=code,name=name,account_type=a_type,category=cat,is_parent=True)
            recommended_tag = IFRSReportingService.determine_reporting_tag(
                account_type=a_type,
                category=cat,
                name=name,
                code=code
            )
            if recommended_tag:
                obj.reporting_tag = recommended_tag
            else:
                missing_tags.append((code, name))
            db.add(obj); db.flush(); existing[code]=obj
    db.flush()
    for child_code,parent_code in PARENTS.items():
        c = existing[child_code]; p = existing[parent_code]
        if c.parent_id != p.id:
            c.parent_id = p.id; db.add(c)
        if not p.is_parent:
            p.is_parent = True; db.add(p)
    child_parent_ids = {c.parent_id for c in existing.values() if c.parent_id}
    for obj in existing.values():
        obj.is_parent = (obj.id in child_parent_ids)
        db.add(obj)
    db.commit()

    if missing_tags:
        missing_preview = ", ".join(f"{code} {name}" for code, name in missing_tags[:5])
        extra = "..." if len(missing_tags) > 5 else ""
        print(
            f"[SEED][IFRS] WARNING: {len(missing_tags)} accounting codes lacked automatic IFRS tags: {missing_preview}{extra}"
        )
