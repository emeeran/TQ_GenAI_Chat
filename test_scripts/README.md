# Test Scripts and Validation Tools

This directory contains all test scripts, validation tools, and demo applications used for testing and validating the TQ GenAI Chat application.

## File Organization

### Core System Tests

- `test_async_handler.py` - Async processing system validation
- `test_async_post_endpoints.py` - POST endpoint async wrapper testing
- `test_database_maintenance.py` - Database maintenance automation tests
- `test_enhanced_file_manager.py` - Enhanced file management system tests
- `test_circuit_breaker.py` - Circuit breaker pattern implementation tests
- `test_timeout_system.py` - Timeout and cancellation system tests

### Cache System Tests

- `test_cache_warmer.py` - Cache warming strategies validation
- `test_query_cache_fixed.py` - Query result caching tests
- `test_query_cache_integration.py` - Cache integration tests
- `test_query_cache_simple.py` - Basic cache functionality tests

### File Processing Tests

- `test_streaming_processor.py` - Streaming file processing validation
- `test_document_chunker.py` - Document chunking strategy tests

### Asset and Frontend Tests

- `test_asset_optimization.py` - Asset optimization pipeline tests
- `test_asset_integration.py` - Asset integration validation
- `simple_asset_test.py` - Simple asset optimization verification

### API and Provider Tests

- `test_all_providers_fallback.py` - Multi-provider fallback testing
- `test_dynamic_fetcher.py` - Dynamic model fetching tests
- `test_model_integration.py` - Model integration validation
- `test_model_update_debug.py` - Model update debugging
- `test_openrouter_fix.py` - OpenRouter provider fixes

### Request Processing Tests

- `test_request_queue.py` - Request queuing system tests
- `test_simple_queue.py` - Basic queue functionality tests
- `demo_request_queue.py` - Request queue demonstration

### Architecture Tests

- `test_modular_architecture.py` - Modular architecture validation
- `test_production_integration.py` - Production integration tests

### Direct Testing Tools

- `test_endpoint_direct.py` - Direct endpoint testing
- `test_minimal_app.py` - Minimal application testing
- `validate_async_endpoints.py` - Async endpoint validation

## Running Tests

### Individual Test Files

```bash
# Run specific test
cd test_scripts
python test_async_handler.py

# Run with pytest (if available)
pytest test_async_handler.py -v
```

### Test Categories

```bash
# Database tests
python test_database_maintenance.py
python test_query_cache_fixed.py

# Performance tests
python test_async_post_endpoints.py
python test_streaming_processor.py

# Integration tests
python test_production_integration.py
python test_asset_integration.py
```

### Demo Applications

```bash
# Request queue demonstration
python demo_request_queue.py

# Asset optimization validation
python simple_asset_test.py
```

## Test Guidelines

1. **Environment Setup**: Ensure test environment variables are configured
2. **Dependencies**: Install required test dependencies (`pytest`, mock libraries)
3. **Test Data**: Some tests may require sample files or database setup
4. **Isolation**: Tests should be independent and not affect production data
5. **Cleanup**: Tests should clean up resources after execution

## Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: Multi-component interaction testing
- **Performance Tests**: Load and performance validation
- **End-to-End Tests**: Complete workflow testing
- **Demo Scripts**: Feature demonstration and validation

---
*Organized from project root for better repository structure and testing workflow*
