# AegisRAG Quick Start Guide

**Get AegisRAG running in 15 minutes**
**Last Updated:** 2025-11-16 (Sprint 28)

---

## Prerequisites

### Required Software

1. **Python 3.12.7**
   ```bash
   python --version
   # Expected: Python 3.12.7
   ```

2. **Poetry** (Dependency Management)
   ```bash
   poetry --version
   # Expected: Poetry (version 1.7+)

   # Install if missing:
   pip install poetry
   ```

3. **Node.js 20+** (Frontend)
   ```bash
   node --version
   # Expected: v20.x.x or higher

   npm --version
   # Expected: 10.x.x or higher
   ```

4. **Docker & Docker Compose** (Databases)
   ```bash
   docker --version
   # Expected: Docker version 24.x or higher

   docker-compose --version
   # Expected: Docker Compose version 2.x or higher
   ```

5. **Git** (Version Control)
   ```bash
   git --version
   # Expected: git version 2.x or higher
   ```

---

## Quick Start (15 Minutes)

### Step 1: Clone Repository (1 min)

```bash
# Clone repository
git clone https://github.com/klapom/AEGIS_Rag.git
cd AEGIS_Rag

# Verify directory structure
ls -la
# Expected: src/, frontend/, docker-compose.yml, pyproject.toml, etc.
```

### Step 2: Environment Setup (2 min)

```bash
# Copy environment template
cp .env.template .env

# Edit .env file (required: Ollama URL, optional: API keys)
# Windows: notepad .env
# Linux/Mac: nano .env
```

**Minimal `.env` Configuration:**
```bash
# Ollama (Primary LLM - No API keys needed!)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_GENERATION=llama3.2:8b
OLLAMA_MODEL_QUERY=llama3.2:3b

# Optional: Alibaba Cloud DashScope (for VLM and cloud models)
# ALIBABA_CLOUD_API_KEY=sk-...

# Optional: OpenAI (if not using local Ollama)
# OPENAI_API_KEY=sk-...

# Database URLs (Docker defaults - no changes needed)
QDRANT_HOST=localhost
QDRANT_PORT=6333
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=aegis-password-123
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Step 3: Start Databases (3 min)

```bash
# Start all databases via Docker Compose
docker-compose up -d qdrant neo4j redis

# Verify all containers are running
docker-compose ps

# Expected output:
# NAME       STATUS              PORTS
# qdrant     Up (healthy)        0.0.0.0:6333->6333/tcp
# neo4j      Up (healthy)        0.0.0.0:7474->7474/tcp, 0.0.0.0:7687->7687/tcp
# redis      Up (healthy)        0.0.0.0:6379->6379/tcp

# Wait for health checks (30 seconds)
docker-compose ps
# All services should show "Up (healthy)"
```

**Verify Database Access:**
```bash
# Qdrant UI
open http://localhost:6333/dashboard
# Expected: Qdrant dashboard (empty, no collections yet)

# Neo4j Browser
open http://localhost:7474
# Login: neo4j / aegis-password-123
# Expected: Neo4j Browser (empty database)

# Redis ping
redis-cli -h localhost -p 6379 PING
# Expected: PONG
```

### Step 4: Backend Setup (4 min)

```bash
# Install Python dependencies with Poetry
poetry install

# Verify virtual environment
poetry env info
# Expected: Python 3.12.7, virtualenv: .venv

# Activate virtual environment (optional, Poetry handles this)
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
```

### Step 5: Start Backend API (1 min)

```bash
# Start FastAPI backend (development mode with hot reload)
poetry run uvicorn src.api.main:app --reload --port 8000

# Expected output:
# INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
# INFO:     Started reloader process
# INFO:     Started server process
# INFO:     Application startup complete
```

**Verify Backend:**
```bash
# Open new terminal (keep backend running in first terminal)

# Health check
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-16T10:00:00Z"
}

# API documentation (Swagger UI)
open http://localhost:8000/docs
```

### Step 6: Frontend Setup (2 min)

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Expected: ~500 packages installed in 30-60 seconds
```

### Step 7: Start Frontend (1 min)

```bash
# Start Vite development server
npm run dev

# Expected output:
#   VITE v5.0.0  ready in 500 ms
#   ➜  Local:   http://localhost:5173/
#   ➜  Network: use --host to expose
#   ➜  press h to show help
```

