# ADR-030: Sprint Extension from 12 to 21+ Sprints

**Status:** ✅ Accepted
**Date:** 2025-11-07
**Sprint:** 21
**Related:** All ADRs (comprehensive project scope evolution)

---

## Context

### Original Plan (Project Inception - Januar 2025)

The AegisRAG project was initially scoped as a **12-sprint project** over 12 weeks:

**Original Roadmap:**
```yaml
Phase 1: Foundation (Sprint 1-3)
  Sprint 1: Infrastructure Setup
    - Docker Compose orchestration
    - Pydantic Settings configuration
    - Structured logging (structlog)

  Sprint 2: Vector Search Foundation
    - Qdrant client with connection pooling
    - BM25 search engine
    - Hybrid search with RRF
    - 212 tests implemented

  Sprint 3: Advanced Retrieval
    - Adaptive chunking (code: 256 tokens, prose: 512, tables: 768)
    - Query expansion
    - Reranking pipeline

Phase 2: Multi-Agent Orchestration (Sprint 4-6)
  Sprint 4: LangGraph Orchestration
    - State machine implementation
    - Multi-agent routing
    - Parallel execution via Send API

  Sprint 5: Graph RAG Integration
    - LightRAG + Neo4j integration
    - Entity/relation extraction
    - Community detection

  Sprint 6: Hybrid Retrieval
    - Vector + Graph fusion
    - Analytics engine
    - Temporal queries

Phase 3: Memory & Tools (Sprint 7-9)
  Sprint 7: 3-Layer Memory Architecture
    - Redis (short-term)
    - Qdrant (semantic long-term)
    - Graphiti (episodic temporal)

  Sprint 8: Memory Consolidation
    - Cross-layer synchronization
    - Memory router
    - Decay strategies

  Sprint 9: MCP Integration
    - Model Context Protocol client
    - Tool integration (Filesystem, GitHub, Web)

Phase 4: Production Readiness (Sprint 10-12)
  Sprint 10: Gradio MVP UI
    - Basic chat interface
    - Health dashboard

  Sprint 11: Performance Optimization
    - GPU optimization
    - Batch processing
    - Caching strategies

  Sprint 12: Production Deployment
    - Kubernetes manifests
    - CI/CD pipelines
    - Monitoring setup
```

**Expected Completion:** March 2025 (12 weeks from January 2025)

### Actual Timeline

**Reality (Januar 2025 - November 2025):**
```yaml
Sprints Completed: 21+ (as of 2025-11-07)
Duration: 10 months (vs. 3 months planned)
Sprint Extension: +9 sprints (+75% over original estimate)
Expected Completion: Ongoing (Sprint 22+ planned)

Breakdown:
  - Original Sprints 1-12: ✅ COMPLETED (with modifications)
  - Extension Sprints 13-21: ✅ COMPLETED (new scope)
  - Future Sprints 22+: ⏳ PLANNED (ongoing improvements)
```

**Extended Sprints (13-21):**
```
Sprint 13: Three-Phase Entity Extraction Pipeline
  - SpaCy NER + Semantic Dedup + Gemma 3 4B
  - Performance: 300s → 15-17s (18-20x speedup)
  - ADR-017, ADR-018

Sprint 14: Backend Performance & Testing
  - Extraction Pipeline Factory
  - Prometheus metrics (12 metrics)
  - 132 tests (112 unit, 20 integration)
  - ADR-019

Sprint 15: React Frontend (PLANNED, deferred to Sprint 22+)
  - Perplexity-inspired UI design
  - SSE streaming
  - ADR-020, ADR-021 (design complete, implementation deferred per ADR-029)

Sprint 16: Unified Architecture & BGE-M3 Migration
  - BGE-M3 embedding model (768D → 1024D)
  - Unified chunking service
  - Reindexing pipeline
  - ADR-022, ADR-023, ADR-024

Sprint 17: Admin UI & Advanced Features
  - Enhanced Gradio UI (5.49.0)
  - Admin dashboard
  - Advanced query modes

Sprint 18: Test Infrastructure & Security Hardening
  - CI/CD pipeline (5 gates)
  - Frontend test modernization
  - Security audits

Sprint 19: Model Configuration Update
  - Ollama model optimization
  - Mirostat v2 tuning
  - Performance benchmarking

Sprint 20: Performance Optimization & Extraction Quality
  - Chunk overhead analysis (65% overhead identified)
  - LLM extraction quality improvements
  - Pure LLM pipeline introduced

Sprint 21: Container-Based Ingestion Pipeline
  - Docling CUDA container migration
  - LlamaIndex deprecation
  - VLM enrichment (Feature 21.6)
  - ADR-027, ADR-028
```

