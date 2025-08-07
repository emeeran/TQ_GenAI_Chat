"""
Test Configuration for TQ Chat Testing & Validation Suite
"""

# Test Environment Configuration
TEST_CONFIG = {
    # Base application URL for testing
    "base_url": "http://localhost:5000",
    # Performance Testing Configuration
    "performance": {
        "load_testing": {"concurrent_users": 100, "duration_seconds": 300, "ramp_up_time": 30},
        "stress_testing": {"max_users": 500, "step_duration": 60, "user_increment": 10},
        "endurance_testing": {"concurrent_users": 50, "duration_hours": 2, "check_interval": 300},
    },
    # Security Testing Configuration
    "security": {
        "enabled_tests": [
            "input_validation",
            "authentication",
            "rate_limiting",
            "security_headers",
            "information_disclosure",
            "penetration",
        ],
        "rate_limiting": {"requests_per_minute": 60, "burst_requests": 100, "test_duration": 60},
    },
    # Integration Testing Configuration
    "integration": {
        "providers_to_test": ["openai", "anthropic", "groq", "xai"],
        "file_types_to_test": ["txt", "json", "csv", "md"],
        "test_suites": [
            "multi_provider",
            "file_processing",
            "cache_system",
            "error_handling",
            "performance_load",
            "data_persistence",
        ],
    },
    # Test Output Configuration
    "output": {
        "reports_directory": "test_reports",
        "log_level": "INFO",
        "save_detailed_logs": True,
        "generate_html_reports": False,
    },
    # Test Data Configuration
    "test_data": {
        "sample_messages": [
            "Hello, how are you?",
            "What is the capital of France?",
            "Write a simple Python function to add two numbers.",
            "Explain quantum computing in simple terms.",
            "What are the benefits of renewable energy?",
        ],
        "sample_files": {
            "test.txt": "This is a test document for file processing.",
            "test.json": '{"key": "value", "test": true}',
            "test.csv": "name,age,city\nJohn,30,New York\nJane,25,London",
            "test.md": "# Test Document\n\nThis is a **markdown** test file.",
        },
    },
}

# Test Environment Validation
REQUIRED_ENDPOINTS = ["/health", "/chat", "/upload", "/search_context", "/files"]

REQUIRED_PROVIDERS = ["openai", "anthropic", "groq", "xai"]

REQUIRED_MODELS = {
    "openai": ["gpt-4o-mini", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-haiku-20240307"],
    "groq": ["llama-3.1-8b-instant"],
    "xai": ["grok-beta"],
}

# Test Thresholds and Acceptance Criteria
PERFORMANCE_THRESHOLDS = {
    "max_response_time": 2.0,  # seconds
    "max_error_rate": 0.05,  # 5%
    "min_throughput": 10,  # requests per second
    "max_memory_increase": 100,  # MB during testing
}

SECURITY_THRESHOLDS = {
    "max_high_severity_vulns": 0,
    "max_medium_severity_vulns": 5,
    "required_security_headers": ["X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection"],
}

INTEGRATION_THRESHOLDS = {
    "min_success_rate": 0.95,  # 95%
    "max_failed_providers": 1,
    "max_file_processing_errors": 2,
}
