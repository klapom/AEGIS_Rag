#!/usr/bin/env python3
"""Generate Sprint-End Code Quality Report.

This script aggregates code quality metrics from various tools and generates
a comprehensive markdown report for sprint retrospectives.

Usage:
    python scripts/generate_sprint_end_report.py --sprint 22 --output report.md
"""

import argparse
from datetime import datetime
from pathlib import Path


def generate_report(args) -> str:
    """Generate markdown report from metrics.

    Args:
        args: Argparse namespace with metrics

    Returns:
        Markdown report string
    """
    sprint_number = args.sprint
    date = datetime.now().strftime("%Y-%m-% d")

    report = f"""# Sprint {sprint_number} - Code Quality Report

**Generated:** {date}
**Status:** {'🟢 PASSED' if _check_thresholds(args) else '🔴 FAILED'}

---

## 📊 Executive Summary

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| **Complexity** | {args.complexity} high | ≤20 | {_status_icon(int(args.complexity or 0), 20, inverse=True)} |
| **Maintainability** | {args.maintainability} | ≥65 | {_status_icon(float(args.maintainability or 0), 65)} |
| **Code Duplication** | {args.duplicates} instances | ≤10 | {_status_icon(int(args.duplicates or 0), 10, inverse=True)} |
| **Dead Code** | {args.dead_code} items | ≤15 | {_status_icon(int(args.dead_code or 0), 15, inverse=True)} |
| **TODOs/FIXMEs** | {args.todos}/{args.fixmes} | - | ℹ️ |
| **Security (High)** | {args.security_high} | 0 | {_status_icon(int(args.security_high or 0), 0, inverse=True)} |
| **Security (Medium)** | {args.security_medium} | ≤5 | {_status_icon(int(args.security_medium or 0), 5, inverse=True)} |
| **Dep Vulnerabilities** | {args.dep_vulns} | 0 | {_status_icon(int(args.dep_vulns or 0), 0, inverse=True)} |
| **Test Coverage** | {args.coverage}% | ≥80% | {_status_icon(float(args.coverage or 0), 80)} |
| **Lines of Code** | {args.loc} | - | ℹ️ |
| **Test/Code Ratio** | {_calculate_ratio(args.test_loc, args.loc)} | ≥0.5 | {_ratio_status(args.test_loc, args.loc)} |

---

## 🎯 Complexity Analysis

**High Complexity Functions:** {args.complexity}
**Threshold:** ≤20

{_complexity_analysis(args.complexity)}

**Recommendation:**
- Functions with complexity >10 should be refactored
- Use helpers, extract methods, simplify conditionals
- Target: All functions ≤10 complexity

---

## 🔧 Maintainability Index

**Average MI:** {args.maintainability}
**Scale:** 0-100 (higher is better)

{_maintainability_analysis(args.maintainability)}

**Recommendation:**
- MI <20: Urgent refactoring needed
- MI 20-65: Consider refactoring
- MI >65: Maintainable code

---

## 📋 Code Duplication

**Duplicated Blocks:** {args.duplicates}
**Threshold:** ≤10

{_duplication_analysis(args.duplicates)}

**Recommendation:**
- Extract duplicated code to helpers/utilities
- Use inheritance, composition, or mixins
- Target: <5% duplication

---

## 🗑️ Dead Code Detection

**Potential Dead Code Items:** {args.dead_code}
**Threshold:** ≤15

{_dead_code_analysis(args.dead_code)}

**Recommendation:**
- Review detected items (false positives possible)
- Delete confirmed dead code
- Update or remove deprecated functions
- Clean up unused imports

---

## 📝 TODO/FIXME Tracking

**TODOs:** {args.todos}
**FIXMEs:** {args.fixmes}

{_todo_analysis(args.todos, args.fixmes)}

**Recommendation:**
- Convert critical FIXMEs to GitHub issues
- Schedule TODO resolution in next sprint
- Remove resolved TODOs promptly

---

## 🔒 Security Analysis

**High Severity:** {args.security_high}
**Medium Severity:** {args.security_medium}
**Dependency Vulnerabilities:** {args.dep_vulns}

{_security_analysis(args.security_high, args.security_medium, args.dep_vulns)}

**Recommendation:**
- Fix ALL high-severity issues immediately
- Schedule medium-severity fixes within 2 sprints
- Update vulnerable dependencies (pip-audit)
- Run `bandit -r src/` for details

---

## ✅ Test Coverage

**Current Coverage:** {args.coverage}%
**Threshold:** ≥80%

{_coverage_analysis(args.coverage)}

**Recommendation:**
- Maintain >80% coverage as minimum
- Focus on uncovered critical paths
- Add integration tests for new features
- Review edge cases and error handling

---

## 📏 Lines of Code Metrics

**Source LOC:** {args.loc}
**Test LOC:** {args.test_loc}
**Test/Code Ratio:** {_calculate_ratio(args.test_loc, args.loc)}

{_loc_analysis(args.loc, args.test_loc)}

**Recommendation:**
- Maintain test/code ratio >0.5 (more tests than code)
- Monitor LOC growth (should correlate with features)
- Consider splitting large modules (>500 LOC)

---

## 🎯 Sprint Retrospective Actions

### Critical (Fix Immediately)
{_generate_critical_actions(args)}

### High Priority (This Sprint)
{_generate_high_priority_actions(args)}

### Medium Priority (Next Sprint)
{_generate_medium_priority_actions(args)}

### Low Priority (Backlog)
{_generate_low_priority_actions(args)}

---

## 📈 Trend Analysis

**Note:** Trend analysis requires historical data (Sprint N-1, N-2).

To track trends, save this report and compare with previous sprints:
- **Complexity Trend:** Compare high complexity function count
- **Coverage Trend:** Track coverage percentage over time
- **LOC Trend:** Monitor codebase growth
- **Debt Trend:** Track TODO/FIXME accumulation

---

## 🔗 Detailed Reports

For detailed analysis, see CI artifacts:
- `complexity.txt` - Full complexity report
- `maintainability.txt` - Maintainability index per file
- `duplication-report.md` - Duplicated code blocks
- `dead-code.txt` - Unused code detection
- `bandit-sprint-end.json` - Security issues
- `pip-audit-sprint-end.json` - Dependency vulnerabilities
- `coverage.json` - Test coverage details

---

**Generated by:** Sprint-End Code Quality Check (GitHub Actions)
**Next Check:** Sprint {int(sprint_number) + 1} End
"""

    return report


