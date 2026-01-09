# Sprint 83 Plan: RAGAS Phase 2 - Structured Data

**Epic:** 1000-Sample Stratified RAGAS Evaluation Benchmark
**Phase:** 2 of 3
**ADR Reference:** [ADR-048](../adr/ADR-048-ragas-1000-sample-benchmark.md)
**Prerequisite:** Sprint 82 (Phase 1 complete)
**Duration:** 7-10 days
**Total Story Points:** 13 SP
**Status:** 📝 Planned

---

## Sprint Goal

Expand the RAGAS benchmark with **300 structured data samples** from:
- **T2-RAGBench:** Financial tables (100 samples)
- **CodeRepoQA:** Code/config files (100 samples)
- **Additional clean_text:** Fill remaining quotas (100 samples)

Plus: **Statistical rigor package** for publication-ready metrics.

---

## Context

### After Sprint 82
- 500 samples (clean_text, log_ticket)
- 10% unanswerables
- ±4% confidence interval

### Target State (Sprint 83)
- **800 total samples** (500 + 300)
- **4 doc_types:** clean_text, log_ticket, table, code_config
- **Statistical rigor:** Bootstrap CI, significance tests
- ±3.5% confidence interval

---

## Features

| # | Feature | SP | Priority | Status |
|---|---------|-----|----------|--------|
| 83.1 | T2-RAGBench table processor | 5 | P0 | 📝 Planned |
| 83.2 | CodeRepoQA code extractor | 5 | P0 | 📝 Planned |
| 83.3 | Statistical rigor package | 2 | P1 | 📝 Planned |
| 83.4 | Phase 2 integration & export | 1 | P0 | 📝 Planned |

---

## Feature 83.1: T2-RAGBench Table Processor (5 SP)

### Description
Process financial tables from T2-RAGBench with structure preservation.

### Challenge

```yaml
Problem:
  - Raw table data loses structure in plain text
  - Financial tables have implicit header relationships
  - Cell references (Row 1, Column A) need context
  - Some answers require numerical computation

Solution:
  - Convert tables to structured markdown format
  - Preserve column headers explicitly
  - Add table caption as context
  - Include row/column metadata
```

### Dataset Schema (T2-RAGBench FinQA)

```python
# Original T2-RAGBench record
{
    "question": "What was the percentage change in revenue from 2019 to 2020?",
    "program_answer": "15.2",
    "original_answer": "15.2%",
    "context": "The following table shows...",
    "table": [
        ["Year", "Revenue", "Profit"],
        ["2019", "$10.5B", "$1.2B"],
        ["2020", "$12.1B", "$1.8B"]
    ],
    "file_name": "annual_report_2020.pdf",
    "page_number": 42
}
```

### Implementation

