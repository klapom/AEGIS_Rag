# Sprint 18: Test Infrastructure & Security Hardening

**Status:** 📋 PLANNED
**Goal:** Achieve 95%+ test pass rate and implement authentication
**Duration:** 5-7 days (estimated)
**Prerequisites:** Sprint 17 complete ✅

---

## 🎯 Sprint Objectives

### **Primary Goals:**
1. Fix 44 failing E2E tests from Sprint 15/16
2. Implement JWT authentication for admin endpoints
3. Add rate limiting for API protection
4. Improve test infrastructure

### **Success Criteria:**
- 95%+ E2E test pass rate (currently 76%)
- All admin endpoints protected with JWT
- Rate limiting active on all public APIs
- Zero critical security vulnerabilities

---

## 📦 Sprint Features

### Feature 18.1: Test Selector Modernization (5 SP)
**Priority:** HIGH
**Duration:** 1 day

**Problem:**
- 44 E2E tests failing due to outdated selectors
- Tests use `getByText` which finds multiple elements
- Test brittleness due to UI structure changes

**Solution:**
Replace text-based selectors with accessibility-first approach.

**Tasks:**
- [ ] Add `data-testid` to ambiguous UI elements
  - Mode selector chips
  - Tab components
  - Loading indicators
- [ ] Replace `getByText` with `getByRole` where applicable
  - Buttons, headings, links
  - Better accessibility validation
- [ ] Use `within()` for scoped queries
  - Avoid multiple element issues
  - More specific test assertions
- [ ] Update HomePage.e2e.test.tsx (6 tests)
- [ ] Update SearchResultsPage.e2e.test.tsx (17 tests)
- [ ] Update FullWorkflow.e2e.test.tsx (11 tests)
- [ ] Update SSEStreaming.e2e.test.tsx (9 tests)
- [ ] Update ErrorHandling.e2e.test.tsx (1 test)

**Deliverables:**
```typescript
// BEFORE (brittle)
getByText('Hybrid')  // Fails if multiple "Hybrid" texts

// AFTER (resilient)
getByRole('button', { name: 'Hybrid Mode' })
within(modeSelector).getByText('Hybrid')
getByTestId('mode-hybrid-button')
```

**Acceptance Criteria:**
- ✅ All 44 failing tests pass
- ✅ No new test failures introduced
- ✅ Test execution time < 40s
- ✅ Better accessibility coverage

---

### Feature 18.2: Mock Data Synchronization (3 SP)
**Priority:** MEDIUM
**Duration:** 0.5 day

**Problem:**
- Mock responses don't match current API structure
- Tests expect old field names/structures
- Difficult to maintain as API evolves

**Solution:**
Generate mocks from TypeScript types, sync with OpenAPI spec.

**Tasks:**
- [ ] Audit all mock data in `fixtures.ts`
- [ ] Compare with current API responses
- [ ] Update mocks to match OpenAPI spec
- [ ] Create mock generator utility
  - `generateMockFromType<T>()`
  - Type-safe mock creation
- [ ] Add validation tests for mocks
  - Ensure mocks match TypeScript types
  - Detect schema drift

**Deliverables:**
```typescript
// Mock generator
import { SystemStats } from '../types/admin';

const mockStats = generateMockFromType<SystemStats>({
  qdrant_total_chunks: 1523,
  // ... compiler validates all required fields
});

// Validation test
it('should match current API structure', () => {
  expectType<SystemStats>(mockAdminStats);
});
```

**Acceptance Criteria:**
- ✅ All mocks validated against types
- ✅ Mock generator utility created
- ✅ No type mismatches
- ✅ Easy to update when API changes

---

### Feature 18.3: JWT Authentication for Admin Endpoints (8 SP)
**Priority:** HIGH
**Duration:** 2 days

**Problem:**
- Admin endpoints (`/api/v1/admin/*`) are publicly accessible
- No authentication or authorization
- Security risk for production deployment

**Solution:**
Implement JWT-based authentication with role-based access control (RBAC).

