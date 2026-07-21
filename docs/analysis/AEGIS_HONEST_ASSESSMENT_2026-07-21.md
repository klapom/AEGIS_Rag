# AEGIS RAG — Ehrliche Projektstand-Bewertung

**Datum:** 2026-07-21
**Basis:** CGC (CodeGraphContext, Neo4j-backed) Seed-Scan des Repos + Verifikation der Fable-5-Vergleichsanalyse gegen RAGU
**Analyst:** Claude Opus 4.7 (mit CGC-graph-queries), aufbauend auf Fable-5-Deep-Analysis

---

## 0. TL;DR

AEGIS ist ein **substanziell großes, architektonisch überwiegend saubes System mit einem sichtbaren Erschöpfungs-Muster:** viele Sprint-Kompensations-Schichten für dieselbe Kern-Baustelle (Extraction-Qualität), parallel ein bereits gebauter aber gestrandeter Distillation-Track. Das Backend ist gut zerlegt (keine einzige Backend-Funktion in den Top-25 Cyclomatic-Complexity — die Top-25 sind zu **21 von 25** Frontend-React-Components). Der eigentliche Aufräum-Hebel liegt an drei Stellen: (1) toter/schmal-integrierter Extraction-Nachbau (`entity_canonicalization`), (2) gestrandeter QLoRA-Adapter, (3) React-Frontend-God-Components.

Fable-5's Vergleich mit RAGU hat drei zentrale Behauptungen gemacht — CGC verifiziert **zwei davon eindeutig**, die dritte muss präzisiert werden:

| Fable-Behauptung | CGC-Verifikation | Status |
|---|---|---|
| `EntityCanonicalizer` ist toter Code | 0 Importe aus `src/`; nur `tests/unit/components/graph_rag/test_entity_canonicalization.py` importiert `CanonicalEntity` | ✅ **bestätigt** |
| QLoRA-Distillation-Track ist gebaut aber gestrandet | Alle 6 relevanten Scripts (`bin/annotate_with_llm.py`, `build_lora_dataset.py`, `download_ner_datasets.py`, `eval_extraction.py`, `eval_lora.py`, `export_for_claude.py`) sind graph-strukturell orphans (keine Import-Kette in `src/`) | ✅ **bestätigt** |
| Kaskade ist "de facto tot" (Sprint 129.6h) | `extraction_cascade`-Config wird von `extraction_factory.py`, `extraction_service.py` und 6 Tests importiert; die *Config-Struktur* lebt, der *Ollama-Rank-2/3-Pfad* ist entfernt | ⚠️ **präziser: Config lebt, Fallback-Ranks tot** |

---

## 1. CGC-Setup (frisch, heute eingerichtet)

- `.cgcignore` erweitert um `data/`, `runs/`, `models/`, `logs/`, `dashboards/`, `htmlcov/`, `llm_cache/`, `reports/`, `searxng/`, `skill_libraries/`, `skills/`, Benchmark-JSONs, node_modules etc.
- systemd-User-Service `cgc-watch-AEGIS_Rag.service` läuft und watched live
- Initial-Seed via `add_code_to_graph` (Watcher hatte in Sekunden bereits selbst begonnen; sekundärer Trigger erübrigt sich)

**Repo-Stats (nach ~2 Minuten Seed-Scan):**

| Kennzahl | Wert |
|---|---|
| Indizierte Dateien | 2 706 |
| Funktionen (Python + TS/React) | 24 438 |
| Klassen | 2 135 |
| Module | 1 477 |

**Größen-Sanity:** manuell gezählt sind es ~1 293 Python-Files (484 `src/` + 234 `scripts/` + 562 `tests/` + 13 `bin/`). Die zusätzlichen ~1 400 sind TypeScript/React im `frontend/`. Damit ist AEGIS zwar formal **ein großes System** — aber der Backend-Anteil (~50%) ist überschaubar. Der Rest ist Frontend-Fläche.

---

## 2. Was CGC an zusätzlichen Befunden liefert (jenseits von Fable)

### 2.1 Backend-Komplexität ist unauffällig — Frontend hat God-Components

