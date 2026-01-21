"""LLM Model Discovery Service for Domain Training.

Sprint 117 Feature 117.12: Per-domain LLM model selection

This module provides functionality for discovering available LLM models
from Ollama and providing recommendations for different use cases
(training, extraction, classification).

Key Features:
- Query Ollama API for available models
- Categorize models by size and recommended use case
- Provide model recommendations for training vs extraction
- Validate model availability before domain creation

Example:
    >>> service = ModelService()
    >>> models = await service.get_available_models()
    >>> recommendations = service.get_model_recommendations(models)
"""

import httpx
import structlog
from typing import Any

from src.core.config import settings
from src.core.exceptions import ExternalServiceError

logger = structlog.get_logger(__name__)

# Model size thresholds (in GB)
SMALL_MODEL_THRESHOLD_GB = 5.0  # < 5GB = fast extraction
MEDIUM_MODEL_THRESHOLD_GB = 15.0  # 5-15GB = balanced
LARGE_MODEL_THRESHOLD_GB = 15.0  # > 15GB = training quality


class ModelInfo:
    """Structured model information.

    Attributes:
        id: Model ID (e.g., "nemotron3", "qwen3:32b")
        name: Human-readable name
        size_gb: Model size in GB
        provider: Model provider (e.g., "ollama")
        recommended_for: List of use cases (training/extraction/classification)
        speed: Speed category (fast/medium/slow)
        quality: Quality category (good/excellent)
        available: Whether model is currently available
    """

    def __init__(
        self,
        id: str,
        name: str,
        size_gb: float,
        provider: str = "ollama",
        recommended_for: list[str] | None = None,
        speed: str = "medium",
        quality: str = "good",
        available: bool = True,
    ):
        self.id = id
        self.name = name
        self.size_gb = size_gb
        self.provider = provider
        self.recommended_for = recommended_for or []
        self.speed = speed
        self.quality = quality
        self.available = available

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "size_gb": round(self.size_gb, 2),
            "recommended_for": self.recommended_for,
            "speed": self.speed,
            "quality": self.quality,
            "available": self.available,
        }


