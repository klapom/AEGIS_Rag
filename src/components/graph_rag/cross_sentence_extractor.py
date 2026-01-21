"""Cross-Sentence Relation Extraction using Sliding Windows.

Sprint 86 Feature 86.8: Extract relations that span multiple sentences.

Problem:
    Sentence 1: "OpenAI released GPT-4 in March 2023."
    Sentence 2: "The model achieved state-of-the-art results on many benchmarks."

    Missed relation: {GPT-4 → ACHIEVED → state-of-the-art results}
    (Because "model" in S2 refers to "GPT-4" in S1)

Solution:
    Use sliding windows of 3 sentences to provide more context to the LLM.
    Combined with coreference resolution, this significantly improves
    cross-sentence relation extraction.

Usage:
    extractor = CrossSentenceExtractor(window_size=3, overlap=1)
    windows = list(extractor.create_windows(text))
    # Each window contains 3 consecutive sentences for extraction
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Iterator

import spacy
import structlog
from spacy.tokens import Doc

logger = structlog.get_logger(__name__)

# Feature flag for cross-sentence extraction
# Default: enabled
USE_CROSS_SENTENCE = os.environ.get("AEGIS_USE_CROSS_SENTENCE", "1") == "1"


@lru_cache(maxsize=4)
def _load_spacy_model(lang: str = "en") -> spacy.Language:
    """Load SpaCy model for sentence segmentation.

    Args:
        lang: Language code ('en', 'de')

    Returns:
        SpaCy Language model
    """
    model_map = {
        "en": ["en_core_web_sm", "en_core_web_md", "en_core_web_lg"],
        "de": ["de_core_news_sm", "de_core_news_md", "de_core_news_lg"],
    }

    models = model_map.get(lang, model_map["en"])

    for model_name in models:
        try:
            return spacy.load(model_name)
        except OSError:
            continue

    # Fallback to blank model with sentencizer
    logger.warning(f"No SpaCy model found for {lang}, using blank model with sentencizer")
    nlp = spacy.blank(lang)
    nlp.add_pipe("sentencizer")
    return nlp


@dataclass
class SentenceWindow:
    """Window of consecutive sentences for relation extraction.

    Attributes:
        sentences: List of sentence texts
        start_idx: Index of first sentence in original document
        end_idx: Index after last sentence (exclusive)
        char_start: Character offset of window start
        char_end: Character offset of window end
    """

    sentences: list[str]
    start_idx: int
    end_idx: int
    char_start: int = 0
    char_end: int = 0

    @property
    def text(self) -> str:
        """Get concatenated window text."""
        return " ".join(self.sentences)

    @property
    def window_size(self) -> int:
        """Number of sentences in window."""
        return len(self.sentences)

    def __repr__(self) -> str:
        return f"SentenceWindow(size={self.window_size}, idx={self.start_idx}-{self.end_idx})"


@dataclass
class CrossSentenceResult:
    """Result of cross-sentence extraction."""

    original_text: str
    windows: list[SentenceWindow] = field(default_factory=list)
    window_count: int = 0
    total_sentences: int = 0
    avg_window_chars: float = 0.0


class CrossSentenceExtractor:
    """Extract relations across sentence boundaries using sliding windows.

    This extractor creates overlapping windows of sentences to provide
    more context for relation extraction. Combined with coreference
    resolution (Feature 86.7), this significantly improves extraction
    of relations that span multiple sentences.

    Example:
        >>> extractor = CrossSentenceExtractor(window_size=3, overlap=1)
        >>> text = "Microsoft founded in 1975. It acquired GitHub. GitHub has 100M users."
        >>> windows = list(extractor.create_windows(text))
        >>> len(windows)
        2  # [S1,S2,S3], [S2,S3,S4] with overlap

    Attributes:
        window_size: Number of sentences per window (default: 3)
        overlap: Sentences to overlap between windows (default: 1)
        lang: Language code for SpaCy model
        nlp: SpaCy language model for sentence segmentation
    """

    def __init__(
        self,
        window_size: int = 3,
        overlap: int = 1,
        lang: str = "en",
        nlp: spacy.Language | None = None,
    ):
        """Initialize the cross-sentence extractor.

        Args:
            window_size: Number of sentences per window (2-5 recommended)
            overlap: Sentences to overlap between windows (0 to window_size-1)
            lang: Language code ('en', 'de')
            nlp: Optional pre-loaded SpaCy model
        """
        if window_size < 2:
            raise ValueError("window_size must be at least 2")
        if overlap >= window_size:
            raise ValueError("overlap must be less than window_size")

        self.window_size = window_size
        self.overlap = overlap
        self.lang = lang
        self.nlp = nlp or _load_spacy_model(lang)

        logger.info(
            "cross_sentence_extractor_initialized",
            window_size=window_size,
            overlap=overlap,
            lang=lang,
            model=self.nlp.meta.get("name", "unknown"),
        )

    def create_windows(self, text: str) -> Iterator[SentenceWindow]:
        """Create overlapping sentence windows from text.

        Args:
            text: Input text to segment into windows

        Yields:
            SentenceWindow objects with consecutive sentences
        """
        if not text or not text.strip():
            return

        doc = self.nlp(text)
        sentences_data = []

        # Collect sentences with character offsets
        for sent in doc.sents:
            sent_text = sent.text.strip()
            if sent_text:  # Skip empty sentences
                sentences_data.append(
                    {
                        "text": sent_text,
                        "char_start": sent.start_char,
                        "char_end": sent.end_char,
                    }
                )

        total_sentences = len(sentences_data)

        if total_sentences == 0:
            return

        # If text is shorter than window_size, yield single window
        if total_sentences <= self.window_size:
            sentences = [s["text"] for s in sentences_data]
            yield SentenceWindow(
                sentences=sentences,
                start_idx=0,
                end_idx=total_sentences,
                char_start=sentences_data[0]["char_start"],
                char_end=sentences_data[-1]["char_end"],
            )
            return

        # Sliding window with overlap
        step = self.window_size - self.overlap

        for i in range(0, total_sentences - self.window_size + 1, step):
            window_data = sentences_data[i : i + self.window_size]
            sentences = [s["text"] for s in window_data]

            yield SentenceWindow(
                sentences=sentences,
                start_idx=i,
                end_idx=i + self.window_size,
                char_start=window_data[0]["char_start"],
                char_end=window_data[-1]["char_end"],
            )

        # Check if we need a final window for remaining sentences
        last_window_end = ((total_sentences - self.window_size) // step) * step + self.window_size
        if last_window_end < total_sentences:
            # Final window covers the last window_size sentences
            window_data = sentences_data[-self.window_size :]
            sentences = [s["text"] for s in window_data]

            yield SentenceWindow(
                sentences=sentences,
                start_idx=total_sentences - self.window_size,
                end_idx=total_sentences,
                char_start=window_data[0]["char_start"],
                char_end=window_data[-1]["char_end"],
            )

    def analyze(self, text: str) -> CrossSentenceResult:
        """Analyze text and return window information.

        Args:
            text: Input text

        Returns:
            CrossSentenceResult with window statistics
        """
        windows = list(self.create_windows(text))

        total_chars = sum(len(w.text) for w in windows)
        avg_chars = total_chars / len(windows) if windows else 0

        doc = self.nlp(text)
        total_sentences = sum(1 for _ in doc.sents)

        result = CrossSentenceResult(
            original_text=text,
            windows=windows,
            window_count=len(windows),
            total_sentences=total_sentences,
            avg_window_chars=avg_chars,
        )

        logger.info(
            "cross_sentence_analysis_complete",
            total_sentences=total_sentences,
            windows_created=len(windows),
            avg_window_chars=round(avg_chars, 1),
        )

        return result


# Module-level singleton
_extractor_cache: dict[str, CrossSentenceExtractor] = {}


def get_cross_sentence_extractor(
    lang: str = "en",
    window_size: int = 3,
    overlap: int = 1,
) -> CrossSentenceExtractor:
    """Get or create a cross-sentence extractor.

    Args:
        lang: Language code
        window_size: Sentences per window
        overlap: Window overlap

    Returns:
        CrossSentenceExtractor instance
    """
    key = f"{lang}_{window_size}_{overlap}"
    if key not in _extractor_cache:
        _extractor_cache[key] = CrossSentenceExtractor(
            window_size=window_size,
            overlap=overlap,
            lang=lang,
        )
    return _extractor_cache[key]


def apply_cross_sentence_windows(
    text: str,
    lang: str = "en",
    window_size: int = 3,
    overlap: int = 1,
) -> list[str]:
    """Convenience function to get window texts from input text.

    Args:
        text: Input text
        lang: Language code
        window_size: Sentences per window
        overlap: Window overlap

    Returns:
        List of window text strings
    """
    if not USE_CROSS_SENTENCE:
        return [text]  # Return original text as single "window"

    extractor = get_cross_sentence_extractor(lang, window_size, overlap)
    windows = extractor.create_windows(text)
    return [w.text for w in windows]
