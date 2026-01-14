# Sprint 94 Plan: Multi-Agent Communication & Skill Orchestration

**Epic:** AegisRAG Agentic Framework Transformation
**Phase:** 5 of 7 (Communication)
**ADR Reference:** [ADR-049](../adr/ADR-049-agentic-framework-architecture.md)
**Prerequisite:** Sprint 93 (Tool Composition & Skill-Tool Mapping)
**Duration:** 14-18 days
**Total Story Points:** 32 SP
**Status:** 📝 Planned

---

## Sprint Goal

Enable **inter-agent communication** with Skill Orchestration:
1. **Agent Messaging Bus** - Direct agent-to-agent communication
2. **Shared Memory Protocol** - Collaborative knowledge sharing via skills
3. **Skill Orchestrator** - Coordinate multiple skills in complex workflows
4. **RISE Integration** - Reasoning behavior control via SAE

**Target Outcome:** +20% coordination efficiency, multi-skill workflows

---

## Research Foundation

> "Die Memory-Komponente fungiert als zentrales Board, auf dem Agenten Teilergebnisse ablegen und von dem sie bei Bedarf lesen. Der Coordinator-Agent könnte einen Planer darstellen, der Aufgaben an spezialisierte Unter-Agenten delegiert."
> — AegisRAG_Agentenframework.docx

> "RISE (Reasoning behavior Interpretability via Sparse auto-Encoder) von Google DeepMind identifiziert latente Dimensionen für solche Denkverhalten und erlaubt es, sie gezielt zu verstärken oder abzuschwächen."
> — AegisRAG_Agentenframework.docx

