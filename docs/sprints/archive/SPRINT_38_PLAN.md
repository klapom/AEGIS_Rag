# Sprint 38: Authentication, Conversation Search & GraphRAG Multi-Hop

**Status:** PLANNED
**Duration:** 2025-12-09 to 2025-12-13 (5 days)
**Story Points:** 25 SP
**Branch:** `sprint-38-auth-graphrag`

---

## Sprint Objectives

### Primary Goals
1. **JWT Authentication Frontend** - Complete auth flow with login UI
2. **Conversation Search** - Search archived conversations semantically
3. **Share Conversation Links** - Generate public shareable links
4. **GraphRAG Multi-Hop** - Full graph-augmented retrieval for complex queries

### Success Criteria
- [ ] Users can log in via frontend and access protected routes
- [ ] Users can search through archived conversations
- [ ] Users can share conversations via expiring links
- [ ] Multi-hop queries automatically expand graph context for better answers

---

## Feature Overview

| Feature | Story Points | Priority | Dependencies |
|---------|--------------|----------|--------------|
| 38.1: JWT Auth Frontend | 8 SP | P0 (Critical) | `auth.py` backend |
| 38.2: Conversation Search UI | 5 SP | P1 (High) | `chat.py` search endpoint |
| 38.3: Share Conversation Links | 4 SP | P2 (Medium) | Redis, auth |
| 38.4: GraphRAG Multi-Hop Integration | 8 SP | P1 (High) | Neo4j, query_decomposition |
| **Total** | **25 SP** | | |

---

## Feature 38.1: JWT Authentication Frontend (8 SP)

**Priority:** P0 (Critical) - Foundation for user-specific features
**Duration:** 2 days
**Backend Ready:** Yes (`src/api/v1/auth.py`)

### Problem
Authentication backend exists but frontend has no login UI. All features requiring user context are blocked.

### Solution
Complete frontend auth flow with login page, token storage, and protected routes.

### Tasks

#### 38.1.1: Login Page Component (3 SP)
```typescript
// frontend/src/pages/LoginPage.tsx
export function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      if (!response.ok) {
        throw new Error('Invalid credentials');
      }

      const data = await response.json();
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('token_expiry', String(Date.now() + data.expires_in * 1000));

      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <form onSubmit={handleLogin} className="w-full max-w-md p-8 bg-white rounded-lg shadow">
        <h1 className="text-2xl font-bold mb-6">AegisRAG Login</h1>

        {error && (
          <div className="mb-4 p-3 bg-red-100 text-red-700 rounded" data-testid="login-error">
            {error}
          </div>
        )}

        <div className="mb-4">
          <label className="block text-sm font-medium mb-1">Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-primary"
            data-testid="login-username"
            required
          />
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium mb-1">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 border rounded focus:ring-2 focus:ring-primary"
            data-testid="login-password"
            required
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 bg-primary text-white rounded hover:bg-primary-hover disabled:opacity-50"
          data-testid="login-submit"
        >
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>
    </div>
  );
}
```

#### 38.1.2: Auth Context & Protected Routes (3 SP)
```typescript
// frontend/src/contexts/AuthContext.tsx
interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for existing token on mount
    const token = localStorage.getItem('access_token');
    const expiry = localStorage.getItem('token_expiry');

    if (token && expiry && Date.now() < Number(expiry)) {
      fetchCurrentUser(token).then(setUser).finally(() => setIsLoading(false));
    } else {
      localStorage.removeItem('access_token');
      localStorage.removeItem('token_expiry');
      setIsLoading(false);
    }
  }, []);

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('token_expiry');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// frontend/src/components/ProtectedRoute.tsx
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
```

#### 38.1.3: API Client with Auth Headers (2 SP)
```typescript
// frontend/src/lib/api.ts
class ApiClient {
  private baseUrl = '/api/v1';

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    const token = localStorage.getItem('access_token');
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return headers;
  }

  async get<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      headers: this.getHeaders(),
    });

    if (response.status === 401) {
      // Token expired - redirect to login
      localStorage.removeItem('access_token');
      window.location.href = '/login';
      throw new Error('Session expired');
    }

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    return response.json();
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(body),
    });

    if (response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
      throw new Error('Session expired');
    }

    return response.json();
  }
}

export const api = new ApiClient();
```

### Deliverables
```
frontend/src/pages/LoginPage.tsx
frontend/src/contexts/AuthContext.tsx
frontend/src/components/ProtectedRoute.tsx
frontend/src/hooks/useAuth.ts
frontend/src/lib/api.ts (updated)
frontend/e2e/tests/auth/login.spec.ts
```

### Acceptance Criteria
- [ ] Login page renders with username/password fields
- [ ] Successful login stores JWT in localStorage
- [ ] Failed login shows error message
- [ ] Protected routes redirect to login when unauthenticated
- [ ] API calls include Authorization header
- [ ] Token expiry triggers logout
- [ ] E2E tests pass for login flow

---

## Feature 38.2: Conversation Search UI (5 SP)