### Reasons for Extension

**1. Underestimated Complexity:**

Original 12-sprint plan assumed straightforward integration of existing tools. Reality revealed significant challenges:

```
Planned (Sprint 5): "Integrate LightRAG with Neo4j"
  Estimate: 5 days
  Actual Reality (Sprint 5 + Sprint 13):
    - Sprint 5: Basic integration (3 days)
    - Sprint 13: Performance unacceptable (300s/doc)
    - Sprint 13: Three-phase pipeline refactor (7 days)
    - TOTAL: 10 days (2x original estimate)

Planned (Sprint 2): "Implement hybrid search"
  Estimate: 3 days
  Actual Reality (Sprint 2 + Sprint 3 + Sprint 16):
    - Sprint 2: Basic RRF (2 days)
    - Sprint 3: Adaptive chunking (3 days)
    - Sprint 16: Unified chunking refactor (4 days)
    - TOTAL: 9 days (3x original estimate)
```

**2. Quality Requirements Higher Than Expected:**

Initial MVP approach insufficient for production use case (OMNITRACKER technical documentation):

```
Original Quality Assumptions:
  - OCR Accuracy: "Good enough" with Tesseract → REALITY: 70% insufficient
  - Entity Extraction: "Use LightRAG default" → REALITY: 30% success rate, unacceptable
  - Chunk Size: "Standard 512 tokens" → REALITY: 600→1800 tokens needed
  - Embeddings: "768-dim sufficient" → REALITY: 1024-dim required for German

Quality Improvements Required (Sprint 13-21):
  - Sprint 13: Three-phase extraction (quality: 30% → 95%)
  - Sprint 16: BGE-M3 migration (German retrieval: +23%)
  - Sprint 20: Pure LLM extraction (domain specificity: +40%)
  - Sprint 21: Docling OCR (accuracy: 70% → 95%)
```

**3. Technology Evolution:**

Tools and frameworks evolved during development, requiring adaptation:

```
LangGraph Evolution:
  - Planned (Sprint 1): LangGraph 0.2.x
  - Sprint 4: LangGraph 0.3.x (breaking changes)
  - Sprint 10: LangGraph 0.4.x (new Send API)
  - Sprint 16: LangGraph 0.5.x (state schema changes)
  - Sprint 21: LangGraph 0.6.10 (current)

  Impact: 4 migration cycles (2 days each = 8 days unplanned effort)

Ollama Model Evolution:
  - Sprint 1: llama2:7b → llama3.2:3b/8b (Sprint 10)
  - Sprint 13: qwen3:0.6b → gemma-3-4b (Sprint 13)
  - Sprint 16: nomic-embed-text → bge-m3 (Sprint 16)
  - Sprint 19: Mirostat v2 optimization

  Impact: Model testing, benchmarking, retraining (10 days total)
```

**4. GPU Memory Constraints:**

RTX 3060 6GB VRAM imposed strict memory management requirements:

```
Naive Plan (Sprint 1-10):
  - Load all models simultaneously
  - Shared memory pool
  - "GPU should handle it"

Reality (Sprint 11-21):
  - Sprint 11: GPU OOM crashes with qwen2.5:14b
  - Sprint 19: Model swapping required (OLLAMA_MAX_LOADED_MODELS=1)
  - Sprint 21: Container isolation needed (Docling start/stop)

  Unplanned Effort:
    - GPU profiling: 3 days
    - Memory optimization: 5 days
    - Container architecture: 7 days
    - TOTAL: 15 days unplanned
```

**5. Scope Additions (Positive Discoveries):**

Development uncovered valuable improvements not in original plan:

```
Unplanned Features (Sprint 13-21):
  - Three-phase extraction pipeline (Sprint 13) → +18-20x performance
  - Semantic entity deduplication (Sprint 13) → +30% entity quality
  - BGE-M3 multilingual embeddings (Sprint 16) → +23% German retrieval
  - Docling GPU OCR (Sprint 21) → +35% accuracy improvement
  - VLM enrichment (Sprint 21) → Diagram understanding capability

  Total Value: Significant quality improvements beyond original MVP scope
```

---

## Decision

**Extend AegisRAG project from 12 sprints to 21+ sprints. Accept ongoing sprint planning based on discovered requirements and quality improvements.**

### Extension Rationale

**Not a Failure, but Agile Evolution:**

The 12-sprint estimate was based on MVP assumptions. Actual development revealed:
1. Higher quality bar needed for production use
2. Technology evolution required adaptation
3. GPU constraints required architectural changes
4. Valuable features discovered during implementation

