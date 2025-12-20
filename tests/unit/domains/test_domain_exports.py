"""Tests for Domain Public API Exports.

Sprint 58: Validates that domain facades export all expected symbols
and maintain backward compatibility with components/ imports.

These tests ensure:
1. All exports from domains/__init__.py are importable
2. Backward compatibility: components/* re-exports work correctly
3. Protocol definitions are properly exposed
"""



class TestLLMIntegrationDomain:
    """Test src.domains.llm_integration exports."""

    def test_import_main_proxy(self):
        """Test main proxy class is importable."""
        from src.domains.llm_integration import AegisLLMProxy, get_aegis_llm_proxy

        assert AegisLLMProxy is not None
        assert callable(get_aegis_llm_proxy)

    def test_import_models(self):
        """Test model classes are importable."""
        from src.domains.llm_integration import (
            LLMResponse,
            LLMTask,
            TaskType,
        )

        assert LLMTask is not None
        assert LLMResponse is not None
        assert TaskType is not None

    def test_import_cost_tracker(self):
        """Test cost tracker is importable."""
        from src.domains.llm_integration import CostTracker, get_cost_tracker

        assert CostTracker is not None
        assert callable(get_cost_tracker)

    def test_import_vlm_factory(self):
        """Test VLM factory exports are importable."""
        from src.domains.llm_integration import (
            VLMBackend,
            get_vlm_client,
        )

        assert VLMBackend is not None
        assert callable(get_vlm_client)

    def test_backward_compat_components_llm_proxy(self):
        """Test backward compatibility via components/llm_proxy."""
        from src.components.llm_proxy import (
            AegisLLMProxy,
            CostTracker,
        )

        # Verify they are the same classes
        from src.domains.llm_integration import (
            AegisLLMProxy as DomainProxy,
        )
        from src.domains.llm_integration import (
            CostTracker as DomainCostTracker,
        )

        assert AegisLLMProxy is DomainProxy
        assert CostTracker is DomainCostTracker


class TestKnowledgeGraphDomain:
    """Test src.domains.knowledge_graph exports."""

    def test_import_protocols(self):
        """Test protocol definitions are importable."""
        from src.domains.knowledge_graph import (
            EntityExtractor,
            GraphStorage,
        )

        # Protocols should be importable
        assert EntityExtractor is not None
        assert GraphStorage is not None

    def test_import_persistence(self):
        """Test persistence exports are importable."""
        from src.domains.knowledge_graph import (
            Neo4jClient,
            get_neo4j_client,
        )

        assert Neo4jClient is not None
        assert callable(get_neo4j_client)

    def test_import_querying(self):
        """Test querying exports are importable."""
        from src.domains.knowledge_graph import (
            LightRAGClient,
            LightRAGWrapper,
        )

        assert LightRAGClient is not None
        assert LightRAGWrapper is not None

    def test_import_extraction(self):
        """Test extraction exports are importable."""
        from src.domains.knowledge_graph import (
            ExtractionService,
            get_extraction_service,
        )

        assert ExtractionService is not None
        assert callable(get_extraction_service)

    def test_import_deduplication(self):
        """Test deduplication exports are importable."""
        from src.domains.knowledge_graph import (
            SYMMETRIC_RELATIONS,
            SemanticDeduplicator,
        )

        assert SemanticDeduplicator is not None
        assert isinstance(SYMMETRIC_RELATIONS, (set, frozenset, list))

    def test_import_communities(self):
        """Test community exports are importable."""
        from src.domains.knowledge_graph import (
            CommunitySummarizer,
            get_community_summarizer,
        )

        assert CommunitySummarizer is not None
        assert callable(get_community_summarizer)

    def test_import_analytics(self):
        """Test analytics exports are importable."""
        from src.domains.knowledge_graph import (
            GraphAnalyticsEngine,
            get_analytics_engine,
        )

        assert GraphAnalyticsEngine is not None
        assert callable(get_analytics_engine)


