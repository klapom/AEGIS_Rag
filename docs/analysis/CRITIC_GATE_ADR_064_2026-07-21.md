# Critic-Gate: ADR-064 (Round-2-Relation-Extraction-Flag)

**Datum:** 2026-07-21
**Critic:** Fable-5 (Pre-Sprint Critic-Gate gemäß globalem CLAUDE.md)
**Geprüftes Artefakt:** `docs/adr/ADR-064-round2-relation-extraction-flag.md` (Status: Proposed) inkl. Patch-Anhang
**Methode:** Deep-Read der fünf Kontext-Dateien + Code-Verifikation aller ADR-Behauptungen mit `path:line`-Beleg

---

## Verdikt vorab: 🟡 GO mit Anpassungen

Die Entscheidung (Round 2 hinter Flag, default aus) ist richtig — und nach dieser Prüfung sogar **stärker begründet, als der ADR selbst behauptet**: Der MERGE-Guard, der laut ADR Round-1-Typen schützt, ist wegen eines `RELATED_TO`/`RELATES_TO`-String-Mismatches **wirkungslos** — Round 2 überschreibt Round-1-`relation_type` bei jeder Kollision (Gap G2). Der Patch braucht 7 präzise Änderungen (Abschnitt D), keine davon stellt die Grundentscheidung in Frage.

---

## A) Design-Gaps

### G1 — „Round 2 ist Duplikat" ist unpräzise: gleiche LLM-Route, aber divergente Taxonomien

**Gleiches Modell:** Beide Rounds laufen über `AegisLLMProxy` mit `TaskType.EXTRACTION` und `settings.extraction_llm_model`:
- Round 1: `extraction_service.py:2437-2447` (`model_override=stage_config.model`)
- Round 2: `relation_extractor.py:147-150` (Default aus `settings.extraction_llm_model`), `:273-284` (`model_local=self.model`, `DataClassification.CONFIDENTIAL`)

**Aber verschiedene Prompts und verschiedene Typ-Taxonomien:**
- Round 1 normalisiert jede LLM-Antwort durch `validate_relation_type()` (`extraction_service.py:692-760`) auf die **21 UNIVERSAL_RELATION_TYPES** (`extraction_service.py:110-140`; Generic-Fallback = `RELATED_TO`).
- Round 2 hat eine **eigene 21-Typen-Liste im Prompt** (`relation_extractor.py:55`): `WORKS_FOR, DERIVED_FROM, INFLUENCES, MEASURES, FUNDED_BY, AUTHORED_BY, PRODUCES, COMPETES_WITH, REGULATES, SUPPORTS, TEACHES, PRECEDED_BY …` — **12 dieser Typen sind NICHT im Universal-Set**, und Round-2-Output läuft **nie** durch `validate_relation_type` (`_parse_json_response` → direkt `store_relations`, `graph_extraction.py:494-505`).

**Konsequenz:** Round 2 ist kein Duplikat, sondern ein **divergenter Extraktor, der Off-Taxonomy-Typen in den Graph schreibt**. Die These „Relations-Count allein reicht als Ablation-Metrik" ist damit falsch — die Ablation MUSS die `relation_type`-Verteilung mitmessen (siehe B1). Das ändert nichts am Verdikt (Off-Taxonomy-Schreiber abzuschalten ist erst recht richtig), aber es ändert die Messmethodik.

### G2 — **KRITISCH: Der MERGE-Guard schützt nichts. ADR-Abschnitt „MERGE-Semantik" ist faktisch falsch.**

Der ADR behauptet (Zeile 60): *„relation_type: geschützt — Round 1s typisierter Wert überlebt."*

Der Guard in `neo4j_client.py:777-781` prüft gegen den String-Literal `'RELATES_TO'`:
```cypher
r.relation_type = CASE
    WHEN rel.relation_type <> 'RELATES_TO' THEN rel.relation_type   -- feuert fast immer!
    ...
```
Aber **kein Extraktor produziert je den Wert `'RELATES_TO'`**:
- Round-1-Generic ist `'RELATED_TO'` (mit D — `extraction_service.py:139`, `:759`)
- Round-2-Generic ist ebenfalls `'RELATED_TO'` (Prompt-Liste, `relation_extractor.py:55`)
- `'RELATES_TO'` entsteht nur als Fallback, wenn gar kein Typ-Key existiert (`neo4j_client.py:793-795`)

