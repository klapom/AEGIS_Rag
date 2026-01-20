"""Core models package for AegisRAG.

Sprint 117 Feature 117.8: Response Format Standardization (3 SP)

This package contains both the legacy models.py exports and new response models.
"""

# Sprint 117.8: New standardized response models
from src.core.models.response import (
    ApiError,
    ApiErrorResponse,
    ApiResponse,
    PaginationMeta,
    RequestMetadata,
)

# Re-export all existing models from models.py to maintain backwards compatibility
# This ensures existing imports like "from src.core.models import ErrorCode" still work
import sys
from pathlib import Path

# Import the models.py module as a sibling
models_py_path = Path(__file__).parent.parent / "models.py"
if models_py_path.exists():
    # Import all public symbols from models.py
    import importlib.util
    spec = importlib.util.spec_from_file_location("_legacy_models", models_py_path)
    if spec and spec.loader:
        _legacy_models = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_legacy_models)

        # Re-export all public symbols
        for name in dir(_legacy_models):
            if not name.startswith("_"):
                globals()[name] = getattr(_legacy_models, name)

__all__ = [
    # Sprint 117.8: New response models
    "ApiError",
    "ApiErrorResponse",
    "ApiResponse",
    "PaginationMeta",
    "RequestMetadata",
]
