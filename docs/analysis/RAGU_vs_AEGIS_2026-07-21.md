# RAGU vs. AEGIS — Harte Architektur-Vergleichsanalyse

**Datum:** 2026-07-21
**Analyst:** Fable-5 (Deep-Analysis-Subagent)
**Gegenstand:** "RAGU: A Multi-Step GraphRAG Engine with a Compact Domain-Adapted LLM" (Komarov et al., NSU+ITMO, 2026, Paper 2607.11683) vs. AEGIS-RAG-Extraction-Stack (Stand Sprint 129)

**Quellenlage / Einschränkungen (ehrlich vorab):**
- RAGU-Seite basiert auf dem bereitgestellten Paper-Extract, **nicht** auf eigenem Lesen von Paper/Repo. Zahlen (4×/21×-Skalierung, Benchmarks) sind nicht unabhängig verifiziert.
- AEGIS-Seite basiert auf direktem Code-Lesen (Pfade+Zeilen unten zitiert).
- `docs/OVERNIGHT_PLAN.md` **existiert nicht mehr** — `bin/overnight_run.py:6` referenziert es noch. Der Plan-Inhalt wurde aus `bin/overnight_run.py`, `bin/annotate_with_llm.py`, `bin/train_qlora.py` und den Daten-Artefakten rekonstruiert.
- Annahme: „Qwen3.6-35B-A3B-FP8" = MoE mit **~3B aktiven Parametern** (Namenskonvention analog Qwen3-30B-A3B). Falls das falsch ist, ändert sich die Kosten-Bewertung in Abschnitt 4 substanziell.

---

## 0. Befunde aus der Code-Inspektion, die die Analyse prägen

Drei Dinge, die vor jedem RAGU-Vergleich auf dem Tisch liegen müssen:

1. **`EntityCanonicalizer` ist toter Code.** `src/components/graph_rag/entity_canonicalization.py` wird nirgendwo in `src/` importiert (grep über alle Module: null Treffer außerhalb der Datei selbst). Zusätzlich hat er einen Bug, der seine Kernidee entwertet: `to_graph_entity()` speichert nur `merged_descriptions[0]` (entity_canonicalization.py:68) — alle über Chunks gesammelten Beschreibungen außer der ersten werden verworfen. Der **echte** Live-Dedup-Pfad ist `semantic_deduplicator.py` via `extraction_pipeline.py:31`.
2. **Der AEGIS-Distillation-Track existiert bereits — und ist gestrandet.** 10 QLoRA-Trainingsläufe am 2026-03-11 (`data/lora_adapters/aegis-ner-qwen25-14b-v1/`), Ziel Qwen2.5-14B-Instruct (`data/lora_training/qlora_config.json`), 2.367 Samples (1.893 Train, **94% LLM-annotiert**, nur 150 gold; `metadata.json`). Der Adapter wird **nirgendwo in `src/` referenziert**, wurde also nie in die Pipeline integriert. Die Qualitäts-Eval ist kaputt: `data/evaluation/extraction_quality_report.json` meldet `overall_f1: 0.0`, 4 von 5 Datasets `no_data`.
3. **Die Kaskade ist de facto tot.** Sprint 129.6h hat Rank 2/3 (Ollama gpt-oss:20b) entfernt (SPRINT_PLAN.md:2230-2233) — GPU-Verschwendung + `cudaErrorIllegalInstruction`. Aktueller Zustand: vLLM Single-Engine + tenacity-Retry. Die im Code noch vorhandene 3-Rank-Logik (`extraction_service.py:9-15`, `extraction_cascade.py`) ist Ballast.

---

## 1. Komponenten-Matrix

Legende: ✅ = wir haben schon · 🔴 = RAGU besser · 🟢 = wir besser · ⚪ = orthogonal / nicht vergleichbar

