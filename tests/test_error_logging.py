"""
Test Error Logging System

This script tests the error logging implementation to ensure
errors are being captured and logged correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.logger import (
    get_logger,
    log_exception,
    log_error_with_context,
    PerformanceLogger,
    performance_tracker
)
import time


def test_basic_logging():
    """Test basic logging functionality"""
    print("\n" + "="*60)
    print("TEST 1: Basic Logging")
    print("="*60)

    logger = get_logger("test.basic")

    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")
    logger.critical("This is a CRITICAL message")

    print("✅ Basic logging test completed")
    print("   Check logs/app.log for all messages")
    print("   Check logs/errors.log for ERROR and CRITICAL only")


def test_exception_logging():
    """Test exception logging"""
    print("\n" + "="*60)
    print("TEST 2: Exception Logging")
    print("="*60)

    logger = get_logger("test.exceptions")

    try:
        # Trigger an exception
        result = 10 / 0
    except Exception as e:
        log_exception(logger, e, context="Testing exception logging")

    print("✅ Exception logging test completed")
    print("   Check logs/errors.log for full stack trace")


def test_contextual_logging():
    """Test logging with context"""
    print("\n" + "="*60)
    print("TEST 3: Contextual Error Logging")
    print("="*60)

    logger = get_logger("test.context")

    log_error_with_context(
        logger,
        "Sample error with context",
        user_id="12345",
        operation="create_sale",
        amount=150.50,
        branch="MAIN",
        timestamp="2025-10-28 10:30:00"
    )

    print("✅ Contextual logging test completed")
    print("   Check logs/errors.log for structured error with context")


def test_performance_logging():
    """Test performance tracking"""
    print("\n" + "="*60)
    print("TEST 4: Performance Logging")
    print("="*60)

    logger = get_logger("test.performance")

    # Test with context manager
    with PerformanceLogger("test_operation", logger):
        time.sleep(0.1)  # Simulate work

    # Test with decorator
    @performance_tracker(logger)
    def slow_function():
        time.sleep(0.2)  # Simulate slow operation
        return "completed"

    result = slow_function()

    print("✅ Performance logging test completed")
    print("   Check logs/app.log for performance metrics")


def test_nested_logging():
    """Test logging in nested operations"""
    print("\n" + "="*60)
    print("TEST 5: Nested Operations Logging")
    print("="*60)

    logger = get_logger("test.nested")

    logger.info("Starting main operation")

    try:
        logger.debug("Step 1: Validating data")
        # Simulate validation
        time.sleep(0.05)

        logger.debug("Step 2: Processing transaction")
        # Simulate processing
        time.sleep(0.05)

        logger.debug("Step 3: Updating database")
        # Simulate error in database update
        raise ValueError("Database connection lost")

    except ValueError as e:
        log_exception(logger, e, context="Error in nested operation")
        logger.warning("Rolling back transaction")
    finally:
        logger.info("Operation completed (with errors)")

    print("✅ Nested logging test completed")
    print("   Check logs/app.log for operation flow")
    print("   Check logs/errors.log for error details")


def test_log_file_existence():
    """Verify log files are created"""
    print("\n" + "="*60)
    print("TEST 6: Log File Verification")
    print("="*60)

    logs_dir = project_root / "logs"
    app_log = logs_dir / "app.log"
    error_log = logs_dir / "errors.log"

    print(f"Logs directory: {logs_dir}")
    print(f"  Exists: {logs_dir.exists()}")

    print(f"\nApp log: {app_log}")
    print(f"  Exists: {app_log.exists()}")
    if app_log.exists():
        size = app_log.stat().st_size
        print(f"  Size: {size:,} bytes")

    print(f"\nError log: {error_log}")
    print(f"  Exists: {error_log.exists()}")
    if error_log.exists():
        size = error_log.stat().st_size
        print(f"  Size: {size:,} bytes")

    if app_log.exists() and error_log.exists():
        print("\n✅ Log files verified")
    else:
        print("\n❌ Some log files are missing!")


def main():
    """Run all logging tests"""
    print("\n" + "="*60)
    print("ERROR LOGGING SYSTEM TEST")
    print("="*60)
    print("\nThis script will test the error logging implementation.")
    print("Watch the console output and then check the log files.")

    # Run tests
    test_basic_logging()
    test_exception_logging()
    test_contextual_logging()
    test_performance_logging()
    test_nested_logging()
    test_log_file_existence()

    # Final summary
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)
    print("\n📁 Log Files:")
    print("   - logs/app.log      (All log messages)")
    print("   - logs/errors.log   (Errors only)")
    print("\n📝 Next Steps:")
    print("   1. Review the log files")
    print("   2. Verify error messages include stack traces")
    print("   3. Check that performance metrics are logged")
    print("   4. Ensure log rotation is working (check file sizes)")
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
