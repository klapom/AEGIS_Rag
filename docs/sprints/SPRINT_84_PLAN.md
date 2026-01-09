# Sprint 84 Plan: RAGAS Phase 3 - Visual Assets

**Epic:** 1000-Sample Stratified RAGAS Evaluation Benchmark
**Phase:** 3 of 3 (FINAL)
**ADR Reference:** [ADR-048](../adr/ADR-048-ragas-1000-sample-benchmark.md)
**Prerequisite:** Sprint 83 (Phase 2 complete)
**Duration:** 10-14 days
**Total Story Points:** 21 SP
**Status:** 📝 Planned

---

## Sprint Goal

Complete the 1000-sample benchmark with **200 visual asset samples**:
- **DocVQA:** Scanned document images with OCR (100 samples)
- **SlideVQA:** Multi-slide presentation Q&A (50 samples)
- **Open RAG Bench:** PDF text documents (50 samples)

**Key Challenge:** This phase involves downloading 15-20GB of assets and handling complex image processing pipelines.

---

## Context

### After Sprint 83
- 800 samples (clean_text, log_ticket, table, code_config)
- Statistical rigor package integrated
- ±3.5% confidence interval

### Target State (Sprint 84)
- **1000 total samples** (800 + 200)
- **7 doc_types:** clean_text, log_ticket, table, code_config, pdf_ocr, slide, pdf_text
- **Full benchmark complete**
- ±3% confidence interval

---

## Features

| # | Feature | SP | Priority | Status |
|---|---------|-----|----------|--------|
| 84.1 | Asset downloader with caching | 8 | P0 | 📝 Planned |
| 84.2 | DocVQA OCR integration | 5 | P0 | 📝 Planned |
| 84.3 | SlideVQA multi-image processor | 5 | P1 | 📝 Planned |
| 84.4 | PDF text extraction fallback | 3 | P1 | 📝 Planned |

---

## Feature 84.1: Asset Downloader with Caching (8 SP)

### Description
Robust asset download infrastructure for visual datasets with local caching.

### Challenge

```yaml
Problem:
  - DocVQA images: ~2GB total (1200 document images)
  - SlideVQA decks: ~5GB total (multi-image presentations)
  - Open RAG Bench PDFs: ~10GB total (arXiv papers)
  - Downloads may fail/timeout (network issues)
  - Re-downloading wastes hours

Solution:
  - Persistent local cache with index
  - Retry logic with exponential backoff
  - SHA256 checksum verification
  - Graceful degradation (skip unavailable, log reason)
  - Progress reporting for long downloads
```

### Storage Structure

```
data/ragas_assets/
├── cache_index.json           # Download status, checksums
├── docvqa/
│   ├── doc_001.png           # ~500KB each
│   ├── doc_002.png
│   └── ...                   # ~1200 files
├── slidevqa/
│   ├── deck_001/
│   │   ├── slide_001.png
│   │   ├── slide_002.png
│   │   └── slide_003.png
│   └── deck_002/
│       └── ...
└── pdfs/
    ├── arxiv_2301.00001.pdf  # ~2-10MB each
    └── ...
```

### Implementation

