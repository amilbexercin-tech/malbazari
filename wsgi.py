"""Production giriş nöqtəsi (WSGI).
Gunicorn / uWSGI bu faylı yükləyir: `gunicorn wsgi:app`."""
from app import app

if __name__ == "__main__":
    app.run()
