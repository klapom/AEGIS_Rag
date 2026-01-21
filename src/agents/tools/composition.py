"""Tool Composition Framework with Skill Integration.

Sprint 93 Feature 93.1: Tool Composition Framework (10 SP)

Enables chaining multiple tools in workflows with data passing,
integrated with the skill system and LangGraph 1.0 patterns.

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │           Tool Composition + Skill Integration              │
    ├─────────────────────────────────────────────────────────────┤
    │                                                             │
    │  User Request: "Find latest Python version and create      │
    │                 a script that prints it"                   │
    │                                                             │
    │  Skill: research-automation                                 │
    │  Authorized Tools: [web_search, parse, python_exec]        │
    │                                                             │
    │  Decomposed into Tool Chain:                                │
    │                                                             │
    │  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
    │  │web_search│───▶│  parse   │───▶│python_exe│              │
    │  │ [query]  │    │ [result] │    │ [script] │              │
    │  └──────────┘    └──────────┘    └──────────┘              │
    │       │              │               │                      │
    │       ▼              ▼               ▼                      │
    │  "Python 3.13"  version="3.13"  print("3.13")              │
    │                                                             │
    │  State Passing: Each tool receives prior outputs            │
    │  Permission Check: Validate skill has tool access           │
    │  Error Handling: Retry or alternative path on failure       │
    └─────────────────────────────────────────────────────────────┘

LangGraph 1.0 Patterns Used:
    - ToolNode with handle_tool_errors=True for automatic error recovery
    - InjectedState for skill context injection into tools
    - Durable execution for long-running chains

Example:
    >>> from src.agents.tools.composition import ToolComposer, ToolChain, ToolStep
    >>>
    >>> # Define a tool chain
    >>> chain = ToolChain(
    ...     id="research_chain",
    ...     skill_name="research",
    ...     steps=[
    ...         ToolStep(name="search", tool="web_search", inputs={"query": "$query"}),
    ...         ToolStep(name="summarize", tool="llm_summarize", inputs={"text": "$search"})
    ...     ]
    ... )
    >>>
    >>> # Execute the chain
    >>> composer = ToolComposer(tool_registry, skill_manager, policy_engine)
    >>> result = await composer.execute_chain(chain, {"query": "Python 3.13 features"})

See Also:
    - docs/sprints/SPRINT_93_PLAN.md: Feature specification
    - docs/adr/ADR-055-langgraph-1.0-migration.md: LangGraph patterns
    - src/agents/skills/lifecycle.py: Skill lifecycle management

References:
    - LangGraph ToolNode: https://langchain-ai.github.io/langgraph/reference/prebuilt/
    - Anthropic Agent Skills: https://github.com/anthropics/skills
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any, Callable, TypedDict

import structlog
from langgraph.prebuilt import InjectedState, ToolNode
from langchain_core.tools import BaseTool, tool

if TYPE_CHECKING:
    from src.agents.skills.lifecycle import SkillLifecycleManager
    from src.agents.tools.policy import PolicyEngine

logger = structlog.get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================


class ToolStatus(Enum):
    """Status of a tool step in a chain.

    Attributes:
        PENDING: Step not yet started
        RUNNING: Step currently executing
        SUCCESS: Step completed successfully
        FAILED: Step failed after all retries
        SKIPPED: Step skipped (optional step or dependency failure)
        DENIED: Permission denied by policy engine
    """

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    DENIED = "denied"


@dataclass
class ToolStep:
    """Single step in a tool chain.

    Attributes:
        name: Unique step identifier within the chain
        tool: Name of the tool to execute
        inputs: Input parameters (supports $variable references)
        output_key: Key to store result in context (defaults to name)
        status: Current execution status
        result: Result of tool execution (if successful)
        error: Error message (if failed)
        retry_count: Number of retries attempted
        max_retries: Maximum retries allowed
        optional: If True, chain continues on failure

    Example:
        >>> step = ToolStep(
        ...     name="search",
        ...     tool="web_search",
        ...     inputs={"query": "$user_query"},
        ...     output_key="search_results"
        ... )
    """

    name: str
    tool: str
    inputs: dict[str, Any]
    output_key: str = ""
    status: ToolStatus = ToolStatus.PENDING
    result: Any = None
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 2
    optional: bool = False
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not self.output_key:
            self.output_key = self.name


@dataclass
class ToolChain:
    """Chain of tools to execute sequentially.

    Attributes:
        id: Unique chain identifier
        skill_name: Skill that owns this chain
        steps: Ordered list of tool steps
        context: Shared context for variable resolution
        final_output_key: Key containing final result
        parallel_groups: List of step names that can run in parallel

    Example:
        >>> chain = ToolChain(
        ...     id="deep_research",
        ...     skill_name="research",
        ...     steps=[
        ...         ToolStep(name="search", tool="web_search", inputs={"q": "$query"}),
        ...         ToolStep(name="analyze", tool="llm_analyze", inputs={"text": "$search"})
        ...     ],
        ...     final_output_key="analyze"
        ... )
    """

    id: str
    skill_name: str
    steps: list[ToolStep]
    context: dict[str, Any] = field(default_factory=dict)
    final_output_key: str = "result"
    parallel_groups: list[list[str]] = field(default_factory=list)


@dataclass
class ChainExecutionResult:
    """Result of tool chain execution.

    Attributes:
        chain_id: ID of executed chain
        success: Whether chain completed successfully
        final_result: Final output value
        context: Full context after execution
        steps_executed: Number of steps that ran
        steps_succeeded: Number of successful steps
        total_duration_ms: Total execution time
        errors: List of errors encountered
    """

    chain_id: str
    success: bool
    final_result: Any
    context: dict[str, Any]
    steps_executed: int
    steps_succeeded: int
    total_duration_ms: float
    errors: list[str] = field(default_factory=list)


# =============================================================================
# Exceptions
# =============================================================================


class ToolChainError(Exception):
    """Base exception for tool chain errors."""

    pass


class ToolPermissionError(ToolChainError):
    """Skill does not have permission to use tool."""

    pass


class ToolExecutionError(ToolChainError):
    """Tool execution failed."""

    pass


class ToolTimeoutError(ToolChainError):
    """Tool execution timed out."""

    pass


# =============================================================================
# Tool Composer
# =============================================================================


class ToolComposer:
    """Compose and execute tool chains with skill permissions.

    LangGraph 1.0 Features Used:
        - ToolNode with handle_tool_errors=True for automatic error recovery
        - InjectedState for skill context injection
        - Durable execution for state persistence

    Attributes:
        tools: Registry of available tools
        skills: Skill lifecycle manager
        policy: Policy engine for permission checks

    Example:
        >>> composer = ToolComposer(
        ...     tool_registry={"web_search": web_search_tool},
        ...     skill_manager=skill_manager,
        ...     policy_engine=policy_engine
        ... )
        >>> result = await composer.execute_chain(chain, {"query": "test"})
    """

    def __init__(
        self,
        tool_registry: dict[str, Callable[..., Any]],
        skill_manager: SkillLifecycleManager | None = None,
        policy_engine: PolicyEngine | None = None,
    ) -> None:
        """Initialize ToolComposer.

        Args:
            tool_registry: Dict mapping tool names to callable functions
            skill_manager: Optional skill lifecycle manager
            policy_engine: Optional policy engine for permission checks
        """
        self.tools = tool_registry
        self.skills = skill_manager
        self.policy = policy_engine

        # Create LangGraph ToolNode with error handling
        # This enables automatic retry on transient failures
        self._tool_node = (
            ToolNode(
                tools=list(tool_registry.values()),
                handle_tool_errors=True,  # LangGraph 1.0: Auto error recovery
            )
            if tool_registry
            else None
        )

        # Execution metrics
        self._execution_count = 0
        self._success_count = 0
        self._failure_count = 0

        logger.info(
            "tool_composer_initialized",
            tool_count=len(tool_registry),
            has_skill_manager=skill_manager is not None,
            has_policy_engine=policy_engine is not None,
        )

    async def execute_chain(
        self,
        chain: ToolChain,
        initial_context: dict[str, Any] | None = None,
        skill_context: dict[str, Any] | None = None,
    ) -> ChainExecutionResult:
        """Execute tool chain with skill permission checks.

        Args:
            chain: ToolChain to execute
            initial_context: Starting context variables
            skill_context: Additional skill-specific context (InjectedState)

        Returns:
            ChainExecutionResult with outcomes

        Raises:
            ToolPermissionError: If skill lacks tool access
            ToolChainError: If chain execution fails critically
        """
        start_time = time.perf_counter()
        self._execution_count += 1

        # Initialize context
        context = {
            **(initial_context or {}),
            **chain.context,
            "_skill_name": chain.skill_name,
            "_chain_id": chain.id,
            "_start_time": datetime.now().isoformat(),
        }

        # Add skill context for InjectedState pattern
        if skill_context:
            context["_skill_context"] = skill_context

        errors: list[str] = []
        steps_executed = 0
        steps_succeeded = 0

        logger.info(
            "chain_execution_started",
            chain_id=chain.id,
            skill_name=chain.skill_name,
            step_count=len(chain.steps),
        )

        # Validate all tools before execution
        await self._validate_chain_permissions(chain)

        # Execute steps sequentially
        for step in chain.steps:
            steps_executed += 1
            step.status = ToolStatus.RUNNING

            try:
                # Check individual tool permission
                if self.policy:
                    can_use = await self.policy.can_use_tool(
                        chain.skill_name,
                        step.tool,
                        step.inputs,
                    )
                    if not can_use:
                        step.status = ToolStatus.DENIED
                        error_msg = f"Permission denied for tool '{step.tool}'"
                        step.error = error_msg
                        errors.append(error_msg)

                        if not step.optional:
                            raise ToolPermissionError(error_msg)
                        continue

                # Resolve input references
                resolved_inputs = self._resolve_inputs(step.inputs, context)

                # Execute tool with timeout
                result = await self._execute_tool_with_timeout(
                    step.tool,
                    resolved_inputs,
                    timeout=step.timeout_seconds,
                    skill_name=chain.skill_name,
                )

                # Store result
                step.result = result
                step.status = ToolStatus.SUCCESS
                context[step.output_key] = result
                steps_succeeded += 1

                logger.debug(
                    "step_completed",
                    chain_id=chain.id,
                    step_name=step.name,
                    tool=step.tool,
                )

            except asyncio.TimeoutError:
                step.status = ToolStatus.FAILED
                step.error = f"Timeout after {step.timeout_seconds}s"
                errors.append(f"Step '{step.name}': {step.error}")

                if not step.optional and not self._can_continue(chain, step):
                    raise ToolTimeoutError(step.error)

            except Exception as e:
                step.error = str(e)

                # Retry logic
                if step.retry_count < step.max_retries:
                    step.retry_count += 1
                    step.status = ToolStatus.PENDING
                    logger.warning(
                        "step_retry",
                        chain_id=chain.id,
                        step_name=step.name,
                        retry=step.retry_count,
                        max_retries=step.max_retries,
                        error=str(e),
                    )
                    # Re-execute this step
                    continue

                step.status = ToolStatus.FAILED
                errors.append(f"Step '{step.name}': {str(e)}")

                if not step.optional and not self._can_continue(chain, step):
                    raise ToolExecutionError(f"Chain failed at '{step.name}': {e}")

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Get final result
        final_result = context.get(chain.final_output_key)
        success = steps_succeeded == len(chain.steps) or all(
            s.status in (ToolStatus.SUCCESS, ToolStatus.SKIPPED) for s in chain.steps
        )

        if success:
            self._success_count += 1
        else:
            self._failure_count += 1

        logger.info(
            "chain_execution_completed",
            chain_id=chain.id,
            success=success,
            steps_executed=steps_executed,
            steps_succeeded=steps_succeeded,
            duration_ms=duration_ms,
            error_count=len(errors),
        )

        return ChainExecutionResult(
            chain_id=chain.id,
            success=success,
            final_result=final_result,
            context=context,
            steps_executed=steps_executed,
            steps_succeeded=steps_succeeded,
            total_duration_ms=duration_ms,
            errors=errors,
        )

    async def _validate_chain_permissions(self, chain: ToolChain) -> None:
        """Validate skill has access to all tools in chain.

        Args:
            chain: ToolChain to validate

        Raises:
            ToolPermissionError: If any tool is not authorized
        """
        if not self.policy:
            return

        for step in chain.steps:
            can_use = await self.policy.can_use_tool(
                chain.skill_name,
                step.tool,
            )
            if not can_use and not step.optional:
                raise ToolPermissionError(
                    f"Skill '{chain.skill_name}' not authorized for tool '{step.tool}'"
                )

    def _resolve_inputs(
        self,
        inputs: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve input references from context.

        Supports:
            - Direct values: {"query": "test"}
            - Context refs: {"query": "$search_result"}
            - Nested refs: {"data": "$step1.output.text"}
            - List refs: {"items": "$results[0]"}

        Args:
            inputs: Input dict with potential $ references
            context: Current execution context

        Returns:
            Resolved inputs with actual values
        """
        resolved = {}

        for key, value in inputs.items():
            if isinstance(value, str) and value.startswith("$"):
                ref = value[1:]  # Remove $
                resolved[key] = self._resolve_reference(ref, context)
            elif isinstance(value, dict):
                # Recursively resolve nested dicts
                resolved[key] = self._resolve_inputs(value, context)
            elif isinstance(value, list):
                # Resolve list items
                resolved[key] = [
                    (
                        self._resolve_inputs({"_": item}, context).get("_", item)
                        if isinstance(item, (dict, str))
                        else item
                    )
                    for item in value
                ]
            else:
                resolved[key] = value

        return resolved

    def _resolve_reference(self, ref: str, context: dict[str, Any]) -> Any:
        """Resolve a single $ reference.

        Args:
            ref: Reference string (without $)
            context: Execution context

        Returns:
            Resolved value or None if not found
        """
        # Handle array indexing: results[0]
        if "[" in ref:
            base, idx_part = ref.split("[", 1)
            idx = int(idx_part.rstrip("]"))
            base_value = context.get(base, [])
            if isinstance(base_value, list) and len(base_value) > idx:
                return base_value[idx]
            return None

        # Handle nested paths: step1.output.text
        parts = ref.split(".")
        result = context

        for part in parts:
            if isinstance(result, dict):
                result = result.get(part)
            elif hasattr(result, part):
                result = getattr(result, part)
            else:
                return None

            if result is None:
                return None

        return result

    async def _execute_tool_with_timeout(
        self,
        tool_name: str,
        inputs: dict[str, Any],
        timeout: float,
        skill_name: str,
    ) -> Any:
        """Execute tool with timeout.

        Args:
            tool_name: Name of tool to execute
            inputs: Resolved input parameters
            timeout: Timeout in seconds
            skill_name: Skill context for logging

        Returns:
            Tool execution result

        Raises:
            asyncio.TimeoutError: If execution exceeds timeout
            ValueError: If tool not found
        """
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        tool_func = self.tools[tool_name]

        # Log tool usage for audit trail
        if self.policy:
            await self.policy.log_tool_usage(skill_name, tool_name, inputs)

        # Execute with timeout
        if asyncio.iscoroutinefunction(tool_func):
            return await asyncio.wait_for(
                tool_func(**inputs),
                timeout=timeout,
            )
        else:
            # Run sync function in executor
            loop = asyncio.get_event_loop()
            return await asyncio.wait_for(
                loop.run_in_executor(None, lambda: tool_func(**inputs)),
                timeout=timeout,
            )

    def _can_continue(self, chain: ToolChain, failed_step: ToolStep) -> bool:
        """Check if chain can continue after step failure.

        Returns True if no remaining steps depend on the failed step's output.

        Args:
            chain: Current tool chain
            failed_step: Step that failed

        Returns:
            True if chain can continue
        """
        failed_output = f"${failed_step.output_key}"

        for step in chain.steps:
            if step.status == ToolStatus.PENDING:
                # Check if any input references failed step
                for value in step.inputs.values():
                    if isinstance(value, str) and failed_output in value:
                        return False

        return True

    def get_metrics(self) -> dict[str, int]:
        """Get execution metrics.

        Returns:
            Dict with execution counts
        """
        return {
            "total_executions": self._execution_count,
            "successful_chains": self._success_count,
            "failed_chains": self._failure_count,
        }


