# Skill Bundles

**Sprint 95, Feature 95.3: Standard Skill Bundles**

Pre-configured skill bundles for common use cases in the AegisRAG system.

## Overview

A **skill bundle** is a collection of related skills with shared configuration, dependencies, and usage patterns. Bundles simplify skill deployment by providing ready-to-use configurations for common workflows.

## Available Bundles

### 1. Research Bundle

**Use Case:** Research and information gathering

**Skills (4):**
- `web_search`: Search external sources (Google, Bing)
- `retrieval`: Vector + sparse hybrid retrieval (Qdrant, BGE-M3)
- `graph_query`: Knowledge graph traversal (Neo4j, 2-hop)
- `citation`: Citation management (APA style)

**Configuration:**
- Context Budget: 8,000 tokens
- Auto-activated: `retrieval`, `citation`
- Priority: Balanced

**Triggers:**
- "research", "find information", "investigate"
- "look up", "search for", "gather data"
- "fact check", "verify sources"

**Performance:**
- Avg Latency: 850ms
- P95 Latency: 1,500ms
- Max Concurrent: 3

**Example:**
```python
from src.agents.skills.bundle_installer import install_bundle

# Install bundle
report = install_bundle("research_bundle")
print(report.summary)
# Output: "Successfully installed 4 skills: web_search, retrieval, graph_query, citation"
```

---

### 2. Analysis Bundle

**Use Case:** Data analysis and validation

**Skills (4):**
- `validation`: Data quality checking (nulls, types, ranges)
- `classification`: LLM-based categorization (intent, sentiment)
- `comparison`: Semantic comparison (datasets, documents)
- `statistical_analysis`: Statistical computations (t-test, chi-square)

**Configuration:**
- Context Budget: 6,000 tokens
- Auto-activated: `validation`, `statistical_analysis`
- Priority: Quality

**Triggers:**
- "analyze", "validate", "compare"
- "classify", "statistics", "data quality"
- "check data", "find patterns"

**Performance:**
- Avg Latency: 450ms
- P95 Latency: 900ms
- Max Concurrent: 4

**Example:**
```python
report = install_bundle("analysis_bundle")
# Analyze customer feedback sentiment, validate data quality
```

---

### 3. Synthesis Bundle

**Use Case:** Content synthesis and formatting

**Skills (4):**
- `summarize`: Multi-document summarization (extractive/abstractive)
- `citation`: Citation management (APA, MLA, Chicago, IEEE)
- `format`: Content formatting (markdown, HTML, LaTeX)
- `markdown_export`: Export to formatted markdown

**Configuration:**
- Context Budget: 7,000 tokens
- Auto-activated: `citation`, `format`
- Priority: Quality

**Triggers:**
- "summarize", "synthesize", "write report"
- "create document", "format text"
- "export to markdown", "generate summary"

**Performance:**
- Avg Latency: 650ms
- P95 Latency: 1,200ms
- Max Concurrent: 3

**Example:**
```python
report = install_bundle("synthesis_bundle")
# Generate literature review from 5 research papers
```

---

### 4. Development Bundle

**Use Case:** Software development workflows

**Skills (4):**
- `code_generation`: Generate production code with type hints
- `code_review`: Quality and security review
- `testing`: Test generation and execution (pytest, jest)
- `debugging`: Debug assistance with fix suggestions

**Configuration:**
- Context Budget: 10,000 tokens
- Auto-activated: `code_review`, `testing`
- Priority: Quality

**Triggers:**
- "write code", "generate function", "create class"
- "review code", "debug error", "fix bug"
- "write tests", "refactor code"

**Performance:**
- Avg Latency: 1,200ms
- P95 Latency: 2,500ms
- Max Concurrent: 2 (resource-intensive)

**Example:**
```python
report = install_bundle("development_bundle")
# Implement authentication endpoint with tests and review
```

---

### 5. Enterprise Bundle

**Use Case:** Full AegisRAG stack deployment

**Skills (23):**
- **Research:** web_search, retrieval, graph_query, citation
- **Analysis:** validation, classification, comparison, statistical_analysis
- **Synthesis:** summarize, format, markdown_export
- **Development:** code_generation, code_review, testing, debugging
- **Enterprise:** compliance, audit, reporting, dashboard, memory_retrieval, context_management, mcp_server, tool_execution

