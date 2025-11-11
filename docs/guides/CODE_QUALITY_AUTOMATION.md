# Code Quality Automation - Sprint-End Checks

**Purpose:** Prevent technical debt accumulation through automated code quality checks at every sprint end.

**Strategy:** Combine pre-commit hooks (developer-facing) with Sprint-End CI checks (retrospective-facing) to maintain code quality.

---

## Overview

### Problem Statement

After Sprint 21, we identified that technical debt can accumulate quickly without regular checks:
- 780+ lines of deprecated code (unified_ingestion.py, three_phase_extractor.py)
- 30+ TODOs scattered across codebase
- Potential code duplication
- High-complexity functions (>10 cyclomatic complexity)

**Solution:** Automated Sprint-End Code Quality Report

---

## Architecture

### Two-Tier Quality System

```
┌─────────────────────┐
│  Developer Commits  │
└──────────┬──────────┘
           │
  ┌────────▼──────────┐
  │  Pre-Commit Hooks │  ← Fast checks (linting, security basics)
  │  (Every Commit)   │
  └────────┬──────────┘
           │
           │  ✅ Passes
           ▼
    ┌─────────────┐
    │  Git Commit │
    └──────┬──────┘
           │
           ▼
      [2 Weeks]
           │
           ▼
  ┌────────────────────────┐
  │ Sprint-End CI Workflow │  ← Deep checks (complexity, duplication, trends)
  │ (Every 2 Weeks)        │
  └────────┬───────────────┘
           │
           ▼
    ┌──────────────────┐
    │ Quality Report   │  ← GitHub Issue + Markdown Report
    │ + Action Items   │
    └──────────────────┘
```

---

## Sprint-End CI Workflow

### Workflow File

**Location:** `.github/workflows/code-quality-sprint-end.yml`

**Trigger:**
- **Manual:** `workflow_dispatch` (button in GitHub Actions)
- **Automatic:** Every 2 weeks on Friday 17:00 UTC (sprint end)

**Runtime:** ~10-15 minutes

**Checks Performed:**

1. **Complexity Analysis** (radon cc)
   - Cyclomatic complexity per function
   - Threshold: ≤20 high-complexity functions
   - Output: `complexity.txt`

2. **Maintainability Index** (radon mi)
   - Maintainability score 0-100 (higher is better)
   - Threshold: ≥65 average
   - Output: `maintainability.txt`

3. **Code Duplication** (jscpd)
   - Duplicated code blocks (≥5 lines, ≥50 tokens)
   - Threshold: ≤10 duplicated blocks
   - Output: `duplication-report.md`

4. **Dead Code Detection** (vulture)
   - Unused functions, imports, variables
   - Threshold: ≤15 items
   - Output: `dead-code.txt`

5. **TODO/FIXME Tracking** (grep)
   - Count TODOs, FIXMEs, HACKs in code
   - No threshold (informational)
   - Output: List of TODOs

6. **Security Scan** (bandit + pip-audit)
   - Python security issues (OWASP top 10)
   - Dependency vulnerabilities
   - Threshold: 0 high-severity issues
   - Output: `bandit-sprint-end.json`, `pip-audit-sprint-end.json`

7. **Test Coverage** (pytest --cov)
   - Line/branch coverage percentage
   - Threshold: ≥80%
   - Output: `coverage.json`

8. **Lines of Code Metrics** (wc + find)
   - Source LOC, Test LOC, Test/Code ratio
   - Threshold: Test/Code ratio ≥0.5
   - Output: Metrics in report

---

## Report Generation

### Script

**Location:** `scripts/generate_sprint_end_report.py`

**Usage:**
```bash
python scripts/generate_sprint_end_report.py \
  --sprint 22 \
  --complexity 15 \
  --maintainability 72 \
  --duplicates 5 \
  --dead-code 8 \
  --todos 25 \
  --fixmes 3 \
  --security-high 0 \
  --security-medium 2 \
  --dep-vulns 1 \
  --coverage 85.3 \
  --loc 12500 \
  --test-loc 7200 \
  --output docs/sprints/SPRINT_22_CODE_QUALITY_REPORT.md
```

