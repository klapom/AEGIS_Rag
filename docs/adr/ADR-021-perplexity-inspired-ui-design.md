# ADR-021: Perplexity-Inspired UI Design for Frontend

## Status
**Accepted** (2025-10-27)

## Context

Sprint 15 introduces the first frontend interface for AegisRAG. Until now, AegisRAG has been a backend-only system with API endpoints for chat, retrieval, and memory management. Users have requested a **production-ready web interface** with:

1. **RAG-specific UX**: Display sources, citations, and provenance clearly
2. **Real-time streaming**: Token-by-token LLM responses (not blocking)
3. **Multi-mode search**: Support Hybrid, Vector, Graph, and Memory retrieval modes
4. **Session management**: Persistent conversation history across sessions
5. **System transparency**: Show health status and performance metrics

**Problem:**
Designing a RAG interface from scratch is time-consuming and risky:
- **UX complexity**: How to balance answer clarity with source transparency?
- **Component structure**: What components are needed for RAG workflows?
- **Design system**: Colors, typography, spacing, accessibility?
- **Proven patterns**: What UX patterns work for RAG search?

**Question:** Should we design a custom interface or adopt proven design patterns from existing RAG systems?

**User Decision:**
> "OK. warum das Rad neu erfinden. Lass uns an der Oberfläche von Perplexity orientieren."
> (Translation: "OK. Why reinvent the wheel. Let's orient ourselves on Perplexity's interface.")

## Decision

We will adopt **Perplexity.ai's UI design patterns** as the foundation for AegisRAG's frontend in Sprint 15.

**What We Adopt:**
1. **Layout**: Minimalist sidebar + main content area
2. **Search-First UX**: Large centered search input on homepage
3. **Source Cards**: Horizontal scrolling source chips with favicons
4. **Streaming Display**: Token-by-token answer with inline citations
5. **Mode Selector**: Chip-based mode selection (Hybrid, Vector, Graph, Memory)
6. **Session History**: Collapsible sidebar with conversation history
7. **Design System**: Teal accent color, Inter font, rounded corners (12-24px)

**What We Adapt for AegisRAG:**
- **Multi-Mode Search**: Add AegisRAG-specific modes (Hybrid, Graph, Memory)
- **Provenance Detail**: Expand source cards to show LightRAG provenance
- **System Health**: Add dashboard for Qdrant/Neo4j/Redis health
- **German Localization**: Support German language (user is German-speaking)

## Alternatives Considered

### Alternative 1: Custom Design from Scratch
**Pro:**
- **Fully tailored**: 100% aligned with AegisRAG's unique features
- **Brand identity**: Unique look and feel
- **No constraints**: Free to innovate on UX patterns

**Contra:**
- **Time-consuming**: 2-3 weeks for design + iteration (delays Sprint 15)
- **UX risk**: Unproven patterns may confuse users
- **Higher cognitive load**: Users must learn new interface patterns
- **No validation**: No proven evidence of effectiveness

**Why Not Chosen:**
Time-to-market is critical. Sprint 15 targets 7-10 days for frontend MVP. Custom design would delay by 2-3 weeks and introduce UX uncertainty.

### Alternative 2: ChatGPT-Like Interface
**Pro:**
- **Familiar**: Most users know ChatGPT's interface
- **Simple**: Minimalist chat-focused design
- **Mobile-friendly**: Responsive on all devices

**Contra:**
- **Not RAG-optimized**: ChatGPT hides sources (citations are secondary)
- **Lacks provenance**: No clear source display for retrieval transparency
- **Single-mode**: No explicit retrieval mode selection (Hybrid/Vector/Graph)
- **Enterprise focus**: ChatGPT is consumer-focused, not enterprise RAG

**Why Not Chosen:**
ChatGPT's design prioritizes conversational simplicity over RAG transparency. AegisRAG is an **enterprise RAG system** where source provenance, multi-mode retrieval, and transparency are critical.

