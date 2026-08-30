"""
Auto-Restart Wrapper for Academic Summary Bot
----------------------------------------------
Menjalankan bot dan otomatis restart jika crash.
Tunggu 5 detik sebelum restart untuk avoid infinite loop.

Cara pakai:
  python auto_restart.py
"""

import subprocess
import sys
import time
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/restart.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

BOT_SCRIPT = "telegram_bot.py"
RESTART_DELAY = 5  # detik sebelum restart
MAX_RESTARTS = 20  # max restart sebelum berhenti (safety)
RESTART_WINDOW = 3600  # 1 jam window untuk hitung restart


def run_bot():
    """Jalankan bot dengan monitoring."""
    restart_count = 0
    restart_times = []

    logger.info("=" * 50)
    logger.info("🚀 Auto-Restart Wrapper Started")
    logger.info(f"   Bot script: {BOT_SCRIPT}")
    logger.info(f"   Max restarts: {MAX_RESTARTS}")
    logger.info("=" * 50)

    while True:
        now = datetime.now()
        restart_times.append(now)

        # Bersihkan restart_times yang sudah lewat window
        cutoff = now.timestamp() - RESTART_WINDOW
        restart_times = [t for t in restart_times if t.timestamp() > cutoff]

        if len(restart_times) > MAX_RESTARTS:
            logger.error(
                f"❌ Terlalu banyak restart ({len(restart_times)}x dalam 1 jam). "
                f"Berhenti untuk safety. Restart manual jika diperlukan."
            )
            break

        restart_count += 1
        logger.info(f"🔄 Starting bot (restart #{restart_count})...")
        logger.info(f"   Restart tracking: {len(restart_times)}/{MAX_RESTARTS} in last hour")

        try:
            result = subprocess.run(
                [sys.executable, BOT_SCRIPT],
                cwd=".",
                timeout=None,
            )
            exit_code = result.returncode

            if exit_code == 0:
                logger.info("✅ Bot exited normally (exit code 0). Restarting...")
            else:
                logger.warning(f"⚠️ Bot crashed with exit code {exit_code}. Restarting in {RESTART_DELAY}s...")

        except KeyboardInterrupt:
            logger.info("🛑 Stopped by user (Ctrl+C).")
            break
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")

        logger.info(f"⏳ Waiting {RESTART_DELAY}s before restart...")
        time.sleep(RESTART_DELAY)


if __name__ == "__main__":
    run_bot()