**Alternative (Reject Extensions) Would Mean:**
- ❌ Ship with 70% OCR accuracy (unusable for German docs)
- ❌ Ship with 30% entity extraction success (poor Graph RAG)
- ❌ Skip GPU optimization (underutilize RTX 3060)
- ❌ Miss valuable features (three-phase pipeline, BGE-M3, Docling)

**Outcome:** **Sprint extensions were CORRECT decision** - delivered production-grade system vs. mediocre MVP.

### New Project Approach

**Shift from Fixed Timeline to Quality-Driven Sprints:**

```yaml
Old Approach (Sprint 1-12):
  Philosophy: "Deliver in 12 weeks, ship what's ready"
  Risk: Sacrifice quality for timeline
  Result: Would have shipped unusable system

New Approach (Sprint 13+):
  Philosophy: "Deliver production-grade features, timeline flexible"
  Focus: Quality, performance, real-world use case (OMNITRACKER docs)
  Result: Usable, high-quality RAG system

Sprint Criteria (Updated):
  - ✅ Feature meets production quality bar
  - ✅ Tests pass (>80% coverage)
  - ✅ Performance acceptable (latency, memory)
  - ✅ Documentation complete
  - ⏸️ Timeline: Secondary concern
```

---

## Alternatives Considered

### Alternative 1: Stick to 12 Sprints (Ship MVP)

**Pros:**
- ✅ Meet original timeline
- ✅ Deliver "something" in 3 months
- ✅ Lower development cost

**Cons:**
- ❌ OCR accuracy: 70% (unusable for scanned German docs)
- ❌ Entity extraction: 30% success (poor Graph RAG quality)
- ❌ No GPU optimization (RTX 3060 6GB wasted)
- ❌ LlamaIndex quality issues unresolved
- ❌ No three-phase pipeline (18-20x slower)

**Verdict:** **REJECTED** - Would have delivered unusable system. Extensions necessary for production readiness.

### Alternative 2: Re-Estimate and Fix New Timeline (24 sprints)

**Pros:**
- ✅ Realistic timeline upfront
- ✅ Stakeholder expectations managed
- ✅ Predictable delivery

**Cons:**
- ❌ Cannot predict future discoveries (3-phase pipeline, Docling)
- ❌ Inflexible to technology evolution
- ❌ May over-estimate (waste time on gold-plating)
- ❌ Solo development: No external pressure for fixed timeline

**Verdict:** **REJECTED** - Solo project allows flexibility. Quality-driven approach more valuable than artificial deadline.

### Alternative 3: Parallel Development (Cut Features, Meet Timeline)

**Pros:**
- ✅ Meet 12-sprint timeline
- ✅ Ship "something" on time
- ✅ Defer advanced features to future releases

**Cons:**
- ❌ Core features (OCR, extraction) cannot be "cut" - they're essential
- ❌ No external users yet (no deployment pressure)
- ❌ Cutting quality features defeats purpose of RAG system

**Verdict:** **REJECTED** - Core quality issues cannot be deferred. Extensions better than compromised features.

### Alternative 4: Hire More Developers (Accelerate)

**Pros:**
- ✅ Faster development (parallel work)
- ✅ More expertise (diverse skills)
- ✅ Could meet 12-sprint timeline

**Cons:**
- ❌ Solo developer project (Klaus Pommer + Claude Code)
- ❌ Hiring cost not justified for learning/research project
- ❌ Onboarding overhead (3-4 weeks lost to training)
- ❌ Coordination complexity (meetings, reviews, merge conflicts)

**Verdict:** **REJECTED** - Solo development model intentional (learning focus). Extensions cheaper than hiring.

---

## Rationale

### Why Sprint Extensions Were Necessary

**1. Production Quality Requirements:**

```
MVP vs. Production Gap (Sprint 1-12 vs. Sprint 13-21):

OCR Quality:
  - MVP (Sprint 10): 70% accuracy, Tesseract CPU
  - Production (Sprint 21): 95% accuracy, Docling GPU
  - Gap: +35% accuracy (CRITICAL for scanned German manuals)

Entity Extraction:
  - MVP (Sprint 5): 30% success, LightRAG default
  - Production (Sprint 13): 95% success, Three-phase pipeline
  - Gap: +65% success (CRITICAL for Graph RAG)

Performance:
  - MVP (Sprint 5): 300s per document
  - Production (Sprint 13): 15-17s per document
  - Gap: 18-20x speedup (CRITICAL for batch ingestion)

German Support:
  - MVP (Sprint 2): 768-dim English embeddings
  - Production (Sprint 16): 1024-dim multilingual BGE-M3
  - Gap: +23% German retrieval quality
```