Key Sources:
- **Anthropic Agent Skills:** [Overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- **RISE (Zhang et al. 2025):** Sparse autoencoder for reasoning control
- **RCR-Router (Liu et al. 2025):** Role-aware routing

---

## Features

| # | Feature | SP | Priority | Status |
|---|---------|-----|----------|--------|
| 94.1 | Agent Messaging Bus | 8 | P0 | 📝 Planned |
| 94.2 | Shared Memory Protocol | 8 | P0 | 📝 Planned |
| 94.3 | Skill Orchestrator | 10 | P0 | 📝 Planned |
| 94.4 | RISE Reasoning Control | 6 | P1 | 📝 Planned |

---

## Feature 94.1: Agent Messaging Bus (8 SP)

### Description

Enable direct communication between agents through a message bus that respects skill boundaries.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│           Agent Messaging + Skill Orchestration              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐         Message Bus         ┌────────────┐ │
│  │ VectorAgent │◀─────────────────────────▶│ GraphAgent │  │
│  │ (retrieval) │      │           │        │ (graph_q)  │  │
│  └─────────────┘      │           │        └────────────┘  │
│         │             │           │              │          │
│         ▼             ▼           ▼              ▼          │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                  Skill-Aware Message Queue              ││
│  │  Types: [SkillRequest, SkillResponse, Broadcast, Query] ││
│  │  Routing: Based on skill dependencies                   ││
│  └─────────────────────────────────────────────────────────┘│
│         │             │           │              │          │
│         ▼             ▼           ▼              ▼          │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐ │
│  │MemoryAgent│ │ActionAgent │ │Orchestrator│ │Synthesiz │ │
│  │ (memory)  │ │ (action)   │ │ (skills)   │ │(synthesis)│ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────┘ │
│                                                             │
│  Skill Context Flow:                                        │
│  - Messages carry skill_context (which skill originated)   │
│  - Receiving agent can load required skills                 │
│  - Skill permissions checked before message delivery        │
└─────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# src/agents/communication/skill_messaging.py

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from enum import Enum
import asyncio
from datetime import datetime
import uuid

from src.agents.skills.lifecycle import SkillLifecycleManager, SkillState


class MessageType(Enum):
    SKILL_REQUEST = "skill_request"    # Request skill execution
    SKILL_RESPONSE = "skill_response"  # Response from skill
    BROADCAST = "broadcast"            # Notify all agents
    QUERY = "query"                    # Ask for information
    HANDOFF = "handoff"                # Hand task to another agent/skill


class MessagePriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


@dataclass
class SkillContext:
    """Context about skill that originated message."""
    skill_name: str
    skill_version: str
    permissions: List[str]
    context_tokens_used: int = 0


@dataclass
class AgentMessage:
    """Message between agents with skill context."""
    id: str
    type: MessageType
    sender: str
    recipient: str  # "*" for broadcast
    content: Dict[str, Any]
    skill_context: Optional[SkillContext] = None
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    ttl: int = 60  # Time-to-live in seconds
    requires_skills: List[str] = field(default_factory=list)


class SkillAwareMessageBus:
    """
    Message bus that respects skill boundaries.

    Features:
    - Skill-aware routing
    - Auto-load required skills
    - Permission checking
    - Context budget tracking
    """

    def __init__(
        self,
        skill_manager: SkillLifecycleManager
    ):
        self.skills = skill_manager
        self._queues: Dict[str, asyncio.Queue] = {}
        self._handlers: Dict[str, Callable] = {}
        self._subscriptions: Dict[str, List[str]] = {}
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._skill_dependencies: Dict[str, List[str]] = {}

    def register_agent(
        self,
        agent_id: str,
        handler: Callable,
        required_skills: List[str] = None
    ):
        """Register agent with its required skills."""
        self._queues[agent_id] = asyncio.Queue()
        self._handlers[agent_id] = handler
        if required_skills:
            self._skill_dependencies[agent_id] = required_skills

    async def send(self, message: AgentMessage) -> Optional[str]:
        """
        Send message with skill-aware routing.

        Auto-loads required skills at recipient before delivery.
        """
        if not message.id:
            message.id = str(uuid.uuid4())

        if message.recipient == "*":
            # Broadcast to all
            for agent_id in self._queues:
                if agent_id != message.sender:
                    await self._deliver(agent_id, message)
        else:
            await self._deliver(message.recipient, message)

        return message.id

    async def _deliver(
        self,
        recipient: str,
        message: AgentMessage
    ):
        """Deliver message, ensuring skills are loaded."""
        if recipient not in self._queues:
            raise ValueError(f"Unknown recipient: {recipient}")

        # Load required skills at recipient
        for skill in message.requires_skills:
            state = self.skills.get_state(skill)
            if state not in [SkillState.LOADED, SkillState.ACTIVE]:
                await self.skills.load(skill)

        # Also load agent's default skills
        agent_skills = self._skill_dependencies.get(recipient, [])
        for skill in agent_skills:
            state = self.skills.get_state(skill)
            if state not in [SkillState.LOADED, SkillState.ACTIVE]:
                await self.skills.load(skill)

        await self._queues[recipient].put(message)

    async def request_skill(
        self,
        sender: str,
        skill_name: str,
        action: str,
        inputs: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[Dict]:
        """
        Request a skill to be executed by any capable agent.

        Finds an agent that has the skill and routes request to it.
        """
        # Find agent with this skill
        target_agent = None
        for agent_id, skills in self._skill_dependencies.items():
            if skill_name in skills:
                target_agent = agent_id
                break

        if not target_agent:
            raise ValueError(f"No agent registered for skill: {skill_name}")

        # Create message
        correlation_id = str(uuid.uuid4())
        message = AgentMessage(
            id=str(uuid.uuid4()),
            type=MessageType.SKILL_REQUEST,
            sender=sender,
            recipient=target_agent,
            content={"action": action, "inputs": inputs},
            requires_skills=[skill_name],
            correlation_id=correlation_id,
            skill_context=SkillContext(
                skill_name=skill_name,
                skill_version="1.0.0",
                permissions=[]
            )
        )

        # Setup response future
        response_future = asyncio.Future()
        self._pending_responses[correlation_id] = response_future

        # Send
        await self.send(message)

        # Wait for response
        try:
            response = await asyncio.wait_for(response_future, timeout=timeout)
            return response.content
        except asyncio.TimeoutError:
            return None
        finally:
            self._pending_responses.pop(correlation_id, None)

    async def respond(
        self,
        original: AgentMessage,
        sender: str,
        content: Dict[str, Any]
    ):
        """Send response to a skill request."""
        response = AgentMessage(
            id=str(uuid.uuid4()),
            type=MessageType.SKILL_RESPONSE,
            sender=sender,
            recipient=original.sender,
            content=content,
            correlation_id=original.correlation_id,
            skill_context=original.skill_context
        )

        if original.correlation_id in self._pending_responses:
            self._pending_responses[original.correlation_id].set_result(response)
        else:
            await self.send(response)

    async def handoff(
        self,
        sender: str,
        target_skill: str,
        task: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Hand off task to another skill.

        Used for skill-to-skill delegation.
        """
        message = AgentMessage(
            id=str(uuid.uuid4()),
            type=MessageType.HANDOFF,
            sender=sender,
            recipient="*",  # Will be routed to appropriate agent
            content={
                "task": task,
                "context": context
            },
            requires_skills=[target_skill],
            skill_context=SkillContext(
                skill_name=target_skill,
                skill_version="1.0.0",
                permissions=[]
            )
        )

        return await self.send(message)
```

---

## Feature 94.2: Shared Memory Protocol (8 SP)

### Description

Collaborative knowledge sharing between skills via shared blackboard.

```python
# src/agents/communication/skill_blackboard.py

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime

from src.agents.skills.lifecycle import SkillLifecycleManager


@dataclass
class BlackboardEntry:
    """Entry on the shared blackboard."""
    key: str
    value: Any
    skill_author: str  # Which skill wrote this
    author_agent: str  # Which agent
    timestamp: datetime
    confidence: float = 1.0
    expires_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    read_permissions: List[str] = field(default_factory=list)  # Skills that can read


class SkillBlackboard:
    """
    Shared knowledge space for skills.

    Skills can:
    - Post findings and hypotheses
    - Read others' contributions (with permission)
    - Subscribe to skill-specific updates
    """

    def __init__(self, skill_manager: SkillLifecycleManager):
        self.skills = skill_manager
        self._entries: Dict[str, BlackboardEntry] = {}
        self._subscribers: Dict[str, List[Callable]] = {}
        self._history: List[BlackboardEntry] = []
        self._skill_namespaces: Dict[str, Dict[str, Any]] = {}

    async def post(
        self,
        key: str,
        value: Any,
        skill_name: str,
        agent_id: str,
        confidence: float = 1.0,
        tags: List[str] = None,
        readable_by: List[str] = None
    ):
        """
        Post entry to blackboard.

        Args:
            key: Entry key
            value: Entry value
            skill_name: Skill that's posting
            agent_id: Agent that's posting
            confidence: Confidence score 0-1
            tags: Optional tags for filtering
            readable_by: Skills that can read (None = all)
        """
        # Verify skill is active
        state = self.skills.get_state(skill_name)
        if state not in [SkillState.ACTIVE, SkillState.LOADED]:
            raise PermissionError(f"Skill '{skill_name}' not active")

        entry = BlackboardEntry(
            key=f"{skill_name}:{key}",  # Namespace by skill
            value=value,
            skill_author=skill_name,
            author_agent=agent_id,
            timestamp=datetime.now(),
            confidence=confidence,
            tags=tags or [],
            read_permissions=readable_by or []  # Empty = public
        )

        old_entry = self._entries.get(entry.key)
        self._entries[entry.key] = entry
        self._history.append(entry)

        # Update skill namespace
        if skill_name not in self._skill_namespaces:
            self._skill_namespaces[skill_name] = {}
        self._skill_namespaces[skill_name][key] = value

        # Notify subscribers
        await self._notify(entry.key, entry, old_entry)

    async def read(
        self,
        key: str,
        skill_name: str,
        from_skill: Optional[str] = None,
        min_confidence: float = 0.0
    ) -> Optional[Any]:
        """
        Read entry from blackboard.

        Args:
            key: Entry key
            skill_name: Skill that's reading
            from_skill: Optional specific skill namespace to read from
            min_confidence: Minimum confidence threshold
        """
        # Build full key
        if from_skill:
            full_key = f"{from_skill}:{key}"
        else:
            full_key = f"{skill_name}:{key}"

        entry = self._entries.get(full_key)

        if not entry:
            return None

        # Check confidence
        if entry.confidence < min_confidence:
            return None

        # Check read permissions
        if entry.read_permissions:
            if skill_name not in entry.read_permissions:
                return None

        return entry.value

    async def query(
        self,
        skill_name: str,
        tags: List[str] = None,
        from_skill: str = None,
        min_confidence: float = 0.0
    ) -> List[BlackboardEntry]:
        """
        Query entries by criteria.

        Args:
            skill_name: Skill making query (for permission check)
            tags: Filter by tags
            from_skill: Filter by author skill
            min_confidence: Minimum confidence
        """
        results = []
        for entry in self._entries.values():
            # Check confidence
            if entry.confidence < min_confidence:
                continue

            # Check permissions
            if entry.read_permissions and skill_name not in entry.read_permissions:
                continue

            # Check author filter
            if from_skill and entry.skill_author != from_skill:
                continue

            # Check tags filter
            if tags and not any(t in entry.tags for t in tags):
                continue

            results.append(entry)

        return results

    def get_skill_namespace(self, skill_name: str) -> Dict[str, Any]:
        """Get all entries from a skill's namespace."""
        return dict(self._skill_namespaces.get(skill_name, {}))

    def subscribe(
        self,
        pattern: str,
        callback: Callable,
        skill_filter: Optional[str] = None
    ):
        """
        Subscribe to changes matching pattern.

        Args:
            pattern: Key pattern (* for wildcard)
            callback: Async callback function
            skill_filter: Only notify for entries from this skill
        """
        sub_key = f"{skill_filter or '*'}:{pattern}"
        if sub_key not in self._subscribers:
            self._subscribers[sub_key] = []
        self._subscribers[sub_key].append(callback)

    async def _notify(
        self,
        key: str,
        entry: BlackboardEntry,
        old_entry: Optional[BlackboardEntry]
    ):
        """Notify subscribers of change."""
        for pattern, callbacks in self._subscribers.items():
            skill_filter, key_pattern = pattern.split(':', 1)

            # Check skill filter
            if skill_filter != '*' and skill_filter != entry.skill_author:
                continue

            # Check key pattern
            if key_pattern != '*' and not key.endswith(key_pattern):
                continue

            for callback in callbacks:
                await callback(key, entry, old_entry)
```

---

## Feature 94.3: Skill Orchestrator (10 SP)

### Description

Coordinate multiple skills in complex workflows.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Skill Orchestrator                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User Query: "Research quantum computing companies and      │
│               analyze their patent portfolios"              │
│                                                             │
│  Orchestration Plan:                                        │
│                                                             │
│  Phase 1: Research (parallel)                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │web_search  │  │ retrieval  │  │ graph_query│            │
│  │   skill    │  │   skill    │  │   skill    │            │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘            │
│        │               │               │                    │
│        └───────────────┼───────────────┘                    │
│                        ▼                                    │
│  Phase 2: Aggregation                                       │
│  ┌─────────────────────────────────────────┐               │
│  │           synthesis skill               │               │
│  │  - Merge results from Phase 1           │               │
│  │  - Deduplicate entities                 │               │
│  └─────────────────────────────────────────┘               │
│                        │                                    │
│                        ▼                                    │
│  Phase 3: Analysis (sequential)                            │
│  ┌────────────┐  →  ┌────────────┐  →  ┌────────────┐      │
│  │ reflection │     │patent_anal │     │ summarize  │      │
│  │   skill    │     │   skill    │     │   skill    │      │
│  └────────────┘     └────────────┘     └────────────┘      │
│                                                             │
│  Context Budget: 10000 tokens total                         │
│  - Phase 1: 3000 (1000 each)                               │
│  - Phase 2: 2000                                           │
│  - Phase 3: 5000                                           │
└─────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# src/agents/orchestration/skill_orchestrator.py

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import asyncio

from src.agents.skills.lifecycle import SkillLifecycleManager
from src.agents.communication.skill_blackboard import SkillBlackboard
from src.agents.communication.skill_messaging import SkillAwareMessageBus


class PhaseType(Enum):
    PARALLEL = "parallel"      # Execute skills in parallel
    SEQUENTIAL = "sequential"  # Execute skills in sequence
    CONDITIONAL = "conditional"  # Execute based on condition


@dataclass
class SkillInvocation:
    """Single skill invocation in orchestration."""
    skill_name: str
    action: str
    inputs: Dict[str, Any]
    output_key: str
    context_budget: int = 2000
    timeout: float = 30.0
    optional: bool = False  # Continue if fails


@dataclass
class OrchestrationPhase:
    """Phase in orchestration plan."""
    name: str
    type: PhaseType
    skills: List[SkillInvocation]
    condition: Optional[str] = None  # For conditional phases


@dataclass
class OrchestrationPlan:
    """Complete orchestration plan."""
    id: str
    phases: List[OrchestrationPhase]
    context_budget: int = 10000
    max_duration: float = 120.0


@dataclass
class OrchestrationResult:
    """Result of orchestration."""
    plan_id: str
    success: bool
    outputs: Dict[str, Any]
    phase_results: List[Dict]
    total_duration: float
    context_used: int
    errors: List[str] = field(default_factory=list)


class SkillOrchestrator:
    """
    Orchestrate multiple skills in complex workflows.

    Features:
    - Parallel and sequential execution
    - Context budget management
    - Cross-skill data passing
    - Error handling and recovery
    """

    def __init__(
        self,
        skill_manager: SkillLifecycleManager,
        blackboard: SkillBlackboard,
        message_bus: SkillAwareMessageBus,
        llm: BaseChatModel
    ):
        self.skills = skill_manager
        self.blackboard = blackboard
        self.bus = message_bus
        self.llm = llm

    async def execute_plan(
        self,
        plan: OrchestrationPlan,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> OrchestrationResult:
        """
        Execute orchestration plan.

        Args:
            plan: OrchestrationPlan to execute
            initial_context: Starting context

        Returns:
            OrchestrationResult with all outputs
        """
        import time
        start_time = time.time()

        context = initial_context or {}
        phase_results = []
        errors = []
        total_context_used = 0

        for phase in plan.phases:
            # Check condition for conditional phases
            if phase.type == PhaseType.CONDITIONAL:
                if not self._evaluate_condition(phase.condition, context):
                    phase_results.append({
                        "phase": phase.name,
                        "skipped": True,
                        "reason": "condition not met"
                    })
                    continue

            # Execute phase
            phase_result = await self._execute_phase(
                phase, context, plan.context_budget - total_context_used
            )

            phase_results.append(phase_result)

            # Merge outputs into context
            context.update(phase_result.get("outputs", {}))
            total_context_used += phase_result.get("context_used", 0)
            errors.extend(phase_result.get("errors", []))

            # Check if should abort
            if phase_result.get("failed") and not phase.skills[0].optional:
                break

        total_duration = time.time() - start_time

        return OrchestrationResult(
            plan_id=plan.id,
            success=len(errors) == 0,
            outputs=context,
            phase_results=phase_results,
            total_duration=total_duration,
            context_used=total_context_used,
            errors=errors
        )

    async def _execute_phase(
        self,
        phase: OrchestrationPhase,
        context: Dict[str, Any],
        available_budget: int
    ) -> Dict:
        """Execute single phase."""
        if phase.type == PhaseType.PARALLEL:
            return await self._execute_parallel(phase, context, available_budget)
        else:
            return await self._execute_sequential(phase, context, available_budget)

    async def _execute_parallel(
        self,
        phase: OrchestrationPhase,
        context: Dict[str, Any],
        available_budget: int
    ) -> Dict:
        """Execute skills in parallel."""
        tasks = []
        for skill_inv in phase.skills:
            # Resolve inputs from context
            resolved_inputs = self._resolve_inputs(skill_inv.inputs, context)

            # Create task
            task = self._execute_skill(
                skill_inv,
                resolved_inputs,
                min(skill_inv.context_budget, available_budget // len(phase.skills))
            )
            tasks.append(task)

        # Run in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect outputs
        outputs = {}
        errors = []
        context_used = 0

        for i, result in enumerate(results):
            skill_name = phase.skills[i].skill_name
            output_key = phase.skills[i].output_key

            if isinstance(result, Exception):
                errors.append(f"{skill_name}: {str(result)}")
            else:
                outputs[output_key] = result.get("output")
                context_used += result.get("context_used", 0)

        return {
            "phase": phase.name,
            "outputs": outputs,
            "errors": errors,
            "context_used": context_used,
            "failed": len(errors) > 0
        }

    async def _execute_sequential(
        self,
        phase: OrchestrationPhase,
        context: Dict[str, Any],
        available_budget: int
    ) -> Dict:
        """Execute skills sequentially."""
        outputs = {}
        errors = []
        context_used = 0
        remaining_budget = available_budget

        for skill_inv in phase.skills:
            # Resolve inputs (including outputs from prior skills)
            resolved_inputs = self._resolve_inputs(
                skill_inv.inputs,
                {**context, **outputs}
            )

            try:
                result = await self._execute_skill(
                    skill_inv,
                    resolved_inputs,
                    min(skill_inv.context_budget, remaining_budget)
                )

                outputs[skill_inv.output_key] = result.get("output")
                used = result.get("context_used", 0)
                context_used += used
                remaining_budget -= used

            except Exception as e:
                errors.append(f"{skill_inv.skill_name}: {str(e)}")
                if not skill_inv.optional:
                    break

        return {
            "phase": phase.name,
            "outputs": outputs,
            "errors": errors,
            "context_used": context_used,
            "failed": len(errors) > 0
        }

    async def _execute_skill(
        self,
        invocation: SkillInvocation,
        inputs: Dict[str, Any],
        budget: int
    ) -> Dict:
        """Execute single skill invocation."""
        # Activate skill with budget
        instructions = await self.skills.activate(
            invocation.skill_name,
            context_allocation=budget
        )

        # Use message bus to request execution
        result = await self.bus.request_skill(
            sender="orchestrator",
            skill_name=invocation.skill_name,
            action=invocation.action,
            inputs=inputs,
            timeout=invocation.timeout
        )

        # Deactivate to free context
        await self.skills.deactivate(invocation.skill_name)

        return {
            "output": result,
            "context_used": budget
        }

    def _resolve_inputs(
        self,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve input references from context."""
        resolved = {}
        for key, value in inputs.items():
            if isinstance(value, str) and value.startswith('$'):
                ref = value[1:]
                parts = ref.split('.')
                result = context
                for part in parts:
                    if isinstance(result, dict):
                        result = result.get(part)
                    else:
                        result = getattr(result, part, None)
                resolved[key] = result
            else:
                resolved[key] = value
        return resolved

    def _evaluate_condition(
        self,
        condition: str,
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate condition string against context."""
        # Simple evaluation - could be expanded
        try:
            return eval(condition, {"__builtins__": {}}, context)
        except:
            return False

    async def plan_orchestration(
        self,
        request: str,
        available_skills: List[str]
    ) -> OrchestrationPlan:
        """
        Use LLM to plan orchestration for complex request.

        Args:
            request: User's complex request
            available_skills: Skills that can be used

        Returns:
            OrchestrationPlan
        """
        skill_docs = await self._get_skill_docs(available_skills)

        prompt = f"""Plan an orchestration of skills for this request.

Request: {request}

Available Skills:
{skill_docs}

Create a multi-phase plan:
- Use PARALLEL for independent operations
- Use SEQUENTIAL for dependent operations
- Specify inputs using $variable references

Output JSON:
{{
  "phases": [
    {{
      "name": "phase_name",
      "type": "parallel|sequential",
      "skills": [
        {{
          "skill": "skill_name",
          "action": "action_name",
          "inputs": {{"key": "value or $ref"}},
          "output_key": "result_name"
        }}
      ]
    }}
  ]
}}

Plan:"""

        response = await self.llm.ainvoke(prompt)
        return self._parse_plan(response.content)
```

---

## Feature 94.4: RISE Reasoning Control (6 SP)

### Description

Integrate RISE (Reasoning behavior Interpretability via Sparse auto-Encoder) for controlling reasoning behaviors within skill execution.

```python
# src/agents/reasoning/skill_rise.py

from dataclasses import dataclass
from typing import Dict, Optional
import torch

from src.agents.skills.lifecycle import SkillLifecycleManager


@dataclass
class ReasoningProfile:
    """Profile of reasoning behavior strengths."""
    reflection: float = 0.0     # Self-checking
    backtracking: float = 0.0   # Abandoning wrong paths
    confidence: float = 0.0     # Certainty in responses
    exploration: float = 0.0    # Trying alternatives
    verification: float = 0.0   # Fact-checking


class SkillRISEController:
    """
    Control reasoning behaviors per skill.

    Different skills may need different reasoning profiles:
    - reflection skill: high reflection, verification
    - creative skill: high exploration, low backtracking
    - retrieval skill: high confidence, low exploration
    """

    # Default profiles per skill type
    SKILL_PROFILES = {
        "reflection": ReasoningProfile(reflection=0.8, verification=0.7),
        "retrieval": ReasoningProfile(confidence=0.6, exploration=0.2),
        "synthesis": ReasoningProfile(exploration=0.4, reflection=0.3),
        "planner": ReasoningProfile(exploration=0.6, backtracking=0.5),
        "research": ReasoningProfile(exploration=0.7, verification=0.6),
    }

    def __init__(
        self,
        skill_manager: SkillLifecycleManager,
        sae_model: Optional[torch.nn.Module] = None
    ):
        self.skills = skill_manager
        self.sae = sae_model
        self._active_profiles: Dict[str, ReasoningProfile] = {}

    def get_profile_for_skill(
        self,
        skill_name: str
    ) -> ReasoningProfile:
        """Get reasoning profile for skill."""
        # Check if custom profile set
        if skill_name in self._active_profiles:
            return self._active_profiles[skill_name]

        # Check default profiles
        for skill_type, profile in self.SKILL_PROFILES.items():
            if skill_type in skill_name:
                return profile

        # Default neutral profile
        return ReasoningProfile()

    def set_profile(
        self,
        skill_name: str,
        profile: ReasoningProfile
    ):
        """Set custom reasoning profile for skill."""
        self._active_profiles[skill_name] = profile

    def get_behavior_adjustments(
        self,
        skill_name: str
    ) -> Dict[str, float]:
        """
        Get behavior adjustments for RISE.

        Returns dict of {behavior: adjustment} for SAE modulation.
        """
        profile = self.get_profile_for_skill(skill_name)

        return {
            "reflection": profile.reflection,
            "backtracking": profile.backtracking,
            "confidence": profile.confidence,
            "exploration": profile.exploration,
            "verification": profile.verification,
        }

    async def enhance_skill_output(
        self,
        skill_name: str,
        output: str,
        context: Dict
    ) -> str:
        """
        Enhance skill output based on reasoning profile.

        For skills with high reflection, trigger reflection loop.
        For skills with high verification, trigger fact-checking.
        """
        profile = self.get_profile_for_skill(skill_name)

        # High reflection: add self-critique
        if profile.reflection > 0.5:
            output = await self._add_reflection(output, context)

        # High verification: add fact-checks
        if profile.verification > 0.5:
            output = await self._add_verification(output, context)

        return output
```

---

## Deliverables

| Artifact | Location | Description |
|----------|----------|-------------|
| Skill Message Bus | `src/agents/communication/skill_messaging.py` | Skill-aware messaging |
| Skill Blackboard | `src/agents/communication/skill_blackboard.py` | Shared memory |
| Orchestrator | `src/agents/orchestration/skill_orchestrator.py` | Multi-skill workflows |
| RISE Integration | `src/agents/reasoning/skill_rise.py` | Behavior control per skill |
| Tests | `tests/unit/agents/communication/` | 35+ tests |

---

## Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Agent Coordination | State-only | Full messaging |
| Cross-Skill Data | Manual | Blackboard |
| Multi-Skill Workflows | ❌ None | ✅ Orchestrator |
| Reasoning Control | ❌ None | ✅ Per-skill RISE |
| Efficiency | Baseline | +20% |

---

**Document:** SPRINT_94_PLAN.md
**Status:** 📝 Planned
**Created:** 2026-01-13
**Updated:** 2026-01-13 (Agent Skills Integration)
