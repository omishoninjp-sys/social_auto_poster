# Gunicorn configuration file
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"
workers = 2
threads = 4
timeout = 300
graceful_timeout = 120
keepalive = 5
