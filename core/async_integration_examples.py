"""
Example Integration: ThreadPoolExecutor in app.py

This file demonstrates how to integrate the AsyncHandler ThreadPoolExecutor implementation
into the existing Flask routes for Task 1.2.1. Shows before/after code examples and
the specific changes needed in app.py.

Author: TQ GenAI Chat
Created: 2025-08-07
"""

# BEFORE: Original synchronous route (blocking)
"""
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        provider = data.get("provider")
        if not provider:
            return jsonify({"error": "Provider is required"}), 400

        if not provider_manager.is_provider_available(provider):
            return (
                jsonify({"error": f"Provider {provider} not available or not configured"}),
                401,
            )

        # This blocks the main thread during API calls and processing
        response = chat_handler.process_chat_request(data)
        return jsonify(response)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Chat error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
"""

# AFTER: AsyncHandler-wrapped route (non-blocking)
"""
from core.app_async_wrappers import async_chat_route, monitor_performance

@app.route("/chat", methods=["POST"])
@monitor_performance()
@async_chat_route(timeout=120.0)  # 2 minute timeout for chat processing
def chat():
    # Same logic, but now runs in ThreadPoolExecutor
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        provider = data.get("provider")
        if not provider:
            return jsonify({"error": "Provider is required"}), 400

        if not provider_manager.is_provider_available(provider):
            return (
                jsonify({"error": f"Provider {provider} not available or not configured"}),
                401,
            )

        # This now runs in thread pool - non-blocking
        response = chat_handler.process_chat_request(data)
        return jsonify(response)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        app.logger.error(f"Chat error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
"""

# BEFORE: Synchronous file processing
"""
@app.route("/upload", methods=["POST"])
def upload_files():
    try:
        if "files" not in request.files:
            return jsonify({"error": "No files provided"}), 400

        files = request.files.getlist("files")
        if not files:
            return jsonify({"error": "No files selected"}), 400

        # Process files synchronously - blocks for large files
        results = []
        for file in files:
            if file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = Path(app.config["UPLOAD_FOLDER"]) / filename
                file.save(file_path)

                # Blocking file processing
                asyncio.create_task(process_file_async(filename, str(file_path)))
                results.append({"filename": filename, "status": "processing"})

        return jsonify({"results": results})

    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        return jsonify({"error": "Upload failed"}), 500
"""

# AFTER: AsyncHandler file processing
"""
from core.app_async_wrappers import async_file_operation, monitor_performance

@app.route("/upload", methods=["POST"])
@monitor_performance()
def upload_files():
    try:
        if "files" not in request.files:
            return jsonify({"error": "No files provided"}), 400

        files = request.files.getlist("files")
        if not files:
            return jsonify({"error": "No files selected"}), 400

        results = []
        for file in files:
            if file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = Path(app.config["UPLOAD_FOLDER"]) / filename
                file.save(file_path)

                # Non-blocking async file processing
                asyncio.create_task(process_file_with_async_handler(filename, str(file_path)))
                results.append({"filename": filename, "status": "processing"})

        return jsonify({"results": results})

    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        return jsonify({"error": "Upload failed"}), 500

@async_file_operation("file_upload_processing", timeout=300.0)
async def process_file_with_async_handler(filename, file_path):
    # Heavy file processing now runs in ThreadPoolExecutor
    try:
        processor = FileProcessor()
        content = await processor.process_file(file_path, filename)

        if content:
            file_manager.add_document(filename, content)
            PROCESSING_STATUS[filename] = {
                "status": "completed",
                "processed_at": time.time()
            }
        else:
            PROCESSING_ERRORS[filename] = "Failed to extract content"

    except Exception as e:
        PROCESSING_ERRORS[filename] = str(e)
        logger.error(f"File processing error for {filename}: {e}")
"""

# BEFORE: Synchronous context search
"""
@app.route("/search_context", methods=["POST"])
def search_context():
    try:
        data = request.get_json()
        query = data.get("message", "")

        if not query:
            return jsonify({"error": "No query provided"}), 400

        # Blocking vector search
        results = file_manager.search_documents(query)

        formatted_results = [
            {
                "filename": r["filename"],
                "excerpt": (
                    r["content"][:500] + "..." if len(r["content"]) > 500 else r["content"]
                ),
                "similarity": r["similarity"],
            }
            for r in results
        ]

        return jsonify({"results": formatted_results})

    except Exception as e:
        app.logger.error(f"Context search error: {str(e)}")
        return jsonify({"error": str(e)}), 500
"""

