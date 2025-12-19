"""Ollama VLM Client - Backward Compatibility Facade.

Sprint 56: Re-exports from src.domains.llm_integration.proxy
OPL-006: These re-exports will be removed in Sprint 58.

Migrate to:
    from src.domains.llm_integration.proxy.ollama_vlm import OllamaVLMClient
"""

# OPL-006: Re-export from new domain location
from src.domains.llm_integration.proxy.ollama_vlm import OllamaVLMClient

__all__ = ["OllamaVLMClient"]
