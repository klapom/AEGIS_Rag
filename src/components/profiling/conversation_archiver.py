"""Conversation Archiving Pipeline for User Profiling.

Sprint 17 Feature 17.4 Phase 1: Implicit User Profiling - Conversation Archiving Pipeline

This module provides:
- Background job to archive conversations from Redis → Qdrant
- Manual archiving trigger for important conversations
- Semantic search over archived conversations
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import structlog
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct

from src.components.memory import get_redis_memory
from src.components.shared import get_embedding_service
from src.components.vector_search import get_qdrant_client
from src.core.exceptions import MemoryError, VectorSearchError
from src.models.profiling import (
    ConversationSearchRequest,
    ConversationSearchResponse,
    ConversationSearchResult,
)

logger = structlog.get_logger(__name__)

# Qdrant collection name for archived conversations
ARCHIVED_CONVERSATIONS_COLLECTION = "archived_conversations"
VECTOR_DIMENSION = 1024  # BGE-M3 embedding dimension


class ConversationArchiver:
    """Archive conversations from Redis to Qdrant for semantic search.

    Sprint 17 Feature 17.4 Phase 1: Conversation Archiving Pipeline (7 SP)

    Features:
    - Scans Redis for conversations older than 7 days OR manually archived
    - Generates embeddings from full conversation text
    - Stores in Qdrant with user-scoped metadata
    - Supports semantic search over archived conversations
    """

    def __init__(
        self,
        collection_name: str = ARCHIVED_CONVERSATIONS_COLLECTION,
        auto_archive_days: int = 7,
    ) -> None:
        """Initialize conversation archiver.

        Args:
            collection_name: Qdrant collection name (default: archived_conversations)
            auto_archive_days: Archive conversations older than N days (default: 7)
        """
        self.collection_name = collection_name
        self.auto_archive_days = auto_archive_days

        self.redis_memory = get_redis_memory()
        self.qdrant_client = get_qdrant_client()
        self.embedding_service = get_embedding_service()

        logger.info(
            "conversation_archiver_initialized",
            collection=collection_name,
            auto_archive_days=auto_archive_days,
        )

    async def ensure_collection_exists(self) -> bool:
        """Ensure Qdrant collection for archived conversations exists.

        Returns:
            True if collection exists or was created successfully

        Raises:
            VectorSearchError: If collection creation fails
        """
        try:
            # Check if collection exists
            collection_info = await self.qdrant_client.get_collection_info(self.collection_name)

            if collection_info:
                logger.info(
                    "archived_conversations_collection_exists",
                    collection=self.collection_name,
                    points_count=collection_info.points_count,
                )
                return True

            # Create collection with BGE-M3 dimensions
            await self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vector_size=VECTOR_DIMENSION,
                distance=Distance.COSINE,
                on_disk_payload=True,  # Save RAM by storing payload on disk
            )

            logger.info(
                "archived_conversations_collection_created",
                collection=self.collection_name,
                vector_size=VECTOR_DIMENSION,
            )

            return True

        except Exception as e:
            logger.error(
                "collection_creation_failed", collection=self.collection_name, error=str(e)
            )
            raise VectorSearchError(query="", reason=f"Failed to ensure collection exists: {e}") from e

    async def archive_conversation(
        self,
        session_id: str,
        user_id: str = "default_user",
        reason: str | None = None,
    ) -> str:
        """Archive a single conversation from Redis to Qdrant.

        Args:
            session_id: Session ID to archive
            user_id: User identifier (for filtering in search)
            reason: Optional reason for archiving

        Returns:
            Qdrant point ID

        Raises:
            MemoryError: If conversation not found in Redis
            VectorSearchError: If archiving to Qdrant fails
        """
        try:
            # Ensure collection exists
            await self.ensure_collection_exists()

            # Load conversation from Redis
            conversation_data = await self.redis_memory.retrieve(
                key=session_id, namespace="conversation"
            )

            if not conversation_data:
                raise MemoryError(operation="operation", reason="Conversation '{session_id}' not found in Redis")

            # Extract value from Redis wrapper
            if isinstance(conversation_data, dict) and "value" in conversation_data:
                conversation_data = conversation_data["value"]

            messages = conversation_data.get("messages", [])
            if not messages:
                raise MemoryError(operation="operation", reason="Conversation '{session_id}' has no messages")

            # Generate full conversation text for embedding
            full_text = self._concatenate_messages(messages)

            # Generate embedding
            embedding = await self.embedding_service.embed_single(full_text)

            # Extract metadata
            title = conversation_data.get("title")
            summary = self._generate_summary(messages)
            topics = self._extract_topics(messages)
            created_at = conversation_data.get("created_at", datetime.now(timezone.utc).isoformat())
            archived_at = datetime.now(timezone.utc).isoformat()
            message_count = len(messages)

            # Create Qdrant point
            point_id = str(uuid.uuid4())

            payload = {
                "session_id": session_id,
                "user_id": user_id,
                "title": title,
                "summary": summary,
                "topics": topics,
                "created_at": created_at,
                "archived_at": archived_at,
                "message_count": message_count,
                "full_text": full_text[:1000],  # Store first 1000 chars for snippets
                "messages": messages,  # Store full messages for retrieval
                "reason": reason,
            }

            point = PointStruct(id=point_id, vector=embedding, payload=payload)

            # Upsert to Qdrant
            await self.qdrant_client.upsert_points(
                collection_name=self.collection_name, points=[point]
            )

            logger.info(
                "conversation_archived",
                session_id=session_id,
                user_id=user_id,
                point_id=point_id,
                message_count=message_count,
                reason=reason,
            )

            # Delete from Redis (conversation is now archived)
            await self.redis_memory.delete(key=session_id, namespace="conversation")

            return point_id

        except MemoryError:
            raise
        except Exception as e:
            logger.error("conversation_archiving_failed", session_id=session_id, error=str(e))
            raise VectorSearchError(query="", reason=f"Failed to archive conversation: {e}") from e

    async def search_archived_conversations(
        self, request: ConversationSearchRequest, user_id: str = "default_user"
    ) -> ConversationSearchResponse:
        """Search archived conversations using semantic similarity.

        Args:
            request: Search request with query and filters
            user_id: User ID to filter results (only returns user's own conversations)

        Returns:
            ConversationSearchResponse with matching conversations

        Raises:
            VectorSearchError: If search fails
        """
        try:
            # Ensure collection exists
            await self.ensure_collection_exists()

            # Generate query embedding
            query_embedding = await self.embedding_service.embed_single(request.query)

            # Build filter (user-scoped)
            filter_conditions = [FieldCondition(key="user_id", match=MatchValue(value=user_id))]

            # Add date filters if provided
            if request.date_from:
                filter_conditions.append(
                    FieldCondition(key="created_at", match=MatchValue(value=request.date_from))
                )
            if request.date_to:
                filter_conditions.append(
                    FieldCondition(key="created_at", match=MatchValue(value=request.date_to))
                )

            query_filter = Filter(must=filter_conditions) if filter_conditions else None

            # Search Qdrant
            search_results = await self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=request.limit,
                score_threshold=request.score_threshold,
                query_filter=query_filter,
            )

            # Format results
            results = []
            for result in search_results:
                payload = result["payload"]

                conversation_result = ConversationSearchResult(
                    session_id=payload.get("session_id", ""),
                    title=payload.get("title"),
                    summary=payload.get("summary"),
                    topics=payload.get("topics", []),
                    created_at=payload.get("created_at", ""),
                    archived_at=payload.get("archived_at", ""),
                    message_count=payload.get("message_count", 0),
                    relevance_score=result["score"],
                    snippet=payload.get("full_text", "")[:300],  # First 300 chars
                    metadata={
                        "reason": payload.get("reason"),
                        "user_id": payload.get("user_id"),
                    },
                )
                results.append(conversation_result)

            logger.info(
                "conversation_search_completed",
                query=request.query[:100],
                user_id=user_id,
                results_count=len(results),
            )

            return ConversationSearchResponse(
                query=request.query,
                results=results,
                total_count=len(results),
                search_timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except Exception as e:
            logger.error("conversation_search_failed", query=request.query, error=str(e))
            raise VectorSearchError(query=request.query, reason=f"Failed to search archived conversations: {e}") from e

    async def archive_old_conversations(self, max_conversations: int = 100) -> Dict[str, Any]:
        """Background job: Archive conversations older than configured threshold.

        Args:
            max_conversations: Maximum conversations to archive in one run

        Returns:
            Job status with statistics
        """
        try:
            logger.info("archive_job_started", max_conversations=max_conversations)

            # Get Redis client for scanning
            redis_client = await self.redis_memory.client

            # Scan for conversation keys
            conversation_keys = []
            cursor = 0
            while True:
                cursor, keys = await redis_client.scan(
                    cursor=cursor, match="conversation:*", count=100
                )
                conversation_keys.extend(keys)
                if cursor == 0:
                    break

            logger.info("conversations_found", count=len(conversation_keys))

            # Process each conversation
            archived_count = 0
            failed_count = 0
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.auto_archive_days)

            for key in conversation_keys[:max_conversations]:
                try:
                    # Extract session_id from key
                    session_id = key.split(":", 1)[1] if ":" in key else key

                    # Load conversation metadata
                    conv_data = await self.redis_memory.retrieve(
                        key=session_id, namespace="conversation"
                    )

                    if not conv_data:
                        continue

                    # Extract value from Redis wrapper
                    if isinstance(conv_data, dict) and "value" in conv_data:
                        conv_data = conv_data["value"]

                    # Check if conversation is old enough
                    created_at_str = conv_data.get("created_at")
                    if not created_at_str:
                        continue

                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

                    if created_at < cutoff_date:
                        # Archive this conversation
                        await self.archive_conversation(
                            session_id=session_id,
                            user_id="default_user",  # TODO: Extract from session metadata
                            reason="auto_archived_after_7_days",
                        )
                        archived_count += 1

                        logger.info(
                            "conversation_auto_archived",
                            session_id=session_id,
                            created_at=created_at_str,
                        )

                except Exception as e:
                    logger.error(
                        "conversation_archiving_failed", session_id=session_id, error=str(e)
                    )
                    failed_count += 1

            logger.info(
                "archive_job_completed",
                total_conversations=len(conversation_keys),
                archived=archived_count,
                failed=failed_count,
            )

            return {
                "status": "completed",
                "total_conversations": len(conversation_keys),
                "archived_count": archived_count,
                "failed_count": failed_count,
                "cutoff_date": cutoff_date.isoformat(),
            }

        except Exception as e:
            logger.error("archive_job_failed", error=str(e))
            return {
                "status": "failed",
                "error": str(e),
            }

    def _concatenate_messages(self, messages: list[Dict[str, Any]]) -> str:
        """Concatenate all messages into a single text for embedding.

        Args:
            messages: List of conversation messages

        Returns:
            Concatenated text
        """
        text_parts = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            text_parts.append(f"{role}: {content}")

        return "\n".join(text_parts)

    def _generate_summary(self, messages: list[Dict[str, Any]]) -> str:
        """Generate simple summary from conversation messages.

        Args:
            messages: List of conversation messages

        Returns:
            Summary string (first question + answer count)
        """
        # Get first user message
        first_user_msg = None
        for msg in messages:
            if msg.get("role") == "user":
                first_user_msg = msg.get("content", "")
                break

        if first_user_msg:
            # Return first 100 chars of first question + message count
            return f"{first_user_msg[:100]}... ({len(messages)} messages)"

        return f"Conversation with {len(messages)} messages"

    def _extract_topics(self, messages: list[Dict[str, Any]]) -> list[str]:
        """Extract simple topics from conversation.

        Args:
            messages: List of conversation messages

        Returns:
            List of topic keywords (basic extraction for Phase 1)
        """
        # Phase 1 MVP: Simple keyword extraction
        # Phase 2 will use LLM for topic extraction
        topics = []

        for msg in messages[:3]:  # Check first 3 messages
            content = msg.get("content", "").lower()

            # Simple keyword detection
            if "rag" in content or "retrieval" in content:
                topics.append("RAG Systems")
            if "graph" in content or "neo4j" in content:
                topics.append("Graph Databases")
            if "vector" in content or "embedding" in content:
                topics.append("Vector Search")
            if "llm" in content or "ollama" in content:
                topics.append("Language Models")

        # Deduplicate and limit to 5 topics
        return list(set(topics))[:5]


# Global instance (singleton)
_conversation_archiver: ConversationArchiver | None = None


def get_conversation_archiver() -> ConversationArchiver:
    """Get global ConversationArchiver instance (singleton).

    Returns:
        ConversationArchiver instance
    """
    global _conversation_archiver
    if _conversation_archiver is None:
        _conversation_archiver = ConversationArchiver()
    return _conversation_archiver
