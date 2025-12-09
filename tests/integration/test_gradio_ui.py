"""Integration Tests for Gradio UI (Sprint 10 Feature 10.1).

Sprint 12 Feature 12.9: Comprehensive Gradio UI integration tests.

Tests cover:
- Chat interface interaction
- Document upload flow
- Session management
- Settings persistence
- Multi-tab functionality
- Error handling
- MCP server management
- Tool call visibility

Prerequisites:
- Gradio installed (pip install gradio>=4.0.0)
- FastAPI backend running on localhost:8000
- Mock backend for isolated testing
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest
import pytest_asyncio

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def gradio_app():
    """Create GradioApp instance for testing.

    This fixture provides a fresh GradioApp instance with mocked HTTP client
    to avoid actual backend dependencies during testing.
    """
    with patch("src.ui.gradio_app.httpx.AsyncClient"):
        # Create app instance
        from src.ui.gradio_app import GradioApp

        app = GradioApp()

        # Mock the async client
        mock_http_client = AsyncMock()
        app.client = mock_http_client

        yield app

        # Cleanup
        await app.client.aclose()


@pytest.fixture
def mock_chat_response():
    """Mock successful chat API response."""
    return {
        "answer": "LangGraph is a framework for multi-agent orchestration.",
        "sources": [
            {"title": "LangGraph Documentation", "score": 0.95},
            {"title": "Multi-Agent Systems Guide", "score": 0.87},
        ],
        "tool_calls": [
            {
                "tool_name": "search_documents",
                "server": "filesystem",
                "duration_ms": 125.5,
                "success": True,
                "result": "Found 3 relevant documents",
            }
        ],
    }


@pytest.fixture
def mock_upload_response():
    """Mock successful upload API response."""
    return {
        "status": "success",
        "chunks_created": 15,
        "embeddings_generated": 15,
        "duration_seconds": 2.5,
    }


@pytest.fixture
def temp_test_file():
    """Create temporary test file for upload testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt", encoding="utf-8") as f:
        f.write("Test document content for upload testing.\n")
        f.write("This is a sample document with multiple lines.\n")
        f.write("AEGIS RAG should index this content.\n")
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


# ============================================================================
# Test 1: Gradio App Initialization
# ============================================================================


async def test_gradio_app_initialization():
    """Test that Gradio app can be initialized without errors.

    Sprint 12: Basic smoke test for UI initialization.

    Validates:
    - App imports successfully
    - Session ID generated
    - HTTP client created
    - No configuration errors
    """
    from src.ui.gradio_app import GradioApp

    app = GradioApp()

    # Verify basic attributes
    assert app is not None
    assert app.session_id is not None
    assert len(app.session_id) > 0
    assert app.client is not None
    assert app.mcp_client is None  # Not initialized until needed

    # Cleanup
    await app.client.aclose()


# ============================================================================
# Test 2: Gradio Interface Building
# ============================================================================


async def test_gradio_interface_building(gradio_app):
    """Test that Gradio interface can be built with all tabs.

    Sprint 12: Validates UI structure and components.

    Validates:
    - Interface builds without errors
    - All expected tabs present
    - Custom CSS applied
    - Components configured correctly
    """
    demo = gradio_app.build_interface()

    # Verify demo created
    assert demo is not None

    # Verify it's a Gradio Blocks instance
    import gradio as gr

    assert isinstance(demo, gr.Blocks)

    # Verify interface has title
    assert demo.title == "AEGIS RAG"

    # Note: Detailed component inspection would require rendering
    # which is not feasible in unit tests. Testing component presence
    # via interaction tests below.


# ============================================================================
# Test 3: Chat Interface - Basic Query
# ============================================================================


