"""Unit tests for DomainRepository.

Sprint 45 Feature 45.1: Domain Registry in Neo4j

Tests:
- Domain creation and retrieval
- Domain listing and deletion
- Domain prompt updates
- Semantic domain matching with embeddings
- Training log creation and updates
- Default domain initialization
- Error handling and validation
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.components.domain_training.domain_repository import (
    DEFAULT_DOMAIN_NAME,
    DomainRepository,
    get_domain_repository,
)
from src.core.exceptions import DatabaseConnectionError


# ============================================================================
# Helper Functions
# ============================================================================


def create_mock_neo4j_client(session_results=None):
    """Create a properly mocked Neo4j client.

    Args:
        session_results: Dictionary mapping query patterns to return values

    Returns:
        AsyncMock Neo4j client with configured responses
    """
    client = AsyncMock()
    client.execute_read = AsyncMock()
    client.execute_write = AsyncMock()

    if session_results:
        for pattern, result in session_results.items():
            if "MATCH" in pattern or "RETURN" in pattern:
                client.execute_read.return_value = result
            else:
                client.execute_write.return_value = result

    return client


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client for domain repository."""
    return create_mock_neo4j_client()


@pytest.fixture
def domain_repository(mock_neo4j_client):
    """Create DomainRepository with mocked Neo4j client."""
    with patch(
        "src.components.domain_training.domain_repository.get_neo4j_client",
        return_value=mock_neo4j_client,
    ):
        repo = DomainRepository()
        return repo


@pytest.fixture
def sample_domain_data():
    """Sample domain configuration data."""
    return {
        "id": "test-domain-id",
        "name": "tech_docs",
        "description": "Technical documentation domain",
        "entity_prompt": "Extract technical entities...",
        "relation_prompt": "Extract technical relations...",
        "entity_examples": '[{"text": "...", "entities": [...]}]',
        "relation_examples": '[{"text": "...", "relations": [...]}]',
        "llm_model": "qwen3:32b",
        "training_samples": 25,
        "training_metrics": '{"entity_f1": 0.85}',
        "status": "ready",
        "created_at": "2025-12-12T00:00:00",
        "updated_at": "2025-12-12T00:00:00",
        "trained_at": "2025-12-12T00:00:00",
    }


@pytest.fixture
def sample_embedding():
    """Sample BGE-M3 embedding (1024-dim)."""
    return [0.1] * 1024


# ============================================================================
# Test Initialization
# ============================================================================


@pytest.mark.asyncio
async def test_repository_initialization(domain_repository):
    """Test domain repository initializes correctly."""
    assert domain_repository is not None
    assert domain_repository.neo4j_client is not None


@pytest.mark.asyncio
async def test_initialize_creates_constraints(mock_neo4j_client):
    """Test initialize() creates unique constraint and default domain."""
    # Mock constraint creation and default domain check
    mock_neo4j_client.execute_write = AsyncMock()
    mock_neo4j_client.execute_read = AsyncMock(return_value=[])  # Domain not exists

    with patch(
        "src.components.domain_training.domain_repository.get_neo4j_client",
        return_value=mock_neo4j_client,
    ):
        repo = DomainRepository()
        await repo.initialize()

        # Verify constraint creation calls
        assert mock_neo4j_client.execute_write.call_count >= 2
        # Verify default domain check
        assert mock_neo4j_client.execute_read.called


@pytest.mark.asyncio
async def test_initialize_skips_default_if_exists(mock_neo4j_client):
    """Test initialize() skips creating default domain if it exists."""
    # Mock that default domain already exists
    mock_neo4j_client.execute_read = AsyncMock(return_value=[{"name": DEFAULT_DOMAIN_NAME}])
    mock_neo4j_client.execute_write = AsyncMock()

    with patch(
        "src.components.domain_training.domain_repository.get_neo4j_client",
        return_value=mock_neo4j_client,
    ):
        repo = DomainRepository()
        await repo.initialize()

        # Should not create new domain (only constraint creation calls)
        write_calls = [
            call
            for call in mock_neo4j_client.execute_write.call_args_list
            if "CREATE (d:Domain" not in str(call)
        ]
        assert len(write_calls) >= 2  # Constraint and index creation only


# ============================================================================
# Test Domain Creation
# ============================================================================


@pytest.mark.asyncio
async def test_create_domain_success(domain_repository, sample_embedding, mock_neo4j_client):
    """Test successful domain creation."""
    # Mock successful creation
    mock_neo4j_client.execute_write.return_value = [
        {"id": "test-id", "name": "tech_docs", "status": "pending"}
    ]

    result = await domain_repository.create_domain(
        name="tech_docs",
        description="Technical documentation",
        llm_model="qwen3:32b",
        description_embedding=sample_embedding,
    )

    assert result["name"] == "tech_docs"
    assert result["status"] == "pending"
    assert mock_neo4j_client.execute_write.called


