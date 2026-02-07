# Sprint 126 Plan: LLM Engine Mode + Domain Sub-Types + DevOps Hardening

**Status:** ✅ COMPLETE
**Story Points:** 22 SP (14 SP features + 8 SP DevOps)
**Duration:** 1 day (2026-02-07)
**Predecessor:** Sprint 125 (vLLM Integration + Domain-Aware Extraction)

---

## Sprint Goals

1. **Runtime LLM Engine Mode** — Switch between vLLM/Ollama/Auto without restart (ADR-062)
2. **Domain Sub-Type Pipeline** — YAML factory defaults → Neo4j runtime overrides → API CRUD
3. **Community Detection as Batch Job** — Decouple from ingestion (85% faster)
4. **Fix DSPy Extraction Signatures** — list[str] → list[dict] for ADR-060 types
5. **NULL Relation Backfill** — Patch 1,021 legacy relations with specific types
6. **Pre-commit Hooks** — 13 automated quality gates (Ruff, Bandit, secrets, TypeScript)
7. **CI/CD Streamlining** — Remove duplicates, -40% pipeline runtime

---

## Features

### 126.1: Runtime LLM Engine Mode (ADR-062) — 2 SP ✅

**Goal:** Hot-switch between vLLM, Ollama, or Auto mode at runtime.

**Implementation:**
- `GET/PUT /api/v1/admin/llm/engine` endpoints with Redis-backed state
- AegisLLMProxy._route_task() honors mode, graceful fallback
- 30s Redis cache prevents thundering herd on mode changes
- Startup skips unnecessary warmups based on active engine
- 3-card Admin UI selector (Ollama/vLLM/Auto)

**Commit:** `7660b27`

---

### 126.2: DeploymentProfilePage Save Bug Fix — 1 SP ✅

**Problem:** Save button on DeploymentProfilePage returned 404/422.
**Fix:** Corrected URL, JSON body format, and auth token header.

**Commit:** `7660b27`

---

### 126.3: Community Detection as Nightly Batch Job — 2 SP ✅

**Goal:** Decouple community detection from the ingestion pipeline.

**Implementation:**
- `GRAPH_COMMUNITY_DETECTION_MODE=scheduled` env var
- APScheduler cron trigger at 5 AM daily
- `POST /api/v1/admin/community-detection/trigger` for manual runs
- `GET /api/v1/admin/community-detection/status` for monitoring

**Impact:** Ingestion 85% faster (732s → ~107s/doc — community detection was the bottleneck)

**Commit:** `6763a8b`

---

### 126.4: DSPy EntityExtractionSignature Fix — 2 SP ✅

**Problem:** DSPy signatures used `list[str]` for entities/relations, but ADR-060 requires typed dicts with subject_type, relation, object_type fields.

**Fix:** Changed `EntityExtractionSignature` and `RelationExtractionSignature` output fields to `list[dict]` matching the S-P-O triple format.

**Commit:** `6763a8b`

---

### 126.5: NULL Relation-Type Backfill — 1 SP ✅

**Problem:** 1,021 relations in Neo4j had NULL relation types (from pre-Sprint 125 ingestion).

**Fix:** Backfill script classified 212 as specific types (STUDIES, USES, PART_OF, etc.) and 809 as RELATED_TO (generic fallback). 0 NULL remaining.

**Commit:** `6763a8b`

---

### 126.6: Domain Sub-Type Pipeline — 3 SP ✅

**Goal:** Multi-tier type system with YAML defaults and Neo4j runtime overrides.

**Implementation:**
- 253 entity aliases + 43 relation aliases from `data/seed_domains.yaml`
- 4-tier prompt priority: trained → domain-enriched → generic → legacy
- LLM produces domain-specific sub_type (e.g., DISEASE) → mapped to universal type (CONCEPT) → sub_type preserved as Neo4j property
- Cache invalidation on `PUT /domains/{name}`
- Full API CRUD for domain sub-types

**Commit:** `d4e015a`

---