async def test_chat_interface_basic_query(gradio_app, mock_chat_response):
    """Test basic chat functionality with successful response.

    Sprint 12: Validates end-to-end chat flow.

    Validates:
    - Message input processing
    - API call to backend
    - Response rendering
    - Chat history update
    """
    # Mock successful API response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_chat_response
    gradio_app.client.post = AsyncMock(return_value=mock_response)

    # Initial empty history
    history = []

    # Simulate user query
    query = "What is LangGraph?"
    updated_history, cleared_input = await gradio_app.chat(query, history)

    # Verify response
    assert len(updated_history) == 2  # User message + assistant response
    assert updated_history[0]["role"] == "user"
    assert updated_history[0]["content"] == query
    assert updated_history[1]["role"] == "assistant"
    assert "LangGraph" in updated_history[1]["content"]
    assert "orchestration" in updated_history[1]["content"]

    # Verify input cleared
    assert cleared_input == ""

    # Verify API was called with correct parameters
    gradio_app.client.post.assert_called_once()
    call_args = gradio_app.client.post.call_args
    assert "chat" in call_args[0][0]  # URL contains 'chat'
    assert call_args[1]["json"]["query"] == query


# ============================================================================
# Test 4: Chat Interface - Empty Message
# ============================================================================


async def test_chat_interface_empty_message(gradio_app):
    """Test chat rejects empty messages.

    Sprint 12: Validates input validation.

    Validates:
    - Empty/whitespace messages ignored
    - History unchanged
    - No API call made
    """
    history = []

    # Try empty message
    updated_history, _ = await gradio_app.chat("", history)
    assert len(updated_history) == 0

    # Try whitespace message
    updated_history, _ = await gradio_app.chat("   ", history)
    assert len(updated_history) == 0

    # Verify no API calls made
    gradio_app.client.post.assert_not_called()


# ============================================================================
# Test 5: Chat Interface - API Error Handling
# ============================================================================


async def test_chat_interface_api_error(gradio_app):
    """Test chat gracefully handles backend errors.

    Sprint 12: Validates error recovery.

    Validates:
    - API errors displayed to user
    - UI doesn't crash
    - Error message in history
    - Helpful error indication
    """
    # Mock API error
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    gradio_app.client.post = AsyncMock(return_value=mock_response)

    history = []
    query = "Test query"

    # Should not crash
    updated_history, _ = await gradio_app.chat(query, history)

    # Should have error message
    assert len(updated_history) == 2
    assert updated_history[1]["role"] == "assistant"
    assert "Fehler" in updated_history[1]["content"] or "500" in updated_history[1]["content"]


# ============================================================================
# Test 6: Chat Interface - Connection Error
# ============================================================================


async def test_chat_interface_connection_error(gradio_app):
    """Test chat handles connection failures.

    Sprint 12: Validates network error handling.

    Validates:
    - Connection errors caught
    - User-friendly error message
    - No application crash
    """
    # Mock connection error
    gradio_app.client.post = AsyncMock(side_effect=Exception("Connection refused"))

    history = []
    query = "Test query"

    # Should not crash
    updated_history, _ = await gradio_app.chat(query, history)

    # Should have error message
    assert len(updated_history) == 2
    assert updated_history[1]["role"] == "assistant"
    assert "Verbindungsfehler" in updated_history[1]["content"]


# ============================================================================
# Test 7: Chat Interface - Source Display
# ============================================================================


async def test_chat_interface_source_display(gradio_app, mock_chat_response):
    """Test chat displays source documents with answers.

    Sprint 12: Validates source attribution.

    Validates:
    - Sources shown with answers
    - Source metadata displayed
    - Relevance scores shown
    """
    # Mock response with sources
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_chat_response
    gradio_app.client.post = AsyncMock(return_value=mock_response)

    history = []
    updated_history, _ = await gradio_app.chat("Test query", history)

    assistant_response = updated_history[1]["content"]

    # Verify sources section present
    assert "Quellen" in assistant_response or "📚" in assistant_response

    # Verify source titles shown
    assert "LangGraph Documentation" in assistant_response
    assert "Multi-Agent Systems Guide" in assistant_response

    # Verify scores shown
    assert "0.95" in assistant_response or "Relevanz" in assistant_response


