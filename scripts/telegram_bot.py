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
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")

PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"

import requests

# ============================================
# PROMPTS
# ============================================

PROMPT_SUMMARY = """Summarize this academic text into a well-structured HTML article in English.

Rules:
- Use <h3> for sections, <h4> for subsections
- Use <p> for paragraphs, <b> for emphasis
- Use <table> for data
- Length: 3000-5000 words
- Do NOT include <html>, <head>, <body>, <style> tags
- Do NOT use MathJax

Title: {title}

Text:
{text}

HTML:"""

PROMPT_TRANSLATE = """Translate the following HTML content to {lang}. OUTPUT ONLY THE TRANSLATED HTML. Do NOT explain, do NOT show your thinking, do NOT add comments. Just output the translated HTML.

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

def extract_text(pdf_data):
    try:
        import pymupdf
        doc = pymupdf.open(stream=pdf_data, filetype="pdf")
        text = ""
        for i in range(len(doc)):
            text += doc.load_page(i).get_text()
        doc.close()
        logger.info(f"Extracted {len(text)} chars")
        return text.strip() if len(text.strip()) > 100 else None
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return None


# ============================================
# AI FUNCTIONS
# ============================================

def call_ai(prompt, max_tokens=8000):
    try:
        resp = requests.post("https://openrouter.ai/api/v1/chat/completions",
                           headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}",
                                   "Content-Type": "application/json"},
                           json={"model": OPENROUTER_MODEL,
                                 "messages": [{"role": "user", "content": prompt}],
                                 "max_tokens": max_tokens, "temperature": 0.3},
                           timeout=600)
        if resp.status_code != 200:
            logger.error(f"API error: {resp.status_code}")
            return None
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        # Clean markdown
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()
    except Exception as e:
        logger.error(f"API failed: {e}")
        return None


def generate_summary(text, title):
    if len(text) > 60000:
        text = text[:60000]
    return call_ai(PROMPT_SUMMARY.format(title=title, text=text))


def translate(html, lang):
    """Translate HTML in chunks to avoid token limit."""
    # Split by <h3> sections to keep structure
    import re
    sections = re.split(r'(<h3[^>]*>.*?</h3>)', html)
    
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
        body {{ font-family: 'Times New Roman', serif; font-size: 12pt; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.8; }}
        h3 {{ color: #1a5276; border-bottom: 2px solid #1a5276; padding-bottom: 5px; }}
        h4 {{ color: #2c3e50; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .eq {{ background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 4px; text-align: center; }}
        @media print {{ body {{ font-size: 12pt; }} }}
    </style>
</head>
<body>
{html}
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
# MAIN PROCESS
# ============================================

def process_pdf(chat_id, bot, pdf_data, filename, summary_type):
    start = time.time()
    
    # Use PDF filename (without extension) as folder name
    folder_name = make_filename(Path(filename).stem)
    title = Path(filename).stem.replace("_", " ").replace("-", " ")
    
    # Step 1: Extract
    bot.send_chat_action(chat_id, "typing")
    bot.send_message(chat_id, "📖 Mengekstrak teks...")
    text = extract_text(pdf_data)
    if not text:
        bot.send_message(chat_id, "❌ Gagal ekstrak teks. PDF mungkin scanned.")
        return False
    
    bot.send_message(chat_id, f"✅ {len(text.split()):,} kata ter-ekstrak")
    
    # Step 2: Generate English
    bot.send_chat_action(chat_id, "typing")
    bot.send_message(chat_id, "🤖 Generating English summary...")
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
    bot.send_message(chat_id, "✅ English selesai")
    
    # Step 3: Translate to Indonesian
    bot.send_chat_action(chat_id, "typing")
    bot.send_message(chat_id, "🤖 Translating to Bahasa Indonesia...")
    ind = translate(eng, "Bahasa Indonesia")
    if ind:
        save_and_create_index(folder, f"Ringkasan_{folder_name}_IND.html", ind, title, "id")
        bot.send_message(chat_id, "✅ Indonesia selesai")
    else:
        bot.send_message(chat_id, "⚠️ Gagal translate, hanya English")
    
    # Step 4: Push
    bot.send_message(chat_id, "🚀 Pushing ke GitHub...")
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
# BOT LOOP
# ============================================

def main():
    if not TELEGRAM_BOT_TOKEN or not OPENROUTER_API_KEY:
        print("ERROR: Set TELEGRAM_BOT_TOKEN and OPENROUTER_API_KEY in .env")
        sys.exit(1)
    
    bot = TelegramBot(TELEGRAM_BOT_TOKEN)
    logger.info(f"Bot started. Model: {OPENROUTER_MODEL}")
    
    pending = {}  # {chat_id: {pdf_data, filename, wait_for, type}}
    
    MENU = ("🤖 <b>Academic Summary Bot</b>\n\n"
            "Kirim PDF, pilih tipe, selesai.\n"
            "Bahasa: English + Indonesia (auto)\n\n"
            "/start - Menu | /cancel - Batal | /status - Status")
    
    while True:
        try:
            for update in bot.get_updates():
                # Callback (button click)
                if "callback_query" in update:
                    cq = update["callback_query"]
                    cid = cq["message"]["chat"]["id"]
                    data = cq["data"]
                    bot.answer_callback_query(cq["id"])
                    
                    if cid in pending and data.startswith("type_"):
                        p = pending[cid]
                        p["type"] = data.replace("type_", "")
                        bot.edit_message(cid, cq["message"]["message_id"],
                                       f"🚀 Proses: {p['filename']}\nTipe: {p['type'].upper()}\nTunggu...")
                        process_pdf(cid, bot, p["pdf_data"], p["filename"], p["type"])
                        del pending[cid]
                        bot.send_message(cid, MENU)
                
                # Text message
                elif "message" in update and "text" in update["message"]:
                    msg = update["message"]
                    cid = msg["chat"]["id"]
                    text = msg["text"]
                    
                    if text in ["/start", "/help"]:
                        bot.send_message(cid, MENU)
                    elif text == "/cancel":
                        if cid in pending:
                            del pending[cid]
                            bot.send_message(cid, "❌ Dibatalkan.")
                        else:
                            bot.send_message(cid, "Tidak ada proses.")
                    elif text == "/status":
                        bot.send_message(cid, f"📊 Model: {OPENROUTER_MODEL}\nPending: {len(pending)}")
                
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