```python
# scripts/ragas_benchmark/asset_manager.py

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional
import httpx
from tqdm.asyncio import tqdm

class AssetCache:
    """Persistent cache for downloaded assets."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.cache_dir / "cache_index.json"
        self.index = self._load_index()

    def _load_index(self) -> Dict:
        """Load cache index from disk."""
        if self.index_path.exists():
            return json.loads(self.index_path.read_text())
        return {"files": {}, "stats": {"hits": 0, "misses": 0, "errors": 0}}

    def _save_index(self):
        """Save cache index to disk."""
        self.index_path.write_text(json.dumps(self.index, indent=2))

    def get_cached(self, url: str) -> Optional[Path]:
        """Return cached path if exists and valid."""
        if url in self.index["files"]:
            entry = self.index["files"][url]
            path = self.cache_dir / entry["path"]
            if path.exists():
                self.index["stats"]["hits"] += 1
                return path
        self.index["stats"]["misses"] += 1
        return None

    def add_to_cache(self, url: str, path: Path, checksum: str):
        """Add downloaded file to cache index."""
        relative_path = path.relative_to(self.cache_dir)
        self.index["files"][url] = {
            "path": str(relative_path),
            "checksum": checksum,
            "downloaded_at": datetime.now().isoformat(),
        }
        self._save_index()

    def verify_checksum(self, path: Path, expected: str) -> bool:
        """Verify SHA256 checksum of file."""
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest() == expected


class AssetDownloader:
    """Download assets with retry logic and progress reporting."""

    def __init__(
        self,
        cache: AssetCache,
        max_retries: int = 3,
        timeout: float = 60.0,
        max_concurrent: int = 5
    ):
        self.cache = cache
        self.max_retries = max_retries
        self.timeout = timeout
        self.max_concurrent = max_concurrent

    async def download(
        self,
        url: str,
        dest_subdir: str,
        filename: Optional[str] = None,
        expected_checksum: Optional[str] = None
    ) -> Optional[Path]:
        """
        Download single asset with caching and retry.

        Args:
            url: Source URL
            dest_subdir: Subdirectory within cache (e.g., "docvqa")
            filename: Override filename (default: from URL)
            expected_checksum: SHA256 to verify (optional)

        Returns:
            Path to downloaded file, or None if failed
        """
        # Check cache first
        cached = self.cache.get_cached(url)
        if cached:
            return cached

        # Determine destination path
        if filename is None:
            filename = url.split("/")[-1]
        dest_dir = self.cache.cache_dir / dest_subdir
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / filename

        # Download with retry
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, follow_redirects=True)
                    response.raise_for_status()

                    # Write to file
                    dest_path.write_bytes(response.content)

                    # Verify checksum if provided
                    if expected_checksum:
                        if not self.cache.verify_checksum(dest_path, expected_checksum):
                            dest_path.unlink()
                            raise ValueError(f"Checksum mismatch for {url}")

                    # Compute and store checksum
                    actual_checksum = hashlib.sha256(response.content).hexdigest()
                    self.cache.add_to_cache(url, dest_path, actual_checksum)

                    return dest_path

            except Exception as e:
                wait_time = 2 ** attempt  # Exponential backoff
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    self.cache.index["stats"]["errors"] += 1
                    logger.error(f"Failed to download {url} after {self.max_retries} attempts: {e}")
                    return None

    async def download_batch(
        self,
        urls: List[str],
        dest_subdir: str,
        progress_desc: str = "Downloading"
    ) -> Dict[str, Optional[Path]]:
        """
        Download multiple assets with concurrency limit.

        Returns:
            Dict mapping URL -> Path (or None if failed)
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)
        results = {}

        async def download_with_semaphore(url: str):
            async with semaphore:
                return url, await self.download(url, dest_subdir)

        tasks = [download_with_semaphore(url) for url in urls]

        for coro in tqdm.as_completed(tasks, desc=progress_desc, total=len(urls)):
            url, path = await coro
            results[url] = path

        return results
```

### Usage

```bash
# Pre-download all Phase 3 assets (run before evaluation)
poetry run python scripts/ragas_benchmark/download_assets.py \
  --datasets docvqa slidevqa open_ragbench \
  --cache-dir data/ragas_assets/ \
  --max-concurrent 10

# Expected output:
# Downloading DocVQA assets: 100%|████████| 1200/1200 [15:23<00:00]
# Downloading SlideVQA assets: 100%|████████| 500/500 [22:45<00:00]
# Downloading PDF assets: 100%|████████| 200/200 [08:12<00:00]
#
# Summary:
#   Downloaded: 1850 files (17.2 GB)
#   Cached: 50 files (hit rate: 2.6%)
#   Failed: 12 files (logged to errors.json)
```

### Acceptance Criteria

- [ ] Cache hit rate >90% after first download
- [ ] Failed downloads logged with reasons
- [ ] Checksum verification for all assets
- [ ] Progress reporting for batch downloads
- [ ] Graceful handling of 404s and timeouts
- [ ] Resume capability (partial downloads)

---

## Feature 84.2: DocVQA OCR Integration (5 SP)

### Description
Process DocVQA scanned document images with dual-mode OCR.

### Challenge

```yaml
Problem:
  - DocVQA provides IMAGES, not text
  - Dataset includes pre-extracted OCR tokens (Tesseract-based)
  - Our Docling OCR may produce different text
  - Comparison with benchmarks requires consistent OCR

Solution:
  - Mode A: Use dataset-provided OCR (benchmark comparison)
  - Mode B: Use Docling CUDA OCR (end-to-end validation)
  - Report BOTH metrics for transparency
  - Compute OCR quality metrics (CER) on subset
```

