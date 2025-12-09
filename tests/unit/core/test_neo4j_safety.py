"""Unit tests for Neo4j Query Safety Layer.

Sprint 41 Feature 41.1: Namespace Isolation Layer

Tests the Neo4jQueryValidator and SecureNeo4jClient to ensure:
1. Queries without namespace filters are REJECTED
2. Queries with valid namespace filters PASS
3. Admin queries (CREATE INDEX, etc.) are allowed without namespace
4. The SecureNeo4jClient wrapper enforces validation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.neo4j_safety import (
    Neo4jQueryValidator,
    NamespaceSecurityError,
    SecureNeo4jClient,
    get_secure_neo4j_client,
)


class TestNeo4jQueryValidator:
    """Tests for Neo4jQueryValidator."""

    # =========================================================================
    # Test: Valid Queries (should PASS)
    # =========================================================================

    @pytest.mark.parametrize(
        "query",
        [
            # WHERE clause patterns
            "MATCH (e:Entity) WHERE e.namespace_id IN $allowed_namespaces RETURN e",
            "MATCH (e:Entity) WHERE e.namespace_id = $namespace_id RETURN e",
            "MATCH (n:base) WHERE n.namespace_id IN $ns RETURN n",
            # Property match patterns
            "MATCH (e:Entity {namespace_id: $ns}) RETURN e",
            "MATCH (e {namespace_id: $namespace_id}) RETURN e",
            # Complex queries with namespace
            """
            MATCH (e:base)
            WHERE e.namespace_id IN $allowed_namespaces
              AND e.entity_name CONTAINS 'test'
            RETURN e
            """,
            # SET patterns (for creating nodes)
            "CREATE (n:Entity) SET n.namespace_id = $namespace_id",
            "MERGE (n:chunk) SET n.namespace_id = $ns, n.text = $text",
            # Multiple conditions
            """
            WITH $query_terms AS terms
            MATCH (e:base)
            WHERE e.namespace_id IN $allowed_namespaces
              AND any(term IN terms WHERE toLower(e.entity_name) CONTAINS term)
            RETURN e
            """,
        ],
    )
    def test_valid_queries_pass(self, query: str):
        """Test that queries with namespace filters pass validation."""
        # Should not raise any exception
        Neo4jQueryValidator.validate(query)

    # =========================================================================
    # Test: Invalid Queries (should be REJECTED)
    # =========================================================================

    @pytest.mark.parametrize(
        "query",
        [
            # No namespace filter at all
            "MATCH (e:Entity) RETURN e",
            "MATCH (n:base)-[:RELATES_TO]->(m) RETURN n, m",
            # Only partial/incorrect patterns
            "MATCH (e:Entity) WHERE e.name = 'test' RETURN e",
            "MATCH (e:Entity {name: 'test'}) RETURN e",
            # Namespace mentioned but not as filter
            "MATCH (e:Entity) RETURN e.namespace_id",
            "MATCH (e:Entity) SET e.name = 'namespace_id' RETURN e",
        ],
    )
    def test_invalid_queries_rejected(self, query: str):
        """Test that queries without namespace filters are rejected."""
        with pytest.raises(NamespaceSecurityError) as exc_info:
            Neo4jQueryValidator.validate(query)

        assert "namespace_id filter" in str(exc_info.value.message)

    # =========================================================================
    # Test: Admin Queries (should be ALLOWED without namespace)
    # =========================================================================

    @pytest.mark.parametrize(
        "query",
        [
            # Index operations
            "CREATE INDEX idx_name IF NOT EXISTS FOR (n:Entity) ON (n.name)",
            "DROP INDEX idx_name IF EXISTS",
            "CREATE CONSTRAINT unique_id FOR (n:Entity) REQUIRE n.id IS UNIQUE",
            # Show operations
            "SHOW INDEXES",
            "SHOW CONSTRAINTS",
            "SHOW DATABASES",
            # DB procedures
            "CALL db.labels()",
            "CALL db.relationshipTypes()",
            "CALL apoc.meta.data()",
            # Health check
            "RETURN 1 AS health",
        ],
    )
    def test_admin_queries_allowed(self, query: str):
        """Test that admin queries are allowed without namespace filter."""
        # Should not raise any exception
        Neo4jQueryValidator.validate(query)

    # =========================================================================
    # Test: Skip Validation Flag
    # =========================================================================

    def test_skip_validation_allows_any_query(self):
        """Test that skip_validation=True allows any query."""
        invalid_query = "MATCH (e:Entity) RETURN e"  # Would normally be rejected

        # Should not raise when skip_validation=True
        Neo4jQueryValidator.validate(invalid_query, skip_validation=True)

    # =========================================================================
    # Test: Write Query Detection
    # =========================================================================

    @pytest.mark.parametrize(
        "query,expected",
        [
            ("MATCH (n) RETURN n", False),
            ("CREATE (n:Entity {name: 'test'})", True),
            ("MERGE (n:Entity {id: 1})", True),
            ("MATCH (n) DELETE n", True),
            ("MATCH (n) SET n.name = 'test'", True),
            ("MATCH (n) REMOVE n.name", True),
            ("MATCH (n) RETURN n LIMIT 10", False),
        ],
    )
    def test_is_write_query(self, query: str, expected: bool):
        """Test write query detection."""
        result = Neo4jQueryValidator.is_write_query(query)
        assert result == expected


class TestSecureNeo4jClient:
    """Tests for SecureNeo4jClient wrapper."""

    @pytest.fixture
    def mock_neo4j_client(self):
        """Create a mock Neo4j client."""
        client = MagicMock()
        client.execute_query = AsyncMock(return_value=[{"result": "test"}])
        client.execute_read = AsyncMock(return_value=[{"result": "test"}])
        client.execute_write = AsyncMock(return_value={"nodes_created": 1})
        client.health_check = AsyncMock(return_value=True)
        client.close = AsyncMock()
        return client

    @pytest.fixture
    def secure_client(self, mock_neo4j_client):
        """Create SecureNeo4jClient with mocked underlying client."""
        return SecureNeo4jClient(mock_neo4j_client, validate_queries=True)

    # =========================================================================
    # Test: Query Execution with Validation
    # =========================================================================

    @pytest.mark.asyncio
    async def test_execute_query_valid(self, secure_client, mock_neo4j_client):
        """Test that valid queries execute successfully."""
        query = "MATCH (e:Entity) WHERE e.namespace_id IN $ns RETURN e"

        result = await secure_client.execute_query(query, {"ns": ["general"]})

        assert result == [{"result": "test"}]
        mock_neo4j_client.execute_query.assert_called_once_with(query, {"ns": ["general"]}, None)

    @pytest.mark.asyncio
    async def test_execute_query_invalid_rejected(self, secure_client):
        """Test that invalid queries are rejected before execution."""
        query = "MATCH (e:Entity) RETURN e"  # No namespace filter

        with pytest.raises(NamespaceSecurityError):
            await secure_client.execute_query(query)

    @pytest.mark.asyncio
    async def test_execute_read_valid(self, secure_client, mock_neo4j_client):
        """Test execute_read with valid query."""
        query = "MATCH (e:Entity) WHERE e.namespace_id = $ns RETURN e"

        result = await secure_client.execute_read(query, {"ns": "general"})

        assert result == [{"result": "test"}]
        mock_neo4j_client.execute_read.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_write_valid(self, secure_client, mock_neo4j_client):
        """Test execute_write with valid query."""
        query = "CREATE (n:Entity) SET n.namespace_id = $ns"

        result = await secure_client.execute_write(query, {"ns": "general"})

        assert result == {"nodes_created": 1}
        mock_neo4j_client.execute_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_write_invalid_rejected(self, secure_client):
        """Test that invalid write queries are rejected."""
        query = "CREATE (n:Entity {name: 'test'})"  # No namespace

        with pytest.raises(NamespaceSecurityError):
            await secure_client.execute_write(query)

    # =========================================================================
    # Test: Skip Validation
    # =========================================================================

    @pytest.mark.asyncio
    async def test_skip_validation_flag(self, secure_client, mock_neo4j_client):
        """Test that skip_validation allows any query."""
        query = "MATCH (e:Entity) RETURN e"  # Would normally be rejected

        result = await secure_client.execute_query(query, skip_validation=True)

        assert result == [{"result": "test"}]
        mock_neo4j_client.execute_query.assert_called_once()

    # =========================================================================
    # Test: Validation Disabled
    # =========================================================================

    @pytest.mark.asyncio
    async def test_validation_disabled(self, mock_neo4j_client):
        """Test client with validation disabled."""
        client = SecureNeo4jClient(mock_neo4j_client, validate_queries=False)
        query = "MATCH (e:Entity) RETURN e"  # Would be rejected with validation

        result = await client.execute_query(query)

        assert result == [{"result": "test"}]

    # =========================================================================
    # Test: Health Check and Close
    # =========================================================================

    @pytest.mark.asyncio
    async def test_health_check(self, secure_client, mock_neo4j_client):
        """Test health check passes through without validation."""
        result = await secure_client.health_check()

        assert result is True
        mock_neo4j_client.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, secure_client, mock_neo4j_client):
        """Test close passes through to underlying client."""
        await secure_client.close()

        mock_neo4j_client.close.assert_called_once()


class TestGetSecureNeo4jClient:
    """Tests for get_secure_neo4j_client factory function."""

    @patch("src.components.graph_rag.neo4j_client.get_neo4j_client")
    def test_creates_secure_client(self, mock_get_client):
        """Test that factory creates SecureNeo4jClient."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        secure_client = get_secure_neo4j_client()

        assert isinstance(secure_client, SecureNeo4jClient)
        mock_get_client.assert_called_once()

    @patch("src.components.graph_rag.neo4j_client.get_neo4j_client")
    def test_validation_flag_passed(self, mock_get_client):
        """Test that validate_queries flag is passed correctly."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        secure_client = get_secure_neo4j_client(validate_queries=False)

        assert secure_client._validate_queries is False


class TestNamespaceSecurityError:
    """Tests for NamespaceSecurityError exception."""

    def test_error_message(self):
        """Test error contains query preview and reason."""
        query = "MATCH (e:Entity) RETURN e"
        reason = "Missing namespace filter"

        error = NamespaceSecurityError(query=query, reason=reason)

        assert "namespace security violation" in error.message.lower()
        assert error.status_code == 403
        assert error.details["reason"] == reason
        assert query[:200] in error.details["query_preview"]

    def test_long_query_truncated(self):
        """Test that long queries are truncated in error details."""
        long_query = "MATCH (e:Entity) " + "WHERE e.name = 'x' " * 50 + "RETURN e"
        reason = "Test"

        error = NamespaceSecurityError(query=long_query, reason=reason)

        # Query preview should be truncated to 200 chars
        assert len(error.details["query_preview"]) <= 200
