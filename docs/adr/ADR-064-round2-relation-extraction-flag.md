# ADR-064: Feature-Flag für Round-2-Relation-Extraction

## Status

**Proposed** (2026-07-21)

## Kontext

Die AEGIS-Ingestion-Pipeline führt in `src/components/ingestion/nodes/graph_extraction.py` **zwei aufeinanderfolgende Relation-Extraction-Rounds** aus:

### Round 1 — via `extract_and_store_entities`
- Aufruf: `graph_extraction.py:316-322`
- Implementierung: `extraction_pipeline.py:130` → `extraction_pipeline.py:443` (`store_relations`)
- Verwendet: `ExtractionService` (3-Rank-Cascade, seit Sprint 129.6h effektiv nur Rank 1 = vLLM)
- Produziert: **typisierte** Entities + Relations (ADR-060: 15 Entity- + 22 Relation-Typen)
- Speichert: `RELATES_TO`-Edges mit `relation_type`-Property (TREATS, ENFORCES, CITES, ...)

### Round 2 — im `graph_extraction_node` selbst
- Ort: `graph_extraction.py:367-561` (Kommentar: *"Round 2: Re-extract relations using entities now stored in Neo4j"*)
- Verwendet: `RelationExtractor.extract_with_gleaning(gleaning_steps=0)` — **anderes** Modul als Round 1
- Nach `asyncio.sleep(1.0)` (Sprint-33-Race-Condition-Fix für Neo4j-Commit-Wait)
- Speichert: **dieselbe** `store_relations`-Funktion → dieselbe `RELATES_TO`-Kante

### Historie

| Sprint | Aktion |
|---|---|
| 33 (Feature 33.x) | Entity-Store-vor-Relation-Query eingeführt, `asyncio.sleep(1.0)` als Race-Fix |
| 34 (Feature 34.1, 34.2) | Round-2-Loop hinzugefügt als "Extract and store `RELATES_TO` relationships" |
| 85 (Feature 85.8) | Gleaning-Support (`gleaning_steps` Parameter) |
| 124 | Gleaning live auf `gleaning_steps=0` gesetzt (Kommentar: "for benchmark") |
| 128 | LightRAG-Removal, `ainsert_custom_kg()` als redundanter Overhead entfernt — Round 1 refactored, Round 2 unangetastet |
| 129.6h | Kaskade-Rank-2/3 entfernt, `ExtractionService` läuft effektiv single-model |

### Gemessene Baseline (2026-07-21)

Aus `docs/analysis/BASELINE_INGESTION_2026-07-21.md`:

- 4 Docs (13 KB Text max) → **21.9 min HTTP-Wall**
- 57 LLM-Calls, avg 23.6 s, p50 13.7 s, p95 59.3 s
- Ingestion ~100 % LLM-getrieben
- Round 2 macht **denselben LLM-Call-Pattern pro Chunk** wie Round 1 (chunk_text + entities → Relations) → strukturell **~50 % aller Chunk-basierten LLM-Calls**

### MERGE-Semantik (Neo4j) — **korrigiert 2026-07-21 nach Critic G2**

`neo4j_client.py:770-790`:
```cypher
MERGE (e1)-[r:RELATES_TO]->(e2)
SET r.weight       = toFloat(rel.strength) / 10.0,
    r.description  = rel.description,
    r.relation_type = CASE
        WHEN rel.relation_type <> 'RELATES_TO' THEN rel.relation_type   -- feuert IMMER
        WHEN r.relation_type IS NOT NULL AND r.relation_type <> 'RELATES_TO' THEN r.relation_type
        ELSE rel.relation_type
    END,
    ...
```

**Ursprüngliche Annahme im ersten ADR-Draft war falsch.** Der Guard schützt den bestehenden `relation_type` nur, wenn der eingehende Wert `'RELATES_TO'` ist. **Kein Extraktor produziert diesen Wert** — beide Rounds liefern entweder ADR-060-typisiert (`CAUSES`, `TREATS`, `CITES`, …) oder das Generic `'RELATED_TO'` (mit `D`, `extraction_service.py:139/:759`, `relation_extractor.py:55`). Die einzige Quelle für `'RELATES_TO'` (mit `S`) ist ein Fallback bei fehlendem Typ-Key (`neo4j_client.py:793-795`).

**Tatsächliches Verhalten (verifiziert):**
- Der erste CASE-Zweig `WHEN rel.relation_type <> 'RELATES_TO'` feuert bei **jeder** Schreibung — Round 2 überschreibt den `relation_type` bei jeder Kollision, inkl. typisiert → generic Downgrades (`CAUSES` → `RELATED_TO`).
- `description` und `weight`: identisch, immer überschrieben.
- Neue `(source, target)`-Paare in Round 2: zusätzliche Kanten mit `RELATED_TO`.

