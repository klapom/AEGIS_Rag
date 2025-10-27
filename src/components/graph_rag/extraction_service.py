"""Entity and relationship extraction service using Ollama LLM.

Sprint 5: Feature 5.3 - Entity & Relationship Extraction

This module provides extraction services for building knowledge graphs from text documents.
Uses Ollama's llama3.2:8b model with structured prompts for reliable JSON output.
"""

import json
import re
import uuid
from typing import Any

import structlog
from ollama import AsyncClient
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import settings
from src.core.models import GraphEntity, GraphRelationship
from src.prompts.extraction_prompts import (
    ENTITY_EXTRACTION_PROMPT,
    RELATIONSHIP_EXTRACTION_PROMPT,
)

logger = structlog.get_logger(__name__)

# Constants
MAX_ENTITIES_PER_DOC = 50
MAX_RELATIONSHIPS_PER_DOC = 100


class ExtractionService:
    """Entity and relationship extraction service using Ollama LLM.

    Provides methods for:
    - Entity extraction from text
    - Relationship extraction between entities
    - Batch processing of multiple documents
    - Integration with LightRAG and Neo4j
    """

    def __init__(
        self,
        llm_model: str | None = None,
        ollama_base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ):
        """Initialize extraction service.

        Args:
            llm_model: Ollama LLM model name (default: llama3.2:8b)
            ollama_base_url: Ollama server URL
            temperature: LLM temperature for extraction (default: 0.1 for consistency)
            max_tokens: Max tokens for LLM response
        """
        self.llm_model = llm_model or settings.lightrag_llm_model
        self.ollama_base_url = ollama_base_url or settings.ollama_base_url
        self.temperature = (
            temperature if temperature is not None else settings.lightrag_llm_temperature
        )
        self.max_tokens = max_tokens or settings.lightrag_llm_max_tokens

        # Initialize Ollama client
        self.client = AsyncClient(host=self.ollama_base_url)

        logger.info(
            "extraction_service_initialized",
            llm_model=self.llm_model,
            ollama_url=self.ollama_base_url,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    def _parse_json_response(self, response: str) -> list[dict[str, Any]]:
        """Parse JSON from LLM response with multiple fallback strategies.

        Sprint 13 Enhancement: Robust parsing for llama3.2:3b output variations.

        Handles various response formats:
        - Markdown code fences: ```json [...] ```
        - Plain JSON array: [...]
        - Text before/after JSON: "Here are the entities: [...] Hope this helps!"
        - Full response as JSON

        Args:
            response: Raw LLM response text

        Returns:
            Parsed JSON as list of dicts

        Raises:
            ValueError: If JSON parsing fails after all strategies
        """
        # 🔍 ENHANCED LOGGING: Log full response for debugging
        logger.info(
            "parsing_llm_response",
            response_length=len(response),
            response_preview=response[:500],
            response_full=response,  # Full response for debugging
        )

        json_str = None
        strategy_used = None

        # Strategy 1: Extract from markdown code fence (```json [...] ``` or ``` [...] ```)
        code_fence_match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", response, re.DOTALL)
        if code_fence_match:
            json_str = code_fence_match.group(1)
            strategy_used = "code_fence"
            logger.info("json_extraction_strategy", strategy=strategy_used)

        # Strategy 2: Extract JSON array pattern (current approach)
        if not json_str:
            json_match = re.search(r"\[.*\]", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                strategy_used = "regex_array"
                logger.info("json_extraction_strategy", strategy=strategy_used)

        # Strategy 3: Try entire response as-is
        if not json_str:
            json_str = response.strip()
            strategy_used = "full_response"
            logger.info("json_extraction_strategy", strategy=strategy_used)

        # Clean up common JSON issues
        json_str = json_str.strip()
        json_str = json_str.replace("'", '"')  # Single quotes to double quotes

        try:
            data = json.loads(json_str)

            # Validate structure: must be list of dicts with required fields
            if isinstance(data, list):
                valid_entities = []
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        # Check for required fields (name and type)
                        if "name" in item and "type" in item:
                            valid_entities.append(item)
                        else:
                            logger.warning(
                                "invalid_entity_structure",
                                index=i,
                                item=item,
                                missing_fields=[
                                    f for f in ["name", "type", "description"] if f not in item
                                ],
                            )
                    else:
                        logger.warning(
                            "invalid_entity_type",
                            index=i,
                            item_type=type(item).__name__,
                        )

                logger.info(
                    "json_parse_success",
                    strategy=strategy_used,
                    total_items=len(data),
                    valid_entities=len(valid_entities),
                    entity_names=[e.get("name", "UNKNOWN") for e in valid_entities],
                )

                return valid_entities

            elif isinstance(data, dict):
                # Single entity as dict (not array)
                logger.warning(
                    "json_not_array_single_entity",
                    data_type=type(data).__name__,
                )
                # Wrap in list if it has required fields
                if "name" in data and "type" in data:
                    logger.info("wrapping_single_entity_in_array")
                    return [data]
                else:
                    logger.error("single_entity_missing_fields", data=data)
                    return []

            else:
                logger.warning("json_unexpected_type", data_type=type(data).__name__)
                return []

        except json.JSONDecodeError as e:
            logger.error(
                "json_parse_failed",
                response_preview=response[:500],
                json_str_preview=json_str[:500] if json_str else "NONE",
                strategy=strategy_used,
                error=str(e),
                error_position=e.pos if hasattr(e, "pos") else None,
            )

            # Sprint 13 CHANGE: Raise error instead of silent failure
            # This triggers retry logic (3 attempts with exponential backoff)
            # If all retries fail, test will show clear error message
            raise ValueError(
                f"Failed to parse JSON from LLM response after trying strategy '{strategy_used}': {str(e)}"
            ) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def extract_entities(
        self,
        text: str,
        document_id: str | None = None,
    ) -> list[GraphEntity]:
        """Extract entities from text using LLM.

        Args:
            text: Document text to extract entities from
            document_id: Source document ID (optional)

        Returns:
            List of extracted entities as GraphEntity objects

        Raises:
            Exception: If extraction fails after retries
        """
        logger.info(
            "extracting_entities",
            text_length=len(text),
            document_id=document_id,
        )

        # Format prompt
        prompt = ENTITY_EXTRACTION_PROMPT.format(text=text)

        try:
            # Call Ollama LLM
            response = await self.client.generate(
                model=self.llm_model,
                prompt=prompt,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            )

            llm_response = response.get("response", "")

            # 🔍 ENHANCED LOGGING: Log LLM response before parsing
            logger.info(
                "llm_entity_extraction_response",
                model=self.llm_model,
                temperature=self.temperature,
                response_length=len(llm_response),
                response_preview=llm_response[:500],
                response_full=llm_response,  # Full response for debugging
            )

            # Parse JSON response
            entities_data = self._parse_json_response(llm_response)

            # Limit entities per document
            if len(entities_data) > MAX_ENTITIES_PER_DOC:
                logger.warning(
                    "max_entities_exceeded",
                    count=len(entities_data),
                    max_allowed=MAX_ENTITIES_PER_DOC,
                )
                entities_data = entities_data[:MAX_ENTITIES_PER_DOC]

            # Create GraphEntity objects
            entities = []
            for entity_dict in entities_data:
                try:
                    entity = GraphEntity(
                        id=str(uuid.uuid4()),  # Generate unique ID
                        name=entity_dict.get("name", ""),
                        type=entity_dict.get("type", "UNKNOWN"),
                        description=entity_dict.get("description", ""),
                        properties={},
                        source_document=document_id,
                        confidence=1.0,  # TODO: Add confidence scoring
                    )
                    entities.append(entity)
                except Exception as e:
                    logger.warning(
                        "entity_creation_failed",
                        entity_dict=entity_dict,
                        error=str(e),
                    )

            logger.info(
                "entities_extracted",
                count=len(entities),
                document_id=document_id,
            )

            return entities

        except Exception as e:
            logger.error(
                "entity_extraction_failed",
                document_id=document_id,
                error=str(e),
            )
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def extract_relationships(
        self,
        text: str,
        entities: list[GraphEntity],
        document_id: str | None = None,
    ) -> list[GraphRelationship]:
        """Extract relationships from text given entities.

        Args:
            text: Document text to extract relationships from
            entities: Extracted entities from the same text
            document_id: Source document ID (optional)

        Returns:
            List of extracted relationships as GraphRelationship objects

        Raises:
            Exception: If extraction fails after retries
        """
        logger.info(
            "extracting_relationships",
            text_length=len(text),
            entity_count=len(entities),
            document_id=document_id,
        )

        if not entities:
            logger.warning("no_entities_for_relationship_extraction")
            return []

        # Format entity list for prompt
        entity_list = "\n".join([f"- {e.name} ({e.type})" for e in entities])

        # Format prompt
        prompt = RELATIONSHIP_EXTRACTION_PROMPT.format(
            entities=entity_list,
            text=text,
        )

        try:
            # Call Ollama LLM
            response = await self.client.generate(
                model=self.llm_model,
                prompt=prompt,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            )

            llm_response = response.get("response", "")

            # Parse JSON response
            relationships_data = self._parse_json_response(llm_response)

            # Limit relationships per document
            if len(relationships_data) > MAX_RELATIONSHIPS_PER_DOC:
                logger.warning(
                    "max_relationships_exceeded",
                    count=len(relationships_data),
                    max_allowed=MAX_RELATIONSHIPS_PER_DOC,
                )
                relationships_data = relationships_data[:MAX_RELATIONSHIPS_PER_DOC]

            # Create GraphRelationship objects
            relationships = []
            for rel_dict in relationships_data:
                try:
                    relationship = GraphRelationship(
                        id=str(uuid.uuid4()),  # Generate unique ID
                        source=rel_dict.get("source", ""),
                        target=rel_dict.get("target", ""),
                        type=rel_dict.get("type", "RELATED_TO"),
                        description=rel_dict.get("description", ""),
                        properties={},
                        source_document=document_id,
                        confidence=1.0,  # TODO: Add confidence scoring
                    )
                    relationships.append(relationship)
                except Exception as e:
                    logger.warning(
                        "relationship_creation_failed",
                        rel_dict=rel_dict,
                        error=str(e),
                    )

            logger.info(
                "relationships_extracted",
                count=len(relationships),
                document_id=document_id,
            )

            return relationships

        except Exception as e:
            logger.error(
                "relationship_extraction_failed",
                document_id=document_id,
                error=str(e),
            )
            raise

    async def extract_and_store(
        self,
        text: str,
        document_id: str,
    ) -> dict[str, Any]:
        """Extract entities and relationships from a document.

        This is the main extraction method that combines entity and relationship extraction.

        Args:
            text: Document text
            document_id: Document ID

        Returns:
            Dictionary with extraction results:
            {
                "entities": list[GraphEntity],
                "relationships": list[GraphRelationship],
                "entity_count": int,
                "relationship_count": int
            }
        """
        logger.info("extracting_from_document", document_id=document_id)

        # Extract entities first
        entities = await self.extract_entities(text, document_id)

        # Extract relationships based on entities
        relationships = await self.extract_relationships(text, entities, document_id)

        result = {
            "entities": entities,
            "relationships": relationships,
            "entity_count": len(entities),
            "relationship_count": len(relationships),
        }

        logger.info(
            "extraction_complete",
            document_id=document_id,
            entities=len(entities),
            relationships=len(relationships),
        )

        return result

    async def extract_batch(
        self,
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Batch extraction from multiple documents.

        Args:
            documents: List of {"id": str, "text": str} dicts

        Returns:
            Dictionary with batch extraction results:
            {
                "total_documents": int,
                "success_count": int,
                "failed_count": int,
                "entities": list[GraphEntity],
                "relationships": list[GraphRelationship],
                "results": list[dict]
            }
        """
        logger.info("batch_extraction_started", document_count=len(documents))

        all_entities: list[GraphEntity] = []
        all_relationships: list[GraphRelationship] = []
        results = []

        for i, doc in enumerate(documents):
            try:
                extraction_result = await self.extract_and_store(
                    doc["text"],
                    doc["id"],
                )
                all_entities.extend(extraction_result["entities"])
                all_relationships.extend(extraction_result["relationships"])
                results.append(
                    {
                        "document_id": doc["id"],
                        "status": "success",
                        "entity_count": extraction_result["entity_count"],
                        "relationship_count": extraction_result["relationship_count"],
                    }
                )

                logger.info(
                    "batch_extraction_progress",
                    progress=f"{i+1}/{len(documents)}",
                )

            except Exception as e:
                logger.error(
                    "batch_extraction_document_failed",
                    document_id=doc["id"],
                    error=str(e),
                )
                results.append(
                    {
                        "document_id": doc["id"],
                        "status": "error",
                        "error": str(e),
                    }
                )

        success_count = sum(1 for r in results if r["status"] == "success")

        logger.info(
            "batch_extraction_complete",
            documents=len(documents),
            success=success_count,
            failed=len(documents) - success_count,
            total_entities=len(all_entities),
            total_relationships=len(all_relationships),
        )

        return {
            "total_documents": len(documents),
            "success_count": success_count,
            "failed_count": len(documents) - success_count,
            "entities": all_entities,
            "relationships": all_relationships,
            "results": results,
        }


# Global instance (singleton pattern)
_extraction_service: ExtractionService | None = None


def get_extraction_service() -> ExtractionService:
    """Get global extraction service instance (singleton).

    Returns:
        ExtractionService instance
    """
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = ExtractionService()
    return _extraction_service
