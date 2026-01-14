"""Pytest fixtures for recursive LLM agent tests (Sprint 92).

Sprint 92 Fixtures:
- Mock embedding service (BGE-M3 dense+sparse)
- Mock C-LARA classifier
- Mock LangChain models
- Mock skill registry
- Sample documents and queries
- RecursiveLLMSettings factory functions
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
import numpy as np


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service returning fake BGE-M3 embeddings.

    Returns embeddings with:
    - dense: 1024-dimensional vector
    - sparse: Dictionary of token_id -> weight pairs
    """
    service = AsyncMock()

    # Mock embed_single for individual queries
    async def embed_single_side_effect(text, **kwargs):
        """Mock embedding for single text."""
        # Deterministic embeddings based on text hash
        seed = hash(text) % (2**31)
        np.random.seed(seed)
        dense = np.random.randn(1024).astype(np.float32) / 100

        # Sparse tokens (simulated lexical weights)
        sparse = {i: float(0.5 - i * 0.1) for i in range(5)}
        sparse = {k: v for k, v in sparse.items() if v > 0.1}

        return {
            "dense": dense.tolist(),
            "sparse": sparse,
        }

    service.embed_single.side_effect = embed_single_side_effect

    # Mock embed_batch for multiple texts
    async def embed_batch_side_effect(texts, **kwargs):
        """Mock embeddings for batch of texts."""
        return [await embed_single_side_effect(text) for text in texts]

    service.embed_batch.side_effect = embed_batch_side_effect

    return service


@pytest.fixture
def mock_embedding_service_sync():
    """Synchronous mock embedding service (for non-async contexts)."""
    service = MagicMock()

    def embed_single_side_effect(text, **kwargs):
        """Mock embedding for single text."""
        seed = hash(text) % (2**31)
        np.random.seed(seed)
        dense = np.random.randn(1024).astype(np.float32) / 100

        sparse = {i: float(0.5 - i * 0.1) for i in range(5)}
        sparse = {k: v for k, v in sparse.items() if v > 0.1}

        return {
            "dense": dense.tolist(),
            "sparse": sparse,
        }

    service.embed_single.side_effect = embed_single_side_effect

    def embed_batch_side_effect(texts, **kwargs):
        """Mock embeddings for batch of texts."""
        return [embed_single_side_effect(text) for text in texts]

    service.embed_batch.side_effect = embed_batch_side_effect

    return service


@pytest.fixture
def mock_clara_classifier():
    """Mock C-LARA intent classifier from Sprint 81.

    Returns AsyncMock that classifies queries into C-LARA intents.
    """
    from src.components.retrieval.intent_classifier import CLARAIntent

    classifier = AsyncMock()

    async def classify_side_effect(query, **kwargs):
        """Mock C-LARA classification based on query patterns."""
        query_lower = query.lower()

        if any(word in query_lower for word in ["where", "find", "locate", "show"]):
            intent = CLARAIntent.NAVIGATION
        elif any(word in query_lower for word in ["how", "implement", "set up", "configure"]):
            intent = CLARAIntent.PROCEDURAL
        elif any(word in query_lower for word in ["compare", "difference", "vs", "versus"]):
            intent = CLARAIntent.COMPARISON
        elif any(word in query_lower for word in ["recommend", "suggest", "best", "should"]):
            intent = CLARAIntent.RECOMMENDATION
        else:
            intent = CLARAIntent.FACTUAL

        return MagicMock(
            clara_intent=intent,
            confidence=0.92,
        )

    classifier.classify.side_effect = classify_side_effect

    return classifier


@pytest.fixture
def mock_llm():
    """Mock LangChain ChatModel for LLM-based scoring."""
    from langchain_core.language_models.chat_models import BaseChatModel

    llm = AsyncMock(spec=BaseChatModel)

    async def invoke_side_effect(text, **kwargs):
        """Mock LLM response."""
        # Return a mock message with content containing a relevance score
        return MagicMock(content="0.85")

    llm.ainvoke.side_effect = invoke_side_effect
    llm.invoke.side_effect = lambda x, **kwargs: MagicMock(content="0.85")

    return llm


