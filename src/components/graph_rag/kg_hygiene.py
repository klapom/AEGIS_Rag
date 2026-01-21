"""Knowledge Graph Hygiene and Deduplication Service.

Sprint 85 Feature 85.5: KG Hygiene & Deduplication (Best Practice)

This module implements KG hygiene following LlamaIndex best practices:
- Entity deduplication using embedding similarity
- Self-loop detection and removal
- Orphan relation cleanup
- Relation validation (evidence present, valid types)

Best Practice Reference:
"Entity deduplication uses a combination of text embedding similarity and
word distance to find potential duplicates. This involves defining a vector
index on entities in the graph using Cypher queries with cosine similarity."
— LlamaIndex Blog: Customizing Property Graph Index
"""

from dataclasses import dataclass
from typing import Any

import structlog

from src.components.graph_rag.neo4j_client import get_neo4j_client
from src.core.models import GraphRelationship

logger = structlog.get_logger(__name__)


# Valid relation types (extend as needed)
VALID_RELATION_TYPES = {
    # Standard types
    "RELATES_TO",
    "RELATED_TO",
    "ASSOCIATED_WITH",
    # Technical types
    "USES",
    "USED_BY",
    "DEPENDS_ON",
    "IMPLEMENTS",
    "EXTENDS",
    "CONTAINS",
    "PART_OF",
    "INSTANCE_OF",
    "TYPE_OF",
    # Causal types
    "CAUSES",
    "LEADS_TO",
    "ENABLES",
    "REQUIRES",
    "FOLLOWS",
    "PRECEDES",
    # Organizational types
    "OWNS",
    "MANAGES",
    "EMPLOYS",
    "FOUNDED_BY",
    "LOCATED_IN",
    # Semantic types
    "SIMILAR_TO",
    "OPPOSITE_OF",
    "SYNONYM_OF",
    # Action types
    "CREATES",
    "MODIFIES",
    "DELETES",
    "READS",
    "WRITES",
}


@dataclass
class HygieneViolation:
    """Represents a hygiene rule violation.

    Attributes:
        rule: Name of the violated rule
        entity_or_relation_id: ID of the violating entity/relation
        description: Human-readable description
        severity: "warning" or "error"
        auto_fixable: Whether this can be automatically fixed
    """

    rule: str
    entity_or_relation_id: str
    description: str
    severity: str = "warning"
    auto_fixable: bool = False


