"""LangGraph 1.0 Integration for Hierarchical Agents.

Sprint 95 Feature 95.1: Hierarchical Agent Pattern (10 SP)

This module provides LangGraph 1.0 integration patterns for hierarchical agents,
including:

1. **create_react_agent** wrappers for each hierarchy level
2. **Handoff tools** for delegation between agents
3. **State modifiers** for agent instructions
4. **Supervisor nodes** with tool-based delegation

Based on: LangGraph Hierarchical Teams Tutorial
    https://langchain-ai.github.io/langgraph/tutorials/multi_agent/hierarchical_agent_teams/

Example:
    >>> from langgraph.prebuilt import create_react_agent
    >>> from langchain_core.tools import tool
    >>>
    >>> # Create handoff tools
    >>> @tool
    >>> def handoff_to_retrieval(query: str) -> str:
    ...     \"\"\"Delegate retrieval task to retrieval worker.\"\"\"
    ...     return "Delegating to retrieval worker..."
    >>>
    >>> # Create worker agent
    >>> retrieval_agent = create_react_agent(
    ...     model=llm,
    ...     tools=[vector_search, bm25_search],
    ...     name="retrieval_worker"
    ... )
    >>>
    >>> # Create manager supervisor
    >>> research_manager = create_react_agent(
    ...     model=llm,
    ...     tools=[handoff_to_retrieval, handoff_to_web_search],
    ...     state_modifier="Coordinate research tasks.",
    ...     name="research_manager"
    ... )

See Also:
    - docs/sprints/SPRINT_95_PLAN.md (lines 26-56): LangGraph patterns
    - src/agents/hierarchy/skill_hierarchy.py: Core hierarchy
"""

from __future__ import annotations

from typing import Any, Callable

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

logger = structlog.get_logger(__name__)


# =============================================================================
# Handoff Tool Factory
# =============================================================================


def create_handoff_tool(
    target_agent_id: str,
    target_agent_name: str,
    capabilities: list[str],
    callback: Callable[[str, dict[str, Any]], Any] | None = None,
) -> Callable:
    """Create handoff tool for delegating to target agent.

    Args:
        target_agent_id: ID of target agent
        target_agent_name: Human-readable agent name
        capabilities: List of capabilities target agent provides
        callback: Optional callback function for actual delegation

    Returns:
        Tool function decorated with @tool

    Example:
        >>> handoff_tool = create_handoff_tool(
        ...     target_agent_id="retrieval_worker",
        ...     target_agent_name="Retrieval Worker",
        ...     capabilities=["vector_search", "bm25_search"],
        ...     callback=lambda task, inputs: worker.receive_task(task)
        ... )
        >>> handoff_tool.name
        'handoff_to_retrieval_worker'
    """

    @tool
    def handoff_tool(task_description: str, **kwargs: Any) -> str:
        f"""Delegate task to {target_agent_name}.

        This agent specializes in: {', '.join(capabilities)}

        Args:
            task_description: Description of task to delegate
            **kwargs: Additional parameters for the task

        Returns:
            Delegation confirmation message
        """
        logger.info(
            "handoff_invoked",
            target_agent=target_agent_id,
            task=task_description[:100],
        )

        if callback:
            result = callback(task_description, kwargs)
            return f"Delegated to {target_agent_name}: {result}"

        return f"Delegating to {target_agent_name} for task: {task_description}"

    # Set tool name dynamically
    handoff_tool.name = f"handoff_to_{target_agent_id}"
    handoff_tool.description = f"Delegate task to {target_agent_name} ({', '.join(capabilities)})"

    return handoff_tool


# =============================================================================
# Supervisor Agent Factory
# =============================================================================


