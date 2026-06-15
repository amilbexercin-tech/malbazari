import os
import json
import time
import secrets
import threading
from datetime import datetime, timedelta
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_from_directory, abort)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
from PIL import Image
import database as db
import i18n
from config import (SECRET_KEY, UPLOAD_FOLDER, MAX_CONTENT_LENGTH,
                    CATEGORIES, REGIONS, BASE_DIR, MAX_IMAGES,
                    SUBCATEGORY_EXAMPLES, DEBUG)

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# CSRF qoruması — bütün POST formaları və AJAX sorğuları üçün token tələb olunur
csrf = CSRFProtect(app)

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# ─── Init ────────────────────────────────────────────────────────────────────

with app.app_context():
    db.init_db()
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

MAINTENANCE_INTERVAL = 600  # 10 dəqiqə
_maintenance_lock = threading.Lock()
_last_maintenance = 0.0


def run_maintenance():
    """Vaxtı keçmiş elanları sil.
    İnterval keçməyibsə və ya başqa sorğu eyni anda işlədirsə — heç nə etmir."""
    global _last_maintenance
    now = time.monotonic()
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


@app.before_request
def _maintenance_before_request():
    run_maintenance()


@app.context_processor
def inject_globals():
    lang = i18n.normalize_lang(session.get('lang', i18n.DEFAULT_LANG))
    return {
        'categories': CATEGORIES,
        'regions': REGIONS,
        'subcategory_examples': SUBCATEGORY_EXAMPLES,
        'site_name': db.get_setting('site_name', 'MalBazari.biz'),
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

    rows, total = db.get_listings(category=slug,
                                  subcategory=sub if sub else None,
                                  region=region if region else None,
                                  page=page, per_page=20)
    listings = [listing_to_dict(l) for l in rows]
    pages = (total + 19) // 20
    return render_template('category.html', cat=cat, slug=slug,
                           listings=listings, total=total,
                           page=page, pages=pages, sub=sub, region=region)

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

    rows, total = db.get_listings(
        category=category if category else None,
        region=region if region else None,
        search=q, page=page, per_page=20)
    listings = [listing_to_dict(l) for l in rows]
    pages = (total + 19) // 20
    return render_template('search.html', listings=listings, total=total,
                           q=q, page=page, pages=pages, region=region, cat=category)

# ─── Auth Routes ─────────────────────────────────────────────────────────────

@app.route('/qeydiyyat', methods=['GET', 'POST'])
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
        flash(f'Xoş gəldiniz, {username}!', 'success')
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/giris', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        user = db.get_user_by_phone(phone)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])
            flash(f'Xoş gəldiniz, {user["username"]}!', 'success')
            nxt = request.args.get('next')
            if nxt and nxt.startswith('/'):
                return redirect(nxt)
            return redirect(url_for('index'))
        flash('Nömrə və ya şifrə yanlışdır.', 'danger')
    return render_template('login.html')

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

# ─── Listing CRUD ────────────────────────────────────────────────────────────

@app.route('/elan-yarat', methods=['GET', 'POST'])
@login_required
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
@login_required
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
        for key in ['site_name', 'card_number', 'card_owner',
                    'anthropic_api_key', 'contact_phone', 'contact_email']:
            val = request.form.get(key, '').strip()
            db.set_setting(key, val)
        flash('Parametrlər yadda saxlanıldı.', 'success')
        return redirect(url_for('admin_settings'))
    settings = db.get_all_settings()
    return render_template('admin/settings.html', settings=settings)

# ─── Admin Code Editor ────────────────────────────────────────────────────────

def safe_path(rel_path):
    safe = os.path.realpath(os.path.join(BASE_DIR, rel_path))
    if not safe.startswith(os.path.realpath(BASE_DIR)):
        return None
    return safe

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

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', code=500, msg='Server xətası'), 500

# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=DEBUG, host='0.0.0.0', port=5000)
