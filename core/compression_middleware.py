"""
Compression Middleware System (Task 3.3.3)

This module implements comprehensive HTTP response compression middleware for the TQ GenAI Chat application,
supporting Brotli, Gzip, and Deflate compression with intelligent algorithm selection and performance monitoring.
"""

import gzip
import logging
import os
import time
import zlib
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from io import BytesIO
from typing import Any, Optional

import brotli
from flask import Flask, Response, g, request

logger = logging.getLogger(__name__)


@dataclass
class CompressionConfig:
    """Configuration for compression middleware."""

    # Enable/disable compression algorithms
    enable_brotli: bool = True
    enable_gzip: bool = True
    enable_deflate: bool = True

    # Compression levels (0-11 for Brotli, 1-9 for Gzip/Deflate)
    brotli_level: int = 6
    gzip_level: int = 6
    deflate_level: int = 6

    # Minimum response size to compress (bytes)
    min_size: int = 1024

    # Maximum response size to compress (bytes)
    max_size: int = 50 * 1024 * 1024  # 50MB

    # Compressible MIME types
    compressible_types: list[str] = field(
        default_factory=lambda: [
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript",
            "application/json",
            "application/xml",
            "text/xml",
            "text/plain",
            "text/csv",
            "application/csv",
            "image/svg+xml",
            "application/rss+xml",
            "application/atom+xml",
        ]
    )

    # Files to exclude from compression (already compressed)
    exclude_extensions: list[str] = field(
        default_factory=lambda: [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
            ".ico",
            ".zip",
            ".rar",
            ".7z",
            ".tar",
            ".gz",
            ".bz2",
            ".mp4",
            ".avi",
            ".mkv",
            ".webm",
            ".mp3",
            ".ogg",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
        ]
    )

    # Pre-compression settings
    enable_precompression: bool = True
    precompression_static_dir: str = "static"

    # Performance settings
    enable_streaming: bool = True
    chunk_size: int = 8192

    # Monitoring settings
    enable_monitoring: bool = True
    monitor_sample_rate: float = 0.1  # Sample 10% of requests


@dataclass
class CompressionStats:
    """Statistics for compression operations."""

    timestamp: datetime
    algorithm: str
    original_size: int
    compressed_size: int
    compression_ratio: float
    compression_time_ms: float
    content_type: str
    user_agent: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "algorithm": self.algorithm,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "compression_ratio": self.compression_ratio,
            "compression_time_ms": self.compression_time_ms,
            "content_type": self.content_type,
            "user_agent": self.user_agent,
        }


class CompressionAlgorithm:
    """Base class for compression algorithms."""

    def __init__(self, name: str, level: int):
        self.name = name
        self.level = level

    def compress(self, data: bytes) -> bytes:
        """Compress data."""
        raise NotImplementedError

    def get_encoding_header(self) -> str:
        """Get the Content-Encoding header value."""
        raise NotImplementedError

    def estimate_ratio(self, content_type: str, size: int) -> float:
        """Estimate compression ratio for given content type and size."""
        # Basic estimates based on content type
        if "json" in content_type:
            return 0.3  # JSON compresses very well
        elif "html" in content_type:
            return 0.4  # HTML compresses well
        elif "css" in content_type or "javascript" in content_type:
            return 0.5  # CSS/JS compress well
        elif "text" in content_type:
            return 0.6  # General text
        else:
            return 0.8  # Conservative estimate


class BrotliAlgorithm(CompressionAlgorithm):
    """Brotli compression algorithm."""

    def __init__(self, level: int = 6):
        super().__init__("brotli", level)

    def compress(self, data: bytes) -> bytes:
        """Compress data using Brotli."""
        return brotli.compress(data, quality=self.level)

    def get_encoding_header(self) -> str:
        """Get the Content-Encoding header value."""
        return "br"

    def estimate_ratio(self, content_type: str, size: int) -> float:
        """Estimate Brotli compression ratio."""
        base_ratio = super().estimate_ratio(content_type, size)
        return base_ratio * 0.85  # Brotli typically 15% better than gzip


