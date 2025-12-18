# Technical Debt Quick Reference

**Last Updated:** 2025-12-18
**Review Period:** Sprint 51 (Phase Display & Admin UX Fixes)

---

## Review Results

**Archival Decision:** 0 items archived (all remain valid)
**Documents Analyzed:** 26 total (14 active, 8 archived, 4 other)
**Action Items:** 3 status verifications needed before Sprint 52

---

## Active Items by Priority

### HIGH PRIORITY (Must Fix)
| TD# | Title | Status | Impact |
|-----|-------|--------|--------|
| TD-043 | Follow-up Questions Redis | OPEN | Backend blocker |
| TD-044 | DoclingParsedDocument Interface | IN PROGRESS | Section extraction broken |
| TD-047 | Critical Path E2E Tests | OPEN | Production confidence |

### MEDIUM PRIORITY (Important)
| TD# | Title | Status | Target Sprint |
|-----|-------|--------|----------------|
| TD-045 | entity_id Migration | OPEN | 49+ |
| TD-049 | User Profiling | OPEN | 52+ |
| TD-051 | Memory Consolidation | OPEN | 52+ |
| TD-054 | Unified Chunking | PARTIAL | 50+ |
| TD-058 | Community Summaries | PLANNED | 52+ |
| TD-059 | Reranking via Ollama | OPEN | 48+ (optional) |

### LOW PRIORITY (Nice-to-Have)
| TD# | Title | Status | Notes |
|-----|-------|--------|-------|
| TD-052 | User Document Upload | OPEN | Verify implementation |
| TD-053 | Admin Dashboard | OPEN | Update after 51 |
| TD-055 | MCP Client | OPEN | Future feature |
| TD-056 | Project Collaboration | PLANNED | Strategic |
| TD-067 | Dataset Annotation | BACKLOG | Evaluation tool |

### NEEDS VERIFICATION
| TD# | Title | Issue | Action |
|-----|-------|-------|--------|
| TD-046 | RELATES_TO Extraction | Status unclear | Verify completion (Sprint 34?) |

---

## Sprint 51 Achievements

✓ **51.1** Phase Display Fixes - All phase events now sent correctly
✓ **51.2** LLM Answer Streaming - Tokens streamed token-by-token
✓ **51.3** Admin Navigation - Sidebar reorganized, links added
✓ **51.4** Domain Delete & Status - Cascading delete implemented
✓ **51.5** Intent Classification Fix - All 4 types now work
✓ **51.6** CommunityDetector Bugs - entity_id & RELATES_TO fixed
✓ **51.7** Maximum Hybrid Search - 4-signal foundation implemented

**Impact on TD Backlog:**
- Feature 51.6 unblocks TD-058 (Community Summaries)
- Feature 51.7 improves foundation for TD-054, TD-051

---

## Documents for Next Sprint Planning

### For Sprint 52 High Priority Items
- Read: `/docs/technical-debt/TD-051_MEMORY_CONSOLIDATION_PIPELINE.md`
- Read: `/docs/technical-debt/TD-058_COMMUNITY_SUMMARY_GENERATION.md`

### For Sprint 52+ Strategic Items
- Read: `/docs/technical-debt/TD-047_CRITICAL_PATH_E2E_TESTS.md`
- Read: `/docs/technical-debt/TD-049_IMPLICIT_USER_PROFILING.md`

### For Status Verification (Before Planning)
- Verify: `/docs/technical-debt/TD-046_RELATES_TO_RELATIONSHIP_EXTRACTION.md`
- Verify: `/docs/technical-debt/TD-052_USER_DOCUMENT_UPLOAD.md`
- Update: `/docs/technical-debt/TD-053_ADMIN_DASHBOARD_FULL.md`

---

## Key Stats

- **Total Active TDs:** 14
- **Total Story Points:** ~230 SP
- **High Priority Items:** 3 (blockers/foundational)
- **Medium Priority Items:** 6 (important features)
- **Low Priority Items:** 5 (future/backlog)
- **Documentation Quality:** Excellent (5 items with 500+ lines)
- **Implementation Plans:** Complete for all items
- **Archival Candidates:** 0 (all remain valid)

---

## Reading Order by Importance

### MUST READ (Before Sprint 52 Planning)
1. `/docs/technical-debt/SPRINT_51_REVIEW_ANALYSIS.md` - Full analysis
2. `/docs/technical-debt/ARCHIVAL_SUMMARY_2025_12_18.md` - Executive summary

### RECOMMENDED (Sprint 52 Items)
3. `TD-051_MEMORY_CONSOLIDATION_PIPELINE.md` - 21 SP, foundational
4. `TD-058_COMMUNITY_SUMMARY_GENERATION.md` - 13 SP, ready post-51.6

### REFERENCE (Future Planning)
5. `TD-047_CRITICAL_PATH_E2E_TESTS.md` - 40 SP, strategic
6. `TD-049_IMPLICIT_USER_PROFILING.md` - 21 SP, strategic

---

## Status of Reviewed Items

```
KEEP AS-IS (No Changes Needed):
  ✓ TD-043, TD-044, TD-045, TD-047, TD-049, TD-051, TD-058

REVIEW & UPDATE:
  ⚠ TD-046 (Verify completion status)
  ⚠ TD-052 (Verify implementation)
  ⚠ TD-053 (Update to PARTIAL)

KEEP IN BACKLOG (Not Urgent):
  ○ TD-054, TD-055, TD-056, TD-067

DEPRIORITIZE (Optional):
  ○ TD-059 (System works without reranking)
```

---

## Links to Analysis Documents

- Full analysis: `/docs/technical-debt/SPRINT_51_REVIEW_ANALYSIS.md`
- Executive summary: `/docs/technical-debt/ARCHIVAL_SUMMARY_2025_12_18.md`
- All TDs index: `/docs/technical-debt/TD_INDEX.md`
- Archive: `/docs/technical-debt/archive/ARCHIVE_INDEX.md`

---

**Use this document as a quick reference during sprint planning.**
