# Dependency Management Guide

**Sprint:** Sprint 25 (Feature 25.6)
**Last Updated:** 2025-11-13
**Related:** Sprint 24 (Dependency Groups & Lazy Imports)

---

## Table of Contents

1. [Overview](#overview)
2. [Poetry Dependency Groups](#poetry-dependency-groups)
3. [Installation Patterns](#installation-patterns)
4. [Lazy Import Strategy](#lazy-import-strategy)
5. [CI/CD Optimization](#cicd-optimization)
6. [Adding New Dependencies](#adding-new-dependencies)
7. [Troubleshooting](#troubleshooting)

---

## Overview

AegisRAG uses **Poetry** for dependency management with a modular **dependency group** strategy introduced in Sprint 24. This approach provides:

### Benefits

- **Selective Installation:** Install only what you need (~600MB core vs ~2.5GB full)
- **Faster CI Builds:** 85% speedup with Poetry cache (Feature 24.12)
- **Lazy Imports:** Optional dependencies loaded only when used (Feature 24.15)
- **Smaller Docker Images:** Production images can exclude unused features
- **Developer Flexibility:** Different teams can use different feature sets

### Architecture

```
Core Dependencies (~600MB)
├── FastAPI, Uvicorn (API layer)
├── Qdrant Client (vector DB)
├── Neo4j Driver (graph DB)
├── Redis Client (cache)
├── Ollama Client (LLM)
├── ANY-LLM SDK (multi-cloud routing)
├── BGE-M3 (embeddings - local)
├── LangGraph, LangChain Core (orchestration)
└── Prometheus Client, Structlog (observability)

Optional Dependency Groups
├── ingestion (~500MB) - LlamaIndex, SpaCy, Docling
├── reranking (~400MB) - sentence-transformers
├── evaluation (~600MB) - RAGAS, datasets
├── graph-analysis (~150MB) - graspologic
└── ui (~200MB) - Gradio
```

---

## Poetry Dependency Groups

### Core Dependencies (Always Installed)

**Install:** `poetry install`
**Size:** ~600MB
**Purpose:** Production-ready API with basic RAG functionality

**Includes:**
- **API Framework:** FastAPI, Uvicorn, Pydantic
- **Vector DB:** Qdrant client
- **Graph DB:** Neo4j driver
- **Cache:** Redis with async support
- **LLM:** Ollama client, ANY-LLM SDK
- **Orchestration:** LangGraph, LangChain Core
- **Memory:** Graphiti, Redis checkpointing
- **Security:** JWT, password hashing
- **Monitoring:** Prometheus client, Structlog

**Use Cases:**
- Production deployment (vector + graph RAG)
- Minimal Docker images
- CI/CD unit tests (no ingestion/evaluation)

---

### Optional Groups

#### 1. Ingestion Group

**Install:** `poetry install --with ingestion`
**Size:** ~500MB
**Purpose:** Document parsing and ingestion pipeline

**Includes:**
- **LlamaIndex:** Core library + 300+ connectors (deprecated as primary, kept as fallback)
- **SpaCy:** NLP and entity extraction (~200MB with models)
- **Docling:** PDF parsing (note: Docling CUDA runs in Docker container)
- **Format Support:** python-pptx, docx2txt

**Use Cases:**
- Document ingestion workflows
- Batch document processing
- Development with local file uploads

**Not Required For:**
- Production API-only deployments (ingestion runs separately)
- Vector search without new document uploads

---

#### 2. Reranking Group

**Install:** `poetry install --with reranking`
**Size:** ~400MB (includes PyTorch models)
**Purpose:** Cross-encoder reranking for improved search quality

**Includes:**
- **sentence-transformers:** HuggingFace cross-encoder models
- **scikit-learn:** Cosine similarity for semantic deduplication

**Use Cases:**
- High-quality retrieval (reranking top-k results)
- Semantic deduplication of entities (Sprint 13)

**Performance Impact:**
- Reranking adds ~50ms latency
- Improves precision@10 by 15-20%

---

#### 3. Evaluation Group

**Install:** `poetry install --with evaluation`
**Size:** ~600MB+ (WARNING: datasets is VERY HEAVY)
**Purpose:** RAG quality evaluation with RAGAS framework

**Includes:**
- **RAGAS:** RAG evaluation metrics (faithfulness, relevance, etc.)
- **datasets:** HuggingFace datasets library (~500MB)

**Use Cases:**
- Offline evaluation of RAG quality
- Benchmarking retrieval strategies
- Research and experimentation

**NOT Recommended For:**
- CI/CD pipelines (too heavy, use mocks instead)
- Production deployments

---

#### 4. Graph-Analysis Group

**Install:** `poetry install --with graph-analysis`
**Size:** ~150MB
**Purpose:** Advanced graph statistics and community detection

**Includes:**
- **graspologic:** Graph statistics and community detection

**Use Cases:**
- Graph analytics and visualization
- Community detection in knowledge graphs
- Graph algorithm research

**Note:** Python 3.12 limited by graspologic dependency (use 3.11 or wait for update)

---

#### 5. UI Group

**Install:** `poetry install --with ui`
**Size:** ~200MB
**Purpose:** Gradio web interface for rapid prototyping

**Includes:**
- **Gradio:** Web UI framework

**Use Cases:**
- Local development with chat interface
- Demos and prototypes
- Internal testing

**Not Required For:**
- Production API-only deployments
- CI/CD testing

---

### Development Dependencies

**Install:** `poetry install --with dev`
**Size:** ~100MB
**Purpose:** Testing, linting, type checking

**Includes:**
- **Testing:** pytest, pytest-asyncio, pytest-cov, pytest-mock, pytest-timeout
- **Code Quality:** ruff, black, mypy, bandit
- **Type Stubs:** types-pyyaml, types-aiofiles, types-python-jose, types-passlib

**Use Cases:**
- Local development
- CI/CD quality gates
- Pre-commit hooks

---

## Installation Patterns

### Local Development

```bash
# Minimal core (vector + graph RAG only)
poetry install

# Core + document ingestion
poetry install --with ingestion

# Core + ingestion + reranking (recommended for development)
poetry install --with ingestion,reranking

# Full development environment (all features + tests)
poetry install --with dev,ingestion,reranking,ui
```

### CI/CD

```bash
# Code quality checks (fastest, ~600MB)
poetry install --only dev --no-root

# Unit tests (core + dev, no heavy dependencies)
poetry install --with dev

# Integration tests (core + dev + ingestion for E2E)
poetry install --with dev,ingestion
```

### Production

```bash
# API-only deployment (smallest image)
poetry install --no-dev

# API + ingestion service
poetry install --with ingestion --no-dev

# All features (full deployment)
poetry install --all-extras --no-dev
```

### Docker Builds

```dockerfile
# Multi-stage build for minimal images
FROM python:3.12-slim AS base
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry config virtualenvs.create false

# Production API (core only)
FROM base AS production
RUN poetry install --no-dev --no-interaction

# Development (all features)
FROM base AS development
RUN poetry install --all-extras --no-interaction
```

---

## Lazy Import Strategy

**Introduced:** Sprint 24, Feature 24.15
**Purpose:** Import optional dependencies only when needed

### Implementation Pattern

```python
# Bad: Import at module level (fails if dependency not installed)
from llama_index import VectorStoreIndex  # ImportError if not installed

# Good: Lazy import at function level
def ingest_document_with_llamaindex(file_path: str):
    """Ingest document using LlamaIndex (optional dependency)."""
    try:
        from llama_index import VectorStoreIndex  # Import only if called
    except ImportError:
        raise RuntimeError(
            "LlamaIndex not installed. Install with: poetry install --with ingestion"
        )

    # Use VectorStoreIndex...
```

### Benefits

- **Graceful Degradation:** Code doesn't crash if optional dependency missing
- **Clear Error Messages:** Tell user how to install missing dependency
- **Faster Startup:** Only import what you use
- **Smaller Memory Footprint:** Don't load unused libraries

### Lazy Import Pattern (Reusable)

```python
def lazy_import(module_name: str, package: str, install_group: str):
    """Lazily import a module with helpful error message."""
    try:
        return importlib.import_module(module_name, package)
    except ImportError:
        raise RuntimeError(
            f"{module_name} not installed. "
            f"Install with: poetry install --with {install_group}"
        )

# Usage:
def process_with_ragas():
    ragas = lazy_import("ragas", None, "evaluation")
    # Use ragas module...
```

---

## CI/CD Optimization

### Poetry Cache Strategy (Sprint 24, Feature 24.12)

**Result:** 85% CI speedup
**Mechanism:** GitHub Actions cache for Poetry dependencies

**GitHub Actions Configuration:**

```yaml
- name: Cache Poetry Dependencies
  uses: actions/cache@v4
  with:
    path: |
      ~/.cache/pypoetry
      .venv
    key: ${{ runner.os }}-poetry-${{ hashFiles('**/poetry.lock') }}
    restore-keys: |
      ${{ runner.os }}-poetry-

- name: Install Poetry
  run: |
    pip install poetry
    poetry config virtualenvs.in-project true

- name: Install Dependencies (selective)
  run: |
    poetry install --with dev --no-interaction
```

**Cache Behavior:**
- **Cache Hit:** Restore from cache (~30s)
- **Cache Miss:** Full install (~5min) → cache for next run
- **Cache Key:** `poetry.lock` hash (invalidates on dependency changes)

---

## Adding New Dependencies

### Step 1: Determine Dependency Group

Ask yourself:
1. **Is it required for core RAG functionality?** → Core dependency
2. **Is it for document ingestion only?** → ingestion group
3. **Is it for testing/development?** → dev group
4. **Is it for a specific optional feature?** → Appropriate optional group

### Step 2: Add Dependency

```bash
# Core dependency (always installed)
poetry add package-name

# Optional group dependency
poetry add --group ingestion package-name
poetry add --group dev package-name

# With version constraint
poetry add package-name@^1.0.0
```

### Step 3: Update pyproject.toml

Ensure the dependency is in the correct section:

```toml
# Core dependencies
[tool.poetry.dependencies]
fastapi = "^0.115.0"

# Optional group
[tool.poetry.group.ingestion.dependencies]
llama-index-core = "^0.14.3"

# Development dependencies
[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
```

### Step 4: Regenerate Lock File

```bash
# Regenerate poetry.lock with new dependency
poetry lock --no-update

# Or update all dependencies (careful!)
poetry update
```

### Step 5: Update CI Configuration

If adding to optional group, update CI jobs to install it:

```yaml
# .github/workflows/ci.yml
- name: Install Dependencies
  run: |
    # Add new group if needed
    poetry install --with dev,ingestion,NEW_GROUP
```

### Step 6: Update Documentation

- Add dependency to `DEPENDENCY_MANAGEMENT.md` (this file)
- Update `CURRENT_ARCHITECTURE.md` if it changes architecture
- Update `README.md` installation instructions if needed

---

## Troubleshooting

### Issue: "Module not found" error in CI

**Cause:** CI is using selective dependency installation without the required group.

**Solution:** Update CI workflow to install the required group:

```yaml
# Before (fails if using llama_index)
poetry install --with dev

# After (includes ingestion group)
poetry install --with dev,ingestion
```

---

### Issue: Poetry lock file conflicts

**Cause:** Multiple developers adding dependencies concurrently.

**Solution:**

```bash
# 1. Pull latest changes
git pull origin main

# 2. Regenerate lock file
poetry lock --no-update

# 3. Commit updated lock file
git add poetry.lock
git commit -m "chore(deps): Regenerate poetry.lock"
```

---

### Issue: CI cache not working

**Cause:** Cache key mismatch or cache eviction.

**Solution:**

```yaml
# Verify cache configuration in .github/workflows/ci.yml
- name: Cache Poetry Dependencies
  uses: actions/cache@v4
  with:
    path: |
      ~/.cache/pypoetry
      .venv
    key: ${{ runner.os }}-poetry-${{ hashFiles('**/poetry.lock') }}
    restore-keys: |
      ${{ runner.os }}-poetry-

# Check GitHub Actions cache size (max 10GB per repo)
```

---

### Issue: Dependency version conflicts

**Cause:** Two packages require incompatible versions of the same dependency.

**Solution:**

```bash
# 1. Check which packages conflict
poetry show --tree

# 2. Try updating dependencies
poetry update package-name

# 3. If still conflicts, constrain versions manually in pyproject.toml
[tool.poetry.dependencies]
conflicting-package = ">=1.0,<2.0"
```

---

### Issue: Docker build fails with dependency errors

**Cause:** Multi-stage Docker build using wrong Poetry commands.

**Solution:**

```dockerfile
# Ensure Poetry is configured correctly
RUN pip install poetry && poetry config virtualenvs.create false

# Use --no-interaction for CI/Docker
RUN poetry install --no-dev --no-interaction

# For optional groups
RUN poetry install --with ingestion --no-dev --no-interaction
```

---

### Issue: Slow Poetry installs locally

**Cause:** Poetry downloads packages every time.

**Solution:**

```bash
# Enable Poetry cache
poetry config cache-dir ~/.cache/pypoetry

# Use --no-update to avoid dependency resolution
poetry install --no-update

# Parallel installation (faster)
poetry config installer.max-workers 10
```

---

## Best Practices

### 1. Minimize Core Dependencies

- **Keep core lean:** Only add to core if required for all deployments
- **Use optional groups:** Most features should be optional
- **Evaluate tradeoffs:** Each core dependency adds ~5-50MB to Docker image

### 2. Pin Major Versions

```toml
# Good: Allow minor/patch updates
fastapi = "^0.115.0"  # Allows 0.115.x, 0.116.x, etc.

# Good: Pin to specific version for stability
qdrant-client = "~1.11.0"  # Allows 1.11.x only

# Avoid: Unpinned (breaks reproducibility)
requests = "*"
```

### 3. Document Installation Requirements

When adding optional dependencies, update:
- This file (DEPENDENCY_MANAGEMENT.md)
- Function docstrings (mention required group)
- Error messages (tell user how to install)

Example:

```python
def evaluate_with_ragas():
    """
    Evaluate RAG quality using RAGAS framework.

    Requires: poetry install --with evaluation

    Raises:
        RuntimeError: If ragas not installed
    """
    try:
        import ragas
    except ImportError:
        raise RuntimeError(
            "RAGAS not installed. Install with: poetry install --with evaluation"
        )
```

### 4. CI/CD Optimization

- **Selective Installation:** Only install what each CI job needs
- **Cache Aggressively:** Use GitHub Actions cache for Poetry
- **Parallel Jobs:** Run code quality, tests, etc. in parallel
- **Skip Heavy Dependencies:** Mock instead of installing evaluation group in CI

### 5. Security Updates

```bash
# Check for security vulnerabilities
poetry run safety check

# Update specific package
poetry update package-name

# Update all (careful, test thoroughly)
poetry update
```

---

## Migration Guide (from pip/requirements.txt)

If migrating from pip to Poetry:

### Step 1: Export existing requirements

```bash
pip freeze > requirements.txt
```

### Step 2: Initialize Poetry project

```bash
poetry init

# Follow prompts to create pyproject.toml
```

### Step 3: Add dependencies

```bash
# Add each dependency
cat requirements.txt | while read line; do
    poetry add "$line"
done
```

### Step 4: Organize into groups

Manually move dependencies in `pyproject.toml`:

```toml
# Move optional dependencies to groups
[tool.poetry.group.ingestion.dependencies]
llama-index = "^0.14.3"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0.0"
```

### Step 5: Test installation

```bash
# Remove old virtualenv
rm -rf venv/

# Install with Poetry
poetry install

# Run tests
poetry run pytest
```

---

## References

- [Poetry Documentation](https://python-poetry.org/docs/)
- [Poetry Dependency Groups](https://python-poetry.org/docs/managing-dependencies/#dependency-groups)
- [Lazy Import Pattern (PEP 690)](https://peps.python.org/pep-0690/)
- [Sprint 24 Planning](../sprints/SPRINT_24_PLAN.md)

---

**Last Updated:** 2025-11-13 (Sprint 25, Feature 25.6)
**Maintained By:** Backend Team
**Next Review:** Sprint 26