**Configuration:**
- Context Budget: 150,000 tokens
- Auto-activated: `retrieval`, `citation`, `compliance`, `audit`, `memory_retrieval`
- Priority: Balanced

**Compliance:**
- GDPR, SOC2, HIPAA support
- PII detection and audit logging
- 90-day retention policy

**Performance:**
- Avg Latency: 2,000ms
- P95 Latency: 5,000ms
- Max Concurrent: 10
- Target Throughput: 50 QPS

**Resource Requirements:**
- Memory: 8 GB
- CPU: 4 cores
- GPU: Optional (for embeddings)
- Disk: 100 GB

**Example:**
```python
report = install_bundle("enterprise_bundle")
# Deploy full production RAG with compliance and monitoring
```

---

## Installation

### Python API

```python
from src.agents.skills.bundle_installer import (
    install_bundle,
    get_bundle_status,
    list_available_bundles
)

# List available bundles
bundles = list_available_bundles()
print(bundles)
# Output: ['research_bundle', 'analysis_bundle', 'synthesis_bundle', 'development_bundle', 'enterprise_bundle']

# Install a bundle
report = install_bundle("research_bundle")

if report.success:
    print(f"✓ {report.summary}")
    print(f"Duration: {report.duration_seconds:.2f}s")
else:
    print(f"✗ {report.summary}")

# Check warnings
if report.warnings:
    for warning in report.warnings:
        print(f"Warning: {warning}")

# Check missing dependencies
if report.missing_dependencies:
    print("Missing dependencies:")
    for dep in report.missing_dependencies:
        print(f"  - {dep}")

# Get bundle status
status = get_bundle_status("research_bundle")
print(f"Installed: {status.installed}")
print(f"Version: {status.version}")
print(f"Skills: {', '.join(status.installed_skills)}")
```

### CLI (Coming Soon)

```bash
# List bundles
aegis-skills bundle list

# Install bundle
aegis-skills bundle install research_bundle

# Check status
aegis-skills bundle status research_bundle
```

---

## Bundle Structure

Each bundle is defined in a YAML file with the following structure:

```yaml
id: bundle_id
name: Bundle Name
version: 1.0.0
description: Bundle description

# Skills in bundle
skills:
  - name: skill_name
    version: "^1.0.0"
    required: true
    description: Skill description
    config:
      # Skill-specific configuration
      key: value

# Bundle configuration
context_budget: 8000
priority: balanced  # balanced, speed, quality

# Auto-activation
auto_activate:
  - skill1
  - skill2

# Natural language triggers
triggers:
  - trigger1
  - trigger2

# Required permissions
permissions:
  tools:
    - tool1
  data:
    - data_permission1
  llm:
    - llm_permission1

# External dependencies
dependencies:
  system:
    - service1 >= 1.0.0
  python:
    - package1 >= 1.0.0

# Installation order
installation_order:
  - skill1
  - skill2
  - skill3

# Bundle metadata
metadata:
  category: research
  use_case: academic_research
  complexity: medium
  maturity: stable
```

---

## Examples

### Running Examples

Each bundle has an example script in `examples/bundles/`:

```bash
# Research bundle example
python examples/bundles/research_bundle_example.py

# Analysis bundle example
python examples/bundles/analysis_bundle_example.py

# Synthesis bundle example
python examples/bundles/synthesis_bundle_example.py

# Development bundle example
python examples/bundles/development_bundle_example.py

# Enterprise bundle example
python examples/bundles/enterprise_bundle_example.py
```

### Custom Bundle

You can create a custom bundle by adding a new YAML file:

```yaml
# src/agents/skills/bundles/custom_bundle.yaml
id: custom_bundle
name: Custom Bundle
version: 1.0.0
description: My custom skill bundle

skills:
  - name: skill1
    version: "^1.0.0"
    required: true
    config:
      key: value

  - name: skill2
    version: "^1.0.0"
    required: true
    config:
      key: value

context_budget: 10000
installation_order:
  - skill1
  - skill2
```

Then install it:

```python
report = install_bundle("custom_bundle")
```

