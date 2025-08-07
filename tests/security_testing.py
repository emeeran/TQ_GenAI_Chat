"""
Security Testing Suite - Testing & Validation
Comprehensive security validation including penetration testing, rate limiting,
and input validation testing
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import requests
from flask import Flask

# Security testing payloads
INJECTION_PAYLOADS = [
    # SQL Injection
    "' OR '1'='1",
    "'; DROP TABLE users; --",
    "' UNION SELECT * FROM information_schema.tables --",
    # XSS
    "<script>alert('XSS')</script>",
    "javascript:alert('XSS')",
    "<img src=x onerror=alert('XSS')>",
    # Command Injection
    "; ls -la",
    "| cat /etc/passwd",
    "&& whoami",
    # Path Traversal
    "../../../etc/passwd",
    "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
    # XXE
    "<?xml version='1.0'?><!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><foo>&xxe;</foo>",
    # LDAP Injection
    "*)(uid=*))(|(uid=*",
    # NoSQL Injection
    "{'$ne': null}",
    "{'$gt': ''}",
]

LARGE_PAYLOADS = [
    "A" * 10000,  # Buffer overflow attempt
    "A" * 100000,  # Large payload
    json.dumps({"key": "A" * 50000}),  # Large JSON
]


@dataclass
class SecurityTestResult:
    """Security test result"""

    test_name: str
    endpoint: str
    payload: str
    method: str
    status_code: int
    response_time: float
    response_size: int
    vulnerability_detected: bool = False
    severity: str = "low"  # low, medium, high, critical
    description: str = ""
    mitigation: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SecurityTestSuite:
    """Security test suite results"""

    test_name: str
    start_time: datetime
    end_time: datetime
    total_tests: int = 0
    vulnerabilities_found: int = 0
    high_severity: int = 0
    medium_severity: int = 0
    low_severity: int = 0
    results: list[SecurityTestResult] = field(default_factory=list)


class SecurityTestRunner:
    """Comprehensive security testing suite"""

    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)

        # Common headers for testing
        self.test_headers = {
            "User-Agent": "SecurityTestRunner/1.0",
            "Accept": "application/json, text/html",
            "Content-Type": "application/json",
        }

        # Rate limiting test configuration
        self.rate_limit_config = {
            "requests_per_minute": 60,
            "burst_requests": 100,
            "test_duration": 60,
        }

    def test_input_validation(self) -> SecurityTestSuite:
        """Test input validation across all endpoints"""
        self.logger.info("Starting input validation tests...")
        start_time = datetime.now()
        results = []

        # Define test endpoints with their expected parameters
        test_endpoints = [
            {
                "url": "/chat",
                "method": "POST",
                "params": ["message", "provider", "model"],
                "base_payload": {"message": "test", "provider": "openai", "model": "gpt-4o-mini"},
            },
            {
                "url": "/search_context",
                "method": "GET",
                "params": ["query"],
                "base_payload": {"query": "test"},
            },
            {"url": "/upload", "method": "POST", "params": ["file"], "base_payload": {}},
        ]

        # Test each endpoint with malicious payloads
        for endpoint in test_endpoints:
            for param in endpoint["params"]:
                for payload in INJECTION_PAYLOADS:
                    result = self._test_endpoint_with_payload(endpoint, param, payload, "injection")
                    results.append(result)

                # Test with large payloads
                for payload in LARGE_PAYLOADS:
                    result = self._test_endpoint_with_payload(
                        endpoint, param, payload, "buffer_overflow"
                    )
                    results.append(result)

        end_time = datetime.now()
        return self._compile_security_results("Input Validation", start_time, end_time, results)

    def test_authentication_authorization(self) -> SecurityTestSuite:
        """Test authentication and authorization mechanisms"""
        self.logger.info("Starting authentication/authorization tests...")
        start_time = datetime.now()
        results = []

        # Test endpoints that might require authentication
        protected_endpoints = [
            "/admin",
            "/api/admin",
            "/config",
            "/settings",
            "/users",
            "/performance/system",
            "/cache/invalidate",
        ]

        for endpoint in protected_endpoints:
            # Test without authentication
            result = self._test_unauthorized_access(endpoint)
            results.append(result)

            # Test with invalid tokens
            invalid_tokens = [
                "Bearer invalid_token",
                "Bearer " + "A" * 1000,
                "Basic invalid_base64",
                "Token malformed",
            ]

            for token in invalid_tokens:
                result = self._test_invalid_auth(endpoint, token)
                results.append(result)

        end_time = datetime.now()
        return self._compile_security_results(
            "Authentication/Authorization", start_time, end_time, results
        )

    def test_rate_limiting(self) -> SecurityTestSuite:
        """Test rate limiting implementation"""
        self.logger.info("Starting rate limiting tests...")
        start_time = datetime.now()
        results = []

        # Test burst requests
        burst_result = self._test_burst_requests()
        results.append(burst_result)

        # Test sustained rate limiting
        sustained_result = self._test_sustained_rate_limit()
        results.append(sustained_result)

        # Test rate limiting bypass attempts
        bypass_results = self._test_rate_limit_bypass()
        results.extend(bypass_results)

        end_time = datetime.now()
        return self._compile_security_results("Rate Limiting", start_time, end_time, results)

    def test_security_headers(self) -> SecurityTestSuite:
        """Test security headers implementation"""
        self.logger.info("Starting security headers tests...")
        start_time = datetime.now()
        results = []

        # Required security headers
        required_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": ["DENY", "SAMEORIGIN"],
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=",
            "Content-Security-Policy": "default-src",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

        # Test main endpoints for security headers
        test_urls = ["/", "/health", "/chat", "/upload"]

        for url in test_urls:
            try:
                response = self.session.get(
                    f"{self.base_url}{url}", headers=self.test_headers, timeout=10
                )

                for header, expected_value in required_headers.items():
                    result = self._check_security_header(
                        url, header, expected_value, response.headers
                    )
                    results.append(result)

            except Exception as e:
                self.logger.error(f"Error testing {url}: {e}")

        end_time = datetime.now()
        return self._compile_security_results("Security Headers", start_time, end_time, results)

    def test_information_disclosure(self) -> SecurityTestSuite:
        """Test for information disclosure vulnerabilities"""
        self.logger.info("Starting information disclosure tests...")
        start_time = datetime.now()
        results = []

        # Test for sensitive information in responses
        disclosure_tests = [
            {
                "url": "/health",
                "check_for": ["version", "debug", "environment", "secret", "key"],
                "severity": "medium",
            },
            {
                "url": "/api/debug",
                "check_for": ["stack trace", "file path", "database"],
                "severity": "high",
            },
            {
                "url": "/.env",
                "check_for": ["API_KEY", "SECRET", "PASSWORD"],
                "severity": "critical",
            },
            {"url": "/config.json", "check_for": ["password", "secret", "key"], "severity": "high"},
        ]

        for test in disclosure_tests:
            result = self._test_information_disclosure(test)
            results.append(result)

        end_time = datetime.now()
        return self._compile_security_results(
            "Information Disclosure", start_time, end_time, results
        )

    def run_penetration_tests(self) -> SecurityTestSuite:
        """Run basic penetration testing"""
        self.logger.info("Starting penetration tests...")
        start_time = datetime.now()
        results = []

        # Directory traversal tests
        traversal_payloads = [
            "../etc/passwd",
            "..\\windows\\system32\\drivers\\etc\\hosts",
            "/etc/passwd",
            "C:\\windows\\system32\\drivers\\etc\\hosts",
        ]

        for payload in traversal_payloads:
            # Test file upload with traversal
            result = self._test_directory_traversal("/upload", payload)
            results.append(result)

            # Test search with traversal
            result = self._test_directory_traversal("/search_context", payload)
            results.append(result)

        # Test for SSRF vulnerabilities
        ssrf_payloads = [
            "http://localhost:22",
            "http://127.0.0.1:8080",
            "file:///etc/passwd",
            "ftp://internal.server/",
        ]

        for payload in ssrf_payloads:
            result = self._test_ssrf("/chat", payload)
            results.append(result)

        end_time = datetime.now()
        return self._compile_security_results("Penetration Testing", start_time, end_time, results)

    def _test_endpoint_with_payload(
        self, endpoint: dict, param: str, payload: str, test_type: str
    ) -> SecurityTestResult:
        """Test endpoint with malicious payload"""
        start_time = time.time()

        try:
            test_payload = endpoint["base_payload"].copy()
            test_payload[param] = payload

            if endpoint["method"] == "GET":
                response = self.session.get(
                    f"{self.base_url}{endpoint['url']}",
                    params=test_payload,
                    headers=self.test_headers,
                    timeout=10,
                )
            else:
                response = self.session.post(
                    f"{self.base_url}{endpoint['url']}",
                    json=test_payload,
                    headers=self.test_headers,
                    timeout=10,
                )

            response_time = time.time() - start_time

            # Analyze response for vulnerabilities
            vulnerability_detected = self._analyze_response_for_vulnerabilities(
                response, payload, test_type
            )

            severity = "high" if vulnerability_detected else "low"
            description = f"{test_type} test with payload: {payload[:50]}..."

            return SecurityTestResult(
                test_name=f"{test_type}_{param}",
                endpoint=endpoint["url"],
                payload=payload,
                method=endpoint["method"],
                status_code=response.status_code,
                response_time=response_time,
                response_size=len(response.content),
                vulnerability_detected=vulnerability_detected,
                severity=severity,
                description=description,
            )

        except Exception as e:
            return SecurityTestResult(
                test_name=f"{test_type}_{param}",
                endpoint=endpoint["url"],
                payload=payload,
                method=endpoint["method"],
                status_code=0,
                response_time=time.time() - start_time,
                response_size=0,
                vulnerability_detected=False,
                severity="low",
                description=f"Request failed: {str(e)}",
            )

    def _test_burst_requests(self) -> SecurityTestResult:
        """Test burst request rate limiting"""
        start_time = time.time()
        burst_count = self.rate_limit_config["burst_requests"]

        success_count = 0
        rate_limited_count = 0

        for i in range(burst_count):
            try:
                response = self.session.get(
                    f"{self.base_url}/health", headers=self.test_headers, timeout=5
                )

                if response.status_code == 200:
                    success_count += 1
                elif response.status_code == 429:
                    rate_limited_count += 1

            except Exception:
                pass

        response_time = time.time() - start_time

        # Rate limiting should kick in before all requests succeed
        vulnerability_detected = success_count >= burst_count * 0.9
        severity = "medium" if vulnerability_detected else "low"

        return SecurityTestResult(
            test_name="burst_rate_limit",
            endpoint="/health",
            payload=f"{burst_count} requests",
            method="GET",
            status_code=200 if success_count > 0 else 429,
            response_time=response_time,
            response_size=0,
            vulnerability_detected=vulnerability_detected,
            severity=severity,
            description=f"Burst test: {success_count}/{burst_count} succeeded, {rate_limited_count} rate limited",
        )

    def _test_sustained_rate_limit(self) -> SecurityTestResult:
        """Test sustained rate limiting"""
        start_time = time.time()
        duration = 30  # 30 seconds test
        request_count = 0
        rate_limited_count = 0

        end_time = start_time + duration

        while time.time() < end_time:
            try:
                response = self.session.get(
                    f"{self.base_url}/health", headers=self.test_headers, timeout=5
                )

                request_count += 1
                if response.status_code == 429:
                    rate_limited_count += 1

            except Exception:
                pass

            time.sleep(0.1)  # 10 requests per second

        total_time = time.time() - start_time
        requests_per_minute = (request_count / total_time) * 60

        # Should be rate limited if exceeding configured limit
        expected_limit = self.rate_limit_config["requests_per_minute"]
        vulnerability_detected = (
            requests_per_minute > expected_limit * 1.2 and rate_limited_count == 0
        )

        severity = "medium" if vulnerability_detected else "low"

        return SecurityTestResult(
            test_name="sustained_rate_limit",
            endpoint="/health",
            payload=f"{request_count} requests in {total_time:.1f}s",
            method="GET",
            status_code=200,
            response_time=total_time,
            response_size=0,
            vulnerability_detected=vulnerability_detected,
            severity=severity,
            description=f"Sustained test: {requests_per_minute:.1f} req/min, {rate_limited_count} rate limited",
        )

    def _test_rate_limit_bypass(self) -> list[SecurityTestResult]:
        """Test rate limiting bypass techniques"""
        results = []

        # Test with different User-Agent headers
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "curl/7.68.0",
            "Python-requests/2.25.1",
            "",
        ]

        for ua in user_agents:
            headers = self.test_headers.copy()
            headers["User-Agent"] = ua

            # Make multiple requests
            success_count = 0
            for _ in range(20):
                try:
                    response = self.session.get(
                        f"{self.base_url}/health", headers=headers, timeout=5
                    )
                    if response.status_code == 200:
                        success_count += 1
                except Exception:
                    pass

            vulnerability_detected = success_count >= 18  # Most should succeed

            results.append(
                SecurityTestResult(
                    test_name="rate_limit_bypass_ua",
                    endpoint="/health",
                    payload=f"User-Agent: {ua[:30]}...",
                    method="GET",
                    status_code=200,
                    response_time=0,
                    response_size=0,
                    vulnerability_detected=vulnerability_detected,
                    severity="medium" if vulnerability_detected else "low",
                    description=f"UA bypass: {success_count}/20 requests succeeded",
                )
            )

        return results

    def _test_unauthorized_access(self, endpoint: str) -> SecurityTestResult:
        """Test access to protected endpoint without authentication"""
        start_time = time.time()

        try:
            response = self.session.get(
                f"{self.base_url}{endpoint}", headers=self.test_headers, timeout=10
            )

            response_time = time.time() - start_time

            # Should return 401 or 403 for protected endpoints
            vulnerability_detected = response.status_code == 200
            severity = "high" if vulnerability_detected else "low"

            return SecurityTestResult(
                test_name="unauthorized_access",
                endpoint=endpoint,
                payload="No authentication",
                method="GET",
                status_code=response.status_code,
                response_time=response_time,
                response_size=len(response.content),
                vulnerability_detected=vulnerability_detected,
                severity=severity,
                description=f"Accessed {endpoint} without authentication",
            )

        except Exception as e:
            return SecurityTestResult(
                test_name="unauthorized_access",
                endpoint=endpoint,
                payload="No authentication",
                method="GET",
                status_code=0,
                response_time=time.time() - start_time,
                response_size=0,
                vulnerability_detected=False,
                severity="low",
                description=f"Request failed: {str(e)}",
            )

    def _test_invalid_auth(self, endpoint: str, token: str) -> SecurityTestResult:
        """Test with invalid authentication token"""
        start_time = time.time()

        headers = self.test_headers.copy()
        headers["Authorization"] = token

        try:
            response = self.session.get(f"{self.base_url}{endpoint}", headers=headers, timeout=10)

            response_time = time.time() - start_time

            # Should reject invalid tokens
            vulnerability_detected = response.status_code == 200
            severity = "medium" if vulnerability_detected else "low"

            return SecurityTestResult(
                test_name="invalid_auth",
                endpoint=endpoint,
                payload=token[:50],
                method="GET",
                status_code=response.status_code,
                response_time=response_time,
                response_size=len(response.content),
                vulnerability_detected=vulnerability_detected,
                severity=severity,
                description=f"Invalid token accepted: {token[:30]}...",
            )

        except Exception as e:
            return SecurityTestResult(
                test_name="invalid_auth",
                endpoint=endpoint,
                payload=token[:50],
                method="GET",
                status_code=0,
                response_time=time.time() - start_time,
                response_size=0,
                vulnerability_detected=False,
                severity="low",
                description=f"Request failed: {str(e)}",
            )

    def _check_security_header(
        self, url: str, header: str, expected: Any, response_headers: dict
    ) -> SecurityTestResult:
        """Check for presence and correctness of security headers"""
        header_present = header in response_headers
        header_value = response_headers.get(header, "")

        if isinstance(expected, list):
            correct_value = any(exp in header_value for exp in expected)
        else:
            correct_value = expected in header_value if header_present else False

        vulnerability_detected = not header_present or not correct_value
        severity = "medium" if vulnerability_detected else "low"

        if not header_present:
            description = f"Missing security header: {header}"
        elif not correct_value:
            description = f"Incorrect {header} value: {header_value}"
        else:
            description = f"Correct {header} header present"

        return SecurityTestResult(
            test_name="security_header",
            endpoint=url,
            payload=header,
            method="GET",
            status_code=200,
            response_time=0,
            response_size=0,
            vulnerability_detected=vulnerability_detected,
            severity=severity,
            description=description,
        )

    def _test_information_disclosure(self, test: dict) -> SecurityTestResult:
        """Test for information disclosure"""
        start_time = time.time()

        try:
            response = self.session.get(
                f"{self.base_url}{test['url']}", headers=self.test_headers, timeout=10
            )

            response_time = time.time() - start_time
            response_text = response.text.lower()

            # Check for sensitive information
            found_info = []
            for check_item in test["check_for"]:
                if check_item.lower() in response_text:
                    found_info.append(check_item)

            vulnerability_detected = len(found_info) > 0

            return SecurityTestResult(
                test_name="information_disclosure",
                endpoint=test["url"],
                payload=", ".join(test["check_for"]),
                method="GET",
                status_code=response.status_code,
                response_time=response_time,
                response_size=len(response.content),
                vulnerability_detected=vulnerability_detected,
                severity=test["severity"] if vulnerability_detected else "low",
                description=f"Found sensitive info: {found_info}"
                if found_info
                else "No sensitive info found",
            )

        except Exception as e:
            return SecurityTestResult(
                test_name="information_disclosure",
                endpoint=test["url"],
                payload=", ".join(test["check_for"]),
                method="GET",
                status_code=0,
                response_time=time.time() - start_time,
                response_size=0,
                vulnerability_detected=False,
                severity="low",
                description=f"Request failed: {str(e)}",
            )

    def _test_directory_traversal(self, endpoint: str, payload: str) -> SecurityTestResult:
        """Test for directory traversal vulnerabilities"""
        start_time = time.time()

        try:
            if endpoint == "/upload":
                # Test file upload with traversal filename
                files = {"file": (payload, "test content")}
                response = self.session.post(f"{self.base_url}{endpoint}", files=files, timeout=10)
            else:
                # Test GET parameter with traversal
                response = self.session.get(
                    f"{self.base_url}{endpoint}", params={"query": payload}, timeout=10
                )

            response_time = time.time() - start_time

            # Check for successful traversal (200 with system file content)
            vulnerability_detected = response.status_code == 200 and (
                "root:" in response.text or "localhost" in response.text
            )

            return SecurityTestResult(
                test_name="directory_traversal",
                endpoint=endpoint,
                payload=payload,
                method="POST" if endpoint == "/upload" else "GET",
                status_code=response.status_code,
                response_time=response_time,
                response_size=len(response.content),
                vulnerability_detected=vulnerability_detected,
                severity="high" if vulnerability_detected else "low",
                description=f"Directory traversal test: {payload}",
            )

        except Exception as e:
            return SecurityTestResult(
                test_name="directory_traversal",
                endpoint=endpoint,
                payload=payload,
                method="GET",
                status_code=0,
                response_time=time.time() - start_time,
                response_size=0,
                vulnerability_detected=False,
                severity="low",
                description=f"Request failed: {str(e)}",
            )

    def _test_ssrf(self, endpoint: str, payload: str) -> SecurityTestResult:
        """Test for SSRF vulnerabilities"""
        start_time = time.time()

        try:
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                json={
                    "message": f"Please fetch data from {payload}",
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                },
                headers=self.test_headers,
                timeout=10,
            )

            response_time = time.time() - start_time

            # Check for signs of SSRF
            vulnerability_detected = (
                response.status_code == 200 and response_time > 5
            )  # Unusually long response time

            return SecurityTestResult(
                test_name="ssrf",
                endpoint=endpoint,
                payload=payload,
                method="POST",
                status_code=response.status_code,
                response_time=response_time,
                response_size=len(response.content),
                vulnerability_detected=vulnerability_detected,
                severity="high" if vulnerability_detected else "low",
                description=f"SSRF test: {payload}",
            )

        except Exception as e:
            return SecurityTestResult(
                test_name="ssrf",
                endpoint=endpoint,
                payload=payload,
                method="POST",
                status_code=0,
                response_time=time.time() - start_time,
                response_size=0,
                vulnerability_detected=False,
                severity="low",
                description=f"Request failed: {str(e)}",
            )

    def _analyze_response_for_vulnerabilities(
        self, response: requests.Response, payload: str, test_type: str
    ) -> bool:
        """Analyze response for vulnerability indicators"""
        # Check for error messages that might indicate vulnerabilities
        response_text = response.text.lower()

        if test_type == "injection":
            # SQL injection indicators
            sql_errors = [
                "sql syntax",
                "mysql_fetch",
                "ora-",
                "postgresql",
                "sqlite_",
                "error in your sql syntax",
            ]
            if any(error in response_text for error in sql_errors):
                return True

            # XSS reflection
            if payload.lower() in response_text:
                return True

        elif test_type == "buffer_overflow":
            # Server errors that might indicate buffer overflow
            if response.status_code == 500:
                return True

        # Generic error indicators
        error_indicators = [
            "stack trace",
            "exception",
            "error occurred",
            "internal server error",
            "debug mode",
        ]

        return any(indicator in response_text for indicator in error_indicators)

    def _compile_security_results(
        self,
        test_name: str,
        start_time: datetime,
        end_time: datetime,
        results: list[SecurityTestResult],
    ) -> SecurityTestSuite:
        """Compile security test results"""
        vulnerabilities = [r for r in results if r.vulnerability_detected]

        severity_counts = {
            "high": len([r for r in vulnerabilities if r.severity == "high"]),
            "medium": len([r for r in vulnerabilities if r.severity == "medium"]),
            "low": len([r for r in vulnerabilities if r.severity == "low"]),
        }

        return SecurityTestSuite(
            test_name=test_name,
            start_time=start_time,
            end_time=end_time,
            total_tests=len(results),
            vulnerabilities_found=len(vulnerabilities),
            high_severity=severity_counts["high"],
            medium_severity=severity_counts["medium"],
            low_severity=severity_counts["low"],
            results=results,
        )

    def run_security_test_suite(self) -> dict[str, SecurityTestSuite]:
        """Run complete security test suite"""
        self.logger.info("Starting comprehensive security test suite")

        results = {}

        try:
            # Input validation tests
            results["input_validation"] = self.test_input_validation()

            # Authentication/Authorization tests
            results["auth"] = self.test_authentication_authorization()

            # Rate limiting tests
            results["rate_limiting"] = self.test_rate_limiting()

            # Security headers tests
            results["security_headers"] = self.test_security_headers()

            # Information disclosure tests
            results["info_disclosure"] = self.test_information_disclosure()

            # Basic penetration tests
            results["penetration"] = self.run_penetration_tests()

        except Exception as e:
            self.logger.error(f"Security test suite error: {e}")

        return results

    def generate_security_report(self, results: dict[str, SecurityTestSuite]) -> str:
        """Generate comprehensive security report"""
        report = []
        report.append("# Security Test Results")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")

        total_vulnerabilities = 0
        total_high = 0
        total_medium = 0
        total_low = 0

        for test_name, result in results.items():
            report.append(f"## {test_name.replace('_', ' ').title()}")
            report.append(f"- **Total Tests:** {result.total_tests}")
            report.append(f"- **Vulnerabilities Found:** {result.vulnerabilities_found}")
            report.append(f"- **High Severity:** {result.high_severity}")
            report.append(f"- **Medium Severity:** {result.medium_severity}")
            report.append(f"- **Low Severity:** {result.low_severity}")

            total_vulnerabilities += result.vulnerabilities_found
            total_high += result.high_severity
            total_medium += result.medium_severity
            total_low += result.low_severity

            # List high severity vulnerabilities
            high_vulns = [
                r for r in result.results if r.severity == "high" and r.vulnerability_detected
            ]
            if high_vulns:
                report.append("### High Severity Issues:")
                for vuln in high_vulns:
                    report.append(f"- **{vuln.endpoint}**: {vuln.description}")

            report.append("")

        # Summary
        report.insert(2, "## Summary")
        report.insert(3, f"- **Total Vulnerabilities:** {total_vulnerabilities}")
        report.insert(4, f"- **Critical/High:** {total_high}")
        report.insert(5, f"- **Medium:** {total_medium}")
        report.insert(6, f"- **Low:** {total_low}")
        report.insert(7, "")

        return "\n".join(report)


# Flask integration
def init_security_testing(app: Flask):
    """Initialize security testing for Flask app"""
    security_suite = SecurityTestRunner()

    @app.route("/test/security/run")
    def run_security_tests():
        """Run security tests (async)"""
        return {"message": "Security tests started", "status": "running"}

    @app.route("/test/security/results")
    def get_security_results():
        """Get latest security test results"""
        return {"message": "Security results endpoint"}

    return security_suite


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TQ Chat Security Testing")
    parser.add_argument("--base-url", default="http://localhost:5000", help="Base URL for testing")
    parser.add_argument(
        "--test-type",
        choices=["input", "auth", "rate", "headers", "info", "pentest", "full"],
        default="full",
        help="Type of security test to run",
    )
    parser.add_argument("--output", help="Output file for results")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run tests
    runner = SecurityTestRunner(args.base_url)

    if args.test_type == "full":
        results = runner.run_security_test_suite()
    elif args.test_type == "input":
        results = {"input_validation": runner.test_input_validation()}
    elif args.test_type == "auth":
        results = {"auth": runner.test_authentication_authorization()}
    elif args.test_type == "rate":
        results = {"rate_limiting": runner.test_rate_limiting()}
    elif args.test_type == "headers":
        results = {"security_headers": runner.test_security_headers()}
    elif args.test_type == "info":
        results = {"info_disclosure": runner.test_information_disclosure()}
    elif args.test_type == "pentest":
        results = {"penetration": runner.run_penetration_tests()}

    # Generate report
    report = runner.generate_security_report(results)
    print(report)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Results saved to {args.output}")
