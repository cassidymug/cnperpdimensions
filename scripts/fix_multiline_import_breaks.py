"""
Fix logger imports that break multi-line import statements.
Pattern: `from module import (`
         `from app.utils.logger import...`  <- breaks the multi-line import!
"""

import re
import os
from pathlib import Path

def fix_file(filepath):
    """Fix logger imports that break multi-line imports"""
    print(f"\nProcessing: {filepath}")

    if not os.path.exists(filepath):
        print(f"  ❌ File not found")
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern: from X import (\n from app.utils.logger import...
    # This breaks the multi-line import statement
    pattern = r'(from [^\n]+ import \()\n(from app\.utils\.logger import[^\n]+\n+logger = get_logger\(__name__\)\n+)'

    matches = list(re.finditer(pattern, content))

    if not matches:
        return False

    print(f"  Found {len(matches)} broken multi-line import(s)")

    # Remove the logger import that's breaking the multi-line import
    for match in reversed(matches):
        # Keep only the "from X import (" part
        content = content[:match.start()] + match.group(1) + '\n' + content[match.end():]

    # Check if logger import exists at top
    has_logger_at_top = re.search(r'^from app\.utils\.logger import', content, re.MULTILINE)

    if not has_logger_at_top:
        # Find last import before the broken multi-line import
        # Find the line before the first "from X import (" statement
        multiline_import = re.search(r'^from [^\n]+ import \(', content, re.MULTILINE)
        if multiline_import:
            # Find last regular import before this
            imports_before = list(re.finditer(r'^(from [^\n]+|import [^\n]+)\n', content[:multiline_import.start()], re.MULTILINE))
            if imports_before:
                insert_pos = imports_before[-1].end()
                logger_import = "from app.utils.logger import get_logger, log_exception, log_error_with_context\n"
                content = content[:insert_pos] + logger_import + content[insert_pos:]
                print(f"  ✅ Added logger import before multi-line import")
            else:
                print(f"  ⚠️  Could not find place to insert")
                return False
        else:
            print(f"  ⚠️  No multi-line import found")
            return False
    else:
        print(f"  ℹ️  Logger import already exists at top")

    # Add logger = get_logger(__name__) after the closing ) of imports if needed
    if 'logger = get_logger(__name__)' not in content[:500]:  # Check in first 500 chars
        # Find the end of all imports (look for "router = APIRouter()" or first non-import line)
        router_match = re.search(r'\n(router = APIRouter\(\))', content)
        if router_match:
            logger_var = "\nlogger = get_logger(__name__)\n"
            content = content[:router_match.start()] + logger_var + content[router_match.start():]
            print(f"  ✅ Added logger variable initialization")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ✅ Fixed successfully")
    return True

def main():
    """Scan all Python files in app/api/v1/endpoints and fix them"""
    print("\n" + "="*60)
    print("FIXING LOGGER IMPORTS BREAKING MULTI-LINE IMPORTS")
    print("="*60)

    workspace_root = Path(__file__).parent.parent
    endpoints_dir = workspace_root / "app" / "api" / "v1" / "endpoints"

    if not endpoints_dir.exists():
        print(f"❌ Directory not found: {endpoints_dir}")
        return

    fixed_count = 0
    total_count = 0

    for filepath in endpoints_dir.glob("*.py"):
        if filepath.name == "__init__.py":
            continue
        total_count += 1
        if fix_file(str(filepath)):
            fixed_count += 1

    print("\n" + "="*60)
    print(f"✅ Fixed {fixed_count}/{total_count} files")
    print("="*60)

if __name__ == "__main__":
    main()