**Priority:** P1 (High)
**Duration:** 1.5 days
**Backend Ready:** Yes (`POST /api/v1/chat/search`)

### Problem
Users cannot search through their archived conversations. Backend endpoint exists but no UI.

### Solution
Add search bar to conversation history sidebar with semantic search results.

### Tasks

#### 38.2.1: Search Bar Component (2 SP)
```typescript
// frontend/src/components/chat/ConversationSearch.tsx
export function ConversationSearch({ onResultSelect }: { onResultSelect: (sessionId: string) => void }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ConversationSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    if (debouncedQuery.length < 3) {
      setResults([]);
      return;
    }

    const search = async () => {
      setLoading(true);
      try {
        const response = await api.post<ConversationSearchResponse>('/chat/search', {
          query: debouncedQuery,
          limit: 10,
          min_score: 0.5
        });
        setResults(response.results);
      } catch (err) {
        console.error('Search failed:', err);
      } finally {
        setLoading(false);
      }
    };

    search();
  }, [debouncedQuery]);

  return (
    <div className="relative" data-testid="conversation-search">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          placeholder="Search conversations..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setIsOpen(true)}
          className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary"
          data-testid="conversation-search-input"
        />
        {loading && (
          <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 animate-spin" />
        )}
      </div>

      {isOpen && results.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border rounded-lg shadow-lg z-50 max-h-96 overflow-auto">
          {results.map((result) => (
            <button
              key={result.session_id}
              onClick={() => {
                onResultSelect(result.session_id);
                setIsOpen(false);
                setQuery('');
              }}
              className="w-full px-4 py-3 text-left hover:bg-gray-50 border-b last:border-b-0"
              data-testid="search-result-item"
            >
              <div className="font-medium text-sm truncate">{result.title}</div>
              <div className="text-xs text-gray-500 mt-1 line-clamp-2">{result.snippet}</div>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-xs text-gray-400">
                  {new Date(result.archived_at).toLocaleDateString()}
                </span>
                <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded">
                  {Math.round(result.score * 100)}% match
                </span>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

#### 38.2.2: Archive Button & Auto-Archive (2 SP)
```typescript
// frontend/src/components/chat/ArchiveButton.tsx
export function ArchiveButton({ sessionId, onArchived }: { sessionId: string; onArchived: () => void }) {
  const [loading, setLoading] = useState(false);

  const handleArchive = async () => {
    if (!confirm('Archive this conversation? It will be searchable but removed from recent history.')) {
      return;
    }

    setLoading(true);
    try {
      await api.post(`/chat/sessions/${sessionId}/archive`, {});
      toast.success('Conversation archived');
      onArchived();
    } catch (err) {
      toast.error('Failed to archive conversation');
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleArchive}
      disabled={loading}
      className="p-2 hover:bg-gray-100 rounded"
      title="Archive conversation"
      data-testid="archive-button"
    >
      <Archive className="w-4 h-4" />
    </button>
  );
}
```

#### 38.2.3: Integration in Sidebar (1 SP)
```typescript
// Update frontend/src/components/layout/Sidebar.tsx
export function Sidebar() {
  const navigate = useNavigate();

  const handleSearchResultSelect = (sessionId: string) => {
    navigate(`/chat/${sessionId}`);
  };

  return (
    <aside className="w-64 bg-white border-r flex flex-col">
      <div className="p-4 border-b">
        <ConversationSearch onResultSelect={handleSearchResultSelect} />
      </div>

      <div className="flex-1 overflow-auto">
        <ConversationHistory />
      </div>
    </aside>
  );
}
```

### Deliverables
```
frontend/src/components/chat/ConversationSearch.tsx
frontend/src/components/chat/ArchiveButton.tsx
frontend/src/hooks/useDebounce.ts
frontend/src/types/search.ts
frontend/e2e/tests/chat/conversation-search.spec.ts
```

### Acceptance Criteria
- [ ] Search bar appears in sidebar
- [ ] Typing triggers debounced search (300ms)
- [ ] Results show title, snippet, date, and relevance score
- [ ] Clicking result navigates to conversation
- [ ] Archive button archives current conversation
- [ ] E2E tests pass for search flow

---

## Feature 38.3: Share Conversation Links (4 SP)

**Priority:** P2 (Medium)
**Duration:** 1 day
**Backend Ready:** Needs implementation

### Problem
Users cannot share conversations with colleagues who don't have accounts.

### Solution
Generate time-limited public links for read-only conversation access.

### Tasks

#### 38.3.1: Backend Share Endpoint (2 SP)
```python
# src/api/v1/chat.py - Add to existing file

class ShareSettings(BaseModel):
    """Settings for conversation sharing."""
    expiry_hours: int = Field(default=24, ge=1, le=168)  # 1h to 7 days


class ShareLinkResponse(BaseModel):
    """Response with share link details."""
    share_url: str
    share_token: str
    expires_at: str
    session_id: str


