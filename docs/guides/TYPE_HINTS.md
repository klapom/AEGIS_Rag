# Type Hints Best Practices

**Sprint:** Sprint 25 (Feature 25.5)
**Status:** Active - MyPy Strict Mode Enabled
**Related:** pyproject.toml `[tool.mypy]` configuration

---

## Overview

AegisRAG enforces **MyPy strict mode** for all Python code to ensure type safety, prevent runtime errors, and improve code maintainability. This guide covers best practices for writing type-safe Python code.

**Why Strict Mode?**
- Catches type errors at development time (not runtime)
- Improves IDE autocomplete and refactoring
- Serves as living documentation
- Prevents common bugs (None errors, wrong argument types)
- Enforces explicit typing for all public APIs

---

## Quick Reference

### Function Signatures

```python
from typing import List, Dict, Optional, Union, Any
from pathlib import Path

# ✅ GOOD: Full type hints
def process_documents(
    docs: List[str],
    metadata: Dict[str, Union[str, int]],
    max_tokens: Optional[int] = None
) -> Dict[str, List[str]]:
    """Process documents with metadata."""
    result: Dict[str, List[str]] = {}
    # ... implementation
    return result

# ❌ BAD: Missing type hints
def process_documents(docs, metadata, max_tokens=None):
    result = {}
    return result
```

### Class Definitions

```python
from typing import ClassVar, List, Optional
from pydantic import BaseModel

# ✅ GOOD: Typed class with Pydantic
class DocumentMetadata(BaseModel):
    """Document metadata with validation."""
    title: str
    author: str
    pages: int
    tags: List[str] = []
    created_at: Optional[str] = None

# ✅ GOOD: Typed class with dataclass
from dataclasses import dataclass

@dataclass
class SearchConfig:
    """Configuration for search."""
    top_k: int = 10
    threshold: float = 0.7
    rerank: bool = False

# ✅ GOOD: Regular class with type hints
class VectorSearchEngine:
    """Vector search engine with type-safe interface."""

    # Class variable
    DEFAULT_TOP_K: ClassVar[int] = 10

    def __init__(self, collection_name: str, top_k: int = 10) -> None:
        self.collection_name = collection_name
        self.top_k = top_k

    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Search with optional filters."""
        pass
```

### Async Functions

```python
from typing import List, Dict, Any
import asyncio

# ✅ GOOD: Async function with return type
async def fetch_data(url: str, timeout: int = 30) -> Dict[str, Any]:
    """Fetch data from URL."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=timeout)
        return response.json()

# ✅ GOOD: Async function returning None
async def process_in_background(data: List[str]) -> None:
    """Process data asynchronously without return value."""
    await asyncio.sleep(1)
    for item in data:
        print(item)
```

---

## Common Type Patterns

### 1. Optional Types (Nullable Values)

```python
from typing import Optional

# ✅ GOOD: Use Optional for nullable values
def get_user_name(user_id: int) -> Optional[str]:
    """Returns username or None if not found."""
    user = find_user(user_id)
    return user.name if user else None

# ✅ GOOD: Modern Python 3.10+ syntax
def get_user_name(user_id: int) -> str | None:
    """Returns username or None if not found."""
    pass

# ❌ BAD: Implicit None without Optional
def get_user_name(user_id: int) -> str:
    return None  # MyPy error: returning None for str
```

### 2. Union Types (Multiple Possible Types)

```python
from typing import Union, List, Dict

# ✅ GOOD: Union for multiple types
def format_value(value: Union[str, int, float]) -> str:
    """Format value as string."""
    return str(value)

# ✅ GOOD: Modern Python 3.10+ syntax
def format_value(value: str | int | float) -> str:
    """Format value as string."""
    return str(value)

# ✅ GOOD: Union with None
def get_config(key: str) -> Union[str, int, None]:
    """Get config value or None."""
    pass

# ✅ BETTER: Use Optional for Union with None
def get_config(key: str) -> Optional[Union[str, int]]:
    """Get config value or None."""
    pass
```