**Konsequenz:** Round 2 **degradiert heute aktiv ADR-060-Qualität**. Sprint 128s gemessene 84.5 % Relation-Specificity enthielten diesen Schaden bereits. Nach Abschaltung ist **steigende** Specificity zu erwarten — das gehört als Ablation-Erfolgsindikator in die Testmatrix.

**Der defekte MERGE-Guard selbst ist ein separates TD-Item** (nicht Teil dieses ADR-Scopes): sobald der Default kein Round 2 mehr schreibt, gibt es im Normal-Betrieb nur noch **einen** Schreiber und der Guard ist tot code — Aufräum-PR im Sprint-130-Wire-or-Delete-Backlog.

### Warum das jetzt ansteht

Fables Architektur-Analyse (2026-07-21) hatte Round 2 als "Sprint-33/34-Relikt" identifiziert und ein hartes Löschen (Refactor R1) mit erwartetem -30–40 %-Effekt vorgeschlagen. Die Baseline-Messung bestätigt die Größenordnung. **Aber**: Ein reines Löschen verliert (a) etwaige Round-2-only-Kanten und (b) ist nicht messbar. Für eine ehrliche Entscheidung braucht es einen **Ablation-Test** — dieselben Docs mit und ohne Round 2, Vergleich der Relation-Counts und der Retrieval-Qualität.

## Entscheidung

**Round 2 wird hinter ein Feature-Flag gestellt und im Default deaktiviert.**

Konfig: neue Env-Variable `AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS` (default `false`).

```python
# graph_extraction.py, in graph_extraction_node
if os.getenv("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", "false").lower() == "true":
    # Round 2 loop (Sprint 34 legacy, deactivated by default per ADR-064)
    ...  # bestehender Block Zeile 367-561
else:
    logger.info("round2_relation_extraction_skipped", reason="disabled_by_adr_064")
    total_relations_created = state.get("relations_count", 0)
```

Das ist reversibel per Env-Var-Flip ohne Code-Change.

## Alternativen (abgewogen)

| Option | Aufwand | Reversibilität | Empfehlung |
|---|---|---|---|
| **A. Feature-Flag (gewählt)** | 3 SP | Env-Var-Flip | ✅ |
| B. Round 2 hart löschen | 2 SP | git revert | ⚠️ nur nach Ablation-Erfolg |
| C. Round 2 unverändert lassen | 0 SP | — | ❌ +50% LLM-Wall bleibt |
| D. Round 2 refactoren (Round 1 nutzen und deduplicieren) | 8 SP | vollständig | ⚠️ hohes Risiko, unklar ob wertvoll |
| E. Round 2 auf `RelationExtractor` mit `gleaning_steps=2` upgraden | 5 SP | Config | ❌ macht Ingestion langsamer, nicht schneller |

Nach Ablation (nächster Schritt unten) kann A → B werden falls kein Coverage-Verlust nachweisbar.

## Konsequenzen

### Erwartet positiv
- **~30–50 % kürzere Ingestion-Wall** (Baseline: 21.9 min → ~11–15 min für dieselben 4 Docs). Präzise Zahl kommt aus Ablation.
- Kein Prompt-Format-Konflikt zwischen `RelationExtractor` und `ExtractionService` mehr — nur noch ein Extraction-Weg im Default-Betrieb.
- Weniger `RELATES_TO`-Kanten mit generic `relation_type=RELATES_TO` — Graph-Retrieval kann sich sauberer auf typisierte Relations verlassen.

### Erwartet neutral / negativ
- **Verlust von Round-2-only-Kanten**. Unbekannter Anteil. Muss gemessen werden. Falls > 15 % Relations-Verlust: Flag wieder anschalten und alternative Route wählen (Option E oder D).
- `asyncio.sleep(1.0)` in Zeile 360 wird redundant (kein späterer Neo4j-Query mehr) — kann in Folge-Patch mit gemessener Sicherheit entfernt werden.
- Falls Community Detection auf hohem `RELATES_TO`-Volume basiert (empirisch offen): Community-Struktur könnte sich ändern → RAGAS-CP/CR-Delta beobachten.

### Interne Legacy-Verweise, die zusätzlich aufgeräumt werden könnten (nicht Teil dieses ADR)
- `PhaseLatencyTracker relation_extraction` wird obsolet
- Log-Zeile `relationships_extracted_with_llm` referenziert statisch `model=nemotron-3-nano:128k rank=1` (Kaskaden-Legacy) — separater Fix
- Sprint-83-Feature-83.1-Latenz-Tracking pro Chunk in Round 2

