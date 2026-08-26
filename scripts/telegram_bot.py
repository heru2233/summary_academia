"""
telegram_bot.py - Bot Telegram untuk Auto-Summary

Improvements:
- Uses PyMuPDF (fitz) for better PDF text extraction
- Auto-detects title from PDF using AI
- Language always "both" (English + Indonesian)
- Full logging to file + console
- Returns to main menu after processing

Cara pakai:
    python telegram_bot.py

Requirements:
    pip install python-dotenv requests PyMuPDF
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

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"

import requests

# ============================================
# PROMPTS
# ============================================

PROMPT_DETECT_TITLE = """Extract the main title from this academic text.
Return ONLY the title, nothing else. If it's a book chapter, return the chapter title.
If it's a journal article, return the article title.

Text (first 2000 chars):
{text}

Title:"""

PROMPT_BOOK = """You are an academic summarizer. Summarize this text into a well-structured HTML article.

IMPORTANT RULES:
- Write everything in {lang_name}
- Use proper HTML5 structure
- Use <h3> for main sections, <h4> for subsections
- Use <p> for paragraphs
- Use <b> or <strong> for emphasis
- Use <ul>/<ol> for lists
- Use <table> for tabular data (with <thead>, <tbody>, <th>, <td>)
- For equations, use: <div class="eq">\\[equation\\]</div>
- Length: 3000-5000 words
- Include key concepts, theories, examples, and conclusions
- Do NOT include <html>, <head>, <body>, or <style> tags - just the content
- Do NOT use MathJax scripts

TITLE: {title}

TEXT:
{text}

Generate the HTML summary now:"""

PROMPT_ARTICLE = """You are an academic summarizer. Summarize this journal article into a well-structured HTML article.

IMPORTANT RULES:
- Write everything in {lang_name}
- Use proper HTML5 structure
- Use <h3> for sections (Introduction, Literature Review, Methodology, Findings, Conclusion)
- Use <p> for paragraphs
- Use <b> for emphasis
- Use <table> for data/results
- For equations, use: <div class="eq">\\[equation\\]</div>
- Length: 2000-4000 words
- Cover: research question, methodology, key findings, implications
- Do NOT include <html>, <head>, <body>, or <style> tags
- Do NOT use MathJax scripts

TITLE: {title}

TEXT:
{text}