**2. Technology Evolution:**

```
Framework Upgrades (Unplanned Effort):
  - LangGraph 0.2 → 0.6.10: 4 migrations × 2 days = 8 days
  - Gradio 4.44 → 5.49: 2 migrations × 1 day = 2 days
  - Ollama model evolution: 10 days benchmarking/testing
  - TOTAL: 20 days unplanned adaptation effort

Justification: Staying current prevents technical debt, enables new features (Send API, streaming, etc.)
```

**3. GPU Memory Optimization:**

```
Unforeseen Challenge (Sprint 11-21):
  - Original Plan: "RTX 3060 12GB should handle all models"
  - Reality: RTX 3060 6GB variant (not 12GB!)
  - Impact: qwen2.5:14b OOM, Ollama crashes, memory management critical

  Unplanned Sprints:
    - Sprint 11: GPU profiling and model swapping
    - Sprint 19: Mirostat v2 optimization
    - Sprint 21: Container isolation (Docling start/stop)
  - TOTAL: 15 days unplanned GPU work

  Value: System now runs reliably on 6GB VRAM (broader hardware compatibility)
```

**4. Valuable Discoveries:**

```
Features NOT in Original Plan (Positive ROI):

  - Three-Phase Pipeline (Sprint 13):
    Discovery: LightRAG too slow (300s/doc)
    Solution: SpaCy + Dedup + Gemma 3 4B
    Benefit: 18-20x speedup + higher quality
    Effort: 7 days
    ROI: MASSIVE (production-critical)

  - BGE-M3 Migration (Sprint 16):
    Discovery: German retrieval poor (nomic-embed-text English-only)
    Solution: Multilingual BGE-M3 (1024-dim)
    Benefit: +23% German quality
    Effort: 4 days
    ROI: HIGH (OMNITRACKER docs are German)

  - Docling CUDA (Sprint 21):
    Discovery: LlamaIndex OCR insufficient (70% accuracy)
    Solution: Docling GPU-accelerated OCR
    Benefit: +35% accuracy, +3.5x speed
    Effort: 7 days
    ROI: CRITICAL (scanned PDFs unusable without)
```

### Sprint Extension Impact

**Positive Outcomes:**
- ✅ Production-ready system (vs. unusable MVP)
- ✅ 95% OCR accuracy (vs. 70%)
- ✅ 95% entity extraction success (vs. 30%)
- ✅ 18-20x extraction performance
- ✅ GPU fully utilized (6GB VRAM optimized)
- ✅ German language support (+23% quality)

**Cost:**
- ⏰ 10 months vs. 3 months (7 months extra)
- 💰 Solo developer time (no external cost)

**ROI:** Extensions delivered **production-grade system** vs. **unusable MVP**. Trade-off justified.

---

## Consequences

### Positive

✅ **Production-Ready Quality:**
- System usable for real-world OMNITRACKER documentation
- 95% OCR accuracy on scanned German PDFs
- 95% entity extraction success rate
- Batch processing reliable (no OOM crashes)

✅ **Comprehensive Feature Set:**
- Three-phase extraction pipeline
- Docling GPU OCR
- BGE-M3 multilingual embeddings
- Container-based architecture
- VLM enrichment (diagrams/images)

✅ **Future-Proof Architecture:**
- LangGraph 0.6.10 (latest stable)
- Docker container isolation
- GPU memory optimization
- Modular, extensible design

✅ **Learning Outcomes:**
- Deep understanding of RAG architecture
- GPU optimization expertise
- LangGraph mastery
- Production deployment experience

### Negative

⚠️ **Timeline Overrun:**
- 10 months vs. 3 months (7 months delay)
- Original "MVP in 3 months" goal missed

**Mitigation:** Solo development with no external deadlines. Quality more important than timeline.

⚠️ **Scope Creep Risk:**
- Continuous improvement cycle (Sprint 22+ ongoing)
- Risk of "never done" syndrome
- Potential feature bloat

**Mitigation:** Define production deployment criteria (Sprint 22 exit conditions). Set explicit "done" state.

⚠️ **Documentation Lag:**
- Sprint 1-9 undocumented until Sprint 21
- ADRs created retroactively (ADR-027 to ADR-030)
- DRIFT_ANALYSIS needed to reconcile plans vs. reality

**Mitigation:** Ongoing documentation effort (Phase 1-4 of current plan).

