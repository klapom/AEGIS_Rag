# Sprint 17: Admin UI & Advanced Features
**Status:** 📋 PLANNED (for after Sprint 16)
**Goal:** Admin UI for re-indexing management and advanced frontend features
**Duration:** 5-7 days (estimated)

---

## 🎯 Sprint Objectives

Based on Sprint 16 learnings and user requests:

### **Key Features Requested:**
1. ✅ **Admin UI for Directory Indexing** (User Request: 2025-10-28)
   - Interface to specify directory to index
   - Real-time indexing progress display
   - Integration with unified re-indexing pipeline (Feature 16.2)

2. 📋 **Technical Debt from Sprint 15/16**
   - TD-36: Accessibility improvements (WCAG 2.1 AA compliance)
   - TD-37: Error boundary implementation (graceful error handling)
   - Frontend E2E test improvements (if needed)

---

## 📦 Sprint Features

### Feature 17.1: Admin UI for Directory Indexing (13 SP)
**Status:** 📋 PLANNED
**Duration:** 2 days

**Problem:**
Currently no user interface to specify directories for indexing or monitor indexing progress in real-time.

**Solution:**
Create admin UI that integrates with the unified re-indexing pipeline (Feature 16.2) and provides real-time progress monitoring.

**Tasks:**
- [ ] Create Admin page component (`AdminPage.tsx`)
- [ ] Directory selection UI (input field + file browser button)
- [ ] Re-indexing control panel (confirm button, dry-run toggle)
- [ ] Real-time progress display (SSE integration)
  - Progress bar with percentage
  - Current phase display (initialization, deletion, chunking, embedding, indexing, validation)
  - Current document being processed
  - ETA calculation display
- [ ] Indexing history table (past re-indexing operations)
- [ ] System statistics dashboard
  - Total documents indexed
  - Total chunks in Qdrant
  - BM25 corpus size
  - Neo4j entity count
- [ ] Admin authentication/authorization
- [ ] Error handling and user feedback
- [ ] Responsive design

**Deliverables:**
```typescript
// frontend/src/pages/AdminPage.tsx
export function AdminPage() {
  const [inputDir, setInputDir] = useState<string>('');
  const [dryRun, setDryRun] = useState<boolean>(false);
  const [progress, setProgress] = useState<ReindexProgress | null>(null);

  // SSE connection to /api/v1/admin/reindex endpoint
  // Real-time progress updates
  // ETA calculation and display
}
```

**API Integration:**
- `POST /api/v1/admin/reindex` (SSE streaming) - from Feature 16.2
- `GET /api/v1/admin/stats` - system statistics endpoint (NEW)
- `GET /api/v1/admin/history` - indexing history (NEW)

**Benefits:**
- ✅ User can specify custom directory for indexing
- ✅ Real-time visibility into indexing progress
- ✅ Dry-run mode to preview changes
- ✅ Historical tracking of indexing operations

---

### Feature 17.2: Admin Statistics API (5 SP)
**Status:** 📋 PLANNED
**Duration:** 0.5 day

**Problem:**
No API endpoint to retrieve system statistics for admin UI display.

**Solution:**
Create admin endpoints for system statistics and indexing history.

**Tasks:**
- [ ] `GET /api/v1/admin/stats` endpoint
  - Total documents indexed
  - Total chunks in Qdrant (collection.info())
  - BM25 corpus size
  - Neo4j entity count (Cypher query)
  - LightRAG graph statistics
  - Last re-indexing timestamp
- [ ] `GET /api/v1/admin/history` endpoint
  - List of past re-indexing operations
  - Timestamp, duration, status, document count
  - Store in SQLite database
- [ ] Add authentication middleware (JWT required)
- [ ] OpenAPI documentation

**Deliverables:**
```python
@router.get("/api/v1/admin/stats")
async def get_system_stats() -> SystemStats:
    """Get comprehensive system statistics."""
    return {
        "documents_total": ...,
        "qdrant_chunks": ...,
        "bm25_corpus_size": ...,
        "neo4j_entities": ...,
        "last_reindex": ...
    }
```

**Benefits:**
- ✅ Admin can monitor system health
- ✅ Track indexing history
- ✅ Data for dashboards and reporting

---

### Feature 17.3: Accessibility Improvements (TD-36) (8 SP)
**Status:** 📋 PLANNED
**Duration:** 1 day

**Problem:**
Frontend lacks proper accessibility features (WCAG 2.1 AA compliance).

**Solution:**
Add accessibility improvements across all components.

**Tasks:**
- [ ] Add ARIA labels to all interactive elements
- [ ] Keyboard navigation support (Tab, Enter, Escape)
- [ ] Focus management (modal dialogs, dropdowns)
- [ ] Color contrast compliance (WCAG AA: 4.5:1)
- [ ] Screen reader testing with NVDA/JAWS
- [ ] Alt text for images
- [ ] Semantic HTML (proper heading hierarchy)
- [ ] Skip navigation links
- [ ] Accessible error messages (role="alert")
- [ ] Form validation with clear error descriptions

