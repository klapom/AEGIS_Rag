# Sprint 45: Manual Test Cases - Semantic Matching

**Feature:** 45.17 Embedding-based Semantic Matching
**Component:** `src/components/domain_training/semantic_matcher.py`
**Date:** 2025-12-15

---

## Overview

Diese Testcases validieren die BGE-M3 Embedding-basierte semantische Ähnlichkeit für DSPy Evaluation Metrics. Statt exaktem String-Matching wird Cosine Similarity verwendet.

### Konfiguration

| Parameter | Wert | Beschreibung |
|-----------|------|--------------|
| Entity Threshold | 0.75 | Minimum Cosine Similarity für Entity Match |
| Relation Threshold | 0.70 | Minimum Cosine Similarity für Relation Match |
| Predicate Weight | 0.4 | Gewichtung des Prädikats in Relation Matching |
| Subject/Object Weight | 0.3 | Gewichtung von Subject/Object (je 0.3) |

---

## Test Suite 1: Entity Matching (Threshold >= 0.75)

### TC-45.17.E1: Exaktes Matching
**Ziel:** Exakt gleiche Entities müssen matchen (Similarity = 1.0)

| Gold Entity | Predicted Entity | Expected Match | Expected Similarity |
|-------------|------------------|----------------|---------------------|
| `OMNITRACKER` | `OMNITRACKER` | ✅ Yes | 1.0 |
| `Rechtesystem` | `Rechtesystem` | ✅ Yes | 1.0 |
| `Benutzer` | `Benutzer` | ✅ Yes | 1.0 |

**Test-Kommando:**
```bash
poetry run python -c "
from src.components.domain_training.semantic_matcher import get_semantic_matcher
m = get_semantic_matcher(threshold=0.75)
assert m.entities_match('OMNITRACKER', 'OMNITRACKER')
assert m.entities_match('Rechtesystem', 'Rechtesystem')
print('✅ TC-45.17.E1: Exaktes Matching PASSED')
"
```

---

### TC-45.17.E2: Case-Insensitive Matching
**Ziel:** Groß-/Kleinschreibung soll ignoriert werden

| Gold Entity | Predicted Entity | Expected Match |
|-------------|------------------|----------------|
| `OMNITRACKER` | `omnitracker` | ✅ Yes |
| `Omnitracker` | `OMNITRACKER` | ✅ Yes |
| `rechtesystem` | `Rechtesystem` | ✅ Yes |

**Test-Kommando:**
```bash
poetry run python -c "
from src.components.domain_training.semantic_matcher import get_semantic_matcher
m = get_semantic_matcher(threshold=0.75)
assert m.entities_match('OMNITRACKER', 'omnitracker')
assert m.entities_match('Omnitracker', 'OMNITRACKER')
assert m.entities_match('rechtesystem', 'Rechtesystem')
print('✅ TC-45.17.E2: Case-Insensitive Matching PASSED')
"
```

---

### TC-45.17.E3: Semantisch ähnliche Entities (Deutsche Synonyme)
**Ziel:** Semantisch ähnliche Begriffe sollen matchen

| Gold Entity | Predicted Entity | Expected Match | Rationale |
|-------------|------------------|----------------|-----------|
| `Benutzer` | `User` | ✅ Yes | Synonym |
| `Rechtesystem` | `Rechte-System` | ✅ Yes | Bindestrich-Variante |
| `Rechteverwaltung` | `Zugriffsrechte` | ✅ Yes | Verwandter Begriff |
| `Administrator` | `Admin` | ✅ Yes | Abkürzung |
| `Datenbank` | `Database` | ✅ Yes | Übersetzung |

**Test-Kommando:**
```bash
poetry run python -c "
from src.components.domain_training.semantic_matcher import get_semantic_matcher
m = get_semantic_matcher(threshold=0.75)

# Synonyme
tests = [
    ('Benutzer', 'User'),
    ('Rechtesystem', 'Rechte-System'),
    ('Administrator', 'Admin'),
    ('Datenbank', 'Database'),
]
for gold, pred in tests:
    sim = m.compute_similarity(gold, pred)
    match = m.entities_match(gold, pred)
    print(f'{gold} vs {pred}: sim={sim:.3f}, match={match}')

print('✅ TC-45.17.E3: Semantisch ähnliche Entities')
"
```

---

### TC-45.17.E4: Nicht-ähnliche Entities (sollten NICHT matchen)
**Ziel:** Semantisch unterschiedliche Begriffe sollen NICHT matchen

