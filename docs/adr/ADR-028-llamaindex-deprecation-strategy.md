# ADR-028: LlamaIndex Deprecation Strategy

**Status:** ✅ Accepted
**Date:** 2025-11-07
**Sprint:** 21
**Related:** ADR-027 (Docling Container), ADR-022 (Unified Chunking)

---

## Context

### Original Plan (Sprint 1-2)

LlamaIndex was selected as the **primary data ingestion framework** for AegisRAG based on its extensive ecosystem:

**Planned Role:**
```yaml
LlamaIndex: Core Ingestion Framework
  Primary Capabilities:
    - 300+ built-in data connectors
    - Document parsing (PDF, DOCX, HTML, Markdown)
    - Vector store integrations (Qdrant, Pinecone, Weaviate)
    - Embedding pipeline orchestration
    - Query engines and retrievers

  Architecture Position:
    User Data → LlamaIndex → Vector/Graph Storage → Retrieval
```

**Key Dependencies (Sprint 1):**
```toml
# pyproject.toml
llama-index-core = "^0.14.3"
llama-index-readers-file = "^0.5.4"
llama-index-vector-stores-qdrant = "^0.6.2"
llama-index-embeddings-ollama = "^0.5.2"
```

**Architecture Decisions:**
- ADR-001: LangGraph for orchestration
- ADR-004: Qdrant for vector storage
- **Implicit:** LlamaIndex for data loading and indexing

### Changes in Sprint 21

Sprint 21 introduced **Docling CUDA Container** as the primary document parser (ADR-027), fundamentally changing LlamaIndex's role:

**Before Sprint 21:**
```python
# Primary ingestion path (Sprint 1-20)
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex

documents = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(documents)
retriever = index.as_retriever(similarity_top_k=10)
```

**After Sprint 21:**
```python
# New primary ingestion path (Sprint 21+)
from src.components.ingestion.docling_client import DoclingContainerClient
from src.components.ingestion.langgraph_pipeline import IngestionPipeline

client = DoclingContainerClient()
await client.start_container()
parsed = await client.parse_document(Path("document.pdf"))
await client.stop_container()

# LangGraph pipeline handles rest (chunking, embedding, graph extraction)
pipeline = IngestionPipeline()
result = await pipeline.run(parsed)
```

**Impact:**
- LlamaIndex's `SimpleDirectoryReader` **replaced** by Docling for PDF/DOCX
- LlamaIndex's `VectorStoreIndex` **replaced** by custom LangGraph pipeline
- LlamaIndex's role: **Primary → Fallback/Connector Library**

### Decision Drivers

**Why Deprecate LlamaIndex for Primary Ingestion?**

1. **Quality Issues (Sprint 20 Analysis):**
   - Tesseract OCR: 70% accuracy on German technical docs (vs 95% Docling)
   - No layout preservation (tables, headings lost)
   - No GPU acceleration (RTX 3060 6GB unused)

2. **Memory Constraints (Sprint 20):**
   - In-process library shares memory with Ollama/Neo4j (4.6GB baseline)
   - Large PDF processing → OOM crashes
   - No isolation mechanism to free resources

3. **Architectural Fit:**
   - LangGraph became primary orchestration layer (ADR-001)
   - LlamaIndex's opinionated pipeline conflicts with LangGraph control
   - Custom pipeline needed for three-phase extraction (ADR-017, ADR-018)

**Why Keep LlamaIndex in Dependencies?**

1. **300+ Connectors Available:**
   - Web scraping (WebReader)
   - Notion (NotionReader)
   - Google Drive (GoogleDriveReader)
   - Database connectors (SQLDatabaseReader, MongoDBReader)
   - Many others not available in Docling

2. **Fallback for Simple Documents:**
   - Text files, Markdown, simple PDFs
   - When Docling container unavailable

3. **Future Flexibility:**
   - May re-integrate for specific connectors (Sprint 22+)
   - Avoid complete rewrite if Docling issues arise

---

## Decision

**Deprecate LlamaIndex as primary ingestion framework. Retain as optional fallback and connector library.**

### New Role Definition

**LlamaIndex Status: OPTIONAL FALLBACK**

