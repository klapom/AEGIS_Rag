# AEGIS RAG Backend Refactoring Plan

**Date:** 2025-11-11
**Sprint:** Post-Sprint 21
**Author:** Backend Agent (Claude Code)
**Status:** Draft for Review

---

## Executive Summary

This document provides a comprehensive refactoring plan for the AEGIS RAG backend codebase based on Sprint 21 completion and ADR-026/ADR-028 strategic shifts. The analysis identified **47 refactoring items** across 4 priority levels, focusing on deprecated code removal, duplication elimination, and architectural consistency.

**Key Findings:**
- 2 files marked DEPRECATED and ready for removal (unified_ingestion.py, three_phase_extractor.py)
- 2 duplicate base agent implementations (base.py, base_agent.py are identical)
- 2 duplicate embedding services (embeddings.py, embedding_service.py - wrapper pattern)
- 30+ TODO comments requiring resolution or documentation
- Inconsistent error handling patterns across components
- Missing type hints in several modules
- Configuration management could be improved with dependency injection

---

## Priority 1: Critical (Security & Deprecated Code)

### 1.1 Remove Deprecated Unified Ingestion Pipeline
**File:** `src/components/shared/unified_ingestion.py`

**Issue:**
- Marked DEPRECATED in Sprint 21 (lines 4-24)
- Replaced by LangGraph ingestion pipeline (ADR-027)
- Parallel execution (asyncio.gather) incompatible with memory constraints
- Breaking changes announced for Sprint 22 removal

**Current Usage:**
```python
# DEPRECATED: Sprint 21
from src.components.shared.unified_ingestion import UnifiedIngestionPipeline
```

**Replacement:**
```python
# NEW: Sprint 21+
from src.components.ingestion.langgraph_pipeline import create_ingestion_graph
```

**Proposed Solution:**
1. Grep codebase for imports of `UnifiedIngestionPipeline`
2. Update all references to use `create_ingestion_graph`
3. Move file to `archive/deprecated/` with timestamp
4. Update documentation to remove references

**Estimated Complexity:** Medium
**Breaking Changes:** Yes (requires import updates in dependent code)
**Dependencies:** Complete LangGraph migration validation

---

### 1.2 Remove/Archive Three-Phase Extractor
**File:** `src/components/graph_rag/three_phase_extractor.py`

**Issue:**
- ADR-026: Pure LLM extraction is now default (Sprint 21)
- Three-phase pipeline (SpaCy NER + Dedup + Gemma) deprecated
- Config default changed from `three_phase` to `llm_extraction`
- Lower quality than pure LLM approach

**Current Status:**
```python
# src/core/config.py - Sprint 21+
extraction_pipeline: Literal["lightrag_default", "three_phase", "llm_extraction"] = Field(
    default="llm_extraction",  # Changed from "three_phase"
)
```

**Proposed Solution:**
**Option A: Complete Removal** (Recommended)
1. Remove file from codebase
2. Update `extraction_factory.py` to remove three_phase branch
3. Update config to remove `"three_phase"` from Literal
4. Archive to `archive/deprecated/three_phase_extractor_sprint13-20.py`

**Option B: Keep for A/B Testing** (Conservative)
1. Keep file but add prominent DEPRECATED warning
2. Update docs to discourage usage
3. Remove in Sprint 23 after LLM extraction proves stable

**Recommendation:** Option A (complete removal) - ADR-026 clearly states LLM extraction is superior and default. No need to maintain deprecated code.

**Estimated Complexity:** Low
**Breaking Changes:** Yes (removes config option)
**Dependencies:** Verify no production systems use `extraction_pipeline=three_phase`

---

### 1.3 Resolve LlamaIndex Deprecation Strategy
**Files:**
- `src/components/vector_search/ingestion.py` (lines 137-163: DEPRECATED method)
- All LlamaIndex import locations

**Issue:**
- ADR-028: LlamaIndex deprecated as primary ingestion framework
- Docling CUDA Container is now primary parser
- `DocumentIngestionPipeline.load_documents()` marked DEPRECATED (lines 137-163)
- LlamaIndex kept only as fallback for connectors

**Current Deprecated Code:**
```python
# src/components/vector_search/ingestion.py
async def load_documents(self, input_dir: str | Path, ...) -> list[Document]:
    """⚠️ DEPRECATED: Sprint 21 - This method will be replaced by DoclingContainerClient"""
    # Uses LlamaIndex SimpleDirectoryReader
    loader = SimpleDirectoryReader(...)
    documents = loader.load_data()
```

