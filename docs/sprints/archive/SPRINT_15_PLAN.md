# Sprint 15 Plan: React Frontend with Perplexity-Style UI

**Sprint Goal:** Build production-ready React frontend with Perplexity-inspired UX and SSE streaming

**Status:** 🔵 PLANNED
**Duration:** 7-10 days
**Branch:** `sprint-15-react-frontend`
**Prerequisites:** Sprint 14 complete (Backend + Testing Infrastructure)

---

## Executive Summary

Sprint 15 delivers a **Perplexity-inspired React frontend** for AegisRAG with:
- **Streaming chat interface** (token-by-token like Perplexity)
- **Clean, minimalist UI** (based on Perplexity design system)
- **Server-Sent Events (SSE)** for real-time updates
- **Source provenance cards** with AegisRAG-specific metadata
- **Session management** with conversation history

**Key Architecture Decisions:**
- SSE (Server-Sent Events) for streaming instead of WebSocket (ADR-020)
- Perplexity-inspired component design (ADR-021)
- React 18 + Vite + TypeScript + Tailwind CSS

---

## Design Philosophy: Why Perplexity?

**Perplexity AI** hat eine der besten RAG-Interfaces auf dem Markt:
- ✅ Klare, fokussierte UX ohne Ablenkung
- ✅ Streaming-Antworten fühlen sich schneller an
- ✅ Source Cards zeigen Provenance inline
- ✅ Minimalistisches Design (Sidebar + Main Content)
- ✅ Responsive und zugänglich

**AegisRAG-Erweiterungen:**
- 🔀 Mode Selector (Vector, Graph, Hybrid, Memory)
- 📊 Advanced Filters (Entity Types, Top-K, Reranking)
- 🏷️ Entity Highlighting in Results
- 📈 Real-time System Health Dashboard

---

## Feature Breakdown

### Feature 15.1: Project Setup & SSE Streaming Backend

**Goal:** Setup React project + implement streaming chat endpoint

#### Part A: React Project Setup

**Deliverables:**
- ✅ React 18 + Vite + TypeScript project
- ✅ Tailwind CSS 3 configuration
- ✅ React Router v6
- ✅ Zustand for state management
- ✅ Axios for HTTP + SSE client
- ✅ ESLint + Prettier
- ✅ Vitest + React Testing Library
- ✅ Docker setup

**Tech Stack:**
```json
{
  "framework": "React 18.2",
  "bundler": "Vite 5",
  "language": "TypeScript 5",
  "styling": "Tailwind CSS 3",
  "routing": "React Router 6",
  "state": "Zustand",
  "http": "Axios + EventSource (SSE)",
  "testing": "Vitest + React Testing Library"
}
```

**File Structure:**
```
frontend/
├── src/
│   ├── components/       # UI components
│   │   ├── ui/           # Base UI (Button, Input, Card)
│   │   ├── layout/       # Layout (Sidebar, Header)
│   │   ├── chat/         # Chat components
│   │   └── search/       # Search components
│   ├── pages/            # Route pages
│   ├── services/         # API services (SSE)
│   ├── stores/           # Zustand stores
│   ├── hooks/            # Custom React hooks
│   ├── types/            # TypeScript types
│   ├── utils/            # Helper functions
│   └── App.tsx
├── public/
├── tests/
├── Dockerfile
├── vite.config.ts
├── tailwind.config.js
└── package.json
```

#### Part B: SSE Streaming Backend

**Deliverables:**
- ✅ `POST /api/v1/chat/stream` - SSE streaming endpoint
- ✅ Modify `CoordinatorAgent` for streaming
- ✅ `GET /api/v1/chat/sessions` - List sessions
- ✅ Unit + Integration tests

**Backend Implementation:**

