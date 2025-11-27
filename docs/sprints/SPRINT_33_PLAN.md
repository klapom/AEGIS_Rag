# Sprint 33: Enhanced Directory Indexing & Live Progress Visualization

**Sprint Duration:** TBD
**Branch:** `sprint-33-directory-indexing`
**Status:** PLANNED

---

## Objective

Verbesserung der Admin-Indizierung mit Verzeichnisauswahl, Dateivorschau, detaillierter Echtzeit-Fortschrittsanzeige, paralleler Verarbeitung und persistentem Logging.

---

## Features Overview

| # | Feature | Story Points | Priority |
|---|---------|--------------|----------|
| 33.1 | Verzeichnisauswahl-Dialog | 5 SP | P0 |
| 33.2 | Dateilisten mit Farbkodierung | 5 SP | P0 |
| 33.3 | Live-Fortschrittsanzeige (Kompakt) | 5 SP | P0 |
| 33.4 | Detail-Dialog (Seite, VLM, Chunks, Pipeline, Entities) | 13 SP | P1 |
| 33.5 | Error-Tracking mit Button | 5 SP | P1 |
| 33.6 | Live-Log Stream | 8 SP | P2 |
| 33.7 | Persistente Logging-Datenbank + API | 13 SP | P1 |
| 33.8 | Parallele Dateiverarbeitung | 8 SP | P1 |
| **Gesamt** | | **62 SP** | |

---

## Feature 33.1: Verzeichnisauswahl-Dialog (5 SP)

### Beschreibung
Auswahldialog für lokale Verzeichnisse mit Option für rekursive Suche.

### Anforderungen
- [ ] Pfad-Eingabefeld für Verzeichnispfad
- [ ] Browse-Button zum Öffnen eines Verzeichnis-Dialogs
- [ ] Checkbox: "Rekursiv durchsuchen" (Unterverzeichnisse einbeziehen)
- [ ] Validierung: Prüfen ob Pfad existiert und lesbar ist
- [ ] Backend-Endpoint: `POST /api/v1/admin/indexing/scan-directory`

### Technische Details
```typescript
// Frontend: DirectorySelector.tsx
interface DirectorySelectorProps {
  onDirectorySelected: (path: string, recursive: boolean) => void;
}

// Backend Request
interface ScanDirectoryRequest {
  path: string;
  recursive: boolean;
}

// Backend Response
interface ScanDirectoryResponse {
  path: string;
  recursive: boolean;
  files: FileInfo[];
  statistics: {
    total: number;
    docling_supported: number;
    llamaindex_supported: number;
    unsupported: number;
  };
}
```

### Acceptance Criteria
- [ ] Verzeichnispfad kann eingegeben werden
- [ ] Rekursiv-Option funktioniert
- [ ] Ungültige Pfade werden mit Fehlermeldung abgelehnt

---

## Feature 33.2: Dateilisten mit Farbkodierung (5 SP)

### Beschreibung
Nach Verzeichnisauswahl: Anzeige aller gefundenen Dateien mit Farbkodierung nach Unterstützungsstatus.

### Farbschema
| Farbe | CSS-Klasse | Bedeutung | Dateitypen |
|-------|------------|-----------|------------|
| Dunkelgrün | `bg-green-700` | Docling (GPU-OCR, optimal) | PDF, DOCX, PPTX, XLSX, PNG, JPG |
| Hellgrün | `bg-green-400` | LlamaIndex Fallback | TXT, MD, HTML, JSON, CSV, RTF |
| Rot | `bg-red-500` | Nicht unterstützt | EXE, ZIP, MP4, etc. |

### UI-Mockup
```
┌─────────────────────────────────────────────────────────┐
│ 📁 /data/documents (rekursiv)                           │
│                                                         │
│ Statistik:                                              │
│ ├── 23 Dateien gefunden                                 │
│ ├── 15 × Docling-unterstützt (PDF, DOCX)      [█████]  │
│ ├── 6 × LlamaIndex-unterstützt (TXT, MD)      [██░░░]  │
│ └── 2 × Nicht unterstützt (wird übersprungen) [█░░░░]  │
│                                                         │
│ Dateien:                                                │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ 🟢 financial_report_2024.pdf        2.4 MB  Docling │ │
│ │ 🟢 presentation_q3.pptx             1.8 MB  Docling │ │
│ │ 🟡 readme.md                        12 KB   LlamaIx │ │
│ │ 🔴 archive.zip                      45 MB   Skip    │ │
│ └─────────────────────────────────────────────────────┘ │
│                                                         │
│ [Alle auswählen] [Keine auswählen] [Nur unterstützte]   │
│                                                         │
│ [Indizierung starten]                                   │
└─────────────────────────────────────────────────────────┘
```

