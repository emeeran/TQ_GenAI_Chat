#!/bin/bash
# Production Deployment Script for TQ GenAI Chat - Task 4.2.3
set -e

APP_NAME="tq-genai-chat"
APP_USER="www-data"
APP_DIR="/opt/$APP_NAME"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="$APP_NAME.service"

echo "======================================================"
echo "TQ GenAI Chat - Production Deployment Script"
echo "======================================================"

# Function to print colored output
print_status() {
    echo -e "\e[32m[INFO]\e[0m $1"
}

print_error() {
    echo -e "\e[31m[ERROR]\e[0m $1"
}

print_warning() {
    echo -e "\e[33m[WARNING]\e[0m $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root"
    exit 1
fi

# Check Ubuntu/Debian
if ! command -v apt-get &> /dev/null; then
    print_error "This script is designed for Ubuntu/Debian systems"
    exit 1
fi

print_status "Updating system packages..."
apt-get update && apt-get upgrade -y

print_status "Installing required system packages..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    nginx \
    redis-server \
    supervisor \
    logrotate \
    ufw \
    fail2ban \
    certbot \
    python3-certbot-nginx \
    htop \
    curl \
    wget \
    unzip \
    git \
    build-essential

# Create application user if not exists
if ! id -u $APP_USER > /dev/null 2>&1; then
    print_status "Creating application user: $APP_USER"
    useradd --system --shell /bin/false --home-dir $APP_DIR $APP_USER
fi

print_status "Creating application directories..."
mkdir -p $APP_DIR
mkdir -p /var/log/$APP_NAME
mkdir -p /var/lib/$APP_NAME/uploads
mkdir -p /var/run/$APP_NAME
mkdir -p /var/cache/nginx/$APP_NAME
mkdir -p /etc/$APP_NAME

print_status "Setting up Python virtual environment..."
sudo -u $APP_USER python3 -m venv $VENV_DIR
sudo -u $APP_USER $VENV_DIR/bin/pip install --upgrade pip

print_status "Installing Python dependencies..."
sudo -u $APP_USER $VENV_DIR/bin/pip install \
    gunicorn \
    gevent \
    psutil \
    redis \
    flask \
    flask-cors \
    requests \
    aiohttp \
    python-multipart \
    python-dotenv

# Copy application files (assuming they're in current directory)
if [ -f "app.py" ]; then
    print_status "Copying application files..."
    cp -r . $APP_DIR/
    rm -rf $APP_DIR/.git $APP_DIR/.gitignore $APP_DIR/__pycache__ $APP_DIR/*.pyc

    # Install application dependencies
    if [ -f "$APP_DIR/requirements.txt" ]; then
        sudo -u $APP_USER $VENV_DIR/bin/pip install -r $APP_DIR/requirements.txt
    fi
else
    print_warning "No app.py found in current directory. Please manually copy your application files to $APP_DIR"
fi

print_status "Generating configuration files..."

# Create gunicorn configuration
cat > $APP_DIR/gunicorn.conf.py << 'EOF'
import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8000"
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
pidfile = "/var/run/tq-genai-chat/gunicorn.pid"
user = "www-data"
group = "www-data"
tmp_upload_dir = None
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}
forwarded_allow_ips = '*'

# Logging
accesslog = "/var/log/tq-genai-chat/access.log"
errorlog = "/var/log/tq-genai-chat/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Application
chdir = "/opt/tq-genai-chat"
EOF

# Create Nginx configuration
cat > /etc/nginx/sites-available/$APP_NAME << 'EOF'
upstream tq_genai_chat {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

# Rate limiting zones
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=upload_limit:10m rate=2r/s;

# Cache zone
proxy_cache_path /var/cache/nginx/tq-genai-chat levels=1:2 keys_zone=app_cache:10m max_size=1g inactive=60m use_temp_path=off;

server {
    listen 80;
    server_name _;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

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

    # Static files
    location /static/ {
        alias /opt/tq-genai-chat/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        gzip_static on;
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

        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering off;
    }

    # Upload endpoint
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

    # Main application
    location / {
        proxy_pass http://tq_genai_chat;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check
    location /health {
        proxy_pass http://tq_genai_chat;
        proxy_set_header Host $host;
        access_log off;
    }

    # Block sensitive files
    location ~ /\.(ht|git|svn|env) {
        deny all;
    }
}
EOF

# Create systemd service
cat > /etc/systemd/system/$SERVICE_NAME << EOF
[Unit]
Description=TQ GenAI Chat - Gunicorn application server
Documentation=https://github.com/benoitc/gunicorn
After=network.target redis.service
Wants=redis.service

[Service]
Type=notify
User=$APP_USER
Group=$APP_USER
RuntimeDirectory=$APP_NAME
WorkingDirectory=$APP_DIR
Environment=PATH=$VENV_DIR/bin
Environment=FLASK_ENV=production
ExecStart=$VENV_DIR/bin/gunicorn --config $APP_DIR/gunicorn.conf.py app:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=30
PrivateTmp=true
RestartSec=10
Restart=always

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR /var/log/$APP_NAME /var/lib/$APP_NAME /tmp
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

# Create logrotate configuration
cat > /etc/logrotate.d/$APP_NAME << 'EOF'
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
EOF

# Create environment file
cat > /etc/$APP_NAME/environment << 'EOF'
# TQ GenAI Chat Environment Configuration
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
REDIS_URL=redis://localhost:6379/0

# API Keys (add your keys here)
# OPENAI_API_KEY=your-openai-key
# ANTHROPIC_API_KEY=your-anthropic-key
# GROQ_API_KEY=your-groq-key
# XAI_API_KEY=your-xai-key
# MISTRAL_API_KEY=your-mistral-key

# Database
DATABASE_URL=sqlite:///var/lib/tq-genai-chat/app.db

# Upload settings
UPLOAD_FOLDER=/var/lib/tq-genai-chat/uploads
MAX_CONTENT_LENGTH=67108864

# Performance settings
MAX_WORKERS=8
WORKER_TIMEOUT=30
EOF

print_status "Setting proper permissions..."
chown -R $APP_USER:$APP_USER $APP_DIR
chown -R $APP_USER:$APP_USER /var/log/$APP_NAME
chown -R $APP_USER:$APP_USER /var/lib/$APP_NAME
chown -R $APP_USER:$APP_USER /var/run/$APP_NAME
chown -R www-data:www-data /var/cache/nginx/$APP_NAME
chmod 600 /etc/$APP_NAME/environment
chmod +x $APP_DIR/deploy_production.sh

print_status "Configuring Nginx..."
# Remove default site if it exists
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm /etc/nginx/sites-enabled/default
fi

# Enable our site
ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
nginx -t || {
    print_error "Nginx configuration test failed"
    exit 1
}

print_status "Configuring firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
echo "y" | ufw enable

print_status "Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << 'EOF'
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

print_status "Starting and enabling services..."
systemctl daemon-reload

# Start Redis
systemctl enable redis-server
systemctl start redis-server

# Start our application
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME

# Start Nginx
systemctl enable nginx
systemctl restart nginx

# Start fail2ban
systemctl enable fail2ban
systemctl restart fail2ban

print_status "Creating management scripts..."

# Create status script
cat > $APP_DIR/status.sh << 'EOF'
#!/bin/bash
echo "=== TQ GenAI Chat Status ==="
echo "Application Service:"
systemctl status tq-genai-chat.service --no-pager -l
echo ""
echo "Nginx Status:"
systemctl status nginx --no-pager -l
echo ""
echo "Redis Status:"
systemctl status redis-server --no-pager -l
echo ""
echo "Logs (last 20 lines):"
tail -n 20 /var/log/tq-genai-chat/error.log
EOF

# Create restart script
cat > $APP_DIR/restart.sh << 'EOF'
#!/bin/bash
echo "Restarting TQ GenAI Chat..."
systemctl restart tq-genai-chat.service
systemctl reload nginx
echo "Restart completed"
EOF

# Create logs script
cat > $APP_DIR/logs.sh << 'EOF'
#!/bin/bash
echo "=== TQ GenAI Chat Logs ==="
echo "Choose log type:"
echo "1) Application logs (error)"
echo "2) Access logs"
echo "3) Application service logs"
echo "4) Nginx error logs"
read -p "Enter choice (1-4): " choice

case $choice in
    1) tail -f /var/log/tq-genai-chat/error.log ;;
    2) tail -f /var/log/tq-genai-chat/access.log ;;
    3) journalctl -fu tq-genai-chat.service ;;
    4) tail -f /var/log/nginx/error.log ;;
    *) echo "Invalid choice" ;;
esac
EOF

chmod +x $APP_DIR/*.sh

print_status "Verifying installation..."
sleep 5

if systemctl is-active --quiet $SERVICE_NAME; then
    print_status "✓ Application service is running"
else
    print_error "✗ Application service failed to start"
    systemctl status $SERVICE_NAME --no-pager
fi

if systemctl is-active --quiet nginx; then
    print_status "✓ Nginx is running"
else
    print_error "✗ Nginx failed to start"
fi

if systemctl is-active --quiet redis-server; then
    print_status "✓ Redis is running"
else
    print_error "✗ Redis failed to start"
fi

# Test application response
if curl -s http://localhost/health > /dev/null; then
    print_status "✓ Application is responding"
else
    print_warning "⚠ Application may not be responding correctly"
fi

echo ""
echo "======================================================"
echo "Deployment completed!"
echo "======================================================"
echo ""
echo "Application is running at: http://$(hostname -I | awk '{print $1}')"
echo "Dashboard available at: http://$(hostname -I | awk '{print $1}')/dashboard"
echo ""
echo "Next steps:"
echo "1. Update API keys in: /etc/$APP_NAME/environment"
echo "2. Configure SSL certificate (recommended):"
echo "   certbot --nginx -d your-domain.com"
echo "3. Test the application thoroughly"
echo ""
echo "Management commands:"
echo "  $APP_DIR/status.sh    - Check service status"
echo "  $APP_DIR/restart.sh   - Restart application"
echo "  $APP_DIR/logs.sh      - View logs"
echo ""
echo "Service management:"
echo "  systemctl status $SERVICE_NAME"
echo "  systemctl restart $SERVICE_NAME"
echo "  systemctl logs -f $SERVICE_NAME"
echo ""
echo "Important files:"
echo "  Application: $APP_DIR/"
echo "  Logs: /var/log/$APP_NAME/"
echo "  Data: /var/lib/$APP_NAME/"
echo "  Config: /etc/$APP_NAME/"
echo ""
print_status "Deployment script completed successfully!"
