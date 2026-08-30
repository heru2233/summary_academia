"""
Fix existing HTML files:
1. Add <h1> title at top of content
2. Wrap foreign terms with <i> tags (italic)
"""

import re
from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent / "docs"

# Foreign terms to wrap with <i> tags
FOREIGN_TERMS = [
    # Agency Theory
    "agency costs", "principal", "agent", "perquisites", "residual loss",
    "monitoring costs", "bonding costs", "property rights", "free cash flow",
    "adverse selection", "moral hazard", "transaction costs", "asset substitution",
    "underinvestment", "debt overhang", "bankruptcy costs",
    # HR/Management
    "human capital", "motivation", "skill-enhancing", "opportunity-enhancing",
    "AMO model",
    # Finance models
    "CAPM", "APT", "Black-Scholes", "Markowitz", "Sharpe ratio",
    "Modigliani-Miller",
    # Statistics
    "regression", "correlation", "variance", "standard deviation",
    "R-squared", "meta-analysis", "SEM",
    # Banking
    "Basel I", "Basel II", "Basel III", "Cooke ratio", "VaR",
    "risk-weighted assets", "internal ratings", "netting",
]

def fix_html_file(filepath: Path):
    """Fix a single HTML file."""
    content = filepath.read_text(encoding="utf-8")
    original = content
    
    # Extract title from <title> tag
    title_match = re.search(r'<title>(.*?)</title>', content)
    if not title_match:
        print(f"  WARN: No <title> found: {filepath.name}")
        return False
    
    title = title_match.group(1)
    
    # Check if <h1> already exists in container
    has_h1 = '<h1>' in content.split('<div class="container">')[-1].split('</div>')[0]
    
    new_content = content
    
    if not has_h1:
        # Add <h1> after <div class="container">
        container_pattern = r'(<div class="container">\s*)'
        h1_html = f'\\1        <a href="index.html" style="display:inline-block;margin-bottom:20px;color:#1a73e8;text-decoration:none;font-size:15px;">\u2190 Back to Index</a>\n        <h1>{title}</h1>\n'
        new_content = re.sub(container_pattern, h1_html, new_content, count=1)
    
    # Wrap foreign terms with <i> tags (only in text content, not in HTML tags)
    # First, extract and protect HTML tags AND their attributes
    html_parts = []
    def protect_html(match):
        html_parts.append(match.group(0))
        return f'__HTML_PLACEHOLDER_{len(html_parts)-1}__'
    
    # Protect all HTML tags (including attributes)
    protected = re.sub(r'<[^>]+>', protect_html, new_content)
    
    # Now wrap foreign terms in text content only
    for term in FOREIGN_TERMS:
        pattern = re.compile(r'(?<!<i>)\b(' + re.escape(term) + r')\b(?![^<]*</i>)', re.IGNORECASE)
        
        def replace_with_italic(match):
            return f'<i>{match.group(1)}</i>'
        
        protected = pattern.sub(replace_with_italic, protected)
    
    # Restore HTML tags
    def restore_html(match):
        idx = int(match.group(1))
        return html_parts[idx]
    
    new_content = re.sub(r'__HTML_PLACEHOLDER_(\d+)__', restore_html, protected)
    
    if new_content != original:
        filepath.write_text(new_content, encoding="utf-8")
        print(f"  FIXED: {filepath.name}")
        return True
    else:
        print(f"  SKIP: {filepath.name}")
        return False


def main():
    """Fix all HTML files."""
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    print("Fixing HTML files...\n")
    
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
    
    print(f"\nFixed {fixed}/{total} files")


if __name__ == "__main__":
    main()
