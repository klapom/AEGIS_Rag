# Sprint 97 Plan: Skill Configuration UI & Admin Dashboard

**Epic:** AegisRAG Agentic Framework Transformation
**Phase:** Post-Phase 7 (Operational Excellence)
**ADR Reference:** [ADR-049](../adr/ADR-049-agentic-framework-architecture.md)
**Prerequisite:** Sprint 96 (EU-Governance & Compliance)
**Duration:** 14-18 days
**Total Story Points:** 38 SP
**Status:** 📝 Planned

---

## Sprint Goal

Implement a comprehensive **Admin UI for Skill Management**:
1. **Skill Registry Browser** - View, search, and inspect all skills
2. **Skill Configuration Editor** - Modify config.yaml via UI
3. **Tool Authorization Manager** - Configure skill-tool permissions
4. **Skill Lifecycle Dashboard** - Monitor activation, usage, metrics

**Target Outcome:** Full visual management of Anthropic Agent Skills ecosystem

---

## Research Foundation

> "Skills are modular capability containers that can be discovered, loaded, and configured dynamically."
> — [Anthropic Agent Skills Overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)

The UI should provide:
- Real-time skill status visualization
- Config editing without file system access
- Permission management with audit logging
- Performance metrics and usage analytics

---

## Features

| # | Feature | SP | Priority | Status |
|---|---------|-----|----------|--------|
| 97.1 | Skill Registry Browser UI | 10 | P0 | 📝 Planned |
| 97.2 | Skill Configuration Editor | 10 | P0 | 📝 Planned |
| 97.3 | Tool Authorization Manager | 8 | P0 | 📝 Planned |
| 97.4 | Skill Lifecycle Dashboard | 6 | P1 | 📝 Planned |
| 97.5 | SKILL.md Visual Editor | 4 | P2 | 📝 Planned |

---

## Feature 97.1: Skill Registry Browser UI (10 SP)

### Description

Visual interface to browse and inspect all available skills.

### Wireframe

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ AegisRAG Admin > Skills                                            [+ Add] │
├─────────────────────────────────────────────────────────────────────────────┤
│ Search: [___________________]  Filter: [All ▼]  Status: [Any ▼]            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│ │ 🔍 retrieval        │  │ 🤔 reflection       │  │ 🌐 web_search       │  │
│ │ v1.2.0              │  │ v1.0.0              │  │ v1.1.0              │  │
│ │ ───────────────────│  │ ───────────────────│  │ ───────────────────│  │
│ │ Vector & graph      │  │ Self-critique and   │  │ Web browsing with   │  │
│ │ retrieval skill     │  │ validation loop     │  │ browser-use         │  │
│ │                     │  │                     │  │                     │  │
│ │ Tools: 3            │  │ Tools: 1            │  │ Tools: 2            │  │
│ │ Triggers: 4         │  │ Triggers: 3         │  │ Triggers: 5         │  │
│ │ ───────────────────│  │ ───────────────────│  │ ───────────────────│  │
│ │ [🟢 Active]         │  │ [⚪ Inactive]       │  │ [🟢 Active]         │  │
│ │ [Config] [Logs]     │  │ [Config] [Logs]     │  │ [Config] [Logs]     │  │
│ └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
│                                                                             │
│ ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│ │ 📝 synthesis        │  │ ⚠️ hallucination     │  │ 🔧 automation       │  │
│ │ v1.0.0              │  │ _monitor v1.0.0     │  │ v0.9.0              │  │
│ │ ───────────────────│  │ ───────────────────│  │ ───────────────────│  │
│ │ Answer generation   │  │ Detect unsupported  │  │ Task automation     │  │
│ │ and summarization   │  │ claims              │  │ with tool chains    │  │
│ │                     │  │                     │  │                     │  │
│ │ Tools: 2            │  │ Tools: 0            │  │ Tools: 5            │  │
│ │ Triggers: 3         │  │ Triggers: 0 (auto)  │  │ Triggers: 4         │  │
│ │ ───────────────────│  │ ───────────────────│  │ ───────────────────│  │
│ │ [⚪ Inactive]       │  │ [🟢 Active]         │  │ [⚪ Inactive]       │  │
│ │ [Config] [Logs]     │  │ [Config] [Logs]     │  │ [Config] [Logs]     │  │
│ └─────────────────────┘  └─────────────────────┘  └─────────────────────┘  │
│                                                                             │
│ Showing 6 of 12 skills                               [1] [2] [>]           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Backend API

