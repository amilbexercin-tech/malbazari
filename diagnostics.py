"""Diaqnostika və data-itməsi qoruyucusu.

Məqsəd: production-da (Railway) bazanın və şəkillərin KALICI diskdə saxlandığını
yoxlamaq. Əgər kalıcı disk (Volume) qoşulmayıbsa, hər restart/deploy-da data
itir (admin 2FA sıfırlanır, elanlar yox olur). Bu modul həm startup-da loga
açıq xəbərdarlıq yazır, həm də /saglamliq səhifəsinə məlumat verir.
"""
import os
import json
import shutil
from datetime import datetime

from config import BASE_DIR, DATA_DIR, DATABASE_PATH, UPLOAD_FOLDER

# SECRET_KEY env-dən gəlir? Gəlmirsə hər deploy-da sessiyalar sıfırlanır.
SECRET_KEY_FROM_ENV = 'SECRET_KEY' in os.environ

# Railway konteynerə RAILWAY_* dəyişənləri qoyur — production-da olub-olmadığını bildirir.
IS_RAILWAY = any(k.startswith('RAILWAY_') for k in os.environ)

# DATA_DIR env-dən təyin edilməyibsə, defolt layihə qovluğudur (müvəqqəti disk!).
DATA_DIR_FROM_ENV = 'DATA_DIR' in os.environ

# Ən aydın təhlükə: production-dayıq, amma data layihə qovluğuna yazılır = müvəqqəti.
EPHEMERAL_RISK = IS_RAILWAY and os.path.abspath(DATA_DIR) == os.path.abspath(BASE_DIR)

_MARKER_PATH = os.path.join(DATA_DIR, '.persistence_marker.json')

# Startup anında markerin əvvəlcədən mövcud olub-olmaması — datanın əvvəlki
# işə salmadan sağ qaldığının EMPİRİK sübutu.
MARKER_EXISTED_AT_BOOT = os.path.exists(_MARKER_PATH)


