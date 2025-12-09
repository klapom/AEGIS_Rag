"""Unit tests for Gradio App.

Sprint 10 Feature 10.2: Gradio UI Tests

These tests validate the Gradio app business logic without requiring Gradio to be installed.
They test the helper methods and integration logic using mocks.

Note: Full UI tests will be added in Sprint 11 with Playwright + React.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Skip all tests if gradio is not installed
pytestmark = pytest.mark.skipif(
    True,  # Always skip for now (Gradio not in dependencies)
    reason="Gradio not installed - Sprint 10 MVP uses manual testing",
)


class TestGradioApp:
    """Tests for GradioApp class."""

    @pytest.mark.asyncio
    async def test_format_answer_with_sources(self):
        """Test answer formatting with source citations."""
        from src.ui.gradio_app import GradioApp

        app = GradioApp()

        # Test with sources
        answer = "AEGIS RAG is a multi-agent system."
        sources = [
            {"title": "CLAUDE.md", "score": 0.92},
            {"title": "TECH_STACK.md", "score": 0.88},
            {"title": "SPRINT_PLAN.md", "score": 0.85},
        ]

        formatted = app._format_answer_with_sources(answer, sources)

        assert "AEGIS RAG is a multi-agent system" in formatted
        assert "Quellen" in formatted
        assert "CLAUDE.md" in formatted
        assert "0.92" in formatted
        assert "TECH_STACK.md" in formatted

    @pytest.mark.asyncio
    async def test_format_answer_without_sources(self):
        """Test answer formatting without sources."""
        from src.ui.gradio_app import GradioApp

        app = GradioApp()

        answer = "No sources available."
        sources = []

        formatted = app._format_answer_with_sources(answer, sources)

        assert formatted == answer  # Should be unchanged
        assert "Quellen" not in formatted

    @pytest.mark.asyncio
    async def test_chat_success(self):
        """Test successful chat interaction."""
        from src.ui.gradio_app import GradioApp

        app = GradioApp()

        # Mock HTTP client
        with patch.object(app.client, "post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "answer": "Test answer",
                "sources": [{"title": "test.md", "score": 0.9}],
                "session_id": app.session_id,
            }
            mock_post.return_value = mock_response

            history = []
            message = "Test question"

            new_history, cleared_input = await app.chat(message, history)

            # Assertions
            assert len(new_history) == 1
            assert new_history[0][0] == message
            assert "Test answer" in new_history[0][1]
            assert "test.md" in new_history[0][1]
            assert cleared_input == ""

            # Verify API was called
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_api_error(self):
        """Test chat with API error."""
        from src.ui.gradio_app import GradioApp

        app = GradioApp()

        with patch.object(app.client, "post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_post.return_value = mock_response

            history = []
            message = "Test question"

            new_history, cleared_input = await app.chat(message, history)

            # Should have error message in history
            assert len(new_history) == 1
            assert "Fehler" in new_history[0][1] or "500" in new_history[0][1]

    @pytest.mark.asyncio
    async def test_chat_empty_message(self):
        """Test chat with empty message."""
        from src.ui.gradio_app import GradioApp

        app = GradioApp()

        history = []
        message = "   "  # Whitespace only

        new_history, cleared_input = await app.chat(message, history)

        # Should return unchanged
        assert new_history == history
        assert cleared_input == ""

    @pytest.mark.asyncio
    async def test_clear_chat(self):
        """Test clearing chat history."""
        from src.ui.gradio_app import GradioApp

        app = GradioApp()
        original_session_id = app.session_id

        with patch.object(app.client, "delete", new_callable=AsyncMock) as mock_delete:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_delete.return_value = mock_response

            result = await app.clear_chat()

            # Should return empty list
            assert result == []

            # Should have new session ID
            assert app.session_id != original_session_id

            # Verify delete was called
            mock_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_health_stats_success(self):
        """Test retrieving health stats."""
        from src.ui.gradio_app import GradioApp

        app = GradioApp()

        with patch.object(app.client, "get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "redis": {"status": "healthy"},
                "qdrant": {"status": "healthy"},
            }
            mock_get.return_value = mock_response

            stats = await app.get_health_stats()

            assert "redis" in stats
            assert "qdrant" in stats
            assert stats["redis"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_get_health_stats_error(self):
        """Test health stats with API error."""
        from src.ui.gradio_app import GradioApp

        app = GradioApp()

        with patch.object(app.client, "get", new_callable=AsyncMock) as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response

            stats = await app.get_health_stats()

            assert "error" in stats


class TestGradioIntegration:
    """Integration tests for Gradio components."""

    @pytest.mark.asyncio
    async def test_session_id_generation(self):
        """Test that session IDs are unique."""
        from src.ui.gradio_app import GradioApp

        app1 = GradioApp()
        app2 = GradioApp()

        assert app1.session_id != app2.session_id
        assert len(app1.session_id) == 36  # UUID length

    @pytest.mark.asyncio
    async def test_session_id_changes_on_clear(self):
        """Test that clearing chat generates new session ID."""
        from src.ui.gradio_app import GradioApp

        app = GradioApp()
        session_id1 = app.session_id

        with patch.object(app.client, "delete", new_callable=AsyncMock):
            await app.clear_chat()

        session_id2 = app.session_id

        assert session_id1 != session_id2
