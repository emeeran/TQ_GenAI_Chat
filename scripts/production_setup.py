#!/usr/bin/env python3
"""
Production Setup Script for TQ GenAI Chat
Automates production deployment setup and configuration
"""

import os
import sys
import subprocess
import secrets
import argparse
from pathlib import Path


def generate_secret_key():
    """Generate a secure secret key"""
    return secrets.token_urlsafe(32)


def generate_password():
    """Generate a secure password"""
    return secrets.token_urlsafe(16)


def create_ssl_certificates(domain=None):
    """Create self-signed SSL certificates for development/testing"""
    ssl_dir = Path("ssl")
    ssl_dir.mkdir(exist_ok=True)
    
    if domain:
        subject = f"/C=US/ST=State/L=City/O=Organization/CN={domain}"
    else:
        subject = "/C=US/ST=State/L=City/O=Organization/CN=localhost"
    
    # Generate private key
    subprocess.run([
        "openssl", "genrsa", "-out", "ssl/private.key", "2048"
    ], check=True)
    
    # Generate certificate
    subprocess.run([
        "openssl", "req", "-new", "-x509", "-key", "ssl/private.key",
        "-out", "ssl/certificate.crt", "-days", "365", "-subj", subject
    ], check=True)
    
    # Generate DH parameters
    subprocess.run([
        "openssl", "dhparam", "-out", "ssl/dhparam.pem", "2048"
    ], check=True)
    
    print("✓ SSL certificates generated")


def setup_environment_file():
    """Setup production environment file"""
    env_prod_path = Path(".env.prod")
    
    if env_prod_path.exists():
        response = input(".env.prod already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Skipping environment file setup")
            return
    
    # Generate secure values
    secret_key = generate_secret_key()
    postgres_password = generate_password()
    redis_password = generate_password()
    grafana_password = generate_password()
    
    env_content = f"""# Production Environment Configuration for TQ GenAI Chat
# Generated on {os.popen('date').read().strip()}

# Application Configuration
FLASK_ENV=production
SECRET_KEY={secret_key}
DEBUG=False
LOG_LEVEL=INFO

# Database Configuration
DATABASE_URL=postgresql://postgres:{postgres_password}@postgres:5432/tq_genai_chat
POSTGRES_PASSWORD={postgres_password}

# Redis Configuration
REDIS_URL=redis://:{redis_password}@redis:6379/0
REDIS_PASSWORD={redis_password}

# Monitoring Configuration
GRAFANA_PASSWORD={grafana_password}

# Security Configuration
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000
SESSION_TIMEOUT=3600

# Performance Configuration
MAX_WORKERS=8
WORKER_TIMEOUT=30
MAX_CONTENT_LENGTH=67108864

# API Keys (replace with your actual keys)
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
GROQ_API_KEY=your-groq-api-key
XAI_API_KEY=your-xai-api-key
MISTRAL_API_KEY=your-mistral-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key
GEMINI_API_KEY=your-gemini-api-key
COHERE_API_KEY=your-cohere-api-key
ALIBABA_API_KEY=your-alibaba-api-key
OPENROUTER_API_KEY=your-openrouter-api-key
MOONSHOT_API_KEY=your-moonshot-api-key
PERPLEXITY_API_KEY=your-perplexity-api-key
CEREBRAS_API_KEY=your-cerebras-api-key

# File Storage
UPLOAD_FOLDER=/app/uploads
MAX_FILES=10

# Cache Configuration
CACHE_ENABLED=True
CACHE_DEFAULT_TTL=300
CACHE_MAX_SIZE=1000

# SSL/TLS Configuration
SSL_CERT_PATH=/app/ssl/certificate.crt
SSL_KEY_PATH=/app/ssl/private.key

# External Services (optional)
# SENTRY_DSN=your-sentry-dsn-for-error-tracking
# DATADOG_API_KEY=your-datadog-api-key
"""
    
    with open(env_prod_path, 'w') as f:
        f.write(env_content)
    
    print("✓ Production environment file created")
    print(f"  - Secret key: {secret_key[:16]}...")
    print(f"  - Postgres password: {postgres_password}")
    print(f"  - Redis password: {redis_password}")
    print(f"  - Grafana password: {grafana_password}")
    print("\n⚠️  Remember to update API keys in .env.prod")


