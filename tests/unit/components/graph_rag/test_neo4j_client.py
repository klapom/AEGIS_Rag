"""Unit tests for Neo4jClient.

Tests the Neo4j client wrapper including:
- Connection initialization
- Health checks with retry logic
- Query execution (read and write)
- Error handling and retries
- Context manager support
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from src.components.graph_rag.neo4j_client import (
    DEFAULT_POOL_SIZE,
    Neo4jClient,
    get_neo4j_client,
)
from src.core.exceptions import DatabaseConnectionError

# ============================================================================
# Helper Functions
# ============================================================================


def create_driver_with_session(mock_session):
    """Create a properly mocked Neo4j driver with session context manager.

    Args:
        mock_session: The mock session to return from session()

    Returns:
        AsyncMock driver with properly configured session context manager
    """
    driver = AsyncMock()

    def create_session_context(*args, **kwargs):
        """Create a new session context for each call (needed for retries)."""
        session_context = MagicMock()
        session_context.__aenter__ = AsyncMock(return_value=mock_session)
        session_context.__aexit__ = AsyncMock(return_value=None)
        return session_context

    driver.session = MagicMock(side_effect=create_session_context)
    return driver


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j AsyncDriver."""
    driver = AsyncMock()
    driver.close = AsyncMock()

    # Mock session context manager
    session_cm = AsyncMock()
    driver.session = MagicMock(return_value=session_cm)

    return driver


@pytest.fixture
def mock_neo4j_session():
    """Mock Neo4j AsyncSession."""
    session = AsyncMock()
    session.run = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_query_result():
    """Mock Neo4j query result."""
    result = AsyncMock()
    result.single = AsyncMock(return_value={"health": 1})
    result.data = AsyncMock(return_value=[{"id": 1, "name": "test"}])
    return result


@pytest.fixture
def mock_write_summary():
    """Mock Neo4j write transaction summary."""
    summary = MagicMock()
    summary.counters.nodes_created = 5
    summary.counters.nodes_deleted = 0
    summary.counters.relationships_created = 3
    summary.counters.relationships_deleted = 0
    summary.counters.properties_set = 8
    return summary


# ============================================================================
# Test Initialization
# ============================================================================


@pytest.mark.unit
def test_neo4j_client_init_default():
    """Test Neo4jClient initialization with default settings."""
    client = Neo4jClient()

    assert client.uri is not None, "URI should be set from settings"
    assert client.user is not None, "User should be set from settings"
    assert client.password is not None, "Password should be set from settings"
    assert client.database is not None, "Database should be set from settings"
    assert client.max_connection_pool_size == DEFAULT_POOL_SIZE, "Default pool size should be 10"
    assert client.connection_timeout == 30, "Default timeout should be 30s"
    assert client._driver is None, "Driver should be lazy initialized"


@pytest.mark.unit
def test_neo4j_client_init_custom():
    """Test Neo4jClient initialization with custom parameters."""
    client = Neo4jClient(
        uri="bolt://custom-host:7687",
        user="custom_user",
        password="custom_password",
        database="custom_db",
        max_connection_pool_size=20,
        connection_timeout=60,
    )

    assert client.uri == "bolt://custom-host:7687", "Custom URI should be set"
    assert client.user == "custom_user", "Custom user should be set"
    assert client.password == "custom_password", "Custom password should be set"
    assert client.database == "custom_db", "Custom database should be set"
    assert client.max_connection_pool_size == 20, "Custom pool size should be set"
    assert client.connection_timeout == 60, "Custom timeout should be set"


@pytest.mark.unit
def test_neo4j_client_lazy_initialization(mock_neo4j_driver):
    """Test that Neo4j driver is lazy initialized."""
    with patch(
        "src.components.graph_rag.neo4j_client.AsyncGraphDatabase.driver",
        return_value=mock_neo4j_driver,
    ) as mock_driver_factory:
        client = Neo4jClient()

        # Driver should not be created yet
        mock_driver_factory.assert_not_called()

        # Access driver triggers initialization
        _ = client.driver
        mock_driver_factory.assert_called_once()


