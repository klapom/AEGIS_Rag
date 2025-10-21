# Sprint 11 Plan: Technical Debt Resolution & Integration Tests

**Sprint Goal:** Resolve critical technical debt and strengthen test coverage
**Duration:** 2 Wochen
**Story Points:** 32 SP
**Start Date:** 2025-10-21
**Branch:** `sprint-11-dev`

---

## Executive Summary

Sprint 11 fokussiert auf **technische Schuldenbeseitigung** und **Test-Qualität**. Anstatt neue Features zu bauen, konsolidieren wir die Architektur und beheben kritische TODOs aus vorherigen Sprints.

### Sprint 11 Priorities

1. **🔴 CRITICAL:** LLM-basierte Antwortgenerierung (TD-01)
2. **🔴 CRITICAL:** Redis LangGraph Checkpointer (TD-02)
3. **🟠 HIGH:** Gradio Dependency Resolution (TD-03)
4. **🟠 HIGH:** E2E Test Fixes (TD-07)
5. **🟡 MEDIUM:** Performance Improvements (TD-09, TD-15, TD-16)
6. **🟡 MEDIUM:** Enhanced Visualization (TD-17, TD-22)
7. **✅ NEW:** Integration Tests für Sprint 10 Features

---

## Features Overview

| ID | Feature | SP | Priority | Status |
|----|---------|----|---------| -------|
| 11.1 | LLM-Based Answer Generation | 5 | 🔴 CRITICAL | 📋 TODO |
| 11.2 | Redis LangGraph Checkpointer | 3 | 🔴 CRITICAL | 📋 TODO |
| 11.3 | Dependency Resolution | 2 | 🟠 HIGH | 📋 TODO |
| 11.4 | E2E Test Fixes | 3 | 🟠 HIGH | 📋 TODO |
| 11.5 | Community Detection Performance | 3 | 🟡 MEDIUM | 📋 TODO |
| 11.6 | LLM Labeling Optimization | 2 | 🟡 MEDIUM | 📋 TODO |
| 11.7 | Temporal Retention Policy | 2 | 🟡 MEDIUM | 📋 TODO |
| 11.8 | Enhanced Graph Visualization | 3 | 🟡 MEDIUM | 📋 TODO |
| 11.9 | Health Check Enhancements | 1 | 🟡 MEDIUM | 📋 TODO |
| 11.10 | Sprint 10 Integration Tests | 8 | 🟠 HIGH | 📋 TODO |
| **TOTAL** | | **32** | | |

---

## Feature 11.1: LLM-Based Answer Generation (5 SP)

**Technical Debt:** TD-01
**Priority:** 🔴 CRITICAL
**Files:** `src/agents/graph.py`, `src/prompts/answer_prompts.py` (new)

### Current Problem

```python
# src/agents/graph.py:57-94
async def simple_answer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Sprint 10 Quick Fix: This is a placeholder answer generator.
    TODO: Replace with proper LLM-based generation in future sprint.
    """
    # Just concatenates context - NO actual answering!
    context_text = "\n\n".join([ctx.get("text", "") for ctx in contexts[:3]])
    answer = f"Based on the retrieved documents:\n\n{context_text}"
```

**Impact:**
- ❌ No synthesis or reasoning
- ❌ Just returns raw context
- ❌ Poor user experience

### Solution Architecture

#### 1. Create Answer Generation Prompts

**File:** `src/prompts/answer_prompts.py`

```python
"""Answer generation prompts for RAG system."""

ANSWER_GENERATION_PROMPT = """You are a helpful AI assistant answering questions based on retrieved context.

**Context Information:**
{context}

**User Question:**
{query}

**Instructions:**
1. Analyze the provided context carefully
2. Answer the question directly and concisely
3. Use ONLY information from the context
4. If context doesn't contain the answer, say "I don't have enough information"
5. Cite sources when possible using [Source: filename]

**Answer:**"""

MULTI_HOP_REASONING_PROMPT = """You are an AI assistant that combines information from multiple sources.

**Retrieved Documents:**
{contexts}

**Question:**
{query}

**Task:**
Connect information across documents to answer the multi-hop question.
Show your reasoning step-by-step.

**Answer:**"""
```