@pytest.fixture
def mock_skill_registry():
    """Mock skill registry for loading context skills."""
    from src.agents.skills.registry import SkillRegistry, LoadedSkill

    registry = MagicMock(spec=SkillRegistry)
    registry._loaded = {}

    # Mock list_available
    registry.list_available.return_value = [
        "recursive-context",
        "synthesis",
        "relevance-scoring",
    ]

    # Mock list_active
    registry.list_active.return_value = []

    # Mock activate
    def activate_side_effect(skill_name):
        if skill_name == "recursive-context":
            skill = MagicMock(spec=LoadedSkill)
            skill.prompts = {
                "relevance_scoring": "Score relevance of '{text_preview}' to query '{query}': "
            }
            registry._loaded[skill_name] = skill
            if skill_name not in registry.list_active():
                registry.list_active.return_value = registry.list_active() + [skill_name]
        elif skill_name == "synthesis":
            skill = MagicMock(spec=LoadedSkill)
            registry._loaded[skill_name] = skill
            if skill_name not in registry.list_active():
                registry.list_active.return_value = registry.list_active() + [skill_name]

    registry.activate.side_effect = activate_side_effect

    # Mock deactivate
    def deactivate_side_effect(skill_name):
        if skill_name in registry._loaded:
            del registry._loaded[skill_name]
        active = [s for s in registry.list_active() if s != skill_name]
        registry.list_active.return_value = active

    registry.deactivate.side_effect = deactivate_side_effect

    return registry


@pytest.fixture
def mock_multi_vector_model():
    """Mock BGE-M3 multi-vector model for FlagEmbedding."""
    model = MagicMock()

    def encode_side_effect(texts, **kwargs):
        """Mock multi-vector encoding (sparse and dense)."""
        if isinstance(texts, str):
            texts = [texts]

        # Return mock output with dense and sparse components
        return {
            "dense_vecs": np.random.randn(len(texts), 1024).astype(np.float32),
            "sparse_vecs": [
                {0: 0.5, 1: 0.3, 2: 0.2} for _ in texts
            ],
        }

    model.encode.side_effect = encode_side_effect

    return model


@pytest.fixture
def recursive_llm_settings():
    """Default RecursiveLLMSettings for testing.

    Returns settings with standard 3-level configuration.
    """
    from src.core.config import RecursiveLLMSettings

    return RecursiveLLMSettings(
        max_depth=3,
        max_parallel_workers=1,  # DGX Spark
        worker_limits={
            "ollama": 1,
            "openai": 10,
            "alibaba": 5,
        },
    )


@pytest.fixture
def recursive_llm_settings_custom():
    """Custom RecursiveLLMSettings with all per-level configs."""
    from src.core.config import RecursiveLLMSettings, RecursiveLevelConfig

    return RecursiveLLMSettings(
        max_depth=3,
        max_parallel_workers=5,
        levels=[
            RecursiveLevelConfig(
                level=0,
                segment_size_tokens=16384,
                overlap_tokens=400,
                top_k_subsegments=5,
                scoring_method="dense+sparse",
                relevance_threshold=0.5,
            ),
            RecursiveLevelConfig(
                level=1,
                segment_size_tokens=8192,
                overlap_tokens=300,
                top_k_subsegments=4,
                scoring_method="dense+sparse",
                relevance_threshold=0.6,
            ),
            RecursiveLevelConfig(
                level=2,
                segment_size_tokens=4096,
                overlap_tokens=200,
                top_k_subsegments=3,
                scoring_method="adaptive",
                relevance_threshold=0.7,
            ),
        ],
    )


@pytest.fixture
def sample_document_short():
    """Short sample document for testing (single level)."""
    return """
# Introduction

This is a short sample document for testing recursive LLM processing.

## Background

The background section explains the context and motivation.

## Methods

We use method A and method B for this study.

## Results

The results show an improvement of 25% over baseline.

## Discussion

This improvement is significant because of reasons X and Y.

## Conclusion

In conclusion, our approach is effective and efficient.
"""