def create_supervisor_agent(
    agent_id: str,
    level: str,
    llm: BaseChatModel,
    child_agents: list[dict[str, Any]],
    state_modifier: str | None = None,
) -> Any:
    """Create LangGraph supervisor agent with handoff tools.

    Args:
        agent_id: Supervisor agent ID
        level: Hierarchy level (executive, manager, worker)
        llm: Language model
        child_agents: List of child agent configurations
        state_modifier: Optional instructions for agent

    Returns:
        LangGraph react agent

    Example:
        >>> research_manager = create_supervisor_agent(
        ...     agent_id="research_manager",
        ...     level="manager",
        ...     llm=llm,
        ...     child_agents=[
        ...         {
        ...             "id": "retrieval_worker",
        ...             "name": "Retrieval Worker",
        ...             "capabilities": ["vector_search", "bm25_search"]
        ...         },
        ...         {
        ...             "id": "web_search_worker",
        ...             "name": "Web Search Worker",
        ...             "capabilities": ["web_search"]
        ...         }
        ...     ],
        ...     state_modifier="Coordinate research tasks."
        ... )
    """
    # Create handoff tools for each child
    handoff_tools = []
    for child in child_agents:
        tool = create_handoff_tool(
            target_agent_id=child["id"],
            target_agent_name=child["name"],
            capabilities=child.get("capabilities", []),
            callback=child.get("callback"),
        )
        handoff_tools.append(tool)

    # Build state modifier
    if state_modifier is None:
        state_modifier = f"{level.capitalize()} supervisor: delegate tasks to specialized agents."

    # Create react agent with handoff tools
    agent = create_react_agent(
        model=llm,
        tools=handoff_tools,
        state_modifier=state_modifier,
        name=agent_id,
    )

    logger.info(
        "supervisor_agent_created",
        agent_id=agent_id,
        level=level,
        child_count=len(child_agents),
        tools_count=len(handoff_tools),
    )

    return agent


# =============================================================================
# Hierarchy Builder
# =============================================================================


