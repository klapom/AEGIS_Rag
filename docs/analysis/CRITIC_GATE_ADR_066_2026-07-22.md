# Critic-Gate: ADR-066 (Qwen-Prompt-Kompatibilität / Bug A)

**Datum:** 2026-07-22
**Critic:** Fable-5 (Pre-Sprint Critic-Gate gemäß globalem CLAUDE.md)
**Geprüftes Artefakt:** `docs/adr/ADR-066-qwen-prompt-compatibility.md` (Commit `3ad7686`, Status: Proposed)
**Methode:** Deep-Read der Kontext-Dateien + Code-Verifikation mit `path:line`-Beleg + **drei Live-Probes gegen den echten Qwen-Endpoint** (byte-exakte Replikation des `_call_vllm`-Requests) + Env-/Redis-Zustandsprüfung des Prod-Systems
**Vorgänger-Referenz:** `docs/analysis/CRITIC_GATE_ADR_064_2026-07-21.md` (🟡, 7 Änderungen)

---

## A) Verdikt vorab: 🔴 STOP (nur für die Implementierung — Phase 0 startet sofort)

**Eine byte-exakte Replikation des Requests, den `_call_vllm` produziert, liefert gegen den
echten `qwen36-35b`-Endpoint mit allen drei verdächtigten Prompts sauberes, parsebares JSON —
R1, R2 und R3 sind damit als hinreichende Ursachen empirisch widerlegt, und der real aktive
Extraktions-Pfad (Legacy-Cascade via `AEGIS_USE_LEGACY_CASCADE=1`) ist nicht der, den der ADR
analysiert.** Ein 7-SP-Prompt-Rewrite auf dieser Beweislage riskiert, einen Nicht-Bug zu fixen,
während die echte Ursache (ein per-Chunk verschluckter Fehler unbekannter Art,
`extraction_pipeline.py:236`) unbehandelt bleibt. Der STOP gilt für den A+D-Bau; die in
Abschnitt E definierte **Phase-0-Reproduktion (~30 min)** kann und soll sofort laufen. Nach
Phase 0 wird der ADR auf Beweisbasis umgeschrieben und erneut gegated.

Dieses Verdikt ist kein Vorwurf an den Draft — er hat R3 selbst als "needs Critic verification"
markiert und Q1 exakt diese Prüfung beauftragt. Die Prüfung fiel nur anders aus als erwartet.

---

## B) Root-Cause-Verifikation (empirisch)

### B0. Warum die Primär-Evidenz weg ist

Die Log-Zeilen des Cold-Cache-Fail-Runs (21.07., 22:58) sind **unwiederbringlich verloren**:
`aegis-api` wurde nach der Ablation force-recreated (Container "Up 10 hours", `docker logs`
seit 22:30 des 21.07.: 0 Treffer für `parsing_llm_response`/`json_parse_failed`). Dabei ist
`_parse_json_response` forensisch ideal instrumentiert — es loggt **`response_full`** bei
jedem Call (`extraction_service.py:1631-1636`). Die Antwort auf Q1 stand also gestern Abend
im Log und wurde durch das Recreate zerstört. → Verfahrensregel in D-9.

### B1. Probe-Methodik

Da die Original-Responses weg sind, wurde der Live-Pfad nachgestellt. Der Request-Body wurde
**byte-identisch zu `_call_vllm`** konstruiert (`src/domains/llm_integration/proxy/`
`aegis_llm_proxy.py:1002-1024`): single User-Message, `temperature=0.1`,
`max_tokens=min(4096*2, 32768)=8192`, `chat_template_kwargs={"enable_thinking": false}`,
POST an `http://192.168.178.10:32000/v1/chat/completions`, `model=qwen36-35b`
(served-ID verifiziert via `/v1/models`; Root: `Qwen/Qwen3.6-35B-A3B-FP8`). Die
Prompt-Konstanten wurden **aus dem Worktree importiert**, nicht abgetippt.

Probe-Skripte (Session-Scratchpad, für Reproduktion):
- `scratchpad/qwen_probe.py` (DSPy-Entity-Prompt, Varianten A/B)
- `scratchpad/qwen_probe2.py` (Stage-2-Enrichment + Stage-3-Relation-Prompt)

**Limitation (ehrlich):** Probe-Text war ~120 Wörter (456 Prompt-Tokens). Reale Chunks sind
800–1800 Tokens (ADR-039). Ein größenabhängiger Effekt ist nicht ausgeschlossen — deshalb ist
Phase 0 mit echten Docs Pflicht und dieses Ergebnis "widerlegt als *hinreichende* Ursache",
nicht "widerlegt unter allen Bedingungen".

### B2. Probe-Ergebnisse

| Probe | Prompt | Setup | Ergebnis |
|---|---|---|---|
| **A** | `DSPY_OPTIMIZED_ENTITY_PROMPT` (:186) | exakt wie `_call_vllm` (thinking off) | **8.8 s, 612 completion tokens, `finish_reason=stop`. Content = reiner JSON-Array, beginnt mit `[`, ~24 valide Entities (PERSON/ORGANIZATION/PRODUCT/QUANTITY/…). Strategy-2-Parse: OK.** |
| **B** | dito | Template-Default (kein `chat_template_kwargs`) | 77.4 s, 5258 tokens. Content beginnt mit **Plain-Text-CoT** (`"Here's a thinking process:"` — **KEINE `<think>`-Tags!**), endet mit vollständigem JSON-Array. `reasoning`-Feld im Message-Objekt vorhanden, aber `null`; `reasoning_content` existiert nicht. |
| **C** | `RELATION_EXTRACTION_FROM_ENTITIES_PROMPT` (:316, `---Role---`-Marker) | wie A | **Perfektes JSON, 6 typisierte Relations (EMPLOYS/USES/DEPENDS_ON/…), Strategy-2-Parse: OK.** |

