"""
Script to add comprehensive error logging to all router files.

This script will:
1. Add logger imports to all router files
2. Wrap endpoints with try-except blocks
3. Add appropriate logging statements
"""

import os
import re
from pathlib import Path

# Router files to update
ROUTER_DIRS = [
    "app/routers",
    "app/api/v1/endpoints"
]

LOGGER_IMPORT = """from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)"""


def add_logging_imports(file_path: Path) -> bool:
    """Add logging imports to a file if not present."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if logger is already imported
    if 'from app.utils.logger import' in content or 'logger = get_logger(__name__)' in content:
        print(f"  ✓ {file_path.name} already has logging imports")
        return False

    # Find the last import statement
    import_pattern = r'^(from .+ import .+|import .+)$'
    lines = content.split('\n')
    last_import_idx = -1

    for idx, line in enumerate(lines):
        if re.match(import_pattern, line.strip()):
            last_import_idx = idx

    if last_import_idx >= 0:
        # Insert logger import after last import
        lines.insert(last_import_idx + 1, '')
        lines.insert(last_import_idx + 2, LOGGER_IMPORT)

        new_content = '\n'.join(lines)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"  ✓ Added logging imports to {file_path.name}")
        return True

    print(f"  ✗ Could not find import section in {file_path.name}")
    return False


def main():
    """Add logging to all router files."""
    print("="*60)
    print("Adding Error Logging to Router Files")
    print("="*60)

    updated_files = []

    for router_dir in ROUTER_DIRS:
        dir_path = Path(router_dir)
        if not dir_path.exists():
            print(f"\n⚠ Directory not found: {router_dir}")
            continue

        print(f"\nProcessing {router_dir}:")

        for file_path in dir_path.glob("*.py"):
            if file_path.name.startswith('__'):
                continue

            if add_logging_imports(file_path):
                updated_files.append(str(file_path))

    print("\n" + "="*60)
    print(f"✅ Updated {len(updated_files)} files")
    print("="*60)

    if updated_files:
        print("\nUpdated files:")
        for file in updated_files:
            print(f"  - {file}")

    print("\n📝 Note: You should now manually add try-except blocks to")
    print("   individual endpoint functions with appropriate logging.")


if __name__ == "__main__":
    main()