**Proposed Solution:**
1. **Immediate (Sprint 22):**
   - Add runtime deprecation warning to `load_documents()`
   - Update all callers to use Docling
   - Document fallback scenarios in code comments

2. **Short-term (Sprint 23):**
   - Remove `load_documents()` method entirely
   - Keep LlamaIndex dependency for connectors only
   - Update `DocumentIngestionPipeline` to require pre-parsed Docling documents

**Estimated Complexity:** High (affects multiple ingestion paths)
**Breaking Changes:** Yes (requires migration to Docling)
**Dependencies:** Complete Docling integration testing

---

## Priority 2: High (Code Duplication & Inconsistencies)

### 2.1 Consolidate Duplicate Base Agent Implementations
**Files:**
- `src/agents/base.py` (155 lines)
- `src/agents/base_agent.py` (155 lines)

**Issue:**
Both files contain **IDENTICAL** `BaseAgent` class implementations:
- Same abstract `process()` method
- Same helper methods (`_add_trace`, `_measure_latency`, etc.)
- Same imports and structure
- Creates confusion about which to use

**Current Duplication:**
```python
# src/agents/base.py
class BaseAgent(ABC):
    """Abstract base class for all agents."""
    # 155 lines of implementation

# src/agents/base_agent.py
class BaseAgent(ABC):
    """Abstract base class for all agents."""
    # IDENTICAL 155 lines!
```

**Proposed Solution:**
1. **Keep:** `src/agents/base_agent.py` (more explicit naming)
2. **Remove:** `src/agents/base.py`
3. **Update all imports:**
   ```python
   # OLD
   from src.agents.base import BaseAgent

   # NEW
   from src.agents.base_agent import BaseAgent
   ```

**Verification:**
```bash
# Check for differences
diff src/agents/base.py src/agents/base_agent.py
# (Expect: No differences)
```

**Estimated Complexity:** Low (simple import refactoring)
**Breaking Changes:** No (transparent to API)
**Dependencies:** None

---

### 2.2 Consolidate Duplicate Embedding Services
**Files:**
- `src/components/shared/embedding_service.py` (UnifiedEmbeddingService - 269 lines)
- `src/components/vector_search/embeddings.py` (EmbeddingService - 160 lines - wrapper)

**Issue:**
`EmbeddingService` is just a wrapper around `UnifiedEmbeddingService` (Sprint 11):
```python
# src/components/vector_search/embeddings.py
class EmbeddingService:
    """Wrapper around UnifiedEmbeddingService for backward compatibility."""

    def __init__(self, ...):
        self.unified_service = get_unified_service()  # Delegates everything!

    async def embed_text(self, text: str) -> list[float]:
        return await self.unified_service.embed_single(text)  # Simple delegation
```

**Purpose:** Backward compatibility (Sprint 11 migration)

**Proposed Solution:**
**Option A: Remove Wrapper** (Recommended for Sprint 23+)
1. Update all imports to use `UnifiedEmbeddingService` directly
2. Remove `EmbeddingService` wrapper
3. Simpler architecture, single source of truth

**Option B: Keep Wrapper Short-Term** (Conservative)
1. Add deprecation warning to `EmbeddingService.__init__()`
2. Update docs to recommend `UnifiedEmbeddingService`
3. Remove in Sprint 24 after migration period

**Recommendation:** Option B - Keep wrapper for 1-2 sprints to ensure smooth migration, then remove.

**Estimated Complexity:** Medium (requires import updates across codebase)
**Breaking Changes:** Yes (if Option A chosen)
**Dependencies:** Test coverage validation

---

### 2.3 Standardize Client Naming Conventions
**Files:** Multiple client classes with inconsistent patterns

**Issue:**
Inconsistent naming for client wrapper classes:
- `QdrantClientWrapper` (wrapper suffix)
- `Neo4jClient` (no suffix)
- `DoclingContainerClient` (container + client)
- `MCPClient` (no suffix)
- `GraphitiWrapper` (wrapper suffix)
- `LightRAGWrapper` (wrapper suffix)

**Proposed Solution:**
Standardize to **`<Service>Client`** pattern (most common in codebase):