**Access Frontend:**
- Open browser: http://localhost:5173
- Expected: AegisRAG Chat Interface

### Step 8: Initialize Databases (1 min)

**Option A: Use Sample Data (Quick Start)**
```bash
# Navigate back to project root
cd ..

# Load sample documents (50 chunks from demo PDFs)
poetry run python scripts/load_sample_data.py

# Expected output:
# Loading sample data...
# ✓ Created Qdrant collection: documents_v1
# ✓ Loaded 50 document chunks
# ✓ Created Neo4j entities: 25 nodes, 40 relationships
# ✓ Sample data loaded successfully
```

**Option B: Full Ingestion (15-30 min)**
```bash
# Run full document ingestion pipeline
poetry run python scripts/ingest_documents.py --input data/documents/ --output data/processed/

# Expected output:
# Starting document ingestion...
# Processing: document1.pdf (15 pages)
# ✓ OCR completed (EasyOCR, 95% accuracy)
# ✓ Extracted 120 chunks
# ✓ Generated 45 entities
# ✓ Stored in Qdrant: 120 vectors
# ✓ Stored in Neo4j: 45 nodes, 80 edges
# ...
# Ingestion complete: 500 chunks, 200 entities
```

---

## Verify Installation

### 1. Backend Health Checks

```bash
# Main health check
curl http://localhost:8000/health

# Memory health (3-layer architecture)
curl http://localhost:8000/health/memory

# Expected: All components "healthy"
```

### 2. Database Verification

**Qdrant (Vector Search):**
```bash
# List collections
curl http://localhost:6333/collections

# Expected:
{
  "result": {
    "collections": [
      {"name": "documents_v1"}
    ]
  }
}
```

**Neo4j (Knowledge Graph):**
```cypher
// Open Neo4j Browser: http://localhost:7474
// Run query:
MATCH (n) RETURN count(n) AS node_count;

// Expected: node_count > 0 (e.g., 25 nodes from sample data)
```

**Redis (Short-Term Memory):**
```bash
redis-cli -h localhost -p 6379
> DBSIZE
(integer) 0  # Initially empty, will fill with conversations

> KEYS *
(empty array)
```

### 3. Test Query

**Via Frontend (Browser):**
1. Open http://localhost:5173
2. Enter query: "What is AegisRAG?"
3. Click "Search"
4. Expected: Streaming answer with sources displayed

**Via API (cURL):**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is AegisRAG?",
    "intent": "general",
    "include_sources": true
  }'

# Expected: JSON response with streaming answer and sources
```

---

## Common Commands

### Backend

```bash
# Start backend (development mode)
poetry run uvicorn src.api.main:app --reload --port 8000

# Run tests
poetry run pytest tests/

# Run specific test file
poetry run pytest tests/unit/test_qdrant_client.py -v

# Code formatting
poetry run black src/
poetry run ruff check src/

# Type checking
poetry run mypy src/
```

### Frontend

```bash
cd frontend

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm test

# Type checking
npm run type-check

# Linting
npm run lint
```

### Docker

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d qdrant

# Stop all services
docker-compose down

# View logs
docker-compose logs -f qdrant
docker-compose logs -f neo4j

# Restart service
docker-compose restart qdrant

# Remove all data (WARNING: Deletes databases!)
docker-compose down -v
```

---

## Directory Structure

```
AEGIS_Rag/
├── src/                        # Backend source code
│   ├── api/                    # FastAPI endpoints
│   ├── agents/                 # LangGraph agents
│   ├── components/             # Core components
│   │   ├── vector_search/      # Qdrant + Hybrid Search
│   │   ├── graph_rag/          # LightRAG + Neo4j
│   │   ├── memory/             # Graphiti + Redis
│   │   ├── llm_proxy/          # AegisLLMProxy (Multi-cloud)
│   │   └── ingestion/          # Document ingestion
│   ├── core/                   # Shared utilities
│   └── prompts/                # LLM prompts
├── frontend/                   # React 19 + TypeScript
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── pages/              # Page components
│   │   ├── api/                # API client
│   │   └── types/              # TypeScript types
│   └── public/                 # Static assets
├── tests/                      # Test suites
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── e2e/                    # End-to-end tests
├── docs/                       # Documentation
│   ├── architecture/           # Architecture docs
│   ├── adr/                    # Architecture Decision Records
│   ├── operations/             # Ops guides (this file!)
│   └── sprints/                # Sprint reports
├── scripts/                    # Utility scripts
│   ├── ingest_documents.py     # Document ingestion
│   ├── load_sample_data.py     # Load demo data
│   └── migrate.py              # Database migrations
├── config/                     # Configuration files
│   ├── prometheus/             # Prometheus config
│   └── grafana/                # Grafana dashboards
├── data/                       # Data directory
│   ├── documents/              # Input documents
│   └── processed/              # Processed data
├── docker-compose.yml          # Docker services
├── pyproject.toml              # Python dependencies (Poetry)
├── .env                        # Environment variables
└── README.md                   # Project overview
```

