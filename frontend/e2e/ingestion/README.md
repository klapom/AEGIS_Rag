# Single Document Upload & Verification Test

## Überblick

Dieser E2E Test prüft den **kompletten Dokumenten-Ingestion und Retrieval-Flow** für ein einzelnes OMNITRACKER-Dokument.

**Test-Dokument:** `D3_CDays2025-OMNITRACKER-13.0.0-GenericAPI.pdf` (1.9MB)

**Coverage:**
- ✅ Admin UI Upload
- ✅ Docling Parsing (GPU-accelerated)
- ✅ Section-Aware Chunking
- ✅ BGE-M3 Embeddings (GPU)
- ✅ Qdrant Indexing
- ✅ Vector Search (BGE-M3)
- ✅ BM25 Keyword Search
- ✅ Graph Reasoning (LightRAG)
- ✅ Hybrid Retrieval (RRF Fusion)

---

## Test-Struktur

### Test 1: Document Upload & Ingestion
**Dauer:** ~2-5 Minuten
**Prüft:**
1. Admin UI File-Upload funktioniert
2. Ingestion Pipeline läuft durch alle Stages
3. Redirect zum Chat mit vorbefüllter Query
4. Keine Fehler im Ingestion-Prozess

### Tests 2-11: Content Verification (10 Fragen)
**Dauer:** ~10-15 Minuten (10 Fragen × ~1 Minute)
**Prüft:**
- Jede Frage testet einen spezifischen Retrieval-Aspekt
- Keyword-Matching zur Validierung der Antwort-Qualität
- Source-Attribution (richtige Dokument-Referenz)
- Intent-Classification (VECTOR/BM25/GRAPH/HYBRID)

### Test 12: Comprehensive Quality Check
**Dauer:** ~20 Minuten (alle 10 Fragen sequenziell)
**Prüft:**
- **Konsistente Retrieval-Qualität** über alle Fragen
- **Success Rate >= 80%** (mind. 8/10 Fragen korrekt)
- Keine "not enough information" Antworten

---

## Test-Fragen Breakdown

| ID | Frage | Retrieval | Keywords (min 2/5) | Zweck |
|----|-------|-----------|-------------------|-------|
| **Q1** | Was ist die OMNITRACKER GenericAPI? | VECTOR | genericapi, api, schnittstelle, rest, omnitracker | Definition |
| **Q2** | Welche HTTP-Methoden werden unterstützt? | BM25 | get, post, put, delete, patch (min 3/5) | Enumeration |
| **Q3** | Wie erfolgt die Authentifizierung? | HYBRID | authentifizierung, token, oauth, bearer, api key | How-to |
| **Q4** | Beziehung zu Application Server? | GRAPH | application server, schnittstelle, verbindung | Relationship |
| **Q5** | Neue Features in Version 13.0.0? | VECTOR | 13.0.0, version, neu, feature | Version-specific |
| **Q6** | Welche Endpoints gibt es? | BM25 | endpoint, url, pfad, route, /api/ | List |
| **Q7** | Welche Datenformate werden akzeptiert? | BM25 | json, xml, csv, format | Specification |
| **Q8** | Unterschied zu anderen APIs? | GRAPH | unterschied, vergleich, andere, api | Comparison |
| **Q9** | Welche Use Cases? | HYBRID | use case, anwendungsfall, beispiel | Use case |
| **Q10** | Welche Fehlerbehandlung? | VECTOR | fehler, error, exception, status code | Implementation |

### Retrieval-Methoden Coverage
- **VECTOR (BGE-M3):** Q1, Q5, Q10 (3 Fragen)
- **BM25 Keyword:** Q2, Q6, Q7 (3 Fragen)
- **GRAPH (LightRAG):** Q4, Q8 (2 Fragen)
- **HYBRID (RRF Fusion):** Q3, Q9 (2 Fragen)

---

## Test ausführen

### Voraussetzungen

1. **Alle Container müssen laufen:**
```bash
docker compose -f docker-compose.dgx-spark.yml up -d

# Verify services
docker ps | grep -E "(aegis-api|docling|qdrant|neo4j|redis|ollama)"
```

2. **Vite Dev Server muss laufen:**
```bash
cd frontend
npm run dev
# Should show: http://localhost:5179
```

3. **Test-Dokument muss existieren:**
```bash
ls -lh data/omnitracker/D3_CDays2025-OMNITRACKER-13.0.0-GenericAPI.pdf
# Should show: 1.9M
```

### Test-Ausführung

**Option 1: Nur Upload-Test (schnell, ~5 min)**
```bash
cd frontend
npx playwright test e2e/ingestion/single-document-test.spec.ts -g "should upload document"
```

