# Sprint 15 Plan: React Frontend Interface

**Sprint Goal:** Build production-ready React frontend for AegisRAG with modern UX/UI

**Status:** 🔵 PLANNED
**Duration:** 7-10 days (depending on design phase)
**Branch:** `sprint-15-react-frontend`
**Prerequisites:** Sprint 14 complete (Backend + Testing Infrastructure)

---

## Executive Summary

Sprint 15 delivers the user-facing React frontend for AegisRAG, enabling users to:
- Submit queries via intuitive search interface
- Select retrieval modes (Vector, Graph, Hybrid, Memory)
- View contextual search results with provenance
- Manage conversation history
- Monitor system health and performance

**Key Decision:** Design-First Approach with Figma (optional, see workflow below)

---

## Design Strategy

### Option A: Design-First (Recommended)

**Phase 1: Design Week (2-3 days)**
1. Create Figma mockups for all features
2. Define component library (Design System)
3. Export design tokens (colors, spacing, typography)
4. Review and align on UX flows

**Phase 2: Implementation Week (5-7 days)**
1. Setup React project with Vite + TypeScript
2. Implement component library
3. Build features based on Figma specs
4. Integration testing with FastAPI backend

**Deliverables from Design Phase:**
- High-fidelity Figma mockups
- Component structure definition
- Design tokens (CSS variables)
- User flow diagrams

### Option B: Code-First (Fallback)

1. Use Material-UI or Shadcn/UI as base
2. Implement standard RAG interface patterns
3. Iterate based on user feedback

---

## Feature Breakdown

### Feature 15.1: Project Setup & Infrastructure

**Goal:** Setup modern React development environment

**Deliverables:**
- ✅ React 18 + Vite + TypeScript project
- ✅ Tailwind CSS (or MUI based on design choice)
- ✅ React Router v6 for navigation
- ✅ Axios for API calls
- ✅ React Query (TanStack Query) for data fetching
- ✅ Zustand or Redux Toolkit for state management
- ✅ Vitest + React Testing Library for tests
- ✅ ESLint + Prettier configuration
- ✅ Docker setup for frontend

**Technical Stack:**
```json
{
  "framework": "React 18",
  "bundler": "Vite 5",
  "language": "TypeScript 5",
  "styling": "Tailwind CSS 3 (or MUI)",
  "routing": "React Router 6",
  "state": "Zustand / Redux Toolkit",
  "data-fetching": "TanStack Query (React Query)",
  "testing": "Vitest + React Testing Library",
  "ui-components": "Shadcn/UI or MUI"
}
```

**File Structure:**
```
frontend/
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── ui/           # Base UI (Button, Input, Card)
│   │   ├── layout/       # Layout components (Header, Sidebar)
│   │   └── features/     # Feature-specific components
│   ├── pages/            # Route pages
│   ├── hooks/            # Custom React hooks
│   ├── services/         # API services
│   ├── stores/           # State management
│   ├── utils/            # Helper functions
│   ├── types/            # TypeScript types
│   └── App.tsx
├── public/
├── tests/
├── Dockerfile
├── vite.config.ts
├── tailwind.config.js
└── package.json
```

**Story Points:** 8 SP
**Duration:** 1 day

---

### Feature 15.2: Query Interface

**Goal:** Intuitive search interface with mode selection

**Deliverables:**
- ✅ Search bar with auto-complete
- ✅ Mode selector (Vector, Graph, Hybrid, Memory)
- ✅ Advanced filters (date range, entity types)
- ✅ Query history dropdown
- ✅ Real-time validation
- ✅ Loading states and error handling

**UI Components:**
1. **SearchBar Component**
   - Large input field with search icon
   - Auto-complete suggestions (based on query history)
   - Clear button
   - Keyboard shortcuts (Cmd/Ctrl + K to focus)

2. **ModeSelector Component**
   - Radio buttons or tabs: Vector | Graph | Hybrid | Memory
   - Tooltips explaining each mode
   - Default: Hybrid

3. **AdvancedFilters Component**
   - Collapsible panel
   - Date range picker
   - Entity type multi-select (Person, Organization, Location)
   - Top-K slider (1-20 results)
   - Rerank toggle

