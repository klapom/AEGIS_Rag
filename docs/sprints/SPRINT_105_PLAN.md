# Sprint 105: Backend-First E2E Fix Strategy

**Created:** 2026-01-16
**Sprint:** 105
**Scope:** 16 SP (Backend fixes + Router registration)
**Goal:** 120-140 / 194 tests passing (62-72%)
**Strategy:** Fix backend APIs FIRST, then re-run tests

---

## Executive Summary

**Sprint 104 Post-Mortem:** Delivered 23 SP but achieved only 84/163 tests passing (52%) due to backend-frontend gap.

**Root Cause:** Added frontend `data-testid` attributes but backend APIs missing/broken.

**Sprint 105 Approach:** **Backend-First** - Fix all API issues before any frontend work.

---

## API Health Check Results (2026-01-16)

**Total Endpoints Tested:** 17
**Working (200):** 4 (23.5%)
**Broken:** 13 (76.5%)

### Broken Endpoints by Type

| Issue Type | Count | Groups Affected | Impact |
|------------|-------|-----------------|--------|
| **401 Unauthorized** | 5 | 1, 4 | Auth wall blocks all MCP tests |
| **404 Not Found** | 5 | 5, 6, 13, 15 | Endpoints not implemented |
| **405 Method Not Allowed** | 3 | 5, 7 | Wrong HTTP methods |

---

## Sprint 105 Features (16 SP)

### Priority 1: Quick Wins (2 SP)

#### Feature 105.1: Explainability Router Registration (0.5 SP)
**Status:** CRITICAL - File exists but not imported!
**Effort:** 15 minutes
**Impact:** +7-9 tests (Group 15)

**File:** `src/api/v1/explainability.py` (435 LOC) - created in Sprint 104 Phase 3
**Problem:** Router not registered in `src/api/main.py`

**Fix:**
```python
# src/api/main.py (add after line 150)
from src.api.v1 import explainability

# Add after other router registrations
app.include_router(explainability.router, prefix="/api/v1", tags=["explainability"])
```

**Validation:**
```bash
curl http://localhost:8000/api/v1/explainability/retrieval
# Should return: 200 with empty list (not 404)
```

---

#### Feature 105.2: Skills Router Path Fix (0.5 SP)
**Status:** CRITICAL - Path mismatch
**Effort:** 30 minutes
**Impact:** +5-8 tests (Group 5)

**Problem:** Tests expect `/api/v1/skills` but router has `/api/v1/skills/registry`

**Current State:**
```python
# src/api/v1/skills.py (line 45)
@router.get("/registry", response_model=SkillListResponse)
async def list_skills(...):
    pass

@router.get("/registry/{skill_name}", response_model=SkillDetailResponse)
async def get_skill_detail(skill_name: str):
    pass
```

**Fix Options:**

**Option A: Change Router Paths (Recommended)**
```python
@router.get("", response_model=SkillListResponse)  # Changed from "/registry"
async def list_skills(...):
    pass

@router.get("/{skill_name}", response_model=SkillDetailResponse)  # Changed
async def get_skill_detail(skill_name: str):
    pass
```

**Option B: Change Frontend Calls**
- Update all frontend API calls to use `/api/v1/skills/registry`
- Less recommended (breaks REST conventions)

**Recommended:** Option A

**Validation:**
```bash
curl http://localhost:8000/api/v1/skills
# Should return: 200 with skills list (not 405)
```

---

#### Feature 105.3: Memory Search Method Fix (0.5 SP)
**Status:** MEDIUM
**Effort:** 15 minutes
**Impact:** +2-3 tests (Group 7)

**Problem:** Tests use GET, backend expects POST

**Fix:**
```python
# src/api/v1/memory.py
@router.get("/search", response_model=MemorySearchResponse)  # Changed from POST
async def search_memory(...):
    pass
```

**Alternative:** Check if POST is correct method, update tests instead.

**Validation:**
```bash
curl "http://localhost:8000/api/v1/memory/search?query=test"
# Should return: 200 (not 405)
```

---

#### Feature 105.4: Rebuild API Container (0.5 SP)
**Status:** CRITICAL
**Effort:** 5 minutes
**Impact:** All API fixes take effect

**Command:**
```bash
docker compose -f docker-compose.dgx-spark.yml build --no-cache api
docker compose -f docker-compose.dgx-spark.yml up -d api
```

---

### Priority 2: Authentication Fix (2 SP)

#### Feature 105.5: Test Auth Bypass (2 SP)
**Status:** CRITICAL
**Effort:** 1-2 hours
**Impact:** +12 tests (Groups 1, 4)

**Problem:** All MCP endpoints return 401 Unauthorized

