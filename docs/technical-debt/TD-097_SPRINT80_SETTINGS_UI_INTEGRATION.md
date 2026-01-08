# TD-097: Sprint 80 Settings UI/DB Integration

**Status:** OPEN
**Priority:** MEDIUM
**Story Points:** 3 SP
**Created:** 2026-01-08
**Sprint:** Sprint 81 (planned)

---

## Problem Statement

**New Sprint 80 settings are not exposed in Admin UI** - The `strict_faithfulness_enabled` config setting (Feature 80.1) was added to `config.py` but needs:
1. Redis persistence (like other Admin UI configs)
2. Admin UI toggle for operators to enable/disable

### Current State

```python
# src/core/config.py:579-593
# Sprint 80 Feature 80.1: Faithfulness Optimization
strict_faithfulness_enabled: bool = Field(
    default=False,
    description="Enable strict citation mode requiring citations for EVERY sentence. "
    "When True, uses FAITHFULNESS_STRICT_PROMPT which forbids general knowledge. "
    "Designed to maximize RAGAS Faithfulness score (F=0.55→0.85+). Default: False.",
)

# Sprint 80 Feature 80.2: Graph→Vector Fallback
graph_vector_fallback_enabled: bool = Field(
    default=True,
    description="Enable automatic fallback to vector search when graph search returns "
    "empty results. Improves Context Recall by ensuring contexts are always retrieved. "
    "Default: True.",
)
```

**Missing**:
- Redis persistence (currently only env var / config.py default)
- Admin UI toggle on Settings page

---

## Impact

### Without UI Control

**Operators cannot**:
1. Toggle strict faithfulness mode without redeploying
2. A/B test citation modes per-namespace
3. Quickly switch between "flexible" (allows general knowledge) and "strict" (100% sourced) modes

### Expected Behavior

| Setting | Default | UI Control | Description |
|---------|---------|------------|-------------|
| `strict_faithfulness_enabled` | `false` | Toggle | Require citations for EVERY sentence (no general knowledge) |
| `graph_vector_fallback_enabled` | `true` | Toggle | Fallback to vector search if graph returns empty |

---

