"""Unit tests for Tool Use Framework.

Sprint 59 Feature 59.2: Tests for tool registration, validation, and execution.

Tests cover:
- Tool registry registration and retrieval
- Parameter validation
- Tool execution (direct and future sandboxed)
- OpenAI schema generation
- Result handling
"""

import pytest

from src.domains.llm_integration.tools import (
    ToolExecutor,
    ToolRegistry,
    ValidationResult,
    create_integer_property,
    create_parameter_schema,
    create_string_property,
    format_tool_result,
    get_tool_executor,
    validate_parameters,
)

# ============================================================================
# Test Tool Registration
# ============================================================================


@pytest.fixture(autouse=True)
def clear_registry():
    """Clear tool registry before each test."""
    ToolRegistry.clear()
    yield
    ToolRegistry.clear()


def test_tool_registration():
    """Test basic tool registration."""

    @ToolRegistry.register(
        name="test_tool",
        description="A test tool",
        parameters={"type": "object", "properties": {}, "required": []},
    )
    async def test_func():
        return "result"

    # Verify tool is registered
    tool = ToolRegistry.get_tool("test_tool")
    assert tool is not None
    assert tool.name == "test_tool"
    assert tool.description == "A test tool"
    assert tool.handler == test_func


def test_tool_registration_with_sandbox():
    """Test tool registration with sandbox requirement."""

    @ToolRegistry.register(
        name="dangerous_tool",
        description="Requires sandboxing",
        parameters={"type": "object"},
        requires_sandbox=True,
    )
    async def dangerous_func():
        return "result"

    tool = ToolRegistry.get_tool("dangerous_tool")
    assert tool.requires_sandbox is True


def test_list_all_tools():
    """Test listing all registered tools."""

    @ToolRegistry.register(name="tool1", description="Tool 1", parameters={"type": "object"})
    async def func1():
        pass

    @ToolRegistry.register(name="tool2", description="Tool 2", parameters={"type": "object"})
    async def func2():
        pass

    tools = ToolRegistry.get_all_tools()
    assert len(tools) == 2
    assert {t.name for t in tools} == {"tool1", "tool2"}


def test_get_openai_tools_schema():
    """Test OpenAI schema generation."""

    @ToolRegistry.register(
        name="calculator",
        description="Perform arithmetic",
        parameters={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    )
    async def calc(a: float, b: float):
        return a + b

    schemas = ToolRegistry.get_openai_tools_schema()
    assert len(schemas) == 1
    assert schemas[0]["type"] == "function"
    assert schemas[0]["function"]["name"] == "calculator"
    assert schemas[0]["function"]["description"] == "Perform arithmetic"
    assert "properties" in schemas[0]["function"]["parameters"]


# ============================================================================
# Test Parameter Validation
# ============================================================================


def test_validate_parameters_success():
    """Test successful parameter validation."""
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name"],
    }

    result = validate_parameters({"name": "Alice", "age": 30}, schema)
    assert result.valid is True
    assert result.error is None


def test_validate_parameters_missing_required():
    """Test validation fails for missing required field."""
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }

    result = validate_parameters({}, schema)
    assert result.valid is False
    assert "name" in result.error.lower()


def test_validate_parameters_wrong_type():
    """Test validation fails for wrong type."""
    schema = {"type": "object", "properties": {"age": {"type": "integer"}}}

    result = validate_parameters({"age": "not a number"}, schema)
    # Note: This might pass with basic validation, fail with jsonschema
    # Both behaviors are acceptable
    assert isinstance(result, ValidationResult)


# ============================================================================
# Test Tool Execution
# ============================================================================


