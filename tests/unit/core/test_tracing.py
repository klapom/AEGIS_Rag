"""Unit tests for LangSmith tracing integration.

Sprint 4 Feature 4.5: LangSmith Integration
Tests tracing setup, environment variables, and configuration.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from src.core.tracing import (
    disable_langsmith_tracing,
    get_trace_url,
    is_tracing_enabled,
    setup_langsmith_tracing,
)


@pytest.fixture(autouse=True)
def clean_env():
    """Clean up LangChain environment variables before and after each test."""
    # Clean before test
    env_vars = [
        "LANGCHAIN_TRACING_V2",
        "LANGCHAIN_PROJECT",
        "LANGCHAIN_API_KEY",
        "LANGCHAIN_ENDPOINT",
    ]
    for var in env_vars:
        os.environ.pop(var, None)

    yield

    # Clean after test
    for var in env_vars:
        os.environ.pop(var, None)


def test_setup_langsmith_tracing_disabled_by_default(clean_env):
    """Test tracing is disabled when langsmith_tracing=False."""
    with patch("src.core.tracing.settings") as mock_settings:
        mock_settings.langsmith_tracing = False
        mock_settings.langsmith_api_key = SecretStr("test-key")
        mock_settings.langsmith_project = "test-project"

        result = setup_langsmith_tracing()

        assert result is False
        assert os.environ.get("LANGCHAIN_TRACING_V2") != "true"


def test_setup_langsmith_tracing_disabled_no_api_key(clean_env):
    """Test tracing is disabled when no API key provided."""
    with patch("src.core.tracing.settings") as mock_settings:
        mock_settings.langsmith_tracing = True
        mock_settings.langsmith_api_key = None
        mock_settings.langsmith_project = "test-project"

        result = setup_langsmith_tracing()

        assert result is False
        assert os.environ.get("LANGCHAIN_TRACING_V2") != "true"


def test_setup_langsmith_tracing_enabled(clean_env):
    """Test tracing is enabled with valid configuration."""
    with patch("src.core.tracing.settings") as mock_settings:
        mock_settings.langsmith_tracing = True
        mock_settings.langsmith_api_key = SecretStr("test-api-key-123")
        mock_settings.langsmith_project = "test-project"

        result = setup_langsmith_tracing()

        assert result is True
        assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
        assert os.environ.get("LANGCHAIN_PROJECT") == "test-project"
        assert os.environ.get("LANGCHAIN_API_KEY") == "test-api-key-123"


def test_setup_langsmith_tracing_sets_environment_variables(clean_env):
    """Test tracing sets all required environment variables."""
    with patch("src.core.tracing.settings") as mock_settings:
        mock_settings.langsmith_tracing = True
        mock_settings.langsmith_api_key = SecretStr("api-key")
        mock_settings.langsmith_project = "my-project"

        setup_langsmith_tracing()

        assert os.environ["LANGCHAIN_TRACING_V2"] == "true"
        assert os.environ["LANGCHAIN_PROJECT"] == "my-project"
        assert os.environ["LANGCHAIN_API_KEY"] == "api-key"


def test_disable_langsmith_tracing(clean_env):
    """Test disabling tracing removes environment variables."""
    # Set up tracing first
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "test-project"
    os.environ["LANGCHAIN_API_KEY"] = "test-key"

    # Disable tracing
    disable_langsmith_tracing()

    # Verify environment variables are removed
    assert "LANGCHAIN_TRACING_V2" not in os.environ
    assert "LANGCHAIN_PROJECT" not in os.environ
    assert "LANGCHAIN_API_KEY" not in os.environ


def test_is_tracing_enabled_true(clean_env):
    """Test is_tracing_enabled returns True when enabled."""
    os.environ["LANGCHAIN_TRACING_V2"] = "true"

    assert is_tracing_enabled() is True


def test_is_tracing_enabled_false(clean_env):
    """Test is_tracing_enabled returns False when disabled."""
    assert is_tracing_enabled() is False


def test_is_tracing_enabled_false_with_other_value(clean_env):
    """Test is_tracing_enabled returns False with non-'true' value."""
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

    assert is_tracing_enabled() is False


def test_get_trace_url():
    """Test get_trace_url generates correct URL."""
    with patch("src.core.tracing.settings") as mock_settings:
        mock_settings.langsmith_project = "my-project"

        url = get_trace_url("abc123")

        assert "smith.langchain.com" in url
        assert "my-project" in url
        assert "abc123" in url
        assert url == "https://smith.langchain.com/o/default/projects/p/my-project/r/abc123"


def test_setup_and_disable_cycle(clean_env):
    """Test setup and disable can be called multiple times."""
    with patch("src.core.tracing.settings") as mock_settings:
        mock_settings.langsmith_tracing = True
        mock_settings.langsmith_api_key = SecretStr("test-key")
        mock_settings.langsmith_project = "test-project"

        # Enable
        result1 = setup_langsmith_tracing()
        assert result1 is True
        assert is_tracing_enabled() is True

        # Disable
        disable_langsmith_tracing()
        assert is_tracing_enabled() is False

        # Enable again
        result2 = setup_langsmith_tracing()
        assert result2 is True
        assert is_tracing_enabled() is True


def test_setup_langsmith_tracing_exception_handling(clean_env):
    """Test setup handles exceptions gracefully."""
    with patch("src.core.tracing.settings") as mock_settings:
        # Create a settings object that will raise an exception
        mock_settings.langsmith_tracing = True
        mock_settings.langsmith_api_key = SecretStr("test-key")
        # Make project property raise exception
        type(mock_settings).langsmith_project = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("Test error"))
        )

        result = setup_langsmith_tracing()

        # Should return False and not crash
        assert result is False


def test_disable_langsmith_tracing_when_not_set(clean_env):
    """Test disable works even when variables aren't set."""
    # Should not raise exception
    disable_langsmith_tracing()

    # Verify nothing is set
    assert "LANGCHAIN_TRACING_V2" not in os.environ
    assert "LANGCHAIN_PROJECT" not in os.environ


def test_tracing_environment_isolation(clean_env):
    """Test tracing doesn't interfere with other environment variables."""
    # Set some unrelated environment variables
    os.environ["CUSTOM_VAR"] = "value"
    os.environ["ANOTHER_VAR"] = "another"

    with patch("src.core.tracing.settings") as mock_settings:
        mock_settings.langsmith_tracing = True
        mock_settings.langsmith_api_key = SecretStr("test-key")
        mock_settings.langsmith_project = "test-project"

        setup_langsmith_tracing()

        # Verify custom vars are untouched
        assert os.environ["CUSTOM_VAR"] == "value"
        assert os.environ["ANOTHER_VAR"] == "another"

        disable_langsmith_tracing()

        # Verify custom vars still exist
        assert os.environ["CUSTOM_VAR"] == "value"
        assert os.environ["ANOTHER_VAR"] == "another"

    # Clean up
    del os.environ["CUSTOM_VAR"]
    del os.environ["ANOTHER_VAR"]
