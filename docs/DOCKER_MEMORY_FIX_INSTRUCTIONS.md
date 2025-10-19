# Docker Desktop Memory Fix - Schritt-für-Schritt Anleitung

**Problem:** LightRAG Tests schlagen fehl wegen zu wenig Speicher (7.63 GB → benötigt 12 GB)

**Fehler:**
```
ERROR: model requires more system memory (5.2 GiB) than is available (5.1 GiB)
```

---

## Lösung: Docker Desktop Memory erhöhen

### Schritt 1: Docker Desktop öffnen

- Klicken Sie auf das **Docker Desktop Symbol** in der Windows Taskleiste
- Oder starten Sie Docker Desktop über das Startmenü

### Schritt 2: Settings öffnen

- Klicken Sie oben rechts auf das **Zahnrad-Symbol ⚙️** (Settings)

### Schritt 3: Resources → Advanced

- Navigieren Sie im linken Menü zu **Resources**
- Klicken Sie auf **Advanced**

### Schritt 4: Memory erhöhen

- Sie sehen einen Slider für **Memory**
- **Aktueller Wert:** 7.63 GB (oder 8 GB)
- **Neuer Wert:** Schieben Sie den Slider auf **12 GB**

### Schritt 5: Apply & Restart

- Klicken Sie unten rechts auf **"Apply & Restart"**
- Docker Desktop wird neu gestartet
- **Warten Sie ~2 Minuten** bis der Neustart abgeschlossen ist

---

## Überprüfung

Nach dem Neustart können Sie die Änderung überprüfen:

```powershell
docker info | findstr "Total Memory"
```

**Erwartetes Ergebnis:**
```
Total Memory: 12 GiB
```

---

## Nach der Memory-Erhöhung

### Sprint 5 Tests erneut ausführen

Sobald Docker neu gestartet ist, führen Sie die fehlgeschlagenen LightRAG Tests aus:

```bash
poetry run pytest tests/integration/test_sprint5_critical_e2e.py::test_graph_construction_full_pipeline_e2e -v
poetry run pytest tests/integration/test_sprint5_critical_e2e.py::test_local_search_entity_level_e2e -v
poetry run pytest tests/integration/test_sprint5_critical_e2e.py::test_global_search_topic_level_e2e -v
poetry run pytest tests/integration/test_sprint5_critical_e2e.py::test_hybrid_search_local_global_e2e -v
```

**Oder alle Sprint 5 Tests:**
```bash
poetry run pytest tests/integration/test_sprint5_critical_e2e.py -v
```

### Erwartetes Ergebnis

**Vorher:**
- 4/15 PASSED (27% Pass Rate)
- 4 Tests schlugen fehl mit "0 entities extracted"

**Nachher:**
- 8/15 PASSED (53% Pass Rate)
- Alle 4 LightRAG Tests sollten PASSEN ✅

---

## Warum 12 GB?

| Komponente | Speicher |
|-----------|----------|
| Docker Overhead | ~2 GB |
| Ollama Service | ~500 MB |
| Neo4j Database | ~1 GB |
| **LightRAG (4 parallel workers)** | **5.2 GB** |
| Qdrant Vector DB | ~500 MB |
| Test Runner | ~500 MB |
| **Gesamt (Peak)** | **~10 GB** |

**12 GB = 20% Buffer** für Sicherheit

---

## Alternativen (falls 12 GB nicht möglich)

### Option 1: LightRAG Worker reduzieren
Wenn Ihr System nicht 12 GB für Docker bereitstellen kann, können wir die Anzahl der LightRAG parallel workers reduzieren:

```python
# In LightRAG Konfiguration (falls möglich)
max_workers=2  # Statt default 4
```

**Memory-Bedarf dann:** ~3 GB statt 5.2 GB

### Option 2: Externe Ollama Installation
Ollama außerhalb von Docker laufen lassen:

```bash
# Ollama nativ auf Windows installieren (nicht in Docker)
# Dann kann Ollama den vollen System-RAM nutzen (16.5 GB)
```

**Effort:** MEDIUM (Reconfiguration nötig)

---

## Support

Bei Problemen:
1. Prüfen Sie, dass Docker Desktop läuft
2. Prüfen Sie die Memory-Einstellung: `docker info`
3. Restart Docker Desktop manuell falls nötig
4. Bei persistent Errors: Kontaktieren Sie Klaus Pommer

---

**Erstellt:** 2025-10-19
**Sprint:** Sprint 8 E2E Testing
**Priorität:** CRITICAL (P0)