class GzipAlgorithm(CompressionAlgorithm):
    """Gzip compression algorithm."""

    def __init__(self, level: int = 6):
        super().__init__("gzip", level)

    def compress(self, data: bytes) -> bytes:
        """Compress data using Gzip."""
        buffer = BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=self.level) as gz_file:
            gz_file.write(data)
        return buffer.getvalue()

    def get_encoding_header(self) -> str:
        """Get the Content-Encoding header value."""
        return "gzip"


class DeflateAlgorithm(CompressionAlgorithm):
    """Deflate compression algorithm."""

    def __init__(self, level: int = 6):
        super().__init__("deflate", level)

    def compress(self, data: bytes) -> bytes:
        """Compress data using Deflate."""
        return zlib.compress(data, self.level)

    def get_encoding_header(self) -> str:
        """Get the Content-Encoding header value."""
        return "deflate"


class CompressionSelector:
    """Intelligent compression algorithm selector."""

    def __init__(self, config: CompressionConfig):
        self.config = config
        self.algorithms = {}

        # Initialize available algorithms
        if config.enable_brotli:
            self.algorithms["brotli"] = BrotliAlgorithm(config.brotli_level)
        if config.enable_gzip:
            self.algorithms["gzip"] = GzipAlgorithm(config.gzip_level)
        if config.enable_deflate:
            self.algorithms["deflate"] = DeflateAlgorithm(config.deflate_level)

    def select_algorithm(
        self, accept_encoding: str, content_type: str, content_length: int
    ) -> Optional[CompressionAlgorithm]:
        """Select the best compression algorithm based on client support and content."""
        if not accept_encoding:
            return None

        # Parse Accept-Encoding header
        accepted = self._parse_accept_encoding(accept_encoding)

        # Prioritize algorithms by effectiveness for content type
        if "brotli" in accepted and "brotli" in self.algorithms:
            return self.algorithms["brotli"]
        elif "gzip" in accepted and "gzip" in self.algorithms:
            return self.algorithms["gzip"]
        elif "deflate" in accepted and "deflate" in self.algorithms:
            return self.algorithms["deflate"]

        return None

    def _parse_accept_encoding(self, accept_encoding: str) -> list[str]:
        """Parse Accept-Encoding header."""
        accepted = []
        for encoding in accept_encoding.lower().split(","):
            encoding = encoding.strip()
            if ";" in encoding:
                encoding = encoding.split(";")[0].strip()

            # Map common variations
            if encoding in ["br"]:
                accepted.append("brotli")
            elif encoding in ["gzip", "x-gzip"]:
                accepted.append("gzip")
            elif encoding in ["deflate"]:
                accepted.append("deflate")

        return accepted


class PreCompressionManager:
    """Manage pre-compressed static assets."""

    def __init__(self, config: CompressionConfig):
        self.config = config
        self.static_dir = config.precompression_static_dir
        self.compressed_cache = {}  # Cache of pre-compressed files

    def get_precompressed_file(
        self, file_path: str, algorithm: CompressionAlgorithm
    ) -> Optional[str]:
        """Get path to pre-compressed file if available."""
        if not self.config.enable_precompression:
            return None

        # Generate compressed file path
        if algorithm.name == "brotli":
            compressed_path = file_path + ".br"
        elif algorithm.name == "gzip":
            compressed_path = file_path + ".gz"
        else:
            return None  # Only support brotli and gzip precompression

        # Check if pre-compressed file exists and is newer
        if os.path.exists(compressed_path):
            original_mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else 0
            compressed_mtime = os.path.getmtime(compressed_path)

            if compressed_mtime >= original_mtime:
                return compressed_path

        return None

    def create_precompressed_files(self, static_dir: str = None):
        """Create pre-compressed versions of static files."""
        if static_dir is None:
            static_dir = self.static_dir

        if not os.path.exists(static_dir):
            logger.warning(f"Static directory {static_dir} does not exist")
            return

        compressible_extensions = [".js", ".css", ".html", ".xml", ".json", ".svg"]

        for root, dirs, files in os.walk(static_dir):
            for file in files:
                file_path = os.path.join(root, file)
                _, ext = os.path.splitext(file)

                if ext.lower() in compressible_extensions:
                    self._create_compressed_versions(file_path)

    def _create_compressed_versions(self, file_path: str):
        """Create compressed versions of a single file."""
        try:
            with open(file_path, "rb") as f:
                data = f.read()

            # Create Brotli version
            if self.config.enable_brotli:
                brotli_data = brotli.compress(data, quality=self.config.brotli_level)
                with open(file_path + ".br", "wb") as f:
                    f.write(brotli_data)

            # Create Gzip version
            if self.config.enable_gzip:
                gzip_data = gzip.compress(data, compresslevel=self.config.gzip_level)
                with open(file_path + ".gz", "wb") as f:
                    f.write(gzip_data)

            logger.debug(f"Created compressed versions for {file_path}")

        except Exception as e:
            logger.error(f"Error creating compressed versions for {file_path}: {e}")


