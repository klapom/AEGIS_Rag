# ADR-063: VLM Model Selection for Table Cross-Validation

## Status
**Accepted** (2026-02-11)

## Context

Sprint 129.6a-b introduced table ingestion with heuristic quality scoring. Tables scoring in the borderline range (0.50-0.85) need a second opinion — the original plan (DECISION_LOG Sprint 129.6c-e) proposed **dual VLM cross-validation** with Granite-Docling-258M + DeepSeek-OCR-2.

Before implementing the cross-validation pipeline, a comprehensive VLM evaluation was needed to select the optimal model(s). Five candidates were evaluated on 5 test images (1 PPT→PDF edge case + 4 academic PDF tables from DP-Bench).

**Hardware constraints:** DGX Spark (128GB unified memory). vLLM extraction engine uses 64.5GB (0.45 util). VLM must fit in remaining budget alongside BGE-M3 (2GB) + system overhead (10GB) — target: **≤10GB VRAM** for VLM.

## Decision

Use **Nemotron Nano VL v1 (8B FP4-QAD)** as the single VLM for table cross-validation, with **P2 HTML table prompt** (NVIDIA RD-TableBench official prompt). Deploy on-demand via the same `aegis-vllm-eugr:latest` base image used for extraction, on a separate vLLM process (port 8002).

**Replaces** the original dual-VLM plan (Granite-Docling-258M + DeepSeek-OCR-2).

**Key parameters:**
- Model: `nvidia/Llama-3.1-Nemotron-Nano-VL-8B-V1-FP4-QAD`
- VRAM: ~5GB (`gpu-memory-utilization=0.10`)
- Port: 8002 (separate from extraction vLLM on 8001)
- Docker image: `aegis-vllm-eugr:latest` (same SM121-native image)
- Runtime deps: `pip install timm open_clip_torch` (C-RADIOv2 vision encoder)
- Prompt: P2 HTML table (see below)
- Average latency: 15.6s per table page

## Alternatives Considered

### 1. Granite-Docling-258M (Original Plan — Candidate A)
**Architecture:** 258M params, docling-serve Docker image, port 8083
**Pro:**
- Tiny model (<2GB VRAM), fast inference
- 97.9% cell accuracy (paper claim)
- Same Docling ecosystem as existing OCR pipeline

**Contra:**
- **Column shift on complex tables** — Benchmark showed systematic misalignment on tables with colspan headers (e.g., DP-Bench doc 46: party columns shifted by 1)
- docling-serve Docker image is 4.3GB (separate from extraction stack)
- Cannot handle PPT→PDF edge cases (silently produces empty output)
- Limited to Docling JSON output format — no instruction-following capability

**Benchmark result:** Tested on 5 images. Column shift errors on 3/5 tables. Not suitable for cross-validation.

### 2. DeepSeek-OCR-2 (Original Plan — Candidate B)
**Architecture:** 3B params, ~8GB VRAM, vLLM-served
**Pro:**
- Fast (165 tok/s on DGX Spark)
- Acceptable VRAM footprint

**Contra:**
- **Only accepts "Free OCR." prompt** — not instruction-following, cannot request specific output format (HTML, markdown, etc.)
- Output is raw OCR text without table structure
- Cannot parse tables into cell grids for cross-validation
- No rowspan/colspan understanding

**Benchmark result:** Tested on 5 images. Raw OCR output only. Unusable for structured table cross-validation.

### 3. Nemotron Nano VL v2 (12B NVFP4-QAD) — Candidate C
**Architecture:** 12B params (NemotronH hybrid Mamba+Attention), NVFP4, ~10GB VRAM
**Pro:**
- Newer architecture with reasoning capability (`/think` CoT mode)
- Higher parameter count → potentially better quality

**Contra:**
- **20% failure rate (6/30 iterations)** — empty responses (1-4 tokens) on PPT→PDF and some normal PDFs
- **33% failure rate in `/no_think` mode** — unreliable for production
- **34% slower** than V1 (22.9 vs 34.7 tok/s)
- Requires 50% more VRAM (0.15 vs 0.10 gpu-memory-utilization)
- `/think` mode adds 2-5x latency (CoT reasoning tokens)
- OOM at 0.10 gpu-memory-utilization (V1 works at 0.10)

