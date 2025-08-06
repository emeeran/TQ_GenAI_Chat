"""
Security enhancements for TQ GenAI Chat application including
API key management, rate limiting, input validation, and audit logging.
"""

import hashlib
import hmac
import json
import logging
import re
import secrets
import time
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any

try:
    import base64

    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class SecurityEvent:
    """Security event for audit logging."""

    timestamp: float
    event_type: str
    user_id: str
    ip_address: str
    details: dict[str, Any]
    severity: str = "INFO"  # INFO, WARNING, ERROR, CRITICAL


class APIKeyManager:
    """
    Secure API key management with encryption and rotation.
    """

    def __init__(self, master_key: str = None):
        if not CRYPTO_AVAILABLE:
            raise ImportError("cryptography library required for API key encryption")

        self.master_key = master_key or self._generate_master_key()
        self.fernet = self._create_fernet()
        self.keys_file = Path("secure_keys.json")
        self.encrypted_keys: dict[str, str] = {}
        self._load_keys()

    def _generate_master_key(self) -> str:
        """Generate a new master key."""
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()

    def _create_fernet(self) -> Fernet:
        """Create Fernet encryption instance."""
        # Derive key from master key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"tq_genai_chat_salt",  # In production, use random salt
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
        return Fernet(key)

    def _load_keys(self):
        """Load encrypted keys from file."""
        if self.keys_file.exists():
            try:
                with open(self.keys_file) as f:
                    self.encrypted_keys = json.load(f)
                logger.info(f"Loaded {len(self.encrypted_keys)} encrypted API keys")
            except Exception as e:
                logger.error(f"Failed to load API keys: {e}")
                self.encrypted_keys = {}

    def _save_keys(self):
        """Save encrypted keys to file."""
        try:
            with open(self.keys_file, "w") as f:
                json.dump(self.encrypted_keys, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save API keys: {e}")

    def store_api_key(self, provider: str, api_key: str) -> bool:
        """Store an encrypted API key."""
        try:
            encrypted_key = self.fernet.encrypt(api_key.encode()).decode()
            self.encrypted_keys[provider] = encrypted_key
            self._save_keys()
            logger.info(f"Stored encrypted API key for {provider}")
            return True
        except Exception as e:
            logger.error(f"Failed to store API key for {provider}: {e}")
            return False

    def get_api_key(self, provider: str) -> str:
        """Retrieve and decrypt an API key."""
        if provider not in self.encrypted_keys:
            return ""

        try:
            encrypted_key = self.encrypted_keys[provider]
            decrypted_key = self.fernet.decrypt(encrypted_key.encode()).decode()
            return decrypted_key
        except Exception as e:
            logger.error(f"Failed to decrypt API key for {provider}: {e}")
            return ""

    def rotate_api_key(self, provider: str, new_key: str) -> bool:
        """Rotate an API key."""
        old_key_exists = provider in self.encrypted_keys
        success = self.store_api_key(provider, new_key)

        if success and old_key_exists:
            logger.info(f"Rotated API key for {provider}")

        return success

    def delete_api_key(self, provider: str) -> bool:
        """Delete an API key."""
        if provider in self.encrypted_keys:
            del self.encrypted_keys[provider]
            self._save_keys()
            logger.info(f"Deleted API key for {provider}")
            return True
        return False

    def list_providers(self) -> list[str]:
        """List all providers with stored keys."""
        return list(self.encrypted_keys.keys())


class RateLimiter:
    """
    Advanced rate limiting with multiple strategies.
    """

    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.local_cache: dict[str, dict] = {}
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()

    def _get_current_time(self) -> float:
        """Get current timestamp."""
        return time.time()

    def _cleanup_local_cache(self):
        """Clean up expired entries from local cache."""
        current_time = self._get_current_time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return

        expired_keys = []
        for key, data in self.local_cache.items():
            if data.get("expires", 0) < current_time:
                expired_keys.append(key)

        for key in expired_keys:
            del self.local_cache[key]

        self.last_cleanup = current_time

    def check_rate_limit(
        self, identifier: str, limit: int, window_seconds: int, burst_limit: int = None
    ) -> tuple[bool, dict[str, Any]]:
        """
        Check if request is within rate limits.
        Returns (allowed, info) where info contains current usage.
        """
        current_time = self._get_current_time()
        window_start = current_time - window_seconds

        if self.redis_client:
            return self._check_rate_limit_redis(
                identifier, limit, window_seconds, burst_limit, current_time
            )
        else:
            return self._check_rate_limit_local(
                identifier,
                limit,
                window_seconds,
                burst_limit,
                current_time,
                window_start,
            )

    def _check_rate_limit_redis(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
        burst_limit: int,
        current_time: float,
    ) -> tuple[bool, dict[str, Any]]:
        """Redis-based rate limiting using sliding window."""
        try:
            pipe = self.redis_client.pipeline()
            key = f"rate_limit:{identifier}"

            # Remove old entries
            pipe.zremrangebyscore(key, 0, current_time - window_seconds)

            # Count current requests
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(current_time): current_time})

            # Set expiration
            pipe.expire(key, window_seconds + 1)

            results = pipe.execute()
            current_count = results[1]

            # Check burst limit
            if burst_limit and current_count >= burst_limit:
                return False, {
                    "allowed": False,
                    "current_count": current_count,
                    "limit": limit,
                    "burst_limit": burst_limit,
                    "window_seconds": window_seconds,
                    "retry_after": window_seconds,
                }

            # Check regular limit
            allowed = current_count < limit

            return allowed, {
                "allowed": allowed,
                "current_count": current_count,
                "limit": limit,
                "window_seconds": window_seconds,
                "retry_after": window_seconds if not allowed else 0,
            }

        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            # Fallback to local cache
            return self._check_rate_limit_local(
                identifier,
                limit,
                window_seconds,
                burst_limit,
                current_time,
                current_time - window_seconds,
            )

    def _check_rate_limit_local(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
        burst_limit: int,
        current_time: float,
        window_start: float,
    ) -> tuple[bool, dict[str, Any]]:
        """Local cache-based rate limiting."""
        self._cleanup_local_cache()

        if identifier not in self.local_cache:
            self.local_cache[identifier] = {
                "requests": [],
                "expires": current_time + window_seconds,
            }

        data = self.local_cache[identifier]

        # Remove old requests
        data["requests"] = [req_time for req_time in data["requests"] if req_time > window_start]

        # Check burst limit
        if burst_limit and len(data["requests"]) >= burst_limit:
            return False, {
                "allowed": False,
                "current_count": len(data["requests"]),
                "limit": limit,
                "burst_limit": burst_limit,
                "window_seconds": window_seconds,
                "retry_after": window_seconds,
            }

        # Check regular limit
        allowed = len(data["requests"]) < limit

        if allowed:
            data["requests"].append(current_time)
            data["expires"] = current_time + window_seconds

        return allowed, {
            "allowed": allowed,
            "current_count": len(data["requests"]),
            "limit": limit,
            "window_seconds": window_seconds,
            "retry_after": window_seconds if not allowed else 0,
        }


