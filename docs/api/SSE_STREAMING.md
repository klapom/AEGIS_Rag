# Server-Sent Events (SSE) Streaming API

**Sprint 15 Feature 15.1:** SSE Streaming for Real-Time Responses
**Last Updated:** 2025-11-10 (Sprint 21)

---

## Overview

AEGIS RAG uses **Server-Sent Events (SSE)** for real-time streaming of:
- Token-by-token chat responses
- Progress updates during re-indexing operations
- Long-running task status

**Why SSE over WebSockets?**
- Simpler protocol (HTTP-based)
- Auto-reconnect support
- Native browser support via `EventSource`
- Unidirectional (server → client) fits use case

---

## SSE Format

SSE messages use the following format:

```
event: <event-type>
data: <json-payload>

```

**Important Notes:**
- Each message ends with **two newlines** (`\n\n`)
- The `event` field is optional (defaults to `message`)
- The `data` field can span multiple lines
- Comments start with `:` (e.g., `: heartbeat`)

---

## Chat Streaming (`/api/v1/chat`)

### Event Types

#### 1. `message` - Token Stream

Streams LLM-generated tokens in real-time.

**Format:**
```
event: message
data: {"token": "Vector", "position": 0}

event: message
data: {"token": " search", "position": 1}

event: message
data: {"token": " uses", "position": 2}
```

**Data Schema:**
```typescript
{
  token: string;      // Generated token
  position: number;   // Token position in response
}
```

#### 2. `progress` - Processing Updates

Indicates processing stage during query execution.

**Format:**
```
event: progress
data: {"phase": "routing", "message": "Analyzing query intent..."}

event: progress
data: {"phase": "retrieval", "message": "Searching 5000 documents..."}

event: progress
data: {"phase": "generation", "message": "Generating response..."}
```

**Data Schema:**
```typescript
{
  phase: "routing" | "retrieval" | "generation" | "validation";
  message: string;      // Human-readable status
  progress_percent?: number;  // Optional 0-100
}
```

**Phases:**
1. **routing**: Query intent classification (vector/graph/hybrid)
2. **retrieval**: Document/knowledge retrieval
3. **generation**: LLM response generation
4. **validation**: Answer quality check

#### 3. `sources` - Source Documents

Sent after retrieval, before generation starts.

**Format:**
```
event: sources
data: {
  "sources": [
    {
      "content": "Vector search uses embeddings to...",
      "metadata": {
        "file_name": "vector_search.pdf",
        "page": 3,
        "chunk_id": "abc123"
      },
      "score": 0.92,
      "rank": 1
    }
  ],
  "total_sources": 5,
  "intent": "hybrid"
}
```

**Data Schema:**
```typescript
{
  sources: Array<{
    content: string;
    metadata: {
      file_name: string;
      page?: number;
      chunk_id: string;
      [key: string]: any;
    };
    score: number;      // Relevance score (0-1)
    rank: number;       // Result rank (1-N)
  }>;
  total_sources: number;
  intent: "vector" | "graph" | "hybrid";
}
```

#### 4. `done` - Completion

Marks end of streaming with final metadata.

**Format:**
```
event: done
data: {
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "latency_ms": 1250,
  "tokens_generated": 45,
  "intent": "hybrid",
  "complete_answer": "Vector search uses embeddings to find semantically similar documents..."
}
```

**Data Schema:**
```typescript
{
  session_id: string;
  latency_ms: number;
  tokens_generated: number;
  intent: string;
  complete_answer: string;  // Full assembled response
}
```

#### 5. `error` - Error Event

Sent when processing fails.

**Format:**
```
event: error
data: {
  "error": "OllamaConnectionError",
  "message": "Failed to connect to Ollama service",
  "details": {"retry_after": 30}
}
```

**Data Schema:**
```typescript
{
  error: string;         // Error code
  message: string;       // Human-readable message
  details?: object;      // Additional context
}
```

---

## Re-Indexing Streaming (`/api/v1/admin/reindex`)

### Event Format

Re-indexing uses **only the `data` field** (no `event` field) for compatibility.

