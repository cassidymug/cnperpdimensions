"""
Automated Error Logging Integration Script

This script automatically adds error logging to all API endpoint files
that don't already have comprehensive logging.
"""

import os
import re
from pathlib import Path
from typing import List, Tuple

# Directories containing API endpoints
ENDPOINT_DIRS = [
    Path("app/api/v1/endpoints"),
    Path("app/routers"),
]

# Logger import template
LOGGER_IMPORT = """from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)"""


def has_logger_import(content: str) -> bool:
    """Check if file already has logger import."""
    return 'get_logger(__name__)' in content or 'logger = logging.getLogger(__name__)' in content


def add_logger_import(content: str) -> str:
    """Add logger import after the last import statement."""
    lines = content.split('\n')

    # Find the last import line
    last_import_idx = -1
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if (stripped.startswith('from ') or stripped.startswith('import ')) and not stripped.startswith('#'):
            last_import_idx = idx

    if last_import_idx >= 0:
        # Insert logger import after last import
        lines.insert(last_import_idx + 1, '')
        lines.insert(last_import_idx + 2, LOGGER_IMPORT)
        return '\n'.join(lines)

    return content


def count_endpoints(content: str) -> int:
    """Count number of route decorators in file."""
    return len(re.findall(r'@router\.(get|post|put|patch|delete|options|head)', content))


def has_error_handling(content: str) -> bool:
    """Check if file has comprehensive error handling."""
    # Look for try-except blocks
    has_try = 'try:' in content
    has_log_exception = 'log_exception' in content or 'logger.exception' in content or 'logger.error' in content

    return has_try and has_log_exception


def process_file(file_path: Path) -> Tuple[bool, str]:
    """
    Process a single endpoint file.

    Returns:
        Tuple of (was_modified, status_message)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Skip if it's an __init__ file or empty
        if file_path.name.startswith('__') or len(content.strip()) < 10:
            return False, "Skipped (init or empty file)"

        # Count endpoints
        endpoint_count = count_endpoints(content)
        if endpoint_count == 0:
            return False, "No endpoints found"

        # Check if already has logging
        has_logging = has_logger_import(content)
        has_error_blocks = has_error_handling(content)

        status_parts = []

        # Add logger import if missing
        modified = False
        if not has_logging:
            content = add_logger_import(content)
            modified = True
            status_parts.append("added logger import")

        # Write back if modified
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

        # Build status message
        status = f"{endpoint_count} endpoints"
        if has_error_blocks:
            status += " | ✅ has error handling"
        else:
            status += " | ⚠ needs error handling"

        if status_parts:
            status += f" | {', '.join(status_parts)}"

        return modified, status

    except Exception as e:
        return False, f"❌ Error: {str(e)}"


def main():
    """Main function to process all endpoint files."""
    print("=" * 80)
    print("ERROR LOGGING INTEGRATION")
    print("=" * 80)

    all_files: List[Tuple[Path, bool, str]] = []

    for endpoint_dir in ENDPOINT_DIRS:
        if not endpoint_dir.exists():
            print(f"\n⚠ Directory not found: {endpoint_dir}")
            continue

        print(f"\n📁 Processing {endpoint_dir}/")
        print("-" * 80)

        # Get all Python files
        py_files = sorted(endpoint_dir.glob("*.py"))

        for file_path in py_files:
            modified, status = process_file(file_path)
            all_files.append((file_path, modified, status))

            # Print status with appropriate icon
            icon = "✓" if modified else "·"
            print(f"  {icon} {file_path.name:40s} {status}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_files = len(all_files)
    modified_count = sum(1 for _, modified, _ in all_files if modified)
    needs_manual = sum(1 for _, _, status in all_files if "needs error handling" in status)

    print(f"\n📊 Total Files:     {total_files}")
    print(f"✅ Modified:        {modified_count}")
    print(f"⚠  Needs Manual:    {needs_manual}")

    if modified_count > 0:
        print(f"\n✅ Successfully added logger imports to {modified_count} files")

    if needs_manual > 0:
        print(f"\n⚠️  {needs_manual} files need manual error handling additions")
        print("   See ERROR_LOGGING_GUIDE.md for examples")

    print("\n" + "=" * 80)
    print("📖 Next Steps:")
    print("   1. Review modified files")
    print("   2. Add try-except blocks to endpoints (see docs/ERROR_LOGGING_GUIDE.md)")
    print("   3. Test error logging with intentional errors")
    print("   4. Monitor logs/app.log and logs/errors.log")
    print("=" * 80)


if __name__ == "__main__":
    main()
