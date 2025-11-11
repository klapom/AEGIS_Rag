# Priority 1 Implementation Guide

**Detailed implementation steps for critical refactoring tasks**
**Target:** Sprint 22 Week 1
**Estimated Effort:** 16-20 hours

---

## Task 1.1: Remove Deprecated UnifiedIngestionPipeline

**File:** `src/components/shared/unified_ingestion.py`
**Lines:** 275
**Status:** DEPRECATED - Sprint 21
**Replacement:** `src/components/ingestion/langgraph_pipeline.py`

### Step 1: Find All References

```bash
# Find Python imports
grep -r "UnifiedIngestionPipeline" src/ --include="*.py"
grep -r "from src.components.shared.unified_ingestion import" src/ --include="*.py"
grep -r "get_unified_pipeline" src/ --include="*.py"

# Find test references
grep -r "UnifiedIngestionPipeline" tests/ --include="*.py"

# Find documentation references
grep -r "UnifiedIngestionPipeline" docs/ --include="*.md"
```

**Expected Output:**
```
src/components/shared/unified_ingestion.py:57:class UnifiedIngestionPipeline:
src/components/shared/unified_ingestion.py:269:def get_unified_pipeline() -> UnifiedIngestionPipeline:
tests/integration/test_unified_ingestion.py:10:from src.components.shared.unified_ingestion import UnifiedIngestionPipeline
scripts/ingest_documents.py:5:from src.components.shared.unified_ingestion import get_unified_pipeline
```

### Step 2: Create Migration Script

Create `scripts/migrate_unified_ingestion.py`:

```python
"""Migration script for UnifiedIngestionPipeline → LangGraph Pipeline.

Usage:
    python scripts/migrate_unified_ingestion.py --dry-run
    python scripts/migrate_unified_ingestion.py --apply
"""

import argparse
from pathlib import Path
import re

MIGRATION_MAP = {
    # Old import → New import
    "from src.components.shared.unified_ingestion import UnifiedIngestionPipeline":
        "from src.components.ingestion.langgraph_pipeline import create_ingestion_graph",

    "from src.components.shared.unified_ingestion import get_unified_pipeline":
        "from src.components.ingestion.langgraph_pipeline import create_ingestion_graph",

    # Old usage → New usage
    "pipeline = UnifiedIngestionPipeline()":
        "pipeline = create_ingestion_graph()",

    "pipeline = get_unified_pipeline()":
        "pipeline = create_ingestion_graph()",

    "await pipeline.ingest_directory(":
        "async for event in pipeline.astream(",
}

def migrate_file(file_path: Path, dry_run: bool = True) -> tuple[bool, list[str]]:
    """Migrate a single file.

    Returns:
        (modified: bool, changes: list[str])
    """
    content = file_path.read_text(encoding="utf-8")
    original = content
    changes = []

    for old_pattern, new_pattern in MIGRATION_MAP.items():
        if old_pattern in content:
            content = content.replace(old_pattern, new_pattern)
            changes.append(f"  - {old_pattern} → {new_pattern}")

    if content != original:
        if not dry_run:
            file_path.write_text(content, encoding="utf-8")
        return True, changes

    return False, []

def main():
    parser = argparse.ArgumentParser(description="Migrate UnifiedIngestionPipeline usage")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    parser.add_argument("--apply", action="store_true", help="Apply changes")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        parser.error("Must specify --dry-run or --apply")

    project_root = Path(__file__).parent.parent
    python_files = list(project_root.glob("src/**/*.py")) + list(project_root.glob("scripts/**/*.py"))

    modified_files = []

    for file_path in python_files:
        modified, changes = migrate_file(file_path, dry_run=args.dry_run)
        if modified:
            modified_files.append((file_path, changes))

    # Print summary
    print(f"\n{'DRY RUN - ' if args.dry_run else ''}Migration Summary:")
    print(f"Files modified: {len(modified_files)}")

    for file_path, changes in modified_files:
        print(f"\n{file_path}:")
        for change in changes:
            print(change)

    if args.dry_run:
        print("\nRun with --apply to make changes")

if __name__ == "__main__":
    main()
```

### Step 3: Run Migration (Dry Run)

```bash
# Preview changes
python scripts/migrate_unified_ingestion.py --dry-run
```

Review output carefully. Expected changes:
- Import statements updated
- Class instantiation updated
- Method calls updated to async streaming

### Step 4: Apply Migration

