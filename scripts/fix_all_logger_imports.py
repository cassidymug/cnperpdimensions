"""
Fix all misplaced logger imports in Python files.
This script finds logger imports that are placed in the middle of files
and moves them to the top where they belong.
"""

import re
import os
from pathlib import Path

# Files that need fixing based on the grep search results
FILES_TO_FIX = [
    ("app/api/v1/endpoints/activity.py", 203),
    ("app/api/v1/endpoints/asset_management.py", 579),
    ("app/api/v1/endpoints/banking.py", 874),
    ("app/api/v1/endpoints/backup.py", 1288),
    ("app/api/v1/endpoints/credit_notes.py", 499),
    ("app/api/v1/endpoints/general_ledger.py", 668),
    ("app/api/v1/endpoints/inventory.py", 733),
    ("app/api/v1/endpoints/inventory_allocation.py", 1166),
    ("app/api/v1/endpoints/invoices.py", 954),
    ("app/api/v1/endpoints/invoice_designer.py", 448),
    ("app/api/v1/endpoints/job_cards.py", 154),
    ("app/api/v1/endpoints/manufacturing.py", 905),
    ("app/api/v1/endpoints/printer_settings.py", 227),
    ("app/api/v1/endpoints/purchases.py", 1348),
    ("app/api/v1/endpoints/quotations.py", 458),
    ("app/api/v1/endpoints/reports.py", 2389),
    ("app/api/v1/endpoints/roles.py", 113),
    ("app/api/v1/endpoints/sales.py", 1702),
    ("app/api/v1/endpoints/system_health.py", 299),
    ("app/api/v1/endpoints/vat.py", 210),
]

def fix_file(filepath):
    """Fix logger imports in a single file"""
    print(f"\n{'='*60}")
    print(f"Processing: {filepath}")
    print('='*60)

    if not os.path.exists(filepath):
        print(f"  ❌ File not found: {filepath}")
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to find misplaced logger imports (with optional blank lines)
    # This matches logger imports that are NOT at the start of a line (i.e., they're indented)
    pattern = r'\n\s+from app\.utils\.logger import[^\n]+\n+\s*logger = get_logger\(__name__\)\s*\n'

    matches = list(re.finditer(pattern, content))

    if not matches:
        print(f"  ℹ️  No misplaced logger imports found")
        return False

    print(f"  Found {len(matches)} misplaced logger import(s)")

    # Remove all misplaced imports
    for match in reversed(matches):  # Reverse to maintain positions
        content = content[:match.start()] + '\n' + content[match.end():]

    # Check if logger import already exists at the top
    has_logger_at_top = re.search(r'^from app\.utils\.logger import', content, re.MULTILINE)

    if not has_logger_at_top:
        # Find the right place to insert (after other imports, before router definition)
        # Look for the last import statement
        import_pattern = r'^(from [^\n]+|import [^\n]+)\n'
        last_import = None
        for match in re.finditer(import_pattern, content, re.MULTILINE):
            last_import = match

        if last_import:
            # Insert after last import
            insert_pos = last_import.end()
            logger_import = "from app.utils.logger import get_logger, log_exception, log_error_with_context\n\nlogger = get_logger(__name__)\n"
            content = content[:insert_pos] + logger_import + content[insert_pos:]
            print(f"  ✅ Added logger import at top of file")
        else:
            print(f"  ⚠️  Could not find import section")
            return False
    else:
        print(f"  ℹ️  Logger import already exists at top")

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ✅ Fixed successfully")
    return True

def main():
    """Main function"""
    print("\n" + "="*60)
    print("FIXING ALL LOGGER IMPORT PLACEMENT ISSUES")
    print("="*60)

    workspace_root = Path(__file__).parent.parent
    fixed_count = 0

    for filepath, line_num in FILES_TO_FIX:
        full_path = workspace_root / filepath.replace('/', '\\')
        if fix_file(str(full_path)):
            fixed_count += 1

    print("\n" + "="*60)
    print(f"✅ Fixed {fixed_count}/{len(FILES_TO_FIX)} files")
    print("="*60)

if __name__ == "__main__":
    main()
