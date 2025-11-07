# AEGIS RAG - Step-by-Step Testing Guide

**Version:** Sprint 20 (Performance Optimization)
**Date:** 2025-11-03
**Status:** Ready for Testing

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Service Startup Sequence](#service-startup-sequence)
4. [Frontend Testing](#frontend-testing)
5. [Backend API Testing](#backend-api-testing)
6. [Sprint 20 Performance Benchmarks](#sprint-20-performance-benchmarks)
7. [Troubleshooting](#troubleshooting)
8. [Test Results Documentation](#test-results-documentation)

---

## Prerequisites

### Required Software

- **Docker Desktop** (for Qdrant, Neo4j, Redis)
- **Node.js** 18+ and npm
- **Python** 3.11+
- **Poetry** (Python dependency manager)
- **Ollama** (for LLM inference)

### Verify Installations

```bash
# Check Docker
docker --version
docker compose version

# Check Node.js
node --version
npm --version

# Check Python
python --version

# Check Poetry
poetry --version

# Check Ollama
ollama --version
```

---

## Environment Setup

### Step 1: Clone and Navigate

```bash
cd "C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag"
```

### Step 2: Environment Configuration

Ensure `.env` file exists in the root directory with required settings:

```bash
# Backend
BACKEND_HOST=localhost
BACKEND_PORT=8000

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_GENERATION=llama3.2:3b
OLLAMA_MODEL_EMBEDDING=bge-m3

# Security
JWT_SECRET_KEY=your_secret_key_here
```

### Step 3: Install Dependencies

```bash
# Backend dependencies
poetry install

# Frontend dependencies
cd frontend
npm install
cd ..
```

---

## Service Startup Sequence

### Step 1: Start Docker Services

```bash
# Start Qdrant, Neo4j, Redis
docker compose up -d

# Verify all services are running
docker compose ps
```

**Expected Output:**
```
NAME                COMMAND                  SERVICE             STATUS
qdrant              "/qdrant/qdrant"         qdrant              Up
neo4j               "tini -s -- /startu…"    neo4j               Up
redis               "docker-entrypoint.s…"   redis               Up
```

### Step 2: Start Ollama

```bash
# If Ollama is not running
ollama serve

# In a new terminal, pull required models
ollama pull llama3.2:3b
ollama pull bge-m3
```

### Step 3: Start Backend API

```bash
# From project root
python -m src.api.main
```

**Expected Output:**
```
INFO:     Uvicorn running on http://localhost:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx]
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Verify Backend:**
```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-03T...",
  "services": {
    "qdrant": "connected",
    "neo4j": "connected",
    "redis": "connected",
    "ollama": "connected"
  }
}
```

### Step 4: Start Frontend

Open a new terminal:

```bash
cd frontend
npm run dev
```

**Expected Output:**
```
  VITE v7.1.7  ready in XXX ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

---

## Frontend Testing

### Test 1: Login Page

1. **Navigate to:** http://localhost:5173/
2. **Expected:** Login form with email/password fields
3. **Test Actions:**
   - Try invalid credentials → Should show error message
   - Try valid credentials → Should redirect to dashboard

**Test Credentials (if seeded):**
```
Email: test@aegisrag.local
Password: test123
```

---

### Test 2: Dashboard

1. **Navigate to:** http://localhost:5173/dashboard
2. **Expected Elements:**
   - Welcome message
   - Quick stats (documents, queries, projects)
   - Recent activity feed
   - Quick action buttons

**Test Actions:**
- Click "New Chat" → Should navigate to `/chat`
- Click "Upload Document" → Should navigate to `/documents/upload`
- Check that stats load correctly

---

### Test 3: Chat Interface (RAG Core)

1. **Navigate to:** http://localhost:5173/chat
2. **Expected Elements:**
   - Query input field
   - Search mode selector (Vector, BM25, Hybrid, LightRAG)
   - Send button
   - Chat history sidebar

**Test Scenarios:**

#### Scenario 3.1: Vector Search
```
Mode: Vector
Query: "Was ist RAG?"
Expected: Semantic search results with document chunks
```

#### Scenario 3.2: BM25 Search
```
Mode: BM25
Query: "Python API"
Expected: Keyword-based search results
```

#### Scenario 3.3: Hybrid Search
```
Mode: Hybrid
Query: "Wie funktioniert die Authentifizierung?"
Expected: Combined vector + BM25 results
```

#### Scenario 3.4: LightRAG Mode
```
Mode: LightRAG
Query: "Erkläre die Architektur"
Expected: Graph-enhanced RAG results with entity relationships
```

**Performance Checks (Sprint 20 Features):**
- ✅ Response starts streaming within 500ms
- ✅ First token appears within 1 second
- ✅ Smooth streaming (no stuttering)
- ✅ Search mode indicator updates correctly

---

### Test 4: Document Upload

1. **Navigate to:** http://localhost:5173/documents/upload
2. **Expected Elements:**
   - Drag-and-drop area
   - File type indicators (PDF, TXT, MD, DOCX)
   - Upload progress bar
   - Success/error notifications

**Test Actions:**
- Upload a PDF document (< 10MB)
- Upload a text file
- Try uploading an unsupported format → Should show error
- Monitor upload progress bar

---

### Test 5: Document Management

1. **Navigate to:** http://localhost:5173/documents
2. **Expected Elements:**
   - Document list/grid
   - Search/filter controls
   - Document metadata (name, size, date, status)
   - Actions: View, Download, Delete

**Test Actions:**
- Search for a document by name
- Filter by document type
- Click "View" → Should show document details
- Click "Delete" → Should show confirmation dialog

---

### Test 6: Chat History

1. **Navigate to:** http://localhost:5173/chat/history
2. **Expected Elements:**
   - List of previous conversations
   - Timestamps
   - Query preview
   - "Load" and "Delete" actions

**Test Actions:**
- Click "Load" on a conversation → Should restore in chat interface
- Delete a conversation → Should remove from list

---

### Test 7: User Profile

1. **Navigate to:** http://localhost:5173/profile
2. **Expected Elements:**
   - User information (name, email)
   - Preferences section (theme, language, default search mode)
   - Password change form
   - Account statistics

**Test Actions:**
- Change theme (Light/Dark) → Should apply immediately
- Change default search mode → Should persist in chat
- Update password → Should require current password

---

### Test 8: Admin Panel (if admin user)

1. **Navigate to:** http://localhost:5173/admin
2. **Expected Elements:**
   - User management
   - System health dashboard
   - Configuration settings
   - Activity logs

---

## Backend API Testing

### Test 1: Health Check

```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{
  "status": "healthy",
  "services": {
    "qdrant": "connected",
    "neo4j": "connected",
    "redis": "connected",
    "ollama": "connected"
  }
}
```

---

### Test 2: Authentication

```bash
# Register new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "SecurePass123!",
    "name": "Test User"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser@example.com",
    "password": "SecurePass123!"
  }'
```

**Expected Login Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": "...",
    "email": "testuser@example.com",
    "name": "Test User"
  }
}
```

**Save the `access_token` for subsequent requests!**

---

### Test 3: Chat Query (RAG Core)

```bash
# Set your token from previous step
TOKEN="your_access_token_here"

# Vector search
curl -X POST http://localhost:8000/api/v1/chat/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Was ist RAG?",
    "mode": "vector",
    "top_k": 5
  }'

# Hybrid search
curl -X POST http://localhost:8000/api/v1/chat/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Erkläre die Architektur",
    "mode": "hybrid",
    "top_k": 5
  }'

# LightRAG mode
curl -X POST http://localhost:8000/api/v1/chat/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Wie funktioniert Graphiti?",
    "mode": "lightrag",
    "top_k": 5
  }'
