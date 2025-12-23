# Sprint 21 - Feature 21.6: Image-Enhanced Document Ingestion - Implementation Progress

**Feature:** 21.6 - Image-Enhanced Document Ingestion with VLM
**Status:** 🔄 IN PROGRESS (40% complete)
**Started:** 2025-11-08
**Last Updated:** 2025-11-08
**Estimated Completion:** 6-7 days remaining

---

## 📋 Executive Summary

Feature 21.6 integriert Qwen3-VL-4B für intelligente Bildbeschreibungen in die Dokumenten-Ingestion-Pipeline mit vollständiger BBox-Provenance-Tracking und On-Demand Frontend-Visualisierung.

**Kernarchitektur:**
- Docling extrahiert Dokument-Struktur + Bilder mit BBox
- Qwen3-VL beschreibt Bilder (nur Bilder, nicht Volltext!)
- VLM-Text wird **IN DoclingDocument eingefügt** (NICHT separate Chunks)
- HybridChunker erstellt kontextualisierte Chunks mit Hierarchie
- Qdrant speichert vollständige BBox-Provenance
- Neo4j speichert minimale Provenance mit Referenz zu Qdrant

---

## ✅ Completed Tasks (40%)

### 1. ✅ Sprint Plan Update
**File:** `docs/sprints/SPRINT_21_PLAN_v2.md`

**Changes:**
- Feature 21.4 (alt: Chunking Strategy) entfernt und als "TBD" markiert
- Feature 21.5 (Tables, Images & Layout Extraction) dokumentiert (✅ COMPLETED)
- Feature 21.6 (Image-Enhanced Document Ingestion with VLM) hinzugefügt mit vollständiger Spezifikation

**Key Sections:**
```markdown
### Feature 21.6: Image-Enhanced Document Ingestion with VLM (55 SP)
- Critical Architecture Decisions documented
- Pipeline Architecture (5 stages)
- Technology Stack (Docling, Qwen3-VL, HybridChunker, BGE-M3)
- Key Data Structures (EnhancedBBox, Qdrant Payload, Neo4j Entity)
- API Endpoints (Unified Search, On-Demand Annotations)
- Configuration (ingestion_config.yaml)
- Performance Targets (5-10 min/doc with 5-10 images)
- Acceptance Criteria (10 items)
```

**Location:** Lines 937-1261 in `SPRINT_21_PLAN_v2.md`

---

### 2. ✅ LangGraph State Schema Extension
**File:** `src/components/ingestion/ingestion_state.py`

**Changes Made:**

#### Header Update:
```python
"""LangGraph Ingestion State Schema - Sprint 21 Feature 21.6.

Feature 21.6: Image-Enhanced Document Ingestion with VLM

This module defines the state structure for the image-enhanced LangGraph ingestion pipeline.
The state is passed through all 5 nodes sequentially:

1. docling_extraction   → Parse document with Docling container, extract BBox + page dimensions
2. image_enrichment     → Qwen3-VL generates image descriptions, insert INTO DoclingDocument
3. chunking             → HybridChunker with BGE-M3, map BBox to chunks
4. embedding            → Embed with BGE-M3, store full provenance in Qdrant
5. graph_extraction     → Extract entities/relations, store minimal provenance in Neo4j
```

#### New State Fields Added:
```python
class IngestionState(TypedDict, total=False):
    # NODE 2: DOCLING PARSING (Feature 21.6)
    document: Any  # DoclingDocument object (main object for VLM enrichment)
    page_dimensions: dict[int, dict]  # {page_no: {width, height, unit, dpi}}
    # ... existing fields ...

    # NODE 2.5: VLM IMAGE ENRICHMENT (Feature 21.6)
    vlm_metadata: list[dict]  # List of VLM metadata with BBox
    enrichment_status: Literal["pending", "running", "completed", "failed"]
```

#### Updated Progress Calculation:
```python
def calculate_progress(state: IngestionState) -> float:
    """Progress weights (Feature 21.6):
    - memory_check: 5%
    - docling:      20%   (reduced from 25%)
    - vlm enrichment: 15% (NEW)
    - chunking:     15%   (unchanged)
    - embedding:    25%   (reduced from 30%)
    - graph:        20%   (reduced from 25%)
    """
```

#### Updated Initialization:
```python
def create_initial_state(...):
    return IngestionState(
        # ... existing fields ...

        # Docling parsing (initialized by docling_extraction_node)
        document=None,  # DoclingDocument object
        page_dimensions={},  # Page metadata
        # ... existing fields ...

        # VLM enrichment (initialized by image_enrichment_node)
        vlm_metadata=[],
        enrichment_status="pending",
    )
```