### Alternative 3: Claude.ai-Like Interface
**Pro:**
- **Artifacts**: Support for generated artifacts (code, documents)
- **Project context**: Multiple document uploads with context
- **Clean design**: Minimalist, professional

**Contra:**
- **Complex**: Artifacts and projects add unnecessary complexity for RAG search
- **Not RAG-focused**: Claude is a general assistant, not a RAG search engine
- **Heavy UI**: More cognitive load than needed for search workflows

**Why Not Chosen:**
Claude's interface is optimized for multi-turn assistant workflows with artifacts. AegisRAG's primary use case is **RAG search** (query → sources → answer), which Perplexity handles better.

### Alternative 4: Google-Like Search Interface
**Pro:**
- **Universal familiarity**: Everyone knows Google's search pattern
- **Fast**: Optimized for quick search → results
- **Mobile-first**: Responsive design

**Contra:**
- **No streaming**: Google shows static results, not streaming LLM responses
- **Limited source detail**: Snippets are brief, not full provenance
- **Traditional search**: Keyword-focused, not conversational RAG

**Why Not Chosen:**
Google's design is for traditional search (keyword → documents). AegisRAG is **conversational RAG** (natural language → LLM answer + sources), which requires streaming and citations.

## Rationale

### Why Perplexity.ai is the Optimal Model

**1. RAG-First Design:**
Perplexity is built specifically for RAG search, not general chat:
- Sources are **primary**, not secondary (displayed prominently)
- Citations are **inline** within the answer (e.g., [1], [2])
- Provenance is **transparent** (title, domain, excerpt)

**2. Proven UX Patterns:**
Perplexity has validated these patterns with millions of users:
- Large search input → immediate focus
- Horizontal source cards → scannable at a glance
- Streaming answer → no blocking wait
- Mode selector chips → explicit retrieval control

**3. Matches AegisRAG Use Cases:**
| AegisRAG Feature        | Perplexity Pattern     | Fit         |
|-------------------------|------------------------|-------------|
| Hybrid retrieval        | Mode selector chips    | ✅ Perfect   |
| LightRAG provenance     | Source cards           | ✅ Perfect   |
| Streaming responses     | Token-by-token display | ✅ Perfect   |
| Session history         | Sidebar conversations  | ✅ Perfect   |
| Multi-turn conversation | Chat-like interaction  | ✅ Perfect   |

**4. Minimalist and Accessible:**
- **Clean design**: No clutter, focus on search
- **Responsive**: Works on mobile, tablet, desktop
- **Accessible**: High contrast, clear typography
- **Fast loading**: Minimal JavaScript, optimized assets

**5. Extensible for AegisRAG:**
Perplexity's design easily accommodates AegisRAG-specific features:
- **Mode selector**: Add "Hybrid", "Graph", "Memory" modes
- **Source cards**: Extend to show LightRAG chunk IDs, confidence scores
- **System health**: Add sidebar section for health dashboard
- **German localization**: Replace English text with German

### Design Analysis from Screenshots

**Screenshot 1: Perplexity Homepage**
```
┌─────────────────────────────────────────────────────┐
│ [Logo]  [+ New Thread]          [☰]  [User Avatar] │  ← Header
├──┬──────────────────────────────────────────────────┤
│S │                                                   │
│I │          [Large Search Input]                    │  ← Main Content
│D │          "Ask anything..."                       │
│E │                                                   │
│B │     [🔀 Hybrid] [📊 Graph] [🧠 Memory]          │  ← Mode Chips
│A │                                                   │
│R │                                                   │
└──┴──────────────────────────────────────────────────┘
```

**Key Insights:**
- **Sidebar**: ~80-100px wide, vertical layout
- **Search input**: ~120px tall, centered, rounded-3xl (24px radius)
- **Mode chips**: Below search, horizontal layout, icon + text
- **Generous spacing**: Padding 24-32px, whitespace for focus