#### 2. Implement LLM Answer Generator

**File:** `src/agents/answer_generator.py` (new)

```python
"""LLM-based answer generation for RAG."""

import structlog
from typing import Any

from src.core.config import settings
from src.prompts.answer_prompts import (
    ANSWER_GENERATION_PROMPT,
    MULTI_HOP_REASONING_PROMPT,
)

logger = structlog.get_logger(__name__)


class AnswerGenerator:
    """Generate answers using LLM with retrieved context."""

    def __init__(self, model_name: str | None = None, temperature: float = 0.0):
        """Initialize answer generator.

        Args:
            model_name: Ollama model name (default: from settings)
            temperature: LLM temperature for answer generation
        """
        from langchain_ollama import ChatOllama

        self.model_name = model_name or settings.router_model
        self.temperature = temperature
        self.llm = ChatOllama(
            model=self.model_name,
            temperature=self.temperature,
            base_url=settings.ollama_base_url,
        )

        logger.info(
            "answer_generator_initialized",
            model=self.model_name,
            temperature=self.temperature,
        )

    async def generate_answer(
        self,
        query: str,
        contexts: list[dict[str, Any]],
        mode: str = "simple",
    ) -> str:
        """Generate answer from query and retrieved contexts.

        Args:
            query: User question
            contexts: Retrieved document contexts
            mode: "simple" or "multi_hop"

        Returns:
            Generated answer string
        """
        if not contexts:
            return self._no_context_answer(query)

        # Format contexts
        context_text = self._format_contexts(contexts)

        # Select prompt based on mode
        if mode == "multi_hop":
            prompt = MULTI_HOP_REASONING_PROMPT.format(
                contexts=context_text, query=query
            )
        else:
            prompt = ANSWER_GENERATION_PROMPT.format(context=context_text, query=query)

        # Generate answer
        logger.debug("generating_answer", query=query[:100], contexts_count=len(contexts))

        try:
            response = await self.llm.ainvoke(prompt)
            answer = response.content.strip()

            logger.info(
                "answer_generated",
                query=query[:100],
                answer_length=len(answer),
                contexts_used=len(contexts),
            )

            return answer

        except Exception as e:
            logger.error("answer_generation_failed", error=str(e), query=query[:100])
            return self._error_answer(query, str(e))

    def _format_contexts(self, contexts: list[dict[str, Any]]) -> str:
        """Format contexts for prompt."""
        formatted = []
        for i, ctx in enumerate(contexts[:5], 1):  # Top 5 contexts
            text = ctx.get("text", "")
            source = ctx.get("source", "Unknown")
            score = ctx.get("score", 0.0)

            formatted.append(
                f"**Document {i}** [Source: {source}, Relevance: {score:.2f}]\n{text}"
            )

        return "\n\n---\n\n".join(formatted)

    def _no_context_answer(self, query: str) -> str:
        """Return answer when no context is available."""
        return (
            f"I don't have enough information to answer '{query}'. "
            "Please make sure relevant documents are indexed in the system."
        )

    def _error_answer(self, query: str, error: str) -> str:
        """Return answer when generation fails."""
        return (
            f"I encountered an error while generating an answer for '{query}': {error}. "
            "Please try again or rephrase your question."
        )


# Singleton instance
_generator: AnswerGenerator | None = None


def get_answer_generator() -> AnswerGenerator:
    """Get singleton AnswerGenerator instance."""
    global _generator
    if _generator is None:
        _generator = AnswerGenerator()
    return _generator
```

#### 3. Replace simple_answer_node

**File:** `src/agents/graph.py`

