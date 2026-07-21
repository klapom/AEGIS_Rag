# ADR-065: Verdrahtung des Extraction-Worker-Pools in den Live-Ingestion-Pfad

## Status

**Proposed — Skizze** (2026-07-21)

## Kontext

### Der Bottleneck ist eine for-Schleife

Die Baseline-Messung (`BASELINE_INGESTION_2026-07-21.md`) zeigt: Ingestion ist **praktisch 100 % LLM-Wall** (21.9 min HTTP-Wall ≈ 22.4 min kumulierte LLM-Latenz über 57 Calls, Ø 23.6 s, p50 13.7 s, p95 59.3 s). Alle Calls laufen **strikt sequenziell**.

Die sequenzielle Verkettung entsteht an genau einer Stelle im Prod-Pfad:

```python
# src/components/graph_rag/extraction_pipeline.py:183-236
for chunk in chunks:
    ...
    entities, relations = await extractor.extract(   # :200 — 2 LLM-Calls pro Chunk,
        text=chunk_text, ...                          # SpaCy-First-Pipeline
    )                                                 # (extraction_service.py:2050)
```

Jeder `extractor.extract`-Aufruf macht intern 2 sequenzielle LLM-Calls (Entity-Enrichment `extraction_service.py:2298`, Timeout 120 s; Relation-Extraction `:2437`, Timeout 180 s). Kein `gather`, keine Semaphore, Concurrency = 1.

Die zweite sequenzielle Schleife — Round-2-Relation-Extraction (`graph_extraction.py:430-561`) — ist per **ADR-064** im Default deaktiviert und **nicht** Gegenstand dieses ADR (siehe „Interaktion mit ADR-064" unten).

### Der Worker-Pool existiert seit Sprint 37 — mit drei Überraschungen

`src/components/ingestion/extraction_worker_pool.py` (Sprint 37 Feature 37.2, 8 SP) liefert: N Worker an einer `asyncio.Queue`, globale `asyncio.Semaphore` für LLM-Calls, Per-Chunk-Timeout, Retry mit Exponential-Backoff, Progress-Callbacks, `AsyncGenerator`-Streaming der Ergebnisse. CGC-verifiziert (Assessment-Anhang) und per grep re-verifiziert 2026-07-21: **Importer sind ausschließlich 2 Testdateien** — kein Prod-Caller.

Ein ehrlicher Deep-Read vor der Verdrahtung findet drei Punkte, die der Modul-Docstring verschweigt:

1. **Der Extraction-Kern ist ein Platzhalter.** `_extract_entities_relations` (`extraction_worker_pool.py:403-459`) trägt einen `TODO: Replace with actual extraction service call` und ruft `RelationExtractor.extract(chunk_text, entities=[])` mit **leerer Entity-Liste** auf — `entities` bleibt immer `[]`. Der Pool würde „as is" verdrahtet **null Entities** extrahieren. Verdrahtung heißt zwingend: Extraction-Funktion injizieren.
2. **Der „VRAM-Guard" existiert nicht.** `vram_limit_mb: int = 5500` (`:83`, Kommentar „RTX 3060" — falsche Hardware) wird von keiner Zeile des Moduls gelesen. Der Docstring-Claim „VRAM-aware semaphore" ist die gewöhnliche Semaphore.
3. **Default-Concurrency 8 ist für DGX Spark falsch.** `max_concurrent_llm_calls: int = 8` (`:82`, und hartkodiert `:487`). Owner-Vorgabe (2026-07-21, Baseline-Report Ergänzung 12:15): auf DGX Spark sind **maximal 2–4 parallele LLM-Calls** sinnvoll — der KV-Cache pro Sequenz füllt bei 30–35B-Modellen (FP8/NVFP4) das Unified Memory; Semaphore-8 erzeugt vLLM-Queueing statt Speedup.

### Retry-/Timeout-Landschaft (Doppel-Ketten-Analyse)