| # | RAGU-Komponente | AEGIS-Äquivalent | Bewertung | Begründung |
|---|---|---|---|---|
| 1 | SimpleChunker | Section-aware Chunking 800–1800 Tokens (ADR-039, `adaptive_chunking.py`) + Table-Chunks mit Quality-Scoring (Sprint 129.6a/b) | 🟢 | RAGU chunkt naiv; AEGIS ist sektions- und tabellenbewusst inkl. 6-Metrik-Quality-Gates. |
| 2 | TwoStageArtifactsExtractorLLM (typed: erst Entities, dann Relations constrained auf Entity-Liste) | SpaCy-First-3-Stage-Pipeline (`extraction_cascade.py:14-17`): SpaCy NER → LLM-Enrichment → LLM-Relations aus bekannter Entity-Liste (`RELATION_EXTRACTION_FROM_ENTITIES_PROMPT`, `extraction_service.py:73`); typisiert per ADR-060 (15 Entity- + 22 Relation-Typen, `extraction_service.py:88-140`) | ✅ | Strukturell äquivalent. Das „2-stage constrained"-Muster, das das Paper als Feature verkauft, ist in AEGIS seit Sprint 89 Standard. |
| 3 | — (RAGU hat kein Äquivalent) | Gleaning-Multi-Pass (`extraction_service.py:3209`), Coreference (86.7), Cross-Sentence-Windows + Bisection-Fallback (`cross_sentence_extractor.py:112-165`, 129.1), Entity-Consolidation vor Relation-Extraction (`entity_consolidator.py:17-22`), Metadata-Blocklist (`extraction_pipeline.py:39-60`) | 🟢 (mit Fußnote) | Mehr Recall-Maschinerie als RAGU. Fußnote: Ein Großteil davon ist **Kompensations-Code für Modellschwächen** — genau das, was RAGU per Trainings-Investment ins Modell verlagert. Siehe Frage A. |
| 4 | DBSCAN-Clustering **innerhalb** einer Entity (Description-Konsolidierung) + LLM-Summarization gemergter Descriptions | `semantic_deduplicator.py`: Name-Embedding-Clustering (BGE-M3, cross-mention), Descriptions werden **konkateniert** mit Suffix `[Deduplicated from N mentions: …]` (`semantic_deduplicator.py:613`). Keine LLM-Zusammenfassung. Der einzige Ort mit Merge-Absicht (`EntityCanonicalizer`) ist tot und droppt Descriptions (s.o.) | 🔴 | **Der eine klare strukturelle Vorsprung von RAGU auf Ingestion-Seite.** AEGIS-Entity-Profile degradieren mit Mention-Count (Fragment-Konkatenation), RAGU-Profile werden kohärenter. Wirkt direkt auf Community-Summaries und Global Search. |
| 5 | Leiden Community Detection | `community_detector.py` (Leiden via Neo4j GDS + NetworkX-Fallback, LRU-Cache) + `community_labeler.py` + `community_summarizer.py` + **`community_delta_tracker.py` (inkrementelle Delta-Updates, `community_summarizer.py:373`)** + `section_communities.py` | 🟢 | RAGU hat Detection. AEGIS hat Detection + Labeling + LLM-Summaries + inkrementelle Re-Summarization nur geänderter Communities + sektions-lokale Communities. |
| 6 | Storage-Abstraction (NetworkX/Neo4j, NanoVDB/Qdrant swappable) | Fest: Neo4j 5.24 + Qdrant 1.11 | ⚪ | Swappability ist ein Bibliotheks-Feature, kein Produkt-Feature. AEGIS braucht sie nicht; Umbau wäre reiner Aufwand ohne Nutzen. |
| 7 | QueryPlanEngine mit Acronym-Expansion, Local+Global Search | `dual_level_search.py` (local/global/hybrid, :123/:275/:489), `query_decomposition.py`, `query_rewriter_v2.py`, `intent_classifier.py` (C-LARA 95%), HyDE-Klassifikation (129.7), SmartEntityExpander (Sprint 78, LLM→Graph→Synonym→Rerank) | 🟢 | AEGIS-Query-Seite ist deutlich reicher. Ehrlicher Abstrich: `global_search` nutzt intern noch naive Stopword-/Keyword-Matches und ist im Code selbst als „simplified implementation" markiert (`dual_level_search.py:296-299`) — der Community-Suchpfad (`community_search.py`) ist der bessere, aber nicht überall verdrahtet. |
| 8 | **Meno-Lite-0.1: 7B, CPT (1,3 Mrd. Tokens) + SFT (50 Mio. Tokens, inkl. Pipeline-Logs), domänen-/pipeline-adaptiert** | Qwen3.6-35B-A3B-FP8 (generalistisch, Port 8088) + gestrandeter QLoRA-Track: 14B-Ziel, ~4 Mio. SFT-Tokens (1.893×~2k), kein CPT, Eval kaputt, nie integriert | 🔴 | **Der zentrale strukturelle Vorsprung von RAGU.** Nicht weil „klein", sondern weil das Modell *auf die eigene Pipeline trainiert* wurde. AEGIS' Versuch in dieselbe Richtung ist 3 Größenordnungen kleiner dimensioniert und operativ tot. |
| 9 | Pydantic-Validation, Retry-Logic, 374 Tests, Mock-LLM-Server | Pydantic v2, tenacity (`extraction_service.py:39-44`), 800+ Tests, vLLM-Capacity-Gate (`extraction_service.py:1364`) | ✅ | Engineering-Parität; AEGIS quantitativ größer. Mock-LLM-Server für Offline-CI wäre ein nettes Detail, kein Strukturthema. |
| 10 | — | Multi-Tenant-Namespaces, GDPR/Audit-Layer (Sprint 96), RAGAS-Harness, VLM/Table-Ingestion, Temporal Memory (Graphiti), Frontend/Admin-UI | ⚪ | AEGIS-only. RAGU ist eine Extraction-Engine, AEGIS ein Produkt. Genau deshalb ist „RAGU adoptieren" als Ganzes keine sinnvolle Option (Frage C). |

