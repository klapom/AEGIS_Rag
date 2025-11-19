# ADR-037: Alibaba Cloud (Qwen3-32B) for Entity/Relation Extraction

**Status:** ACCEPTED (2025-11-19)
**Supersedes:** Local-only extraction (Gemma 2 4B)
**Deciders:** Project Lead (Klaus Pommer)
**Date Created:** 2025-11-19
**Date Accepted:** 2025-11-19
**Sprint:** Sprint 30 (VLM-Enhanced PDF Indexing)

---

## Context and Problem Statement

### Background

In Sprint 21-23, we established a three-tier LLM execution strategy via AegisLLMProxy (ADR-033):

- **Tier 1:** Local Ollama (FREE, 70% of tasks)
- **Tier 2:** Alibaba Cloud / Qwen models (cost-effective, 20% of tasks)
- **Tier 3:** OpenAI (critical quality, 10% of tasks)

**Current Entity/Relation Extraction:**
- **Model:** Local Gemma 2 4B (4 billion parameters)
- **Quality:** Good (adequate for most use cases)
- **Cost:** $0/month (local execution)
- **Complexity Setting:** MEDIUM → Routes to local only
- **Routing Logic:** Does NOT meet threshold for Alibaba Cloud (requires HIGH complexity + HIGH quality)

### Problem Statement

Entity and relationship extraction is a **HIGH complexity task** that requires:
1. Understanding context and semantic relationships
2. Extracting structured JSON from unstructured text
3. Identifying entity types with nuanced understanding
4. Resolving ambiguous entity references

**Current Mismatch:**
- Extraction is marked as `Complexity.MEDIUM`
- Actual complexity is **HIGH** (context understanding + structured extraction)
- Alibaba Cloud routing requires `Complexity.HIGH` + `QualityRequirement.HIGH`
- **Result:** Extraction always routes to local 4B model (suboptimal quality)

### LightRAG GitHub Research

**Finding:** NO recent entity extraction improvements for Qwen models in LightRAG.

Recent LightRAG commit (Jan 30, 2025): "Improve prompts to avoid make-up respond from LLM like qwen-plus"
- Modified RAG **response** prompts (NOT extraction prompts)
- Entity extraction prompts remain model-agnostic
- No Qwen-specific optimizations to adopt

**Conclusion:** No LightRAG improvements justify Alibaba Cloud adoption. However, **model parameter count** (32B vs 4B) provides significant quality improvement.

---

## Decision Drivers

### Quality vs. Cost Analysis

| Factor | Local Gemma 2 4B | Alibaba Cloud Qwen3-32B |
|--------|------------------|--------------------------|
| **Parameters** | 4 billion | 32 billion (8x larger) |
| **Quality** | Good | Excellent |
| **Context Understanding** | Limited | Advanced |
| **Entity Disambiguation** | Basic | Advanced |
| **Relationship Extraction** | Adequate | Superior |
| **Cost** | $0/month | ~$0.001-0.003 per 1,000 tokens |
| **Monthly Budget** | - | $120 (covers ~40,000-120,000 chunks) |
| **Fallback** | None (already local) | Automatic to local if budget exceeded |

### Routing Logic (AegisLLMProxy)

**Current Routing (Complexity.MEDIUM):**
```python
# extraction_service.py:269
task = LLMTask(
    task_type=TaskType.EXTRACTION,
    quality_requirement=QualityRequirement.HIGH,  # HIGH
    complexity=Complexity.MEDIUM,  # MEDIUM ← Does NOT route to Alibaba
)
```

**Routing Decision:**
- Quality: HIGH ✓
- Complexity: MEDIUM ✗
- **Result:** Routes to `local_ollama` (default)

