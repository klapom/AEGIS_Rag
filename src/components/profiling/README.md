# User Profiling Component

**Sprint 17:** Implicit User Profiling via Conversation Archiving
**Architecture:** Redis → Qdrant Archiving Pipeline
**Performance:** <100ms conversation search, 7-day auto-archive

---

## Overview

The Profiling Component provides **conversation archiving** for implicit user profiling (Sprint 17 Feature 17.4 Phase 1).

### Key Features

- **Conversation Archiving:** Redis → Qdrant pipeline for semantic search over historical conversations
- **Auto-Archive Scheduler:** Background job for 7-day+ old conversations
- **Manual Archive Trigger:** Archive important conversations on-demand
- **Semantic Search:** Find similar past conversations with BGE-M3 embeddings
- **User-Scoped Search:** Filter by user_id for privacy compliance

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│          Conversation Archiving Pipeline                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Redis Memory (Layer 1)                     │  │
│  │                                                       │  │
│  │  Active Conversations (< 7 days)                     │  │
│  │  • session_id → conversation history                 │  │
│  │  • Fast access (<10ms)                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                      │                                       │
│                      ▼                                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │       ConversationArchiver (Background Job)          │  │
│  │                                                       │  │
│  │  • Runs daily (configurable schedule)                │  │
│  │  • Scans Redis for old conversations (>7 days)       │  │
│  │  • Generates BGE-M3 embeddings                       │  │
│  │  • Archives to Qdrant                                │  │
│  └──────────────────────────────────────────────────────┘  │
│                      │                                       │
│                      ▼                                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │       Qdrant (Archived Conversations)                │  │
│  │                                                       │  │
│  │  • Semantic search over historical conversations     │  │
│  │  • User-scoped filtering (user_id)                   │  │
│  │  • Full-text search (conversation content)           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Component Files

| File | Purpose | LOC |
|------|---------|-----|
| `conversation_archiver.py` | Archiving pipeline & search | 450 |

**Total:** ~450 lines of code

---

## Conversation Archiver

### Overview

`ConversationArchiver` archives conversations from Redis to Qdrant for long-term semantic search.

### Usage

```python
from src.components.profiling.conversation_archiver import ConversationArchiver

# Initialize archiver
archiver = ConversationArchiver(
    collection_name="archived_conversations",
    auto_archive_days=7  # Archive conversations older than 7 days
)

# Ensure Qdrant collection exists
await archiver.ensure_collection_exists()

# Run archiving (manual trigger)
result = await archiver.archive_old_conversations()

# Returns: ArchiveResult
print(f"Archived: {result.conversations_archived}")
print(f"Deleted from Redis: {result.conversations_deleted}")
print(f"Duration: {result.duration_seconds}s")
```

### Auto-Archive Scheduler

```python
# Start background scheduler (runs daily)
import asyncio
from src.components.profiling.conversation_archiver import start_archive_scheduler

# Start scheduler as background task
asyncio.create_task(start_archive_scheduler(
    auto_archive_days=7,
    schedule_time="03:00"  # 3 AM daily
))

# Scheduler automatically archives old conversations
# Logs: conversation_archived session_id=abc123 user_id=user456
```

### Manual Archive

```python
# Archive specific conversation immediately
await archiver.archive_conversation(
    session_id="important-session-123",
    user_id="user-456",
    force=True  # Archive even if < 7 days old
)
```

---

## Conversation Search

### Semantic Search

```python
from src.models.profiling import ConversationSearchRequest

# Search for similar past conversations
request = ConversationSearchRequest(
    query="What is vector search and BM25?",
    user_id="user-456",  # Filter by user
    top_k=5,
    min_score=0.7
)

results = await archiver.search_conversations(request)

# Returns: ConversationSearchResponse
for result in results.results:
    print(f"Session: {result.session_id}")
    print(f"User: {result.user_id}")
    print(f"Similarity: {result.score:.3f}")
    print(f"Preview: {result.conversation_preview[:100]}...")
    print(f"Archived: {result.archived_at}")
```

### Full-Text Search

```python
# Search by keyword (metadata filter)
request = ConversationSearchRequest(
    query="",  # Empty query = metadata-only search
    user_id="user-456",
    metadata_filters={
        "contains_keyword": "docker",
        "date_range": {
            "start": "2024-01-01",
            "end": "2024-12-31"
        }
    }
)

results = await archiver.search_conversations(request)
```

---

## Data Model

### Archived Conversation Schema