**Screenshot 2: Perplexity Results Page**
```
┌─────────────────────────────────────────────────────┐
│ [Logo]  [Query Title]           [☰]  [User Avatar] │  ← Header
├──┬──────────────────────────────────────────────────┤
│S │  "Ich möchte mit Claude Code..."                 │  ← Query Title
│I │                                                   │
│D │  [⭐ Antwort] [📷 Bilder] [📚 Quellen]          │  ← Tabs
│E │                                                   │
│B │  [Src1] [Src2] [Src3] [Src4] ───────────→       │  ← Source Cards
│A │                                                   │
│R │  Dies ist die Antwort [1][2]...                  │  ← Streaming Answer
│  │  Weitere Details [3]...                          │
│  │                                                   │
│  │  [Follow-up Input]                               │  ← Follow-up Input
└──┴──────────────────────────────────────────────────┘
```

**Key Insights:**
- **Query title**: Large, bold (text-2xl, font-bold)
- **Tab bar**: Antwort (Answer), Bilder (Images), Quellen (Sources)
- **Source cards**: Horizontal scroll, ~200px width, favicon + title + domain
- **Inline citations**: [1], [2], [3] in answer text (clickable)
- **Follow-up input**: Smaller input at bottom for multi-turn

### Design System Extracted from Perplexity

**Colors:**
```css
--primary: #20808D;        /* Teal - accent color */
--primary-hover: #1A6B76;  /* Darker teal on hover */
--gray-50: #F5F5F5;        /* Background light */
--gray-100: #E8E8E8;       /* Border light */
--gray-700: #6B6B6B;       /* Text secondary */
--gray-900: #1A1A1A;       /* Text primary */
--white: #FFFFFF;          /* Background white */
--error: #DC2626;          /* Error red */
--success: #16A34A;        /* Success green */
```

**Typography:**
```css
font-family: 'Inter', system-ui, sans-serif;
font-size-base: 16px;
line-height: 1.5;

/* Headings */
h1: 32px, font-weight: 700
h2: 24px, font-weight: 600
h3: 20px, font-weight: 600

/* Body */
body: 16px, font-weight: 400
small: 14px, font-weight: 400
```

**Spacing:**
```css
--spacing-xs: 4px;
--spacing-sm: 8px;
--spacing-md: 16px;
--spacing-lg: 24px;
--spacing-xl: 32px;
--spacing-2xl: 48px;
```

**Border Radius:**
```css
--radius-sm: 8px;    /* Buttons, inputs */
--radius-md: 12px;   /* Cards */
--radius-lg: 16px;   /* Source cards */
--radius-xl: 24px;   /* Search input */
--radius-full: 9999px; /* Circular (avatars, icon buttons) */
```

**Shadows:**
```css
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 6px rgba(0, 0, 0, 0.1);
--shadow-lg: 0 10px 15px rgba(0, 0, 0, 0.1);
```

## Consequences

### Positive

✅ **Faster Development:**
- No design iteration needed (patterns validated by Perplexity)
- Clear component structure from screenshots
- Design system extracted → Tailwind config ready
- **Estimated time saved:** 2-3 weeks

✅ **Proven UX:**
- Millions of users validate Perplexity's patterns
- RAG-first design (sources, citations, provenance)
- Streaming UX is battle-tested
- Reduces user onboarding friction (familiar patterns)

✅ **RAG-Optimized:**
- Source cards prominently displayed
- Inline citations for transparency
- Mode selector for explicit retrieval control
- Multi-turn conversation support

✅ **Extensible:**
- Easy to add AegisRAG-specific features:
  - LightRAG provenance details (chunk IDs, confidence)
  - System health dashboard (Qdrant, Neo4j, Redis)
  - German localization (replace strings)
- Modular component structure

✅ **Accessible and Responsive:**
- High contrast colors (WCAG AA compliant)
- Clear typography (Inter is accessible)
- Responsive design (mobile, tablet, desktop)
- Keyboard navigation support