@router.post("/sessions/{session_id}/share", response_model=ShareLinkResponse)
async def create_share_link(
    session_id: str,
    settings: ShareSettings = ShareSettings(),
) -> ShareLinkResponse:
    """Generate public share link for conversation.

    Creates a time-limited, read-only access link for the conversation.
    Link can be shared with anyone - no authentication required to view.

    Args:
        session_id: Session ID to share
        settings: Share settings (expiry time)

    Returns:
        ShareLinkResponse with URL and expiry
    """
    import secrets
    from datetime import datetime, timedelta, UTC

    logger.info("create_share_link_requested", session_id=session_id)

    try:
        # Generate secure token
        share_token = secrets.token_urlsafe(16)
        expiry = datetime.now(UTC) + timedelta(hours=settings.expiry_hours)

        # Store share metadata in Redis
        from src.components.memory import get_redis_memory
        redis = get_redis_memory()

        await redis.store(
            key=f"share:{share_token}",
            value={
                "session_id": session_id,
                "created_at": datetime.now(UTC).isoformat(),
                "expires_at": expiry.isoformat(),
            },
            ttl_seconds=settings.expiry_hours * 3600,
            namespace="shares"
        )

        # Build share URL
        base_url = settings.base_url or "http://localhost:5173"
        share_url = f"{base_url}/share/{share_token}"

        logger.info(
            "share_link_created",
            session_id=session_id,
            expires_at=expiry.isoformat(),
        )

        return ShareLinkResponse(
            share_url=share_url,
            share_token=share_token,
            expires_at=expiry.isoformat(),
            session_id=session_id,
        )

    except Exception as e:
        logger.error("create_share_link_failed", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create share link: {str(e)}",
        ) from e


@router.get("/share/{share_token}")
async def get_shared_conversation(share_token: str) -> ConversationHistoryResponse:
    """Get shared conversation (read-only, no auth required).

    Args:
        share_token: Share token from URL

    Returns:
        Conversation history (read-only view)

    Raises:
        HTTPException: 404 if link expired or not found
    """
    from src.components.memory import get_redis_memory
    redis = get_redis_memory()

    share_data = await redis.retrieve(key=f"share:{share_token}", namespace="shares")

    if not share_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link expired or not found"
        )

    # Return conversation history
    return await get_conversation_history(share_data["session_id"])