(Probe für `ENTITY_ENRICHMENT_PROMPT` (:271) lief im selben Skript; Output ebenfalls
Array-förmig — Fixture liegt im Scratchpad, gehört in die Test-Suite, E/U-Tests.)

### B3. Konsequenz für R1 (DSPy-Prompts "Nemotron-gefittet")

**Widerlegt als hinreichende Ursache.** Der exakte Prod-Request mit dem DSPy-Prompt liefert
sauberes JSON. Zusätzlich zwei strukturelle Gegenargumente:

1. Der DSPy-Prompt ist **kein exotisch MIPROv2-geformtes Artefakt** — er ist beinahe
   textidentisch mit `GENERIC_ENTITY_EXTRACTION_PROMPT` (:22). Diff: ausformulierte
   Typ-Beschreibungen + `Domain:`-Zeile. Die ADR-These "Instruction-Formulierung … für die
   Nemotron-Response-Distribution gefittet. Nicht portabel." (Abschnitt R1) ist durch den
   tatsächlichen Prompt-Text nicht gedeckt.
2. Daraus folgt auch: **wenn** die DSPy-Prompts auf Qwen scheiterten, scheiterten die
   Legacy-Prompts fast sicher mit — der `AEGIS_USE_LEGACY_PROMPTS`-Rollback (AC-5) wäre
   keine Diversität, sondern derselbe Prompt in grün (siehe G2).

### B4. Konsequenz für R2 (`---Role---`-Marker-Prompt)

**Widerlegt als hinreichende Ursache** (Probe C). Zusätzlich: der R2-Callsite
(`extraction_service.py:2413`, `_pipeline_stage3_relation_extraction`) liegt in der
**SpaCy-First-Pipeline, die in Prod deaktiviert ist** (B6) — R2 beschreibt einen Prompt, der
im Fail-Run mutmaßlich nie gefeuert hat.

### B5. Konsequenz für R3 (`<think>`-Parser-Bypass) — die beauftragte Verifikation

**In der behaupteten Form widerlegt; ein realer, aber anderer Parser-Befund bleibt.**

1. **Faktisch falsch am Draft:** Qwen3.6 emittiert auf diesem Endpoint **keine
   `<think>`-Tags** — weder mit noch ohne `enable_thinking=false`. Default-Reasoning kommt
   als Plain-Text-CoT im `content` (Probe B). Ein `<think>…</think>`-Stripper (Option D
   wie spezifiziert) würde einen Token strippen, der nicht vorkommt.
2. **Der Proxy ist bereits gehärtet, was der ADR übersieht:** `_call_vllm` sendet
   `chat_template_kwargs={"enable_thinking": false}` (`aegis_llm_proxy.py:1022`), verdoppelt
   `max_tokens` als Reasoning-Leak-Puffer (`:1017`) und hat einen
   `reasoning_content`-Fallback (`:1040-1054`). Der ADR erwähnt nichts davon.
3. **Code-Trace der Parser-Kette** (statisch, `extraction_service.py`):
   - Strategie 1 (Code-Fence, `:1642`), Strategie 2 (Greedy-Regex `\[.*\]`, `:1650`),
     Strategie 3 (Full-Response, `:1657`), danach Repair (`:1668`) und bei
     `JSONDecodeError` **Individual-Object-Fallback auf der VOLLEN Response**
     (`:1835`, `_extract_json_objects_individually` :1195).
   - Ein `<think>`-präfixierter Response **bypassed die Kette NICHT**, solange irgendwo ein
     vollständiges `{…}`-Objekt mit `name`+`type` steht — der Individual-Fallback fängt es.
     Total-0 pro Call erfordert eine Response **ohne ein einziges valides Objekt** (leer,
     komplett trunkiert, oder Exception vor dem Parse).
   - **Realer Befund stattdessen (R3′):** Die Greedy-Regex `\[.*\]` spannt bei
     Inline-CoT-Responses vom ersten `[` im CoT bis zum letzten `]` → `json.loads` failt →
     Individual-Fallback läuft über die volle Response **inklusive CoT-Entwurfsobjekten und
     ge-echoten Few-Shot-Beispielen** (die Prompts enthalten `{"name": "NVIDIA", …}` als
     Beispiel!) → **Qualitäts-/Duplikat-Hazard, kein 0-Entities-Hazard.** Das ist die
     korrekte Spezifikation für Option D (siehe D-3).

**Q1-Antwort:** R3 ist **nicht load-bearing für Bug A**. Ein Parser-Hardening (in der
R3′-Form) ist trotzdem sinnvoll — als Robustheits-, nicht als Bugfix-Maßnahme.
**Q3-Antwort:** Gegenstandslos für `<think>`; für Inline-CoT zeigt Probe B, dass das finale
JSON-Array *nach* dem CoT vollständig ist (eher Über- als Unterextraktion) — Stripping des
CoT ist semantisch sicher, solange man **das letzte vollständige Array** nimmt.

### B6. Der eigentliche Befund: Der ADR analysiert den falschen Pfad

Verifizierter Prod-/Ablation-Zustand:

| Beobachtung | Beleg |
|---|---|
| `AEGIS_USE_LEGACY_CASCADE=1` in Prod-`.env` **UND** im Ablation-Backup `.env.pre-ablation-20260721_160957` | grep beider Dateien |
| → SpaCy-First-Pipeline **deaktiviert** (`extraction_cascade.py:32`, `should_use_spacy_first_pipeline` :218); aktiver Pfad = Legacy-Cascade | `extraction_factory.py:180,190-213` |
| Legacy-Cascade = **nur noch Rank 1** (Sprint 129 hat Rank 2/3 entfernt), `model=_DEFAULT_EXTRACTION_MODEL` = Env `EXTRACTION_LLM_MODEL` oder Default **`nemotron-3-nano:128k`** | `extraction_cascade.py:88-108` |
| Rank-1-Entity-Extraktion nutzt `get_extraction_prompts(domain)` → bei domain=None (Ablation-Upload sendet **kein** domain-Feld, nur `namespace_id`) → **generischer DSPy-Prompt** — also Probe-A-Form | `extraction_service.py:1923-1930`; `scratchpad/baseline_2026-07-21/ablation.py:79-100` |
| Routing: `engine_mode` in Redis = **`vllm`** (live ausgelesen: `aegis:llm_engine_mode`); `VLLM_MODEL=qwen36-35b` = served-ID; **`model_override`/`model_local` wird weder vom Routing noch von `_call_vllm` gelesen** — `_call_vllm` postet immer `self._vllm_model` (`:1009`) | `aegis_llm_proxy.py:838-899, 979-1024`; 0 grep-Treffer für `model_override` im Proxy |

Daraus folgt: **Der Live-Request des Fail-Runs war in Form, Modell, Flags und Prompt identisch
mit Probe A — und Probe A funktioniert.** Die ADR-Callsites 2273 (Stage 2) und 2413 (Stage 3)
liegen in totem Code; R4 ("hardcoded nemotron `:2231`") ist nur deshalb harmlos, weil
`_call_vllm` den Override **stillschweigend ignoriert** — eine brüchige Koinzidenz, kein Design
(D-6). Die Nemotron-Modell-Strings im Warm-Log stammen aus Bug-B-Zombie-Cache **und** aus dem
Rank-1-Default `nemotron-3-nano:128k` — der ADR schreibt sie allein dem Cache zu.

### B7. Wie "0 Entities überall" trotzdem entsteht — die ehrliche Hypothesen-Liste

`extract_and_store_entities` fängt **jede** per-Chunk-Exception und macht weiter
(`extraction_pipeline.py:236`, `chunk_extraction_failed`). Rank-1-Fehler (Parse ODER HTTP
ODER Timeout ODER KeyError) → 3 Retries → `all_cascade_ranks_failed` → raise
(`extraction_service.py:2960-2961`) → verschluckt → Chunk trägt 0 bei. **Die 0-Entities-
Signatur beweist nur "wiederholte Exception pro Chunk", nicht "Prompt-Inkompatibilität".**
Wall-Zeiten (6.2 s/Item, skalierend mit Doc-Größe) belegen, dass echte Generierung stattfand.

Kandidaten in absteigender Priorität für Phase 0 (alle mit den Probes NICHT abgedeckt):

1. **Größeneffekt**: 1500-Token-Chunks → längere Outputs → `finish_reason=length` mitten im
   Array, oder CoT-Rückfall trotz `enable_thinking=false` bei langen Inputs.
2. **`prompt_cache`-Schreib-/Lesepfad im `generate()`-Wrapper** (Bug-B-Nachbarschaft) —
   der Proxy-Pfad zwischen `generate()` und `_call_vllm` wurde von den Probes umgangen.
3. **Ablation-Setup-Artefakt**: `network_mode: host`-Behelfs-Compose, httpx-Verhalten,
   Auth/Timeout — der Fail-Run lief auf einem handgepatchten Container (Anhang B der
   Ablation dokumentiert 5 Fehlversuche vorher).
4. **Gleaning-Pfad aktiv** (`gleaning_steps` aus ChunkingConfig, `:2832-2852`):
   zusätzliche Prompts (90/121) im Spiel; YES/NO-Check mit `max_tokens=10` gegen ein
   preamble-freudiges Modell.
5. Echte prompt-shape-Inkompatibilität **nur bei realen Chunk-Größen** (Rest-Risiko, durch
   Probe-Limitation B1 nicht ausschließbar).

**Interne Inkonsistenz, die Phase 0 auflösen muss:** Ablation Doc 5 (on-state) meldet
`entities_extracted=0` **und** 1 gespeicherte Round-2-Relation — `RelationExtractor` braucht
aber eine Entity-Liste (≥2 pro Chunk). Beides zugleich passt nicht; entweder sind die
Zähler nicht das, wofür der ADR sie hält, oder Round 2 bezieht Entities aus einer anderen
Quelle. Der ADR baut AC-Schwellen auf diesen Zählern auf, ohne ihre Semantik geklärt zu haben.

### B8. Neues Ranking nach demonstrierter Load-Bearing-Evidenz

| Rang | Ursache | Status |
|---|---|---|
| 1 | **Unbekannte per-Chunk-Exception im Legacy-Cascade-Pfad** (Kandidaten B7.1–B7.4) | **offen — einzig durch Phase 0 entscheidbar** |
| 2 | R3′ Parser-Fragilität (Greedy-Regex + CoT-Objekt-Ingestion + Beispiel-Echo) | **belegt, aber nachweislich kein 0-Entities-Verursacher**; fixwürdig |
| 3 | R1/R2 Prompt-Shape | **widerlegt als hinreichende Ursache** bei getesteten Größen; Rest-Risiko nur via B7.5 |
| — | R4 hardcoded Nemotron | kein Bug-A-Verursacher, aber von "incidental" auf "brüchige Koinzidenz" hochgestuft (D-6) |
| — | R5 Proxy | bestätigt unschuldig — mit der neuen Fußnote, dass `model_override` im vLLM-Pfad **ignoriert** wird |

