"""
LogQA dataset adapter.

LogQA is a question answering dataset based on system logs
and support tickets, focusing on IT operations questions.

Dataset: https://huggingface.co/datasets/tianyao-chen/logqa

Sprint 82: Phase 1 - Text-Only Benchmark
"""

from typing import Dict, Any, Optional, List
import logging

from .base import DatasetAdapter
from ..models import NormalizedSample

logger = logging.getLogger(__name__)


class LogQAAdapter(DatasetAdapter):
    """
    Adapter for LogQA dataset.

    LogQA Structure:
    - question: The question about logs/systems
    - answer: Ground truth answer
    - context: Log entries or documentation context
    - log_type: Type of log (system, application, security, etc.)

    Normalization:
    - Preserves log structure in context
    - Question type inferred from log-specific keywords
    - Difficulty based on log complexity
    """

    # Log-specific question type keywords
    LOG_QUESTION_KEYWORDS = {
        "lookup": [
            "what error", "which error", "what exception", "error code",
            "timestamp", "when did", "log entry", "message",
        ],
        "howto": [
            "how to fix", "how to resolve", "troubleshoot", "debug",
            "solution for", "steps to", "remedy", "workaround",
        ],
        "entity": [
            "which service", "what component", "which server", "what process",
            "which user", "what application", "source of", "origin of",
        ],
        "multihop": [
            "relationship between", "caused by", "led to", "correlated",
            "sequence of", "before", "after", "following",
        ],
        "policy": [
            "should", "best practice", "recommended", "standard",
            "compliance", "security requirement", "policy",
        ],
    }

    def get_doc_type(self) -> str:
        return "log_ticket"

    def get_source_name(self) -> str:
        return "logqa"

    def get_fields_mapping(self) -> Dict[str, str]:
        return {
            "question": "question",
            "ground_truth": "answer",
            "contexts": "context",
            "log_type": "log_type",
        }

    def adapt(self, record: Dict[str, Any], record_idx: int = 0) -> Optional[NormalizedSample]:
        """
        Transform LogQA record to NormalizedSample.

        Args:
            record: Raw LogQA record
            record_idx: Sequential index

        Returns:
            NormalizedSample or None if invalid
        """
        try:
            # Extract fields
            question = record.get("question", "")
            answer = self._extract_answer(record)
            contexts = self._extract_contexts(record)

            # Validate
            is_valid, drop_reason = self.validate_sample(question, answer, contexts)
            if not is_valid:
                self.record_drop(drop_reason)
                return None

            # Classify question type using log-specific keywords
            question_type = self._classify_log_question(question)

            # Assign difficulty based on log complexity
            context_length = sum(len(c) for c in contexts)
            log_type = record.get("log_type", "")
            difficulty = self._assign_log_difficulty(question_type, context_length, log_type)

            # Generate ID
            original_id = record.get("id", str(record_idx))
            sample_id = self.generate_id("logqa", original_id, record_idx)

            # Build metadata
            metadata = {
                "original_id": original_id,
                "log_type": log_type,
                "sample_method": "stratified",
                "phase": 1,
            }

            # Preserve additional log-specific fields
            for field in ["system", "component", "severity", "category"]:
                if field in record and record[field]:
                    metadata[f"logqa_{field}"] = record[field]

            return NormalizedSample(
                id=sample_id,
                question=question,
                ground_truth=answer,
                contexts=contexts,
                doc_type=self.get_doc_type(),
                question_type=question_type,
                difficulty=difficulty,
                answerable=True,
                source_dataset=self.get_source_name(),
                metadata=metadata,
            )

        except Exception as e:
            logger.warning(f"Failed to adapt LogQA record {record_idx}: {e}")
            self.record_drop("adaptation_error")
            return None

    def _extract_answer(self, record: Dict[str, Any]) -> Optional[str]:
        """Extract answer from LogQA record."""
        # Try answer field
        if "answer" in record and record["answer"]:
            answer = record["answer"]
            if isinstance(answer, list):
                return answer[0] if answer else None
            return str(answer)

        # Try answers field (list format)
        if "answers" in record and record["answers"]:
            answers = record["answers"]
            if isinstance(answers, list) and answers:
                return str(answers[0])

        # Try response field
        if "response" in record and record["response"]:
            return str(record["response"])

        return None

    def _extract_contexts(self, record: Dict[str, Any]) -> List[str]:
        """
        Extract contexts from LogQA record.

        LogQA contexts may contain:
        - Raw log entries
        - Documentation snippets
        - Error messages
        """
        contexts = []

        # Try context field
        if "context" in record and record["context"]:
            context = record["context"]
            if isinstance(context, str):
                contexts.append(context)
            elif isinstance(context, list):
                for c in context:
                    if isinstance(c, str) and c.strip():
                        contexts.append(c.strip())

        # Try log_entries field
        if not contexts and "log_entries" in record:
            entries = record["log_entries"]
            if isinstance(entries, list):
                # Join log entries into single context
                log_text = "\n".join(str(e) for e in entries if e)
                if log_text.strip():
                    contexts.append(log_text)
            elif isinstance(entries, str):
                contexts.append(entries)

        # Try documents field
        if not contexts and "documents" in record:
            docs = record["documents"]
            if isinstance(docs, list):
                for doc in docs:
                    if isinstance(doc, str) and doc.strip():
                        contexts.append(doc.strip())

        return contexts

    def _classify_log_question(self, question: str) -> str:
        """
        Classify question type using log-specific keywords.

        Args:
            question: Question text

        Returns:
            Question type string
        """
        question_lower = question.lower()

        # Check log-specific keywords first
        for qtype, keywords in self.LOG_QUESTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in question_lower:
                    return qtype

        # Fall back to general classification
        return self.classify_question_type(question)

    def _assign_log_difficulty(
        self,
        question_type: str,
        context_length: int,
        log_type: str
    ) -> str:
        """
        Assign difficulty based on log-specific factors.

        Heuristics:
        - Security logs → harder (D2-D3)
        - Application logs → medium (D1-D2)
        - Multi-hop questions → D3
        - Short lookup questions → D1

        Args:
            question_type: Classified question type
            context_length: Total context length
            log_type: Type of log

        Returns:
            Difficulty level (D1, D2, D3)
        """
        # Security and audit logs are harder
        if log_type and any(t in log_type.lower() for t in ["security", "audit", "auth"]):
            return "D3" if question_type in ["multihop", "policy"] else "D2"

        # Multi-hop and policy questions are hard
        if question_type in ["multihop", "policy"]:
            return "D3"

        # Troubleshooting (howto) is medium
        if question_type == "howto":
            return "D2"

        # Simple lookups based on context length
        if question_type in ["lookup", "entity"]:
            return "D1" if context_length < 1000 else "D2"

        # Default
        return "D2"