```python
# src/api/v1/chat.py - NEW ENDPOINT

from fastapi.responses import StreamingResponse
import json

@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Stream chat response with Server-Sent Events (Perplexity-style).

    Streams:
    - Metadata (session_id, intent)
    - Source cards (as retrieved)
    - Answer tokens (word-by-word or sentence-by-sentence)
    - Final metadata (latency, agent_path)

    Returns:
        StreamingResponse with text/event-stream
    """
    async def generate_stream():
        session_id = request.session_id or str(uuid.uuid4())

        # 1. Send initial metadata
        yield f"data: {json.dumps({
            'type': 'metadata',
            'session_id': session_id,
            'query': request.query
        })}\n\n"

        try:
            coordinator = get_coordinator()

            # 2. Stream query processing
            async for chunk in coordinator.process_query_stream(
                query=request.query,
                session_id=session_id,
                intent=request.intent
            ):
                if chunk["type"] == "intent":
                    yield f"data: {json.dumps({
                        'type': 'intent',
                        'intent': chunk['intent']
                    })}\n\n"

                elif chunk["type"] == "source":
                    yield f"data: {json.dumps({
                        'type': 'source',
                        'source': chunk['data']
                    })}\n\n"

                elif chunk["type"] == "token":
                    yield f"data: {json.dumps({
                        'type': 'token',
                        'content': chunk['content']
                    })}\n\n"

                elif chunk["type"] == "done":
                    yield f"data: {json.dumps({
                        'type': 'done',
                        'metadata': chunk['metadata']
                    })}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("Streaming error", error=str(e))
            yield f"data: {json.dumps({
                'type': 'error',
                'error': str(e)
            })}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/sessions")
async def list_sessions() -> dict:
    """List all active conversation sessions.

    Returns:
        List of session objects with metadata
    """
    try:
        memory_api = get_unified_memory_api()

        # Get all conversation keys from Redis
        sessions = await memory_api.list_keys(namespace="conversation")

        session_list = []
        for session_key in sessions:
            # Extract session_id from key
            session_id = session_key.replace("conversation:", "")

            # Get session metadata
            session_data = await memory_api.retrieve(
                key=session_key,
                namespace="memory"
            )

            if session_data:
                messages = session_data.get("messages", [])
                last_message = messages[-1] if messages else None

                session_list.append({
                    "session_id": session_id,
                    "message_count": len(messages),
                    "last_message": last_message.get("content", "")[:100] if last_message else "",
                    "created_at": session_data.get("created_at"),
                    "updated_at": session_data.get("updated_at")
                })

        return {
            "sessions": session_list,
            "total": len(session_list)
        }

    except Exception as e:
        logger.error("Failed to list sessions", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sessions: {str(e)}"
        )
```

**Frontend SSE Client:**

```typescript
// src/services/chat.service.ts

export interface ChatChunk {
  type: 'metadata' | 'intent' | 'source' | 'token' | 'done' | 'error';
  [key: string]: any;
}

export async function* streamChat(request: ChatRequest): AsyncGenerator<ChatChunk> {
  const response = await fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');

      // Keep last incomplete line in buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);

          if (data === '[DONE]') {
            return;
          }

          try {
            const chunk = JSON.parse(data);
            yield chunk;
          } catch (e) {
            console.warn('Failed to parse SSE chunk:', data);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
```

**Story Points:** 13 SP
**Duration:** 2 days

---

### Feature 15.2: Perplexity-Style Layout & Navigation

**Goal:** Implement minimalist sidebar + main content layout

**Deliverables:**
- ✅ Sidebar navigation (Perplexity-style)
- ✅ Logo + New Chat button
- ✅ Navigation items (Startseite, History, Settings)
- ✅ Responsive layout (hide sidebar on mobile)
- ✅ Dark mode toggle

**Components:**

```tsx
// src/components/layout/Sidebar.tsx

export function Sidebar() {
  return (
    <aside className="w-24 bg-gray-50 flex flex-col items-center py-6 space-y-8">
      {/* Logo */}
      <div className="text-teal-600 text-3xl font-bold">
        Aegis
      </div>

      {/* New Chat Button */}
      <button className="p-3 hover:bg-gray-200 rounded-lg transition">
        <PlusIcon className="w-6 h-6 text-gray-700" />
      </button>

      {/* Navigation */}
      <nav className="flex-1 flex flex-col space-y-4">
        <NavItem icon={<SearchIcon />} label="Suche" active />
        <NavItem icon={<HistoryIcon />} label="History" />
        <NavItem icon={<SettingsIcon />} label="Settings" />
      </nav>

      {/* User/Login */}
      <button className="p-3 bg-teal-600 text-white rounded-full">
        <UserIcon className="w-6 h-6" />
      </button>
    </aside>
  );
}

// src/components/layout/MainLayout.tsx

export function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-white">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        {children}
      </main>
    </div>
  );
}
```