Generate the HTML summary now:"""


# ============================================
# TELEGRAM BOT CLASS
# ============================================

class TelegramBot:
    """Simple Telegram bot using long polling."""

    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.offset = 0
        logger.info(f"Bot initialized with token ending: ...{token[-8:]}")

    def get_updates(self):
        url = f"{self.base_url}/getUpdates"
        params = {"offset": self.offset, "timeout": 30}
        try:
            resp = requests.get(url, params=params, timeout=35)
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
        url = f"{self.base_url}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        try:
            resp = requests.post(url, json=payload, timeout=10)
            result = resp.json()
            if not result.get("ok"):
                logger.error(f"send_message failed: {result}")
            return result
        except Exception as e:
            logger.error(f"send_message error: {e}")
            return None

    def send_chat_action(self, chat_id, action="typing"):
        url = f"{self.base_url}/sendChatAction"
        try:
            requests.post(url, json={"chat_id": chat_id, "action": action}, timeout=5)
        except:
            pass

    def get_file(self, file_id):
        url = f"{self.base_url}/getFile"
        resp = requests.get(url, params={"file_id": file_id}, timeout=10)
        if resp.status_code != 200:
            return None

        file_info = resp.json().get("result", {})
        file_path = file_info.get("file_path")
        if not file_path:
            return None

        download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        resp = requests.get(download_url, timeout=60)
        if resp.status_code == 200:
            return resp.content
        return None

    def answer_callback_query(self, callback_query_id, text=""):
        url = f"{self.base_url}/answerCallbackQuery"
        try:
            requests.post(url, json={
                "callback_query_id": callback_query_id,
                "text": text
            }, timeout=5)
        except:
            pass

    def edit_message(self, chat_id, message_id, text, reply_markup=None):
        url = f"{self.base_url}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        try:
            resp = requests.post(url, json=payload, timeout=10)
            return resp.json()
        except Exception as e:
            logger.error(f"edit_message error: {e}")
            return None


# ============================================
# MAIN MENU
# ============================================

def send_main_menu(bot, chat_id):
    """Send main menu to user."""
    bot.send_message(
        chat_id,
        "🤖 <b>Academic Summary Bot</b>\n\n"
        "Kirim file PDF untuk diringkas otomatis.\n\n"
        "<b>Cara pakai:</b>\n"
        "1. Kirim file PDF\n"
        "2. Pilih tipe (buku/artikel)\n"
        "3. Tunggu proses selesai\n"
        "4. Dapatkan link GitHub Pages\n\n"
        "Judul & bahasa (ENG+IND) di-auto oleh AI.\n\n"
        "<b>Commands:</b>\n"
        "/start - Menu utama\n"
        "/help - Bantuan\n"
        "/cancel - Batalkan proses\n"
        "/status - Status bot"
    )


# ============================================
# PDF TEXT EXTRACTION (PyMuPDF)
# ============================================

def extract_text_from_pdf(pdf_data):
    """Extract text from PDF using PyMuPDF - much more reliable than pdftotext."""
    try:
        import pymupdf  # New PyMuPDF API
        doc = pymupdf.open(stream=pdf_data, filetype="pdf")
        page_count = len(doc)
        text = ""
        for page_num in range(page_count):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            text += f"\n--- Page {page_num + 1} ---\n{page_text}"
        doc.close()
        
        if len(text.strip()) < 100:
            logger.warning(f"Extracted text too short ({len(text)} chars), PDF might be scanned")
            return None
        
        logger.info(f"Extracted {len(text)} chars from {page_count} pages")
        return text.strip()
    except ImportError:
        logger.error("PyMuPDF not installed. Run: pip install pymupdf")
        return None
    except Exception as e:
        logger.error(f"PyMuPDF extraction failed: {e}")
        return None


# ============================================
# AI FUNCTIONS
# ============================================

def call_openrouter(prompt, max_tokens=8000):
    """Call OpenRouter API."""
    url = "https://openrouter.ai/api/v1/chat/completions"
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

    try:
        logger.info(f"Calling OpenRouter API (model: {OPENROUTER_MODEL})")
        resp = requests.post(url, headers=headers, json=payload, timeout=600)
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(f"API response: {len(content)} chars")
            return content
        else:
            logger.error(f"API error {resp.status_code}: {resp.text[:500]}")
            return None
    except Exception as e:
        logger.error(f"API call failed: {e}")
        return None


def detect_title(text):
    """Auto-detect title from PDF text using AI."""
    sample = text[:2000]
    prompt = PROMPT_DETECT_TITLE.format(text=sample)
    title = call_openrouter(prompt, max_tokens=100)
    if title:
        title = title.strip().strip('"').strip("'")
        logger.info(f"Detected title: {title}")
    return title


def generate_html(text, title, summary_type, lang):
    """Generate HTML summary using AI."""
    lang_name = "Bahasa Indonesia" if lang == "ind" else "English"

    if summary_type == "book":
        prompt = PROMPT_BOOK.format(lang_name=lang_name, title=title, text=text)
    else:
        prompt = PROMPT_ARTICLE.format(lang_name=lang_name, title=title, text=text)

    # Truncate if too long (keep first 80K chars)
    if len(text) > 80000:
        text = text[:80000] + "\n\n[TEXT TRUNCATED]"
        prompt = prompt.replace(text[:80000], text)

    return call_openrouter(prompt, max_tokens=8000)


# ============================================
# SAVE & PUSH
# ============================================

def save_html(html_content, title, summary_type, lang, category=None):
    """Save HTML to docs folder."""
    clean_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
    clean_title = clean_title.replace(" ", "_")

    lang_suffix = lang.upper()

    if summary_type == "book":
        book_folder = category or "financial-institutions-management"
        folder = DOCS_DIR / "books" / book_folder
        filename = f"Ringkasan_{clean_title}_{lang_suffix}.html"
    else:
        article_folder = category or clean_title.lower().replace("_", "-")
        folder = DOCS_DIR / "articles" / article_folder
        filename = f"Ringkasan_{clean_title}_{lang_suffix}.html"

    folder.mkdir(parents=True, exist_ok=True)
    filepath = folder / filename

    full_html = f"""<!DOCTYPE html>