class InputValidator:
    """
    Input validation and sanitization for security.
    """

    def __init__(self):
        # Patterns for validation
        self.email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        self.filename_pattern = re.compile(r"^[a-zA-Z0-9._-]+$")
        self.safe_text_pattern = re.compile(r'^[a-zA-Z0-9\s.,!?;:()\'"@#$%&*+=\-_/\\]+$')

        # SQL injection patterns
        self.sql_injection_patterns = [
            re.compile(
                r"(\bUNION\b|\bSELECT\b|\bINSERT\b|\bDELETE\b|\bUPDATE\b|\bDROP\b)",
                re.IGNORECASE,
            ),
            re.compile(r"(--|#|/\*|\*/)", re.IGNORECASE),
            re.compile(r"(\bOR\b\s+\d+\s*=\s*\d+|\bAND\b\s+\d+\s*=\s*\d+)", re.IGNORECASE),
        ]

        # XSS patterns
        self.xss_patterns = [
            re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
            re.compile(r"javascript:", re.IGNORECASE),
            re.compile(r"on\w+\s*=", re.IGNORECASE),
            re.compile(r"<iframe[^>]*>.*?</iframe>", re.IGNORECASE | re.DOTALL),
        ]

    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        if not email or len(email) > 254:
            return False
        return bool(self.email_pattern.match(email))

    def validate_filename(self, filename: str) -> bool:
        """Validate filename for security."""
        if not filename or len(filename) > 255:
            return False

        # Check for path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            return False

        return bool(self.filename_pattern.match(filename))

    def sanitize_text(self, text: str, max_length: int = 10000) -> str:
        """Sanitize text input."""
        if not isinstance(text, str):
            return ""

        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]

        # Remove null bytes
        text = text.replace("\x00", "")

        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def check_sql_injection(self, text: str) -> bool:
        """Check for SQL injection patterns."""
        for pattern in self.sql_injection_patterns:
            if pattern.search(text):
                return True
        return False

    def check_xss(self, text: str) -> bool:
        """Check for XSS patterns."""
        for pattern in self.xss_patterns:
            if pattern.search(text):
                return True
        return False

    def validate_api_input(self, data: dict) -> tuple[bool, list[str]]:
        """Validate API input data."""
        errors = []

        # Check for required fields
        if "message" not in data:
            errors.append("Message is required")

        # Validate message
        if "message" in data:
            message = data["message"]
            if not isinstance(message, str):
                errors.append("Message must be a string")
            elif len(message) == 0:
                errors.append("Message cannot be empty")
            elif len(message) > 50000:  # 50KB limit
                errors.append("Message too long")
            elif self.check_sql_injection(message):
                errors.append("Message contains potentially malicious content")
            elif self.check_xss(message):
                errors.append("Message contains potentially malicious content")

        # Validate provider
        if "provider" in data:
            provider = data["provider"]
            if not isinstance(provider, str) or not provider.isalnum():
                errors.append("Invalid provider")

        # Validate model
        if "model" in data:
            model = data["model"]
            if not isinstance(model, str) or len(model) > 100:
                errors.append("Invalid model")

        return len(errors) == 0, errors


