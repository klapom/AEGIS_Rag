# Sprint 10: End-User Interface (Gradio MVP)

**Sprint Goal:** Funktionale Web-UI für erste User-Interaktion mit AEGIS RAG
**Duration:** 1 Woche
**Story Points:** 20 SP
**Branch:** sprint-10-dev
**Status:** 🚧 In Planning

---

## Executive Summary

Sprint 10 implementiert eine **Gradio-basierte MVP UI**, um schnell ein Gefühl für die App zu entwickeln. Dies ist eine **bewusste Zwischenlösung**:

- ✅ **Jetzt (Sprint 10):** Gradio für schnelles Prototyping und User Feedback
- 🔄 **Später (Sprint 11+):** Migration zu React mit vollständigem Playwright Testing

**Philosophie:** "Make it work, make it right, make it fast"
Sprint 10 = "Make it work"

---

## Strategic Decisions (ADR-016 implizit)

### UI Framework Choice: Gradio (Temporary)

**Decision:** Verwende Gradio für Sprint 10 als MVP, plane React-Migration für späteren Sprint.

**Rationale:**
1. **Time-to-Value:** Gradio UI in 2-3 Tagen statt 2 Wochen (React)
2. **User Feedback:** Schnell testbare UI für Stakeholder-Feedback
3. **Low Risk:** Backend-APIs bleiben gleich, UI ist austauschbar
4. **Learning:** Team lernt App-Requirements vor finaler UI-Architektur

**Migration Path:**
```
Sprint 10 (Gradio MVP)
    ↓
User Testing & Feedback Collection
    ↓
Sprint 11+ (React Production UI)
    ↓
Playwright E2E Test Suite
```

### Testing Strategy for Sprint 10

**Backend:** Full TDD with Pytest (wie gewohnt)
**Gradio UI:** Manuelle Tests + Unit Tests für Business Logic
**E2E:** Optional 2-3 Playwright Smoke Tests (low priority)

**Reason:** Gradio ist temporär, investiere nicht zu viel in UI-Tests. Fokus auf Backend-APIs, die auch mit React funktionieren werden.

---

## Sprint 10 Feature Breakdown

### Feature 10.1: FastAPI Chat Endpoints (6 SP) 🎯 HIGH PRIORITY

**Goal:** RESTful API für Chat-Interaktion, unabhängig von UI-Framework.

**Deliverables:**
- `POST /api/v1/chat` - Chat query mit streaming support
- `GET /api/v1/chat/history/{session_id}` - Conversation history
- `DELETE /api/v1/chat/history/{session_id}` - Clear history
- WebSocket `/ws/chat` - Real-time streaming (optional, nice-to-have)

**Technical Implementation:**

```python
# src/api/routes/chat.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.agents.query_agent import QueryAgent
from src.components.memory import get_unified_memory_api

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None
    stream: bool = False

class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    session_id: str
    metadata: dict

@router.post("/", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint.

    Integration:
    - QueryAgent (from Sprint 4)
    - UnifiedMemoryAPI (from Sprint 9)
    - LightRAG (from Sprint 7)
    """
    # Implementation will integrate existing components
    pass
```

**Testing:**
```python
# tests/unit/api/test_chat_endpoints.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_chat_endpoint_returns_answer(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/chat",
        json={"query": "Was ist AEGIS RAG?", "session_id": "test-123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert len(data["answer"]) > 0

@pytest.mark.asyncio
async def test_chat_endpoint_uses_memory(async_client: AsyncClient):
    # First query
    r1 = await async_client.post("/api/v1/chat", json={
        "query": "Mein Name ist Klaus",
        "session_id": "test-456"
    })

    # Second query - should remember context
    r2 = await async_client.post("/api/v1/chat", json={
        "query": "Wie heiße ich?",
        "session_id": "test-456"
    })

    assert "Klaus" in r2.json()["answer"]
```

**Success Criteria:**
- ✅ Chat endpoint integriert QueryAgent, Memory, LightRAG
- ✅ Session-basierte Conversation History funktioniert
- ✅ Response-Zeit <2s für simple Queries
- ✅ 15+ Unit Tests (100% passing)
- ✅ API dokumentiert mit OpenAPI/Swagger

**Git Commit:** `feat(api): add chat endpoints with session management`

---

### Feature 10.2: Gradio Chat Interface (5 SP) 🎨 CORE UI

**Goal:** Funktionale Chat-UI mit Gradio für erste User-Interaktion.

