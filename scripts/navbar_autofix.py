import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / 'app' / 'static'

RE_NAVBAR_JS_TAG = re.compile(r"<script[^>]+src=[\"\']([^\"\']*navbar\.js[^\"\']*)[\"\'][^>]*>\s*</script>", re.IGNORECASE)
RE_NAVBAR_CONTAINER = re.compile(r"<div[^>]*\bid=[\"\']navbar-container[\"\'][^>]*>\s*</div>", re.IGNORECASE)

VERSION = datetime.now().strftime('%Y%m%d%H%M%S')
PREFERRED_TAG = f'<script src="js/navbar.js?v={VERSION}"></script>'
PREFERRED_CONTAINER = '<div id="navbar-container"></div>'


def _ensure_single_navbar_container(content: str) -> str:
    """Ensure exactly one #navbar-container exists; return updated content."""
    containers = list(RE_NAVBAR_CONTAINER.finditer(content))
    if len(containers) == 0:
        # Insert at top of body in a normalized form
        content = content.replace('<body>', f'<body>\n    {PREFERRED_CONTAINER}', 1)
    elif len(containers) > 1:
        # Remove all containers then insert one at top of body
        content = RE_NAVBAR_CONTAINER.sub('', content)
        content = content.replace('<body>', f'<body>\n    {PREFERRED_CONTAINER}', 1)
    return content


def _remove_all_navbar_js(content: str) -> str:
    """Remove all occurrences of navbar.js <script> tags."""
    return RE_NAVBAR_JS_TAG.sub('', content)


def _insert_single_navbar_js_after_container(content: str) -> str:
    """Insert a single preferred navbar.js <script> tag immediately after the first #navbar-container."""
    m = RE_NAVBAR_CONTAINER.search(content)
    if m:
        insert_at = m.end()
        injection = f"\n    <!-- Navbar Scripts -->\n    {PREFERRED_TAG}"
        return content[:insert_at] + injection + content[insert_at:]
    # Fallback: before closing body or end of file
    if '</body>' in content:
        return content.replace('</body>', f'    <!-- Navbar Scripts -->\n    {PREFERRED_TAG}\n</body>', 1)
    return content + f"\n{PREFERRED_TAG}\n"


def normalize_html(content: str) -> str:
    original = content

    # 1) Normalize containers first
    content = _ensure_single_navbar_container(content)

    # 2) Remove all navbar.js occurrences completely
    content = _remove_all_navbar_js(content)

    # 3) Insert a single navbar.js immediately after the (now single) container
    content = _insert_single_navbar_js_after_container(content)

    # Final cleanup: remove duplicate blank lines introduced
    content = re.sub(r"\n{3,}", "\n\n", content)

    return content if content != original else None


def main():
    changed = 0
    files = sorted(STATIC_DIR.glob('*.html'))
    for fp in files:
        try:
            text = fp.read_text(encoding='utf-8', errors='ignore')
            updated = normalize_html(text)
            if updated is not None:
                fp.write_text(updated, encoding='utf-8')
                changed += 1
                print(f"Fixed: {fp.relative_to(ROOT)}")
        except Exception as e:
            print(f"Skip {fp}: {e}")
    print(f"Total files changed: {changed}")


if __name__ == '__main__':
    main()
