# ADR-029: React Frontend Migration Deferral

**Status:** ✅ Accepted
**Date:** 2025-11-07
**Sprint:** 21
**Related:** ADR-020 (SSE Streaming), ADR-021 (Perplexity UI Design)

---

## Context

### Original Plan (Sprint 10-14)

The initial AegisRAG roadmap planned a two-phase frontend approach:

**Phase 1 (Sprint 10): Gradio MVP**
```yaml
Sprint 10: Gradio Prototype
  Purpose: Quick MVP for testing core RAG functionality
  Technology: Gradio 4.x
  Features:
    - Simple chat interface
    - Query input + response display
    - Source citations
    - Basic health dashboard
  Effort: 5 days (13 Story Points)
  Outcome: Functional but basic UI
```

**Phase 2 (Sprint 14): React Production UI**
```yaml
Sprint 14: React Migration (PLANNED)
  Purpose: Production-ready web interface
  Technology: React 18 + Next.js 14 + TypeScript + Tailwind CSS
  Features:
    - Perplexity-inspired design (ADR-021)
    - SSE streaming (ADR-020)
    - Multi-mode search (Hybrid, Vector, Graph, Memory)
    - Conversation history
    - Advanced settings panel
  Effort: 10 days (73 Story Points)
  Expected Delivery: Sprint 14 (2025-10-27)
```

