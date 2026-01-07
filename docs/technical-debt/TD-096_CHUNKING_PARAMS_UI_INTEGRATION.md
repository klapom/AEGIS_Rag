# TD-096: Chunking Parameters UI Integration

**Status:** 🟡 OPEN
**Priority:** 🟠 HIGH
**Story Points:** 5 SP
**Created:** 2026-01-07
**Sprint:** Sprint 78 (planned)

---

## Problem Statement

**Chunking parameters are hardcoded** - users cannot tune chunk size, overlap, gleaning, or hard limits via Admin UI, despite these being critical for ER-Extraction quality and performance.

### Current State (Hardcoded)

```python
# src/components/ingestion/nodes/adaptive_chunking.py:662-663
adaptive_chunks = adaptive_section_chunking(
    sections=sections,
    min_chunk=800,           # ❌ Hardcoded
    max_chunk=1800,          # ❌ Hardcoded
    large_section_threshold=1200  # ❌ Hardcoded
)
```

**Missing Parameters**:
- Chunk overlap (tokens)
- Gleaning steps (entity extraction refinement)
- Max hard limit (prevent ER-Extraction timeouts)

---

## Impact

### Without UI Control

**Operators cannot**:
1. Tune chunking for domain-specific documents (medical vs legal vs technical)
2. Optimize ER-Extraction throughput (larger chunks = fewer LLM calls)
3. Prevent timeouts by enforcing hard limits
4. Enable/disable gleaning based on quality requirements

### GraphRAG Best Practices (Microsoft Research)

| Chunk Size | Overlap | Gleaning | Use Case |
|------------|---------|----------|----------|
| 200-400 | 50-100 | 2 | High precision, noisy PDFs |
| 800-1200 | 100-150 | 1 | **Default** (best recall/time ratio) |
| 1200-1500 | 100 | 0-1 | Fast throughput, structured domains |
| >1500 | - | - | ❌ Not recommended (ER-Extraction timeouts) |