4. **QueryHistory Component**
   - Dropdown with last 10 queries
   - Click to re-run query
   - Clear history button

**API Integration:**
```typescript
// services/query.service.ts
interface QueryRequest {
  query: string;
  mode: 'vector' | 'graph' | 'hybrid' | 'memory';
  filters?: {
    dateRange?: [Date, Date];
    entityTypes?: string[];
    topK?: number;
    rerank?: boolean;
  };
}

interface QueryResponse {
  query: string;
  mode: string;
  results: SearchResult[];
  metadata: {
    total_results: number;
    processing_time_ms: number;
    agent_path: string[];
  };
}

export async function submitQuery(request: QueryRequest): Promise<QueryResponse> {
  const response = await axios.post('/api/v1/query', request);
  return response.data;
}
```

**User Flows (to be designed in Figma):**
1. User types query → Auto-complete suggestions → Select/Hit Enter
2. User selects mode → Advanced filters open → Apply filters → Submit
3. User clicks query history → Previous query loads → Edit → Re-submit

**Story Points:** 13 SP
**Duration:** 2-3 days

---

### Feature 15.3: Results Display

**Goal:** Rich, contextual display of search results with provenance

**Deliverables:**
- ✅ Result cards with metadata
- ✅ Provenance information (source documents, chunks)
- ✅ Relevance scores visualization
- ✅ Entity highlighting in context
- ✅ Expandable details view
- ✅ Export results (JSON, CSV)

**UI Components:**

1. **ResultsList Component**
   - Virtualized list for performance (react-window)
   - Grid or list view toggle
   - Sort options (relevance, date, entity count)

2. **ResultCard Component**
   ```
   ┌─────────────────────────────────────────┐
   │ [Score: 0.85] [Vector] [Graph]          │
   │ Entity: Alice (PERSON)                  │
   │ Context: "Alice works at TechCorp..."   │
   │                                          │
   │ Source: document_123.pdf (chunk 5/10)   │
   │ Entities: [Alice] [TechCorp] [SF]       │
   │                                          │
   │ [Expand Details] [View Graph] [Export]  │
   └─────────────────────────────────────────┘
   ```

3. **ProvenancePanel Component**
   - Document metadata (title, author, date)
   - Chunk information (chunk index, text preview)
   - LightRAG provenance (original text location)
   - Relationship graph visualization (if graph result)

4. **EntityHighlight Component**
   - Highlighted entities in context text
   - Color-coded by type (Person, Org, Location)
   - Hover to see entity details

5. **GraphVisualization Component** (if applicable)
   - Interactive graph using D3.js or vis.js
   - Show entities and relationships
   - Click to explore neighbors

**Example Result Data:**
```typescript
interface SearchResult {
  id: string;
  score: number;
  retrieval_modes: ('vector' | 'graph' | 'memory')[];
  entity: {
    name: string;
    type: string;
    description?: string;
  };
  context: string;
  source: {
    document_id: string;
    document_title: string;
    chunk_index: number;
    total_chunks: number;
  };
  entities: Array<{
    text: string;
    type: string;
    start_pos: number;
    end_pos: number;
  }>;
  relationships?: Array<{
    source: string;
    relation: string;
    target: string;
  }>;
}
```

**Story Points:** 21 SP
**Duration:** 3-4 days

---

### Feature 15.4: Conversation History & Memory

**Goal:** Multi-turn conversation support with persistent memory

**Deliverables:**
- ✅ Conversation thread view (chat-like interface)
- ✅ Session management (create, list, delete)
- ✅ Memory state visualization
- ✅ Context window indicator

**UI Components:**

1. **ConversationThread Component**
   - Chat-like interface
   - User queries on right, system responses on left
   - Timestamp for each message
   - "Continue this conversation" button

2. **SessionSidebar Component**
   - List of past sessions
   - Create new session button
   - Delete/Archive session
   - Session metadata (date, query count)

3. **MemoryStatePanel Component**
   - Current memory entries (short-term, semantic, episodic)
   - Memory size indicator
   - Clear memory button