Das Draft-Ranking R1 > R2 > R3 ist damit **nicht haltbar**.

---

## C) Design-Gaps

### G1 — KRITISCH: Falscher Pipeline-Pfad analysiert
Der ADR erwähnt `AEGIS_USE_LEGACY_CASCADE` mit keinem Wort, obwohl das Flag in Prod UND
während der Ablation gesetzt war und den kompletten Callsite-Graph ändert (B6). Die
Blast-Radius-Aussagen ("RelationExtractor unberührt", Stage-3-Scope) beziehen sich teils auf
toten Code. Der Legacy-Relations-Pfad läuft über `get_extraction_prompts` → DSPy-Relation-
Prompt (`:3387`) + Relationship-Gleaning (`:3890`, `:3964`) — keiner dieser Callsites steht
im ADR. Zusätzlich offene Grundsatzfrage an Klaus: **warum** ist der Legacy-Cascade aktiv,
und ist er der Ziel-Zustand? (Die SpaCy-First-Stages 2/3 haben hartcodiert
`model="nemotron-3-nano:latest"`, `extraction_cascade.py:153,165` — auch der Alternativ-Pfad
ist Nemotron-verdrahtet.) → F-1.

### G2 — KRITISCH: AC-5-Rollback ist kein funktionierender Escape
Drei unabhängige Defekte:
(a) `AEGIS_USE_LEGACY_PROMPTS=1` greift erst auf **Priorität 3/4** der Prompt-Kette —
Domain-trained-Prompts aus Neo4j (Prio 1, `extraction_service.py:1480-1495`) und
Domain-enriched-Prompts aus YAML (Prio 2, `:1497-1526`) **umgehen das Flag vollständig**.
Für jedes Dokument mit trainierter/ge-hinteter Domain ist der Rollback wirkungslos.
(b) `USE_DSPY_PROMPTS` ist eine **Import-Zeit-Konstante** (`extraction_prompts.py:16`) —
Container-Recreate nötig (ok, aber dokumentieren; Tests brauchen `importlib.reload`, das
ADR-064-Gate hat dieses Muster als test-feindlich eingestuft, G6 dort).
(c) Legacy-GENERIC- und DSPy-Prompts sind nahezu identisch (B3.1) — der Rollback bietet
**keine Verhaltens-Diversität**. Falls Prompts wirklich das Problem wären, fiele der
Rollback mit. Bonus: Docstring `:1451` referenziert eine nicht existierende Env-Var
`AEGIS_USE_DSPY_PROMPTS`.

### G3 — Gleaning-/Enrichment-/Continuation-Prompts unscoped
Der ADR scoped nur Entity/Relation-Hauptprompts. Unter Legacy-Cascade mit `gleaning_steps>0`
sind `COMPLETENESS_CHECK_PROMPT` (:69), `CONTINUATION_EXTRACTION_PROMPT` (:90),
`RELATIONSHIP_COMPLETENESS_CHECK_PROMPT` (:121), `RELATIONSHIP_CONTINUATION_PROMPT` (:149)
im Hot-Path. Der YES/NO-Check läuft mit `max_tokens=10` (`extraction_service.py:2997`) —
ein Modell, das mit Preamble antwortet, liefert in 10 Tokens evtl. weder YES noch NO;
`"YES" in response` ist dann False → Extraktion gilt als "complete" → **stiller
Qualitätsverlust ohne Fehler**. Ob Gleaning in Prod aktiv ist (ChunkingConfig), ist
unverifiziert → Phase-0-Checkliste.

### G4 — AC-6 (Nemotron-Regression) hat keinen Infra-Plan und einen Zielkonflikt
Der Prod-vLLM-Endpoint (32000) hostet `qwen36-35b`/`qwen35-35b` und wird von pommer-agents
mitgenutzt. Ein Nemotron-Cold-Test erfordert einen eigenen vLLM-Start (lokal Port 8001,
NVFP4-Modell) auf derselben 128-GB-Unified-Memory-Maschine, auf der der Qwen-Server schon
läuft — Speicher-Koordination nötig, im ADR unerwähnt. Zielkonflikt: Wenn die neuen
robusten Prompts auf Nemotron minimal schlechter abschneiden, failt ein hartes AC-6 den
Sprint, obwohl Klaus' dokumentierte Richtung Qwen ist. Empfehlung: **AC-6 zu Soft-Gate
(Report-only) abstufen**; Nemotron-Sicherheit kommt primär über den `VLLM_MODEL`-Env-Rollback
(Option C), nicht über Prompt-Bidirektionalität. → D-5, F-2.

