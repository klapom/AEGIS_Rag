# Sprint 14 Plan: Backend Performance & Production Readiness

**Sprint Duration:** 2 weeks (14 days)
**Sprint Goal:** Integrate 3-Phase Pipeline, optimize Performance, achieve Production-Readiness
**Total Story Points:** 15 SP
**Theme:** Backend Excellence - Performance, Stability & CI/CD
**Status:** 🟢 IN PROGRESS
**Start Date:** 2025-10-25

---

## 📋 Executive Summary

Sprint 14 focuses on **backend stabilization and production readiness** following the successful implementation of the Three-Phase Extraction Pipeline in Sprint 13. This sprint integrates the new pipeline into LightRAG, optimizes performance, and establishes production-grade monitoring and CI/CD.

### Why This Sprint Exists

After Sprint 13's major feature implementation (3-Phase Pipeline), we need to:
- **Integrate** the new pipeline into production workflows
- **Optimize** performance and resource usage
- **Stabilize** CI/CD pipeline for reliable deployments
- **Prepare** for production deployment

### Key Deliverables

1. ✅ **LightRAG Integration** - ThreePhaseExtractor as default extraction method
2. ✅ **Configuration System** - Toggle between extraction pipelines
3. ✅ **Performance Benchmarks** - Comprehensive performance metrics
4. ✅ **GPU Optimization** - VRAM usage optimization
5. ✅ **Error Handling** - Production-grade retry logic
6. ✅ **Monitoring** - Prometheus metrics and structured logging
7. ✅ **CI/CD Stability** - Fix CI pipeline issues, add caching

---

## 🎯 Sprint Goals

### Primary Goals (Must-Have)

1. **Integrate 3-Phase Pipeline** into LightRAG workflow as default
2. **Optimize Performance** with benchmarking and GPU tuning
3. **Production Error Handling** with retry logic and graceful degradation
4. **Monitoring Infrastructure** with Prometheus metrics
5. **Stable CI/CD Pipeline** with caching and artifact management

### Secondary Goals (Nice-to-Have)

- Grafana dashboard for metrics visualization
- Docker multi-stage builds for size reduction
- Automated performance regression testing
- Code cleanup (remove experimental scripts)

### Success Criteria

- ✅ All LightRAG E2E tests pass with 3-phase pipeline
- ✅ Document processing: >300s → <60s (5x improvement minimum)
- ✅ Peak VRAM usage documented and optimized
- ✅ Error rate < 1% in production scenarios
- ✅ CI pipeline runs successfully end-to-end
- ✅ Prometheus metrics exposed and documented
- ✅ Zero critical bugs in production code

---

## 📊 Feature Breakdown

| Feature ID | Feature Name | Story Points | Priority | Status |
|-----------|--------------|--------------|----------|--------|
| **INTEGRATION & CORE** |
| 14.1 | Integrate 3-Phase Pipeline into LightRAG | 3 SP | 🔴 CRITICAL | 🔵 Planned |
| 14.2 | Configuration & Toggle System | 2 SP | 🔴 CRITICAL | 🔵 Planned |
| **PERFORMANCE** |
| 14.3 | Performance Benchmarking Suite | 2 SP | 🟠 HIGH | 🔵 Planned |
| 14.4 | GPU Memory Optimization | 2 SP | 🟠 HIGH | 🔵 Planned |
| **PRODUCTION READINESS** |
| 14.5 | Error Handling & Retry Logic | 2 SP | 🟠 HIGH | 🔵 Planned |
| 14.6 | Monitoring & Metrics | 2 SP | 🟡 MEDIUM | 🔵 Planned |
| **CI/CD** |
| 14.7 | CI/CD Pipeline Stability | 2 SP | 🟠 HIGH | 🔵 Planned |
| **TOTAL** | **15 SP** | | |

---

## 🚀 Feature Details

### Feature 14.1: Integrate 3-Phase Pipeline into LightRAG - 3 SP

**Priority:** 🔴 CRITICAL
**Complexity:** High
**Dependencies:** Sprint 13 Feature 13.9
**Estimated Time:** 2 days

#### Description

Replace LightRAG's default entity/relation extraction with the ThreePhaseExtractor pipeline. Update all workflows to use SpaCy NER + Semantic Dedup + Gemma 3 4B instead of llama3.2:3b-based extraction.

#### Technical Requirements

1. **LightRAG Wrapper Updates**
   - Replace `_extract_entities()` with `ThreePhaseExtractor.extract()`
   - Update `insert_documents()` workflow
   - Update `query_graph()` workflow if needed
   - Maintain backward compatibility for testing

