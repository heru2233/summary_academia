#!/usr/bin/env python3
"""
auto_summary.py - Automatic PDF Summarization using OpenRouter API

Uses PyMuPDF (fitz) for reliable text extraction (better than pdftotext).

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
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import requests

# Configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
SOURCES_DIR = PROJECT_ROOT / "sources"


# ============================================
# PDF TEXT EXTRACTION (PyMuPDF)
# ============================================

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using PyMuPDF (fitz) - much more reliable than pdftotext."""
    try:
        import pymupdf  # New PyMuPDF API
        doc = pymupdf.open(pdf_path)
        page_count = len(doc)
        text = ""
        for page_num in range(page_count):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            text += f"\n--- Page {page_num + 1} ---\n{page_text}"
        doc.close()
        
        if len(text.strip()) < 100:
            logger.warning(f"Extracted text too short ({len(text)} chars), PDF might be scanned/image-based")
            return None
        
        logger.info(f"Extracted {len(text)} chars from {page_count} pages")
        return text.strip()
    except ImportError:
        logger.error("PyMuPDF not installed. Run: pip install pymupdf")
        sys.exit(1)
    except Exception as e:
        logger.error(f"PyMuPDF extraction failed: {e}")
        sys.exit(1)


# ============================================
# PROMPTS
# ============================================

PROMPT_BOOK = """You are an academic summarizer. Create a comprehensive summary of this book chapter.

RULES:
1. Output ONLY valid HTML content (no <html>, <head>, <body> tags)
2. Use <h3> for sections, <h4> for subsections
3. Use <p> for paragraphs, <b> for emphasis
4. Use <table> for tabular data
5. For equations: <div class="eq">\\[equation\\]</div>
6. Length: 5000-8000 words
7. Include all key concepts, formulas, tables, and examples
8. Language: {lang}

TITLE: {title}

PDF CONTENT:
{text}

Generate the HTML summary now:"""

PROMPT_ARTICLE = """You are an academic summarizer. Create a summary of this journal article.

RULES:
1. Output ONLY valid HTML content (no <html>, <head>, <body> tags)
2. Use <h3> for sections (Introduction, Methodology, Findings, Conclusion)
3. Use <p> for paragraphs, <b> for emphasis
4. Use <table> for data/results
5. For equations: <div class="eq">\\[equation\\]</div>
6. Length: 2000-4000 words
7. Cover: research question, methodology, key findings, implications
8. Language: {lang}

TITLE: {title}

PDF CONTENT:
{text}

Generate the HTML summary now:"""


# ============================================
# API CALL
# ============================================

