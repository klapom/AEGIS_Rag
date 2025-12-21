# Code Conventions & Standards

**Project:** AEGIS RAG (Agentic Enterprise Graph Intelligence System)
**Last Updated:** 2025-12-21 (Sprint 60 - Documentation Consolidation)

---

## Python Naming Conventions

### Files & Modules
```python
# Snake case for modules and files
vector_search.py
graph_query_agent.py
reciprocal_rank_fusion.py

# Avoid abbreviations unless industry standard
✅ embedding_model.py
❌ emb_mdl.py

# Test files mirror source structure
src/agents/coordinator.py → tests/unit/agents/test_coordinator.py
```

### Classes
```python
# PascalCase for classes
class VectorSearchAgent:
    pass

class QdrantClient:
    pass

class RetrievalResult:
    pass

# Suffix patterns
*Agent      # For LangGraph agents
*Client     # For database/API clients
*Config     # For configuration classes
*Exception  # For custom exceptions
*Service    # For business logic services
*Repository # For data access layers
```

### Functions & Methods
```python
# Snake case for functions
def search_documents(query: str) -> List[Document]:
    pass

def calculate_reciprocal_rank_fusion(results: List[List[Document]]) -> List[Document]:
    pass

# Verb prefixes indicate action
get_*      # Retrieve data (idempotent)
fetch_*    # Retrieve from external source
create_*   # Create new resource
update_*   # Modify existing resource
delete_*   # Remove resource
build_*    # Construct complex object
validate_* # Check constraints
parse_*    # Transform format
```

### Variables & Constants
```python
# Snake case for variables
user_query = "What is RAG?"
retrieved_documents = []
similarity_score = 0.95

# SCREAMING_SNAKE_CASE for constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT_SECONDS = 30
EMBEDDING_DIMENSION = 1024
REDIS_MEMORY_TTL = 3600

# Type hints always
def process_query(query: str, max_results: int = 10) -> QueryResult:
    pass
```

### Private Members
```python
class Agent:
    def __init__(self):
        self._internal_state = {}  # Protected (convention)
        self.__private_data = []   # Name mangling (rare)

    def public_method(self):
        pass

    def _internal_helper(self):
        pass
```

---

## Directory & File Structure

### Domain-Driven Design Structure (Post-Sprint 53-59 Refactoring)

```
src/
├── agents/                     # LangGraph Multi-Agent System
│   ├── coordinator.py          # Main orchestrator
│   ├── vector_search.py        # Qdrant hybrid search
│   ├── graph_query.py          # Neo4j + LightRAG
│   ├── memory.py               # Graphiti memory
│   ├── action.py               # Tool execution
│   └── research/               # Agentic research agent (Sprint 59)
│
├── domains/                    # Domain-Driven Design Structure
│   ├── document_processing/    # Ingestion domain
│   │   ├── chunking/           # Section-aware chunking
│   │   ├── embedding/          # BGE-M3 embeddings
│   │   └── storage/            # Qdrant/Neo4j storage
│   │
│   ├── knowledge_graph/        # Graph domain
│   │   ├── entities/           # Entity management
│   │   ├── relationships/      # Relationship extraction
│   │   └── community/          # Community detection
│   │
│   ├── vector_search/          # Vector search domain
│   │   ├── hybrid/             # Hybrid search (Vector + BM25)
│   │   └── reranking/          # Result reranking
│   │
│   ├── memory/                 # Memory domain
│   │   ├── redis/              # Short-term memory
│   │   ├── qdrant/             # Semantic memory
│   │   └── graphiti/           # Episodic memory
│   │
│   └── llm_integration/        # LLM domain
│       ├── proxy/              # AegisLLMProxy
│       ├── tools/              # Tool framework (Sprint 59)
│       │   ├── registry.py     # Tool registration
│       │   ├── executor.py     # Tool execution
│       │   └── builtin/        # Bash/Python tools
│       └── sandbox/            # Docker sandboxing (Sprint 59)
│
├── api/                        # FastAPI endpoints
│   └── v1/                     # API v1
│       ├── chat.py             # Chat/Query endpoint
│       ├── admin.py            # Admin endpoints
│       └── memory.py           # Memory access
│
└── core/                       # Core infrastructure
    ├── config/                 # Configuration
    ├── logging/                # Structured logging
    └── exceptions/             # Custom exceptions
```

