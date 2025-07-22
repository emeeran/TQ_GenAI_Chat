# TQ GenAI Chat - Refactoring Plan

## Current Architecture Assessment

### Working Components:
1. **Flask Application** (`app.py`): Main entry point with routing and API endpoints
2. **AI Model Definitions** (`ai_models.py`): Comprehensive model configurations
3. **Persona Definitions** (`persona.py`): Well-structured persona templates
4. **Core File Processing** (`core/file_processor.py`): Efficient file processing system

### Components Needing Refactoring:
1. **Missing Service Files**: The `services` directory contains only compiled Python files
2. **Empty Core Modules**: `api_services.py` and `document_store.py` are empty
3. **Util vs Core Confusion**: Functionality is split between `utils` and `core` directories
4. **Redundant Code**: Functionality in trash2review needs proper integration
5. **Missing README**: Documentation is essential for maintainability

## Refactoring Strategy

### 1. Service Layer Reconstruction
- Restore `file_manager.py` and `xai_service.py` from trash2review to services directory
- Ensure proper imports and module references

### 2. Core Module Implementation
- Implement `api_services.py` as a centralized API client handler
- Develop `document_store.py` for document processing and storage
- Move utilities from utils folder to core as needed

### 3. Configuration Management
- Move API configuration settings to config/settings.py
- Standardize configuration access across modules

### 4. Code De-duplication
- Remove duplicate code between utils and core directories
- Establish clear responsibility boundaries

### 5. Documentation
- Create comprehensive README.md
- Add docstrings to all modules and classes

## Implementation Priority
1. Service layer reconstruction
2. Core module implementation
3. Configuration standardization
4. Code cleanup and de-duplication
5. Documentation
