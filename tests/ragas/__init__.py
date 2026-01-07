"""RAGAS Evaluation Tests for AEGIS RAG System.

Sprint 74 Feature 74.2: RAGAS Backend Integration

This package contains RAGAS evaluation tests that measure RAG system quality using:
- Context Precision: Relevance of retrieved contexts
- Context Recall: Coverage of ground truth information
- Faithfulness: Answer grounded in retrieved contexts (no hallucination)
- Answer Relevancy: Answer addresses the question

Test Organization:
- test_ragas_integration.py: Core RAGAS metric tests
- test_retrieval_comparison.py: Compare retrieval methods (BM25, Vector, Hybrid)
- data/: Test datasets (JSONL format)
- conftest.py: Pytest fixtures and configuration

Usage:
    # Run all RAGAS tests
    pytest tests/ragas/ -m ragas -v

    # Run only quick tests
    pytest tests/ragas/ -m ragas_quick -v

    # Run with coverage
    pytest tests/ragas/ --cov=src.evaluation --cov-report=html

Requirements:
    - Backend services running (Qdrant, Neo4j, Redis, Ollama)
    - Evaluation dependencies: poetry install --with evaluation
"""

__version__ = "1.0.0"
