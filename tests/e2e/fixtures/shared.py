"""Shared fixtures for E2E tests.

Provides reusable test data and utilities for E2E tests across all test modules:
- Sample documents (various domains)
- Test data generators
- Database client fixtures
- Configuration fixtures

These fixtures are used by conftest.py and automatically available to all tests.
"""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def sample_documents_dir(tmp_path_factory) -> Path:
    """Create a temporary directory with sample test documents."""
    doc_dir = tmp_path_factory.mktemp("sample_docs")

    # Create various sample documents
    samples = {
        "tech_doc.txt": """# Technical Document: Machine Learning Algorithms

## Introduction
Machine learning is a subset of artificial intelligence.

## Key Algorithms
1. Linear Regression - for continuous predictions
2. Logistic Regression - for binary classification
3. Decision Trees - for tree-based models
4. Neural Networks - for deep learning

## Applications
- Computer Vision
- Natural Language Processing
- Recommendation Systems
""",
        "medical_doc.txt": """# Medical Research: COVID-19 Treatment Advances

## Abstract
This paper discusses recent advances in COVID-19 treatment methodologies.

## Treatment Options
- Antiviral Therapy
- Immunotherapy
- Monoclonal Antibodies
- Combination Therapies

## Clinical Results
Results show 85% effectiveness with combination therapy approaches.
""",
        "legal_doc.txt": """# Legal Document: Contract Terms and Conditions

## Party A and Party B Agreement

### Definitions
- Service: The provision of consulting services
- Term: Initial term of 12 months from effective date
- Fees: As specified in Schedule A

### Terms
1. Service Provision
2. Payment Terms
3. Confidentiality
4. Termination Conditions
""",
    }

    for filename, content in samples.items():
        (doc_dir / filename).write_text(content, encoding="utf-8")

    return doc_dir


@pytest.fixture
def sample_document_tech(sample_documents_dir) -> Path:
    """Get path to sample technical document."""
    return sample_documents_dir / "tech_doc.txt"


@pytest.fixture
def sample_document_medical(sample_documents_dir) -> Path:
    """Get path to sample medical document."""
    return sample_documents_dir / "medical_doc.txt"


@pytest.fixture
def sample_document_legal(sample_documents_dir) -> Path:
    """Get path to sample legal document."""
    return sample_documents_dir / "legal_doc.txt"


@pytest.fixture(scope="session")
def test_config_dict() -> dict:
    """Provide test configuration dictionary."""
    return {
        "frontend_url": "http://localhost:5179",
        "api_url": "http://localhost:8000",
        "qdrant_url": "http://localhost:6333",
        "neo4j_uri": "bolt://localhost:7687",
        "redis_url": "redis://localhost:6379",
        "ollama_url": "http://localhost:11434",
        "test_timeout_ms": 30000,
        "network_idle_timeout_ms": 5000,
    }


@pytest.fixture
def admin_credentials() -> dict:
    """Provide test admin credentials."""
    return {
        "username": "admin",
        "password": "admin123",
    }