```python
# scripts/ragas_benchmark/adapters/t2ragbench.py

class T2RAGBenchAdapter(DatasetAdapter):
    """Adapter for T2-RAGBench (FinQA, TAT-QA subsets)."""

    def get_doc_type(self) -> str:
        return "table"

    def adapt(self, record: Dict) -> NormalizedSample:
        # Combine context + table + caption
        context_text = record.get("context", "")
        table_md = self.table_to_markdown(record.get("table", []))
        caption = record.get("table_caption", "")

        combined_context = f"{context_text}\n\n{table_md}"
        if caption:
            combined_context += f"\n\nTable Caption: {caption}"

        # Use program_answer (computed) over original_answer (may have units)
        ground_truth = str(record.get("program_answer") or record.get("original_answer", ""))

        return NormalizedSample(
            id=self._generate_id(record),
            question=record["question"],
            ground_truth=ground_truth,
            contexts=[combined_context],
            doc_type="table",
            question_type=self._classify_table_question(record),
            difficulty=self._assign_difficulty(record),
            source_dataset="t2-ragbench",
            metadata={
                "table_rows": len(record.get("table", [])),
                "table_cols": len(record.get("table", [[]])[0]) if record.get("table") else 0,
                "file_name": record.get("file_name"),
                "page_number": record.get("page_number"),
                "has_computation": self._requires_computation(record),
            }
        )

    def table_to_markdown(self, table_data: List[List[str]]) -> str:
        """
        Convert table to markdown with headers.

        Example output:
        | Year | Revenue | Profit |
        |------|---------|--------|
        | 2019 | $10.5B  | $1.2B  |
        | 2020 | $12.1B  | $1.8B  |
        """
        if not table_data:
            return ""

        # First row is header
        header = table_data[0]
        separator = ["-" * max(3, len(str(h))) for h in header]
        rows = table_data[1:]

        lines = [
            "| " + " | ".join(str(h) for h in header) + " |",
            "| " + " | ".join(separator) + " |",
        ]
        for row in rows:
            lines.append("| " + " | ".join(str(c) for c in row) + " |")

        return "\n".join(lines)

    def _classify_table_question(self, record: Dict) -> str:
        """Classify table question type."""
        question = record["question"].lower()

        if any(w in question for w in ["percentage", "change", "growth", "increase", "decrease"]):
            return "numeric"
        if any(w in question for w in ["compare", "difference", "vs", "versus"]):
            return "comparison"
        if any(w in question for w in ["what is", "how much", "how many"]):
            return "lookup"
        return "lookup"

    def _requires_computation(self, record: Dict) -> bool:
        """Check if answer requires numerical computation."""
        question = record["question"].lower()
        return any(w in question for w in [
            "percentage", "ratio", "average", "total", "sum",
            "change", "growth", "difference"
        ])
```

### Target Quota

| Category | Count |
|----------|-------|
| table (T2-RAGBench) | 100 |
| **Question Types:** | |
| - numeric | 50 |
| - lookup | 25 |
| - comparison | 20 |
| - policy | 5 |

### Acceptance Criteria

- [ ] 100 table samples extracted
- [ ] Table structure preserved in markdown
- [ ] Numeric values correctly extracted
- [ ] Question types classified
- [ ] Unit tests for table conversion

### Test Cases

```python
def test_table_to_markdown_basic():
    """Test basic table conversion."""
    adapter = T2RAGBenchAdapter()
    table = [
        ["Year", "Revenue"],
        ["2020", "$10B"],
    ]
    md = adapter.table_to_markdown(table)
    assert "| Year | Revenue |" in md
    assert "| 2020 | $10B |" in md

def test_table_question_classification():
    """Test table question type classification."""
    adapter = T2RAGBenchAdapter()
    record = {"question": "What was the percentage change in revenue?"}
    assert adapter._classify_table_question(record) == "numeric"
```

---

## Feature 83.2: CodeRepoQA Code Extractor (5 SP)

### Description
Process code repository Q&A with syntax-aware handling.

### Challenge

```yaml
Problem:
  - Code snippets contain special characters
  - Language context matters for understanding
  - Function/class boundaries need preservation
  - Indentation is semantically meaningful

Solution:
  - Preserve code blocks with language hints
  - Include file path as context
  - Use markdown code fences
  - Add function/class metadata
```

### Dataset Schema (CodeRepoQA)

```python
# Original CodeRepoQA record (approximate schema)
{
    "question": "What does the authenticate function return?",
    "answer": "Returns a JWT token if credentials are valid, None otherwise.",
    "code": "def authenticate(username, password):\n    ...",
    "file_path": "src/auth/login.py",
    "repo": "example/webapp",
    "language": "python"
}
```

### Implementation