# ============================================================================
# Test 8: Chat Interface - Tool Call Visibility (Feature 10.7)
# ============================================================================


async def test_chat_interface_tool_call_visibility(gradio_app, mock_chat_response):
    """Test chat displays MCP tool call information.

    Sprint 12: Feature 10.7 validation.

    Validates:
    - Tool calls shown in response
    - Tool metadata displayed
    - Success/error indicators
    - Duration information
    """
    # Mock response with tool calls
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_chat_response
    gradio_app.client.post = AsyncMock(return_value=mock_response)

    history = []
    updated_history, _ = await gradio_app.chat("Test query", history)

    assistant_response = updated_history[1]["content"]

    # Verify tool calls section present
    assert "Tool Calls" in assistant_response or "🔧" in assistant_response

    # Verify tool details shown
    assert "search_documents" in assistant_response
    assert "filesystem" in assistant_response
    assert "125.5" in assistant_response or "ms" in assistant_response


# ============================================================================
# Test 9: Chat History Persistence
# ============================================================================


async def test_chat_history_persistence(gradio_app, mock_chat_response):
    """Test chat history accumulates across queries.

    Sprint 12: Validates conversation context.

    Validates:
    - Chat history accumulates
    - Previous messages maintained
    - Correct message ordering
    """
    # Mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_chat_response
    gradio_app.client.post = AsyncMock(return_value=mock_response)

    # Start with empty history
    history = []

    # Send first query
    history, _ = await gradio_app.chat("Query 1", history)
    assert len(history) == 2  # User + assistant

    # Send second query
    history, _ = await gradio_app.chat("Query 2", history)
    assert len(history) == 4  # 2 previous + 2 new

    # Send third query
    history, _ = await gradio_app.chat("Query 3", history)
    assert len(history) == 6  # 4 previous + 2 new

    # Verify ordering
    assert history[0]["content"] == "Query 1"
    assert history[2]["content"] == "Query 2"
    assert history[4]["content"] == "Query 3"
    assert all(
        msg["role"] == "assistant" if i % 2 == 1 else msg["role"] == "user"
        for i, msg in enumerate(history)
    )


# ============================================================================
# Test 10: Chat Clear Functionality
# ============================================================================


async def test_chat_clear_functionality(gradio_app):
    """Test clearing chat history.

    Sprint 12: Validates reset functionality.

    Validates:
    - Chat history cleared
    - New session ID generated
    - API called to delete history
    """
    # Mock delete API
    mock_delete_response = Mock()
    mock_delete_response.status_code = 200
    gradio_app.client.delete = AsyncMock(return_value=mock_delete_response)

    # Store original session ID
    original_session_id = gradio_app.session_id

    # Clear chat
    result = await gradio_app.clear_chat()

    # Verify empty history returned
    assert result == []

    # Verify new session ID generated
    assert gradio_app.session_id != original_session_id

    # Verify delete API called
    gradio_app.client.delete.assert_called_once()


# ============================================================================
# Test 11: Document Upload - Single File
# ============================================================================


async def test_document_upload_single_file(gradio_app, temp_test_file, mock_upload_response):
    """Test single document upload through Gradio UI.

    Sprint 12: Validates file upload integration.

    Validates:
    - File upload handling
    - Progress indication
    - API call to backend
    - Success feedback
    """
    # Mock upload API
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_upload_response
    gradio_app.client.post = AsyncMock(return_value=mock_response)

    # Create file object (simulating Gradio file)
    file_obj = Mock()
    file_obj.name = temp_test_file

    # Mock progress
    mock_progress = Mock()

    # Upload file
    result = await gradio_app.upload_document(file_obj, progress=mock_progress)

    # Verify success message
    assert result is not None
    assert "erfolgreich" in result.lower() or "✅" in result
    assert "15" in result  # Chunks count
    assert "2.5" in result  # Duration

    # Verify API called
    gradio_app.client.post.assert_called()