### Dataset Schema (DocVQA)

```python
# nielsr/docvqa_1200_examples record
{
    "questionId": 1234,
    "question": "What is the date on this invoice?",
    "answers": ["March 15, 2019", "15 March 2019"],  # Multiple valid answers
    "image": <PIL.Image>,  # Or path to image
    "docId": "doc_001",
    "ocr_tokens": ["March", "15", ",", "2019", "INVOICE", ...],
    "ocr_boxes": [[x1, y1, x2, y2], ...],  # Bounding boxes
}
```

### Implementation

```python
# scripts/ragas_benchmark/adapters/docvqa.py

class DocVQAAdapter(DatasetAdapter):
    """Adapter for DocVQA with dual OCR modes."""

    def __init__(
        self,
        ocr_mode: str = "dataset",  # "dataset" or "docling"
        docling_url: str = "http://localhost:5001"
    ):
        self.ocr_mode = ocr_mode
        self.docling_client = None
        if ocr_mode == "docling":
            self.docling_client = DoclingClient(docling_url)

    def get_doc_type(self) -> str:
        return "pdf_ocr"

    async def adapt(
        self,
        record: Dict,
        image_path: Optional[Path] = None
    ) -> NormalizedSample:
        """
        Adapt DocVQA record with specified OCR mode.

        Args:
            record: DocVQA record from HuggingFace
            image_path: Path to downloaded image (for docling mode)
        """
        # Extract text based on OCR mode
        if self.ocr_mode == "dataset":
            # Use pre-extracted OCR tokens from dataset
            context_text = self._tokens_to_text(record.get("ocr_tokens", []))
        else:
            # Use Docling CUDA OCR
            if image_path is None:
                raise ValueError("image_path required for docling mode")
            context_text = await self._docling_ocr(image_path)

        # Handle multiple valid answers (take first as ground truth)
        answers = record.get("answers", [])
        ground_truth = answers[0] if answers else ""

        return NormalizedSample(
            id=f"docvqa_{record.get('docId', record.get('questionId'))}",
            question=record["question"],
            ground_truth=ground_truth,
            contexts=[context_text],
            doc_type="pdf_ocr",
            question_type=self._classify_question(record),
            difficulty=self._assign_difficulty(record),
            source_dataset="docvqa",
            metadata={
                "docId": record.get("docId"),
                "questionId": record.get("questionId"),
                "ocr_mode": self.ocr_mode,
                "num_answers": len(answers),
                "all_answers": answers,  # For evaluation flexibility
                "image_path": str(image_path) if image_path else None,
                "ocr_token_count": len(record.get("ocr_tokens", [])),
            }
        )

    def _tokens_to_text(self, tokens: List[str]) -> str:
        """
        Convert OCR tokens to readable text.

        Handles spacing around punctuation.
        """
        if not tokens:
            return ""

        text_parts = []
        for i, token in enumerate(tokens):
            # Don't add space before punctuation
            if token in ".,;:!?)]}":
                if text_parts:
                    text_parts[-1] += token
                else:
                    text_parts.append(token)
            # Don't add space after opening brackets
            elif i > 0 and tokens[i-1] in "([{":
                text_parts[-1] += token
            else:
                text_parts.append(token)

        return " ".join(text_parts)

    async def _docling_ocr(self, image_path: Path) -> str:
        """
        Run Docling CUDA OCR on image.

        Uses existing Docling container (ADR-027).
        """
        return await self.docling_client.ocr_image(image_path)

    def _classify_question(self, record: Dict) -> str:
        """Classify DocVQA question type."""
        question = record["question"].lower()

        if any(w in question for w in ["date", "when", "year", "month"]):
            return "entity"  # Date extraction
        if any(w in question for w in ["how much", "total", "amount", "price"]):
            return "numeric"
        if any(w in question for w in ["what is", "name", "who"]):
            return "lookup"
        return "lookup"
```

### Dual-Mode Evaluation Strategy

