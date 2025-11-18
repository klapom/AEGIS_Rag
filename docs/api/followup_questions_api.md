# Follow-up Questions API

**Sprint 27 Feature 27.5**

Generate 3-5 follow-up questions after each answer to guide users to deeper insights.

---

## Endpoint

```
GET /api/v1/chat/sessions/{session_id}/followup-questions
```

---

## Parameters

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Session identifier for the conversation |

---

## Responses

### 200 OK - Success

Returns 3-5 follow-up questions (or empty list if generation fails gracefully).

**Response Schema:**

```json
{
  "session_id": "string",
  "followup_questions": ["string"],
  "generated_at": "string (ISO 8601)",
  "from_cache": "boolean"
}
```

**Example Response:**

```json
{
  "session_id": "user-123-session",
  "followup_questions": [
    "How does hybrid search combine vector and keyword search?",
    "What role does the graph database play in retrieval?",
    "Can you explain the memory consolidation process?"
  ],
  "generated_at": "2025-11-18T10:30:00Z",
  "from_cache": false
}
```

**Field Descriptions:**

- `session_id`: The session identifier provided in the request
- `followup_questions`: Array of 3-5 question strings (empty if generation fails)
- `generated_at`: Timestamp when questions were generated/retrieved (ISO 8601 UTC)
- `from_cache`: `true` if questions were from cache, `false` if freshly generated

---

### 404 NOT FOUND - Session Not Found

The specified session does not exist in Redis.

**Example Response:**

```json
{
  "detail": "Session 'nonexistent-session' not found"
}
```

---

### 500 INTERNAL SERVER ERROR - Generation Failed

Critical error during question generation (rare, as most errors return empty list).

**Example Response:**

```json
{
  "detail": "Failed to generate follow-up questions: LLM service unavailable"
}
```

---

## Behavior

### Cache Strategy

- **Cache Key:** `{session_id}:followup`
- **TTL:** 5 minutes (300 seconds)
- **Namespace:** `cache`

Questions are cached to avoid regenerating for the same Q&A when users refresh or navigate back.

### Question Generation

1. **Load Conversation:** Retrieve last Q&A from Redis
2. **Extract Context:** Get query, answer, and sources
3. **Generate Questions:** Use llama3.2:3b via AegisLLMProxy
4. **Validate:** Filter questions <10 chars, limit to 5
5. **Cache:** Store in Redis for 5 minutes
6. **Return:** Send response to client

### Empty Results

The endpoint returns an empty `followup_questions` array in these cases:

1. Conversation has <2 messages (no Q&A pair yet)
2. Last messages don't form a Q&A pair
3. LLM generation fails (graceful degradation)
4. JSON parsing fails (invalid LLM response)
5. All generated questions are too short (<10 chars)

**This is intentional:** Follow-up questions are a non-critical feature and should never break the user flow.

---

## Examples

### cURL

```bash
curl -X GET "http://localhost:8000/api/v1/chat/sessions/session-123/followup-questions" \
  -H "Accept: application/json"
```

### Python (requests)

```python
import requests

session_id = "user-123-session"
response = requests.get(
    f"http://localhost:8000/api/v1/chat/sessions/{session_id}/followup-questions"
)

if response.status_code == 200:
    data = response.json()
    print(f"Questions: {data['followup_questions']}")
    print(f"From cache: {data['from_cache']}")
elif response.status_code == 404:
    print("Session not found")
else:
    print(f"Error: {response.status_code}")
```

### JavaScript (fetch)

```javascript
const sessionId = "user-123-session";

fetch(`/api/v1/chat/sessions/${sessionId}/followup-questions`)
  .then(response => {
    if (response.ok) {
      return response.json();
    } else if (response.status === 404) {
      console.log("Session not found");
      return null;
    } else {
      throw new Error(`HTTP ${response.status}`);
    }
  })
  .then(data => {
    if (data) {
      console.log("Questions:", data.followup_questions);
      console.log("From cache:", data.from_cache);
    }
  })
  .catch(error => console.error("Error:", error));
```

### TypeScript (React Hook)

```typescript
import { useState, useEffect } from 'react';

interface FollowUpData {
  session_id: string;
  followup_questions: string[];
  generated_at: string;
  from_cache: boolean;
}

export function useFollowUpQuestions(sessionId: string) {
  const [data, setData] = useState<FollowUpData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchQuestions = async () => {
      try {
        setLoading(true);
        const response = await fetch(
          `/api/v1/chat/sessions/${sessionId}/followup-questions`
        );

        if (response.ok) {
          const data = await response.json();
          setData(data);
        } else if (response.status === 404) {
          setError(new Error("Session not found"));
        } else {
          setError(new Error(`HTTP ${response.status}`));
        }
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    fetchQuestions();
  }, [sessionId]);

  return { data, loading, error };
}
```