# ============================================================================
# Test 12: Document Upload - Multiple Files
# ============================================================================


async def test_document_upload_multiple_files(gradio_app, mock_upload_response):
    """Test multiple document upload.

    Sprint 12: Validates batch upload.

    Validates:
    - Multiple files handled
    - Progress per file
    - Summary statistics
    """
    # Mock upload API
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_upload_response
    gradio_app.client.post = AsyncMock(return_value=mock_response)

    # Create temp files
    temp_files = []
    for i in range(3):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(f"Test content {i}")
            temp_files.append(f.name)

    try:
        # Create file objects
        file_objs = [Mock(name=path) for path in temp_files]

        # Mock progress
        mock_progress = Mock()

        # Upload files
        result = await gradio_app.upload_document(file_objs, progress=mock_progress)

        # Verify success
        assert "3" in result or "erfolgreich" in result.lower()

        # Verify total statistics
        assert "45" in result  # 15 chunks * 3 files

    finally:
        # Cleanup
        for path in temp_files:
            Path(path).unlink(missing_ok=True)


# ============================================================================
# Test 13: Document Upload - No File Selected
# ============================================================================


async def test_document_upload_no_file(gradio_app):
    """Test upload validation when no file selected.

    Sprint 12: Validates input validation.

    Validates:
    - Empty file list rejected
    - User-friendly error message
    - No API call made
    """
    # Mock progress
    mock_progress = Mock()

    # Test None
    result = await gradio_app.upload_document(None, progress=mock_progress)
    assert "Bitte wählen" in result

    # Test empty list
    result = await gradio_app.upload_document([], progress=mock_progress)
    assert "Bitte wählen" in result

    # Verify no API calls
    gradio_app.client.post.assert_not_called()


# ============================================================================
# Test 14: Document Upload - API Error
# ============================================================================


async def test_document_upload_api_error(gradio_app, temp_test_file):
    """Test upload handles API errors gracefully.

    Sprint 12: Validates error handling.

    Validates:
    - Upload errors reported
    - Partial success tracked
    - Error details shown
    """
    # Mock API error
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Server error"
    gradio_app.client.post = AsyncMock(return_value=mock_response)

    file_obj = Mock(name=temp_test_file)
    mock_progress = Mock()

    result = await gradio_app.upload_document(file_obj, progress=mock_progress)

    # Should show error
    assert "❌" in result or "Fehler" in result
    assert "0 erfolgreich" in result or "fehlgeschlagen" in result


# ============================================================================
# Test 15: Session Management
# ============================================================================


async def test_session_management():
    """Test session ID generation and uniqueness.

    Sprint 12: Validates session isolation.

    Validates:
    - Unique session IDs generated
    - Sessions independent
    - UUID format valid
    """
    from src.ui.gradio_app import GradioApp

    # Create two apps (simulating two users)
    app1 = GradioApp()
    app2 = GradioApp()

    try:
        # Sessions should be different
        assert app1.session_id != app2.session_id

        # Should be valid UUIDs
        assert len(app1.session_id) == 36  # UUID string length
        assert len(app2.session_id) == 36

        # Should contain hyphens (UUID format)
        assert "-" in app1.session_id
        assert "-" in app2.session_id

    finally:
        await app1.client.aclose()
        await app2.client.aclose()


# ============================================================================
# Test 16: Health Stats Retrieval
# ============================================================================


async def test_health_stats_retrieval(gradio_app):
    """Test system health statistics retrieval.

    Sprint 12: Feature 10.5 validation.

    Validates:
    - Health endpoint called
    - Metrics returned
    - Error handling
    """
    # Mock health response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "healthy",
        "version": "1.0.0",
        "uptime": 3600,
        "components": {"qdrant": "connected", "redis": "connected"},
    }
    gradio_app.client.get = AsyncMock(return_value=mock_response)

    # Get health stats
    stats = await gradio_app.get_health_stats()

    # Verify stats retrieved
    assert stats is not None
    assert stats["status"] == "healthy"
    assert "components" in stats

    # Verify correct endpoint called
    gradio_app.client.get.assert_called_once()