### Negative

⚠️ **Not Unique Brand Identity:**
- AegisRAG's UI will resemble Perplexity
- **Mitigation:** Customize with AegisRAG logo, add unique features (health dashboard, advanced provenance)
- **Impact:** Low (user value > unique branding for enterprise RAG)

⚠️ **Limited Innovation:**
- Following existing patterns → less room for UX innovation
- **Mitigation:** Innovate in AegisRAG-specific areas (graph visualization, temporal memory)
- **Impact:** Low (proven patterns reduce risk)

⚠️ **Perception Risk:**
- Users may perceive AegisRAG as "Perplexity clone"
- **Mitigation:** Emphasize AegisRAG's unique backend (LightRAG, Graphiti, MCP)
- **Impact:** Low (backend differentiation is primary value)

### Mitigations

**For Brand Differentiation:**
- Add AegisRAG logo and brand colors (keep teal as accent)
- Highlight unique features: Graph visualization, Multi-agent orchestration, MCP tools
- Add "Powered by AegisRAG" badge in footer

**For Innovation:**
- Reserve innovation for AegisRAG-specific features:
  - **Graph visualization**: Interactive Neo4j graph for "Graph" mode
  - **Temporal memory**: Timeline view for episodic memory
  - **MCP tool cards**: Display tool calls and results

**For User Perception:**
- Clear documentation: "Inspired by Perplexity, powered by AegisRAG"
- Emphasize backend superiority: "4 retrieval modes, Multi-agent system, Local LLMs"

## Implementation

### Component Structure

```
frontend/src/
├── components/
│   ├── layout/
│   │   ├── AppLayout.tsx          # Main layout wrapper
│   │   ├── Sidebar.tsx            # Left sidebar (history, health)
│   │   ├── Header.tsx             # Top header (logo, user)
│   │   └── Footer.tsx             # Footer (powered by)
│   ├── search/
│   │   ├── SearchInput.tsx        # Large centered search input
│   │   ├── ModeSelector.tsx       # Chip-based mode selector
│   │   └── QuickPrompts.tsx       # Example prompts
│   ├── results/
│   │   ├── StreamingAnswer.tsx    # Token-by-token answer display
│   │   ├── SourceCard.tsx         # Individual source card
│   │   ├── SourceCarousel.tsx     # Horizontal scrolling sources
│   │   ├── InlineCitation.tsx     # [1][2][3] clickable citations
│   │   └── TabBar.tsx             # Answer/Sources/Images tabs
│   ├── history/
│   │   ├── SessionList.tsx        # Sidebar conversation list
│   │   ├── SessionItem.tsx        # Individual session item
│   │   └── NewSessionButton.tsx   # + New Thread button
│   ├── health/
│   │   ├── HealthDashboard.tsx    # System health overview
│   │   ├── ServiceStatus.tsx      # Qdrant/Neo4j/Redis status
│   │   └── MetricsChart.tsx       # Performance metrics
│   └── common/
│       ├── Button.tsx             # Reusable button component
│       ├── IconButton.tsx         # Circular icon button
│       ├── Chip.tsx               # Mode chip component
│       ├── LoadingSpinner.tsx     # Loading indicator
│       └── ErrorBoundary.tsx      # Error handling
├── pages/
│   ├── HomePage.tsx               # Landing page with search
│   ├── ResultsPage.tsx            # Search results with streaming
│   ├── HistoryPage.tsx            # Conversation history
│   └── HealthPage.tsx             # System health dashboard
├── hooks/
│   ├── useStreamChat.ts           # SSE streaming hook
│   ├── useSessions.ts             # Session management
│   ├── useHealthCheck.ts          # Health monitoring
│   └── useLocalStorage.ts         # Persistent state
├── stores/
│   ├── chatStore.ts               # Zustand chat state
│   ├── sessionStore.ts            # Zustand session state
│   └── uiStore.ts                 # Zustand UI state (sidebar open/close)
├── api/
│   ├── chat.ts                    # Chat API client
│   ├── sessions.ts                # Session API client
│   └── health.ts                  # Health API client
├── types/
│   ├── chat.ts                    # ChatRequest, ChatResponse types
│   ├── sources.ts                 # Source, Citation types
│   └── health.ts                  # HealthStatus types
└── styles/
    ├── globals.css                # Global styles + Tailwind
    └── tailwind.config.js         # Perplexity-inspired config
```