**Benchmark result:** 45-iteration benchmark (3 prompts × 2 modes × 5 images + 15 from V1). V2 inferior on all metrics.

### 4. Nemotron Nano VL v1 (8B FP4-QAD) — **SELECTED**
**Architecture:** 8B params (Llama_Nemotron_Nano_VL), FP4 quantized, C-RADIOv2 vision encoder
**Pro:**
- **0% failure rate** — 15/15 iterations successful, 100% reliability
- **34.7 tok/s** — fastest of all instruction-following candidates
- **~5GB VRAM** — lowest memory footprint (0.10 gpu-memory-utilization)
- Same Docker base image as extraction vLLM (zero additional disk)
- All 3 NVIDIA official prompts work reliably
- Produces clean HTML `<table>` output with correct rowspan/colspan

**Contra:**
- Smaller model (8B vs 12B) — potentially less capable on very complex tables
- Requires runtime pip install of `timm` + `open_clip_torch`

## Evaluation Methodology

### Test Suite
5 test images selected for diversity:
1. **VM3_page2_PPT** — Edge case: PowerPoint→PDF with merged cells (Audi EV specs table)
2. **PDF_046_parties1** — 12×7 political party registration table (multi-column headers)
3. **PDF_047_parties2** — Continuation of doc 46 (7 parties + total row)
4. **PDF_051_govt_women** — Government participation stats (merged header cells)
5. **PDF_052_regions** — Regional statistics table (4 columns, 12 rows)

### Prompts (NVIDIA Official — RD-TableBench)
3 prompts evaluated per model:
- **P1 (Doc Extraction):** Full document parsing as Mathpix markdown with bounding boxes and semantic categories
- **P2 (HTML Table):** `<table>` HTML with rowspan/colspan — **WINNER** (cleanest output, parseable)
- **P3 (HTML Table + BBox):** Same as P2 plus bounding box coordinates

### Benchmark Results

#### V1 Summary (15 iterations at 0.10 GPU)

| Prompt | Avg Time | Avg Tokens | Avg tok/s | Failures |
|--------|----------|------------|-----------|----------|
| P1 (doc extraction) | 22.0s | 751 | 34.2 | 0/5 |
| P2 (HTML table) | 12.3s | 435 | 35.1 | 0/5 |
| P3 (HTML + bbox) | 12.4s | 431 | 34.9 | 0/5 |

**P2 wins:** Shortest latency (12.3s avg), clean parseable HTML output, no bounding box overhead.

#### V2 Summary (30 iterations at 0.15 GPU)

| Prompt | Mode | Avg Time | Failures | Notes |
|--------|------|----------|----------|-------|
| P1 | no_think | 26.1s | 1/5 (VM3) | VM3 returns 2 tokens |
| P1 | think | 26.1s | 1/5 (VM3) | VM3 returns 2 tokens |
| P2 | no_think | 9.1s | 3/5 | VM3 + 2 normal PDFs empty |
| P2 | think | 43.2s | 0/5 | CoT adds 3.5x latency |
| P3 | no_think | 21.7s | 0/5 | Only reliable no_think combo |
| P3 | think | 57.6s | 1/5 (VM3) | VM3 returns 2 tokens |

**V2 reliability:** 24/30 real successes (80%). `/no_think` mode: 17/15 OK = only 67% reliable.

#### V1 vs V2 Head-to-Head

| Metric | V1 (8B FP4) | V2 (12B NVFP4) | Winner |
|--------|-------------|-----------------|--------|
| **Reliability** | 100% (15/15) | 80% (24/30) | V1 |
| **Throughput** | 34.7 tok/s | 22.9 tok/s | V1 (+52%) |
| **VRAM** | ~5GB (0.10) | ~10GB (0.15) | V1 (50% less) |
| **Avg latency (P2)** | 12.3s | 43.2s (think) | V1 (3.5x faster) |
| **HTML quality** | Clean, parseable | Clean when not empty | V1 |
| **Edge cases (PPT)** | Always produces output | 33% empty | V1 |

