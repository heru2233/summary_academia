"""
telegram_bot.py - Bot Telegram untuk Auto-Summary (SIMPLIFIED)

Flow:
1. User kirim PDF
2. User pilih tipe (buku/artikel)
3. Bot generate English summary
4. Bot translate to Indonesian
5. Push ke GitHub Pages

Nama folder = nama file PDF (tanpa ekstensi)
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"bot_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load config
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")

PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"

import requests

# ============================================
# PROMPTS
# ============================================

PROMPT_SUMMARY = """CRITICAL: Output ONLY pure HTML. No markdown, no explanation, no thinking. Just HTML.

Create a COMPREHENSIVE summary of this academic text in English.

## HTML STRUCTURE - USE EXACTLY THIS FORMAT:

<div class="toc">
  <h3>Table of Contents</h3>
  <ul>
    <li><a href="#section1">Section Title</a></li>
  </ul>
</div>

<h2 id="section1">Section Title</h2>

<div class="interpretation">
  <h4>Interpretation</h4>
  <p>Deep explanation...</p>
</div>

<div class="formula-box">
  <span class="label">Formula Name</span>
  <div class="formula">Formula here</div>
</div>

<div class="example">
  <h4>Example</h4>
  <p>Step by step...</p>
</div>

<div class="analogy">
  <h4>Analogy</h4>
  <p>Simple comparison...</p>
</div>

<div class="insight">
  <h4>Key Insight</h4>
  <p>Important points...</p>
</div>

<div class="key-takeaway">
  <h4>Key Takeaways</h4>
  <ul><li>Summary points...</li></ul>
</div>