```python
# scripts/ragas_benchmark/adapters/coderepoqa.py

class CodeRepoQAAdapter(DatasetAdapter):
    """Adapter for CodeRepoQA dataset."""

    LANGUAGE_HINTS = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".c": "c",
        ".rb": "ruby",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".json": "json",
        ".toml": "toml",
    }

    def get_doc_type(self) -> str:
        return "code_config"

    def adapt(self, record: Dict) -> NormalizedSample:
        code_context = self.format_code_context(record)

        return NormalizedSample(
            id=self._generate_id(record),
            question=record["question"],
            ground_truth=record.get("answer", ""),
            contexts=[code_context],
            doc_type="code_config",
            question_type=self._classify_code_question(record),
            difficulty=self._assign_difficulty(record),
            source_dataset="coderepoqa",
            metadata={
                "repo": record.get("repo"),
                "file_path": record.get("file_path"),
                "language": self.detect_language(record),
                "code_length": len(record.get("code", "")),
            }
        )

    def format_code_context(self, record: Dict) -> str:
        """
        Format code with language hint and path.

        Example output:
        ```python
        # File: src/auth/login.py
        # Repository: example/webapp

        def authenticate(username, password):
            ...
        ```
        """
        language = self.detect_language(record)
        code = record.get("code", record.get("snippet", ""))
        file_path = record.get("file_path", "unknown")
        repo = record.get("repo", "")

        header_lines = [f"# File: {file_path}"]
        if repo:
            header_lines.append(f"# Repository: {repo}")
        header_lines.append("")  # Empty line before code

        header = "\n".join(header_lines)
        return f"```{language}\n{header}{code}\n```"

    def detect_language(self, record: Dict) -> str:
        """Detect programming language from file path or explicit field."""
        # Check explicit language field
        if "language" in record:
            return record["language"].lower()

        # Infer from file path
        file_path = record.get("file_path", "")
        for ext, lang in self.LANGUAGE_HINTS.items():
            if file_path.endswith(ext):
                return lang

        return "text"  # Default fallback

    def _classify_code_question(self, record: Dict) -> str:
        """Classify code question type."""
        question = record["question"].lower()

        if any(w in question for w in ["how to", "how do", "implement", "create"]):
            return "howto"
        if any(w in question for w in ["what does", "what is", "explain", "describe"]):
            return "definition"
        if any(w in question for w in ["where", "which file", "find"]):
            return "lookup"
        if any(w in question for w in ["error", "bug", "fix", "issue"]):
            return "entity"  # Error/bug as "entity"
        return "lookup"
```

### Target Quota

| Category | Count |
|----------|-------|
| code_config (CodeRepoQA) | 100 |
| **Question Types:** | |
| - howto | 40 |
| - definition | 30 |
| - lookup | 20 |
| - entity (errors) | 10 |

### Acceptance Criteria

- [ ] 100 code samples extracted
- [ ] Code syntax preserved with fences
- [ ] Language correctly detected
- [ ] File paths included
- [ ] Unit tests for code formatting

---

## Feature 83.3: Statistical Rigor Package (2 SP)

### Description
Add statistical functions for publication-ready metrics.

### Implementation

