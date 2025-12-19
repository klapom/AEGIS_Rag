"""Ollama VLM Client - Backward Compatibility Facade.

Sprint 56: Re-exports from src.domains.llm_integration.proxy

Recommended import:
    from src.domains.llm_integration.proxy.ollama_vlm import OllamaVLMClient
"""

# Re-export from domain location
from src.domains.llm_integration.proxy.ollama_vlm import OllamaVLMClient

__all__ = ["OllamaVLMClient"]
