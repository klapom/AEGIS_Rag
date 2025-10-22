"""Action Agent with LangGraph Integration.

LangGraph-based agent that executes actions via MCP tools.
Supports tool selection, execution, and error handling in a graph workflow.

Sprint 9 Feature 9.8: Action Agent (LangGraph Integration)
"""

import operator
from typing import Annotated, Any

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from src.agents.tool_selector import ToolSelector
from src.components.mcp.client import MCPClient
from src.components.mcp.tool_executor import ToolExecutor
from src.core.logging import get_logger

logger = get_logger(__name__)


class ActionAgentState(TypedDict):
    """State for action agent workflow.

    Attributes:
        action: Action description to execute
        parameters: Parameters for the action/tool
        selected_tool: Name of selected tool
        tool_result: Result from tool execution
        error: Error message if any
        messages: Execution trace messages
    """

    action: str
    parameters: dict[str, Any]
    selected_tool: str
    tool_result: dict[str, Any]
    error: str
    messages: Annotated[list[str], operator.add]


class ActionAgent:
    """LangGraph agent that executes actions via MCP tools.

    Workflow:
    1. select_tool: Choose appropriate MCP tool for action
    2. execute_tool: Execute the selected tool
    3. handle_result: Process result or error

    Features:
    - Automatic tool selection based on action
    - Error handling and retry (via ToolExecutor)
    - LangSmith tracing support
    - Execution logging and metrics
    """

    def __init__(self, mcp_client: MCPClient, tool_executor: ToolExecutor):
        """Initialize action agent.

        Args:
            mcp_client: MCP client instance
            tool_executor: Tool executor with retry logic
        """
        self.client = mcp_client
        self.executor = tool_executor
        self.tool_selector = ToolSelector(mcp_client)
        self.logger = logger.bind(agent="action_agent")
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow.

        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(ActionAgentState)

        # Add nodes
        workflow.add_node("select_tool", self._select_tool_node)
        workflow.add_node("execute_tool", self._execute_tool_node)
        workflow.add_node("handle_result", self._handle_result_node)

        # Define edges
        workflow.set_entry_point("select_tool")
        workflow.add_edge("select_tool", "execute_tool")
        workflow.add_edge("execute_tool", "handle_result")
        workflow.add_edge("handle_result", END)

        return workflow.compile()

    async def _select_tool_node(self, state: ActionAgentState) -> ActionAgentState:
        """Select appropriate tool for action.

        Args:
            state: Current agent state

        Returns:
            Updated state with selected tool
        """
        self.logger.info("selecting_tool", action=state["action"])

        # Select tool based on action
        tool = self.tool_selector.select_tool(state["action"])

        if not tool:
            state["error"] = f"No tool found for action: {state['action']}"
            state["messages"].append(f"ERROR: {state['error']}")
            return state

        state["selected_tool"] = tool.name
        state["messages"].append(f"Selected tool: {tool.name}")

        self.logger.info("tool_selected", tool=tool.name, action=state["action"])

        return state

    async def _execute_tool_node(self, state: ActionAgentState) -> ActionAgentState:
        """Execute selected tool.

        Args:
            state: Current agent state

        Returns:
            Updated state with tool result
        """
        # Skip execution if there's already an error
        if state.get("error"):
            return state

        tool_name = state["selected_tool"]
        parameters = state.get("parameters", {})

        self.logger.info("executing_tool", tool=tool_name, params=parameters)

        try:
            # Execute tool with retry logic
            result = await self.executor.execute(
                tool_name=tool_name,
                parameters=parameters,
            )

            if result.success:
                state["tool_result"] = result.result or {}
                state["messages"].append(
                    f"Tool executed successfully (took {result.execution_time:.2f}s)"
                )
                self.logger.info(
                    "tool_execution_success",
                    tool=tool_name,
                    execution_time=result.execution_time,
                )
            else:
                state["error"] = result.error or "Unknown error"
                state["messages"].append(f"Tool execution failed: {state['error']}")
                self.logger.error(
                    "tool_execution_failed",
                    tool=tool_name,
                    error=state["error"],
                )

        except Exception as e:
            state["error"] = str(e)
            state["messages"].append(f"Tool execution exception: {str(e)}")
            self.logger.error(
                "tool_execution_exception",
                tool=tool_name,
                error=str(e),
                error_type=type(e).__name__,
            )

        return state

    async def _handle_result_node(self, state: ActionAgentState) -> ActionAgentState:
        """Handle tool result or error.

        Args:
            state: Current agent state

        Returns:
            Updated state with final status
        """
        if state.get("error"):
            state["messages"].append(f"Action failed: {state['error']}")
            self.logger.warning("action_failed", error=state["error"])
        else:
            state["messages"].append("Action completed successfully")
            self.logger.info("action_success", action=state["action"])

        return state

    async def execute(
        self, action: str, parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute an action using MCP tools.

        Args:
            action: Action description (e.g., "read the README file")
            parameters: Optional parameters for the action

        Returns:
            Execution result with success status, result, error, and trace
        """
        self.logger.info("action_started", action=action, parameters=parameters)

        # Initialize state
        initial_state: ActionAgentState = {
            "action": action,
            "parameters": parameters or {},
            "selected_tool": "",
            "tool_result": {},
            "error": "",
            "messages": [],
        }

        try:
            # Run graph workflow
            final_state = await self.graph.ainvoke(initial_state)

            # Build result
            result = {
                "success": not final_state.get("error"),
                "result": final_state.get("tool_result", {}),
                "error": final_state.get("error"),
                "trace": final_state.get("messages", []),
                "tool": final_state.get("selected_tool"),
            }

            self.logger.info(
                "action_completed",
                action=action,
                success=result["success"],
                tool=result["tool"],
            )

            return result

        except Exception as e:
            self.logger.error(
                "action_execution_error",
                action=action,
                error=str(e),
                error_type=type(e).__name__,
            )

            return {
                "success": False,
                "result": {},
                "error": f"Action execution failed: {str(e)}",
                "trace": [f"ERROR: {str(e)}"],
                "tool": None,
            }

    def get_available_tools(self) -> list[str]:
        """Get list of available tool names.

        Returns:
            List of tool names
        """
        tools = self.client.list_tools()
        return [tool.name for tool in tools]

    def get_tool_info(self, tool_name: str) -> dict[str, Any] | None:
        """Get information about a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool information or None if not found
        """
        tool = self.client.get_tool(tool_name)
        if not tool:
            return None

        return {
            "name": tool.name,
            "description": tool.description,
            "server": tool.server,
            "parameters": tool.parameters,
            "version": tool.version,
        }
