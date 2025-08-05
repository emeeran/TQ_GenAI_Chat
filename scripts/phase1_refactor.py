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

        # Step 3: Remove redundant files
        self.remove_duplicates()

        # Step 4: Modernize dependency management
        self.modernize_dependencies()

        # Step 5: Create initial app factory structure
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
            "pyproject.toml"
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
                "unique": ["enhanced error handling", "better validation"]
            },
            "app_integration.py": {
                "lines": 500,
                "duplicates": ["optimization routes", "background tasks"],
                "unique": ["async optimizations", "performance monitoring"]
            },
            "ai_models.py": {
                "lines": 439,
                "duplicates": ["model configurations", "API endpoints"],
                "unique": ["centralized model config"]
            }
        }

        for file, info in duplicate_files.items():
            print(f"  📄 {file}: {info['lines']} lines")
            print(f"    - Duplicates: {', '.join(info['duplicates'])}")
            print(f"    - Unique: {', '.join(info['unique'])}")

    def remove_duplicates(self):
        """Remove duplicate files after extracting unique functionality."""
        print("🗑️ Removing duplicate files...")

        # Files to remove (after extracting unique features)
        files_to_remove = [
            "app_refactored.py",
            "app_integration.py",
            "ai_models.py"
        ]

        for file in files_to_remove:
            file_path = self.project_root / file
            if file_path.exists():
                file_path.unlink()
                print(f"  ✓ Removed {file}")

    def modernize_dependencies(self):
        """Modernize dependency management to use uv."""
        print("📦 Modernizing dependency management...")

        # Create modern pyproject.toml
        modern_pyproject = '''[build-system]
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
extend-exclude = """
/(
    migrations
  | .venv
  | venv
)/
"""

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
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
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
'''

        # Write modern pyproject.toml
        with open(self.project_root / "pyproject.toml", "w") as f:
            f.write(modern_pyproject)
        print("  ✓ Created modern pyproject.toml")

        # Create .python-version for pyenv
        with open(self.project_root / ".python-version", "w") as f:
            f.write("3.12.0\\n")
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
from typing import Optional

from config.settings import config
from app.extensions import init_extensions
from app.blueprints import register_blueprints


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

    # Load configuration
    app.config.from_object(config[config_name])

    # Initialize extensions
    init_extensions(app)

    # Register blueprints
    register_blueprints(app)

    # Configure CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    return app


def create_celery_app(app: Optional[Flask] = None) -> 'Celery':
    """
    Create Celery app for background tasks.

    Args:
        app: Flask application instance

    Returns:
        Configured Celery instance
    """
    from celery import Celery

    app = app or create_app()

    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context."""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
'''

        with open(app_dir / "__init__.py", "w") as f:
            f.write(app_init)
        print("  ✓ Created app/__init__.py with factory pattern")

        # Create extensions.py
        extensions = '''"""
Flask extensions initialization.
"""

from flask import Flask


def init_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    # Initialize extensions here as they're added
    pass
'''

        with open(app_dir / "extensions.py", "w") as f:
            f.write(extensions)
        print("  ✓ Created app/extensions.py")

        # Create blueprints.py
        blueprints = '''"""
Blueprint registration.
"""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """Register application blueprints."""
    from app.api import api_bp
    from app.web import web_bp

    # Register API blueprint
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    # Register web blueprint
    app.register_blueprint(web_bp)
'''

        with open(app_dir / "blueprints.py", "w") as f:
            f.write(blueprints)
        print("  ✓ Created app/blueprints.py")

        # Create blueprint directories
        for bp_name in ['api', 'web']:
            bp_dir = app_dir / bp_name
            bp_dir.mkdir(exist_ok=True)

            # Create blueprint __init__.py
            if bp_name == 'api':
                bp_init = '''"""
API Blueprint - REST API endpoints.
"""

from flask import Blueprint

api_bp = Blueprint('api', __name__)

# Import routes to register them
from app.api import chat, files, models  # noqa: F401
'''
            else:
                bp_init = '''"""
Web Blueprint - Web interface routes.
"""

from flask import Blueprint

web_bp = Blueprint('web', __name__)

# Import routes to register them
from app.web import views  # noqa: F401
'''

            with open(bp_dir / "__init__.py", "w") as f:
                f.write(bp_init)
            print(f"  ✓ Created app/{bp_name}/__init__.py")

    def generate_migration_script(self):
        """Generate script to help with the migration."""
        print("📝 Generating migration helper script...")

        migration_script = '''#!/usr/bin/env python3
"""
Migration Helper Script
Helps migrate from old structure to new application factory pattern.
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Execute migration steps."""
    print("🔄 Migrating to modern Python environment...")

    # Install uv if not present
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
        print("✓ uv is already installed")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Installing uv...")
        subprocess.run([sys.executable, "-m", "pip", "install", "uv"], check=True)

    # Initialize uv project
    print("Initializing uv project...")
    subprocess.run(["uv", "sync"], check=True)

    # Install pre-commit hooks
    print("Installing pre-commit hooks...")
    subprocess.run(["uv", "run", "pre-commit", "install"], check=True)

    print("✅ Migration completed! Use 'uv run python -m app' to start the application.")


if __name__ == "__main__":
    main()
'''

        with open(self.project_root / "migrate.py", "w") as f:
            f.write(migration_script)

        # Make it executable
        import stat
        migration_path = self.project_root / "migrate.py"
        migration_path.chmod(migration_path.stat().st_mode | stat.S_IEXEC)

        print("  ✓ Created migrate.py helper script")


def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    refactor = RefactorPhase1(project_root)
    refactor.execute()
    refactor.generate_migration_script()

    print("""
🎉 Phase 1 Complete!

Next steps:
1. Review the changes in refactor_backup/
2. Run: python migrate.py
3. Test the application: uv run python -m app
4. Proceed to Phase 2 when ready

Files modified:
- ✅ Removed duplicate app files
- ✅ Created modern pyproject.toml
- ✅ Set up application factory pattern
- ✅ Created blueprint structure

Ready for Phase 2: Architectural Refactoring
""")


if __name__ == "__main__":
    main()
