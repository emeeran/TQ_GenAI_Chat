"""
Comprehensive Test Suite Runner - Testing & Validation
Coordinates and executes Performance, Security, and Integration testing
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from integration_testing import IntegrationTestRunner

# Local test suite imports
from performance_testing import PerformanceTestSuite
from security_testing import SecurityTestRunner


class ComprehensiveTestRunner:
    """Coordinates all testing suites for TQ Chat application"""

    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)

        # Initialize test suites
        self.performance_suite = PerformanceTestSuite(base_url)
        self.security_suite = SecurityTestRunner(base_url)
        self.integration_suite = IntegrationTestRunner(base_url)

        # Test configuration
        self.config = {
            "performance": {
                "enabled": True,
                "concurrent_users": 100,
                "duration": 300,
                "stress_multiplier": 2.0,
            },
            "security": {
                "enabled": True,
                "include_penetration": True,
                "include_rate_limiting": True,
            },
            "integration": {
                "enabled": True,
                "test_all_providers": True,
                "test_file_processing": True,
            },
        }

    def run_all_tests(self, output_dir: str = "test_reports") -> dict[str, Any]:
        """Run all testing suites and generate comprehensive report"""
        self.logger.info("Starting comprehensive test suite execution")

        # Ensure output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        start_time = datetime.now()
        results = {"execution_start": start_time.isoformat(), "test_suites": {}, "summary": {}}

        # Run Performance Tests
        if self.config["performance"]["enabled"]:
            try:
                self.logger.info("Executing Performance Tests...")
                perf_results = self._run_performance_tests()
                results["test_suites"]["performance"] = perf_results

                # Save performance report
                perf_report = self.performance_suite.generate_report(perf_results)
                self._save_report(output_path / "performance_report.md", perf_report)

            except Exception as e:
                self.logger.error(f"Performance tests failed: {e}")
                results["test_suites"]["performance"] = {"error": str(e)}

        # Run Security Tests
        if self.config["security"]["enabled"]:
            try:
                self.logger.info("Executing Security Tests...")
                security_results = self.security_suite.run_security_test_suite()
                results["test_suites"]["security"] = security_results

                # Save security report
                security_report = self.security_suite.generate_security_report(security_results)
                self._save_report(output_path / "security_report.md", security_report)

            except Exception as e:
                self.logger.error(f"Security tests failed: {e}")
                results["test_suites"]["security"] = {"error": str(e)}

        # Run Integration Tests
        if self.config["integration"]["enabled"]:
            try:
                self.logger.info("Executing Integration Tests...")
                integration_results = self.integration_suite.run_integration_test_suite()
                results["test_suites"]["integration"] = integration_results

                # Save integration report
                integration_report = self.integration_suite.generate_integration_report(
                    integration_results
                )
                self._save_report(output_path / "integration_report.md", integration_report)

            except Exception as e:
                self.logger.error(f"Integration tests failed: {e}")
                results["test_suites"]["integration"] = {"error": str(e)}

        # Generate comprehensive summary
        end_time = datetime.now()
        results["execution_end"] = end_time.isoformat()
        results["total_duration"] = (end_time - start_time).total_seconds()
        results["summary"] = self._generate_summary(results["test_suites"])

        # Save comprehensive report
        comprehensive_report = self._generate_comprehensive_report(results)
        self._save_report(output_path / "comprehensive_test_report.md", comprehensive_report)

        self.logger.info("Comprehensive test suite execution completed")
        return results

    def _run_performance_tests(self) -> dict[str, Any]:
        """Execute performance testing suite"""
        results = {}

        # Load Testing
        load_config = {
            "concurrent_users": self.config["performance"]["concurrent_users"],
            "duration_seconds": self.config["performance"]["duration"],
            "ramp_up_time": 30,
        }

        load_result = asyncio.run(self.performance_suite.load_test(**load_config))
        results["load_test"] = load_result

        # Stress Testing
        stress_config = {
            "max_users": self.config["performance"]["concurrent_users"]
            * self.config["performance"]["stress_multiplier"],
            "step_duration": 60,
            "user_increment": 10,
        }

        stress_result = asyncio.run(self.performance_suite.stress_test(**stress_config))
        results["stress_test"] = stress_result

        # Endurance Testing
        endurance_config = {
            "concurrent_users": 50,
            "duration_hours": 1,  # Reduced for testing
            "check_interval": 300,
        }

        endurance_result = asyncio.run(self.performance_suite.endurance_test(**endurance_config))
        results["endurance_test"] = endurance_result

        return results

    def _generate_summary(self, test_suites: dict[str, Any]) -> dict[str, Any]:
        """Generate test execution summary"""
        summary = {
            "total_suites": len(test_suites),
            "successful_suites": 0,
            "failed_suites": 0,
            "performance_summary": {},
            "security_summary": {},
            "integration_summary": {},
            "critical_issues": [],
            "recommendations": [],
        }

        # Performance Summary
        if "performance" in test_suites and "error" not in test_suites["performance"]:
            summary["successful_suites"] += 1
            perf_data = test_suites["performance"]

            # Extract key performance metrics
            if "load_test" in perf_data:
                load_test = perf_data["load_test"]
                summary["performance_summary"] = {
                    "max_concurrent_users": load_test.concurrent_users,
                    "avg_response_time": load_test.avg_response_time,
                    "error_rate": load_test.error_rate,
                    "requests_per_second": load_test.requests_per_second,
                }

                # Check for performance issues
                if load_test.avg_response_time > 2.0:
                    summary["critical_issues"].append(
                        f"High average response time: {load_test.avg_response_time:.2f}s"
                    )

                if load_test.error_rate > 0.05:
                    summary["critical_issues"].append(
                        f"High error rate: {load_test.error_rate:.2%}"
                    )
        else:
            summary["failed_suites"] += 1
            if "performance" in test_suites:
                summary["critical_issues"].append(
                    f"Performance testing failed: {test_suites['performance'].get('error', 'Unknown error')}"
                )

        # Security Summary
        if "security" in test_suites and "error" not in test_suites["security"]:
            summary["successful_suites"] += 1
            security_data = test_suites["security"]

            total_vulnerabilities = 0
            high_severity = 0

            for test_name, test_result in security_data.items():
                if hasattr(test_result, "vulnerabilities_found"):
                    total_vulnerabilities += test_result.vulnerabilities_found
                    high_severity += test_result.high_severity

            summary["security_summary"] = {
                "total_vulnerabilities": total_vulnerabilities,
                "high_severity_issues": high_severity,
                "tests_completed": len(security_data),
            }

            # Check for security issues
            if high_severity > 0:
                summary["critical_issues"].append(
                    f"High severity security vulnerabilities found: {high_severity}"
                )

        else:
            summary["failed_suites"] += 1
            if "security" in test_suites:
                summary["critical_issues"].append(
                    f"Security testing failed: {test_suites['security'].get('error', 'Unknown error')}"
                )

        # Integration Summary
        if "integration" in test_suites and "error" not in test_suites["integration"]:
            summary["successful_suites"] += 1
            integration_data = test_suites["integration"]

            total_tests = 0
            total_passed = 0
            total_failed = 0

            for suite_name, suite_result in integration_data.items():
                if hasattr(suite_result, "total_tests"):
                    total_tests += suite_result.total_tests
                    total_passed += suite_result.passed_tests
                    total_failed += suite_result.failed_tests

            success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

            summary["integration_summary"] = {
                "total_tests": total_tests,
                "passed_tests": total_passed,
                "failed_tests": total_failed,
                "success_rate": success_rate,
            }

            # Check for integration issues
            if success_rate < 90:
                summary["critical_issues"].append(
                    f"Low integration test success rate: {success_rate:.1f}%"
                )

        else:
            summary["failed_suites"] += 1
            if "integration" in test_suites:
                summary["critical_issues"].append(
                    f"Integration testing failed: {test_suites['integration'].get('error', 'Unknown error')}"
                )

        # Generate recommendations
        summary["recommendations"] = self._generate_recommendations(summary)

        return summary

    def _generate_recommendations(self, summary: dict[str, Any]) -> list[str]:
        """Generate recommendations based on test results"""
        recommendations = []

        # Performance recommendations
        perf_summary = summary.get("performance_summary", {})
        if perf_summary.get("avg_response_time", 0) > 1.0:
            recommendations.append(
                "Consider optimizing response times through caching, database optimization, or CDN implementation"
            )

        if perf_summary.get("error_rate", 0) > 0.01:
            recommendations.append(
                "Investigate and resolve sources of errors to improve system reliability"
            )

        # Security recommendations
        security_summary = summary.get("security_summary", {})
        if security_summary.get("total_vulnerabilities", 0) > 0:
            recommendations.append(
                "Address identified security vulnerabilities immediately, prioritizing high-severity issues"
            )

        # Integration recommendations
        integration_summary = summary.get("integration_summary", {})
        if integration_summary.get("success_rate", 100) < 95:
            recommendations.append(
                "Investigate integration test failures to ensure system reliability"
            )

        # General recommendations
        if summary["failed_suites"] > 0:
            recommendations.append(
                "Resolve test suite execution failures to ensure comprehensive testing coverage"
            )

        if not recommendations:
            recommendations.append(
                "All tests completed successfully! Continue monitoring and maintain regular testing schedule."
            )

        return recommendations

    def _generate_comprehensive_report(self, results: dict[str, Any]) -> str:
        """Generate comprehensive test report"""
        report = []
        report.append("# Comprehensive Test Suite Report")
        report.append(f"**Generated:** {datetime.now().isoformat()}")
        report.append(f"**Execution Duration:** {results['total_duration']:.2f} seconds")
        report.append("")

        # Executive Summary
        summary = results["summary"]
        report.append("## Executive Summary")
        report.append(f"- **Test Suites Executed:** {summary['total_suites']}")
        report.append(f"- **Successful Suites:** {summary['successful_suites']}")
        report.append(f"- **Failed Suites:** {summary['failed_suites']}")
        report.append("")

        # Critical Issues
        if summary["critical_issues"]:
            report.append("## Critical Issues")
            for issue in summary["critical_issues"]:
                report.append(f"- 🚨 {issue}")
            report.append("")

        # Performance Summary
        if summary["performance_summary"]:
            perf = summary["performance_summary"]
            report.append("## Performance Summary")
            report.append(f"- **Max Concurrent Users:** {perf.get('max_concurrent_users', 'N/A')}")
            report.append(f"- **Average Response Time:** {perf.get('avg_response_time', 0):.3f}s")
            report.append(f"- **Error Rate:** {perf.get('error_rate', 0):.2%}")
            report.append(f"- **Requests per Second:** {perf.get('requests_per_second', 0):.2f}")
            report.append("")

        # Security Summary
        if summary["security_summary"]:
            sec = summary["security_summary"]
            report.append("## Security Summary")
            report.append(f"- **Total Vulnerabilities:** {sec.get('total_vulnerabilities', 0)}")
            report.append(f"- **High Severity Issues:** {sec.get('high_severity_issues', 0)}")
            report.append(f"- **Tests Completed:** {sec.get('tests_completed', 0)}")
            report.append("")

        # Integration Summary
        if summary["integration_summary"]:
            integ = summary["integration_summary"]
            report.append("## Integration Summary")
            report.append(f"- **Total Tests:** {integ.get('total_tests', 0)}")
            report.append(f"- **Passed Tests:** {integ.get('passed_tests', 0)}")
            report.append(f"- **Failed Tests:** {integ.get('failed_tests', 0)}")
            report.append(f"- **Success Rate:** {integ.get('success_rate', 0):.1f}%")
            report.append("")

        # Recommendations
        report.append("## Recommendations")
        for recommendation in summary["recommendations"]:
            report.append(f"- {recommendation}")
        report.append("")

        # Detailed Results
        report.append("## Detailed Results")
        report.append("See individual test suite reports for detailed findings:")
        report.append("- `performance_report.md` - Performance testing details")
        report.append("- `security_report.md` - Security testing details")
        report.append("- `integration_report.md` - Integration testing details")
        report.append("")

        return "\n".join(report)

    def _save_report(self, file_path: Path, content: str) -> None:
        """Save report to file"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.logger.info(f"Report saved to {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save report to {file_path}: {e}")

    def run_specific_suite(self, suite_name: str, **kwargs) -> dict[str, Any]:
        """Run a specific test suite"""
        self.logger.info(f"Running {suite_name} test suite")

        if suite_name == "performance":
            return self._run_performance_tests()
        elif suite_name == "security":
            return self.security_suite.run_security_test_suite()
        elif suite_name == "integration":
            return self.integration_suite.run_integration_test_suite()
        else:
            raise ValueError(f"Unknown test suite: {suite_name}")

    def configure_suite(self, suite_name: str, **config) -> None:
        """Configure specific test suite parameters"""
        if suite_name in self.config:
            self.config[suite_name].update(config)
            self.logger.info(f"Updated {suite_name} configuration: {config}")
        else:
            raise ValueError(f"Unknown test suite: {suite_name}")


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TQ Chat Comprehensive Testing Suite")
    parser.add_argument("--base-url", default="http://localhost:5000", help="Base URL for testing")
    parser.add_argument(
        "--suite",
        choices=["all", "performance", "security", "integration"],
        default="all",
        help="Test suite to run",
    )
    parser.add_argument("--output-dir", default="test_reports", help="Output directory for reports")
    parser.add_argument(
        "--concurrent-users",
        type=int,
        default=100,
        help="Number of concurrent users for performance testing",
    )
    parser.add_argument(
        "--test-duration", type=int, default=300, help="Duration in seconds for performance testing"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("test_execution.log")],
    )

    # Initialize test runner
    runner = ComprehensiveTestRunner(args.base_url)

    # Configure performance settings from CLI args
    runner.configure_suite(
        "performance", concurrent_users=args.concurrent_users, duration=args.test_duration
    )

    try:
        if args.suite == "all":
            results = runner.run_all_tests(args.output_dir)
            logging.info(f"Comprehensive testing completed. Reports saved to {args.output_dir}")
        else:
            results = runner.run_specific_suite(args.suite)
            logging.info(f"{args.suite.title()} testing completed")

        # Print summary
        if "summary" in results:
            summary = results["summary"]
            logging.info("=== TEST EXECUTION SUMMARY ===")
            logging.info(f"Successful Suites: {summary['successful_suites']}")
            logging.info(f"Failed Suites: {summary['failed_suites']}")

            if summary["critical_issues"]:
                logging.warning("Critical Issues Found:")
                for issue in summary["critical_issues"]:
                    logging.warning(f"  - {issue}")

    except Exception as e:
        logging.error(f"Test execution failed: {e}")
        sys.exit(1)
