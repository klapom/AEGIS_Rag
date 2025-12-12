"""Domain Training Component for DSPy-based Knowledge Graph Optimization.

Sprint 45 - Feature 45.1: Domain Registry in Neo4j

This component manages domain-specific extraction prompts and training configurations
for optimizing knowledge graph construction using DSPy.

Key Features:
- Domain registry stored in Neo4j with semantic search
- Training log tracking with progress and metrics
- Default "general" domain fallback
- BGE-M3 embeddings for domain matching (1024-dim)

Architecture:
    DomainRepository → Neo4j (Domain + TrainingLog nodes)
    ├── Domain nodes with entity/relation prompts
    ├── Description embeddings for semantic matching
    └── Training logs with metrics and progress

Usage:
    >>> from src.components.domain_training import get_domain_repository
    >>> repo = get_domain_repository()
    >>> domain = await repo.get_domain("tech_docs")
    >>> if domain:
    ...     print(domain["entity_prompt"])
"""

from src.components.domain_training.domain_repository import (
    DomainRepository,
    get_domain_repository,
)

__all__ = [
    "DomainRepository",
    "get_domain_repository",
]