### G5 — AC-1/AC-2-Schwellen auf Zombie-Zahlen geankert
"Doc 4 = 395 Relations, 67 % typisiert" ist eine **Warm-Cache-Messung**, die laut
Ablation-Report selbst aus dem Nemotron-Zombie-Cache bedient wurde; "60–100 Entities pro
13-KB-Doc" ist im ADR unbelegt. Die abgeleiteten 45/200/30-Schwellen sind daher
Pseudo-Präzision. Q4-Antwort: **die Self-Referential-Variante des Drafts ist die richtige**
(erst frische Qwen-Baseline mit repariertem Pfad, dann ACs als ≥90 % davon), ergänzt um
absolute Floors (Doc 4 ≥ 30 Entities, ≥ 15 unique Pairs — unterhalb davon ist offensichtlich
etwas kaputt). Wichtig: Probe A zeigt eher **Über-Extraktion** (24 Entities auf 120 Wörter,
inkl. QUANTITY-Spam wie "15 documents") — das Qwen-Risiko ist **Rauschen, nicht Leere**.
Deshalb brauchen AC-1/2 zusätzlich Rausch-Metriken: Typ-Verteilung, %QUANTITY/DATE_TIME,
Dedup-Rate, und die M2/M3/M4-Metriken aus dem ADR-064-Gate wiederverwenden.

### G6 — `MAX_ENTITIES_PER_DOC=50` wirkt pro Chunk und interagiert mit Über-Extraktion
Der Cap greift im Rank-Parse (`extraction_service.py:1961-1967`, Konstante `:1279`). Bei
Qwen-Über-Extraktion verdrängen QUANTITY-Rauschentities gute Entities innerhalb des Caps
(first-50-wins, kein Confidence-Sort erkennbar). AC-1-Ziel "Doc 5 ≥ 200" ist mit
11 Chunks × 50 = 550 theoretischem Max zwar erreichbar, aber der Cap gehört in die
Ablation-Auswertung dokumentiert.

### G7 — Option D ist gegen das falsche Symptom spezifiziert
Statt `<think>`-Stripper (kommt nicht vor, B5.1) braucht der Parser:
(a) Preamble-Strip bis zum ersten balancierten `[`/`{` **bzw. bevorzugt das LETZTE
vollständige JSON-Array** der Response (CoT-sicher, Probe B-validiert);
(b) Ersatz der Greedy-Regex `\[.*\]` (`:1650`) durch Balanced-Bracket-Scan;
(c) Guard im Individual-Fallback gegen ge-echote Few-Shot-Beispielobjekte und
CoT-Entwurfsobjekte (Duplikat-Quelle);
(d) Truncation-Handling für `finish_reason=length` (letztes vollständiges Objekt);
(e) sauberer AC-3-Metrik-Hook (Zähler statt Log-Grep, siehe E).
`_repair_json_string`/`_extract_json_objects_individually` selbst sind solide; die
Ein-Ebenen-Nesting-Grenze der Objekt-Regex (`:1213`) ist für flache Entity-Objekte ok.

### G8 — Test-Masking-Risiko + Forensik-Erhalt
`tests/unit/prompts/test_extraction_prompts.py` asserted mutmaßlich Konstanten-Inhalte —
nach Rewrite müssen diese Tests **bewusst** migriert werden (AC-4 sieht das vor, gut), aber
zusätzlich gilt: **kein Test darf grün werden, weil er den alten Prompt-Text weiter lädt**
(Import-Zeit-Konstanten! `importlib.reload`-Falle). Und: das `response_full`-Logging in
`_parse_json_response` (`:1635`) ist das zentrale Forensik-Werkzeug dieses Bugs — darf im
Zuge von "Log-Hygiene" nicht entfernt werden.

### G9 — Bug-B-Koordination unterspezifiziert
"Out of Scope, parallel in Worktree bug-b" reicht nicht: Merge-Reihenfolge und Test-Protokoll
hängen zusammen. Solange Bug B nicht gefixt ist, **muss jeder AC-Test Redis
`prompt_cache*` flushen**, sonst misst man Zombie-Antworten (der Fehler, der Bug A monatelang
versteckt hat). Wird Bug B zuerst gemerged, entfällt der Flush-Zwang (Model-Segment im Key),
und die Bug-A-Ablation wird einfacher. Empfehlung: **Bug B zuerst mergen.** → F-4.

### G10 — Zähler-Semantik ungeklärt
Die AC-Metriken hängen an `entities_extracted`/`total_relations_stored`, deren Semantik die
Doc-5-Inkonsistenz (B7, 0 Entities + 1 Relation) nicht erklärt. Das ADR-064-Gate hat bereits
stored≠extracted-Mismatches gefunden (dort G5). Vor AC-Finalisierung: einmalige Klärung,
welcher Zähler was zählt, im Phase-0-Report.

---

## D) Verbindliche Änderungen (Spec für den Implementierer)