```python
# Generate BOTH dataset OCR and Docling OCR samples
# for comparison in evaluation

async def generate_docvqa_samples(
    dataset,
    image_cache: AssetCache,
    target_count: int = 100
) -> Tuple[List[NormalizedSample], List[NormalizedSample]]:
    """
    Generate DocVQA samples in both OCR modes.

    Returns:
        Tuple of (dataset_ocr_samples, docling_ocr_samples)
    """
    dataset_adapter = DocVQAAdapter(ocr_mode="dataset")
    docling_adapter = DocVQAAdapter(ocr_mode="docling")

    dataset_samples = []
    docling_samples = []

    for record in dataset[:target_count]:
        image_path = image_cache.get_cached(record["image_url"])

        # Dataset OCR mode
        sample_dataset = await dataset_adapter.adapt(record)
        dataset_samples.append(sample_dataset)

        # Docling OCR mode (if image available)
        if image_path:
            sample_docling = await docling_adapter.adapt(record, image_path)
            docling_samples.append(sample_docling)

    return dataset_samples, docling_samples
```

### OCR Quality Metrics

```python
def compute_ocr_quality(
    dataset_text: str,
    docling_text: str
) -> Dict[str, float]:
    """
    Compute OCR quality metrics between two extractions.

    Returns:
        Dict with CER (Character Error Rate), WER (Word Error Rate)
    """
    import editdistance

    # Character Error Rate
    cer = editdistance.eval(dataset_text, docling_text) / max(len(dataset_text), 1)

    # Word Error Rate
    dataset_words = dataset_text.split()
    docling_words = docling_text.split()
    wer = editdistance.eval(dataset_words, docling_words) / max(len(dataset_words), 1)

    return {"cer": cer, "wer": wer}
```

### Target Quota

| Category | Count |
|----------|-------|
| pdf_ocr (DocVQA) | 100 |
| **By OCR Mode:** | |
| - dataset_ocr | 50 (benchmark) |
| - docling_ocr | 50 (validation) |
| **Question Types:** | |
| - lookup | 40 |
| - entity | 30 |
| - numeric | 30 |

### Acceptance Criteria

- [ ] 100 DocVQA samples processed
- [ ] Both OCR modes functional
- [ ] OCR quality metrics (CER/WER) computed on 20-sample subset
- [ ] Multiple valid answers handled
- [ ] Image paths stored in metadata

---

## Feature 84.3: SlideVQA Multi-Image Processor (5 SP)

### Description
Process SlideVQA presentations with multi-slide context aggregation.

### Challenge

```yaml
Problem:
  - Single question spans MULTIPLE slide images
  - Slide ordering matters for context
  - Visual elements (charts, diagrams) carry meaning
  - Evidence may be on specific slides only

Solution:
  - Process each slide independently (OCR + VLM)
  - Preserve slide ordering in chunk structure
  - Combine per-slide contexts with ordering metadata
  - Track which slides contain answer evidence
```

### Dataset Schema (SlideVQA)

```python
# NTT-hil-insight/SlideVQA record
{
    "question": "What is the main conclusion of the presentation?",
    "answer": "AI will transform healthcare by 2030",
    "deck_id": "presentation_456",
    "slides": [
        {"slide_id": 1, "image_path": "deck_456/slide_001.png"},
        {"slide_id": 2, "image_path": "deck_456/slide_002.png"},
        {"slide_id": 3, "image_path": "deck_456/slide_003.png"},
    ],
    "evidence_slide_ids": [2, 3],  # Answer found on these slides
    "ocr_per_slide": {
        1: "Introduction to AI in Healthcare...",
        2: "Current Applications: ...",
        3: "Conclusion: AI will transform healthcare by 2030",
    }
}
```

### Implementation