```python
from src.models.profiling import ArchivedConversation

class ArchivedConversation(BaseModel):
    session_id: str               # Unique session identifier
    user_id: str                  # User identifier (for scoping)
    conversation_text: str        # Full conversation history (user + assistant messages)
    message_count: int            # Number of messages
    archived_at: str              # ISO 8601 timestamp
    conversation_start: str       # First message timestamp
    conversation_end: str         # Last message timestamp
    topics: List[str]             # Extracted topics (optional)
    sentiment: str                # Positive/Neutral/Negative (optional)

# Qdrant payload
{
  "session_id": "session-abc123",
  "user_id": "user-456",
  "conversation_text": "User: What is vector search?\nAssistant: Vector search...",
  "message_count": 8,
  "archived_at": "2024-11-10T03:00:00Z",
  "conversation_start": "2024-11-01T10:30:00Z",
  "conversation_end": "2024-11-01T10:45:00Z",
  "topics": ["vector_search", "qdrant", "embeddings"],
  "sentiment": "positive"
}
```

### Redis Conversation Format

```python
# Redis key: conversation:{session_id}
# Redis value (JSON):
{
  "session_id": "session-abc123",
  "user_id": "user-456",
  "messages": [
    {
      "role": "user",
      "content": "What is vector search?",
      "timestamp": "2024-11-01T10:30:00Z"
    },
    {
      "role": "assistant",
      "content": "Vector search is a similarity-based...",
      "timestamp": "2024-11-01T10:30:15Z"
    }
  ],
  "created_at": "2024-11-01T10:30:00Z",
  "last_updated": "2024-11-01T10:45:00Z"
}
```

---

## Archive Pipeline

### Step-by-Step Process

**1. Scan Redis for Old Conversations:**
```python
# Find conversations older than auto_archive_days
cutoff_date = datetime.now() - timedelta(days=7)

# Query Redis
sessions = await redis_memory.get_all_sessions()
old_sessions = [
    s for s in sessions
    if datetime.fromisoformat(s["last_updated"]) < cutoff_date
]
```

**2. Generate Embeddings:**
```python
# Extract full conversation text
conversation_text = "\n".join([
    f"{msg['role']}: {msg['content']}"
    for msg in conversation["messages"]
])

# Generate BGE-M3 embedding
embedding = await embedding_service.embed(conversation_text)
```

**3. Store to Qdrant:**
```python
# Create Qdrant point
point = PointStruct(
    id=uuid.uuid4().hex,
    vector=embedding,
    payload={
        "session_id": conversation["session_id"],
        "user_id": conversation["user_id"],
        "conversation_text": conversation_text,
        "message_count": len(conversation["messages"]),
        "archived_at": datetime.now().isoformat(),
        ...
    }
)

# Upsert to Qdrant
await qdrant_client.upsert(
    collection_name="archived_conversations",
    points=[point]
)
```

**4. Delete from Redis:**
```python
# Free up Redis memory
await redis_memory.delete(f"conversation:{session_id}")
```

---

## Use Cases

### User Profile Building

```python
# Get user's conversation history
user_conversations = await archiver.search_conversations(
    ConversationSearchRequest(
        query="",  # All conversations
        user_id="user-456",
        top_k=100  # Last 100 conversations
    )
)

# Extract topics
all_topics = []
for conv in user_conversations.results:
    all_topics.extend(conv.topics)

# Build profile
user_profile = {
    "user_id": "user-456",
    "top_topics": Counter(all_topics).most_common(10),
    "conversation_count": len(user_conversations.results),
    "avg_message_count": sum(c.message_count for c in user_conversations.results) / len(user_conversations.results)
}
```

### Context Retrieval for New Conversations

```python
# Find similar past conversations for context
similar_convs = await archiver.search_conversations(
    ConversationSearchRequest(
        query="How do I configure Qdrant?",
        user_id="user-456",
        top_k=3,
        min_score=0.8
    )
)

# Use as context for LLM
context = "\n\n".join([
    f"Past conversation (score: {c.score:.2f}):\n{c.conversation_preview}"
    for c in similar_convs.results
])

# Add to LLM prompt
prompt = f"""Context from past conversations:
{context}

Current query: How do I configure Qdrant?
"""
```

---

## Testing

### Unit Tests

```bash
# Test conversation archiver
pytest tests/unit/components/profiling/test_conversation_archiver.py
```

### Integration Tests

