"""Pytest configuration for LLM proxy tests - isolated from global conftest."""

import pytest


# Override global conftest to prevent loading the full API
def pytest_configure(config):
    """Configure pytest for isolated LLM proxy tests."""
    pass
