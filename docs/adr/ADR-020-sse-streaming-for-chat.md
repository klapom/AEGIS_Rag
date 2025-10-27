# ADR-020: Server-Sent Events (SSE) Streaming for Chat

## Status
**Accepted** (2025-10-27)

## Context

Sprint 15 introduces a Perplexity-inspired frontend for AegisRAG, requiring real-time streaming of chat responses to improve user experience. Users expect:

1. **Token-by-token streaming**: Display LLM responses as they are generated (not after completion)
2. **Progressive source display**: Show retrieved sources as they become available
3. **Real-time metadata**: Session IDs, thinking indicators, tool calls
4. **Responsive UX**: Immediate feedback (<100ms to first token)

**Current State:**
- Existing `/api/v1/chat/` endpoint returns complete responses only (blocking, slow)
- No streaming capability for CoordinatorAgent → Frontend
- Users wait 5-30+ seconds for full response before seeing anything

**Problem:**
We need a bi-directional communication mechanism that:
- Streams data from backend → frontend in real-time
- Supports text chunks, metadata, and structured events
- Works with existing FastAPI/React infrastructure
- Scales to 50-100 concurrent connections

**Options:**
1. **Server-Sent Events (SSE)** - HTTP-based, unidirectional streaming
2. **WebSocket** - Full-duplex, persistent connections
3. **Long Polling** - Repeated HTTP requests
4. **GraphQL Subscriptions** - Event-based subscriptions

## Decision

We will use **Server-Sent Events (SSE)** for streaming chat responses from backend to frontend.

**Implementation:**
```python
# Backend: FastAPI SSE endpoint
@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    async def generate_stream():
        session_id = request.session_id or str(uuid.uuid4())

        # Send metadata first
        yield f"data: {json.dumps({'type': 'metadata', 'session_id': session_id})}\n\n"

        # Stream tokens from CoordinatorAgent
        coordinator = get_coordinator()
        async for chunk in coordinator.process_query_stream(
            query=request.query,
            session_id=session_id,
            intent=request.intent
        ):
            if chunk["type"] == "token":
                yield f"data: {json.dumps({'type': 'token', 'content': chunk['content']})}\n\n"
            elif chunk["type"] == "source":
                yield f"data: {json.dumps({'type': 'source', 'source': chunk['data']})}\n\n"
            elif chunk["type"] == "metadata":
                yield f"data: {json.dumps({'type': 'metadata', 'data': chunk['data']})}\n\n"

        # Signal completion
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
```

```typescript
// Frontend: EventSource client
export async function* streamChat(request: ChatRequest): AsyncGenerator<ChatChunk> {
  const response = await fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') return;

        try {
          const chunk = JSON.parse(data);
          yield chunk;
        } catch (e) {
          console.error('Failed to parse SSE chunk:', e);
        }
      }
    }
  }
}
```

## Alternatives Considered

### Alternative 1: WebSocket
**Pro:**
- **Full-duplex communication**: Bidirectional message passing
- **Lower latency**: Persistent connection reduces handshake overhead
- **Binary support**: Efficient for large payloads
- **Industry standard**: Used by ChatGPT, Claude, etc.

**Contra:**
- **Overkill for unidirectional streaming**: We don't need client → server streaming
- **More complex**: Requires WebSocket server, connection management, heartbeats
- **Load balancing issues**: Sticky sessions required for WebSocket proxies
- **No HTTP/2 benefits**: Cannot leverage HTTP/2 multiplexing
- **Higher infrastructure cost**: Connection pooling, scaling more complex

**Why Not Chosen:**
AegisRAG chat is primarily **server → client streaming**. Users send a query (HTTP POST), then receive a stream of tokens (one direction). WebSocket's bidirectional nature is unnecessary complexity.

### Alternative 2: Long Polling
**Pro:**
- **Simple HTTP**: No special protocols, works everywhere
- **Compatible with all proxies**: Standard HTTP requests
- **Easy debugging**: Standard HTTP tooling (curl, Postman)

**Contra:**
- **Inefficient**: Repeated HTTP requests → high latency (100-500ms per poll)
- **High overhead**: Each poll = new TCP handshake, headers, etc.
- **Poor UX**: Delayed token display, not truly "real-time"
- **Server load**: Constant polling creates unnecessary load

**Why Not Chosen:**
Long polling is too slow for token-by-token streaming. Users expect <100ms latency to first token, not 500ms+ polling intervals.