@dataclass
class HygieneReport:
    """Report of KG hygiene analysis.

    Attributes:
        total_entities: Total entities in graph
        total_relations: Total relations in graph
        self_loops: Number of self-loop relations (A->A)
        missing_evidence: Relations without evidence_span
        invalid_types: Relations with unknown types
        orphan_relations: Relations where source or target doesn't exist
        duplicate_entities: Potential duplicate entity pairs
        violations: List of specific violations
    """

    total_entities: int = 0
    total_relations: int = 0
    self_loops: int = 0
    missing_evidence: int = 0
    invalid_types: int = 0
    orphan_relations: int = 0
    duplicate_entities: int = 0
    violations: list[HygieneViolation] = None

    def __post_init__(self) -> None:
        if self.violations is None:
            self.violations = []

    @property
    def is_healthy(self) -> bool:
        """Check if graph passes hygiene checks."""
        return self.self_loops == 0 and self.orphan_relations == 0 and self.invalid_types == 0

    @property
    def health_score(self) -> float:
        """Calculate health score (0-100)."""
        if self.total_relations == 0:
            return 100.0

        issues = self.self_loops + self.orphan_relations + self.invalid_types
        return max(0, 100 - (issues / self.total_relations * 100))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/API."""
        return {
            "total_entities": self.total_entities,
            "total_relations": self.total_relations,
            "self_loops": self.self_loops,
            "missing_evidence": self.missing_evidence,
            "invalid_types": self.invalid_types,
            "orphan_relations": self.orphan_relations,
            "duplicate_entities": self.duplicate_entities,
            "is_healthy": self.is_healthy,
            "health_score": round(self.health_score, 1),
            "violation_count": len(self.violations),
        }


class KGHygieneService:
    """Knowledge Graph hygiene and deduplication service.

    Provides methods for:
    - Detecting duplicate entities using embeddings
    - Validating relations against hygiene rules
    - Merging duplicate entities (APOC)
    - Generating hygiene reports
    """

    def __init__(self) -> None:
        """Initialize KG hygiene service."""
        self.neo4j_client = get_neo4j_client()
        logger.info("kg_hygiene_service_initialized")

    async def analyze_graph(self, namespace_id: str | None = None) -> HygieneReport:
        """Analyze graph for hygiene issues.

        Args:
            namespace_id: Optional namespace to filter analysis

        Returns:
            HygieneReport with analysis results
        """
        logger.info("analyzing_graph_hygiene", namespace_id=namespace_id)

        report = HygieneReport()
        violations: list[HygieneViolation] = []

        # Build namespace filter
        namespace_filter = ""
        params: dict[str, Any] = {}
        if namespace_id:
            namespace_filter = " AND e.namespace_id = $namespace_id"
            params["namespace_id"] = namespace_id

        try:
            # Count total entities
            entity_count = await self.neo4j_client.execute_read(
                f"""
                MATCH (e:base)
                WHERE e.entity_name IS NOT NULL {namespace_filter}
                RETURN count(e) AS count
                """,
                params,
            )
            report.total_entities = entity_count[0]["count"] if entity_count else 0

            # Count total relations
            relation_count = await self.neo4j_client.execute_read(
                f"""
                MATCH (s:base)-[r:RELATES_TO]->(t:base)
                WHERE s.entity_name IS NOT NULL AND t.entity_name IS NOT NULL
                {namespace_filter.replace('e.', 's.')}
                RETURN count(r) AS count
                """,
                params,
            )
            report.total_relations = relation_count[0]["count"] if relation_count else 0

            # Detect self-loops (A -> A)
            self_loops = await self.neo4j_client.execute_read(
                f"""
                MATCH (e:base)-[r:RELATES_TO]->(e)
                WHERE e.entity_name IS NOT NULL {namespace_filter}
                RETURN e.entity_name AS entity, count(r) AS loop_count
                """,
                params,
            )
            for loop in self_loops:
                report.self_loops += loop["loop_count"]
                violations.append(
                    HygieneViolation(
                        rule="no_self_loops",
                        entity_or_relation_id=loop["entity"],
                        description=f"Entity '{loop['entity']}' has {loop['loop_count']} self-loop relation(s)",
                        severity="error",
                        auto_fixable=True,
                    )
                )

            # Detect relations without evidence
            no_evidence = await self.neo4j_client.execute_read(
                f"""
                MATCH (s:base)-[r:RELATES_TO]->(t:base)
                WHERE (r.evidence_span IS NULL OR r.evidence_span = "")
                {namespace_filter.replace('e.', 's.')}
                RETURN count(r) AS count
                """,
                params,
            )
            report.missing_evidence = no_evidence[0]["count"] if no_evidence else 0

            # Detect invalid relation types
            invalid_types = await self.neo4j_client.execute_read(
                f"""
                MATCH (s:base)-[r:RELATES_TO]->(t:base)
                WHERE r.relation_type IS NOT NULL
                {namespace_filter.replace('e.', 's.')}
                RETURN DISTINCT r.relation_type AS rel_type, count(r) AS count
                """,
                params,
            )
            for rt in invalid_types:
                if rt["rel_type"] and rt["rel_type"] not in VALID_RELATION_TYPES:
                    report.invalid_types += rt["count"]
                    violations.append(
                        HygieneViolation(
                            rule="valid_relation_type",
                            entity_or_relation_id=rt["rel_type"],
                            description=f"Unknown relation type '{rt['rel_type']}' ({rt['count']} occurrences)",
                            severity="warning",
                            auto_fixable=False,
                        )
                    )

            report.violations = violations

            logger.info(
                "graph_hygiene_analysis_complete",
                namespace_id=namespace_id,
                **report.to_dict(),
            )

            return report

        except Exception as e:
            logger.error(
                "graph_hygiene_analysis_failed",
                namespace_id=namespace_id,
                error=str(e),
            )
            raise

    async def find_duplicate_entities(
        self,
        similarity_threshold: float = 0.90,
        namespace_id: str | None = None,
        limit: int = 100,
    ) -> list[tuple[str, str, float]]:
        """Find potential duplicate entities using embedding similarity.

        Note: Requires vector index on entities. If not available, falls back to name similarity.

        Args:
            similarity_threshold: Minimum cosine similarity
            namespace_id: Optional namespace filter
            limit: Maximum duplicates to return

        Returns:
            List of (entity1_name, entity2_name, similarity) tuples
        """
        logger.info(
            "finding_duplicate_entities",
            similarity_threshold=similarity_threshold,
            namespace_id=namespace_id,
        )

        # Build namespace filter
        params: dict[str, Any] = {
            "threshold": similarity_threshold,
            "limit": limit,
        }

        namespace_filter = ""
        if namespace_id:
            namespace_filter = "WHERE e1.namespace_id = $namespace_id"
            params["namespace_id"] = namespace_id

        try:
            # Try vector-based similarity first (requires vector index)
            try:
                results = await self.neo4j_client.execute_read(
                    f"""
                    MATCH (e1:base)
                    {namespace_filter}
                    WITH e1
                    WHERE e1.embedding IS NOT NULL
                    CALL db.index.vector.queryNodes('entity_embedding_index', 10, e1.embedding)
                    YIELD node AS e2, score
                    WHERE e1 <> e2 AND score >= $threshold
                    RETURN e1.entity_name AS entity1,
                           e2.entity_name AS entity2,
                           score AS similarity
                    ORDER BY score DESC
                    LIMIT $limit
                    """,
                    params,
                )
                logger.info("duplicate_detection_used_vector_index", count=len(results))
                return [(r["entity1"], r["entity2"], r["similarity"]) for r in results]

            except Exception as vector_error:
                logger.warning(
                    "vector_index_not_available_using_name_similarity",
                    error=str(vector_error),
                )

            # Fallback: Name-based similarity (simple substring/prefix matching)
            results = await self.neo4j_client.execute_read(
                f"""
                MATCH (e1:base), (e2:base)
                {namespace_filter.replace('e1.', 'e1.')} {"AND" if namespace_filter else "WHERE"}
                e1 <> e2
                AND toLower(e1.entity_name) < toLower(e2.entity_name)
                AND (
                    toLower(e1.entity_name) CONTAINS toLower(e2.entity_name)
                    OR toLower(e2.entity_name) CONTAINS toLower(e1.entity_name)
                    OR toLower(e1.entity_name) = toLower(e2.entity_name)
                )
                RETURN e1.entity_name AS entity1,
                       e2.entity_name AS entity2,
                       1.0 AS similarity
                ORDER BY entity1
                LIMIT $limit
                """,
                params,
            )
            logger.info("duplicate_detection_used_name_similarity", count=len(results))
            return [(r["entity1"], r["entity2"], r["similarity"]) for r in results]

        except Exception as e:
            logger.error("find_duplicate_entities_failed", error=str(e))
            return []

    async def remove_self_loops(self, namespace_id: str | None = None) -> int:
        """Remove self-loop relations (entity -> same entity).

        Args:
            namespace_id: Optional namespace filter

        Returns:
            Number of self-loops removed
        """
        logger.info("removing_self_loops", namespace_id=namespace_id)

        params: dict[str, Any] = {}
        namespace_filter = ""
        if namespace_id:
            namespace_filter = "AND e.namespace_id = $namespace_id"
            params["namespace_id"] = namespace_id

        try:
            result = await self.neo4j_client.execute_write(
                f"""
                MATCH (e:base)-[r:RELATES_TO]->(e)
                WHERE e.entity_name IS NOT NULL {namespace_filter}
                DELETE r
                RETURN count(r) AS deleted
                """,
                params,
            )
            deleted = result[0]["deleted"] if result else 0
            logger.info("self_loops_removed", count=deleted, namespace_id=namespace_id)
            return deleted

        except Exception as e:
            logger.error("remove_self_loops_failed", error=str(e))
            return 0

    async def merge_duplicate_entities(
        self,
        entity1_name: str,
        entity2_name: str,
        keep: str = "entity1",
    ) -> bool:
        """Merge two duplicate entities, preserving all relationships.

        Note: Requires APOC plugin for Neo4j.

        Args:
            entity1_name: First entity name
            entity2_name: Second entity name
            keep: Which entity to keep ("entity1" or "entity2")

        Returns:
            True if merge successful
        """
        logger.info(
            "merging_duplicate_entities",
            entity1=entity1_name,
            entity2=entity2_name,
            keep=keep,
        )

        keep_name = entity1_name if keep == "entity1" else entity2_name
        remove_name = entity2_name if keep == "entity1" else entity1_name

        try:
            # First, try APOC merge (preferred)
            try:
                await self.neo4j_client.execute_write(
                    """
                    MATCH (keep:base {entity_name: $keep_name})
                    MATCH (remove:base {entity_name: $remove_name})
                    CALL apoc.refactor.mergeNodes([keep, remove], {
                        properties: "combine",
                        mergeRels: true
                    })
                    YIELD node
                    RETURN node.entity_name AS merged_name
                    """,
                    {"keep_name": keep_name, "remove_name": remove_name},
                )
                logger.info("entities_merged_with_apoc", keep=keep_name, removed=remove_name)
                return True

            except Exception as apoc_error:
                logger.warning(
                    "apoc_not_available_using_manual_merge",
                    error=str(apoc_error),
                )

            # Fallback: Manual merge (transfer relationships, delete old entity)
            # Transfer outgoing relationships
            await self.neo4j_client.execute_write(
                """
                MATCH (remove:base {entity_name: $remove_name})-[r:RELATES_TO]->(target:base)
                MATCH (keep:base {entity_name: $keep_name})
                WHERE NOT (keep)-[:RELATES_TO]->(target)
                CREATE (keep)-[r2:RELATES_TO]->(target)
                SET r2 = properties(r)
                DELETE r
                """,
                {"keep_name": keep_name, "remove_name": remove_name},
            )

            # Transfer incoming relationships
            await self.neo4j_client.execute_write(
                """
                MATCH (source:base)-[r:RELATES_TO]->(remove:base {entity_name: $remove_name})
                MATCH (keep:base {entity_name: $keep_name})
                WHERE NOT (source)-[:RELATES_TO]->(keep)
                CREATE (source)-[r2:RELATES_TO]->(keep)
                SET r2 = properties(r)
                DELETE r
                """,
                {"keep_name": keep_name, "remove_name": remove_name},
            )

            # Delete the removed entity
            await self.neo4j_client.execute_write(
                """
                MATCH (remove:base {entity_name: $remove_name})
                DETACH DELETE remove
                """,
                {"remove_name": remove_name},
            )

            logger.info("entities_merged_manually", keep=keep_name, removed=remove_name)
            return True

        except Exception as e:
            logger.error(
                "merge_duplicate_entities_failed",
                entity1=entity1_name,
                entity2=entity2_name,
                error=str(e),
            )
            return False

    def validate_relation(
        self,
        relation: GraphRelationship | dict[str, Any],
        require_evidence: bool = True,
    ) -> tuple[bool, str]:
        """Validate a relation against hygiene rules.

        Rules:
        1. No self-loops (source != target)
        2. Evidence present (if required)
        3. Valid relation type

        Args:
            relation: Relation to validate
            require_evidence: Whether evidence_span is required

        Returns:
            Tuple of (is_valid, reason)
        """
        # Extract fields from relation
        if isinstance(relation, dict):
            source = relation.get("source", "")
            target = relation.get("target", "")
            rel_type = relation.get("type", "RELATES_TO")
            evidence = relation.get("evidence_span", "")
        else:
            source = relation.source
            target = relation.target
            rel_type = relation.type
            evidence = getattr(relation, "evidence_span", "") or ""

        # Rule 1: No self-loops
        if source and target and source.lower() == target.lower():
            return False, f"Self-loop: {source} -> {target}"

        # Rule 2: Evidence present
        if require_evidence and not evidence:
            return False, "Missing evidence_span"

        # Rule 3: Valid relation type (warning only)
        if rel_type and rel_type not in VALID_RELATION_TYPES:
            logger.warning("unknown_relation_type", type=rel_type)
            # Don't fail, just warn

        return True, "valid"

    async def run_hygiene_fixes(
        self,
        namespace_id: str | None = None,
        fix_self_loops: bool = True,
        merge_duplicates: bool = False,
        similarity_threshold: float = 0.95,
    ) -> dict[str, int]:
        """Run automatic hygiene fixes on the graph.

        Args:
            namespace_id: Optional namespace filter
            fix_self_loops: Remove self-loop relations
            merge_duplicates: Merge duplicate entities (conservative threshold)
            similarity_threshold: Threshold for duplicate detection

        Returns:
            Dictionary with fix counts
        """
        logger.info(
            "running_hygiene_fixes",
            namespace_id=namespace_id,
            fix_self_loops=fix_self_loops,
            merge_duplicates=merge_duplicates,
        )

        fixes = {
            "self_loops_removed": 0,
            "duplicates_merged": 0,
        }

        # Fix self-loops
        if fix_self_loops:
            fixes["self_loops_removed"] = await self.remove_self_loops(namespace_id)

        # Merge duplicates (conservative - only very high similarity)
        if merge_duplicates:
            duplicates = await self.find_duplicate_entities(
                similarity_threshold=similarity_threshold,
                namespace_id=namespace_id,
                limit=50,
            )
            for entity1, entity2, _similarity in duplicates:
                if await self.merge_duplicate_entities(entity1, entity2):
                    fixes["duplicates_merged"] += 1

        logger.info("hygiene_fixes_complete", **fixes)
        return fixes


# Global instance (singleton pattern)
_kg_hygiene_service: KGHygieneService | None = None


def get_kg_hygiene_service() -> KGHygieneService:
    """Get global KG hygiene service instance (singleton).

    Returns:
        KGHygieneService instance
    """
    global _kg_hygiene_service
    if _kg_hygiene_service is None:
        _kg_hygiene_service = KGHygieneService()
    return _kg_hygiene_service
