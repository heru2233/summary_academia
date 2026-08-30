"""
Setup Windows Task Scheduler for Auto-Start Bot
-------------------------------------------------
Jalankan sekali dengan admin privileges untuk daftarkan bot
otomatis start saat Windows login.

Cara pakai (Run as Administrator):
  python setup_task_scheduler.py --install
  python setup_task_scheduler.py --remove
"""

import subprocess
import sys
import os
import argparse

TASK_NAME = "AcademicSummaryBot"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_PATH = sys.executable
WRAPPER_SCRIPT = os.path.join(SCRIPT_DIR, "auto_restart.py")


def install_task():
    """Daftarkan task ke Windows Task Scheduler."""
    print(f"📦 Installing task: {TASK_NAME}")
    print(f"   Python: {PYTHON_PATH}")
    print(f"   Script: {WRAPPER_SCRIPT}")
    print()

    # Buat task via schtasks
    cmd = [
        "schtasks",
        "/create",
        "/tn", TASK_NAME,
        "/tr", f'"{PYTHON_PATH}" "{WRAPPER_SCRIPT}"',
        "/sc", "onlogon",        # Trigger saat user login
        "/rl", "highest",        # Run with highest privileges
        "/f",                    # Force overwrite jika sudah ada
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"✅ Task '{TASK_NAME}' berhasil didaftarkan!")
        print()
        print("📋 Detail:")
        print(f"   Trigger: Saat Windows login")
        print(f"   Script:  {WRAPPER_SCRIPT}")
        print(f"   Status:  Akan jalan otomatis saat login berikutnya")
        print()
        print("🚀 Untuk menjalankan sekarang:")
        print(f"   schtasks /run /tn {TASK_NAME}")
        print()
        print("🛑 Untuk menghapus:")
        print(f"   python setup_task_scheduler.py --remove")
    else:
        print(f"❌ Gagal daftar task!")
        print(f"   Error: {result.stderr}")
        print()
        print("💡 Pastikan jalankan script ini sebagai Administrator!")
        print("   Klik kanan → Run as administrator")


def remove_task():
    """Hapus task dari Windows Task Scheduler."""
    print(f"🗑️ Removing task: {TASK_NAME}")

    cmd = ["schtasks", "/delete", "/tn", TASK_NAME, "/f"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"✅ Task '{TASK_NAME}' berhasil dihapus!")
    else:
        print(f"❌ Gagal hapus task: {result.stderr}")


def show_status():
    """Tampilkan status task."""
    cmd = ["schtasks", "/query", "/tn", TASK_NAME, "/v", "/fo", "list"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"📋 Status task '{TASK_NAME}':")
        print(result.stdout)
    else:
        print(f"❌ Task '{TASK_NAME}' tidak ditemukan.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup Windows Task Scheduler for Bot")
    parser.add_argument("--install", action="store_true", help="Install task scheduler")
    parser.add_argument("--remove", action="store_true", help="Remove task scheduler")
    parser.add_argument("--status", action="store_true", help="Show task status")

    args = parser.parse_args()

    if args.install:
        install_task()
    elif args.remove:
        remove_task()
    elif args.status:
        show_status()
    else:
        parser.print_help()
        print()
        print("Contoh:")
        print("  python setup_task_scheduler.py --install   # Install")
        print("  python setup_task_scheduler.py --status    # Cek status")
        print("  python setup_task_scheduler.py --remove    # Hapus")