---

## Troubleshooting

### Port Already in Use

**Error:** `Address already in use (port 8000)`

**Solution:**
```bash
# Find process using port
# Windows:
netstat -ano | findstr :8000

# Linux/Mac:
lsof -i :8000

# Kill process
# Windows: taskkill /PID <PID> /F
# Linux/Mac: kill -9 <PID>
```

### Docker Container Won't Start

**Error:** `Container unhealthy` or `Exited (1)`

**Solution:**
```bash
# Check logs
docker-compose logs qdrant
docker-compose logs neo4j

# Common issues:
# - Port conflict: Change port in docker-compose.yml
# - Insufficient memory: Increase Docker memory limit
# - Permission denied: Run with sudo (Linux) or check Docker settings (Windows)

# Restart from scratch
docker-compose down -v
docker-compose up -d
```

### Poetry Install Fails

**Error:** `Poetry could not find a pyproject.toml file`

**Solution:**
```bash
# Ensure you're in project root
pwd
# Expected: /path/to/AEGIS_Rag

# Verify pyproject.toml exists
ls pyproject.toml

# Reinstall Poetry if corrupted
pip install --upgrade poetry
```

### Frontend Won't Start

**Error:** `Module not found` or `ENOENT`

**Solution:**
```bash
cd frontend

# Delete node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear npm cache
npm cache clean --force
npm install
```

### Ollama Connection Failed

**Error:** `Connection refused to localhost:11434`

**Solution:**
```bash
# Start Ollama (if not running)
ollama serve

# Pull required models
ollama pull llama3.2:3b
ollama pull llama3.2:8b
ollama pull nomic-embed-text

# Verify Ollama is accessible
curl http://localhost:11434/api/tags
```

---

## Next Steps

### 1. Load Your Own Documents

```bash
# Place PDFs in data/documents/
cp /path/to/your/documents/*.pdf data/documents/

# Run ingestion
poetry run python scripts/ingest_documents.py --input data/documents/
```

### 2. Configure Cloud LLMs (Optional)

Edit `.env`:
```bash
# Alibaba Cloud DashScope (for VLM and cloud models)
ALIBABA_CLOUD_API_KEY=sk-your-key-here
MONTHLY_BUDGET_ALIBABA_CLOUD=10.0  # USD

# OpenAI (alternative cloud provider)
OPENAI_API_KEY=sk-your-key-here
MONTHLY_BUDGET_OPENAI=20.0  # USD
```

### 3. Set Up Monitoring

```bash
# Start Prometheus + Grafana
docker-compose up -d prometheus grafana

# Access Grafana
open http://localhost:3000
# Login: admin / admin (change on first login)

# See: docs/operations/MONITORING_GUIDE.md
```

### 4. Configure Settings (Frontend)

1. Open http://localhost:5173/settings
2. Set theme: Light / Dark / Auto
3. Configure Ollama URL (if not localhost)
4. Set default model (llama3.2:3b or llama3.2:8b)

---

## Additional Resources

- **Full Documentation:** `docs/README.md`
- **Architecture:** `docs/architecture/SYSTEM_OVERVIEW.md`
- **API Reference:** http://localhost:8000/docs (when backend running)
- **Monitoring Guide:** `docs/operations/MONITORING_GUIDE.md`
- **Sprint Reports:** `docs/sprints/`
- **ADRs:** `docs/adr/`

---

## Support

**Issues:**
- GitHub Issues: https://github.com/klapom/AEGIS_Rag/issues
- Check `docs/TROUBLESHOOTING.md` for common problems

**Community:**
- Discord: (coming soon)
- Discussions: GitHub Discussions

---

**Last Updated:** 2025-11-16 (Sprint 28)
**Maintainer:** Klaus Pommer
**License:** MIT