class SecurityAuditor:
    """
    Security audit logging and monitoring.
    """

    def __init__(self, log_file: str = "security_audit.log"):
        self.log_file = Path(log_file)
        self.events: list[SecurityEvent] = []
        self.max_events = 10000

        # Setup audit logger
        self.audit_logger = logging.getLogger("security_audit")
        handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.audit_logger.addHandler(handler)
        self.audit_logger.setLevel(logging.INFO)

    def log_event(
        self,
        event_type: str,
        user_id: str,
        ip_address: str,
        details: dict[str, Any],
        severity: str = "INFO",
    ):
        """Log a security event."""
        event = SecurityEvent(
            timestamp=time.time(),
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            details=details,
            severity=severity,
        )

        # Add to memory
        self.events.append(event)
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events :]

        # Log to file
        log_message = json.dumps(
            {
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "user_id": event.user_id,
                "ip_address": event.ip_address,
                "details": event.details,
                "severity": event.severity,
            }
        )

        if severity == "CRITICAL":
            self.audit_logger.critical(log_message)
        elif severity == "ERROR":
            self.audit_logger.error(log_message)
        elif severity == "WARNING":
            self.audit_logger.warning(log_message)
        else:
            self.audit_logger.info(log_message)

    def log_failed_login(self, user_id: str, ip_address: str, reason: str):
        """Log failed login attempt."""
        self.log_event("FAILED_LOGIN", user_id, ip_address, {"reason": reason}, "WARNING")

    def log_rate_limit_exceeded(self, user_id: str, ip_address: str, endpoint: str):
        """Log rate limit exceeded."""
        self.log_event(
            "RATE_LIMIT_EXCEEDED",
            user_id,
            ip_address,
            {"endpoint": endpoint},
            "WARNING",
        )

    def log_suspicious_input(self, user_id: str, ip_address: str, input_type: str, content: str):
        """Log suspicious input detected."""
        self.log_event(
            "SUSPICIOUS_INPUT",
            user_id,
            ip_address,
            {"input_type": input_type, "content": content[:100]},
            "ERROR",
        )

    def log_api_key_access(self, user_id: str, ip_address: str, provider: str, action: str):
        """Log API key access."""
        self.log_event(
            "API_KEY_ACCESS",
            user_id,
            ip_address,
            {"provider": provider, "action": action},
            "INFO",
        )

    def get_recent_events(self, hours: int = 24, severity: str = None) -> list[SecurityEvent]:
        """Get recent security events."""
        cutoff_time = time.time() - (hours * 3600)

        recent_events = [event for event in self.events if event.timestamp >= cutoff_time]

        if severity:
            recent_events = [event for event in recent_events if event.severity == severity]

        return recent_events

    def detect_anomalies(self) -> list[dict[str, Any]]:
        """Detect security anomalies."""
        anomalies = []
        recent_events = self.get_recent_events(hours=1)

        # Count events by type
        event_counts = {}
        ip_counts = {}
        user_counts = {}

        for event in recent_events:
            event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
            ip_counts[event.ip_address] = ip_counts.get(event.ip_address, 0) + 1
            user_counts[event.user_id] = user_counts.get(event.user_id, 0) + 1

        # Check for anomalies

        # Too many failed logins
        if event_counts.get("FAILED_LOGIN", 0) > 10:
            anomalies.append(
                {
                    "type": "EXCESSIVE_FAILED_LOGINS",
                    "count": event_counts["FAILED_LOGIN"],
                    "severity": "HIGH",
                }
            )

        # Too many requests from single IP
        for ip, count in ip_counts.items():
            if count > 100:  # More than 100 events per hour
                anomalies.append(
                    {
                        "type": "EXCESSIVE_REQUESTS_FROM_IP",
                        "ip_address": ip,
                        "count": count,
                        "severity": "MEDIUM",
                    }
                )

        # Too many rate limit violations
        if event_counts.get("RATE_LIMIT_EXCEEDED", 0) > 20:
            anomalies.append(
                {
                    "type": "EXCESSIVE_RATE_LIMITING",
                    "count": event_counts["RATE_LIMIT_EXCEEDED"],
                    "severity": "MEDIUM",
                }
            )

        return anomalies


