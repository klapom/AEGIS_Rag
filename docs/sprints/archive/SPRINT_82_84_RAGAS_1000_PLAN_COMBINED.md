# Sprint 82-84 Plan: RAGAS 1000-Sample Benchmark Implementation

**Epic:** 1000-Sample Stratified RAGAS Evaluation Benchmark
**ADR Reference:** [ADR-048](../adr/ADR-048-ragas-1000-sample-benchmark.md)
**Total Story Points:** 42 SP (Phase 1-3)
**Timeline:** Sprint 82-84 (6-8 weeks)

---

## Executive Summary

Implement a 1000-sample stratified RAGAS benchmark to replace the current 5-sample HotpotQA evaluation. This enables:

- **Statistical validity:** ±3% confidence intervals (vs. ±20% with 5 samples)
- **Capability breakdown:** Per doc_type, question_type analysis
- **Anti-hallucination testing:** 12% unanswerable questions
- **Regression tracking:** Sprint-over-sprint comparison

---

## Sprint 82: Phase 1 - Text-Only Benchmark (8 SP)

**Duration:** 5-7 days
**Goal:** 500 text-only samples from HotpotQA, RAGBench, LogQA

### Features

| # | Feature | SP | Owner | Status |
|---|---------|-----|-------|--------|
| 82.1 | Dataset loader infrastructure | 3 | Backend | 📝 Planned |
| 82.2 | Stratified sampling engine | 2 | Backend | 📝 Planned |
| 82.3 | Unanswerable generation | 2 | Backend | 📝 Planned |
| 82.4 | AegisRAG JSONL export | 1 | Backend | 📝 Planned |

### Feature 82.1: Dataset Loader Infrastructure (3 SP)

**Files to Create:**
```
scripts/ragas_benchmark/
├── __init__.py
├── dataset_loader.py       # HuggingFace dataset loading
├── adapters/
│   ├── __init__.py
│   ├── hotpotqa.py         # HotpotQA adapter
│   ├── ragbench.py         # RAGBench adapter
│   └── logqa.py            # LogQA adapter
└── config.py               # Dataset configs, quotas
```

**Key Classes:**
```python
class DatasetLoader:
    """Load and normalize HuggingFace datasets."""

    def load_dataset(self, name: str, subset: str = None) -> List[Dict]
    def get_available_datasets() -> List[str]

class DatasetAdapter(ABC):
    """Abstract adapter for dataset normalization."""

    @abstractmethod
    def adapt(self, record: Dict) -> NormalizedSample

    @abstractmethod
    def get_doc_type(self) -> str
```

**Acceptance Criteria:**
- [ ] Load HotpotQA (113k samples available)
- [ ] Load RAGBench (10k samples available)
- [ ] Load LogQA (5k samples available)
- [ ] Handle missing fields gracefully (fallback values)
- [ ] Log dropped samples with reasons

### Feature 82.2: Stratified Sampling Engine (2 SP)

**Quota Configuration:**
```python
# scripts/ragas_benchmark/config.py

DOC_TYPE_QUOTAS = {
    "clean_text": 350,  # HotpotQA + RAGBench
    "log_ticket": 150,  # LogQA
}

QUESTION_TYPE_QUOTAS = {
    "clean_text": {
        "lookup": 80,
        "definition": 60,
        "howto": 60,
        "multihop": 80,
        "comparison": 50,
        "policy": 20,
    },
    "log_ticket": {
        "lookup": 40,
        "howto": 45,
        "entity": 25,
        "multihop": 25,
        "policy": 15,
    },
}

DIFFICULTY_DISTRIBUTION = {"D1": 0.40, "D2": 0.35, "D3": 0.25}
```

**Key Functions:**
```python
def stratified_sample(
    pool: List[NormalizedSample],
    doc_type_quotas: Dict[str, int],
    qtype_quotas: Dict[str, Dict[str, int]],
    seed: int = 42
) -> List[NormalizedSample]:
    """Sample from pool respecting quotas."""

def classify_question_type(question: str, doc_type: str) -> str:
    """Heuristic classification of question type."""

def assign_difficulty(doc_type: str, qtype: str) -> str:
    """Assign D1/D2/D3 based on heuristics."""
```

**Acceptance Criteria:**
- [ ] Exact quota fulfillment (±0 per category)
- [ ] Reproducible with fixed seed
- [ ] Fallback when category underfills (borrow from "lookup")

### Feature 82.3: Unanswerable Generation (2 SP)