```

#### 38.3.2: Frontend Share Modal (2 SP)
```typescript
// frontend/src/components/chat/ShareModal.tsx
export function ShareModal({ sessionId, onClose }: { sessionId: string; onClose: () => void }) {
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [expiryHours, setExpiryHours] = useState(24);

  const handleGenerateLink = async () => {
    setLoading(true);
    try {
      const response = await api.post<ShareLinkResponse>(`/chat/sessions/${sessionId}/share`, {
        expiry_hours: expiryHours
      });
      setShareUrl(response.share_url);
    } catch (err) {
      toast.error('Failed to generate share link');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (shareUrl) {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Modal onClose={onClose} data-testid="share-modal">
      <h2 className="text-xl font-semibold mb-4">Share Conversation</h2>

      {!shareUrl ? (
        <>
          <p className="text-gray-600 mb-4">
            Create a public link for this conversation. Anyone with the link can view it.
          </p>

          <label className="block mb-4">
            <span className="text-sm text-gray-700">Link expires in:</span>
            <select
              value={expiryHours}
              onChange={(e) => setExpiryHours(Number(e.target.value))}
              className="mt-1 block w-full rounded-lg border-gray-300"
              data-testid="expiry-select"
            >
              <option value={1}>1 hour</option>
              <option value={24}>24 hours</option>
              <option value={72}>3 days</option>
              <option value={168}>7 days</option>
            </select>
          </label>

          <button
            onClick={handleGenerateLink}
            disabled={loading}
            className="w-full py-2 bg-primary text-white rounded-lg hover:bg-primary-hover"
            data-testid="generate-link-button"
          >
            {loading ? 'Generating...' : 'Generate Link'}
          </button>
        </>
      ) : (
        <>
          <p className="text-sm text-gray-600 mb-2">Your share link:</p>
          <div className="flex items-center gap-2 mb-4">
            <input
              type="text"
              value={shareUrl}
              readOnly
              className="flex-1 px-3 py-2 border rounded-lg bg-gray-50 text-sm"
              data-testid="share-url-input"
            />
            <button
              onClick={handleCopy}
              className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover"
              data-testid="copy-button"
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <p className="text-xs text-gray-500">
            Link expires in {expiryHours} hours
          </p>
        </>
      )}
    </Modal>
  );
}

// frontend/src/pages/SharedConversationPage.tsx
export function SharedConversationPage() {
  const { shareToken } = useParams<{ shareToken: string }>();
  const [conversation, setConversation] = useState<ConversationHistory | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchShared = async () => {
      try {
        // Note: No auth header needed for shared links
        const response = await fetch(`/api/v1/chat/share/${shareToken}`);
        if (!response.ok) {
          throw new Error('Link expired or not found');
        }
        setConversation(await response.json());
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    };

    fetchShared();
  }, [shareToken]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorPage message={error} />;
  if (!conversation) return null;

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-6">
        <p className="text-sm text-yellow-800">
          This is a shared conversation (read-only view)
        </p>
      </div>

      <div className="space-y-4">
        {conversation.messages.map((msg, idx) => (
          <MessageBubble key={idx} message={msg} />
        ))}
      </div>
    </div>
  );
}
```

### Deliverables
```
src/api/v1/chat.py (updated with share endpoints)
frontend/src/components/chat/ShareModal.tsx
frontend/src/pages/SharedConversationPage.tsx
frontend/e2e/tests/chat/share-conversation.spec.ts
```

### Acceptance Criteria
- [ ] Share button opens modal
- [ ] User can select expiry time (1h, 24h, 3d, 7d)
- [ ] Generated link is copyable
- [ ] Shared link shows read-only conversation
- [ ] Expired links return 404
- [ ] E2E tests pass for share flow

---

## Feature 38.4: GraphRAG Multi-Hop Integration (8 SP)

**Priority:** P1 (High)
**Duration:** 2 days
**Reference:** [Neo4j GraphRAG Article](https://neo4j.com/blog/genai/knowledge-graph-llm-multi-hop-reasoning/)

### Problem
Complex multi-hop queries (e.g., "Who developed the algorithm used by Qdrant?") fail because:
1. Query decomposition detects MULTI_HOP but doesn't expand graph context
2. Each sub-query runs in isolation without previous results
3. Graph traversal exists in `graph_viz.py` but isn't integrated into RAG

### Solution
Create a unified `GraphRAGRetriever` that combines:
- Query classification (existing)
- Graph expansion for found entities (new)
- Context injection between sub-queries (new)
- Graph-augmented answer generation (enhanced)

### Architecture

```
User Query: "Who founded the company that created Kubernetes?"
                    │
                    ▼
        ┌─────────────────────┐
        │ Query Classification │
        │   → MULTI_HOP        │
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │ Query Decomposition  │
        │ 1. "Who created K8s?"│
        │ 2. "Who founded [X]?"│
        └──────────┬──────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   │
┌─────────────────┐          │
│ Sub-Query 1     │          │
│ Vector Search   │          │
│ → "Google"      │          │
└────────┬────────┘          │
         │                   │
         ▼                   │
┌─────────────────┐          │
│ Graph Expansion │          │
│ Google ──2hop──►│          │
│ → Larry Page    │          │
│ → Sergey Brin   │          │
└────────┬────────┘          │
         │                   │
         ▼                   ▼
┌─────────────────────────────┐
│ Context Injection           │
│ Sub-Query 2 gets:           │
│ - "Google created K8s"      │
│ - "Larry Page founded Goog" │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Graph-Augmented Generation  │
│ Context includes:           │
│ - Entities                  │
│ - Relationships (paths)     │
│ - Source documents          │
└──────────┬──────────────────┘
           │
           ▼
   "Larry Page and Sergey Brin
    founded Google, which created
    Kubernetes in 2014."
```

### Tasks

#### 38.4.1: GraphRAGRetriever Class (4 SP)
```python
# src/components/retrieval/graph_rag_retriever.py
"""GraphRAG Retriever with Multi-Hop Support.

Sprint 38 Feature 38.4: Full GraphRAG implementation following Neo4j pattern.
Reference: https://neo4j.com/blog/genai/knowledge-graph-llm-multi-hop-reasoning/

This retriever combines:
- Vector search (Qdrant)
- Graph traversal (Neo4j)
- Query decomposition (LLM)
- Context-aware answer generation
"""

import asyncio
from typing import Any

import structlog
from pydantic import BaseModel, Field

from src.components.graph_rag.neo4j_client import get_neo4j_client
from src.components.llm_proxy import get_aegis_llm_proxy
from src.components.llm_proxy.models import (
    Complexity,
    LLMTask,
    QualityRequirement,
    TaskType,
)
from src.components.retrieval.query_decomposition import (
    QueryDecomposer,
    QueryType,
    SubQuery,
)
from src.components.vector_search.hybrid_search import HybridSearch

logger = structlog.get_logger(__name__)


class GraphContext(BaseModel):
    """Accumulated graph context across multi-hop queries."""

    entities: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)
    paths: list[list[str]] = Field(default_factory=list)
    documents: list[dict[str, Any]] = Field(default_factory=list)

    def add_entities(self, entities: list[dict]) -> None:
        """Add entities, avoiding duplicates by name."""
        existing_names = {e.get("name") for e in self.entities}
        for entity in entities:
            if entity.get("name") not in existing_names:
                self.entities.append(entity)
                existing_names.add(entity.get("name"))

    def add_relationships(self, relationships: list[dict]) -> None:
        """Add relationships, avoiding duplicates."""
        existing = {(r.get("source"), r.get("target"), r.get("type")) for r in self.relationships}
        for rel in relationships:
            key = (rel.get("source"), rel.get("target"), rel.get("type"))
            if key not in existing:
                self.relationships.append(rel)
                existing.add(key)

    def to_prompt_context(self) -> str:
        """Convert to prompt-friendly context string."""
        parts = []

        if self.entities:
            parts.append("=== Entities ===")
            for e in self.entities[:15]:  # Limit to avoid context overflow
                parts.append(f"- {e.get('name')} ({e.get('type', 'Entity')}): {e.get('description', '')[:100]}")

        if self.relationships:
            parts.append("\n=== Relationships ===")
            for r in self.relationships[:15]:
                parts.append(f"- {r.get('source')} --[{r.get('type')}]--> {r.get('target')}")
                if r.get('description'):
                    parts.append(f"  Description: {r.get('description')[:100]}")

        if self.paths:
            parts.append("\n=== Connection Paths ===")
            for path in self.paths[:5]:
                parts.append(f"- {' → '.join(path)}")

        if self.documents:
            parts.append("\n=== Source Documents ===")
            for doc in self.documents[:10]:
                parts.append(f"- [{doc.get('source', 'Unknown')}]: {doc.get('text', '')[:150]}...")

        return "\n".join(parts)


