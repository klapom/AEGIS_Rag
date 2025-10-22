# Sprint 13 Plan: E2E Test Completion & React Migration Phase 1

**Sprint Goal:** Achieve 70%+ E2E test pass rate and begin React Frontend Migration
**Duration:** 2 Wochen
**Story Points:** 44 SP (High Priority: 29 SP, Medium: 13 SP, Low: 7 SP)
**Start Date:** TBD
**Branch:** `sprint-13-dev`

---

## Executive Summary

Sprint 13 focuses on **test infrastructure completion** and **React Frontend Migration Phase 1**. With production deployment readiness achieved in Sprint 12, we now prioritize increasing test coverage from ~38% to 70%+ and replacing Gradio with a professional React frontend.

### Critical Priorities (Week 1)

1. **Complete E2E Test Fixes (8 SP):** Fix remaining 27 failing tests from Sprint 12
   - Memory agent event loop cleanup (4 errors)
   - Graphiti API compatibility (18 skipped tests)
   - LightRAG fixture connection stability (5 tests)
   - pytest-timeout integration

2. **CI/CD Pipeline Finalization (3 SP):** Test timeout, parallel execution, coverage reporting

### Strategic Priorities (Week 2)

3. **React Frontend Migration - Phase 1 (13 SP):** Replace Gradio with React + Next.js
   - Server-Sent Events for streaming responses
   - Authentication with NextAuth.js
   - Full UI customization with Tailwind CSS

### Medium Priority (If Time Permits)

4. **Performance Optimization (5 SP):** Community detection caching, LLM batching
5. **Integration Test Completion (5 SP):** Implement 22 placeholder tests

---

## Features Overview

| ID | Feature | SP | Priority | Dependencies | Status |
|----|---------|----|---------| -------------|--------|
| **WEEK 1: TEST INFRASTRUCTURE** |
| 13.1 | Fix Memory Agent Event Loop Errors | 2 | 🔴 CRITICAL | None | 📋 TODO |
| 13.2 | Fix Graphiti API Compatibility | 3 | 🔴 CRITICAL | None | 📋 TODO |
| 13.3 | Fix LightRAG Fixture Connection | 2 | 🔴 CRITICAL | None | 📋 TODO |
| 13.4 | Add pytest-timeout Plugin | 1 | 🟠 HIGH | None | 📋 TODO |
| 13.5 | CI/CD Pipeline Enhancements | 3 | 🟠 HIGH | 13.4 | 📋 TODO |
| **WEEK 2: REACT MIGRATION** |
| 13.6 | React Project Setup | 2 | 🟠 HIGH | None | 📋 TODO |
| 13.7 | Basic Chat UI Component | 3 | 🟠 HIGH | 13.6 | 📋 TODO |
| 13.8 | Server-Sent Events Streaming | 3 | 🟠 HIGH | 13.7 | 📋 TODO |
| 13.9 | NextAuth.js Authentication | 3 | 🟠 HIGH | 13.6 | 📋 TODO |
| 13.10 | Tailwind CSS Styling | 2 | 🟠 HIGH | 13.6, 13.7 | 📋 TODO |
| **MEDIUM PRIORITY** |
| 13.11 | Community Detection Caching | 2 | 🟡 MEDIUM | None | 📋 TODO |
| 13.12 | LLM Labeling Batching | 2 | 🟡 MEDIUM | None | 📋 TODO |
| 13.13 | Cache Invalidation Patterns | 1 | 🟡 MEDIUM | None | 📋 TODO |
| 13.14 | Implement Placeholder Integration Tests | 5 | 🟡 MEDIUM | None | 📋 TODO |
| 13.15 | Graph Viz Pagination | 3 | 🟡 MEDIUM | None | 📋 TODO |
| **LOW PRIORITY** |
| 13.16 | Export Functionality (CSV/JSON) | 2 | 🟢 LOW | None | 📋 TODO |
| 13.17 | Documentation Updates | 2 | 🟢 LOW | None | 📋 TODO |
| 13.18 | Security Enhancements | 3 | 🟢 LOW | 13.9 | 📋 TODO |
| **TOTAL** | | **44** | | | |