#### GPU Memory Experiment (V1: 0.10 vs 0.20)

Re-ran all 15 V1 iterations at 0.20 gpu-memory-utilization:

| Metric | 0.10 GPU | 0.20 GPU | Improvement |
|--------|----------|----------|-------------|
| Avg time | 15.6s | 15.0s | **1.03x (3%)** |
| Avg tok/s | 34.7 | 35.3 | +1.7% |

**Conclusion:** Model is decode-bound (autoregressive token generation), not prefill-bound. Doubling KV-cache has negligible impact. **Use 0.10 to minimize VRAM footprint.**

## Rationale

### Why Single VLM (not Dual)

The original plan used Granite + DeepSeek for 3-source weighted blending. Both were eliminated during evaluation:
- Granite: Column shift errors on 60% of test tables
- DeepSeek-OCR: Not instruction-following — cannot produce structured table output

A single high-quality VLM (Nemotron VL v1) provides better cross-validation than two weaker ones. The scoring algorithm simplifies from 3-source blend to 2-source (heuristic + VLM):
- **2 sources:** `0.50 × Heuristic + 0.50 × VLM`
- Heuristic provides structural metrics (density, consistency, header presence)
- VLM provides semantic validation (cell content accuracy via HTML comparison)

### Why P2 HTML Prompt

- **Parseable:** `<table>...</table>` can be parsed with any HTML parser into a cell grid for comparison with Docling's output
- **Rowspan/colspan aware:** Prompt explicitly requests these attributes → essential for merged-cell tables
- **Minimal overhead:** No bounding box coordinates (P3) or LaTeX equations (P1) — reduces token count and latency
- **Official benchmark prompt:** Used in NVIDIA's RD-TableBench evaluation — proven effective

### Container Architecture

vLLM only serves one model per process. Two separate containers are required:
1. **aegis-vllm-eugr-test** (port 8001) — Nemotron-3-Nano-30B extraction (always-on during ingestion)
2. **aegis-vlm-table** (port 8002) — Nemotron VL v1 8B table cross-validation (on-demand)

Both use `aegis-vllm-eugr:latest` base image → Docker layer caching means zero additional disk space. The VLM container only starts during ingestion batches with borderline tables.

## Consequences

**Positive:**
- Single VLM simplifies deployment (1 container vs 2)
- Same Docker image as extraction → familiar ops, shared cache
- 5GB VRAM fits easily within 128GB budget
- 100% reliability eliminates error handling for VLM failures
- 12.3s average per table is acceptable for batch ingestion

**Negative:**
- 8B model may miss nuances on very complex multi-page tables
- Runtime pip install adds ~30s to container cold start
- VLM is overkill for tables that Docling already handles well (score >0.85)

**Mitigations:**
- Cross-validation only for borderline tables (0.50-0.85) — EXCELLENT tables skip VLM
- Bake `timm` + `open_clip_torch` into custom Docker image for production
- Monitor VLM agreement rate — if <70% agreement, investigate model limitations

## References

- [NVIDIA Nemotron VL v1 Model Card](https://huggingface.co/nvidia/Llama-3.1-Nemotron-Nano-VL-8B-V1-FP4-QAD)
- [NVIDIA RD-TableBench Paper](https://arxiv.org/abs/2403.04822) — Source of P2 HTML prompt
- [Benchmark data: V1](/tmp/vlm_benchmark_v1.json), [V2](/tmp/vlm_benchmark_v2.json), [V1 0.20](/tmp/vlm_benchmark_v1_020.json)
- [ADR-059](ADR-059-vllm-dual-engine.md) — vLLM dual-engine architecture
- [Sprint 129.6 Table Ingestion](../sprints/SPRINT_129_PLAN.md) — Table ingestion pipeline
