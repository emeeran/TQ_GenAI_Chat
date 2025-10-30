# Quick Start Guide - Optimized Setup

This guide helps you set up an optimized, lightweight version of TQ GenAI Chat.

## 🚀 Quick Setup (5 minutes)

### 1. Clean existing installation

```bash
# Navigate to project
cd /home/em/code/wip/TQ_GenAI_Chat

# Run optimization script
./optimize.sh
```

### 2. Set up optimized virtual environment

```bash
# Remove old virtual environment
rm -rf fastapi_env/

# Create new lightweight environment
python3.12 -m venv .venv

# Activate
source .venv/bin/activate

# Install production dependencies only
pip install -r requirements-prod.txt

# For development, also install:
# pip install -r requirements-dev.txt
```

### 3. Configure environment

```bash
# Copy example environment file
cp .env.example .env  # or create if doesn't exist

# Edit with your API keys
nano .env
```

Required environment variables:
```bash
# At minimum, configure one AI provider:
OPENAI_API_KEY=your_key_here
# or
ANTHROPIC_API_KEY=your_key_here
# or
GROQ_API_KEY=your_key_here

# Optional: Redis (for caching)
REDIS_URL=redis://localhost:6379

# Optional: Secret key for sessions
SECRET_KEY=your_secret_key_here
```

### 4. Initialize directories

```bash
# Create required directories
mkdir -p uploads saved_chats exports

# Add .gitkeep files
touch uploads/.gitkeep saved_chats/.gitkeep exports/.gitkeep
```

### 5. Run the application

```bash
# Activate virtual environment if not already active
source .venv/bin/activate

# Run with uvicorn (FastAPI)
python main.py

# Or manually:
# uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Visit: http://localhost:8000

## 📊 Verification

Check that optimization worked:

```bash
# Check project size
du -sh .

# Check virtual environment size
du -sh .venv/

# Count dependencies
pip list | wc -l

# Verify no cache files
find . -name "__pycache__" -o -name "*.pyc" | wc -l
```

Expected results:
- Project size: < 400MB
- Virtual environment: < 300MB
- Dependencies: ~25-30 packages
- Cache files: 0

## 🔧 Troubleshooting

### Issue: Module not found

```bash
# Reinstall dependencies
pip install -r requirements-prod.txt --force-reinstall
```

### Issue: Redis connection error

```bash
# Start Redis (if installed)
redis-server

# Or disable Redis in code by not setting REDIS_URL
```

### Issue: Port already in use

```bash
# Change port in main.py or run with custom port:
uvicorn main:app --port 8001
```

## 🎯 Performance Tips

### Enable Response Compression

Already configured in `main.py`:
```python
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### Use Production Server

For production, use Gunicorn with Uvicorn workers:

```bash
pip install gunicorn

gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### Enable Caching

Make sure Redis is running and configured:

```bash
# Install Redis
sudo apt install redis-server  # Ubuntu/Debian
brew install redis             # macOS

# Start Redis
redis-server

# Verify
redis-cli ping  # Should return PONG
```

## 📦 Deployment Options

### Option 1: Docker (Recommended)

```bash
# Build image
docker build -t tq-genai-chat .

# Run container
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  -v $(pwd)/uploads:/app/uploads \
  tq-genai-chat
```

### Option 2: Systemd Service

Create `/etc/systemd/system/tq-genai-chat.service`:

```ini
[Unit]
Description=TQ GenAI Chat
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/path/to/TQ_GenAI_Chat
Environment="PATH=/path/to/TQ_GenAI_Chat/.venv/bin"
ExecStart=/path/to/TQ_GenAI_Chat/.venv/bin/gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable tq-genai-chat
sudo systemctl start tq-genai-chat
sudo systemctl status tq-genai-chat
```

### Option 3: Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/TQ_GenAI_Chat/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## 📝 Development Workflow

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=core --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Code Formatting

```bash
# Format code
black .

# Sort imports
isort .

# Check types
mypy core/ app/
```

### Adding New Dependencies

```bash
# Add to requirements-prod.txt for production dependencies
# Add to requirements-dev.txt for development-only dependencies

# Reinstall
pip install -r requirements-prod.txt
```

## 🔐 Security Checklist

- [ ] Change default SECRET_KEY in .env
- [ ] Use HTTPS in production (configure Nginx with Let's Encrypt)
- [ ] Restrict CORS origins in main.py (change from `["*"]`)
- [ ] Set up rate limiting
- [ ] Enable authentication for sensitive routes
- [ ] Keep API keys in .env (never commit to git)
- [ ] Regular dependency updates: `pip list --outdated`

## 📈 Monitoring

### Check Application Health

```bash
curl http://localhost:8000/health
```

### Monitor Resource Usage

```bash
# CPU and memory
htop

# Disk space
df -h

# Check logs
tail -f logs/app.log
```

### Performance Profiling

```bash
# Install profiling tools
pip install py-spy

# Profile running application
sudo py-spy top --pid $(pgrep -f "python main.py")
```

## 🆘 Getting Help

1. Check logs: `tail -f logs/app.log`
2. Review configuration: `cat .env`
3. Test API: `curl http://localhost:8000/api/v1/health`
4. Check Redis: `redis-cli ping`
5. Verify dependencies: `pip list`

## 🎉 Next Steps

After basic setup:

1. Read `OPTIMIZATION_RECOMMENDATIONS.md` for detailed optimization guide
2. Configure additional AI providers in `.env`
3. Set up monitoring and alerting
4. Configure backup strategy for uploads and database
5. Implement CI/CD pipeline

---

**Happy coding!** 🚀