### Test File Naming
```
tests/
├── unit/
│   ├── agents/
│   │   ├── test_coordinator.py
│   │   └── test_vector_search_agent.py
│   ├── domains/
│   │   ├── test_hybrid_search.py
│   │   └── test_reranker.py
│   └── utils/
│       └── test_text_splitter.py
├── integration/
│   ├── test_vector_graph_fusion.py
│   ├── test_memory_consolidation.py
│   └── test_agent_orchestration.py
└── e2e/
    ├── test_query_flow.py
    └── test_multi_turn_conversation.py
```

---

## Code Standards

### Imports Organization
```python
# Standard library
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime

# Third-party packages
import numpy as np
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

# LangChain ecosystem
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, MessagesState

# Local imports (relative)
from ..core.config import settings
from ..core.exceptions import RetrievalError
from .base import BaseAgent
```

### Type Hints Best Practices
```python
from typing import List, Dict, Optional, Union, Literal, TypeVar, Generic

# Always use type hints
def search(
    query: str,
    top_k: int = 10,
    filters: Optional[Dict[str, Any]] = None
) -> List[Document]:
    pass

# Use Pydantic for complex types
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=10, ge=1, le=100)
    filters: Optional[Dict[str, str]] = None
    mode: Literal["vector", "hybrid", "graph"] = "hybrid"

# Use TypeVar for generics
T = TypeVar('T')
def first_or_none(items: List[T]) -> Optional[T]:
    return items[0] if items else None
```

### Docstrings
```python
def reciprocal_rank_fusion(
    result_lists: List[List[Document]],
    k: int = 60,
    weights: Optional[List[float]] = None
) -> List[Document]:
    """
    Combine multiple ranked document lists using Reciprocal Rank Fusion.

    RRF assigns a score to each document based on its rank in each list,
    with the formula: score = sum(1 / (k + rank_i)) for all lists.

    Args:
        result_lists: List of ranked document lists to combine.
        k: Constant for RRF formula (default 60, from original paper).
        weights: Optional weights for each list (must sum to 1.0).

    Returns:
        Fused list of documents sorted by combined RRF score.

    Raises:
        ValueError: If result_lists is empty or weights don't sum to 1.0.

    Example:
        >>> vector_results = [doc1, doc2, doc3]
        >>> bm25_results = [doc2, doc1, doc4]
        >>> fused = reciprocal_rank_fusion([vector_results, bm25_results])
        >>> assert fused[0] in [doc1, doc2]  # Top-ranked in both
    """
    pass
```

### Error Handling
```python
# Custom exceptions
class AegisRAGException(Exception):
    """Base exception for all AegisRAG errors."""
    pass

class RetrievalError(AegisRAGException):
    """Raised when document retrieval fails."""
    pass

class GraphQueryError(AegisRAGException):
    """Raised when Neo4j query execution fails."""
    pass

# Use specific exceptions
try:
    results = await qdrant_client.search(query)
except QdrantException as e:
    logger.error(f"Qdrant search failed: {e}")
    raise RetrievalError(f"Vector search failed: {str(e)}") from e

# Async context managers
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

### Logging
```python
import structlog

logger = structlog.get_logger(__name__)

# Structured logging with context
logger.info(
    "hybrid_search_completed",
    query=query,
    vector_results=len(vector_results),
    bm25_results=len(bm25_results),
    fused_results=len(fused_results),
    latency_ms=elapsed_ms
)

# Log levels
logger.debug("Detailed information for debugging")
logger.info("General informational messages")
logger.warning("Warning messages for potential issues")
logger.error("Error messages", exc_info=True)
logger.critical("Critical errors requiring immediate attention")
```

### Configuration Management
```python
from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:8b"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    # Qdrant Configuration
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "documents_v1"

    # Neo4j Configuration
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: SecretStr

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

---

## API Conventions

### Endpoint Naming
```python
# RESTful patterns
GET    /api/v1/documents          # List documents
GET    /api/v1/documents/{id}     # Get specific document
POST   /api/v1/documents          # Create document
PUT    /api/v1/documents/{id}     # Update document (full)
PATCH  /api/v1/documents/{id}     # Update document (partial)
DELETE /api/v1/documents/{id}     # Delete document

# Action endpoints (POST)
POST   /api/v1/search             # Perform search
POST   /api/v1/query              # Execute query
POST   /api/v1/chat               # Chat interaction

# Status endpoints
GET    /health                    # Health check
GET    /metrics                   # Prometheus metrics
GET    /api/v1/status             # System status
```