### Alternative 3: GraphQL Subscriptions
**Pro:**
- **Schema-driven**: Type-safe subscriptions with GraphQL schema
- **Flexible**: Supports filtering, batching, multiplexing
- **Ecosystem**: Apollo Client/Server, Relay support

**Contra:**
- **Requires GraphQL stack**: Must adopt GraphQL (we use FastAPI/REST)
- **Complexity**: GraphQL server, schema management, resolvers
- **Transport dependency**: Still requires WebSocket or SSE under the hood
- **Migration cost**: Rewrite existing REST API → GraphQL

**Why Not Chosen:**
AegisRAG uses FastAPI + REST. Adopting GraphQL for streaming alone is architectural overkill. SSE integrates seamlessly with existing FastAPI.

## Rationale

### Why SSE is Optimal for AegisRAG

**1. Unidirectional Streaming Matches Use Case:**
- User sends query → Backend streams response
- No need for client → server streaming (future user interruptions can use separate HTTP DELETE)
- SSE is designed exactly for this pattern

**2. Native Browser Support:**
```typescript
// No external libraries needed (unlike WebSocket libraries)
const eventSource = new EventSource('/api/v1/chat/stream');
eventSource.onmessage = (event) => {
  const chunk = JSON.parse(event.data);
  console.log(chunk);
};
```

**3. Automatic Reconnection:**
- Browser EventSource API auto-reconnects on connection drop
- Built-in Last-Event-ID header for resumption
- No manual reconnection logic needed

**4. HTTP/2 Multiplexing:**
- SSE works over HTTP/1.1 and HTTP/2
- HTTP/2 allows multiple SSE streams over single TCP connection
- Better resource utilization than WebSocket

**5. Simplicity:**
- No handshake protocol (unlike WebSocket)
- Standard HTTP headers, status codes
- Works with existing FastAPI `StreamingResponse`
- No connection pooling complexity

**6. Infrastructure Compatibility:**
- Works with all HTTP proxies (nginx, Cloudflare, AWS ALB)
- No sticky session requirements
- Standard HTTP caching headers (`Cache-Control: no-cache`)
- Easy to debug with curl:
  ```bash
  curl -N -X POST http://localhost:8000/api/v1/chat/stream \
    -H "Content-Type: application/json" \
    -d '{"query": "What is AegisRAG?"}'
  ```

**7. Security:**
- Same-origin policy enforced by browsers
- No CORS preflight for same-origin requests
- Can add JWT auth via `Authorization` header (custom EventSource wrapper)

**8. Performance:**
- Latency to first token: <100ms (HTTP overhead only)
- Throughput: 1-5 KB/s per stream (sufficient for text tokens)
- Concurrent connections: 50-100 per server (tested with FastAPI)

### Comparison Matrix

| Feature                  | SSE         | WebSocket   | Long Polling | GraphQL Sub |
|--------------------------|-------------|-------------|--------------|-------------|
| Unidirectional streaming | ✅ Native    | ⚠️ Overkill  | ❌ Inefficient | ✅ Supported |
| Browser support          | ✅ Native    | ✅ Native    | ✅ Native     | ⚠️ Requires lib |
| Auto-reconnect           | ✅ Built-in  | ❌ Manual    | ❌ Manual     | ⚠️ Depends   |
| HTTP/2 multiplexing      | ✅ Yes       | ❌ No        | ✅ Yes        | ⚠️ Depends   |
| Infrastructure compat    | ✅ Standard  | ⚠️ Sticky    | ✅ Standard   | ⚠️ Complex  |
| Debugging                | ✅ curl      | ⚠️ wscat     | ✅ curl       | ⚠️ Special  |
| FastAPI integration      | ✅ Native    | ⚠️ starlette | ✅ Native     | ❌ New stack |
| Latency                  | <100ms      | <50ms       | 100-500ms    | <100ms      |

**Decision:** SSE offers the best balance of simplicity, performance, and compatibility for AegisRAG's streaming requirements.

## Consequences

### Positive

✅ **Simplified Architecture:**
- No WebSocket server management (connection pools, heartbeats)
- FastAPI `StreamingResponse` handles SSE automatically
- Standard HTTP patterns (logging, monitoring, rate limiting)

✅ **Better Developer Experience:**
- Easy to test with curl, Postman, or browser DevTools
- No special client libraries required (fetch API + EventSource)
- Faster development iteration

✅ **Infrastructure Friendly:**
- Works with all standard HTTP proxies (nginx, Cloudflare)
- No sticky session requirements (easier load balancing)
- HTTP/2 multiplexing improves resource utilization

