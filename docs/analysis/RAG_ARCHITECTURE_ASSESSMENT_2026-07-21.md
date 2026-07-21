# AEGIS-RAG — Architektur- und Latenz-Assessment

**Datum:** 2026-07-21
**Analyst:** Fable-5 (Deep-Analysis-Subagent), aufbauend auf `RAGU_vs_AEGIS_2026-07-21.md` und `AEGIS_HONEST_ASSESSMENT_2026-07-21.md` (Befunde von dort werden hier NICHT wiederholt)
**Methode:** Deep-Read der Live-Pfade (Upload→Neo4j, Chat→Answer) + CGC-Graph-Queries (find_importers) zur Verifikation von Verdrahtungs-Behauptungen
**Extraction-LLM:** `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4` via vLLM :8001; Chat: Ollama Nemotron3 :11434

**Ehrlicher Vorbehalt:** Es gibt keine per-Stage-Messungen (Sprint-130-Item 1 "Latenz-Profiling" ist genau deshalb richtig priorisiert). Alle Zeitschätzungen unten sind aus Call-Counts × plausiblen Latenzen hergeleitet und als Spannen angegeben. Die *Struktur*-Befunde (wer ruft wen, sequenziell vs. parallel, was ist doppelt) sind dagegen Code-belegt und messungsunabhängig.

---

## 0. Die drei Kernbefunde in einem Absatz

