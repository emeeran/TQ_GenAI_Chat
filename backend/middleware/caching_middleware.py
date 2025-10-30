"""
Caching Middleware - Zero Risk Enhancement

FastAPI middleware for adding browser caching headers.
Improves performance for repeat visits without affecting functionality.
"""

import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CachingMiddleware(BaseHTTPMiddleware):
    """
    Zero-risk caching middleware.

    Adds appropriate caching headers for different types of content:
    - Static assets (CSS, JS, images): Long-term caching
    - API responses: Short-term or no caching
    - HTML pages: Moderate caching with validation

    Does not modify response content, only adds headers.
    """

    def __init__(self, app):
        super().__init__(app)
        # Define caching strategies for different content types
        self.cache_directives = {
            # Static assets - long cache (1 year)
            'text/css': 'public, max-age=31536000, immutable',
            'application/javascript': 'public, max-age=31536000, immutable',
            'text/javascript': 'public, max-age=31536000, immutable',
            'image/png': 'public, max-age=31536000, immutable',
            'image/jpeg': 'public, max-age=31536000, immutable',
            'image/gif': 'public, max-age=31536000, immutable',
            'image/webp': 'public, max-age=31536000, immutable',
            'image/svg+xml': 'public, max-age=31536000, immutable',
            'image/x-icon': 'public, max-age=31536000, immutable',
            'font/woff': 'public, max-age=31536000, immutable',
            'font/woff2': 'public, max-age=31536000, immutable',
            'application/font-woff': 'public, max-age=31536000, immutable',
            'application/font-woff2': 'public, max-age=31536000, immutable',

            # HTML pages - moderate cache with validation (1 hour)
            'text/html': 'public, max-age=3600, must-revalidate',

            # API responses - short cache or no cache
            'application/json': 'no-cache, no-store, must-revalidate',
            'application/problem+json': 'no-cache, no-store, must-revalidate',

            # Default - moderate cache
            'default': 'public, max-age=3600'
        }

        # Paths that should never be cached
        self.no_cache_paths = {
            '/health', '/metrics', '/chat', '/documents', '/files'
        }

        logger.info("Caching middleware initialized - zero risk performance enhancement")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add appropriate caching headers.
        Zero-risk: always passes through the original call_next().
        """
        # Process the request normally
        response = await call_next(request)

        # Skip caching for certain paths
        if request.url.path in self.no_cache_paths:
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response

        # Get content type from response
        content_type = response.headers.get('content-type', '').split(';')[0].strip()

        # Determine appropriate cache directive
        cache_directive = self.cache_directives.get(content_type, self.cache_directives['default'])

        # Add caching headers
        response.headers['Cache-Control'] = cache_directive

        # Add additional headers for better caching
        if 'immutable' in cache_directive:
            # For immutable assets, add a far-future expires header
            future_date = datetime.utcnow() + timedelta(days=365)
            response.headers['Expires'] = future_date.strftime('%a, %d %b %Y %H:%M:%S GMT')

        # Add ETag for response validation if not already present
        if 'ETag' not in response.headers and content_type.startswith('text/html'):
            # Generate simple ETag based on content length and current time
            content_length = response.headers.get('content-length', '0')
            etag = f'"{content_length}-{int(datetime.utcnow().timestamp())}"'
            response.headers['ETag'] = etag

        # Add Vary header for proper caching with compression
        if 'Vary' not in response.headers:
            response.headers['Vary'] = 'Accept-Encoding'

        # Add Last-Modified header for HTML responses
        if content_type.startswith('text/html') and 'Last-Modified' not in response.headers:
            response.headers['Last-Modified'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')

        return response


class ResourceHintsMiddleware(BaseHTTPMiddleware):
    """
    Zero-risk resource hints middleware.

    Adds resource hints (preconnect, prefetch) to improve performance.
    Only affects HTML responses and adds hints via Link headers.
    """

    def __init__(self, app):
        super().__init__(app)
        # Define external resources that should be preconnected
        self.preconnect_domains = [
            'https://fonts.googleapis.com',
            'https://fonts.gstatic.com',
            'https://cdn.jsdelivr.net',
        ]

        logger.info("Resource hints middleware initialized - zero risk enhancement")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add resource hints for HTML responses."""
        response = await call_next(request)

        # Only add hints to HTML responses
        content_type = response.headers.get('content-type', '').split(';')[0].strip()
        if content_type == 'text/html':
            link_headers = []

            # Add preconnect hints
            for domain in self.preconnect_domains:
                link_headers.append(f'<{domain}>; rel=preconnect')

            # Add DNS prefetch hints
            link_headers.append('</>; rel=dns-prefetch')

            # Combine and add Link header
            if link_headers:
                existing_link = response.headers.get('Link', '')
                if existing_link:
                    link_headers.insert(0, existing_link)
                response.headers['Link'] = ', '.join(link_headers)

        return response