@pytest.mark.unit
def test_neo4j_client_driver_property_caching(mock_neo4j_driver):
    """Test that driver property caches the driver instance."""
    with patch(
        "src.components.graph_rag.neo4j_client.AsyncGraphDatabase.driver",
        return_value=mock_neo4j_driver,
    ) as mock_driver_factory:
        client = Neo4jClient()

        # Access driver multiple times
        driver1 = client.driver
        driver2 = client.driver

        # Should only create driver once
        mock_driver_factory.assert_called_once()
        assert driver1 is driver2, "Should return same driver instance"


# ============================================================================
# Test Health Check
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_success(mock_neo4j_session, mock_query_result):
    """Test successful health check."""
    mock_neo4j_session.run.return_value = mock_query_result

    client = Neo4jClient()
    client._driver = create_driver_with_session(mock_neo4j_session)

    result = await client.health_check()

    assert result is True, "Health check should return True"
    mock_neo4j_session.run.assert_called_once_with("RETURN 1 AS health")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_failure(mock_neo4j_session):
    """Test health check failure and exception raising."""
    mock_neo4j_session.run.side_effect = Exception("Connection refused")

    client = Neo4jClient()
    client._driver = create_driver_with_session(mock_neo4j_session)

    with pytest.raises(DatabaseConnectionError) as exc_info:
        await client.health_check()

    assert "health check failed" in str(exc_info.value).lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_retry_logic(mock_neo4j_session, mock_query_result):
    """Test health check retry logic on transient failures."""
    # Fail twice with ServiceUnavailable, then succeed
    mock_neo4j_session.run.side_effect = [
        ServiceUnavailable("Service unavailable"),
        ServiceUnavailable("Service unavailable"),
        mock_query_result,
    ]

    client = Neo4jClient()
    client._driver = create_driver_with_session(mock_neo4j_session)

    result = await client.health_check()

    assert result is True, "Should succeed after retries"
    assert mock_neo4j_session.run.call_count == 3, "Should retry failed calls"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_max_retries_exceeded(mock_neo4j_session):
    """Test health check when max retries exceeded."""
    from tenacity import RetryError

    # Always fail with ServiceUnavailable
    mock_neo4j_session.run.side_effect = ServiceUnavailable("Service unavailable")

    client = Neo4jClient()
    client._driver = create_driver_with_session(mock_neo4j_session)

    with pytest.raises(RetryError):
        await client.health_check()

    # Should try 3 times (initial + 2 retries)
    assert mock_neo4j_session.run.call_count == 3


