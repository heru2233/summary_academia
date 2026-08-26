"""
telegram_bot.py - Bot Telegram untuk Auto-Summary

Cara pakai:
    python telegram_bot.py

Alur:
    1. User kirim PDF ke bot
    2. Bot tanya: judul, tipe (buku/artikel), bahasa
    3. Bot proses: ekstrak teks → AI summarize → save HTML
    4. Bot push ke GitHub Pages
    5. Bot kirim link ke user

Requirements:
    pip install python-dotenv requests
"""

import os
import sys
import json
import time
import subprocess
import tempfile
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load config
load_dotenv(Path(__file__).parent / ".env")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free")

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
SOURCES_DIR = PROJECT_ROOT / "sources"
DOCS_DIR = PROJECT_ROOT / "docs"

# Prompt template untuk buku
PROMPT_BOOK = """You are an academic summarizer. Summarize this text into a well-structured HTML article.

OUTPUT FORMAT:
- Write in {lang_name}
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

# Prompt template untuk artikel
PROMPT_ARTICLE = """You are an academic summarizer. Summarize this journal article into a well-structured HTML article.

OUTPUT FORMAT:
- Write in {lang_name}
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


class TelegramBot:
    """Simple Telegram bot using long polling."""

    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.offset = 0
        self.user_states = {}  # Track conversation state per user

    def get_updates(self):
        """Get pending updates from Telegram."""
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
            print(f"[ERROR] get_updates: {e}")
            return []

    def send_message(self, chat_id, text, reply_markup=None):
        """Send text message."""
        url = f"{self.base_url}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        try:
            resp = requests.post(url, json=payload, timeout=10)
            return resp.json()
        except Exception as e:
            print(f"[ERROR] send_message: {e}")
            return None

    def send_chat_action(self, chat_id, action="typing"):
        """Send chat action (typing indicator)."""
        url = f"{self.base_url}/sendChatAction"
        try:
            requests.post(url, json={"chat_id": chat_id, "action": action}, timeout=5)
        except:
            pass

    def get_file(self, file_id):
        """Download file from Telegram."""
        # Get file info
        url = f"{self.base_url}/getFile"
        resp = requests.get(url, params={"file_id": file_id}, timeout=10)
        if resp.status_code != 200:
            return None

        file_info = resp.json().get("result", {})
        file_path = file_info.get("file_path")
        if not file_path:
            return None

        # Download file
        download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
        resp = requests.get(download_url, timeout=60)
        if resp.status_code == 200:
            return resp.content
        return None

    def answer_callback_query(self, callback_query_id, text=""):
        """Answer callback query (button press)."""
        url = f"{self.base_url}/answerCallbackQuery"
        try:
            requests.post(url, json={
                "callback_query_id": callback_query_id,
                "text": text
            }, timeout=5)
        except:
            pass

    def edit_message(self, chat_id, message_id, text, reply_markup=None):
        """Edit existing message."""
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
            print(f"[ERROR] edit_message: {e}")
            return None


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using pdftotext."""
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"[ERROR] pdftotext failed: {result.stderr}")
            return None
    except FileNotFoundError:
        print("[ERROR] pdftotext not found. Install poppler-utils.")
        return None
    except subprocess.TimeoutExpired:
        print("[ERROR] pdftotext timeout")
        return None


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
        resp = requests.post(url, headers=headers, json=payload, timeout=600)
        if resp.status_code == 200:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        else:
            print(f"[ERROR] API {resp.status_code}: {resp.text[:500]}")
            return None
    except Exception as e:
        print(f"[ERROR] API call failed: {e}")
        return None


def generate_html(text, title, summary_type, lang):
    """Generate HTML summary using AI."""
    lang_name = "Bahasa Indonesia" if lang == "ind" else "English"

    if summary_type == "book":
        prompt = PROMPT_BOOK.format(lang_name=lang_name, title=title, text=text)
    else:
        prompt = PROMPT_ARTICLE.format(lang_name=lang_name, title=title, text=text)

    # Truncate if too long (keep first 80K chars)
    if len(text) > 80000:
        text = text[:80000] + "\n\n[TEXT TRUNCATED - too long for API]"
        prompt = prompt.replace(text[:80000], text)

    return call_openrouter(prompt, max_tokens=8000)


def save_html(html_content, title, summary_type, lang, category=None):
    """Save HTML to docs folder."""
    # Clean title for filename
    clean_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
    clean_title = clean_title.replace(" ", "_")

    lang_suffix = lang.upper()

    if summary_type == "book":
        # Default ke financial-institutions-management
        book_folder = category or "financial-institutions-management"
        folder = DOCS_DIR / "books" / book_folder
        filename = f"Ringkasan_{clean_title}_{lang_suffix}.html"
    else:
        # Artikel
        article_folder = category or clean_title.lower().replace("_", "-")
        folder = DOCS_DIR / "articles" / article_folder
        filename = f"Ringkasan_{clean_title}_{lang_suffix}.html"

    folder.mkdir(parents=True, exist_ok=True)
    filepath = folder / filename

    # Wrap in full HTML
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
    return filepath


def push_to_github():
    """Git add, commit, push."""
    try:
        subprocess.run(["git", "add", "docs/"], cwd=PROJECT_ROOT, check=True, timeout=30)
        subprocess.run(
            ["git", "commit", "-m", "Auto-summary: update via Telegram bot"],
            cwd=PROJECT_ROOT, check=True, timeout=30
        )
        subprocess.run(["git", "push"], cwd=PROJECT_ROOT, check=True, timeout=60)
        return True
    except Exception as e:
        print(f"[ERROR] git push failed: {e}")
        return False


def get_github_pages_url(filepath):
    """Convert local path to GitHub Pages URL."""
    try:
        rel = filepath.relative_to(DOCS_DIR)
        return f"https://heru2233.github.io/summary_academia/{rel.as_posix()}"
    except:
        return None


def process_pdf(chat_id, bot, pdf_data, title, summary_type, lang, category=None):
    """Full pipeline: PDF → extract → AI → save → push."""
    bot.send_chat_action(chat_id, "typing")

    # Save PDF to temp
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_data)
        tmp_path = tmp.name

    try:
        # Step 1: Extract text
        bot.send_message(chat_id, "📖 Mengekstrak teks dari PDF...")
        text = extract_text_from_pdf(tmp_path)
        if not text:
            bot.send_message(chat_id, "❌ Gagal mengekstrak teks dari PDF.")
            return

        word_count = len(text.split())
        bot.send_message(chat_id, f"✅ Teks ter-ekstrak: {word_count:,} kata")

        # Step 2: Generate summary
        langs_to_process = []
        if lang == "both":
            langs_to_process = ["eng", "ind"]
        else:
            langs_to_process = [lang]

        urls = []
        for l in langs_to_process:
            lang_name = "English" if l == "eng" else "Bahasa Indonesia"
            bot.send_chat_action(chat_id, "typing")
            bot.send_message(chat_id, f"🤖 Generating summary ({lang_name})... ini butuh beberapa menit, mohon tunggu...")

            html = generate_html(text, title, summary_type, l)
            if not html:
                bot.send_message(chat_id, f"❌ Gagal generate ringkasan {lang_name}")
                continue

            # Step 3: Save
            filepath = save_html(html, title, summary_type, l, category)
            url = get_github_pages_url(filepath)
            urls.append((l, url))
            bot.send_message(chat_id, f"✅ {lang_name} selesai: {filepath.name}")

        # Step 4: Push to GitHub
        if urls:
            bot.send_message(chat_id, "🚀 Pushing ke GitHub...")
            push_success = push_to_github()

            # Build response
            result_msg = "✅ <b>Selesai!</b>\n\n"
            for l, url in urls:
                lang_name = "English" if l == "eng" else "Bahasa Indonesia"
                result_msg += f"📖 {lang_name}: {url}\n\n"

            if push_success:
                result_msg += "🔗 GitHub Pages akan update dalam 1-2 menit."
            else:
                result_msg += "⚠️ Push gagal. Coba push manual: git push"

            bot.send_message(chat_id, result_msg)
        else:
            bot.send_message(chat_id, "❌ Tidak ada ringkasan yang berhasil dibuat.")

    finally:
        # Cleanup temp file
        try:
            os.unlink(tmp_path)
        except:
            pass


def main():
    """Main bot loop."""
    if not TELEGRAM_BOT_TOKEN:
        print("[ERROR] TELEGRAM_BOT_TOKEN not set in .env")
        sys.exit(1)

    if not OPENROUTER_API_KEY:
        print("[ERROR] OPENROUTER_API_KEY not set in .env")
        sys.exit(1)

    bot = TelegramBot(TELEGRAM_BOT_TOKEN)
    print(f"[INFO] Bot started. Model: {OPENROUTER_MODEL}")
    print("[INFO] Waiting for messages... (Ctrl+C to stop)")

    # Pending PDFs per user (waiting for title input)
    pending_pdfs = {}

    while True:
        try:
            updates = bot.get_updates()

            for update in updates:
                # Handle callback queries (inline keyboard buttons)
                if "callback_query" in update:
                    cq = update["callback_query"]
                    chat_id = cq["message"]["chat"]["id"]
                    data = cq["data"]

                    bot.answer_callback_query(cq["id"])

                    if data.startswith("type_"):
                        summary_type = data.replace("type_", "")
                        if chat_id in pending_pdfs:
                            pending_pdfs[chat_id]["type"] = summary_type
                            # Ask for language
                            bot.edit_message(
                                chat_id, cq["message"]["message_id"],
                                f"📄 Tipe: <b>{summary_type.upper()}</b>\n\n"
                                "Pilih bahasa ringkasan:",
                                reply_markup={
                                    "inline_keyboard": [
                                        [
                                            {"text": "🇬🇧 English", "callback_data": "lang_eng"},
                                            {"text": "🇮🇩 Indonesia", "callback_data": "lang_ind"}
                                        ],
                                        [{"text": "🌐 Keduanya", "callback_data": "lang_both"}]
                                    ]
                                }
                            )

                    elif data.startswith("lang_"):
                        lang = data.replace("lang_", "")
                        if chat_id in pending_pdfs:
                            pending_pdfs[chat_id]["lang"] = lang
                            # Ask for category
                            p = pending_pdfs[chat_id]
                            if p["type"] == "book":
                                bot.edit_message(
                                    chat_id, cq["message"]["message_id"],
                                    f"📚 <b>Buku</b> | Lang: <b>{lang.upper()}</b>\n\n"
                                    "Masukkan folder buku (atau ketik 'default' untuk financial-institutions-management):",
                                )
                                pending_pdfs[chat_id]["wait_for"] = "category"
                            else:
                                # For articles, ask for folder
                                bot.edit_message(
                                    chat_id, cq["message"]["message_id"],
                                    f"📄 <b>Artikel</b> | Lang: <b>{lang.upper()}</b>\n\n"
                                    "Masukkan folder artikel (atau ketik 'default'):"
                                )
                                pending_pdfs[chat_id]["wait_for"] = "category"

                # Handle text messages
                elif "message" in update and "text" in update["message"]:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    text = msg["text"]

                    # Check if waiting for input
                    if chat_id in pending_pdfs:
                        state = pending_pdfs[chat_id]

                        if state.get("wait_for") == "title":
                            state["title"] = text
                            state["wait_for"] = None

                            # Show confirmation and ask for type
                            bot.send_message(
                                chat_id,
                                f"📝 <b>Judul:</b> {text}\n\n"
                                "Pilih tipe ringkasan:",
                                reply_markup={
                                    "inline_keyboard": [
                                        [{"text": "📚 Buku", "callback_data": "type_book"}],
                                        [{"text": "📄 Artikel Jurnal", "callback_data": "type_article"}]
                                    ]
                                }
                            )

                        elif state.get("wait_for") == "category":
                            category = text if text.lower() != "default" else None
                            state["category"] = category
                            state["wait_for"] = None

                            # Start processing
                            bot.send_message(
                                chat_id,
                                "🚀 <b>Memulai proses...</b>\n\n"
                                f"Judul: {state['title']}\n"
                                f"Tipe: {state['type']}\n"
                                f"Bahasa: {state['lang']}\n\n"
                                "Mohon tunggu, ini akan memakan waktu beberapa menit..."
                            )

                            # Process in same thread (blocking but simple)
                            process_pdf(
                                chat_id, bot,
                                state["pdf_data"],
                                state["title"],
                                state["type"],
                                state["lang"],
                                state["category"]
                            )

                            # Cleanup
                            del pending_pdfs[chat_id]

                    # Handle /start and /help
                    elif text in ["/start", "/help"]:
                        bot.send_message(
                            chat_id,
                            "🤖 <b>Academic Summary Bot</b>\n\n"
                            "Kirim file PDF untuk diringkas otomatis.\n\n"
                            "<b>Cara pakai:</b>\n"
                            "1. Kirim file PDF\n"
                            "2. Ketik judul ringkasan\n"
                            "3. Pilih tipe (buku/artikel)\n"
                            "4. Pilih bahasa (ENG/IND/both)\n"
                            "5. Tunggu proses selesai\n\n"
                            "<b>Commands:</b>\n"
                            "/start - Mulai\n"
                            "/help - Bantuan\n"
                            "/cancel - Batalkan proses"
                        )

                    elif text == "/cancel":
                        if chat_id in pending_pdfs:
                            del pending_pdfs[chat_id]
                            bot.send_message(chat_id, "❌ Proses dibatalkan.")
                        else:
                            bot.send_message(chat_id, "Tidak ada proses yang sedang berjalan.")

                    # Handle /status
                    elif text == "/status":
                        bot.send_message(
                            chat_id,
                            f"📊 <b>Bot Status</b>\n\n"
                            f"Model: {OPENROUTER_MODEL}\n"
                            f"Docs dir: {DOCS_DIR}\n"
                            f"Pending: {len(pending_pdfs)} users"
                        )

                # Handle document (PDF)
                elif "message" in update and "document" in update["message"]:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    doc = msg["document"]

                    # Check if PDF
                    if not doc.get("file_name", "").lower().endswith(".pdf"):
                        bot.send_message(chat_id, "❌ Hanya file PDF yang didukung.")
                        continue

                    # Check file size (max 20MB)
                    if doc.get("file_size", 0) > 20 * 1024 * 1024:
                        bot.send_message(chat_id, "❌ File terlalu besar (maks 20MB).")
                        continue

                    bot.send_message(chat_id, f"📥 Menerima file: <b>{doc['file_name']}</b>")

                    # Download PDF
                    bot.send_chat_action(chat_id, "typing")
                    pdf_data = bot.get_file(doc["file_id"])
                    if not pdf_data:
                        bot.send_message(chat_id, "❌ Gagal download file.")
                        continue

                    # Store PDF and ask for title
                    pending_pdfs[chat_id] = {
                        "pdf_data": pdf_data,
                        "filename": doc["file_name"],
                        "wait_for": "title"
                    }

                    bot.send_message(
                        chat_id,
                        f"✅ File diterima: <b>{doc['file_name']}</b> ({len(pdf_data) / 1024:.1f} KB)\n\n"
                        "Ketik judul ringkasan (contoh: Why Are Financial Institutions Special?):"
                    )

        except KeyboardInterrupt:
            print("\n[INFO] Bot stopped.")
            break
        except Exception as e:
            print(f"[ERROR] {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
