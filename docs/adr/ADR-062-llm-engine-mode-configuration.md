# ADR-062: LLM Engine Mode Configuration (vLLM/Ollama Runtime Selection)

## Status
**Accepted** (2026-02-07)

## Context

Sprint 125 deployment exposed a critical operational constraint: vLLM (40.7 GB GPU) and Ollama (24 GB GPU) cannot run simultaneously on DGX Spark (128 GB unified memory). Current architecture forces either-or operation:

- **Ollama-only:** Instant API startup, but extraction throttled at 4 concurrent requests (HTTP 000 timeouts)
- **vLLM-only:** 19x extraction throughput, but 60s cold start, Ollama unavailable for chat

Production deployments need flexibility to:
1. Start API without expensive vLLM initialization (chat workloads)
2. Activate vLLM on-demand for bulk ingestion jobs
3. Route chat vs extraction tasks independently
4. Hot-reload engine mode without container restart

## Decision

### Runtime Engine Mode Configuration

Implement a **configurable LLM engine mode** stored in Redis (`aegis:llm_engine_mode`) with three modes:

| Mode | Ollama | vLLM | Use Case |
|------|--------|------|----------|
| **vllm** | ❌ Disabled | ✅ Active | High-throughput extraction, bulk ingestion |
| **ollama** | ✅ Active | ❌ Disabled | Chat, generation, low-latency queries |
| **auto** (default) | ✅ Active | ✅ Both | Dual-engine (if resources permit) |

### Admin API Endpoints

```python
# GET current engine mode
GET /api/v1/admin/llm/engine
→ { "mode": "ollama", "health": { "ollama": "ok", "vllm": "unavailable" } }

# SET engine mode (hot-reload, no restart)
PUT /api/v1/admin/llm/engine
Body: { "mode": "vllm" }
→ { "mode": "vllm", "previous": "ollama" }
```

### AegisLLMProxy Routing Logic

```python
async def _get_engine_mode(self) -> str:
    """Get current engine mode from Redis with 30s cache."""
    cached = await self.redis.get("aegis:llm_engine_mode")
    if cached:
        return cached.decode()
    return "auto"  # Default

async def _route_task(self, task: LLMTask) -> str:
    """Route task based on type and engine mode."""
    mode = await self._get_engine_mode()

    if task.task_type == TaskType.EXTRACTION:
        if mode in ["vllm", "auto"] and self._vllm_available:
            return "vllm"  # High-throughput route
        return "ollama"  # Fallback

    # Chat/generation always prefer Ollama (lower latency)
    if mode in ["ollama", "auto"] and self._ollama_available:
        return "ollama"
    return "vllm"  # Fallback if Ollama unavailable
```

### Startup Behavior

**api/main.py initialization:**

```python
async def lifespan(app: FastAPI):
    mode = settings.LLM_ENGINE_MODE  # From .env or config
    await redis.set("aegis:llm_engine_mode", mode, ex=None)

    if mode != "vllm":
        # Chat-focused: warm up Ollama, skip vLLM
        await ollama.warmup()
    else:
        # Extraction-focused: skip Ollama warmup, vLLM already running
        pass

    yield
    # Cleanup...
```

## Alternatives Considered

### A. Single-Engine Only (Forced Choice)
**Rejected.** Operators must choose deployment personality at startup. No flexibility for mixed workloads or ad-hoc switching.

### B. Automatic Engine Detection (ML-Based)
**Rejected.** Would require RAGAS evaluation or throughput prediction model. Too complex for current Sprint. Manual selection is clear and sufficient.

### C. Load-Based Auto-Switching
**Rejected.** Complex state machine (detecting extraction vs chat), risks mid-job switches causing task failures. Manual control safer.

### D. Separate Proxy Services (One per Engine)
**Rejected.** Operational overhead (2 processes, 2 health checks). Single proxy with routing is simpler.

## Consequences

### Positive
- ✅ **Zero-Startup Mode:** `ollama` mode eliminates 60s vLLM cold start for chat-only deployments
- ✅ **Hot-Reload:** Engine mode changes via Redis without container restart (30s cache + in-flight requests)
- ✅ **Mixed Workloads:** `auto` mode supports both chat and extraction (if VRAM permits)
- ✅ **Operator Flexibility:** Deployment profiles (pharma = ollama, enterprise_ingestion = vllm)
- ✅ **Cost Efficient:** vLLM only runs during heavy ingestion (not 24/7)
- ✅ **Graceful Degradation:** Fallback routing ensures task completion even if target engine unavailable

### Negative
- ⚠️ **Operational Complexity:** Operators must understand engine tradeoffs
- ⚠️ **Network Overhead:** Redis cache checks add ~1-2ms per extraction (negligible at scale)
- ⚠️ **In-Flight Race Condition:** Tasks mid-execution when mode changes (mitigated by 30s cache + logical task boundaries)

### Neutral
- 🔄 **No Code Changes to Prompts:** Engine mode is transparent to extraction logic (same LLM inputs/outputs)
- 🔄 **No Database Changes:** All data structures remain unchanged

## Implementation Notes

### Frontend Admin UI (DeploymentProfilePage + AdminLLMConfigPage)

Three-card selector with live health status:

```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     vLLM        │  │     Ollama      │  │      Auto       │
│  🟢 Active      │  │  ⚫ Inactive    │  │  🟡 Disabled    │
│  793 tok/s      │  │  41 tok/s       │  │  Dual-Engine    │
│  EXTRACTION     │  │  CHAT           │  │  (if available) │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

Health endpoint response:

```json
{
  "mode": "ollama",
  "health": {
    "ollama": "ok",
    "ollama_throughput": "41 tok/s",
    "vllm": "unavailable",
    "vllm_reason": "Not started (config: PROFILE=chat_only)"
  }
}
```

### Redis Storage

**Key:** `aegis:llm_engine_mode`
**Value:** `"vllm" | "ollama" | "auto"`
**TTL:** None (persistent until explicitly changed)
**Cache Strategy:** 30s local cache in proxy to avoid Redis round-trip per task

### Configuration File (.env)

```bash
# LLM Engine Mode (startup default)
LLM_ENGINE_MODE=auto  # Options: vllm, ollama, auto

# Optional: Deployment Profile (for future automation)
DEPLOYMENT_PROFILE=engineering  # pharma, law_firm, engineering, chat_only, etc.
```

## Related Decisions

- **ADR-059:** vLLM Integration for Dual-Engine Architecture (this ADR enables runtime selection)
- **ADR-033:** AegisLLMProxy Multi-Cloud Routing (vLLM + Ollama as dual local providers)
- **ADR-060:** Domain Taxonomy Architecture (deployment profiles reference engine mode)

## References

- [vLLM Documentation](https://docs.vllm.ai/en/latest/)
- [Ollama Configuration](https://github.com/ollama/ollama)
- [DGX Spark VRAM Budget Analysis](docs/CLAUDE.md)
- [Sprint 125 Plan](docs/sprints/SPRINT_125_PLAN.md)

## Revision History

- **2026-02-07:** Initial version (Status: Accepted)