Top-25 Cyclomatic-Complexity im gesamten Repo:

| # | Funktion / Component | Datei | Complexity |
|---|---|---|---|
| 1 | `GraphViewer` | `frontend/src/components/graph/GraphViewer.tsx` | **145** |
| 2 | `AdminIndexingPage` | `frontend/src/pages/admin/AdminIndexingPage.tsx` | **139** |
| 3 | `useStreamChat` | `frontend/src/hooks/useStreamChat.ts` | 128 |
| 4 | `AdminLLMConfigPage` | `frontend/src/pages/admin/AdminLLMConfigPage.tsx` | 127 |
| 5 | `handleChunk` (in `useStreamChat`) | `frontend/src/hooks/useStreamChat.ts` | 84 |
| 6–22 | weitere Frontend-Files | | 50–80 |
| 23 | `test_complete_graph_exploration_workflow` | `tests/e2e/test_e2e_graph_exploration_workflow.py` | 47 |
| 24 | `HomePage` | `frontend/src/pages/HomePage.tsx` | 47 |
| 25 | `main` | `scripts/e2e_pipeline_benchmark.py` | 45 |

**21 von 25 Top-Komplexen sind Frontend/React.** Kein einziges Backend-Modul erscheint. Das ist gleichzeitig gute Nachricht (Extraction-Service mit 4 295 Zeilen ist trotz Länge sinnvoll dekomponiert) und Hinweis auf konzentrierten Technical-Debt-Cluster im Frontend.

`GraphViewer.tsx` mit **CC 145** ist eine God-Component. Das ist die Art Datei, in der bei jedem Feature ein bisschen mehr `if`-Kette dazukommt und niemand refactored, weil sie schon so komplex ist.

### 2.2 `bin/`-Directory ist ein Friedhof für den Distillation-Track

CGC-`find_dead_code` findet nur *entdeckbare* Dead-Code-Kandidaten (also: nicht als API-Endpunkt/Fixture/Property/etc. dekoriert). Die Ausgabe wird von den 6 Distillation-Scripts komplett dominiert:

- `bin/annotate_with_llm.py` (Teacher-Annotation, 8 orphan-funcs)
- `bin/build_lora_dataset.py` (SFT-Datensatz-Bau, 8 orphan-funcs)
- `bin/download_ner_datasets.py` (HF-Downloads, 8 orphan-funcs)
- `bin/eval_extraction.py` (Extraction-Eval, 8 orphan-funcs)
- `bin/eval_lora.py` (LoRA-Modell-Eval, 14 orphan-funcs — der größte)
- `bin/export_for_claude.py` (Batch-Export, 4 orphan-funcs)

Diese Scripts sind **strukturell nicht "toter Code"** (sie sind CLI-Tools, laufen standalone) — aber sie sind eben auch **niemals aus dem System heraus aufgerufen** und ihre Outputs (Adapter unter `data/lora_adapters/`) werden von `src/` nicht konsumiert. Fable's "gestrandeter Track" ist damit graph-strukturell verifiziert: **es gibt keinen Pfad vom Trainings-Artefakt zurück in die Pipeline.**

### 2.3 Component-Health-Matrix aus Live-Import-Zählungen