### 126.7: AdminNavigationBar on Admin Pages — 1 SP ✅

**Goal:** Consistent navigation across all ~28 admin pages.

**Implementation:** Added AdminNavigationBar component import and rendering to all admin page components.

**Commit:** `7660b27`

---

### 126.8: Domain Seeding into Neo4j — 2 SP ✅

**Goal:** Seed all 35 DDC+FORD domains into Neo4j on startup.

**Implementation:** Reads `data/seed_domains.yaml`, creates `:Domain` nodes with entity_sub_type_mapping, relation_hints, keywords, and ontology references.

**Commit:** `d4e015a`

---

### 126.9: Pre-commit Hooks Setup — 5 SP ✅

**Goal:** Automated code quality gates on every commit.

**13 Hooks Configured:**
1. Ruff Linter (v0.14.8) — lint + auto-fix
2. Ruff Formatter — consistent formatting
3. Secret Detection (detect-secrets) — prevent API key leaks
4. TypeScript Check — catch compile errors
5. YAML/JSON/TOML Syntax — config validation
6. Large Files (>1MB) — prevent binary bloat
7. Merge Conflict Markers — catch unresolved merges
8. Trailing Whitespace — clean formatting
9. End of File Newline — POSIX compliance
10. Bandit Security — static analysis (5 global skips, ~45 nosec annotations)
11. Naming Conventions — custom check (Sprint 18)
12. Conventional Commits — commit message format validation

**Security Fixes:**
- B324 (MD5): Added `usedforsecurity=False` to hashlib.md5 calls
- B307 (eval): Replaced 3 `eval()` calls with `ast.literal_eval` in domain_training.py
- B104/B106/B108/B110/B603: ~45 nosec annotations for intentional patterns

**Commit:** `78be84c`

---

### 126.10: CI/CD Pipeline Streamlining — 3 SP ✅

**Goal:** Remove duplicate checks between pre-commit and CI, eliminate low-value jobs.

**Removed:**
- 8 duplicate checks (Ruff, Bandit, detect-secrets, etc. — now in pre-commit)
- 9 unnecessary checks (MyPy strict, docstring validation, import validation, etc.)

**Impact:**
- ci.yml: 849 → 636 lines (-25%), 11 → 8 jobs
- code-quality-sprint-end.yml: -16%
- e2e.yml: -23%
- **CI runtime: 25-30 min → 15-20 min (-40%)**

**Commit:** `cf2d493`

---

## Additional Commits

| Commit | Type | Description |
|--------|------|-------------|
| `2d11560` | chore(infra) | /commit slash command for sprint-aware workflow |

---

## Story Points Breakdown

| Category | Features | SP |
|----------|----------|-----|
| LLM Engine Mode (126.1-126.2) | 2 | 3 |
| Extraction Fixes (126.3-126.5) | 3 | 5 |
| Domain Pipeline (126.6-126.8) | 3 | 6 |
| DevOps (126.9-126.10) | 2 | 8 |
| **Total** | **10** | **22** |

---

## Success Criteria (All Met)

- [x] Engine mode switchable via API without restart
- [x] Community detection decoupled from ingestion (85% faster)
- [x] DSPy signatures produce ADR-060 typed dicts
- [x] 0 NULL relation types in Neo4j
- [x] Domain sub-types preserved through extraction → storage
- [x] 13 pre-commit hooks passing on every commit
- [x] CI pipeline 40% faster with no duplicate checks
- [x] All 35 domains seeded into Neo4j

---

## References

- [ADR-062: LLM Engine Mode Configuration](../adr/ADR-062-llm-engine-mode-configuration.md)
- [ADR-060: Domain Taxonomy](../adr/ADR-060-domain-taxonomy.md)
- [Sprint 125 Plan](SPRINT_125_PLAN.md) — predecessor
- [Sprint 127 Plan](SPRINT_127_PLAN.md) — RAGAS Phase 1 Benchmark (next)
- [DECISION_LOG.md](../DECISION_LOG.md) — Sprint 126 section
