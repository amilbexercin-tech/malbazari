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
import sqlite3
import zipfile
import tempfile
from datetime import datetime
from config import DATABASE_PATH, UPLOAD_FOLDER, BASE_DIR

KEEP = 14  # neçə son yedək saxlanılsın


def make_backup():
    backups_dir = os.path.join(BASE_DIR, 'backups')
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
    return zip_path


if __name__ == '__main__':
    make_backup()