### 3. Generic Collections

```python
from typing import List, Dict, Set, Tuple, Any

# ✅ GOOD: Specify element types
def get_document_ids() -> List[int]:
    """Returns list of document IDs."""
    return [1, 2, 3]

def get_metadata() -> Dict[str, str]:
    """Returns metadata dictionary."""
    return {"author": "John", "title": "Doc"}

def get_tags() -> Set[str]:
    """Returns unique tags."""
    return {"python", "typing"}

def get_coordinates() -> Tuple[float, float]:
    """Returns x, y coordinates."""
    return (1.0, 2.0)

# ❌ BAD: Generic list without element type
def get_document_ids() -> List:
    return [1, 2, 3]

# ❌ BAD: Using Any (defeats type checking)
def get_data() -> List[Any]:
    return [1, "two", 3.0]  # Avoid Any unless truly dynamic
```

### 4. Complex Nested Types

```python
from typing import Dict, List, Optional, Union

# ✅ GOOD: Complex nested type
def analyze_results(
    data: Dict[str, List[Dict[str, Union[str, int, float]]]]
) -> Optional[Dict[str, float]]:
    """Analyze nested results structure."""
    if not data:
        return None

    scores: Dict[str, float] = {}
    for key, items in data.items():
        total = sum(
            float(item["score"])
            for item in items
            if "score" in item
        )
        scores[key] = total
    return scores

# ✅ BETTER: Use TypeAlias for readability
from typing import TypeAlias

ResultItem: TypeAlias = Dict[str, Union[str, int, float]]
ResultData: TypeAlias = Dict[str, List[ResultItem]]
ScoreMap: TypeAlias = Dict[str, float]

def analyze_results(data: ResultData) -> Optional[ScoreMap]:
    """Analyze nested results structure."""
    pass
```

### 5. Callable Types (Functions as Arguments)

```python
from typing import Callable, List

# ✅ GOOD: Callback function type
def process_items(
    items: List[str],
    callback: Callable[[str], int]
) -> List[int]:
    """Process items with callback function."""
    return [callback(item) for item in items]

# Example usage:
def count_chars(text: str) -> int:
    return len(text)

result = process_items(["hello", "world"], count_chars)

# ✅ GOOD: Callback with multiple args and return type
def transform_data(
    data: List[int],
    transformer: Callable[[int, int], float]
) -> List[float]:
    """Transform data using function."""
    return [transformer(x, i) for i, x in enumerate(data)]
```

---

## Advanced Patterns

### 1. Generic Classes

```python
from typing import Generic, TypeVar, List

T = TypeVar('T')

class Repository(Generic[T]):
    """Generic repository for any type."""

    def __init__(self) -> None:
        self._items: List[T] = []

    def add(self, item: T) -> None:
        """Add item to repository."""
        self._items.append(item)

    def get_all(self) -> List[T]:
        """Get all items."""
        return self._items.copy()

# Usage with specific types:
doc_repo: Repository[Document] = Repository()
user_repo: Repository[User] = Repository()
```

### 2. Protocol (Structural Subtyping)

```python
from typing import Protocol, List

class Searchable(Protocol):
    """Protocol for searchable objects."""

    def search(self, query: str) -> List[str]:
        """Search interface."""
        ...

# Any class implementing search() method is compatible
class VectorSearch:
    def search(self, query: str) -> List[str]:
        return ["result1", "result2"]

class KeywordSearch:
    def search(self, query: str) -> List[str]:
        return ["result3", "result4"]

# Both work with functions expecting Searchable
def perform_search(engine: Searchable, query: str) -> List[str]:
    return engine.search(query)
```

### 3. Literal Types (Exact Values)