**Deliverables:**
- Chat Interface mit History
- Beispiel-Queries (Examples)
- Source Citations Display
- Basic Error Handling

**Technical Implementation:**

```python
# src/ui/gradio_app.py
import gradio as gr
from src.api.routes.chat import chat_endpoint
import uuid

class GradioApp:
    def __init__(self):
        self.session_id = str(uuid.uuid4())

    async def chat(self, message: str, history: list):
        """
        Gradio chat function.
        Calls FastAPI endpoint internally.
        """
        if not message.strip():
            return history, ""

        # Call FastAPI endpoint
        response = await chat_endpoint(ChatRequest(
            query=message,
            session_id=self.session_id
        ))

        # Format response with citations
        answer = response.answer
        if response.sources:
            answer += "\n\n📚 **Quellen:**\n"
            for src in response.sources[:3]:  # Top 3
                answer += f"- {src['title']} (Score: {src['score']:.2f})\n"

        history.append((message, answer))
        return history, ""

    def build_interface(self):
        with gr.Blocks(title="AEGIS RAG", theme=gr.themes.Soft()) as demo:
            gr.Markdown("# 🛡️ AEGIS RAG - Agentic Enterprise Graph Intelligence System")
            gr.Markdown("Stellen Sie Fragen zu Ihren Dokumenten.")

            chatbot = gr.Chatbot(
                value=[],
                elem_id="chatbot",
                height=500,
                label="Conversation"
            )

            with gr.Row():
                msg = gr.Textbox(
                    placeholder="Ihre Frage...",
                    show_label=False,
                    elem_id="user-input",
                    scale=9
                )
                submit = gr.Button("Senden", elem_id="submit-btn", scale=1)

            # Example queries
            gr.Examples(
                examples=[
                    "Was ist AEGIS RAG?",
                    "Welche Komponenten hat das System?",
                    "Erkläre die Memory-Architektur",
                ],
                inputs=msg
            )

            # Event handlers
            submit.click(self.chat, [msg, chatbot], [chatbot, msg])
            msg.submit(self.chat, [msg, chatbot], [chatbot, msg])

        return demo

def launch():
    app = GradioApp()
    demo = app.build_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False  # Set True for public sharing
    )

if __name__ == "__main__":
    launch()
```

**Testing:**
```python
# tests/unit/ui/test_gradio_app.py
import pytest
from src.ui.gradio_app import GradioApp

@pytest.mark.asyncio
async def test_chat_function_basic():
    app = GradioApp()
    history = []

    new_history, cleared_input = await app.chat("Test query", history)

    assert len(new_history) == 1
    assert new_history[0][0] == "Test query"  # User message
    assert len(new_history[0][1]) > 0  # Bot response exists
    assert cleared_input == ""  # Input cleared

@pytest.mark.asyncio
async def test_chat_function_shows_sources():
    app = GradioApp()
    history = []

    new_history, _ = await app.chat("What is X?", history)

    response = new_history[0][1]
    assert "📚" in response or "Quellen" in response  # Contains sources
```

**Success Criteria:**
- ✅ Chat UI läuft unter http://localhost:7860
- ✅ Multi-turn Conversations funktionieren
- ✅ Source Citations werden angezeigt
- ✅ Beispiel-Queries sind klickbar
- ✅ UI ist responsiv (Desktop-optimiert)
- ✅ 5+ Unit Tests für Gradio-Functions

**Git Commit:** `feat(ui): add Gradio chat interface with citations`

---

### Feature 10.3: Document Upload Interface (4 SP) 📄

**Goal:** User können Dokumente hochladen, die in das RAG-System indexiert werden.

**Deliverables:**
- File Upload Component (PDF, TXT, MD, DOCX)
- Upload Progress Indicator
- Indexing Status Display
- Integration mit DocumentIngestionPipeline (Sprint 2)

**Technical Implementation:**