def _status_icon(value: float, threshold: float, inverse: bool = False) -> str:
    """Generate status icon based on threshold.

    Args:
        value: Actual value
        threshold: Threshold value
        inverse: If True, lower is better (e.g., complexity)

    Returns:
        Status icon (🟢, 🟡, 🔴)
    """
    if inverse:
        if value <= threshold:
            return "🟢 PASS"
        elif value <= threshold * 1.5:
            return "🟡 WARN"
        else:
            return "🔴 FAIL"
    else:
        if value >= threshold:
            return "🟢 PASS"
        elif value >= threshold * 0.8:
            return "🟡 WARN"
        else:
            return "🔴 FAIL"


def _calculate_ratio(test_loc: str, code_loc: str) -> str:
    """Calculate test/code ratio."""
    try:
        ratio = int(test_loc) / int(code_loc)
        return f"{ratio:.2f}"
    except (ValueError, ZeroDivisionError):
        return "N/A"


def _ratio_status(test_loc: str, code_loc: str) -> str:
    """Status icon for test/code ratio."""
    try:
        ratio = int(test_loc) / int(code_loc)
        return _status_icon(ratio, 0.5)
    except (ValueError, ZeroDivisionError):
        return "ℹ️"


def _check_thresholds(args) -> bool:
    """Check if all thresholds are met."""
    try:
        if int(args.complexity or 0) > 20:
            return False
        if int(args.security_high or 0) > 0:
            return False
        if float(args.coverage or 0) < 80:
            return False
        return True
    except (ValueError, TypeError):
        return False


def _complexity_analysis(complexity: str) -> str:
    """Generate complexity analysis text."""
    try:
        count = int(complexity or 0)
        if count == 0:
            return "✅ **Excellent!** No high-complexity functions detected."
        elif count <= 10:
            return f"🟡 **Good.** {count} high-complexity functions detected. Consider refactoring."
        elif count <= 20:
            return f"🟠 **Warning.** {count} high-complexity functions. Refactoring recommended."
        else:
            return f"🔴 **Critical.** {count} high-complexity functions. Immediate refactoring needed."
    except (ValueError, TypeError):
        return "ℹ️ Data not available."


