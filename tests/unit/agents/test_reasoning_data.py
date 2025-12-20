"""Unit tests for ReasoningData Builder.

Sprint 48 Feature 48.7: ReasoningData Builder (3 SP)

These tests verify:
- ReasoningData initialization with default empty lists
- add_phase_event method correctly appends events
- to_dict method generates correct summary
- Data accumulation from multiple agents
- Thread safety assumptions (single-threaded per query)
"""

from datetime import datetime

from src.agents.reasoning_data import ReasoningData
from src.models.phase_event import PhaseEvent, PhaseStatus, PhaseType


class TestReasoningDataInitialization:
    """Tests for ReasoningData initialization."""

    def test_default_initialization(self) -> None:
        """Test ReasoningData initializes with empty lists."""
        reasoning = ReasoningData()

        assert reasoning.phase_events == []
        assert reasoning.retrieved_docs == []
        assert reasoning.graph_entities == []
        assert reasoning.memories == []

    def test_initialization_creates_independent_instances(self) -> None:
        """Test each ReasoningData instance has independent lists."""
        reasoning1 = ReasoningData()
        reasoning2 = ReasoningData()

        # Add event to reasoning1
        event = PhaseEvent(
            phase_type=PhaseType.VECTOR_SEARCH,
            status=PhaseStatus.COMPLETED,
            start_time=datetime.now(),
        )
        reasoning1.add_phase_event(event)

        # reasoning2 should still be empty
        assert len(reasoning1.phase_events) == 1
        assert len(reasoning2.phase_events) == 0


class TestAddPhaseEvent:
    """Tests for add_phase_event method."""

    def test_add_single_phase_event(self) -> None:
        """Test adding a single phase event."""
        reasoning = ReasoningData()
        event = PhaseEvent(
            phase_type=PhaseType.VECTOR_SEARCH,
            status=PhaseStatus.COMPLETED,
            start_time=datetime.now(),
            duration_ms=150.0,
        )

        reasoning.add_phase_event(event)

        assert len(reasoning.phase_events) == 1
        assert reasoning.phase_events[0] == event

    def test_add_multiple_phase_events(self) -> None:
        """Test adding multiple phase events in order."""
        reasoning = ReasoningData()
        events = [
            PhaseEvent(
                phase_type=PhaseType.INTENT_CLASSIFICATION,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.now(),
                duration_ms=50.0,
            ),
            PhaseEvent(
                phase_type=PhaseType.VECTOR_SEARCH,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.now(),
                duration_ms=150.0,
            ),
            PhaseEvent(
                phase_type=PhaseType.LLM_GENERATION,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.now(),
                duration_ms=500.0,
            ),
        ]

        for event in events:
            reasoning.add_phase_event(event)

        assert len(reasoning.phase_events) == 3
        assert reasoning.phase_events[0].phase_type == PhaseType.INTENT_CLASSIFICATION
        assert reasoning.phase_events[1].phase_type == PhaseType.VECTOR_SEARCH
        assert reasoning.phase_events[2].phase_type == PhaseType.LLM_GENERATION

    def test_add_phase_event_preserves_order(self) -> None:
        """Test phase events maintain chronological order."""
        reasoning = ReasoningData()
        phase_types = [
            PhaseType.INTENT_CLASSIFICATION,
            PhaseType.VECTOR_SEARCH,
            PhaseType.RERANKING,
            PhaseType.LLM_GENERATION,
        ]

        for phase_type in phase_types:
            event = PhaseEvent(
                phase_type=phase_type,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.now(),
            )
            reasoning.add_phase_event(event)

        # Verify order matches insertion order
        for i, phase_type in enumerate(phase_types):
            assert reasoning.phase_events[i].phase_type == phase_type

    def test_add_phase_event_with_different_statuses(self) -> None:
        """Test adding phase events with various statuses."""
        reasoning = ReasoningData()
        statuses = [
            PhaseStatus.COMPLETED,
            PhaseStatus.FAILED,
            PhaseStatus.SKIPPED,
        ]

        for status in statuses:
            event = PhaseEvent(
                phase_type=PhaseType.VECTOR_SEARCH,
                status=status,
                start_time=datetime.now(),
            )
            reasoning.add_phase_event(event)

        assert len(reasoning.phase_events) == 3
        for i, status in enumerate(statuses):
            assert reasoning.phase_events[i].status == status


