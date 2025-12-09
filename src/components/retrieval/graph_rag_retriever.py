"""GraphRAG Multi-Hop Retriever for Complex Query Answering.

Sprint 38 Feature 38.4: Multi-hop graph reasoning with Neo4j integration.

This module implements the GraphRAG retriever pattern with support for:
- Simple queries (vector + optional graph expansion)
- Compound queries (parallel sub-query execution)
- Multi-hop queries (sequential reasoning with context injection)

Architecture:
    Query → QueryDecomposer → Route → [Vector + Graph + LLM] → Answer

The retriever combines:
1. Vector search (Qdrant via HybridSearch) for semantic retrieval
2. Graph expansion (Neo4j) for entity relationships and multi-hop paths
3. LLM generation (AegisLLMProxy) for final answer synthesis

Example:
    >>> retriever = get_graph_rag_retriever()
    >>> result = await retriever.retrieve(
    ...     query="Who founded the company that developed RAG?",
    ...     max_hops=2
    ... )
    >>> print(result.answer)
    "Facebook (now Meta) developed RAG, founded by Mark Zuckerberg..."
"""

import asyncio
from typing import Any

import structlog
from pydantic import BaseModel, Field

from src.components.graph_rag.neo4j_client import Neo4jClient, get_neo4j_client
from src.components.llm_proxy import get_aegis_llm_proxy
from src.components.llm_proxy.models import (
    Complexity,
    LLMTask,
    QualityRequirement,
    TaskType,
)
from src.components.retrieval.query_decomposition import (
    QueryDecomposer,
    QueryType,
    SubQuery,
)
from src.components.vector_search.hybrid_search import HybridSearch
from src.core.exceptions import GraphQueryError

logger = structlog.get_logger(__name__)


# ============================================================================
# Data Models
# ============================================================================


class Entity(BaseModel):
    """Entity extracted from graph or vector results."""

    name: str = Field(..., description="Entity name")
    type: str = Field(..., description="Entity type (e.g., Person, Organization)")
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional properties")


class Relationship(BaseModel):
    """Relationship between entities."""

    source: str = Field(..., description="Source entity name")
    target: str = Field(..., description="Target entity name")
    type: str = Field(..., description="Relationship type (e.g., RELATES_TO)")
    properties: dict[str, Any] = Field(default_factory=dict, description="Relationship properties")


class GraphPath(BaseModel):
    """Graph path representing multi-hop traversal."""

    nodes: list[str] = Field(..., description="Node names in path")
    relationships: list[str] = Field(..., description="Relationship types in path")
    length: int = Field(..., description="Path length (number of hops)")


class Document(BaseModel):
    """Retrieved document/chunk."""

    id: str = Field(..., description="Document ID")
    text: str = Field(..., description="Document text")
    score: float = Field(..., description="Retrieval score")
    source: str = Field(default="", description="Document source")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Document metadata")