| Ebene | Mechanismus | Gilt im Live-Pfad? |
|---|---|---|
| `extraction_service.py` SpaCy-First (`:2050`) | `asyncio.wait_for` 120 s (Stage 2) + 180 s (Stage 3); Timeout → **leeres Ergebnis, kein Retry** | ✅ ja |
| `extraction_service.py` tenacity-`@retry` (`:1944`, `:3072`, `:3421`) | exponential, `rank_config.max_retries` | ❌ nur Legacy-Cascade-/Gleaning-Pfade |
| `relation_extractor.py:260` tenacity | exponential | ❌ nur Round 2 (ADR-064: default aus) |
| Worker-Pool (`:300-401`) | Timeout 120 s + `max_retries=2`, exp. Backoff | — (bisher nie live) |

Zwei Konflikte bei naiver Verdrahtung:

- **Timeout-Konflikt:** Pool-Timeout 120 s < innere Worst-Case-Summe 120 s + 180 s = 300 s. Der Pool würde legitim langsame Chunks (p95 = 59.3 s *pro Call*, zwei Calls plus SpaCy/Konsolidierung) mitten im Flug abbrechen und neu starten — bis zu **3× Lastverstärkung** auf genau der Hardware, deren Parallelitäts-Decke das Problem ist.
- **Retry-Redundanz ist gering, aber asymmetrisch:** Der Live-Pfad rethrowt innere Timeouts nicht (leeres Ergebnis = „Erfolg" aus Pool-Sicht), Pool-Retries griffen also nur bei harten Exceptions — die der Sequenz-Pfad heute per `except: continue` (`extraction_pipeline.py:234-236`) **ohne Retry** überspringt. Pool-Retry würde das heutige Verhalten stillschweigend ändern und Fehler-Chunks verdreifachen.

### Reihenfolge-Sensitivität der Downstream-Stufen

Alle Doc-weiten Stufen laufen **nach** der Chunk-Schleife auf den aggregierten Listen — nicht interleaved: Blocklist-Filter (`extraction_pipeline.py:239`), Entity-Dedup/`semantic_deduplicator` (`:247-280`), Relation-Dedup (`:284-306`), `kg_hygiene` (`:326-354`), Neo4j-Store (`:427-448`). `kg_hygiene` ist per-Relation zustandslos. Die Dedup-Stufen können jedoch **listen-reihenfolge-abhängig** sein (Repräsentanten-Wahl „first wins"). Konsequenz für das Design: Ergebnisse werden nach der parallelen Phase **in ursprünglicher Chunk-Reihenfolge** re-assembliert — dann sind die Downstream-Inputs bit-identisch zur sequenziellen Ausführung (modulo LLM-Nichtdeterminismus), und keine der Stufen muss angefasst werden.

## Entscheidung

**Der Worker-Pool wird an genau einer Stelle verdrahtet: innerhalb von `extract_and_store_entities` (`extraction_pipeline.py:183-236`) ersetzt er die sequenzielle Chunk-Schleife. Dafür wird er in drei Punkten repariert: injizierbare Extract-Funktion, Concurrency-Default 4 (env-überschreibbar), Pool-Retry aus / Timeout 360 s.**

### 1. Verdrahtungsort: Option (a) — `extraction_pipeline.py` intern

| | (a) in `extract_and_store_entities` | (b) Batch-Split in `graph_extraction_node` (vor `:316`) |
|---|---|---|
| Invasivität | nur die Schleife `:183-236` ersetzt; Aggregation, Dedup, Hygiene, Store **unverändert** | `extract_and_store_entities` müsste in Extract-/Store-Hälften zerlegt oder pro Batch aufgerufen werden |
| Dedup-Semantik | Doc-weit erhalten (Dedup sieht alle Chunks) | Dedup liefe **pro Batch** → mehr Duplikate, andere Kanten-Zahlen — Semantik-Änderung |
| Nutznießer | alle Caller von `extract_and_store_entities` (Upload-Pfad, Admin-Bulk via `parallel_orchestrator` → dort multipliziert sich Datei- × Chunk-Parallelität, siehe Konsequenzen) | nur der LangGraph-Node |

**→ (a).** Minimal-invasiv, semantik-erhaltend, ein einziger Eingriffspunkt.

### 2. Concurrency-Konfiguration

Neue Env-Var **`AEGIS_EXTRACTION_LLM_CONCURRENCY`**, default **4** (neues Settings-Feld `extraction_llm_concurrency` in `config.py`, `ge=1`):

| Wert | Verhalten |
|---|---|
| `1` | sequenziell — verhaltensgleich zum heutigen Pfad; dient als **Rollback ohne Code-Change** |
| `2–4` | empfohlener Betriebsbereich DGX Spark (KV-Cache-Grenze) |
| `≥5` | erlaubt, aber Warnung ins Log: `extraction_concurrency_above_tested_limit … above tested DGX Spark limit (KV-cache), expect vLLM queueing` |

`WorkerPoolConfig.max_concurrent_llm_calls`-Default sinkt **8 → 4**; der hartkodierte `8` in `get_extraction_worker_pool` (`:487`) wird durch das Settings-Feld ersetzt. Semantik-Hinweis: die Semaphore begrenzt parallele *Chunks in Extraction*; da die 2 LLM-Calls pro Chunk intern sequenziell sind, ist das identisch mit max. parallelen LLM-Calls. `num_workers` wird an die Concurrency gekoppelt (getrennte Werte haben ohne echten VRAM-Guard keinen Nutzen).

**Embeddings sind ein separater, unabhängiger Hebel** und hier bewusst außen vor: der native BGE-M3-Pfad (`EMBEDDING_BACKEND=flag-embedding`, `ST_BATCH_SIZE=64`) batcht bereits in einem GPU-Forward-Pass; Embedding-Latenz war in der Baseline unter dem <5-%-Rauschen. Embedding-Concurrency (32+ wäre zulässig) ist kein Handlungsbedarf, nur ein dokumentierter zweiter Regler, falls je der Ollama-Fallback-Pfad aktiv würde.

### 3. Kein Feature-Flag — direkter Refactor

Anders als R1/ADR-064 ändert R2 **keine Extraktions-Semantik**: dieselben Prompts, dieselben Calls, dieselben Downstream-Inputs (dank Reihenfolge-Re-Assemblierung); nur die zeitliche Anordnung ändert sich. `AEGIS_EXTRACTION_LLM_CONCURRENCY=1` **ist** der Fallback — ein zusätzliches Bool-Flag würde nur die Testmatrix verdoppeln. Die Ablation (unten) bleibt trotzdem verpflichtend, weil „semantik-erhaltend" eine Behauptung ist, die gemessen gehört.

### 4. Fehlerbehandlung: Parität mit heute

- Pool wird mit **`max_retries=0`** verdrahtet (heutige Semantik: Fehler-Chunk wird geloggt und übersprungen, `extraction_pipeline.py:234-236`; kein Dead-Letter — den gibt es heute auch nicht).
- `ExtractionResult(success=False)` → Chunk wird geskippt, zählt in neues Stats-Feld `failed_chunks`; bei Fehlerquote > 20 % ein aggregiertes `WARNING`.
- Pool-Timeout **120 s → 360 s** (> innere 300-s-Worst-Case-Summe + Marge) — er ist damit reiner Havarie-Schutz gegen Hänger, nicht Teil der normalen Fehlerbehandlung. Die inneren `asyncio.wait_for`-Timeouts (120/180 s, → leeres Ergebnis) bleiben die maßgebliche Ebene.
- Der tote `vram_limit_mb`-Parameter wird **entfernt** (wire-or-delete auf Feld-Ebene).

## Alternativen (abgewogen)

| Option | Aufwand | Bewertung |
|---|---|---|
| **A. Pool reparieren + in `extract_and_store_entities` verdrahten (gewählt)** | 3 SP | ✅ löst den Hotspot #1 des Assessments; erfüllt wire-or-delete für das Sprint-37-Modul; Progress-Callbacks füttern die bestehenden `emit_progress`-Events |
| B. Schlankes `asyncio.Semaphore` + `gather` direkt in der Schleife, Pool löschen | 2 SP (+1 SP Lösch-PR) | ⚠️ ~15 LOC, weniger bewegliche Teile — technisch gleichwertig, da Pool-Retry/VRAM-Guard ohnehin deaktiviert/inexistent. Legitime Wahl, falls Review den Pool als Ballast einstuft; dann gehört `extraction_worker_pool.py` **gelöscht**, nicht liegengelassen |
| C. `parallel_orchestrator` (Sprint 33) statt Pool | — | ❌ orthogonal: parallelisiert **Dateien** (Admin-Bulk, `admin_indexing.py`), nicht Chunks innerhalb eines Dokuments; löst den 1-Doc-Upload-Fall nicht |
| D. `streaming_pipeline.py` reaktivieren (Pipeline-Überlappung) | ~8 SP | ❌ jetzt: strukturell größerer Umbau (Assessment-Hotspot #5, 🔴); sinnvoll erst nach R1/R2/R3 |
| E. Batch-Split im `graph_extraction_node` (Option (b) oben) | 4 SP | ❌ bricht Doc-weite Dedup-Semantik |

Zwischen A und B ist die Entscheidung bewusst knapp: A gewinnt wegen Progress-Streaming (Upload-Status-UX) und weil das Sprint-37-Modul damit erstmals seinen Zweck erfüllt. Wer B wählt, muss den Lösch-PR mitliefern.

## Konsequenzen

### Erwartet positiv
- **Doc 4 (13 KB): 17 min → ~4 min** (Baseline-korrigierte Erwartung, Semaphore-4). Kombiniert mit R1: **~3 min ≈ 5×** (siehe unten).
- Ideal-Speedup 4× wird real eher **~3–3.5×**: p95/p50 = 59.3/13.7 ≈ 4.3 → Straggler-Chunks dominieren das letzte Batch-Viertel (Amdahl auf Chunk-Ebene). Die Ablation misst den echten Faktor.
- Ein totes Modul wird Live-Code; Docstring-Fiktionen (VRAM-Guard, Stub-Extractor) verschwinden.

### Erwartet neutral / zu beobachten
- **vLLM-Sättigung:** 4 parallele Sequenzen erhöhen KV-Cache-Druck; vLLM-Log auf Preemption/Queueing beobachten (Ablation-Metrik). Konservativer Start mit `2` ist per Env-Var jederzeit möglich.
- **Admin-Bulk-Multiplikation:** `parallel_orchestrator` (3 Dateien parallel) × Chunk-Concurrency 4 = bis zu 12 gleichzeitige LLM-Calls im Admin-Bulk-Pfad. Für Sprint 130 akzeptiert (Admin-Pfad, bewusst ausgelöst), aber im Log sichtbar machen; saubere Lösung (globale Cross-Doc-Semaphore, z. B. prozessweite Semaphore statt pro-Pool-Instanz) als Follow-up-Kandidat notieren.
- **Log-Interleaving:** `extracting_chunk`/`chunk_extraction_complete`-Zeilen sind nicht mehr paarweise sequenziell; Log-basierte Auswertungen (wie das Baseline-Skript) müssen per `chunk_id` korrelieren.

### Erwartet negativ
- Peak-Memory der API steigt leicht (4 in-flight Responses statt 1) — vernachlässigbar gegen die vLLM-Seite.
- Nichtdeterminismus in der *Ausführungsreihenfolge* (nicht im Ergebnis, dank Re-Assemblierung) kann Race-Bugs in bisher nie parallel gelaufenem Code sichtbar machen (z. B. geteilter `extractor`-State). Der `ExtractionService` muss auf Instanz-State-Mutation im Extract-Pfad geprüft werden (Teil von PR-1-Review).

## Interaktion mit ADR-064 (R1)

Die beiden Refactors greifen an **disjunkten Call-Mengen** an und multiplizieren sich:

- **R1** (Round-2-Skip) *eliminiert* ~1/3 der LLM-Calls (gemessen −30–40 % Wall): Doc 4 17 → ~12 min.
- **R2** *komprimiert* die verbleibenden Round-1-Calls um Faktor ~3–3.5 (Semaphore-4 minus Straggler): ~12 → **~3–4 min**.
- Zusammen: **~5× auf Doc 4** (17 → ~3 min); Doc 5 (55 KB, heute Timeout > 20 min) → erwartet ~5–8 min.

**Warum die Reihenfolge R1 → R2 verteidigt bleibt:**
1. R2 parallelisiert **nur** die Round-1-Schleife. Die Round-2-Schleife (`graph_extraction.py:430-561`) bleibt sequenziell — R2 zuerst würde bei aktivem Round 2 also nur ~60 % der Wall angreifen und der Speedup bliebe bei ~1.7× statt ~3×.
2. R1 ist eine *Semantik*-Änderung (weniger Kanten) mit eigener Ablation; R2 ist *semantik-erhaltend*. Wer beide gleichzeitig scharf schaltet, kann einen Relation-Count-Drop nicht mehr attribuieren.
3. Die R2-Ablation ist auf der post-R1-Pipeline sauberer: weniger Calls → kürzere Messläufe, klarere Zuordnung.

## Ablation-Testplan (verpflichtend vor Merge)

**Setup:** identisch zur Baseline — dieselben 5 RAGAS-Phase-1-Docs (`measure_baseline.py`), frischer Namespace pro Lauf, externer Qwen-Endpoint wie Baseline (oder dokumentiert abweichend), ADR-064-Flag `false` (post-R1-Zustand als neue Referenz).

**Läufe (Concurrency-Matrix):**

| Lauf | `AEGIS_EXTRACTION_LLM_CONCURRENCY` | Zweck |
|---|---|---|
| K1 | 1 | Kontrolle: muss ≈ post-R1-Baseline sein (validiert „semantik-erhaltend" + kein Overhead) |
| K2 | 2 | konservativer Betriebspunkt |
| K4 | 4 | Default-Kandidat |
| K8 (optional) | 8 | Negativ-Beweis: erwartet ≈ K4 wegen KV-Cache-Queueing → validiert Default 4 empirisch |

**Metriken pro Lauf:**
1. Wall-Zeit pro Doc (primär Doc 4)
2. Entity-/Relation-Counts in Neo4j pro Doc + `failed_chunks`
3. vLLM-seitig: Queueing/Preemption-Indikatoren, p50/p95 der Einzel-Call-Latenz (steigt p95 stark, frisst Queueing den Speedup)
4. RAGAS-Retrieval auf ~10 Fragen (CP/CR)

**Pass/Fail:**
- ✅ K4: Doc 4 ≤ **6 min** (Ziel ~4 min; > 6 min → Straggler-/Queueing-Analyse vor Merge)
- ✅ K1 vs. K4: Entity-/Relation-Counts-Abweichung ≤ 10 % (LLM-Nichtdeterminismus-Budget), `failed_chunks` nicht erhöht
- ✅ RAGAS CP/CR: kein Abfall > 0.02 gegenüber K1
- ❌ Fail → Default per Env-Var auf 2 senken bzw. bei Count-Drift Reihenfolge-Re-Assemblierung debuggen

Ergebnis dokumentieren als `docs/analysis/ABLATION_R2_CONCURRENCY_2026-07-XX.md`.

## Rollback

1. **Betrieb:** `AEGIS_EXTRACTION_LLM_CONCURRENCY=1` + `docker compose … --force-recreate api` → sequenzielles Verhalten, kein Code-Change.
2. **Code:** ein PR, ein Revert; keine Datenmigration (Neo4j-/Qdrant-Schreibformate unverändert).
3. Kein Datenrisiko: fehlgeschlagene Chunks werden wie heute geskippt; parallele Läufe schreiben doc-weit aggregiert wie bisher (Store-Phase unverändert sequenziell nach der Extraction).

## Umsetzungsschritte

1. **PR-1 (3 SP): Pool-Reparatur + Verdrahtung**
   - `extraction_worker_pool.py`: Konstruktor-Param `extract_fn: Callable[[dict], Awaitable[tuple[list, list]]]`; Platzhalter `_extract_entities_relations` ersetzt; `max_concurrent_llm_calls`-Default 8 → 4 (aus Settings); `vram_limit_mb` + toten „RTX 3060"-Kommentar entfernen; `chunk_timeout_seconds` default 360; Warnung bei Concurrency ≥ 5
   - `config.py`: Feld `extraction_llm_concurrency` (Env `AEGIS_EXTRACTION_LLM_CONCURRENCY`, default 4, `ge=1`)
   - `extraction_pipeline.py:183-236`: Schleife → Pool; `extract_fn`-Closure über bestehenden `extractor.extract(text=…, document_id=f"{document_id}#{chunk_index}", domain=domain_id)`; Ergebnisse **in ursprünglicher Chunk-Reihenfolge** re-assemblieren, dann unveränderte Downstream-Kette; `failed_chunks` in Stats; Pool-`progress_callback` → bestehende `emit_progress`-Events
   - `graph_extraction.py` / `langgraph_pipeline.py`: **keine Änderung** (Eingriff liegt vollständig unterhalb von `extract_and_store_entities`)
   - Review-Punkt: `ExtractionService`-Instanz-State auf Parallel-Sicherheit prüfen (kein mutierender Shared State im Extract-Pfad)
   - Unit-Tests: Reihenfolge-Re-Assemblierung; Concurrency=1 ≡ sequenziell; Fehler-Chunk → Skip + Count; Warnung bei ≥ 5; bestehende `test_extraction_worker_pool.py` auf injizierte `extract_fn` migrieren
2. **Ablation-Messung (0.5 Tag):** Matrix K1/K2/K4(/K8), Report
3. **Doc-Updates:** `docs/CLAUDE_extended.md` + `docs/TECH_STACK.md` Env-Var-Sektion; `ADR_INDEX.md`
4. **Follow-up-Kandidaten (nicht Teil dieses ADR):** globale Cross-Doc-LLM-Semaphore (Admin-Bulk × Chunk-Parallelität); `parallel_extractor.py`-Löschung (R6 wire-or-delete); Embedding-Concurrency-Verifikation (`native_batch_embedding_success` im Log)

## Referenzen

- `docs/analysis/BASELINE_INGESTION_2026-07-21.md` — Baseline inkl. Ergänzung 12:15 (DGX-Spark-Concurrency-Grenze 2–4, korrigierte R2-Erwartung ~4×→ real ~3–3.5×)
- `docs/analysis/RAG_ARCHITECTURE_ASSESSMENT_2026-07-21.md` — Hotspot #1, Refactor R2, CGC-Verdrahtungs-Nachweise
- `docs/adr/ADR-064-round2-relation-extraction-flag.md` — R1; Reihenfolge-Argument oben
- ADR-059/ADR-062 — vLLM-Engine-Betrieb (Extraction-Route)
- `src/components/ingestion/extraction_worker_pool.py` — Sprint 37 Feature 37.2
- `src/components/graph_rag/extraction_pipeline.py:183-236` — der ersetzte Sequenz-Loop
- Owner-Vorgabe 2026-07-21: max 2–4 parallele LLM-Calls auf DGX Spark (KV-Cache); Embeddings 32+ unkritisch

---

## Anhang: Verdrahtungs-Skizze (Kern, kein finaler Patch)

```python
# extraction_pipeline.py — ersetzt die for-Schleife :183-236
async def _extract_chunk(chunk: dict[str, Any]) -> tuple[list, list]:
    return await extractor.extract(
        text=chunk["text"],
        document_id=f"{document_id}#{chunk['chunk_index']}",
        domain=domain_id,
    )

pool = get_extraction_worker_pool(extract_fn=_extract_chunk)  # Concurrency aus Settings/Env

results_by_id: dict[str, ExtractionResult] = {}
async for result in pool.process_chunks(valid_chunks, progress_callback=_on_progress):
    results_by_id[result.chunk_id] = result

failed_chunks = 0
for chunk in valid_chunks:                      # ← ursprüngliche Reihenfolge!
    result = results_by_id[chunk["chunk_id"]]
    if not result.success:
        failed_chunks += 1
        continue
    # chunk_id/document_id/chunk_index-Anreicherung wie bisher,
    # dann all_entities.extend / all_relations.extend / converted_chunks.append
```

```python
# extraction_worker_pool.py — Config-Änderung
@dataclass
class WorkerPoolConfig:
    num_workers: int = 4
    chunk_timeout_seconds: int = 360        # > innere 120+180 s Worst-Case
    max_retries: int = 0                    # innere Ebene (graceful degradation) ist maßgeblich
    max_concurrent_llm_calls: int = 4       # DGX Spark KV-Cache-Grenze (Owner 2026-07-21)
    # vram_limit_mb entfernt — wurde nie gelesen
```
