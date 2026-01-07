"""Domain-Specific Metrics for Knowledge Graph Quality Assessment.

Sprint 77 Feature 77.5 (TD-095): Entity Connectivity as Domain Training Metric

This module provides domain-specific benchmarks for evaluating knowledge graph
extraction quality, with focus on entity connectivity metrics.

Key Concept:
    Different domains have different expected connectivity patterns:
    - Factual domains (HotpotQA, Wikipedia): Sparse, atomic facts (0.3-0.8 relations/entity)
    - Narrative domains (Stories, articles): Dense, narrative-driven (1.5-3.0 relations/entity)
    - Technical domains (Documentation, manuals): Hierarchical, structured (2.0-4.0 relations/entity)
    - Academic domains (Research papers): Citation-heavy, interconnected (2.5-5.0 relations/entity)

Usage:
    >>> from src.components.domain_training.domain_metrics import evaluate_connectivity
    >>> metrics = await evaluate_connectivity(namespace_id="hotpotqa_large", domain_type="factual")
    >>> print(f"Connectivity: {metrics.relations_per_entity:.2f} (benchmark: {metrics.benchmark_range})")

Architecture:
    Domain Type → Benchmark Range → Neo4j Query → Connectivity Metric → Pass/Fail

Integration:
    - Domain Training UI: Display connectivity metrics with benchmark comparison
    - DSPy Optimization: Use connectivity as quality metric for prompt optimization
    - Grafana Dashboard: Track connectivity trends over time per domain
"""

from dataclasses import dataclass
from typing import Literal

import structlog

logger = structlog.get_logger(__name__)

# ============================================================================
# Domain-Specific Connectivity Benchmarks
# ============================================================================

DomainType = Literal["factual", "narrative", "technical", "academic"]


@dataclass
class ConnectivityBenchmark:
    """Connectivity benchmark for a domain type.

    Attributes:
        domain_type: Type of domain (factual, narrative, technical, academic)
        relations_per_entity_min: Minimum expected relations per entity
        relations_per_entity_max: Maximum expected relations per entity
        entities_per_community_min: Minimum expected entities per community
        entities_per_community_max: Maximum expected entities per community
        description: Human-readable description of graph characteristics
        examples: Example domains that fit this type
    """

    domain_type: DomainType
    relations_per_entity_min: float
    relations_per_entity_max: float
    entities_per_community_min: float
    entities_per_community_max: float
    description: str
    examples: list[str]


# Domain-specific connectivity benchmarks based on GraphRAG research and empirical data
DOMAIN_CONNECTIVITY_BENCHMARKS: dict[DomainType, ConnectivityBenchmark] = {
    "factual": ConnectivityBenchmark(
        domain_type="factual",
        relations_per_entity_min=0.3,
        relations_per_entity_max=0.8,
        entities_per_community_min=1.5,
        entities_per_community_max=3.0,
        description="Sparse, fact-oriented graphs with atomic statements",
        examples=["HotpotQA", "Wikipedia snippets", "Trivia datasets", "Q&A datasets"],
    ),
    "narrative": ConnectivityBenchmark(
        domain_type="narrative",
        relations_per_entity_min=1.5,
        relations_per_entity_max=3.0,
        entities_per_community_min=5.0,
        entities_per_community_max=10.0,
        description="Dense, narrative-driven graphs with story arcs and character relationships",
        examples=["News articles", "Blog posts", "Stories", "Case studies", "Reports"],
    ),
    "technical": ConnectivityBenchmark(
        domain_type="technical",
        relations_per_entity_min=2.0,
        relations_per_entity_max=4.0,
        entities_per_community_min=3.0,
        entities_per_community_max=8.0,
        description="Hierarchical, structured graphs with component relationships",
        examples=["Technical documentation", "API docs", "Manuals", "Specifications", "Tutorials"],
    ),
    "academic": ConnectivityBenchmark(
        domain_type="academic",
        relations_per_entity_min=2.5,
        relations_per_entity_max=5.0,
        entities_per_community_min=4.0,
        entities_per_community_max=12.0,
        description="Citation-heavy, interconnected graphs with research relationships",
        examples=["Research papers", "Theses", "Literature reviews", "Scientific articles"],
    ),
}