```python
# Erweiterung von src/ui/gradio_app.py
async def upload_document(self, file):
    """
    Upload and index a document.
    """
    if file is None:
        return "⚠️ Bitte wählen Sie eine Datei."

    try:
        # Call ingestion pipeline
        from src.pipelines.ingestion import DocumentIngestionPipeline

        pipeline = DocumentIngestionPipeline()
        result = await pipeline.ingest_file(file.name)

        return f"✅ Dokument '{file.name}' erfolgreich indexiert!\n" \
               f"📊 {result['chunks_created']} Chunks erstellt."

    except Exception as e:
        return f"❌ Fehler beim Hochladen: {str(e)}"

# In build_interface():
with gr.Tab("📄 Dokumente hochladen"):
    gr.Markdown("### Dokumente zum RAG-System hinzufügen")

    file_upload = gr.File(
        label="Datei auswählen",
        file_types=[".pdf", ".txt", ".md", ".docx"],
        elem_id="file-upload"
    )

    upload_btn = gr.Button("Hochladen & Indexieren", elem_id="upload-btn")
    upload_status = gr.Textbox(label="Status", elem_id="upload-status")

    upload_btn.click(
        self.upload_document,
        inputs=file_upload,
        outputs=upload_status
    )
```

**API Endpoint:**
```python
# src/api/routes/documents.py
@router.post("/upload")
async def upload_document_endpoint(file: UploadFile):
    """
    Upload and index a document.

    Integration:
    - DocumentIngestionPipeline (Sprint 2)
    - QdrantClient (Sprint 2)
    - EmbeddingService (Sprint 2)
    """
    pass
```

**Testing:**
```python
# tests/unit/api/test_document_endpoints.py
@pytest.mark.asyncio
async def test_upload_pdf_document(async_client: AsyncClient):
    files = {"file": ("test.pdf", open("tests/fixtures/test.pdf", "rb"), "application/pdf")}

    response = await async_client.post("/api/v1/documents/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["chunks_created"] > 0
```

**Success Criteria:**
- ✅ Upload funktioniert für PDF, TXT, MD, DOCX
- ✅ Ingestion Pipeline wird korrekt aufgerufen
- ✅ Status-Feedback für User sichtbar
- ✅ Error Handling bei ungültigen Files
- ✅ 8+ Tests für Upload-Flow

**Git Commit:** `feat(ui): add document upload with ingestion integration`

---

### Feature 10.4: Conversation History Persistence (3 SP) 💾

**Goal:** Chat-History wird persistiert, kann geladen/gelöscht werden.

**Deliverables:**
- Session-basierte History in Redis
- "Clear Chat" Button
- History Laden beim Neustart (optional)

**Technical Implementation:**

```python
# src/services/conversation_service.py
from src.components.memory import get_redis_memory

class ConversationService:
    def __init__(self):
        self.redis = get_redis_memory()

    async def save_message(self, session_id: str, role: str, content: str):
        """Save a message to Redis."""
        key = f"conversation:{session_id}"
        message = {"role": role, "content": content, "timestamp": datetime.utcnow().isoformat()}
        await self.redis.rpush(key, json.dumps(message))
        await self.redis.expire(key, 86400)  # 24h TTL

    async def get_history(self, session_id: str) -> list[dict]:
        """Retrieve conversation history."""
        key = f"conversation:{session_id}"
        messages = await self.redis.lrange(key, 0, -1)
        return [json.loads(msg) for msg in messages]

    async def clear_history(self, session_id: str):
        """Clear conversation history."""
        key = f"conversation:{session_id}"
        await self.redis.delete(key)
```

**Gradio Integration:**
```python
# In GradioApp:
async def clear_chat(self):
    """Clear conversation history."""
    await conversation_service.clear_history(self.session_id)
    self.session_id = str(uuid.uuid4())  # New session
    return []  # Empty chatbot

# In build_interface():
clear_btn = gr.Button("🗑️ Chat löschen", elem_id="clear-btn")
clear_btn.click(self.clear_chat, outputs=chatbot)
```

**Success Criteria:**
- ✅ History wird in Redis gespeichert
- ✅ Clear-Button funktioniert
- ✅ TTL verhindert unbegrenztes Wachstum
- ✅ 6+ Tests für Conversation Service

**Git Commit:** `feat(services): add conversation history persistence`

---

### Feature 10.5: Health Dashboard Integration (2 SP) 📊

**Goal:** Zeige System-Health in Gradio UI (optional Tab).

**Deliverables:**
- Health Tab mit Memory Stats
- Qdrant Status
- Redis Status
- Recent Query Metrics

**Technical Implementation:**

```python
# In build_interface():
with gr.Tab("📊 System Health"):
    gr.Markdown("### System Status")

    refresh_btn = gr.Button("🔄 Refresh", elem_id="refresh-health")

    health_status = gr.JSON(label="Health Metrics", elem_id="health-json")

    async def get_health():
        """Fetch health from existing endpoint."""
        from src.api.health.memory_health import get_memory_health
        return await get_memory_health()

    refresh_btn.click(get_health, outputs=health_status)

    # Auto-load on tab open
    demo.load(get_health, outputs=health_status)
```

