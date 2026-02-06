# ADR-060: Standards-Based Domain Taxonomy Architecture

## Status
**Accepted** (2026-02-06)

## Context

AegisRAG's entity/relation extraction pipeline operates without domain awareness. Three domain classifiers exist (C-LARA SetFit, BGE-M3 DomainClassifier, LangGraph agent) but none is wired into the ingestion pipeline (Sprint 125.7). When domain-aware extraction is activated, we need a principled taxonomy of knowledge domains — not an ad-hoc list.

### Key Questions
1. How many domains? What should they be?
2. What standards should define the taxonomy?
3. How many entity/relation types per domain?
4. How does this interact with Neo4j labels, Prometheus metrics, and UI?
5. How many domains will a typical deployment actually use?

### Research Findings

**Industry standards (NAICS, ISIC, NACE, GICS)** classify economic activities, not knowledge domains. They miss academic/theoretical fields (philosophy, mathematics, arts, linguistics).

**Knowledge standards (DDC, FORD, LoC, CIP)** classify knowledge areas and map well to document domains:
- **DDC (Dewey Decimal):** 10 main classes → 100 divisions. 138+ countries, since 1876.
- **FORD (OECD):** 6 fields → 42 subfields. International R&D standard.
- **LoC:** 21 classes, freely available but US-centric.
- **CIP:** 47 series, education-focused.

**Empirical BGE-M3 validation** on the DGX Spark (production environment):
- 25 domains with description sentences: 3 danger pairs, 56 warning pairs (too similar)
- 25 domains with keywords: 0 danger pairs, 1 warning pair (-24% mean similarity)
- 35 domains with keywords: 0 danger pairs, 0 warning pairs (max similarity 0.699)

**Domain-specific ontologies** exist for ALL 35 proposed domains:
- 32/35 have free, formal ontologies (SNOMED-CT, FIBO, ACM CCS, GEMET, etc.)
- 3/35 have commercial/academic-only sources (ISA-95, SIL Ethnologue, GeoRef)

**Deployment reality:** Most companies use 1-5 domains, even large conglomerates max ~7-8.

## Decision

### 1. DDC + FORD Hybrid Taxonomy (35 Domains)

Use Dewey Decimal Classification (DDC) for universal coverage + OECD Fields of Research & Development (FORD) for research granularity. Each domain has DDC code + FORD code for traceability.

**35 domains across 5 sectors:**
- Natural Sciences (7): CS/IT, Math, Physics, Chemistry, Biology, Earth Sci, Astronomy
- Engineering & Technology (8): Engineering, Medicine, Agriculture, Materials, Manufacturing, Energy, Architecture, Telecom, Transport/Logistics
- Social Sciences (7): Psychology, Economics, Law, Political Science, Education, Sociology, Media
- Humanities (7): Philosophy, History, Linguistics, Literature, Visual Arts, Music, Religion
- Applied/Interdisciplinary (6): Defense, Sports, Hospitality, Real Estate, Environmental Policy

### 2. Two-Tier Entity/Relation Type System

**Tier 1 — Universal (15 entity types, 21 relation types):**
- Used in Neo4j labels, Prometheus counters, UI colors/icons, KG Hygiene validation
- Consistent across all domains: PERSON, ORGANIZATION, LOCATION, CONCEPT, TECHNOLOGY, PRODUCT, etc.

**Tier 2 — Domain-specific (8-12 entity sub-types, 6-10 relation hints per domain):**
- Stored as Neo4j property (`e.sub_type`), NOT as label
- Only in extraction prompts (LLM hints) and Neo4j properties
- Mapped to universal Tier 1 types (e.g., DISEASE → CONCEPT, MEDICATION → PRODUCT)
- Derived from established ontologies (SNOMED-CT, FIBO, ACM CCS, etc.)

### 3. Deployment Profiles

Companies select a profile at setup (e.g., "Pharma" → activates Medicine, Chemistry, Biology, Regulation). Only selected domains are seeded in Neo4j, loaded in classifier, shown in UI.

Pre-defined profiles: pharma, law_firm, engineering, software, financial, healthcare, energy, media, university (all 35), consulting, custom.

### 4. Seed Domain Catalog (`data/seed_domains.yaml`)

Machine-readable catalog with per-domain:
- DDC/FORD codes (traceability to standards)
- Keywords (for BGE-M3 zero-shot classification)
- Ontology references (name, URL, license)
- Entity sub-types with mapping to universal types
- Relation hints for extraction prompts

## Alternatives Considered

### A. Single Standard (DDC only)
**Rejected.** DDC's 10 top-level classes are too coarse, 100 divisions too fine. FORD adds the right middle-ground granularity for research/academic content.

### B. Industry Standards (NAICS/GICS)
**Rejected.** Missing non-business domains (philosophy, arts, history, linguistics). Only suitable for business document classification.

### C. No Domain Taxonomy (Generic Extraction)
**Rejected.** Sprint 124 showed 100% RELATES_TO relations with generic prompts. Domain-specific extraction is critical for knowledge graph quality.

### D. Flat Entity Type List (50+ types globally)
**Rejected.** Prometheus cardinality explosion (50 types × 3 models = 150+ time series), Neo4j index overhead (50+ labels), UI unmanageable (50+ colors). Two-tier system keeps Tier 1 at 15 types.

### E. 100+ Domains (Fine-Grained)
**Rejected.** BGE-M3 embedding similarity degrades beyond ~40 domains. Most companies need 1-5. 35 domains is the sweet spot between coverage and separability.

## Consequences

### Positive
- **Standards-based:** Every domain traceable to DDC/FORD, no ad-hoc naming
- **Ontology-backed:** Entity/relation types derived from established vocabularies (SNOMED-CT, FIBO, etc.)
- **Prometheus-safe:** Only 15 universal entity types in counters (not 260+)
- **Neo4j-efficient:** Only 15 Neo4j labels (not 260+), sub-types in properties
- **UI-manageable:** 15 colors/icons for entity types
- **LLM-focused:** Extraction prompt sees ~25 entity types + ~28 relation types per chunk (not all 260)
- **Deployment-flexible:** 1-35 domains active per installation

### Negative
- **Sub-type mapping:** Added complexity of mapping DISEASE → CONCEPT, etc.
- **35 domains maintenance:** Seed catalog needs updates as ontologies evolve
- **Profile selection:** Requires setup step (which profile?)

### Metrics Impact
- **LLM prompt overhead:** ~150-200 tokens for domain-specific types (~10% of budget)
- **BGE-M3 classification:** <50ms per document (zero-shot, cached embeddings)
- **Neo4j storage:** +1 property per entity (`sub_type`), negligible

## Related Decisions
- ADR-026: Pure LLM Extraction Pipeline (domain prompts extend this)
- ADR-039: Section-Aware Chunking (chunks classified per domain)
- ADR-040: RELATES_TO Semantic Relationships (relation_type property)
- ADR-059: vLLM Integration (extraction engine for domain-specific prompts)
- Sprint 125.7: Domain-Aware Extraction Pipeline (wiring)
- Sprint 125.8: Domain Taxonomy & Seed Catalog (this ADR)