class GraphRAGResult(BaseModel):
    """Result from GraphRAG retrieval."""

    query: str
    answer: str
    graph_context: GraphContext
    query_type: str
    sub_queries: list[str] = Field(default_factory=list)
    execution_strategy: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphRAGRetriever:
    """GraphRAG Retriever with full multi-hop support.

    Implements the GraphRAG pattern:
    1. Classify query (SIMPLE, COMPOUND, MULTI_HOP)
    2. For MULTI_HOP: Decompose into sub-queries
    3. Execute each sub-query with graph expansion
    4. Inject context between dependent queries
    5. Generate answer with full graph context
    """

    def __init__(self) -> None:
        """Initialize GraphRAG retriever."""
        self.decomposer = QueryDecomposer()
        self.hybrid_search = HybridSearch()
        self.neo4j = get_neo4j_client()
        self.proxy = get_aegis_llm_proxy()

        logger.info("graph_rag_retriever_initialized")

    async def retrieve(self, query: str, max_hops: int = 2) -> GraphRAGResult:
        """Execute GraphRAG retrieval.

        Args:
            query: User query
            max_hops: Maximum graph traversal hops (default: 2)

        Returns:
            GraphRAGResult with answer and graph context
        """
        logger.info("graph_rag_retrieve_started", query=query[:100])

        # 1. Classify query
        classification = await self.decomposer.classify_query(query)

        # 2. Route based on query type
        if classification.query_type == QueryType.MULTI_HOP:
            return await self._multi_hop_retrieve(query, max_hops)
        elif classification.query_type == QueryType.COMPOUND:
            return await self._compound_retrieve(query, max_hops)
        else:
            return await self._simple_retrieve(query, max_hops)

    async def _simple_retrieve(self, query: str, max_hops: int) -> GraphRAGResult:
        """Simple query: Vector search + optional graph expansion."""
        graph_context = GraphContext()

        # Vector search
        vector_results = await self.hybrid_search.search(query, top_k=10)
        graph_context.documents = vector_results.get("results", [])

        # Extract entities from results
        entities = await self._extract_entities_from_results(vector_results)
        graph_context.add_entities(entities)

        # Optional: 1-hop expansion for found entities
        if entities:
            expanded = await self._graph_expand(entities[:3], max_hops=1)
            graph_context.add_entities(expanded.get("entities", []))
            graph_context.add_relationships(expanded.get("relationships", []))

        # Generate answer
        answer = await self._generate_answer(query, graph_context)

        return GraphRAGResult(
            query=query,
            answer=answer,
            graph_context=graph_context,
            query_type="SIMPLE",
            execution_strategy="direct",
            metadata={"vector_results": len(vector_results.get("results", []))}
        )

    async def _compound_retrieve(self, query: str, max_hops: int) -> GraphRAGResult:
        """Compound query: Parallel sub-query execution with merged context."""
        graph_context = GraphContext()

        # Decompose
        sub_queries = await self.decomposer.decompose_query(query, QueryType.COMPOUND)

        # Execute in parallel
        tasks = [self._execute_sub_query(sq.query, max_hops) for sq in sub_queries]
        sub_results = await asyncio.gather(*tasks)

        # Merge contexts
        for result in sub_results:
            graph_context.add_entities(result.get("entities", []))
            graph_context.add_relationships(result.get("relationships", []))
            graph_context.documents.extend(result.get("documents", []))

        # Generate unified answer
        answer = await self._generate_answer(query, graph_context)

        return GraphRAGResult(
            query=query,
            answer=answer,
            graph_context=graph_context,
            query_type="COMPOUND",
            sub_queries=[sq.query for sq in sub_queries],
            execution_strategy="parallel",
        )

    async def _multi_hop_retrieve(self, query: str, max_hops: int) -> GraphRAGResult:
        """Multi-hop query: Sequential execution with context injection.

        This is the key GraphRAG innovation - each step builds on previous.
        """
        graph_context = GraphContext()

        # Decompose into sequential sub-queries
        sub_queries = await self.decomposer.decompose_query(query, QueryType.MULTI_HOP)

        logger.info(
            "multi_hop_decomposed",
            num_sub_queries=len(sub_queries),
            sub_queries=[sq.query for sq in sub_queries],
        )

        # Execute sequentially with context accumulation
        for i, sub_query in enumerate(sorted(sub_queries, key=lambda x: x.index)):
            logger.info(f"executing_sub_query_{i}", query=sub_query.query)

            # 1. Vector search for this sub-query
            vector_results = await self.hybrid_search.search(sub_query.query, top_k=5)
            graph_context.documents.extend(vector_results.get("results", []))

            # 2. Extract entities from vector results
            new_entities = await self._extract_entities_from_results(vector_results)

            # 3. CRITICAL: Also search for entities mentioned in previous context
            if graph_context.entities:
                # Use previous entities to guide search
                context_query = f"{sub_query.query} {' '.join(e.get('name', '') for e in graph_context.entities[:5])}"
                context_results = await self.hybrid_search.search(context_query, top_k=3)
                context_entities = await self._extract_entities_from_results(context_results)
                new_entities.extend(context_entities)

            graph_context.add_entities(new_entities)

            # 4. Graph expansion for ALL accumulated entities
            if new_entities:
                expanded = await self._graph_expand(
                    new_entities[:5],
                    max_hops=max_hops,
                    filter_entities=graph_context.entities  # Connect to existing
                )
                graph_context.add_entities(expanded.get("entities", []))
                graph_context.add_relationships(expanded.get("relationships", []))

                # Track paths for explainability
                if expanded.get("paths"):
                    graph_context.paths.extend(expanded["paths"])

            logger.info(
                f"sub_query_{i}_completed",
                entities=len(graph_context.entities),
                relationships=len(graph_context.relationships),
            )

        # Generate answer with full accumulated context
        answer = await self._generate_answer(query, graph_context)

        return GraphRAGResult(
            query=query,
            answer=answer,
            graph_context=graph_context,
            query_type="MULTI_HOP",
            sub_queries=[sq.query for sq in sub_queries],
            execution_strategy="sequential_with_graph_expansion",
            metadata={
                "total_entities": len(graph_context.entities),
                "total_relationships": len(graph_context.relationships),
                "paths_found": len(graph_context.paths),
            }
        )

    async def _execute_sub_query(self, query: str, max_hops: int) -> dict[str, Any]:
        """Execute a single sub-query with graph expansion."""
        # Vector search
        vector_results = await self.hybrid_search.search(query, top_k=5)

        # Extract and expand entities
        entities = await self._extract_entities_from_results(vector_results)

        result = {
            "entities": entities,
            "relationships": [],
            "documents": vector_results.get("results", []),
        }

        if entities:
            expanded = await self._graph_expand(entities[:3], max_hops)
            result["entities"].extend(expanded.get("entities", []))
            result["relationships"] = expanded.get("relationships", [])

        return result

    async def _extract_entities_from_results(
        self,
        vector_results: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Extract entity mentions from vector search results.

        Uses Neo4j to find entities mentioned in the retrieved text.
        """
        results = vector_results.get("results", [])
        if not results:
            return []

        # Combine text from top results
        combined_text = " ".join(r.get("text", "")[:500] for r in results[:5])

        # Query Neo4j for entities mentioned in text
        cypher = """
        MATCH (e:base)
        WHERE toLower($text) CONTAINS toLower(e.name)
        RETURN e.name AS name, e.type AS type, e.description AS description,
               e.entity_id AS id
        LIMIT 10
        """

        try:
            entity_results = await self.neo4j.execute_read(cypher, {"text": combined_text})
            return [dict(r) for r in entity_results]
        except Exception as e:
            logger.warning("entity_extraction_failed", error=str(e))
            return []

    async def _graph_expand(
        self,
        entities: list[dict[str, Any]],
        max_hops: int = 2,
        filter_entities: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Expand graph context from seed entities.

        Performs N-hop traversal from each entity to find connected nodes.
        """
        if not entities:
            return {"entities": [], "relationships": [], "paths": []}

        entity_names = [e.get("name") for e in entities if e.get("name")]
        if not entity_names:
            return {"entities": [], "relationships": [], "paths": []}

        # Build filter for connecting to existing context
        filter_clause = ""
        if filter_entities:
            filter_names = [e.get("name") for e in filter_entities if e.get("name")]
            if filter_names:
                # Prioritize paths that connect to existing entities
                filter_clause = f"OR connected.name IN {filter_names}"

        # Multi-hop traversal query
        cypher = f"""
        MATCH path = (start:base)-[r:RELATES_TO|MENTIONED_IN*1..{max_hops}]-(connected:base)
        WHERE start.name IN $entity_names {filter_clause}
        WITH connected, path, length(path) AS hops,
             [rel IN relationships(path) | type(rel)] AS rel_types,
             [node IN nodes(path) | node.name] AS path_nodes
        RETURN DISTINCT
            connected.name AS name,
            connected.type AS type,
            connected.description AS description,
            hops,
            rel_types,
            path_nodes
        ORDER BY hops
        LIMIT 20
        """

        try:
            results = await self.neo4j.execute_read(cypher, {"entity_names": entity_names})

            expanded_entities = []
            relationships = []
            paths = []

            for record in results:
                # Add entity
                expanded_entities.append({
                    "name": record.get("name"),
                    "type": record.get("type"),
                    "description": record.get("description"),
                    "hops": record.get("hops"),
                })

                # Track path
                path_nodes = record.get("path_nodes", [])
                if path_nodes:
                    paths.append(path_nodes)

                # Build relationships from path
                rel_types = record.get("rel_types", [])
                for i, rel_type in enumerate(rel_types):
                    if i < len(path_nodes) - 1:
                        relationships.append({
                            "source": path_nodes[i],
                            "target": path_nodes[i + 1],
                            "type": rel_type,
                        })

            logger.info(
                "graph_expansion_completed",
                seed_entities=len(entity_names),
                expanded_entities=len(expanded_entities),
                relationships=len(relationships),
            )

            return {
                "entities": expanded_entities,
                "relationships": relationships,
                "paths": paths,
            }

        except Exception as e:
            logger.error("graph_expansion_failed", error=str(e))
            return {"entities": [], "relationships": [], "paths": []}

    async def _generate_answer(self, query: str, context: GraphContext) -> str:
        """Generate answer using graph-augmented context."""
        context_str = context.to_prompt_context()

        prompt = f"""You are a helpful assistant with access to a knowledge graph.
Use the following graph context to answer the user's question.

The context includes:
- Entities: Key concepts and their descriptions
- Relationships: How entities are connected
- Connection Paths: Chains showing how concepts relate
- Source Documents: Original text snippets

=== GRAPH CONTEXT ===
{context_str}

=== USER QUESTION ===
{query}

=== INSTRUCTIONS ===
1. Answer based ONLY on the provided context
2. If the context shows a path between concepts, explain the connection
3. Cite specific relationships when relevant
4. If context is insufficient, say so clearly

Answer:"""

        try:
            task = LLMTask(
                task_type=TaskType.ANSWER_GENERATION,
                prompt=prompt,
                quality_requirement=QualityRequirement.HIGH,
                complexity=Complexity.HIGH,  # Multi-hop needs quality
                max_tokens=1024,
                temperature=0.3,
            )

            result = await self.proxy.generate(task)

            logger.info(
                "graph_rag_answer_generated",
                provider=result.provider,
                model=result.model,
                tokens=result.total_tokens,
            )

            return result.content.strip()

        except Exception as e:
            logger.error("answer_generation_failed", error=str(e))
            return f"Unable to generate answer: {str(e)}"


# Singleton
_graph_rag_retriever: GraphRAGRetriever | None = None


def get_graph_rag_retriever() -> GraphRAGRetriever:
    """Get global GraphRAGRetriever instance."""
    global _graph_rag_retriever
    if _graph_rag_retriever is None:
        _graph_rag_retriever = GraphRAGRetriever()
    return _graph_rag_retriever
```

#### 38.4.2: Integration with Chat Endpoint (2 SP)
```python
# src/api/v1/chat.py - Update stream_chat to use GraphRAG for complex queries

@router.post("/stream")
async def stream_chat(request: ChatRequest) -> StreamingResponse:
    """Stream chat response with automatic GraphRAG for complex queries."""

    # Classify query complexity
    from src.components.retrieval.query_decomposition import QueryDecomposer, QueryType
    decomposer = QueryDecomposer()
    classification = await decomposer.classify_query(request.query)

    # Use GraphRAG for MULTI_HOP queries
    if classification.query_type == QueryType.MULTI_HOP:
        logger.info("using_graph_rag_for_multi_hop", query=request.query[:100])

        from src.components.retrieval.graph_rag_retriever import get_graph_rag_retriever
        retriever = get_graph_rag_retriever()

        result = await retriever.retrieve(request.query, max_hops=2)

        # Stream the GraphRAG result
        async def generate():
            # Yield answer in chunks for streaming effect
            chunks = result.answer.split(". ")
            for chunk in chunks:
                yield f"data: {json.dumps({'type': 'content', 'content': chunk + '. '})}\n\n"
                await asyncio.sleep(0.05)

            # Yield graph context metadata
            yield f"data: {json.dumps({'type': 'graph_context', 'entities': len(result.graph_context.entities), 'relationships': len(result.graph_context.relationships)})}\n\n"

            yield "data: [DONE]\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream")

    # Standard retrieval for SIMPLE/COMPOUND queries
    # ... existing streaming logic ...
