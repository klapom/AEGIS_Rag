# AEGIS RAG - Consolidated Refactoring Plan (Pre-Production V1)

**Status:** V1 Pre-Production (Not Live)
**Advantage:** No breaking changes concerns, no migration guides needed, no backward compatibility required
**Timeline:** 3-4 Weeks (80-110h total)
**Approach:** Direct refactoring, immediate cleanup, simplified workflow

---

## Executive Summary

Since we're **not yet live**, we can refactor aggressively without worrying about:
- Breaking external users
- API versioning (v1→v2)
- Deprecation periods
- Parallel implementations
- Migration guides

This reduces complexity and timeline by **~40-50%** compared to post-production refactoring.

**Key Findings:**
- **725 lines of deprecated code** to delete immediately
- **500+ lines of duplicate code** to eliminate
- **5 critical security issues** in API layer
- **10 critical test gaps** to fill
- **Estimated savings:** 10-15% codebase reduction

---

## Refactoring Items by Priority

### Priority 1: Critical (Must Do - Sprint 22)
**Effort:** 42-58h over 2 weeks

#### Backend P1: Deprecated Code Removal (16-20h)
1. **Delete `unified_ingestion.py`** (275 lines) → Replaced by LangGraph pipeline
   - Update all imports to LangGraph pipeline
   - Update/delete related tests
   - **No migration:** Just delete, fix imports, done

2. **Delete `three_phase_extractor.py`** (350 lines) → Replaced by Pure LLM (ADR-026)
   - Update all references to pure LLM extraction
   - Delete related tests
   - **No archive:** Just delete (already deprecated per ADR-026)

3. **Remove `base.py` duplicate** (155 lines) → Identical to `base_agent.py`
   - Delete `base.py`
   - Update imports to `base_agent.py`
   - Run tests

4. **LlamaIndex deprecation** (ADR-028)
   - Update docs: LlamaIndex is fallback only
   - Add logging when LlamaIndex is used
   - No warnings needed (internal only)

#### API P1: Security Fixes (8-12h)
1. **Fix CORS configuration** (30 min)
   - Change `allow_origins=["*"]` → specific list
   - No backward compatibility needed

2. **Standardize error responses** (3-4h)
   - Create `StandardErrorResponse` model
   - Update all endpoints
   - **Breaking change OK:** No external users yet

3. **Add rate limiting** (2-3h)
   - Add to annotations endpoints
   - Add to admin endpoints
   - No grandfathering needed

4. **Fix authentication inconsistency** (2-3h)
   - Standardize: RequireAuth vs OptionalAuth
   - Apply consistently across all endpoints
   - **Breaking change OK:** Internal only

5. **Fix SSE race condition** (1-2h)
   - Add try/finally to save conversation
   - No backward compatibility concerns

#### Testing P1: Critical Gaps (18-26h)
Fill the 7 most critical test gaps before heavy refactoring:
1. **Client lifecycle tests** (3-4h) - Connection pooling, reconnection
2. **Error propagation tests** (4-5h) - Cascade failure scenarios
3. **Configuration injection tests** (2-3h) - DI pattern validation
4. **Embedding service parity** (2-3h) - Wrapper vs core equivalence
5. **LangGraph state persistence** (3-4h) - Redis checkpointing
6. **Chunking consistency** (2-3h) - All strategies tested
7. **API authentication coverage** (2-4h) - JWT, rate limiting

---

### Priority 2: High (Should Do - Sprint 22 or 23)
**Effort:** 30-40h over 1-2 weeks

#### Backend P2: Architectural Improvements (20-24h)
1. **Create `BaseClient` abstract class** (6-8h)
   - Consolidate 300+ lines of duplicate connection logic
   - Migrate 3-5 clients as pilot
   - **No parallel:** Migrate all at once

2. **Eliminate embedding service duplication** (4-6h)
   - Remove 160-line wrapper delegation
   - Direct usage of BGE-M3 service
   - **No migration:** Just refactor, update tests

3. **Standardize client naming** (3-4h)
   - `QdrantClientWrapper` → `QdrantClient`
   - `GraphitiWrapper` → `GraphitiClient`
   - **No aliases:** Direct rename (not live yet)

4. **Create `BaseRetriever` interface** (4-5h)
   - Standardize retrieval patterns
   - Implement in 3-4 retrievers
   - Update tests

5. **Error handling pattern** (3-4h)
   - Create standardized exception hierarchy
   - Apply across components
   - No backward compat needed

#### API P2: Validation & Consistency (10-16h)
1. **File upload validation** (3-4h)
   - Size limits (50MB)
   - Content type validation
   - Malware scanning (ClamAV)
   - **No grandfathering:** Apply immediately

2. **Standardize pagination** (3-4h)
   - `top_k` → `limit/offset` everywhere
   - Create `PaginationParams` model
   - **Breaking OK:** Consistent is better

