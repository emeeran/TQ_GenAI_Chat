"""
Security Module for TQ GenAI Chat
Implements comprehensive security measures for production deployment
"""

import hashlib
import hmac
import logging
import os
import secrets
import time
from functools import wraps
from typing import Any, Dict, Optional

from flask import Flask, request, jsonify, g
import redis
from werkzeug.security import check_password_hash, generate_password_hash

logger = logging.getLogger(__name__)


class SecurityManager:
    """Centralized security management"""
    
    def __init__(self, app: Optional[Flask] = None, redis_client: Optional[redis.Redis] = None):
        self.app = app
        self.redis_client = redis_client
        self.rate_limits = {}
        self.blocked_ips = set()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize security for Flask app"""
        self.app = app
        
        # Configure security headers
        @app.after_request
        def add_security_headers(response):
            return self._add_security_headers(response)
        
        # Configure request validation
        @app.before_request
        def validate_request():
            return self._validate_request()
    
    def _add_security_headers(self, response):
        """Add comprehensive security headers"""
        # Prevent XSS attacks
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://fonts.gstatic.com; "
            "connect-src 'self';"
        )
        response.headers['Content-Security-Policy'] = csp
        
        # Other security headers
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # HSTS (if HTTPS)
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # Remove server information
        response.headers.pop('Server', None)
        
        return response
    
    def _validate_request(self):
        """Validate incoming requests"""
        client_ip = self._get_client_ip()
        
        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            logger.warning(f"Blocked IP attempted access: {client_ip}")
            return jsonify({'error': 'Access denied'}), 403
        
        # Rate limiting
        if self._is_rate_limited(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return jsonify({'error': 'Rate limit exceeded'}), 429
        
        # Validate request size
        if request.content_length and request.content_length > 64 * 1024 * 1024:  # 64MB
            return jsonify({'error': 'Request too large'}), 413
        
        # Store client info for logging
        g.client_ip = client_ip
        g.user_agent = request.headers.get('User-Agent', '')
    
    def _get_client_ip(self) -> str:
        """Get real client IP address"""
        # Check for forwarded headers (from reverse proxy)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.remote_addr or '127.0.0.1'
    
    def _is_rate_limited(self, client_ip: str) -> bool:
        """Check if client is rate limited"""
        if not self.redis_client:
            return False
        
        current_time = int(time.time())
        window = 60  # 1 minute window
        limit = 60   # 60 requests per minute
        
        key = f"rate_limit:{client_ip}:{current_time // window}"
        
        try:
            current_requests = self.redis_client.incr(key)
            if current_requests == 1:
                self.redis_client.expire(key, window)
            
            return current_requests > limit
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            return False
    
    def block_ip(self, ip: str, duration: int = 3600):
        """Block an IP address"""
        self.blocked_ips.add(ip)
        
        if self.redis_client:
            try:
                self.redis_client.setex(f"blocked_ip:{ip}", duration, "1")
            except Exception as e:
                logger.error(f"Error blocking IP in Redis: {e}")
    
    def unblock_ip(self, ip: str):
        """Unblock an IP address"""
        self.blocked_ips.discard(ip)
        
        if self.redis_client:
            try:
                self.redis_client.delete(f"blocked_ip:{ip}")
            except Exception as e:
                logger.error(f"Error unblocking IP in Redis: {e}")


class APIKeyManager:
    """Manage API keys securely"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.api_keys = {}
    
    def generate_api_key(self, user_id: str, permissions: list = None) -> str:
        """Generate a new API key"""
        api_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        key_data = {
            'user_id': user_id,
            'permissions': permissions or [],
            'created_at': int(time.time()),
            'last_used': None,
            'usage_count': 0
        }
        
        if self.redis_client:
            try:
                self.redis_client.hset(f"api_key:{key_hash}", mapping=key_data)
            except Exception as e:
                logger.error(f"Error storing API key: {e}")
        
        self.api_keys[key_hash] = key_data
        return api_key
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate an API key"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Try Redis first
        if self.redis_client:
            try:
                key_data = self.redis_client.hgetall(f"api_key:{key_hash}")
                if key_data:
                    # Update last used
                    self.redis_client.hset(f"api_key:{key_hash}", 'last_used', int(time.time()))
                    self.redis_client.hincrby(f"api_key:{key_hash}", 'usage_count', 1)
                    return {k.decode(): v.decode() for k, v in key_data.items()}
            except Exception as e:
                logger.error(f"Error validating API key: {e}")
        
        # Fallback to memory
        key_data = self.api_keys.get(key_hash)
        if key_data:
            key_data['last_used'] = int(time.time())
            key_data['usage_count'] += 1
        
        return key_data
    
    def revoke_api_key(self, api_key: str):
        """Revoke an API key"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        if self.redis_client:
            try:
                self.redis_client.delete(f"api_key:{key_hash}")
            except Exception as e:
                logger.error(f"Error revoking API key: {e}")
        
        self.api_keys.pop(key_hash, None)


def require_api_key(permissions: list = None):
    """Decorator to require API key authentication"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get('X-API-Key')
            if not api_key:
                return jsonify({'error': 'API key required'}), 401
            
            # Validate API key (implement your validation logic)
            if not _validate_api_key(api_key, permissions):
                return jsonify({'error': 'Invalid API key'}), 401
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def _validate_api_key(api_key: str, required_permissions: list = None) -> bool:
    """Validate API key (placeholder implementation)"""
    # Implement your API key validation logic here
    # This is a simple example - use proper validation in production
    valid_keys = os.getenv('VALID_API_KEYS', '').split(',')
    return api_key in valid_keys