```

**Expected Response Structure:**
```json
{
  "query": "Was ist RAG?",
  "mode": "vector",
  "response": "RAG (Retrieval-Augmented Generation) ist...",
  "sources": [
    {
      "document_id": "...",
      "chunk_id": "...",
      "content": "...",
      "score": 0.85,
      "metadata": {...}
    }
  ],
  "metadata": {
    "retrieval_time_ms": 120,
    "generation_time_ms": 850,
    "total_time_ms": 970
  }
}
```

---

### Test 4: Document Upload

```bash
TOKEN="your_access_token_here"

# Upload a document
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/document.pdf" \
  -F "metadata={\"title\":\"Test Document\",\"tags\":[\"test\"]}"
```

**Expected Response:**
```json
{
  "document_id": "...",
  "filename": "document.pdf",
  "status": "processing",
  "chunks_created": 0,
  "message": "Document uploaded successfully and is being processed"
}
```

---

### Test 5: List Documents

```bash
TOKEN="your_access_token_here"

curl http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN"
```

**Expected Response:**
```json
{
  "documents": [
    {
      "id": "...",
      "filename": "document.pdf",
      "status": "processed",
      "chunks_count": 42,
      "uploaded_at": "2025-11-03T...",
      "metadata": {...}
    }
  ],
  "total": 1
}
```

---

## Sprint 20 Performance Benchmarks

Sprint 20 focused on **Performance Optimization**. Use these scripts to verify improvements.

### Benchmark 1: Chat Model Evaluation

**Purpose:** Compare llama3.2:3b vs gemma2:2b performance

```bash
# From project root
python scripts/evaluate_chat_models.py --all
```

**Expected Output:**
```
=== AEGIS RAG Chat Model Evaluation ===

Model: llama3.2:3b
--------------------------------------------------
Query 1: "Was ist RAG?"
  ✓ Response Time: 1.24s
  ✓ First Token: 0.45s
  ✓ Tokens/sec: 28.5

Query 2: "Erkläre die Architektur"
  ✓ Response Time: 2.10s
  ✓ First Token: 0.52s
  ✓ Tokens/sec: 26.8

Model: gemma2:2b
--------------------------------------------------
...

=== Summary ===
Recommended Model: llama3.2:3b (best balance of speed/quality)
```

**Test Matrix (20 queries × 2 models):**
- ✅ Response time < 3 seconds
- ✅ First token < 1 second
- ✅ Throughput > 20 tokens/sec
- ✅ Quality scores > 0.8

---

### Benchmark 2: Comprehensive Model Evaluation

**Purpose:** Evaluate embedding models (BGE-M3 vs alternatives)

```bash
python scripts/evaluate_models_comprehensive.py
```

**Expected Output:**
```
=== Model Performance Report ===

Embedding Model: bge-m3
--------------------------------------------------
  Embedding Time (1000 tokens): 245ms
  Dimension: 1024
  Batch Size: 32

  Retrieval Accuracy (100 queries):
    - Vector Search: 0.87
    - Hybrid Search: 0.91

  Memory Usage: 1.2GB

=== Recommendations ===
✓ bge-m3: Best for production (speed + accuracy)
```

---

### Benchmark 3: LM Studio Parameter Evaluation

**Purpose:** Test LM Studio integration with parameter variations

```bash
python scripts/evaluate_lmstudio_params.py
```

**Test Matrix:**
- Temperature: [0.3, 0.5, 0.7, 0.9]
- Top-p: [0.8, 0.9, 0.95]
- Max Tokens: [512, 1024, 2048]

**Expected Output:**
```
=== LM Studio Parameter Sweep ===

Configuration 1: temp=0.3, top_p=0.9, max_tokens=1024
  Response Time: 1.85s
  Quality Score: 0.89
  Coherence: High

Configuration 2: temp=0.7, top_p=0.95, max_tokens=1024
  Response Time: 2.10s
  Quality Score: 0.82
  Coherence: Medium

=== Recommendation ===
✓ Optimal: temp=0.5, top_p=0.9, max_tokens=1024
```

---

## Troubleshooting

### Issue 1: Docker Services Not Starting

**Symptom:** `docker compose ps` shows services as "unhealthy"

**Solutions:**
```bash
# Check Docker daemon
docker info

# Restart Docker Desktop
# (Windows: Right-click tray icon → Restart)

# Remove volumes and restart
docker compose down -v
docker compose up -d

# Check logs
docker compose logs qdrant
docker compose logs neo4j
docker compose logs redis
```

---

### Issue 2: Backend Connection Errors

**Symptom:** Frontend shows "API Connection Failed"

**Solutions:**
```bash
# Check backend is running
curl http://localhost:8000/health

# Check .env configuration
cat .env | grep BACKEND

# Restart backend
# (Press CTRL+C in backend terminal, then restart)
python -m src.api.main

# Check firewall settings (Windows)
# Allow Python through Windows Firewall
```

---

### Issue 3: Ollama Model Not Found

**Symptom:** "Model llama3.2:3b not found"

**Solutions:**
```bash
# List installed models
ollama list

# Pull missing model
ollama pull llama3.2:3b
ollama pull bge-m3

# Verify Ollama is running
curl http://localhost:11434/api/tags
```

---

### Issue 4: Qdrant Collection Errors

**Symptom:** "Collection 'aegis_rag_chunks' not found"

**Solutions:**
```bash
# Check Qdrant status
curl http://localhost:6333/collections

# Recreate collections (if needed)
python -m src.scripts.init_collections

# Check Qdrant logs
docker compose logs qdrant
```

---

### Issue 5: Frontend Build Errors

**Symptom:** `npm run dev` fails with TypeScript errors

**Solutions:**
```bash
cd frontend

# Clear cache
rm -rf node_modules
rm package-lock.json

# Reinstall dependencies
npm install

# Run type check separately
npm run type-check

# If still failing, check Node.js version
node --version  # Should be 18+
```

---

### Issue 6: Neo4j Connection Refused

**Symptom:** "Unable to connect to Neo4j at bolt://localhost:7687"

**Solutions:**
```bash
# Check Neo4j is running
docker compose ps neo4j

# Check Neo4j logs
docker compose logs neo4j

# Access Neo4j browser
# Open: http://localhost:7474
# Login: neo4j / your_password

# Restart Neo4j
docker compose restart neo4j
```

---

### Issue 7: Redis Connection Timeout

**Symptom:** "Redis connection timeout"

**Solutions:**
```bash
# Check Redis is running
docker compose ps redis

# Test Redis connection
docker exec -it redis redis-cli ping
# Expected: PONG

# Flush Redis (if needed)
docker exec -it redis redis-cli FLUSHALL

# Restart Redis
docker compose restart redis
```

---

### Issue 8: Slow Query Performance

**Symptom:** Queries take > 5 seconds

**Diagnostics:**
```bash
# Check system resources
docker stats

# Check Ollama performance
curl http://localhost:11434/api/ps

# Run performance benchmarks
python scripts/evaluate_chat_models.py --query "test" --verbose

# Check Qdrant collection size
curl http://localhost:6333/collections/aegis_rag_chunks
```

**Solutions:**
- Reduce `top_k` in queries (default: 5)
- Use smaller LLM model (gemma2:2b instead of llama3.2:3b)
- Enable caching in Redis
- Optimize Qdrant HNSW parameters

---

## Test Results Documentation

### Performance Tracking Template

Create a file `test_results_YYYY-MM-DD.md` with:

```markdown
# AEGIS RAG Test Results

**Date:** YYYY-MM-DD
**Tester:** Your Name
**Sprint:** 20 (Performance Optimization)

## Frontend Tests

| Test | Status | Notes |
|------|--------|-------|
| Login Page | ✅ PASS | Login successful |
| Dashboard | ✅ PASS | Stats load correctly |
| Chat Interface | ✅ PASS | All modes work |
| Document Upload | ❌ FAIL | Timeout on large files |
| ... | | |

## Backend API Tests

| Endpoint | Status | Response Time | Notes |
|----------|--------|---------------|-------|
| /health | ✅ PASS | 45ms | All services connected |
| /api/v1/auth/login | ✅ PASS | 120ms | JWT issued |
| /api/v1/chat/query | ✅ PASS | 1.2s | Vector mode |
| ... | | | |

## Performance Benchmarks

### Chat Model Evaluation
- **llama3.2:3b:** Avg 1.5s, 27 tok/s ✅
- **gemma2:2b:** Avg 0.9s, 35 tok/s ✅

### Retrieval Performance
- **Vector Search:** 120ms avg ✅
- **BM25 Search:** 80ms avg ✅
- **Hybrid Search:** 150ms avg ✅
- **LightRAG:** 200ms avg ⚠️ (within 250ms target)

## Issues Found

1. **Issue:** Document upload timeout for files > 50MB
   **Severity:** Medium
   **Workaround:** Split large documents

2. **Issue:** Chat history pagination missing
   **Severity:** Low
   **Status:** Feature request for Sprint 21

## Recommendations

- ✅ Sprint 20 performance targets met
- ✅ Ready for production testing
- 🔄 Consider caching for repeated queries
```

---

## Next Steps

### After Testing Sprint 20:

1. **Document Results**: Fill out the performance tracking template
2. **Report Issues**: Create GitHub issues for any bugs found
3. **Sprint 20 Completion**: Run all benchmarks and create completion report
4. **Sprint 21 Planning**: Review ADR-025 (mem0 integration)

### Sprint 21 Preview (Next Sprint):

**Focus:** Authentication & Multi-Tenancy + mem0 User Preferences

**New Features to Test:**
- JWT-based authentication with refresh tokens
- User registration/login flows
- Role-based access control (RBAC)
- User preference learning (mem0 Layer 0)
- Personalized chat responses

---

## Quick Reference

### Essential URLs

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Qdrant UI:** http://localhost:6333/dashboard
- **Neo4j Browser:** http://localhost:7474
- **Redis Commander:** (if installed) http://localhost:8081

### Service Ports

| Service | Port | Protocol |
|---------|------|----------|
| Frontend | 5173 | HTTP |
| Backend | 8000 | HTTP |
| Qdrant | 6333 | HTTP |
| Neo4j | 7687 | Bolt |
| Neo4j Browser | 7474 | HTTP |
| Redis | 6379 | TCP |
| Ollama | 11434 | HTTP |

### Useful Commands

```bash
# Start everything
docker compose up -d && python -m src.api.main &
cd frontend && npm run dev

# Stop everything
docker compose down
# (Then CTRL+C in backend and frontend terminals)

# View logs
docker compose logs -f
docker compose logs -f qdrant
docker compose logs -f neo4j

# Reset everything
docker compose down -v
docker compose up -d
python -m src.scripts.init_collections

# Run all tests
cd frontend && npm run test
poetry run pytest tests/
```

---

## Support

**Documentation:**
- [docs/CLAUDE.md](docs/CLAUDE.md) - Project overview
- [docs/CONTEXT_REFRESH.md](docs/CONTEXT_REFRESH.md) - Current status
- [docs/sprints/SPRINT_20_PLAN.md](docs/sprints/SPRINT_20_PLAN.md) - Sprint 20 details

**Getting Help:**
- Check troubleshooting section above
- Review Docker logs: `docker compose logs`
- Check backend logs in terminal
- Verify all prerequisites are installed

---

**Happy Testing! 🚀**