<html lang="{lang}">
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
{html_content}
</body>
</html>"""

    filepath.write_text(full_html, encoding="utf-8")
    logger.info(f"Saved: {filepath}")
    return filepath


def push_to_github():
    """Git add, commit, push."""
    try:
        import subprocess
        subprocess.run(["git", "add", "docs/"], cwd=PROJECT_ROOT, check=True, timeout=30)
        subprocess.run(
            ["git", "commit", "-m", "Auto-summary: update via Telegram bot"],
            cwd=PROJECT_ROOT, check=True, timeout=30
        )
        subprocess.run(["git", "push"], cwd=PROJECT_ROOT, check=True, timeout=60)
        logger.info("Git push successful")
        return True
    except Exception as e:
        logger.error(f"Git push failed: {e}")
        return False


def get_github_pages_url(filepath):
    """Convert local path to GitHub Pages URL."""
    try:
        rel = filepath.relative_to(DOCS_DIR)
        return f"https://heru2233.github.io/summary_academia/{rel.as_posix()}"
    except:
        return None


# ============================================
# MAIN PROCESSING
# ============================================

def process_pdf(chat_id, bot, pdf_data, filename, summary_type="auto"):
    """Full pipeline: PDF -> extract -> detect title -> AI summarize -> save -> push."""
    start_time = time.time()
    bot.send_chat_action(chat_id, "typing")

    try:
        # Step 1: Extract text
        bot.send_message(chat_id, "📖 Mengekstrak teks dari PDF...")
        text = extract_text_from_pdf(pdf_data)
        if not text:
            bot.send_message(chat_id, "❌ Gagal mengekstrak teks. PDF mungkin scanned/gambar.")
            return False

        word_count = len(text.split())
        bot.send_message(chat_id, f"✅ Teks ter-ekstrak: {word_count:,} kata")

        # Step 2: Auto-detect title
        bot.send_chat_action(chat_id, "typing")
        bot.send_message(chat_id, "🔍 Mendeteksi judul...")
        title = detect_title(text)
        if not title:
            title = Path(filename).stem.replace("_", " ")
            bot.send_message(chat_id, f"⚠️ AI gagal deteksi judul, menggunakan: {title}")
        else:
            bot.send_message(chat_id, f"📝 Judul: <b>{title}</b>")

        # Step 3: Auto-detect type (book vs article) if not specified
        if summary_type == "auto":
            bot.send_chat_action(chat_id, "typing")
            type_prompt = f"Is this text from a BOOK CHAPTER or a JOURNAL ARTICLE? Reply with only: book or article\n\nTitle: {title}\nFirst 500 chars: {text[:500]}"
            type_result = call_openrouter(type_prompt, max_tokens=10)
            if type_result and "article" in type_result.lower():
                summary_type = "article"
            else:
                summary_type = "book"
            bot.send_message(chat_id, f"📋 Tipe: <b>{summary_type.upper()}</b>")

        # Step 4: Generate summaries in BOTH languages
        urls = []
        for lang in ["eng", "ind"]:
            lang_name = "English" if lang == "eng" else "Bahasa Indonesia"
            bot.send_chat_action(chat_id, "typing")
            bot.send_message(chat_id, f"🤖 Generating {lang_name} summary... mohon tunggu 1-2 menit...")

            html = generate_html(text, title, summary_type, lang)
            if not html:
                bot.send_message(chat_id, f"❌ Gagal generate ringkasan {lang_name}")
                continue

            filepath = save_html(html, title, summary_type, lang)
            url = get_github_pages_url(filepath)
            urls.append((lang, url, filepath.name))
            bot.send_message(chat_id, f"✅ {lang_name} selesai: {filepath.name}")

        # Step 5: Push to GitHub
        if urls:
            bot.send_message(chat_id, "🚀 Pushing ke GitHub...")
            push_success = push_to_github()

            elapsed = time.time() - start_time
            result_msg = f"✅ <b>Selesai!</b> ({elapsed:.0f} detik)\n\n"
            for lang, url, fname in urls:
                lang_name = "English" if lang == "eng" else "Indonesia"
                result_msg += f"📖 {lang_name}: {url}\n\n"

            if push_success:
                result_msg += "🔗 GitHub Pages akan update dalam 1-2 menit."
            else:
                result_msg += "⚠️ Push gagal. Coba push manual: git push"

            bot.send_message(chat_id, result_msg)
            logger.info(f"Process completed in {elapsed:.0f}s: {title}")
            return True
        else:
            bot.send_message(chat_id, "❌ Tidak ada ringkasan yang berhasil dibuat.")
            return False

    except Exception as e:
        logger.error(f"Process failed: {e}", exc_info=True)
        bot.send_message(chat_id, f"❌ Error: {str(e)[:200]}")
        return False


# ============================================
# BOT MAIN LOOP
# ============================================

def main():
    """Main bot loop."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY not set in .env")
        sys.exit(1)

    bot = TelegramBot(TELEGRAM_BOT_TOKEN)
    logger.info(f"Bot started. Model: {OPENROUTER_MODEL}")
    logger.info(f"Log file: {LOG_FILE}")
    logger.info("Waiting for messages... (Ctrl+C to stop)")

    # Track pending PDFs per user
    pending_pdfs = {}

    while True:
        try:
            updates = bot.get_updates()

            for update in updates:
                update_id = update.get("update_id", "?")

                # Handle callback queries (inline keyboard buttons)
                if "callback_query" in update:
                    cq = update["callback_query"]
                    chat_id = cq["message"]["chat"]["id"]
                    data = cq["data"]
                    user = cq["from"].get("username", cq["from"].get("first_name", "?"))

                    logger.info(f"[{user}] callback: {data}")
                    bot.answer_callback_query(cq["id"])

                    if data.startswith("type_"):
                        summary_type = data.replace("type_", "")
                        if chat_id in pending_pdfs:
                            pending_pdfs[chat_id]["type"] = summary_type
                            # Start processing (language always both)
                            p = pending_pdfs[chat_id]
                            bot.edit_message(
                                chat_id, cq["message"]["message_id"],
                                f"📄 Tipe: <b>{summary_type.upper()}</b>\n"
                                f"🌐 Bahasa: <b>BOTH</b>\n\n"
                                "🚀 <b>Memulai proses...</b>\n"
                                "Mohon tunggu beberapa menit..."
                            )
                            # Process and return to main menu
                            process_pdf(chat_id, bot, p["pdf_data"], p["filename"], summary_type)
                            del pending_pdfs[chat_id]
                            # Return to main menu
                            send_main_menu(bot, chat_id)

                # Handle text messages
                elif "message" in update and "text" in update["message"]:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    text = msg["text"]
                    user = msg["from"].get("username", msg["from"].get("first_name", "?"))

                    logger.info(f"[{user}] text: {text}")

                    # Check if waiting for type selection
                    if chat_id in pending_pdfs and pending_pdfs[chat_id].get("wait_for") == "type":
                        # User typed instead of clicking button
                        if text.lower() in ["book", "buku"]:
                            pending_pdfs[chat_id]["type"] = "book"
                        elif text.lower() in ["article", "artikel"]:
                            pending_pdfs[chat_id]["type"] = "article"
                        else:
                            bot.send_message(chat_id, "Pilih: <b>book</b> atau <b>article</b>")
                            continue

                        pending_pdfs[chat_id]["wait_for"] = None
                        p = pending_pdfs[chat_id]
                        bot.send_message(
                            chat_id,
                            "🚀 <b>Memulai proses...</b>\n"
                            "Mohon tunggu beberapa menit..."
                        )
                        # Process and return to main menu
                        process_pdf(chat_id, bot, p["pdf_data"], p["filename"], p["type"])
                        del pending_pdfs[chat_id]
                        # Return to main menu
                        send_main_menu(bot, chat_id)

                    # Handle /start and /help
                    elif text in ["/start", "/help"]:
                        send_main_menu(bot, chat_id)

                    elif text == "/cancel":
                        if chat_id in pending_pdfs:
                            del pending_pdfs[chat_id]
                            bot.send_message(chat_id, "❌ Proses dibatalkan.")
                        else:
                            bot.send_message(chat_id, "Tidak ada proses yang sedang berjalan.")

                    elif text == "/status":
                        pending_count = len(pending_pdfs)
                        bot.send_message(
                            chat_id,
                            f"📊 <b>Bot Status</b>\n\n"
                            f"Model: {OPENROUTER_MODEL}\n"
                            f"Log: {LOG_FILE.name}\n"
                            f"Pending: {pending_count} users"
                        )

                # Handle document (PDF)
                elif "message" in update and "document" in update["message"]:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    doc = msg["document"]
                    user = msg["from"].get("username", msg["from"].get("first_name", "?"))

                    # Check if PDF
                    if not doc.get("file_name", "").lower().endswith(".pdf"):
                        bot.send_message(chat_id, "❌ Hanya file PDF yang didukung.")
                        continue

                    # Check file size (max 20MB)
                    if doc.get("file_size", 0) > 20 * 1024 * 1024:
                        bot.send_message(chat_id, "❌ File terlalu besar (maks 20MB).")
                        continue

                    logger.info(f"[{user}] sent PDF: {doc['file_name']} ({doc.get('file_size', 0) / 1024:.1f} KB)")
                    bot.send_message(chat_id, f"📥 Menerima file: <b>{doc['file_name']}</b>")

                    # Download PDF
                    bot.send_chat_action(chat_id, "typing")
                    pdf_data = bot.get_file(doc["file_id"])
                    if not pdf_data:
                        bot.send_message(chat_id, "❌ Gagal download file.")
                        continue

                    # Store PDF and ask for type (title & language auto-detected)
                    pending_pdfs[chat_id] = {
                        "pdf_data": pdf_data,
                        "filename": doc["file_name"],
                        "wait_for": "type"
                    }

                    bot.send_message(
                        chat_id,
                        f"✅ File diterima: <b>{doc['file_name']}</b> ({len(pdf_data) / 1024:.1f} KB)\n\n"
                        "Judul & bahasa akan di-auto oleh AI.\n"
                        "Pilih tipe ringkasan:",
                        reply_markup={
                            "inline_keyboard": [
                                [{"text": "📚 Buku (Book Chapter)", "callback_data": "type_book"}],
                                [{"text": "📄 Artikel Jurnal (Journal Article)", "callback_data": "type_article"}]
                            ]
                        }
                    )

        except KeyboardInterrupt:
            logger.info("Bot stopped by user.")
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}", exc_info=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