class TestDocumentProcessingDomain:
    """Test src.domains.document_processing exports."""

    def test_import_protocols(self):
        """Test protocol definitions are importable."""
        from src.domains.document_processing import (
            ChunkingService,
            DocumentParser,
        )

        assert DocumentParser is not None
        assert ChunkingService is not None

    def test_import_parsing(self):
        """Test parsing exports are importable."""
        from src.domains.document_processing import (
            DOCLING_FORMATS,
            DoclingContainerClient,
        )

        assert DoclingContainerClient is not None
        assert isinstance(DOCLING_FORMATS, (set, frozenset, list, tuple))

    def test_import_pipeline(self):
        """Test pipeline exports are importable."""
        from src.domains.document_processing import (
            IngestionState,
            create_initial_state,
            run_ingestion_pipeline,
        )

        assert IngestionState is not None
        assert callable(create_initial_state)
        assert callable(run_ingestion_pipeline)

    def test_import_chunking(self):
        """Test chunking exports are importable."""
        from src.domains.document_processing import (
            SectionMetadata,
            chunking_node,
        )

        assert callable(chunking_node)
        assert SectionMetadata is not None

    def test_import_enrichment(self):
        """Test enrichment exports are importable."""
        from src.domains.document_processing import (
            ImageProcessor,
            image_enrichment_node,
        )

        assert callable(image_enrichment_node)
        assert ImageProcessor is not None


class TestMemoryDomain:
    """Test src.domains.memory exports."""

    def test_import_memory_protocols(self):
        """Test memory domain protocol exports are importable."""
        from src.domains.memory import (
            CacheService,
            ConversationMemory,
            MemoryConsolidation,
            SessionStore,
        )

        # Sprint 57: These are Protocol definitions
        assert ConversationMemory is not None
        assert SessionStore is not None
        assert CacheService is not None
        assert MemoryConsolidation is not None


class TestVectorSearchDomain:
    """Test src.domains.vector_search exports."""

    def test_import_vector_search_protocols(self):
        """Test vector search domain protocol exports are importable."""
        from src.domains.vector_search import (
            EmbeddingService,
            HybridSearchService,
            RerankingService,
            VectorStore,
        )

        # Sprint 57: These are Protocol definitions
        assert EmbeddingService is not None
        assert VectorStore is not None
        assert HybridSearchService is not None
        assert RerankingService is not None


class TestBackwardCompatibility:
    """Test backward compatibility of component imports."""

    def test_components_graph_rag_imports(self):
        """Test components/graph_rag backward compatibility."""
        from src.components.graph_rag import (
            CommunitySummarizer,
            Neo4jClient,
            SemanticDeduplicator,
            get_community_summarizer,
            get_neo4j_client,
        )

        assert Neo4jClient is not None
        assert callable(get_neo4j_client)
        assert CommunitySummarizer is not None
        assert callable(get_community_summarizer)
        assert SemanticDeduplicator is not None

    def test_components_graph_rag_lightrag_imports(self):
        """Test components/graph_rag/lightrag backward compatibility."""
        from src.components.graph_rag.lightrag import (
            LightRAGClient,
            LightRAGWrapper,
            QueryMode,
            get_lightrag_client,
        )

        assert LightRAGClient is not None
        assert LightRAGWrapper is not None
        assert callable(get_lightrag_client)
        assert QueryMode is not None

    def test_components_ingestion_imports(self):
        """Test components/ingestion backward compatibility."""
        from src.components.ingestion import (
            DoclingContainerClient,
            create_initial_state,
            run_ingestion_pipeline,
        )

        assert callable(create_initial_state)
        assert callable(run_ingestion_pipeline)
        assert DoclingContainerClient is not None

    def test_components_memory_imports(self):
        """Test components/memory backward compatibility."""
        from src.components.memory import (
            MemoryRouter,
            RedisMemoryManager,
            get_memory_router,
            get_redis_memory,
        )

        assert callable(get_redis_memory)
        assert MemoryRouter is not None
        assert callable(get_memory_router)
        assert RedisMemoryManager is not None

    def test_components_vector_search_imports(self):
        """Test components/vector_search backward compatibility."""
        from src.components.vector_search import (
            EmbeddingService,
            HybridSearch,
            QdrantClientWrapper,
            get_embedding_service,
            get_qdrant_client,
        )

        assert QdrantClientWrapper is not None
        assert callable(get_qdrant_client)
        assert HybridSearch is not None
        assert EmbeddingService is not None
        assert callable(get_embedding_service)