```python
# BEFORE
QdrantClientWrapper     → QdrantClient
GraphitiWrapper         → GraphitiClient
LightRAGWrapper         → LightRAGClient
DoclingContainerClient  → DoclingClient (container is implementation detail)

# AFTER
QdrantClient           ✓
Neo4jClient            ✓ (already correct)
DoclingClient          ✓
MCPClient              ✓ (already correct)
GraphitiClient         ✓
LightRAGClient         ✓
```

**Rationale:**
- `Client` suffix indicates external service wrapper
- No need for `Wrapper` suffix (redundant)
- `Container` is implementation detail, not API concern

**Estimated Complexity:** Medium (requires import updates)
**Breaking Changes:** Yes (public API changes)
**Dependencies:** Update tests, docs, and all imports

---

### 2.4 Standardize Error Handling Patterns
**Issue:** Inconsistent error handling across components

**Current Inconsistencies:**

**Pattern 1: Bare try/except**
```python
# src/components/graph_rag/community_detector.py
try:
    result = await detect_communities()
except Exception as e:
    logger.error("detection_failed", error=str(e))
    return []  # Silent failure
```

**Pattern 2: Re-raise with custom exception**
```python
# src/components/vector_search/ingestion.py
try:
    documents = await load()
except Exception as e:
    logger.error("load_failed", error=str(e))
    raise VectorSearchError(f"Failed to load: {e}") from e  # Good!
```

**Pattern 3: Tenacity retry decorator**
```python
# src/components/shared/embedding_service.py
@retry(stop=stop_after_attempt(3), wait=wait_exponential(...))
async def embed_single(self, text: str) -> list[float]:
    # Automatic retry with exponential backoff
```

**Proposed Solution:**
Create `src/core/error_handling.py` with standardized patterns:

```python
from typing import TypeVar, Callable, Any
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar('T')

def with_retries(
    max_attempts: int = 3,
    min_wait: float = 2.0,
    max_wait: float = 10.0,
):
    """Decorator for automatic retry with exponential backoff."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        reraise=True,
    )

async def safe_execute(
    operation: Callable[[], T],
    error_class: type[Exception],
    error_message: str,
    fallback: T | None = None,
    log_error: bool = True,
) -> T:
    """Execute operation with standardized error handling.

    Args:
        operation: Async callable to execute
        error_class: Exception class to raise on failure
        error_message: Error message template
        fallback: Optional fallback value (returns instead of raising)
        log_error: Whether to log errors (default: True)

    Returns:
        Operation result or fallback value

    Raises:
        error_class: If operation fails and no fallback provided
    """
    try:
        return await operation()
    except Exception as e:
        if log_error:
            logger.error("operation_failed", error=str(e), exc_info=True)

        if fallback is not None:
            return fallback

        raise error_class(f"{error_message}: {e}") from e
```

**Usage Example:**
```python
# BEFORE
try:
    documents = await self.load_documents(path)
except Exception as e:
    logger.error("load_failed", error=str(e))
    raise VectorSearchError(f"Failed to load: {e}") from e

# AFTER
from src.core.error_handling import safe_execute

documents = await safe_execute(
    operation=lambda: self.load_documents(path),
    error_class=VectorSearchError,
    error_message="Failed to load documents",
)
```

**Estimated Complexity:** High (affects all components)
**Breaking Changes:** No (additive, gradual migration)
**Dependencies:** None

---

### 2.5 Consolidate Chunking Service Implementations
**Files:**
- `src/core/chunking_service.py` (516 lines - unified service)
- `src/components/retrieval/chunking.py` (if exists - legacy?)
- Multiple duplicate chunking logic scattered

**Issue:**
ADR-022 introduced `ChunkingService` as "single source of truth", but legacy chunking code may still exist.

**Verification Needed:**
```bash
grep -r "def chunk" src/components/ --include="*.py"
grep -r "SentenceSplitter" src/ --include="*.py"
grep -r "tiktoken" src/ --include="*.py"
```

**Proposed Solution:**
1. Audit all chunking implementations
2. Migrate to `ChunkingService` API
3. Remove duplicate implementations
4. Ensure all pipelines use unified service

**Estimated Complexity:** Medium
**Breaking Changes:** Depends on findings
**Dependencies:** ADR-022 compliance audit

---

## Priority 3: Medium (Pattern Improvements & Abstractions)

