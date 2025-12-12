"""Domain Auto-Discovery Service using LLM analysis.

Sprint 45 - Feature 45.9: Domain Auto-Discovery (5 SP)

This module provides LLM-based domain recognition from sample documents.
It analyzes document content to suggest domain names, descriptions, and
expected entity/relation types.

Key Features:
- LLM-based domain suggestion from 3-10 sample documents
- Automatic domain name normalization (lowercase, underscores)
- Entity and relation type prediction
- Confidence scoring with reasoning
- JSON response parsing with validation

Architecture:
    Sample Docs → LLM Analysis → DomainSuggestion
    ├── Name generation (normalized)
    ├── Description generation (detailed)
    ├── Entity types prediction
    ├── Relation types prediction
    └── Confidence scoring

Usage:
    >>> from src.components.domain_training import get_domain_discovery_service
    >>> service = get_domain_discovery_service()
    >>> suggestion = await service.discover_domain(sample_texts)
    >>> print(f"Suggested domain: {suggestion.name}")
    >>> print(f"Confidence: {suggestion.confidence}")

Performance:
- LLM call: ~5-15s for qwen3:32b
- Response parsing: <10ms
- Total: <20s for typical inputs
"""

import json
import re

import httpx
import structlog
from pydantic import BaseModel, Field

from src.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class DomainSuggestion(BaseModel):
    """Suggested domain based on document analysis.

    Represents an LLM-generated domain suggestion with normalized name,
    detailed description, and predicted entity/relation types.

    Attributes:
        name: Domain name (lowercase, underscores, max 30 chars)
        title: Human-readable title
        description: Detailed description for semantic matching (100-300 words)
        confidence: Confidence score (0-1)
        reasoning: LLM's reasoning for the suggestion
        entity_types: Expected entity types (e.g., "Person", "Organization")
        relation_types: Expected relation types (e.g., "works_for", "mentions")
    """

    name: str = Field(..., min_length=2, max_length=30, pattern="^[a-z][a-z0-9_]*$")
    title: str = Field(..., min_length=2, max_length=100)
    description: str = Field(..., min_length=10, max_length=1000)
    confidence: float = Field(..., ge=0, le=1)
    reasoning: str = Field(default="", max_length=500)
    entity_types: list[str] = Field(default_factory=list)
    relation_types: list[str] = Field(default_factory=list)


DISCOVERY_PROMPT = """Analyze the following sample documents and suggest a domain name and description.

Sample Documents:
{samples}

Based on these documents, provide:
1. A short domain name (lowercase, underscores, max 30 chars) - e.g., "tech_docs", "legal_contracts", "medical_records"
2. A human-readable title
3. A detailed description (100-300 words) that captures what makes this domain unique
4. Your confidence level (0-1)
5. Brief reasoning for your suggestion
6. List of expected entity types (e.g., "Person", "Organization", "Technical Term")
7. List of expected relation types (e.g., "works_for", "mentions", "implements")

Respond in JSON format:
{{
    "name": "domain_name",
    "title": "Human Readable Title",
    "description": "Detailed description...",
    "confidence": 0.85,
    "reasoning": "These documents share...",
    "entity_types": ["Person", "Organization", ...],
    "relation_types": ["works_for", "mentions", ...]
}}
"""