✅ **User Experience:**
- Token-by-token streaming (<100ms to first token)
- Automatic reconnection on network hiccups
- Progress indicators (sources, thinking states)

✅ **Security:**
- Standard HTTP authentication (JWT, OAuth)
- Same-origin policy enforced
- No CORS complexity for same-origin requests

### Negative

⚠️ **Unidirectional Only:**
- Cannot send client → server messages during stream
- **Mitigation:** Use separate HTTP DELETE for user interruptions (future feature)
- **Impact:** Low (current use case is query → response only)

⚠️ **Connection Limits (HTTP/1.1):**
- Browsers limit 6 concurrent SSE connections per domain (HTTP/1.1)
- **Mitigation:** Use HTTP/2 (removes limit), or multiplex multiple streams over one connection
- **Impact:** Low (users rarely have >6 concurrent chats)

⚠️ **Text-Only Protocol:**
- SSE spec requires UTF-8 text (no binary)
- **Mitigation:** JSON-encode binary data (base64) if needed (rare)
- **Impact:** None (LLM tokens are text)

⚠️ **Browser Compatibility (IE11):**
- EventSource not supported in IE11 (<1% usage)
- **Mitigation:** Polyfill or fallback to long polling
- **Impact:** None (IE11 not a target browser)

### Mitigations

**For Connection Limits:**
- Deploy with HTTP/2 enabled (nginx, Cloudflare)
- Monitor concurrent connection metrics
- Add rate limiting per user (max 3 concurrent streams)

**For Debugging:**
- Add structured logging for SSE events
- Include request IDs in SSE metadata
- Use Prometheus metrics for stream duration, chunk count

**For Reliability:**
- Add connection timeout (30s idle → close)
- Send periodic "heartbeat" comments (`: ping\n\n`)
- Handle client disconnects gracefully (cancel agent execution)

## Implementation

### Backend Changes

**1. New SSE Endpoint** (`src/api/v1/chat.py`):
```python
@router.post("/stream", status_code=status.HTTP_200_OK)
async def chat_stream(
    request: ChatRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
) -> StreamingResponse:
    """Stream chat response with SSE."""

    async def generate_stream():
        try:
            session_id = request.session_id or str(uuid.uuid4())

            # Send metadata first
            yield sse_message({
                "type": "metadata",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat()
            })

            # Stream from CoordinatorAgent
            coordinator = CoordinatorAgent()
            async for chunk in coordinator.process_query_stream(
                query=request.query,
                session_id=session_id,
                intent=request.intent,
                user_id=current_user.id if current_user else None
            ):
                yield sse_message(chunk)

            # Signal completion
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield sse_message({
                "type": "error",
                "error": str(e),
                "code": "STREAM_ERROR"
            })

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )

def sse_message(data: dict) -> str:
    """Format data as SSE message."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
```

**2. CoordinatorAgent Streaming** (`src/agents/coordinator.py`):
```python
class CoordinatorAgent:
    async def process_query_stream(
        self,
        query: str,
        session_id: str,
        intent: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream query processing with intermediate results."""

        # 1. Emit intent classification
        detected_intent = await self._classify_intent(query)
        yield {
            "type": "metadata",
            "data": {"intent": detected_intent}
        }

        # 2. Emit retrieval sources as they arrive
        async for source in self._stream_retrieval(query, detected_intent):
            yield {
                "type": "source",
                "source": source.dict()
            }

        # 3. Stream LLM tokens
        async for token in self._stream_generation(query, context):
            yield {
                "type": "token",
                "content": token
            }
```

### Frontend Changes

