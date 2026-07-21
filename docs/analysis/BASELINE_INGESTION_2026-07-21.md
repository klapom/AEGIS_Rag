# AEGIS RAG — Ingestion Baseline-Messung

**Datum:** 2026-07-21
**Analyst:** Claude Opus 4.7 (Live-Messung + Log-Aggregation)
**Vorgänger:** RAGU-vs-AEGIS-Analyse, AEGIS-Honest-Assessment, RAG-Architecture-Assessment (alle im selben Ordner)
**Zweck:** Fables Call-Count-Herleitung (Ingestion ~85–90 % LLM-Wall aus ~150 sequenziellen Calls) durch reale Messung ablösen; harte Baseline-Zahl vor jeder R1/R2-Refactor-Investition.

---

## 0. Kurzfassung (drei Sätze)

- **Fables Prognose war konservativ.** Ein 13 KB reiner Text (~2 500 Wörter) braucht in der Live-Pipeline **16.8 Minuten**; ein 55 KB-Doc sprengt 20 Minuten Timeout. Die 6–8 min/Doc, die durch die Session zirkulierten, gelten bereits für kleine Text-Docs — nicht für 30-Seiten-PDFs.
- **Die Ingestion ist zu praktisch 100 % LLM-Wall-Time** (nicht 85 %). Über 4 fertige Docs: 21.9 min HTTP-Wall vs. 22.4 min kumulierte LLM-Call-Wall. Alle Nicht-LLM-Stages zusammen sind Rauschen.
- **Der Hebel liegt in Parallelisierung + Round-2-Löschung.** Bei p50 = 13.7 s / p95 = 59.3 s pro LLM-Call und strikt sequenzieller Verkettung ist der Ingestion-Weltraumaufzug quasi kein Modell-Problem, sondern ein Orchestrierungs-Problem. Der `extraction_worker_pool` steht seit Sprint 37 fertig — ungenutzt.

---

## 1. Setup

**Stack (heute für Messung hochgefahren):**
- `aegis-api` container (frisch aus Compose gebaut, `network_mode: host`, VLLM-Endpoint auf `secretary-vllm-qwen36:32000` umgelegt)
- `aegis-neo4j` (seit Feb im Prod-Betrieb)
- Qdrant (Container-Name `qdrant`, mit Prod-Volume `aegis_rag_qdrant_data`)
- Redis (via `mcp-gateway-redis-1`, shared)
- **Kein Ollama, kein Docling, kein aegis-vllm** (der eigene Nemotron NVFP4 nicht benötigt — Umleitung auf externen Qwen)