```python
# BEFORE (Sprint 10 Quick Fix):
async def simple_answer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Sprint 10 Quick Fix: This is a placeholder answer generator."""
    context_text = "\n\n".join([ctx.get("text", "") for ctx in contexts[:3]])
    answer = f"Based on the retrieved documents:\n\n{context_text}"
    # ...

# AFTER (Sprint 11 Fix):
async def llm_answer_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generate LLM-based answer from retrieved contexts.

    Sprint 11: Replaced placeholder with proper LLM-based generation.
    """
    from src.agents.answer_generator import get_answer_generator

    query = state.get("query", "")
    contexts = state.get("retrieved_contexts", [])

    # Get answer generator
    generator = get_answer_generator()

    # Generate answer
    answer = await generator.generate_answer(query, contexts, mode="simple")

    # Update state
    if "messages" not in state:
        state["messages"] = []

    state["messages"].append({"role": "assistant", "content": answer})
    state["answer"] = answer

    logger.info("llm_answer_generated", answer_length=len(answer), contexts_used=len(contexts))

    return state
```

#### 4. Update Graph Compilation

```python
# Update node name in graph
graph.add_node("answer", llm_answer_node)  # was: simple_answer_node
```

### Testing Strategy

#### Unit Tests (`tests/unit/agents/test_answer_generator.py`)

```python
import pytest
from src.agents.answer_generator import AnswerGenerator


@pytest.mark.asyncio
async def test_generate_answer_with_context():
    """Test answer generation with valid context."""
    generator = AnswerGenerator(temperature=0.0)

    contexts = [
        {
            "text": "Python was created by Guido van Rossum in 1991.",
            "source": "python_history.md",
            "score": 0.95,
        }
    ]

    answer = await generator.generate_answer("Who created Python?", contexts)

    assert answer
    assert "Guido van Rossum" in answer
    assert len(answer) > 10


@pytest.mark.asyncio
async def test_generate_answer_no_context():
    """Test answer generation with no context."""
    generator = AnswerGenerator()

    answer = await generator.generate_answer("Who created Python?", [])

    assert "don't have enough information" in answer.lower()


@pytest.mark.asyncio
async def test_multi_hop_reasoning():
    """Test multi-hop answer generation."""
    generator = AnswerGenerator(temperature=0.0)

    contexts = [
        {"text": "Python was created by Guido van Rossum.", "source": "doc1.md", "score": 0.9},
        {"text": "Guido van Rossum worked at Google.", "source": "doc2.md", "score": 0.85},
    ]

    answer = await generator.generate_answer(
        "Where did the creator of Python work?",
        contexts,
        mode="multi_hop",
    )

    assert answer
    assert "Google" in answer or "Guido" in answer
```

#### Integration Tests (`tests/integration/test_llm_answer_flow.py`)

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_answer_generation(coordinator: CoordinatorAgent):
    """Test full flow: query → retrieval → LLM answer."""
    result = await coordinator.process_query(
        query="What is AEGIS RAG?",
        session_id="test-session",
    )

    assert result["answer"]
    assert len(result["answer"]) > 50  # Real answer, not placeholder
    assert "Based on the retrieved documents:" not in result["answer"]  # Not placeholder format
    assert result["retrieved_contexts"]
