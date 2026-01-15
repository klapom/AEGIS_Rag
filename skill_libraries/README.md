# Skill Libraries & Bundles

This directory contains reusable skill packages organized into libraries and pre-configured bundles.

**Sprint 95 Feature 95.2: Skill Libraries & Bundles (8 SP)**

## Structure

```
skill_libraries/
├── core/                     # Core library (fundamental skills)
│   ├── LIBRARY.yaml         # Library manifest
│   ├── retrieval/           # Vector/Graph/BM25 retrieval skill
│   ├── synthesis/           # Summarization skill
│   └── reflection/          # Self-critique skill
│
├── research/                 # Research library
│   ├── LIBRARY.yaml         # Library manifest
│   ├── web_search/          # Web search skill
│   ├── academic/            # Academic search skill
│   └── fact_check/          # Fact verification skill
│
├── analysis/                 # Analysis library
│   ├── LIBRARY.yaml         # Library manifest
│   ├── statistics/          # Statistical analysis skill
│   ├── data_viz/            # Data visualization skill
│   └── comparison/          # Comparison skill
│
└── bundles/                  # Pre-configured bundles
    ├── research_assistant/
    │   └── BUNDLE.yaml      # Research workflow bundle
    ├── data_analyst/
    │   └── BUNDLE.yaml      # Data analysis bundle
    └── code_reviewer/
        └── BUNDLE.yaml      # Code review bundle
```

## Libraries

### Core Library
**Purpose**: Fundamental skills used across all workflows

**Skills**:
- `retrieval`: Vector/Graph/BM25 retrieval
- `synthesis`: Summarization and aggregation
- `reflection`: Self-critique and quality checking

**Use Cases**: Base functionality for all RAG operations

### Research Library
**Purpose**: Research and information gathering skills

**Skills**:
- `web_search`: Multi-engine web search
- `academic`: Academic paper search
- `fact_check`: Fact verification

**Use Cases**: Web research, academic queries, fact-checking

### Analysis Library
**Purpose**: Data analysis and visualization skills

**Skills**:
- `statistics`: Statistical analysis
- `data_viz`: Chart and graph generation
- `comparison`: Comparative analysis

**Use Cases**: Data exploration, trend analysis, reporting

## Bundles

### Research Assistant Bundle
**Description**: Complete research workflow with web search and fact-checking

**Includes**:
- core/retrieval
- core/synthesis
- core/reflection
- research/web_search
- research/academic
- research/fact_check

**Context Budget**: 8000 tokens

**Auto-activate**: retrieval, synthesis

**Use Cases**:
- Comprehensive research queries
- Academic paper search
- Fact verification
- Web-based information gathering

### Data Analyst Bundle
**Description**: Data analysis and visualization workflow

**Includes**:
- core/retrieval
- analysis/statistics
- analysis/data_viz
- analysis/comparison
- core/synthesis

**Context Budget**: 6000 tokens

**Auto-activate**: statistics, synthesis

**Use Cases**:
- Statistical data analysis
- Data visualization
- Comparative analysis
- Trend identification

### Code Reviewer Bundle
**Description**: Code review and quality analysis

**Includes**:
- coding/review
- coding/security
- coding/performance
- core/reflection
- core/synthesis

**Context Budget**: 7000 tokens

**Auto-activate**: review, security

**Use Cases**:
- Code review automation
- Security vulnerability detection
- Performance optimization
- Code quality assessment

## Usage

### Python API

```python
from pathlib import Path
from src.agents.skills import SkillLibraryManager, SkillLifecycleManager

# Initialize managers
lifecycle = SkillLifecycleManager(skills_dir=Path("skills"))
library = SkillLibraryManager(
    libraries_dir=Path("skill_libraries"),
    skill_manager=lifecycle
)

# Discover libraries and bundles
library.discover_libraries()

# Load a bundle
loaded_skills = await library.load_bundle("research_assistant")
# Returns: ['retrieval', 'synthesis', 'web_search', 'fact_check', 'academic', 'reflection']

# Search for skills by capability
skills = library.search_skills(
    query="web",
    capabilities=["search"]
)

# Create custom bundle
custom = library.create_bundle(
    name="my_workflow",
    skills=["core/retrieval", "research/web_search"],
    context_budget=5000,
    auto_activate=["retrieval"]
)

# Load custom bundle
await library.load_bundle("my_workflow")
```

## Creating New Libraries

1. Create library directory: `skill_libraries/my_library/`
2. Add `LIBRARY.yaml`:

```yaml
name: my_library
version: "1.0.0"
description: My custom skill library
skills:
  - skill1
  - skill2
dependencies:
  - package>=1.0.0
```

3. Add skill directories with `SKILL.md` files

## Creating New Bundles

1. Create bundle directory: `skill_libraries/bundles/my_bundle/`
2. Add `BUNDLE.yaml`:

```yaml
name: my_bundle
version: "1.0.0"
description: My custom workflow bundle
skills:
  - core/retrieval
  - my_library/skill1
context_budget: 6000
auto_activate:
  - retrieval
dependencies:
  - package>=1.0.0
```

## Bundle Definition Reference

```yaml
name: bundle_name              # Unique bundle identifier
version: "1.0.0"              # Semantic version
description: "Description"    # Human-readable description
skills:                       # List of skills (library/skill format)
  - core/retrieval
  - research/web_search
context_budget: 8000         # Total context budget in tokens
auto_activate:               # Skills to automatically activate
  - retrieval
  - synthesis
triggers:                    # Intent patterns that trigger this bundle
  - "research"
  - "find information"
permissions:                 # Required permissions
  tools:
    - browser
    - web_fetch
  network: true
  filesystem: false
dependencies:                # External package dependencies
  - playwright>=1.40.0
  - requests>=2.28.0
metadata:                    # Additional metadata
  author: "Author Name"
  category: "research"
  tags:
    - research
    - web
```

## Integration with LangGraph

Bundles integrate seamlessly with LangGraph agent workflows:

```python
from langgraph.graph import StateGraph, MessagesState

# Load bundle for agent context
await library.load_bundle("research_assistant")

# Active skills are automatically injected into agent context
class AgentState(MessagesState):
    active_bundle: str
    available_skills: list[str]

# Skills can be activated/deactivated per agent node
def research_node(state):
    # Bundle skills are available here
    return {"messages": [...]}
```

## See Also

- [Sprint 95 Plan](../../docs/sprints/SPRINT_95_PLAN.md)
- [ADR-049: Agentic Framework Architecture](../../docs/adr/ADR-049-agentic-framework-architecture.md)
- [Anthropic Skills Repository](https://github.com/anthropics/skills)
- [Skill Lifecycle Management](../../src/agents/skills/lifecycle.py)
- [Skill Tool Mapping](../../src/agents/tools/mapping.py)
