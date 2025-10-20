# ChatGPT_Tests – End-to-End (E2E) Tests

Diese Suite führt echte E2E-Tests ohne Mocks gegen die laufenden Services aus (Ollama, Qdrant, Neo4j, Redis, FastAPI API). Sie verwendet echte Daten aus `data/sample_documents` und ruft die REST-API auf.

- Services: via `docker-compose.yml` (Ollama, Qdrant, Neo4j, Redis)
- API: `uvicorn src.api.main:app` auf `http://localhost:8000`
- Daten: `data/sample_documents/`

Voraussetzungen
- Docker + Docker Compose
- Python 3.11+

Schnellstart
1) `pwsh ChatGPT_Tests/run_e2e.ps1`
   - Startet Services, lädt Ollama-Modelle, startet API, indiziert Dokumente und führt Tests aus

Inhalte
- `test_e2e_retrieval.py` – Auth, Ingestion, Stats, BM25 vorbereiten, Suche (vector/bm25/hybrid)
- `test_e2e_graph.py` – LightRAG-Dokumenteinfügung in Neo4j und Graph-Analytics/Visualisierung-Endpunkte

Hinweise
- Auth ist standardmäßig aktiv; der Test bezieht das Token über `/api/v1/retrieval/auth/token` mit User `admin` und Passwort aus `Settings.api_admin_password` (Default `admin123`).
- Die Tests benutzen echte Ollama-Modelle. Das Skript `run_e2e.ps1` lädt die benötigten Modelle via `scripts/setup_ollama_models.ps1`.
