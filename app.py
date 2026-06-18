import os
import io
import json
import time
import base64
import random
import secrets
import threading
import pyotp
import qrcode
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_from_directory, send_file, abort)
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from PIL import Image
import database as db
import i18n
import sms
from config import (SECRET_KEY, UPLOAD_FOLDER, MAX_CONTENT_LENGTH,
                    CATEGORIES, REGIONS, BASE_DIR, MAX_IMAGES,
                    SUBCATEGORY_EXAMPLES, DEBUG, PURPOSES, SORT_OPTIONS,
                    OTP_TTL_SECONDS, SMS_PROVIDER, REQUIRE_PHONE_VERIFICATION)

# ── Sentry (kod xətası monitorinqi) — SENTRY_DSN təyin olunubsa aktivləşir ──
SENTRY_DSN = os.environ.get('SENTRY_DSN', '').strip()
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        sentry_sdk.init(dsn=SENTRY_DSN,
                        integrations=[FlaskIntegration()],
                        traces_sample_rate=0.0,
                        send_default_pii=False)
    except Exception as _e:
        print(f'Sentry işə düşmədi: {_e}')

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    # Production-da HTTPS arxasında SESSION_COOKIE_SECURE=1 təyin et.
    # Lokal HTTP üçün defolt False (yoxsa sessiya kukisi göndərilmir).
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', '').lower() in ('1', 'true', 'yes'),
)

# CSRF qoruması — bütün POST formaları və AJAX sorğuları üçün token tələb olunur
csrf = CSRFProtect(app)

# Rate limiting — spam və brute-force qoruması
limiter = Limiter(get_remote_address, app=app,
                  default_limits=["600 per hour"],
                  storage_uri="memory://")

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# ─── Init ────────────────────────────────────────────────────────────────────

with app.app_context():
    db.init_db()
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    # Data-itməsi diaqnostikası: kalıcı diskin qoşulub-qoşulmadığını loga yaz.
    try:
        import diagnostics
        diagnostics.log_startup_diagnostics()
    except Exception as _e:
        print(f'Diaqnostika işə düşmədi: {_e}')