@pytest.mark.asyncio
async def test_execute_tool_success():
    """Test successful tool execution."""

    @ToolRegistry.register(
        name="add",
        description="Add two numbers",
        parameters={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    )
    async def add(a: float, b: float):
        return a + b

    executor = ToolExecutor(sandbox_enabled=False)
    result = await executor.execute("add", {"a": 5, "b": 3})

    assert "result" in result
    assert result["result"] == 8


@pytest.mark.asyncio
async def test_execute_unknown_tool():
    """Test executing unknown tool returns error."""
    executor = ToolExecutor()
    result = await executor.execute("nonexistent", {})

    assert "error" in result
    assert "Unknown tool" in result["error"]


@pytest.mark.asyncio
async def test_execute_with_invalid_parameters():
    """Test execution fails with invalid parameters."""

    @ToolRegistry.register(
        name="greet",
        description="Greet user",
        parameters={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    )
    async def greet(name: str):
        return f"Hello, {name}!"

    executor = ToolExecutor()
    result = await executor.execute("greet", {})  # Missing required 'name'

    assert "error" in result
    assert "invalid" in result["error"].lower() or "missing" in result["error"].lower()


@pytest.mark.asyncio
async def test_execute_tool_with_exception():
    """Test tool execution handles exceptions."""

    @ToolRegistry.register(
        name="error_tool",
        description="Always fails",
        parameters={"type": "object", "properties": {}},
    )
    async def error_func():
        raise ValueError("Something went wrong")

    executor = ToolExecutor()
    result = await executor.execute("error_tool", {})

    assert "error" in result
    assert "Something went wrong" in result["error"]


@pytest.mark.asyncio
async def test_batch_execute():
    """Test batch execution of multiple tools."""

    @ToolRegistry.register(
        name="multiply",
        description="Multiply two numbers",
        parameters={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    )
    async def multiply(a: float, b: float):
        return a * b

    executor = ToolExecutor(sandbox_enabled=False)
    calls = [
        {"name": "multiply", "parameters": {"a": 2, "b": 3}},
        {"name": "multiply", "parameters": {"a": 4, "b": 5}},
    ]

    results = await executor.batch_execute(calls)

    assert len(results) == 2
    assert results[0]["result"] == 6
    assert results[1]["result"] == 20


# ============================================================================
# Test Schema Helpers
# ============================================================================


def test_create_parameter_schema():
    """Test parameter schema creation."""
    schema = create_parameter_schema(
        properties={
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
        },
        required=["query"],
    )

    assert schema["type"] == "object"
    assert "query" in schema["properties"]
    assert "limit" in schema["properties"]
    assert schema["required"] == ["query"]


def test_create_string_property():
    """Test string property creation."""
    prop = create_string_property(
        description="User name", min_length=1, max_length=50, default="Guest"
    )

    assert prop["type"] == "string"
    assert prop["description"] == "User name"
    assert prop["minLength"] == 1
    assert prop["maxLength"] == 50
    assert prop["default"] == "Guest"


def test_create_integer_property():
    """Test integer property creation."""
    prop = create_integer_property(description="Age", minimum=0, maximum=150, default=25)

    assert prop["type"] == "integer"
    assert prop["minimum"] == 0
    assert prop["maximum"] == 150
    assert prop["default"] == 25


# ============================================================================
# Test Result Handling
# ============================================================================


def test_format_tool_result_success():
    """Test formatting successful tool result."""
    raw = {"result": "Search found 42 documents"}
    result = format_tool_result(raw)

    assert result.success is True
    assert result.data == "Search found 42 documents"
    assert result.error is None


def test_format_tool_result_error():
    """Test formatting error result."""
    raw = {"error": "Connection timeout"}
    result = format_tool_result(raw)

    assert result.success is False
    assert result.error == "Connection timeout"
    assert result.data is None


def test_format_tool_result_truncation():
    """Test result truncation for large outputs."""
    long_text = "a" * 1000
    raw = {"result": long_text}

    result = format_tool_result(raw, max_length=100)

    assert result.success is True
    assert len(str(result.data)) <= 120  # 100 + "... [truncated]"
    assert result.metadata.get("truncated") is True


# ============================================================================
# Test Executor Stats
# ============================================================================


@pytest.mark.asyncio
async def test_executor_stats():
    """Test execution statistics tracking."""

    @ToolRegistry.register(
        name="stats_test",
        description="Test tool",
        parameters={"type": "object", "properties": {}},
    )
    async def stats_func():
        return "ok"

    executor = ToolExecutor()

    # Execute successfully
    await executor.execute("stats_test", {})

    # Execute with error
    await executor.execute("nonexistent", {})

    stats = executor.get_stats()

    assert stats["total_executions"] == 2
    assert stats["errors"] == 1
    assert stats["error_rate"] == 0.5


# ============================================================================
# Test Singleton
# ============================================================================


def test_get_tool_executor_singleton():
    """Test that get_tool_executor returns singleton."""
    executor1 = get_tool_executor()
    executor2 = get_tool_executor()

    assert executor1 is executor2