| # | Was ist falsch | Was zu tun ist | Blocking? |
|---|---|---|---|
| **D-1** | Root-Cause-Analyse basiert auf Plausibilität; alle drei Kandidaten empirisch widerlegt (B2–B5) | **Phase 0 (instrumentierte Cold-Cache-Repro, Protokoll in E-0) als Gate VOR jeder Implementierung in den ADR aufnehmen.** ADR-Abschnitt "Root Cause Analysis" nach Phase 0 auf Beweisbasis neu schreiben; Ranking aus B8 übernehmen, bis Phase 0 es ersetzt | **JA — der STOP hängt hieran** |
| **D-2** | ADR analysiert deaktivierten Pfad (G1) | `AEGIS_USE_LEGACY_CASCADE=1` + aktiven Callsite-Graph dokumentieren (Rank-1 :1923, Relations :3387, Gleaning :2986/:3055/:3890/:3964); tote Callsites (2273/2413) als solche kennzeichnen; Ziel-Pipeline-Entscheidung von Klaus einholen (F-1) | **JA** |
| **D-3** | Option D zielt auf nicht existierende `<think>`-Tags (G7) | Option D neu spezifizieren gemäß G7 (a)–(e): Last-Array-Präferenz, Balanced-Bracket-Scan, Beispiel-Echo-Guard, Truncation-Handling, Metrik-Hook | **JA** |
| **D-4** | AC-5-Rollback wirkungslos für Domain-Pfade, Import-Zeit-Flag, keine Diversität (G2) | Entweder Flag auf Prio 1/2 ausdehnen (Legacy erzwingt Generic ÜBERALL) oder Limitation explizit in ADR + `.env.template`; Docstring-Fix `:1451`; Test dafür (E, U-5) | **JA** |
| **D-5** | AC-Schwellen auf Warm-Cache-Zombie-Zahlen geankert; AC-6 ohne Infra-Plan (G4, G5) | AC-1/2 self-referential neu ankern (E-3); Rausch-Metriken ergänzen; AC-6 zu Soft-Gate abstufen ODER Nemotron-Testhost-Plan in den ADR | **JA** |
| **D-6** | R4-Einstufung "incidental" verdeckt, dass `_call_vllm` `model_override` still ignoriert (B6) | ADR-Notiz + TD-Item: Override-Verhalten explizit machen (Log-Warnung bei ignoriertem Override); Hardcode `:2231` im selben TD | nein |
| **D-7** | Gleaning-/Continuation-Prompts unscoped (G3) | `gleaning_steps`-Prod-Wert in Phase 0 erheben; falls >0: Prompts 69/90/121/149 in Scope und AC-Abdeckung aufnehmen; YES/NO-Check robust machen (z.B. `max_tokens=10` beibehalten, aber Antwort-Regex `\b(YES|NO)\b` + Default bei Miss dokumentieren) | nein (wird JA, falls Gleaning aktiv) |
| **D-8** | Bug-B-Interaktion nur als "out of scope" (G9) | Merge-Reihenfolge festlegen (Empfehlung: **Bug B zuerst**); bis dahin Redis-Flush als Pflichtschritt in jedes AC-Testprotokoll | nein |
| **D-9** | Primär-Evidenz durch Container-Recreate zerstört (B0) | Runbook-Regel in den ADR: **vor jedem `--force-recreate` während Bug-A-Arbeit `docker logs aegis-api > logs/aegis-api-$(date +%s).log`**; Phase-0-Skript macht das automatisch | nein (aber sofort praktizieren) |
| **D-10** | Zähler-Semantik/Doc-5-Inkonsistenz (G10) | Phase-0-Report muss die 0-Entities-+-1-Relation-Anomalie erklären; AC-Metriken erst danach final formulieren | nein |

Q2-Antwort (DSPy-Konstanten behalten/löschen): **behalten als opt-in**, bis Phase 0 klärt, ob
Prompts überhaupt das Problem sind — Löschen jetzt wäre Scope-Creep auf unbewiesener Basis.
Entscheidung nach Phase 0 im ADR nachtragen.

---

## E) Akzeptanz-Test-Spezifikation

### E-0. Phase 0: Instrumentierte Cold-Cache-Reproduktion (GATE, ~30 min)

Ziel: die failing Stage mit den **vorhandenen** Logs identifizieren. Kein Code-Change nötig.

```bash
# 0. Log-Sicherung (D-9)
docker logs aegis-api > /tmp/aegis-api-pre-phase0.log 2>&1

# 1. Cold machen — Variante B des Ablation-Reports (KEIN vLLM-Restart nötig,
#    schont pommer-agents): frisches Doc, das nie im KV-Cache war
docker exec aegis-redis redis-cli --scan --pattern 'prompt_cache*' | \
  xargs -r docker exec -i aegis-redis redis-cli del
# Frisches Doc: neuer RAGAS-Phase-1-Context (~13 KB), NICHT die 5 Ablation-Docs

# 2. Ein Upload, ein Namespace
curl -X POST http://localhost:8000/api/v1/retrieval/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@fresh_doc.txt" -F "namespace_id=phase0_bug_a"

# 3. Forensik (die Reihenfolge ist der Entscheidungsbaum)
docker logs aegis-api --since 10m > /tmp/phase0.log 2>&1
grep -c "vllm_request_complete"            /tmp/phase0.log   # (i)
grep    "parsing_llm_response"             /tmp/phase0.log   # (ii) response_full!
grep    "json_parse_failed_all_strategies" /tmp/phase0.log   # (iii)
grep    "chunk_extraction_failed"          /tmp/phase0.log   # (iv) error=<Typ>!
grep    "cascade_rank_success\|all_cascade_ranks_failed\|gleaning" /tmp/phase0.log
```

**Entscheidungsbaum:**
- (i)=0 → Request erreicht vLLM nie → Routing/Infra-Bug → ADR-Optionen A/D obsolet,
  neuer RCA-Abschnitt.
- (i)>0 ∧ (iii)>0 → Parse-Fail auf realen Chunks → `response_full` aus (ii) zeigt WARUM →
  Option D (in D-3-Form) bestätigt; ob zusätzlich A nötig ist, zeigt der Response-Inhalt.
- (i)>0 ∧ (iii)=0 ∧ Entities=0 → Parse ok, Verlust downstream (Consolidation/Storage/Zähler)
  → weder A noch D fixt Bug A; neuer RCA.
- (iv) mit `error=TimeoutError/HTTPStatusError/KeyError` → jeweiliger Infra-/Code-Pfad.
- Reproduziert der Lauf **gar nicht** (Entities > 0): Bug A war ein Artefakt des
  Ablation-Behelfs-Setups → ADR-Scope schrumpft auf R3′-Hardening + Bug B; mit dem
  Prod-Compose gegentesten, bevor entwarnt wird.

