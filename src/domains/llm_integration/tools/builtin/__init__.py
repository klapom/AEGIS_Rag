"""Built-in Tools for LLM Tool Use.

Sprint 59 Features 59.3-59.4: Pre-built tools for common operations.

This package contains built-in tools that are ready to use:
- bash: Execute bash commands (Feature 59.3)
- python: Execute Python code (Feature 59.4)

Future tools (Sprint 60+):
- file_operations: File read/write/search
- web_search: Web searching capabilities
- database_query: Database operations

Usage:
    >>> # Tools are auto-registered when imported
    >>> from src.domains.llm_integration.tools.builtin import bash_tool
    >>> from src.domains.llm_integration.tools import get_tool_executor
    >>>
    >>> executor = get_tool_executor()
    >>> result = await executor.execute(
    ...     "bash",
    ...     {"command": "ls -la"}
    ... )
"""

# Tools will be imported here as they are implemented in Sprint 59.3+
__all__: list[str] = []
