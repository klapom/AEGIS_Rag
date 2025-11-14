"""Embedding Service for nomic-embed-text via Ollama.

============================================================================
⚠️ DEPRECATED: Sprint 25 Feature 25.8 - This module is deprecated
============================================================================
EmbeddingService wrapper was removed. Use UnifiedEmbeddingService directly.

REPLACEMENT:
  from src.components.shared.embedding_service import (
      UnifiedEmbeddingService,
      get_embedding_service
  )

Backward compatibility aliases are provided below (deprecation period: Sprint 25-26)
============================================================================
"""

import warnings

# Backward compatibility re-exports (Sprint 25 Feature 25.8)
from src.components.shared.embedding_service import (
    UnifiedEmbeddingService as EmbeddingService,
)
from src.components.shared.embedding_service import (
    get_embedding_service,
)

# Deprecation warning
warnings.warn(
    "src.components.vector_search.embeddings is deprecated. "
    "Use src.components.shared.embedding_service instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["EmbeddingService", "get_embedding_service"]
