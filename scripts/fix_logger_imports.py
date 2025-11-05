"""
Fix Logger Import Indentation Issues

This script fixes logger imports that were incorrectly inserted in the middle of functions.
"""

import re
from pathlib import Path

def fix_file(file_path: Path) -> bool:
    """Fix logger import placement in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Pattern to find misplaced logger imports (indented logger import lines)
        # These are imports that appear after some code (have leading whitespace)
        pattern = r'\n[ \t]+from app\.utils\.logger import[^\n]+\n[ \t]+logger = get_logger\(__name__\)\n'

        # Find all matches
        matches = list(re.finditer(pattern, content))

        if not matches:
            return False

        # Remove all misplaced logger imports
        new_content = re.sub(pattern, '\n', content)

        # Check if logger import already exists at the top
        if 'from app.utils.logger import' not in new_content[:2000]:
            # Find the last import statement near the top
            lines = new_content.split('\n')
            last_import_idx = -1

            for idx, line in enumerate(lines[:100]):  # Check first 100 lines
                stripped = line.strip()
                if (stripped.startswith('from ') or stripped.startswith('import ')) and not stripped.startswith('#'):
                    last_import_idx = idx

            if last_import_idx >= 0:
                # Insert logger import after last import
                logger_import = '\nfrom app.utils.logger import get_logger, log_exception, log_error_with_context\n\nlogger = get_logger(__name__)'
                lines.insert(last_import_idx + 1, logger_import)
                new_content = '\n'.join(lines)

        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"✅ Fixed: {file_path.name}")
        return True

    except Exception as e:
        print(f"❌ Error fixing {file_path.name}: {e}")
        return False


def main():
    """Fix all files with logger import issues."""
    print("="*60)
    print("FIXING LOGGER IMPORT INDENTATION ISSUES")
    print("="*60)

    # Files that were manually edited
    files_to_check = [
        Path("app/routers/banking_dimensions.py"),
        Path("app/routers/dimensional_reports.py"),
        Path("app/routers/accounting_dimensions.py"),
        Path("app/api/v1/endpoints/accounting.py"),
        Path("app/api/v1/endpoints/activity.py"),
        Path("app/api/v1/endpoints/credit_notes.py"),
        Path("app/api/v1/endpoints/banking.py"),
        Path("app/api/v1/endpoints/branch_sales_realtime.py"),
        Path("app/api/v1/endpoints/branches.py"),
        Path("app/api/v1/endpoints/asset_management.py"),
        Path("app/api/v1/endpoints/inventory.py"),
        Path("app/api/v1/endpoints/manufacturing.py"),
        Path("app/api/v1/endpoints/purchases.py"),
        Path("app/api/v1/endpoints/sales.py"),
        Path("app/api/v1/endpoints/vat.py"),
        Path("app/api/v1/endpoints/workflows.py"),
        Path("app/api/v1/endpoints/users.py"),
    ]

    fixed_count = 0
    for file_path in files_to_check:
        if not file_path.exists():
            print(f"⚠️  Not found: {file_path}")
            continue

        if fix_file(file_path):
            fixed_count += 1

    print("\n" + "="*60)
    print(f"✅ Fixed {fixed_count} files")
    print("="*60)


if __name__ == "__main__":
    main()