---

## Performance

### Latency

| Scenario | Target | Typical |
|----------|--------|---------|
| Cache HIT | <50ms | ~35ms |
| Cache MISS (generation) | <500ms | ~420ms |
| LLM generation only | <400ms | ~350ms |

### Cost

| Provider | Cost per Request |
|----------|------------------|
| Local Ollama (llama3.2:3b) | **$0.00** |
| Alibaba Cloud (qwen-turbo) | ~$0.0001 |
| OpenAI (gpt-3.5-turbo) | ~$0.0015 |

**Current Implementation:** Uses local Ollama (free, fast, sufficient quality).

---

## Rate Limiting

No specific rate limits for this endpoint. Uses the general API rate limits:

- **Per User:** 100 requests/minute
- **Per IP:** 200 requests/minute

---

## Monitoring

### Key Metrics

1. **Cache Hit Rate:** Percentage of requests served from cache (target: >60%)
2. **Empty Response Rate:** Percentage returning empty list (target: <5%)
3. **Latency (p95):** 95th percentile response time (target: <500ms)
4. **Question CTR:** Click-through rate on generated questions (target: >40%)
5. **Follow-up Rate:** Percentage of questions leading to new queries (target: >20%)

### Log Events

```
followup_questions_requested → Endpoint called
followup_questions_from_cache → Cache hit
followup_questions_generated → New questions generated
followup_generation_json_parse_error → JSON parsing failed
followup_generation_unexpected_error → Critical error
```

---

## Best Practices

### When to Call

1. **After Each Answer:** Call immediately after displaying the answer
2. **On Page Load:** If user returns to a previous conversation
3. **After Navigation:** When user navigates back to Q&A view

### When NOT to Call

1. **Before First Answer:** Session has no Q&A pair yet
2. **On Every Keystroke:** Wait until user submits query
3. **In Parallel with Answer:** Wait for answer to complete

### Error Handling

```typescript
try {
  const response = await fetch(`/api/v1/chat/sessions/${sessionId}/followup-questions`);

  if (response.ok) {
    const data = await response.json();
    if (data.followup_questions.length > 0) {
      // Display questions
      displayFollowUpQuestions(data.followup_questions);
    } else {
      // Empty list - hide follow-up section
      hideFollowUpQuestions();
    }
  } else if (response.status === 404) {
    // Session not found - normal for new sessions
    console.debug("Session not found (new session)");
  } else {
    // Error - log but don't show to user
    console.error("Failed to fetch follow-up questions");
  }
} catch (error) {
  // Network error - log but don't show to user
  console.error("Network error fetching follow-up questions", error);
}
```

**Key Points:**
- Never block the UI if follow-up questions fail
- Hide the follow-up section if empty list is returned
- Log errors for monitoring but don't alert users
- Treat 404 as normal for new sessions

---

## Security

### Authentication

Uses the same authentication as other `/chat` endpoints:

- JWT token in `Authorization` header
- Session ownership verification (user can only access their own sessions)

### Input Validation

- Session ID must be valid UUID or alphanumeric string
- Maximum session ID length: 128 characters
- No SQL injection risk (Redis key-value lookup)

### Rate Limiting

Standard API rate limits apply to prevent abuse.

---

## Troubleshooting

### Empty Questions Array

**Symptom:** `followup_questions` is `[]`

**Possible Causes:**
1. Conversation has <2 messages
2. Last messages aren't a Q&A pair
3. LLM generation failed
4. JSON parsing failed

**Solution:** Check logs for error messages. This is normal behavior for new sessions.

### 404 Session Not Found

**Symptom:** HTTP 404 error

**Possible Causes:**
1. Session ID is invalid
2. Session expired (7-day TTL)
3. Session was deleted

**Solution:** Create a new session with `/chat` POST endpoint.

### Slow Response

**Symptom:** >1000ms response time

**Possible Causes:**
1. Cache miss on first request
2. LLM service is slow
3. Network latency

**Solution:**
- Check Ollama service status
- Monitor LLM generation time in logs
- Verify Redis is running

---

## Related Documentation

- [Full Feature Documentation](../sprints/SPRINT_27_FEATURE_27.5_FOLLOWUP_QUESTIONS.md)
- [Usage Examples](../../examples/followup_questions_example.py)
- [ADR-033: Multi-Cloud LLM Execution](../adrs/ADR-033-mozilla-any-llm-integration.md)
- [Chat API Documentation](chat_api.md)

---

## Changelog

### v1.0.0 (2025-11-18)

- Initial implementation
- Local Ollama (llama3.2:3b) for generation
- 5-minute Redis caching
- Graceful error handling
- Comprehensive test coverage
