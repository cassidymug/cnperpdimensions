import os
import re
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / 'app' / 'static'
NAVBAR_JS = STATIC_DIR / 'js' / 'navbar.js'
REPORTS_DIR = ROOT / 'reports'
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = REPORTS_DIR / 'navbar_consistency_report.md'

RE_NAVBAR_JS = re.compile(r"<script[^>]+src=[\'\"]([^\'\"]*navbar\.js[^\'\"]*)[\'\"][^>]*>", re.IGNORECASE)
RE_NAVBAR_CONTAINER = re.compile(r"id=[\'\"]navbar-container[\'\"]", re.IGNORECASE)
RE_BOOTSTRAP_BUNDLE = re.compile(r"<script[^>]+bootstrap\.bundle\.min\.js", re.IGNORECASE)

# Extract expected links from navbar.js (hrefs inside createNavbar template)
RE_HREF = re.compile(r"href=\"(/static/[^\"]+\.html)\"", re.IGNORECASE)

REQUIRED_LINKS = {
    '/static/vat-reports.html',
    '/static/budgeting.html',
    '/static/job-cards.html',
    '/static/procurement.html',
}


def extract_navbar_links(navbar_js_path: Path):
    try:
        text = navbar_js_path.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        return set(), f"Failed to read navbar.js: {e}"
    links = set(RE_HREF.findall(text))
    return links, None


def analyze_page(html_path: Path):
    text = html_path.read_text(encoding='utf-8', errors='ignore')
    js_includes = RE_NAVBAR_JS.findall(text)
    container_count = len(RE_NAVBAR_CONTAINER.findall(text))
    has_bootstrap = bool(RE_BOOTSTRAP_BUNDLE.search(text))

    issues = []
    status = 'OK'

    if not js_includes:
        issues.append('Missing navbar.js include')
    elif len(js_includes) > 1:
        status = 'WARN'
        issues.append(f'Duplicate navbar.js includes ({len(js_includes)})')
    else:
        # Path variety note
        src = js_includes[0]
        if src.startswith('/static/') and 'js/navbar.js' in src:
            pass  # acceptable
        elif src.startswith('js/navbar.js') or 'js/navbar.js' in src:
            pass  # acceptable
        else:
            status = 'WARN'
            issues.append(f'Non-standard navbar.js path: {src}')

    if container_count == 0:
        # Not an error because navbar.js injects container if missing; just note
        issues.append('No #navbar-container (navbar.js will inject)')
    elif container_count > 1:
        status = 'WARN'
        issues.append(f'Duplicate #navbar-container elements ({container_count})')

    # Optional note: bootstrap presence
    if not has_bootstrap:
        issues.append('No Bootstrap bundle found (fallback in navbar.js will be used)')

    return {
        'file': str(html_path.relative_to(ROOT)),
        'navbar_js_count': len(js_includes),
        'navbar_js_srcs': js_includes,
        'navbar_container_count': container_count,
        'has_bootstrap_bundle': has_bootstrap,
        'status': status,
        'issues': issues,
    }


def main():
    links, err = extract_navbar_links(NAVBAR_JS)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    rows = []
    pages = sorted(p for p in STATIC_DIR.glob('*.html'))

    for page in pages:
        result = analyze_page(page)
        rows.append(result)

    # Check required links are present in navbar.js
    missing_required = sorted([l for l in REQUIRED_LINKS if l not in links])

    # Aggregate stats
    total = len(rows)
    ok = sum(1 for r in rows if r['status'] == 'OK')
    warn = sum(1 for r in rows if r['status'] == 'WARN')
    missing_nav = sum(1 for r in rows if r['navbar_js_count'] == 0)
    dup_js = sum(1 for r in rows if r['navbar_js_count'] > 1)
    dup_container = sum(1 for r in rows if r['navbar_container_count'] > 1)

    md = []
    md.append(f"# Navbar Consistency Report\n")
    md.append(f"Generated: {now}\n")
    md.append("")
    md.append("## Summary")
    md.append(f"- Pages scanned: {total}")
    md.append(f"- OK: {ok}")
    md.append(f"- WARN: {warn}")
    md.append(f"- Missing navbar.js include: {missing_nav}")
    md.append(f"- Duplicate navbar.js includes: {dup_js}")
    md.append(f"- Duplicate #navbar-container: {dup_container}")
    md.append("")

    md.append("## Navbar.js Links Detected")
    if err:
        md.append(f"- ERROR reading navbar.js: {err}")
    else:
        for l in sorted(links):
            md.append(f"- {l}")
    md.append("")

    md.append("## Required Links Presence in Navbar")
    if missing_required:
        md.append("- Missing in navbar.js:")
        for l in missing_required:
            md.append(f"  - {l}")
    else:
        md.append("- All required links present: " + ", ".join(sorted(REQUIRED_LINKS)))
    md.append("")

    md.append("## Per-Page Checks")
    for r in rows:
        md.append(f"### {r['file']}")
        md.append(f"- Status: {r['status']}")
        md.append(f"- navbar.js includes: {r['navbar_js_count']}" + (f" (srcs: {', '.join(r['navbar_js_srcs'])})" if r['navbar_js_srcs'] else ""))
        md.append(f"- #navbar-container elements: {r['navbar_container_count']}")
        md.append(f"- Bootstrap bundle: {'Yes' if r['has_bootstrap_bundle'] else 'No'}")
        if r['issues']:
            md.append(f"- Issues:")
            for issue in r['issues']:
                md.append(f"  - {issue}")
        md.append("")

    REPORT_PATH.write_text("\n".join(md), encoding='utf-8')
    print(f"Report written to {REPORT_PATH}")


if __name__ == '__main__':
    main()