**Generation Methods:**
```python
class UnanswerableGenerator:
    """Generate unanswerable variants of answerable questions."""

    def temporal_shift(self, sample: NormalizedSample) -> NormalizedSample:
        """Add future/past context that doesn't exist."""

    def entity_swap(self, sample: NormalizedSample) -> NormalizedSample:
        """Replace key entity with non-existent one."""

    def negation(self, sample: NormalizedSample) -> NormalizedSample:
        """Ask about something explicitly NOT in corpus."""

    def cross_domain(self, sample: NormalizedSample) -> NormalizedSample:
        """Ask about unrelated domain."""

    def generate_batch(
        self,
        samples: List[NormalizedSample],
        target_count: int = 50
    ) -> List[NormalizedSample]:
        """Generate target_count unanswerables from pool."""
```

**Target Distribution (50 unanswerables for Phase 1):**
- temporal_shift: 15
- entity_swap: 15
- negation: 10
- cross_domain: 10

**Acceptance Criteria:**
- [ ] 10% unanswerable rate (50/500)
- [ ] Human-validated subset (10 samples) confirms unanswerability
- [ ] Balanced across generation methods

### Feature 82.4: AegisRAG JSONL Export (1 SP)

**Output Format:**
```json
{
  "id": "ragas_001_hotpot_abc123",
  "question": "Which magazine was started first?",
  "ground_truth": "Arthur's Magazine",
  "contexts": ["Arthur's Magazine (1844–1846)...", "First for Women is..."],
  "answerable": true,
  "doc_type": "clean_text",
  "question_type": "comparison",
  "difficulty": "D2",
  "source_dataset": "hotpot_qa",
  "metadata": {
    "original_id": "5a8b57f25542995d1e6f1371",
    "supporting_facts": [["Arthur's Magazine", 0]],
    "sample_method": "stratified",
    "generation_timestamp": "2026-01-15T10:30:00Z"
  }
}
```

**Export Script:**
```bash
poetry run python scripts/ragas_benchmark/build_phase1.py \
  --output data/evaluation/ragas_phase1_500.jsonl \
  --manifest data/evaluation/ragas_phase1_manifest.csv \
  --seed 42
```

**Acceptance Criteria:**
- [ ] Valid JSONL output (1 sample per line)
- [ ] Manifest CSV with all metadata for audit
- [ ] SHA256 hash of output for reproducibility

### Sprint 82 Deliverables

| Artifact | Location |
|----------|----------|
| Dataset loaders | `scripts/ragas_benchmark/` |
| Phase 1 dataset | `data/evaluation/ragas_phase1_500.jsonl` |
| Manifest | `data/evaluation/ragas_phase1_manifest.csv` |
| Unit tests | `tests/ragas_benchmark/test_phase1.py` |

### Sprint 82 Success Criteria

- [ ] 500 samples generated with correct quota distribution
- [ ] 50 unanswerables (10%) included
- [ ] Dataset passes RAGAS evaluation (no format errors)
- [ ] Statistical report: samples per doc_type, qtype, difficulty

---

## Sprint 83: Phase 2 - Structured Data (13 SP)

**Duration:** 7-10 days
**Goal:** Add 300 samples from table/code datasets

### Features

| # | Feature | SP | Owner | Status |
|---|---------|-----|-------|--------|
| 83.1 | T2-RAGBench table processor | 5 | Backend | 📝 Planned |
| 83.2 | CodeRepoQA code extractor | 5 | Backend | 📝 Planned |
| 83.3 | Statistical rigor package | 2 | Backend | 📝 Planned |
| 83.4 | Phase 2 integration | 1 | Backend | 📝 Planned |

### Feature 83.1: T2-RAGBench Table Processor (5 SP)

**Challenge:** Tables need special handling for RAG

```yaml
Problem:
  - Raw table data loses structure in plain text
  - Financial tables have implicit relationships
  - Cell references (A1, B2) need resolution

Solution:
  - Convert tables to structured markdown
  - Preserve column headers
  - Add table caption as context
```

**Implementation:**
```python
class T2RAGBenchAdapter(DatasetAdapter):
    """Adapter for T2-RAGBench (FinQA subset)."""

    def adapt(self, record: Dict) -> NormalizedSample:
        # Combine table + context + caption
        table_md = self.table_to_markdown(record["table"])
        context = record.get("context", "")
        combined = f"{context}\n\n{table_md}"

        return NormalizedSample(
            question=record["question"],
            ground_truth=record["program_answer"],
            contexts=[combined],
            doc_type="table",
            metadata={
                "table_rows": len(record["table"]),
                "file_name": record.get("file_name"),
            }
        )

    def table_to_markdown(self, table_data: List[List[str]]) -> str:
        """Convert table to markdown with headers."""
```