class GraphContext(BaseModel):
    """Accumulated graph context for multi-hop reasoning.

    This class manages the context accumulation during multi-hop graph traversal,
    deduplicating entities, relationships, and paths by their unique identifiers.

    Deduplication Strategy:
    - Entities: By name (case-insensitive)
    - Relationships: By (source, target, type) tuple
    - Paths: By node sequence
    - Documents: By ID
    """

    entities: list[Entity] = Field(default_factory=list, description="Entities in context")
    relationships: list[Relationship] = Field(
        default_factory=list, description="Relationships in context"
    )
    paths: list[GraphPath] = Field(default_factory=list, description="Graph paths traversed")
    documents: list[Document] = Field(
        default_factory=list, description="Retrieved documents/chunks"
    )

    def add_entity(self, entity: Entity) -> None:
        """Add entity with deduplication by name (case-insensitive).

        Args:
            entity: Entity to add
        """
        existing_names = {e.name.lower() for e in self.entities}
        if entity.name.lower() not in existing_names:
            self.entities.append(entity)

    def add_relationship(self, relationship: Relationship) -> None:
        """Add relationship with deduplication by (source, target, type).

        Args:
            relationship: Relationship to add
        """
        existing_rels = {
            (r.source.lower(), r.target.lower(), r.type.lower()) for r in self.relationships
        }
        rel_key = (
            relationship.source.lower(),
            relationship.target.lower(),
            relationship.type.lower(),
        )
        if rel_key not in existing_rels:
            self.relationships.append(relationship)

    def add_path(self, path: GraphPath) -> None:
        """Add graph path with deduplication by node sequence.

        Args:
            path: GraphPath to add
        """
        existing_paths = {tuple(p.nodes) for p in self.paths}
        path_key = tuple(path.nodes)
        if path_key not in existing_paths:
            self.paths.append(path)

    def add_document(self, document: Document) -> None:
        """Add document with deduplication by ID.

        Args:
            document: Document to add
        """
        existing_ids = {d.id for d in self.documents}
        if document.id not in existing_ids:
            self.documents.append(document)

    def to_prompt_context(self) -> str:
        """Convert graph context to formatted string for LLM prompt.

        Returns:
            Formatted context string with entities, relationships, paths, and documents
        """
        context_parts = []

        # Entities section
        if self.entities:
            context_parts.append("## Entities")
            for entity in self.entities[:20]:  # Limit to top 20
                props_str = ", ".join(f"{k}={v}" for k, v in entity.properties.items())
                entity_str = f"- {entity.name} ({entity.type})"
                if props_str:
                    entity_str += f" [{props_str}]"
                context_parts.append(entity_str)

        # Relationships section
        if self.relationships:
            context_parts.append("\n## Relationships")
            for rel in self.relationships[:30]:  # Limit to top 30
                context_parts.append(f"- {rel.source} --[{rel.type}]--> {rel.target}")

        # Paths section (multi-hop)
        if self.paths:
            context_parts.append("\n## Graph Paths")
            for path in self.paths[:10]:  # Limit to top 10
                path_str = " -> ".join(
                    f"{node} [{rel}]" if i < len(path.relationships) else node
                    for i, node in enumerate(path.nodes)
                    for rel in ([path.relationships[i]] if i < len(path.relationships) else [])
                )
                context_parts.append(f"- {path_str} (hops: {path.length})")

        # Documents section
        if self.documents:
            context_parts.append("\n## Retrieved Documents")
            for doc in self.documents[:5]:  # Limit to top 5
                doc_preview = doc.text[:200] + "..." if len(doc.text) > 200 else doc.text
                context_parts.append(f"- [{doc.source}] (score: {doc.score:.3f})")
                context_parts.append(f"  {doc_preview}")

        return "\n".join(context_parts)


class GraphRAGResult(BaseModel):
    """Result from GraphRAG retrieval."""

    query: str = Field(..., description="Original query")
    answer: str = Field(..., description="Generated answer")
    context: GraphContext = Field(..., description="Accumulated graph context")
    query_type: QueryType = Field(..., description="Classified query type")
    sub_queries: list[SubQuery] = Field(default_factory=list, description="Decomposed sub-queries")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ============================================================================
# GraphRAG Retriever
# ============================================================================


