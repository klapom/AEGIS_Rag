"""LangGraph Ingestion State Schema - Sprint 21 Feature 21.6.

Feature 21.6: Image-Enhanced Document Ingestion with VLM

This module defines the state structure for the image-enhanced LangGraph ingestion pipeline.
The state is passed through all 5 nodes sequentially:

1. docling_extraction   → Parse document with Docling container, extract BBox + page dimensions
2. image_enrichment     → Qwen3-VL generates image descriptions, insert INTO DoclingDocument
3. chunking             → HybridChunker with BGE-M3, map BBox to chunks
4. embedding            → Embed with BGE-M3, store full provenance in Qdrant
5. graph_extraction     → Extract entities/relations, store minimal provenance in Neo4j

State Management:
- TypedDict ensures type safety across nodes
- Progress tracking (0.0 to 1.0)
- Error accumulation (continue on partial failure)
- Memory monitoring (4.4GB RAM, 6GB VRAM constraints)
- VLM metadata with complete BBox provenance

Example:
    >>> state = create_initial_state(
    ...     document_path="/path/to/doc.pdf",
    ...     document_id="doc_001",
    ...     batch_id="batch_20251107_001",
    ... )
    >>> # Pass through nodes
    >>> state = await docling_extraction_node(state)
    >>> state = await image_enrichment_node(state)
    >>> # ... etc
"""

from typing import Any, Literal, TypedDict

from src.core.chunk import Chunk