### 3.1 Extract Common Client Base Class
**Issue:** All client classes share common patterns (connection, error handling, logging)

**Current Duplication:**
```python
# src/components/vector_search/qdrant_client.py
class QdrantClient:
    def __init__(self, ...):
        self.logger = structlog.get_logger(__name__)
        self.config = settings
        # Connection logic

    async def connect(self): ...
    async def disconnect(self): ...
    async def health_check(self): ...

# src/components/graph_rag/neo4j_client.py
class Neo4jClient:
    def __init__(self, ...):
        self.logger = structlog.get_logger(__name__)
        self.config = settings
        # SAME connection pattern!

    async def connect(self): ...
    async def disconnect(self): ...
    async def health_check(self): ...
```

**Proposed Solution:**
Create `src/core/base_client.py`:

```python
from abc import ABC, abstractmethod
from typing import Any
import structlog
from src.core.config import Settings

class BaseClient(ABC):
    """Base class for all external service clients.

    Provides:
    - Connection lifecycle management
    - Health checking
    - Structured logging
    - Error handling helpers
    """

    def __init__(self, config: Settings | None = None):
        self.config = config or get_settings()
        self.logger = structlog.get_logger(self.__class__.__name__)
        self._connected = False

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to external service."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to external service."""
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check service health status."""
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
```

**Usage:**
```python
class QdrantClient(BaseClient):
    """Qdrant vector database client."""

    async def connect(self) -> None:
        # Specific implementation
        self._client = AsyncQdrantClient(...)
        self._connected = True

    async def disconnect(self) -> None:
        # Specific implementation
        await self._client.close()
        self._connected = False

    async def health_check(self) -> dict[str, Any]:
        # Specific implementation
        return {"status": "healthy", ...}
```

**Benefits:**
- Reduces boilerplate by ~50 lines per client
- Ensures consistent patterns (health checks, logging, lifecycle)
- Enables async context manager pattern (`async with client:`)

**Estimated Complexity:** Medium
**Breaking Changes:** No (additive base class)
**Dependencies:** None

---

### 3.2 Implement Dependency Injection for Settings
**Issue:** Direct `settings` imports create tight coupling and testing difficulties

**Current Pattern (Tight Coupling):**
```python
# src/components/vector_search/qdrant_client.py
from src.core.config import settings  # Global import!

class QdrantClient:
    def __init__(self):
        self.url = settings.qdrant_url  # Tight coupling
```

**Problems:**
- Hard to test (global state)
- Hard to override settings per instance
- Implicit dependency (not visible in constructor)

**Proposed Pattern (Dependency Injection):**
```python
# src/components/vector_search/qdrant_client.py
from src.core.config import Settings, get_settings

class QdrantClient:
    def __init__(self, config: Settings | None = None):
        self.config = config or get_settings()  # Explicit dependency
        self.url = self.config.qdrant_url
```

**Benefits:**
- Testable (inject mock settings)
- Explicit dependencies
- Instance-specific configuration possible

**Migration Strategy:**
1. Add optional `config` parameter to all classes (backward compatible)
2. Update tests to use explicit config injection
3. Update docs to recommend DI pattern
4. Gradually migrate away from global `settings` imports

**Estimated Complexity:** High (affects ~50+ classes)
**Breaking Changes:** No (backward compatible with defaults)
**Dependencies:** None

---

### 3.3 Standardize Logging Patterns
**Issue:** Inconsistent logging practices across codebase

**Current Inconsistencies:**

**Pattern 1: structlog.get_logger**
```python
import structlog
logger = structlog.get_logger(__name__)  # ✓ Good
```

**Pattern 2: src.core.logging.get_logger**
```python
from src.core.logging import get_logger
logger = get_logger(__name__)  # ✓ Also good, but inconsistent
```

**Pattern 3: No logger binding**
```python
logger.info("event", key=value)  # No context about which module
```

**Proposed Solution:**
Standardize on **`structlog.get_logger(__name__)`** with class-level binding:

```python
# Standard pattern for all modules
import structlog

logger = structlog.get_logger(__name__)

class MyComponent:
    def __init__(self, name: str):
        self.name = name
        self.logger = logger.bind(component=name)  # Bind context

    async def process(self):
        self.logger.info("processing_start")  # Auto-includes component name
```

