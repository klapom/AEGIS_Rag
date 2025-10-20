# AEGIS RAG Gradio UI

Sprint 10 Gradio-based MVP User Interface.

## Installation

### Option 1: Poetry (Recommended)

Due to dependency conflicts with the main project, install Gradio separately:

```bash
# In the project directory
poetry run pip install gradio>=4.44.0
```

### Option 2: System Python

```bash
pip install gradio>=4.44.0
```

## Running the UI

### Step 1: Start Docker Services

```bash
docker compose up -d
```

Verify services are running:
```bash
docker ps
```

Should show: qdrant, redis, neo4j, ollama (all healthy)

### Step 2: Index Demo Documents (First Time Only)

```bash
poetry run python scripts/setup_demo_data.py
```

This indexes all `*.md` files in the project (~900+ documents).

**Options:**
- `--stats`: Show current collection stats
- `--force`: Re-index even if data exists
- `--clear`: Delete all indexed data

### Step 3: Start FastAPI Backend

```bash
# Terminal 1
poetry run uvicorn src.api.main:app --reload --port 8000
```

Verify API is running: http://localhost:8000/health

### Step 4: Start Gradio UI

```bash
# Terminal 2
poetry run python src/ui/gradio_app.py
```

The UI will be available at: **http://localhost:7860**

## Features

### 💬 Chat Tab (Feature 10.2)
- Multi-turn conversations with session management
- Source citations from retrieved documents
- Example queries for quick testing
- Clear chat button to reset conversation

### 📄 Document Upload Tab (Feature 10.3)
- Upload PDF, TXT, MD, DOCX, CSV files
- Auto-indexing with status feedback
- Supports drag & drop

### 📊 System Health Tab (Feature 10.5)
- Real-time memory metrics
- Redis, Qdrant, Graphiti status
- Performance stats (latency, capacity)

### ℹ️ About Tab
- System information
- Technology stack
- Session ID display

## API Integration

The Gradio UI calls these FastAPI endpoints:

- `POST /api/v1/chat` - Main chat endpoint
- `GET /api/v1/chat/history/{session_id}` - Retrieve history
- `DELETE /api/v1/chat/history/{session_id}` - Clear history
- `POST /api/v1/documents/upload` - Upload documents (TODO)
- `GET /health/memory` - Health metrics

## Configuration

Edit `src/core/config.py` to change:

```python
api_port: int = 8000  # FastAPI port
```

Edit `src/ui/gradio_app.py` to change:

```python
server_port: int = 7860  # Gradio port
```

## Troubleshooting

### "Gradio is not installed"

```bash
poetry run pip install gradio>=4.44.0
```

### "Connection refused" in Chat

Make sure FastAPI is running:
```bash
curl http://localhost:8000/health
```

### "No documents found" in responses

Index demo data first:
```bash
poetry run python scripts/setup_demo_data.py --force
```

### Empty Health Dashboard

Check if memory services are running:
```bash
docker ps | grep -E "redis|qdrant"
```

## Development

### Running in Dev Mode

```bash
# With auto-reload
poetry run python src/ui/gradio_app.py
```

### Accessing from Remote Machine

```bash
# Change server_name in gradio_app.py
demo.launch(
    server_name="0.0.0.0",  # Listen on all interfaces
    server_port=7860,
    share=False  # Or True for public URL
)
```

### Public URL (Gradio Share)

```bash
# In gradio_app.py, set:
share=True
```

This creates a temporary public URL (valid for 72 hours).

## Architecture

```
User Browser (localhost:7860)
    ↓
Gradio UI (src/ui/gradio_app.py)
    ↓ HTTP REST API
FastAPI Backend (localhost:8000)
    ↓
CoordinatorAgent (Multi-Agent Orchestration)
    ↓
├─ VectorSearchAgent → Qdrant
├─ GraphQueryAgent → Neo4j
└─ MemoryAgent → Redis
```

## Next Steps (Sprint 11+)

- **React Migration:** Replace Gradio with Next.js + React
- **Playwright E2E Tests:** Full UI testing suite
- **Authentication:** User management and permissions
- **Streaming Responses:** Real-time token streaming
- **Mobile Optimization:** Responsive design improvements

## Limitations (Gradio MVP)

⚠️ This is a **Minimum Viable Product** for Sprint 10:

- No authentication (single user)
- No real-time streaming (batch responses)
- Basic error handling
- Limited customization (Gradio constraints)
- Not production-ready (use React in Sprint 11+)

## License

Part of AEGIS RAG Project - Sprint 10 Deliverable
