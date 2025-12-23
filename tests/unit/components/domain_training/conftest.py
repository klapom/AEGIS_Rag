"""Pytest fixtures for domain training tests.

Sprint 45: Feature 45.1 - Domain Repository Fixtures
Shared fixtures for domain training module tests.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock

import pytest


@pytest.fixture
def mock_neo4j_client():
    """Mock Neo4j client for domain repository tests.

    Returns:
        AsyncMock: Mock async Neo4j client with query methods
    """
    client = AsyncMock()
    client.execute = AsyncMock()
    client.query = AsyncMock()
    client.run = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def sample_domain():
    """Sample domain for testing.

    Returns:
        dict: Sample domain data with required fields
    """
    return {
        "id": str(uuid.uuid4()),
        "name": "tech_docs",
        "description": "Technical documentation for software engineering",
        "description_embedding": [0.1] * 1024,
        "status": "ready",
        "created_at": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_domain_with_prompts(sample_domain):
    """Sample domain with extraction prompts (Feature 45.8).

    Returns:
        dict: Domain with custom entity and relationship extraction prompts
    """
    domain = sample_domain.copy()
    domain.update(
        {
            "entity_prompt": """Extract technical entities from {text}.
Focus on software concepts, technologies, frameworks, and platforms.
Return JSON array with name, type, description fields.""",
            "relationship_prompt": """Extract technical relationships from {text} given entities: {entities}.
Focus on dependencies, integrations, and technical relationships.
Return JSON array with source, target, type, description fields.""",
        }
    )
    return domain


@pytest.fixture
def sample_domain_general():
    """Sample general domain (uses generic prompts).

    Returns:
        dict: Domain named 'general' without custom prompts
    """
    return {
        "id": str(uuid.uuid4()),
        "name": "general",
        "description": "General purpose domain with generic extraction",
        "description_embedding": [0.2] * 1024,
        "status": "ready",
        "created_at": datetime.now().isoformat(),
    }


@pytest.fixture
def sample_training_log():
    """Sample training log for testing.

    Returns:
        dict: Training log data with progress and metrics
    """
    return {
        "id": str(uuid.uuid4()),
        "domain_id": str(uuid.uuid4()),
        "domain_name": "tech_docs",
        "training_type": "entity_extraction",
        "status": "in_progress",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "total_documents": 100,
        "processed_documents": 50,
        "success_count": 48,
        "error_count": 2,
        "metrics": {
            "precision": 0.92,
            "recall": 0.88,
            "f1_score": 0.90,
        },
    }


@pytest.fixture
def sample_training_log_completed(sample_training_log):
    """Sample completed training log.

    Returns:
        dict: Training log marked as completed with final metrics
    """
    log = sample_training_log.copy()
    log.update(
        {
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "processed_documents": 100,
            "success_count": 98,
            "error_count": 2,
            "metrics": {
                "precision": 0.94,
                "recall": 0.91,
                "f1_score": 0.925,
            },
        }
    )
    return log
