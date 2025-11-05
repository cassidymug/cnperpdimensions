"""
Centralized Logging Configuration for CNPERP ERP System

This module provides a standardized logging setup with:
- File rotation to prevent disk space issues
- Separate error log file for critical issues
- Consistent formatting across all modules
- Performance tracking capabilities
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
from functools import wraps
from typing import Callable, Any
import traceback

# Create logs directory if it doesn't exist
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

# Log file paths
APP_LOG_FILE = LOGS_DIR / "app.log"
ERROR_LOG_FILE = LOGS_DIR / "errors.log"
PERFORMANCE_LOG_FILE = LOGS_DIR / "performance.log"

# Log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Max log file size (10 MB)
MAX_BYTES = 10 * 1024 * 1024
# Keep 5 backup files
BACKUP_COUNT = 5


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Create a configured logger instance.

    Args:
        name: Logger name (typically __name__ of the module)
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    # Console handler - INFO and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    console_handler.setFormatter(console_formatter)

    # Main app log file handler - DEBUG and above
    file_handler = RotatingFileHandler(
        APP_LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    file_handler.setFormatter(file_formatter)

    # Error log file handler - ERROR and above
    error_handler = RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d]\n"
        "Message: %(message)s\n"
        "%(exc_info)s\n",
        DATE_FORMAT
    )
    error_handler.setFormatter(error_formatter)

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger instance.

    Args:
        name: Logger name (typically __name__ of the module)

    Returns:
        Configured logger instance
    """
    return setup_logger(name)


def log_exception(logger: logging.Logger, error: Exception, context: str = "") -> None:
    """
    Log an exception with full traceback.

    Args:
        logger: Logger instance
        error: Exception to log
        context: Additional context information
    """
    error_msg = f"{context}\n" if context else ""
    error_msg += f"Exception Type: {type(error).__name__}\n"
    error_msg += f"Exception Message: {str(error)}\n"
    error_msg += f"Traceback:\n{traceback.format_exc()}"

    logger.error(error_msg)


def log_error_with_context(logger: logging.Logger, message: str, **kwargs) -> None:
    """
    Log an error with additional context information.

    Args:
        logger: Logger instance
        message: Error message
        **kwargs: Additional context as key-value pairs
    """
    context = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    full_message = f"{message} | Context: {context}" if context else message
    logger.error(full_message)


def exception_handler(logger: logging.Logger = None):
    """
    Decorator to handle exceptions and log them.

    Usage:
        @exception_handler(logger)
        def my_function():
            # Your code here

    Args:
        logger: Logger instance (if None, creates a default logger)
    """
    def decorator(func: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_exception(
                    logger,
                    e,
                    context=f"Error in {func.__module__}.{func.__name__}"
                )
                raise

        return wrapper

    return decorator


def async_exception_handler(logger: logging.Logger = None):
    """
    Decorator to handle exceptions in async functions and log them.

    Usage:
        @async_exception_handler(logger)
        async def my_async_function():
            # Your async code here

    Args:
        logger: Logger instance (if None, creates a default logger)
    """
    def decorator(func: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)

        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                log_exception(
                    logger,
                    e,
                    context=f"Error in async {func.__module__}.{func.__name__}"
                )
                raise

        return wrapper

    return decorator


class PerformanceLogger:
    """
    Context manager for logging function performance.

    Usage:
        with PerformanceLogger("my_operation", logger):
            # Your code here
    """

    def __init__(self, operation_name: str, logger: logging.Logger = None):
        self.operation_name = operation_name
        self.logger = logger or get_logger("performance")
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"Starting: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()

        if exc_type is not None:
            self.logger.error(
                f"Failed: {self.operation_name} (duration: {duration:.3f}s) - "
                f"Exception: {exc_type.__name__}: {exc_val}"
            )
        else:
            self.logger.info(f"Completed: {self.operation_name} (duration: {duration:.3f}s)")

        # Don't suppress exceptions
        return False


def performance_tracker(logger: logging.Logger = None):
    """
    Decorator to track function performance.

    Usage:
        @performance_tracker(logger)
        def my_function():
            # Your code here

    Args:
        logger: Logger instance (if None, uses performance logger)
    """
    def decorator(func: Callable) -> Callable:
        perf_logger = logger or get_logger("performance")

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = datetime.now()
            func_name = f"{func.__module__}.{func.__name__}"

            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                perf_logger.info(f"{func_name} completed in {duration:.3f}s")
                return result
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                perf_logger.error(f"{func_name} failed after {duration:.3f}s: {str(e)}")
                raise

        return wrapper

    return decorator


# Create default loggers
app_logger = get_logger("app")
db_logger = get_logger("database")
api_logger = get_logger("api")
service_logger = get_logger("service")