**API Integration:**
```typescript
interface ConversationSession {
  session_id: string;
  created_at: string;
  last_updated: string;
  query_count: number;
  messages: ConversationMessage[];
}

interface ConversationMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  metadata?: {
    results_count?: number;
    processing_time_ms?: number;
  };
}

export async function createSession(): Promise<ConversationSession> {
  const response = await axios.post('/api/v1/sessions');
  return response.data;
}

export async function getSessionHistory(sessionId: string): Promise<ConversationMessage[]> {
  const response = await axios.get(`/api/v1/sessions/${sessionId}/history`);
  return response.data;
}
```

**Story Points:** 13 SP
**Duration:** 2 days

---

### Feature 15.5: System Monitoring Dashboard

**Goal:** Real-time system health and performance monitoring

**Deliverables:**
- ✅ Health status indicators (Qdrant, Neo4j, Ollama, Redis)
- ✅ Query performance metrics (latency, throughput)
- ✅ API endpoint health checks
- ✅ Error log viewer

**UI Components:**

1. **HealthDashboard Component**
   ```
   ┌──────────────────────────────────────────┐
   │ System Status: ● Healthy                 │
   ├──────────────────────────────────────────┤
   │ ✅ Qdrant Vector DB       (latency: 20ms)│
   │ ✅ Neo4j Graph DB         (latency: 35ms)│
   │ ✅ Ollama LLM Service     (latency: 150ms)│
   │ ✅ Redis Memory Cache     (latency: 5ms) │
   ├──────────────────────────────────────────┤
   │ Query Metrics (Last Hour):               │
   │ - Total Queries: 127                     │
   │ - Avg Latency: 450ms (p95: 800ms)        │
   │ - Error Rate: 0.8%                       │
   └──────────────────────────────────────────┘
   ```

2. **DependencyHealthCard Component**
   - Service name
   - Status indicator (green/yellow/red)
   - Latency metric
   - Last checked timestamp

3. **PerformanceChart Component**
   - Real-time line chart (Recharts or Chart.js)
   - Latency over time (last 1h/24h/7d)
   - Throughput (queries per minute)

4. **ErrorLogViewer Component**
   - Table of recent errors
   - Filter by severity (Error, Warning, Info)
   - Expandable stack traces

**API Integration:**
```typescript
interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  environment: string;
  dependencies: {
    qdrant: DependencyHealth;
    neo4j: DependencyHealth;
    ollama: DependencyHealth;
    redis: DependencyHealth;
  };
}

interface DependencyHealth {
  name: string;
  status: 'up' | 'down' | 'degraded';
  latency_ms: number;
  details?: Record<string, any>;
}

export async function getSystemHealth(): Promise<HealthStatus> {
  const response = await axios.get('/api/v1/health/detailed');
  return response.data;
}
```

**Story Points:** 8 SP
**Duration:** 1-2 days

---

### Feature 15.6: Configuration & Settings

**Goal:** User-configurable settings and preferences

**Deliverables:**
- ✅ Theme toggle (Light/Dark mode)
- ✅ Default retrieval mode setting
- ✅ Result display preferences (grid/list, results per page)
- ✅ API endpoint configuration (for self-hosted deployments)

**UI Components:**

1. **SettingsPanel Component**
   - Tabbed interface (Appearance, Query Defaults, Advanced)
   - Save/Reset buttons

2. **ThemeToggle Component**
   - Light/Dark mode switch
   - System preference detection

3. **DefaultsConfiguration Component**
   - Default retrieval mode selector
   - Default top-K value
   - Auto-rerank toggle

**Storage:**
- Use localStorage for user preferences
- Persist theme, default mode, display preferences

**Story Points:** 5 SP
**Duration:** 1 day

---

## Testing Strategy

### Unit Tests (Vitest + React Testing Library)

**Target:** >80% coverage for components

**Test Cases:**
- Component rendering with various props
- User interactions (click, input, select)
- State management (Zustand store mutations)
- API service mocks

**Example Test:**
```typescript
// SearchBar.test.tsx
describe('SearchBar Component', () => {
  it('should call onSubmit when Enter key pressed', () => {
    const mockOnSubmit = vi.fn();
    render(<SearchBar onSubmit={mockOnSubmit} />);

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'test query' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(mockOnSubmit).toHaveBeenCalledWith('test query');
  });
});
```