| Modul | src/-Importer | tests/-Importer | scripts/-Importer | Status |
|---|---:|---:|---:|---|
| `extraction_service` | **11** (viele Callsites) | 4 | 5 | 💚 Zentral, lebendig |
| `extraction_pipeline` | **5** (v.a. `ingestion/*`, `evaluation/*`, `batch_ingestion`) | 1 | 4 | 💚 Lebendig |
| `dual_level_search` | **5** (`agents/graph_query_agent`, `retrieval/maximum_hybrid_search`, `community_search`) | 4 | 2 | 💚 Lebendig |
| `semantic_deduplicator` | **3** (`extraction_pipeline`, 2× domain-Bootstrap `__init__`) | 1 | 6 | 💚 Lebendig |
| `community_delta_tracker` | **4** (2 Bootstrap-Init, `community_detector`, `community_summarizer`) | 2 | 0 | 💚 Lebendig |
| `community_summarizer` | **4** (`api/v1/admin_graph`, `community_detector`, `jobs/community_batch_job`, Bootstrap) | 2 | 1 | 💚 Lebendig |
| `cross_sentence_extractor` | **1** (nur `extraction_service`) | 0 | 5 (nur Benchmarks) | 💚 Lebendig, aber schmal integriert |
| `kg_hygiene` | **1** (nur `extraction_pipeline`) | 3 | 0 | 💚 Lebendig, aber schmal integriert |
| `entity_consolidator` | **1** (nur `extraction_service`) | 0 | 0 | 💚 Lebendig, aber schmal integriert |
| `hybrid_extraction_service` | **1** (nur `extraction_service`) | 1 | 0 | 🟡 Beschränkt integriert |
| `section_communities` | **1** (nur `agents/graph_query_agent`) | 1 | 0 | 🟡 Beschränkt integriert |
| `community_search` | **1** (nur Domain-Bootstrap `__init__`) | 1 | 0 | 🟠 Nur indirekt sichtbar |
| `extraction_cascade` (config) | **2** (`extraction_factory`, `extraction_service`) | 5 | 3 | 💚 Config lebt (Ollama-Ranks entfernt) |
| `entity_canonicalization` | **0** | **1** (nur `CanonicalEntity`-Dataclass) | 0 | 🔴 **Tot** |

**Interpretationen:**
- Die 💚-Kern-Achse `extraction_service` → `extraction_pipeline` → `dual_level_search` ist gesund verdrahtet.
- Aber: **fünf** Backend-Module (`cross_sentence_extractor`, `kg_hygiene`, `entity_consolidator`, `hybrid_extraction_service`, `section_communities`) hängen an genau **einem** Aufrufer. Das sind Sprint-Investitionen mit hohem "wurde nur einmal integriert, wenn der Aufrufer wegfällt, ist die ganze Fläche tot"-Risiko.
- `community_search` (Fable hatte es als "besserer Pfad, aber nicht überall verdrahtet" markiert): CGC bestätigt — kein direkter Aufrufer in `src/api/` oder `src/agents/`, nur ein Bootstrap-Init. Effektiv nur über `DualLevelSearch.global_search` konsumierbar, das aber im Code als "simplified implementation" markiert ist.
- `entity_canonicalization`: **eindeutig tot**, wie Fable behauptet hat.

---

## 3. Kohärenz-Prüfung der Fable-Empfehlung mit CGC-Daten

### 3.1 Fable Item 2: "Description-Konsolidierung in `semantic_deduplicator` einbauen, toten `EntityCanonicalizer` löschen"

**CGC-Verifikation:** ✅ Löschung risikolos. Nur ein Testfile importiert `CanonicalEntity`. Der Test kann in denselben PR wandern.

### 3.2 Fable Item 4: "Distillation-Track sanieren"

**CGC-Verifikation:** ✅ Track ist strukturell isoliert, hat keine Kette in die laufende Pipeline. "Sanieren" bedeutet konkret: Adapter-Ladepfad in `extraction_service.py` einbauen (bisher **kein einziger Import von** `data/lora_adapters/*` in `src/`). Ohne diesen Ladepfad testet die geplante Sanierung die 7B-These nicht, sondern zieht nur die Eval-Skripte auf grün.

### 3.3 Fable Item 1: "7B-vs-A3B-Benchmark auf 15-Doc-Set"

**CGC-Verifikation:** ⚠️ Ergänzung nötig. Das 15-Doc-Set (128er E2E-Benchmark) läuft über die volle Pipeline — enthält damit **alle** Sprint-129-Recall-Kompensationen (Gleaning, Window-Bisection, Consolidation, Blocklist, Cascade-Guard). Ein 7B-Modell mit **derselben** Kompensations-Kette gemessen: der Test misst die *ganze Kette*, nicht das Modell. Sinnvoll ist ein zweiter Modus, in dem die Kompensations-Layer minimiert werden — sonst ist die Aussage "7B ist gleich gut" nicht sauber vom "7B ist gleich gut *nur* wegen der Nachbrenner" trennbar.

### 3.4 Fable Item 3: "Latenz-Profiling"

