"""LLM Tool Use Framework.

Sprint 59 Feature 59.2: Tool Use Framework for LLM function calling.

This package provides a comprehensive framework for LLM tool use:
- Tool registry with decorator-based registration
- Parameter validation with JSON Schema
- Tool execution with sandboxing support
- OpenAI-compatible function calling schemas
- Result handling and formatting

Architecture:
    ToolRegistry → ToolExecutor → Tool Handler
         ↓              ↓
    Validator    → Result Handler

Components:
    - registry.py: Central tool registration
    - executor.py: Tool execution engine
    - validators.py: Parameter validation
    - schemas.py: JSON Schema helpers
    - result_handlers.py: Result formatting

Usage:
    >>> from src.domains.llm_integration.tools import (
    ...     ToolRegistry,
    ...     ToolExecutor,
    ...     get_tool_executor
    ... )
    >>>
    >>> # Register a tool
    >>> @ToolRegistry.register(
    ...     name="calculator",
    ...     description="Perform arithmetic",
    ...     parameters={
    ...         "type": "object",
    ...         "properties": {
    ...             "operation": {"type": "string"},
    ...             "a": {"type": "number"},
    ...             "b": {"type": "number"}
    ...         },
    ...         "required": ["operation", "a", "b"]
    ...     }
    ... )
    >>> async def calculator(operation: str, a: float, b: float) -> float:
    ...     if operation == "add":
    ...         return a + b
    ...     elif operation == "subtract":
    ...         return a - b
    ...     # ...
    >>>
    >>> # Execute a tool
    >>> executor = get_tool_executor()
    >>> result = await executor.execute(
    ...     "calculator",
    ...     {"operation": "add", "a": 5, "b": 3}
    ... )
    >>> print(result)  # {"result": 8}
    >>>
    >>> # Get OpenAI-compatible schemas
    >>> tools = ToolRegistry.get_openai_tools_schema()
    >>> # Use with LLM provider...

Example - Full Tool Registration:
    >>> from src.domains.llm_integration.tools import ToolRegistry
    >>> from src.domains.llm_integration.tools.schemas import (
    ...     create_parameter_schema,
    ...     create_string_property,
    ...     create_integer_property
    ... )
    >>>
    >>> @ToolRegistry.register(
    ...     name="search",
    ...     description="Search the knowledge base",
    ...     parameters=create_parameter_schema(
    ...         properties={
    ...             "query": create_string_property(
    ...                 description="Search query",
    ...                 min_length=1,
    ...                 max_length=500
    ...             ),
    ...             "limit": create_integer_property(
    ...                 description="Max results",
    ...                 minimum=1,
    ...                 maximum=100,
    ...                 default=10
    ...             )
    ...         },
    ...         required=["query"]
    ...     )
    ... )
    >>> async def search_tool(query: str, limit: int = 10) -> dict:
    ...     # Implementation...
    ...     return {"results": [...]}
"""

from src.domains.llm_integration.tools.executor import ToolExecutor, get_tool_executor
from src.domains.llm_integration.tools.registry import ToolDefinition, ToolRegistry
from src.domains.llm_integration.tools.result_handlers import ToolResult, format_tool_result
from src.domains.llm_integration.tools.schemas import (
    create_array_property,
    create_boolean_property,
    create_function_schema,
    create_integer_property,
    create_number_property,
    create_object_property,
    create_parameter_schema,
    create_string_property,
)
from src.domains.llm_integration.tools.validators import ValidationResult, validate_parameters

__all__ = [
    # Registry
    "ToolRegistry",
    "ToolDefinition",
    # Executor
    "ToolExecutor",
    "get_tool_executor",
    # Validators
    "validate_parameters",
    "ValidationResult",
    # Schemas
    "create_parameter_schema",
    "create_function_schema",
    "create_string_property",
    "create_integer_property",
    "create_number_property",
    "create_boolean_property",
    "create_array_property",
    "create_object_property",
    # Result Handlers
    "ToolResult",
    "format_tool_result",
]
