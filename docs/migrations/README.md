# Database Migrations

This directory contains database migration scripts and documentation for AegisRAG.

**Last Updated:** Sprint 124 (2026-02-07)

---

## Migration Index

| ID | Sprint | Title | Status | Date | Impact |
|----|--------|-------|--------|------|--------|
| 001 | 124 | NULL Relation Types Backfill | ✅ Complete | 2026-02-07 | 1,021 relations |

---

## Migration 001: NULL Relation Types Backfill

**Problem:** 1,021 `RELATES_TO` relationships had `relation_type = NULL` from before Sprint 124's S-P-O extraction fix.

**Solution:** Automated pattern matching against 21 universal relation types (ADR-040) with `RELATED_TO` fallback.

**Results:**
- ✅ 1,021 relations migrated (0 NULL remaining)
- ✅ 213 relations (20.9%) matched specific types with ~85% accuracy
- ⚠️ 808 relations (79.1%) fell back to generic `RELATED_TO` (acceptable given pre-Sprint 124 data quality)
- ✅ 0 relations deleted (non-destructive migration)
- ✅ 0 orphaned entities (data integrity maintained)

**Execution:**
```bash
# Preview changes
poetry run python scripts/backfill_relation_types.py --dry-run

# Run migration
poetry run python scripts/backfill_relation_types.py
```

**Files:**
- Script: `/home/admin/projects/aegisrag/AEGIS_Rag/scripts/backfill_relation_types.py`
- Documentation: `MIGRATION_001_NULL_RELATION_TYPES.md`
- Technical Analysis: `MIGRATION_001_ANALYSIS.md`

**Performance:** 0.3s execution time (1,021 relations in 3 batches)

---

## Migration Best Practices

### Before Running a Migration

1. **Backup Database:**
   ```bash
   # Neo4j backup
   docker exec neo4j neo4j-admin database dump neo4j --to-path=/backups

   # Qdrant backup
   docker exec qdrant-qdrant-1 tar -czf /qdrant/backups/backup-$(date +%F).tar.gz /qdrant/storage
   ```

2. **Test in Development:**
   - Run migration on dev environment first
   - Verify results with sample queries
   - Check performance on production-sized dataset

3. **Run Dry-Run:**
   - All migration scripts must support `--dry-run` flag
   - Review dry-run output carefully
   - Check estimated execution time

4. **Document Migration:**
   - Create `MIGRATION_XXX_*.md` in this directory
   - Document problem, solution, results
   - Include rollback plan

### During Migration

1. **Monitor Progress:**
   - Log all operations with timestamps
   - Use batch processing (avoid single large transaction)
   - Track metrics (records processed, time elapsed)

2. **Handle Errors:**
   - Use try-catch with detailed error logging
   - Implement retry logic for transient failures
   - Fail fast for critical errors

3. **Maintain Idempotency:**
   - Safe to run multiple times
   - Check if migration already applied
   - Skip already-migrated records

### After Migration

1. **Verify Results:**
   - Run verification queries
   - Check data integrity (foreign keys, constraints)
   - Compare before/after metrics

2. **Monitor Performance:**
   - Check query performance on migrated data
   - Monitor database size changes
   - Watch for anomalies in application logs

3. **Update Documentation:**
   - Mark migration as complete in README
   - Archive migration scripts (if one-time)
   - Update ADRs if architectural changes

4. **Clean Up:**
   - Remove temporary tables/indexes
   - Archive old data (if applicable)
   - Update monitoring dashboards

---

## Migration Template

Use this template for new migrations:

```python
#!/usr/bin/env python3
"""
Database Migration XXX: [Title]

Problem:
    [Brief description of the problem]

Solution:
    [Brief description of the solution]

Usage:
    python scripts/migrate_xxx.py              # Execute migration
    python scripts/migrate_xxx.py --dry-run    # Preview changes
"""

import asyncio
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def analyze_state():
    """Analyze current state before migration."""
    logger.info("Analyzing current state...")
    # Implementation here

async def execute_migration(dry_run: bool = False):
    """Execute migration."""
    logger.info("=" * 60)
    logger.info("MIGRATION XXX: [Title]")
    logger.info("=" * 60)

    # Step 1: Analyze
    await analyze_state()

    # Step 2: Migrate
    if not dry_run:
        logger.info("Executing migration...")
        # Implementation here
    else:
        logger.info("[DRY-RUN] Would execute migration")

    # Step 3: Verify
    logger.info("Verifying results...")
    # Implementation here

async def main():
    parser = argparse.ArgumentParser(description="Migration XXX: [Title]")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying database")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("🔍 Running in DRY-RUN mode")
    else:
        logger.info("🚀 Running migration")

    await execute_migration(dry_run=args.dry_run)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Migration Checklist

Before marking a migration as complete, ensure:

- [ ] Migration script is idempotent (safe to run multiple times)
- [ ] Dry-run mode is implemented and tested
- [ ] Comprehensive logging is in place
- [ ] Verification queries confirm success
- [ ] Documentation is complete (MIGRATION_XXX_*.md)
- [ ] scripts/README.md is updated
- [ ] Performance is acceptable (<5s for <10k records)
- [ ] Rollback plan is documented
- [ ] Database backup is taken
- [ ] Production deployment plan is reviewed

---

## Migration History

### Sprint 124 (2026-02-07)

**Migration 001: NULL Relation Types Backfill**
- **Problem:** 1,021 NULL relation_types from pre-Sprint 124 extraction
- **Solution:** Pattern matching + generic fallback
- **Result:** ✅ 100% migrated, 20.9% specific types, 79.1% generic
- **Time:** 0.3s
- **Impact:** Improved graph query quality, enabled semantic filtering

---

## Future Migrations (Planned)

### Sprint 125 (Tentative)

**Migration 002: Refine RELATED_TO Relations (808 relations)**
- **Problem:** 79% of relations use generic `RELATED_TO` type
- **Solution:** LLM-based classification (Nemotron3 Nano)
- **Expected Outcome:** 80% of 808 relations upgraded to specific types
- **Estimated Time:** 5-10 minutes (LLM inference)

### Sprint 126 (Tentative)

**Migration 003: Fix NULL Entity Names**
- **Problem:** Many relations have `name = None` for source/target entities
- **Solution:** Re-extract entities from descriptions or delete invalid relations
- **Expected Outcome:** All entities have valid names or invalid relations removed

---

## Contact

For migration questions or issues:
- **Backend Agent** (Claude Sonnet 4.5) - Core logic, database operations
- **Infrastructure Agent** - Backup/restore, deployment
- **Documentation Agent** - Migration documentation, ADRs

---

**Total Migrations:** 1
**Active Migrations:** 0
**Pending Migrations:** 2 (tentative)
