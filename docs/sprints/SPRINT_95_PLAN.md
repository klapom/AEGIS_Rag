# Sprint 95 Plan: Hierarchical Agents & Skill Libraries

**Epic:** AegisRAG Agentic Framework Transformation
**Phase:** 6 of 7 (Hierarchy)
**ADR Reference:** [ADR-049](../adr/ADR-049-agentic-framework-architecture.md)
**Prerequisite:** Sprint 94 (Multi-Agent Communication)
**Duration:** 14-18 days
**Total Story Points:** 30 SP
**Status:** 📝 Planned

---

## Sprint Goal

Complete hierarchical agent architecture with Skill Libraries:
1. **Hierarchical Agent Pattern** - Manager/Worker architecture with skill delegation
2. **Skill Libraries & Bundles** - Reusable skill packages
3. **Standard Skill Bundles** - Pre-configured bundles for common use cases
4. **Procedural Memory** - Learning from skill execution history

**Target Outcome:** +50% scalability, reusable skill ecosystem

---

## Research Foundation

> "Statt einen monolithischen Agenten alle Aufgaben sequenziell lösen zu lassen, kann man mehrere spezialisierte Rollen schaffen, die zusammenwirken."
> — AegisRAG_Agentenframework.docx

Key Sources:
- **Anthropic Agent Skills:** [Overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- **Anthropic Skills Repository:** [github.com/anthropics/skills](https://github.com/anthropics/skills)
- **ROME (2025):** Agentic trajectory learning
- **ALE (Alibaba 2025):** Tool creation and learning

---

## Features

| # | Feature | SP | Priority | Status |
|---|---------|-----|----------|--------|
| 95.1 | Hierarchical Agent Pattern | 10 | P0 | 📝 Planned |
| 95.2 | Skill Libraries & Bundles | 8 | P0 | 📝 Planned |
| 95.3 | Standard Skill Bundles | 6 | P1 | 📝 Planned |
| 95.4 | Procedural Memory System | 4 | P1 | 📝 Planned |
| 95.5 | Integration Testing | 2 | P0 | 📝 Planned |

---

## Feature 95.1: Hierarchical Agent Pattern (10 SP)

### Description

Implement Manager/Worker architecture with skill-based delegation.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           Hierarchical Agents + Skill Delegation            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    ┌──────────────┐                         │
│                    │   Executive  │ ← Strategic decisions   │
│                    │   Director   │   Skills: [planner,     │
│                    │              │    orchestrator]        │
│                    └──────┬───────┘                         │
│                           │                                 │
│              ┌────────────┼────────────┐                    │
│              ▼            ▼            ▼                    │
│       ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│       │ Research │ │ Analysis │ │ Synthesis│ ← Task mgmt   │
│       │ Manager  │ │ Manager  │ │ Manager  │   Delegates   │
│       │[research]│ │[analysis]│ │[synthesis]│   to workers  │
│       └────┬─────┘ └────┬─────┘ └────┬─────┘               │
│            │            │            │                      │
│     ┌──────┴──────┐     │     ┌──────┴──────┐              │
│     ▼      ▼      ▼     ▼     ▼      ▼      ▼              │
│   ┌───┐  ┌───┐  ┌───┐ ┌───┐ ┌───┐  ┌───┐  ┌───┐           │
│   │W1 │  │W2 │  │W3 │ │W4 │ │W5 │  │W6 │  │W7 │← Workers  │
│   │ret│  │web│  │grp│ │val│ │sum│  │cit│  │fmt│   Execute │
│   └───┘  └───┘  └───┘ └───┘ └───┘  └───┘  └───┘   skills   │
│                                                             │
│   Skill Delegation:                                         │
│   - Executive has high-level skills (planner, orchestrator) │
│   - Managers have domain skills (research, analysis)        │
│   - Workers have atomic skills (retrieval, summarize)       │
│                                                             │
│   Communication: Top-down delegation, bottom-up reporting   │
│   Context Budget: Flows down hierarchy                      │
└─────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# src/agents/hierarchy/skill_hierarchy.py

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from src.agents.skills.lifecycle import SkillLifecycleManager, SkillState
from src.agents.orchestration.skill_orchestrator import SkillOrchestrator


class AgentLevel(Enum):
    EXECUTIVE = 0    # Strategic decisions, high-level skills
    MANAGER = 1      # Task coordination, domain skills
    WORKER = 2       # Task execution, atomic skills


@dataclass
class SkillTask:
    """Task delegated through hierarchy."""
    id: str
    description: str
    required_skills: List[str]
    context_budget: int
    priority: int
    assigned_to: Optional[str] = None
    parent_task_id: Optional[str] = None
    status: str = "pending"
    result: Any = None
    sub_tasks: List['SkillTask'] = field(default_factory=list)


class HierarchicalSkillAgent(ABC):
    """
    Base class for hierarchical agents with skill support.

    Each level has different skill access:
    - Executive: planner, orchestrator, high-level reasoning
    - Manager: domain-specific skills, coordination
    - Worker: atomic execution skills
    """

    def __init__(
        self,
        agent_id: str,
        level: AgentLevel,
        skill_manager: SkillLifecycleManager,
        available_skills: List[str],
        parent: Optional['HierarchicalSkillAgent'] = None
    ):
        self.agent_id = agent_id
        self.level = level
        self.skills = skill_manager
        self.available_skills = available_skills
        self.parent = parent
        self.children: List['HierarchicalSkillAgent'] = []
        self._active_skills: List[str] = []

    def add_child(self, child: 'HierarchicalSkillAgent'):
        """Add subordinate agent."""
        child.parent = self
        self.children.append(child)

    async def activate_my_skills(self, context_budget: int):
        """Activate this agent's skills with budget."""
        budget_per_skill = context_budget // max(1, len(self.available_skills))

        for skill_name in self.available_skills:
            await self.skills.activate(skill_name, budget_per_skill)
            self._active_skills.append(skill_name)

    async def deactivate_my_skills(self):
        """Deactivate this agent's skills."""
        for skill_name in self._active_skills:
            await self.skills.deactivate(skill_name)
        self._active_skills = []

    async def receive_task(self, task: SkillTask) -> SkillTask:
        """
        Receive task from parent.

        Managers: Decompose and delegate using skills
        Workers: Execute directly using atomic skills
        """
        # Activate skills for this task
        await self.activate_my_skills(task.context_budget)

        try:
            if self.level == AgentLevel.WORKER:
                return await self._execute_with_skills(task)
            else:
                return await self._delegate_with_skills(task)
        finally:
            await self.deactivate_my_skills()

    async def _delegate_with_skills(self, task: SkillTask) -> SkillTask:
        """Decompose and delegate task using manager skills."""
        # Use planner skill if available
        if "planner" in self._active_skills:
            sub_tasks = await self._plan_subtasks(task)
        else:
            sub_tasks = self._simple_decompose(task)

        task.sub_tasks = sub_tasks

        # Assign to children based on required skills
        assignments = self._assign_by_skills(sub_tasks)

        # Execute delegated tasks
        results = await self._execute_delegated(assignments)

        # Aggregate using synthesis skill if available
        if "synthesis" in self._active_skills:
            task.result = await self._synthesize_results(task, results)
        else:
            task.result = self._simple_aggregate(results)

        task.status = "completed"

        # Report to parent
        if self.parent:
            await self.parent.receive_report(task)

        return task

    async def _plan_subtasks(self, task: SkillTask) -> List[SkillTask]:
        """Use planner skill to decompose task."""
        # Get planner skill instructions
        planner_instructions = await self.skills.activate("planner")

        # Plan decomposition (would use LLM with planner instructions)
        # For now, simple decomposition
        return self._simple_decompose(task)

    def _simple_decompose(self, task: SkillTask) -> List[SkillTask]:
        """Simple task decomposition without planner skill."""
        # Default: create one subtask per required skill
        sub_tasks = []
        budget_per_sub = task.context_budget // max(1, len(task.required_skills))

        for i, skill in enumerate(task.required_skills):
            sub_tasks.append(SkillTask(
                id=f"{task.id}_sub_{i}",
                description=f"{task.description} (using {skill})",
                required_skills=[skill],
                context_budget=budget_per_sub,
                priority=task.priority,
                parent_task_id=task.id
            ))

        return sub_tasks

    def _assign_by_skills(
        self,
        sub_tasks: List[SkillTask]
    ) -> Dict[str, List[SkillTask]]:
        """Assign tasks to children based on skill match."""
        assignments = {child.agent_id: [] for child in self.children}

        for task in sub_tasks:
            best_child = self._find_child_with_skills(task.required_skills)
            if best_child:
                task.assigned_to = best_child.agent_id
                assignments[best_child.agent_id].append(task)

        return assignments

    def _find_child_with_skills(
        self,
        required_skills: List[str]
    ) -> Optional['HierarchicalSkillAgent']:
        """Find child that has required skills."""
        for child in self.children:
            if all(s in child.available_skills for s in required_skills):
                return child

        # Fallback: find child with most matching skills
        best_child = None
        best_match = 0
        for child in self.children:
            matches = sum(1 for s in required_skills if s in child.available_skills)
            if matches > best_match:
                best_match = matches
                best_child = child

        return best_child

    async def _execute_delegated(
        self,
        assignments: Dict[str, List[SkillTask]]
    ) -> Dict[str, List[SkillTask]]:
        """Execute delegated tasks."""
        results = {}

        # Parallel execution
        tasks_to_run = []
        for child_id, tasks in assignments.items():
            child = next(c for c in self.children if c.agent_id == child_id)
            for task in tasks:
                tasks_to_run.append((child, task))

        import asyncio
        completed = await asyncio.gather(
            *[child.receive_task(task) for child, task in tasks_to_run],
            return_exceptions=True
        )

        for i, result in enumerate(completed):
            if not isinstance(result, Exception):
                child_id = tasks_to_run[i][1].assigned_to
                if child_id not in results:
                    results[child_id] = []
                results[child_id].append(result)

        return results

    async def _synthesize_results(
        self,
        parent_task: SkillTask,
        child_results: Dict[str, List[SkillTask]]
    ) -> str:
        """Synthesize results using synthesis skill."""
        # Collect all results
        all_results = []
        for tasks in child_results.values():
            for task in tasks:
                if task.result:
                    all_results.append(str(task.result))

        # Use synthesis skill (would invoke LLM with skill instructions)
        return "\n\n".join(all_results)

    def _simple_aggregate(
        self,
        child_results: Dict[str, List[SkillTask]]
    ) -> str:
        """Simple result aggregation."""
        all_results = []
        for tasks in child_results.values():
            for task in tasks:
                if task.result:
                    all_results.append(str(task.result))
        return "\n\n".join(all_results)

    @abstractmethod
    async def _execute_with_skills(self, task: SkillTask) -> SkillTask:
        """Execute task using atomic skills (worker implementation)."""
        pass

    async def receive_report(self, task: SkillTask):
        """Receive completion report from child."""
        pass


class ExecutiveAgent(HierarchicalSkillAgent):
    """Top-level strategic agent with executive skills."""

    def __init__(
        self,
        agent_id: str,
        skill_manager: SkillLifecycleManager,
        orchestrator: SkillOrchestrator
    ):
        super().__init__(
            agent_id,
            AgentLevel.EXECUTIVE,
            skill_manager,
            available_skills=["planner", "orchestrator", "reflection"]
        )
        self.orchestrator = orchestrator

    async def _execute_with_skills(self, task: SkillTask) -> SkillTask:
        """Executives delegate, not execute directly."""
        raise NotImplementedError("Executive agents delegate, not execute")

    async def set_goal(
        self,
        goal: str,
        context_budget: int = 10000
    ) -> SkillTask:
        """Set strategic goal and initiate execution."""
        # Create top-level task
        task = SkillTask(
            id="goal_" + str(uuid.uuid4())[:8],
            description=goal,
            required_skills=["planner", "orchestrator"],
            context_budget=context_budget,
            priority=10
        )

        return await self.receive_task(task)


class ManagerAgent(HierarchicalSkillAgent):
    """Mid-level coordination agent with domain skills."""

    def __init__(
        self,
        agent_id: str,
        domain: str,
        skill_manager: SkillLifecycleManager,
        domain_skills: List[str]
    ):
        super().__init__(
            agent_id,
            AgentLevel.MANAGER,
            skill_manager,
            available_skills=domain_skills
        )
        self.domain = domain

    async def _execute_with_skills(self, task: SkillTask) -> SkillTask:
        """Managers coordinate, not execute directly."""
        return await self._delegate_with_skills(task)


class WorkerAgent(HierarchicalSkillAgent):
    """Leaf-level execution agent with atomic skills."""

    def __init__(
        self,
        agent_id: str,
        skill_manager: SkillLifecycleManager,
        atomic_skills: List[str],
        llm: BaseChatModel
    ):
        super().__init__(
            agent_id,
            AgentLevel.WORKER,
            skill_manager,
            available_skills=atomic_skills
        )
        self.llm = llm

    async def _execute_with_skills(self, task: SkillTask) -> SkillTask:
        """Execute task using atomic skills."""
        try:
            # Get skill instructions for all required skills
            skill_instructions = []
            for skill_name in task.required_skills:
                if skill_name in self._active_skills:
                    instructions = self.skills._loaded_content.get(skill_name, "")
                    skill_instructions.append(instructions)

            combined_instructions = "\n\n".join(skill_instructions)

            # Execute with LLM
            prompt = f"""{combined_instructions}

Task: {task.description}

Execute the task according to the skill instructions above.

Result:"""

            response = await self.llm.ainvoke(prompt)
            task.result = response.content
            task.status = "completed"

        except Exception as e:
            task.status = "failed"
            task.result = str(e)

        return task
```

---

## Feature 95.2: Skill Libraries & Bundles (8 SP)

### Description

Create reusable skill packages for common use cases.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Skill Libraries & Bundles                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  skill_libraries/                                           │
│  │                                                          │
│  ├── core/                    # Core library (always avail) │
│  │   ├── retrieval/           # Vector/Graph/BM25           │
│  │   ├── synthesis/           # Summarization               │
│  │   └── reflection/          # Self-critique               │
│  │                                                          │
│  ├── research/                # Research library            │
│  │   ├── web_search/          # Web search skill            │
│  │   ├── academic/            # Academic search             │
│  │   └── fact_check/          # Fact verification           │
│  │                                                          │
│  ├── analysis/                # Analysis library            │
│  │   ├── data_viz/            # Data visualization          │
│  │   ├── statistics/          # Statistical analysis        │
│  │   └── comparison/          # Comparison skill            │
│  │                                                          │
│  └── bundles/                 # Pre-configured bundles      │
│      ├── research_assistant/  # Bundle: research skills     │
│      ├── data_analyst/        # Bundle: analysis skills     │
│      └── code_reviewer/       # Bundle: code review skills  │
│                                                             │
│  Bundle Definition (BUNDLE.yaml):                            │
│  ```yaml                                                    │
│  name: research_assistant                                   │
│  version: "1.0.0"                                           │
│  skills:                                                    │
│    - core/retrieval                                         │
│    - core/synthesis                                         │
│    - research/web_search                                    │
│    - research/fact_check                                    │
│  context_budget: 8000                                       │
│  dependencies:                                              │
│    - playwright  # For web_search                           │
│  ```                                                        │
└─────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# src/agents/skills/library.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from pathlib import Path
import yaml


@dataclass
class SkillLibrary:
    """Collection of related skills."""
    name: str
    version: str
    description: str
    skills: List[str]
    dependencies: List[str] = field(default_factory=list)
    path: Path = None


@dataclass
class SkillBundle:
    """Pre-configured bundle of skills."""
    name: str
    version: str
    description: str
    skills: List[str]
    context_budget: int
    auto_activate: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


class SkillLibraryManager:
    """
    Manage skill libraries and bundles.

    Features:
    - Discover and load skill libraries
    - Create and manage bundles
    - Resolve dependencies
    - Version compatibility checking
    """

    def __init__(
        self,
        libraries_dir: Path,
        skill_manager: SkillLifecycleManager
    ):
        self.libraries_dir = libraries_dir
        self.skills = skill_manager
        self._libraries: Dict[str, SkillLibrary] = {}
        self._bundles: Dict[str, SkillBundle] = {}
        self._loaded_bundles: Set[str] = set()

    def discover_libraries(self):
        """Discover all skill libraries."""
        for lib_dir in self.libraries_dir.iterdir():
            if lib_dir.is_dir() and lib_dir.name != "bundles":
                library = self._parse_library(lib_dir)
                if library:
                    self._libraries[library.name] = library

        # Discover bundles
        bundles_dir = self.libraries_dir / "bundles"
        if bundles_dir.exists():
            for bundle_dir in bundles_dir.iterdir():
                if bundle_dir.is_dir():
                    bundle = self._parse_bundle(bundle_dir)
                    if bundle:
                        self._bundles[bundle.name] = bundle

    def _parse_library(self, lib_dir: Path) -> Optional[SkillLibrary]:
        """Parse library from directory."""
        lib_yaml = lib_dir / "LIBRARY.yaml"
        if not lib_yaml.exists():
            # Infer library from skill directories
            skills = []
            for skill_dir in lib_dir.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    skills.append(f"{lib_dir.name}/{skill_dir.name}")

            return SkillLibrary(
                name=lib_dir.name,
                version="1.0.0",
                description=f"Library: {lib_dir.name}",
                skills=skills,
                path=lib_dir
            )

        config = yaml.safe_load(lib_yaml.read_text())
        return SkillLibrary(
            name=config.get("name", lib_dir.name),
            version=config.get("version", "1.0.0"),
            description=config.get("description", ""),
            skills=config.get("skills", []),
            dependencies=config.get("dependencies", []),
            path=lib_dir
        )

    def _parse_bundle(self, bundle_dir: Path) -> Optional[SkillBundle]:
        """Parse bundle from directory."""
        bundle_yaml = bundle_dir / "BUNDLE.yaml"
        if not bundle_yaml.exists():
            return None

        config = yaml.safe_load(bundle_yaml.read_text())
        return SkillBundle(
            name=config.get("name", bundle_dir.name),
            version=config.get("version", "1.0.0"),
            description=config.get("description", ""),
            skills=config.get("skills", []),
            context_budget=config.get("context_budget", 5000),
            auto_activate=config.get("auto_activate", []),
            dependencies=config.get("dependencies", [])
        )

    async def load_bundle(
        self,
        bundle_name: str,
        context_budget: Optional[int] = None
    ) -> List[str]:
        """
        Load all skills in a bundle.

        Args:
            bundle_name: Name of bundle to load
            context_budget: Override bundle's default budget

        Returns:
            List of loaded skill names
        """
        bundle = self._bundles.get(bundle_name)
        if not bundle:
            raise ValueError(f"Bundle not found: {bundle_name}")

        budget = context_budget or bundle.context_budget
        budget_per_skill = budget // max(1, len(bundle.skills))

        loaded = []
        for skill_path in bundle.skills:
            # Resolve skill path (library/skill format)
            skill_name = self._resolve_skill_path(skill_path)

            # Load skill
            await self.skills.load(skill_name)
            loaded.append(skill_name)

        # Auto-activate specified skills
        for skill_name in bundle.auto_activate:
            resolved = self._resolve_skill_path(skill_name)
            await self.skills.activate(resolved, budget_per_skill)

        self._loaded_bundles.add(bundle_name)
        return loaded

    async def unload_bundle(self, bundle_name: str):
        """Unload all skills in a bundle."""
        bundle = self._bundles.get(bundle_name)
        if not bundle:
            return

        for skill_path in bundle.skills:
            skill_name = self._resolve_skill_path(skill_path)
            await self.skills.unload(skill_name)

        self._loaded_bundles.discard(bundle_name)

    def _resolve_skill_path(self, skill_path: str) -> str:
        """Resolve library/skill path to skill name."""
        if "/" in skill_path:
            parts = skill_path.split("/")
            return parts[-1]  # Return just skill name
        return skill_path

    def get_library_skills(self, library_name: str) -> List[str]:
        """Get all skills in a library."""
        library = self._libraries.get(library_name)
        return library.skills if library else []

    def get_bundle_skills(self, bundle_name: str) -> List[str]:
        """Get all skills in a bundle."""
        bundle = self._bundles.get(bundle_name)
        return bundle.skills if bundle else []

    def create_bundle(
        self,
        name: str,
        skills: List[str],
        context_budget: int = 5000,
        description: str = ""
    ) -> SkillBundle:
        """Create a new bundle dynamically."""
        bundle = SkillBundle(
            name=name,
            version="1.0.0",
            description=description,
            skills=skills,
            context_budget=context_budget
        )
        self._bundles[name] = bundle
        return bundle
```

---

## Feature 95.3: Standard Skill Bundles (6 SP)

### Description

Pre-configured bundles for common use cases.

```yaml
# skill_libraries/bundles/research_assistant/BUNDLE.yaml
name: research_assistant
version: "1.0.0"
description: Complete research workflow bundle

skills:
  - core/retrieval
  - core/synthesis
  - core/reflection
  - research/web_search
  - research/academic
  - research/fact_check

context_budget: 8000
auto_activate:
  - retrieval
  - synthesis

triggers:
  - "research"
  - "find information"
  - "investigate"
  - "look up"

permissions:
  tools:
    - browser
    - web_fetch
    - search_api

dependencies:
  - playwright
```

```yaml
# skill_libraries/bundles/data_analyst/BUNDLE.yaml
name: data_analyst
version: "1.0.0"
description: Data analysis and visualization bundle

skills:
  - core/retrieval
  - analysis/statistics
  - analysis/data_viz
  - analysis/comparison
  - core/synthesis

context_budget: 6000
auto_activate:
  - statistics
  - synthesis

triggers:
  - "analyze"
  - "visualize"
  - "compare"
  - "statistics"

permissions:
  tools:
    - python_exec
    - file_read
```

```yaml
# skill_libraries/bundles/code_reviewer/BUNDLE.yaml
name: code_reviewer
version: "1.0.0"
description: Code review and quality analysis bundle

skills:
  - coding/review
  - coding/security
  - coding/performance
  - core/reflection
  - core/synthesis

context_budget: 7000
auto_activate:
  - review
  - security

triggers:
  - "review code"
  - "check security"
  - "analyze performance"
  - "code quality"

permissions:
  tools:
    - code_search
    - static_analysis
```

---

## Feature 95.4: Procedural Memory System (4 SP)

### Description

Learn from skill execution history to improve future performance.

```python
# src/agents/memory/skill_procedural.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime


@dataclass
class SkillExecutionTrace:
    """Record of skill execution."""
    id: str
    skill_name: str
    bundle_used: Optional[str]
    query: str
    inputs: Dict[str, Any]
    output: str
    success: bool
    duration_ms: float
    context_used: int
    user_feedback: Optional[float] = None  # 1-5 rating
    timestamp: datetime = field(default_factory=datetime.now)


class SkillProceduralMemory:
    """
    Learn from skill executions to improve future performance.

    Features:
    - Track skill success patterns
    - Recommend bundles for queries
    - Optimize context allocation
    - Learn skill sequences
    """

    def __init__(
        self,
        storage: VectorStore,
        embedding_model: Embeddings
    ):
        self.storage = storage
        self.embeddings = embedding_model
        self._skill_success_rates: Dict[str, float] = {}
        self._bundle_success_rates: Dict[str, float] = {}
        self._skill_sequences: Dict[str, List[str]] = {}

    async def record(self, trace: SkillExecutionTrace):
        """Record skill execution trace."""
        # Store for similarity search
        embedding = await self.embeddings.aembed_query(trace.query)

        await self.storage.add_documents([
            Document(
                page_content=trace.query,
                metadata={
                    "trace_id": trace.id,
                    "skill": trace.skill_name,
                    "bundle": trace.bundle_used,
                    "success": trace.success,
                    "duration": trace.duration_ms,
                    "feedback": trace.user_feedback
                }
            )
        ])

        # Update success rates
        self._update_success_rate(
            trace.skill_name,
            trace.success,
            self._skill_success_rates
        )

        if trace.bundle_used:
            self._update_success_rate(
                trace.bundle_used,
                trace.success,
                self._bundle_success_rates
            )

    def _update_success_rate(
        self,
        key: str,
        success: bool,
        rates: Dict[str, float]
    ):
        """Update success rate using exponential moving average."""
        current = rates.get(key, 0.5)
        rates[key] = 0.9 * current + 0.1 * (1.0 if success else 0.0)

    async def suggest_bundle(
        self,
        query: str,
        available_bundles: List[str]
    ) -> Optional[str]:
        """
        Suggest best bundle for query based on history.

        Args:
            query: User's query
            available_bundles: Bundles that can be used

        Returns:
            Recommended bundle name
        """
        # Find similar past queries
        similar = await self.storage.similarity_search(query, k=5)

        # Score bundles
        bundle_scores: Dict[str, float] = {}

        for doc in similar:
            bundle = doc.metadata.get("bundle")
            if bundle and bundle in available_bundles:
                success = doc.metadata.get("success", False)
                feedback = doc.metadata.get("feedback", 3)

                score = (1.0 if success else 0.0) + (feedback / 5.0)
                bundle_scores[bundle] = bundle_scores.get(bundle, 0) + score

        # Add base success rates
        for bundle in available_bundles:
            base_rate = self._bundle_success_rates.get(bundle, 0.5)
            bundle_scores[bundle] = bundle_scores.get(bundle, 0) + base_rate

        if bundle_scores:
            return max(bundle_scores, key=bundle_scores.get)

        return None

    async def suggest_context_budget(
        self,
        skill_name: str,
        query: str
    ) -> int:
        """Suggest context budget based on past executions."""
        similar = await self.storage.similarity_search(
            query,
            k=3,
            filter={"skill": skill_name}
        )

        if not similar:
            return 2000  # Default

        # Average context used in successful executions
        successful_contexts = [
            doc.metadata.get("context_used", 2000)
            for doc in similar
            if doc.metadata.get("success", False)
        ]

        if successful_contexts:
            return int(sum(successful_contexts) / len(successful_contexts))

        return 2000

    def get_skill_success_rate(self, skill_name: str) -> float:
        """Get historical success rate for skill."""
        return self._skill_success_rates.get(skill_name, 0.5)

    def get_bundle_success_rate(self, bundle_name: str) -> float:
        """Get historical success rate for bundle."""
        return self._bundle_success_rates.get(bundle_name, 0.5)
```

---

## Deliverables

| Artifact | Location | Description |
|----------|----------|-------------|
| Hierarchical Agents | `src/agents/hierarchy/skill_hierarchy.py` | Manager/Worker with skills |
| Skill Libraries | `src/agents/skills/library.py` | Library management |
| Standard Bundles | `skill_libraries/bundles/` | Pre-configured bundles |
| Procedural Memory | `src/agents/memory/skill_procedural.py` | Execution learning |
| Tests | `tests/integration/test_agentic_framework.py` | E2E tests |

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Hierarchical Agents | ❌ Flat | ✅ 3-level with skills |
| Skill Libraries | ❌ None | ✅ Core, Research, Analysis |
| Standard Bundles | ❌ None | ✅ 3+ bundles |
| Procedural Memory | ❌ None | ✅ Learning |
| Scalability | Baseline | +50% |

---

## Sprint 90-95 Summary

| Sprint | Focus | Key Deliverables | Impact |
|--------|-------|------------------|--------|
| **90** | Foundation | Skill Registry, Reflection, Hallucination | Faithfulness +8% |
| **91** | Routing | Intent Router, Permission Engine | Skill activation |
| **92** | Context | Recursive LLM, Skill Lifecycle | 10x context |
| **93** | Tools | Skill-Tool Mapping, Browser | +40% automation |
| **94** | Communication | Orchestrator, Messaging, Blackboard | +20% coordination |
| **95** | Hierarchy | Agent Hierarchy, Skill Libraries | +50% scalability |

**Total Transformation:** AegisRAG evolves from RAG to Skill-based Agentic Framework

---

**Document:** SPRINT_95_PLAN.md
**Status:** 📝 Planned
**Created:** 2026-01-13
**Updated:** 2026-01-13 (Agent Skills Integration)
