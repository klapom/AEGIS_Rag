# SPRINT_AGENTS_ADAPTATION.md — AEGIS RAG Adaptation (Paper 2512.16301-geleiteter Scope)

## Sprint-Ziel
AEGIS RAG so vorbereiten, dass **gezielte Adaptation auf Tool-Ebene (T1/T2)** möglich wird (Retriever/Reranker/Query-Rewriter/Memory), ohne den Core-LLM direkt zu finetunen. Fokus: **Messbarkeit → Trainingssignale → austauschbare Module**.

## Leitplanken
- **Default: Tool-Adaptation (T1/T2)** vor Agent-Adaptation (A1/A2).
- Reproduzierbar: klare Datasets, feste Prompts/Seeds, versionierte Artefakte.
- Sicherheit/Robustheit: keine “silent regressions” (Eval-Gates + Canary-Sets).

## Deliverables
- Instrumentierung + Logging-Schema für Retrieval/Graph/Memory/Answer
- Eval-Harness (Grounding, Citation-Coverage, Format-Compliance)
- Trainierbare Datasets aus Logs (Pairs/Triplets + Labels/Rewards)
- Mind. 1 adaptives Tool-Modul in Produktion (z. B. Reranker) + A/B Vergleich

---

## Feature-Liste (priorisiert)

### FEAT-001 — Unified Trace & Telemetry für RAG/Graph/Memory
**Beschreibung**  
Einheitliches Trace-Format über alle Stufen: Query → Rewrite → Vector/Graph Retrieval → Rerank → Evidence → Answer → Postchecks.

**Akzeptanzkriterien**
- Jede Anfrage erzeugt ein Trace-Objekt (JSON) inkl. `request_id`, `document_id`, `chunk_id`, Scores, Top-k Listen
- Persistenz in `runs/` oder zentralem Store mit Versionierung
- Mind. 3 Beispieltraces im Repo + README (Schema)

**Tasks**
- Trace-Schema definieren (`trace_v1.jsonschema`)
- Logger Hooks in Retriever / Graph Walker / Memory / Answerer
- Minimal Viewer (CLI) zum Filtern nach `request_id`

**Size**: M  
**Dependencies**: —


### FEAT-002 — Eval-Harness: Grounding / Citations / Format-Compliance
**Beschreibung**  
Automatische Qualitätschecks als Gates (CI/Local):
- Groundedness-Heuristik oder Judge-Model
- Citation-Coverage (Zitate zeigen auf passende Evidenz)
- Format-Compliance (JSON-Schema / Tabellenlayout / Pflichtfelder)

**Akzeptanzkriterien**
- `eval run --suite canary` liefert Scorecards + Fail-Reasons
- Canary-Suite (20–50 Queries) im Repo, versioniert
- Metriken: `grounding_score`, `citation_coverage`, `format_pass_rate`, `retrieval_hit@k`

**Tasks**
- Eval-Suites: `canary`, `regression`, `stress`
- Parser/Validator für Output-Formate (JSONSchema)
- Citation-Matcher (Chunk-ID / Offsets / fuzzy match)

**Size**: M-L  
**Dependencies**: FEAT-001


### FEAT-003 — Dataset Builder aus Traces (Ranking + Rewriting)
**Beschreibung**  
Aus produktionsnahen Traces Trainingsdaten erzeugen:
- Rerank-Daten: (query, pos_chunk, neg_chunk)
- Rewrite-Daten: (query, rewrite, retrieval_outcome)
- Optional Rewards: tool-execution / eval-scores

**Akzeptanzkriterien**
- `dataset build --from traces/ --out data/datasets/v1/`
- Outputs: `rerank_pairs.jsonl`, `rewrite_supervision.jsonl`, `metadata.json`
- Dedup + PII/Sensitive-Filter (mind. basic)

**Tasks**
- Sampling-Strategien (hard negatives, in-batch negatives)
- Labeling-Regeln (Hit@k, Eval-Score thresholds)
- Dataset-Versionierung + Stats-Report

**Size**: M  
**Dependencies**: FEAT-001, FEAT-002


### FEAT-004 — Adaptives Tool (T2): Reranker v1 integrieren
**Beschreibung**  
Reranker als austauschbares Modul (Cross-Encoder oder LLM-distilled), trainierbar auf FEAT-003-Daten.