**Deliverables:**
- All components pass axe-core automated testing
- Manual testing with screen readers
- Accessibility documentation

**Benefits:**
- ✅ Compliance with WCAG 2.1 AA standards
- ✅ Better user experience for all users
- ✅ Legal compliance (accessibility laws)

---

### Feature 17.4: Error Boundary Implementation (TD-37) (5 SP)
**Status:** 📋 PLANNED
**Duration:** 0.5 day

**Problem:**
Frontend lacks error boundaries for graceful error handling.

**Solution:**
Implement React error boundaries at component level.

**Tasks:**
- [ ] Create `ErrorBoundary` component
- [ ] Add error boundaries at key component levels
  - App level (global fallback)
  - Page level (per page)
  - Component level (critical components)
- [ ] Error logging integration (send to backend)
- [ ] User-friendly error UI
- [ ] Automatic error recovery (retry button)
- [ ] Development vs. production error display

**Deliverables:**
```typescript
// frontend/src/components/ErrorBoundary.tsx
export class ErrorBoundary extends React.Component {
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error to backend
    // Display user-friendly message
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback error={this.state.error} />;
    }
    return this.props.children;
  }
}
```

**Benefits:**
- ✅ Graceful error handling without app crash
- ✅ Better debugging with error logs
- ✅ Improved user experience

---

### Feature 17.5: Frontend E2E Test Improvements (8 SP)
**Status:** 📋 CONDITIONAL (only if Sprint 16 E2E tests need improvements)
**Duration:** 1 day

**Tasks:**
- [ ] Review Sprint 16 E2E test results
- [ ] Fix any flaky tests
- [ ] Add missing test coverage
- [ ] Improve test reliability
- [ ] Add visual regression testing
- [ ] CI integration improvements

---

## 📊 Sprint Metrics

### **Story Points Breakdown:**
```yaml
Feature 17.1: Admin UI for Directory Indexing   13 SP
Feature 17.2: Admin Statistics API               5 SP
Feature 17.3: Accessibility Improvements         8 SP
Feature 17.4: Error Boundary Implementation      5 SP
Feature 17.5: E2E Test Improvements              8 SP (optional)
-----------------------------------------------------------
Total:                                          39 SP (31 SP required, 8 SP optional)
```

### **Estimated Duration:**
- **Optimistic:** 4 days (7.75 SP/day velocity)
- **Realistic:** 5-6 days (6.5 SP/day velocity)
- **Pessimistic:** 7 days (5.6 SP/day velocity)

### **Feature Dependencies:**
```
Sprint 16 (Feature 16.2: Unified Re-Indexing) ✅ PREREQUISITE
  └── 17.1 (Admin UI) 📋 NEXT
  └── 17.2 (Admin API) 📋 NEXT

17.3 (Accessibility) 📋 (Independent)
17.4 (Error Boundaries) 📋 (Independent)
17.5 (E2E Tests) 📋 (Conditional)
```

**Critical Path:** Sprint 16.2 → 17.1 → 17.2 (18 SP)

---

## 🎯 Success Criteria

### **Functional Requirements:**
- [ ] Admin can specify directory to index via UI
- [ ] Real-time progress display shows current phase and ETA
- [ ] System statistics dashboard displays accurate data
- [ ] Indexing history shows past operations
- [ ] All components meet WCAG 2.1 AA standards
- [ ] Error boundaries prevent app crashes
- [ ] Admin UI works on mobile + desktop

### **Non-Functional Requirements:**
- [ ] Admin UI response time <100ms
- [ ] SSE progress updates every 500ms
- [ ] Accessibility score >95 (axe-core)
- [ ] Error boundary catches all React errors
- [ ] Test coverage >80% for new components

### **Documentation:**
- [ ] Admin UI user guide
- [ ] API documentation for admin endpoints
- [ ] Accessibility testing guide
- [ ] Error handling best practices

---

## 📚 References

- **Sprint 16 Plan:** Unified Re-Indexing Pipeline (Feature 16.2)
- **Sprint 15 Plan:** Frontend completion
- **Technical Debt:** TD-36 (Accessibility), TD-37 (Error Boundaries)

---

## 🚀 Next Steps

**Immediate Actions (after Sprint 16 completion):**
1. Review Sprint 16 Feature 16.2 re-indexing API
2. Design Admin UI mockups
3. Create statistics API endpoints
4. Implement Admin UI components
5. Add accessibility features
6. Add error boundaries

**Estimated Start:** After Sprint 16 completion
**Estimated Completion:** Sprint 17: TBD (depends on Sprint 16 end date)

---

**Last Updated:** 2025-10-28
**Status:** 📋 PLANNED (Feature 17.1 requested by user on 2025-10-28)