@pytest.mark.asyncio
async def test_create_domain_invalid_name(domain_repository, sample_embedding):
    """Test domain creation with invalid name format."""
    with pytest.raises(ValueError, match="must be lowercase"):
        await domain_repository.create_domain(
            name="TechDocs",  # Invalid: uppercase
            description="Technical documentation",
            llm_model="qwen3:32b",
            description_embedding=sample_embedding,
        )


@pytest.mark.asyncio
async def test_create_domain_invalid_embedding_dimension(domain_repository):
    """Test domain creation with wrong embedding dimension."""
    with pytest.raises(ValueError, match="must be 1024-dim"):
        await domain_repository.create_domain(
            name="tech_docs",
            description="Technical documentation",
            llm_model="qwen3:32b",
            description_embedding=[0.1] * 512,  # Wrong dimension
        )


@pytest.mark.asyncio
async def test_create_domain_duplicate_name(domain_repository, sample_embedding, mock_neo4j_client):
    """Test domain creation with duplicate name."""
    # Mock constraint violation
    mock_neo4j_client.execute_write.side_effect = Exception(
        "ConstraintValidationFailed: Duplicate domain name"
    )

    with pytest.raises(ValueError, match="already exists"):
        await domain_repository.create_domain(
            name="tech_docs",
            description="Technical documentation",
            llm_model="qwen3:32b",
            description_embedding=sample_embedding,
        )


# ============================================================================
# Test Domain Retrieval
# ============================================================================


@pytest.mark.asyncio
async def test_get_domain_success(domain_repository, sample_domain_data, mock_neo4j_client):
    """Test successful domain retrieval."""
    mock_neo4j_client.execute_read.return_value = [sample_domain_data]

    result = await domain_repository.get_domain("tech_docs")

    assert result is not None
    assert result["name"] == "tech_docs"
    assert result["status"] == "ready"
    assert mock_neo4j_client.execute_read.called


@pytest.mark.asyncio
async def test_get_domain_not_found(domain_repository, mock_neo4j_client):
    """Test domain retrieval when domain doesn't exist."""
    mock_neo4j_client.execute_read.return_value = []

    result = await domain_repository.get_domain("nonexistent")

    assert result is None


@pytest.mark.asyncio
async def test_list_domains(domain_repository, sample_domain_data, mock_neo4j_client):
    """Test listing all domains."""
    mock_neo4j_client.execute_read.return_value = [
        sample_domain_data,
        {**sample_domain_data, "name": "legal_contracts"},
    ]

    result = await domain_repository.list_domains()

    assert len(result) == 2
    assert result[0]["name"] == "tech_docs"
    assert result[1]["name"] == "legal_contracts"


# ============================================================================
# Test Domain Updates
# ============================================================================


@pytest.mark.asyncio
async def test_update_domain_prompts(domain_repository, mock_neo4j_client):
    """Test updating domain with trained prompts."""
    mock_neo4j_client.execute_write.return_value = [{"name": "tech_docs"}]

    entity_examples = [{"text": "Sample text", "entities": ["Entity1"]}]
    relation_examples = [{"text": "Sample text", "relations": ["Rel1"]}]
    metrics = {"entity_f1": 0.85, "relation_f1": 0.80}

    result = await domain_repository.update_domain_prompts(
        name="tech_docs",
        entity_prompt="Extract entities...",
        relation_prompt="Extract relations...",
        entity_examples=entity_examples,
        relation_examples=relation_examples,
        metrics=metrics,
    )

    assert result is True
    assert mock_neo4j_client.execute_write.called


# ============================================================================
# Test Domain Matching
# ============================================================================


@pytest.mark.asyncio
async def test_find_best_matching_domain_success(
    domain_repository, sample_embedding, mock_neo4j_client
):
    """Test finding best matching domain with cosine similarity."""
    mock_neo4j_client.execute_read.return_value = [
        {
            "id": "test-id",
            "name": "tech_docs",
            "description": "Technical documentation",
            "entity_prompt": "Extract...",
            "relation_prompt": "Extract...",
            "llm_model": "qwen3:32b",
            "similarity": 0.85,
        }
    ]

    result = await domain_repository.find_best_matching_domain(sample_embedding, threshold=0.5)

    assert result is not None
    assert result["domain"]["name"] == "tech_docs"
    assert result["score"] == 0.85


@pytest.mark.asyncio
async def test_find_best_matching_domain_no_match(
    domain_repository, sample_embedding, mock_neo4j_client
):
    """Test finding domain when no match above threshold."""
    mock_neo4j_client.execute_read.return_value = []

    result = await domain_repository.find_best_matching_domain(sample_embedding, threshold=0.8)

    assert result is None