2. **Entity/Relation Format Mapping**
   ```python
   # Map ThreePhaseExtractor output to LightRAG format
   def map_to_lightrag_format(entities, relations):
       # Ensure compatibility with Neo4j schema
       # Handle type mappings (SpaCy → LightRAG types)
   ```

3. **Testing Updates**
   - Update `test_sprint5_critical_e2e.py` to use new pipeline
   - Verify TD-31/32/33 tests pass with <60s execution
   - Add comparison tests (old vs new pipeline)

#### Acceptance Criteria

- ✅ `lightrag_wrapper.py` uses `ThreePhaseExtractor` by default
- ✅ All existing LightRAG E2E tests pass
- ✅ Performance: Document insertion <60s (vs >300s before)
- ✅ Quality: Same or better entity/relation accuracy
- ✅ Neo4j schema compatibility maintained
- ✅ No breaking changes to public API

#### Files to Modify

- `src/components/graph_rag/lightrag_wrapper.py`
- `tests/integration/test_sprint5_critical_e2e.py`
- `src/core/config.py` (if config changes needed)

---

### Feature 14.2: Configuration & Toggle System - 2 SP

**Priority:** 🔴 CRITICAL
**Complexity:** Medium
**Dependencies:** Feature 14.1
**Estimated Time:** 1 day

#### Description

Implement flexible configuration system to toggle between extraction pipelines (LightRAG default vs ThreePhase). Enable A/B testing and gradual rollout.

#### Technical Requirements

1. **Configuration Settings** (`src/core/config.py`)
   ```python
   # Entity/Relation Extraction Pipeline Selection (Sprint 14)
   extraction_pipeline: Literal["lightrag_default", "three_phase"] = Field(
       default="three_phase",
       description="Entity/relation extraction pipeline to use"
   )

   enable_legacy_extraction: bool = Field(
       default=False,
       description="Enable legacy LightRAG extraction for comparison"
   )

   # Performance tuning
   extraction_batch_size: int = Field(default=10, ge=1, le=100)
   extraction_max_workers: int = Field(default=4, ge=1, le=16)
   ```

2. **Factory Pattern**
   ```python
   # src/components/graph_rag/extraction_factory.py
   class ExtractionPipelineFactory:
       @staticmethod
       def create(config):
           if config.extraction_pipeline == "three_phase":
               return ThreePhaseExtractor(config)
           else:
               return LegacyLightRAGExtractor(config)
   ```

3. **Environment Variable Support**
   - `EXTRACTION_PIPELINE=three_phase`
   - `ENABLE_LEGACY_EXTRACTION=false`

#### Acceptance Criteria

- ✅ Can switch pipelines via environment variable
- ✅ Can switch pipelines via `.env` file
- ✅ Factory pattern implemented
- ✅ Tests cover both pipelines
- ✅ Default is `three_phase`
- ✅ Documentation updated

#### Files to Create/Modify

- `src/components/graph_rag/extraction_factory.py` (new)
- `src/core/config.py`
- `tests/unit/test_extraction_factory.py` (new)
- `README.md` (configuration section)

---

### Feature 14.3: Performance Benchmarking Suite - 2 SP

**Priority:** 🟠 HIGH
**Complexity:** Medium
**Dependencies:** Feature 14.1
**Estimated Time:** 1 day

#### Description

Create comprehensive benchmarking suite to measure performance across document types, sizes, and scenarios. Generate comparison reports.

#### Technical Requirements

1. **Benchmark Script** (`scripts/benchmark_production_pipeline.py`)
   ```python
   # Test scenarios
   scenarios = [
       ("small", 100-500 words),
       ("medium", 500-2000 words),
       ("large", 2000-5000 words),
       ("batch_10", 10 medium docs),
       ("batch_50", 50 small docs),
   ]

   # Metrics to collect
   - Extraction time (total + per phase)
   - Memory usage (RAM + VRAM)
   - Throughput (docs/minute)
   - Entity/relation counts
   - Quality scores (if ground truth available)
   ```

2. **Comparison Tests**
   - LightRAG default vs ThreePhase
   - Different model configurations (Q4_K_M vs Q8_0)
   - GPU vs CPU performance

3. **Report Generation**
   - Markdown report with tables and charts
   - JSON results for CI/CD integration
   - Performance regression detection

#### Acceptance Criteria

- ✅ Automated benchmark script runs end-to-end
- ✅ Tests all document size categories
- ✅ Generates comparison report (old vs new)
- ✅ Performance targets met:
  - Small docs: <10s
  - Medium docs: <30s
  - Large docs: <60s
  - Batch 10: <5 min