```bash
# Apply changes
python scripts/migrate_unified_ingestion.py --apply

# Verify changes
git diff src/ scripts/
```

### Step 5: Update Tests

For each test file using `UnifiedIngestionPipeline`:

**Before:**
```python
# tests/integration/test_unified_ingestion.py
from src.components.shared.unified_ingestion import UnifiedIngestionPipeline

async def test_ingestion():
    pipeline = UnifiedIngestionPipeline()
    result = await pipeline.ingest_directory("./data")
    assert result.total_documents > 0
```

**After:**
```python
# tests/integration/test_langgraph_ingestion.py (renamed)
from src.components.ingestion.langgraph_pipeline import create_ingestion_graph
from src.components.ingestion.state import IngestionState

async def test_ingestion():
    pipeline = create_ingestion_graph()
    initial_state = IngestionState(input_dir="./data", documents=[])

    final_state = None
    async for event in pipeline.astream(initial_state):
        # Get final state
        node_name = list(event.keys())[0]
        final_state = event[node_name]

    assert final_state.documents_indexed > 0
```

### Step 6: Archive Deprecated File

```bash
# Create archive directory
mkdir -p archive/deprecated/sprint21

# Move file with timestamp
mv src/components/shared/unified_ingestion.py \
   archive/deprecated/sprint21/unified_ingestion_deprecated_2025-11-11.py

# Add README
cat > archive/deprecated/sprint21/README.md << 'EOF'
# Deprecated Code - Sprint 21

## unified_ingestion.py

**Deprecated:** 2025-11-11
**Reason:** Replaced by LangGraph ingestion pipeline (ADR-027)
**Replacement:** `src/components/ingestion/langgraph_pipeline.py`

**Why deprecated:**
- Parallel execution (asyncio.gather) incompatible with memory constraints
- No support for Docling container lifecycle management
- No SSE progress streaming support
- LangGraph provides better orchestration and error handling

**Migration Guide:** See `docs/refactoring/PRIORITY_1_IMPLEMENTATION_GUIDE.md`
EOF
```

### Step 7: Run Tests

```bash
# Run full test suite
pytest tests/ -v

# Specific ingestion tests
pytest tests/integration/test_langgraph_ingestion.py -v

# Check coverage
pytest tests/ --cov=src/components/ingestion --cov-report=html
```

**Success Criteria:**
- All tests pass
- No imports of `UnifiedIngestionPipeline` in `src/`
- Coverage >80% for ingestion components

### Step 8: Update Documentation

**Files to Update:**
- `docs/architecture/INGESTION_PIPELINE.md`
- `docs/tutorials/DOCUMENT_INGESTION.md`
- `README.md` (if mentioned)
- `CHANGELOG.md` (add breaking change notice)

**Example Changelog Entry:**
```markdown
## [Unreleased] - Sprint 22

### Breaking Changes
- **Removed `UnifiedIngestionPipeline`** (deprecated Sprint 21)
  - **Reason:** Replaced by LangGraph state machine for better orchestration
  - **Migration:** Use `create_ingestion_graph()` from `src.components.ingestion.langgraph_pipeline`
  - **See:** ADR-027, `docs/refactoring/PRIORITY_1_IMPLEMENTATION_GUIDE.md`
```

---

## Task 1.2: Archive Three-Phase Extractor

**File:** `src/components/graph_rag/three_phase_extractor.py`
**Lines:** 350
**Status:** DEPRECATED - ADR-026
**Replacement:** Pure LLM extraction (`extraction_pipeline=llm_extraction`)

### Step 1: Verify No Production Usage

```bash
# Check current default
grep "extraction_pipeline" .env
# Expected: EXTRACTION_PIPELINE=llm_extraction

# Find all three_phase references
grep -r "three_phase" src/ --include="*.py" | grep -v "# DEPRECATED"
grep -r "ThreePhaseExtractor" src/ --include="*.py"

# Check config usage
grep -r "extraction_pipeline.*three_phase" src/ --include="*.py"
```

### Step 2: Update Config to Remove Option

**Before:**
```python
# src/core/config.py
extraction_pipeline: Literal["lightrag_default", "three_phase", "llm_extraction"] = Field(
    default="llm_extraction",
    description=(
        "- 'llm_extraction': Pure LLM (NO SpaCy, high quality) - DEFAULT\n"
        "- 'three_phase': SpaCy + Dedup + Gemma (fast) - DEPRECATED\n"
        "- 'lightrag_default': Legacy baseline"
    ),
)
```