```yaml
Primary Ingestion (Sprint 21+):
  PDF/DOCX: Docling CUDA Container (ADR-027)
  Chunking: Custom ChunkingService (ADR-022)
  Embeddings: Direct Ollama API (BGE-M3)
  Graph Extraction: Custom LightRAG integration (ADR-018)

LlamaIndex Usage (Fallback Only):
  - Web scraping (when needed)
  - Simple text files (TXT, MD)
  - Legacy code compatibility
  - Connector-specific tasks (Notion, Google Drive, etc.)

Deprecated (DO NOT USE):
  - ❌ SimpleDirectoryReader (use Docling)
  - ❌ VectorStoreIndex (use custom pipeline)
  - ❌ Query engines (use custom retrievers)
```

### Configuration

**Environment Variable:**
```bash
# .env
LLAMAINDEX_ENABLED=false          # Disabled by default
LLAMAINDEX_FALLBACK=true          # Available as fallback
DOCLING_ENABLED=true              # Primary parser
```

**Python Config:**
```python
# src/core/config.py
class Settings(BaseSettings):
    llamaindex_enabled: bool = Field(
        default=False,
        description="Enable LlamaIndex for ingestion (deprecated, use Docling)"
    )
    llamaindex_fallback: bool = Field(
        default=True,
        description="Use LlamaIndex as fallback when Docling unavailable"
    )
    docling_enabled: bool = Field(
        default=True,
        description="Use Docling CUDA container for primary ingestion"
    )
```

### Dependencies

**Keep in pyproject.toml (Fallback + Connectors):**
```toml
# Core library (for connectors)
llama-index-core = "^0.14.3"

# File readers (fallback)
llama-index-readers-file = "^0.5.4"

# Optional connectors (install on demand)
# llama-index-readers-web = "^0.3.1"         # Web scraping
# llama-index-readers-notion = "^0.2.4"      # Notion integration
# llama-index-readers-google-drive = "^0.2.1" # Google Drive
```

**Remove from Direct Usage:**
```python
# ❌ DEPRECATED (Sprint 21+)
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex

# ✅ USE INSTEAD
from src.components.ingestion.docling_client import DoclingContainerClient
from src.components.ingestion.langgraph_pipeline import IngestionPipeline
```

---

## Alternatives Considered

### Alternative 1: Complete Removal (Delete from Dependencies)

**Pros:**
- ✅ Simplifies dependency tree
- ✅ Reduces package size (~200MB)
- ✅ Eliminates confusion about which library to use
- ✅ Cleaner architecture (single ingestion path)

**Cons:**
- ❌ Lose access to 300+ connectors
- ❌ No fallback if Docling has issues
- ❌ Need custom implementations for Web/Notion/Drive
- ❌ Breaking changes for existing scripts

**Verdict:** **REJECTED** - Connectors too valuable, fallback needed for reliability.

### Alternative 2: Hybrid Default (LlamaIndex for Simple, Docling for Complex)

**Pros:**
- ✅ Best of both worlds
- ✅ Automatic routing based on file type
- ✅ Leverage LlamaIndex simplicity for TXT/MD
- ✅ Use Docling quality for PDF/DOCX

**Cons:**
- ❌ Complex routing logic (when to use which?)
- ❌ Inconsistent output formats
- ❌ Two parsing paths to maintain
- ❌ Testing complexity (2x integration tests)
- ❌ Confusion for developers (which to use?)

**Verdict:** **REJECTED** - Complexity outweighs benefits. Docling handles all formats adequately.

### Alternative 3: LlamaIndex with Custom OCR Plugin

**Pros:**
- ✅ Keep LlamaIndex as orchestrator
- ✅ Add GPU OCR via custom reader
- ✅ Leverage existing LlamaIndex ecosystem
- ✅ Familiarity for team

**Cons:**
- ❌ High development effort (custom OCR integration)
- ❌ Maintenance burden (OCR updates)
- ❌ Still in-process (no memory isolation)
- ❌ Reinventing Docling (which already does this)

**Verdict:** **REJECTED** - Docling provides better OCR out-of-the-box, not worth custom development.

### Alternative 4: Gradual Migration (Keep LlamaIndex as Primary for 1-2 Sprints)

**Pros:**
- ✅ Lower migration risk
- ✅ Time to evaluate Docling in production
- ✅ Parallel testing of both systems
- ✅ Easy rollback if issues

