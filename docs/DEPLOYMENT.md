# Deployment Guide

## Overview

This guide covers deployment options for the TQ GenAI Chat application, from local development to production environments. The refactored architecture is optimized for various deployment scenarios.

## Quick Deployment

### Local Development
```bash
# Clone and setup
git clone https://github.com/emeeran/TQ_GenAI_Chat.git
cd TQ_GenAI_Chat

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your API keys

# Run development server
python app.py
```

### Docker Deployment
```bash
# Build image
docker build -t tq-genai-chat .

# Run container
docker run -d \
  --name tq-chat \
  -p 5000:5000 \
  --env-file .env \
  tq-genai-chat

# Or use docker-compose
docker-compose up -d
```

## Environment Configuration

### Required Environment Variables

```env
# Core Settings
FLASK_ENV=production
SECRET_KEY=your-secret-key-here

# AI Provider API Keys (at least one required)
GROQ_API_KEY=your_groq_key_here          # Recommended for free tier
OPENAI_API_KEY=your_openai_key_here      # High quality responses
ANTHROPIC_API_KEY=your_claude_key_here   # Advanced reasoning
GEMINI_API_KEY=your_gemini_key_here      # Google integration

# Optional Providers
MISTRAL_API_KEY=your_mistral_key_here
XAI_API_KEY=your_grok_key_here
DEEPSEEK_API_KEY=your_deepseek_key_here
COHERE_API_KEY=your_cohere_key_here
MOONSHOT_API_KEY=your_moonshot_key_here

# Performance Settings
REQUEST_TIMEOUT=60
MAX_RETRIES=3
CACHE_TTL=300
WORKER_TIMEOUT=120

# Database Configuration
DATABASE_URL=sqlite:///documents.db
# For PostgreSQL: postgresql://user:pass@host:port/dbname

# Redis Configuration (Optional)
REDIS_URL=redis://localhost:6379/0
ENABLE_REDIS_CACHE=true

# File Upload Settings
MAX_CONTENT_LENGTH=16777216  # 16MB
UPLOAD_FOLDER=uploads/temp
```

### API Key Priority
The application will use providers in this order of preference:
1. **Groq** (fastest, free tier available)
2. **OpenAI** (highest quality)
3. **Gemini** (good balance, limited free tier)
4. **Other providers** (based on availability)

## Production Deployment

### Using Gunicorn (Recommended)
```bash
# Install gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app

# With logging
gunicorn -w 4 -b 0.0.0.0:5000 \
  --timeout 120 \
  --access-logfile access.log \
  --error-logfile error.log \
  --log-level info \
  app:app
```

### Systemd Service (Linux)
Create `/etc/systemd/system/tq-genai-chat.service`:

```ini
[Unit]
Description=TQ GenAI Chat Application
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/tq-genai-chat
Environment=PATH=/opt/tq-genai-chat/venv/bin
EnvironmentFile=/opt/tq-genai-chat/.env
ExecStart=/opt/tq-genai-chat/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable tq-genai-chat
sudo systemctl start tq-genai-chat
sudo systemctl status tq-genai-chat
```