---

## Bundle Selection Guide

| Use Case | Recommended Bundle | Skills | Context Budget |
|----------|-------------------|--------|----------------|
| Academic research | Research Bundle | 4 | 8,000 |
| Data analysis | Analysis Bundle | 4 | 6,000 |
| Report writing | Synthesis Bundle | 4 | 7,000 |
| Code development | Development Bundle | 4 | 10,000 |
| Production deployment | Enterprise Bundle | 23 | 150,000 |

---

## Dependencies

### Research Bundle
- **System:** Qdrant >= 1.11.0, Neo4j >= 5.0.0
- **Python:** langchain >= 0.1.0, requests >= 2.31.0

### Analysis Bundle
- **Python:** numpy >= 1.24.0, pandas >= 2.0.0, scipy >= 1.10.0, scikit-learn >= 1.3.0

### Synthesis Bundle
- **Python:** markdown >= 3.5.0, pyyaml >= 6.0.0, python-docx >= 1.1.0

### Development Bundle
- **Python:** pytest >= 7.4.0, mypy >= 1.7.0, ruff >= 0.1.0, black >= 23.11.0
- **System:** git >= 2.40.0

### Enterprise Bundle
- **System:** Qdrant >= 1.11.0, Neo4j >= 5.0.0, Redis >= 7.0.0, Ollama >= 0.1.0, Postgres >= 14.0
- **Python:** All dependencies from other bundles

---

## Troubleshooting

### Missing Dependencies

If you see missing dependency warnings:

```python
report = install_bundle("research_bundle")
if report.missing_dependencies:
    print("Missing:")
    for dep in report.missing_dependencies:
        print(f"  {dep}")
```

Install missing Python packages:
```bash
poetry install
```

Check system services:
```bash
docker compose up -d  # Start Qdrant, Neo4j, Redis
```

### Bundle Already Installed

To reinstall a bundle:

```python
report = install_bundle("research_bundle", force=True)
```

### Skill Installation Failed

Check the installation report:

```python
report = install_bundle("research_bundle")
if not report.success:
    print(f"Failed skills: {report.failed_skills}")
```

---

## Performance Tuning

### Context Budget

Adjust context budget based on your use case:

```yaml
# High-quality, comprehensive results
context_budget: 20000

# Fast, concise results
context_budget: 4000
```

### Priority

Set priority to optimize for speed or quality:

```yaml
# Speed-optimized
priority: speed

# Quality-optimized
priority: quality

# Balanced (default)
priority: balanced
```

### Max Concurrent

Adjust max concurrent skills based on resources:

```yaml
# High concurrency (requires more resources)
max_concurrent: 10

# Low concurrency (resource-constrained)
max_concurrent: 2
```

---

## Architecture

### Bundle Installer

- **Location:** `src/agents/skills/bundle_installer.py`
- **Class:** `BundleInstaller`
- **Singleton:** `get_bundle_installer()`

### Bundle Registry

- **Location:** `src/agents/skills/bundles/`
- **Format:** YAML files (`{bundle_id}.yaml`)

### Installation Process

1. **Load:** Parse bundle YAML
2. **Validate:** Check dependencies
3. **Install:** Install skills in order
4. **Activate:** Auto-activate specified skills
5. **Report:** Generate installation report

---

## Testing

Unit tests are located in `tests/unit/agents/skills/test_bundles.py`.

Run tests:
```bash
pytest tests/unit/agents/skills/test_bundles.py -v
```

---

## See Also

- **Skill Registry:** `src/agents/skills/registry.py`
- **Sprint Plan:** `docs/sprints/SPRINT_95_PLAN.md`
- **Examples:** `examples/bundles/`

---

## Contributing

To add a new bundle:

1. Create YAML file in `src/agents/skills/bundles/{bundle_id}.yaml`
2. Define skills, configuration, and dependencies
3. Create example script in `examples/bundles/{bundle_id}_example.py`
4. Add tests in `tests/unit/agents/skills/test_bundles.py`
5. Update this README

---

**Last Updated:** 2026-01-15
**Sprint:** 95
**Feature:** 95.3 - Standard Skill Bundles
**Author:** AegisRAG Team