Damit feuert bei jeder Round-2-Schreibung der **erste** CASE-Zweig: Round 2 überschreibt Round-1-`relation_type` bei **jeder** `(source, target)`-Kollision — auch typisiert→generic-Downgrades (`CAUSES` → `RELATED_TO`). Zusammen mit `description`/`weight` (immer überschrieben, plain `SET`) heißt das: **Round 2 degradiert heute aktiv die ADR-060-Qualität von Round 1.** Sprint 128s gemessene 84.5 % Relation-Specificity enthielten diesen Schaden bereits — nach Abschaltung sollte Specificity **steigen** (Ablation-Metrik, B1).

Folgen: (a) ADR-Sektion „MERGE-Semantik" korrigieren; (b) Ablation-Metrik „Anteil generic" muss auf `'RELATED_TO'` matchen, nicht `'RELATES_TO'`; (c) der kaputte Guard selbst ist ein separates TD-Item (nicht PR-1-Scope — mit Round 2 aus gibt es im Default-Betrieb nur noch einen Schreiber).

### G3 — `asyncio.sleep(1.0)`: PR-1 ok, PR-2-Entfernung hat eine übersehene Abhängigkeit

Im Patch bleibt das Sleep (`graph_extraction.py:360`) vor dem Branch — für PR-1 korrekt und unkritisch. **Aber:** Der ADR begründet die spätere Entfernung mit „kein späterer Neo4j-Query mehr". Das stimmt nicht ganz: `create_section_nodes` (`graph_extraction.py:623`) läuft nach dem Branch und MATCHt Entities, die Round 1 geschrieben hat (`defines_entity_rels`). Das ist potenziell dieselbe Sichtbarkeits-Race, die das Sleep in Sprint 33 gepflastert hat. PR-2 darf das Sleep nur entfernen, wenn verifiziert ist, dass `store_chunks_and_provenance` und `create_section_nodes` über dieselbe Driver-Session/Causal-Consistency laufen — sonst Sleep vor die Section-Nodes verschieben statt löschen.

### G4 — SSE-Progress / Frontend: **kein Bruch** (verifiziert)

- `emit_progress` schreibt in eine phasen-agnostische Queue; `phase` ist freier String ohne Enum-Validierung (`progress_events.py:44-77`); `format_progress_message` behandelt `total=0` sauber (`:232-235`).
- Das Frontend referenziert `relation_extraction` **nirgends** (grep über `frontend/src`: 0 Treffer). Kein Konsument erwartet die Phase.
- `GraphViewer.tsx` rendert, was Neo4j liefert — 30–50 % weniger Kanten ist kein Layout-Bruch, eher Entlastung.
- **Echte sichtbare Änderung:** `UploadResultCard.tsx` / `ExtractionSummary.tsx` zeigen `relations_count` aus der Upload-Response (`retrieval.py:762` ← `state["relations_count"]`). Heute zählt dieses Feld **nur Round-2-Relationen** (`graph_extraction.py:567`) — Round 1 wurde nie mitgezählt, die API under-reported also bisher. Mit Flag-off wird der Wert semantisch korrekter (Round-1-Zahl). Kein Bug, aber im ADR als API-Semantik-Änderung dokumentieren.

### G5 — State-/Monitoring-Konsistenz: Skip-Log ist ok, aber zwei Fixes nötig