**Benefits:**
- Consistent logging format
- Better tracing (component context in all logs)
- Easier debugging

**Estimated Complexity:** Low (find & replace)
**Breaking Changes:** No
**Dependencies:** None

---

### 3.4 Create Abstract Retriever Base Class
**Issue:** Multiple retriever implementations with no shared interface

**Current Implementations:**
- `VectorSearchAgent` (vector retrieval)
- `GraphQueryAgent` (graph retrieval)
- `MemoryAgent` (memory retrieval)
- Each with different method signatures and patterns

**Proposed Solution:**
Create `src/core/base_retriever.py`:

```python
from abc import ABC, abstractmethod
from typing import Any, List
from pydantic import BaseModel

class RetrievalContext(BaseModel):
    """Context for retrieval operation."""
    query: str
    top_k: int = 5
    filters: dict[str, Any] | None = None
    metadata: dict[str, Any] = {}

class RetrievalResult(BaseModel):
    """Result from retrieval operation."""
    documents: List[dict[str, Any]]
    scores: List[float] | None = None
    metadata: dict[str, Any] = {}

class BaseRetriever(ABC):
    """Abstract base class for all retrievers."""

    @abstractmethod
    async def retrieve(self, context: RetrievalContext) -> RetrievalResult:
        """Retrieve documents based on context.

        Args:
            context: Retrieval context with query and parameters

        Returns:
            RetrievalResult with documents and scores
        """
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check retriever health status."""
        pass
```

**Usage:**
```python
class VectorSearchAgent(BaseAgent, BaseRetriever):
    async def retrieve(self, context: RetrievalContext) -> RetrievalResult:
        # Vector-specific implementation
        embeddings = await self.embed(context.query)
        results = await self.qdrant.search(embeddings, top_k=context.top_k)
        return RetrievalResult(documents=results, scores=scores)
```

**Benefits:**
- Uniform retrieval interface
- Easier to compose multiple retrievers
- Better type safety with Pydantic models

**Estimated Complexity:** High (requires refactoring agent implementations)
**Breaking Changes:** Yes (changes agent interfaces)
**Dependencies:** BaseAgent refactoring (Priority 2.1)

---

### 3.5 Extract Common Metrics/Monitoring Pattern
**Issue:** Prometheus metrics defined ad-hoc across components

**Current Pattern:**
```python
# src/core/chunking_service.py
from prometheus_client import Counter, Gauge, Histogram

# Metrics defined per-file
chunking_duration_seconds = Histogram(...)
chunks_created_total = Counter(...)
avg_chunk_size_tokens = Gauge(...)
```

**Problem:** No centralized metric registry, hard to discover all metrics

**Proposed Solution:**
Create `src/monitoring/metrics.py`:

```python
from prometheus_client import Counter, Gauge, Histogram
from typing import Dict

class MetricsRegistry:
    """Centralized metrics registry for all components."""

    def __init__(self):
        self._metrics: Dict[str, Any] = {}

    def counter(self, name: str, description: str, labelnames: list[str] = []):
        """Create or get counter metric."""
        if name not in self._metrics:
            self._metrics[name] = Counter(name, description, labelnames=labelnames)
        return self._metrics[name]

    def histogram(self, name: str, description: str, labelnames: list[str] = [], buckets: list[float] = []):
        """Create or get histogram metric."""
        if name not in self._metrics:
            self._metrics[name] = Histogram(name, description, labelnames=labelnames, buckets=buckets)
        return self._metrics[name]

    def gauge(self, name: str, description: str, labelnames: list[str] = []):
        """Create or get gauge metric."""
        if name not in self._metrics:
            self._metrics[name] = Gauge(name, description, labelnames=labelnames)
        return self._metrics[name]

    def list_metrics(self) -> list[str]:
        """List all registered metrics."""
        return list(self._metrics.keys())

# Global registry
metrics = MetricsRegistry()

# Component-specific metrics
class ChunkingMetrics:
    duration = metrics.histogram(
        "chunking_duration_seconds",
        "Time spent chunking documents",
        labelnames=["strategy"],
        buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
    )
    chunks_created = metrics.counter(
        "chunks_created_total",
        "Total chunks created",
        labelnames=["strategy"],
    )
    avg_size = metrics.gauge(
        "avg_chunk_size_tokens",
        "Average chunk size in tokens",
        labelnames=["strategy"],
    )
```