class TestRetrievedDataAccumulation:
    """Tests for retrieved data accumulation (docs, entities, memories)."""

    def test_add_retrieved_documents(self) -> None:
        """Test adding retrieved documents."""
        reasoning = ReasoningData()
        docs = [
            {"doc_id": "123", "score": 0.95, "content": "..."},
            {"doc_id": "456", "score": 0.88, "content": "..."},
        ]

        reasoning.retrieved_docs.extend(docs)

        assert len(reasoning.retrieved_docs) == 2
        assert reasoning.retrieved_docs[0]["doc_id"] == "123"

    def test_add_graph_entities(self) -> None:
        """Test adding graph entities."""
        reasoning = ReasoningData()
        entities = [
            {"entity_id": "e1", "type": "ORGANIZATION", "name": "NVIDIA"},
            {"entity_id": "e2", "type": "PRODUCT", "name": "Grace Blackwell"},
        ]

        reasoning.graph_entities.extend(entities)

        assert len(reasoning.graph_entities) == 2
        assert reasoning.graph_entities[0]["name"] == "NVIDIA"

    def test_add_memories(self) -> None:
        """Test adding memories."""
        reasoning = ReasoningData()
        memories = [
            {"memory_id": "m1", "content": "User asked about NVIDIA GPUs", "timestamp": "2025-01-01"},
            {"memory_id": "m2", "content": "User interested in RAG systems", "timestamp": "2025-01-02"},
        ]

        reasoning.memories.extend(memories)

        assert len(reasoning.memories) == 2
        assert reasoning.memories[0]["memory_id"] == "m1"

    def test_mixed_data_accumulation(self) -> None:
        """Test accumulating all types of data together."""
        reasoning = ReasoningData()

        # Add phase events
        reasoning.add_phase_event(
            PhaseEvent(
                phase_type=PhaseType.VECTOR_SEARCH,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.now(),
            )
        )

        # Add documents
        reasoning.retrieved_docs.append({"doc_id": "123"})
        reasoning.retrieved_docs.append({"doc_id": "456"})

        # Add entities
        reasoning.graph_entities.append({"entity_id": "e1"})

        # Add memories
        reasoning.memories.append({"memory_id": "m1"})
        reasoning.memories.append({"memory_id": "m2"})
        reasoning.memories.append({"memory_id": "m3"})

        assert len(reasoning.phase_events) == 1
        assert len(reasoning.retrieved_docs) == 2
        assert len(reasoning.graph_entities) == 1
        assert len(reasoning.memories) == 3


class TestToDictSerialization:
    """Tests for to_dict serialization method."""

    def test_to_dict_empty_reasoning(self) -> None:
        """Test to_dict with empty ReasoningData."""
        reasoning = ReasoningData()
        result = reasoning.to_dict()

        assert result == {
            "phase_events": [],
            "retrieved_docs_count": 0,
            "graph_entities_count": 0,
            "memories_count": 0,
        }

    def test_to_dict_with_phase_events(self) -> None:
        """Test to_dict correctly serializes phase events."""
        reasoning = ReasoningData()
        event = PhaseEvent(
            phase_type=PhaseType.VECTOR_SEARCH,
            status=PhaseStatus.COMPLETED,
            start_time=datetime(2025, 1, 1, 12, 0, 0),
            duration_ms=150.0,
            metadata={"docs_retrieved": 10},
        )
        reasoning.add_phase_event(event)

        result = reasoning.to_dict()

        assert len(result["phase_events"]) == 1
        assert result["phase_events"][0]["phase_type"] == "vector_search"
        assert result["phase_events"][0]["status"] == "completed"
        assert result["phase_events"][0]["duration_ms"] == 150.0
        assert result["phase_events"][0]["metadata"]["docs_retrieved"] == 10

    def test_to_dict_returns_counts_not_full_data(self) -> None:
        """Test to_dict returns counts for docs/entities/memories, not full data."""
        reasoning = ReasoningData()

        # Add various data
        reasoning.retrieved_docs.extend([{"doc_id": f"doc{i}"} for i in range(10)])
        reasoning.graph_entities.extend([{"entity_id": f"e{i}"} for i in range(5)])
        reasoning.memories.extend([{"memory_id": f"m{i}"} for i in range(3)])

        result = reasoning.to_dict()

        # Should return counts, not full arrays
        assert result["retrieved_docs_count"] == 10
        assert result["graph_entities_count"] == 5
        assert result["memories_count"] == 3
        # Should NOT contain "retrieved_docs" key with full array
        assert "retrieved_docs" not in result
        assert "graph_entities" not in result
        assert "memories" not in result

    def test_to_dict_with_multiple_phase_events(self) -> None:
        """Test to_dict with multiple phase events."""
        reasoning = ReasoningData()
        phases = [
            (PhaseType.INTENT_CLASSIFICATION, 50.0),
            (PhaseType.VECTOR_SEARCH, 150.0),
            (PhaseType.RERANKING, 80.0),
            (PhaseType.LLM_GENERATION, 500.0),
        ]

        for phase_type, duration in phases:
            event = PhaseEvent(
                phase_type=phase_type,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.now(),
                duration_ms=duration,
            )
            reasoning.add_phase_event(event)

        result = reasoning.to_dict()

        assert len(result["phase_events"]) == 4
        # Verify phases are in correct order
        assert result["phase_events"][0]["phase_type"] == "intent_classification"
        assert result["phase_events"][1]["phase_type"] == "vector_search"
        assert result["phase_events"][2]["phase_type"] == "reranking"
        assert result["phase_events"][3]["phase_type"] == "llm_generation"

    def test_to_dict_is_json_serializable(self) -> None:
        """Test to_dict output can be JSON-serialized."""
        import json

        reasoning = ReasoningData()
        event = PhaseEvent(
            phase_type=PhaseType.VECTOR_SEARCH,
            status=PhaseStatus.COMPLETED,
            start_time=datetime(2025, 1, 1, 12, 0, 0),
            duration_ms=150.0,
        )
        reasoning.add_phase_event(event)
        reasoning.retrieved_docs.append({"doc_id": "123"})

        result = reasoning.to_dict()

        # Should be JSON-serializable (datetimes handled by Pydantic)
        json_str = json.dumps(result, default=str)
        assert isinstance(json_str, str)
        assert "vector_search" in json_str


