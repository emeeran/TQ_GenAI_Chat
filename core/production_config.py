"""
Production Configuration Module - Task 4.2.3
Optimized production deployment settings with Gunicorn, Nginx, SSL/TLS, security headers
"""

import logging
import multiprocessing
import os
from pathlib import Path
from typing import Any


class ProductionConfig:
    """Production deployment configuration"""

    def __init__(self):
        self.app_name = "tq-genai-chat"
        self.app_version = "1.0.0"
        self.environment = os.getenv("FLASK_ENV", "production")
        self.debug = False
        self.testing = False

        # Performance settings
        self.max_workers = self._calculate_workers()
        self.worker_class = "gevent"
        self.worker_connections = 1000
        self.max_requests = 1000
        self.max_requests_jitter = 100
        self.preload_app = True
        self.timeout = 30
        self.keepalive = 60

        # Security settings
        self.secret_key = os.getenv("SECRET_KEY", self._generate_secret_key())
        self.secure_cookies = True
        self.ssl_redirect = True
        self.force_https = True

        # Database settings
        self.db_pool_size = 20
        self.db_max_overflow = 30
        self.db_pool_timeout = 30
        self.db_pool_recycle = 3600

        # Cache settings
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.cache_type = "redis"
        self.cache_default_timeout = 300

        # Log settings
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_format = "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
        self.log_file = "/var/log/tq-genai-chat/app.log"
        self.access_log = "/var/log/tq-genai-chat/access.log"
        self.error_log = "/var/log/tq-genai-chat/error.log"

        # File upload settings
        self.max_content_length = 64 * 1024 * 1024  # 64MB
        self.upload_folder = "/var/lib/tq-genai-chat/uploads"
        self.allowed_extensions = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "docx", "csv", "xlsx"}

        # Rate limiting
        self.rate_limit_per_minute = 60
        self.rate_limit_per_hour = 1000
        self.rate_limit_storage_url = self.redis_url

    def _calculate_workers(self) -> int:
        """Calculate optimal number of workers"""
        cpu_count = multiprocessing.cpu_count()
        # Formula: (2 x CPU cores) + 1
        return min(max((2 * cpu_count) + 1, 4), 16)  # Between 4-16 workers

    def _generate_secret_key(self) -> str:
        """Generate a secure secret key"""
        import secrets

        return secrets.token_urlsafe(32)

    def get_gunicorn_config(self) -> dict[str, Any]:
        """Get Gunicorn configuration"""
        return {
            "bind": "0.0.0.0:8000",
            "workers": self.max_workers,
            "worker_class": self.worker_class,
            "worker_connections": self.worker_connections,
            "max_requests": self.max_requests,
            "max_requests_jitter": self.max_requests_jitter,
            "preload_app": self.preload_app,
            "timeout": self.timeout,
            "keepalive": self.keepalive,
            "user": "www-data",
            "group": "www-data",
            "tmp_upload_dir": "/tmp",
            "secure_scheme_headers": {
                "X-FORWARDED-PROTOCOL": "ssl",
                "X-FORWARDED-PROTO": "https",
                "X-FORWARDED-SSL": "on",
            },
            "forwarded_allow_ips": "*",
            "access_log": self.access_log,
            "error_log": self.error_log,
            "loglevel": self.log_level.lower(),
            "access_log_format": '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s',
            "pidfile": "/var/run/tq-genai-chat/gunicorn.pid",
            "daemon": False,
            "reload": False,
            "chdir": "/opt/tq-genai-chat",
        }

    def get_nginx_config(self) -> str:
        """Generate Nginx configuration"""
        return """
upstream tq_genai_chat {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=2r/s;

# Cache zones
proxy_cache_path /var/cache/nginx/tq-genai-chat levels=1:2 keys_zone=app_cache:10m max_size=1g inactive=60m use_temp_path=off;

server {
    listen 80;
    server_name _;

    # Redirect HTTP to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name _;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/tq-genai-chat.crt;
    ssl_certificate_key /etc/ssl/private/tq-genai-chat.key;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-SHA384;
    ssl_prefer_server_ciphers on;
    ssl_dhparam /etc/ssl/certs/dhparam.pem;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com; connect-src 'self';" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    # Basic settings
    client_max_body_size 64M;
    client_body_timeout 60s;
    client_header_timeout 60s;
    keepalive_timeout 65s;
    send_timeout 60s;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;

    # Static files with long cache
    location /static/ {
        alias /opt/tq-genai-chat/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        gzip_static on;

        # Security for static files
        location ~* \\.(php|jsp|asp|sh|py)$ {
            deny all;
        }
    }

    # API endpoints with rate limiting
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://tq_genai_chat;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;

        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering off;
    }

    # Upload endpoint with special rate limiting
    location /upload {
        limit_req zone=upload_limit burst=5 nodelay;
        client_max_body_size 64M;
        client_body_timeout 300s;

        proxy_pass http://tq_genai_chat;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 30s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        proxy_request_buffering off;
        proxy_buffering off;
    }

    # Main application with caching
    location / {
        # Cache static responses
        proxy_cache app_cache;
        proxy_cache_valid 200 5m;
        proxy_cache_valid 404 1m;
        proxy_cache_use_stale error timeout invalid_header updating http_500 http_502 http_503 http_504;
        proxy_cache_background_update on;
        proxy_cache_lock on;

        proxy_pass http://tq_genai_chat;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;

        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Add cache headers
        add_header X-Cache-Status $upstream_cache_status;
    }

    # Health check (no rate limiting)
    location /health {
        proxy_pass http://tq_genai_chat;
        proxy_set_header Host $host;
        access_log off;
    }

    # Block access to sensitive files
    location ~ /\\.ht {
        deny all;
    }

    location ~ /\\.(env|git|svn) {
        deny all;
    }

    # Custom error pages
    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        root /var/www/html;
    }

    error_page 404 /404.html;
    location = /404.html {
        root /var/www/html;
    }
}
"""

    def get_systemd_service(self) -> str:
        """Generate systemd service configuration"""
        return """
[Unit]
Description=TQ GenAI Chat - Gunicorn application server
Documentation=https://docs.gunicorn.org/
After=network.target redis.service
Wants=redis.service

[Service]
Type=notify
User=www-data
Group=www-data
RuntimeDirectory=tq-genai-chat
WorkingDirectory=/opt/tq-genai-chat
Environment=PATH=/opt/tq-genai-chat/venv/bin
Environment=FLASK_ENV=production
ExecStart=/opt/tq-genai-chat/venv/bin/gunicorn --config /opt/tq-genai-chat/gunicorn.conf.py app:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=30
PrivateTmp=true
RestartSec=10
Restart=always

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/tq-genai-chat /var/log/tq-genai-chat /var/lib/tq-genai-chat /tmp
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
"""

    def get_logrotate_config(self) -> str:
        """Generate logrotate configuration"""
        return """
/var/log/tq-genai-chat/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        if [ -f /var/run/tq-genai-chat/gunicorn.pid ]; then
            kill -USR1 `cat /var/run/tq-genai-chat/gunicorn.pid`
        fi
    endscript
}
"""

    def get_security_headers_middleware(self):
        """Flask middleware for security headers"""

        def security_headers_middleware(app):
            @app.after_request
            def add_security_headers(response):
                # Prevent XSS attacks
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "SAMEORIGIN"
                response.headers["X-XSS-Protection"] = "1; mode=block"

                # Content Security Policy
                csp = (
                    "default-src 'self'; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                    "style-src 'self' 'unsafe-inline'; "
                    "img-src 'self' data: https:; "
                    "font-src 'self' https://fonts.gstatic.com; "
                    "connect-src 'self';"
                )
                response.headers["Content-Security-Policy"] = csp

                # Other security headers
                response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

                # HSTS (if HTTPS)
                if request.is_secure:
                    response.headers[
                        "Strict-Transport-Security"
                    ] = "max-age=31536000; includeSubDomains; preload"

                return response

            return app

        return security_headers_middleware

    def setup_logging(self):
        """Setup production logging configuration"""
        # Ensure log directory exists
        log_dir = Path(self.log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # Configure logging
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format=self.log_format,
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler(),  # For systemd journal
            ],
        )

        # Configure access logging
        access_logger = logging.getLogger("gunicorn.access")
        access_handler = logging.FileHandler(self.access_log)
        access_handler.setFormatter(logging.Formatter(self.log_format))
        access_logger.addHandler(access_handler)

        # Configure error logging
        error_logger = logging.getLogger("gunicorn.error")
        error_handler = logging.FileHandler(self.error_log)
        error_handler.setFormatter(logging.Formatter(self.log_format))
        error_logger.addHandler(error_handler)

    def create_directories(self):
        """Create necessary directories for production"""
        directories = [
            Path(self.log_file).parent,
            Path(self.upload_folder),
            Path("/var/lib/tq-genai-chat"),
            Path("/var/run/tq-genai-chat"),
            Path("/var/cache/nginx/tq-genai-chat"),
            Path("/opt/tq-genai-chat"),
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True, mode=0o755)

    def generate_deployment_script(self) -> str:
        """Generate deployment script"""
        return """#!/bin/bash
set -e

# TQ GenAI Chat Production Deployment Script

echo "Starting TQ GenAI Chat deployment..."

# Variables
APP_NAME="tq-genai-chat"
APP_USER="www-data"
APP_DIR="/opt/$APP_NAME"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="$APP_NAME.service"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Update system
echo "Updating system packages..."
apt-get update && apt-get upgrade -y

# Install required packages
echo "Installing required packages..."
apt-get install -y python3 python3-pip python3-venv nginx redis-server \
    supervisor logrotate ufw fail2ban certbot python3-certbot-nginx

# Create application user if not exists
if ! id -u $APP_USER > /dev/null 2>&1; then
    useradd --system --shell /bin/false --home-dir $APP_DIR $APP_USER
fi

# Create directories
echo "Creating directories..."
mkdir -p $APP_DIR
mkdir -p /var/log/$APP_NAME
mkdir -p /var/lib/$APP_NAME/uploads
mkdir -p /var/run/$APP_NAME
mkdir -p /var/cache/nginx/$APP_NAME

# Set permissions
chown -R $APP_USER:$APP_USER $APP_DIR
chown -R $APP_USER:$APP_USER /var/log/$APP_NAME
chown -R $APP_USER:$APP_USER /var/lib/$APP_NAME
chown -R $APP_USER:$APP_USER /var/run/$APP_NAME

# Create virtual environment
echo "Setting up Python virtual environment..."
sudo -u $APP_USER python3 -m venv $VENV_DIR
sudo -u $APP_USER $VENV_DIR/bin/pip install --upgrade pip

# Install Python dependencies
echo "Installing Python dependencies..."
sudo -u $APP_USER $VENV_DIR/bin/pip install gunicorn gevent psutil redis

# Copy application files (assuming they're in current directory)
echo "Copying application files..."
cp -r . $APP_DIR/
chown -R $APP_USER:$APP_USER $APP_DIR

# Install application dependencies
sudo -u $APP_USER $VENV_DIR/bin/pip install -r $APP_DIR/requirements.txt

# Generate configuration files
python3 -c "
from core.production_config import ProductionConfig
config = ProductionConfig()

# Gunicorn config
with open('/opt/$APP_NAME/gunicorn.conf.py', 'w') as f:
    gunicorn_config = config.get_gunicorn_config()
    for key, value in gunicorn_config.items():
        f.write(f'{key} = {repr(value)}\\n')

# Nginx config
with open('/etc/nginx/sites-available/$APP_NAME', 'w') as f:
    f.write(config.get_nginx_config())

# Systemd service
with open('/etc/systemd/system/$SERVICE_NAME', 'w') as f:
    f.write(config.get_systemd_service())

# Logrotate config
with open('/etc/logrotate.d/$APP_NAME', 'w') as f:
    f.write(config.get_logrotate_config())
"

# Enable Nginx site
ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# Configure firewall
echo "Configuring firewall..."
ufw allow 22
ufw allow 80
ufw allow 443
ufw --force enable

# Configure fail2ban
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[nginx-http-auth]
enabled = true

[nginx-noscript]
enabled = true

[nginx-bad-request]
enabled = true

[nginx-botsearch]
enabled = true
EOF

systemctl enable fail2ban
systemctl restart fail2ban

# Start and enable services
echo "Starting services..."
systemctl daemon-reload
systemctl enable redis-server
systemctl start redis-server
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME
systemctl enable nginx
systemctl restart nginx

# Generate SSL certificate (Let's Encrypt)
echo "Setting up SSL certificate..."
read -p "Enter your domain name: " domain_name
if [ ! -z "$domain_name" ]; then
    certbot --nginx -d $domain_name --non-interactive --agree-tos --email admin@$domain_name

    # Setup auto-renewal
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
fi

echo "Deployment completed successfully!"
echo "Application is running at: https://$domain_name"
echo "Dashboard available at: https://$domain_name/dashboard"
echo ""
echo "Service management commands:"
echo "  systemctl status $SERVICE_NAME"
echo "  systemctl restart $SERVICE_NAME"
echo "  systemctl logs -f $SERVICE_NAME"
"""


# Global production config instance
production_config = ProductionConfig()