@dataclass
class ConnectivityMetrics:
    """Entity connectivity metrics for a namespace.

    Attributes:
        namespace_id: Namespace identifier
        domain_type: Detected or specified domain type
        total_entities: Total number of entities in namespace
        total_relationships: Total number of relationships
        total_communities: Total number of communities
        relations_per_entity: Actual relations per entity ratio
        entities_per_community: Actual entities per community ratio
        benchmark_min: Benchmark minimum for relations_per_entity
        benchmark_max: Benchmark maximum for relations_per_entity
        within_benchmark: Whether connectivity is within expected range
        benchmark_status: Status indicator (below, within, above)
        recommendations: List of recommendations if outside benchmark
    """

    namespace_id: str
    domain_type: DomainType
    total_entities: int
    total_relationships: int
    total_communities: int
    relations_per_entity: float
    entities_per_community: float
    benchmark_min: float
    benchmark_max: float
    within_benchmark: bool
    benchmark_status: Literal["below", "within", "above"]
    recommendations: list[str]


# ============================================================================
# Connectivity Evaluation
# ============================================================================


async def evaluate_connectivity(
    namespace_id: str,
    domain_type: DomainType = "factual",
) -> ConnectivityMetrics:
    """Evaluate entity connectivity for a namespace against domain benchmark.

    Sprint 77 Feature 77.5: Entity connectivity as quality metric for domain training.

    This function queries Neo4j for connectivity statistics and compares them
    to domain-specific benchmarks. It provides actionable recommendations for
    improving graph extraction quality.

    Args:
        namespace_id: Namespace to evaluate
        domain_type: Domain type for benchmark comparison (default: "factual")

    Returns:
        ConnectivityMetrics with actual values, benchmark comparison, and recommendations

    Example:
        >>> metrics = await evaluate_connectivity("hotpotqa_large", "factual")
        >>> print(f"Connectivity: {metrics.relations_per_entity:.2f}")
        >>> print(f"Benchmark: {metrics.benchmark_min}-{metrics.benchmark_max}")
        >>> print(f"Status: {metrics.benchmark_status}")
    """
    from src.components.graph_rag.neo4j_client import get_neo4j_client

    logger.info(
        "evaluating_connectivity",
        namespace_id=namespace_id,
        domain_type=domain_type,
    )

    neo4j = get_neo4j_client()

    # Get connectivity statistics from Neo4j
    cypher = """
    MATCH (e:base)
    WHERE e.namespace = $namespace
    WITH count(e) AS total_entities,
         count(DISTINCT e.community_id) AS total_communities

    MATCH (e1:base)-[r:RELATES_TO]->(e2:base)
    WHERE e1.namespace = $namespace
      AND e2.namespace = $namespace
    WITH total_entities, total_communities, count(r) AS total_relationships

    RETURN total_entities, total_relationships, total_communities
    """

    results = await neo4j.execute_read(cypher, {"namespace": namespace_id})

    if not results or not results[0]:
        logger.warning("no_entities_found_in_namespace", namespace_id=namespace_id)
        # Return empty metrics
        benchmark = DOMAIN_CONNECTIVITY_BENCHMARKS[domain_type]
        return ConnectivityMetrics(
            namespace_id=namespace_id,
            domain_type=domain_type,
            total_entities=0,
            total_relationships=0,
            total_communities=0,
            relations_per_entity=0.0,
            entities_per_community=0.0,
            benchmark_min=benchmark.relations_per_entity_min,
            benchmark_max=benchmark.relations_per_entity_max,
            within_benchmark=False,
            benchmark_status="below",
            recommendations=["No entities found - ingest documents first"],
        )

    record = results[0]
    total_entities = record.get("total_entities", 0)
    total_relationships = record.get("total_relationships", 0)
    total_communities = record.get("total_communities", 0)

    # Calculate connectivity ratios
    relations_per_entity = total_relationships / total_entities if total_entities > 0 else 0.0
    entities_per_community = total_entities / total_communities if total_communities > 0 else 0.0

    # Get benchmark
    benchmark = DOMAIN_CONNECTIVITY_BENCHMARKS[domain_type]

    # Determine status
    if relations_per_entity < benchmark.relations_per_entity_min:
        benchmark_status = "below"
        within_benchmark = False
    elif relations_per_entity > benchmark.relations_per_entity_max:
        benchmark_status = "above"
        within_benchmark = False
    else:
        benchmark_status = "within"
        within_benchmark = True

    # Generate recommendations
    recommendations = _generate_recommendations(
        relations_per_entity=relations_per_entity,
        entities_per_community=entities_per_community,
        benchmark=benchmark,
        benchmark_status=benchmark_status,
    )

    logger.info(
        "connectivity_evaluated",
        namespace_id=namespace_id,
        domain_type=domain_type,
        relations_per_entity=round(relations_per_entity, 2),
        benchmark_status=benchmark_status,
        within_benchmark=within_benchmark,
    )

    return ConnectivityMetrics(
        namespace_id=namespace_id,
        domain_type=domain_type,
        total_entities=total_entities,
        total_relationships=total_relationships,
        total_communities=total_communities,
        relations_per_entity=relations_per_entity,
        entities_per_community=entities_per_community,
        benchmark_min=benchmark.relations_per_entity_min,
        benchmark_max=benchmark.relations_per_entity_max,
        within_benchmark=within_benchmark,
        benchmark_status=benchmark_status,
        recommendations=recommendations,
    )


