# TD-067: Dataset Annotation Tool for Domain Training

## Status
**Status:** BACKLOG
**Priority:** Low
**Created:** 2025-12-12
**Sprint:** N/A (Future enhancement)

## Context

Sprint 45 introduces domain-specific prompt training using DSPy. This requires annotated training datasets in JSONL format:

```jsonl
{"text": "...", "entities": ["Entity1", "Entity2"], "relations": [{"subject": "Entity1", "predicate": "...", "object": "Entity2"}]}
```

Currently, users must create these datasets manually or use external annotation tools.

## Problem

Creating high-quality annotated datasets for knowledge graph extraction is labor-intensive:
1. **Manual annotation** is slow and error-prone
2. **No in-system tooling** for annotation
3. **External tools** require export/import workflows
4. **Quality control** is difficult without preview/validation

## Proposed Solution

Build an integrated annotation UI within AegisRAG:

### Features
1. **Document Viewer** - Display documents with text highlighting
2. **Entity Annotation** - Click-to-select text spans as entities
3. **Relation Annotation** - Draw connections between entities
4. **Batch Annotation** - Annotate multiple documents efficiently
5. **Export to JSONL** - Format compatible with DSPy training
6. **LLM Pre-Annotation** - Use LLM to suggest annotations, human corrects

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Annotation UI                             │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────────────┐   │
│  │   Document Viewer   │  │     Annotation Panel        │   │
│  │   ─────────────────│  │     ─────────────────────    │   │
│  │   [Lorem ipsum...]  │  │     Entities:               │   │
│  │   with |Entity1|   │  │     ☑ Entity1 (Person)      │   │
│  │   highlighted      │  │     ☑ Entity2 (Org)         │   │
│  │   |Entity2| text   │  │     Relations:               │   │
│  │                     │  │     Entity1 --WORKS_AT-->   │   │
│  │                     │  │                Entity2      │   │
│  └─────────────────────┘  └─────────────────────────────┘   │
│                                                             │
│  [< Prev] [Save & Next >]  [Export JSONL]                  │
└─────────────────────────────────────────────────────────────┘
```

### Technical Components
- `frontend/src/pages/admin/AnnotationPage.tsx`
- `src/api/v1/annotation.py` - Save/load annotations
- `src/components/annotation/exporter.py` - JSONL export

## Effort Estimate
- **Story Points:** 13-21 SP
- **Complexity:** Medium-High (UI-heavy feature)

## Dependencies
- Sprint 45 (Domain Training) must be completed first
- React text selection/highlighting library
- Entity type configuration from domain settings

## Alternatives
1. **Prodigy** - Commercial annotation tool by Explosion AI
2. **Label Studio** - Open-source, self-hosted
3. **Argilla** - Open-source with active learning
4. **Manual JSONL** - Continue with current approach

## Decision
Defer to future sprint. For Sprint 45, users create datasets manually or use external tools.

## References
- Sprint 45: Domain-Specific Prompt Optimization
- [Label Studio](https://labelstud.io/)
- [Argilla](https://argilla.io/)