### Integration Tests

**Test Scenarios:**
1. Submit query → Display results → Select result → View details
2. Create session → Submit multiple queries → View history
3. Change mode → Submit query → Verify correct API call
4. View health dashboard → Check all services healthy

### E2E Tests (Playwright or Cypress)

**Critical User Flows:**
1. First-time user submits query and gets results
2. User creates conversation, submits multiple queries, reviews history
3. User changes settings, verifies persistence across sessions

---

## Architecture & Technical Decisions

### State Management Strategy

**Zustand (Recommended):**
```typescript
// stores/queryStore.ts
interface QueryState {
  currentQuery: string;
  selectedMode: RetrievalMode;
  filters: QueryFilters;
  results: SearchResult[];
  isLoading: boolean;
  error: string | null;

  setQuery: (query: string) => void;
  setMode: (mode: RetrievalMode) => void;
  submitQuery: () => Promise<void>;
}

export const useQueryStore = create<QueryState>((set, get) => ({
  currentQuery: '',
  selectedMode: 'hybrid',
  filters: {},
  results: [],
  isLoading: false,
  error: null,

  setQuery: (query) => set({ currentQuery: query }),
  setMode: (mode) => set({ selectedMode: mode }),

  submitQuery: async () => {
    set({ isLoading: true, error: null });
    try {
      const results = await queryService.submitQuery({
        query: get().currentQuery,
        mode: get().selectedMode,
        filters: get().filters,
      });
      set({ results, isLoading: false });
    } catch (error) {
      set({ error: error.message, isLoading: false });
    }
  },
}));
```

### API Client Setup

