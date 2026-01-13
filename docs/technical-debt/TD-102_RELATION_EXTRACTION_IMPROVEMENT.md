# TD-102: Relation Extraction Improvement

**Status:** OPEN
**Priority:** HIGH
**Story Points:** 18 SP (iterativ über Sprint 85-86)
**Created:** 2026-01-11 (Sprint 85 Analysis)
**Target:** Sprint 85-86
**Depends On:** TD-078 (Section Extraction Performance) - FIXED

---

## Problem Statement

Relation Extraction Ratio ist zu niedrig für qualitativ hochwertigen Knowledge Graph.

### Aktuelle Metriken (Sprint 85 Multi-Format Test)

| Format | Entities | Relations | Ratio | Bewertung |
|--------|----------|-----------|-------|-----------|
| CSV | 5 | 2 | 0.40 | 🔴 Schlecht |
| XLSX | 5 | 2 | 0.40 | 🔴 Schlecht |
| PDF | 22 | 6 | **0.27** | 🔴 Sehr schlecht |
| DOCX | 22 | 10 | 0.45 | 🟡 Mäßig |
| PPTX | 23 | 14 | 0.61 | 🟡 Mäßig |

**Ziel:** Relation Ratio ≥ 1.0 (jede Entity hat mindestens 1 Relation)

---

## Root Cause Analysis

| Root Cause | Impact | Iteration |
|------------|--------|-----------|
| Fehlende Entity-Basis (SpaCy nur Fallback) | Entities fehlen → keine Relations möglich | Iteration 1 |
| Schwache Relation-Instruction (nur "RELATES_TO") | LLM extrahiert zu wenig Relations | Iteration 2 |
| Single-Pass Extraction | Latente Relations werden übersehen | Iteration 3 |
| Nicht-domänenspezifische Prompts | Generic Prompts zu schwach | Iteration 4 |
| Fehlende KG-Hygiene | Duplikate, Self-Loops, Fragmentation | Iteration 5 |

---

## Erweiterte Metriken (Verbesserung #1)

**Relation Ratio alleine ist zu grob!** Ergänzende Kontrollmetriken:

| Metrik | Definition | Ziel |
|--------|------------|------|
| **Relation Ratio** | Relations / Entities | ≥ 1.0 |
| **Relation Precision** | Valid Relations / Total Relations | ≥ 0.85 |
| **Relation Recall** | Found Relations / Expected Relations | ≥ 0.70 |
| **Duplication Rate** | Duplicate Triples / Total Triples | ≤ 0.05 |
| **Typed Coverage** | Typed Relations / Total Relations | ≥ 0.60 |

### Minimal-Evaluation (ohne Gold Standard)

```python
# LLM-as-Judge auf 50-100 Samples je Iteration
evaluation_config = {
    "sample_size": 100,
    "stratify_by": ["doc_type", "format"],
    "judge_criteria": [
        "Relation hat Evidenz-Spanne im Text",
        "Entities sind korrekt identifiziert",
        "Relation Type ist semantisch korrekt"
    ]
}
```

---

## Iteration 1: SpaCy-first Cascade + Entity Contract (3 SP)

**Ziel:** Solide Entity-Basis für Relation Extraction

### 1.1 Cascade-Reihenfolge ändern

```python
# VORHER: LLM → LLM → SpaCy (Fallback)
# NACHHER: SpaCy → LLM (Entity-enriched Relation Extraction)

NEW_CASCADE = [
    # Rank 1: SpaCy NER - Deterministic Entity Baseline
    CascadeRankConfig(
        rank=1,
        model="spacy_multi",  # de_core_news_lg + en_core_web_trf
        method=ExtractionMethod.NER_ONLY,
        entity_timeout_s=60,
    ),
    # Rank 2: LLM Relation Extraction + Entity Enrichment
    CascadeRankConfig(
        rank=2,
        model="nemotron-3-nano:latest",
        method=ExtractionMethod.LLM_RELATION_ONLY,  # NEU: Nur Relations!
        relation_timeout_s=300,
    ),
    # Rank 3: Fallback Full LLM
    CascadeRankConfig(
        rank=3,
        model="gpt-oss:20b",
        method=ExtractionMethod.LLM_ONLY,
        entity_timeout_s=300,
        relation_timeout_s=300,
    ),
]
```

### 1.2 Entity Canonicalization Contract (Verbesserung #2)

**Problem:** Entity Fragmentation killt Relation Quality