### Key React Components

**1. SearchInput Component:**
```tsx
export function SearchInput({ onSubmit }: Props) {
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
          className="w-full h-28 px-6 pr-48 text-lg border-2 border-gray-200
                     rounded-3xl focus:border-primary focus:ring-2 focus:ring-primary/20"
        />

        {/* Action Buttons */}
        <div className="absolute right-4 bottom-4 flex items-center space-x-2">
          <IconButton icon={<MicrophoneIcon />} onClick={() => {}} />
          <IconButton icon={<AttachIcon />} onClick={() => {}} />
          <IconButton icon={<ArrowUpIcon />} primary onClick={handleSubmit} />
        </div>
      </div>

      {/* Mode Selector */}
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
          icon="📊"
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
          icon="🧠"
        >
          Memory
        </ModeChip>
      </div>
    </div>
  );
}
```

**2. StreamingAnswer Component:**
```tsx
export function StreamingAnswer({ sessionId, query }: Props) {
  const [tokens, setTokens] = useState<string[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [isStreaming, setIsStreaming] = useState(true);
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
          if (chunk.data.complete) {
            setIsStreaming(false);
          }
          break;
      }
    });
  }, [query, sessionId]);

  return (
    <div className="space-y-6">
      {/* Source Cards */}
      {sources.length > 0 && (
        <SourceCarousel sources={sources} />
      )}

      {/* Streaming Answer */}
      <div className="prose prose-lg max-w-none">
        <AnswerText tokens={tokens} sources={sources} />
        {isStreaming && <BlinkingCursor />}
      </div>

      {/* Follow-up Input */}
      {!isStreaming && (
        <SearchInput onSubmit={(q, m) => {/* handle follow-up */}} />
      )}
    </div>
  );
}
```

**3. SourceCard Component:**
```tsx
export function SourceCard({ source, index }: Props) {
  return (
    <div className="flex-shrink-0 w-64 p-4 bg-white border border-gray-200
                    rounded-xl hover:shadow-md transition cursor-pointer">
      {/* Header */}
      <div className="flex items-center space-x-2 mb-2">
        <img src={source.favicon} alt="" className="w-4 h-4" />
        <span className="text-sm font-semibold text-gray-900">
          {index + 1}. {source.title}
        </span>
      </div>

      {/* Domain */}
      <div className="text-xs text-gray-500 mb-2">
        {source.domain}
      </div>

      {/* Excerpt */}
      <div className="text-sm text-gray-700 line-clamp-3">
        {source.excerpt}
      </div>

      {/* AegisRAG-specific: Provenance */}
      <div className="mt-2 flex items-center space-x-2">
        <Chip size="xs" color="teal">Chunk {source.chunk_id}</Chip>
        <Chip size="xs" color="gray">{source.confidence}% match</Chip>
      </div>
    </div>
  );
}
```

### Tailwind Configuration

```javascript
// tailwind.config.js
export default {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#20808D',
          hover: '#1A6B76',
          light: '#E0F2F5',
        },
        gray: {
          50: '#F5F5F5',
          100: '#E8E8E8',
          200: '#D1D1D1',
          300: '#B0B0B0',
          700: '#6B6B6B',
          900: '#1A1A1A',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'xs': '12px',
        'sm': '14px',
        'base': '16px',
        'lg': '18px',
        'xl': '20px',
        '2xl': '24px',
        '3xl': '32px',
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
        '3xl': '24px',
      },
      spacing: {
        '18': '4.5rem',  // 72px (search input height)
        '28': '7rem',    // 112px (search input height)
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),  // For prose
  ],
};
```