**Lines Modified:** 1-40 (header), 135-148 (state fields), 238-249 (initialization), 279-339 (progress calculation)

---

### 3. ✅ Qwen3-VL Image Processor Implementation
**File:** `src/components/ingestion/image_processor.py` (NEW)

**Implemented Components:**

#### A. Configuration Class
```python
class ImageProcessorConfig:
    """Configuration for image processing."""

    def __init__(self):
        settings = get_settings()

        # VLM Settings (Qwen3-VL defaults)
        self.vlm_model = "qwen3-vl:4b-instruct"
        self.temperature = 0.7  # Qwen3-VL default
        self.top_p = 0.8
        self.top_k = 20
        self.num_ctx = 4096

        # Image Filtering
        self.min_size = 100
        self.min_aspect_ratio = 0.1
        self.max_aspect_ratio = 10.0
```

#### B. Image Filtering Function
```python
def should_process_image(
    image: Image.Image,
    min_size: int = 100,
    min_aspect_ratio: float = 0.1,
    max_aspect_ratio: float = 10.0,
) -> Tuple[bool, str]:
    """Determine if an image should be processed by VLM.

    Returns:
        Tuple of (should_process: bool, reason: str)
    """
```

**Filters:**
- Minimum size: 100x100 pixels
- Aspect ratio: 0.1 to 10.0 (prevents very thin/wide images)

#### C. VLM Description Generation
```python
def generate_vlm_description(
    image_path: Path,
    model: str = "qwen3-vl:4b-instruct",
    temperature: float = 0.7,
    top_p: float = 0.8,
    top_k: int = 20,
    num_ctx: int = 4096,
    prompt_template: Optional[str] = None,
) -> str:
    """Generate image description using Qwen3-VL via Ollama.

    Qwen3-VL Best Practice:
    - Use simple, natural language prompts
    - Do NOT use complex JSON instructions
    - Default temperature: 0.7 (model default)
    """
```

**Default Prompt (Qwen3-VL Best Practice):**
```
"Describe this image from a document in detail, including any text,
 diagrams, charts, or important visual elements."
```

#### D. ImageProcessor Class
```python
class ImageProcessor:
    """Image processor for VLM-enhanced document ingestion.

    Handles:
    - Image filtering (size, aspect ratio)
    - Temporary file management
    - VLM description generation via Ollama
    - Error handling and logging
    """

    def process_image(
        self,
        image: Image.Image,
        picture_index: int,
        skip_filtering: bool = False,
    ) -> Optional[str]:
        """Process a single image with VLM.

        Workflow:
        1. Filter image (size, aspect ratio)
        2. Save to temp file
        3. Generate VLM description via Ollama
        4. Cleanup temp file
        5. Return description or None
        """
```

**Features:**
- Automatic temp directory creation (`/tmp/aegis_vlm_images`)
- Safe temp file cleanup (in finally block)
- Comprehensive logging with structlog
- Error handling with optional fallback

#### E. Convenience Function
```python
def process_image_with_vlm(
    image: Image.Image,
    picture_index: int = 0,
    model: str = "qwen3-vl:4b-instruct",
    skip_filtering: bool = False,
) -> Optional[str]:
    """Convenience function to process a single image."""
```

**Total Lines:** 415 lines (well-documented, production-ready)

**Dependencies:**
- `ollama` (VLM client)
- `PIL` (Image processing)
- `structlog` (Logging)
- `src.core.config` (Settings)

---

## 🔄 In Progress Tasks (20%)

### 4. 🔄 LangGraph Nodes - VLM Image Enrichment Node
**File:** `src/components/ingestion/langgraph_nodes.py`

**Status:** Header updated, node implementation pending

**What Needs to Be Done:**

#### A. Update Module Header
```python
"""LangGraph Ingestion Pipeline Nodes - Sprint 21 Feature 21.6.

This module implements the 6 nodes of the image-enhanced LangGraph ingestion pipeline:

1. memory_check_node       → Check RAM/VRAM availability
2. docling_extraction_node → Parse document with Docling, extract BBox + page dimensions
3. image_enrichment_node   → Qwen3-VL image descriptions (NEW - Feature 21.6)
4. chunking_node          → HybridChunker with BGE-M3, map BBox to chunks
5. embedding_node         → Generate BGE-M3 vectors → Qdrant with full provenance
6. graph_extraction_node  → Extract entities/relations → Neo4j with minimal provenance
"""
```