class LangGraphHierarchyBuilder:
    """Build complete LangGraph hierarchical agent system.

    Creates three-level hierarchy with LangGraph 1.0 patterns:
    - Executive supervisor (top)
    - Manager supervisors (mid)
    - Worker agents (bottom)

    Example:
        >>> builder = LangGraphHierarchyBuilder(llm=llm)
        >>>
        >>> # Define hierarchy
        >>> hierarchy = builder.build_hierarchy(
        ...     executive_config={
        ...         "id": "executive",
        ...         "state_modifier": "Strategic planning and coordination."
        ...     },
        ...     managers=[
        ...         {
        ...             "id": "research_manager",
        ...             "name": "Research Manager",
        ...             "workers": [
        ...                 {
        ...                     "id": "retrieval_worker",
        ...                     "name": "Retrieval Worker",
        ...                     "capabilities": ["vector_search"],
        ...                     "tools": [vector_search_tool]
        ...                 }
        ...             ]
        ...         }
        ...     ]
        ... )
        >>>
        >>> executive = hierarchy["executive"]
        >>> research_manager = hierarchy["managers"]["research_manager"]
    """

    def __init__(self, llm: BaseChatModel) -> None:
        """Initialize hierarchy builder.

        Args:
            llm: Language model for all agents
        """
        self.llm = llm
        self._agents: dict[str, Any] = {}

    def build_hierarchy(
        self,
        executive_config: dict[str, Any],
        managers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build complete three-level hierarchy.

        Args:
            executive_config: Executive agent configuration
            managers: List of manager configurations with workers

        Returns:
            Dict with created agents

        Example:
            >>> hierarchy = builder.build_hierarchy(
            ...     executive_config={"id": "executive"},
            ...     managers=[
            ...         {
            ...             "id": "research_manager",
            ...             "workers": [{"id": "retrieval_worker", "tools": [...]}]
            ...         }
            ...     ]
            ... )
        """
        # Create worker agents first
        workers_by_manager: dict[str, list[dict[str, Any]]] = {}

        for manager_config in managers:
            manager_id = manager_config["id"]
            workers_by_manager[manager_id] = []

            for worker_config in manager_config.get("workers", []):
                worker = self._create_worker_agent(worker_config)
                workers_by_manager[manager_id].append(
                    {
                        "id": worker_config["id"],
                        "name": worker_config.get("name", worker_config["id"]),
                        "capabilities": worker_config.get("capabilities", []),
                        "agent": worker,
                    }
                )

        # Create manager supervisors
        manager_agents = {}
        manager_handoff_configs = []

        for manager_config in managers:
            manager_id = manager_config["id"]
            child_workers = workers_by_manager[manager_id]

            manager = create_supervisor_agent(
                agent_id=manager_id,
                level="manager",
                llm=self.llm,
                child_agents=child_workers,
                state_modifier=manager_config.get("state_modifier"),
            )

            manager_agents[manager_id] = manager

            # Prepare for executive handoff
            manager_handoff_configs.append(
                {
                    "id": manager_id,
                    "name": manager_config.get("name", manager_id),
                    "capabilities": manager_config.get("capabilities", []),
                }
            )

        # Create executive supervisor
        executive = create_supervisor_agent(
            agent_id=executive_config["id"],
            level="executive",
            llm=self.llm,
            child_agents=manager_handoff_configs,
            state_modifier=executive_config.get("state_modifier"),
        )

        hierarchy = {
            "executive": executive,
            "managers": manager_agents,
            "workers": {
                manager_id: workers for manager_id, workers in workers_by_manager.items()
            },
        }

        logger.info(
            "hierarchy_built",
            executive=executive_config["id"],
            manager_count=len(manager_agents),
            worker_count=sum(len(w) for w in workers_by_manager.values()),
        )

        return hierarchy

    def _create_worker_agent(self, worker_config: dict[str, Any]) -> Any:
        """Create worker agent with tools.

        Args:
            worker_config: Worker configuration with tools

        Returns:
            LangGraph react agent
        """
        worker = create_react_agent(
            model=self.llm,
            tools=worker_config.get("tools", []),
            state_modifier=worker_config.get("state_modifier"),
            name=worker_config["id"],
        )

        logger.debug(
            "worker_agent_created",
            worker_id=worker_config["id"],
            tools_count=len(worker_config.get("tools", [])),
        )

        return worker


# =============================================================================
# Convenience Functions
# =============================================================================


def create_executive_supervisor(
    llm: BaseChatModel,
    manager_ids: list[str],
    manager_names: list[str] | None = None,
    state_modifier: str | None = None,
) -> Any:
    """Create executive supervisor with manager handoffs.

    Args:
        llm: Language model
        manager_ids: List of manager agent IDs
        manager_names: Optional human-readable names
        state_modifier: Optional instructions

    Returns:
        LangGraph executive agent

    Example:
        >>> executive = create_executive_supervisor(
        ...     llm=llm,
        ...     manager_ids=["research_manager", "analysis_manager"],
        ...     manager_names=["Research Manager", "Analysis Manager"],
        ...     state_modifier="Strategic planning and coordination."
        ... )
    """
    if manager_names is None:
        manager_names = [m.replace("_", " ").title() for m in manager_ids]

    child_agents = [
        {"id": mid, "name": mname, "capabilities": []}
        for mid, mname in zip(manager_ids, manager_names)
    ]

    return create_supervisor_agent(
        agent_id="executive",
        level="executive",
        llm=llm,
        child_agents=child_agents,
        state_modifier=state_modifier,
    )


def create_manager_supervisor(
    manager_id: str,
    llm: BaseChatModel,
    worker_ids: list[str],
    worker_capabilities: list[list[str]],
    worker_names: list[str] | None = None,
    state_modifier: str | None = None,
) -> Any:
    """Create manager supervisor with worker handoffs.

    Args:
        manager_id: Manager agent ID
        llm: Language model
        worker_ids: List of worker agent IDs
        worker_capabilities: List of capability lists for each worker
        worker_names: Optional human-readable names
        state_modifier: Optional instructions

    Returns:
        LangGraph manager agent

    Example:
        >>> research_manager = create_manager_supervisor(
        ...     manager_id="research_manager",
        ...     llm=llm,
        ...     worker_ids=["retrieval_worker", "web_search_worker"],
        ...     worker_capabilities=[["vector_search"], ["web_search"]],
        ...     state_modifier="Coordinate research tasks."
        ... )
    """
    if worker_names is None:
        worker_names = [w.replace("_", " ").title() for w in worker_ids]

    child_agents = [
        {"id": wid, "name": wname, "capabilities": caps}
        for wid, wname, caps in zip(worker_ids, worker_names, worker_capabilities)
    ]

    return create_supervisor_agent(
        agent_id=manager_id,
        level="manager",
        llm=llm,
        child_agents=child_agents,
        state_modifier=state_modifier,
    )