**Benefits:**
- Centralized metric discovery
- Prevents duplicate metric names
- Easier to generate metrics documentation
- Type-safe metric access

**Estimated Complexity:** Medium
**Breaking Changes:** No (transparent migration)
**Dependencies:** None

---

## Priority 4: Low (Nice-to-Haves & Documentation)

### 4.1 Add Type Hints to Remaining Functions
**Issue:** Some functions lack complete type hints

**Example Findings:**
```python
# Incomplete type hints
def process_data(data):  # Missing types!
    return data.upper()

# Should be:
def process_data(data: str) -> str:
    return data.upper()
```

**Proposed Solution:**
1. Run `mypy` in strict mode to find missing type hints
2. Add type hints incrementally (low priority, do during feature work)
3. Set pre-commit hook to enforce type hints on new code

**Estimated Complexity:** Low (incremental)
**Breaking Changes:** No
**Dependencies:** None

---

### 4.2 Resolve TODO Comments
**Issue:** 30+ TODO comments scattered across codebase

**High-Priority TODOs:**

**TODO 1: Memory consolidation**
```python
# src/components/memory/consolidation.py:427
# TODO: Migrate unique items to Qdrant/Graphiti
```
**Action:** Document decision in ADR or implement in Sprint 22

**TODO 2: Monitoring stubs**
```python
# src/components/memory/monitoring.py:211-212
capacity = 0.0  # TODO: Get from Qdrant API
entries = 0  # TODO: Get collection size
```
**Action:** Implement Qdrant monitoring in Sprint 22

**TODO 3: Health check stubs**
```python
# src/api/health/memory_health.py:251-260
# TODO: Implement Qdrant health check when client is available
```
**Action:** Connect to actual Qdrant client in Sprint 22

**Proposed Solution:**
1. Categorize TODOs by priority (must-fix vs nice-to-have)
2. Create issues for high-priority TODOs
3. Remove outdated TODOs
4. Document deferred TODOs in BACKLOG.md

**Estimated Complexity:** Low (documentation task)
**Breaking Changes:** No
**Dependencies:** None

---

### 4.3 Add Docstrings to Public Functions
**Issue:** Some public functions lack docstrings

**Proposed Solution:**
1. Run `pydocstyle` to find missing docstrings
2. Add Google-style docstrings incrementally
3. Focus on public APIs first, then internal functions

**Template:**
```python
def function_name(param1: str, param2: int) -> bool:
    """One-line summary of function.

    Longer description if needed. Explain what the function does,
    not how it does it (implementation details go in code comments).

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When param1 is empty
        RuntimeError: When operation fails

    Example:
        >>> function_name("test", 42)
        True
    """
    ...
```

**Estimated Complexity:** Low (incremental)
**Breaking Changes:** No
**Dependencies:** None

---

### 4.4 Improve Configuration Documentation
**Issue:** `src/core/config.py` is 708 lines - great docs but could extract examples

**Proposed Solution:**
1. Keep config.py focused on Settings class
2. Extract examples to `docs/configuration/EXAMPLES.md`
3. Extract environment variable reference to `docs/configuration/ENV_VARS.md`
4. Add configuration validation guide

**Estimated Complexity:** Low (documentation refactoring)
**Breaking Changes:** No
**Dependencies:** None

---

### 4.5 Standardize Module __init__.py Patterns
**Issue:** Inconsistent `__init__.py` patterns across components

**Current Patterns:**

**Pattern 1: Empty `__init__.py`**
```python
# src/components/mcp/__init__.py
# (empty file)
```

**Pattern 2: Explicit exports**
```python
# src/components/vector_search/__init__.py
from .qdrant_client import QdrantClient
from .embeddings import EmbeddingService

__all__ = ["QdrantClient", "EmbeddingService"]
```

**Pattern 3: Star imports (avoid)**
```python
# Anti-pattern (do not use)
from .module import *
```

**Proposed Standard:**
```python
# src/components/<component>/__init__.py
"""Component name and brief description.

This module provides:
- Feature 1
- Feature 2
"""

# Explicit imports for public API
from .main_class import MainClass
from .helper import HelperClass

# Public API declaration
__all__ = [
    "MainClass",
    "HelperClass",
]
```

**Benefits:**
- Clear public API
- Better IDE autocomplete
- Prevents accidental exports

