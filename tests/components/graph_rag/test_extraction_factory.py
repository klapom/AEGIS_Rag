"""Unit Tests for Extraction Pipeline Factory - Sprint 14 Feature 14.2.

Tests the factory pattern for creating entity/relation extraction pipelines
with configurable backend selection (ThreePhase vs LightRAG Legacy).

Target Coverage: extraction_factory.py 0% → 80%

Author: Claude Code
Date: 2025-10-27
"""

from unittest.mock import Mock, patch

import pytest

from src.components.graph_rag.extraction_factory import (
    ExtractionPipeline,
    ExtractionPipelineFactory,
    create_extraction_pipeline_from_config,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_config_three_phase():
    """Mock config for three_phase/llm_extraction pipeline.

    Note: three_phase was renamed to llm_extraction in Sprint 20.
    The config includes lightrag_* attributes used by ExtractionService.
    """
    config = Mock()
    config.extraction_pipeline = "three_phase"
    config.enable_semantic_dedup = True
    config.extraction_max_retries = 3
    config.neo4j_uri = "bolt://localhost:7687"
    config.neo4j_user = "neo4j"
    config.neo4j_password = Mock()
    config.neo4j_password.get_secret_value.return_value = "testpassword"
    # Attributes needed by _create_llm_extraction (Sprint 20)
    config.lightrag_llm_model = "llama3.2:8b"
    config.ollama_base_url = "http://localhost:11434"
    config.lightrag_llm_max_tokens = 4000
    return config


@pytest.fixture
def mock_config_lightrag():
    """Mock config for lightrag_default pipeline."""
    config = Mock()
    config.extraction_pipeline = "lightrag_default"
    config.enable_legacy_extraction = True
    config.lightrag_llm_model = "llama3.2:3b"
    config.lightrag_embedding_model = "nomic-embed-text"
    config.lightrag_working_dir = "./data/lightrag"
    config.neo4j_uri = "bolt://localhost:7687"
    config.neo4j_user = "neo4j"
    config.neo4j_password = Mock()
    config.neo4j_password.get_secret_value.return_value = "testpassword"
    return config


@pytest.fixture
def mock_config_default():
    """Mock config with minimal attributes (defaults)."""
    config = Mock()
    # No extraction_pipeline attribute - should default to three_phase
    del config.extraction_pipeline
    config.neo4j_password = Mock()
    config.neo4j_password.get_secret_value.return_value = "testpassword"
    return config


# ============================================================================
# Test Factory Creation
# ============================================================================


@pytest.mark.unit
def test_factory_creates_three_phase_pipeline(mock_config_three_phase):
    """Test factory creates LLM extraction pipeline (ExtractionService) when configured.

    Note: ThreePhaseExtractor was refactored to ExtractionService in Sprint 20.
    The 'three_phase' config value now creates an LLMExtractionPipeline adapter.
    We patch _create_llm_extraction to avoid ExtractionService initialization.
    """
    mock_pipeline = Mock()
    with patch.object(
        ExtractionPipelineFactory, "_create_llm_extraction", return_value=mock_pipeline
    ) as mock_create:
        pipeline = ExtractionPipelineFactory.create(mock_config_three_phase)

        # Verify _create_llm_extraction was called
        mock_create.assert_called_once_with(mock_config_three_phase)
        # Pipeline should be the mocked pipeline
        assert pipeline is mock_pipeline


@pytest.mark.unit
def test_factory_creates_lightrag_pipeline_falls_back(mock_config_lightrag, caplog):
    """Test factory falls back to llm_extraction when lightrag_default is configured.

    Sprint 128: LightRAG removed, lightrag_default config now falls back to llm_extraction.
    """
    mock_pipeline = Mock(spec=ExtractionPipeline)
    with (
        patch.object(
            ExtractionPipelineFactory, "_create_llm_extraction", return_value=mock_pipeline
        ) as mock_create,
        caplog.at_level("WARNING"),
    ):
        pipeline = ExtractionPipelineFactory.create(mock_config_lightrag)

        # Should fall back to llm_extraction
        mock_create.assert_called_once()
        assert pipeline is mock_pipeline

        # Should log warning about fallback
        assert any("lightrag_default_deprecated" in record.message for record in caplog.records)


@pytest.mark.unit
def test_factory_defaults_to_three_phase(mock_config_default):
    """Test factory defaults to LLM extraction (three_phase) when no pipeline specified.

    Note: ThreePhaseExtractor was refactored to ExtractionService in Sprint 20.
    We patch _create_llm_extraction to avoid ExtractionService initialization.
    """
    mock_pipeline = Mock()
    with patch.object(
        ExtractionPipelineFactory, "_create_llm_extraction", return_value=mock_pipeline
    ) as mock_create:
        pipeline = ExtractionPipelineFactory.create(mock_config_default)

        # Should create LLM extraction pipeline by default
        mock_create.assert_called_once()
        assert pipeline is mock_pipeline


@pytest.mark.unit
def test_factory_raises_on_invalid_pipeline_type():
    """Test factory raises ValueError for unsupported pipeline type."""
    config = Mock()
    config.extraction_pipeline = "invalid_pipeline"

    with pytest.raises(ValueError, match="Unsupported extraction pipeline: invalid_pipeline"):
        ExtractionPipelineFactory.create(config)


@pytest.mark.unit
def test_factory_raises_with_helpful_error_message():
    """Test error message lists valid pipeline types."""
    config = Mock()
    config.extraction_pipeline = "unknown"

    with pytest.raises(ValueError) as exc_info:
        ExtractionPipelineFactory.create(config)

    error_msg = str(exc_info.value)
    # Sprint 128: only llm_extraction is valid
    assert "llm_extraction" in error_msg


# ============================================================================
# Test Configuration Reading
# ============================================================================


@pytest.mark.unit
def test_factory_reads_enable_semantic_dedup_true(mock_config_three_phase):
    """Test factory creates pipeline with semantic dedup config.

    Note: Sprint 20 refactored to ExtractionService - dedup is now handled
    differently. This test verifies the pipeline is created successfully.
    We patch _create_llm_extraction to avoid ExtractionService initialization.
    """
    mock_config_three_phase.enable_semantic_dedup = True

    mock_pipeline = Mock()
    with patch.object(
        ExtractionPipelineFactory, "_create_llm_extraction", return_value=mock_pipeline
    ):
        pipeline = ExtractionPipelineFactory.create(mock_config_three_phase)

        # Pipeline created successfully
        assert pipeline is mock_pipeline


@pytest.mark.unit
def test_factory_reads_enable_semantic_dedup_false():
    """Test factory creates pipeline with semantic dedup=False config.

    Note: Sprint 20 refactored to ExtractionService.
    We patch _create_llm_extraction to avoid ExtractionService initialization.
    """
    config = Mock()
    config.extraction_pipeline = "three_phase"
    config.enable_semantic_dedup = False

    mock_pipeline = Mock()
    with patch.object(
        ExtractionPipelineFactory, "_create_llm_extraction", return_value=mock_pipeline
    ):
        pipeline = ExtractionPipelineFactory.create(config)

        assert pipeline is mock_pipeline


@pytest.mark.unit
def test_factory_defaults_semantic_dedup_to_true():
    """Test factory creates pipeline when enable_semantic_dedup not in config.

    Note: Sprint 20 refactored to ExtractionService.
    We patch _create_llm_extraction to avoid ExtractionService initialization.
    """
    config = Mock()
    config.extraction_pipeline = "three_phase"
    del config.enable_semantic_dedup  # Simulate missing attribute

    mock_pipeline = Mock()
    with patch.object(
        ExtractionPipelineFactory, "_create_llm_extraction", return_value=mock_pipeline
    ):
        pipeline = ExtractionPipelineFactory.create(config)

        # Pipeline created successfully even without explicit dedup config
        assert pipeline is mock_pipeline


@pytest.mark.unit
def test_factory_reads_lightrag_model_config_falls_back(mock_config_lightrag):
    """Test factory falls back when lightrag config is provided.

    Sprint 128: LightRAG removed, config values no longer used.
    """
    mock_config_lightrag.lightrag_llm_model = "custom-model:7b"
    mock_config_lightrag.lightrag_embedding_model = "custom-embed"

    mock_pipeline = Mock(spec=ExtractionPipeline)
    with patch.object(
        ExtractionPipelineFactory, "_create_llm_extraction", return_value=mock_pipeline
    ):
        pipeline = ExtractionPipelineFactory.create(mock_config_lightrag)

        # Should create llm_extraction pipeline (lightrag config ignored)
        assert pipeline is mock_pipeline


# ============================================================================
# Test Pipeline Interface Compliance
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_three_phase_pipeline_implements_protocol(mock_config_three_phase):
    """Test that created three_phase pipeline implements ExtractionPipeline protocol.

    Note: ThreePhaseExtractor was refactored to ExtractionService in Sprint 20.
    We patch _create_llm_extraction to avoid ExtractionService initialization.
    """
    mock_pipeline = Mock(spec=ExtractionPipeline)
    with patch.object(
        ExtractionPipelineFactory, "_create_llm_extraction", return_value=mock_pipeline
    ):
        pipeline = ExtractionPipelineFactory.create(mock_config_three_phase)

        # Verify it has extract method
        assert hasattr(pipeline, "extract")
        assert callable(pipeline.extract)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_lightrag_pipeline_falls_back_to_llm_extraction(mock_config_lightrag):
    """Test that lightrag_default config falls back to llm_extraction pipeline.

    Sprint 128: LightRAG removed, lightrag_default now creates llm_extraction pipeline.
    """
    mock_pipeline = Mock(spec=ExtractionPipeline)
    with patch.object(
        ExtractionPipelineFactory, "_create_llm_extraction", return_value=mock_pipeline
    ):
        pipeline = ExtractionPipelineFactory.create(mock_config_lightrag)

        # Verify it has extract method
        assert hasattr(pipeline, "extract")
        assert callable(pipeline.extract)


# ============================================================================
# Test Convenience Function
# ============================================================================


@pytest.mark.unit
def test_convenience_function_with_config():
    """Test create_extraction_pipeline_from_config with provided config.

    Note: ThreePhaseExtractor was refactored to ExtractionService in Sprint 20.
    We patch _create_llm_extraction to avoid ExtractionService initialization.
    """
    config = Mock()
    config.extraction_pipeline = "three_phase"

    mock_pipeline = Mock(spec=ExtractionPipeline)
    with patch.object(
        ExtractionPipelineFactory, "_create_llm_extraction", return_value=mock_pipeline
    ):
        result = create_extraction_pipeline_from_config(config)

        # Should create pipeline using provided config
        assert result is mock_pipeline


@pytest.mark.unit
def test_convenience_function_without_config():
    """Test create_extraction_pipeline_from_config loads settings if no config.

    Note: ThreePhaseExtractor was refactored to ExtractionService in Sprint 20.
    We patch _create_llm_extraction to avoid ExtractionService initialization.
    """
    mock_pipeline = Mock(spec=ExtractionPipeline)
    with (
        patch("src.core.config.get_settings") as mock_settings,
        patch.object(
            ExtractionPipelineFactory, "_create_llm_extraction", return_value=mock_pipeline
        ),
    ):
        mock_config = Mock()
        mock_config.extraction_pipeline = "three_phase"
        mock_settings.return_value = mock_config

        result = create_extraction_pipeline_from_config()

        # Should call get_settings()
        mock_settings.assert_called_once()
        # Should create pipeline with loaded settings
        assert result is mock_pipeline


# ============================================================================
# Test Logging and Observability
# ============================================================================


@pytest.mark.unit
def test_factory_logs_pipeline_creation(mock_config_three_phase, caplog):
    """Test factory logs pipeline creation events.

    Note: ThreePhaseExtractor was refactored to ExtractionService in Sprint 20.
    We patch _create_llm_extraction to avoid ExtractionService initialization.
    """
    mock_pipeline = Mock(spec=ExtractionPipeline)
    with patch.object(
        ExtractionPipelineFactory, "_create_llm_extraction", return_value=mock_pipeline
    ):
        with caplog.at_level("INFO"):
            ExtractionPipelineFactory.create(mock_config_three_phase)

        # Check that creation was logged
        # Note: With the factory method patched, we still get the initial log message
        assert any(
            "extraction_factory_creating_pipeline" in record.message for record in caplog.records
        )


@pytest.mark.unit
def test_factory_logs_fallback_warning(mock_config_lightrag, caplog):
    """Test factory logs warning when falling back from lightrag_default.

    Sprint 128: LightRAG removed, factory should log fallback warning.
    """
    mock_pipeline = Mock(spec=ExtractionPipeline)
    with (
        patch.object(
            ExtractionPipelineFactory, "_create_llm_extraction", return_value=mock_pipeline
        ),
        caplog.at_level("WARNING"),
    ):
        ExtractionPipelineFactory.create(mock_config_lightrag)

        # Check that fallback warning was logged
        assert any("lightrag_default_deprecated" in record.message for record in caplog.records)


# ============================================================================
# Test Edge Cases and Error Handling
# ============================================================================


@pytest.mark.unit
def test_factory_handles_missing_config_attributes():
    """Test factory gracefully handles missing optional config attributes.

    Note: ThreePhaseExtractor was refactored to ExtractionService in Sprint 20.
    We patch _create_llm_extraction to avoid ExtractionService initialization.
    """
    config = Mock()
    config.extraction_pipeline = "three_phase"
    # Remove all optional attributes
    del config.enable_semantic_dedup
    del config.extraction_max_retries

    mock_pipeline = Mock(spec=ExtractionPipeline)
    with patch.object(
        ExtractionPipelineFactory, "_create_llm_extraction", return_value=mock_pipeline
    ):
        # Should not raise - uses getattr with defaults
        result = ExtractionPipelineFactory.create(config)

        assert result is mock_pipeline


@pytest.mark.unit
def test_factory_handles_none_pipeline_type():
    """Test factory handles None as pipeline type."""
    config = Mock()
    config.extraction_pipeline = None

    with pytest.raises(ValueError, match="Unsupported extraction pipeline: None"):
        ExtractionPipelineFactory.create(config)


@pytest.mark.unit
def test_factory_handles_empty_string_pipeline_type():
    """Test factory handles empty string as pipeline type."""
    config = Mock()
    config.extraction_pipeline = ""

    with pytest.raises(ValueError, match="Unsupported extraction pipeline"):
        ExtractionPipelineFactory.create(config)


@pytest.mark.unit
def test_factory_handles_case_sensitive_pipeline_names():
    """Test factory is case-sensitive for pipeline names."""
    config = Mock()
    config.extraction_pipeline = "Three_Phase"  # Wrong case

    with pytest.raises(ValueError, match="Unsupported extraction pipeline"):
        ExtractionPipelineFactory.create(config)


@pytest.mark.unit
def test_factory_preserves_config_object(mock_config_three_phase):
    """Test factory passes original config object to _create_llm_extraction.

    Note: ThreePhaseExtractor was refactored to ExtractionService in Sprint 20.
    We patch _create_llm_extraction to avoid ExtractionService initialization.
    """
    mock_pipeline = Mock(spec=ExtractionPipeline)
    with patch.object(
        ExtractionPipelineFactory, "_create_llm_extraction", return_value=mock_pipeline
    ) as mock_create:
        ExtractionPipelineFactory.create(mock_config_three_phase)

        # Verify _create_llm_extraction was called with config
        mock_create.assert_called_once_with(mock_config_three_phase)


# ============================================================================
# Test Integration with Real Components (Limited)
# ============================================================================


@pytest.mark.unit
def test_factory_integration_with_real_extraction_service_import():
    """Test factory can import real ExtractionService (no instantiation).

    Note: ThreePhaseExtractor was refactored to ExtractionService in Sprint 20.
    """
    # This test verifies imports work without creating actual instances
    from src.components.graph_rag.extraction_service import ExtractionService

    # Should be importable
    assert ExtractionService is not None


@pytest.mark.unit
def test_factory_integration_with_neo4j_client_import():
    """Test factory can import Neo4jClient (replacement for LightRAGWrapper).

    Sprint 128: LightRAG removed, tests now use Neo4jClient.
    """
    from src.components.graph_rag.neo4j_client import Neo4jClient

    # Should be importable
    assert Neo4jClient is not None