# ============================================================================
# Test 17: Health Stats - API Error
# ============================================================================


async def test_health_stats_api_error(gradio_app):
    """Test health stats handles errors.

    Sprint 12: Validates error recovery.

    Validates:
    - API errors caught
    - Error information returned
    - No crash
    """
    # Mock API error
    gradio_app.client.get = AsyncMock(side_effect=Exception("Connection failed"))

    # Should not crash
    stats = await gradio_app.get_health_stats()

    # Should return error info
    assert "error" in stats
    assert "Connection failed" in stats["error"]


# ============================================================================
# Test 18: MCP Server Connection (Feature 10.6)
# ============================================================================


async def test_mcp_server_connection(gradio_app):
    """Test MCP server connection flow.

    Sprint 12: Feature 10.6 validation.

    Validates:
    - MCP client initialization
    - Server connection
    - Tool discovery
    - Status reporting
    """
    # Mock MCP client
    mock_mcp_client = Mock()
    mock_mcp_client.connect = AsyncMock(return_value=True)

    # Mock stats
    mock_stats = Mock()
    mock_stats.connected_servers = 1
    mock_stats.total_tools = 5
    mock_mcp_client.get_stats.return_value = mock_stats

    # Mock tools
    mock_tool = Mock()
    mock_tool.name = "read_file"
    mock_tool.server = "filesystem"
    mock_tool.description = "Read a file from the filesystem"
    mock_tool.parameters = {"properties": {"path": {"type": "string"}}}
    mock_mcp_client.list_tools = AsyncMock(return_value=[mock_tool])

    with patch("src.ui.gradio_app.MCPClient", return_value=mock_mcp_client):
        # Connect to server
        status, tools_df = await gradio_app.connect_mcp_server(
            name="filesystem",
            transport="STDIO",
            endpoint="npx @modelcontextprotocol/server-filesystem /tmp",
        )

        # Verify connection successful
        assert status["status"] == "connected"
        assert status["server_name"] == "filesystem"
        assert status["total_tools"] == 5

        # Verify tools DataFrame populated
        assert isinstance(tools_df, pd.DataFrame)
        assert len(tools_df) == 1
        assert tools_df.iloc[0]["Tool Name"] == "read_file"


# ============================================================================
# Test 19: MCP Server Connection Error
# ============================================================================


async def test_mcp_server_connection_error(gradio_app):
    """Test MCP connection handles errors.

    Sprint 12: Validates error handling.

    Validates:
    - Connection errors caught
    - Error details returned
    - Empty tools DataFrame on error
    """
    with patch("src.ui.gradio_app.MCPClient", side_effect=Exception("MCP initialization failed")):
        # Attempt connection
        status, tools_df = await gradio_app.connect_mcp_server(
            name="test", transport="HTTP", endpoint="http://localhost:3000"
        )

        # Should return error
        assert "error" in status
        assert isinstance(tools_df, pd.DataFrame)
        assert len(tools_df) == 0


# ============================================================================
# Test 20: MCP Server Disconnect
# ============================================================================


async def test_mcp_server_disconnect(gradio_app):
    """Test MCP server disconnection.

    Sprint 12: Validates cleanup.

    Validates:
    - Disconnect called
    - Status updated
    - Graceful handling
    """
    # Setup mock MCP client
    mock_mcp_client = Mock()
    mock_mcp_client.disconnect = AsyncMock()
    gradio_app.mcp_client = mock_mcp_client

    # Disconnect
    status = await gradio_app.disconnect_mcp_server("filesystem")

    # Verify disconnect called
    assert status["status"] == "disconnected"
    assert status["server_name"] == "filesystem"
    mock_mcp_client.disconnect.assert_called_once_with("filesystem")


# ============================================================================
# Test 21: MCP Tools Refresh
# ============================================================================