#### B. Add Import for Image Processor
```python
from src.components.ingestion.image_processor import ImageProcessor
```

#### C. Implement image_enrichment_node
**Location:** Insert between `docling_extraction_node` (line 171) and `chunking_node` (line 276)

**Pseudo-code Structure:**
```python
async def image_enrichment_node(state: IngestionState) -> IngestionState:
    """Node 2.5: VLM Image Enrichment (Feature 21.6).

    CRITICAL: VLM-Text wird IN DoclingDocument eingefügt!

    Workflow:
    1. Get DoclingDocument from state
    2. For each picture_item in document.pictures:
       a. Filter image (size, aspect ratio)
       b. Extract BBox with page context
       c. Generate VLM description
       d. INSERT description INTO picture_item.text
       e. Store VLM metadata with enhanced BBox
    3. Update state with enriched document + VLM metadata

    Args:
        state: Current ingestion state

    Returns:
        Updated state with enriched document
    """

    logger.info("node_vlm_enrichment_start", document_id=state["document_id"])

    state["enrichment_status"] = "running"

    try:
        # 1. Get DoclingDocument
        doc = state.get("document")
        if doc is None:
            raise IngestionError("No DoclingDocument in state")

        page_dimensions = state.get("page_dimensions", {})
        vlm_metadata = []

        # 2. Initialize ImageProcessor
        processor = ImageProcessor()

        try:
            # 3. Process each picture
            for idx, picture_item in enumerate(doc.pictures):
                # 3a. Get PIL image
                pil_image = picture_item.get_image()

                # 3b. Filter image
                # (handled by processor.process_image)

                # 3c. Extract enhanced BBox
                enhanced_bbox = None
                if picture_item.prov:
                    prov = picture_item.prov[0]
                    page_no = prov.page_no
                    page_dim = page_dimensions.get(page_no, {})

                    enhanced_bbox = {
                        'bbox_absolute': {
                            'left': prov.bbox.l,
                            'top': prov.bbox.t,
                            'right': prov.bbox.r,
                            'bottom': prov.bbox.b
                        },
                        'page_context': {
                            'page_no': page_no,
                            'page_width': page_dim.get('width'),
                            'page_height': page_dim.get('height'),
                            'unit': 'pt',
                            'dpi': 72,
                            'coord_origin': prov.bbox.coord_origin.value
                        },
                        'bbox_normalized': {
                            'left': prov.bbox.l / page_dim.get('width', 1),
                            'top': prov.bbox.t / page_dim.get('height', 1),
                            'right': prov.bbox.r / page_dim.get('width', 1),
                            'bottom': prov.bbox.b / page_dim.get('height', 1)
                        }
                    }

                # 3d. Generate VLM description
                description = processor.process_image(
                    image=pil_image,
                    picture_index=idx,
                )

                if description is None:
                    # Image filtered out
                    continue

                # 3e. INSERT INTO DoclingDocument (CRITICAL!)
                if picture_item.caption:
                    picture_item.text = f"{picture_item.caption}\n\n{description}"
                else:
                    picture_item.text = description

                # 3f. Store VLM metadata
                vlm_metadata.append({
                    'picture_index': idx,
                    'picture_ref': f'#/pictures/{idx}',
                    'description': description,
                    'bbox_full': enhanced_bbox,
                    'vlm_model': 'qwen3-vl:4b-instruct',
                    'timestamp': datetime.now().isoformat(),
                })

                logger.info(
                    "vlm_image_processed",
                    picture_index=idx,
                    description_length=len(description),
                )

        finally:
            # Cleanup
            processor.cleanup()

        # 4. Update state
        state["document"] = doc  # Enriched document
        state["vlm_metadata"] = vlm_metadata
        state["enrichment_status"] = "completed"
        state["overall_progress"] = calculate_progress(state)

        logger.info(
            "node_vlm_enrichment_complete",
            document_id=state["document_id"],
            images_processed=len(vlm_metadata),
        )

        return state

    except Exception as e:
        logger.error("node_vlm_enrichment_error", document_id=state["document_id"], error=str(e))
        add_error(state, "vlm_enrichment", str(e), "error")
        state["enrichment_status"] = "failed"
        raise
```

**Estimated Lines:** ~150 lines

---

## ⏸️ Pending Tasks (40%)