class SecurityManager:
    """
    Main security manager that coordinates all security components.
    """

    def __init__(self, master_key: str = None, redis_client=None):
        self.api_key_manager = APIKeyManager(master_key) if CRYPTO_AVAILABLE else None
        self.rate_limiter = RateLimiter(redis_client)
        self.input_validator = InputValidator()
        self.auditor = SecurityAuditor()

        if not CRYPTO_AVAILABLE:
            logger.warning("Cryptography not available - API key encryption disabled")

    def get_api_key(self, provider: str) -> str:
        """Get API key for provider."""
        if self.api_key_manager:
            return self.api_key_manager.get_api_key(provider)
        return ""

    def validate_request(
        self,
        user_id: str,
        ip_address: str,
        endpoint: str,
        data: dict,
        rate_limit: int = 60,
    ) -> tuple[bool, str]:
        """Validate incoming request."""

        # Rate limiting
        allowed, rate_info = self.rate_limiter.check_rate_limit(
            f"{user_id}:{ip_address}",
            rate_limit,
            60,  # 1 minute window
        )

        if not allowed:
            self.auditor.log_rate_limit_exceeded(user_id, ip_address, endpoint)
            return (
                False,
                f"Rate limit exceeded. Try again in {rate_info['retry_after']} seconds.",
            )

        # Input validation
        valid, errors = self.input_validator.validate_api_input(data)
        if not valid:
            self.auditor.log_suspicious_input(user_id, ip_address, "API_INPUT", str(errors))
            return False, f"Invalid input: {'; '.join(errors)}"

        return True, "OK"

    def create_session_token(self, user_id: str) -> str:
        """Create secure session token."""
        timestamp = str(int(time.time()))
        data = f"{user_id}:{timestamp}"

        # Create HMAC signature
        secret_key = secrets.token_urlsafe(32)
        signature = hmac.new(secret_key.encode(), data.encode(), hashlib.sha256).hexdigest()

        return f"{data}:{signature}:{secret_key}"

    def verify_session_token(self, token: str, max_age: int = 3600) -> tuple[bool, str]:
        """Verify session token."""
        try:
            parts = token.split(":")
            if len(parts) != 4:
                return False, ""

            user_id, timestamp, signature, secret_key = parts

            # Check age
            token_time = int(timestamp)
            if time.time() - token_time > max_age:
                return False, ""

            # Verify signature
            data = f"{user_id}:{timestamp}"
            expected_signature = hmac.new(
                secret_key.encode(), data.encode(), hashlib.sha256
            ).hexdigest()

            if hmac.compare_digest(signature, expected_signature):
                return True, user_id

            return False, ""

        except Exception:
            return False, ""


# Decorators for easy security integration


def require_rate_limit(limit: int = 60, window: int = 60):
    """Decorator for rate limiting."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # This would need to be integrated with Flask request context
            # Implementation depends on specific framework integration
            return func(*args, **kwargs)

        return wrapper

    return decorator


def validate_input(validator_func: Callable = None):
    """Decorator for input validation."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # This would need to be integrated with Flask request context
            # Implementation depends on specific framework integration
            return func(*args, **kwargs)

        return wrapper

    return decorator


# Global security manager instance
_security_manager = None


def get_security_manager(master_key: str = None, redis_client=None) -> SecurityManager:
    """Get or create the global security manager instance."""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager(master_key, redis_client)
    return _security_manager