def call_openrouter(prompt: str, max_tokens: int = 16000) -> str:
    """Call OpenRouter API."""
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY not found in .env")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.3
    }

    logger.info(f"Calling OpenRouter API (model: {OPENROUTER_MODEL})")

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=600)

        if response.status_code != 200:
            logger.error(f"API error {response.status_code}: {response.text[:500]}")
            sys.exit(1)

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # Clean up markdown code blocks if present
        if content.startswith("```html"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        logger.info(f"API response: {len(content)} chars")
        return content.strip()

    except requests.exceptions.Timeout:
        logger.error("API request timed out")
        sys.exit(1)
    except Exception as e:
        logger.error(f"API request failed: {e}")
        sys.exit(1)


# ============================================
# SAVE HTML
# ============================================

def save_html(content: str, output_path: Path, title: str, lang_code: str):
    """Save HTML content to file with proper wrapper."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    full_html = f"""<!DOCTYPE html>
<html lang="{lang_code}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ringkasan {title}</title>
    <link rel="stylesheet" href="../../css/responsive.css">
    <script>
        MathJax = {{
            tex: {{ inlineMath: [['$', '$'], ['\\\\(', '\\\\)']] }},
            svg: {{ fontCache: 'global' }}
        }};
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js" async></script>
    <style>
        body {{ font-family: 'Times New Roman', serif; font-size: 12pt; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.8; }}
        h3 {{ color: #1a5276; border-bottom: 2px solid #1a5276; padding-bottom: 5px; }}
        h4 {{ color: #2c3e50; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .eq {{ background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 4px; text-align: center; overflow-x: auto; }}
        @media print {{ body {{ font-size: 12pt; }} }}
    </style>
</head>
<body>
{content}
</body>
</html>"""

    output_path.write_text(full_html, encoding="utf-8")
    logger.info(f"Saved: {output_path}")


# ============================================
# MAIN
# ============================================

def main():
    parser = argparse.ArgumentParser(description="Auto-summary using OpenRouter API")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--title", help="Title (auto-detected if not provided)")
    parser.add_argument("--type", choices=["book", "article"], default="auto", help="Type of content (auto-detected)")
    parser.add_argument("--lang", choices=["ind", "eng", "both"], default="both", help="Language(s)")
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Only extract text")

    args = parser.parse_args()

    # Resolve PDF path
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        pdf_path = PROJECT_ROOT / args.pdf
        if not pdf_path.exists():
            logger.error(f"PDF not found: {args.pdf}")
            sys.exit(1)

    logger.info(f"PDF: {pdf_path}")
    logger.info(f"Log: {LOG_FILE}")

    # Step 1: Extract text
    logger.info("STEP 1: Extracting text from PDF...")
    text = extract_text_from_pdf(str(pdf_path))
    if not text:
        logger.error("Failed to extract text from PDF")
        sys.exit(1)

    if args.dry_run:
        logger.info("DRY RUN - Text extracted. Not calling API.")
        print(text[:3000])
        return

    # Step 2: Auto-detect title if not provided
    title = args.title
    if not title:
        logger.info("STEP 2: Auto-detecting title...")
        title_prompt = f"Extract ONLY the title of this document. Return as a short phrase (max 10 words). Do not explain.\n\nExamples: Enterprise Risk Management and Firm Performance, The Capital Structure Puzzle\n\nText:\n{text[:1500]}\n\nTitle (short phrase only):"
        title = call_openrouter(title_prompt, max_tokens=50)
        if title:
            title = title.strip().strip('"').strip("'").strip('.')
            title = title.split('\n')[0].strip()  # Take first line only
            if len(title) > 60:
                title = title[:57] + '...'
        else:
            title = pdf_path.stem.replace("_", " ").replace("-", " ")
        logger.info(f"Detected title: {title}")
    else:
        logger.info(f"Title: {title}")

    # Step 3: Auto-detect type if not specified
    summary_type = args.type
    if summary_type == "auto":
        logger.info("STEP 3: Auto-detecting type...")
        type_prompt = f"Is this from a BOOK CHAPTER or JOURNAL ARTICLE? Reply with only: book or article\n\nTitle: {title}\nFirst 500 chars: {text[:500]}"
        type_result = call_openrouter(type_prompt, max_tokens=10)
        if type_result and "article" in type_result.lower():
            summary_type = "article"
        else:
            summary_type = "book"
        logger.info(f"Detected type: {summary_type}")

    # Step 4: Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        pdf_parts = pdf_path.parts
        if "books" in pdf_parts:
            book_name = pdf_parts[pdf_parts.index("books") + 1]
            output_dir = DOCS_DIR / "books" / book_name
        elif "articles" in pdf_parts:
            article_name = pdf_parts[pdf_parts.index("articles") + 1]
            output_dir = DOCS_DIR / "articles" / article_name
        else:
            output_dir = DOCS_DIR / "misc"

    logger.info(f"Output: {output_dir}")

    # Step 5: Generate summaries
    languages = []
    if args.lang in ["ind", "both"]:
        languages.append(("ind", "id", "Bahasa Indonesia"))
    if args.lang in ["eng", "both"]:
        languages.append(("eng", "en", "English"))

    urls = []
    for lang_code, html_code, lang_name in languages:
        logger.info(f"Generating {lang_name} summary...")

        if summary_type == "book":
            prompt = PROMPT_BOOK.format(lang=lang_name, title=title, text=text)
        else:
            prompt = PROMPT_ARTICLE.format(lang=lang_name, title=title, text=text)

        # Truncate if too long
        if len(text) > 80000:
            text = text[:80000] + "\n\n[TEXT TRUNCATED]"
            prompt = prompt.replace(text[:80000], text)

        html_content = call_openrouter(prompt, max_tokens=16000)

        # Generate filename
        clean_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
        clean_title = clean_title.replace(" ", "_")
        if len(clean_title) > 50:
            clean_title = clean_title[:47] + "..."
        filename = f"Ringkasan_{clean_title}_{lang_code.upper()}.html"

        output_path = output_dir / filename
        save_html(html_content, output_path, title, html_code)
        urls.append((lang_name, output_path))

    # Done
    logger.info("=" * 50)
    logger.info("DONE! All summaries generated.")
    for lang_name, path in urls:
        logger.info(f"  {lang_name}: {path}")

    logger.info("\nTo publish to GitHub Pages:")
    logger.info(f"  cd {PROJECT_ROOT}")
    logger.info(f"  git add docs/")
    logger.info(f"  git commit -m 'Add summary: {title}'")
    logger.info(f"  git push")


if __name__ == "__main__":
    main()
