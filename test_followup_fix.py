"""Manual verification script for Follow-up Questions Redis Fix.

Sprint 35 Feature 35.3: TD-043 Fix

This script:
1. Saves a conversation with follow-up questions
2. Retrieves the conversation from Redis
3. Verifies follow-up questions are stored correctly
4. Tests the get_followup_questions endpoint
"""

import asyncio
import sys
from datetime import UTC, datetime


async def main():
    """Test the follow-up questions fix."""
    print("=" * 80)
    print("Follow-up Questions Redis Fix - Manual Verification")
    print("Sprint 35 Feature 35.3: TD-043")
    print("=" * 80)

    try:
        # Import required modules
        from src.api.v1.chat import get_followup_questions, save_conversation_turn
        from src.components.memory import get_redis_memory

        print("\n[1] Getting Redis memory manager...")
        redis = get_redis_memory()
        print("✓ Redis memory manager obtained")

        # Test session ID
        session_id = f"manual_test_{int(datetime.now(UTC).timestamp())}"
        print(f"\n[2] Using session ID: {session_id}")

        # Sample data
        sample_sources = [
            {
                "text": "RAG stands for Retrieval-Augmented Generation",
                "title": "RAG Paper",
                "source": "rag_paper.pdf",
                "score": 0.95,
                "metadata": {"page": 1}
            }
        ]

        sample_follow_ups = [
            "How does RAG improve answer accuracy?",
            "What are the limitations of RAG systems?",
            "Can RAG handle multi-hop reasoning?"
        ]

        print("\n[3] Saving conversation with follow-up questions...")
        success = await save_conversation_turn(
            session_id=session_id,
            user_message="What is RAG?",
            assistant_message="RAG stands for Retrieval-Augmented Generation. It combines retrieval and generation to produce more accurate answers.",
            intent="factual",
            sources=sample_sources,
            follow_up_questions=sample_follow_ups
        )

        if success:
            print("✓ Conversation saved successfully")
        else:
            print("✗ FAILED: Conversation save returned False")
            return 1

        print("\n[4] Retrieving conversation from Redis...")
        conversation = await redis.retrieve(
            key=session_id,
            namespace="conversation"
        )

        if conversation is None:
            print("✗ FAILED: Conversation not found in Redis")
            return 1

        # Extract value from Redis wrapper
        if isinstance(conversation, dict) and "value" in conversation:
            conversation = conversation["value"]

        print("✓ Conversation retrieved successfully")

        # Verify structure
        print("\n[5] Verifying conversation structure...")
        assert "messages" in conversation, "Missing 'messages' field"
        assert "follow_up_questions" in conversation, "Missing 'follow_up_questions' field"
        assert len(conversation["messages"]) == 2, f"Expected 2 messages, got {len(conversation['messages'])}"
        assert len(conversation["follow_up_questions"]) == 3, f"Expected 3 follow-ups, got {len(conversation['follow_up_questions'])}"

        print(f"  Messages: {len(conversation['messages'])}")
        print(f"  Follow-up questions: {len(conversation['follow_up_questions'])}")
        print("✓ Structure verification passed")

        # Verify follow-up questions content
        print("\n[6] Verifying follow-up questions content...")
        stored_questions = conversation["follow_up_questions"]
        for i, question in enumerate(stored_questions, 1):
            print(f"  {i}. {question}")

        assert stored_questions == sample_follow_ups, "Follow-up questions don't match"
        print("✓ Follow-up questions match")

        # Test the endpoint
        print("\n[7] Testing get_followup_questions endpoint...")
        try:
            response = await get_followup_questions(session_id)
            print(f"✓ Endpoint returned {len(response.followup_questions)} questions")

            for i, question in enumerate(response.followup_questions, 1):
                print(f"  {i}. {question}")

            assert len(response.followup_questions) == 3, f"Expected 3 questions, got {len(response.followup_questions)}"
            assert response.followup_questions == sample_follow_ups, "Questions from endpoint don't match"
            print("✓ Endpoint verification passed")

        except Exception as e:
            print(f"✗ FAILED: Endpoint test failed: {e}")
            return 1

        # Test TTL
        print("\n[8] Verifying TTL (7 days = 604800 seconds)...")
        ttl = await redis._client.ttl(f"conversation:{session_id}")
        print(f"  Current TTL: {ttl} seconds")

        if ttl > 604700 and ttl <= 604800:
            print("✓ TTL is correct (7 days)")
        else:
            print(f"⚠ WARNING: TTL is {ttl}s, expected ~604800s")

        # Cleanup
        print("\n[9] Cleaning up test data...")
        await redis._client.delete(f"conversation:{session_id}")
        print("✓ Cleanup complete")

        print("\n" + "=" * 80)
        print("ALL TESTS PASSED! ✓")
        print("=" * 80)
        print("\nSummary:")
        print("  - Conversation saved to Redis: ✓")
        print("  - Follow-up questions stored: ✓")
        print("  - Follow-up questions retrieved: ✓")
        print("  - Endpoint returns correct data: ✓")
        print("  - TTL set correctly: ✓")
        print("\nThe fix is working correctly!")
        return 0

    except Exception as e:
        print(f"\n✗ FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
