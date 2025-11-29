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
| 33.9 | DoclingParsedDocument Interface Fix (TD-044) | 5 SP | P0 |
| 33.10 | Multi-Format Section Extraction & Legacy Handling | 5 SP | P0 |
| 33.11 | VLM Pipeline Integration & Image Filtering | 5 SP | P1 |
| **Gesamt** | | **77 SP** | |

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

## Feature 33.9: DoclingParsedDocument Interface Fix (TD-044) (5 SP)

### Beschreibung
Kritische Fehlerbehebung für DoclingParsedDocument Interface-Mismatch, der Section Extraction für alle Dokumentformate blockiert hat.

### Problem
- `DoclingParsedDocument` (HTTP API Wrapper) fehlten `.body` und `.document` Attribute
- Section Extraction scheiterte für ALLE Formate (PDF, DOCX, PPTX - nicht nur PowerPoint)
- Dead Code in `langgraph_nodes.py` (Zeilen 510-529) wurde nie ausgeführt
- Doppeltes Chunking: Pipeline → 1 Chunk, LightRAG → 122 Chunks
- Symptom: Alle Dateien bekamen nur 1 Chunk ohne Sections

### Root Cause
```python
# DoclingParsedDocument (HTTP wrapper) war:
class DoclingParsedDocument:
    json_content: dict  # Parsed document as dict
    # FEHLEND: .body und .document wie native Docling Objekte

# Aber section_extraction.py erwartete:
if isinstance(parsed_doc.document.body, list):  # AttributeError!
```

### Lösung

#### 1. Property Accessors zu DoclingParsedDocument hinzufügen
```python
@property
def body(self):
    """Access document body from Docling JSON."""
    return self.json_content.get("body")

@property
def document(self):
    """Self-reference for native Docling object interface."""
    return self
```

#### 2. Dead Code aus langgraph_nodes.py entfernen (Zeilen 510-529)
```python
# ENTFERNEN: Dieser Code wurde nie ausgeführt
if hasattr(parsed_docling_doc, "document") and parsed_docling_doc.document is not None:
    # This branch never executed for DoclingParsedDocument
    sections = extract_sections_from_docling(parsed_docling_doc.document.body)
else:
    # Always took this path, so dead code above was useless
    sections = extract_sections_from_docling(parsed_docling_doc.json_content.get("body"))
```

#### 3. section_extraction.py für Dict-Format aktualisieren
```python
# Jetzt funktioniert mit beiden Formaten:
# - Docling native Objekte: parsed_doc.document.body
# - DoclingParsedDocument HTTP wrapper: parsed_doc.body (via property)
def extract_sections(body_content):
    if isinstance(body_content, dict):
        # Handle dict format from Docling JSON
        return extract_from_dict(body_content)
    elif isinstance(body_content, list):
        # Handle native Docling object format
        return extract_from_list(body_content)
```

### Auswirkungen
- Section Extraction funktioniert jetzt für PDF, DOCX, PPTX
- Kein doppeltes Chunking mehr
- Dead Code entfernt, Codebase sauberer
- Backward compatible (alle Dateitypen)

### Betroffene Dateien
- `src/components/ingestion/docling_client.py` (Add properties)
- `src/components/ingestion/langgraph_nodes.py` (Remove dead code)
- `src/components/ingestion/section_extraction.py` (Handle dict format)

### Acceptance Criteria
- [ ] Section Extraction funktioniert für PDF
- [ ] Section Extraction funktioniert für DOCX
- [ ] Section Extraction funktioniert für PPTX
- [ ] Kein doppeltes Chunking mehr
- [ ] Dead Code entfernt
- [ ] Alle Tests bestehen (>80% coverage)
- [ ] Integration Tests für all 3 Formate

### Test-Strategie
```python
@pytest.mark.parametrize("file_format", ["pdf", "docx", "pptx"])
async def test_section_extraction_for_all_formats(file_format):
    # Test mit echten Test-Dateien für alle Formate
    parsed_doc = await docling_client.parse_document(test_file[file_format])
    sections = extract_sections(parsed_doc)
    assert len(sections) > 0
    assert all(s.heading for s in sections)
```

### Dokumentation
- **TD-044:** `docs/technical-debt/TD-044_DOCLING_PARSED_DOCUMENT_INTERFACE.md`
- **Sprint 33:** Diese Feature dokumentiert in SPRINT_33_PLAN.md
- **Architecture:** ARCHITECTURE_EVOLUTION.md aktualisiert

### Abhängigkeiten
- Keine - Standalone Bug Fix
- Blockiert: Alle anderen Sprint-33-Features (bis TD-044 behoben)

---

## Feature 33.10: Multi-Format Section Extraction & Legacy Format Handling (5 SP)

### Beschreibung
Verbesserungen an der Section Extraction für verschiedene Dokumentformate nach detaillierter API-Analyse und Tests.

