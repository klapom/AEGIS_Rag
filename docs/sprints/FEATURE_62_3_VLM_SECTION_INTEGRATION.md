# Feature 62.3: VLM Image Integration with Sections (5 SP)

## Overview

Feature 62.3 implements VLM (Vision Language Model) image integration with section-aware document structure. This feature links VLM-generated image descriptions to their source document sections, enabling queries like "images in section 3.2" and maintaining complete provenance from document sections to image descriptions.

## Motivation

Previously, VLM-enriched images were processed but their association with document sections was lost. This feature:

- Links each image to its source section for better context preservation
- Enables section-filtered image search
- Maintains complete metadata chain: document → section → image → VLM description
- Improves retrieval accuracy by preserving hierarchical document structure

## Architecture

### Components

1. **VLMService** (`src/domains/document_processing/vlm_service.py`)
   - High-level API for section-aware image enrichment
   - Preserves section metadata through processing pipeline
   - Manages image processor lifecycle

2. **ImageWithSectionContext** (data model)
   - Image with associated section metadata
   - Bridges image processing and document structure
   - Fields: image, section_id, section_heading, section_level, page_number

3. **VLMImageResult** (data model)
   - Result from VLM processing with complete metadata
   - Includes section information and model details
   - Fields: description, section_id, section_heading, tokens_used, cost_usd

4. **Image Enrichment Node with Sections** (`src/components/ingestion/nodes/image_enrichment_with_sections.py`)
   - Extended enrichment pipeline with section tracking
   - Builds section map from chunks
   - Associates images with sections based on page numbers
   - Parallel processing with section preservation

## Key Files

### Core Implementation

1. `/src/domains/document_processing/vlm_service.py` (NEW)
   - VLMService class for section-aware processing
   - ImageWithSectionContext data model
   - VLMImageResult data model

2. `/src/components/ingestion/nodes/image_enrichment_with_sections.py` (NEW)
   - image_enrichment_node_with_sections() async function
   - _build_section_map_from_chunks() helper
   - _identify_image_section() helper

3. `/src/domains/document_processing/__init__.py` (MODIFIED)
   - Exports VLMService, ImageWithSectionContext, VLMImageResult

### Tests

1. `/tests/unit/domains/document_processing/test_vlm_service.py` (NEW - 30 tests)
   - Unit tests for VLMService
   - Tests for data models
   - Tests for section metadata handling
   - Edge cases and error handling

2. `/tests/unit/domains/document_processing/test_image_enrichment_with_sections.py` (NEW - 22 tests)
   - Integration tests for enrichment node
   - Section map building tests
   - Image-section association tests
   - Multiple image batch tests

## Implementation Details

### VLMService

```python
class VLMService:
    """Service for VLM-enhanced image processing with section tracking."""

    async def process_image_with_section(
        self,
        image_context: ImageWithSectionContext,
        include_section_in_prompt: bool = False,
    ) -> VLMImageResult:
        """Process a single image with section context preservation."""

    async def process_images_with_sections(
        self,
        images_with_sections: list[ImageWithSectionContext],
        include_section_in_prompt: bool = False,
    ) -> list[VLMImageResult]:
        """Process multiple images with section context preservation."""
```

### Data Flow

```
Document with Images
    ↓
Docling Parser
    ↓
Chunking with Section Metadata
    ↓
Image Enrichment Node with Sections
    ├─ Build section map from chunks
    ├─ Identify image section (page → section)
    ├─ Process images with VLM
    └─ Store section_id in metadata
    ↓
Vector Store Integration
    ├─ Store image_section_id in payloads
    └─ Enable section-filtered search
```

### Section Identification Algorithm

1. **Exact Page Match**: If image page has direct section mapping, use it
2. **Backward Search**: Search backward from image page to find parent section
3. **Fallback**: Default "unknown" section if no match found

Example:
```
Chunks:
- section_1 (pages 1-3)
- section_3.2 (pages 5-9)
- section_5 (pages 10-12)

Image on page 7 → Maps to section_3.2 (exact match)
Image on page 8 → Maps to section_3.2 (backward search)
Image on page 100 → Maps to section_5 (backward search)
```

## Integration with Vector Store

VLM metadata stored with images includes:

```python
vlm_metadata = {
    "picture_index": 0,
    "picture_ref": "#/pictures/0",
    "description": "VLM-generated description",
    "bbox_full": {...},
    # Feature 62.3: Section metadata
    "section_id": "section_3.2",
    "section_heading": "Multi-Server Architecture",
    "section_level": 2,
    "vlm_model": "qwen3-vl:4b-instruct",
    "timestamp": 1234567890,
}
```

This enables queries:
- "Find all images in section 3.2"
- "Find images in sections at level 2"
- "Find images with descriptions matching 'server architecture'"

## Test Coverage

Total Tests: **52 tests**
- VLM Service Unit Tests: 30 tests
- Image Enrichment Integration Tests: 22 tests

Coverage Breakdown:

1. **Data Model Tests** (6 tests)
   - ImageWithSectionContext creation and validation
   - VLMImageResult creation and structure

2. **VLMService Tests** (24 tests)
   - Initialization and cleanup
   - Single image processing with section preservation
   - Batch processing of multiple images
   - Section information extraction
   - Error handling and edge cases
   - Model identification and metadata

3. **Image Enrichment Node Tests** (22 tests)
   - Section map building from chunks
   - Image-to-section identification
   - Enrichment pipeline with sections
   - Multiple images with different sections
   - Metadata completeness
   - Error handling

All tests pass with >80% code coverage.

## Usage Example

### Basic Usage

```python
from src.domains.document_processing import (
    VLMService,
    ImageWithSectionContext,
)
from pathlib import Path
from PIL import Image

# Initialize service
service = VLMService()

# Create image with section context
image_context = ImageWithSectionContext(
    image=Image.open("diagram.png"),
    image_path=Path("diagram.png"),
    page_number=5,
    section_id="section_3.2",
    section_heading="Multi-Server Architecture",
    section_level=2,
    document_id="doc_001",
)

# Process image with section preservation
result = await service.process_image_with_section(image_context)

print(f"Section: {result.section_id}")
print(f"Heading: {result.section_heading}")
print(f"Description: {result.description}")

# Cleanup
service.cleanup()
```

### Batch Processing

```python
# Create list of images with sections
images = [
    ImageWithSectionContext(...),
    ImageWithSectionContext(...),
    ImageWithSectionContext(...),
]

# Process batch
results = await service.process_images_with_sections(images)

# Access results with section info preserved
for result in results:
    print(f"{result.section_id}: {len(result.description)} chars")
```

### In Ingestion Pipeline

```python
from src.components.ingestion.nodes.image_enrichment_with_sections import (
    image_enrichment_node_with_sections,
)

# In LangGraph pipeline
state = await image_enrichment_node_with_sections(state)

# VLM metadata now includes section_id
for metadata in state["vlm_metadata"]:
    print(f"Image in {metadata['section_id']}: {metadata['description'][:100]}")
```

## Related Architecture Decisions

- **ADR-026**: Pure LLM extraction pipeline (VLM processing aligned)
- **ADR-039**: Adaptive section-aware chunking (section metadata source)
- **ADR-033**: AegisLLMProxy multi-cloud routing (VLM backend routing)

## Future Enhancements

1. **Section-Aware Prompting**: Inject section context into VLM prompts for better descriptions
2. **Token Tracking**: Track tokens consumed by VLM per section
3. **Cost Analysis**: Analyze VLM costs per section
4. **Image Search**: Enable "find images similar to section 3.2 images" queries

## References

- VLM Service: `src/domains/document_processing/vlm_service.py`
- Image Processor: `src/components/ingestion/image_processor.py`
- Enrichment Node: `src/components/ingestion/nodes/image_enrichment_with_sections.py`
- Tests: `tests/unit/domains/document_processing/test_vlm_service.py`
- Tests: `tests/unit/domains/document_processing/test_image_enrichment_with_sections.py`

## Success Criteria Met

- [x] VLMService class with section tracking implemented
- [x] Images linked to document sections
- [x] Section metadata preserved through pipeline
- [x] Image enrichment node supports section integration
- [x] Section identification algorithm implemented
- [x] 30 unit tests for VLMService (>80% coverage)
- [x] 22 integration tests for enrichment node (>80% coverage)
- [x] All tests passing
- [x] Error handling and edge cases covered
- [x] Documentation complete

## Notes

- All 52 tests pass
- Code follows project conventions (Black, Ruff, MyPy)
- Backward compatible with existing image processor
- Async processing maintained for performance
- Section metadata optional (graceful fallback to "unknown")