## Ablation-Testplan (verpflichtend vor Merge) — **verweise auf Critic-Report B1/B2/B3**

Der Testplan wird durch die Metrik-Präzisierung im Critic-Report `CRITIC_GATE_ADR_064_2026-07-21.md` ersetzt:

**Pflicht-Metriken M1–M5** (Sektion B1 im Critic-Report), maßgeblich:
- **M1**: unique `(source, target)`-Paare pro Doc (nicht Raw-Count) — Verlust ≤ 15 % pro Doc
- **M2**: Anteil typisierter Relations (nicht `RELATED_TO`) an allen Relations — muss **steigen oder gleich bleiben** (Ziel des Refactors)
- **M3**: Anteil Generic (`RELATED_TO`, mit D — nicht `RELATES_TO`!) — muss **sinken**
- **M4**: Off-Taxonomy-Typen aus Round-2-Prompt (`relation_extractor.py:55` — 12 Typen außerhalb des Universal-Sets) — muss **auf 0 sinken**
- **M5**: Ingestion-Wall — Ziel −30–40 % pro Doc

**Stichprobe** (Critic B2): dieselben 5 Docs aus `BASELINE_INGESTION_2026-07-21.md`, **je 2 Runs pro Zustand** (Flag on/off), **frische Namespaces** pro Run (`ablation_r1_run1`, `ablation_r1_run2`, …).

**RAGAS-Retrieval-Check** (Critic B3): Manifest-Match auf die 5 Baseline-Doc-IDs in `data/evaluation/ragas_phase1_manifest.csv`; Fragen aus `data/evaluation/ragas_phase1_questions.jsonl` filtern; CP/CR-Delta ≥ −0.05 als Pass-Gate.

**Pass-/Fail-Gates**: siehe Critic-Report Sektion C3.

Ergebnis dokumentieren als `docs/analysis/BASELINE_ROUND2_ABLATION_2026-07-21.md`. Bei Erfolg: Feature-Flag entfernen (Option B, Follow-up-PR).

## Rollback — **korrigiert 2026-07-21 nach Critic G7**

- Env-Var im `.env`/Compose auf `AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS=true` setzen, dann **Container-Recreate erforderlich**: `docker compose -f docker-compose.dgx-spark.yml up -d --force-recreate api` (~10 s Wall). Grund: `os.getenv` liest das Prozess-Environment, das im Docker-Betrieb beim Container-Start eingefroren wird. Der Laufzeit-Read pro Ingestion-Call ist nur für Unit-Tests (`monkeypatch.setenv`) relevant, nicht für Prod-Rollback.
- Kein Code-Change, kein Rebuild.
- Bei Neo4j-Datenverlust-Verdacht: `namespace_id`-scoped Re-Ingestion mit Flag `true` reproduziert den vorigen Zustand für neue Docs. Für bereits ingestet Docs vor der Änderung: kein Effekt (die alten Kanten bleiben, MERGE ändert nichts wenn nicht neu ingestet).

## Umsetzungsschritte

1. **PR-1** (3 SP): Feature-Flag einbauen — Umsetzungsdetails gemäß **Critic-Report Sektion D (Punkte 1–7)** und **Testumfang C1–C4** (`docs/analysis/CRITIC_GATE_ADR_064_2026-07-21.md`).
2. **Ablation-Messung** (0.5 Tag): gemäß M1–M5 in "Ablation-Testplan" oben.
3. **PR-2** (2 SP, konditional): Falls Ablation grün → Round 2 hart löschen. **`asyncio.sleep(1.0)` nicht mitentfernen ohne Verifikation** (Critic G3): `create_section_nodes` (`graph_extraction.py:623`) hat potenziell dieselbe Sichtbarkeits-Race die das Sleep in Sprint 33 gepflastert hat. Verifizieren dass `store_chunks_and_provenance` und `create_section_nodes` über dieselbe Driver-Session/Causal-Consistency laufen — sonst Sleep vor die Section-Nodes verschieben, nicht löschen.
4. **Follow-up** (nicht Teil dieses ADR): `extraction_worker_pool` verdrahten (Refactor R2, siehe ADR-065).
5. **Follow-up TD-Item** (nicht PR-1): defekter MERGE-Guard in `neo4j_client.py:777-781` (`'RELATES_TO'` ≠ `'RELATED_TO'`, Critic G2). Nach ADR-064 gibt es im Default-Betrieb nur noch **einen** Schreiber → Guard ist dann Dead Code, Aufräum im Sprint-130-Wire-or-Delete-Backlog.

