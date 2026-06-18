# HeyvanBazar — Yayım (Deployment) Təlimatı

## 1. Ətraf mühit dəyişənləri (production-da MÜTLƏQ təyin et)

| Dəyişən | Təsvir |
|---------|--------|
| `SECRET_KEY` | Sessiya açarı. Təyin olunmasa `.secret_key` faylından oxunur. Production-da öz dəyərini ver. |
| `ADMIN_PHONE` | İlk admin login (yalnız boş bazada). |
| `ADMIN_PASSWORD` | İlk admin parolu (yalnız boş bazada). |
| `FLASK_DEBUG` | **Production-da TƏYİN ETMƏ** (defolt söndürülüb). |
| `SESSION_COOKIE_SECURE` | HTTPS arxasında **1** təyin et (sessiya kukisi yalnız HTTPS-də). Lokal HTTP-də boş saxla. |
| `SMS_PROVIDER` | OTP üçün: `dev` (kod ekranda) və ya `twilio` (real SMS). |
| `SMS_ACCOUNT_SID` | Twilio Account SID (real SMS üçün). |
| `SMS_API_KEY` / `SMS_SENDER` | Twilio Auth Token və göndərən nömrə (+1…). |

Nümunə:
```bash
export SECRET_KEY="$(python -c 'import secrets;print(secrets.token_hex(32))')"
export ADMIN_PHONE="@Superlahiye@"
export ADMIN_PASSWORD="güclü-parol-buraya"
```

## 2. Quraşdırma

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3. İşə salma (production — Gunicorn, Linux)

```bash
gunicorn -c gunicorn_config.py wsgi:app
# və ya: gunicorn -w 3 -b 0.0.0.0:8000 wsgi:app
```

> Qeyd: Gunicorn Windows-da işləmir. Lokal Windows inkişafı üçün `python run.py` istifadə et.
> Windows production üçün `waitress` alternativ ola bilər: `waitress-serve --port=8000 wsgi:app`.

## 4. Nginx (reverse proxy + statik fayllar) nümunəsi

```nginx
server {
    listen 80;
    server_name heyvanbazar.az www.heyvanbazar.az;

    client_max_body_size 16M;          # şəkil yükləmə limiti

    location /static/ {
        alias /path/to/malbazari/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

HTTPS üçün: `certbot --nginx -d heyvanbazar.az -d www.heyvanbazar.az`

## 5. systemd servisi (avtomatik başlatma) nümunəsi

`/etc/systemd/system/malbazari.service`:
```ini
[Unit]
Description=HeyvanBazar Gunicorn
After=network.target

[Service]
WorkingDirectory=/path/to/malbazari
Environment="SECRET_KEY=..."
Environment="ADMIN_PASSWORD=..."
ExecStart=/path/to/malbazari/venv/bin/gunicorn -c gunicorn_config.py wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now malbazari
```

## 6. Yedəkləmə (backup)

Bütün məlumat `malbazari.db` faylındadır + şəkillər `static/uploads/`-da.

**Avtomatik yedək** (`backup.py` — baza + şəkilləri zip-ə yığır, son 14-ü saxlayır):
```bash
python backup.py        # əl ilə
# Cron (hər gecə 03:00):
0 3 * * * cd /path/to/malbazari && /path/to/venv/bin/python backup.py
```
Admin paneldən də **"Yedək Al"** düyməsi ilə zip yükləyə bilərsən.

## 7. Təhlükəsizlik xatırlatması

- **Admin kod redaktoru** (`/admin/kod-redaktoru`) brauzerdən fayl yazmağa imkan verir (potensial RCE).
  Production-da admin hesabını güclü parolla qoru və ya bu funksiyanı söndür.
- Debug rejimini production-da AÇMA.
- SQLite az-orta trafik üçün uyğundur; böyük yük olarsa PostgreSQL-ə keç.
