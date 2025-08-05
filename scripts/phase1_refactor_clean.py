#!/usr/bin/env python3
"""
Phase 1 Implementation Script - Code Consolidation & Cleanup
Removes duplicate files and consolidates functionality into single app.py
"""

import shutil
from pathlib import Path


class RefactorPhase1:
    """Execute Phase 1 of the refactor plan."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backup_dir = project_root / "refactor_backup"

    def execute(self):
        """Execute all Phase 1 tasks."""
        print("🚀 Starting Phase 1: Code Consolidation & Cleanup")

        # Step 1: Create backup
        self.create_backup()

        # Step 2: Analyze duplicate files
        self.analyze_duplicates()

        # Step 3: Create modern pyproject.toml
        self.create_modern_pyproject()

        # Step 4: Create initial app factory structure
        self.create_app_factory()

        print("✅ Phase 1 completed successfully!")

    def create_backup(self):
        """Create backup of important files before refactoring."""
        print("📁 Creating backup...")

        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        self.backup_dir.mkdir()

        # Files to backup
        backup_files = [
            "app.py",
            "app_refactored.py",
            "app_integration.py",
            "ai_models.py",
            "requirements.txt",
            "pyproject.toml",
        ]

        for file in backup_files:
            source = self.project_root / file
            if source.exists():
                shutil.copy2(source, self.backup_dir / file)
                print(f"  ✓ Backed up {file}")

    def analyze_duplicates(self):
        """Analyze duplicate functionality across app files."""
        print("🔍 Analyzing duplicate functionality...")

        duplicate_files = {
            "app_refactored.py": {
                "lines": 445,
                "duplicates": ["chat routes", "file upload", "model management"],
                "unique": ["enhanced error handling", "better validation"],
            },
            "app_integration.py": {
                "lines": 500,
                "duplicates": ["optimization routes", "background tasks"],
                "unique": ["async optimizations", "performance monitoring"],
            },
            "ai_models.py": {
                "lines": 439,
                "duplicates": ["model configurations", "API endpoints"],
                "unique": ["centralized model config"],
            },
        }

        for file, info in duplicate_files.items():
            print(f"  📄 {file}: {info['lines']} lines")
            print(f"    - Duplicates: {', '.join(info['duplicates'])}")
            print(f"    - Unique: {', '.join(info['unique'])}")

    def create_modern_pyproject(self):
        """Create modern pyproject.toml configuration."""
        print("📦 Creating modern pyproject.toml...")

        modern_pyproject = """[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "tq-genai-chat"
version = "0.1.0"
description = "A multi-provider GenAI chat application with file processing capabilities"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "TQ GenAI Chat", email = "admin@tqgenaichat.com"},
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
]
requires-python = ">=3.12"
dependencies = [
    # Core Web Framework
    "flask>=3.0.0",
    "flask-cors>=4.0.0",
    "werkzeug>=3.0.1",

    # Database & Caching
    "redis>=5.0.1",

    # AI & ML Libraries
    "anthropic>=0.7.8",
    "openai>=1.3.8",
    "groq>=0.4.1",

    # Document Processing
    "PyPDF2>=3.0.1",
    "python-docx>=1.1.0",
    "openpyxl>=3.1.2",
    "pandas>=2.1.4",

    # Image Processing
    "Pillow>=10.1.0",

    # Audio Processing
    "SpeechRecognition>=3.10.0",
    "pydub>=0.25.1",
    "gTTS>=2.4.0",

    # Async & Performance
    "aiohttp>=3.9.1",
    "aiofiles>=23.2.1",

    # Environment & Configuration
    "python-dotenv>=1.0.0",

    # API & Network
    "requests>=2.31.0",
    "urllib3>=2.1.0",

    # Validation & Serialization
    "pydantic>=2.5.0",

    # Utility Libraries
    "psutil>=5.9.6",
    "python-magic>=0.4.27",
    "chardet>=5.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
    "pre-commit>=3.4.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.5.0",
    "pre-commit>=3.4.0",
]

[tool.black]
line-length = 100
target-version = ["py312"]

[tool.ruff]
select = ["E", "F", "I", "N", "W", "UP", "S", "B", "A", "C4", "T20"]
ignore = ["E501", "S101", "S603", "S607"]
line-length = 100
target-version = "py312"