### 5. ⏸️ Update docling_extraction_node
**File:** `src/components/ingestion/langgraph_nodes.py`

**Current Node:** `docling_parse_node` (lines 171-268)

**Required Changes:**

#### A. Rename Node
```python
# OLD: docling_parse_node
# NEW: docling_extraction_node
async def docling_extraction_node(state: IngestionState) -> IngestionState:
```

#### B. Store DoclingDocument Object
```python
# Current (line 231):
state["parsed_content"] = parsed.text

# NEW (Feature 21.6):
state["document"] = parsed.document  # ← DoclingDocument object
state["parsed_content"] = parsed.text  # Keep for backwards compatibility
```

#### C. Extract Page Dimensions
```python
# NEW: Extract page dimensions for BBox normalization
page_dimensions = {}
for page in parsed.document.pages:
    page_dimensions[page.page_no] = {
        'width': page.size.width,
        'height': page.size.height,
        'unit': 'pt',
        'dpi': 72
    }

state["page_dimensions"] = page_dimensions
```

**Estimated Changes:** 10-15 lines

---

### 6. ⏸️ Update chunking_node
**File:** `src/components/ingestion/langgraph_nodes.py`

**Current Node:** `chunking_node` (lines 276-345)

**Required Changes:**

#### A. Use Enriched DoclingDocument
```python
# Current (line 305):
content = state.get("parsed_content", "")

# NEW (Feature 21.6):
# Use enriched DoclingDocument instead of plain text
enriched_doc = state.get("document")
if enriched_doc is None:
    # Fallback to parsed_content
    content = state.get("parsed_content", "")
```

#### B. Replace Chunking Service with HybridChunker
```python
# Current (lines 310-323):
chunk_strategy = ChunkStrategy(...)
chunking_service = get_chunking_service(strategy=chunk_strategy)
chunks = chunking_service.chunk_document(...)

# NEW (Feature 21.6):
from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer

tokenizer = HuggingFaceTokenizer(
    tokenizer=AutoTokenizer.from_pretrained("BAAI/bge-m3"),
    max_tokens=8192  # BGE-M3 context window
)

chunker = HybridChunker(
    tokenizer=tokenizer,
    merge_peers=True
)

base_chunks = list(chunker.chunk(enriched_doc))
```

#### C. Map BBox to Chunks
```python
# NEW: Create VLM lookup
vlm_metadata = state.get("vlm_metadata", [])
vlm_lookup = {vm['picture_ref']: vm for vm in vlm_metadata}

# NEW: Enhance chunks with BBox information
enhanced_chunks = []
for chunk in base_chunks:
    # Find picture references in chunk
    picture_refs = [
        ref for ref in chunk.meta.doc_items
        if ref.startswith('#/pictures/')
    ]

    # Collect BBox info
    chunk_bboxes = []
    for pic_ref in picture_refs:
        if pic_ref in vlm_lookup:
            vlm_info = vlm_lookup[pic_ref]
            chunk_bboxes.append({
                'picture_ref': pic_ref,
                'description': vlm_info['description'],
                'bbox_full': vlm_info['bbox_full'],
                'vlm_model': vlm_info['vlm_model']
            })

    enhanced_chunk = {
        'chunk': chunk,
        'image_bboxes': chunk_bboxes
    }
    enhanced_chunks.append(enhanced_chunk)

state["chunks"] = enhanced_chunks
```

**Estimated Changes:** 40-50 lines

---

### 7. ⏸️ Update embedding_node
**File:** `src/components/ingestion/langgraph_nodes.py`

**Current Node:** `embedding_node` (lines 353-449)

**Required Changes:**

#### A. Handle Enhanced Chunks
```python
# Current (line 385):
chunks = state.get("chunks", [])

# NEW (Feature 21.6):
chunk_data_list = state.get("chunks", [])  # Now list of {chunk, image_bboxes}
```

#### B. Extract Contextualized Text
```python
# NEW: Use chunk.contextualize() for hierarchical context
texts = []
for chunk_data in chunk_data_list:
    chunk = chunk_data['chunk']
    contextualized_text = chunk.contextualize()  # Includes headings, captions, page
    texts.append(contextualized_text)
```

