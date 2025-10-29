# TASK: Comprehensive Codebase Refactor, Optimization, and Modernization

Follow these steps when editing or generating code:

1. **Refactor & Simplify**
   - Apply DRY: remove redundant logic.
   - Simplify loops/conditionals → reduce cyclomatic complexity.
   - Use clear, descriptive variable and function names.
   - Adopt modern syntax (async/await, comprehensions, f-strings, etc.).

2. **Performance Optimization**
   - Profile critical paths; optimize speed and memory.
   - Replace inefficient algorithms/data structures.
   - Optimize database queries (reduce N+1, add indexes).
   - Add caching for expensive operations.

3. **Architecture & Patterns**
   - Break code into modular components (SRP).
   - Define clear module boundaries (low coupling).
   - Apply design patterns for scalability (e.g., Factory, Observer, Strategy).

4. **Code Quality & Error Handling**
   - Enforce strict linting + formatting (Black, ESLint, Pylint, Prettier).
   - Standardize error handling (structured exceptions).
   - Keep files ≤ 500 lines for modularity.

5. **Security**
   - Fix OWASP Top 10 vulnerabilities.
   - Sanitize all external inputs.
   - Remove hardcoded secrets; use environment variables/secret manager.

6. **Testing**
   - Ensure all existing tests pass post-refactor.
   - Add new tests for modified/new logic.
   - Aim for >80% coverage.

7. **Documentation**
   - Add inline comments for complex logic.
   - Update/generate docstrings (Google/NumPy/JSdoc style).
   - Revise README.md with setup, build, config, API usage.

8. **Cleanup**
   - Delete commented-out/dead code.
   - Move deprecated/obsolete files → `./trash2review`.

9. **Version Control**
   - Work in feature branch: `refactor/codebase-optimization-2025`.
   - Use atomic commits with conventional messages (`feat:`, `refactor:`, `docs:`).

## Phase 1 – Baseline Audit (2025-10-29)

- **Monolith hotspots**: `core/document_chunker.py` (1,254 LOC), `core/async_handler.py` (804 LOC), and `core/api_gateway.py` (621 LOC) exceed the 500-line ceiling and mix multiple responsibilities (chunk strategies, executor lifecycle, provider dispatch respectively).
- **Framework drift**: Mixed Flask/FastAPI layers (`core/security.py`, legacy `services/trash2review/app.py`) share middleware concerns, creating duplicate auth/rate-limit code and conflicting request lifecycles.
- **Async execution**: ThreadPool abstractions in `core/async_handler.py` duplicate logic found in `core/background_tasks.py`; both wrap CPU-bound ops without shared instrumentation or backpressure controls.
- **File/vector pipeline**: `core/document_store.py` and `services/file_manager.py` handle similar indexing steps with parallel caching rules, leading to redundant TF-IDF calculations and inconsistent error handling.
- **Provider integrations**: `core/api_services.py` bundles provider selection, retries, and response normalization in a single module; no clear strategy interface and rate-limit logic scattered across `core/providers.py` and router layers.
- **Security posture**: Global request validation lives in Flask `core/security.py`; FastAPI routes lack equivalent safeguards (headers, input sanitization, rate limiting), exposing gaps once Flask fallback is removed.
- **Testing debt**: No async/unit coverage observed for chunking, provider fallback, or Redis-backed rate limiting. `tests/` directory missing entirely.
- **Tooling gaps**: Lint/format configs absent from repo; `pyproject.toml` lacks Black/Ruff/Pylint settings. No CI automation noted.

### Phase 2 Target Areas

1. Split oversized core modules into cohesive packages (e.g., `core/chunking/`, `core/executors/`, provider strategy interfaces).
2. Consolidate async execution primitives into a single service with bounded queues and shared metrics hooks.
3. Design unified provider strategy pattern with pluggable retry/backoff and per-provider throttling.
4. Normalize file ingestion pipeline with streaming parsers, shared caching, and sanitization for untrusted content.
5. Introduce security middleware equivalents for FastAPI routes (headers, rate limiting, API key validation).
6. Scaffold pytest suite with async fixtures, provider mocks, and Redis instrumentation tests.
7. Add repo-level tooling: formatter, linter, type checker, and GitHub Actions smoke tests.

## Phase 2 – Progress Log (2025-10-29)

- Created `core/chunking/` package with typed strategies (`semantic`, `pdf`, `docx`, `csv`), shared config, metadata models, and manager facade.
- Replaced monolithic `core/document_chunker.py` with lightweight wrapper that proxies to the modular package for backward compatibility.
- Refactored `core/document_store.py` to delegate chunk creation to `DocumentChunkerManager`, persist chunks transactionally, and emit fallback chunks for small documents.
- Added `register_chunks` API to `DocumentChunkerManager` and ensured `DocumentStore` calls it, keeping in-memory registry in sync with DB writes (including fallback chunks).
- Updated ingestion paths:
   - FastAPI: `/app/routers/files.py` already persists via `FileManager.add_document` (no change required).
   - Flask: `/app/api/documents.py` now ingests OCR uploads into `DocumentStore` and returns `chunk_summary`.
   - Flask blueprint: `/blueprints/file.py` upload now extracts content with `FileProcessor`, persists via `FileManager` (DocumentStore), and returns `document_id` + `chunk_summary`.
- Reworked `core/context.py` to read/write exclusively through `DocumentStore` and to assemble chunk-based context snippets with a configurable horizon; added fallbacks and reduced complexity.
- Codacy analysis run for all edited files; no issues reported after fixes.