**Output:**
- Markdown report with status icons (🟢🟡🔴)
- Executive summary table
- Detailed analysis per metric
- Action items (Critical, High, Medium, Low priority)
- Trend analysis section (requires historical data)

**Example Output:**
```markdown
# Sprint 22 - Code Quality Report

**Generated:** 2025-11-11
**Status:** 🟢 PASSED

## 📊 Executive Summary

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| **Complexity** | 15 high | ≤20 | 🟢 PASS |
| **Maintainability** | 72 | ≥65 | 🟢 PASS |
| **Code Duplication** | 5 instances | ≤10 | 🟢 PASS |
| **Dead Code** | 8 items | ≤15 | 🟢 PASS |
| **Security (High)** | 0 | 0 | 🟢 PASS |
| **Test Coverage** | 85.3% | ≥80% | 🟢 PASS |
| **Test/Code Ratio** | 0.58 | ≥0.5 | 🟢 PASS |

## 🎯 Sprint Retrospective Actions

### Critical (Fix Immediately)
- None

### High Priority (This Sprint)
- [ ] Update 1 vulnerable dependency (run `pip-audit` for details)
- [ ] Fix 2 medium-severity security issues

### Medium Priority (Next Sprint)
- [ ] Convert 3 FIXMEs to GitHub issues
- [ ] Schedule resolution of 25 TODOs

### Low Priority (Backlog)
- None

---

**Generated by:** Sprint-End Code Quality Check (GitHub Actions)
**Next Check:** Sprint 23 End
```

---

## Usage

### Manual Trigger (Recommended at Sprint End)

1. Go to GitHub Actions tab
2. Select "Sprint-End Code Quality Report" workflow
3. Click "Run workflow"
4. Enter sprint number (e.g., "22")
5. Click "Run workflow" button

**Wait 10-15 minutes** for report generation.

### Automatic Trigger (Optional)

Workflow runs automatically every 2 weeks on Friday at 17:00 UTC (end of sprint week).

**Customize schedule:**
```yaml
schedule:
  - cron: '0 17 * * 5'  # Every Friday at 17:00 UTC
```

Change to your sprint end day/time.

---

## Interpreting Results

### Status Icons

- 🟢 **PASS** - Metric meets threshold, no action needed
- 🟡 **WARN** - Metric slightly below/above threshold, monitor
- 🔴 **FAIL** - Metric exceeds threshold, immediate action required
- ℹ️ **INFO** - Informational metric, no threshold

### Thresholds

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| **High Complexity** | ≤20 functions | >10 cyclomatic complexity is risky |
| **Maintainability** | ≥65 | Below 65 indicates refactoring needed |
| **Duplication** | ≤10 blocks | >10% duplication is high |
| **Dead Code** | ≤15 items | False positives possible, review needed |
| **Security (High)** | 0 | High-severity must be fixed immediately |
| **Security (Medium)** | ≤5 | Medium-severity should be fixed soon |
| **Coverage** | ≥80% | Industry standard minimum |
| **Test/Code Ratio** | ≥0.5 | More tests than code (good practice) |

**Note:** Thresholds can be adjusted in `.github/workflows/code-quality-sprint-end.yml` step: "Check quality thresholds"

---

## Action Items Workflow

### After Sprint-End Report Generated

1. **Review Report:**
   - Download artifact: `docs/sprints/SPRINT_N_CODE_QUALITY_REPORT.md`
   - Read Executive Summary
   - Check status (🟢 PASSED or 🔴 FAILED)

2. **Create GitHub Issues for Critical Items:**
   - Copy Critical actions from report
   - Create issues with label `technical-debt`
   - Assign to next sprint

3. **Discuss in Sprint Retrospective:**
   - Show trend analysis (compare with previous sprint)
   - Identify patterns (e.g., complexity increasing)
   - Decide on actions for next sprint

4. **Update Sprint Plan:**
   - Add refactoring tasks based on report
   - Budget time for technical debt reduction
   - Example: "Sprint 23: Fix 2 medium-severity security issues (2h)"