**References**:
- [GraphRAG Official Docs](https://microsoft.github.io/graphrag/)
- "From Local to Global" paper: smaller chunks = 2× more entity references
- Bertelsmann GraphRAG implementation: chunk 1200 / overlap 100

---

## Proposed Solution

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Admin UI (Frontend)                                     │
├─────────────────────────────────────────────────────────┤
│ General Setup > Chunking Configuration                  │
│                                                          │
│ ┌─────────────────────────────────────────────────────┐│
│ │ Chunk Size (tokens):          [1200] (800-1500)    ││
│ │ Overlap (tokens):             [100]  (50-200)      ││
│ │ Gleaning Steps:               [0]    (0-3)         ││
│ │ Hard Limit (tokens):          [1500] (1200-2000)   ││
│ │                                                     ││
│ │ Preset: [GraphRAG Default ▼]                       ││
│ │         - High Precision                           ││
│ │         - Balanced (Default)                       ││
│ │         - Fast Throughput                          ││
│ │                                                     ││
│ │ [Save Configuration]                               ││
│ └─────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
                        ↓
                   API POST /api/v1/admin/chunking/config
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Backend (FastAPI)                                       │
├─────────────────────────────────────────────────────────┤
│ src/api/v1/admin_chunking.py                           │
│ - GET  /chunking/config  → Load from Redis             │
│ - POST /chunking/config  → Save to Redis               │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Redis Storage                                           │
├─────────────────────────────────────────────────────────┤
│ Key: "admin:chunking_config"                           │
│ Value: {                                               │
│   "chunk_size": 1200,                                  │
│   "overlap": 100,                                      │
│   "gleaning_steps": 0,                                 │
│   "max_hard_limit": 1500,                              │
│   "updated_at": "2026-01-07T10:30:00Z"                 │
│ }                                                       │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ Ingestion Pipeline                                      │
├─────────────────────────────────────────────────────────┤
│ src/components/ingestion/nodes/adaptive_chunking.py    │
│ - Load config from Redis (cached 60s)                  │
│ - Apply to adaptive_section_chunking()                 │
│ - Enforce hard limit (split sections >max_hard_limit)  │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Backend Config Service (2 SP, 2 hours)

**Files**:
- `src/components/chunking_config/chunking_config_service.py` (NEW)
- `src/components/chunking_config/__init__.py` (NEW)

**Models**:
```python
from pydantic import BaseModel, Field

class ChunkingConfig(BaseModel):
    """Chunking configuration (persisted in Redis)."""

    chunk_size: int = Field(
        default=1200,
        ge=800,
        le=1500,
        description="Target chunk size in tokens (GraphRAG default: 1200)"
    )
    overlap: int = Field(
        default=100,
        ge=50,
        le=200,
        description="Overlap between chunks in tokens (GraphRAG default: 100)"
    )
    gleaning_steps: int = Field(
        default=0,
        ge=0,
        le=3,
        description="Entity extraction refinement passes (0=disabled)"
    )
    max_hard_limit: int = Field(
        default=1500,
        ge=1200,
        le=2000,
        description="Hard limit for large sections (prevent ER-Extraction timeouts)"
    )
    updated_at: str = Field(default="", description="ISO timestamp of last update")

    class Config:
        json_schema_extra = {
            "example": {
                "chunk_size": 1200,
                "overlap": 100,
                "gleaning_steps": 0,
                "max_hard_limit": 1500,
                "updated_at": "2026-01-07T10:30:00Z"
            }
        }
```

**Service**:
```python
class ChunkingConfigService:
    """Manage chunking configuration in Redis."""

    REDIS_KEY = "admin:chunking_config"
    CACHE_TTL = 60  # 60s cache (hot-reloadable)

    async def get_config(self) -> ChunkingConfig:
        """Load config from Redis (with 60s cache)."""
        # Try cache first
        if cached := self._cache.get(self.REDIS_KEY):
            return cached

        # Load from Redis
        redis = await get_redis_memory()
        config_json = await redis.client.get(self.REDIS_KEY)

        if config_json:
            config = ChunkingConfig.model_validate_json(config_json)
        else:
            # Default config (first run)
            config = ChunkingConfig()

        # Cache for 60s
        self._cache[self.REDIS_KEY] = config
        return config

    async def save_config(self, config: ChunkingConfig) -> ChunkingConfig:
        """Save config to Redis and invalidate cache."""
        redis = await get_redis_memory()
        config.updated_at = datetime.now().isoformat()
        await redis.client.set(self.REDIS_KEY, config.model_dump_json())

        # Invalidate cache
        self._cache.pop(self.REDIS_KEY, None)
        return config
```

---

### Phase 2: API Endpoints (1 SP, 1 hour)

**File**: `src/api/v1/admin_chunking.py` (NEW)

**Endpoints**:
```python
@router.get("/chunking/config", response_model=ChunkingConfig)
async def get_chunking_config() -> ChunkingConfig:
    """Get current chunking configuration from Redis."""
    service = get_chunking_config_service()
    return await service.get_config()

@router.post("/chunking/config", response_model=ChunkingConfig)
async def update_chunking_config(config: ChunkingConfig) -> ChunkingConfig:
    """Update chunking configuration (saved to Redis, takes effect within 60s)."""
    service = get_chunking_config_service()
    return await service.save_config(config)

@router.get("/chunking/presets")
async def get_chunking_presets():
    """Get preset configurations (High Precision, Balanced, Fast Throughput)."""
    return {
        "presets": [
            {
                "name": "High Precision",
                "description": "Small chunks, high gleaning (best recall, slower)",
                "chunk_size": 600,
                "overlap": 100,
                "gleaning_steps": 2,
                "max_hard_limit": 1200,
            },
            {
                "name": "Balanced (Default)",
                "description": "GraphRAG recommended settings",
                "chunk_size": 1200,
                "overlap": 100,
                "gleaning_steps": 0,
                "max_hard_limit": 1500,
            },
            {
                "name": "Fast Throughput",
                "description": "Larger chunks, no gleaning (faster, lower recall)",
                "chunk_size": 1500,
                "overlap": 80,
                "gleaning_steps": 0,
                "max_hard_limit": 1500,
            },
        ]
    }
```

---

### Phase 3: Chunker Integration (1 SP, 1 hour)

**File**: `src/components/ingestion/nodes/adaptive_chunking.py`

**Changes**:
```python
async def chunking_node(state: IngestionState) -> IngestionState:
    # Load chunking config from Redis (cached 60s)
    from src.components.chunking_config import get_chunking_config_service
    config = await get_chunking_config_service().get_config()

    # Apply adaptive chunking with config
    adaptive_chunks = adaptive_section_chunking(
        sections=sections,
        min_chunk=max(800, config.chunk_size - 200),  # Dynamic min
        max_chunk=config.chunk_size,  # From config
        large_section_threshold=config.chunk_size,  # From config
        max_hard_limit=config.max_hard_limit,  # NEW: Hard limit
        overlap=config.overlap,  # NEW: Overlap
    )
```

**New Function**: `_split_large_section()`
```python
def _split_large_section(
    section: SectionMetadata,
    max_hard_limit: int = 1500
) -> list[AdaptiveChunk]:
    """Split large section into chunks <=max_hard_limit tokens.

    Prevents ER-Extraction timeouts by enforcing hard token limit.
    """
    if section.token_count <= max_hard_limit:
        return [_create_chunk(section)]

    # Split section text into max_hard_limit chunks
    chunks = []
    # ... (implementation using BGE-M3 tokenizer)
    return chunks
```

---

### Phase 4: Frontend UI (1 SP, 1 hour)

**File**: `frontend/src/pages/admin/AdminChunkingConfig.tsx` (NEW)

**UI Components**:
- Slider for chunk_size (800-1500)
- Slider for overlap (50-200)
- Dropdown for gleaning_steps (0-3)
- Slider for max_hard_limit (1200-2000)
- Preset selector (High Precision / Balanced / Fast Throughput)
- Save button → POST /api/v1/admin/chunking/config

**Integration**: Add to Admin navigation menu

---

## Defaults (Sprint 78)

Based on GraphRAG best practices and user request:

```python
DEFAULT_CHUNKING_CONFIG = {
    "chunk_size": 1200,        # GraphRAG "positive experience" value
    "overlap": 100,            # GraphRAG standard
    "gleaning_steps": 0,       # Disabled (enable for high-precision use cases)
    "max_hard_limit": 1500,    # Prevent ER-Extraction timeouts
}
```

---

## Validation Rules

| Parameter | Min | Max | Description |
|-----------|-----|-----|-------------|
| `chunk_size` | 800 | 1500 | Target chunk size (tokens) |
| `overlap` | 50 | 200 | Overlap between chunks (tokens) |
| `gleaning_steps` | 0 | 3 | Entity extraction refinement passes |
| `max_hard_limit` | 1200 | 2000 | Hard limit for section splitting |

**Constraints**:
- `max_hard_limit >= chunk_size` (hard limit must be at least chunk size)
- `overlap < chunk_size / 2` (overlap cannot exceed half chunk size)

---

## Testing Strategy

### Unit Tests
```python
async def test_chunking_config_service():
    service = get_chunking_config_service()

    # Test default config
    config = await service.get_config()
    assert config.chunk_size == 1200

    # Test save and reload
    config.chunk_size = 800
    await service.save_config(config)
    reloaded = await service.get_config()
    assert reloaded.chunk_size == 800
```

### Integration Tests
```python
async def test_chunking_with_config():
    # Set small chunk size
    await update_chunking_config(ChunkingConfig(chunk_size=600))

    # Ingest document
    result = await ingest_document("test.txt")

    # Verify chunks are <=600 tokens
    chunks = await get_chunks(result.document_id)
    assert all(c.token_count <= 600 for c in chunks)
```

### E2E Tests (Playwright)
```typescript
test('Admin can update chunking config', async ({ page }) => {
  await page.goto('/admin/chunking');

  // Change chunk size
  await page.fill('input[name="chunk_size"]', '800');
  await page.click('button:has-text("Save")');

  // Verify saved
  await expect(page.locator('.success-message')).toBeVisible();
});
```

---

## Metrics

**Before** (Hardcoded):
- Chunk size: Fixed 800-1800 tokens
- Overlap: 0 (not implemented)
- Gleaning: 0 (not configurable)
- Hard limit: None (sections can be 6000+ chars → timeouts)

**After** (Configurable):
- Chunk size: 800-1500 tokens (user-configurable)
- Overlap: 50-200 tokens (user-configurable)
- Gleaning: 0-3 steps (user-configurable)
- Hard limit: 1200-2000 tokens (enforced, prevents timeouts)

---

## Related Issues

- **TD-091**: Chunk Count Mismatch (root cause: no hard limit → ER-Extraction timeouts)
- **Sprint 77 Session 1**: Discovered 9/17 chunks (53%) are HUGE (>5000 chars)
- **ADR-039**: Adaptive Section-Aware Chunking (needs hard limit enforcement)

---

## References

**GraphRAG Research**:
- [Microsoft GraphRAG Documentation](https://microsoft.github.io/graphrag/)
- [From Local to Global: A Graph RAG Approach](https://arxiv.org/abs/2404.16130)
- [Bertelsmann GraphRAG Implementation](https://tech.bertelsmann.com/)

**Best Practices**:
- Chunk size 1200 tokens + 1 glean = good quality/speed balance
- Smaller chunks (600) → 2× more entity references (higher recall)
- Chunks >1500 tokens → ER-Extraction reliability drops

---

**Priority**: 🟠 HIGH (blocks optimal ER-Extraction, causes timeouts)
**Effort**: 5 SP (2 hours backend, 1 hour API, 1 hour chunker, 1 hour UI)
**Target Sprint**: Sprint 78
