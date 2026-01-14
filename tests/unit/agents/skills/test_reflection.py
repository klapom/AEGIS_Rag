"""Unit tests for Reflection Skill.

Sprint Context:
    - Sprint 90 (2026-01-14): Feature 90.2 - Reflection Loop in Agent Core (8 SP)

Tests:
    - Reflection on answers
    - Score parsing from critique
    - Issue extraction
    - Answer improvement loop
    - Max iterations limit
    - Confidence threshold
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.skills.reflection import ReflectionResult, ReflectionSkill


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    llm = MagicMock()
    llm.ainvoke = AsyncMock()
    return llm


@pytest.fixture
def reflection_skill(mock_llm):
    """Create ReflectionSkill instance."""
    return ReflectionSkill(llm=mock_llm, max_iterations=3, confidence_threshold=0.85)


@pytest.fixture
def sample_contexts():
    """Sample contexts for testing."""
    return [
        "Photosynthesis is the process by which plants convert light energy into chemical energy.",
        "During photosynthesis, plants use carbon dioxide, water, and sunlight to produce glucose and oxygen.",
        "The process occurs in chloroplasts, specifically in the chlorophyll-containing thylakoid membranes.",
    ]


class TestReflectionBasics:
    """Test basic reflection functionality."""

    @pytest.mark.asyncio
    async def test_reflect_on_answer(
        self, reflection_skill, mock_llm, sample_contexts
    ):
        """Test reflecting on an answer."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = """SCORE: 0.65
ISSUES: [incomplete, lacks detail about process steps]
SUGGESTIONS: [explain the light-dependent and light-independent reactions]

The answer is factually correct but incomplete. It doesn't explain the detailed process.
"""
        mock_llm.ainvoke.return_value = mock_response

        result = await reflection_skill.reflect(
            query="What is photosynthesis?",
            answer="Plants convert sunlight into energy.",
            contexts=sample_contexts,
        )

        assert isinstance(result, ReflectionResult)
        assert result.score == 0.65
        assert "incomplete" in result.issues
        assert "lacks detail about process steps" in result.issues
        assert result.original_answer == "Plants convert sunlight into energy."
        assert result.iteration == 0
        assert result.improved_answer is None

    @pytest.mark.asyncio
    async def test_reflect_high_score(
        self, reflection_skill, mock_llm, sample_contexts
    ):
        """Test reflection on high-quality answer."""
        # Mock LLM response with high score
        mock_response = MagicMock()
        mock_response.content = """SCORE: 0.95
ISSUES: []
SUGGESTIONS: []