**After:**
```python
# src/core/config.py
extraction_pipeline: Literal["lightrag_default", "llm_extraction"] = Field(
    default="llm_extraction",
    description=(
        "Entity/relation extraction pipeline:\n"
        "- 'llm_extraction': Pure LLM (NO SpaCy, high quality) - DEFAULT (Sprint 21+)\n"
        "- 'lightrag_default': Legacy LightRAG baseline (comparison only)\n"
        "\n"
        "REMOVED Sprint 22: 'three_phase' (SpaCy + Dedup + Gemma)\n"
        "  Reason: Lower quality than pure LLM (ADR-026)\n"
        "  Migration: Use 'llm_extraction' (already default)"
    ),
)
```

### Step 3: Update Extraction Factory

**Before:**
```python
# src/components/graph_rag/extraction_factory.py
def create_extractor(pipeline: str):
    if pipeline == "three_phase":
        from .three_phase_extractor import ThreePhaseExtractor
        return ThreePhaseExtractor()
    elif pipeline == "llm_extraction":
        from .llm_extractor import LLMExtractor
        return LLMExtractor()
    # ...
```

**After:**
```python
# src/components/graph_rag/extraction_factory.py
def create_extractor(pipeline: str):
    if pipeline == "llm_extraction":
        from .llm_extractor import LLMExtractor
        return LLMExtractor()
    elif pipeline == "lightrag_default":
        from .lightrag_wrapper import LightRAGWrapper
        return LightRAGWrapper()
    else:
        raise ValueError(
            f"Unknown extraction pipeline: {pipeline}. "
            f"Valid options: 'llm_extraction', 'lightrag_default'. "
            f"Note: 'three_phase' removed in Sprint 22 (see ADR-026)"
        )
```

### Step 4: Archive File

```bash
# Move to archive
mkdir -p archive/deprecated/sprint22
mv src/components/graph_rag/three_phase_extractor.py \
   archive/deprecated/sprint22/three_phase_extractor_sprint13-20.py

# Create README
cat > archive/deprecated/sprint22/README.md << 'EOF'
# Deprecated: Three-Phase Extraction Pipeline

**Deprecated:** 2025-11-11 (Sprint 22)
**Reason:** ADR-026 - Pure LLM extraction provides higher quality
**Active Period:** Sprint 13-20

## What was Three-Phase?

**Architecture:**
1. Phase 1: SpaCy Transformer NER (~0.5s) - Fast entity extraction
2. Phase 2: Semantic Deduplication (~0.5-1.5s) - Remove duplicates
3. Phase 3: Gemma 3 4B Relation Extraction (~13-16s) - Relations

**Performance:** ~15-17s per document

**Why Deprecated:**
- Lower quality than pure LLM (70% vs 90% precision)
- SpaCy misses domain-specific entities (OMNITRACKER, MSA, etc.)
- German technical terms poorly handled
- False positives (numbers, generic concepts as entities)

**Replacement:** Pure LLM extraction (`extraction_pipeline=llm_extraction`)
- Higher quality (90%+ precision)
- Better domain understanding
- Handles German technical terms
- No SpaCy dependency

**See:** ADR-026 for full rationale
EOF
```

### Step 5: Remove Related Imports

Find and remove unused SpaCy imports:

```bash
# Find SpaCy imports (may still be used elsewhere, verify!)
grep -r "import spacy" src/components/graph_rag/ --include="*.py"

# If only used by three_phase_extractor, remove from pyproject.toml:
# - spacy
# - en_core_web_trf
```

**Note:** Do NOT remove SpaCy if used by other components!

### Step 6: Update Tests

```bash
# Find three_phase tests
find tests/ -name "*three_phase*" -type f

# Update or remove
mv tests/unit/test_three_phase_extractor.py \
   archive/deprecated/sprint22/test_three_phase_extractor.py

# Update integration tests to use llm_extraction only
```

### Step 7: Run Tests

```bash
# Verify extraction still works
pytest tests/integration/test_llm_extraction.py -v

# Full test suite
pytest tests/ -v

# Check no three_phase references remain
grep -r "three_phase" src/ tests/ --include="*.py" | grep -v "DEPRECATED\|removed"
```

---

## Task 1.3: Add LlamaIndex Deprecation Warnings