### Request/Response Models
```python
from pydantic import BaseModel, Field
from datetime import datetime

class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    query: str = Field(..., description="User query")
    mode: Literal["vector", "graph", "hybrid"] = "hybrid"
    top_k: int = Field(default=5, ge=1, le=50)
    filters: Optional[Dict[str, str]] = None

class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    query: str
    answer: str
    sources: List[Source]
    metadata: QueryMetadata

class Source(BaseModel):
    """Document source with citation."""
    doc_id: str
    title: str
    content: str
    score: float
    source_type: Literal["vector", "graph"]

class QueryMetadata(BaseModel):
    """Metadata about query execution."""
    latency_ms: float
    retrieval_count: int
    agent_path: List[str]
    timestamp: datetime
```

---

## Database Conventions

### Qdrant Collection Names
```python
COLLECTION_DOCUMENTS = "documents_v1"
COLLECTION_MEMORIES = "memories_v1"
COLLECTION_SUMMARIES = "summaries_v1"

# Versioning scheme: {name}_v{major}
# Increment on breaking schema changes
```

### Neo4j Node Labels & Relationships
```python
# Node Labels (PascalCase)
(:Entity)
(:Topic)
(:Community)
(:Conversation)
(:Memory)
(:Section)        # Sprint 32: Section-aware chunking

# Relationship Types (SCREAMING_SNAKE_CASE)
-[:RELATES_TO]->      # Sprint 34: Semantic relationships
-[:PART_OF]->
-[:MENTIONS]->
-[:MENTIONED_IN]->    # Sprint 51: Cross-modal fusion
-[:DISCUSSED_IN]->
-[:EXTRACTED_FROM]->

# Properties (snake_case)
{
    entity_id: "uuid",
    created_at: "2025-01-15T10:30:00Z",
    updated_at: "2025-01-15T10:30:00Z",
    valid_from: "2025-01-15T10:30:00Z",
    valid_to: null
}
```

### Redis Key Patterns
```python
# Format: {namespace}:{resource_type}:{identifier}
f"aegis:session:{session_id}"
f"aegis:memory:short_term:{user_id}"
f"aegis:cache:query:{hash(query)}"
f"aegis:lock:indexing:{doc_id}"

# Use colons for hierarchy
# Include TTL in key design
```

---

## Testing Conventions

### Test Function Naming
```python
# Pattern: test_{method}__{scenario}__{expected_outcome}
def test_search__valid_query__returns_documents():
    pass

def test_search__empty_query__raises_validation_error():
    pass

def test_fusion__multiple_lists__combines_correctly():
    pass

# Descriptive names explain test purpose
def test_hybrid_search_with_filters_returns_only_matching_documents():
    pass
```

### Fixtures & Factories
```python
import pytest
from faker import Faker

@pytest.fixture
def mock_qdrant_client():
    """Mocked Qdrant client for unit tests."""
    client = Mock(spec=QdrantClient)
    client.search.return_value = [mock_document()]
    return client

@pytest.fixture
def sample_query() -> str:
    """Sample user query for testing."""
    return "What is retrieval augmented generation?"

# Factory pattern for test data
class DocumentFactory:
    @staticmethod
    def create(content: str = None, metadata: dict = None) -> Document:
        fake = Faker()
        return Document(
            page_content=content or fake.text(),
            metadata=metadata or {"source": fake.url()}
        )
```

### Async Test Patterns
```python
import pytest

@pytest.mark.asyncio
async def test_async_retrieval__concurrent_calls__all_succeed():
    """Test concurrent retrieval operations."""
    queries = ["query1", "query2", "query3"]
    results = await asyncio.gather(*[search(q) for q in queries])
    assert all(len(r) > 0 for r in results)
```

---

## Git Commit Standards

### Conventional Commits
```bash
# Format
<type>(<scope>): <subject>

<body>

<footer>

# Types
feat     # New feature
fix      # Bug fix
docs     # Documentation only
style    # Code style (formatting, no logic change)
refactor # Code restructuring (no feature/bug change)
test     # Add/modify tests
chore    # Maintenance (dependencies, build)
perf     # Performance improvement
ci       # CI/CD changes

# Examples
feat(vector): implement hybrid search with BM25
fix(graph): resolve neo4j connection pool exhaustion
docs(api): add OpenAPI examples for query endpoint
refactor(agents): extract common retry logic to decorator
test(memory): add integration tests for consolidation
chore(deps): upgrade langchain to 0.3.0
```

### Branch Naming
```bash
feature/hybrid-search-implementation
fix/neo4j-connection-leak
docs/add-deployment-guide
refactor/simplify-agent-routing
sprint-60/documentation-consolidation
```