@pytest.fixture
def sample_document_long():
    """Long sample document for testing (multiple levels)."""
    chapters = []
    for ch in range(3):
        chapter = f"""
# Chapter {ch + 1}: Main Topic

This chapter covers important content related to the research.

## Section {ch + 1}.1: Background

Background information for this section. This provides context and motivation
for the research question. We need to understand the prior work in this area.

The prior work includes studies A, B, and C. These studies showed that X is true
and Y is false. Our work extends these findings by investigating Z.

## Section {ch + 1}.2: Methodology

We conducted experiments using the following methodology:

1. First, we collected data from N participants
2. We applied preprocessing steps A and B
3. We trained model X with hyperparameters Y
4. We evaluated using metrics P, Q, and R

The evaluation showed F1 scores ranging from 0.82 to 0.95.

## Section {ch + 1}.3: Results

The results are presented in Table {ch + 1} and Figure {ch + 1}.

Table {ch + 1} shows the comparative results. The p-value is 0.001, indicating
statistical significance. The improvement over baseline is {30 + ch * 5}%.

Figure {ch + 1} illustrates the distribution of results. The mean is {100 + ch * 10}
and the standard deviation is {5 + ch}.

## Section {ch + 1}.4: Analysis

We analyze these results in light of the research question. The findings support
our hypothesis that approach X is more effective than approach Y.

The analysis reveals several insights:
- Insight 1 about the data
- Insight 2 about the methodology
- Insight 3 about future work

## Section {ch + 1}.5: Discussion

Discussing the implications of our findings. These findings contribute to the field
by providing new evidence for claim X and questioning assumption Y.

However, there are limitations to consider. First, the sample size was limited to
N participants. Second, we used only English language data. Third, we did not
test on all possible domains.

Future work should address these limitations by collecting more data, testing
in other languages, and evaluating on diverse domains.
"""
        chapters.append(chapter)

    return "\n\n".join(chapters)


@pytest.fixture
def sample_queries():
    """Sample queries for testing granularity classification."""
    return {
        "navigation": [
            "Where is the introduction section?",
            "Find the methodology section",
            "Show me the conclusion",
            "Locate the results table",
        ],
        "factual_fine_grained": [
            "What is the p-value?",
            "Show Table 1",
            "What does Figure 3 show?",
            "What is the exact accuracy?",
        ],
        "factual_holistic": [
            "Summarize the methodology",
            "Explain the approach",
            "Describe the overall findings",
            "Why did they choose this method?",
        ],
        "procedural": [
            "How do I implement this algorithm?",
            "What are the steps to set up?",
            "Walk me through the process",
            "How to reproduce the results?",
        ],
        "comparison": [
            "Compare method A with method B",
            "What is the difference between X and Y?",
            "Which approach is better?",
            "How do these methods compare?",
        ],
    }


@pytest.fixture
def sample_segments():
    """Sample document segments for testing scoring."""
    from src.agents.context.recursive_llm import DocumentSegment

    return [
        DocumentSegment(
            id="seg_0_0",
            content="Introduction section explaining the research question and motivation.",
            level=0,
            parent_id=None,
            start_offset=0,
            end_offset=100,
            relevance_score=0.0,
            summary="",
        ),
        DocumentSegment(
            id="seg_0_1",
            content="Methods section describing the experimental setup and procedures.",
            level=0,
            parent_id=None,
            start_offset=100,
            end_offset=200,
            relevance_score=0.0,
            summary="",
        ),
        DocumentSegment(
            id="seg_0_2",
            content="Results section showing the p-value, accuracy metrics, and statistical tests.",
            level=0,
            parent_id=None,
            start_offset=200,
            end_offset=300,
            relevance_score=0.0,
            summary="",
        ),
        DocumentSegment(
            id="seg_0_3",
            content="Discussion of implications and limitations of the findings.",
            level=0,
            parent_id=None,
            start_offset=300,
            end_offset=400,
            relevance_score=0.0,
            summary="",
        ),
        DocumentSegment(
            id="seg_0_4",
            content="Conclusion summarizing the main contributions and future work.",
            level=0,
            parent_id=None,
            start_offset=400,
            end_offset=500,
            relevance_score=0.0,
            summary="",
        ),
    ]


@pytest.fixture
def sample_embedding_vectors():
    """Sample pre-computed embeddings for testing."""
    np.random.seed(42)

    # Query embedding
    query_embedding = np.random.randn(1024).astype(np.float32) / 100

    # Document embeddings
    doc_embeddings = {
        "doc_0": np.random.randn(1024).astype(np.float32) / 100,  # Random
        "doc_1": np.random.randn(1024).astype(np.float32) / 100,  # Random
        "doc_2": (query_embedding + np.random.randn(1024).astype(np.float32) * 0.1),  # Similar to query
        "doc_3": np.random.randn(1024).astype(np.float32) / 100,  # Random
    }

    return {
        "query": query_embedding,
        "documents": doc_embeddings,
    }


@pytest.fixture
def cleanup_temp_models(tmp_path):
    """Cleanup fixture for temporary model files."""
    yield tmp_path
    # Cleanup after test
    import shutil
    if tmp_path.exists():
        shutil.rmtree(tmp_path, ignore_errors=True)
