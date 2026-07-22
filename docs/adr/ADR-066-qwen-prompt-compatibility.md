# ADR-066: ExtractionService-Prompt-Kompatibilität mit Qwen (Bug A Fix)

## Status

**Proposed — Draft für Fable-Critic-Gate** (2026-07-22)

## Kontext

Nach der Umstellung des Ingestion-vLLM-Endpoints von **Nemotron-3-Nano-30B-A3B-NVFP4** auf **Qwen3.6-35B-A3B-FP8** (Klaus's Präferenz nach schlechten Nemotron-Erfahrungen, siehe supermemory `feedback_qwen_over_nemotron`) produziert `ExtractionService` in cold-cache Läufen **0 Entities und 0 Relations** für die meisten Docs. Der Bug wurde am 2026-07-21 während der ADR-064-Ablation entdeckt — vorher unbemerkt, weil ein Zombie-Cache (Bug B, siehe [[bug_prompt_cache_model_blindness]]) alte Nemotron-Responses ausgeliefert hat.

### Verifiziertes Verhalten (aus `docs/analysis/BASELINE_ROUND2_ABLATION_2026-07-21.md` Anhang, Truly-Cold-Cache Rerun 22:58)

| Doc | Größe | Wall (Qwen cold-cache) | M1 (unique (source,target)) | Notiz |
|---|---:|---:|---:|---|
| 1 | 576 B | 19.2 s | 0 | 0 aus Round 1 UND Round 2 |
| 2 | 2.3 KB | 8.2 s | 0 | 0 aus beiden Rounds |
| 3 | 7 KB | 15.3 s | 0 | 0 aus beiden Rounds |
| 4 | 13 KB | 21.4 s | 0 (off) / 7 (on) | **Round 2 findet noch, Round 1 nicht** |
| 5 | 55 KB | 71.4 s | 0 (off) / 1 (on) | Round-2-Only |

Log-Beleg aus `docker logs aegis-api` für Doc 5:
- 11 chunks, `entities_extracted=0`, `relations_extracted=0`, `total_relations_stored=0`
- **Aber** `graph_ms=69494`, `per_item_avg_ms=6220` — 11 LLM-Calls à 6.2 s wurden gemacht, jeder gab leer zurück.

**Nemotron-Baseline (zum Vergleich, warm-cache):** Doc 4 = 395 Round-1-Relations, 67 % typisiert. Der DSPy-Prompt-Erfolg (+22 % Entity-F1, +30 % Relation-F1 — dokumentiert in `src/prompts/extraction_prompts.py:14-15`) war Nemotron-spezifisch.

### Auswirkung

- **Prod-Deploy-Blocker.** Ohne Fix bricht die Ingestion nach Cache-Ablauf komplett — sichtbar nur, wenn AEGIS-`prompt_cache` in Redis geleert wird (aktuell ~338 Zombie-Keys aus Nemotron-Ära).
- **PR-2 zu ADR-064 blockiert** (Round-2-Hard-Delete). Ohne Round-2-Fallback und mit gebrochenem Round 1 wäre nach PR-2-Merge die Extraktion faktisch tot.
- **Description-Konsolidierung (Sprint-130 Item 2) blockiert**, da sie eine funktionierende typisierte Round-1-Extraktion voraussetzt.

## Root Cause Analysis

Vier Kandidaten wurden untersucht (`extraction_service.py` = 4295 Zeilen, `extraction_prompts.py` = 592 Zeilen). Rankings nach empirischer Load-Bearing-Wahrscheinlichkeit:

### Load-Bearing (belegt)

**R1. DSPy-MIPROv2-Prompts sind auf Nemotron/gptoss trainiert** (`src/prompts/extraction_prompts.py:186` `DSPY_OPTIMIZED_ENTITY_PROMPT`, `:221` `DSPY_OPTIMIZED_RELATION_PROMPT`).
- Quelldatei laut Kommentar Zeile 183–184: `data/dspy_prompts/pipeline_gptoss/pipeline_extraction_20260113_060510.json`
- Default-Selection: `USE_DSPY_PROMPTS = os.environ.get("AEGIS_USE_LEGACY_PROMPTS", "0") != "1"` → default `True`
- Genutzt an Callsite `extraction_service.py:2739` (DSPy-Entity) und im Domain-Enriched-Builder `extraction_prompts.py:425` (Fallback für keine Domain-Sub-Types)
- MIPROv2-Optimierung ist **modell-spezifisch** — die Instruction-Formulierung, Beispiel-Selektion und JSON-Format-Marker wurden für die Nemotron-Response-Distribution gefittet. Nicht portabel.

**R2. `RELATION_EXTRACTION_FROM_ENTITIES_PROMPT`** (`extraction_prompts.py:316`)
- Genutzt an Callsite `extraction_service.py:2413` (`_pipeline_stage3_relation_extraction`)
- SpaCy-First-Pipeline, ADR-060-typisiert. Sehr ausführlich strukturiert mit `---Role---`, `---Entities---`, `---Output Format---`, `---22 Universal Relation Types---`. Diese XML-artigen Section-Marker sind Nemotron-optimiert; Qwen3 mit thinking-mode versteht sie zwar, aber die Response-Formatierung weicht ab.

**R3. `_repair_json_string` / `_parse_json_response`** (`extraction_service.py:1059` und `:1605`)
- Der Parser hat drei Strategien: direktes `json.loads`, Repair-Pass, Individual-Object-Extraction (`_extract_json_objects_individually` :1195).
- **Verifikationsbedarf:** Qwen3 hat einen **thinking-mode-Default** — Response kann mit `<think>...</think>`-Block anfangen, gefolgt vom eigentlichen JSON. Der aktuelle Parser strippt diesen nicht. Wenn 6.2 s pro Call verbraucht werden (Doc 5) aber 0 Entities zurückkommen, ist ein Parser-Total-Fail plausibel. **Muss durch Critic mit einem echten Qwen-Raw-Response verifiziert werden.**

### Incidental (nicht die Ursache)

**R4. Hardcoded `model="nemotron-3-nano:latest"`** (`extraction_service.py:2231`)
- Nur im SpaCy-NER-Fallback-Pfad (`_extract_entities_llm_only` mit expliziter Model-Override). Wird nur getroffen, wenn `spacy_ner_failed`. Nicht die primäre Failure-Path.
- Der Docstring bei `:1586` erkennt das Anti-Pattern an (*"Returns 'qwen3:32b' from Admin UI config, not hardcoded 'nemotron-3-nano'"*) — die zentrale Model-Selection ist Env-driven, dieser Override wurde vergessen.

**R5. LLM-Proxy-Routing.** `AegisLLMProxy._route_task` (`aegis_llm_proxy.py:813`) nutzt `self._vllm_model` aus `settings.vllm_model` (= Env `VLLM_MODEL`). Modell-agnostisch. `LLMTask.model_override` (Callsite `:2739`) erlaubt Per-Call-Override. **Der Proxy ist nicht Teil des Bugs.**

## Optionen

### A) Model-agnostischer Prompt-Rewrite (empfohlen für Critic)

Ersetzt `DSPY_OPTIMIZED_*_PROMPT` durch überarbeitete generische Prompts, die auf **Format-Robustheit** und **explizite JSON-Schema-Spezifikation** setzen. Details:
- Klarer Output-Contract: `Return ONLY a raw JSON array. Do NOT include markdown fences, explanatory text, or thinking tags.`
- Optional 1–2 Few-Shot-Beispiele pro Prompt (schon vorhanden, aber Format anpassen).
- Prompts an DSPy-Struktur-Erfahrungen orientieren, aber nicht MIPROv2-optimieren (Modell-neutral).
- Feature-Flag: `AEGIS_USE_LEGACY_PROMPTS=1` → alte `GENERIC_*_EXTRACTION_PROMPT` als Rollback.

**Aufwand:** 5 SP (Prompt-Design 2 SP, Regression-Tests 2 SP, Ablation 1 SP)
**Rollback:** `AEGIS_USE_LEGACY_PROMPTS=1` → alte Prompts, dann `docker compose ... up -d --force-recreate api`.
**Blast-Radius:** ExtractionService only; RelationExtractor (Round-2) unberührt. DSPy-trained-per-Domain-Prompts (Priority 1 in `get_extraction_prompts`) bleiben intakt für Domains, die trainiert sind.
**Pros:** Ein Prompt-Set zu pflegen, testbar in Isolation, honoriert `AEGIS_USE_LEGACY_PROMPTS`-Flag-Vertrag.
**Cons:** Verliert den DSPy-behaupteten +22 %/+30 % F1-Gain für Nemotron. Aber: dieser Gain gilt nachweislich nicht für Qwen, und Klaus's Präferenz ist Qwen.

### B) Model-conditional Prompt Selection

Neue Env-Var `AEGIS_LLM_MODEL_FAMILY` (`nemotron|qwen|generic`), Prompt-Registry per Family. DSPy-Nemotron bleibt, neue DSPy-Qwen-Prompts würden erst nach DSPy-Trainings-Run existieren.

**Aufwand:** 8 SP (Registry 2 SP, DSPy-Training auf Qwen 4 SP, Tests 2 SP)
**Rollback:** Env-Var umsetzen.
**Blast-Radius:** ExtractionService + neuer Env-Vertrag + Trainings-Pipeline.
**Pros:** Optimiert pro Model.
**Cons:** Doppelte Prompt-Pflege, DSPy-Trainings-Runs auf DGX für jedes neue Modell nötig, mehr Ops-Overhead. Nicht Sprint-130-freundlich.

### C) Rollback auf Nemotron

`VLLM_MODEL=nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4` zurückrollen, Bug B-Fix separat.

**Aufwand:** 1 SP.
**Rollback:** trivial.
**Blast-Radius:** Auch der shared `secretary-vllm-qwen36`-Endpoint hostet für Klaus's `pommer-agents` mit Qwen; der Rollback bricht dort ggf. Erwartungen.
**Pros:** Sofortige Wiederherstellung der Prod-Extraktion.
**Cons:** **Widerspricht Klaus's dokumentierter Präferenz** (`feedback_qwen_over_nemotron` in supermemory). Nur als Notfall-Fallback vertretbar.

### D) JSON-Parser-Hardening für Qwen thinking-mode

Erweitert `_repair_json_string` (:1059) um einen `<think>...</think>`-Stripper und robuster JSON-Boundary-Detection.

**Aufwand:** 2 SP (Parser-Änderung 0.5 SP, Regression-Tests 1.5 SP)
**Rollback:** Reverten des Parser-Commits.
**Blast-Radius:** Alle Parser-Callsites in `extraction_service.py` (~5 Aufrufer). Kein Prompt-Change.
**Pros:** Wenn R3 die tatsächliche Ursache ist, adressiert D allein 100 % des Bugs. Reversibel und low-risk.
**Cons:** Wenn R1/R2 auch load-bearing ist, hilft D allein nicht — Qwen produziert dann kein JSON, sondern narrative Text.

## Präliminäre Empfehlung (für Critic zu challenge)

**A + D kombiniert (7 SP).** Reasoning:
1. R3 (Parser vs. Qwen-Output) muss **empirisch** geprüft werden — der Critic sollte einen echten Qwen-Raw-Response beschaffen (aus `docker logs` einer cold-cache Ingestion oder durch direktes Chatten mit dem Endpoint). Wenn `<think>`-Blöcke sichtbar sind, ist D notwendig unabhängig von A.
2. Selbst wenn D das Sofortproblem löst, bleibt R1 (Model-spezifische MIPROv2-Optimierung) eine tickende Fragilität. A macht das System robust.
3. C ist Backup, wenn A+D den Sprint sprengt.

Nicht empfohlen: B allein (Ops-Overhead), C allein (widerspricht Klaus's Präferenz).

## Akzeptanz-Kriterien (Draft — Critic verfeinert)

Alle Messungen mit **truly-cold-cache** (vLLM-Restart + Redis `prompt_cache*` flush):

**AC-1: Round-1-Extraktion produziert typisierte Entities.**
- Doc 4 (13 KB, `ragbench_techqaTR`): ≥ **45 unique entities** (Nemotron-Baseline war 60–100, 45 = ~70 % als konservatives Ziel).
- Doc 5 (55 KB): ≥ **200 unique entities** (Nemotron-Baseline war 1746, 200 = ~11 % als absolute Untergrenze).

**AC-2: Round-1-Extraktion produziert typisierte Relations.**
- Doc 4: ≥ **30 unique (source, target)** pairs.
- Typisierungsanteil (`relation_type ≠ 'RELATED_TO'`): ≥ **50 %**.

**AC-3: JSON-Parse-Error-Rate ≤ 5 %.**
- Metrik aus `_parse_json_response`: Anzahl `json_parse_failed_all_strategies` ÷ total LLM-Calls.
- Aktuell (cold-cache Qwen): ~100 %.

**AC-4: Keine Test-Regression.**
- `pytest tests/unit/components/graph_rag/` grün nach Änderungen.
- `pytest tests/unit/prompts/` grün.
- Bestehende DSPy-Prompt-Tests (`tests/unit/prompts/test_extraction_prompts.py`) bleiben grün ODER werden bewusst angepasst mit Commit-Message-Begründung.

**AC-5: Rollback-Pfad verifiziert.**
- Setzen `AEGIS_USE_LEGACY_PROMPTS=1` + `docker compose ... up -d --force-recreate api` → alte Legacy-Prompts aktiv (verifiziert durch Log-Zeile oder Test).
- Wechsel zurück auf Default (Env unset) → neue Prompts aktiv.

**AC-6: Nemotron-Kompatibilität bleibt.**
- Nach Prompt-Rewrite: derselbe cold-cache Test mit `VLLM_MODEL=nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-NVFP4` liefert ebenfalls ≥ AC-1/AC-2-Zahlen für Doc 4.
- Grund: A darf keine Regression auf Nemotron einführen (Rollback-Sicherheit).

## Out of Scope

- **Prompt-Cache Model-Segment** — separate Sprint-130 Task #3 [[bug_prompt_cache_model_blindness]], parallel in Worktree `bug-b`.
- **ADR-065 R2 Worker-Pool Wire-up** — blockiert durch dieses ADR, kommt danach.
- **Description-Konsolidierung** (Sprint-130 Item 2) — separate Task, blockiert durch dieses ADR.
- **Hardcoded `nemotron-3-nano:latest` in `extraction_service.py:2231`** — bewusst NICHT im Scope; SpaCy-Fallback-Pfad wird selten getroffen. Wenn Critic das reinnehmen möchte: Aufwand +0.5 SP, aber unabhängig zu fixen.
- **DSPy-Trainings-Pipeline** (Distillation-Track, Sprint-130 Item 4b) — komplett orthogonal.
- **RelationExtractor / Round-2-Prompts** — laut Ablation-Beleg funktionieren die noch mit Qwen. Nicht anfassen.

## Offene Fragen für Fable-Critic-Gate

**Q1. Ist R3 (Parser vs. Qwen `<think>`-Output) tatsächlich load-bearing?**
Critic sollte einen realen Qwen-Raw-Response beschaffen (ein direkter POST an `192.168.178.10:32000` mit einem der DSPy-Prompts) und den Parser dagegen laufen lassen. Wenn ja → D obligatorisch. Wenn nein → A allein reicht, D wird optional.

**Q2. Sollen DSPy-Prompts ganz entfernt oder opt-in gemacht werden?**
Aktuell sind sie Default. Nach Rewrite von GENERIC → robust: sollen `DSPY_OPTIMIZED_*`-Konstanten bleiben (als opt-in via anderem Flag) oder gelöscht werden? Löschen spart Wartung, Behalten erhält Reproduzierbarkeit historischer Benchmarks.

**Q3. Ist `<think>`-Stripping semantisch sicher?**
Wenn Qwen im `<think>`-Block Entity-Kandidaten diskutiert und im JSON nur ausgewählte listet, ist Stripping korrekt. Wenn manche Entities NUR im `<think>`-Block auftauchen, gehen sie verloren. Critic sollte dies mit einem Beispiel-Prompt validieren.

**Q4. Soll `AC-1`/`AC-2` mit Nemotron-oder-Qwen-Zielen definiert werden?**
Draft nutzt Nemotron-Baseline als Referenz. Wenn Qwen strukturell weniger Entities extrahiert (kleinere Modelle tun das), müssen die Ziele geadjustet werden. Alternative: erst Baseline-Messung mit fresh-cache Qwen + robusten Prompts, dann AC-1/AC-2 als "≥ 90 % dieser Baseline" definieren (self-referential, aber ehrlich).

## Referenzen

- Session-Log: `docs/analysis/BASELINE_ROUND2_ABLATION_2026-07-21.md` (Anhang, Truly-Cold-Cache Rerun)
- Memory: [[bug_qwen_prompt_incompatibility]], [[bug_prompt_cache_model_blindness]], [[feedback_qwen_over_nemotron]], [[dgx_spark_concurrency_limits]]
- ADR-060 (S-P-O Taxonomy) — die 15/22-Typen sind der Ausgabe-Vertrag.
- ADR-064 (Round-2 Feature Flag) — merged, entfernt Round-2-Overhead aber deckt Bug A nicht.
- ADR-065 (R2 Worker Pool) — Sketch, blockiert durch dieses ADR.
- Sprint 86 Feature 86.2 Commit: DSPy MIPROv2-Prompts (Ursprung des Bugs, war zu ihrer Zeit korrekt für Nemotron).
- `src/prompts/extraction_prompts.py:186, 221` — die betroffenen DSPy-Konstanten.
- `src/prompts/extraction_prompts.py:316` — `RELATION_EXTRACTION_FROM_ENTITIES_PROMPT` (SpaCy-First Round 1 Relations).
- `src/components/graph_rag/extraction_service.py:1059, 1195, 1605` — Parser-Kette.
- `src/components/graph_rag/extraction_service.py:2231` — Hardcoded Nemotron (Out of Scope).
