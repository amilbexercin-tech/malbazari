import sqlite3
import json
import os
from datetime import datetime, timedelta
from config import DATABASE_PATH, FREE_DAYS, UPLOAD_FOLDER, ADMIN_PHONE, ADMIN_PASSWORD

def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        phone_verified INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        category TEXT NOT NULL,
        subcategory TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        price REAL,
        unit TEXT DEFAULT 'AZN',
        weight TEXT,
        weight_kg REAL,
        quantity INTEGER DEFAULT 1,
        region TEXT,
        phone TEXT,
        purpose TEXT,
        breed TEXT,
        age TEXT,
        vaccinated INTEGER,
        lat REAL,
        lng REAL,
        images TEXT DEFAULT '[]',
        status TEXT DEFAULT 'active',
        is_vip INTEGER DEFAULT 0,
        is_boosted INTEGER DEFAULT 0,
        vip_expires TEXT,
        boost_date TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        expires_at TEXT,
        views INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS edit_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        user_id INTEGER
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        listing_id INTEGER,
        body TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    )''')
    c.execute("CREATE INDEX IF NOT EXISTS idx_msg_receiver ON messages(receiver_id, is_read)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_msg_thread ON messages(listing_id, sender_id, receiver_id)")

    c.execute('''CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        listing_id INTEGER NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(user_id, listing_id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reporter_id INTEGER,
        listing_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT (datetime('now'))
    )''')

    # ── Mövcud bazalar üçün miqrasiya: çatışmayan sütunları əlavə et ──
    migrations = [
        ("users", "phone_verified", "INTEGER DEFAULT 0"),
        ("users", "totp_secret", "TEXT"),
        ("users", "backup_codes", "TEXT"),
        ("listings", "weight_kg", "REAL"),
        ("listings", "purpose", "TEXT"),
        ("listings", "breed", "TEXT"),
        ("listings", "age", "TEXT"),
        ("listings", "vaccinated", "INTEGER"),
        ("listings", "lat", "REAL"),
        ("listings", "lng", "REAL"),
    ]
    for table, col, coltype in migrations:
        cols = [r[1] for r in c.execute(f"PRAGMA table_info({table})").fetchall()]
        if col not in cols:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")
            # Mövcud istifadəçiləri təsdiqlənmiş say (yalnız bu sütun ilk dəfə əlavə olunanda)
            if table == "users" and col == "phone_verified":
                c.execute("UPDATE users SET phone_verified=1")

    defaults = [
        ('site_name', 'MalBazari.biz'),
        ('anthropic_api_key', ''),
        ('contact_phone', '+994 XX XXX XX XX'),
        ('contact_email', 'info@malbazari.biz'),
    ]
    for k, v in defaults:
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))

    from werkzeug.security import generate_password_hash
    admin_hash = generate_password_hash(ADMIN_PASSWORD)
    c.execute("""INSERT OR IGNORE INTO users(username,phone,password_hash,is_admin,phone_verified)
                 VALUES(?,?,?,?,?)""", ('Admin', ADMIN_PHONE, admin_hash, 1, 1))

    conn.commit()
    conn.close()

# ─── Listings ───────────────────────────────────────────────────────────────

def create_listing(data):
    conn = get_db()
    expires = (datetime.now() + timedelta(days=FREE_DAYS)).strftime('%Y-%m-%d %H:%M:%S')
    conn.execute("""INSERT INTO listings
        (user_id,category,subcategory,title,description,price,weight,weight_kg,quantity,
         region,phone,purpose,breed,age,vaccinated,lat,lng,images,expires_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (data['user_id'], data['category'], data['subcategory'], data['title'],
         data.get('description',''), data.get('price'), data.get('weight',''),
         data.get('weight_kg'), data.get('quantity',1), data.get('region',''),
         data.get('phone',''), data.get('purpose'), data.get('breed'), data.get('age'),
         data.get('vaccinated'), data.get('lat'), data.get('lng'),
         data.get('images','[]'), expires))
    lid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit(); conn.close()
    return lid

def get_listing(lid):
    conn = get_db()
    row = conn.execute("SELECT l.*,u.username FROM listings l LEFT JOIN users u ON l.user_id=u.id WHERE l.id=?", (lid,)).fetchone()
    conn.close()
    return row

def update_listing(lid, data):
    conn = get_db()
    conn.execute("""UPDATE listings SET category=?,subcategory=?,title=?,description=?,
        price=?,weight=?,weight_kg=?,quantity=?,region=?,phone=?,
        purpose=?,breed=?,age=?,vaccinated=?,lat=?,lng=?,images=? WHERE id=?""",
        (data['category'], data['subcategory'], data['title'], data.get('description',''),
         data.get('price'), data.get('weight',''), data.get('weight_kg'),
         data.get('quantity',1), data.get('region',''), data.get('phone',''),
         data.get('purpose'), data.get('breed'), data.get('age'), data.get('vaccinated'),
         data.get('lat'), data.get('lng'), data.get('images','[]'), lid))
    conn.commit(); conn.close()

def delete_listing(lid):
    conn = get_db()
    # Get images before deleting so caller can clean up files
    row = conn.execute("SELECT images FROM listings WHERE id=?", (lid,)).fetchone()
    images = []
    if row:
        try:
            images = json.loads(row['images'] or '[]')
        except Exception:
            pass
    conn.execute("DELETE FROM favorites WHERE listing_id=?", (lid,))
    conn.execute("DELETE FROM reports WHERE listing_id=?", (lid,))
    conn.execute("DELETE FROM messages WHERE listing_id=?", (lid,))
    conn.execute("DELETE FROM listings WHERE id=?", (lid,))
    conn.commit(); conn.close()
    # Delete uploaded images from disk
    for img in images:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, img))
        except OSError:
            pass

def increment_views(lid):
    conn = get_db()
    conn.execute("UPDATE listings SET views=views+1 WHERE id=?", (lid,))
    conn.commit(); conn.close()

SORT_SQL = {
    'new': 'l.created_at DESC',
    'old': 'l.created_at ASC',
    'price_asc': 'l.price IS NULL, l.price ASC',
    'price_desc': 'l.price IS NULL, l.price DESC',
}

def get_listings(category=None, subcategory=None, region=None, search=None,
                 page=1, per_page=20, user_id=None,
                 price_min=None, price_max=None, weight_min=None, weight_max=None,
                 purpose=None, vaccinated=None, breed=None, sort='new'):
    conn = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # All conditions use ? placeholders — no string interpolation of user data
    conds = ["l.status='active'", "l.expires_at>?"]
    params = [now]

    if category:
        conds.append("l.category=?"); params.append(category)
    if subcategory:
        conds.append("l.subcategory=?"); params.append(subcategory)
    if region:
        conds.append("l.region=?"); params.append(region)
    if user_id:
        conds.append("l.user_id=?"); params.append(user_id)
    if search:
        conds.append("(l.title LIKE ? OR l.description LIKE ? OR l.breed LIKE ?)")
        params += [f'%{search}%', f'%{search}%', f'%{search}%']
    if price_min is not None:
        conds.append("l.price >= ?"); params.append(price_min)
    if price_max is not None:
        conds.append("l.price <= ?"); params.append(price_max)
    if weight_min is not None:
        conds.append("l.weight_kg >= ?"); params.append(weight_min)
    if weight_max is not None:
        conds.append("l.weight_kg <= ?"); params.append(weight_max)
    if purpose:
        conds.append("l.purpose = ?"); params.append(purpose)
    if vaccinated is not None:
        conds.append("l.vaccinated = ?"); params.append(vaccinated)
    if breed:
        conds.append("l.breed LIKE ?"); params.append(f'%{breed}%')

    where = " AND ".join(conds)
    offset = (page - 1) * per_page
    order_by = SORT_SQL.get(sort, SORT_SQL['new'])

    total = conn.execute(f"SELECT COUNT(*) FROM listings l WHERE {where}", params).fetchone()[0]
    rows = conn.execute(f"""SELECT l.*,u.username FROM listings l
        LEFT JOIN users u ON l.user_id=u.id WHERE {where}
        ORDER BY {order_by}
        LIMIT ? OFFSET ?""", params + [per_page, offset]).fetchall()
    conn.close()
    return rows, total

def expire_listings():
    """Delete listings whose free period has elapsed. Returns image filenames to clean up."""
    conn = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    expired = conn.execute(
        "SELECT id, images FROM listings WHERE expires_at<? AND status='active'", (now,)
    ).fetchall()

    images_to_delete = []
    if expired:
        ids = [r['id'] for r in expired]
        for row in expired:
            try:
                imgs = json.loads(row['images'] or '[]')
                images_to_delete.extend(imgs)
            except Exception:
                pass
        ph = ','.join('?' * len(ids))
        conn.execute(f"DELETE FROM favorites WHERE listing_id IN ({ph})", ids)
        conn.execute(f"DELETE FROM reports WHERE listing_id IN ({ph})", ids)
        conn.execute(f"DELETE FROM messages WHERE listing_id IN ({ph})", ids)
        conn.execute(f"DELETE FROM listings WHERE id IN ({ph})", ids)

    conn.commit(); conn.close()
    return images_to_delete

def admin_get_all_listings(page=1, per_page=30, status=None):
    conn = get_db()
    conds = ["1=1"]
    params = []
    if status:
        conds.append("l.status=?"); params.append(status)
    where = " AND ".join(conds)
    offset = (page-1)*per_page
    total = conn.execute(f"SELECT COUNT(*) FROM listings l WHERE {where}", params).fetchone()[0]
    rows = conn.execute(f"""SELECT l.*,u.username,u.phone as user_phone FROM listings l
        LEFT JOIN users u ON l.user_id=u.id WHERE {where}
        ORDER BY l.created_at DESC LIMIT ? OFFSET ?""", params+[per_page, offset]).fetchall()
    conn.close()
    return rows, total

# ─── Users ──────────────────────────────────────────────────────────────────

def create_user(username, phone, password_hash):
    conn = get_db()
    try:
        conn.execute("INSERT INTO users(username,phone,password_hash) VALUES(?,?,?)",
                     (username, phone, password_hash))
        conn.commit()
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return uid
    except sqlite3.IntegrityError:
        conn.close()
        return None

def get_user_by_phone(phone):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE phone=?", (phone,)).fetchone()
    conn.close()
    return row

def get_user_by_id(uid):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return row

def get_all_users(page=1, per_page=30):
    conn = get_db()
    offset = (page-1)*per_page
    total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?",
                        (per_page, offset)).fetchall()
    conn.close()
    return rows, total

def delete_user(uid):
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=?", (uid,))
    conn.commit(); conn.close()

def set_phone_verified(uid):
    conn = get_db()
    conn.execute("UPDATE users SET phone_verified=1 WHERE id=?", (uid,))
    conn.commit(); conn.close()

def set_totp_secret(uid, secret):
    conn = get_db()
    conn.execute("UPDATE users SET totp_secret=? WHERE id=?", (secret, uid))
    conn.commit(); conn.close()

def update_username(uid, username):
    conn = get_db()
    conn.execute("UPDATE users SET username=? WHERE id=?", (username, uid))
    conn.commit(); conn.close()

def update_password(uid, password_hash):
    conn = get_db()
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (password_hash, uid))
    conn.commit(); conn.close()

def set_backup_codes(uid, codes_json):
    conn = get_db()
    conn.execute("UPDATE users SET backup_codes=? WHERE id=?", (codes_json, uid))
    conn.commit(); conn.close()

# ─── Settings ────────────────────────────────────────────────────────────────

def get_setting(key, default=''):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row['value'] if row else default

def set_setting(key, value):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
    conn.commit(); conn.close()

def get_all_settings():
    conn = get_db()
    rows = conn.execute("SELECT * FROM settings").fetchall()
    conn.close()
    return {r['key']: r['value'] for r in rows}

# ─── Edit History ────────────────────────────────────────────────────────────

def save_edit_history(filename, content, user_id=None):
    conn = get_db()
    conn.execute("INSERT INTO edit_history(filename,content,user_id) VALUES(?,?,?)",
                 (filename, content, user_id))
    conn.commit(); conn.close()

def get_edit_history(filename=None, limit=20):
    conn = get_db()
    if filename:
        rows = conn.execute("""SELECT eh.*,u.username FROM edit_history eh
            LEFT JOIN users u ON eh.user_id=u.id
            WHERE eh.filename=? ORDER BY eh.created_at DESC LIMIT ?""",
            (filename, limit)).fetchall()
    else:
        rows = conn.execute("""SELECT eh.*,u.username FROM edit_history eh
            LEFT JOIN users u ON eh.user_id=u.id
            ORDER BY eh.created_at DESC LIMIT ?""", (limit,)).fetchall()
    conn.close()
    return rows

# ─── Messages ────────────────────────────────────────────────────────────────

def send_message(sender_id, receiver_id, listing_id, body):
    conn = get_db()
    conn.execute("""INSERT INTO messages(sender_id,receiver_id,listing_id,body)
                    VALUES(?,?,?,?)""", (sender_id, receiver_id, listing_id, body))
    conn.commit(); conn.close()


def get_conversations(user_id):
    """İstifadəçinin bütün söhbətləri — hər (qarşı tərəf + elan) cütü üçün son mesaj."""
    conn = get_db()
    rows = conn.execute("""
        SELECT m.*,
            (CASE WHEN m.sender_id=? THEN m.receiver_id ELSE m.sender_id END) AS other_id,
            u.username AS other_name,
            l.title AS listing_title, l.status AS listing_status,
            (SELECT COUNT(*) FROM messages mm
               WHERE mm.receiver_id=? AND mm.is_read=0
                 AND mm.sender_id=(CASE WHEN m.sender_id=? THEN m.receiver_id ELSE m.sender_id END)
                 AND IFNULL(mm.listing_id,0)=IFNULL(m.listing_id,0)) AS unread
        FROM messages m
        LEFT JOIN users u ON u.id=(CASE WHEN m.sender_id=? THEN m.receiver_id ELSE m.sender_id END)
        LEFT JOIN listings l ON l.id=m.listing_id
        WHERE m.id IN (
            SELECT MAX(id) FROM messages
            WHERE sender_id=? OR receiver_id=?
            GROUP BY IFNULL(listing_id,0),
                     (CASE WHEN sender_id=? THEN receiver_id ELSE sender_id END)
        )
        ORDER BY m.created_at DESC
    """, (user_id, user_id, user_id, user_id, user_id, user_id, user_id)).fetchall()
    conn.close()
    return rows


def get_conversation(user_id, other_id, listing_id):
    conn = get_db()
    rows = conn.execute("""SELECT m.*, u.username AS sender_name FROM messages m
        LEFT JOIN users u ON u.id=m.sender_id
        WHERE IFNULL(m.listing_id,0)=IFNULL(?,0)
          AND ((m.sender_id=? AND m.receiver_id=?) OR (m.sender_id=? AND m.receiver_id=?))
        ORDER BY m.created_at ASC""",
        (listing_id, user_id, other_id, other_id, user_id)).fetchall()
    conn.close()
    return rows


def mark_messages_read(user_id, other_id, listing_id):
    conn = get_db()
    conn.execute("""UPDATE messages SET is_read=1
        WHERE receiver_id=? AND sender_id=? AND IFNULL(listing_id,0)=IFNULL(?,0)""",
        (user_id, other_id, listing_id))
    conn.commit(); conn.close()


def count_unread(user_id):
    conn = get_db()
    n = conn.execute("SELECT COUNT(*) FROM messages WHERE receiver_id=? AND is_read=0",
                     (user_id,)).fetchone()[0]
    conn.close()
    return n


# ─── Favorites ───────────────────────────────────────────────────────────────

def add_favorite(user_id, listing_id):
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO favorites(user_id,listing_id) VALUES(?,?)",
                 (user_id, listing_id))
    conn.commit(); conn.close()


def remove_favorite(user_id, listing_id):
    conn = get_db()
    conn.execute("DELETE FROM favorites WHERE user_id=? AND listing_id=?",
                 (user_id, listing_id))
    conn.commit(); conn.close()


def is_favorite(user_id, listing_id):
    conn = get_db()
    row = conn.execute("SELECT 1 FROM favorites WHERE user_id=? AND listing_id=?",
                       (user_id, listing_id)).fetchone()
    conn.close()
    return row is not None


def get_favorite_ids(user_id):
    """İstifadəçinin seçdiyi elan id-ləri (kartlarda ürək işarəsi üçün) — set kimi."""
    conn = get_db()
    rows = conn.execute("SELECT listing_id FROM favorites WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return {r['listing_id'] for r in rows}


def get_favorites(user_id):
    conn = get_db()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    rows = conn.execute("""SELECT l.*, u.username FROM favorites f
        JOIN listings l ON l.id=f.listing_id
        LEFT JOIN users u ON u.id=l.user_id
        WHERE f.user_id=? AND l.status='active' AND l.expires_at>?
        ORDER BY f.created_at DESC""", (user_id, now)).fetchall()
    conn.close()
    return rows


# ─── Reports ─────────────────────────────────────────────────────────────────

def create_report(reporter_id, listing_id, reason):
    conn = get_db()
    conn.execute("INSERT INTO reports(reporter_id,listing_id,reason) VALUES(?,?,?)",
                 (reporter_id, listing_id, reason))
    conn.commit(); conn.close()


def get_reports(page=1, per_page=30, status=None):
    conn = get_db()
    conds = ["1=1"]; params = []
    if status:
        conds.append("r.status=?"); params.append(status)
    where = " AND ".join(conds)
    offset = (page-1)*per_page
    total = conn.execute(f"SELECT COUNT(*) FROM reports r WHERE {where}", params).fetchone()[0]
    rows = conn.execute(f"""SELECT r.*, u.username AS reporter_name,
            l.title AS listing_title FROM reports r
        LEFT JOIN users u ON u.id=r.reporter_id
        LEFT JOIN listings l ON l.id=r.listing_id
        WHERE {where} ORDER BY r.created_at DESC LIMIT ? OFFSET ?""",
        params+[per_page, offset]).fetchall()
    conn.close()
    return rows, total


def resolve_report(rid):
    conn = get_db()
    conn.execute("UPDATE reports SET status='resolved' WHERE id=?", (rid,))
    conn.commit(); conn.close()


def count_pending_reports():
    conn = get_db()
    n = conn.execute("SELECT COUNT(*) FROM reports WHERE status='pending'").fetchone()[0]
    conn.close()
    return n


# ─── Stats ───────────────────────────────────────────────────────────────────

def get_stats():
    conn = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    stats = {
        'total_listings': conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0],
        'active_listings': conn.execute("SELECT COUNT(*) FROM listings WHERE status='active'").fetchone()[0],
        'total_users': conn.execute("SELECT COUNT(*) FROM users WHERE is_admin=0").fetchone()[0],
        'today_listings': conn.execute("SELECT COUNT(*) FROM listings WHERE date(created_at)=?", (today,)).fetchone()[0],
        'pending_reports': conn.execute("SELECT COUNT(*) FROM reports WHERE status='pending'").fetchone()[0],
    }
    conn.close()
    return stats