- ✅ Results saved to `benchmark_results_sprint14.json`

#### Files to Create

- `scripts/benchmark_production_pipeline.py`
- `docs/PERFORMANCE_BENCHMARKS.md`

---

### Feature 14.4: GPU Memory Optimization - 2 SP

**Priority:** 🟠 HIGH
**Complexity:** Medium
**Dependencies:** Feature 14.1, 14.3
**Estimated Time:** 1 day

#### Description

Profile and optimize GPU memory usage across the extraction pipeline. Enable efficient batch processing and document GPU requirements for different hardware.

#### Technical Requirements

1. **GPU Memory Profiling**
   - Profile SpaCy Transformer NER (en_core_web_trf)
   - Profile Gemma 3 4B Q4_K_M (via Ollama)
   - Measure peak VRAM during extraction
   - Identify memory leaks or inefficiencies

2. **Optimization Strategies**
   ```python
   # Batch size tuning based on VRAM
   def calculate_optimal_batch_size(available_vram_gb: float):
       # SpaCy: ~2GB base + ~100MB per 1000 tokens
       # Gemma Q4_K_M: ~2.5GB model + ~500MB per request
       # Target: Use 80% of available VRAM
       pass

   # Memory cleanup between phases
   def cleanup_gpu_memory():
       torch.cuda.empty_cache()
       gc.collect()
   ```

3. **Model Quantization Options**
   - Document Q4_K_M vs Q8_0 tradeoffs
   - Benchmark quality vs VRAM usage
   - Provide configuration guidance

4. **Hardware Requirements Documentation**
   - Minimum: RTX 3060 (12GB) - Q4_K_M
   - Recommended: RTX 4070 (16GB) - Q8_0
   - Optimal: RTX 4090 (24GB) - full precision

#### Acceptance Criteria

- ✅ Peak VRAM usage measured and documented
- ✅ Batch size auto-tuning implemented
- ✅ Memory cleanup between phases
- ✅ Runs efficiently on RTX 3060 (12GB VRAM)
- ✅ Configuration guide for different GPUs
- ✅ No CUDA OOM errors in normal operation

#### Files to Modify/Create

- `src/components/graph_rag/three_phase_extractor.py`
- `src/components/graph_rag/gemma_relation_extractor.py`
- `docs/GPU_REQUIREMENTS.md` (new)

---

### Feature 14.5: Error Handling & Retry Logic - 2 SP

**Priority:** 🟠 HIGH
**Complexity:** Medium
**Dependencies:** Feature 14.1
**Estimated Time:** 1 day

#### Description

Implement production-grade error handling with retry logic, graceful degradation, and comprehensive error tracking.

#### Technical Requirements

1. **Retry Logic for LLM Calls**
   ```python
   # Exponential backoff for Gemma API calls
   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=2, max=10),
       retry=retry_if_exception_type((ConnectionError, TimeoutError))
   )
   async def call_gemma_with_retry(self, text, entities):
       # Gemma relation extraction with retry
       pass
   ```

2. **Graceful Degradation**
   ```python
   # Phase 1: SpaCy NER fails → Fallback to regex NER
   try:
       entities = self._extract_entities_spacy(text)
   except Exception as e:
       logger.warning("spacy_ner_failed", error=str(e))
       entities = self._extract_entities_regex_fallback(text)

   # Phase 2: Deduplication fails → Skip dedup, continue
   try:
       deduplicated = self.deduplicator.deduplicate(entities)
   except Exception as e:
       logger.warning("dedup_failed", error=str(e))
       deduplicated = entities  # Continue without dedup

   # Phase 3: Gemma fails → Retry 3x, then return empty relations
   try:
       relations = await self._extract_relations_with_retry(text, entities)
   except Exception as e:
       logger.error("relation_extraction_failed_all_retries", error=str(e))
       relations = []  # Continue with entities only
   ```

3. **Structured Error Logging**
   - Correlation IDs for request tracking
   - Error context (input size, phase, attempt number)
   - Metrics for error rates

4. **Error Recovery Testing**
   - Test network failures (Ollama down)
   - Test model failures (invalid output)
   - Test resource exhaustion (OOM)

#### Acceptance Criteria

- ✅ Transient errors auto-retry (3x max with backoff)
- ✅ Permanent errors logged with full context
- ✅ Pipeline continues with degraded features (graceful degradation)
- ✅ Unit tests cover all failure scenarios
- ✅ Error metrics tracked (by type, phase, severity)
- ✅ Zero unhandled exceptions in production code