---

## 2. Frage A — Was macht RAGU strukturell anders (jenseits „kleineres Modell")?

**A1. Qualitäts-Allokation: Gewichte statt Pipeline-Code.** Das ist der eigentliche Unterschied. AEGIS' Sprint-86/89/128/129-Historie ist eine Kette von *nachgelagerten Kompensationen* für Extraction-Schwächen: Gleaning-Pässe, Completeness-Checks, Window-Bisection bei 0-Relation-Fenstern, Entity-Quality-Filter, Metadata-Blocklists, Consolidation-Stufen, Relation-Caps rein und wieder raus (128.9→129.10). Jede dieser Schichten kostet LLM-Calls, Latenz und Wartung. RAGU investiert einmalig in Trainings-Compute (CPT+SFT auf Pipeline-Log-Format) und bekommt dafür ein Modell, das die Ziel-Formate nativ produziert — weniger Parse-Failures, weniger Retry, weniger Kompensat. Die Meno-SFT-Daten enthalten explizit LightRAG-Logs, d.h. das Modell ist auf die *Prompts der eigenen Pipeline* konditioniert. AEGIS hat mit `training_data_collector` (`extraction_pipeline.py:32`) und `extraction_debug_logger.py` die Rohstoffe dafür längst — nutzt sie aber nicht.

**A2. Description-Konsolidierung als eigene Pipeline-Stufe.** RAGU clustert Descriptions *innerhalb* einer Entity (DBSCAN) und lässt das LLM die gemergten Cluster zusammenfassen. AEGIS konkateniert (`semantic_deduplicator.py:613`) bzw. verwirft (`entity_canonicalization.py:68`, toter Code). Bei 498-Doc-Ingestion (129.3) mit hochfrequenten Entities ist das der Unterschied zwischen einem kohärenten Entity-Profil und einer Fragmenthalde — mit direkter Downstream-Wirkung auf `community_summarizer` (der die Entity-Descriptions als Input nimmt, `community_summarizer.py:30-43`) und Global Search.

**A3. Sonst: weniger als das Paper suggeriert.** Two-Stage-typed-Extraction (✅ vorhanden), Leiden (✅ vorhanden, AEGIS weiter), Local+Global (✅ vorhanden, AEGIS weiter), Storage-Abstraction (⚪ irrelevant). RAGUs Pipeline ist eine saubere, schlanke Teilmenge dessen, was AEGIS schon hat — plus die zwei echten Punkte A1/A2.

---

## 3. Frage B — Ist die 7B-Distillation-These für AEGIS' Domäne plausibel?

**Die Skalierungs-These kritisch geprüft.** „Comprehension skaliert 4×, Factual Knowledge 21× (0.5B→72B); Extraction braucht Comprehension" — dazu drei Punkte:

1. **Der Kern trägt auch für EN/DE:** Extraction ist überwiegend *Copy-and-Type* — Spans erkennen, die im Kontext stehen, und typisieren. Das Modell muss den Fakt nicht *wissen*, es muss ihn im Text *erkennen*. Das ist Comprehension, und die RAGU-Messung (auf RU/Qwen-Familie) hat keinen erkennbaren Grund, sprachspezifisch zu kippen — Qwen2.5-7B ist auf EN stärker als auf RU.
2. **Aber: Die Asymmetrie ist in Fach-Domänen schwächer als in RU-General.** Korrekte *Typisierung* seltener Terminologie (ist „Methotrexat" MATERIAL oder PRODUCT? Ist „§ 823 BGB" REGULATION oder DOCUMENT?) und Abkürzungs-Auflösung in Medical/Legal sind parametrisches Wissen. Genau deshalb macht Meno **CPT auf Domänen-Korpora** (1,3 Mrd. Tokens) und nicht nur SFT. Ohne CPT-Äquivalent ist die 7B-These für Medical/Legal/EN+DE **nicht** belegt. Meno selbst ist zudem russisch-primär — als Direkt-Drop-in für AEGIS ungeeignet; als *Rezept-Beleg* aber valide.
3. **Absolute Zahlen ehrlich lesen:** Meno NEREL-Harmonic-Mean 0.4676 ist *relativ zur Größe* stark, absolut mäßig. Und End-to-End matched RAGU 32B nur — schlägt es nicht. Die These lautet korrekt: „7B+Adaption erreicht 32B-Parität bei Bruchteil der Kosten", nicht „7B ist besser".

**Was ein AEGIS-Meno-Äquivalent trainingsseitig können müsste:**
- **Basis:** EN/DE-fähiges 7–8B (Qwen2.5-7B-Instruct hat brauchbares Deutsch; EuroLLM-9B/Teuken-7B wären DE-stärker, aber Ökosystem/vLLM-Reife schwächer).
- **CPT:** 300M–1,3 Mrd. Tokens Medical/Legal/Technical EN+DE. Die Korpora dafür lädt `bin/fetch_api_datasets.py` **bereits** (OpenAlex CC0, EUR-Lex — nativ zweisprachig!, ClinicalTrials). EUR-Lex ist für DE-Legal ein Glücksfall.
- **SFT:** ~50 Mio. Tokens im AEGIS-DSPy-Schema (ADR-060), Teacher = Qwen3.6-35B, plus **echte Pipeline-Logs** via `training_data_collector`. Der aktuelle Datensatz (2.367 Samples ≈ 4M Tokens, 94% ungefiltert LLM-annotiert) ist ~10× zu klein und qualitativ ungesichert.
- **Realistischer Compute-Check:** CPT von 7B auf >1 Mrd. Tokens auf einer einzelnen GB10 dauert Wochen. Ehrliche Optionen: (a) CPT auf 300–500M Tokens lokal, (b) GPU-Rental für CPT — die CPT-Daten sind öffentliche Korpora, **kein** Privacy-Konflikt; nur die SFT-Teacher-Daten aus Kundendokumenten müssen lokal bleiben.

**Urteil:** Plausibel **mit** CPT, unbelegt ohne. Das aktuelle AEGIS-QLoRA-Setup (14B, 4M Tokens, kein CPT) testet die These gar nicht erst.

---

## 4. Kosten-Claim einordnen ($0.001 vs. $0.10/doc)

Der Paper-Vergleich ist API-vs-Rental und für AEGIS doppelt schief:

1. **AEGIS läuft on-prem** — die Währung ist GPU-Zeit, Latenz und Unified-Memory-Belegung, nicht Dollar/Doc.
2. **Entscheidender: AEGIS' „35B" ist ein A3B-MoE.** Bei ~3B aktiven Parametern in FP8 liegt der *Compute pro Token* bereits in der Klasse eines kleinen Dense-Modells — der RAGU-Kostenvorteil „7B dense statt 32B dense" (≈4,5× Compute) ist gegen Qwen3.6-35B-A3B **weitgehend schon realisiert**. Was ein 7B-Dense-Modell noch brächte: ~28 GB weniger Weights im Unified Memory (35 GB FP8 → ~7 GB FP8) — relevant für VLM/FLUX-Koexistenz auf der 128-GB-Spark — und ggf. bessere Batch-Effizienz. Was es *nicht* automatisch brächte: die 6–8 min/doc zu halbieren.
3. **Die Latenz ist mutmaßlich Call-Count-dominiert, nicht Modellgrößen-dominiert.** 50 Chunks × (Enrichment + Relations + Gleaning-Pässe + Completeness-Checks + Cross-Sentence-Windows + Bisection-Retries) ergibt hunderte LLM-Calls pro Dokument. Ein spezialisiertes Modell hilft hier vor allem *indirekt*: weniger 0-Relation-Fenster → weniger Bisection, weniger Parse-Failures → weniger Retries, ggf. Gleaning überflüssig. **Das ist ungemessen** — Item 3 in Sprint 130 unten.