```

### Success Criteria

- ✅ All unit tests passing (8+ tests)
- ✅ Integration tests passing
- ✅ Manual testing shows proper answers (not raw context)
- ✅ No "Based on the retrieved documents:" prefix
- ✅ Answers synthesize information from multiple sources
- ✅ Performance: < 3s for answer generation

### Effort Estimate

- **Prompt Engineering:** 0.5 SP
- **AnswerGenerator Implementation:** 2 SP
- **Graph Integration:** 0.5 SP
- **Unit Tests:** 1 SP
- **Integration Tests:** 1 SP

**Total:** 5 SP

---

## Feature 11.2: Redis LangGraph Checkpointer (3 SP)

**Technical Debt:** TD-02
**Priority:** 🔴 CRITICAL
**Files:** `src/agents/checkpointer.py`

### Current Problem

```python
# src/agents/checkpointer.py:146-165
# TODO Sprint 7: Redis Checkpointer
# def create_redis_checkpointer() -> BaseCheckpointSaver:
#     ...commented out since Sprint 7...
```

**Impact:**
- ❌ State lost on backend restart
- ❌ Cannot scale horizontally
- ❌ Only MemorySaver (RAM-based) available

### Solution

#### 1. Uncomment and Update Redis Checkpointer

```python
def create_redis_checkpointer() -> BaseCheckpointSaver:
    """Create Redis-based checkpointer for production.

    Returns:
        Redis checkpointer instance

    Raises:
        ConnectionError: If Redis is unavailable
    """
    from langgraph.checkpoint.redis import RedisCheckpointSaver
    import redis

    try:
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password.get_secret_value() if settings.redis_password else None,
            db=settings.redis_db,
            decode_responses=False,  # LangGraph needs bytes
        )

        # Test connection
        redis_client.ping()

        checkpointer = RedisCheckpointSaver(redis_client)

        logger.info(
            "redis_checkpointer_created",
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
        )

        return checkpointer

    except redis.ConnectionError as e:
        logger.error("redis_connection_failed", error=str(e))
        raise ConnectionError(f"Failed to connect to Redis: {e}")


def create_checkpointer() -> BaseCheckpointSaver:
    """Create appropriate checkpointer based on environment.

    Returns:
        Redis checkpointer for production, Memory for dev/testing
    """
    # Use Redis in production/staging, Memory for dev
    if settings.environment in ["production", "staging"]:
        try:
            return create_redis_checkpointer()
        except ConnectionError as e:
            logger.warning(
                "redis_unavailable_fallback_to_memory",
                error=str(e),
                environment=settings.environment,
            )
            # Fallback to memory if Redis unavailable
            return MemorySaver()
    else:
        # Development: use memory
        logger.info("using_memory_checkpointer", environment=settings.environment)
        return MemorySaver()
```

#### 2. Add Configuration

```python
# src/core/config.py - Add Redis DB configuration
class Settings(BaseSettings):
    # ... existing Redis settings ...

    redis_db: int = Field(
        default=1,  # Use DB 1 for LangGraph (DB 0 for cache)
        description="Redis database number for LangGraph checkpoints"
    )

    environment: str = Field(
        default="development",
        description="Environment: development, staging, production"
    )
```

#### 3. Update docker-compose.yml

Ensure Redis persistence:

```yaml
services:
  redis:
    # ... existing config ...
    command: redis-server --appendonly yes --appendfsync everysec
    volumes:
      - redis_data:/data  # Persist Redis data

volumes:
  redis_data:  # Add volume for Redis
```

### Testing

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_checkpointer_persistence(redis_client):
    """Test that checkpoints persist in Redis."""
    checkpointer = create_redis_checkpointer()

    # Create checkpoint
    state = {"query": "test", "answer": "test answer"}
    checkpoint_id = str(uuid.uuid4())

    await checkpointer.aput(checkpoint_id, state)

    # Retrieve checkpoint
    retrieved = await checkpointer.aget(checkpoint_id)

    assert retrieved == state


@pytest.mark.integration
def test_checkpointer_fallback():
    """Test fallback to Memory when Redis unavailable."""
    # Mock Redis connection failure
    with patch("redis.Redis.ping", side_effect=redis.ConnectionError):
        checkpointer = create_checkpointer()

        # Should fallback to MemorySaver
        assert isinstance(checkpointer, MemorySaver)
```

### Success Criteria

- ✅ Redis checkpointer works in production mode
- ✅ State persists across backend restarts
- ✅ Graceful fallback to Memory when Redis unavailable
- ✅ All existing tests still pass
- ✅ No performance degradation

### Effort: 3 SP

---

## Feature 11.3: Dependency Resolution (2 SP)