### Localization (German)

```typescript
// src/i18n/de.ts
export const de = {
  search: {
    placeholder: 'Fragen Sie alles. Tippen Sie @ für Erwähnungen.',
    submit: 'Suchen',
  },
  modes: {
    hybrid: 'Hybrid',
    vector: 'Vektor',
    graph: 'Graph',
    memory: 'Gedächtnis',
  },
  tabs: {
    answer: 'Antwort',
    images: 'Bilder',
    sources: 'Quellen',
  },
  sidebar: {
    newThread: 'Neuer Thread',
    history: 'Verlauf',
    health: 'Systemstatus',
  },
};
```

## Performance Considerations

### Component Optimization
- **Memoization**: Use `React.memo()` for SourceCard (prevent re-renders)
- **Virtualization**: Use `react-window` for long SessionList (>100 items)
- **Lazy Loading**: Code-split HealthDashboard (not needed on homepage)

### Bundle Size
- **Target**: <200KB initial bundle (gzipped)
- **Strategy**:
  - Tree-shake unused Tailwind classes
  - Dynamic imports for routes
  - Optimize images (WebP, lazy loading)

### Accessibility
- **WCAG AA**: High contrast colors (4.5:1 ratio)
- **Keyboard Navigation**: Tab through all interactive elements
- **Screen Readers**: ARIA labels on all icons and actions
- **Focus Indicators**: Visible focus rings (ring-2, ring-primary)

## Testing Strategy

**1. Visual Regression Tests** (Chromatic, Percy):
- Compare screenshots against Perplexity reference
- Verify design system consistency (colors, typography, spacing)

**2. Component Tests** (Vitest + React Testing Library):
```typescript
describe('SearchInput', () => {
  it('should match Perplexity design', () => {
    render(<SearchInput onSubmit={jest.fn()} />);

    const input = screen.getByPlaceholderText(/Fragen Sie alles/);
    expect(input).toHaveClass('h-28', 'rounded-3xl');
  });
});
```

**3. E2E Tests** (Playwright):
```typescript
test('should display streaming answer like Perplexity', async ({ page }) => {
  await page.goto('/');
  await page.fill('[data-testid="search-input"]', 'What is AegisRAG?');
  await page.click('[data-testid="submit"]');

  // Wait for sources to appear
  await page.waitForSelector('[data-testid="source-card"]');

  // Verify streaming answer
  const answer = await page.textContent('[data-testid="answer-text"]');
  expect(answer.length).toBeGreaterThan(100);
});
```

## References

- **Sprint 15 Plan**: [SPRINT_15_PLAN.md](../sprints/SPRINT_15_PLAN.md)
- **ADR-020**: SSE Streaming for Chat
- **Perplexity.ai**: https://www.perplexity.ai (reference UI)
- **Tailwind CSS**: https://tailwindcss.com (styling framework)
- **React 18**: https://react.dev (UI library)

## Review History

- **2025-10-27**: Accepted during Sprint 15 planning
- **Reviewed by**: Claude Code, User (Product Owner)
- **User Quote**: "OK. warum das Rad neu erfinden. Lass uns an der Oberfläche von Perplexity orientieren."

---

**Summary:**

Adopting Perplexity.ai's UI design patterns accelerates Sprint 15 development by 2-3 weeks while providing battle-tested RAG UX. Perplexity's minimalist, source-first design aligns perfectly with AegisRAG's transparency requirements, and its component structure (search input, source cards, streaming answer) maps directly to AegisRAG features. Customization for AegisRAG-specific features (multi-mode retrieval, LightRAG provenance, system health) extends the design without compromising proven patterns.
