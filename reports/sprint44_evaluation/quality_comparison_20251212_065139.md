# Model Quality Comparison Report

**Date:** 2025-12-12
**Reference Model:** qwen3:32b
**Samples:** 3

---

## Aggregated Results (vs Reference)

### Entity Extraction Quality

| Model | Precision | Recall | F1 Score |
|-------|-----------|--------|----------|
| qwen2.5:7b | 61.5% | 43.9% | 50.2% |
| qwen2.5:3b | 56.7% | 29.1% | 35.6% |

### Relation Extraction Quality

| Model | Precision | Recall | F1 Score |
|-------|-----------|--------|----------|
| qwen2.5:7b | 8.5% | 5.3% | 6.3% |
| qwen2.5:3b | 0.0% | 0.0% | 0.0% |

---

## Interpretation Guide

- **Precision**: How many of the model's extractions are also in the reference? (Higher = fewer false positives)
- **Recall**: How many of the reference's extractions does the model find? (Higher = fewer misses)
- **F1 Score**: Harmonic mean of precision and recall (balanced metric)

### Quality Thresholds

| Quality Level | F1 Score |
|---------------|----------|
| Excellent | >= 80% |
| Good | 60-80% |
| Moderate | 40-60% |
| Poor | < 40% |

---

## Per-Sample Details

### sample_0000
**Question:** Were Scott Derrickson and Ed Wood of the same nationality?

**Reference (qwen3:32b):** 31 entities

**qwen2.5:7b:**
- Entities: 21 found, 11 overlap (36% recall)
- Relations: 15 found, 0 overlap (0% recall)
- Unique entities: 300 (film), dawn of the dead (film), deliver us from evil (2014 film), doctor strange (2016 film), ed wood (film)...
- Missed entities: anneliese michel, benedict cumberbatch, conrad brooks, deliver us from evil, doctor strange...

**qwen2.5:3b:**
- Entities: 38 found, 11 overlap (36% recall)
- Relations: 8 found, 0 overlap (0% recall)
- Unique entities: baltimore, maryland, benedict wong, benjamin bratt, bill murray, chiwetel ejiofor...
- Missed entities: anneliese michel, conrad brooks, deliver us from evil, doctor strange, ed wood...

### sample_0001
**Question:** What government position was held by the woman who portrayed Corliss Archer in the film Kiss and Tell?

**Reference (qwen3:32b):** 27 entities

**qwen2.5:7b:**
- Entities: 14 found, 11 overlap (41% recall)
- Relations: 9 found, 1 overlap (4% recall)
- Unique entities: janet waldo, kiss and tell, meet corliss archer (radio series)...
- Missed entities: bangui, cbs, central african republic, flippers new adventure, hampshire...

**qwen2.5:3b:**
- Entities: 8 found, 7 overlap (26% recall)
- Relations: 5 found, 0 overlap (0% recall)
- Unique entities: janet waldo...
- Missed entities: a kiss for corliss, bangui, cbs, central african republic, charles craft...

### sample_0002
**Question:** What science fantasy young adult series, told in first person, has a set of companion books narrating the stories of enslaved worlds and alien species?

**Reference (qwen3:32b):** 27 entities

**qwen2.5:7b:**
- Entities: 28 found, 15 overlap (56% recall)
- Relations: 21 found, 3 overlap (12% recall)
- Unique entities: andre norton award for young adult science fiction and fantasy, back to the divide (2005), indigo magic, jinx on the divide (2006), kyril bonfiglioli...
- Missed entities: andre norton, andre norton award, etiquette & espionage, gail carriger, jerry b. jenkins...

**qwen2.5:3b:**
- Entities: 13 found, 7 overlap (26% recall)
- Relations: 13 found, 0 overlap (0% recall)
- Unique entities: cotton wood press, digicube, egmont usa, kyril bonfiglioli, studio bentstuff...
- Missed entities: andre norton, andre norton award, animorphs, daniel josé older, elizabeth kay...

---

*Generated: 2025-12-12 06:51:39*