**Technical Debt:** TD-03
**Priority:** 🟠 HIGH
**Files:** `pyproject.toml`

### Current Problem

Already partially resolved in Sprint 10 (ruff upgraded to ^0.14.0), but Gradio still requires manual installation.

### Solution

**Option A:** Verify ruff upgrade resolves conflict
```bash
poetry add gradio
# Test if it works now with ruff 0.14.0
```

**Option B:** If still conflicts, add as optional dependency
```toml
[tool.poetry.group.ui.dependencies]
gradio = "^5.49.0"

# Install with:
# poetry install --with ui
```

### Success Criteria

- ✅ `poetry add gradio` works without conflicts
- ✅ `poetry lock` succeeds
- ✅ Gradio in poetry.lock
- ✅ No manual pip install needed

### Effort: 2 SP

---

## Feature 11.4: E2E Test Fixes (3 SP)

**Technical Debt:** TD-07
**Priority:** 🟠 HIGH
**Files:** `tests/e2e/*.py`

### Current Problem

E2E tests use outdated API signatures from Sprint 8. All tests skipped/failing.

### Solution

1. **Audit E2E test files** - identify API mismatches
2. **Update API calls** to match current FastAPI endpoints
3. **Re-enable tests** - remove skip markers
4. **Add to CI** - ensure E2E tests run in pipeline

### Testing Files to Fix

- `tests/e2e/test_e2e_full_rag_workflow.py`
- `tests/e2e/test_e2e_graph_rag.py`
- `tests/e2e/test_e2e_memory.py`
- `tests/e2e/test_e2e_mcp.py`

### Success Criteria

- ✅ All E2E tests updated and passing
- ✅ E2E tests run in CI/CD
- ✅ Coverage report includes E2E results

### Effort: 3 SP

---

## Feature 11.5: Community Detection Performance (3 SP)

**Technical Debt:** TD-09
**Priority:** 🟡 MEDIUM
**Files:** `src/components/graph_rag/community_detection.py`

### Current Problem

Community detection takes 30s for 1000 nodes (target: 5s). NetworkX fallback is slow.

### Solution

1. **Document GDS requirement** for production
2. **Add progress callbacks** for long operations
3. **Optimize NetworkX** implementation

```python
async def detect_communities_with_progress(
    graph,
    progress_callback=None,
) -> dict:
    """Detect communities with progress updates."""
    if progress_callback:
        await progress_callback(0.0, "Initializing...")

    # Try GDS first
    if gds_available:
        result = await _detect_with_gds(graph, progress_callback)
    else:
        result = await _detect_with_networkx_optimized(graph, progress_callback)

    if progress_callback:
        await progress_callback(1.0, "Complete")

    return result
```

### Success Criteria

- ✅ GDS usage documented
- ✅ Progress callbacks implemented
- ✅ NetworkX optimized (20s target)
- ✅ Performance tests added

### Effort: 3 SP

---

## Feature 11.6: LLM Labeling Optimization (2 SP)

**Technical Debt:** TD-15
**Priority:** 🟡 MEDIUM

### Solution

Batch multiple communities in single prompt:

```python
async def label_communities_batch(communities: list, batch_size: int = 5):
    """Label communities in batches for performance."""
    batches = [communities[i:i+batch_size] for i in range(0, len(communities), batch_size)]

    prompt = """Label the following communities:

    {community_descriptions}

    Return labels as JSON array."""

    # Single LLM call for batch
    response = await llm.ainvoke(prompt)
```

### Effort: 2 SP

---

## Feature 11.7: Temporal Retention Policy (2 SP)

**Technical Debt:** TD-16
**Priority:** 🟡 MEDIUM
**Solution:** Add retention policy config