## API-Semantik-Nebeneffekt (Critic G4)

Die Upload-Response-Feld `relations_count` (`retrieval.py:762` ← `state["relations_count"]`) zählt heute nur Round-2-Relations (`graph_extraction.py:567`). Mit Flag off enthält es korrekt die **Round-1-Zahl**. Kein Bruch, aber semantische API-Änderung — im Frontend-Feld sichtbar (`UploadResultCard.tsx`, `ExtractionSummary.tsx`). Als Changelog-Eintrag in `docs/DECISION_LOG.md` vermerken.

## Referenzen

- `docs/analysis/BASELINE_INGESTION_2026-07-21.md` — gemessene Baseline
- `docs/analysis/RAG_ARCHITECTURE_ASSESSMENT_2026-07-21.md` — Fable-Architekturanalyse, Ursprung von R1
- `docs/analysis/RAGU_vs_AEGIS_2026-07-21.md` — Kontext (Extraction-Qualität via Distillation ist orthogonaler Hebel)
- `docs/analysis/AEGIS_HONEST_ASSESSMENT_2026-07-21.md` — Wire-or-Delete-Muster (dieser ADR ist ein Instanz davon)
- ADR-060 — Domain-Taxonomy (typisierte Relations)
- ADR-061 — LightRAG-Removal (Vorbild-Refactor)

---

## Anhang: Patch-Vorschlag (unified diff)

```diff
diff --git a/src/components/ingestion/nodes/graph_extraction.py b/src/components/ingestion/nodes/graph_extraction.py
--- a/src/components/ingestion/nodes/graph_extraction.py
+++ b/src/components/ingestion/nodes/graph_extraction.py
@@ -14,6 +14,7 @@
 """

 import asyncio
+import os
 import time
 from typing import Any

@@ -364,300 +365,317 @@ async def graph_extraction_node(state: IngestionState) -> IngestionState:
             wait_seconds=1.0,
         )

-        # Sprint 34 Feature 34.1 & 34.2: Extract and store RELATES_TO relationships
-        # Round 2: Re-extract relations using entities now stored in Neo4j
-        relation_extraction_start = time.perf_counter()
-        total_relations_created = 0
+        # ADR-064: Round-2 relation extraction is deactivated by default.
+        # Round 1 (extract_and_store_entities above) already writes typed RELATES_TO edges.
+        # Set AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS=true to reactivate the Sprint-34 legacy path.
+        _round2_enabled = os.getenv(
+            "AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", "false"
+        ).lower() == "true"
+
+        if not _round2_enabled:
+            logger.info(
+                "round2_relation_extraction_skipped",
+                reason="disabled_by_adr_064",
+                round1_relations=graph_stats.get("stats", {}).get("total_relations", 0),
+            )
+            state["relations_count"] = graph_stats.get("stats", {}).get("total_relations", 0)
+        else:
+            # Sprint 34 Feature 34.1 & 34.2: Extract and store RELATES_TO relationships
+            # Round 2: Re-extract relations using entities now stored in Neo4j
+            relation_extraction_start = time.perf_counter()
+            total_relations_created = 0
+
+            # Sprint 83 Feature 83.1: Track per-chunk latencies for relation extraction
+            relation_latency_tracker = PhaseLatencyTracker()
+
+            logger.info(
+                "TIMING_relation_extraction_start",
+                stage="graph_extraction",
+                substage="relation_extraction",
+                chunks_to_process=len(prechunked_docs),
+            )
+
+            # ... (existing Round-2 loop stays unchanged, indented one level deeper)
+            #   ↳ bestehender Block Zeile 382-561 wird in diesen else-Zweig eingerückt
+
+            relation_extraction_end = time.perf_counter()
+            relation_extraction_ms = (relation_extraction_end - relation_extraction_start) * 1000
+            state["relations_count"] = total_relations_created
```

**Umsetzungshinweise für den Implementierer:**
- Zeile 367-568 komplett in den `else`-Zweig einrücken (kein Logik-Change, nur Indentation)
- `state["relations_count"]`-Setzen in beiden Zweigen sicherstellen
- Neue Unit-Tests: `test_graph_extraction_node_skips_round2_by_default`, `test_graph_extraction_node_runs_round2_when_flag_set`
- Integration-Test-Fixture: default-Flag `false` sicherstellen (nicht versehentlich in Test-Umgebung `true` setzen)
- Doc-Update: `docs/CLAUDE_extended.md` und `docs/TECH_STACK.md` Env-Var-Sektion ergänzen
