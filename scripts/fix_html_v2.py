"""
Fix existing HTML files v2:
1. Fix corrupted href attributes (remove <i> tags from href)
2. Add <h1> title at top of content
3. Wrap foreign terms with <i> tags (italic) - ONLY in text content
"""

import re
from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent / "docs"

# Foreign terms to wrap with <i> tags
FOREIGN_TERMS = [
    "agency costs", "principal", "agent", "perquisites", "residual loss",
    "monitoring costs", "bonding costs", "property rights", "free cash flow",
    "adverse selection", "moral hazard", "transaction costs", "asset substitution",
    "underinvestment", "debt overhang", "bankruptcy costs",
    "human capital", "motivation", "skill-enhancing", "opportunity-enhancing",
    "AMO model", "CAPM", "APT", "Black-Scholes", "Markowitz", "Sharpe ratio",
    "Modigliani-Miller", "regression", "correlation", "variance",
    "standard deviation", "R-squared", "meta-analysis", "SEM",
    "Basel I", "Basel II", "Basel III", "Cooke ratio", "VaR",
    "risk-weighted assets", "internal ratings", "netting",
]


def fix_html_file(filepath):
    """Fix a single HTML file."""
    content = filepath.read_text(encoding="utf-8")
    original = content

    # Step 1: Fix corrupted attributes (remove <i> and </i> from href/id values)
    content = re.sub(r'href="#<i>([^<]+)</i>"', r'href="#\1"', content)
    content = re.sub(r"href='#<i>([^<]+)</i>'", r"href='#\1'", content)
    content = re.sub(r'id="<i>([^<]+)</i>"', r'id="\1"', content)
    content = re.sub(r"id='<i>([^<]+)</i>'", r"id='\1'", content)

    # Step 2: Extract title from <title> tag
    title_match = re.search(r'<title>(.*?)</title>', content)
    if not title_match:
        print("  WARN: No <title> found: " + filepath.name)
        return False

    title = title_match.group(1)

    # Step 3: Check if <h1> already exists in container
    if '<div class="container">' in content:
        container_part = content.split('<div class="container">')[-1]
        has_h1 = '<h1>' in container_part.split('</div>')[0]
    else:
        has_h1 = False

    if not has_h1:
        marker = '<div class="container">\n'
        if marker in content:
            replacement = '<div class="container">\n' \
                '        <a href="index.html" style="display:inline-block;margin-bottom:20px;color:#1a73e8;text-decoration:none;font-size:15px;">\u2190 Back to Index</a>\n' \
                '        <h1>' + title + '</h1>\n'
            content = content.replace(marker, replacement, 1)
        else:
            # Try with \r\n
            marker2 = '<div class="container">\r\n'
            if marker2 in content:
                replacement2 = '<div class="container">\r\n' \
                    '        <a href="index.html" style="display:inline-block;margin-bottom:20px;color:#1a73e8;text-decoration:none;font-size:15px;">\u2190 Back to Index</a>\r\n' \
                    '        <h1>' + title + '</h1>\r\n'
                content = content.replace(marker2, replacement2, 1)

    # Step 4: Wrap foreign terms with <i> tags in text content only
    # Protect ALL HTML tags (including their attributes)
    html_parts = []

    def protect_html(match):
        html_parts.append(match.group(0))
        return '__PH_' + str(len(html_parts) - 1) + '__'

    protected = re.sub(r'<[^>]+>', protect_html, content)

    # Now wrap foreign terms in text content only
    for term in FOREIGN_TERMS:
        escaped = re.escape(term)
        pattern = re.compile(r'(?<!<i>)\b(' + escaped + r')\b(?![^<]*</i>)', re.IGNORECASE)

        def make_replacer(t):
            def replacer(match):
                return '<i>' + match.group(1) + '</i>'
            return replacer

        protected = pattern.sub(make_replacer(term), protected)

    # Restore HTML tags
    def restore_html(match):
        idx = int(match.group(1))
        return html_parts[idx]

    content = re.sub(r'__PH_(\d+)__', restore_html, protected)

    if content != original:
        filepath.write_text(content, encoding="utf-8")
        print("  FIXED: " + filepath.name)
        return True
    else:
        print("  SKIP: " + filepath.name)
        return False


def main():
    """Fix all HTML files."""
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("Fixing HTML files v2...\n")

    fixed = 0
    total = 0

    for section in ["books", "articles"]:
        section_dir = DOCS_DIR / section
        if not section_dir.exists():
            continue

        for folder in sorted(section_dir.iterdir()):
            if not folder.is_dir():
                continue

            for html_file in sorted(folder.glob("Ringkasan_*.html")):
                total += 1
                if fix_html_file(html_file):
                    fixed += 1

    print("\nFixed " + str(fixed) + "/" + str(total) + " files")


if __name__ == "__main__":
    main()
