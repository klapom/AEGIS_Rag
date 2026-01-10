# Feature 83.5: Configurable 3-Rank Cascade

**Story Points:** 3 SP
**Sprint:** 83 (Optional Extension)
**Priority:** MEDIUM (Nice-to-have for domain-specific optimization)

---

## User Story

**As a** Domain Administrator
**I want to** configure extraction strategy per rank (LLM model, timeout, prompt source, extraction type)
**So that** I can optimize extraction for different document types (e.g., legal: SpaCy Rank 1, technical: Nemotron3)

---

## Requirements

### 1. Extended CascadeRankConfig (Pydantic Model)

```python
# src/config/extraction_cascade.py

from pydantic import BaseModel, Field
from typing import Literal, Optional

class CascadeRankConfig(BaseModel):
    """Configuration for a single cascade rank."""

    rank: int = Field(ge=1, le=3, description="Cascade rank (1-3)")

    # LLM Selection (from available Ollama models)
    model_id: str = Field(
        default="nemotron3",
        description="Ollama model ID (e.g., 'nemotron3', 'gpt-oss:20b', 'qwen2.5:7b')"
    )

    # Timeout Configuration
    timeout_s: int = Field(
        default=300,
        ge=60,
        le=900,
        description="LLM timeout in seconds (60-900s)"
    )

    # Prompt Source
    prompt_source: Literal["default", "dspy"] = Field(
        default="default",
        description="Prompt source: 'default' (hardcoded) or 'dspy' (optimized)"
    )

    # Extraction Type
    extraction_type: Literal["llm", "spacy", "hybrid"] = Field(
        default="llm",
        description="Extraction strategy: 'llm' (pure LLM), 'spacy' (NER only), 'hybrid' (SpaCy entities + LLM relations)"
    )

    # SpaCy Configuration (for extraction_type="spacy" or "hybrid")
    spacy_languages: Optional[List[str]] = Field(
        default=["de", "en", "fr", "es"],
        description="SpaCy language models to load (e.g., ['de', 'en'])"
    )

    # Retry Configuration
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Max retry attempts with exponential backoff"
    )

# Example Configurations:

# Default (Sprint 83 Current)
DEFAULT_CASCADE = [
    CascadeRankConfig(
        rank=1,
        model_id="nemotron3",
        timeout_s=300,
        prompt_source="default",
        extraction_type="llm"
    ),
    CascadeRankConfig(
        rank=2,
        model_id="gpt-oss:20b",
        timeout_s=300,
        prompt_source="default",
        extraction_type="llm"
    ),
    CascadeRankConfig(
        rank=3,
        model_id="gpt-oss:20b",
        timeout_s=600,
        prompt_source="default",
        extraction_type="hybrid",
        spacy_languages=["de", "en", "fr", "es"]
    ),
]

# Legal Documents (Exhaustive Extraction)
LEGAL_CASCADE = [
    CascadeRankConfig(
        rank=1,
        model_id="qwen2.5:7b",
        timeout_s=300,
        prompt_source="dspy",  # DSPy-optimized prompts
        extraction_type="llm"
    ),
    CascadeRankConfig(
        rank=2,
        model_id="gpt-oss:20b",
        timeout_s=600,
        prompt_source="dspy",
        extraction_type="llm"
    ),
    CascadeRankConfig(
        rank=3,
        model_id="spacy",  # SpaCy-only (fast, no LLM)
        timeout_s=0,
        prompt_source="default",
        extraction_type="spacy",
        spacy_languages=["de", "en"]
    ),
]

# Technical Docs (Speed-Optimized)
TECH_CASCADE = [
    CascadeRankConfig(
        rank=1,
        model_id="spacy",  # SpaCy first (instant)
        timeout_s=0,
        prompt_source="default",
        extraction_type="spacy",
        spacy_languages=["en"]
    ),
    CascadeRankConfig(
        rank=2,
        model_id="nemotron3",
        timeout_s=180,  # Shorter timeout
        prompt_source="default",
        extraction_type="llm"
    ),
    CascadeRankConfig(
        rank=3,
        model_id="gpt-oss:20b",
        timeout_s=300,
        prompt_source="default",
        extraction_type="hybrid"
    ),
]
```

### 2. DSPy Prompt Integration

```python
# src/prompts/dspy_prompts.py (NEW)

import dspy
from typing import Optional

class EntityExtractionSignature(dspy.Signature):
    """DSPy signature for entity extraction."""

    document_text = dspy.InputField(desc="Document text to extract entities from")
    chunk_id = dspy.InputField(desc="Unique chunk identifier")

    entities = dspy.OutputField(desc="List of extracted entities in JSON format")

class DSPyPromptManager:
    """Manage DSPy-optimized prompts for extraction."""

    def __init__(self, model_id: str = "nemotron3"):
        self.lm = dspy.OllamaLocal(
            model=model_id,
            base_url="http://localhost:11434"
        )
        dspy.settings.configure(lm=self.lm)

        # Load optimized prompt (if exists)
        self.entity_extractor = self._load_optimized_extractor()

    def _load_optimized_extractor(self) -> dspy.Module:
        """Load DSPy-optimized entity extraction prompt."""
        try:
            # Load from checkpoint (if Sprint 79+ DSPy optimization done)
            return dspy.ChainOfThought(EntityExtractionSignature).load(
                "checkpoints/entity_extraction_dspy.json"
            )
        except FileNotFoundError:
            # Fallback to basic DSPy prompt
            return dspy.ChainOfThought(EntityExtractionSignature)

    def extract_entities(self, document_text: str, chunk_id: str) -> str:
        """Extract entities using DSPy-optimized prompt."""
        result = self.entity_extractor(
            document_text=document_text,
            chunk_id=chunk_id
        )
        return result.entities
```

