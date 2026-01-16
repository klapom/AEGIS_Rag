"""Integration tests for MCP Tool Execution API endpoints.

Sprint 103 Feature 103.1: Test tool execution endpoints with real tool executors.

Tests cover:
- Bash tool execution
- Python tool execution
- Browser tool execution
- Error handling
- Authentication
- Parameter validation
- Tool listing
- Schema retrieval
"""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from src.api.main import app
from src.core.auth import User


@pytest.fixture
def auth_headers():
    """Mock authentication headers."""
    return {"Authorization": "Bearer test_token"}


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    return User(
        user_id="test_user",
        email="test@example.com",
        role="user",
    )


@pytest.fixture
def mock_auth(mock_user):
    """Mock authentication dependency."""
    with patch("src.api.v1.mcp_tools.get_current_user", return_value=mock_user):
        yield


@pytest.fixture
def mock_playwright_browser():
    """Mock Playwright browser for browser tools."""
    browser = MagicMock()
    browser.is_connected.return_value = True

    context = MagicMock()
    page = AsyncMock()

    # Setup page mock
    page.goto = AsyncMock()
    page.title = AsyncMock(return_value="Example Domain")
    page.url = "https://example.com"
    page.click = AsyncMock()
    page.screenshot = AsyncMock(return_value=b"fake_screenshot")
    page.evaluate = AsyncMock(return_value="Result")
    page.wait_for_selector = AsyncMock()
    page.fill = AsyncMock()
    page.type = AsyncMock()

    # Setup element
    element = AsyncMock()
    element.text_content = AsyncMock(return_value="Test content")
    element.screenshot = AsyncMock(return_value=b"fake_element_screenshot")
    page.wait_for_selector.return_value = element

    # Setup context
    context.pages = [page]
    browser.contexts = [context]

    return browser


class TestBashToolExecution:
    """Test suite for bash tool execution endpoint."""

    @pytest.mark.asyncio
    async def test_execute_bash_command_success(self, mock_auth, auth_headers):
        """Test successful bash command execution."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mcp/tools/bash/execute",
                json={
                    "parameters": {"command": "echo 'Hello World'"},
                    "timeout": 30,
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] in ["success", "error"]
        assert "result" in data
        assert "execution_time_ms" in data
        assert data["execution_time_ms"] >= 0

        if data["status"] == "success":
            result = data["result"]
            assert "stdout" in result or "success" in result

    @pytest.mark.asyncio
    async def test_execute_bash_blocked_command(self, mock_auth, auth_headers):
        """Test that dangerous bash commands are blocked."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mcp/tools/bash/execute",
                json={
                    "parameters": {"command": "rm -rf /"},
                    "timeout": 30,
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return error status due to security block
        assert data["status"] == "error"
        assert data["error_message"] is not None
        assert "blocked" in data["error_message"].lower()

    @pytest.mark.asyncio
    async def test_execute_bash_timeout(self, mock_auth, auth_headers):
        """Test bash command timeout enforcement."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mcp/tools/bash/execute",
                json={
                    "parameters": {"command": "sleep 100"},
                    "timeout": 1,  # 1 second timeout
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should timeout
        assert data["status"] == "timeout"
        assert "timed out" in data["error_message"].lower()

    @pytest.mark.asyncio
    async def test_execute_bash_invalid_parameters(self, mock_auth, auth_headers):
        """Test bash execution with missing required parameters."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mcp/tools/bash/execute",
                json={
                    "parameters": {},  # Missing 'command' parameter
                    "timeout": 30,
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestPythonToolExecution:
    """Test suite for python tool execution endpoint."""

    @pytest.mark.asyncio
    async def test_execute_python_code_success(self, mock_auth, auth_headers):
        """Test successful Python code execution."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mcp/tools/python/execute",
                json={
                    "parameters": {"code": "print('Hello World')"},
                    "timeout": 30,
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "success"
        assert "result" in data
        assert "execution_time_ms" in data

        result = data["result"]
        assert "output" in result
        assert "Hello World" in result["output"]

    @pytest.mark.asyncio
    async def test_execute_python_blocked_import(self, mock_auth, auth_headers):
        """Test that dangerous Python imports are blocked."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mcp/tools/python/execute",
                json={
                    "parameters": {"code": "import os; os.system('ls')"},
                    "timeout": 30,
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Should return error due to blocked module
        assert data["status"] == "error"
        assert "Blocked module" in data["error_message"]

    @pytest.mark.asyncio
    async def test_execute_python_syntax_error(self, mock_auth, auth_headers):
        """Test Python execution with syntax error."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mcp/tools/python/execute",
                json={
                    "parameters": {"code": "print('unclosed string"},
                    "timeout": 30,
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "error"
        assert "Syntax error" in data["error_message"]

    @pytest.mark.asyncio
    async def test_execute_python_math_calculation(self, mock_auth, auth_headers):
        """Test Python math calculation."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mcp/tools/python/execute",
                json={
                    "parameters": {"code": "result = 2 + 2\nprint(result)"},
                    "timeout": 30,
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "success"
        result = data["result"]
        assert "4" in result["output"]


class TestBrowserToolExecution:
    """Test suite for browser tool execution endpoints."""

    @pytest.mark.asyncio
    async def test_browser_navigate_success(self, mock_auth, auth_headers, mock_playwright_browser):
        """Test successful browser navigation."""
        with patch(
            "src.domains.llm_integration.tools.builtin.browser_executor.get_browser",
            return_value=mock_playwright_browser,
        ):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/mcp/tools/browser_navigate/execute",
                    json={
                        "parameters": {"url": "https://example.com"},
                        "timeout": 30,
                    },
                    headers=auth_headers,
                )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "success"
        assert "result" in data
        result = data["result"]
        assert result["url"] == "https://example.com"
        assert result["title"] == "Example Domain"

    @pytest.mark.asyncio
    async def test_browser_screenshot(self, mock_auth, auth_headers, mock_playwright_browser):
        """Test browser screenshot capture."""
        with patch(
            "src.domains.llm_integration.tools.builtin.browser_executor.get_browser",
            return_value=mock_playwright_browser,
        ):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/mcp/tools/browser_screenshot/execute",
                    json={
                        "parameters": {"full_page": True},
                        "timeout": 30,
                    },
                    headers=auth_headers,
                )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "success"
        result = data["result"]
        assert "data" in result
        assert result["format"] == "png"

        # Verify base64 encoding
        screenshot_bytes = base64.b64decode(result["data"])
        assert screenshot_bytes == b"fake_screenshot"

    @pytest.mark.asyncio
    async def test_browser_evaluate(self, mock_auth, auth_headers, mock_playwright_browser):
        """Test browser JavaScript evaluation."""
        with patch(
            "src.domains.llm_integration.tools.builtin.browser_executor.get_browser",
            return_value=mock_playwright_browser,
        ):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/mcp/tools/browser_evaluate/execute",
                    json={
                        "parameters": {"expression": "document.title"},
                        "timeout": 30,
                    },
                    headers=auth_headers,
                )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "success"
        result = data["result"]
        assert result["result"] == "Result"

    @pytest.mark.asyncio
    async def test_browser_get_text(self, mock_auth, auth_headers, mock_playwright_browser):
        """Test browser text extraction."""
        with patch(
            "src.domains.llm_integration.tools.builtin.browser_executor.get_browser",
            return_value=mock_playwright_browser,
        ):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/mcp/tools/browser_get_text/execute",
                    json={
                        "parameters": {"selector": "h1"},
                        "timeout": 30,
                    },
                    headers=auth_headers,
                )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "success"
        result = data["result"]
        assert result["text"] == "Test content"
        assert result["selector"] == "h1"