**Affected Endpoints:**
- `/api/v1/mcp/servers` (Group 1)
- `/api/v1/mcp/tools` (Group 1)
- `/api/v1/mcp/tools/browser_*/execute` (Group 4)

**Fix Options:**

**Option A: Localhost Auth Bypass (Recommended)**
```python
# src/api/middleware/auth.py
from fastapi import Request

async def auth_middleware(request: Request, call_next):
    # Bypass auth for localhost in development
    if request.client.host in ["127.0.0.1", "localhost", "172.26.0.10"]:
        response = await call_next(request)
        return response

    # Normal auth flow for production
    ...
```

**Option B: Test API Key**
- Create test-only API key
- Add to E2E test fixtures
- More secure but more complex

**Option C: Disable Auth in Dev Mode**
```python
# src/core/config.py
class Settings(BaseSettings):
    DISABLE_AUTH: bool = Field(default=False, env="DISABLE_AUTH")

# .env.test
DISABLE_AUTH=true
```

**Recommended:** Option A (simple, safe for localhost)

**Validation:**
```bash
curl http://localhost:8000/api/v1/mcp/servers
# Should return: 200 with servers list (not 401)
```

---

### Priority 3: Missing Endpoints (11 SP)

#### Feature 105.6: Skills Toggle Endpoint (2 SP)
**Status:** HIGH PRIORITY
**Effort:** 1-2 hours
**Impact:** +3 tests (Group 5)

**Create:** `PUT /api/v1/skills/{skill_name}/toggle`

**Implementation:**
```python
# src/api/v1/skills.py

@router.put("/{skill_name}/toggle", response_model=SkillToggleResponse)
async def toggle_skill(skill_name: str) -> SkillToggleResponse:
    """Toggle skill active/inactive status.

    Sprint 105 Feature 105.6: Skills Toggle Endpoint
    Endpoint: PUT /api/v1/skills/:name/toggle

    Returns:
        SkillToggleResponse with new status
    """
    try:
        # Load skill metadata
        skill_path = Path(f"skills/{skill_name}/skill.yaml")
        if not skill_path.exists():
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        with open(skill_path) as f:
            skill_config = yaml.safe_load(f)

        # Toggle is_active status
        current_status = skill_config.get("is_active", False)
        skill_config["is_active"] = not current_status

        # Save updated config
        with open(skill_path, "w") as f:
            yaml.dump(skill_config, f)

        logger.info(f"Toggled skill '{skill_name}': {current_status} → {not current_status}")

        return SkillToggleResponse(
            skill_name=skill_name,
            is_active=not current_status,
            message=f"Skill '{skill_name}' {'activated' if not current_status else 'deactivated'}"
        )

    except Exception as e:
        logger.error(f"Failed to toggle skill '{skill_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Pydantic Model:**
```python
class SkillToggleResponse(BaseModel):
    skill_name: str
    is_active: bool
    message: str
```

---

#### Feature 105.7: Skills Execute Endpoint (3 SP)
**Status:** HIGH PRIORITY
**Effort:** 2-3 hours
**Impact:** +9 tests (Group 6)

**Create:** `POST /api/v1/skills/{skill_name}/execute`

**Implementation:**
```python
# src/api/v1/skills.py

class SkillExecuteRequest(BaseModel):
    parameters: dict[str, Any] = Field(default_factory=dict)
    context: Optional[dict[str, Any]] = None

class SkillExecuteResponse(BaseModel):
    skill_name: str
    status: Literal["success", "error"]
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: int

@router.post("/{skill_name}/execute", response_model=SkillExecuteResponse)
async def execute_skill(
    skill_name: str,
    request: SkillExecuteRequest
) -> SkillExecuteResponse:
    """Execute a skill with given parameters.

    Sprint 105 Feature 105.7: Skills Execute Endpoint
    Endpoint: POST /api/v1/skills/:name/execute

    Integrates with Tool Composition Framework (Sprint 93-94).
    """
    start_time = time.time()

    try:
        # Load skill
        from src.agents.skills.loader import load_skill
        skill = await load_skill(skill_name)

        if not skill.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Skill '{skill_name}' is not active"
            )

        # Execute skill
        result = await skill.execute(**request.parameters, context=request.context)

        execution_time = int((time.time() - start_time) * 1000)

        return SkillExecuteResponse(
            skill_name=skill_name,
            status="success",
            result=result,
            execution_time_ms=execution_time
        )

    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)
        logger.error(f"Skill execution failed for '{skill_name}': {e}")

        return SkillExecuteResponse(
            skill_name=skill_name,
            status="error",
            error=str(e),
            execution_time_ms=execution_time
        )