**Axios with Interceptors:**
```typescript
// services/apiClient.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
});

// Request interceptor (add auth token if needed)
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor (handle errors globally)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

### Routing Structure

```typescript
// App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<QueryPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="sessions/:sessionId" element={<SessionPage />} />
          <Route path="monitoring" element={<MonitoringPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

---

## Docker Setup

### Frontend Dockerfile

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Nginx Configuration

```nginx
# nginx.conf
server {
  listen 80;
  server_name localhost;

  root /usr/share/nginx/html;
  index index.html;

  # SPA routing
  location / {
    try_files $uri $uri/ /index.html;
  }

  # API proxy (optional, for CORS)
  location /api {
    proxy_pass http://backend:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
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

## Performance Optimizations

### Code Splitting

```typescript
// Lazy load heavy components
const GraphVisualization = lazy(() => import('./components/GraphVisualization'));
const MonitoringDashboard = lazy(() => import('./pages/MonitoringPage'));

// Use Suspense for loading states
<Suspense fallback={<Spinner />}>
  <GraphVisualization data={graphData} />
</Suspense>
```

### Virtualization for Long Lists

```typescript
import { FixedSizeList } from 'react-window';

function ResultsList({ results }: { results: SearchResult[] }) {
  return (
    <FixedSizeList
      height={600}
      itemCount={results.length}
      itemSize={150}
      width="100%"
    >
      {({ index, style }) => (
        <div style={style}>
          <ResultCard result={results[index]} />
        </div>
      )}
    </FixedSizeList>
  );
}
```

### React Query Caching

```typescript
// Cache query results for 5 minutes
const { data: results, isLoading } = useQuery({
  queryKey: ['search', query, mode],
  queryFn: () => queryService.submitQuery({ query, mode }),
  staleTime: 5 * 60 * 1000, // 5 minutes
  cacheTime: 10 * 60 * 1000, // 10 minutes
});
```

---

## Accessibility (A11y)

**WCAG 2.1 Level AA Compliance:**
- ✅ Semantic HTML (proper heading hierarchy)
- ✅ ARIA labels for screen readers
- ✅ Keyboard navigation (Tab, Enter, Escape)
- ✅ Focus indicators
- ✅ Color contrast ratio >4.5:1
- ✅ Skip-to-content links

**Testing:**
- Lighthouse accessibility audit (score >90)
- axe DevTools for accessibility issues
- Keyboard-only navigation testing

---

## Sprint Execution Timeline

### Week 1 (Days 1-5)

**Day 1: Setup & Infrastructure (Feature 15.1)**
- Initialize React project with Vite + TypeScript
- Setup Tailwind CSS, React Router, Zustand
- Configure ESLint, Prettier, Vitest
- Create basic layout (Header, Sidebar, Footer)

**Day 2-3: Query Interface (Feature 15.2)**
- Implement SearchBar component
- Build ModeSelector component
- Create AdvancedFilters component
- Integrate with backend API

**Day 4-5: Results Display (Feature 15.3 - Part 1)**
- Build ResultsList component
- Create ResultCard component
- Implement basic provenance display

### Week 2 (Days 6-10)

**Day 6-7: Results Display (Feature 15.3 - Part 2)**
- Add EntityHighlight component
- Build GraphVisualization component (if needed)
- Implement export functionality

**Day 8: Conversation History (Feature 15.4)**
- Create ConversationThread component
- Build SessionSidebar component
- Integrate session management API

**Day 9: System Monitoring (Feature 15.5)**
- Build HealthDashboard component
- Create PerformanceChart component
- Implement real-time updates (polling or WebSocket)

**Day 10: Configuration & Polish (Feature 15.6)**
- Add SettingsPanel component
- Implement theme toggle (Light/Dark)
- Final bug fixes and UI polish

---

## Sprint Metrics

**Story Points:** 68 SP total

| Feature | Story Points | Duration |
|---------|--------------|----------|
| 15.1 Project Setup | 8 SP | 1 day |
| 15.2 Query Interface | 13 SP | 2-3 days |
| 15.3 Results Display | 21 SP | 3-4 days |
| 15.4 Conversation History | 13 SP | 2 days |
| 15.5 System Monitoring | 8 SP | 1-2 days |
| 15.6 Configuration | 5 SP | 1 day |

**Velocity Target:** 7-8 SP/day (realistic for frontend work)

---

## Deliverables Checklist

### Code Deliverables
- [ ] React frontend application (src/)
- [ ] Component library (reusable UI components)
- [ ] API service layer (services/)
- [ ] State management (stores/)
- [ ] Unit tests (>80% coverage)
- [ ] Integration tests
- [ ] E2E tests (critical flows)

### Docker & Deployment
- [ ] Dockerfile for frontend
- [ ] Nginx configuration
- [ ] Updated docker-compose.yml
- [ ] Environment variable configuration

### Documentation
- [ ] Component documentation (Storybook optional)
- [ ] API integration guide
- [ ] User guide (README in frontend/)
- [ ] Developer setup guide
- [ ] Sprint 15 completion report

---

## Risks & Mitigation

### Risk: Design complexity slows implementation
**Mitigation:** Use component library (Shadcn/UI or MUI) for base components, focus on UX flows

### Risk: Graph visualization performance issues
**Mitigation:** Use D3.js or vis.js with virtualization, limit initial graph size

### Risk: Backend API changes break frontend
**Mitigation:** Use OpenAPI spec, generate TypeScript types, maintain API versioning

### Risk: Responsive design edge cases
**Mitigation:** Mobile-first approach, test on multiple devices/browsers

---

## Next Steps After Sprint 15

**Sprint 16 (Potential):**
- Advanced features: Saved queries, query templates
- Collaborative features: Share results, annotations
- Admin panel: User management, analytics dashboard
- Performance monitoring: APM integration (Sentry, DataDog)

---

## Decision: Design-First or Code-First?

**Please decide before starting Sprint 15:**

**Option A: Design-First with Figma**
- You create Figma mockups (2-3 days)
- I implement based on designs
- More time upfront, better UX/UI outcome

**Option B: Code-First with Standard UI**
- I use Shadcn/UI or Material-UI
- Implement standard RAG interface patterns
- Faster start, iterate based on feedback

**Option C: Hybrid**
- You create basic wireframes (Excalidraw/Figma)
- I implement with component library
- Refine UI iteratively

**Lass mich wissen, welche Option du bevorzugst!**

---

**Author:** Claude Code
**Date:** 2025-10-27
**Sprint:** 15
**Status:** PLANNED
