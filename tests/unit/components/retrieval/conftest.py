"""Local conftest for retrieval tests to avoid app import issues."""

import pytest


# Override the global conftest to avoid importing the app
pytest_plugins = []