### Technische Details
```typescript
// Datei-Typ-Mapping
const FILE_TYPE_CONFIG = {
  docling: {
    extensions: ['.pdf', '.docx', '.pptx', '.xlsx', '.png', '.jpg', '.jpeg'],
    color: 'bg-green-700',
    label: 'Docling'
  },
  llamaindex: {
    extensions: ['.txt', '.md', '.html', '.json', '.csv', '.rtf'],
    color: 'bg-green-400',
    label: 'LlamaIndex'
  },
  unsupported: {
    color: 'bg-red-500',
    label: 'Nicht unterstützt'
  }
};
```

### Acceptance Criteria
- [ ] Dateien werden farbkodiert angezeigt
- [ ] Statistik zeigt Anzahl pro Kategorie
- [ ] Dateien können einzeln ausgewählt/abgewählt werden

---

## Feature 33.3: Live-Fortschrittsanzeige Kompakt (5 SP)

### Beschreibung
Kompakte Fortschrittsanzeige während der Indizierung mit aktuellem Dateinamen, Seitenzahl und Gesamtfortschritt.

### UI-Mockup
```
┌─────────────────────────────────────────────────────────┐
│  📄 Verarbeite: financial_report_2024.pdf              │
│  📑 Seite: 12 / 45                                      │
│  📁 Datei: 3 / 23                                       │
│                                                         │
│  ████████████░░░░░░░░ 27%                               │
│  Geschätzte Restzeit: ~4 min 32s                        │
│                                                         │
│  [Details...] [Errors (0)] [Log] [Abbrechen]            │
└─────────────────────────────────────────────────────────┘
```

### SSE-Events vom Backend
```typescript
interface IngestionProgressEvent {
  type: 'progress';
  job_id: string;
  current_file: string;
  current_page: number;
  total_pages: number;
  files_processed: number;
  files_total: number;
  percentage: number;
  estimated_remaining_seconds: number;
}
```

### Acceptance Criteria
- [ ] Aktueller Dateiname wird angezeigt
- [ ] Seitennummer wird live aktualisiert
- [ ] Fortschrittsbalken zeigt Gesamtfortschritt
- [ ] Geschätzte Restzeit wird berechnet

---

## Feature 33.4: Detail-Dialog (13 SP)

### Beschreibung
Erweitertes Panel mit detaillierten Informationen zum aktuellen Indizierungsfortschritt.

### Bereiche

#### Bereich 1: Dokument & Seitenvorschau
- Thumbnail der aktuellen Seite (PNG aus Docling)
- Erkannte Elemente (Tabellen, Bilder, Wortanzahl)
- Parser-Info (Docling/LlamaIndex)

#### Bereich 2: VLM-Bildanalyse
- Liste aller Bilder auf der aktuellen Seite
- Thumbnail + VLM-Status für jedes Bild
- Generierte Beschreibung anzeigen
- VLM-Kosten und Statistik

#### Bereich 3: Chunk-Verarbeitung
- Aktueller Chunk-Text (Preview)
- Token-Anzahl und Section-Name
- Navigation zwischen Chunks
- VLM-Annotation-Hinweis wenn Bild enthalten

#### Bereich 4: Pipeline-Status
- Status aller Pipeline-Phasen:
  - Parsing (Docling)
  - VLM-Analyse
  - Chunking
  - Embeddings
  - BM25 Index
  - Graph (Neo4j)
- Aktuelle Operation mit Fortschritt

#### Bereich 5: Extrahierte Entitäten (Live)
- Neue Entitäten aus aktueller Seite
- Neue Relationen
- Gesamtzähler

### Acceptance Criteria
- [ ] Seitenvorschau wird als Thumbnail angezeigt
- [ ] VLM-Beschreibungen werden live angezeigt
- [ ] Chunks können durchgeblättert werden
- [ ] Pipeline-Status zeigt alle Phasen
- [ ] Entitäten werden live aktualisiert

---

## Feature 33.5: Error-Tracking mit Button (5 SP)

### Beschreibung
Error-Button in der Hauptansicht mit Anzahl der Fehler. Bei Klick öffnet sich ein Dialog mit allen Fehlern.

### Fehler-Kategorien
| Typ | Symbol | Farbe | Bedeutung |
|-----|--------|-------|-----------|
| ERROR | ❌ | Rot | Datei übersprungen |
| WARNING | ⚠️ | Orange | Problem, aber fortgesetzt |
| INFO | ℹ️ | Blau | Hinweis (z.B. Fallback) |