---

## Week 1: Critical Test Infrastructure Fixes

### Feature 13.1: Fix Memory Agent Event Loop Errors (2 SP)

**Priority:** 🔴 CRITICAL
**Category:** Testing / AsyncIO
**Technical Debt:** TD-26 (NEW)

#### Current Issue

4 integration tests fail during teardown with event loop errors:

```
ERROR at teardown of test_memory_agent_process_with_coordinator_e2e
ERROR at teardown of test_memory_agent_state_management_e2e
ERROR at teardown of test_memory_agent_latency_target_e2e
ERROR at teardown of test_session_context_endpoint_e2e

RuntimeError: Event loop is closed
RuntimeError: Task <Task pending> got Future attached to a different loop
```

**Tests Affected:**
- `tests/integration/agents/test_memory_agent_e2e.py` (3 tests)
- `tests/integration/api/test_memory_api_e2e.py` (1 test)

#### Root Cause Analysis

**Hypothesis 1:** Async fixture cleanup timing
- Memory agent fixtures may be using different event loops
- Cleanup happens after pytest event loop is closed

**Hypothesis 2:** Graphiti async cleanup incomplete
- Similar to Redis async cleanup (TD-25, resolved in Sprint 12)
- Graphiti wrapper needs proper aclose() method

#### Solution

1. **Add aclose() to GraphitiWrapper:**
   ```python
   # src/components/memory/graphiti_wrapper.py
   class GraphitiWrapper:
       async def aclose(self) -> None:
           """Close Graphiti client and Neo4j connections."""
           if self.client:
               await self.client.close()  # If Graphiti has async close
               self.client = None
   ```

2. **Update conftest.py fixture:**
   ```python
   # tests/conftest.py
   @pytest.fixture
   async def graphiti_wrapper(neo4j_driver):
       wrapper = GraphitiWrapper()
       yield wrapper
       await wrapper.aclose()  # Proper cleanup
   ```

3. **Ensure event loop consistency:**
   ```python
   # tests/conftest.py
   @pytest.fixture(scope="function")
   def event_loop():
       """Create event loop for each test."""
       loop = asyncio.new_event_loop()
       yield loop
       loop.close()
   ```

#### Acceptance Criteria
- [ ] All 4 memory agent tests pass without teardown errors
- [ ] No "Event loop is closed" errors
- [ ] No "Task attached to different loop" errors
- [ ] GraphitiWrapper has proper async cleanup

#### Verification
```bash
poetry run pytest tests/integration/agents/test_memory_agent_e2e.py -v
poetry run pytest tests/integration/api/test_memory_api_e2e.py -v
# Expected: 4 tests PASSED, 0 errors
```

---

### Feature 13.2: Fix Graphiti API Compatibility (3 SP)

**Priority:** 🔴 CRITICAL
**Category:** Integration / Dependencies
**Technical Debt:** TD-27 (NEW)

#### Current Issue

18 Graphiti tests skipped due to constructor signature change:

```
SKIPPED: Graphiti not available: Failed to initialize Graphiti:
Graphiti.__init__() got an unexpected keyword argument 'neo4j_uri'
```

**Tests Affected:**
- `tests/integration/memory/test_graphiti_e2e.py` (18 tests)

#### Root Cause Analysis

**Graphiti Library Breaking Change:**
- Sprint 12 Feature 12.2 fixed `generate_response()` → `_generate_response()`
- However, constructor signature also changed
- Old: `Graphiti(neo4j_uri="...", neo4j_user="...", neo4j_password="...")`
- New: Unknown constructor signature (need to check Graphiti docs)

#### Investigation Steps

1. **Check Graphiti library version:**
   ```bash
   poetry show graphiti-core
   ```