#### Files to Modify

- `src/components/graph_rag/three_phase_extractor.py`
- `src/components/graph_rag/gemma_relation_extractor.py`
- `src/components/graph_rag/semantic_deduplicator.py`
- `tests/unit/test_error_handling.py` (new)

---

### Feature 14.6: Monitoring & Metrics - 2 SP

**Priority:** 🟡 MEDIUM
**Complexity:** Medium
**Dependencies:** Feature 14.1
**Estimated Time:** 1 day

#### Description

Implement production monitoring with Prometheus metrics, structured logging, and health checks.

#### Technical Requirements

1. **Prometheus Metrics** (`src/monitoring/metrics.py`)
   ```python
   from prometheus_client import Counter, Histogram, Gauge

   # Extraction metrics
   extraction_duration = Histogram(
       'aegis_extraction_duration_seconds',
       'Time spent in extraction pipeline',
       ['phase', 'pipeline_type']
   )

   extraction_entities_total = Counter(
       'aegis_extraction_entities_total',
       'Total entities extracted',
       ['entity_type', 'pipeline_type']
   )

   extraction_relations_total = Counter(
       'aegis_extraction_relations_total',
       'Total relations extracted',
       ['pipeline_type']
   )

   extraction_errors_total = Counter(
       'aegis_extraction_errors_total',
       'Total extraction errors',
       ['phase', 'error_type']
   )

   gpu_memory_usage_bytes = Gauge(
       'aegis_gpu_memory_usage_bytes',
       'Current GPU memory usage'
   )
   ```

2. **Structured Logging Enhancements**
   ```python
   # Add correlation IDs
   import uuid

   correlation_id = str(uuid.uuid4())
   logger.info(
       "extraction_start",
       correlation_id=correlation_id,
       text_length=len(text),
       document_id=document_id
   )
   ```

3. **Health Check Endpoints** (`src/api/health.py`)
   ```python
   @router.get("/health/extraction")
   async def extraction_health():
       """Check extraction pipeline health."""
       return {
           "status": "healthy",
           "pipeline": "three_phase",
           "components": {
               "spacy": check_spacy_available(),
               "deduplicator": check_dedup_model(),
               "gemma": check_ollama_connection()
           }
       }
   ```

4. **Optional: Grafana Dashboard**
   - Extraction performance over time
   - Error rates by phase
   - GPU memory utilization
   - Throughput metrics

#### Acceptance Criteria

- ✅ Prometheus metrics exposed at `/metrics`
- ✅ Structured logs include correlation IDs
- ✅ Health check endpoint returns component status
- ✅ Metrics cover all extraction phases
- ✅ Error tracking by type and phase
- ✅ Sample Grafana dashboard JSON (optional)

#### Files to Create/Modify

- `src/monitoring/metrics.py` (new)
- `src/api/health.py`
- `src/components/graph_rag/three_phase_extractor.py`
- `grafana/dashboards/extraction_pipeline.json` (optional)

---

### Feature 14.7: CI/CD Pipeline Stability - 2 SP

**Priority:** 🟠 HIGH
**Complexity:** Medium
**Dependencies:** None
**Estimated Time:** 1 day

#### Description

Analyze and fix CI/CD pipeline issues from Sprint 13. Add dependency caching, optimize test execution, and ensure reliable CI runs.

#### Technical Requirements

1. **GitHub Actions Optimization**
   ```yaml
   # .github/workflows/ci.yml improvements

   # Add dependency caching
   - name: Cache Poetry dependencies
     uses: actions/cache@v3
     with:
       path: ~/.cache/pypoetry
       key: ${{ runner.os }}-poetry-${{ hashFiles('**/poetry.lock') }}

   # Add Docker layer caching
   - name: Cache Docker layers
     uses: actions/cache@v3
     with:
       path: /tmp/.buildx-cache
       key: ${{ runner.os }}-buildx-${{ github.sha }}

   # Optimize test execution
   - name: Run tests with coverage
     run: |
       poetry run pytest tests/ \
         --cov=src \
         --cov-report=xml \
         --cov-report=html \
         --timeout=300 \
         -n auto \  # Parallel execution
         --maxfail=5
   ```

2. **CI Pipeline Analysis**
   - Analyze current CI failures
   - Identify flaky tests
   - Optimize job dependencies
   - Add timeout budgets per job

3. **Test Infrastructure Improvements**
   - Separate unit and integration test jobs
   - Add test result artifacts
   - Add coverage trend tracking
   - Fail fast for critical errors