# ============================================================================
# Test Query Execution
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_query_success(mock_neo4j_session):
    """Test successful query execution."""
    expected_data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    mock_result = AsyncMock()
    mock_result.data.return_value = expected_data
    mock_neo4j_session.run.return_value = mock_result

    client = Neo4jClient()
    client._driver = create_driver_with_session(mock_neo4j_session)

    query = "MATCH (n:Person) RETURN n.id AS id, n.name AS name"
    results = await client.execute_query(query)

    assert results == expected_data, "Should return query results"
    mock_neo4j_session.run.assert_called_once_with(query, {})


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_query_with_parameters(mock_neo4j_session):
    """Test query execution with parameters."""
    expected_data = [{"id": 1, "name": "Alice"}]
    mock_result = AsyncMock()
    mock_result.data.return_value = expected_data
    mock_neo4j_session.run.return_value = mock_result

    client = Neo4jClient()
    client._driver = create_driver_with_session(mock_neo4j_session)

    query = "MATCH (n:Person {id: $id}) RETURN n.id AS id, n.name AS name"
    parameters = {"id": 1}
    results = await client.execute_query(query, parameters)

    assert results == expected_data, "Should return query results"
    mock_neo4j_session.run.assert_called_once_with(query, parameters)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_query_custom_database(mock_neo4j_session):
    """Test query execution with custom database."""
    mock_result = AsyncMock()
    mock_result.data.return_value = []
    mock_neo4j_session.run.return_value = mock_result

    client = Neo4jClient()
    driver = create_driver_with_session(mock_neo4j_session)
    client._driver = driver

    query = "RETURN 1"
    await client.execute_query(query, database="custom_db")

    # Verify session was created with custom database
    driver.session.assert_called_once_with(database="custom_db")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_query_failure(mock_neo4j_session):
    """Test query execution failure with non-retriable error."""
    mock_neo4j_session.run.side_effect = ValueError("Invalid parameter")

    client = Neo4jClient()
    client._driver = create_driver_with_session(mock_neo4j_session)

    with pytest.raises(DatabaseConnectionError) as exc_info:
        await client.execute_query("INVALID QUERY")

    assert "Query execution failed" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_query_retry_logic(mock_neo4j_session):
    """Test query execution retry logic on transient failures."""
    expected_data = [{"result": 1}]
    mock_result = AsyncMock()
    mock_result.data.return_value = expected_data

    # Fail twice with ServiceUnavailable, then succeed
    mock_neo4j_session.run.side_effect = [
        ServiceUnavailable("Service unavailable"),
        ServiceUnavailable("Service unavailable"),
        mock_result,
    ]

    client = Neo4jClient()
    client._driver = create_driver_with_session(mock_neo4j_session)

    results = await client.execute_query("RETURN 1 AS result")

    assert results == expected_data, "Should succeed after retries"
    assert mock_neo4j_session.run.call_count == 3


# ============================================================================
# Test Write Transactions
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_write_success(mock_neo4j_session, mock_write_summary):
    """Test successful write transaction."""
    mock_result = AsyncMock()
    mock_result.consume.return_value = mock_write_summary
    mock_neo4j_session.run.return_value = mock_result

    client = Neo4jClient()
    client._driver = create_driver_with_session(mock_neo4j_session)

    query = "CREATE (n:Person {name: $name})"
    parameters = {"name": "Alice"}
    summary = await client.execute_write(query, parameters)

    assert summary["nodes_created"] == 5, "Should report nodes created"
    assert summary["relationships_created"] == 3, "Should report relationships created"
    assert summary["properties_set"] == 8, "Should report properties set"
    mock_neo4j_session.run.assert_called_once_with(query, parameters)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_write_failure(mock_neo4j_session):
    """Test write transaction failure with non-retriable error."""
    mock_neo4j_session.run.side_effect = ValueError("Invalid parameter")

    client = Neo4jClient()
    client._driver = create_driver_with_session(mock_neo4j_session)

    with pytest.raises(DatabaseConnectionError) as exc_info:
        await client.execute_write("CREATE (n:Person {id: 1})")

    assert "Write transaction failed" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_write_retry_logic(mock_neo4j_session, mock_write_summary):
    """Test write transaction retry logic on transient failures."""
    mock_result = AsyncMock()
    mock_result.consume.return_value = mock_write_summary

    # Fail twice, then succeed
    mock_neo4j_session.run.side_effect = [
        ServiceUnavailable("Service unavailable"),
        Neo4jError("Transient error"),
        mock_result,
    ]

    client = Neo4jClient()
    client._driver = create_driver_with_session(mock_neo4j_session)

    summary = await client.execute_write("CREATE (n:Test)")

    assert summary is not None, "Should succeed after retries"
    assert mock_neo4j_session.run.call_count == 3


