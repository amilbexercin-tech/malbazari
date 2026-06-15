# Gunicorn konfiqurasiyası (production)
# İşə salmaq: gunicorn -c gunicorn_config.py wsgi:app

import os

bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
workers = int(os.environ.get("GUNICORN_WORKERS", "3"))
threads = int(os.environ.get("GUNICORN_THREADS", "2"))
timeout = 60
keepalive = 5

# Loglar stdout/stderr-ə (systemd / docker üçün rahatdır)
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")
