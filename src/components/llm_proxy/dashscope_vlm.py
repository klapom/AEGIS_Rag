"""Alibaba Cloud DashScope VLM Integration.

Sprint 23 - Feature 23.4: Multi-Cloud LLM Execution
VLM Best Practices from Alibaba Cloud Documentation

This module provides direct integration with Alibaba Cloud's DashScope API
for Vision Language Models (VLM), implementing best practices:
- Primary model: qwen3-vl-30b-a3b-instruct (cheaper output tokens)
- Fallback model: qwen3-vl-30b-a3b-thinking (on 403 errors)
- enable_thinking parameter for thinking model
- vl_high_resolution_images for better quality

Reference: https://www.alibabacloud.com/help/en/model-studio/vision
"""

import base64
import os
from pathlib import Path

import httpx
import structlog
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = structlog.get_logger(__name__)


class DashScopeVLMClient:
    """Client for Alibaba Cloud DashScope Vision Language Models."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """Initialize DashScope VLM client.

        Args:
            api_key: DashScope API key (defaults to env var)
            base_url: DashScope base URL (defaults to env var)
        """
        # Load from environment variables directly
        self.api_key = api_key or os.getenv("ALIBABA_CLOUD_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or ""
        self.base_url = base_url or os.getenv(
            "ALIBABA_CLOUD_BASE_URL",
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        )

        if not self.api_key:
            raise ValueError("DashScope API key not configured. Set ALIBABA_CLOUD_API_KEY or DASHSCOPE_API_KEY env var.")

        self.client = httpx.AsyncClient(timeout=120.0)

        logger.info(
            "DashScopeVLMClient initialized",
            base_url=self.base_url,
            has_api_key=bool(self.api_key),
        )

    async def generate_image_description(
        self,
        image_path: Path,
        prompt: str,
        model: str = "qwen3-vl-30b-a3b-instruct",
        enable_thinking: bool = False,
        vl_high_resolution_images: bool = True,
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> tuple[str, dict]:
        """Generate image description using DashScope VLM.

        Args:
            image_path: Path to image file
            prompt: Text prompt for VLM
            model: Model to use (instruct or thinking)
            enable_thinking: Enable reasoning mode (thinking model only)
            vl_high_resolution_images: Use high-res processing (16,384 vs 2,560 tokens)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Tuple of (description_text, metadata_dict)

        Raises:
            httpx.HTTPStatusError: On API errors (403, 429, etc.)
            FileNotFoundError: If image file doesn't exist
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Read and encode image
        with open(image_path, "rb") as f:
            image_data = f.read()

        image_base64 = base64.b64encode(image_data).decode("utf-8")

        # Determine MIME type
        suffix = image_path.suffix.lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_types.get(suffix, "image/png")

        # Build request payload (OpenAI-compatible format)
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}"
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Add VLM-specific parameters
        if enable_thinking and "thinking" in model:
            payload["enable_thinking"] = True

        if vl_high_resolution_images:
            payload["vl_high_resolution_images"] = True

        # Make API request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.info(
            "Sending VLM request to DashScope",
            model=model,
            image_size_kb=len(image_data) / 1024,
            enable_thinking=enable_thinking,
            vl_high_res=vl_high_resolution_images,
        )

        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )

            response.raise_for_status()

            data = response.json()

            # Extract description
            description = data["choices"][0]["message"]["content"]

            # Extract metadata
            metadata = {
                "model": data.get("model", model),
                "tokens_input": data.get("usage", {}).get("prompt_tokens", 0),
                "tokens_output": data.get("usage", {}).get("completion_tokens", 0),
                "tokens_total": data.get("usage", {}).get("total_tokens", 0),
                "finish_reason": data["choices"][0].get("finish_reason"),
            }

            logger.info(
                "VLM description generated",
                model=metadata["model"],
                tokens_total=metadata["tokens_total"],
                description_length=len(description),
            )

            return description, metadata

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.warning(
                    "403 Forbidden from DashScope (model quota?)",
                    model=model,
                    status_code=403,
                )
            raise

    async def generate_with_fallback(
        self,
        image_path: Path,
        prompt: str,
        primary_model: str = "qwen3-vl-30b-a3b-instruct",
        fallback_model: str = "qwen3-vl-30b-a3b-thinking",
        **kwargs,
    ) -> tuple[str, dict]:
        """Generate image description with automatic fallback.

        Tries primary model first (instruct - cheaper), falls back to thinking on 403.

        Args:
            image_path: Path to image
            prompt: Text prompt
            primary_model: First model to try
            fallback_model: Fallback on 403 errors
            **kwargs: Additional parameters for generate_image_description

        Returns:
            Tuple of (description_text, metadata_dict)
        """
        # Try primary model first
        try:
            logger.info(
                "Attempting VLM with primary model",
                model=primary_model,
            )

            description, metadata = await self.generate_image_description(
                image_path=image_path,
                prompt=prompt,
                model=primary_model,
                enable_thinking=False,  # Instruct model doesn't use thinking
                **kwargs,
            )

            metadata["fallback_used"] = False
            metadata["model_attempted"] = primary_model

            return description, metadata

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 403:
                logger.warning(
                    "Primary VLM model returned 403, trying fallback",
                    primary_model=primary_model,
                    fallback_model=fallback_model,
                )

                # Try fallback model
                description, metadata = await self.generate_image_description(
                    image_path=image_path,
                    prompt=prompt,
                    model=fallback_model,
                    enable_thinking=True,  # Thinking model benefits from this
                    **kwargs,
                )

                metadata["fallback_used"] = True
                metadata["model_attempted"] = primary_model
                metadata["fallback_reason"] = "403_forbidden"

                return description, metadata
            else:
                # Other HTTP errors - re-raise
                raise

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


async def get_dashscope_vlm_client() -> DashScopeVLMClient:
    """Get DashScope VLM client (singleton pattern).

    Returns:
        DashScopeVLMClient instance
    """
    # Simple factory - could be enhanced with caching/singleton
    return DashScopeVLMClient()
