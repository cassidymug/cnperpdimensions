# Phase 4: Banking Module Deployment Guide

**Version**: 1.0
**Date**: October 23, 2025
**Status**: Ready for Production Deployment

## Table of Contents
1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Database Migration](#database-migration)
3. [Application Deployment](#application-deployment)
4. [Smoke Testing](#smoke-testing)
5. [Rollback Procedure](#rollback-procedure)
6. [Monitoring & Alerts](#monitoring--alerts)
7. [Post-Deployment Verification](#post-deployment-verification)

## Pre-Deployment Checklist

### Development Environment
- [ ] All tests passing (`pytest app/tests/test_banking_phase4.py -v`)
- [ ] No import errors or warnings
- [ ] Application starts without errors (`uvicorn app.main:app`)
- [ ] All 6 banking endpoints accessible
- [ ] Database schema changes reviewed

### Code Review
- [ ] Phase 4 design approved
- [ ] API endpoint specifications reviewed
- [ ] Service method implementations reviewed
- [ ] Test coverage acceptable (90%+)
- [ ] Error handling comprehensive

### Staging Verification
- [ ] Database backup created
- [ ] Backup verified and tested
- [ ] Rollback procedure documented
- [ ] Monitoring configured
- [ ] Performance baseline established

### Documentation
- [ ] API documentation complete
- [ ] Deployment guide reviewed
- [ ] Quick reference prepared
- [ ] User documentation ready

## Database Migration

### 1. Pre-Migration

**Step 1.1: Create Backup**
```powershell
# Backup current database
python scripts/backup_database.py --type full

# Verify backup
python scripts/verify_backup.py --latest
```

**Step 1.2: Verify Database State**
```sql
-- Connect to production database
SELECT COUNT(*) as transaction_count FROM bank_transactions;
SELECT COUNT(*) as reconciliation_count FROM bank_reconciliations;
```

**Step 1.3: Review Migration Script**
```powershell
# Review the migration (don't execute yet)
cat migrations/add_banking_dimensions.py
```

### 2. Execute Migration

**Step 2.1: Run Idempotent Migration**
```powershell
# Navigate to project root
cd c:\dev\cnperp-dimensions

# Run migration
python -m alembic upgrade head

# OR use custom migration script
python migrations/add_banking_dimensions.py --execute
```

**Step 2.2: Verify Migration Results**
```sql
-- Check new columns exist
SELECT column_name FROM information_schema.columns
WHERE table_name = 'bank_transactions'
AND column_name IN ('cost_center_id', 'project_id', 'department_id', 'posting_status')
ORDER BY column_name;

-- Verify bridge table created
SELECT COUNT(*) FROM information_schema.tables
WHERE table_name = 'bank_transfer_allocations';

-- Check indexes created
SELECT COUNT(*) as index_count FROM information_schema.statistics
WHERE table_name = 'bank_transfer_allocations';
```

**Expected Results**:
- 9 new columns in `bank_transactions`
- 3 new columns in `cash_submissions`
- 2 new columns in `float_allocations`
- 8 new columns in `bank_reconciliations`
- 1 new table `bank_transfer_allocations` (17 columns)
- 11 new indexes created

**Step 2.3: Validate Data Integrity**
```powershell
# Check for NULL constraints violations
python -c "
from app.core.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT COUNT(*) FROM bank_transactions WHERE cost_center_id IS NOT NULL'))
    print(f'Transactions with cost_center: {result.scalar()}')
"
```

### 3. Post-Migration Validation

**Step 3.1: Verify Foreign Keys**
```sql
-- Check FK constraints created
SELECT CONSTRAINT_NAME, TABLE_NAME, REFERENCED_TABLE_NAME
FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS
WHERE TABLE_NAME IN ('bank_transactions', 'bank_transfer_allocations');
```

**Step 3.2: Performance Test**
```powershell
# Test index performance
python scripts/test_index_performance.py --table bank_transactions

# Expected: < 100ms for period queries
```

## Application Deployment

### 1. Pre-Deployment Setup

**Step 1.1: Install Dependencies**
```powershell
# Update pip and tools
python -m pip install --upgrade pip setuptools wheel

# Install new dependencies (if any)
pip install -r requirements.txt --upgrade
```

**Step 1.2: Build and Test**
```powershell
# Run full test suite
pytest app/tests/test_banking_phase4.py -v --cov=app --cov-report=term-missing

# Build check
python -m py_compile app/services/banking_service.py
python -m py_compile app/routers/banking_dimensions.py
```

### 2. Deployment Steps

**Step 2.1: Deploy Code**
```powershell
# If using git (recommended)
git pull origin main

# OR manually copy files
Copy-Item "app\services\banking_service.py" "\\prod-server\app\services\" -Force
Copy-Item "app\routers\banking_dimensions.py" "\\prod-server\app\routers\" -Force
Copy-Item "app\models\banking.py" "\\prod-server\app\models\" -Force
Copy-Item "app\tests\test_banking_phase4.py" "\\prod-server\app\tests\" -Force
```

**Step 2.2: Update Configuration**
```powershell
# Update environment variables
$env:BANKING_RECONCILIATION_THRESHOLD = "1000.00"
$env:BANKING_VARIANCE_ALERT_THRESHOLD = "5000.00"

# Verify settings
python -c "import os; print(os.getenv('BANKING_RECONCILIATION_THRESHOLD'))"
```

**Step 2.3: Restart Application**
```powershell
# Stop existing service
Stop-Service CNPERP

# Start service
Start-Service CNPERP

# Verify running
Get-Service CNPERP | Select-Object Name, Status
```

**Step 2.4: Verify Endpoints**
```powershell
# Test endpoint availability
$endpoints = @(
    "http://localhost:8010/api/v1/banking/transactions/test-id/post-accounting",
    "http://localhost:8010/api/v1/banking/reconciliation",
    "http://localhost:8010/api/v1/banking/cash-position",
    "http://localhost:8010/api/v1/banking/transfer-tracking",
    "http://localhost:8010/api/v1/banking/dimensional-analysis",
    "http://localhost:8010/api/v1/banking/variance-report"
)

foreach ($endpoint in $endpoints) {
    try {
        $response = Invoke-WebRequest -Uri $endpoint -Method GET -ErrorAction Stop
        Write-Host "✅ $endpoint - $($response.StatusCode)"
    } catch {
        Write-Host "❌ $endpoint - Failed"
    }
}
```

## Smoke Testing

### 1. Basic Connectivity

**Step 1.1: Health Check**
```powershell
curl http://localhost:8010/docs
# Expected: 200 OK with Swagger UI
```

**Step 1.2: Database Connectivity**
```powershell
python -c "
from app.core.database import engine
from app.models.banking import BankTransaction
try:
    engine.connect()
    print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
"
```

### 2. API Endpoint Testing

**Step 2.1: Create Test Data**
```powershell
# Create test transaction
python -c "
from app.core.database import SessionLocal
from app.models.banking import BankTransaction
from datetime import date
from decimal import Decimal

db = SessionLocal()
txn = BankTransaction(
    id='smoke-test-1',
    transaction_type='deposit',
    amount=Decimal('5000.00'),
    transaction_date=date.today(),
    bank_account_id='ba-op',
    branch_id='test-branch',
    cost_center_id='cc-hq',
    posting_status='draft'
)
db.add(txn)
db.commit()
print('✅ Test transaction created')
db.close()
"
```

**Step 2.2: Test Each Endpoint**

```powershell
# 1. POST /api/v1/banking/transactions/{id}/post-accounting
$response = Invoke-WebRequest -Uri "http://localhost:8010/api/v1/banking/transactions/smoke-test-1/post-accounting" `
    -Method POST `
    -ContentType "application/json" `
    -Body '{"user_id":"test-user-1"}'
Write-Host "Endpoint 1 Response: $($response.StatusCode)"

# 2. GET /api/v1/banking/reconciliation
$response = Invoke-WebRequest -Uri "http://localhost:8010/api/v1/banking/reconciliation?bank_account_id=ba-op&period=2025-10" `
    -Method GET
Write-Host "Endpoint 2 Response: $($response.StatusCode)"

# 3. GET /api/v1/banking/cash-position
$response = Invoke-WebRequest -Uri "http://localhost:8010/api/v1/banking/cash-position?bank_account_id=ba-op&period=2025-10" `
    -Method GET
Write-Host "Endpoint 3 Response: $($response.StatusCode)"

# 4. GET /api/v1/banking/transfer-tracking
$response = Invoke-WebRequest -Uri "http://localhost:8010/api/v1/banking/transfer-tracking?bank_account_id=ba-op" `
    -Method GET
Write-Host "Endpoint 4 Response: $($response.StatusCode)"

# 5. GET /api/v1/banking/dimensional-analysis
$response = Invoke-WebRequest -Uri "http://localhost:8010/api/v1/banking/dimensional-analysis?bank_account_id=ba-op&period=2025-10" `
    -Method GET
Write-Host "Endpoint 5 Response: $($response.StatusCode)"

# 6. GET /api/v1/banking/variance-report
$response = Invoke-WebRequest -Uri "http://localhost:8010/api/v1/banking/variance-report?bank_account_id=ba-op&period=2025-10" `
    -Method GET
Write-Host "Endpoint 6 Response: $($response.StatusCode)"
```

**Expected Results**: All endpoints return HTTP 200 with valid JSON

### 3. Data Validation

**Step 3.1: Verify GL Entries Created**
```powershell
python -c "
from app.core.database import SessionLocal
from app.models.accounting import JournalEntry
db = SessionLocal()
entries = db.query(JournalEntry).filter(
    JournalEntry.reference.like('%smoke-test-1%')
).all()
print(f'GL entries created: {len(entries)}')
if entries:
    for e in entries:
        print(f'  - Debit: {e.debit}, Credit: {e.credit}')
db.close()
"
```

**Step 3.2: Verify Dimensions Assigned**
```powershell
python -c "
from app.core.database import SessionLocal
from app.models.accounting import JournalEntry
db = SessionLocal()
entry = db.query(JournalEntry).filter(
    JournalEntry.reference.like('%smoke-test-1%')
).first()
if entry:
    print(f'Dimension assignments: {len(entry.dimension_assignments)}')
db.close()
"
```

## Rollback Procedure

### If Deployment Fails

**Step 1: Stop Application**
```powershell
Stop-Service CNPERP
```

**Step 2: Restore Previous Code**
```powershell
git revert HEAD  # If using git
# OR
Copy-Item "backup\app\services\banking_service.py" "app\services\" -Force
```

**Step 3: Restore Database** (If migration failed)
```powershell
# Restore from backup
python scripts/restore_backup.py --backup-file latest --execute

# Verify restoration
python -c "
from app.core.database import engine
engine.connect()
print('✅ Database restored')
"
```

**Step 4: Restart Application**
```powershell
Start-Service CNPERP

# Verify
Get-Service CNPERP | Select-Object Name, Status
```

**Step 5: Verify Rollback**
```powershell
# Test endpoints still work
curl http://localhost:8010/api/v1/sales/invoices
# Should return 200
```

## Monitoring & Alerts

### 1. Set Up Monitoring

**Step 1.1: Application Logs**
```powershell
# Monitor logs in real-time
Get-Content app.log -Wait -Tail 50

# Search for errors
Select-String "ERROR|EXCEPTION" app.log | Tail -20
```

**Step 1.2: Database Performance**
```sql
-- Monitor slow queries
SELECT * FROM performance_schema.events_statements_summary_by_digest
WHERE SUM_TIMER_WAIT > 1000000000000  -- 1 second
ORDER BY SUM_TIMER_WAIT DESC
LIMIT 10;
```

**Step 1.3: API Performance**
```powershell
# Test response times
$start = Get-Date
$response = Invoke-WebRequest -Uri "http://localhost:8010/api/v1/banking/cash-position?bank_account_id=ba-op&period=2025-10"
$duration = (Get-Date) - $start
Write-Host "Response time: $($duration.TotalMilliseconds)ms"
# Expected: < 500ms
```

### 2. Configure Alerts

**Step 2.1: Error Alerts**
```powershell
# Monitor for errors and alert
while($true) {
    $errors = Select-String "ERROR|EXCEPTION" app.log -Raw | Measure-Object -Line
    if ($errors.Lines -gt 100) {
        # Send alert
        Send-AlertEmail -Subject "CNPERP Banking Module Errors" `
            -Body "More than 100 errors detected in logs"
    }
    Start-Sleep -Seconds 60
}
```

**Step 2.2: Reconciliation Alerts**
```powershell
# Alert if large variance detected
python -c "
from app.core.database import SessionLocal
from app.models.banking import BankReconciliation
from decimal import Decimal

db = SessionLocal()
recent = db.query(BankReconciliation).order_by(
    BankReconciliation.reconciliation_date.desc()
).first()

if recent and recent.variance > Decimal('5000.00'):
    print(f'⚠️ ALERT: Large variance detected: {recent.variance}')
db.close()
"
```

## Post-Deployment Verification

### 1. Functional Verification

**Step 1.1: Run Full Test Suite**
```powershell
pytest app/tests/test_banking_phase4.py -v --tb=short

# Expected: All tests passing
```

**Step 1.2: API Integration Test**
```powershell
# Run integration test suite (when available)
pytest app/tests/integration/test_banking_integration.py -v
```

**Step 1.3: Data Integrity Check**
```sql
-- Verify GL balancing
SELECT
    reference,
    SUM(debit) as total_debit,
    SUM(credit) as total_credit,
    ABS(SUM(debit) - SUM(credit)) as imbalance
FROM journal_entries
GROUP BY reference
HAVING imbalance > 0.01;
-- Expected: Empty result set
```

### 2. Performance Verification

**Step 2.1: Reconciliation Performance**
```powershell
# Test with real data
$start = Get-Date
python -c "
import asyncio
from app.core.database import SessionLocal
from app.services.banking_service import BankingService

async def test():
    db = SessionLocal()
    service = BankingService(db)
    result = await service.reconcile_banking_by_dimension('ba-op', '2025-10')
    print(f'Reconciliation result: {result}')
    db.close()

asyncio.run(test())
"
$duration = (Get-Date) - $start
Write-Host "Reconciliation time: $($duration.TotalSeconds)s"
# Expected: < 5 seconds for monthly data
```

**Step 2.2: Cache Verification**
```sql
-- Check query cache hit rate
SELECT
    (SUM_TIMER_WAIT - SUM_TIMER_READ) / SUM_TIMER_WAIT as cache_hit_ratio
FROM performance_schema.events_statements_summary_by_digest
LIMIT 1;
```

### 3. User Acceptance Verification

**Step 3.1: Demo Scenario**
1. Create bank transaction with dimensions
2. Post to GL
3. Verify GL entries created
4. Run reconciliation
5. Check cash position by dimension
6. Generate variance report

**Step 3.2: Get Sign-Off**
- [ ] Business analyst approves functionality
- [ ] Finance approves GL reconciliation
- [ ] Operations approves performance
- [ ] IT approves stability

## Troubleshooting

### Issue: Migration Fails

**Solution**:
```powershell
# Check migration status
alembic current

# Rollback to previous version
alembic downgrade -1

# Check logs for specific error
type migration.log | tail -50
```

### Issue: Endpoints Return 500 Error

**Solution**:
```powershell
# Check application logs
Get-Content app.log | Select-String "ERROR" | tail -50

# Verify service methods are loaded
python -c "from app.services.banking_service import BankingService; print('Service imported successfully')"
```

### Issue: Slow Response Times

**Solution**:
```sql
-- Check for missing indexes
SELECT * FROM information_schema.statistics
WHERE table_name = 'bank_transactions'
ORDER BY column_name;

-- Check index usage
SELECT object_schema, object_name, count_read, count_write
FROM performance_schema.table_io_waits_summary
WHERE object_name IN ('bank_transactions', 'bank_transfer_allocations');
```

### Issue: GL Entries Not Balanced

**Solution**:
1. Check service method logging
2. Verify GL account configuration
3. Manual audit of recent postings
4. Restore from backup if necessary

## Deployment Rollback Decision Tree

```
Smoke Tests Pass?
├─ YES → Monitor for 1 hour
│         └─ Errors Detected?
│             ├─ YES → Execute Rollback Procedure
│             └─ NO → DEPLOYMENT COMPLETE ✅
└─ NO → Execute Rollback Procedure
        └─ Investigate Errors
            └─ Fix Issues
                └─ Redeploy
```

## Post-Deployment Support

### First 24 Hours
- Monitor application logs continuously
- Check for unusual error patterns
- Verify GL reconciliation accuracy
- Monitor API response times

### First Week
- Daily reconciliation verification
- Weekly performance analysis
- Collect user feedback
- Plan Phase 4 Task 8 (Integration Testing)

### Ongoing
- Monthly reconciliation audits
- Quarterly performance reviews
- Bi-annual disaster recovery drills

---

**Deployment Completed**: ___________
**Verified By**: ___________
**Date**: ___________

*For questions or issues, contact the CNPERP Development Team*
