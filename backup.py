# -*- coding: utf-8 -*-
"""Avtomatik yedəkləmə skripti — cron/Task Scheduler ilə işlədilmək üçün.

İstifadə:
    python backup.py

Nə edir:
  - Bazanın tutarlı surətini (SQLite backup API) + şəkilləri tək zip-ə yığır
  - backups/ qovluğuna timestamp ilə saxlayır
  - Yalnız son KEEP qədərini saxlayır, köhnələri silir

Linux cron nümunəsi (hər gecə 03:00):
    0 3 * * * cd /path/to/malbazari && /path/to/venv/bin/python backup.py
"""
import os
import glob
import uuid
import sqlite3
import zipfile
import tempfile
import urllib.request
from datetime import datetime
from config import DATABASE_PATH, UPLOAD_FOLDER, DATA_DIR

KEEP = 14  # neçə son yedək saxlanılsın

# Kənar (offsite) yedək üçün Telegram bot — env-dən. Boşdursa söndürülü.
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '').strip()


def send_to_telegram(zip_path):
    """Yedək zip-ini Telegram-a göndərir (offsite ehtiyat nüsxə).
    TELEGRAM_BOT_TOKEN və TELEGRAM_CHAT_ID təyin olunmayıbsa heç nə etmir.
    Əlavə kitabxana tələb etmir — yalnız standart urllib (multipart)."""
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        return False
    # Telegram bot sendDocument limiti ~50 MB
    if os.path.getsize(zip_path) > 49 * 1024 * 1024:
        print("Telegram yedək ötürüldü: fayl 50 MB-dan böyükdür.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    boundary = uuid.uuid4().hex
    fname = os.path.basename(zip_path)
    with open(zip_path, 'rb') as f:
        file_bytes = f.read()

    def part(name, value):
        return (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"'
                f'\r\n\r\n{value}\r\n').encode()

    body = part('chat_id', TELEGRAM_CHAT_ID)
    body += part('caption', f'MalBazari yedək — {fname}')
    body += (f'--{boundary}\r\nContent-Disposition: form-data; name="document"; '
             f'filename="{fname}"\r\nContent-Type: application/zip\r\n\r\n').encode()
    body += file_bytes + f'\r\n--{boundary}--\r\n'.encode()

    req = urllib.request.Request(url, data=body, method='POST')
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            ok = resp.status == 200
        print("Telegram-a yedək göndərildi." if ok else "Telegram yedək uğursuz.")
        return ok
    except Exception as e:
        print(f"Telegram yedək xətası: {e}")
        return False


def make_backup(send=True):
    # Yedəklər kalıcı diskdə saxlanılır (Railway: /data/backups)
    backups_dir = os.path.join(DATA_DIR, 'backups')
    os.makedirs(backups_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    zip_path = os.path.join(backups_dir, f'malbazari-backup-{ts}.zip')

    tmp_db = os.path.join(tempfile.gettempdir(), f'mb-{ts}.sqlite')
    src = sqlite3.connect(DATABASE_PATH)
    dst = sqlite3.connect(tmp_db)
    with dst:
        src.backup(dst)
    src.close(); dst.close()

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(tmp_db, 'malbazari.db')
        if os.path.isdir(UPLOAD_FOLDER):
            for root, _, files in os.walk(UPLOAD_FOLDER):
                for fn in files:
                    fp = os.path.join(root, fn)
                    z.write(fp, os.path.join('uploads', os.path.relpath(fp, UPLOAD_FOLDER)))
    os.remove(tmp_db)

    # Köhnələri təmizlə
    backups = sorted(glob.glob(os.path.join(backups_dir, 'malbazari-backup-*.zip')))
    for old in backups[:-KEEP]:
        try:
            os.remove(old)
        except OSError:
            pass

    print(f"Yedək yaradıldı: {zip_path}")
    # Kənar (offsite) yedək — konfiqurasiya olunubsa Telegram-a göndər
    if send:
        send_to_telegram(zip_path)
    return zip_path


if __name__ == '__main__':
    make_backup()