class InputSanitizer:
    """Sanitize user inputs"""
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal"""
        # Remove path separators and dangerous characters
        filename = filename.replace('/', '').replace('\\', '')
        filename = filename.replace('..', '')
        
        # Remove null bytes
        filename = filename.replace('\x00', '')
        
        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255-len(ext)] + ext
        
        return filename
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 10000) -> str:
        """Sanitize text input"""
        if not isinstance(text, str):
            return ""
        
        # Remove null bytes and control characters
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        # Limit length
        if len(text) > max_length:
            text = text[:max_length]
        
        return text.strip()
    
    @staticmethod
    def validate_json_input(data: dict, required_fields: list = None) -> tuple[bool, str]:
        """Validate JSON input"""
        if not isinstance(data, dict):
            return False, "Invalid JSON format"
        
        if required_fields:
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return False, f"Missing required fields: {', '.join(missing_fields)}"
        
        return True, ""


class SessionManager:
    """Manage user sessions securely"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.sessions = {}
    
    def create_session(self, user_id: str, data: dict = None) -> str:
        """Create a new session"""
        session_id = secrets.token_urlsafe(32)
        session_data = {
            'user_id': user_id,
            'created_at': int(time.time()),
            'last_activity': int(time.time()),
            'data': data or {}
        }
        
        if self.redis_client:
            try:
                self.redis_client.setex(
                    f"session:{session_id}", 
                    3600,  # 1 hour expiry
                    str(session_data)
                )
            except Exception as e:
                logger.error(f"Error creating session: {e}")
        
        self.sessions[session_id] = session_data
        return session_id
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data"""
        if self.redis_client:
            try:
                session_data = self.redis_client.get(f"session:{session_id}")
                if session_data:
                    return eval(session_data.decode())  # Use proper JSON in production
            except Exception as e:
                logger.error(f"Error getting session: {e}")
        
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, data: dict):
        """Update session data"""
        session_data = self.get_session(session_id)
        if session_data:
            session_data['last_activity'] = int(time.time())
            session_data['data'].update(data)
            
            if self.redis_client:
                try:
                    self.redis_client.setex(
                        f"session:{session_id}", 
                        3600,
                        str(session_data)
                    )
                except Exception as e:
                    logger.error(f"Error updating session: {e}")
            
            self.sessions[session_id] = session_data
    
    def delete_session(self, session_id: str):
        """Delete a session"""
        if self.redis_client:
            try:
                self.redis_client.delete(f"session:{session_id}")
            except Exception as e:
                logger.error(f"Error deleting session: {e}")
        
        self.sessions.pop(session_id, None)


# Global security manager instance
security_manager = SecurityManager()
api_key_manager = APIKeyManager()
session_manager = SessionManager()
input_sanitizer = InputSanitizer()