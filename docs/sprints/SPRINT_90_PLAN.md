# Sprint 90 Plan: Reflexion, Hallucination & Skill Registry Bootstrap

**Epic:** AegisRAG Agentic Framework Transformation
**Phase:** 1 of 7 (Foundation)
**ADR Reference:** [ADR-049](../adr/ADR-049-agentic-framework-architecture.md)
**Prerequisite:** Sprint 89 (RAGAS 1000-Sample Complete)
**Duration:** 14-18 days
**Total Story Points:** 36 SP
**Status:** 📝 Planned

---

## Sprint Goal

Establish the **foundation for agentic capabilities** with Anthropic Agent Skills integration:
1. **Skill Registry** - Local, configurable registry for Agent Skills
2. **Reflection Loop** - Self-critique and validation in Agent Core
3. **Hallucination Monitoring** - Active detection with logging
4. **SKILL.md MVP** - Standard skill metadata structure

**Target Outcome:** RAGAS Faithfulness 80% → 88%+, Skill Registry operational

---

## Why Agent Skills?

> "Agent Skills are folders of instructions, scripts and resources loaded dynamically."
> — [Anthropic Agent Skills Overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)

**Key Benefits:**
- **Token Efficiency:** Skills loaded only when needed, reducing context overhead
- **Modularity:** Expertise packaged as reusable components
- **Portability:** Open standard for cross-platform compatibility
- **Governance:** Per-skill permissions and audit trails

---

## Research Foundation

### Anthropic Agent Skills Standard