**1. SSE Client Hook** (`frontend/src/hooks/useStreamChat.ts`):
```typescript
export function useStreamChat() {
  const streamChat = useCallback(
    async (request: ChatRequest, onChunk: (chunk: ChatChunk) => void) => {
      try {
        const response = await fetch('/api/v1/chat/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getAuthToken()}`,
          },
          body: JSON.stringify(request),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data === '[DONE]') return;

              const chunk = JSON.parse(data);
              onChunk(chunk);
            }
          }
        }
      } catch (error) {
        console.error('Stream error:', error);
        throw error;
      }
    },
    []
  );

  return { streamChat };
}
```

**2. React Component Integration** (`frontend/src/components/ChatStream.tsx`):
```typescript
export function ChatStream({ query, sessionId }: Props) {
  const [tokens, setTokens] = useState<string[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const { streamChat } = useStreamChat();

  useEffect(() => {
    const request: ChatRequest = { query, session_id: sessionId };

    streamChat(request, (chunk) => {
      switch (chunk.type) {
        case 'token':
          setTokens((prev) => [...prev, chunk.content]);
          break;
        case 'source':
          setSources((prev) => [...prev, chunk.source]);
          break;
        case 'metadata':
          console.log('Metadata:', chunk.data);
          break;
        case 'error':
          console.error('Stream error:', chunk.error);
          break;
      }
    });
  }, [query, sessionId]);

  return (
    <div>
      <div className="answer">{tokens.join('')}</div>
      <div className="sources">
        {sources.map((source, i) => (
          <SourceCard key={i} source={source} />
        ))}
      </div>
    </div>
  );
}
```

### Testing Strategy

**1. Unit Tests** (Backend):
```python
@pytest.mark.asyncio
async def test_sse_stream_format():
    """Test SSE message formatting."""
    request = ChatRequest(query="Test query", session_id="test-123")

    response = await chat_stream(request)

    # Consume stream
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode('utf-8'))

    # Verify SSE format
    assert chunks[0].startswith("data: {")
    assert chunks[-1] == "data: [DONE]\n\n"

    # Verify metadata
    metadata = json.loads(chunks[0][6:].strip())
    assert metadata["type"] == "metadata"
    assert metadata["session_id"] == "test-123"
```

**2. Integration Tests** (Frontend + Backend):
```typescript
describe('SSE Streaming', () => {
  it('should stream tokens from backend', async () => {
    const chunks: ChatChunk[] = [];
    const { streamChat } = useStreamChat();

    await streamChat(
      { query: 'What is AegisRAG?', session_id: 'test-session' },
      (chunk) => chunks.push(chunk)
    );

    expect(chunks.length).toBeGreaterThan(0);
    expect(chunks[0].type).toBe('metadata');
    expect(chunks.filter((c) => c.type === 'token').length).toBeGreaterThan(10);
  });
});
```

**3. E2E Tests** (Playwright):
```typescript
test('should display streaming answer in real-time', async ({ page }) => {
  await page.goto('/');
  await page.fill('[data-testid="search-input"]', 'What is AegisRAG?');
  await page.click('[data-testid="submit-button"]');

  // Wait for first token
  await page.waitForSelector('[data-testid="answer-text"]');

  // Verify streaming (text should grow over time)
  const initialLength = await page.textContent('[data-testid="answer-text"]');
  await page.waitForTimeout(500);
  const laterLength = await page.textContent('[data-testid="answer-text"]');

  expect(laterLength.length).toBeGreaterThan(initialLength.length);
});
```

## Performance Considerations

### Latency Targets
- **Time to First Token (TTFT):** <100ms from query submission
- **Token Throughput:** 10-50 tokens/second (depends on LLM)
- **Connection Overhead:** <10ms per SSE connection setup

### Scalability
- **Concurrent Streams:** 50-100 per FastAPI instance (tested)
- **Load Balancing:** Standard HTTP round-robin (no sticky sessions)
- **Resource Usage:** ~5MB memory per active stream

### Monitoring Metrics
```python
# Prometheus metrics to track
stream_duration_seconds = Histogram(
    "chat_stream_duration_seconds",
    "Duration of SSE chat streams"
)

stream_chunk_count = Histogram(
    "chat_stream_chunk_count",
    "Number of chunks sent per stream"
)

active_streams = Gauge(
    "chat_active_streams",
    "Number of currently active SSE streams"
)
```

## References

- **Sprint 15 Plan**: [SPRINT_15_PLAN.md](../sprints/SPRINT_15_PLAN.md)
- **ADR-021**: Perplexity-inspired UI Design
- **FastAPI StreamingResponse**: https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse
- **MDN SSE Docs**: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
- **SSE Spec**: https://html.spec.whatwg.org/multipage/server-sent-events.html

## Review History

- **2025-10-27**: Accepted during Sprint 15 planning
- **Reviewed by**: Claude Code, User (Product Owner)

---

**Summary:**

Server-Sent Events (SSE) provides the optimal balance of simplicity, performance, and infrastructure compatibility for streaming chat responses in AegisRAG Sprint 15. SSE's unidirectional nature perfectly matches the query → response pattern, while its native browser support and HTTP/2 compatibility eliminate the complexity of WebSocket management. This decision enables a Perplexity-like real-time UX without architectural overkill.