```python
# scripts/ragas_benchmark/adapters/slidevqa.py

class SlideVQAAdapter(DatasetAdapter):
    """Adapter for SlideVQA with multi-slide handling."""

    def __init__(
        self,
        docling_url: str = "http://localhost:5001",
        use_vlm: bool = True
    ):
        self.docling_client = DoclingClient(docling_url)
        self.use_vlm = use_vlm
        if use_vlm:
            # VLM from Sprint 66
            self.vlm = VLMMetadataExtractor()

    def get_doc_type(self) -> str:
        return "slide"

    async def adapt(
        self,
        record: Dict,
        slide_paths: List[Path]
    ) -> NormalizedSample:
        """
        Adapt SlideVQA record with multi-slide processing.

        Args:
            record: SlideVQA record
            slide_paths: Ordered list of paths to slide images
        """
        slide_contexts = []

        for idx, slide_path in enumerate(slide_paths):
            slide_context = await self._process_slide(
                slide_path,
                slide_index=idx,
                is_evidence=idx in record.get("evidence_slide_ids", [])
            )
            slide_contexts.append(slide_context)

        # Combine all slide contexts
        combined_context = self._combine_slide_contexts(slide_contexts)

        return NormalizedSample(
            id=f"slidevqa_{record['deck_id']}_{record.get('question_id', 0)}",
            question=record["question"],
            ground_truth=record["answer"],
            contexts=[combined_context],
            doc_type="slide",
            question_type=self._classify_question(record),
            difficulty=self._assign_difficulty(record),
            source_dataset="slidevqa",
            metadata={
                "deck_id": record["deck_id"],
                "num_slides": len(slide_paths),
                "evidence_slide_ids": record.get("evidence_slide_ids", []),
                "per_slide_contexts": slide_contexts,  # For detailed analysis
                "vlm_enabled": self.use_vlm,
            }
        )

    async def _process_slide(
        self,
        slide_path: Path,
        slide_index: int,
        is_evidence: bool
    ) -> Dict:
        """
        Process single slide with OCR and optional VLM.

        Returns:
            Dict with slide_index, ocr_text, vlm_description, combined_text
        """
        # OCR extraction
        ocr_text = await self.docling_client.ocr_image(slide_path)

        # VLM description (optional)
        vlm_description = ""
        if self.use_vlm:
            vlm_description = await self.vlm.describe_slide(slide_path)

        # Combine for context
        combined = f"[Slide {slide_index + 1}]"
        if is_evidence:
            combined += " [EVIDENCE]"
        combined += f"\n{ocr_text}"
        if vlm_description:
            combined += f"\n\nVisual Description: {vlm_description}"

        return {
            "slide_index": slide_index,
            "is_evidence": is_evidence,
            "ocr_text": ocr_text,
            "vlm_description": vlm_description,
            "combined_text": combined,
        }

    def _combine_slide_contexts(
        self,
        slide_contexts: List[Dict]
    ) -> str:
        """
        Combine per-slide contexts into single context string.

        Preserves slide ordering and evidence markers.
        """
        parts = []
        for ctx in slide_contexts:
            parts.append(ctx["combined_text"])
        return "\n\n---\n\n".join(parts)

    def _classify_question(self, record: Dict) -> str:
        """Classify SlideVQA question type."""
        question = record["question"].lower()

        if any(w in question for w in ["conclusion", "summary", "main point"]):
            return "multihop"  # Requires reading multiple slides
        if any(w in question for w in ["compare", "difference", "vs"]):
            return "comparison"
        if any(w in question for w in ["how many", "count", "number"]):
            return "numeric"
        if any(w in question for w in ["what is", "who", "when"]):
            return "lookup"
        return "multihop"  # Default for presentations
```

### Target Quota

| Category | Count |
|----------|-------|
| slide (SlideVQA) | 50 |
| **Question Types:** | |
| - multihop | 25 |
| - lookup | 15 |
| - comparison | 10 |

### Acceptance Criteria

- [ ] 50 SlideVQA samples processed
- [ ] Multi-slide contexts correctly ordered
- [ ] VLM descriptions integrated
- [ ] Evidence slides marked in metadata
- [ ] Handles variable deck sizes (2-20 slides)

---

## Feature 84.4: PDF Text Extraction Fallback (3 SP)

### Description
Process Open RAG Bench PDF documents with text extraction fallback chain.

### Implementation

```python
# scripts/ragas_benchmark/adapters/openragbench.py

class OpenRAGBenchAdapter(DatasetAdapter):
    """Adapter for Open RAG Bench (arXiv PDFs)."""

    def __init__(self, docling_url: str = "http://localhost:5001"):
        self.docling_client = DoclingClient(docling_url)

    def get_doc_type(self) -> str:
        return "pdf_text"

    async def adapt(
        self,
        record: Dict,
        pdf_path: Optional[Path] = None
    ) -> NormalizedSample:
        """
        Adapt Open RAG Bench record with PDF fallback.

        Priority:
        1. Use dataset-provided extracted text (if available)
        2. Fall back to Docling PDF extraction
        """
        # Try dataset-provided text first
        context_text = record.get("context") or record.get("passage") or ""

        # Fall back to Docling if text is short/missing
        if len(context_text) < 100 and pdf_path:
            context_text = await self.docling_client.parse_pdf(pdf_path)

        return NormalizedSample(
            id=f"openragbench_{record.get('paper_id', record.get('id'))}",
            question=record["question"],
            ground_truth=record.get("answer", record.get("ground_truth", "")),
            contexts=[context_text],
            doc_type="pdf_text",
            question_type=self._classify_question(record),
            difficulty="D2",  # Academic papers are generally medium difficulty
            source_dataset="open_ragbench",
            metadata={
                "paper_id": record.get("paper_id"),
                "extraction_method": "dataset" if len(record.get("context", "")) >= 100 else "docling",
                "pdf_path": str(pdf_path) if pdf_path else None,
            }
        )
```