2. **Review Graphiti documentation:**
   - Check official docs for current constructor API
   - Check GitHub releases for breaking changes

3. **Inspect current GraphitiWrapper implementation:**
   ```bash
   grep -A 20 "class GraphitiWrapper" src/components/memory/graphiti_wrapper.py
   ```

#### Solution (Placeholder - Needs Investigation)

**Option A: Update Constructor Signature**
```python
# src/components/memory/graphiti_wrapper.py
class GraphitiWrapper:
    def __init__(self):
        # OLD (Sprint 7):
        # self.client = Graphiti(
        #     neo4j_uri=settings.neo4j_uri,
        #     neo4j_user=settings.neo4j_user,
        #     neo4j_password=settings.neo4j_password,
        # )

        # NEW (Sprint 13 - needs verification):
        self.client = Graphiti(
            neo4j_config={
                "uri": settings.neo4j_uri,
                "user": settings.neo4j_user,
                "password": settings.neo4j_password,
            },
            # Other required params?
        )
```

**Option B: Pin Graphiti Version**
```toml
# pyproject.toml
[tool.poetry.dependencies]
graphiti-core = "0.2.0"  # Pin to working version
```

**Option C: Use Graphiti Builder Pattern**
```python
self.client = GraphitiBuilder()
    .with_neo4j(uri, user, password)
    .with_llm(ollama_client)
    .build()
```

#### Acceptance Criteria
- [ ] GraphitiWrapper initializes without errors
- [ ] 18 skipped tests now run
- [ ] Graphiti integration tests pass
- [ ] Memory system functional with Graphiti

#### Verification
```bash
poetry run pytest tests/integration/memory/test_graphiti_e2e.py -v
# Expected: 18 tests PASSED (or at least attempted, not skipped)
```

---

### Feature 13.3: Fix LightRAG Fixture Connection (2 SP)

**Priority:** 🔴 CRITICAL
**Category:** Testing / Integration
**Technical Debt:** TD-28 (NEW)

#### Current Issue

5 Sprint 5 E2E tests updated to use `lightrag_instance` fixture (Feature 12.1) but tests fail at setup:

```
ERROR: fixture 'lightrag_instance' not found
```

**Tests Affected:**
- `tests/integration/test_sprint5_critical_e2e.py::test_graph_construction_full_pipeline_e2e`
- `tests/integration/test_sprint5_critical_e2e.py::test_local_search_entity_level_e2e`
- `tests/integration/test_sprint5_critical_e2e.py::test_global_search_topic_level_e2e`
- `tests/integration/test_sprint5_critical_e2e.py::test_hybrid_search_local_global_e2e`
- `tests/integration/test_sprint5_critical_e2e.py::test_incremental_graph_updates_e2e`

#### Root Cause Analysis

**Sprint 12 Feature 12.1 Documentation states:**
> "Added lightrag_instance fixture parameter to all 5 tests"

**However:**
- SPRINT_12_E2E_TEST_REPORT.md confirms: `fixture 'lightrag_instance' not found`
- Fixture exists in `tests/conftest.py:41-85` (Sprint 11 implementation)
- **Possible causes:**
  1. Fixture exists but Neo4j connection timing issues
  2. Fixture name mismatch (lightrag_instance vs lightrag_wrapper)
  3. Fixture scope issue (session vs function)

#### Investigation Steps

1. **Check if fixture exists:**
   ```bash
   pytest --fixtures | grep lightrag
   ```

2. **Review fixture implementation:**
   ```bash
   grep -A 30 "def lightrag_instance" tests/conftest.py
   ```

3. **Check test signatures:**
   ```bash
   grep -B 2 "async def test.*e2e.*lightrag" tests/integration/test_sprint5_critical_e2e.py
   ```

#### Solution