class CompressionMonitor:
    """Monitor compression performance and statistics."""

    def __init__(self, config: CompressionConfig):
        self.config = config
        self.stats_history = []
        self.max_history = 10000

        # Aggregate statistics
        self.total_requests = 0
        self.compressed_requests = 0
        self.total_original_bytes = 0
        self.total_compressed_bytes = 0
        self.algorithm_usage = {"brotli": 0, "gzip": 0, "deflate": 0}

    def record_compression(self, stats: CompressionStats):
        """Record compression statistics."""
        if not self.config.enable_monitoring:
            return

        # Store individual stats (with sampling)
        if len(self.stats_history) < self.max_history and (
            self.config.monitor_sample_rate >= 1.0
            or hash(stats.timestamp) % 100 < self.config.monitor_sample_rate * 100
        ):
            self.stats_history.append(stats)

        # Update aggregates
        self.total_requests += 1
        self.compressed_requests += 1
        self.total_original_bytes += stats.original_size
        self.total_compressed_bytes += stats.compressed_size
        self.algorithm_usage[stats.algorithm] += 1

    def record_uncompressed(self, size: int, reason: str):
        """Record uncompressed response."""
        self.total_requests += 1
        # Could add reasons tracking if needed

    def get_statistics(self) -> dict[str, Any]:
        """Get comprehensive compression statistics."""
        if self.total_requests == 0:
            return {}

        compression_rate = self.compressed_requests / self.total_requests
        overall_ratio = (
            self.total_compressed_bytes / self.total_original_bytes
            if self.total_original_bytes > 0
            else 1.0
        )

        # Recent performance (last 100 compressions)
        recent_stats = self.stats_history[-100:] if self.stats_history else []
        avg_compression_time = (
            sum(s.compression_time_ms for s in recent_stats) / len(recent_stats)
            if recent_stats
            else 0
        )

        return {
            "total_requests": self.total_requests,
            "compressed_requests": self.compressed_requests,
            "compression_rate": compression_rate,
            "overall_compression_ratio": overall_ratio,
            "bytes_saved": self.total_original_bytes - self.total_compressed_bytes,
            "average_compression_time_ms": avg_compression_time,
            "algorithm_usage": self.algorithm_usage.copy(),
            "recent_compressions": len(recent_stats),
        }

    def get_detailed_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get detailed compression history."""
        return [stats.to_dict() for stats in self.stats_history[-limit:]]


class CompressionMiddleware:
    """Main compression middleware."""

    def __init__(self, app: Flask = None, config: CompressionConfig = None):
        self.config = config or CompressionConfig()
        self.selector = CompressionSelector(self.config)
        self.precompression = PreCompressionManager(self.config)
        self.monitor = CompressionMonitor(self.config)

        if app:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initialize middleware with Flask app."""
        app.after_request(self.after_request)

        # Store reference for access in views
        app.compression_middleware = self

        # Create pre-compressed files if enabled
        if self.config.enable_precompression:
            try:
                self.precompression.create_precompressed_files()
            except Exception as e:
                logger.warning(f"Could not create pre-compressed files: {e}")

    def after_request(self, response: Response) -> Response:
        """Process response for compression."""
        try:
            return self._compress_response(response)
        except Exception as e:
            logger.error(f"Error in compression middleware: {e}")
            return response

    def _compress_response(self, response: Response) -> Response:
        """Compress response if appropriate."""
        # Skip if already compressed
        if response.headers.get("Content-Encoding"):
            return response

        # Skip if no content
        if not response.data or response.status_code != 200:
            return response

        # Check content type
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
        if not self._is_compressible_type(content_type):
            self.monitor.record_uncompressed(len(response.data), "non-compressible-type")
            return response

        # Check size constraints
        content_length = len(response.data)
        if content_length < self.config.min_size:
            self.monitor.record_uncompressed(content_length, "too-small")
            return response
        if content_length > self.config.max_size:
            self.monitor.record_uncompressed(content_length, "too-large")
            return response

        # Select compression algorithm
        accept_encoding = request.headers.get("Accept-Encoding", "")
        algorithm = self.selector.select_algorithm(accept_encoding, content_type, content_length)

        if not algorithm:
            self.monitor.record_uncompressed(content_length, "no-supported-algorithm")
            return response

        # Perform compression
        start_time = time.time()
        try:
            compressed_data = algorithm.compress(response.data)
            compression_time = (time.time() - start_time) * 1000

            # Update response
            response.data = compressed_data
            response.headers["Content-Encoding"] = algorithm.get_encoding_header()
            response.headers["Content-Length"] = str(len(compressed_data))

            # Add Vary header for caching
            vary_header = response.headers.get("Vary", "")
            if "Accept-Encoding" not in vary_header:
                if vary_header:
                    vary_header += ", Accept-Encoding"
                else:
                    vary_header = "Accept-Encoding"
                response.headers["Vary"] = vary_header

            # Record statistics
            stats = CompressionStats(
                timestamp=datetime.now(),
                algorithm=algorithm.name,
                original_size=content_length,
                compressed_size=len(compressed_data),
                compression_ratio=len(compressed_data) / content_length,
                compression_time_ms=compression_time,
                content_type=content_type,
                user_agent=request.headers.get("User-Agent", "")[:100],  # Truncate
            )
            self.monitor.record_compression(stats)

            return response

        except Exception as e:
            logger.error(f"Compression failed: {e}")
            self.monitor.record_uncompressed(content_length, "compression-error")
            return response

    def _is_compressible_type(self, content_type: str) -> bool:
        """Check if content type is compressible."""
        return any(comp_type in content_type for comp_type in self.config.compressible_types)

    def get_statistics(self) -> dict[str, Any]:
        """Get compression statistics."""
        return self.monitor.get_statistics()

    def get_detailed_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get detailed compression history."""
        return self.monitor.get_detailed_history(limit)


# Decorator for manual compression control
def compress_response(algorithm: str = None, level: int = None):
    """Decorator to manually control response compression."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Set compression preferences in Flask g object
            g.compression_algorithm = algorithm
            g.compression_level = level
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Global middleware instance
_compression_middleware = None


def init_compression(app: Flask, config: CompressionConfig = None) -> CompressionMiddleware:
    """Initialize compression middleware."""
    global _compression_middleware
    _compression_middleware = CompressionMiddleware(app, config)
    return _compression_middleware


def get_compression_middleware() -> Optional[CompressionMiddleware]:
    """Get the global compression middleware instance."""
    return _compression_middleware


def get_compression_stats() -> dict[str, Any]:
    """Get compression statistics."""
    if _compression_middleware:
        return _compression_middleware.get_statistics()
    return {}


if __name__ == "__main__":
    # Example usage
    from flask import Flask, jsonify

    app = Flask(__name__)

    # Initialize compression with custom config
    config = CompressionConfig(brotli_level=8, gzip_level=7, min_size=500)

    compression = init_compression(app, config)

    @app.route("/")
    def home():
        return "Hello World! " * 1000  # Large enough to compress

    @app.route("/api/large-data")
    @compress_response(algorithm="brotli", level=9)
    def large_data():
        return jsonify(
            {
                "data": ["item"] * 10000,
                "message": "This is a large JSON response that should compress well",
            }
        )

    @app.route("/compression/stats")
    def compression_stats():
        return jsonify(get_compression_stats())

    app.run(debug=True)