**Design System (Tailwind Config):**

```javascript
// tailwind.config.js

export default {
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#20808D', // Teal
          hover: '#1A6B76',
        },
        gray: {
          50: '#F5F5F5',
          100: '#E8E8E8',
          700: '#6B6B6B',
          900: '#1A1A1A',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
};
```

**Story Points:** 8 SP
**Duration:** 1 day

---

### Feature 15.3: Search Input with Mode Selector

**Goal:** Large search input (Perplexity-style) with AegisRAG mode chips

**Deliverables:**
- ✅ Large centered search input
- ✅ Mode selector chips (Hybrid, Vector, Graph, Memory)
- ✅ Input icons (Search, Focus, Voice, Submit)
- ✅ Auto-focus on load
- ✅ Keyboard shortcuts (Cmd/Ctrl+K)

**Components:**

```tsx
// src/components/search/SearchInput.tsx

export function SearchInput({ onSubmit }: { onSubmit: (query: string, mode: string) => void }) {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'hybrid' | 'vector' | 'graph' | 'memory'>('hybrid');

  const handleSubmit = () => {
    if (query.trim()) {
      onSubmit(query, mode);
    }
  };

  return (
    <div className="max-w-3xl mx-auto w-full space-y-6">
      {/* Search Input */}
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
          placeholder="Fragen Sie alles. Tippen Sie @ für Erwähnungen."
          className="w-full h-28 px-6 pr-48 text-lg border-2 border-gray-200 rounded-3xl
                     focus:border-primary focus:outline-none placeholder-gray-400"
        />

        {/* Input Icons */}
        <div className="absolute right-4 bottom-4 flex items-center space-x-2">
          <IconButton icon={<SearchIcon />} />
          <IconButton icon={<FocusIcon />} />
          <IconButton icon={<MicIcon />} />
          <IconButton
            icon={<ArrowUpIcon />}
            primary
            onClick={handleSubmit}
            disabled={!query.trim()}
          />
        </div>
      </div>

      {/* Mode Selector Chips */}
      <div className="flex justify-center space-x-3">
        <ModeChip
          active={mode === 'hybrid'}
          onClick={() => setMode('hybrid')}
          icon="🔀"
        >
          Hybrid
        </ModeChip>
        <ModeChip
          active={mode === 'vector'}
          onClick={() => setMode('vector')}
          icon="🔍"
        >
          Vector
        </ModeChip>
        <ModeChip
          active={mode === 'graph'}
          onClick={() => setMode('graph')}
          icon="🕸️"
        >
          Graph
        </ModeChip>
        <ModeChip
          active={mode === 'memory'}
          onClick={() => setMode('memory')}
          icon="💭"
        >
          Memory
        </ModeChip>
      </div>
    </div>
  );
}

// src/components/search/ModeChip.tsx

export function ModeChip({
  active,
  onClick,
  icon,
  children
}: {
  active: boolean;
  onClick: () => void;
  icon: string;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        px-6 py-3 rounded-full border-2 flex items-center space-x-2 transition
        ${active
          ? 'bg-primary text-white border-primary'
          : 'bg-white text-gray-700 border-gray-200 hover:border-gray-300'
        }
      `}
    >
      <span className="text-xl">{icon}</span>
      <span className="font-medium">{children}</span>
    </button>
  );
}
```

**Story Points:** 10 SP
**Duration:** 1.5 days

---

### Feature 15.4: Streaming Answer Display

**Goal:** Display streaming answer with source cards (Perplexity-style)

**Deliverables:**
- ✅ Answer streaming component (token-by-token)
- ✅ Source cards (horizontal scroll)
- ✅ Inline citations
- ✅ Markdown rendering
- ✅ Loading states

**Components:**

```tsx
// src/components/chat/StreamingAnswer.tsx