#### C. Create Qdrant Payload with Full Provenance
```python
# Current (line 413-418):
point = PointStruct(
    id=chunk.chunk_id,
    vector=embedding,
    payload=chunk.to_qdrant_payload(),
)

# NEW (Feature 21.6):
chunk_id = f"{state['document_id']}_chunk_{hash(chunk.text)[:8]}"

payload = {
    # Content
    "content": chunk.text,
    "contextualized_content": contextualized_text,

    # Document Provenance
    "document_id": state["document_id"],
    "document_path": state["document_path"],
    "page_no": chunk.meta.page_no,
    "headings": chunk.meta.headings,
    "chunk_id": chunk_id,

    # Page Dimensions
    "page_dimensions": state["page_dimensions"].get(chunk.meta.page_no),

    # Image Annotations with BBox (CRITICAL!)
    "contains_images": len(chunk_data['image_bboxes']) > 0,
    "image_annotations": [
        {
            "description": img['description'],
            "vlm_model": img['vlm_model'],
            "bbox_absolute": img['bbox_full']['bbox_absolute'],
            "page_context": img['bbox_full']['page_context'],
            "bbox_normalized": img['bbox_full']['bbox_normalized']
        }
        for img in chunk_data['image_bboxes']
    ],

    # Timestamps
    "ingestion_timestamp": datetime.now().isoformat()
}

point = PointStruct(
    id=chunk_id,
    vector=embedding,
    payload=payload,
)
```

**Estimated Changes:** 30-40 lines

---

### 8. ⏸️ Update graph_extraction_node
**File:** `src/components/ingestion/langgraph_nodes.py`

**Current Node:** `graph_extraction_node` (lines 457-541)

**Required Changes:**

#### A. Handle Enhanced Chunks
```python
# Current (line 494):
chunks = state.get("chunks", [])

# NEW (Feature 21.6):
chunk_data_list = state.get("chunks", [])
```

#### B. Create Entities with Minimal Provenance
```python
# Current (lines 502-511):
lightrag_docs = []
for chunk in chunks:
    lightrag_docs.append({
        "text": chunk.content,
        "id": chunk.chunk_id,
        "metadata": chunk.metadata,
    })

# NEW (Feature 21.6):
lightrag_docs = []
for chunk_data in chunk_data_list:
    chunk = chunk_data['chunk']
    image_bboxes = chunk_data['image_bboxes']

    chunk_id = f"{state['document_id']}_chunk_{hash(chunk.text)[:8]}"

    # Add minimal provenance to metadata
    metadata = {
        **chunk.metadata,
        'qdrant_point_id': chunk_id,
        'has_image_annotation': len(image_bboxes) > 0,
        'image_page_nos': [
            bbox['bbox_full']['page_context']['page_no']
            for bbox in image_bboxes
        ] if image_bboxes else []
    }

    lightrag_docs.append({
        "text": chunk.content,
        "id": chunk_id,
        "metadata": metadata,
    })
```

**Estimated Changes:** 15-20 lines

---

### 9. ⏸️ Create ingestion_config.yaml
**File:** `ingestion_config.yaml` (NEW, root directory)

**Full Content:**
```yaml
# Feature 21.6: Image-Enhanced Document Ingestion Configuration

docling:
  container_name: "aegis-docling"
  port: 5001
  memory_limit: "2g"
  options:
    do_ocr: true
    generate_picture_images: true
    images_scale: 2.0
    do_table_structure: true

qwen3vl:
  model: "qwen3-vl:4b-instruct"
  temperature: 0.7
  top_p: 0.8
  top_k: 20
  num_ctx: 4096

image_filtering:
  min_size: 100
  min_aspect_ratio: 0.1
  max_aspect_ratio: 10

chunking:
  tokenizer_model: "BAAI/bge-m3"
  max_tokens: 8192
  merge_peers: true

embedding:
  model: "bge-m3"
  batch_size: 32

graph:
  llm_model: "qwen2.5:3b"
  temperature: 0.1
```

**Estimated Lines:** 35 lines

---

### 10. ⏸️ Update Docker Compose
**File:** `docker-compose.yml`

**Add Docling Service:**
```yaml
services:
  # ... existing services ...

  docling:
    image: quay.io/docling-project/docling-serve
    container_name: aegis-docling
    ports:
      - "5001:5001"
    volumes:
      - docling_cache:/root/.cache
      - ./temp/docling-images:/tmp/images
    mem_limit: 2g
    restart: "no"  # Manual start/stop via LangGraph
    profiles:
      - ingestion

volumes:
  # ... existing volumes ...
  docling_cache:
    driver: local
```

**Estimated Changes:** 15 lines

---

### 11. ⏸️ Update src/core/config.py
**File:** `src/core/config.py`