```python
from typing import Literal

# ✅ GOOD: Restrict to specific values
def set_log_level(level: Literal["DEBUG", "INFO", "WARNING", "ERROR"]) -> None:
    """Set logging level to specific value."""
    print(f"Setting level to {level}")

# Usage:
set_log_level("DEBUG")  # OK
set_log_level("TRACE")  # MyPy error: invalid value

# ✅ GOOD: Multiple literal values
Mode = Literal["vector", "graph", "hybrid"]

def search(query: str, mode: Mode) -> List[Document]:
    """Search with specific mode."""
    pass
```

### 4. TypedDict (Structured Dictionaries)

```python
from typing import TypedDict, Optional

# ✅ GOOD: Define dict structure
class UserInfo(TypedDict):
    """User information dictionary."""
    id: int
    name: str
    email: str
    age: Optional[int]

def create_user(info: UserInfo) -> int:
    """Create user from structured dict."""
    # MyPy knows info has specific keys
    print(info["name"])  # OK
    print(info["invalid"])  # MyPy error
    return info["id"]

# Usage:
user: UserInfo = {
    "id": 1,
    "name": "John",
    "email": "john@example.com",
    "age": 30
}
```

---

## Handling Third-Party Libraries

### 1. Libraries Without Type Stubs

```python
# Add to pyproject.toml [[tool.mypy.overrides]]:
[[tool.mypy.overrides]]
module = [
    "qdrant_client.*",
    "llama_index.*",
    "ollama.*",
]
ignore_missing_imports = true
```

### 2. Type Stubs for Common Libraries

Install type stubs where available:

```bash
poetry add --group dev types-pyyaml types-aiofiles types-redis
```

### 3. Wrapping Untyped Libraries

```python
from typing import Any, List, cast

# Wrap untyped library with type-safe interface
import untyped_library  # type: ignore

def safe_wrapper(data: List[str]) -> List[int]:
    """Type-safe wrapper around untyped function."""
    # Use cast to tell MyPy the return type
    result = untyped_library.process(data)
    return cast(List[int], result)
```

---

## When to Use `Any` (Rarely!)

`Any` should be avoided as it defeats type checking. Use only when:

1. **Truly Dynamic Data** (JSON from external API)
   ```python
   from typing import Any, Dict

   def parse_json_response(response: str) -> Dict[str, Any]:
       """Parse unknown JSON structure."""
       return json.loads(response)
   ```

2. **Gradual Migration** (temporary during refactoring)
   ```python
   # TODO: Replace Any with proper types
   def legacy_function(data: Any) -> Any:
       pass
   ```

3. **Framework Requirements** (e.g., Pydantic Field)
   ```python
   from pydantic import BaseModel, Field
   from typing import Any

   class Config(BaseModel):
       extra: Dict[str, Any] = Field(default_factory=dict)
   ```

---

## Mypy Configuration

### Current AegisRAG Configuration (pyproject.toml)

```toml
[tool.mypy]
python_version = "3.11"
strict = true  # Enables all strict checks

# Additional checks
warn_return_any = true
warn_unused_configs = true
disallow_any_unimported = true
no_implicit_optional = true
warn_no_return = true
show_error_codes = true
show_column_numbers = true
pretty = true

# Ignore third-party libraries without stubs
[[tool.mypy.overrides]]
module = [
    "qdrant_client.*",
    "llama_index.*",
    "ollama.*",
    "rank_bm25.*",
]
ignore_missing_imports = true
```

### Running MyPy Locally

```bash
# Check all source code
poetry run mypy src/

# Check specific file
poetry run mypy src/components/llm_proxy/aegis_llm_proxy.py

# Check with verbose output
poetry run mypy src/ --verbose

# Show error codes
poetry run mypy src/ --show-error-codes
```

---

## Common MyPy Errors and Fixes

### 1. Missing Return Type

```python
# ❌ ERROR: Function is missing a return type annotation
def get_data():
    return [1, 2, 3]

# ✅ FIX: Add return type
def get_data() -> List[int]:
    return [1, 2, 3]
```

