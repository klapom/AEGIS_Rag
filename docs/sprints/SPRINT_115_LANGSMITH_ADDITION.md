# Sprint 115 Feature 115.6: LangSmith Tracing Activation

**ADD THIS SECTION TO SPRINT_115_PLAN.md AFTER FEATURE 115.4**

---

## Feature 115.6: LangSmith Tracing Activation (1 SP) ✅ COMPLETE

**Goal:** Enable LangSmith tracing infrastructure for instant LLM call visibility

**Why:** Tracing provides instant visibility into LLM call chains without code changes. Critical for debugging Category E timeout tests (>60s).

**What's Already Implemented:**
- ✅ `src/core/tracing.py`: Full LangSmith integration module
- ✅ `src/api/main.py`: Tracing setup in FastAPI lifespan
- ✅ `src/core/config.py`: LangSmith settings (lines 835-838)
- ✅ `.env.template`: Documentation for LANGSMITH_* variables

**What Was Updated:**
1. ✅ **Updated `.env.template`** (0.5 SP)
   - Added Feature 115.6 context comment
   - Updated project name default to `aegis-rag-sprint115`
   - Added endpoint URL documentation
   - Added clear usage instructions

2. ✅ **Updated Docker Compose** (0.5 SP)
   - Added `LANGSMITH_TRACING` to API service env vars
   - Added `LANGSMITH_API_KEY` (optional) to API service env vars
   - Added `LANGSMITH_PROJECT` to API service env vars
   - Added `LANGSMITH_ENDPOINT` (optional) to API service env vars
   - Documented setup in service comments

**Expected Benefits:**
- **Instant LLM Call Tracing:** See full call chain for every request
- **Token Count Visibility:** Track input/output tokens per LLM call
- **Latency Breakdown:** Identify bottlenecks in agent orchestration
- **No Code Changes:** Just set environment variables and restart
- **Production-Safe:** Tracing is opt-in (default: disabled)

**Usage:**
```bash
# 1. Get LangSmith API key from https://smith.langchain.com
# 2. Add to .env (or set in Docker Compose environment section)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-api-key-here
LANGSMITH_PROJECT=aegis-rag-sprint115

# 3. Restart API
docker compose -f docker-compose.dgx-spark.yml restart api

# 4. Run any query or test
# 5. View traces at https://smith.langchain.com
```

**Sprint 115 Context:**
- Enables Feature 115.1 (Backend Tracing) without OpenTelemetry complexity
- Provides immediate value for Category E test investigation
- LangSmith has zero-config LangChain/LangGraph integration
- All LangGraph agents automatically traced (no code changes required)

---

## UPDATE TO SPRINT 115 STORY POINTS TABLE

**OLD:**
| Feature | SP | Priority |
|---------|-----|----------|
| 115.1 Backend Tracing | 15 | P0 |
| 115.2 LLM Mock | 12 | P0 |
| 115.3 CI Optimization | 15 | P1 |
| 115.4 Test Optimization | 8 | P1 |
| **Total** | **50** | - |

**NEW:**
| Feature | SP | Priority |
|---------|-----|----------|
| 115.1 Backend Tracing | 15 | P0 |
| 115.2 LLM Mock | 12 | P0 |
| 115.3 CI Optimization | 15 | P1 |
| 115.4 Test Optimization | 8 | P1 |
| 115.6 LangSmith Tracing | 1 | P0 |
| **Total** | **51** | - |

---

*Created: 2026-01-20*
*Feature 115.6 Implementation Complete*