3. **Request ID tracking** (2-3h)
   - Middleware for X-Request-ID
   - Propagate to logs and errors
   - No backward compatibility needed

4. **Consolidate duplicate models** (2-3h)
   - Move to `src/api/models/`
   - Single source of truth
   - Update imports

5. **OpenAPI documentation** (0-2h)
   - Add examples to all endpoints
   - Standardize descriptions
   - No API versioning concerns

---

### Priority 3: Medium (Nice to Have - Sprint 23+)
**Effort:** 20-30h over 1-2 weeks

#### Backend P3: Code Quality (12-16h)
1. **Dependency injection pilot** (5-6h)
   - Replace direct `settings` imports in 5-10 classes
   - Create injectable config objects
   - Easier testing

2. **Remaining client migrations** (4-6h)
   - Migrate remaining clients to `BaseClient`
   - Full consolidation

3. **Logging standardization** (2-3h)
   - Consistent logger usage
   - Structured logging fields
   - Snake_case event names

4. **Resolve TODOs** (1-2h)
   - 30+ TODOs in codebase
   - Delete or implement

#### API P3: Enhancements (8-14h)
1. **Helper function extraction** (2-3h)
   - Move SSE helpers to `src/api/utils/`
   - Reusable response builders

2. **Router registration simplification** (1-2h)
   - Utility function for bulk registration
   - Less boilerplate

3. **Session ID generation** (1-2h)
   - Centralized function
   - Validation logic

4. **Add response compression** (1h)
   - GZipMiddleware for responses >1KB

5. **Add API metrics** (2-3h)
   - Prometheus FastAPI instrumentator
   - Request/response metrics

6. **Deprecation decorator** (1-2h)
   - For future deprecations
   - Not needed now, but good pattern

---

### Priority 4: Low (Future - Sprint 24+)
**Effort:** 10-15h

1. **Background task health checks** (2-3h)
2. **Request/response logging middleware** (2-3h)
3. **Swagger UI customization** (1-2h)
4. **Rate limit headers** (2-3h)
5. **Webhook support for long operations** (3-4h)

---

## Simplified 3-Week Roadmap (Pre-Production)

### Week 1: Critical Cleanup (P1 Backend + Tests)
**Effort:** 34-46h

#### Day 1-2: Deprecated Code Deletion (8-10h)
- Delete `unified_ingestion.py` (275 lines)
- Delete `three_phase_extractor.py` (350 lines)
- Delete `base.py` duplicate (155 lines)
- Update all imports
- Fix tests (not parallel, just fix)
- **No migration:** Direct deletion

**Result:** 780 lines deleted, codebase cleaner

#### Day 3-5: Critical Test Gaps (18-26h)
- Write 7 critical baseline tests
- Client lifecycle, error propagation, etc.
- No need for "before/after" parity tests (not live)
- Just ensure new code is well-tested

**Result:** Test coverage ≥85%, critical gaps filled

#### Day 6: LlamaIndex Deprecation (2-4h)
- Update docs (ADR-028)
- Add logging when used
- No warnings needed (internal)

**Result:** LlamaIndex properly documented as fallback

---

### Week 2: Security & Architecture (P1 API + P2 Backend)
**Effort:** 28-36h

#### Day 1: API Security Fixes (8-12h)
- Fix CORS (30 min)
- Standardize error responses (3-4h)
- Add rate limiting (2-3h)
- Fix authentication (2-3h)
- Fix SSE race condition (1-2h)
- **No backward compat:** Just fix

**Result:** All P1 security issues resolved

#### Day 2-3: BaseClient Creation (10-14h)
- Create `BaseClient` abstract class (6-8h)
- Migrate 3-5 clients as pilot (4-6h)
- **No parallel:** Direct migration

**Result:** Client pattern established, boilerplate reduced 50%

#### Day 4-5: Embedding & Naming (8-10h)
- Remove embedding wrapper duplication (4-6h)
- Rename all clients (Wrapper → Client) (3-4h)
- Update tests
- **No aliases:** Direct rename

**Result:** Consistent naming, less duplication

---

### Week 3: Validation & Enhancements (P2 API + P3)
**Effort:** 20-30h

#### Day 1-2: API Validation (10-16h)
- File upload validation (3-4h)
- Standardize pagination (3-4h)
- Request ID tracking (2-3h)
- Consolidate models (2-3h)
- OpenAPI docs (0-2h)

**Result:** API layer consistent and validated

#### Day 3-5: Code Quality (10-14h)
- BaseRetriever interface (4-5h)
- Error handling pattern (3-4h)
- Logging standardization (2-3h)
- Resolve TODOs (1-2h)

**Result:** Code quality improved, patterns established

---

## Total Effort Summary