**Target Quota:** 100 table samples

**Acceptance Criteria:**
- [ ] Table structure preserved in output
- [ ] Numeric values correctly extracted
- [ ] Ground truth matches expected format

### Feature 83.2: CodeRepoQA Code Extractor (5 SP)

**Challenge:** Code needs syntax-aware handling

```yaml
Problem:
  - Code snippets contain special characters
  - Language context matters
  - Function boundaries need preservation

Solution:
  - Preserve code blocks with language hints
  - Include file path as context
  - Use markdown code fences
```

**Implementation:**
```python
class CodeRepoQAAdapter(DatasetAdapter):
    """Adapter for CodeRepoQA."""

    def adapt(self, record: Dict) -> NormalizedSample:
        code_context = self.format_code_context(record)

        return NormalizedSample(
            question=record["question"],
            ground_truth=record["answer"],
            contexts=[code_context],
            doc_type="code_config",
            metadata={
                "repo": record.get("repo"),
                "language": self.detect_language(record),
            }
        )

    def format_code_context(self, record: Dict) -> str:
        """Format code with language hint and path."""
        language = self.detect_language(record)
        code = record.get("code", record.get("snippet", ""))
        path = record.get("file_path", "unknown")

        return f"""```{language}
# File: {path}
{code}
```"""
```

**Target Quota:** 100 code samples

**Acceptance Criteria:**
- [ ] Code syntax preserved
- [ ] Language correctly detected
- [ ] File paths included in metadata

### Feature 83.3: Statistical Rigor Package (2 SP)

**Purpose:** Enable defensible statistical claims

**Implementation:**
```python
# scripts/ragas_benchmark/statistics.py

def compute_confidence_interval(
    scores: List[float],
    confidence: float = 0.95
) -> Tuple[float, float, float]:
    """Bootstrap 95% CI for metric scores."""

def significance_test(
    group_a: List[float],
    group_b: List[float]
) -> Dict[str, float]:
    """McNemar's test for paired comparisons."""
    return {
        "p_value": p,
        "effect_size": cohens_d,
        "significant": p < 0.05
    }

def power_analysis(n: int, effect_size: float) -> float:
    """Post-hoc power calculation."""
```

**Integration with Evaluation:**
```python
# Enhanced output in run_ragas_evaluation.py
{
    "metrics": {
        "faithfulness": 0.72,
        "faithfulness_ci": [0.68, 0.76],
        "faithfulness_n": 500
    },
    "comparisons": {
        "hybrid_vs_vector": {
            "p_value": 0.003,
            "effect_size": 0.45,
            "significant": true
        }
    }
}
```

**Acceptance Criteria:**
- [ ] CI computed for all 4 RAGAS metrics
- [ ] Significance tests for mode comparisons
- [ ] Power analysis included in reports

### Feature 83.4: Phase 2 Integration (1 SP)

**Combined Dataset:**
- Phase 1: 500 samples (text, logs)
- Phase 2: +300 samples (tables, code)
- **Total: 800 samples**

**Output:**
```bash
data/evaluation/
├── ragas_phase1_500.jsonl
├── ragas_phase2_300.jsonl
├── ragas_combined_800.jsonl  # NEW
└── ragas_manifest_800.csv    # NEW
```

### Sprint 83 Success Criteria

- [ ] 800 total samples (500 + 300)
- [ ] Table and code doc_types included
- [ ] Statistical package integrated
- [ ] All tests passing

---

## Sprint 84: Phase 3 - Visual Assets (21 SP)

**Duration:** 10-14 days
**Goal:** Add 200 samples from PDF/OCR/slide datasets

### Features

| # | Feature | SP | Owner | Status |
|---|---------|-----|-------|--------|
| 84.1 | Asset downloader with caching | 8 | Backend | 📝 Planned |
| 84.2 | DocVQA OCR integration | 5 | Backend | 📝 Planned |
| 84.3 | SlideVQA multi-image processor | 5 | Backend | 📝 Planned |
| 84.4 | PDF text extraction fallback | 3 | Backend | 📝 Planned |

### Feature 84.1: Asset Downloader with Caching (8 SP)

**Challenge:** Visual datasets reference external assets

```yaml
Problem:
  - DocVQA images: ~2GB total
  - SlideVQA decks: ~5GB total
  - Downloads may fail/timeout
  - Re-downloading wastes time

Solution:
  - Implement caching layer
  - Retry logic with exponential backoff
  - Checksum verification
  - Graceful degradation (skip unavailable)
```