class DomainDiscoveryService:
    """Discovers domain characteristics from sample documents using LLM.

    Uses Ollama-based LLM to analyze sample documents and suggest appropriate
    domain configurations including name, description, and expected types.

    Attributes:
        llm_model: Ollama model name (default: qwen3:32b)
        ollama_base_url: Ollama API endpoint
    """

    def __init__(
        self,
        llm_model: str = "qwen3:32b",
        ollama_base_url: str | None = None,
    ):
        """Initialize domain discovery service.

        Args:
            llm_model: Ollama model name for analysis
            ollama_base_url: Ollama API endpoint (default from settings)
        """
        self.llm_model = llm_model
        self.ollama_base_url = (
            ollama_base_url or settings.ollama_base_url or "http://localhost:11434"
        )

    async def discover_domain(
        self,
        sample_texts: list[str],
        max_sample_length: int = 2000,
    ) -> DomainSuggestion:
        """Analyze samples and suggest domain configuration.

        Analyzes 3-10 representative documents to suggest a domain name,
        description, and expected entity/relation types.

        Args:
            sample_texts: 3-10 representative document texts
            max_sample_length: Max chars per sample to include in prompt

        Returns:
            DomainSuggestion with name, description, and expected types

        Raises:
            ValueError: If less than 3 samples provided
            httpx.HTTPError: If Ollama API call fails
            json.JSONDecodeError: If LLM response is not valid JSON
        """
        if len(sample_texts) < 3:
            logger.error("discover_domain_insufficient_samples", count=len(sample_texts))
            raise ValueError("At least 3 sample documents required")

        # Limit to 10 samples for reasonable prompt size
        if len(sample_texts) > 10:
            logger.info(
                "discover_domain_truncating_samples",
                original_count=len(sample_texts),
                truncated_count=10,
            )
            sample_texts = sample_texts[:10]

        # Truncate samples to max length
        truncated = [
            text[:max_sample_length] + "..." if len(text) > max_sample_length else text
            for text in sample_texts
        ]

        # Format samples for prompt
        samples_text = "\n\n---\n\n".join(
            [f"Document {i+1}:\n{text}" for i, text in enumerate(truncated)]
        )

        prompt = DISCOVERY_PROMPT.format(samples=samples_text)

        logger.info(
            "discover_domain_calling_llm",
            model=self.llm_model,
            sample_count=len(truncated),
            prompt_length=len(prompt),
        )

        # Call LLM
        response_text = await self._call_llm(prompt)

        logger.info(
            "discover_domain_llm_response_received",
            response_length=len(response_text),
        )

        # Parse response
        suggestion = self._parse_response(response_text)

        logger.info(
            "discover_domain_suggestion_created",
            name=suggestion.name,
            confidence=suggestion.confidence,
            entity_types_count=len(suggestion.entity_types),
            relation_types_count=len(suggestion.relation_types),
        )

        return suggestion

    async def _call_llm(self, prompt: str) -> str:
        """Call Ollama LLM for domain analysis.

        Args:
            prompt: Formatted prompt with sample documents

        Returns:
            LLM response text

        Raises:
            httpx.HTTPError: If API call fails
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={
                        "model": self.llm_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.3},
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["response"]

            except httpx.ConnectError as e:
                logger.error(
                    "discover_domain_ollama_connection_error",
                    url=self.ollama_base_url,
                    error=str(e),
                )
                raise

            except httpx.HTTPStatusError as e:
                logger.error(
                    "discover_domain_ollama_http_error",
                    status_code=e.response.status_code,
                    error=str(e),
                )
                raise

    def _parse_response(self, response: str) -> DomainSuggestion:
        """Parse LLM response to DomainSuggestion.

        Extracts JSON from response text, normalizes the domain name,
        and validates all fields.

        Args:
            response: LLM response text containing JSON

        Returns:
            Validated DomainSuggestion

        Raises:
            ValueError: If JSON cannot be extracted or parsed
            json.JSONDecodeError: If JSON is malformed
        """
        # Extract JSON from response (may have markdown fences or extra text)
        json_match = re.search(r"\{[\s\S]*\}", response)
        if not json_match:
            logger.error(
                "discover_domain_no_json_found",
                response_preview=response[:200],
            )
            raise ValueError("Could not parse LLM response as JSON")

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            logger.error(
                "discover_domain_json_decode_error",
                error=str(e),
                json_text=json_match.group()[:200],
            )
            raise

        # Normalize name: lowercase, underscores only, max 30 chars
        raw_name = data.get("name", "unknown_domain")
        name = raw_name.lower().replace(" ", "_").replace("-", "_")
        name = re.sub(r"[^a-z0-9_]", "", name)[:30]

        # Ensure name starts with letter
        if not name or not name[0].isalpha():
            name = "domain_" + name

        logger.info(
            "discover_domain_name_normalized",
            raw_name=raw_name,
            normalized_name=name,
        )

        # Build suggestion with defaults for missing fields
        return DomainSuggestion(
            name=name,
            title=data.get("title", name.replace("_", " ").title()),
            description=data.get("description", "Custom domain"),
            confidence=float(data.get("confidence", 0.7)),
            reasoning=data.get("reasoning", ""),
            entity_types=data.get("entity_types", []),
            relation_types=data.get("relation_types", []),
        )


# Singleton instance
_discovery_service: DomainDiscoveryService | None = None


def get_domain_discovery_service() -> DomainDiscoveryService:
    """Get or create singleton DomainDiscoveryService instance.

    Returns:
        Global DomainDiscoveryService instance
    """
    global _discovery_service
    if _discovery_service is None:
        _discovery_service = DomainDiscoveryService()
    return _discovery_service