**Alibaba Cloud Routing Threshold (aegis_llm_proxy.py:343-351):**
```python
# Alibaba Cloud preferred for:
if (
    task.quality_requirement == QualityRequirement.HIGH
    and task.complexity == Complexity.HIGH  # REQUIRES HIGH!
    and not self._is_budget_exceeded("alibaba_cloud")
):
    return ("alibaba_cloud", "high_quality_high_complexity")
```

**Required Change:**
```python
# extraction_service.py:269, 392
complexity=Complexity.HIGH,  # Changed from MEDIUM (enables Alibaba Cloud routing)
```

### Cost-Benefit Analysis

**Estimated Usage:**
- Average document: 1,800-token chunks
- Entities per chunk: ~10-20 entities
- Relations per chunk: ~5-15 relations
- Extraction prompt: ~500 tokens input + ~1,000 tokens output
- **Cost per chunk:** ~$0.0015-0.0045 USD
- **Cost per document (26 chunks):** ~$0.039-0.117 USD

**Monthly Budget:**
- Budget: $120/month (configurable in llm_config.yml)
- Documents per month: ~1,000-3,000 documents
- **Budget covers:** 40,000-120,000 chunks/month

**Quality Improvement:**
- **32B vs 4B parameters:** 8x model size
- Expected entity accuracy: 85% → 95% (+10%)
- Expected relation accuracy: 75% → 90% (+15%)
- Better disambiguation and context understanding

---

## Decision

**ACCEPTED:** Change entity/relation extraction complexity from MEDIUM to HIGH to enable Alibaba Cloud (qwen3-32b) routing.

### Implementation

**Changed Files:**
1. `src/components/graph_rag/extraction_service.py`

**Changes:**
```python
# Line 269 (Entity Extraction)
complexity=Complexity.HIGH,  # High complexity enables Alibaba Cloud routing (Sprint 30)

# Line 392 (Relationship Extraction)
complexity=Complexity.HIGH,  # High complexity enables Alibaba Cloud routing (Sprint 30)
```

**Expected Routing:**
- **Provider:** `alibaba_cloud`
- **Model:** `qwen3-32b` (32B parameters)
- **Routing Reason:** `high_quality_high_complexity`
- **Fallback:** Automatic to `local_ollama` if budget exceeded

**Budget Configuration (config/llm_config.yml):**
```yaml
budgets:
  monthly_limits:
    alibaba_cloud: 120.0  # $120/month (60% of total budget)
  alert_threshold: 0.8    # Alert at 80% budget utilization

model_defaults:
  alibaba_cloud:
    extraction: qwen3-32b   # High quality extraction (32B params)
```

---

## Consequences

### Positive Consequences

1. **Improved Extraction Quality:**
   - 8x larger model (32B vs 4B parameters)
   - Better entity disambiguation
   - Superior relationship extraction
   - Advanced context understanding

2. **Cost-Effective:**
   - $120/month covers 1,000-3,000 documents
   - ~$0.039-0.117 per document
   - Automatic fallback to local if budget exceeded

3. **Automatic Budget Management:**
   - Built-in budget tracking (SQLite database)
   - Alert at 80% utilization
   - Monthly reset on 1st of each month
   - No manual intervention needed

4. **Minimal Code Changes:**
   - One-line change per method (2 changes total)
   - No infrastructure work needed
   - Leverages existing AegisLLMProxy routing

5. **Production-Ready:**
   - Automatic fallback to local
   - Budget enforcement
   - Cost tracking and monitoring
   - Graceful degradation

### Negative Consequences

1. **Operational Costs:**
   - $120/month (vs $0 for local)
   - Requires Alibaba Cloud API key
   - Requires monitoring of budget utilization

2. **Cloud Dependency:**
   - Requires internet connectivity
   - Subject to Alibaba Cloud API availability
   - Latency: +200-500ms per extraction (network overhead)

3. **Budget Monitoring Required:**
   - Must track monthly spend
   - Alerts at 80% threshold
   - Fallback to local if exceeded (quality degradation)

### Risk Mitigation