---

## 5. Frage C — Adoptieren, selektiv integrieren oder eigener Pfad?

**Empfehlung: eigener Pfad + selektive Integration von zwei RAGU-Ideen. RAGU-Adoption als Engine ist ausgeschlossen.**

Gegen Adoption:
- RAGU ersetzt nur die Matrix-Zeilen 1–7 — und dort ist AEGIS in 5 von 7 gleichauf oder besser. Adoption würde ersatzlos verlieren: Multi-Tenant-Namespaces, GDPR/Audit (Sprint 96), Table-/VLM-Ingestion (129.6), RAGAS-Harness, Temporal Memory, Admin-UI, C-LARA/HyDE-Query-Seite. Sprint 128 hat gerade erst LightRAG herausoperiert (−6.660 LOC, `extraction_pipeline.py:3-5`) — eine neue Fremd-Engine einzubauen wäre derselbe Fehler in neu.
- Meno-Lite ist russisch-primär: als AEGIS-Extraction-Modell für EN/DE-Medical/Legal nicht einsetzbar.

Selektiv integrieren (konkret):
1. **Description-Konsolidierung (Matrix #4)** — der einzige Ingestion-Baustein, wo RAGU klar besser ist. Einbau in den bestehenden `semantic_deduplicator`-Pfad, toten `EntityCanonicalizer` löschen.
2. **Das Trainings-Rezept (Matrix #8)** — nicht das Modell. CPT+SFT-auf-Pipeline-Logs als Blaupause für die Sanierung des eigenen, bereits existierenden Distillation-Tracks.

Beim eigenen Pfad bleiben, aber mit RAGU-Referenzrahmen: GraphRAG-Bench (Medical) als externes Maßband übernehmen — AEGIS hat bislang nur interne Benchmarks (RAGAS CP=0.739/CR=0.760, 84.5% Relation-Specificity) und keinen Vergleichspunkt gegen den Feldstand (RAGU Evidence-Recall 0.84).

---

## 6. Frage D — Was bedeutet das für `~/projects/propositionizer/`?

**Neu-scopen, nicht beerdigen — Phase 0 pausieren bis zum Benchmark-Ergebnis.**

- RAGU **bestätigt die Prämisse** des Propositionizers (kleines domänen-adaptiertes Modell im Extraction-Pfad) — und stellt zugleich seine *Architektur* in Frage: RAGU zeigt, dass **direktes** Fine-Tuning eines 7B auf typed ER-Extraction End-to-End-Parität mit 32B erreicht — ohne die vierstufige Zielarchitektur des Propositionizer-Plans (fastcoref → T5-Propositionizer → SetFit-Router → GLiNER/GLiREL → Bi-Encoder, `~/projects/propositionizer/PLAN.md:20-27`), deren Stufen 2–3 noch gar nicht existieren und je eigene Fehlerquellen einführen.
- AEGIS besitzt den Direkt-Distillations-Pfad **schon** (Overnight-Track, Abschnitt 0.2) — er ist nur gestrandet. Zwei parallele Trainings-Projekte mit demselben Ziel (Extraction-Qualität pro Compute) sind eines zu viel.
- **Konkretes Re-Scoping:** (a) Propositionizer-Phase-0 nicht starten, bis der 7B-vs-35B-Benchmark (Sprint-130-Item 1) gelaufen ist. (b) Wenn direkte 7B-SFT die Lücke schließt: Propositionizer-Idee als **Datenaufbereitung** für das Extraction-Training weiterverwenden (atomare Propositionen als SFT-Zwischenformat verbessern nachweislich Teacher-Label-Qualität), nicht als Runtime-Stage. (c) Nur wenn direkte SFT scheitert (Faithfulness-Probleme bei komplexen Satzgefügen), hat die explizite Propositionizer-Stage als Runtime-Komponente wieder einen Business Case.

---

## 7. Empfehlung Sprint 130 — Actionable Items

| # | Item | SP | Erwartungswert |
|---|------|----|----------------|
| 1 | **Small-Model-Benchmark:** Qwen2.5-7B-Instruct (stock) und optional Meno-Lite-0.1 (nur EN-Subset, als Datenpunkt fürs Rezept) gegen Qwen3.6-35B-A3B auf dem bestehenden 15-Doc-E2E-Benchmark (Sprint 128: 212 Entities / 626 Relations / 84.5% Specificity) fahren. Metriken: Entity-/Relation-Count, Specificity, Parse-Failure-Rate, 0-Relation-Window-Rate, tok/s. | 3 | Entscheidet die Distillation-Frage mit eigenen Daten statt Paper-Claims. Quantifiziert das „Headroom": Ist die 7B-Lücke <15%, lohnt Item 4 groß; ist sie >30%, ist CPT Pflicht oder der Track fällt. |
| 2 | **Entity-Description-Konsolidierung (RAGU-Muster):** In `semantic_deduplicator.py` nach dem Name-Clustering eine Description-Konsolidierung ergänzen — Embedding-Clustering der Descriptions innerhalb jeder gemergten Entity (DBSCAN/agglomerativ, BGE-M3 vorhanden), Cluster >N per LLM zusammenfassen statt konkatenieren (`semantic_deduplicator.py:613`). Toten `entity_canonicalization.py` löschen. | 5 | Direkter Qualitätshebel auf Entity-Profile → Community-Summaries (`community_summarizer.py:30-43` konsumiert Descriptions) → Global Search → RAGAS Context Precision. Bester Quality-per-SP-Kandidat dieser Liste. |
| 3 | **Extraction-Latenz-Profiling:** `extraction_metrics.py` um per-Doc-Aufschlüsselung erweitern: LLM-Call-Count × Latenz pro Stufe (Enrichment / Relations / Gleaning / Bisection / Dedup). Eine 6–8-min-Ingestion in ihre Bestandteile zerlegen. | 3 | Verhindert die teuerste Fehlinvestition: Modell verkleinern, wenn in Wahrheit der Call-Count dominiert (Abschnitt 4.3). Liefert zugleich die Baseline für Erfolgsmessung von Item 2/4. |
| 4 | **Distillation-Track sanieren (nicht neu bauen):** (a) Eval-Pipeline fixen (`overall_f1: 0.0`, 4/5 Datasets `no_data`), (b) vorhandenen `aegis-ner-qwen25-14b-v1`-Adapter erstmals gegen Teacher evaluieren, (c) bei positivem Item-1-Signal: Re-Target auf 7–8B, SFT-Set von 2,4k auf 30–50k Samples skalieren (Quellen: `training_data_collector`-Logs + Teacher-Annotation, Gold-Anteil >150 erhöhen), CPT-Lite auf den bereits heruntergeladenen EUR-Lex/OpenAlex/ClinicalTrials-Korpora prüfen. | 8 | Der Track hat bereits versunkene Kosten (Skripte, Daten, 10 Trainingsläufe) — Sanierung ist billiger als der Propositionizer-Neuaufbau und testet die RAGU-These direkt am eigenen Stack. |
| 5 | **Propositionizer-Decision-Gate + GraphRAG-Bench:** Kurzes Decision-Doc: Propositionizer Phase 0 pausiert bis Item-1/4-Ergebnisse (Abschnitt 6). Parallel GraphRAG-Bench-Medical als externen Benchmark ins RAGAS-Harness aufnehmen (RAGU-Vergleichspunkt: Evidence-Recall 0.84). | 3 | Beendet die Doppelinvestition zweier Trainingsprojekte; schafft erstmals externe Vergleichbarkeit von AEGIS gegen publizierte GraphRAG-Systeme. |

**Summe: 22 SP** — passt neben die 129-Carryovers (129.3/129.4/129.5/129.8, ~19 SP).

---

## 8. Zusammenfassung in einem Satz

RAGU ist kein besseres GraphRAG als AEGIS — es ist ein schlankeres mit einem besser trainierten Extraction-Modell und einer saubereren Description-Konsolidierung; genau diese zwei Dinge sollte AEGIS übernehmen (als Rezept bzw. als Pipeline-Stufe), alles andere hat AEGIS bereits gleichwertig oder besser, und der eigene, gestrandete Distillation-Track plus der pausierte Propositionizer sollten zu **einem** RAGU-Rezept-basierten Trainingsprojekt konsolidiert werden.