**Estimated Complexity:** Low
**Breaking Changes:** No
**Dependencies:** None

---

## Implementation Strategy

### Phase 1: Immediate (Sprint 22) - Priority 1
**Timeline:** 1 week
**Focus:** Remove deprecated code and security issues

**Tasks:**
1. Remove `unified_ingestion.py` (1.1)
2. Archive `three_phase_extractor.py` (1.2)
3. Plan LlamaIndex deprecation migration (1.3)

**Success Criteria:**
- Zero DEPRECATED warnings in codebase
- All tests passing after removals
- Migration guide documented

---

### Phase 2: Short-term (Sprint 22-23) - Priority 2
**Timeline:** 2-3 weeks
**Focus:** Eliminate duplication and inconsistencies

**Tasks:**
1. Consolidate base agent classes (2.1)
2. Plan embedding service migration (2.2)
3. Standardize client naming (2.3)
4. Create error handling patterns (2.4)
5. Audit chunking implementations (2.5)

**Success Criteria:**
- No duplicate base classes
- Consistent naming across all clients
- Error handling pattern documented and adopted in new code

---

### Phase 3: Medium-term (Sprint 24-25) - Priority 3
**Timeline:** 4-6 weeks
**Focus:** Architectural improvements and abstractions

**Tasks:**
1. Extract BaseClient (3.1)
2. Implement dependency injection for settings (3.2)
3. Standardize logging patterns (3.3)
4. Create BaseRetriever (3.4)
5. Centralize metrics registry (3.5)

**Success Criteria:**
- All clients inherit from BaseClient
- Settings injected via constructors
- Uniform logging across codebase
- BaseRetriever adopted by all retrieval agents

---

### Phase 4: Long-term (Sprint 26+) - Priority 4
**Timeline:** Ongoing
**Focus:** Documentation and code quality

**Tasks:**
1. Add missing type hints (4.1)
2. Resolve TODO comments (4.2)
3. Complete docstring coverage (4.3)
4. Improve configuration docs (4.4)
5. Standardize __init__.py patterns (4.5)

**Success Criteria:**
- 100% type hint coverage (mypy --strict passes)
- Zero outdated TODO comments
- All public functions documented
- Consistent module structure

---

## Risk Mitigation

### Risk 1: Breaking Changes
**Mitigation:**
- Maintain backward compatibility where possible
- Add deprecation warnings before removals
- Provide migration guides for breaking changes
- Test extensively before releasing

---

### Risk 2: Scope Creep
**Mitigation:**
- Strict prioritization (use 4-tier system)
- Each phase has clear deliverables
- Can pause between phases
- No Phase 2 until Phase 1 complete

---

### Risk 3: Test Coverage Gaps
**Mitigation:**
- Run full test suite after each refactoring
- Measure code coverage before/after
- Target >80% coverage for refactored components
- Add tests for extracted abstractions

---

## Success Metrics

**Quantitative:**
- Lines of code reduced by >10% (duplication removal)
- Code duplication <5% (measured by tool)
- Test coverage >80% for all refactored components
- Type hint coverage 100% (mypy --strict)
- Zero DEPRECATED warnings

**Qualitative:**
- Easier to onboard new developers
- Faster feature development (less boilerplate)
- Fewer production bugs (better error handling)
- Better code maintainability (consistent patterns)

---

## Open Questions

1. **UnifiedIngestionPipeline removal:** Are there any production scripts still using it?
2. **Three-phase extractor:** Any use cases for A/B testing vs pure LLM?
3. **LlamaIndex connectors:** Which connectors (if any) are needed for Sprint 22?
4. **Breaking change tolerance:** What's acceptable timeline for breaking changes?
5. **Test migration effort:** How much time allocated for test updates?

---

## References

**Internal Documentation:**
- ADR-026: Pure LLM Extraction Default
- ADR-028: LlamaIndex Deprecation Strategy
- ADR-022: Unified Chunking Service
- docs/NAMING_CONVENTIONS.md
- docs/CLAUDE.md

**Related Issues:**
- Sprint 21 Summary: `docs/sprints/SPRINT_21_SUMMARY.md`
- Sprint 22 Planning: TBD

---

**Author:** Backend Agent (Claude Code)
**Reviewers:** Klaus Pommer, Documentation Agent
**Last Updated:** 2025-11-11
**Status:** Draft - Awaiting Review