```python
# src/core/config.py
class Settings(BaseSettings):
    # Temporal Retention (Sprint 11 - TD-16)
    temporal_retention_days: int = Field(
        default=365,
        description="Days to retain temporal versions (0 = infinite)"
    )

    temporal_auto_purge: bool = Field(
        default=True,
        description="Automatically purge old temporal versions"
    )

    temporal_purge_schedule: str = Field(
        default="0 2 * * *",  # 2 AM daily
        description="Cron schedule for temporal purge"
    )
```

### Purge Implementation

```python
# src/components/memory/temporal_purge.py
async def purge_old_versions(retention_days: int):
    """Delete temporal versions older than retention period."""
    cutoff_date = datetime.now() - timedelta(days=retention_days)

    query = """
    MATCH (n)
    WHERE n.valid_to < $cutoff
    DELETE n
    RETURN count(n) as purged_count
    """

    result = await neo4j.execute(query, {"cutoff": cutoff_date})
    return result["purged_count"]
```

### Effort: 2 SP

---

## Feature 11.8: Enhanced Graph Visualization (3 SP)

**Technical Debt:** TD-17, TD-22
**Priority:** 🟡 MEDIUM

### TD-17: Increase Node Limit with Pagination

```python
@router.get("/graph/visualize")
async def visualize_graph(
    limit: int = 100,
    offset: int = 0,
    filter_by: str | None = None,
):
    """Get graph visualization with pagination."""
    # Paginated query
    nodes = await get_nodes(limit=limit, offset=offset, filter=filter_by)
    return {"nodes": nodes, "has_more": len(nodes) == limit}
```

### TD-22: GDS Detection in Health Check

```python
# src/api/v1/health.py
@router.get("/health")
async def health_check():
    """Health check with GDS detection."""
    neo4j_health = await check_neo4j()

    # Detect GDS
    gds_available, gds_version = await detect_gds()

    return {
        "neo4j": {
            "status": "healthy",
            "gds_available": gds_available,
            "gds_version": gds_version if gds_available else None,
        }
    }
```

### Effort: 3 SP

---

## Feature 11.9: Health Check Enhancements (1 SP)

**Technical Debt:** TD-22
**Priority:** 🟡 MEDIUM
**Effort:** 1 SP (included in 11.8)

---

## Feature 11.10: Sprint 10 Integration Tests (8 SP)

**Priority:** 🟠 HIGH
**Files:** `tests/integration/test_sprint10_features.py`

### Test Coverage

#### Chat API Integration Tests (2 SP)

```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestChatAPIIntegration:
    """Integration tests for Sprint 10 Chat API."""

    async def test_chat_with_session_persistence(self, client):
        """Test chat session persistence across requests."""
        session_id = str(uuid.uuid4())

        # First message
        response1 = await client.post(
            "/api/v1/chat/",
            json={"query": "What is Python?", "session_id": session_id},
        )
        assert response1.status_code == 200

        # Second message (same session)
        response2 = await client.post(
            "/api/v1/chat/",
            json={"query": "Who created it?", "session_id": session_id},
        )
        assert response2.status_code == 200

        # Retrieve history
        history = await client.get(f"/api/v1/chat/history/{session_id}")
        assert len(history.json()["messages"]) >= 4  # 2 user + 2 assistant

    async def test_chat_with_sources(self, client):
        """Test source citation extraction."""
        response = await client.post(
            "/api/v1/chat/",
            json={"query": "What is AEGIS RAG?", "include_sources": True},
        )

        data = response.json()
        assert data["sources"]
        assert len(data["sources"]) > 0
        assert data["sources"][0]["text"]
        assert data["sources"][0]["score"] > 0

    async def test_chat_with_tool_calls(self, client):
        """Test MCP tool call visibility."""
        response = await client.post(
            "/api/v1/chat/",
            json={
                "query": "What is AEGIS RAG?",
                "include_tool_calls": True,
            },
        )

        data = response.json()
        assert "tool_calls" in data
        # Tool calls may be empty if no MCP tools invoked
```

#### Document Upload Integration Tests (2 SP)