```python
@dataclass
class EntityCanonical:
    """Canonical Entity Form für stabile Relations."""

    surface: str          # Original: "RTX 3060"
    lemma: str            # Lemma: "rtx 3060"
    normalized: str       # Normalized: "nvidia_rtx_3060"
    entity_type: str      # Type: "HARDWARE"
    aliases: list[str]    # Aliases: ["RTX3060", "GeForce RTX 3060"]
    kb_id: str | None     # Optional: Wikidata ID

# Regeln für Canonicalization:
CANON_RULES = {
    "compound_nouns_de": True,      # "Grafikprozessor" nicht splitten
    "abbreviation_expansion": True,  # "OT" → "OMNITRACKER"
    "number_normalization": True,    # "6 GB" → "6gb"
    "case_folding": "lower",         # Kleinschreibung für Matching
}
```

### 1.3 LLM Entity-Contract

```python
ENTITY_CONTRACT_PROMPT = """
Du erhältst eine Liste von Entities aus SpaCy NER.
Deine Aufgabe:
1. Extrahiere NUR Relationen zwischen diesen bekannten Entities
2. Du darfst KEINE neuen Entities erfinden
3. Optional: Ergänze fehlende Entities (Konzepte, die SpaCy nicht erkennt)

Bekannte Entities:
{spacy_entities}

Text:
{text}
"""
```

**Erwartete Verbesserung:** +30-40% Relation Ratio

---

## Iteration 2: Typed Relations + Candidate Pairing (3 SP)

**Ziel:** Strukturierte Relations statt nur "RELATES_TO"

### 2.1 Relation Type Schema (Verbesserung #3)

```python
# VORHER: Nur RELATES_TO (zu generisch)
# NACHHER: Typed Relations

RELATION_TYPES = {
    # Technische Domain
    "USES": {"domain": ["SOFTWARE", "SYSTEM"], "range": ["LIBRARY", "API"]},
    "RUNS_ON": {"domain": ["SOFTWARE"], "range": ["HARDWARE", "PLATFORM"]},
    "PART_OF": {"domain": ["COMPONENT"], "range": ["SYSTEM"]},
    "HAS_VERSION": {"domain": ["SOFTWARE"], "range": ["VERSION"]},
    "DEPENDS_ON": {"domain": ["SOFTWARE"], "range": ["SOFTWARE", "LIBRARY"]},

    # Organisatorische Domain
    "LOCATED_IN": {"domain": ["ORGANIZATION", "PERSON"], "range": ["LOCATION"]},
    "WORKS_FOR": {"domain": ["PERSON"], "range": ["ORGANIZATION"]},
    "CREATED_BY": {"domain": ["ARTIFACT"], "range": ["PERSON", "ORGANIZATION"]},

    # Fallback
    "RELATES_TO": {"domain": ["*"], "range": ["*"]},  # Nur wenn nichts passt
}
```

### 2.2 Candidate Pairing Strategy

```python
# Nicht alle Entity-Paare prüfen - gezieltes Pairing

PAIRING_STRATEGIES = [
    "same_sentence",       # Entities im selben Satz (höchste Prio)
    "window_2_sentences",  # ±2 Sätze Kontext
    "heading_paragraph",   # Heading-Entity → Paragraph-Entities
    "table_row",          # Entities in derselben Tabellenzeile
]

def generate_candidate_pairs(entities: list, text: str) -> list[tuple]:
    """Generiere nur relevante Entity-Paare für Relation Extraction."""
    pairs = []
    for strategy in PAIRING_STRATEGIES:
        pairs.extend(apply_pairing_strategy(entities, text, strategy))
    return deduplicate(pairs)
```

### 2.3 Verbesserter Relation Prompt

```python
RELATION_EXTRACTION_PROMPT = """
Extrahiere Relationen zwischen den gegebenen Entities.

Verfügbare Relation Types (bevorzugt verwenden):
- USES: Software/System verwendet Library/API
- RUNS_ON: Software läuft auf Hardware/Platform
- PART_OF: Komponente ist Teil von System
- DEPENDS_ON: Software hängt von anderer Software ab
- RELATES_TO: Nur wenn kein spezifischer Type passt

Entity-Paare zu prüfen:
{candidate_pairs}

Text:
{text}

WICHTIG:
- Jede Relation MUSS eine Evidenz-Spanne im Text haben
- Keine Relationen erfinden, die nicht im Text belegt sind
- Negative Beispiele beachten: Entities nebeneinander ≠ automatisch Relation
"""
```

