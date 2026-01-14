# AegisRAG Agent Skills

This directory contains **Agent Skills** following the Anthropic Agent Skills standard. Skills are modular capability containers that can be dynamically loaded and activated based on intent.

## What are Agent Skills?

Agent Skills are folders of instructions, scripts, and resources that:
- **Load on-demand** based on query intent (token-efficient)
- **Package expertise** as reusable components
- **Follow open standards** for cross-platform compatibility
- **Enable governance** with per-skill permissions

## Directory Structure

```
skills/
├── README.md                  # This file
├── retrieval/                 # Vector and graph retrieval
│   ├── SKILL.md              # Metadata and instructions
│   ├── config.yaml           # Configuration
│   └── prompts/              # Prompt templates
├── reflection/                # Self-critique and validation
│   ├── SKILL.md
│   ├── config.yaml
│   └── prompts/
├── synthesis/                 # Answer generation
│   ├── SKILL.md
│   ├── config.yaml
│   └── prompts/
└── hallucination_monitor/     # Hallucination detection (auto-active)
    ├── SKILL.md
    ├── config.yaml
    └── prompts/
```

## Available Skills

| Skill | Version | Description | Triggers |
|-------|---------|-------------|----------|
| `retrieval` | 1.0.0 | BGE-M3 hybrid search + LightRAG graph reasoning | search, find, lookup |
| `reflection` | 1.0.0 | Self-critique and iterative improvement (Reflexion) | validate, verify, check |
| `synthesis` | 1.0.0 | Answer generation and summarization | answer, summarize, explain |
| `hallucination_monitor` | 1.0.0 | Active hallucination detection (auto-active) | (auto) |

## Creating a New Skill

### 1. Use the Template

Start with the SKILL.md template:
```bash
cp docs/skills/SKILL_TEMPLATE.md skills/my_skill/SKILL.md
```

### 2. Fill in Metadata

Edit the YAML frontmatter:
```yaml
---
name: my_skill
version: 1.0.0
description: Brief description
author: Your Name
triggers:
  - keyword1
  - keyword2
dependencies:
  - other_skill
permissions:
  - read_documents
---
```

### 3. Write Instructions

Add detailed instructions for the agent in markdown format after the frontmatter.

### 4. Add Configuration

Create `config.yaml` with skill-specific settings:
```yaml
# my_skill configuration
settings:
  option1: value1
  option2: value2
```

### 5. Add Prompts (Optional)

Create prompt templates in `prompts/`:
```
skills/my_skill/prompts/
├── template1.txt
└── template2.txt
```

Use `{variable}` syntax for placeholders.

### 6. Add Scripts (Optional)

Create utility scripts in `scripts/`:
```
skills/my_skill/scripts/
├── helper.py
└── validator.py
```

Each script should have a `main()` or `run()` function as the entry point.

## Using Skills

### Discovery

The Skill Registry (`src/agents/skills/registry.py`) automatically discovers all skills:
```python
from src.agents.skills.registry import get_skill_registry

registry = get_skill_registry()
available = registry.list_available()
# ['retrieval', 'reflection', 'synthesis', 'hallucination_monitor']
```

### Loading

Load a skill into memory:
```python
skill = registry.load("retrieval")
print(skill.metadata.description)
# "Vector and graph retrieval using BGE-M3 hybrid search and LightRAG entity reasoning"
```

### Activation

Activate a skill to inject its instructions into the agent's context:
```python
instructions = registry.activate("retrieval")
# Returns: Full skill instructions from SKILL.md
```

### Intent Matching

Match skills based on user intent:
```python
query = "Find documents about neural networks"
matches = registry.match_intent(query, similarity_threshold=0.75)
# ['retrieval']
```

### Deactivation

Deactivate a skill to save context tokens:
```python
registry.deactivate("retrieval")
```

## Skill Lifecycle

```
┌──────────────┐
│   Discover   │  Scan skills/ directory for SKILL.md files
└──────┬───────┘
       │
       v
┌──────────────┐
│     Load     │  Read SKILL.md, config.yaml, prompts, scripts
└──────┬───────┘
       │
       v
┌──────────────┐
│   Activate   │  Inject instructions into agent context
└──────┬───────┘
       │
       v
┌──────────────┐
│   Execute    │  Agent uses skill knowledge to perform task
└──────┬───────┘
       │
       v
┌──────────────┐
│  Deactivate  │  Remove instructions to save tokens
└──────────────┘
```

## Auto-Active Skills

Some skills (like `hallucination_monitor`) are **auto-active**:
- No explicit triggers required
- Automatically run after specific events (e.g., answer generation)
- Cannot be manually deactivated
- Used for quality assurance and monitoring

## Configuration

### Global Configuration

Global skill settings in `src/core/config.py`:
```python
SKILL_REGISTRY_PATH = Path("skills")
SKILL_AUTO_DISCOVER = True
SKILL_CACHE_TTL_SECONDS = 300
```

### Per-Skill Configuration

Each skill has its own `config.yaml`:
```yaml
# Example: skills/retrieval/config.yaml
vector:
  top_k: 10
  score_threshold: 0.6
graph:
  enabled: true
  max_hops: 2
```

## Permissions

Skills can request permissions in their metadata:

| Permission | Risk | Description |
|------------|------|-------------|
| `read_documents` | Low | Read document content from vector DB |
| `write_documents` | Medium | Write/modify documents |
| `read_memory` | Low | Read from Redis/Graphiti memory |
| `write_memory` | Medium | Write to memory |
| `invoke_llm` | Medium | Make LLM API calls |
| `web_access` | High | Access external web services |
| `execute_code` | Critical | Execute Python/shell scripts |

## Best Practices

### Metadata
- Use clear, descriptive names (lowercase with underscores)
- Follow semantic versioning (MAJOR.MINOR.PATCH)
- List all intent patterns in triggers
- Declare all dependencies

### Instructions
- Write for a language model (be explicit)
- Use headings and lists for structure
- Provide concrete examples
- Document edge cases

### Configuration
- Provide reasonable defaults
- Document all settings
- Validate configuration on load
- Never store secrets (use environment variables)

### Prompts
- One prompt per file
- Use descriptive filenames
- Include variable placeholders: `{variable}`
- Test with multiple LLMs

## Testing

Test skills using the test suite:
```bash
pytest tests/unit/agents/skills/test_skill_registry.py
pytest tests/integration/agents/skills/test_retrieval_skill.py
```

## References

- [SKILL.md Template](../docs/skills/SKILL_TEMPLATE.md)
- [Skill Registry Implementation](../src/agents/skills/registry.py)
- [Anthropic Agent Skills Docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Agent Skills Engineering Blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Sprint 90 Plan](../docs/sprints/SPRINT_90_PLAN.md)

---

**Version:** 1.0.0
**Last Updated:** 2026-01-14
**Sprint:** 90