| Gold Entity | Predicted Entity | Expected Match | Rationale |
|-------------|------------------|----------------|-----------|
| `OMNITRACKER` | `Microsoft` | ❌ No | Völlig unterschiedlich |
| `Benutzer` | `Server` | ❌ No | Unterschiedliche Konzepte |
| `Datenbank` | `Netzwerk` | ❌ No | Unterschiedliche Domänen |
| `Administrator` | `Drucker` | ❌ No | Keine Beziehung |

**Test-Kommando:**
```bash
poetry run python -c "
from src.components.domain_training.semantic_matcher import get_semantic_matcher
m = get_semantic_matcher(threshold=0.75)

# Nicht-ähnliche Entities
tests = [
    ('OMNITRACKER', 'Microsoft'),
    ('Benutzer', 'Server'),
    ('Datenbank', 'Netzwerk'),
    ('Administrator', 'Drucker'),
]
for gold, pred in tests:
    sim = m.compute_similarity(gold, pred)
    match = m.entities_match(gold, pred)
    print(f'{gold} vs {pred}: sim={sim:.3f}, match={match}')
    assert not match, f'Should NOT match: {gold} vs {pred}'

print('✅ TC-45.17.E4: Nicht-ähnliche Entities PASSED')
"
```

---

### TC-45.17.E5: Entity Metrics (Precision/Recall/F1)
**Ziel:** Korrekte Berechnung von P/R/F1 mit semantischem Matching

**Testfall:**
```
Gold Entities: {OMNITRACKER, Rechtesystem, Benutzer}
Predicted:     {OMNITRACKER, Rechte-System, User, ExtraEntity}

Expected:
- True Positives: 3 (OMNITRACKER=exact, Rechtesystem~Rechte-System, Benutzer~User)
- False Positives: 1 (ExtraEntity)
- False Negatives: 0

Precision = 3/4 = 0.75
Recall    = 3/3 = 1.0
F1        = 2 * (0.75 * 1.0) / (0.75 + 1.0) = 0.857
```

**Test-Kommando:**
```bash
poetry run python -c "
from src.components.domain_training.semantic_matcher import get_semantic_matcher
m = get_semantic_matcher(threshold=0.75)

gold = {'OMNITRACKER', 'Rechtesystem', 'Benutzer'}
pred = {'OMNITRACKER', 'Rechte-System', 'User', 'ExtraEntity'}

metrics = m.compute_entity_metrics(gold, pred)
print(f'Precision: {metrics[\"precision\"]:.3f}')
print(f'Recall:    {metrics[\"recall\"]:.3f}')
print(f'F1:        {metrics[\"f1\"]:.3f}')

# Erwartete Werte (mit Toleranz)
assert metrics['recall'] >= 0.95, f'Recall should be ~1.0, got {metrics[\"recall\"]}'
assert metrics['precision'] >= 0.7, f'Precision should be ~0.75, got {metrics[\"precision\"]}'
print('✅ TC-45.17.E5: Entity Metrics PASSED')
"
```

---

## Test Suite 2: Relation Matching (Gewichtete Similarity)

### Gewichtungsformel

```
relation_similarity = (
    subject_sim * 0.3 +
    predicate_sim * 0.4 +
    object_sim * 0.3
)

Match wenn: relation_similarity >= 0.70
```

---

### TC-45.17.R1: Exaktes Relation Matching
**Ziel:** Exakt gleiche Relationen müssen matchen

| Gold Relation | Predicted Relation | Expected Match |
|---------------|-------------------|----------------|
| (OMNITRACKER, verfügt über, Rechtesystem) | (OMNITRACKER, verfügt über, Rechtesystem) | ✅ Yes |

**Test-Kommando:**
```bash
poetry run python -c "
from src.components.domain_training.semantic_matcher import get_semantic_matcher
m = get_semantic_matcher(threshold=0.70, predicate_weight=0.4)

gold = [{'subject': 'OMNITRACKER', 'predicate': 'verfügt über', 'object': 'Rechtesystem'}]
pred = [{'subject': 'OMNITRACKER', 'predicate': 'verfügt über', 'object': 'Rechtesystem'}]

metrics = m.compute_relation_metrics(gold, pred)
print(f'Precision: {metrics[\"precision\"]:.3f}')
print(f'Recall:    {metrics[\"recall\"]:.3f}')
print(f'F1:        {metrics[\"f1\"]:.3f}')
assert metrics['f1'] == 1.0
print('✅ TC-45.17.R1: Exaktes Relation Matching PASSED')
"
```

