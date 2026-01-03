# Conversation Archiving API Guide

**Sprint 17 Feature 17.4 Phase 1**
**Quick Reference for Developers**

---

## Overview

The Conversation Archiving API allows you to:
- Archive important conversations for long-term storage
- Search past conversations using semantic similarity
- Automatically archive old conversations (7+ days)

All operations are **user-scoped** for privacy.

---

## Quick Start

### 1. Archive a Conversation

```bash
POST /api/v1/chat/sessions/{session_id}/archive
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/chat/sessions/abc-123/archive
```

**Response:**
```json
{
  "session_id": "abc-123",
  "status": "success",
  "message": "Conversation 'abc-123' archived successfully",
  "archived_at": "2025-10-29T16:00:00Z",
  "qdrant_point_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
```

### 2. Search Archived Conversations

```bash
POST /api/v1/chat/search
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/chat/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does RAG work?",
    "limit": 5,
    "score_threshold": 0.7
  }'
```

**Response:**
```json
{
  "query": "How does RAG work?",
  "results": [
    {
      "session_id": "abc-123",
      "title": "RAG and Vector Search",
      "summary": "What is RAG?... (4 messages)",
      "topics": ["RAG Systems", "Vector Search"],
      "created_at": "2025-10-28T10:00:00Z",
      "archived_at": "2025-10-29T15:30:45Z",
      "message_count": 4,
      "relevance_score": 0.89,
      "snippet": "user: What is RAG?\nassistant: RAG stands for...",
      "metadata": {
        "reason": "manual_archive",
        "user_id": "default_user"
      }
    }
  ],
  "total_count": 1,
  "search_timestamp": "2025-10-29T16:00:00Z"
}
```

---

## API Reference

### Archive Endpoint

**Endpoint:** `POST /api/v1/chat/sessions/{session_id}/archive`

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| session_id | string | Yes | Session ID to archive |

**Request Body:** None

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| session_id | string | Archived session ID |
| status | string | "success" or "failed" |
| message | string | Status message |
| archived_at | string | ISO 8601 timestamp |
| qdrant_point_id | string | UUID of Qdrant vector point |

**Status Codes:**
- `200 OK` - Conversation archived successfully
- `404 NOT FOUND` - Conversation not found in Redis
- `500 INTERNAL SERVER ERROR` - Archiving failed

### Search Endpoint

**Endpoint:** `POST /api/v1/chat/search`

**Request Body:**
```typescript
{
  query: string           // Search query (1-500 chars)
  user_id?: string        // Filter by user (null = current user)
  limit?: number          // Max results (1-20, default: 5)
  score_threshold?: float // Min score (0.0-1.0, default: 0.7)
  date_from?: string      // ISO 8601 date filter (optional)
  date_to?: string        // ISO 8601 date filter (optional)
}
```

**Response Body:**
```typescript
{
  query: string
  results: [
    {
      session_id: string
      title?: string
      summary?: string
      topics: string[]
      created_at: string
      archived_at: string
      message_count: number
      relevance_score: number
      snippet: string
      metadata: {
        reason?: string
        user_id: string
      }
    }
  ]
  total_count: number
  search_timestamp: string
}
```

**Status Codes:**
- `200 OK` - Search completed successfully
- `400 BAD REQUEST` - Invalid query parameters
- `500 INTERNAL SERVER ERROR` - Search failed

---

## Python Client Example

```python
import httpx
import asyncio

async def archive_and_search():
    async with httpx.AsyncClient() as client:
        # Archive a conversation
        archive_response = await client.post(
            "http://localhost:8000/api/v1/chat/sessions/abc-123/archive"
        )
        print(f"Archived: {archive_response.json()}")

        # Search archived conversations
        search_response = await client.post(
            "http://localhost:8000/api/v1/chat/search",
            json={
                "query": "How does RAG work?",
                "limit": 5,
                "score_threshold": 0.7
            }
        )
        results = search_response.json()
        print(f"Found {results['total_count']} conversations")

        for result in results['results']:
            print(f"- {result['title']} (score: {result['relevance_score']:.2f})")

asyncio.run(archive_and_search())
```

---

## JavaScript/TypeScript Client Example

```typescript
async function archiveAndSearch() {
  // Archive a conversation
  const archiveResponse = await fetch(
    'http://localhost:8000/api/v1/chat/sessions/abc-123/archive',
    { method: 'POST' }
  );
  const archiveData = await archiveResponse.json();
  console.log('Archived:', archiveData);

  // Search archived conversations
  const searchResponse = await fetch(
    'http://localhost:8000/api/v1/chat/search',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: 'How does RAG work?',
        limit: 5,
        score_threshold: 0.7
      })
    }
  );
  const searchData = await searchResponse.json();
  console.log(`Found ${searchData.total_count} conversations`);

  searchData.results.forEach(result => {
    console.log(`- ${result.title} (score: ${result.relevance_score.toFixed(2)})`);
  });
}

archiveAndSearch();
```

---

## Common Use Cases

### 1. Save Important Conversation

**Scenario:** User clicks "Archive" button in chat UI

```bash
POST /api/v1/chat/sessions/{session_id}/archive
```

**User sees:** "Conversation archived successfully"

### 2. Find Related Past Conversations

**Scenario:** User asks "What did we discuss about RAG before?"

```bash
POST /api/v1/chat/search
Body: {"query": "RAG discussions", "limit": 3}
```

**System shows:** Top 3 most relevant past conversations

### 3. Browse Conversations by Topic

**Scenario:** User wants to see all graph database conversations

```bash
POST /api/v1/chat/search
Body: {"query": "neo4j graph databases", "limit": 10}
```