@pytest.mark.asyncio
async def test_find_best_matching_domain_invalid_embedding(domain_repository):
    """Test domain matching with invalid embedding dimension."""
    with pytest.raises(ValueError, match="must be 1024-dim"):
        await domain_repository.find_best_matching_domain([0.1] * 512)


# ============================================================================
# Test Domain Deletion
# ============================================================================


@pytest.mark.asyncio
async def test_delete_domain_success(domain_repository, mock_neo4j_client):
    """Test successful domain deletion."""
    mock_neo4j_client.execute_write.return_value = [{"deleted_count": 1}]

    result = await domain_repository.delete_domain("tech_docs")

    assert result is True
    assert mock_neo4j_client.execute_write.called


@pytest.mark.asyncio
async def test_delete_domain_not_found(domain_repository, mock_neo4j_client):
    """Test deleting non-existent domain."""
    mock_neo4j_client.execute_write.return_value = [{"deleted_count": 0}]

    result = await domain_repository.delete_domain("nonexistent")

    assert result is False


@pytest.mark.asyncio
async def test_delete_default_domain_raises_error(domain_repository):
    """Test that deleting default domain raises error."""
    with pytest.raises(ValueError, match="Cannot delete default domain"):
        await domain_repository.delete_domain(DEFAULT_DOMAIN_NAME)


# ============================================================================
# Test Training Logs
# ============================================================================


@pytest.mark.asyncio
async def test_create_training_log(domain_repository, mock_neo4j_client):
    """Test creating training log for domain."""
    mock_neo4j_client.execute_write.return_value = [
        {"id": "log-id", "status": "pending", "started_at": "2025-12-12T00:00:00"}
    ]

    result = await domain_repository.create_training_log("tech_docs")

    assert result["domain_name"] == "tech_docs"
    assert result["status"] == "pending"
    assert result["progress_percent"] == 0.0
    assert mock_neo4j_client.execute_write.called


@pytest.mark.asyncio
async def test_update_training_log(domain_repository, mock_neo4j_client):
    """Test updating training log progress."""
    mock_neo4j_client.execute_write.return_value = [{"id": "log-id"}]

    result = await domain_repository.update_training_log(
        log_id="log-id",
        progress=50.0,
        message="Training in progress...",
        status="running",
        metrics={"loss": 0.5},
    )

    assert result is True
    assert mock_neo4j_client.execute_write.called


@pytest.mark.asyncio
async def test_get_latest_training_log(domain_repository, mock_neo4j_client):
    """Test retrieving latest training log."""
    mock_neo4j_client.execute_read.return_value = [
        {
            "id": "log-id",
            "status": "completed",
            "progress_percent": 100.0,
            "current_step": "Training complete",
            "started_at": "2025-12-12T00:00:00",
            "completed_at": "2025-12-12T01:00:00",
            "log_messages": "[]",
            "metrics": '{"entity_f1": 0.85}',
            "error_message": None,
        }
    ]

    result = await domain_repository.get_latest_training_log("tech_docs")

    assert result is not None
    assert result["status"] == "completed"
    assert result["progress_percent"] == 100.0


@pytest.mark.asyncio
async def test_get_latest_training_log_none(domain_repository, mock_neo4j_client):
    """Test retrieving training log when none exists."""
    mock_neo4j_client.execute_read.return_value = []

    result = await domain_repository.get_latest_training_log("tech_docs")

    assert result is None


# ============================================================================
# Test Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_create_domain_database_error(domain_repository, sample_embedding, mock_neo4j_client):
    """Test domain creation with database error."""
    mock_neo4j_client.execute_write.side_effect = Exception("Database connection failed")

    with pytest.raises(DatabaseConnectionError):
        await domain_repository.create_domain(
            name="tech_docs",
            description="Technical documentation",
            llm_model="qwen3:32b",
            description_embedding=sample_embedding,
        )


@pytest.mark.asyncio
async def test_get_domain_database_error(domain_repository, mock_neo4j_client):
    """Test domain retrieval with database error."""
    mock_neo4j_client.execute_read.side_effect = Exception("Database connection failed")

    with pytest.raises(DatabaseConnectionError):
        await domain_repository.get_domain("tech_docs")


# ============================================================================
# Test Singleton Pattern
# ============================================================================


def test_get_domain_repository_singleton():
    """Test that get_domain_repository returns singleton instance."""
    with patch("src.components.domain_training.domain_repository.get_neo4j_client"):
        repo1 = get_domain_repository()
        repo2 = get_domain_repository()

        assert repo1 is repo2
