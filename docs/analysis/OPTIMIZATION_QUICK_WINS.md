# AegisRAG Ingestion Pipeline - Quick Win Optimizations

**Date:** 2025-11-28
**Context:** Immediate actionable optimizations (1-2 days effort)
**Expected Speedup:** 3-5x overall performance improvement

---

## Quick Win #1: Fix Missing Function (CRITICAL - 30 minutes)

### Problem
`parallel_orchestrator.py` imports `process_single_document` which doesn't exist, causing ImportError at runtime.

### Solution
Add this function to `src/components/ingestion/langgraph_pipeline.py` (after line 414):

```python
async def process_single_document(
    document_path: str,
    document_id: str,
) -> dict[str, Any]:
    """Process single document (convenience wrapper for parallel orchestrator).

    Args:
        document_path: Absolute path to document file
        document_id: Unique document identifier

    Returns:
        dict with:
        - success: bool (True if all stages completed)
        - state: IngestionState (complete pipeline state)
        - error: str | None (error message if failed)

    Example:
        >>> result = await process_single_document(
        ...     document_path="/data/doc.pdf",
        ...     document_id="doc_001"
        ... )
        >>> print(f"Success: {result['success']}")
        >>> print(f"Chunks: {len(result['state']['chunks'])}")
    """
    try:
        state = await run_ingestion_pipeline(
            document_path=document_path,
            document_id=document_id,
            batch_id="parallel_batch",
            batch_index=0,
            total_documents=1,
        )

        # Determine success based on graph extraction status
        success = state.get("graph_status") == "completed"

        return {
            "success": success,
            "state": state,
            "error": state["errors"][0]["message"] if state.get("errors") else None,
        }

    except Exception as e:
        logger.error(
            "process_single_document_failed",
            document_id=document_id,
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "state": {},
            "error": str(e),
        }
```

**Also add to exports** (update line 668):
```python
__all__ = [
    "create_ingestion_graph",
    "run_ingestion_pipeline",
    "run_ingestion_pipeline_streaming",
    "run_batch_ingestion",
    "initialize_pipeline_router",
    "process_single_document",  # ADD THIS
]
```

**Test:**
```bash
poetry run python -c "from src.components.ingestion.langgraph_pipeline import process_single_document; print('OK')"
```

---

## Quick Win #2: Parallelize VLM Image Processing (2 hours, 5-10x speedup)

### Problem
Images processed sequentially (1 at a time). Document with 10 images takes 20-50 seconds.

### Solution
Replace sequential loop with `asyncio.gather` in `src/components/ingestion/langgraph_nodes.py` (lines 870-957):

**BEFORE:**
```python
for idx, picture_item in enumerate(doc.pictures):
    try:
        pil_image = picture_item.get_image()
        enhanced_bbox = None
        if hasattr(picture_item, "prov") and picture_item.prov:
            # Extract bbox...
            enhanced_bbox = {...}

        description = await processor.process_image(
            image=pil_image,
            picture_index=idx,
        )

        if description is None:
            continue

        picture_item.text = description
        vlm_metadata.append({...})

    except Exception as e:
        logger.warning("vlm_image_processing_error", ...)
        continue
```

**AFTER:**
```python
# Prepare all image processing tasks
tasks = []
for idx, picture_item in enumerate(doc.pictures):
    try:
        pil_image = picture_item.get_image()

        # Extract enhanced BBox
        enhanced_bbox = None
        if hasattr(picture_item, "prov") and picture_item.prov:
            prov = picture_item.prov[0]
            page_no = prov.page_no
            page_dim = page_dimensions.get(page_no, {})
            if page_dim:
                enhanced_bbox = {
                    "bbox_absolute": {
                        "left": prov.bbox.l,
                        "top": prov.bbox.t,
                        "right": prov.bbox.r,
                        "bottom": prov.bbox.b,
                    },
                    "page_context": {
                        "page_no": page_no,
                        "page_width": page_dim.get("width", 1),
                        "page_height": page_dim.get("height", 1),
                        "unit": "pt",
                        "dpi": 72,
                        "coord_origin": prov.bbox.coord_origin.value,
                    },
                    "bbox_normalized": {
                        "left": prov.bbox.l / page_dim.get("width", 1),
                        "top": prov.bbox.t / page_dim.get("height", 1),
                        "right": prov.bbox.r / page_dim.get("width", 1),
                        "bottom": prov.bbox.b / page_dim.get("height", 1),
                    },
                }

        # Create task for async processing
        task = asyncio.create_task(
            processor.process_image(
                image=pil_image,
                picture_index=idx,
            )
        )
        tasks.append((idx, picture_item, enhanced_bbox, task))

    except Exception as e:
        logger.warning(
            "vlm_image_preparation_error",
            picture_index=idx,
            error=str(e),
        )
        continue

# Process all images concurrently (limit to 10 at a time to avoid overwhelming API)
MAX_CONCURRENT_VLM = 10
vlm_metadata = []

for i in range(0, len(tasks), MAX_CONCURRENT_VLM):
    batch_tasks = tasks[i:i+MAX_CONCURRENT_VLM]

    # Gather results for this batch
    batch_results = await asyncio.gather(
        *[task for _, _, _, task in batch_tasks],
        return_exceptions=True
    )

    # Process results
    for (idx, picture_item, enhanced_bbox, _), description in zip(batch_tasks, batch_results):
        # Handle exceptions from gather
        if isinstance(description, Exception):
            logger.warning(
                "vlm_image_processing_error",
                picture_index=idx,
                error=str(description),
                action="skipping_image",
            )
            continue

        if description is None:
            logger.debug(
                "vlm_image_filtered",
                picture_index=idx,
                reason="failed_filter_check",
            )
            continue

        # Insert description into DoclingDocument
        if hasattr(picture_item, "caption") and picture_item.caption:
            picture_item.text = f"{picture_item.caption}\n\n{description}"
        else:
            picture_item.text = description

        # Store VLM metadata
        vlm_metadata.append(
            {
                "picture_index": idx,
                "picture_ref": f"#/pictures/{idx}",
                "description": description,
                "bbox_full": enhanced_bbox,
                "vlm_model": "qwen3-vl:4b-instruct",
                "timestamp": time.time(),
            }
        )

        logger.info(
            "vlm_image_processed",
            picture_index=idx,
            description_length=len(description),
            has_bbox=enhanced_bbox is not None,
        )

logger.info(
    "vlm_parallel_processing_complete",
    images_total=len(doc.pictures),
    images_processed=len(vlm_metadata),
    batch_size=MAX_CONCURRENT_VLM,
)
```

