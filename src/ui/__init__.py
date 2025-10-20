"""User Interface module for AEGIS RAG.

Sprint 10: Gradio-based MVP UI
"""

__all__ = ["GradioApp"]

try:
    from src.ui.gradio_app import GradioApp
except ImportError:
    # Gradio not installed
    GradioApp = None  # type: ignore
