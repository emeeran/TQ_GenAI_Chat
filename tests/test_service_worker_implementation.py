"""
TQ GenAI Chat - Service Worker Implementation Tests

Comprehensive test suite for Task 2.1.3: Service Worker Implementation
Tests service worker functionality, offline capabilities, background sync,
PWA features, and Flask integration.

Author: TQ GenAI Chat
Created: 2025-08-07
"""

import json
import os
import tempfile
from pathlib import Path

import pytest


class TestServiceWorkerImplementation:
    """Test service worker core functionality"""

    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        from app import app

        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    def test_service_worker_file_served(self, client):
        """Test that service worker file is served correctly"""
        response = client.get("/sw.js")

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/javascript"
        assert response.headers["Service-Worker-Allowed"] == "/"
        assert b"TQ GenAI Chat - Service Worker" in response.data

    def test_manifest_file_served(self, client):
        """Test that PWA manifest is served correctly"""
        response = client.get("/manifest.json")

        assert response.status_code == 200

        # Parse and validate manifest
        manifest = json.loads(response.data)
        assert manifest["name"] == "TQ GenAI Chat"
        assert manifest["short_name"] == "TQ Chat"
        assert manifest["display"] == "standalone"
        assert manifest["theme_color"] == "#667eea"
        assert len(manifest["icons"]) > 0

    def test_cache_status_endpoint(self, client):
        """Test service worker cache status endpoint"""
        response = client.get("/api/sw/cache-status")

        assert response.status_code == 200

        data = json.loads(response.data)
        assert "server_cache" in data
        assert "timestamp" in data
        assert "version" in data

    def test_sync_status_endpoint(self, client):
        """Test background sync status endpoint"""
        response = client.get("/api/sw/sync-status")

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["online"] is True
        assert "last_sync" in data
        assert "sync_enabled" in data


