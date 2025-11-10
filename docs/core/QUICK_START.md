# Quick Start Guide
## AegisRAG - Agentisches RAG-System mit Claude Code

Dieser Guide führt dich durch das initiale Setup des Projekts in Claude Code.

---

## 📋 Voraussetzungen

### Lokale Umgebung
- **Python 3.12.7** installiert (3.11+ kompatibel)
- **Docker & Docker Compose** installiert
- **NVIDIA Container Toolkit** (für GPU-Beschleunigung, siehe unten)
- **Git** konfiguriert
- **Claude Code CLI** installiert

### GPU-Beschleunigung (Sprint 21+)

**NVIDIA Container Toolkit** (erforderlich für Docling CUDA Container):

```powershell
# Windows: NVIDIA Container Toolkit Installation
# Voraussetzung: NVIDIA GPU (z.B. RTX 3060 6GB), CUDA 12.4+

# 1. Docker Desktop mit WSL2 Backend installieren
winget install Docker.DockerDesktop

# 2. NVIDIA Driver installieren (falls nicht vorhanden)
# Download: https://www.nvidia.com/Download/index.aspx

# 3. CUDA Toolkit 12.4+ installieren
# Download: https://developer.nvidia.com/cuda-downloads

# 4. NVIDIA Container Toolkit in WSL2 installieren
wsl
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
exit

# 5. GPU-Zugriff testen
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

**Hinweis:** Ohne GPU läuft Docling im CPU-Modus (langsamer, siehe ADR-027).

### Ollama (Local LLM - Primär)

- **Ollama installiert** (https://ollama.ai)
- **Empfohlene Models (Sprint 21)**:
  ```bash
  # Core Models
  ollama pull llama3.2:3b                       # Schnelle Queries (2GB RAM)
  ollama pull llama3.2:8b                       # Qualitäts-Generierung (4.7GB RAM)

  # Embeddings (Sprint 16: BGE-M3 Migration, ADR-024)
  ollama pull bge-m3                            # Multilingual Embeddings (1024-dim, 2.2GB)

  # Entity/Relation Extraction (Sprint 13, ADR-018)
  ollama pull hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q8_0  # Gemma 3 4B (4.5GB RAM)

  # Vision (Sprint 21 Feature 21.6)
  ollama pull llava:7b-v1.6-mistral-q2_K        # Vision-Language Model (4.3GB VRAM)
  ```

**Total Download:** ~18GB, **VRAM Bedarf:** 6GB (RTX 3060 empfohlen)

### API Keys (Optional für Production)
- Azure OpenAI API Key (optional, falls benötigt)
- Optional: LangSmith API Key (für Monitoring)

---

## 🚀 Projekt-Setup in Claude Code

### Schritt 1: Strategische Dokumentation übertragen

Erstelle ein neues Verzeichnis und kopiere die Strategiedokumente:

```bash
mkdir aegis-rag && cd aegis-rag
mkdir docs

# Kopiere die strategischen Dokumente in das Projekt
cp /home/claude/SPRINT_PLAN.md ./docs/
cp /home/claude/CLAUDE.md ./
cp /home/claude/NAMING_CONVENTIONS.md ./docs/
cp /home/claude/ADR_INDEX.md ./docs/ADR/
cp /home/claude/SUBAGENTS.md ./docs/
cp /home/claude/TECH_STACK.md ./docs/
```

### Schritt 2: Claude Code initialisieren

```bash
# Starte Claude Code im Projektverzeichnis
claude-code .
```

### Schritt 3: Initiales Setup mit Claude Code

Im Claude Code Chat:

```
Hey Claude! Ich möchte das AegisRAG-Projekt starten basierend auf der Dokumentation in ./docs/ und CLAUDE.md.

Bitte führe folgende Schritte aus:

**Sprint 1 - Foundation Setup:**
1. Repository-Struktur erstellen (siehe CLAUDE.md)
2. pyproject.toml mit allen Dependencies (siehe TECH_STACK.md)
3. Docker Compose für Qdrant, Neo4j, Redis
4. Basic FastAPI Health-Check Endpoint
5. Pre-commit Hooks Setup
6. GitHub Actions CI Pipeline (lint, test)
7. .env.template mit allen erforderlichen Secrets

**Nutze die Subagenten optimal:**
- Infrastructure Agent: Docker & CI/CD
- Backend Agent: pyproject.toml & core structure
- API Agent: FastAPI setup
- Testing Agent: pytest configuration
- Documentation Agent: README.md