```python
# src/api/v1/admin/skills.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/admin/skills", tags=["Admin Skills"])


class SkillSummary(BaseModel):
    """Skill card data for UI."""
    name: str
    version: str
    description: str
    author: str
    is_active: bool
    tools_count: int
    triggers_count: int
    icon: str  # Emoji or icon name


class SkillDetail(BaseModel):
    """Full skill details."""
    name: str
    version: str
    description: str
    author: str
    triggers: List[str]
    tools: List[str]
    dependencies: List[str]
    permissions: List[str]
    config: dict
    instructions: str  # Markdown from SKILL.md
    is_active: bool
    activation_count: int
    last_activated: Optional[str]


@router.get("/", response_model=List[SkillSummary])
async def list_skills(
    search: Optional[str] = None,
    status: Optional[str] = None,  # active, inactive, all
    page: int = 1,
    limit: int = 12
):
    """List all available skills with filtering."""
    registry = get_skill_registry()
    skills = registry.list_available()

    summaries = []
    for name in skills:
        metadata = registry.get_metadata(name)
        skill = registry._loaded.get(name)

        summaries.append(SkillSummary(
            name=metadata.name,
            version=metadata.version,
            description=metadata.description,
            author=metadata.author,
            is_active=skill.is_active if skill else False,
            tools_count=len(metadata.tools) if hasattr(metadata, 'tools') else 0,
            triggers_count=len(metadata.triggers),
            icon=_get_skill_icon(metadata.name)
        ))

    # Apply filters
    if search:
        summaries = [s for s in summaries if search.lower() in s.name.lower() or search.lower() in s.description.lower()]
    if status == "active":
        summaries = [s for s in summaries if s.is_active]
    elif status == "inactive":
        summaries = [s for s in summaries if not s.is_active]

    # Paginate
    start = (page - 1) * limit
    return summaries[start:start + limit]


@router.get("/{skill_name}", response_model=SkillDetail)
async def get_skill(skill_name: str):
    """Get full skill details."""
    registry = get_skill_registry()
    if skill_name not in registry.list_available():
        raise HTTPException(404, f"Skill not found: {skill_name}")

    registry.load(skill_name)
    loaded = registry._loaded[skill_name]

    return SkillDetail(
        name=loaded.metadata.name,
        version=loaded.metadata.version,
        description=loaded.metadata.description,
        author=loaded.metadata.author,
        triggers=loaded.metadata.triggers,
        tools=[t.tool_name for t in loaded.metadata.tools] if hasattr(loaded.metadata, 'tools') else [],
        dependencies=loaded.metadata.dependencies,
        permissions=loaded.metadata.permissions,
        config=loaded.config,
        instructions=loaded.instructions,
        is_active=loaded.is_active,
        activation_count=_get_activation_count(skill_name),
        last_activated=_get_last_activation(skill_name)
    )


@router.post("/{skill_name}/activate")
async def activate_skill(skill_name: str):
    """Activate a skill."""
    registry = get_skill_registry()
    instructions = registry.activate(skill_name)
    return {"status": "activated", "instructions_length": len(instructions)}


@router.post("/{skill_name}/deactivate")
async def deactivate_skill(skill_name: str):
    """Deactivate a skill."""
    registry = get_skill_registry()
    registry.deactivate(skill_name)
    return {"status": "deactivated"}
```

### React Component