**Option 2: Einzelne Frage testen**
```bash
# Test nur Q1
npx playwright test e2e/ingestion/single-document-test.spec.ts -g "Q1:"

# Test nur Q4 (Graph)
npx playwright test e2e/ingestion/single-document-test.spec.ts -g "Q4:"
```

**Option 3: Alle 10 Content-Tests (mittel, ~15 min)**
```bash
npx playwright test e2e/ingestion/single-document-test.spec.ts -g "Q[0-9]+:"
```

**Option 4: Comprehensive Test (lang, ~20 min)**
```bash
npx playwright test e2e/ingestion/single-document-test.spec.ts -g "comprehensive"
```

**Option 5: Alle Tests (vollständig, ~25 min)**
```bash
npx playwright test e2e/ingestion/single-document-test.spec.ts
```

### Test-Output

**Erfolgreicher Test:**
```
✅ Selected document: D3_CDays2025-OMNITRACKER-13.0.0-GenericAPI.pdf
🔄 Upload started, waiting for ingestion to complete...
  ✓ Stage: Upload
  ✓ Stage: Parsing
  ✓ Stage: Chunking
  ✓ Stage: Embedding
  ✓ Stage: Indexing
  ✓ Stage: Complete
✅ Ingestion complete!
✅ Redirected to chat page with pre-filled query

📝 Testing Q1: Was ist die OMNITRACKER GenericAPI?
   Expected Retrieval: VECTOR
   ✓ Response received (342 characters)
   ✓ Found keywords (3/5): genericapi, api, schnittstelle
   ℹ️  Detected Intent: VECTOR (Faktenbezogen)
   ✓ Source verified: D3_CDays2025-OMNITRACKER-13.0.0-GenericAPI.pdf
✅ Q1 PASSED

...

📊 Test Results Summary:
   Passed: 9/10
   Success Rate: 90.0%
   ✅ Q1: 3/5 keywords
   ✅ Q2: 4/5 keywords
   ✅ Q3: 3/6 keywords
   ✅ Q4: 2/5 keywords
   ❌ Q5: 1/6 keywords (FAILED - expected 2)
   ✅ Q6: 3/5 keywords
   ✅ Q7: 2/5 keywords
   ✅ Q8: 3/6 keywords
   ✅ Q9: 3/5 keywords
   ✅ Q10: 4/7 keywords

✅ Overall Success: 90.0% (>= 80% required)
```

---

## Fehlerbehebung

### Problem: Upload schlägt fehl

**Symptom:** "Upload & Ingest" Button bleibt disabled oder Fehler bei File-Upload

**Lösungen:**
1. Prüfe, ob Docling Container läuft:
```bash
docker ps | grep docling
docker logs docling --tail 50
```

2. Prüfe, ob Datei existiert:
```bash
ls -lh data/omnitracker/D3_CDays2025-OMNITRACKER-13.0.0-GenericAPI.pdf
```

3. Prüfe Admin UI Logs:
```bash
# Browser DevTools Console (F12)
# Sollte keine 500 Errors zeigen
```

### Problem: Ingestion hängt bei "Parsing"

**Symptom:** Test timeout nach 5 Minuten bei "Parsing" Stage

**Lösungen:**
1. Prüfe Docling Container Logs:
```bash
docker logs docling --tail 100
# Sollte keine OCR Errors zeigen
```

2. GPU-Acceleration prüfen:
```bash
docker exec docling nvidia-smi
# Sollte GPU usage zeigen
```

3. Fallback: Neustart Docling Container:
```bash
docker compose -f docker-compose.dgx-spark.yml restart docling
```

### Problem: Fragen liefern "not enough information"

**Symptom:** Alle/viele Fragen scheitern mit "I don't have enough information"

**Lösungen:**
1. **Prüfe, ob Dokument in Qdrant ist:**
```bash
curl -s http://localhost:6333/collections/documents_v1 | jq '.result.points_count'
# Sollte >44 sein (vorher nur 44, jetzt mit GenericAPI ~100)
```

2. **Prüfe Namespace:**
```bash
# Suche nach "GenericAPI" in Qdrant
curl -X POST http://localhost:6333/collections/documents_v1/points/scroll \
  -H "Content-Type: application/json" \
  -d '{"limit": 10, "with_payload": true, "filter": {"must": [{"key": "metadata.source", "match": {"text": "GenericAPI"}}]}}' \
  | jq '.result.points | length'
# Sollte >0 sein
```

3. **Embedding-Model prüfen:**
```bash
docker exec aegis-api python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('BAAI/bge-m3')
print(f'Device: {model.device}')
"
# Sollte "cuda" sein, nicht "cpu"
```

### Problem: Keywords werden nicht gefunden

**Symptom:** Test scheitert mit "Expected >= 2 keywords, found 1"