**Wichtig:**
- Folge NAMING_CONVENTIONS.md
- Berücksichtige alle ADRs
- Python 3.11+, alle Versionen aus TECH_STACK.md
```

---

## 📁 Erwartete Projekt-Struktur nach Sprint 1

```
aegis-rag/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── security.yml
├── docker/
│   ├── Dockerfile.api
│   └── docker-compose.yml
├── docs/
│   ├── ADR/
│   │   └── ADR_INDEX.md
│   ├── SPRINT_PLAN.md
│   ├── NAMING_CONVENTIONS.md
│   ├── SUBAGENTS.md
│   └── TECH_STACK.md
├── src/
│   ├── __init__.py
│   ├── agents/
│   ├── components/
│   │   ├── vector_search/
│   │   ├── graph_rag/
│   │   ├── memory/
│   │   └── mcp/
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   ├── models.py
│   │   └── exceptions.py
│   ├── api/
│   │   ├── main.py
│   │   ├── health.py
│   │   └── v1/
│   └── utils/
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/
├── .env.template
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

---

## 🔧 Lokale Entwicklung starten

### 1. Environment Setup

```bash
# Virtual Environment erstellen
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# oder: .venv\Scripts\activate  # Windows

# Dependencies installieren
pip install poetry
poetry install

# Pre-commit Hooks installieren
pre-commit install
```

### 2. Secrets konfigurieren

```bash
# .env erstellen aus Template
cp .env.template .env

# .env editieren und API Keys eintragen
nano .env
```

**Minimale .env für Sprint 21+ (Ollama + Docling):**
```bash
# LLM Configuration (Ollama by default)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_GENERATION=llama3.2:8b
OLLAMA_MODEL_QUERY=llama3.2:3b
OLLAMA_MAX_LOADED_MODELS=1  # Sprint 19: Sequential model loading for 6GB VRAM

# Embeddings (Sprint 16: BGE-M3 Migration, ADR-024)
OLLAMA_MODEL_EMBEDDING=bge-m3  # 1024-dim multilingual embeddings

# Entity/Relation Extraction (Sprint 13, ADR-018)
EXTRACTION_LLM_MODEL=hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q8_0

# Extraction Pipeline (Sprint 21, ADR-026)
EXTRACTION_PIPELINE=llm_extraction  # Options: llm_extraction, three_phase, lightrag_default

# Docling Container (Sprint 21, ADR-027)
DOCLING_ENABLED=true
DOCLING_BASE_URL=http://localhost:8080
DOCLING_DEVICE=cuda  # Options: cuda, cpu
DOCLING_MAX_FILE_SIZE=100000000  # 100MB

# Optional: Azure OpenAI (nur falls benötigt)
# USE_AZURE_LLM=false
# AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
# AZURE_OPENAI_API_KEY=your-key
# AZURE_OPENAI_MODEL=gpt-4o

# Databases (Docker defaults)
QDRANT_HOST=localhost
QDRANT_PORT=6333

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme

REDIS_HOST=localhost
REDIS_PORT=6379

# Optional: LangSmith Monitoring
LANGSMITH_API_KEY=<optional>
LANGSMITH_PROJECT=aegis-rag
```

### 3. Docker Services starten

```bash
# Alle Services starten (inkl. Docling Container, Sprint 21)
docker compose up -d

# Services prüfen
docker compose ps

# Logs anschauen
docker compose logs -f

# Einzelne Services:
# Qdrant Dashboard: http://localhost:6333/dashboard
# Neo4j Browser: http://localhost:7474
# Redis: redis-cli -h localhost -p 6379
# Docling API: http://localhost:8080/health (Sprint 21+)

# GPU-Status prüfen (Docling Container)
docker exec aegis-docling nvidia-smi
```

**Sprint 21 Hinweis - Docling Container:**
- Startet automatisch mit `docker compose up -d`
- Benötigt **6GB VRAM** (RTX 3060 oder besser)
- **Container-Lifecycle**: Wird von LangGraph Pipeline gestartet/gestoppt (ADR-027)
- **Healthcheck**: `curl http://localhost:8080/health`
- **GPU-Modus**: Wenn `DOCLING_DEVICE=cuda` in `.env`
- **CPU-Fallback**: Wenn GPU nicht verfügbar, läuft automatisch auf CPU (langsamer)

### 4. API Server starten

