"""Tool Integration Module.

Sprint 70 Feature 70.5-70.6: Tool Use Integration with ReAct Pattern
Sprint 93 Feature 93.1: Tool Composition Framework
Sprint 93 Feature 93.2: Browser Tool with Playwright
Sprint 93 Feature 93.3: Skill-Tool Mapping Layer
Sprint 93 Feature 93.4: Policy Guardrails Engine
Sprint 93 Feature 93.5: Tool Chain DSL

This module provides tool integration capabilities for LangGraph agents:
- ReAct pattern tool execution (Sprint 70)
- Tool composition and chaining (Sprint 93)
- Declarative tool chain DSL (YAML/JSON/Python API) (Sprint 93)
- Browser automation with Playwright (Sprint 93)
- Skill-Tool mapping and discovery (Sprint 93)
- Policy-based access control (Sprint 93)
- Built-in utility tools (Sprint 93)

Example:
    >>> from src.agents.tools import ToolComposer, PolicyEngine, get_builtin_tools
    >>> from src.agents.tools import SkillToolMapper, ToolCapability
    >>> from src.agents.tools import browser_navigate, browser_screenshot
    >>> from src.agents.tools import ChainBuilder, parse_chain_yaml, create_chain
    >>>
    >>> # Define chain using DSL
    >>> chain = (
    ...     ChainBuilder("research_chain", skill="research")
    ...     .add_step("search", "web_search", inputs={"query": "$query"})
    ...     .add_step("summarize", "llm_summarize", inputs={"text": "$search"})
    ...     .build()
    ... )
    >>>
    >>> # Or parse from YAML
    >>> chain = parse_chain_yaml(yaml_config)
    >>>
    >>> # Create mapper with tool discovery
    >>> mapper = SkillToolMapper()
    >>> mapper.register_tool(
    ...     "browser",
    ...     ToolCapability(name="browser", description="Web browsing"),
    ...     required_skills=["research"],
    ... )
    >>>
    >>> # Discover tools for skill
    >>> tools = mapper.discover_tools("research", {"async_support": True})
    >>>
    >>> # Create composer with policy enforcement
    >>> policy = PolicyEngine()
    >>> composer = ToolComposer(
    ...     tool_registry=get_builtin_tools(),
    ...     policy_engine=policy,
    ... )
    >>>
    >>> # Execute a tool chain
    >>> result = await composer.execute_chain(chain, {"query": "test"})
    >>>
    >>> # Use browser tools
    >>> nav_result = await browser_navigate("https://example.com")
    >>> screenshot = await browser_screenshot(full_page=True)
"""

# Sprint 70: Tool Integration
from src.agents.tools.tool_integration import should_use_tools, tools_node

# Sprint 93: Tool Composition Framework
from src.agents.tools.composition import (
    ChainExecutionResult,
    ToolChain,
    ToolChainError,
    ToolComposer,
    ToolExecutionError,
    ToolPermissionError,
    ToolStatus,
    ToolStep,
    ToolTimeoutError,
    create_tool_composer,
    skill_aware_tool,
)

# Sprint 93: Built-in Tools
from src.agents.tools.builtin import (
    echo_tool,
    format_tool,
    from_json_tool,
    get_builtin_tools,
    join_tool,
    json_extract_tool,
    replace_tool,
    split_tool,
    template_tool,
    to_json_tool,
    truncate_tool,
)

# Sprint 93: Policy Engine
from src.agents.tools.policy import (
    AuditLogEntry,
    PolicyDecision,
    PolicyEngine,
    PolicyRule,
    SkillPermissions,
    create_default_policy_engine,
)

# Sprint 93: Browser Tool
from src.agents.tools.browser import (
    BrowserAction,
    BrowserResult,
    BrowserSession,
    BrowserTool,
    BrowserToolError,
    browser_click,
    browser_fill_form,
    browser_navigate,
    browser_screenshot,
    browser_type_text,
    get_browser_tools,
)

# Sprint 93: Skill-Tool Mapping Layer
from src.agents.tools.mapping import (
    SkillToolMapper,
    ToolCapability,
    ToolRegistration,
    check_tool_permission,
)

# Sprint 93: Tool Chain DSL
from src.agents.tools.dsl import (
    ChainBuilder,
    DSLParseError,
    DSLValidationError,
    chain_to_json,
    chain_to_yaml,
    create_chain,
    parse_chain_json,
    parse_chain_yaml,
)

__all__ = [
    # Sprint 70
    "should_use_tools",
    "tools_node",
    # Sprint 93: Composition
    "ChainExecutionResult",
    "ToolChain",
    "ToolChainError",
    "ToolComposer",
    "ToolExecutionError",
    "ToolPermissionError",
    "ToolStatus",
    "ToolStep",
    "ToolTimeoutError",
    "create_tool_composer",
    "skill_aware_tool",
    # Sprint 93: Built-in Tools
    "echo_tool",
    "format_tool",
    "from_json_tool",
    "get_builtin_tools",
    "join_tool",
    "json_extract_tool",
    "replace_tool",
    "split_tool",
    "template_tool",
    "to_json_tool",
    "truncate_tool",
    # Sprint 93: Policy
    "AuditLogEntry",
    "PolicyDecision",
    "PolicyEngine",
    "PolicyRule",
    "SkillPermissions",
    "create_default_policy_engine",
    # Sprint 93: Browser Tool
    "BrowserAction",
    "BrowserResult",
    "BrowserSession",
    "BrowserTool",
    "BrowserToolError",
    "browser_click",
    "browser_fill_form",
    "browser_navigate",
    "browser_screenshot",
    "browser_type_text",
    "get_browser_tools",
    # Sprint 93: Skill-Tool Mapping
    "SkillToolMapper",
    "ToolCapability",
    "ToolRegistration",
    "check_tool_permission",
    # Sprint 93: Tool Chain DSL
    "ChainBuilder",
    "DSLParseError",
    "DSLValidationError",
    "chain_to_json",
    "chain_to_yaml",
    "create_chain",
    "parse_chain_json",
    "parse_chain_yaml",
]