class ModelService:
    """Service for LLM model discovery and recommendations.

    Provides methods for:
    - Querying Ollama for available models
    - Categorizing models by size and capabilities
    - Recommending models for training vs extraction
    - Validating model availability
    """

    def __init__(self, ollama_base_url: str | None = None):
        """Initialize model service.

        Args:
            ollama_base_url: Ollama API base URL (default: from settings)
        """
        self.ollama_base_url = ollama_base_url or settings.ollama_base_url
        logger.info(
            "model_service_initialized",
            ollama_base_url=self.ollama_base_url,
        )

    async def get_available_models(self) -> list[ModelInfo]:
        """Query Ollama API for available models.

        Returns:
            List of ModelInfo objects with metadata

        Raises:
            ExternalServiceError: If Ollama API is unreachable

        Example:
            >>> service = ModelService()
            >>> models = await service.get_available_models()
            >>> for model in models:
            ...     print(f"{model.name}: {model.size_gb}GB ({model.speed})")
        """
        logger.info("fetching_available_models", ollama_base_url=self.ollama_base_url)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Ollama models endpoint: GET /api/tags
                response = await client.get(f"{self.ollama_base_url}/api/tags")

                if response.status_code != 200:
                    logger.error(
                        "ollama_api_error",
                        status_code=response.status_code,
                        response_text=response.text,
                    )
                    raise ExternalServiceError(
                        "Ollama",
                        f"Failed to fetch models: HTTP {response.status_code}",
                    )

                data = response.json()
                raw_models = data.get("models", [])

                logger.info(
                    "ollama_models_fetched",
                    count=len(raw_models),
                )

                # Parse and categorize models
                models: list[ModelInfo] = []
                for raw_model in raw_models:
                    model_info = self._parse_ollama_model(raw_model)
                    if model_info:
                        models.append(model_info)

                logger.info(
                    "models_parsed",
                    total_models=len(models),
                    small_models=sum(1 for m in models if m.size_gb < SMALL_MODEL_THRESHOLD_GB),
                    medium_models=sum(
                        1
                        for m in models
                        if SMALL_MODEL_THRESHOLD_GB <= m.size_gb < MEDIUM_MODEL_THRESHOLD_GB
                    ),
                    large_models=sum(1 for m in models if m.size_gb >= LARGE_MODEL_THRESHOLD_GB),
                )

                return models

        except httpx.RequestError as e:
            logger.error(
                "ollama_connection_error",
                error=str(e),
                error_type=type(e).__name__,
                ollama_base_url=self.ollama_base_url,
            )
            raise ExternalServiceError(
                "Ollama",
                f"Failed to connect to Ollama API: {e}",
            ) from e

    def _parse_ollama_model(self, raw_model: dict[str, Any]) -> ModelInfo | None:
        """Parse raw Ollama model data into ModelInfo.

        Args:
            raw_model: Raw model dict from Ollama API

        Returns:
            ModelInfo object or None if parsing fails

        Example Ollama response:
            {
                "name": "nemotron3:latest",
                "model": "nemotron3:latest",
                "size": 5059903488,
                "digest": "sha256:...",
                "details": {
                    "format": "gguf",
                    "family": "nemotron",
                    "parameter_size": "8B",
                    ...
                }
            }
        """
        try:
            # Extract model ID (remove ":latest" suffix)
            model_name = raw_model.get("name", "")
            model_id = model_name.replace(":latest", "")

            # Extract size in GB
            size_bytes = raw_model.get("size", 0)
            size_gb = size_bytes / (1024**3)  # Convert bytes to GB

            # Extract parameter count from details
            details = raw_model.get("details", {})
            parameter_size = details.get("parameter_size", "")

            # Generate human-readable name
            human_name = self._generate_model_name(model_id, parameter_size)

            # Categorize model
            speed, quality, recommended_for = self._categorize_model(size_gb, model_id)

            logger.debug(
                "model_parsed",
                id=model_id,
                name=human_name,
                size_gb=round(size_gb, 2),
                speed=speed,
                quality=quality,
                recommended_for=recommended_for,
            )

            return ModelInfo(
                id=model_id,
                name=human_name,
                size_gb=size_gb,
                provider="ollama",
                recommended_for=recommended_for,
                speed=speed,
                quality=quality,
                available=True,
            )

        except Exception as e:
            logger.warning(
                "model_parse_error",
                error=str(e),
                raw_model=raw_model,
            )
            return None

    def _generate_model_name(self, model_id: str, parameter_size: str) -> str:
        """Generate human-readable model name.

        Args:
            model_id: Model ID (e.g., "nemotron3", "qwen3:32b")
            parameter_size: Parameter size (e.g., "8B", "32B")

        Returns:
            Human-readable name (e.g., "Nemotron3 8B", "Qwen3 32B")
        """
        # Capitalize first letter
        base_name = model_id.split(":")[0].capitalize()

        # Extract parameter size from model_id if not in details
        if not parameter_size and ":" in model_id:
            parameter_size = model_id.split(":")[1].upper()

        # Combine
        if parameter_size:
            return f"{base_name} {parameter_size}"
        else:
            return base_name

    def _categorize_model(self, size_gb: float, model_id: str) -> tuple[str, str, list[str]]:
        """Categorize model by size and capabilities.

        Args:
            size_gb: Model size in GB
            model_id: Model ID

        Returns:
            Tuple of (speed, quality, recommended_for)

        Size-based categorization:
        - < 5GB: Fast extraction, good quality
        - 5-15GB: Balanced, good quality
        - > 15GB: Slow but excellent quality (training)
        """
        recommended_for: list[str] = []

        if size_gb < SMALL_MODEL_THRESHOLD_GB:
            # Small models: Fast extraction
            speed = "fast"
            quality = "good"
            recommended_for = ["extraction", "classification"]

        elif size_gb < MEDIUM_MODEL_THRESHOLD_GB:
            # Medium models: Balanced
            speed = "medium"
            quality = "good"
            recommended_for = ["extraction", "classification"]

        else:
            # Large models: Training quality
            speed = "slow"
            quality = "excellent"
            recommended_for = ["training"]

        return speed, quality, recommended_for

    def get_model_recommendations(self, models: list[ModelInfo]) -> dict[str, str]:
        """Get recommended models for each use case.

        Args:
            models: List of available models

        Returns:
            Dictionary mapping use case to recommended model ID
            {
                "training": "qwen3:32b",
                "extraction": "nemotron3",
                "classification": "nemotron3"
            }

        Recommendation logic:
        - Training: Largest model (best quality)
        - Extraction: Smallest model with "good" quality (best speed)
        - Classification: Same as extraction
        """
        recommendations: dict[str, str] = {}

        if not models:
            logger.warning("no_models_available_for_recommendations")
            return recommendations

        # Training: Largest model (best quality)
        training_candidates = [m for m in models if "training" in m.recommended_for]
        if training_candidates:
            training_model = max(training_candidates, key=lambda m: m.size_gb)
            recommendations["training"] = training_model.id
        else:
            # Fallback: Largest available model
            largest_model = max(models, key=lambda m: m.size_gb)
            recommendations["training"] = largest_model.id

        # Extraction: Smallest model with good quality (best speed)
        extraction_candidates = [m for m in models if "extraction" in m.recommended_for]
        if extraction_candidates:
            extraction_model = min(extraction_candidates, key=lambda m: m.size_gb)
            recommendations["extraction"] = extraction_model.id
        else:
            # Fallback: Smallest available model
            smallest_model = min(models, key=lambda m: m.size_gb)
            recommendations["extraction"] = smallest_model.id

        # Classification: Same as extraction
        recommendations["classification"] = recommendations["extraction"]

        logger.info(
            "model_recommendations_generated",
            training=recommendations.get("training"),
            extraction=recommendations.get("extraction"),
            classification=recommendations.get("classification"),
        )

        return recommendations

    async def validate_model_available(self, model_id: str) -> bool:
        """Validate that a model is available in Ollama.

        Args:
            model_id: Model ID to validate

        Returns:
            True if model is available, False otherwise

        Example:
            >>> service = ModelService()
            >>> is_available = await service.validate_model_available("nemotron3")
            >>> if not is_available:
            ...     raise ValueError("Model not available")
        """
        logger.info("validating_model_availability", model_id=model_id)

        try:
            models = await self.get_available_models()
            model_ids = {m.id for m in models}

            # Check with and without ":latest" suffix
            # Model IDs in the set have :latest stripped by _parse_ollama_model
            model_id_base = model_id.replace(":latest", "")
            is_available = (
                model_id in model_ids
                or model_id_base in model_ids
                or f"{model_id}:latest" in model_ids
            )

            logger.info(
                "model_validation_result",
                model_id=model_id,
                model_id_base=model_id_base,
                is_available=is_available,
                available_models=list(model_ids),
            )

            return is_available

        except ExternalServiceError as e:
            logger.error(
                "model_validation_failed",
                model_id=model_id,
                error=str(e),
            )
            # Fail open: If Ollama is down, allow model selection
            # (will fail later at training/extraction time with better error message)
            return True


# Global singleton instance
_model_service: ModelService | None = None


def get_model_service() -> ModelService:
    """Get global model service instance (singleton).

    Returns:
        ModelService instance

    Example:
        >>> service = get_model_service()
        >>> models = await service.get_available_models()
    """
    global _model_service

    if _model_service is None:
        _model_service = ModelService()

    return _model_service
