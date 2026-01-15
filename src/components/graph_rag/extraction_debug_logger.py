"""Comprehensive Extraction Debug Logger.

Sprint 92 Feature 92.17: Full-detail logging for extraction pipeline debugging.

This module provides detailed logging for every step of the extraction pipeline:
- Full LLM requests (prompts)
- Full LLM responses (raw JSON)
- Parsed entities with all fields
- Parsed relations with all fields
- Timing breakdown per stage
- JSON validation errors
- Token counts and costs

Usage:
    from src.components.graph_rag.extraction_debug_logger import ExtractionDebugLogger

    logger = ExtractionDebugLogger(document_id="doc_123", chunk_index=0)
    logger.log_llm_request("entity_extraction", prompt, model)
    logger.log_llm_response("entity_extraction", response, duration_ms)
    logger.log_entities(entities)
    logger.log_relations(relations)
    logger.log_summary()
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

# Enable/disable debug logging via environment variable
EXTRACTION_DEBUG_ENABLED = os.environ.get("AEGIS_EXTRACTION_DEBUG", "1") == "1"
EXTRACTION_DEBUG_DIR = Path(os.environ.get("AEGIS_EXTRACTION_DEBUG_DIR", "/tmp/extraction_debug"))

logger = structlog.get_logger(__name__)


@dataclass
class StageMetrics:
    """Metrics for a single extraction stage."""

    stage_name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0

    # LLM metrics
    prompt_tokens: int = 0
    response_tokens: int = 0
    model: str = ""

    # Results
    entities_count: int = 0
    relations_count: int = 0

    # Errors
    error: str | None = None
    json_valid: bool = True
    json_error: str | None = None


@dataclass
class ExtractionDebugSession:
    """Debug session for a single chunk extraction."""

    document_id: str
    chunk_index: int
    text_length: int = 0

    # Timing
    session_start: float = field(default_factory=time.time)
    session_end: float = 0.0

    # Stage metrics
    stages: dict[str, StageMetrics] = field(default_factory=dict)

    # Full data
    input_text: str = ""
    llm_requests: list[dict] = field(default_factory=list)
    llm_responses: list[dict] = field(default_factory=list)

    # Results
    entities: list[dict] = field(default_factory=list)
    relations: list[dict] = field(default_factory=list)

    # Validation
    validation_errors: list[str] = field(default_factory=list)


class ExtractionDebugLogger:
    """Comprehensive debug logger for extraction pipeline.

    Logs every detail of the extraction process to enable deep debugging:
    - Full prompts sent to LLM
    - Full responses from LLM
    - Parsed entities and relations
    - Timing breakdown
    - JSON validation issues
    """

    def __init__(
        self,
        document_id: str,
        chunk_index: int = 0,
        save_to_file: bool = True,
    ):
        """Initialize debug logger.

        Args:
            document_id: Document being processed
            chunk_index: Chunk index within document
            save_to_file: Whether to save debug output to file
        """
        self.enabled = EXTRACTION_DEBUG_ENABLED
        self.save_to_file = save_to_file and self.enabled

        self.session = ExtractionDebugSession(
            document_id=document_id,
            chunk_index=chunk_index,
        )

        if self.save_to_file:
            EXTRACTION_DEBUG_DIR.mkdir(parents=True, exist_ok=True)

        if self.enabled:
            logger.info(
                "extraction_debug_session_started",
                document_id=document_id,
                chunk_index=chunk_index,
                debug_enabled=True,
            )

    def log_input_text(self, text: str) -> None:
        """Log the input text being processed.

        Args:
            text: Full input text
        """
        if not self.enabled:
            return

        self.session.input_text = text
        self.session.text_length = len(text)

        logger.info(
            "EXTRACTION_DEBUG_INPUT",
            document_id=self.session.document_id,
            chunk_index=self.session.chunk_index,
            text_length=len(text),
            text_preview=text[:500] + "..." if len(text) > 500 else text,
        )

    def start_stage(self, stage_name: str, model: str = "") -> None:
        """Mark the start of an extraction stage.

        Args:
            stage_name: Name of the stage (e.g., "spacy_ner", "llm_entity_enrichment")
            model: LLM model being used (if applicable)
        """
        if not self.enabled:
            return

        self.session.stages[stage_name] = StageMetrics(
            stage_name=stage_name,
            start_time=time.time(),
            model=model,
        )

        logger.info(
            "EXTRACTION_DEBUG_STAGE_START",
            document_id=self.session.document_id,
            chunk_index=self.session.chunk_index,
            stage=stage_name,
            model=model,
        )

    def end_stage(
        self,
        stage_name: str,
        entities_count: int = 0,
        relations_count: int = 0,
        error: str | None = None,
    ) -> None:
        """Mark the end of an extraction stage.

        Args:
            stage_name: Name of the stage
            entities_count: Number of entities extracted in this stage
            relations_count: Number of relations extracted in this stage
            error: Error message if stage failed
        """
        if not self.enabled:
            return

        if stage_name not in self.session.stages:
            self.session.stages[stage_name] = StageMetrics(stage_name=stage_name)

        stage = self.session.stages[stage_name]
        stage.end_time = time.time()
        stage.duration_ms = (stage.end_time - stage.start_time) * 1000 if stage.start_time else 0
        stage.entities_count = entities_count
        stage.relations_count = relations_count
        stage.error = error

        logger.info(
            "EXTRACTION_DEBUG_STAGE_END",
            document_id=self.session.document_id,
            chunk_index=self.session.chunk_index,
            stage=stage_name,
            duration_ms=round(stage.duration_ms, 2),
            entities_count=entities_count,
            relations_count=relations_count,
            error=error,
        )

    def log_llm_request(
        self,
        stage_name: str,
        prompt: str,
        model: str,
        system_prompt: str | None = None,
    ) -> None:
        """Log full LLM request.

        Args:
            stage_name: Stage making the request
            prompt: Full user prompt
            model: LLM model
            system_prompt: System prompt if used
        """
        if not self.enabled:
            return

        request_data = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage_name,
            "model": model,
            "system_prompt": system_prompt,
            "user_prompt": prompt,
            "prompt_length": len(prompt),
        }

        self.session.llm_requests.append(request_data)

        # Update stage metrics
        if stage_name in self.session.stages:
            self.session.stages[stage_name].prompt_tokens = len(prompt.split())  # Rough estimate

        logger.info(
            "EXTRACTION_DEBUG_LLM_REQUEST",
            document_id=self.session.document_id,
            chunk_index=self.session.chunk_index,
            stage=stage_name,
            model=model,
            prompt_length=len(prompt),
            system_prompt_length=len(system_prompt) if system_prompt else 0,
            # Log FULL prompt for debugging
            full_prompt=prompt,
        )

    def log_llm_response(
        self,
        stage_name: str,
        response: str,
        duration_ms: float,
        is_valid_json: bool = True,
        json_error: str | None = None,
    ) -> None:
        """Log full LLM response.

        Args:
            stage_name: Stage that received the response
            response: Full raw response from LLM
            duration_ms: Time taken for LLM call
            is_valid_json: Whether response is valid JSON
            json_error: JSON parsing error if any
        """
        if not self.enabled:
            return

        response_data = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage_name,
            "response": response,
            "response_length": len(response),
            "duration_ms": duration_ms,
            "is_valid_json": is_valid_json,
            "json_error": json_error,
        }

        self.session.llm_responses.append(response_data)

        # Update stage metrics
        if stage_name in self.session.stages:
            stage = self.session.stages[stage_name]
            stage.response_tokens = len(response.split())  # Rough estimate
            stage.json_valid = is_valid_json
            stage.json_error = json_error

        # Add validation error if JSON invalid
        if not is_valid_json and json_error:
            self.session.validation_errors.append(f"{stage_name}: {json_error}")

        logger.info(
            "EXTRACTION_DEBUG_LLM_RESPONSE",
            document_id=self.session.document_id,
            chunk_index=self.session.chunk_index,
            stage=stage_name,
            response_length=len(response),
            duration_ms=round(duration_ms, 2),
            is_valid_json=is_valid_json,
            json_error=json_error,
            # Log FULL response for debugging
            full_response=response,
        )

    def log_entities(self, entities: list[Any], source: str = "combined") -> None:
        """Log all extracted entities with full details.

        Args:
            entities: List of extracted entities (dict or GraphEntity)
            source: Source of entities (e.g., "spacy", "llm", "combined")
        """
        if not self.enabled:
            return

        entity_dicts = []
        for entity in entities:
            if hasattr(entity, "__dict__"):
                # Convert Pydantic model or dataclass to dict
                entity_dict = {
                    "name": getattr(entity, "name", ""),
                    "type": getattr(entity, "type", ""),
                    "description": getattr(entity, "description", ""),
                    "source_document": getattr(entity, "source_document", ""),
                    "confidence": getattr(entity, "confidence", 1.0),
                }
            else:
                entity_dict = dict(entity)

            entity_dicts.append(entity_dict)

        self.session.entities.extend(entity_dicts)

        logger.info(
            "EXTRACTION_DEBUG_ENTITIES",
            document_id=self.session.document_id,
            chunk_index=self.session.chunk_index,
            source=source,
            entity_count=len(entities),
            # Log ALL entities with FULL details
            entities=entity_dicts,
        )

        # Log each entity individually for easier grep
        for i, entity in enumerate(entity_dicts):
            logger.info(
                "EXTRACTION_DEBUG_ENTITY_DETAIL",
                document_id=self.session.document_id,
                chunk_index=self.session.chunk_index,
                entity_index=i,
                entity_name=entity.get("name", ""),
                entity_type=entity.get("type", ""),
                entity_name_length=len(entity.get("name", "")),
                entity_description=entity.get("description", "")[:200] if entity.get("description") else "",
            )

    def log_relations(self, relations: list[Any], source: str = "combined") -> None:
        """Log all extracted relations with full details.

        Args:
            relations: List of extracted relations
            source: Source of relations
        """
        if not self.enabled:
            return

        relation_dicts = []
        for relation in relations:
            if hasattr(relation, "__dict__"):
                relation_dict = {
                    "source": getattr(relation, "source", ""),
                    "target": getattr(relation, "target", ""),
                    "type": getattr(relation, "type", ""),
                    "description": getattr(relation, "description", ""),
                    "confidence": getattr(relation, "confidence", 1.0),
                }
            else:
                relation_dict = dict(relation)

            relation_dicts.append(relation_dict)

        self.session.relations.extend(relation_dicts)

        logger.info(
            "EXTRACTION_DEBUG_RELATIONS",
            document_id=self.session.document_id,
            chunk_index=self.session.chunk_index,
            source=source,
            relation_count=len(relations),
            # Log ALL relations with FULL details
            relations=relation_dicts,
        )

        # Log each relation individually
        for i, relation in enumerate(relation_dicts):
            logger.info(
                "EXTRACTION_DEBUG_RELATION_DETAIL",
                document_id=self.session.document_id,
                chunk_index=self.session.chunk_index,
                relation_index=i,
                relation_source=relation.get("source", ""),
                relation_target=relation.get("target", ""),
                relation_type=relation.get("type", ""),
                relation_description=relation.get("description", "")[:200] if relation.get("description") else "",
            )

    def log_validation_error(self, error: str, context: str = "") -> None:
        """Log a validation error.

        Args:
            error: Error message
            context: Additional context
        """
        if not self.enabled:
            return

        self.session.validation_errors.append(f"{context}: {error}" if context else error)

        logger.error(
            "EXTRACTION_DEBUG_VALIDATION_ERROR",
            document_id=self.session.document_id,
            chunk_index=self.session.chunk_index,
            error=error,
            context=context,
        )

    def log_summary(self) -> dict[str, Any]:
        """Log extraction summary and save to file.

        Returns:
            Summary dict with all metrics
        """
        if not self.enabled:
            return {}

        self.session.session_end = time.time()
        total_duration_ms = (self.session.session_end - self.session.session_start) * 1000

        # Build summary
        summary = {
            "document_id": self.session.document_id,
            "chunk_index": self.session.chunk_index,
            "text_length": self.session.text_length,
            "total_duration_ms": round(total_duration_ms, 2),
            "total_entities": len(self.session.entities),
            "total_relations": len(self.session.relations),
            "validation_errors": len(self.session.validation_errors),
            "stages": {},
        }

        for stage_name, metrics in self.session.stages.items():
            summary["stages"][stage_name] = {
                "duration_ms": round(metrics.duration_ms, 2),
                "entities_count": metrics.entities_count,
                "relations_count": metrics.relations_count,
                "json_valid": metrics.json_valid,
                "error": metrics.error,
            }

        logger.info(
            "EXTRACTION_DEBUG_SUMMARY",
            document_id=self.session.document_id,
            chunk_index=self.session.chunk_index,
            total_duration_ms=round(total_duration_ms, 2),
            total_entities=len(self.session.entities),
            total_relations=len(self.session.relations),
            validation_errors=self.session.validation_errors,
            stage_durations={k: round(v.duration_ms, 2) for k, v in self.session.stages.items()},
        )

        # Save full debug session to file
        if self.save_to_file:
            self._save_to_file(summary)

        return summary

    def _save_to_file(self, summary: dict[str, Any]) -> None:
        """Save full debug session to JSON file.

        Args:
            summary: Summary dict
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"extraction_{self.session.document_id}_{self.session.chunk_index}_{timestamp}.json"
            filepath = EXTRACTION_DEBUG_DIR / filename

            full_data = {
                "summary": summary,
                "input_text": self.session.input_text[:10000],  # Limit to prevent huge files
                "llm_requests": self.session.llm_requests,
                "llm_responses": self.session.llm_responses,
                "entities": self.session.entities,
                "relations": self.session.relations,
                "validation_errors": self.session.validation_errors,
            }

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(full_data, f, indent=2, ensure_ascii=False)

            logger.info(
                "EXTRACTION_DEBUG_FILE_SAVED",
                filepath=str(filepath),
                file_size_kb=round(filepath.stat().st_size / 1024, 2),
            )

        except Exception as e:
            logger.error("extraction_debug_file_save_failed", error=str(e))


# Convenience function
def get_debug_logger(document_id: str, chunk_index: int = 0) -> ExtractionDebugLogger:
    """Get a debug logger instance.

    Args:
        document_id: Document ID
        chunk_index: Chunk index

    Returns:
        ExtractionDebugLogger instance
    """
    return ExtractionDebugLogger(document_id, chunk_index)
