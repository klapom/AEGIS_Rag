"""LLM Integration Domain Protocols.

Sprint 57 Feature 57.3: Protocol definitions for LLM operations.
Enables dependency injection and improves testability.

Usage:
    from src.domains.llm_integration.protocols import (
        LLMProvider,
        LLMRouter,
        CostTracker,
        ToolExecutor,
    )

These protocols define interfaces for:
- LLM generation and streaming
- Multi-cloud routing
- Cost tracking
- Tool execution (Sprint 59 preparation)

IMPORTANT: ToolExecutor Protocol is required for Sprint 59 Agentic Features:
- Bash/Python Execution
- Agentic Search
- Deep Research
"""

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM providers.

    Implementations should provide text generation capabilities
    using language models.

    Example:
        >>> class OllamaProvider:
        ...     async def generate(self, prompt: str, model: str | None = None) -> str:
        ...         # Use Ollama to generate text
        ...         pass
    """

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate text from prompt.

        Args:
            prompt: Input prompt
            model: Model to use (optional, uses default)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated text
        """
        ...

    async def stream(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Stream text generation.

        Args:
            prompt: Input prompt
            model: Model to use
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Yields:
            Text chunks as they're generated
        """
        ...

    def get_available_models(self) -> list[str]:
        """Get list of available models.

        Returns:
            List of model identifiers
        """
        ...


@runtime_checkable
class LLMRouter(Protocol):
    """Protocol for multi-cloud LLM routing.

    Implementations should route requests to optimal providers
    based on task type, cost, and availability.

    ADR-033: AegisLLMProxy multi-cloud routing.
    """

    async def route(
        self,
        task_type: str,
        preferred_provider: str | None = None,
    ) -> "LLMProvider":
        """Route request to optimal provider.

        Args:
            task_type: Type of task (generation, extraction, embedding, etc.)
            preferred_provider: Optional preferred provider

        Returns:
            LLMProvider instance for the selected provider
        """
        ...

    async def get_provider(
        self,
        provider_name: str,
    ) -> "LLMProvider":
        """Get specific provider by name.

        Args:
            provider_name: Provider identifier (ollama, dashscope, openai)

        Returns:
            LLMProvider instance
        """
        ...

    def get_available_providers(self) -> list[str]:
        """Get list of available providers.

        Returns:
            List of provider identifiers
        """
        ...


@runtime_checkable
class CostTracker(Protocol):
    """Protocol for LLM cost tracking.

    Implementations should track token usage and costs
    across providers and models.
    """

    async def record_usage(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float = 0.0,
    ) -> None:
        """Record LLM usage for cost tracking.

        Args:
            provider: Provider identifier
            model: Model identifier
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost_usd: Cost in USD
        """
        ...

    async def get_total_cost(
        self,
        period: str = "day",
    ) -> float:
        """Get total cost for period.

        Args:
            period: Time period (day, week, month)

        Returns:
            Total cost in USD
        """
        ...

    async def get_usage_stats(
        self,
        period: str = "day",
    ) -> dict[str, Any]:
        """Get usage statistics for period.

        Args:
            period: Time period

        Returns:
            Statistics including:
            - total_cost: float
            - total_tokens: int
            - by_provider: dict
            - by_model: dict
        """
        ...


@runtime_checkable
class ToolExecutor(Protocol):
    """Protocol for LLM tool execution.

    IMPORTANT: Required for Sprint 59 Agentic Features!
    This protocol defines the interface for executing tools
    in response to LLM function calls.

    Sprint 59 Tools:
    - bash: Execute bash commands
    - python: Execute Python code
    - search: Web search
    - file_read: Read files
    - file_write: Write files
    """

    async def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool with given parameters.

        Args:
            tool_name: Name of tool to execute
            parameters: Tool parameters

        Returns:
            Execution result with:
            - success: bool
            - output: Any
            - error: str | None
            - metadata: dict
        """
        ...

    def get_available_tools(self) -> list[dict[str, Any]]:
        """Get list of available tools with schemas.

        Returns:
            List of tool definitions with:
            - name: str
            - description: str
            - parameters: dict (JSON schema)
        """
        ...

    def is_tool_available(self, tool_name: str) -> bool:
        """Check if a tool is available.

        Args:
            tool_name: Name of tool to check

        Returns:
            True if tool is available
        """
        ...


@runtime_checkable
class VLMProvider(Protocol):
    """Protocol for Vision Language Model providers.

    Implementations should generate descriptions for images
    using vision-language models.
    """

    async def generate_image_description(
        self,
        image_path: Any,  # Path or bytes
        prompt: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> tuple[str, dict[str, Any]]:
        """Generate image description using VLM.

        Args:
            image_path: Path to image or image bytes
            prompt: Text prompt for description
            model: Model to use
            **kwargs: Additional parameters

        Returns:
            Tuple of (description, metadata)
        """
        ...

    async def close(self) -> None:
        """Close client and cleanup resources."""
        ...


__all__ = [
    "LLMProvider",
    "LLMRouter",
    "CostTracker",
    "ToolExecutor",
    "VLMProvider",
]
