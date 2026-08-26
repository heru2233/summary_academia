#!/usr/bin/env python3
"""
auto_summary.py - Automatic PDF Summarization using OpenRouter API

Usage:
    python auto_summary.py --pdf <path> --title "Title" --type book|article [--lang ind|eng|both]

Examples:
    python auto_summary.py --pdf "../sources/books/financial-institutions-management/ch1.pdf" --title "Why Are Financial Institutions Special?" --type book --lang both
    python auto_summary.py --pdf "../sources/articles/myers-1984/Myers_1984.pdf" --title "The Capital Structure Puzzle" --type article --lang both
"""

import os
import sys
import json
import argparse
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "stealth/ox-alpha:free")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
SOURCES_DIR = PROJECT_ROOT / "sources"


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using pdftotext."""
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", pdf_path, "-"],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode != 0:
            print(f"[ERROR] pdftotext failed: {result.stderr}")
            sys.exit(1)
        return result.stdout
    except FileNotFoundError:
        print("[ERROR] pdftotext not found. Install poppler: choco install poppler")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("[ERROR] pdftotext timeout - PDF might be too large")
        sys.exit(1)


def get_book_prompt(title: str, lang: str, lang_code: str) -> str:
    """Get prompt for book chapter summarization."""
    return f"""You are an academic summarizer. Create a comprehensive summary of this book chapter.

RULES:
1. Output ONLY valid HTML, no markdown or code blocks
2. Use Times New Roman 12pt styling
3. Include all key concepts, formulas, tables, and examples
4. Structure with h2 for sections, h3 for subsections
5. Length: 5000-8000 words
6. Include MathJax for formulas: \\[display\\] and \\(inline\\)
7. Add print button at top
8. Language: {lang}
9. Make it responsive for mobile devices

OUTPUT FORMAT - Return ONLY this HTML (fill in the content):