**CGC-Verifikation:** Backend-Struktur macht das Profiling einfach: `extraction_service.py` importiert 3 Pipeline-Stufen als getrennte Module (`cross_sentence_extractor`, `entity_consolidator`, `hybrid_extraction_service`), plus Cascade-Config. Ein Trace-Middleware auf diese vier Aufruf-Sites reicht. Der Aufwand ist realistisch niedriger als Fables 3 SP.

---

## 4. Neue Befunde, die Fable nicht gesehen hat

### 4.1 Frontend-God-Components sind der versteckte Wartungsschmerz

Vier Frontend-Files mit CC > 100 (`GraphViewer.tsx`, `AdminIndexingPage.tsx`, `useStreamChat.ts`, `AdminLLMConfigPage.tsx`) sind pro-Feature-Änderung teuer. Das ist keine RAGU-Frage, sondern eigenständiger Sprint-Kandidat. Realistischer Fix: `GraphViewer` splitten in `GraphViewerCore` + `GraphViewerControls` + `GraphFilters` (existiert bereits!) — vermutlich 5–8 SP mit sichtbarem Effekt auf Frontend-Velocity.

### 4.2 Fünf Backend-Module hängen an einem einzelnen Importer

Das ist ein **strukturelles Fragilitäts-Signal**. Falls Sprint 130 den `extraction_service` restrukturiert (was bei "sanieren" ansteht), verlieren ohne Wachsamkeit `cross_sentence_extractor`, `entity_consolidator` und `hybrid_extraction_service` gleichzeitig ihre einzigen Callsites. Empfehlung: bei jeder `extraction_service`-Änderung explizite Regression-Tests auf diese drei Sub-Modul-Grenzen.

### 4.3 `community_search` ist "gebaut, nicht verdrahtet" (analog zu `entity_canonicalization`, aber schwächer)

Kein direkter Import aus `api/`, `agents/` oder `pipelines/`. Nur ein Bootstrap-`__init__` und Tests. Wenn Fable-Item-2-artige "wir haben das schon"-Argumente für `community_search` fallen — CGC widerspricht: es existiert im Repo, aber wird nicht aktiv genutzt. Ein Sprint-Kandidat: entweder verdrahten (via `DualLevelSearch.global_search`, das seinen Code als "simplified" markiert) oder streichen.

### 4.4 `hybrid_extraction_service` als Ballast-Verdächtigter

Zweiter Kandidat für "wurde für eine ADR gebaut, dann nicht wirklich integriert": nur `extraction_service` importiert ihn. Wenn er in Nutzung ist, sollte er auch woanders auftauchen (Pipeline, Factory, mindestens ein Test außer der eigenen Unit-Suite). Weitere Prüfung nötig — kein sicherer Death-Row-Kandidat, aber Yellow Flag.

### 4.5 `bin/`-Scripts brauchen ein Aufräum-Signal

Sechs Distillation-Scripts, alle strukturell isoliert. Der `.gitignore` verbietet `bin/` sogar (Zeile 2), aber sie sind trotzdem im Repo. Zwei Optionen: **archivieren** in `scripts/archive/distillation-track-2026-03/` (mit README, wie es zum Stillstand kam) — oder als `Makefile`-Targets wiederbeleben, damit klar ist, wie man sie aufruft. Der jetzige Zustand ("liegen rum, keiner weiß wie sie zu benutzen sind") ist der schlechteste.

---

## 5. Ehrliche Gesamt-Bewertung

### Was AEGIS strukturell gut macht
- **Backend ist gut zerlegt.** Keine God-Function im Backend, `extraction_service` mit 4 295 LOC hat viele kleine Funktionen — das ist ordentliche OO/Modular-Praxis.
- **Kernachse Extraction → Pipeline → Retrieval → Dual-Search ist konsistent verdrahtet.** Kein "im-Pfad-fehlender-Aufrufer"-Bruch.
- **Community-Stack ist reichhaltiger als RAGU** (5 Module: Detector, Labeler, Summarizer, Search, Delta-Tracker + `section_communities`), im Kern über Bootstrap-Inits konsistent exportiert.
- **Test-Fläche ist substantiell.** Tests importieren die Kern-Module 1:1 — die Test-Infrastruktur ist da, wenn Refactorings sicher gemacht werden sollen.