**Success Criteria:**
- ✅ Health Tab zeigt Memory Stats
- ✅ Refresh Button funktioniert
- ✅ Nutzt existing Health Endpoints (Sprint 9)
- ✅ 2+ Tests für UI-Integration

**Git Commit:** `feat(ui): add health dashboard tab`

---

## Testing Strategy for Sprint 10

### Backend API Tests (TDD) ✅

**Coverage Target:** 90%+ für alle API Endpoints

```python
tests/unit/api/
├── test_chat_endpoints.py (15+ tests)
├── test_document_endpoints.py (8+ tests)
└── test_conversation_service.py (6+ tests)

tests/integration/
└── test_chat_e2e_flow.py (3 tests - happy paths)
```

**Testing mit Pytest + httpx:**
```python
@pytest.fixture
async def async_client():
    from src.api.main import app
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

### Gradio UI Tests (Unit Tests nur) ⚠️

**Coverage Target:** 60%+ für Gradio-Functions

```python
tests/unit/ui/
├── test_gradio_app.py (5+ tests)
└── test_gradio_upload.py (4+ tests)
```

**Keine Playwright Tests** für Sprint 10 (Gradio ist temporär).

### Manual Testing Checklist ✅

```markdown
- [ ] Chat-Interface lädt ohne Errors
- [ ] Beispiel-Queries funktionieren
- [ ] Dokument-Upload funktioniert
- [ ] Source Citations werden angezeigt
- [ ] Clear Chat Button funktioniert
- [ ] Health Dashboard zeigt Daten
- [ ] Multi-turn Conversation funktioniert
- [ ] Error Messages sind user-friendly
```

---

## Integration with Existing Components

Sprint 10 nutzt **alle bisherigen Sprints**:

```
Sprint 10 (Gradio UI)
    ↓ calls
Sprint 4 (QueryAgent) ← orchestriert Retrieval
    ↓ uses
Sprint 9 (UnifiedMemoryAPI) ← Session Memory
    ↓ uses
Sprint 7 (LightRAG) ← Graph-basiertes Retrieval
    ↓ uses
Sprint 2 (Qdrant + Embeddings) ← Vector Search
    ↓ uses
Sprint 1 (Infrastructure) ← Redis, Docker, Logging
```

**Keine neuen Komponenten**, nur **Integration Layer**.

---

## Dependencies & Setup

### New Dependencies

```toml
# pyproject.toml
[tool.poetry.dependencies]
gradio = "^4.0.0"  # UI Framework
python-multipart = "^0.0.6"  # File uploads in FastAPI
```

### Environment Variables

```bash
# .env
GRADIO_SERVER_NAME=0.0.0.0
GRADIO_SERVER_PORT=7860
GRADIO_SHARE=false  # Set true for public URL
```

### Run Commands

```bash
# Start Gradio UI
poetry run python src/ui/gradio_app.py

