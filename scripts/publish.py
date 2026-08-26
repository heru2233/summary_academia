#!/usr/bin/env python3
"""
publish.py -- Script publish ringkasan HTML ke Telegraph dan/atau GitHub Pages

Cara pakai:
    # Publish ke Telegraph + kirim ke Telegram
    python publish.py -f ../summaries/buku-01 -t "Financial Institutions Management" --mode telegraph --telegram

    # Generate file untuk GitHub Pages
    python publish.py -f ../summaries/buku-01 -t "Financial Institutions Management" --mode github

    # Keduanya
    python publish.py -f ../summaries/buku-01 -t "Financial Institutions Management" --mode both --telegram

    # Dry run (preview tanpa publish)
    python publish.py -f ../summaries/buku-01 -t "Financial Institutions Management" --mode telegraph --dry-run
"""

import os
import sys
import time
import re
import argparse
from pathlib import Path
from datetime import datetime

# ============================================================
# IMPORTS (dengan penanganan dependency missing)
# ============================================================
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("[ERROR] beautifulsoup4 belum terinstall. Jalankan: pip install beautifulsoup4")
    sys.exit(1)

try:
    from telegraph import Telegraph
except ImportError:
    Telegraph = None  # Akan dicek saat mode telegraph dipilih

try:
    import requests
except ImportError:
    requests = None

# Import config
try:
    from config import (
        TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
        TELEGRAPH_AUTHOR_NAME, TELEGRAPH_SHORT_NAME,
        GITHUB_PAGES_BASE_URL, GITHUB_REPO_NAME,
        DEFAULT_TELEGRAM_BATCH_SIZE, DEFAULT_TELEGRAPH_DELAY,
        DEFAULT_TELEGRAPH_MAX_RETRIES, DEFAULT_AUTHOR_NAME
    )
except ImportError:
    print("[WARN]  config.py tidak ditemukan. Menggunakan default.")
    TELEGRAM_BOT_TOKEN = ""
    TELEGRAM_CHAT_ID = ""
    TELEGRAPH_AUTHOR_NAME = "Freebuff Summary"
    TELEGRAPH_SHORT_NAME = "BookBot"
    GITHUB_PAGES_BASE_URL = "https://YOUR_USERNAME.github.io/akademia-ringkas"
    GITHUB_REPO_NAME = "akademia-ringkas"
    DEFAULT_TELEGRAM_BATCH_SIZE = 50
    DEFAULT_TELEGRAPH_DELAY = 2
    DEFAULT_TELEGRAPH_MAX_RETRIES = 5
    DEFAULT_AUTHOR_NAME = "Freebuff Summary"