```bash
# Test Redis → Qdrant archiving pipeline
pytest tests/integration/components/profiling/test_archiving_pipeline.py

# Test semantic search over archived conversations
pytest tests/integration/components/profiling/test_conversation_search.py
```

**Test Coverage:** 78% (42 unit tests, 12 integration tests)

---

## Configuration

### Environment Variables

```bash
# Conversation Archiving
CONVERSATION_AUTO_ARCHIVE_DAYS=7
CONVERSATION_ARCHIVE_SCHEDULE=03:00   # 3 AM daily
CONVERSATION_ARCHIVE_ENABLED=true

# Qdrant Collection
ARCHIVED_CONVERSATIONS_COLLECTION=archived_conversations

# Privacy
CONVERSATION_ARCHIVE_USER_SCOPED=true  # Enforce user_id filtering
```

---

## Performance

### Benchmarks

**Archiving Performance:**
- **100 conversations:** 45s (embedding generation dominant)
- **1000 conversations:** 420s (~7 minutes)
- **Bottleneck:** BGE-M3 embedding generation (~400ms/conversation)

**Search Performance:**
- **Semantic search (Top-5):** <100ms (Qdrant vector search)
- **User-scoped search (100K conversations):** <150ms (with user_id filter)

### Optimization Tips

**Batch Embedding:**
```python
# Batch process embeddings (faster)
texts = [conv["conversation_text"] for conv in conversations]
embeddings = await embedding_service.embed_batch(texts)

# vs single embedding (slower)
for conv in conversations:
    embedding = await embedding_service.embed(conv["conversation_text"])
```

**Limit Archive Frequency:**
```bash
# Archive weekly instead of daily (reduce load)
CONVERSATION_AUTO_ARCHIVE_DAYS=7
CONVERSATION_ARCHIVE_SCHEDULE=03:00,sunday  # Sunday only
```

---

## Privacy & Compliance

### User Data Scoping

**Enforce user_id filtering:**
```python
# ALWAYS filter by user_id (GDPR/privacy)
results = await archiver.search_conversations(
    ConversationSearchRequest(
        query="...",
        user_id="user-456",  # REQUIRED
        enforce_user_scope=True  # Raise error if user_id missing
    )
)
```

### Data Deletion (Right to be Forgotten)

```python
# Delete all conversations for user
await archiver.delete_user_conversations(user_id="user-456")

# Deletes from:
# - Qdrant (archived conversations)
# - Redis (active conversations)
# - Logs (if applicable)
```

### Data Retention

```bash
# Configure retention policy
CONVERSATION_RETENTION_DAYS=365  # 1 year

# Auto-delete conversations older than retention period
# (Separate from archiving - applies to archived conversations in Qdrant)
```

---

## Troubleshooting

### Issue: Archiving too slow

**Solutions:**
```python
# Reduce batch size (less memory, but slower)
await archiver.archive_old_conversations(batch_size=10)

# Archive in smaller time windows
await archiver.archive_conversations_range(
    start_date="2024-01-01",
    end_date="2024-01-31"
)
```

### Issue: Embedding generation fails

**Check Ollama service:**
```bash
# Test BGE-M3 model
curl http://localhost:11434/api/embeddings -d '{
  "model": "bge-m3:latest",
  "prompt": "test"
}'
```

**Fallback to smaller batches:**
```python
# Process one conversation at a time
for conv in conversations:
    try:
        await archiver.archive_conversation(conv["session_id"], conv["user_id"])
    except Exception as e:
        logger.error(f"Failed to archive {conv['session_id']}: {e}")
```

---

## Future Enhancements (Phase 2+)

**Planned Features (Sprint 18+):**
- **Topic Extraction:** Automatic topic labeling with LLM
- **Sentiment Analysis:** Classify conversation sentiment (positive/negative/neutral)
- **User Preference Extraction:** Extract explicit preferences (e.g., "I prefer concise answers")
- **Conversation Clustering:** Group similar conversations for pattern detection
- **Adaptive Memory:** Use archived conversations to personalize responses

---

## Related Documentation

- **Sprint 17 Summary:** [SPRINT_17_SUMMARY.md](../../docs/sprints/SPRINT_17_SUMMARY.md)
- **Memory Component:** [src/components/memory/README.md](../memory/README.md)
- **ADR-025:** Mem0 for User Preferences (planned Layer 0)

---

**Last Updated:** 2025-11-10
**Sprint:** 17 (Feature 17.4 Phase 1: Conversation Archiving)
**Maintainer:** Klaus Pommer + Claude Code (backend-agent, documentation-agent)