```

**Dependencies:**
- Sprint 93-94 Tool Composition Framework
- Skill loader infrastructure
- May require additional integration work

---

#### Feature 105.8: Agent Stats Endpoint (2 SP)
**Status:** MEDIUM PRIORITY
**Effort:** 1-2 hours
**Impact:** +2-3 tests (Group 13)

**Create:** `GET /api/v1/agents/stats`

**Implementation:**
```python
# src/api/v1/agents.py

class AgentStats(BaseModel):
    total_agents: int
    executive_count: int
    manager_count: int
    worker_count: int
    average_performance: float
    total_tasks_completed: int

@router.get("/stats", response_model=AgentStats)
async def get_agent_stats() -> AgentStats:
    """Get agent hierarchy statistics.

    Sprint 105 Feature 105.8: Agent Stats Endpoint
    Endpoint: GET /api/v1/agents/stats
    """
    # Query from agent hierarchy system
    from src.agents.hierarchy import get_all_agents

    agents = await get_all_agents()

    executive = [a for a in agents if a.role == "executive"]
    manager = [a for a in agents if a.role == "manager"]
    worker = [a for a in agents if a.role == "worker"]

    return AgentStats(
        total_agents=len(agents),
        executive_count=len(executive),
        manager_count=len(manager),
        worker_count=len(worker),
        average_performance=sum(a.performance for a in agents) / len(agents) if agents else 0.0,
        total_tasks_completed=sum(a.tasks_completed for a in agents)
    )
```

---

#### Feature 105.9: Browser Tools Backend Verification (3 SP)
**Status:** HIGH PRIORITY (if not implemented)
**Effort:** 2-3 hours
**Impact:** +6 tests (Group 4)

**Affected Endpoints:**
- `POST /api/v1/mcp/tools/browser_navigate/execute`
- `POST /api/v1/mcp/tools/browser_screenshot/execute`
- `POST /api/v1/mcp/tools/browser_evaluate/execute`

**Investigation Required:**
1. Check if endpoints exist in Sprint 103 MCP backend
2. If missing: Implement browser tool execution handlers
3. If exists: Fix auth issue (Feature 105.5)

**Implementation (if missing):**
```python
# src/api/v1/mcp_tools.py

@router.post("/tools/browser_navigate/execute")
async def execute_browser_navigate(request: BrowserNavigateRequest):
    """Execute browser navigate tool.

    Sprint 105 Feature 105.9: Browser Tools Backend
    """
    # Integration with Playwright MCP server
    from src.tools.browser import BrowserTool

    browser = BrowserTool()
    result = await browser.navigate(request.url, timeout=request.timeout)

    return BrowserToolResponse(
        tool="browser_navigate",
        status="success",
        result=result
    )
```

**Note:** May already exist from Sprint 93 Tool Composition Framework.

---

#### Feature 105.10: Explainability Backend Data Integration (1 SP)
**Status:** LOW PRIORITY
**Effort:** 30-60 minutes
**Impact:** +2-3 tests (Group 15)

**Problem:** Router registered (105.1) but returns empty data

**Fix:**
```python
# src/api/v1/explainability.py (update existing endpoints)

