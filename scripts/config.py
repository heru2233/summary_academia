"""
config.py — Konfigurasi proyek Academic Summary Pipeline

Semua token dan pengaturan disimpan di sini.
Bisa di-override via environment variable atau file .env
"""

import os
from pathlib import Path

# ============================================================
# LOAD .env FILE (jika ada)
# ============================================================
def load_dotenv(env_path: str = None):
    """Load variabel dari file .env (tanpa library tambahan)."""
    if env_path is None:
        env_path = Path(__file__).parent / ".env"
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and value:
                    os.environ.setdefault(key, value)

load_dotenv()

# ============================================================
# TELEGRAM
# ============================================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ============================================================
# TELEGRAPH
# ============================================================
TELEGRAPH_AUTHOR_NAME = "Freebuff Summary"
TELEGRAPH_SHORT_NAME = "BookBot"

# ============================================================
# GITHUB PAGES
# ============================================================
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "heru2233")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME", "summary_academia")
GITHUB_PAGES_BASE_URL = f"https://{GITHUB_USERNAME}.github.io/{GITHUB_REPO_NAME}"

# ============================================================
# DEFAULTS
# ============================================================
DEFAULT_TELEGRAM_BATCH_SIZE = 50   # Maks tombol inline per pesan
DEFAULT_TELEGRAPH_DELAY = 2        # Detik antar upload Telegraph
DEFAULT_TELEGRAPH_MAX_RETRIES = 5  # Max retry flood control
DEFAULT_AUTHOR_NAME = "Freebuff Summary"
