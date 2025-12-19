"""Ollama VLM Client for local image understanding.

Sprint 36 - Feature 36.2: OllamaVLMClient Implementation
Uses qwen3-vl:32b for image understanding on DGX Spark.

Ollama VLM API Documentation:
    POST /api/generate
    {
        "model": "qwen3-vl:32b",
        "prompt": "Describe this image",
        "images": ["base64_encoded_image"],
        "stream": false
    }
"""

import base64
import os
from pathlib import Path

import httpx
import structlog

logger = structlog.get_logger(__name__)


class OllamaVLMClient:
    """Local VLM client using Ollama API.

    Uses qwen3-vl:32b for image understanding on DGX Spark.
    Cost: $0 (local inference)
    Privacy: Data stays on-premise

    Example:
        client = OllamaVLMClient()
        description, metadata = await client.generate_image_description(
            image_path=Path("image.png"),
            prompt="Describe this technical diagram"
        )
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 120.0,
        default_model: str | None = None,
    ):
        """Initialize Ollama VLM client.

        Args:
            base_url: Ollama API URL (default: OLLAMA_BASE_URL env or localhost:11434)
            timeout: Request timeout in seconds
            default_model: Default model (default: OLLAMA_MODEL_VLM env or qwen3-vl:32b)
        """
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.timeout = timeout
        self.default_model = default_model or os.getenv("OLLAMA_MODEL_VLM", "qwen3-vl:32b")
        self.client = httpx.AsyncClient(timeout=timeout)

        logger.info(
            "OllamaVLMClient initialized",
            base_url=self.base_url,
            default_model=self.default_model,
        )

    async def generate_image_description(
        self,
        image_path: Path,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> tuple[str, dict]:
        """Generate image description using local Ollama VLM.

        Args:
            image_path: Path to image file (PNG, JPG, etc.)
            prompt: Text prompt describing what to extract/describe
            model: Model to use (default: qwen3-vl:32b)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-2.0)

        Returns:
            Tuple of (description_text, metadata_dict)

        Raises:
            FileNotFoundError: If image file doesn't exist
            httpx.HTTPStatusError: On API errors
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        model = model or self.default_model

        # Read and encode image as base64
        with open(image_path, "rb") as f:
            image_data = f.read()
        image_base64 = base64.b64encode(image_data).decode("utf-8")

        # Ollama /api/generate request payload
        # Sprint 36: Add think=false to disable Qwen3 thinking mode (127x speedup)
        payload = {
            "model": model,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
            "think": False,  # Disable Qwen3 thinking mode for faster inference
            "options": {"num_predict": max_tokens, "temperature": temperature},
        }

        logger.info(
            "Sending VLM request to Ollama",
            model=model,
            image_size_kb=len(image_data) / 1024,
            prompt_length=len(prompt),
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            description = data.get("response", "")

            # Build metadata dict
            metadata = {
                "model": model,
                "provider": "ollama",
                "backend": "local",
                "tokens_total": data.get("eval_count", 0),
                "tokens_prompt": data.get("prompt_eval_count", 0),
                "duration_ms": data.get("total_duration", 0) / 1_000_000,  # ns to ms
                "eval_duration_ms": data.get("eval_duration", 0) / 1_000_000,
                "local": True,
                "cost_usd": 0.0,  # Local inference is free!
            }

            logger.info(
                "VLM description generated (local)",
                model=model,
                tokens=metadata["tokens_total"],
                duration_ms=round(metadata["duration_ms"], 2),
                description_length=len(description),
            )

            return description, metadata

        except httpx.HTTPStatusError as e:
            logger.error(
                "Ollama VLM request failed",
                status_code=e.response.status_code,
                model=model,
                error=str(e),
            )
            raise
        except httpx.ConnectError as e:
            logger.error(
                "Cannot connect to Ollama",
                base_url=self.base_url,
                error=str(e),
            )
            raise

    async def check_model_available(self, model: str | None = None) -> bool:
        """Check if VLM model is available in Ollama.

        Args:
            model: Model to check (default: configured default model)

        Returns:
            True if model is available, False otherwise
        """
        model = model or self.default_model
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()

            available_models = [m.get("name", "") for m in data.get("models", [])]
            is_available = any(model in m or m in model for m in available_models)

            logger.debug(
                "Model availability check",
                model=model,
                available=is_available,
                total_models=len(available_models),
            )

            return is_available
        except Exception as e:
            logger.warning(f"Could not check model availability: {e}")
            return False

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
        logger.debug("OllamaVLMClient closed")

    async def __aenter__(self) -> "OllamaVLMClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, _exc_type, _exc_val, _exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