export function StreamingAnswer({ query, mode }: { query: string; mode: string }) {
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState<Source[]>([]);
  const [metadata, setMetadata] = useState<any>(null);
  const [isStreaming, setIsStreaming] = useState(true);

  useEffect(() => {
    const stream = streamChat({ query, mode });

    (async () => {
      try {
        for await (const chunk of stream) {
          switch (chunk.type) {
            case 'source':
              setSources((prev) => [...prev, chunk.source]);
              break;

            case 'token':
              setAnswer((prev) => prev + chunk.content);
              break;

            case 'done':
              setMetadata(chunk.metadata);
              setIsStreaming(false);
              break;
          }
        }
      } catch (error) {
        console.error('Stream error:', error);
        setIsStreaming(false);
      }
    })();
  }, [query, mode]);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Query Title */}
      <h1 className="text-3xl font-bold text-gray-900">{query}</h1>

      {/* Tabs */}
      <div className="flex space-x-6 border-b border-gray-200">
        <Tab active>🤖 Antwort</Tab>
        <Tab>🖼️ Bilder</Tab>
        <Tab>🌐 Quellen {sources.length}</Tab>
      </div>

      {/* Source Cards */}
      {sources.length > 0 && (
        <SourceCardsScroll sources={sources} />
      )}

      {/* Answer Content */}
      <div className="prose prose-lg max-w-none">
        <ReactMarkdown>{answer}</ReactMarkdown>
        {isStreaming && <span className="animate-pulse">▊</span>}
      </div>

      {/* Metadata */}
      {metadata && (
        <div className="text-sm text-gray-500 flex items-center space-x-4">
          <span>⚡ {metadata.latency_seconds}s</span>
          <span>📊 {metadata.agent_path.join(' → ')}</span>
        </div>
      )}
    </div>
  );
}

// src/components/chat/SourceCardsScroll.tsx

export function SourceCardsScroll({ sources }: { sources: Source[] }) {
  return (
    <div className="flex space-x-4 overflow-x-auto pb-4 scrollbar-hide">
      {sources.map((source, index) => (
        <SourceCard key={index} source={source} />
      ))}
    </div>
  );
}

// src/components/chat/SourceCard.tsx

export function SourceCard({ source }: { source: Source }) {
  return (
    <div className="flex-shrink-0 w-64 p-4 bg-gray-50 rounded-xl border border-gray-200
                    hover:shadow-md transition cursor-pointer">
      {/* Source Header */}
      <div className="flex items-center space-x-2 mb-2">
        <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
          <span className="text-white text-sm">📄</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 truncate">
            {source.document_id}
          </div>
          <div className="text-xs text-gray-500">
            Chunk {source.chunk_index}/{source.total_chunks}
          </div>
        </div>
      </div>

      {/* Metadata */}
      <div className="space-y-1 mb-3">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-500">Score:</span>
          <span className="font-medium">{source.score.toFixed(3)}</span>
        </div>
        <div className="flex items-center space-x-1">
          {source.retrieval_modes.includes('vector') && (
            <Badge>🔍 Vector</Badge>
          )}
          {source.retrieval_modes.includes('graph') && (
            <Badge>🕸️ Graph</Badge>
          )}
        </div>
      </div>

      {/* Preview */}
      <p className="text-sm text-gray-700 line-clamp-3">
        {source.context}
      </p>

      {/* Entity Tags */}
      {source.entities && (
        <div className="mt-3 flex flex-wrap gap-1">
          {source.entities.slice(0, 3).map((entity, i) => (
            <EntityTag key={i} entity={entity} />
          ))}
        </div>
      )}
    </div>
  );
}
```

**Story Points:** 21 SP
**Duration:** 3 days

---

### Feature 15.5: Conversation History Sidebar

**Goal:** Session management with conversation list

**Deliverables:**
- ✅ Session list in sidebar (collapsible)
- ✅ Load session on click
- ✅ Delete session button
- ✅ Search within sessions
- ✅ Session grouping (Today, Yesterday, Last 7 days)

**Components:**

```tsx
// src/components/history/SessionSidebar.tsx