---

## Code Review Checklist

### Must-Have Before Merge
- [ ] All tests pass (unit, integration, E2E)
- [ ] Test coverage >80% for critical paths
- [ ] Type hints on all public functions
- [ ] Docstrings for classes and complex functions
- [ ] No hardcoded secrets or credentials
- [ ] Error handling for external dependencies
- [ ] Logging at appropriate levels
- [ ] Code formatted with Black (line-length=100)
- [ ] No linting errors (Ruff)
- [ ] Type checking passes (MyPy)
- [ ] Performance considerations documented
- [ ] Breaking changes documented in PR

### Nice-to-Have
- [ ] Performance benchmarks for critical paths
- [ ] Example usage in docstrings
- [ ] Edge cases tested
- [ ] Metrics/monitoring added for new features

---

## Performance Guidelines

### Optimization Priorities
1. **Correctness** > **Performance** > **Elegance**
2. Profile before optimizing (use cProfile, py-spy)
3. Async I/O for external calls (DB, API)
4. Batch operations where possible
5. Cache expensive computations (LRU, Redis)

### Anti-Patterns to Avoid
```python
# ❌ Synchronous I/O in async context
async def bad_search(query):
    results = requests.get(url)  # Blocks event loop
    return results

# ✅ Use async client
async def good_search(query):
    async with httpx.AsyncClient() as client:
        results = await client.get(url)
    return results

# ❌ Loading all data into memory
documents = load_all_documents()  # 10GB dataset
for doc in documents:
    process(doc)

# ✅ Stream processing
for doc in stream_documents():
    process(doc)

# ❌ N+1 queries
for doc_id in doc_ids:
    doc = db.get(doc_id)  # 1000 queries

# ✅ Batch fetch
docs = db.get_many(doc_ids)  # 1 query
```

---

## Security Best Practices

```python
# Input sanitization
from pydantic import validator, constr

class QueryInput(BaseModel):
    query: constr(min_length=1, max_length=1000)

    @validator('query')
    def sanitize_query(cls, v):
        # Remove potential injection patterns
        dangerous_patterns = ['DROP', 'DELETE', 'INSERT']
        if any(p in v.upper() for p in dangerous_patterns):
            raise ValueError("Potentially dangerous query pattern detected")
        return v

# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/query")
@limiter.limit("10/minute")
async def query(request: Request, query_input: QueryInput):
    pass

# Secrets management
# ❌ Never commit secrets
OPENAI_API_KEY = "sk-..."

# ✅ Use environment variables
from pydantic import SecretStr
ollama_api_key: SecretStr = Field(..., env='OLLAMA_API_KEY')
```

---

## Documentation Standards

### README Structure
```markdown
# Project Title
Brief description (1-2 sentences)

## Features
- Key feature 1
- Key feature 2

## Quick Start
```bash
# Minimal setup to run
```

## Architecture
High-level diagram + explanation

## Development
How to set up dev environment

## Deployment
Production deployment guide

## Contributing
Guidelines for contributors

## License
```

### Inline Comments
```python
# Comments explain WHY, not WHAT
# ❌ Bad comment
x = x + 1  # Increment x

# ✅ Good comment
# Compensate for border offset in layout calculation
x = x + 1

# Use comments for complex logic
# Reciprocal Rank Fusion (Cormack et al. 2009)
# Combines rankings by: score = sum(1/(k + rank_i))
# where k=60 (empirically optimal per original paper)
score = sum(1 / (60 + rank) for rank in ranks)
```

---

## Sprint 59: Tool Framework Conventions

### Tool Registration
```python
from src.domains.llm_integration.tools.registry import ToolRegistry

@ToolRegistry.register(
    name="bash",
    description="Execute bash command",
    parameters=BASH_TOOL_SCHEMA,
    requires_sandbox=True
)
async def bash_execute(command: str, timeout: int = 30):
    """Execute bash command with security validation."""
    pass
```

### Tool Security
- **5-Layer Defense:** Input validation → Restricted environment → Sandbox → Timeout → Truncation
- **Bash Tool:** Blacklist validation, sanitized env vars
- **Python Tool:** AST validation, restricted globals
- **Docker Sandbox:** Network isolation, read-only filesystem, resource limits

---

These standards should be enforced in all code reviews. If unclear: Discuss in the team and update this document.

---

**Document Consolidated:** Sprint 60 Feature 60.1
**Source:** NAMING_CONVENTIONS.md
**Maintainer:** Claude Code with Human Review