**Erwartete Verbesserung:** +15-25% Relation Ratio, +20% Typed Coverage

---

## Iteration 3: Gleaning / Multi-Pass (3 SP)

**Ziel:** Latente Relations durch zweiten Pass extrahieren

### Reihenfolge geändert (Verbesserung #7)

**Original:** 1 → 2 → DSPy → Gleaning
**Verbessert:** 1 → 2 → **Gleaning** → DSPy

**Begründung:** Gleaning liefert bessere Trainingsdaten für DSPy!

### 3.1 Gleaning Prompt (Microsoft GraphRAG Ansatz)

```python
GLEANING_PROMPT = """
Erste Extraktion hat folgende Relations gefunden:
{existing_relations}

Prüfe den Text erneut auf FEHLENDE Relationen:
- Implizite Relationen (nicht explizit genannt, aber logisch ableitbar)
- Relationen über Satzgrenzen hinweg
- Relationen aus Tabellen/Listen

Text:
{text}

WICHTIG:
- NUR neue Relationen, die noch nicht extrahiert wurden
- Jede Relation MUSS Evidenz-Spanne angeben
- Confidence Score angeben (0.0-1.0)
"""
```

### 3.2 Gleaning Guardrails (Verbesserung #5)

```python
@dataclass
class GleaningConfig:
    """Konfiguration für kontrolliertes Gleaning."""

    max_passes: int = 2
    min_confidence: float = 0.7
    evidence_required: bool = True
    max_evidence_words: int = 25
    allow_new_relations_only: bool = True
    dedupe_on_canonical: bool = True

def validate_gleaning_relation(relation: dict, config: GleaningConfig) -> bool:
    """Validiere Gleaning-Relation gegen Guardrails."""

    # Confidence Check
    if relation.get("confidence", 0) < config.min_confidence:
        return False

    # Evidence Check
    if config.evidence_required:
        evidence = relation.get("evidence_span", "")
        if not evidence or len(evidence.split()) > config.max_evidence_words:
            return False

    # Duplicate Check
    if config.allow_new_relations_only:
        if is_duplicate_relation(relation):
            return False

    return True
```

### 3.3 Relation Confidence Metadata (Strategische Ergänzung)

```python
@dataclass
class RelationMetadata:
    """Metadata für Graph Pruning & Hybrid Retrieval."""

    source_pass: Literal["initial", "gleaning"]
    entity_origin: Literal["spacy", "llm", "hybrid"]
    confidence: float
    evidence_span: str
    evidence_start: int
    evidence_end: int
    extraction_model: str
    extraction_timestamp: datetime
```

**Erwartete Verbesserung:** +20-35% Relation Recall

---

## Iteration 4: DSPy MIPROv2 Optimization (5 SP)

**Ziel:** Universal Extraction Prompts durch Prompt Learning

### 4.1 Multi-Objective Score (Verbesserung #4)

```python
def dspy_objective(predictions, gold) -> float:
    """Multi-Objective Score für DSPy Training."""

    f1 = compute_f1(predictions, gold)
    coverage = compute_coverage(predictions)  # unique typed relations / entities
    dup_rate = compute_duplication_rate(predictions)

    # Gewichteter Score
    score = 0.5 * f1 + 0.3 * coverage - 0.2 * dup_rate

    return score
```

### 4.2 Balanced Training Corpus

```yaml
# Stratifizierter Korpus für DSPy Training
training_corpus:
  doc_types:
    - pdf_text: 20%
    - pdf_ocr: 15%
    - tables: 20%
    - tickets_logs: 15%
    - code_config: 15%
    - slides: 15%

  languages:
    - de: 60%
    - en: 40%

  min_samples_per_type: 50
  total_samples: 500
```

### 4.3 Hard Negatives (Verbesserung #4)

```python
HARD_NEGATIVE_EXAMPLES = [
    {
        "text": "Python und Java sind beliebte Programmiersprachen.",
        "entities": ["Python", "Java"],
        "relations": [],  # KEINE Relation! Nur Aufzählung
        "explanation": "Nebeneinander stehen ≠ Relation"
    },
    {
        "text": "Das Meeting findet am Montag statt. TensorFlow wird besprochen.",
        "entities": ["Meeting", "Montag", "TensorFlow"],
        "relations": [],  # Kein semantischer Zusammenhang
        "explanation": "Verschiedene Sätze ohne logische Verbindung"
    },
]
```