- Es gibt **keine Grafana-Dashboards, die auf `TIMING_relation_extraction_*` oder den `PhaseLatencyTracker relation_extraction` referenzieren** (kein `monitoring/`/`grafana/`-Treffer im Repo). Der Wegfall der Log-Events im Skip-Zweig bricht nichts Maschinelles; das vorgeschlagene `round2_relation_extraction_skipped`-Event genügt.
- **Fix 1:** Das Skip-Log im Patch hat **kein `document_id`-Feld** — jede andere Log-Zeile im Node hat eins. Ergänzen.
- **Fix 2 (wichtiger):** Der Patch setzt `relations_count = stats.total_relations` — das ist die **extrahierte** Zahl (`extraction_pipeline.py:460` = `len(all_relations)` nach Dedup/Hygiene), nicht die **gespeicherte** (`total_relations_stored`, `:448`, fehlt im stats-Dict!). Wegen Entity-MATCH-Misses beim MERGE ist stored ≤ extracted. `extraction_pipeline.py` muss `total_relations_stored` ins `aggregate_stats` aufnehmen und der Skip-Zweig diesen Wert verwenden — sonst over-reported die API.
- **Latenter Bugfix gratis:** Das Community-Detection-Gate im „immediate"-Mode (`graph_extraction.py:703`, `relations_created > 0`) hängt an `relations_count`. Heute: wenn Round 2 zufällig 0 liefert, Round 1 aber 100 Relations hat, wird CD fälschlich geskippt. Mit dem Patch ist das Gate korrekt von Round 1 gespeist. Als Testfall aufnehmen (C, U5).

### G6 — Env-Var-Semantik: `.lower() == "true"` ist repo-konsistent; **kein** strtobool-Helper einführen

Repo-Bestand (verifiziert):
- `AEGIS_LLM_THINKING`: `os.environ.get(...).lower() == "true"`, **Laufzeit-Read pro Call** (`aegis_llm_proxy.py:1195`, `:1393`)
- `AEGIS_USE_CROSS_SENTENCE` (`cross_sentence_extractor.py:36`) und `AEGIS_USE_LEGACY_CASCADE` (`extraction_cascade.py:32`): `== "1"`-Vergleich, **Import-Zeit-Konstante**
- `strtobool`: existiert **nirgends** in `src/`

Der ADR-Vorschlag entspricht exakt dem `AEGIS_LLM_THINKING`-Muster — das ist die richtige Wahl: (a) Laufzeit-Read macht die Unit-Tests trivial (`monkeypatch.setenv` ohne `importlib.reload`; das Import-Zeit-Muster von `AEGIS_USE_CROSS_SENTENCE` ist test-feindlich), (b) ein strtobool-Helper für ein einzelnes Flag wäre Scope-Creep. **Aber:** `"1"`, `"yes"`, `"on"` werden NICHT akzeptiert — exakt akzeptierten Wert (`true`, case-insensitive) in `.env.template` + `docs/CLAUDE_extended.md` dokumentieren.

### G7 — Laufzeit-Read ≠ „Rollback ohne Restart": ADR-Rollback-Wording korrigieren

