# TQ GenAI Chat - CRUSH

This file provides agentic coding assistants with essential commands and guidelines for this repository.

## Commands

- **Run all tests:** `pytest`
- **Run a single test file:** `pytest tests/test_file.py`
- **Run a single test function:** `pytest tests/test_file.py::test_function`
- **Lint:** `ruff check .`
- **Format:** `black .`
- **Typecheck:** `mypy .`

## Code Style

- **Formatting:** Use `black` with a line length of 100 characters.
- **Imports:** Sort imports with `isort`.
- **Typing:** Use strict `mypy` typing. All functions must have type hints.
- **Naming:** Follow PEP 8 naming conventions (snake_case for functions and variables, PascalCase for classes).
- **Error Handling:** Use specific exception types. Avoid broad `except Exception:` clauses.
- **Docstrings:** Use Google-style docstrings for all public modules, classes, and functions.

## Project Structure

- `app.py`: Main Flask application.
- `core/`: Core business logic.
- `services/`: Third-party service integrations.
- `tests/`: Pytest tests.

## Dependencies

- Use `uv` for dependency management.
- Add new dependencies to `pyproject.toml` under `[project.dependencies]`.
- Development dependencies go in `[project.optional-dependencies]`.