### UI-Mockup Error-Dialog
```
┌─ Fehler während Indizierung (3) ────────────────────────┐
│                                                         │
│  ┌─ Fehler 1 ─────────────────────────────────────────┐ │
│  │ ⚠️ WARNUNG | 14:23:45                               │ │
│  │ 📄 report_2023.pdf, Seite 7                         │ │
│  │ VLM-Timeout: Bildanalyse nach 30s abgebrochen      │ │
│  │ → Fallback: Bild ohne Beschreibung indiziert       │ │
│  └─────────────────────────────────────────────────────┘ │
│                                                         │
│  [Als CSV exportieren] [Schließen]                      │
└─────────────────────────────────────────────────────────┘
```

### Acceptance Criteria
- [ ] Error-Button zeigt Anzahl der Fehler
- [ ] Button ist rot wenn Fehler > 0, grau wenn 0
- [ ] Dialog zeigt alle Fehler mit Details
- [ ] CSV-Export funktioniert

---

## Feature 33.6: Live-Log Stream (8 SP)

### Beschreibung
Scrollbarer Log-Bereich mit allen Ereignissen der Indizierung.

### UI-Mockup
```
┌─ Indizierungs-Log ──────────────────────────────────────┐
│  [Auto-Scroll ✓] [Filter: Alle ▼] [Suche: ________]    │
│  ───────────────────────────────────────────────────── │
│  14:23:41 [INFO]  Starte Verzeichnis-Scan...           │
│  14:23:42 [INFO]  📄 report_2023.pdf - Parsing...      │
│  14:23:45 [DEBUG] VLM Response: 892 tokens, 2.1s       │
│  14:23:53 [WARN]  VLM Timeout auf Seite 7              │
│  ...                                                    │
│  ───────────────────────────────────────────────────── │
│  [Export Log] [Schließen]                               │
└─────────────────────────────────────────────────────────┘
```

### Filter-Optionen
- Level: Alle / INFO / DEBUG / WARN / ERROR
- Nach Datei filtern
- Nach Pipeline-Phase filtern

### Acceptance Criteria
- [ ] Logs werden live gestreamt
- [ ] Auto-Scroll funktioniert
- [ ] Filter funktionieren
- [ ] Log-Export als TXT/JSON

---

## Feature 33.7: Persistente Logging-Datenbank (13 SP)

### Beschreibung
SQLite-Datenbank für persistentes Tracking aller Indizierungsjobs mit API-Endpoints.

### Datenbank-Schema
```sql
CREATE TABLE ingestion_jobs (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status TEXT NOT NULL,  -- running, completed, failed, cancelled
    directory_path TEXT NOT NULL,
    recursive BOOLEAN NOT NULL,
    total_files INTEGER NOT NULL,
    processed_files INTEGER DEFAULT 0,
    total_errors INTEGER DEFAULT 0,
    total_warnings INTEGER DEFAULT 0,
    config JSON  -- Speichert Konfiguration zum Zeitpunkt des Jobs
);

CREATE TABLE ingestion_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL REFERENCES ingestion_jobs(id),
    timestamp TIMESTAMP NOT NULL,
    level TEXT NOT NULL,  -- INFO, DEBUG, WARN, ERROR
    phase TEXT,  -- parsing, vlm, chunking, embedding, bm25, graph
    file_name TEXT,
    page_number INTEGER,
    chunk_id TEXT,
    message TEXT NOT NULL,
    details JSON
);

CREATE TABLE ingestion_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL REFERENCES ingestion_jobs(id),
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size_bytes INTEGER,
    parser_used TEXT,  -- docling, llamaindex
    status TEXT NOT NULL,  -- pending, processing, completed, failed, skipped
    pages_total INTEGER,
    pages_processed INTEGER DEFAULT 0,
    chunks_created INTEGER DEFAULT 0,
    entities_extracted INTEGER DEFAULT 0,
    relations_extracted INTEGER DEFAULT 0,
    vlm_images_total INTEGER DEFAULT 0,
    vlm_images_processed INTEGER DEFAULT 0,
    processing_time_ms INTEGER,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Index für Performance
CREATE INDEX idx_events_job_id ON ingestion_events(job_id);
CREATE INDEX idx_events_level ON ingestion_events(level);
CREATE INDEX idx_files_job_id ON ingestion_files(job_id);
CREATE INDEX idx_jobs_status ON ingestion_jobs(status);
```

