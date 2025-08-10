"""
Production Gunicorn Configuration for TQ GenAI Chat
Optimized for high performance and reliability
"""

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = min(max((2 * multiprocessing.cpu_count()) + 1, 4), 16)
worker_class = "gevent"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
preload_app = True
timeout = 30
keepalive = 60

# Process naming
proc_name = "tq-genai-chat"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = os.getenv("APP_USER", "appuser")
group = os.getenv("APP_GROUP", "appuser")
tmp_upload_dir = None

# SSL/TLS
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}
forwarded_allow_ips = '*'

# Logging
accesslog = "/app/logs/access.log"
errorlog = "/app/logs/error.log"
loglevel = os.getenv("LOG_LEVEL", "info").lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Application
chdir = "/app"

# Performance tuning
max_requests_jitter = 100
preload_app = True
worker_tmp_dir = "/dev/shm"

# Graceful shutdown
graceful_timeout = 30
timeout = 30

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# SSL Context (if using SSL termination at Gunicorn level)
# keyfile = "/app/ssl/private.key"
# certfile = "/app/ssl/certificate.crt"
# ssl_version = 2  # TLSv1.2
# ciphers = "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    """Called just after a worker has been killed by a signal."""
    worker.log.info("worker received INT or QUIT signal")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info("Worker initialized (pid: %s)", worker.pid)

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.info("worker received SIGABRT signal")