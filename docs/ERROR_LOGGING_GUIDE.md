# Error Logging Implementation Guide

## Overview

This guide explains how error logging has been implemented across the CNPERP ERP system to help track and fix errors effectively.

## Logging Utility

A centralized logging utility has been created at `app/utils/logger.py` with the following features:

### Features

1. **File Rotation** - Prevents disk space issues (10MB max per file, 5 backups)
2. **Separate Error Log** - Critical errors logged to `logs/errors.log`
3. **Performance Tracking** - Track function execution times
4. **Consistent Formatting** - Standardized log format across all modules
5. **Multiple Log Levels** - DEBUG, INFO, WARNING, ERROR, CRITICAL

### Log Files

- **logs/app.log** - Main application log (DEBUG and above)
- **logs/errors.log** - Error log only (ERROR and above)
- **logs/performance.log** - Performance metrics

## How to Add Logging to Modules

### 1. Import the Logger

At the top of your Python file, add:

```python
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)
```

### 2. Router/Endpoint Logging

For API endpoints in `app/routers/` or `app/api/v1/endpoints/`:

```python
@router.post("/items/", response_model=ItemResponse)
def create_item(
    item_data: ItemCreate,
    db: Session = Depends(get_db)
):
    """Create a new item"""
    try:
        logger.info(f"Creating item: {item_data.name}")

        # Your business logic here
        service = ItemService(db)
        item = service.create_item(item_data)

        logger.info(f"Successfully created item: {item.id} - {item.name}")
        return ItemResponse.from_orm(item)

    except ValueError as e:
        # Validation errors (400)
        log_error_with_context(
            logger,
            "Validation error creating item",
            item_name=item_data.name,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Unexpected errors (500)
        log_exception(logger, e, context=f"Error creating item: {item_data.name}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error creating item"
        )
```

### 3. Service Layer Logging

For business logic in `app/services/`:

```python
class ItemService:
    """Service for managing items"""

    def __init__(self, db: Session):
        self.db = db

    def create_item(self, item_data: ItemCreate) -> Item:
        """Create a new item"""
        try:
            logger.debug(f"Creating item: {item_data.name}")

            item = Item(**item_data.dict())
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)

            logger.info(f"Successfully created item: {item.id}")
            return item

        except IntegrityError as e:
            self.db.rollback()
            error_msg = f"Item with SKU '{item_data.sku}' already exists"
            log_error_with_context(
                logger,
                error_msg,
                sku=item_data.sku,
                name=item_data.name
            )
            raise ValueError(error_msg)

        except Exception as e:
            self.db.rollback()
            log_exception(logger, e, context=f"Error creating item: {item_data.name}")
            raise
```

### 4. Database Operations Logging

For complex queries or database operations:

```python
def get_items_with_low_stock(self, branch_id: str) -> List[Item]:
    """Get items with stock below reorder point"""
    try:
        logger.debug(f"Fetching low stock items for branch: {branch_id}")

        items = self.db.query(Item).filter(
            Item.branch_id == branch_id,
            Item.quantity < Item.reorder_point
        ).all()

        logger.info(f"Found {len(items)} low stock items in branch {branch_id}")
        return items

    except Exception as e:
        log_exception(
            logger,
            e,
            context=f"Error fetching low stock items for branch: {branch_id}"
        )
        raise
```

### 5. Background Task Logging

For async operations or background tasks:

```python
from app.utils.logger import async_exception_handler

@async_exception_handler(logger)
async def process_sales_report(branch_id: str):
    """Generate and email sales report"""
    logger.info(f"Starting sales report generation for branch: {branch_id}")

    # Your async code here
    report = await generate_report(branch_id)
    await send_email(report)

    logger.info(f"Successfully sent sales report for branch: {branch_id}")
```

### 6. Performance Tracking

For operations that might be slow:

```python
from app.utils.logger import PerformanceLogger

def generate_financial_statements(year: int, month: int):
    """Generate monthly financial statements"""
    with PerformanceLogger(f"Financial statements {year}-{month:02d}", logger):
        # Your code here
        statements = calculate_statements(year, month)
        return statements
```

Or as a decorator:

