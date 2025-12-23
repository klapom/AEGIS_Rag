"""
Pytest configuration for cache tests.

Avoids loading the main app to prevent import errors.
"""

import pytest


@pytest.fixture
def anyio_backend():
    """Use asyncio as the async backend."""
    return "asyncio"