class IngestionState(TypedDict, total=False):
    """State for LangGraph ingestion pipeline.

    This state is passed through all 5 nodes in the pipeline.
    Each node reads input fields, performs processing, and writes output fields.

    Attributes:
        # ============================================================
        # INPUT FIELDS (set by caller before pipeline starts)
        # ============================================================
        document_path: Absolute path to document file
        document_id: Unique document identifier (SHA-256 hash of path)
        batch_id: Batch identifier for grouping documents
        batch_index: Index of this document in the batch (0-based)
        total_documents: Total number of documents in the batch

        # ============================================================
        # NODE 1: MEMORY CHECK
        # ============================================================
        current_memory_mb: Current system RAM usage in MB
        current_vram_mb: Current GPU VRAM usage in MB (from nvidia-smi)
        memory_check_passed: True if sufficient memory available
        requires_container_restart: True if VRAM leak detected (>5GB)

        # ============================================================
        # NODE 2: DOCLING PARSING
        # ============================================================
        parsed_content: Full document text (with OCR)
        parsed_metadata: Document metadata (pages, size, mime_type)
        parsed_tables: Extracted tables with structure
        parsed_images: Image references with positions
        parsed_layout: Document layout (headings, lists, sections)
        docling_status: Status of Docling parsing

        # ============================================================
        # NODE 3: CHUNKING
        # ============================================================
        chunks: List of Chunk objects (1800 tokens each, Feature 21.4)
        chunking_status: Status of chunking operation

        # ============================================================
        # NODE 4: EMBEDDING
        # ============================================================
        embedded_chunk_ids: List of Qdrant point IDs after upload
        embedding_status: Status of embedding operation

        # ============================================================
        # NODE 5: GRAPH EXTRACTION
        # ============================================================
        entities: List of extracted entities (ThreePhaseExtractor)
        relations: List of extracted relations
        graph_status: Status of graph extraction

        # ============================================================
        # PROGRESS & ERROR TRACKING (updated by all nodes)
        # ============================================================
        overall_progress: Overall progress (0.0 to 1.0)
        errors: List of error messages (accumulates errors)
        retry_count: Number of retries for current document
        max_retries: Maximum retries before skipping (default: 3)

        # ============================================================
        # TIMESTAMPS (for performance monitoring)
        # ============================================================
        start_time: Pipeline start timestamp (Unix epoch)
        docling_start_time: Docling node start time
        docling_end_time: Docling node end time
        chunking_start_time: Chunking node start time
        chunking_end_time: Chunking node end time
        embedding_start_time: Embedding node start time
        embedding_end_time: Embedding node end time
        graph_start_time: Graph extraction start time
        graph_end_time: Graph extraction end time
        end_time: Pipeline end timestamp
    """

    # ============================================================
    # INPUT FIELDS (Required)
    # ============================================================
    document_path: str  # Absolute path to document file
    document_id: str  # Unique document identifier
    batch_id: str  # Batch identifier
    batch_index: int  # Index in batch (0-based)
    total_documents: int  # Total documents in batch

    # ============================================================
    # NODE 1: MEMORY CHECK
    # ============================================================
    current_memory_mb: float  # Current RAM usage
    current_vram_mb: float  # Current VRAM usage (GPU)
    memory_check_passed: bool  # True if sufficient memory
    requires_container_restart: bool  # True if VRAM leak detected

    # ============================================================
    # NODE 2: DOCLING PARSING (Feature 21.6)
    # ============================================================
    document: Any  # DoclingDocument object (main object for VLM enrichment)
    page_dimensions: dict[int, dict]  # {page_no: {width, height, unit, dpi}}
    parsed_content: str  # Full document text
    parsed_metadata: dict  # Document metadata
    parsed_tables: list[dict]  # Extracted tables
    parsed_images: list[dict]  # Image references
    parsed_layout: dict  # Document layout structure
    docling_status: Literal["pending", "running", "completed", "failed"]

    # ============================================================
    # NODE 2.5: VLM IMAGE ENRICHMENT (Feature 21.6)
    # ============================================================
    vlm_metadata: list[dict]  # List of VLM metadata with BBox
    enrichment_status: Literal["pending", "running", "completed", "failed"]

    # ============================================================
    # NODE 3: CHUNKING
    # ============================================================
    chunks: list[Chunk]  # Chunk objects (1800 tokens)
    chunking_status: Literal["pending", "running", "completed", "failed"]

    # ============================================================
    # NODE 4: EMBEDDING
    # ============================================================
    embedded_chunk_ids: list[str]  # Qdrant point IDs
    embedding_status: Literal["pending", "running", "completed", "failed"]

    # ============================================================
    # NODE 5: GRAPH EXTRACTION
    # ============================================================
    entities: list[Any]  # Extracted entities (stored in Neo4j, not in state)
    relations: list[Any]  # Extracted relations (stored in Neo4j, not in state)
    graph_status: Literal["pending", "running", "completed", "failed"]

    # ============================================================
    # PROGRESS & ERROR TRACKING
    # ============================================================
    overall_progress: float  # 0.0 to 1.0
    errors: list[dict]  # Error messages with context
    retry_count: int  # Number of retries
    max_retries: int  # Maximum retries (default: 3)

    # ============================================================
    # TIMESTAMPS (Performance Monitoring)
    # ============================================================
    start_time: float  # Unix epoch timestamp
    docling_start_time: float
    docling_end_time: float
    chunking_start_time: float
    chunking_end_time: float
    embedding_start_time: float
    embedding_end_time: float
    graph_start_time: float
    graph_end_time: float
    end_time: float


def create_initial_state(
    document_path: str,
    document_id: str,
    batch_id: str,
    batch_index: int,
    total_documents: int,
    max_retries: int = 3,
) -> IngestionState:
    """Create initial ingestion state for a document.

    Args:
        document_path: Absolute path to document file
        document_id: Unique document identifier
        batch_id: Batch identifier
        batch_index: Index in batch (0-based)
        total_documents: Total documents in batch
        max_retries: Maximum retries before skipping (default: 3)

    Returns:
        IngestionState with initialized fields

    Example:
        >>> state = create_initial_state(
        ...     document_path="/data/doc.pdf",
        ...     document_id="doc_001",
        ...     batch_id="batch_001",
        ...     batch_index=0,
        ...     total_documents=10,
        ... )
        >>> state["overall_progress"]
        0.0
    """
    import time

    return IngestionState(
        # Input fields
        document_path=document_path,
        document_id=document_id,
        batch_id=batch_id,
        batch_index=batch_index,
        total_documents=total_documents,
        # Memory check (initialized by memory_check_node)
        current_memory_mb=0.0,
        current_vram_mb=0.0,
        memory_check_passed=False,
        requires_container_restart=False,
        # Docling parsing (initialized by docling_extraction_node)
        document=None,  # DoclingDocument object
        page_dimensions={},  # Page metadata
        parsed_content="",
        parsed_metadata={},
        parsed_tables=[],
        parsed_images=[],
        parsed_layout={},
        docling_status="pending",
        # VLM enrichment (initialized by image_enrichment_node)
        vlm_metadata=[],
        enrichment_status="pending",
        # Chunking (initialized by chunking_node)
        chunks=[],
        chunking_status="pending",
        # Embedding (initialized by embedding_node)
        embedded_chunk_ids=[],
        embedding_status="pending",
        # Graph extraction (initialized by graph_extraction_node)
        entities=[],
        relations=[],
        graph_status="pending",
        # Progress tracking
        overall_progress=0.0,
        errors=[],
        retry_count=0,
        max_retries=max_retries,
        # Timestamps
        start_time=time.time(),
        docling_start_time=0.0,
        docling_end_time=0.0,
        chunking_start_time=0.0,
        chunking_end_time=0.0,
        embedding_start_time=0.0,
        embedding_end_time=0.0,
        graph_start_time=0.0,
        graph_end_time=0.0,
        end_time=0.0,
    )