**Add VLM Configuration:**
```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Feature 21.6: VLM Image Processing
    qwen3vl_model: str = "qwen3-vl:4b-instruct"
    qwen3vl_temperature: float = 0.7
    qwen3vl_top_p: float = 0.8
    qwen3vl_top_k: int = 20
    qwen3vl_num_ctx: int = 4096

    # Image Filtering
    image_min_size: int = 100
    image_min_aspect_ratio: float = 0.1
    image_max_aspect_ratio: float = 10.0

    # Chunking (BGE-M3)
    chunking_tokenizer_model: str = "BAAI/bge-m3"
    chunking_max_tokens: int = 8192
    chunking_merge_peers: bool = True
```

**Estimated Changes:** 15 lines

---

### 12. ⏸️ API Endpoints
**File:** `src/api/v1/annotations.py` (NEW)

**Endpoints to Implement:**

#### A. Unified Search Endpoint (Update existing)
```python
@router.post("/api/search")
async def unified_search(
    query: str,
    search_type: Literal["vector", "graph", "hybrid"] = "hybrid",
    include_annotations: bool = False  # NEW parameter
):
    """Unified search with optional annotation enrichment."""
```

#### B. On-Demand Annotations Endpoint
```python
@router.get("/api/document/{document_id}/annotations")
async def get_document_annotations(
    document_id: str,
    chunk_ids: Optional[List[str]] = Query(None),
    page_no: Optional[int] = None
):
    """Get image annotations for PDF rendering (on-demand).

    Returns:
        {
            "document_id": str,
            "annotations_by_page": {
                "15": {
                    "page_dimensions": {...},
                    "annotations": [...]
                }
            }
        }
    """
```

**Estimated Lines:** 100 lines

---

### 13. ⏸️ Unit Tests
**Files to Create:**

#### A. `tests/unit/components/ingestion/test_image_processor.py`
```python
"""Unit tests for ImageProcessor."""

def test_should_process_image_valid():
    """Test image filtering with valid image."""

def test_should_process_image_too_small():
    """Test image filtering with too small image."""

def test_should_process_image_aspect_ratio():
    """Test image filtering with invalid aspect ratio."""

def test_generate_vlm_description_mock():
    """Test VLM description generation (mocked Ollama)."""

def test_image_processor_process_image():
    """Test ImageProcessor.process_image()."""

def test_image_processor_cleanup():
    """Test temp directory cleanup."""
```

**Estimated:** 6 tests, ~150 lines

#### B. `tests/unit/components/ingestion/test_langgraph_nodes_vlm.py`
```python
"""Unit tests for VLM-enhanced LangGraph nodes."""

async def test_image_enrichment_node_success():
    """Test image_enrichment_node with valid input."""

async def test_image_enrichment_node_no_images():
    """Test image_enrichment_node with no images."""

async def test_image_enrichment_node_error():
    """Test image_enrichment_node error handling."""

async def test_chunking_node_with_vlm():
    """Test chunking_node with VLM-enriched document."""

async def test_embedding_node_with_bbox():
    """Test embedding_node with BBox payload."""
```

**Estimated:** 5 tests, ~200 lines

---

### 14. ⏸️ Integration Tests
**File:** `tests/integration/components/ingestion/test_image_pipeline.py` (NEW)

```python
"""Integration tests for Feature 21.6 end-to-end pipeline."""

@pytest.mark.integration
@pytest.mark.asyncio
async def test_vlm_pipeline_end_to_end():
    """Test complete pipeline with VLM enrichment.

    Uses: retired_13.pdf (has images)
    """

@pytest.mark.integration
@pytest.mark.asyncio
async def test_vlm_bbox_provenance():
    """Test BBox provenance through entire pipeline."""

@pytest.mark.integration
@pytest.mark.asyncio
async def test_on_demand_annotations_api():
    """Test on-demand annotation retrieval."""
```

**Estimated:** 3 tests, ~250 lines

---

## 📊 Progress Summary