Zusätzlich in Phase 0 erheben: `gleaning_steps` (ChunkingConfig), `EXTRACTION_LLM_MODEL`-Env,
Erklärung der Doc-5-Anomalie (D-10).

### E-1. Unit-Tests (Parser, `tests/unit/components/graph_rag/`)

Fixtures: die **echten Probe-Responses** aus dieser Session als Testdaten einchecken
(Scratchpad `qwen_probe*.py`-Outputs; Probe A = Clean-JSON, Probe B = Inline-CoT+JSON).

| ID | Test | Assertion |
|----|------|-----------|
| U-1 | Clean-JSON (Probe-A-Fixture) | Strategy 2, n≥20 Entities, 0 Warnings |
| U-2 | Inline-CoT + finales Array (Probe-B-Fixture) | Parser liefert NUR die Objekte des **letzten** Arrays; keine CoT-Entwurfs-/Beispiel-Objekte (heute FAILT das → Red-Test für D-3) |
| U-3 | Truncated (`finish_reason=length`, Array ohne `]`) | Individual-Fallback liefert alle vollständigen Objekte, kein Total-Fail |
| U-4 | Preamble ("Here is the JSON: […]") | Parse ok |
| U-5 | Prompt-Prioritätskette | Mit `AEGIS_USE_LEGACY_PROMPTS=1` + Domain mit trained/YAML-Prompts: dokumentiertes Verhalten (je nach D-4-Entscheid Bypass oder Nicht-Bypass) — als Contract-Test |
| U-6 | Few-Shot-Echo | Response = wortgleiches Echo des Prompt-Beispiels (`NVIDIA`/`machine learning`) + reale Objekte → Beispiel-Objekte werden nicht dupliziert ingestiert (D-3c) |
| U-7 | Bestands-Suite `tests/unit/prompts/` | Migration explizit; `importlib.reload`-sauber; kein Test grün durch alten Konstanten-Import (G8) |

### E-2. Integration (1 Test, live Endpoint)

Single-Chunk-Ingestion (Mini-Doc, 3–4 Sätze) gegen `qwen36-35b`, frischer Namespace, Redis
prompt_cache geflusht: Upload-Response Entities > 0, Neo4j enthält typisierte Entities,
`json_parse_failed_all_strategies`-Count = 0. (Das ist der Test, der Bug A je wieder
auffliegen lässt — er MUSS cold laufen, sonst testet er den Cache.)

### E-3. Ablation-Level (AC-1/AC-2 neu geankert, ersetzt Draft-Zahlen)

Protokoll: 5 Docs × 2 Runs, je frischer Namespace, Redis-Flush (bis Bug-B-Merge), frische
Doc-Varianten oder vLLM-Restart nach F-3-Absprache. Metriken M1–M5 aus dem ADR-064-Gate
wiederverwenden + Rausch-Metriken (G5).

- **Schritt 1:** Baseline-Run mit repariertem Pfad → dokumentierte Qwen-Referenzzahlen.
- **Schritt 2:** ACs = ≥ 90 % dieser Baseline in Wiederholungs-Runs, PLUS absolute Floors:
  Doc 4 ≥ 30 unique Entities, ≥ 15 unique (source,target)-Pairs, Typisierungsanteil ≥ 50 %.
- **AC-3 präzisiert:** Parse-Error-Rate = `json_parse_failed_all_strategies` ÷
  `vllm_request_complete` ≤ 5 % (exakte Zähler, keine Prosa); Implementierung als
  Counter-Metrik, nicht Log-Grep (D-3e).
- **AC-6:** Soft-Gate (Report-only) mit Nemotron auf separatem vLLM-Start ODER gestrichen
  zugunsten dokumentiertem Option-C-Rollback — nach F-2-Entscheid.
- 5-%-/90-%-Begründung: 2-Run-Varianz quantifiziert Nondeterminismus (temp 0.1 ≠ 0);
  Schwellen unterhalb der Run-zu-Run-Varianz wären Rauschen-Gates.

### E-4. Exit-Kriterium für den Fable-Adversarial-Schritt

(1) E-1 bis E-3 grün; (2) Adversarial-Fixture-Suite (Fable generiert: Mixed-Language,
Nested-Quotes, 10k-Token-Response, reine CoT ohne JSON, leerer Content, Beispiel-Echo)
ohne Crash und ohne Silent-Wrong-Data (leere Liste ist ok, falsche Objekte nicht);
(3) U-7-Audit: kein maskierter Test; (4) Phase-0-Erkenntnisse im ADR eingearbeitet und
ADR-Status auf Accepted.

---

## F) Blocker & Voraussetzungen (Klaus-Entscheide)

| # | Entscheidung/Voraussetzung | Kontext |
|---|---|---|
| **F-1** | **Ziel-Pipeline:** Legacy-Cascade behalten (dann ist er der Fix-Gegenstand) oder SpaCy-First reaktivieren (dann müssen deren Nemotron-Hardcodes `:153/:165/:2231` mit in Scope)? Warum steht `AEGIS_USE_LEGACY_CASCADE=1` in Prod? | G1, B6 |
| **F-2** | AC-6 hart vs. soft; falls hart: Nemotron-vLLM-Host/GPU-Budget-Plan | G4 |
| **F-3** | Cold-Cache-Verfahren: vLLM-Restart (pommer-agents-Absprache) vs. Frische-Docs-Protokoll (empfohlen, keine Absprache nötig) | E-0/E-3 |
| **F-4** | Merge-Reihenfolge Bug B vor Bug A (empfohlen) | G9 |
| **F-5** | Phase-0-Durchführung auf Prod-Compose (nicht auf dem Ablation-Behelfs-Setup) — Prod-Zustand laut Memory "Compose lokal auf Baseline-Config" ist herzustellen/verifizieren | B7.3 |

