# 🚀 AegisRAG Quick Start Guide

Sprint 15: React Frontend mit Perplexity-Style UI

---

## 📋 Voraussetzungen

✅ Python 3.12+ (mit Poetry)
✅ Node.js 20+ (mit npm)
✅ Git

---

## 🎯 Einfachster Start (2 Terminals)

### Terminal 1: Backend starten

```powershell
# Im Hauptverzeichnis
cd "C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag"

# PowerShell Script ausführen
.\start-backend.ps1
```

**Oder manuell:**
```powershell
poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend läuft auf: **http://localhost:8000**

---

### Terminal 2: Frontend starten

```powershell
# Im Hauptverzeichnis
cd "C:\Users\Klaus Pommer\OneDrive - Pommer IT-Consulting GmbH\99_Studium_Klaus\AEGIS_Rag"

# PowerShell Script ausführen
.\start-frontend.ps1
```

**Oder manuell:**
```powershell
cd frontend
npm install  # Nur beim ersten Mal
npm run dev
```

✅ Frontend läuft auf: **http://localhost:5173**

---

## 🌐 Oberfläche öffnen

Öffne deinen Browser:

**Hauptseite:** http://localhost:5173

### Verfügbare Seiten:

1. **Homepage** (`/`)
   - Großes Suchfeld
   - Mode-Chips (Hybrid, Vector, Graph, Memory)
   - Quick-Prompts

2. **Search Results** (`/search?q=...`)
   - Streaming-Antwort (Token für Token)
   - Source Cards
   - Metadaten

3. **Health Dashboard** (`/health`)
   - System-Status
   - Dependency-Monitoring
   - Performance-Metriken

---

## 🧪 Test die Oberfläche

### Schritt 1: Suche starten
1. Gib eine Frage ein: **"Was ist RAG?"**
2. Wähle einen Mode: **Hybrid** (Standard)
3. Drücke **Enter** oder klicke auf ➡️
4. Sieh zu, wie die Antwort streamt!

### Schritt 2: History Sidebar
1. Klicke auf **☰** (Hamburger-Menü)
2. Sieh alle Konversationen
3. Klicke auf eine Session zum Laden

### Schritt 3: Health Dashboard
1. Navigiere zu: http://localhost:5173/health
2. Sieh System-Status und Dependency-Health

---

## 🐛 Troubleshooting

### Problem: "poetry: command not found"
```powershell
# Installiere Poetry
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

### Problem: "npm: command not found"
Installiere Node.js von: https://nodejs.org/

### Problem: Backend startet nicht
```powershell
# Installiere Dependencies
poetry install

# Dann starten
poetry run uvicorn src.api.main:app --reload --port 8000
```

### Problem: Frontend startet nicht
```powershell
cd frontend
npm install
npm run dev
```

### Problem: "Connection refused" im Frontend
1. Stelle sicher, dass Backend läuft (Port 8000)
2. Überprüfe `frontend/.env`:
   ```
   VITE_API_BASE_URL=http://localhost:8000
   ```

---

## 📚 Weitere Dokumentation

- **Sprint 15 Plan:** `docs/sprints/SPRINT_15_PLAN.md`
- **Completion Report:** `docs/sprints/SPRINT_15_COMPLETION_REPORT.md`
- **Test Summary:** `docs/sprints/SPRINT_15_TEST_SUMMARY.md`

---

## 🎨 Features der neuen UI

### ✅ Perplexity-Style Design
- Minimalistisches, cleanes Layout
- Fokus auf Content
- Mobile-responsive

### ✅ SSE Streaming
- Token-by-token Antworten
- Real-time Updates
- Wie Perplexity.ai

### ✅ Mode Selector
- **Hybrid:** Vector + Graph + BM25
- **Vector:** Semantische Suche
- **Graph:** Entity-Beziehungen
- **Memory:** Conversation History

### ✅ Source Cards
- Horizontal Scroll
- Metadaten & Scores
- Entity Tags

### ✅ Session Management
- Automatisches Speichern
- History Sidebar
- Datum-Gruppierung

### ✅ Health Monitoring
- Real-time Status
- Dependency Cards
- Auto-refresh

---

## 🚀 Optional: Volle Backend-Services starten

Für vollständige Funktionalität (Qdrant, Neo4j, Redis, Ollama):

```powershell
docker-compose up -d
```

Dies startet:
- ✅ Qdrant (Vector DB) - Port 6333
- ✅ Neo4j (Graph DB) - Port 7474/7687
- ✅ Redis (Memory Cache) - Port 6379
- ✅ Ollama (LLM) - Port 11434

---

## 📞 Support

Bei Problemen:
1. Überprüfe dass beide Terminals laufen
2. Schaue in die Logs für Fehlermeldungen
3. Stelle sicher, dass Ports 8000 und 5173 frei sind

---

**Viel Erfolg! 🎉**