def calculate_progress(state: IngestionState) -> float:
    """Calculate overall progress based on node completion.

    Progress weights (Feature 21.6):
    - memory_check: 5%
    - docling:      20%
    - vlm enrichment: 15%
    - chunking:     15%
    - embedding:    25%
    - graph:        20%

    Args:
        state: Current ingestion state

    Returns:
        Progress value between 0.0 and 1.0

    Example:
        >>> state = create_initial_state(...)
        >>> state["docling_status"] = "completed"
        >>> state["enrichment_status"] = "completed"
        >>> calculate_progress(state)
        0.40  # 5% memory + 20% docling + 15% vlm
    """
    progress = 0.0

    # Memory check: 5%
    if state.get("memory_check_passed", False):
        progress += 0.05

    # Docling parsing: 20%
    if state.get("docling_status") == "completed":
        progress += 0.20
    elif state.get("docling_status") == "running":
        progress += 0.10  # Half credit for running

    # VLM enrichment: 15% (Feature 21.6)
    if state.get("enrichment_status") == "completed":
        progress += 0.15
    elif state.get("enrichment_status") == "running":
        progress += 0.075

    # Chunking: 15%
    if state.get("chunking_status") == "completed":
        progress += 0.15
    elif state.get("chunking_status") == "running":
        progress += 0.075

    # Embedding: 25%
    if state.get("embedding_status") == "completed":
        progress += 0.25
    elif state.get("embedding_status") == "running":
        progress += 0.125

    # Graph extraction: 20%
    if state.get("graph_status") == "completed":
        progress += 0.20
    elif state.get("graph_status") == "running":
        progress += 0.10

    return min(progress, 1.0)  # Cap at 1.0


def add_error(state: IngestionState, node_name: str, error_message: str, error_type: str = "error") -> None:
    """Add error to state error list.

    Args:
        state: Current ingestion state
        node_name: Name of node where error occurred
        error_message: Error message
        error_type: Error type ("error", "warning", "info")

    Example:
        >>> add_error(state, "docling", "Container timeout", "error")
        >>> state["errors"]
        [{"node": "docling", "message": "Container timeout", "type": "error"}]
    """
    import time

    if "errors" not in state:
        state["errors"] = []

    state["errors"].append(
        {
            "node": node_name,
            "message": error_message,
            "type": error_type,
            "timestamp": time.time(),
        }
    )


def should_retry(state: IngestionState) -> bool:
    """Check if document should be retried.

    Args:
        state: Current ingestion state

    Returns:
        True if retry count < max_retries

    Example:
        >>> state = create_initial_state(...)
        >>> state["retry_count"] = 2
        >>> state["max_retries"] = 3
        >>> should_retry(state)
        True
    """
    return state.get("retry_count", 0) < state.get("max_retries", 3)


def increment_retry(state: IngestionState) -> None:
    """Increment retry count.

    Args:
        state: Current ingestion state

    Example:
        >>> state = create_initial_state(...)
        >>> increment_retry(state)
        >>> state["retry_count"]
        1
    """
    state["retry_count"] = state.get("retry_count", 0) + 1