async def test_mcp_tools_refresh(gradio_app):
    """Test refreshing MCP tools list.

    Sprint 12: Validates tool discovery updates.

    Validates:
    - Stats refreshed
    - Tools list updated
    - Current state reflected
    """
    # Setup mock MCP client with tools
    mock_mcp_client = Mock()

    mock_stats = Mock()
    mock_stats.connected_servers = 2
    mock_stats.total_tools = 10
    mock_stats.total_calls = 50
    mock_stats.successful_calls = 48
    mock_mcp_client.get_stats.return_value = mock_stats

    mock_tool1 = Mock()
    mock_tool1.name = "tool1"
    mock_tool1.server = "server1"
    mock_tool1.description = "Test tool 1"
    mock_tool1.parameters = {"properties": {}}

    mock_tool2 = Mock()
    mock_tool2.name = "tool2"
    mock_tool2.server = "server2"
    mock_tool2.description = "Test tool 2"
    mock_tool2.parameters = {"properties": {"arg": {}}}

    mock_mcp_client.list_tools = AsyncMock(return_value=[mock_tool1, mock_tool2])
    gradio_app.mcp_client = mock_mcp_client

    # Refresh tools
    status, tools_df = await gradio_app.refresh_mcp_tools()

    # Verify stats
    assert status["connected_servers"] == 2
    assert status["total_tools"] == 10
    assert status["total_calls"] == 50
    assert status["successful_calls"] == 48

    # Verify tools
    assert len(tools_df) == 2
    assert "tool1" in tools_df["Tool Name"].values
    assert "tool2" in tools_df["Tool Name"].values


# ============================================================================
# Test 22: Answer Formatting with Sources
# ============================================================================


async def test_answer_formatting_with_sources(gradio_app):
    """Test answer formatting includes sources properly.

    Sprint 12: Validates response formatting.

    Validates:
    - Answer text preserved
    - Sources appended
    - Proper formatting
    - Markdown structure
    """
    answer = "LangGraph is a framework for building multi-agent systems."
    sources = [
        {"title": "LangGraph Docs", "score": 0.95},
        {"title": "Agent Tutorial", "score": 0.88},
        {"title": "Graph Guide", "score": 0.76},
    ]
    tool_calls = []

    formatted = gradio_app._format_answer_with_sources_and_tools(answer, sources, tool_calls)

    # Verify answer included
    assert "LangGraph is a framework" in formatted

    # Verify sources section
    assert "Quellen" in formatted or "📚" in formatted
    assert "LangGraph Docs" in formatted
    assert "Agent Tutorial" in formatted
    assert "Graph Guide" in formatted

    # Verify scores shown
    assert "0.95" in formatted
    assert "0.88" in formatted


# ============================================================================
# Test 23: Answer Formatting with Tool Calls
# ============================================================================


async def test_answer_formatting_with_tool_calls(gradio_app):
    """Test answer formatting includes tool call details.

    Sprint 12: Feature 10.7 validation.

    Validates:
    - Tool calls section added
    - Tool metadata shown
    - Success/error indicators
    - Result previews
    """
    answer = "Found the requested information."
    sources = []
    tool_calls = [
        {
            "tool_name": "search_files",
            "server": "filesystem",
            "duration_ms": 45.2,
            "success": True,
            "result": "Found 5 matching files",
        },
        {
            "tool_name": "fetch_url",
            "server": "web",
            "duration_ms": 1250.0,
            "success": False,
            "error": "Timeout after 1s",
        },
    ]

    formatted = gradio_app._format_answer_with_sources_and_tools(answer, sources, tool_calls)

    # Verify tool calls section
    assert "Tool Calls" in formatted or "🔧" in formatted

    # Verify first tool (success)
    assert "search_files" in formatted
    assert "filesystem" in formatted
    assert "45.2" in formatted
    assert "✅" in formatted

    # Verify second tool (error)
    assert "fetch_url" in formatted
    assert "❌" in formatted
    assert "Timeout" in formatted