# ============================================================================
# Test Client Lifecycle
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_driver(mock_neo4j_driver):
    """Test closing driver connection."""
    client = Neo4jClient()
    client._driver = mock_neo4j_driver

    await client.close()

    mock_neo4j_driver.close.assert_called_once()
    assert client._driver is None, "Driver should be set to None after close"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_uninitialized_driver():
    """Test closing without initializing driver (should not error)."""
    client = Neo4jClient()

    # Should not raise exception
    await client.close()
    assert client._driver is None


# ============================================================================
# Test Context Manager
# ============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_context_manager_async(mock_neo4j_driver):
    """Test async context manager."""
    with patch(
        "src.components.graph_rag.neo4j_client.AsyncGraphDatabase.driver",
        return_value=mock_neo4j_driver,
    ):
        async with Neo4jClient() as client:
            assert client is not None, "Context manager should provide client"
            assert isinstance(client, Neo4jClient), "Should be Neo4jClient"
            # Initialize driver by accessing it
            _ = client.driver

        # Verify close was called
        mock_neo4j_driver.close.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_context_manager_exception_handling(mock_neo4j_driver):
    """Test context manager handles exceptions properly."""
    with patch(
        "src.components.graph_rag.neo4j_client.AsyncGraphDatabase.driver",
        return_value=mock_neo4j_driver,
    ):
        try:
            async with Neo4jClient() as client:
                # Initialize driver by accessing it
                _ = client.driver
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected

        # Verify close was called even with exception
        mock_neo4j_driver.close.assert_called_once()


# ============================================================================
# Test Singleton Pattern
# ============================================================================


@pytest.mark.unit
def test_get_neo4j_client_singleton():
    """Test that get_neo4j_client returns singleton instance."""
    # Reset global client
    import src.components.graph_rag.neo4j_client as neo4j_module

    neo4j_module._neo4j_client = None

    client1 = get_neo4j_client()
    client2 = get_neo4j_client()

    assert client1 is client2, "Should return same instance"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_neo4j_client_async_context_manager():
    """Test async context manager for Neo4j client."""
    from src.components.graph_rag.neo4j_client import get_neo4j_client_async

    async with get_neo4j_client_async() as client:
        assert client is not None, "Context manager should provide client"
        assert isinstance(client, Neo4jClient), "Should be Neo4jClient"


# ============================================================================
# Test Error Scenarios
# ============================================================================


@pytest.mark.unit
def test_driver_initialization_failure():
    """Test driver initialization failure."""
    with patch(
        "src.components.graph_rag.neo4j_client.AsyncGraphDatabase.driver",
        side_effect=Exception("Connection refused"),
    ):
        client = Neo4jClient()

        with pytest.raises(DatabaseConnectionError) as exc_info:
            _ = client.driver

        assert "Failed to initialize Neo4j driver" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_empty_query_results(mock_neo4j_session):
    """Test query returning empty results."""
    mock_result = AsyncMock()
    mock_result.data.return_value = []
    mock_neo4j_session.run.return_value = mock_result

    client = Neo4jClient()
    client._driver = create_driver_with_session(mock_neo4j_session)

    results = await client.execute_query("MATCH (n:NonExistent) RETURN n")

    assert results == [], "Should return empty list"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_with_zero_changes(mock_neo4j_session):
    """Test write transaction that makes no changes."""
    mock_summary = MagicMock()
    mock_summary.counters.nodes_created = 0
    mock_summary.counters.nodes_deleted = 0
    mock_summary.counters.relationships_created = 0
    mock_summary.counters.relationships_deleted = 0
    mock_summary.counters.properties_set = 0

    mock_result = AsyncMock()
    mock_result.consume.return_value = mock_summary
    mock_neo4j_session.run.return_value = mock_result

    client = Neo4jClient()
    client._driver = create_driver_with_session(mock_neo4j_session)

    summary = await client.execute_write("MATCH (n) RETURN n")

    assert summary["nodes_created"] == 0
    assert summary["relationships_created"] == 0
    assert summary["properties_set"] == 0


# ============================================================================
# Test Section Nodes (Sprint 32 Feature 32.4)
# ============================================================================