**Step 1: Verify/Create lightrag_instance Fixture**
```python
# tests/conftest.py
@pytest.fixture(scope="session")
async def lightrag_instance(neo4j_driver, ollama_client_real):
    """LightRAG singleton with Neo4j cleanup.

    Sprint 11: Uses singleton LightRAG instance (avoids re-initialization)
    but cleans Neo4j database before each test for isolation.
    """
    from src.components.graph_rag.lightrag_wrapper import LightRAGWrapper, reset_singleton

    # Clean Neo4j before tests
    async with neo4j_driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")

    # Reset singleton to force re-initialization with clean DB
    reset_singleton()

    # Get singleton instance
    wrapper = await get_lightrag_wrapper_async()

    yield wrapper

    # Cleanup after session
    reset_singleton()
```

**Step 2: Ensure Test Uses Fixture**
```python
# tests/integration/test_sprint5_critical_e2e.py
@pytest.mark.asyncio
async def test_graph_construction_full_pipeline_e2e(lightrag_instance):
    """Test full LightRAG pipeline."""
    wrapper = lightrag_instance  # Use fixture

    # Test continues...
```

**Step 3: Handle Async Initialization**
```python
# If fixture needs to be function-scoped for isolation:
@pytest.fixture(scope="function")  # Changed from session
async def lightrag_instance(neo4j_driver):
    # Cleanup, init, yield, cleanup
    ...
```

#### Acceptance Criteria
- [ ] Fixture is discoverable via `pytest --fixtures`
- [ ] 5 tests run without "fixture not found" error
- [ ] Tests can access lightrag_instance
- [ ] Neo4j database is properly cleaned between tests
- [ ] No pickle errors occur

#### Verification
```bash
pytest --fixtures | grep lightrag  # Fixture exists
poetry run pytest tests/integration/test_sprint5_critical_e2e.py::test_graph_construction_full_pipeline_e2e -v
# Expected: PASSED (not ERROR at setup)
```

---

### Feature 13.4: Add pytest-timeout Plugin (1 SP)

**Priority:** 🟠 HIGH
**Category:** Testing / DevOps
**Technical Debt:** TD-29 (NEW)

#### Current Issue

```bash
poetry run pytest tests/integration/ --timeout=300
ERROR: unrecognized arguments: --timeout=300
```

**Impact:**
- Cannot enforce test timeouts locally
- Long-running tests can hang development workflow
- CI/CD has timeout enforcement, but local dev doesn't

#### Solution

**Step 1: Add to pyproject.toml**
```toml
# pyproject.toml
[tool.poetry.group.dev.dependencies]
pytest-timeout = "^2.2.0"
```

**Step 2: Install**
```bash
poetry install --with dev
```

**Step 3: Configure in pytest.ini**
```ini
# pytest.ini
[pytest]
# Timeout for tests (prevent hanging)
timeout = 300  # 5 minutes default
timeout_method = thread  # or signal (Unix only)
```

**Step 4: Use in Tests**
```python
# For specific test with custom timeout
@pytest.mark.timeout(600)  # 10 minutes
async def test_large_document_processing_e2e():
    ...
```

#### Acceptance Criteria
- [ ] pytest-timeout installed in dev dependencies
- [ ] --timeout flag recognized
- [ ] Default 300s timeout configured
- [ ] Tests fail after timeout (not hang)

#### Verification
```bash
poetry show pytest-timeout  # Installed
poetry run pytest --version  # Shows timeout plugin
poetry run pytest tests/integration/ --timeout=10  # Should timeout some tests
```

---

### Feature 13.5: CI/CD Pipeline Enhancements (3 SP)

**Priority:** 🟠 HIGH
**Category:** DevOps / CI/CD
**Dependencies:** Feature 13.4

#### Current Status

Sprint 12 CI/CD improvements:
- ✅ Ollama service added
- ✅ 20min timeout for integration tests
- ✅ Docker cache configured
- ✅ Model pulling automated

