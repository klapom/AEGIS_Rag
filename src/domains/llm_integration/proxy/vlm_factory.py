"""VLM Factory Pattern for backend switching.

Sprint 56: Migrated from src/components/llm_proxy/vlm_factory.py
Original Sprint Context: Sprint 36 (2025-12-05) - Feature 36.1: VLM Factory Pattern
Enables switching between local (Ollama) and cloud (DashScope) VLM backends.

Architecture:
    - Factory pattern for backend selection (similar to embedding_factory.py)
    - Configuration-driven (VLM_BACKEND env var + llm_config.yml)
    - Protocol-based interface for type safety
    - Global singleton pattern for efficiency

Supported Backends:
    - 'ollama': Local qwen3-vl:32b via Ollama API (DGX Spark default)
    - 'dashscope': Alibaba Cloud qwen3-vl-30b (cloud fallback)

Configuration Priority:
    1. VLM_BACKEND environment variable
    2. llm_config.yml routing.vlm_backend
    3. Default: 'ollama' (local-first for DGX Spark)

Example:
    >>> from src.domains.llm_integration.proxy import get_vlm_client
    >>> client = get_vlm_client()  # Uses config/env
    >>> description, metadata = await client.generate_image_description(
    ...     image_path=Path("image.png"),
    ...     prompt="Describe this image"
    ... )

Example (Explicit Backend):
    >>> from src.domains.llm_integration.proxy import get_vlm_client, VLMBackend
    >>> client = get_vlm_client(VLMBackend.DASHSCOPE)  # Force cloud

Example (Singleton Pattern):
    >>> from src.domains.llm_integration.proxy import get_shared_vlm_client
    >>> client = await get_shared_vlm_client()  # Cached globally

Important Note:
    VLM cannot use ANY-LLM (acompletion()) because image inputs are not supported.
    VLM must remain separate from AegisLLMProxy.

See Also:
    - src/domains/llm_integration/proxy/ollama_vlm.py: Local Ollama backend
    - src/domains/llm_integration/proxy/dashscope_vlm.py: Cloud DashScope backend
    - src/components/shared/embedding_factory.py: Similar factory pattern
    - config/llm_config.yml: VLM backend configuration
"""

import os
from enum import Enum

import structlog

from src.domains.llm_integration.proxy.vlm_protocol import VLMClient

logger = structlog.get_logger(__name__)


class VLMBackend(str, Enum):
    """Available VLM backends.

    Attributes:
        OLLAMA: Local qwen3-vl:32b via Ollama API (DGX Spark default)
        DASHSCOPE: Alibaba Cloud qwen3-vl-30b (cloud fallback)
    """

    OLLAMA = "ollama"
    DASHSCOPE = "dashscope"


def get_vlm_backend_from_config() -> VLMBackend:
    """Get VLM backend from configuration.

    Priority:
        1. VLM_BACKEND environment variable
        2. llm_config.yml routing.vlm_backend
        3. Default: OLLAMA (local-first for DGX Spark)

    Returns:
        VLMBackend enum value

    Example:
        >>> backend = get_vlm_backend_from_config()
        >>> print(backend)
        VLMBackend.OLLAMA

    Notes:
        - Invalid values log warning and use default
        - Default is OLLAMA for DGX Spark (local-first)
        - Config file is optional (falls back to env var)
    """
    # Priority 1: Check environment variable
    backend_str = os.getenv("VLM_BACKEND")
    if backend_str:
        try:
            backend = VLMBackend(backend_str.lower())
            logger.info(
                "vlm_backend_from_env",
                backend=backend.value,
                source="VLM_BACKEND env var",
            )
            return backend
        except ValueError:
            logger.warning(
                "invalid_vlm_backend_env",
                value=backend_str,
                valid_values=["ollama", "dashscope"],
                using_default="ollama",
            )

    # Priority 2: Check config file
    try:
        from src.domains.llm_integration.config import get_llm_proxy_config

        config = get_llm_proxy_config()
        vlm_backend = config.routing.get("vlm_backend")

        if vlm_backend:
            backend = VLMBackend(vlm_backend.lower())
            logger.info(
                "vlm_backend_from_config",
                backend=backend.value,
                source="llm_config.yml",
            )
            return backend
    except Exception as e:
        logger.debug("could_not_load_vlm_config", error=str(e))

    # Priority 3: Default to local (DGX Spark)
    logger.info(
        "vlm_backend_default",
        backend="ollama",
        reason="No config found, using local-first default",
    )
    return VLMBackend.OLLAMA


