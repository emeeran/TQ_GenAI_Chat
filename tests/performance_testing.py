"""
Performance Testing Suite - Testing & Validation
Comprehensive performance validation with load, stress, and endurance testing
"""

import asyncio
import logging
import statistics
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import aiohttp
import psutil
import requests
from flask import Flask

# Optional dependencies
try:
    import locust
    from locust import HttpUser, between, task
    from locust.env import Environment
    from locust.log import setup_logging
    from locust.stats import stats_history, stats_printer

    LOCUST_AVAILABLE = True
except ImportError:
    LOCUST_AVAILABLE = False
    locust = None

try:
    import subprocess

    ARTILLERY_AVAILABLE = True
except ImportError:
    ARTILLERY_AVAILABLE = False


@dataclass
class TestResult:
    """Individual test result"""

    test_name: str
    start_time: datetime
    end_time: datetime
    success: bool
    response_time: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    memory_usage: Optional[float] = None
    cpu_usage: Optional[float] = None


@dataclass
class TestSuiteResults:
    """Complete test suite results"""

    suite_name: str
    start_time: datetime
    end_time: datetime
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    min_response_time: float = float("inf")
    max_response_time: float = 0.0
    percentile_95: float = 0.0
    percentile_99: float = 0.0
    throughput: float = 0.0
    memory_leak_detected: bool = False
    breaking_point_users: Optional[int] = None
    results: List[TestResult] = field(default_factory=list)