```python
from app.utils.logger import performance_tracker

@performance_tracker(logger)
def calculate_cogs(sale_id: str) -> float:
    """Calculate cost of goods sold"""
    # Your expensive calculation here
    return total_cogs
```

## Logging Best Practices

### 1. Use Appropriate Log Levels

- **DEBUG**: Detailed diagnostic information (disabled in production)
- **INFO**: General informational messages (successful operations)
- **WARNING**: Something unexpected but not an error
- **ERROR**: Error that needs attention
- **CRITICAL**: Severe error that might cause system failure

### 2. Include Context

Always include relevant context in your log messages:

```python
# Good ✅
logger.error(f"Failed to process sale: {sale_id} for customer: {customer_id}")

# Bad ❌
logger.error("Failed to process sale")
```

### 3. Use Structured Logging

Use `log_error_with_context` for key-value pairs:

```python
log_error_with_context(
    logger,
    "Payment processing failed",
    sale_id=sale.id,
    amount=sale.total,
    payment_method=payment.method,
    error_code=error.code
)
```

### 4. Don't Log Sensitive Data

Never log passwords, credit card numbers, or other sensitive information:

```python
# Good ✅
logger.info(f"User logged in: {user.username}")

# Bad ❌
logger.info(f"Login attempt: {username} / {password}")
```

### 5. Log Before and After Operations

For critical operations, log both start and completion:

```python
logger.info(f"Starting bank reconciliation for account: {account_id}")
try:
    result = reconcile_account(account_id)
    logger.info(f"Bank reconciliation completed: {account_id} - {result.matched_transactions} transactions matched")
except Exception as e:
    log_exception(logger, e, context=f"Bank reconciliation failed: {account_id}")
    raise
```

## Viewing Logs

### View All Logs

```bash
# View main log file
tail -f logs/app.log

# View error log only
tail -f logs/errors.log

# View performance log
tail -f logs/performance.log
```

### Search Logs

```bash
# Find all errors
grep "ERROR" logs/app.log

# Find specific operation
grep "Creating sale" logs/app.log

# Find errors for specific module
grep "app.services.sales_service" logs/errors.log
```

### Windows PowerShell

```powershell
# View last 50 lines
Get-Content logs\app.log -Tail 50

# Follow log in real-time
Get-Content logs\app.log -Wait -Tail 50

# Find errors
Select-String "ERROR" logs\app.log
```

## Files Updated

### Core Logging

- ✅ `app/utils/logger.py` - Centralized logging utility (NEW)

### Routers

- ✅ `app/routers/accounting_dimensions.py` - Added comprehensive error logging
- ⏳ `app/routers/banking_dimensions.py` - TODO
- ⏳ `app/routers/dimensional_reports.py` - TODO
- ⏳ `app/api/v1/endpoints/*.py` - TODO (40+ files)

### Services

- ✅ `app/services/accounting_dimensions_service.py` - Added error logging
- ⏳ `app/services/*.py` - TODO (30+ files)

### Models

- ⏳ `app/models/*.py` - TODO (add logging to complex operations)

## Next Steps

To complete error logging implementation across the entire application:

1. **Add logger imports** to all remaining router files
2. **Wrap endpoints** with try-except blocks
3. **Add service-level logging** to all service classes
4. **Add database operation logging** to complex queries
5. **Test logging** by triggering various errors
6. **Set up log monitoring** (optional: integrate with log aggregation service)

## Testing Error Logging

Test that errors are being logged correctly:

```python
# In your test file
def test_error_logging():
    """Test that errors are properly logged"""
    import logging
    from app.utils.logger import get_logger

    logger = get_logger("test")

    try:
        # Trigger an error
        raise ValueError("Test error")
    except ValueError as e:
        log_exception(logger, e, context="Testing error logging")

    # Check that error was logged to file
    with open("logs/errors.log", "r") as f:
        logs = f.read()
        assert "Test error" in logs
```

## Support

For questions or issues with logging:
1. Check this guide
2. Review `app/utils/logger.py` for available functions
3. Look at examples in updated files
4. Ensure logs directory exists and is writable

---

**Last Updated**: October 28, 2025
**Status**: Implementation in progress
