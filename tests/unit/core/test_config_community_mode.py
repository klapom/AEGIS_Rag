"""Unit tests for community detection mode configuration.

Sprint 126 Feature 126.1: Scheduled Community Detection
"""

import pytest
from pydantic import ValidationError

from src.core.config import Settings


def test_community_detection_mode_scheduled():
    """Test scheduled mode (default)."""
    settings = Settings()
    assert settings.graph_community_detection_mode == "scheduled"


def test_community_detection_mode_sync():
    """Test sync mode configuration."""
    settings = Settings(graph_community_detection_mode="sync")
    assert settings.graph_community_detection_mode == "sync"


def test_community_detection_mode_disabled():
    """Test disabled mode configuration."""
    settings = Settings(graph_community_detection_mode="disabled")
    assert settings.graph_community_detection_mode == "disabled"


def test_community_detection_mode_invalid():
    """Test invalid mode raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(graph_community_detection_mode="invalid_mode")

    # Check that validation error mentions valid choices
    error_msg = str(exc_info.value)
    assert "sync" in error_msg or "scheduled" in error_msg or "disabled" in error_msg