def create_directories():
    """Create necessary directories"""
    directories = [
        "logs",
        "uploads",
        "data",
        "cache",
        "ssl",
        "monitoring/grafana/dashboards",
        "monitoring/grafana/datasources",
        "nginx/conf.d",
        "postgres"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✓ Directories created")


def setup_monitoring_configs():
    """Setup monitoring configuration files"""
    
    # Grafana datasource
    grafana_datasource = """apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100"""
    
    with open("monitoring/grafana/datasources/datasources.yml", 'w') as f:
        f.write(grafana_datasource)
    
    # Loki config
    loki_config = """auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s
  chunk_idle_period: 5m
  chunk_retain_period: 30s

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 168h

storage_config:
  boltdb:
    directory: /loki/index

  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h"""
    
    with open("monitoring/loki.yml", 'w') as f:
        f.write(loki_config)
    
    # Promtail config
    promtail_config = """server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: app-logs
    static_configs:
      - targets:
          - localhost
        labels:
          job: tq-genai-chat
          __path__: /var/log/app/*.log"""
    
    with open("monitoring/promtail.yml", 'w') as f:
        f.write(promtail_config)
    
    print("✓ Monitoring configurations created")


def setup_postgres_init():
    """Setup PostgreSQL initialization script"""
    postgres_init = """-- TQ GenAI Chat Database Initialization

-- Create database if not exists
SELECT 'CREATE DATABASE tq_genai_chat'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'tq_genai_chat');

-- Connect to the database
\\c tq_genai_chat;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create tables (basic structure)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    content TEXT,
    file_size INTEGER,
    mime_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_documents_title ON documents USING gin(title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_documents_content ON documents USING gin(content gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created ON chat_messages(created_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers
DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_chat_sessions_updated_at ON chat_sessions;
CREATE TRIGGER update_chat_sessions_updated_at
    BEFORE UPDATE ON chat_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();"""
    
    with open("postgres/init.sql", 'w') as f:
        f.write(postgres_init)
    
    print("✓ PostgreSQL initialization script created")


def build_docker_images():
    """Build Docker images"""
    print("Building Docker images...")
    
    try:
        subprocess.run(["docker-compose", "-f", "docker-compose.prod.yml", "build"], check=True)
        print("✓ Docker images built successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Docker build failed: {e}")
        return False
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Setup TQ GenAI Chat for production")
    parser.add_argument("--domain", help="Domain name for SSL certificate")
    parser.add_argument("--skip-ssl", action="store_true", help="Skip SSL certificate generation")
    parser.add_argument("--skip-build", action="store_true", help="Skip Docker image building")
    
    args = parser.parse_args()
    
    print("🚀 Setting up TQ GenAI Chat for production...")
    print("=" * 50)
    
    # Create directories
    create_directories()
    
    # Setup environment file
    setup_environment_file()
    
    # Setup monitoring
    setup_monitoring_configs()
    
    # Setup database
    setup_postgres_init()
    
    # Generate SSL certificates
    if not args.skip_ssl:
        try:
            create_ssl_certificates(args.domain)
        except subprocess.CalledProcessError as e:
            print(f"⚠️  SSL certificate generation failed: {e}")
            print("   You can generate them manually or use Let's Encrypt")
    
    # Build Docker images
    if not args.skip_build:
        if not build_docker_images():
            print("⚠️  Docker build failed, but setup can continue")
    
    print("\n" + "=" * 50)
    print("✅ Production setup completed!")
    print("\nNext steps:")
    print("1. Update API keys in .env.prod")
    print("2. Review and customize configuration files")
    print("3. Start the application:")
    print("   docker-compose -f docker-compose.prod.yml up -d")
    print("4. Access the application at https://localhost")
    print("5. Monitor at http://localhost:3000 (Grafana)")
    print("\nFor SSL in production, consider using Let's Encrypt:")
    print("   certbot --nginx -d yourdomain.com")


if __name__ == "__main__":
    main()