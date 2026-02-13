# TD-124: VLM LoRA Fine-Tuning for Table OCR Quality

**Created:** 2026-02-12 (Sprint 129)
**Priority:** LOW
**Story Points:** ~8 SP
**Status:** DEFERRED
**Target Sprint:** Post-Sprint 130 (when table ingestion is production-ready)
**Prerequisite:** Sprint 129.6 Table Ingestion Pipeline complete

---

## Problem

Nemotron VL FP4 (`nvidia/Llama-3.1-Nemotron-Nano-VL-8B-V1-FP4-QAD`) produces 22 OCR errors across 4 complex German automotive tables (Sprint 129 Benchmark). Error types:

| Error Type | Count | Example |
|------------|-------|---------|
| Morphological | 8 | "Koeffersum" → "Koeffersumme", "Gtriebe" → "Getriebe" |
| Superscript merge | 4 | "372²" → "3722" |
| Unit errors | 3 | "kW" → "kWh" |
| Column structure | 4 | Values shifted to adjacent columns |
| Other OCR | 3 | Minor character substitutions |

These errors are domain-specific (German automotive terminology) and could be reduced by LoRA fine-tuning on corrected training data.

---

## VLM Cross-Validation Benchmark Results (2026-02-12)

Three alternative VLMs were benchmarked against Nemotron VL FP4. **Nemotron remains the best choice.**

| Model | tok/s | Avg Quality | Tables Found | Truncations | VRAM | Total Time |
|-------|-------|-------------|--------------|-------------|------|------------|
| **Nemotron VL FP4** | 34.7 | ~0.95 | 9 (Docling parity) | 0 | ~5GB | ~63s (6 PDFs) |
| Qwen2.5-VL-7B | 8.6 | 0.816 | 30 | 4 | ~16GB | 6,358s |
| Qwen3-VL-8B | 9.4 | 0.813 | 23 | 0 | ~17GB | 3,754s |
| MiniCPM-V-2.6 | - | - | - | - | - | Gated model (skipped) |

**Key findings:**
- Nemotron VL FP4 is 20-40x faster and produces higher quality output
- Qwen models find more tables (they hallucinate tables from non-tabular content)
- Qwen3-VL is 41% faster than Qwen2.5-VL with 23% fewer prompt tokens
- All models support LoRA/QLoRA fine-tuning
- Prompt has minimal effect on output length — table complexity drives token count

---

## Proposed Solution: LoRA Fine-Tuning

### Architecture

```
BF16 Base Model (nvidia/Llama-3.1-Nemotron-Nano-VL-8B-V1)
  → LoRA Fine-Tune (NeMo/Megatron-Bridge)
  → Merge LoRA Adapter
  → (Optional) Re-quantize to FP4
  → Deploy in vLLM
```

**Why BF16→LoRA→FP4 (not direct FP4 LoRA):**
- NVFP4 + LoRA is experimental (QeRL framework, not yet in vLLM)
- BF16 base + LoRA training is well-supported in NeMo
- After merge, re-quantize to FP4 for production deployment

### Training Data

**Source:** Pre-annotated via Human-in-the-Loop correction of Nemotron VL FP4 + Docling outputs.

- 40 pages already benchmarked (Sprint 129 VLM Benchmark)
- Best-of-both strategy: Use higher-quality output (VLM or Docling) as correction starting point
- Target: 100-500 annotated (image, corrected HTML) pairs
- Format: LLaVA-style JSON (image + instruction + response)

### Training Configuration (DGX Spark)

```bash
# NeMo Container
nvcr.io/nvidia/nemo:25.04.01.llama_nemotron_nano_vl

# LoRA on Language Model only (recommended first)
torchrun --nproc-per-node=1 \
  examples/recipes/nemotron_vl/finetune_nemotron_nano_vl.py \
  --hf-model-path nvidia/Llama-3.1-Nemotron-Nano-VL-8B-V1 \
  --pretrained-checkpoint <megatron_checkpoint> \
  --lora-on-language-model \
  --peft='lora' \
  model.freeze_language_model=True \
  model.freeze_vision_model=False \
  model.freeze_vision_projection=False

# LoRA on Vision + Language (if language-only insufficient)
  --lora-on-language-model \
  --lora-on-vision-model \
  model.freeze_language_model=True \
  model.freeze_vision_model=True \
  model.freeze_vision_projection=True
```

**Memory estimate:** ~17GB BF16 + ~2GB LoRA = ~19GB. Fits easily in 128GB unified memory.

### Deployment Options

1. **Merged model** — `vllm serve /path/to/merged --dtype bfloat16` (~17GB VRAM)
2. **LoRA adapter** — `vllm serve base --enable-lora --lora-modules table-ocr=/path/to/adapter` (dynamic swap)
3. **Re-quantized FP4** — Same as current deployment (~5GB VRAM, fastest)

---

## Archived Data

All benchmark data is archived in:
**`data/evaluation/table_benchmark/TD-124_VLM_LORA_TABLE_FINETUNING.zip`**

Contents:
- `benchmark_vlm_universal.py` — Universal VLM benchmark script
- `vlm_bench_qwen2.5-vl-7b-instruct.json` — Qwen2.5-VL full results
- `vlm_bench_qwen3-vl-8b-instruct.json` — Qwen3-VL full results
- `vlm_bench_qwen25vl_concise.log` — Qwen2.5-VL console log (final run)
- `vlm_bench_qwen3vl_concise.log` — Qwen3-VL console log (final run)
- `vlm_bench_qwen25vl_run4.log` — Earlier Qwen2.5-VL run (max_tokens=4096, truncation issues)
- `vlm_bench_qwen25vl_run5.log` — Qwen2.5-VL run (max_tokens=11000, timeout 600s)
- `vlm_bench_qwen25vl_run6.log` — Qwen2.5-VL run (max_tokens=11000, timeout 1200s)
- `vlm_bench_qwen25vl_run7.log` — Qwen2.5-VL run (P2 prompt variant)
- `vlm_bench_qwen25vl_qwenvl.log` — "QwenVL HTML" prompt test (page layout, not tables)

**Note:** Benchmark PDFs remain at `data/evaluation/table_benchmark/complex/` (6 PDFs) and `simple/` (6 PDFs).

---

## Estimated Effort

| Step | Time |
|------|------|
| Training data annotation (100 tables) | 2-4h |
| Container setup + model conversion | 1-2h |
| LoRA training (100 samples) | 30-60 min |
| Merge + deployment | 30 min |
| Evaluation (benchmark re-run) | 1h |
| **Total** | **~6-8h (~8 SP)** |

---

## Expected Improvement

- 50-70% reduction of German automotive OCR errors (morphological, unit, superscript)
- Minimal quality regression on non-German tables (LoRA is additive)
- LoRA adapter can be swapped per document domain (automotive vs. medical vs. legal)

---

## References

- [Nemotron Nano V2 VL Fine-Tuning — Megatron Bridge](https://docs.nvidia.com/nemo/megatron-bridge/latest/models/vlm/nemotron-nano-v2-vl.html)
- [vLLM LoRA Adapters](https://docs.vllm.ai/en/latest/features/lora/)
- [DGX Spark + Unsloth Fine-Tuning](https://blogs.nvidia.com/blog/rtx-ai-garage-fine-tuning-unsloth-dgx-spark/)
- RAGAS Journey Phase 7: VLM Cross-Validation Benchmark (`docs/ragas/RAGAS_JOURNEY.md`)
- Sprint 129.6 Table Ingestion Pipeline