# OR integrate with FastAPI
poetry run uvicorn src.api.main:app --reload --port 8000
# Gradio runs on separate port 7860
```

---

## Success Criteria for Sprint 10

### Functional Requirements ✅
- ✅ User kann Fragen im Chat stellen
- ✅ System antwortet mit RAG-basierten Antworten
- ✅ Source Citations werden angezeigt
- ✅ Dokumente können hochgeladen werden
- ✅ Conversation History funktioniert
- ✅ System Health ist einsehbar

### Non-Functional Requirements ✅
- ✅ Response Time <2s für einfache Queries
- ✅ UI läuft stabil ohne Crashes
- ✅ Error Messages sind verständlich
- ✅ 30+ Tests (Backend focus)
- ✅ Code Coverage >80% (Backend APIs)

### User Experience ✅
- ✅ UI ist intuitiv bedienbar (ohne Dokumentation)
- ✅ Beispiel-Queries helfen beim Einstieg
- ✅ Upload-Feedback ist klar
- ✅ Citations sind nachvollziehbar

---

## Sprint 10 Timeline (1 Woche)

### Tag 1-2: Backend APIs (6 SP)
- Feature 10.1: Chat Endpoints (TDD)
- Feature 10.4: Conversation Service

### Tag 3-4: Gradio UI (5 SP)
- Feature 10.2: Chat Interface
- Feature 10.5: Health Dashboard

### Tag 5: Document Upload (4 SP)
- Feature 10.3: Upload Integration

### Tag 6: Integration Testing & Bugfixes (3 SP)
- Manual Testing
- Bug Fixing
- Documentation

### Tag 7: Review & Sprint Abschluss (2 SP)
- Code Review
- Sprint Report
- Demo vorbereiten

**Total:** 20 SP

---

## Post-Sprint 10: Backlog Items

### Immediate (Post-Sprint 10)
1. **User Feedback Collection** (2h)
   - Sammle Feedback zu Gradio UI
   - Liste gewünschte Features für React UI

2. **Performance Benchmarking** (3h)
   - Load Test mit Locust (10+ concurrent users)
   - Identifiziere Bottlenecks

### Future Sprints
1. **Sprint 11: React Migration** (30 SP)
   - Next.js Setup
   - Playwright E2E Test Suite
   - Production-ready UI/UX
   - Design System (Tailwind)

2. **Sprint 11: Admin Dashboard** (15 SP)
   - Streamlit-basiertes Admin Interface
   - Configuration Management
   - User Management

---

## ADR: Migration Path to React

**ADR-017: Gradio → React Migration Strategy**

**Context:** Sprint 10 verwendet Gradio als MVP, Sprint 11+ migriert zu React.

**Decision:**
1. Backend APIs (Sprint 10) sind **framework-agnostic** (RESTful)
2. Gradio UI bleibt als **fallback** für interne Entwickler
3. React UI wird **zusätzlich** gebaut, nicht als Ersatz
4. Beide UIs teilen sich dieselben Backend-Endpoints

**Migration Approach:**
```
Sprint 10: Gradio (localhost:7860) + FastAPI (localhost:8000)
    ↓
Sprint 11: Gradio (localhost:7860) + React (localhost:3000) + FastAPI (localhost:8000)
    ↓
Sprint 12: React (production) + FastAPI (production)
             Gradio (nur development)
```

**Benefits:**
- ✅ Kein Breaking Change
- ✅ A/B Testing möglich
- ✅ Gradio als Developer Tool behalten

---

## Notes & Assumptions

1. **Ollama muss laufen:** Gradio UI benötigt Ollama für Embeddings/LLM
2. **Redis/Qdrant/Neo4j müssen laufen:** `docker compose up -d`
3. **Dokumente müssen vorindiziert sein:** Oder via Upload indexieren
4. **Session IDs:** Werden clientseitig generiert (UUID), später Auth-basiert

---

## Git Strategy

```bash
# Feature Branches von sprint-10-dev
git checkout sprint-10-dev
git checkout -b feature/10.1-chat-endpoints
# ... develop & test
git checkout sprint-10-dev
git merge feature/10.1-chat-endpoints --no-ff
git push origin sprint-10-dev

# Repeat for 10.2, 10.3, 10.4, 10.5
```

**Final Merge:**
```bash
git checkout main
git merge sprint-10-dev --no-ff -m "feat(sprint10): Gradio MVP UI with chat and upload"
git push origin main
```

---

## Questions & Risks

### Questions for Clarification
- ✅ Resolved: UI Framework = Gradio (temporary)
- ✅ Resolved: Testing = Backend TDD, UI manual
- ⏸️ Open: Welche Dokumente sollen pre-loaded sein?
- ⏸️ Open: Soll Gradio `share=True` nutzen? (öffentliche URL)

### Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Gradio zu limitiert für Requirements | ✅ React-Migration geplant (Sprint 11) |
| Performance bei vielen Usern | ⚠️ Sprint 10 ist Single-User fokussiert |
| Breaking API Changes | ✅ Versionierte API (`/api/v1/`) |

---

## Definition of Done

- ✅ Alle 5 Features implementiert (20 SP)
- ✅ 30+ Tests passing (90%+ Backend Coverage)
- ✅ Gradio UI läuft stabil auf localhost:7860
- ✅ Chat + Upload funktionieren End-to-End
- ✅ Code Review abgeschlossen
- ✅ Git committed & pushed zu sprint-10-dev
- ✅ Sprint 10 Completion Report erstellt
- ✅ Demo-Video/Screenshots für Stakeholder

---

**Ready to Start:** ✅ YES
**Blocked By:** None
**Next Step:** Feature 10.1 implementieren (Chat Endpoints)