`os.getenv` liest das **Prozess**-Environment — das ist im Docker-Betrieb beim Container-Start eingefroren. Ein `.env`-Flip wirkt erst nach `docker compose up -d --force-recreate api`. Der ADR sagt in Zeile 132 beides („kein Restart nötig … Falls … erst bei API-Restart wirksam") — das Erste ist im Deployment-Kontext falsch und muss raus. Korrekt: *Rollback = Env-Flip + Container-Recreate (~10 s), kein Code-Change, kein Rebuild.* Der Laufzeit-Read bleibt trotzdem richtig (Testbarkeit, G6).

### G8 — Sprint-128-Rückblick: dasselbe Muster, damals nicht miterkannt

`extraction_pipeline.py:139-141` dokumentiert die Sprint-128-Entfernung von `ainsert_custom_kg`: *„92% overhead and overwrote typed relations with generic RELATED_TO"*. Round 2 ist **exakt dasselbe Muster** — ein zweiter Schreiber, der typisierte Relations degradiert (siehe G2) — nur in einem anderen Node (`graph_extraction.py` statt LightRAG-Ingestion). In den Sprint-128-Dokumenten gibt es **keinen** Kommentar zu Round 2 (grep über `docs/sprints/`: 0 Treffer für Round-2-Varianten); es wurde schlicht übersehen, weil der Refactor auf das LightRAG-Modul scoped war. ADR-064 ist die konsequente Vervollständigung von Sprint 128 / ADR-061 — das gehört so in den ADR-Kontext (stärkt die Begründung).

---

## B) Entschiedene Design-Fragen

### B1 — Ablation-Metriken und Toleranzen (entschieden)

Primärmetriken, jeweils pro Doc in **frischem, run-eigenem Namespace** (löst das Doc-übergreifende-Entities-Problem: namespace-scoped zählen, keine Kontamination durch Alt-Daten):

| # | Metrik | Cypher-Basis | Pass-Kriterium |
|---|--------|--------------|----------------|
| M1 | Unique `(source, target)`-Paare | `MATCH (a:base)-[r:RELATES_TO]->(b:base) WHERE r.namespace_id=$ns RETURN count(r)` | Verlust ≤ **15 %** vs. Flag-on-Run |
| M2 | Anzahl **typisierter** Relations (`r.relation_type` ∈ UNIVERSAL_RELATION_TYPES ohne `RELATED_TO`) | wie M1 + Filter | Verlust ≤ **5 %** (Round 2 kann keine ADR-060-Typen beitragen; mehr Verlust = Mess-Rauschen-Alarm) |
| M3 | Generic-Anteil: `r.relation_type IN ['RELATED_TO','RELATES_TO']` / gesamt | wie M1 | **sinkt** (Flag-off < Flag-on); wegen G2 auf **`RELATED_TO`** matchen, `RELATES_TO` nur als Alt-Daten-Fallback mitzählen |
| M4 | Off-Taxonomy-Anteil (`relation_type` ∉ UNIVERSAL_RELATION_TYPES) | wie M1 | Flag-off: **→ 0** (nur Round 2 schreibt off-taxonomy) |
| M5 | Wall-Zeit pro Doc (HTTP) | `measure_baseline.py` | −30–50 % (Erwartung, kein Hard-Gate) |

„Relations pro Doc" (raw count) ist als Primärmetrik **verworfen** — sie vermischt Kollisions-Überschreibungen mit echten Extra-Kanten; M1 (unique Paare) ist die ehrliche Coverage-Zahl. Die 15 % gelten für M1.

**Warum 15 % bleibt:** Round-2-only-Kanten sind per Konstruktion untypisiert-assoziativ („clearly related", `relation_extractor.py:51`) und für das typisierte Graph-Retrieval (ADR-060) nachrangig. 15 % Paar-Verlust bei gleichzeitig steigender Typisierungs-Quote (M3↓, M2 stabil) ist ein guter Tausch. > 15 % → Flag an, Option D/E prüfen (wie ADR).

### B2 — Stichprobe (entschieden)

- **Verpflichtend:** dieselben **5 Docs** aus `BASELINE_INGESTION_2026-07-21.md` (`data/ragas_phase1_contexts/`, IDs 0985/2013/2690/0368/0370), **2 Runs pro Flag-Zustand** in je frischem Namespace (`ablation_r2on_run{1,2}`, `ablation_r2off_run{1,2}`). Der Doppel-Run quantifiziert LLM-Nondeterminismus-Rauschen (temp 0.1 ≠ deterministisch) — ohne Varianzschätzung ist „≤ 15 %" nicht interpretierbar. Doc 2 (2.3 KB, Cache-Hit-Anomalie der Baseline) dabei re-messen.
- **Nicht verpflichtend** (nice-to-have, +0.5 Tag): das Sprint-128-15-Doc-E2E-Set als Domain-Stratifikation (Referenz: 212 Entities / 626 Relations / 84.5 % Specificity — mit Round 2 gemessen, direkt vergleichbar). Medical/legal-Stratifikation ist mit den vorhandenen RAGAS-Tech-Contexts nicht ehrlich machbar — nicht erfinden, sondern als Limitation dokumentieren.

### B3 — RAGAS-Retrieval-Check (entschieden, präzisiert)

- **Quelle:** `data/evaluation/ragas_phase1_questions.jsonl` — exakt die Fragen, deren Kontext-IDs den 5 Baseline-Docs entsprechen (Manifest: `data/evaluation/ragas_phase1_manifest.csv`, IDs 0985, 2013, 2690, 0368, 0370). Das sind je nach Datensatz ~5–15 Fragen; falls < 10, mit den nächsten IDs desselben Manifests auf 10 auffüllen und die IDs im Ablation-Report festschreiben.
- **Metriken:** Context Precision + Context Recall (die Sprint-127-Referenzmetriken, CP=0.739/CR=0.760), je gegen den Flag-on- und Flag-off-Namespace.
- **Gate:** CP/CR-Delta ≥ −0.05 absolut = Pass. Größerer Einbruch → Befund analysieren, bevor PR-2 (Hard-Delete) freigegeben wird; PR-1 (Flag) darf trotzdem mergen, weil reversibel.

---

## C) Akzeptanz-Tests („Grün-Marker")

### C1 — Unit-Tests (`tests/unit/components/ingestion/nodes/test_graph_extraction.py`)

Bestehende Suite: 12 Tests, alle laufen implizit mit Round-2-Verhalten (u.a. `test_graph_extraction_relation_extraction` :270, `test_graph_extraction_community_skipped_no_relations` :450). Die Fixtures `mock_relation_extractor` (:131) und `mock_neo4j_client` (:87) sind wiederverwendbar.

| ID | Test | Setup | Assertions |
|----|------|-------|------------|
| U1 | `test_graph_extraction_node_skips_round2_by_default` | Env-Var **nicht** gesetzt (`monkeypatch.delenv(..., raising=False)`); Mocks wie `test_graph_extraction_success` | `RelationExtractor.extract_with_gleaning` **nie** aufgerufen (`mock.assert_not_awaited()`); `neo4j_client.store_relations` aus dem Node **nicht** aufgerufen (nur via `extract_and_store_entities`-Mock); `state["relations_count"] == <stats.total_relations_stored des Mocks>`; Skip-Log `round2_relation_extraction_skipped` mit Feldern `reason="disabled_by_adr_064"`, `document_id`, `round1_relations` emittiert (structlog capture) |
| U2 | `test_graph_extraction_node_runs_round2_when_flag_true` | `monkeypatch.setenv("AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS", "true")` | `extract_with_gleaning` awaited (pro Chunk mit ≥ 2 Entities); `store_relations` aufgerufen; `state["relations_count"] == total_relations_created` (Round-2-Zählung, bisheriges Verhalten byte-identisch) |
| U3 | `test_round2_flag_rejects_non_true_values` | parametrisiert: `"1"`, `"yes"`, `"TRUE "` (trailing space), `"True"` | nur `"true"`/`"True"`/`"TRUE"` (case-insensitiv, exakt) aktivieren; `"1"`/`"yes"`/`"TRUE "` → skip. Dokumentiert die Semantik als Contract |
| U4 | `test_round2_skip_emits_no_relation_extraction_progress` | wie U1, `emit_progress` gemockt | kein `emit_progress`-Call mit `phase="relation_extraction"`; `entity_extraction`-Events unverändert vorhanden |
| U5 | `test_community_detection_immediate_uses_round1_count_when_skipped` | Flag unset, `graph_community_detection_mode="immediate"` (settings-Mock), Round-1-Stats mit `total_relations_stored=5` | Community-Detection wird **ausgeführt** (Gate `graph_extraction.py:703` sieht 5 > 0) — deckt den latenten Gate-Bug aus G5 ab |
| U6 | Bestands-Suite | keine Env-Var gesetzt in CI | Die 12 bestehenden Tests: alle, die Round-2-Verhalten asserten (mind. :270, :602, :720), auf den `flag=true`-Kontext umstellen oder auf Skip-Semantik anpassen — **kein Test darf ungewollt grün werden, weil Round 2 einfach fehlt** |

Dazu 1 Unit-Test in `tests/unit/components/graph_rag/`: `test_extraction_pipeline_reports_stored_relation_count` — `aggregate_stats["total_relations_stored"]` == Summe der `store_relations`-Returns (G5-Fix 2).

### C2 — Integration-Tests

| ID | Test | Setup | Assertions |
|----|------|-------|------------|
| I1 | `test_upload_response_relations_count_round1_only` (tests/integration) | Live-Neo4j (Testcontainer/Compose), 1 Mini-Doc (3–4 Sätze, ≥ 3 Entities), Flag unset | Upload-Response `neo4j_relationships` > 0 (`retrieval.py:762` liefert Round-1-Zahl); Neo4j: `RELATES_TO`-Kanten vorhanden; **kein** `relation_type` außerhalb UNIVERSAL_RELATION_TYPES (M4=0, beweist dass nur Round 1 geschrieben hat) |
| I2 | `test_round2_flag_true_restores_legacy_path` | wie I1 mit `AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS=true` im Test-Env | Kantenzahl ≥ I1-Zahl; Log enthält `TIMING_relation_extraction_start` |
| I3 | Fixture-Guard | CI-/Test-Env prüfen | `AEGIS_ENABLE_LEGACY_ROUND2_RELATIONS` ist in keiner CI-Config/`conftest.py`/`.env.template`-Default gesetzt (ADR-Umsetzungshinweis 4, als asserted Check statt Hoffnung) |

### C3 — Ablation-Test (Pass/Fail-Gates)

Skript: Erweiterung von `measure_baseline.py` (Scratchpad → nach `scripts/` heben als `scripts/ablation_round2.py`). Ablauf: B2-Design (5 Docs × 2 Flag-Zustände × 2 Runs, frische Namespaces), danach Cypher-Auswertung M1–M5 pro Namespace, Ergebnis als `docs/analysis/BASELINE_ROUND2_ABLATION_2026-07-21.md`.

**Pass** (alle vier): M1-Verlust ≤ 15 % · M2-Verlust ≤ 5 % · M3 sinkt · M4 = 0 im Flag-off-Run. **Zusätzlich** B3-RAGAS: CP/CR-Delta ≥ −0.05. M5 (Wall-Zeit) wird berichtet, ist aber kein Gate.
**Fail** → Flag bleibt implementiert, Default wird vor Merge auf `true` gestellt (Verhalten unverändert ausgeliefert), Optionen D/E neu bewerten. PR-1 ist auch im Fail-Fall nicht verloren.

### C4 — Rollback-Test

| ID | Test | Assertions |
|----|------|------------|
| R1 | Flag-Flip-Roundtrip (Integration, gleicher Aufbau wie I1/I2) | Sequenz: Ingest Doc A (Flag off) → Ingest Doc B (Flag on) → Ingest Doc C (Flag off). Doc B hat Round-2-Verhalten (I2-Assertions), Doc A und C identisches Skip-Verhalten; keine State-Leckage zwischen Runs (Laufzeit-Read verifiziert) |
| R2 | Deployment-Rollback (manuell, dokumentiert im Ablation-Report) | `.env`-Flip + `docker compose up -d --force-recreate api` (~10 s) → nächster Upload zeigt `TIMING_relation_extraction_start` im Log. Bestätigt G7-korrigiertes Rollback-Verfahren |

---

## D) Verdikt: 🟡 GO mit Anpassungen

Der ADR ist in Entscheidung, Optionsabwägung und Vorgehen (Flag → Ablation → konditionales Hard-Delete) solide und wird durch die Prüfung **gestärkt** (G2, G8: Round 2 degradiert aktiv Round-1-Qualität; ADR-064 vervollständigt Sprint 128). Vor der Implementierung durch Sonnet sind folgende Änderungen verbindlich:

1. **ADR-Sektion „MERGE-Semantik" korrigieren** (G2): `relation_type` ist NICHT geschützt — der Guard prüft `'RELATES_TO'`, die Extraktoren liefern `'RELATED_TO'`/typisierte Werte; Round 2 überschreibt bei jeder Kollision. Kaputten Guard als TD-Item erfassen (Fix nicht in PR-1).
2. **`extraction_pipeline.py`: `total_relations_stored` ins `aggregate_stats`-Dict** aufnehmen (`:448` existiert bereits als lokale Variable) und **Skip-Zweig setzt `relations_count` auf stored, nicht extracted** (G5-Fix 2). Betroffen: Patch-Zeilen mit `stats.total_relations`.
3. **Skip-Log um `document_id=state["document_id"]` ergänzen** (G5-Fix 1).
4. **Ablation-Metrik-Set M1–M5 aus B1 in den ADR-Testplan übernehmen** — insbesondere: unique Paare statt Raw-Count, Generic-Match auf `'RELATED_TO'`, M4 (Off-Taxonomy → 0) als neues Gate, 2 Runs pro Zustand für Varianz (B2).
5. **Rollback-Sektion umformulieren** (G7): Env-Flip wirkt erst nach `--force-recreate api`; „kein Restart nötig" streichen.
6. **PR-2-Vorbehalt ergänzen** (G3): `sleep(1.0)`-Entfernung erst nach Verifikation, dass `create_section_nodes` (`graph_extraction.py:623`) nicht dieselbe Sichtbarkeits-Race trifft; sonst Sleep verschieben statt löschen.
7. **Test-Umfang = C1–C4** dieses Reports statt der zwei im ADR genannten Unit-Tests; Bestands-Suite gemäß U6 migrieren. `.env.template` + `docs/CLAUDE_extended.md`: exakte Flag-Semantik (`"true"`, case-insensitiv, Laufzeit-Read) dokumentieren (G6).

Kein 🔴-Befund: Nichts davon stellt Flag-Ansatz, Default-off oder den Ablation-vor-Hard-Delete-Plan in Frage. Aufwandsschätzung PR-1 bleibt bei 3 SP (Anpassungen 1–3, 5–7 sind klein; 4 betrifft den Mess-Schritt).

---

## Anhang: Verifikations-Log

| ADR-Behauptung | Prüfung | Ergebnis |
|---|---|---|
| Round 1 und Round 2 nutzen dieselbe `store_relations` | `extraction_pipeline.py:443`, `graph_extraction.py:501` | ✅ |
| Round 2 = „gleiches LLM" | beide via AegisLLMProxy + `settings.extraction_llm_model` (`relation_extractor.py:147-150`, `extraction_service.py:2444`) | ✅ Modell ja, ❌ Prompt/Taxonomie nein (G1) |
| „relation_type geschützt durch MERGE-Guard" | `neo4j_client.py:777-781` vs. `extraction_service.py:139/759` vs. `relation_extractor.py:55` | ❌ **falsch** — String-Mismatch `RELATED_TO`≠`RELATES_TO` (G2) |
| SSE/Frontend bricht bei Skip nicht | `progress_events.py:44-77,232-235`; grep `frontend/src` → 0 Treffer für `relation_extraction` | ✅ kein Bruch (G4) |
| Grafana verliert Metrik | kein `monitoring/`/`grafana/`-Verzeichnis referenziert `TIMING_relation_extraction` | ✅ kein maschineller Konsument (G5) |
| Env-Var-Muster konsistent | `aegis_llm_proxy.py:1195` (gleich), `cross_sentence_extractor.py:36` / `extraction_cascade.py:32` (anders: `=="1"`, import-time); kein `strtobool` in `src/` | ✅ ADR-Wahl = `AEGIS_LLM_THINKING`-Muster (G6) |
| `relations_count`-Konsumenten | `retrieval.py:762` (API-Response), `graph_extraction.py:676,703` (CD-Gate), Frontend `UploadResultCard.tsx`/`ExtractionSummary.tsx` | ⚠️ Semantik-Wechsel + stored/extracted-Mismatch (G5) |
| Sprint 128 hat Round 2 übersehen | `extraction_pipeline.py:139-141` (Muster-Beschreibung); grep `docs/sprints/` → 0 Round-2-Treffer | ✅ gleiche Muster-Klasse, damals out-of-scope (G8) |
| RAGAS-Fragen existieren | `data/evaluation/ragas_phase1_questions.jsonl`, `ragas_phase1_manifest.csv`, Contexts in `data/ragas_phase1_contexts/` | ✅ (B3) |