**Mögliche Ursachen:**
1. **Dokument-Content passt nicht zu Fragen**
   - GenericAPI-Dokument enthält möglicherweise nicht alle erwarteten Keywords
   - **Lösung:** Keywords in Test anpassen basierend auf tatsächlichem Content

2. **LLM paraphrasiert zu stark**
   - LLM verwendet Synonyme statt exakter Keywords
   - **Lösung:** Erweitere `expectedKeywords` um Synonyme

3. **Retrieval-Qualität niedrig**
   - Relevante Chunks werden nicht gefunden
   - **Lösung:** Prüfe Chunking-Strategie, erhöhe `top_k` Parameter

### Problem: Intent-Classification falsch

**Symptom:** Test erwartet "GRAPH", bekommt aber "VECTOR"

**Erklärung:** Intent-Classification ist **nicht deterministisch**. LLM kann Fragen unterschiedlich klassifizieren.

**Lösung:** Intent-Checks sind **nur informativ**, nicht Teil der Assertions (außer bei sehr eindeutigen Fragen)

---

## Test-Metriken

### Erfolgs-Kriterien

**Upload & Ingestion:**
- ✅ Ingestion in <5 Minuten
- ✅ Alle Stages erfolgreich (Upload → Complete)
- ✅ Redirect zum Chat funktioniert

**Content Verification (pro Frage):**
- ✅ Response > 50 Zeichen
- ✅ Keine "not enough information" Fehlermeldung
- ✅ Mindestens `minKeywords` gefunden (meist 2/5)
- ✅ Source-Attribution korrekt

**Overall Quality:**
- ✅ **Success Rate >= 80%** (mind. 8/10 Fragen)
- ✅ Konsistente Antwortqualität

### Performance-Benchmarks

**Ingestion (1.9MB PDF):**
- Upload: <10s
- Parsing (Docling GPU): 30-60s
- Chunking: 10-20s
- Embedding (BGE-M3 GPU): 20-40s (~50 chunks)
- Indexing (Qdrant): <10s
- **Total: 2-3 Minuten**

**Retrieval (pro Frage):**
- Vector Search: 50-200ms (GPU)
- BM25 Search: 20-100ms
- Graph Reasoning: 500-1500ms (LightRAG)
- LLM Generation: 2-5s (qwen3:32b)
- **Total: 3-7s pro Frage**

---

## Test-Erweiterungen

### Weitere Test-Dokumente hinzufügen

Um mehrere Dokumente zu testen, erstelle ähnliche Test-Dateien:

```typescript
// single-document-test-omnilytics.spec.ts
const TEST_DOCUMENT = {
  filename: 'B4_CDays25_OMNILYTICS-Designed-Simplicity.pdf',
  // ... angepasste Fragen für OMNILYTICS
};
```

### Custom Keywords pro Dokument

Passe `expectedKeywords` basierend auf tatsächlichem Dokument-Content an:

```typescript
// Nach Upload einmal manuell testen:
// 1. Dokument hochladen
// 2. Jede Frage stellen
// 3. Response analysieren
// 4. Häufigste Keywords extrahieren
// 5. Test-Keywords aktualisieren
```

### Integration in CI/CD

```yaml
# .github/workflows/e2e-ingestion.yml
name: E2E Ingestion Tests

on:
  pull_request:
    paths:
      - 'src/domains/document_processing/**'
      - 'src/domains/vector_search/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Start services
        run: docker compose up -d
      - name: Run ingestion test
        run: |
          cd frontend
          npm ci
          npx playwright test e2e/ingestion/single-document-test.spec.ts
```

---

## Zusammenfassung

Dieser Test bietet **1:1 Inhaltsprüfung** für einzelne Dokumente durch:

1. ✅ **Isolierte Ingestion:** Nur 1 Dokument, keine anderen Daten
2. ✅ **Spezifische Fragen:** 10 gezielte Fragen zum Dokument-Content
3. ✅ **Keyword-Validierung:** Automatische Qualitätsprüfung
4. ✅ **Multi-Method Coverage:** Vector, BM25, Graph, Hybrid
5. ✅ **Reproduzierbar:** Jeder Lauf sollte identische Ergebnisse liefern

**Sprint 66 Ziel:** Dieser Test muss **10/10 Fragen korrekt beantworten** (100% Success Rate)

---

**Erstellt:** Sprint 66, Feature 66.4 - Single Document Upload User Journey
**Test-Dokument:** D3_CDays2025-OMNITRACKER-13.0.0-GenericAPI.pdf (1.9MB)
**Erwartete Ingestion-Zeit:** 2-3 Minuten
**Erwartete Test-Zeit:** 15-25 Minuten (abhängig von Test-Scope)
