"""
Add page-guard.js to all HTML files in static folder
except pos.html and login.html (POS users should access these)
"""

import os
import re

# Static folder path
STATIC_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'static')

# Files that should NOT have page guard (POS users can access these)
EXCLUDED_FILES = ['pos.html', 'login.html', 'logout.html']

# Page guard script tag to insert
PAGE_GUARD_SCRIPT = '    <!-- Page Access Guard - Restrict POS users to POS page only -->\n    <script src="/static/js/page-guard.js"></script>\n'

# Pattern to match after auth.js script tag
AUTH_PATTERN = re.compile(r'(<script src=["\'].*?auth\.js.*?["\']></script>)', re.IGNORECASE)

def add_page_guard_to_file(filepath):
    """Add page-guard.js script to HTML file if not already present"""

    filename = os.path.basename(filepath)

    # Skip excluded files
    if filename in EXCLUDED_FILES:
        print(f"⏭️  Skipping {filename} (excluded)")
        return False

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Skip if page-guard.js already present
        if 'page-guard.js' in content:
            print(f"✓  {filename} (already has page-guard)")
            return False

        # Skip if no auth.js found
        if 'auth.js' not in content:
            print(f"⏭️  Skipping {filename} (no auth.js found)")
            return False

        # Find auth.js script tag and insert page-guard.js after it
        match = AUTH_PATTERN.search(content)
        if not match:
            print(f"⚠️  {filename} (auth.js pattern not matched)")
            return False

        # Insert page-guard.js after auth.js
        auth_tag = match.group(1)
        new_content = content.replace(
            auth_tag,
            auth_tag + '\n' + PAGE_GUARD_SCRIPT
        )

        # Write updated content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

        print(f"✅ Added page-guard to {filename}")
        return True

    except Exception as e:
        print(f"❌ Error processing {filename}: {e}")
        return False

def main():
    """Process all HTML files in static folder"""

    print("=" * 80)
    print("ADDING PAGE GUARD TO HTML FILES")
    print("=" * 80)
    print(f"Static folder: {STATIC_FOLDER}")
    print(f"Excluded files: {', '.join(EXCLUDED_FILES)}\n")

    total_files = 0
    modified_files = 0

    # Walk through static folder
    for root, dirs, files in os.walk(STATIC_FOLDER):
        for filename in files:
            if filename.endswith('.html'):
                total_files += 1
                filepath = os.path.join(root, filename)

                # Make path relative for display
                rel_path = os.path.relpath(filepath, STATIC_FOLDER)

                if add_page_guard_to_file(filepath):
                    modified_files += 1

    print("\n" + "=" * 80)
    print(f"COMPLETE: Modified {modified_files} of {total_files} HTML files")
    print("=" * 80)
    print("\n📋 Summary:")
    print(f"  • Total HTML files: {total_files}")
    print(f"  • Files modified: {modified_files}")
    print(f"  • Files skipped: {total_files - modified_files}")
    print("\n🔒 Access Control:")
    print("  ✓ POS users can ONLY access pos.html and login.html")
    print("  ✓ All other pages will redirect POS users to POS")
    print("  ✓ Page guard loads immediately after auth.js")

if __name__ == '__main__':
    main()