```bash
# Development Server mit Hot Reload
uvicorn src.api.main:app --reload --port 8000

# API testen
curl http://localhost:8000/health

# OpenAPI Docs
open http://localhost:8000/docs
```

### 5. Tests ausführen

```bash
# Alle Tests
pytest

# Mit Coverage
pytest --cov=src --cov-report=html

# Nur Unit Tests
pytest tests/unit/

# Spezifischer Test
pytest tests/unit/agents/test_coordinator.py -v
```

---

## 📊 Entwicklungs-Workflow

### Feature Development mit Claude Code

```
1. Sprint Planning: Checke SPRINT_PLAN.md für aktuelle Ziele
2. Task Assignment: Delegiere an Subagenten (siehe SUBAGENTS.md)
3. Development: Claude Code implementiert
4. Testing: Testing Agent schreibt Tests
5. Review: Code Quality Gates prüfen
6. Commit: Conventional Commits (siehe NAMING_CONVENTIONS.md)
7. Deploy: CI/CD Pipeline automatisch
```

### Beispiel: Sprint 2 Task

**Im Claude Code Chat:**
```
Wir starten jetzt Sprint 2: Component 1 - Vector Search Foundation.

**Backend Agent:** 
Implementiere den Qdrant Client Wrapper mit:
- Connection Pooling
- Async I/O
- Error Handling mit Retry Logic
- Health Check Method
Siehe: docs/TECH_STACK.md für Qdrant Version

**Infrastructure Agent:**
Erweitere docker-compose.yml mit:
- Qdrant Service (v1.11.0)
- Persistent Volume
- Health Check
- Resource Limits

**Testing Agent:**
Schreibe Unit Tests für Qdrant Client:
- Test Connection
- Test Search (mocked)
- Test Error Handling
- Coverage >80%

Referenz: CLAUDE.md Sektion "Qdrant Integration"
```

---

## 🐛 Troubleshooting

### Docker Services starten nicht

```bash
# Ports prüfen
netstat -tulpn | grep -E '6333|6379|7474|7687|8080'

# Docker Logs prüfen
docker compose logs qdrant
docker compose logs neo4j
docker compose logs redis
docker compose logs docling  # Sprint 21+

# Services neustarten
docker compose down
docker compose up -d
```

### GPU/CUDA Probleme (Sprint 21+)

**Docling Container startet nicht:**

```powershell
# 1. GPU-Verfügbarkeit prüfen
nvidia-smi

# 2. NVIDIA Container Toolkit prüfen (WSL2)
wsl
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
exit

# 3. Docling Container Logs prüfen
docker compose logs docling

# 4. CPU-Fallback aktivieren (falls GPU-Probleme)
# .env ändern:
# DOCLING_DEVICE=cpu
docker compose restart docling

# 5. Container-Berechtigungen prüfen
docker compose exec docling ls -la /workspace
```

**VRAM-Probleme (Out of Memory):**

```powershell
# 1. VRAM-Nutzung prüfen
nvidia-smi

# 2. Ollama-Models reduzieren (nur 1 Model gleichzeitig laden)
# .env anpassen:
# OLLAMA_MAX_LOADED_MODELS=1

# 3. Docling Container stoppen wenn nicht benötigt
docker compose stop docling

# 4. Kleinere Vision-Models verwenden
ollama pull llava:7b-v1.6-mistral-q2_K  # Statt größerer Varianten
```

**Performance-Probleme (langsames OCR):**

```powershell
# 1. GPU-Auslastung prüfen
docker exec aegis-docling nvidia-smi

# 2. GPU-Mode verifizieren
curl http://localhost:8080/health | jq '.device'  # Sollte "cuda" sein

# 3. CUDA-Version prüfen
docker exec aegis-docling nvcc --version  # Sollte 12.4+ sein

# 4. Falls CPU-Mode: Batch-Processing verwenden
# Große PDFs in kleinere Teile splitten
```

### Import Errors

```bash
# Python Path prüfen
python -c "import sys; print(sys.path)"

# Neu installieren
poetry install --no-cache

# Oder mit pip
pip install -e .
```

### Tests schlagen fehl

```bash
# Pytest Cache löschen
pytest --cache-clear

# Nur failed Tests wiederholen
pytest --lf

# Verbose Output
pytest -vv -s
```

### Pre-commit Hooks schlagen fehl

```bash
# Manuell ausführen
pre-commit run --all-files

# Bestimmten Hook skippen (nur für Notfälle)
SKIP=mypy git commit -m "message"

# Hooks aktualisieren
pre-commit autoupdate
```