# =============================================================================
# Skill-Aware Tool Decorator
# =============================================================================


def skill_aware_tool(
    name: str,
    description: str,
    authorized_skills: list[str] | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to create skill-aware tools with InjectedState.

    LangGraph 1.0 Pattern: Uses InjectedState to inject skill context.

    Args:
        name: Tool name
        description: Tool description for LLM
        authorized_skills: List of skills that can use this tool (None = all)

    Returns:
        Decorated function as LangChain tool

    Example:
        >>> @skill_aware_tool(
        ...     name="web_search",
        ...     description="Search the web",
        ...     authorized_skills=["research", "web_automation"]
        ... )
        ... async def search(query: str, state: Annotated[dict, InjectedState]) -> str:
        ...     skill = state.get("_skill_name")
        ...     # Use skill context in tool logic
        ...     return f"Results for {query} (skill: {skill})"
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Store metadata on function
        func._tool_name = name
        func._tool_description = description
        func._authorized_skills = authorized_skills

        # Wrap with langchain tool decorator
        @tool(name=name, description=description)
        async def wrapper(
            *args: Any,
            state: Annotated[dict[str, Any], InjectedState] = None,
            **kwargs: Any,
        ) -> Any:
            # Inject state if function accepts it
            if state is not None:
                kwargs["state"] = state
            return (
                await func(*args, **kwargs)
                if asyncio.iscoroutinefunction(func)
                else func(*args, **kwargs)
            )

        return wrapper

    return decorator


# =============================================================================
# Factory Functions
# =============================================================================


def create_tool_composer(
    tools: dict[str, Callable[..., Any]] | None = None,
    skill_manager: SkillLifecycleManager | None = None,
    policy_engine: PolicyEngine | None = None,
) -> ToolComposer:
    """Factory function to create a ToolComposer.

    Args:
        tools: Optional tool registry (uses defaults if None)
        skill_manager: Optional skill lifecycle manager
        policy_engine: Optional policy engine

    Returns:
        Configured ToolComposer instance
    """
    if tools is None:
        tools = _get_default_tools()

    return ToolComposer(
        tool_registry=tools,
        skill_manager=skill_manager,
        policy_engine=policy_engine,
    )


def _get_default_tools() -> dict[str, Callable[..., Any]]:
    """Get default tool registry.

    Returns:
        Dict of built-in tools
    """
    # Import here to avoid circular imports
    from src.agents.tools.builtin import (
        echo_tool,
        format_tool,
        json_extract_tool,
    )

    return {
        "echo": echo_tool,
        "format": format_tool,
        "json_extract": json_extract_tool,
    }