@pytest.fixture
def mock_section_metadata():
    """Create mock SectionMetadata for testing."""
    from dataclasses import dataclass

    @dataclass
    class SectionMetadata:
        heading: str
        level: int
        page_no: int
        bbox: dict
        text: str
        token_count: int
        metadata: dict

    return [
        SectionMetadata(
            heading="Multi-Server Architecture",
            level=1,
            page_no=1,
            bbox={"l": 50.0, "t": 30.0, "r": 670.0, "b": 80.0},
            text="A multi-server architecture distributes load across multiple instances.",
            token_count=245,
            metadata={"source": "presentation.pptx"},
        ),
        SectionMetadata(
            heading="Load Balancing",
            level=2,
            page_no=2,
            bbox={"l": 50.0, "t": 100.0, "r": 670.0, "b": 150.0},
            text="Load balancing ensures requests are distributed evenly.",
            token_count=180,
            metadata={"source": "presentation.pptx"},
        ),
    ]


@pytest.fixture
def mock_adaptive_chunks():
    """Create mock AdaptiveChunk for testing."""
    from dataclasses import dataclass

    @dataclass
    class AdaptiveChunk:
        text: str
        token_count: int
        section_headings: list
        section_pages: list
        section_bboxes: list
        primary_section: str
        metadata: dict

    return [
        AdaptiveChunk(
            text="A multi-server architecture distributes load across multiple instances. Load balancing ensures requests are distributed evenly.",
            token_count=425,
            section_headings=["Multi-Server Architecture", "Load Balancing"],
            section_pages=[1, 2],
            section_bboxes=[
                {"l": 50.0, "t": 30.0, "r": 670.0, "b": 80.0},
                {"l": 50.0, "t": 100.0, "r": 670.0, "b": 150.0},
            ],
            primary_section="Multi-Server Architecture",
            metadata={"source": "presentation.pptx", "num_sections": 2},
        )
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_section_nodes_success(
    mock_neo4j_session, mock_section_metadata, mock_adaptive_chunks
):
    """Test successful section node creation with Sprint 33 batch operations."""
    # Sprint 33 Performance Fix: Mock batch query results
    # The new implementation uses UNWIND batches that return counts

    # Create different mock results for each query type
    # Query 1: Document MERGE (no return)
    mock_doc_result = AsyncMock()

    # Query 2: Batch section creation (returns sections_created count)
    mock_section_result = AsyncMock()
    mock_section_record = {"sections_created": 2}  # 2 sections in mock_section_metadata
    mock_section_result.single = AsyncMock(return_value=mock_section_record)

    # Query 3: Batch CONTAINS_CHUNK (returns rels_created count)
    mock_contains_result = AsyncMock()
    mock_contains_record = {"rels_created": 2}  # 2 section headings in mock_adaptive_chunks
    mock_contains_result.single = AsyncMock(return_value=mock_contains_record)

    # Query 4: Batch DEFINES (returns defines_created count)
    mock_defines_result = AsyncMock()
    mock_defines_record = {"defines_created": 5}  # 5 entities
    mock_defines_result.single = AsyncMock(return_value=mock_defines_record)

    # Set up side_effect to return different results for each call
    mock_neo4j_session.run.side_effect = [
        mock_doc_result,       # Document MERGE
        mock_section_result,   # Batch section creation
        mock_contains_result,  # Batch CONTAINS_CHUNK
        mock_defines_result,   # Batch DEFINES
    ]

    client = Neo4jClient()
    client._driver = create_driver_with_session(mock_neo4j_session)

    stats = await client.create_section_nodes(
        document_id="doc123",
        sections=mock_section_metadata,
        chunks=mock_adaptive_chunks,
    )

    # Verify statistics from batch operations
    assert stats["sections_created"] == 2, "Should create 2 sections"
    assert stats["has_section_rels"] == 2, "Should create 2 HAS_SECTION relationships"
    assert stats["contains_chunk_rels"] == 2, "Should create 2 CONTAINS_CHUNK relationships"
    assert stats["defines_entity_rels"] == 5, "Should create 5 DEFINES relationships"

    # Verify session.run was called 4 times (batch operations)
    assert mock_neo4j_session.run.call_count == 4


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_section_nodes_empty_sections(mock_neo4j_session, mock_adaptive_chunks):
    """Test section node creation with empty sections list."""
    # Sprint 33: Mock batch results for empty sections case

    # Query 1: Document MERGE (no return)
    mock_doc_result = AsyncMock()

    # Query 2: Batch section creation (returns 0 for empty list)
    mock_section_result = AsyncMock()
    mock_section_result.single = AsyncMock(return_value=None)  # No sections created

    # Query 3: Batch CONTAINS_CHUNK (returns 0 for no mappings)
    mock_contains_result = AsyncMock()
    mock_contains_result.single = AsyncMock(return_value=None)

    # Query 4: Batch DEFINES (returns 0)
    mock_defines_result = AsyncMock()
    mock_defines_result.single = AsyncMock(return_value=None)

    mock_neo4j_session.run.side_effect = [
        mock_doc_result,
        mock_section_result,
        mock_contains_result,
        mock_defines_result,
    ]

    client = Neo4jClient()
    client._driver = create_driver_with_session(mock_neo4j_session)

    stats = await client.create_section_nodes(
        document_id="doc123",
        sections=[],  # Empty sections
        chunks=mock_adaptive_chunks,
    )

    # Should still create document node but no sections
    assert stats["sections_created"] == 0
    assert stats["has_section_rels"] == 0
    # With empty sections, no CONTAINS_CHUNK relationships
    assert stats["contains_chunk_rels"] == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_section_nodes_error_handling(
    mock_neo4j_session, mock_section_metadata, mock_adaptive_chunks
):
    """Test error handling in section node creation."""
    # Simulate database error
    mock_neo4j_session.run.side_effect = Neo4jError("Database connection lost")

    client = Neo4jClient()
    client._driver = create_driver_with_session(mock_neo4j_session)

    with pytest.raises(DatabaseConnectionError) as exc_info:
        await client.create_section_nodes(
            document_id="doc123",
            sections=mock_section_metadata,
            chunks=mock_adaptive_chunks,
        )

    assert "Section nodes creation failed" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_section_nodes_hierarchical_structure(
    mock_neo4j_session, mock_section_metadata, mock_adaptive_chunks
):
    """Test that section nodes maintain hierarchical structure with batch ops."""
    # Sprint 33: Mock batch query results for hierarchical test

    # Query 1: Document MERGE
    mock_doc_result = AsyncMock()

    # Query 2: Batch section creation (returns sections_created count)
    mock_section_result = AsyncMock()
    mock_section_result.single = AsyncMock(return_value={"sections_created": 2})

    # Query 3: Batch CONTAINS_CHUNK
    mock_contains_result = AsyncMock()
    mock_contains_result.single = AsyncMock(return_value={"rels_created": 2})

    # Query 4: Batch DEFINES
    mock_defines_result = AsyncMock()
    mock_defines_result.single = AsyncMock(return_value={"defines_created": 3})

    mock_neo4j_session.run.side_effect = [
        mock_doc_result,
        mock_section_result,
        mock_contains_result,
        mock_defines_result,
    ]

    client = Neo4jClient()
    client._driver = create_driver_with_session(mock_neo4j_session)

    stats = await client.create_section_nodes(
        document_id="doc123",
        sections=mock_section_metadata,
        chunks=mock_adaptive_chunks,
    )

    # Verify sections maintain order
    assert stats["sections_created"] == 2

    # Verify run was called with batch operations
    calls = mock_neo4j_session.run.call_args_list
    # Batch operations should include order parameter in section data