## Proposed Solution

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Admin UI (Frontend)                                         │
├─────────────────────────────────────────────────────────────┤
│ General Setup > Answer Generation                           │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ Strict Faithfulness Mode:   [OFF] / ON                   ││
│ │                                                          ││
│ │ When enabled, the LLM must cite a source for EVERY       ││
│ │ sentence. No general knowledge allowed.                  ││
│ │                                                          ││
│ │ ⚠️ Recommended for: High-compliance, legal, medical     ││
│ │ ⚠️ May reduce answer quality for general questions      ││
│ │                                                          ││
│ │ [Save Configuration]                                    ││
│ └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                        ↓
                   API POST /api/v1/admin/generation/config
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ Backend (FastAPI)                                           │
├─────────────────────────────────────────────────────────────┤
│ src/api/v1/admin_generation.py                              │
│ - GET  /generation/config  → Load from Redis                │
│ - POST /generation/config  → Save to Redis                  │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ Redis Storage                                               │
├─────────────────────────────────────────────────────────────┤
│ Key: "admin:generation_config"                              │
│ Value: {                                                    │
│   "strict_faithfulness_enabled": false,                     │
│   "updated_at": "2026-01-08T12:00:00Z"                      │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ Answer Generator                                            │
├─────────────────────────────────────────────────────────────┤
│ src/agents/answer_generator.py                              │
│ - Load config from Redis (cached 60s) OR config.py default  │
│ - Apply strict_faithfulness to prompt selection             │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Backend Config Service (1 SP, 1 hour)

**Files**:
- `src/components/generation_config/generation_config_service.py` (NEW)
- `src/components/generation_config/__init__.py` (NEW)

**Models**:
```python
from pydantic import BaseModel, Field

class GenerationConfig(BaseModel):
    """Answer generation configuration (persisted in Redis)."""

    strict_faithfulness_enabled: bool = Field(
        default=False,
        description="Require citations for EVERY sentence (no general knowledge)"
    )
    updated_at: str = Field(default="", description="ISO timestamp of last update")

    class Config:
        json_schema_extra = {
            "example": {
                "strict_faithfulness_enabled": False,
                "updated_at": "2026-01-08T12:00:00Z"
            }
        }
```

**Service**:
```python
class GenerationConfigService:
    """Manage answer generation configuration in Redis."""

    REDIS_KEY = "admin:generation_config"
    CACHE_TTL = 60  # 60s cache

    async def get_config(self) -> GenerationConfig:
        """Load config from Redis (with 60s cache)."""
        # Fallback to config.py defaults if Redis empty
        ...

    async def save_config(self, config: GenerationConfig) -> GenerationConfig:
        """Save config to Redis and invalidate cache."""
        ...
```

---

### Phase 2: API Endpoints (0.5 SP, 30 min)

**File**: `src/api/v1/admin_generation.py` (NEW)

**Endpoints**:
```python
@router.get("/generation/config", response_model=GenerationConfig)
async def get_generation_config() -> GenerationConfig:
    """Get current answer generation configuration from Redis."""

@router.post("/generation/config", response_model=GenerationConfig)
async def update_generation_config(config: GenerationConfig) -> GenerationConfig:
    """Update answer generation configuration (saved to Redis)."""
```

---

### Phase 3: Answer Generator Integration (0.5 SP, 30 min)

**File**: `src/agents/answer_generator.py`

**Changes**:
```python
async def generate_with_citations(
    self,
    query: str,
    contexts: list[dict[str, Any]],
    intent: str | None = None,
    strict_faithfulness: bool | None = None,  # None = load from config
) -> tuple[str, dict[int, dict[str, Any]]]:
    # If strict_faithfulness not explicitly passed, load from Redis config
    if strict_faithfulness is None:
        from src.components.generation_config import get_generation_config_service
        config = await get_generation_config_service().get_config()
        strict_faithfulness = config.strict_faithfulness_enabled
    ...
```

---

### Phase 4: Frontend UI (1 SP, 1 hour)

**File**: `frontend/src/pages/admin/AdminGenerationConfig.tsx` (NEW)

**UI Components**:
- Toggle switch for `strict_faithfulness_enabled`
- Explanation text
- Warning about impact on answer quality
- Save button → POST /api/v1/admin/generation/config

**Integration**: Add to Admin navigation menu under "Answer Generation"

---

## Testing Strategy

### Unit Tests
```python
async def test_generation_config_service():
    service = get_generation_config_service()

    # Test default config
    config = await service.get_config()
    assert config.strict_faithfulness_enabled == False

    # Test save and reload
    config.strict_faithfulness_enabled = True
    await service.save_config(config)
    reloaded = await service.get_config()
    assert reloaded.strict_faithfulness_enabled == True
```

### E2E Tests (Playwright)
```typescript
test('Admin can toggle strict faithfulness mode', async ({ page }) => {
  await page.goto('/admin/generation');

  // Toggle strict mode ON
  await page.click('input[name="strict_faithfulness_enabled"]');
  await page.click('button:has-text("Save")');

  // Verify saved
  await expect(page.locator('.success-message')).toBeVisible();

  // Reload and verify persisted
  await page.reload();
  await expect(page.locator('input[name="strict_faithfulness_enabled"]')).toBeChecked();
});
```

---

## Related Issues

- **Feature 80.1**: Cite-Sources Prompt Engineering (Sprint 80)
- **TD-096**: Chunking Parameters UI Integration (similar pattern)
- **RAGAS_JOURNEY.md**: Documents Faithfulness optimization experiments

---

## References

**Sprint 80 Context**:
- RAGAS Faithfulness target: F=0.55 → 0.85+ with strict citations
- `FAITHFULNESS_STRICT_PROMPT` requires [1], [2] for every sentence
- Default OFF to preserve backwards compatibility

---

**Priority**: MEDIUM (Feature works via config.py, UI is convenience)
**Effort**: 3 SP (1 hour backend, 30 min API, 30 min integration, 1 hour UI)
**Target Sprint**: Sprint 81