---

### TC-45.17.R2: Semantisch ähnliche Prädikate (Deutsch)
**Ziel:** Semantisch ähnliche Verben sollen matchen

| Gold Predicate | Predicted Predicate | Expected Match | Rationale |
|----------------|---------------------|----------------|-----------|
| `verfügt über` | `hat` | ✅ Yes | Synonym |
| `enthält` | `beinhaltet` | ✅ Yes | Synonym |
| `gehört zu` | `ist Teil von` | ✅ Yes | Verwandt |
| `verwendet` | `nutzt` | ✅ Yes | Synonym |
| `ist` | `entspricht` | ✅ Yes | Verwandt |

**Test-Kommando:**
```bash
poetry run python -c "
from src.components.domain_training.semantic_matcher import get_semantic_matcher
m = get_semantic_matcher(threshold=0.70, predicate_weight=0.4)

# Test: 'verfügt über' vs 'hat'
gold = [{'subject': 'OMNITRACKER', 'predicate': 'verfügt über', 'object': 'Rechtesystem'}]
pred = [{'subject': 'OMNITRACKER', 'predicate': 'hat', 'object': 'Rechtesystem'}]

metrics = m.compute_relation_metrics(gold, pred)
print(f'\"verfügt über\" vs \"hat\": F1={metrics[\"f1\"]:.3f}')

# Test: 'enthält' vs 'beinhaltet'
gold2 = [{'subject': 'System', 'predicate': 'enthält', 'object': 'Module'}]
pred2 = [{'subject': 'System', 'predicate': 'beinhaltet', 'object': 'Module'}]

metrics2 = m.compute_relation_metrics(gold2, pred2)
print(f'\"enthält\" vs \"beinhaltet\": F1={metrics2[\"f1\"]:.3f}')

print('✅ TC-45.17.R2: Semantisch ähnliche Prädikate')
"
```

---

### TC-45.17.R3: Gewichtete Relation Similarity
**Ziel:** Gewichtung (0.3/0.4/0.3) korrekt anwenden

**Testfall:**
```
Gold:      (OMNITRACKER, verfügt über, Rechtesystem)
Predicted: (OMNITRACKER, hat,          Rechte-System)

Subject:   OMNITRACKER = OMNITRACKER     → sim = 1.0
Predicate: verfügt über ≈ hat            → sim ≈ 0.7-0.9
Object:    Rechtesystem ≈ Rechte-System  → sim ≈ 0.9-1.0

Weighted: 1.0*0.3 + 0.8*0.4 + 0.95*0.3 = 0.3 + 0.32 + 0.285 = 0.905
```

**Test-Kommando:**
```bash
poetry run python -c "
from src.components.domain_training.semantic_matcher import get_semantic_matcher
m = get_semantic_matcher(threshold=0.70, predicate_weight=0.4)

gold = [{'subject': 'OMNITRACKER', 'predicate': 'verfügt über', 'object': 'Rechtesystem'}]
pred = [{'subject': 'OMNITRACKER', 'predicate': 'hat', 'object': 'Rechte-System'}]

metrics = m.compute_relation_metrics(gold, pred)
print(f'Precision: {metrics[\"precision\"]:.3f}')
print(f'Recall:    {metrics[\"recall\"]:.3f}')
print(f'F1:        {metrics[\"f1\"]:.3f}')

# Sollte matchen (F1 > 0)
assert metrics['f1'] > 0.5, f'Should match with F1 > 0.5, got {metrics[\"f1\"]}'
print('✅ TC-45.17.R3: Gewichtete Relation Similarity PASSED')
"
```

---

### TC-45.17.R4: Nicht-matchende Relationen
**Ziel:** Semantisch unterschiedliche Relationen sollen NICHT matchen

| Gold | Predicted | Expected Match |
|------|-----------|----------------|
| (OMNITRACKER, verfügt über, Rechtesystem) | (Microsoft, kauft, Apple) | ❌ No |
| (Benutzer, hat, Rolle) | (Server, läuft auf, Linux) | ❌ No |

