"""
Find and fix ALL logger imports that break multi-line import statements.
"""

import re
from pathlib import Path

def fix_file(filepath):
    """Fix one file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Find pattern: from X import (\n<LOGGER_IMPORT>\n    items...
    # Replace with: from X import (\n    items...
    # And add logger import before the multi-line import

    # Step 1: Find all occurrences of logger import breaking multi-line imports
    # Pattern: from SOMETHING import (\nfrom app.utils.logger import...\nlogger = get_logger...\n    ITEM
    pattern = r'(from [^\n]+ import \()\s*\n\s*from app\.utils\.logger import[^\n]+\s*\n\s*logger = get_logger\(__name__\)\s*\n(\s+[A-Z][^\n]+)'

    match = re.search(pattern, content)
    if not match:
        return False, "No pattern found"

    print(f"Found broken multi-line import in {filepath.name}")

    # Remove the logger import from inside the multi-line import
    content = re.sub(
        r'\nfrom app\.utils\.logger import[^\n]+\s*\n\s*logger = get_logger\(__name__\)\s*\n',
        '\n',
        content
    )

    # Check if logger import already exists at top level
    if not re.search(r'^from app\.utils\.logger import', content, re.MULTILINE):
        # Find where to insert - after last regular import before first multi-line import
        # Find the position right before "from app.schemas" or similar multi-line imports
        multiline_start = re.search(r'from app\.(schemas|models)[^\n]+ import \(', content)
        if multiline_start:
            # Find all imports before this position
            imports_section = content[:multiline_start.start()]
            last_import = None
            for match in re.finditer(r'^(from [^\n]+|import [^\n]+)\n', imports_section, re.MULTILINE):
                last_import = match

            if last_import:
                insert_pos = last_import.end()
                logger_import = "from app.utils.logger import get_logger, log_exception, log_error_with_context\n"
                content = content[:insert_pos] + logger_import + content[insert_pos:]
                print(f"  Added logger import at line {content[:insert_pos].count(chr(10)) + 1}")

    # Add logger = get_logger(__name__) after imports section
    if 'logger = get_logger(__name__)' not in content[:1000]:
        # Find router = APIRouter() and insert before it
        router_match = re.search(r'\n(router = APIRouter\(\))', content)
        if router_match:
            logger_var = "\nlogger = get_logger(__name__)\n"
            content = content[:router_match.start()] + logger_var + content[router_match.start():]
            print(f"  Added logger variable")

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ Fixed {filepath.name}")
        return True, "Fixed"

    return False, "No changes needed"

def main():
    """Process all files"""
    endpoints_dir = Path(__file__).parent.parent / "app" / "api" / "v1" / "endpoints"

    fixed_count = 0
    for filepath in sorted(endpoints_dir.glob("*.py")):
        if filepath.name == "__init__.py":
            continue

        try:
            was_fixed, msg = fix_file(filepath)
            if was_fixed:
                fixed_count += 1
        except Exception as e:
            print(f"❌ Error processing {filepath.name}: {e}")

    print(f"\n✅ Fixed {fixed_count} files")

if __name__ == "__main__":
    main()