---

## Pre-Commit Hooks (Developer-Facing)

### Already Configured

Pre-commit hooks are already comprehensive (see `.pre-commit-config.yaml`):
- ✅ Ruff Linter + Formatter
- ✅ Black Formatter
- ✅ MyPy Type Checker (strict mode)
- ✅ Bandit Security Scanner
- ✅ Safety Dependency Scanner
- ✅ Detect Secrets
- ✅ Naming Conventions Check
- ✅ ADR Detection
- ✅ Import Validation
- ✅ Router Prefix Validation
- ✅ Docstring Validation
- ✅ Commit Message Validation

**These run on EVERY commit** (fast checks only).

### Optional: Add Complexity Check to Pre-Commit

**Warning:** Complexity checks are slow (~5-10s), may annoy developers.

**Add to `.pre-commit-config.yaml`:**
```yaml
  # OPTIONAL: Complexity Check (slow, use sparingly)
  - repo: local
    hooks:
      - id: check-complexity
        name: "🔬 Check Complexity"
        entry: radon cc src/ --min B --show-complexity
        language: system
        pass_filenames: false
        # Only run manually or on CI
        stages: [manual]
```

**Usage:**
```bash
pre-commit run check-complexity --all-files
```

---

## Integration with Sprint Process

### Sprint Start (Week 1, Day 1)

1. Review previous sprint's Code Quality Report
2. Add technical debt tasks to Sprint Backlog
3. Budget time for refactoring (10-20% of sprint capacity)

### During Sprint (Continuous)

1. Pre-commit hooks catch issues early (every commit)
2. Developers address TODOs/FIXMEs as they work
3. Code reviews check for complexity/duplication

### Sprint End (Week 2, Friday)

1. **Manual trigger:** Run Sprint-End Code Quality Report
2. **Review:** Download and review report
3. **Create Issues:** Convert Critical/High priority items to GitHub issues
4. **Retrospective:** Discuss trends, decide on actions

### Sprint Retrospective

**Agenda Item:** Code Quality Review (10-15 minutes)
- Show Sprint-End Report
- Compare with previous sprint (trend analysis)
- Discuss: What improved? What got worse?
- Decide: What to focus on next sprint?

**Example Discussion:**
- "Complexity increased from 12 → 18 functions. Why?"
- "Dead code decreased from 20 → 8. Good progress!"
- "Test coverage dropped from 85% → 82%. Need more tests."

---

## Troubleshooting

### Workflow Fails

**Error:** "Check quality thresholds" step fails
**Cause:** One or more thresholds exceeded (complexity >20, coverage <80%, security issues)
**Solution:** This is intentional! Review report, create issues, fix in next sprint.

**Error:** Tool not found (radon, vulture, jscpd)
**Cause:** Tool not installed in CI environment
**Solution:** Check step "Install code quality tools" in workflow, ensure pip install succeeds.

### Report Not Generated

**Cause:** Script failed, missing metrics
**Solution:** Check CI logs, ensure all previous steps succeeded. Script handles missing data gracefully (shows "N/A").

### False Positives

**Dead Code Detection:**
- Vulture may flag code used dynamically (e.g., MCP tools, FastAPI dependencies)
- Review manually, add `# noqa: vulture` comment if false positive

**Complexity:**
- Some functions legitimately complex (e.g., state machines)
- Consider refactoring or document why high complexity is necessary

---

## Customization

### Adjust Thresholds

**Edit:** `.github/workflows/code-quality-sprint-end.yml`

**Step:** "Check quality thresholds"

```yaml
# Example: Relax complexity threshold
if [ "$HIGH_COMPLEXITY" -gt 30 ]; then  # Changed from 20 to 30
  echo "❌ Too many high-complexity functions: $HIGH_COMPLEXITY (threshold: 30)"
  FAIL=1
fi
```

### Add New Checks

**Example:** Add import sorting check

**Step:** Add to workflow before "Generate sprint-end report"

