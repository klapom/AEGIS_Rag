## ADR-058: Skill Tool Auto-Resolve (Hybrid Install-Time Classification)

### Status
**Accepted** (2026-01-28)

### Context
Skills in AegisRAG need access to MCP tools for execution (e.g., a "research" skill needs `web_search`, `browser`; a "data_viz" skill needs `python_execute`). The current system has two problems:

1. **Static Tool Assignment:** Skills define their tools in SKILL.md frontmatter (`permissions: [web_search, browser]`), but these are manually curated and become stale when new MCP tools are installed.
2. **No Auto-Discovery:** When a new MCP tool is installed (e.g., a `pdf_reader` tool), no existing skill automatically gains access — even if the tool's capabilities perfectly match the skill's permission requirements.

We need a mechanism that:
- Automatically discovers which MCP tools match a skill's declared permissions
- Works without runtime LLM calls (latency-sensitive)
- Allows admin override of auto-resolved mappings
- Integrates with the existing `SkillToolMapper` (Sprint 93) and `PolicyEngine`

### Decision
We implement **Option C: Hybrid Install-Time Classification + Runtime Cache Lookup**.

**Two-phase approach:**

1. **Install-Time Classification (one-time per tool):**
   - When a new MCP tool is installed/discovered, ONE LLM call classifies its capabilities
   - Classification maps tool → capability categories from `config/tool_capabilities.yaml`
   - Result is cached in Redis (`tool:capabilities:{tool_name}`)
   - Example: `read_file` → `["filesystem_read"]`, `web_search` → `["web_search", "web_read"]`

2. **Activation-Time Resolution (cache lookup, ~0ms):**
   - When a skill is activated, its `permissions` from SKILL.md are matched against cached tool capabilities
   - Pure dictionary lookup — no LLM call needed
   - Result: list of resolved tools for the skill
   - Admin can review and override via UI

**Data flow:**
```
MCP Tool Install → LLM Classification → Redis Cache
                                             ↓
Skill Activation → Permission Matching → Resolved Tools → Admin Review
```

### Alternatives Considered

#### Option A: Static Capability Map (YAML-only)
**Pro:**
- Zero LLM calls, deterministic
- Simple to understand and debug
- No external dependencies

**Contra:**
- Requires manual YAML updates for every new tool
- Cannot classify tools with complex or novel capabilities
- Becomes maintenance burden as tool count grows

#### Option B: Runtime LLM Matching
**Pro:**
- Most flexible, handles any tool/skill combination
- No upfront classification needed
- Adapts to context changes

**Contra:**
- LLM call on every skill activation (~500ms-2s latency)
- Non-deterministic results across activations
- Cost: LLM token usage per activation
- Failure mode: LLM unavailable = no tool resolution

#### Option C: Hybrid (CHOSEN)
**Pro:**
- One-time LLM cost per tool (amortized)
- Runtime resolution is pure cache lookup (~0ms)
- Deterministic after classification
- Graceful fallback to YAML map if LLM unavailable
- Admin can review/override classifications

**Contra:**
- More complex architecture than A
- Requires Redis for cache persistence
- Initial LLM call may fail (mitigated by YAML fallback)

### Rationale

Option C provides the best balance:

1. **Performance:** Runtime resolution is a Redis/dict lookup (~0ms), not an LLM call
2. **Accuracy:** LLM classification handles complex tool descriptions better than static regex
3. **Maintainability:** New tools are auto-classified; no YAML edits needed
4. **Reliability:** YAML fallback ensures resolution works even without LLM/Redis
5. **Governance:** Admin override UI prevents unwanted tool-skill bindings
6. **Integration:** Builds on existing `SkillToolMapper` (Sprint 93) and `PolicyEngine`

### Implementation

#### Components

1. **`config/tool_capabilities.yaml`** — Defines capability categories and static fallback map
2. **`src/agents/skills/tool_resolver.py`** — `SkillToolResolver` class (~200 LOC)
3. **API Endpoints:**
   - `GET /api/v1/skills/{name}/resolved-tools` — Get auto-resolved tools for a skill
   - `POST /api/v1/skills/{name}/resolved-tools/override` — Admin override
   - `GET /api/v1/skills/lifecycle/metrics` — Aggregated lifecycle metrics (also fixes 404)
   - `GET /api/v1/skills/{name}/skill-md` — Get SKILL.md content (also fixes 404)
4. **Frontend:** Resolved Tools panel in SkillConfigEditor

#### Capability Categories
```yaml
# config/tool_capabilities.yaml
capabilities:
  web_search:    ["web_search", "search_engine", "google_search"]
  web_read:      ["browser", "fetch_url", "scrape_page"]
  filesystem_read:  ["read_file", "list_directory", "glob"]
  filesystem_write: ["write_file", "create_directory"]
  code_execute:  ["python_execute", "bash_execute", "run_code"]
  database_read: ["sql_query", "neo4j_query", "qdrant_search"]
  database_write: ["sql_insert", "neo4j_write"]
  api_call:      ["http_request", "rest_api", "graphql"]
```

#### Resolution Algorithm
```python
def resolve_tools(skill_permissions: list[str]) -> list[ResolvedTool]:
    """
    1. For each permission in skill.permissions:
       a. Look up capability category in tool_capabilities.yaml
       b. Find all cached MCP tools matching that category
       c. Filter by PolicyEngine rules
    2. Return deduplicated list of resolved tools
    """
```

### Consequences

**Positive:**
- ✅ New MCP tools auto-discovered by existing skills
- ✅ Zero runtime latency for tool resolution
- ✅ Admin governance via override UI
- ✅ Deterministic after initial classification
- ✅ Graceful YAML fallback

**Negative:**
- ⚠️ Initial LLM call per new tool (~1 call per tool install)
- ⚠️ Redis dependency for cache (mitigated by in-memory fallback)
- ⚠️ Classification accuracy depends on LLM quality

**Mitigations:**
- YAML static map as fallback for common tools
- Admin override UI for incorrect classifications
- Classification quality monitoring via metrics endpoint
- In-memory dict fallback if Redis unavailable

### References
- Sprint 93: Tool Composition Framework (`src/agents/tools/mapping.py`)
- Sprint 93: PolicyEngine (`src/agents/tools/policy.py`)
- ADR-007: MCP Client Integration
- `src/components/mcp/models.py`: MCPTool dataclass
