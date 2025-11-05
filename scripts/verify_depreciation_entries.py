"""
Verify depreciation accounting entries were created
"""
from app.core.database import SessionLocal
from app.models.accounting import AccountingEntry, JournalEntry
import warnings
warnings.filterwarnings('ignore')

db = SessionLocal()

entries = db.query(AccountingEntry).filter(
    AccountingEntry.particulars.like('%Depreciation%')
).order_by(AccountingEntry.created_at.desc()).limit(3).all()

print(f'\n✅ Accounting Entries Created: {len(entries)}\n')

for e in entries:
    print(f'📊 {e.date_posted}: {e.particulars}')
    print(f'   Book: {e.book} | Status: {e.status}')

    je = db.query(JournalEntry).filter(
        JournalEntry.accounting_entry_id == e.id
    ).all()

    for j in je:
        amount = float(j.debit_amount or 0) + float(j.credit_amount or 0)
        print(f'   {j.entry_type.upper():6s}: P{amount:,.2f} - {j.narration}')
    print()

db.close()
