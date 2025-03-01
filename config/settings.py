from pathlib import Path

# Performance settings
CACHE_TTL = 300
REQUEST_TIMEOUT = 60
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 50
MAX_RETRIES = 3
RATE_LIMIT = 60

# Vector search settings
MAX_FEATURES = 10000
SIMILARITY_THRESHOLD = 0.1
CACHE_SIZE = 1000
VECTOR_BATCH_SIZE = 32

# File processing settings
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {
    'pdf', 'epub', 'docx', 'xlsx',
    'csv', 'md', 'jpg', 'jpeg', 'png'
}

# Path settings
BASE_DIR = Path(__file__).parent.parent
SAVE_DIR = BASE_DIR / 'saved_chats'
EXPORT_DIR = BASE_DIR / 'exports'
UPLOAD_DIR = BASE_DIR / 'uploads'

# Ensure directories exist
for directory in [SAVE_DIR, EXPORT_DIR, UPLOAD_DIR]:
    directory.mkdir(mode=0o755, parents=True, exist_ok=True)

# API configurations with connection pooling
API_POOL_CONFIG = {
    'max_size': 100,
    'max_retries': 3,
    'timeout': REQUEST_TIMEOUT,
    'ttl_dns_cache': 300,
    'use_dns_cache': True
}