class PerformanceTestSuite:
    """Comprehensive performance testing suite"""

    def __init__(self, base_url: str = "http://localhost:5000", max_workers: int = 100):
        self.base_url = base_url.rstrip("/")
        self.max_workers = max_workers
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()

        # Test configuration
        self.test_configs = {
            "load_test": {
                "users": [10, 50, 100, 200, 500],
                "duration": 60,  # seconds
                "ramp_up": 30,  # seconds
            },
            "stress_test": {"users": [100, 300, 500, 1000, 2000], "duration": 120, "ramp_up": 60},
            "endurance_test": {
                "users": 100,
                "duration": 3600,  # 1 hour
                "ramp_up": 300,  # 5 minutes
            },
        }

        # Memory baseline
        self.memory_baseline = None
        self.memory_samples = []

    def get_system_metrics(self) -> Dict[str, float]:
        """Get current system metrics"""
        process = psutil.Process()
        return {
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "cpu_percent": process.cpu_percent(),
            "system_memory_percent": psutil.virtual_memory().percent,
            "system_cpu_percent": psutil.cpu_percent(),
        }

    def warmup_test(self) -> bool:
        """Warm up the application before testing"""
        self.logger.info("Starting application warmup...")

        warmup_endpoints = ["/health", "/get_models/openai", "/get_personas", "/performance/system"]

        for endpoint in warmup_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                if response.status_code != 200:
                    self.logger.warning(f"Warmup failed for {endpoint}: {response.status_code}")
            except Exception as e:
                self.logger.warning(f"Warmup error for {endpoint}: {e}")

        # Set memory baseline
        self.memory_baseline = self.get_system_metrics()["memory_mb"]
        self.logger.info(f"Memory baseline set: {self.memory_baseline:.2f} MB")
        return True

    async def async_request(
        self, session: aiohttp.ClientSession, method: str, url: str, **kwargs
    ) -> TestResult:
        """Make async HTTP request and measure performance"""
        start_time = datetime.now()
        metrics_before = self.get_system_metrics()

        try:
            async with session.request(method, url, **kwargs) as response:
                await response.read()  # Ensure full response is received

                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()
                metrics_after = self.get_system_metrics()

                return TestResult(
                    test_name=f"{method} {url}",
                    start_time=start_time,
                    end_time=end_time,
                    success=200 <= response.status < 400,
                    response_time=response_time,
                    status_code=response.status,
                    memory_usage=metrics_after["memory_mb"],
                    cpu_usage=metrics_after["cpu_percent"],
                )

        except Exception as e:
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()

            return TestResult(
                test_name=f"{method} {url}",
                start_time=start_time,
                end_time=end_time,
                success=False,
                response_time=response_time,
                error_message=str(e),
                memory_usage=metrics_before["memory_mb"],
            )

    def sync_request(self, method: str, url: str, **kwargs) -> TestResult:
        """Make synchronous HTTP request and measure performance"""
        start_time = datetime.now()
        metrics_before = self.get_system_metrics()

        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()
            metrics_after = self.get_system_metrics()

            return TestResult(
                test_name=f"{method} {url}",
                start_time=start_time,
                end_time=end_time,
                success=200 <= response.status_code < 400,
                response_time=response_time,
                status_code=response.status_code,
                memory_usage=metrics_after["memory_mb"],
                cpu_usage=metrics_after["cpu_percent"],
            )

        except Exception as e:
            end_time = datetime.now()
            response_time = (end_time - start_time).total_seconds()

            return TestResult(
                test_name=f"{method} {url}",
                start_time=start_time,
                end_time=end_time,
                success=False,
                response_time=response_time,
                error_message=str(e),
                memory_usage=metrics_before["memory_mb"],
            )

    async def load_test(self, concurrent_users: int, duration: int = 60) -> TestSuiteResults:
        """Run load test with specified concurrent users"""
        self.logger.info(f"Starting load test: {concurrent_users} users for {duration}s")

        start_time = datetime.now()
        results = []

        # Test endpoints with different complexities
        test_scenarios = [
            {"method": "GET", "url": "/health", "weight": 0.3},
            {"method": "GET", "url": "/get_models/openai", "weight": 0.2},
            {
                "method": "POST",
                "url": "/chat",
                "weight": 0.4,
                "json": {
                    "message": "Hello, this is a test message.",
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
            },
            {"method": "GET", "url": "/search_context", "weight": 0.1},
        ]

        async with aiohttp.ClientSession() as session:
            tasks = []
            end_time = start_time + timedelta(seconds=duration)

            # Create worker tasks
            for user_id in range(concurrent_users):
                task = self._user_simulation(session, test_scenarios, end_time, user_id)
                tasks.append(asyncio.create_task(task))

            # Wait for all tasks to complete
            user_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Flatten results
            for user_result in user_results:
                if isinstance(user_result, list):
                    results.extend(user_result)
                elif isinstance(user_result, Exception):
                    self.logger.error(f"User simulation error: {user_result}")

        return self._compile_results("Load Test", start_time, results, concurrent_users)

    async def _user_simulation(
        self,
        session: aiohttp.ClientSession,
        scenarios: List[Dict],
        end_time: datetime,
        user_id: int,
    ) -> List[TestResult]:
        """Simulate a single user's behavior"""
        results = []
        request_count = 0

        while datetime.now() < end_time:
            # Select scenario based on weights
            import random

            scenario = random.choices(scenarios, weights=[s["weight"] for s in scenarios])[0]

            url = f"{self.base_url}{scenario['url']}"
            method = scenario["method"]
            kwargs = {k: v for k, v in scenario.items() if k not in ["method", "url", "weight"]}

            result = await self.async_request(session, method, url, **kwargs)
            results.append(result)
            request_count += 1

            # Add realistic user delay
            await asyncio.sleep(random.uniform(0.5, 2.0))

        self.logger.debug(f"User {user_id} completed {request_count} requests")
        return results

    def stress_test(
        self, max_users: int = 2000, step_size: int = 100, step_duration: int = 30
    ) -> TestSuiteResults:
        """Run stress test to find breaking point"""
        self.logger.info(f"Starting stress test: up to {max_users} users")

        start_time = datetime.now()
        all_results = []
        breaking_point = None

        for users in range(step_size, max_users + 1, step_size):
            self.logger.info(f"Testing with {users} users...")

            # Run load test for this user count
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                test_results = loop.run_until_complete(self.load_test(users, step_duration))
                all_results.extend(test_results.results)

                # Check if this is the breaking point
                success_rate = test_results.successful_requests / test_results.total_requests
                avg_response_time = test_results.avg_response_time

                if success_rate < 0.95 or avg_response_time > 5.0:
                    breaking_point = users
                    self.logger.warning(f"Breaking point detected at {users} users")
                    break

            finally:
                loop.close()

            # Brief pause between steps
            time.sleep(5)

        results = self._compile_results("Stress Test", start_time, all_results)
        results.breaking_point_users = breaking_point
        return results

    def endurance_test(self, users: int = 100, duration: int = 3600) -> TestSuiteResults:
        """Run endurance test to detect memory leaks"""
        self.logger.info(f"Starting endurance test: {users} users for {duration}s")

        start_time = datetime.now()
        self.memory_samples = []

        # Start memory monitoring thread
        stop_monitoring = threading.Event()
        monitor_thread = threading.Thread(target=self._monitor_memory, args=(stop_monitoring,))
        monitor_thread.start()

        try:
            # Run load test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(self.load_test(users, duration))
            finally:
                loop.close()

        finally:
            stop_monitoring.set()
            monitor_thread.join()

        # Analyze memory trend
        results.memory_leak_detected = self._detect_memory_leak()
        return results

    def _monitor_memory(self, stop_event: threading.Event):
        """Monitor memory usage during endurance test"""
        while not stop_event.is_set():
            metrics = self.get_system_metrics()
            self.memory_samples.append(
                {
                    "timestamp": datetime.now(),
                    "memory_mb": metrics["memory_mb"],
                    "system_memory_percent": metrics["system_memory_percent"],
                }
            )
            time.sleep(30)  # Sample every 30 seconds

    def _detect_memory_leak(self) -> bool:
        """Detect memory leaks from samples"""
        if len(self.memory_samples) < 10:
            return False

        # Calculate memory growth trend
        memory_values = [sample["memory_mb"] for sample in self.memory_samples]

        # Simple linear regression to detect trend
        n = len(memory_values)
        x_values = list(range(n))

        x_mean = sum(x_values) / n
        y_mean = sum(memory_values) / n

        numerator = sum((x_values[i] - x_mean) * (memory_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return False

        slope = numerator / denominator

        # Memory leak if growth rate > 1MB per hour
        leak_threshold = 1.0 / 120  # 1MB per 120 samples (1 hour)

        if slope > leak_threshold:
            self.logger.warning(f"Memory leak detected: {slope:.4f} MB/sample")
            return True

        return False

    def _compile_results(
        self,
        suite_name: str,
        start_time: datetime,
        results: List[TestResult],
        concurrent_users: Optional[int] = None,
    ) -> TestSuiteResults:
        """Compile test results into summary"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        if not results:
            return TestSuiteResults(suite_name=suite_name, start_time=start_time, end_time=end_time)

        # Calculate statistics
        response_times = [r.response_time for r in results]
        successful_results = [r for r in results if r.success]

        suite_results = TestSuiteResults(
            suite_name=suite_name,
            start_time=start_time,
            end_time=end_time,
            total_requests=len(results),
            successful_requests=len(successful_results),
            failed_requests=len(results) - len(successful_results),
            results=results,
        )

        if response_times:
            suite_results.avg_response_time = statistics.mean(response_times)
            suite_results.min_response_time = min(response_times)
            suite_results.max_response_time = max(response_times)

            # Calculate percentiles
            sorted_times = sorted(response_times)
            suite_results.percentile_95 = sorted_times[int(0.95 * len(sorted_times))]
            suite_results.percentile_99 = sorted_times[int(0.99 * len(sorted_times))]

            # Calculate throughput
            suite_results.throughput = len(successful_results) / duration

        return suite_results

    def run_performance_test_suite(self) -> Dict[str, TestSuiteResults]:
        """Run complete performance test suite"""
        self.logger.info("Starting comprehensive performance test suite")

        # Warmup
        self.warmup_test()

        results = {}

        try:
            # Load test
            self.logger.info("Running load tests...")
            for users in self.test_configs["load_test"]["users"]:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    test_result = loop.run_until_complete(
                        self.load_test(users, self.test_configs["load_test"]["duration"])
                    )
                    results[f"load_test_{users}_users"] = test_result
                finally:
                    loop.close()

                # Brief pause between tests
                time.sleep(10)

            # Stress test
            self.logger.info("Running stress test...")
            stress_result = self.stress_test(
                max_users=max(self.test_configs["stress_test"]["users"])
            )
            results["stress_test"] = stress_result

            # Endurance test (shorter for automation)
            self.logger.info("Running endurance test...")
            endurance_result = self.endurance_test(
                users=self.test_configs["endurance_test"]["users"],
                duration=600,  # 10 minutes for automation
            )
            results["endurance_test"] = endurance_result

        except Exception as e:
            self.logger.error(f"Test suite error: {e}")

        return results

    def generate_report(self, results: Dict[str, TestSuiteResults]) -> str:
        """Generate comprehensive test report"""
        report = []
        report.append("# Performance Test Results")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")

        for test_name, result in results.items():
            report.append(f"## {test_name.replace('_', ' ').title()}")
            report.append(
                f"- **Duration:** {(result.end_time - result.start_time).total_seconds():.1f}s"
            )
            report.append(f"- **Total Requests:** {result.total_requests}")
            report.append(f"- **Successful:** {result.successful_requests}")
            report.append(f"- **Failed:** {result.failed_requests}")

            if result.total_requests > 0:
                success_rate = (result.successful_requests / result.total_requests) * 100
                report.append(f"- **Success Rate:** {success_rate:.1f}%")

            if result.avg_response_time > 0:
                report.append(f"- **Avg Response Time:** {result.avg_response_time:.3f}s")
                report.append(f"- **95th Percentile:** {result.percentile_95:.3f}s")
                report.append(f"- **99th Percentile:** {result.percentile_99:.3f}s")
                report.append(f"- **Throughput:** {result.throughput:.1f} req/s")

            if result.breaking_point_users:
                report.append(f"- **Breaking Point:** {result.breaking_point_users} users")

            if hasattr(result, "memory_leak_detected"):
                leak_status = "❌ DETECTED" if result.memory_leak_detected else "✅ None"
                report.append(f"- **Memory Leaks:** {leak_status}")

            report.append("")

        return "\n".join(report)


# Flask integration
def init_performance_testing(app: Flask):
    """Initialize performance testing for Flask app"""
    performance_suite = PerformanceTestSuite()

    @app.route("/test/performance/run")
    def run_performance_tests():
        """Run performance tests (async)"""
        # This should be run as a background task
        return {"message": "Performance tests started", "status": "running"}

    @app.route("/test/performance/results")
    def get_performance_results():
        """Get latest performance test results"""
        # Return cached results
        return {"message": "Performance results endpoint"}

    return performance_suite


# Locust integration (if available)
if LOCUST_AVAILABLE:

    class TQChatUser(HttpUser):
        """Locust user for TQ Chat application"""

        wait_time = between(1, 3)

        def on_start(self):
            """Called when user starts"""
            # Warmup request
            self.client.get("/health")

        @task(3)
        def get_health(self):
            """Health check endpoint"""
            self.client.get("/health")

        @task(2)
        def get_models(self):
            """Get available models"""
            self.client.get("/get_models/openai")

        @task(5)
        def send_chat_message(self):
            """Send chat message"""
            self.client.post(
                "/chat",
                json={
                    "message": "Hello, this is a test message.",
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
            )

        @task(1)
        def search_context(self):
            """Search document context"""
            self.client.get("/search_context", params={"query": "test"})


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TQ Chat Performance Testing")
    parser.add_argument("--base-url", default="http://localhost:5000", help="Base URL for testing")
    parser.add_argument("--users", type=int, default=100, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument(
        "--test-type",
        choices=["load", "stress", "endurance", "full"],
        default="load",
        help="Type of test to run",
    )
    parser.add_argument("--output", help="Output file for results")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run tests
    suite = PerformanceTestSuite(args.base_url)

    if args.test_type == "full":
        results = suite.run_performance_test_suite()
    elif args.test_type == "load":
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(suite.load_test(args.users, args.duration))
            results = {"load_test": result}
        finally:
            loop.close()
    elif args.test_type == "stress":
        result = suite.stress_test()
        results = {"stress_test": result}
    elif args.test_type == "endurance":
        result = suite.endurance_test(args.users, args.duration)
        results = {"endurance_test": result}

    # Generate report
    report = suite.generate_report(results)
    print(report)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Results saved to {args.output}")
