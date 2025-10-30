# Deprecated Scripts

**Archived**: Sprint 19 (2025-10-30)

These scripts are **obsolete** and replaced by newer implementations.

## Obsolete Reindex Scripts (5 scripts)

| Script | Reason for Deprecation | Replacement |
|--------|------------------------|-------------|
| `trigger_reindex.py` | No path-traversal fix | `index_three_specific_docs.py` |
| `simple_reindex.py` | Incomplete error handling | `index_documents.py` |
| `hybrid_reindex.py` | Old chunking strategy | `index_documents.py` |
| `reset_and_reindex.py` | No start_token fix | `index_one_doc_test.py` |
| `index_three_docs.py` | Hardcoded paths | `index_three_specific_docs.py` |

**Issues**:
- Missing Sprint 10 path-traversal fix (commit 79abe52)
- Missing Sprint 16 start_token fix (commit d8e52c0)
- Outdated chunking parameters (512 tokens vs 600 tokens)

## Obsolete Test Scripts (7 scripts)

| Script | Reason for Deprecation | Notes |
|--------|------------------------|-------|
| `run_failing_tests_with_fixes.py` | Sprint 11 temporary fix | Tests now pass |
| `apply_all_fixes.py` | One-time migration script | Sprint 11 fixes applied |
| `add_test_logging.py` | Debug logging added | Logging now in conftest.py |
| `demo_router.py` | Early routing prototype | Replaced by LangGraph router |
| `test_vector_agent.py` | Sprint 6 agent prototype | Now in `tests/agents/` |
| `test_real_intent_classification.py` | Intent classifier test | Moved to `tests/agents/` |
| `test_hybrid_search.py` | Early hybrid search test | Replaced by `test_hybrid_10docs.py` |

## Why Keep These?

**DO NOT USE** these scripts in production. They are kept for:
1. Historical reference (understanding code evolution)
2. Sprint report validation (matching completion reports)
3. Disaster recovery (if new scripts have regressions)

## If You Need to Use Old Scripts

1. Check `git log` for when they were last functional
2. Review Sprint completion reports for context
3. Use modern replacements in `scripts/` instead

---

**Safe to Delete?**

After Sprint 20 completion, review if these are still needed for historical reference. If git history is sufficient, these can be removed.

---

**Archived**: Sprint 19 (2025-10-30)