### Target Quota

| Category | Count |
|----------|-------|
| pdf_text (Open RAG Bench) | 50 |
| **Question Types:** | |
| - lookup | 20 |
| - definition | 15 |
| - multihop | 15 |

---

## Deliverables

| Artifact | Location | Description |
|----------|----------|-------------|
| Asset manager | `scripts/ragas_benchmark/asset_manager.py` | Download & cache |
| DocVQA adapter | `scripts/ragas_benchmark/adapters/docvqa.py` | OCR integration |
| SlideVQA adapter | `scripts/ragas_benchmark/adapters/slidevqa.py` | Multi-image |
| OpenRAGBench adapter | `scripts/ragas_benchmark/adapters/openragbench.py` | PDF fallback |
| Phase 3 dataset | `data/evaluation/ragas_phase3_200.jsonl` | 200 samples |
| **Full 1000 dataset** | `data/evaluation/ragas_1000.jsonl` | **FINAL** |
| Asset cache | `data/ragas_assets/` | 15-20GB |

---

## Final Combined Dataset

```
data/evaluation/
├── ragas_phase1_500.jsonl        # Phase 1: text, logs
├── ragas_phase2_300.jsonl        # Phase 2: table, code
├── ragas_phase3_200.jsonl        # Phase 3: pdf_ocr, slide, pdf_text
├── ragas_1000.jsonl              # COMBINED FINAL
├── ragas_manifest_1000.csv       # Full manifest
└── ragas_1000_statistics.json    # Distribution stats
```

### Final Distribution

| Doc Type | Count | % |
|----------|-------|---|
| clean_text | 450 | 45% |
| log_ticket | 150 | 15% |
| table | 100 | 10% |
| code_config | 100 | 10% |
| pdf_ocr | 100 | 10% |
| slide | 50 | 5% |
| pdf_text | 50 | 5% |
| **Total** | **1000** | **100%** |

| Answerable | Count | % |
|------------|-------|---|
| True | 880 | 88% |
| False (unanswerable) | 120 | 12% |

---

## Success Criteria

- [ ] 1000 total samples in final dataset
- [ ] All 7 doc_types represented
- [ ] Asset download pipeline stable (>95% success rate)
- [ ] Full RAGAS evaluation completes without errors
- [ ] OCR quality metrics documented
- [ ] Statistical report with CI for all metrics
- [ ] Documentation complete

---

## Evaluation Timeline

After Sprint 84, run full evaluation:

| Mode | Est. Time | Samples |
|------|-----------|---------|
| Hybrid | 100-160 hours | 1000 |
| Vector | 100-160 hours | 1000 |
| Graph | 100-160 hours | 1000 |
| **Total** | **300-480 hours** | |

**Recommendation:** Run in parallel across 3 machines, or evaluate Hybrid-only first for quick results.

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Asset download failures | Medium | High | Retry logic, graceful degradation |
| Docling OCR quality issues | Medium | Medium | Dual-mode evaluation |
| SlideVQA deck size variance | Medium | Low | Variable slide handling |
| Storage constraints | Low | High | External storage, compression |
| VLM timeout | Medium | Low | Skip VLM, fallback to OCR-only |

---

## References

- [ADR-048: RAGAS 1000-Sample Benchmark Strategy](../adr/ADR-048-ragas-1000-sample-benchmark.md)
- [Sprint 82 Plan](SPRINT_82_PLAN.md) - Phase 1
- [Sprint 83 Plan](SPRINT_83_PLAN.md) - Phase 2
- [ADR-027: Docling CUDA Ingestion](../adr/ADR-027-docling-cuda-ingestion.md)
- [DocVQA Dataset](https://huggingface.co/datasets/nielsr/docvqa_1200_examples)
- [SlideVQA Repository](https://github.com/nttmdlab-nlp/SlideVQA)
- [Open RAG Bench Paper](https://arxiv.org/abs/2410.11920)