```typescript
// frontend/src/components/admin/SkillCard.tsx

interface SkillCardProps {
  skill: SkillSummary;
  onSelect: (name: string) => void;
  onToggle: (name: string, active: boolean) => void;
}

export const SkillCard: React.FC<SkillCardProps> = ({ skill, onSelect, onToggle }) => {
  return (
    <div className="bg-white rounded-lg shadow-md p-4 hover:shadow-lg transition-shadow">
      <div className="flex items-center justify-between mb-2">
        <span className="text-2xl">{skill.icon}</span>
        <span className="text-xs text-gray-500">v{skill.version}</span>
      </div>

      <h3 className="font-semibold text-lg mb-1">{skill.name}</h3>
      <p className="text-sm text-gray-600 mb-3 line-clamp-2">{skill.description}</p>

      <div className="flex gap-4 text-xs text-gray-500 mb-3">
        <span>🔧 {skill.tools_count} tools</span>
        <span>🎯 {skill.triggers_count} triggers</span>
      </div>

      <div className="flex items-center justify-between">
        <button
          onClick={() => onToggle(skill.name, !skill.is_active)}
          className={`px-3 py-1 rounded-full text-xs font-medium ${
            skill.is_active
              ? 'bg-green-100 text-green-700'
              : 'bg-gray-100 text-gray-600'
          }`}
        >
          {skill.is_active ? '🟢 Active' : '⚪ Inactive'}
        </button>

        <div className="flex gap-2">
          <button
            onClick={() => onSelect(skill.name)}
            className="text-blue-600 hover:text-blue-800 text-sm"
          >
            Config
          </button>
          <button className="text-gray-500 hover:text-gray-700 text-sm">
            Logs
          </button>
        </div>
      </div>
    </div>
  );
};
```

---

## Feature 97.2: Skill Configuration Editor (10 SP)

### Description

YAML-based configuration editor with validation and live preview.

### Wireframe

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Skill: retrieval > Configuration                          [Save] [Reset]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ┌─────────────────────────────────────┐  ┌─────────────────────────────────┤
│ │ config.yaml                         │  │ Preview                         │
│ │ ─────────────────────────────────── │  │ ───────────────────────────────│
│ │ # Retrieval Skill Configuration     │  │                                 │
│ │                                     │  │ ✅ Valid YAML                   │
│ │ embedding:                          │  │                                 │
│ │   model: bge-m3                     │  │ Settings:                       │
│ │   dimension: 1024                   │  │ ─────────                       │
│ │                                     │  │ • Embedding: bge-m3 (1024D)     │
│ │ search:                             │  │ • Top-K: 10                     │
│ │   top_k: 10                         │  │ • Modes: vector, hybrid         │
│ │   modes:                            │  │ • RRF k: 60                     │
│ │     - vector                        │  │                                 │
│ │     - hybrid                        │  │ Triggers:                       │
│ │   rrf_k: 60                         │  │ ─────────                       │
│ │                                     │  │ • search                        │
│ │ neo4j:                              │  │ • find                          │
│ │   max_hops: 2                       │  │ • lookup                        │
│ │   entity_limit: 50                  │  │ • retrieve                      │
│ │                                     │  │                                 │
│ │ reranking:                          │  │ Dependencies:                   │
│ │   enabled: true                     │  │ ─────────────                   │
│ │   model: cross-encoder/ms-marco     │  │ • qdrant ✅                     │
│ │   top_n: 5                          │  │ • neo4j ✅                      │
│ │                                     │  │ • embedding_service ✅          │
│ │                                     │  │                                 │
│ └─────────────────────────────────────┘  └─────────────────────────────────┘
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┤
│ │ Validation                                                               │
│ │ ───────────────────────────────────────────────────────────────────────│
│ │ ✅ YAML syntax valid                                                     │
│ │ ✅ Required fields present: embedding.model, search.top_k                │
│ │ ⚠️ Warning: search.top_k > 20 may impact latency                        │
│ │ ✅ Dependencies available: qdrant, neo4j, embedding_service              │
│ └─────────────────────────────────────────────────────────────────────────┘
└─────────────────────────────────────────────────────────────────────────────┘
```

### Backend API

```python
@router.get("/{skill_name}/config")
async def get_skill_config(skill_name: str) -> dict:
    """Get skill configuration."""
    registry = get_skill_registry()
    registry.load(skill_name)
    return registry._loaded[skill_name].config