**Akzeptanzkriterien**
- Reranker-Interface: `rank(query, candidates)->sorted`
- Offline-Verbesserung ggü. Baseline: +X% `retrieval_hit@k` oder +X% `grounding_score`
- Online Flag: `--reranker=v1|baseline` + Logging in Traces

**Tasks**
- Baseline-Reranker (Heuristik) + v1 Modell
- Training-Skript + Checkpoint-Handling
- A/B Evaluierung auf Canary + Regression

**Size**: L  
**Dependencies**: FEAT-003


### FEAT-005 — Adaptives Tool (T2): Query-Rewriter v1 (Hybrid Vector+Graph)
**Beschreibung**  
Rewrite-Agent/Modul erzeugt:
- Vektor-Suchquery (präzise, keyword+semantisch)
- Graph-Intent (Entity/Relation hints) für Traversal

**Akzeptanzkriterien**
- `rewrite(query)-> {vector_query, graph_intent}`
- Verbesserte Recall-Metrik: +X% `retrieval_hit@k` auf Canary
- Graph-Intent wird im Trace persistiert und im Graph-Walker genutzt

**Tasks**
- Prompt-basierter Rewriter (Teacher) + optional Student Distillation
- Regeln für Entity/Relation extraction (lightweight)
- Integration in Retrieval-Pipeline (vor Vector+Graph)

**Size**: M-L  
**Dependencies**: FEAT-001, optional FEAT-003


### FEAT-006 — Adaptives Tool (T2): Memory-Write Policy + Forgetting
**Beschreibung**  
Steuerung, **was** persistiert wird (Long-term Memory) und **wie** verdichtet/vergessen wird, basierend auf Nutzen-Signal (Eval + Retrieval Utility).

**Akzeptanzkriterien**
- Memory-Writer entscheidet pro Chunk/Fact: keep/summarize/drop + Begründung im Trace
- Nachweis: weniger Memory-Bloat bei gleicher/verbesserter Answer-Qualität
- Konfigurierbare Policies (thresholds + budgets)

**Tasks**
- Memory Budgeting (tokens/chunks/time)
- Utility-Signal aus FEAT-002 ableiten
- Summarizer/Compactor job + Versionierung

**Size**: M-L  
**Dependencies**: FEAT-001, FEAT-002


### FEAT-007 — Optional (A1): Tool-Execution Reward Loop für “verifizierbare” Tasks
**Beschreibung**  
Nur für Workloads mit harten Outcomes (z. B. SQL/Code-Execution): Reward aus Tool-Ausführung zur Optimierung von Plan/Query.

**Akzeptanzkriterien**
- Mind. 1 Task-Typ mit Execution-Check (pass/fail + diagnostics)
- Rewards werden in Trace gespeichert und in Dataset Builder übernommen
- Keine Regression auf Nicht-Execution Queries

**Tasks**
- Execution-Tooling (Sandbox/Runner) + Ergebnisparser
- Reward-Definition (binary + shaped reward) + Logging
- Canary-Subset speziell für Execution Tasks

**Size**: S-M (optional)  
**Dependencies**: FEAT-001, FEAT-002


### FEAT-008 — Optional (A2): Output-Judge Loop für Format & Policy
**Beschreibung**  
Judge bewertet Outputs (Format/Policy/Clarity) → Feedback für Prompt/Policy oder spätere Agent-Adaptation.

**Akzeptanzkriterien**
- Judge-Scoring integriert in Eval-Harness
- Verbesserte `format_pass_rate` um +X% auf Canary
- Transparente Fail-Reasons im Report

**Tasks**
- Judge Prompt + Score-Skalen + Calibration
- Kombination aus Judge + heuristischen Checks (Ensemble)
- Regression-Gates für “Judge drift”

**Size**: S-M (optional)  
**Dependencies**: FEAT-002

---

## Definition of Done
- Alle implementierten Features: Tests + Doku + Beispielruns
- Canary-Suite grün, Regression nicht schlechter als Baseline (definierte Toleranzen)
- Artefakte versioniert: Schemas, Datasets, Checkpoints, Reports

## Risiken / Watch-outs
- “Tool-Spaghetti”: Pipeline-Tiefe begrenzen (2–3 Stufen)
- Label-Leakage / Overfitting auf Canary: getrennte Splits + zeitbasierte Holdouts
- Evaluationsbias durch Judge: parallel heuristische Checks behalten
