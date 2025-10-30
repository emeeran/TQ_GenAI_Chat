#!/usr/bin/env python3
"""
Performance Benchmark Script

Zero-risk performance validation script.
Tests and measures application performance without affecting production data.
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any
import aiohttp
import statistics

logger = logging.getLogger(__name__)

class PerformanceBenchmark:
    """
    Zero-risk performance benchmarking tool.

    Tests various aspects of application performance:
    - API response times
    - Throughput under load
    - Error rates
    - Memory usage trends
    - Caching effectiveness
    """

    def __init__(self, base_url: str = "http://127.0.0.1:5005"):
        self.base_url = base_url
        self.results: Dict[str, Any] = {}
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def measure_response_time(self, endpoint: str, method: str = "GET", data: Dict = None) -> float:
        """Measure response time for a single request"""
        start_time = time.time()
        try:
            if method == "GET":
                async with self.session.get(f"{self.base_url}{endpoint}") as response:
                    await response.text()  # Consume response
                    return time.time() - start_time
            elif method == "POST" and data:
                async with self.session.post(f"{self.base_url}{endpoint}", json=data) as response:
                    await response.text()  # Consume response
                    return time.time() - start_time
        except Exception as e:
            logger.warning(f"Request failed for {endpoint}: {e}")
            return -1  # Indicates error

    async def benchmark_endpoint(self, endpoint: str, requests: int = 10) -> Dict[str, Any]:
        """Benchmark a specific endpoint with multiple requests"""
        print(f"🔍 Benchmarking {endpoint} with {requests} requests...")

        response_times = []
        errors = 0

        for i in range(requests):
            response_time = await self.measure_response_time(endpoint)
            if response_time >= 0:
                response_times.append(response_time * 1000)  # Convert to ms
            else:
                errors += 1

            if i % 5 == 0:
                print(f"  Progress: {i}/{requests} requests")

        if response_times:
            return {
                "endpoint": endpoint,
                "total_requests": requests,
                "successful_requests": len(response_times),
                "errors": errors,
                "avg_response_time_ms": statistics.mean(response_times),
                "min_response_time_ms": min(response_times),
                "max_response_time_ms": max(response_times),
                "median_response_time_ms": statistics.median(response_times),
                "p95_response_time_ms": self._percentile(response_times, 95),
                "p99_response_time_ms": self._percentile(response_times, 99),
                "error_rate_percent": (errors / requests) * 100
            }
        else:
            return {
                "endpoint": endpoint,
                "total_requests": requests,
                "successful_requests": 0,
                "errors": errors,
                "error_rate_percent": 100.0,
                "avg_response_time_ms": 0
            }

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * (percentile / 100))
        return sorted_data[min(index, len(sorted_data) - 1)]

    async def run_concurrent_benchmark(self, endpoint: str, concurrent_requests: int = 5, total_requests: int = 50) -> Dict[str, Any]:
        """Test performance under concurrent load"""
        print(f"🚀 Running concurrent benchmark on {endpoint}")
        print(f"   Concurrency: {concurrent_requests}, Total requests: {total_requests}")

        semaphore = asyncio.Semaphore(concurrent_requests)
        response_times = []
        errors = 0
        start_time = time.time()

        async def bounded_request():
            async with semaphore:
                response_time = await self.measure_response_time(endpoint)
                return response_time

        tasks = [bounded_request() for _ in range(total_requests)]
        results = await asyncio.gather(*tasks)

        total_time = time.time() - start_time

        for response_time in results:
            if response_time >= 0:
                response_times.append(response_time * 1000)
            else:
                errors += 1

        if response_times:
            return {
                "endpoint": endpoint,
                "concurrent_requests": concurrent_requests,
                "total_requests": total_requests,
                "total_time_seconds": total_time,
                "requests_per_second": total_requests / total_time,
                "successful_requests": len(response_times),
                "errors": errors,
                "avg_response_time_ms": statistics.mean(response_times),
                "p95_response_time_ms": self._percentile(response_times, 95),
                "error_rate_percent": (errors / total_requests) * 100
            }
        else:
            return {
                "endpoint": endpoint,
                "concurrent_requests": concurrent_requests,
                "total_requests": total_requests,
                "total_time_seconds": total_time,
                "requests_per_second": 0,
                "errors": total_requests,
                "error_rate_percent": 100.0
            }

    async def test_caching_effectiveness(self, endpoint: str) -> Dict[str, Any]:
        """Test if caching headers are working correctly"""
        print(f"💾 Testing caching effectiveness for {endpoint}")

        # Make first request
        first_response_time = await self.measure_response_time(endpoint) * 1000

        # Make second request (should be cached if applicable)
        second_response_time = await self.measure_response_time(endpoint) * 1000

        # Check response headers
        try:
            async with self.session.get(f"{self.base_url}{endpoint}") as response:
                cache_control = response.headers.get('Cache-Control', '')
                etag = response.headers.get('ETag', '')
                expires = response.headers.get('Expires', '')

                return {
                    "endpoint": endpoint,
                    "first_request_ms": first_response_time,
                    "second_request_ms": second_response_time,
                    "improvement_percent": ((first_response_time - second_response_time) / first_response_time * 100) if first_response_time > 0 else 0,
                    "cache_control": cache_control,
                    "etag": etag[:50] + '...' if len(etag) > 50 else etag,
                    "expires": expires
                }
        except Exception as e:
            return {
                "endpoint": endpoint,
                "error": str(e),
                "first_request_ms": first_response_time,
                "second_request_ms": second_response_time
            }

    async def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive performance benchmark"""
        print("🎯 Starting Comprehensive Performance Benchmark")
        print("=" * 50)

        # Define endpoints to test
        endpoints = [
            "/health",
            "/metrics",
            "/",
        ]

        # Basic endpoint benchmarks
        basic_results = []
        for endpoint in endpoints:
            result = await self.benchmark_endpoint(endpoint, requests=20)
            basic_results.append(result)
            print(f"✅ {endpoint}: {result['avg_response_time_ms']:.2f}ms avg, {result['error_rate_percent']:.1f}% errors")

        # Concurrent benchmarks
        concurrent_results = []
        for endpoint in ["/health", "/metrics"]:  # Test on lightweight endpoints
            result = await self.run_concurrent_benchmark(endpoint, concurrent_requests=10, total_requests=100)
            concurrent_results.append(result)
            print(f"🚀 {endpoint}: {result['requests_per_second']:.1f} req/s, {result['error_rate_percent']:.1f}% errors")

        # Caching tests
        caching_results = []
        for endpoint in ["/health", "/metrics"]:
            result = await self.test_caching_effectiveness(endpoint)
            caching_results.append(result)
            cache_status = "✅" if result.get('cache_control') else "❌"
            print(f"💾 {endpoint}: {cache_status} {result.get('cache_control', 'No caching headers')}")

        # Get application metrics
        try:
            async with self.session.get(f"{self.base_url}/metrics") as response:
                app_metrics = await response.json()
        except Exception as e:
            app_metrics = {"error": str(e)}

        # Compile results
        benchmark_results = {
            "timestamp": time.time(),
            "benchmark_summary": {
                "total_endpoints_tested": len(endpoints),
                "total_requests_made": sum(r["total_requests"] for r in basic_results + concurrent_results),
                "overall_success_rate": 100 - (statistics.mean([r.get("error_rate_percent", 0) for r in basic_results + concurrent_results])),
            },
            "basic_benchmarks": basic_results,
            "concurrent_benchmarks": concurrent_results,
            "caching_tests": caching_results,
            "application_metrics": app_metrics,
            "performance_grade": self._calculate_performance_grade(basic_results + concurrent_results)
        }

        return benchmark_results

    def _calculate_performance_grade(self, results: List[Dict]) -> str:
        """Calculate overall performance grade"""
        if not results:
            return "N/A"

        avg_response_times = [r.get("avg_response_time_ms", 0) for r in results]
        error_rates = [r.get("error_rate_percent", 0) for r in results]

        avg_response_time = statistics.mean(avg_response_times)
        avg_error_rate = statistics.mean(error_rates)

        if avg_response_time < 100 and avg_error_rate == 0:
            return "A+ (Excellent)"
        elif avg_response_time < 200 and avg_error_rate < 1:
            return "A (Very Good)"
        elif avg_response_time < 500 and avg_error_rate < 5:
            return "B (Good)"
        elif avg_response_time < 1000 and avg_error_rate < 10:
            return "C (Fair)"
        else:
            return "D (Needs Improvement)"

    def save_results(self, results: Dict[str, Any], filename: str = None) -> str:
        """Save benchmark results to file"""
        if filename is None:
            filename = f"performance_benchmark_{int(time.time())}.json"

        filepath = Path(filename)
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"📄 Benchmark results saved to {filepath}")
        return str(filepath)

async def main():
    """Run the performance benchmark"""
    import argparse

    parser = argparse.ArgumentParser(description="Run performance benchmarks")
    parser.add_argument("--url", default="http://127.0.0.1:5005", help="Base URL to test")
    parser.add_argument("--output", help="Output file for results")
    args = parser.parse_args()

    async with PerformanceBenchmark(args.url) as benchmark:
        results = await benchmark.run_comprehensive_benchmark()

        # Print summary
        print("\n" + "=" * 50)
        print("📊 BENCHMARK SUMMARY")
        print("=" * 50)
        print(f"Performance Grade: {results['performance_grade']}")
        print(f"Total Requests: {results['benchmark_summary']['total_requests_made']}")
        print(f"Success Rate: {results['benchmark_summary']['overall_success_rate']:.1f}%")

        # Save results
        output_file = benchmark.save_results(results, args.output)

        return results

if __name__ == "__main__":
    asyncio.run(main())