Die 6–8 min/doc entstehen **nicht** im Modell und **nicht** in den Datenbanken, sondern aus drei strukturellen Eigenschaften des Ingestion-Codes: **(1) Relation-Extraction läuft doppelt** — einmal in der Extraction-Pipeline (Stage 3), danach ein komplett zweiter Durchlauf pro Chunk in `graph_extraction_node` („Round 2", ein Sprint-33/34-Relikt); **(2) alle ~150 LLM-Calls pro Dokument laufen strikt sequenziell** — obwohl im Repo *zwei* fertig gebaute Parallelisierungs-Module liegen (`extraction_worker_pool.py`, `parallel_extractor.py`), die CGC-verifiziert von keinem Live-Pfad importiert werden; **(3) der Upload-Endpoint hält den HTTP-Request über die gesamte Ingestion offen**. Punkt 1+2 sind zusammen eine realistische **~5–6× Beschleunigung ohne Modellwechsel und ohne Qualitätsrisiko-Experimente**.

---

## A) Ingestion-Flow-Karte

### A.1 End-to-End-Trace

```
POST /api/v1/retrieval/upload                        retrieval.py:646
  └─ await run_ingestion_pipeline(...)               retrieval.py:745  ← Request bleibt offen (6–8 min!)
       LangGraph (strikt sequenziell, keine Node-Überlappung):   langgraph_pipeline.py:241–249
       memory_check → parse → image_enrichment → chunking → embedding → graph → END
```

Der `graph`-Node zerfällt intern in 7 Sub-Stufen:

```
graph_extraction_node                                nodes/graph_extraction.py:41
  1. Domain-Auto-Klassifikation (BGE-M3)             :93–226   (~100 ms)
  2. ROUND 1: extract_and_store_entities             :316 → extraction_pipeline.py:130
       pro Chunk SEQUENZIELL (for-Schleife, kein gather):       extraction_pipeline.py:183–236
         SpaCy NER            (~50 ms)               extraction_service.py:2095
         LLM Entity-Enrichment (1 LLM-Call)          extraction_service.py:2298, Timeout 120 s
         Entity-Consolidation (CPU)                  extraction_service.py:2136
         LLM Relation-Extraction (1 LLM-Call)        extraction_service.py:2437, Timeout 180 s
       danach doc-weit: Blocklist-Filter → Semantic-Dedup (BGE-M3-Batch) →
       Relation-Dedup → KG-Hygiene → Neo4j-Store (UNWIND-batched)
  3. await asyncio.sleep(1.0)  „Neo4j-Commit-Wait"   graph_extraction.py:360
  4. ROUND 2: Relation-Re-Extraction                 graph_extraction.py:430–561
       pro Chunk SEQUENZIELL:
         2 Neo4j-Reads (Chunks + Entities je Chunk)  :396–416, :442–454
         1 LLM-Call RelationExtractor.extract        relation_extractor.py:175 (gleaning_steps=0)
         Neo4j store_relations                       :501
  5. Section-Nodes (UNWIND-batched, schnell)         graph_extraction.py:623
  6. Community Detection: default „scheduled" → SKIP config.py:705 (nightly 5-AM-Job)
  7. Stats + Progress-Events
```

### A.2 Stage-Tabelle (Referenzdokument: 50 Chunks)

| # | Stage | Modul / Funktion | Sync/Async | LLM-Calls | Timeout | Retry | Concurrency | Zeit/Doc (geschätzt) |
|---|-------|------------------|-----------|-----------|---------|-------|-------------|----------------------|
| 1 | Upload + Temp-Save | `retrieval.py:646` `upload_file` | async, **Request bleibt offen** | 0 | Rate-Limit only | — | 1 Request | <1 s |
| 2 | memory_check | `nodes/memory_management.py` | async | 0 | — | — | — | <1 s |
| 3 | Docling-Parse | `nodes/document_parsers.py:153`, Container-Client :236 | async → GPU-Container | 0 | `docling_timeout_seconds` (config.py:1012) | `docling_max_retries` | 1 | **20–90 s** (Prewarm-abhängig; Container-Restart bei VRAM-Leak :244–249; Stop gibt ~6 GB frei :329) |
| 4 | Image/VLM-Enrichment | `nodes/image_enrichment*.py`, `vlm_page_processor` | async | 0–N VLM | — | — | `ingestion_max_concurrent_vlm` (config.py:1105) | 0–120 s (nur Bild-PDFs) |
| 5 | Adaptive Chunking | `nodes/adaptive_chunking.py` (ADR-039) | async, CPU | 0 | — | — | — | <5 s |
| 6 | Embedding + Qdrant | `nodes/vector_embedding.py:147` `embed_batch`, Upsert batch_size=100 :376 | async, **batched** | 0 | — | — | Batch | 5–15 s |
| 7 | Domain-Klassifikation | `graph_extraction.py:135` (BGE-M3) | async | 0 | — | best-effort | — | <1 s |
| 8 | **Round-1-Extraction** | `extraction_pipeline.py:183–236` → `extraction_service.py:2050` | async, **sequenziell pro Chunk** | **2/Chunk = 100** | 120 s + 180 s pro Stage | Timeout→leeres Ergebnis (kein Retry im SpaCy-First-Pfad) | **1** (!) | **≈ 200–400 s** |
| 9 | Dedup + Hygiene | `semantic_deduplicator.py:322` (BGE-M3 embed_batch), `kg_hygiene` | async, batched | 0 | — | Fallback auf raw | Batch 32 | 5–15 s |
| 10 | Neo4j-Store R1 | `neo4j_client.py:739` store_relations, UNWIND :770; store_chunks_and_provenance | async, UNWIND-batched, aber **pro Chunk-Gruppe einzeln** (extraction_pipeline.py:442) | 0 | — | — | 1 | <5 s |
| 11 | Commit-Sleep | `graph_extraction.py:360` | `asyncio.sleep(1.0)` | 0 | — | — | — | 1 s |
| 12 | **Round-2-Relations** | `graph_extraction.py:430–561` → `relation_extractor.py:175` | async, **sequenziell pro Chunk** | **1/Chunk = 50** + 2 Neo4j-Reads/Chunk | LLM-Proxy-Timeout | tenacity (relation_extractor.py:236) | **1** (!) | **≈ 100–250 s** |
| 13 | Section-Nodes | `neo4j_client.py` create_section_nodes (UNWIND :401) | async, batched | 0 | — | optional (Fehler ≠ Abbruch) | — | <2 s |
| 14 | Community Detection | `community_detector.py:206` | **default übersprungen** (`scheduled`, config.py:705) | 0 (nightly: +LLM-Summaries via Delta-Tracker) | — | — | — | 0 s |

**Σ ≈ 5,5–13 min — deckt die beobachteten 6–8 min ab. ~150 sequenzielle LLM-Calls ≈ 85–90 % der Wall-Time.**

### A.3 Was im Live-Pfad NICHT läuft (wichtig für Abschnitt D)

Code-verifiziert (SpaCy-First ist default, `extraction_cascade.py:218`):

- **Gleaning:** Round 2 ruft `extract_with_gleaning(gleaning_steps=0)` auf (graph_extraction.py:494-496) — Gleaning ist **abgeschaltet**. Die Gleaning-Methoden in `extraction_service.py` (:3209, :4038) haben keine Caller außerhalb des Legacy-Pfads.
- **Cross-Sentence-Windows + Bisection:** nur erreichbar über `extract_relationships` → `_extract_relationships_windowed` (extraction_service.py:3716→3766) — das ist der **Legacy-Cascade-Pfad** (`AEGIS_USE_LEGacy_CASCADE=1`). Im SpaCy-First-Pfad (Stage 3 = einzelner LLM-Call, :2437) laufen sie **nicht**.
- **Cascade-Guard** (`_wait_for_vllm_capacity`, :1364): nur im Legacy-Cascade-Pfad relevant.

Die Sprint-128/129-„Kompensations-Layer" sind also im Default-Betrieb überwiegend **schlafender Code** — sie kosten keine Latenz, aber sie kosten Wartung und täuschen im Sprint-Log Aktivität vor, die im Produktionspfad gar nicht wirkt. (Ausnahme: Blocklist :extraction_pipeline.py:42 und Entity-Consolidation :extraction_service.py:2136 laufen live und sind billig.)

---

## B) Query-Flow-Karte

### B.1 End-to-End-Trace

```
POST /api/v1/chat[/stream]                            chat.py:375 / :540
  └─ CoordinatorAgent.process_query[_stream]          chat.py:417 / :610
       LangGraph-Stern (graph.py:469–538):
       START → router → {hybrid_search | vector_search | graph_query | memory | tools} → answer → END

router_node                                           router.py:257
  intent vom User gesetzt (UI-Mode) → SKIP            router.py:284–295
  intent=None/auto → LLM-Klassifikation (1 Call!)     router.py:171–216   ← 2–10 s

hybrid_search_node (default)                          graph.py:213
  └─ vector_search_node → VectorSearchAgent.process   vector_search_agent.py:74
       └─ FourWayHybridSearch.search                  four_way_hybrid_search.py:167
            1. Query-Cache-Check (Redis)              :237
            2. Intent-Klassifikation #2: SetFit C-LARA, ~20–50 ms   intent_classifier.py:14
            3. 4 Kanäle PARALLEL (asyncio.gather :301):
               dense + sparse (Qdrant BGE-M3), graph_local (~100 ms Cypher),
               graph_global (~100 ms, Community-basiert)
            4. Entity-Expansion via Vector-Results    :330
            5. Intent-gewichtete RRF-Fusion
            6. Rerank (reranker_enabled=True default, config.py:513):
               backend „sentence-transformers" (default, config.py:517): Cross-Encoder-Batch
               backend „ollama": 1 LLM-Call PRO DOKUMENT, sequenziell!  ollama_reranker.py:148–161
  └─ Text-Dedup (erste 200 Zeichen)                   graph.py:310–316

llm_answer_node                                       graph.py:37
  └─ AnswerGenerator.generate_with_citations_streaming (Ollama Nemotron3, Token-Streaming)
       ← dominiert: Antwortlänge / 64 tok/s ⇒ 5–15 s

Hinweis Sprint 115 / ADR-057: graph_query_node ist im Hybrid-Pfad DEAKTIVIERT
(graph.py:221–228) — SmartEntityExpander kostete ~26 s (2 LLM-Calls); Graph-Suche
läuft jetzt als graph_local/graph_global-Kanal in FourWayHybridSearch.
```

### B.2 Query-Stage-Tabelle

| Stage | Modul | LLM-Calls | Zeit (geschätzt) | Anmerkung |
|-------|-------|-----------|------------------|-----------|
| Router-Intent | `router.py:171` | **0 oder 1** | 0 ms / **2–10 s** | Nur bei intent=auto; UI-Modus überspringt |
| Intent #2 (C-LARA) | `intent_classifier.py` | 0 (SetFit) | 20–50 ms | redundant zum Router, aber billig |
| 4-Kanal-Retrieval | `four_way_hybrid_search.py:301` | 0 | 100–500 ms | parallel via gather — sauber |
| Entity-Expansion | :330 | 0 | ~100 ms | |
| Rerank | Cross-Encoder default | 0 | 200 ms–1 s | **Ollama-Backend wäre O(n) LLM-Calls sequenziell — nicht aktivieren ohne Fix** (ollama_reranker.py:148) |
| Answer-Generation | Ollama Nemotron3 streaming | 1 (streaming) | **5–15 s** | tokenzahl-gebunden, 64 tok/s |

**Query-Latenz ist strukturell in Ordnung.** Post-ADR-057 ist Retrieval sub-sekündig; die Wall-Time ist Answer-Generierung (unvermeidlich, gestreamt) plus — im Auto-Modus — der **LLM-Router als einzig vermeidbarer Block von 2–10 s**.

**HyDE ist im Live-Query-Pfad nicht verdrahtet:** `hyde.py` wird ausschließlich von `maximum_hybrid_search.py` importiert (:41,:175,:183), und `maximum_hybrid_search` hat keinen Caller in `api/` oder `agents/` (nur `__init__`-Re-Export). Der Chat-Pfad (graph.py → vector_search_agent → FourWayHybridSearch) führt HyDE **nie** aus. Gleiche Kategorie wie `community_search` im vorherigen Assessment: gebaut, nicht verdrahtet.

**Store-Beteiligung pro Standard-Query:** Qdrant (dense+sparse) ✓, Neo4j (graph_local/global) ✓, Redis (Query-Cache, Session) ✓, **Graphiti nur im MEMORY-Intent-Pfad** (memory_agent.py:49) — bei Standard-Hybrid-Queries unbeteiligt.

---

## C) Latenz-Hotspot-Ranking

Ingestion (I) pro Doc à 50 Chunks; Query (Q) pro Request. Fix-Schwierigkeit: 🟢 einfach / 🟡 mittel / 🔴 schwer.

| # | Hotspot | Beleg | Zeit | Grund | Fix |
|---|---------|-------|------|-------|-----|
| 1 | **I: Round-1-Extraction sequenziell** | `extraction_pipeline.py:183` (`for chunk in chunks: await extractor.extract`) | ~200–400 s | 100 LLM-Calls, Concurrency=1; vLLM-A3B könnte 4–8 parallel batchen | 🟢 `asyncio.gather` + `Semaphore(settings.graph_extraction_workers)` — Config existiert schon (config.py:659, default 4)! |
| 2 | **I: Round-2-Relation-Loop = Duplikat** | `graph_extraction.py:430–561`; Round 1 speichert Relationen bereits (extraction_pipeline.py:442–448) | ~100–250 s | 50 zusätzliche LLM-Calls + 100 Neo4j-Reads für Arbeit, die Stage 3 gerade erledigt hat — mit *untypisierten* Relationen (relation_extractor.py) gegen die ADR-060-typisierten aus Round 1 | 🟢 **Löschen.** Höchstes Nutzen/Risiko-Verhältnis im ganzen System |
| 3 | **I: Docling-Parse** | `document_parsers.py:236–253`, Container-Lifecycle :244–249, :329 | ~20–90 s | GPU-OCR + ggf. Container-Kaltstart/Restart | 🟡 Prewarm konsequent (Mechanismus existiert :212–228); Messung nötig |
| 4 | **Q: LLM-Router im Auto-Modus** | `router.py:171–216` | 2–10 s/Query | 1 LLM-Call für 4-Klassen-Entscheidung, während 20-ms-SetFit-Classifier im selben Repo existiert | 🟢 SetFit-Klassifier (intent_classifier.py) auch fürs Routing nutzen |
| 5 | **I: keine Pipeline-Überlappung** | `langgraph_pipeline.py:244–249` | verdeckt ~30–100 s | Embedding wartet auf komplettes Chunking, Graph auf komplettes Embedding; Chunks könnten streamen | 🔴 strukturell (StreamingPipelineOrchestrator existiert ungenutzt: `streaming_pipeline.py`, nur Domain-`__init__`+Tests importieren ihn) |
| 6 | **I: VLM-Enrichment** | `document_parsers.py:314`, `image_enrichment*.py` | 0–120 s | pro Seite/Bild VLM-Calls | 🟡 nur bildlastige Docs; parallel-Flag existiert (`vlm_parallel_pages_enabled`) |
| 7 | **Q: Answer-Generation** | graph.py:112 | 5–15 s | tokenzahl-gebunden, 64 tok/s Ollama | 🔴 nur via kürzere Prompts/Kontexte oder schnellere Serving-Engine; gestreamt → UX ok |
| 8 | **I: Upload hält Request offen** | `retrieval.py:745` | (keine CPU-Zeit, aber Timeout-/UX-Risiko) | synchrones `await` über 6–8 min; Proxy-Timeouts, kein Retry-Handle | 🟢 202 + Job-ID; `parallel_orchestrator` + `job_tracker` existieren bereits (admin_indexing.py nutzt sie) |
| 9 | **I: `asyncio.sleep(1.0)`** | `graph_extraction.py:360` | 1 s | Race-Condition-Pflaster statt Transaktions-Garantie | 🟢 entfällt mit Fix #2 komplett |
| 10 | **Q: Ollama-Reranker (latent)** | `ollama_reranker.py:148–161` | (nur wenn backend=ollama) | sequenzielle Doc-Schleife, 1 LLM-Call/Dokument | 🟢 `gather` — oder Backend gelöscht lassen (default ist Cross-Encoder) |

**Unsicher / nicht behauptet:** Ob Docling (#3) oder VLM (#6) im konkreten Workload dominieren, ist **ungemessen** — bei Text-PDFs sicher nicht, bei Scan-PDFs möglicherweise doch. Das Latenz-Profiling (Sprint-130-Item 1) entscheidet das; die Struktur-Fixes #1/#2 lohnen sich unabhängig davon.

---

## D) Architektur-Kritik

### D.1 Ist der Aufbau prinzipiell sinnvoll? — **Ja, mit zwei Krankheiten.**

Das Grunddesign ist lehrbuchhaft solide und dem Problem angemessen: section-aware Chunking → typisierte ER-Extraction → Dual-Store (Vector+Graph) → intent-gewichtetes 4-Kanal-Retrieval mit RRF → gestreamte, zitierende Antwort. Die Query-Seite ist nach ADR-057 sogar vorbildlich aufgeräumt (27 s → <2 s durch Entfernen eines redundanten Pfads — genau die Operation, die die Ingestion-Seite jetzt braucht). Die zwei Krankheiten:

1. **Sedimentation statt Subtraktion.** Neue Sprint-Lösungen werden *neben* alte gelegt, alte werden selten entfernt. Messbare Symptome: Round-1+Round-2-Doppel-Extraction (Sprint 20/128-Pipeline neben Sprint-33/34-Loop im selben Node); drei Extraction-Pfade in einem Modul (SpaCy-First live, Legacy-Cascade schlafend, Gleaning/Windowed schlafend); zwei Intent-Klassifikatoren mit verschiedenen Taxonomien (router.py LLM-basiert, intent_classifier.py SetFit); vier ungenutzte Pipeline-/Parallelisierungs-Module.
2. **„Gebaut ≠ verdrahtet" ist systemisch, nicht episodisch.** Zum bekannten Bestand (EntityCanonicalizer, QLoRA-Track, community_search) kommen CGC-verifiziert hinzu: `extraction_worker_pool.py` (Importer: nur 2 Testfiles), `parallel_extractor.py` (nur Archiv-Benchmarks + Domain-`__init__`), `streaming_pipeline.py` (nur Domain-`__init__` + Tests), **HyDE** (nur via nicht-aufgerufenes `maximum_hybrid_search`). Das Bitterste daran: **Die Lösung für den Haupt-Latenz-Hotspot liegt seit Sprint 33/37 fertig im Repo** (Worker-Pool mit Semaphore-8, VRAM-Guard, Timeout-Handling) — die Live-Pipeline läuft sequenziell daran vorbei.

### D.2 Vier Stores — zusammen oder gegeneinander?

| Store | Ingestion-Rolle | Query-Rolle | Urteil |
|-------|----------------|-------------|--------|
| Qdrant | Chunk-Embeddings (dense+sparse) | 2 von 4 RRF-Kanälen | ✅ tragend |
| Neo4j | Entities/Relations/Sections/Communities/Domains | 2 von 4 RRF-Kanälen | ✅ tragend; komplementär zu Qdrant, echte Arbeitsteilung |
| Redis | Progress-Events, Feature-Flags | Query-Cache, Sessions | ✅ Infrastruktur, unkritisch |
| Graphiti | Temporal Memory Layer | **nur MEMORY-Intent** (memory_agent.py:49) | 🟡 schmalste Wertschöpfung pro Betriebskomplexität; kein Konflikt, aber ein vierter Store für einen Nischen-Pfad |

Kein „Gegeneinander" — die Chunk-ID-Vereinheitlichung Qdrant↔Neo4j (Sprint 42) ist sauber. Der einzige echte Konsistenz-Wackler ist der Qdrant-Domain-Backfill (graph_extraction.py:161–178): weil Embedding vor Domain-Klassifikation läuft, werden Payloads nachträglich gepatcht — mit **hartkodiertem Collection-Namen `documents_v1`** (:169) und synchronem QdrantClient im async-Kontext. Funktioniert, ist aber die Sorte Fix, die beim nächsten Collection-Rename lautlos bricht. Symptom des eigentlichen Problems: Domain-Klassifikation gehört *vor* den Embedding-Node, nicht in den Graph-Node.

### D.3 `extraction_service.py` (4 295 LOC)

CGC-Befund „keine God-Function" stimmt — aber das Modul ist ein **God-Module auf der Achsen-Ebene**: Es enthält (a) den Live-SpaCy-First-Pfad (~450 LOC), (b) den Legacy-Cascade-Pfad inkl. Rank-Logik, deren Ranks 2/3 seit 129.6h tot sind, (c) Gleaning-/Completeness-/Windowed-Maschinerie ohne Live-Caller, (d) Prompt-Definitionen, (e) Typ-Mapping-Verwaltung inkl. Neo4j-Refresh, (f) den vLLM-Capacity-Guard. Schätzung: **~50–60 % des Moduls sind im Default-Betrieb unerreichbar.** Die Zerlegung in kleine Funktionen ist gut; die Ansammlung dreier Generationen von Extraction-Strategien im selben File ist das Problem — jede Änderung am Live-Pfad erfordert Navigation durch zwei tote.

### D.4 „Multi-Agent" — ehrlich benannt

Der LangGraph ist ein **Router-Stern mit einem Retrieval-Schritt und einem Answer-Schritt** (graph.py:493–538). Seit ADR-057 den parallelen graph_query-Zweig deaktiviert hat, gibt es keine echte Agent-Kooperation, keine Iteration, keine Delegation im Standard-Pfad. Das ist **kein Mangel** — für die Aufgabe ist ein Stern richtig, und ADR-057 hat bewiesen, dass weniger Agenten = 13× schneller. Aber die Selbstbeschreibung „Multi-Agent-System" führt Planungs-Diskussionen in die Irre: Investitionen in „Agent-Orchestrierung" haben derzeit kein Substrat. Die Verzeichnisse `agents/hierarchy`, `agents/messaging`, `agents/routing`, `orchestrator/` wären ein eigenes Verdrahtungs-Audit wert.

### D.5 Kompensations-Layer unter dem RAGU-Befund

| Layer | Live-Status | Urteil |
|-------|-------------|--------|
| Gleaning (Entities+Relations) | **aus** (gleaning_steps=0, graph_extraction.py:495; keine Caller im SpaCy-First-Pfad) | Code löschen oder als Benchmark-Flag isolieren — aktuell nur Wartungslast |
| Cross-Sentence-Windows + Bisection | **nur Legacy-Pfad** (extraction_service.py:3766) | mit Legacy-Cascade zusammen entfernen |
| Cascade-Guard | nur Legacy-Pfad relevant | mit Cascade entfernen |
| Metadata-Blocklist | **live** (extraction_pipeline.py:239) | behalten — kostenlos, wirksam |
| Entity-Consolidation | **live** (extraction_service.py:2136) | behalten — CPU-only, sinnvoll |
| Completeness-Checks | Legacy-Pfad | entfernen |

Fazit gegenüber der RAGU-These: Die teuren Kompensationen sind im Live-Pfad bereits stillgelegt — was läuft, ist schlanker als die Sprint-Historie suggeriert. Das **eigentliche** Latenzproblem war nie die Kompensations-Kaskade, sondern Doppel-Extraction + Sequenzialität. Das relativiert auch Abschnitt 4.3 der RAGU-Analyse: der Call-Count ist tatsächlich der Treiber, aber er besteht zu einem Drittel aus schlicht **redundanter** Arbeit.

---

## E) Refactor-Prioritäten

| # | Refactor | Code | Warum jetzt | SP | Erwarteter Effekt | Risiko |
|---|----------|------|-------------|----|--------------------|--------|
| R1 | **Round-2-Relation-Loop löschen** (inkl. sleep(1.0)) | `graph_extraction.py:358–597` | Duplikat von Stage 3; produziert untypisierte Relationen neben ADR-060-typisierten; ~⅓ aller LLM-Calls | 3 | **Ingestion −30–40 %** (6–8 → ~4–5,5 min); −240 LOC; ein Extraction-Pfad statt zwei | niedrig — vorher 1 Benchmark-Doc mit/ohne vergleichen (Relation-Counts + Specificity); Round-1-Relationen sind die qualitativ besseren |
| R2 | **Chunk-Parallelisierung Round 1** | `extraction_pipeline.py:183–236` → `gather` + `Semaphore(settings.graph_extraction_workers)` | Config existiert (config.py:659); vLLM-A3B batcht ohnehin; alternativ Worker-Pool verdrahten (`extraction_worker_pool.py`, fertig inkl. VRAM-Guard) | 3 | **weitere −60–70 %** auf Extraction (nach R1: → ~1,5–2 min/doc) | mittel — vLLM-Sättigung beobachten; Semaphore=2 als konservativer Start |
| R3 | **`extraction_service.py` entkernen**: Legacy-Cascade, Gleaning, Windowed, Cascade-Guard raus | extraction_service.py :1862–2049, :2963–3715, :3860–4152 (nach Audit) | Nach R1/R2 ist der Live-Pfad klar; ~2 000 LOC schlafender Code blockiert jedes weitere Refactoring | 8 | −40–50 % Modulgröße; Extraction-Änderungen berühren nur noch einen Pfad | mittel — Testsuite referenziert Legacy-Pfade; Tests mit-migrieren |
| R4 | **Upload → 202 + Background-Job** | `retrieval.py:719–786`; Bausteine: `parallel_orchestrator.py`, `job_tracker.py` (admin_indexing nutzt beide schon) | 6–8-min-offene-Requests sind Proxy-Timeout-Roulette; Status-Endpoint existiert bereits (`/admin/upload-status/{id}`) | 3 | Robustheit; Voraussetzung für Multi-Doc-Batch-UX | niedrig — Frontend-Anpassung nötig |
| R5 | **Router-LLM durch SetFit ersetzen** | `router.py:171–216` → Mapping auf `intent_classifier.py`-SetFit | einziger vermeidbarer Query-Block (2–10 s im Auto-Modus); Classifier existiert, 20–50 ms | 2 | Auto-Modus-Queries −2–10 s; ein Intent-System statt zwei | niedrig — C-LARA-5-Klassen → 4 Routen mappen; LLM als Fallback bei low confidence behalten |
| R6 | **Wire-or-delete-Audit**: HyDE/maximum_hybrid_search, streaming/fast/refinement_pipeline, worker_pool, parallel_extractor, agents/hierarchy+messaging+orchestrator | div. | das Muster wächst schneller, als es abgebaut wird (4 Neufunde in dieser Analyse) | 5 | Ehrliche Codebase; verhindert die nächste „wir haben doch HyDE"-Fehlannahme | niedrig |
| R7 | **Domain-Klassifikation vor Embedding-Node ziehen** | `graph_extraction.py:93–226` → eigener Node vor `embedding` | eliminiert Qdrant-Backfill-Hack inkl. hartkodiertem `documents_v1` (:169) | 2 | Konsistenz; −90 LOC Sonderpfad | niedrig |
| R8 | **`dual_level_search.global_search` auf `community_search` umstellen oder community_search löschen** | dual_level_search.py:296–299 („simplified") | Carryover aus beiden Vor-Analysen; entscheidet, ob der Community-Stack Query-seitig überhaupt Ertrag liefert | 3 | Global-Search-Qualität ODER −1 Modul | mittel |

Empfohlene Reihenfolge: **R1 → R2 → R4 → R5** (alles vor R3, weil R3 vom stabilisierten Live-Pfad profitiert). R1+R2 zusammen sind 6 SP für eine ~4–5× schnellere Ingestion.

---

## F) Speedup-Roadmap (Sprint 130+): 6–8 min/doc → Ziel

### Freie Optimierungen (kein Modellwechsel, kein Qualitäts-Trade-off)

| Schritt | Maßnahme | Speedup (Faktor) | kumuliert (min/doc) |
|---------|----------|------------------|----------------------|
| 0 | **Erst messen**: Latenz-Profiling (Sprint-130-Item 1) — bestätigt die Call-Count-Hypothese und liefert die Baseline | — | 6–8 (Baseline) |
| 1 | **R1: Round-2 löschen** | ~1,4–1,6× | **~4–5,5** |
| 2 | **R2: Parallelisierung (Semaphore 4)** | ~2,5–3,5× auf Extraction | **~1,5–2,5** |
| 3 | Docling-Prewarm konsequent + VLM-Parallel-Flag an (falls Profiling Parse >30 s zeigt) | +10–30 s/doc | **~1–2** |

### Strukturelle Optimierungen (Qualitäts-Benchmark nötig)

| Schritt | Maßnahme | Speedup | Vorbedingung |
|---------|----------|---------|--------------|
| 4 | **Stage 2+3 zu einem Call fusionieren** (ein Prompt: Entities anreichern + Relationen, constrained auf SpaCy+LLM-Entity-Liste) — halbiert die verbleibenden Calls | ~1,5–1,8× → **~0,7–1,2 min/doc** | 15-Doc-Benchmark: Specificity/Counts dürfen nicht kippen; Vorsicht: das widerspricht dem RAGU-„two-stage constrained"-Muster — deshalb als Experiment, nicht als Default |
| 5 | **Pipeline-Streaming** (Extraction startet, sobald erste Chunks embedded sind) — `streaming_pipeline.py` reaktivieren oder LangGraph-Send-API | verdeckt Parse+Embed-Zeit (~20–60 s) | R1–R3 abgeschlossen |
| 6 | **Distilled 7–8B-Extraction-Modell** (Sprint-130-Item 4 aus der RAGU-Analyse) | pro Call ~1,2–2× (A3B ist schon klein!); Hauptertrag ist Qualität/RAM, nicht Latenz | 7B-vs-A3B-Benchmark |

**Realistisches Gesamtbild: 6–8 min → ~1,5–2,5 min mit Schritt 1–2 (6 SP, risikoarm), → unter 1 min nur mit Schritt 4/5 (strukturell).** Schritt 6 sollte aus Latenz-Sicht *nicht* als Speedup verkauft werden — der Compute pro Token ist beim A3B-MoE bereits klein; sein Wert liegt in Qualität (weniger Parse-Failures) und 28 GB freiem Unified Memory.

---

## Anhang: Verifikations-Log (CGC)

| Behauptung | Verfahren | Ergebnis |
|------------|-----------|----------|
| `extraction_worker_pool` ohne Live-Caller | CGC find_importers | nur `tests/integration/.../test_streaming_pipeline.py`, `tests/unit/.../test_extraction_worker_pool.py` ✅ |
| `parallel_extractor` ohne Live-Caller | CGC find_importers | nur `scripts/archive/benchmarks/*` (2×) + Domain-`__init__`-Re-Export ✅ |
| `streaming_pipeline` ohne Live-Caller | CGC find_importers | nur Domain-`__init__` + 2 Testfiles ✅ |
| `parallel_orchestrator` verdrahtet? | CGC find_importers | **ja**: `api/v1/admin_indexing.py` — Datei-Parallelität (3 Files) existiert im Admin-Bulk-Pfad; Chunk-Extraction bleibt auch dort sequenziell |
| HyDE-Verdrahtung | grep Importer von `hyde` | nur `maximum_hybrid_search.py`; das wiederum ohne Caller in api/agents ✅ |
| SpaCy-First ist Default | `extraction_cascade.py:218–225` | ✅ (Legacy nur via `AEGIS_USE_LEGACY_CASCADE=1`) |
| Community Detection default deferred | `config.py:705` (`scheduled`) | ✅ nightly 5-AM-Job |
| Reranker-Default | `config.py:513–524` | enabled=True, backend=sentence-transformers (Ollama-Sequenz-Schleife latent, nicht aktiv) |