**Rationale for React (Original):**
- ✅ Production-grade UX (vs Gradio's research-oriented design)
- ✅ Full control over UI/UX (vs Gradio's constraints)
- ✅ SSE streaming support (better than Gradio's polling)
- ✅ Modern developer experience (TypeScript, Vite, Hot Reload)
- ✅ Scalability (component library, state management)

### What Actually Happened

**Sprint 10 (2025-10-20):**
- ✅ Gradio 4.44.0 UI implemented
- ✅ Basic chat interface functional
- ✅ Source citations working
- ✅ Health dashboard added

**Sprint 11-21 (2025-10-21 - 2025-11-07):**
- ⏸️ React migration **NOT started**
- ✅ Gradio 5.49.0 upgrade (Sprint 14)
- ✅ Gradio UI enhancements (Sprint 14, 17)
- ✅ Backend performance prioritized (Sprint 13, 14, 20, 21)

**Current State (Sprint 21):**
- Gradio 5.49.0 still in use
- React migration deferred to Post-Sprint 21
- Gradio sufficient for development/testing

### Decision Drivers

**Why Defer React Migration?**

**1. Backend Instability (Sprint 11-21):**

```
Sprint 11: GPU Memory Issues (RTX 3060 6GB)
  - Ollama model swapping causing crashes
  - VRAM exhaustion with qwen2.5:14b
  - Required: Model optimization

Sprint 13: Entity Extraction Performance
  - LightRAG taking 300+ seconds per document
  - Three-phase pipeline needed (ADR-017, ADR-018)
  - Required: Complete architecture refactor

Sprint 20: Ingestion Quality Issues
  - OCR accuracy insufficient (70% with LlamaIndex)
  - Table structures lost
  - Required: Docling migration (ADR-027)

Sprint 21: Container Architecture
  - Docling CUDA container integration
  - Memory management overhaul
  - LangGraph pipeline redesign
```

**Impact:** Frontend migration would be **wasted effort** if backend keeps changing.

**2. Gradio "Good Enough" for Current Needs:**

```python
# Gradio 5.49.0 capabilities (Sprint 14 upgrade)
import gradio as gr

# Streaming support (added Sprint 14)
def respond_stream(message, history):
    for chunk in sse_client.stream(message):
        yield chunk

# Multi-tab interface
with gr.Blocks() as app:
    with gr.Tab("Chat"):
        chatbot = gr.Chatbot()
        msg = gr.Textbox()
    with gr.Tab("Health"):
        health_dashboard()
    with gr.Tab("Settings"):
        settings_panel()

# Runs on http://localhost:7860
app.launch()
```

**Features Available:**
- ✅ Streaming responses (via generator functions)
- ✅ Multi-tab interface (Chat, Health, Settings)
- ✅ Source citations (via Markdown)
- ✅ Conversation history (via state)
- ✅ Health dashboard (custom components)

**Missing vs React:**
- ⚠️ No Perplexity-inspired design (basic Gradio theme)
- ⚠️ Limited UX customization (Gradio constraints)
- ⚠️ No TypeScript (Python-only)
- ⚠️ Less modern feel (research tool aesthetic)

**Conclusion:** Gradio **sufficient** for development and internal testing. React nice-to-have but not blocking.

**3. Resource Prioritization:**

```yaml
Sprint 11-21 Priority Decisions:
  1. Backend Performance (CRITICAL)
     - GPU optimization
     - Entity extraction speed
     - Ingestion quality

  2. Core Infrastructure (HIGH)
     - Docling integration
     - LangGraph pipeline
     - Container architecture

  3. Testing & Quality (HIGH)
     - 132 tests added (Sprint 14)
     - Integration test suite
     - Performance benchmarks

  4. Frontend Migration (LOW)
     - Gradio functional
     - No user complaints
     - Can wait until backend stable
```

**Decision:** Defer React to **Post-Sprint 21** when backend architecture solidifies.

---

## Decision

**Defer React frontend migration to Post-Sprint 21. Continue using Gradio 5.49.0 for development and testing.**

### Gradio Retention Strategy

**Current Role (Sprint 21):**
```yaml
Gradio 5.49.0: Development & Testing UI
  Usage:
    - Developer testing of RAG queries
    - Internal demos
    - Performance benchmarking
    - Integration test UI

  Sufficient Features:
    - Chat interface with streaming
    - Health dashboard
    - Settings panel
    - Source citations

  Not Production-Ready:
    - Basic design (research tool aesthetic)
    - Limited UX customization
    - No advanced UI patterns
```

**Future React Migration (Sprint 22+):**
```yaml
React 18 + Next.js 14: Production UI (PLANNED)
  Timeline: Sprint 22 or later (when backend stable)
  Triggers:
    - Backend architecture finalized
    - No major refactors in 2+ sprints
    - External user demand for better UI

  Features (ADR-020, ADR-021):
    - Perplexity-inspired design
    - SSE streaming with better UX
    - Multi-mode search selector
    - Conversation history sidebar
    - Advanced settings
    - Responsive mobile design
```

### Configuration

**Environment Variables:**
```bash
# .env
FRONTEND_TYPE=gradio  # Options: gradio, react (future)
GRADIO_SERVER_NAME=0.0.0.0
GRADIO_SERVER_PORT=7860
GRADIO_THEME=default  # Options: default, soft, monochrome
```

**Launch Script:**
```python
# scripts/launch_ui.py
import os
from src.ui.gradio_app import create_app

if __name__ == "__main__":
    frontend_type = os.getenv("FRONTEND_TYPE", "gradio")

    if frontend_type == "gradio":
        app = create_app()
        app.launch(
            server_name=os.getenv("GRADIO_SERVER_NAME", "0.0.0.0"),
            server_port=int(os.getenv("GRADIO_SERVER_PORT", 7860)),
            share=False
        )
    elif frontend_type == "react":
        # Future: Launch Next.js dev server
        raise NotImplementedError("React frontend not yet implemented")
```

---

## Alternatives Considered

### Alternative 1: Immediate React Migration (Sprint 14 as Planned)

**Pros:**
- ✅ Production-ready UI sooner
- ✅ Better user experience immediately
- ✅ TypeScript + modern tooling
- ✅ Follow original roadmap

**Cons:**
- ❌ Backend unstable (Sprint 13-21 major refactors)
- ❌ API contracts changing frequently
- ❌ Wasted effort redoing frontend for each backend change
- ❌ 10 days (73 SP) diverted from critical backend work
- ❌ Gradio already functional

**Verdict:** **REJECTED** - Backend instability makes this premature. Wait for architecture to stabilize.

### Alternative 2: Hybrid Approach (Gradio + React in Parallel)

**Pros:**
- ✅ Gradio for developers, React for external users
- ✅ Parallel development (no waiting)
- ✅ Flexibility to choose UI per deployment

**Cons:**
- ❌ Dual maintenance burden (2x UI codebases)
- ❌ API must support both (complexity)
- ❌ Testing overhead (2x integration tests)
- ❌ Resource waste (building 2 UIs for same backend)
- ❌ Confusing for users (which UI to use?)

**Verdict:** **REJECTED** - Maintenance burden too high, no clear benefit over sequential approach.

### Alternative 3: Gradio Premium Themes (Custom Styling)

**Pros:**
- ✅ Improve Gradio aesthetics (closer to production-ready)
- ✅ Lower effort than React migration (~2 days vs 10 days)
- ✅ Keep Python-only stack
- ✅ No frontend build tooling needed

**Cons:**
- ⚠️ Still limited by Gradio constraints
- ⚠️ Cannot achieve Perplexity-level UX
- ⚠️ No TypeScript/component library benefits
- ⚠️ Eventually need React anyway for production

**Verdict:** **CONSIDERED** - May implement as interim improvement (Sprint 22), but doesn't replace React long-term.

### Alternative 4: Use Gradio Permanently (Skip React)

**Pros:**
- ✅ No migration effort ever
- ✅ Python-only stack (simpler)
- ✅ Gradio improving rapidly (5.x has many features)
- ✅ Sufficient for research/internal tools

**Cons:**
- ❌ Not suitable for external production users
- ❌ Limited UX customization
- ❌ Research tool aesthetic (not professional)
- ❌ No SSE streaming (Gradio uses polling)
- ❌ No mobile responsiveness

**Verdict:** **REJECTED** - Gradio suitable for development, but React needed for production deployment to external users.

---

## Rationale

### Why Deferral Makes Sense

**1. Backend Architecture Finalization:**

```
Sprint 11-21 Major Changes:
  - Sprint 13: Three-phase extraction pipeline
  - Sprint 16: BGE-M3 embedding migration
  - Sprint 20: Pure LLM extraction default
  - Sprint 21: Docling container architecture

Impact on Frontend:
  - API endpoints changed multiple times
  - Response formats evolved
  - Streaming protocols updated
  - Health metrics added/removed

Result: Frontend built in Sprint 14 would need COMPLETE rewrite by Sprint 21
```

**2. Gradio Sufficient for Current Users:**

```
Current Users (Sprint 21):
  - Primary: Solo developer (Klaus Pommer)
  - Secondary: Internal testing team
  - External: None (not yet deployed publicly)

User Needs:
  - ✅ Test RAG queries → Gradio works
  - ✅ View source citations → Gradio works
  - ✅ Monitor health → Gradio works
  - ❌ Beautiful UX → Not critical yet
  - ❌ Mobile access → Not needed yet

Conclusion: Gradio meets ALL current user needs
```

**3. Resource Optimization:**

```
React Migration Cost (Sprint 14 estimate):
  - Frontend Development: 7 days
  - Backend API Adjustments: 2 days
  - Integration Testing: 1 day
  - TOTAL: 10 days (73 Story Points)

Alternative Use of 10 Days (Sprint 13-21):
  - Sprint 13: Three-phase pipeline (5 days) ✅ DONE
  - Sprint 14: Testing infrastructure (3 days) ✅ DONE
  - Sprint 20: LLM extraction quality (2 days) ✅ DONE
  - TOTAL: 10 days invested in CRITICAL backend quality

ROI: Backend improvements > UI aesthetics (for current development phase)
```

### When to Revisit React Migration

**Trigger Conditions:**
1. **Backend Stability:** No major architecture changes for 2+ sprints
2. **External Users:** External deployment planned (not just internal)
3. **User Demand:** Complaints about Gradio UX from stakeholders
4. **Feature Gaps:** Need features Gradio cannot provide (advanced SSE, mobile, etc.)

**Expected Timeline:** Sprint 22-23 (December 2025 - January 2026)

---

## Consequences

### Positive

✅ **Backend Quality Prioritized:**
- 10 days (73 SP) invested in performance, quality, testing
- Solid foundation before frontend work
- Avoid rework from backend changes

✅ **Gradio Improvements Leveraged:**
- Gradio 5.x has many new features (streaming, custom components)
- Continuous improvements without migration effort
- Python-only stack simpler for solo development

✅ **Reduced Risk:**
- No premature frontend work
- Wait for backend API stability
- Clear requirements before React development

✅ **Resource Efficiency:**
- Solo developer focuses on one layer at a time
- No context switching between frontend/backend
- Backend expertise maximized

### Negative

⚠️ **Delayed Production Deployment:**
- Gradio not suitable for external users
- Production deployment blocked until React migration
- Potential user dissatisfaction if demoing Gradio

**Mitigation:** React migration planned for Sprint 22 (1-2 months). External deployment timeline adjusted accordingly.

⚠️ **Technical Debt:**
- Gradio code may need to be discarded
- Potential waste if Gradio customizations abandoned
- Risk of Gradio "good enough" syndrome (never migrating)

**Mitigation:** Document React migration plan (ADR-020, ADR-021). Set explicit trigger conditions for migration.

⚠️ **Developer Experience Gap:**
- Missing TypeScript/modern tooling benefits
- Less attractive for potential contributors
- Gradio debugging more difficult than React DevTools

**Mitigation:** Acceptable for solo development. Re-evaluate when team expands.

### Neutral

🔄 **Gradio 5.x Adoption:**
- Upgraded from 4.44.0 → 5.49.0 (Sprint 14)
- New features available (streaming, custom components)
- Python-only development continues

🔄 **React Plan Preserved:**
- ADR-020 (SSE Streaming) still valid
- ADR-021 (Perplexity UI Design) still valid
- Technical design ready when migration starts

---

## Implementation

### Current Gradio Setup (Sprint 21)

**Dependencies:**
```toml
# pyproject.toml
gradio = "^5.49.0"
```

**Application Structure:**
```python
# src/ui/gradio_app.py
import gradio as gr

def create_app():
    with gr.Blocks(theme=gr.themes.Default()) as app:
        with gr.Tab("Chat"):
            chatbot = gr.Chatbot()
            msg = gr.Textbox(placeholder="Ask a question...")
            submit = gr.Button("Submit")

        with gr.Tab("Health"):
            health_status = gr.JSON()
            refresh_btn = gr.Button("Refresh")

        with gr.Tab("Settings"):
            search_mode = gr.Dropdown(
                choices=["hybrid", "vector", "graph", "memory"],
                value="hybrid",
                label="Search Mode"
            )

    return app
```

### Future React Migration (Sprint 22+)

**Planned Structure:**
```
frontend/
├── app/                    # Next.js 14 App Router
│   ├── layout.tsx
│   ├── page.tsx
│   └── chat/
│       └── page.tsx
├── components/
│   ├── Chat/
│   │   ├── ChatInterface.tsx
│   │   ├── MessageList.tsx
│   │   └── SourceCard.tsx
│   ├── Sidebar/
│   │   ├── ConversationHistory.tsx
│   │   └── SettingsPanel.tsx
│   └── Dashboard/
│       └── HealthDashboard.tsx
├── lib/
│   ├── api-client.ts
│   └── sse-client.ts
├── package.json
└── tsconfig.json
```

---

## Timeline

### Sprint 10 (2025-10-20): Gradio MVP
- ✅ Gradio 4.44.0 implemented
- ✅ Basic chat interface
- ✅ Health dashboard
- ✅ Settings panel

### Sprint 14 (2025-10-27): Gradio Upgrade
- ✅ Gradio 5.49.0 upgrade
- ✅ Streaming support added
- ✅ UI enhancements
- ⏸️ React migration deferred

### Sprint 15-21 (2025-10-28 - 2025-11-07): Backend Focus
- ✅ Backend performance (Sprint 13, 14, 20)
- ✅ Docling migration (Sprint 21)
- ✅ Testing infrastructure (Sprint 14, 18)
- ⏸️ React migration deferred

### Sprint 22+ (2025-12-01+): React Migration (PLANNED)
- ⏳ Evaluate backend stability
- ⏳ Check trigger conditions
- ⏳ Execute React migration if conditions met
- ⏳ Deploy production UI

---

## Notes

**Relationship to Other ADRs:**
- **ADR-020:** SSE Streaming for Chat (React migration plan preserved)
- **ADR-021:** Perplexity-Inspired UI Design (design spec ready for React)
- **ADR-027:** Docling Container (backend refactor justifies deferral)

**Not a Cancellation:**
- React migration is **DEFERRED**, not **CANCELLED**
- Technical design complete (ADR-020, ADR-021)
- Timeline adjusted based on backend stability

**Deferral Precedent:**
- Original 12-sprint plan extended to 21+ sprints
- React migration is one of several timeline adjustments
- Agile approach: adapt based on actual progress

---

## References

**External:**
- [Gradio Documentation](https://www.gradio.app/docs)
- [Gradio 5.x Release Notes](https://github.com/gradio-app/gradio/releases)
- [React 18 Documentation](https://react.dev/)
- [Next.js 14 Documentation](https://nextjs.org/docs)

**Internal:**
- **ADR-020:** `docs/adr/ADR-020-sse-streaming-for-chat.md`
- **ADR-021:** `docs/adr/ADR-021-perplexity-inspired-ui-design.md`
- **Sprint 10 Summary:** (Gradio MVP implementation)
- **Sprint 14 Summary:** (Gradio 5.x upgrade)
- **Drift Analysis:** `docs/DRIFT_ANALYSIS.md` (Section 3.3: UI Framework Evolution)
- **Gradio App:** `src/ui/gradio_app.py`

---

**Author:** Klaus Pommer + Claude Code (documentation-agent)
**Reviewers:** N/A (Solo Development)
**Last Updated:** 2025-11-10
