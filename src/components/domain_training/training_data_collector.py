"""DSPy Training Data Collector for Domain-Specific Optimization.

Sprint 85 Feature 85.7: DSPy Training Data Collection

This module collects high-quality training data during extraction for future
DSPy MIPROv2 optimization. Samples are collected when quality thresholds are met.

DSPy Training Data Format (from dspy_optimizer.py):
- Entity: {"text": str, "entities": list[str]}
- Relation: {"text": str, "entities": list[str], "relations": list[dict]}

Collection Strategy:
1. During extraction, evaluate quality metrics
2. If thresholds met, save sample to collector
3. Export to JSONL for DSPy training
4. Stratify by doc_type and language
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from src.core.models import GraphEntity, GraphRelationship

logger = structlog.get_logger(__name__)


@dataclass
class DSPyTrainingSample:
    """Training sample for DSPy optimization.

    Attributes:
        text: Source text for extraction
        entities: List of entity names (strings, not full objects)
        relations: List of relation dicts [{"subject": str, "predicate": str, "object": str}]
        doc_type: Document type (pdf_text, docx, table, etc.)
        language: Language code (de, en, fr, es)
        extraction_source: How this sample was validated ("validated_llm", "manual", "high_confidence")
        entity_confidence: Average confidence of extracted entities
        relation_confidence: Average confidence of extracted relations
        evidence_coverage: Percentage of relations with evidence spans
        document_id: Source document ID
        chunk_id: Source chunk ID
        domain: Domain name (if available)
        timestamp: When the sample was collected
    """

    # Core DSPy fields (required by dspy_optimizer.py)
    text: str
    entities: list[str]
    relations: list[dict[str, str]]

    # Metadata for stratification
    doc_type: str = "unknown"
    language: str = "en"
    extraction_source: str = "validated_llm"

    # Quality indicators
    entity_confidence: float = 0.0
    relation_confidence: float = 0.0
    evidence_coverage: float = 0.0

    # Provenance
    document_id: str = ""
    chunk_id: str = ""
    domain: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dspy_entity_format(self) -> dict[str, Any]:
        """Convert to DSPy entity extraction training format."""
        return {
            "text": self.text,
            "entities": self.entities,
        }

    def to_dspy_relation_format(self) -> dict[str, Any]:
        """Convert to DSPy relation extraction training format."""
        return {
            "text": self.text,
            "entities": self.entities,
            "relations": self.relations,
        }

    def to_full_dict(self) -> dict[str, Any]:
        """Convert to full dictionary including metadata."""
        result = asdict(self)
        result["timestamp"] = self.timestamp.isoformat()
        return result


class TrainingDataCollector:
    """Collect training data during extraction for DSPy optimization.

    Collects high-quality samples that meet confidence and evidence thresholds.
    Supports stratification by document type and language.

    Attributes:
        min_entity_confidence: Minimum average entity confidence
        min_relation_confidence: Minimum average relation confidence
        min_evidence_coverage: Minimum percentage of relations with evidence
        min_entities: Minimum entities per sample
        min_relations: Minimum relations per sample
    """

    def __init__(
        self,
        min_entity_confidence: float = 0.7,
        min_relation_confidence: float = 0.6,
        min_evidence_coverage: float = 0.5,
        min_entities: int = 2,
        min_relations: int = 1,
    ) -> None:
        """Initialize training data collector.

        Args:
            min_entity_confidence: Minimum average entity confidence (0-1)
            min_relation_confidence: Minimum average relation confidence (0-1)
            min_evidence_coverage: Minimum percentage of relations with evidence (0-1)
            min_entities: Minimum entities per sample
            min_relations: Minimum relations per sample
        """
        self.min_entity_confidence = min_entity_confidence
        self.min_relation_confidence = min_relation_confidence
        self.min_evidence_coverage = min_evidence_coverage
        self.min_entities = min_entities
        self.min_relations = min_relations

        # Storage
        self.samples: list[DSPyTrainingSample] = []

        # Statistics
        self.total_candidates = 0
        self.rejected_low_confidence = 0
        self.rejected_low_evidence = 0
        self.rejected_too_few_items = 0

        logger.info(
            "training_data_collector_initialized",
            min_entity_confidence=min_entity_confidence,
            min_relation_confidence=min_relation_confidence,
            min_evidence_coverage=min_evidence_coverage,
            min_entities=min_entities,
            min_relations=min_relations,
        )

    def _calculate_metrics(
        self,
        entities: list[GraphEntity | dict[str, Any]],
        relations: list[GraphRelationship | dict[str, Any]],
    ) -> tuple[float, float, float]:
        """Calculate quality metrics for entities and relations.

        Returns:
            Tuple of (avg_entity_conf, avg_relation_conf, evidence_coverage)
        """
        # Entity confidence
        entity_confs = []
        for e in entities:
            conf = e.confidence if hasattr(e, "confidence") else e.get("confidence", 1.0)
            entity_confs.append(conf)
        avg_entity_conf = sum(entity_confs) / len(entity_confs) if entity_confs else 0.0

        # Relation confidence
        relation_confs = []
        evidence_count = 0
        for r in relations:
            conf = r.confidence if hasattr(r, "confidence") else r.get("confidence", 1.0)
            relation_confs.append(conf)

            # Check evidence
            evidence = (
                getattr(r, "evidence_span", None)
                if hasattr(r, "evidence_span")
                else r.get("evidence_span")
            )
            if evidence:
                evidence_count += 1

        avg_relation_conf = sum(relation_confs) / len(relation_confs) if relation_confs else 0.0
        evidence_coverage = evidence_count / len(relations) if relations else 0.0

        return avg_entity_conf, avg_relation_conf, evidence_coverage

    def collect(
        self,
        text: str,
        entities: list[GraphEntity | dict[str, Any]],
        relations: list[GraphRelationship | dict[str, Any]],
        metadata: dict[str, Any],
    ) -> DSPyTrainingSample | None:
        """Collect sample if quality thresholds are met.

        Args:
            text: Source text
            entities: Extracted entities
            relations: Extracted relations
            metadata: Extraction metadata (doc_type, language, document_id, chunk_id, domain)

        Returns:
            DSPyTrainingSample if quality thresholds met, None otherwise
        """
        self.total_candidates += 1

        # Check minimum counts
        if len(entities) < self.min_entities:
            self.rejected_too_few_items += 1
            logger.debug(
                "training_sample_rejected_too_few_entities",
                entities=len(entities),
                min_required=self.min_entities,
            )
            return None

        if len(relations) < self.min_relations:
            self.rejected_too_few_items += 1
            logger.debug(
                "training_sample_rejected_too_few_relations",
                relations=len(relations),
                min_required=self.min_relations,
            )
            return None

        # Calculate quality metrics
        avg_entity_conf, avg_relation_conf, evidence_coverage = self._calculate_metrics(
            entities, relations
        )

        # Check confidence thresholds
        if avg_entity_conf < self.min_entity_confidence:
            self.rejected_low_confidence += 1
            logger.debug(
                "training_sample_rejected_low_entity_confidence",
                confidence=avg_entity_conf,
                min_required=self.min_entity_confidence,
            )
            return None

        if avg_relation_conf < self.min_relation_confidence:
            self.rejected_low_confidence += 1
            logger.debug(
                "training_sample_rejected_low_relation_confidence",
                confidence=avg_relation_conf,
                min_required=self.min_relation_confidence,
            )
            return None

        # Check evidence coverage
        if evidence_coverage < self.min_evidence_coverage:
            self.rejected_low_evidence += 1
            logger.debug(
                "training_sample_rejected_low_evidence",
                coverage=evidence_coverage,
                min_required=self.min_evidence_coverage,
            )
            return None

        # Convert to DSPy format
        entity_names = []
        for e in entities:
            name = e.name if hasattr(e, "name") else e.get("name", "")
            if name:
                entity_names.append(name)

        relation_dicts = []
        for r in relations:
            source = r.source if hasattr(r, "source") else r.get("source", "")
            target = r.target if hasattr(r, "target") else r.get("target", "")
            rel_type = r.type if hasattr(r, "type") else r.get("type", "RELATES_TO")
            if source and target:
                relation_dicts.append({
                    "subject": source,
                    "predicate": rel_type,
                    "object": target,
                })

        # Create sample
        sample = DSPyTrainingSample(
            text=text,
            entities=entity_names,
            relations=relation_dicts,
            doc_type=metadata.get("doc_type", "unknown"),
            language=metadata.get("language", "en"),
            extraction_source="validated_llm",
            entity_confidence=avg_entity_conf,
            relation_confidence=avg_relation_conf,
            evidence_coverage=evidence_coverage,
            document_id=metadata.get("document_id", ""),
            chunk_id=metadata.get("chunk_id", ""),
            domain=metadata.get("domain"),
            timestamp=datetime.utcnow(),
        )

        self.samples.append(sample)

        logger.info(
            "training_sample_collected",
            entities=len(entity_names),
            relations=len(relation_dicts),
            entity_confidence=round(avg_entity_conf, 2),
            relation_confidence=round(avg_relation_conf, 2),
            evidence_coverage=round(evidence_coverage, 2),
            doc_type=sample.doc_type,
            language=sample.language,
            total_samples=len(self.samples),
        )

        return sample

    def get_statistics(self) -> dict[str, Any]:
        """Get collection statistics."""
        return {
            "total_samples": len(self.samples),
            "total_candidates": self.total_candidates,
            "rejected_low_confidence": self.rejected_low_confidence,
            "rejected_low_evidence": self.rejected_low_evidence,
            "rejected_too_few_items": self.rejected_too_few_items,
            "acceptance_rate": len(self.samples) / self.total_candidates
            if self.total_candidates > 0
            else 0.0,
        }

    def get_stratification(self) -> dict[str, dict[str, int]]:
        """Get stratification breakdown by doc_type and language."""
        by_doc_type: dict[str, int] = {}
        by_language: dict[str, int] = {}

        for sample in self.samples:
            by_doc_type[sample.doc_type] = by_doc_type.get(sample.doc_type, 0) + 1
            by_language[sample.language] = by_language.get(sample.language, 0) + 1

        return {
            "by_doc_type": by_doc_type,
            "by_language": by_language,
        }

    def export_to_jsonl(
        self,
        path: Path | str,
        format: str = "both",
    ) -> dict[str, int]:
        """Export samples to JSONL for DSPy training.

        Args:
            path: Output file path
            format: "entity" (entity extraction only), "relation" (relation extraction only), "both"

        Returns:
            Dictionary with export counts
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        entity_count = 0
        relation_count = 0

        with open(path, "w") as f:
            for sample in self.samples:
                if format in ("entity", "both"):
                    f.write(json.dumps(sample.to_dspy_entity_format()) + "\n")
                    entity_count += 1

                if format in ("relation", "both"):
                    f.write(json.dumps(sample.to_dspy_relation_format()) + "\n")
                    relation_count += 1

        logger.info(
            "training_data_exported",
            path=str(path),
            format=format,
            entity_samples=entity_count,
            relation_samples=relation_count,
        )

        return {
            "entity_samples": entity_count,
            "relation_samples": relation_count,
            "file_path": str(path),
        }

    def export_full_samples(self, path: Path | str) -> int:
        """Export full samples with metadata to JSONL.

        Args:
            path: Output file path

        Returns:
            Number of samples exported
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            for sample in self.samples:
                f.write(json.dumps(sample.to_full_dict()) + "\n")

        logger.info(
            "full_training_data_exported",
            path=str(path),
            samples=len(self.samples),
        )

        return len(self.samples)

    def clear(self) -> None:
        """Clear all collected samples and reset statistics."""
        self.samples.clear()
        self.total_candidates = 0
        self.rejected_low_confidence = 0
        self.rejected_low_evidence = 0
        self.rejected_too_few_items = 0
        logger.info("training_data_collector_cleared")


# Global instance (singleton pattern)
_training_data_collector: TrainingDataCollector | None = None


def get_training_data_collector(
    min_entity_confidence: float = 0.7,
    min_relation_confidence: float = 0.6,
    min_evidence_coverage: float = 0.5,
) -> TrainingDataCollector:
    """Get global training data collector instance (singleton).

    Args:
        min_entity_confidence: Minimum average entity confidence
        min_relation_confidence: Minimum average relation confidence
        min_evidence_coverage: Minimum percentage of relations with evidence

    Returns:
        TrainingDataCollector instance
    """
    global _training_data_collector
    if _training_data_collector is None:
        _training_data_collector = TrainingDataCollector(
            min_entity_confidence=min_entity_confidence,
            min_relation_confidence=min_relation_confidence,
            min_evidence_coverage=min_evidence_coverage,
        )
    return _training_data_collector
