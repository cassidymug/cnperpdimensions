"""
Logging Viewer API Endpoints

Provides REST API for viewing and managing application logs.
Allows monitoring of errors, performance metrics, and general logs.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
import re
from collections import defaultdict

from app.core.database import get_db
from app.utils.logger import get_logger
from pydantic import BaseModel

logger = get_logger(__name__)
router = APIRouter()

# Pydantic schemas
class LogEntry(BaseModel):
    timestamp: str
    level: str
    module: str
    message: str
    line_number: int

class LogStats(BaseModel):
    total_logs: int
    error_count: int
    warning_count: int
    info_count: int
    debug_count: int
    log_file_size: int
    error_file_size: int
    last_error: Optional[str] = None
    last_error_time: Optional[str] = None

class ErrorSummary(BaseModel):
    error_type: str
    count: int
    last_occurred: str
    sample_message: str

class PerformanceMetric(BaseModel):
    function_name: str
    module: str
    execution_time: float
    timestamp: str

class LogFileInfo(BaseModel):
    name: str
    size: int
    size_mb: float
    last_modified: str
    line_count: int

# Helper functions
def get_log_path(log_type: str = "app") -> Path:
    """Get path to log file"""
    base_path = Path(__file__).parent.parent.parent.parent / "logs"

    if log_type == "app":
        return base_path / "app.log"
    elif log_type == "error":
        return base_path / "errors.log"
    elif log_type == "performance":
        return base_path / "performance.log"
    else:
        raise ValueError(f"Unknown log type: {log_type}")

def parse_log_line(line: str) -> Optional[Dict[str, Any]]:
    """Parse a log line into components"""
    # Format: 2025-01-27 12:34:56,789 INFO module_name - message
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) (\w+) ([\w\.]+) - (.+)'
    match = re.match(pattern, line)

    if match:
        return {
            "timestamp": match.group(1),
            "level": match.group(2),
            "module": match.group(3),
            "message": match.group(4)
        }
    return None

def read_log_file(log_path: Path, limit: int = 100, level_filter: Optional[str] = None) -> List[Dict]:
    """Read and parse log file"""
    if not log_path.exists():
        return []

    entries = []
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Read from end of file (most recent first)
        for i, line in enumerate(reversed(lines[-1000:])):  # Last 1000 lines
            if len(entries) >= limit:
                break

            parsed = parse_log_line(line.strip())
            if parsed:
                if level_filter and parsed['level'] != level_filter:
                    continue

                parsed['line_number'] = len(lines) - i
                entries.append(parsed)

    except Exception as e:
        logger.error(f"Error reading log file: {e}")

    return entries

# API Endpoints

@router.get("/logs", response_model=List[LogEntry])
async def get_logs(
    log_type: str = Query("app", description="Type of log: app, error, or performance"),
    limit: int = Query(100, ge=1, le=1000),
    level: Optional[str] = Query(None, description="Filter by level: DEBUG, INFO, WARNING, ERROR, CRITICAL")
):
    """
    Get recent log entries

    - **log_type**: Type of log file to read (app, error, performance)
    - **limit**: Maximum number of entries to return
    - **level**: Filter by log level
    """
    try:
        log_path = get_log_path(log_type)
        entries = read_log_file(log_path, limit, level)

        logger.info(f"Retrieved {len(entries)} log entries from {log_type} log")
        return entries

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")

@router.get("/logs/stats", response_model=LogStats)
async def get_log_stats():
    """
    Get statistics about logs

    Returns counts of log entries by level, file sizes, and recent errors.
    """
    try:
        app_log_path = get_log_path("app")
        error_log_path = get_log_path("error")

        stats = {
            "total_logs": 0,
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "debug_count": 0,
            "log_file_size": 0,
            "error_file_size": 0,
            "last_error": None,
            "last_error_time": None
        }

        # Count log levels
        if app_log_path.exists():
            stats["log_file_size"] = app_log_path.stat().st_size

            with open(app_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    stats["total_logs"] += 1
                    if "ERROR" in line:
                        stats["error_count"] += 1
                    elif "WARNING" in line:
                        stats["warning_count"] += 1
                    elif "INFO" in line:
                        stats["info_count"] += 1
                    elif "DEBUG" in line:
                        stats["debug_count"] += 1

        # Get last error
        if error_log_path.exists():
            stats["error_file_size"] = error_log_path.stat().st_size

            with open(error_log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    last_error_line = lines[-1].strip()
                    parsed = parse_log_line(last_error_line)
                    if parsed:
                        stats["last_error"] = parsed["message"]
                        stats["last_error_time"] = parsed["timestamp"]

        logger.info("Retrieved log statistics")
        return stats

    except Exception as e:
        logger.error(f"Error getting log stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get log statistics")

@router.get("/logs/errors/summary", response_model=List[ErrorSummary])
async def get_error_summary(
    limit: int = Query(10, ge=1, le=100),
    hours: int = Query(24, ge=1, le=168, description="Time window in hours")
):
    """
    Get summary of errors grouped by type

    - **limit**: Maximum number of error types to return
    - **hours**: Time window to analyze (default 24 hours)
    """
    try:
        error_log_path = get_log_path("error")

        if not error_log_path.exists():
            return []

        # Group errors by type
        error_groups = defaultdict(lambda: {
            "count": 0,
            "last_occurred": None,
            "sample_message": None
        })

        cutoff_time = datetime.now() - timedelta(hours=hours)

        with open(error_log_path, 'r', encoding='utf-8') as f:
            for line in f:
                parsed = parse_log_line(line.strip())
                if not parsed:
                    continue

                # Parse timestamp
                try:
                    log_time = datetime.strptime(parsed["timestamp"], "%Y-%m-%d %H:%M:%S,%f")
                    if log_time < cutoff_time:
                        continue
                except:
                    continue

                # Extract error type from message
                message = parsed["message"]
                error_type = "General Error"

                # Try to extract exception type
                if ":" in message:
                    potential_type = message.split(":")[0].strip()
                    if potential_type.endswith("Error") or potential_type.endswith("Exception"):
                        error_type = potential_type

                # Update group
                group = error_groups[error_type]
                group["count"] += 1
                group["last_occurred"] = parsed["timestamp"]
                if group["sample_message"] is None:
                    group["sample_message"] = message[:200]  # First 200 chars

        # Convert to list and sort by count
        summaries = [
            ErrorSummary(
                error_type=error_type,
                count=data["count"],
                last_occurred=data["last_occurred"],
                sample_message=data["sample_message"]
            )
            for error_type, data in error_groups.items()
        ]

        summaries.sort(key=lambda x: x.count, reverse=True)

        logger.info(f"Retrieved {len(summaries)} error summaries")
        return summaries[:limit]

    except Exception as e:
        logger.error(f"Error getting error summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get error summary")

@router.get("/logs/performance", response_model=List[PerformanceMetric])
async def get_performance_metrics(
    limit: int = Query(50, ge=1, le=500),
    min_duration: float = Query(0.0, ge=0.0, description="Minimum execution time in seconds")
):
    """
    Get performance metrics from logs

    - **limit**: Maximum number of metrics to return
    - **min_duration**: Only show operations taking longer than this (seconds)
    """
    try:
        perf_log_path = get_log_path("performance")

        if not perf_log_path.exists():
            return []

        metrics = []

        # Pattern: module.function took X.XXX seconds
        pattern = r'([\w\.]+)\.([\w]+) took ([\d\.]+) seconds'

        with open(perf_log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Read from end (most recent first)
        for line in reversed(lines[-1000:]):
            if len(metrics) >= limit:
                break

            parsed = parse_log_line(line.strip())
            if not parsed:
                continue

            match = re.search(pattern, parsed["message"])
            if match:
                execution_time = float(match.group(3))

                if execution_time >= min_duration:
                    metrics.append(PerformanceMetric(
                        module=match.group(1),
                        function_name=match.group(2),
                        execution_time=execution_time,
                        timestamp=parsed["timestamp"]
                    ))

        logger.info(f"Retrieved {len(metrics)} performance metrics")
        return metrics

    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")

@router.get("/logs/files", response_model=List[LogFileInfo])
async def get_log_files():
    """
    Get information about all log files

    Returns file sizes, line counts, and last modified times.
    """
    try:
        logs_dir = Path(__file__).parent.parent.parent.parent / "logs"

        if not logs_dir.exists():
            return []

        files_info = []

        for log_file in logs_dir.glob("*.log*"):
            if log_file.is_file():
                stat = log_file.stat()

                # Count lines
                line_count = 0
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        line_count = sum(1 for _ in f)
                except:
                    line_count = 0

                files_info.append(LogFileInfo(
                    name=log_file.name,
                    size=stat.st_size,
                    size_mb=round(stat.st_size / (1024 * 1024), 2),
                    last_modified=datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    line_count=line_count
                ))

        files_info.sort(key=lambda x: x.name)

        logger.info(f"Retrieved info for {len(files_info)} log files")
        return files_info

    except Exception as e:
        logger.error(f"Error getting log files: {e}")
        raise HTTPException(status_code=500, detail="Failed to get log files info")

@router.get("/logs/search")
async def search_logs(
    query: str = Query(..., min_length=1),
    log_type: str = Query("app", description="Type of log: app, error, or performance"),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    Search through logs

    - **query**: Search term (case-insensitive)
    - **log_type**: Type of log file to search
    - **limit**: Maximum number of results
    """
    try:
        log_path = get_log_path(log_type)

        if not log_path.exists():
            return {"results": [], "count": 0}

        results = []
        query_lower = query.lower()

        with open(log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Search through lines
        for i, line in enumerate(reversed(lines[-10000:])):  # Search last 10k lines
            if len(results) >= limit:
                break

            if query_lower in line.lower():
                parsed = parse_log_line(line.strip())
                if parsed:
                    parsed['line_number'] = len(lines) - i
                    results.append(parsed)

        logger.info(f"Search for '{query}' found {len(results)} results")
        return {
            "results": results,
            "count": len(results),
            "query": query,
            "log_type": log_type
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error searching logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to search logs")

@router.delete("/logs/clear/{log_type}")
async def clear_log_file(log_type: str):
    """
    Clear a log file (admin only)

    **WARNING**: This will delete all log entries!

    - **log_type**: Type of log to clear (app, error, or performance)
    """
    try:
        log_path = get_log_path(log_type)

        if log_path.exists():
            # Create backup first
            backup_path = log_path.with_suffix(f'.log.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            log_path.rename(backup_path)

            # Create new empty file
            log_path.touch()

            logger.warning(f"Cleared {log_type} log file (backup created: {backup_path.name})")
            return {
                "success": True,
                "message": f"Log file cleared",
                "backup": backup_path.name
            }
        else:
            raise HTTPException(status_code=404, detail=f"Log file not found: {log_type}")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error clearing log file: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear log file")

@router.get("/logs/tail/{log_type}")
async def tail_log(
    log_type: str,
    lines: int = Query(50, ge=1, le=500)
):
    """
    Get the last N lines from a log file (like Unix 'tail' command)

    - **log_type**: Type of log file
    - **lines**: Number of lines to return
    """
    try:
        log_path = get_log_path(log_type)

        if not log_path.exists():
            return {"lines": [], "count": 0}

        with open(log_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()

        tail_lines = all_lines[-lines:]

        return {
            "lines": [line.rstrip() for line in tail_lines],
            "count": len(tail_lines),
            "total_lines": len(all_lines),
            "log_type": log_type
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error tailing log: {e}")
        raise HTTPException(status_code=500, detail="Failed to tail log file")