```

#### 38.4.3: Tests (2 SP)
```python
# tests/components/retrieval/test_graph_rag_retriever.py
import pytest
from src.components.retrieval.graph_rag_retriever import (
    GraphRAGRetriever,
    GraphContext,
)


class TestGraphContext:
    """Tests for GraphContext accumulation."""

    def test_add_entities_deduplicates(self):
        ctx = GraphContext()
        ctx.add_entities([{"name": "A"}, {"name": "B"}])
        ctx.add_entities([{"name": "A"}, {"name": "C"}])  # A is duplicate

        assert len(ctx.entities) == 3
        names = {e["name"] for e in ctx.entities}
        assert names == {"A", "B", "C"}

    def test_to_prompt_context_format(self):
        ctx = GraphContext(
            entities=[{"name": "Google", "type": "ORG", "description": "Tech company"}],
            relationships=[{"source": "Google", "target": "K8s", "type": "CREATED"}],
        )

        prompt = ctx.to_prompt_context()

        assert "=== Entities ===" in prompt
        assert "Google (ORG)" in prompt
        assert "=== Relationships ===" in prompt
        assert "Google --[CREATED]--> K8s" in prompt


class TestGraphRAGRetriever:
    """Integration tests for GraphRAGRetriever."""

    @pytest.fixture
    def retriever(self):
        return GraphRAGRetriever()

    @pytest.mark.asyncio
    async def test_simple_query_returns_result(self, retriever):
        result = await retriever.retrieve("What is vector search?")

        assert result.query_type == "SIMPLE"
        assert result.execution_strategy == "direct"
        assert len(result.answer) > 0

    @pytest.mark.asyncio
    async def test_multi_hop_query_expands_graph(self, retriever):
        # This query requires multi-hop reasoning
        result = await retriever.retrieve(
            "Who founded the company that created Kubernetes?"
        )

        assert result.query_type == "MULTI_HOP"
        assert result.execution_strategy == "sequential_with_graph_expansion"
        assert len(result.sub_queries) >= 2
        # Should have accumulated entities across hops
        assert len(result.graph_context.entities) > 0