<!DOCTYPE html>
<html lang="{lang_code}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="../../css/responsive.css">
<title>Chapter Summary - {title} ({lang})</title>
<style>
  body {{ font-family: "Times New Roman", serif; font-size: 12pt; line-height: 1.5; text-align: justify; max-width: 210mm; margin: 0 auto; padding: 20px 3.18cm; }}
  h1 {{ font-size: 16pt; text-align: center; }}
  h2 {{ font-size: 14pt; border-bottom: 1px solid #000; padding-bottom: 3px; }}
  h3 {{ font-size: 12pt; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 11pt; }}
  th, td {{ border: 1px solid #000; padding: 5px 7px; }}
  th {{ background-color: #eee; }}
  .toolbar {{ text-align: center; margin-bottom: 14px; }}
  .toolbar button {{ font-size: 12pt; padding: 6px 16px; cursor: pointer; }}
  @media print {{ .toolbar {{ display: none; }} body {{ padding: 0; }} }}
  @media screen and (max-width: 768px) {{ body {{ padding: 16px; font-size: 14px; }} table {{ display: block; overflow-x: auto; }} }}
  @media screen and (max-width: 480px) {{ body {{ padding: 12px; font-size: 13px; }} }}
</style>
<script>window.MathJax = {{ tex: {{ inlineMath: [['\\\\(','\\\\)']], displayMath: [['\\\\[','\\\\]']] }} }};</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js" async></script>
</head>
<body>
<div class="toolbar"><button onclick="window.print()">Print / Save as PDF</button></div>
<h1>Ringkasan: {title}</h1>
<p style="text-align:center; font-style:italic;">{title}</p>
<p style="text-align:center; font-size:11pt;">Summarized from original source</p>

<!-- WRITE YOUR SUMMARY CONTENT HERE -->

<p style="font-size:10pt; font-style:italic; color:#333; margin-top:24px; border-top:1px solid #999; padding-top:8px;">
Note: This is a self-study summary generated for educational purposes. For academic use, please refer to the original source.
</p>
</body>
</html>"""


def get_article_prompt(title: str, lang: str, lang_code: str) -> str:
    """Get prompt for journal article summarization."""
    return f"""You are an academic summarizer. Create a summary of this journal article.

RULES:
1. Output ONLY valid HTML, no markdown or code blocks
2. Use Times New Roman 12pt styling
3. Focus on key arguments, methodology, findings, and contributions
4. Length: 2000-4000 words
5. Include essential formulas with MathJax
6. Add print button at top
7. Language: {lang}
8. Make it responsive for mobile devices

OUTPUT FORMAT - Return ONLY this HTML (fill in the content):

<!DOCTYPE html>
<html lang="{lang_code}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="../../css/responsive.css">
<title>{title} - Summary ({lang})</title>
<style>
  body {{ font-family: "Times New Roman", serif; font-size: 12pt; line-height: 1.5; text-align: justify; max-width: 210mm; margin: 0 auto; padding: 20px 3.18cm; }}
  h1 {{ font-size: 16pt; text-align: center; }}
  h2 {{ font-size: 14pt; border-bottom: 1px solid #000; padding-bottom: 3px; }}
  h3 {{ font-size: 12pt; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 11pt; }}
  th, td {{ border: 1px solid #000; padding: 5px 7px; }}
  th {{ background-color: #eee; }}
  .toolbar {{ text-align: center; margin-bottom: 14px; }}
  .toolbar button {{ font-size: 12pt; padding: 6px 16px; cursor: pointer; }}
  @media print {{ .toolbar {{ display: none; }} body {{ padding: 0; }} }}
  @media screen and (max-width: 768px) {{ body {{ padding: 16px; font-size: 14px; }} table {{ display: block; overflow-x: auto; }} }}
  @media screen and (max-width: 480px) {{ body {{ padding: 12px; font-size: 13px; }} }}
</style>
<script>window.MathJax = {{ tex: {{ inlineMath: [['\\\\(','\\\\)']], displayMath: [['\\\\[','\\\\]']] }} }};</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js" async></script>
</head>
<body>
<div class="toolbar"><button onclick="window.print()">Print / Save as PDF</button></div>
<h1>Ringkasan: {title}</h1>
<p style="text-align:center; font-style:italic;">{title}</p>
<p style="text-align:center; font-size:11pt;">Summarized from original source</p>

<!-- WRITE YOUR SUMMARY CONTENT HERE -->

<p style="font-size:10pt; font-style:italic; color:#333; margin-top:24px; border-top:1px solid #999; padding-top:8px;">
Note: This is a self-study summary generated for educational purposes. For academic use, please refer to the original source.
</p>
</body>
</html>"""


def call_openrouter(text: str, prompt: str) -> str:
    """Call OpenRouter API with the given text and prompt."""
    if not OPENROUTER_API_KEY:
        print("[ERROR] OPENROUTER_API_KEY not found in .env")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/heru2233/summary_academia",
        "X-Title": "Academic Summary Pipeline"
    }

    # Truncate text if too long (Ox Alpha has 1M context, but let's be safe)
    max_chars = 800000  # ~200K tokens
    if len(text) > max_chars:
        print(f"[WARNING] Text truncated from {len(text)} to {max_chars} chars")
        text = text[:max_chars]

    messages = [
        {
            "role": "system",
            "content": "You are an expert academic summarizer. Output ONLY valid HTML, no markdown or code blocks."
        },
        {
            "role": "user",
            "content": f"{prompt}\n\n---\n\nPDF CONTENT:\n\n{text}"
        }
    ]

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "max_tokens": 16000,
        "temperature": 0.3
    }

    print(f"[INFO] Calling OpenRouter API (model: {OPENROUTER_MODEL})...")
    print(f"[INFO] Text length: {len(text)} chars (~{len(text)//4} tokens)")

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=300  # 5 minutes timeout
        )

        if response.status_code != 200:
            print(f"[ERROR] API error {response.status_code}: {response.text}")
            sys.exit(1)

        result = response.json()

        if "choices" not in result or len(result["choices"]) == 0:
            print(f"[ERROR] No choices in response: {json.dumps(result, indent=2)}")
            sys.exit(1)

        content = result["choices"][0]["message"]["content"]

        # Clean up: remove markdown code blocks if present
        if content.startswith("```html"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        return content.strip()

    except requests.exceptions.Timeout:
        print("[ERROR] API request timed out")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] API request failed: {e}")
        sys.exit(1)


def save_html(content: str, output_path: Path):
    """Save HTML content to file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"[OK] Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Auto-summary using OpenRouter API")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--title", required=True, help="Title of the book/article")
    parser.add_argument("--type", choices=["book", "article"], required=True, help="Type of content")
    parser.add_argument("--lang", choices=["ind", "eng", "both"], default="both", help="Language(s) to generate")
    parser.add_argument("--output", help="Output directory (default: auto-detect)")
    parser.add_argument("--dry-run", action="store_true", help="Only extract text, don't call API")

    args = parser.parse_args()

    # Resolve PDF path
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        # Try relative to project root
        pdf_path = PROJECT_ROOT / args.pdf
        if not pdf_path.exists():
            print(f"[ERROR] PDF not found: {args.pdf}")
            sys.exit(1)

    print(f"[INFO] PDF: {pdf_path}")
    print(f"[INFO] Title: {args.title}")
    print(f"[INFO] Type: {args.type}")
    print(f"[INFO] Language: {args.lang}")

    # Extract text
    print("\n[STEP 1] Extracting text from PDF...")
    text = extract_text_from_pdf(str(pdf_path))
    print(f"[OK] Extracted {len(text)} characters")

    if args.dry_run:
        print("\n[DRY RUN] Text extracted. Not calling API.")
        print(text[:2000] + "..." if len(text) > 2000 else text)
        return

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        # Auto-detect based on PDF location
        pdf_parts = pdf_path.parts
        if "books" in pdf_parts:
            book_name = pdf_parts[pdf_parts.index("books") + 1]
            output_dir = DOCS_DIR / "books" / book_name
        elif "articles" in pdf_parts:
            article_name = pdf_parts[pdf_parts.index("articles") + 1]
            output_dir = DOCS_DIR / "articles" / article_name
        else:
            output_dir = DOCS_DIR / "misc"

    print(f"\n[STEP 2] Output directory: {output_dir}")

    # Generate summaries
    languages = []
    if args.lang in ["ind", "both"]:
        languages.append(("ind", "id", "Bahasa Indonesia"))
    if args.lang in ["eng", "both"]:
        languages.append(("eng", "en", "English"))

    for lang_code, html_code, lang_name in languages:
        print(f"\n[STEP 3] Generating {lang_name} summary...")

        # Get prompt
        if args.type == "book":
            prompt = get_book_prompt(args.title, lang_name, html_code)
        else:
            prompt = get_article_prompt(args.title, lang_name, html_code)

        # Call API
        html_content = call_openrouter(text, prompt)

        # Generate filename
        if args.type == "book":
            # Try to extract chapter number from title or PDF name
            pdf_name = pdf_path.stem
            if "ch" in pdf_name.lower():
                ch_num = pdf_name.replace("ch", "").replace("CH", "")
                filename = f"Ringkasan_Chapter_{ch_num}_{lang_code.upper()}.html"
            else:
                filename = f"Ringkasan_{args.title.replace(' ', '_')}_{lang_code.upper()}.html"
        else:
            # Article: use author year format
            pdf_name = pdf_path.stem
            if "Myers" in pdf_name or "myers" in pdf_name:
                filename = f"Ringkasan_Myers_1984_{lang_code.upper()}.html"
            elif "McInnes" in pdf_name or "mcinnes" in pdf_name:
                filename = f"Ringkasan_McInnes_1982_{lang_code.upper()}.html"
            else:
                filename = f"Ringkasan_{pdf_name}_{lang_code.upper()}.html"

        output_path = output_dir / filename
        save_html(html_content, output_path)

    print("\n" + "=" * 50)
    print("[DONE] All summaries generated!")
    print(f"[INFO] Output: {output_dir}")
    print("\n[NEXT] To publish to GitHub Pages:")
    print(f"  cd {PROJECT_ROOT}")
    print(f"  git add docs/")
    print(f"  git commit -m 'Add summary: {args.title}'")
    print(f"  git push")


if __name__ == "__main__":
    main()
