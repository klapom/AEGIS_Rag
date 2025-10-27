"""Health check modules for AEGIS RAG."""

# Re-export router from parent health.py to maintain backward compatibility
# This allows imports like: from src.api.health import router
# Note: This is a workaround because we have both health.py and health/ directory

import sys
from pathlib import Path

# Import from the parent health.py file
parent_dir = Path(__file__).parent.parent
health_module_path = parent_dir / "health.py"

if health_module_path.exists():
    import importlib.util

    spec = importlib.util.spec_from_file_location("health_module", health_module_path)
    if spec and spec.loader:
        health_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(health_module)
        router = health_module.router
        __all__ = ["router"]
