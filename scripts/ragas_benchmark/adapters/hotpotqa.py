"""
HotpotQA dataset adapter.

HotpotQA is a multi-hop question answering dataset requiring
reasoning over multiple Wikipedia paragraphs.

Dataset: https://huggingface.co/datasets/hotpot_qa
Paper: https://arxiv.org/abs/1809.09600

Sprint 82: Phase 1 - Text-Only Benchmark
"""

from typing import Dict, Any, Optional, List
import logging

from .base import DatasetAdapter
from ..models import NormalizedSample

logger = logging.getLogger(__name__)


class HotpotQAAdapter(DatasetAdapter):
    """
    Adapter for HotpotQA dataset.

    HotpotQA Structure:
    - id: Unique question ID
    - question: The question text
    - answer: Ground truth answer
    - type: "comparison" or "bridge" (multi-hop type)
    - level: "easy", "medium", "hard"
    - context: Dict with "title" and "sentences" lists
    - supporting_facts: List of [title, sentence_idx] pairs

    Normalization:
    - Contexts are flattened from nested structure
    - Supporting facts are preserved in metadata
    - Question type is inferred from content + HotpotQA type field
    """

    def get_doc_type(self) -> str:
        return "clean_text"

    def get_source_name(self) -> str:
        return "hotpot_qa"

    def get_fields_mapping(self) -> Dict[str, str]:
        return {
            "id": "id",
            "question": "question",
            "ground_truth": "answer",
            "contexts": "context",
            "type": "type",
            "level": "level",
            "supporting_facts": "supporting_facts",
        }

    def adapt(self, record: Dict[str, Any], record_idx: int = 0) -> Optional[NormalizedSample]:
        """
        Transform HotpotQA record to NormalizedSample.

        Args:
            record: Raw HotpotQA record
            record_idx: Sequential index

        Returns:
            NormalizedSample or None if invalid
        """
        try:
            # Extract fields
            original_id = record.get("id", f"unknown_{record_idx}")
            question = record.get("question", "")
            answer = record.get("answer", "")

            # Extract contexts from nested structure
            contexts = self._extract_contexts(record)

            # Validate
            is_valid, drop_reason = self.validate_sample(question, answer, contexts)
            if not is_valid:
                self.record_drop(drop_reason)
                return None

            # Classify question type
            # Use HotpotQA's type field as a hint
            hotpot_type = record.get("type", "")
            question_type = self._infer_question_type(question, hotpot_type)

            # Assign difficulty
            # Use HotpotQA's level field as a hint
            hotpot_level = record.get("level", "")
            context_length = sum(len(c) for c in contexts)
            difficulty = self._infer_difficulty(hotpot_level, question_type, context_length)

            # Generate ID
            sample_id = self.generate_id("hotpot", original_id, record_idx)

            # Build metadata
            supporting_facts = record.get("supporting_facts", {})
            metadata = {
                "original_id": original_id,
                "hotpot_type": hotpot_type,
                "hotpot_level": hotpot_level,
                "supporting_facts": self._format_supporting_facts(supporting_facts),
                "sample_method": "stratified",
                "phase": 1,
            }

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
            logger.warning(f"Failed to adapt HotpotQA record {record_idx}: {e}")
            self.record_drop("adaptation_error")
            return None

    def _extract_contexts(self, record: Dict[str, Any]) -> List[str]:
        """
        Extract and flatten contexts from HotpotQA structure.

        HotpotQA context structure:
        {
            "title": ["Title1", "Title2", ...],
            "sentences": [["Sent1a", "Sent1b"], ["Sent2a"], ...]
        }

        Returns:
            List of context strings (one per document)
        """
        contexts = []
        context_data = record.get("context", {})

        if not context_data:
            return contexts

        titles = context_data.get("title", [])
        sentences_list = context_data.get("sentences", [])

        # Combine title + sentences for each document
        for i, title in enumerate(titles):
            if i < len(sentences_list):
                sentences = sentences_list[i]
                if isinstance(sentences, list):
                    # Join sentences into paragraph
                    text = " ".join(sentences)
                    context = f"{title}: {text}" if title else text
                    if context.strip():
                        contexts.append(context.strip())

        return contexts

    def _format_supporting_facts(self, facts: Dict[str, Any]) -> List[List[Any]]:
        """
        Format supporting facts for metadata.

        HotpotQA format: {"title": ["T1", "T2"], "sent_id": [0, 1]}
        Output format: [["T1", 0], ["T2", 1]]
        """
        if not facts:
            return []

        titles = facts.get("title", [])
        sent_ids = facts.get("sent_id", [])

        result = []
        for i, title in enumerate(titles):
            sent_id = sent_ids[i] if i < len(sent_ids) else 0
            result.append([title, sent_id])

        return result

    def _infer_question_type(self, question: str, hotpot_type: str) -> str:
        """
        Infer question type from question text and HotpotQA type.

        Args:
            question: Question text
            hotpot_type: HotpotQA type field ("comparison" or "bridge")

        Returns:
            Normalized question type
        """
        # Use HotpotQA type as primary signal
        if hotpot_type == "comparison":
            return "comparison"

        # "bridge" type = multi-hop reasoning
        if hotpot_type == "bridge":
            return "multihop"

        # Fall back to keyword-based classification
        return self.classify_question_type(question)

    def _infer_difficulty(
        self,
        hotpot_level: str,
        question_type: str,
        context_length: int
    ) -> str:
        """
        Infer difficulty from HotpotQA level and other factors.

        Args:
            hotpot_level: HotpotQA level field
            question_type: Classified question type
            context_length: Total context length

        Returns:
            Difficulty level (D1, D2, D3)
        """
        # Map HotpotQA levels to our difficulty
        level_mapping = {
            "easy": "D1",
            "medium": "D2",
            "hard": "D3",
        }

        if hotpot_level in level_mapping:
            return level_mapping[hotpot_level]

        # Fall back to heuristic
        return self.assign_difficulty(question_type, context_length)