```python
# scripts/ragas_benchmark/statistics.py

import numpy as np
from scipy import stats
from typing import List, Dict, Tuple

def compute_confidence_interval(
    scores: List[float],
    confidence: float = 0.95,
    method: str = "bootstrap"
) -> Tuple[float, float, float]:
    """
    Compute confidence interval for metric scores.

    Args:
        scores: List of metric scores
        confidence: Confidence level (default 95%)
        method: "bootstrap" or "normal"

    Returns:
        Tuple of (mean, lower_bound, upper_bound)
    """
    scores = np.array(scores)
    mean = np.mean(scores)

    if method == "bootstrap":
        # Bootstrap CI (more robust for non-normal distributions)
        n_bootstrap = 10000
        bootstrap_means = []
        for _ in range(n_bootstrap):
            sample = np.random.choice(scores, size=len(scores), replace=True)
            bootstrap_means.append(np.mean(sample))

        alpha = 1 - confidence
        lower = np.percentile(bootstrap_means, 100 * alpha / 2)
        upper = np.percentile(bootstrap_means, 100 * (1 - alpha / 2))
    else:
        # Normal approximation CI
        se = stats.sem(scores)
        h = se * stats.t.ppf((1 + confidence) / 2, len(scores) - 1)
        lower = mean - h
        upper = mean + h

    return mean, lower, upper


def significance_test(
    group_a: List[float],
    group_b: List[float],
    test: str = "mcnemar"
) -> Dict[str, float]:
    """
    Statistical significance test for paired comparisons.

    Args:
        group_a: Scores from condition A
        group_b: Scores from condition B
        test: "mcnemar" for binary, "wilcoxon" for continuous

    Returns:
        Dict with p_value, effect_size, significant
    """
    a = np.array(group_a)
    b = np.array(group_b)

    if test == "wilcoxon":
        # Wilcoxon signed-rank test (paired, non-parametric)
        stat, p_value = stats.wilcoxon(a, b)
    else:
        # For continuous scores, use paired t-test
        stat, p_value = stats.ttest_rel(a, b)

    # Cohen's d effect size
    diff = a - b
    cohens_d = np.mean(diff) / np.std(diff, ddof=1)

    return {
        "statistic": float(stat),
        "p_value": float(p_value),
        "effect_size": float(cohens_d),
        "significant": p_value < 0.05,
        "significant_bonferroni": p_value < (0.05 / 7),  # 7 comparisons
    }


def power_analysis(
    n: int,
    effect_size: float = 0.3,
    alpha: float = 0.05
) -> float:
    """
    Post-hoc power calculation.

    Args:
        n: Sample size
        effect_size: Expected Cohen's d
        alpha: Significance level

    Returns:
        Statistical power (0-1)
    """
    from scipy.stats import norm

    # Two-tailed test
    z_alpha = norm.ppf(1 - alpha / 2)
    z_beta = effect_size * np.sqrt(n) - z_alpha
    power = norm.cdf(z_beta)

    return float(power)


def compute_all_statistics(
    results: Dict[str, List[float]],
    mode_comparisons: List[Tuple[str, str]] = None
) -> Dict:
    """
    Compute all statistics for RAGAS results.

    Args:
        results: Dict mapping mode -> list of scores per metric
        mode_comparisons: List of (mode_a, mode_b) pairs to compare

    Returns:
        Comprehensive statistics dict
    """
    if mode_comparisons is None:
        mode_comparisons = [
            ("hybrid", "vector"),
            ("hybrid", "graph"),
            ("vector", "graph"),
        ]

    stats_output = {
        "per_mode": {},
        "comparisons": {},
        "power_analysis": {},
    }

    # Per-mode statistics
    for mode, scores in results.items():
        mean, lower, upper = compute_confidence_interval(scores)
        stats_output["per_mode"][mode] = {
            "mean": mean,
            "ci_lower": lower,
            "ci_upper": upper,
            "n": len(scores),
            "std": float(np.std(scores)),
        }

    # Mode comparisons
    for mode_a, mode_b in mode_comparisons:
        if mode_a in results and mode_b in results:
            comparison = significance_test(results[mode_a], results[mode_b])
            stats_output["comparisons"][f"{mode_a}_vs_{mode_b}"] = comparison

    # Power analysis
    n = len(next(iter(results.values())))
    for effect_size in [0.2, 0.3, 0.5]:
        power = power_analysis(n, effect_size)
        stats_output["power_analysis"][f"d={effect_size}"] = power

    return stats_output
```

### Integration with Evaluation

```python
# Enhanced output format in run_ragas_evaluation.py

{
    "metrics": {
        "faithfulness": {
            "mean": 0.72,
            "ci_95": [0.68, 0.76],
            "n": 800,
            "std": 0.15
        },
        "context_precision": {
            "mean": 0.85,
            "ci_95": [0.82, 0.88],
            "n": 800,
            "std": 0.12
        }
    },
    "comparisons": {
        "hybrid_vs_vector": {
            "p_value": 0.003,
            "effect_size": 0.45,
            "significant": true,
            "significant_bonferroni": true
        }
    },
    "power_analysis": {
        "d=0.2": 0.65,
        "d=0.3": 0.89,
        "d=0.5": 0.99
    }
}
```

### Acceptance Criteria