**Format:**
```
data: {"status": "in_progress", "phase": "initialization", "progress_percent": 0, "message": "Initializing re-indexing pipeline..."}

data: {"status": "in_progress", "phase": "deletion", "progress_percent": 10, "message": "Deleting old indexes..."}

data: {"status": "in_progress", "phase": "chunking", "progress_percent": 30, "documents_processed": 150, "documents_total": 500, "message": "Chunking documents..."}

data: {"status": "completed", "progress_percent": 100, "message": "Re-indexing completed successfully", "documents_indexed": 500}
```

### Data Schema

```typescript
{
  status: "in_progress" | "completed" | "error";
  phase?: "initialization" | "deletion" | "chunking" | "embedding" | "indexing" | "validation";
  progress_percent: number;      // 0-100
  documents_processed?: number;
  documents_total?: number;
  eta_seconds?: number | null;
  current_document?: string | null;
  message: string;
  error?: string;                // Only if status === "error"
}
```

### Phases

1. **initialization** (0-5%): Service startup and document discovery
2. **deletion** (5-10%): Delete old Qdrant/Neo4j data
3. **chunking** (10-40%): Document parsing and text chunking
4. **embedding** (40-70%): Generate embeddings with BGE-M3
5. **indexing** (70-90%): Insert into Qdrant and Neo4j
6. **validation** (90-100%): Verify indexes and run health checks

---

## Client Implementation

### JavaScript (Browser)

```javascript
// EventSource API (native browser support)
const eventSource = new EventSource('http://localhost:8000/api/v1/chat');

eventSource.addEventListener('message', (e) => {
  const data = JSON.parse(e.data);
  console.log('Token:', data.token);
  // Append token to UI
  document.getElementById('response').textContent += data.token;
});

eventSource.addEventListener('progress', (e) => {
  const data = JSON.parse(e.data);
  console.log('Progress:', data.message);
  // Update progress indicator
  document.getElementById('status').textContent = data.message;
});

eventSource.addEventListener('sources', (e) => {
  const data = JSON.parse(e.data);
  console.log('Sources:', data.sources.length, 'documents');
  // Display source documents
});

eventSource.addEventListener('done', (e) => {
  const data = JSON.parse(e.data);
  console.log('Complete! Latency:', data.latency_ms, 'ms');
  eventSource.close();  // Close connection
});

eventSource.addEventListener('error', (e) => {
  console.error('SSE Error:', e);
  eventSource.close();
});
```

### JavaScript (POST Request with SSE)

For POST endpoints (like `/api/v1/chat`), use `fetch` with stream processing:

```javascript
async function streamChat(query) {
  const response = await fetch('http://localhost:8000/api/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, stream: true })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || '';  // Keep incomplete message

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        const eventMatch = line.match(/^event: (.+)\ndata: (.+)$/s);
        if (eventMatch) {
          const [, event, dataStr] = eventMatch;
          const data = JSON.parse(dataStr);
          handleEvent(event, data);
        }
      } else if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        handleEvent('message', data);  // Default event type
      }
    }
  }
}

function handleEvent(event, data) {
  switch (event) {
    case 'message':
      console.log('Token:', data.token);
      break;
    case 'progress':
      console.log('Progress:', data.message);
      break;
    case 'sources':
      console.log('Sources:', data.sources.length);
      break;
    case 'done':
      console.log('Complete!');
      break;
    case 'error':
      console.error('Error:', data.message);
      break;
  }
}
```

### Python (httpx)

```python
import httpx
import json

async def stream_chat(query: str):
    """Stream chat response with SSE."""
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:8000/api/v1/chat",
            json={"query": query, "stream": True}
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("event: "):
                    # Parse event and data
                    parts = line.split("\n", 1)
                    event = parts[0][7:]  # Remove "event: "
                    data_line = parts[1] if len(parts) > 1 else ""

                    if data_line.startswith("data: "):
                        data = json.loads(data_line[6:])
                        handle_event(event, data)

                elif line.startswith("data: "):
                    # Default message event
                    data = json.loads(line[6:])
                    handle_event("message", data)

def handle_event(event: str, data: dict):
    """Handle SSE event."""
    if event == "message":
        print(f"Token: {data['token']}", end="", flush=True)
    elif event == "progress":
        print(f"\n[{data['phase']}] {data['message']}")
    elif event == "sources":
        print(f"\nSources: {data['total_sources']} documents")
    elif event == "done":
        print(f"\n\nComplete! Latency: {data['latency_ms']}ms")
    elif event == "error":
        print(f"\nError: {data['message']}")

# Usage
await stream_chat("What is vector search?")
```