**Test-Kommando:**
```bash
poetry run python -c "
from src.components.domain_training.semantic_matcher import get_semantic_matcher
m = get_semantic_matcher(threshold=0.70, predicate_weight=0.4)

gold = [{'subject': 'OMNITRACKER', 'predicate': 'verfügt über', 'object': 'Rechtesystem'}]
pred = [{'subject': 'Microsoft', 'predicate': 'kauft', 'object': 'Apple'}]

metrics = m.compute_relation_metrics(gold, pred)
print(f'Different relations: F1={metrics[\"f1\"]:.3f}')
assert metrics['f1'] < 0.5, 'Should NOT match'
print('✅ TC-45.17.R4: Nicht-matchende Relationen PASSED')
"
```

---

### TC-45.17.R5: Relation Metrics mit mehreren Relationen
**Ziel:** Korrekte P/R/F1 bei mehreren Relationen

**Testfall:**
```
Gold Relations:
1. (OMNITRACKER, verfügt über, Rechtesystem)
2. (Benutzer, hat, Rolle)
3. (System, enthält, Module)

Predicted Relations:
1. (OMNITRACKER, hat, Rechte-System)           → Match mit Gold #1
2. (User, besitzt, Rolle)                      → Match mit Gold #2
3. (System, beinhaltet, Module)                → Match mit Gold #3
4. (Extra, unbekannt, Entity)                  → No Match (FP)

Expected:
- TP: 3
- FP: 1
- FN: 0
- Precision: 3/4 = 0.75
- Recall: 3/3 = 1.0
```

**Test-Kommando:**
```bash
poetry run python -c "
from src.components.domain_training.semantic_matcher import get_semantic_matcher
m = get_semantic_matcher(threshold=0.70, predicate_weight=0.4)

gold = [
    {'subject': 'OMNITRACKER', 'predicate': 'verfügt über', 'object': 'Rechtesystem'},
    {'subject': 'Benutzer', 'predicate': 'hat', 'object': 'Rolle'},
    {'subject': 'System', 'predicate': 'enthält', 'object': 'Module'},
]
pred = [
    {'subject': 'OMNITRACKER', 'predicate': 'hat', 'object': 'Rechte-System'},
    {'subject': 'User', 'predicate': 'besitzt', 'object': 'Rolle'},
    {'subject': 'System', 'predicate': 'beinhaltet', 'object': 'Module'},
    {'subject': 'Extra', 'predicate': 'unbekannt', 'object': 'Entity'},
]

metrics = m.compute_relation_metrics(gold, pred)
print(f'Precision: {metrics[\"precision\"]:.3f}')
print(f'Recall:    {metrics[\"recall\"]:.3f}')
print(f'F1:        {metrics[\"f1\"]:.3f}')

print('✅ TC-45.17.R5: Relation Metrics mit mehreren Relationen')
"
```

---

## Test Suite 3: Edge Cases

### TC-45.17.EC1: Leere Listen
**Ziel:** Graceful Handling von leeren Gold/Predicted Listen

**Test-Kommando:**
```bash
poetry run python -c "
from src.components.domain_training.semantic_matcher import get_semantic_matcher
m = get_semantic_matcher(threshold=0.75)

# Beide leer
metrics = m.compute_entity_metrics(set(), set())
assert metrics['f1'] == 1.0, 'Empty sets should have F1=1.0'

# Gold leer, Predicted nicht leer
metrics = m.compute_entity_metrics(set(), {'A', 'B'})
assert metrics['precision'] == 0.0
assert metrics['recall'] == 1.0  # Nothing to recall

# Predicted leer, Gold nicht leer
metrics = m.compute_entity_metrics({'A', 'B'}, set())
assert metrics['precision'] == 1.0  # Nothing predicted wrong
assert metrics['recall'] == 0.0

print('✅ TC-45.17.EC1: Leere Listen PASSED')
"
```

---

### TC-45.17.EC2: Sonderzeichen und Umlaute
**Ziel:** Korrekte Verarbeitung von deutschen Umlauten

| Gold Entity | Predicted Entity | Expected Match |
|-------------|------------------|----------------|
| `Größe` | `Groesse` | ✅ Yes |
| `Übersicht` | `Uebersicht` | ✅ Yes |
| `Gemäß` | `Gemaess` | ✅ Yes |

**Test-Kommando:**
```bash
poetry run python -c "
from src.components.domain_training.semantic_matcher import get_semantic_matcher
m = get_semantic_matcher(threshold=0.75)

tests = [
    ('Größe', 'Groesse'),
    ('Übersicht', 'Uebersicht'),
]
for gold, pred in tests:
    sim = m.compute_similarity(gold, pred)
    print(f'{gold} vs {pred}: sim={sim:.3f}')

print('✅ TC-45.17.EC2: Sonderzeichen und Umlaute')
"
```