---

## 📈 Progress Tracking

### Sprint 1 Checkliste

- [ ] Repository-Struktur erstellt
- [ ] pyproject.toml konfiguriert
- [ ] Docker Compose funktional (`docker compose up`)
- [ ] Health-Check Endpoint (`/health` returns 200)
- [ ] Pre-commit Hooks installiert
- [ ] CI Pipeline grün
- [ ] .env.template erstellt
- [ ] README.md mit Setup Instructions
- [ ] Alle Team-Mitglieder können lokal entwickeln

### Definition of Done (Sprint 1)

```bash
# Alle Tests laufen durch
pytest
# ✅ Passed

# Linting erfolgreich
ruff check src/
# ✅ No errors

# Type Checking erfolgreich
mypy src/
# ✅ Success

# Docker Services healthy
docker compose ps
# ✅ All services healthy

# CI Pipeline grün
# ✅ Check GitHub Actions
```

---

## 🔄 Nächste Schritte nach Sprint 1

1. **Sprint 2 vorbereiten:**
   - Test-Dokumente für Vector Search sammeln (PDF, TXT, MD)
   - Ollama Models pullen (llama3.2:3b, llama3.2:8b, nomic-embed-text)
   - Qdrant Collection Schema designen

2. **Team Onboarding:**
   - Alle Entwickler durch Setup führen
   - CLAUDE.md durcharbeiten
   - Claude Code Training

3. **Sprint 2 starten:**
   - Vector Search Foundation implementieren
   - Siehe SPRINT_PLAN.md für Details

---

## 📚 Wichtige Ressourcen

### Interne Dokumentation
- `CLAUDE.md` - Projekt Context für Claude Code
- `docs/SPRINT_PLAN.md` - 10-Sprint Roadmap
- `docs/NAMING_CONVENTIONS.md` - Code Standards
- `docs/ADR_INDEX.md` - Architektur-Entscheidungen
- `docs/SUBAGENTS.md` - Subagent Delegation
- `docs/TECH_STACK.md` - Technology Choices

### Externe Ressourcen
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [LlamaIndex Docs](https://docs.llamaindex.ai/)
- [Qdrant Docs](https://qdrant.tech/documentation/)
- [Neo4j Cypher](https://neo4j.com/docs/cypher-manual/)
- [FastAPI Docs](https://fastapi.tiangolo.com/)

### Community
- LangChain Discord
- LlamaIndex Discord
- AegisRAG GitHub Discussions (create after repo setup)

---

## 💡 Pro Tips für Claude Code

### Effektive Delegation

**Gut:**
```
Backend Agent: Implementiere Hybrid Search mit den Requirements aus TECH_STACK.md.
Nutze Reciprocal Rank Fusion (siehe ADR-008).
Target: <200ms Latency, >80% Test Coverage.
```

**Schlecht:**
```
Mach mal Hybrid Search fertig.
```

### Kontext bereitstellen

Claude Code arbeitet besser mit explizitem Kontext:
```
Kontext: Sprint 2, Tag 3
Ziel: Hybrid Search MVP
Abhängigkeiten: Qdrant Client (bereits implementiert)
Referenz: docs/TECH_STACK.md, Section "Qdrant"
```

### Iteratives Vorgehen

Statt:
```
Implementiere das gesamte RAG-System
```

Besser:
```
1. Qdrant Client Wrapper (heute)
2. Document Ingestion (morgen)
3. Hybrid Search (übermorgen)
```

### Feedback geben

Nach jedem Task:
```
✅ Gut: Fehlerbehandlung, Type Hints, Tests
⚠️ Improve: Docstrings fehlen noch
📝 Next: API Endpoint für Search
```

---

## ✅ Sprint 1 Completion Criteria

**Vor dem Merge zu `main`:**
- [ ] Alle Tests grün
- [ ] CI Pipeline erfolgreich
- [ ] Code Review abgeschlossen
- [ ] Documentation vollständig
- [ ] Demo erfolgreich (`docker compose up` → `/health` → 200 OK)
- [ ] Team Sign-Off

**Dann:**
```bash
git checkout main
git merge develop
git tag v0.1.0
git push origin main --tags
```

---

Viel Erfolg beim Projekt! 🚀

Bei Fragen: Checke CLAUDE.md oder frage Claude Code nach spezifischen Implementierungs-Details.
