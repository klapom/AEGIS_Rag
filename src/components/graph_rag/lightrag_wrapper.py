"""LightRAG wrapper for graph-based knowledge retrieval.

This module wraps the LightRAG library to provide:
- Multi-cloud LLM integration via AegisLLMProxy (Sprint 23)
- Neo4j backend storage
- Async support
- Error handling and retry logic

Sprint 5: Feature 5.1 - LightRAG Core Integration
Sprint 14: Feature 14.1 - Three-Phase Pipeline Integration with Graph-based Provenance
Sprint 23: Feature 23.6 - AegisLLMProxy Integration
"""

import time
from pathlib import Path
from typing import Any

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.chunk import ChunkStrategy
from src.core.chunking_service import get_chunking_service
from src.core.config import settings
from src.core.models import GraphQueryResult

# Sprint 32 FIX: Use ExtractionPipelineFactory instead of deprecated ThreePhaseExtractor
# The ThreePhaseExtractor was removed in Sprint 25 (ADR-026) and caused 'NoneType' is not callable errors
from src.components.graph_rag.extraction_factory import create_extraction_pipeline_from_config

logger = structlog.get_logger(__name__)


class LightRAGClient:
    """Async wrapper for LightRAG with Ollama and Neo4j backend.

    Sprint 25 Feature 25.9: Renamed from LightRAGWrapper to LightRAGClient for consistency.

    Provides:
    - Document ingestion and graph construction
    - Dual-level retrieval (local/global/hybrid)
    - Entity and relationship extraction
    - Integration with existing AEGIS RAG components
    """

    def __init__(
        self,
        working_dir: str | None = None,
        llm_model: str | None = None,
        embedding_model: str | None = None,
        neo4j_uri: str | None = None,
        neo4j_user: str | None = None,
        neo4j_password: str | None = None,
    ) -> None:
        """Initialize LightRAG wrapper.

        Args:
            working_dir: Working directory for LightRAG
            llm_model: Ollama LLM model name
            embedding_model: Ollama embedding model name
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        # Configuration
        self.working_dir = Path(working_dir or settings.lightrag_working_dir)
        self.llm_model = llm_model or settings.lightrag_llm_model
        self.embedding_model = embedding_model or settings.lightrag_embedding_model
        self.neo4j_uri = neo4j_uri or settings.neo4j_uri
        self.neo4j_user = neo4j_user or settings.neo4j_user
        self.neo4j_password = neo4j_password or settings.neo4j_password.get_secret_value()

        # Create working directory
        self.working_dir.mkdir(parents=True, exist_ok=True)

        # Initialize LightRAG with Ollama LLM functions
        self.rag: Any = None  # Will be initialized lazily
        self._initialized = False

        logger.info(
            "lightrag_wrapper_initialized",
            working_dir=str(self.working_dir),
            llm_model=self.llm_model,
            embedding_model=self.embedding_model,
            neo4j_uri=self.neo4j_uri,
        )

    async def _ensure_initialized(self) -> None:
        """Ensure LightRAG is initialized (lazy initialization)."""
        if self._initialized:
            return

        try:
            # Import LightRAG components (optional dependency)
            import os

            from lightrag import LightRAG

            # set Neo4j environment variables (required by Neo4JStorage)
            os.environ["NEO4J_URI"] = self.neo4j_uri
            os.environ["NEO4J_USERNAME"] = self.neo4j_user
            os.environ["NEO4J_PASSWORD"] = self.neo4j_password

            # Sprint 23: Configure multi-cloud LLM function via AegisLLMProxy
            from src.components.llm_proxy import get_aegis_llm_proxy
            from src.components.llm_proxy.models import (
                Complexity,
                LLMTask,
                QualityRequirement,
                TaskType,
            )

            proxy = get_aegis_llm_proxy()

            async def aegis_llm_complete(
                prompt: str,
                system_prompt: str | None = None,
                model: str = self.llm_model,
                **kwargs: Any,
            ) -> str:
                """Multi-cloud LLM completion function for LightRAG.

                Sprint 23: Uses AegisLLMProxy for intelligent routing.
                LightRAG sends entity extraction instructions in system_prompt
                and the actual task in prompt.
                """
                # Combine system prompt and user prompt
                combined_prompt = prompt
                if system_prompt:
                    combined_prompt = f"{system_prompt}\n\n{prompt}"

                # Log prompts being sent to LLM
                logger.info(
                    "lightrag_llm_request",
                    model=model,
                    system_prompt_length=len(system_prompt) if system_prompt else 0,
                    system_prompt_preview=(system_prompt[:500] if system_prompt else ""),
                    user_prompt_length=len(prompt),
                    user_prompt_preview=prompt[:500],
                    system_prompt_full=system_prompt,  # Full system prompt
                    user_prompt_full=prompt,  # Full user prompt
                )

                # Sprint 23: Use AegisLLMProxy for generation
                task = LLMTask(
                    task_type=TaskType.EXTRACTION,
                    prompt=combined_prompt,
                    quality_requirement=QualityRequirement.MEDIUM,
                    complexity=Complexity.MEDIUM,
                    temperature=settings.lightrag_llm_temperature,
                    max_tokens=settings.lightrag_llm_max_tokens,
                    model_local=model,
                )

                response = await proxy.generate(task)
                result: str = response.content

                # Log response from LLM
                logger.info(
                    "lightrag_llm_response",
                    provider=response.provider,
                    model=response.model,
                    response_length=len(result),
                    response_preview=result[:500],  # First 500 chars
                    response_full=result,  # Full response for debugging
                    cost_usd=response.cost_usd,
                    latency_ms=response.latency_ms,
                )

                return result

            # Configure Ollama embedding function with UnifiedEmbeddingService
            # Sprint 11 Feature 11.2: Use shared embedding service for cache sharing across components
            # Sprint 12 Fix: UnifiedEmbeddingService now pickle-compatible (lazy AsyncClient creation)
            from src.components.shared.embedding_service import get_embedding_service

            class UnifiedEmbeddingFunc:
                """Wrapper for UnifiedEmbeddingService compatible with LightRAG.

                Sprint 12: This wrapper is now PICKLE-COMPATIBLE because UnifiedEmbeddingService
                uses lazy AsyncClient creation instead of storing it as instance variable.

                See: src/components/shared/embedding_service.py for detailed explanation
                     of pickle compatibility design decision.
                """

                def __init__(self, embedding_dim: int = 768):
                    self.embedding_dim = embedding_dim
                    self.unified_service = get_embedding_service()

                async def __call__(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
                    """Generate embeddings using shared service."""
                    return await self.unified_service.embed_batch(texts)

                @property
                def async_func(self) -> None:
                    """Return self to indicate this is an async function."""
                    return self

            # Create embedding function instance
            # Sprint 16 Feature 16.2: BGE-M3 system-wide standardization (1024 dimensions)
            embedding_func = UnifiedEmbeddingFunc(embedding_dim=1024)

            # Initialize LightRAG with Neo4j backend (uses env vars)
            # Sprint 13 TD-31 Fix: Optimize for llama3.2:3b (8k context, small model)
            # Sprint 16 Feature 16.6: Disable internal chunking (use ChunkingService instead)
            # Sprint 23: Use AegisLLMProxy for multi-cloud routing
            self.rag = LightRAG(
                working_dir=str(self.working_dir),
                llm_model_func=aegis_llm_complete,  # Sprint 23: Multi-cloud routing
                embedding_func=embedding_func,
                graph_storage="Neo4JStorage",  # Storage type name as string
                llm_model_max_async=2,  # Reduce from 4 to 2 workers (halves memory usage)
                # Sprint 16 Feature 16.6: CHUNKING DISABLED - we use ChunkingService
                # Internal chunking is bypassed by using insert_documents_optimized()
                # which calls _chunk_text_with_metadata() -> ChunkingService
                chunk_token_size=99999,  # Effectively disable (will never chunk internally)
                chunk_overlap_token_size=0,  # No overlap for internal chunking
                top_k=15,  # Reduce from default 60 (entities/relations per query)
                chunk_top_k=10,  # Reduce from default 15 (max chunks in context)
                max_entity_tokens=2500,  # Reduce from default 6000
                max_relation_tokens=2500,  # Reduce from default 6000
                max_total_tokens=7000,  # CRITICAL: Reduce from default 30000 (was 4x too large!)
                cosine_threshold=0.05,  # Lower from default 0.2 (small model embeddings less precise)
            )

            # Initialize storages (required by lightrag-hku 1.4.9+)
            from lightrag.kg.shared_storage import initialize_pipeline_status

            await self.rag.initialize_storages()
            await initialize_pipeline_status()

            self._initialized = True
            logger.info("lightrag_initialized_successfully")

        except ImportError as e:
            logger.error(
                "lightrag_import_failed",
                error=str(e),
                hint="Run: poetry add lightrag-hku networkx graspologic",
            )
            raise
        except Exception as e:
            logger.error("lightrag_initialization_failed", error=str(e))
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def insert_documents(self, documents: list[dict[str, Any]]) -> dict[str, Any]:
        """Insert multiple documents into knowledge graph.

        Args:
            documents: list of documents with 'text' and optional 'metadata' fields

        Returns:
            Batch insertion result with success/failure counts
        """
        await self._ensure_initialized()

        logger.info("lightrag_insert_documents", count=len(documents))

        results = []
        for i, doc in enumerate(documents):
            try:
                text = doc.get("text", "")
                if not text:
                    logger.warning("empty_document", index=i)
                    results.append({"index": i, "status": "skipped", "reason": "empty_text"})
                    continue

                # Insert text into LightRAG
                # LightRAG automatically:
                # 1. Extracts entities and relationships using LLM
                # 2. Builds knowledge graph in Neo4j
                # 3. Creates embeddings for entities
                result = await self.rag.ainsert(text)

                results.append({"index": i, "status": "success", "result": result})
                logger.debug("document_inserted", index=i, result=result)

            except Exception as e:
                logger.error(
                    "lightrag_insert_document_failed",
                    index=i,
                    error=str(e),
                )
                results.append({"index": i, "status": "error", "error": str(e)})

        success_count = sum(1 for r in results if r["status"] == "success")
        logger.info(
            "lightrag_insert_documents_complete",
            total=len(documents),
            success=success_count,
            failed=len(documents) - success_count,
        )

        return {
            "total": len(documents),
            "success": success_count,
            "failed": len(documents) - success_count,
            "results": results,
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def query_graph(
        self,
        query: str,
        mode: str = "hybrid",
    ) -> GraphQueryResult:
        """Query knowledge graph with dual-level retrieval.

        Args:
            query: User query string
            mode: Search mode (local/global/hybrid)

        Returns:
            GraphQueryResult with answer and retrieved entities/relationships
        """
        await self._ensure_initialized()

        logger.info("🔍 [QUERY START] lightrag_query", query=query, mode=mode)

        try:
            # Import QueryParam
            from lightrag import QueryParam

            # 🔍 ULTRATHINK: Check LightRAG internal state before query
            logger.info("🔍 [PRE-QUERY CHECK] Checking LightRAG state before query")

            # Check if graph has entities
            try:
                stats = await self.get_stats()
                logger.info("🔍 [GRAPH STATS]", **stats)

                if stats.get("entity_count", 0) == 0:
                    logger.warning(
                        "⚠️ [NO ENTITIES] Graph is empty! Query will likely return empty answer."
                    )
            except Exception as e:
                logger.warning("🔍 [STATS CHECK FAILED]", error=str(e))

            # 🔍 ULTRATHINK: Log QueryParam details
            query_param = QueryParam(mode=mode)
            logger.info(
                "🔍 [QUERY PARAM]",
                mode=mode,
                param_type=type(query_param).__name__,
                param_attrs=dir(query_param),
            )

            # 🔍 ULTRATHINK: Log aquery call details
            logger.info(
                "🔍 [CALLING AQUERY] About to call self.rag.aquery()",
                rag_instance=str(type(self.rag).__name__),
                rag_working_dir=str(self.working_dir),
                rag_llm_func=str(
                    self.rag.llm_model_func if hasattr(self.rag, "llm_model_func") else "NOT SET"
                ),
                rag_embedding_func=str(
                    type(self.rag.embedding_func).__name__
                    if hasattr(self.rag, "embedding_func")
                    else "NOT SET"
                ),
            )

            # Query LightRAG
            # - local: Entity-level retrieval (specific entities and relationships)
            # - global: Topic-level retrieval (high-level summaries, communities)
            # - hybrid: Combined local + global
            logger.info("🔍 [AQUERY] Calling rag.aquery() now...")
            answer = await self.rag.aquery(
                query=query,
                param=query_param,
            )
            logger.info(
                "🔍 [AQUERY COMPLETE] rag.aquery() returned",
                answer_type=type(answer).__name__,
                answer_length=len(answer) if answer else 0,
                answer_is_empty=(not answer or answer.strip() == ""),
                answer_preview=(answer[:200] if answer else "EMPTY"),
                answer_full=answer,  # Full answer for debugging
            )

            # 🔍 ULTRATHINK: Check answer content
            if not answer or answer.strip() == "":
                logger.error(
                    "❌ [EMPTY ANSWER] aquery() returned empty answer!",
                    query=query,
                    mode=mode,
                    answer_repr=repr(answer),
                )

            # LightRAG returns a string answer
            # We need to parse/structure it for our response
            result = GraphQueryResult(
                query=query,
                answer=answer or "",
                entities=[],  # TODO: Extract from LightRAG internal state
                relationships=[],  # TODO: Extract from LightRAG internal state
                topics=[],
                context="",  # TODO: Get context used for generation
                mode=mode,
                metadata={
                    "mode": mode,
                    "answer_length": len(answer) if answer else 0,
                },
            )

            logger.info(
                "✅ [QUERY COMPLETE] lightrag_query_complete",
                query=query[:100],
                mode=mode,
                answer_length=len(answer) if answer else 0,
                result_has_answer=bool(result.answer),
            )

            return result

        except Exception as e:
            logger.error(
                "❌ [QUERY FAILED] lightrag_query_failed",
                query=query[:100],
                mode=mode,
                error=str(e),
                error_type=type(e).__name__,
                traceback=str(e.__traceback__) if hasattr(e, "__traceback__") else None,
            )
            raise

    async def get_stats(self) -> dict[str, Any]:
        """Get graph statistics (entity count, relationship count).

        Returns:
            Dictionary with entity_count and relationship_count
        """
        logger.info("lightrag_get_stats")

        try:
            # Query Neo4j directly for statistics
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password),
            )

            async with driver.session() as session:
                # Get entity count (LightRAG uses 'base' label, not 'Entity')
                entity_result = await session.run("MATCH (e:base) RETURN count(e) AS count")
                entity_record = await entity_result.single()
                entity_count = entity_record["count"] if entity_record else 0

                # Get relationship count
                rel_result = await session.run("MATCH ()-[r]->() RETURN count(r) AS count")
                rel_record = await rel_result.single()
                relationship_count = rel_record["count"] if rel_record else 0

            await driver.close()

            stats = {
                "entity_count": entity_count,
                "relationship_count": relationship_count,
            }

            logger.info("lightrag_stats", **stats)
            return stats

        except Exception as e:
            logger.error("lightrag_stats_failed", error=str(e))
            return {
                "entity_count": 0,
                "relationship_count": 0,
                "error": str(e),
            }

    async def health_check(self) -> bool:
        """Check health of LightRAG and Neo4j connection.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Test Neo4j connection
            from neo4j import AsyncGraphDatabase

            driver = AsyncGraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password),
            )

            async with driver.session() as session:
                result = await session.run("RETURN 1 AS health")
                record = await result.single()
                healthy: bool = bool(record and record["health"] == 1)

            await driver.close()

            logger.info("lightrag_health_check", healthy=healthy)
            return healthy

        except Exception as e:
            logger.error("lightrag_health_check_failed", error=str(e))
            return False

    def _chunk_text_with_metadata(
        self,
        text: str,
        document_id: str,
        chunk_token_size: int = 600,
        chunk_overlap_token_size: int = 100,
    ) -> list[dict[str, Any]]:
        """Chunk text using unified ChunkingService.

        Sprint 16 Feature 16.1: Now uses unified ChunkingService with "fixed" strategy (tiktoken-based)
        to ensure compatibility with LightRAG embeddings and consistent chunking across all pipelines.

        Args:
            text: Document text to chunk
            document_id: Source document ID for provenance tracking
            chunk_token_size: Target chunk size in tokens (default: 600, matches LightRAG config)
            chunk_overlap_token_size: Overlap between chunks (default: 100)

        Returns:
            list of chunk dictionaries compatible with LightRAG format
        """
        logger.info(
            "chunking_text_with_unified_service",
            document_id=document_id,
            text_length=len(text),
            chunk_token_size=chunk_token_size,
            chunk_overlap=chunk_overlap_token_size,
        )

        # Sprint 16.7: Use unified ChunkingService with adaptive strategy
        # ALIGNED with Qdrant pipeline for maximum synergie (same chunk_ids!)
        chunking_service = get_chunking_service(
            strategy=ChunkStrategy(
                method="adaptive",  # Changed from "fixed" to "adaptive" for better entity extraction
                chunk_size=chunk_token_size,
                overlap=chunk_overlap_token_size,
            )
        )

        # Get chunks from ChunkingService
        chunks_obj = chunking_service.chunk_document(
            document_id=document_id,
            content=text,
            metadata={},
        )

        # Convert Chunk objects to LightRAG format
        chunks = []
        for chunk_obj in chunks_obj:
            chunk = chunk_obj.to_lightrag_format()
            chunks.append(chunk)

        logger.info(
            "chunking_complete_unified_service",
            document_id=document_id,
            total_chunks=len(chunks),
        )

        return chunks

    async def _extract_per_chunk_with_three_phase(
        self,
        document_text: str,
        document_id: str,
    ) -> dict[str, Any]:
        """Extract entities and relations per-chunk using Three-Phase Pipeline.

        Sprint 14 Feature 14.1 - Phase 2: Per-Chunk Extraction

        Process:
        1. Chunk document with tiktoken (600 tokens, 100 overlap)
        2. For each chunk: Run Three-Phase Pipeline (SpaCy + Dedup + Gemma)
        3. Annotate all entities/relations with chunk_id for provenance

        Args:
            document_text: Full document text
            document_id: Source document ID

        Returns:
            Dictionary with:
            - chunks: list of chunk metadata
            - entities: list of all entities from all chunks (with chunk_id)
            - relations: list of all relations from all chunks (with chunk_id)
            - stats: Extraction statistics
        """
        start_time = time.time()

        logger.info(
            "per_chunk_extraction_start",
            document_id=document_id,
            text_length=len(document_text),
        )

        # Step 1: Chunk the document (Sprint 30: aligned with Qdrant)
        chunks = self._chunk_text_with_metadata(
            text=document_text,
            document_id=document_id,
            chunk_token_size=1800,  # Sprint 30: Aligned with Qdrant (1800 tokens)
            chunk_overlap_token_size=300,  # Sprint 30: 16.7% overlap (aligned with Qdrant)
        )

        logger.info(
            "chunking_complete",
            document_id=document_id,
            total_chunks=len(chunks),
        )

        # Step 2: Initialize Extraction Pipeline (Sprint 32 FIX: Use Factory per ADR-026)
        # Replaces deprecated ThreePhaseExtractor which was removed in Sprint 25
        extractor = create_extraction_pipeline_from_config()
        logger.info(
            "extraction_pipeline_initialized",
            pipeline_type="llm_extraction",
            note="Using ExtractionPipelineFactory for entity/relation extraction",
        )

        # Step 3: Extract entities and relations per chunk
        all_entities = []
        all_relations = []

        for chunk in chunks:
            chunk_id = chunk["chunk_id"]
            chunk_text = chunk["text"]
            chunk_index = chunk["chunk_index"]

            logger.info(
                "extracting_chunk",
                document_id=document_id,
                chunk_id=chunk_id[:8],
                chunk_index=chunk_index,
                chunk_tokens=chunk["tokens"],
            )

            try:
                # Run LLM Extraction Pipeline (Sprint 32 FIX: Replaced Three-Phase)
                entities, relations = await extractor.extract(
                    text=chunk_text, document_id=f"{document_id}#{chunk_index}"
                )

                # Annotate entities with chunk_id and chunk metadata
                # Sprint 16 fix (d8e52c0): Handle both old and new Chunk formats
                tokens = chunk.get("tokens", chunk.get("token_count", 0))
                start_token = chunk.get("start_token", 0)  # Default to 0 if not present
                end_token = chunk.get("end_token", tokens)  # Default to token count

                for entity in entities:
                    entity["chunk_id"] = chunk_id
                    entity["document_id"] = document_id
                    entity["chunk_index"] = chunk_index
                    entity["start_token"] = start_token
                    entity["end_token"] = end_token

                # Annotate relations with chunk_id and chunk metadata
                for relation in relations:
                    relation["chunk_id"] = chunk_id
                    relation["document_id"] = document_id
                    relation["chunk_index"] = chunk_index
                    relation["start_token"] = start_token
                    relation["end_token"] = end_token

                all_entities.extend(entities)
                all_relations.extend(relations)

                logger.info(
                    "chunk_extraction_complete",
                    chunk_id=chunk_id[:8],
                    entities_found=len(entities),
                    relations_found=len(relations),
                )

            except Exception as e:
                logger.error(
                    "chunk_extraction_failed",
                    chunk_id=chunk_id[:8],
                    chunk_index=chunk_index,
                    error=str(e),
                )
                # Continue with next chunk (don't fail entire document)
                continue

        # Step 4: Calculate statistics
        extraction_time = time.time() - start_time

        stats = {
            "total_chunks": len(chunks),
            "total_entities": len(all_entities),
            "total_relations": len(all_relations),
            "avg_entities_per_chunk": len(all_entities) / len(chunks) if chunks else 0,
            "avg_relations_per_chunk": len(all_relations) / len(chunks) if chunks else 0,
            "extraction_time_seconds": extraction_time,
        }

        logger.info(
            "per_chunk_extraction_complete",
            document_id=document_id,
            **stats,
        )

        return {
            "chunks": chunks,
            "entities": all_entities,
            "relations": all_relations,
            "stats": stats,
        }

    def _convert_chunks_to_lightrag_format(
        self, chunks: list[dict[str, Any]], document_id: str
    ) -> list[dict[str, Any]]:
        """Convert chunks to LightRAG ainsert_custom_kg format.

        Sprint 30 FIX: Converts chunks to format expected by LightRAG's ainsert_custom_kg()
        to populate chunk_to_source_map and prevent UNKNOWN source_id warnings.

        LightRAG expects:
        {
            "content": str,      # Chunk text
            "source_id": str,    # Unique identifier for this chunk (will be the KEY in chunk_to_source_map)
            "file_path": str,    # Document provenance
        }

        Args:
            chunks: list of chunk dictionaries from _chunk_text_with_metadata()
            document_id: Document ID for file_path

        Returns:
            list of chunks in LightRAG ainsert_custom_kg format
        """
        logger.info("converting_chunks_to_lightrag", count=len(chunks), document_id=document_id)

        lightrag_chunks = []

        for chunk in chunks:
            # Use chunk_id as source_id - this will be the KEY in chunk_to_source_map
            chunk_id = chunk.get("chunk_id", f"chunk_{chunk.get('chunk_index', 0)}")

            lightrag_chunk = {
                "content": chunk.get("text", ""),  # LightRAG expects "content" not "text"
                "source_id": chunk_id,  # This becomes the KEY in chunk_to_source_map
                "file_path": document_id,
            }
            lightrag_chunks.append(lightrag_chunk)

        logger.info(
            "chunks_converted",
            original_count=len(chunks),
            converted_count=len(lightrag_chunks),
        )

        return lightrag_chunks

    def _convert_entities_to_lightrag_format(
        self,
        entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert Three-Phase entities to LightRAG format.

        Sprint 14 Feature 14.1 - Phase 3: Entity Format Conversion
        Sprint 32 FIX: Handle both "name" (Three-Phase) and "entity_name" (LLMExtractionPipeline) keys

        Input formats (both supported):
        - Three-Phase: {"name": "...", "type": "..."}
        - LLMExtractionPipeline: {"entity_name": "...", "entity_type": "..."}

        LightRAG Format:
        {
            "entity_name": "Entity Name",
            "entity_type": "PERSON",
            "description": "...",
            "source_id": "abc123...",
            "file_path": "docs/file.md"
        }

        Args:
            entities: list of entities from extraction pipeline

        Returns:
            list of entities in LightRAG format
        """
        logger.info("converting_entities_to_lightrag", count=len(entities))

        lightrag_entities = []

        for entity in entities:
            # Sprint 32 FIX: Handle both "name" and "entity_name" keys
            # LLMExtractionPipeline uses "entity_name", Three-Phase uses "name"
            entity_name = entity.get("name", entity.get("entity_name", "UNKNOWN"))
            # Sprint 30: Ensure source_id is never empty (LightRAG treats "" as UNKNOWN)
            # Use chunk_id if available, otherwise fallback to document_id
            chunk_id = entity.get("chunk_id", "")
            document_id = entity.get("document_id", "")
            source_id = chunk_id if chunk_id else document_id

            # Sprint 30: Debug logging to understand UNKNOWN source_id warnings
            if not source_id or source_id == "UNKNOWN":
                logger.warning(
                    "entity_missing_source_id",
                    entity_name=entity_name,
                    chunk_id=chunk_id,
                    document_id=document_id,
                    has_chunk_id=bool(chunk_id),
                    entity_keys=list(entity.keys()),
                )

            # Sprint 32 FIX: Handle both "type" and "entity_type" keys
            entity_type = entity.get("type", entity.get("entity_type", "UNKNOWN"))

            lightrag_entity = {
                # LightRAG uses both entity_name (input) and entity_id (storage)
                "entity_name": entity_name,
                "entity_id": entity_name,  # Same as entity_name
                "entity_type": entity_type,
                "description": entity.get("description", ""),
                "source_id": source_id,  # Sprint 30: Never empty, fallback to document_id
                "file_path": document_id,  # Sprint 30: Use document_id for file_path
                # Preserve additional provenance metadata
                "chunk_index": entity.get("chunk_index"),
                "start_token": entity.get("start_token"),
                "end_token": entity.get("end_token"),
            }
            lightrag_entities.append(lightrag_entity)

        logger.info(
            "entities_converted",
            original_count=len(entities),
            converted_count=len(lightrag_entities),
        )

        return lightrag_entities

    def _convert_relations_to_lightrag_format(
        self,
        relations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert Three-Phase relations to LightRAG format.

        Sprint 14 Feature 14.1 - Phase 4: Relation Format Conversion

        Three-Phase Format:
        {
            "source": "Entity A",
            "target": "Entity B",
            "type": "WORKS_WITH",
            "description": "...",
            "confidence": 0.95,
            "chunk_id": "abc123...",
            "document_id": "docs/file.md",
            "chunk_index": 0,
            "start_token": 0,
            "end_token": 600
        }

        LightRAG Format:
        {
            "src_id": "Entity A",
            "tgt_id": "Entity B",
            "description": "...",
            "keywords": "WORKS_WITH",
            "weight": 0.95,
            "source_id": "abc123...",
            "file_path": "docs/file.md"
        }

        Args:
            relations: list of relations from Three-Phase Pipeline

        Returns:
            list of relations in LightRAG format
        """
        logger.info("converting_relations_to_lightrag", count=len(relations))

        lightrag_relations = []

        for relation in relations:
            # Extract relation type for keywords
            rel_type = relation.get("type", "RELATED_TO")
            # Sprint 30: Ensure source_id is never empty (LightRAG treats "" as UNKNOWN)
            # Use chunk_id if available, otherwise fallback to document_id
            chunk_id = relation.get("chunk_id", "")
            document_id = relation.get("document_id", "")
            source_id = chunk_id if chunk_id else document_id

            lightrag_relation = {
                "src_id": relation.get("source", "UNKNOWN"),
                "tgt_id": relation.get("target", "UNKNOWN"),
                "description": relation.get("description", ""),
                "keywords": rel_type,  # LightRAG expects string or list
                "weight": relation.get("confidence", 1.0),
                "source_id": source_id,  # Sprint 30: Never empty, fallback to document_id
                "file_path": document_id,  # Sprint 30: Use document_id for file_path
                # Preserve additional provenance metadata
                "chunk_index": relation.get("chunk_index"),
                "start_token": relation.get("start_token"),
                "end_token": relation.get("end_token"),
            }
            lightrag_relations.append(lightrag_relation)

        logger.info(
            "relations_converted",
            original_count=len(relations),
            converted_count=len(lightrag_relations),
        )

        return lightrag_relations

    async def _store_chunks_and_provenance_in_neo4j(
        self,
        chunks: list[dict[str, Any]],
        entities: list[dict[str, Any]],
    ) -> None:
        """Store chunk nodes and MENTIONED_IN relationships in Neo4j.

        Sprint 14 Feature 14.1 - Phase 5: Neo4j Integration

        Creates Neo4j schema:
        - :chunk nodes with text, tokens, document_id, chunk_index metadata
        - MENTIONED_IN relationships from :base entities to :chunk nodes

        Args:
            chunks: list of chunk metadata from _chunk_text_with_metadata()
            entities: list of entities in LightRAG format (with source_id=chunk_id)
        """
        await self._ensure_initialized()

        if not self.rag or not self.rag.chunk_entity_relation_graph:
            logger.error("neo4j_storage_not_initialized", hint="Call _ensure_initialized() first")
            raise RuntimeError("Neo4j storage not initialized")

        logger.info(
            "storing_chunks_and_provenance",
            total_chunks=len(chunks),
            total_entities=len(entities),
        )

        try:
            # Get Neo4j driver from LightRAG
            graph = self.rag.chunk_entity_relation_graph
            if not hasattr(graph, "_driver"):
                logger.error("neo4j_driver_not_found")
                raise RuntimeError("Neo4j driver not available")

            # Use Neo4j driver for direct operations
            async with graph._driver.session() as session:

                # Step 1: Create :chunk nodes
                for chunk in chunks:
                    chunk_id = chunk["chunk_id"]

                    # Extract token positions (Sprint 16: handle both old and new Chunk formats)
                    # Old format has start_token/end_token, new format has token_count
                    tokens = chunk.get("tokens", chunk.get("token_count", 0))
                    start_token = chunk.get("start_token", 0)  # Default to 0 if not present
                    end_token = chunk.get("end_token", tokens)  # Default to token count

                    # Create chunk node
                    await session.run(
                        """
                        MERGE (c:chunk {chunk_id: $chunk_id})
                        SET c.text = $text,
                            c.document_id = $document_id,
                            c.chunk_index = $chunk_index,
                            c.tokens = $tokens,
                            c.start_token = $start_token,
                            c.end_token = $end_token,
                            c.created_at = datetime()
                        """,
                        chunk_id=chunk_id,
                        text=chunk.get("text", chunk.get("content", "")),  # Handle both formats
                        document_id=chunk["document_id"],
                        chunk_index=chunk["chunk_index"],
                        tokens=tokens,
                        start_token=start_token,
                        end_token=end_token,
                    )

                logger.info("chunk_nodes_created", count=len(chunks))

                # Step 1.5: Create :base entity nodes (FIX for missing entity_name bug)
                # These nodes were never being created, causing MENTIONED_IN to fail!
                for entity in entities:
                    entity_id = entity.get("entity_id", "")
                    entity_name = entity.get("entity_name", entity_id)  # Fallback to entity_id
                    entity_type = entity.get("entity_type", "UNKNOWN")

                    if not entity_id:
                        logger.warning("entity_missing_id", entity=entity)
                        continue

                    # Create dynamic label based on entity type (e.g., :base:ORGANIZATION)
                    # This matches the label structure seen in Neo4j (base:ORGANIZATION, etc.)
                    labels_str = f"base:{entity_type}"

                    await session.run(
                        f"""
                        MERGE (e:{labels_str} {{entity_id: $entity_id}})
                        SET e.entity_name = $entity_name,
                            e.entity_type = $entity_type,
                            e.description = $description,
                            e.source_id = $source_id,
                            e.file_path = $file_path,
                            e.chunk_index = $chunk_index,
                            e.created_at = datetime()
                        """,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        entity_type=entity_type,
                        description=entity.get("description", ""),
                        source_id=entity.get("source_id", ""),
                        file_path=entity.get("file_path", ""),
                        chunk_index=entity.get("chunk_index", 0),
                    )

                logger.info("entity_nodes_created", count=len(entities))

                # Step 2: Create MENTIONED_IN relationships
                # Group entities by chunk_id for efficient batch creation
                entities_by_chunk = {}
                for entity in entities:
                    chunk_id = entity.get("source_id", "")
                    if chunk_id:
                        if chunk_id not in entities_by_chunk:
                            entities_by_chunk[chunk_id] = []
                        # LightRAG uses "entity_id" not "entity_name"
                        entities_by_chunk[chunk_id].append(entity["entity_id"])

                mentioned_in_count = 0
                for chunk_id, entity_ids in entities_by_chunk.items():
                    # Create MENTIONED_IN for all entities in this chunk
                    await session.run(
                        """
                        UNWIND $entity_ids AS entity_id
                        MATCH (e:base {entity_id: entity_id})
                        MATCH (c:chunk {chunk_id: $chunk_id})
                        MERGE (e)-[r:MENTIONED_IN]->(c)
                        SET r.created_at = datetime()
                        """,
                        chunk_id=chunk_id,
                        entity_ids=entity_ids,
                    )
                    mentioned_in_count += len(entity_ids)

                logger.info("mentioned_in_relationships_created", count=mentioned_in_count)

            logger.info(
                "chunks_and_provenance_stored_successfully",
                chunks=len(chunks),
                entities=len(entities),
                relationships=mentioned_in_count,
            )

        except Exception as e:
            logger.error(
                "store_chunks_and_provenance_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def insert_documents_optimized(
        self,
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Insert documents using Three-Phase Pipeline with Graph-based Provenance.

        Sprint 14 Feature 14.1 - Phase 7: Main Integration Method

        This method provides an optimized alternative to insert_documents() that:
        1. Uses Three-Phase Pipeline (SpaCy + Dedup + Gemma) for fast extraction
        2. Chunks documents for precise provenance tracking
        3. Stores chunk nodes and MENTIONED_IN relationships in Neo4j
        4. Leverages LightRAG embeddings for query compatibility

        Performance: ~15-17s per document (vs >300s with LightRAG's llama3.2:3b)
        Quality: 144% entity accuracy, 123% relation accuracy, 28.6% deduplication

        Args:
            documents: list of documents with 'text' and optional 'metadata' fields
                      Each document should have: {"text": "...", "id": "doc_123"}

        Returns:
            Batch insertion result with:
            - total: Total documents processed
            - success: Successfully inserted documents
            - failed: Failed documents
            - stats: Aggregate statistics (entities, relations, chunks)
            - results: Per-document results

        Example:
            >>> wrapper = LightRAGWrapper()
            >>> results = await wrapper.insert_documents_optimized([
            ...     {"text": "AEGIS RAG is a hybrid system...", "id": "doc_001"}
            ... ])
            >>> results["stats"]["total_entities"]
            42
        """
        await self._ensure_initialized()

        logger.info("insert_documents_optimized_start", count=len(documents))

        total_start = time.time()
        results = []
        aggregate_stats = {
            "total_chunks": 0,
            "total_entities": 0,
            "total_relations": 0,
            "total_mentioned_in": 0,
        }

        for i, doc in enumerate(documents):
            doc_start = time.time()

            try:
                # Validate document
                text = doc.get("text", "")
                doc_id = doc.get("id", f"doc_{i}")

                if not text:
                    logger.warning("empty_document", index=i, doc_id=doc_id)
                    results.append(
                        {"index": i, "doc_id": doc_id, "status": "skipped", "reason": "empty_text"}
                    )
                    continue

                logger.info(
                    "processing_document",
                    index=i,
                    doc_id=doc_id,
                    text_length=len(text),
                )

                # PHASE 1-2: Extract per-chunk with Three-Phase Pipeline
                extraction_result = await self._extract_per_chunk_with_three_phase(
                    document_text=text,
                    document_id=doc_id,
                )

                chunks = extraction_result["chunks"]
                entities = extraction_result["entities"]
                relations = extraction_result["relations"]

                # PHASE 3-4: Convert to LightRAG format
                lightrag_entities = self._convert_entities_to_lightrag_format(entities)
                lightrag_relations = self._convert_relations_to_lightrag_format(relations)
                lightrag_chunks = self._convert_chunks_to_lightrag_format(chunks, doc_id)

                # PHASE 6: Insert into LightRAG (embeddings + storage)
                # Use ainsert_custom_kg to insert pre-extracted entities/relations
                # Sprint 30 FIX: Include chunks to populate chunk_to_source_map
                if hasattr(self.rag, "ainsert_custom_kg"):
                    await self.rag.ainsert_custom_kg(
                        custom_kg={
                            "chunks": lightrag_chunks,
                            "entities": lightrag_entities,
                            "relations": lightrag_relations,
                        },
                        full_doc_id=doc_id,
                    )
                    logger.info(
                        "lightrag_custom_kg_inserted",
                        chunks=len(lightrag_chunks),
                        entities=len(lightrag_entities),
                        relations=len(lightrag_relations),
                    )
                else:
                    # Fallback: Use regular ainsert (less optimal)
                    logger.warning(
                        "ainsert_custom_kg_unavailable", fallback="using_regular_ainsert"
                    )
                    await self.rag.ainsert(text)

                # PHASE 5: Store chunks and provenance in Neo4j
                await self._store_chunks_and_provenance_in_neo4j(
                    chunks=chunks,
                    entities=lightrag_entities,
                )

                # Calculate document stats
                doc_time = time.time() - doc_start

                doc_result = {
                    "index": i,
                    "doc_id": doc_id,
                    "status": "success",
                    "chunks": len(chunks),
                    "entities": len(entities),
                    "relations": len(relations),
                    "time_seconds": doc_time,
                }

                results.append(doc_result)

                # Update aggregate stats
                aggregate_stats["total_chunks"] += len(chunks)
                aggregate_stats["total_entities"] += len(entities)
                aggregate_stats["total_relations"] += len(relations)
                aggregate_stats["total_mentioned_in"] += len(entities)  # 1:1 mapping

                logger.info(
                    "document_processed_successfully",
                    **doc_result,
                )

            except Exception as e:
                logger.error(
                    "document_processing_failed",
                    index=i,
                    doc_id=doc.get("id", f"doc_{i}"),
                    error=str(e),
                    error_type=type(e).__name__,
                )
                results.append(
                    {
                        "index": i,
                        "doc_id": doc.get("id", f"doc_{i}"),
                        "status": "error",
                        "error": str(e),
                    }
                )

        # Calculate final statistics
        total_time = time.time() - total_start
        success_count = sum(1 for r in results if r["status"] == "success")
        failed_count = len(documents) - success_count

        logger.info(
            "insert_documents_optimized_complete",
            total=len(documents),
            success=success_count,
            failed=failed_count,
            total_time_seconds=total_time,
            **aggregate_stats,
        )

        return {
            "total": len(documents),
            "success": success_count,
            "failed": failed_count,
            "stats": aggregate_stats,
            "total_time_seconds": total_time,
            "results": results,
        }

    async def _clear_neo4j_database(self) -> None:
        """Clear all data from Neo4j database (for test cleanup).

        Sprint 11: Used by pytest fixtures to ensure test isolation.
        Deletes all nodes and relationships from the knowledge graph.
        """
        await self._ensure_initialized()

        if not self.rag or not self.rag.chunk_entity_relation_graph:
            logger.warning("neo4j_clear_skipped", reason="graph_not_initialized")
            return

        try:
            # Get Neo4j driver from LightRAG's graph instance
            graph = self.rag.chunk_entity_relation_graph
            if hasattr(graph, "_driver"):
                async with graph._driver.session() as session:
                    # Delete all nodes and relationships
                    await session.run("MATCH (n) DETACH DELETE n")
                    logger.info("neo4j_database_cleared")
            else:
                logger.warning("neo4j_clear_skipped", reason="no_driver_found")
        except Exception as e:
            logger.error("neo4j_clear_failed", error=str(e))
            # Don't raise - cleanup is best-effort


# Global instance (singleton pattern)
_lightrag_client: LightRAGClient | None = None


def get_lightrag_client() -> LightRAGClient:
    """Get global LightRAG client instance (singleton).

    Returns:
        LightRAGClient instance (renamed from LightRAGWrapper in Sprint 25)
    """
    global _lightrag_client
    if _lightrag_client is None:
        _lightrag_client = LightRAGClient()
    return _lightrag_client


async def get_lightrag_client_async() -> LightRAGClient:
    """Get global LightRAG client instance (singleton) - async version.

    Ensures LightRAG is properly initialized before returning.

    Returns:
        LightRAGClient instance (renamed from LightRAGWrapper in Sprint 25)
    """
    client = get_lightrag_client()
    await client._ensure_initialized()
    return client


# ============================================================================
# Backward Compatibility Aliases (Sprint 25 Feature 25.9)
# ============================================================================
# Deprecation period: Sprint 25-26
LightRAGWrapper = LightRAGClient
get_lightrag_wrapper = get_lightrag_client
get_lightrag_wrapper_async = get_lightrag_client_async