The answer is comprehensive, accurate, and well-structured.
"""
        mock_llm.ainvoke.return_value = mock_response

        result = await reflection_skill.reflect(
            query="What is photosynthesis?",
            answer="Photosynthesis is the process by which plants convert light energy into chemical energy, producing glucose and oxygen from carbon dioxide and water.",
            contexts=sample_contexts,
        )

        assert result.score == 0.95
        assert len(result.issues) == 0

    @pytest.mark.asyncio
    async def test_reflect_handles_dict_response(
        self, reflection_skill, mock_llm, sample_contexts
    ):
        """Test reflection handles dict response from LLM."""
        # Mock LLM response as dict (AegisLLMProxy format)
        mock_llm.ainvoke.return_value = {
            "content": "SCORE: 0.7\nISSUES: [missing examples]\nSUGGESTIONS: [add examples]"
        }

        result = await reflection_skill.reflect(
            query="What is photosynthesis?",
            answer="Plants make food.",
            contexts=sample_contexts,
        )

        assert result.score == 0.7
        assert "missing examples" in result.issues


class TestScoreParsing:
    """Test score parsing from critique."""

    def test_parse_score_valid(self, reflection_skill):
        """Test parsing valid score."""
        critique = "SCORE: 0.75\nISSUES: [some issues]"
        score = reflection_skill._parse_score(critique)
        assert score == 0.75

    def test_parse_score_float(self, reflection_skill):
        """Test parsing float score."""
        critique = "SCORE: 0.888\nISSUES: []"
        score = reflection_skill._parse_score(critique)
        assert score == 0.888

    def test_parse_score_out_of_range_high(self, reflection_skill):
        """Test parsing score > 1.0 clamps to 1.0."""
        critique = "SCORE: 1.5\nISSUES: []"
        score = reflection_skill._parse_score(critique)
        assert score == 1.0

    def test_parse_score_out_of_range_low(self, reflection_skill):
        """Test parsing score < 0.0 clamps to 0.0."""
        critique = "SCORE: -0.5\nISSUES: []"
        score = reflection_skill._parse_score(critique)
        assert score == 0.0

    def test_parse_score_missing(self, reflection_skill):
        """Test parsing missing score defaults to 0.5."""
        critique = "No score provided.\nISSUES: [missing score]"
        score = reflection_skill._parse_score(critique)
        assert score == 0.5


class TestIssuesParsing:
    """Test issues parsing from critique."""

    def test_parse_issues_single(self, reflection_skill):
        """Test parsing single issue."""
        critique = "SCORE: 0.5\nISSUES: [incomplete]"
        issues = reflection_skill._parse_issues(critique)
        assert "incomplete" in issues
        assert len(issues) == 1

    def test_parse_issues_multiple(self, reflection_skill):
        """Test parsing multiple issues."""
        critique = "SCORE: 0.4\nISSUES: [incomplete, lacks detail, missing examples]"
        issues = reflection_skill._parse_issues(critique)
        assert "incomplete" in issues
        assert "lacks detail" in issues
        assert "missing examples" in issues
        assert len(issues) == 3

    def test_parse_issues_empty(self, reflection_skill):
        """Test parsing empty issues list."""
        critique = "SCORE: 0.9\nISSUES: []"
        issues = reflection_skill._parse_issues(critique)
        assert len(issues) == 0

    def test_parse_issues_missing(self, reflection_skill):
        """Test parsing missing issues defaults to empty list."""
        critique = "SCORE: 0.5\nNo issues listed."
        issues = reflection_skill._parse_issues(critique)
        assert len(issues) == 0


class TestAnswerImprovement:
    """Test answer improvement functionality."""

    @pytest.mark.asyncio
    async def test_improve_answer(
        self, reflection_skill, mock_llm, sample_contexts
    ):
        """Test improving an answer."""
        # Initial reflection result
        initial_result = ReflectionResult(
            original_answer="Plants make food.",
            critique="SCORE: 0.5\nISSUES: [too brief, missing details]",
            score=0.5,
            issues=["too brief", "missing details"],
            iteration=0,
        )

        # Mock improved answer
        improve_response = MagicMock()
        improve_response.content = "Plants use photosynthesis to convert light energy into chemical energy, producing glucose and oxygen from carbon dioxide and water."
        mock_llm.ainvoke.return_value = improve_response

        # Mock re-evaluation (high score)
        reflection_skill.reflect = AsyncMock(
            return_value=ReflectionResult(
                original_answer=improve_response.content,
                critique="SCORE: 0.92\nISSUES: []",
                score=0.92,
                issues=[],
                iteration=1,
            )
        )

        result = await reflection_skill.improve(
            query="What is photosynthesis?",
            reflection=initial_result,
            contexts=sample_contexts,
        )

        assert result.iteration == 1
        assert result.score > initial_result.score
        assert result.improved_answer is not None

    @pytest.mark.asyncio
    async def test_improve_already_confident(
        self, reflection_skill, mock_llm, sample_contexts
    ):
        """Test improvement skipped if already confident."""
        # High-confidence reflection
        high_score_result = ReflectionResult(
            original_answer="Comprehensive answer.",
            critique="SCORE: 0.95\nISSUES: []",
            score=0.95,
            issues=[],
            iteration=0,
        )

        result = await reflection_skill.improve(
            query="What is photosynthesis?",
            reflection=high_score_result,
            contexts=sample_contexts,
        )

        # Should return same result (no improvement needed)
        assert result is high_score_result
        assert mock_llm.ainvoke.call_count == 0


class TestReflectionLoop:
    """Test full reflection loop with iterations."""

    @pytest.mark.asyncio
    async def test_reflect_and_improve_reaches_threshold(
        self, reflection_skill, mock_llm, sample_contexts
    ):
        """Test reflection loop reaches confidence threshold."""
        # First reflection (low score)
        reflection_response = MagicMock()
        reflection_response.content = "SCORE: 0.6\nISSUES: [incomplete]"

        # Improvement (higher score)
        improve_response = MagicMock()
        improve_response.content = "Improved answer with more detail."

        # Re-evaluation (high score)
        reeval_response = MagicMock()
        reeval_response.content = "SCORE: 0.9\nISSUES: []"

        mock_llm.ainvoke.side_effect = [
            reflection_response,
            improve_response,
            reeval_response,
        ]

        result = await reflection_skill.reflect_and_improve(
            query="What is photosynthesis?",
            answer="Plants make food.",
            contexts=sample_contexts,
        )

        # Should stop after reaching threshold
        assert result.score >= 0.85
        assert result.iteration <= 3

    @pytest.mark.asyncio
    async def test_reflect_and_improve_max_iterations(
        self, reflection_skill, mock_llm, sample_contexts
    ):
        """Test reflection loop hits max iterations."""
        # Always return low score (never reaches threshold)
        low_score_response = MagicMock()
        low_score_response.content = "SCORE: 0.6\nISSUES: [still incomplete]"

        improve_response = MagicMock()
        improve_response.content = "Slightly improved answer."

        # Alternate between reflection and improvement
        mock_llm.ainvoke.side_effect = [
            low_score_response,  # Initial reflection
            improve_response,  # Improvement 1
            low_score_response,  # Re-eval 1
            improve_response,  # Improvement 2
            low_score_response,  # Re-eval 2
            improve_response,  # Improvement 3
            low_score_response,  # Re-eval 3
        ]

        result = await reflection_skill.reflect_and_improve(
            query="What is photosynthesis?",
            answer="Plants make food.",
            contexts=sample_contexts,
        )

        # Should stop after max iterations
        assert result.iteration == 3

    @pytest.mark.asyncio
    async def test_reflect_and_improve_first_try_success(
        self, reflection_skill, mock_llm, sample_contexts
    ):
        """Test reflection loop succeeds on first try (high initial score)."""
        # High score on first reflection
        high_score_response = MagicMock()
        high_score_response.content = "SCORE: 0.95\nISSUES: []"

        mock_llm.ainvoke.return_value = high_score_response

        result = await reflection_skill.reflect_and_improve(
            query="What is photosynthesis?",
            answer="Photosynthesis is the process by which plants convert light energy into chemical energy.",
            contexts=sample_contexts,
        )

        # Should not iterate (already confident)
        assert result.iteration == 0
        assert result.score >= 0.85
        assert mock_llm.ainvoke.call_count == 1


class TestFormatContexts:
    """Test context formatting."""

    def test_format_contexts(self, reflection_skill, sample_contexts):
        """Test formatting contexts with numbered list."""
        formatted = reflection_skill._format_contexts(sample_contexts)
        assert "[1]" in formatted
        assert "[2]" in formatted
        assert "[3]" in formatted
        assert sample_contexts[0] in formatted
        assert sample_contexts[1] in formatted
        assert sample_contexts[2] in formatted

    def test_format_empty_contexts(self, reflection_skill):
        """Test formatting empty contexts."""
        formatted = reflection_skill._format_contexts([])
        assert formatted == ""

    def test_format_single_context(self, reflection_skill):
        """Test formatting single context."""
        contexts = ["Single context string."]
        formatted = reflection_skill._format_contexts(contexts)
        assert "[1]" in formatted
        assert "Single context string." in formatted