### 3. Extraction Service Integration

```python
# src/components/graph_rag/extraction_service.py (MODIFY)

class ExtractionService:
    """Entity/Relation extraction with configurable 3-rank cascade."""

    def __init__(self, cascade_config: List[CascadeRankConfig]):
        self.cascade = cascade_config
        self.dspy_manager = DSPyPromptManager() if any(
            rank.prompt_source == "dspy" for rank in cascade_config
        ) else None

    async def _extract_entities_with_rank(
        self,
        document_text: str,
        chunk_id: str,
        rank_config: CascadeRankConfig
    ) -> List[Entity]:
        """Extract entities using specific rank configuration."""

        # 1. Select Extraction Strategy
        if rank_config.extraction_type == "spacy":
            # SpaCy NER only (instant, no LLM)
            return await self.hybrid_service.extract_entities_spacy(
                document_text, chunk_id, languages=rank_config.spacy_languages
            )

        elif rank_config.extraction_type == "hybrid":
            # SpaCy entities + LLM relations
            return await self.hybrid_service.extract_entities_hybrid(
                document_text, chunk_id, llm_model=rank_config.model_id
            )

        elif rank_config.extraction_type == "llm":
            # Pure LLM extraction

            # 2. Select Prompt Source
            if rank_config.prompt_source == "dspy":
                # DSPy-optimized prompt
                entities_json = await self.dspy_manager.extract_entities(
                    document_text, chunk_id
                )
            else:
                # Default hardcoded prompt
                entities_json = await self.llm_client.generate(
                    prompt=ENTITY_EXTRACTION_PROMPT.format(
                        document_text=document_text, chunk_id=chunk_id
                    ),
                    model=rank_config.model_id,
                    timeout=rank_config.timeout_s
                )

            # 3. Parse entities
            return self._parse_entities(entities_json)

        else:
            raise ValueError(f"Unknown extraction_type: {rank_config.extraction_type}")
```

---

## Implementation Steps

**Step 1: Extend CascadeRankConfig (1 SP)**
- [x] Add `model_id`, `prompt_source`, `extraction_type` fields
- [x] Add validation (Pydantic validators)
- [x] Add example configurations (DEFAULT, LEGAL, TECH)
- [x] Unit tests (10 tests)

**Step 2: DSPy Prompt Integration (1 SP)**
- [ ] Create `DSPyPromptManager` class
- [ ] Load DSPy checkpoint (if exists from Sprint 79)
- [ ] Fallback to basic DSPy prompt
- [ ] Unit tests (5 tests)

**Step 3: ExtractionService Integration (1 SP)**
- [ ] Modify `_extract_entities_with_rank()` to use rank_config
- [ ] Switch between LLM/SpaCy/Hybrid based on `extraction_type`
- [ ] Switch between DSPy/Default prompts based on `prompt_source`
- [ ] Integration tests (3 tests)

---

## Testing

### Unit Tests (18 tests)

1. **CascadeRankConfig Validation (10 tests)**
   - Valid config (all fields)
   - Invalid timeout (< 60s or > 900s)
   - Invalid rank (< 1 or > 3)
   - Invalid model_id (empty string)
   - Valid extraction_type (llm, spacy, hybrid)
   - Valid prompt_source (default, dspy)
   - SpaCy languages validation
   - Max retries validation

2. **DSPyPromptManager (5 tests)**
   - Load optimized checkpoint (if exists)
   - Fallback to basic DSPy prompt
   - Entity extraction with DSPy
   - Error handling on invalid model
   - Timeout handling

3. **ExtractionService Integration (3 tests)**
   - Extract with extraction_type="llm"
   - Extract with extraction_type="spacy"
   - Extract with extraction_type="hybrid"

### Integration Tests (2 tests)

1. **End-to-End Cascade with Custom Config**
   - Define TECH_CASCADE (SpaCy Rank 1)
   - Extract entities from sample document
   - Verify Rank 1 (SpaCy) succeeds

2. **DSPy Prompt Performance**
   - Compare DSPy vs Default prompt latency
   - Expected: DSPy 20-30% faster (from Sprint 79 optimization)

---

## Success Criteria

- [x] CascadeRankConfig supports all 5 fields (model_id, timeout_s, prompt_source, extraction_type, spacy_languages)
- [ ] DSPy prompts loaded and working (if Sprint 79 optimization done)
- [ ] Extraction type switching (llm/spacy/hybrid) working
- [ ] 18 unit tests passing (100% coverage)
- [ ] 2 integration tests passing
- [ ] Domain-specific cascade configs defined (DEFAULT, LEGAL, TECH)

---

## Future Work (Sprint 84+)

**Sprint 84.3: Admin UI for Cascade Configuration (5 SP)**
- Web UI to configure cascade per domain
- Live preview of cascade flow
- Validation & error messages
- Save to DomainConfig.extraction_settings

**Sprint 85: DSPy Prompt Optimization (8 SP)**
- Train DSPy prompts on HotpotQA + RAGBench
- Expected: 20-30% latency reduction
- Expected: +5-10% entity quality
- Checkpoint: `checkpoints/entity_extraction_dspy.json`

---

## Notes

- **DSPy Dependency:** Feature requires DSPy installed (`pip install dspy-ai`)
- **Ollama Models:** All configured models must be available in Ollama (`ollama list`)
- **SpaCy Models:** Must be downloaded (`python -m spacy download de_core_news_lg`)
- **Backward Compatibility:** DEFAULT_CASCADE matches Sprint 83 behavior (no breaking changes)

---

**Status:** ⏸️ Proposed (Sprint 83 optional extension)
**Effort:** 3 SP (without Admin UI)
**Dependencies:** DSPy (optional), SpaCy (already installed)