**Cons:**
- ❌ Delayed quality improvements
- ❌ Dual maintenance burden
- ❌ Confusion about which to use
- ❌ Delayed memory optimization benefits

**Verdict:** **REJECTED** - Docling benefits clear, immediate migration justified.

---

## Rationale

### Why Deprecate Primary Role?

**1. Quality Gap Too Large (Sprint 20 Benchmarks):**

```
Document: OMNITRACKER_Manual.pdf (247 pages, German)

LlamaIndex (Tesseract OCR):
  - OCR Accuracy: 70%
  - Table Detection: 0% (lost)
  - Processing Time: 420 seconds
  - GPU Usage: 0%

Docling (EasyOCR CUDA):
  - OCR Accuracy: 95% (+35%)
  - Table Detection: 92%
  - Processing Time: 120 seconds (-71%)
  - GPU Usage: 85%
```

**Impact:** LlamaIndex quality insufficient for production OMNITRACKER documentation.

**2. Memory Management Superior with Container:**

```python
# LlamaIndex (in-process) - Memory accumulates
documents = SimpleDirectoryReader("./data").load_data()  # Loads all to RAM
# Problem: 50 PDFs × 200 pages → 10GB+ memory → OOM crash

# Docling (container) - Memory controlled
for pdf in pdf_files:
    await docling.start_container()  # +6GB
    result = await docling.parse(pdf)
    await docling.stop_container()   # -6GB (freed!)
# Result: Constant 6GB usage, no accumulation
```

**3. Architectural Alignment:**
- LangGraph (ADR-001) is primary orchestrator
- Custom pipeline needed for three-phase extraction (ADR-017, ADR-018)
- LlamaIndex's opinionated `VectorStoreIndex` conflicts with custom flow

### Why Keep as Fallback?

**1. Connector Ecosystem (300+ Readers):**

```python
# Future Sprint 22+ scenarios
from llama_index.readers.web import SimpleWebPageReader
from llama_index.readers.notion import NotionPageReader
from llama_index.readers.google import GoogleDriveReader

# Web scraping
web_docs = SimpleWebPageReader().load_data(["https://example.com"])

# Notion knowledge base
notion_docs = NotionPageReader(token=...).load_data(page_ids=[...])

# Google Drive integration
drive_docs = GoogleDriveReader().load_data(folder_id="...")
```

**These connectors are not available in Docling!** Maintaining LlamaIndex dependency preserves flexibility.

**2. Fallback Reliability:**

```python
# Graceful degradation when Docling unavailable
async def parse_document(path: Path) -> ParsedDocument:
    if settings.docling_enabled:
        try:
            client = DoclingContainerClient()
            return await client.parse_document(path)
        except DockerNotRunningError:
            logger.warning("Docling unavailable, falling back to LlamaIndex")

    # Fallback to LlamaIndex
    if settings.llamaindex_fallback:
        from llama_index.core import SimpleDirectoryReader
        docs = SimpleDirectoryReader(input_files=[path]).load_data()
        return convert_to_parsed_document(docs[0])

    raise IngestionError("No parser available")
```

**3. Low Cost to Maintain:**
- Dependency already in `pyproject.toml` (~200MB)
- No active development needed
- Only used when explicitly invoked

---

## Consequences

### Positive

✅ **Higher Ingestion Quality:**
- 95% OCR accuracy (vs 70% LlamaIndex)
- Table structure preserved
- Layout detection enabled

✅ **Better Memory Management:**
- Container isolation prevents OOM
- Predictable memory usage
- Batch processing reliable

✅ **GPU Utilization:**
- RTX 3060 6GB now fully used
- 3.5x performance improvement

✅ **Architectural Clarity:**
- LangGraph as single orchestrator
- No conflicting abstraction layers
- Easier to reason about pipeline

### Negative

⚠️ **Learning Curve:**
- Team must learn Docling API (vs familiar LlamaIndex)
- Custom pipeline code (vs LlamaIndex abstractions)

**Mitigation:** Comprehensive documentation (ADR-027, code comments), training sessions.

⚠️ **Connector Workarounds:**
- Web scraping requires fallback to LlamaIndex
- Notion/Drive integrations delayed to Sprint 22+

**Mitigation:** LlamaIndex kept in dependencies for connector use.

⚠️ **Dependency Bloat:**
- Both LlamaIndex + Docling in dependencies (~400MB total)
- Unused LlamaIndex code in package

