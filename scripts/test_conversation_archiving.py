"""Test script for Sprint 17 Feature 17.4 Phase 1 - Conversation Archiving Pipeline.

This script tests:
1. Qdrant collection creation
2. Manual conversation archiving
3. Semantic conversation search
4. Background archiving job
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog

logger = structlog.get_logger(__name__)


async def test_conversation_archiving():
    """Test conversation archiving pipeline."""
    from src.components.memory import get_redis_memory
    from src.components.profiling import get_conversation_archiver
    from src.models.profiling import ConversationSearchRequest

    logger.info("test_conversation_archiving_started")

    # Initialize components
    redis_memory = get_redis_memory()
    archiver = get_conversation_archiver()

    # Step 1: Ensure Qdrant collection exists
    logger.info("step_1_ensure_collection_exists")
    collection_exists = await archiver.ensure_collection_exists()
    assert collection_exists, "Failed to create Qdrant collection"
    logger.info("step_1_completed", collection_exists=collection_exists)

    # Step 2: Create test conversations in Redis
    logger.info("step_2_create_test_conversations")
    test_sessions = []

    # Create 3 test conversations with different topics
    test_conversations = [
        {
            "session_id": str(uuid.uuid4()),
            "messages": [
                {"role": "user", "content": "What is RAG?", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"role": "assistant", "content": "RAG stands for Retrieval-Augmented Generation. It's a technique that combines retrieval of relevant documents with LLM generation.", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"role": "user", "content": "How does vector search work in RAG?", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"role": "assistant", "content": "Vector search uses embeddings to find semantically similar documents. Qdrant stores these vectors for efficient similarity search.", "timestamp": datetime.now(timezone.utc).isoformat()},
            ],
            "title": "RAG and Vector Search",
        },
        {
            "session_id": str(uuid.uuid4()),
            "messages": [
                {"role": "user", "content": "Tell me about Neo4j and graph databases", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"role": "assistant", "content": "Neo4j is a graph database that stores data as nodes and relationships. It's excellent for modeling connected data and knowledge graphs.", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"role": "user", "content": "How do you use Neo4j with LLMs?", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"role": "assistant", "content": "You can use Neo4j to store entity relationships extracted by LLMs, creating a knowledge graph that can be queried for context retrieval.", "timestamp": datetime.now(timezone.utc).isoformat()},
            ],
            "title": "Neo4j and Graph RAG",
        },
        {
            "session_id": str(uuid.uuid4()),
            "messages": [
                {"role": "user", "content": "What are the best practices for chunking documents?", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"role": "assistant", "content": "Good chunking strategies include semantic chunking (respecting document structure), overlapping chunks, and adaptive chunk sizes based on content type.", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"role": "user", "content": "How do you handle code files?", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"role": "assistant", "content": "Code files should be chunked at function/class boundaries to preserve semantic meaning. Use language-specific parsers for better results.", "timestamp": datetime.now(timezone.utc).isoformat()},
            ],
            "title": "Document Chunking Strategies",
        },
    ]

    for conv in test_conversations:
        session_id = conv["session_id"]

        # Store conversation in Redis
        conversation_data = {
            "messages": conv["messages"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "message_count": len(conv["messages"]),
            "title": conv["title"],
        }

        await redis_memory.store(
            key=session_id,
            value=conversation_data,
            ttl_seconds=604800,  # 7 days
            namespace="conversation",
        )

        test_sessions.append(session_id)
        logger.info("test_conversation_created", session_id=session_id, title=conv["title"])

    logger.info("step_2_completed", test_sessions_count=len(test_sessions))

    # Step 3: Archive conversations manually
    logger.info("step_3_archive_conversations")
    archived_point_ids = []

    for session_id in test_sessions:
        point_id = await archiver.archive_conversation(
            session_id=session_id,
            user_id="test_user",
            reason="test_archiving",
        )
        archived_point_ids.append(point_id)
        logger.info("conversation_archived", session_id=session_id, point_id=point_id)

    logger.info("step_3_completed", archived_count=len(archived_point_ids))

    # Step 4: Verify conversations were removed from Redis
    logger.info("step_4_verify_redis_removal")
    for session_id in test_sessions:
        conv_data = await redis_memory.retrieve(key=session_id, namespace="conversation")
        assert conv_data is None, f"Conversation {session_id} still exists in Redis after archiving"
        logger.info("conversation_removed_from_redis", session_id=session_id)

    logger.info("step_4_completed")

    # Step 5: Search archived conversations
    logger.info("step_5_search_archived_conversations")

    # Test search 1: RAG-related query
    search_request_1 = ConversationSearchRequest(
        query="How does retrieval augmented generation work?",
        user_id="test_user",
        limit=5,
        score_threshold=0.3,  # Lower threshold for testing
    )

    results_1 = await archiver.search_archived_conversations(
        request=search_request_1,
        user_id="test_user",
    )

    logger.info(
        "search_completed_1",
        query=search_request_1.query,
        results_count=results_1.total_count,
    )

    assert results_1.total_count > 0, "No results found for RAG query"

    for result in results_1.results:
        logger.info(
            "search_result_1",
            session_id=result.session_id,
            title=result.title,
            relevance_score=result.relevance_score,
            snippet=result.snippet[:100],
        )

    # Test search 2: Graph database query
    search_request_2 = ConversationSearchRequest(
        query="Neo4j knowledge graphs",
        user_id="test_user",
        limit=5,
        score_threshold=0.3,
    )

    results_2 = await archiver.search_archived_conversations(
        request=search_request_2,
        user_id="test_user",
    )

    logger.info(
        "search_completed_2",
        query=search_request_2.query,
        results_count=results_2.total_count,
    )

    assert results_2.total_count > 0, "No results found for Neo4j query"

    for result in results_2.results:
        logger.info(
            "search_result_2",
            session_id=result.session_id,
            title=result.title,
            relevance_score=result.relevance_score,
            snippet=result.snippet[:100],
        )

    # Test search 3: Chunking query
    search_request_3 = ConversationSearchRequest(
        query="document chunking strategies",
        user_id="test_user",
        limit=5,
        score_threshold=0.3,
    )

    results_3 = await archiver.search_archived_conversations(
        request=search_request_3,
        user_id="test_user",
    )

    logger.info(
        "search_completed_3",
        query=search_request_3.query,
        results_count=results_3.total_count,
    )

    assert results_3.total_count > 0, "No results found for chunking query"

    for result in results_3.results:
        logger.info(
            "search_result_3",
            session_id=result.session_id,
            title=result.title,
            relevance_score=result.relevance_score,
            snippet=result.snippet[:100],
        )

    logger.info("step_5_completed")

    # Step 6: Test background archiving job
    logger.info("step_6_test_background_archiving_job")

    # Create an old conversation (simulate conversation from 8 days ago)
    old_session_id = str(uuid.uuid4())
    old_conversation_data = {
        "messages": [
            {"role": "user", "content": "This is an old conversation", "timestamp": datetime.now(timezone.utc).isoformat()},
            {"role": "assistant", "content": "Yes, this should be auto-archived", "timestamp": datetime.now(timezone.utc).isoformat()},
        ],
        "created_at": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "message_count": 2,
        "title": "Old Conversation",
    }

    await redis_memory.store(
        key=old_session_id,
        value=old_conversation_data,
        ttl_seconds=604800,
        namespace="conversation",
    )

    logger.info("old_conversation_created", session_id=old_session_id)

    # Run background archiving job
    job_result = await archiver.archive_old_conversations(max_conversations=100)

    logger.info("background_archiving_job_completed", job_result=job_result)

    assert job_result["status"] == "completed", "Background archiving job failed"
    assert job_result["archived_count"] >= 1, "Old conversation was not archived"

    logger.info("step_6_completed")

    # Summary
    logger.info(
        "test_conversation_archiving_completed",
        test_sessions_count=len(test_sessions),
        archived_count=len(archived_point_ids),
        search_tests_passed=3,
        background_job_passed=True,
    )

    print("\n" + "=" * 80)
    print("CONVERSATION ARCHIVING TEST PASSED")
    print("=" * 80)
    print(f"✓ Created {len(test_sessions)} test conversations")
    print(f"✓ Archived {len(archived_point_ids)} conversations to Qdrant")
    print(f"✓ Verified conversations removed from Redis")
    print(f"✓ Semantic search returned relevant results")
    print(f"✓ Background archiving job processed old conversations")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_conversation_archiving())