Keine dieser Entscheidungen blockiert den **Start von Phase 0** (F-3-Empfehlung nutzen).

---

## G) Empfohlene nächste Schritte (Reihenfolge)

1. **Sofort:** Phase 0 nach E-0 ausführen (30 min, kein Code-Change). Log-Sicherung zuerst.
2. Phase-0-Befund → Opus patcht ADR-066: RCA-Sektion neu (B8-Ranking als Ausgangspunkt),
   D-1 bis D-5 einarbeiten, Optionen neu bewerten (A könnte komplett entfallen; D in
   G7-Form bleibt vermutlich; ggf. neue Option E für den echten Befund).
3. Klaus-Entscheide F-1 bis F-5 einholen (können parallel zu 1–2 laufen).
4. Re-Gate durch Fable (kurz — nur RCA-Sektion + AC-Anker prüfen; Rest dieses Reports
   bleibt gültig).
5. Sonnet-TDD gegen E-1/E-2 (Red-Tests U-2/U-6 zuerst), dann E-3-Ablation.
6. Fable-Adversarial-Schritt nach E-4, dann Merge (nach Bug B, F-4).
7. Follow-ups als TD: D-6 (Override-Transparenz), G3 (Gleaning-Robustheit), G6 (Cap-Politik).

---

## Anhang: Verifikations-Log

| ADR-Behauptung | Prüfung | Ergebnis |
|---|---|---|
| R1: DSPy-Prompts inkompatibel mit Qwen | Live-Probe A: byte-exakter `_call_vllm`-Request, `DSPY_OPTIMIZED_ENTITY_PROMPT`, qwen36-35b | ❌ widerlegt als hinreichende Ursache — 8.8 s, reines JSON, 24 Entities, Strategy-2-Parse ok |
| R2: `---Role---`-Marker-Prompt scheitert an Qwen | Live-Probe C: `RELATION_EXTRACTION_FROM_ENTITIES_PROMPT` | ❌ widerlegt — perfektes JSON, 6 typisierte Relations |
| R3: `<think>`-Block bypassed Parser | Live-Probe B + Code-Trace `:1642-1845` | ❌ in dieser Form falsch — keine `<think>`-Tags auf diesem Endpoint (Inline-Plain-Text-CoT); Individual-Fallback fängt think-präfixierte Responses; realer Befund ist R3′ (Greedy-Regex + Objekt-Echo, Qualitäts- nicht Leere-Hazard) |
| "Parser strippt `<think>` nicht" | `_call_vllm` `:1017-1054` | ⚠️ irreführend — Proxy sendet bereits `enable_thinking:false`, 2× max_tokens, `reasoning_content`-Fallback; ADR erwähnt nichts davon |
| R4 "nur SpaCy-Fallback-Pfad, incidental" | `:2231` + Proxy-grep `model_override` → 0 Treffer | ⚠️ harmlos nur, weil `_call_vllm` Overrides still ignoriert (`:1009`); Hochstufung auf "brüchige Koinzidenz" |
| R5 "Proxy nicht Teil des Bugs" | `_route_task :838-899`, Redis `aegis:llm_engine_mode` = `vllm`, `VLLM_MODEL=qwen36-35b` = served-ID | ✅ bestätigt (mit Override-Fußnote) |
| Blast-Radius "Stage-3/Enrichment betroffen" | `AEGIS_USE_LEGACY_CASCADE=1` in Prod-`.env` UND `.env.pre-ablation-20260721_160957`; `extraction_factory.py:180ff` | ❌ Callsites 2273/2413 liegen im deaktivierten Pfad; aktiver Pfad = Rank-1 `:1923` + Relations `:3387` + Gleaning `:2986/:3055/:3890/:3964` |
| AC-5-Rollback funktioniert | Prompt-Prioritätskette `:1475-1570`; `USE_DSPY_PROMPTS` Import-Zeit `extraction_prompts.py:16`; Prompt-Diff GENERIC vs DSPy | ❌ dreifach defekt (G2) |
| AC-1-Anker "Doc 4 = 395 Relations, 60–100 Entities" | `BASELINE_ROUND2_ABLATION` §2 + Nachtrag | ⚠️ Warm-Cache-Zombie-Zahlen; "60–100" unbelegt (G5) |
| "Round 2 funktioniert noch mit Qwen" | Ablation-Nachtrag: Doc 5 on-state `entities_extracted=0` UND 1 Relation | ⚠️ intern inkonsistent — RelationExtractor braucht Entity-Liste; muss Phase 0 erklären (G10, D-10) |
| Log-Beleg "11 LLM-Calls à 6.2 s" | `extraction_pipeline.py:236` Exception-Swallowing; Wall-Skalierung mit Doc-Größe | ✅ Generierung fand statt; 0-Signatur beweist nur "wiederholte per-Chunk-Exception beliebigen Typs" |
| Cold-Run-Evidenz verfügbar | `docker logs aegis-api --since 2026-07-21T22:30` → 0 Treffer; Container Up 10 h | ❌ durch Recreate zerstört → D-9-Runbook-Regel |

**Live-Probe-Rohdaten:** `scratchpad/qwen_probe.py`, `scratchpad/qwen_probe2.py` (Outputs im
Session-Log; als Test-Fixtures nach E-1 zu übernehmen).
