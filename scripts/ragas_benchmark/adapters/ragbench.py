"""
RAGBench dataset adapter.

RAGBench is a comprehensive RAG evaluation benchmark from Galileo
covering diverse document types and question categories.

Dataset: https://huggingface.co/datasets/rungalileo/ragbench

Sprint 82: Phase 1 - Text-Only Benchmark
"""

from typing import Dict, Any, Optional, List
import logging

from .base import DatasetAdapter
from ..models import NormalizedSample

logger = logging.getLogger(__name__)


class RAGBenchAdapter(DatasetAdapter):
    """
    Adapter for RAGBench dataset.

    RAGBench Structure (varies by subset):
    - question: The question text
    - answer: Ground truth answer (or "response")
    - context: Context string or list
    - documents: List of document texts (alternative to context)

    Multiple subsets available:
    - covidqa, cuad, delucionqa, emanual, expertqa
    - finqa, hagrid, hotpotqa, msmarco, pubmedqa
    - tatqa, techqa

    Normalization:
    - Handles both "answer" and "response" fields
    - Handles both "context" and "documents" fields
    - Question type inferred from keywords
    """

    def get_doc_type(self) -> str:
        return "clean_text"

    def get_source_name(self) -> str:
        return "ragbench"

    def get_fields_mapping(self) -> Dict[str, str]:
        return {
            "question": "question",
            "ground_truth": "answer OR response",
            "contexts": "context OR documents",
        }

    def adapt(self, record: Dict[str, Any], record_idx: int = 0) -> Optional[NormalizedSample]:
        """
        Transform RAGBench record to NormalizedSample.

        Args:
            record: Raw RAGBench record
            record_idx: Sequential index

        Returns:
            NormalizedSample or None if invalid
        """
        try:
            # Extract question
            question = record.get("question", "")
            if not question:
                self.record_drop("missing_question")
                return None

            # Extract answer (handle multiple field names)
            answer = self._extract_answer(record)
            if not answer:
                self.record_drop("missing_answer")
                return None

            # Extract contexts (handle multiple formats)
            contexts = self._extract_contexts(record)

            # Validate
            is_valid, drop_reason = self.validate_sample(question, answer, contexts)
            if not is_valid:
                self.record_drop(drop_reason)
                return None

            # Classify question type
            question_type = self.classify_question_type(question)

            # Assign difficulty
            context_length = sum(len(c) for c in contexts)
            difficulty = self.assign_difficulty(question_type, context_length)

            # Generate ID
            original_id = record.get("id", str(record_idx))
            sample_id = self.generate_id("ragbench", original_id, record_idx)

            # Build metadata
            metadata = {
                "original_id": original_id,
                "ragbench_subset": record.get("subset", "unknown"),
                "sample_method": "stratified",
                "phase": 1,
            }

            # Preserve any additional fields
            for field in ["source", "category", "domain"]:
                if field in record:
                    metadata[f"ragbench_{field}"] = record[field]

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
            logger.warning(f"Failed to adapt RAGBench record {record_idx}: {e}")
            self.record_drop("adaptation_error")
            return None

    def _extract_answer(self, record: Dict[str, Any]) -> Optional[str]:
        """
        Extract answer from record, handling multiple field names.

        RAGBench uses different field names across subsets:
        - "answer": Most common
        - "response": Some subsets
        - "answers": List format (take first)
        """
        # Try direct answer field
        if "answer" in record and record["answer"]:
            answer = record["answer"]
            if isinstance(answer, list):
                return answer[0] if answer else None
            return str(answer)

        # Try response field
        if "response" in record and record["response"]:
            return str(record["response"])

        # Try answers list
        if "answers" in record and record["answers"]:
            answers = record["answers"]
            if isinstance(answers, list) and answers:
                return str(answers[0])
            return str(answers)

        return None

    def _extract_contexts(self, record: Dict[str, Any]) -> List[str]:
        """
        Extract contexts from record, handling multiple formats.

        RAGBench uses different context formats:
        - "context": Single string or list
        - "documents": List of document dicts or strings
        - "passages": List of passage strings
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
                    elif isinstance(c, dict):
                        # Handle dict format {"text": "...", "title": "..."}
                        text = c.get("text", c.get("content", ""))
                        if text:
                            contexts.append(str(text))

        # Try documents field
        if not contexts and "documents" in record and record["documents"]:
            docs = record["documents"]
            if isinstance(docs, list):
                for doc in docs:
                    if isinstance(doc, str) and doc.strip():
                        contexts.append(doc.strip())
                    elif isinstance(doc, dict):
                        text = doc.get("text", doc.get("content", doc.get("document", "")))
                        if text:
                            contexts.append(str(text))

        # Try passages field
        if not contexts and "passages" in record and record["passages"]:
            passages = record["passages"]
            if isinstance(passages, list):
                for p in passages:
                    if isinstance(p, str) and p.strip():
                        contexts.append(p.strip())
                    elif isinstance(p, dict):
                        text = p.get("text", p.get("passage", ""))
                        if text:
                            contexts.append(str(text))

        # Try retrieved_contexts field (some RAGAS datasets)
        if not contexts and "retrieved_contexts" in record and record["retrieved_contexts"]:
            retrieved = record["retrieved_contexts"]
            if isinstance(retrieved, list):
                for ctx in retrieved:
                    if isinstance(ctx, str) and ctx.strip():
                        contexts.append(ctx.strip())

        return contexts