**Tasks:**
- [ ] **Backend: JWT Authentication Middleware**
  - Install `python-jose[cryptography]` via Poetry
  - Create `src/core/auth.py` with JWT utils
  - Implement `get_current_user()` dependency
  - Add `require_admin` dependency
- [ ] **Backend: User Management**
  - Create `src/models/user.py` (User, UserRole)
  - Add `POST /api/v1/auth/login` endpoint
  - Add `POST /api/v1/auth/register` endpoint (admin-only)
  - Store users in Redis (MVP) or PostgreSQL (production)
- [ ] **Backend: Protect Admin Endpoints**
  - Apply `Depends(require_admin)` to all `/admin/*` routes
  - Update OpenAPI documentation
  - Add authentication tests
- [ ] **Frontend: Login Page**
  - Create `LoginPage.tsx` component
  - JWT storage in localStorage
  - Auto-refresh token logic
- [ ] **Frontend: Protected Routes**
  - Create `ProtectedRoute.tsx` wrapper
  - Redirect to login if not authenticated
  - Apply to `/admin` route

**Technical Specs:**
```python
# Backend: auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    # Validate JWT token
    # Return User object

async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# Protected route
@router.get("/stats", dependencies=[Depends(require_admin)])
async def get_stats() -> SystemStats:
    ...
```

```typescript
// Frontend: ProtectedRoute.tsx
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const token = localStorage.getItem('jwt_token');

  if (!token) {
    return <Navigate to="/login" />;
  }

  return <>{children}</>;
}

// App.tsx
<Route path="/admin" element={
  <ProtectedRoute>
    <AdminPage />
  </ProtectedRoute>
} />
```

**Acceptance Criteria:**
- ✅ JWT tokens issued on login
- ✅ Admin endpoints require valid JWT
- ✅ Non-admin users get 403 Forbidden
- ✅ Token refresh works correctly
- ✅ Frontend redirects to login if unauthorized
- ✅ Secure token storage (httpOnly cookies in production)

---

### Feature 18.4: API Rate Limiting (5 SP)
**Priority:** MEDIUM
**Duration:** 1 day

**Problem:**
- No rate limiting on public APIs
- Vulnerable to DoS attacks
- No cost control for LLM usage

**Solution:**
Implement rate limiting with Redis-backed storage.

**Tasks:**
- [ ] Install `slowapi` via Poetry
  - Redis-backed rate limiter
  - Configurable limits per endpoint
- [ ] Create `src/core/rate_limit.py`
  - Rate limiter initialization
  - Custom limit decorators
- [ ] Apply rate limits to endpoints
  - `/api/v1/chat/stream`: 10 req/min per IP
  - `/api/v1/chat/search`: 30 req/min per IP
  - `/api/v1/admin/*`: 100 req/min per user
- [ ] Add rate limit headers
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`
- [ ] Create monitoring dashboard
  - Track rate limit hits
  - Alert on suspicious activity
- [ ] Add tests for rate limiting
  - Verify limits enforced
  - Test burst handling

**Technical Specs:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, storage_uri=settings.redis_url)

@router.post("/stream")
@limiter.limit("10/minute")
async def chat_stream(request: ChatRequest):
    ...

# Custom limiter for authenticated users
@limiter.limit("100/minute", key_func=lambda: current_user.id)
```

**Acceptance Criteria:**
- ✅ Rate limits enforced on all public endpoints
- ✅ 429 Too Many Requests returned when exceeded
- ✅ Rate limit headers included in responses
- ✅ Redis stores rate limit state
- ✅ Configurable limits via environment variables
- ✅ Bypass for admin users (higher limits)

---

### Feature 18.5: Test Helper Library (3 SP)
**Priority:** LOW
**Duration:** 0.5 day

**Problem:**
- Duplicate test code across files
- Inconsistent wait/retry logic
- Poor error messages in tests

**Solution:**
Create reusable test utilities and custom matchers.

**Tasks:**
- [ ] Create `test/utils/` directory
- [ ] Build common test helpers
  - `waitForElement()` with better timeouts
  - `waitForText()` with partial matching
  - `fillSearchInput()` - common action
  - `selectMode()` - mode switching helper