### API-Endpoints
```
GET  /api/v1/admin/ingestion/jobs                    -- Liste aller Jobs
GET  /api/v1/admin/ingestion/jobs/{id}               -- Job-Details
GET  /api/v1/admin/ingestion/jobs/{id}/events        -- Events für Job
GET  /api/v1/admin/ingestion/jobs/{id}/files         -- Dateien für Job
GET  /api/v1/admin/ingestion/jobs/{id}/errors        -- Nur Fehler
POST /api/v1/admin/ingestion/jobs/{id}/cancel        -- Job abbrechen
DELETE /api/v1/admin/ingestion/jobs/{id}             -- Job löschen
```

### Konfiguration
```yaml
# config/settings.yaml
ingestion:
  logging:
    retention_days: 30          # Wie lange Logs aufbewahrt werden
    max_jobs: 1000              # Maximale Anzahl gespeicherter Jobs
    cleanup_on_startup: true    # Alte Jobs beim Start bereinigen
```

### Acceptance Criteria
- [ ] SQLite-Datenbank wird erstellt
- [ ] Jobs werden persistiert
- [ ] Events werden geloggt
- [ ] API-Endpoints funktionieren
- [ ] Retention/Cleanup funktioniert per Konfiguration

---

## Feature 33.8: Parallele Dateiverarbeitung (8 SP)

### Beschreibung
Mehrere Dateien können parallel verarbeitet werden, um die Gesamtzeit zu reduzieren.

### Technische Details
```python
# Konfiguration
PARALLEL_FILES = 3  # Anzahl parallel verarbeiteter Dateien
PARALLEL_CHUNKS = 10  # Anzahl parallel verarbeiteter Chunks für Embeddings

# Implementierung mit asyncio
async def process_files_parallel(files: list[Path], max_workers: int = 3):
    semaphore = asyncio.Semaphore(max_workers)

    async def process_with_semaphore(file: Path):
        async with semaphore:
            return await process_single_file(file)

    tasks = [process_with_semaphore(f) for f in files]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### Konfiguration
```yaml
# config/settings.yaml
ingestion:
  parallelization:
    max_parallel_files: 3       # Parallele Dateien
    max_parallel_chunks: 10     # Parallele Chunk-Embeddings
    max_parallel_vlm: 2         # Parallele VLM-Requests (API-Limit beachten)
```

### UI-Anpassung
- Fortschrittsanzeige zeigt mehrere aktive Dateien
- Detail-Dialog kann zwischen Dateien wechseln

### Acceptance Criteria
- [ ] Mehrere Dateien werden parallel verarbeitet
- [ ] Parallelität ist konfigurierbar
- [ ] Fortschrittsanzeige zeigt alle aktiven Dateien
- [ ] Fehler in einer Datei stoppen nicht die anderen

---

## Abhängigkeiten

### Bestehende Komponenten (wiederverwendet)
- `DoclingContainerClient` - Dokument-Parsing
- `ImageProcessor` - VLM-Bildanalyse
- `ChunkingService` - Adaptive Chunking
- `QdrantClientWrapper` - Embeddings & BM25
- `LightRAGClient` - Graph-Extraktion
- SSE-Streaming (bereits für Chat implementiert)

### Neue Komponenten
- `IngestionJobTracker` - SQLite-basiertes Job-Tracking
- `DirectoryScanner` - Verzeichnis-Scanning mit Typ-Erkennung
- `ParallelIngestionOrchestrator` - Parallele Verarbeitung

---

## Nicht im Scope

- ❌ Job-Wiederaufnahme nach Abbruch
- ❌ Push-Notifications bei Job-Abschluss
- ❌ Cloud-Storage-Integration (S3, Azure Blob)
- ❌ Scheduling/Cron-Jobs

---

## Risiken

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Docling Container nicht verfügbar | Mittel | Hoch | LlamaIndex Fallback |
| VLM API Rate-Limiting | Mittel | Mittel | Konfigurierbare Parallelität |
| SQLite Lock-Contention bei Parallelisierung | Niedrig | Mittel | WAL-Mode aktivieren |
| Memory bei großen Verzeichnissen | Niedrig | Mittel | Streaming/Batching |

---

## Definition of Done

- [ ] Alle Features implementiert und getestet
- [ ] Unit Tests für Backend-Komponenten (>80% Coverage)
- [ ] E2E Tests für Frontend-Flows
- [ ] API-Dokumentation aktualisiert
- [ ] CLAUDE.md aktualisiert
- [ ] Code-Review abgeschlossen
- [ ] Keine kritischen Bugs offen