# ============================================================
# TELEGRAPH: SANITASI HTML
# ============================================================
def sanitize_html_for_telegraph(html_content: str) -> str:
    """
    Bersihkan HTML agar sesuai dengan whitelist tag Telegraph.
    WARNING: Tabel, style, script, MathJax akan HILANG.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Hapus elemen non-konten
    unwanted_tags = [
        "head", "script", "style", "meta", "link", "title",
        "button", "input", "form", "svg", "nav", "footer", "header"
    ]
    for tag in soup(unwanted_tags):
        tag.decompose()

    content_root = soup.body if soup.body else soup

    # 2. Standarisasi heading
    for tag in content_root.find_all("h1"):
        tag.name = "h3"
    for tag in content_root.find_all("h2"):
        tag.name = "h4"
    for tag in content_root.find_all(["h5", "h6"]):
        tag.name = "p"

    # 3. Whitelist tag resmi Telegraph
    ALLOWED_TAGS = {
        'a', 'aside', 'b', 'blockquote', 'br', 'code', 'em',
        'figcaption', 'figure', 'h3', 'h4', 'hr', 'i', 'iframe',
        'img', 'li', 'ol', 'p', 'pre', 's', 'strong', 'u', 'ul', 'video'
    }

    # 4. Ubah container umum ke <p>
    for tag in content_root.find_all(["div", "section", "article", "main", "table"]):
        tag.name = "p"

    # 5. Lepas tag tak dikenal tanpa menghapus teksnya
    for tag in content_root.find_all():
        if tag.name not in ALLOWED_TAGS:
            tag.unwrap()

    # 6. Bersihkan atribut
    for tag in content_root.find_all(True):
        allowed_attrs = {}
        if tag.name == 'a' and tag.has_attr('href'):
            allowed_attrs['href'] = tag['href']
        elif tag.name in ['img', 'video', 'iframe'] and tag.has_attr('src'):
            allowed_attrs['src'] = tag['src']
        tag.attrs = allowed_attrs

    inner_html = "".join(str(child) for child in content_root.contents).strip()
    return inner_html if inner_html else f"<p>{soup.get_text()}</p>"


# ============================================================
# TELEGRAPH: UPLOAD
# ============================================================
def init_telegraph():
    """Inisialisasi Telegraph API."""
    if Telegraph is None:
        print("[ERROR] library 'telegraph' belum terinstall. Jalankan: pip install telegraph")
        sys.exit(1)
    tg = Telegraph()
    tg.create_account(short_name=TELEGRAPH_SHORT_NAME, author_name=TELEGRAPH_AUTHOR_NAME)
    return tg


def upload_to_telegraph(tg, title: str, html_content: str,
                        author: str = DEFAULT_AUTHOR_NAME,
                        max_retries: int = DEFAULT_TELEGRAPH_MAX_RETRIES) -> dict | None:
    """Upload satu halaman ke Telegraph dengan retry flood control."""
    for attempt in range(max_retries):
        try:
            page = tg.create_page(
                title=title[:256],
                html_content=html_content,
                author_name=author
            )
            return page
        except Exception as e:
            err_msg = str(e)
            if "Flood control exceeded" in err_msg:
                match = re.search(r"Retry in (\d+) seconds", err_msg)
                wait_time = int(match.group(1)) + 2 if match else 10
                print(f"   [WAIT] Limit tercapai, menunggu {wait_time} detik...")
                time.sleep(wait_time)
            else:
                print(f"   [FAIL] Error: {e}")
                return None
    print(f"   [FAIL] Gagal setelah {max_retries} percobaan")
    return None


# ============================================================
# TELEGRAM: KIRIM MENU
# ============================================================
def send_telegram_menu(title: str, chapter_links: list[tuple[str, str]],
                       batch_size: int = DEFAULT_TELEGRAM_BATCH_SIZE):
    """Kirim menu inline keyboard ke Telegram."""
    if requests is None:
        print("[ERROR] library 'requests' belum terinstall. Jalankan: pip install requests")
        return

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[ERROR] TELEGRAM_BOT_TOKEN atau TELEGRAM_CHAT_ID belum diatur di config.py")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    for i in range(0, len(chapter_links), batch_size):
        batch = chapter_links[i:i + batch_size]
        inline_keyboard = [[{"text": f"> {chap_title}", "url": chap_url}]
                           for chap_title, chap_url in batch]

        part_info = f" (Bagian {i // batch_size + 1})" if len(chapter_links) > batch_size else ""
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"BOOK: <b>RINGKASAN{part_info}</b>\n<b>{title}</b>\n\n<i>Klik di bawah untuk membaca:</i>",
            "parse_mode": "HTML",
            "reply_markup": {"inline_keyboard": inline_keyboard}
        }

        response = requests.post(url, json=payload)
        if not response.ok:
            print(f"[Error] Gagal kirim menu: {response.text}")

    print("\n[DONE] Menu daftar isi berhasil dikirim ke Telegram!")


# ============================================================
# GITHUB PAGES: GENERATE INDEX
# ============================================================
def generate_github_index(html_files: list[dict], title: str, output_dir: str):
    """
    Generate file index.html untuk GitHub Pages.
    html_files: list of dict {filename, title, path}
    """
    today = datetime.now().strftime("%d %B %Y")

    links_html = ""
    for f in html_files:
        lang_flag = "[ID]" if "_IND" in f["filename"] else "[EN]"
        links_html += f'      <a href="{f["filename"]}" class="chapter-link">{lang_flag} {f["title"]}</a>\n'

    index_html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="css/responsive.css">
<title>{title} - Ringkasan</title>
<style>
  body {{
    font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
    max-width: 700px; margin: 40px auto; padding: 0 20px;
    color: #1a1a2e; background: #f8f9fa;
  }}
  h1 {{ text-align: center; color: #16213e; font-size: 1.5em; }}
  .meta {{ text-align: center; color: #666; font-size: 0.9em; margin-bottom: 30px; }}
  .chapter-link {{
    display: block; padding: 12px 16px; margin: 6px 0;
    background: #fff; border: 1px solid #dee2e6; border-radius: 8px;
    text-decoration: none; color: #1a1a2e; font-size: 1em;
    transition: all 0.2s;
  }}
  .chapter-link:hover {{ background: #e9ecef; border-color: #adb5bd; transform: translateX(4px); }}
  .footer {{ text-align: center; color: #999; font-size: 0.8em; margin-top: 40px; }}
</style>
</head>
<body>

<h1>BOOK: {title}</h1>
<p class="meta">Ringkasan belajar mandiri &mdash; Diperbarui: {today}</p>

{links_html}

<p class="footer">Disusun dengan bantuan AI &bull; Freebuff</p>

</body>
</html>"""

    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"[OK] Index page dibuat: {index_path}")