### Erkenntnisse aus der Docling API-Analyse

#### Docling DocItemLabel Enum
Docling verwendet verschiedene Labels je nach Dokumenttyp:
- **PPTX:** `title`, `subtitle-level-1`, `subtitle-level-2`, `paragraph`, `list_item`
- **DOCX:** `section_header` (für Word Heading Styles), `paragraph`, `list_item`
- **PDF:** `section_header`, `title`, `paragraph`

**Wichtig:** Unser Code hatte ursprünglich nur `title` Labels geprüft, aber DOCX verwendet `section_header` mit `level` Attribut!

#### Format Support Matrix

| Format | Status | Strategy | Labels | Notes |
|--------|--------|----------|--------|-------|
| **PPTX** | Working | `labels` | `title`, `subtitle-level-*` | Slide titles werden erkannt |
| **DOCX** (mit Word Heading Styles) | Fixed | `labels` | `section_header` mit `level` | Nach Fix für `section_header` Label |
| **DOCX** (ohne Heading Styles) | Fixed | `formatting` | `paragraph` mit `formatting.bold` | Fallback für formatierte Headings |
| **PDF** | Working | `labels` | `title`, `section_header` | Standard PDF Headings |
| **PPT** | NOT SUPPORTED | N/A | N/A | Legacy Binary Format |
| **DOC** | NOT SUPPORTED | N/A | N/A | Legacy Binary Format |
| **XLS** | NOT SUPPORTED | N/A | N/A | Legacy Binary Format |

### Implementierte Fixes

#### 1. `section_header` Label Support
```python
# Vorher: Nur title Labels
HEADING_LABELS = {"title", "subtitle-level-1", "subtitle-level-2"}

# Nachher: Auch section_header
HEADING_LABELS = {"title", "section_header", "subtitle-level-1", "subtitle-level-2"}
```

#### 2. Level-Attribut für section_header
```python
def _get_heading_level(heading_type: str, text_item: dict | None = None) -> int:
    # section_header hat level-Attribut (1, 2, 3, etc.)
    if heading_type == "section_header" and text_item:
        level = text_item.get("level")
        if level and isinstance(level, int) and 1 <= level <= 6:
            return level
        return 1
    # Andere Labels: Mapping
    heading_map = {"title": 1, "section_header": 1, "subtitle-level-1": 2, "subtitle-level-2": 3}
    return heading_map.get(heading_type, 1)
```

#### 3. Legacy Format Rejection
```python
# docling_client.py: Runtime check für unsupported formats
LEGACY_FORMATS = {".doc", ".xls", ".ppt"}
if file_ext in LEGACY_FORMATS:
    raise IngestionError(
        f"Legacy Office format '{file_ext}' is NOT SUPPORTED. "
        f"Please convert to modern format (.docx, .xlsx, .pptx) before processing."
    )
```

### Betroffene Dateien
- `src/components/ingestion/section_extraction.py`
  - Added `section_header` to HEADING_LABELS
  - Updated `_get_heading_level()` for level attribute
  - Strategy detection für `labels` vs `formatting`
- `src/components/ingestion/docling_client.py`
  - Added format support matrix documentation
  - Added legacy format runtime rejection

### Test-Ergebnisse

**OT_requirements_FNT_Command_20221219.docx** (mit Word Heading Styles):
```
section_header labels: 42
Level distribution:
- L1: 8 headings (Hauptkapitel)
- L2: 22 headings (Unterkapitel)
- L3: 12 headings (Abschnitte)
```

**DE-D-AdvancedAdministration_0368.docx** (ohne Word Heading Styles):
```
section_header labels: 0 (uses formatting.bold fallback)
Formatting-based headings: 187
Strategy: formatting
```

### Acceptance Criteria
- [x] `section_header` Label wird erkannt
- [x] Level-Attribut wird korrekt verarbeitet (1-6)
- [x] DOCX mit Word Heading Styles extrahiert Sections korrekt
- [x] DOCX ohne Heading Styles nutzt Formatting-Fallback
- [x] Legacy Formate (.doc, .xls, .ppt) werden mit klarer Fehlermeldung abgelehnt
- [x] API-Dokumentation im Code aktualisiert
- [x] TD-044 Addendum dokumentiert

### Lessons Learned
- Docling API Dokumentation ist nicht vollständig - praktisches Testen essentiell
- DOCX verwendet `section_header` statt `title` für Word Heading Styles
- Legacy Office Formate (Binary) werden von Docling nicht unterstützt (python-docx limitation)
- Formatting-based heading detection ist guter Fallback für DOCX ohne Styles

---

## Feature 33.11: VLM Pipeline Integration & Image Filtering (5 SP)

### Beschreibung
Integration des VLM Image Enrichment Nodes in die LangGraph Ingestion Pipeline mit optimierten Bildfiltern zur Kosteneinsparung.