- [ ] Custom matchers
  - `toHaveLoadingState()`
  - `toHaveStreamingCursor()`
  - `toHaveSourceCards(count)`
- [ ] Improve error messages
  - Show available elements on failure
  - Include component tree context
- [ ] Documentation
  - Testing guide with examples
  - Best practices document

**Deliverables:**
```typescript
// test/utils/helpers.ts
export async function waitForStreamingComplete(timeout = 5000) {
  await waitFor(() => {
    expect(screen.queryByText(/Suche läuft/i)).not.toBeInTheDocument();
  }, { timeout });
}

export function selectMode(mode: 'hybrid' | 'vector' | 'graph' | 'memory') {
  const button = screen.getByRole('button', { name: new RegExp(mode, 'i') });
  fireEvent.click(button);
}

// Custom matcher
expect.extend({
  toHaveSourceCards(received, expectedCount) {
    const sources = within(received).queryAllByTestId('source-card');
    return {
      pass: sources.length === expectedCount,
      message: () => `Expected ${expectedCount} sources, found ${sources.length}`
    };
  }
});

// Usage in tests
await waitForStreamingComplete();
selectMode('hybrid');
expect(resultsContainer).toHaveSourceCards(3);
```

**Acceptance Criteria:**
- ✅ 5+ reusable test helpers created
- ✅ 3+ custom matchers implemented
- ✅ Test code duplication reduced by 50%
- ✅ Better error messages in test failures
- ✅ Documentation with examples

---

## 📊 Story Points Breakdown

```yaml
Feature 18.1: Test Selector Modernization     5 SP
Feature 18.2: Mock Data Synchronization       3 SP
Feature 18.3: JWT Authentication              8 SP
Feature 18.4: API Rate Limiting               5 SP
Feature 18.5: Test Helper Library             3 SP
----------------------------------------------------
Total:                                       24 SP
```

**Estimated Duration:** 5 days (team of 1-2)

---

## 🔗 Dependencies

**From Sprint 17:**
- ✅ Admin Statistics API (Feature 17.6)
- ✅ Admin UI Component (Feature 17.1)
- ✅ E2E Test Infrastructure (32 tests)

**External Dependencies:**
- Poetry for Python dependency management
- Redis for rate limiting storage
- `python-jose` for JWT handling
- `slowapi` for rate limiting

---

## 🎯 Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| E2E Test Pass Rate | 76% | 95%+ | `npm test` |
| Test Execution Time | 33s | <40s | CI/CD pipeline |
| API Response Time | ~200ms | <250ms | Prometheus |
| Auth Coverage | 0% | 100% admin | Manual audit |
| Rate Limit Hits | N/A | <1%/day | Redis metrics |

---

## 🚀 Rollout Plan

### Phase 1: Test Fixes (Day 1-2)
1. Fix selector issues in existing tests
2. Achieve 95%+ pass rate
3. Validate no regressions

### Phase 2: Authentication (Day 3-4)
1. Implement JWT backend
2. Create login UI
3. Protect admin routes
4. Test auth flow

### Phase 3: Rate Limiting (Day 5)
1. Install and configure slowapi
2. Apply limits to endpoints
3. Monitor rate limit metrics

### Phase 4: Polish (Day 6)
1. Test helper library
2. Documentation updates
3. Final validation

---

## 📝 Notes

- **Poetry Migration:** Sprint 17 already uses Poetry, no migration needed
- **Security:** Follow OWASP guidelines for JWT storage (httpOnly cookies in prod)
- **Monitoring:** Integrate with existing Prometheus metrics
- **Backward Compatibility:** Maintain API compatibility during auth rollout

---

## 🔄 Rollback Plan

If issues arise:
1. **Test Fixes:** Revert to Sprint 17 test suite (32 passing tests remain)
2. **Authentication:** Feature flag to disable auth temporarily
3. **Rate Limiting:** Increase limits to effectively disable
4. **Monitoring:** Alert on unusual error rates

---

**Plan Created:** 2025-10-29
**Sprint Start:** TBD
**Prerequisites Met:** ✅ YES (Sprint 17 complete)