```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestDocumentUploadIntegration:
    """Integration tests for document upload."""

    async def test_single_file_upload(self, client, temp_file):
        """Test single file upload and indexing."""
        files = {"file": ("test.txt", temp_file, "text/plain")}

        response = await client.post("/api/v1/retrieval/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["chunks_created"] > 0
        assert data["embeddings_generated"] > 0

    async def test_multi_file_upload(self, client, temp_files):
        """Test multiple file upload (UI feature)."""
        for temp_file in temp_files:
            files = {"file": (temp_file.name, temp_file, "text/plain")}
            response = await client.post("/api/v1/retrieval/upload", files=files)
            assert response.status_code == 200

    async def test_upload_and_query(self, client, temp_file):
        """Test full flow: upload → index → query."""
        # Upload
        files = {"file": ("python_doc.txt", temp_file, "text/plain")}
        upload_response = await client.post("/api/v1/retrieval/upload", files=files)
        assert upload_response.status_code == 200

        # Wait for BM25 update
        await asyncio.sleep(2)

        # Query
        chat_response = await client.post(
            "/api/v1/chat/",
            json={"query": "content from python_doc.txt"},
        )

        assert chat_response.status_code == 200
        assert chat_response.json()["answer"]
```

#### BM25 Persistence Integration Tests (1 SP)

```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestBM25PersistenceIntegration:
    """Integration tests for BM25 disk persistence."""

    async def test_bm25_save_and_load(self, hybrid_search):
        """Test BM25 index persistence across restarts."""
        # Fit BM25
        docs = [{"text": "Python programming language"}]
        await hybrid_search.prepare_bm25_index()

        # Save
        hybrid_search.bm25_search.save_to_disk()

        # Create new instance (simulates restart)
        new_hybrid_search = HybridSearch()

        # Load from disk
        loaded = new_hybrid_search.bm25_search.load_from_disk()
        assert loaded
        assert new_hybrid_search.bm25_search.is_fitted()

    async def test_bm25_cache_file_exists(self):
        """Test BM25 cache file creation."""
        cache_file = Path("data/cache/bm25_index.pkl")
        assert cache_file.exists()
        assert cache_file.stat().st_size > 0
```

#### MCP Integration Tests (2 SP)

```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestMCPIntegration:
    """Integration tests for MCP features."""

    async def test_mcp_server_connection(self, mcp_client):
        """Test connecting to MCP server."""
        server = MCPServer(
            name="test-server",
            transport=TransportType.STDIO,
            endpoint="echo test",
        )

        success = await mcp_client.connect(server)
        assert success

    async def test_mcp_tool_discovery(self, mcp_client, connected_server):
        """Test tool discovery from connected server."""
        tools = await mcp_client.list_tools()
        assert len(tools) > 0
        assert tools[0].name
        assert tools[0].description

    async def test_mcp_gradio_integration(self, gradio_app):
        """Test MCP integration in Gradio UI."""
        status, tools_df = await gradio_app.connect_mcp_server(
            name="test", transport="STDIO", endpoint="test command"
        )

        assert status["status"] == "connected"
        assert len(tools_df) > 0
```

#### Markdown Rendering Integration Test (1 SP)

```python
@pytest.mark.integration
def test_gradio_markdown_rendering():
    """Test markdown rendering in Gradio UI."""
    from src.ui.gradio_app import GradioApp

    app = GradioApp()

    # Test formatting
    answer = "Test answer"
    sources = [{"title": "doc.md", "score": 0.9}]
    tool_calls = [
        {
            "tool_name": "test_tool",
            "server": "test-server",
            "duration_ms": 10.0,
            "success": True,
        }
    ]

    formatted = app._format_answer_with_sources_and_tools(answer, sources, tool_calls)

    # Check markdown elements
    assert "**🔧 MCP Tool Calls:**" in formatted
    assert "**📚 Quellen:**" in formatted
    assert "✅" in formatted  # Success icon
```

### Total Integration Tests: 8 SP

