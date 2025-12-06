# Sprint 36: Qwen3 Thinking Mode Performance Fix

**Date:** 2025-12-06
**Author:** Claude Code
**Status:** RESOLVED

## Problem Statement

LLM calls on DGX Spark with Qwen3:32b were taking **5+ minutes per call** instead of the expected few seconds. This made the ingestion pipeline unusably slow (650 seconds for a small test document).

## Root Cause Analysis

### Issue 1: NVML Container Error (Resolved)

Docker containers can lose GPU access after system daemon reloads. The Ollama container showed:
```
Failed to initialize NVML: Unknown Error
```

**Fix:** Restart the Ollama container:
```bash
docker compose -f docker-compose.dgx-spark.yml restart ollama
```

**References:**
- https://github.com/NVIDIA/nvidia-docker/issues/1730
- https://github.com/ollama/ollama/issues/10026

### Issue 2: Qwen3 Thinking Mode (Main Issue)

Qwen3 models have **"Thinking Mode" enabled by default**. This causes the model to generate 200+ internal reasoning tokens before producing the actual response.

**CLI Test Results:**
```bash
# With thinking mode (default):
$ ollama run qwen3:32b "Say hello"
# Time: ~42 seconds, generates internal <think>...</think> tokens

# Without thinking mode:
$ ollama run qwen3:32b --think=false "Say hello"
# Time: ~332ms (127x faster!)
```

### Issue 3: ANY-LLM Parameter Passing (Critical Bug)

The `extra_body={"think": False}` parameter was NOT being passed correctly to Ollama.

**Root Cause:** ANY-LLM's Ollama provider expects `think` as a **top-level keyword argument**, NOT nested inside `extra_body`.

From `any_llm/providers/ollama/ollama.py`:
```python
response = await self.client.chat(
    model=params.model_id,
    think=completion_kwargs.pop("think", None),  # Expects direct param!
    messages=cleaned_messages,
    ...
)
```

When we passed `extra_body={"think": False}`, the `think` parameter remained nested and was never extracted, so Ollama received `think=None` (default = enabled).

## Solution

### File: `src/components/llm_proxy/aegis_llm_proxy.py`

**Before (broken):**
```python
extra_body = {}
if provider == "local_ollama" and "qwen3" in model.lower():
    extra_body["think"] = False  # WRONG: Nested in extra_body

if extra_body:
    completion_kwargs["extra_body"] = extra_body
```

**After (working):**
```python
# Local Ollama: Disable Qwen3 thinking mode for faster inference
# CRITICAL: Pass "think" directly, NOT via extra_body (ANY-LLM requirement)
if provider == "local_ollama" and "qwen3" in model.lower():
    completion_kwargs["think"] = False  # CORRECT: Direct kwarg
```

### File: `src/components/llm_proxy/ollama_vlm.py`

Added `think: False` to the Ollama `/api/generate` payload:
```python
payload = {
    "model": model,
    "prompt": prompt,
    "images": [image_base64],
    "stream": False,
    "think": False,  # Disable Qwen3 thinking mode for faster inference
    "options": {"num_predict": max_tokens, "temperature": temperature},
}
```

## Performance Results

| Metric | Before Fix | After Fix | Improvement |
|--------|-----------|-----------|-------------|
| Pipeline Total | 650s | 50.5s | **13x faster** |
| LLM Call Latency | 135s | 19s | **7x faster** |
| Entity Extraction | ~5 min | ~40s | **7.5x faster** |

## Verification

Check logs for the confirmation message:
```
ollama_thinking_disabled | model=qwen3:32b | reason=performance_optimization_127x_speedup
```

## Lessons Learned

1. **ANY-LLM Provider-Specific Parameters:** Each provider in ANY-LLM has different parameter expectations. Always check the provider implementation before assuming `extra_body` will work.

2. **Qwen3 Thinking Mode:** Qwen3 models (including VL variants) default to thinking mode ON. Always disable for production use unless reasoning traces are needed.

3. **Container GPU Access:** Docker containers can lose GPU access after system daemon reloads. Restart containers if `nvidia-smi` fails inside.

4. **Test CLI First:** When debugging slow LLM calls, test directly via CLI (`ollama run`) to isolate SDK/library issues from model issues.

## Related Files

- `src/components/llm_proxy/aegis_llm_proxy.py` - Main LLM routing with think=False
- `src/components/llm_proxy/ollama_vlm.py` - VLM client with think=False
- `config/llm_config.yml` - LLM configuration (vlm_backend: ollama)
- `docker-compose.dgx-spark.yml` - Container configuration

## ADR Reference

This fix aligns with:
- ADR-033: Multi-Cloud LLM Execution Strategy
- ADR-038: DashScope Extra Body Parameters (for DashScope, extra_body is still needed)