- [ ] Bootstrap CI computed for all metrics
- [ ] Significance tests for mode comparisons
- [ ] Effect sizes (Cohen's d) reported
- [ ] Power analysis included
- [ ] Unit tests for statistical functions

---

## Feature 83.4: Phase 2 Integration & Export (1 SP)

### Description
Combine Phase 1 and Phase 2 datasets, generate combined export.

### Combined Dataset Structure

```
Phase 1 (Sprint 82): 500 samples
  - clean_text: 350
  - log_ticket: 150

Phase 2 (Sprint 83): 300 samples
  - table: 100
  - code_config: 100
  - clean_text: 100 (additional)

Combined: 800 samples
  - clean_text: 450
  - log_ticket: 150
  - table: 100
  - code_config: 100
```

### Output Files

```
data/evaluation/
├── ragas_phase1_500.jsonl        # Phase 1 only
├── ragas_phase1_manifest.csv
├── ragas_phase2_300.jsonl        # Phase 2 only (NEW)
├── ragas_phase2_manifest.csv     # (NEW)
├── ragas_combined_800.jsonl      # Combined (NEW)
└── ragas_manifest_800.csv        # Combined manifest (NEW)
```

### Build Script

```bash
# Build Phase 2 dataset
poetry run python scripts/ragas_benchmark/build_phase2.py \
  --output data/evaluation/ragas_phase2_300.jsonl \
  --manifest data/evaluation/ragas_phase2_manifest.csv \
  --seed 42

# Combine Phase 1 + Phase 2
poetry run python scripts/ragas_benchmark/combine_phases.py \
  --phase1 data/evaluation/ragas_phase1_500.jsonl \
  --phase2 data/evaluation/ragas_phase2_300.jsonl \
  --output data/evaluation/ragas_combined_800.jsonl \
  --manifest data/evaluation/ragas_manifest_800.csv
```

### Acceptance Criteria

- [ ] 800 total samples in combined file
- [ ] All 4 doc_types represented
- [ ] Manifest updated with all samples
- [ ] No duplicate IDs across phases

---

## Deliverables

| Artifact | Location | Description |
|----------|----------|-------------|
| T2-RAGBench adapter | `scripts/ragas_benchmark/adapters/t2ragbench.py` | Table processing |
| CodeRepoQA adapter | `scripts/ragas_benchmark/adapters/coderepoqa.py` | Code processing |
| Statistics module | `scripts/ragas_benchmark/statistics.py` | Statistical functions |
| Phase 2 dataset | `data/evaluation/ragas_phase2_300.jsonl` | 300 samples |
| Combined dataset | `data/evaluation/ragas_combined_800.jsonl` | 800 samples |
| Unit tests | `tests/ragas_benchmark/test_phase2.py` | Phase 2 tests |

---

## Success Criteria

- [ ] 800 total samples (500 + 300)
- [ ] Table and code doc_types functional
- [ ] Statistical rigor package integrated
- [ ] All unit tests passing
- [ ] Documentation updated

---

## Dependencies

### Sprint 82 Prerequisites

- [ ] Dataset loader infrastructure (82.1)
- [ ] Stratified sampling engine (82.2)
- [ ] JSONL export format (82.4)

### Python Packages

```toml
# Additional dependencies
scipy = "^1.11.0"  # Statistical functions
```

---

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| T2-RAGBench schema differs | Medium | Medium | Adapter flexibility, fallbacks |
| CodeRepoQA unavailable | Low | High | Alternative: GitHub Code Search |
| Table markdown parsing issues | Medium | Low | Unit tests, manual validation |

---

## References

- [ADR-048: RAGAS 1000-Sample Benchmark Strategy](../adr/ADR-048-ragas-1000-sample-benchmark.md)
- [Sprint 82 Plan](SPRINT_82_PLAN.md)
- [T2-RAGBench Paper](https://arxiv.org/abs/2407.11170)
- [CodeRepoQA Dataset](https://huggingface.co/datasets/code-repo-qa/CodeRepoQA)