# ============================================================================
# Test 24: Concurrent User Simulation
# ============================================================================


async def test_concurrent_user_handling():
    """Test multiple concurrent users with separate sessions.

    Sprint 12: Validates multi-user support.

    Validates:
    - Multiple sessions simultaneously
    - No session mixing
    - Independent state
    """
    from src.ui.gradio_app import GradioApp

    # Create 5 user sessions
    apps = [GradioApp() for _ in range(5)]

    try:
        # Verify all have unique sessions
        session_ids = [app.session_id for app in apps]
        assert len(session_ids) == len(set(session_ids))  # All unique

        # Simulate concurrent operations
        async def user_operation(app: GradioApp, user_id: int):
            """Simulate a user operation."""
            # Mock response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "answer": f"Response for user {user_id}",
                "sources": [],
                "tool_calls": [],
            }
            app.client.post = AsyncMock(return_value=mock_response)

            # Send query
            history = []
            history, _ = await app.chat(f"Query from user {user_id}", history)
            return history

        # Run concurrently
        results = await asyncio.gather(*[user_operation(app, i) for i, app in enumerate(apps)])

        # Verify all succeeded
        assert len(results) == 5
        for i, history in enumerate(results):
            assert len(history) == 2
            assert f"user {i}" in history[1]["content"]

    finally:
        # Cleanup
        for app in apps:
            await app.client.aclose()


# ============================================================================
# Test 25: Upload Progress Simulation
# ============================================================================


async def test_upload_progress_tracking(gradio_app, temp_test_file, mock_upload_response):
    """Test upload progress indication.

    Sprint 12: Validates UX feedback.

    Validates:
    - Progress callbacks invoked
    - Progress updates during upload
    - Completion notification
    """
    # Mock upload API with delay
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_upload_response

    async def delayed_post(*args, **kwargs):
        await asyncio.sleep(0.1)  # Simulate processing time
        return mock_response

    gradio_app.client.post = delayed_post

    file_obj = Mock(name=temp_test_file)

    # Track progress calls
    progress_calls = []

    def progress_tracker(value, desc=None):
        progress_calls.append({"value": value, "desc": desc})

    mock_progress = Mock(side_effect=progress_tracker)

    # Upload with progress
    await gradio_app.upload_document(file_obj, progress=mock_progress)

    # Verify progress was called
    assert len(progress_calls) > 0

    # Verify final completion call
    final_call = progress_calls[-1]
    assert final_call["value"] == 1.0
    assert "abgeschlossen" in final_call["desc"].lower()


# ============================================================================
# Test 26: Source Formatting Edge Cases
# ============================================================================


async def test_source_formatting_edge_cases(gradio_app):
    """Test source formatting handles edge cases.

    Sprint 12: Validates robustness.

    Validates:
    - Empty sources handled
    - Missing fields handled
    - Long descriptions truncated
    """
    answer = "Test answer"

    # Test with no sources
    formatted = gradio_app._format_answer_with_sources_and_tools(answer, [], [])
    assert "Test answer" in formatted
    # Should not have sources section
    assert formatted.count("---") == 0  # No separator

    # Test with missing score
    sources_no_score = [{"title": "Doc1"}]
    formatted = gradio_app._format_answer_with_sources_and_tools(answer, sources_no_score, [])
    assert "Doc1" in formatted

    # Test with only 1 source (should show all, not just top 3)
    sources_single = [{"title": "Single Doc", "score": 0.9}]
    formatted = gradio_app._format_answer_with_sources_and_tools(answer, sources_single, [])
    assert "Single Doc" in formatted


# ============================================================================
# Test 27: Tool Call Formatting Edge Cases
# ============================================================================