### Python (sseclient-py)

```python
import sseclient
import requests
import json

def stream_reindex():
    """Stream re-indexing progress."""
    response = requests.post(
        "http://localhost:8000/api/v1/admin/reindex?confirm=true",
        stream=True
    )

    client = sseclient.SSEClient(response)

    for event in client.events():
        data = json.loads(event.data)

        if data["status"] == "in_progress":
            print(f"[{data['phase']}] {data['progress_percent']}% - {data['message']}")
        elif data["status"] == "completed":
            print(f"✅ Completed! {data['documents_indexed']} documents indexed")
        elif data["status"] == "error":
            print(f"❌ Error: {data['message']}")
            break

# Usage
stream_reindex()
```

---

## Error Handling

### Connection Errors

```javascript
eventSource.onerror = (error) => {
  console.error('SSE connection error:', error);

  // EventSource auto-reconnects by default (3s retry)
  // To prevent reconnect:
  eventSource.close();
};
```

### Timeout Handling

```javascript
const TIMEOUT_MS = 30000;  // 30 seconds

const timeout = setTimeout(() => {
  console.error('SSE timeout - no response in 30s');
  eventSource.close();
}, TIMEOUT_MS);

eventSource.addEventListener('message', () => {
  clearTimeout(timeout);  // Reset on each message
});
```

### Graceful Degradation

```javascript
// Check SSE support
if (typeof EventSource === 'undefined') {
  console.warn('SSE not supported, falling back to polling');
  // Use non-streaming endpoint
  const response = await fetch('/api/v1/chat', {
    method: 'POST',
    body: JSON.stringify({ query, stream: false })
  });
  const data = await response.json();
  console.log('Answer:', data.answer);
}
```

---

## Testing SSE Endpoints

### cURL

```bash
# Chat streaming
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is AEGIS RAG?", "stream": true}' \
  --no-buffer

# Re-indexing progress
curl -X POST "http://localhost:8000/api/v1/admin/reindex?confirm=true" \
  --no-buffer
```

### Postman

1. Set method to `POST`
2. Add request body (JSON)
3. Send request
4. View streaming response in "Body" tab (auto-updates)

---

## Performance Characteristics

### Chat Streaming

- **First Token Latency:** ~500ms (query processing + LLM startup)
- **Token Generation Rate:** ~20-40 tokens/second (llama3.2:8b)
- **Total Response Time:** ~1-5 seconds (depends on answer length)

### Re-Indexing Streaming

- **Update Frequency:** Every 50 documents processed
- **Typical Duration:** 2-10 minutes (500-5000 documents)
- **Progress Precision:** ±5% (estimated from phase completion)

---

## Troubleshooting

### Issue: No SSE events received

**Possible Causes:**
1. CORS blocking (check `Access-Control-Allow-Origin`)
2. Proxy/CDN buffering (disable buffering with `X-Accel-Buffering: no`)
3. HTTP/2 connection issues (SSE requires HTTP/1.1 or HTTP/2)

**Solution:**
```bash
# Test with cURL to isolate issue
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "stream": true}' \
  --no-buffer -v
```

### Issue: Connection drops mid-stream

**Possible Causes:**
1. Server timeout (default: 60s)
2. Network interruption
3. Server-side exception

**Solution:**
```javascript
// Implement reconnection logic
let retryCount = 0;
const MAX_RETRIES = 3;

function connectSSE() {
  const eventSource = new EventSource('/api/v1/chat');

  eventSource.onerror = () => {
    if (retryCount < MAX_RETRIES) {
      retryCount++;
      setTimeout(() => connectSSE(), 1000 * retryCount);
    }
  };

  eventSource.addEventListener('done', () => {
    retryCount = 0;  // Reset on success
  });
}
```

---

## Additional Resources

- [MDN: Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [SSE Specification (W3C)](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [EventSource API Reference](https://developer.mozilla.org/en-US/docs/Web/API/EventSource)

---

**Last Updated:** 2025-11-10
**Sprint:** 21
**Maintainer:** Klaus Pommer + Claude Code (documentation-agent)
