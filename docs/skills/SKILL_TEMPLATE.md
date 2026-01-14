# SKILL.md Template

This document defines the standard structure for AegisRAG Agent Skills following the Anthropic Agent Skills standard.

## Purpose

SKILL.md files provide:
- **Metadata** for discovery and activation
- **Instructions** for agent behavior when skill is active
- **Configuration** requirements and options
- **Examples** showing usage patterns

## Template

```markdown
---
# Required metadata
name: skill_name
version: 1.0.0
description: Brief description of what this skill does
author: Author Name

# Activation triggers (intent patterns)
triggers:
  - keyword1
  - keyword2
  - pattern_*

# Dependencies on other skills or services
dependencies:
  - other_skill
  - qdrant
  - neo4j

# Permissions required
permissions:
  - read_documents
  - write_memory
  - invoke_llm
  - web_access

# Resource files
resources:
  prompts: prompts/
  scripts: scripts/
  data: data/
---

# Skill Name

## Overview

Detailed description of what this skill does and when to use it.
This section should explain the skill's purpose, primary use cases, and value proposition.

## Capabilities

- Capability 1: Description
- Capability 2: Description
- Capability 3: Description

## Usage

### When to Activate

Describe conditions that should trigger this skill:
- User query patterns
- Intent classifications
- System states
- Dependency conditions

### Input Requirements

What information the skill needs to function:
- Required parameters
- Optional parameters
- Context dependencies
- External service requirements

### Output Format

What the skill produces:
- Output structure
- Data types
- Success conditions
- Error handling

## Configuration

```yaml
# config.yaml example
setting1: value1
setting2: value2
nested:
  option_a: true
  option_b: 42
```

### Configuration Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| setting1 | string | Yes | - | Description of setting1 |
| setting2 | integer | No | 10 | Description of setting2 |

## Examples

### Example 1: Basic Usage

**Input:**
```
User query: "What is hybrid search?"
Intent: SEARCH
```

**Output:**
```
Retrieved 5 documents using BGE-M3 hybrid search...
```

### Example 2: Advanced Usage

**Input:**
```
User query: "Find documents about neural networks and explain their architecture"
Intent: RESEARCH
Dependencies: retrieval, synthesis
```

**Output:**
```
Phase 1: Retrieved 10 documents about neural networks
Phase 2: Generated comprehensive explanation with citations
```

## Limitations

- Known limitation 1: Description and workaround
- Known limitation 2: Description and workaround
- Known limitation 3: Description and mitigation

## Version History

- 1.0.0 (2026-01-14): Initial release
  - Core functionality
  - Basic configuration
  - Standard prompts

- 0.9.0 (2026-01-10): Beta release
  - Prototype implementation
  - Limited testing
```

## Metadata Fields Reference

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `name` | string | Unique skill identifier (lowercase, underscores) | `retrieval` |
| `version` | string | Semantic version (MAJOR.MINOR.PATCH) | `1.0.0` |
| `description` | string | Brief skill description (1-2 sentences) | `Vector and graph retrieval skill` |
| `author` | string | Skill author/maintainer | `AegisRAG Team` |

### Optional Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `triggers` | list[string] | Intent patterns that activate this skill | `[search, find, lookup]` |
| `dependencies` | list[string] | Required skills or services | `[qdrant, neo4j]` |
| `permissions` | list[string] | Required permissions | `[read_documents, invoke_llm]` |
| `resources` | dict[string, string] | Resource file locations | `{prompts: "prompts/"}` |

### Permission Types

| Permission | Description | Risk Level |
|------------|-------------|------------|
| `read_documents` | Read document content from vector DB | Low |
| `write_documents` | Write/modify documents in vector DB | Medium |
| `read_memory` | Read from Redis/Graphiti memory | Low |
| `write_memory` | Write to Redis/Graphiti memory | Medium |
| `invoke_llm` | Make LLM API calls | Medium |
| `web_access` | Access external web services | High |
| `execute_code` | Execute Python/shell scripts | Critical |

## Directory Structure

Each skill should follow this structure:

```
skills/
└── skill_name/
    ├── SKILL.md           # Metadata and instructions (REQUIRED)
    ├── config.yaml        # Configuration (recommended)
    ├── prompts/           # Prompt templates (optional)
    │   ├── template1.txt
    │   └── template2.txt
    ├── scripts/           # Utility scripts (optional)
    │   ├── helper.py
    │   └── validator.py
    └── data/              # Static data files (optional)
        ├── lookup.json
        └── schema.yaml
```

## Best Practices

### Metadata

1. **Unique Names**: Use lowercase with underscores: `graph_search`, not `GraphSearch`
2. **Semantic Versioning**: Follow SemVer (1.0.0, 1.1.0, 2.0.0)
3. **Clear Descriptions**: Be specific about functionality
4. **Accurate Triggers**: List all intent patterns that should activate this skill

### Instructions

1. **Clarity**: Write for a language model - be explicit and unambiguous
2. **Structure**: Use headings and lists for easy parsing
3. **Examples**: Provide concrete input/output examples
4. **Edge Cases**: Document error conditions and handling

### Configuration

1. **Reasonable Defaults**: Provide sensible defaults for all optional settings
2. **Validation**: Document valid ranges and types
3. **Documentation**: Explain each configuration field
4. **Security**: Never store secrets in config.yaml - use environment variables

### Prompts

1. **Modularity**: One prompt per file
2. **Naming**: Use descriptive names: `critique.txt`, not `prompt1.txt`
3. **Variables**: Use `{variable}` syntax for template variables
4. **Testing**: Test prompts with multiple LLMs if possible

## Integration with Skill Registry

The Skill Registry (`src/agents/skills/registry.py`) uses this structure:

1. **Discovery**: Scans `skills/` directory for SKILL.md files
2. **Parsing**: Extracts YAML frontmatter for metadata
3. **Loading**: Reads instructions, config, prompts, scripts
4. **Activation**: Injects instructions into agent context when triggered
5. **Deactivation**: Removes instructions to save context tokens

## Examples from Base Skills

See actual implementations:
- `skills/retrieval/SKILL.md` - Vector and graph retrieval
- `skills/reflection/SKILL.md` - Self-critique and validation
- `skills/synthesis/SKILL.md` - Answer generation
- `skills/hallucination_monitor/SKILL.md` - Hallucination detection

## References

- [Anthropic Agent Skills Overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Agent Skills Engineering Blog](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Agent Skills GitHub Repository](https://github.com/anthropics/skills)
- [Agent Skills Deep Dive](https://medium.com/aimonks/claude-agent-skills-a-first-principles-deep-dive-into-prompt-based-meta-tools-022de66fc721)

---

**Version:** 1.0.0
**Last Updated:** 2026-01-14
**Sprint:** 90