# ============================================================
# UTILS
# ============================================================
def extract_title_from_html(html_content: str, fallback: str) -> str:
    """Ekstrak judul dari tag <title> atau <h1> dalam HTML."""
    soup = BeautifulSoup(html_content, "html.parser")

    # Coba dari <title>
    if soup.title and soup.title.string:
        return soup.title.string.strip()

    # Coba dari <h1>
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)

    return fallback


def list_html_files(folder: str) -> list[str]:
    """List semua file .html di folder, sorted."""
    if not os.path.isdir(folder):
        print(f"[ERROR] Folder tidak ditemukan: {folder}")
        sys.exit(1)

    files = sorted([
        f for f in os.listdir(folder)
        if f.lower().endswith(".html") and not f.startswith("index")
    ])

    if not files:
        print(f"[WARN] Tidak ada file .html di: {folder}")
        sys.exit(1)

    return files


# ============================================================
# MODE: TELEGRAPH
# ============================================================
def publish_telegraph(folder: str, title: str, author: str,
                      send_telegram: bool, dry_run: bool,
                      delay: int = DEFAULT_TELEGRAPH_DELAY):
    """Publish semua HTML ke Telegraph, lalu kirim menu ke Telegram."""
    files = list_html_files(folder)
    print(f"FOLDER: Ditemukan {len(files)} file HTML di: {folder}\n")

    if dry_run:
        print(">> DRY RUN -- Tidak ada yang di-publish\n")
        for f in files:
            file_path = os.path.join(folder, f)
            with open(file_path, "r", encoding="utf-8") as fh:
                content = fh.read()
            file_title = extract_title_from_html(content, f.replace(".html", "").replace("_", " "))
            print(f"    - {f} -> \"{file_title}\"")
        print(f"\nTotal: {len(files)} file siap di-publish")
        return

    print(">> Mulai publish ke Telegraph...\n")
    tg = init_telegraph()
    chapter_links = []

    for i, file_name in enumerate(files, 1):
        file_path = os.path.join(folder, file_name)
        with open(file_path, "r", encoding="utf-8") as f:
            raw_html = f.read()

        file_title = extract_title_from_html(raw_html, file_name.replace(".html", "").replace("_", " "))
        clean_html = sanitize_html_for_telegraph(raw_html)

        print(f"  [{i}/{len(files)}] {file_title}...", end=" ")
        page = upload_to_telegraph(tg, file_title, clean_html, author=author)

        if page:
            telegraph_url = f"https://telegra.ph/{page['path']}"
            print(f"[OK] {telegraph_url}")
            chapter_links.append((file_title, telegraph_url))
        else:
            print("[FAIL] Gagal")

        if i < len(files):
            time.sleep(delay)

    print(f"\nRESULT: Hasil: {len(chapter_links)}/{len(files)} berhasil")

    if send_telegram and chapter_links:
        print("\n>> Mengirim menu ke Telegram...")
        send_telegram_menu(title, chapter_links)
    elif not send_telegram:
        print("\nTIP: Untuk kirim ke Telegram, tambahkan flag --telegram")