**Remaining Improvements Needed:**
1. Test timeout enforcement in CI
2. Parallel test execution
3. Coverage reporting integration
4. Test result artifacts

#### Solution

**1. Enable pytest-timeout in CI:**
```yaml
# .github/workflows/ci.yml
- name: Run Integration Tests
  timeout-minutes: 20
  run: |
    poetry run pytest tests/integration/ \
      --cov=src \
      --cov-report=xml \
      --timeout=300 \      # NEW: Per-test timeout
      --timeout-method=thread \
      -v
```

**2. Parallel Test Execution:**
```yaml
# Install pytest-xdist
[tool.poetry.group.dev.dependencies]
pytest-xdist = "^3.5.0"

# Run tests in parallel
poetry run pytest tests/integration/ -n auto  # Use all CPU cores
```

**3. Coverage Reporting:**
```yaml
# .github/workflows/ci.yml
- name: Upload Coverage to Codecov
  uses: codecov/codecov-action@v4
  with:
    file: ./coverage.xml
    flags: integration
    fail_ci_if_error: true  # NEW: Fail if coverage upload fails
```

**4. Test Result Artifacts:**
```yaml
# .github/workflows/ci.yml
- name: Upload Test Results
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: test-results
    path: |
      test_*.txt
      pytest_report.html
      coverage.xml
```

#### Acceptance Criteria
- [ ] pytest-timeout enabled in CI
- [ ] Parallel test execution (pytest-xdist)
- [ ] Coverage reports uploaded to Codecov
- [ ] Test results available as artifacts
- [ ] CI fails fast on first test failure (optional: --maxfail=1)

#### Verification
```bash
# Local parallel execution test
poetry install --with dev
poetry run pytest tests/unit/ -n auto -v
# Expected: Tests run in parallel, faster completion
```

---

## Week 2: React Frontend Migration - Phase 1

### Feature 13.6: React Project Setup (2 SP)

**Priority:** 🟠 HIGH
**Category:** Frontend / Architecture
**Technical Debt:** TD-03, TD-05, TD-06, TD-08 (Gradio limitations)

#### Implementation

**1. Create Next.js Project:**
```bash
# In project root
npx create-next-app@latest frontend \
  --typescript \
  --tailwind \
  --app \
  --src-dir \
  --import-alias "@/*"

cd frontend
npm install
```

**2. Project Structure:**
```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx              # Home page
│   │   ├── layout.tsx            # Root layout
│   │   └── api/
│   │       ├── auth/[...nextauth].ts
│   │       └── chat/stream.ts    # SSE endpoint
│   ├── components/
│   │   ├── Chat/
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── ChatMessage.tsx
│   │   │   └── ChatInput.tsx
│   │   └── Upload/
│   │       └── DocumentUpload.tsx
│   ├── lib/
│   │   ├── api.ts                # API client
│   │   └── auth.ts               # Auth helpers
│   └── styles/
│       └── globals.css
├── public/
├── package.json
└── tsconfig.json
```

**3. Configure API Proxy:**
```typescript
// next.config.js
module.exports = {
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:8000/api/v1/:path*',
      },
    ];
  },
};
```

**4. Install Dependencies:**
```json
// package.json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "next-auth": "^4.24.0",
    "tailwindcss": "^3.3.0",
    "lucide-react": "^0.300.0",  // Icons
    "react-markdown": "^9.0.0",   // Markdown rendering
    "react-syntax-highlighter": "^15.5.0"  // Code highlighting
  }
}
```

#### Acceptance Criteria
- [ ] Next.js 14+ project created
- [ ] TypeScript configured
- [ ] Tailwind CSS integrated
- [ ] API proxy configured
- [ ] Project builds without errors (`npm run build`)

---

### Feature 13.7: Basic Chat UI Component (3 SP)

**Priority:** 🟠 HIGH
**Category:** Frontend / UI
**Dependencies:** Feature 13.6

#### Implementation