| Component | Status | Completion | Estimated Remaining |
|-----------|--------|------------|-------------------|
| Sprint Plan Update | ✅ Complete | 100% | 0 hours |
| LangGraph State Schema | ✅ Complete | 100% | 0 hours |
| Qwen3-VL Image Processor | ✅ Complete | 100% | 0 hours |
| VLM Image Enrichment Node | 🔄 In Progress | 20% | 3 hours |
| Update Docling Extraction Node | ⏸️ Pending | 0% | 1 hour |
| Update Chunking Node | ⏸️ Pending | 0% | 2 hours |
| Update Embedding Node | ⏸️ Pending | 0% | 2 hours |
| Update Graph Extraction Node | ⏸️ Pending | 0% | 1 hour |
| Configuration Files | ⏸️ Pending | 0% | 1 hour |
| API Endpoints | ⏸️ Pending | 0% | 3 hours |
| Unit Tests | ⏸️ Pending | 0% | 4 hours |
| Integration Tests | ⏸️ Pending | 0% | 3 hours |
| Documentation | ⏸️ Pending | 0% | 2 hours |
| **TOTAL** | **🔄 In Progress** | **40%** | **22 hours (~3 days)** |

---

## 🎯 Next Session Action Items

### Priority 1: Complete VLM Node Implementation (3 hours)
1. Open `src/components/ingestion/langgraph_nodes.py`
2. Add import: `from src.components.ingestion.image_processor import ImageProcessor`
3. Insert `image_enrichment_node` after `docling_extraction_node` (around line 270)
4. Test with: `pytest tests/unit/components/ingestion/test_langgraph_nodes_vlm.py -v`

**Verification:**
```bash
python -c "from src.components.ingestion.langgraph_nodes import image_enrichment_node; print('✅ VLM node imported')"
```

### Priority 2: Update Existing Nodes (6 hours)
1. Update `docling_extraction_node` (store `document` + `page_dimensions`)
2. Update `chunking_node` (HybridChunker + BBox mapping)
3. Update `embedding_node` (full provenance payload)
4. Update `graph_extraction_node` (minimal provenance)

**Verification:**
```bash
pytest tests/unit/components/ingestion/test_langgraph_nodes_vlm.py::test_chunking_node_with_vlm -v
```

### Priority 3: Configuration & API (4 hours)
1. Create `ingestion_config.yaml`
2. Update `src/core/config.py`
3. Create `src/api/v1/annotations.py`
4. Update `docker-compose.yml`

**Verification:**
```bash
# Test config loading
python -c "from src.core.config import get_settings; s = get_settings(); print(f'VLM Model: {s.qwen3vl_model}')"

# Test API
curl http://localhost:8000/api/document/doc_123/annotations
```

### Priority 4: Testing (7 hours)
1. Create unit tests for `ImageProcessor`
2. Create unit tests for VLM-enhanced nodes
3. Create integration test for E2E pipeline
4. Run full test suite

**Verification:**
```bash
pytest tests/unit/components/ingestion/test_image_processor.py -v
pytest tests/unit/components/ingestion/test_langgraph_nodes_vlm.py -v
pytest tests/integration/components/ingestion/test_image_pipeline.py -v
```

### Priority 5: Documentation (2 hours)
1. Create `docs/features/FEATURE_21_6_IMAGE_VLM.md`
2. Update `docs/sprints/SPRINT_21_PLAN_v2.md` with completion status
3. Update `README.md` with Feature 21.6

---

## 🔑 Critical Implementation Notes

### 1. VLM Text Insertion (MOST CRITICAL!)
```python
# ✅ CORRECT (Feature 21.6):
picture_item.text = f"{caption}\n\n{vlm_description}"
# HybridChunker will automatically include hierarchical context!

# ❌ WRONG:
# Create separate image chunks
# (loses document hierarchy!)
```

### 2. BBox Provenance Storage
```python
# ✅ CORRECT: Only in Qdrant
qdrant_payload = {
    "image_annotations": [{
        "bbox_absolute": {...},
        "page_context": {...},
        "bbox_normalized": {...}
    }]
}

# ✅ CORRECT: Only reference in Neo4j
neo4j_entity = {
    "qdrant_point_id": chunk_id,
    "has_image_annotation": True,
    # NO full BBox data!
}
```

### 3. Qwen3-VL Prompting
```python
# ✅ CORRECT (Qwen3-VL best practice):
prompt = "Describe this image from a document in detail, including any text, diagrams, charts, or important visual elements."

# ❌ WRONG (too complex):
prompt = "Please provide a JSON with {description: ..., entities: [...], ...}"
```

### 4. HybridChunker vs ChunkingService
```python
# ✅ CORRECT (Feature 21.6):
from docling.chunking import HybridChunker
chunker = HybridChunker(tokenizer=tokenizer, merge_peers=True)
chunks = list(chunker.chunk(enriched_doc))

# ❌ WRONG (old approach):
chunking_service = get_chunking_service()
chunks = chunking_service.chunk_document(content)
```