def _maintainability_analysis(mi: str) -> str:
    """Generate maintainability analysis text."""
    try:
        value = float(mi or 0)
        if value >= 85:
            return "✅ **Excellent!** Code is highly maintainable."
        elif value >= 65:
            return "🟢 **Good.** Code is maintainable."
        elif value >= 20:
            return "🟡 **Warning.** Some modules need refactoring."
        else:
            return "🔴 **Critical.** Code maintainability is poor."
    except (ValueError, TypeError):
        return "ℹ️ Data not available."


def _duplication_analysis(duplicates: str) -> str:
    """Generate duplication analysis text."""
    try:
        count = int(duplicates or 0)
        if count == 0:
            return "✅ **Excellent!** No significant code duplication detected."
        elif count <= 5:
            return f"🟢 **Good.** {count} duplicated blocks. Acceptable level."
        elif count <= 10:
            return f"🟡 **Warning.** {count} duplicated blocks. Consider extraction."
        else:
            return f"🔴 **Critical.** {count} duplicated blocks. Refactoring needed."
    except (ValueError, TypeError):
        return "ℹ️ Data not available."


def _dead_code_analysis(dead_code: str) -> str:
    """Generate dead code analysis text."""
    try:
        count = int(dead_code or 0)
        if count == 0:
            return "✅ **Excellent!** No dead code detected."
        elif count <= 5:
            return f"🟢 **Good.** {count} potential dead code items (review for false positives)."
        elif count <= 15:
            return f"🟡 **Warning.** {count} potential dead code items. Review and clean up."
        else:
            return f"🔴 **Critical.** {count} potential dead code items. Major cleanup needed."
    except (ValueError, TypeError):
        return "ℹ️ Data not available."


def _todo_analysis(todos: str, fixmes: str) -> str:
    """Generate TODO/FIXME analysis text."""
    try:
        todo_count = int(todos or 0)
        fixme_count = int(fixmes or 0)
        total = todo_count + fixme_count

        if total == 0:
            return "✅ **Excellent!** No outstanding TODOs or FIXMEs."
        elif total <= 10:
            return f"🟢 **Good.** {total} total TODOs/FIXMEs. Manageable level."
        elif total <= 30:
            return f"🟡 **Warning.** {total} total TODOs/FIXMEs. Consider scheduling resolution."
        else:
            return f"🔴 **Critical.** {total} total TODOs/FIXMEs. Many unresolved issues."
    except (ValueError, TypeError):
        return "ℹ️ Data not available."


def _security_analysis(high: str, medium: str, dep_vulns: str) -> str:
    """Generate security analysis text."""
    try:
        high_count = int(high or 0)
        medium_count = int(medium or 0)
        vuln_count = int(dep_vulns or 0)

        if high_count == 0 and medium_count == 0 and vuln_count == 0:
            return "✅ **Excellent!** No security issues detected."
        elif high_count == 0:
            return f"🟡 **Warning.** {medium_count} medium-severity issues, {vuln_count} dependency vulnerabilities."
        else:
            return f"🔴 **Critical.** {high_count} high-severity security issues! Fix immediately."
    except (ValueError, TypeError):
        return "ℹ️ Data not available."


def _coverage_analysis(coverage: str) -> str:
    """Generate coverage analysis text."""
    try:
        value = float(coverage or 0)
        if value >= 90:
            return "✅ **Excellent!** Coverage is very high."
        elif value >= 80:
            return "🟢 **Good.** Coverage meets threshold."
        elif value >= 70:
            return "🟡 **Warning.** Coverage slightly below threshold."
        else:
            return "🔴 **Critical.** Coverage is too low."
    except (ValueError, TypeError):
        return "ℹ️ Data not available."