### Problem
- `image_enrichment_node` existierte bereits (Feature 21.6), war aber NICHT in die Pipeline eingebunden
- Keine Bildfilterung für irrelevante Bilder (kleine Icons, Platzhalter, Banner)
- Pipeline hatte nur 5 Nodes: `memory_check → parse → chunking → embedding → graph`

### Lösung

#### 1. VLM Node in Pipeline integriert
```python
# langgraph_pipeline.py - Neue 6-Node Pipeline
graph.add_edge("memory_check", "parse")
graph.add_edge("parse", "image_enrichment")  # NEU: VLM nach Parsing
graph.add_edge("image_enrichment", "chunking")
graph.add_edge("chunking", "embedding")
graph.add_edge("embedding", "graph")
```

#### 2. Optimierte Bildfilter (Kostenersparnis)
```python
# image_processor.py - Verbesserte Defaults
class ImageProcessorConfig:
    min_size: int = 200           # War 100 - Skip kleine Icons
    min_aspect_ratio: float = 0.2 # War 0.1 - Skip schmale Balken
    max_aspect_ratio: float = 5.0 # War 10.0 - Skip breite Banner
    min_unique_colors: int = 16   # NEU - Skip einfarbige Platzhalter
```

#### 3. Farbfilter für Platzhalter-Bilder
```python
def count_unique_colors(image: Image.Image, sample_size: int = 10000) -> int:
    """Zählt einzigartige Farben (mit Sampling für Performance)."""
    pixels = list(image.getdata())
    if len(pixels) > sample_size:
        pixels = random.sample(pixels, sample_size)
    return len(set(pixels))

def should_process_image(..., min_unique_colors: int = 16) -> tuple[bool, str]:
    # ... size und aspect ratio checks ...
    if min_unique_colors > 0:
        unique_colors = count_unique_colors(image)
        if unique_colors < min_unique_colors:
            return False, f"too_few_colors: {unique_colors} < {min_unique_colors}"
    return True, "valid"
```

### Pipeline Flow (Neu)
```
START
  ↓
memory_check_node (5% progress)
  ↓
parse_node (20% progress) - Docling oder LlamaIndex
  ↓
image_enrichment_node (35% progress) - NEU: Qwen3-VL Beschreibungen
  ↓
chunking_node (50% progress)
  ↓
embedding_node (75% progress)
  ↓
graph_extraction_node (100% progress)
  ↓
END
```

### VLM-Text Platzierung
- VLM-Beschreibungen werden in `picture_item.text` eingefügt (Docling-Objekt)
- Beim Chunking fließt der VLM-Text in den richtigen Dokumentkontext
- BBox-Metadaten bleiben für präzise Lokalisierung erhalten
- Funktioniert für alle Docling-unterstützten Formate (PDF, DOCX, PPTX, XLSX)

### Betroffene Dateien
- `src/components/ingestion/image_processor.py`
  - Neue Defaults für Filter (min_size=200, aspect ratios, colors)
  - `count_unique_colors()` Funktion hinzugefügt
  - `should_process_image()` erweitert um Farbfilter
- `src/components/ingestion/langgraph_pipeline.py`
  - Import von `image_enrichment_node`
  - Node zur Pipeline hinzugefügt zwischen `parse` und `chunking`
  - Timing-Logs aktualisiert für VLM-Metrik

### Test-Ergebnisse
```
IMAGE FILTER TESTS - Sprint 33
============================================================

1. Single color image:    1 unique colors -> too_few_colors: 1 < 16    PASS
2. Small image (50x50):   -> too_small: 50x50 < 200px                  PASS
3. Wide image (10:1):     -> too_small: 1000x100 < 200px               PASS
4. Narrow image (0.1:1):  -> too_small: 100x1000 < 200px               PASS
5. Good gradient image:   9609 unique colors -> valid                  PASS

ALL FILTER TESTS PASSED!
```

### Erwartete Kosteneinsparung
| Filter | Geschätzte Filterrate | Einsparung |
|--------|----------------------|------------|
| min_size: 200px | ~30% Icons/Logos | 30% VLM Calls |
| aspect_ratio: 0.2-5.0 | ~10% Banner/Bars | 10% VLM Calls |
| min_unique_colors: 16 | ~20% Platzhalter | 20% VLM Calls |
| **Gesamt** | | **~50% weniger VLM Calls** |

### Acceptance Criteria
- [x] `image_enrichment_node` ist in Pipeline eingebunden
- [x] Filter-Defaults optimiert (min_size=200, aspect ratios)
- [x] Farbfilter für einfarbige Bilder implementiert
- [x] Alle Filter-Tests bestehen
- [x] Pipeline-Timing enthält VLM-Metrik
- [x] Dokumentation aktualisiert

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