@router.put("/{skill_name}/config")
async def update_skill_config(skill_name: str, config: dict):
    """Update skill configuration."""
    # Validate YAML structure
    errors = validate_skill_config(skill_name, config)
    if errors:
        raise HTTPException(400, {"errors": errors})

    # Write to config.yaml
    skill_path = Path("skills") / skill_name / "config.yaml"
    with open(skill_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    # Reload skill
    registry = get_skill_registry()
    if skill_name in registry._loaded:
        del registry._loaded[skill_name]
    registry.load(skill_name)

    return {"status": "updated", "config": config}


@router.post("/{skill_name}/config/validate")
async def validate_config(skill_name: str, config: dict):
    """Validate config without saving."""
    errors = validate_skill_config(skill_name, config)
    warnings = get_config_warnings(skill_name, config)

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }
```

---

## Feature 97.3: Tool Authorization Manager (8 SP)

### Description

Visual interface to manage which tools each skill can access.

### Wireframe

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Skill: automation > Tool Authorization                          [Save]     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ Authorized Tools                                                            │
│ ─────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│ ┌───────────────────────────────────────────────────────────────────────┐  │
│ │ Tool              │ Access Level │ Rate Limit │ Domains    │ Actions  │  │
│ ├───────────────────┼──────────────┼────────────┼────────────┼──────────┤  │
│ │ 🌐 browser        │ [Standard ▼] │ [30/min]   │ [Edit]     │ [🗑️]     │  │
│ │ 🐍 python_exec    │ [Elevated ▼] │ [10/min]   │ N/A        │ [🗑️]     │  │
│ │ 📁 file_write     │ [Elevated ▼] │ [20/min]   │ N/A        │ [🗑️]     │  │
│ │ 🔍 web_search     │ [Standard ▼] │ [60/min]   │ [Edit]     │ [🗑️]     │  │
│ │ 📝 llm_summarize  │ [Standard ▼] │ [∞]        │ N/A        │ [🗑️]     │  │
│ └───────────────────┴──────────────┴────────────┴────────────┴──────────┘  │
│                                                                             │
│ [+ Add Tool]                                                                │
│                                                                             │
│ ─────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│ Domain Restrictions (browser, web_search)                                   │
│ ─────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│ Allowed Domains:                          Blocked Domains:                  │
│ ┌───────────────────────────────────┐     ┌───────────────────────────────┐│
│ │ *.wikipedia.org           [🗑️]    │     │ *.malware.com         [🗑️]    ││
│ │ *.github.com              [🗑️]    │     │ *.phishing.net        [🗑️]    ││
│ │ *.arxiv.org               [🗑️]    │     │                               ││
│ │ *.stackoverflow.com       [🗑️]    │     │                               ││
│ │ [+ Add domain]                    │     │ [+ Add domain]                ││
│ └───────────────────────────────────┘     └───────────────────────────────┘│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Feature 97.4: Skill Lifecycle Dashboard (6 SP)

### Description

Real-time monitoring of skill activation, usage, and performance.

### Wireframe

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Skill Lifecycle Dashboard                          Last updated: 12:34:56  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ┌─────────────────────────┐  ┌─────────────────────────┐  ┌───────────────┐│
│ │ Active Skills           │  │ Tool Calls (24h)        │  │ Policy Alerts ││
│ │         4/12            │  │        1,247            │  │      3        ││
│ │ ███████████░░░░░░░      │  │ ████████████████        │  │ ⚠️ 2 warnings  ││
│ │         33%             │  │ +12% vs yesterday       │  │ 🔴 1 critical  ││
│ └─────────────────────────┘  └─────────────────────────┘  └───────────────┘│
│                                                                             │
│ Skill Activation Timeline (Last 24 Hours)                                   │
│ ─────────────────────────────────────────────────────────────────────────── │
│ retrieval   ████████████████████████████████████████████████               │
│ reflection  ░░░░████░░░░████░░░░████░░░░████░░░░████░░░░                   │
│ web_search  ░░░░░░░░████████░░░░░░░░░░░░░░░░████████░░░░                   │
│ synthesis   ░░░░░░░░░░░░████████████░░░░░░░░████████████                   │
│             ───────────────────────────────────────────────                │
│             00:00    06:00    12:00    18:00    24:00                      │
│                                                                             │
│ Top Tool Usage                          Recent Policy Violations            │
│ ─────────────────────────               ──────────────────────────────────│
│ 1. vector_search    412 calls          ⚠️ rate_limit: web_search (14:23)   │
│ 2. llm_generate     389 calls          ⚠️ rate_limit: browser (13:45)      │
│ 3. browser          156 calls          🔴 blocked_pattern: python_exec     │
│ 4. graph_query      134 calls              (12:01) - "rm -rf" detected     │
│ 5. python_exec       89 calls                                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Feature 97.5: SKILL.md Visual Editor (4 SP)

### Description

Markdown editor with frontmatter GUI for editing SKILL.md files.

### Implementation

```typescript
// Split view: Frontmatter form + Markdown editor