# E2E test
# frontend/e2e/tests/chat/multi-hop-query.spec.ts
test('multi-hop query shows graph context', async ({ page }) => {
  await page.goto('/');

  // Ask a multi-hop question
  await page.fill('[data-testid="message-input"]',
    'Who founded the company that created Kubernetes?');
  await page.click('[data-testid="send-button"]');

  // Wait for streaming response
  await page.waitForSelector('[data-testid="assistant-message"]');

  // Verify response mentions the connection
  const response = await page.textContent('[data-testid="assistant-message"]');
  expect(response).toContain('Google');  // K8s was created by Google
});
```

### Deliverables
```
src/components/retrieval/graph_rag_retriever.py (NEW - 450 LOC)
src/api/v1/chat.py (updated for GraphRAG routing)
tests/components/retrieval/test_graph_rag_retriever.py
tests/integration/test_graph_rag_e2e.py
frontend/e2e/tests/chat/multi-hop-query.spec.ts
docs/adr/ADR-042-graphrag-multi-hop.md
```

### Acceptance Criteria
- [ ] MULTI_HOP queries automatically use GraphRAG
- [ ] Sub-queries execute sequentially with context injection
- [ ] Graph expansion finds connected entities within N hops
- [ ] Answer generation includes relationship paths
- [ ] Logging shows multi-hop execution flow
- [ ] Unit tests pass for GraphContext and GraphRAGRetriever
- [ ] E2E test verifies multi-hop answer quality

---

## Sprint Schedule

| Day | Features | Deliverables |
|-----|----------|--------------|
| Day 1 (Mon) | 38.1: Login Page + Auth Context | LoginPage.tsx, AuthContext.tsx |
| Day 2 (Tue) | 38.1: API Client + Protected Routes | api.ts, ProtectedRoute.tsx |
| Day 3 (Wed) | 38.2: Conversation Search | ConversationSearch.tsx, ArchiveButton.tsx |
| Day 4 (Thu) | 38.3: Share Links + 38.4 Start | ShareModal.tsx, graph_rag_retriever.py |
| Day 5 (Fri) | 38.4: GraphRAG Integration + Tests | Chat integration, E2E tests |

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Neo4j performance with deep traversal | High | Limit max_hops to 2, add query timeout |
| LLM costs for multi-hop | Medium | Use local model for classification, cloud for generation |
| Auth breaking existing features | High | Feature flag for auth requirement |
| GraphRAG answer quality | Medium | Fallback to standard RAG if confidence low |

---

## Definition of Done

- [ ] All features implemented and tested
- [ ] E2E tests passing (>90%)
- [ ] Unit test coverage >80%
- [ ] No TypeScript/Python type errors
- [ ] Documentation updated (ADR-042 for GraphRAG)
- [ ] Code reviewed and merged to main
- [ ] CLAUDE.md updated with Sprint 38 status

---

## Related Documents

- [TD-056: Project Collaboration System](../technical-debt/TD-056_PROJECT_COLLABORATION_SYSTEM.md)
- [Neo4j GraphRAG Article](https://neo4j.com/blog/genai/knowledge-graph-llm-multi-hop-reasoning/)
- `src/components/retrieval/query_decomposition.py` - Existing decomposition
- `src/components/graph_rag/dual_level_search.py` - Existing graph search
- `src/api/routers/graph_viz.py` - Existing multi-hop endpoint