**1. Chat Interface Component:**
```typescript
// src/components/Chat/ChatInterface.tsx
'use client';

import { useState } from 'react';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (query: string) => {
    setIsLoading(true);

    // Add user message
    setMessages([...messages, { role: 'user', content: query }]);

    try {
      // Call API (to be implemented in Feature 13.8)
      const response = await fetch('/api/v1/chat/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, strategy: 'simple' }),
      });

      const data = await response.json();

      // Add assistant message
      setMessages([...messages, {
        role: 'assistant',
        content: data.answer,
        sources: data.sources
      }]);
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <ChatMessage key={i} message={msg} />
        ))}
      </div>
      <ChatInput onSend={sendMessage} isLoading={isLoading} />
    </div>
  );
}
```

**2. Chat Message Component:**
```typescript
// src/components/Chat/ChatMessage.tsx
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';

export function ChatMessage({ message }) {
  return (
    <div className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-2xl p-4 rounded-lg ${
        message.role === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-100'
      }`}>
        <ReactMarkdown
          components={{
            code({ node, inline, className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || '');
              return !inline && match ? (
                <SyntaxHighlighter language={match[1]} {...props}>
                  {String(children).replace(/\n$, '')}
                </SyntaxHighlighter>
              ) : (
                <code className={className} {...props}>{children}</code>
              );
            },
          }}
        >
          {message.content}
        </ReactMarkdown>

        {message.sources && (
          <div className="mt-2 text-sm opacity-70">
            Sources: {message.sources.length} documents
          </div>
        )}
      </div>
    </div>
  );
}
```

**3. Chat Input Component:**
```typescript
// src/components/Chat/ChatInput.tsx
'use client';

import { useState } from 'react';
import { Send } from 'lucide-react';

export function ChatInput({ onSend, isLoading }) {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSend(input);
      setInput('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 border-t">
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          className="flex-1 p-2 border rounded-lg"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg disabled:opacity-50"
        >
          <Send size={20} />
        </button>
      </div>
    </form>
  );
}
```

#### Acceptance Criteria
- [ ] Chat interface renders correctly
- [ ] User can type and send messages
- [ ] Messages display with proper styling
- [ ] Markdown rendering works (bold, italic, code, lists)
- [ ] Loading state shows during API calls
- [ ] Sources are displayed below messages

---

### Feature 13.8: Server-Sent Events Streaming (3 SP)

**Priority:** 🟠 HIGH
**Category:** Frontend / Backend
**Dependencies:** Feature 13.7
**Technical Debt:** TD-05 (No Real-Time Streaming)

#### Implementation

**1. Backend Streaming Endpoint:**
```python
# src/api/v1/chat.py
from fastapi.responses import StreamingResponse

@router.post("/chat/stream")
async def chat_stream(query: QueryRequest) -> StreamingResponse:
    """Stream chat response with Server-Sent Events."""

    async def event_generator():
        # Initialize answer generator
        generator = AnswerGenerator()

        # Stream tokens as they're generated
        async for token in generator.stream_answer(
            query=query.query,
            contexts=retrieved_contexts,
        ):
            # SSE format: data: {json}\n\n
            yield f"data: {json.dumps({'token': token})}\n\n"

        # Send completion event
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
```

**2. Frontend Streaming Consumer:**
```typescript
// src/lib/api.ts
export async function streamChat(query: string, onToken: (token: string) => void) {
  const response = await fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, strategy: 'simple' }),
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader!.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        if (data.token) {
          onToken(data.token);
        }
      }
    }
  }
}
```

**3. Update Chat Interface:**
```typescript
// src/components/Chat/ChatInterface.tsx (updated)
const sendMessage = async (query: string) => {
  setIsLoading(true);
  setMessages([...messages, { role: 'user', content: query }]);

  let assistantMessage = '';

  await streamChat(query, (token) => {
    // Update assistant message as tokens arrive
    assistantMessage += token;
    setMessages([
      ...messages,
      { role: 'assistant', content: assistantMessage }
    ]);
  });

  setIsLoading(false);
};
```

#### Acceptance Criteria
- [ ] Backend streams tokens via SSE
- [ ] Frontend receives and displays tokens in real-time
- [ ] User sees progressive response (not batch)
- [ ] Connection properly closes after completion
- [ ] Error handling for connection failures

---

### Feature 13.9: NextAuth.js Authentication (3 SP)

**Priority:** 🟠 HIGH
**Category:** Security / Authentication
**Dependencies:** Feature 13.6
**Technical Debt:** TD-06 (Single User / No Authentication)

#### Implementation

**1. Install NextAuth.js:**
```bash
cd frontend
npm install next-auth
```

**2. Configure Auth Provider:**
```typescript
// src/app/api/auth/[...nextauth]/route.ts
import NextAuth from 'next-auth';
import GithubProvider from 'next-auth/providers/github';
import CredentialsProvider from 'next-auth/providers/credentials';

