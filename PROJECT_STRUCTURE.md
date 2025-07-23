# TQ GenAI Chat - Clean Project Structure

## 📁 Project Organization

After streamlining and reorganization, the project now has a clean, focused structure:

```
TQ_GenAI_Chat/
├── .env                     # Environment variables (local)
├── .env.example            # Environment template
├── .gitignore              # Git ignore rules
├── README.md               # Project documentation
├── ai_models.py            # AI model definitions
├── app.py                  # Main Flask application (1,182 lines)
├── deploy.py               # Deployment & setup script
├── persona.py              # AI assistant personalities
├── pyproject.toml          # Python project configuration
├── requirements.txt        # Full production dependencies
├── requirements-lite.txt   # Lightweight dependencies
├── uv.lock                 # Dependency lock file
├── config/
│   └── settings.py         # Centralized configuration
├── core/
│   ├── __init__.py
│   ├── api_services.py     # Multi-provider API abstraction
│   ├── document_store.py   # Document storage & retrieval
│   ├── file_processor.py   # File processing utilities
│   ├── model_utils.py      # Model management utilities
│   └── utilities.py        # General utilities
├── services/
│   ├── __init__.py
│   ├── file_manager.py     # File management with vector search
│   └── xai_service.py      # XAI/Grok API integration
├── static/
│   ├── favicon.ico         # Site icon
│   ├── portrait-sketch-simple.svg  # Sidebar logo
│   ├── portrait-sketch.svg # Alternative logo
│   ├── script.js           # Main JavaScript application
│   └── styles.css          # CSS framework
├── templates/
│   └── index.html          # Main HTML template
├── exports/                # Chat export files
├── saved_chats/            # Saved conversations
├── uploads/                # File upload storage
├── flask_session/          # Session storage (cleaned)
├── scripts/                # Utility scripts
└── trash2review/           # Archived/redundant files
    ├── app_original.py
    ├── script_original.js
    ├── styles_original.css
    ├── REBASE_SUMMARY.md
    ├── defaults_cache.json
    ├── models_cache.json
    └── [other archived files...]
```

## 🧹 Files Moved to trash2review

### Cache & Temporary Files
- `defaults_cache.json` - Model defaults cache
- `models_cache.json` - API models cache
- `deployment.log` - Deployment log file
- `documents.db` - SQLite database (regeneratable)
- `.ruff_cache/` - Linter cache directory

### Project History Files
- `REBASE_COMPLETE.md` - Rebase completion log
- `REBASE_SUMMARY.md` - Rebase summary report
- `refactoring_plan.md` - Old refactoring notes

### Redundant Static Assets
- `Untitled.svg` - Unused SVG file
- `bootstrap.min.css` - Unused Bootstrap CSS

### Session Files
- Cleaned `flask_session/` directory
- Removed `__pycache__/` directories

## ✅ Current Active Structure

### Core Application Files
- **`app.py`** - Main Flask application (1,182 lines)
- **`ai_models.py`** - AI model configurations
- **`persona.py`** - Assistant personality definitions
- **`deploy.py`** - Setup and deployment automation

### Frontend Assets
- **`templates/index.html`** - Single HTML template
- **`static/script.js`** - Unified JavaScript application
- **`static/styles.css`** - Complete CSS framework

### Backend Modules
- **`core/`** - Business logic (API services, file processing, utilities)
- **`services/`** - Specialized services (file manager, XAI integration)
- **`config/`** - Configuration management

### Dependencies
- **`requirements.txt`** - Full production dependencies (201 packages)
- **`requirements-lite.txt`** - Minimal dependencies (40 packages)

## 🎯 Benefits of This Structure

1. **Simplified Navigation** - Clean, logical file organization
2. **No Redundancy** - Eliminated duplicate and obsolete files
3. **Clear Separation** - Business logic separated from presentation
4. **Maintainable** - Single source of truth for each component
5. **Archived History** - Old versions preserved in `trash2review/`

## 📋 Next Steps

1. The project is now streamlined and ready for development
2. All redundant files are safely archived in `trash2review/`
3. Cache files and temporary data have been cleaned
4. The structure follows best practices for Flask applications

## 🔧 Known Issues & Fixes

### pydub Regex Warnings (FIXED)
- **Issue**: Python 3.12+ shows SyntaxWarnings from pydub's regex patterns
- **Solution**: Added `warnings.filterwarnings("ignore", category=SyntaxWarning, module="pydub")` in `app.py`
- **Status**: ✅ **RESOLVED** - Application now starts without warnings

The project now has a clean, professional structure that's easy to navigate and maintain.