### 5. BGE-M3 Tokenizer
```python
# ✅ CORRECT:
tokenizer = HuggingFaceTokenizer(
    tokenizer=AutoTokenizer.from_pretrained("BAAI/bge-m3"),
    max_tokens=8192
)

# ❌ WRONG (old model):
tokenizer = AutoTokenizer.from_pretrained("nomic-ai/nomic-embed-text-v1.5")
```

---

## 📁 File Structure Overview

```
AEGIS_Rag/
├── src/
│   ├── components/
│   │   └── ingestion/
│   │       ├── __init__.py
│   │       ├── docling_client.py              (existing, needs update)
│   │       ├── ingestion_state.py             ✅ UPDATED
│   │       ├── image_processor.py             ✅ NEW
│   │       ├── langgraph_nodes.py             🔄 IN PROGRESS
│   │       └── langgraph_pipeline.py          (needs update)
│   ├── core/
│   │   └── config.py                          ⏸️ NEEDS UPDATE
│   └── api/
│       └── v1/
│           └── annotations.py                 ⏸️ NEW
├── tests/
│   ├── unit/
│   │   └── components/
│   │       └── ingestion/
│   │           ├── test_image_processor.py    ⏸️ NEW
│   │           └── test_langgraph_nodes_vlm.py ⏸️ NEW
│   └── integration/
│       └── components/
│           └── ingestion/
│               └── test_image_pipeline.py     ⏸️ NEW
├── docs/
│   ├── sprints/
│   │   ├── SPRINT_21_PLAN_v2.md               ✅ UPDATED
│   │   └── SPRINT_21_FEATURE_21_6_PROGRESS.md ✅ THIS FILE
│   └── features/
│       └── FEATURE_21_6_IMAGE_VLM.md          ⏸️ NEW
├── ingestion_config.yaml                       ⏸️ NEW
└── docker-compose.yml                          ⏸️ NEEDS UPDATE
```

---

## 🚀 Quick Start Commands for Next Session

```bash
# 1. Verify completed work
cat src/components/ingestion/ingestion_state.py | grep "enrichment_status"
cat src/components/ingestion/image_processor.py | head -20
cat docs/sprints/SPRINT_21_PLAN_v2.md | grep "Feature 21.6"

# 2. Continue with VLM Node
code src/components/ingestion/langgraph_nodes.py
# Insert image_enrichment_node at line 270

# 3. Test as you go
pytest tests/unit/components/ingestion/ -v -k vlm

# 4. Check progress
python -c "
from src.components.ingestion.ingestion_state import IngestionState
from src.components.ingestion.image_processor import ImageProcessor
print('✅ State schema ready')
print('✅ Image processor ready')
"
```

---

## 📞 Key Decisions Reference

| Decision | Reasoning | File Reference |
|----------|-----------|----------------|
| VLM text IN DoclingDocument | HybridChunker auto-adds hierarchical context | `langgraph_nodes.py:image_enrichment_node` |
| BBox only in Qdrant | Single source of truth, avoid duplication | `langgraph_nodes.py:embedding_node` |
| Simple Qwen3-VL prompts | Official best practice, better results | `image_processor.py:generate_vlm_description` |
| On-demand annotations | Performance, only load when PDF displayed | `annotations.py:get_document_annotations` |
| BGE-M3 tokenizer | Replaces nomic-embed-text, 8192 context | `langgraph_nodes.py:chunking_node` |
| Normalized coordinates | Scale-independent frontend rendering | `langgraph_nodes.py:image_enrichment_node` |

---

## ✅ Success Criteria Checklist

- [ ] Docling extrahiert Bilder mit BBox + Page-Context
- [ ] Qwen3-VL beschreibt Bilder (>90% Success-Rate)
- [ ] VLM-Text wird IN DoclingDocument eingefügt
- [ ] HybridChunker erstellt Chunks mit Hierarchie-Kontext
- [ ] Qdrant speichert vollständige BBox-Provenance
- [ ] Neo4j Entities haben Referenz zu Qdrant
- [ ] API-Endpoint für On-Demand Annotations (Latenz <50ms)
- [ ] Normalisierte Koordinaten funktionieren mit PDF.js
- [ ] Integration Tests bestanden
- [ ] Dokumentation vollständig

**Current Status:** 0/10 criteria met (40% implementation complete)

---

**Last Updated:** 2025-11-08 23:45 UTC
**Next Review:** Upon session resume
**Estimated Completion:** 2025-11-11 (3 days remaining)