**Implementation:**
```python
class AssetCache:
    """Persistent cache for downloaded assets."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.index = self.load_index()

    async def download(
        self,
        url: str,
        expected_hash: str = None
    ) -> Optional[Path]:
        """Download asset with caching and verification."""

    def get_cached(self, url: str) -> Optional[Path]:
        """Return cached path if exists."""

    def verify_checksum(self, path: Path, expected: str) -> bool:
        """Verify SHA256 checksum."""

class AssetDownloader:
    """Download assets from HuggingFace/URLs."""

    async def download_batch(
        self,
        urls: List[str],
        max_concurrent: int = 5,
        timeout: float = 60.0
    ) -> Dict[str, Path]:
        """Download multiple assets with progress."""
```

**Storage Structure:**
```
data/ragas_assets/
├── cache_index.json
├── docvqa/
│   ├── doc_001.png
│   └── doc_002.png
├── slidevqa/
│   ├── deck_001/
│   │   ├── slide_001.png
│   │   └── slide_002.png
│   └── deck_002/
└── pdfs/
    ├── arxiv_001.pdf
    └── arxiv_002.pdf
```

**Acceptance Criteria:**
- [ ] Cache hit rate >90% after first download
- [ ] Failed downloads logged with reasons
- [ ] Checksum verification for all assets
- [ ] Progress reporting during download

### Feature 84.2: DocVQA OCR Integration (5 SP)

**Challenge:** DocVQA provides images, not text

```yaml
Problem:
  - Original dataset has pre-extracted OCR tokens
  - Our Docling OCR may produce different text
  - Comparing both is important

Approach:
  - Mode A: Use dataset OCR (benchmark comparison)
  - Mode B: Use Docling OCR (end-to-end validation)
  - Report both metrics
```

**Implementation:**
```python
class DocVQAAdapter(DatasetAdapter):
    """Adapter for DocVQA with dual OCR modes."""

    def __init__(self, ocr_mode: str = "dataset"):
        self.ocr_mode = ocr_mode  # "dataset" or "docling"
        self.docling_client = DoclingClient() if ocr_mode == "docling" else None

    async def adapt(self, record: Dict, image_path: Path) -> NormalizedSample:
        if self.ocr_mode == "dataset":
            context_text = " ".join(record.get("ocr_tokens", []))
        else:
            context_text = await self.docling_client.ocr_image(image_path)

        return NormalizedSample(
            question=record["question"],
            ground_truth=record["answers"][0],
            contexts=[context_text],
            doc_type="pdf_ocr",
            metadata={
                "ocr_mode": self.ocr_mode,
                "image_path": str(image_path),
                "docId": record.get("docId"),
            }
        )
```

**Target Quota:** 100 PDF/OCR samples (50 dataset OCR + 50 Docling OCR)

**Acceptance Criteria:**
- [ ] Both OCR modes functional
- [ ] Metrics reported separately for comparison
- [ ] OCR quality metrics (CER) computed on subset

### Feature 84.3: SlideVQA Multi-Image Processor (5 SP)

**Challenge:** Questions span multiple slides

```yaml
Problem:
  - Single question references multiple images
  - Slide order matters
  - Visual elements carry meaning

Approach:
  - Process each slide independently
  - Combine OCR + VLM description
  - Preserve slide ordering in metadata
```

**Implementation:**
```python
class SlideVQAAdapter(DatasetAdapter):
    """Adapter for SlideVQA with multi-slide handling."""

    def __init__(self):
        self.docling = DoclingClient()
        self.vlm = VLMMetadataExtractor()  # Sprint 66 component

    async def adapt(
        self,
        record: Dict,
        slide_paths: List[Path]
    ) -> NormalizedSample:
        contexts = []

        for idx, slide_path in enumerate(slide_paths):
            ocr_text = await self.docling.ocr_image(slide_path)
            vlm_desc = await self.vlm.describe_slide(slide_path)

            combined = f"[Slide {idx+1}]\n{ocr_text}\n\nVisual: {vlm_desc}"
            contexts.append(combined)

        return NormalizedSample(
            question=record["question"],
            ground_truth=record["answer"],
            contexts=contexts,
            doc_type="slide",
            metadata={
                "num_slides": len(slide_paths),
                "evidence_slides": record.get("evidence_slide_ids", []),
            }
        )
```

**Target Quota:** 50 slide samples

**Acceptance Criteria:**
- [ ] Multi-slide contexts correctly ordered
- [ ] VLM descriptions add value (human validation)
- [ ] Evidence slides highlighted in metadata

### Feature 84.4: PDF Text Extraction Fallback (3 SP)

**Challenge:** Some PDFs may not have pre-extracted text

