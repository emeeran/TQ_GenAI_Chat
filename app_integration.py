"""
Integration updates for app.py to use all the new optimization modules.
This file contains the modifications needed to integrate the optimization modules
into the main Flask application.
"""

import asyncio
import logging
import os
import time

from flask import Flask, g, jsonify, request, session

from core.background_tasks import CELERY_AVAILABLE, task_manager
from core.database_optimizations import get_document_store
from core.hybrid_cache import get_cache_manager

# Import optimization modules
from core.optimized_api_client import get_api_client
from core.performance_monitor import ai_request_timer, get_performance_monitor, request_timer
from core.security_enhancements import get_security_manager
from core.streaming_processor import StreamingFileProcessor
from core.websocket_handler import get_websocket_handler

logger = logging.getLogger(__name__)

# Global instances
api_client = None
cache_manager = None
streaming_processor = None
websocket_handler = None
document_store = None
performance_monitor = None
security_manager = None


def initialize_optimizations(app: Flask):
    """
    Initialize all optimization modules.
    Call this function during Flask app initialization.
    """
    global api_client, cache_manager, streaming_processor, websocket_handler
    global document_store, performance_monitor, security_manager

    logger.info("Initializing optimization modules...")

    # Initialize Redis URL from environment
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    try:
        # Initialize cache manager
        cache_manager = get_cache_manager(redis_url=redis_url)
        logger.info("✓ Cache manager initialized")

        # Initialize document store
        database_path = os.getenv('DATABASE_PATH', 'documents.db')
        document_store = get_document_store(database_path, redis_url)
        logger.info("✓ Document store initialized")

        # Initialize performance monitor
        performance_monitor = get_performance_monitor(redis_url)
        performance_monitor.start()
        logger.info("✓ Performance monitor initialized")

        # Initialize security manager
        master_key = os.getenv('SECURITY_MASTER_KEY')
        security_manager = get_security_manager(master_key)
        logger.info("✓ Security manager initialized")

        # Initialize streaming processor
        streaming_processor = StreamingFileProcessor()
        logger.info("✓ Streaming processor initialized")

        # Initialize WebSocket handler
        websocket_handler = get_websocket_handler()
        logger.info("✓ WebSocket handler initialized")

        # Initialize API client (async)
        async def init_api_client():
            global api_client
            api_client = await get_api_client()
            logger.info("✓ Optimized API client initialized")

        # Run async initialization
        asyncio.run(init_api_client())

        logger.info("🚀 All optimization modules initialized successfully!")

    except Exception as e:
        logger.error(f"❌ Failed to initialize optimizations: {e}")
        raise