def _loc_analysis(loc: str, test_loc: str) -> str:
    """Generate LOC analysis text."""
    try:
        code = int(loc or 0)
        tests = int(test_loc or 0)
        ratio = tests / code if code > 0 else 0

        if ratio >= 1.0:
            return "✅ **Excellent!** More test code than source code."
        elif ratio >= 0.5:
            return "🟢 **Good.** Healthy test/code ratio."
        elif ratio >= 0.3:
            return "🟡 **Warning.** Consider adding more tests."
        else:
            return "🔴 **Critical.** Test coverage is insufficient."
    except (ValueError, TypeError, ZeroDivisionError):
        return "ℹ️ Data not available."


def _generate_critical_actions(args) -> str:
    """Generate critical action items."""
    actions = []

    try:
        if int(args.security_high or 0) > 0:
            actions.append(f"- [ ] Fix {args.security_high} high-severity security issues (run `bandit -r src/` for details)")

        if float(args.coverage or 0) < 70:
            actions.append(f"- [ ] Increase test coverage from {args.coverage}% to >80%")

        if int(args.complexity or 0) > 30:
            actions.append(f"- [ ] Refactor {args.complexity} high-complexity functions (target: ≤20)")

    except (ValueError, TypeError):
        pass

    return "\n".join(actions) if actions else "- None"


def _generate_high_priority_actions(args) -> str:
    """Generate high-priority action items."""
    actions = []

    try:
        if int(args.security_medium or 0) > 5:
            actions.append(f"- [ ] Fix {args.security_medium} medium-severity security issues")

        if int(args.dep_vulns or 0) > 0:
            actions.append(f"- [ ] Update {args.dep_vulns} vulnerable dependencies (run `pip-audit` for details)")

        if float(args.coverage or 0) < 80:
            actions.append(f"- [ ] Add tests to reach 80% coverage (currently {args.coverage}%)")

        if int(args.duplicates or 0) > 10:
            actions.append(f"- [ ] Extract {args.duplicates} duplicated code blocks")

    except (ValueError, TypeError):
        pass

    return "\n".join(actions) if actions else "- None"


def _generate_medium_priority_actions(args) -> str:
    """Generate medium-priority action items."""
    actions = []

    try:
        if int(args.dead_code or 0) > 15:
            actions.append(f"- [ ] Review and remove {args.dead_code} dead code items")

        if int(args.fixmes or 0) > 10:
            actions.append(f"- [ ] Convert {args.fixmes} FIXMEs to GitHub issues")

        if int(args.complexity or 0) > 20:
            actions.append(f"- [ ] Refactor remaining high-complexity functions")

    except (ValueError, TypeError):
        pass

    return "\n".join(actions) if actions else "- None"


def _generate_low_priority_actions(args) -> str:
    """Generate low-priority action items."""
    actions = []

    try:
        if int(args.todos or 0) > 20:
            actions.append(f"- [ ] Schedule resolution of {args.todos} TODOs")

        if float(args.maintainability or 0) < 65:
            actions.append("- [ ] Improve maintainability index (add docs, simplify logic)")

    except (ValueError, TypeError):
        pass

    return "\n".join(actions) if actions else "- None"


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Generate sprint-end code quality report")
    parser.add_argument("--sprint", required=True, help="Sprint number")
    parser.add_argument("--complexity", default="0", help="High complexity function count")
    parser.add_argument("--maintainability", default="0", help="Average maintainability index")
    parser.add_argument("--duplicates", default="0", help="Duplicated code blocks")
    parser.add_argument("--dead-code", default="0", help="Dead code items")
    parser.add_argument("--todos", default="0", help="TODO count")
    parser.add_argument("--fixmes", default="0", help="FIXME count")
    parser.add_argument("--security-high", default="0", help="High-severity security issues")
    parser.add_argument("--security-medium", default="0", help="Medium-severity security issues")
    parser.add_argument("--dep-vulns", default="0", help="Dependency vulnerabilities")
    parser.add_argument("--coverage", default="0", help="Test coverage percentage")
    parser.add_argument("--loc", default="0", help="Lines of code")
    parser.add_argument("--test-loc", default="0", help="Test lines of code")
    parser.add_argument("--output", required=True, help="Output file path")

    args = parser.parse_args()

    # Generate report
    report = generate_report(args)

    # Write to file
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)

    print(f"✅ Sprint-end report generated: {output_path}")


if __name__ == "__main__":
    main()