**File:** `src/components/vector_search/ingestion.py`
**Method:** `load_documents()` (lines 137-163)
**Status:** DEPRECATED - ADR-028
**Replacement:** Docling container client

### Step 1: Add Runtime Warning

```python
# src/components/vector_search/ingestion.py

async def load_documents(
    self,
    input_dir: str | Path,
    required_exts: list[str] | None = None,
    recursive: bool = True,
) -> list[Document]:
    """Load documents from directory.

    ⚠️ DEPRECATED: Sprint 21 - Use DoclingContainerClient instead.

    This method uses LlamaIndex SimpleDirectoryReader, which has limitations:
    - No OCR for scanned PDFs (Docling: 95% OCR accuracy)
    - No table extraction (tables lost in plain text)
    - No GPU acceleration (Docling uses RTX 3060)
    - In-process memory usage (Docling isolated in container)

    Migration:
        >>> # OLD (deprecated)
        >>> docs = await pipeline.load_documents("./data")

        >>> # NEW (recommended)
        >>> from src.components.ingestion.docling_client import DoclingContainerClient
        >>> client = DoclingContainerClient()
        >>> await client.start_container()
        >>> parsed = await client.parse_document(Path("doc.pdf"))
        >>> await client.stop_container()

    See: ADR-028 (LlamaIndex Deprecation Strategy)

    Args:
        input_dir: Directory containing documents
        required_exts: File extensions to load
        recursive: Search subdirectories

    Returns:
        List of LlamaIndex Document objects

    Raises:
        VectorSearchError: If loading fails

    .. deprecated:: Sprint 21
       Use :class:`DoclingContainerClient` instead.
    """
    import warnings

    warnings.warn(
        "DocumentIngestionPipeline.load_documents() is deprecated (Sprint 21). "
        "Use DoclingContainerClient for better OCR, table extraction, and GPU acceleration. "
        "See ADR-028 for migration guide.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Existing implementation continues...
    if required_exts is None:
        required_exts = [".pdf", ".txt", ".md", ".docx", ".csv", ".pptx"]

    # ... rest of method
```

### Step 2: Add Config Flag

```python
# src/core/config.py

class Settings(BaseSettings):
    # ... existing fields

    # LlamaIndex Deprecation (Sprint 21 - ADR-028)
    llamaindex_fallback_enabled: bool = Field(
        default=True,
        description=(
            "Enable LlamaIndex as fallback parser when Docling unavailable. "
            "Primary parser is DoclingContainerClient (ADR-027). "
            "LlamaIndex kept for connectors (Web, Notion, Drive) only."
        ),
    )

    llamaindex_warn_deprecated: bool = Field(
        default=True,
        description="Show deprecation warnings when using LlamaIndex (Sprint 21+)",
    )
```

### Step 3: Update load_documents() to Check Config

```python
async def load_documents(self, ...) -> list[Document]:
    """Load documents from directory."""

    # Check if warnings enabled
    if self.config.llamaindex_warn_deprecated:
        warnings.warn(
            "DocumentIngestionPipeline.load_documents() is deprecated (Sprint 21). "
            "Use DoclingContainerClient instead. "
            "Set LLAMAINDEX_WARN_DEPRECATED=false to suppress this warning.",
            DeprecationWarning,
            stacklevel=2,
        )

    # Rest of implementation...
```

### Step 4: Add Fallback Logic