def _generate_recommendations(
    relations_per_entity: float,
    entities_per_community: float,
    benchmark: ConnectivityBenchmark,
    benchmark_status: Literal["below", "within", "above"],
) -> list[str]:
    """Generate actionable recommendations based on connectivity metrics.

    Args:
        relations_per_entity: Actual relations per entity
        entities_per_community: Actual entities per community
        benchmark: Domain-specific benchmark
        benchmark_status: Status indicator (below, within, above)

    Returns:
        List of human-readable recommendations
    """
    recommendations = []

    if benchmark_status == "below":
        # Too few relations (sparse graph)
        recommendations.extend(
            [
                f"⚠️  Entity connectivity is below benchmark ({relations_per_entity:.2f} < {benchmark.relations_per_entity_min})",
                "Consider improving ER-Extraction prompts to capture more relationships",
                "Use DSPy domain training to optimize extraction quality",
                "Review domain-specific examples to ensure relationship coverage",
                f"Target: {benchmark.relations_per_entity_min:.1f}-{benchmark.relations_per_entity_max:.1f} relations/entity",
            ]
        )
    elif benchmark_status == "above":
        # Too many relations (over-extraction)
        recommendations.extend(
            [
                f"⚠️  Entity connectivity is above benchmark ({relations_per_entity:.2f} > {benchmark.relations_per_entity_max})",
                "Graph may have over-extraction (spurious relationships)",
                "Consider tightening ER-Extraction prompts to reduce false positives",
                "Review extracted relationships for quality vs quantity",
                f"Target: {benchmark.relations_per_entity_min:.1f}-{benchmark.relations_per_entity_max:.1f} relations/entity",
            ]
        )
    else:
        # Within benchmark (good!)
        recommendations.extend(
            [
                f"✅ Entity connectivity within benchmark ({relations_per_entity:.2f} in [{benchmark.relations_per_entity_min}, {benchmark.relations_per_entity_max}])",
                f"Graph quality is appropriate for {benchmark.domain_type} domain",
                "Continue monitoring connectivity as more documents are ingested",
            ]
        )

    # Community size recommendations
    if entities_per_community < benchmark.entities_per_community_min:
        recommendations.append(
            f"ℹ️  Communities are small ({entities_per_community:.1f} entities/community < {benchmark.entities_per_community_min})"
        )
    elif entities_per_community > benchmark.entities_per_community_max:
        recommendations.append(
            f"ℹ️  Communities are large ({entities_per_community:.1f} entities/community > {benchmark.entities_per_community_max})"
        )

    return recommendations


# ============================================================================
# DSPy Integration (Future)
# ============================================================================


def get_connectivity_score(
    relations_per_entity: float,
    benchmark: ConnectivityBenchmark,
) -> float:
    """Calculate normalized connectivity score (0-1) for DSPy optimization.

    This score can be used as a DSPy metric to optimize ER-Extraction prompts
    for domain-specific connectivity targets.

    Args:
        relations_per_entity: Actual relations per entity
        benchmark: Domain-specific benchmark

    Returns:
        Normalized score (0-1), where 1.0 = perfect match to benchmark

    Example:
        >>> benchmark = DOMAIN_CONNECTIVITY_BENCHMARKS["factual"]
        >>> score = get_connectivity_score(0.45, benchmark)
        >>> print(f"Score: {score:.2f}")  # ~1.0 (within 0.3-0.8 range)
    """
    target_min = benchmark.relations_per_entity_min
    target_max = benchmark.relations_per_entity_max

    # If within range, score = 1.0 (perfect)
    if target_min <= relations_per_entity <= target_max:
        return 1.0

    # If below range, penalize linearly
    if relations_per_entity < target_min:
        return relations_per_entity / target_min

    # If above range, penalize inversely
    return target_max / relations_per_entity


# ============================================================================
# Singleton
# ============================================================================

# Export benchmarks for easy access
__all__ = [
    "DomainType",
    "ConnectivityBenchmark",
    "ConnectivityMetrics",
    "DOMAIN_CONNECTIVITY_BENCHMARKS",
    "evaluate_connectivity",
    "get_connectivity_score",
]