class TestReasoningDataUsagePatterns:
    """Tests for typical usage patterns in the RAG pipeline."""

    def test_typical_rag_pipeline_flow(self) -> None:
        """Test simulating a typical RAG pipeline execution."""
        reasoning = ReasoningData()
        base_time = datetime(2025, 1, 1, 12, 0, 0)

        # 1. Intent classification
        reasoning.add_phase_event(
            PhaseEvent(
                phase_type=PhaseType.INTENT_CLASSIFICATION,
                status=PhaseStatus.COMPLETED,
                start_time=base_time,
                duration_ms=50.0,
                metadata={"intent": "hybrid"},
            )
        )

        # 2. Vector search
        reasoning.add_phase_event(
            PhaseEvent(
                phase_type=PhaseType.VECTOR_SEARCH,
                status=PhaseStatus.COMPLETED,
                start_time=base_time,
                duration_ms=150.0,
                metadata={"docs_found": 10},
            )
        )
        reasoning.retrieved_docs.extend([{"doc_id": f"doc{i}"} for i in range(10)])

        # 3. Reranking
        reasoning.add_phase_event(
            PhaseEvent(
                phase_type=PhaseType.RERANKING,
                status=PhaseStatus.COMPLETED,
                start_time=base_time,
                duration_ms=80.0,
                metadata={"reranked_count": 10},
            )
        )

        # 4. LLM generation
        reasoning.add_phase_event(
            PhaseEvent(
                phase_type=PhaseType.LLM_GENERATION,
                status=PhaseStatus.COMPLETED,
                start_time=base_time,
                duration_ms=500.0,
                metadata={"model": "nemotron-no-think", "tokens": 1024},
            )
        )

        result = reasoning.to_dict()

        assert len(result["phase_events"]) == 4
        assert result["retrieved_docs_count"] == 10
        assert result["phase_events"][3]["metadata"]["model"] == "nemotron-no-think"

    def test_failed_phase_handling(self) -> None:
        """Test handling of failed phases in reasoning data."""
        reasoning = ReasoningData()

        # Successful phase
        reasoning.add_phase_event(
            PhaseEvent(
                phase_type=PhaseType.INTENT_CLASSIFICATION,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.now(),
            )
        )

        # Failed phase
        reasoning.add_phase_event(
            PhaseEvent(
                phase_type=PhaseType.GRAPH_QUERY,
                status=PhaseStatus.FAILED,
                start_time=datetime.now(),
                error="Neo4j connection timeout",
            )
        )

        # Recovery phase
        reasoning.add_phase_event(
            PhaseEvent(
                phase_type=PhaseType.LLM_GENERATION,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.now(),
            )
        )

        result = reasoning.to_dict()

        assert len(result["phase_events"]) == 3
        assert result["phase_events"][1]["status"] == "failed"
        assert result["phase_events"][1]["error"] == "Neo4j connection timeout"

    def test_skipped_phases(self) -> None:
        """Test tracking of skipped phases (e.g., graph query not needed)."""
        reasoning = ReasoningData()

        # Intent: vector_only
        reasoning.add_phase_event(
            PhaseEvent(
                phase_type=PhaseType.INTENT_CLASSIFICATION,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.now(),
                metadata={"intent": "vector_only"},
            )
        )

        # Vector search executed
        reasoning.add_phase_event(
            PhaseEvent(
                phase_type=PhaseType.VECTOR_SEARCH,
                status=PhaseStatus.COMPLETED,
                start_time=datetime.now(),
            )
        )

        # Graph query skipped
        reasoning.add_phase_event(
            PhaseEvent(
                phase_type=PhaseType.GRAPH_QUERY,
                status=PhaseStatus.SKIPPED,
                start_time=datetime.now(),
                metadata={"reason": "vector_only_intent"},
            )
        )

        result = reasoning.to_dict()

        skipped_event = [
            e for e in result["phase_events"] if e["status"] == "skipped"
        ]
        assert len(skipped_event) == 1
        assert skipped_event[0]["metadata"]["reason"] == "vector_only_intent"