class TestToolListing:
    """Test suite for tool listing endpoint."""

    @pytest.mark.asyncio
    async def test_list_available_tools(self, mock_auth, auth_headers):
        """Test listing all available tools."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/mcp/tools/list",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "execution" in data
        assert "browser" in data
        assert "all" in data

        # Check that expected tools are present
        assert "bash" in data["execution"]
        assert "python" in data["execution"]
        assert "browser_navigate" in data["browser"]
        assert "browser_screenshot" in data["browser"]

        # Check that all tools are in the combined list
        all_tools = data["all"]
        assert len(all_tools) >= 9  # 2 execution + 7 browser tools


class TestToolSchema:
    """Test suite for tool schema endpoint."""

    @pytest.mark.asyncio
    async def test_get_bash_schema(self, mock_auth, auth_headers):
        """Test retrieving bash tool schema."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/mcp/tools/bash/schema",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["tool_name"] == "bash"
        assert "schema" in data

        schema = data["schema"]
        assert "properties" in schema
        assert "command" in schema["properties"]
        assert "timeout" in schema["properties"]

    @pytest.mark.asyncio
    async def test_get_python_schema(self, mock_auth, auth_headers):
        """Test retrieving python tool schema."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/mcp/tools/python/schema",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["tool_name"] == "python"
        schema = data["schema"]
        assert "code" in schema["properties"]

    @pytest.mark.asyncio
    async def test_get_browser_navigate_schema(self, mock_auth, auth_headers):
        """Test retrieving browser_navigate tool schema."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/mcp/tools/browser_navigate/schema",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["tool_name"] == "browser_navigate"
        schema = data["schema"]
        assert "url" in schema["properties"]
        assert "wait_until" in schema["properties"]

    @pytest.mark.asyncio
    async def test_get_schema_tool_not_found(self, mock_auth, auth_headers):
        """Test retrieving schema for non-existent tool."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/mcp/tools/nonexistent/schema",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAuthentication:
    """Test suite for authentication requirements."""

    @pytest.mark.asyncio
    async def test_execute_tool_without_auth(self):
        """Test that tool execution requires authentication."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mcp/tools/bash/execute",
                json={
                    "parameters": {"command": "echo test"},
                    "timeout": 30,
                },
            )

        # Should fail due to missing authentication
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    @pytest.mark.asyncio
    async def test_list_tools_without_auth(self):
        """Test that tool listing requires authentication."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/mcp/tools/list")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]


class TestErrorHandling:
    """Test suite for error handling."""

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self, mock_auth, auth_headers):
        """Test executing a tool that doesn't exist."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mcp/tools/nonexistent_tool/execute",
                json={
                    "parameters": {},
                    "timeout": 30,
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_execute_with_invalid_timeout(self, mock_auth, auth_headers):
        """Test execution with invalid timeout value."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mcp/tools/bash/execute",
                json={
                    "parameters": {"command": "echo test"},
                    "timeout": 0,  # Invalid: below minimum
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_execute_with_excessive_timeout(self, mock_auth, auth_headers):
        """Test that excessive timeout is rejected by validation."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mcp/tools/bash/execute",
                json={
                    "parameters": {"command": "echo test"},
                    "timeout": 120,  # Invalid: above maximum
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestExecutionMetrics:
    """Test suite for execution time metrics."""

    @pytest.mark.asyncio
    async def test_execution_time_recorded(self, mock_auth, auth_headers):
        """Test that execution time is recorded and returned."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/mcp/tools/python/execute",
                json={
                    "parameters": {"code": "print('test')"},
                    "timeout": 30,
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "execution_time_ms" in data
        assert isinstance(data["execution_time_ms"], int)
        assert data["execution_time_ms"] >= 0
        # Should complete in reasonable time (under 5 seconds)
        assert data["execution_time_ms"] < 5000
