"""Tool Selector for Action Agent.

Selects appropriate MCP tools based on action descriptions.
Uses keyword matching with extensibility for LLM-based selection.

Sprint 9 Feature 9.8: Action Agent (LangGraph Integration)
"""

from typing import Optional

from src.components.mcp.client import MCPClient
from src.components.mcp.models import MCPTool
from src.core.logging import get_logger

logger = get_logger(__name__)


class ToolSelector:
    """Select appropriate MCP tool for a given action.

    Uses keyword-based matching to find the best tool for an action.
    Can be extended to use LLM-based selection for more complex scenarios.
    """

    def __init__(self, mcp_client: MCPClient):
        """Initialize tool selector.

        Args:
            mcp_client: MCP client instance
        """
        self.client = mcp_client
        self.logger = logger.bind(component="tool_selector")

        # Define action keywords mapped to tool name patterns
        self.action_patterns = {
            "file_read": ["read", "file", "open", "view", "cat"],
            "file_write": ["write", "create", "save", "edit"],
            "file_list": ["list", "ls", "dir", "show files"],
            "github_issue": ["issue", "github", "bug", "ticket"],
            "github_pr": ["pull request", "pr", "merge"],
            "search": ["search", "find", "grep", "query"],
            "execute": ["run", "execute", "exec", "command"],
        }

    def select_tool(
        self, action: str, server_name: Optional[str] = None
    ) -> Optional[MCPTool]:
        """Select best tool for action.

        Args:
            action: Action description (e.g., "read the README file")
            server_name: Optional server name to filter by

        Returns:
            Selected MCPTool or None if no match found
        """
        available_tools = self.client.list_tools(server_name)

        if not available_tools:
            self.logger.warning("no_tools_available", server=server_name)
            return None

        action_lower = action.lower()

        # Try to match action patterns
        matched_category = self._match_action_category(action_lower)

        if matched_category:
            # Find tool matching the category
            tool = self._find_tool_by_category(matched_category, available_tools)
            if tool:
                self.logger.info(
                    "tool_selected",
                    action=action,
                    tool=tool.name,
                    category=matched_category,
                )
                return tool

        # Fallback: try direct name matching
        tool = self._find_tool_by_direct_match(action_lower, available_tools)
        if tool:
            self.logger.info(
                "tool_selected_direct",
                action=action,
                tool=tool.name,
            )
            return tool

        # No match found - return first available tool as last resort
        self.logger.warning(
            "no_tool_match",
            action=action,
            using_default=available_tools[0].name if available_tools else None,
        )
        return available_tools[0] if available_tools else None

    def _match_action_category(self, action_lower: str) -> Optional[str]:
        """Match action to a category.

        Args:
            action_lower: Lowercase action string

        Returns:
            Matched category name or None
        """
        for category, keywords in self.action_patterns.items():
            if any(keyword in action_lower for keyword in keywords):
                return category
        return None

    def _find_tool_by_category(
        self, category: str, tools: list[MCPTool]
    ) -> Optional[MCPTool]:
        """Find tool matching a category.

        Args:
            category: Category name
            tools: List of available tools

        Returns:
            Matching tool or None
        """
        # Map categories to tool name patterns
        category_to_pattern = {
            "file_read": ["read", "get", "fetch"],
            "file_write": ["write", "create", "update"],
            "file_list": ["list", "dir"],
            "github_issue": ["issue", "create_issue"],
            "github_pr": ["pull_request", "pr"],
            "search": ["search", "grep", "find"],
            "execute": ["exec", "run", "command"],
        }

        patterns = category_to_pattern.get(category, [])

        for pattern in patterns:
            for tool in tools:
                if pattern in tool.name.lower():
                    return tool

        return None

    def _find_tool_by_direct_match(
        self, action_lower: str, tools: list[MCPTool]
    ) -> Optional[MCPTool]:
        """Find tool by direct name match.

        Args:
            action_lower: Lowercase action string
            tools: List of available tools

        Returns:
            Matching tool or None
        """
        # Extract potential tool name from action
        words = action_lower.split()

        for word in words:
            for tool in tools:
                if word in tool.name.lower() or tool.name.lower() in word:
                    return tool

        return None

    def get_tool_suggestions(self, action: str, top_n: int = 3) -> list[MCPTool]:
        """Get top N tool suggestions for an action.

        Args:
            action: Action description
            top_n: Number of suggestions to return

        Returns:
            List of suggested tools
        """
        available_tools = self.client.list_tools()

        if not available_tools:
            return []

        action_lower = action.lower()

        # Score each tool based on keyword matches
        scored_tools = []
        for tool in available_tools:
            score = self._score_tool(action_lower, tool)
            scored_tools.append((score, tool))

        # Sort by score (descending) and return top N
        scored_tools.sort(key=lambda x: x[0], reverse=True)
        return [tool for _, tool in scored_tools[:top_n]]

    def _score_tool(self, action_lower: str, tool: MCPTool) -> float:
        """Score a tool based on how well it matches an action.

        Args:
            action_lower: Lowercase action string
            tool: Tool to score

        Returns:
            Match score (higher is better)
        """
        score = 0.0

        tool_name_lower = tool.name.lower()
        tool_desc_lower = tool.description.lower()

        # Exact name match
        if action_lower in tool_name_lower or tool_name_lower in action_lower:
            score += 10.0

        # Description match
        action_words = set(action_lower.split())
        desc_words = set(tool_desc_lower.split())
        common_words = action_words & desc_words
        score += len(common_words) * 2.0

        # Keyword matches
        for category, keywords in self.action_patterns.items():
            if any(kw in action_lower for kw in keywords):
                if any(kw in tool_name_lower for kw in keywords):
                    score += 5.0

        return score