export function SessionSidebar() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    // Load sessions from API
    fetchSessions().then(setSessions);
  }, []);

  const groupedSessions = groupSessionsByDate(sessions);

  return (
    <div className={`
      transition-all duration-300
      ${expanded ? 'w-80' : 'w-0'}
      bg-gray-50 border-r border-gray-200 overflow-hidden
    `}>
      <div className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">History</h2>
          <button onClick={() => setExpanded(!expanded)}>
            <ChevronIcon />
          </button>
        </div>

        {/* Search */}
        <input
          type="text"
          placeholder="Suchen..."
          className="w-full px-4 py-2 border border-gray-200 rounded-lg"
        />

        {/* Session Groups */}
        <div className="space-y-6">
          {Object.entries(groupedSessions).map(([group, sessions]) => (
            <SessionGroup key={group} title={group} sessions={sessions} />
          ))}
        </div>
      </div>
    </div>
  );
}

// src/components/history/SessionGroup.tsx

export function SessionGroup({ title, sessions }: { title: string; sessions: Session[] }) {
  return (
    <div>
      <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">
        {title}
      </h3>
      <div className="space-y-1">
        {sessions.map((session) => (
          <SessionItem key={session.session_id} session={session} />
        ))}
      </div>
    </div>
  );
}

// src/components/history/SessionItem.tsx

export function SessionItem({ session }: { session: Session }) {
  const navigate = useNavigate();
  const [showDelete, setShowDelete] = useState(false);

  return (
    <div
      className="group relative p-3 hover:bg-white rounded-lg cursor-pointer transition"
      onClick={() => navigate(`/chat/${session.session_id}`)}
      onMouseEnter={() => setShowDelete(true)}
      onMouseLeave={() => setShowDelete(false)}
    >
      <div className="text-sm font-medium text-gray-900 line-clamp-1">
        {session.last_message}
      </div>
      <div className="text-xs text-gray-500 mt-1">
        {session.message_count} messages • {formatDate(session.updated_at)}
      </div>

      {/* Delete Button */}
      {showDelete && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            deleteSession(session.session_id);
          }}
          className="absolute right-3 top-3 p-1 bg-red-500 text-white rounded-md
                     opacity-0 group-hover:opacity-100 transition"
        >
          <TrashIcon className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
```

**Story Points:** 13 SP
**Duration:** 2 days

---

### Feature 15.6: System Health Dashboard

**Goal:** Real-time system monitoring (admin view)

**Deliverables:**
- ✅ Health status dashboard
- ✅ Dependency health cards (Qdrant, Ollama, Neo4j, Redis)
- ✅ Performance metrics chart
- ✅ Auto-refresh every 30s

**Components:**

```tsx
// src/pages/HealthDashboard.tsx

export function HealthDashboard() {
  const [health, setHealth] = useState<DetailedHealthResponse | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      const data = await getSystemHealth();
      setHealth(data);
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 30000); // 30s refresh

    return () => clearInterval(interval);
  }, []);

  if (!health) return <Loading />;

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">System Health</h1>
        <StatusBadge status={health.status} />
      </div>

      {/* Dependencies Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
        {Object.entries(health.dependencies).map(([key, dep]) => (
          <DependencyCard key={key} dependency={dep} />
        ))}
      </div>

      {/* Performance Metrics */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold mb-4">Query Performance (Last Hour)</h2>
        <PerformanceChart />
      </div>
    </div>
  );
}

// src/components/health/DependencyCard.tsx

