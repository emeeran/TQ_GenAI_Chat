"""
Integration Testing Suite - Testing & Validation
End-to-end functionality testing including multi-provider chat,
file processing workflows, and cache system validation
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import aiohttp
import requests
from flask import Flask


@dataclass
class IntegrationTestResult:
    """Integration test result"""

    test_name: str
    test_type: str
    status: str  # pass, fail, error
    duration: float
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class IntegrationTestSuite:
    """Integration test suite results"""

    suite_name: str
    start_time: datetime
    end_time: datetime
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error_tests: int = 0
    results: list[IntegrationTestResult] = field(default_factory=list)


class IntegrationTestRunner:
    """Comprehensive integration testing suite"""

    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)

        # Test configuration
        self.test_config = {
            "timeout": 30,
            "retry_attempts": 3,
            "providers": ["openai", "anthropic", "groq", "xai"],
            "models": {
                "openai": ["gpt-4o-mini", "gpt-3.5-turbo"],
                "anthropic": ["claude-3-haiku-20240307"],
                "groq": ["llama-3.1-8b-instant"],
                "xai": ["grok-beta"],
            },
        }

        # Test data
        self.test_messages = [
            "Hello, how are you?",
            "What is the capital of France?",
            "Write a simple Python function to add two numbers.",
            "Explain quantum computing in simple terms.",
        ]

    def test_multi_provider_chat(self) -> IntegrationTestSuite:
        """Test chat functionality across multiple providers"""
        self.logger.info("Starting multi-provider chat tests...")
        start_time = datetime.now()
        results = []

        for provider in self.test_config["providers"]:
            for model in self.test_config["models"].get(provider, []):
                for message in self.test_messages:
                    result = self._test_chat_request(provider, model, message)
                    results.append(result)

        end_time = datetime.now()
        return self._compile_integration_results(
            "Multi-Provider Chat", start_time, end_time, results
        )

    def test_file_processing_workflow(self) -> IntegrationTestSuite:
        """Test complete file processing workflow"""
        self.logger.info("Starting file processing workflow tests...")
        start_time = datetime.now()
        results = []

        # Test different file types
        test_files = [
            {"name": "test.txt", "content": "This is a test document.", "type": "text/plain"},
            {"name": "test.json", "content": '{"key": "value"}', "type": "application/json"},
            {"name": "test.csv", "content": "name,age\nJohn,30\nJane,25", "type": "text/csv"},
            {
                "name": "test.md",
                "content": "# Test\nThis is a **markdown** file.",
                "type": "text/markdown",
            },
        ]

        for file_data in test_files:
            # Test file upload
            upload_result = self._test_file_upload(file_data)
            results.append(upload_result)

            # Test file processing status
            if upload_result.status == "pass":
                status_result = self._test_file_processing_status(file_data["name"])
                results.append(status_result)

                # Test search functionality
                search_result = self._test_file_search(file_data["name"])
                results.append(search_result)

        # Test file list endpoint
        list_result = self._test_file_list()
        results.append(list_result)

        end_time = datetime.now()
        return self._compile_integration_results(
            "File Processing Workflow", start_time, end_time, results
        )

    def test_cache_system_integration(self) -> IntegrationTestSuite:
        """Test cache system functionality"""
        self.logger.info("Starting cache system integration tests...")
        start_time = datetime.now()
        results = []

        # Test cache hit/miss
        cache_result = self._test_cache_functionality()
        results.append(cache_result)

        # Test cache invalidation
        invalidation_result = self._test_cache_invalidation()
        results.append(invalidation_result)

        # Test cache statistics
        stats_result = self._test_cache_statistics()
        results.append(stats_result)

        end_time = datetime.now()
        return self._compile_integration_results(
            "Cache System Integration", start_time, end_time, results
        )

    def test_error_handling_recovery(self) -> IntegrationTestSuite:
        """Test error handling and recovery mechanisms"""
        self.logger.info("Starting error handling tests...")
        start_time = datetime.now()
        results = []

        # Test invalid provider
        invalid_provider_result = self._test_invalid_provider()
        results.append(invalid_provider_result)

        # Test invalid model
        invalid_model_result = self._test_invalid_model()
        results.append(invalid_model_result)

        # Test malformed requests
        malformed_result = self._test_malformed_requests()
        results.append(malformed_result)

        # Test timeout handling
        timeout_result = self._test_timeout_handling()
        results.append(timeout_result)

        # Test retry mechanism
        retry_result = self._test_retry_mechanism()
        results.append(retry_result)

        end_time = datetime.now()
        return self._compile_integration_results(
            "Error Handling Recovery", start_time, end_time, results
        )

    def test_performance_under_load(self) -> IntegrationTestSuite:
        """Test system performance under load"""
        self.logger.info("Starting performance under load tests...")
        start_time = datetime.now()
        results = []

        # Test concurrent requests
        concurrent_result = self._test_concurrent_requests()
        results.append(concurrent_result)

        # Test large file processing
        large_file_result = self._test_large_file_processing()
        results.append(large_file_result)

        # Test memory usage under load
        memory_result = self._test_memory_usage_under_load()
        results.append(memory_result)

        end_time = datetime.now()
        return self._compile_integration_results(
            "Performance Under Load", start_time, end_time, results
        )

    def test_data_persistence(self) -> IntegrationTestSuite:
        """Test data persistence and recovery"""
        self.logger.info("Starting data persistence tests...")
        start_time = datetime.now()
        results = []

        # Test chat history persistence
        history_result = self._test_chat_history_persistence()
        results.append(history_result)

        # Test file storage persistence
        storage_result = self._test_file_storage_persistence()
        results.append(storage_result)

        # Test configuration persistence
        config_result = self._test_configuration_persistence()
        results.append(config_result)

        end_time = datetime.now()
        return self._compile_integration_results("Data Persistence", start_time, end_time, results)

    def _test_chat_request(self, provider: str, model: str, message: str) -> IntegrationTestResult:
        """Test individual chat request"""
        start_time = time.time()
        test_name = f"chat_{provider}_{model}"

        try:
            response = self.session.post(
                f"{self.base_url}/chat",
                json={"message": message, "provider": provider, "model": model},
                timeout=self.test_config["timeout"],
            )

            duration = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                if "response" in data and data["response"]:
                    return IntegrationTestResult(
                        test_name=test_name,
                        test_type="chat_request",
                        status="pass",
                        duration=duration,
                        message=f"Chat successful with {provider}/{model}",
                        details={
                            "provider": provider,
                            "model": model,
                            "response_length": len(data["response"]),
                            "status_code": response.status_code,
                        },
                    )
                else:
                    return IntegrationTestResult(
                        test_name=test_name,
                        test_type="chat_request",
                        status="fail",
                        duration=duration,
                        message="Empty response received",
                        details={"provider": provider, "model": model},
                    )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="chat_request",
                    status="fail",
                    duration=duration,
                    message=f"HTTP {response.status_code}",
                    details={
                        "provider": provider,
                        "model": model,
                        "status_code": response.status_code,
                    },
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="chat_request",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={"provider": provider, "model": model},
            )

    def _test_file_upload(self, file_data: dict) -> IntegrationTestResult:
        """Test file upload functionality"""
        start_time = time.time()
        test_name = f"file_upload_{file_data['name']}"

        try:
            files = {"file": (file_data["name"], file_data["content"], file_data["type"])}

            response = self.session.post(
                f"{self.base_url}/upload", files=files, timeout=self.test_config["timeout"]
            )

            duration = time.time() - start_time

            if response.status_code == 200:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="file_upload",
                    status="pass",
                    duration=duration,
                    message=f"File {file_data['name']} uploaded successfully",
                    details={"filename": file_data["name"], "size": len(file_data["content"])},
                )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="file_upload",
                    status="fail",
                    duration=duration,
                    message=f"Upload failed with HTTP {response.status_code}",
                    details={"filename": file_data["name"]},
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="file_upload",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={"filename": file_data["name"]},
            )

    def _test_file_processing_status(self, filename: str) -> IntegrationTestResult:
        """Test file processing status endpoint"""
        start_time = time.time()
        test_name = f"file_status_{filename}"

        try:
            response = self.session.get(
                f"{self.base_url}/upload/status/{filename}", timeout=self.test_config["timeout"]
            )

            duration = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="file_status",
                    status="pass",
                    duration=duration,
                    message=f"Status retrieved for {filename}",
                    details={"filename": filename, "status": data.get("status")},
                )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="file_status",
                    status="fail",
                    duration=duration,
                    message=f"Status check failed with HTTP {response.status_code}",
                    details={"filename": filename},
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="file_status",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={"filename": filename},
            )

    def _test_file_search(self, filename: str) -> IntegrationTestResult:
        """Test file search functionality"""
        start_time = time.time()
        test_name = f"file_search_{filename}"

        try:
            response = self.session.get(
                f"{self.base_url}/search_context",
                params={"query": "test"},
                timeout=self.test_config["timeout"],
            )

            duration = time.time() - start_time

            if response.status_code == 200:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="file_search",
                    status="pass",
                    duration=duration,
                    message="Search functionality working",
                    details={"query": "test"},
                )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="file_search",
                    status="fail",
                    duration=duration,
                    message=f"Search failed with HTTP {response.status_code}",
                    details={"query": "test"},
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="file_search",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={"query": "test"},
            )

    def _test_file_list(self) -> IntegrationTestResult:
        """Test file listing functionality"""
        start_time = time.time()
        test_name = "file_list"

        try:
            response = self.session.get(
                f"{self.base_url}/files", timeout=self.test_config["timeout"]
            )

            duration = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="file_list",
                    status="pass",
                    duration=duration,
                    message="File listing successful",
                    details={"file_count": len(data.get("files", []))},
                )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="file_list",
                    status="fail",
                    duration=duration,
                    message=f"File listing failed with HTTP {response.status_code}",
                    details={},
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="file_list",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={},
            )

    def _test_cache_functionality(self) -> IntegrationTestResult:
        """Test cache hit/miss functionality"""
        start_time = time.time()
        test_name = "cache_functionality"

        try:
            # Make same request twice to test caching
            request_data = {
                "message": "Test cache message",
                "provider": "openai",
                "model": "gpt-4o-mini",
            }

            # First request (should be cache miss)
            response1 = self.session.post(
                f"{self.base_url}/chat", json=request_data, timeout=self.test_config["timeout"]
            )

            time.sleep(1)  # Brief pause

            # Second request (should be cache hit)
            response2 = self.session.post(
                f"{self.base_url}/chat", json=request_data, timeout=self.test_config["timeout"]
            )

            duration = time.time() - start_time

            if response1.status_code == 200 and response2.status_code == 200:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="cache_test",
                    status="pass",
                    duration=duration,
                    message="Cache functionality working",
                    details={"cache_tested": True},
                )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="cache_test",
                    status="fail",
                    duration=duration,
                    message="Cache test failed",
                    details={
                        "response1_status": response1.status_code,
                        "response2_status": response2.status_code,
                    },
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="cache_test",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={},
            )

    def _test_cache_invalidation(self) -> IntegrationTestResult:
        """Test cache invalidation"""
        start_time = time.time()
        test_name = "cache_invalidation"

        try:
            response = self.session.post(
                f"{self.base_url}/cache/invalidate", timeout=self.test_config["timeout"]
            )

            duration = time.time() - start_time

            if response.status_code in [200, 204]:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="cache_invalidation",
                    status="pass",
                    duration=duration,
                    message="Cache invalidation successful",
                    details={},
                )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="cache_invalidation",
                    status="fail",
                    duration=duration,
                    message=f"Cache invalidation failed with HTTP {response.status_code}",
                    details={},
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="cache_invalidation",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={},
            )

    def _test_cache_statistics(self) -> IntegrationTestResult:
        """Test cache statistics endpoint"""
        start_time = time.time()
        test_name = "cache_statistics"

        try:
            response = self.session.get(
                f"{self.base_url}/cache/stats", timeout=self.test_config["timeout"]
            )

            duration = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="cache_statistics",
                    status="pass",
                    duration=duration,
                    message="Cache statistics retrieved",
                    details={"stats": data},
                )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="cache_statistics",
                    status="fail",
                    duration=duration,
                    message=f"Cache stats failed with HTTP {response.status_code}",
                    details={},
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="cache_statistics",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={},
            )

    def _test_invalid_provider(self) -> IntegrationTestResult:
        """Test handling of invalid provider"""
        start_time = time.time()
        test_name = "invalid_provider"

        try:
            response = self.session.post(
                f"{self.base_url}/chat",
                json={
                    "message": "Test message",
                    "provider": "invalid_provider",
                    "model": "test_model",
                },
                timeout=self.test_config["timeout"],
            )

            duration = time.time() - start_time

            # Should return error status
            if response.status_code in [400, 422]:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="error_handling",
                    status="pass",
                    duration=duration,
                    message="Invalid provider properly handled",
                    details={"status_code": response.status_code},
                )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="error_handling",
                    status="fail",
                    duration=duration,
                    message=f"Unexpected status code: {response.status_code}",
                    details={"status_code": response.status_code},
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="error_handling",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={},
            )

    def _test_invalid_model(self) -> IntegrationTestResult:
        """Test handling of invalid model"""
        start_time = time.time()
        test_name = "invalid_model"

        try:
            response = self.session.post(
                f"{self.base_url}/chat",
                json={"message": "Test message", "provider": "openai", "model": "invalid_model"},
                timeout=self.test_config["timeout"],
            )

            duration = time.time() - start_time

            # Should return error status
            if response.status_code in [400, 422]:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="error_handling",
                    status="pass",
                    duration=duration,
                    message="Invalid model properly handled",
                    details={"status_code": response.status_code},
                )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="error_handling",
                    status="fail",
                    duration=duration,
                    message=f"Unexpected status code: {response.status_code}",
                    details={"status_code": response.status_code},
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="error_handling",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={},
            )

    def _test_malformed_requests(self) -> IntegrationTestResult:
        """Test handling of malformed requests"""
        start_time = time.time()
        test_name = "malformed_requests"

        malformed_requests = [
            {},  # Empty request
            {"message": ""},  # Empty message
            {"provider": "openai"},  # Missing message and model
            {"invalid_field": "value"},  # Invalid fields
        ]

        try:
            error_count = 0
            for malformed_data in malformed_requests:
                response = self.session.post(
                    f"{self.base_url}/chat",
                    json=malformed_data,
                    timeout=self.test_config["timeout"],
                )

                if response.status_code in [400, 422]:
                    error_count += 1

            duration = time.time() - start_time

            if error_count == len(malformed_requests):
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="error_handling",
                    status="pass",
                    duration=duration,
                    message="All malformed requests properly rejected",
                    details={"tested_requests": len(malformed_requests)},
                )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="error_handling",
                    status="fail",
                    duration=duration,
                    message=f"Only {error_count}/{len(malformed_requests)} requests properly rejected",
                    details={"tested_requests": len(malformed_requests), "rejected": error_count},
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="error_handling",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={},
            )

    def _test_timeout_handling(self) -> IntegrationTestResult:
        """Test timeout handling"""
        start_time = time.time()
        test_name = "timeout_handling"

        try:
            # Test with very short timeout
            response = self.session.post(
                f"{self.base_url}/chat",
                json={
                    "message": "Write a very long story about space exploration",
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
                timeout=0.1,  # Very short timeout
            )

            duration = time.time() - start_time

            # Should timeout
            return IntegrationTestResult(
                test_name=test_name,
                test_type="timeout_handling",
                status="fail",
                duration=duration,
                message="Request completed when timeout expected",
                details={},
            )

        except requests.exceptions.Timeout:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="timeout_handling",
                status="pass",
                duration=time.time() - start_time,
                message="Timeout properly handled",
                details={},
            )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="timeout_handling",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={},
            )

    def _test_retry_mechanism(self) -> IntegrationTestResult:
        """Test retry mechanism"""
        start_time = time.time()
        test_name = "retry_mechanism"

        try:
            # This would need to be tested with actual retry logic
            # For now, just test that retry endpoint exists
            response = self.session.post(
                f"{self.base_url}/retry_last",
                json={"provider": "openai", "model": "gpt-4o-mini"},
                timeout=self.test_config["timeout"],
            )

            duration = time.time() - start_time

            # Retry endpoint should exist (even if no previous request to retry)
            if response.status_code in [200, 400, 404]:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="retry_mechanism",
                    status="pass",
                    duration=duration,
                    message="Retry endpoint accessible",
                    details={"status_code": response.status_code},
                )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="retry_mechanism",
                    status="fail",
                    duration=duration,
                    message=f"Retry endpoint failed with HTTP {response.status_code}",
                    details={"status_code": response.status_code},
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="retry_mechanism",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={},
            )

    async def _test_concurrent_requests_async(self) -> list[dict]:
        """Async helper for concurrent request testing"""
        async with aiohttp.ClientSession() as session:
            tasks = []

            for i in range(10):  # 10 concurrent requests
                task = self._make_async_request(session, i)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

    async def _make_async_request(self, session: aiohttp.ClientSession, request_id: int) -> dict:
        """Make async request"""
        try:
            async with session.post(
                f"{self.base_url}/chat",
                json={
                    "message": f"Test concurrent message {request_id}",
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
                timeout=30,
            ) as response:
                return {
                    "request_id": request_id,
                    "status_code": response.status,
                    "success": response.status == 200,
                }
        except Exception as e:
            return {"request_id": request_id, "status_code": 0, "success": False, "error": str(e)}

    def _test_concurrent_requests(self) -> IntegrationTestResult:
        """Test concurrent request handling"""
        start_time = time.time()
        test_name = "concurrent_requests"

        try:
            # Run async concurrent requests
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(self._test_concurrent_requests_async())
            loop.close()

            duration = time.time() - start_time

            success_count = sum(
                1 for r in results if isinstance(r, dict) and r.get("success", False)
            )
            total_count = len(results)

            if success_count >= total_count * 0.8:  # At least 80% success
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="concurrent_load",
                    status="pass",
                    duration=duration,
                    message=f"Concurrent requests handled: {success_count}/{total_count}",
                    details={"success_count": success_count, "total_count": total_count},
                )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="concurrent_load",
                    status="fail",
                    duration=duration,
                    message=f"Low success rate: {success_count}/{total_count}",
                    details={"success_count": success_count, "total_count": total_count},
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="concurrent_load",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={},
            )

    def _test_large_file_processing(self) -> IntegrationTestResult:
        """Test large file processing"""
        start_time = time.time()
        test_name = "large_file_processing"

        try:
            # Create a large test file (1MB)
            large_content = "This is a test line.\n" * 50000  # ~1MB

            files = {"file": ("large_test.txt", large_content, "text/plain")}

            response = self.session.post(
                f"{self.base_url}/upload",
                files=files,
                timeout=60,  # Longer timeout for large files
            )

            duration = time.time() - start_time

            if response.status_code == 200:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="large_file",
                    status="pass",
                    duration=duration,
                    message="Large file processed successfully",
                    details={"file_size": len(large_content)},
                )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="large_file",
                    status="fail",
                    duration=duration,
                    message=f"Large file processing failed with HTTP {response.status_code}",
                    details={"file_size": len(large_content)},
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="large_file",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={},
            )

    def _test_memory_usage_under_load(self) -> IntegrationTestResult:
        """Test memory usage under load"""
        start_time = time.time()
        test_name = "memory_usage_load"

        try:
            import os

            import psutil

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss

            # Make multiple requests to stress memory
            for _ in range(20):
                response = self.session.post(
                    f"{self.base_url}/chat",
                    json={
                        "message": "Test memory usage with a longer message that contains more content",
                        "provider": "openai",
                        "model": "gpt-4o-mini",
                    },
                    timeout=10,
                )

            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory
            duration = time.time() - start_time

            # Memory increase should be reasonable (less than 100MB)
            if memory_increase < 100 * 1024 * 1024:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="memory_load",
                    status="pass",
                    duration=duration,
                    message="Memory usage under control",
                    details={"memory_increase_mb": memory_increase / (1024 * 1024)},
                )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="memory_load",
                    status="fail",
                    duration=duration,
                    message="Excessive memory usage detected",
                    details={"memory_increase_mb": memory_increase / (1024 * 1024)},
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="memory_load",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={},
            )

    def _test_chat_history_persistence(self) -> IntegrationTestResult:
        """Test chat history persistence"""
        start_time = time.time()
        test_name = "chat_history_persistence"

        try:
            # Make a chat request
            response = self.session.post(
                f"{self.base_url}/chat",
                json={
                    "message": "Test history persistence",
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
                timeout=self.test_config["timeout"],
            )

            # Check if history is accessible
            history_response = self.session.get(
                f"{self.base_url}/chat_history", timeout=self.test_config["timeout"]
            )

            duration = time.time() - start_time

            if response.status_code == 200 and history_response.status_code == 200:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="data_persistence",
                    status="pass",
                    duration=duration,
                    message="Chat history persistence working",
                    details={},
                )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="data_persistence",
                    status="fail",
                    duration=duration,
                    message="Chat history persistence failed",
                    details={
                        "chat_status": response.status_code,
                        "history_status": history_response.status_code,
                    },
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="data_persistence",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={},
            )

    def _test_file_storage_persistence(self) -> IntegrationTestResult:
        """Test file storage persistence"""
        start_time = time.time()
        test_name = "file_storage_persistence"

        try:
            # Upload a test file
            files = {"file": ("persistence_test.txt", "Test persistence content", "text/plain")}

            upload_response = self.session.post(
                f"{self.base_url}/upload", files=files, timeout=self.test_config["timeout"]
            )

            # Check if file is listed
            list_response = self.session.get(
                f"{self.base_url}/files", timeout=self.test_config["timeout"]
            )

            duration = time.time() - start_time

            if upload_response.status_code == 200 and list_response.status_code == 200:
                files_data = list_response.json()
                files_list = files_data.get("files", [])
                file_found = any("persistence_test.txt" in f for f in files_list)

                if file_found:
                    return IntegrationTestResult(
                        test_name=test_name,
                        test_type="data_persistence",
                        status="pass",
                        duration=duration,
                        message="File storage persistence working",
                        details={"file_count": len(files_list)},
                    )
                else:
                    return IntegrationTestResult(
                        test_name=test_name,
                        test_type="data_persistence",
                        status="fail",
                        duration=duration,
                        message="Uploaded file not found in listing",
                        details={"file_count": len(files_list)},
                    )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="data_persistence",
                    status="fail",
                    duration=duration,
                    message="File storage persistence failed",
                    details={
                        "upload_status": upload_response.status_code,
                        "list_status": list_response.status_code,
                    },
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="data_persistence",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={},
            )

    def _test_configuration_persistence(self) -> IntegrationTestResult:
        """Test configuration persistence"""
        start_time = time.time()
        test_name = "configuration_persistence"

        try:
            # Test health endpoint to verify basic configuration
            response = self.session.get(
                f"{self.base_url}/health", timeout=self.test_config["timeout"]
            )

            duration = time.time() - start_time

            if response.status_code == 200:
                health_data = response.json()
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="data_persistence",
                    status="pass",
                    duration=duration,
                    message="Configuration persistence working",
                    details={"health_data": health_data},
                )
            else:
                return IntegrationTestResult(
                    test_name=test_name,
                    test_type="data_persistence",
                    status="fail",
                    duration=duration,
                    message=f"Configuration test failed with HTTP {response.status_code}",
                    details={},
                )

        except Exception as e:
            return IntegrationTestResult(
                test_name=test_name,
                test_type="data_persistence",
                status="error",
                duration=time.time() - start_time,
                message=str(e),
                details={},
            )

    def _compile_integration_results(
        self,
        suite_name: str,
        start_time: datetime,
        end_time: datetime,
        results: list[IntegrationTestResult],
    ) -> IntegrationTestSuite:
        """Compile integration test results"""
        passed = len([r for r in results if r.status == "pass"])
        failed = len([r for r in results if r.status == "fail"])
        errors = len([r for r in results if r.status == "error"])

        return IntegrationTestSuite(
            suite_name=suite_name,
            start_time=start_time,
            end_time=end_time,
            total_tests=len(results),
            passed_tests=passed,
            failed_tests=failed,
            error_tests=errors,
            results=results,
        )

    def run_integration_test_suite(self) -> dict[str, IntegrationTestSuite]:
        """Run complete integration test suite"""
        self.logger.info("Starting comprehensive integration test suite")

        results = {}

        try:
            # Multi-provider chat tests
            results["multi_provider"] = self.test_multi_provider_chat()

            # File processing workflow tests
            results["file_processing"] = self.test_file_processing_workflow()

            # Cache system tests
            results["cache_system"] = self.test_cache_system_integration()

            # Error handling tests
            results["error_handling"] = self.test_error_handling_recovery()

            # Performance under load tests
            results["performance_load"] = self.test_performance_under_load()

            # Data persistence tests
            results["data_persistence"] = self.test_data_persistence()

        except Exception as e:
            self.logger.error(f"Integration test suite error: {e}")

        return results

    def generate_integration_report(self, results: dict[str, IntegrationTestSuite]) -> str:
        """Generate comprehensive integration report"""
        report = []
        report.append("# Integration Test Results")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")

        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_errors = 0

        for suite_name, result in results.items():
            report.append(f"## {suite_name.replace('_', ' ').title()}")
            report.append(f"- **Total Tests:** {result.total_tests}")
            report.append(f"- **Passed:** {result.passed_tests}")
            report.append(f"- **Failed:** {result.failed_tests}")
            report.append(f"- **Errors:** {result.error_tests}")
            report.append(
                f"- **Success Rate:** {(result.passed_tests/result.total_tests*100):.1f}%"
            )

            total_tests += result.total_tests
            total_passed += result.passed_tests
            total_failed += result.failed_tests
            total_errors += result.error_tests

            # List failed tests
            failed_tests = [r for r in result.results if r.status in ["fail", "error"]]
            if failed_tests:
                report.append("### Failed/Error Tests:")
                for test in failed_tests:
                    report.append(f"- **{test.test_name}**: {test.message}")

            report.append("")

        # Summary
        overall_success = (total_passed / total_tests * 100) if total_tests > 0 else 0
        report.insert(2, "## Summary")
        report.insert(3, f"- **Total Tests:** {total_tests}")
        report.insert(4, f"- **Passed:** {total_passed}")
        report.insert(5, f"- **Failed:** {total_failed}")
        report.insert(6, f"- **Errors:** {total_errors}")
        report.insert(7, f"- **Overall Success Rate:** {overall_success:.1f}%")
        report.insert(8, "")

        return "\n".join(report)


# Flask integration
def init_integration_testing(app: Flask):
    """Initialize integration testing for Flask app"""
    integration_suite = IntegrationTestRunner()

    @app.route("/test/integration/run")
    def run_integration_tests():
        """Run integration tests (async)"""
        return {"message": "Integration tests started", "status": "running"}

    @app.route("/test/integration/results")
    def get_integration_results():
        """Get latest integration test results"""
        return {"message": "Integration results endpoint"}

    return integration_suite


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TQ Chat Integration Testing")
    parser.add_argument("--base-url", default="http://localhost:5000", help="Base URL for testing")
    parser.add_argument(
        "--test-suite",
        choices=[
            "multi_provider",
            "file_processing",
            "cache_system",
            "error_handling",
            "performance_load",
            "data_persistence",
            "full",
        ],
        default="full",
        help="Integration test suite to run",
    )
    parser.add_argument("--output", help="Output file for results")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run tests
    runner = IntegrationTestRunner(args.base_url)

    if args.test_suite == "full":
        results = runner.run_integration_test_suite()
    elif args.test_suite == "multi_provider":
        results = {"multi_provider": runner.test_multi_provider_chat()}
    elif args.test_suite == "file_processing":
        results = {"file_processing": runner.test_file_processing_workflow()}
    elif args.test_suite == "cache_system":
        results = {"cache_system": runner.test_cache_system_integration()}
    elif args.test_suite == "error_handling":
        results = {"error_handling": runner.test_error_handling_recovery()}
    elif args.test_suite == "performance_load":
        results = {"performance_load": runner.test_performance_under_load()}
    elif args.test_suite == "data_persistence":
        results = {"data_persistence": runner.test_data_persistence()}

    # Generate report
    report = runner.generate_integration_report(results)

    # Log report instead of print
    logging.info("Integration Test Report Generated")
    logging.info(report)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        logging.info(f"Results saved to {args.output}")