---

## Test Suite 4: Integration mit DSPy Training

### TC-45.17.INT1: Entity Extraction Metric in DSPy
**Ziel:** SemanticMatcher wird korrekt in entity_extraction_metric verwendet

**Vorbereitung:**
1. Domain mit Trainingsdaten erstellen
2. DSPy Training starten
3. Metrics im Training Log prüfen

**Erwartetes Verhalten:**
- F1 > 0 auch bei nicht-exakten Matches
- Semantisch ähnliche Entities werden als TP gezählt

---

### TC-45.17.INT2: Relation Extraction Metric in DSPy
**Ziel:** SemanticMatcher wird korrekt in relation_extraction_metric verwendet

**Erwartetes Verhalten:**
- Relationen mit ähnlichen Prädikaten werden gematch
- Gewichtung (0.4 Predicate, 0.3 Subject/Object) wird angewendet

---

## Vollständiger Test-Runner

**Alle Tests ausführen:**

```bash
poetry run python -c "
print('=' * 60)
print('Sprint 45.17 Manual Tests - Semantic Matching')
print('=' * 60)

from src.components.domain_training.semantic_matcher import get_semantic_matcher

# Entity Matcher
em = get_semantic_matcher(threshold=0.75)

# Relation Matcher
rm = get_semantic_matcher(threshold=0.70, predicate_weight=0.4)

print()
print('--- TC-45.17.E1: Exaktes Entity Matching ---')
assert em.entities_match('OMNITRACKER', 'OMNITRACKER')
print('✅ PASSED')

print()
print('--- TC-45.17.E2: Case-Insensitive ---')
assert em.entities_match('OMNITRACKER', 'omnitracker')
print('✅ PASSED')

print()
print('--- TC-45.17.E3: Semantisch ähnliche Entities ---')
for gold, pred in [('Benutzer', 'User'), ('Administrator', 'Admin')]:
    sim = em.compute_similarity(gold, pred)
    print(f'  {gold} vs {pred}: {sim:.3f}')
print('✅ Similarity computed')

print()
print('--- TC-45.17.E5: Entity Metrics ---')
gold_e = {'OMNITRACKER', 'Rechtesystem', 'Benutzer'}
pred_e = {'OMNITRACKER', 'Rechte-System', 'User', 'ExtraEntity'}
metrics = em.compute_entity_metrics(gold_e, pred_e)
print(f'  P={metrics[\"precision\"]:.2f} R={metrics[\"recall\"]:.2f} F1={metrics[\"f1\"]:.2f}')
print('✅ PASSED')

print()
print('--- TC-45.17.R3: Gewichtete Relation Similarity ---')
gold_r = [{'subject': 'OMNITRACKER', 'predicate': 'verfügt über', 'object': 'Rechtesystem'}]
pred_r = [{'subject': 'OMNITRACKER', 'predicate': 'hat', 'object': 'Rechte-System'}]
metrics = rm.compute_relation_metrics(gold_r, pred_r)
print(f'  P={metrics[\"precision\"]:.2f} R={metrics[\"recall\"]:.2f} F1={metrics[\"f1\"]:.2f}')
assert metrics['f1'] > 0.5
print('✅ PASSED')

print()
print('--- TC-45.17.EC1: Leere Listen ---')
metrics = em.compute_entity_metrics(set(), set())
assert metrics['f1'] == 1.0
print('✅ PASSED')

print()
print('=' * 60)
print('ALL TESTS PASSED')
print('=' * 60)
"
```

---

## Ergebnisprotokoll

| Test Case | Status | Datum | Tester | Bemerkungen |
|-----------|--------|-------|--------|-------------|
| TC-45.17.E1 | ⬜ | | | |
| TC-45.17.E2 | ⬜ | | | |
| TC-45.17.E3 | ⬜ | | | |
| TC-45.17.E4 | ⬜ | | | |
| TC-45.17.E5 | ⬜ | | | |
| TC-45.17.R1 | ⬜ | | | |
| TC-45.17.R2 | ⬜ | | | |
| TC-45.17.R3 | ⬜ | | | |
| TC-45.17.R4 | ⬜ | | | |
| TC-45.17.R5 | ⬜ | | | |
| TC-45.17.EC1 | ⬜ | | | |
| TC-45.17.EC2 | ⬜ | | | |
| TC-45.17.INT1 | ⬜ | | | |
| TC-45.17.INT2 | ⬜ | | | |
