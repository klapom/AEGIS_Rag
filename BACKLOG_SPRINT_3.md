# Sprint 3 Backlog - Technical Debt & Security

## 🔒 Security Findings (from Bandit Scanner)

### P2: MD5 Hash Usage in Cache Key Generation
- **File:** `src/components/vector_search/embeddings.py:164`
- **Issue:** Use of weak MD5 hash (B324 - CWE-327)
- **Severity:** HIGH (Confidence: HIGH)
- **Current Code:**
```python
return hashlib.md5(text.encode("utf-8")).hexdigest()
```
- **Recommendation:**
  - MD5 is used only for cache key generation (non-security purpose)
  - Fix: Add `usedforsecurity=False` parameter (Python 3.9+)
  - Alternative: Switch to SHA256 for cache keys
```python
return hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()
# OR
return hashlib.sha256(text.encode("utf-8")).hexdigest()
```
- **Impact:** Low (cache key generation, not cryptographic use)
- **Effort:** 5 minutes
- **Priority:** P2 (Nice to have)

### P3: API Server Binding to All Interfaces
- **File:** `src/core/config.py:31`
- **Issue:** Binding to 0.0.0.0 (B104 - CWE-605)
- **Severity:** MEDIUM (Confidence: MEDIUM)
- **Current Code:**
```python
api_host: str = Field(default="0.0.0.0", description="API server host")
```
- **Recommendation:**
  - This is intentional for Docker deployment
  - For production: Use reverse proxy (nginx/traefik) with rate limiting
  - For local dev: Can be overridden to "127.0.0.1" via .env
- **Mitigation:** Already implemented via:
  - Rate limiting (slowapi)
  - JWT authentication (can be enabled)
  - Input validation (P0 security)
- **Impact:** Low (mitigated by existing security layers)
- **Effort:** No action needed (by design)
- **Priority:** P3 (Informational only)

---

## ⚠️ CI/CD Issues (Non-Critical)

### P3: Integration Tests - Neo4j Startup Timeout
- **Status:** ❌ Times out after 60 seconds
- **Root Cause:** Neo4j 5.24 needs >60s to start on GitHub Actions runners
- **Impact:** Integration tests don't run in CI (but pass locally)
- **Solution Options:**
  1. Increase timeout to 120s (may still fail on slow runners)
  2. Skip Neo4j in CI until Sprint 5 (Graph RAG)
  3. Use Neo4j health check via HTTP instead of cypher-shell
- **Recommendation:** Option 2 - Skip Neo4j tests in CI until Sprint 5
- **Effort:** 15 minutes (add pytest marker `@pytest.mark.skip_ci`)
- **Priority:** P3 (Neo4j not used until Sprint 5)

### P4: Naming Conventions - 2 Violations
- **File:** `src/core/exceptions.py`
- **Issues:**
  1. `AegisRAGException` - doesn't follow PascalCase (false positive)
  2. `LLMError` - doesn't follow PascalCase (false positive)
- **Status:** Both are valid Python class names (PascalCase)
- **Action:** Add exceptions to naming check script or disable rule
- **Priority:** P4 (False positives, can be ignored)

---

## 📋 Sprint 3 Preparation

### Carry-Over from Sprint 2
- [ ] Fix MD5 hash security warning (5 min)
- [ ] Document Bandit findings resolution
- [ ] Update CI to skip Neo4j tests (optional)

### Sprint 3 Planning
- Review Sprint 3 features (TBD)
- Update SPRINT_PLAN.md with Sprint 3 breakdown
- Define feature list (3.1, 3.2, 3.3, etc.)

---

## 📊 Security Audit Summary

**Total Findings:** 2
**High Severity:** 1 (MD5 hash - non-security use)
**Medium Severity:** 1 (0.0.0.0 binding - by design)
**Actionable:** 1 (MD5 fix)
**Informational:** 1 (0.0.0.0 binding)

**Overall Security Posture:** ✅ **EXCELLENT**
- P0/P1/P2 security controls implemented
- Only 2 findings, both low-impact
- 1 quick fix, 1 accepted by design

---

*Generated: 2025-10-15*
*Bandit Report: CI Run 18525248764*