| Priority | Backend | API | Testing | Total |
|----------|---------|-----|---------|-------|
| **P1** | 16-20h | 8-12h | 18-26h | **42-58h** |
| **P2** | 20-24h | 10-16h | - | **30-40h** |
| **P3** | 12-16h | 8-14h | - | **20-30h** |
| **P4** | - | 10-15h | - | **10-15h** |
| **Total** | 48-60h | 36-57h | 18-26h | **102-143h** |

**Recommended Sprint 22:** P1 + P2 (72-98h over 3 weeks)

---

## Success Criteria (Simplified)

### Code Quality
- ✅ 780+ lines of deprecated/duplicate code deleted
- ✅ All client classes renamed consistently
- ✅ BaseClient and BaseRetriever implemented
- ✅ All TODOs resolved or deleted
- ✅ MyPy strict mode passes

### Testing
- ✅ Test coverage: ≥85% overall
- ✅ Core coverage: ≥90% (src/core/)
- ✅ API coverage: ≥90% (src/api/)
- ✅ All 7 critical test gaps filled
- ✅ Test execution time: <180s

### Security
- ✅ CORS configured properly
- ✅ Rate limiting on all public endpoints
- ✅ Authentication consistent across API
- ✅ File upload validation complete
- ✅ Bandit security score: 0 High/Medium issues

### Performance
- ✅ No latency degradation (p95 <500ms hybrid query)
- ✅ Error rate <1%
- ✅ Memory usage stable or reduced

---

## What's Different (Pre-Production Advantages)

| Concern | Post-Production | Pre-Production (Us) |
|---------|-----------------|---------------------|
| **Breaking Changes** | Must avoid or version | ✅ Make freely |
| **Migration Guides** | Required for users | ✅ Not needed (internal) |
| **Deprecation Period** | 6+ months | ✅ Delete immediately |
| **Parallel Implementations** | Keep old + new | ✅ Direct replacement |
| **API Versioning** | v1 → v2 strategy | ✅ Just fix v1 |
| **Feature Flags** | Gradual rollout | ✅ Deploy all at once |
| **Backward Compat** | Critical concern | ✅ Not applicable |
| **Timeline** | 6+ weeks | ✅ 3-4 weeks |
| **Complexity** | High (safe migration) | ✅ Low (direct fix) |

**Result:** ~40-50% less effort, cleaner code, faster delivery

---

## Risk Mitigation (Simplified)

| Risk | Mitigation (Pre-Production) |
|------|----------------------------|
| **Tests break** | Just fix them (no external users affected) |
| **Breaking changes** | Not a concern (not live yet) |
| **Coverage drops** | Pre-commit hooks, enforce 85% floor |
| **Performance regression** | Benchmarks before/after, rollback if needed |
| **Time overrun** | Prioritize P1 → P2, defer P3/P4 |

No need for:
- ❌ Complex rollback strategies
- ❌ Feature flags
- ❌ Canary deployments
- ❌ User communication plans
- ❌ Migration documentation

---

## Next Steps

### Recommended Approach: Sprint 22 (3 weeks)
**Do P1 + P2 items:** Critical cleanup + architectural improvements

**Week 1:** Delete deprecated code, fill critical test gaps (34-46h)
**Week 2:** Fix API security, create BaseClient (28-36h)
**Week 3:** API validation, code quality improvements (20-30h)

**Total:** 82-112h over 3 weeks (27-37h/week)

### Alternative: Just P1 (2 weeks)
**Do only critical items:** Deprecated code + security fixes

**Week 1:** Backend P1 + Testing P1 (34-46h)
**Week 2:** API P1 (8-12h)

**Total:** 42-58h over 2 weeks (21-29h/week)

P2/P3 items can be deferred to Sprint 23+ if time is tight.

---

## Deliverables

### Code Changes
- 780+ lines deleted (deprecated/duplicate code)
- BaseClient abstract class created
- All clients renamed consistently
- API error responses standardized
- 7 critical test gaps filled

### Documentation Updates
- CLAUDE.md (if structure changes)
- Component READMEs (if APIs change)
- ADR updates (if architecture changes)
- Test documentation (new test patterns)

### Validation
- Full test suite passing (≥85% coverage)
- No performance regressions
- All security issues resolved
- Bandit scan clean

---

## Summary

**Pre-production advantage:** We can refactor aggressively without worrying about breaking external users. This simplifies the plan dramatically:

- **No migration guides** → Just delete and fix
- **No API versioning** → Just improve v1
- **No deprecation periods** → Delete immediately
- **No backward compatibility** → Make breaking changes freely
- **~40-50% less effort** → 3-4 weeks instead of 6

**Recommended:** Execute P1 + P2 in Sprint 22 (3 weeks, 82-112h total)

**Result:** Cleaner codebase, better architecture, production-ready for V1 launch.