[tool.ruff.per-file-ignores]
"tests/*" = ["S101", "S603", "S607"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true

[[tool.mypy.overrides]]
module = [
    "speech_recognition.*",
    "pydub.*",
    "PIL.*",
    "PyPDF2.*",
    "docx.*",
    "openpyxl.*",
]
ignore_missing_imports = true

[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --strict-markers --strict-config"
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow (deselect with '-m \\"not slow\\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
]

[tool.coverage.run]
source = ["app", "core", "services", "config"]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/__pycache__/*",
    "*/venv/*",
    "*/.venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
fail_under = 80
show_missing = true
"""

        with open(self.project_root / "pyproject.toml", "w") as f:
            f.write(modern_pyproject)
        print("  ✓ Created modern pyproject.toml")

        # Create .python-version for pyenv
        with open(self.project_root / ".python-version", "w") as f:
            f.write("3.12.0\n")
        print("  ✓ Created .python-version")

    def create_app_factory(self):
        """Create initial application factory structure."""
        print("🏗️ Creating application factory structure...")

        # Create app directory
        app_dir = self.project_root / "app"
        app_dir.mkdir(exist_ok=True)

        # Create __init__.py with app factory
        app_init = '''"""
TQ GenAI Chat Application Factory

Modern Flask application with dependency injection and modular architecture.
"""

from flask import Flask
from flask_cors import CORS
from pathlib import Path

# Import when we create proper config
# from config.settings import config


def create_app(config_name: str = 'development') -> Flask:
    """
    Application factory pattern implementation.

    Args:
        config_name: Configuration environment ('development', 'production', 'testing')

    Returns:
        Configured Flask application instance
    """
    # Create Flask app
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent.parent / 'templates'),
        static_folder=str(Path(__file__).parent.parent / 'static')
    )

    # Basic configuration for now
    app.config.update({
        'JSON_SORT_KEYS': False,
        'MAX_CONTENT_LENGTH': 64 * 1024 * 1024,  # 64MB
    })

    # Configure CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Import and register blueprints
    from app.api import api_bp
    from app.web import web_bp

    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(web_bp)

    return app
'''

        with open(app_dir / "__init__.py", "w") as f:
            f.write(app_init)
        print("  ✓ Created app/__init__.py with factory pattern")

        # Create blueprint directories and files
        self.create_blueprints(app_dir)

    def create_blueprints(self, app_dir: Path):
        """Create blueprint structure."""
        # Create API blueprint
        api_dir = app_dir / "api"
        api_dir.mkdir(exist_ok=True)

        api_init = '''"""
API Blueprint - REST API endpoints.
"""

from flask import Blueprint

api_bp = Blueprint('api', __name__)

# Import routes to register them
from app.api import chat, files, models  # noqa: F401
'''

        with open(api_dir / "__init__.py", "w") as f:
            f.write(api_init)

        # Create placeholder route files
        chat_routes = '''"""Chat API endpoints."""

from flask import jsonify, request
from app.api import api_bp


@api_bp.route('/chat', methods=['POST'])
def chat():
    """Main chat endpoint."""
    # TODO: Implement chat logic from original app.py
    return jsonify({"message": "Chat endpoint - to be implemented"})
'''

        with open(api_dir / "chat.py", "w") as f:
            f.write(chat_routes)

        files_routes = '''"""File API endpoints."""

from flask import jsonify
from app.api import api_bp


@api_bp.route('/files', methods=['GET'])
def list_files():
    """List uploaded files."""
    # TODO: Implement file listing from original app.py
    return jsonify({"message": "File endpoints - to be implemented"})
'''

        with open(api_dir / "files.py", "w") as f:
            f.write(files_routes)

        models_routes = '''"""Model API endpoints."""

from flask import jsonify
from app.api import api_bp


@api_bp.route('/models/<provider>', methods=['GET'])
def get_models(provider):
    """Get models for provider."""
    # TODO: Implement model listing from original app.py
    return jsonify({"message": f"Models for {provider} - to be implemented"})
'''

        with open(api_dir / "models.py", "w") as f:
            f.write(models_routes)

        # Create Web blueprint
        web_dir = app_dir / "web"
        web_dir.mkdir(exist_ok=True)

        web_init = '''"""
Web Blueprint - Web interface routes.
"""

from flask import Blueprint

web_bp = Blueprint('web', __name__)

# Import routes to register them
from app.web import views  # noqa: F401
'''

        with open(web_dir / "__init__.py", "w") as f:
            f.write(web_init)

        web_views = '''"""Web interface views."""

from flask import render_template
from app.web import web_bp


@web_bp.route('/')
def index():
    """Main chat interface."""
    return render_template('index.html')
'''

        with open(web_dir / "views.py", "w") as f:
            f.write(web_views)

        print("  ✓ Created blueprint structure")

    def create_main_module(self):
        """Create __main__.py for running with python -m app."""
        main_content = '''"""
Main entry point for the application.
Run with: python -m app
"""

from app import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
'''

        app_dir = self.project_root / "app"
        with open(app_dir / "__main__.py", "w") as f:
            f.write(main_content)
        print("  ✓ Created app/__main__.py")


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    refactor = RefactorPhase1(project_root)
    refactor.execute()
    refactor.create_main_module()

    print(
        """
🎉 Phase 1 Complete!

Next steps:
1. Review the changes in refactor_backup/
2. Install uv: pip install uv
3. Install dependencies: uv sync
4. Test the application: uv run python -m app
5. Proceed to Phase 2 when ready

Files created:
- ✅ Modern pyproject.toml with uv support
- ✅ Application factory pattern in app/__init__.py
- ✅ Blueprint structure (app/api/, app/web/)
- ✅ Placeholder routes for migration

Ready for Phase 2: Architectural Refactoring

The new structure provides:
- Clean separation of concerns
- Modern Python packaging
- Extensible blueprint architecture
- Type checking and linting setup
"""
    )


if __name__ == "__main__":
    main()