```yaml
- name: Check import sorting
  run: |
    echo "## Import Sorting" >> $GITHUB_STEP_SUMMARY
    isort src/ --check-only --diff | tee import-sorting.txt || true
    UNSORTED=$(wc -l < import-sorting.txt || echo "0")
    echo "Unsorted imports: $UNSORTED" >> $GITHUB_STEP_SUMMARY
    echo "unsorted_imports=$UNSORTED" >> $GITHUB_OUTPUT
```

**Then:** Update `scripts/generate_sprint_end_report.py` to include new metric in report.

---

## Best Practices

### 1. Run at Consistent Times

- Same day/time every sprint (e.g., Friday 17:00 UTC)
- Creates predictable routine
- Easier to track trends

### 2. Store Historical Reports

- Keep all reports in `docs/sprints/`
- Compare trends over time (Sprint N-1, N-2, N-3)
- Identify patterns (e.g., complexity always increases before release)

### 3. Balance Thresholds

- Too strict: CI always fails, team ignores
- Too lenient: Technical debt accumulates
- **Recommended:** Start lenient, tighten gradually over 3-4 sprints

### 4. Prioritize Actions

- Not every issue needs immediate fixing
- Focus on Critical/High priority items
- Low priority can wait 2-3 sprints

### 5. Celebrate Improvements

- Show positive trends in retrospective
- "Test coverage increased 75% → 85% in 3 sprints!"
- Motivates team to maintain quality

---

## Metrics Definitions

### Cyclomatic Complexity

**Definition:** Number of independent paths through code (if/else, loops, etc.)

**Interpretation:**
- 1-5: Simple, easy to test
- 6-10: Moderate, manageable
- 11-20: Complex, refactor recommended
- >20: Very complex, high risk

**Tools:** radon cc, mccabe

### Maintainability Index

**Definition:** 0-100 score combining complexity, LOC, Halstead Volume

**Interpretation:**
- 85-100: Excellent
- 65-84: Good
- 20-64: Needs refactoring
- 0-19: Urgent refactoring

**Tools:** radon mi

### Code Duplication

**Definition:** Identical or very similar code blocks (≥5 lines, ≥50 tokens)

**Interpretation:**
- 0-5%: Acceptable
- 5-10%: High
- >10%: Very high, refactor

**Tools:** jscpd, dupeguru

### Dead Code

**Definition:** Unused functions, imports, variables, classes

**Interpretation:**
- Review manually (false positives common)
- Delete confirmed dead code
- Update or remove deprecated functions

**Tools:** vulture, pylint

---

## Related Documents

- [Pre-Commit Hooks Configuration](../../.pre-commit-config.yaml)
- [Sprint 22 Hybrid Approach Plan](../refactoring/SPRINT_22_HYBRID_APPROACH_PLAN.md)
- [Naming Conventions](../NAMING_CONVENTIONS.md)
- [Sprint Plans](../sprints/)

---

## FAQ

**Q: Do pre-commit hooks replace Sprint-End checks?**
A: No, they complement each other. Pre-commit hooks catch issues early (linting, security basics). Sprint-End checks are deeper (complexity, duplication, trends).

**Q: Can I run Sprint-End checks locally?**
A: Yes, manually run each tool:
```bash
radon cc src/ -a -s --min B
radon mi src/ -s
vulture src/ --min-confidence 80
bandit -r src/ -f json -o bandit-report.json
pytest tests/ --cov=src --cov-report=term
```

**Q: What if CI fails due to thresholds?**
A: This is intentional! It means technical debt exceeded thresholds. Review report, create issues for next sprint, fix iteratively.

**Q: How often should thresholds be adjusted?**
A: Review every 3-4 sprints. If CI always fails (team overwhelmed) → relax. If always passes (too easy) → tighten.

**Q: Can Sprint-End checks block merges?**
A: Not recommended. These are retrospective checks, not blocking. Use pre-commit hooks for blocking (fast checks only).

---

**Maintained by:** Infrastructure Team
**Last Updated:** 2025-11-11 (Sprint 22)
**Next Review:** Sprint 24 (2025-11-25)