```python
class PDFTextExtractor:
    """Extract text from PDFs with fallback chain."""

    def __init__(self):
        self.docling = DoclingClient()

    async def extract(
        self,
        pdf_path: Path,
        dataset_text: Optional[str] = None
    ) -> str:
        """Extract text with fallback to Docling."""

        # Prefer dataset-provided text (benchmark consistency)
        if dataset_text and len(dataset_text) > 100:
            return dataset_text

        # Fall back to Docling extraction
        return await self.docling.parse_pdf(pdf_path)
```

**Target Quota:** 50 PDF text samples

### Sprint 84 Deliverables

| Artifact | Location |
|----------|----------|
| Asset cache | `data/ragas_assets/` |
| Phase 3 dataset | `data/evaluation/ragas_phase3_200.jsonl` |
| Full 1000 dataset | `data/evaluation/ragas_1000.jsonl` |
| Manifest | `data/evaluation/ragas_manifest_1000.csv` |

### Sprint 84 Success Criteria

- [ ] 1000 total samples (500 + 300 + 200)
- [ ] Visual doc_types included (pdf_ocr, slide, pdf_text)
- [ ] Asset download pipeline stable
- [ ] Full RAGAS evaluation completes without errors

---

## Post-Implementation: Evaluation Runs

### Initial Evaluation (Sprint 84 End)

```bash
# Run full 1000-sample evaluation (estimated: 100-160 hours)
# Split by doc_type for parallelization

# Phase 1: Text-only (fast)
poetry run python scripts/run_ragas_evaluation.py \
  --dataset data/evaluation/ragas_phase1_500.jsonl \
  --namespace ragas_benchmark_v1 \
  --mode hybrid \
  --output-dir data/evaluation/results/v1/

# Phase 2: Structured (medium)
poetry run python scripts/run_ragas_evaluation.py \
  --dataset data/evaluation/ragas_phase2_300.jsonl \
  --namespace ragas_benchmark_v1 \
  --mode hybrid \
  --output-dir data/evaluation/results/v1/

# Phase 3: Visual (slow)
poetry run python scripts/run_ragas_evaluation.py \
  --dataset data/evaluation/ragas_phase3_200.jsonl \
  --namespace ragas_benchmark_v1 \
  --mode hybrid \
  --output-dir data/evaluation/results/v1/
```

### Expected Timeline

| Phase | Samples | Est. Time (Hybrid) | Est. Time (All 3 Modes) |
|-------|---------|-------------------|-------------------------|
| Phase 1 | 500 | 50-80 hours | 150-240 hours |
| Phase 2 | 300 | 30-48 hours | 90-144 hours |
| Phase 3 | 200 | 20-32 hours | 60-96 hours |
| **Total** | **1000** | **100-160 hours** | **300-480 hours** |

### Reporting

After evaluation, generate:
- `data/evaluation/results/v1/RAGAS_1000_REPORT.md`
- Breakdown by doc_type, question_type, difficulty
- Comparison with 5-sample baseline
- Statistical significance tests

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| HuggingFace API rate limits | Medium | High | Local caching, retry logic |
| Dataset schema changes | Low | Medium | Version pinning, adapter tests |
| Asset download failures | Medium | Medium | Graceful degradation, fallbacks |
| Evaluation timeout | High | High | Split by doc_type, checkpointing |
| OCR quality variance | Medium | Medium | Dual-mode evaluation |

---

## Dependencies

- **RAGAS 0.4.2** - Already integrated (Sprint 79)
- **Docling CUDA** - Already integrated (ADR-027)
- **VLM Metadata** - Already integrated (Sprint 66)
- **HuggingFace datasets** - Add to pyproject.toml

```toml
# pyproject.toml addition
[tool.poetry.dependencies]
datasets = "^2.18.0"
```

---

## Open Questions

1. **Namespace strategy:** Separate namespace per benchmark version, or reuse?
2. **Ingestion approach:** Direct context injection vs. full document ingestion?
3. **Language:** English-only or include German subset?
4. **Update frequency:** One-time benchmark or continuous update cycle?

---

## References

- [ADR-048: RAGAS 1000-Sample Benchmark Strategy](../adr/ADR-048-ragas-1000-sample-benchmark.md)
- [RAGAS_JOURNEY.md](../ragas/RAGAS_JOURNEY.md)
- [HotpotQA Dataset](https://huggingface.co/datasets/hotpot_qa)
- [T2-RAGBench Dataset](https://huggingface.co/datasets/G4KMU/t2-ragbench)
- [DocVQA Dataset](https://huggingface.co/datasets/nielsr/docvqa_1200_examples)