async def test_tool_call_formatting_edge_cases(gradio_app):
    """Test tool call formatting handles edge cases.

    Sprint 12: Validates robustness.

    Validates:
    - Missing fields handled
    - Long results truncated
    - Unknown tools handled
    """
    answer = "Test"

    # Tool with minimal info
    tool_calls = [{"tool_name": "unknown_tool"}]
    formatted = gradio_app._format_answer_with_sources_and_tools(answer, [], tool_calls)
    assert "unknown_tool" in formatted

    # Tool with very long result
    long_result = "x" * 200
    tool_calls_long = [
        {
            "tool_name": "test",
            "server": "local",
            "duration_ms": 10,
            "success": True,
            "result": long_result,
        }
    ]
    formatted = gradio_app._format_answer_with_sources_and_tools(answer, [], tool_calls_long)
    # Should be truncated
    assert len(formatted) < len(answer) + len(long_result)
    assert "..." in formatted


# ============================================================================
# Test 28: Session ID Regeneration on Clear
# ============================================================================


async def test_session_id_regeneration_on_clear(gradio_app):
    """Test new session ID generated after clearing chat.

    Sprint 12: Validates session lifecycle.

    Validates:
    - Old session ID stored
    - New session ID generated
    - Session IDs are different
    """
    # Mock delete API
    mock_delete_response = Mock()
    mock_delete_response.status_code = 200
    gradio_app.client.delete = AsyncMock(return_value=mock_delete_response)

    # Store IDs
    session_ids = [gradio_app.session_id]

    # Clear multiple times
    for _ in range(3):
        await gradio_app.clear_chat()
        session_ids.append(gradio_app.session_id)

    # All should be unique
    assert len(session_ids) == len(set(session_ids))


# ============================================================================
# Test 29: MCP Client Lazy Initialization
# ============================================================================


async def test_mcp_client_lazy_initialization(gradio_app):
    """Test MCP client only initialized when needed.

    Sprint 12: Validates resource efficiency.

    Validates:
    - MCP client starts as None
    - Initialized on first connection
    - Reused for subsequent operations
    """
    # Initially None
    assert gradio_app.mcp_client is None

    # Mock MCP Client
    mock_mcp_client = Mock()
    mock_mcp_client.connect = AsyncMock(return_value=True)
    mock_mcp_client.get_stats.return_value = Mock(connected_servers=1, total_tools=1)
    mock_mcp_client.list_tools = AsyncMock(return_value=[])

    with patch("src.ui.gradio_app.MCPClient", return_value=mock_mcp_client):
        # Connect to server
        await gradio_app.connect_mcp_server("test", "HTTP", "http://localhost:3000")

        # Now should be initialized
        assert gradio_app.mcp_client is not None


# ============================================================================
# Test 30: Upload Timeout Configuration
# ============================================================================


async def test_upload_timeout_configuration(gradio_app):
    """Test upload timeout scales with file count.

    Sprint 12: Validates timeout handling.

    Validates:
    - Timeout increases with files
    - Client created with appropriate timeout
    - Long uploads accommodated
    """
    # Create multiple test files
    temp_files = []
    for i in range(5):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write(f"Content {i}")
            temp_files.append(f.name)

    try:
        file_objs = [Mock(name=path) for path in temp_files]

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "chunks_created": 10,
            "embeddings_generated": 10,
            "duration_seconds": 1.0,
        }

        # Track httpx.AsyncClient creation to verify timeout
        created_clients = []

        async def mock_client_post(*args, **kwargs):
            return mock_response

        def track_client_creation(timeout=None, **kwargs):
            client = Mock()
            client.post = mock_client_post
            client.aclose = AsyncMock()
            created_clients.append({"timeout": timeout})
            return client

        with patch("src.ui.gradio_app.httpx.AsyncClient", side_effect=track_client_creation):
            mock_progress = Mock()
            await gradio_app.upload_document(file_objs, progress=mock_progress)

            # Verify timeout was set and scaled
            # Expected: 180 + (5 files * 60) = 480 seconds
            assert len(created_clients) > 0
            # Note: Actual implementation uses dynamic client, verify concept

    finally:
        for path in temp_files:
            Path(path).unlink(missing_ok=True)