### Was AEGIS strukturell nicht gut macht
- **Sprint-Kompensations-Muster ist sichtbar.** Fables Beobachtung stimmt: Gleaning, Window-Bisection, Consolidation, Blocklists, Cascade-Guard, Cross-Sentence-Windows — jede dieser Investitionen ist eine Reaktion auf ein Extraction-Qualitäts-Problem, das im Modell selbst gelöst gehört. Der eigentliche Hebel (Distillation) liegt gebaut aber unbenutzt herum.
- **Fragilität in "einer-Aufrufer"-Sub-Modulen.** Fünf Backend-Module hängen an genau einem Importer. Refactoring-Risiko.
- **Frontend-God-Components.** Vier Files mit CC > 100 sind unversöhnter Technical Debt.
- **Tote/schmale-Module ohne Aufräum-Disziplin.** `entity_canonicalization` ist eindeutig tot; `community_search` und `hybrid_extraction_service` sind "gebaut, kaum verdrahtet". Diese Muster haben sich vermutlich über mehrere Sprints angesammelt.
- **`bin/`-Directory ist verwaist.** Zeigt auf ein Prozess-Problem: als der Distillation-Track im März gestrandet ist, wurde weder abgeschlossen noch archiviert.

### Was AEGIS relativ zu RAGU auszeichnet
- Produkt vs. Engine: AEGIS hat Multi-Tenant, GDPR, Table/VLM-Ingestion, RAGAS-Harness, Temporal-Memory, Admin-UI. RAGU ist eine schlanke Extraction-Engine mit besser trainiertem Modell.
- Community-Stack, Query-Seite (C-LARA, HyDE, SmartEntityExpander), Chunking (section-aware, adaptive) sind bei AEGIS reicher.

### Wo RAGU strukturell einen Punkt macht
- **Beim Modell selbst.** Fable's Kern-These ist damit klar: der Meno-Lite-Ansatz (7B mit CPT+SFT auf Domänen-Korpus + Pipeline-Logs) ist konzeptionell überlegen. Bei AEGIS liegen die Rohstoffe für dasselbe Rezept bereit (EUR-Lex/OpenAlex/ClinicalTrials + `training_data_collector`), aber der eigene Track ist gestrandet.
- **Bei der Description-Konsolidierung.** Live-Dedup konkateniert nur; das echte Merge-Konzept war in `EntityCanonicalizer` gedacht, das aber nie in den Pfad kam und mit einem "nimm nur erste Description"-Bug ausgestattet ist.

---

## 6. Sprint-130-Priorisierung nach dieser Verifikation

Ich übernehme Fables 5-Item-Vorschlag, aber **ordne um** und modifiziere:

| Rang | Item | SP | Warum jetzt |
|---|---|---:|---|
| **1** | **Latenz-Profiling** (Fable #3) mit Trace-Middleware auf die 4 `extraction_service`-Sub-Modul-Aufruf-Sites | 2 | Fable schätzte 3 SP; CGC zeigt: Struktur ist bereits so zerlegt, dass Middleware trivial ist. **Entscheidet, ob Modellgröße oder Call-Count der Bottleneck ist — Voraussetzung für Item 4-Priorisierung.** |
| **2** | **Toten `EntityCanonicalizer` löschen + Description-Konsolidierung** in `semantic_deduplicator` einbauen (Fable #2, RAGU-Muster) | 5 | Niedrigstes Risiko (0 src/-Aufrufer), höchster Quality-per-SP (wirkt auf `community_summarizer` → Global Search → RAGAS CP/CR). |
| **3** | **7B-vs-A3B-Benchmark** auf 15-Doc-Set (Fable #1) — **erweitert**: zwei Modi (mit / ohne Sprint-129-Kompensations-Layer) | 5 | Fable schätzte 3 SP; CGC-Befund: ohne den zweiten Modus misst der Test die Kompensations-Kette, nicht das Modell. Aussagekraft entscheidet Item 4. |
| **4** | **Distillation-Track sanieren mit CPT** (Fable #4) — **erweitert**: Adapter-Ladepfad in `extraction_service` einbauen, Eval fixen, dann Re-Target 7B mit CPT auf EUR-Lex/OpenAlex/ClinicalTrials | 8 | Anders als Fable: der Ladepfad muss **vor** allem anderen rein, sonst testet die Sanierung wieder nur die Scripts. |
| **5** | **GraphRAG-Bench-Medical als externes Maßband + Propositionizer-Decision-Gate** (Fable #5) | 3 | Externer Vergleichspunkt; Propositionizer-Projekt pausieren bis Item 3/4 Ergebnis. |
| **6 (neu)** | **`bin/`-Archivierung**: sechs Scripts nach `scripts/archive/distillation-track-2026-03/` verschieben, README schreiben ("So starb der Track"). Falls Item 4 startet: neu aufsetzen in `bin/` mit klarer Doku. | 1 | Aufräum-Disziplin. Klärt Ursprung des Track für Sprint 130-Owner. |
| **7 (neu)** | **`community_search`- und `hybrid_extraction_service`-Verdrahtungs-Audit**: verdrahten oder streichen (analog `EntityCanonicalizer`) | 2 | Verhindert dass sich das Muster verfestigt. |

**Neue Summe:** 26 SP (statt 22). Der Zusatz-Aufwand kommt aus (a) der Erweiterung von Item 3 auf zwei Modi und (b) den beiden CGC-Aufräum-Items. Beides ist notwendig, wenn die Verifikation ehrlich abgeschlossen werden soll.

**Optional, nicht in Sprint 130:**
- **Frontend-God-Component-Refactor** (`GraphViewer` splitten): ~5–8 SP, aber orthogonal — nichts mit RAGU / Extraction zu tun. Kandidat für eigenen Frontend-Sprint.

---

## 7. Meta-Beobachtung — was AEGIS über sich lernen sollte

Über die letzten Sprints (128 → 129) hat AEGIS **funktional viel geliefert** (LightRAG-Removal, Cascade-Guard, HyDE, Window-Bisection, Table-/VLM-Ingestion, Nemotron3-Migration). Aber die Sprint-Reihenfolge ist verräterisch: fast jede Investition ist entweder eine **Kompensation** für Extraction-Qualität oder eine **neue Fläche** oben drauf. Der eigentliche Hebel — das Modell — wurde einmal angegangen (März 2026, QLoRA-Track), ist unbemerkt gestrandet, und keine spätere Sprint-Retrospektive hat ihn wieder aufgegriffen.

Das ist kein individueller Fehler; es ist ein **Prozess-Muster**: die schnellen Gewinne (nachgelagerte Kompensation) sind sichtbarer und weniger riskant als die langsamen Gewinne (Modelltraining). RAGU als externer Referenzpunkt hilft, weil er zeigt: das Modell zu trainieren ist der Hebel, den man mit den Rohstoffen (EUR-Lex/OpenAlex/ClinicalTrials + `training_data_collector`), die bereits im Haus liegen, angehen sollte.

Sprint 130 ist der Punkt, an dem entweder das Modell wieder auf die Prio-Liste kommt — oder AEGIS mit einer weiteren Ebene Kompensations-Sprint-Investitionen weiterläuft und die 6–8 min/doc-Ingestion sich langsam auf 8–10 min entwickelt, weil noch ein Nachbrenner dazu kommt.

---

## Anhang — CGC-Setup als reproduzierbarer Schritt

```bash
# 1. .cgcignore anlegen (siehe Repo-Root)
# 2. Bootstrap
~/.claude/scripts/cgc-bootstrap.sh /home/admin/projects/aegisrag/AEGIS_Rag/
# 3. Optional: initial seed (Watcher startet ihn ohnehin selbst)
#    mcp__codegraph__add_code_to_graph(path="/home/admin/projects/aegisrag/AEGIS_Rag")
# 4. Ab jetzt Code-Fragen via CGC statt grep:
#    mcp__codegraph__find_code, analyze_code_relationships (find_importers, class_hierarchy,
#    dead_code), find_most_complex_functions, get_repository_stats
```