# AFTER: AsyncHandler context search
"""
from core.app_async_wrappers import async_context_search, monitor_performance

@app.route("/search_context", methods=["POST"])
@monitor_performance()
@async_context_search(timeout=45.0)
def search_context():
    try:
        data = request.get_json()
        query = data.get("message", "")

        if not query:
            return jsonify({"error": "No query provided"}), 400

        # Non-blocking vector search in ThreadPoolExecutor
        results = file_manager.search_documents(query)

        formatted_results = [
            {
                "filename": r["filename"],
                "excerpt": (
                    r["content"][:500] + "..." if len(r["content"]) > 500 else r["content"]
                ),
                "similarity": r["similarity"],
            }
            for r in results
        ]

        return jsonify({"results": formatted_results})

    except Exception as e:
        app.logger.error(f"Context search error: {str(e)}")
        return jsonify({"error": str(e)}), 500
"""

# BEFORE: Synchronous database operations
"""
@app.route("/save_chat", methods=["POST"])
def save_chat():
    try:
        data = request.get_json()

        # Blocking database save
        filename = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000000, 9999999)}.json"
        file_path = Path("saved_chats") / filename

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

        return jsonify({"filename": filename, "status": "saved"})

    except Exception as e:
        app.logger.error(f"Save chat error: {str(e)}")
        return jsonify({"error": "Failed to save chat"}), 500
"""

# AFTER: AsyncHandler database operations
"""
from core.app_async_wrappers import async_database_operation, monitor_performance

@app.route("/save_chat", methods=["POST"])
@monitor_performance()
@async_database_operation(timeout=30.0)
def save_chat():
    try:
        data = request.get_json()

        # Non-blocking database save in ThreadPoolExecutor
        filename = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000000, 9999999)}.json"
        file_path = Path("saved_chats") / filename

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)

        return jsonify({"filename": filename, "status": "saved"})

    except Exception as e:
        app.logger.error(f"Save chat error: {str(e)}")
        return jsonify({"error": "Failed to save chat"}), 500
"""

# INITIALIZATION: Add to app.py startup
"""
from core.app_async_wrappers import init_async_app_handler, get_app_performance_stats

# Initialize AsyncHandler for the app
init_async_app_handler()

# Add performance monitoring endpoint
@app.route("/performance/async", methods=["GET"])
def async_performance():
    try:
        stats = get_app_performance_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
"""

# SHUTDOWN HANDLING: Add to app.py cleanup
"""
import atexit
from core.async_handler import shutdown_async_handler

# Graceful shutdown
atexit.register(shutdown_async_handler)

# For Flask apps with proper shutdown
@app.teardown_appcontext
def cleanup_async_handler(error):
    if error:
        logger.error(f"App context error: {error}")
"""

# PERFORMANCE TESTING: Validate 50+ concurrent requests
"""
import threading
import requests
import time

def test_concurrent_chat_requests():
    '''Test ThreadPoolExecutor performance with 50+ concurrent requests'''

    def make_chat_request():
        try:
            response = requests.post('http://localhost:5000/chat', json={
                'provider': 'openai',
                'model': 'gpt-4o-mini',
                'messages': [{'role': 'user', 'content': 'Hello'}]
            }, timeout=30)
            return response.status_code == 200
        except Exception as e:
            print(f"Request failed: {e}")
            return False

    # Launch 50 concurrent requests
    threads = []
    results = []
    start_time = time.time()

    for i in range(50):
        thread = threading.Thread(target=lambda: results.append(make_chat_request()))
        threads.append(thread)
        thread.start()

    # Wait for all threads
    for thread in threads:
        thread.join()

    end_time = time.time()
    success_rate = sum(results) / len(results) if results else 0
    total_time = end_time - start_time

    print(f"Concurrent test results:")
    print(f"- Total requests: {len(results)}")
    print(f"- Success rate: {success_rate:.2%}")
    print(f"- Total time: {total_time:.2f}s")
    print(f"- Requests per second: {len(results) / total_time:.2f}")

    # Verify performance improvement
    assert success_rate > 0.95, f"Success rate too low: {success_rate:.2%}"
    assert total_time < 60, f"Total time too high: {total_time:.2f}s"

    print("✅ ThreadPoolExecutor concurrent test passed!")

if __name__ == "__main__":
    test_concurrent_chat_requests()
"""

# MONITORING AND DEBUGGING
"""
# Add logging to see ThreadPoolExecutor in action
import logging
logging.getLogger('core.async_handler').setLevel(logging.DEBUG)

# Check AsyncHandler stats during runtime
from core.app_async_wrappers import get_app_performance_stats

# In a debug route:
@app.route("/debug/async")
def debug_async():
    stats = get_app_performance_stats()
    return f'''
    <h2>AsyncHandler Status</h2>
    <pre>{json.dumps(stats, indent=2)}</pre>
    '''
"""