**Extraction-LLM für die Baseline:** `Qwen3.6-35B-A3B-FP8` auf Port 32000 (A3B-MoE, ~3B aktive Params, sub. Klaus' schlechte Nemotron-Erfahrung).

**Auth:** JWT via `POST /api/v1/retrieval/auth/token` mit `admin/admin123` (Default in `retrieval.py`).

**Namespace:** `baseline_2026-07-21` (cleanbar nachher).

**Endpoint:** `POST /api/v1/retrieval/upload` (Formfeld `namespace_id`) — dieser Pfad wird tatsächlich vom Frontend (`frontend/src/api/upload.ts:74`) benutzt. Der `/admin/upload-fast`-Endpoint ist im Live-Betrieb defekt (siehe Anhang A) und wird vom Frontend nicht angesprochen.

**Test-Docs:** 5 RAGAS-Phase-1-Contexts, verschiedene Größen (576 B bis 55 KB), reiner Text.

---

## 2. Live-Messung — Rohdaten

| # | Doc | Größe | HTTP-Wall | Bemerkung |
|---:|---|---:|---:|---|
| 1 | `ragas_phase1_0985_logqa_emanual5.txt` | 576 B | **32.0 s** | 1 Chunk |
| 2 | `ragas_phase1_2013_hotpot_5ae185ae.txt` | 2 273 B | **2.5 s** | **Ausreißer** — vermutlich Dedup-Cache-Hit (Hash bereits im Store) |
| 3 | `ragas_phase1_2690_hotpot_5ae2cd3b.txt` | 7 045 B | **267.0 s** = 4.4 min | ~2 Chunks |
| 4 | `ragas_phase1_0368_ragbench_techqaTR.txt` | 13 264 B | **1 010.6 s** = **16.8 min** | ~3 Chunks |
| 5 | `ragas_phase1_0370_ragbench_techqaTR.txt` | 55 580 B | **> 20 min (Timeout)** | Client-Timeout; Backend-Job läuft zum Report-Zeitpunkt noch (aktuell `chunk 3, window 20`) |

**Sofortiger Reality-Check:** Doc 4 hat 13 KB Text (~2 500 Wörter). Ein professioneller Rechtstext dieser Länge im Live-Endpoint = **17 Minuten Ingestion**. Das dokumentierte Architektur-Modell (`docs/ARCHITECTURE.md` Sprint 83.4: "Fast Upload 2–5 s + Background Refinement 30–60 s") ist entweder für andere Bedingungen dokumentiert oder überholt.

---

## 3. Aggregierte LLM-Call-Statistik

Aus `docker logs aegis-api --since 12m`:

| Metrik | Wert |
|---|---|
| Extraction-Requests (task_type=extraction) | 171 |
| LLM-Calls completed (llm_request_complete) | 57 |
| Summe LLM-Latenz | **1 346.9 s = 22.4 min** |
| Ø LLM-Call | **23.6 s** |
| p50 LLM-Call | 13.7 s |
| p95 LLM-Call | 59.3 s |
| Max LLM-Call | 84.3 s |

**Zentraler Vergleich:**
- HTTP-Wall über 4 fertige Docs (excl. Doc 5): **21.9 min**
- LLM-Wall über 57 Calls: **22.4 min**

Die kumulierte LLM-Zeit **überschreitet** die HTTP-Wall leicht (weil ein paar Calls in Doc 5 anteilig mit gezählt sind). Die Ingestion ist damit **praktisch 100 % LLM-Wall**, nicht 85 %. Kein anderer Layer (Docling, Chunking, Embedding, Neo4j-Write, Qdrant-Upload) trägt messbar bei.

**Konsequenz für Fables Refactor-Prioritäten:**
- R1 (Round-2 löschen) hebt weiterhin (–30–40 %), aber der eigentliche Skalierungshebel ist R2.
- R2 (Chunk-Parallelisierung via `extraction_worker_pool`, Semaphore 8) hätte hier direkt gemessene Wirkung: 22.4 min Wall bei 8-way-Parallelität → **≈ 3 min** (best case, ignoriert kleine Serialisierungs-Reste). Das ist ein **7× Speedup**.
- R1 + R2 kombiniert: 22.4 min → 15 min → **≈ 2 min**. Ein **>10× Speedup** aus 6 SP Refactor.

---

## 4. Nichtlinearität — die eigentliche Schadensfläche

| Doc-Größe | Zeit | s/Byte |
|---:|---:|---:|
| 576 B | 32 s | 55.6 ms/B |
| 7 045 B | 267 s | 37.9 ms/B |
| 13 264 B | 1 011 s | **76.2 ms/B** |
| 55 580 B | > 1 200 s | > 21.6 ms/B (nicht abgeschlossen) |

Wenn die Pipeline linear wäre, würde ein 13-KB-Doc gegenüber 7 KB **~2× so lange** brauchen. Tatsächlich braucht er **~3.8×** so lange. Der Grund ist die Kombination aus:

1. **Sequenzialität** (jeder Chunk wartet auf den vorigen)
2. **Round-2-Doppelextraction** (Fable-Befund, `graph_extraction.py:430-561`) — jeder Chunk wird zweifach durch die Relations-Pipeline geschickt
3. **Cross-Sentence-Windows** — pro Chunk werden mehrere Windows produziert (Log: `#3_window_20` für Doc 5 → Doc 5 hat allein Chunk 3 mit 20+ Windows). Jedes Fenster ist ein zusätzlicher sequenzieller LLM-Call.

Das erklärt, warum ein 13-KB-Text-Doc 17 Minuten braucht, ein PDF mit 30 Seiten aber nur 6–8 Minuten (Fable-Schätzung): **die Fenster-Explosion dominiert**, und die ist nicht sauber Größen-linear.

---

## 5. Beobachtete Sub-Befunde während der Messung

### 5.1 Live-Bug: `/api/v1/admin/upload-fast` (Fast Upload)

Erste Messrunde ging an den Fast-Upload-Endpoint. Alle 5 Uploads scheiterten mit HTTP 500:

```
File "/app/src/components/ingestion/fast_pipeline.py", line 190
AttributeError: 'str' object has no attribute 'exists'
```

`fast_pipeline.py:190` gibt `str(file_path)` an `DoclingClient.parse_document(file_path: Path)`. Der DoclingClient ruft intern `file_path.exists()` → crash. Trivialer 1-Zeilen-Fix.

Der Fast-Upload-Endpoint (Sprint 83 Feature 83.4) wird vom Frontend **nicht** benutzt (`frontend/src/api/upload.ts` ruft nur `/api/v1/retrieval/upload`) — deshalb ist der Bug im Live-Betrieb unbemerkt geblieben. Sprint-130-Kandidat: entweder wire-or-delete oder fixen und verdrahten.

### 5.2 Log-Legacy nach Kaskaden-Removal (Sprint 129.6h)

Live-Log-Zeile während der Messung:
```
relationships_extracted_with_llm ... model=nemotron-3-nano:128k rank=1 ...
```

Aber der tatsächliche Call ging an Qwen (parallele Zeile: `llm_cost_summary ... model=qwen36-35b`). Die Log-Zeile in `extraction_service.py` liest ein statisches Modell-Feld aus der Cascade-Config, das nach Sprint 129.6h nicht mit dem aktiven LLM synchronisiert wurde. Kosmetisch, aber ein weiterer Beleg für den "Kaskaden-Entkernungs"-Cleanup.

### 5.3 Doc 2 als Cache-Hit-Anomalie (2.5 s)

Doc 2 lief in 2.5 s durch — bei 2.3 KB Text passt das zu **einer** LLM-Call-Latenz plus Chunking. Möglich: `Fast-Path` bei doppeltem File-Hash, oder Format-Router hat den txt-Content erkannt und übersprungen. Wert für die Baseline: **niedrigster realistischer Datenpunkt**, aber nicht repräsentativ für Erstsicht.

### 5.4 Entity-Name-Truncation (`max_words=4`)

Beobachtete Warnings im Log:
```
entity_name_truncated ... original="Tivoli Management Services server components" ... truncated="Tivoli Management Services server"
entity_name_truncated ... original="Version 6.2.3 Fixpack 1 or later" ... truncated="Version 6.2.3 Fixpack 1"
entity_name_truncated ... original="Self-describing agent (SDA) application support installation" ... truncated="Self-describing agent (SDA) application"
```

Ein hartkodierter `max_words=4`-Cap verstümmelt legitime Entity-Namen. Für Domain wie `techqaTR` (IBM-Tivoli-Dokumentation) sind das **produktive Extraktions-Verluste**. Nicht Sprint-130-relevant, aber im Backlog vermerken.

---

## 6. Was diese Messung *nicht* misst — und warum das ok ist

- **Stage-detaillierte Aufteilung** (Chunking vs. Embedding vs. Extraction vs. Community-Detection): der aktuelle Log-Level gibt keine sauberen per-Stage-Marker, die ich pro Doc zuordnen kann. Da Extraction aber **>95 % der Wall-Zeit** ist (57 Calls × Ø 23.6 s = 22.4 min bei 21.9 min HTTP-Wall), ist die Detail-Aufschlüsselung nachrangig.
- **PDF/Docling-Pfad**: TXT umgeht Docling. Für PDF-Ingestion ist zusätzlich Docling-Latenz (Fables Schätzung 20–90 s pro Doc) einzurechnen — spielt aber neben 20+ min Extraction keine Rolle.
- **Community-Detection**: default `GRAPH_COMMUNITY_DETECTION_MODE=scheduled` — läuft nicht während Ingestion. Fables Befund bestätigt.
- **Docling-VLM / Tabellen-Extraktion**: nicht relevant für Text-Docs.

Die Messung ist damit für die **Extraction-getriebene Frage** (R1/R2/Distillation) valide. Für PDF-spezifische Fragen muss man 30–90 s pro Doc addieren.

---

## 7. Revidierte Sprint-130-Erwartung (gemessen statt geschätzt)

| Refactor | Aufwand | Erwarteter Effekt (gemessen-basiert) |
|---|---:|---|
| **R1** (Round-2 in `graph_extraction.py:430-561` löschen) | 3 SP | **−30–40 %** LLM-Wall → **~14 min** für Doc 4 (statt 17) |
| **R2** (Chunk-Parallelisierung via `extraction_worker_pool`, Semaphore 8) | 3 SP | **7× Speedup auf LLM-Wall** → Doc 4: **~2 min** (statt 17) |
| **R1 + R2 kombiniert** | 6 SP | **≥10× Speedup** → Doc 4: **~1.5 min** (statt 17), Doc 5 (55 KB): **~5–8 min** (statt >20) |
| **R4** (Upload auf 202 + Job-ID) | 2 SP | UX-Instant-Response (Wall-Zeit unverändert, aber User sieht 200 statt Timeout) |
| **7B-Distillation** (RAGU-Idee, gestrandete QLoRA sanieren) | 8 SP | LLM-Latenz p50: 13.7 s → ~4–6 s = **~2× auf LLM-Wall** (unabhängig von R1/R2) |

**Realistisches Sprint-130-Ziel (nur R1+R2, ohne Distillation):** Doc 4 von 17 min → 1.5 min = **~11× Speedup**. Kombiniert mit Distillation (mittelfristig): weitere **~2×**. Endziel: ein 13-KB-Doc in **<1 min** ingestierbar.

---

## 8. Nächster Schritt

Der Messwert ist da. **R1 (Round-2 löschen)** ist der klare erste Move — 3 SP, niedriges Risiko, +30–40 % sofort. Kann nach diesem Report direkt geplant werden.

**Vor R1:** eine 2. Baseline-Messung mit **denselben 5 Docs** durchführen, um Doc 2 (Cache-Hit) zu re-messen (2. Upload sollte ähnliche Zeit haben) und die Doc-5-Timing zu ergänzen (Backend-Job läuft zum Report-Zeitpunkt noch).

**Rollback-Zustand nach Messung:**
- `.env` restaurierbar aus `.env.nemotron-backup-20260721_114928`
- `docker-compose.dgx-spark.yml` restaurierbar aus `docker-compose.dgx-spark.yml.baseline-backup-20260721_115505`
- Baseline-Docs in Qdrant im Namespace `baseline_2026-07-21` cleanbar via Admin-API
- `gemma-judge-e4b` container ist gestoppt — kann via `docker start gemma-judge-e4b` wieder hochgefahren werden

---

## Anhang A — Bug-Beleg `/admin/upload-fast`

Log-Auszug aus dem gescheiterten ersten Mess-Run:
```
INFO fast_upload_start ... document_id=doc_c1573080a3627e61 ...
INFO fast_upload_parsing_start ... document_id=doc_c1573080a3627e61 ...
ERROR fast_upload_failed ... error='str' object has no attribute 'exists' ...
Traceback (most recent call last):
  File "/app/src/components/ingestion/fast_pipeline.py", line 190, in run_fast_upload
AttributeError: 'str' object has no attribute 'exists'
```

Root Cause: `docling_client.parse_document(str(file_path))` — der DoclingClient-Signature erwartet `file_path: Path`, ruft intern `file_path.exists()`.

Fix (untested, one-liner):
```python
# fast_pipeline.py:190
- parsed_doc = await docling_client.parse_document(str(file_path))
+ parsed_doc = await docling_client.parse_document(file_path)
```

## Anhang B — Rohdaten

- Mess-Skript: `/tmp/claude-1000/-home-admin-projects-aegisrag/5432c0ae-fed3-40c4-b743-862093c2a475/scratchpad/baseline_2026-07-21/measure_baseline.py`
- Run-Logs: `run.log` (Fast-Upload-Fehlversuch), `run2.log` (Auth-Fehlversuch), `run3.log` (erfolgreicher Run)
- Ergebnis-JSONs: `results_20260721_*.json` im selben Ordner
- Bereinigter API-Log-Extract (12 min): `/tmp/aegis-log.txt`

---

## Ergänzung 12:15 — DGX-Spark-Concurrency-Realität

Rückmeldung vom Owner (2026-07-21 12:14): **auf DGX Spark liegt die maximale LLM-Parallelität bei 2–4 Calls**, nicht bei 8. Grund: KV-Cache-Speicher pro Sequenz füllt das Unified Memory bei größeren Modellen (30–35 B FP8/NVFP4) schnell. Ein Semaphore-8 würde vLLM-Queueing verursachen, nicht echten Speedup. Embeddings dagegen gehen deutlich höher parallel (BGE-M3 batched sehr gut, `ST_BATCH_SIZE=64` heute).

### Korrektur der R2-Erwartung

**Nicht 7× Speedup, sondern ~4×** (mit `max_concurrent_llm_calls=4` statt Default 8).

| Refactor | SP | Erwartung (korrigiert) |
|---|---:|---|
| R1 (Round-2 löschen) | 3 | Doc 4: 17 min → **~12 min** |
| R2 (Semaphore-4, nicht -8) | 3 | Doc 4: 17 min → **~4 min** (nicht ~2 min) |
| **R1+R2** | 6 | Doc 4: 17 min → **~3 min = ~5× Speedup** (nicht ~11×) |
| 7B-Distillation | 8 | LLM-p50 13.7 s → ~4–6 s = weitere ~2× |

Der `extraction_worker_pool.py:129` hat `max_concurrent_llm_calls: int = 8` als Default — bei R2-Verdrahtung muss dieser Default auf 4 gesenkt oder als Env-Var exportiert werden.

### Embedding als zweiter, unabhängiger Hebel

CGC + Code-Read zeigen zwei Embedding-Pfade in `src/components/shared/embedding_service.py`:

1. **Native BGE-M3-Pfad** (`EMBEDDING_BACKEND=flag-embedding`, aktuelle Prod-Config): batched alle Chunks in einem GPU-Forward-Pass. **Vermutlich schon effizient**, kein Hebel.
2. **Ollama-Backend-Pfad** (Fallback): Semaphore-basiert mit `asyncio.gather` (Zeile 467–477). Semaphore ist auf `max_concurrent`-Parameter gekoppelt, historischer Default möglicherweise klein.

**Sprint-130-Item ergänzen (Priorität niedrig, ~1 SP):** verifizieren dass native BGE-M3 aktiv ist (Log: `native_batch_embedding_success` sollte auftauchen). Falls Ollama-Fallback aktiv wäre, `max_concurrent` auf 32+ hochziehen — Embeddings sind rechnerisch billig, das kostet nichts.

Aus der Baseline-Log-Analyse: Embedding-Latenz war unter den <5 % Rauschen (LLM-Wall 22.4 min ≈ HTTP-Wall 21.9 min, kein Puffer für signifikante Embedding-Zeit) — der native Pfad ist mit hoher Wahrscheinlichkeit aktiv. Der Refactor ist damit prophylaktisch, kein Latenz-Gewinn erwartet.

### Konsequenz für die Priorisierung

R1+R2 bleiben trotz halbiertem Speedup **die klar billigsten Hebel** (6 SP für ~5× Speedup). Distillation als Latenz-Hebel wird durch die 2–4-Grenze **noch weniger attraktiv** — sie verkürzt einzelne Calls, aber die Parallelitäts-Decke bleibt hart. Distillation-Wert liegt damit noch stärker im **Qualitäts-Argument (RAGU-These), nicht Latenz**.

Actionable-Reihenfolge unverändert: **R1 → R2 (mit Semaphore-4) → dann Fable's übrige Items**.

---

## Anhang C — Compose-Änderungen für die Messung

`docker-compose.dgx-spark.yml` wurde temporär gepatched:
1. `api.depends_on` gekürzt auf nur `neo4j` (ollama/qdrant/redis/prometheus entfernt)
2. `network_mode: host` hinzugefügt, `networks:` entfernt
3. `VLLM_BASE_URL`, `VLLM_MODEL`, `QDRANT_HOST`, `NEO4J_URI`, `REDIS_HOST`, `REDIS_MEMORY_URL` auf `localhost`/externen Qwen-Endpoint umgeleitet
4. `VLLM_ENABLED=true` forciert

Alle Änderungen sind rückgängig durch Restore aus dem Backup. Für die produktive Nemotron-Konfiguration reicht:
```bash
cp docker-compose.dgx-spark.yml.baseline-backup-20260721_115505 docker-compose.dgx-spark.yml
cp .env.nemotron-backup-20260721_114928 .env
docker compose -f docker-compose.dgx-spark.yml up -d --force-recreate api
```