def _read_marker():
    try:
        with open(_MARKER_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def record_boot():
    """Hər işə salınanda boot sayğacını artırır. Əgər data kalıcıdırsa,
    'first_boot' köhnə qalır və 'boot_count' restartlar arası artmağa davam edir.
    Əgər disk müvəqqəti olarsa, hər deploy-da sıfırlanır (first_boot=indi)."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data = _read_marker()
    if not data.get('first_boot'):
        data['first_boot'] = now
        data['boot_count'] = 1
    else:
        data['boot_count'] = int(data.get('boot_count', 0)) + 1
    data['last_boot'] = now
    try:
        with open(_MARKER_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception:
        pass
    return data


def _writable(path):
    """Qovluğun yazıla bilən olub-olmadığını faktiki yazıb-silərək yoxlayır."""
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, '.write_probe')
        with open(probe, 'w') as f:
            f.write('ok')
        os.remove(probe)
        return True
    except Exception:
        return False


def _disk_free_mb(path):
    try:
        usage = shutil.disk_usage(path)
        return round(usage.free / (1024 * 1024), 1)
    except Exception:
        return None


def collect_health():
    """Saytın saglamliq vəziyyətini lüğət kimi qaytarır (admin səhifəsi üçün)."""
    import database as db

    marker = _read_marker()
    db_exists = os.path.exists(DATABASE_PATH)
    db_size_kb = round(os.path.getsize(DATABASE_PATH) / 1024, 1) if db_exists else 0

    try:
        stats = db.get_stats()
        users = stats.get('total_users')
        listings = stats.get('active_listings')
    except Exception:
        users = listings = None

    # Yekun hökm: data kalıcıdırmı?
    if EPHEMERAL_RISK:
        verdict = 'danger'
        verdict_text = ('XEYR — Kalıcı disk (Volume) QOŞULMAYIB. '
                        'Hər deploy/restart-da bütün data (elanlar, istifadəçilər, '
                        'admin 2FA) SİLİNİR.')
    elif IS_RAILWAY and not MARKER_EXISTED_AT_BOOT:
        verdict = 'warning'
        verdict_text = ('EHTİYATLI OL — Bu işə salmada əvvəlki data tapılmadı. '
                        'Əgər bu hər deploy-da təkrarlanırsa, disk kalıcı deyil. '
                        'Aşağıdakı "İlk boot" və "Boot sayı" restartlar arası dəyişməməlidir.')
    else:
        verdict = 'ok'
        verdict_text = 'BƏLİ — Data kalıcı diskdə saxlanılır.'

    data_dir_writable = _writable(DATA_DIR)
    uploads_writable = _writable(UPLOAD_FOLDER)
    disk_free = _disk_free_mb(DATA_DIR)

    # ── Tapılan problemləri açıq dildə topla (hər biri: səviyyə, mətn, həll) ──
    problems = []
    if EPHEMERAL_RISK:
        problems.append({
            'level': 'danger',
            'text': 'Kalıcı disk (Volume) qoşulmayıb — data hər deploy/restart-da silinir.',
            'fix': 'Railway → Volume yarat (mount path = /data), sonra Variables-ə '
                   'DATA_DIR=/data əlavə et və yenidən deploy et.',
        })
    if IS_RAILWAY and not DATA_DIR_FROM_ENV:
        problems.append({
            'level': 'danger',
            'text': 'DATA_DIR dəyişəni təyin edilməyib (defolt /app işlənir — müvəqqəti).',
            'fix': 'Railway → Variables → DATA_DIR = /data əlavə et (Volume mount path ilə eyni).',
        })
    if not data_dir_writable:
        problems.append({
            'level': 'danger',
            'text': 'Data qovluğuna yazmaq mümkün deyil — baza yenilənə bilməz.',
            'fix': 'Volume mount path-ın düzgün olduğunu və icazələri yoxla.',
        })
    if not uploads_writable:
        problems.append({
            'level': 'danger',
            'text': 'Şəkil qovluğuna yazmaq mümkün deyil — şəkillər yüklənməyəcək.',
            'fix': 'DATA_DIR/static/uploads qovluğunun yazıla bilməsini yoxla.',
        })
    if IS_RAILWAY and not SECRET_KEY_FROM_ENV:
        problems.append({
            'level': 'warning',
            'text': 'SECRET_KEY dəyişəni təyin edilməyib — hər deploy-da bütün '
                    'istifadəçilər sistemdən çıxa bilər.',
            'fix': 'Railway → Variables → SECRET_KEY = (uzun təsadüfi mətn) əlavə et.',
        })
    if disk_free is not None and disk_free < 100:
        problems.append({
            'level': 'warning',
            'text': f'Disk sahəsi azalır ({disk_free} MB qalıb).',
            'fix': 'Köhnə şəkilləri/yedəkləri təmizlə və ya disk ölçüsünü artır.',
        })

    return {
        'verdict': verdict,
        'verdict_text': verdict_text,
        'problems': problems,
        'all_ok': len(problems) == 0,
        'is_railway': IS_RAILWAY,
        'data_dir': DATA_DIR,
        'data_dir_from_env': DATA_DIR_FROM_ENV,
        'secret_key_from_env': SECRET_KEY_FROM_ENV,
        'sentry_configured': bool(os.environ.get('SENTRY_DSN', '').strip()),
        'telegram_backup_configured': bool(os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
                                           and os.environ.get('TELEGRAM_CHAT_ID', '').strip()),
        'last_backup_date': db.get_setting('last_backup_date', '—'),
        'backup_hour_az': os.environ.get('BACKUP_HOUR', '23'),
        'health_ping_url': '/health',
        'base_dir': BASE_DIR,
        'database_path': DATABASE_PATH,
        'db_exists': db_exists,
        'db_size_kb': db_size_kb,
        'data_dir_writable': data_dir_writable,
        'uploads_writable': uploads_writable,
        'disk_free_mb': disk_free,
        'marker_existed_at_boot': MARKER_EXISTED_AT_BOOT,
        'first_boot': marker.get('first_boot', '—'),
        'last_boot': marker.get('last_boot', '—'),
        'boot_count': marker.get('boot_count', '—'),
        'users': users,
        'listings': listings,
        'checked_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }


def live_persistence_test():
    """Canlı sübut: bazaya və diskə real dəyər yazıb geri oxuyur.
    Datanın həqiqətən saxlandığını (yazılıb-oxunduğunu) yoxlayır."""
    import database as db

    stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    results = []
    ok = True

    # 1) Baza yazma/oxuma testi
    try:
        db.set_setting('_diag_probe', stamp)
        readback = db.get_setting('_diag_probe', '')
        if readback == stamp:
            results.append(('Bazaya yazma/oxuma', True, f'Dəyər saxlanıldı: {stamp}'))
        else:
            ok = False
            results.append(('Bazaya yazma/oxuma', False, 'Yazıldı, amma geri oxunan dəyər fərqlidir!'))
    except Exception as e:
        ok = False
        results.append(('Bazaya yazma/oxuma', False, f'Xəta: {e}'))

    # 2) Disk yazma/oxuma testi (DATA_DIR)
    try:
        probe = os.path.join(DATA_DIR, '.diag_probe.txt')
        with open(probe, 'w', encoding='utf-8') as f:
            f.write(stamp)
        with open(probe, 'r', encoding='utf-8') as f:
            disk_read = f.read()
        os.remove(probe)
        if disk_read == stamp:
            results.append(('Diskə yazma/oxuma', True, 'Fayl yazıldı və oxundu.'))
        else:
            ok = False
            results.append(('Diskə yazma/oxuma', False, 'Fayl oxunuşu uyğun gəlmədi!'))
    except Exception as e:
        ok = False
        results.append(('Diskə yazma/oxuma', False, f'Xəta: {e}'))

    return {'ok': ok, 'results': results, 'stamp': stamp}


def log_startup_diagnostics():
    """İşə salınanda deploy loglarına aydın diaqnostika yazır."""
    import sys

    def out(line):
        print(line, file=sys.stderr, flush=True)

    marker = record_boot()
    out('=' * 60)
    out('  HeyvanBazar — DATA DİAQNOSTİKASI')
    out('=' * 60)
    out(f'  Mühit         : {"Railway (production)" if IS_RAILWAY else "Lokal"}')
    out(f'  DATA_DIR      : {DATA_DIR}  (env-dən: {DATA_DIR_FROM_ENV})')
    out(f'  Baza faylı    : {DATABASE_PATH}')
    out(f'  Baza var?     : {os.path.exists(DATABASE_PATH)}')
    out(f'  Yazıla bilir? : {_writable(DATA_DIR)}')
    out(f'  İlk boot      : {marker.get("first_boot")}')
    out(f'  Boot sayı     : {marker.get("boot_count")}')
    out(f'  Marker vardı? : {MARKER_EXISTED_AT_BOOT} '
        '(bu işə salmadan əvvəl data mövcud idimi)')
    try:
        import database as db
        stats = db.get_stats()
        out(f'  İstifadəçi    : {stats.get("total_users")}')
        out(f'  Aktiv elan    : {stats.get("active_listings")}')
    except Exception as e:
        out(f'  Statistika alınmadı: {e}')

    if EPHEMERAL_RISK:
        out('-' * 60)
        out('  ⚠️  XƏBƏRDARLIQ: KALICI DİSK (VOLUME) QOŞULMAYIB!')
        out('  Data layihə qovluğuna yazılır — hər deploy/restart-da SİLİNİR.')
        out('  HƏLLİ: Railway-də Volume yarat (məs. mount path = /data),')
        out('  sonra Variables-ə DATA_DIR=/data əlavə et və yenidən deploy et.')
        out('-' * 60)
    out('=' * 60)