class GraphRAGRetriever:
    """GraphRAG retriever for multi-hop question answering.

    This retriever implements the GraphRAG pattern with support for:
    - SIMPLE queries: Vector search + optional graph expansion
    - COMPOUND queries: Parallel sub-query execution with result fusion
    - MULTI_HOP queries: Sequential reasoning with context accumulation

    Attributes:
        query_decomposer: QueryDecomposer for query classification
        hybrid_search: HybridSearch for vector + BM25 retrieval
        neo4j_client: Neo4jClient for graph queries
        llm_proxy: AegisLLMProxy for answer generation
    """

    def __init__(
        self,
        query_decomposer: QueryDecomposer | None = None,
        hybrid_search: HybridSearch | None = None,
        neo4j_client: Neo4jClient | None = None,
    ) -> None:
        """Initialize GraphRAG retriever.

        Args:
            query_decomposer: QueryDecomposer instance (default: new instance)
            hybrid_search: HybridSearch instance (default: new instance)
            neo4j_client: Neo4jClient instance (default: singleton)
        """
        self.query_decomposer = query_decomposer or QueryDecomposer()
        self.hybrid_search = hybrid_search or HybridSearch()
        self.neo4j_client = neo4j_client or get_neo4j_client()
        self.llm_proxy = get_aegis_llm_proxy()

        logger.info("graph_rag_retriever_initialized")

    async def retrieve(
        self,
        query: str,
        max_hops: int = 2,
        top_k: int = 5,
        use_graph_expansion: bool = True,
    ) -> GraphRAGResult:
        """Retrieve and answer query using GraphRAG approach.

        This is the main entry point for GraphRAG retrieval. It:
        1. Classifies query type (SIMPLE/COMPOUND/MULTI_HOP)
        2. Routes to appropriate retrieval strategy
        3. Generates answer from accumulated context

        Args:
            query: User query
            max_hops: Maximum graph traversal depth (default: 2)
            top_k: Number of documents to retrieve (default: 5)
            use_graph_expansion: Enable graph expansion (default: True)

        Returns:
            GraphRAGResult with answer and context

        Example:
            >>> result = await retriever.retrieve(
            ...     "Who founded the company that developed RAG?",
            ...     max_hops=2
            ... )
        """
        logger.info("graph_rag_retrieve_start", query=query[:100], max_hops=max_hops)

        # Step 1: Classify query
        decomposition = await self.query_decomposer.decompose(query)
        query_type = decomposition.classification.query_type

        logger.info(
            "query_classified",
            query_type=query_type.value,
            confidence=decomposition.classification.confidence,
            num_sub_queries=len(decomposition.sub_queries),
        )

        # Step 2: Route to appropriate retrieval strategy
        context = GraphContext()

        if query_type == QueryType.SIMPLE:
            context = await self._simple_retrieve(
                query=query,
                top_k=top_k,
                max_hops=max_hops,
                use_graph_expansion=use_graph_expansion,
            )
        elif query_type == QueryType.COMPOUND:
            context = await self._compound_retrieve(
                sub_queries=decomposition.sub_queries,
                top_k=top_k,
                max_hops=max_hops,
                use_graph_expansion=use_graph_expansion,
            )
        else:  # MULTI_HOP
            context = await self._multi_hop_retrieve(
                sub_queries=decomposition.sub_queries,
                top_k=top_k,
                max_hops=max_hops,
            )

        # Step 3: Generate answer from context
        answer = await self._generate_answer(query=query, context=context)

        logger.info(
            "graph_rag_retrieve_complete",
            query_type=query_type.value,
            num_entities=len(context.entities),
            num_relationships=len(context.relationships),
            num_documents=len(context.documents),
            answer_length=len(answer),
        )

        return GraphRAGResult(
            query=query,
            answer=answer,
            context=context,
            query_type=query_type,
            sub_queries=decomposition.sub_queries,
            metadata={
                "max_hops": max_hops,
                "top_k": top_k,
                "use_graph_expansion": use_graph_expansion,
            },
        )

    async def _simple_retrieve(
        self,
        query: str,
        top_k: int,
        max_hops: int,
        use_graph_expansion: bool,
    ) -> GraphContext:
        """Handle SIMPLE query: vector search + optional graph expansion.

        Args:
            query: Query string
            top_k: Number of documents to retrieve
            max_hops: Maximum graph expansion hops
            use_graph_expansion: Enable graph expansion

        Returns:
            GraphContext with retrieved documents and entities
        """
        context = GraphContext()

        # Step 1: Vector search
        search_result = await self.hybrid_search.hybrid_search(
            query=query,
            top_k=top_k,
            use_reranking=True,
        )

        # Convert search results to documents
        for result in search_result["results"]:
            doc = Document(
                id=result.get("id", ""),
                text=result.get("text", ""),
                score=result.get("rerank_score", result.get("score", 0.0)),
                source=result.get("source", ""),
                metadata=result,
            )
            context.add_document(doc)

        # Step 2: Extract entities from results
        if use_graph_expansion and context.documents:
            entities = await self._extract_entities_from_results(context.documents)
            for entity in entities:
                context.add_entity(entity)

            # Step 3: Graph expansion (1-hop neighborhood)
            if entities:
                await self._graph_expand(
                    context=context,
                    entity_names=[e.name for e in entities[:10]],  # Limit to top 10
                    max_hops=min(max_hops, 1),  # Simple queries: max 1 hop
                )

        logger.info(
            "simple_retrieve_complete",
            num_documents=len(context.documents),
            num_entities=len(context.entities),
            num_relationships=len(context.relationships),
        )

        return context

    async def _compound_retrieve(
        self,
        sub_queries: list[SubQuery],
        top_k: int,
        max_hops: int,
        use_graph_expansion: bool,
    ) -> GraphContext:
        """Handle COMPOUND query: parallel sub-query execution.

        Args:
            sub_queries: List of sub-queries to execute in parallel
            top_k: Number of documents per sub-query
            max_hops: Maximum graph expansion hops
            use_graph_expansion: Enable graph expansion

        Returns:
            GraphContext with merged results from all sub-queries
        """
        context = GraphContext()

        # Execute all sub-queries in parallel
        tasks = [
            self._simple_retrieve(
                query=sq.query,
                top_k=top_k,
                max_hops=max_hops,
                use_graph_expansion=use_graph_expansion,
            )
            for sq in sub_queries
        ]

        sub_contexts = await asyncio.gather(*tasks)

        # Merge all contexts (deduplication handled by add_* methods)
        for sub_context in sub_contexts:
            for entity in sub_context.entities:
                context.add_entity(entity)
            for rel in sub_context.relationships:
                context.add_relationship(rel)
            for path in sub_context.paths:
                context.add_path(path)
            for doc in sub_context.documents:
                context.add_document(doc)

        logger.info(
            "compound_retrieve_complete",
            num_sub_queries=len(sub_queries),
            num_documents=len(context.documents),
            num_entities=len(context.entities),
        )

        return context

    async def _multi_hop_retrieve(
        self,
        sub_queries: list[SubQuery],
        top_k: int,
        max_hops: int,
    ) -> GraphContext:
        """Handle MULTI_HOP query: sequential reasoning with context injection.

        This method executes sub-queries sequentially, using the context from
        previous queries to inform subsequent queries (context injection).

        Args:
            sub_queries: List of sub-queries with dependencies
            top_k: Number of documents per sub-query
            max_hops: Maximum graph expansion hops

        Returns:
            GraphContext with accumulated multi-hop reasoning context
        """
        context = GraphContext()

        # Execute sub-queries in dependency order
        sorted_queries = sorted(sub_queries, key=lambda sq: sq.index)

        for sq in sorted_queries:
            logger.info(
                "multi_hop_step",
                step=sq.index,
                query=sq.query[:100],
                depends_on=sq.depends_on,
            )

            # Build augmented query with context from previous steps
            augmented_query = sq.query
            if sq.depends_on and context.entities:
                # Inject entity names from previous steps
                entity_names = [e.name for e in context.entities[:5]]
                augmented_query = f"{sq.query}\n\nRelevant entities: {', '.join(entity_names)}"

            # Execute vector search
            search_result = await self.hybrid_search.hybrid_search(
                query=augmented_query,
                top_k=top_k,
                use_reranking=True,
            )

            # Add documents to context
            for result in search_result["results"]:
                doc = Document(
                    id=result.get("id", ""),
                    text=result.get("text", ""),
                    score=result.get("rerank_score", result.get("score", 0.0)),
                    source=result.get("source", ""),
                    metadata=result,
                )
                context.add_document(doc)

            # Extract entities and expand graph
            entities = await self._extract_entities_from_results(
                [
                    doc
                    for doc in context.documents
                    if doc not in context.documents[: -len(search_result["results"])]
                ]
            )
            for entity in entities:
                context.add_entity(entity)

            if entities:
                await self._graph_expand(
                    context=context,
                    entity_names=[e.name for e in entities[:10]],
                    max_hops=max_hops,
                )

        logger.info(
            "multi_hop_retrieve_complete",
            num_steps=len(sorted_queries),
            num_documents=len(context.documents),
            num_entities=len(context.entities),
            num_paths=len(context.paths),
        )

        return context

    async def _extract_entities_from_results(
        self,
        documents: list[Document],
    ) -> list[Entity]:
        """Extract entities from retrieved documents using Neo4j graph lookup.

        This method searches the Neo4j graph for entities mentioned in the
        retrieved documents by matching text content.

        Args:
            documents: Retrieved documents

        Returns:
            List of entities found in Neo4j graph
        """
        if not documents:
            return []

        entities = []

        try:
            # Build text snippets for matching
            text_snippets = [doc.text[:500] for doc in documents[:5]]  # Limit to top 5 docs

            # Query Neo4j for entities mentioned in documents
            # Note: This is a simplified approach. In production, you'd use NER + entity linking
            cypher = """
            UNWIND $text_snippets AS snippet
            MATCH (e:base)
            WHERE snippet CONTAINS e.name
            RETURN DISTINCT e.name AS name, e.type AS type,
                   properties(e) AS properties
            LIMIT 20
            """

            results = await self.neo4j_client.execute_query(
                query=cypher,
                parameters={"text_snippets": text_snippets},
            )

            for record in results:
                entity = Entity(
                    name=record["name"],
                    type=record.get("type", "Unknown"),
                    properties=record.get("properties", {}),
                )
                entities.append(entity)

            logger.info(
                "entities_extracted_from_results",
                num_documents=len(documents),
                num_entities=len(entities),
            )

        except Exception as e:
            logger.warning("entity_extraction_failed", error=str(e))

        return entities

    async def _graph_expand(
        self,
        context: GraphContext,
        entity_names: list[str],
        max_hops: int,
    ) -> None:
        """Expand graph context with N-hop traversal from seed entities.

        This method performs graph traversal starting from seed entities,
        following RELATES_TO and MENTIONED_IN relationships up to max_hops.

        Args:
            context: GraphContext to populate (modified in-place)
            entity_names: Seed entity names for traversal
            max_hops: Maximum traversal depth
        """
        if not entity_names or max_hops < 1:
            return

        try:
            # Multi-hop traversal query
            cypher = f"""
            MATCH path = (start:base)-[r:RELATES_TO|MENTIONED_IN*1..{max_hops}]-(connected:base)
            WHERE start.name IN $entity_names
            WITH connected, path, length(path) AS hops,
                 [rel IN relationships(path) | type(rel)] AS rel_types,
                 [node IN nodes(path) | node.name] AS path_nodes
            RETURN DISTINCT connected.name AS name,
                   connected.type AS type,
                   hops,
                   rel_types,
                   path_nodes
            ORDER BY hops
            LIMIT 20
            """

            results = await self.neo4j_client.execute_query(
                query=cypher,
                parameters={"entity_names": entity_names},
            )

            for record in results:
                # Add expanded entity
                entity = Entity(
                    name=record["name"],
                    type=record.get("type", "Unknown"),
                    properties={"hops": record["hops"]},
                )
                context.add_entity(entity)

                # Add path
                path = GraphPath(
                    nodes=record["path_nodes"],
                    relationships=record["rel_types"],
                    length=record["hops"],
                )
                context.add_path(path)

                # Add relationships from path
                for i in range(len(record["path_nodes"]) - 1):
                    rel = Relationship(
                        source=record["path_nodes"][i],
                        target=record["path_nodes"][i + 1],
                        type=record["rel_types"][i] if i < len(record["rel_types"]) else "UNKNOWN",
                    )
                    context.add_relationship(rel)

            logger.info(
                "graph_expand_complete",
                seed_entities=len(entity_names),
                max_hops=max_hops,
                expanded_entities=len(results),
                total_entities=len(context.entities),
                total_relationships=len(context.relationships),
                total_paths=len(context.paths),
            )

        except Exception as e:
            logger.error("graph_expand_failed", error=str(e))
            raise GraphQueryError(
                query=f"Graph expansion for {entity_names[:3]}", reason=str(e)
            ) from e

    async def _generate_answer(
        self,
        query: str,
        context: GraphContext,
    ) -> str:
        """Generate answer from query and accumulated context using LLM.

        Args:
            query: Original user query
            context: GraphContext with entities, relationships, documents

        Returns:
            Generated answer string
        """
        # Build prompt with context
        context_str = context.to_prompt_context()

        prompt = f"""Answer the following question using the provided context.

Question: {query}

Context:
{context_str}

Instructions:
- Answer the question directly and concisely
- Use information from entities, relationships, and documents
- If the context doesn't contain enough information, say so
- Cite sources when possible

Answer:"""

        # Generate answer using AegisLLMProxy
        task = LLMTask(
            task_type=TaskType.ANSWER_GENERATION,
            prompt=prompt,
            quality_requirement=QualityRequirement.MEDIUM,
            complexity=Complexity.MEDIUM,
            max_tokens=512,
            temperature=0.3,
        )

        try:
            response = await self.llm_proxy.generate(task)
            answer = response.content.strip()

            logger.info(
                "answer_generated",
                query=query[:100],
                answer_length=len(answer),
                provider=response.provider,
                tokens_used=response.tokens_used,
            )

            return answer

        except Exception as e:
            logger.error("answer_generation_failed", error=str(e))
            return f"Failed to generate answer: {e}"


# ============================================================================
# Singleton Pattern
# ============================================================================

_graph_rag_retriever_instance: GraphRAGRetriever | None = None


def get_graph_rag_retriever() -> GraphRAGRetriever:
    """Get singleton instance of GraphRAGRetriever.

    Returns:
        GraphRAGRetriever instance
    """
    global _graph_rag_retriever_instance
    if _graph_rag_retriever_instance is None:
        _graph_rag_retriever_instance = GraphRAGRetriever()
    return _graph_rag_retriever_instance