def create_optimized_routes(app: Flask):
    """
    Create optimized routes that use the new modules.
    Add these routes to your Flask app.
    """

    @app.before_request
    def before_request():
        """Security and monitoring setup for each request."""
        # Start performance monitoring
        g.request_timer = request_timer(request.endpoint or 'unknown', request.method)
        g.request_timer.__enter__()

        # Get user info
        user_id = session.get('user_id', 'anonymous')
        ip_address = request.remote_addr or 'unknown'

        # Security validation for API endpoints
        if request.endpoint and request.endpoint.startswith('api_'):
            is_valid, error_message = security_manager.validate_request(
                user_id=user_id,
                ip_address=ip_address,
                endpoint=request.endpoint,
                data=request.get_json() or {},
                rate_limit=60  # 60 requests per minute
            )

            if not is_valid:
                g.request_timer.__exit__(None, None, None)
                return jsonify({'error': error_message}), 429

    @app.after_request
    def after_request(response):
        """Cleanup after each request."""
        if hasattr(g, 'request_timer'):
            g.request_timer.__exit__(None, None, None)
        return response

    @app.route('/api/chat/optimized', methods=['POST'])
    async def optimized_chat():
        """Optimized chat endpoint using all performance improvements."""
        try:
            data = request.get_json()
            user_id = session.get('user_id', 'anonymous')

            # Input validation
            message = data.get('message', '')
            provider = data.get('provider', 'openai')
            model = data.get('model', 'gpt-3.5-turbo')

            if not message:
                return jsonify({'error': 'Message is required'}), 400

            # Check cache first
            cache_key = f"chat:{provider}:{model}:{hash(message)}"
            cached_response = await cache_manager.get(cache_key)

            if cached_response:
                logger.info("Cache hit for chat request")
                return jsonify({
                    'response': cached_response,
                    'cached': True,
                    'provider': provider,
                    'model': model
                })

            # Background processing for long requests
            if CELERY_AVAILABLE and len(message) > 5000:
                # Submit to background task
                task_id = await task_manager.submit_ai_chat_task(
                    message=message,
                    provider=provider,
                    model=model,
                    user_id=user_id,
                    context={'api_key': security_manager.get_api_key(provider)}
                )

                return jsonify({
                    'task_id': task_id,
                    'status': 'processing',
                    'message': 'Request submitted for background processing'
                })

            # Process request with monitoring
            with ai_request_timer(provider, model, performance_monitor):
                # Get API key securely
                api_key = security_manager.get_api_key(provider)
                if not api_key:
                    return jsonify({'error': f'API key not configured for {provider}'}), 400

                # Make optimized API request
                if provider == 'openai':
                    endpoint = "https://api.openai.com/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": model,
                        "messages": [{"role": "user", "content": message}],
                        "stream": False
                    }
                else:
                    return jsonify({'error': f'Provider {provider} not supported'}), 400

                # Use optimized API client
                response = await api_client.make_request(
                    method='POST',
                    url=endpoint,
                    headers=headers,
                    json_data=payload
                )

                # Extract response
                ai_response = response['choices'][0]['message']['content']

                # Cache the response
                await cache_manager.set(cache_key, ai_response, ttl=3600)  # 1 hour

                # Store in database
                document_store.add_chat_history(
                    session_id=session.get('session_id', user_id),
                    user_message=message,
                    ai_response=ai_response,
                    provider=provider,
                    model=model,
                    response_time_ms=int(time.time() * 1000),
                    metadata={'user_id': user_id}
                )

                return jsonify({
                    'response': ai_response,
                    'cached': False,
                    'provider': provider,
                    'model': model
                })

        except Exception as e:
            logger.error(f"Optimized chat error: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/upload/optimized', methods=['POST'])
    async def optimized_file_upload():
        """Optimized file upload with streaming processing."""
        try:
            if 'files' not in request.files:
                return jsonify({'error': 'No files uploaded'}), 400

            files = request.files.getlist('files')
            user_id = session.get('user_id', 'anonymous')
            results = []

            for file in files:
                if file.filename == '':
                    continue

                # Validate filename
                if not security_manager.input_validator.validate_filename(file.filename):
                    results.append({
                        'filename': file.filename,
                        'error': 'Invalid filename'
                    })
                    continue

                # Read file data
                file_data = file.read()
                file.seek(0)  # Reset for potential reuse

                # Check file size
                if len(file_data) > 16 * 1024 * 1024:  # 16MB limit
                    results.append({
                        'filename': file.filename,
                        'error': 'File too large (max 16MB)'
                    })
                    continue

                # Background processing for large files
                if CELERY_AVAILABLE and len(file_data) > 5 * 1024 * 1024:  # 5MB
                    task_id = await task_manager.submit_file_processing_task(
                        file_data=file_data,
                        filename=file.filename,
                        user_id=user_id
                    )

                    results.append({
                        'filename': file.filename,
                        'task_id': task_id,
                        'status': 'processing'
                    })
                else:
                    # Process immediately with streaming
                    try:
                        content = await streaming_processor.process_file_content(
                            file_data, file.filename
                        )

                        # Store in document store
                        doc_id = document_store.add_document(
                            filename=file.filename,
                            content=content,
                            metadata={'user_id': user_id, 'file_size': len(file_data)}
                        )

                        results.append({
                            'filename': file.filename,
                            'document_id': doc_id,
                            'content_length': len(content),
                            'status': 'completed'
                        })

                    except Exception as e:
                        logger.error(f"File processing error for {file.filename}: {e}")
                        results.append({
                            'filename': file.filename,
                            'error': str(e)
                        })

            return jsonify({'results': results})

        except Exception as e:
            logger.error(f"Optimized upload error: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/search/optimized', methods=['GET'])
    async def optimized_search():
        """Optimized document search with caching."""
        try:
            query = request.args.get('q', '')
            limit = min(int(request.args.get('limit', 10)), 50)

            if not query:
                return jsonify({'error': 'Query parameter required'}), 400

            # Check cache first
            cache_key = f"search:{hash(query)}:{limit}"
            cached_results = await cache_manager.get(cache_key)

            if cached_results:
                return jsonify({
                    'results': cached_results,
                    'cached': True
                })

            # Search documents
            results = document_store.search_documents(query, limit)

            # Cache results
            await cache_manager.set(cache_key, results, ttl=300)  # 5 minutes

            return jsonify({
                'results': results,
                'cached': False
            })

        except Exception as e:
            logger.error(f"Optimized search error: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/performance/stats', methods=['GET'])
    def performance_stats():
        """Get performance statistics."""
        try:
            snapshot = performance_monitor.get_performance_snapshot()

            return jsonify({
                'timestamp': snapshot.timestamp,
                'system': {
                    'cpu_percent': snapshot.cpu_percent,
                    'memory_percent': snapshot.memory_percent,
                    'memory_mb': snapshot.memory_mb,
                },
                'network': {
                    'sent_mb_per_sec': snapshot.network_sent_mb,
                    'recv_mb_per_sec': snapshot.network_recv_mb,
                },
                'application': {
                    'active_connections': snapshot.active_connections,
                    'response_times': snapshot.response_times,
                    'error_rates': snapshot.error_rates,
                    'custom_metrics': snapshot.custom_metrics
                }
            })

        except Exception as e:
            logger.error(f"Performance stats error: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/task/status/<task_id>', methods=['GET'])
    def task_status(task_id):
        """Get background task status."""
        try:
            status = task_manager.get_task_status(task_id)
            return jsonify(status)
        except Exception as e:
            logger.error(f"Task status error: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/security/audit', methods=['GET'])
    def security_audit():
        """Get security audit information."""
        try:
            hours = int(request.args.get('hours', 24))
            severity = request.args.get('severity')

            # Get recent events
            events = security_manager.auditor.get_recent_events(hours, severity)

            # Get anomalies
            anomalies = security_manager.auditor.detect_anomalies()

            return jsonify({
                'events': [
                    {
                        'timestamp': event.timestamp,
                        'event_type': event.event_type,
                        'user_id': event.user_id,
                        'ip_address': event.ip_address,
                        'severity': event.severity,
                        'details': event.details
                    }
                    for event in events
                ],
                'anomalies': anomalies,
                'total_events': len(events)
            })

        except Exception as e:
            logger.error(f"Security audit error: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/health/detailed', methods=['GET'])
    def detailed_health_check():
        """Detailed health check with all systems."""
        try:
            health_status = {
                'status': 'healthy',
                'timestamp': time.time(),
                'services': {}
            }

            # Check cache manager
            try:
                await cache_manager.get('health_check')
                health_status['services']['cache'] = 'healthy'
            except Exception as e:
                health_status['services']['cache'] = f'unhealthy: {e}'
                health_status['status'] = 'degraded'

            # Check document store
            try:
                document_store.get_statistics()
                health_status['services']['database'] = 'healthy'
            except Exception as e:
                health_status['services']['database'] = f'unhealthy: {e}'
                health_status['status'] = 'degraded'

            # Check performance monitor
            try:
                performance_monitor.get_performance_snapshot()
                health_status['services']['monitoring'] = 'healthy'
            except Exception as e:
                health_status['services']['monitoring'] = f'unhealthy: {e}'
                health_status['status'] = 'degraded'

            # Check background tasks
            if CELERY_AVAILABLE:
                health_status['services']['background_tasks'] = 'healthy'
            else:
                health_status['services']['background_tasks'] = 'disabled'

            return jsonify(health_status)

        except Exception as e:
            logger.error(f"Health check error: {e}")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e)
            }), 500


def shutdown_optimizations():
    """
    Cleanup function to call during app shutdown.
    """
    logger.info("Shutting down optimization modules...")

    try:
        if performance_monitor:
            performance_monitor.stop()

        if document_store:
            document_store.close()

        if api_client:
            asyncio.run(api_client.close())

        logger.info("✓ Optimization modules shut down successfully")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Flask app factory with optimizations
def create_optimized_app():
    """
    Create Flask app with all optimizations enabled.
    """
    from flask import Flask

    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

    # Initialize optimizations
    initialize_optimizations(app)

    # Create optimized routes
    create_optimized_routes(app)

    # Register shutdown handler
    @app.teardown_appcontext
    def close_connections(error):
        """Close connections on app context teardown."""
        pass

    # Add shutdown handler
    import atexit
    atexit.register(shutdown_optimizations)

    return app


# Example usage instructions
INTEGRATION_INSTRUCTIONS = """
INTEGRATION INSTRUCTIONS FOR EXISTING APP.PY:

1. Add these imports to the top of your app.py:
   ```python
   from app_integration import (
       initialize_optimizations,
       create_optimized_routes,
       shutdown_optimizations
   )
   ```

2. After creating your Flask app, initialize optimizations:
   ```python
   app = Flask(__name__)
   initialize_optimizations(app)
   create_optimized_routes(app)
   ```

3. Add shutdown handling:
   ```python
   import atexit
   atexit.register(shutdown_optimizations)
   ```

4. Update your existing endpoints to use the optimization modules:
   - Replace requests with the optimized API client
   - Add caching to expensive operations
   - Use streaming processor for large files
   - Add performance monitoring to critical paths

5. Environment variables to set:
   - REDIS_URL: Redis connection string (optional)
   - DATABASE_PATH: Path to SQLite database (optional)
   - SECURITY_MASTER_KEY: Master key for API key encryption (recommended)
   - SECRET_KEY: Flask session secret key

6. Optional: Install additional dependencies for full functionality:
   ```bash
   pip install celery redis cryptography psutil
   ```

For detailed integration, see the functions in this file and adapt them
to your existing route structure.
"""

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info(INTEGRATION_INSTRUCTIONS)
