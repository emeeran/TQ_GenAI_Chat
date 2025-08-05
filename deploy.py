#!/usr/bin/env python3
"""
TQ GenAI Chat - Deployment and Testing Script
Comprehensive setup, testing, and deployment automation
"""

import logging
import shutil
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("deployment.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class DeploymentManager:
    """Manage deployment, testing, and setup operations"""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent
        self.venv_path = self.project_root / "venv"
        self.requirements_file = self.project_root / "requirements.txt"
        self.env_file = self.project_root / ".env"

    def run_command(
        self, command: str, check: bool = True, cwd: Path = None
    ) -> tuple[int, str, str]:
        """Run shell command and return result"""
        try:
            result = subprocess.run(
                command.split(),
                cwd=cwd or self.project_root,
                capture_output=True,
                text=True,
                check=check,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {command}")
            logger.error(f"Error: {e.stderr}")
            return e.returncode, e.stdout, e.stderr

    def check_prerequisites(self) -> dict[str, bool]:
        """Check if all prerequisites are installed"""
        checks = {}

        # Check Python version
        python_version = sys.version_info
        checks["python"] = python_version >= (3, 9)
        logger.info(
            f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}"
        )

        # Check Redis
        redis_code, _, _ = self.run_command("redis-cli ping", check=False)
        checks["redis"] = redis_code == 0

        # Check Git
        git_code, _, _ = self.run_command("git --version", check=False)
        checks["git"] = git_code == 0

        # Check Node.js (optional)
        node_code, _, _ = self.run_command("node --version", check=False)
        checks["nodejs"] = node_code == 0

        # Check Docker (optional)
        docker_code, _, _ = self.run_command("docker --version", check=False)
        checks["docker"] = docker_code == 0

        return checks

    def setup_virtual_environment(self) -> bool:
        """Create and setup virtual environment"""
        try:
            if self.venv_path.exists():
                logger.info("Virtual environment already exists")
                return True

            logger.info("Creating virtual environment...")
            # Use sys.executable to get the correct Python path
            python_executable = sys.executable
            code, _, stderr = self.run_command(f"{python_executable} -m venv {self.venv_path}")

            if code != 0:
                logger.error(f"Failed to create virtual environment: {stderr}")
                return False

            logger.info("Virtual environment created successfully")
            return True

        except Exception as e:
            logger.error(f"Error setting up virtual environment: {e}")
            return False

    def install_dependencies(self) -> bool:
        """Install Python dependencies"""
        try:
            if not self.requirements_file.exists():
                logger.error("Requirements file not found")
                return False

            # Determine pip path
            if sys.platform == "win32":
                pip_path = self.venv_path / "Scripts" / "pip"
            else:
                pip_path = self.venv_path / "bin" / "pip"

            logger.info("Installing dependencies...")
            code, stdout, stderr = self.run_command(
                f"{pip_path} install -r {self.requirements_file}"
            )

            if code != 0:
                logger.error(f"Failed to install dependencies: {stderr}")
                return False

            logger.info("Dependencies installed successfully")
            return True

        except Exception as e:
            logger.error(f"Error installing dependencies: {e}")
            return False

    def setup_environment_file(self) -> bool:
        """Create .env file from template"""
        try:
            env_template = self.project_root / ".env.example"

            if self.env_file.exists():
                logger.info(".env file already exists")
                return True

            if not env_template.exists():
                # Create a basic .env template
                env_content = """# TQ GenAI Chat - Environment Configuration

# Core API Keys (Required)
OPENAI_API_KEY=your_openai_api_key_here
GROQ_API_KEY=your_groq_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
XAI_API_KEY=your_xai_api_key_here

# Optional API Keys
MISTRAL_API_KEY=your_mistral_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
COHERE_API_KEY=your_cohere_api_key_here

# Application Settings
SECRET_KEY=change_this_in_production_to_a_secure_random_string
FLASK_ENV=development
DEBUG=True
PORT=5000

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=

# Performance Settings
MAX_CONTENT_LENGTH=67108864
MAX_FILES=10
CACHE_TTL=300
REQUEST_TIMEOUT=60
RATE_LIMIT=100/hour

# Security Settings
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ORIGINS=*

# Optional: Monitoring & Analytics
SENTRY_DSN=
DATADOG_API_KEY=
"""
                with open(self.env_file, "w") as f:
                    f.write(env_content)
                logger.info("Created .env file from template")
            else:
                shutil.copy(env_template, self.env_file)
                logger.info("Copied .env.example to .env")

            logger.warning("Please edit .env file with your actual API keys!")
            return True

        except Exception as e:
            logger.error(f"Error setting up environment file: {e}")
            return False

    def test_redis_connection(self) -> bool:
        """Test Redis connection"""
        try:
            import redis

            # Try to connect to Redis
            redis_client = redis.from_url("redis://localhost:6379/0")
            redis_client.ping()
            logger.info("Redis connection test: PASSED")
            return True

        except Exception as e:
            logger.error(f"Redis connection test: FAILED - {e}")
            logger.info("Please ensure Redis server is running:")
            logger.info("  Ubuntu/Debian: sudo systemctl start redis-server")
            logger.info("  macOS: brew services start redis")
            logger.info("  Windows: docker run -d -p 6379:6379 redis:alpine")
            return False

    def run_tests(self) -> bool:
        """Run comprehensive test suite"""
        try:
            # Determine python path
            if sys.platform == "win32":
                python_path = self.venv_path / "Scripts" / "python"
            else:
                python_path = self.venv_path / "bin" / "python"

            logger.info("Running test suite...")

            # Create basic test if none exists
            test_file = self.project_root / "test_app.py"
            if not test_file.exists():
                self.create_basic_tests()

            # Run tests
            code, stdout, stderr = self.run_command(f"{python_path} -m pytest test_app.py -v")

            if code == 0:
                logger.info("All tests passed!")
                return True
            else:
                logger.error(f"Some tests failed: {stderr}")
                return False

        except Exception as e:
            logger.error(f"Error running tests: {e}")
            return False

    def create_basic_tests(self):
        """Create basic test file"""
        test_content = '''"""
Basic tests for TQ GenAI Chat Enhanced
"""
import pytest
import json
import os
from pathlib import Path

# Set test environment
os.environ['FLASK_ENV'] = 'testing'
os.environ['REDIS_URL'] = 'redis://localhost:6379/1'  # Use different DB for tests

def test_environment_setup():
    """Test that basic environment is set up correctly"""
    assert Path('.env').exists(), ".env file should exist"
    assert Path('requirements.txt').exists(), "Requirements file should exist"

def test_import_app():
    """Test that app can be imported"""
    try:
        import app
        assert hasattr(app, 'app'), "App should have Flask app instance"
    except ImportError as e:
        pytest.skip(f"App not available: {e}")

def test_static_files_exist():
    """Test that static files exist"""
    static_path = Path('static')
    required_files = [
        'styles.css',
        'script.js',
        'manifest.json',
        'sw.js'
    ]

    for file in required_files:
        assert (static_path / file).exists(), f"{file} should exist in static folder"

def test_templates_exist():
    """Test that templates exist"""
    templates_path = Path('templates')
    assert (templates_path / 'index.html').exists(), "Template should exist"

def test_core_modules_exist():
    """Test that core enhancement modules exist"""
    core_path = Path('core')
    assert (core_path / 'ai_enhancements.py').exists(), "AI enhancements module should exist"

@pytest.mark.asyncio
async def test_basic_functionality():
    """Test basic app functionality"""
    try:
        from app import app

        with app.test_client() as client:
            # Test health endpoint
            response = client.get('/health')
            assert response.status_code == 200, "Health endpoint should return 200"

            data = json.loads(response.data)
            assert 'status' in data, "Health response should include status"

    except ImportError:
        pytest.skip("App not available for testing")

def test_redis_availability():
    """Test Redis connection for caching"""
    try:
        import redis
        client = redis.from_url('redis://localhost:6379/1')
        client.ping()
        assert True, "Redis should be available"
    except Exception:
        pytest.skip("Redis not available for testing")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
'''

        with open(self.project_root / "test_app.py", "w") as f:
            f.write(test_content)
        logger.info("Created basic test suite")

    def start_development_server(self) -> bool:
        """Start the development server"""
        try:
            # Determine python path
            if sys.platform == "win32":
                python_path = self.venv_path / "Scripts" / "python"
            else:
                python_path = self.venv_path / "bin" / "python"

            logger.info("Starting development server...")
            logger.info("Server will be available at: http://localhost:5000")
            logger.info("Press Ctrl+C to stop the server")

            # Start server
            process = subprocess.Popen([str(python_path), "app.py"], cwd=self.project_root)

            try:
                process.wait()
            except KeyboardInterrupt:
                logger.info("Stopping server...")
                process.terminate()
                process.wait()

            return True

        except Exception as e:
            logger.error(f"Error starting development server: {e}")
            return False

    def create_docker_files(self):
        """Create Docker configuration files"""
        # Dockerfile
        dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    redis-server \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements-enhanced.txt .
RUN pip install --no-cache-dir -r requirements-enhanced.txt

# Copy application code
COPY . .

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:5000/health || exit 1

# Start command
CMD ["python", "app.py"]
"""

        # Docker Compose
        docker_compose_content = """version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    volumes:
      - ./uploads:/app/uploads
      - ./.env:/app/.env
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    command: redis-server --appendonly yes

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./static:/var/www/static
    depends_on:
      - app
    restart: unless-stopped

volumes:
  redis_data:
"""

        # Nginx configuration
        nginx_conf_content = """events {
    worker_connections 1024;
}

http {
    upstream app {
        server app:5000;
    }

    server {
        listen 80;
        server_name localhost;

        # Gzip compression
        gzip on;
        gzip_types text/plain text/css application/json application/javascript;

        # Static files
        location /static/ {
            alias /var/www/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # API endpoints
        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
"""

        # Write files
        with open(self.project_root / "Dockerfile", "w") as f:
            f.write(dockerfile_content)

        with open(self.project_root / "docker-compose.yml", "w") as f:
            f.write(docker_compose_content)

        with open(self.project_root / "nginx.conf", "w") as f:
            f.write(nginx_conf_content)

        logger.info("Docker configuration files created")

    def generate_deployment_report(self, checks: dict[str, bool]) -> str:
        """Generate deployment status report"""
        report = []
        report.append("=" * 60)
        report.append("TQ GenAI Chat - Enhanced Deployment Report")
        report.append("=" * 60)
        report.append("")

        # Prerequisites
        report.append("Prerequisites Status:")
        for check, status in checks.items():
            status_icon = "✅" if status else "❌"
            report.append(f"  {status_icon} {check.capitalize()}: {'OK' if status else 'MISSING'}")

        report.append("")

        # Files status
        important_files = [
            "app.py",
            "requirements.txt",
            ".env",
            "static/styles.css",
            "static/script.js",
            "templates/index.html",
            "core/ai_enhancements.py",
        ]

        report.append("Core Files Status:")
        for file_path in important_files:
            exists = (self.project_root / file_path).exists()
            status_icon = "✅" if exists else "❌"
            report.append(f"  {status_icon} {file_path}")

        report.append("")

        # Next steps
        report.append("Next Steps:")
        if not checks.get("redis", False):
            report.append("  1. Install and start Redis server")
        if not (self.project_root / ".env").exists():
            report.append("  2. Configure .env file with API keys")

        report.append("  3. Run: python deploy.py --test")
        report.append("  4. Run: python deploy.py --start")
        report.append("")

        # URLs
        report.append("Access URLs:")
        report.append("  - Development: http://localhost:5000")
        report.append("  - Health Check: http://localhost:5000/health")
        report.append("  - API Docs: http://localhost:5000/api/docs")
        report.append("")

        report.append("=" * 60)

        return "\n".join(report)


def main():
    """Main deployment script"""
    import argparse

    parser = argparse.ArgumentParser(description="TQ GenAI Chat Deployment")
    parser.add_argument("--setup", action="store_true", help="Setup environment and dependencies")
    parser.add_argument("--test", action="store_true", help="Run test suite")
    parser.add_argument("--start", action="store_true", help="Start development server")
    parser.add_argument("--docker", action="store_true", help="Create Docker configuration")
    parser.add_argument("--check", action="store_true", help="Check prerequisites only")

    args = parser.parse_args()

    # Initialize deployment manager
    deployer = DeploymentManager()

    # Check prerequisites
    logger.info("Checking prerequisites...")
    checks = deployer.check_prerequisites()

    if args.check:
        deployer.generate_deployment_report(checks)
        return

    # Setup environment
    if args.setup or not any(vars(args).values()):
        logger.info("Setting up enhanced environment...")

        # Create virtual environment
        if not deployer.setup_virtual_environment():
            logger.error("Failed to setup virtual environment")
            return

        # Install dependencies
        if not deployer.install_dependencies():
            logger.error("Failed to install dependencies")
            return

        # Setup .env file
        if not deployer.setup_environment_file():
            logger.error("Failed to setup environment file")
            return

        # Test Redis
        if not deployer.test_redis_connection():
            logger.warning("Redis not available - some features may not work")

        logger.info("Setup completed successfully!")

    # Run tests
    if args.test:
        logger.info("Running tests...")
        if deployer.run_tests():
            logger.info("All tests passed!")
        else:
            logger.error("Some tests failed")
            return

    # Create Docker files
    if args.docker:
        deployer.create_docker_files()
        logger.info("Docker configuration created")
        logger.info("To run with Docker: docker-compose up --build")

    # Start development server
    if args.start:
        deployer.start_development_server()

    # Generate final report
    if not args.start:
        deployer.generate_deployment_report(checks)


if __name__ == "__main__":
    main()