const handler = NextAuth({
  providers: [
    GithubProvider({
      clientId: process.env.GITHUB_ID!,
      clientSecret: process.env.GITHUB_SECRET!,
    }),
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        // Validate credentials against backend
        const res = await fetch('http://localhost:8000/api/v1/auth/login', {
          method: 'POST',
          body: JSON.stringify(credentials),
          headers: { "Content-Type": "application/json" }
        });

        if (res.ok) {
          return await res.json();
        }
        return null;
      },
    }),
  ],
  session: {
    strategy: 'jwt',
  },
  pages: {
    signIn: '/auth/signin',
  },
});

export { handler as GET, handler as POST };
```

**3. Protect Routes:**
```typescript
// src/app/page.tsx
'use client';

import { useSession } from 'next-auth/react';
import { redirect } from 'next/navigation';

export default function ChatPage() {
  const { data: session, status } = useSession();

  if (status === 'loading') {
    return <div>Loading...</div>;
  }

  if (!session) {
    redirect('/auth/signin');
  }

  return <ChatInterface user={session.user} />;
}
```

**4. Backend Auth Middleware:**
```python
# src/api/dependencies.py
from fastapi import Header, HTTPException
import jwt

async def get_current_user(authorization: str = Header(None)) -> str:
    """Validate JWT token from NextAuth."""
    if not authorization:
        raise HTTPException(401, "Missing Authorization header")

    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload["sub"]  # User ID
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
```

#### Acceptance Criteria
- [ ] NextAuth.js configured with GitHub OAuth
- [ ] Users can sign in via GitHub
- [ ] Session persists across page reloads
- [ ] Protected routes redirect to sign-in
- [ ] Backend validates JWT tokens
- [ ] User isolation works (each user has own session)

---

### Feature 13.10: Tailwind CSS Styling (2 SP)

**Priority:** 🟠 HIGH
**Category:** UI / Design
**Dependencies:** Features 13.6, 13.7
**Technical Debt:** TD-08 (Limited UI Customization)

#### Implementation

**1. Tailwind Configuration:**
```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
        },
        // Bundeswehr colors (if needed)
        bundeswehr: {
          green: '#4a5f3a',
          gold: '#d4af37',
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),  // For markdown
    require('@tailwindcss/forms'),        // For form inputs
  ],
};
```

**2. Global Styles:**
```css
/* src/styles/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer components {
  .chat-container {
    @apply flex flex-col h-screen max-w-7xl mx-auto;
  }

  .chat-message-user {
    @apply bg-primary-500 text-white p-4 rounded-lg max-w-2xl ml-auto;
  }

  .chat-message-assistant {
    @apply bg-gray-100 p-4 rounded-lg max-w-2xl;
  }

  .chat-input {
    @apply w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500;
  }
}
```

**3. Dark Mode Support:**
```typescript
// src/app/layout.tsx
export default function RootLayout({ children }) {
  return (
    <html lang="de" className="dark">
      <body className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
        {children}
      </body>
    </html>
  );
}
```

#### Acceptance Criteria
- [ ] Tailwind CSS fully configured
- [ ] Custom color palette applied
- [ ] Typography plugin for markdown
- [ ] Forms plugin for inputs
- [ ] Dark mode support
- [ ] Responsive design (mobile, tablet, desktop)

---

## Medium Priority Features

### Feature 13.11: Community Detection Caching (2 SP)

**Technical Debt:** TD-09
**Priority:** 🟡 MEDIUM

**Implementation:** Add Redis cache for community detection results

---

### Feature 13.12: LLM Labeling Batching (2 SP)

**Technical Debt:** TD-15
**Priority:** 🟡 MEDIUM

**Implementation:** Batch multiple communities in single LLM prompt

---

### Feature 13.13: Cache Invalidation Patterns (1 SP)

**Technical Debt:** TD-11
**Priority:** 🟡 MEDIUM

**Implementation:** Upgrade to regex-based cache invalidation

---

### Feature 13.14: Implement Placeholder Integration Tests (5 SP)

**Technical Debt:** TD-19
**Priority:** 🟡 MEDIUM

**Implementation:** Complete 22 placeholder integration tests from Sprint 9

---

### Feature 13.15: Graph Visualization Pagination (3 SP)

**Technical Debt:** TD-17
**Priority:** 🟡 MEDIUM

**Implementation:** Add pagination, dynamic loading, WebGL renderer

---

## Sprint 13 Success Criteria

### Must Have (Critical Path)
- [ ] E2E test pass rate ≥70% (currently ~38%)
- [ ] All 4 memory agent event loop errors resolved
- [ ] All 18 Graphiti API compatibility tests passing
- [ ] All 5 LightRAG fixture connection tests passing
- [ ] pytest-timeout integrated
- [ ] React project setup complete
- [ ] Basic chat UI functional

### Should Have (High Value)
- [ ] Server-Sent Events streaming working
- [ ] NextAuth.js authentication implemented
- [ ] Tailwind CSS styling applied
- [ ] CI/CD parallel test execution

### Could Have (If Time Permits)
- [ ] Community detection caching
- [ ] LLM labeling batching
- [ ] Integration test placeholders completed

---

## Known Risks & Mitigation

### Risk 1: Graphiti API Investigation Time
**Risk:** Graphiti constructor signature unknown, may take time to investigate
**Mitigation:** Allocate 3 SP (includes investigation), consider pinning version as fallback

### Risk 2: React Learning Curve
**Risk:** Team may be new to Next.js 14 App Router
**Mitigation:** Start with simple components, use official documentation, allocate 13 SP for Phase 1

### Risk 3: Test Fixing Complexity
**Risk:** Event loop errors may be deeper than expected
**Mitigation:** 2 SP allocated, can defer to Sprint 14 if needed (keep low priority)

---

## Sprint 13 Velocity Planning

**Planned:** 44 SP total
**Recommended Focus:** 29 SP (High Priority only)
- Week 1: Test Infrastructure (11 SP)
- Week 2: React Phase 1 (13 SP)
- Buffer: 5 SP for unknowns

**Stretch Goals:** +13 SP (Medium Priority)
**Nice to Have:** +7 SP (Low Priority)

---

## Next Sprints Preview

### Sprint 14: React Phase 2 + Multi-Tenancy
- Document upload UI in React
- MCP tool call visualization
- Session history management
- Multi-tenant architecture
- Advanced authentication (RBAC)

### Sprint 15: Production Deployment & Monitoring
- Production deployment to staging
- Performance monitoring dashboards
- Automated alerting
- Load testing at scale
- Security audit

---

**Sprint 13 Start Date:** TBD
**Sprint 13 End Date:** TBD (2 weeks from start)
**Previous Sprint:** Sprint 12 (COMPLETE - 31/32 SP, 97%)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