# ============================================================
# MODE: GITHUB PAGES
# ============================================================
def publish_github(folder: str, title: str, output_dir: str, dry_run: bool):
    """Siapkan file untuk GitHub Pages."""
    files = list_html_files(folder)
    print(f"FOLDER: Ditemukan {len(files)} file HTML di: {folder}\n")

    if dry_run:
        print(">> DRY RUN -- Tidak ada file yang dicopy\n")
        for f in files:
            print(f"    - {f}")
        print(f"\nTotal: {len(files)} file + index.html akan disalin ke: {output_dir}")
        return

    # Buat output directory
    os.makedirs(output_dir, exist_ok=True)

    # Copy HTML files
    html_entries = []
    for file_name in files:
        src = os.path.join(folder, file_name)
        dst = os.path.join(output_dir, file_name)

        with open(src, "r", encoding="utf-8") as f:
            content = f.read()

        # Update path relatif untuk CSS/JS lokal jika ada
        file_title = extract_title_from_html(content, file_name.replace(".html", "").replace("_", " "))

        with open(dst, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"  [OK] {file_name}")
        html_entries.append({
            "filename": file_name,
            "title": file_title,
            "path": dst
        })

    # Generate index
    generate_github_index(html_entries, title, output_dir)

    print(f"\n[DONE] {len(files)} file + index.html disalin ke: {output_dir}")
    print(f"🌐 Setelah push ke GitHub, akses di: {GITHUB_PAGES_BASE_URL}/")


# ============================================================
# MAIN
# ============================================================
def main():
    parser = argparse.ArgumentParser(
        description="Publish ringkasan HTML ke Telegraph dan/atau GitHub Pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh penggunaan:
  # Publish ke Telegraph + Telegram
  python publish.py -f ../summaries/buku-01 -t "Financial Institutions Management" --mode telegraph --telegram

  # Generate untuk GitHub Pages
  python publish.py -f ../summaries/buku-01 -t "Financial Institutions Management" --mode github -o ../docs/buku-01

  # Dry run (preview)
  python publish.py -f ../summaries/artikel-01 -t "Myers 1984" --mode telegraph --dry-run
        """
    )

    parser.add_argument("-f", "--folder", required=True,
                        help="Folder yang berisi file HTML ringkasan")
    parser.add_argument("-t", "--title", required=True,
                        help="Judul buku atau artikel")
    parser.add_argument("-m", "--mode", choices=["telegraph", "github", "both"],
                        default="telegraph",
                        help="Target publish: telegraph, github, atau both (default: telegraph)")
    parser.add_argument("--telegram", action="store_true",
                        help="Kirim menu inline keyboard ke Telegram (hanya untuk mode telegraph)")
    parser.add_argument("-o", "--output",
                        help="Output folder untuk mode github (default: ../docs/[nama-folder])")
    parser.add_argument("--author", default=DEFAULT_AUTHOR_NAME,
                        help=f"Nama author untuk Telegraph (default: {DEFAULT_AUTHOR_NAME})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview tanpa publish apapun")
    parser.add_argument("--delay", type=int, default=DEFAULT_TELEGRAPH_DELAY,
                        help=f"Jeda detik antar upload Telegraph (default: {DEFAULT_TELEGRAPH_DELAY})")

    args = parser.parse_args()

    # Validasi folder
    folder = os.path.abspath(args.folder)
    if not os.path.isdir(folder):
        print(f"❌ Folder tidak ditemukan: {folder}")
        sys.exit(1)

    print("=" * 60)
    print("BOOK: Academic Summary Publisher")
    print("=" * 60)
    print(f"  Folder  : {folder}")
    print(f"  Judul   : {args.title}")
    print(f"  Mode    : {args.mode}")
    print(f"  Telegram: {'Ya' if args.telegram else 'Tidak'}")
    print(f"  Dry Run : {'Ya' if args.dry_run else 'Tidak'}")
    print("=" * 60 + "\n")

    # Jalankan berdasarkan mode
    if args.mode in ("telegraph", "both"):
        print("-- MODE: TELEGRAPH --")
        publish_telegraph(folder, args.title, args.author,
                          args.telegram, args.dry_run, args.delay)
        print()

    if args.mode in ("github", "both"):
        print("-- MODE: GITHUB PAGES --")
        output_dir = args.output
        if not output_dir:
            # Default: ../docs/[nama-folder-terakhir]
            folder_name = os.path.basename(folder)
            output_dir = os.path.join(os.path.dirname(folder), "docs", folder_name)
        publish_github(folder, args.title, output_dir, args.dry_run)
        print()

    print("=" * 60)
    print("[DONE] Selesai!")
    print("=" * 60)


if __name__ == "__main__":
    main()