## STRICT RULES:
1. OUTPUT PURE HTML ONLY - NO markdown (##, **, ```)
2. Use <h2 id="..."> for main sections
3. Use <h3> for subsections
4. Each section MUST have: interpretation, formula (if applicable), example, analogy, insight
5. Complete content - do NOT truncate or abbreviate
6. Length: 8000-15000 words (comprehensive)
7. Include Table of Contents at top with anchor links
8. Include Key Takeaways at end

Title: {title}

Text:
{text}

HTML:"""

PROMPT_TRANSLATE = """Translate the following HTML content to {lang}.

## CRITICAL RULES:
1. OUTPUT ONLY THE TRANSLATED HTML - no explanations, no thinking, no comments
2. PRESERVE all HTML tags EXACTLY
3. PRESERVE all class names and id attributes
4. Keep mathematical formulas unchanged
5. COMPLETE TRANSLATION - translate ALL content, do NOT truncate or abbreviate
6. If content is long, translate in FULL - do NOT stop mid-sentence

## FOREIGN TERMS RULE (VERY IMPORTANT):
Keep these terms in their ORIGINAL English form (do NOT translate):
- Academic/technical terms: agency costs, principal, agent, perquisites, residual loss, monitoring costs, bonding costs, property rights, free cash flow, adverse selection, moral hazard, transaction costs, asset substitution, underinvestment, debt overhang, bankruptcy costs, human capital, motivation, skill-enhancing, opportunity-enhancing
- Model names: CAPM, APT, Black-Scholes, Markowitz, Sharpe ratio, Modigliani-Miller, AMO model
- Mathematical symbols and formulas
- Company names, author names, journal names
- Statistical terms: regression, correlation, variance, standard deviation, R-squared, meta-analysis, SEM

For general text, translate naturally to {lang}.

{html}"""


# ============================================
# BOT CLASS
# ============================================

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.offset = 0

    def get_updates(self):
        try:
            resp = requests.get(f"{self.base_url}/getUpdates", 
                              params={"offset": self.offset, "timeout": 30}, timeout=35)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    updates = data.get("result", [])
                    if updates:
                        self.offset = updates[-1]["update_id"] + 1
                    return updates
            return []
        except Exception as e:
            logger.error(f"get_updates error: {e}")
            return []

    def send_message(self, chat_id, text, reply_markup=None):
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        try:
            return requests.post(f"{self.base_url}/sendMessage", json=payload, timeout=10).json()
        except Exception as e:
            logger.error(f"send_message error: {e}")
            return None

    def send_chat_action(self, chat_id, action="typing"):
        try:
            requests.post(f"{self.base_url}/sendChatAction", 
                         json={"chat_id": chat_id, "action": action}, timeout=5)
        except:
            pass

    def get_file(self, file_id):
        try:
            resp = requests.get(f"{self.base_url}/getFile", params={"file_id": file_id}, timeout=10)
            if resp.status_code != 200:
                return None
            file_path = resp.json().get("result", {}).get("file_path")
            if not file_path:
                return None
            download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            resp = requests.get(download_url, timeout=60)
            return resp.content if resp.status_code == 200 else None
        except:
            return None

    def answer_callback_query(self, callback_query_id):
        try:
            requests.post(f"{self.base_url}/answerCallbackQuery",
                         json={"callback_query_id": callback_query_id}, timeout=5)
        except:
            pass

    def edit_message(self, chat_id, message_id, text):
        try:
            return requests.post(f"{self.base_url}/editMessageText",
                               json={"chat_id": chat_id, "message_id": message_id, 
                                     "text": text, "parse_mode": "HTML"}, timeout=10).json()
        except:
            return None


# ============================================
# PDF EXTRACTION
# ============================================

# Text cache to avoid re-extraction
_text_cache = {}

def extract_text(pdf_data, cache_key=None):
    """Extract text from PDF with optional caching."""
    # Check cache first
    if cache_key and cache_key in _text_cache:
        logger.info(f"Using cached text for {cache_key}")
        return _text_cache[cache_key]
    
    try:
        import pymupdf
        doc = pymupdf.open(stream=pdf_data, filetype="pdf")
        text = ""
        for i in range(len(doc)):
            text += doc.load_page(i).get_text()
        doc.close()
        
        result = text.strip() if len(text.strip()) > 100 else None
        
        # Cache the result
        if cache_key and result:
            _text_cache[cache_key] = result
            logger.info(f"Cached text for {cache_key}")
        
        logger.info(f"Extracted {len(text)} chars")
        return result
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return None


# ============================================
# AI CONFIG
# ============================================

# API Configuration - change these to switch providers
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.b.ai")
API_MODEL = os.getenv("API_MODEL", "gpt-5.2")

# ============================================
# AI FUNCTIONS
# ============================================

def call_ai(prompt, max_tokens=16000, retries=3):
    """Call AI API with retry logic for rate limits."""
    for attempt in range(retries):
        try:
            resp = requests.post(f"{API_BASE_URL}/v1/chat/completions",
                               headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}",
                                       "Content-Type": "application/json"},
                               json={"model": API_MODEL,
                                     "messages": [{"role": "user", "content": prompt}],
                                     "max_tokens": max_tokens, "temperature": 0.3},
                               timeout=600)
            
            # Success
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                # Clean markdown
                if content.startswith("```"):
                    content = content.split("\n", 1)[1] if "\n" in content else content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                return content.strip()
            
            # Rate limit (429) - retry with backoff
            if resp.status_code == 429:
                wait_time = (attempt + 1) * 10  # 10s, 20s, 30s
                logger.warning(f"Rate limited (429). Waiting {wait_time}s before retry {attempt + 1}/{retries}...")
                time.sleep(wait_time)
                continue
            
            # Other errors
            logger.error(f"API error: {resp.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"API failed: {e}")
            if attempt < retries - 1:
                time.sleep(10)
                continue
            return None
    
    logger.error(f"API failed after {retries} retries")
    return None


def generate_summary(text, title):
    if len(text) > 60000:
        text = text[:60000]
    return call_ai(PROMPT_SUMMARY.format(title=title, text=text), max_tokens=20000)


def translate(html, lang):
    """Translate HTML in chunks to avoid token limit."""
    # Split by <h2> or <h3> sections to keep structure
    import re
    sections = re.split(r'(<h2[^>]*>.*?</h2>|<h3[^>]*>.*?</h3>)', html)
    
    translated_parts = []
    current_chunk = ""
    
    for part in sections:
        # If adding this part would exceed 40K chars, translate current chunk first
        if len(current_chunk) + len(part) > 40000 and current_chunk:
            result = call_ai(PROMPT_TRANSLATE.format(lang=lang, html=current_chunk), max_tokens=15000)
            if result:
                translated_parts.append(result)
            current_chunk = ""
        current_chunk += part
    
    # Translate remaining chunk
    if current_chunk:
        result = call_ai(PROMPT_TRANSLATE.format(lang=lang, html=current_chunk), max_tokens=15000)
        if result:
            translated_parts.append(result)
    
    return "\n".join(translated_parts) if translated_parts else None


# ============================================
# SAVE & PUSH
# ============================================

def make_filename(name):
    """Sanitize filename."""
    clean = "".join(c for c in name if c.isalnum() or c in " -_").strip()
    clean = clean.replace(" ", "_")
    while "__" in clean:
        clean = clean.replace("__", "_")
    return clean[:40].rstrip("_. ") or "untitled"


def save_and_create_index(folder, filename, html, title, lang):
    """Save HTML file and create index.html if needed."""
    folder.mkdir(parents=True, exist_ok=True)
    
    # Save HTML
    filepath = folder / filename
    full_html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="../../css/responsive.css">
    <script>
        MathJax = {{ tex: {{ inlineMath: [['$', '$'], ['\\\\(', '\\\\)']] }}, svg: {{ fontCache: 'global' }} }};
    </script>
    <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js" async></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.8;
            color: #333;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-left: 10px;
            border-left: 4px solid #3498db;
        }}
        h3 {{
            color: #2980b9;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        h4 {{
            color: #7d3c98;
            margin-top: 15px;
            margin-bottom: 8px;
        }}
        .formula-box {{
            background: #ecf0f1;
            border-left: 4px solid #e74c3c;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
            font-family: 'Cambria Math', 'Times New Roman', serif;
        }}
        .formula-box .label {{
            font-weight: bold;
            color: #e74c3c;
            display: block;
            margin-bottom: 5px;
        }}
        .formula {{
            font-size: 18px;
            color: #2c3e50;
        }}
        .interpretation {{
            background: #e8f8f5;
            border-left: 4px solid #1abc9c;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }}
        .interpretation h4 {{
            color: #16a085;
            margin-top: 0;
        }}
        .example {{
            background: #fdf2e9;
            border-left: 4px solid #e67e22;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }}
        .example h4 {{
            color: #d35400;
            margin-top: 0;
        }}
        .analogy {{
            background: #f4ecf7;
            border-left: 4px solid #8e44ad;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }}
        .analogy h4 {{
            color: #7d3c98;
            margin-top: 0;
        }}
        .insight {{
            background: #d6eaf8;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }}
        .insight h4 {{
            color: #2980b9;
            margin-top: 0;
        }}
        .key-takeaway {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .key-takeaway h4 {{
            color: #856404;
            margin-bottom: 10px;
        }}
        .toc {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
        }}
        .toc h3 {{
            margin-top: 0;
            color: #2c3e50;
        }}
        .toc ul {{
            list-style: none;
            margin-left: 0;
        }}
        .toc li {{
            padding: 5px 0;
        }}
        .toc a {{
            color: #3498db;
            text-decoration: none;
        }}
        .toc a:hover {{
            text-decoration: underline;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            background: white;
        }}
        th, td {{
            border: 1px solid #bdc3c7;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background: #3498db;
            color: white;
            font-weight: bold;
        }}
        tr:nth-child(even) {{
            background: #f8f9fa;
        }}
        tr:hover {{
            background: #e8f4f8;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: Consolas, Monaco, monospace;
            color: #e74c3c;
        }}
        .highlight {{
            background: #ffeaa7;
            padding: 2px 5px;
            border-radius: 3px;
        }}
        ul, ol {{
            margin-left: 20px;
            margin-bottom: 15px;
        }}
        li {{
            margin-bottom: 8px;
        }}
        p {{
            margin-bottom: 12px;
        }}
        /* Mobile Mode Toggle */
        .mode-toggle {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
            background: #3498db;
            color: white;
            border: none;
            border-radius: 50px;
            padding: 12px 20px;
            font-size: 14px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transition: all 0.3s;
        }}
        .mode-toggle:hover {{
            background: #2980b9;
            transform: translateY(-2px);
        }}
        
        /* Mobile Mode Styles */
        body.mobile-mode {{
            padding: 10px !important;
            background: white !important;
        }}
        body.mobile-mode .container {{
            padding: 15px !important;
            box-shadow: none !important;
            border-radius: 0 !important;
            max-width: 100% !important;
        }}
        body.mobile-mode h1 {{
            font-size: 20px !important;
            padding-bottom: 8px !important;
        }}
        body.mobile-mode h2 {{
            font-size: 17px !important;
            margin-top: 20px !important;
        }}
        body.mobile-mode h3 {{
            font-size: 15px !important;
        }}
        body.mobile-mode .interpretation,
        body.mobile-mode .formula-box,
        body.mobile-mode .example,
        body.mobile-mode .analogy,
        body.mobile-mode .insight,
        body.mobile-mode .key-takeaway,
        body.mobile-mode .toc {{
            padding: 12px !important;
            margin: 10px 0 !important;
        }}
        body.mobile-mode .formula-box .formula {{
            font-size: 14px !important;
            word-wrap: break-word;
        }}
        body.mobile-mode table {{
            font-size: 12px !important;
        }}
        body.mobile-mode th, body.mobile-mode td {{
            padding: 6px 8px !important;
        }}
        body.mobile-mode .toc li {{
            padding: 4px 0 !important;
        }}
        body.mobile-mode .toc a {{
            font-size: 14px !important;
        }}
        
        @media print {{ body {{ font-size: 12pt; }} .mode-toggle {{ display: none; }} }}
    </style>
    <script>
        function toggleMode() {{
            document.body.classList.toggle('mobile-mode');
            const btn = document.querySelector('.mode-toggle');
            if (document.body.classList.contains('mobile-mode')) {{
                btn.textContent = '🖥️ Desktop Mode';
                localStorage.setItem('viewMode', 'mobile');
            }} else {{
                btn.textContent = '📱 Mobile Mode';
                localStorage.setItem('viewMode', 'desktop');
            }}
        }}
        
        // Load saved mode
        window.onload = function() {{
            const savedMode = localStorage.getItem('viewMode');
            if (savedMode === 'mobile') {{
                document.body.classList.add('mobile-mode');
                document.querySelector('.mode-toggle').textContent = '🖥️ Desktop Mode';
            }}
        }};
    </script>
</head>
<body>
    <button class="mode-toggle" onclick="toggleMode()">📱 Mobile Mode</button>
    <div class="container">
{html}
    </div>
</body>
</html>"""
    filepath.write_text(full_html, encoding="utf-8")
    logger.info(f"Saved: {filepath}")
    
    # Create index.html if not exists
    if not (folder / "index.html").exists():
        folder_name = folder.name
        index = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="stylesheet" href="../../css/responsive.css">
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: 'Times New Roman', serif; background: #f5f5f5; color: #333; min-height: 100vh; display: flex; flex-direction: column; align-items: center; padding: 40px 20px; }}
    @media screen and (max-width: 768px) {{ body {{ padding: 20px 16px; }} }}
    .container {{ max-width: 600px; width: 100%; }}
    .back {{ display: inline-block; margin-bottom: 20px; color: #1a73e8; text-decoration: none; }}
    .back:hover {{ text-decoration: underline; }}
    h1 {{ font-size: 22px; margin-bottom: 30px; }}
    .lang-card {{ background: #fff; border: 1px solid #ddd; border-radius: 8px; padding: 28px 30px; margin-bottom: 16px; text-decoration: none; color: #333; display: flex; align-items: center; justify-content: space-between; }}
    .lang-card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.1); transform: translateY(-2px); }}
    .lang-card .flag {{ font-size: 36px; margin-right: 16px; }}
    .lang-card .info {{ flex: 1; }}
    .lang-card .title {{ font-size: 20px; font-weight: bold; }}
    .lang-card .desc {{ font-size: 14px; color: #666; }}
    .lang-card .arrow {{ font-size: 24px; color: #999; }}
  </style>
</head>
<body>
  <div class="container">
    <a href="../index.html" class="back">&larr; Back to Articles</a>
    <h1>{title}</h1>
    <a href="Ringkasan_{folder_name}_ENG.html" class="lang-card">
      <span class="flag">🇬🇧</span>
      <div class="info">
        <div class="title">English</div>
        <div class="desc">Summary in English</div>
      </div>
      <span class="arrow">&rsaquo;</span>
    </a>
    <a href="Ringkasan_{folder_name}_IND.html" class="lang-card">
      <span class="flag">🇮🇩</span>
      <div class="info">
        <div class="title">Bahasa Indonesia</div>
        <div class="desc">Ringkasan dalam Bahasa Indonesia</div>
      </div>
      <span class="arrow">&rsaquo;</span>
    </a>
  </div>
</body>
</html>"""
        (folder / "index.html").write_text(index, encoding="utf-8")
        logger.info(f"Created index.html")
    
    return filepath


def update_articles_listing(folder_name, title):
    """Add new article to articles/index.html if not already listed."""
    articles_index = DOCS_DIR / "articles" / "index.html"
    if not articles_index.exists():
        return
    content = articles_index.read_text(encoding="utf-8")
    if folder_name in content:
        return
    new_card = f"""
    <a href="{folder_name}/index.html" class="article-card">
      <div class="info">
        <div class="title">{title}</div>
        <div class="meta">Auto-generated &bull; 2026</div>
      </div>
      <span class="arrow">&rsaquo;</span>
    </a>"""
    content = content.replace("\n  </div>", f"{new_card}\n\n  </div>")
    articles_index.write_text(content, encoding="utf-8")
    logger.info(f"Updated articles/index.html")


def push_to_github():
    try:
        import subprocess
        subprocess.run(["git", "add", "docs/"], cwd=PROJECT_ROOT, check=True, timeout=30)
        subprocess.run(["git", "commit", "-m", "Auto-summary: update"], cwd=PROJECT_ROOT, check=True, timeout=30)
        subprocess.run(["git", "push"], cwd=PROJECT_ROOT, check=True, timeout=60)
        return True
    except Exception as e:
        logger.error(f"Push failed: {e}")
        return False


def get_url(filepath):
    try:
        return f"https://heru2233.github.io/summary_academia/{filepath.relative_to(DOCS_DIR).as_posix()}"
    except:
        return None


# ============================================
# LIST & DELETE
# ============================================

def list_summaries():
    """List all saved summaries in docs/"""
    items = []
    for section in ["books", "articles"]:
        section_dir = DOCS_DIR / section
        if not section_dir.exists():
            continue
        for folder in sorted(section_dir.iterdir()):
            if not folder.is_dir() or folder.name.startswith("."):
                continue
            # Find ENG and IND files
            eng_files = list(folder.glob("*_ENG.html"))
            ind_files = list(folder.glob("*_IND.html"))
            if eng_files or ind_files:
                # Get title from folder name
                title = folder.name.replace("_", " ").replace("-", " ").title()
                items.append({
                    "folder": folder.name,
                    "section": section,
                    "title": title,
                    "has_eng": bool(eng_files),
                    "has_ind": bool(ind_files),
                    "path": folder
                })
    return items


def delete_summary(section, folder_name):
    """Delete a summary folder and its contents."""
    folder = DOCS_DIR / section / folder_name
    if not folder.exists():
        return False, "Folder not found"
    
    # Delete all files in folder
    for f in folder.iterdir():
        if f.is_file():
            f.unlink()
    # Delete folder
    folder.rmdir()
    
    # Update listing (articles/index.html)
    if section == "articles":
        _remove_from_listing(folder_name)
    
    return True, "Deleted"


def _remove_from_listing(folder_name):
    """Remove article from articles/index.html"""
    articles_index = DOCS_DIR / "articles" / "index.html"
    if not articles_index.exists():
        return
    content = articles_index.read_text(encoding="utf-8")
    # Remove the card block for this folder
    import re
    pattern = rf'\s*<a href="{re.escape(folder_name)}/index\.html".*?</a>'
    content = re.sub(pattern, "", content, flags=re.DOTALL)
    articles_index.write_text(content, encoding="utf-8")


def format_list_with_buttons(items):
    """Format items list with delete buttons."""
    if not items:
        return "📭 Tidak ada ringkasan tersimpan.", None
    
    msg = f"📚 <b>Ringkasan Tersimpan</b> ({len(items)} item)\n"
    msg += "Klik 🗑️ untuk menghapus item:\n\n"
    
    buttons = []
    for i, item in enumerate(items, 1):
        flags = ""
        if item["has_eng"]:
            flags += "🇬🇧"
        if item["has_ind"]:
            flags += "🇮🇩"
        section_label = "Buku" if item["section"] == "books" else "Artikel"
        msg += f"{i}. {flags} <b>{item['title']}</b> [{section_label}]\n"
        
        # Add delete button for each item
        buttons.append([{"text": f"🗑️ Hapus {item['title'][:30]}", "callback_data": f"delete_{item['section']}_{item['folder']}"}])
    
    # Add cancel button at bottom
    buttons.append([{"text": "❌ Batal", "callback_data": "cancel_delete"}])
    
    return msg, {"inline_keyboard": buttons}


# ============================================
# MAIN PROCESS
# ============================================

def process_pdf(chat_id, bot, pdf_data, filename, summary_type):
    start = time.time()
    
    # Use PDF filename (without extension) as folder name
    folder_name = make_filename(Path(filename).stem)
    title = Path(filename).stem.replace("_", " ").replace("-", " ")
    
    # Step 1: Extract (1/4)
    bot.send_chat_action(chat_id, "typing")
    bot.send_message(chat_id, "📖 <b>[1/4]</b> Mengekstrak teks...")
    text = extract_text(pdf_data, cache_key=folder_name)
    if not text:
        bot.send_message(chat_id, "❌ Gagal ekstrak teks. PDF mungkin scanned.")
        return False
    
    word_count = len(text.split())
    char_count = len(text)
    bot.send_message(chat_id, f"✅ <b>[1/4]</b> Selesai: {word_count:,} kata ({char_count:,} karakter)")
    
    # Step 2: Generate English (2/4)
    bot.send_chat_action(chat_id, "typing")
    bot.send_message(chat_id, "🤖 <b>[2/4]</b> Generating English summary...\n⏳ Estimated: 1-2 minutes")
    eng = generate_summary(text, title)
    if not eng:
        bot.send_message(chat_id, "❌ Gagal generate English summary")
        return False
    
    # Save English
    if summary_type == "book":
        folder = DOCS_DIR / "books" / folder_name
    else:
        folder = DOCS_DIR / "articles" / folder_name
    
    save_and_create_index(folder, f"Ringkasan_{folder_name}_ENG.html", eng, title, "en")
    if summary_type == "article":
        update_articles_listing(folder_name, title)
    eng_words = len(eng.split())
    bot.send_message(chat_id, f"✅ <b>[2/4]</b> English selesai ({eng_words:,} kata)")
    
    # Step 3: Translate to Indonesian (3/4)
    bot.send_chat_action(chat_id, "typing")
    bot.send_message(chat_id, "🤖 <b>[3/4]</b> Translating to Bahasa Indonesia...\n⏳ Estimated: 1-2 minutes")
    ind = translate(eng, "Bahasa Indonesia")
    if ind:
        save_and_create_index(folder, f"Ringkasan_{folder_name}_IND.html", ind, title, "id")
        ind_words = len(ind.split())
        bot.send_message(chat_id, f"✅ <b>[3/4]</b> Indonesia selesai ({ind_words:,} kata)")
    else:
        bot.send_message(chat_id, "⚠️ Gagal translate, hanya English")
    
    # Step 4: Push (4/4)
    bot.send_message(chat_id, "🚀 <b>[4/4]</b> Pushing ke GitHub...")
    pushed = push_to_github()
    
    # Results
    eng_url = get_url(folder / f"Ringkasan_{folder_name}_ENG.html")
    ind_url = get_url(folder / f"Ringkasan_{folder_name}_IND.html")
    
    elapsed = time.time() - start
    msg = f"✅ <b>Selesai!</b> ({elapsed:.0f}s)\n\n"
    msg += f"📖 English: {eng_url}\n"
    if ind:
        msg += f"📖 Indonesia: {ind_url}\n"
    msg += "\n🔗 Update dalam 1-2 menit." if pushed else "\n⚠️ Push gagal."
    
    bot.send_message(chat_id, msg)
    logger.info(f"Done in {elapsed:.0f}s: {title}")
    return True


# ============================================
# USER IDENTIFICATION
# ============================================

def get_user_name(update):
    """Extract user name from Telegram update."""
    try:
        if "callback_query" in update:
            user = update["callback_query"]["from"]
        elif "message" in update:
            user = update["message"]["from"]
        else:
            return "Unknown"
        name = user.get("first_name", "")
        username = user.get("username", "")
        if username:
            return f"@{username}"
        return name or "Unknown"
    except:
        return "Unknown"


# ============================================
# BOT LOOP
# ============================================

def main():
    if not TELEGRAM_BOT_TOKEN or not OPENROUTER_API_KEY:
        print("ERROR: Set TELEGRAM_BOT_TOKEN and OPENROUTER_API_KEY in .env")
        sys.exit(1)
    
    bot = TelegramBot(TELEGRAM_BOT_TOKEN)
    logger.info(f"Bot started. Model: {API_MODEL} @ {API_BASE_URL}")
    
    pending = {}  # {chat_id: {pdf_data, filename, wait_for, type}}
    
    MENU = ("🤖 <b>Academic Summary Bot</b>\n\n"
            "Kirim PDF, pilih tipe, selesai.\n"
            "Bahasa: English + Indonesia (auto)\n\n"
            "<b>Commands:</b>\n"
            "/start - Menu\n"
            "/list - Lihat semua ringkasan\n"
            "/delete [nomor] - Hapus ringkasan\n"
            "/cancel - Batal proses\n"
            "/status - Status bot\n\n"
            "<b>📚 Website:</b>\n"
            "<a href=\"https://heru2233.github.io/summary_academia\">Lihat Ringkasan Online</a>")
    
    while True:
        try:
            for update in bot.get_updates():
                user = get_user_name(update)
                
                # Callback (button click)
                if "callback_query" in update:
                    cq = update["callback_query"]
                    cid = cq["message"]["chat"]["id"]
                    data = cq["data"]
                    bot.answer_callback_query(cq["id"])
                    logger.info(f"[{user}] callback: {data}")
                    
                    # Handle PDF type selection
                    if cid in pending and data.startswith("type_"):
                        p = pending[cid]
                        p["type"] = data.replace("type_", "")
                        bot.edit_message(cid, cq["message"]["message_id"],
                                       f"🚀 Proses: {p['filename']}\nTipe: {p['type'].upper()}\nTunggu...")
                        process_pdf(cid, bot, p["pdf_data"], p["filename"], p["type"])
                        del pending[cid]
                        bot.send_message(cid, MENU)
                    
                    # Handle delete from list
                    elif data.startswith("delete_"):
                        parts = data.split("_", 2)
                        if len(parts) == 3:
                            section = parts[1]
                            folder_name = parts[2]
                            ok, msg = delete_summary(section, folder_name)
                            if ok:
                                bot.edit_message(cid, cq["message"]["message_id"],
                                               f"🗑️ Dihapus: {folder_name}")
                                push_to_github()
                                bot.send_message(cid, "🚀 Updated ke GitHub.")
                            else:
                                bot.send_message(cid, f"❌ Gagal menghapus: {msg}")
                            # Always return to menu
                            bot.send_message(cid, MENU)
                    
                    # Handle cancel delete
                    elif data == "cancel_delete":
                        bot.edit_message(cid, cq["message"]["message_id"],
                                       "❌ Dibatalkan.")
                        bot.send_message(cid, MENU)
                
                # Text message
                elif "message" in update and "text" in update["message"]:
                    msg = update["message"]
                    cid = msg["chat"]["id"]
                    text = msg["text"]
                    logger.info(f"[{user}] text: {text}")
                    
                    if text in ["/start", "/help"]:
                        bot.send_message(cid, MENU)
                    
                    elif text == "/list":
                        items = list_summaries()
                        msg, buttons = format_list_with_buttons(items)
                        bot.send_message(cid, msg, reply_markup=buttons)
                    
                    elif text.startswith("/delete"):
                        parts = text.split()
                        if len(parts) < 2:
                            bot.send_message(cid, "Format: /delete [nomor]\nLihat nomor di /list")
                        else:
                            try:
                                idx = int(parts[1]) - 1
                                items = list_summaries()
                                if 0 <= idx < len(items):
                                    item = items[idx]
                                    ok, msg = delete_summary(item["section"], item["folder"])
                                    if ok:
                                        bot.send_message(cid, f"🗑️ Dihapus: {item['title']}")
                                        push_to_github()
                                        bot.send_message(cid, "🚀 Updated ke GitHub.")
                                    else:
                                        bot.send_message(cid, f"❌ {msg}")
                                else:
                                    bot.send_message(cid, "❌ Nomor tidak valid.")
                            except ValueError:
                                bot.send_message(cid, "Format: /delete [nomor]")
                        bot.send_message(cid, MENU)
                    
                    elif text == "/cancel":
                        if cid in pending:
                            del pending[cid]
                            bot.send_message(cid, "❌ Dibatalkan.")
                        else:
                            bot.send_message(cid, "Tidak ada proses.")
                        bot.send_message(cid, MENU)
                    
                    elif text == "/status":
                        items = list_summaries()
                        bot.send_message(cid, f"📊 Model: {API_MODEL}\n"
                                       f"📁 Ringkasan: {len(items)}\n"
                                       f"⏳ Pending: {len(pending)}")
                        bot.send_message(cid, MENU)
                
                # Document (PDF)
                elif "message" in update and "document" in update["message"]:
                    msg = update["message"]
                    cid = msg["chat"]["id"]
                    doc = msg["document"]
                    
                    if not doc.get("file_name", "").lower().endswith(".pdf"):
                        bot.send_message(cid, "❌ Hanya PDF.")
                        continue
                    if doc.get("file_size", 0) > 20 * 1024 * 1024:
                        bot.send_message(cid, "❌ Maks 20MB.")
                        continue
                    
                    size_kb = doc.get("file_size", 0) / 1024
                    logger.info(f"[{user}] sent PDF: {doc['file_name']} ({size_kb:.1f} KB)")
                    
                    bot.send_chat_action(cid, "typing")
                    pdf_data = bot.get_file(doc["file_id"])
                    if not pdf_data:
                        bot.send_message(cid, "❌ Gagal download.")
                        continue
                    
                    pending[cid] = {"pdf_data": pdf_data, "filename": doc["file_name"]}
                    bot.send_message(cid, f"📥 <b>{doc['file_name']}</b>\nPilih tipe:",
                                   reply_markup={"inline_keyboard": [
                                       [{"text": "📚 Buku", "callback_data": "type_book"}],
                                       [{"text": "📄 Artikel", "callback_data": "type_article"}]
                                   ]})
        
        except KeyboardInterrupt:
            logger.info("Stopped.")
            break
        except Exception as e:
            logger.error(f"Loop error: {e}", exc_info=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
