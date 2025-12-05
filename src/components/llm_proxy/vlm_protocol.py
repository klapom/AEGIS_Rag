"""VLM Client Protocol Definition.

Sprint 36 - Feature 36.1: VLM Factory Pattern
Defines the interface that all VLM clients must implement.

This protocol ensures consistent interface across:
- OllamaVLMClient (local qwen3-vl:32b)
- DashScopeVLMClient (cloud qwen3-vl-30b)
"""

from pathlib import Path
from typing import Protocol


class VLMClient(Protocol):
    """Protocol for Vision Language Model clients.

    All VLM clients must implement this interface to be compatible
    with the VLM Factory pattern.

    Example:
        class MyVLMClient:
            async def generate_image_description(
                self,
                image_path: Path,
                prompt: str,
                model: str | None = None,
                **kwargs
            ) -> tuple[str, dict]:
                # Implementation
                pass
    """

    async def generate_image_description(
        self,
        image_path: Path,
        prompt: str,
        model: str | None = None,
        **kwargs,
    ) -> tuple[str, dict]:
        """Generate image description using VLM.

        Args:
            image_path: Path to image file (PNG, JPG, etc.)
            prompt: Text prompt describing what to extract/describe
            model: Model to use (optional, uses client default)
            **kwargs: Additional parameters (max_tokens, temperature, etc.)

        Returns:
            Tuple of (description_text, metadata_dict)

            metadata_dict must include:
            - model: str - Model identifier used
            - provider: str - Provider name (ollama, dashscope, etc.)
            - tokens_total: int - Total tokens used
            - local: bool - Whether inference was local
            - cost_usd: float - Cost in USD (0.0 for local)

        Raises:
            FileNotFoundError: If image file doesn't exist
            httpx.HTTPStatusError: On API errors
        """
        ...

    async def close(self) -> None:
        """Close HTTP client and cleanup resources.

        This method should be called when the VLM client is no longer needed
        to properly close HTTP connections and free resources.
        """
        ...
