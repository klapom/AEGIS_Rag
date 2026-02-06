# ADR-059: vLLM Integration for Extraction Pipeline (Dual-Engine Architecture)

## Status
**Accepted** (2026-02-06)

## Context

Sprint 124's gpt-oss:120b ingestion run exposed critical Ollama bottlenecks:

| Issue | Impact | Root Cause |
|-------|--------|------------|
| HTTP 000 Timeout Loop | Ingestion stuck at 28/498 docs | Ollama max 4 parallel requests |
| 100% RELATES_TO Relations | Poor graph query quality | Generic extraction prompt (separate fix in 125.3) |
| Community Summarization Backlog | Blocks new uploads | Sequential Ollama processing |

NVIDIA's txt2kg cookbook demonstrates vLLM for 19x throughput over Ollama. Red Hat benchmarks confirm:

| Metric | Ollama | vLLM | Factor |
|--------|--------|------|--------|
| Peak Throughput | 41 tok/s | 793 tok/s | 19.3x |
| TTFT P99 | 673 ms | 80 ms | 8.4x |
| Max Concurrent | 4 | 256+ | 64x |

DGX Spark (128 GB unified memory) can run both Ollama and vLLM simultaneously.

## Decision

### Dual-Engine Architecture

Add vLLM as a separate Docker container alongside Ollama. Route tasks by type:

- **Chat/Generation** → Ollama (Nemotron-3-Nano Q4_K_M, already running, user-facing latency)
- **Extraction** → vLLM (Nemotron-3-Nano NVFP4, bulk throughput, batch processing)

### Docker Profiles for On-Demand Start

```yaml
vllm:
  image: vllm/vllm-openai:latest
  profiles: [ingestion]  # Only started when needed
  ports: ["8001:8001"]
  command: >
    --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4
    --max-model-len 32768
    --max-num-seqs 8
    --gpu-memory-utilization 0.4
    --port 8001
    --trust-remote-code
    --kv-cache-dtype fp8
```

Start modes:
- Normal: `docker compose up -d` (Ollama only, chat)
- Ingestion: `docker compose --profile ingestion up -d` (Ollama + vLLM)

### Model: Nemotron-3-Nano-30B-A3B-NVFP4

| Spec | Value |
|------|-------|
| Total Params | 30B |
| Active Params | 3.5B (MoE, 10% activation) |
| Architecture | Mamba2 + MoE + Attention |
| Quantization | NVFP4 (Blackwell FP4 tensor cores) |
| VRAM | ~18 GB |
| Context | 256K (up to 1M) |
| Expected tok/s | 60-80 on DGX Spark |

### AegisLLMProxy Routing

```python
async def _select_provider(self, task: LLMTask) -> str:
    if task.task_type == TaskType.EXTRACTION and self._vllm_available:
        return "vllm"
    return "local_ollama"  # Chat, generation, community summarization
```

Graceful fallback: if vLLM is down, extraction routes to Ollama (degraded throughput).

## Alternatives Considered

### A. Replace Ollama Entirely with vLLM
**Rejected.** vLLM has ~60s cold start, no GGUF support. Ollama provides instant response for chat. Dual-engine avoids single point of failure.

### B. SGLang Instead of vLLM
**Rejected.** SGLang shows higher tok/s on benchmarks (53 vs 36 for GPT-OSS-120B) but vLLM has larger ecosystem, better Docker support, OpenAI-compatible API. vLLM is de facto standard for production inference.

### C. Scale Ollama (More Concurrent Requests)
**Rejected.** Ollama's architecture limits to 4 concurrent requests (GGML/llama.cpp threading). Not solvable with configuration changes.

### D. Use Cloud LLM for Extraction
**Rejected.** Violates ADR-002 (Ollama-Only Strategy / no cloud LLM), DSGVO concerns with document text leaving premises. vLLM keeps everything on-premises.

## Consequences

### Positive
- 19x extraction throughput (793 vs 41 tok/s)
- 64x concurrent request capacity (256+ vs 4)
- RAGAS Phase 1 ingestion (498 docs) feasible in ~1.5 hours (was stuck at 28)
- NVFP4 optimized for Blackwell FP4 tensor cores (4x FLOPS over BF16)
- On-demand: vLLM only runs during ingestion, no VRAM waste during chat

### Negative
- Additional Docker container complexity
- ~60s cold start for vLLM
- Different model format (HuggingFace NVFP4 vs Ollama GGUF)
- ~18 GB VRAM reserved during ingestion

### VRAM Budget
```
Normal Mode:    Ollama 25GB + BGE-M3 2GB + Reranker 1GB + OS 10GB = 38 GB / 128 GB
Ingestion Mode: + vLLM 18GB = 56 GB / 128 GB (72 GB free)
```

## Related Decisions
- ADR-002: Ollama-Only LLM Strategy (extended, not replaced)
- ADR-026: Pure LLM Extraction Pipeline (vLLM becomes extraction engine)
- ADR-033: AegisLLMProxy Multi-Cloud Routing (vLLM added as local provider)
- ADR-060: Domain Taxonomy Architecture (domain-specific prompts via vLLM)