4. **Documentation**
   - CI/CD troubleshooting guide
   - How to debug CI failures locally
   - Performance optimization tips

#### Acceptance Criteria

- ✅ CI pipeline runs successfully end-to-end
- ✅ Dependency caching reduces build time by >50%
- ✅ Test jobs complete in <20 minutes
- ✅ Flaky tests identified and fixed/skipped
- ✅ Coverage artifacts uploaded to Codecov
- ✅ CI documentation complete

#### Files to Modify

- `.github/workflows/ci.yml`
- `docs/CI_CD_GUIDE.md` (new)

---

## 📈 Sprint 14 Timeline

### Week 1 (Days 1-7)

**Days 1-2**: Feature 14.1 - LightRAG Integration
- Integrate ThreePhaseExtractor into lightrag_wrapper.py
- Update E2E tests
- Verify performance improvements

**Day 3**: Feature 14.2 - Configuration System
- Implement extraction pipeline factory
- Add config settings
- Environment variable support

**Day 4**: Feature 14.3 - Performance Benchmarking
- Create benchmark script
- Run comprehensive tests
- Generate performance report

### Week 2 (Days 8-14)

**Day 5**: Feature 14.4 - GPU Optimization
- Profile VRAM usage
- Implement batch size tuning
- Document hardware requirements

**Day 6**: Feature 14.5 - Error Handling
- Implement retry logic
- Add graceful degradation
- Error handling tests

**Day 7**: Feature 14.6 - Monitoring
- Prometheus metrics
- Structured logging
- Health check endpoints

**Day 8**: Feature 14.7 - CI/CD Stability
- Fix CI pipeline issues
- Add caching
- Documentation

**Days 9-10**: Testing, Documentation, Buffer
- Integration testing across features
- Final documentation updates
- Address any blockers

---

## 🎯 Success Metrics

### Performance Metrics

- ✅ **Document Processing**: >300s → <60s (5x improvement)
- ✅ **Entity Extraction**: <1s per document (Phase 1)
- ✅ **Deduplication**: <2s per document (Phase 2)
- ✅ **Relation Extraction**: <20s per document (Phase 3)
- ✅ **Peak VRAM**: <8GB on RTX 3060
- ✅ **Throughput**: >10 docs/minute (small docs)

### Quality Metrics

- ✅ **Test Pass Rate**: 100% (all E2E tests)
- ✅ **Error Rate**: <1% in production scenarios
- ✅ **Entity Accuracy**: ≥95% (vs baseline)
- ✅ **Relation Accuracy**: ≥90% (vs baseline)
- ✅ **Deduplication Precision**: ≥90%

### CI/CD Metrics

- ✅ **Build Time**: <20 minutes (with caching)
- ✅ **Test Coverage**: ≥80%
- ✅ **CI Success Rate**: ≥95%
- ✅ **Flaky Test Rate**: <5%

---

## 📋 Definition of Done

A feature is "Done" when:

1. ✅ **Code Complete**: All code implemented and reviewed
2. ✅ **Tests Pass**: Unit tests + integration tests pass
3. ✅ **Documentation**: Code documented, README updated
4. ✅ **Performance**: Meets performance targets
5. ✅ **Error Handling**: Graceful error handling implemented
6. ✅ **Monitoring**: Metrics/logging in place
7. ✅ **CI/CD**: Passes CI pipeline
8. ✅ **Reviewed**: Code review complete (if applicable)

---

## 🔄 Risk Management

### High Risks

1. **LightRAG Integration Complexity** (Feature 14.1)
   - *Mitigation*: Thorough testing, maintain backward compatibility

2. **GPU Memory Issues** (Feature 14.4)
   - *Mitigation*: Extensive profiling, fallback to CPU if needed

3. **CI Pipeline Failures** (Feature 14.7)
   - *Mitigation*: Incremental fixes, parallel debugging

### Medium Risks

1. **Performance Regression**
   - *Mitigation*: Comprehensive benchmarking (Feature 14.3)

2. **Error Handling Edge Cases**
   - *Mitigation*: Extensive error scenario testing

---

## 📝 Notes

- Sprint 14 shifts from feature development to **production readiness**
- Focus on **stability, performance, and monitoring**
- React frontend migration moved to Sprint 15
- All work builds on Sprint 13's Three-Phase Pipeline foundation

---

**Sprint 14 Status**: 🟢 READY TO START
**Next Steps**: Create branch `sprint-14-backend-performance` and begin Feature 14.1