### 2. Missing Parameter Types

```python
# ❌ ERROR: Function is missing a type annotation for parameter
def process(data):
    return len(data)

# ✅ FIX: Add parameter types
def process(data: List[str]) -> int:
    return len(data)
```

### 3. Incompatible Return Type

```python
# ❌ ERROR: Incompatible return value type
def get_name() -> str:
    return None  # Returns None, expects str

# ✅ FIX: Use Optional
def get_name() -> Optional[str]:
    return None
```

### 4. Untyped Decorator

```python
from typing import Callable, TypeVar, cast
from functools import wraps

F = TypeVar('F', bound=Callable[..., Any])

# ✅ FIX: Type decorator properly
def my_decorator(func: F) -> F:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        print("Before")
        result = func(*args, **kwargs)
        print("After")
        return result
    return cast(F, wrapper)
```

### 5. Dict with Unknown Keys

```python
# ❌ ERROR: Value of type "dict[str, Any]" is not indexable
def get_value(data: Dict[str, Any], key: str) -> str:
    return data[key]  # May not exist

# ✅ FIX: Check key existence
def get_value(data: Dict[str, Any], key: str) -> Optional[str]:
    return data.get(key)

# ✅ BETTER: Use TypedDict
from typing import TypedDict

class ConfigData(TypedDict):
    host: str
    port: int

def get_host(config: ConfigData) -> str:
    return config["host"]  # Type-safe
```

---

## CI/CD Integration

MyPy runs automatically in CI pipeline:

```yaml
# .github/workflows/ci.yml
- name: Run MyPy Type Checker (Strict Mode)
  run: |
    poetry run mypy src/ --config-file=pyproject.toml
```

Currently set to `continue-on-error: true` during migration phase. Will be enforced once all type errors are fixed.

---

## Migration Strategy

### Phase 1: Configuration (Complete)
- ✅ Enable strict mode in pyproject.toml
- ✅ Add MyPy to CI pipeline
- ✅ Document best practices (this file)

### Phase 2: Fix Critical Files (In Progress)
Priority order:
1. `src/components/llm_proxy/` (LLM abstraction)
2. `src/agents/` (Agent orchestration)
3. `src/components/vector_search/` (Retrieval)
4. `src/components/graph_rag/` (Graph)
5. `src/api/` (API endpoints)
6. `src/core/` (Shared modules)
7. `src/utils/` (Helpers)

### Phase 3: Enforce Strict Mode
- Remove `continue-on-error: true` from CI
- Block PRs with type errors
- Maintain 100% type coverage

---

## IDE Integration

### VS Code

Install Pylance extension and add to `settings.json`:

```json
{
  "python.linting.mypyEnabled": true,
  "python.linting.mypyArgs": [
    "--config-file=pyproject.toml"
  ],
  "python.analysis.typeCheckingMode": "strict"
}
```

### PyCharm

Enable type checking:
1. Settings > Editor > Inspections
2. Enable "Python > Type checker"
3. Set severity to "Error"

---

## References

- [MyPy Documentation](https://mypy.readthedocs.io/)
- [PEP 484 - Type Hints](https://www.python.org/dev/peps/pep-0484/)
- [PEP 526 - Variable Annotations](https://www.python.org/dev/peps/pep-0526/)
- [Python Typing Module](https://docs.python.org/3/library/typing.html)
- [Real Python Type Hints Guide](https://realpython.com/python-type-checking/)

---

## Questions or Issues?

- Check MyPy error codes: https://mypy.readthedocs.io/en/stable/error_codes.html
- Ask in team Slack channel: #aegis-rag-dev
- Open issue: GitHub Issues with `type-hints` label

---

**Last Updated:** 2025-11-13 (Sprint 25, Feature 25.5)
**Maintained By:** Backend Team