**System shows:** All archived conversations about graphs

### 4. Date-Filtered Search

**Scenario:** User wants conversations from last month

```bash
POST /api/v1/chat/search
Body: {
  "query": "RAG",
  "date_from": "2025-09-01T00:00:00Z",
  "date_to": "2025-09-30T23:59:59Z"
}
```

---

## Background Archiving Job

### Automatic Archiving (Phase 1)

Conversations older than **7 days** are automatically archived.

**Trigger Job Manually:**
```python
from src.components.profiling import get_conversation_archiver

archiver = get_conversation_archiver()
result = await archiver.archive_old_conversations(max_conversations=100)

print(f"Archived: {result['archived_count']} conversations")
print(f"Failed: {result['failed_count']} conversations")
```

**Expected Output:**
```json
{
  "status": "completed",
  "total_conversations": 45,
  "archived_count": 12,
  "failed_count": 0,
  "cutoff_date": "2025-10-22T15:30:00Z"
}
```

### Scheduling (TODO - Phase 2)

**Option 1: Cron Job**
```bash
# Run daily at 2 AM
0 2 * * * python -m scripts.run_archive_job
```

**Option 2: APScheduler**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(
    archiver.archive_old_conversations,
    'cron',
    hour=2,
    minute=0
)
scheduler.start()
```

---

## Testing

### Prerequisites

Ensure services are running:
```bash
docker-compose up -d redis qdrant
```

Verify Ollama has BGE-M3 model:
```bash
ollama pull bge-m3
```

### Manual Test

```bash
# 1. Start FastAPI server
uvicorn src.main:app --reload

# 2. Create a test conversation
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is RAG?", "session_id": "test-001"}'

# 3. Archive the conversation
curl -X POST http://localhost:8000/api/v1/chat/sessions/test-001/archive

# 4. Search for the conversation
curl -X POST http://localhost:8000/api/v1/chat/search \
  -H "Content-Type: application/json" \
  -d '{"query": "retrieval augmented", "limit": 3}'
```

### Automated Test

```bash
python scripts/test_conversation_archiving.py
```

**Expected Output:**
```
================================================================================
CONVERSATION ARCHIVING TEST PASSED
================================================================================
✓ Created 3 test conversations
✓ Archived 3 conversations to Qdrant
✓ Verified conversations removed from Redis
✓ Semantic search returned relevant results
✓ Background archiving job processed old conversations
================================================================================
```

---

## Troubleshooting

### Issue: "Collection not found"

**Cause:** Qdrant collection not created

**Solution:** Collection is auto-created on first archive operation. Manually trigger:
```python
from src.components.profiling import get_conversation_archiver
archiver = get_conversation_archiver()
await archiver.ensure_collection_exists()
```

### Issue: "Conversation not found in Redis"

**Cause:** Session ID doesn't exist or already archived

**Solution:** Check session exists before archiving:
```bash
# List active sessions
curl http://localhost:8000/api/v1/chat/sessions
```

### Issue: "No search results"

**Possible Causes:**
1. Score threshold too high (try 0.5 instead of 0.7)
2. Query not semantically similar to archived conversations
3. User filter excluding results (check `user_id`)

**Solution:**
```bash
# Lower threshold and increase limit
curl -X POST http://localhost:8000/api/v1/chat/search \
  -d '{"query": "...", "score_threshold": 0.5, "limit": 10}'
```

### Issue: "Embedding generation timeout"

**Cause:** Ollama service slow or not responding

**Solution:**
```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Restart Ollama if needed
ollama serve
```

---

## Performance Tips

### 1. Optimize Search Queries

- Use specific keywords (better semantic match)
- Lower `score_threshold` for broader results
- Increase `limit` if expecting many matches

### 2. Batch Archiving

Archive multiple conversations efficiently:
```python
for session_id in session_ids:
    await archiver.archive_conversation(session_id, user_id)
```

### 3. Monitor Qdrant Performance

```bash
# Check collection stats
curl http://localhost:6333/collections/archived_conversations
```

---

## Security & Privacy

### User Isolation

- All searches automatically filtered by `user_id`
- No cross-user data leakage
- Archived conversations preserve user ownership

### Data Protection

- Conversations deleted from Redis after archiving
- Single source of truth in Qdrant
- No PII in embeddings (only semantic meaning)

### Authentication (TODO - Phase 2)

Currently uses hardcoded `"default_user"`. Future enhancement:
```python
# Extract from JWT token
user_id = request.user.id

await archiver.archive_conversation(
    session_id=session_id,
    user_id=user_id
)
```

---

## Next Steps

### Phase 2 Enhancements (Planned)

1. **LLM-Based Topic Extraction**
   - Replace keyword matching with Ollama-based classification
   - Multi-label topics with confidence scores

2. **Advanced Summaries**
   - LLM-generated conversation summaries
   - Key points extraction

3. **Conversation Clustering**
   - Group similar conversations by topic
   - Trend analysis over time

4. **Profile-Aware Search**
   - Personalized ranking based on user interests
   - Related conversation recommendations

---

## Support

**Documentation:** `docs/SPRINT_17_FEATURE_17.4_PHASE_1_IMPLEMENTATION.md`
**Test Script:** `scripts/test_conversation_archiving.py`
**API Code:** `src/api/v1/chat.py`
**Core Logic:** `src/components/profiling/conversation_archiver.py`

**Questions?** Contact the AEGIS RAG development team.

---

**Last Updated:** 2025-10-29
**API Version:** v1
**Sprint:** 17
**Feature:** 17.4 Phase 1