### Nginx Reverse Proxy
Create `/etc/nginx/sites-available/tq-genai-chat`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    
    client_max_body_size 20M;  # Allow large file uploads
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Handle large uploads
        proxy_request_buffering off;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
    
    # Static files (optional optimization)
    location /static {
        alias /opt/tq-genai-chat/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/tq-genai-chat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Cloud Deployment

### Heroku
Create `Procfile`:
```
web: gunicorn -w 4 -b 0.0.0.0:$PORT --timeout 120 app:app
```

Deploy:
```bash
# Login and create app
heroku login
heroku create your-app-name

# Set environment variables
heroku config:set GROQ_API_KEY=your_key_here
heroku config:set OPENAI_API_KEY=your_key_here
# ... add other keys

# Deploy
git push heroku main
```

### Railway
Create `railway.toml`:
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "gunicorn -w 4 -b 0.0.0.0:$PORT app:app"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

[env]
FLASK_ENV = "production"
```

Deploy:
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### DigitalOcean App Platform
Create `.do/app.yaml`:
```yaml
name: tq-genai-chat
services:
- name: web
  source_dir: /
  github:
    repo: your-username/TQ_GenAI_Chat
    branch: main
    deploy_on_push: true
  run_command: gunicorn -w 4 -b 0.0.0.0:$PORT app:app
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  env:
  - key: FLASK_ENV
    value: production
  - key: GROQ_API_KEY
    value: ${GROQ_API_KEY}
    type: SECRET
  - key: OPENAI_API_KEY
    value: ${OPENAI_API_KEY}
    type: SECRET
```

### AWS Elastic Beanstalk
Create `.ebextensions/python.config`:
```yaml
option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: app:app
  aws:elasticbeanstalk:application:environment:
    FLASK_ENV: production
    PYTHONPATH: /var/app/current
```

Deploy:
```bash
# Install EB CLI
pip install awsebcli

# Initialize and deploy
eb init
eb create production
eb deploy
```

## Docker Configuration

### Dockerfile
```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads/temp

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONPATH=/app

# Run gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120", "app:app"]
```

### Docker Compose
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    volumes:
      - ./uploads:/app/uploads
    depends_on:
      - redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - app
    restart: unless-stopped

volumes:
  redis_data:
```

## Performance Optimization

### Gunicorn Configuration
Create `gunicorn.conf.py`:
```python
# Worker configuration
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 2

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "tq-genai-chat"

# Worker recycling
max_requests = 1000
max_requests_jitter = 50

# Preload application
preload_app = True
```

### Redis Configuration
Add to your deployment:
```yaml
# docker-compose.yml redis service
redis:
  image: redis:7-alpine
  command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
  volumes:
    - redis_data:/data
```

### Database Optimization
For production, consider PostgreSQL:
```bash
# Install psycopg2
pip install psycopg2-binary

# Update DATABASE_URL
export DATABASE_URL="postgresql://user:password@host:port/database"
```

## Monitoring and Logging

### Health Checks
The application provides a health endpoint:
```bash
curl http://localhost:5000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-27T10:30:00Z",
  "version": "2.0.0",
  "providers": {
    "openai": "connected",
    "groq": "connected",
    "anthropic": "api_key_missing"
  }
}
```

### Logging Configuration
Add to your environment:
```env
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

### Prometheus Metrics (Optional)
Install and configure:
```bash
pip install prometheus-flask-exporter

# Add to app.py
from prometheus_flask_exporter import PrometheusMetrics
metrics = PrometheusMetrics(app)
```

## Security Considerations

### API Key Management
- Use environment variables, never hardcode keys
- Rotate keys regularly
- Monitor usage and set rate limits
- Use least privilege principle

### Web Security
```nginx
# Add security headers in Nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
```

### SSL/TLS
Use Let's Encrypt for free SSL:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## Backup and Recovery

### Database Backup
```bash
# SQLite backup
sqlite3 documents.db ".backup backup.db"

# PostgreSQL backup
pg_dump $DATABASE_URL > backup.sql
```

### File Upload Backup
```bash
# Sync uploads directory
rsync -av uploads/ backup/uploads/
```

### Automated Backups
Create backup script:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
sqlite3 documents.db ".backup backups/documents_$DATE.db"
tar -czf backups/uploads_$DATE.tar.gz uploads/
find backups/ -name "*.db" -mtime +7 -delete
find backups/ -name "*.tar.gz" -mtime +7 -delete
```

## Troubleshooting

### Common Issues

**Application won't start**:
```bash
# Check logs
sudo journalctl -u tq-genai-chat -f

# Check configuration
python -c "from app import app; print('Config OK')"
```

**File upload errors**:
```bash
# Check permissions
ls -la uploads/
sudo chown -R www-data:www-data uploads/
```

**Provider connection issues**:
```bash
# Test API keys
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models
```

**Performance issues**:
```bash
# Monitor resources
htop
iostat 1
```

### Debug Mode
For development troubleshooting:
```env
FLASK_ENV=development
FLASK_DEBUG=true
LOG_LEVEL=DEBUG
```

This comprehensive deployment guide ensures your TQ GenAI Chat application runs reliably in any environment, from local development to large-scale production deployments.