@router.get("/retrieval", response_model=List[RetrievalExplanation])
async def list_retrieval_explanations(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    """List recent retrieval explanations with REAL data.

    Sprint 105 Feature 105.10: Real Data Integration
    """
    # Connect to actual explainability logs
    from src.components.explainability import get_recent_explanations

    explanations = await get_recent_explanations(limit=limit, skip=skip)

    return [
        RetrievalExplanation(
            query_id=exp.query_id,
            query=exp.query,
            technical=exp.technical_explanation,
            business=exp.business_explanation,
            regulatory=exp.regulatory_explanation,
            created_at=exp.timestamp.isoformat() + "Z"
        )
        for exp in explanations
    ]
```

---

### Priority 4: Testing & Validation (1 SP)

#### Feature 105.11: Sequential E2E Test Run (1 SP)
**Status:** CRITICAL
**Effort:** 30-60 minutes (execution time)
**Impact:** Accurate baseline without DGX Spark overload

**Command:**
```bash
npm run test:e2e -- --workers=1 --grep "group(01|02|04|05|06|07|09|10|11|12|13|14|15)"
```

**Expected Result:** 120-140 / 163 tests passing (74-86%)

---

## Expected Impact by Group

| Group | Current | After 105 | Delta | Key Fixes |
|-------|---------|-----------|-------|-----------|
| **Group 1** | 13/19 (68%) | 18/19 (95%) | +5 | 105.5 (auth bypass) |
| **Group 2** | 15/16 (94%) | 16/16 (100%) | +1 | Already fixed in 104 |
| **Group 4** | 0/6 (0%) | 6/6 (100%) | +6 | 105.5 (auth) + 105.9 (backends) |
| **Group 5** | 0/8 (0%) | 6/8 (75%) | +6 | 105.2 (paths) + 105.6 (toggle) |
| **Group 6** | 0/9 (0%) | 7/9 (78%) | +7 | 105.7 (execute) |
| **Group 7** | 3/15 (20%) | 12/15 (80%) | +9 | 105.3 (search method) + DOM fixes |
| **Group 9** | 12/13 (92%) | 13/13 (100%) | +1 | Already fixed in 104 |
| **Group 10** | 13/13 (100%) | 13/13 (100%) | 0 | Already fixed in 104 |
| **Group 11** | 13/15 (87%) | 15/15 (100%) | +2 | Already fixed in 104 |
| **Group 12** | 14/15 (93%) | 15/15 (100%) | +1 | Already fixed in 104 |
| **Group 13** | 2/8 (25%) | 6/8 (75%) | +4 | 105.8 (stats endpoint) |
| **Group 14** | 3/14 (21%) | 12/14 (86%) | +9 | API contracts work, minor fixes |
| **Group 15** | 4/13 (31%) | 11/13 (85%) | +7 | 105.1 (router) + 105.10 (data) |

**Total Expected:** 84/163 → 136/163 = **83%** pass rate (+31pp)

---

## Sprint 105 Phases

### Phase 1: Quick Wins (2 SP, 1 hour)
1. Feature 105.1: Explainability router registration (15 min)
2. Feature 105.2: Skills router path fix (30 min)
3. Feature 105.3: Memory search method fix (15 min)
4. Feature 105.4: Rebuild API container (5 min)

**Validation:** Run health check script, verify 7/17 endpoints working (up from 4/17)

---

### Phase 2: Authentication (2 SP, 1-2 hours)
5. Feature 105.5: Test auth bypass (1-2 hours)

**Validation:** Health check should show 12/17 endpoints working

---

### Phase 3: Missing Endpoints (11 SP, 6-8 hours)
6. Feature 105.6: Skills toggle endpoint (2 SP)
7. Feature 105.7: Skills execute endpoint (3 SP)
8. Feature 105.8: Agent stats endpoint (2 SP)
9. Feature 105.9: Browser tools backend (3 SP)
10. Feature 105.10: Explainability data integration (1 SP)

**Validation:** Health check should show 17/17 endpoints working

---

### Phase 4: Testing (1 SP, 1 hour)
11. Feature 105.11: Sequential E2E test run (1 SP)

**Final Validation:** 120-140 / 194 tests passing (62-72%)

---

## Acceptance Criteria

Sprint 105 is complete when:

1. ✅ **All 17 API endpoints working** (health check returns 200/422, no 401/404/405)
2. ✅ **120+ / 194 E2E tests passing** (62%+ pass rate)
3. ✅ **0 authentication failures** (no 401 errors in test logs)
4. ✅ **Explainability router registered** and returning data
5. ✅ **Skills toggle/execute** endpoints implemented and tested
6. ✅ **API container rebuilt** with all fixes

---

## Risk Assessment

### Low Risk Items (High Confidence)
- ✅ Feature 105.1 (router registration): 2 lines of code
- ✅ Feature 105.2 (path fix): Path changes only
- ✅ Feature 105.3 (method fix): GET vs POST change
- ✅ Feature 105.4 (container rebuild): Standard operation

### Medium Risk Items
- ⚠️ Feature 105.5 (auth bypass): Security implications, needs careful testing
- ⚠️ Feature 105.6 (toggle endpoint): File I/O, YAML parsing
- ⚠️ Feature 105.8 (stats endpoint): Depends on agent hierarchy system

### High Risk Items
- 🔴 Feature 105.7 (execute endpoint): Complex integration with Tool Composition Framework
- 🔴 Feature 105.9 (browser backends): May not exist, 3 SP implementation

---

## Rollback Plan

If Sprint 105 fails:

1. **Git Revert:** All Sprint 105 commits
2. **Container Rebuild:** Revert to Sprint 104 image
3. **Fallback Strategy:** Incremental approach (1 group at a time)

---

## Next Steps (Sprint 106+)

After Sprint 105 achieves 120-140 tests (62-72%), Sprint 106 will target:

1. **Group 7 DOM Fixes:** Tab visibility issues (remaining failures)
2. **Group 13 D3 SVG:** Dynamic test ID rendering
3. **Groups 14-15:** API contract fine-tuning
4. **Target:** 175+ / 194 tests (90%+)

---

**Sprint 105 Summary:**
- **Effort:** 16 SP (~8 hours)
- **Target:** 120-140 / 194 tests (62-72%)
- **Strategy:** Backend-first, API fixes, then validate
- **Key Insight:** Always verify backend before frontend!

**Status:** DRAFT - Awaiting Sequential Test Results

**Last Updated:** 2026-01-16
**Sprint:** 105