# ─── Helpers ─────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Zəhmət olmasa giriş edin.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Admin panelinə giriş üçün hesabınıza daxil olun.', 'warning')
            return redirect(url_for('login', next=request.url))
        if not session.get('is_admin'):
            flash('Bu səhifəyə giriş icazəniz yoxdur.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

def verified_required(f):
    """Telefonu təsdiqlənməmiş istifadəçini təsdiq səhifəsinə yönəldir.
    REQUIRE_PHONE_VERIFICATION söndürülübsə, sadəcə girişi tələb edir."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Zəhmət olmasa giriş edin.', 'warning')
            return redirect(url_for('login', next=request.url))
        if REQUIRE_PHONE_VERIFICATION:
            user = db.get_user_by_id(session['user_id'])
            if not user or not user['phone_verified']:
                flash('Davam etmək üçün telefon nömrənizi təsdiqləyin.', 'warning')
                return redirect(url_for('verify_phone'))
        return f(*args, **kwargs)
    return decorated

# ─── OTP köməkçiləri ───────────────────────────────────────────────────────────

def _start_otp(phone):
    """Yeni OTP yaradır, sessiyada saxlayır və SMS göndərir.
    dev rejimində kodu qaytarır ki, interfeysdə göstərilsin."""
    code = f"{random.randint(0, 999999):06d}"
    session['otp_code'] = code
    session['otp_phone'] = phone
    session['otp_expires'] = time.time() + OTP_TTL_SECONDS
    sms.send_otp(phone, code)
    return code

# ─── 2FA (TOTP) köməkçiləri ────────────────────────────────────────────────────

def _qr_data_uri(text):
    """Mətndən QR kod yaradıb data-URI (base64 PNG) qaytarır — səhifəyə yerləşdirmək üçün."""
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()

def _finalize_login(user):
    """2FA-dan sonra sessiyanı tam giriş halına gətirir."""
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['is_admin'] = bool(user['is_admin'])
    for k in ('pending_2fa_uid', 'totp_setup_secret'):
        session.pop(k, None)

# PIL formatından etibarlı uzantıya xəritə — uzantı istifadəçinin adından deyil,
# faylın əsl məzmunundan götürülür.
PIL_FORMAT_EXT = {'JPEG': 'jpg', 'PNG': 'png', 'GIF': 'gif', 'WEBP': 'webp'}


def save_images(files):
    saved = []
    for f in files[:MAX_IMAGES]:
        if not (f and f.filename):
            continue
        try:
            # 1) Bütövlüyü yoxla — zədəli/saxta fayl burada xəta verir
            f.stream.seek(0)
            with Image.open(f.stream) as probe:
                probe.verify()
            # verify() şəkli "istehlak edir" — yenidən aç
            f.stream.seek(0)
            img = Image.open(f.stream)
            # 2) Əsl formata güvən (uzantıya yox)
            ext = PIL_FORMAT_EXT.get(img.format)
            if not ext:
                continue  # icazə verilməyən və ya naməlum format — ötür
            # 3) Ölçünü kiçilt və YENİDƏN KODLA (gizli zərərli məzmunu təmizləyir)
            img.thumbnail((1200, 900))
            fname = secrets.token_hex(16) + '.' + ext
            path = os.path.join(UPLOAD_FOLDER, fname)
            if ext == 'jpg':
                img = img.convert('RGB')
            img.save(path, optimize=True, quality=85)
            saved.append(fname)
        except Exception:
            # Şəkil deyil və ya emal edilə bilmədi — sakitcə ötür, fayl yazılmır
            continue
    return saved

def listing_to_dict(row):
    d = dict(row)
    try:
        d['images'] = json.loads(d.get('images') or '[]')
    except Exception:
        d['images'] = []
    return d

# ─── Background Maintenance (throttled) ───────────────────────────────────────
# Vaxtı keçmiş elanların silinməsi ƏVVƏL hər sorğuda işləyirdi (yavaşladırdı).
# İndi ən çox MAINTENANCE_INTERVAL saniyədə bir dəfə işləyir.

MAINTENANCE_INTERVAL = 600     # 10 dəqiqə (köhnə elanların təmizlənməsi)
AUTO_BACKUP = os.environ.get('AUTO_BACKUP', '1').lower() in ('1', 'true', 'yes')
# Gündəlik yedək saatı — Azərbaycan vaxtı (UTC+4). Defolt 23:00 (gün sonu).
BACKUP_HOUR_AZ = int(os.environ.get('BACKUP_HOUR', '23'))
_AZ_TZ = timezone(timedelta(hours=4))
_maintenance_lock = threading.Lock()
_last_maintenance = 0.0


def _az_now():
    """Azərbaycan yerli vaxtı (UTC+4), server UTC olsa belə düzgün işləyir."""
    return datetime.now(timezone.utc).astimezone(_AZ_TZ)


def _safe_backup():
    """Yedəyi arxa planda yaradır — sorğunu bloklamır, xəta saytı çökdürmür."""
    try:
        import backup
        backup.make_backup()
    except Exception as e:
        app.logger.error("Avtomatik yedək xətası: %s", e)


def run_maintenance():
    """Vaxtı keçmiş elanları sil + gündə BİR DƏFƏ (gün sonunda) avtomatik yedək.
    Yedək bazadakı tarixlə idarə olunur — restart/worker fərq etmir, təkrarlanmır."""
    global _last_maintenance
    now = time.monotonic()

    # Gündəlik yedək — yalnız AZ vaxtı ilə gün sonundan sonra, gündə bir dəfə.
    if AUTO_BACKUP:
        az = _az_now()
        if az.hour >= BACKUP_HOUR_AZ:
            today = az.strftime('%Y-%m-%d')
            try:
                if db.get_setting('last_backup_date', '') != today and db.claim_backup_date(today):
                    threading.Thread(target=_safe_backup, daemon=True).start()
            except Exception as e:
                app.logger.error("Yedək planlayıcı xətası: %s", e)

    if now - _last_maintenance < MAINTENANCE_INTERVAL:
        return
    if not _maintenance_lock.acquire(blocking=False):
        return
    try:
        _last_maintenance = now
        expired_images = db.expire_listings()
        for img in expired_images:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, img))
            except OSError:
                pass
    finally:
        _maintenance_lock.release()


# Əsas (canonical) domen — təyin olunsa, bütün digər hostlar buraya 301 yönləndirilir.
# Domen alınmayana qədər boş qalır → heç bir yönləndirmə olmur (sayt eyni işləyir).
# Domen bağlananda Railway Variables-ə əlavə et: CANONICAL_HOST=heyvanbazar.az
CANONICAL_HOST = os.environ.get('CANONICAL_HOST', '').strip().lower()


@app.before_request
def _canonical_host_redirect():
    # /health istisna — UptimeRobot/Railway istənilən hostda yoxlaya bilsin.
    if not CANONICAL_HOST or request.path == '/health':
        return
    host = (request.host or '').split(':')[0].lower()
    if host and host != CANONICAL_HOST:
        path = request.full_path
        if path.endswith('?'):
            path = path[:-1]
        return redirect(f'https://{CANONICAL_HOST}{path}', code=301)


@app.before_request
def _maintenance_before_request():
    run_maintenance()


@app.context_processor
def inject_globals():
    lang = i18n.normalize_lang(session.get('lang', i18n.DEFAULT_LANG))
    return {
        'categories': CATEGORIES,
        'regions': REGIONS,
        'purposes': PURPOSES,
        'sort_options': SORT_OPTIONS,
        'subcategory_examples': SUBCATEGORY_EXAMPLES,
        'site_name': db.get_setting('site_name', 'HeyvanBazar'),
        'current_user': db.get_user_by_id(session['user_id']) if 'user_id' in session else None,
        'now': datetime.now(),
        'db_setting': db.get_setting,
        'stats': db.get_stats() if 'user_id' in session and session.get('is_admin') else None,
        'unread_messages': db.count_unread(session['user_id']) if 'user_id' in session else 0,
        'favorite_ids': db.get_favorite_ids(session['user_id']) if 'user_id' in session else set(),
        'lang': lang,
        'languages': i18n.LANGUAGES,
        't': lambda key: i18n.t(key, lang),
    }

# ─── Language ────────────────────────────────────────────────────────────────

@app.route('/dil/<lang>')
def set_language(lang):
    session['lang'] = i18n.normalize_lang(lang)
    nxt = request.referrer
    if nxt and nxt.startswith(request.host_url):
        return redirect(nxt)
    return redirect(url_for('index'))

# ─── Public Routes ───────────────────────────────────────────────────────────

def _parse_filters():
    """Axtarış/kateqoriya filtrlərini request.args-dan oxu."""
    def argnum(name):
        v = (request.args.get(name) or '').strip()
        try:
            return float(v) if v != '' else None
        except ValueError:
            return None
    vacc = request.args.get('vaccinated', '')
    sort = request.args.get('sort', 'new')
    if sort not in SORT_OPTIONS:
        sort = 'new'
    purpose = (request.args.get('purpose') or '').strip()
    return {
        'price_min': argnum('price_min'),
        'price_max': argnum('price_max'),
        'weight_min': argnum('weight_min'),
        'weight_max': argnum('weight_max'),
        'purpose': purpose if purpose in PURPOSES else None,
        'vaccinated': 1 if vacc == '1' else (0 if vacc == '0' else None),
        'breed': (request.args.get('breed') or '').strip() or None,
        'sort': sort,
    }

@app.route('/health')
@limiter.exempt
@csrf.exempt
def health_ping():
    """Public liveness yoxlaması — UptimeRobot kimi monitorinq xidmətləri üçün.
    Baza əlçatandırsa 200 'ok', deyilsə 500 qaytarır."""
    try:
        db.get_setting('site_name')
        return jsonify(status='ok'), 200
    except Exception:
        return jsonify(status='error'), 500

@app.route('/')
def index():
    recent_rows, _ = db.get_listings(page=1, per_page=12)
    recent = [listing_to_dict(l) for l in recent_rows]

    cat_counts = {}
    for slug in CATEGORIES:
        rows, total = db.get_listings(category=slug, per_page=1)
        cat_counts[slug] = total
    stats = db.get_stats()
    return render_template('index.html', recent=recent,
                           cat_counts=cat_counts, stats=stats)

@app.route('/kateqoriya/<slug>')
def category(slug):
    if slug not in CATEGORIES:
        abort(404)
    cat = CATEGORIES[slug]
    sub = request.args.get('sub', '')
    region = request.args.get('region', '')
    page = int(request.args.get('page', 1))
    filters = _parse_filters()

    rows, total = db.get_listings(category=slug,
                                  subcategory=sub if sub else None,
                                  region=region if region else None,
                                  page=page, per_page=20, **filters)
    listings = [listing_to_dict(l) for l in rows]
    pages = (total + 19) // 20
    return render_template('category.html', cat=cat, slug=slug,
                           listings=listings, total=total,
                           page=page, pages=pages, sub=sub, region=region,
                           f=request.args, sort=filters['sort'])

@app.route('/elan/<int:lid>')
def listing_detail(lid):
    row = db.get_listing(lid)
    if not row:
        abort(404)
    db.increment_views(lid)
    listing = listing_to_dict(row)
    cat = CATEGORIES.get(listing['category'], {})
    return render_template('listing.html', listing=listing, cat=cat)

@app.route('/haqqinda')
def about():
    stats = db.get_stats()
    return render_template('about.html', stats=stats)

@app.route('/axtar')
def search():
    q = request.args.get('q', '').strip()
    category = request.args.get('cat', '')
    region = request.args.get('region', '')
    page = int(request.args.get('page', 1))

    if not q:
        return redirect(url_for('index'))

    filters = _parse_filters()
    rows, total = db.get_listings(
        category=category if category else None,
        region=region if region else None,
        search=q, page=page, per_page=20, **filters)
    listings = [listing_to_dict(l) for l in rows]
    pages = (total + 19) // 20
    return render_template('search.html', listings=listings, total=total,
                           q=q, page=page, pages=pages, region=region, cat=category,
                           f=request.args, sort=filters['sort'])

# ─── Auth Routes ─────────────────────────────────────────────────────────────

@app.route('/qeydiyyat', methods=['GET', 'POST'])
@limiter.limit("5 per hour", methods=['POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        if not all([username, phone, password]):
            flash('Bütün sahələri doldurun.', 'danger')
            return render_template('register.html')
        if len(password) < 6:
            flash('Şifrə ən az 6 simvol olmalıdır.', 'danger')
            return render_template('register.html')
        if password != confirm:
            flash('Şifrələr uyğun gəlmir.', 'danger')
            return render_template('register.html')
        uid = db.create_user(username, phone, generate_password_hash(password))
        if uid is None:
            flash('Bu nömrə artıq qeydiyyatdan keçib.', 'danger')
            return render_template('register.html')
        session['user_id'] = uid
        session['username'] = username
        session['is_admin'] = False
        if REQUIRE_PHONE_VERIFICATION:
            # Telefon təsdiqi üçün OTP başlat
            _start_otp(phone)
            flash(f'Xoş gəldiniz, {username}! Telefon nömrənizi təsdiqləyin.', 'success')
            return redirect(url_for('verify_phone'))
        # Təsdiq söndürülüb — birbaşa qəbul et
        db.set_phone_verified(uid)
        flash(f'Xoş gəldiniz, {username}!', 'success')
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/telefon-tesdiq', methods=['GET', 'POST'])
@login_required
def verify_phone():
    if not REQUIRE_PHONE_VERIFICATION:
        return redirect(url_for('index'))
    user = db.get_user_by_id(session['user_id'])
    if user['phone_verified']:
        return redirect(url_for('index'))
    if request.method == 'POST':
        entered = request.form.get('code', '').strip()
        code = session.get('otp_code')
        expires = session.get('otp_expires', 0)
        if not code or time.time() > expires:
            flash('Kodun vaxtı bitib. Yeni kod istəyin.', 'warning')
        elif entered == code:
            db.set_phone_verified(user['id'])
            for k in ('otp_code', 'otp_phone', 'otp_expires'):
                session.pop(k, None)
            flash('Telefon nömrəniz təsdiqləndi! ✅', 'success')
            return redirect(url_for('index'))
        else:
            flash('Kod yanlışdır.', 'danger')
    # dev rejimində kodu interfeysdə göstər (real SMS yoxdur)
    dev_code = session.get('otp_code') if SMS_PROVIDER == 'dev' else None
    return render_template('verify.html', phone=user['phone'], dev_code=dev_code)

@app.route('/otp-yenile', methods=['POST'])
@login_required
@limiter.limit("3 per 5 minutes")
def resend_otp():
    user = db.get_user_by_id(session['user_id'])
    if not user['phone_verified']:
        _start_otp(user['phone'])
        flash('Yeni təsdiq kodu göndərildi.', 'info')
    return redirect(url_for('verify_phone'))

@app.route('/giris', methods=['GET', 'POST'])
@limiter.limit("10 per 5 minutes", methods=['POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        user = db.get_user_by_phone(phone)
        if user and check_password_hash(user['password_hash'], password):
            nxt = request.args.get('next')
            # Adminlər üçün məcburi ikili doğrulama (2FA)
            if user['is_admin']:
                session.clear()
                session['pending_2fa_uid'] = user['id']
                if nxt and nxt.startswith('/'):
                    session['post_login_next'] = nxt
                if user['totp_secret']:
                    return redirect(url_for('two_factor'))
                return redirect(url_for('two_factor_setup'))
            # Adi istifadəçi — birbaşa giriş
            _finalize_login(user)
            flash(f'Xoş gəldiniz, {user["username"]}!', 'success')
            if nxt and nxt.startswith('/'):
                return redirect(nxt)
            return redirect(url_for('index'))
        flash('Nömrə və ya şifrə yanlışdır.', 'danger')
    return render_template('login.html')

@app.route('/2fa', methods=['GET', 'POST'])
@limiter.limit("10 per 5 minutes", methods=['POST'])
def two_factor():
    uid = session.get('pending_2fa_uid')
    if not uid:
        return redirect(url_for('login'))
    user = db.get_user_by_id(uid)
    if not user or not user['totp_secret']:
        return redirect(url_for('two_factor_setup'))
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        ok = pyotp.TOTP(user['totp_secret']).verify(code, valid_window=1)
        # TOTP tutmadısa, bərpa kodunu yoxla
        if not ok and user['backup_codes']:
            try:
                codes = json.loads(user['backup_codes'])
            except Exception:
                codes = []
            for i, h in enumerate(codes):
                if check_password_hash(h, code):
                    codes.pop(i)
                    db.set_backup_codes(user['id'], json.dumps(codes))
                    ok = True
                    flash('Bərpa kodu istifadə olundu. Authenticator-i yenidən qurmağı tövsiyə edirik.', 'warning')
                    break
        if ok:
            nxt = session.get('post_login_next')
            _finalize_login(user)
            session.pop('post_login_next', None)
            flash(f'Xoş gəldiniz, {user["username"]}!', 'success')
            return redirect(nxt if nxt and nxt.startswith('/') else url_for('admin_dashboard'))
        flash('Kod yanlışdır.', 'danger')
    return render_template('two_factor.html')

@app.route('/2fa-qur', methods=['GET', 'POST'])
@limiter.limit("10 per 5 minutes", methods=['POST'])
def two_factor_setup():
    uid = session.get('pending_2fa_uid')
    if not uid:
        return redirect(url_for('login'))
    user = db.get_user_by_id(uid)
    if not user:
        return redirect(url_for('login'))
    if user['totp_secret']:
        return redirect(url_for('two_factor'))
    # Sirr təsdiqlənənə qədər sessiyada saxlanılır
    secret = session.get('totp_setup_secret')
    if not secret:
        secret = pyotp.random_base32()
        session['totp_setup_secret'] = secret
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if pyotp.TOTP(secret).verify(code, valid_window=1):
            db.set_totp_secret(user['id'], secret)
            # Birdəfəlik bərpa kodları yarat (telefon itəndə giriş üçün)
            codes = [secrets.token_hex(4) for _ in range(8)]
            db.set_backup_codes(user['id'], json.dumps(
                [generate_password_hash(c) for c in codes]))
            nxt = session.get('post_login_next')
            _finalize_login(user)
            session.pop('post_login_next', None)
            session['show_backup_codes'] = codes
            session['backup_next'] = nxt if nxt and nxt.startswith('/') else url_for('admin_dashboard')
            flash('İkili doğrulama aktivləşdi! ✅', 'success')
            return redirect(url_for('backup_codes_view'))
        flash('Kod yanlışdır, yenidən cəhd edin.', 'danger')
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user['phone'],
                                                   issuer_name='HeyvanBazar')
    return render_template('two_factor_setup.html', qr=_qr_data_uri(uri), secret=secret)

@app.route('/2fa-berpa-kodlari')
@admin_required
def backup_codes_view():
    codes = session.pop('show_backup_codes', None)
    nxt = session.pop('backup_next', None) or url_for('admin_dashboard')
    if not codes:
        return redirect(url_for('admin_dashboard'))
    return render_template('backup_codes.html', codes=codes, nxt=nxt)

@app.route('/2fa-berpa-yenile', methods=['POST'])
@admin_required
def regenerate_backup_codes():
    """Admin üçün yeni birdəfəlik bərpa kodları yaradır (köhnələri ləğv edir)."""
    codes = [secrets.token_hex(4) for _ in range(8)]
    db.set_backup_codes(session['user_id'], json.dumps(
        [generate_password_hash(c) for c in codes]))
    session['show_backup_codes'] = codes
    session['backup_next'] = url_for('account_settings')
    return redirect(url_for('backup_codes_view'))

# ─── Parol bərpası ──────────────────────────────────────────────────────────────

@app.route('/sifre-unutdum', methods=['GET', 'POST'])
@limiter.limit("5 per 15 minutes", methods=['POST'])
def forgot_password():
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        user = db.get_user_by_phone(phone)
        if user:
            _start_otp(phone)
            session['reset_uid'] = user['id']
            session['reset_phone'] = phone
        # Nömrənin mövcudluğunu açıqlamırıq
        flash('Əgər bu nömrə qeydiyyatdadırsa, təsdiq kodu göndərildi.', 'info')
        return redirect(url_for('reset_password'))
    return render_template('forgot.html')

@app.route('/sifre-sifirla', methods=['GET', 'POST'])
@limiter.limit("10 per 15 minutes", methods=['POST'])
def reset_password():
    uid = session.get('reset_uid')
    if not uid:
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        entered = request.form.get('code', '').strip()
        pw = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        code = session.get('otp_code')
        expires = session.get('otp_expires', 0)
        if not code or time.time() > expires:
            flash('Kodun vaxtı bitib. Yenidən cəhd edin.', 'warning')
            return redirect(url_for('forgot_password'))
        if entered != code:
            flash('Kod yanlışdır.', 'danger')
        elif len(pw) < 6:
            flash('Şifrə ən az 6 simvol olmalıdır.', 'danger')
        elif pw != confirm:
            flash('Şifrələr uyğun gəlmir.', 'danger')
        else:
            db.update_password(uid, generate_password_hash(pw))
            for k in ('otp_code', 'otp_phone', 'otp_expires', 'reset_uid', 'reset_phone'):
                session.pop(k, None)
            flash('Şifrəniz yeniləndi. İndi daxil ola bilərsiniz.', 'success')
            return redirect(url_for('login'))
    dev_code = session.get('otp_code') if SMS_PROVIDER == 'dev' else None
    return render_template('reset.html', phone=session.get('reset_phone', ''), dev_code=dev_code)

@app.route('/cixis')
def logout():
    session.clear()
    flash('Hesabdan çıxış edildi.', 'info')
    return redirect(url_for('index'))

@app.route('/profil')
@login_required
def profile():
    uid = session['user_id']
    user = db.get_user_by_id(uid)
    rows, total = db.get_listings(user_id=uid, per_page=50)
    listings = [listing_to_dict(l) for l in rows]
    return render_template('profile.html', user=user, listings=listings, total=total)

@app.route('/hesab-ayarlari', methods=['GET', 'POST'])
@login_required
def account_settings():
    uid = session['user_id']
    user = db.get_user_by_id(uid)
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'name':
            username = request.form.get('username', '').strip()[:50]
            if username:
                db.update_username(uid, username)
                session['username'] = username
                flash('Adınız yeniləndi.', 'success')
            else:
                flash('Ad boş ola bilməz.', 'danger')
        elif action == 'password':
            current = request.form.get('current', '')
            new = request.form.get('password', '')
            confirm = request.form.get('confirm', '')
            if not check_password_hash(user['password_hash'], current):
                flash('Cari şifrə yanlışdır.', 'danger')
            elif len(new) < 6:
                flash('Yeni şifrə ən az 6 simvol olmalıdır.', 'danger')
            elif new != confirm:
                flash('Yeni şifrələr uyğun gəlmir.', 'danger')
            else:
                db.update_password(uid, generate_password_hash(new))
                flash('Şifrəniz dəyişdirildi.', 'success')
        return redirect(url_for('account_settings'))
    return render_template('account.html', user=user)

# ─── Listing CRUD ────────────────────────────────────────────────────────────

def _form_num(name):
    """Formadan ədəd oxu — boş və ya yanlışdırsa None."""
    v = (request.form.get(name) or '').strip()
    try:
        return float(v) if v != '' else None
    except ValueError:
        return None

def _extra_listing_fields():
    """Heyvana xas + xəritə sahələri (create və edit üçün ortaq)."""
    vacc = request.form.get('vaccinated', '')
    purpose = (request.form.get('purpose') or '').strip()
    return {
        'weight_kg': _form_num('weight_kg'),
        'purpose': purpose if purpose in PURPOSES else None,
        'breed': (request.form.get('breed') or '').strip()[:100] or None,
        'age': (request.form.get('age') or '').strip()[:50] or None,
        'vaccinated': 1 if vacc == '1' else (0 if vacc == '0' else None),
        'lat': _form_num('lat'),
        'lng': _form_num('lng'),
    }

@app.route('/elan-yarat', methods=['GET', 'POST'])
@verified_required
@limiter.limit("20 per hour", methods=['POST'])
def create_listing():
    if request.method == 'POST':
        files = request.files.getlist('images')
        saved_images = save_images(files)
        data = {
            'user_id': session['user_id'],
            'category': request.form.get('category', ''),
            'subcategory': request.form.get('subcategory', ''),
            'title': request.form.get('title', '').strip()[:200],
            'description': request.form.get('description', '').strip()[:2000],
            'price': request.form.get('price') or None,
            'weight': request.form.get('weight', '').strip(),
            'quantity': int(request.form.get('quantity', 1) or 1),
            'region': request.form.get('region', ''),
            'phone': request.form.get('phone', '').strip()[:20],
            'images': json.dumps(saved_images),
        }
        data.update(_extra_listing_fields())
        if not data['category'] or not data['subcategory'] or not data['title']:
            flash('Kateqoriya, alt kateqoriya və başlıq mütləqdir.', 'danger')
            return render_template('create.html')
        lid = db.create_listing(data)
        flash('Elanınız uğurla əlavə edildi!', 'success')
        return redirect(url_for('listing_detail', lid=lid))
    return render_template('create.html')

@app.route('/elan-duzenle/<int:lid>', methods=['GET', 'POST'])
@login_required
def edit_listing(lid):
    row = db.get_listing(lid)
    if not row:
        abort(404)
    listing = listing_to_dict(row)
    if listing['user_id'] != session['user_id'] and not session.get('is_admin'):
        abort(403)
    if request.method == 'POST':
        files = request.files.getlist('images')
        existing = json.loads(request.form.get('existing_images', '[]'))
        new_images = save_images(files)
        all_images = (existing + new_images)[:MAX_IMAGES]
        data = {
            'category': request.form.get('category', ''),
            'subcategory': request.form.get('subcategory', ''),
            'title': request.form.get('title', '').strip()[:200],
            'description': request.form.get('description', '').strip()[:2000],
            'price': request.form.get('price') or None,
            'weight': request.form.get('weight', '').strip(),
            'quantity': int(request.form.get('quantity', 1) or 1),
            'region': request.form.get('region', ''),
            'phone': request.form.get('phone', '').strip()[:20],
            'images': json.dumps(all_images),
        }
        data.update(_extra_listing_fields())
        db.update_listing(lid, data)
        flash('Elan yeniləndi.', 'success')
        return redirect(url_for('listing_detail', lid=lid))
    return render_template('edit.html', listing=listing)

@app.route('/elan-sil/<int:lid>', methods=['POST'])
@login_required
def delete_listing(lid):
    row = db.get_listing(lid)
    if not row:
        abort(404)
    if row['user_id'] != session['user_id'] and not session.get('is_admin'):
        abort(403)
    db.delete_listing(lid)
    flash('Elan silindi.', 'info')
    return redirect(url_for('profile'))

# ─── Messaging ────────────────────────────────────────────────────────────────

@app.route('/mesajlar')
@login_required
def messages_inbox():
    convos = db.get_conversations(session['user_id'])
    return render_template('messages.html', conversations=[dict(c) for c in convos])


@app.route('/mesajlar/<int:lid>/<int:other_id>')
@login_required
def conversation(lid, other_id):
    uid = session['user_id']
    if other_id == uid:
        abort(400)
    listing = db.get_listing(lid)
    other = db.get_user_by_id(other_id)
    if not other:
        abort(404)
    db.mark_messages_read(uid, other_id, lid)
    msgs = db.get_conversation(uid, other_id, lid)
    return render_template('conversation.html',
                           messages=[dict(m) for m in msgs],
                           listing=dict(listing) if listing else None,
                           other=dict(other), lid=lid, other_id=other_id)


@app.route('/mesaj-gonder/<int:lid>/<int:receiver_id>', methods=['POST'])
@verified_required
@limiter.limit("30 per minute")
def send_message(lid, receiver_id):
    uid = session['user_id']
    body = request.form.get('body', '').strip()[:2000]
    if receiver_id == uid:
        flash('Özünüzə mesaj göndərə bilməzsiniz.', 'warning')
        return redirect(url_for('listing_detail', lid=lid))
    if not db.get_user_by_id(receiver_id):
        abort(404)
    if not body:
        flash('Mesaj boş ola bilməz.', 'warning')
        return redirect(url_for('conversation', lid=lid, other_id=receiver_id))
    db.send_message(uid, receiver_id, lid, body)
    return redirect(url_for('conversation', lid=lid, other_id=receiver_id))


# ─── Favorites ────────────────────────────────────────────────────────────────

@app.route('/sec/<int:lid>', methods=['POST'])
@login_required
def toggle_favorite(lid):
    uid = session['user_id']
    if db.is_favorite(uid, lid):
        db.remove_favorite(uid, lid)
    else:
        db.add_favorite(uid, lid)
    nxt = request.form.get('next') or request.referrer or url_for('index')
    if nxt.startswith('/'):
        return redirect(nxt)
    return redirect(url_for('index'))


@app.route('/secilmisler')
@login_required
def favorites():
    rows = db.get_favorites(session['user_id'])
    listings = [listing_to_dict(l) for l in rows]
    return render_template('favorites.html', listings=listings, total=len(listings))


# ─── Reports ──────────────────────────────────────────────────────────────────

@app.route('/sikayet/<int:lid>', methods=['POST'])
@login_required
@limiter.limit("10 per hour")
def report_listing(lid):
    if not db.get_listing(lid):
        abort(404)
    reason = request.form.get('reason', '').strip()[:500]
    if not reason:
        flash('Şikayət səbəbini yazın.', 'warning')
    else:
        db.create_report(session['user_id'], lid, reason)
        flash('Şikayətiniz qəbul edildi. Admin yoxlayacaq.', 'success')
    return redirect(url_for('listing_detail', lid=lid))


# ─── Admin Routes ─────────────────────────────────────────────────────────────

@app.route('/admin/')
@admin_required
def admin_dashboard():
    stats = db.get_stats()
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/elanlar')
@admin_required
def admin_listings():
    page = int(request.args.get('page', 1))
    status = request.args.get('status', '')
    rows, total = db.admin_get_all_listings(page=page, per_page=30,
                                             status=status if status else None)
    listings = [listing_to_dict(l) for l in rows]
    pages = (total + 29) // 30
    return render_template('admin/listings.html', listings=listings,
                           total=total, page=page, pages=pages, status=status)

@app.route('/admin/elan-sil/<int:lid>', methods=['POST'])
@admin_required
def admin_delete_listing(lid):
    db.delete_listing(lid)
    flash('Elan silindi.', 'info')
    return redirect(url_for('admin_listings'))

@app.route('/admin/istifadeciler')
@admin_required
def admin_users():
    page = int(request.args.get('page', 1))
    rows, total = db.get_all_users(page=page, per_page=30)
    pages = (total + 29) // 30
    return render_template('admin/users.html', users=[dict(u) for u in rows],
                           total=total, page=page, pages=pages)

@app.route('/admin/istifadeci-sil/<int:uid>', methods=['POST'])
@admin_required
def admin_delete_user(uid):
    if uid == session['user_id']:
        flash('Öz hesabınızı silə bilməzsiniz.', 'danger')
    else:
        db.delete_user(uid)
        flash('İstifadəçi silindi.', 'info')
    return redirect(url_for('admin_users'))

@app.route('/admin/sikayetler')
@admin_required
def admin_reports():
    page = int(request.args.get('page', 1))
    status = request.args.get('status', '')
    rows, total = db.get_reports(page=page, per_page=30,
                                 status=status if status else None)
    pages = (total + 29) // 30
    return render_template('admin/reports.html', reports=[dict(r) for r in rows],
                           total=total, page=page, pages=pages, status=status)


@app.route('/admin/sikayet-hell/<int:rid>', methods=['POST'])
@admin_required
def admin_resolve_report(rid):
    db.resolve_report(rid)
    flash('Şikayət həll edildi.', 'success')
    return redirect(url_for('admin_reports'))


@app.route('/admin/parametrler', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    if request.method == 'POST':
        for key in ['site_name', 'anthropic_api_key', 'contact_phone', 'contact_email',
                    'social_tiktok', 'social_instagram', 'social_whatsapp']:
            val = request.form.get(key, '').strip()
            db.set_setting(key, val)
        flash('Parametrlər yadda saxlanıldı.', 'success')
        return redirect(url_for('admin_settings'))
    settings = db.get_all_settings()
    return render_template('admin/settings.html', settings=settings)

@app.route('/admin/saglamliq', methods=['GET', 'POST'])
@admin_required
def admin_health():
    """Sistem sağlamlığı + data-itməsi yoxlaması (kalıcı disk işləyirmi).
    POST = canlı yazma/oxuma testini işə salır."""
    import diagnostics
    test_result = None
    if request.method == 'POST':
        test_result = diagnostics.live_persistence_test()
    return render_template('admin/health.html',
                           h=diagnostics.collect_health(),
                           test_result=test_result)

@app.route('/admin/telegram-test', methods=['POST'])
@admin_required
def admin_telegram_test():
    """Telegram kənar yedəyini dərhal test edir: yedək yaradıb göndərir."""
    import backup
    if not (backup.TELEGRAM_BOT_TOKEN and backup.TELEGRAM_CHAT_ID):
        flash('Telegram qoşulmayıb — TELEGRAM_BOT_TOKEN və TELEGRAM_CHAT_ID əlavə et.', 'warning')
        return redirect(url_for('admin_health'))
    try:
        path = backup.make_backup(send=False)
        if backup.send_to_telegram(path):
            flash('✅ Test yedəyi Telegram-a göndərildi — Telegram-ı yoxla.', 'success')
        else:
            flash('❌ Telegram-a göndərilmədi. Token/chat id-ni yoxla.', 'danger')
    except Exception as e:
        flash(f'Xəta: {e}', 'danger')
    return redirect(url_for('admin_health'))

@app.route('/admin/yedek')
@admin_required
def admin_backup():
    """Bazanın (tutarlı snapshot) + şəkillərin zip yedəyini yaradıb yükləyir."""
    import zipfile
    import tempfile
    import sqlite3
    from config import DATABASE_PATH
    ts = datetime.now().strftime('%Y%m%d-%H%M%S')
    tmp_zip = os.path.join(tempfile.gettempdir(), f'malbazari-backup-{ts}.zip')
    tmp_db = os.path.join(tempfile.gettempdir(), f'mb-{ts}.sqlite')
    # SQLite backup API ilə tutarlı surət
    src = sqlite3.connect(DATABASE_PATH)
    dst = sqlite3.connect(tmp_db)
    with dst:
        src.backup(dst)
    src.close(); dst.close()
    with zipfile.ZipFile(tmp_zip, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(tmp_db, 'malbazari.db')
        if os.path.isdir(UPLOAD_FOLDER):
            for root, _, files in os.walk(UPLOAD_FOLDER):
                for fn in files:
                    fp = os.path.join(root, fn)
                    z.write(fp, os.path.join('uploads', os.path.relpath(fp, UPLOAD_FOLDER)))
    try:
        os.remove(tmp_db)
    except OSError:
        pass
    return send_file(tmp_zip, as_attachment=True, download_name=f'malbazari-backup-{ts}.zip')

# ─── Admin Code Editor ────────────────────────────────────────────────────────

# Təhlükəsizlik: yalnız bu uzantılar REDAKTƏ oluna bilər (RCE-nin qarşısını alır).
# .py / .db / .secret_key və s. yazıla bilməz — admin hesabı ələ keçsə belə
# server kodu dəyişdirilə bilməz.
EDITABLE_EXT = {'html', 'css', 'js', 'txt', 'md', 'json'}

def safe_path(rel_path):
    safe = os.path.realpath(os.path.join(BASE_DIR, rel_path))
    if not safe.startswith(os.path.realpath(BASE_DIR)):
        return None
    return safe

def _is_editable(rel_path):
    ext = rel_path.rsplit('.', 1)[-1].lower() if '.' in rel_path else ''
    return ext in EDITABLE_EXT

@app.route('/admin/kod-redaktoru')
@admin_required
def admin_editor():
    def list_files(directory, base):
        result = []
        for item in sorted(os.listdir(directory)):
            full = os.path.join(directory, item)
            rel = os.path.relpath(full, base).replace('\\', '/')
            if os.path.isdir(full) and not item.startswith('.') and item not in ['__pycache__', 'uploads']:
                result.append({'type': 'dir', 'name': item, 'path': rel,
                                'children': list_files(full, base)})
            elif os.path.isfile(full) and item.rsplit('.', 1)[-1] in [
                    'py', 'html', 'css', 'js', 'txt', 'md', 'json']:
                result.append({'type': 'file', 'name': item, 'path': rel})
        return result

    file_tree = list_files(BASE_DIR, BASE_DIR)
    history = db.get_edit_history(limit=10)
    return render_template('admin/editor.html', file_tree=file_tree,
                           history=[dict(h) for h in history])

@app.route('/admin/fayl-oku', methods=['POST'])
@admin_required
def admin_read_file():
    rel = request.json.get('path', '')
    path = safe_path(rel)
    if not path or not os.path.isfile(path):
        return jsonify({'error': 'Fayl tapılmadı'}), 404
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({'content': content, 'path': rel})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/fayl-yaz', methods=['POST'])
@admin_required
def admin_write_file():
    rel = request.json.get('path', '')
    content = request.json.get('content', '')
    path = safe_path(rel)
    if not path:
        return jsonify({'error': 'İcazəsiz yol'}), 403
    if not _is_editable(rel):
        return jsonify({'error': 'Bu fayl tipini redaktə etmək olmaz (yalnız şablon/mətn). '
                                 'Kod (.py) dəyişiklikləri təhlükəsizlik üçün bağlanıb.'}), 403
    # Save backup
    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as f:
            old = f.read()
        db.save_edit_history(rel, old, session.get('user_id'))
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/tarix-bax/<int:hid>', methods=['POST'])
@admin_required
def admin_restore_history(hid):
    conn_db = db.get_db()
    row = conn_db.execute("SELECT * FROM edit_history WHERE id=?", (hid,)).fetchone()
    conn_db.close()
    if not row:
        return jsonify({'error': 'Tapılmadı'}), 404
    path = safe_path(row['filename'])
    if not path:
        return jsonify({'error': 'İcazəsiz'}), 403
    if not _is_editable(row['filename']):
        return jsonify({'error': 'Bu fayl tipini bərpa etmək olmaz.'}), 403
    with open(path, 'w', encoding='utf-8') as f:
        f.write(row['content'])
    return jsonify({'ok': True})

@app.route('/admin/ai-kod', methods=['POST'])
@admin_required
def admin_ai_code():
    instruction = request.json.get('instruction', '').strip()
    current_code = request.json.get('code', '')
    filename = request.json.get('filename', '')

    api_key = db.get_setting('anthropic_api_key')
    if not api_key:
        return jsonify({'error': 'Anthropic API açarı ayarlanmayıb. Parametrlər bölməsindən əlavə edin.'}), 400

    try:
        import anthropic as ant
        client = ant.Anthropic(api_key=api_key)
        prompt = f"""Fayl: {filename}

Mövcud kod:
```
{current_code}
```

Tapşırıq: {instruction}

Yalnız dəyişdirilmiş tam kodu qaytarın. Heç bir izahat, markdown blok işarəsi ```  olmadan, yalnız xalis kodu yazın."""

        message = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=8192,
            messages=[{"role": "user", "content": prompt}]
        )
        new_code = message.content[0].text
        # Strip markdown code blocks if present
        if new_code.startswith('```'):
            lines = new_code.split('\n')
            new_code = '\n'.join(lines[1:-1]) if lines[-1] == '```' else '\n'.join(lines[1:])
        return jsonify({'code': new_code})
    except Exception as e:
        return jsonify({'error': f'AI xətası: {str(e)}'}), 500

# ─── Static Uploads ───────────────────────────────────────────────────────────

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ─── SEO (sitemap / robots) ────────────────────────────────────────────────────

@app.route('/sitemap.xml')
def sitemap():
    from flask import Response
    pages = []
    pages.append(url_for('index', _external=True))
    pages.append(url_for('about', _external=True))
    pages.append(url_for('search', _external=True))
    for slug in CATEGORIES:
        pages.append(url_for('category', slug=slug, _external=True))
    # Aktiv elanlar
    rows, _ = db.get_listings(page=1, per_page=1000)
    for r in rows:
        pages.append(url_for('listing_detail', lid=r['id'], _external=True))

    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in pages:
        xml.append(f'  <url><loc>{u}</loc></url>')
    xml.append('</urlset>')
    return Response('\n'.join(xml), mimetype='application/xml')


@app.route('/robots.txt')
def robots():
    from flask import Response
    lines = [
        'User-agent: *',
        'Disallow: /admin/',
        'Disallow: /profil',
        'Disallow: /mesajlar',
        'Disallow: /secilmisler',
        f'Sitemap: {url_for("sitemap", _external=True)}',
    ]
    return Response('\n'.join(lines), mimetype='text/plain')

# ─── Error Handlers ───────────────────────────────────────────────────────────

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, msg='İcazə rədd edildi'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, msg='Səhifə tapılmadı'), 404

@app.errorhandler(429)
def too_many(e):
    return render_template('error.html', code=429,
                           msg='Çox sayda sorğu göndərdiniz. Bir az gözləyib yenidən cəhd edin.'), 429

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', code=500, msg='Server xətası'), 500

# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=DEBUG, host='0.0.0.0', port=5000)