def get_vlm_client(backend: VLMBackend | None = None, model: str | None = None) -> VLMClient:
    """Factory function for VLM clients.

    Creates VLM client based on backend selection. Uses lazy imports
    to avoid loading unnecessary dependencies.

    Sprint 66 Fix (TD-077): Now accepts model parameter for Admin UI integration.

    Args:
        backend: Explicit backend selection. If None, uses config/env.
        model: Model ID to use (e.g., "ollama/qwen3-vl:4b-instruct"). If None, uses backend default.

    Returns:
        VLMClient instance (OllamaVLMClient or DashScopeVLMClient)

    Raises:
        ValueError: If backend is invalid
        ImportError: If backend dependencies are missing

    Example:
        >>> # Use config/env
        >>> client = get_vlm_client()

        >>> # Force specific backend
        >>> client = get_vlm_client(VLMBackend.DASHSCOPE)

        >>> # Specify model from Admin UI config
        >>> client = get_vlm_client(VLMBackend.OLLAMA, model="ollama/qwen3-vl:4b-instruct")

    Notes:
        - Does NOT use singleton pattern (caller manages instance)
        - Use get_shared_vlm_client() for singleton behavior
        - Lazy imports to avoid circular dependencies
    """
    if backend is None:
        backend = get_vlm_backend_from_config()

    # Sprint 66: Extract model name from full model_id (e.g., "ollama/qwen3-vl:4b" → "qwen3-vl:4b")
    default_model = None
    if model:
        # Handle both "ollama/qwen3-vl:4b-instruct" and "qwen3-vl:4b-instruct"
        if "/" in model:
            default_model = model.split("/", 1)[1]  # Extract model name after provider prefix
        else:
            default_model = model

    logger.info("creating_vlm_client", backend=backend.value, model=default_model or "default")

    if backend == VLMBackend.OLLAMA:
        # Lazy import to avoid loading when not needed
        from src.domains.llm_integration.proxy.ollama_vlm import OllamaVLMClient

        return OllamaVLMClient(default_model=default_model)

    elif backend == VLMBackend.DASHSCOPE:
        # Lazy import to avoid loading when not needed
        from src.domains.llm_integration.proxy.dashscope_vlm import DashScopeVLMClient

        return DashScopeVLMClient()

    else:
        raise ValueError(
            f"Invalid VLM backend: {backend}. " f"Must be VLMBackend.OLLAMA or VLMBackend.DASHSCOPE"
        )


# Global singleton instance for shared usage
_vlm_client: VLMClient | None = None


async def get_shared_vlm_client() -> VLMClient:
    """Get shared VLM client instance (singleton pattern).

    Use this for repeated calls to avoid creating new clients.
    Client is created on first call and cached globally.

    Returns:
        VLMClient instance (cached globally)

    Example:
        >>> # All calls use same instance
        >>> client1 = await get_shared_vlm_client()
        >>> client2 = await get_shared_vlm_client()
        >>> assert client1 is client2

    Notes:
        - Thread-safe for async contexts
        - To change backend, call close_shared_vlm_client() first
        - Backend is determined on first call (config/env)

    See Also:
        close_shared_vlm_client: Clean up singleton instance
    """
    global _vlm_client

    if _vlm_client is None:
        _vlm_client = get_vlm_client()
        logger.info("shared_vlm_client_created")

    return _vlm_client


async def close_shared_vlm_client() -> None:
    """Close shared VLM client and reset singleton.

    Cleans up resources from shared client instance.
    Safe to call multiple times (no-op if client is None).

    Example:
        >>> await close_shared_vlm_client()
        >>> # Next call to get_shared_vlm_client() creates new instance

    Notes:
        - Automatically called on application shutdown
        - Use in tests to reset state between test cases
        - No-op if no shared client exists
    """
    global _vlm_client

    if _vlm_client is not None:
        await _vlm_client.close()
        _vlm_client = None
        logger.info("shared_vlm_client_closed")


def reset_vlm_client() -> None:
    """Reset global VLM client instance without closing.

    Used for testing to force reinitialization with different config.
    Does NOT call close() on existing client (use close_shared_vlm_client for that).

    Example:
        >>> from src.domains.llm_integration.proxy import reset_vlm_client
        >>> reset_vlm_client()
        >>> client = await get_shared_vlm_client()  # Forces reinitialization

    Notes:
        - Test utility only - DO NOT use in production
        - Prefer close_shared_vlm_client() for proper cleanup
    """
    global _vlm_client
    _vlm_client = None
    logger.debug("vlm_client_reset")
