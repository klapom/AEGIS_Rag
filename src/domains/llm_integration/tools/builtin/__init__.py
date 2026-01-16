"""Built-in Tools for LLM Tool Use.

Sprint 59 Features 59.3-59.5: Pre-built tools for common operations.

This package contains built-in tools that are ready to use:
- bash: Execute bash commands (Feature 59.3)
- python: Execute Python code (Feature 59.4)
- browser: Execute browser operations with Playwright (Feature 59.5)

Future tools (Sprint 60+):
- file_operations: File read/write/search
- web_search: Web searching capabilities
- database_query: Database operations

Usage:
    >>> # Tools are auto-registered when imported
    >>> from src.domains.llm_integration.tools.builtin import bash_tool, browser_tool
    >>> from src.domains.llm_integration.tools import get_tool_executor
    >>>
    >>> executor = get_tool_executor()
    >>> result = await executor.execute(
    ...     "bash",
    ...     {"command": "ls -la"}
    ... )
    >>> result = await executor.execute(
    ...     "browser_navigate",
    ...     {"url": "https://example.com"}
    ... )
"""

# Import tools to trigger auto-registration
from src.domains.llm_integration.tools.builtin import bash_tool, browser_executor, python_tool

__all__: list[str] = ["bash_tool", "python_tool", "browser_executor"]