- Chat API: 2 SP
- Document Upload: 2 SP
- BM25 Persistence: 1 SP
- MCP Integration: 2 SP
- Markdown Rendering: 1 SP

---

## Sprint 11 Timeline

### Week 1: Critical Fixes (10 SP)

**Days 1-2:**
- Feature 11.1: LLM Answer Generation (5 SP)

**Days 3-4:**
- Feature 11.2: Redis Checkpointer (3 SP)
- Feature 11.3: Dependency Resolution (2 SP)

### Week 2: Testing & Optimization (22 SP)

**Days 1-3:**
- Feature 11.10: Sprint 10 Integration Tests (8 SP)
- Feature 11.4: E2E Test Fixes (3 SP)

**Days 4-5:**
- Feature 11.5: Community Detection (3 SP)
- Feature 11.6: LLM Labeling (2 SP)
- Feature 11.7: Retention Policy (2 SP)
- Feature 11.8: Enhanced Visualization (3 SP)
- Feature 11.9: Health Checks (1 SP)

---

## Success Metrics

### Technical Debt Resolution

- ✅ 2 CRITICAL items resolved (TD-01, TD-02)
- ✅ 2 HIGH priority items resolved (TD-03, TD-07)
- ✅ 6 MEDIUM priority items resolved (TD-09, TD-15, TD-16, TD-17, TD-22)

### Test Coverage

- ✅ 8+ integration tests for Sprint 10 features
- ✅ All E2E tests passing
- ✅ Overall coverage maintained > 80%

### Quality Metrics

- ✅ No new critical bugs introduced
- ✅ Performance maintained or improved
- ✅ All CI/CD pipelines green
- ✅ Technical debt reduced by 40%

---

## Risk Management

### Risks

1. **Redis Migration** - Potential data loss if not tested properly
   - **Mitigation:** Thorough testing in staging before production

2. **LLM Answer Quality** - Generated answers may be inconsistent
   - **Mitigation:** Temperature=0.0, extensive prompt engineering, human review

3. **Performance Regression** - Optimizations may have edge cases
   - **Mitigation:** Performance benchmarks before/after

### Contingencies

- If Redis migration issues → Keep MemorySaver as fallback
- If LLM answers poor quality → Keep simple_answer_node as fallback option
- If timeline slips → Deprioritize low-priority items (TD-17, TD-22)

---

## Post-Sprint 11

### Resolved Technical Debt

- TD-01 ✅ LLM Answer Generation
- TD-02 ✅ Redis Checkpointer
- TD-03 ✅ Dependency Resolution
- TD-07 ✅ E2E Tests
- TD-09 ✅ Community Detection
- TD-15 ✅ LLM Labeling
- TD-16 ✅ Retention Policy
- TD-17 ✅ Visualization Limits
- TD-22 ✅ Health Check

### Remaining Technical Debt (for Sprint 12+)

- TD-05: Real-Time Streaming (requires React migration)
- TD-06: Authentication (requires React migration)
- TD-08: UI Customization (requires React migration)
- TD-10: Neo4j Test Timeout
- TD-11: Cache Pattern Matching
- TD-12: Timestamp Precision
- TD-13: NetworkX Variance
- TD-14: LightRAG Limitation (documented)
- TD-18: Performance Test Placeholders
- TD-19: Integration Test Placeholders
- TD-20: Graph Export
- TD-21: AST Parsing

### Sprint 12 Candidates

**Option A: React Migration (30 SP)**
- Resolves TD-05, TD-06, TD-08
- New frontend with streaming, auth, full customization

**Option B: Performance Sprint (25 SP)**
- Focus on TD-10, TD-11, TD-18
- Benchmarking, optimization, load testing

**Option C: Advanced Features (28 SP)**
- Graph export, AST parsing, enhanced analytics

---

**Sprint 11 Start:** 2025-10-21
**Sprint 11 End:** 2025-11-04 (2 weeks)
**Next Review:** 2025-11-04