```python
# src/components/ingestion/document_parser.py (new file)

from pathlib import Path
from typing import Union
import structlog
from src.core.config import get_settings
from src.core.exceptions import IngestionError

logger = structlog.get_logger(__name__)

async def parse_document(
    file_path: Path,
    use_docling: bool = True,
) -> dict:
    """Parse document with fallback to LlamaIndex.

    Args:
        file_path: Path to document
        use_docling: Try Docling first (default: True)

    Returns:
        Parsed document dict with text, metadata, tables, images

    Raises:
        IngestionError: If all parsers fail
    """
    settings = get_settings()

    # Primary: Try Docling
    if use_docling and settings.docling_enabled:
        try:
            from src.components.ingestion.docling_client import DoclingContainerClient

            client = DoclingContainerClient()
            await client.start_container()
            result = await client.parse_document(file_path)
            await client.stop_container()

            logger.info("document_parsed_docling", file=str(file_path))
            return result

        except Exception as e:
            logger.warning(
                "docling_parse_failed_trying_fallback",
                file=str(file_path),
                error=str(e),
            )

    # Fallback: LlamaIndex (if enabled)
    if settings.llamaindex_fallback_enabled:
        try:
            from llama_index.core import SimpleDirectoryReader

            if settings.llamaindex_warn_deprecated:
                import warnings
                warnings.warn(
                    f"Using LlamaIndex fallback for {file_path.name}. "
                    "Consider using Docling for better quality.",
                    DeprecationWarning,
                    stacklevel=2,
                )

            reader = SimpleDirectoryReader(input_files=[str(file_path)])
            docs = reader.load_data()

            logger.info("document_parsed_llamaindex_fallback", file=str(file_path))

            return {
                "text": docs[0].text if docs else "",
                "metadata": docs[0].metadata if docs else {},
                "tables": [],  # LlamaIndex doesn't extract tables
                "images": [],
            }

        except Exception as e:
            logger.error("llamaindex_fallback_failed", file=str(file_path), error=str(e))

    # Both failed
    raise IngestionError(
        f"Failed to parse {file_path}: Docling and LlamaIndex both failed. "
        "Check Docling container status or file format."
    )
```

### Step 5: Test Fallback Behavior

```python
# tests/integration/test_document_parser_fallback.py

import pytest
from pathlib import Path
from src.components.ingestion.document_parser import parse_document
from src.core.config import Settings

@pytest.mark.asyncio
async def test_docling_primary_parser():
    """Test Docling used as primary parser."""
    result = await parse_document(Path("test.pdf"), use_docling=True)
    assert "text" in result
    assert "tables" in result  # Docling extracts tables

@pytest.mark.asyncio
async def test_llamaindex_fallback_when_docling_disabled():
    """Test LlamaIndex used when Docling disabled."""
    # Simulate Docling unavailable
    result = await parse_document(Path("test.txt"), use_docling=False)
    assert "text" in result
    # LlamaIndex doesn't extract tables
    assert result.get("tables") == []

@pytest.mark.asyncio
async def test_deprecation_warning_shown():
    """Test deprecation warning displayed when using LlamaIndex."""
    with pytest.warns(DeprecationWarning, match="LlamaIndex fallback"):
        await parse_document(Path("test.txt"), use_docling=False)
```

---

## Post-Implementation Checklist

After completing all Priority 1 tasks:

### Code Quality
- [ ] All tests pass (`pytest tests/ -v`)
- [ ] No DEPRECATED files in `src/`
- [ ] No imports of removed classes
- [ ] Coverage >80% for affected components
- [ ] Type hints complete (mypy --strict passes)
- [ ] Pre-commit hooks pass

### Documentation
- [ ] CHANGELOG.md updated with breaking changes
- [ ] Migration guides written
- [ ] ADRs referenced correctly
- [ ] README.md updated (if needed)
- [ ] API docs regenerated

### Communication
- [ ] Team notified of breaking changes
- [ ] Migration script provided
- [ ] Estimated migration time communicated
- [ ] Rollback plan documented

### Monitoring
- [ ] Deprecation warnings logged in production
- [ ] Metrics for new vs old code paths
- [ ] Error rates monitored post-deployment

---

## Rollback Plan

If issues arise after deployment:

### Emergency Rollback (< 1 hour)
```bash
# Restore from archive
cp archive/deprecated/sprint21/unified_ingestion_deprecated_2025-11-11.py \
   src/components/shared/unified_ingestion.py

cp archive/deprecated/sprint22/three_phase_extractor_sprint13-20.py \
   src/components/graph_rag/three_phase_extractor.py

# Revert config changes
git checkout HEAD~1 src/core/config.py

# Restart services
docker-compose restart
```

### Permanent Rollback (if new code has issues)
1. Create hotfix branch
2. Revert commits
3. Re-enable deprecated code
4. Schedule proper migration for next sprint
5. Document issues in post-mortem

---

## Success Metrics

**Quantitative:**
- Removed code: ~725 lines
- Test coverage: >80% (maintained or improved)
- Migration time per codebase: <2 hours
- Zero production errors from removals

**Qualitative:**
- Clearer codebase (no deprecated warnings)
- Easier onboarding (single ingestion path)
- Better performance (LangGraph + Docling)
- Reduced maintenance burden

---

**Author:** Backend Agent (Claude Code)
**Status:** Implementation Ready
**Estimated Effort:** 16-20 hours
**Target Completion:** Sprint 22 Week 1
