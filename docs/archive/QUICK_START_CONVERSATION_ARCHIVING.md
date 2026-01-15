# ARCHIVED (Sprint 17) - Outdated, see current docs

> This document is archived and obsolete. Conversation archiving functionality may have been superseded by newer memory management features. Please refer to the current documentation for memory management and conversation handling.

---

# Quick Start: Conversation Archiving (Sprint 17 Feature 17.4 Phase 1)

**5-Minute Setup Guide**

---

## What This Does

Automatically archive your conversations to Qdrant for long-term semantic search. Think of it as "Google for your past conversations."

---

## Prerequisites

```bash
# Make sure these are running:
docker-compose up -d redis qdrant

# Verify Ollama has BGE-M3 model:
ollama pull bge-m3
```

---

## Step 1: Start the Server

```bash
# From project root
uvicorn src.main:app --reload
```

Server will be available at `http://localhost:8000`

---

## Step 2: Create a Test Conversation

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is RAG?",
    "session_id": "my-first-test"
  }'
```

You should get back an answer about RAG systems.

---

## Step 3: Archive the Conversation

```bash
curl -X POST http://localhost:8000/api/v1/chat/sessions/my-first-test/archive
```

**Expected Response:**
```json
{
  "session_id": "my-first-test",
  "status": "success",
  "message": "Conversation 'my-first-test' archived successfully",
  "archived_at": "2025-10-29T16:00:00Z",
  "qdrant_point_id": "some-uuid-here"
}
```

---

## Step 4: Search Your Archived Conversations

```bash
curl -X POST http://localhost:8000/api/v1/chat/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "retrieval augmented generation",
    "limit": 3
  }'
```

**Expected Response:**
```json
{
  "query": "retrieval augmented generation",
  "results": [
    {
      "session_id": "my-first-test",
      "title": null,
      "summary": "What is RAG?... (2 messages)",
      "topics": ["RAG Systems"],
      "relevance_score": 0.91,
      "snippet": "user: What is RAG?\nassistant: RAG stands for..."
    }
  ],
  "total_count": 1
}
```

---

## That's It!

You now have:
- ✅ Conversations automatically archived after 7 days
- ✅ Semantic search over all past conversations
- ✅ Privacy-preserving (user-scoped access)

---

## Common Commands

### Archive Specific Conversation
```bash
curl -X POST http://localhost:8000/api/v1/chat/sessions/{session_id}/archive
```

### Search Archived Conversations
```bash
curl -X POST http://localhost:8000/api/v1/chat/search \
  -H "Content-Type: application/json" \
  -d '{"query": "your search query", "limit": 5}'
```

### List Active Sessions (Not Archived Yet)
```bash
curl http://localhost:8000/api/v1/chat/sessions
```

---

## Troubleshooting

### "Collection not found"
**Fix:** Collection is auto-created on first archive. Just retry.

### "Conversation not found in Redis"
**Fix:** Conversation may already be archived or doesn't exist.
```bash
# Check active sessions first
curl http://localhost:8000/api/v1/chat/sessions
```

### "No search results"
**Fix:** Lower the score threshold or increase limit:
```bash
curl -X POST http://localhost:8000/api/v1/chat/search \
  -H "Content-Type: application/json" \
  -d '{"query": "...", "score_threshold": 0.5, "limit": 10}'
```

---

## Python Code Example

```python
import httpx
import asyncio

async def archive_example():
    async with httpx.AsyncClient() as client:
        # Archive
        archive = await client.post(
            "http://localhost:8000/api/v1/chat/sessions/test-123/archive"
        )
        print(archive.json())

        # Search
        search = await client.post(
            "http://localhost:8000/api/v1/chat/search",
            json={"query": "RAG", "limit": 5}
        )
        print(search.json())

asyncio.run(archive_example())
```

---

## What's Next?

- **Full Docs:** `docs/SPRINT_17_FEATURE_17.4_PHASE_1_IMPLEMENTATION.md`
- **API Reference:** `docs/API_CONVERSATION_ARCHIVING.md`
- **Test Script:** `scripts/test_conversation_archiving.py`

---

## Background Job (Optional)

Archive all conversations older than 7 days:

```python
from src.components.profiling import get_conversation_archiver
import asyncio

async def run_archive_job():
    archiver = get_conversation_archiver()
    result = await archiver.archive_old_conversations(max_conversations=100)
    print(f"Archived: {result['archived_count']} conversations")

asyncio.run(run_archive_job())
```

---

**Sprint 17 Feature 17.4 Phase 1**
**Status:** ✅ Ready to Use
**Questions?** See comprehensive docs in `docs/` directory