### Neutral

🔄 **Agile Methodology Validated:**
- Fixed timeline impossible for research/learning project
- Quality-driven sprints more valuable
- Continuous adaptation to discoveries

🔄 **Solo Development Model:**
- Flexibility to extend timeline (no team pressure)
- Deep learning vs. fast delivery trade-off accepted
- Claude Code collaboration enables comprehensive work

---

## Future Sprint Planning

### Sprint 22+ Criteria (Exit Conditions)

**When to Consider Project "Complete":**

```yaml
Production Readiness Criteria:
  1. Backend Stability:
     - No major architecture changes for 2+ sprints
     - All core features stable (ingestion, retrieval, memory)
     - Test suite comprehensive (>80% coverage)

  2. Frontend Production-Ready:
     - React migration complete (ADR-029)
     - Perplexity-inspired UI deployed (ADR-020, ADR-021)
     - SSE streaming functional
     - Mobile-responsive design

  3. Documentation Complete:
     - All ADRs written (including gaps ADR-010 to ADR-013)
     - Sprint documentation backfilled (Sprint 1-21)
     - CLAUDE.md updated to Sprint 21 state
     - API documentation current

  4. External Deployment:
     - Kubernetes manifests ready
     - CI/CD pipeline functional (5 gates passing)
     - Monitoring dashboard deployed (Prometheus + Grafana)
     - Production instance running (external users)

  5. Performance Validated:
     - Batch ingestion: 100+ docs without OOM
     - Query latency: <500ms p95 (hybrid search)
     - OCR accuracy: >90% (German technical docs)
     - Entity extraction: >90% success rate
```

**Expected Timeline:**
- **Sprint 22:** React migration (10 days)
- **Sprint 23:** Production deployment (7 days)
- **Sprint 24:** External user testing + iteration (10 days)
- **TOTAL:** ~4-6 additional weeks → **PROJECT COMPLETE by January 2026**

### Ongoing vs. Complete

**Two Outcomes:**

**Option A: Declare Complete (January 2026)**
```yaml
Criteria Met:
  - Production deployed
  - External users onboarded
  - No critical bugs
  - Documentation current

State: "Version 1.0" release, maintenance mode
```

**Option B: Continuous Improvement**
```yaml
Rationale:
  - RAG technology evolving rapidly
  - New models (Llama 4, Gemma 4, etc.)
  - New features (advanced VLM, multi-modal search)
  - Performance optimizations

State: Ongoing sprints (Sprint 25, 26, ...) with lower velocity
```

**Recommended:** **Option A** (declare complete January 2026), then **Option B** (maintenance sprints at lower priority).

---

## Notes

**Extension as Success Indicator:**
- Extensions driven by quality improvements (NOT scope creep)
- Each sprint delivered tangible value (OCR quality, extraction speed, GPU optimization)
- Alternative (ship MVP in 12 sprints) would have failed production use case

**Solo Development Context:**
- No external pressure for fixed timeline
- Learning and research goals prioritize quality over speed
- Claude Code collaboration enables comprehensive work

**Comparison to Industry:**
```
Typical RAG MVP (Industry):
  - Timeline: 2-4 weeks
  - Quality: Basic (70-80% accuracy)
  - Use Case: Demo/prototype

AegisRAG (This Project):
  - Timeline: 10 months
  - Quality: Production-grade (95% accuracy)
  - Use Case: Real-world OMNITRACKER documentation (scanned German PDFs)

Conclusion: 10 months justified for production quality + learning goals
```

---

## References

**External:**
- [Agile Manifesto](https://agilemanifesto.org/) - "Responding to change over following a plan"
- [LangGraph Release Notes](https://github.com/langchain-ai/langgraph/releases) (0.2 → 0.6 evolution)
- [Scrum Guide](https://scrumguides.org/) - Sprint planning principles

**Internal:**
- **Original Roadmap:** `docs/PROJECT_SUMMARY.md` (12-sprint plan)
- **Sprint Summaries:** `docs/sprints/SPRINT_01-03_FOUNDATION_SUMMARY.md` (and others)
- **Drift Analysis:** `docs/DRIFT_ANALYSIS.md` (Section 4.1: Sprint Plan Divergence)
- **All Sprint 13-21 ADRs:** ADR-017 through ADR-029 (document extended scope)
- **CLAUDE.md:** Section "Current Project State (Sprint 15)" (outdated, needs Sprint 21 update)

---

**Author:** Klaus Pommer + Claude Code (documentation-agent)
**Reviewers:** N/A (Solo Development)
**Last Updated:** 2025-11-10