**Configuration:** Add to `src/core/config.py`:
```python
class Settings(BaseSettings):
    # ... existing settings ...

    # VLM Performance
    max_concurrent_vlm_calls: int = Field(
        default=10,
        description="Maximum concurrent VLM image processing calls"
    )
```

**Test:**
```bash
# Test with document containing 10 images
# Before: ~20-50 seconds
# After: ~2-5 seconds (10x speedup)
```

---

## Quick Win #3: Pre-warm Docling Container (4 hours, save 5-10s per file)

### Problem
Docling container starts fresh for each batch, wasting 5-10 seconds per file.

### Solution
Start container on server startup and keep alive during ingestion in `src/main.py`:

**Add lifespan manager** (after imports, before app creation):
```python
from contextlib import asynccontextmanager
from src.components.ingestion.docling_client import DoclingClient

# Global Docling client (pre-warmed)
_docling_client: DoclingClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager: pre-warm Docling container."""
    global _docling_client

    logger.info("lifespan_startup_start")

    # Pre-warm Docling container
    try:
        _docling_client = DoclingClient()
        await _docling_client.start_container()
        logger.info("docling_container_prewarmed", status="ready")
    except Exception as e:
        logger.warning("docling_container_prewarm_failed", error=str(e))
        _docling_client = None

    yield  # Application runs here

    # Cleanup on shutdown
    logger.info("lifespan_shutdown_start")
    if _docling_client:
        await _docling_client.stop_container()
        logger.info("docling_container_stopped")

# Update app creation
app = FastAPI(
    title="AegisRAG API",
    version="0.1.0",
    lifespan=lifespan,  # ADD THIS
)
```

**Add getter function:**
```python
def get_prewarmed_docling_client() -> DoclingClient | None:
    """Get pre-warmed Docling client (or None if unavailable).

    Returns:
        DoclingClient instance if pre-warmed, else None
    """
    return _docling_client
```

**Update `src/components/ingestion/langgraph_nodes.py`** (line 451):
```python
# BEFORE
docling = DoclingContainerClient(
    base_url=settings.docling_base_url,
    timeout_seconds=settings.docling_timeout_seconds,
    max_retries=settings.docling_max_retries,
)
await docling.start_container()

# AFTER
from src.main import get_prewarmed_docling_client

docling = get_prewarmed_docling_client()
if docling is None:
    # Fallback: start fresh container (old behavior)
    docling = DoclingContainerClient(
        base_url=settings.docling_base_url,
        timeout_seconds=settings.docling_timeout_seconds,
        max_retries=settings.docling_max_retries,
    )
    await docling.start_container()
    should_stop_container = True
else:
    # Use pre-warmed container (no startup overhead)
    should_stop_container = False
    logger.info("using_prewarmed_docling_container")

try:
    # Parse document
    parsed = await docling.parse_document(doc_path)
finally:
    # Only stop if we started it ourselves
    if should_stop_container:
        await docling.stop_container()
```

**Test:**
```bash
# Start server
poetry run uvicorn src.main:app --reload

# Check logs for:
# "docling_container_prewarmed"

# Test ingestion - should be 5-10s faster
```

---

## Quick Win #4: Increase File Parallelism (1 hour, 2x speedup)

### Problem
Only 3 files processed concurrently. If RAM/VRAM allows, we can do more.

### Solution
Make parallelism configurable in `src/core/config.py`:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Parallel Ingestion
    parallel_files: int = Field(
        default=3,
        description="Maximum concurrent files to process (default 3, increase if RAM allows)"
    )
    parallel_chunks: int = Field(
        default=10,
        description="Maximum concurrent chunk processing (default 10)"
    )