export function DependencyCard({ dependency }: { dependency: DependencyHealth }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900">{dependency.name}</h3>
        <StatusDot status={dependency.status} />
      </div>

      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Status:</span>
          <span className={`font-medium ${
            dependency.status === 'up' ? 'text-green-600' : 'text-red-600'
          }`}>
            {dependency.status.toUpperCase()}
          </span>
        </div>

        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Latency:</span>
          <span className="font-medium">{dependency.latency_ms}ms</span>
        </div>

        {Object.entries(dependency.details).map(([key, value]) => (
          <div key={key} className="flex justify-between text-xs text-gray-600">
            <span>{key}:</span>
            <span>{String(value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Story Points:** 8 SP
**Duration:** 1 day

---

## Testing Strategy

### Unit Tests (Vitest + React Testing Library)

**Coverage Target:** >80%

**Component Tests:**
```typescript
// tests/components/SearchInput.test.tsx
describe('SearchInput', () => {
  it('should call onSubmit when Enter pressed', () => {
    const mockOnSubmit = vi.fn();
    render(<SearchInput onSubmit={mockOnSubmit} />);

    const input = screen.getByPlaceholderText(/Fragen Sie alles/);
    fireEvent.change(input, { target: { value: 'test query' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(mockOnSubmit).toHaveBeenCalledWith('test query', 'hybrid');
  });

  it('should change mode when chip clicked', () => {
    render(<SearchInput onSubmit={vi.fn()} />);

    const vectorChip = screen.getByText('Vector');
    fireEvent.click(vectorChip);

    expect(vectorChip).toHaveClass('bg-primary');
  });
});
```

**SSE Service Tests:**
```typescript
// tests/services/chat.service.test.ts
describe('streamChat', () => {
  it('should parse SSE chunks correctly', async () => {
    const mockResponse = new Response(
      'data: {"type":"token","content":"Hello"}\n\ndata: [DONE]\n\n'
    );

    global.fetch = vi.fn().mockResolvedValue(mockResponse);

    const chunks: ChatChunk[] = [];
    for await (const chunk of streamChat({ query: 'test' })) {
      chunks.push(chunk);
    }

    expect(chunks).toHaveLength(1);
    expect(chunks[0].type).toBe('token');
    expect(chunks[0].content).toBe('Hello');
  });
});
```

### Integration Tests

**E2E User Flows (Playwright):**
1. User submits query → sees streaming answer → clicks source
2. User creates session → submits multiple queries → reviews history
3. User changes mode → submits query → verifies correct API call

### Performance Tests

**Metrics:**
- First Contentful Paint: <1.5s
- Time to Interactive: <3s
- SSE latency: <500ms for first token
- Component render time: <100ms

---

## Docker Setup

### Frontend Dockerfile

```dockerfile
# frontend/Dockerfile

# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Build app
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built app
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Nginx Configuration

```nginx
# frontend/nginx.conf

server {
  listen 80;
  server_name localhost;

  root /usr/share/nginx/html;
  index index.html;

  # SPA routing
  location / {
    try_files $uri $uri/ /index.html;
  }

  # API proxy (for SSE)
  location /api {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;

    # SSE-specific headers
    proxy_set_header Connection '';
    proxy_set_header Cache-Control 'no-cache';
    proxy_buffering off;
    proxy_read_timeout 86400;

    # Standard headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }

  # Health check
  location /health {
    access_log off;
    return 200 "healthy\n";
    add_header Content-Type text/plain;
  }
}
```

### Updated docker-compose.yml

```yaml
services:
  # ... existing services (qdrant, neo4j, ollama, redis, backend)

  frontend:
    build: ./frontend
    container_name: aegis-frontend
    ports:
      - "3000:80"
    environment:
      - VITE_API_BASE_URL=http://localhost:8000
    depends_on:
      - backend
    networks:
      - aegis-network
    restart: unless-stopped
```

---

## Architecture Decisions

### ADR-020: Server-Sent Events for Chat Streaming

**Context:** Need real-time streaming for chat responses

**Decision:** Use SSE instead of WebSocket

**Rationale:**
- Simpler than WebSocket (unidirectional)
- Native browser support (EventSource API)
- Works with HTTP/2 multiplexing
- Easier to implement with FastAPI
- Automatic reconnection handling

**Alternatives Considered:**
- WebSocket: Overkill for unidirectional streaming
- Long-polling: Higher latency and overhead

**See:** `docs/adr/ADR-020-sse-streaming-for-chat.md`

### ADR-021: Perplexity-Inspired UI Design

**Context:** Need proven UX pattern for RAG interface

**Decision:** Adopt Perplexity's minimalist design patterns

**Rationale:**
- Proven UX in production RAG systems
- Focuses user attention on content
- Clean, accessible, responsive
- Easy to extend with AegisRAG-specific features

**See:** `docs/adr/ADR-021-perplexity-inspired-ui.md`

---

## Sprint Timeline

### Week 1 (Days 1-5)

**Day 1: Setup + Backend Streaming**
- React project setup (Vite, TypeScript, Tailwind)
- Backend SSE endpoint (`POST /api/v1/chat/stream`)
- Sessions list endpoint (`GET /api/v1/chat/sessions`)

**Day 2: Layout + Navigation**
- Sidebar component (Perplexity-style)
- MainLayout component
- Routing setup
- Dark mode toggle

**Day 3: Search Input**
- Large search input component
- Mode selector chips
- Input validation
- Keyboard shortcuts

**Day 4-5: Streaming Answer Display**
- SSE client service
- Streaming answer component
- Source cards (horizontal scroll)
- Markdown rendering

### Week 2 (Days 6-10)

**Day 6-7: Conversation History**
- Session sidebar
- Session list with grouping
- Load/delete sessions
- Search within sessions

**Day 8: Health Dashboard**
- Health status page
- Dependency cards
- Performance charts
- Auto-refresh

**Day 9: Testing & Polish**
- Unit tests (>80% coverage)
- E2E tests (critical flows)
- Accessibility improvements
- Performance optimization

**Day 10: Documentation & Deployment**
- Component documentation
- User guide
- Docker deployment
- Sprint 15 completion report

---

## Deliverables Checklist

### Code
- [ ] React frontend (src/)
- [ ] SSE streaming backend endpoint
- [ ] Sessions list endpoint
- [ ] Component library
- [ ] API service layer
- [ ] State management (Zustand)
- [ ] Unit tests (>80% coverage)
- [ ] E2E tests (Playwright)

### Docker & Deployment
- [ ] Frontend Dockerfile
- [ ] Nginx configuration
- [ ] Updated docker-compose.yml
- [ ] Environment configuration

### Documentation
- [ ] ADR-020: SSE Streaming
- [ ] ADR-021: Perplexity UI
- [ ] Component documentation
- [ ] User guide
- [ ] Developer setup guide
- [ ] Sprint 15 completion report

---

## Risks & Mitigation

### Risk: SSE browser compatibility issues
**Mitigation:** Use `EventSource` polyfill for older browsers, test on Safari/Firefox/Chrome

### Risk: Streaming latency on slow connections
**Mitigation:** Implement progressive loading, show skeleton states, buffer small chunks

### Risk: Session management scale issues
**Mitigation:** Paginate session list, implement search, Redis TTL for cleanup

### Risk: Mobile responsiveness challenges
**Mitigation:** Mobile-first CSS, test on real devices, collapsible sidebar

---

## Success Metrics

**User Experience:**
- First token latency: <500ms
- Time to Interactive: <3s
- Mobile usability score: >90

**Technical:**
- Test coverage: >80%
- Lighthouse score: >90
- Zero critical accessibility issues
- SSE reconnection success rate: >95%

**Business:**
- User can complete query in <10s
- Session management works for 100+ sessions
- System health visible in <2s

---

## Post-Sprint 15 Improvements (Sprint 16)

**Potential Features:**
1. Advanced filters UI (entity types, date range, top-k)
2. Graph visualization tab (D3.js/vis.js)
3. Export functionality (JSON, CSV, Markdown)
4. Saved queries / templates
5. User authentication (OAuth)
6. Admin panel (ingestion, stats)
7. Collaborative features (share results, annotations)
8. Performance monitoring (APM integration)

---

**Author:** Claude Code
**Date:** 2025-10-27
**Sprint:** 15
**Status:** PLANNED