class TestOfflineCapabilities:
    """Test offline functionality and caching"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from app import app

        app.config["TESTING"] = True
        return app.test_client()

    def test_offline_page_served(self, client):
        """Test offline fallback page"""
        response = client.get("/offline")

        assert response.status_code in [200, 503]  # 503 for actual offline simulation

    def test_manifest_cache_configuration(self):
        """Test that manifest has proper cache configuration"""
        manifest_path = Path(__file__).parent.parent / "static" / "manifest.json"

        with open(manifest_path) as f:
            manifest = json.load(f)

        # Test PWA configuration
        assert manifest["display"] == "standalone"
        assert manifest["start_url"] == "/"
        assert manifest["scope"] == "/"

        # Test features
        assert "features" in manifest
        features = manifest["features"]
        assert any("offline" in feature.lower() for feature in features)

    def test_service_worker_cache_strategy(self):
        """Test service worker cache strategy configuration"""
        sw_path = Path(__file__).parent.parent / "static" / "sw.js"

        with open(sw_path) as f:
            sw_content = f.read()

        # Check for cache configuration
        assert "CACHE_VERSION" in sw_content
        assert "STATIC_CACHE" in sw_content
        assert "DYNAMIC_CACHE" in sw_content
        assert "API_CACHE" in sw_content

        # Check for cache strategies
        assert "handleStaticAsset" in sw_content
        assert "handleAPIRequest" in sw_content
        assert "handleNavigationRequest" in sw_content


class TestBackgroundSync:
    """Test background sync functionality"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from app import app

        app.config["TESTING"] = True
        return app.test_client()

    def test_offline_sync_endpoint(self, client):
        """Test offline sync endpoint"""
        sync_data = {
            "tag": "chat-message-sync",
            "data": {
                "message": "Test offline message",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "timestamp": "2025-01-07T10:00:00Z",
            },
        }

        response = client.post(
            "/api/offline-sync", data=json.dumps(sync_data), content_type="application/json"
        )

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert data["tag"] == "chat-message-sync"
        assert "result" in data

    def test_chat_message_sync(self, client):
        """Test chat message background sync"""
        sync_data = {
            "tag": "chat-message-sync",
            "data": {
                "message": "Hello from offline",
                "provider": "openai",
                "model": "gpt-4o-mini",
                "timestamp": "2025-01-07T10:00:00Z",
            },
        }

        response = client.post(
            "/api/offline-sync", data=json.dumps(sync_data), content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "message_id" in data["result"]
        assert data["result"]["processed"] is True

    def test_file_upload_sync(self, client):
        """Test file upload background sync"""
        sync_data = {
            "tag": "file-upload-sync",
            "data": {
                "filename": "test.txt",
                "file_data": "dGVzdCBjb250ZW50",  # base64 encoded "test content"
            },
        }

        response = client.post(
            "/api/offline-sync", data=json.dumps(sync_data), content_type="application/json"
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "file_id" in data["result"]
        assert data["result"]["filename"] == "test.txt"

    def test_invalid_sync_tag(self, client):
        """Test handling of invalid sync tags"""
        sync_data = {"tag": "invalid-sync-tag", "data": {"test": "data"}}

        response = client.post(
            "/api/offline-sync", data=json.dumps(sync_data), content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "Unknown sync tag" in data["error"]


class TestPushNotifications:
    """Test push notification functionality"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from app import app

        app.config["TESTING"] = True
        return app.test_client()

    def test_push_notification_endpoint(self, client):
        """Test push notification handling"""
        notification_data = {
            "title": "Test Notification",
            "body": "This is a test notification",
            "tag": "test-notification",
        }

        response = client.post(
            "/api/sw/notification",
            data=json.dumps(notification_data),
            content_type="application/json",
        )

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["success"] is True
        assert data["notification"]["title"] == "Test Notification"
        assert data["notification"]["body"] == "This is a test notification"

    def test_notification_defaults(self, client):
        """Test notification default values"""
        response = client.post(
            "/api/sw/notification", data=json.dumps({}), content_type="application/json"
        )

        assert response.status_code == 200

        data = json.loads(response.data)
        notification = data["notification"]
        assert notification["title"] == "TQ GenAI Chat"
        assert notification["body"] == "You have a new message"
        assert notification["icon"] == "/static/images/icon-192x192.png"


class TestWebShareAPI:
    """Test Web Share API integration"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from app import app

        app.config["TESTING"] = True
        return app.test_client()

    def test_web_share_text_content(self, client):
        """Test sharing text content"""
        share_data = {
            "title": "Shared Article",
            "text": "This is shared content from another app",
            "url": "https://example.com/article",
        }

        response = client.post("/share", data=share_data)

        assert response.status_code == 200
        assert b"Shared content:" in response.data
        assert b"Shared Article" in response.data

    def test_web_share_with_files(self, client):
        """Test sharing with file attachments"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"Test file content")
            temp_file.flush()

            with open(temp_file.name, "rb") as file:
                share_data = {
                    "title": "Document Share",
                    "text": "Sharing a document",
                    "file": (file, "test.txt", "text/plain"),
                }

                response = client.post(
                    "/share", data=share_data, content_type="multipart/form-data"
                )

                assert response.status_code == 200
                assert b"Files: test.txt" in response.data

        # Cleanup
        os.unlink(temp_file.name)


class TestPWAFeatures:
    """Test Progressive Web App features"""

    def test_manifest_pwa_configuration(self):
        """Test PWA manifest configuration"""
        manifest_path = Path(__file__).parent.parent / "static" / "manifest.json"

        with open(manifest_path) as f:
            manifest = json.load(f)

        # Test required PWA fields
        assert manifest["name"]
        assert manifest["short_name"]
        assert manifest["start_url"]
        assert manifest["display"]
        assert manifest["theme_color"]
        assert manifest["background_color"]

        # Test icons
        assert len(manifest["icons"]) > 0
        icon_sizes = [icon["sizes"] for icon in manifest["icons"]]
        assert "192x192" in icon_sizes
        assert "512x512" in icon_sizes

    def test_manifest_shortcuts(self):
        """Test PWA shortcuts configuration"""
        manifest_path = Path(__file__).parent.parent / "static" / "manifest.json"

        with open(manifest_path) as f:
            manifest = json.load(f)

        # Test shortcuts
        assert "shortcuts" in manifest
        shortcuts = manifest["shortcuts"]
        assert len(shortcuts) > 0

        # Test shortcut structure
        for shortcut in shortcuts:
            assert "name" in shortcut
            assert "url" in shortcut
            assert "icons" in shortcut

    def test_manifest_file_handlers(self):
        """Test PWA file handler configuration"""
        manifest_path = Path(__file__).parent.parent / "static" / "manifest.json"

        with open(manifest_path) as f:
            manifest = json.load(f)

        # Test file handlers
        assert "file_handlers" in manifest
        file_handlers = manifest["file_handlers"]
        assert len(file_handlers) > 0

        # Test supported file types
        handler = file_handlers[0]
        assert "accept" in handler
        accepted_types = handler["accept"]
        assert "text/plain" in accepted_types
        assert "application/pdf" in accepted_types


class TestServiceWorkerManager:
    """Test service worker manager JavaScript functionality"""

    def test_service_worker_manager_file_exists(self):
        """Test that service worker manager file exists"""
        sw_manager_path = Path(__file__).parent.parent / "static" / "js" / "sw-manager.js"
        assert sw_manager_path.exists()

    def test_service_worker_manager_structure(self):
        """Test service worker manager JavaScript structure"""
        sw_manager_path = Path(__file__).parent.parent / "static" / "js" / "sw-manager.js"

        with open(sw_manager_path) as f:
            content = f.read()

        # Test class definition
        assert "class ServiceWorkerManager" in content

        # Test key methods
        assert "init()" in content
        assert "register()" in content
        assert "handleOnline()" in content
        assert "handleOffline()" in content
        assert "queueBackgroundSync(" in content

        # Test notification handling
        assert "showNotification(" in content
        assert "requestNotificationPermission()" in content


class TestHTMLIntegration:
    """Test HTML template integration"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from app import app

        app.config["TESTING"] = True
        return app.test_client()

    def test_pwa_meta_tags_in_html(self, client):
        """Test that PWA meta tags are present in HTML"""
        response = client.get("/")

        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        # Test PWA meta tags
        assert 'name="theme-color"' in html_content
        assert 'name="mobile-web-app-capable"' in html_content
        assert 'name="apple-mobile-web-app-capable"' in html_content
        assert 'rel="manifest"' in html_content

    def test_service_worker_registration_in_html(self, client):
        """Test that service worker registration is in HTML"""
        response = client.get("/")

        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        # Test service worker registration
        assert "serviceWorker" in html_content
        assert "sw-manager.js" in html_content

    def test_offline_indicator_styles(self, client):
        """Test that offline indicator styles are present"""
        response = client.get("/")

        assert response.status_code == 200
        html_content = response.data.decode("utf-8")

        # Test offline indicator
        assert "offline-indicator" in html_content
        assert "pwa-install-prompt" in html_content


class TestPerformanceAndCaching:
    """Test performance and caching aspects"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from app import app

        app.config["TESTING"] = True
        return app.test_client()

    def test_service_worker_cache_headers(self, client):
        """Test service worker cache headers"""
        response = client.get("/sw.js")

        assert response.status_code == 200
        assert response.headers["Service-Worker-Allowed"] == "/"

    def test_manifest_cache_headers(self, client):
        """Test manifest cache headers"""
        response = client.get("/manifest.json")

        assert response.status_code == 200
        # Manifest should be cacheable
        assert "Cache-Control" not in response.headers or "no-cache" not in response.headers.get(
            "Cache-Control", ""
        )

    def test_service_worker_performance_features(self):
        """Test service worker performance features"""
        sw_path = Path(__file__).parent.parent / "static" / "sw.js"

        with open(sw_path) as f:
            content = f.read()

        # Test performance optimizations
        assert "CACHE_LIFETIMES" in content
        assert "cleanupOldCaches" in content
        assert "compression" in content.lower() or "gzip" in content.lower()


class TestIntegrationTests:
    """Integration tests for complete service worker functionality"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from app import app

        app.config["TESTING"] = True
        return app.test_client()

    def test_full_offline_workflow(self, client):
        """Test complete offline workflow"""
        # 1. Get service worker
        sw_response = client.get("/sw.js")
        assert sw_response.status_code == 200

        # 2. Get manifest
        manifest_response = client.get("/manifest.json")
        assert manifest_response.status_code == 200

        # 3. Test offline sync
        sync_data = {
            "tag": "chat-message-sync",
            "data": {
                "message": "Integration test message",
                "provider": "openai",
                "model": "gpt-4o-mini",
            },
        }

        sync_response = client.post(
            "/api/offline-sync", data=json.dumps(sync_data), content_type="application/json"
        )
        assert sync_response.status_code == 200

        # 4. Test cache status
        cache_response = client.get("/api/sw/cache-status")
        assert cache_response.status_code == 200

    def test_pwa_installation_flow(self, client):
        """Test PWA installation flow"""
        # 1. Main page with PWA features
        response = client.get("/")
        assert response.status_code == 200

        html_content = response.data.decode("utf-8")
        assert "pwa-install-prompt" in html_content
        assert "beforeinstallprompt" in html_content

        # 2. Manifest is accessible
        manifest_response = client.get("/manifest.json")
        assert manifest_response.status_code == 200

        manifest = json.loads(manifest_response.data)
        assert manifest["display"] == "standalone"

    def test_service_worker_lifecycle(self, client):
        """Test service worker lifecycle events"""
        sw_response = client.get("/sw.js")
        assert sw_response.status_code == 200

        sw_content = sw_response.data.decode("utf-8")

        # Test lifecycle events
        assert "addEventListener('install'" in sw_content
        assert "addEventListener('activate'" in sw_content
        assert "addEventListener('fetch'" in sw_content
        assert "addEventListener('sync'" in sw_content
        assert "addEventListener('push'" in sw_content


class TestErrorHandling:
    """Test error handling in service worker implementation"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        from app import app

        app.config["TESTING"] = True
        return app.test_client()

    def test_malformed_sync_request(self, client):
        """Test handling of malformed sync requests"""
        response = client.post(
            "/api/offline-sync", data="invalid json", content_type="application/json"
        )

        assert response.status_code == 400

    def test_missing_sync_data(self, client):
        """Test handling of missing sync data"""
        response = client.post(
            "/api/offline-sync", data=json.dumps({}), content_type="application/json"
        )

        assert response.status_code == 400

    def test_invalid_notification_request(self, client):
        """Test handling of invalid notification requests"""
        response = client.post(
            "/api/sw/notification", data="invalid json", content_type="application/json"
        )

        assert response.status_code == 400


# Test execution and reporting
if __name__ == "__main__":
    print("🧪 Running Service Worker Implementation Tests...")

    # Run tests with detailed output
    pytest_args = ["-v", "--tb=short", "--color=yes", __file__]

    result = pytest.main(pytest_args)

    if result == 0:
        print("\n✅ All Service Worker tests passed!")
        print("📊 Service Worker Implementation Status:")
        print("   ✅ Service Worker file served correctly")
        print("   ✅ PWA manifest configured properly")
        print("   ✅ Offline capabilities working")
        print("   ✅ Background sync functional")
        print("   ✅ Push notifications supported")
        print("   ✅ Web Share API integrated")
        print("   ✅ HTML integration complete")
        print("   ✅ Performance optimizations active")
        print("   ✅ Error handling robust")
        print("\n🎉 Task 2.1.3: Service Worker Implementation - COMPLETED!")
    else:
        print(f"\n❌ Some tests failed. Exit code: {result}")
        print("🔧 Please review and fix failing tests before deployment")

    exit(result)