1. **Automatic Fallback:**
   - Falls back to local Gemma 2 4B if budget exceeded
   - Ensures continuous operation (no downtime)

2. **Budget Alerts:**
   - Alert at 80% utilization (before limit hit)
   - SQLite cost tracking for monitoring
   - Monthly reset prevents runaway costs

3. **Cost Monitoring:**
   ```bash
   # Check cost tracking database
   sqlite3 data/cost_tracking.db "SELECT * FROM costs WHERE provider='alibaba_cloud' ORDER BY timestamp DESC LIMIT 10;"
   ```

4. **Budget Adjustment:**
   - Configurable in `config/llm_config.yml`
   - Can increase/decrease monthly limit as needed
   - Can disable by removing API key

---

## Validation

### Test Verification

**Test Command:**
```bash
poetry run python scripts/test_single_pdf.py "path/to/test.pdf"
```

**Expected Logs:**
```json
{
  "event": "routing_decision",
  "provider": "alibaba_cloud",
  "routing_reason": "high_quality_high_complexity",
  "task_type": "extraction",
  "quality": "high",
  "complexity": "high"
}

{
  "event": "llm_entity_extraction_response",
  "provider": "alibaba_cloud",
  "model": "qwen3-32b",
  "cost_usd": 0.0023,
  "tokens_input": 512,
  "tokens_output": 1024
}
```

**Cost Tracking Verification:**
```bash
sqlite3 data/cost_tracking.db "SELECT provider, model, SUM(cost_usd) FROM costs WHERE date(timestamp) = date('now') GROUP BY provider;"
```

### Quality Metrics

**Baseline (Gemma 2 4B):**
- Entity accuracy: ~85%
- Relation accuracy: ~75%
- Extraction time: ~15-17s per document

**Expected (Qwen3-32B):**
- Entity accuracy: ~95% (+10%)
- Relation accuracy: ~90% (+15%)
- Extraction time: ~15-20s per document (+3-5s cloud latency)

---

## Related Decisions

- **ADR-033:** Mozilla ANY-LLM Integration + Alibaba Cloud (establishes three-tier routing)
- **ADR-026:** Pure LLM Extraction Default (establishes LLM-based extraction as default)
- **ADR-018:** Gemma 2 4B Model Selection (original local extraction model)
- **ADR-005:** LightRAG over Microsoft GraphRAG (knowledge graph construction)

---

## References

- **LightRAG GitHub:** https://github.com/HKUDS/LightRAG
- **Alibaba DashScope:** https://dashscope-intl.aliyuncs.com/
- **Qwen3 Model Documentation:** https://qwen.readthedocs.io/
- **AegisLLMProxy Implementation:** `src/components/llm_proxy/aegis_llm_proxy.py`
- **Extraction Service:** `src/components/graph_rag/extraction_service.py`
- **LLM Config:** `config/llm_config.yml`

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-11-19 | Initial decision record created | Klaus Pommer |
| 2025-11-19 | Decision ACCEPTED - implementation complete | Klaus Pommer |

---

## Notes

**Rationale for HIGH Complexity:**

Entity and relationship extraction IS high complexity because it requires:

1. **Context Understanding:** Understanding semantic relationships across multiple sentences
2. **Structured Extraction:** Converting unstructured text to structured JSON
3. **Entity Disambiguation:** Resolving ambiguous entity references (e.g., "Germany" vs "German government")
4. **Type Classification:** Determining correct entity types (ORGANIZATION, PERSON, LOCATION, etc.)
5. **Relationship Inference:** Inferring implicit relationships between entities

**Previous MEDIUM classification was incorrect** - this task requires advanced language understanding capabilities that benefit significantly from larger models (32B >> 4B parameters).

**Cost-Benefit Justification:**

At $0.039-0.117 per document, the quality improvement (10-15% higher accuracy) is worth the cost for production use cases where accurate knowledge graph construction is critical for downstream retrieval and reasoning tasks.
