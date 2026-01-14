# Sprint 91 Quick Reference: Intent Router & Skill Activation

**For Developers:** Fast reference for using the new skill activation system

---

## Quick Start

```python
from src.agents.routing import SkillRouter
from src.agents.skills import get_skill_registry
from src.agents.security import PermissionEngine
from src.components.retrieval.intent_classifier import get_intent_classifier

# Initialize
classifier = get_intent_classifier()
registry = get_skill_registry()
permissions = PermissionEngine()
router = SkillRouter(classifier, registry, permissions)

# Route query
plan = await router.route("How does authentication work?")
instructions = await router.activate_skills(plan)
```

---

## Intent Types

| Intent | Use Case | Context Budget | Skills |
|--------|----------|----------------|--------|
| VECTOR | Factual lookups | 2K tokens | retrieval, synthesis |
| GRAPH | Entity queries | 3K tokens | retrieval, graph_reasoning, reflection |
| HYBRID | Complex queries | 4K tokens | retrieval, graph_reasoning, reflection, synthesis |
| MEMORY | Conversation history | 2K tokens | memory, retrieval |
| RESEARCH | Multi-step research | 5K tokens | retrieval, reflection, planner, web_search, synthesis |

---

## Permission Types

| Permission | Purpose | Example Skills |
|------------|---------|----------------|
| READ_DOCUMENTS | Read indexed data | retrieval, graph_reasoning |
| WRITE_MEMORY | Write conversation history | memory |
| INVOKE_LLM | Make LLM calls | all skills |
| WEB_ACCESS | Internet access | web_search |
| CODE_EXECUTION | Run code | code_interpreter |
| FILE_ACCESS | Local filesystem | file_manager |
| ADMIN | Admin operations | admin_tools |

---

## Configuration

Edit `config/skill_triggers.yaml`:

```yaml
intent_triggers:
  RESEARCH:
    required: [retrieval, reflection, planner]
    optional: [web_search, synthesis]
    budget: 5000

pattern_triggers:
  - pattern: "(?i)(latest|recent)"
    skills: [web_search]
    priority: high
```

---

## Metrics

```python
from src.agents.routing.metrics import get_metrics_collector

collector = get_metrics_collector()

# Get stats
stats = collector.get_usage_stats()
efficiency = collector.get_context_efficiency()

print(f"Savings: {efficiency['savings_percentage']}%")
```

---

## Files

- `src/agents/routing/skill_router.py` - Intent routing
- `src/agents/routing/trigger_config.py` - Trigger configuration
- `src/agents/routing/metrics.py` - Metrics collection
- `src/agents/security/permission_engine.py` - Permission management
- `config/skill_triggers.yaml` - Trigger rules

---

**Created:** 2026-01-14
**Sprint:** 91