**Erwartete Verbesserung:** +50-100% (aufbauend auf Iteration 1-3)

---

## Iteration 5: Post-Processing & KG Hygiene (2 SP)

**Ziel:** Sauberer Knowledge Graph ohne Artefakte

### 5.1 Validation Rules

```python
KG_HYGIENE_RULES = [
    # Keine Self-Loops
    lambda r: r["source"] != r["target"],

    # Domain/Range Type Check (wenn Schema vorhanden)
    lambda r: check_type_compatibility(r["source_type"], r["relation_type"], r["target_type"]),

    # Symmetrie-Check (RELATES_TO ist symmetrisch)
    lambda r: handle_symmetry(r),

    # Evidence vorhanden
    lambda r: r.get("evidence_span") is not None,
]

def validate_relation(relation: dict) -> tuple[bool, list[str]]:
    """Validiere Relation gegen KG Hygiene Rules."""
    violations = []
    for rule in KG_HYGIENE_RULES:
        if not rule(relation):
            violations.append(rule.__name__)
    return len(violations) == 0, violations
```

### 5.2 Deduplication & Merge

```python
def dedupe_relations(relations: list[dict]) -> list[dict]:
    """Dedupliziere Relations auf Canonical Basis."""

    seen = set()
    unique = []

    for rel in relations:
        # Canonical Key: normalized entities + relation type
        key = (
            normalize_entity(rel["source"]),
            rel["relation_type"],
            normalize_entity(rel["target"]),
        )

        if key not in seen:
            seen.add(key)
            unique.append(rel)
        else:
            # Merge: Behalte höhere Confidence
            existing = find_by_key(unique, key)
            if rel["confidence"] > existing["confidence"]:
                merge_relations(existing, rel)

    return unique
```

**Erwartete Verbesserung:** Ratio stabil, aber Precision +10-15%

---

## Zusammenfassung: Iterationsplan

| Iteration | Focus | SP | Erwartete Verbesserung | Sprint |
|-----------|-------|----|-----------------------|--------|
| **1** | SpaCy-first + Entity Contract | 3 | Ratio +30-40% | 85 |
| **2** | Typed Relations + Candidate Pairing | 3 | Ratio +15-25%, Typed +20% | 85 |
| **3** | Gleaning / Multi-Pass | 3 | Recall +20-35% | 85 |
| **4** | DSPy MIPROv2 Optimization | 5 | Ratio +50-100% (kumulativ) | 86 |
| **5** | KG Hygiene & Post-Processing | 2 | Precision +10-15% | 85 |

**Total:** 16 SP (+2 SP Buffer = 18 SP)

---

## Erwartetes Endergebnis

| Metrik | Baseline | Nach Iteration 5 |
|--------|----------|------------------|
| **Relation Ratio** | 0.27-0.61 | **1.1-1.4** |
| **Precision** | ~0.70 (geschätzt) | ≥0.85 |
| **Recall** | ~0.30 (geschätzt) | ≥0.70 |
| **Duplication Rate** | ~0.15 | ≤0.05 |
| **Typed Coverage** | 0% (nur RELATES_TO) | ≥60% |

---

## Dokumentation

Alle Iterationen werden dokumentiert in:
- `docs/ragas/MULTIFORMAT_INGESTION_TEST.md` - Test Results
- `docs/technical-debt/TD-102_PROGRESS.md` - Iteration Progress (neu)

---

## Akzeptanzkriterien

- [ ] Iteration 1: Relation Ratio ≥ 0.5 auf Multi-Format Test
- [ ] Iteration 2: Typed Coverage ≥ 30%
- [ ] Iteration 3: Recall +20% vs Baseline
- [ ] Iteration 4: Relation Ratio ≥ 1.0 auf Multi-Format Test
- [ ] Iteration 5: Duplication Rate ≤ 5%
- [ ] Alle Ergebnisse in MULTIFORMAT_INGESTION_TEST.md dokumentiert

---

## Related Items

- **TD-078:** Section Extraction Performance (FIXED - O(n²) Bug)
- **TD-101:** Community Summarization Bottleneck (Quick Fix applied)
- **ADR-026:** Pure LLM Extraction Pipeline
- **Sprint 83:** 3-Rank LLM Cascade Implementation

---

**Created by:** Claude Code + User Review
**Analysis Date:** 2026-01-11
**Document Version:** 1.0