```

**Update `src/components/ingestion/parallel_orchestrator.py`** (line 86):
```python
# BEFORE
def __init__(self, max_workers: int = PARALLEL_FILES, max_chunk_workers: int = PARALLEL_CHUNKS):

# AFTER
def __init__(
    self,
    max_workers: int | None = None,
    max_chunk_workers: int | None = None
):
    from src.core.config import settings

    # Use settings if not explicitly provided
    self.max_workers = max_workers or settings.parallel_files
    self.max_chunk_workers = max_chunk_workers or settings.parallel_chunks
```

**Configuration** (add to `.env`):
```bash
# Increase if you have >16GB RAM and 8GB+ VRAM
PARALLEL_FILES=5  # was 3 (67% more parallelism)
PARALLEL_CHUNKS=15  # was 10 (50% more parallelism)
```

**Test:**
```bash
# Monitor RAM/VRAM during ingestion
watch -n 1 nvidia-smi  # VRAM
watch -n 1 free -h     # RAM

# If no OOM → increase further
# If OOM → decrease
```

---

## Quick Win #5: Add Performance Logging (2 hours, monitoring)

### Problem
Can't identify slowest stages without detailed logging.

### Solution
Already implemented in Sprint 33! Just verify logs are working.

**Verify logging** in `src/components/ingestion/langgraph_pipeline.py` (lines 357-403):
```bash
# Check logs for these messages:
grep "TIMING_pipeline_execution_start" logs/aegisrag.log
grep "TIMING_node_" logs/aegisrag.log
grep "TIMING_pipeline_complete" logs/aegisrag.log
```

**Expected output:**
```
TIMING_pipeline_execution_start document_id=doc123 document_name=report.pdf
TIMING_node_memory_check document_id=doc123 node=memory_check duration_seconds=0.12
TIMING_node_parse document_id=doc123 node=parse duration_seconds=45.3
TIMING_node_chunking document_id=doc123 node=chunking duration_seconds=0.8
TIMING_node_embedding document_id=doc123 node=embedding duration_seconds=12.4
TIMING_node_graph document_id=doc123 node=graph duration_seconds=28.6
TIMING_pipeline_complete total_seconds=87.22 slowest_node=parse
```

**Add Prometheus metrics** (optional, 1 hour):
```python
# In src/core/metrics.py
from prometheus_client import Histogram

ingestion_node_duration = Histogram(
    "aegis_ingestion_node_duration_seconds",
    "Time spent in each ingestion node",
    ["node_name", "document_type"],
    buckets=[0.1, 0.5, 1, 5, 10, 30, 60, 120, 300]
)

# In langgraph_pipeline.py after each node
ingestion_node_duration.labels(
    node_name=node_name,
    document_type=file_path.suffix
).observe(node_duration)
```

---

## Testing Checklist

After implementing each quick win, verify:

### Functional Tests
- [ ] `process_single_document` function imports correctly
- [ ] Parallel VLM processing returns correct descriptions
- [ ] Pre-warmed Docling container accepts requests
- [ ] Increased parallelism doesn't cause OOM
- [ ] Timing logs appear in output

### Performance Tests
- [ ] Single document (10 pages, 5 images): <30s (was 65-230s)
- [ ] Batch (10 documents): <2 minutes (was 10-40 minutes)
- [ ] Memory usage: <8GB RAM, <6GB VRAM
- [ ] No errors in logs

### Benchmark Script
```python
import asyncio
import time
from pathlib import Path
from src.components.ingestion.langgraph_pipeline import process_single_document

async def benchmark():
    start = time.time()
    result = await process_single_document(
        document_path="/data/test_doc.pdf",
        document_id="benchmark_001"
    )
    duration = time.time() - start

    print(f"Duration: {duration:.2f}s")
    print(f"Success: {result['success']}")
    print(f"Chunks: {len(result['state']['chunks'])}")

asyncio.run(benchmark())
```

---

## Expected Results

| Metric | Before | After Quick Wins | Improvement |
|--------|--------|------------------|-------------|
| Single PDF (10 pages) | 65-230s | 20-60s | 3-4x faster |
| Batch (10 PDFs) | 650-2300s | 200-600s | 3-4x faster |
| VLM (10 images) | 20-50s | 2-5s | 10x faster |
| Container startup | 5-10s per file | 0s (pre-warmed) | Eliminated |
| File parallelism | 3 files | 5 files | 67% more |

**Overall speedup:** 3-5x
**Time to implement:** 1-2 days
**Risk:** LOW (no breaking changes)

---

## Next Steps (After Quick Wins)

Once quick wins are implemented and tested:

1. **Measure impact:** Run benchmarks, compare with baseline
2. **Identify remaining bottlenecks:** Check timing logs for slowest nodes
3. **Implement medium wins:** Batch Neo4j queries, parallelize embeddings
4. **Consider major improvements:** Chunk-level parallelism, pipeline parallelism

See `INGESTION_PERFORMANCE_ANALYSIS.md` for complete roadmap.