**Mitigation:** Acceptable cost for fallback reliability and connectors.

### Neutral

🔄 **Migration Path:**
- Existing LlamaIndex scripts still work (if `LLAMAINDEX_ENABLED=true`)
- No immediate breaking changes
- Gradual migration over Sprint 21-22

🔄 **Future Re-Integration:**
- Can re-enable LlamaIndex for specific use cases
- Config-driven toggle (`LLAMAINDEX_ENABLED`)
- No architectural lock-in

---

## Migration Guide

### For Developers

**Old Code (Sprint 1-20):**
```python
# ❌ DEPRECATED
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex

documents = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(documents)
retriever = index.as_retriever()
```

**New Code (Sprint 21+):**
```python
# ✅ RECOMMENDED
from src.components.ingestion.docling_client import DoclingContainerClient
from src.components.ingestion.langgraph_pipeline import IngestionPipeline

client = DoclingContainerClient()
await client.start_container()
parsed = await client.parse_document(Path("document.pdf"))
await client.stop_container()

pipeline = IngestionPipeline()
result = await pipeline.run(parsed)
```

### For Existing Scripts

**Scripts Using LlamaIndex:**
1. Check if Docling can replace functionality
2. If yes: Migrate to Docling + LangGraph
3. If no (e.g., Web scraping): Keep LlamaIndex with explicit flag

**Example: Keep LlamaIndex for Web Scraping:**
```python
# Web scraping still uses LlamaIndex (no Docling equivalent)
from llama_index.readers.web import SimpleWebPageReader

reader = SimpleWebPageReader()
docs = reader.load_data(["https://example.com"])
# Process with custom pipeline (not VectorStoreIndex)
```

### For New Features

**Decision Tree:**
```
Is it PDF/DOCX parsing?
  ├─ YES → Use Docling (ADR-027)
  └─ NO
      ├─ Is it Web/Notion/Drive?
      │   ├─ YES → Use LlamaIndex connector
      │   └─ NO → Use Docling or custom reader
```

---

## Timeline

### Sprint 21 (COMPLETED)
- ✅ Docling as primary parser (ADR-027)
- ✅ LlamaIndex marked as deprecated
- ✅ Fallback mechanism implemented
- ✅ Documentation updated

### Sprint 22 (PLANNED)
- ⏳ Add Web scraping support (LlamaIndex WebReader)
- ⏳ Evaluate Notion integration (LlamaIndex NotionReader)
- ⏳ Update QUICK_START.md with migration guide

### Sprint 23+ (FUTURE)
- 💡 Consider removing LlamaIndex if unused
- 💡 Evaluate alternative connector libraries
- 💡 Monitor Docling roadmap for connector additions

---

## Notes

**Relationship to Other ADRs:**
- **ADR-027:** Docling Container Architecture (why Docling chosen)
- **ADR-022:** Unified Chunking Service (why custom pipeline needed)
- **ADR-026:** Pure LLM Extraction (why LlamaIndex extraction insufficient)

**Deprecation != Deletion:**
- LlamaIndex remains in `pyproject.toml`
- Available for fallback and connectors
- Not deleted to preserve flexibility

**Future Considerations:**
- If Docling adds connectors (Web, Notion, Drive), fully remove LlamaIndex
- If Docling proves unreliable, re-enable LlamaIndex as primary
- Config-driven approach allows easy pivot

---

## References

**External:**
- [LlamaIndex Documentation](https://docs.llamaindex.ai/)
- [LlamaIndex GitHub](https://github.com/run-llama/llama_index)
- [LlamaIndex Data Connectors](https://llamahub.ai/)

**Internal:**
- **ADR-027:** `docs/adr/ADR-027-docling-container-architecture.md`
- **Sprint 21 Plan v2:** `docs/sprints/SPRINT_21_PLAN_v2.md`
- **Drift Analysis:** `docs/DRIFT_ANALYSIS.md` (Section 3.1: Ingestion Stack Evolution)
- **Docling Client:** `src/components/ingestion/docling_client.py`
- **LangGraph Pipeline:** `src/components/ingestion/langgraph_pipeline.py`

---

**Author:** Klaus Pommer + Claude Code (documentation-agent)
**Reviewers:** N/A (Solo Development)
**Last Updated:** 2025-11-10