interface SkillMdEditorProps {
  skillName: string;
}

export const SkillMdEditor: React.FC<SkillMdEditorProps> = ({ skillName }) => {
  const [frontmatter, setFrontmatter] = useState<SkillFrontmatter>({});
  const [markdown, setMarkdown] = useState("");

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Frontmatter Form */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-semibold mb-4">Metadata</h3>

        <Input label="Name" value={frontmatter.name} onChange={...} />
        <Input label="Version" value={frontmatter.version} onChange={...} />
        <Textarea label="Description" value={frontmatter.description} onChange={...} />
        <Input label="Author" value={frontmatter.author} onChange={...} />

        <TagInput label="Triggers" tags={frontmatter.triggers} onChange={...} />
        <TagInput label="Dependencies" tags={frontmatter.dependencies} onChange={...} />
        <TagInput label="Permissions" tags={frontmatter.permissions} onChange={...} />
      </div>

      {/* Markdown Editor */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="font-semibold mb-4">Instructions</h3>
        <MarkdownEditor
          value={markdown}
          onChange={setMarkdown}
          preview={true}
        />
      </div>
    </div>
  );
};
```

---

## Deliverables

| Artifact | Location | Description |
|----------|----------|-------------|
| Skills API | `src/api/v1/admin/skills.py` | Backend endpoints |
| Skill Browser | `frontend/src/components/admin/SkillBrowser.tsx` | Grid view of skills |
| Config Editor | `frontend/src/components/admin/SkillConfigEditor.tsx` | YAML editor |
| Tool Auth Manager | `frontend/src/components/admin/ToolAuthManager.tsx` | Permission UI |
| Dashboard | `frontend/src/pages/admin/SkillDashboard.tsx` | Lifecycle monitoring |
| E2E Tests | `frontend/tests/e2e/admin-skills.spec.ts` | Playwright tests |

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Skill Management UI | ❌ None | ✅ Full CRUD |
| Config Editing | File-based only | Visual editor |
| Tool Authorization | Hardcoded | UI-configurable |
| Lifecycle Monitoring | Logs only | Real-time dashboard |

---

## Dependencies

- Sprint 90: Skill Registry (for API integration)
- Sprint 92: Skill Lifecycle Manager (for dashboard data)
- Sprint 93: Tool Authorization (for permissions UI)
- Sprint 94: Metrics collection (for dashboard charts)

---

**Document:** SPRINT_97_PLAN.md
**Status:** 📝 Planned
**Created:** 2026-01-13