| Source | URL | Key Insight |
|--------|-----|-------------|
| Official Docs | [platform.claude.com/docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) | Skills are modular capability containers |
| Engineering Blog | [anthropic.com/engineering](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) | Skills lifecycle and best practices |
| GitHub Repo | [github.com/anthropics/skills](https://github.com/anthropics/skills) | Reference implementations |
| Open Standard | [aibusiness.com](https://aibusiness.com/foundation-models/anthropic-launches-skills-open-standard-claude) | Industry adoption trend |
| Deep Dive | [medium.com/aimonks](https://medium.com/aimonks/claude-agent-skills-a-first-principles-deep-dive-into-prompt-based-meta-tools-022de66fc721) | First-principles analysis |

---

## Features

| # | Feature | SP | Priority | Status |
|---|---------|-----|----------|--------|
| 90.1 | Skill Registry Implementation | 10 | P0 | 📝 Planned |
| 90.2 | Reflection Loop in Agent Core | 8 | P0 | 📝 Planned |
| 90.3 | Hallucination Monitoring & Logging | 8 | P0 | 📝 Planned |
| 90.4 | SKILL.md MVP Structure | 5 | P0 | 📝 Planned |
| 90.5 | Base Skills (Retrieval, Answer) | 5 | P1 | 📝 Planned |

---

## Feature 90.1: Skill Registry Implementation (10 SP)

### Description

Implement a **local, configurable Skill Registry** following the Anthropic Agent Skills standard.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Skill Registry Architecture              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  skills/                                                    │
│  ├── retrieval/                                             │
│  │   ├── SKILL.md          # Skill metadata & instructions  │
│  │   ├── config.yaml       # Skill configuration            │
│  │   ├── prompts/          # Specialized prompts            │
│  │   └── scripts/          # Utility scripts                │
│  ├── reasoning/                                             │
│  │   ├── SKILL.md                                           │
│  │   ├── reflection.py     # Reflection implementation      │
│  │   └── prompts/                                           │
│  └── synthesis/                                             │
│      ├── SKILL.md                                           │
│      └── templates/                                         │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Skill Registry API                  │   │
│  │  - discover()   : Find available skills              │   │
│  │  - load(name)   : Load skill into context            │   │
│  │  - unload(name) : Remove skill from context          │   │
│  │  - list_active(): Get currently loaded skills        │   │
│  │  - get_metadata(): Read SKILL.md info                │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# src/agents/skills/registry.py

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import yaml
import importlib.util

@dataclass
class SkillMetadata:
    """Metadata from SKILL.md."""
    name: str
    version: str
    description: str
    author: str
    triggers: List[str]  # Intent patterns that activate this skill
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    resources: Dict[str, str] = field(default_factory=dict)


@dataclass
class LoadedSkill:
    """A skill loaded into memory."""
    metadata: SkillMetadata
    path: Path
    instructions: str  # Parsed from SKILL.md
    config: Dict[str, Any]
    prompts: Dict[str, str]
    scripts: Dict[str, Callable]
    is_active: bool = False


class SkillRegistry:
    """
    Registry for Anthropic Agent Skills.

    Skills are modular capability containers that can be:
    - Discovered from filesystem
    - Loaded on-demand based on intent
    - Unloaded to save context tokens
    - Versioned and updated independently

    Based on: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
    """

    def __init__(
        self,
        skills_dir: Path = Path("skills"),
        auto_discover: bool = True
    ):
        self.skills_dir = skills_dir
        self._available: Dict[str, SkillMetadata] = {}
        self._loaded: Dict[str, LoadedSkill] = {}
        self._active: List[str] = []
        # Sprint 90: Embedding-based intent matching
        self._embedding_service = None
        self._trigger_embeddings: Dict[str, list] = {}

        if auto_discover:
            self.discover()

    def discover(self) -> Dict[str, SkillMetadata]:
        """
        Discover all available skills in skills directory.

        Scans for SKILL.md files and parses metadata.
        """
        self._available.clear()

        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            return {}

        for skill_path in self.skills_dir.iterdir():
            if skill_path.is_dir():
                skill_md = skill_path / "SKILL.md"
                if skill_md.exists():
                    metadata = self._parse_skill_md(skill_md)
                    if metadata:
                        self._available[metadata.name] = metadata

        return self._available

    def _parse_skill_md(self, path: Path) -> Optional[SkillMetadata]:
        """
        Parse SKILL.md file for metadata.

        Expected format:
        ---
        name: retrieval
        version: 1.0.0
        description: Vector and graph retrieval skill
        author: AegisRAG Team
        triggers:
          - search
          - find
          - lookup
        dependencies:
          - qdrant
          - neo4j
        permissions:
          - read_documents
        ---

        # Retrieval Skill

        Instructions for the agent...
        """
        content = path.read_text()

        # Parse YAML frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1])
                    return SkillMetadata(
                        name=frontmatter.get('name', path.parent.name),
                        version=frontmatter.get('version', '0.1.0'),
                        description=frontmatter.get('description', ''),
                        author=frontmatter.get('author', 'Unknown'),
                        triggers=frontmatter.get('triggers', []),
                        dependencies=frontmatter.get('dependencies', []),
                        permissions=frontmatter.get('permissions', []),
                        resources=frontmatter.get('resources', {})
                    )
                except yaml.YAMLError:
                    pass

        return None

    def load(self, name: str) -> LoadedSkill:
        """
        Load a skill into memory.

        Reads:
        - SKILL.md (instructions)
        - config.yaml (configuration)
        - prompts/*.txt (prompt templates)
        - scripts/*.py (utility functions)
        """
        if name in self._loaded:
            return self._loaded[name]

        if name not in self._available:
            raise ValueError(f"Skill not found: {name}")

        skill_path = self.skills_dir / name
        metadata = self._available[name]

        # Read instructions from SKILL.md
        skill_md = skill_path / "SKILL.md"
        content = skill_md.read_text()
        instructions = self._extract_instructions(content)

        # Load config
        config = {}
        config_path = skill_path / "config.yaml"
        if config_path.exists():
            config = yaml.safe_load(config_path.read_text())

        # Load prompts
        prompts = {}
        prompts_dir = skill_path / "prompts"
        if prompts_dir.exists():
            for prompt_file in prompts_dir.glob("*.txt"):
                prompts[prompt_file.stem] = prompt_file.read_text()

        # Load scripts
        scripts = {}
        scripts_dir = skill_path / "scripts"
        if scripts_dir.exists():
            for script_file in scripts_dir.glob("*.py"):
                scripts[script_file.stem] = self._load_script(script_file)

        skill = LoadedSkill(
            metadata=metadata,
            path=skill_path,
            instructions=instructions,
            config=config,
            prompts=prompts,
            scripts=scripts,
            is_active=False
        )

        self._loaded[name] = skill
        return skill

    def _extract_instructions(self, content: str) -> str:
        """Extract instructions from SKILL.md (after frontmatter)."""
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                return parts[2].strip()
        return content

    def _load_script(self, path: Path) -> Optional[Callable]:
        """Dynamically load a Python script."""
        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # Return main function if exists
                return getattr(module, 'main', None) or getattr(module, 'run', None)
        except Exception:
            pass
        return None

    def activate(self, name: str) -> str:
        """
        Activate a skill and return its instructions for the context.

        This is the key operation that adds skill knowledge to the agent.
        """
        if name not in self._loaded:
            self.load(name)

        skill = self._loaded[name]
        skill.is_active = True

        if name not in self._active:
            self._active.append(name)

        return skill.instructions

    def deactivate(self, name: str):
        """Deactivate a skill to save context tokens."""
        if name in self._loaded:
            self._loaded[name].is_active = False
        if name in self._active:
            self._active.remove(name)

    def get_active_instructions(self) -> str:
        """Get combined instructions from all active skills."""
        instructions = []
        for name in self._active:
            if name in self._loaded:
                skill = self._loaded[name]
                instructions.append(f"## Skill: {skill.metadata.name}\n\n{skill.instructions}")
        return "\n\n---\n\n".join(instructions)

    def list_available(self) -> List[str]:
        """List all available skills."""
        return list(self._available.keys())

    def list_active(self) -> List[str]:
        """List currently active skills."""
        return list(self._active)

    def get_metadata(self, name: str) -> Optional[SkillMetadata]:
        """Get metadata for a skill."""
        return self._available.get(name)

    def match_intent(self, intent: str, similarity_threshold: float = 0.75) -> List[str]:
        """
        Find skills that match an intent using embedding-based semantic matching.

        Uses BGE-M3 embeddings for semantic similarity instead of string matching.
        This allows matching "find documents" to skill trigger "search" even without
        exact keyword overlap.

        Args:
            intent: User intent to match
            similarity_threshold: Minimum cosine similarity (0.0-1.0) for match

        Returns:
            List of matching skill names, sorted by similarity
        """
        # Sprint 90: Embedding-based matching (not string matching)
        # Uses pre-computed trigger embeddings for fast lookup
        if self._embedding_service is None:
            from src.components.embedding.embedding_factory import create_embedding_service
            self._embedding_service = create_embedding_service()
            self._precompute_trigger_embeddings()

        intent_embedding = self._embedding_service.embed_query(intent)

        matches = []
        for name, metadata in self._available.items():
            # Get max similarity across all triggers for this skill
            max_similarity = 0.0
            for trigger in metadata.triggers:
                trigger_key = f"{name}:{trigger}"
                if trigger_key in self._trigger_embeddings:
                    similarity = self._cosine_similarity(
                        intent_embedding,
                        self._trigger_embeddings[trigger_key]
                    )
                    max_similarity = max(max_similarity, similarity)

            if max_similarity >= similarity_threshold:
                matches.append((name, max_similarity))

        # Sort by similarity (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in matches]

    def _precompute_trigger_embeddings(self):
        """Pre-compute embeddings for all skill triggers."""
        self._trigger_embeddings = {}
        for name, metadata in self._available.items():
            for trigger in metadata.triggers:
                trigger_key = f"{name}:{trigger}"
                self._trigger_embeddings[trigger_key] = self._embedding_service.embed_query(trigger)

    def _cosine_similarity(self, a: list, b: list) -> float:
        """Compute cosine similarity between two vectors."""
        import numpy as np
        a, b = np.array(a), np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# Global registry instance
_registry: Optional[SkillRegistry] = None

def get_skill_registry(skills_dir: Optional[Path] = None) -> SkillRegistry:
    """Get or create the global skill registry."""
    global _registry
    if _registry is None:
        _registry = SkillRegistry(skills_dir or Path("skills"))
    return _registry
```

### Acceptance Criteria

- [ ] Skill discovery from filesystem working
- [ ] SKILL.md parsing with frontmatter
- [ ] Load/unload skills on demand
- [ ] Active skill instructions merged into context
- [ ] Intent-based skill matching
- [ ] 10 unit tests (100% coverage)

---

## Feature 90.2: Reflection Loop in Agent Core (8 SP)

### Description

Implement a **Reflection Loop** that allows the agent to self-critique and validate responses.

### Implementation

```python
# src/agents/skills/reflection.py
# This would be packaged as skills/reflection/

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ReflectionResult:
    """Result of reflection step."""
    original_answer: str
    critique: str
    score: float  # 0.0 - 1.0
    issues: List[str]
    improved_answer: Optional[str] = None
    iteration: int = 0


class ReflectionSkill:
    """
    Reflection skill for self-critique and validation.

    Loaded as: skills/reflection/

    Based on: Reflexion paper (Shinn et al. 2023)
    """

    def __init__(
        self,
        llm: BaseChatModel,
        max_iterations: int = 3,
        confidence_threshold: float = 0.85
    ):
        self.llm = llm
        self.max_iterations = max_iterations
        self.confidence_threshold = confidence_threshold

    async def reflect(
        self,
        query: str,
        answer: str,
        contexts: List[str]
    ) -> ReflectionResult:
        """
        Reflect on an answer and identify issues.

        Steps:
        1. Critique the answer for factual accuracy
        2. Check alignment with provided contexts
        3. Identify missing information
        4. Score confidence
        """
        critique_prompt = f"""You are a critical reviewer. Evaluate this answer:

Question: {query}

Contexts provided:
{self._format_contexts(contexts)}

Answer to evaluate:
{answer}

Evaluate for:
1. FACTUAL ACCURACY: Does it match the contexts?
2. COMPLETENESS: Does it fully answer the question?
3. HALLUCINATION: Does it include unsupported claims?
4. CLARITY: Is it clear and well-structured?

Provide:
SCORE: [0.0-1.0]
ISSUES: [list specific problems]
SUGGESTIONS: [improvements needed]

Critique:"""

        response = await self.llm.ainvoke(critique_prompt)
        critique = response.content

        score = self._parse_score(critique)
        issues = self._parse_issues(critique)

        return ReflectionResult(
            original_answer=answer,
            critique=critique,
            score=score,
            issues=issues,
            iteration=0
        )

    async def improve(
        self,
        query: str,
        reflection: ReflectionResult,
        contexts: List[str]
    ) -> ReflectionResult:
        """Improve answer based on reflection."""
        if reflection.score >= self.confidence_threshold:
            return reflection

        improve_prompt = f"""Improve this answer based on the critique.

Question: {query}

Contexts:
{self._format_contexts(contexts)}

Original Answer:
{reflection.original_answer}

Critique:
{reflection.critique}

Issues to fix:
{chr(10).join(f'- {issue}' for issue in reflection.issues)}

Write an improved answer that addresses all issues.
Only use information from the provided contexts.

Improved Answer:"""

        response = await self.llm.ainvoke(improve_prompt)
        improved = response.content

        # Re-evaluate
        new_reflection = await self.reflect(query, improved, contexts)
        new_reflection.iteration = reflection.iteration + 1
        new_reflection.improved_answer = improved

        return new_reflection

    async def reflect_and_improve(
        self,
        query: str,
        answer: str,
        contexts: List[str]
    ) -> ReflectionResult:
        """Full reflection loop with improvements."""
        reflection = await self.reflect(query, answer, contexts)

        for i in range(self.max_iterations):
            if reflection.score >= self.confidence_threshold:
                break
            reflection = await self.improve(query, reflection, contexts)

        return reflection

    def _format_contexts(self, contexts: List[str]) -> str:
        return "\n\n".join(f"[{i+1}] {ctx}" for i, ctx in enumerate(contexts))

    def _parse_score(self, critique: str) -> float:
        import re
        match = re.search(r'SCORE:\s*([0-9.]+)', critique)
        if match:
            return min(1.0, max(0.0, float(match.group(1))))
        return 0.5

    def _parse_issues(self, critique: str) -> List[str]:
        import re
        issues = []
        match = re.search(r'ISSUES:\s*\[(.*?)\]', critique, re.DOTALL)
        if match:
            issues_text = match.group(1)
            issues = [i.strip() for i in issues_text.split(',') if i.strip()]
        return issues
```

### SKILL.md for Reflection

```markdown
---
name: reflection
version: 1.0.0
description: Self-critique and validation loop for answer quality
author: AegisRAG Team
triggers:
  - validate
  - check
  - verify
  - critique
dependencies: []
permissions:
  - read_contexts
  - invoke_llm
---

# Reflection Skill

This skill enables the agent to critically evaluate and improve its own responses.

## When to Use

- Complex questions requiring multi-step reasoning
- Questions where accuracy is critical
- When initial answer confidence is low
- Research-type queries

## Process

1. **Generate** initial answer from contexts
2. **Critique** answer for accuracy, completeness, hallucination
3. **Score** confidence (0.0-1.0)
4. **Improve** if score < 0.85 (max 3 iterations)
5. **Return** best answer with reflection trace

## Configuration

```yaml
max_iterations: 3
confidence_threshold: 0.85
auto_activate_for:
  - RESEARCH intent
  - GRAPH intent
```
```

---

## Feature 90.3: Hallucination Monitoring & Logging (8 SP)

### Description

Implement **active hallucination detection** with comprehensive logging.

```python
# src/agents/skills/hallucination_monitor.py

class HallucinationMonitor:
    """
    Monitor and log hallucinations in generated answers.

    Packaged as: skills/hallucination_monitor/
    """

    def __init__(
        self,
        llm: BaseChatModel,
        logger: Logger
    ):
        self.llm = llm
        self.logger = logger
        self._metrics = {
            "total_checks": 0,
            "hallucinations_detected": 0,
            "claims_verified": 0,
            "claims_unsupported": 0
        }

    async def check(
        self,
        answer: str,
        contexts: List[str]
    ) -> HallucinationReport:
        """Check answer for hallucinations."""
        self._metrics["total_checks"] += 1

        # Extract claims
        claims = await self._extract_claims(answer)

        # Verify each claim
        verifications = []
        for claim in claims:
            result = await self._verify_claim(claim, contexts)
            verifications.append(result)

            if result.is_supported:
                self._metrics["claims_verified"] += 1
            else:
                self._metrics["claims_unsupported"] += 1

        # Calculate score
        unsupported = [v for v in verifications if not v.is_supported]
        score = len(unsupported) / len(claims) if claims else 0.0

        if score > 0.1:
            self._metrics["hallucinations_detected"] += 1

        # Log
        self._log_check(answer, claims, verifications, score)

        return HallucinationReport(
            answer=answer,
            claims=claims,
            verifications=verifications,
            hallucination_score=score,
            unsupported_claims=[v.claim for v in unsupported]
        )

    def _log_check(
        self,
        answer: str,
        claims: List[Claim],
        verifications: List[ClaimVerification],
        score: float
    ):
        """Log hallucination check results."""
        self.logger.info(
            "hallucination_check",
            extra={
                "answer_length": len(answer),
                "num_claims": len(claims),
                "num_verified": sum(1 for v in verifications if v.is_supported),
                "num_unsupported": sum(1 for v in verifications if not v.is_supported),
                "hallucination_score": score,
                "verdict": "PASS" if score < 0.1 else "WARN" if score < 0.3 else "FAIL"
            }
        )

    def get_metrics(self) -> Dict[str, int]:
        """Get accumulated metrics."""
        return self._metrics.copy()
```

---

## Feature 90.4: SKILL.md MVP Structure (5 SP)

### Description

Define the standard SKILL.md structure for AegisRAG skills.

### Template

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

## Capabilities

- Capability 1
- Capability 2
- Capability 3

## Usage

### When to Activate

Describe conditions that should trigger this skill.

### Input Requirements

What information the skill needs to function.

### Output Format

What the skill produces.

## Configuration

```yaml
# config.yaml example
setting1: value1
setting2: value2
```

## Examples

### Example 1: Basic Usage

```
Input: ...
Output: ...
```

### Example 2: Advanced Usage

```
Input: ...
Output: ...
```

## Limitations

- Known limitation 1
- Known limitation 2

## Version History

- 1.0.0: Initial release
```

---

## Feature 90.5: Base Skills (5 SP)

### Description

Create initial skill packages for core functionality.

### Skills to Create

| Skill | Purpose | Triggers |
|-------|---------|----------|
| `retrieval` | Vector & graph search | search, find, lookup |
| `reflection` | Self-critique loop | validate, check, verify |
| `synthesis` | Answer generation | answer, summarize, explain |
| `hallucination_monitor` | Detect unsupported claims | (auto-active) |

### Directory Structure

```
skills/
├── retrieval/
│   ├── SKILL.md
│   ├── config.yaml
│   └── prompts/
│       ├── vector_search.txt
│       └── graph_search.txt
├── reflection/
│   ├── SKILL.md
│   ├── config.yaml
│   └── prompts/
│       ├── critique.txt
│       └── improve.txt
├── synthesis/
│   ├── SKILL.md
│   ├── config.yaml
│   └── prompts/
│       └── answer_template.txt
└── hallucination_monitor/
    ├── SKILL.md
    └── config.yaml
```

---

## Deliverables

| Artifact | Location | Description |
|----------|----------|-------------|
| Skill Registry | `src/agents/skills/registry.py` | Core registry implementation |
| Reflection Skill | `skills/reflection/` | Self-critique capability |
| Hallucination Monitor | `skills/hallucination_monitor/` | Detection & logging |
| SKILL.md Template | `docs/skills/SKILL_TEMPLATE.md` | Standard structure |
| Base Skills | `skills/` | retrieval, synthesis |
| Tests | `tests/unit/agents/skills/` | 30+ tests |

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| RAGAS Faithfulness | 80.2% | 88%+ |
| Skill Registry | ❌ None | ✅ Operational |
| Reflection Loop | ❌ None | ✅ Integrated |
| Hallucination Logging | ❌ None | ✅ Active |

---

## References

| Resource | URL |
|----------|-----|
| Anthropic Agent Skills | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview |
| Engineering Blog | https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills |
| Skills GitHub | https://github.com/anthropics/skills |
| Open Standard | https://aibusiness.com/foundation-models/anthropic-launches-skills-open-standard-claude |
| Deep Dive | https://medium.com/aimonks/claude-agent-skills-a-first-principles-deep-dive-into-prompt-based-meta-tools-022de66fc721 |

---

**Document:** SPRINT_90_PLAN.md
**Status:** 📝 Planned
**Created:** 2026-01-13
